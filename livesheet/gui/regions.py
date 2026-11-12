"""Worksheet regions: freely placed math and text blocks on the canvas."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
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

from ..engine import RegionResult, wiring
from ..engine.formatting import format_grid, format_table
from ..engine import completion
from .completion_popup import CompletionPopup
from .keys import colon_edit
from .pretty import display_source, pretty_source_html

GRID = 10
PAD = 3
GRIP = 3   # extra hit width outside the padding while editing (spec 023)

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
        after = getattr(self.region, "after_key", None)
        if after is not None:
            after(event)

    def sceneEvent(self, event) -> bool:
        """QGraphicsTextItem hands Tab straight to its text control; while a completion popup
        is open it must reach keyPressEvent/handle_key instead (spec 024)."""
        if (event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
                and getattr(self.region, "popup_open", lambda: False)()):
            self.keyPressEvent(event)
            event.accept()
            return True
        return super().sceneEvent(event)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if event.reason() != Qt.FocusReason.PopupFocusReason:
            self.region.finish_editing()


class Region(QGraphicsObject):
    """Base class: a selectable block containing an editor. Moving is driven by the Worksheet
    (spec 023: threshold, group move, Esc-cancel); ``setPos`` still snaps and clamps."""

    kind = "base"
    contentChanged = Signal()
    editingFinished = Signal(object, bool)   # region, move crosshair below
    moved = Signal()

    def __init__(self, text: str = ""):
        super().__init__()
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.editor = _Editor(self)
        self.editor.setPos(PAD, PAD)
        self.editor.document().setDocumentMargin(1)
        self.editing = False
        self._has_error = False
        self.editor.document().contentsChanged.connect(self._on_contents_changed)
        self.setAcceptHoverEvents(True)

    # -- geometry / painting ------------------------------------------------

    def content_rect(self) -> QRectF:
        return self.editor.mapRectToParent(self.editor.boundingRect())

    def _frame_rect(self) -> QRectF:
        r = self.childrenBoundingRect()
        return r.adjusted(-PAD, -PAD, PAD, PAD) | QRectF(0, 0, 2 * PAD + 8, 2 * PAD + 8)

    def boundingRect(self) -> QRectF:
        # While editing, the hit area is widened by GRIP so the frame ring (padding + GRIP) is a
        # move grip (spec 023); the drawn frame and saved layout are unaffected.
        r = self._frame_rect()
        return r.adjusted(-GRIP, -GRIP, GRIP, GRIP) if self.editing else r

    def in_grip(self, local_pos: QPointF) -> bool:
        """True for a point on an editing region that is not inside the text area."""
        return self.editing and not self.content_rect().contains(local_pos)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        if self.scene() is None:
            return
        rect = self._frame_rect().adjusted(0.5, 0.5, -0.5, -0.5)
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
        self.prepareGeometryChange()
        self.editing = True
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.editor.setCursor(Qt.CursorShape.IBeamCursor)
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
        self.prepareGeometryChange()
        self.editing = False
        self.editor.unsetCursor()
        self.unsetCursor()
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
        self.prepareGeometryChange()
        self.editing = False
        self.editor.unsetCursor()
        self.unsetCursor()
        self.editor.clearFocus()
        self.editor.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.editor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def handle_key(self, event: QKeyEvent) -> bool:
        """Return True when the key was handled here."""
        if event.key() == Qt.Key.Key_Escape:
            scene = self.scene()
            if scene is not None and getattr(scene, "cancel_move", None) and scene.cancel_move():
                return True   # Esc during a drag cancels the drag, not the editing
            self.editor.clearFocus()
            return True
        return False

    def mouseDoubleClickEvent(self, event) -> None:
        scene = self.scene()
        if scene is not None and getattr(scene, "move_active", None) and scene.move_active():
            event.accept()   # the Worksheet runs on_double_click on release if it was no drag
            return
        self.on_double_click(event.scenePos())

    def on_double_click(self, scene_pos: QPointF) -> None:
        """Double-click action; the Worksheet defers it to button release so that a click
        followed quickly by a press-and-drag moves the region instead (spec 023)."""
        self.start_editing(scene_pos)

    def update_cursor(self, local_pos: QPointF) -> None:
        """Open hand on a movable body / the editing grip; default over special hot spots."""
        if self.editing or not self.is_hot_spot(local_pos):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def is_hot_spot(self, local_pos: QPointF) -> bool:
        return False

    def hoverEnterEvent(self, event) -> None:
        self.update_cursor(event.pos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event) -> None:
        self.update_cursor(event.pos())
        super().hoverMoveEvent(event)

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
        self._popup: CompletionPopup | None = None
        self._popup_dismissed: int | None = None   # word start the user dismissed with Esc
        self._in_key = False
        self._show_display()

    def text(self) -> str:
        return self.source

    def is_empty(self) -> bool:
        return not self.source.strip()

    def handle_key(self, event: QKeyEvent) -> bool:
        key, mods, txt = event.key(), event.modifiers(), event.text()
        self._in_key = True
        if self.popup_open() and self._popup_key(event):
            self._skip_refresh = True
            return True
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

    # -- completion popup (spec 024) ---------------------------------------------

    _skip_refresh = False

    def popup_open(self) -> bool:
        return self._popup is not None and self._popup.is_open()

    def completion_popup(self) -> CompletionPopup | None:
        return self._popup

    def _popup_key(self, event: QKeyEvent) -> bool:
        key, popup = event.key(), self._popup
        if key == Qt.Key.Key_Down:
            popup.move(1)
        elif key == Qt.Key.Key_Up:
            popup.move(-1)
        elif key == Qt.Key.Key_PageDown:
            popup.page(1)
        elif key == Qt.Key.Key_PageUp:
            popup.page(-1)
        elif key == Qt.Key.Key_Tab:
            self.accept_completion(popup.highlighted())
        elif key == Qt.Key.Key_Escape:
            word = completion.word_at(self.editor.toPlainText(), self.editor.textCursor().position())
            self._popup_dismissed = word[0] if word else None
            self.close_popup()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close_popup()
            return False
        else:
            return False
        return True

    def after_key(self, event: QKeyEvent) -> None:
        """Runs after the editor processed a key: refresh the popup after typing, else close it."""
        self._in_key = False
        if self._skip_refresh:
            self._skip_refresh = False
            return
        if not self.editing:
            return
        key = event.key()
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
                   Qt.Key.Key_CapsLock, Qt.Key.Key_AltGr):
            return
        mods = event.modifiers()
        text = event.text()
        typed = (key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
                 or (bool(text) and text.isprintable()
                     and not mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)))
        if typed:
            self.refresh_popup()
        else:
            self.close_popup()

    def _other_sources(self) -> list[str]:
        scene = self.scene()
        if scene is None or not hasattr(scene, "regions"):
            return []
        return [r.source for r in scene.regions() if r is not self and isinstance(r, MathRegion)]

    def refresh_popup(self) -> None:
        scene = self.scene()
        text, caret = self.editor.toPlainText(), self.editor.textCursor().position()
        if not self.editing or scene is None:
            self.close_popup()
            return
        word = completion.word_at(text, caret)
        if word is None:
            self._popup_dismissed = None
            self.close_popup()
            return
        if word[0] == self._popup_dismissed:
            self.close_popup()
            return
        result = completion.complete(text, caret, self._other_sources(),
                                         getattr(scene, "datasets", ()))
        if result is None:
            self.close_popup()
            return
        if self._popup is None:
            self._popup = CompletionPopup(self.accept_completion)
        if self._popup.scene() is None:
            scene.addItem(self._popup)
        self._popup.set_items(result.candidates)
        self._popup.setVisible(True)
        self._place_popup(result.start, caret)

    def _caret_scene_point(self, pos: int) -> tuple[QPointF, float]:
        doc = self.editor.document()
        block = doc.findBlock(pos)
        layout = block.layout()
        x, y, h = 0.0, 0.0, 20.0
        if layout is not None and layout.lineCount():
            line = layout.lineForTextPosition(pos - block.position())
            if line.isValid():
                x = line.cursorToX(pos - block.position())[0]
                y = line.y() + layout.position().y()
                h = line.height()
        return self.editor.mapToScene(QPointF(x, y)), h

    def _place_popup(self, start: int, caret: int) -> None:
        origin, line_h = self._caret_scene_point(start)
        w, h = self._popup.size()
        x, y = origin.x(), origin.y() + line_h + 2
        scene = self.scene()
        views = scene.views() if scene is not None else []
        if views:
            view = views[0]
            vis = view.mapToScene(view.viewport().rect()).boundingRect()
            if y + h > vis.bottom():
                y = origin.y() - h - 2
            x = max(vis.left(), min(x, vis.right() - w))
        self._popup.setPos(x, y)

    def close_popup(self) -> None:
        popup = self._popup
        if popup is None:
            return
        popup.clear()
        if popup.scene() is not None:
            popup.scene().removeItem(popup)

    def accept_completion(self, index: int) -> None:
        popup = self._popup
        if popup is None or not popup.is_open():
            return
        popup.move(index - popup.highlighted(), wrap=False)
        cand = popup.current()
        text, caret = self.editor.toPlainText(), self.editor.textCursor().position()
        self.close_popup()
        if cand is None:
            return
        new_text, new_caret = completion.accept(text, caret, cand)
        cursor = self.editor.textCursor()
        cursor.setPosition(completion.word_at(text, caret)[0] if completion.word_at(text, caret) else caret)
        cursor.setPosition(caret, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new_text[cursor.selectionStart():new_caret])
        self.editor.setTextCursor(cursor)

    def abort_editing(self) -> None:
        self.close_popup()
        super().abort_editing()

    def _text_before_cursor(self) -> str:
        cursor = self.editor.textCursor()
        return self.editor.toPlainText()[: cursor.position()]

    def _on_contents_changed(self) -> None:
        if self.editing:
            self.source = self.editor.toPlainText().replace("\n", " ").replace(" ", " ")
            if not self._in_key and self.popup_open():
                self.close_popup()   # programmatic insert (Greek buttons, formula tabs, paste)
        super()._on_contents_changed()

    def _enter_edit_display(self) -> None:
        self.editor.document().blockSignals(True)
        self.editor.setPlainText(self.source)
        self.editor.document().blockSignals(False)
        self._place_result()

    def _leave_edit_display(self) -> None:
        self.close_popup()
        self._popup_dismissed = None
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


# -- components (spec 009) ---------------------------------------------------------------------

HEADER_H = 18.0
SUMMARY_H = 14.0
ROW_H = 16.0
PORT_R = 3.5
LABEL_GAP = 6.0
MIN_BODY_W = 80.0

_COMPONENT_HEADER_FONT = QFont()
_COMPONENT_HEADER_FONT.setFamilies(["Helvetica Neue", "Segoe UI", "Arial", "sans-serif"])
_COMPONENT_HEADER_FONT.setPointSize(10)
_COMPONENT_HEADER_FONT.setBold(True)

_COMPONENT_LABEL_FONT = QFont()
_COMPONENT_LABEL_FONT.setFamilies(["Helvetica Neue", "Segoe UI", "Arial", "sans-serif"])
_COMPONENT_LABEL_FONT.setPointSize(9)


class ComponentRegion(Region):
    """A labelled box with named input/output ports (spec 009): a self-contained calculation
    step, wired to other such boxes rather than defining/using ordinary sheet variables.

    Unlike ``MathRegion``/``TextRegion``/``PlotRegion`` there is no inline text editor: the box
    is fully configured by the "Add Component" dialog at creation time (``componentdialog.py``)
    and auto-sizes to fit its header, longest port label and configuration summary -- it is not
    user-resizable in this spec.
    """

    kind = "component"

    def __init__(self, component_name: str = "", component_kind: str = "value",
                 config: dict[str, str] | None = None):
        super().__init__()
        self.component_name = component_name or "Comp"
        self.component_kind = component_kind
        self.config: dict[str, str] = dict(config or {})
        self.result = None   # engine.wiring.ComponentResult | None
        self.editor.setVisible(False)   # no inline text editor for a component
        self._inputs: list[str] = []
        self._outputs: list[str] = []
        self._summary = ""
        self._box_w = MIN_BODY_W
        self._box_h = HEADER_H + ROW_H
        self._left_margin = 0.0
        self._right_margin = 0.0
        self._layout()

    # -- Region contract -----------------------------------------------------------------

    def text(self) -> str:
        return ""   # component state round-trips via component_name/component_kind/config

    def is_empty(self) -> bool:
        return False   # a placed component is always fully configured (dialog OK, never blank)

    def start_editing(self, scene_pos: QPointF | None = None) -> None:
        pass   # no inline text editor; Enter-on-selected-component is a no-op

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()   # swallow the generic "start inline edit" double-click

    def on_double_click(self, scene_pos: QPointF) -> None:
        pass

    def is_hot_spot(self, local_pos: QPointF) -> bool:
        return self.port_at(local_pos) is not None

    # -- configuration / layout -----------------------------------------------------------

    def set_name(self, name: str) -> None:
        self.component_name = name
        self._layout()

    def set_config(self, config: dict[str, str]) -> None:
        self.config = dict(config)
        self._layout()

    def _config_summary(self) -> str:
        if self.component_kind == "value":
            return f"expr: {self.config.get('expr', '')}"
        if self.component_kind == "formula":
            return f"({self.config.get('inputs', '')}) = {self.config.get('expr', '')}"
        return ""

    def _layout(self) -> None:
        self.prepareGeometryChange()
        self._inputs = [p for p, _required in wiring.input_ports(self.component_kind, self.config)]
        self._outputs = wiring.output_ports(self.component_kind, self.config)
        self._summary = self._config_summary()
        header_metrics = QFontMetricsF(_COMPONENT_HEADER_FONT)
        label_metrics = QFontMetricsF(_COMPONENT_LABEL_FONT)
        header_text = f"{self.component_name}: {self.component_kind}"
        header_w = header_metrics.horizontalAdvance(header_text) + 2 * PAD
        summary_w = (label_metrics.horizontalAdvance(self._summary) + 2 * PAD) if self._summary else 0.0
        self._box_w = max(header_w, summary_w, MIN_BODY_W)
        rows = max(1, len(self._inputs), len(self._outputs))
        self._box_h = HEADER_H + (SUMMARY_H if self._summary else 0.0) + rows * ROW_H + PAD
        left_label_w = max((label_metrics.horizontalAdvance(n) for n in self._inputs), default=0.0)
        right_label_w = max((label_metrics.horizontalAdvance(n) for n in self._outputs), default=0.0)
        self._left_margin = (left_label_w + LABEL_GAP + 2 * PORT_R) if self._inputs else 0.0
        self._right_margin = (right_label_w + LABEL_GAP + 2 * PORT_R) if self._outputs else 0.0
        self.update()

    # -- geometry -------------------------------------------------------------------------

    def _box_rect(self) -> QRectF:
        return QRectF(0, 0, self._box_w, self._box_h)

    def boundingRect(self) -> QRectF:
        return self._box_rect().adjusted(-self._left_margin, -2, self._right_margin, 2)

    def content_rect(self) -> QRectF:
        return self._box_rect()

    def _row_top(self) -> float:
        return HEADER_H + (SUMMARY_H if self._summary else 0.0)

    def _row_y(self, i: int) -> float:
        return self._row_top() + ROW_H * i + ROW_H / 2

    def _input_pos(self, i: int) -> QPointF:
        return QPointF(0.0, self._row_y(i))

    def _output_pos(self, i: int) -> QPointF:
        return QPointF(self._box_w, self._row_y(i))

    def port_at(self, local_pos: QPointF, tolerance: float = 7.0) -> tuple[str, str] | None:
        """``("input"|"output", port_name)`` for the port terminal nearest ``local_pos`` (item
        coordinates), within ``tolerance``; ``None`` when nothing is close enough -- used both by
        the drag-to-connect gesture and by the "Connect…" context-menu action (spec 009)."""
        for i, name in enumerate(self._inputs):
            d = self._input_pos(i) - local_pos
            if (d.x() ** 2 + d.y() ** 2) ** 0.5 <= tolerance:
                return ("input", name)
        for i, name in enumerate(self._outputs):
            d = self._output_pos(i) - local_pos
            if (d.x() ** 2 + d.y() ** 2) ** 0.5 <= tolerance:
                return ("output", name)
        return None

    def port_scene_pos(self, side: str, name: str) -> QPointF:
        """Scene position of a named port's terminal centre, for wire drawing. Falls back to the
        box edge's vertical centre when ``name`` is not currently a declared port of this
        component's kind -- keeps a wire from a corrupted/forward-compatible file (unrecognised
        ``component_kind``, see spec 009's edge cases) drawable rather than crashing."""
        ports = self._inputs if side == "input" else self._outputs
        if name in ports:
            i = ports.index(name)
            local = self._input_pos(i) if side == "input" else self._output_pos(i)
        else:
            local = QPointF(0.0 if side == "input" else self._box_w, self._box_h / 2)
        return self.mapToScene(local)

    # -- painting -------------------------------------------------------------------------

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        if self.scene() is None:
            return
        rect = self._box_rect()
        painter.fillRect(rect, COLOR_ERROR_BG if self._has_error else QColor("#ffffff"))
        painter.setPen(QPen(COLOR_FRAME, 1.5 if self.isSelected() else 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        painter.setFont(_COMPONENT_HEADER_FONT)
        painter.setPen(QColor("#222222"))
        header_rect = QRectF(rect.left() + PAD, rect.top(), rect.width() - 2 * PAD, HEADER_H)
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                          f"{self.component_name}: {self.component_kind}")
        painter.drawLine(QPointF(rect.left(), rect.top() + HEADER_H),
                          QPointF(rect.right(), rect.top() + HEADER_H))

        if self._summary:
            painter.setFont(_COMPONENT_LABEL_FONT)
            painter.setPen(QColor("#666666"))
            summary_rect = QRectF(rect.left() + PAD, rect.top() + HEADER_H,
                                   rect.width() - 2 * PAD, SUMMARY_H)
            painter.drawText(summary_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                              self._summary)

        painter.setFont(_COMPONENT_LABEL_FONT)
        painter.setPen(QColor("#222222"))
        painter.setBrush(QColor(COLOR_FRAME))
        for i, name in enumerate(self._inputs):
            pos = self._input_pos(i)
            painter.drawEllipse(pos, PORT_R, PORT_R)
            label_rect = QRectF(rect.left() - self._left_margin, pos.y() - 7,
                                 self._left_margin - LABEL_GAP, 14)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)
        for i, name in enumerate(self._outputs):
            pos = self._output_pos(i)
            painter.drawEllipse(pos, PORT_R, PORT_R)
            label_rect = QRectF(rect.right() + LABEL_GAP, pos.y() - 7,
                                 self._right_margin - LABEL_GAP, 14)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

    # -- result / error state --------------------------------------------------------------

    def set_result(self, result) -> None:
        self.result = result
        self._has_error = bool(result and result.status == "error")
        self.setToolTip(result.error if result and result.status == "error" else "")
        self.update()


__all__ = ["Region", "MathRegion", "TextRegion", "ComponentRegion", "snap", "GRID"]
