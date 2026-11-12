"""Electrical-engineering function library, phase 1A (spec 034).

Resistor networks, RMS / peak, AC power, balanced three-phase and ideal-transformer relations.
Every function is a plain positional call in a math region. Dimensional arguments must carry a
unit of the right dimension (a bare number is an error), angles are radians (plain numbers or
``pi`` expressions; any unit that is not dimensionless is an error), turns are plain positive
numbers, and results are returned in SI base units (power results as W, displayable as VA / var).

Assumptions (stated, not enforced): sinusoidal steady state, balanced three-phase loads and
supply, ideal transformer. GUI-independent: no PySide6 import.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable

import sympy as sp

from .statistics import _deferred
from .syntax import StatementError
from .units import UNITS, Measured, UnitError, dims_to_text, measure

# Dimension vocabulary: name -> (SI unit expression, example unit shown in the hint).
_DIMS: dict[str, tuple[sp.Expr, str]] = {
    "voltage": (UNITS["V"], "1 V"),
    "current": (UNITS["A"], "1 A"),
    "resistance": (UNITS["ohm"], "1 ohm"),
}
_DIM_KEYS = {name: measure(unit).dims for name, (unit, _) in _DIMS.items()}
_POWER = UNITS["W"]

ANGLE = "angle"
TURNS = "turns"


@dataclass(frozen=True)
class _Arg:
    name: str
    dim: str            # key of _DIMS, ANGLE, TURNS
    positive: bool      # must be greater than zero
    vector: bool = False


def _a(name: str, dim: str, positive: bool = True, vector: bool = False) -> _Arg:
    return _Arg(name, dim, positive, vector)


def _scalar(fn: str, arg: _Arg, value) -> sp.Expr:
    """SI magnitude of a single value after the dimension check."""
    try:
        m: Measured = measure(sp.sympify(value))
    except UnitError as exc:
        raise StatementError(f"{fn}: {arg.name} has inconsistent units ({exc})") from None
    if arg.dim == ANGLE:
        if m.dims:
            raise StatementError(f"{fn}: {arg.name} must be an angle in radians, not "
                                 f"{dims_to_text(m.dims)}")
    elif arg.dim == TURNS:
        if m.dims:
            raise StatementError(f"{fn}: {arg.name} must be a plain number of turns, not "
                                 f"{dims_to_text(m.dims)}")
    elif not m.dims:
        raise StatementError(
            f"{fn}: {arg.name} needs a unit of {arg.dim}, for example {_DIMS[arg.dim][1]}")
    elif m.dims != _DIM_KEYS[arg.dim]:
        raise StatementError(f"{fn}: {arg.name} must be a {arg.dim}, not {dims_to_text(m.dims)}")
    mag = sp.sympify(m.magnitude)
    if not (mag.is_number and mag.is_real):
        raise StatementError(f"{fn}: {arg.name} must be a real number")
    if arg.positive and not mag > 0:
        raise StatementError(f"{fn}: {arg.name} must be greater than zero")
    return mag


def _check_arg(fn: str, arg: _Arg, value):
    if not arg.vector:
        return _scalar(fn, arg, value)
    value = sp.sympify(value)
    if isinstance(value, sp.MatrixBase):
        if value.rows != 1 and value.cols != 1 and value.rows * value.cols:
            raise StatementError(f"{fn}: {arg.name} must be a vector")
        items = list(value)
    else:
        items = [value]
    if not items:
        raise StatementError(f"{fn}: needs at least one resistance")
    return [_scalar(fn, arg, v) for v in items]


def _make(name: str, args: list[_Arg], result: str | None, formula: Callable) -> Callable:
    """Build the checked, deferred builtin. ``result`` is an SI unit expression or None."""
    n = len(args)

    def checked(*given):
        if len(given) != n:
            raise TypeError(f"{name}() takes {n} positional arguments but {len(given)} were given")
        vals = [_check_arg(name, spec, v) for spec, v in zip(args, given)]
        value = formula(*vals)
        return value if result is None else value * result

    checked.__name__ = name
    checked.__doc__ = formula.__doc__
    checked.__signature__ = inspect.signature(formula)   # argument names for the call hint
    return _deferred(name, checked)


_s2 = sp.sqrt(2)
_s3 = sp.sqrt(3)
_V, _A, _OHM = UNITS["V"], UNITS["A"], UNITS["ohm"]

_SPEC = [
    # --- resistor networks ---
    ("resistors_series", [_a("R", "resistance", vector=True)], _OHM,
     lambda R: sum(R)),
    ("resistors_parallel", [_a("R", "resistance", vector=True)], _OHM,
     lambda R: 1 / sum(1 / r for r in R)),
    ("voltage_divider",
     [_a("Vin", "voltage", False), _a("R1", "resistance"), _a("R2", "resistance")], _V,
     lambda Vin, R1, R2: Vin * R2 / (R1 + R2)),
    ("current_divider",
     [_a("Itot", "current", False), _a("R1", "resistance"), _a("R2", "resistance")], _A,
     lambda Itot, R1, R2: Itot * R2 / (R1 + R2)),
    # --- RMS / peak ---
    ("rms_from_peak", [_a("Vpk", "voltage")], _V, lambda Vpk: Vpk / _s2),
    ("peak_from_rms", [_a("Vrms", "voltage")], _V, lambda Vrms: _s2 * Vrms),
    # --- AC power ---
    ("average_power",
     [_a("Vrms", "voltage"), _a("Irms", "current"), _a("phi", ANGLE, False)], _POWER,
     lambda Vrms, Irms, phi: Vrms * Irms * sp.cos(phi)),
    ("apparent_power", [_a("Vrms", "voltage"), _a("Irms", "current")], _POWER,
     lambda Vrms, Irms: Vrms * Irms),
    ("reactive_power",
     [_a("Vrms", "voltage"), _a("Irms", "current"), _a("phi", ANGLE, False)], _POWER,
     lambda Vrms, Irms, phi: Vrms * Irms * sp.sin(phi)),
    ("power_factor", [_a("phi", ANGLE, False)], None, lambda phi: sp.cos(phi)),
    # --- balanced three-phase ---
    ("wye_line_voltage", [_a("Vph", "voltage")], _V, lambda Vph: _s3 * Vph),
    ("wye_phase_voltage", [_a("Vline", "voltage")], _V, lambda Vline: Vline / _s3),
    ("delta_line_current", [_a("Iph", "current")], _A, lambda Iph: _s3 * Iph),
    ("three_phase_power",
     [_a("VL", "voltage"), _a("IL", "current"), _a("phi", ANGLE, False)], _POWER,
     lambda VL, IL, phi: _s3 * VL * IL * sp.cos(phi)),
    # --- ideal transformer ---
    ("transformer_secondary_voltage",
     [_a("Vp", "voltage", False), _a("Np", TURNS), _a("Ns", TURNS)], _V,
     lambda Vp, Np, Ns: Vp * Ns / Np),
    ("transformer_secondary_current",
     [_a("Ip", "current", False), _a("Np", TURNS), _a("Ns", TURNS)], _A,
     lambda Ip, Np, Ns: Ip * Np / Ns),
    ("reflected_impedance",
     [_a("Zs", "resistance"), _a("Np", TURNS), _a("Ns", TURNS)], _OHM,
     lambda Zs, Np, Ns: Zs * (Np / Ns) ** 2),
]

ELEC_BUILTINS: dict[str, Callable] = {
    name: _make(name, args, result, formula) for name, args, result, formula in _SPEC
}

__all__ = ["ELEC_BUILTINS"]
