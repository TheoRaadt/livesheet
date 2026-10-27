"""Numeric solve models: unknowns with guesses plus equality constraints (Phase A: ``settle``).

Regions join a model through a trailing ``in <name>`` tag. The unknowns are scaled to
dimensionless numbers near 1 (the SI magnitude of the guess is the scale) and the constraints
are turned into plain-float callables once; units are checked symbolically at the guess.
scipy is imported lazily so that the GUI starts without it.
"""

from __future__ import annotations

import math
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


@dataclass
class Settings:
    accuracy: float = DEFAULT_ACCURACY
    steps: int = DEFAULT_STEPS


@dataclass
class Solution:
    unknowns: list[Unknown]
    values: list[float]     # SI magnitudes


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


def build_constraints(engine: "Engine", regions: list[Statement], unknowns: list[Unknown],
                      env: dict) -> list[Constraint]:
    local = dict(env)
    for u in unknowns:
        local[u.name] = u.scale * u.symbol * _unit_expr(u.dims)
    zs = [u.symbol for u in unknowns]
    start = [u.start for u in unknowns]
    out: list[Constraint] = []
    for st in regions:
        if st.kind != "model_require":
            continue
        for src in st.relations:
            if "==" not in src:
                raise StatementError("Inequality constraints are not available yet")
            lhs, rhs = src.split("==", 1)
            left, right = engine.parse(lhs, local), engine.parse(rhs, local)
            for side in (left, right):
                if isinstance(side, sp.MatrixBase):
                    raise StatementError(f'Constraint "{src}" must be scalar')
            free = (left.free_symbols | right.free_symbols)
            undefined = sorted({str(x) for x in free if x not in zs}
                               | {f.func.__name__ for e in (left, right) for f in e.atoms(AppliedUndef)})
            if undefined:
                names = ", ".join(undefined)
                raise StatementError(f"{names} {'is' if len(undefined) == 1 else 'are'} not defined")
            if not (free & set(zs)):
                raise StatementError(f'Constraint "{src}" does not involve any unknown')
            try:
                ml, mr = measure(left), measure(right)
            except UnitError as exc:
                raise UnitError(f'Units do not match in constraint "{src}" ({exc})') from None
            if ml.dims != mr.dims:
                raise UnitError(f'Units do not match in constraint "{src}"')
            lf = sp.lambdify(zs, ml.magnitude, modules=["numpy"])
            rf = sp.lambdify(zs, mr.magnitude, modules=["numpy"])
            try:
                l0, r0 = _scalar(lf(*start)), _scalar(rf(*start))
            except (ArithmeticError, ValueError, TypeError) as exc:
                raise StatementError(f"Cannot evaluate at the starting guess: {exc}") from None
            if not (math.isfinite(l0) and math.isfinite(r0)):
                raise StatementError("Cannot evaluate at the starting guess: result is not finite")
            ref = abs(l0) + abs(r0)
            out.append(Constraint(src, lf, rf, ref if ref > 0 else 1.0))
    if not out:
        raise StatementError("No constraints declared for this model")
    return out


def _scalar(x) -> float:
    value = complex(x)
    if abs(value.imag) > 1e-12 * max(1.0, abs(value.real)):
        raise ValueError("complex value")
    return value.real


def _residuals(constraints: list[Constraint], z):
    import numpy as np

    out = []
    for c in constraints:
        try:
            out.append((_scalar(c.left(*z)) - _scalar(c.right(*z))) / c.ref)
        except (ArithmeticError, ValueError, TypeError):
            out.append(float("nan"))
    return np.array(out, dtype=float)


def _violations(constraints: list[Constraint], z, tol: float) -> list[tuple[float, str]]:
    """(normalised violation, source) for every constraint; <= tol means satisfied."""
    result = []
    for c in constraints:
        try:
            l, r = _scalar(c.left(*z)), _scalar(c.right(*z))
            scale = max(abs(l), abs(r), c.ref)
            result.append((abs(l - r) / scale, c.source))
        except (ArithmeticError, ValueError, TypeError):
            result.append((float("inf"), c.source))
    return result


def settle(engine: "Engine", model: str, regions: list[Statement], env: dict) -> Solution:
    try:
        from scipy import optimize
    except ImportError:
        raise StatementError("Solving needs the scipy package") from None
    import numpy as np

    unknowns = declare(engine, model, regions, env)
    settings = read_settings(engine, regions, env)
    constraints = build_constraints(engine, regions, unknowns, env)
    z0 = np.array([u.start for u in unknowns], dtype=float)
    n_eq, n = len(constraints), len(unknowns)
    limit = False

    def fun(z):
        return _residuals(constraints, z)

    if n_eq == n:
        res = optimize.root(fun, z0, method="hybr", tol=1e-14, options={"maxfev": settings.steps})
        z, used, limit = res.x, int(res.nfev), res.status == 2 or (not res.success and res.nfev >= settings.steps)
    elif n_eq > n:
        res = optimize.least_squares(fun, z0, xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=settings.steps)
        z, used, limit = res.x, int(res.nfev), res.status == 0
    else:
        res = optimize.minimize(lambda z: float(np.sum((z - z0) ** 2)), z0, method="SLSQP",
                                jac=lambda z: 2 * (z - z0),
                                constraints=[{"type": "eq", "fun": fun}],
                                options={"maxiter": settings.steps, "ftol": 1e-16})
        z, used, limit = res.x, int(res.nit), res.status == 9
        z = _polish(constraints, z, fun)
    viol = _violations(constraints, z, settings.accuracy)
    worst, source = max(viol, key=lambda v: (v[0] if math.isfinite(v[0]) else float("inf")))
    if worst <= settings.accuracy:
        return Solution(unknowns, [float(zi) * u.scale for zi, u in zip(z, unknowns)])
    if limit:
        raise StatementError(f"Not converged: stopped after {used} steps, largest violation {worst:.1e} "
                             "(try another starting guess or raise steps)")
    raise StatementError(f'No solution found: closest point violates "{source}" by {worst:.1e}')


def _polish(constraints, z, fun):
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
