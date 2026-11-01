"""DXF profile import, phases 1+2 (specs 013/014): reading one or more closed loops out of a
``.dxf`` drawing and computing their combined 2D section properties.

GUI-independent, like the rest of ``livesheet/engine``. Depends on ``ezdxf`` (MIT) for the
file-format reading only; ``section_properties`` is a pure function over plain floats with no
``ezdxf``, no SymPy, and no ``Engine`` dependency at all, so the engineering-property math is
independently unit-testable against hand-worked numbers without needing a DXF file at all.

Spec 013 (phase 1) supported exactly one closed, straight-sided ``LWPOLYLINE``/``POLYLINE``
loop. Spec 014 (phase 2) generalises the candidate-finding step -- ``assemble_loops`` -- to also
tessellate standalone ``ARC``/``CIRCLE`` entities and ``LWPOLYLINE``/``POLYLINE`` bulge (arc)
segments, chain separate ``LINE`` entities into one closed loop, and recognise more than one
closed loop as a single composite (outer + holes) section. ``section_properties`` is
correspondingly generalised from one vertex list to a list of loops; a single loop is exactly
013's own math (unchanged), and more than one loop sums each per-loop, origin-referenced moment
term (spec 014's own "composite section = sum of signed sub-areas" idea) before the
centroid-divide/parallel-axis steps that already existed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import ezdxf

__all__ = [
    "INSUNITS_TO_UNIT", "CadProfileError", "SectionProperties",
    "read_profile", "section_properties", "assemble_loops",
]

# ``$INSUNITS`` header variable -> this engine's own existing length-unit name. Codes not listed
# here (0, 8, 9, missing, or anything else) have no mapping -- see ``_resolve_unit``.
INSUNITS_TO_UNIT: dict[int, str] = {
    1: "inch", 2: "ft", 3: "mi", 4: "mm", 5: "cm", 6: "m", 7: "km", 10: "yd",
}

# The subset of engine/units.py's UNITS table this component accepts for its own `unit`
# configuration field -- linear length units only (matches the spec's own explicit list).
_LENGTH_UNITS = ("m", "km", "cm", "mm", "um", "nm", "inch", "ft", "yd", "mi")

_LOOP_KINDS = ("LWPOLYLINE", "POLYLINE")

# Spec 014's own fixed, deterministic tessellation step -- not a library default, not exposed as
# user configuration in this phase (see spec 014's Open questions).
_TESSELLATION_STEP_DEG = 10.0

# Spec 014's own fixed LINE-chaining coordinate-matching tolerance, in the file's own native
# drawing units -- not exposed as configuration in this phase (see spec 014's Open questions).
_LINE_CHAIN_TOLERANCE = 1e-6


class CadProfileError(ValueError):
    """Raised for every DXF-import/profile-finding failure mode this component recognises."""


@dataclass
class SectionProperties:
    """Every engineering output this component computes, as plain floats in the profile's own
    raw (unit-less) coordinate system -- the caller attaches the resolved unit."""

    area: float
    centroid_x: float
    centroid_y: float
    Ixx: float
    Iyy: float
    Ixy: float
    J: float
    rx: float
    ry: float
    Sx_top: float
    Sx_bottom: float
    Sy_left: float
    Sy_right: float


def _signed_area(verts: list[tuple[float, float]]) -> float:
    """Shoelace signed area (public-domain statics); positive for a counter-clockwise loop."""
    n = len(verts)
    total = 0.0
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[(i + 1) % n]
        total += xi * yj - xj * yi
    return 0.5 * total


def section_properties(loops: list[list[tuple[float, float]]]) -> SectionProperties:
    """Shoelace-formula-family section properties (public-domain statics) of either a single
    simple polygon or -- spec 014's own generalisation -- a composite outer+holes section.

    ``loops`` is a list of vertex-list loops, each given in file order (indices wrap, vertex
    ``n`` is vertex ``0``). A single loop (``len(loops) == 1``) behaves exactly as spec 013
    already specified: either winding is accepted, normalised internally (reversed up front if
    its raw signed area is negative) so the centroid/moment formulas below -- which assume a
    counter-clockwise loop -- stay correct; this is the only error this function itself raises
    for the single-loop case (``CadProfileError("Profile has zero area.")`` for fewer than 3
    distinct vertices or an exactly-zero signed area).

    More than one loop is spec 014's composite case: every per-loop, origin-referenced moment
    term (area, the unnormalised centroid-numerator sums, and the "about origin" Ixx/Iyy/Ixy
    sums) is simply summed across loops -- using each loop's own natural, already-validated
    winding (outer positive, each hole negative) -- before the same centroid-divide/
    parallel-axis steps run once, at the end, on the totals. ``assemble_loops`` has already
    validated and ordered these loops (outer first) by the time they reach this function, so no
    further winding normalisation happens here for the multi-loop case; this additive approach
    is what makes a composite section's Ixx/Iyy/Ixy come out identical to computing each shape's
    own moment about its own centroid and combining via the parallel-axis theorem by hand (spec
    014's own "composite section = sum of signed sub-areas" idea, applied to every output, not
    just area).
    """
    if len(loops) == 1:
        loop = loops[0]
        if len(set(loop)) < 3:
            raise CadProfileError("Profile has zero area.")
        if _signed_area(loop) == 0:
            raise CadProfileError("Profile has zero area.")
        if _signed_area(loop) < 0:
            loop = list(reversed(loop))
        working_loops = [loop]
    else:
        working_loops = loops

    area_signed_total = 0.0
    cx_sum = cy_sum = ixx_o_sum = iyy_o_sum = ixy_o_sum = 0.0
    xs: list[float] = []
    ys: list[float] = []

    for loop in working_loops:
        n = len(loop)
        area_signed_total += _signed_area(loop)

        c = []
        for i in range(n):
            xi, yi = loop[i]
            xj, yj = loop[(i + 1) % n]
            c.append(xi * yj - xj * yi)

        for i in range(n):
            xi, yi = loop[i]
            xj, yj = loop[(i + 1) % n]
            ci = c[i]
            cx_sum += (xi + xj) * ci
            cy_sum += (yi + yj) * ci
            ixx_o_sum += (yi ** 2 + yi * yj + yj ** 2) * ci
            iyy_o_sum += (xi ** 2 + xi * xj + xj ** 2) * ci
            ixy_o_sum += (2 * xi * yi + xi * yj + xj * yi + 2 * xj * yj) * ci

        xs.extend(v[0] for v in loop)
        ys.extend(v[1] for v in loop)

    cx = cx_sum / (6 * area_signed_total)
    cy = cy_sum / (6 * area_signed_total)
    ixx_o = ixx_o_sum / 12
    iyy_o = iyy_o_sum / 12
    ixy_o = ixy_o_sum / 24

    ixx = ixx_o - area_signed_total * cy ** 2
    iyy = iyy_o - area_signed_total * cx ** 2
    ixy = ixy_o - area_signed_total * cx * cy
    j = ixx + iyy

    area_abs = abs(area_signed_total)
    # A self-intersecting (non-simple) input polygon is an explicitly out-of-scope known
    # limitation (see spec 013's own edge cases) that this phase does not detect; it can make
    # Ixx/Iyy above come out negative (a real, if meaningless, consequence of applying the
    # simple-polygon formulas above to a non-simple loop). Per the spec's own stated intent --
    # "a mathematically meaningless but non-crashing numeric answer" -- abs() here keeps rx/ry
    # finite instead of raising from sqrt() on a negative operand, without attempting any real
    # self-intersection detection (out of scope for this phase and for phase 2, see spec 014).
    rx = math.sqrt(abs(ixx / area_abs))
    ry = math.sqrt(abs(iyy / area_abs))

    c_top = max(ys) - cy
    c_bottom = cy - min(ys)
    c_left = cx - min(xs)
    c_right = max(xs) - cx

    return SectionProperties(
        area=area_abs, centroid_x=cx, centroid_y=cy,
        Ixx=ixx, Iyy=iyy, Ixy=ixy, J=j, rx=rx, ry=ry,
        Sx_top=ixx / c_top, Sx_bottom=ixx / c_bottom,
        Sy_left=iyy / c_left, Sy_right=iyy / c_right,
    )


# -- spec 014: tessellating ARC/CIRCLE entities and LWPOLYLINE/POLYLINE bulge segments ----------

def _tessellate_arc_points(cx: float, cy: float, r: float, start_deg: float,
                            included_deg: float) -> list[tuple[float, float]]:
    """Spec 014's own fixed, deterministic tessellation rule (10 degrees per segment, not a
    library default): samples ``segment_count + 1`` points landing exactly on both the true
    start and end points, so a flattened arc's chain always connects cleanly to whatever
    straight geometry meets it, with no gap or overlap. ``included_deg`` may be negative (a
    clockwise-wound arc, e.g. from a negative ``LWPOLYLINE`` bulge); its magnitude drives the
    segment count, its sign drives the sampling direction."""
    segment_count = max(1, math.ceil(abs(included_deg) / _TESSELLATION_STEP_DEG))
    step = included_deg / segment_count
    points = []
    for k in range(segment_count + 1):
        angle = math.radians(start_deg + k * step)
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def _tessellate_circle(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """A full ``CIRCLE`` tessellates to a 36-gon (``ceil(360/10)`` segments), ``k = 0`` at
    ``(cx + r, cy)``, counter-clockwise -- a closed loop of 36 points on its own, no separate
    "closing" point (the same "N points for an N-gon, wrap implicitly" convention a
    ``LWPOLYLINE`` vertex list already uses)."""
    return _tessellate_arc_points(cx, cy, r, 0.0, 360.0)[:-1]


def _closed_loop_from_full_arc(entity) -> list[tuple[float, float]] | None:
    """A standalone ``ARC`` entity tessellates to a *closed* loop only when its own included
    angle is effectively a full circle (``start_angle == end_angle``, per the DXF convention
    that an ``ARC`` always runs counter-clockwise from start to end); ``None`` otherwise -- a
    genuinely open arc cannot, by itself, form a closed candidate loop in this phase."""
    cx = float(entity.dxf.center.x)
    cy = float(entity.dxf.center.y)
    r = float(entity.dxf.radius)
    start = float(entity.dxf.start_angle)
    end = float(entity.dxf.end_angle)
    included = (end - start) % 360.0
    if included == 0.0:
        included = 360.0
    if included < 360.0:
        return None
    return _tessellate_arc_points(cx, cy, r, start, 360.0)[:-1]


def _tessellate_bulge_segment(p0: tuple[float, float], p1: tuple[float, float],
                               b: float) -> list[tuple[float, float]]:
    """DXF's own published, documented ``bulge`` meaning (group code 42): a signed value with
    ``bulge = tan(included_angle / 4)`` for the arc that replaces an otherwise-straight segment
    from ``p0`` to ``p1`` (positive = counter-clockwise, negative = clockwise). Centre and
    radius are derived from ``p0``/``p1``/the included angle by the standard chord/sagitta
    relationship (own first-principles derivation from the defining property that the arc's
    centre is equidistant from both endpoints and lies on their perpendicular bisector -- not
    vendor code): with the (unnormalised) chord vector ``v = p1 - p0`` and the signed included
    angle ``theta = 4*atan(b)`` (this ``theta`` is the literal signed sweep from ``p0`` to
    ``p1`` around the arc's own centre -- positive/counter-clockwise for ``b > 0``, negative/
    clockwise for ``b < 0``, exactly the documented group-code-42 meaning cited above, with no
    extra sign flip), the centre is ``midpoint(p0, p1) + rotate_90_ccw(v) / (2*tan(theta/2))``
    and the radius is ``|p1 - p0| * (1 + b**2) / (4 * |b|)``. Dividing by ``tan(theta/2)``
    (an odd function of ``theta``) is what places the centre on the correct side of the chord
    for each sign of ``b`` without any separate case split: for ``b > 0`` the centre sits to
    the left of the ``p0`` -> ``p1`` direction and the arc itself bulges to the right of that
    direction (the geometric midpoint of a counter-clockwise arc lies on the far side from its
    own centre); for ``b < 0`` both flip. (Verified against the spec's own worked semicircle
    example -- bulge 1.0 between ``(-10, 0)`` and ``(10, 0)`` -- which keeps the same *area*
    either way since the area magnitude is symmetric top/bottom; this derivation's own chosen
    side is additionally cross-checked against the "must bulge outward, away from the
    interior" requirement of a bulged triangle edge documented in this module's own tests.)
    Returns ``segment_count + 1`` points from ``p0`` to ``p1`` inclusive, tessellated the same
    way a standalone ``ARC`` is."""
    x0, y0 = p0
    x1, y1 = p1
    theta = 4.0 * math.atan(b)
    vx, vy = x1 - x0, y1 - y0
    d = math.hypot(vx, vy)
    r = d * (1.0 + b * b) / (4.0 * abs(b))
    t = math.tan(theta / 2.0)
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    cx = mx + (-vy) / (2.0 * t)
    cy = my + vx / (2.0 * t)
    start_deg = math.degrees(math.atan2(y0 - cy, x0 - cx))
    return _tessellate_arc_points(cx, cy, r, start_deg, math.degrees(theta))


def _closed_tessellated_vertices(entity) -> list[tuple[float, float]] | None:
    """Vertex list (file order, Z ignored) for a closed ``LWPOLYLINE``/2D ``POLYLINE`` loop --
    straight-only (spec 013) or mixing straight and bulge (arc) segments (spec 014's own
    addition, tessellated per the fixed 10-degree rule above, contributing each bulge segment's
    intermediate points between the existing endpoints already in the list, no duplicate
    endpoints); ``None`` for anything else, including an open polyline (still out of this
    component's scope -- spec 014 does not add open-polyline support)."""
    kind = entity.dxftype()
    if kind == "LWPOLYLINE":
        if not entity.closed:
            return None
        raw = [(float(x), float(y), float(b)) for x, y, b in entity.get_points("xyb")]
    elif kind == "POLYLINE" and getattr(entity, "is_2d_polyline", False):
        if not entity.is_closed:
            return None
        raw = [(float(v.dxf.location.x), float(v.dxf.location.y), float(v.dxf.bulge or 0.0))
               for v in entity.vertices]
    else:
        return None

    n = len(raw)
    if n < 2:
        return None

    points: list[tuple[float, float]] = []
    for i in range(n):
        x0, y0, b = raw[i]
        x1, y1, _ = raw[(i + 1) % n]
        points.append((x0, y0))
        if b != 0:
            points.extend(_tessellate_bulge_segment((x0, y0), (x1, y1), b)[1:-1])
    return points


# -- spec 014: assembling a loop from separate LINE entities -------------------------------------

def _assemble_lines_into_loop(
        lines: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[tuple[float, float]]:
    """Every standalone ``LINE`` entity's two endpoints are nodes in an undirected graph (one
    edge per ``LINE``), two endpoints considered "the same node" within
    ``_LINE_CHAIN_TOLERANCE``. Assembles into exactly one closed loop when there is exactly one
    connected component and every node has degree exactly 2 -- a connected, everywhere-degree-2
    graph is necessarily a single simple cycle (standard graph-theory fact: with ``V`` nodes and
    ``E`` edges, ``2E = sum(degrees) = 2V`` so ``E == V``, and a connected graph with as many
    edges as nodes has exactly one cycle, using every node); otherwise raises
    ``CadProfileError`` -- not a crash, not a best-effort guess."""
    nodes: list[tuple[float, float]] = []

    def node_index(p: tuple[float, float]) -> int:
        for i, existing in enumerate(nodes):
            if math.hypot(existing[0] - p[0], existing[1] - p[1]) <= _LINE_CHAIN_TOLERANCE:
                return i
        nodes.append(p)
        return len(nodes) - 1

    edges: list[tuple[int, int]] = []
    incident: dict[int, list[int]] = {}
    for p0, p1 in lines:
        i, j = node_index(p0), node_index(p1)
        edge_idx = len(edges)
        edges.append((i, j))
        incident.setdefault(i, []).append(edge_idx)
        incident.setdefault(j, []).append(edge_idx)

    error = CadProfileError(
        "Could not assemble a single closed loop from LINE entities on this layer.")

    n = len(nodes)
    if n == 0 or any(len(incident.get(k, [])) != 2 for k in range(n)):
        raise error

    used_edges: set[int] = set()
    order_idx = [0]
    current = 0
    prev_edge = -1
    for _ in range(n):
        next_edge = None
        for e in incident[current]:
            if e == prev_edge or e in used_edges:
                continue
            next_edge = e
            break
        if next_edge is None:
            raise error
        used_edges.add(next_edge)
        a, b = edges[next_edge]
        current = b if a == current else a
        prev_edge = next_edge
        order_idx.append(current)

    if current != 0 or len(used_edges) != n or len(set(order_idx[:-1])) != n:
        raise error

    return [nodes[i] for i in order_idx[:-1]]


# -- spec 014: composite (outer + holes) section validation --------------------------------------

def _bbox(loop: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in loop]
    ys = [p[1] for p in loop]
    return min(xs), max(xs), min(ys), max(ys)


def _bbox_contained(inner: tuple[float, float, float, float],
                     outer: tuple[float, float, float, float]) -> bool:
    ix0, ix1, iy0, iy1 = inner
    ox0, ox1, oy0, oy1 = outer
    return ix0 >= ox0 and ix1 <= ox1 and iy0 >= oy0 and iy1 <= oy1


def _validate_composite(
        loops: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Spec 014's outer+holes composite rule: the loop with the largest ``abs(signed_area)`` is
    the candidate outer loop and must be wound counter-clockwise; every other loop is a
    candidate hole and must be wound clockwise and bounding-box-contained inside the outer
    loop's own bounding box (a cheap containment check, not full point-in-polygon -- spec 014's
    own deliberately conservative middle ground). Raises one of the two new, more exact
    diagnoses on any violation -- superseding spec 013's own generic "multiple profiles found"
    message for every 2+-candidate case, per the spec's own explicit framing ("a more exact
    diagnosis is now available"). A hole loop that is itself degenerate (zero area) is rejected
    with 013's own zero-area message before any of the above runs, so one bad hole cannot
    silently distort the composite sum. Returns the loops reordered outer-first, then each hole
    in the order it was found."""
    areas: list[float] = []
    for loop in loops:
        if len(set(loop)) < 3 or _signed_area(loop) == 0:
            raise CadProfileError("Profile has zero area.")
        areas.append(_signed_area(loop))

    outer_idx = max(range(len(loops)), key=lambda i: abs(areas[i]))
    winding_error = CadProfileError(
        "Loop winding does not match the outer/hole convention (outer counter-clockwise, "
        "inner clockwise); check this profile's winding direction.")
    if areas[outer_idx] <= 0:
        raise winding_error
    if any(areas[i] >= 0 for i in range(len(loops)) if i != outer_idx):
        raise winding_error

    outer_bbox = _bbox(loops[outer_idx])
    ordered = [loops[outer_idx]]
    for i, loop in enumerate(loops):
        if i == outer_idx:
            continue
        if not _bbox_contained(_bbox(loop), outer_bbox):
            raise CadProfileError("A hole loop extends outside the outer profile's boundary.")
        ordered.append(loop)
    return ordered


# -- candidate-loop assembly (spec 013's single-candidate search, generalised by spec 014) -------

def _entity_layer(entity) -> str:
    return str(entity.dxf.layer)


def assemble_loops(entities, layer: str) -> list[list[tuple[float, float]]]:
    """Finds every candidate closed loop in ``entities`` (after the ``layer`` filter, blank =
    every layer): closed straight/bulge ``LWPOLYLINE``/``POLYLINE`` loops, tessellated
    standalone ``CIRCLE``/full-circle ``ARC`` loops, and a loop chained from separate ``LINE``
    entities (spec 014's additions to spec 013's original single-candidate search) -- then
    applies the outer+holes composite validation above when more than one candidate is found.
    Raises ``CadProfileError`` for every failure mode this phase recognises (no usable
    candidate at all, a ``LINE`` set that doesn't chain into one closed loop, or a composite
    validation failure); returns a non-empty list of loops on success (exactly one for a plain
    single-loop profile, more for a composite, outer loop first)."""
    layer = layer.strip()
    filtered = [e for e in entities if not layer or _entity_layer(e) == layer]

    candidates: list[list[tuple[float, float]]] = []
    scope_boundary_present = False
    standalone_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []

    for entity in filtered:
        kind = entity.dxftype()
        if kind in _LOOP_KINDS:
            verts = _closed_tessellated_vertices(entity)
            if verts is not None:
                candidates.append(verts)
            else:
                scope_boundary_present = True
        elif kind == "CIRCLE":
            candidates.append(_tessellate_circle(
                float(entity.dxf.center.x), float(entity.dxf.center.y), float(entity.dxf.radius)))
        elif kind == "ARC":
            loop = _closed_loop_from_full_arc(entity)
            if loop is not None:
                candidates.append(loop)
            else:
                scope_boundary_present = True
        elif kind == "LINE":
            standalone_lines.append((
                (float(entity.dxf.start.x), float(entity.dxf.start.y)),
                (float(entity.dxf.end.x), float(entity.dxf.end.y))))

    if standalone_lines:
        candidates.append(_assemble_lines_into_loop(standalone_lines))

    if not candidates:
        if scope_boundary_present:
            raise CadProfileError(
                "This profile uses curved segments or separate line segments, not yet "
                "supported by this component (phase 1 supports one closed straight-sided "
                "polyline entity only).")
        raise CadProfileError(
            "No closed profile found (phase 1 supports one closed straight-sided polyline "
            "entity only).")

    if len(candidates) > 1:
        candidates = _validate_composite(candidates)

    return candidates


def _open_dxf(path: str):
    try:
        return ezdxf.readfile(path)
    except (FileNotFoundError, PermissionError, IsADirectoryError) as exc:
        msg = f"Could not open DXF file: {exc}."
        raise CadProfileError(msg[:160]) from None
    except Exception:  # noqa: BLE001 - any other read failure means "not a valid DXF file"
        raise CadProfileError("Could not read DXF file: not a valid DXF file.") from None


def _resolve_unit(doc, unit: str) -> str:
    unit = unit.strip()
    if unit:
        if unit not in _LENGTH_UNITS:
            raise CadProfileError(
                f"Unknown length unit '{unit}'; use one of LiveSheet's existing length "
                "units, e.g. 'mm', 'm', 'inch'.")
        return unit
    insunits = doc.header.get("$INSUNITS")
    resolved = INSUNITS_TO_UNIT.get(insunits) if insunits is not None else None
    if resolved is None:
        raise CadProfileError(
            "Drawing has no usable unit information; set 'unit' in this component's "
            "configuration, e.g. 'mm'.")
    return resolved


def read_profile(path: str, layer: str, unit: str) -> tuple[list[list[tuple[float, float]]], str]:
    """Opens ``path``, applies the ``layer`` filter (blank = every layer), finds every closed
    loop candidate via ``assemble_loops`` (exactly one for a plain profile, more for a spec
    014 composite outer+holes section), resolves the unit (override, ``$INSUNITS``, or error),
    and returns ``(loops, resolved_unit_name)``. Raises ``CadProfileError`` for every failure
    mode described in specs 013/014."""
    if not path:
        raise CadProfileError("No DXF file path set.")

    doc = _open_dxf(path)
    loops = assemble_loops(doc.modelspace(), layer)
    resolved_unit = _resolve_unit(doc, unit)
    return loops, resolved_unit
