"""Additional independent black-box tests for spec 014
(``docs/board/specs/014-dxf-profile-geometry-extensions.md``), written during a second,
independent review pass (see ``docs/board/reviews/014-dxf-profile-geometry-extensions.md``).

``tests/test_cadprofile_spec014_blackbox.py`` (39 cases, from an earlier, interrupted tester
session) already independently re-derives the bulge-direction sign convention, LINE-chaining,
and composite rules from the spec text. This file adds a second, differently-derived oracle for
the bulge formula (radius via ``sin(theta/2)`` and a signed-sagitta/normal construction, rather
than the existing file's ``tan(theta/2)``-division construction -- a genuinely different
algebraic route to the same DXF-documented bulge definition, cross-checked here against
``_tessellate_bulge_segment`` bit-for-bit), plus two LINE-chaining degenerate-geometry edge
cases not present in either existing test file, confirming graceful (non-crashing, still an
error -- just not the LINE-chaining-specific message) handling rather than silently wrong output.
Not from the implementation or either existing test file's own expected numbers.
"""

from __future__ import annotations

import math

import pytest

from livesheet.engine.cadprofile import (
    CadProfileError,
    _assemble_lines_into_loop,
    _tessellate_bulge_segment,
    section_properties,
)

TOL = 1e-9


def _approx(x):
    return pytest.approx(x, rel=TOL, abs=1e-9)


def _oracle_bulge_tessellate(p0, p1, b, step_deg=10.0):
    """A second, independently-derived route to the same DXF-documented bulge definition
    (``bulge = tan(included_angle / 4)``, signed: + = CCW traversal p0->p1 around the arc's
    own centre), deliberately using different algebra from ``_tessellate_bulge_segment``'s own
    ``tan(theta/2)``-division construction: here the radius comes from the standard chord/
    half-angle relationship ``r = d / (2*sin(theta/2))``, and the centre is placed via an
    explicit signed offset along the chord's own unit normal (the "centre is 90 degrees to the
    left of the direction of travel for genuinely counter-clockwise motion" rule, re-derived by
    hand, independently, in the review that added this file -- not read from this module's own
    docstring derivation)."""
    x0, y0 = p0
    x1, y1 = p1
    theta = 4.0 * math.atan(b)
    d = math.hypot(x1 - x0, y1 - y0)
    r = abs(d / (2.0 * math.sin(theta / 2.0)))
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    nx, ny = -uy, ux  # chord direction rotated +90 degrees (CCW)
    sagitta_to_centre = r * math.cos(theta / 2.0)
    sign = 1.0 if theta > 0 else -1.0
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    cx = mx + sign * sagitta_to_centre * nx
    cy = my + sign * sagitta_to_centre * ny
    start = math.degrees(math.atan2(y0 - cy, x0 - cx))
    n_seg = max(1, math.ceil(abs(math.degrees(theta)) / step_deg))
    step = math.degrees(theta) / n_seg
    return [
        (cx + r * math.cos(math.radians(start + k * step)),
         cy + r * math.sin(math.radians(start + k * step)))
        for k in range(n_seg + 1)
    ]


@pytest.mark.parametrize("p0,p1,b", [
    ((1.0, 0.0), (0.0, 1.0), math.tan(math.radians(22.5))),   # unambiguous quarter circle, CCW
    ((0.0, 1.0), (1.0, 0.0), math.tan(math.radians(22.5))),   # same arc, chord reversed
    ((0.0, 0.0), (40.0, 0.0), 0.5),                            # asymmetric triangle edge, CCW
    ((0.0, 0.0), (40.0, 0.0), -0.5),                           # same edge, opposite (CW) bulge
    ((3.0, -2.0), (-5.0, 7.0), 0.37),                          # generic oblique edge, no symmetry
    ((3.0, -2.0), (-5.0, 7.0), -0.37),
])
def test_second_independent_oracle_matches_implementation_bitwise(p0, p1, b):
    """A second, differently-derived formula for the same documented bulge definition must
    produce the same tessellated points as the implementation, for several asymmetric
    (p0, p1, b) triples -- not just the symmetric semicircle case, which cannot by itself
    distinguish a correct sign convention from a flipped one."""
    oracle = _oracle_bulge_tessellate(p0, p1, b)
    code = _tessellate_bulge_segment(p0, p1, b)
    assert len(oracle) == len(code)
    for (ox, oy), (cx, cy) in zip(oracle, code):
        assert ox == _approx(cx)
        assert oy == _approx(cy)


def test_asymmetric_triangle_bulge_outward_area_exceeds_straight_value():
    """The 013 worked-example triangle (0,0),(40,0),(0,20), area 400, with a 0.5 bulge on its
    (0,0)-(40,0) edge, bulging outward (away from the opposite vertex (0,20)), must give an
    area strictly greater than 400 -- fed through the oracle construction above (a formula
    independent of ``_tessellate_bulge_segment``'s own code path, cross-checked bitwise against
    it in the parametrized test above) into the same ``section_properties`` pipeline, on the
    exact asymmetric shape the disclosed sign-flip bug actually affected."""
    triangle = [(0.0, 0.0), (40.0, 0.0), (0.0, 20.0)]
    straight_area = section_properties([triangle]).area
    arc = _oracle_bulge_tessellate((0.0, 0.0), (40.0, 0.0), 0.5)
    loop = [triangle[0]] + arc[1:-1] + [triangle[1], triangle[2]]
    bulged_area = section_properties([loop]).area
    assert bulged_area > straight_area
    assert bulged_area == _approx(676.817683)  # independent oracle's own computed value


# ===========================================================================
# LINE-chaining: degenerate geometry not covered by either existing test file
# ===========================================================================

def test_single_zero_length_line_does_not_crash_and_is_rejected_cleanly():
    """A degenerate (zero-length) standalone LINE: both its "nodes" collapse to one point
    within the chaining tolerance, so the graph has 1 node with degree 2 (the same edge seen
    from both ends) -- passes the chaining walk mechanically, producing a 1-vertex "loop",
    which the downstream zero-area check must then reject. Documents that this reaches a
    clean, non-crashing error (via the zero-area message, not the LINE-chaining message) for
    a real degenerate input, not silently producing a bogus nonzero profile."""
    loop = _assemble_lines_into_loop([((5.0, 5.0), (5.0, 5.0))])
    assert len(loop) == 1
    with pytest.raises(CadProfileError, match="zero area"):
        section_properties([loop])


def test_duplicate_parallel_line_pair_does_not_crash_and_is_rejected_cleanly():
    """Two standalone LINE entities with identical endpoints (a duplicated/traced-over edge):
    each node ends up with degree 2 (one incidence per duplicate edge), so the chaining walk
    mechanically accepts it as a "loop" of the 2 distinct endpoints -- which the downstream
    zero-area/fewer-than-3-distinct-vertices check must then reject. Same category as the
    zero-length-LINE case above: a real degenerate input must not crash or silently produce a
    bogus nonzero profile."""
    loop = _assemble_lines_into_loop([((0.0, 0.0), (1.0, 1.0)), ((0.0, 0.0), (1.0, 1.0))])
    assert len(loop) == 2
    with pytest.raises(CadProfileError, match="zero area"):
        section_properties([loop])
