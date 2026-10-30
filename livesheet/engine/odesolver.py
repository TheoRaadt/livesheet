"""Initial-value ODE solving (spec 010): closed form via SymPy's ``dsolve``, falling back to a
numeric integration via SciPy's ``solve_ivp`` when no closed form is found (or when forced).

Units are handled the same way ``solver.py`` already handles them for spec 003's solve
models: every quantity is converted to a SI magnitude before any symbolic/numeric solving
step, and the appropriate unit factor is re-attached when a solved function is bound. SciPy
is imported lazily so the GUI starts without it.
"""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Note: the timeout guard below spawns a subprocess, so any standalone script that imports
# this module (engine/ has no GUI dependency) must itself be guarded with
# `if __name__ == "__main__":` -- a plain multiprocessing/spawn requirement, not specific to
# this engine. LiveSheet's own entry points already do this correctly.

import sympy as sp
from sympy.core.function import AppliedUndef

from .syntax import Statement, StatementError, parse_ode_equation
from .solver import _unit_expr as unit_expr
from .units import Measured, UnitError, dims_to_text, measure

if TYPE_CHECKING:  # pragma: no cover
    from .evaluator import Engine

DEFAULT_ACCURACY = 1e-6
DEFAULT_STEPS = 10000
DEFAULT_POINTS = 101
MAX_POINTS = 10000
SYMBOLIC_TIMEOUT = 1.0  # seconds; dsolve can run for a very long time on some nonlinear ODEs
                        # (a SymPy limitation, not something this engine can fix) -- treated
                        # the same as "no closed form found". Run on a subprocess (not a
                        # thread) specifically so a timeout can actually *terminate* the
                        # still-running computation instead of leaving it to burn CPU forever.


@dataclass
class Condition:
    source: str
    order: int
    point: Measured
    value: Measured


@dataclass
class FuncInfo:
    name: str
    func: sp.core.function.UndefinedFunction
    order: int
    dims: tuple
    conditions: dict[int, Condition]


@dataclass
class Settings:
    accuracy: float = DEFAULT_ACCURACY
    steps: int = DEFAULT_STEPS


@dataclass
class System:
    model: str
    indep_name: str
    t: sp.Symbol
    t_dims: tuple
    functions: dict[str, FuncInfo]
    equations: dict[str, sp.Eq]   # bare (unit-free) equation, keyed by function name
    point_bare: float
    settings: Settings
    env: dict


@dataclass
class SymbolicOutcome:
    formulas: dict[str, sp.Lambda]


@dataclass
class NumericOutcome:
    t_name: str
    t_bare: list[float]
    t_dims: tuple
    order: list[str]
    values: dict[str, list[float]]
    dims: dict[str, tuple]
    functions: dict[str, sp.Lambda]


# -- settings (same two keywords/validation as solver.py, different defaults) ------------

def read_settings(engine: "Engine", members: list[Statement], env: dict) -> Settings:
    settings = Settings()
    for st in members:
        if st.kind != "model_setting":
            continue
        value = engine.parse(st.expr, env)
        if st.name == "accuracy":
            if not (value.is_number and value.is_real and 0 < value < 1):
                raise StatementError("accuracy must be a positive number below 1")
            settings.accuracy = float(value)
        else:
            if not (value.is_Integer and value >= 1):
                raise StatementError("steps must be a whole number of at least 1")
            settings.steps = int(value)
    return settings


# -- dimension bookkeeping -----------------------------------------------------------------

def _bare_env(env: dict) -> dict:
    """``env`` with every measurable value replaced by its bare SI magnitude."""
    bare = {}
    for key, val in env.items():
        try:
            bare[key] = measure(val).magnitude
        except Exception:  # noqa: BLE001 - not every env value is a plain measured quantity
            bare[key] = val
    return bare


def _dims_combine(a: tuple, b: tuple, scale=1) -> tuple:
    acc = dict(a)
    for name, exp in b:
        acc[name] = acc.get(name, 0) + scale * exp
    return tuple(sorted((n, e) for n, e in acc.items() if e != 0))


def _dims_scale(a: tuple, scale) -> tuple:
    out = [(n, e * scale) for n, e in a]
    return tuple(sorted((n, e) for n, e in out if e != 0))


def _term_vector(term: sp.Expr, func_dims: dict[str, tuple]) -> tuple[tuple, int]:
    """``(concrete_dims, dt_coeff)`` for one additive term, where the term's true dimension
    is ``concrete_dims`` combined with ``dt_coeff`` times the (unknown) independent variable's
    dimension."""
    dt_coeff = 0
    dims_acc: list[tuple] = []
    stripped = term
    for d in list(stripped.atoms(sp.Derivative)):
        name = d.expr.func.__name__
        if name in func_dims:
            order = sum(count for _, count in d.variable_count)
            dims_acc.append(func_dims[name])
            dt_coeff -= order
            stripped = stripped.xreplace({d: sp.Integer(1)})
    for app in list(stripped.atoms(AppliedUndef)):
        name = app.func.__name__
        if name in func_dims:
            dims_acc.append(func_dims[name])
            stripped = stripped.xreplace({app: sp.Integer(1)})
    total = measure(stripped).dims
    for d in dims_acc:
        total = _dims_combine(total, d)
    return total, dt_coeff


def _dims_from_equation(eq: sp.Eq, func_dims: dict[str, tuple], model: str, source: str) -> tuple | None:
    """Independent variable's dimension implied by one equation, or ``None`` if the equation
    gives no constraint on it. Raises ``UnitError`` on a genuine internal inconsistency."""
    terms = sp.Add.make_args(sp.expand(eq.lhs - eq.rhs))
    vectors = [_term_vector(term, func_dims) for term in terms]
    dt: tuple | None = None
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            ci, ki = vectors[i]
            cj, kj = vectors[j]
            if ki == kj:
                if ci != cj:
                    raise UnitError(f'Units do not match in the equation "{source}" of "{model}"')
                continue
            candidate = _dims_scale(_dims_combine(cj, ci, scale=-1), sp.Rational(1, ki - kj))
            if dt is None:
                dt = candidate
            elif dt != candidate:
                raise UnitError(f'Units do not match in the equation "{source}" of "{model}"')
    return dt


def _infer_t_dims(equations: dict[str, tuple[sp.Eq, str]], func_dims: dict[str, tuple], model: str) -> tuple:
    dt: tuple | None = None
    for eq, source in equations.values():
        candidate = _dims_from_equation(eq, func_dims, model, source)
        if candidate is None:
            continue
        if dt is None:
            dt = candidate
        elif dt != candidate:
            raise UnitError(f'Units do not match: equations of "{model}" imply different units '
                            "for the independent variable")
    return dt if dt is not None else ()


# -- building the system -------------------------------------------------------------------

def build(engine: "Engine", model: str, members: list[Statement], env: dict) -> System:
    ode_members = [st for st in members if st.kind == "model_ode"]
    ic_members = [st for st in members if st.kind == "model_ic"]
    if not ode_members:
        raise StatementError(f'No equations declared for ODE system "{model}"')

    indep_name: str | None = None
    orders: dict[str, int] = {}
    equation_text: dict[str, str] = {}
    for st in ode_members:
        fname, vname, order, _, _ = parse_ode_equation(st.expr)
        if indep_name is None:
            indep_name = vname
        elif vname != indep_name:
            raise StatementError(f'All equations of "{model}" must use the same independent variable')
        orders[fname] = max(orders.get(fname, 0), order)
        equation_text[fname] = st.expr
    func_names = set(orders)

    raw_conditions: dict[str, list[Condition]] = {name: [] for name in func_names}
    point_ref: tuple[sp.Expr, tuple] | None = None   # (magnitude, dims) of the first condition's point
    point_dims_known: tuple | None = None            # dims of the first *nonzero* point seen, if any
    for st in ic_members:
        for fname, order, point_text, value_text in st.conditions:
            if fname not in func_names:
                raise StatementError(f'"{fname}" is not an equation of ODE system "{model}"')
            point = measure(engine.parse(point_text, env, keep_units=True))
            value = measure(engine.parse(value_text, env, keep_units=True))
            if point_ref is None:
                point_ref = (point.magnitude, point.dims)
            else:
                same_value = sp.simplify(point.magnitude - point_ref[0]) == 0
                same_dims = point.dims == point_ref[1] or point.magnitude == 0 or point_ref[0] == 0
                if not (same_value and same_dims):
                    raise StatementError(f'All conditions of "{model}" must be given at the same point')
            if point.magnitude != 0 and point_dims_known is None:
                point_dims_known = point.dims
            raw_conditions[fname].append(Condition(f"{fname}" + "'" * order + f"({point_text})", order,
                                                   point, value))

    point_bare = point_ref[0] if point_ref is not None else sp.Integer(0)
    point_dims = point_dims_known if point_dims_known is not None else (
        point_ref[1] if point_ref is not None else ())

    # A duplicate or missing order is reported the same generic way (a count mismatch): the
    # exact set of orders needed is {0, ..., order-1} with one condition each, but any extra
    # or missing condition -- duplicate order included -- just shows up as the wrong count.
    conditions: dict[str, dict[int, Condition]] = {}
    for name in func_names:
        needed = orders[name]
        given = raw_conditions[name]
        by_order = {c.order: c for c in given}
        if len(given) != needed or sorted(by_order) != list(range(needed)):
            raise StatementError(f'"{model}" needs {needed} initial condition(s) for {name}, '
                                 f'has {len(given)}')
        conditions[name] = by_order

    func_dims = {name: conditions[name][0].value.dims for name in func_names}

    indep_symbol = sp.Symbol(indep_name, real=True)
    bare_env = _bare_env(env)
    dimensioned_env = dict(env)
    bare_env[indep_name] = indep_symbol
    dimensioned_env[indep_name] = indep_symbol
    functions: dict[str, sp.core.function.UndefinedFunction] = {}
    for name in func_names:
        functions[name] = sp.Function(name)
        bare_env[name] = functions[name]
        dimensioned_env[name] = functions[name]

    bare_equations: dict[str, sp.Eq] = {}
    dimensioned_equations: dict[str, tuple[sp.Eq, str]] = {}
    for name, text in equation_text.items():
        bare_equations[name] = engine.parse(text, bare_env)
        dimensioned_equations[name] = (engine.parse(text, dimensioned_env), text)

    t_dims = _infer_t_dims(dimensioned_equations, func_dims, model)
    if point_dims and point_dims != t_dims:
        raise UnitError(f'Units do not match: the condition point is '
                        f'{dims_to_text(point_dims) or "dimensionless"}')

    settings = read_settings(engine, members, env)

    func_infos = {
        name: FuncInfo(name, functions[name], orders[name], func_dims[name], conditions[name])
        for name in func_names
    }
    return System(model, indep_name, indep_symbol, t_dims, func_infos, bare_equations, point_bare,
                  settings, env)


# -- symbolic (closed-form) solving ---------------------------------------------------------

def _topo_order(equations: dict[str, sp.Eq], func_names: set[str]) -> list[str] | None:
    """Order functions so each is solved only after every other function its own equation
    references; ``None`` on a genuine cycle (mutual coupling, not supported symbolically)."""
    deps = {}
    for name, eq in equations.items():
        others = {a.func.__name__ for a in (eq.lhs - eq.rhs).atoms(AppliedUndef)} & func_names
        others.discard(name)
        deps[name] = others
    order: list[str] = []
    remaining = set(equations)
    while remaining:
        ready = sorted(f for f in remaining if deps[f] <= set(order))
        if not ready:
            return None
        order.extend(ready)
        remaining -= set(ready)
    return order


def _dsolve_worker(eq: sp.Eq, func_call: sp.Expr, ics: dict, conn) -> None:
    try:
        conn.send(("ok", sp.dsolve(eq, func_call, ics=ics)))
    except Exception as exc:  # noqa: BLE001 - re-raised on the calling side below
        conn.send(("error", exc))
    finally:
        conn.close()


def _mp_context():
    # ``spawn`` (a fresh interpreter), not ``fork``: this module may run inside the PySide6
    # GUI process, and forking a process that already has an open Qt/graphics event loop is a
    # well-known source of hangs and crashes unrelated to this engine's own code; ``spawn`` is
    # slower to start (a few hundred ms) but has none of that risk, on every platform.
    return mp.get_context("spawn")


def _dsolve_timeout(eq: sp.Eq, func_call: sp.Expr, ics: dict, timeout: float = SYMBOLIC_TIMEOUT):
    """``sp.dsolve`` on a subprocess, giving up (returning ``None``) after ``timeout`` seconds:
    some nonlinear ODEs make ``dsolve`` run for a very long time (a SymPy limitation); treated
    the same as "no closed form found". A subprocess (not a thread) is used specifically so a
    timeout can *terminate* the still-running computation -- Python cannot forcibly stop a
    running thread, which would otherwise keep burning CPU in the background indefinitely."""
    ctx = _mp_context()
    parent_conn, child_conn = ctx.Pipe()
    proc = ctx.Process(target=_dsolve_worker, args=(eq, func_call, ics, child_conn), daemon=True)
    proc.start()
    child_conn.close()
    try:
        if not parent_conn.poll(timeout):
            return None
        try:
            status, payload = parent_conn.recv()
        except EOFError:
            return None
        if status == "error":
            if isinstance(payload, NotImplementedError):
                return None
            raise payload
        return payload
    finally:
        parent_conn.close()
        if proc.is_alive():
            proc.terminate()
        proc.join(1.0)


def _extract_formula(result, func, t: sp.Symbol) -> sp.Expr | None:
    if isinstance(result, (list, tuple)):
        if len(result) != 1:
            return None
        result = result[0]
    if not isinstance(result, sp.Eq) or result.lhs != func(t):
        return None
    rhs = result.rhs
    if rhs.atoms(AppliedUndef) or rhs.atoms(sp.Integral) or rhs.has(sp.Derivative):
        return None  # an implicit result counts as "no closed form found"
    return rhs


def _bind(system: System, name: str, bare_formula: sp.Expr) -> sp.Lambda:
    """Bind a bare (SI-magnitude) formula as a unit-aware worksheet function."""
    info = system.functions[name]
    t_unit = unit_expr(system.t_dims)
    f_unit = unit_expr(info.dims)
    bare_t = system.t if t_unit == 1 else system.t / t_unit
    scaled = bare_formula.xreplace({system.t: bare_t})
    return sp.Lambda(system.t, scaled * f_unit)


def solve_symbolic(system: System) -> SymbolicOutcome | None:
    """Closed form via ``dsolve``, one function at a time in dependency order (substituting
    an already-solved function into any later equation that references it); ``None`` when no
    closed form is found, the system is mutually (circularly) coupled, or a result is
    implicit."""
    order = _topo_order(system.equations, set(system.functions))
    if order is None:
        return None
    solved: dict[str, sp.Expr] = {}
    for name in order:
        info = system.functions[name]
        eq = system.equations[name]
        if solved:
            subs_map = {system.functions[other].func(system.t): solved[other] for other in solved}
            eq = eq.xreplace(subs_map)
        ics = {}
        base = info.func(system.t)
        for k, cond in info.conditions.items():
            key = base if k == 0 else sp.Derivative(base, system.t, k)
            ics[key.subs(system.t, system.point_bare)] = cond.value.magnitude
        result = _dsolve_timeout(eq, base, ics)
        if result is None:
            return None
        formula = _extract_formula(result, info.func, system.t)
        if formula is None:
            return None
        solved[name] = formula
    return SymbolicOutcome({name: _bind(system, name, solved[name]) for name in solved})


# -- numeric fallback ------------------------------------------------------------------------

def _state_layout(system: System) -> list[tuple[str, int]]:
    layout = []
    for name in sorted(system.functions):
        for k in range(system.functions[name].order):
            layout.append((name, k))
    return layout


def _build_rhs(system: System, layout: list[tuple[str, int]]):
    index = {p: i for i, p in enumerate(layout)}
    state_symbols = {p: sp.Symbol(f"_z_{p[0]}_{p[1]}", real=True) for p in layout}
    last_funcs = {}
    for name, info in system.functions.items():
        eq = system.equations[name]
        deriv = sp.Derivative(info.func(system.t), system.t, info.order)
        solved = sp.solve(sp.Eq(eq.lhs - eq.rhs, 0), deriv)
        if len(solved) != 1:
            raise StatementError(f'Cannot isolate the highest derivative of "{name}" in "{system.model}"')
        rhs = solved[0]
        subs_map = {}
        for other_name, other_info in system.functions.items():
            base = other_info.func(system.t)
            for k in range(other_info.order):
                node = base if k == 0 else sp.Derivative(base, system.t, k)
                subs_map[node] = state_symbols[(other_name, k)]
        rhs = rhs.xreplace(subs_map)
        args = [system.t] + [state_symbols[p] for p in layout]
        last_funcs[name] = sp.lambdify(args, rhs, modules=["numpy"])

    def rhs_fn(t, y):
        out = [0.0] * len(layout)
        values = list(y)
        for i, (name, k) in enumerate(layout):
            info = system.functions[name]
            if k < info.order - 1:
                out[i] = y[index[(name, k + 1)]]
            else:
                out[i] = float(last_funcs[name](t, *values))
        return out

    return rhs_fn


def _integrate(rhs_fn, t0: float, y0: list[float], t_eval: list[float], accuracy: float,
               steps: int) -> list[list[float]]:
    import numpy as np
    from scipy.integrate import solve_ivp

    t_eval_arr = [float(t) for t in t_eval]
    forward = sorted(t for t in t_eval_arr if t >= t0)
    backward = sorted((t for t in t_eval_arr if t < t0), reverse=True)
    out: dict[float, list[float]] = {}
    for branch in (forward, backward):
        if not branch:
            continue
        t_end = branch[-1]
        if t_end == t0:
            for t in branch:
                out[t] = list(y0)
            continue
        sol = solve_ivp(rhs_fn, (t0, t_end), y0, method="RK45", rtol=accuracy,
                        atol=max(accuracy * 1e-6, 1e-12), dense_output=True)
        if not sol.success:
            raise StatementError(f"Not converged: {sol.message}")
        n_steps = max(0, len(sol.t) - 1)
        if n_steps > steps:
            raise StatementError(f"Not converged: stopped after {n_steps} steps "
                                 f"(steps limit {steps})")
        for t in branch:
            out[t] = [float(v) for v in np.atleast_1d(sol.sol(t))]
    return [out[t] for t in t_eval_arr]


def _piecewise_linear(t: sp.Expr, xs: list[float], ys: list[float]) -> sp.Expr:
    pieces = [(sp.Float(ys[0]), t <= sp.Float(xs[0]))]
    for i in range(1, len(xs)):
        x0, x1 = xs[i - 1], xs[i]
        y0, y1 = ys[i - 1], ys[i]
        if x1 == x0:
            formula = sp.Float(y1)
        else:
            slope = (y1 - y0) / (x1 - x0)
            formula = sp.Float(y0) + sp.Float(slope) * (t - sp.Float(x0))
        pieces.append((formula, t <= sp.Float(x1)))
    pieces.append((sp.Float(ys[-1]), True))
    return sp.Piecewise(*pieces)


def _bind_numeric(system: System, name: str, xs: list[float], ys: list[float]) -> sp.Lambda:
    info = system.functions[name]
    t_unit = unit_expr(system.t_dims)
    f_unit = unit_expr(info.dims)
    bare_t = system.t if t_unit == 1 else system.t / t_unit
    formula = _piecewise_linear(bare_t, xs, ys)
    return sp.Lambda(system.t, formula * f_unit)


def _point_count(engine: "Engine", env: dict, text: str) -> int:
    value = measure(engine.parse(text, env, keep_units=True))
    try:
        n = float(value.magnitude)
    except TypeError:
        raise StatementError(f"points must be between 2 and {MAX_POINTS}") from None
    if value.dims or n != int(n) or not 2 <= n <= MAX_POINTS:
        raise StatementError(f"points must be between 2 and {MAX_POINTS}")
    return int(n)


def solve_numeric(engine: "Engine", system: System, over: Statement | None) -> NumericOutcome:
    """Numeric fallback via ``scipy.integrate.solve_ivp``, reducing any order-N equation to N
    first-order ones internally."""
    if over is None:
        raise StatementError(f'over {system.indep_name} from ... to ... is needed to solve '
                             f'"{system.model}" numerically')
    if over.name != system.indep_name:
        raise StatementError(f'"{over.name}" is not the independent variable of ODE system '
                             f'"{system.model}" (expected "{system.indep_name}")')
    start = measure(engine.parse(over.expr, system.env, keep_units=True))
    end = measure(engine.parse(over.range_end, system.env, keep_units=True))
    if start.dims != end.dims:
        raise UnitError("Units do not match: sampling limits have different units")
    if system.t_dims and start.dims != system.t_dims and start.magnitude != 0:
        raise UnitError(f'Units do not match: "over {over.name}" should be in '
                        f'{dims_to_text(system.t_dims) or "dimensionless"}')
    n_points = _point_count(engine, system.env, over.over_points) if over.over_points else DEFAULT_POINTS
    a, b = float(start.magnitude), float(end.magnitude)
    t_eval = [a + k * (b - a) / (n_points - 1) for k in range(n_points)]
    t_eval[-1] = b

    layout = _state_layout(system)
    rhs_fn = _build_rhs(system, layout)
    y0 = [float(system.functions[name].conditions[k].value.magnitude) for name, k in layout]
    states = _integrate(rhs_fn, float(system.point_bare), y0, t_eval, system.settings.accuracy,
                        system.settings.steps)

    order = sorted(system.functions)
    index0 = {name: layout.index((name, 0)) for name in order}
    values = {name: [state[index0[name]] for state in states] for name in order}
    dims = {name: system.functions[name].dims for name in order}
    functions = {name: _bind_numeric(system, name, t_eval, values[name]) for name in order}
    return NumericOutcome(system.indep_name, t_eval, system.t_dims, order, values, dims, functions)
