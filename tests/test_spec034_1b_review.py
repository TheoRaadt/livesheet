"""Independent black-box review of spec 034 phase 1B (phasors, impedance, transients, resonance,
RC filters). Expected values are recomputed here with math / cmath, not copied from the code."""

import cmath
import math

import pytest

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import builtin_candidates, signature_for
from livesheet.engine.electrical import ELEC_BUILTINS
from livesheet.engine.units import UNITS

NAMES_1A = {
    "resistors_series", "resistors_parallel", "voltage_divider", "current_divider",
    "rms_from_peak", "peak_from_rms", "average_power", "apparent_power", "reactive_power",
    "power_factor", "wye_line_voltage", "wye_phase_voltage", "delta_line_current",
    "three_phase_power", "transformer_secondary_voltage", "transformer_secondary_current",
    "reflected_impedance",
}
NAMES_1B = {
    "phasor", "phasor_magnitude", "phasor_angle", "impedance_resistor", "impedance_inductor",
    "impedance_capacitor", "impedance_series", "impedance_parallel", "angular_frequency",
    "rc_time_constant", "rl_time_constant", "rc_charge_voltage", "rl_current_rise",
    "resonant_frequency", "series_rlc_quality_factor", "series_rlc_bandwidth",
    "rc_lowpass_cutoff", "rc_lowpass_gain", "rc_highpass_gain",
}
PI = math.pi


def run(*lines):
    res = Engine().evaluate([(i, s) for i, s in enumerate(lines)])
    return res[len(lines) - 1]


def num(text: str) -> float:
    t = text.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        t = t.replace(sup, ch)
    return float(t)


def val(src, unit=None):
    r = run(f"{src} = {unit}" if unit else f"{src} =")
    assert r.status == "ok", r.error
    if unit:
        assert r.output.strip().endswith(unit), r.output
    return num(r.output)


def err(src):
    r = run(src + " =")
    assert r.status == "error", r.output
    return r.error


# --- registry / autocomplete -----------------------------------------------------------------

def test_registry_is_exactly_36_names():
    # The developer relaxed the 1A exact-set test to a subset check. Acceptable only because this
    # test pins the exact full set, so a stray or missing name still fails.
    assert set(ELEC_BUILTINS) == NAMES_1A | NAMES_1B
    assert len(ELEC_BUILTINS) == 36


def test_no_collision_with_builtins_units():
    others = (set(evaluator.BUILTINS) - set(ELEC_BUILTINS)) | set(UNITS)
    assert not set(ELEC_BUILTINS) & others


def test_autocomplete_lists_all_1b_with_arg_names():
    cands = {c.name: c.signature for c in builtin_candidates()}
    for n in NAMES_1B:
        assert n in cands and cands[n].startswith(n + "(")
        assert signature_for(n) == cands[n]
    assert "rc_charge_voltage(Vs, t, R, C)" == cands["rc_charge_voltage"]
    assert "phasor(mag, phi)" == cands["phasor"]


def test_arg_names_avoid_E_I_L_g_as_variables_but_L_is_documented_arg():
    # Spec table itself names the inductance argument L and capacitance C (documentation only).
    # What matters: user variables E, I, L, g still work and feed the functions.
    r = run("L := 0.1 H", "im(impedance_inductor(50 Hz, L)) = ohm")
    assert r.status == "ok", r.error
    assert num(r.output) == pytest.approx(2 * PI * 50 * 0.1, rel=1e-5)
    r = run("E := 12 V", "g := 3 m/s^2", "rc_charge_voltage(E, 0.01 s, 1 kohm, 10 uF) = V")
    assert num(r.output) == pytest.approx(12 * (1 - math.exp(-1)), rel=1e-5)
    assert run("L =").status == "error"          # bare L, E, g stay undefined
    assert run("E =").status == "error"


# --- C1..C3 phasors --------------------------------------------------------------------------

@pytest.mark.parametrize("phi", [0.3, PI / 6, PI / 2 + 0.2, PI - 0.1, -0.7, -PI / 2 - 0.4, 2.5])
def test_phasor_parts_and_roundtrip(phi):
    z = 10 * cmath.exp(1j * phi)
    arg = f"phasor(10 V, {phi!r})"
    assert val(f"re({arg})", "V") == pytest.approx(z.real, rel=1e-5, abs=1e-5)
    assert val(f"im({arg})", "V") == pytest.approx(z.imag, rel=1e-5, abs=1e-5)
    assert val(f"phasor_magnitude({arg})", "V") == pytest.approx(10, rel=1e-5)
    assert val(f"phasor_angle({arg})") == pytest.approx(phi, rel=1e-5)


@pytest.mark.parametrize("phi,expect", [
    (3 * PI / 4, 3 * PI / 4), (-3 * PI / 4, -3 * PI / 4),   # quadrants II and III
    (3 * PI / 2, -PI / 2), (5 * PI / 2, PI / 2), (-3 * PI / 2, PI / 2),
])
def test_phasor_angle_principal_range(phi, expect):
    assert val(f"phasor_angle(phasor(5 V, {phi!r}))") == pytest.approx(expect, rel=1e-5)


def test_phasor_angle_negative_real_axis_is_plus_pi():
    assert val("phasor_angle(-5 V)") == pytest.approx(PI, rel=1e-6)
    assert val("phasor_angle(phasor(1 V, pi))") == pytest.approx(PI, rel=1e-6)


def test_phasor_angle_of_imaginary_axes():
    assert val("phasor_angle(phasor(1 A, pi/2))") == pytest.approx(PI / 2, rel=1e-5)
    assert val("phasor_angle(phasor(1 A, -pi/2))") == pytest.approx(-PI / 2, rel=1e-5)


def test_phasor_keeps_unit_and_prefix_scaling():
    assert val("phasor_magnitude(phasor(10 kV, 1))", "kV") == pytest.approx(10, rel=1e-6)
    assert val("phasor_magnitude(phasor(10 kV, 1))", "V") == pytest.approx(1e4, rel=1e-6)
    assert val("phasor_magnitude(phasor(3 mA, 0.2))", "A") == pytest.approx(3e-3, rel=1e-6)


def test_phasor_magnitude_of_manual_complex_with_unit():
    assert val("phasor_magnitude(3 ohm + 4 I ohm)", "ohm") == pytest.approx(5, rel=1e-6)
    assert val("phasor_angle(3 ohm + 4 I ohm)") == pytest.approx(math.atan2(4, 3), rel=1e-6)


def test_phasor_angle_rejects_unit_angle_and_zero():
    assert "phi must be an angle in radians, not V" in err("phasor(10 V, 5 V)")
    assert "phi must be an angle" in err("phasor(10 V, 1 ohm)")
    assert "z must not be zero" in err("phasor_angle(0 V)")


# --- C4..C6 impedances (signs) -----------------------------------------------------------------

def test_impedance_resistor_real_si():
    assert val("impedance_resistor(4.7 kohm)", "ohm") == pytest.approx(4700, rel=1e-9)
    assert val("impedance_resistor(4.7 kohm)", "kohm") == pytest.approx(4.7, rel=1e-9)


@pytest.mark.parametrize("f,L", [(50, 0.1), (1000, 2e-3), (1e6, 1e-6)])
def test_inductor_impedance_positive_imaginary(f, L):
    x = 2 * PI * f * L
    assert val(f"im(impedance_inductor({f} Hz, {L!r} H))", "ohm") == pytest.approx(x, rel=1e-5)
    # real part is exactly zero; the engine drops the unit of a zero, so check without unit
    assert val(f"re(impedance_inductor({f} Hz, {L!r} H))") == 0


@pytest.mark.parametrize("f,C", [(50, 100e-6), (1e3, 1e-7), (60, 2.2e-3)])
def test_capacitor_impedance_negative_imaginary(f, C):
    x = -1 / (2 * PI * f * C)
    assert val(f"im(impedance_capacitor({f} Hz, {C!r} F))", "ohm") == pytest.approx(x, rel=1e-5)
    assert val(f"re(impedance_capacitor({f} Hz, {C!r} F))") == 0


def test_inductor_capacitor_prefix_units_equivalent():
    a = val("im(impedance_inductor(1 kHz, 10 mH))", "ohm")
    b = val("im(impedance_inductor(1000 Hz, 0.01 H))", "ohm")
    assert a == pytest.approx(b, rel=1e-9)
    c = val("im(impedance_capacitor(1 kHz, 100 nF))", "ohm")
    assert c == pytest.approx(-1 / (2 * PI * 1000 * 100e-9), rel=1e-5)


# --- C7/C8 series and parallel with complex ---------------------------------------------------

def test_series_complex_magnitude_and_angle():
    z = 10 + 1j * 2 * PI * 50 * 0.1
    s = "impedance_series([10 ohm; impedance_inductor(50 Hz, 0.1 H)])"
    assert val(f"phasor_magnitude({s})", "ohm") == pytest.approx(abs(z), rel=1e-5)
    assert val(f"phasor_angle({s})") == pytest.approx(cmath.phase(z), rel=1e-5)


def test_parallel_complex_values():
    zl = 1j * 2 * PI * 50 * 0.1
    z = 1 / (1 / 10 + 1 / zl)
    p = "impedance_parallel([10 ohm; impedance_inductor(50 Hz, 0.1 H)])"
    assert val(f"re({p})", "ohm") == pytest.approx(z.real, rel=1e-5)
    assert val(f"im({p})", "ohm") == pytest.approx(z.imag, rel=1e-5)


def test_parallel_three_branch_rlc():
    f, R, L, C = 200.0, 33.0, 5e-3, 47e-6
    z = 1 / (1 / R + 1 / (1j * 2 * PI * f * L) + 1j * 2 * PI * f * C)
    p = "impedance_parallel([33 ohm; impedance_inductor(200 Hz, 5 mH); impedance_capacitor(200 Hz, 47 uF)])"
    assert val(f"re({p})", "ohm") == pytest.approx(z.real, rel=1e-4)
    assert val(f"im({p})", "ohm") == pytest.approx(z.imag, rel=1e-4)


def test_parallel_real_equal_branches_and_single():
    assert val("impedance_parallel([10 ohm; 10 ohm])", "ohm") == pytest.approx(5, rel=1e-9)
    assert val("impedance_parallel(5 ohm)", "ohm") == pytest.approx(5, rel=1e-9)
    assert val("impedance_series([10 ohm; 5 ohm; 1 kohm])", "ohm") == pytest.approx(1015)


def test_series_rlc_at_resonance_is_pure_resistance_and_Q():
    R, L, C = 10.0, 0.01, 10e-6
    f0 = 1 / (2 * PI * math.sqrt(L * C))
    xl = 2 * PI * f0 * L
    f0s = repr(f0)
    s = f"impedance_series([10 ohm; impedance_inductor({f0s} Hz, 10 mH); impedance_capacitor({f0s} Hz, 10 uF)])"
    mag = val(f"phasor_magnitude({s})", "ohm")
    assert mag == pytest.approx(R, rel=1e-6)
    # Q = X_L / R at resonance
    q = val("series_rlc_quality_factor(10 ohm, 10 mH, 10 uF)")
    assert q == pytest.approx(xl / R, rel=1e-5)
    # off resonance the angle sign flips: above f0 inductive (+), below capacitive (-)
    hi = "impedance_series([10 ohm; impedance_inductor(1 kHz, 10 mH); impedance_capacitor(1 kHz, 10 uF)])"
    lo = "impedance_series([10 ohm; impedance_inductor(100 Hz, 10 mH); impedance_capacitor(100 Hz, 10 uF)])"
    assert val(f"phasor_angle({hi})") > 0
    assert val(f"phasor_angle({lo})") < 0


def test_series_parallel_unit_errors():
    assert "z must be a resistance, not V" in err("impedance_series([1 ohm; 2 V])")
    assert "needs a unit of resistance" in err("impedance_parallel([1; 2])")
    assert "needs a unit of resistance" in err("impedance_series([1 ohm; 1 I])")  # bare complex


# --- C9 ----------------------------------------------------------------------------------------

def test_angular_frequency_value_and_unit():
    r = run("angular_frequency(50 Hz) =")
    assert r.status == "ok"
    assert num(r.output) == pytest.approx(2 * PI * 50, rel=1e-6)
    assert "s⁻¹" in r.output
    assert val("angular_frequency(2 kHz)", "Hz") == pytest.approx(2 * PI * 2000, rel=1e-5)


# --- T1..T4 transients ------------------------------------------------------------------------

def test_time_constants_si_and_prefix_display():
    assert val("rc_time_constant(1 kohm, 10 uF)", "s") == pytest.approx(0.01, rel=1e-9)
    assert val("rc_time_constant(1 kohm, 10 uF)", "ms") == pytest.approx(10, rel=1e-9)
    assert val("rl_time_constant(0.5 H, 10 ohm)", "s") == pytest.approx(0.05, rel=1e-9)
    assert val("rl_time_constant(50 mH, 1 kohm)", "s") == pytest.approx(5e-5, rel=1e-9)


@pytest.mark.parametrize("t,Vs", [(0.01, 12), (0.003, 5), (0.05, 12), (1e-6, 3.3)])
def test_rc_charge_voltage(t, Vs):
    tau = 1e3 * 10e-6
    got = val(f"rc_charge_voltage({Vs} V, {t!r} s, 1 kohm, 10 uF)", "V")
    assert got == pytest.approx(Vs * (1 - math.exp(-t / tau)), rel=1e-5)


def test_rc_charge_voltage_limits_and_ms_input():
    assert val("rc_charge_voltage(12 V, 10 s, 1 kohm, 10 uF)", "V") == pytest.approx(12, rel=1e-9)
    assert val("rc_charge_voltage(12 V, 10 ms, 1 kohm, 10 uF)", "V") == pytest.approx(
        12 * (1 - math.exp(-1)), rel=1e-5)
    # tiny positive time (near t = 0) avoids the zero-unit-drop path
    assert val("rc_charge_voltage(12 V, 0.001 ms, 1 kohm, 10 uF)", "V") == pytest.approx(
        12 * (1 - math.exp(-1e-6 / 0.01)), rel=1e-4)
    # at 5 tau: 99.33 percent
    assert val("rc_charge_voltage(12 V, 5 * 10 ms, 1 kohm, 10 uF)", "V") == pytest.approx(
        12 * (1 - math.exp(-5)), rel=1e-5)


@pytest.mark.parametrize("t", [1e-3, 0.05, 0.2])
def test_rl_current_rise(t):
    got = val(f"rl_current_rise(12 V, {t!r} s, 10 ohm, 0.5 H)", "A")
    assert got == pytest.approx(1.2 * (1 - math.exp(-10 * t / 0.5)), rel=1e-5)


def test_rl_current_rise_steady_state_is_V_over_R():
    assert val("rl_current_rise(12 V, 10 s, 10 ohm, 0.5 H)", "A") == pytest.approx(1.2, rel=1e-9)


def test_transient_at_t_zero_bare_prints_zero():
    r = run("rc_charge_voltage(12 V, 0 s, 1 kohm, 10 uF) =")
    assert r.status == "ok" and num(r.output) == 0
    r = run("rl_current_rise(12 V, 0 s, 10 ohm, 0.5 H) =")
    assert r.status == "ok" and num(r.output) == 0


@pytest.mark.xfail(strict=True, reason="034-1A-1 / 034-1B-1: zero result loses its unit")
def test_transient_t_zero_can_be_displayed_in_V():
    r = run("rc_charge_voltage(12 V, 0 s, 1 kohm, 10 uF) = V")
    assert r.status == "ok", r.error


@pytest.mark.xfail(strict=True, reason="034-1A-1: zero power loses its unit (known low defect)")
def test_zero_unit_drop_known_1A_defect_still_present():
    r = run("average_power(230 V, 10 A, pi/2) = W")
    assert r.status == "ok", r.error


def test_transient_errors():
    assert err("rc_charge_voltage(12 V, -1 ms, 1 kohm, 10 uF)") == \
        "rc_charge_voltage: t must not be negative"
    assert "t must not be negative" in err("rl_current_rise(12 V, -1 ms, 10 ohm, 0.5 H)")
    assert "t needs a unit of time" in err("rc_charge_voltage(12 V, 0.01, 1 kohm, 10 uF)")
    assert "R must be greater than zero" in err("rc_time_constant(-1 kohm, 10 uF)")
    assert "C must be greater than zero" in err("rc_time_constant(1 kohm, -10 uF)")
    assert "L must be greater than zero" in err("rl_time_constant(-1 H, 1 ohm)")
    assert "C must be a capacitance, not Ω" in err("rc_time_constant(1 kohm, 1 ohm)")


# --- S1..S3 resonance --------------------------------------------------------------------------

def test_resonance_values_and_consistency():
    L, C, R = 0.01, 10e-6, 10.0
    f0 = 1 / (2 * PI * math.sqrt(L * C))
    q = math.sqrt(L / C) / R
    b = R / (2 * PI * L)
    assert val("resonant_frequency(0.01 H, 10 uF)", "Hz") == pytest.approx(f0, rel=1e-6)
    assert val("resonant_frequency(10 mH, 10 uF)", "kHz") == pytest.approx(f0 / 1e3, rel=1e-6)
    assert val("series_rlc_quality_factor(10 ohm, 0.01 H, 10 uF)") == pytest.approx(q, rel=1e-6)
    assert val("series_rlc_bandwidth(10 ohm, 0.01 H)", "Hz") == pytest.approx(b, rel=1e-6)
    assert f0 / b == pytest.approx(q, rel=1e-9)
    assert val("resonant_frequency(10 mH, 10 uF)", "Hz") / \
        val("series_rlc_bandwidth(10 ohm, 10 mH)", "Hz") == pytest.approx(q, rel=1e-5)


def test_resonant_frequency_makes_reactances_cancel():
    f0 = val("resonant_frequency(3 mH, 220 nF)", "Hz")
    xl = val(f"im(impedance_inductor({f0!r} Hz, 3 mH))", "ohm")
    xc = val(f"im(impedance_capacitor({f0!r} Hz, 220 nF))", "ohm")
    assert xl == pytest.approx(-xc, rel=1e-4)


def test_Q_is_dimensionless_and_rejects_unit_slot_errors():
    r = run("series_rlc_quality_factor(10 ohm, 0.01 H, 10 uF) =")
    assert r.status == "ok" and r.output.split()[-1].replace(".", "").isdigit()
    assert "R needs a unit of resistance" in err("series_rlc_quality_factor(10, 0.01 H, 10 uF)")
    assert "L needs a unit of inductance" in err("series_rlc_quality_factor(10 ohm, 0.01, 10 uF)")
    assert "C needs a unit of capacitance" in err("resonant_frequency(1 H, 5)")
    assert "R must be greater than zero" in err("series_rlc_bandwidth(-1 ohm, 1 H)")


# --- F1..F3 filters ----------------------------------------------------------------------------

def test_filter_cutoff_and_gain_at_cutoff():
    fc = 1 / (2 * PI * 1e3 * 1e-6)
    assert val("rc_lowpass_cutoff(1 kohm, 1 uF)", "Hz") == pytest.approx(fc, rel=1e-6)
    fcs = repr(fc)
    assert val(f"rc_lowpass_gain({fcs} Hz, 1 kohm, 1 uF)") == pytest.approx(1 / math.sqrt(2), rel=1e-6)
    assert val(f"rc_highpass_gain({fcs} Hz, 1 kohm, 1 uF)") == pytest.approx(1 / math.sqrt(2), rel=1e-6)


@pytest.mark.parametrize("f", [1.0, 10.0, 159.1549, 1591.549, 1e5])
def test_filter_gain_curve_and_complementarity(f):
    x = 2 * PI * f * 1e3 * 1e-6
    lp = val(f"rc_lowpass_gain({f!r} Hz, 1 kohm, 1 uF)")
    hp = val(f"rc_highpass_gain({f!r} Hz, 1 kohm, 1 uF)")
    assert lp == pytest.approx(1 / math.sqrt(1 + x * x), rel=1e-5)
    assert hp == pytest.approx(x / math.sqrt(1 + x * x), rel=1e-5)
    assert lp ** 2 + hp ** 2 == pytest.approx(1, rel=1e-4)


def test_filter_gain_decade_and_prefix_inputs():
    assert val("rc_lowpass_gain(1.591549 kHz, 1 kohm, 1 uF)") == pytest.approx(1 / math.sqrt(101), rel=1e-5)
    assert val("rc_lowpass_gain(1000 Hz, 1000 ohm, 1000 nF)") == pytest.approx(
        val("rc_lowpass_gain(1 kHz, 1 kohm, 1 uF)"), rel=1e-9)


def test_filter_errors():
    assert "f needs a unit of frequency" in err("rc_lowpass_gain(100, 1 kohm, 1 uF)")
    assert err("impedance_capacitor(-50 Hz, 100 uF)") == "impedance_capacitor: f must be greater than zero"
    assert "R must be greater than zero" in err("rc_lowpass_cutoff(-1 kohm, 1 uF)")
    assert "R must be a resistance, not A" in err("rc_highpass_gain(1 Hz, 3 A, 1 uF)")


# --- generic strict-unit rejection of bare numbers in every dimensional slot -------------------

STRICT = {  # function -> list of argument templates (valid), bare number replaced one at a time
    "impedance_resistor": ["1 ohm"], "impedance_inductor": ["1 Hz", "1 H"],
    "impedance_capacitor": ["1 Hz", "1 F"], "angular_frequency": ["1 Hz"],
    "rc_time_constant": ["1 ohm", "1 F"], "rl_time_constant": ["1 H", "1 ohm"],
    "rc_charge_voltage": ["1 V", "1 s", "1 ohm", "1 F"],
    "rl_current_rise": ["1 V", "1 s", "1 ohm", "1 H"],
    "resonant_frequency": ["1 H", "1 F"],
    "series_rlc_quality_factor": ["1 ohm", "1 H", "1 F"],
    "series_rlc_bandwidth": ["1 ohm", "1 H"],
    "rc_lowpass_cutoff": ["1 ohm", "1 F"],
    "rc_lowpass_gain": ["1 Hz", "1 ohm", "1 F"], "rc_highpass_gain": ["1 Hz", "1 ohm", "1 F"],
}


@pytest.mark.parametrize("fn", sorted(STRICT))
def test_bare_number_rejected_each_slot(fn):
    good = STRICT[fn]
    assert run(f"{fn}({', '.join(good)}) =").status == "ok"
    for i in range(len(good)):
        args = list(good)
        args[i] = "2"
        e = err(f"{fn}({', '.join(args)})")
        assert e.startswith(f"{fn}: ") and "needs a unit of" in e and "for example" in e, e
        assert "Traceback" not in e


@pytest.mark.parametrize("fn", sorted(STRICT))
def test_wrong_dimension_each_slot_and_arg_count(fn):
    good = STRICT[fn]
    for i in range(len(good)):
        args = list(good)
        args[i] = "2 kg"
        e = err(f"{fn}({', '.join(args)})")
        assert e.startswith(f"{fn}: ") and "must be" in e, e
    assert err(f"{fn}()") == "Wrong number of arguments"
    assert err(f"{fn}({', '.join(good + ['1 V'])})") == "Wrong number of arguments"


def test_phasor_and_z_slots_arg_count():
    assert err("phasor(1 V)") == "Wrong number of arguments"
    assert err("phasor_angle()") == "Wrong number of arguments"
    assert err("phasor_magnitude(1 V, 2 V)") == "Wrong number of arguments"


def test_no_python_traceback_text_anywhere():
    for s in ["phasor(1 V, pi/2, 3)", "impedance_series([])", "impedance_parallel([])",
              "phasor_magnitude(3 V + 4 A)", "rc_time_constant(R, Ccap)"]:
        e = err(s)
        assert "Traceback" not in e and "Error(" not in e and "sympy" not in e.lower(), e


def test_undefined_names_message():
    assert "Ccap" in err("rc_time_constant(R, Ccap)")
    assert "not defined" in err("rc_time_constant(R, C)")   # spec says "C, R ..."; C is the coulomb unit


def test_empty_vector_message_is_engine_level_not_function_level():
    # spec criterion 34 expects "impedance_parallel: needs at least one impedance"
    assert err("impedance_parallel([])") == "Empty matrix"
    with pytest.raises(Exception) as ei:
        ELEC_BUILTINS["impedance_parallel"](__import__("sympy").Matrix([]))
    assert "needs at least one impedance" in str(ei.value)


# --- zero handling / edge cases ----------------------------------------------------------------

def test_zero_impedance_in_parallel_is_error_not_division_by_zero():
    assert "must not contain a zero impedance" in err("impedance_parallel([0 ohm; 5 ohm])")


@pytest.mark.xfail(strict=True, reason="034-1B-3: ideal parallel LC gives ok 'undefined'")
def test_parallel_of_opposite_reactances_gives_open_circuit_marker():
    # Defect 034-1B-3 (low): ideal parallel LC at resonance reports status ok with "undefined".
    r = run("impedance_parallel([1 ohm; -1 ohm]) =")
    assert r.status == "error" or "undefined" not in r.output, r.output


def test_zero_valued_phasor_args_accept_bare_zero_only_for_t_and_z():
    assert run("phasor_magnitude(0 V) =").status == "ok"
    assert val("impedance_series([0 ohm; 5 ohm])", "ohm") == pytest.approx(5)


@pytest.mark.xfail(strict=True, reason="034-1B-2: 0 Hz / 0 s give misleading 'needs a unit' text")
def test_zero_frequency_message_is_not_misleading():
    assert "needs a unit" not in err("impedance_inductor(0 Hz, 1 H)")


@pytest.mark.xfail(strict=True, reason="034-1B-4 cosmetic: 'a inductance'")
def test_grammar_a_inductance():
    assert "a inductance" not in err("rl_time_constant(1 V, 1 ohm)")


def test_large_and_small_magnitudes_stay_finite():
    assert val("rc_lowpass_cutoff(1 Mohm, 1 pF)", "kHz") == pytest.approx(
        1 / (2 * PI * 1e6 * 1e-12) / 1e3, rel=1e-6)
    assert val("resonant_frequency(1 uH, 1 pF)", "MHz") == pytest.approx(
        1 / (2 * PI * math.sqrt(1e-6 * 1e-12)) / 1e6, rel=1e-6)
    assert val("rc_charge_voltage(5 V, 1000 s, 1 ohm, 1 uF)", "V") == pytest.approx(5, rel=1e-9)


def test_function_values_composable_in_expressions_and_variables():
    r = run("fc := rc_lowpass_cutoff(1 kohm, 1 uF)", "rc_lowpass_gain(fc, 1 kohm, 1 uF) =")
    assert r.status == "ok" and num(r.output) == pytest.approx(1 / math.sqrt(2), rel=1e-5)
    r = run("Z := impedance_series([10 ohm; impedance_inductor(50 Hz, 0.1 H)])",
            "phasor_magnitude(Z) = ohm")
    assert num(r.output) == pytest.approx(abs(10 + 1j * 2 * PI * 5), rel=1e-5)
    # Ohm's law with a phasor: I = V / Z, then magnitude in A
    r = run("Z := impedance_series([10 ohm; impedance_inductor(50 Hz, 0.1 H)])",
            "I1 := phasor(230 V, 0) / Z", "phasor_magnitude(I1) = A")
    assert r.status == "ok", r.error
    assert num(r.output) == pytest.approx(230 / abs(10 + 1j * 2 * PI * 5), rel=1e-5)
