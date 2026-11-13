"""Independent black-box tests for spec 033 phase 1 (mechanical-engineering library).

Expected values are computed here from first principles with plain Python (math), using mixed input
units, and compared with the engine's 6-significant-digit output.
"""

import math
import subprocess
import sys
from pathlib import Path

import pytest

from livesheet.engine import Engine
from livesheet.engine.completion import signature_for

ROOT = Path(__file__).parent.parent

FACT = {"mm": 1e-3, "cm": 1e-2, "m": 1.0, "N": 1.0, "kN": 1e3, "MN": 1e6, "Pa": 1.0,
        "kPa": 1e3, "MPa": 1e6, "GPa": 1e9}

NAMES = """rect_area rect_inertia rect_section_modulus circle_area circle_inertia circle_polar_inertia
circle_section_modulus ring_area ring_inertia ring_section_modulus radius_of_gyration
cantilever_tip_deflection cantilever_udl_deflection simply_supported_center_deflection
simply_supported_udl_deflection cantilever_tip_max_moment cantilever_udl_max_moment
simply_supported_center_max_moment simply_supported_udl_max_moment axial_stress axial_strain
axial_elongation bending_stress hoop_stress longitudinal_stress euler_critical_load
slenderness_ratio euler_transition_slenderness""".split()


def run(*lines):
    res = Engine().evaluate([(i, s) for i, s in enumerate(lines)])
    return res[len(lines) - 1]


def parse(out: str) -> float:
    t = out.lstrip("= ").split()[0].replace("×10", "e")
    for sup, ch in zip("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"):
        t = t.replace(sup, ch)
    return float(t)


def val(src, rel=1e-5):
    r = run(src)
    assert r.status == "ok", (src, r.error)
    return parse(r.output)


def err(src):
    r = run(src)
    assert r.status == "error", (src, r.output)
    assert "Traceback" not in r.error
    return r.error


def q(x, u):
    """literal 'x u' where x is a float in unit u"""
    return f"{x!r} {u}"


def si(x, u):
    return x * FACT[u]


# ---------------- registration ----------------

def test_all_28_registered_and_callable_names():
    from livesheet.engine import evaluator
    assert len(NAMES) == 28
    for n in NAMES:
        assert n in evaluator.BUILTINS, n


def test_no_collision_with_units_or_keywords():
    from livesheet.engine import evaluator
    from livesheet.engine.units import UNITS
    for n in NAMES:
        assert n not in UNITS
    # keyword/builtin key sets other than the mech entries themselves
    from livesheet.engine.mecheng import MECH_BUILTINS
    assert set(NAMES) <= set(MECH_BUILTINS)  # phase 2 names (spec 040a) are added on top
    others = set(evaluator.BUILTINS) - set(MECH_BUILTINS)
    assert not set(NAMES) & others


def test_signature_hints_all():
    expect = {
        "rect_area": "(b, h)", "ring_section_modulus": "(do, di)", "radius_of_gyration": "(I, A)",
        "cantilever_udl_deflection": "(w, L, E, I)", "simply_supported_udl_max_moment": "(w, L)",
        "axial_elongation": "(F, L, A, E)", "bending_stress": "(M, c, I)", "hoop_stress": "(p, r, t)",
        "euler_critical_load": "(E, I, L, K)", "slenderness_ratio": "(L, K, r)",
        "euler_transition_slenderness": "(E, sy)", "axial_strain": "(dL, L)",
    }
    for n, tail in expect.items():
        assert signature_for(n) == n + tail
    for n in NAMES:
        assert signature_for(n).startswith(n + "(")


def test_completion_lists_names():
    from livesheet.engine import completion
    for fn in ("completions", "complete", "candidates"):
        if hasattr(completion, fn):
            try:
                res = getattr(completion, fn)("rect_")
            except TypeError:
                continue
            flat = str(res)
            assert "rect_area" in flat and "rect_inertia" in flat
            return
    pytest.skip("no completion list helper with simple signature")


def test_engine_package_qt_free_fresh_interpreter():
    code = ("import sys; import livesheet.engine.mecheng, livesheet.engine; "
            "bad=[m for m in sys.modules if m.startswith('PySide6')]; "
            "sys.exit(1 if bad else 0)")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_source_has_no_imperial_units():
    src = (ROOT / "livesheet/engine/mecheng.py").read_text().lower()
    for bad in ("psi", "ksi", "lbf", "inch", "foot", "feet", "ft", "lbm"):
        assert not any(bad == w for w in src.replace("(", " ").replace(")", " ").replace(",", " ").split()), bad


# ---------------- first-principles numerics ----------------

SECTION_CASES = [  # (b, ub, h, uh) mixed units
    (50.0, "mm", 10.0, "cm"), (0.2, "m", 35.0, "mm"), (7.5, "cm", 0.12, "m"),
]


@pytest.mark.parametrize("b,ub,h,uh", SECTION_CASES)
def test_rect(b, ub, h, uh):
    B, H = si(b, ub), si(h, uh)
    a = f"{q(b, ub)}, {q(h, uh)}"
    assert val(f"rect_area({a}) = m^2") == pytest.approx(B * H, rel=1e-5)
    assert val(f"rect_inertia({a}) = m^4") == pytest.approx(B * H ** 3 / 12, rel=1e-5)
    assert val(f"rect_section_modulus({a}) = m^3") == pytest.approx(B * H ** 2 / 6, rel=1e-5)


@pytest.mark.parametrize("d,u", [(40.0, "mm"), (2.5, "cm"), (0.3, "m")])
def test_circle(d, u):
    D = si(d, u)
    a = q(d, u)
    assert val(f"circle_area({a}) = m^2") == pytest.approx(math.pi * D ** 2 / 4, rel=1e-5)
    assert val(f"circle_inertia({a}) = m^4") == pytest.approx(math.pi * D ** 4 / 64, rel=1e-5)
    assert val(f"circle_polar_inertia({a}) = m^4") == pytest.approx(math.pi * D ** 4 / 32, rel=1e-5)
    assert val(f"circle_section_modulus({a}) = m^3") == pytest.approx(math.pi * D ** 3 / 32, rel=1e-5)


@pytest.mark.parametrize("do,uo,di,ui", [(40.0, "mm", 3.0, "cm"), (0.1, "m", 80.0, "mm"),
                                          (6.0, "cm", 1.0, "mm")])
def test_ring(do, uo, di, ui):
    O, I_ = si(do, uo), si(di, ui)
    a = f"{q(do, uo)}, {q(di, ui)}"
    assert val(f"ring_area({a}) = m^2") == pytest.approx(math.pi * (O ** 2 - I_ ** 2) / 4, rel=1e-5)
    assert val(f"ring_inertia({a}) = m^4") == pytest.approx(math.pi * (O ** 4 - I_ ** 4) / 64, rel=1e-5)
    assert val(f"ring_section_modulus({a}) = m^3") == pytest.approx(
        math.pi * (O ** 4 - I_ ** 4) / (32 * O), rel=1e-5)


def test_radius_of_gyration_is_sqrt_not_ratio():
    # rectangle: r = h/sqrt(12) about the horizontal axis
    r = val("radius_of_gyration(rect_inertia(50 mm, 100 mm), rect_area(50 mm, 100 mm)) = m")
    assert r == pytest.approx(0.1 / math.sqrt(12), rel=1e-5)
    # ring: r = sqrt(do^2+di^2)/4
    r = val("radius_of_gyration(ring_inertia(40 mm, 30 mm), ring_area(40 mm, 30 mm)) = mm")
    assert r == pytest.approx(math.sqrt(40 ** 2 + 30 ** 2) / 4, rel=1e-5)
    # direct inputs, mixed units
    r = val("radius_of_gyration(8 cm^4, 2 cm^2) = m")
    assert r == pytest.approx(math.sqrt(8e-8 / 2e-4), rel=1e-5)
    # solid circle exactly d/4
    assert run("radius_of_gyration(circle_inertia(40 mm), circle_area(40 mm)) = mm").output == "= 10 mm"


def test_polar_is_twice_inertia_and_ring_reduces_to_circle():
    a = val("circle_polar_inertia(33 mm) / circle_inertia(33 mm) =")
    assert a == pytest.approx(2.0, rel=1e-5)
    a = val("ring_inertia(33 mm, 1e-9 mm) / circle_inertia(33 mm) =")
    assert a == pytest.approx(1.0, rel=1e-9)


# ---------------- beams ----------------

def beam_args(P, uP, L, uL, E, uE, I_, uI):
    return (f"{q(P, uP)}, {q(L, uL)}, {q(E, uE)}, {I_!r} {uI}",
            si(P, uP), si(L, uL), si(E, uE), I_ * (FACT[uI.split("^")[0]] ** 4))


BEAMS = [(1.0, "kN", 2.0, "m", 200.0, "GPa", 1e-6, "m^4"),
         (7.5, "kN", 350.0, "cm", 70.0, "GPa", 2500.0, "cm^4"),
         (800.0, "N", 1200.0, "mm", 210000.0, "MPa", 3e5, "mm^4")]


@pytest.mark.parametrize("case", BEAMS)
def test_point_load_beams(case):
    s, P, L, E, I_ = beam_args(*case)
    assert val(f"cantilever_tip_deflection({s}) = m") == pytest.approx(P * L ** 3 / (3 * E * I_), rel=1e-5)
    assert val(f"simply_supported_center_deflection({s}) = m") == pytest.approx(
        P * L ** 3 / (48 * E * I_), rel=1e-5)


@pytest.mark.parametrize("case", BEAMS)
def test_udl_beams(case):
    P, uP, L, uL, E, uE, I_, uI = case
    w, uw = P, uP + "/m"
    s = f"{q(w, uw)}, {q(L, uL)}, {q(E, uE)}, {I_!r} {uI}"
    W, LL, EE = si(w, uP), si(L, uL), si(E, uE)
    II = I_ * FACT[uI.split("^")[0]] ** 4
    assert val(f"cantilever_udl_deflection({s}) = m") == pytest.approx(W * LL ** 4 / (8 * EE * II), rel=1e-5)
    assert val(f"simply_supported_udl_deflection({s}) = m") == pytest.approx(
        5 * W * LL ** 4 / (384 * EE * II), rel=1e-5)


def test_textbook_simply_supported_steel_beam():
    # 6 m span, uniform 10 kN/m, E = 200 GPa, I = 8000 cm^4: delta = 5wL^4/(384EI) = 0.0211 m
    d = val("simply_supported_udl_deflection(10 kN/m, 6 m, 200 GPa, 8000 cm^4) = mm")
    assert d == pytest.approx(5 * 10e3 * 6 ** 4 / (384 * 200e9 * 8000e-8) * 1000, rel=1e-5)
    assert 10.5 < d < 10.6
    m = val("simply_supported_udl_max_moment(10 kN/m, 6 m) = kN*m")
    assert m == pytest.approx(45.0, rel=1e-5)
    # bending stress at extreme fibre of a rectangular 100x300 section
    s = val("bending_stress(simply_supported_udl_max_moment(10 kN/m, 6 m), 150 mm, "
            "rect_inertia(100 mm, 300 mm)) = MPa")
    assert s == pytest.approx(45e3 * 0.15 / (0.1 * 0.3 ** 3 / 12) / 1e6, rel=1e-5)
    s2 = val("simply_supported_udl_max_moment(10 kN/m, 6 m) / rect_section_modulus(100 mm, 300 mm) = MPa")
    assert s2 == pytest.approx(s, rel=1e-5)


def test_max_moments_mixed_units():
    assert val("cantilever_tip_max_moment(2.5 kN, 350 cm) = N*m") == pytest.approx(2500 * 3.5, rel=1e-5)
    assert val("cantilever_udl_max_moment(3 kN/m, 400 cm) = N*m") == pytest.approx(3000 * 16 / 2, rel=1e-5)
    assert val("simply_supported_center_max_moment(12 kN, 800 mm) = N*m") == pytest.approx(12000 * 0.8 / 4, rel=1e-5)
    assert val("simply_supported_udl_max_moment(900 N/m, 5 m) = N*m") == pytest.approx(900 * 25 / 8, rel=1e-5)


def test_beam_scaling_laws():
    base = "200 GPa, 1e-6 m^4"
    f = lambda fn, a, L: f"{fn}({a}, {L}, {base})"
    assert val(f("cantilever_tip_deflection", "1 kN", "4 m") + " / " + f("cantilever_tip_deflection", "1 kN", "2 m") + " =") == pytest.approx(8.0, rel=1e-5)
    assert val(f("cantilever_udl_deflection", "1 kN/m", "4 m") + " / " + f("cantilever_udl_deflection", "1 kN/m", "2 m") + " =") == pytest.approx(16.0, rel=1e-5)
    # inertia doubling halves deflection
    assert val("cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 2e-6 m^4) / cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) =") == pytest.approx(0.5, rel=1e-5)
    # cantilever tip vs simply supported: ratio 16
    assert val("cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) / simply_supported_center_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) =") == pytest.approx(16.0, rel=1e-5)


def test_negative_load_allowed_and_sign_kept():
    assert val("cantilever_tip_max_moment(-1 kN, 2 m) = N*m") == pytest.approx(-2000, rel=1e-5)
    assert val("axial_stress(-10 kN, 100 mm^2) = MPa") == pytest.approx(-100, rel=1e-5)
    assert val("axial_strain(-0.5 mm, 2 m) =") == pytest.approx(-0.00025, rel=1e-5)
    assert val("cantilever_tip_deflection(-1 kN, 2 m, 200 GPa, 1e-6 m^4) = mm") == pytest.approx(-13.3333, rel=1e-5)


# ---------------- stress / strain ----------------

def test_stress_strain():
    assert val("axial_stress(12 kN, 3 cm^2) = Pa") == pytest.approx(12e3 / 3e-4, rel=1e-5)
    assert val("axial_strain(2 mm, 0.5 m) =") == pytest.approx(0.004, rel=1e-5)
    assert val("axial_strain(1 cm, 10 mm) =") == pytest.approx(1.0, rel=1e-5)
    assert val("axial_elongation(20 kN, 3 m, 4 cm^2, 70 GPa) = m") == pytest.approx(20e3 * 3 / (4e-4 * 70e9), rel=1e-5)
    assert val("bending_stress(1.2 kN*m, 60 mm, 3e6 mm^4) = Pa") == pytest.approx(1200 * 0.06 / 3e-6, rel=1e-5)
    assert val("hoop_stress(1.5 MPa, 30 cm, 8 mm) = Pa") == pytest.approx(1.5e6 * 0.3 / 0.008, rel=1e-5)
    assert val("longitudinal_stress(1.5 MPa, 30 cm, 8 mm) = Pa") == pytest.approx(1.5e6 * 0.3 / 0.016, rel=1e-5)
    assert val("hoop_stress(2 MPa, 1 m, 5 mm) / longitudinal_stress(2 MPa, 1 m, 5 mm) =") == pytest.approx(2.0, rel=1e-5)
    # Hooke consistency: elongation / L == stress / E
    e = val("axial_elongation(9 kN, 2 m, 150 mm^2, 200 GPa) / 2 m =")
    assert e == pytest.approx(9e3 / 150e-6 / 200e9, rel=1e-5)


def test_bending_stress_c_may_be_signed():
    assert val("bending_stress(500 N*m, -0.05 m, 8e-6 m^4) = MPa") == pytest.approx(-3.125, rel=1e-5)


def test_moment_unit_accepted_as_n_m_and_j_free():
    # N*m input in kN*m
    assert val("bending_stress(0.5 kN*m, 50 mm, 8e-6 m^4) = MPa") == pytest.approx(3.125, rel=1e-5)


# ---------------- columns ----------------

def test_euler():
    E_, I_, L, K = 200e9, 1e-6, 2.0, 1.0
    assert val("euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 1) = N") == pytest.approx(math.pi ** 2 * E_ * I_ / 4, rel=1e-5)
    for K in (0.5, 0.7, 2.0):
        assert val(f"euler_critical_load(200 GPa, 1e-6 m^4, 2 m, {K}) = N") == pytest.approx(
            math.pi ** 2 * E_ * I_ / (K * L) ** 2, rel=1e-5)
    # mixed units
    assert val("euler_critical_load(70000 MPa, 20 cm^4, 3000 mm, 0.7) = kN") == pytest.approx(
        math.pi ** 2 * 70e9 * 20e-8 / (0.7 * 3) ** 2 / 1e3, rel=1e-5)


def test_slenderness():
    assert val("slenderness_ratio(2 m, 1, 0.05 m) =") == pytest.approx(40, rel=1e-5)
    assert val("slenderness_ratio(3000 mm, 0.7, 2 cm) =") == pytest.approx(0.7 * 3 / 0.02, rel=1e-5)
    assert val("slenderness_ratio(2 m, 1, 50 mm) =") == pytest.approx(40, rel=1e-5)


def test_transition_slenderness_formula():
    # sqrt(2 pi^2 E / sy)
    assert val("euler_transition_slenderness(200 GPa, 250 MPa) =") == pytest.approx(
        math.sqrt(2 * math.pi ** 2 * 200e9 / 250e6), rel=1e-5)
    assert val("euler_transition_slenderness(70 GPa, 300 MPa) =") == pytest.approx(
        math.sqrt(2 * math.pi ** 2 * 70e9 / 300e6), rel=1e-5)
    # at the transition slenderness Euler stress equals half the yield strength
    lam = val("euler_transition_slenderness(200 GPa, 250 MPa) =")
    assert math.pi ** 2 * 200e9 / lam ** 2 == pytest.approx(125e6, rel=1e-5)


def test_euler_consistent_with_slenderness():
    # P_cr/A = pi^2 E / lambda^2 for a circle d = 40 mm, L = 1.5 m, K = 1
    pcr = val("euler_critical_load(200 GPa, circle_inertia(40 mm), 1.5 m, 1) = N")
    lam = 1.5 / (0.04 / 4)
    assert pcr / (math.pi * 0.04 ** 2 / 4) == pytest.approx(math.pi ** 2 * 200e9 / lam ** 2, rel=1e-5)


# ---------------- unit-rule errors ----------------

DIM_SLOTS = [
    ("rect_area(50, 100 mm)", "rect_area: b needs a unit of length, for example 1 mm"),
    ("rect_area(50 mm, 100)", "rect_area: h needs a unit of length, for example 1 mm"),
    ("rect_area(50 mm, 100 kg)", "rect_area: h must be a length, not kg"),
    ("circle_area(5 mm^2)", "circle_area: d must be a length"),
    ("euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 1 m)", "euler_critical_load: K must be dimensionless"),
    ("slenderness_ratio(2 m, 1 m, 0.05 m)", "slenderness_ratio: K must be dimensionless"),
    ("cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^2)", "cantilever_tip_deflection: I must be a second moment of area"),
    ("cantilever_tip_deflection(1 m, 2 m, 200 GPa, 1e-6 m^4)", "cantilever_tip_deflection: P must be a force"),
    ("cantilever_tip_deflection(1 kN, 2 m, 200 N, 1e-6 m^4)", "cantilever_tip_deflection: E must be a pressure"),
    ("cantilever_udl_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4)", "cantilever_udl_deflection: w must be a force per length"),
    ("cantilever_tip_max_moment(1 kN, 2)", "cantilever_tip_max_moment: L needs a unit of length"),
    ("cantilever_tip_max_moment(1, 2 m)", "cantilever_tip_max_moment: P needs a unit of force"),
    ("bending_stress(500 J, 0.05 m, 8e-6 m^4)", None),  # J == N*m dimensionally: must be accepted
    ("bending_stress(500 N, 0.05 m, 8e-6 m^4)", "bending_stress: M must be a moment"),
    ("axial_stress(10 kN, 100 mm)", "axial_stress: A must be a area"),
    ("axial_strain(0.5, 2 m)", "axial_strain: dL needs a unit of length"),
    ("hoop_stress(2, 500 mm, 10 mm)", "hoop_stress: p needs a unit of pressure"),
    ("euler_transition_slenderness(200 GPa, 250)", "euler_transition_slenderness: sy needs a unit of pressure"),
    ("radius_of_gyration(8 cm^4, 2 cm)", "radius_of_gyration: A must be"),
]


@pytest.mark.parametrize("src,frag", DIM_SLOTS)
def test_dimension_errors(src, frag):
    if frag is None:
        assert run(src + " =").status == "ok"
        return
    e = err(src + " =")
    assert frag in e, e


def test_wrong_arg_counts_all():
    for n, k in [("rect_area", 2), ("circle_area", 1), ("euler_critical_load", 4), ("hoop_stress", 3)]:
        e = err(f"{n}() =")
        assert "number of arguments" in e.lower() or "argument" in e.lower(), e
        e = err(f"{n}({', '.join(['1 m'] * (k + 1))}) =")
        assert "argument" in e.lower(), e


def test_nonpositive():
    assert "circle_inertia: d must be greater than zero" in err("circle_inertia(-40 mm) =")
    assert "rect_area: b must be greater than zero" in err("rect_area(-1 mm, 5 mm) =")
    assert "euler_critical_load: K must be greater than zero" in err("euler_critical_load(200 GPa, 1e-6 m^4, 2 m, -1) =")
    # zero K: bare 0 dimensionless
    assert "K must be greater than zero" in err("euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 0) =")
    assert "K must be greater than zero" in err("slenderness_ratio(2 m, 0, 1 m) =")
    # negative modulus / area / inertia / thickness
    assert "E must be greater than zero" in err("cantilever_tip_deflection(1 kN, 2 m, -200 GPa, 1e-6 m^4) =")
    assert "I must be greater than zero" in err("cantilever_tip_deflection(1 kN, 2 m, 200 GPa, -1e-6 m^4) =")
    assert "t must be greater than zero" in err("hoop_stress(1 MPa, 1 m, -5 mm) =")
    assert "A must be greater than zero" in err("axial_stress(1 kN, -5 mm^2) =")
    assert "L must be greater than zero" in err("cantilever_tip_max_moment(1 kN, -2 m) =")
    assert "sy must be greater than zero" in err("euler_transition_slenderness(200 GPa, -250 MPa) =")


def test_zero_dimensional_values_rejected_not_crash():
    # zero with unit may lose its unit in the engine (documented limitation); either message is fine,
    # but it must be an error without traceback and no result
    for src in ("circle_area(0 mm) =", "rect_area(0 m, 1 m) =", "axial_stress(1 kN, 0 mm^2) ="):
        r = run(src)
        assert r.status == "error" and "Traceback" not in r.error, (src, r.output, r.error)


def test_ring_ordering():
    assert "ring_inertia: do must be larger than di" in err("ring_inertia(30 mm, 40 mm) =")
    for fn in ("ring_area", "ring_section_modulus"):
        assert f"{fn}: do must be larger than di" in err(f"{fn}(30 mm, 40 mm) =")
        assert f"{fn}: do must be larger than di" in err(f"{fn}(40 mm, 40 mm) =")   # di == do
    assert "do must be larger than di" in err("ring_inertia(4 cm, 40 mm) =")      # equal after conversion


def test_complex_or_symbolic_input_error_not_traceback():
    r = run("cantilever_tip_max_moment(1 kN * I, 2 m) =")
    assert r.status == "error" and "Traceback" not in r.error
    r = run("rect_area(1 m, 2 m * sqrt(-1)) =")
    assert r.status == "error" and "Traceback" not in r.error


# ---------------- name collisions and sheet integration ----------------

def test_undefined_names_not_swallowed():
    e = err("cantilever_tip_deflection(P, L, E, I) =")
    assert "not defined" in e or "undefined" in e.lower()
    e = err("rect_area(b, h) =")
    assert "b" in e and "h" in e and "not defined" in e


def test_defined_variables_pass_through():
    r = run("P := 1 kN", "Ls := 2 m", "Ee := 200 GPa", "Ii := 1e-6 m^4",
            "cantilever_tip_deflection(P, Ls, Ee, Ii) = mm")
    assert r.status == "ok" and parse(r.output) == pytest.approx(13.3333, rel=1e-5)


def test_shadowing_name_collisions_E_I_L():
    # user variables called E / I / L are not accepted as euler/imag/litre silently
    # arg names inside the library must not break when the user defines E-ish names
    r = run("Es := 200 GPa", "Is := 1e-6 m^4", "euler_critical_load(Es, Is, 2 m, 1) = kN")
    assert r.status == "ok" and parse(r.output) == pytest.approx(493.48, rel=1e-5)
    # bare E (Euler number) and I (imaginary) are not accepted in dimensional slots
    assert run("euler_critical_load(E, 1e-6 m^4, 2 m, 1) =").status == "error"
    assert run("radius_of_gyration(I, 1 m^2) =").status == "error"
    # L is litre: 1 L is a volume, not a length -> dimension error
    assert "must be a length" in err("rect_area(1 L, 1 m) =")


def test_user_function_bodies():
    r = run("f(x) := rect_area(x, 100 mm)", "f(50 mm) = m^2")
    assert r.status == "ok" and parse(r.output) == pytest.approx(0.005, rel=1e-5)
    r = run("defl(P, L) := cantilever_tip_deflection(P, L, 200 GPa, 1e-6 m^4)", "defl(1 kN, 2 m) = mm")
    assert r.status == "ok" and parse(r.output) == pytest.approx(13.3333, rel=1e-5)
    # error raised at call time with the library's own wording
    r = run("f(x) := rect_area(x, 100 mm)", "f(50) =")
    assert r.status == "error" and "rect_area: b needs a unit of length" in r.error
    r = run("g(d) := circle_inertia(d) / circle_area(d)", "g(40 mm) = mm^2")
    assert r.status == "ok" and parse(r.output) == pytest.approx(40 ** 2 / 16, rel=1e-5)


def test_bare_equals_prints_si_and_unit_conversion():
    assert run("rect_area(50 mm, 100 mm) =").output == "= 0.005 m²"
    assert val("rect_area(50 mm, 100 mm) = cm^2") == pytest.approx(50.0, rel=1e-5)
    assert val("axial_stress(10 kN, 100 mm^2) = kPa") == pytest.approx(1e5, rel=1e-5)


def test_wrong_display_unit_for_result():
    r = run("rect_area(50 mm, 100 mm) = kg")
    assert r.status == "error"


def test_dimensionless_results_have_no_unit():
    for src in ("axial_strain(0.5 mm, 2 m) =", "slenderness_ratio(2 m, 1, 0.05 m) =",
                "euler_transition_slenderness(200 GPa, 250 MPa) ="):
        out = run(src).output
        assert out.startswith("=") and len(out.split()) == 2, out


def test_results_usable_in_arithmetic_and_variables():
    r = run("A := circle_area(40 mm)", "s := axial_stress(10 kN, A)", "s = MPa")
    assert r.status == "ok" and parse(r.output) == pytest.approx(1e4 / (math.pi * 0.04 ** 2 / 4) / 1e6, rel=1e-5)
    r = run("2 * rect_area(1 m, 1 m) + 3 m^2 = m^2")
    assert r.status == "ok" and parse(r.output) == pytest.approx(5, rel=1e-5)


def test_vector_argument_does_not_traceback():
    r = run("rect_area([1; 2] m, 1 m) =")
    assert "Traceback" not in (r.error or "")   # error or elementwise are both acceptable


def test_no_imperial_units_in_engine_unit_table():
    for u in ("psi", "ksi", "lbf"):
        r = run(f"axial_stress(10 kN, 100 mm^2) = {u}")
        assert r.status == "error", u
