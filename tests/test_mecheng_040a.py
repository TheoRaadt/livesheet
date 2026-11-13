"""Spec 040a: torsion of circular shafts and plane stress (Mohr), engine part."""

from math import atan2, cos, hypot, pi, sin
from pathlib import Path

import pytest

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import signature_for
from livesheet.engine.mecheng import MECH_BUILTINS
from livesheet.engine.units import UNITS

NAMES = ["shaft_max_shear_solid", "shaft_max_shear_hollow", "shaft_twist_solid",
         "shaft_twist_hollow", "shaft_power", "principal_stress_max", "principal_stress_min",
         "max_shear_stress", "principal_angle", "rotated_normal_stress", "rotated_shear_stress"]
S = "80 MPa, 20 MPa, 30 MPa"


def run(*lines):
    return Engine().evaluate([(i, s) for i, s in enumerate(lines)])[len(lines) - 1]


def value(src: str) -> float:
    res = run(src if "=" in src else src + " =")
    assert res.status == "ok", res.error
    text = res.output.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        text = text.replace(sup, ch)
    return float(text)


def err(src: str) -> str:
    res = run(src)
    assert res.status == "error", res.output
    return res.error


def si(src: str, unit: str) -> float:
    return value(f"{src} = {unit}")


def test_registration():
    assert len(NAMES) == 11
    for n in NAMES:
        assert n in MECH_BUILTINS and n in evaluator.BUILTINS
    others = (set(evaluator.BUILTINS) - set(MECH_BUILTINS)) | set(UNITS)
    others |= evaluator._ENTRYWISE_KEYWORDS | evaluator._SCALAR_KEYWORDS
    assert not set(NAMES) & others


def test_no_qt_and_hints():
    src = Path(__file__).parent.parent / "livesheet" / "engine" / "mecheng.py"
    assert "PySide6" not in "".join(l for l in src.read_text().splitlines() if l.startswith(("import", "from")))
    assert signature_for("shaft_twist_hollow") == "shaft_twist_hollow(torque, span, shear_mod, dia_o, dia_i)"
    assert signature_for("rotated_shear_stress") == "rotated_shear_stress(sx, sy, txy, theta)"


def test_wrong_arg_count():
    res = run("shaft_power(500 N*m)")
    assert res.status == "error" and "Traceback" not in res.error


def test_unit_errors():
    assert err("shaft_max_shear_solid(1000, 50 mm)") == \
        "shaft_max_shear_solid: torque needs a unit of moment, for example 1 N*m"
    assert err("shaft_power(500 N*m, 30 kg)") == "shaft_power: freq must be a frequency, not kg"
    assert "theta must be dimensionless" in err(f"rotated_normal_stress({S}, 1 m)")


def test_torsion_values():
    assert si("shaft_max_shear_solid(1 kN*m, 50 mm)", "MPa") == pytest.approx(40.7437, rel=1e-5)
    assert si("shaft_max_shear_hollow(1 kN*m, 50 mm, 30 mm)", "MPa") == pytest.approx(46.8103, rel=1e-5)
    assert value("shaft_twist_solid(1 kN*m, 1 m, 80 GPa, 50 mm)") == pytest.approx(0.0203718, rel=1e-5)
    assert value("shaft_twist_hollow(1 kN*m, 1 m, 80 GPa, 50 mm, 30 mm)") == pytest.approx(0.0234051, rel=1e-5)
    assert si("shaft_power(500 N*m, 30 Hz)", "kW") == pytest.approx(94.2478, rel=1e-5)


def test_torsion_cross_checks():
    a = si("shaft_max_shear_solid(1 kN*m, 50 mm)", "MPa")
    b = si("shaft_max_shear_hollow(1 kN*m, 50 mm, 30 mm)", "MPa")
    assert b / a == pytest.approx(6.25e6 / 5.44e6, rel=1e-5)
    p = value("shaft_twist_solid(1 kN*m, 1 m, 80 GPa, 50 mm)")
    q = value("shaft_twist_hollow(1 kN*m, 1 m, 80 GPa, 50 mm, 30 mm)")
    assert q / p == pytest.approx(6.25e6 / 5.44e6, rel=1e-5)


def test_power_accepts_inverse_seconds():
    assert si("shaft_power(500 N*m, 30 1/s)", "kW") == pytest.approx(94.2478, rel=1e-5)


def test_plane_stress_values():
    assert si(f"principal_stress_max({S})", "MPa") == pytest.approx(92.4264, rel=1e-5)
    assert si(f"principal_stress_min({S})", "MPa") == pytest.approx(7.57359, rel=1e-5)
    assert si(f"max_shear_stress({S})", "MPa") == pytest.approx(42.4264, rel=1e-5)
    assert value(f"principal_angle({S})") == pytest.approx(pi / 8, rel=1e-5)
    assert si(f"rotated_normal_stress({S}, pi/6)", "MPa") == pytest.approx(90.9808, rel=1e-5)
    assert si(f"rotated_shear_stress({S}, pi/6)", "MPa") == pytest.approx(-10.9808, rel=1e-5)


def test_plane_stress_invariants():
    s1 = si(f"principal_stress_max({S})", "MPa")
    s2 = si(f"principal_stress_min({S})", "MPa")
    assert s1 + s2 == pytest.approx(100, rel=1e-5)  # display rounds to 6 digits
    assert si(f"rotated_normal_stress({S}, pi/6 + pi/2)", "MPa") == pytest.approx(9.01924, rel=1e-5)
    assert si(f"rotated_shear_stress({S}, 0)", "MPa") == pytest.approx(30, rel=1e-9)
    assert si(f"rotated_normal_stress({S}, principal_angle({S}))", "MPa") == pytest.approx(s1, rel=1e-9)


def test_shear_zero_at_principal_angle():
    # the exact result is 0; the engine drops the unit of a zero (known limitation), so no "= MPa"
    assert value(f"rotated_shear_stress({S}, principal_angle({S}))") == 0


def test_principal_angle_range_and_quadrants():
    # sx < sy with positive shear: direction of s1 stays inside (-pi/2, pi/2]
    sx, sy, t = -40.0, 20.0, 25.0
    expect = 0.5 * atan2(2 * t, sx - sy)
    got = value("principal_angle(-40 MPa, 20 MPa, 25 MPa)")
    assert got == pytest.approx(expect, rel=1e-5) and -pi / 2 < got <= pi / 2
    assert value("principal_angle(80 MPa, 20 MPa, -30 MPa)") == pytest.approx(-pi / 8, rel=1e-5)


def test_errors():
    assert err("shaft_max_shear_solid(1 kN*m, -50 mm)") == "shaft_max_shear_solid: dia must be greater than zero"
    assert err("shaft_max_shear_hollow(1 kN*m, 30 mm, 50 mm)") == \
        "shaft_max_shear_hollow: dia_o must be larger than dia_i"
    assert err("shaft_twist_hollow(1 kN*m, 1 m, 80 GPa, 30 mm, 50 mm)") == \
        "shaft_twist_hollow: dia_o must be larger than dia_i"
    # "0 MPa" cannot reach the function with its unit (zero-unit drop, known limitation), so the
    # isotropic check is tested on the formula helper; through the engine the unit error shows.
    from livesheet.engine.mecheng import _principal_angle
    from livesheet.engine.syntax import StatementError
    with pytest.raises(StatementError, match="no unique principal direction"):
        _principal_angle(50, 50, 0)
    assert "txy needs a unit of pressure" in err("principal_angle(50 MPa, 50 MPa, 0 MPa) =")
    assert "freq, torque are not defined" in err("shaft_power(torque, freq) =")


def test_isotropic_with_shear_is_fine():
    assert value("principal_angle(50 MPa, 50 MPa, 10 MPa)") == pytest.approx(pi / 4, rel=1e-5)


def test_negative_torque_gives_negative_shear():
    assert si("shaft_max_shear_solid(-1 kN*m, 50 mm)", "MPa") == pytest.approx(-40.7437, rel=1e-5)


def test_phase1_bounds_unchanged():
    assert err("rect_area(1 m, -1 m)") == "rect_area: h must be greater than zero"
    assert si("axial_stress(-1 kN, 10 mm^2)", "MPa") == pytest.approx(-100, rel=1e-9)
