"""Spec 040b: statics (two forces) and 1-DOF vibration, engine part."""

from math import log, pi, sqrt
from pathlib import Path

import pytest

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import signature_for
from livesheet.engine.mecheng import MECH_BUILTINS
from livesheet.engine.units import UNITS

NAMES = ["resultant_two_forces", "resultant_direction", "force_x_component",
         "force_y_component", "friction_limit", "natural_angular_frequency",
         "natural_frequency_hz", "damped_angular_frequency", "damping_ratio",
         "critical_damping", "log_decrement", "damping_ratio_from_log_decrement"]


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


def test_registration():
    assert len(NAMES) == 12
    for n in NAMES:
        assert n in MECH_BUILTINS and n in evaluator.BUILTINS
    others = (set(evaluator.BUILTINS) - set(MECH_BUILTINS)) | set(UNITS)
    others |= evaluator._ENTRYWISE_KEYWORDS | evaluator._SCALAR_KEYWORDS
    assert not set(NAMES) & others


def test_no_qt_and_hints():
    src = Path(__file__).parent.parent / "livesheet" / "engine" / "mecheng.py"
    assert "PySide6" not in "".join(
        l for l in src.read_text().splitlines() if l.startswith(("import", "from")))
    assert signature_for("damping_ratio") == "damping_ratio(damping, stiffness, mass)"
    assert signature_for("resultant_two_forces") == "resultant_two_forces(P1, P2, theta)"


def test_wrong_arg_count():
    res = run("friction_limit(0.3)")
    assert res.status == "error" and "Traceback" not in res.error


def test_unit_errors():
    assert err("resultant_two_forces(300, 400 N, pi/2)") == \
        "resultant_two_forces: P1 needs a unit of force, for example 1 kN"
    assert err("natural_frequency_hz(8 kN/m, 2 m)") == \
        "natural_frequency_hz: mass must be a mass, not m"
    assert err("damped_angular_frequency(100 rad/s, 0.3 m)") == \
        "damped_angular_frequency: zeta must be dimensionless"
    assert err("friction_limit(0.3 N, 2 kN)") == "friction_limit: mu must be dimensionless"
    assert "needs a unit of stiffness" in err("critical_damping(8, 2 kg)")
    assert "needs a unit of damping coefficient" in err("damping_ratio(40, 8 kN/m, 2 kg)")


def test_statics():
    assert value("resultant_two_forces(300 N, 400 N, pi/2) = N") == pytest.approx(500, rel=1e-5)
    assert value("resultant_two_forces(300 N, 400 N, pi/3) = N") == pytest.approx(sqrt(370000), rel=1e-5)
    assert value("resultant_two_forces(300 N, 400 N, 0) = N") == pytest.approx(700, rel=1e-9)
    assert value("resultant_two_forces(300 N, 400 N, pi) = N") == pytest.approx(100, rel=1e-9)
    assert value("resultant_direction(300 N, 400 N, pi/2)") == pytest.approx(0.927295, rel=1e-5)
    fx = value("force_x_component(500 N, pi/3) = N")
    fy = value("force_y_component(500 N, pi/3) = N")
    assert fx == pytest.approx(250, rel=1e-5) and fy == pytest.approx(433.013, rel=1e-5)
    assert fx ** 2 + fy ** 2 == pytest.approx(250000, rel=1e-5)
    assert value("friction_limit(0.3, 2 kN) = N") == pytest.approx(600, rel=1e-9)
    assert value("friction_limit(0.3, 2 kN) = kN") == pytest.approx(0.6, rel=1e-9)


def test_vibration():
    wn = value("natural_angular_frequency(8 kN/m, 2 kg) = 1/s")
    assert wn == pytest.approx(63.2456, rel=1e-5)
    fn = value("natural_frequency_hz(8 kN/m, 2 kg) = Hz")
    assert fn == pytest.approx(10.0658, rel=1e-5)
    assert fn * 2 * pi == pytest.approx(sqrt(4000), rel=1e-5)
    assert value("damped_angular_frequency(100 rad/s, 0.3) = 1/s") == pytest.approx(95.3939, rel=1e-5)
    assert value("damped_angular_frequency(100 rad/s, 0) = 1/s") == pytest.approx(100, rel=1e-9)
    z = value("damping_ratio(40 N*s/m, 8 kN/m, 2 kg)")
    assert z == pytest.approx(0.158114, rel=1e-5)
    cc = value("critical_damping(8 kN/m, 2 kg) = N*s/m")
    assert cc == pytest.approx(252.982, rel=1e-5)
    assert z == pytest.approx(40 / cc, rel=1e-5)
    assert value("log_decrement(10 mm, 4 mm)") == pytest.approx(log(2.5), rel=1e-5)
    d = value("damping_ratio_from_log_decrement(0.916291)")
    assert d == pytest.approx(0.144306, rel=1e-5)
    assert value("damping_ratio_from_log_decrement(log_decrement(10 mm, 4 mm))") == \
        pytest.approx(d, rel=1e-5)


def test_direct_precision():
    f = MECH_BUILTINS
    assert float(Engine().evaluate([(0, "natural_frequency_hz(8 kN/m, 2 kg) = Hz")])[0].output.split()[1]) \
        == pytest.approx(sqrt(4000) / (2 * pi), rel=1e-5)
    assert set(f) >= set(NAMES)


def test_errors():
    assert err("damped_angular_frequency(100 rad/s, -0.3)") == \
        "damped_angular_frequency: zeta must not be negative"
    assert err("damped_angular_frequency(100 rad/s, 1)") == \
        "damped_angular_frequency: zeta must be less than one"
    assert err("log_decrement(4 mm, 10 mm)") == "log_decrement: x1 must be larger than x2"
    assert err("resultant_direction(300 N, 300 N, pi)") == \
        "resultant_direction: resultant is zero, direction undefined"
    assert err("natural_frequency_hz(8 kN/m, -2 kg)") == \
        "natural_frequency_hz: mass must be greater than zero"
    assert err("damping_ratio_from_log_decrement(0)") == \
        "damping_ratio_from_log_decrement: delta must be greater than zero"
    assert "not defined" in err("natural_frequency_hz(stiffness, mass) =")
