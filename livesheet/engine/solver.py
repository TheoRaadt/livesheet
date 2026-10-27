"""Numeric solve models: unknowns with guesses plus equality constraints (Phase A: ``settle``).

Regions join a model through a trailing ``in <name>`` tag. The unknowns are scaled to
dimensionless numbers near 1 (the SI magnitude of the guess is the scale) and the constraints
are turned into plain-float callables once; units are checked symbolically at the guess.
scipy is imported lazily so that the GUI starts without it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import sympy as sp
from sympy.core.function import AppliedUndef

from .syntax import Statement, StatementError
from .units import BASE_UNIT_BY_DIM, Measured, UnitError, measure

if TYPE_CHECKING:  # pragma: no cover
    from .evaluator import Engine

DEFAULT_ACCURACY = 1e-8
DEFAULT_STEPS = 200


@dataclass
class Unknown:
    name: str
    scale: float            # SI magnitude used to scale the unknown (1 when the guess is 0)
    start: float            # scaled starting value (guess / scale)
    dims: tuple
    symbol: sp.Symbol


@dataclass
class Constraint:
    source: str
    left: object            # callables of the scaled unknowns -> SI magnitude
    right: object
    ref: float              # |l0| + |r0| at the guess (1 when zero)
    op: str = "=="          # == | <= | >=  (strict < and > are treated as non-strict)
    owner: int = 0          # index of the declaring region in the model's region list
    grad: object = None     # callable: scaled unknowns -> gradient of the gap (SI), or None


@dataclass
class Objective:
    source: str
    func: object            # callable of the scaled unknowns -> SI magnitude
    scale: float            # |value at the guess| (1 when zero)
    sign: float             # +1 minimise, -1 maximise
    dims: tuple
    grad: object = None     # callable: scaled unknowns -> gradient of the magnitude, or None


@dataclass
class Settings:
    accuracy: float = DEFAULT_ACCURACY
    steps: int = DEFAULT_STEPS


@dataclass
class Solution:
    unknowns: list[Unknown]
    values: list[float]     # SI magnitudes
    objective: tuple[float, tuple] | None = None   # (SI magnitude, dims) for least / most
    constraints: list[Constraint] = field(default_factory=list)


class SolveError(StatementError):
    """Solver failure; ``owner`` is the region index of the worst violated constraint (or -1)."""

    def __init__(self, message: str, owner: int = -1):
        super().__init__(message)
        self.owner = owner


def _unit_expr(dims: tuple) -> sp.Expr:
    expr = sp.Integer(1)
    for dim, exp in dims:
        expr = expr * BASE_UNIT_BY_DIM[dim] ** exp
    return expr


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


def check_setting(engine: "Engine", st: Statement, env: dict) -> None:
    read_settings(engine, [st], env)


def declare(engine: "Engine", model: str, regions: list[Statement], env: dict) -> list[Unknown]:
    unknowns: list[Unknown] = []
    for st in regions:
        if st.kind != "model_vary":
            continue
        for name, text in st.guesses:
            if any(u.name == name for u in unknowns):
                raise StatementError(f'"{name}" is declared twice in model "{model}"')
            meas = measure(engine.parse(text, env, keep_units=True))
            try:
                g = float(meas.magnitude)
            except TypeError:
                raise StatementError(f'Starting guess for "{name}" must be a real number') from None
            if not math.isfinite(g):
                raise StatementError(f'Starting guess for "{name}" must be finite')
            scale = abs(g) if g != 0 else 1.0
            unknowns.append(Unknown(name, scale, g / scale, meas.dims, sp.Symbol(f"_z_{name}", real=True)))
    if not unknowns:
        raise StatementError(f'No unknowns declared for model "{model}"')
    return unknowns


def _relation_parts(src: str) -> tuple[str, str, str]:
    mt = re.search(r"==|<=|>=|<|>", src)
    op = {"<": "<=", ">": ">="}.get(mt.group(0), mt.group(0))
    return src[:mt.start()], op, src[mt.end():]


def _checked(engine: "Engine", text: str, local: dict, zs: list, what: str):
    """Parse ``text``; every free name must be an unknown or defined, and units must be consistent."""
    value = engine.parse(text, local)
    if isinstance(value, sp.MatrixBase):
        raise StatementError(f'{what} "{text.strip()}" must be scalar')
    return value


def _undefined(exprs, zs) -> None:
    free = set().union(*(e.free_symbols for e in exprs))
    undefined = sorted({str(x) for x in free if x not in zs}
                       | {f.func.__name__ for e in exprs for f in e.atoms(AppliedUndef)})
    if undefined:
        names = ", ".join(undefined)
        raise StatementError(f"{names} {'is' if len(undefined) == 1 else 'are'} not defined")


def _local_env(unknowns: list[Unknown], env: dict) -> dict:
    local = dict(env)
    for u in unknowns:
        local[u.name] = u.scale * u.symbol * _unit_expr(u.dims)
    return local


def _eval_start(fn, start, what: str) -> float:
    try:
        value = _scalar(fn(*start))
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise StatementError(f"Cannot evaluate at the starting guess: {exc}") from None
    if not math.isfinite(value):
        raise StatementError("Cannot evaluate at the starting guess: result is not finite")
    return value


def build_constraints(engine: "Engine", regions: list[Statement], unknowns: list[Unknown],
                      env: dict) -> list[Constraint]:
    local = _local_env(unknowns, env)
    zs = [u.symbol for u in unknowns]
    start = [u.start for u in unknowns]
    out: list[Constraint] = []
    for index, st in enumerate(regions):
        if st.kind != "model_require":
            continue
        for src in st.relations:
            lhs, op, rhs = _relation_parts(src)
            left, right = _checked(engine, lhs, local, zs, "Constraint"), _checked(engine, rhs, local, zs, "Constraint")
            _undefined([left, right], zs)
            if not ((left.free_symbols | right.free_symbols) & set(zs)):
                raise StatementError(f'Constraint "{src}" does not involve any unknown')
            try:
                ml, mr = measure(left), measure(right)
            except UnitError as exc:
                raise UnitError(f'Units do not match in constraint "{src}" ({exc})') from None
            if ml.dims != mr.dims and not (left == 0 or right == 0):   # a plain 0 fits any dimension
                raise UnitError(f'Units do not match in constraint "{src}"')
            lf = sp.lambdify(zs, ml.magnitude, modules=["numpy"])
            rf = sp.lambdify(zs, mr.magnitude, modules=["numpy"])
            ref = abs(_eval_start(lf, start, src)) + abs(_eval_start(rf, start, src))
            gap = (mr.magnitude - ml.magnitude) if op == ">=" else (ml.magnitude - mr.magnitude)
            out.append(Constraint(src, lf, rf, ref if ref > 0 else 1.0, op, index, _gradient(zs, gap)))
    return out


def build_objective(engine: "Engine", st: Statement, unknowns: list[Unknown], env: dict) -> Objective:
    local = _local_env(unknowns, env)
    zs = [u.symbol for u in unknowns]
    expr = _checked(engine, st.expr, local, zs, "Objective")
    _undefined([expr], zs)
    if not (expr.free_symbols & set(zs)):
        raise StatementError(f'Objective "{st.expr}" does not involve any unknown')
    meas = measure(expr)
    func = sp.lambdify(zs, meas.magnitude, modules=["numpy"])
    f0 = _eval_start(func, [u.start for u in unknowns], st.expr)
    return Objective(st.expr, func, abs(f0) if f0 != 0 else 1.0, 1.0 if st.goal == "min" else -1.0,
                     meas.dims, _gradient(zs, meas.magnitude))


def _gradient(zs: list, expr):
    """Exact gradient as a callable (or ``None`` when SymPy cannot differentiate the expression)."""
    try:
        return sp.lambdify(zs, [sp.diff(expr, z) for z in zs], modules=["numpy"])
    except Exception:  # noqa: BLE001 - finite differences are the fallback
        return None


def _scalar(x) -> float:
    value = complex(x)
    if abs(value.imag) > 1e-12 * max(1.0, abs(value.real)):
        raise ValueError("complex value")
    return value.real


def _gap(c: Constraint, z) -> float:
    """Signed gap in SI: zero for a satisfied equality, <= 0 for a satisfied inequality."""
    d = _scalar(c.left(*z)) - _scalar(c.right(*z))
    return -d if c.op == ">=" else d


def _residuals(constraints: list[Constraint], z):
    import numpy as np

    out = []
    for c in constraints:
        try:
            out.append(_gap(c, z) / c.ref)
        except (ArithmeticError, ValueError, TypeError):
            out.append(float("nan"))
    return np.array(out, dtype=float)


def _violations(constraints: list[Constraint], z) -> list[tuple[float, str, int]]:
    """(normalised violation, source, owner) per constraint; <= accuracy means satisfied."""
    result = []
    for c in constraints:
        try:
            l, r = _scalar(c.left(*z)), _scalar(c.right(*z))
            gap = _gap(c, z)
            raw = abs(gap) if c.op == "==" else max(0.0, gap)
            result.append((raw / max(abs(l), abs(r), c.ref), c.source, c.owner))
        except (ArithmeticError, ValueError, TypeError):
            result.append((float("inf"), c.source, c.owner))
    return result


def _strict(constraints: list[Constraint], z) -> list[float]:
    out = []
    for c in constraints:
        try:
            gap = _gap(c, z)
            out.append((abs(gap) if c.op == "==" else max(0.0, gap)) / c.ref)
        except (ArithmeticError, ValueError, TypeError):
            out.append(float("inf"))
    return out


def settle(engine: "Engine", model: str, regions: list[Statement], env: dict,
           goal: Statement | None = None) -> Solution:
    """Solve the model: ``goal`` is the least/most result statement (``None`` for settle)."""
    import warnings

    try:
        import numpy as np
        from scipy import optimize  # noqa: F401 - checked here so that a missing package is reported cleanly
    except ImportError:
        raise StatementError("Solving needs the scipy package") from None
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _solve(engine, model, regions, env, goal)


def _starts(z0):
    """Deterministic starting points: the guess, small perturbations, then rescaled guesses."""
    import numpy as np

    yield z0
    h = 1e-3 * np.maximum(1.0, np.abs(z0))
    yield z0 + h
    yield z0 - h
    base = np.where(z0 != 0, z0, 1.0)
    for k in range(1, 13):
        yield base * 10.0 ** k
        yield -base * 10.0 ** k


def _jacobian(np, group: list, z):
    return np.array([[float(g) for g in c.grad(*z)] for c in group], dtype=float) / \
        np.array([[c.ref] for c in group], dtype=float)


def _attempt(optimize, np, constraints, objective, z0, start, settings, exact=True):
    """One run from ``start``: (z, evaluations used, hit the step limit, optimiser reported success)."""
    eqs = [c for c in constraints if c.op == "=="]
    ineqs = [c for c in constraints if c.op != "=="]
    n = len(z0)

    def eq_fun(z):
        return _residuals(eqs, z)

    if objective is None and not ineqs and eqs:
        if len(eqs) == n:
            res = optimize.root(eq_fun, start, method="hybr", tol=1e-14, options={"maxfev": settings.steps})
            return res.x, int(res.nfev), res.status == 2 or (not res.success and res.nfev >= settings.steps), True
        if len(eqs) > n:
            res = optimize.least_squares(eq_fun, start, xtol=1e-15, ftol=1e-15, gtol=1e-15,
                                         max_nfev=settings.steps)
            return res.x, int(res.nfev), res.status == 0, True
    cons = []
    use = exact and all(c.grad is not None for c in constraints)
    if eqs:
        cons.append({"type": "eq", "fun": eq_fun})
        if use:
            cons[-1]["jac"] = lambda z: _jacobian(np, eqs, z)
    if ineqs:
        cons.append({"type": "ineq", "fun": lambda z: -_residuals(ineqs, z)})
        if use:
            cons[-1]["jac"] = lambda z: -_jacobian(np, ineqs, z)
    if objective is None:
        fun, jac = (lambda z: float(np.sum((z - z0) ** 2))), (lambda z: 2 * (z - z0))
    else:
        def fun(z):
            return float(objective.sign * _scalar(objective.func(*z)) / objective.scale)

        jac = None
        if exact and objective.grad is not None:
            def jac(z):
                return objective.sign * np.array([float(g) for g in objective.grad(*z)]) / objective.scale
    res = optimize.minimize(fun, start, method="SLSQP", jac=jac, constraints=cons,
                            options={"maxiter": settings.steps, "ftol": 1e-16})
    for _ in range(3):          # restarting from the result tightens active-constraint solutions
        if res.status != 0:
            break
        again = optimize.minimize(fun, res.x, method="SLSQP", jac=jac, constraints=cons,
                                  options={"maxiter": settings.steps, "ftol": 1e-16})
        if again.status != 0 or not np.isfinite(again.fun) or again.fun > res.fun + 1e-12:
            break
        res = again
    z = res.x
    if objective is None and not ineqs:
        z = _polish(z, eq_fun)
    return z, int(res.nit), res.status == 9, res.status == 0


def _worst(constraints, z):
    viol = _violations(constraints, z)
    if not viol:
        return 0.0, "", -1
    return max(viol, key=lambda v: (v[0] if math.isfinite(v[0]) else float("inf")))


def _solve(engine: "Engine", model: str, regions: list[Statement], env: dict, goal) -> Solution:
    from scipy import optimize
    import numpy as np

    unknowns = declare(engine, model, regions, env)
    settings = read_settings(engine, regions, env)
    constraints = build_constraints(engine, regions, unknowns, env)
    objective = build_objective(engine, goal, unknowns, env) if goal is not None else None
    if not constraints and objective is None:
        raise StatementError("No constraints declared for this model")
    z0 = np.array([u.start for u in unknowns], dtype=float)
    best = None            # (worst violation, source, owner, z)
    first = None           # (evaluations used, hit the step limit) of the run from the guess
    message = ""
    for k, start in enumerate(_starts(z0)):
        try:
            try:
                z, used, limit, ok = _attempt(optimize, np, constraints, objective, z0, start, settings)
                if not np.all(np.isfinite(z)):
                    raise ValueError("non-finite result")
            except (ArithmeticError, ValueError, TypeError):   # e.g. a bad exact gradient: use differences
                z, used, limit, ok = _attempt(optimize, np, constraints, objective, z0, start, settings, False)
        except (ArithmeticError, ValueError, TypeError):
            z, used, limit, ok = start, 0, False, False
        if first is None:
            first = (used, limit)
        worst, source, owner = _worst(constraints, z)
        if k > 0 and constraints:
            # a retried start must satisfy the stricter test relative to the guess scale only,
            # otherwise huge values would pass the relative rule trivially (x == x + 1 at x = 1e12)
            worst = max(_strict(constraints, z))
        feasible = worst <= settings.accuracy
        if feasible and (objective is None or ok):
            value = None
            if objective is not None:
                value = (_scalar(objective.func(*z)), objective.dims)
            return Solution(unknowns, _clean([float(zi) * u.scale for zi, u in zip(z, unknowns)], unknowns),
                            value, constraints)
        if feasible and objective is not None:
            worst, source, owner = float("inf"), "", -1   # feasible, but no optimum reported
        if best is None or worst < best[0] or not math.isfinite(best[0]):
            best = (worst, source, owner, z)
    worst, source, owner, _ = best
    if first[1]:
        raise SolveError(f"Not converged: stopped after {first[0]} function evaluations "
                         f"(steps limit {settings.steps}), largest violation {worst:.1e} "
                         "(try another starting guess or raise steps)", owner)
    if not math.isfinite(worst) and not source:
        raise SolveError("No solution found: the objective has no optimum within the constraints "
                         "(unbounded or the solver did not converge)")
    raise SolveError(f'No solution found: closest point violates "{source}" by {worst:.1e}', owner)


def _clean(values: list[float], unknowns: list[Unknown]) -> list[float]:
    """Round-off such as 5e-17 next to an unknown of 2 (same dimension) is reported as 0."""
    out = []
    for v, u in zip(values, unknowns):
        peers = [abs(w) for w, o in zip(values, unknowns) if o.dims == u.dims]
        out.append(0.0 if len(peers) > 1 and abs(v) <= 1e-12 * max(peers) else v)
    return out


def _polish(z, fun):
    """A few Gauss-Newton steps onto the constraint surface (minimum-norm correction)."""
    import numpy as np

    for _ in range(5):
        f = fun(z)
        if not np.all(np.isfinite(f)) or np.max(np.abs(f)) < 1e-15:
            break
        h = 1e-7
        jac = np.column_stack([(fun(z + h * e) - f) / h for e in np.eye(len(z))])
        step = np.linalg.lstsq(jac, -f, rcond=None)[0]
        z = z + step
    return z
