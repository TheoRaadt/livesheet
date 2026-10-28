"""Vectors and matrices: bracket pre-parse, the matrix value type and matrix functions.

A matrix is an immutable SymPy matrix (``LMat``) whose operators raise worksheet-style
errors. Indices are 1-based. The text ``[a, b; c, d]`` is rewritten before parsing into
``_mat(_row(a, b), _row(c, d))`` and ``X[i, j]`` into ``_idx(X, i, j)``.
"""

from __future__ import annotations

import sympy as sp
from sympy.physics.units import Quantity

from .syntax import StatementError

MAX_SIZE = 200
_DENSE = sp.ImmutableDenseMatrix
_SINGULAR_TOLERANCE = 1e-12


# ---------------------------------------------------------------- pre-parse

def rewrite_brackets(text: str) -> str:
    """Rewrite matrix literals and index brackets into plain function calls."""
    if "[" not in text and "]" not in text:
        return text
    return _convert(text, in_literal=False)


def _convert(text: str, in_literal: bool) -> str:
    out = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "[":
            j = _matching_bracket(text, i)
            inner = text[i + 1:j]
            if out and (out[-1].isalnum() or out[-1] in "_)."):
                start = _operand_start(out)
                args = [_convert_index(a, in_literal) for a in _split_top(inner, ",")]
                out = out[:start] + "_idx(" + out[start:] + ", " + ", ".join(args) + ")"
            else:
                if in_literal:
                    raise StatementError("Nested matrices are not supported")
                out += _literal(inner)
            i = j + 1
        elif ch == "]":
            raise StatementError("Unbalanced brackets")
        else:
            out += ch
            i += 1
    return out


def _matching_bracket(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    raise StatementError("Unbalanced brackets")


def _operand_start(out: str) -> int:
    """Start of the atom (name, call or parenthesised group) that ends ``out``."""
    end = len(out)
    if out[-1] == ")":
        depth = 0
        for k in range(end - 1, -1, -1):
            if out[k] == ")":
                depth += 1
            elif out[k] == "(":
                depth -= 1
                if depth == 0:
                    end = k
                    break
        else:
            raise StatementError("Unbalanced brackets")
    k = end
    while k > 0 and (out[k - 1].isalnum() or out[k - 1] in "_."):
        k -= 1
    return k


def _split_top(text: str, sep: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _convert_index(arg: str, in_literal: bool) -> str:
    arg = arg.strip()
    if arg == ":":
        return "_all"
    if not arg:
        raise StatementError("Empty index")
    return _convert(arg, in_literal)


def _literal(inner: str) -> str:
    if not inner.strip():
        return "_mat()"
    rows = []
    for row in _split_top(inner, ";"):
        cells = []
        for cell in _split_top(row, ","):
            if not cell.strip():
                raise StatementError("Empty matrix element")
            text = _convert(cell.strip(), True)
            cells.append(f"_c({text}, {text!r})")
        rows.append("_row(" + ", ".join(cells) + ")")
    return "_mat(" + ", ".join(rows) + ")"


# ---------------------------------------------------------------- value type

# While a parse is running: (engine, env), so zero-valued cells can recover their unit.
CONTEXT: list = []


def _has_unit(x) -> bool:
    return isinstance(x, sp.Basic) and x.has(Quantity)


def keep_cell(value, text: str):
    """Cell value; a zero that lost its unit (``0 m``) is re-read unevaluated to keep it."""
    if CONTEXT and isinstance(value, sp.Expr) and value == 0:
        engine, env = CONTEXT[-1]
        try:
            kept = engine._parse_unevaluated(text, env)
        except Exception:  # noqa: BLE001 - best effort only
            return value
        if _has_unit(kept):
            return kept
    return value


def smul(a, b):
    r = a * b
    if r == 0 and (_has_unit(a) or _has_unit(b)):
        return sp.Mul(a, b, evaluate=False)
    return r


def sdiv(a, b):
    r = a / b
    if r == 0 and (_has_unit(a) or _has_unit(b)):
        return sp.Mul(a, sp.Pow(b, -1, evaluate=False), evaluate=False)
    return r


def sadd(a, b):
    r = a + b
    if r == 0 and (_has_unit(a) or _has_unit(b)):
        return sp.Add(a, b, evaluate=False)
    return r


def ssub(a, b):
    r = a - b
    if r == 0 and (_has_unit(a) or _has_unit(b)):
        return sp.Add(a, sp.Mul(-1, b, evaluate=False), evaluate=False)
    return r


def sneg(a):
    return sp.Mul(-1, a, evaluate=False) if _has_unit(a) and (-a) == 0 else -a


def _shape(m) -> str:
    return f"{m.rows}x{m.cols}"


def _is_scalar(x) -> bool:
    return isinstance(x, (sp.Expr, int, float, complex)) and not isinstance(x, sp.MatrixBase)


class LMat(_DENSE):
    """Immutable matrix with worksheet error messages for the arithmetic operators."""

    def _same_shape(self, other) -> None:
        if (self.rows, self.cols) != (other.rows, other.cols):
            raise StatementError(f"Matrix sizes do not match: {_shape(self)} and {_shape(other)}")

    def _elementwise(self, other, op, scalar_message: str):
        if isinstance(other, sp.MatrixBase):
            self._same_shape(other)
            return wrap(self.rows, self.cols, [op(a, b) for a, b in zip(self, other)])
        raise StatementError(scalar_message)

    def __add__(self, other):
        return self._elementwise(other, sadd, "Cannot add a scalar to a matrix")

    __radd__ = __add__

    def __sub__(self, other):
        return self._elementwise(other, ssub, "Cannot add a scalar to a matrix")

    def __rsub__(self, other):
        if isinstance(other, sp.MatrixBase):
            return wrap(other) - self
        raise StatementError("Cannot add a scalar to a matrix")

    def __neg__(self):
        return wrap(self.rows, self.cols, [sneg(a) for a in self])

    def __pos__(self):
        return self

    def __mul__(self, other):
        if isinstance(other, sp.MatrixBase):
            if self.cols != other.rows:
                raise StatementError(f"Cannot multiply {_shape(self)} by {_shape(other)}")
            prod = _fix_zero_units(self, other, plain(self) * plain(other))
            if prod.rows == 1 and prod.cols == 1:
                return prod[0, 0]
            return wrap(prod)
        if _is_scalar(other):
            other = sp.sympify(other)
            return wrap(self.rows, self.cols, [smul(a, other) for a in self])
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, sp.MatrixBase):
            return wrap(other) * self
        if _is_scalar(other):
            other = sp.sympify(other)
            return wrap(self.rows, self.cols, [smul(other, a) for a in self])
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, sp.MatrixBase):
            raise StatementError("Cannot divide by a matrix; use inv(...)")
        if _is_scalar(other):
            other = sp.sympify(other)
            return wrap(self.rows, self.cols, [sdiv(a, other) for a in self])
        return NotImplemented

    def __rpow__(self, other):
        raise StatementError("A matrix cannot be used as an exponent")

    def __rtruediv__(self, other):
        raise StatementError("Cannot divide by a matrix; use inv(...)")

    def __pow__(self, exponent, modulo=None):
        n = sp.sympify(exponent)
        if isinstance(n, sp.MatrixBase) or not n.is_Integer:
            raise StatementError("Matrix power must be an integer")
        _square(self)
        if n == 0:
            return wrap(_DENSE.eye(self.rows))
        base = self if n > 0 else inv(self)
        return wrap(plain(base) ** abs(int(n)))


def _fix_zero_units(a, b, prod):
    """Recompute zero entries of a product whose factors carry units, so the unit stays."""
    if not any(_has_unit(e) for e in list(a) + list(b)):
        return prod
    flat = list(prod)
    for i in range(prod.rows):
        for j in range(prod.cols):
            if flat[i * prod.cols + j] == 0:
                terms = [smul(a[i, k], b[k, j]) for k in range(a.cols)]
                total = terms[0]
                for t in terms[1:]:
                    total = sadd(total, t)
                flat[i * prod.cols + j] = total
    return _DENSE(prod.rows, prod.cols, flat)


def plain(m):
    """The same matrix as a plain (non-``LMat``) SymPy matrix, with native operators."""
    return _DENSE(m.rows, m.cols, list(m))


def wrap(*args) -> LMat:
    """Build an ``LMat`` from a matrix, or from (rows, cols, flat list)."""
    if len(args) == 1:
        m = args[0]
        return m if isinstance(m, LMat) else LMat(m.rows, m.cols, list(m))
    return LMat(*args)


# ---------------------------------------------------------------- helpers

def _need_matrix(name: str, x) -> sp.MatrixBase:
    if not isinstance(x, sp.MatrixBase):
        _not_defined(x)
        raise StatementError(f"{name}() needs a matrix")
    return x


def _not_defined(x) -> None:
    if isinstance(x, sp.Symbol):
        raise StatementError(f"{x.name} is not defined")


def _square(m) -> None:
    if m.rows != m.cols:
        raise StatementError(f"Matrix must be square (got {_shape(m)})")


def _is_vector(m) -> bool:
    return m.rows == 1 or m.cols == 1


def _need_vector(name: str, x) -> list:
    _need_matrix(name, x)
    if not _is_vector(x):
        raise StatementError(f"{name}() needs vectors")
    return list(x)


def _numeric_array(m):
    """numpy array when every entry is a plain number without units, else None."""
    if not all(e.is_number and not e.has(Quantity) for e in m):
        return None
    import numpy as np

    complex_entries = any(e.is_real is False for e in m)
    try:
        return np.array([[complex(m[r, c]) if complex_entries else float(m[r, c])
                          for c in range(m.cols)] for r in range(m.rows)])
    except (TypeError, ValueError):
        return None


def _has_float(m) -> bool:
    return any(e.has(sp.Float) for e in m)


def _from_array(arr):
    def conv(x):
        x = complex(x)
        return sp.Float(x.real) if x.imag == 0 else sp.Float(x.real) + sp.I * sp.Float(x.imag)

    if arr.ndim == 0:
        return conv(arr)
    return wrap(arr.shape[0], arr.shape[1], [conv(x) for x in arr.flatten()])


def strip_units(m):
    """Matrix of SI magnitudes (units removed); raises UnitError on inconsistent sums."""
    from .units import measure

    return _DENSE(m.rows, m.cols, [measure(e).magnitude if e.has(Quantity) else e for e in m])


def is_singular(m) -> bool:
    mag = strip_units(m)
    arr = _numeric_array(mag)
    if arr is not None and _has_float(mag):
        import numpy as np

        s = np.linalg.svd(arr, compute_uv=False)
        return bool(s[0] == 0 or s[-1] <= _SINGULAR_TOLERANCE * s[0])
    d = mag.det()
    return d == 0 if d.is_Rational else sp.simplify(d) == 0


MAX_SYMBOLIC = 5


def _check_symbolic_size(m) -> None:
    if max(m.rows, m.cols) > MAX_SYMBOLIC and any(e.free_symbols for e in m):
        raise StatementError(f"Matrix too large for symbolic evaluation (max {MAX_SYMBOLIC}x{MAX_SYMBOLIC}); "
                             "use numeric entries")


def _require_invertible(m) -> None:
    _square(m)
    _check_symbolic_size(m)
    if is_singular(m):
        raise StatementError("Matrix is singular")


# ---------------------------------------------------------------- functions

def det(m):
    _need_matrix("det", m)
    _square(m)
    _check_symbolic_size(m)
    arr = _numeric_array(m)
    if arr is not None and _has_float(m):
        import numpy as np

        return _from_array(np.linalg.det(arr))
    return m.det()


def inv(m):
    _need_matrix("inv", m)
    _require_invertible(m)
    arr = _numeric_array(m)
    if arr is not None and _has_float(m):
        import numpy as np

        return _from_array(np.linalg.inv(arr))
    return wrap(m.inv())


def transpose(m):
    _need_matrix("transpose", m)
    return wrap(m.T)


def trace(m):
    _need_matrix("trace", m)
    _square(m)
    return sp.Add(*[m[i, i] for i in range(m.rows)])


def solve_system(a, b):
    _need_matrix("solve_system", a)
    _need_matrix("solve_system", b)
    _square(a)
    if b.rows != a.rows:
        raise StatementError(f"Right-hand side has {b.rows} rows, matrix has {a.rows}")
    _require_invertible(a)
    arr_a, arr_b = _numeric_array(a), _numeric_array(b)
    if arr_a is not None and arr_b is not None and (_has_float(a) or _has_float(b)):
        import numpy as np

        return _from_array(np.linalg.solve(arr_a, arr_b))
    return wrap(a.inv() * b)


def dot(u, v):
    a, b = _need_vector("dot", u), _need_vector("dot", v)
    if len(a) != len(b):
        raise StatementError("dot() needs vectors of equal length")
    return sp.Add(*[x * y for x, y in zip(a, b)])


def cross(u, v):
    a, b = _need_vector("cross", u), _need_vector("cross", v)
    if len(a) != 3 or len(b) != 3:
        raise StatementError("cross() needs vectors of length 3")
    flat = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    return wrap(1, 3, flat) if u.rows == 1 and u.cols == 3 else wrap(3, 1, flat)


def hadamard(a, b):
    _need_matrix("hadamard", a)
    _need_matrix("hadamard", b)
    a = wrap(a)
    return a._elementwise(b, smul, "")


def _size(x) -> int:
    n = sp.sympify(x)
    if isinstance(n, sp.MatrixBase) or not (n.is_Integer and n > 0):
        raise StatementError("Size must be a positive integer")
    if n > MAX_SIZE:
        raise StatementError(f"Size too large (max {MAX_SIZE})")
    return int(n)


def eye(n):
    return wrap(_DENSE.eye(_size(n)))


def zeros(r, c):
    r, c = _size(r), _size(c)
    return wrap(r, c, [sp.Integer(0)] * (r * c))


def ones(r, c):
    r, c = _size(r), _size(c)
    return wrap(r, c, [sp.Integer(1)] * (r * c))


def diag(v):
    items = _need_vector("diag", v)
    n = len(items)
    flat = [items[i] if i == j else sp.Integer(0) for i in range(n) for j in range(n)]
    return wrap(n, n, flat)


def nrows(m):
    return sp.Integer(_need_matrix("nrows", m).rows)


def ncols(m):
    return sp.Integer(_need_matrix("ncols", m).cols)


def length(v):
    _need_matrix("len", v)
    if not _is_vector(v):
        raise StatementError("len() needs a vector")
    return sp.Integer(v.rows * v.cols)


# ---------------------------------------------------------------- constructors / indexing

ALL = sp.Symbol("_all")  # marker for the ``:`` slice (the parser turns the name into this symbol)


def make_row(*cells):
    return tuple(cells)


def make_matrix(*rows):
    if not rows:
        raise StatementError("Empty matrix")
    width = len(rows[0])
    for row in rows[1:]:
        if len(row) != width:
            raise StatementError(f"Rows have different lengths ({width} and {len(row)})")
    flat = []
    for row in rows:
        for cell in row:
            if isinstance(cell, sp.MatrixBase):
                raise StatementError("Nested matrices are not supported")
            flat.append(sp.sympify(cell))
    return LMat(len(rows), width, flat)


def _index(spec, size: int):
    if spec == ALL:
        return ALL
    k = sp.sympify(spec)
    if not k.is_Integer:
        raise StatementError("Index must be an integer")
    if k < 1 or k > size:
        raise StatementError(f"Index {k} out of range 1..{size}")
    return int(k) - 1


def index(x, *specs):
    if not isinstance(x, sp.MatrixBase):
        _not_defined(x)
        raise StatementError("Only matrices can be indexed")
    if len(specs) == 1:
        if not _is_vector(x):
            raise StatementError("A matrix needs two indices")
        k = _index(specs[0], x.rows * x.cols)
        if k == ALL:
            return wrap(x)
        return list(x)[k]
    if len(specs) != 2:
        raise StatementError("Too many indices")
    r, c = _index(specs[0], x.rows), _index(specs[1], x.cols)
    if r == ALL and c == ALL:
        return wrap(x)
    if r == ALL:
        return wrap(x.rows, 1, [x[i, c] for i in range(x.rows)])
    if c == ALL:
        return wrap(1, x.cols, [x[r, j] for j in range(x.cols)])
    return x[r, c]

# ---------------------------------------------------------------- spec 002b: eigen-analysis

EXACT_MODE = [False]  # set by the evaluator while a symbolic (arrow) result is computed
_EIG_TOLERANCE = 1e-10
_DEFECT_TOLERANCE = 1e-8
_NO_CLOSED_FORM = "No closed form found; use ="


def unit_of(dims):
    """Product of base units for a dimension tuple (empty tuple gives 1)."""
    from .units import BASE_UNIT_BY_DIM

    expr = sp.Integer(1)
    for dim, exp in dims:
        expr = expr * BASE_UNIT_BY_DIM[dim] ** exp
    return expr


def split_units(m):
    """(matrix of SI magnitudes, common dimension tuple); mixed dimensions raise UnitError.

    A zero without a unit fits any dimension, as in result formatting.
    """
    from .units import UnitError, measure

    mags, seen = [], set()
    for e in m:
        meas = measure(e) if _has_unit(e) else None
        mag, dims = (meas.magnitude, meas.dims) if meas else (e, ())
        mags.append(mag)
        if mag != 0 or dims:
            seen.add(dims)
    if len(seen) > 1:
        raise UnitError("Units do not match")
    return _DENSE(m.rows, m.cols, mags), next(iter(seen), ())


def attach_units(m, dims) -> LMat:
    """Matrix ``m`` (SI magnitudes) multiplied by the unit of ``dims``."""
    if not dims:
        return wrap(m)
    unit = unit_of(dims)
    return wrap(m.rows, m.cols, [smul(e, unit) for e in m])


def _symbolic_entries(m) -> bool:
    return any(e.free_symbols for e in m)


def _use_exact(m) -> bool:
    return _symbolic_entries(m) or (EXACT_MODE[0] and not _has_float(m))


def _entries_array(m, what: str):
    arr = _numeric_array(m)
    if arr is None:
        raise StatementError(f"{what} needs numeric matrix entries")
    return arr


def _order(vals) -> list[int]:
    """Indices that sort complex values by real part, ties (within tolerance) by imaginary part."""
    scale = max((abs(v) for v in vals), default=0.0)
    tol = _EIG_TOLERANCE * scale
    idx = sorted(range(len(vals)), key=lambda i: (vals[i].real, vals[i].imag))
    out, group = [], []
    for i in idx:
        if group and vals[i].real - vals[group[0]].real > tol:
            out += sorted(group, key=lambda k: (vals[k].imag, vals[k].real))
            group = []
        group.append(i)
    return out + sorted(group, key=lambda k: (vals[k].imag, vals[k].real))


def _fix_vectors(vecs, tol: float = 1e-12):
    """Sign/phase convention (first significant component positive) and noise snapping."""
    import numpy as np

    vecs = vecs.astype(complex)
    for k in range(vecs.shape[1]):
        col = vecs[:, k]
        big = np.nonzero(np.abs(col) > _EIG_TOLERANCE)[0]
        if big.size:
            lead = col[big[0]]
            vecs[:, k] = col * (np.conj(lead) / abs(lead))
    vecs.real[np.abs(vecs.real) < tol] = 0.0
    vecs.imag[np.abs(vecs.imag) < tol] = 0.0
    return vecs


def _eig_numeric(arr, want_vectors: bool):
    """Sorted eigenvalues (complex array) and unit eigenvectors (columns) of a float matrix."""
    import numpy as np

    arr = arr.astype(complex) if np.iscomplexobj(arr) else arr.astype(float)
    symmetric = np.array_equal(arr, arr.conj().T)
    vals, vecs = np.linalg.eigh(arr) if symmetric else np.linalg.eig(arr)
    vals = vals.astype(complex)
    tol = _EIG_TOLERANCE * (np.abs(vals).max() if vals.size else 0.0)
    vals.imag[np.abs(vals.imag) <= tol] = 0.0
    order = _order(list(vals))
    vals, vecs = vals[order], vecs[:, order]
    if want_vectors and not symmetric and vecs.shape[0]:
        s = np.linalg.svd(vecs, compute_uv=False)
        if s[-1] <= _DEFECT_TOLERANCE * s[0]:
            raise StatementError("Matrix is defective: not enough independent eigenvectors")
    start = 0
    while start < len(vals):
        end = start + 1
        while end < len(vals) and abs(vals[end] - vals[start]) <= tol:
            end += 1
        if end - start > 1:
            vals[start:end] = vals[start:end].mean()
            if want_vectors and not symmetric:
                vecs[:, start:end] = np.linalg.qr(vecs[:, start:end])[0]
        start = end
    return vals, (_fix_vectors(vecs) if want_vectors else None)


def _real_if_possible(arr):
    import numpy as np

    return arr.real if not np.any(arr.imag) else arr


def _float_number(x):
    x = complex(x)
    if x.imag == 0:
        return sp.Float(x.real + 0.0)
    imag = sp.I * sp.Float(x.imag)
    return imag if x.real == 0 else sp.Float(x.real) + imag


def _float_matrix(arr) -> LMat:
    arr = _real_if_possible(arr)
    return wrap(arr.shape[0], arr.shape[1], [_float_number(x) for x in arr.flatten()])


def _exact_sort_key(vals) -> list[int]:
    if all(v.is_number for v in vals):
        nums = [complex(sp.N(v, 30)) for v in vals]
        return _order(nums)
    return sorted(range(len(vals)), key=lambda i: sp.default_sort_key(vals[i]))


def _closed_form_or_fail(*items) -> None:
    if any(isinstance(x, sp.Basic) and x.has(sp.CRootOf) for x in items):
        raise StatementError(_NO_CLOSED_FORM)


def _exact_eigenvalues(m) -> list:
    _check_symbolic_size(m)
    try:
        table = _DENSE(m).eigenvals()
    except (NotImplementedError, sp.PolynomialError, ValueError):
        raise StatementError(_NO_CLOSED_FORM) from None
    vals = [v for v, k in table.items() for _ in range(k)]
    _closed_form_or_fail(*vals)
    if len(vals) != m.rows:
        raise StatementError(_NO_CLOSED_FORM)
    return [vals[i] for i in _exact_sort_key(vals)]


def _exact_eigenvectors(m):
    _check_symbolic_size(m)
    try:
        triples = _DENSE(m).eigenvects()
    except (NotImplementedError, sp.PolynomialError, ValueError):
        raise StatementError(_NO_CLOSED_FORM) from None
    values, columns = [], []
    for val, mult, vecs in triples:
        _closed_form_or_fail(val, *vecs)
        if len(vecs) < mult:
            raise StatementError("Matrix is defective: not enough independent eigenvectors")
        basis = sp.GramSchmidt([sp.Matrix(v) for v in vecs], True)
        for v in basis:
            values.append(val)
            columns.append(_exact_sign([sp.simplify(e) for e in v]))
    if len(values) != m.rows:
        raise StatementError(_NO_CLOSED_FORM)
    order = _exact_sort_key(values)
    cols = [columns[i] for i in order]
    return wrap(m.rows, m.rows, [cols[c][r] for r in range(m.rows) for c in range(m.rows)])


def _exact_sign(col: list) -> list:
    lead = next((e for e in col if e != 0), None)
    if lead is not None and lead.is_extended_negative:
        return [-e for e in col]
    return col


def _eigen_input(name: str, m):
    _need_matrix(name, m)
    _square(m)
    return split_units(m)


def eigenvalues(m):
    mag, dims = _eigen_input("eigenvalues", m)
    if _use_exact(mag):
        vals = _exact_eigenvalues(mag)
        return attach_units(_DENSE(len(vals), 1, vals), dims)
    vals, _ = _eig_numeric(_entries_array(mag, "eigenvalues()"), False)
    return attach_units(_float_matrix(vals.reshape(-1, 1)), dims)


def eigenvectors(m):
    mag, _dims = _eigen_input("eigenvectors", m)
    if _use_exact(mag):
        return _exact_eigenvectors(mag)
    _, vecs = _eig_numeric(_entries_array(mag, "eigenvectors()"), True)
    return _float_matrix(vecs)


def rank(m):
    _need_matrix("rank", m)
    from .units import measure

    # per-entry magnitudes: columns may legitimately carry different units
    mag = _DENSE(m.rows, m.cols, [measure(e).magnitude if _has_unit(e) else e for e in m])
    _check_symbolic_size(mag)
    return sp.Integer(_rank_exact_or_float(mag))


def norm(x):
    if not isinstance(x, sp.MatrixBase):
        return sp.Abs(x)
    mag, dims = split_units(x)
    total = sp.Add(*[sp.Abs(e) ** 2 for e in mag])
    result = sp.sqrt(total)
    return smul(result, unit_of(dims)) if dims else result


def _rank_exact_or_float(mag) -> int:
    arr = _numeric_array(mag)
    if arr is not None and _has_float(mag):
        import numpy as np

        s = np.linalg.svd(arr, compute_uv=False)
        return int((s > _EIG_TOLERANCE * s[0]).sum()) if s.size and s[0] > 0 else 0
    return mag.rank(simplify=True)


def solve_least_squares(a, b):
    _need_matrix("solve_least_squares", a)
    _need_matrix("solve_least_squares", b)
    if a.rows < a.cols:
        raise StatementError("Need at least as many rows as columns")
    if b.rows != a.rows:
        raise StatementError(f"Right-hand side has {b.rows} rows, matrix has {a.rows}")
    ma, da = split_units(a)
    mb, db = split_units(b)
    _check_symbolic_size(ma)
    if _rank_exact_or_float(ma) < ma.cols:
        raise StatementError("Matrix does not have full column rank")
    arr_a, arr_b = _numeric_array(ma), _numeric_array(mb)
    if arr_a is not None and arr_b is not None and (_has_float(ma) or _has_float(mb)):
        import numpy as np

        x = _float_matrix(np.linalg.lstsq(arr_a, arr_b, rcond=None)[0])
    else:
        t = ma.H if any(e.has(sp.I) for e in ma) else ma.T
        x = wrap((t * ma).inv() * (t * mb))
    exps = dict(db)
    for dim, exp in da:
        exps[dim] = exps.get(dim, 0) - exp
    return attach_units(x, tuple(sorted((d, e) for d, e in exps.items() if e != 0)))


MATRIX_BUILTINS = {
    "_mat": make_matrix, "_c": keep_cell, "_row": make_row, "_idx": index, 
    "det": det, "inv": inv, "transpose": transpose, "trace": trace,
    "solve_system": solve_system, "dot": dot, "cross": cross, "hadamard": hadamard,
    "eye": eye, "zeros": zeros, "ones": ones, "diag": diag,
    "nrows": nrows, "ncols": ncols, "len": length,
    "eigenvalues": eigenvalues, "eigenvectors": eigenvectors, "rank": rank, "norm": norm,
    "solve_least_squares": solve_least_squares,
}
