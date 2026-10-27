"""Unit namespace and dimensional analysis for LiveSheet.

Units are built on the seven SI base quantities from ``sympy.physics.units``.
Every other unit is an ordinary SymPy expression in those base quantities
(``km`` is ``1000*meter``), so unit arithmetic is plain symbolic algebra and
dimension checking is delegated to SymPy's SI unit system.

Angles are dimensionless (``deg = pi/180``), as in Mathcad.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from sympy.physics import units as u
from sympy.physics.units.systems.si import SI, dimsys_SI

# --- base quantities -------------------------------------------------------

m = u.meter
kg = u.kilogram
s = u.second
A = u.ampere
K = u.kelvin
mol = u.mole
cd = u.candela

BASE_ORDER = [
    ("mass", "kg"),
    ("length", "m"),
    ("time", "s"),
    ("current", "A"),
    ("temperature", "K"),
    ("amount_of_substance", "mol"),
    ("luminous_intensity", "cd"),
]

BASE_UNIT_BY_DIM = {
    "mass": kg, "length": m, "time": s, "current": A,
    "temperature": K, "amount_of_substance": mol, "luminous_intensity": cd,
}

# SymPy measures mass internally in grams (kilogram has scale factor 1000).
_INTERNAL_SCALE = {"mass": sp.Integer(1000)}

# --- derived units ---------------------------------------------------------

N = kg * m / s**2
J = N * m
W = J / s
Pa = N / m**2
C = A * s
V = W / A
ohm = V / A
F = C / V
Wb = V * s
T = Wb / m**2
H = Wb / A
Hz = 1 / s

_k, _M, _G = sp.Integer(10) ** 3, sp.Integer(10) ** 6, sp.Integer(10) ** 9
_c, _ml, _mu = sp.Rational(1, 100), sp.Rational(1, 1000), sp.Rational(1, 10**6)

UNITS: dict[str, sp.Expr] = {
    # length
    "m": m, "km": _k * m, "cm": _c * m, "mm": _ml * m, "um": _mu * m, "μm": _mu * m,
    "nm": sp.Rational(1, 10**9) * m,
    "inch": sp.Rational(254, 10000) * m, "ft": sp.Rational(3048, 10000) * m,
    "yd": sp.Rational(9144, 10000) * m, "mi": sp.Rational(1609344, 1000) * m,
    # area / volume
    "ha": 10**4 * m**2, "L": _ml * m**3, "mL": _mu * m**3,
    # mass
    "kg": kg, "gm": _ml * kg, "mg": _mu * kg, "tonne": 1000 * kg,
    "lb": sp.Rational(45359237, 10**8) * kg,
    # time
    "s": s, "ms": _ml * s, "min": 60 * s, "hr": 3600 * s, "day": 86400 * s,
    "week": 7 * 86400 * s, "yr": sp.Rational(36525, 100) * 86400 * s,
    # force
    "N": N, "kN": _k * N, "MN": _M * N, "lbf": sp.Rational(45359237, 10**8) * sp.Rational(980665, 10**5) * N,
    # pressure
    "Pa": Pa, "kPa": _k * Pa, "MPa": _M * Pa, "GPa": _G * Pa, "bar": 10**5 * Pa,
    "mbar": 100 * Pa, "atm": 101325 * Pa,
    "psi": sp.Rational(45359237, 10**8) * sp.Rational(980665, 10**5) * N / (sp.Rational(254, 10000) * m) ** 2,
    # energy / power
    "J": J, "kJ": _k * J, "MJ": _M * J, "GJ": _G * J, "Wh": 3600 * J, "kWh": 3600 * _k * J,
    "MWh": 3600 * _M * J, "cal": sp.Rational(4184, 1000) * J, "kcal": sp.Rational(4184, 1) * J,
    "W": W, "kW": _k * W, "MW": _M * W, "GW": _G * W,
    # electrical
    "A": A, "mA": _ml * A, "kA": _k * A, "V": V, "mV": _ml * V, "kV": _k * V,
    "ohm": ohm, "Ω": ohm, "kohm": _k * ohm, "kΩ": _k * ohm, "Mohm": _M * ohm, "MΩ": _M * ohm,
    "C": C, "F": F, "uF": _mu * F, "μF": _mu * F, "nF": sp.Rational(1, 10**9) * F,
    "Wb": Wb, "T": T, "H": H,
    # frequency
    "Hz": Hz, "kHz": _k * Hz, "MHz": _M * Hz, "GHz": _G * Hz,
    "rpm": 2 * sp.pi / (60 * s),
    # other base units
    "K": K, "mol": mol, "cd": cd,
    # angles (dimensionless)
    "rad": sp.Integer(1), "deg": sp.pi / 180, "°": sp.pi / 180,
    # constants
    "g": sp.Rational(980665, 10**5) * m / s**2,
}

# Derived units preferred for display, keyed by their base-dimension exponents.
_PREFERRED_DISPLAY = [
    ("N", N), ("J", J), ("W", W), ("Pa", Pa), ("C", C), ("V", V),
    ("Ω", ohm), ("F", F), ("Wb", Wb), ("T", T), ("H", H),
]

ABBREV = {
    u.meter: "m", u.kilogram: "kg", u.second: "s", u.ampere: "A",
    u.kelvin: "K", u.mole: "mol", u.candela: "cd",
}


class UnitError(ValueError):
    """Raised when an expression mixes incompatible dimensions."""


@dataclass(frozen=True)
class Measured:
    """A value split into a SI magnitude and base-dimension exponents."""

    magnitude: sp.Expr                 # numeric value in coherent SI units
    dims: tuple[tuple[str, int], ...]  # sorted (dimension, exponent) pairs, zero exponents dropped

    @property
    def dimensionless(self) -> bool:
        return not self.dims


def _dims_key(deps: dict) -> tuple[tuple[str, int], ...]:
    out = []
    for dim, exp in deps.items():
        name = getattr(dim, "name", dim)
        name = str(name)
        exp = sp.nsimplify(exp)
        if exp != 0:
            out.append((name, int(exp) if exp.is_integer else exp))
    return tuple(sorted(out))


# Functions that pass their argument's unit through instead of requiring 1.
_UNIT_TRANSPARENT = (sp.Abs, sp.Max, sp.Min, sp.re, sp.im, sp.conjugate, sp.sign)


def _check_function_args(expr) -> None:
    from sympy.core.function import AppliedUndef

    for fn in expr.atoms(sp.Function):
        if isinstance(fn, AppliedUndef) or isinstance(fn, _UNIT_TRANSPARENT):
            continue
        for arg in fn.args:
            if measure(arg).dims:
                raise UnitError(f"{fn.func.__name__}() needs a dimensionless argument")


def measure(expr: sp.Expr) -> Measured:
    """Split ``expr`` into SI magnitude and dimension, checking consistency."""
    expr = sp.sympify(expr)
    _check_function_args(expr)
    try:
        factor, dim = SI._collect_factor_and_dimension(expr)
    except ValueError as exc:  # sympy raises ValueError for mismatched dims
        raise UnitError(_friendly_unit_error(str(exc))) from None
    deps = dimsys_SI.get_dimensional_dependencies(dim)
    key = _dims_key(deps)
    for name, exp in key:
        scale = _INTERNAL_SCALE.get(name)
        if scale is not None:
            factor = factor / scale**exp
    return Measured(sp.nsimplify(factor) if factor.is_Rational else factor, key)


def _friendly_unit_error(msg: str) -> str:
    if "should be" in msg:
        return "Units do not match"
    if "dimensionless" in msg or "Dimension of" in msg:
        return "Function argument must be dimensionless"
    return "Unit error: " + msg


_preferred_cache: dict | None = None


def _preferred() -> dict:
    global _preferred_cache
    if _preferred_cache is None:
        _preferred_cache = {measure(expr).dims: name for name, expr in _PREFERRED_DISPLAY}
    return _preferred_cache


def dims_to_text(dims: tuple[tuple[str, int], ...]) -> str:
    """Render base dimensions as a unit string, e.g. ``kg·m²/s²`` or ``N``."""
    if not dims:
        return ""
    pref = _preferred().get(dims)
    if pref:
        return pref
    from .formatting import superscript

    lookup = dict(dims)
    num, den = [], []
    for name, sym in BASE_ORDER:
        exp = lookup.get(name)
        if not exp:
            continue
        target = num if exp > 0 else den
        e = abs(exp)
        target.append(sym if e == 1 else sym + superscript(e))
    if not num:
        return "·".join(
            sym + superscript(exp) for name, sym in BASE_ORDER
            if (exp := lookup.get(name)) and exp < 0
        )
    text = "·".join(num)
    if den:
        text += "/" + ("·".join(den) if len(den) == 1 else "(" + "·".join(den) + ")")
    return text


def is_unit_name(name: str) -> bool:
    return name in UNITS


__all__ = [
    "UNITS", "UnitError", "Measured", "measure", "dims_to_text", "ABBREV",
    "is_unit_name",
]
