"""Worksheet evaluation: run statements top-to-bottom with a shared namespace."""

from __future__ import annotations

import tokenize
from dataclasses import dataclass, field
from typing import Hashable, Iterable

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

import math
import re

from .plotting import PlotData, build_plot
from .formatting import format_expr, format_number, format_value
from . import matrices, solver
from .matrices import MATRIX_BUILTINS, rewrite_brackets, wrap
from .syntax import Statement, StatementError, parse_statement
from .units import BASE_UNIT_BY_DIM, UNITS, Measured, UnitError, dims_to_text, measure

TRANSFORMS = standard_transformations + (implicit_multiplication, convert_xor)


def _log(x, base=10):
    """Mathcad convention: log is base 10, ln is natural."""
    return sp.log(x, base)


def _builtins() -> dict:
    g: dict = {}
    exec("from sympy import Integer, Float, Rational, Symbol, Function", g)  # noqa: S102 - needed by parse_expr
    g.update({
        # elementary
        "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
        "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "atan2": sp.atan2,
        "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
        "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
        "exp": sp.exp, "ln": sp.log, "log": _log, "log10": lambda x: sp.log(x, 10),
        "sqrt": sp.sqrt, "root": sp.root, "abs": sp.Abs, "sign": sp.sign,
        "floor": sp.floor, "ceil": sp.ceiling, "mod": sp.Mod,
        "Max": sp.Max, "Min": sp.Min, "max": sp.Max, "min": sp.Min,
        "factorial": sp.factorial, "binomial": sp.binomial, "Gamma": sp.gamma,
        "re": sp.re, "im": sp.im, "conj": sp.conjugate, "arg": sp.arg,
        # calculus / CAS
        "diff": sp.diff, "integrate": sp.integrate, "limit": sp.limit,
        "sum": sp.summation, "product": sp.product, "series": sp.series,
        "solve": sp.solve, "expand": sp.expand, "factor": sp.factor,
        "simplify": sp.simplify, "Eq": sp.Eq,
        # constants
        "pi": sp.pi, "e": sp.E, "I": sp.I, "oo": sp.oo, "inf": sp.oo,
    })
    for name, fn in list(g.items()):
        if callable(fn) and name not in _UNWRAPPED:
            g[name] = _scalar_only(name, fn)
    g.update(MATRIX_BUILTINS)
    return g


_ENTRYWISE_KEYWORDS = {"simplify", "expand", "factor", "together", "float", "substitute"}
_SCALAR_KEYWORDS = {"solve", "collect", "series", "partfrac", "apart", "diff", "integrate", "limit"}
_UNWRAPPED = {"Integer", "Float", "Rational", "Symbol", "Function"}


def _scalar_only(name: str, fn):
    """Scalar function that gives a worksheet error when handed a matrix."""
    def wrapper(*args, **kwargs):
        if any(isinstance(a, sp.MatrixBase) for a in args):
            raise StatementError(f"{name}() does not accept a matrix")
        return fn(*args, **kwargs)

    wrapper.__name__ = name
    return wrapper


BUILTINS = _builtins()

_TAG_RE = re.compile(r"\s+in\s+([^\W\d]\w*)\s*$")
MAX_SHOWN = 10  # larger matrices print as a placeholder
MAX_RANGE_VALUES = 10000
_COUNT_TOLERANCE = 1e-9
_IDENT_FIND_RE = re.compile(r"(?<![\w.])[^\W\d]\w*")
_NUMBER_RE = re.compile(r"(?<![\w.])(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass
class RangeVar:
    """Evenly spaced values ``start + k*step`` (SI magnitudes) with a common dimension."""

    start: sp.Expr
    step: sp.Expr
    count: int
    dims: tuple

    def unit_expr(self) -> sp.Expr:
        expr = sp.Integer(1)
        for dim, exp in self.dims:
            expr = expr * BASE_UNIT_BY_DIM[dim] ** exp
        return expr

    def value(self, k: int) -> sp.Expr:
        return (self.start + k * self.step) * self.unit_expr()


@dataclass
class RegionResult:
    status: str             # ok | error | empty
    output: str = ""        # text shown next to the input, e.g. "= 12.5 m/s"
    error: str = ""
    defines: str = ""       # name defined by this region, if any
    columns: list[str] = field(default_factory=list)       # table header (table statements)
    rows: list[list[str]] = field(default_factory=list)    # table cells, one list per row
    grid: list[list[str]] = field(default_factory=list)    # matrix result cells (not set for placeholders)
    grid_unit: str = ""     # unit text printed after a matrix grid
    plot: PlotData | None = None   # plot statements: chart data


class Engine:
    """Evaluates worksheet regions in reading order."""

    def __init__(self, significant: int = 6):
        self.significant = significant
        self._grid: tuple[list[list[str]], str] | None = None  # cells of the last matrix result

    # -- parsing -------------------------------------------------------------

    def parse(self, text: str, env: dict, keep_units: bool = False) -> sp.Expr:
        text = text.strip()
        if not text:
            raise StatementError("Empty expression")
        for name in _IDENT_FIND_RE.findall(text):
            if isinstance(env.get(name), RangeVar):
                raise StatementError(f"{name} is a range variable (use table)")
        text = rewrite_brackets(text)
        if keep_units:  # unevaluated tree, so that e.g. ``0 s`` keeps its unit
            return self._parse_unevaluated(text, env)
        if text.count("==") == 1:
            lhs, rhs = text.split("==")
            left, right = self.parse(lhs, env), self.parse(rhs, env)
            if isinstance(left, sp.MatrixBase) or isinstance(right, sp.MatrixBase):
                raise StatementError("Cannot compare matrices with ==")
            return sp.Eq(left, right)
        local = dict(env)
        matrices.CONTEXT.append((self, local))
        try:
            return parse_expr(text, local_dict=local, global_dict=dict(BUILTINS),
                              transformations=TRANSFORMS, evaluate=True)
        except (SyntaxError, tokenize.TokenError, sp.SympifyError):
            raise StatementError("Syntax error") from None
        except TypeError as exc:
            raise StatementError(_call_error_text(exc, text, local)) from None
        finally:
            matrices.CONTEXT.pop()

    def _parse_unevaluated(self, text: str, env: dict) -> sp.Expr:
        glob = dict(BUILTINS)
        glob.update(Mul=sp.Mul, Add=sp.Add, Pow=sp.Pow)
        try:
            return parse_expr(text, local_dict=dict(env), global_dict=glob,
                              transformations=TRANSFORMS, evaluate=False)
        except (SyntaxError, tokenize.TokenError, sp.SympifyError):
            raise StatementError("Syntax error") from None
        except TypeError as exc:
            raise StatementError(_type_error_text(exc)) from None

    # -- evaluation ----------------------------------------------------------

    def evaluate(self, regions: Iterable[tuple[Hashable, str]]) -> dict[Hashable, RegionResult]:
        """Evaluate ``(key, source)`` pairs given in reading order."""
        regions = list(regions)
        results: dict[Hashable, RegionResult] = {}
        statements: dict[Hashable, Statement] = {}

        broken_models: dict[str, int] = {}   # model name -> regions that failed to parse
        for key, source in regions:
            try:
                statements[key] = parse_statement(source)
            except StatementError as exc:
                results[key] = RegionResult("error", error=str(exc))
                tag = _TAG_RE.search(source)
                if tag:
                    broken_models[tag.group(1)] = broken_models.get(tag.group(1), 0) + 1

        # Pass 1: global definitions, in reading order, visible to every region.
        env: dict = dict(UNITS)
        for key, _ in regions:
            st = statements.get(key)
            if st is not None and _is_global(st):
                results[key] = self._run(st, env)

        # Pass 2: everything else, in reading order.
        last_result: dict[str, int] = {}     # model name -> position of its last result region
        for pos, (key, _) in enumerate(regions):
            st = statements.get(key)
            if st is not None and st.kind == "model_result":
                last_result[st.model] = pos
        earlier: dict[str, list[Statement]] = {}
        for pos, (key, _) in enumerate(regions):
            st = statements.get(key)
            if st is None or _is_global(st):
                continue
            if st.kind.startswith("model_"):
                results[key] = self._run_model(st, pos, key, env, earlier, last_result, broken_models, results)
                continue
            results[key] = self._run(st, env)
        return results

    def _run_model(self, st: Statement, pos: int, key, env: dict, earlier: dict, last_result: dict,
                   broken: dict, results: dict) -> RegionResult:
        try:
            if st.kind != "model_result":
                if last_result.get(st.model, -1) <= pos:
                    raise StatementError(f'No result region for model "{st.model}" below this region')
                earlier.setdefault(st.model, []).append((key, st))
                if st.kind == "model_require":
                    try:
                        for rel in st.relations:
                            for side in re.split(r"==|<=|>=|<|>", rel):
                                self.parse(side, env)
                    except StatementError:
                        broken[st.model] = broken.get(st.model, 0) + 1
                        raise
                if st.kind == "model_setting":
                    solver.check_setting(self, st, env)
                return RegionResult("ok")
            if broken.get(st.model):
                raise StatementError(f'Fix the errors in the regions of model "{st.model}" first')
            members = earlier.get(st.model, [])
            if not members:
                raise StatementError(f'No unknowns declared for model "{st.model}"')
            keys, regions = [k for k, _ in members], [m for _, m in members]
            try:
                solution = solver.settle(self, st.model, regions, env, st if st.goal != "root" else None)
            except solver.SolveError as exc:
                self._mark(results, keys, regions, "✗", exc.owner)
                raise
            self._mark(results, keys, regions, "✓", None)
            return RegionResult("ok", self._solution_text(solution, env))
        except (StatementError, UnitError) as exc:
            return RegionResult("error", error=str(exc))
        except Exception as exc:  # noqa: BLE001 - surface any solver failure in the region
            msg = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            return RegionResult("error", error=msg[:160])

    @staticmethod
    def _mark(results: dict, keys: list, regions: list, mark: str, only: int | None) -> None:
        """Constraint status marks: ``✓`` on all constraint regions, or ``✗`` on the worst one."""
        for i, (key, st) in enumerate(zip(keys, regions)):
            if st.kind == "model_require" and key in results and results[key].status == "ok":
                if only is None:
                    results[key].output = mark
                elif i == only:
                    results[key].output = mark

    def _solution_text(self, solution, env: dict) -> str:
        parts = []
        for u, value in zip(solution.unknowns, solution.values):
            parts.append(f"{u.name} = " + self._format_measured(Measured(sp.Float(value), u.dims), "", env))
            env[u.name] = sp.Float(value) * solver._unit_expr(u.dims)
        text = "⇒ " + ", ".join(parts)
        if solution.objective is not None:
            value, dims = solution.objective
            text += "; value = " + self._format_measured(Measured(sp.Float(value), dims), "", env)
        return text

    def _run(self, st: Statement, env: dict) -> RegionResult:
        self._grid = None
        result = self._run_statement(st, env)
        if self._grid is not None and result.status == "ok":
            result.grid, result.grid_unit = self._grid
        return result

    def _run_statement(self, st: Statement, env: dict) -> RegionResult:
        try:
            if st.kind == "empty":
                return RegionResult("empty")
            if st.kind in ("define", "global"):
                value = self._define(st, env)
                out = ""
                if st.show:
                    out = "= " + self._numeric(value, st.unit, env)
                return RegionResult("ok", out, defines=st.name)
            if st.kind == "range":
                env[st.name] = self._make_range(st, env)
                return RegionResult("ok", defines=st.name)
            if st.kind == "table":
                return self._table(st, env)
            if st.kind == "plot":
                data = build_plot(st, env, self)
                n = len(data.traces)
                return RegionResult("ok", f"plot {n} traces, {len(data.traces[0].x)} points", plot=data)
            if st.kind == "evaluate":
                value = self.parse(st.expr, env)
                return RegionResult("ok", "= " + self._numeric(value, st.unit, env))
            if st.kind == "symbolic":
                return RegionResult("ok", "→ " + self._symbolic(st, env))
            if st.kind == "expression":
                self.parse(st.expr, env)  # validate only
                return RegionResult("ok")
            raise StatementError(f"Unknown statement kind {st.kind}")
        except (StatementError, UnitError) as exc:
            return RegionResult("error", error=str(exc))
        except ZeroDivisionError:
            return RegionResult("error", error="Division by zero")
        except Exception as exc:  # noqa: BLE001 - surface any engine failure in the region
            msg = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            return RegionResult("error", error=msg[:160])

    def _define(self, st: Statement, env: dict):
        if st.params:
            params = [sp.Symbol(p) for p in st.params]
            local = dict(env)
            local.update({p.name: p for p in params})
            body = self.parse(st.expr, local)
            value = sp.Lambda(tuple(params), body)
        else:
            value = self.parse(st.expr, env)
        env[st.name] = value
        return value

    # -- ranges and tables ---------------------------------------------------

    def _make_range(self, st: Statement, env: dict) -> RangeVar:
        start = measure(self.parse(st.expr, env, keep_units=True))
        end = measure(self.parse(st.range_end, env, keep_units=True))
        step = self._range_step(st, start, env)
        for other in (end, step):
            if other.dims != start.dims:
                raise UnitError("Units do not match: start is "
                                f"{dims_to_text(start.dims) or 'dimensionless'}, "
                                f"{dims_to_text(other.dims) or 'dimensionless'} given")
        for meas in (start, end, step):
            _check_defined(meas.magnitude)
        try:
            m0, m1, dm = start.magnitude, end.magnitude, step.magnitude
            if any(x.is_finite is False for x in (m0, m1, dm)):
                raise StatementError("Range limits must be finite numbers")
            if any(x.is_real is False for x in (m0, m1, dm)):
                raise StatementError("Range limits must be real numbers")
            if dm.is_zero:
                raise StatementError("step must not be zero")
            quotient = float((m1 - m0) / dm)
        except (TypeError, OverflowError):
            raise StatementError("Range limits must be real numbers") from None
        if quotient < 0:
            raise StatementError("step has the wrong sign")
        if not math.isfinite(quotient) or quotient >= MAX_RANGE_VALUES:
            count = MAX_RANGE_VALUES + 1 if not math.isfinite(quotient) else math.floor(quotient + _COUNT_TOLERANCE) + 1
        else:
            count = math.floor(quotient + _COUNT_TOLERANCE) + 1
        if count > MAX_RANGE_VALUES:
            raise StatementError(f"too many values (limit {MAX_RANGE_VALUES})")
        return RangeVar(m0, dm, count, start.dims)

    def _range_step(self, st: Statement, start: Measured, env: dict) -> Measured:
        if st.range_step:
            return measure(self.parse(st.range_step, env, keep_units=True))
        # default: 1 in the unit the start was written in (e.g. 0 km -> 1 km)
        numbers = _NUMBER_RE.findall(st.expr)
        rest = st.expr.strip()
        if len(numbers) == 1 and re.match(r"[-+]?\s*" + re.escape(numbers[0]), rest) \
                and not re.search(r"[+-]", rest[len(numbers[0]) + 1:]):
            probe = self.parse(_NUMBER_RE.sub("1", st.expr.lstrip("+-").strip(), count=1), env)
            guess = measure(probe)
            if guess.dims == start.dims:
                return guess
        return Measured(sp.Integer(1), start.dims)

    def _table(self, st: Statement, env: dict) -> RegionResult:
        used = {name for expr, _ in st.columns for name in _IDENT_FIND_RE.findall(expr)
                if isinstance(env.get(name), RangeVar)}
        if not used:
            for expr, _ in st.columns:
                _check_defined(self.parse(expr, env))
            raise StatementError("table needs a range variable in at least one column")
        if len(used) > 1:
            raise StatementError("table can use only one range variable")
        name = next(iter(used))
        rng: RangeVar = env[name]
        probe_dims: dict[int, tuple] = {}
        rows: list[list[str]] = []
        for k in range(rng.count):
            local = dict(env)
            local[name] = rng.value(k)
            rows.append([self._cell(i, expr, unit, local, name, rng, probe_dims)
                         for i, (expr, unit) in enumerate(st.columns)])
        columns = [expr for expr, _ in st.columns]
        label = "row" if len(rows) == 1 else "rows"
        return RegionResult("ok", f"table {len(rows)} {label}", columns=columns, rows=rows)

    def _cell(self, index: int, expr: str, unit: str, local: dict, name: str,
              rng: RangeVar, probe_dims: dict) -> str:
        value = self.parse(expr, local)
        if isinstance(value, sp.Expr) and not isinstance(value, sp.Lambda) and value == 0:
            # a zero result lost its unit while evaluating; recover it from a non-zero probe
            if index not in probe_dims:
                probe_dims[index] = self._probe_dims(expr, local, name, rng)
            if probe_dims[index]:
                return self._format_measured(Measured(sp.Integer(0), probe_dims[index]), unit, local)
        return self._numeric(value, unit, local)

    def _probe_dims(self, expr: str, local: dict, name: str, rng: RangeVar) -> tuple:
        probe = dict(local)
        probe[name] = rng.unit_expr()
        try:
            value = self.parse(expr, probe)
            return measure(value).dims
        except Exception:  # noqa: BLE001 - probe is best effort
            return ()

    def _numeric(self, value, unit_text: str, env: dict) -> str:
        if isinstance(value, sp.Lambda):
            raise StatementError("A function needs arguments to be evaluated")
        if isinstance(value, (bool, sp.logic.boolalg.BooleanAtom)):
            return "true" if bool(value) else "false"
        if isinstance(value, sp.Rel):
            return format_expr(value, self.significant)
        if isinstance(value, (list, tuple)):
            return "{" + ", ".join(self._numeric(v, "", env) for v in value) + "}"
        _check_defined(value)
        if isinstance(value, sp.MatrixBase):
            return self._numeric_matrix(value, unit_text, env)
        return self._format_measured(measure(value), unit_text, env)

    def _numeric_matrix(self, m, unit_text: str, env: dict) -> str:
        if m.rows > MAX_SHOWN or m.cols > MAX_SHOWN:
            return f"[{m.rows}x{m.cols} matrix]"
        measured = [measure(e) for e in m]
        # a zero without a unit fits any dimension; a zero that kept its unit counts
        shared = {x.dims for x in measured if x.magnitude != 0 or x.dims}
        suffix = ""
        if len(shared) <= 1:
            dims = next(iter(shared), ())
            if unit_text:
                target = measure(self.parse(unit_text, env))
                if shared and target.dims != dims:
                    raise UnitError("Units do not match: result is "
                                    f"{dims_to_text(dims) or 'dimensionless'}")
                cells = [format_number(x.magnitude / target.magnitude, self.significant) for x in measured]
                suffix = " " + _unit_label(unit_text)
            else:
                cells = [format_number(x.magnitude, self.significant) for x in measured]
                suffix = " " + dims_to_text(dims) if dims else ""
        else:
            cells = [self._format_measured(x, unit_text, env) for x in measured]
        grid = [cells[r * m.cols:(r + 1) * m.cols] for r in range(m.rows)]
        self._grid = (grid, suffix.strip())
        rows = [", ".join(r) for r in grid]
        return "[" + "; ".join(rows) + "]" + suffix

    def _in_unit(self, meas: Measured, unit_text: str, env: dict) -> sp.Expr:
        """Magnitude of ``meas`` expressed in the unit written as ``unit_text`` (dimensions must match)."""
        unit_val = self.parse(unit_text, env)
        _check_defined(unit_val)
        target = measure(unit_val)
        if target.dims != meas.dims:
            raise UnitError(f"Units do not match: result is {dims_to_text(meas.dims) or 'dimensionless'}")
        return meas.magnitude / target.magnitude

    def _format_measured(self, meas: Measured, unit_text: str, env: dict) -> str:
        if unit_text:
            number = format_number(self._in_unit(meas, unit_text, env), self.significant)
            return f"{number} {_unit_label(unit_text)}"
        number = format_number(meas.magnitude, self.significant)
        unit = dims_to_text(meas.dims)
        return f"{number} {unit}" if unit else number

    def _symbolic(self, st: Statement, env: dict) -> str:
        # Variables named by keywords (solve, x) must stay symbolic.
        free_names = set()
        for words in st.keywords:
            if words[0] in ("solve", "collect", "series", "partfrac", "diff", "integrate", "limit"):
                free_names.update(w.split("=")[0].strip() for w in words[1:2])
        local = {k: v for k, v in env.items() if k not in free_names}
        matrices.EXACT_MODE[0] = True
        try:
            value = self.parse(st.expr, local)
        finally:
            matrices.EXACT_MODE[0] = False
        for words in st.keywords:
            value = self._apply_keyword(value, words, local)
        if isinstance(value, sp.MatrixBase):
            return self._symbolic_matrix(value)
        return format_value(value, self.significant)

    def _symbolic_matrix(self, m) -> str:
        if m.rows > MAX_SHOWN or m.cols > MAX_SHOWN:
            return f"[{m.rows}x{m.cols} matrix]"
        cells = [format_expr(e, self.significant) for e in m]
        grid = [cells[r * m.cols:(r + 1) * m.cols] for r in range(m.rows)]
        self._grid = (grid, "")
        return "[" + "; ".join(", ".join(r) for r in grid) + "]"

    def _apply_keyword(self, value, words: list[str], env: dict):
        kw, args = words[0].lower(), words[1:]
        if isinstance(value, sp.MatrixBase):
            if kw not in _ENTRYWISE_KEYWORDS:
                if kw in _SCALAR_KEYWORDS:
                    raise StatementError(f"'{kw}' does not apply to matrices")
                raise StatementError(f"Unknown keyword '{kw}'")
            return wrap(value.rows, value.cols, [self._apply_keyword(e, words, env) for e in value])

        def sym(i, default=None):
            if len(args) > i:
                return self.parse(args[i], {k: v for k, v in env.items() if k != args[i]})
            if default is not None:
                return default
            free = sorted(getattr(value, "free_symbols", []), key=str)
            if len(free) == 1:
                return free[0]
            raise StatementError(f"'{kw}' needs a variable, e.g. → {kw}, x")

        if kw == "simplify":
            return sp.simplify(value)
        if kw == "expand":
            return sp.expand(value)
        if kw == "factor":
            return sp.factor(value)
        if kw == "together":
            return sp.together(value)
        if kw in ("partfrac", "apart"):
            return sp.apart(value, sym(0))
        if kw == "collect":
            return sp.collect(sp.expand(value), sym(0))
        if kw == "solve":
            var = sym(0)
            sols = sp.solve(value, var)
            if not sols:
                raise StatementError("No solution found")
            return sols[0] if len(sols) == 1 else list(sols)
        if kw == "float":
            digits = int(args[0]) if args else self.significant
            return sp.N(value, digits)
        if kw == "diff":
            return sp.diff(value, sym(0))
        if kw == "integrate":
            return sp.integrate(value, sym(0))
        if kw == "series":
            var = sym(0)
            order = int(args[1]) if len(args) > 1 else 6
            return sp.series(value, var, 0, order).removeO()
        if kw == "substitute":
            if not args or "=" not in args[0]:
                raise StatementError("Use → substitute, x = value")
            out = value
            for a in args:
                name, rhs = a.split("=", 1)
                out = out.subs(sp.Symbol(name.strip()), self.parse(rhs, env))
            return out
        raise StatementError(f"Unknown keyword '{kw}'")


def _is_global(st: Statement) -> bool:
    return st.kind == "global" or (st.kind == "range" and st.is_global)


def _check_defined(value) -> None:
    free = getattr(value, "free_symbols", set())
    undef = sorted({str(s) for s in free} | {f.func.__name__ for f in value.atoms(AppliedUndef)}) \
        if isinstance(value, sp.Basic) else []
    if undef:
        names = ", ".join(undef)
        raise StatementError(f"{names} {'is' if len(undef) == 1 else 'are'} not defined")


def _unit_label(text: str) -> str:
    out = text.strip().replace("**", "^").replace("*", "·")
    for digit, sup in zip("23456789", "²³⁴⁵⁶⁷⁸⁹"):
        out = out.replace("^" + digit, sup)
    return out


_CALL_RE = re.compile(r"(?<![\w.])([^\W\d]\w*)\s*\(")


def _call_error_text(exc: TypeError, text: str, env: dict) -> str:
    """Error text for a failed call; a unit or value used like a function gets a clear name."""
    for name in _CALL_RE.findall(text):
        value = env.get(name)
        if value is not None and not isinstance(value, sp.Lambda) and not callable(value):
            return f"Not a function: {name}"
    return _type_error_text(exc)


def _type_error_text(exc: TypeError) -> str:
    msg = str(exc)
    if "not callable" in msg:
        return "Not a function: " + msg.split("'")[1] if "'" in msg else "Not a function"
    if "positional argument" in msg or "takes" in msg:
        return "Wrong number of arguments"
    return msg
