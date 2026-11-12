"""Independent black-box tests for spec 013, phase 1 (DXF profile import, single closed
straight-sided loop -> section properties -- ``docs/board/specs/013-dxf-profile-import-core.md``).

Written from the spec's own acceptance criteria and "Behaviour" section, not from the
developer's implementation or the developer's own tests (``tests/test_cadprofile.py``,
``tests/test_wiring_cadprofile.py``), which are deliberately not read for test-case ideas.

The worked-example triangle's section properties are re-derived here independently, with exact
``fractions.Fraction`` arithmetic (an independent route from both the spec's own stated decimal
numbers and the implementation's floating-point computation) applying the shoelace-formula-
family math the spec's own "Behaviour" section states, in a standalone script, not by importing
anything from ``livesheet``:

    area = 400 (exact)
    centroid_x = 40/3, centroid_y = 20/3
    Ixx = 80000/9, Iyy = 320000/9, Ixy = -80000/9, J = 400000/9
    rx = sqrt(200/9), ry = sqrt(800/9)
    c_top = 40/3, c_bottom = 20/3, c_left = 40/3, c_right = 80/3
    Sx_top = 666.667, Sx_bottom = 1333.33, Sy_left = 2666.67, Sy_right = 1333.33

These match the spec's own stated worked numbers exactly (cross-checked, not just trusted), and
are what every numeric assertion below compares against.

Every ``.dxf`` fixture is generated at test time via ezdxf's own write API (``ezdxf.new()``,
``.modelspace().add_lwpolyline(...)``/``.add_polyline2d(...)``/``.add_circle(...)``/etc.,
``doc.header['$INSUNITS'] = ...``, ``doc.saveas(...)``) -- never a hand-authored raw-tagged-text
file and never anyone else's example file, per the spec's own test-fixture discipline.

Pure Python/SymPy/ezdxf engine-level tests plus one GUI-level (headless, offscreen) round-trip
test for acceptance criterion 11.
"""

from __future__ import annotations

import math
import os

import ezdxf
import pytest
import sympy as sp

from livesheet.engine.cadprofile import CadProfileError, section_properties
from livesheet.engine.evaluator import Engine
from livesheet.engine.units import UNITS, UnitError, measure
from livesheet.engine.wiring import ComponentSpec, WireSpec, evaluate

# Worked example from the spec's own acceptance criteria: a right triangle, CCW wound,
# $INSUNITS = 4 (millimetres).
TRIANGLE_CCW = [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]
# Same triangle, same polygon, wound the other way (CW) -- used to independently verify the
# developer's disclosed clockwise-sign-flip fix (reverse the vertex list up front when the raw
# signed area is negative).
TRIANGLE_CW = [(0.0, 0.0), (0.0, 20.0), (40.0, 0.0)]

# Exact values re-derived independently with fractions.Fraction arithmetic (see module docstring).
EXPECTED = dict(
    area=400.0, centroid_x=40 / 3, centroid_y=20 / 3,
    Ixx=80000 / 9, Iyy=320000 / 9, Ixy=-80000 / 9, J=400000 / 9,
    rx=math.sqrt(200 / 9), ry=math.sqrt(800 / 9),
    Sx_top=666.6666666666666, Sx_bottom=1333.3333333333333,
    Sy_left=2666.6666666666665, Sy_right=1333.3333333333333,
)

TOL = 1e-6


def _approx(x):
    return pytest.approx(x, rel=TOL, abs=1e-9)


# ===========================================================================
# Pure math: section_properties() against the independently re-derived numbers
# ===========================================================================

def test_section_properties_matches_hand_derived_triangle_ccw():
    # NOTE (spec 014 signature generalisation, mechanical update only -- see docs/board/log.md's
    # spec-014 developer entry): section_properties() now takes a list of loops, not one flat
    # vertex list; a single-loop call becomes section_properties([one_loop]) per spec 014's own
    # architecture note. This is the only change in this function; the assertions are untouched.
    props = section_properties([TRIANGLE_CCW])
    for field, expected in EXPECTED.items():
        assert getattr(props, field) == _approx(expected), field


def test_section_properties_clockwise_winding_gives_identical_area_and_moments():
    """The one thing the task asks to specifically verify independently: a clockwise-wound
    version of the worked-example triangle must give identical area/Ixx/Iyy/Ixy/J/rx/ry to the
    CCW version (the sign-flip-on-clockwise-winding fix), not a crash, not different numbers."""
    ccw = section_properties([TRIANGLE_CCW])
    cw = section_properties([TRIANGLE_CW])
    for field in ("area", "centroid_x", "centroid_y", "Ixx", "Iyy", "Ixy", "J", "rx", "ry",
                  "Sx_top", "Sx_bottom", "Sy_left", "Sy_right"):
        assert getattr(cw, field) == _approx(getattr(ccw, field)), field


def test_section_properties_rejects_collinear_points_zero_area():
    with pytest.raises(CadProfileError, match="zero area"):
        section_properties([[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]])


def test_section_properties_rejects_fewer_than_three_distinct_vertices():
    with pytest.raises(CadProfileError, match="zero area"):
        section_properties([[(0.0, 0.0), (5.0, 5.0), (0.0, 0.0)]])


def test_section_properties_self_intersecting_does_not_crash():
    """Spec's own edge case: "a self-intersecting input produces a mathematically meaningless
    but non-crashing numeric answer." (A *symmetric* bowtie's crossing cancels to exactly zero
    net signed area -- verified by hand -- so this uses an asymmetric self-intersecting quad
    instead, confirmed non-zero-area first.)

    Previously a documented, left-failing defect repro (an uncaught ValueError from
    math.sqrt()); fixed by the developer (see docs/board/log.md's spec-013 sqrt-guard-fix
    entry) by guarding rx/ry with abs() -- this now passes."""
    bowtie = [(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (14.0, 0.0)]
    props = section_properties([bowtie])
    assert math.isfinite(props.area)
    assert math.isfinite(props.Ixx)


# ===========================================================================
# DXF fixture helper (generated at test time via ezdxf's own write API only)
# ===========================================================================

def _write_dxf(tmp_path, filename, *, insunits=4, loops=None, extra=None):
    """``loops``: list of ``(vertices, layer_name_or_None)`` closed straight LWPOLYLINEs.
    ``extra``: list of callables ``f(msp)`` adding any other entity."""
    doc = ezdxf.new()
    if insunits is None:
        if "$INSUNITS" in doc.header:
            del doc.header["$INSUNITS"]
    else:
        doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    for _verts, layer in loops or []:
        if layer and layer not in doc.layers:
            doc.layers.add(layer)
    for verts, layer in loops or []:
        attribs = {"layer": layer} if layer else {}
        msp.add_lwpolyline(verts, close=True, dxfattribs=attribs)
    for build in extra or []:
        build(msp)
    path = tmp_path / filename
    doc.saveas(str(path))
    return str(path)


@pytest.fixture
def engine():
    return Engine()


def _mag(value, unit_name, power=1):
    """float magnitude of a unit-bearing SymPy value, expressed in ``unit_name ** power``."""
    return float(sp.nsimplify(value / (UNITS[unit_name] ** power)))


# ===========================================================================
# Criterion 1: purely additive -- a sheet with no cad-profile component is unaffected
# ===========================================================================

def test_criterion1_non_cad_profile_components_unaffected(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "5 m"}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a * 2"}),
    ]
    wires = [WireSpec("V1", "value", "F1", "a")]
    results = evaluate(specs, wires, engine)
    assert results["V1"].status == "ok"
    assert results["F1"].status == "ok"
    m = measure(results["F1"].outputs["result"])
    assert m.magnitude == _approx(10.0)
    assert m.dims == (("length", 1),)


# ===========================================================================
# Criterion 2: worked-example triangle, no overrides
# ===========================================================================

def test_criterion2_worked_example_triangle_all_ports(tmp_path, engine):
    path = _write_dxf(tmp_path, "tri.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error

    assert _mag(result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(EXPECTED["centroid_x"])
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(EXPECTED["centroid_y"])
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(EXPECTED["Ixx"])
    assert _mag(result.outputs["Iyy"], "mm", 4) == _approx(EXPECTED["Iyy"])
    assert _mag(result.outputs["Ixy"], "mm", 4) == _approx(EXPECTED["Ixy"])
    assert _mag(result.outputs["J"], "mm", 4) == _approx(EXPECTED["J"])
    assert _mag(result.outputs["rx"], "mm") == _approx(EXPECTED["rx"])
    assert _mag(result.outputs["ry"], "mm") == _approx(EXPECTED["ry"])
    assert _mag(result.outputs["Sx_top"], "mm", 3) == _approx(EXPECTED["Sx_top"])
    assert _mag(result.outputs["Sx_bottom"], "mm", 3) == _approx(EXPECTED["Sx_bottom"])
    assert _mag(result.outputs["Sy_left"], "mm", 3) == _approx(EXPECTED["Sy_left"])
    assert _mag(result.outputs["Sy_right"], "mm", 3) == _approx(EXPECTED["Sy_right"])

    outline = result.outputs["outline"]
    assert outline.shape == (3, 2)
    for i, (x, y) in enumerate(TRIANGLE_CCW):
        assert _mag(outline[i, 0], "mm") == _approx(x)
        assert _mag(outline[i, 1], "mm") == _approx(y)


def test_criterion2_clockwise_fixture_gives_identical_properties_but_different_outline_order(
        tmp_path, engine):
    """Independent check of the developer's disclosed subtlety, through the *whole* wiring path
    (not just the pure-math function): a clockwise-wound DXF fixture must give identical
    area/Ixx/Iyy/rx/ry to the CCW fixture, while ``outline`` (raw file-order vertices, never
    reordered) differs in winding order between the two fixtures."""
    path_ccw = _write_dxf(tmp_path, "ccw.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    path_cw = _write_dxf(tmp_path, "cw.dxf", insunits=4, loops=[(TRIANGLE_CW, None)])
    specs = [
        ComponentSpec("CCW", "cad-profile", {"path": path_ccw, "layer": "", "unit": ""}),
        ComponentSpec("CW", "cad-profile", {"path": path_cw, "layer": "", "unit": ""}),
    ]
    results = evaluate(specs, [], engine)
    ccw, cw = results["CCW"], results["CW"]
    assert ccw.status == "ok", ccw.error
    assert cw.status == "ok", cw.error
    for port in ("area", "centroid_x", "centroid_y", "Ixx", "Iyy", "Ixy", "J", "rx", "ry",
                 "Sx_top", "Sx_bottom", "Sy_left", "Sy_right"):
        m_ccw, m_cw = measure(ccw.outputs[port]), measure(cw.outputs[port])
        assert m_cw.magnitude == _approx(float(m_ccw.magnitude)), port
        assert m_cw.dims == m_ccw.dims, port

    ccw_outline = [(_mag(ccw.outputs["outline"][i, 0], "mm"),
                    _mag(ccw.outputs["outline"][i, 1], "mm")) for i in range(3)]
    cw_outline = [(_mag(cw.outputs["outline"][i, 0], "mm"),
                   _mag(cw.outputs["outline"][i, 1], "mm")) for i in range(3)]
    assert [(round(x, 6), round(y, 6)) for x, y in ccw_outline] == TRIANGLE_CCW
    assert [(round(x, 6), round(y, 6)) for x, y in cw_outline] == TRIANGLE_CW
    assert ccw_outline != cw_outline


# ===========================================================================
# Criterion 3: missing $INSUNITS, explicit unit override substitutes cleanly
# ===========================================================================

def test_criterion3_missing_insunits_with_explicit_unit_override(tmp_path, engine):
    path = _write_dxf(tmp_path, "tri_nounits.dxf", insunits=None, loops=[(TRIANGLE_CCW, None)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": "mm"})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(EXPECTED["Ixx"])


# ===========================================================================
# Criterion 4: layer filter picks the right one of two closed profiles
# ===========================================================================

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]  # area 100, centroid (5, 5)


def _two_layer_fixture(tmp_path):
    return _write_dxf(
        tmp_path, "layered.dxf", insunits=4,
        loops=[(TRIANGLE_CCW, "profile"), (SQUARE, "scrap")])


def test_criterion4_layer_filter_selects_triangle(tmp_path, engine):
    path = _two_layer_fixture(tmp_path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "profile", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(EXPECTED["Ixx"])


def test_criterion4_layer_filter_selects_square(tmp_path, engine):
    path = _two_layer_fixture(tmp_path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "scrap", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(100.0)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(5.0)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(5.0)


# ===========================================================================
# Criterion 5: blank path
# ===========================================================================

def test_criterion5_blank_path_error(engine):
    specs = [ComponentSpec("P1", "cad-profile", {"path": "", "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == "No DXF file path set."


# ===========================================================================
# Criterion 6: layer blank with two candidates -> multiple-profiles error
# ===========================================================================

def test_criterion6_two_same_winding_candidates_is_now_a_winding_mismatch_per_spec_014(
        tmp_path, engine):
    """UPDATED for spec 014 (see docs/board/log.md's dev note): spec 014 explicitly supersedes
    013's own "2+ candidates is always ambiguous" rule (013's acceptance criterion 6) with a
    more exact outer/hole diagnosis. This fixture's two candidates (the worked-example triangle
    and the square, both written counter-clockwise by ``_write_dxf``) are not a valid
    outer+hole pair -- a second counter-clockwise loop alongside the largest one is exactly
    spec 014's own "more than one counter-clockwise loop" winding-mismatch case, not 013's
    generic "multiple profiles found" message."""
    path = _two_layer_fixture(tmp_path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")


# ===========================================================================
# Criterion 7: standalone CIRCLE only -> curved/out-of-scope error
# ===========================================================================

def test_criterion7_standalone_circle_only_is_now_supported_per_spec_014(tmp_path, engine):
    """UPDATED for spec 014 (see docs/board/log.md's dev note): a standalone ``CIRCLE`` entity
    is spec 014's own criterion 1 -- tessellated into a 36-gon (10 degrees/segment), directly
    superseding 013's "curved segments ... not yet supported" error for this exact case."""
    path = _write_dxf(tmp_path, "circle.dxf", insunits=4,
                       extra=[lambda msp: msp.add_circle((0, 0), radius=5)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(0.5 * 36 * 5.0 ** 2 *
                                                              math.sin(math.radians(10)))
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(0.0)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(0.0)


def test_edgecase_standalone_line_only_is_now_a_line_chaining_error_per_spec_014(
        tmp_path, engine):
    """UPDATED for spec 014 (see docs/board/log.md's dev note): a single standalone ``LINE`` is
    still an error (it can never close into a loop by itself -- both its endpoints have degree
    1, not 2), but spec 014's ``LINE``-chaining pass now gives a more exact diagnosis than
    013's generic "curved segments or separate line segments" message."""
    path = _write_dxf(tmp_path, "line.dxf", insunits=4,
                       extra=[lambda msp: msp.add_line((0, 0), (10, 10))])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Could not assemble a single closed loop from LINE entities on this layer.")


def test_edgecase_bulged_polyline_segment_is_now_supported_per_spec_014(tmp_path, engine):
    """UPDATED for spec 014 (see docs/board/log.md's dev note): a closed polyline with one
    nonzero-bulge segment is spec 014's own "fully supported here (013 only handled the
    all-straight case)" edge case -- directly superseding 013's own "out of this phase's
    scope" edge case that used this exact fixture. The bulge arcs outward along the
    (0,0)-(10,0) edge (away from the opposite vertex (10,10)), so the resulting area must
    exceed the all-straight right triangle's own 50 mm^2."""
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0, 0, 0, 0.5), (10, 0, 0, 0, 0), (10, 10, 0, 0, 0)], format="xyseb",
                        close=True)
    path = str(tmp_path / "bulge.dxf")
    doc.saveas(path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) > 50.0


# ===========================================================================
# Criterion 8: no $INSUNITS and no override -> unusable-unit error
# ===========================================================================

def test_criterion8_missing_insunits_and_no_override_errors(tmp_path, engine):
    path = _write_dxf(tmp_path, "nounits.dxf", insunits=None, loops=[(TRIANGLE_CCW, None)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Drawing has no usable unit information; set 'unit' in this component's "
        "configuration, e.g. 'mm'.")


@pytest.mark.parametrize("insunits_code", [0, 8, 9, 99])
def test_edgecase_unrecognised_insunits_code_also_errors(tmp_path, engine, insunits_code):
    path = _write_dxf(tmp_path, f"u{insunits_code}.dxf", insunits=insunits_code,
                       loops=[(TRIANGLE_CCW, None)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert "no usable unit information" in result.error


# ===========================================================================
# Criterion 9: unknown unit override
# ===========================================================================

def test_criterion9_unknown_unit_override_errors(tmp_path, engine):
    path = _write_dxf(tmp_path, "tri.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": "banana"})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Unknown length unit 'banana'; use one of LiveSheet's existing length units, "
        "e.g. 'mm', 'm', 'km'.")


# ===========================================================================
# Criterion 10: wiring area -> a Formula component, zero special-casing
# ===========================================================================

def test_criterion10_wire_area_into_formula_component(tmp_path, engine):
    path = _write_dxf(tmp_path, "tri.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    specs = [
        ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a"}),
    ]
    wires = [WireSpec("P1", "area", "F1", "a")]
    results = evaluate(specs, wires, engine)
    assert results["P1"].status == "ok"
    assert results["F1"].status == "ok", results["F1"].error
    m_area = measure(results["P1"].outputs["area"])
    m_result = measure(results["F1"].outputs["result"])
    assert m_result.magnitude == _approx(float(m_area.magnitude))
    assert m_result.dims == m_area.dims
    assert _mag(results["F1"].outputs["result"], "mm", 2) == _approx(EXPECTED["area"])


def test_edgecase_incompatible_unit_mix_on_cad_profile_output_fails_cleanly(tmp_path, engine):
    """Feeding a cad-profile output into an incompatible operation fails with the engine's
    existing "Units do not match" message -- no special-casing for this kind's outputs."""
    path = _write_dxf(tmp_path, "tri.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    specs = [
        ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a + 1"}),
    ]
    wires = [WireSpec("P1", "area", "F1", "a")]
    results = evaluate(specs, wires, engine)
    assert results["F1"].status == "error"
    assert results["F1"].error == "Units do not match"


# ===========================================================================
# Criterion 11: .lsheet save/round-trip, through the real GUI Worksheet
# ===========================================================================

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_criterion11_lsheet_round_trip(tmp_path):
    try:
        import PySide6.QtWidgets  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"PySide6 cannot be loaded: {exc}")

    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QApplication

    from livesheet.document import SheetDocument
    from livesheet.gui.worksheet import Worksheet

    QApplication.instance() or QApplication([])

    dxf_path = _write_dxf(tmp_path, "tri.dxf", insunits=4, loops=[(TRIANGLE_CCW, None)])
    ws = Worksheet()
    config = {"path": dxf_path, "layer": "", "unit": ""}
    region = ws.add_component_region("P1", "cad-profile", config, QPointF(40, 40))
    ws.recalculate()
    assert region.result is not None and region.result.status == "ok", (
        region.result.error if region.result else "no result")

    lsheet_path = tmp_path / "profile.lsheet"
    doc_before = ws.to_document()
    comp_region_before = [r for r in doc_before.regions if r.kind == "component"][0]
    assert comp_region_before.component_kind == "cad-profile"
    assert comp_region_before.component_name == "P1"
    assert comp_region_before.config == config
    assert doc_before.version() == 3
    doc_before.save(lsheet_path)

    ws2 = Worksheet()
    doc_after = SheetDocument.load(lsheet_path)
    comp_region_after = [r for r in doc_after.regions if r.kind == "component"][0]
    assert comp_region_after.component_kind == "cad-profile"
    assert comp_region_after.component_name == "P1"
    assert comp_region_after.config == config

    ws2.load_document(doc_after)   # recalculates on load with no further user action
    region2 = [r for r in ws2.component_regions() if r.component_name == "P1"][0]
    assert region2.result is not None and region2.result.status == "ok"
    assert _mag(region2.result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
    assert _mag(region2.result.outputs["Ixx"], "mm", 4) == _approx(EXPECTED["Ixx"])


# ===========================================================================
# Edge cases from the spec's own "Edge cases" section
# ===========================================================================

def test_edgecase_file_does_not_exist(engine):
    specs = [ComponentSpec(
        "P1", "cad-profile", {"path": "/no/such/directory/missing.dxf", "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error.startswith("Could not open DXF file:")
    assert len(result.error) <= 160


def test_edgecase_corrupted_not_a_dxf_file(tmp_path, engine):
    path = tmp_path / "garbage.dxf"
    path.write_text("this is not a dxf file at all\njust some random text\n")
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == "Could not read DXF file: not a valid DXF file."


def test_edgecase_no_entities_at_all_text_only(tmp_path, engine):
    path = _write_dxf(tmp_path, "textonly.dxf", insunits=4,
                       extra=[lambda msp: msp.add_text("hello", dxfattribs={"insert": (0, 0)})])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "No closed profile found (phase 1 supports one closed straight-sided polyline "
        "entity only).")


def test_edgecase_zero_entities_empty_file(tmp_path, engine):
    path = _write_dxf(tmp_path, "empty.dxf", insunits=4, loops=[])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "No closed profile found (phase 1 supports one closed straight-sided polyline "
        "entity only).")


def test_edgecase_block_insert_entities_not_traversed(tmp_path, engine):
    """A closed profile defined only inside a BLOCK, referenced via INSERT, is invisible to this
    component -- the modelspace, with only the INSERT entity, has no usable profile."""
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    block = doc.blocks.new(name="MYBLOCK")
    block.add_lwpolyline(TRIANGLE_CCW, close=True)
    msp = doc.modelspace()
    msp.add_blockref("MYBLOCK", (0, 0))
    path = str(tmp_path / "block.dxf")
    doc.saveas(path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "No closed profile found (phase 1 supports one closed straight-sided polyline "
        "entity only).")


def test_edgecase_z_coordinate_on_2d_polyline_vertices_is_ignored(tmp_path, engine):
    """Group-code-30 Z values on an (otherwise 2D) POLYLINE's vertices are read and ignored --
    the profile is flattened onto its own X/Y plane regardless of Z, giving identical results to
    the same loop with Z=0 everywhere."""
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_polyline2d(
        [(0, 0, 5), (40, 0, -3), (0, 20, 7)], close=True)
    path = str(tmp_path / "zcoord.dxf")
    doc.saveas(path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(EXPECTED["Ixx"])
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(EXPECTED["centroid_x"])


def test_edgecase_polyline_entity_kind_also_recognised_not_just_lwpolyline(tmp_path, engine):
    """Spec names both LWPOLYLINE and (2D) POLYLINE as recognised candidate entity kinds."""
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_polyline2d([(x, y) for x, y in TRIANGLE_CCW], close=True)
    path = str(tmp_path / "poly2d.dxf")
    doc.saveas(path)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(EXPECTED["area"])
