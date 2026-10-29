"""Plot region: a text spec while editing, a drawn chart otherwise (spec 004, phase A2)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsProxyWidget, QPushButton, QStyleOptionGraphicsItem

from ..document import DEFAULT_PLOT_SIZE
from ..engine import RegionResult
from .plotview import paint_message, paint_plot
from .regions import COLOR_EDIT_BG, COLOR_ERROR, COLOR_FRAME, GRID, PAD, Region, snap

MIN_SIZE = (200.0, 140.0)
HANDLE = 12.0
STARTER_TEXT = "plot\nover \nshow "
HINT_TEXT = "Empty plot: double-click to edit.\nAdd an 'over' line (range or vector) and one or more 'show' lines."

SPEC_FONT = QFont()
SPEC_FONT.setFamilies(["Menlo", "Consolas", "DejaVu Sans Mono", "monospace"])
SPEC_FONT.setStyleHint(QFont.StyleHint.Monospace)
SPEC_FONT.setPointSize(12)


def spec_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def is_plot_spec(text: str) -> bool:
    """True when the first non-blank line is exactly ``plot`` (the engine's own rule)."""
    lines = spec_lines(text)
    return bool(lines) and lines[0] == "plot"


def is_blank_spec(text: str) -> bool:
    """A spec without content: just ``plot`` plus bare ``over`` / ``show`` keywords."""
    lines = spec_lines(text)
    return bool(lines) and lines[0] == "plot" and all(ln in ("over", "show") for ln in lines[1:])


def engine_source(text: str) -> str:
    """Text handed to the engine; anything that is not a plot spec can never define a name."""
    return text if is_plot_spec(text) else "plot\n" + text


def clamp_size(w: float, h: float) -> tuple[float, float]:
    """Snap a plot size to the grid and apply the minimum size."""
    return max(MIN_SIZE[0], snap(w)), max(MIN_SIZE[1], snap(h))


class PlotRegion(Region):
    kind = "plot"

    def __init__(self, text: str = "", w: float | None = None, h: float | None = None):
        super().__init__()
        self.source = text
        self.size_w = float(w) if w else DEFAULT_PLOT_SIZE[0]
        self.size_h = float(h) if h else DEFAULT_PLOT_SIZE[1]
        self.result: RegionResult | None = None
        self._resizing: tuple[QPointF, float, float] | None = None
        # Whether this region currently has a previously-committed, saved spec to fall back to:
        # used by the dialog's Cancel to decide "discard the new region" vs "revert its text"
        # (spec 006). True from the start for a region created with real text (e.g. loaded from
        # a file); set True once a brand-new region's dialog session ends with OK, or once its
        # raw text editor is committed with non-empty content, exactly like any other region.
        self.has_baseline = bool(text.strip())
        self.editor.setFont(SPEC_FONT)
        self.editor.setDefaultTextColor(QColor("#222222"))
        self._set_editor_text()
        self.editor.setVisible(False)
        self._use_dialog_btn = QPushButton("Use dialog...")
        self._use_dialog_btn.setStyleSheet("font-size: 10px; padding: 1px 6px;")
        self._use_dialog_btn.clicked.connect(self._on_use_dialog_clicked)
        self._use_dialog_proxy = QGraphicsProxyWidget(self)
        self._use_dialog_proxy.setWidget(self._use_dialog_btn)
        self._use_dialog_proxy.setVisible(False)

    # -- content -----------------------------------------------------------------

    def text(self) -> str:
        return self.source

    def is_empty(self) -> bool:
        return not self.source.strip()

    def _set_editor_text(self) -> None:
        self.editor.document().blockSignals(True)
        self.editor.setPlainText(self.source)
        self.editor.document().blockSignals(False)

    def _on_contents_changed(self) -> None:
        if self.editing:
            self.source = self.editor.toPlainText().replace("\u00a0", " ")
            self._update_use_dialog_control()
        super()._on_contents_changed()

    def set_result(self, result: RegionResult | None) -> None:
        self.result = result
        self.setToolTip(result.error if result and result.status == "error" else "")
        self.update()

    def set_size(self, w: float, h: float) -> None:
        w, h = clamp_size(w, h)
        if (w, h) != (self.size_w, self.size_h):
            self.prepareGeometryChange()
            self.size_w, self.size_h = w, h
            self.update()
            self.moved.emit()

    # -- editing display -----------------------------------------------------------

    def _enter_edit_display(self) -> None:
        self._set_editor_text()
        self.editor.setVisible(True)
        self._update_use_dialog_control()

    def _leave_edit_display(self) -> None:
        self.editor.setVisible(False)
        self._use_dialog_proxy.setVisible(False)

    def _update_use_dialog_control(self) -> None:
        """Keep the raw editor's reciprocal 'Use dialog...' control positioned and enabled only
        when the current text is representable by the dialog (spec 006)."""
        from .plotdialog import decompose_plot_text

        ok = decompose_plot_text(self.source) is not None
        self._use_dialog_btn.setEnabled(ok)
        self._use_dialog_btn.setToolTip(
            "" if ok else "Not representable by the dialog (this text uses raw-only options).")
        rect = self.content_rect()
        self._use_dialog_proxy.setPos(rect.left(), rect.bottom() + 2)
        self._use_dialog_proxy.setVisible(True)

    def _on_use_dialog_clicked(self) -> None:
        self.finish_editing()
        scene = self.scene()
        if scene is None:
            return
        from .plotdialog import PlotDialog

        parent = scene.views()[0] if scene.views() else None
        dialog = PlotDialog(self, scene, parent=parent)
        dialog.exec()

    # -- geometry / painting -------------------------------------------------------

    def chart_rect(self) -> QRectF:
        return QRectF(0, 0, self.size_w, self.size_h)

    def handle_rect(self) -> QRectF:
        return QRectF(self.size_w - HANDLE, self.size_h - HANDLE, HANDLE, HANDLE)

    def boundingRect(self) -> QRectF:
        rect = self.chart_rect().adjusted(-1, -1, 1, 1)
        if self.editing:
            rect |= self.content_rect().adjusted(-PAD, -PAD, PAD, PAD)
            btn_rect = QRectF(self._use_dialog_proxy.pos(), self._use_dialog_btn.sizeHint())
            rect |= btn_rect.adjusted(-PAD, -PAD, PAD, PAD)
        return rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        if self.scene() is None:
            return
        rect = self.chart_rect()
        if self.editing:
            full = self.boundingRect().adjusted(1.5, 1.5, -1.5, -1.5)
            painter.fillRect(full, COLOR_EDIT_BG)
            painter.setPen(QPen(COLOR_FRAME, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(full)
            return
        painter.fillRect(rect, QColor("#ffffff"))
        self._paint_content(painter, rect)
        if self.isSelected():
            painter.setPen(QPen(COLOR_FRAME, 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(-1, -1, 1, 1))
            painter.fillRect(self.handle_rect(), COLOR_FRAME)

    def _paint_content(self, painter: QPainter, rect: QRectF) -> None:
        res = self.result
        if not is_plot_spec(self.source) and self.source.strip():
            paint_message(painter, rect, "A plot spec must start with the line 'plot'.", COLOR_ERROR)
        elif is_blank_spec(self.source) or not self.source.strip():
            paint_message(painter, rect, HINT_TEXT, "#7a7a7a")
        elif res is None:
            paint_message(painter, rect, "", COLOR_ERROR)
        elif res.status == "error":
            paint_message(painter, rect, res.error, COLOR_ERROR)
        elif res.plot is not None:
            paint_plot(painter, rect, res.plot)
        else:
            paint_message(painter, rect, "", COLOR_ERROR)

    # -- opening the dialog or the raw editor ---------------------------------------------

    def mouseDoubleClickEvent(self, event) -> None:
        from .plotdialog import PlotDialog, decompose_plot_text

        if decompose_plot_text(self.source) is not None:
            scene = self.scene()
            parent = scene.views()[0] if scene and scene.views() else None
            dialog = PlotDialog(self, scene, parent=parent)
            dialog.exec()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # -- resizing ---------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.LeftButton and not self.editing
                and self.handle_rect().contains(event.pos())):
            self._resizing = (event.scenePos(), self.size_w, self.size_h)
            self.setSelected(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing is not None:
            start, w, h = self._resizing
            delta = event.scenePos() - start
            self.set_size(w + delta.x(), h + delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resizing is not None:
            self._resizing = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


__all__ = ["PlotRegion", "STARTER_TEXT", "MIN_SIZE", "GRID", "engine_source", "is_plot_spec", "clamp_size"]
