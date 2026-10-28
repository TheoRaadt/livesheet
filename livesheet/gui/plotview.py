"""Drawing of 2-D plots (spec 004, phase A2) with plain ``QPainter`` calls.

``paint_plot`` works on any painter (screen, ``QPdfWriter``, ``QImage``) and only issues painter
calls (lines, polygons, text), so the PDF output is vector graphics.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen, QPolygonF

from ..engine.formatting import format_number
from ..engine.plotting import PlotData

PALETTE = ("#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf")
COLOR_AXIS = QColor("#333333")
COLOR_GRID = QColor("#e3e6ea")
COLOR_TEXT = QColor("#222222")
LABEL_PX = 11
TITLE_PX = 13
TICK_LEN = 4.0
DOT_RADIUS = 2.2
_BIG = 1e6   # pixel coordinates are clamped to this so extreme data cannot upset the paint engine


def trace_color(style_index: int) -> QColor:
    return QColor(PALETTE[style_index % len(PALETTE)])


def tick_text(value: float) -> str:
    """Tick label through the sheet's number formatter (6 significant digits)."""
    text = format_number(value, 6)
    return "0" if text in ("-0", "-0.0") else text


def _font(pixel: int, bold: bool = False) -> QFont:
    font = QFont()
    font.setFamilies(["Helvetica Neue", "Segoe UI", "Arial", "sans-serif"])
    font.setPixelSize(pixel)
    font.setBold(bold)
    return font


def _clamp(v: float) -> float:
    return max(-_BIG, min(_BIG, v))


def _mapper(lo: float, hi: float, start: float, length: float, flip: bool):
    span = hi - lo
    if not span > 0 or not math.isfinite(span):
        span = 1.0

    def f(v: float) -> float:
        t = (v - lo) / span
        return _clamp(start + (length * (1.0 - t) if flip else length * t))
    return f


def _segments(xs: list[float], ys: list[float], fx, fy) -> list[list[QPointF]]:
    """Split a trace into runs of consecutive finite points (NaN/inf make a gap)."""
    runs: list[list[QPointF]] = []
    run: list[QPointF] = []
    for x, y in zip(xs, ys):
        if math.isfinite(x) and math.isfinite(y):
            run.append(QPointF(fx(x), fy(y)))
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def paint_plot(painter, rect: QRectF, data: PlotData) -> None:
    """Draw ``data`` inside ``rect`` (frame, grid, ticks, labels, traces, title)."""
    painter.save()
    try:
        _paint(painter, QRectF(rect), data)
    finally:
        painter.restore()


def _paint(painter, rect: QRectF, data: PlotData) -> None:
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    label_font, title_font = _font(LABEL_PX), _font(TITLE_PX, bold=True)
    fm = QFontMetricsF(label_font)
    x_ticks = [(t, tick_text(t)) for t in data.x_ticks if data.x_limits[0] <= t <= data.x_limits[1]]
    y_ticks = [(t, tick_text(t)) for t in data.y_ticks if data.y_limits[0] <= t <= data.y_limits[1]]
    top = 8.0 + (QFontMetricsF(title_font).height() + 4 if data.title else 0.0)
    left = 8.0 + (fm.height() + 4 if data.y_label else 0.0) + max(
        (fm.horizontalAdvance(s) for _, s in y_ticks), default=0.0) + TICK_LEN + 4
    bottom = 8.0 + (fm.height() + 2 if data.x_label else 0.0) + fm.height() + TICK_LEN + 2
    area = QRectF(rect.left() + left, rect.top() + top,
                  max(10.0, rect.width() - left - 14), max(10.0, rect.height() - top - bottom))
    fx = _mapper(*data.x_limits, area.left(), area.width(), flip=False)
    fy = _mapper(*data.y_limits, area.top(), area.height(), flip=True)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(COLOR_GRID, 1))
    for t, _ in x_ticks:
        painter.drawLine(QPointF(fx(t), area.top()), QPointF(fx(t), area.bottom()))
    for t, _ in y_ticks:
        painter.drawLine(QPointF(area.left(), fy(t)), QPointF(area.right(), fy(t)))

    _paint_traces(painter, area, data, fx, fy)

    painter.setPen(QPen(COLOR_AXIS, 1))
    painter.drawRect(area)
    painter.setFont(label_font)
    painter.setPen(QPen(COLOR_TEXT, 1))
    for t, s in x_ticks:
        px = fx(t)
        painter.setPen(QPen(COLOR_AXIS, 1))
        painter.drawLine(QPointF(px, area.bottom()), QPointF(px, area.bottom() + TICK_LEN))
        painter.setPen(QPen(COLOR_TEXT, 1))
        w = fm.horizontalAdvance(s)
        painter.drawText(QPointF(px - w / 2, area.bottom() + TICK_LEN + fm.ascent() + 1), s)
    for t, s in y_ticks:
        py = fy(t)
        painter.setPen(QPen(COLOR_AXIS, 1))
        painter.drawLine(QPointF(area.left() - TICK_LEN, py), QPointF(area.left(), py))
        painter.setPen(QPen(COLOR_TEXT, 1))
        painter.drawText(QPointF(area.left() - TICK_LEN - 3 - fm.horizontalAdvance(s), py + fm.ascent() / 2 - 1), s)
    _paint_labels(painter, rect, area, data, fm, title_font)


def _paint_traces(painter, area: QRectF, data: PlotData, fx, fy) -> None:
    painter.save()
    painter.setClipRect(area)
    for trace in data.traces:
        color = trace_color(trace.style_index)
        runs = _segments(trace.x, trace.y, fx, fy)
        painter.setPen(QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for run in runs:
            if len(run) > 1:
                painter.drawPolyline(QPolygonF(run))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for run in runs:
            if len(run) == 1:
                painter.drawEllipse(run[0], DOT_RADIUS, DOT_RADIUS)
    painter.restore()


def _paint_labels(painter, rect: QRectF, area: QRectF, data: PlotData, fm: QFontMetricsF, title_font: QFont) -> None:
    painter.setPen(QPen(COLOR_TEXT, 1))
    if data.title:
        painter.setFont(title_font)
        tfm = QFontMetricsF(title_font)
        w = tfm.horizontalAdvance(data.title)
        painter.drawText(QPointF(area.center().x() - w / 2, rect.top() + 6 + tfm.ascent()), data.title)
    painter.setFont(_font(LABEL_PX))
    if data.x_label:
        w = fm.horizontalAdvance(data.x_label)
        painter.drawText(QPointF(area.center().x() - w / 2, rect.bottom() - 6 - fm.descent()), data.x_label)
    if data.y_label:
        painter.save()
        w = fm.horizontalAdvance(data.y_label)
        painter.translate(rect.left() + 6 + fm.ascent(), area.center().y() + w / 2)
        painter.rotate(-90)
        painter.drawText(QPointF(0, 0), data.y_label)
        painter.restore()


def paint_message(painter, rect: QRectF, text: str, color: QColor | str, frame: bool = True) -> None:
    """Centre ``text`` (word-wrapped) in ``rect``, optionally inside a thin frame."""
    painter.save()
    try:
        if frame:
            painter.setPen(QPen(COLOR_AXIS, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        painter.setPen(QPen(QColor(color), 1))
        painter.setFont(_font(LABEL_PX + 1))
        painter.drawText(rect.adjusted(10, 10, -10, -10),
                         int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap), text)
    finally:
        painter.restore()
