"""Independent black-box review of spec 034 phase 1A (electrical library). Expected values are
recomputed here with math / sympy, not copied from the implementation."""

import math

import pytest
import sympy as sp

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import builtin_candidates, signature_for
from livesheet.engine.electrical import ELEC_BUILTINS
from livesheet.engine.units import UNITS

NAMES = {
    "resistors_series", "resistors_parallel", "voltage_divider", "current_divider",
    "rms_from_peak", "peak_from_rms", "average_power", "apparent_power", "reactive_power",
    "power_factor", "wye_line_voltage", "wye_phase_voltage", "delta_line_current",
    "three_phase_power", "transformer_secondary_voltage", "transformer_secondary_current",
    "reflected_impedance",
}


def run(*lines):
    res = Engine().evaluate([(i, s) for i, s in enumerate(lines)])
    return res[len(lines) - 1]


def num(text: str) -> float:
    t = text.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        t = t.replace(sup, ch)
    return float(t)


def val(src, unit):
    r = run(f"{src} = {unit}")
    assert r.status == "ok", r.error
    assert r.output.strip().endswith(unit), r.output
    return num(r.output)


def err(src):
    r = run(src + " =")
    assert r.status == "error", r.output
    return r.error


# --- registry / autocomplete -----------------------------------------------------------------

def test_names_exact_and_collision_free():
    assert NAMES <= set(ELEC_BUILTINS)   # phase 1B (tests/test_electrical_1b.py) adds 19 more
    others = (set(evaluator.BUILTINS) - set(ELEC_BUILTINS)) | set(UNITS)
    assert not set(ELEC_BUILTINS) & others


def test_autocomplete_lists_all_with_arg_names():
    cands = {c.name: c.signature for c in builtin_candidates()}
    for n in NAMES:
        assert n in cands and cands[n].startswith(n + "(")
        assert signature_for(n) == cands[n]
    assert cands["three_phase_power"] == "three_phase_power(VL, IL, phi)"
    assert cands["resistors_series"] == "resistors_series(R)"


def test_argument_names_avoid_reserved_letters():
    import re
    for n in NAMES:
        args = re.findall(r"[A-Za-z_]\w*", signature_for(n).split("(", 1)[1])
        assert not set(args) & {"E", "I", "L", "g", "e", "j", "V", "A", "F", "H", "C", "T", "W", "S"}


@pytest.mark.parametrize("name,n", [("power_factor", 1), ("apparent_power", 2), ("voltage_divider", 3)])
def test_wrong_arg_count(name, n):
    args = ", ".join(["1 V"] * (n + 1))
    assert "Wrong number of arguments" in err(f"{name}({args})")
    assert "Wrong number of arguments" in err(f"{name}()")


# --- spec criteria 5-9 ------------------------------------------------------------------------

def test_bare_number_rejected_every_dimensional_slot():
    cases = {
        "voltage_divider(12, 1 kohm, 3 kohm)": "voltage_divider: Vin needs a unit of voltage, for example 1 V",
        "current_divider(1, 1 kohm, 3 kohm)": "current_divider: Itot needs a unit of current",
        "rms_from_peak(325)": "rms_from_peak: Vpk needs a unit of voltage",
        "peak_from_rms(230)": "peak_from_rms: Vrms needs a unit of voltage",
        "average_power(230, 10 A, 0)": "average_power: Vrms needs a unit of voltage",
        "average_power(230 V, 10, 0)": "average_power: Irms needs a unit of current",
        "apparent_power(230 V, 10)": "apparent_power: Irms needs a unit of current",
        "reactive_power(230, 10 A, 0)": "reactive_power: Vrms needs a unit",
        "wye_line_voltage(230)": "wye_line_voltage: Vph needs a unit",
        "wye_phase_voltage(400)": "wye_phase_voltage: Vline needs a unit",
        "delta_line_current(10)": "delta_line_current: Iph needs a unit of current",
        "three_phase_power(400, 10 A, 0)": "three_phase_power: VL needs a unit",
        "three_phase_power(400 V, 10, 0)": "three_phase_power: IL needs a unit",
        "transformer_secondary_voltage(230, 10, 1)": "transformer_secondary_voltage: Vp needs a unit",
        "transformer_secondary_current(2, 10, 1)": "transformer_secondary_current: Ip needs a unit",
        "reflected_impedance(8, 10, 1)": "reflected_impedance: Zs needs a unit of resistance",
        "resistors_series([10 ohm; 5])": "resistors_series: R needs a unit of resistance",
        "resistors_parallel(10)": "resistors_parallel: R needs a unit of resistance",
    }
    for src, msg in cases.items():
        assert msg in err(src), src


def test_wrong_dimension_messages():
    assert err("voltage_divider(12 V, 1 kohm, 3 A)") == "voltage_divider: R2 must be a resistance, not A"
    assert "must be a voltage" in err("rms_from_peak(3 A)")
    assert "must be a current" in err("delta_line_current(3 V)")
    assert "must be a resistance" in err("resistors_series([10 ohm; 5 V])")
    assert err("average_power(230 V, 10 A, 60 V)") == "average_power: phi must be an angle in radians, not V"
    assert "angle" in err("power_factor(2 s)")
    assert err("transformer_secondary_voltage(230 V, 1000 A, 100)") == \
        "transformer_secondary_voltage: Np must be a plain number of turns, not A"
    assert "turns" in err("reflected_impedance(8 ohm, 10, 2 kg)")


def test_mixed_compatible_units():
    assert val("voltage_divider(12 V, 1 kohm, 3000 ohm)", "V") == pytest.approx(9)
    assert val("voltage_divider(0.012 kV, 1000 ohm, 3 kohm)", "V") == pytest.approx(9)
    assert val("wye_line_voltage(1 kV)", "kV") == pytest.approx(math.sqrt(3))
    assert val("apparent_power(1 mV, 1 mA)", "W") == pytest.approx(1e-6)


# --- numerics, recomputed ---------------------------------------------------------------------

def test_rms_peak():
    assert val("rms_from_peak(325 V)", "V") == pytest.approx(325 / math.sqrt(2), rel=1e-5)
    assert val("peak_from_rms(230 V)", "V") == pytest.approx(230 * math.sqrt(2), rel=1e-5)
    assert val("rms_from_peak(peak_from_rms(7 V))", "V") == pytest.approx(7, rel=1e-5)


def test_ac_power():
    p, s, q = 230 * 10 * math.cos(math.pi / 3), 2300, 2300 * math.sin(math.pi / 3)
    assert val("average_power(230 V, 10 A, pi/3)", "W") == pytest.approx(p, rel=1e-5)
    assert val("apparent_power(230 V, 10 A)", "VA") == pytest.approx(s)
    assert val("reactive_power(230 V, 10 A, pi/3)", "var") == pytest.approx(q, rel=1e-5)
    assert val("reactive_power(230 V, 10 A, -pi/3)", "var") == pytest.approx(-q, rel=1e-5)
    assert num(run("power_factor(pi/3) =").output) == pytest.approx(0.5)
    assert num(run("power_factor(0) =").output) == 1
    assert num(run("power_factor(1.0471975511966) =").output) == pytest.approx(0.5, abs=1e-9)
    # plain number is radians: cos(1) not cos(1 deg)
    assert num(run("power_factor(1) =").output) == pytest.approx(math.cos(1), rel=1e-5)


def test_power_triangle():
    for phi in ("pi/3", "0.4", "-1.1", "2.5"):
        # inside the engine (full precision); displayed values are rounded to 6 digits
        r = run(f"(apparent_power(230 V, 10 A)^2) / (average_power(230 V, 10 A, {phi})^2 "
                f"+ reactive_power(230 V, 10 A, {phi})^2) =")
        assert r.status == "ok", r.error
        assert num(r.output) == pytest.approx(1.0, abs=1e-9)


def test_va_var_labels_and_si_base():
    assert run("apparent_power(230 V, 10 A) = VA").output.strip().endswith("VA")
    assert run("reactive_power(230 V, 10 A, pi/3) = var").output.strip().endswith("var")
    assert run("apparent_power(230 V, 10 A) =").output.strip() == "= 2300 W"
    assert run("average_power(230 V, 10 A, pi/3) =").output.strip() == "= 1150 W"
    assert run("apparent_power(230 V, 10 A) = V").status == "error"


def test_resistor_networks():
    assert val("resistors_series([10 ohm; 22 ohm; 33 ohm])", "ohm") == 65
    assert val("resistors_parallel([10 ohm; 10 ohm])", "ohm") == 5
    assert val("resistors_parallel([100 ohm; 200 ohm; 300 ohm])", "ohm") == \
        pytest.approx(1 / (1 / 100 + 1 / 200 + 1 / 300), rel=1e-5)
    assert val("resistors_series([1 kohm; 500 ohm])", "ohm") == pytest.approx(1500)
    assert val("resistors_parallel([1 kohm; 1 kohm])", "kohm") == pytest.approx(0.5)
    assert val("resistors_series(10 ohm)", "ohm") == 10      # scalar = one-element list
    assert val("voltage_divider(12 V, 1 kohm, 3 kohm)", "V") == pytest.approx(9)
    assert val("voltage_divider(-12 V, 1 kohm, 3 kohm)", "V") == pytest.approx(-9)
    assert val("current_divider(10 mA, 1 kohm, 1 kohm)", "mA") == pytest.approx(5)
    # I1 = Itot*R2/(R1+R2); with R1=1k, R2=3k carry 7.5 A of 10 A through R1
    assert val("current_divider(10 A, 1 kohm, 3 kohm)", "A") == pytest.approx(7.5)


def test_three_phase():
    assert val("wye_line_voltage(230 V)", "V") == pytest.approx(230 * math.sqrt(3), rel=1e-6)
    assert val("wye_phase_voltage(400 V)", "V") == pytest.approx(400 / math.sqrt(3), rel=1e-6)
    assert val("delta_line_current(10 A)", "A") == pytest.approx(10 * math.sqrt(3), rel=1e-6)
    assert val("three_phase_power(400 V, 10 A, pi/6)", "W") == pytest.approx(6000, rel=1e-6)
    assert val("wye_phase_voltage(wye_line_voltage(230 V))", "V") == pytest.approx(230, rel=1e-9)


def test_transformer():
    assert val("transformer_secondary_voltage(230 V, 1000, 100)", "V") == pytest.approx(23)
    assert val("transformer_secondary_current(2 A, 1000, 100)", "A") == pytest.approx(20)
    assert val("reflected_impedance(8 ohm, 1000, 100)", "ohm") == pytest.approx(800)
    assert val("reflected_impedance(8 ohm, 3, 6)", "ohm") == pytest.approx(2)
    assert val("transformer_secondary_voltage(230 V, 5, 5)", "V") == pytest.approx(230)
    # power conservation
    vs = val("transformer_secondary_voltage(230 V, 7, 3)", "V")
    is_ = val("transformer_secondary_current(2 A, 7, 3)", "A")
    assert vs * is_ == pytest.approx(460, rel=1e-5)   # 6-digit display rounding


# --- errors / edges ---------------------------------------------------------------------------

def test_positivity_errors():
    assert err("resistors_parallel([-100 ohm; 200 ohm])") == "resistors_parallel: R must be greater than zero"
    assert "greater than zero" in err("rms_from_peak(-5 V)")
    assert "Np must be greater than zero" in err("transformer_secondary_voltage(230 V, 0, 100)")
    assert "Ns must be greater than zero" in err("transformer_secondary_current(2 A, 10, -1)")
    assert "R1 must be greater than zero" in err("voltage_divider(12 V, -1 ohm, 3 kohm)")


def test_no_traceback_text():
    for src in ["resistors_series([1 ohm 2 ohm; 3 ohm 4 ohm])", "power_factor(x)", "resistors_parallel([])",
                "average_power(1 V, 1 A, 1 + 2*I)", "transformer_secondary_voltage(1 V, 1+2*I, 1)"]:
        r = run(src + " =")
        assert r.status == "error"
        assert "Traceback" not in r.error and "Error(" not in r.error


def test_undefined_names_reported():
    assert "not defined" in err("voltage_divider(Vs, R1, R2)")


def test_user_variables_E_I_L_g_not_hijacked():
    # user-defined E, I, L, g feed the functions as ordinary values
    r = run("E := 230 V", "rms_from_peak(E) =")
    assert num(r.output) == pytest.approx(230 / math.sqrt(2), rel=1e-5)
    r = run("L := 3 mH", "I := 2 A", "L*I = Wb")
    assert num(r.output) == pytest.approx(0.006)
    r = run("g := 3 m/s^2", "g =")
    assert r.output.strip() == "= 3 m/s²"
    # bare names keep their previous status
    assert run("E =").status == "error"
    assert run("L =").status == "error"
    assert run("g =").status == "error"


def test_new_units():
    assert val("1 mH", "H") == pytest.approx(1e-3)
    assert val("1 uH", "H") == pytest.approx(1e-6)
    assert val("1 nH", "H") == pytest.approx(1e-9)
    assert val("1 pF", "F") == pytest.approx(1e-12)
    assert val("1 mH + 1 uH", "mH") == pytest.approx(1.001)
    assert val("1 pF + 1 nF", "nF") == pytest.approx(1.001)
    assert val("2*pi*50 Hz*10 mH", "ohm") == pytest.approx(2 * math.pi * 50 * 0.01, rel=1e-5)
    assert val("10 pF * 10 V", "C") == pytest.approx(1e-10)
    assert val("3 VA + 2 W", "W") == pytest.approx(5)


def test_no_siemens_no_j_added():
    assert "S" not in UNITS and "j" not in UNITS


# --- defects found (strict xfail: flips to failure when fixed) --------------------------------

@pytest.mark.xfail(strict=True, reason="034-1A-1: zero result loses its unit, `= W` display errors")
def test_zero_power_can_be_displayed_in_w():
    r = run("average_power(230 V, 10 A, pi/2) = W")
    assert r.status == "ok", r.error


@pytest.mark.xfail(strict=True, reason="034-1A-2: matrix argument that is not a vector gives a garbled message")
def test_matrix_argument_message_is_readable():
    r = run("resistors_series([1 ohm 2 ohm; 3 ohm 4 ohm]) =")
    assert r.status == "error" and "vector" in r.error
