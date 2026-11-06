"""Generic layout widgets for the window-wide wrapping tab strip (spec 022).

``TabStrip`` is a row-wrapping, justified strip of tab buttons (a pure view: the owner keeps the
tab model and mirrors it into the strip). ``FlowLayout`` is a plain wrapping layout used for the
click-to-insert button pages in the band under the strip. Nothing here knows about LiveSheet's
tokens or tabs.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QLayout,
    QLayoutItem,
    QSizePolicy,
    QWidget,
    QWidgetItem,
)

GAP = 2   # px between strip buttons and between strip rows


def greedy_rows(widths: list[int], total: int, gap: int = GAP) -> list[list[int]]:
    """Greedy, order-preserving row fill: indices of ``widths`` grouped into rows that fit ``total``."""
    rows: list[list[int]] = []
    used = 0
    for i, w in enumerate(widths):
        if rows and used + gap + w <= total:
            rows[-1].append(i)
            used += gap + w
        else:
            rows.append([i])
            used = w
    return rows


def _blend(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


class TabStripButton(QAbstractButton):
    """One tab of the strip. Checked == selected. Painted from the live palette (no hard-coded
    colours), so light/dark switches need no restyling. The selected look has three cues beyond
    plain state: tinted fill, a heavy underline in the accent colour and a bold label."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName(text)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def nextCheckState(self) -> None:   # the strip owns the selected state, not a click toggle
        pass

    def _bold_font(self) -> QFont:
        font = QFont(self.font())
        font.setBold(True)
        return font

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._bold_font())   # bold metrics always, so selecting never reflows
        return QSize(fm.horizontalAdvance(self.text()) + 24, fm.height() + 12)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        pal = self.palette()
        rect = self.rect()
        base = pal.color(pal.ColorRole.Button)
        accent = pal.color(pal.ColorRole.Highlight)
        text_colour = pal.color(pal.ColorRole.ButtonText)
        selected = self.isChecked()
        if selected:
            fill = _blend(base, accent, 0.30)
        elif self.underMouse():
            fill = _blend(base, text_colour, 0.12)
        else:
            fill = base
        p.fillRect(rect, fill)
        p.setPen(QPen(pal.color(pal.ColorRole.Mid), 1))
        p.drawRect(rect.adjusted(0, 0, -1, -1))
        if selected:
            p.fillRect(QRect(0, rect.height() - 4, rect.width(), 4), accent)
        font = self._bold_font() if selected else self.font()
        p.setFont(font)
        p.setPen(text_colour)
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text())
        if self.hasFocus():
            ring = QPen(pal.color(pal.ColorRole.WindowText), 2, Qt.PenStyle.DotLine)
            p.setPen(ring)
            p.drawRect(rect.adjusted(3, 3, -4, -4))
        p.end()

    def keyPressEvent(self, event) -> None:
        strip = self.parent()
        if isinstance(strip, TabStrip) and strip.handle_key(self, event):
            event.accept()
            return
        super().keyPressEvent(event)


class TabStrip(QWidget):
    """Wrapping, justified strip of ``TabStripButton`` (height-for-width)."""

    tabRequested = Signal(int)   # user asked for tab i (click or key); owner decides

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: list[TabStripButton] = []
        self._current = -1
        self._button_h = 0
        self._last_min_h = -1
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # -- model mirror ---------------------------------------------------------

    def buttons(self) -> list[TabStripButton]:
        return list(self._buttons)

    def current(self) -> int:
        return self._current

    def set_labels(self, labels: list[str], current: int) -> None:
        for b in self._buttons:
            b.setParent(None)
            b.deleteLater()
        self._buttons = []
        for i, text in enumerate(labels):
            b = TabStripButton(text, self)
            b.clicked.connect(lambda _c=False, k=i: self._on_clicked(k))
            b.show()
            self._buttons.append(b)
        self._button_h = max((b.sizeHint().height() for b in self._buttons), default=0)
        self._current = -1
        self.set_current(current)
        self.updateGeometry()
        self._relayout()

    def set_current(self, index: int) -> None:
        self._current = index
        for i, b in enumerate(self._buttons):
            on = i == index
            b.setChecked(on)
            b.setFocusPolicy(Qt.FocusPolicy.TabFocus if on else Qt.FocusPolicy.NoFocus)
            b.update()
        self.setFocusProxy(self._buttons[index] if 0 <= index < len(self._buttons) else None)

    def _on_clicked(self, index: int) -> None:
        if index != self._current:
            self.tabRequested.emit(index)
        else:
            self._buttons[index].setChecked(True)

    # -- geometry -------------------------------------------------------------

    def _natural(self) -> list[int]:
        return [b.sizeHint().width() for b in self._buttons]

    def _row_count(self, width: int) -> int:
        return len(greedy_rows(self._natural(), width))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        if not self._buttons:
            return 0
        rows = self._row_count(width)
        return rows * self._button_h + (rows - 1) * GAP

    def minimumSizeHint(self) -> QSize:
        widest = max(self._natural(), default=0)
        # Height follows the wrapped height at the current width, so a layout never squeezes the
        # strip below what its rows need (the band shrinks first, spec 022 edge cases).
        return QSize(widest, self.heightForWidth(max(self.width(), widest)))

    def sizeHint(self) -> QSize:
        total = sum(self._natural()) + GAP * max(len(self._buttons) - 1, 0)
        return QSize(total, self.heightForWidth(total))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._relayout()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == event.Type.FontChange:
            self._button_h = max((b.sizeHint().height() for b in self._buttons), default=0)
            self.updateGeometry()
            self._relayout()

    def _relayout(self) -> None:
        if not self._buttons:
            return
        if self.minimumSizeHint().height() != self._last_min_h:
            self._last_min_h = self.minimumSizeHint().height()
            self.updateGeometry()
        total = self.width()
        rows = greedy_rows(self._natural(), total)
        y = 0
        for row in rows:
            naturals = [self._buttons[i].sizeHint().width() for i in row]
            extra = max(total - sum(naturals) - GAP * (len(row) - 1), 0)
            base, rem = divmod(extra, len(row))
            x = 0
            for n, i in enumerate(row):
                w = naturals[n] + base + (1 if n < rem else 0)
                self._buttons[i].setGeometry(x, y, w, self._button_h)
                x += w + GAP
            y += self._button_h + GAP

    def row_indices(self) -> list[list[int]]:
        """Button indices grouped by their current visual row (top to bottom, left to right)."""
        by_y: dict[int, list[int]] = {}
        for i, b in enumerate(self._buttons):
            by_y.setdefault(b.y(), []).append(i)
        return [sorted(by_y[y], key=lambda i: self._buttons[i].x()) for y in sorted(by_y)]

    # -- keyboard -------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        index = self._current
        focus = self.window().focusWidget() if self.window() else None
        target = focus if focus in self._buttons else (
            self._buttons[index] if 0 <= index < len(self._buttons) else None)
        if target is None or not self.handle_key(target, event):
            super().keyPressEvent(event)
        else:
            event.accept()

    def handle_key(self, button: TabStripButton, event) -> bool:
        if button not in self._buttons:
            return False
        i = self._buttons.index(button)
        key = event.key()
        K = Qt.Key
        if key in (K.Key_Space, K.Key_Return, K.Key_Enter):
            self._go(i, focus=True)
            return True
        if key == K.Key_Left:
            self._go(i - 1, focus=True)
        elif key == K.Key_Right:
            self._go(i + 1, focus=True)
        elif key == K.Key_Home:
            self._go(0, focus=True)
        elif key == K.Key_End:
            self._go(len(self._buttons) - 1, focus=True)
        elif key in (K.Key_Up, K.Key_Down):
            self._go(self._vertical_neighbour(i, -1 if key == K.Key_Up else 1), focus=True)
        else:
            return False
        return True

    def _vertical_neighbour(self, i: int, step: int) -> int:
        rows = self.row_indices()
        r = next(n for n, row in enumerate(rows) if i in row)
        if not 0 <= r + step < len(rows):
            return i
        cx = self._buttons[i].geometry().center().x()
        return min(rows[r + step], key=lambda k: abs(self._buttons[k].geometry().center().x() - cx))

    def _go(self, index: int, focus: bool) -> None:
        if not 0 <= index < len(self._buttons):
            return
        if index != self._current:
            self.tabRequested.emit(index)
        if focus:
            self._buttons[index].setFocus(Qt.FocusReason.OtherFocusReason)


class FlowLayout(QLayout):
    """Left-to-right wrapping layout; an item may be flagged to always start a new row."""

    def __init__(self, parent: QWidget | None = None, margin: int = 6, spacing: int = 4):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._breaks: list[bool] = []
        self._gap = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def add_widget(self, widget: QWidget, new_row: bool = False) -> None:
        self.addChildWidget(widget)
        self._items.append(QWidgetItem(widget))
        self._breaks.append(new_row)
        self.invalidate()

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)
        self._breaks.append(False)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            self._breaks.pop(index)
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._flow(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._flow(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _flow(self, rect: QRect, apply: bool) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = area.x(), area.y(), 0
        for item, new_row in zip(self._items, self._breaks):
            hint = item.sizeHint()
            w = min(hint.width(), max(area.width(), 1))
            if x > area.x() and (new_row or x + w > area.right() + 1):
                x = area.x()
                y += line_h + self._gap
                line_h = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, hint.height())))
            x += w + self._gap
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


__all__ = ["GAP", "greedy_rows", "TabStripButton", "TabStrip", "FlowLayout"]
