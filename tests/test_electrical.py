"""Spec 034 phase 1A: electrical-engineering function library (engine part) and unit prerequisites."""

from pathlib import Path

import pytest

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import signature_for
from livesheet.engine.electrical import ELEC_BUILTINS
from livesheet.engine.units import UNITS


def run(*lines: str):
    return Engine().evaluate([(i, s) for i, s in enumerate(lines)])[len(lines) - 1]


def value(src: str) -> float:
    res = run(src)
    assert res.status == "ok", res.error
    text = res.output.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        text = text.replace(sup, ch)
    return float(text)


def err(src: str) -> str:
    res = run(src)
    assert res.status == "error", res.output
    return res.error


# --- registration -----------------------------------------------------------------------------

def test_17_names_registered():
    assert len(ELEC_BUILTINS) == 17
    for name in ELEC_BUILTINS:
        assert name in evaluator.BUILTINS


def test_no_name_collisions():
    names = set(ELEC_BUILTINS)
    others = (set(evaluator.BUILTINS) - names) | set(UNITS)
    others |= evaluator._ENTRYWISE_KEYWORDS | evaluator._SCALAR_KEYWORDS
    assert not names & others


def test_engine_module_has_no_qt():
    src = Path(__file__).parent.parent / "livesheet" / "engine" / "electrical.py"
    assert not [l for l in src.read_text().splitlines() if l.startswith(("import", "from")) and "PySide6" in l]


def test_signature_hints():
    assert signature_for("average_power") == "average_power(Vrms, Irms, phi)"
    assert signature_for("voltage_divider") == "voltage_divider(Vin, R1, R2)"


def test_wrong_argument_count():
    assert "Wrong number of arguments" in err("apparent_power(230 V) =")


def test_undefined_names():
    assert err("voltage_divider(Vin, R1, R2) =") == "R1, R2, Vin are not defined"


# --- unit rules -------------------------------------------------------------------------------

def test_bare_number_rejected():
    assert err("voltage_divider(12, 1 kohm, 3 kohm) =") == \
        "voltage_divider: Vin needs a unit of voltage, for example 1 V"


def test_wrong_dimension():
    assert err("voltage_divider(12 V, 1 kohm, 3 A) =") == \
        "voltage_divider: R2 must be a resistance, not A"


def test_angle_rule():
    assert err("average_power(230 V, 10 A, 60 V) =") == \
        "average_power: phi must be an angle in radians, not V"
    assert value("average_power(230 V, 10 A, pi/3) = W") == pytest.approx(1150, rel=1e-6)
    assert value("average_power(230 V, 10 A, 1 rad) = W") == pytest.approx(1242.7, rel=1e-4)


def test_turns_rule():
    assert err("transformer_secondary_voltage(230 V, 1000 A, 100) =") == \
        "transformer_secondary_voltage: Np must be a plain number of turns, not A"
    assert err("transformer_secondary_voltage(230 V, 0, 100) =") == \
        "transformer_secondary_voltage: Np must be greater than zero"


def test_mixed_units():
    assert value("voltage_divider(12 V, 1 kohm, 3000 ohm) = V") == pytest.approx(9)
    assert value("voltage_divider(0.012 kV, 1000 ohm, 3 kohm) = V") == pytest.approx(9)


# --- AC magnitudes and power ------------------------------------------------------------------

def test_rms_peak():
    assert value("rms_from_peak(325 V) = V") == pytest.approx(229.8097, rel=1e-5)
    assert value("peak_from_rms(230 V) = V") == pytest.approx(325.2691, rel=1e-5)


def test_ac_power():
    assert value("apparent_power(230 V, 10 A) = VA") == pytest.approx(2300)
    assert value("reactive_power(230 V, 10 A, pi/3) = var") == pytest.approx(1991.858, rel=1e-5)   # display is 6 significant digits
    assert value("power_factor(pi/3) =") == pytest.approx(0.5)
    assert run("apparent_power(230 V, 10 A) = VA").output.endswith("VA")
    assert run("reactive_power(230 V, 10 A, pi/3) = var").output.endswith("var")


def test_power_triangle():
    assert value("apparent_power(230 V, 10 A)^2 - average_power(230 V, 10 A, pi/3)^2 "
                 "- reactive_power(230 V, 10 A, pi/3)^2 =") == pytest.approx(0, abs=1e-6)


def test_degrees_unit_is_dimensionless_angle():
    assert value("power_factor(60 deg) =") == pytest.approx(0.5)


# --- networks, three-phase, transformers ------------------------------------------------------

def test_resistor_networks():
    assert value("resistors_series([10 ohm; 22 ohm; 33 ohm]) = ohm") == 65
    assert value("resistors_parallel([10 ohm; 10 ohm]) = ohm") == 5
    assert value("resistors_parallel([100 ohm; 200 ohm; 300 ohm]) = ohm") == pytest.approx(54.54545, rel=1e-6)
    assert value("voltage_divider(12 V, 1 kohm, 3 kohm) = V") == pytest.approx(9)
    assert value("current_divider(10 mA, 1 kohm, 1 kohm) = mA") == pytest.approx(5)


def test_network_errors():
    assert err("resistors_parallel([-100 ohm; 200 ohm]) =") == "resistors_parallel: R must be greater than zero"
    assert err("resistors_series([10 ohm; 5 V]) =") == "resistors_series: R must be a resistance, not V"
    assert err("resistors_series([1 ohm, 2 ohm; 3 ohm, 4 ohm]) =") == "resistors_series: R must be a vector"


def test_three_phase():
    assert value("wye_line_voltage(230 V) = V") == pytest.approx(398.3717, rel=1e-6)
    assert value("wye_phase_voltage(400 V) = V") == pytest.approx(230.9401, rel=1e-6)
    assert value("delta_line_current(10 A) = A") == pytest.approx(17.32051, rel=1e-6)
    assert value("three_phase_power(400 V, 10 A, pi/6) = W") == pytest.approx(6000, rel=1e-6)


def test_transformers():
    assert value("transformer_secondary_voltage(230 V, 1000, 100) = V") == pytest.approx(23)
    assert value("transformer_secondary_current(2 A, 1000, 100) = A") == pytest.approx(20)
    assert value("reflected_impedance(8 ohm, 1000, 100) = ohm") == pytest.approx(800)


def test_works_in_user_function_body():
    res = Engine().evaluate([(0, "f(a) := voltage_divider(a, 1 kohm, 3 kohm)"), (1, "f(12 V) = V")])
    assert res[1].status == "ok" and res[1].output == "= 9 V"


def test_complex_values_with_units_display():
    assert run("((3+4*I) V) * (2 A) = VA").output == "= 6 + 8i VA"
    assert value("abs((3+4*I) ohm) = ohm") == 5


# --- unit prerequisites -----------------------------------------------------------------------

def test_new_units():
    assert value("1 mH = H") == pytest.approx(1e-3)
    assert value("1 pF = F") == pytest.approx(1e-12)
    assert value("1 uH = H") == pytest.approx(1e-6)
    assert value("1 nH = H") == pytest.approx(1e-9)
    assert run("2300 W = VA").output == "= 2300 VA"
