"""Canvas item that lists name completions under the caret (spec 024).

A plain scene item, not a window: it never takes keyboard focus, scales with zoom and is not
painted while the worksheet is exporting. The owning ``MathRegion`` drives it.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem

from ..engine.completion import Candidate

ROWS = 8
ROW_H = 18.0
MAX_W = 360.0
MIN_W = 120.0
PAD_X = 6.0
KIND_TAGS = {"constant": "const", "variable": "var", "user_function": "user"}

POPUP_FONT = QFont()
POPUP_FONT.setPointSize(11)
COLOR_BG = QColor("#ffffff")
COLOR_BORDER = QColor("#7a9cc6")
COLOR_TEXT = QColor("#1f2a37")
COLOR_MUTED = QColor("#6b7a90")
COLOR_HILITE = QColor("#1f6feb")


class CompletionPopup(QGraphicsItem):
    def __init__(self, on_pick: Callable[[int], None] | None = None):
        super().__init__()
        self.setZValue(1000)
        self._items: list[Candidate] = []
        self._index = 0
        self._top = 0
        self._on_pick = on_pick
        self._width = MIN_W
        self._open = False

    # -- state ----------------------------------------------------------------

    def is_open(self) -> bool:
        return self._open

    def candidates(self) -> list[str]:
        return [c.name for c in self._items]

    def highlighted(self) -> int:
        return self._index

    def current(self) -> Candidate | None:
        return self._items[self._index] if self._items else None

    def visible_rows(self) -> int:
        return min(ROWS, len(self._items))

    def set_items(self, items: list[Candidate]) -> None:
        self.prepareGeometryChange()
        self._items = list(items)
        self._index = 0
        self._top = 0
        self._open = bool(items)
        self._width = self._fit_width()
        self.update()

    def clear(self) -> None:
        self._items = []
        self._open = False
        self._index = 0
        self._top = 0

    def move(self, delta: int, wrap: bool = True) -> None:
        n = len(self._items)
        if not n:
            return
        if wrap:
            self._index = (self._index + delta) % n
        else:
            self._index = max(0, min(n - 1, self._index + delta))
        if self._index < self._top:
            self._top = self._index
        elif self._index >= self._top + ROWS:
            self._top = self._index - ROWS + 1
        self.update()

    def page(self, direction: int) -> None:
        self.move(direction * ROWS, wrap=False)

    # -- geometry ---------------------------------------------------------------

    def _row_text(self, c: Candidate) -> tuple[str, str]:
        tag = KIND_TAGS.get(c.kind, "")
        hint = c.signature if c.signature and c.signature != c.name else ""
        return c.name, (f"{hint}  [{tag}]" if hint and tag else hint or (f"[{tag}]" if tag else ""))

    def _fit_width(self) -> float:
        fm = QFontMetricsF(POPUP_FONT)
        widest = 0.0
        for c in self._items[:200]:
            name, hint = self._row_text(c)
            widest = max(widest, fm.horizontalAdvance(name) + 16 + fm.horizontalAdvance(hint))
        return max(MIN_W, min(MAX_W, widest + 2 * PAD_X))

    def size(self) -> tuple[float, float]:
        return self._width, ROW_H * self.visible_rows() + 2

    def boundingRect(self) -> QRectF:
        w, h = self.size()
        return QRectF(-1, -1, w + 2, h + 2)

    # -- painting ---------------------------------------------------------------

    def paint(self, painter: QPainter, option, widget=None) -> None:
        scene = self.scene()
        if not self._open or (scene is not None and getattr(scene, "printing", False)):
            return
        w, h = self.size()
        painter.setFont(POPUP_FONT)
        painter.setPen(QPen(COLOR_BORDER, 1))
        painter.setBrush(COLOR_BG)
        painter.drawRect(QRectF(0, 0, w, h))
        fm = QFontMetricsF(POPUP_FONT)
        for row in range(self.visible_rows()):
            idx = self._top + row
            c = self._items[idx]
            rect = QRectF(1, 1 + row * ROW_H, w - 2, ROW_H)
            selected = idx == self._index
            if selected:
                painter.fillRect(rect, COLOR_HILITE)
            name, hint = self._row_text(c)
            base = rect.adjusted(PAD_X, 0, -PAD_X, 0)
            painter.setPen(QColor("#ffffff") if selected else COLOR_TEXT)
            painter.drawText(base, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
            if hint:
                x = base.left() + fm.horizontalAdvance(name) + 12
                room = base.right() - x
                if room > 20:
                    painter.setPen(QColor("#dbe7ff") if selected else COLOR_MUTED)
                    shown = fm.elidedText(hint, Qt.TextElideMode.ElideRight, room)
                    painter.drawText(QRectF(x, rect.top(), room, ROW_H),
                                     Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, shown)

    # -- mouse ------------------------------------------------------------------

    def row_at(self, local: QPointF) -> int | None:
        row = int((local.y() - 1) // ROW_H)
        if 0 <= row < self.visible_rows() and 0 <= local.x() <= self._width:
            return self._top + row
        return None

    def pick_at(self, local: QPointF) -> None:
        idx = self.row_at(local)
        if idx is not None and self._on_pick is not None:
            self._on_pick(idx)

    def mousePressEvent(self, event) -> None:
        event.accept()
        self.pick_at(event.pos())
