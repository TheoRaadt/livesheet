"""Two-dimensional plot data (spec 004, phase A1): Qt-free.

A plot spec is a block of text lines (see ``syntax.parse_statement``).  This module turns the
parsed statement plus the current environment into ``PlotData``: numbers in display units,
axis limits and ticks.  Drawing is the job of the GUI.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import sympy as sp

from .syntax import StatementError, parse_sampling_clause
from .syntax import split_top_words as _split_top
from .units import Measured, UnitError, dims_to_text, measure

DEFAULT_POINTS = 101
MAX_POINTS = 10000
MAX_TRACES = 20
_TOL = 1e-9
_KEYWORDS = ("over", "show", "xunit", "yunit", "xlim", "ylim", "title", "xlabel", "ylabel")
_IDENT_RE = re.compile(r"^[^\W\d]\w*$")
NAN = float("nan")


@dataclass
class PlotTrace:
    label: str                 # expression text
    x: list[float]             # display unit, NaN for undefined
    y: list[float]
    style_index: int           # 0-based trace number, renderer maps to colour


@dataclass
class PlotData:
    title: str
    x_label: str               # text incl. " [unit]"
    y_label: str
    x_unit: str                # "" when dimensionless
    y_unit: str
    traces: list[PlotTrace]
    x_limits: tuple[float, float]
    y_limits: tuple[float, float]
    x_ticks: list[float]
    y_ticks: list[float]
    skipped: int = 0           # points not drawn


# -- nice axis -----------------------------------------------------------------------------

def _round12(value: float) -> float:
    return float(f"{value:.12g}") + 0.0


def _snap(q: float, up: bool) -> int:
    """Integer floor (or ceil) of ``q``; a quotient within 1e-9 of an integer is that integer."""
    near = round(q)
    if abs(q - near) < _TOL:
        return int(near)
    return math.ceil(q) if up else math.floor(q)


def _step_for(span: float) -> float:
    """Smallest 1/2/5 times a power of ten with ``span/step <= 8``."""
    exponent = math.floor(math.log10(span / 8)) - 1
    while True:
        for mult in (1, 2, 5):
            step = float(f"{mult}e{exponent}")
            if span / step <= 8 * (1 + _TOL):
                return step
        exponent += 1


def _widen(lo: float, hi: float) -> tuple[float, float]:
    if lo != hi:
        return lo, hi
    d = 0.1 * abs(lo) if lo != 0 else 1.0
    return lo - d, hi + d


def _ticks(lo: float, hi: float, step: float) -> list[float]:
    first = math.ceil(lo / step - _TOL)
    last = math.floor(hi / step + _TOL)
    return [_round12(k * step) for k in range(first, last + 1)]


def nice_axis(lo: float, hi: float, manual_lo: float | None = None,
              manual_hi: float | None = None) -> tuple[float, float, list[float]]:
    """Axis limits and ticks for data in ``[lo, hi]``; a manual side is kept as given."""
    if manual_lo is not None and manual_hi is not None:
        if not manual_lo < manual_hi:
            raise ValueError("lower limit must be below upper limit")
        return manual_lo, manual_hi, _ticks(manual_lo, manual_hi, _step_for(manual_hi - manual_lo))
    lo, hi = _widen(lo, hi)
    if manual_lo is None and manual_hi is None:
        step = _step_for(hi - lo)
        a, b = _round12(_snap(lo / step, False) * step), _round12(_snap(hi / step, True) * step)
        return a, b, _ticks(a, b, step)
    # one side automatic: the step comes from the span between the data side and the given side
    given = manual_lo if manual_lo is not None else manual_hi
    other = lo if manual_lo is not None else hi
    span = abs(given - other)
    if span == 0:
        span = 0.2 * abs(given) if given != 0 else 2.0
    step = _step_for(span)
    if manual_lo is not None:
        a, b = manual_lo, _round12(_snap(hi / step, True) * step)
    else:
        a, b = _round12(_snap(lo / step, False) * step), manual_hi
    if not a < b:  # data lies beyond the given side: fall back to a window around it
        a, b = (given, given + abs(span)) if manual_lo is not None else (given - abs(span), given)
    return a, b, _ticks(a, b, _step_for(b - a))


# -- builder -------------------------------------------------------------------------------

@dataclass
class _Axis:
    """Values of one axis in SI magnitudes; ``dims`` is None while only zeros were seen."""

    values: list[complex]
    dims: tuple | None


@dataclass
class _Options:
    over: str = ""
    shows: list[str] = field(default_factory=list)
    single: dict[str, str] = field(default_factory=dict)


def _read_options(lines: list[tuple[str, str]]) -> _Options:
    opts = _Options()
    for kw, rest in lines:
        if kw not in _KEYWORDS:
            raise StatementError(f"Unknown plot option '{kw}'")
        if kw == "show":
            opts.shows.append(rest)
        elif kw in opts.single or (kw == "over" and opts.over):
            raise StatementError(f"only one '{kw}' line is allowed")
        elif kw == "over":
            opts.over = rest
            opts.single["over"] = rest
        else:
            opts.single[kw] = rest
    if "over" not in opts.single:
        raise StatementError("plot needs an 'over' line")
    if not opts.shows:
        raise StatementError("plot needs at least one 'show' line")
    if len(opts.shows) > MAX_TRACES:
        raise StatementError(f"too many traces (max {MAX_TRACES})")
    if any(not s for s in opts.shows):
        raise StatementError("show needs an expression")
    return opts


def _real(value: complex) -> float:
    """Real value of a complex number; NaN when not finite or genuinely complex."""
    if math.isnan(value.real) or math.isnan(value.imag):
        return NAN
    if abs(value.imag) > 1e-12 * max(1.0, abs(value.real)):
        return NAN
    return value.real if math.isfinite(value.real) else NAN


def _to_complex(magnitude) -> complex:
    try:
        return complex(sp.N(magnitude))
    except (TypeError, ValueError, OverflowError):
        return complex(NAN, 0.0)


def _merge_dims(current: tuple | None, new: tuple | None) -> tuple | None:
    if new is None:
        return current
    if current is not None and current != new:
        raise UnitError("Units do not match: values have different units")
    return new


def _measure_value(value) -> tuple[complex, tuple | None]:
    """SI magnitude and dimension of a scalar; a unitless zero fits any dimension."""
    meas = measure(value)
    mag = _to_complex(meas.magnitude)
    if not meas.dims and mag == 0:
        return mag, None
    return mag, meas.dims


def _require_scalar(value, text: str) -> None:
    if isinstance(value, sp.MatrixBase):
        raise StatementError(f"show '{text}' needs a single value")
    if not isinstance(value, sp.Expr) or isinstance(value, sp.Lambda):
        raise StatementError(f"show '{text}' needs a numeric expression")


class _Builder:
    def __init__(self, engine, env: dict, opts: _Options):
        self.engine = engine
        self.env = env
        self.opts = opts
        self.x_name = ""         # name the sweep variable has inside the expressions
        self.x_text = ""
        self.sweep = None        # callable(k) -> exact value, or None in vector mode
        self.sym = sp.Dummy("sweep", real=True)
        self.unit_expr: sp.Expr = sp.Integer(1)
        self.x_si: list[float] = []

    # -- x side ---

    def prepare_x(self) -> _Axis:
        from .evaluator import RangeVar, _check_defined

        text = self.opts.over
        parts = _split_top(text, ("from", "to", "points"))
        if len(parts) > 1:
            return self._sampling(text)
        if _IDENT_RE.match(text) and isinstance(self.env.get(text), RangeVar):
            rng = self.env[text]
            self.x_name, self.x_text = text, text
            self.unit_expr = rng.unit_expr()
            self.sweep = rng.value
            self.x_si = [float(rng.start + k * rng.step) for k in range(rng.count)]
            return _Axis([complex(v) for v in self.x_si], rng.dims or ())
        value = self.engine.parse(text, self.env)
        if not isinstance(value, sp.MatrixBase):
            _check_defined(value)
            raise StatementError("over needs a range variable or a vector")
        return self._vector_axis(value, text)

    def _vector_axis(self, value, text: str) -> _Axis:
        from .evaluator import _check_defined

        if value.rows != 1 and value.cols != 1:
            raise StatementError("over needs a vector (one row or one column)")
        values, dims = [], None
        for elem in value:
            _check_defined(elem)
            mag, d = _measure_value(elem)
            values.append(mag)
            dims = _merge_dims(dims, d)
        self.x_text = text
        self.x_si = [_real(v) for v in values]
        return _Axis(values, dims)

    def _sampling(self, text: str) -> _Axis:
        head, a_text, b_text, n_text = parse_sampling_clause(text)
        start = self._measure_keep(a_text)
        end = self._measure_keep(b_text)
        if start.dims != end.dims:
            raise UnitError("Units do not match: sampling limits have different units")
        count = self._point_count(n_text) if n_text else DEFAULT_POINTS
        a, b = (float(_real(_to_complex(m.magnitude))) for m in (start, end))
        if not (math.isfinite(a) and math.isfinite(b)):
            raise StatementError("Sampling limits must be finite real numbers")
        xs = [a + k * (b - a) / (count - 1) for k in range(count)]
        xs[-1] = b
        self.x_name, self.x_text = head, head
        self.unit_expr = _unit_of(start.dims)
        self.sweep = lambda k, xs=xs: sp.Float(xs[k], 17) * self.unit_expr
        self.x_si = xs
        return _Axis([complex(v) for v in xs], start.dims)

    def _measure_keep(self, text: str) -> Measured:
        from .evaluator import _check_defined

        value = self.engine.parse(text, self.env, keep_units=True)
        _check_defined(value)
        return measure(value)

    def _point_count(self, text: str) -> int:
        try:
            meas = self._measure_keep(text)
            n = float(meas.magnitude)
        except (TypeError, ValueError):
            raise StatementError("points must be between 2 and 10000") from None
        if meas.dims or n != int(n) or not 2 <= n <= MAX_POINTS:
            raise StatementError(f"points must be between 2 and {MAX_POINTS}")
        return int(n)

    # -- y side ---

    def trace(self, text: str) -> _Axis:
        if self.sweep is None:
            return self._vector_trace(text)
        local = dict(self.env)
        local[self.x_name] = self.sym * self.unit_expr
        value = self.engine.parse(text, local)
        _require_scalar(value, text)
        self._check_defined(value)
        try:
            return self._fast(value)
        except Exception:  # noqa: BLE001 - anything unusual: evaluate point by point instead
            return self._slow(text)

    def _check_defined(self, value) -> None:
        from .evaluator import _check_defined

        _check_defined(value.xreplace({self.sym: sp.Integer(1)}))

    def _fast(self, value) -> _Axis:
        meas = measure(value)
        factor = meas.magnitude
        dims: tuple | None = meas.dims
        if not dims and factor == 0:
            dims = None
        func = sp.lambdify(self.sym, factor, "mpmath")
        out = []
        for x in self.x_si:
            try:
                out.append(complex(func(x)))
            except (ZeroDivisionError, OverflowError, ValueError):
                out.append(complex(NAN, 0.0))
        return _Axis(out, dims)

    def _slow(self, text: str) -> _Axis:
        values, dims = [], None
        for k in range(len(self.x_si)):
            local = dict(self.env)
            local[self.x_name] = self.sweep(k)
            value = self.engine.parse(text, local)
            _require_scalar(value, text)
            from .evaluator import _check_defined

            _check_defined(value)
            mag, d = _measure_value(value)
            values.append(mag)
            dims = _merge_dims(dims, d)
        return _Axis(values, dims)

    def _vector_trace(self, text: str) -> _Axis:
        from .evaluator import _check_defined

        value = self.engine.parse(text, self.env)
        if not isinstance(value, sp.MatrixBase):
            raise StatementError(f"show '{text}' needs a vector")
        if value.rows != 1 and value.cols != 1:
            raise StatementError(f"show '{text}' needs a vector (one row or one column)")
        if len(value) != len(self.x_si):
            raise StatementError(f"show '{text}' must have the same length as over {self.x_text}")
        values, dims = [], None
        for elem in value:
            _check_defined(elem)
            mag, d = _measure_value(elem)
            values.append(mag)
            dims = _merge_dims(dims, d)
        return _Axis(values, dims)


def _unit_of(dims: tuple) -> sp.Expr:
    from .units import BASE_UNIT_BY_DIM

    expr: sp.Expr = sp.Integer(1)
    for dim, exp in dims:
        expr = expr * BASE_UNIT_BY_DIM[dim] ** exp
    return expr


def _axis_unit(engine, env: dict, axis: str, unit_text: str | None, dims: tuple | None) -> tuple[str, float, tuple]:
    """Display unit text, SI-to-display divisor and final dims of one axis."""
    from .evaluator import _check_defined, _unit_label

    if not unit_text:
        if unit_text == "":
            raise StatementError(f"{axis}unit needs a unit")
        return dims_to_text(dims or ()), 1.0, dims or ()
    if dims == ():
        raise StatementError(f"{axis}unit given but {axis} has no unit")
    if dims is None:  # only zeros seen: the unit decides the dimension
        target = measure(engine.parse(unit_text, env))
        dims = target.dims
    ratio = float(engine._in_unit(Measured(sp.Integer(1), dims), unit_text, env))
    if not dims:
        raise StatementError(f"{axis}unit given but {axis} has no unit")
    return _unit_label(unit_text), 1.0 / ratio, dims


def _limit(engine, env: dict, text: str, dims: tuple | None, scale: float) -> float | None:
    from .evaluator import _check_defined

    if text.strip() == "auto":
        return None
    value = engine.parse(text, env, keep_units=True)
    _check_defined(value)
    meas = measure(value)
    mag = _real(_to_complex(meas.magnitude))
    if math.isnan(mag):
        raise StatementError("Axis limits must be finite real numbers")
    if mag == 0 and not meas.dims:
        return 0.0
    if dims is not None and meas.dims != dims:
        raise UnitError("Units do not match: limit is "
                        f"{dims_to_text(meas.dims) or 'dimensionless'}")
    return mag / scale


def _limits(engine, env: dict, name: str, text: str | None, dims, scale, lo: float, hi: float):
    if text is None:
        return nice_axis(lo, hi)
    parts = _split_top(text, ("to",))
    if len(parts) != 2 or not parts[0][1] or not parts[1][1]:
        raise StatementError(f"{name} needs 'LO to HI'")
    a = _limit(engine, env, parts[0][1], dims, scale)
    b = _limit(engine, env, parts[1][1], dims, scale)
    if a is not None and b is not None and not a < b:
        raise StatementError("lower limit must be below upper limit")
    try:
        return nice_axis(lo, hi, a, b)
    except ValueError as exc:
        raise StatementError(str(exc)) from None


def _label(text: str, unit: str) -> str:
    return f"{text} [{unit}]".strip() if unit else text


def build_plot(st, env: dict, engine) -> PlotData:
    """Evaluate a plot statement (``st.plot_lines``) into ``PlotData``; raises on any error."""
    opts = _read_options(st.plot_lines)
    builder = _Builder(engine, env, opts)
    x_axis = builder.prepare_x()
    traces = [builder.trace(text) for text in opts.shows]

    y_dims: tuple | None = None
    for t in traces:
        if t.dims is not None and y_dims is not None and t.dims != y_dims:
            raise UnitError("Units do not match: traces have different units")
        y_dims = _merge_dims(y_dims, t.dims)

    x_unit, x_scale, x_dims = _axis_unit(engine, env, "x", opts.single.get("xunit"), x_axis.dims)
    y_unit, y_scale, y_dims = _axis_unit(engine, env, "y", opts.single.get("yunit"), y_dims)
    xs = [_real(v) / x_scale for v in x_axis.values]

    plot_traces, skipped = [], 0
    drawn_x: list[float] = []
    drawn_y: list[float] = []
    for i, (text, t) in enumerate(zip(opts.shows, traces)):
        ys = [_real(v) / y_scale for v in t.values]
        for x, y in zip(xs, ys):
            if math.isnan(x) or math.isnan(y):
                skipped += 1
            else:
                drawn_x.append(x)
                drawn_y.append(y)
        plot_traces.append(PlotTrace(text, list(xs), ys, i))
    if not drawn_x:
        raise StatementError("no finite values to plot")

    xl, xh, xticks = _limits(engine, env, "xlim", opts.single.get("xlim"), x_dims, x_scale,
                             min(drawn_x), max(drawn_x))
    yl, yh, yticks = _limits(engine, env, "ylim", opts.single.get("ylim"), y_dims, y_scale,
                             min(drawn_y), max(drawn_y))
    x_text = opts.single.get("xlabel", builder.x_text)
    y_text = opts.single.get("ylabel", opts.shows[0] if len(opts.shows) == 1 else "")
    return PlotData(
        title=opts.single.get("title", ""),
        x_label=_label(x_text, x_unit), y_label=_label(y_text, y_unit),
        x_unit=x_unit, y_unit=y_unit, traces=plot_traces,
        x_limits=(xl, xh), y_limits=(yl, yh), x_ticks=xticks, y_ticks=yticks,
        skipped=skipped,
    )
