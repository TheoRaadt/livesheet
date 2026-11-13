"""Spec 034 phase 1B: phasors, impedance, transients, resonance, RC filters (engine part)."""

import math
from pathlib import Path

import sympy as sp

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import signature_for
from livesheet.engine.electrical import ELEC_BUILTINS
from livesheet.engine.units import UNITS

NAMES_1B = [
    "phasor", "phasor_magnitude", "phasor_angle", "impedance_resistor", "impedance_inductor",
    "impedance_capacitor", "impedance_series", "impedance_parallel", "angular_frequency",
    "rc_time_constant", "rl_time_constant", "rc_charge_voltage", "rl_current_rise",
    "resonant_frequency", "series_rlc_quality_factor", "series_rlc_bandwidth",
    "rc_lowpass_cutoff", "rc_lowpass_gain", "rc_highpass_gain",
]


def run(*lines: str):
    return Engine().evaluate([(i, s) for i, s in enumerate(lines)])[len(lines) - 1]


def value(*lines: str) -> float:
    res = run(*lines)
    assert res.status == "ok", res.error
    text = res.output.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        text = text.replace(sup, ch)
    return float(text)


def err(src: str) -> str:
    res = run(src)
    assert res.status == "error", res.output
    return res.error


def close(a: float, b: float, rel: float = 1e-5) -> bool:
    return math.isclose(a, b, rel_tol=rel)


# --- registration -----------------------------------------------------------------------------

def test_registration_and_collisions():
    assert len(NAMES_1B) == 19
    for n in NAMES_1B:
        assert n in ELEC_BUILTINS and n in evaluator.BUILTINS
    names = set(ELEC_BUILTINS)
    others = (set(evaluator.BUILTINS) - names) | set(UNITS)
    others |= evaluator._ENTRYWISE_KEYWORDS | evaluator._SCALAR_KEYWORDS
    assert not names & others


def test_signature_hints():
    assert signature_for("phasor") == "phasor(mag, phi)"
    assert signature_for("impedance_inductor") == "impedance_inductor(f, L)"
    assert signature_for("rc_charge_voltage") == "rc_charge_voltage(Vs, t, R, C)"


def test_wrong_argument_count():
    assert "Wrong number of arguments" in err("rc_time_constant(1 kohm) =")


# --- phasors and impedance --------------------------------------------------------------------

def test_phasor_parts():
    assert close(value("z := phasor(10 V, pi/6)", "re(z) = V"), 8.660254)
    assert close(value("z := phasor(10 V, pi/6)", "im(z) = V"), 5)
    assert close(value("phasor_magnitude(phasor(10 V, pi/6)) = V"), 10)
    assert close(value("phasor_angle(phasor(10 V, pi/6)) ="), math.pi / 6, 1e-5)
    assert abs(float(ELEC_BUILTINS["phasor_angle"](ELEC_BUILTINS["phasor"](10 * UNITS["V"], sp.pi / 6)))
               - math.pi / 6) < 1e-9


def test_phasor_keeps_unit_and_prefix():
    assert close(value("phasor_magnitude(phasor(3 kV, 1)) = kV"), 3)


def test_phasor_angle_range():
    assert close(value("phasor_angle(phasor(1 A, 3*pi/2)) ="), -math.pi / 2, 1e-5)


def test_phasor_errors():
    assert err("phasor(2 A, 60 V) =") == "phasor: phi must be an angle in radians, not V"
    assert "z must not be zero" in err("phasor_angle(0 V) =")


def test_impedance_inductor_capacitor():
    assert close(value("im(impedance_inductor(50 Hz, 0.1 H)) = ohm"), 31.41593)
    res = run("impedance_inductor(50 Hz, 0.1 H) =")   # pure imaginary, real part 0
    assert res.status == "ok" and res.output.startswith("= 31.4159i")
    assert close(value("im(impedance_capacitor(50 Hz, 100 uF)) = ohm"), -31.83099)
    assert close(value("impedance_resistor(4.7 kohm) = kohm"), 4.7)


def test_impedance_prefixed_inputs():
    assert close(value("im(impedance_inductor(0.05 kHz, 100 mH)) = ohm"), 31.41593)


def test_impedance_series_parallel():
    assert close(value("phasor_magnitude(impedance_series([10 ohm; "
                       "impedance_inductor(50 Hz, 0.1 H)])) = ohm"), 32.96908)
    assert close(value("impedance_parallel([10 ohm; 10 ohm]) = ohm"), 5)
    assert close(value("impedance_series([10 ohm; 22 ohm; 33 ohm]) = ohm"), 65)
    res = run("impedance_parallel([10 ohm; impedance_capacitor(50 Hz, 100 uF)]) = ohm")
    assert res.status == "ok" and "9.1017" in res.output and "2.85938" in res.output


def test_angular_frequency():
    assert close(value("angular_frequency(50 Hz) ="), 314.1593)


def test_impedance_errors():
    assert err("impedance_capacitor(-50 Hz, 100 uF) =") == \
        "impedance_capacitor: f must be greater than zero"
    assert "z must not contain a zero" in err("impedance_parallel([0 ohm; 5 ohm]) =")
    assert "needs a unit of frequency" in err("impedance_inductor(50, 0.1 H) =")
    assert "L must be a inductance" in err("impedance_inductor(50 Hz, 0.1 V) =")


# --- transients -------------------------------------------------------------------------------

def test_time_constants():
    assert close(value("rc_time_constant(1 kohm, 10 uF) = s"), 0.01)
    assert close(value("rl_time_constant(0.5 H, 10 ohm) = s"), 0.05)


def test_step_responses():
    assert close(value("rc_charge_voltage(12 V, 0.01 s, 1 kohm, 10 uF) = V"),
                 12 * (1 - math.exp(-1)))
    assert close(value("rl_current_rise(12 V, 0.05 s, 10 ohm, 0.5 H) = A"),
                 1.2 * (1 - math.exp(-1)))
    assert close(value("rc_charge_voltage(12 V, 10 ms, 1 kohm, 10 uF) = V"), 7.585447)


def test_step_response_at_zero_time():
    assert value("rc_charge_voltage(12 V, 0 s, 1 kohm, 10 uF) =") == 0
    assert value("rl_current_rise(12 V, 0, 10 ohm, 0.5 H) =") == 0


def test_transient_errors():
    assert err("rc_charge_voltage(12 V, -1 ms, 1 kohm, 10 uF) =") == \
        "rc_charge_voltage: t must not be negative"
    assert "t must be a time" in err("rc_charge_voltage(12 V, 1 V, 1 kohm, 10 uF) =")
    assert "R must be greater than zero" in err("rc_time_constant(-1 kohm, 1 uF) =")


# --- resonance and filters --------------------------------------------------------------------

def test_resonance():
    assert close(value("resonant_frequency(0.01 H, 10 uF) = Hz"), 503.2921)
    assert close(value("series_rlc_quality_factor(10 ohm, 0.01 H, 10 uF) ="), 3.162278)
    assert close(value("series_rlc_bandwidth(10 ohm, 0.01 H) = Hz"), 159.1549)


def test_resonance_consistency():
    f0 = value("resonant_frequency(0.01 H, 10 uF) = Hz")
    bw = value("series_rlc_bandwidth(10 ohm, 0.01 H) = Hz")
    assert close(f0 / bw, value("series_rlc_quality_factor(10 ohm, 0.01 H, 10 uF) ="))


def test_filters():
    assert close(value("rc_lowpass_cutoff(1 kohm, 1 uF) = Hz"), 159.1549)
    assert close(value("rc_lowpass_gain(159.1549 Hz, 1 kohm, 1 uF) ="), 0.7071068)
    assert close(value("rc_lowpass_gain(1591.549 Hz, 1 kohm, 1 uF) ="), 0.0995037)
    assert close(value("rc_highpass_gain(159.1549 Hz, 1 kohm, 1 uF) ="), 0.7071068)


def test_filter_gains_power_complementary():
    lo = value("rc_lowpass_gain(300 Hz, 2.2 kohm, 330 nF) =")
    hi = value("rc_highpass_gain(300 Hz, 2.2 kohm, 330 nF) =")
    assert close(lo**2 + hi**2, 1, 1e-4)


def test_unit_errors_new_dims():
    assert "C needs a unit of capacitance" in err("rc_lowpass_cutoff(1 kohm, 1) =")
    assert "f must be a frequency" in err("rc_lowpass_gain(1 s, 1 kohm, 1 uF) =")


def test_undefined_names():
    assert "not defined" in err("rc_time_constant(R, C) =")


def test_in_user_function_body():
    assert close(value("tau(r, c) := rc_time_constant(r, c)", "tau(1 kohm, 10 uF) = s"), 0.01)


def test_module_has_no_qt():
    src = Path(__file__).parent.parent / "livesheet" / "engine" / "electrical.py"
    assert not [l for l in src.read_text().splitlines()
                if l.startswith(("import", "from")) and "PySide6" in l]
