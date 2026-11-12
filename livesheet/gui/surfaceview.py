"""Drawing of 3-D surface plots (spec 031, phase A2) with plain ``QPainter`` calls.

``layout_surface`` is a pure function (no painting): it projects the normalised cube and the
visible grid cells with an orthographic view and returns everything the painter needs.
``paint_surface`` draws such a layout on any painter (screen, ``QPdfWriter``, ``QImage``), so the
PDF output is vector graphics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPen, QPolygonF

from ..engine.surface import SurfaceData, visible_cells
from .plotview import COLOR_AXIS, COLOR_TEXT, LABEL_PX, TITLE_PX, _font, tick_text

BASE_COLOR = (74, 134, 196)
LIGHT = (-0.3, -0.5, 0.8)
MIN_BRIGHTNESS = 0.35
SCALE_FACTOR = 0.42
TICK_OFFSET = 9.0
TITLE_OFFSET = 26.0
COLOR_BOX = QColor("#9a9a9a")
COLOR_WIRE = QColor("#2a5f94")
COLOR_HALO = QColor(255, 255, 255, 220)   # light backing behind labels, keeps them readable
HALO_PAD = 1.5
MAX_TITLE_CHARS = 28                      # longer default axis titles are shortened (backlog 71)
CHAR_W, CHAR_H = 6.0, 12.0                # rough label size for the overlap nudge
NUDGE_STEP, NUDGE_MAX = 7.0, 10


@dataclass
class Anchor:
    x: float
    y: float
    text: str


@dataclass
class SurfaceCell:
    polygon: list[tuple[float, float]]
    depth: float
    brightness: float
    fill: QColor | None          # None in wire mode


@dataclass
class SurfaceLayout:
    center: tuple[float, float]
    scale: float
    corners: list[tuple[float, float, float]]            # projected cube corners (x, y, depth)
    cells: list[SurfaceCell]                             # draw order: farthest first
    box_edges: list[tuple[tuple[float, float], tuple[float, float]]]
    tick_anchors: list[Anchor] = field(default_factory=list)
    title_anchor: Anchor | None = None
    axis_title_anchors: list[Anchor] = field(default_factory=list)   # x, y, z
    mode: str = "mesh"


def view_vectors(az_deg: float, el_deg: float):
    """Unit vectors (towards viewer, screen right, screen up) for azimuth/elevation in degrees."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    r = np.array([-math.sin(a), math.cos(a), 0.0])
    u = np.array([-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e)])
    return d, r, u


def _normalise(values, limits) -> np.ndarray:
    lo, hi = limits
    span = hi - lo
    return (np.asarray(values, dtype=float) - lo) / (span if span else 1.0) - 0.5


def _cube_edges() -> list[tuple[int, int]]:
    edges = []
    for a in range(8):
        for bit in (1, 2, 4):
            if not a & bit:
                edges.append((a, a | bit))
    return edges


class _Projector:
    def __init__(self, rect: QRectF, az: float, el: float, zoom: float):
        self.d, self.r, self.u = view_vectors(az, el)
        self.cx, self.cy = rect.center().x(), rect.center().y()
        self.scale = SCALE_FACTOR * min(rect.width(), rect.height()) * zoom

    def screen(self, p: np.ndarray) -> np.ndarray:
        """Project points (..., 3) to (..., 3) = screen x, screen y, depth."""
        return np.stack([self.cx + self.scale * (p @ self.r),
                         self.cy - self.scale * (p @ self.u),
                         p @ self.d], axis=-1)


def _shade(normals: np.ndarray, d: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(normals, axis=-1, keepdims=True)
    safe = np.where(length > 0, length, 1.0)
    n = np.where(length > 0, normals / safe, np.array([0.0, 0.0, 1.0]))
    flip = np.where((n @ d) < 0, -1.0, 1.0)[..., None]
    n = n * flip
    light = np.array(LIGHT) / np.linalg.norm(LIGHT)
    return MIN_BRIGHTNESS + (1.0 - MIN_BRIGHTNESS) * np.maximum(0.0, n @ light)


def _layout_cells(data: SurfaceData, proj: _Projector, mode: str) -> list[SurfaceCell]:
    cells = visible_cells(data.xs, data.ys, data.zs, data.x_limits, data.y_limits, data.z_limits)
    if not cells:
        return []
    x = _normalise(data.xs, data.x_limits)
    y = _normalise(data.ys, data.y_limits)
    z = np.nan_to_num(_normalise(data.zs, data.z_limits), nan=0.0)
    grid = np.stack([np.broadcast_to(x[None, :], z.shape), np.broadcast_to(y[:, None], z.shape), z], axis=-1)
    scr = proj.screen(grid)
    ij = np.array(cells)
    i, j = ij[:, 0], ij[:, 1]
    p00, p10, p11, p01 = grid[j, i], grid[j, i + 1], grid[j + 1, i + 1], grid[j + 1, i]
    s00, s10, s11, s01 = scr[j, i], scr[j, i + 1], scr[j + 1, i + 1], scr[j + 1, i]
    depth = (s00[:, 2] + s10[:, 2] + s11[:, 2] + s01[:, 2]) / 4.0
    bright = _shade(np.cross(p11 - p00, p01 - p10), proj.d)
    order = np.argsort(depth, kind="stable")
    base = np.array(BASE_COLOR, dtype=float)
    out = []
    for k in order:
        poly = [(float(s[k, 0]), float(s[k, 1])) for s in (s00, s10, s11, s01)]
        b = float(bright[k])
        fill = None
        if mode == "mesh":
            r, g, bl = (int(round(c)) for c in base * b)
            fill = QColor(r, g, bl)
        out.append(SurfaceCell(poly, float(depth[k]), b, fill))
    return out


def _outward(point: np.ndarray, center: tuple[float, float]) -> tuple[float, float]:
    dx, dy = point[0] - center[0], point[1] - center[1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length > 1e-9 else (0.0, 1.0)


def shorten_title(text: str, limit: int = MAX_TITLE_CHARS) -> str:
    """Shorten a long axis title with an ellipsis, keeping a trailing ' [unit]' part."""
    if len(text) <= limit:
        return text
    cut = text.rfind(" [") if text.endswith("]") else -1
    unit = text[cut:] if cut > 0 else ""
    base = text[:cut] if cut > 0 else text
    keep = max(1, limit - len(unit) - 1)
    return base[:keep].rstrip() + "\u2026" + unit


def _overlaps(a: Anchor, b: Anchor) -> bool:
    wa, wb = CHAR_W * len(a.text), CHAR_W * len(b.text)
    return abs(a.x - b.x) < (wa + wb) / 2.0 and abs(a.y - b.y) < CHAR_H


def _declutter(groups: list[tuple[list[Anchor], tuple[float, float]]]) -> None:
    """Push the labels of later axes outward until they no longer overprint earlier labels
    (the last x tick and first y tick meet at the near floor corner)."""
    placed: list[Anchor] = []
    for anchors, (ox, oy) in groups:
        for anchor in anchors:
            for _ in range(NUDGE_MAX):
                if not any(_overlaps(anchor, other) for other in placed):
                    break
                anchor.x += NUDGE_STEP * ox
                anchor.y += NUDGE_STEP * oy
        placed.extend(anchors)


def _axis_anchors(proj: _Projector, data: SurfaceData, center: tuple[float, float], norm_ticks):
    """Tick anchors, title anchor and outward direction of one axis along the edge ``edge(t)``
    (t in [-0.5, 0.5])."""
    edge, ticks, text = norm_ticks
    mid = proj.screen(edge(0.0))
    ox, oy = _outward(mid, center)
    anchors = []
    for value, t in ticks:
        pt = proj.screen(edge(t))
        anchors.append(Anchor(float(pt[0] + TICK_OFFSET * ox), float(pt[1] + TICK_OFFSET * oy),
                              tick_text(value)))
    title = Anchor(float(mid[0] + TITLE_OFFSET * ox), float(mid[1] + TITLE_OFFSET * oy),
                   shorten_title(text))
    return anchors, title, (ox, oy)


def layout_surface(data: SurfaceData, rect: QRectF, az: float, el: float, zoom: float,
                   mode: str) -> SurfaceLayout:
    """Project ``data`` into ``rect``; pure geometry, no painting."""
    rect = QRectF(rect)
    proj = _Projector(rect, az, el, zoom)
    center = (proj.cx, proj.cy)
    corner_pts = np.array([[(-0.5, 0.5)[a & 1], (-0.5, 0.5)[(a >> 1) & 1], (-0.5, 0.5)[(a >> 2) & 1]]
                           for a in range(8)])
    scr = proj.screen(corner_pts)
    corners = [(float(c[0]), float(c[1]), float(c[2])) for c in scr]
    box = [((corners[a][0], corners[a][1]), (corners[b][0], corners[b][1])) for a, b in _cube_edges()]

    sx = 0.5 if proj.d[0] >= 0 else -0.5      # side of the cube nearest the viewer
    sy = 0.5 if proj.d[1] >= 0 else -0.5
    specs = (
        (lambda t: np.array([t, sy, -0.5]), data.x_ticks, data.x_limits, data.x_label),
        (lambda t: np.array([sx, t, -0.5]), data.y_ticks, data.y_limits, data.y_label),
        (lambda t: np.array([sx, sy, t]), data.z_ticks, data.z_limits, data.z_label),
    )
    ticks, titles, groups = [], [], []
    for edge, values, limits, label in specs:
        norm = [(v, float(_normalise([v], limits)[0])) for v in values]
        anchors, title, direction = _axis_anchors(proj, data, center, (edge, norm, label))
        ticks.extend(anchors)
        titles.append(title)
        groups.append((anchors, direction))
    _declutter(groups)
    title_anchor = Anchor(proj.cx, rect.top() + 12.0, data.title)
    return SurfaceLayout(center, proj.scale, corners, _layout_cells(data, proj, mode), box, ticks,
                         title_anchor, titles, mode)


def _draw_text(painter, anchor: Anchor, fm: QFontMetricsF) -> None:
    if not anchor.text:
        return
    w = fm.horizontalAdvance(anchor.text)
    base = QPointF(anchor.x - w / 2.0, anchor.y + fm.ascent() / 2.0 - 1.0)
    back = QRectF(base.x() - HALO_PAD, base.y() - fm.ascent() - HALO_PAD,
                  w + 2 * HALO_PAD, fm.height() + 2 * HALO_PAD)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(COLOR_HALO)
    painter.drawRect(back)        # vector backing so labels stay readable over the surface
    painter.restore()
    painter.drawText(base, anchor.text)


def paint_surface(painter, rect: QRectF, data: SurfaceData, az: float, el: float, zoom: float,
                  mode: str) -> None:
    """Draw ``data`` inside ``rect``: frame, box, surface cells, tick labels and titles."""
    layout = layout_surface(data, rect, az, el, zoom, mode)
    painter.save()
    try:
        painter.setClipRect(rect)
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(COLOR_AXIS, 1))
        painter.drawRect(rect)
        painter.setPen(QPen(COLOR_BOX, 0.8))
        for (x0, y0), (x1, y1) in layout.box_edges:
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        _paint_cells(painter, layout)
        painter.setPen(QPen(COLOR_TEXT, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        small, big = _font(LABEL_PX), _font(TITLE_PX, bold=True)
        painter.setFont(small)
        fm = QFontMetricsF(small)
        for anchor in layout.tick_anchors + layout.axis_title_anchors:
            _draw_text(painter, anchor, fm)
        if layout.title_anchor is not None:
            painter.setFont(big)
            _draw_text(painter, layout.title_anchor, QFontMetricsF(big))
    finally:
        painter.restore()


def _paint_cells(painter, layout: SurfaceLayout) -> None:
    for cell in layout.cells:
        poly = QPolygonF([QPointF(x, y) for x, y in cell.polygon])
        if cell.fill is not None:
            painter.setBrush(cell.fill)
            painter.setPen(QPen(cell.fill.darker(130), 0.4))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(COLOR_WIRE, 0.7))
        painter.drawPolygon(poly)
