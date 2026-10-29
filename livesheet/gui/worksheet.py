"""The worksheet canvas: scene with regions, crosshair and live recalculation."""

from __future__ import annotations

import math
import time

import shiboken6
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen, QPolygonF, QWheelEvent
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
from ..engine import Engine, wiring
from .plotregion import PlotRegion, engine_source
from .regions import COLOR_ERROR, COLOR_FRAME, GRID, ComponentRegion, MathRegion, Region, TextRegion, snap

PAGE_WIDTH = 820
MIN_HEIGHT = 1100
RECALC_DELAY_MS = 200
HINT_TEXT = "Click to place the cursor, then start typing"


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


class Worksheet(QGraphicsScene):
    modifiedChanged = Signal(bool)
    statusMessage = Signal(str)
    evaluationFinished = Signal(int, int, float)   # errors, total regions, elapsed ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = Engine()
        self.crosshair = Crosshair()
        self.addItem(self.crosshair)
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self._modified = False
        self._discarded: list[Region] = []   # removed regions waiting for their single deletion
        self._wires: list[WireItem] = []     # component-to-component connections (spec 009)
        self._wire_drag: tuple[ComponentRegion, str] | None = None   # drag-to-connect source
        self._wire_drag_item: QGraphicsLineItem | None = None
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
        region.setPos(QPointF(snap(pos.x()), snap(pos.y())))
        region.contentChanged.connect(self._on_content_changed)
        region.editingFinished.connect(self._on_editing_finished)
        region.moved.connect(self._on_moved)
        self._update_rect()
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

    def _destroy_discarded(self) -> None:
        discarded, self._discarded = self._discarded, []
        for region in discarded:
            if shiboken6.isValid(region):
                shiboken6.delete(region)

    def clear_sheet(self) -> None:
        for w in list(self._wires):
            if w.scene() is self:
                self.removeItem(w)
        self._wires = []
        for r in self.regions():
            self._discard(r)
        self.crosshair.setPos(GRID * 4, GRID * 4)
        self.crosshair.show()
        self._update_rect()

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
        return SheetDocument(regions=regs, significant=self.engine.significant, wires=wires)

    def load_document(self, doc: SheetDocument) -> None:
        self.clear_sheet()
        self.engine.significant = doc.significant
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
            (id(r), engine_source(r.source) if isinstance(r, PlotRegion) else r.source) for r in evaluated)
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
        comp_results = wiring.evaluate(specs, wire_specs, self.engine)
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
        self.set_modified()
        self.schedule_recalc()

    def _on_moved(self) -> None:
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

    def mouseMoveEvent(self, event) -> None:
        if self._wire_drag is not None:
            self._update_wire_drag(event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._wire_drag is not None:
            self._finish_wire_drag(event.scenePos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.editing_region() is not None:
            super().keyPressEvent(event)
            return
        key, text = event.key(), event.text()
        selected = [it for it in self.selectedItems() if isinstance(it, Region)]
        selected_wires = [it for it in self.selectedItems() if isinstance(it, WireItem)]
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and (selected or selected_wires):
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
