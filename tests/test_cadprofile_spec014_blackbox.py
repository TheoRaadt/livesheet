"""Independent black-box tests for spec 014 (DXF profile import, phase 2: curved entities,
LINE-chaining, composite hole sections) -- ``docs/board/specs/014-dxf-profile-geometry-
extensions.md``.

Written from spec 014's own "Behaviour" section and numbered acceptance criteria, re-deriving
every worked number from scratch (never trusting the spec's own stated decimals, the developer's
own ``tests/test_cadprofile.py``/``tests/test_cadprofile_blackbox.py``, or the implementation's
output). Those two developer-owned files were skimmed only for fixture-construction API shape
(``ComponentSpec``/``WireSpec``/``evaluate``/``ezdxf.new()`` conventions), never for assertion
ideas or expected numbers.

Particular focus, per this review's task: independently re-verifying the disclosed
``_tessellate_bulge_segment`` sign-flip fix is actually correct (not just "symmetric cases still
pass"), on several *asymmetric* shapes and edge orientations, not only the one case the developer
already checked; the LINE-chaining graph logic; the composite outer/hole winding and containment
rules; and unit handling through tessellated/composite outputs.
"""

from __future__ import annotations

import math

import ezdxf
import pytest
import sympy as sp

from livesheet.engine.cadprofile import (
    CadProfileError,
    _assemble_lines_into_loop,
    _tessellate_bulge_segment,
    _tessellate_circle,
    assemble_loops,
    read_profile,
    section_properties,
)
from livesheet.engine.evaluator import Engine
from livesheet.engine.units import UNITS, measure
from livesheet.engine.wiring import ComponentSpec, WireSpec, evaluate

TOL = 1e-6


def _approx(x):
    return pytest.approx(x, rel=TOL, abs=1e-9)


def _mag(value, unit_name, power=1):
    return float(sp.nsimplify(value / (UNITS[unit_name] ** power)))


@pytest.fixture
def engine():
    return Engine()


def _new_doc(insunits=4):
    doc = ezdxf.new()
    if insunits is not None:
        doc.header["$INSUNITS"] = insunits
    return doc


def _save(doc, tmp_path, name):
    path = str(tmp_path / name)
    doc.saveas(path)
    return path


# ===========================================================================
# Criterion 1: full circle tessellation, independently re-derived
# ===========================================================================

def test_criterion1_circle_tessellation_area_and_centroid_independently_derived():
    """36-gon inscribed in r=10: area = sum of 36 isoceles triangles from the centre, each
    with apex angle 10 degrees -> 36 * 0.5 * r^2 * sin(10deg). Derived from scratch here (not
    copied from the spec's own stated 312.567), compared against both ``_tessellate_circle``'s
    output and the full ``section_properties`` pipeline."""
    expected_area = 36 * 0.5 * 10.0 ** 2 * math.sin(math.radians(10))
    assert expected_area == pytest.approx(312.567, abs=0.001)  # sanity vs spec's own quoted value

    pts = _tessellate_circle(0.0, 0.0, 10.0)
    assert len(pts) == 36
    props = section_properties([pts])
    assert props.area == _approx(expected_area)
    assert props.centroid_x == _approx(0.0)
    assert props.centroid_y == _approx(0.0)
    # Strictly less than the continuous circle, same direction of discretisation error always.
    assert props.area < math.pi * 10.0 ** 2


def test_criterion1_through_wiring_with_insunits_mm(tmp_path, engine):
    doc = _new_doc(insunits=4)
    doc.modelspace().add_circle((0, 0), radius=10)
    path = _save(doc, tmp_path, "circle.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    expected_area = 36 * 0.5 * 10.0 ** 2 * math.sin(math.radians(10))
    assert _mag(result.outputs["area"], "mm", 2) == _approx(expected_area)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(0.0)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(0.0)


# ===========================================================================
# Criterion 2 + bulge-direction sign checks (the class of bug just fixed)
# ===========================================================================

def test_criterion2_bulge_semicircle_area_independently_derived():
    """Independent re-derivation (triangulation from the origin, not trusting the spec's own
    900*sin(10deg) number blindly): the 18 small triangles between consecutive tessellated arc
    points each have area 0.5*r^2*sin(10deg); the final chord back from (10,0) to (-10,0) passes
    exactly through the centre (diametrically opposite points), contributing zero extra area to
    an origin-triangulation decomposition. Total = 18 * 0.5 * 10^2 * sin(10deg) = 900*sin(10deg)."""
    expected_area = 18 * 0.5 * 10.0 ** 2 * math.sin(math.radians(10))
    assert expected_area == pytest.approx(156.283, abs=0.001)

    pts = _tessellate_bulge_segment((-10.0, 0.0), (10.0, 0.0), 1.0)
    assert len(pts) == 19
    assert pts[0] == pytest.approx((-10.0, 0.0))
    assert pts[-1] == pytest.approx((10.0, 0.0))
    area = section_properties([pts]).area
    assert area == _approx(expected_area)


def test_unambiguous_quarter_circle_oracle_confirms_ccw_sign_convention():
    """Clean, first-principles oracle with NO symmetry ambiguity (unlike the semicircle): a
    bulge connecting (1,0) to (0,1) with the bulge value for a true 90-degree CCW arc centred at
    the origin (b = tan(22.5deg)) must tessellate to points lying exactly on the unit circle
    through the first quadrant (midpoint (cos45, sin45)) -- this is the universally unambiguous
    definition of "counter-clockwise from (1,0) to (0,1)" (standard increasing-angle convention),
    so it independently pins down the sign convention without relying on any symmetric case that
    could mask a flip. If this fails, the bulge-to-arc sign convention itself is wrong, not just
    "some asymmetric shape looks odd"."""
    b = math.tan(math.radians(22.5))
    pts = _tessellate_bulge_segment((1.0, 0.0), (0.0, 1.0), b)
    assert pts[0] == pytest.approx((1.0, 0.0), abs=1e-9)
    assert pts[-1] == pytest.approx((0.0, 1.0), abs=1e-9)
    mid = pts[len(pts) // 2]
    assert mid == pytest.approx((math.cos(math.radians(45)), math.sin(math.radians(45))), abs=1e-9)
    # Every intermediate point must lie at radius 1 from the origin (centre must resolve to
    # the origin for this to hold -- an independent check that centre/radius derivation is
    # correct, not just the final sampled angle).
    for x, y in pts:
        assert math.hypot(x, y) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("edge", ["bottom", "right_diagonal", "left_vertical"])
@pytest.mark.parametrize("sign", [1, -1])
def test_positive_bulge_always_bulges_outward_on_a_ccw_polygon_regardless_of_edge_orientation(
        edge, sign):
    """Generalises the developer's own single-edge check (one axis-aligned edge of one
    triangle) to three *differently oriented* edges of the same CCW-wound polygon -- exactly
    the "sibling case" this review was asked to look for. For *any* edge of a CCW polygon, a
    small positive bulge must increase the enclosed area (arcs outward, away from the
    interior) and a small negative bulge must decrease it (arcs inward) -- this must hold no
    matter which of the polygon's edges carries the bulge, since the underlying geometric rule
    (interior is to the left of travel on a CCW loop; the documented CCW arc convention bulges
    to the right of travel) does not depend on the edge's orientation.
    """
    # CCW quadrilateral, deliberately scalene/non-symmetric so no edge is an accidental mirror
    # of another.
    base = [(0.0, 0.0), (30.0, 0.0), (22.0, 18.0), (4.0, 14.0)]
    assert section_properties([base]).area > 0  # sanity: genuinely a valid, nonzero polygon

    straight_area = section_properties([base]).area
    edge_index = {"bottom": 0, "right_diagonal": 1, "left_vertical": 3}[edge]
    p0 = base[edge_index]
    p1 = base[(edge_index + 1) % len(base)]
    b = 0.08 * sign

    arc_pts = _tessellate_bulge_segment(p0, p1, b)
    loop = []
    for i, v in enumerate(base):
        loop.append(v)
        if i == edge_index:
            loop.extend(arc_pts[1:-1])
    bulged_area = section_properties([loop]).area

    if sign > 0:
        assert bulged_area > straight_area, f"edge={edge}"
    else:
        assert bulged_area < straight_area, f"edge={edge}"


def test_positive_bulge_bulges_inward_on_a_clockwise_polygon_same_edge():
    """Winding-interaction sibling check: reverse the same quadrilateral's vertex order (now
    clockwise) and repeat the bottom-edge bulge. Interior is now to the *right* of travel along
    that edge (winding flipped), so the same positive bulge (still "arc to the right of travel"
    per the fixed, winding-independent convention) now bulges *into* the interior, shrinking
    the enclosed area -- the opposite sign relationship from the CCW case above. If the fix had
    accidentally made the bulge direction depend on polygon winding (rather than purely on the
    bulge's own sign, as the DXF format defines it), this would catch it."""
    base_ccw = [(0.0, 0.0), (30.0, 0.0), (22.0, 18.0), (4.0, 14.0)]
    base_cw = list(reversed(base_ccw))  # [(0,0),(4,14),(22,18),(30,0)]
    straight_area = abs(section_properties([base_cw]).area)

    # Bottom edge of the CW loop, in CW order, is (30,0) -> (0,0) (the reverse direction).
    p0, p1 = (30.0, 0.0), (0.0, 0.0)
    b = 0.08
    arc_pts = _tessellate_bulge_segment(p0, p1, b)
    idx = base_cw.index(p0)
    loop = []
    for i, v in enumerate(base_cw):
        loop.append(v)
        if i == idx:
            loop.extend(arc_pts[1:-1])
    bulged_area = abs(section_properties([loop]).area)
    assert bulged_area < straight_area


def test_semicircle_direction_note_spec_prose_describes_the_wrong_side():
    """Not a defect in the implementation -- a documentation note about spec 014's own
    acceptance-criterion-2 prose, found while independently re-deriving the sign convention.

    The spec's text says: "vertex (-10, 0)'s segment to (10, 0) is the upper semicircle
    (counter-clockwise from (-10,0) through (0,10) to (10,0))". Independently re-derived from
    three unrelated angles (all agreeing): (1) algebraically, theta=4*atan(b) with b=1 combined
    with the centre-finding formula gives centre ~ (0, +infinitesimal) and start angle 180deg,
    end angle 0deg with a *positive* (CCW, increasing-angle) 180deg sweep -- tracing through
    270deg, i.e. (0,-10), not 90deg/(0,10); (2) the standard circular-motion fact "when
    travelling CCW (increasing angle) around a circle, its centre is always 90 degrees to your
    LEFT" applied to this centre location; (3) the unambiguous quarter-circle oracle above,
    which has no symmetry to get backwards and independently confirms the same sign convention.
    All three agree the correct semicircle for a *positive* bulge on this left-to-right chord is
    the LOWER one, through (0,-10) -- matching this review's own asymmetric-edge-orientation
    checks above and the developer's own already-disclosed fix for the real (asymmetric
    triangle) bug. This does not affect acceptance criterion 2's actual pass/fail (its only
    numeric assertion is the area, which is identical for either semicircle by symmetry), so it
    is reported as a spec-wording flaw for the record (same category as spec 010's own
    previously-flagged worked-example flaw), not as an implementation defect."""
    pts = _tessellate_bulge_segment((-10.0, 0.0), (10.0, 0.0), 1.0)
    mid = pts[len(pts) // 2]
    assert mid[1] < 0, (
        "implementation produces the lower semicircle for b=1.0 on this chord -- correct per "
        "independent re-derivation; spec's own prose describes the upper one, a wording flaw")


def test_multiple_bulges_in_one_loop_each_bulges_outward():
    """Multiple bulge segments in the same closed polyline (spec's own edge case: "mixes some
    zero-bulge and some nonzero-bulge segments") -- both must independently bulge outward on a
    CCW loop, not just the first one processed."""
    base = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]  # CCW square, area 400
    straight_area = section_properties([base]).area

    def bulge_edge(loop, idx, b):
        p0, p1 = loop[idx], loop[(idx + 1) % len(loop)]
        arc = _tessellate_bulge_segment(p0, p1, b)[1:-1]
        out = []
        for i, v in enumerate(loop):
            out.append(v)
            if i == idx:
                out.extend(arc)
        return out

    arc_bottom = _tessellate_bulge_segment(base[0], base[1], 0.1)[1:-1]
    arc_top = _tessellate_bulge_segment(base[2], base[3], 0.1)[1:-1]
    loop2 = [base[0]] + arc_bottom + [base[1], base[2]] + arc_top + [base[3]]
    area2 = section_properties([loop2]).area
    assert area2 > straight_area


# ===========================================================================
# ARC entities: full-circle-equivalent accepted, genuinely partial arc is a scope boundary
# ===========================================================================

def test_full_arc_entity_same_result_as_circle_entity():
    doc = _new_doc()
    msp = doc.modelspace()
    msp.add_arc(center=(0, 0), radius=10, start_angle=0, end_angle=360)
    loops = assemble_loops(msp, "")
    assert len(loops) == 1
    props = section_properties(loops)
    expected_area = 36 * 0.5 * 10.0 ** 2 * math.sin(math.radians(10))
    assert props.area == _approx(expected_area)


def test_partial_arc_alone_is_a_scope_boundary_not_a_closed_loop(tmp_path, engine):
    doc = _new_doc(insunits=4)
    doc.modelspace().add_arc(center=(0, 0), radius=10, start_angle=0, end_angle=180)
    path = _save(doc, tmp_path, "partialarc.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "This profile uses curved segments or separate line segments, not yet "
        "supported by this component (phase 1 supports one closed straight-sided "
        "polyline entity only).")


# ===========================================================================
# Criterion 3 + LINE-chaining graph logic edge cases
# ===========================================================================

RECT_LINES = [
    ((0.0, 0.0), (40.0, 0.0)),
    ((40.0, 0.0), (40.0, 20.0)),
    ((40.0, 20.0), (0.0, 20.0)),
    ((0.0, 20.0), (0.0, 0.0)),
]


def test_criterion3_rectangle_from_chained_lines_independently_derived():
    loop = _assemble_lines_into_loop(RECT_LINES)
    props = section_properties([loop])
    assert props.area == _approx(800.0)
    assert props.centroid_x == _approx(20.0)
    assert props.centroid_y == _approx(10.0)
    assert props.Ixx == _approx(40.0 * 20.0 ** 3 / 12)
    assert props.Iyy == _approx(20.0 * 40.0 ** 3 / 12)


def test_criterion3_through_wiring_with_scrambled_and_reversed_line_order(tmp_path, engine):
    """The spec only shows the lines in forward, sequential order -- independently check the
    chaining logic is actually order/direction-independent (a real DXF file has no guaranteed
    entity order), by scrambling the 4 lines' order and reversing two of their endpoints."""
    doc = _new_doc(insunits=4)
    msp = doc.modelspace()
    scrambled = [
        ((40.0, 20.0), (0.0, 20.0)),
        ((0.0, 0.0), (0.0, 20.0)),  # reversed direction vs RECT_LINES[3]
        ((40.0, 0.0), (0.0, 0.0)),  # reversed direction vs RECT_LINES[0]
        ((40.0, 0.0), (40.0, 20.0)),
    ]
    for p0, p1 in scrambled:
        msp.add_line(p0, p1)
    path = _save(doc, tmp_path, "scrambled_rect.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(800.0)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(20.0)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(10.0)


def test_criterion4_gap_in_chain_errors(tmp_path, engine):
    doc = _new_doc(insunits=4)
    msp = doc.modelspace()
    msp.add_line((0, 0), (40, 0))
    msp.add_line((40, 0), (40, 20))
    msp.add_line((40, 20), (5, 20))  # shortened: should reach (0, 20), leaves a gap
    msp.add_line((0, 20), (0, 0))
    path = _save(doc, tmp_path, "gap_rect.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Could not assemble a single closed loop from LINE entities on this layer.")


def test_line_chaining_branch_point_degree_three_errors():
    """A "lollipop"/T-junction: a closed triangle plus an extra stray LINE attached to one of
    its corners. That corner now has degree 3, not 2 -- must error, not silently ignore the
    stray edge or crash."""
    triangle = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (0.0, 10.0)),
        ((0.0, 10.0), (0.0, 0.0)),
    ]
    stray = [((0.0, 0.0), (-5.0, -5.0))]
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop(triangle + stray)


def test_line_chaining_two_disconnected_cycles_errors():
    """Two independently-closed rectangles made of LINE entities, no shared nodes -- more than
    one connected component, must error (spec's own point 3: "multiple separate outer bodies
    ... out of scope" for this phase, and LINE-chaining only ever attempts a single candidate
    loop from the whole standalone-LINE set)."""
    rect_a = RECT_LINES
    rect_b = [
        ((100.0, 0.0), (110.0, 0.0)),
        ((110.0, 0.0), (110.0, 10.0)),
        ((110.0, 10.0), (100.0, 10.0)),
        ((100.0, 10.0), (100.0, 0.0)),
    ]
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop(rect_a + rect_b)


def test_line_chaining_open_dangling_chain_errors():
    """Three lines forming an open "U" shape (no closing edge) -- both ends have degree 1."""
    open_chain = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 10.0)),
        ((10.0, 10.0), (0.0, 10.0)),
    ]
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop(open_chain)


def test_line_chaining_tolerance_boundary():
    """Spec's own fixed 1e-6 native-unit tolerance: an endpoint gap of 5e-7 (inside tolerance)
    must still chain; a gap of 5e-5 (outside tolerance) must not."""
    close_enough = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 10.0)),
        ((10.0, 10.0), (0.0, 10.0)),
        ((0.0 + 5e-7, 10.0), (0.0, 0.0)),
    ]
    loop = _assemble_lines_into_loop(close_enough)
    assert section_properties([loop]).area == _approx(100.0)

    too_far = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.0, 0.0), (10.0, 10.0)),
        ((10.0, 10.0), (0.0, 10.0)),
        ((0.0 + 5e-5, 10.0), (0.0, 0.0)),
    ]
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop(too_far)


# ===========================================================================
# Criterion 5/6/7: composite outer+hole section
# ===========================================================================

OUTER_RECT = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]  # CCW, area 800
HOLE_SQUARE_CENTRED_CW = [(15.0, 5.0), (15.0, 15.0), (25.0, 15.0), (25.0, 5.0)]  # CW, area -100
HOLE_SQUARE_CENTRED_CCW = list(reversed(HOLE_SQUARE_CENTRED_CW))


def _composite_fixture(tmp_path, hole, insunits=4):
    doc = _new_doc(insunits=insunits)
    msp = doc.modelspace()
    msp.add_lwpolyline(OUTER_RECT, close=True)
    msp.add_lwpolyline(hole, close=True)
    return _save(doc, tmp_path, "composite.dxf")


def test_criterion5_composite_hole_section_independently_derived(tmp_path, engine):
    path = _composite_fixture(tmp_path, HOLE_SQUARE_CENTRED_CW)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error

    # Independent re-derivation: both centroids coincide (hole centred inside outer), so no
    # parallel-axis shift is needed; composite moments are plain subtraction.
    outer_area, hole_area = 800.0, 100.0
    outer_ixx, outer_iyy = 40.0 * 20.0 ** 3 / 12, 20.0 * 40.0 ** 3 / 12
    hole_ixx = hole_iyy = 10.0 * 10.0 ** 3 / 12

    assert _mag(result.outputs["area"], "mm", 2) == _approx(outer_area - hole_area)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(20.0)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(10.0)
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(outer_ixx - hole_ixx)
    assert _mag(result.outputs["Iyy"], "mm", 4) == _approx(outer_iyy - hole_iyy)

    outline = result.outputs["outline"]
    assert outline.shape == (8, 2)  # 4 outer + 4 hole vertices, concatenated outer-first
    for i, (x, y) in enumerate(OUTER_RECT):
        assert _mag(outline[i, 0], "mm") == _approx(x)
        assert _mag(outline[i, 1], "mm") == _approx(y)
    for i, (x, y) in enumerate(HOLE_SQUARE_CENTRED_CW):
        assert _mag(outline[4 + i, 0], "mm") == _approx(x)
        assert _mag(outline[4 + i, 1], "mm") == _approx(y)


def test_criterion5_composite_offcentre_hole_cross_checked_with_parallel_axis_by_hand(
        tmp_path, engine):
    """A second, independent composite worked example (not the spec's own centred hole, which
    conveniently needs no parallel-axis shift) -- a hole NOT centred on the outer rectangle, so
    the composite centroid moves and a genuine parallel-axis term is needed. Hand-derived from
    scratch with the standard composite-section method (sum of signed sub-areas / moments,
    parallel axis theorem), independent of this module's own additive-moment-sum implementation
    detail."""
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]  # area 800, centroid (20,10)
    hole_cw = [(5.0, 2.0), (5.0, 7.0), (10.0, 7.0), (10.0, 2.0)]  # 5x5 square, area 25

    A1, A2 = 800.0, 25.0
    cx1, cy1 = 20.0, 10.0
    cx2, cy2 = 7.5, 4.5
    A = A1 - A2
    cx = (A1 * cx1 - A2 * cx2) / A
    cy = (A1 * cy1 - A2 * cy2) / A

    ixx1_own = 40.0 * 20.0 ** 3 / 12
    iyy1_own = 20.0 * 40.0 ** 3 / 12
    ixx2_own = 5.0 * 5.0 ** 3 / 12
    iyy2_own = 5.0 * 5.0 ** 3 / 12

    ixx1_about_c = ixx1_own + A1 * (cy1 - cy) ** 2
    iyy1_about_c = iyy1_own + A1 * (cx1 - cx) ** 2
    ixx2_about_c = ixx2_own + A2 * (cy2 - cy) ** 2
    iyy2_about_c = iyy2_own + A2 * (cx2 - cx) ** 2
    ixx_total = ixx1_about_c - ixx2_about_c
    iyy_total = iyy1_about_c - iyy2_about_c

    doc = _new_doc(insunits=4)
    msp = doc.modelspace()
    msp.add_lwpolyline(outer, close=True)
    msp.add_lwpolyline(hole_cw, close=True)
    path = _save(doc, tmp_path, "offcentre.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine := Engine())["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(A)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(cx)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(cy)
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(ixx_total)
    assert _mag(result.outputs["Iyy"], "mm", 4) == _approx(iyy_total)


def test_criterion6_winding_mismatch_error(tmp_path, engine):
    path = _composite_fixture(tmp_path, HOLE_SQUARE_CENTRED_CCW)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")


def test_criterion6_both_loops_clockwise_also_winding_mismatch(tmp_path, engine):
    """A sibling of criterion 6 not literally in the spec text but implied by its rule ("the
    one largest loop is clockwise" is explicitly listed as a trigger): outer CW, hole CW too."""
    outer_cw = list(reversed(OUTER_RECT))
    doc = _new_doc(insunits=4)
    msp = doc.modelspace()
    msp.add_lwpolyline(outer_cw, close=True)
    msp.add_lwpolyline(HOLE_SQUARE_CENTRED_CW, close=True)
    path = _save(doc, tmp_path, "both_cw.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == (
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")


def test_criterion7_hole_extends_outside_outer_boundary(tmp_path, engine):
    hole_outside = [(35.0, 5.0), (35.0, 15.0), (45.0, 15.0), (45.0, 5.0)]  # CW, x up to 45 > 40
    path = _composite_fixture(tmp_path, hole_outside)
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "error"
    assert result.error == "A hole loop extends outside the outer profile's boundary."


def test_hole_bbox_exactly_touching_outer_boundary_is_accepted():
    """Boundary/tie case not explicitly spelled out by the spec's prose: a hole whose bounding
    box touches the outer's edge exactly (not strictly inside) -- the implementation's
    ``>=``/``<=`` comparisons accept this. Documenting this as the implementation's actual,
    reasonable reading of "entirely inside" (touching the edge is still "inside or on"), not
    filed as a defect since the spec does not state a strict-inequality requirement either way."""
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]
    hole_touching = [(30.0, 5.0), (30.0, 15.0), (40.0, 15.0), (40.0, 5.0)]  # CW, right edge x=40
    ordered = _validate([outer, hole_touching])
    props = section_properties(ordered)
    assert props.area == _approx(800.0 - 100.0)


def _validate(loops):
    from livesheet.engine.cadprofile import _validate_composite
    return _validate_composite(loops)


def test_three_loops_outer_plus_two_holes():
    outer = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)]  # area 5000
    hole1 = list(reversed([(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)]))  # area -400
    hole2 = list(reversed([(60.0, 10.0), (80.0, 10.0), (80.0, 30.0), (60.0, 30.0)]))  # area -400
    ordered = _validate([outer, hole1, hole2])
    props = section_properties(ordered)
    assert props.area == _approx(5000.0 - 400.0 - 400.0)


def test_degenerate_zero_area_hole_rejected_before_composite_math():
    outer = OUTER_RECT
    degenerate_hole = [(5.0, 5.0), (10.0, 5.0), (15.0, 5.0)]  # collinear, zero area
    with pytest.raises(CadProfileError, match="Profile has zero area."):
        _validate([outer, degenerate_hole])


def test_composite_mixes_line_chained_outer_with_polyline_hole(tmp_path, engine):
    """Spec's own explicit claim: loops from LWPOLYLINE, tessellated arcs, and LINE-chaining
    are "all treated uniformly from this point on" -- build the outer from chained LINE
    entities and the hole from an ordinary LWPOLYLINE, confirm the composite math still works."""
    doc = _new_doc(insunits=4)
    msp = doc.modelspace()
    for p0, p1 in RECT_LINES:  # outer 40x20 rectangle, from LINEs, CCW
        msp.add_line(p0, p1)
    msp.add_lwpolyline(HOLE_SQUARE_CENTRED_CW, close=True)
    path = _save(doc, tmp_path, "mixed_composite.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(800.0 - 100.0)


# ===========================================================================
# Units carried through tessellation/composite correctly (mm/m/cm)
# ===========================================================================

@pytest.mark.parametrize("insunits,unit_name", [(4, "mm"), (6, "m"), (5, "cm")])
def test_units_carried_through_circle_tessellation(tmp_path, engine, insunits, unit_name):
    doc = _new_doc(insunits=insunits)
    doc.modelspace().add_circle((0, 0), radius=10)
    path = _save(doc, tmp_path, f"circle_{unit_name}.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    expected_area = 36 * 0.5 * 10.0 ** 2 * math.sin(math.radians(10))
    m = measure(result.outputs["area"])
    assert m.dims == (("length", 2),)
    assert _mag(result.outputs["area"], unit_name, 2) == _approx(expected_area)
    # Cross-unit check: the same raw-coordinate area, reported in a *different* unit, must
    # convert by the square of the length ratio -- an independent consistency check that the
    # resolved unit is actually multiplying through area/length^2 outputs correctly, not just
    # being echoed back as a label.
    if unit_name == "mm":
        assert _mag(result.outputs["area"], "m", 2) == _approx(expected_area * 1e-6)
    if unit_name == "m":
        assert _mag(result.outputs["area"], "mm", 2) == _approx(expected_area * 1e6)


def test_units_carried_through_composite_section_cm(tmp_path, engine):
    doc = _new_doc(insunits=5)  # cm
    msp = doc.modelspace()
    msp.add_lwpolyline(OUTER_RECT, close=True)
    msp.add_lwpolyline(HOLE_SQUARE_CENTRED_CW, close=True)
    path = _save(doc, tmp_path, "composite_cm.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "cm", 2) == _approx(700.0)
    # Convert to mm^2: 1 cm^2 = 100 mm^2.
    assert _mag(result.outputs["area"], "mm", 2) == _approx(70000.0)
    assert _mag(result.outputs["Ixx"], "cm", 4) == _approx(25833.3333)


def test_units_carried_through_line_chaining_and_bulge_combo(tmp_path, engine):
    """Units through a LINE-chained loop that also has... actually LINE entities have no
    bulge; this instead checks units through a LWPOLYLINE loop combining straight + bulge
    segments (spec's own explicitly-supported mixed case), in metres."""
    doc = _new_doc(insunits=6)  # m
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0, 0, 0, 0.0), (10, 0, 0, 0, 0.0), (10, 10, 0, 0, 0.3)], format="xyseb", close=True)
    path = _save(doc, tmp_path, "mixed_units.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    m = measure(result.outputs["area"])
    assert m.dims == (("length", 2),)
    # Straight right triangle (0,0),(10,0),(10,10) has area 50; the 0.3 bulge on the
    # (10,10)->(0,0) edge must bulge outward (away from the opposite vertex (10,0)), so area
    # must exceed 50 -- another independent asymmetric-direction check, this time on a
    # different (diagonal, closing) edge and in metre units rather than millimetres.
    assert _mag(result.outputs["area"], "m", 2) > 50.0


# ===========================================================================
# Criterion 8: spec-013 regression -- single-loop path unaffected
# ===========================================================================

def test_criterion8_spec013_single_loop_worked_triangle_unaffected(tmp_path, engine):
    """013's own worked right triangle, re-derived independently again here (not reusing the
    spec-013 reviewer's own numbers verbatim, as a second independent check that spec 014's
    generalisation to ``list[list[...]]`` did not disturb the single-loop path)."""
    triangle = [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]
    doc = _new_doc(insunits=4)
    doc.modelspace().add_lwpolyline(triangle, close=True)
    path = _save(doc, tmp_path, "tri013.dxf")
    specs = [ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""})]
    result = evaluate(specs, [], engine)["P1"]
    assert result.status == "ok", result.error
    assert _mag(result.outputs["area"], "mm", 2) == _approx(400.0)
    assert _mag(result.outputs["centroid_x"], "mm") == _approx(40 / 3)
    assert _mag(result.outputs["centroid_y"], "mm") == _approx(20 / 3)
    assert _mag(result.outputs["Ixx"], "mm", 4) == _approx(80000 / 9)
    assert _mag(result.outputs["Iyy"], "mm", 4) == _approx(320000 / 9)


def test_criterion8_single_loop_via_section_properties_matches_013_formula_directly():
    """Direct pure-function regression: ``section_properties([loop])`` (spec 014's own stated
    013-compatibility wrapper) must be bit-identical to calling the single-loop path."""
    triangle = [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]
    props = section_properties([triangle])
    assert props.area == _approx(400.0)
    assert props.Ixy == _approx(-80000 / 9)
    assert props.J == _approx(400000 / 9)


# ===========================================================================
# Wiring into Formula still works with a composite/tessellated profile
# ===========================================================================

def test_composite_area_wires_into_formula_component(tmp_path, engine):
    path = _composite_fixture(tmp_path, HOLE_SQUARE_CENTRED_CW)
    specs = [
        ComponentSpec("P1", "cad-profile", {"path": path, "layer": "", "unit": ""}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a * 2"}),
    ]
    wires = [WireSpec("P1", "area", "F1", "a")]
    results = evaluate(specs, wires, engine)
    assert results["F1"].status == "ok", results["F1"].error
    assert _mag(results["F1"].outputs["result"], "mm", 2) == _approx(700.0 * 2)
