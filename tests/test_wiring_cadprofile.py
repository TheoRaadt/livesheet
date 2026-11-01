"""Developer tests for spec 013, phase 1 (`docs/board/specs/013-dxf-profile-import-core.md`), and
spec 014, phase 2 (`docs/board/specs/014-dxf-profile-geometry-extensions.md`), engine-level:
acceptance criteria driven through ``wiring.evaluate()``. Fixture ``.dxf`` files are generated at
test time via ezdxf's own write API (``ezdxf.new()``, ``.modelspace().add_lwpolyline(...)``/
``.add_arc(...)``/``.add_circle(...)``/``.add_line(...)``, ``doc.header['$INSUNITS'] = ...``,
``doc.saveas(...)``) -- never a hand-authored raw-tagged-text file and never anyone else's
example file, so there is no copied-content question at all, and the fixtures are trivially
correct (ezdxf's own writer guarantees well-formed output). Pure Python/SymPy, no Qt import.

Two of spec 013's own tests below were updated for spec 014's explicitly-disclosed, spec-mandated
behaviour changes (see docs/board/log.md's spec-014 developer entry for the full disclosure):
spec 014 explicitly supersedes spec 013's own acceptance criterion 6 (its own text: "superseding
spec 013's own '2+ candidates is always ambiguous' rule (013's acceptance criterion 6) for
exactly the case this composite check accepts") and explicitly makes a standalone CIRCLE and a
mixed straight/bulge LWPOLYLINE newly supported (spec 014's own criteria 1 and its "mixes some
zero-bulge and some nonzero-bulge segments" edge case) where spec 013 treated both as out of
scope -- so ``test_criterion6_no_layer_filter_finds_multiple_profiles`` and
``test_edge_case_bulged_segment_is_out_of_scope`` below now assert the new, intentional
behaviour instead of the superseded one.
"""

from __future__ import annotations

import math

import ezdxf
import pytest

from livesheet.engine.evaluator import Engine
from livesheet.engine.units import UNITS, measure
from livesheet.engine.wiring import ComponentSpec, WireSpec, evaluate

TRIANGLE = [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]
SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


@pytest.fixture
def engine() -> Engine:
    return Engine()


def _make_dxf(tmp_path, name: str, *, insunits: int | None = 4,
              polylines: list[tuple[list[tuple[float, float]], str]] | None = None,
              extra_entities=None) -> str:
    """Write a minimal DXF file with the given closed LWPOLYLINE loops (each ``(vertices,
    layer)``) via ezdxf's own write API; ``insunits=None`` omits ``$INSUNITS`` entirely."""
    doc = ezdxf.new()
    if insunits is None:
        del doc.header["$INSUNITS"]
    else:
        doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    for layer_name in {layer for _, layer in (polylines or []) if layer}:
        if layer_name not in doc.layers:
            doc.layers.add(layer_name)
    for verts, layer in polylines or []:
        attribs = {"layer": layer} if layer else {}
        msp.add_lwpolyline(verts, close=True, dxfattribs=attribs)
    for build in extra_entities or []:
        build(msp)
    path = tmp_path / name
    doc.saveas(str(path))
    return str(path)


def _area_m2(mag) -> float:
    return float(measure(mag).magnitude)


# ===========================================================================
# Criterion 1: purely additive, a sheet with no cad-profile component is unaffected
# ===========================================================================

def test_criterion1_sheet_without_cad_profile_unaffected(engine):
    specs = [ComponentSpec("V", "value", {"expr": "1 m"})]
    result = evaluate(specs, [], engine)
    assert result["V"].status == "ok"


# ===========================================================================
# Criterion 2: worked-example triangle, no overrides
# ===========================================================================

def test_criterion2_worked_example_triangle(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri.dxf", insunits=4, polylines=[(TRIANGLE, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    r = result["P1"]
    assert r.status == "ok", r.error

    mm = UNITS["mm"]
    expected = {
        "area": 400 * mm ** 2,
        "centroid_x": (40 / 3) * mm,
        "centroid_y": (20 / 3) * mm,
        "Ixx": (80000 / 9) * mm ** 4,
        "Iyy": (320000 / 9) * mm ** 4,
        "Ixy": (-80000 / 9) * mm ** 4,
        "J": (400000 / 9) * mm ** 4,
        "rx": math.sqrt(200 / 9) * mm,
        "ry": math.sqrt(800 / 9) * mm,
        "Sx_top": (2000 / 3) * mm ** 3,
        "Sx_bottom": (4000 / 3) * mm ** 3,
        "Sy_left": (8000 / 3) * mm ** 3,
        "Sy_right": (4000 / 3) * mm ** 3,
    }
    for port, exp in expected.items():
        got = measure(r.outputs[port])
        want = measure(exp)
        assert got.dims == want.dims, port
        assert float(got.magnitude) == pytest.approx(float(want.magnitude), rel=1e-6), port

    outline = r.outputs["outline"]
    assert outline.shape == (3, 2)
    rows = [(float(measure(outline[i, 0]).magnitude), float(measure(outline[i, 1]).magnitude))
            for i in range(3)]
    want_rows = [(x * float(measure(mm).magnitude), y * float(measure(mm).magnitude))
                 for x, y in TRIANGLE]
    for got_row, want_row in zip(rows, want_rows):
        assert got_row[0] == pytest.approx(want_row[0], abs=1e-12)
        assert got_row[1] == pytest.approx(want_row[1], abs=1e-12)


# ===========================================================================
# Criterion 3: missing $INSUNITS, explicit unit override substitutes cleanly
# ===========================================================================

def test_criterion3_missing_insunits_with_explicit_unit_override(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri_nounits.dxf", insunits=None, polylines=[(TRIANGLE, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": "mm"})]
    result = evaluate(specs, [], engine)
    r = result["P1"]
    assert r.status == "ok", r.error
    assert _area_m2(r.outputs["area"]) == pytest.approx(_area_m2(400 * UNITS["mm"] ** 2))


# ===========================================================================
# Criterion 4: layer filter selects the triangle or the square independently
# ===========================================================================

def test_criterion4_layer_filter_selects_one_profile(tmp_path, engine):
    path = _make_dxf(tmp_path, "layers.dxf", insunits=4,
                      polylines=[(TRIANGLE, "profile"), (SQUARE, "scrap")])

    specs_profile = [ComponentSpec(
        "P1", "cad-profile", {"path": path, "layer": "profile", "unit": ""})]
    result = evaluate(specs_profile, [], engine)
    assert result["P1"].status == "ok"
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(400 * UNITS["mm"] ** 2))

    specs_scrap = [ComponentSpec(
        "P1", "cad-profile", {"path": path, "layer": "scrap", "unit": ""})]
    result2 = evaluate(specs_scrap, [], engine)
    assert result2["P1"].status == "ok"
    assert _area_m2(result2["P1"].outputs["area"]) == pytest.approx(
        _area_m2(100 * UNITS["mm"] ** 2))


# ===========================================================================
# Criterion 5: blank path
# ===========================================================================

def test_criterion5_blank_path_errors(engine):
    specs = [ComponentSpec("P1", "cad-profile", {"path": "", "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == "No DXF file path set."


# ===========================================================================
# Criterion 6: layer+scrap fixture, no layer filter -> multiple profiles
# ===========================================================================

def test_criterion6_no_layer_filter_finds_multiple_profiles(tmp_path, engine):
    """UPDATED for spec 014 (see module docstring): both TRIANGLE and SQUARE here are wound
    counter-clockwise and SQUARE's bounding box happens to sit inside TRIANGLE's, so under spec
    014's composite outer/hole rule this is exactly the "two separate valid profiles, not one
    profile with a winding mistake" edge case spec 014 itself names as explicitly out of scope
    (its own Behaviour point 3) -- it now fails the winding-mismatch check (SQUARE is CCW, not
    the required CW for a hole) instead of spec 013's old, more generic "multiple profiles"
    message, which spec 014's own text says this scenario supersedes."""
    path = _make_dxf(tmp_path, "layers.dxf", insunits=4,
                      polylines=[(TRIANGLE, "profile"), (SQUARE, "scrap")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")


# ===========================================================================
# Criterion 7 (013): standalone CIRCLE only -- superseded by spec 014's own criterion 1
# ===========================================================================

def test_criterion7_standalone_circle_only_is_now_supported_per_spec_014(tmp_path, engine):
    """RENAMED/UPDATED for spec 014 (see module docstring): a standalone CIRCLE is spec 014's
    own criterion 1's example of newly-supported tessellated geometry, directly superseding
    013's own criterion 7 (which used this exact "lone CIRCLE" scenario as its own out-of-scope
    example). Numbers cross-checked against the 36-gon formula in tests/test_cadprofile.py."""
    path = _make_dxf(tmp_path, "circle.dxf", insunits=4,
                      extra_entities=[lambda msp: msp.add_circle((0, 0), 5)])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    expected_area = 0.5 * 36 * 5.0 ** 2 * math.sin(math.radians(10))
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(expected_area * UNITS["mm"] ** 2))


# ===========================================================================
# Criterion 8: missing $INSUNITS and no unit override
# ===========================================================================

def test_criterion8_missing_insunits_and_no_unit_override(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri_nounits.dxf", insunits=None, polylines=[(TRIANGLE, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "Drawing has no usable unit information; set 'unit' in this component's "
        "configuration, e.g. 'mm'.")


# ===========================================================================
# Criterion 9: unknown unit override
# ===========================================================================

def test_criterion9_unknown_unit_override(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri.dxf", insunits=4, polylines=[(TRIANGLE, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": "banana"})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "Unknown length unit 'banana'; use one of LiveSheet's existing length units, "
        "e.g. 'mm', 'm', 'inch'.")


# ===========================================================================
# Criterion 10: wiring P1.area -> F1.a, no special-casing needed downstream
# ===========================================================================

def test_criterion10_wired_into_formula_component(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri.dxf", insunits=4, polylines=[(TRIANGLE, "")])
    specs = [
        ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a"}),
    ]
    wires = [WireSpec("P1", "area", "F1", "a")]
    result = evaluate(specs, wires, engine)
    assert result["P1"].status == "ok"
    assert result["F1"].status == "ok"
    p1_area = measure(result["P1"].outputs["area"])
    f1_result = measure(result["F1"].outputs["result"])
    assert f1_result.dims == p1_area.dims
    assert float(f1_result.magnitude) == pytest.approx(float(p1_area.magnitude))


# ===========================================================================
# Edge cases: file-level failures
# ===========================================================================

def test_edge_case_nonexistent_path_errors(engine):
    specs = [ComponentSpec(
        "P1", "cad-profile", {"path": "/no/such/file.dxf", "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error.startswith("Could not open DXF file:")


def test_edge_case_corrupted_file_errors(tmp_path, engine):
    path = tmp_path / "garbage.dxf"
    path.write_text("this is not a DXF file at all")
    specs = [ComponentSpec(
        "P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == "Could not read DXF file: not a valid DXF file."


def test_edge_case_no_closed_profile_found(tmp_path, engine):
    path = _make_dxf(tmp_path, "empty.dxf", insunits=4)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "No closed profile found (phase 1 supports one closed straight-sided polyline "
        "entity only).")


def test_edge_case_zero_area_collinear_profile(tmp_path, engine):
    collinear = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    path = _make_dxf(tmp_path, "collinear.dxf", insunits=4, polylines=[(collinear, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == "Profile has zero area."


def test_edge_case_open_polyline_is_out_of_scope(tmp_path, engine):
    """A polyline present but not marked closed is a scope-boundary case, same error text as
    a curved/standalone-line profile -- not a "nothing here" message."""
    path = tmp_path / "open.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    doc.modelspace().add_lwpolyline(TRIANGLE, close=False)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "This profile uses curved segments or separate line segments, not yet supported by "
        "this component (phase 1 supports one closed straight-sided polyline entity only).")


def test_edge_case_bulged_segment_is_now_supported_per_spec_014(tmp_path, engine):
    """UPDATED for spec 014 (see module docstring): a closed polyline mixing straight and
    nonzero-bulge segments is spec 014's own "fully supported here (013 only handled the
    all-straight case)" edge case, directly superseding 013's own "out of this phase's scope"
    edge case that used this exact fixture. The bulge arcs outward along the (0,0)-(40,0) edge,
    so the resulting area must exceed the all-straight triangle's own 400 mm^2 -- proof the arc
    was really tessellated, not silently ignored or dropped."""
    path = tmp_path / "bulged.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_lwpolyline([(0.0, 0.0, 0.0, 0.0, 0.5), (40.0, 0.0, 0.0, 0.0, 0.0),
                         (0.0, 20.0, 0.0, 0.0, 0.0)], format="xyseb", close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    assert _area_m2(result["P1"].outputs["area"]) > _area_m2(400 * UNITS["mm"] ** 2)


def test_edge_case_clockwise_wound_triangle_matches_counter_clockwise(tmp_path, engine):
    """A clockwise-wound single loop is accepted (not rejected), and -- a defensible
    implementation choice flagged in this developer's handoff, not explicit in the spec's own
    formulas -- its section properties come out identical to the same polygon wound
    counter-clockwise, not sign-flipped and not a crash."""
    cw = list(reversed(TRIANGLE))
    path = _make_dxf(tmp_path, "tri_cw.dxf", insunits=4, polylines=[(cw, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(400 * UNITS["mm"] ** 2))
    ixx = measure(result["P1"].outputs["Ixx"])
    assert float(ixx.magnitude) > 0


def test_edge_case_z_coordinate_ignored(tmp_path, engine):
    path = tmp_path / "withz.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    doc.modelspace().add_lwpolyline(
        [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)], close=True, dxfattribs={"elevation": 5.0})
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(400 * UNITS["mm"] ** 2))


def test_edge_case_incompatible_units_mix_fails_downstream(tmp_path, engine):
    path = _make_dxf(tmp_path, "tri.dxf", insunits=4, polylines=[(TRIANGLE, "")])
    specs = [
        ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a + 1"}),
    ]
    wires = [WireSpec("P1", "area", "F1", "a")]
    result = evaluate(specs, wires, engine)
    assert result["F1"].status == "error"
    assert result["F1"].error == "Units do not match"


def test_edge_case_file_re_read_every_recalculation(tmp_path, engine):
    """No caching: changing the file on disk between two calls to ``evaluate`` with the same
    config changes the result (same convention as "Value"/"Formula" re-parsing ``expr``)."""
    path = tmp_path / "mutable.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    doc.modelspace().add_lwpolyline(TRIANGLE, close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    first = evaluate(specs, [], engine)
    assert _area_m2(first["P1"].outputs["area"]) == pytest.approx(_area_m2(400 * UNITS["mm"] ** 2))

    doc2 = ezdxf.new()
    doc2.header["$INSUNITS"] = 4
    doc2.modelspace().add_lwpolyline(SQUARE, close=True)
    doc2.saveas(str(path))
    second = evaluate(specs, [], engine)
    assert _area_m2(second["P1"].outputs["area"]) == pytest.approx(_area_m2(100 * UNITS["mm"] ** 2))


# ===========================================================================
# Spec 014 (phase 2): curved entities, LINE-chaining, composite (hole) sections -- through the
# real wiring.evaluate() path, DXF fixtures generated at test time via ezdxf's own write API.
# ===========================================================================

def test_spec014_criterion1_full_circle_tessellation(tmp_path, engine):
    path = tmp_path / "circle.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    doc.modelspace().add_circle((0, 0), radius=10)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    expected_area = 0.5 * 36 * 10.0 ** 2 * math.sin(math.radians(10))
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(expected_area * UNITS["mm"] ** 2))
    assert measure(result["P1"].outputs["centroid_x"]).magnitude == pytest.approx(0.0, abs=1e-9)
    assert measure(result["P1"].outputs["centroid_y"]).magnitude == pytest.approx(0.0, abs=1e-9)


def test_spec014_criterion2_bulge_arc_semicircle(tmp_path, engine):
    path = tmp_path / "bulge_arc.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    doc.modelspace().add_lwpolyline(
        [(-10.0, 0.0, 1.0), (10.0, 0.0, 0.0)], format="xyb", close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    expected_area = 900.0 * math.sin(math.radians(10))
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(
        _area_m2(expected_area * UNITS["mm"] ** 2))


def test_spec014_criterion3_line_chaining_rectangle(tmp_path, engine):
    path = tmp_path / "lines_rect.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_line((0, 0), (40, 0))
    msp.add_line((40, 0), (40, 20))
    msp.add_line((40, 20), (0, 20))
    msp.add_line((0, 20), (0, 0))
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(_area_m2(800 * UNITS["mm"] ** 2))
    assert measure(result["P1"].outputs["centroid_x"]).magnitude == pytest.approx(
        measure(20 * UNITS["mm"]).magnitude)
    assert measure(result["P1"].outputs["centroid_y"]).magnitude == pytest.approx(
        measure(10 * UNITS["mm"]).magnitude)
    assert _area_m2(result["P1"].outputs["Ixx"]) == pytest.approx(
        _area_m2((26666.7) * UNITS["mm"] ** 4), rel=1e-5)
    assert _area_m2(result["P1"].outputs["Iyy"]) == pytest.approx(
        _area_m2((106667.0) * UNITS["mm"] ** 4), rel=1e-5)


def test_spec014_criterion4_line_chaining_failure_gap(tmp_path, engine):
    path = tmp_path / "lines_gap.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_line((0, 0), (40, 0))
    msp.add_line((40, 0), (40, 20))
    msp.add_line((40, 20), (5, 20))  # shortened: no longer reaches (0, 20), leaves a gap
    msp.add_line((0, 20), (0, 0))
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "Could not assemble a single closed loop from LINE entities on this layer.")


def test_spec014_criterion5_composite_hole_section(tmp_path, engine):
    path = tmp_path / "hole.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]  # CCW
    hole = [(15.0, 5.0), (15.0, 15.0), (25.0, 15.0), (25.0, 5.0)]  # CW
    msp.add_lwpolyline(outer, close=True)
    msp.add_lwpolyline(hole, close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "ok", result["P1"].error
    assert _area_m2(result["P1"].outputs["area"]) == pytest.approx(_area_m2(700 * UNITS["mm"] ** 2))
    assert measure(result["P1"].outputs["centroid_x"]).magnitude == pytest.approx(
        measure(20 * UNITS["mm"]).magnitude)
    assert measure(result["P1"].outputs["centroid_y"]).magnitude == pytest.approx(
        measure(10 * UNITS["mm"]).magnitude)
    expected_ixx = 40.0 * 20.0 ** 3 / 12 - 10.0 * 10.0 ** 3 / 12
    expected_iyy = 20.0 * 40.0 ** 3 / 12 - 10.0 * 10.0 ** 3 / 12
    assert _area_m2(result["P1"].outputs["Ixx"]) == pytest.approx(
        _area_m2(expected_ixx * UNITS["mm"] ** 4), rel=1e-5)
    assert _area_m2(result["P1"].outputs["Iyy"]) == pytest.approx(
        _area_m2(expected_iyy * UNITS["mm"] ** 4), rel=1e-5)
    # outline concatenates outer first, then the hole, per spec 014's own ordering rule.
    outline = result["P1"].outputs["outline"]
    assert outline.shape == (8, 2)


def test_spec014_criterion6_winding_mismatch(tmp_path, engine):
    path = tmp_path / "winding_mismatch.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]  # CCW
    hole_ccw = [(15.0, 5.0), (25.0, 5.0), (25.0, 15.0), (15.0, 15.0)]  # also CCW -- the defect
    msp.add_lwpolyline(outer, close=True)
    msp.add_lwpolyline(hole_ccw, close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == (
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")


def test_spec014_criterion7_containment_failure(tmp_path, engine):
    path = tmp_path / "containment_failure.dxf"
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]  # CCW
    hole_outside = [(35.0, 5.0), (35.0, 15.0), (45.0, 15.0), (45.0, 5.0)]  # CW, sticks out past x=40
    msp.add_lwpolyline(outer, close=True)
    msp.add_lwpolyline(hole_outside, close=True)
    doc.saveas(str(path))
    specs = [ComponentSpec("P1", "cad-profile", {"path": str(path), "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)
    assert result["P1"].status == "error"
    assert result["P1"].error == "A hole loop extends outside the outer profile's boundary."


def test_spec014_criterion8_spec013_regression_through_wiring(tmp_path, engine):
    """Spec 014's own criterion 8: every acceptance criterion in spec 013 still passes
    unmodified -- re-run spec 013's own criterion 2 (worked-example triangle) and criterion 9
    (unknown unit override) end to end through wiring.evaluate(), confirming the single-loop
    path is exactly the len(loops) == 1 special case of this spec's more general path, not a
    separate code path that could silently diverge. (Every other test above in this module that
    is unaffected by spec 014's explicitly-disclosed behaviour changes -- see module docstring
    -- already re-runs unmodified as part of the same test suite; this is one more, explicit,
    named check of the exact regression criterion 8 calls out.)"""
    path = _make_dxf(tmp_path, "regression_tri.dxf", insunits=4, polylines=[(TRIANGLE, "")])
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    mm = UNITS["mm"]
    assert _area_m2(result.outputs["area"]) == pytest.approx(_area_m2(400 * mm ** 2))
    assert _area_m2(result.outputs["Ixx"]) == pytest.approx(_area_m2((80000 / 9) * mm ** 4))

    specs_bad_unit = [ComponentSpec(
        "P1", "cad-profile", {"path": path, "layer": "", "unit": "banana"})]
    result2 = evaluate(specs_bad_unit, [], engine)["P1"]
    assert result2.status == "error"
    assert result2.error == (
        "Unknown length unit 'banana'; use one of LiveSheet's existing length units, "
        "e.g. 'mm', 'm', 'inch'.")
