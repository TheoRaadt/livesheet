"""Developer tests for spec 013 phase 1 (`docs/board/specs/013-dxf-profile-import-core.md`) and
spec 014 phase 2 (`docs/board/specs/014-dxf-profile-geometry-extensions.md`), covering the pure,
ezdxf-free engineering/geometry math in ``livesheet/engine/cadprofile.py``: ``section_properties``
against the spec's own hand-worked right-triangle numbers (013) and a composite outer+hole
rectangle (014), plus the tessellation and LINE-chaining-graph pure functions. No DXF file, no Qt;
``tests/test_wiring_cadprofile.py`` covers the DXF-reading/wiring side separately.
"""

from __future__ import annotations

import math

import pytest

from livesheet.engine.cadprofile import (
    CadProfileError,
    _assemble_lines_into_loop,
    _tessellate_bulge_segment,
    _tessellate_circle,
    _validate_composite,
    section_properties,
)


# ===========================================================================
# Spec 013: section_properties(), single-loop case
# ===========================================================================

def test_worked_example_right_triangle():
    """Spec's own worked example: (0,0), (40,0), (0,20), CCW, cross-checked twice by hand.

    Spec 014 generalised section_properties() from one flat vertex list to a list of loops;
    013's own single-loop call becomes section_properties([one_loop]) (spec 014's own
    architecture note) -- the only change in this test, the assertions are untouched."""
    p = section_properties([[(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]])
    assert p.area == pytest.approx(400)
    assert p.centroid_x == pytest.approx(40 / 3)
    assert p.centroid_y == pytest.approx(20 / 3)
    assert p.Ixx == pytest.approx(80000 / 9)
    assert p.Iyy == pytest.approx(320000 / 9)
    assert p.Ixy == pytest.approx(-80000 / 9)
    assert p.J == pytest.approx(400000 / 9)
    assert p.rx == pytest.approx(math.sqrt(200 / 9))
    assert p.ry == pytest.approx(math.sqrt(800 / 9))
    assert p.Sx_top == pytest.approx(666.666666667, rel=1e-6)
    assert p.Sx_bottom == pytest.approx(1333.33333333, rel=1e-6)
    assert p.Sy_left == pytest.approx(2666.66666667, rel=1e-6)
    assert p.Sy_right == pytest.approx(1333.33333333, rel=1e-6)


def test_clockwise_winding_gives_same_absolute_area_and_properties():
    """Winding the same triangle clockwise flips the internal signed area but the reported
    ``area`` output stays the positive absolute value, and every centroid/moment comes out the
    same (the spec's formulas use the signed area internally precisely so this holds)."""
    ccw = section_properties([[(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]])
    cw = section_properties([[(0.0, 0.0), (0.0, 20.0), (40.0, 0.0)]])
    assert cw.area == pytest.approx(ccw.area)
    assert cw.centroid_x == pytest.approx(ccw.centroid_x)
    assert cw.centroid_y == pytest.approx(ccw.centroid_y)
    assert cw.Ixx == pytest.approx(ccw.Ixx)
    assert cw.Iyy == pytest.approx(ccw.Iyy)
    assert cw.Ixy == pytest.approx(ccw.Ixy)


def test_degenerate_collinear_points_raises_zero_area():
    with pytest.raises(CadProfileError, match="Profile has zero area."):
        section_properties([[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]])


def test_degenerate_fewer_than_three_distinct_vertices_raises_zero_area():
    with pytest.raises(CadProfileError, match="Profile has zero area."):
        section_properties([[(0.0, 0.0), (1.0, 1.0), (0.0, 0.0)]])


def test_self_intersecting_polygon_does_not_crash_rx_ry():
    """Fix for the independent review's defect (docs/board/reviews/013-dxf-profile-import-core.md,
    docs/board/decisions.md's "Decided 2026-10-30 (manager, spec 013 independent review)" entry):
    a self-intersecting (non-simple) loop is an already-documented, explicitly out-of-scope known
    limitation (see spec 013's own edge cases), but it must still degrade the way the spec
    actually describes -- "a mathematically meaningless but non-crashing numeric answer" -- not
    with an uncaught ``ValueError`` from ``math.sqrt()`` on a negative Ixx/Iyy. Minimal repro from
    the review."""
    bowtie = [(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (14.0, 0.0)]
    p = section_properties([bowtie])
    assert math.isfinite(p.area)
    assert math.isfinite(p.Ixx)
    assert math.isfinite(p.Iyy)
    assert math.isfinite(p.rx)
    assert math.isfinite(p.ry)


def test_asymmetric_profile_has_four_independently_computed_section_moduli():
    """Design decision 1 from the spec: a general (asymmetric) profile's four section moduli are
    computed independently from each of its four extreme-fibre distances, so ``Sx_top`` !=
    ``Sx_bottom`` and ``Sy_left`` != ``Sy_right`` in the common case (a scalene triangle, unlike
    the spec's own worked example where ``Sx_bottom`` and ``Sy_right`` happen to coincide)."""
    p = section_properties([[(0.0, 0.0), (50.0, 0.0), (10.0, 30.0)]])
    assert p.Sx_top != pytest.approx(p.Sx_bottom)
    assert p.Sy_left != pytest.approx(p.Sy_right)


# ===========================================================================
# Spec 014: tessellation math (ARC/CIRCLE, bulge segments)
# ===========================================================================

def test_tessellate_circle_matches_regular_36gon_formula():
    """Criterion 1's own hand-derived number: a 36-gon inscribed in radius 10 has area
    0.5*36*10**2*sin(10 deg) ~= 312.567, not the continuous circle's pi*10**2 ~= 314.159."""
    pts = _tessellate_circle(0.0, 0.0, 10.0)
    assert len(pts) == 36
    # k=0 lands at (cx+r, cy) per spec's own convention.
    assert pts[0] == pytest.approx((10.0, 0.0))
    area = section_properties([pts]).area
    assert area == pytest.approx(0.5 * 36 * 10.0 ** 2 * math.sin(math.radians(10)), rel=1e-9)
    assert area < math.pi * 10.0 ** 2  # strictly less than the continuous circle's own area


def test_tessellate_bulge_segment_semicircle_matches_hand_derived_area():
    """Criterion 2's own hand-derived number: bulge 1.0 is exactly a 180-degree arc
    (tan(45 deg) == 1); area of the resulting "closing straight edge + flattened semicircle"
    loop is 900*sin(10 deg) ~= 156.283 (see spec's own derivation)."""
    pts = _tessellate_bulge_segment((-10.0, 0.0), (10.0, 0.0), 1.0)
    assert len(pts) == 19  # segment_count=18 for a 180-degree arc at 10 deg/segment, +1 point
    assert pts[0] == pytest.approx((-10.0, 0.0))
    assert pts[-1] == pytest.approx((10.0, 0.0))
    # pts already is [v0, ...intermediate arc points..., v1]; wrapping the last point (v1) back
    # to the first (v0) -- section_properties()'s own implicit wrap -- is exactly the polyline's
    # own straight closing edge, so the full list (not pts[:-1]) is the right closed loop here.
    area = section_properties([pts]).area
    assert area == pytest.approx(900.0 * math.sin(math.radians(10)), rel=1e-9)


def test_tessellate_bulge_segment_clockwise_direction():
    """A negative bulge tessellates a clockwise arc -- same radius/centre magnitude as the
    equivalent positive bulge, opposite-signed intermediate-point curvature direction.

    UPDATED (dev note, see docs/board/log.md): a positive bulge is the documented
    group-code-42 "counter-clockwise arc from p0 to p1" (literally, around the arc's own
    centre) -- for this left-to-right chord that places the arc's own midpoint *below* the
    chord (the centre itself sits above/left; the swept minor arc lies on the far side from
    its centre), not above as an earlier, buggy sign convention produced. CCW (b>0) bulges
    down (-y); CW (b<0) bulges up (+y); same endpoints either way.
    """
    ccw = _tessellate_bulge_segment((-10.0, 0.0), (10.0, 0.0), 1.0)
    cw = _tessellate_bulge_segment((-10.0, 0.0), (10.0, 0.0), -1.0)
    assert ccw[len(ccw) // 2][1] < 0
    assert cw[len(cw) // 2][1] > 0
    assert ccw[0] == pytest.approx(cw[0])
    assert ccw[-1] == pytest.approx(cw[-1])


# ===========================================================================
# Spec 014: LINE-chaining graph logic
# ===========================================================================

_RECT_LINES = [
    ((0.0, 0.0), (40.0, 0.0)),
    ((40.0, 0.0), (40.0, 20.0)),
    ((40.0, 20.0), (0.0, 20.0)),
    ((0.0, 20.0), (0.0, 0.0)),
]


def test_assemble_lines_into_loop_valid_rectangle():
    loop = _assemble_lines_into_loop(_RECT_LINES)
    assert len(loop) == 4
    props = section_properties([loop])
    assert props.area == pytest.approx(800.0)
    assert props.centroid_x == pytest.approx(20.0)
    assert props.centroid_y == pytest.approx(10.0)
    assert props.Ixx == pytest.approx(40.0 * 20.0 ** 3 / 12)
    assert props.Iyy == pytest.approx(20.0 * 40.0 ** 3 / 12)


def test_assemble_lines_into_loop_broken_chain_raises():
    """The same rectangle but with the third edge shortened so it no longer reaches (0, 20),
    leaving a gap -- not a single closed loop (two dangling degree-1 nodes)."""
    broken = list(_RECT_LINES)
    broken[2] = ((40.0, 20.0), (5.0, 20.0))
    with pytest.raises(
            CadProfileError,
            match="Could not assemble a single closed loop from LINE entities on this layer."):
        _assemble_lines_into_loop(broken)


def test_assemble_lines_into_loop_single_line_raises():
    """A single standalone LINE has two degree-1 nodes -- can never be a closed loop by itself."""
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop([((0.0, 0.0), (10.0, 10.0))])


def test_assemble_lines_into_loop_two_disjoint_loops_raises():
    """Two separate, individually-valid closed triangles among the LINE entities: every node is
    still degree 2, but there are two connected components, not one -- must still fail, not
    silently pick one of the two."""
    triangle_a = [((0.0, 0.0), (10.0, 0.0)), ((10.0, 0.0), (0.0, 10.0)), ((0.0, 10.0), (0.0, 0.0))]
    triangle_b = [((100.0, 0.0), (110.0, 0.0)), ((110.0, 0.0), (100.0, 10.0)),
                  ((100.0, 10.0), (100.0, 0.0))]
    with pytest.raises(CadProfileError, match="Could not assemble a single closed loop"):
        _assemble_lines_into_loop(triangle_a + triangle_b)


# ===========================================================================
# Spec 014: composite outer/hole validation logic
# ===========================================================================

_OUTER_CCW = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]
_HOLE_CW = [(15.0, 5.0), (15.0, 15.0), (25.0, 15.0), (25.0, 5.0)]


def test_validate_composite_valid_outer_and_hole_reorders_outer_first():
    ordered = _validate_composite([_HOLE_CW, _OUTER_CCW])  # hole given first, on purpose
    assert ordered == [_OUTER_CCW, _HOLE_CW]


def test_validate_composite_hole_wound_same_as_outer_raises_winding_mismatch():
    hole_ccw = list(reversed(_HOLE_CW))
    with pytest.raises(CadProfileError, match="Loop winding does not match"):
        _validate_composite([_OUTER_CCW, hole_ccw])


def test_validate_composite_outer_wound_clockwise_raises_winding_mismatch():
    outer_cw = list(reversed(_OUTER_CCW))
    with pytest.raises(CadProfileError, match="Loop winding does not match"):
        _validate_composite([outer_cw, _HOLE_CW])


def test_validate_composite_hole_outside_outer_bbox_raises_containment_error():
    hole_outside = [(35.0, 5.0), (35.0, 15.0), (45.0, 15.0), (45.0, 5.0)]
    with pytest.raises(CadProfileError, match="extends outside the outer profile's boundary"):
        _validate_composite([_OUTER_CCW, hole_outside])


def test_validate_composite_degenerate_hole_raises_zero_area_before_other_checks():
    collinear_hole = [(15.0, 10.0), (20.0, 10.0), (25.0, 10.0)]
    with pytest.raises(CadProfileError, match="Profile has zero area."):
        _validate_composite([_OUTER_CCW, collinear_hole])


def test_composite_section_properties_matches_hand_derived_outer_minus_hole():
    """Criterion 5's own hand-derived numbers: a 40x20 outer rectangle minus a centred 10x10
    hole square (sharing the same centroid by symmetry)."""
    p = section_properties([_OUTER_CCW, _HOLE_CW])
    assert p.area == pytest.approx(700.0)
    assert p.centroid_x == pytest.approx(20.0)
    assert p.centroid_y == pytest.approx(10.0)
    assert p.Ixx == pytest.approx(40.0 * 20.0 ** 3 / 12 - 10.0 * 10.0 ** 3 / 12, rel=1e-6)
    assert p.Iyy == pytest.approx(20.0 * 40.0 ** 3 / 12 - 10.0 * 10.0 ** 3 / 12, rel=1e-6)
