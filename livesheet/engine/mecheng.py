"""Mechanical-engineering function library, phase 1 (spec 033): mechanics of materials.

Section properties of plane shapes, beam deflection and maximum-moment cases, axial / bending /
thin-wall stress and Euler column buckling. Every function is a plain positional call in a math
region. Dimensional arguments must carry a unit of the right dimension (a bare number is an
error), dimensionless arguments must not carry one, and results are returned in SI base units.

Validity ranges (stated here, not enforced; no warning mechanism exists yet):
- hoop_stress / longitudinal_stress assume a thin wall (r/t of about 10 or more).
- euler_critical_load is the Euler value even below the transition slenderness
  (see euler_transition_slenderness).
- Beams are prismatic, linear-elastic, small deflection, single load case.

GUI-independent: no PySide6 import.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable

import sympy as sp

from .statistics import _deferred
from .syntax import StatementError
from .units import BASE_UNIT_BY_DIM, UNITS, Measured, UnitError, dims_to_text, measure

_m, _N, _Pa = UNITS["m"], UNITS["N"], UNITS["Pa"]

# Dimension vocabulary: name -> (SI unit expression, example unit shown in the hint).
_DIMS: dict[str, tuple[sp.Expr, str]] = {
    "length": (_m, "1 mm"),
    "area": (_m ** 2, "1 mm^2"),
    "length^3": (_m ** 3, "1 mm^3"),
    "second moment of area": (_m ** 4, "1 mm^4"),
    "force": (_N, "1 kN"),
    "force per length": (_N / _m, "1 kN/m"),
    "moment": (_N * _m, "1 N*m"),
    "pressure": (_Pa, "1 MPa"),
}
_DIM_KEYS = {name: measure(unit).dims for name, (unit, _) in _DIMS.items()}

DIMENSIONLESS = "dimensionless"


@dataclass(frozen=True)
class _Arg:
    name: str
    dim: str            # key of _DIMS or DIMENSIONLESS
    positive: bool      # must be greater than zero


def _a(name: str, dim: str, positive: bool = True) -> _Arg:
    return _Arg(name, dim, positive)


def _unit_for(dims: tuple[tuple[str, int], ...]) -> sp.Expr:
    out: sp.Expr = sp.Integer(1)
    for name, exp in dims:
        out = out * BASE_UNIT_BY_DIM[name] ** exp
    return out


def _real_number(fn: str, arg: _Arg, mag: sp.Expr) -> sp.Expr:
    if not (mag.is_number and mag.is_real):
        raise StatementError(f"{fn}: {arg.name} must be a real number")
    if arg.positive and not mag > 0:
        raise StatementError(f"{fn}: {arg.name} must be greater than zero")
    return mag


def _check_arg(fn: str, arg: _Arg, value) -> sp.Expr:
    """Return the SI magnitude of ``value`` after checking its dimension against ``arg``."""
    try:
        m: Measured = measure(sp.sympify(value))
    except UnitError as exc:
        raise StatementError(f"{fn}: {arg.name} has inconsistent units ({exc})") from None
    if arg.dim == DIMENSIONLESS:
        if m.dims:
            raise StatementError(f"{fn}: {arg.name} must be dimensionless")
        return _real_number(fn, arg, sp.sympify(m.magnitude))
    if not m.dims:
        example = _DIMS[arg.dim][1]
        raise StatementError(f"{fn}: {arg.name} needs a unit of {arg.dim}, for example {example}")
    if m.dims != _DIM_KEYS[arg.dim]:
        raise StatementError(
            f"{fn}: {arg.name} must be a {arg.dim}, not {dims_to_text(m.dims)}")
    return _real_number(fn, arg, sp.sympify(m.magnitude))


def _make(name: str, args: list[_Arg], result: str, formula: Callable,
          order: tuple[str, str] | None = None) -> Callable:
    """Build the checked, deferred builtin.

    ``formula`` takes the SI magnitudes (parameters named like ``args``) and returns the SI
    magnitude. ``order=(a, b)`` additionally requires argument ``a`` to exceed argument ``b``.
    """
    n = len(args)

    def checked(*given):
        if len(given) != n:
            raise TypeError(f"{name}() takes {n} positional arguments but {len(given)} were given")
        vals = [_check_arg(name, spec, v) for spec, v in zip(args, given)]
        if order is not None:
            names = [a.name for a in args]
            if not vals[names.index(order[0])] > vals[names.index(order[1])]:
                raise StatementError(f"{name}: {order[0]} must be larger than {order[1]}")
        value = formula(*vals)
        if result == DIMENSIONLESS:
            return value
        return value * _DIMS[result][0]

    checked.__name__ = name
    checked.__doc__ = formula.__doc__
    checked.__signature__ = inspect.signature(formula)   # argument names for the call hint
    return _deferred(name, checked)


_pi = sp.pi
_S = sp.Integer

_SPEC = [
    # --- section properties (about the centroidal axis) ---
    ("rect_area", [_a("b", "length"), _a("h", "length")], "area",
     lambda b, h: b * h, None),
    ("rect_inertia", [_a("b", "length"), _a("h", "length")], "second moment of area",
     lambda b, h: b * h ** 3 / 12, None),
    ("rect_section_modulus", [_a("b", "length"), _a("h", "length")], "length^3",
     lambda b, h: b * h ** 2 / 6, None),
    ("circle_area", [_a("d", "length")], "area",
     lambda d: _pi * d ** 2 / 4, None),
    ("circle_inertia", [_a("d", "length")], "second moment of area",
     lambda d: _pi * d ** 4 / 64, None),
    ("circle_polar_inertia", [_a("d", "length")], "second moment of area",
     lambda d: _pi * d ** 4 / 32, None),
    ("circle_section_modulus", [_a("d", "length")], "length^3",
     lambda d: _pi * d ** 3 / 32, None),
    ("ring_area", [_a("do", "length"), _a("di", "length")], "area",
     lambda do, di: _pi * (do ** 2 - di ** 2) / 4, ("do", "di")),
    ("ring_inertia", [_a("do", "length"), _a("di", "length")], "second moment of area",
     lambda do, di: _pi * (do ** 4 - di ** 4) / 64, ("do", "di")),
    ("ring_section_modulus", [_a("do", "length"), _a("di", "length")], "length^3",
     lambda do, di: _pi * (do ** 4 - di ** 4) / (32 * do), ("do", "di")),
    ("radius_of_gyration", [_a("I", "second moment of area"), _a("A", "area")], "length",
     lambda I, A: sp.sqrt(I / A), None),
    # --- beams ---
    ("cantilever_tip_deflection",
     [_a("P", "force", False), _a("L", "length"), _a("E", "pressure"),
      _a("I", "second moment of area")], "length",
     lambda P, L, E, I: P * L ** 3 / (3 * E * I), None),
    ("cantilever_udl_deflection",
     [_a("w", "force per length", False), _a("L", "length"), _a("E", "pressure"),
      _a("I", "second moment of area")], "length",
     lambda w, L, E, I: w * L ** 4 / (8 * E * I), None),
    ("simply_supported_center_deflection",
     [_a("P", "force", False), _a("L", "length"), _a("E", "pressure"),
      _a("I", "second moment of area")], "length",
     lambda P, L, E, I: P * L ** 3 / (48 * E * I), None),
    ("simply_supported_udl_deflection",
     [_a("w", "force per length", False), _a("L", "length"), _a("E", "pressure"),
      _a("I", "second moment of area")], "length",
     lambda w, L, E, I: 5 * w * L ** 4 / (384 * E * I), None),
    ("cantilever_tip_max_moment", [_a("P", "force", False), _a("L", "length")], "moment",
     lambda P, L: P * L, None),
    ("cantilever_udl_max_moment", [_a("w", "force per length", False), _a("L", "length")],
     "moment", lambda w, L: w * L ** 2 / 2, None),
    ("simply_supported_center_max_moment",
     [_a("P", "force", False), _a("L", "length")], "moment",
     lambda P, L: P * L / 4, None),
    ("simply_supported_udl_max_moment",
     [_a("w", "force per length", False), _a("L", "length")], "moment",
     lambda w, L: w * L ** 2 / 8, None),
    # --- stress and strain ---
    ("axial_stress", [_a("F", "force", False), _a("A", "area")], "pressure",
     lambda F, A: F / A, None),
    ("axial_strain", [_a("dL", "length", False), _a("L", "length")], DIMENSIONLESS,
     lambda dL, L: dL / L, None),
    ("axial_elongation",
     [_a("F", "force", False), _a("L", "length"), _a("A", "area"), _a("E", "pressure")],
     "length", lambda F, L, A, E: F * L / (A * E), None),
    ("bending_stress",
     [_a("M", "moment", False), _a("c", "length", False), _a("I", "second moment of area")],
     "pressure", lambda M, c, I: M * c / I, None),
    ("hoop_stress",
     [_a("p", "pressure", False), _a("r", "length"), _a("t", "length")], "pressure",
     lambda p, r, t: p * r / t, None),
    ("longitudinal_stress",
     [_a("p", "pressure", False), _a("r", "length"), _a("t", "length")], "pressure",
     lambda p, r, t: p * r / (2 * t), None),
    # --- columns (Euler buckling) ---
    ("euler_critical_load",
     [_a("E", "pressure"), _a("I", "second moment of area"), _a("L", "length"),
      _a("K", DIMENSIONLESS)], "force",
     lambda E, I, L, K: _pi ** 2 * E * I / (K * L) ** 2, None),
    ("slenderness_ratio",
     [_a("L", "length"), _a("K", DIMENSIONLESS), _a("r", "length")], DIMENSIONLESS,
     lambda L, K, r: K * L / r, None),
    ("euler_transition_slenderness", [_a("E", "pressure"), _a("sy", "pressure")],
     DIMENSIONLESS, lambda E, sy: sp.sqrt(2 * _pi ** 2 * E / sy), None),
]

MECH_BUILTINS: dict[str, Callable] = {
    name: _make(name, args, result, formula, order)
    for name, args, result, formula, order in _SPEC
}

__all__ = ["MECH_BUILTINS"]
