"""The worksheet canvas: scene with regions, crosshair and live recalculation."""

from __future__ import annotations

import math
import time
from pathlib import Path

import shiboken6
from dataclasses import dataclass, field, replace

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPainterPath, QPen, QPolygonF, QWheelEvent
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

from ..document import RegionData, SheetDocument, WireData
from ..engine import Engine, dataio, wiring
from ..engine.pagination import PAGE_HEIGHT, PAGE_WIDTH, order_key
from .completion_popup import CompletionPopup
from .plotregion import PlotRegion, engine_source
from .regions import COLOR_ERROR, COLOR_FRAME, GRID, ComponentRegion, MathRegion, Region, TextRegion, snap

MIN_HEIGHT = 1100
RECALC_DELAY_MS = 200
HINT_TEXT = "Click to place the cursor, then start typing"


DRAG_THRESHOLD_PX = 4      # view pixels before a press becomes a drag (spec 023)
SHIFT_NUDGE_CELLS = 5      # Shift+arrow moves this many grid cells
EDGE_SCROLL_PX = 24
EDGE_SCROLL_STEP = 20      # view pixels scrolled per mouse event near an edge


@dataclass
class _MoveSession:
    """State of one press-drag-release move gesture (spec 023)."""
    primary: Region
    starts: dict          # Region -> start QPointF
    press_scene: QPointF
    press_screen: QPointF
    modified_before: bool
    dbl_pending: bool = False   # press was a double-click event: edit on release if not dragged
    started: bool = False
    cancelled: bool = False
    last_delta: tuple = field(default=(0.0, 0.0))


class Crosshair(QGraphicsItem):
    """Red insertion cross marking where the next region will be placed."""

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


class WireItem(QGraphicsPathItem):
    """A directed connector between one component's output port and another's input port
    (spec 009). Not a ``Region`` subclass -- it has no editable text and must not be picked up by
    ``Worksheet.regions()``'s ``isinstance(it, Region)`` filter or by reading-order sorting; the
    component-level dependency graph (``engine/wiring.py``), not canvas position, orders
    components once they are wired.

    Its path is recomputed from the two ports' *live* scene positions every time it repaints, so
    moving either component moves its drawn wires with it.
    """

    ARROW = 7.0

    def __init__(self, source: ComponentRegion, source_port: str,
                 dest: ComponentRegion, dest_port: str):
        super().__init__()
        self.source = source
        self.source_port = source_port
        self.dest = dest
        self.dest_port = dest_port
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPen(QPen(QColor(COLOR_FRAME), 1.5))

    def endpoints(self) -> tuple[QPointF, QPointF]:
        return (self.source.port_scene_pos("output", self.source_port),
                self.dest.port_scene_pos("input", self.dest_port))

    def sync(self) -> None:
        """Recompute this wire's path and colour from the two ports' current positions/state."""
        start, end = self.endpoints()
        path = QPainterPath(start)
        path.lineTo(end)
        self.setPath(path)
        is_error = bool(getattr(self.dest, "_has_error", False))
        self.setPen(QPen(QColor(COLOR_ERROR if is_error else COLOR_FRAME), 1.5))

    def paint(self, painter: QPainter, option, widget=None) -> None:
        self.sync()
        super().paint(painter, option, widget)
        start, end = self.endpoints()
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        back = QPointF(end.x() - ux * self.ARROW, end.y() - uy * self.ARROW)
        left = QPointF(back.x() - uy * self.ARROW * 0.5, back.y() + ux * self.ARROW * 0.5)
        right = QPointF(back.x() + uy * self.ARROW * 0.5, back.y() - ux * self.ARROW * 0.5)
        painter.setBrush(self.pen().color())
        painter.drawPolygon(QPolygonF([end, left, right]))


def heading_text(region: TextRegion) -> str | None:
    """Whitespace-collapsed plain text of the first paragraph when it is non-empty and entirely
    bold, else None (spec 027). Never raises on odd content."""
    try:
        block = region.editor.document().firstBlock()
        if not block.isValid():
            return None
        parts: list[str] = []
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and frag.text():
                if frag.charFormat().fontWeight() < QFont.Weight.DemiBold:
                    return None
                parts.append(frag.text())
            it += 1
        text = " ".join("".join(parts).split())
        return text or None
    except Exception:
        return None


class PageBreakItem(QGraphicsItem):
    """A manual page-break marker (spec 021, phase B): a full-width rule with a small "Page N"
    label. Not a ``Region`` (no text, never evaluated, not part of ``Worksheet.regions()``).
    Selectable and deletable but deliberately not movable: to change a break, delete it and insert
    another. Hidden while the scene is exporting (``Worksheet.printing``)."""

    BAND = 4.0

    def __init__(self, y: float):
        super().__init__()
        self.number = 2   # the page that starts at this marker; kept current by the Worksheet
        self.setZValue(-2)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPos(0.0, float(y))

    @property
    def y(self) -> float:
        return self.pos().y()

    def boundingRect(self) -> QRectF:
        return QRectF(0, -16, PAGE_WIDTH, 32)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(QRectF(0, -self.BAND, PAGE_WIDTH, 2 * self.BAND))
        return path

    def paint(self, painter: QPainter, option, widget=None) -> None:
        scene = self.scene()
        if scene is not None and getattr(scene, "printing", False):
            return
        color = QColor("#1f6feb") if self.isSelected() else QColor("#7a8da6")
        painter.setPen(QPen(color, 2 if self.isSelected() else 1.2))
        painter.drawLine(QPointF(0, 0), QPointF(PAGE_WIDTH, 0))
        painter.setPen(QPen(color, 1))
        painter.drawText(QPointF(PAGE_WIDTH - 60, -4), f"Page {self.number}")


class Worksheet(QGraphicsScene):
    modifiedChanged = Signal(bool)
    statusMessage = Signal(str)
    evaluationFinished = Signal(int, int, float)   # errors, total regions, elapsed ms
    datasetsChanged = Signal()   # dataset list edited (spec 028)
    outlineDirty = Signal()   # anything that can change the heading list (spec 027)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = Engine()
        self.datasets: list[dataio.Dataset] = []   # embedded imported data (spec 028)
        self.crosshair = Crosshair()
        self.addItem(self.crosshair)
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self._modified = False
        self._page_markers: list[PageBreakItem] = []   # page-break markers (spec 021)
        self._seq_counter = 0                 # creation sequence for exact-position ties
        self._discarded: list[Region] = []   # removed regions waiting for their single deletion
        self._wires: list[WireItem] = []     # component-to-component connections (spec 009)
        self._wire_drag: tuple[ComponentRegion, str] | None = None   # drag-to-connect source
        self._wire_drag_item: QGraphicsLineItem | None = None
        self._move: _MoveSession | None = None   # active drag-to-move gesture (spec 023)
        self._pressing = False
        self._scrolling = False
        self._moving = False                      # suppress per-region _on_moved side effects
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
        """Regions in evaluation order: page, then left to right, then top to bottom; exact
        position ties are broken by creation sequence (spec 021)."""
        breaks = self.page_break_ys()
        return sorted(self.regions(), key=lambda r: (
            order_key(r.pos().x(), r.pos().y(), breaks), getattr(r, "_seq", 0)))

    def page_break_ys(self) -> list[float]:
        """The document's page-break y-coordinates, ascending."""
        return sorted(m.y for m in self._page_markers)

    def page_markers(self) -> list[PageBreakItem]:
        return sorted(self._page_markers, key=lambda m: m.y)

    def _renumber_markers(self) -> None:
        for i, m in enumerate(self.page_markers()):
            m.number = i + 2
            m.update()

    def _add_marker(self, y: float) -> PageBreakItem:
        marker = PageBreakItem(y)
        self.addItem(marker)
        self._page_markers.append(marker)
        self._renumber_markers()
        self.outlineDirty.emit()
        return marker

    def _clear_markers(self) -> None:
        for m in self._page_markers:
            if m.scene() is self:
                self.removeItem(m)
        self._page_markers = []
        self.outlineDirty.emit()

    def headings(self) -> list[tuple[Region, int, str]]:
        """Heading text regions as (region, 0-based page index, plain first line), in reading
        order: page, then top to bottom, then left to right (spec 027). Read-only."""
        breaks = self.page_break_ys()
        found = []
        for r in self.regions():
            if not isinstance(r, TextRegion):
                continue
            text = heading_text(r)
            if text is None:
                continue
            y = r.pos().y()
            page = sum(1 for b in breaks if b <= y)
            found.append(((page, y, r.pos().x(), getattr(r, "_seq", 0)), (r, page, text)))
        found.sort(key=lambda t: t[0])
        return [t[1] for t in found]

    def reveal_region(self, region: Region) -> bool:
        """Select ``region`` and scroll so it sits near the top of the view (zoom unchanged,
        focus untouched). False for a region no longer in the sheet."""
        if not shiboken6.isValid(region) or region.scene() is not self:
            return False
        self.clearSelection()
        region.setSelected(True)
        rect = region.sceneBoundingRect()
        for view in self.views():
            view.ensureVisible(rect, 20, 20)
            top = view.mapFromScene(rect.topLeft()).y()
            target = int(view.viewport().height() * 0.1)
            vbar = view.verticalScrollBar()
            vbar.setValue(vbar.value() + top - target)
        return True

    def remove_page_breaks(self, markers: list[PageBreakItem]) -> None:
        """Delete markers only; regions do not move back (spec 021)."""
        removed = False
        for m in markers:
            if m in self._page_markers:
                self._page_markers.remove(m)
                removed = True
            if m.scene() is self:
                self.removeItem(m)
        if removed:
            self._renumber_markers()
            self.outlineDirty.emit()
            self.set_modified()
            self.recalculate()

    def insert_page_break(self, y: float | None = None) -> bool:
        """Insert a page break at ``y`` (default: the crosshair) with word-processor reflow
        (spec 021): content at or below ``y`` moves down so it starts at the top of the next A4
        page. One method so a future undo can wrap it as a single step. Returns False if refused."""
        current = self.editing_region()
        if current is not None:
            current.finish_editing()
        if y is None:
            y = self.crosshair.pos().y()
        y = float(snap(y))
        breaks = self.page_break_ys()
        top = max((b for b in breaks if b <= y), default=0.0)
        if y == top:
            self.statusMessage.emit("This position is already the top of a page.")
            return False
        bottom_edge = top + PAGE_HEIGHT * math.ceil((y - top) / PAGE_HEIGHT)
        delta = bottom_edge - y
        moved = 0
        if delta:
            for r in self.regions():
                if r.pos().y() >= y:
                    r.setPos(r.pos().x(), r.pos().y() + delta)
                    moved += 1
            for m in self._page_markers:
                if m.y >= y:
                    m.setPos(0.0, m.y + delta)
        self._add_marker(bottom_edge)
        self.crosshair.setPos(self.crosshair.pos().x(), bottom_edge)
        self.set_modified()
        self._update_rect()
        self.recalculate()
        self.statusMessage.emit(
            f"Page break inserted; moved {moved} regions down by {int(delta)} units.")
        return True

    def fold_guide_ys(self, limit: float) -> list[float]:
        """Y of the dashed fold guides (every PAGE_HEIGHT from each page top, strictly inside its
        page) up to ``limit``."""
        tops = [0.0] + self.page_break_ys()
        out: list[float] = []
        for i, t in enumerate(tops):
            end = tops[i + 1] if i + 1 < len(tops) else limit
            y = t + PAGE_HEIGHT
            while y < end and y <= limit:
                out.append(y)
                y += PAGE_HEIGHT
        return out

    def _assign_seq(self, region: Region) -> None:
        self._seq_counter += 1
        region._seq = self._seq_counter

    def editing_region(self) -> Region | None:
        for r in self.regions():
            if r.editing:
                return r
        return None

    # -- region management -----------------------------------------------------

    def add_region(self, kind: str, pos: QPointF, text: str = "",
                   size: tuple[float, float] | None = None) -> Region:
        region: Region
        if kind == "math":
            region = MathRegion(text)
        elif kind == "plot":
            region = PlotRegion(text, *(size or (None, None)))
        else:
            region = TextRegion(text)
        self.addItem(region)
        self._assign_seq(region)
        region.setPos(QPointF(snap(pos.x()), snap(pos.y())))
        region.contentChanged.connect(self._on_content_changed)
        region.editingFinished.connect(self._on_editing_finished)
        region.moved.connect(self._on_moved)
        self._update_rect()
        self.outlineDirty.emit()
        return region

    def insert_region(self, kind: str, initial_text: str = "") -> Region:
        """Create a region at the crosshair and start editing it (a plot opens its dialog
        instead, spec 006)."""
        current = self.editing_region()
        if current is not None:
            current.finish_editing()
        if kind == "plot":
            region = self.add_region(kind, self.crosshair.pos(), "")
            self.clearSelection()
            if self.views():
                # A region created via a menu action (e.g. the native macOS menu bar) leaves
                # keyboard focus on the menu, not the view: the item then *thinks* it has focus
                # but never receives real key events. Reclaim it before opening the dialog.
                self.views()[0].setFocus(Qt.FocusReason.OtherFocusReason)
            self.crosshair.hide()
            self.set_modified()
            self._open_plot_dialog(region)
            return region
        region = self.add_region(kind, self.crosshair.pos())
        self.clearSelection()
        if self.views():
            # See the comment above: reclaim real keyboard focus from a menu action.
            self.views()[0].setFocus(Qt.FocusReason.OtherFocusReason)
        region.start_editing()
        if initial_text:
            region.editor.textCursor().insertText(initial_text)
            region.editor.setTextCursor(region.editor.textCursor())
        self.crosshair.hide()
        self.set_modified()
        return region

    def _open_plot_dialog(self, region: PlotRegion) -> None:
        from .plotdialog import PlotDialog

        parent = self.views()[0] if self.views() else None
        dialog = PlotDialog(region, self, parent=parent)
        dialog.exec()

    def insert_plot_at(self, pos: QPointF) -> Region:
        """Create a plot region at ``pos`` (snapped) and open its dialog (spec 006)."""
        self.crosshair.setPos(snap(pos.x()), snap(pos.y()))
        return self.insert_region("plot")

    def insert_matrix_at(self, pos: QPointF) -> Region | None:
        """Open the matrix dialog's Size step at ``pos`` (snapped) for a brand-new insertion
        (spec 008). Unlike a plot, nothing is created on the canvas until OK: Cancel at either
        step of the dialog leaves the canvas exactly as before."""
        from .matrixdialog import MatrixDialog

        current = self.editing_region()
        if current is not None:
            current.finish_editing()
        if self.views():
            # See insert_region's comment: reclaim real keyboard focus from a menu action.
            self.views()[0].setFocus(Qt.FocusReason.OtherFocusReason)
        parent = self.views()[0] if self.views() else None
        dialog = MatrixDialog(self, region=None, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.compiled_text()
            self.crosshair.setPos(snap(pos.x()), snap(pos.y()))
            return self.insert_region("math", initial_text=text)
        return None

    def _open_matrix_dialog(self, region: MathRegion) -> None:
        from .matrixdialog import MatrixDialog

        parent = self.views()[0] if self.views() else None
        dialog = MatrixDialog(self, region=region, parent=parent)
        dialog.exec()

    # -- components and wires (spec 009) ---------------------------------------------------

    def component_regions(self) -> list[ComponentRegion]:
        return [it for it in self.items() if isinstance(it, ComponentRegion)]

    def _unique_component_name(self, name: str) -> str:
        """Appends '' (2)'', '' (3)'', ... when ``name`` is already used by a live component --
        never a hard failure over a name collision (spec 009's edge case; reused both for a
        freshly created component and for one restored from a hand-edited/corrupted file)."""
        existing = {c.component_name for c in self.component_regions()}
        if name not in existing:
            return name
        i = 2
        while f"{name} ({i})" in existing:
            i += 1
        return f"{name} ({i})"

    def add_component_region(self, name: str, kind: str, config: dict[str, str],
                              pos: QPointF) -> ComponentRegion:
        region = ComponentRegion(self._unique_component_name(name or "Comp"), kind, config)
        self.addItem(region)
        self._assign_seq(region)
        region.setPos(QPointF(snap(pos.x()), snap(pos.y())))
        region.moved.connect(self._on_moved)
        self.set_modified()
        self._update_rect()
        return region

    def insert_component_at(self, pos: QPointF) -> ComponentRegion | None:
        """Open the "Add Component" dialog for a brand-new insertion at ``pos`` (snapped).
        Nothing is created on the canvas until OK; Cancel leaves the canvas exactly as before."""
        from .componentdialog import AddComponentDialog

        current = self.editing_region()
        if current is not None:
            current.finish_editing()
        if self.views():
            # See insert_region's comment: reclaim real keyboard focus from a menu action.
            self.views()[0].setFocus(Qt.FocusReason.OtherFocusReason)
        parent = self.views()[0] if self.views() else None
        dialog = AddComponentDialog(parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, kind, config = dialog.result_fields()
            region = self.add_component_region(name, kind, config, pos)
            self.crosshair.setPos(snap(pos.x()), snap(pos.y()))
            self.schedule_recalc()
            return region
        return None

    def try_connect(self, source: tuple[ComponentRegion, str],
                     dest: tuple[ComponentRegion, str]) -> str | None:
        """Create a wire from the output port ``source`` to the input port ``dest``, or report
        why not. Returns ``None`` on success, an error message on rejection -- the one shared
        place the one-connection-per-input and no-cycle rules are enforced, for both the
        drag-to-connect gesture and the "Connect…" dialog."""
        src_region, src_port = source
        dst_region, dst_port = dest
        if src_port not in src_region._outputs or dst_port not in dst_region._inputs:
            return "A wire must run from an output port to an input port."
        for w in self._wires:
            if w.dest is dst_region and w.dest_port == dst_port:
                return (f"Input '{dst_port}' on {dst_region.component_name} is already "
                        "connected — disconnect it first.")
        names = [c.component_name for c in self.component_regions()]
        edges = {(w.source.component_name, w.dest.component_name) for w in self._wires}
        candidate = (src_region.component_name, dst_region.component_name)
        if wiring.would_create_cycle(names, edges, candidate):
            return "This connection would create a circular dependency."
        wire = WireItem(src_region, src_port, dst_region, dst_port)
        self.addItem(wire)
        self._wires.append(wire)
        self._sync_all_wires()
        self.set_modified()
        self.schedule_recalc()
        return None

    def _remove_wires(self, wires: list[WireItem]) -> None:
        for w in wires:
            if w in self._wires:
                self._wires.remove(w)
            if w.scene() is self:
                self.removeItem(w)

    def _sync_all_wires(self) -> None:
        for w in self._wires:
            w.prepareGeometryChange()
            w.sync()
            w.update()

    def _open_connect_dialog(self, region: ComponentRegion, side: str, port: str) -> None:
        from .componentdialog import ConnectDialog

        candidates = self._connect_candidates(region, side, port)
        parent = self.views()[0] if self.views() else None
        dialog = ConnectDialog(region, side, port, candidates, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            other = dialog.chosen()
            if other is not None:
                other_region, other_port = other
                if side == "output":
                    msg = self.try_connect((region, port), (other_region, other_port))
                else:
                    msg = self.try_connect((other_region, other_port), (region, port))
                if msg:
                    self.statusMessage.emit(msg)

    def _connect_candidates(self, region: ComponentRegion, side: str,
                             port: str) -> list[tuple[ComponentRegion, str]]:
        opposite = "input" if side == "output" else "output"
        out: list[tuple[ComponentRegion, str]] = []
        for c in self.component_regions():
            if c is region:
                continue
            ports = c._inputs if opposite == "input" else c._outputs
            out.extend((c, p) for p in ports)
        return out

    # -- drag-to-connect gesture (spec 009) --------------------------------------------------

    def _begin_wire_drag(self, region: ComponentRegion, port: str, scene_pos: QPointF) -> None:
        self._wire_drag = (region, port)
        line = QGraphicsLineItem()
        line.setPen(QPen(QColor(COLOR_FRAME), 1.5, Qt.PenStyle.DashLine))
        line.setZValue(2000)
        start = region.port_scene_pos("output", port)
        line.setLine(start.x(), start.y(), scene_pos.x(), scene_pos.y())
        self.addItem(line)
        self._wire_drag_item = line

    def _update_wire_drag(self, scene_pos: QPointF) -> None:
        if self._wire_drag is None or self._wire_drag_item is None:
            return
        region, port = self._wire_drag
        start = region.port_scene_pos("output", port)
        self._wire_drag_item.setLine(start.x(), start.y(), scene_pos.x(), scene_pos.y())

    def _finish_wire_drag(self, scene_pos: QPointF) -> None:
        if self._wire_drag is None:
            return
        region, port = self._wire_drag
        if self._wire_drag_item is not None and self._wire_drag_item.scene() is self:
            self.removeItem(self._wire_drag_item)
        self._wire_drag_item = None
        self._wire_drag = None
        item = self.itemAt(scene_pos, self.views()[0].transform() if self.views() else self._identity())
        target = self._region_of(item)
        if isinstance(target, ComponentRegion):
            local = target.mapFromScene(scene_pos)
            hit = target.port_at(local)
            if hit is not None and hit[0] == "input":
                msg = self.try_connect((region, port), (target, hit[1]))
                if msg:
                    self.statusMessage.emit(msg)

    def remove_regions(self, regions: list[Region]) -> None:
        self._drop_move()
        if not regions:
            return
        for r in regions:
            if isinstance(r, ComponentRegion):
                # Deleting a component deletes its wires (spec 009).
                attached = [w for w in self._wires if w.source is r or w.dest is r]
                self._remove_wires(attached)
            self._discard(r)
        self.set_modified()
        self.schedule_recalc()
        self._update_rect()

    def _discard(self, region: Region) -> None:
        """Take a region out of the scene and destroy it exactly once, at a safe moment.

        Selection, focus and editing are cleared first, the signals are cut, and the item is
        hidden and removed. The Python wrapper then owns it (no deleteLater, so there is a single
        owner) and the C++ object is deleted from a zero-delay timer, never while the view may
        still be painting or while this region's own signal is being emitted.
        """
        if region.scene() is not self:
            return
        region.abort_editing()
        for signal in (region.contentChanged, region.editingFinished, region.moved):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass
        region.setSelected(False)
        focus = self.focusItem()
        if focus is not None and (focus is region or region.isAncestorOf(focus)):
            focus.clearFocus()
        region.hide()
        self.removeItem(region)
        self._discarded.append(region)
        QTimer.singleShot(0, self._destroy_discarded)
        self.outlineDirty.emit()

    def _destroy_discarded(self) -> None:
        discarded, self._discarded = self._discarded, []
        for region in discarded:
            if shiboken6.isValid(region):
                shiboken6.delete(region)

    def clear_sheet(self) -> None:
        self._drop_move()
        for w in list(self._wires):
            if w.scene() is self:
                self.removeItem(w)
        self._wires = []
        self._clear_markers()
        for r in self.regions():
            self._discard(r)
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self.crosshair.show()
        if self.datasets:
            self.datasets = []
            self.datasetsChanged.emit()
        self._update_rect()

    # -- datasets (spec 028) -----------------------------------------------------

    def dataset(self, name: str) -> dataio.Dataset | None:
        return next((d for d in self.datasets if d.name == name), None)

    def _datasets_edited(self) -> None:
        self.datasetsChanged.emit()
        self.set_modified()
        self.recalculate()

    def add_dataset(self, dataset: dataio.Dataset) -> None:
        """Add an imported dataset (name validated against the existing ones)."""
        dataio.validate_dataset_name(dataset.name, [d.name for d in self.datasets])
        dataio.check_variable_conflicts(dataset, self.datasets)
        self.datasets.append(dataset)
        self._datasets_edited()

    def remove_dataset(self, name: str) -> None:
        self.datasets = [d for d in self.datasets if d.name != name]
        self._datasets_edited()

    def rename_dataset(self, old: str, new: str) -> None:
        """Rename; formulas using the old variable names are not rewritten."""
        target = self.dataset(old)
        if target is None or old == new:
            return
        dataio.validate_dataset_name(new, [d.name for d in self.datasets if d.name != old])
        renamed = replace(target, name=new)
        dataio.check_variable_conflicts(renamed, self.datasets)
        target.name = new
        self._datasets_edited()

    def refresh_dataset(self, name: str, base_dir: str | Path | None = None) -> list[str]:
        """Re-read the stored source with the stored options and units. Returns messages
        (warnings and a columns-changed note). On failure raises DataImportError and leaves the
        dataset unchanged."""
        old = self.dataset(name)
        if old is None:
            raise dataio.DataImportError(f"There is no dataset named '{name}'.")
        if not old.source:
            raise dataio.DataImportError("This dataset has no source file to refresh from.")
        path = Path(old.source)
        if not path.is_absolute() and base_dir is not None:
            path = Path(base_dir) / path
        units = {c.name: c.unit for c in old.columns if c.kind == "number"}
        new = dataio.read_table(path, old.options, name=name, units=units)
        new.source = old.source
        messages = list(new.warnings)
        before = {c.name for c in old.columns}
        after = {c.name for c in new.columns}
        if before != after:
            parts = []
            if before - after:
                parts.append("removed " + ", ".join(f"'{n}'" for n in sorted(before - after)))
            if after - before:
                parts.append("added " + ", ".join(f"'{n}'" for n in sorted(after - before)))
            messages.append("Columns changed: " + "; ".join(parts) + ".")
        self.datasets[self.datasets.index(old)] = new
        self._datasets_edited()
        return messages

    # -- document I/O ------------------------------------------------------------

    def to_document(self) -> SheetDocument:
        regs = []
        for r in self.ordered_regions():
            if isinstance(r, ComponentRegion):
                regs.append(RegionData("component", r.pos().x(), r.pos().y(), "",
                                        component_name=r.component_name,
                                        component_kind=r.component_kind,
                                        config=dict(r.config)))
                continue
            if r.is_empty():
                continue
            regs.append(RegionData(r.kind, r.pos().x(), r.pos().y(), r.text(),
                                    *((r.size_w, r.size_h) if isinstance(r, PlotRegion) else (None, None))))
        wires = [WireData(w.source.component_name, w.source_port, w.dest.component_name, w.dest_port)
                 for w in self._wires]
        return SheetDocument(regions=regs, significant=self.engine.significant, wires=wires,
                             page_breaks=self.page_break_ys(), datasets=list(self.datasets))

    def load_document(self, doc: SheetDocument) -> None:
        self._drop_move()
        self.clear_sheet()
        for b in sorted(doc.page_breaks):
            self._add_marker(b)
        self.engine.significant = doc.significant
        self.datasets = list(doc.datasets)
        self.datasetsChanged.emit()
        by_name: dict[str, ComponentRegion] = {}
        for rd in doc.regions:
            if rd.kind == "component":
                region = self.add_component_region(rd.component_name, rd.component_kind,
                                                     rd.config, QPointF(rd.x, rd.y))
                by_name[region.component_name] = region
            else:
                self.add_region(rd.kind, QPointF(rd.x, rd.y), rd.text,
                                (rd.w, rd.h) if rd.kind == "plot" else None)
        for wd in doc.wires:
            src, dst = by_name.get(wd.from_component), by_name.get(wd.to_component)
            if src is None or dst is None:
                continue   # names the component no longer exists: dropped silently (edge case)
            # A recognised kind's port list is trusted (drop a genuinely stale port reference);
            # an *unrecognised* kind's own ports are left unvalidated so its wires still survive,
            # per spec 009's edge case ("the box, its name, its configuration and its wires all
            # survive" for an unrecognised component_kind).
            if wiring.known_kind(src.component_kind) and wd.from_port not in src._outputs:
                continue
            if wiring.known_kind(dst.component_kind) and wd.to_port not in dst._inputs:
                continue
            wire = WireItem(src, wd.from_port, dst, wd.to_port)
            self.addItem(wire)
            self._wires.append(wire)
        self._sync_all_wires()
        self.recalculate()
        bottom = max((r.sceneBoundingRect().bottom() for r in self.regions()), default=GRID * 2)
        self.crosshair.setPos(GRID * 4, snap(bottom + 2 * GRID))
        self.set_modified(False)

    # -- calculation -------------------------------------------------------------

    def schedule_recalc(self) -> None:
        self._timer.start()

    def recalculate(self) -> None:
        self._timer.stop()
        start = time.perf_counter()
        evaluated = [r for r in self.ordered_regions() if isinstance(r, (MathRegion, PlotRegion))]
        results = self.engine.evaluate(
            ((id(r), engine_source(r.source) if isinstance(r, PlotRegion) else r.source)
             for r in evaluated), datasets=self.datasets)
        errors = 0
        for r in evaluated:
            res = results.get(id(r))
            r.set_result(res)
            errors += bool(res and res.status == "error")

        # Additive, independent step (spec 009): a no-op (empty specs/wires in, empty dict out)
        # on a sheet with no ComponentRegions, which is what keeps acceptance criterion 1 true.
        components = self.component_regions()
        specs = [wiring.ComponentSpec(c.component_name, c.component_kind, dict(c.config),
                                       c.pos().x(), c.pos().y()) for c in components]
        wire_specs = [wiring.WireSpec(w.source.component_name, w.source_port,
                                       w.dest.component_name, w.dest_port) for w in self._wires]
        comp_results = wiring.evaluate(specs, wire_specs, self.engine, page_breaks=self.page_break_ys())
        for c in components:
            res = comp_results.get(c.component_name)
            c.set_result(res)
            errors += bool(res and res.status == "error")
        self._sync_all_wires()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._update_rect()
        maths = sum(isinstance(r, MathRegion) for r in evaluated)
        plots = len(evaluated) - maths
        self.statusMessage.emit(f"{maths} math regions" + (f" · {plots} plots" if plots else "")
                                + (f" · {errors} with errors" if errors else ""))
        self.evaluationFinished.emit(errors, len(evaluated) + len(components), elapsed_ms)

    # -- events ------------------------------------------------------------------

    def _on_content_changed(self) -> None:
        self.outlineDirty.emit()
        self.set_modified()
        self.schedule_recalc()

    def _on_moved(self) -> None:
        if self._moving:
            return   # batched: the mover calls _after_move once per step (spec 023)
        self.outlineDirty.emit()
        self.set_modified()
        self.schedule_recalc()
        self._update_rect()
        self._sync_all_wires()   # a moved component's wires track it live (spec 009)

    def _on_editing_finished(self, region: Region, move_below: bool) -> None:
        if region.is_empty():
            self._discard(region)
        else:
            if isinstance(region, PlotRegion):
                region.has_baseline = True
            if move_below:
                rect = region.sceneBoundingRect()
                self.crosshair.setPos(region.pos().x(), snap(rect.bottom() + 2 * GRID))
        self.crosshair.show()
        self.recalculate()

    def contextMenuEvent(self, event) -> None:
        if self.editing_region() is not None:
            super().contextMenuEvent(event)
            return
        pos = event.scenePos()
        item = self.itemAt(pos, self.views()[0].transform() if self.views() else self._identity())
        region = self._region_of(item)
        port_hit = None
        if isinstance(region, ComponentRegion):
            port_hit = region.port_at(region.mapFromScene(pos))
        # "Connect…" target (spec 009 + D1 fix): prefer the exact port terminal under the
        # cursor; otherwise, for any right-clicked ComponentRegion that has at least one port,
        # fall back to its first output port (or first input port, if it has no outputs) so the
        # dialog is reachable without needing a pixel-precise hit on the tiny terminal --
        # mirroring how "Edit as grid..." (spec 008) is offered for a whole MathRegion rather
        # than requiring a pixel-precise hit.
        connect_target = port_hit
        if connect_target is None and isinstance(region, ComponentRegion):
            if region._outputs:
                connect_target = ("output", region._outputs[0])
            elif region._inputs:
                connect_target = ("input", region._inputs[0])
        menu = QMenu()
        plot_here = menu.addAction("Plot here")
        # "Matrix here" (spec 008): only offered when the right-click did not land on an existing
        # region, matching this entry's own trigger rule (next to the existing "Plot here" above).
        matrix_here = menu.addAction("Matrix here") if region is None else None
        edit_as_grid = None
        if isinstance(region, MathRegion) and not region.editing:
            from .matrixdialog import decompose_matrix_text

            if decompose_matrix_text(region.source) is not None:
                edit_as_grid = menu.addAction("Edit as grid...")
        # "Connect…" (spec 009): offered whenever the right-click lands on a port terminal, or
        # anywhere else on a ComponentRegion that has a port to default to (D1 fix) -- the
        # generic pick-from-a-list dialog that is the primary, always-available way to create a
        # wire without needing pixel-perfect port targeting.
        connect_action = menu.addAction("Connect…") if connect_target is not None else None
        chosen = menu.exec(event.screenPos())
        if chosen is plot_here:
            self.insert_plot_at(pos)
        elif matrix_here is not None and chosen is matrix_here:
            self.insert_matrix_at(pos)
        elif edit_as_grid is not None and chosen is edit_as_grid:
            self._open_matrix_dialog(region)
        elif connect_action is not None and chosen is connect_action:
            self._open_connect_dialog(region, connect_target[0], connect_target[1])
        event.accept()

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else self._identity())
        if isinstance(item, CompletionPopup):
            item.pick_at(item.mapFromScene(event.scenePos()))   # spec 024: pick a row
            event.accept()
            return
        region = self._region_of(item)
        if (event.button() == Qt.MouseButton.LeftButton and isinstance(region, ComponentRegion)
                and not region.editing):
            hit = region.port_at(region.mapFromScene(event.scenePos()))
            if hit is not None and hit[0] == "output":
                # Drag-to-connect (spec 009): press on an output port terminal starts a wire
                # drag instead of the usual move/select interaction.
                self._begin_wire_drag(region, hit[1], event.scenePos())
                event.accept()
                return
        if isinstance(item, PageBreakItem) and event.button() == Qt.MouseButton.LeftButton:
            editing = self.editing_region()
            if editing is not None:
                editing.finish_editing()
            self.clearSelection()
            item.setSelected(True)
            event.accept()
            return
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
        if region is not None and event.button() == Qt.MouseButton.LeftButton:
            self._press_on_region(region, event)
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """A press arriving as a double-click event (click, then quickly press-and-drag) must
        still be able to start a move; the "edit" action is deferred to release (spec 023)."""
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else self._identity())
        region = self._region_of(item)
        if (region is not None and not region.editing and event.button() == Qt.MouseButton.LeftButton
                and self.editing_region() is None):
            self._press_on_region(region, event, dbl=True)
            return
        super().mouseDoubleClickEvent(event)

    # -- drag to move (spec 023) --------------------------------------------------

    def move_active(self) -> bool:
        return self._move is not None or self._pressing

    def _press_on_region(self, region: Region, event, dbl: bool = False) -> None:
        editing = self.editing_region()
        if editing is not None and editing is not region:
            editing.finish_editing()
        local = region.mapFromScene(event.scenePos())
        if region.editing:
            if not region.in_grip(local):
                super().mousePressEvent(event)   # caret / text selection, never a move
                return
            # Frame ring of an editing region: move grip; keep editing and focus untouched.
            if not region.isSelected():
                self.clearSelection()
                region.setSelected(True)
            self._begin_move(region, event, dbl)
            event.accept()
            return
        self._pressing = True   # a double-click-typed press must not reach on_double_click
        try:
            super().mousePressEvent(event)
        finally:
            self._pressing = False
        if getattr(region, "_resizing", None) is not None or not region.isSelected():
            return   # plot resize handle (or a toggled-off selection) wins over moving
        self._begin_move(region, event, dbl)

    def _begin_move(self, region: Region, event, dbl: bool) -> None:
        members = [it for it in self.selectedItems() if isinstance(it, Region)]
        if region not in members:
            members.append(region)
        self._move = _MoveSession(
            primary=region, starts={r: QPointF(r.pos()) for r in members},
            press_scene=QPointF(event.scenePos()), press_screen=QPointF(event.screenPos()),
            modified_before=self._modified, dbl_pending=dbl)

    def _drop_move(self) -> None:
        if self._move is not None:
            self._move = None
            self._set_drag_cursor(False)

    def _set_drag_cursor(self, on: bool) -> None:
        for v in self.views():
            if on:
                v.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                v.viewport().unsetCursor()

    def clamped_delta(self, starts: list[QPointF], dx: float, dy: float) -> tuple[float, float]:
        """Reduce a displacement so no member ends at x < 0 or y < 0 (the group clamps as a whole)."""
        if starts:
            dx = max(dx, -min(p.x() for p in starts))
            dy = max(dy, -min(p.y() for p in starts))
        return dx, dy

    def _drag_step(self, event) -> None:
        m = self._move
        if m is None or m.cancelled:
            return
        if not m.started:
            d = QPointF(event.screenPos()) - m.press_screen
            if math.hypot(d.x(), d.y()) < DRAG_THRESHOLD_PX:
                return
            m.started = True
            self._set_drag_cursor(True)
        start = m.starts[m.primary]
        delta = event.scenePos() - m.press_scene
        dx = snap(start.x() + delta.x()) - start.x()
        dy = snap(start.y() + delta.y()) - start.y()
        dx, dy = self.clamped_delta(list(m.starts.values()), dx, dy)
        changed = False
        self._moving = True
        try:
            for r, p in m.starts.items():
                target = QPointF(p.x() + dx, p.y() + dy)
                if r.pos() != target:
                    r.setPos(target)
                    changed = True
        finally:
            self._moving = False
        m.last_delta = (dx, dy)
        if changed:
            self._after_move()
        self._keep_visible(event)

    def _keep_visible(self, event) -> None:
        """Scroll the view a little each step while the pointer is within EDGE_SCROLL_PX of (or
        beyond) a viewport edge, so the dragged region stays reachable. Bounded per event."""
        if EDGE_SCROLL_STEP <= 0:
            return
        self._scrolling = True   # the view replays the last mouse move after a scroll; ignore it
        try:
            self._scroll_views(event)
        finally:
            self._scrolling = False

    def _scroll_views(self, event) -> None:
        for v in self.views():
            p = v.mapFromScene(event.scenePos())
            r = v.viewport().rect()
            hbar, vbar = v.horizontalScrollBar(), v.verticalScrollBar()
            if p.x() < EDGE_SCROLL_PX:
                hbar.setValue(hbar.value() - EDGE_SCROLL_STEP)
            elif p.x() > r.width() - EDGE_SCROLL_PX:
                hbar.setValue(hbar.value() + EDGE_SCROLL_STEP)
            if p.y() < EDGE_SCROLL_PX:
                vbar.setValue(vbar.value() - EDGE_SCROLL_STEP)
            elif p.y() > r.height() - EDGE_SCROLL_PX:
                vbar.setValue(vbar.value() + EDGE_SCROLL_STEP)

    def _after_move(self) -> None:
        """Side effects of region movement, batched: once per mouse step or key press."""
        self.outlineDirty.emit()
        self.schedule_recalc()
        self._update_rect()
        self._sync_all_wires()

    def _finish_move(self, event) -> None:
        m, self._move = self._move, None
        self._set_drag_cursor(False)
        if m is None or m.cancelled:
            return
        if not m.started:
            if m.dbl_pending and not m.primary.editing and m.primary.scene() is self:
                m.primary.on_double_click(event.scenePos())
            return
        moves = [(r, p, QPointF(r.pos())) for r, p in m.starts.items() if r.pos() != p]
        if moves:
            self.move_regions(moves)
        else:
            self.recalculate()
        pos = m.primary.mapFromScene(event.scenePos())
        if m.primary.scene() is self:
            m.primary.update_cursor(pos)

    def cancel_move(self) -> bool:
        """Esc during a drag: put everything back. Returns True if a drag was in progress."""
        m = self._move
        if m is None or m.cancelled or not m.started:
            return False
        m.cancelled = True
        self._moving = True
        try:
            for r, p in m.starts.items():
                r.setPos(p)
        finally:
            self._moving = False
        self._set_drag_cursor(False)
        self._update_rect()
        self.set_modified(m.modified_before)
        self.recalculate()
        return True

    def move_regions(self, moves: list, immediate: bool = True) -> None:
        """Commit a move: ``moves`` is a list of (region, old_pos, new_pos). The single entry
        point for completed drags and nudges, so a future undo can wrap one call as one step."""
        self._moving = True
        try:
            for r, _old, new in moves:
                if r.pos() != new:
                    r.setPos(new)
        finally:
            self._moving = False
        if any(old != new for _r, old, new in moves):
            self.set_modified()
        self._update_rect()
        self._sync_all_wires()
        if immediate:
            self.recalculate()
        else:
            self.schedule_recalc()

    def nudge(self, selected: list[Region], dx: float, dy: float) -> None:
        starts = [r.pos() for r in selected]
        if any(p.x() + dx < 0 for p in starts):
            dx = 0.0
        if any(p.y() + dy < 0 for p in starts):
            dy = 0.0
        if dx == 0.0 and dy == 0.0:
            return
        self.move_regions([(r, QPointF(r.pos()), QPointF(r.pos().x() + dx, r.pos().y() + dy))
                           for r in selected], immediate=False)

    def focusOutEvent(self, event) -> None:
        self.cancel_move()   # losing the window focus mid-drag counts as Esc
        super().focusOutEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._wire_drag is not None:
            self._update_wire_drag(event.scenePos())
            event.accept()
            return
        if self._move is not None:
            if not self._scrolling:
                self._drag_step(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._wire_drag is not None:
            self._finish_wire_drag(event.scenePos())
            event.accept()
            return
        if self._move is not None and event.button() == Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)   # lets the scene drop its mouse grabber
            self._finish_move(event)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.cancel_move():
            event.accept()
            return
        if self.editing_region() is not None:
            super().keyPressEvent(event)
            return
        key, text = event.key(), event.text()
        selected = [it for it in self.selectedItems() if isinstance(it, Region)]
        selected_wires = [it for it in self.selectedItems() if isinstance(it, WireItem)]
        selected_breaks = [it for it in self.selectedItems() if isinstance(it, PageBreakItem)]
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and (
                selected or selected_wires or selected_breaks):
            if selected_breaks:
                self.remove_page_breaks(selected_breaks)
            if selected:
                self.remove_regions(selected)
            if selected_wires:
                # Deleting a wire (spec 009) removes only that one connection; the two
                # components themselves are untouched.
                self._remove_wires(selected_wires)
                self.set_modified()
                self.schedule_recalc()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(selected) == 1:
            selected[0].start_editing()
            return
        step = {Qt.Key.Key_Left: (-GRID, 0), Qt.Key.Key_Right: (GRID, 0),
                Qt.Key.Key_Up: (0, -GRID), Qt.Key.Key_Down: (0, GRID)}.get(key)
        if step:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                step = (step[0] * SHIFT_NUDGE_CELLS, step[1] * SHIFT_NUDGE_CELLS)
            if selected:
                self.nudge(selected, *step)
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

    def should_show_hint(self) -> bool:
        """True on a brand-new or emptied-back-to-zero worksheet (spec 007's first-run hint)."""
        return len(self.regions()) == 0

    def _paint_empty_hint(self, painter: QPainter) -> None:
        pos = self.crosshair.pos()
        painter.setPen(QPen(QColor("#9aa6b5"), 1))
        painter.drawText(QPointF(pos.x() + GRID * 2, pos.y() + GRID // 2), HINT_TEXT)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#ffffff"))
        if self.printing:
            return
        # first-run hint: a passive background label, never a region, never saved, and -- just
        # like the crosshair during export_pdf -- never rendered while self.printing is set above.
        if self.should_show_hint():
            self._paint_empty_hint(painter)
        # page edge
        painter.setPen(QPen(QColor("#c9d3e0"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(PAGE_WIDTH, rect.top()), QPointF(PAGE_WIDTH, rect.bottom()))
        # fold guides: where export cuts an overflowing page onto extra sheets
        painter.setPen(QPen(QColor("#c9d3e0"), 1, Qt.PenStyle.DashLine))
        for gy in self.fold_guide_ys(max(self.sceneRect().bottom(), rect.bottom())):
            if rect.top() - 1 <= gy <= rect.bottom() + 1:
                painter.drawLine(QPointF(rect.left(), gy), QPointF(PAGE_WIDTH, gy))
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

    def focusNextPrevChild(self, next_: bool) -> bool:
        """Keep Tab for the editor while a completion popup is open (spec 024)."""
        scene = self.scene()
        editing = scene.editing_region() if scene is not None and hasattr(scene, "editing_region") else None
        if editing is not None and getattr(editing, "popup_open", lambda: False)():
            return False
        return super().focusNextPrevChild(next_)

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
