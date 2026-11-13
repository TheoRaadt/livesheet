"""Spec 033 phase 1: mechanical-engineering function library (mechanics of materials)."""

from pathlib import Path

import pytest

from livesheet.engine import Engine, evaluator
from livesheet.engine.completion import signature_for
from livesheet.engine.mecheng import MECH_BUILTINS
from livesheet.engine.units import UNITS

BEAM = "200 GPa, 1e-6 m^4"


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


# --- registration and naming ---------------------------------------------------------------

def test_28_names_and_registered():
    assert len(MECH_BUILTINS) == 51  # 28 phase 1 + 11 phase 2a + 12 phase 2b (spec 040)
    for name in MECH_BUILTINS:
        assert name in evaluator.BUILTINS


def test_no_name_collisions():
    names = set(MECH_BUILTINS)
    others = (set(evaluator.BUILTINS) - names) | set(UNITS)
    others |= evaluator._ENTRYWISE_KEYWORDS | evaluator._SCALAR_KEYWORDS
    assert not names & others


def test_engine_module_has_no_qt():
    src = Path(__file__).parent.parent / "livesheet" / "engine" / "mecheng.py"
    assert not [l for l in src.read_text().splitlines() if l.startswith(("import", "from")) and "PySide6" in l]


def test_signature_hints():
    assert signature_for("cantilever_tip_deflection") == "cantilever_tip_deflection(P, L, E, I)"
    assert signature_for("ring_inertia") == "ring_inertia(do, di)"
    assert signature_for("euler_critical_load") == "euler_critical_load(E, I, L, K)"


def test_wrong_argument_count():
    assert "Wrong number of arguments" in err("rect_area(50 mm) =")


# --- unit rules ----------------------------------------------------------------------------

def test_bare_number_rejected():
    assert err("rect_area(50, 100 mm) =") == "rect_area: b needs a unit of length, for example 1 mm"


def test_wrong_dimension():
    assert err("rect_area(50 mm, 100 kg) =") == "rect_area: h must be a length, not kg"


def test_dimensionless_with_unit():
    assert err(f"euler_critical_load({BEAM}, 2 m, 1 m) =") == \
        "euler_critical_load: K must be dimensionless"


def test_mixed_input_units():
    assert value("ring_inertia(0.04 m, 30 mm) = mm^4") == pytest.approx(85902.92, rel=1e-6)


def test_bare_equals_is_si():
    assert run("rect_area(50 mm, 100 mm) =").output == "= 0.005 m²"


# --- section properties --------------------------------------------------------------------

@pytest.mark.parametrize("src,expected", [
    ("rect_area(50 mm, 100 mm) = mm^2", 5000),
    ("rect_inertia(50 mm, 100 mm) = mm^4", 4166666.67),
    ("rect_section_modulus(50 mm, 100 mm) = mm^3", 83333.33),
    ("circle_area(40 mm) = mm^2", 1256.637),
    ("circle_inertia(40 mm) = mm^4", 125663.71),
    ("circle_polar_inertia(40 mm) = mm^4", 251327.41),
    ("circle_section_modulus(40 mm) = mm^3", 6283.185),
    ("ring_area(40 mm, 30 mm) = mm^2", 549.779),
    ("ring_inertia(40 mm, 30 mm) = mm^4", 85902.92),
    ("ring_section_modulus(40 mm, 30 mm) = mm^3", 4295.146),
])
def test_section_properties(src, expected):
    # output is formatted to 6 significant digits
    assert value(src) == pytest.approx(expected, rel=1e-5)


def test_radius_of_gyration_is_sqrt():
    out = run("radius_of_gyration(circle_inertia(40 mm), circle_area(40 mm)) = mm").output
    assert out == "= 10 mm"


# --- beams ---------------------------------------------------------------------------------

@pytest.mark.parametrize("src,expected", [
    (f"cantilever_tip_deflection(1 kN, 2 m, {BEAM}) = mm", 13.3333),
    (f"simply_supported_center_deflection(1 kN, 2 m, {BEAM}) = mm", 0.833333),
    (f"cantilever_udl_deflection(2 kN/m, 2 m, {BEAM}) = mm", 20),
    (f"simply_supported_udl_deflection(2 kN/m, 2 m, {BEAM}) = mm", 2.08333),
    ("cantilever_tip_max_moment(1 kN, 2 m) = N*m", 2000),
    ("cantilever_udl_max_moment(2 kN/m, 2 m) = N*m", 4000),
    ("simply_supported_center_max_moment(1 kN, 2 m) = N*m", 500),
    ("simply_supported_udl_max_moment(2 kN/m, 2 m) = N*m", 1000),
])
def test_beams(src, expected):
    assert value(src) == pytest.approx(expected, rel=1e-5)


def test_beam_length_scaling():
    q = (f"cantilever_tip_deflection(1 kN, 4 m, {BEAM}) / "
         f"cantilever_tip_deflection(1 kN, 2 m, {BEAM}) =")
    assert run(q).output == "= 8"


# --- stress and strain ---------------------------------------------------------------------

@pytest.mark.parametrize("src,expected", [
    ("axial_stress(10 kN, 100 mm^2) = MPa", 100),
    ("axial_elongation(5 kN, 2 m, 100 mm^2, 200 GPa) = mm", 0.5),
    ("bending_stress(500 N*m, 0.05 m, 8e-6 m^4) = MPa", 3.125),
    ("axial_strain(0.5 mm, 2 m) =", 0.00025),
    ("hoop_stress(2 MPa, 500 mm, 10 mm) = MPa", 100),
    ("longitudinal_stress(2 MPa, 500 mm, 10 mm) = MPa", 50),
])
def test_stress(src, expected):
    assert value(src) == pytest.approx(expected, rel=1e-6)


def test_signed_inputs_allowed():
    assert value("axial_stress(-10 kN, 100 mm^2) = MPa") == pytest.approx(-100)


# --- columns -------------------------------------------------------------------------------

def test_euler():
    k1 = value(f"euler_critical_load({BEAM}, 2 m, 1) = kN")
    k2 = value(f"euler_critical_load({BEAM}, 2 m, 0.5) = kN")
    assert k1 == pytest.approx(493.48, rel=1e-5)
    assert k2 == pytest.approx(1973.92, rel=1e-5)
    assert k2 == pytest.approx(4 * k1, rel=1e-4)


def test_slenderness():
    assert value("slenderness_ratio(2 m, 1, 0.05 m) =") == 40
    assert value("euler_transition_slenderness(200 GPa, 250 MPa) =") == pytest.approx(125.6637, rel=1e-4)


# --- errors --------------------------------------------------------------------------------

def test_non_positive():
    assert err("circle_inertia(-40 mm) =") == "circle_inertia: d must be greater than zero"
    assert err(f"euler_critical_load({BEAM}, 2 m, -1) =") == \
        "euler_critical_load: K must be greater than zero"


def test_ring_order():
    assert err("ring_inertia(30 mm, 40 mm) =") == "ring_inertia: do must be larger than di"


def test_undefined_names_not_swallowed():
    # note: L is the litre unit and E, I are constants in the engine, so use other names
    assert "not defined" in err("cantilever_tip_deflection(P, Lb, Em, Ix) =")


def test_inside_function_body():
    res = run("f(x) := rect_area(x, 100 mm)", "f(50 mm) = m^2")
    assert res.status == "ok" and res.output == "= 0.005 m²"


def test_function_body_checks_at_call_time():
    res = run("f(x) := rect_area(x, 100 mm)", "f(50) = m^2")
    assert res.status == "error" and "needs a unit of length" in res.error
