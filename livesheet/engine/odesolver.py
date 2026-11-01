"""ODE systems: equations + initial conditions, closed-form via SymPy ``dsolve``, numeric
fallback via SciPy ``solve_ivp`` (spec 010). Parallel in spirit to ``solver.py``: regions join
a model through a trailing ``in <name>`` tag, collected by ``evaluator.py``'s ``_run_model``
and handed to ``build()`` here. scipy is imported lazily so the GUI starts without it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import sympy as sp
from sympy.core.function import AppliedUndef

from .solver import _unit_expr
from .syntax import Statement, StatementError, split_ode_equation
from .units import Measured, UnitError, dims_to_text, measure

if TYPE_CHECKING:  # pragma: no cover
    from .evaluator import Engine

DEFAULT_ACCURACY = 1e-6
DEFAULT_STEPS = 10000
DEFAULT_POINTS = 101


@dataclass
class Settings:
    accuracy: float = DEFAULT_ACCURACY
    steps: int = DEFAULT_STEPS


@dataclass
class EquationLine:
    source: str        # original "<lhs> == <rhs>" text (the model_ode statement's ``expr``)
    func_name: str
    order: int          # the derivative order this particular line defines


@dataclass
class System:
    model: str
    indep_name: str
    indep_symbol: sp.Symbol
    func_names: list[str]
    functions: dict[str, sp.Function]
    highest_order: dict[str, int]
    equations: list[EquationLine]
    conditions: dict[str, dict[int, tuple[str, str]]]   # func -> order -> (point text, value text)
    over: Statement | None
    settings: Settings
    point: Measured                 # the conditions' shared initial point
    local_env: dict                 # env + function placeholders + the independent-variable symbol


@dataclass
class SymbolicOutcome:
    indep_name: str
    indep_symbol: sp.Symbol
    formulas: dict[str, sp.Expr]     # func name -> explicit formula in terms of indep_symbol


@dataclass
class NumericOutcome:
    indep_name: str
    func_names: list[str]
    x_start: float
    x_step: float
    count: int
    x_dims: tuple
    func_dims: dict[str, tuple]
    x_values_si: list[float]
    y_values_si: dict[str, list[float]]
    callables: dict[str, object]     # func name -> python callable usable as a worksheet function


class _StepLimitExceeded(Exception):
    pass


# -- settings (own defaults; otherwise identical rules to solver.py's) -------------------

def read_settings(engine: "Engine", regions: list[Statement], env: dict) -> Settings:
    settings = Settings()
    for st in regions:
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


# -- build: gather ode/start/over/settings regions into one System ----------------------

def build(engine: "Engine", model: str, regions: list[Statement], env: dict) -> System:
    equations: list[EquationLine] = []
    func_names: list[str] = []
    highest_order: dict[str, int] = {}
    indep_name: str | None = None
    for st in regions:
        if st.kind != "model_ode":
            continue
        fname, var, order = split_ode_equation(st.expr)
        if indep_name is None:
            indep_name = var
        elif var != indep_name:
            raise StatementError(f'All equations of "{model}" must use the same independent variable')
        if fname not in func_names:
            func_names.append(fname)
        highest_order[fname] = max(highest_order.get(fname, 0), order)
        equations.append(EquationLine(st.expr, fname, order))
    if not equations or indep_name is None:
        raise StatementError(f'No equations declared for ODE system "{model}"')

    indep_symbol = sp.Symbol(indep_name, real=True)
    functions = {name: sp.Function(name) for name in func_names}
    local_env = dict(env)
    local_env.update(functions)
    local_env[indep_name] = indep_symbol

    conditions: dict[str, dict[int, tuple[str, str]]] = {name: {} for name in func_names}
    over_st: Statement | None = None
    for st in regions:
        if st.kind == "model_ic":
            for fname, order, point_text, value_text in st.conditions:
                if fname not in conditions:
                    raise StatementError(f'"{fname}" is not an equation of ODE system "{model}"')
                if order in conditions[fname]:
                    prime_name = fname + "'" * order
                    raise StatementError(f'"{prime_name}" is declared twice in model "{model}"')
                conditions[fname][order] = (point_text, value_text)
        elif st.kind == "model_over":
            if over_st is not None:
                raise StatementError("only one 'over' line is allowed")
            if st.name != indep_name:
                raise StatementError(f'"over" must use the independent variable "{indep_name}"')
            over_st = st

    for fname in func_names:
        need = highest_order[fname]
        have = conditions[fname]
        if len(have) != need:
            raise StatementError(f'"{model}" needs {need} initial condition(s) for {fname}, has {len(have)}')
        if sorted(have) != list(range(need)):
            raise StatementError(f'"{model}" needs one condition of each order 0..{need - 1} for {fname}')

    _check_condition_dims(engine, model, conditions, local_env, _indep_dims(engine, over_st, local_env))
    point = _shared_point(engine, model, conditions, local_env)
    settings = read_settings(engine, regions, env)
    return System(model, indep_name, indep_symbol, func_names, functions, highest_order,
                  equations, conditions, over_st, settings, point, local_env)


def _indep_dims(engine: "Engine", over_st: Statement | None, local_env: dict) -> tuple:
    """The independent variable's dimension, inferred from an ``over`` line's start value
    when one is declared; dimensionless by default (same "zero/no unit given" convention
    already used for a shared initial point) when no ``over`` line exists yet to tell."""
    if over_st is None:
        return ()
    return measure(engine.parse(over_st.expr, local_env, keep_units=True)).dims


def _check_condition_dims(engine: "Engine", model: str, conditions: dict, local_env: dict,
                          x_dims: tuple) -> None:
    """Cross-check a single function's several initial-condition orders against each other,
    once, up front -- before any call into SymPy/SciPy (D1, spec 010 independent review).
    Order 0 fixes the function's own dimension; order N's dimension must then be order 0's
    divided by the independent variable's dimension raised to the N-th power (e.g. `y` in
    metres and `t` in seconds requires `y'` in m/s, `y''` in m/s², ...). A bare, unitless
    zero is exempt (same "zero fits any dimension" convention this module already uses for
    a shared initial point), since it carries no real dimensional information either way.
    """
    for fname, have in conditions.items():
        if 0 not in have:
            continue
        base = measure(engine.parse(have[0][1], local_env, keep_units=True))
        if base.magnitude == 0:
            continue   # no real base dimension to check the other orders against
        for order, (point_text, value_text) in have.items():
            if order == 0:
                continue
            value = measure(engine.parse(value_text, local_env, keep_units=True))
            if value.magnitude == 0:
                continue
            expected = measure(_unit_expr(base.dims) / _unit_expr(x_dims) ** order)
            if value.dims != expected.dims:
                prime_name = fname + "'" * order
                raise UnitError(
                    'Units do not match: '
                    f'"{prime_name}({point_text})" should have units '
                    f"{dims_to_text(expected.dims) or 'dimensionless'}, not "
                    f"{dims_to_text(value.dims) or 'dimensionless'}"
                )


def _same_point(a: Measured, b: Measured) -> bool:
    same_mag = abs(float(a.magnitude) - float(b.magnitude)) <= 1e-9 * max(1.0, abs(float(b.magnitude)))
    same_dims = a.dims == b.dims or a.magnitude == 0 or b.magnitude == 0
    return same_mag and same_dims


def _shared_point(engine: "Engine", model: str, conditions: dict, local_env: dict) -> Measured:
    first: Measured | None = None
    for items in conditions.values():
        for point_text, _value_text in items.values():
            meas = measure(engine.parse(point_text, local_env, keep_units=True))
            if first is None:
                first = meas
                continue
            if not _same_point(meas, first):
                raise StatementError(f'All initial conditions of "{model}" must be given at the same point')
    if first is None:
        raise StatementError(f'No initial conditions declared for ODE system "{model}"')
    return first


# -- symbolic: dsolve per equation, topologically, falling back to a batch system -------

def solve_symbolic(engine: "Engine", system: System) -> SymbolicOutcome | None:
    solved: dict[str, sp.Expr] = {}
    remaining = list(system.equations)
    progress = True
    while remaining and progress:
        progress = False
        for eqline in list(remaining):
            try:
                eq = engine.parse(eqline.source, system.local_env)
            except StatementError:
                return None
            deps = _other_function_deps(eq, eqline.func_name) - set(solved)
            if deps:
                continue
            eq = _substitute_solved(eq, solved, system)
            target = system.functions[eqline.func_name](system.indep_symbol)
            ics = _build_ics(engine, system, eqline.func_name)
            sol = _try_dsolve(eq, target, ics)
            if sol is None or not _is_explicit(sol, target):
                return None
            solved[eqline.func_name] = sol.rhs
            remaining.remove(eqline)
            progress = True
    if remaining:
        names_remaining = {e.func_name for e in remaining}
        try:
            eqs = [_substitute_solved(engine.parse(e.source, system.local_env), solved, system)
                   for e in remaining]
            funcs = [system.functions[e.func_name](system.indep_symbol) for e in remaining]
            ics: dict = {}
            for e in remaining:
                ics.update(_build_ics(engine, system, e.func_name))
            sols = sp.dsolve(eqs, funcs, ics=ics, simplify=False)
        except Exception:  # noqa: BLE001 - any solver failure means "no closed form"
            return None
        if not isinstance(sols, list):
            sols = [sols]
        for sol in sols:
            fname = _lhs_func_name(sol, system)
            if fname is None or fname not in names_remaining:
                return None
            if not _is_explicit(sol, system.functions[fname](system.indep_symbol)):
                return None
            solved[fname] = sol.rhs
    return SymbolicOutcome(system.indep_name, system.indep_symbol,
                           {name: solved[name] for name in system.func_names})


def _try_dsolve(eq: sp.Eq, target: sp.Expr, ics: dict):
    try:
        sol = sp.dsolve(eq, target, ics=ics, simplify=False)
    except Exception:  # noqa: BLE001 - any solver failure means "no closed form"
        return None
    if isinstance(sol, list):
        return sol[0] if len(sol) == 1 else None
    return sol


def _other_function_deps(eq: sp.Eq, own_name: str) -> set[str]:
    names: set[str] = set()
    for side in (eq.lhs, eq.rhs):
        for fn in side.atoms(AppliedUndef):
            if fn.func.__name__ != own_name:
                names.add(fn.func.__name__)
    return names


def _substitute_solved(eq: sp.Eq, solved: dict[str, sp.Expr], system: System) -> sp.Eq:
    for name, formula in solved.items():
        eq = eq.subs(system.functions[name](system.indep_symbol), formula)
    return eq


def _build_ics(engine: "Engine", system: System, func_name: str) -> dict:
    ics = {}
    func = system.functions[func_name](system.indep_symbol)
    for order, (point_text, value_text) in system.conditions[func_name].items():
        point_val = engine.parse(point_text, system.local_env, keep_units=True)
        value_val = engine.parse(value_text, system.local_env, keep_units=True)
        if order == 0:
            key = func.subs(system.indep_symbol, point_val)
        else:
            key = sp.Derivative(func, system.indep_symbol, order).subs(system.indep_symbol, point_val)
        ics[key] = value_val
    return ics


def _is_explicit(sol, target) -> bool:
    if not (isinstance(sol, sp.Eq) and sol.lhs == target):
        return False
    rhs = sol.rhs
    if rhs.has(sp.Integral) or rhs.atoms(sp.Derivative):
        return False
    return target not in rhs.atoms(AppliedUndef)


def _lhs_func_name(sol, system: System) -> str | None:
    if not isinstance(sol, sp.Eq) or not isinstance(sol.lhs, AppliedUndef):
        return None
    name = sol.lhs.func.__name__
    return name if name in system.functions else None


# -- numeric: reduce to a first-order system, integrate with scipy ----------------------

def _state_layout(system: System) -> tuple[dict[str, int], int]:
    offsets: dict[str, int] = {}
    idx = 0
    for name in system.func_names:
        offsets[name] = idx
        idx += system.highest_order[name]
    return offsets, idx


def _numeric_rhs(engine: "Engine", system: System, name: str):
    order = system.highest_order[name]
    eqline = next(e for e in system.equations if e.func_name == name and e.order == order)
    eq = engine.parse(eqline.source, system.local_env)
    target = sp.Derivative(system.functions[name](system.indep_symbol), system.indep_symbol, order)
    sols = sp.solve(eq, target)
    if len(sols) != 1:
        raise StatementError(f'Cannot isolate the highest derivative of "{name}" in "{system.model}"')
    isolated = sols[0]
    state_symbols = {g: sp.Symbol(f"_state_{g}") for g in system.func_names}
    isolated = isolated.subs({system.functions[g](system.indep_symbol): state_symbols[g]
                              for g in system.func_names})
    if isolated.atoms(sp.Derivative) or isolated.atoms(AppliedUndef):
        raise StatementError(f'"{eqline.source.strip()}" uses a derivative this system cannot '
                             "reduce to a first-order system")
    measured = measure(isolated)
    args = [system.indep_symbol] + [state_symbols[g] for g in system.func_names]
    return sp.lambdify(args, measured.magnitude, "numpy")


def _make_rhs(system: System, offsets: dict[str, int], total: int, rhs_funcs: dict, limit: int):
    calls = {"n": 0}

    def rhs(t, state):
        calls["n"] += 1
        if calls["n"] > limit:
            raise _StepLimitExceeded()
        values0 = [state[offsets[g]] for g in system.func_names]
        out = [0.0] * total
        for name in system.func_names:
            n = system.highest_order[name]
            off = offsets[name]
            for c in range(n - 1):
                out[off + c] = state[off + c + 1]
            out[off + n - 1] = float(rhs_funcs[name](t, *values0))
        return out

    return rhs, calls


def _point_count(engine: "Engine", system: System) -> int:
    meas = measure(engine.parse(system.over.over_points, system.local_env, keep_units=True))
    n = float(meas.magnitude)
    if meas.dims or n != int(n) or n < 2:
        raise StatementError("points must be a whole number of at least 2")
    return int(n)


def _make_callable(offsets: dict[str, int], dense_sol, x_dims: tuple, func_dims: dict, name: str):
    comp = offsets[name]
    f_unit = _unit_expr(func_dims[name])

    def f(x_value):
        xm = measure(x_value)
        if xm.dims != x_dims and not (xm.magnitude == 0 or x_dims == () and not xm.dims):
            raise UnitError("Units do not match: expected "
                            f"{dims_to_text(x_dims) or 'dimensionless'}")
        state = dense_sol(float(xm.magnitude))
        value = state[comp] if getattr(state, "ndim", 0) else float(state)
        return sp.Float(float(value)) * f_unit

    return f


def solve_numeric(engine: "Engine", system: System) -> NumericOutcome:
    if system.over is None:
        raise StatementError(f'over {system.indep_name} from ... to ... is needed to solve '
                             f'"{system.model}" numerically')
    start = measure(engine.parse(system.over.expr, system.local_env, keep_units=True))
    end = measure(engine.parse(system.over.range_end, system.local_env, keep_units=True))
    if start.dims != end.dims:
        raise UnitError("Units do not match: sampling limits have different units")
    if not _same_point(start, system.point):
        raise StatementError(f'"over" must start at the shared initial point of "{system.model}"')
    count = _point_count(engine, system) if system.over.over_points else DEFAULT_POINTS
    if count < 2:
        raise StatementError("points must be a whole number of at least 2")
    a, b = float(start.magnitude), float(end.magnitude)
    step = (b - a) / (count - 1)

    offsets, total = _state_layout(system)
    initial = [0.0] * total
    func_dims: dict[str, tuple] = {}
    for name in system.func_names:
        for order in range(system.highest_order[name]):
            _point_text, value_text = system.conditions[name][order]
            value = measure(engine.parse(value_text, system.local_env, keep_units=True))
            initial[offsets[name] + order] = float(value.magnitude)
            if order == 0:
                func_dims[name] = value.dims

    rhs_funcs = {name: _numeric_rhs(engine, system, name) for name in system.func_names}
    limit = system.settings.steps
    rhs, calls = _make_rhs(system, offsets, total, rhs_funcs, limit)

    xs = [a + k * step for k in range(count)]
    xs[-1] = b

    import numpy as np
    from scipy.integrate import solve_ivp

    try:
        sol = solve_ivp(rhs, (a, b), initial, t_eval=np.array(xs, dtype=float),
                        method="RK45", rtol=system.settings.accuracy, dense_output=True)
    except _StepLimitExceeded:
        raise StatementError(f"Not converged: stopped after {calls['n']} function evaluations "
                             f"(steps limit {limit})") from None
    if not sol.success:
        raise StatementError(f"Not converged: {sol.message}")

    y_values_si = {name: [float(v) for v in sol.y[offsets[name]]] for name in system.func_names}
    callables = {name: _make_callable(offsets, sol.sol, start.dims, func_dims, name)
                for name in system.func_names}
    return NumericOutcome(system.indep_name, list(system.func_names), a, step, count, start.dims,
                          func_dims, list(xs), y_values_si, callables)
