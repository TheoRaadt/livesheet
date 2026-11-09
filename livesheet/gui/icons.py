"""Own plain geometric toolbar glyphs (spec 025), drawn with QPainter on demand.

No raster assets: each glyph is a few lines/rects/arcs in a 20x20 design grid, stroked in the
palette's ButtonText colour (Disabled group for the disabled mode), so one drawing serves light,
dark, disabled and any device-pixel ratio.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QIconEngine,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QApplication

GRID = 20.0


def _page(p: QPainter, x: float, y: float, w: float, h: float, fold: float = 5.0) -> None:
    """A page outline with the top-right corner folded."""
    path = QPainterPath(QPointF(x, y))
    path.lineTo(x + w - fold, y)
    path.lineTo(x + w, y + fold)
    path.lineTo(x + w, y + h)
    path.lineTo(x, y + h)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(x + w - fold, y), QPointF(x + w - fold, y + fold))
    p.drawLine(QPointF(x + w - fold, y + fold), QPointF(x + w, y + fold))


def _draw_new(p: QPainter) -> None:
    _page(p, 4.5, 2.5, 11, 15)


def _draw_open(p: QPainter) -> None:
    back = QPainterPath(QPointF(2.5, 16))
    back.lineTo(2.5, 4.5)
    back.lineTo(7.5, 4.5)
    back.lineTo(9.5, 6.5)
    back.lineTo(15.5, 6.5)
    back.lineTo(15.5, 9)
    p.drawPath(back)
    front = QPolygonF([QPointF(2.5, 16), QPointF(5, 9), QPointF(18, 9), QPointF(15.5, 16)])
    p.drawPolygon(front)


def _draw_save(p: QPainter) -> None:
    body = QPainterPath(QPointF(3, 3))
    body.lineTo(14, 3)
    body.lineTo(17, 6)
    body.lineTo(17, 17)
    body.lineTo(3, 17)
    body.closeSubpath()
    p.drawPath(body)
    p.drawRect(QRectF(6, 3, 6, 4))                     # shutter along the top edge
    p.save()
    p.setBrush(p.pen().color())
    p.drawRect(QRectF(6, 11, 8, 6))                    # inset label (the only filled shape)
    p.restore()


def _arrow_head(p: QPainter, tip: QPointF, dx: float, dy: float, size: float = 3.0) -> None:
    """Open arrowhead at ``tip`` pointing along the unit-ish vector (dx, dy)."""
    nx, ny = -dy, dx
    p.drawLine(tip, QPointF(tip.x() - dx * size + nx * size, tip.y() - dy * size + ny * size))
    p.drawLine(tip, QPointF(tip.x() - dx * size - nx * size, tip.y() - dy * size - ny * size))


def _draw_export(p: QPainter) -> None:
    _page(p, 3, 2.5, 10, 15)
    p.drawLine(QPointF(8, 11), QPointF(17.5, 11))
    _arrow_head(p, QPointF(17.5, 11), 1, 0)


def _draw_recalc(p: QPainter) -> None:
    rect = QRectF(3.5, 3.5, 13, 13)
    p.drawArc(rect, 40 * 16, 280 * 16)                 # open circle, gap at the upper right
    _arrow_head(p, QPointF(14.6, 4.2), 0.9, -0.45, 3.2)


_GLYPHS: dict[str, Callable[[QPainter], None]] = {
    "new": _draw_new,
    "open": _draw_open,
    "save": _draw_save,
    "export": _draw_export,
    "recalculate": _draw_recalc,
}
GLYPH_NAMES = tuple(_GLYPHS)


def _glyph_colour(mode: QIcon.Mode) -> QColor:
    group = QPalette.ColorGroup.Disabled if mode == QIcon.Mode.Disabled else QPalette.ColorGroup.Active
    return QApplication.palette().color(group, QPalette.ColorRole.ButtonText)


def render_glyph(name: str, size: QSize, mode: QIcon.Mode = QIcon.Mode.Normal) -> QPixmap:
    """Render ``name`` into a pixmap of exactly ``size`` device pixels (transparent background)."""
    pm = QPixmap(size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = min(size.width(), size.height()) / GRID
    p.scale(scale, scale)
    pen = QPen(_glyph_colour(mode), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _GLYPHS[name](p)
    p.end()
    return pm


class GlyphIconEngine(QIconEngine):
    """Draws a glyph on demand for the requested size, mode and device-pixel ratio."""

    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def clone(self) -> "GlyphIconEngine":
        return GlyphIconEngine(self._name)

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return render_glyph(self._name, size, mode)

    def paint(self, painter: QPainter, rect, mode: QIcon.Mode, state: QIcon.State) -> None:
        pm = self.pixmap(rect.size(), mode, state)
        painter.drawPixmap(rect, pm)


def glyph_icon(name: str) -> QIcon:
    return QIcon(GlyphIconEngine(name))
