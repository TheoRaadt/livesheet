"""The worksheet canvas: scene with regions, crosshair and live recalculation."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from ..document import RegionData, SheetDocument
from ..engine import Engine
from .regions import GRID, MathRegion, Region, TextRegion, snap

PAGE_WIDTH = 820
MIN_HEIGHT = 1100
RECALC_DELAY_MS = 200


class Crosshair(QGraphicsItem):
    """Red insertion cross, Mathcad style."""

    SIZE = 7

    def __init__(self):
        super().__init__()
        self.setZValue(1000)

    def boundingRect(self) -> QRectF:
        s = self.SIZE + 1
        return QRectF(-s, -s, 2 * s, 2 * s)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setPen(QPen(QColor("#d32f2f"), 1.5))
        s = self.SIZE
        painter.drawLine(QPointF(-s, 0), QPointF(s, 0))
        painter.drawLine(QPointF(0, -s), QPointF(0, s))


class Worksheet(QGraphicsScene):
    modifiedChanged = Signal(bool)
    statusMessage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = Engine()
        self.crosshair = Crosshair()
        self.addItem(self.crosshair)
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self._modified = False
        self.printing = False  # suppress grid/page edge while exporting
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(RECALC_DELAY_MS)
        self._timer.timeout.connect(self.recalculate)
        self._update_rect()

    # -- state ----------------------------------------------------------------

    @property
    def modified(self) -> bool:
        return self._modified

    def set_modified(self, value: bool = True) -> None:
        if value != self._modified:
            self._modified = value
            self.modifiedChanged.emit(value)

    @property
    def significant(self) -> int:
        return self.engine.significant

    def set_significant(self, digits: int) -> None:
        self.engine.significant = digits
        self.set_modified()
        self.recalculate()

    def regions(self) -> list[Region]:
        return [it for it in self.items() if isinstance(it, Region)]

    def ordered_regions(self) -> list[Region]:
        return sorted(self.regions(), key=lambda r: (r.pos().y(), r.pos().x()))

    def editing_region(self) -> Region | None:
        for r in self.regions():
            if r.editing:
                return r
        return None

    # -- region management -----------------------------------------------------

    def add_region(self, kind: str, pos: QPointF, text: str = "") -> Region:
        region: Region = MathRegion(text) if kind == "math" else TextRegion(text)
        self.addItem(region)
        region.setPos(QPointF(snap(pos.x()), snap(pos.y())))
        region.contentChanged.connect(self._on_content_changed)
        region.editingFinished.connect(self._on_editing_finished)
        region.moved.connect(self._on_moved)
        self._update_rect()
        return region

    def insert_region(self, kind: str, initial_text: str = "") -> Region:
        """Create a region at the crosshair and start editing it."""
        current = self.editing_region()
        if current is not None:
            current.finish_editing()
        region = self.add_region(kind, self.crosshair.pos())
        self.clearSelection()
        region.start_editing()
        if initial_text:
            region.editor.textCursor().insertText(initial_text)
            region.editor.setTextCursor(region.editor.textCursor())
        self.crosshair.hide()
        self.set_modified()
        return region

    def remove_regions(self, regions: list[Region]) -> None:
        if not regions:
            return
        for r in regions:
            self.removeItem(r)
            r.deleteLater()
        self.set_modified()
        self.schedule_recalc()
        self._update_rect()

    def clear_sheet(self) -> None:
        for r in self.regions():
            self.removeItem(r)
            r.deleteLater()
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self.crosshair.show()
        self._update_rect()

    # -- document I/O ------------------------------------------------------------

    def to_document(self) -> SheetDocument:
        regs = [
            RegionData(r.kind, r.pos().x(), r.pos().y(), r.text())
            for r in self.ordered_regions() if not r.is_empty()
        ]
        return SheetDocument(regions=regs, significant=self.engine.significant)

    def load_document(self, doc: SheetDocument) -> None:
        self.clear_sheet()
        self.engine.significant = doc.significant
        for rd in doc.regions:
            self.add_region(rd.kind, QPointF(rd.x, rd.y), rd.text)
        self.recalculate()
        bottom = max((r.sceneBoundingRect().bottom() for r in self.regions()), default=GRID * 2)
        self.crosshair.setPos(GRID * 4, snap(bottom + 2 * GRID))
        self.set_modified(False)

    # -- calculation -------------------------------------------------------------

    def schedule_recalc(self) -> None:
        self._timer.start()

    def recalculate(self) -> None:
        self._timer.stop()
        maths = [r for r in self.ordered_regions() if isinstance(r, MathRegion)]
        results = self.engine.evaluate((id(r), r.source) for r in maths)
        errors = 0
        for r in maths:
            res = results.get(id(r))
            r.set_result(res)
            errors += bool(res and res.status == "error")
        self._update_rect()
        self.statusMessage.emit(f"{len(maths)} math regions" + (f" · {errors} with errors" if errors else ""))

    # -- events ------------------------------------------------------------------

    def _on_content_changed(self) -> None:
        self.set_modified()
        self.schedule_recalc()

    def _on_moved(self) -> None:
        self.set_modified()
        self.schedule_recalc()
        self._update_rect()

    def _on_editing_finished(self, region: Region, move_below: bool) -> None:
        if region.is_empty():
            self.removeItem(region)
            region.deleteLater()
        elif move_below:
            rect = region.sceneBoundingRect()
            self.crosshair.setPos(region.pos().x(), snap(rect.bottom() + 2 * GRID))
        self.crosshair.show()
        self.recalculate()

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else self._identity())
        region = self._region_of(item)
        if region is None and event.button() == Qt.MouseButton.LeftButton:
            editing = self.editing_region()
            if editing is not None:
                editing.finish_editing()
            self.clearSelection()
            self.setFocusItem(None)
            self.crosshair.setPos(snap(event.scenePos().x()), snap(event.scenePos().y()))
            self.crosshair.show()
            event.ignore()  # let the view start a rubber-band selection
            return
        if region is not None and not region.editing:
            editing = self.editing_region()
            if editing is not None and editing is not region:
                editing.finish_editing()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.editing_region() is not None:
            super().keyPressEvent(event)
            return
        key, text = event.key(), event.text()
        selected = [it for it in self.selectedItems() if isinstance(it, Region)]
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and selected:
            self.remove_regions(selected)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(selected) == 1:
            selected[0].start_editing()
            return
        step = {Qt.Key.Key_Left: (-GRID, 0), Qt.Key.Key_Right: (GRID, 0),
                Qt.Key.Key_Up: (0, -GRID), Qt.Key.Key_Down: (0, GRID)}.get(key)
        if step:
            if selected:
                for r in selected:
                    r.moveBy(*step)
            else:
                p = self.crosshair.pos() + QPointF(*step)
                self.crosshair.setPos(max(0.0, p.x()), max(0.0, p.y()))
            return
        if text and text.isprintable() and not event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier
        ):
            if text == '"':
                self.insert_region("text")
            else:
                region = self.insert_region("math")
                # Route the key through the region so ':' etc. are handled.
                region.editor.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#ffffff"))
        if self.printing:
            return
        # page edge
        painter.setPen(QPen(QColor("#c9d3e0"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(PAGE_WIDTH, rect.top()), QPointF(PAGE_WIDTH, rect.bottom()))
        # faint grid dots
        painter.setPen(QPen(QColor("#e3e8ef"), 1))
        step = GRID * 2
        left = int(rect.left()) - int(rect.left()) % step
        top = int(rect.top()) - int(rect.top()) % step
        points = [QPointF(x, y)
                  for x in range(left, int(rect.right()) + 1, step)
                  for y in range(top, int(rect.bottom()) + 1, step)]
        if len(points) < 40000:
            painter.drawPoints(points)

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _identity():
        from PySide6.QtGui import QTransform
        return QTransform()

    @staticmethod
    def _region_of(item) -> Region | None:
        while item is not None and not isinstance(item, Region):
            item = item.parentItem()
        return item

    def _update_rect(self) -> None:
        bottom = max((r.sceneBoundingRect().bottom() for r in self.regions()), default=0)
        right = max((r.sceneBoundingRect().right() for r in self.regions()), default=0)
        self.setSceneRect(QRectF(0, 0, max(PAGE_WIDTH + 40, right + 200), max(MIN_HEIGHT, bottom + 600)))


class WorksheetView(QGraphicsView):
    zoomChanged = Signal(float)

    def __init__(self, scene: Worksheet, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._zoom = 1.0

    def zoom(self) -> float:
        return self._zoom

    def set_zoom(self, factor: float) -> None:
        factor = max(0.4, min(3.0, factor))
        self.resetTransform()
        self.scale(factor, factor)
        self._zoom = factor
        self.zoomChanged.emit(factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_zoom(self._zoom * (1.1 if event.angleDelta().y() > 0 else 1 / 1.1))
            event.accept()
            return
        super().wheelEvent(event)
