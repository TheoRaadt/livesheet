"""Worksheet regions: freely placed math and text blocks on the canvas."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPen,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
)

from ..engine import RegionResult
from ..engine.formatting import format_grid, format_table
from .keys import colon_edit
from .pretty import display_source, pretty_source_html

GRID = 10
PAD = 3

MATH_FONT = QFont()
MATH_FONT.setFamilies(["Cambria Math", "STIX Two Text", "Times New Roman", "serif"])
MATH_FONT.setPointSize(14)

TEXT_FONT = QFont()
TEXT_FONT.setFamilies(["Helvetica Neue", "Segoe UI", "Arial", "sans-serif"])
TEXT_FONT.setPointSize(12)

COLOR_RESULT = "#1b4f9c"
COLOR_ERROR = "#c62828"
COLOR_FRAME = QColor("#7a9cc6")
COLOR_EDIT_BG = QColor(235, 243, 255)
COLOR_ERROR_BG = QColor(255, 235, 235)


def snap(value: float) -> float:
    return round(value / GRID) * GRID


class _Editor(QGraphicsTextItem):
    """Text item that forwards editing events to its owning region."""

    def __init__(self, region: "Region"):
        super().__init__(region)
        self.region = region
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self.region.handle_key(event):
            super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if event.reason() != Qt.FocusReason.PopupFocusReason:
            self.region.finish_editing()


class Region(QGraphicsObject):
    """Base class: a movable, selectable block containing an editor."""

    kind = "base"
    contentChanged = Signal()
    editingFinished = Signal(object, bool)   # region, move crosshair below
    moved = Signal()

    def __init__(self, text: str = ""):
        super().__init__()
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.editor = _Editor(self)
        self.editor.setPos(PAD, PAD)
        self.editor.document().setDocumentMargin(1)
        self.editing = False
        self._has_error = False
        self.editor.document().contentsChanged.connect(self._on_contents_changed)

    # -- geometry / painting ------------------------------------------------

    def content_rect(self) -> QRectF:
        return self.editor.mapRectToParent(self.editor.boundingRect())

    def boundingRect(self) -> QRectF:
        r = self.childrenBoundingRect()
        return r.adjusted(-PAD, -PAD, PAD, PAD) | QRectF(0, 0, 2 * PAD + 8, 2 * PAD + 8)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        if self.scene() is None:
            return
        rect = self.boundingRect().adjusted(0.5, 0.5, -0.5, -0.5)
        if self.editing:
            painter.fillRect(rect, COLOR_EDIT_BG)
        elif self._has_error:
            painter.fillRect(rect, COLOR_ERROR_BG)
        if self.editing or self.isSelected():
            pen = QPen(COLOR_FRAME, 1, Qt.PenStyle.DashLine if not self.editing else Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

    def _relayout(self) -> None:
        self.prepareGeometryChange()
        self.update()

    # -- editing ------------------------------------------------------------

    def start_editing(self, scene_pos: QPointF | None = None) -> None:
        if self.editing:
            return
        self.editing = True
        self._enter_edit_display()
        self.editor.setAcceptedMouseButtons(Qt.MouseButton.AllButtons)
        self.editor.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        cursor = self.editor.textCursor()
        if scene_pos is not None:
            local = self.editor.mapFromScene(scene_pos)
            pos = self.editor.document().documentLayout().hitTest(local, Qt.HitTestAccuracy.FuzzyHit)
            cursor.setPosition(max(0, pos))
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)
        self._relayout()

    def finish_editing(self, move_below: bool = False) -> None:
        if not self.editing:
            return
        self.editing = False
        self.editor.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.editor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        cursor = self.editor.textCursor()
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)
        self._leave_edit_display()
        self._relayout()
        self.editingFinished.emit(self, move_below)

    def abort_editing(self) -> None:
        """Leave edit mode without emitting signals (used right before the region is discarded)."""
        if not self.editing:
            return
        self.editing = False
        self.editor.clearFocus()
        self.editor.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.editor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def handle_key(self, event: QKeyEvent) -> bool:
        """Return True when the key was handled here."""
        if event.key() == Qt.Key.Key_Escape:
            self.editor.clearFocus()
            return True
        return False

    def mouseDoubleClickEvent(self, event) -> None:
        self.start_editing(event.scenePos())

    def _on_contents_changed(self) -> None:
        if self.editing:
            self._relayout()
            self.contentChanged.emit()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return QPointF(max(0.0, snap(value.x())), max(0.0, snap(value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.moved.emit()
        return super().itemChange(change, value)

    # -- subclasses ---------------------------------------------------------

    def is_empty(self) -> bool:
        raise NotImplementedError

    def text(self) -> str:
        raise NotImplementedError

    def _enter_edit_display(self) -> None:
        pass

    def _leave_edit_display(self) -> None:
        pass


class MathRegion(Region):
    """A single math statement plus its live result."""

    kind = "math"

    def __init__(self, source: str = ""):
        super().__init__()
        self.source = source
        self.result: RegionResult | None = None
        self.editor.setFont(MATH_FONT)
        self.result_item = QGraphicsTextItem(self)
        self.result_item.setFont(MATH_FONT)
        self.result_item.document().setDocumentMargin(1)
        self.result_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._show_display()

    def text(self) -> str:
        return self.source

    def is_empty(self) -> bool:
        return not self.source.strip()

    def handle_key(self, event: QKeyEvent) -> bool:
        key, mods, txt = event.key(), event.modifiers(), event.text()
        cursor = self.editor.textCursor()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish_editing(move_below=True)
            return True
        if txt == ":":
            delete, insert = colon_edit(self._text_before_cursor())
            for _ in range(delete):
                cursor.deletePreviousChar()
            cursor.insertText(insert)
            return True
        if txt == "=" and self._text_before_cursor().rstrip().endswith(":="):
            return True                      # ':' already produced ':='
        if txt == "~":
            cursor.insertText("≡ ")
            return True
        if key == Qt.Key.Key_Period and mods & Qt.KeyboardModifier.ControlModifier:
            cursor.insertText(" → ")
            return True
        return super().handle_key(event)

    def _text_before_cursor(self) -> str:
        cursor = self.editor.textCursor()
        return self.editor.toPlainText()[: cursor.position()]

    def _on_contents_changed(self) -> None:
        if self.editing:
            self.source = self.editor.toPlainText().replace("\n", " ").replace(" ", " ")
        super()._on_contents_changed()

    def _enter_edit_display(self) -> None:
        self.editor.document().blockSignals(True)
        self.editor.setPlainText(self.source)
        self.editor.document().blockSignals(False)
        self._place_result()

    def _leave_edit_display(self) -> None:
        self._show_display()

    def _show_display(self) -> None:
        self.editor.document().blockSignals(True)
        self.editor.setHtml(pretty_source_html(display_source(self.source)) or "&nbsp;")
        self.editor.document().blockSignals(False)
        self._place_result()

    def set_result(self, result: RegionResult | None) -> None:
        self.result = result
        self._has_error = bool(result and result.status == "error")
        if result is None or result.status == "empty":
            html = ""
        elif result.status == "error":
            html = f'<span style="color:{COLOR_ERROR}; font-size:small">&nbsp;⚠ {_esc(result.error)}</span>'
        elif result.grid:
            text = format_grid(result.grid, result.grid_unit)
            html = (f'<pre style="color:{COLOR_RESULT}; font-family:Menlo,Consolas,monospace; '
                    f'margin:0">{_esc(text)}</pre>')
        elif result.rows:
            text = format_table(result.columns, result.rows)
            html = (f'<pre style="color:{COLOR_RESULT}; font-family:Menlo,Consolas,monospace; '
                    f'margin:0">{_esc(text)}</pre>')
        else:
            html = f'<span style="color:{COLOR_RESULT}">{_esc(result.output)}</span>' if result.output else ""
        self.result_item.setHtml(html)
        self.setToolTip(result.error if self._has_error else "")
        self._place_result()

    def _place_result(self) -> None:
        r = self.editor.boundingRect()
        self.result_item.setPos(PAD + r.width() + 2, PAD)
        self._relayout()

    def _relayout(self) -> None:
        if hasattr(self, "result_item"):
            r = self.editor.boundingRect()
            self.result_item.setPos(PAD + r.width() + 2, PAD)
        super()._relayout()


class TextRegion(Region):
    """Free text (rich text) annotation."""

    kind = "text"

    def __init__(self, html: str = ""):
        super().__init__()
        self.editor.setFont(TEXT_FONT)
        self.editor.setDefaultTextColor(QColor("#222222"))
        if html:
            self.editor.setHtml(html)

    def text(self) -> str:
        return self.editor.toHtml()

    def is_empty(self) -> bool:
        return not self.editor.toPlainText().strip()

    def handle_key(self, event: QKeyEvent) -> bool:
        mods = event.modifiers()
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and mods & Qt.KeyboardModifier.ControlModifier:
            self.finish_editing(move_below=True)
            return True
        if mods & Qt.KeyboardModifier.ControlModifier and event.key() in (Qt.Key.Key_B, Qt.Key.Key_I, Qt.Key.Key_U):
            cursor = self.editor.textCursor()
            fmt = cursor.charFormat()
            if event.key() == Qt.Key.Key_B:
                fmt.setFontWeight(QFont.Weight.Normal if fmt.fontWeight() > QFont.Weight.Normal else QFont.Weight.Bold)
            elif event.key() == Qt.Key.Key_I:
                fmt.setFontItalic(not fmt.fontItalic())
            else:
                fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
            return True
        return super().handle_key(event)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = ["Region", "MathRegion", "TextRegion", "snap", "GRID"]
