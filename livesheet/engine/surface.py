"""Three-dimensional surface data (spec 031, phase A1): Qt-free.

A ``surface`` spec is a block of text lines (see ``syntax.parse_statement``).  This module turns
the parsed statement plus the current environment into ``SurfaceData``: a grid of heights in
display units, axis limits and ticks, and the count of grid cells that pass the visibility rule.
Projection and drawing are the job of ``gui/surfaceview.py``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import sympy as sp

from .plotting import (NAN, _axis_unit, _limits, _measure_value, _merge_dims, _real,
                       _require_scalar, _to_complex, _unit_of, _label)
from .sampling import split_top as _split_top
from .syntax import StatementError
from .units import UnitError, measure

DEFAULT_POINTS = 25
MAX_POINTS = 100
DEFAULT_VIEW = (40.0, 30.0)
_IDENT_RE = re.compile(r"^[^\W\d]\w*$")
_KEYWORDS = ("over", "across", "show", "draw", "view", "xunit", "yunit", "zunit",
             "xlim", "ylim", "zlim", "title", "xlabel", "ylabel", "zlabel")
_VISIBLE_TOL = 1e-9


@dataclass
class SurfaceData:
    title: str
    x_label: str; y_label: str; z_label: str     # text incl. " [unit]"
    x_unit: str; y_unit: str; z_unit: str        # "" when dimensionless
    xs: list[float]                  # display unit, sample positions, given order
    ys: list[float]
    zs: list[list[float]]            # zs[j][i]: j = across index, i = over index; NaN if undefined
    x_limits: tuple[float, float]; y_limits: tuple[float, float]; z_limits: tuple[float, float]
    x_ticks: list[float]; y_ticks: list[float]; z_ticks: list[float]
    draw: str = "mesh"               # "mesh" | "wire"
    view_az: float = DEFAULT_VIEW[0]
    view_el: float = DEFAULT_VIEW[1]  # degrees
    skipped: int = 0                 # grid points whose height is undefined
    cells_drawn: int = 0             # cells passing the visibility rule


def _read_options(lines: list[tuple[str, str]]) -> dict[str, str]:
    single: dict[str, str] = {}
    shows = 0
    for kw, rest in lines:
        if kw not in _KEYWORDS:
            raise StatementError(f"Unknown 3-D plot option '{kw}'")
        if kw == "show":
            shows += 1
            if shows > 1:
                raise StatementError("surface takes exactly one 'show' line")
        elif kw in single:
            raise StatementError(f"only one '{kw}' line is allowed")
        single[kw] = rest
    for kw, article in (("over", "an"), ("across", "an"), ("show", "a")):
        if kw not in single:
            raise StatementError(f"surface needs {article} '{kw}' line")
    if not single["show"]:
        raise StatementError("show needs an expression")
    return single


# -- horizontal axes -------------------------------------------------------------------------

@dataclass
class _Axis:
    name: str                 # name the sweep value has inside the expression ("" if none)
    text: str                 # default label text
    si: list[float]           # SI magnitudes in given order
    dims: tuple | None        # None while only zeros were seen
    unit_expr: sp.Expr
    sweep: object             # callable(k) -> exact value with units


def _check_defined(value) -> None:
    from .evaluator import _check_defined as check

    check(value)


def _points(engine, env: dict, text: str) -> int:
    msg = f"points must be between 2 and {MAX_POINTS}"
    try:
        value = engine.parse(text, env, keep_units=True)
        _check_defined(value)
        meas = measure(value)
        n = float(meas.magnitude)
    except (TypeError, ValueError):
        raise StatementError(msg) from None
    if meas.dims or n != int(n) or not 2 <= n <= MAX_POINTS:
        raise StatementError(msg)
    return int(n)


def _sampling_axis(engine, env: dict, which: str, parts: list[tuple[str, str]]) -> _Axis:
    words = [w for w, _ in parts[1:]]
    head = parts[0][1]
    if words[:2] != ["from", "to"] or words not in (["from", "to"], ["from", "to", "points"]):
        raise StatementError(f"{which} needs 'NAME from A to B [points N]'")
    if not _IDENT_RE.match(head):
        raise StatementError(f"{which} needs a name before 'from'")
    texts = [t for _, t in parts[1:]]
    if not all(texts):
        raise StatementError(f"{which} needs 'NAME from A to B [points N]'")
    ends = []
    for text in texts[:2]:
        value = engine.parse(text, env, keep_units=True)
        _check_defined(value)
        ends.append(measure(value))
    start, end = ends
    if start.dims != end.dims:
        raise UnitError("Units do not match: sampling limits have different units")
    count = _points(engine, env, texts[2]) if len(texts) > 2 else DEFAULT_POINTS
    a, b = (float(_real(_to_complex(m.magnitude))) for m in (start, end))
    if not (math.isfinite(a) and math.isfinite(b)):
        raise StatementError("Sampling limits must be finite real numbers")
    vals = [a + k * (b - a) / (count - 1) for k in range(count)]
    vals[-1] = b
    unit = _unit_of(start.dims)
    return _Axis(head, head, vals, start.dims, unit,
                 lambda k, vals=vals, unit=unit: sp.Float(vals[k], 17) * unit)


def _vector_axis(which: str, value, text: str) -> _Axis:
    if value.rows != 1 and value.cols != 1:
        raise StatementError(f"{which} needs a vector (one row or one column)")
    if len(value) > MAX_POINTS:
        raise StatementError(f"{which} has more than {MAX_POINTS} values for a 3-D plot")
    mags, dims = [], None
    for elem in value:
        _check_defined(elem)
        mag, d = _measure_value(elem)
        mags.append(mag)
        dims = _merge_dims(dims, d)
    name = text if _IDENT_RE.match(text) else ""
    unit = _unit_of(dims) if dims else sp.Integer(1)
    elems = list(value)
    return _Axis(name, text, [_real(m) for m in mags], dims, unit, lambda k, elems=elems: elems[k])


def _build_axis(engine, env: dict, which: str, text: str) -> _Axis:
    from .evaluator import RangeVar

    parts = _split_top(text, ("from", "to", "points"))
    if len(parts) > 1:
        return _sampling_axis(engine, env, which, parts)
    if _IDENT_RE.match(text) and isinstance(env.get(text), RangeVar):
        rng = env[text]
        if rng.count > MAX_POINTS:
            raise StatementError(f"range has more than {MAX_POINTS} values for a 3-D plot")
        si = [float(rng.start + k * rng.step) for k in range(rng.count)]
        return _Axis(text, text, si, rng.dims or (), rng.unit_expr(), rng.value)
    value = engine.parse(text, env)
    if not isinstance(value, sp.MatrixBase):
        _check_defined(value)
        raise StatementError(f"{which} needs a range variable or a vector")
    return _vector_axis(which, value, text)


# -- heights ---------------------------------------------------------------------------------

def _heights_fast(engine, env: dict, text: str, ax: _Axis, ay: _Axis, sx, sy):
    local = dict(env)
    if ax.name:
        local[ax.name] = sx * ax.unit_expr
    if ay.name:
        local[ay.name] = sy * ay.unit_expr
    value = engine.parse(text, local)
    _require_scalar(value, text)
    _check_defined(value.xreplace({sx: sp.Integer(1), sy: sp.Integer(1)}))
    meas = measure(value)
    dims = None if (not meas.dims and meas.magnitude == 0) else meas.dims
    func = sp.lambdify((sx, sy), meas.magnitude, "mpmath")
    rows = []
    for y in ay.si:
        row = []
        for x in ax.si:
            try:
                row.append(complex(func(x, y)))
            except (ZeroDivisionError, OverflowError, ValueError):
                row.append(complex(NAN, 0.0))
        rows.append(row)
    return rows, dims


def _heights_slow(engine, env: dict, text: str, ax: _Axis, ay: _Axis):
    rows, dims = [], None
    for j in range(len(ay.si)):
        row = []
        for i in range(len(ax.si)):
            local = dict(env)
            if ax.name:
                local[ax.name] = ax.sweep(i)
            if ay.name:
                local[ay.name] = ay.sweep(j)
            value = engine.parse(text, local)
            _require_scalar(value, text)
            _check_defined(value)
            mag, d = _measure_value(value)
            row.append(mag)
            dims = _merge_dims(dims, d)
        rows.append(row)
    return rows, dims


def _heights(engine, env: dict, text: str, ax: _Axis, ay: _Axis):
    sx, sy = sp.Dummy("sx", real=True), sp.Dummy("sy", real=True)
    try:
        return _heights_fast(engine, env, text, ax, ay, sx, sy)
    except Exception:  # noqa: BLE001 - anything unusual: evaluate point by point instead
        return _heights_slow(engine, env, text, ax, ay)


# -- view, cells -----------------------------------------------------------------------------

def _parse_view(text: str) -> tuple[float, float]:
    words = text.split()
    if len(words) != 2:
        raise StatementError("view needs two numbers: azimuth and elevation")
    try:
        az, el = float(words[0]), float(words[1])
    except ValueError:
        raise StatementError("view needs two plain numbers") from None
    if not (math.isfinite(az) and math.isfinite(el)):
        raise StatementError("view needs two plain numbers")
    if not -90.0 <= el <= 90.0:
        raise StatementError("elevation must be between -90 and 90")
    return az, el


def _inside(value: float, limits: tuple[float, float]) -> bool:
    tol = _VISIBLE_TOL * max(1.0, abs(limits[1] - limits[0]))
    return limits[0] - tol <= value <= limits[1] + tol


def visible_cells(xs, ys, zs, xl, yl, zl) -> list[tuple[int, int]]:
    """Grid cells (i, j) whose four heights are finite and whose corners all lie inside the limits.

    Cell (i, j) is the quadrilateral between columns i, i+1 (over) and rows j, j+1 (across).
    """
    ok_x = [_inside(x, xl) for x in xs]
    ok_y = [_inside(y, yl) for y in ys]
    ok_z = [[(not math.isnan(z)) and _inside(z, zl) for z in row] for row in zs]
    cells = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            if (ok_x[i] and ok_x[i + 1] and ok_y[j] and ok_y[j + 1]
                    and ok_z[j][i] and ok_z[j][i + 1] and ok_z[j + 1][i] and ok_z[j + 1][i + 1]):
                cells.append((i, j))
    return cells


def count_cells(xs, ys, zs, xl, yl, zl) -> int:
    return len(visible_cells(xs, ys, zs, xl, yl, zl))


def _numeric_limits(engine, env, name, text, dims, scale, values):
    lo, hi = min(values), max(values)
    return _limits(engine, env, name, text, dims, scale, lo, hi)


def build_surface(st, env: dict, engine) -> SurfaceData:
    """Evaluate a surface statement (``st.plot_lines``) into ``SurfaceData``; raises on any error."""
    opts = _read_options(st.plot_lines)
    draw = opts.get("draw", "mesh")
    if draw not in ("mesh", "wire"):
        raise StatementError("draw must be mesh or wire")
    az, el = _parse_view(opts["view"]) if "view" in opts else DEFAULT_VIEW

    ax = _build_axis(engine, env, "over", opts["over"])
    ay = _build_axis(engine, env, "across", opts["across"])
    if ax.text == ay.text:
        raise StatementError("over and across need different names")
    rows, z_dims = _heights(engine, env, opts["show"], ax, ay)

    x_unit, x_scale, x_dims = _axis_unit(engine, env, "x", opts.get("xunit"), ax.dims)
    y_unit, y_scale, y_dims = _axis_unit(engine, env, "y", opts.get("yunit"), ay.dims)
    z_unit, z_scale, z_dims = _axis_unit(engine, env, "z", opts.get("zunit"), z_dims)
    xs = [v / x_scale for v in ax.si]
    ys = [v / y_scale for v in ay.si]
    zs = [[_real(v) / z_scale for v in row] for row in rows]
    finite = [z for row in zs for z in row if not math.isnan(z)]
    if not finite or any(math.isnan(v) for v in xs + ys):
        raise StatementError("no finite values to plot")
    skipped = sum(1 for row in zs for z in row if math.isnan(z))

    xl, xh, xticks = _numeric_limits(engine, env, "xlim", opts.get("xlim"), x_dims, x_scale, xs)
    yl, yh, yticks = _numeric_limits(engine, env, "ylim", opts.get("ylim"), y_dims, y_scale, ys)
    zl, zh, zticks = _numeric_limits(engine, env, "zlim", opts.get("zlim"), z_dims, z_scale, finite)
    return SurfaceData(
        title=opts.get("title", ""),
        x_label=_label(opts.get("xlabel", ax.text), x_unit),
        y_label=_label(opts.get("ylabel", ay.text), y_unit),
        z_label=_label(opts.get("zlabel", opts["show"]), z_unit),
        x_unit=x_unit, y_unit=y_unit, z_unit=z_unit,
        xs=xs, ys=ys, zs=zs,
        x_limits=(xl, xh), y_limits=(yl, yh), z_limits=(zl, zh),
        x_ticks=xticks, y_ticks=yticks, z_ticks=zticks,
        draw=draw, view_az=az, view_el=el, skipped=skipped,
        cells_drawn=count_cells(xs, ys, zs, (xl, xh), (yl, yh), (zl, zh)),
    )
