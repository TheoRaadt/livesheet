"""Developer tests for spec 009, phase W2 (canvas drawing + dialogs), written from the spec's
own acceptance criteria and "Fits current architecture?" section while implementing
``livesheet/gui/componentdialog.py``, ``ComponentRegion`` and the wiring-related parts of
``Worksheet``. The spec's architecture section explicitly calls for GUI-level coverage here (a
new ``tests/test_wiring_gui.py``), separate from the Qt-free engine-layer tests in
``tests/test_wiring_core.py`` -- this file is that deliverable, written after the tester's
independent black-box review (``tests/test_wiring_blackbox.py``, which covers the same GUI
surface from the outside) flagged that it had never been added.

Scope, deliberately complementary to (not a duplicate of) ``tests/test_wiring_blackbox.py``:
- ``ComponentRegion`` drawing/geometry: bounding rect accounts for port-label margins, ``port_at``
  hit-testing, and that ``paint()`` runs without raising for both placeholder kinds.
- Drag-to-connect through the real ``mousePressEvent``/``mouseMoveEvent``/``mouseReleaseEvent``
  handlers.
- The exact-port right-click "Connect…" path through the real ``contextMenuEvent``.
- D1 fix (docs/board/reviews/009-component-wiring-core.md): right-clicking a ``ComponentRegion``'s
  *body* (not its exact port pixel) now also offers "Connect…", defaulting to the component's
  first output port (or first input port, if it has none) -- the gap the tester's review found
  and this developer pass is fixing.
- "Insert > Component…" menu entry.

Qt-dependent; skips gracefully when PySide6 cannot load, like the rest of the GUI test suite.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QStyleOptionGraphicsItem  # noqa: E402

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.componentdialog import ComponentFields  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.worksheet import WireItem, Worksheet  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _ensure_app()
    return Worksheet()


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never touch the real on-disk LiveSheet preferences from this test module."""
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


class _FakeContextEvent:
    """Stand-in for a QGraphicsSceneContextMenuEvent carrying only the members
    ``Worksheet.contextMenuEvent`` reads."""

    def __init__(self, pos: QPointF):
        self._pos = pos

    def accept(self) -> None:
        pass

    def scenePos(self) -> QPointF:
        return self._pos

    def screenPos(self) -> QPoint:
        return QPoint(0, 0)


def _mouse_event(pos: QPointF, button=Qt.MouseButton.LeftButton):
    """A real ``QGraphicsSceneMouseEvent`` at ``pos``, so a fall-through to Qt's own default
    handling (not just this project's early-return branches) also works."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent

    ev = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMousePress)
    ev.setScenePos(pos)
    ev.setButton(button)
    ev.setButtons(button)
    return ev


def _open_menu_and_pick(sheet: Worksheet, pos: QPointF, label: str) -> None:
    """Drive the real, unpatched ``contextMenuEvent`` -> ``QMenu.exec()`` call and pick the
    action with the given visible text, using the same ``QTimer.singleShot``-from-inside-the-
    nested-event-loop technique already used by ``tests/test_matrix_dialog_blackbox.py`` and
    ``tests/test_wiring_blackbox.py`` for a live, unpatched ``QMenu``."""
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu

    def pick() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu)
        action = next((a for a in menu.actions() if a.text() == label), None)
        if action is None:
            QTest.keyClick(menu, Qt.Key.Key_Escape)
            return
        menu.setActiveAction(action)
        QTest.keyClick(menu, Qt.Key.Key_Enter)

    QTimer.singleShot(0, pick)
    sheet.contextMenuEvent(_FakeContextEvent(pos))


def _menu_labels_at(sheet: Worksheet, pos: QPointF) -> list[str]:
    """Open the real context menu at ``pos``, record its visible action labels, dismiss it."""
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu

    seen: dict = {}

    def spy() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu)
        seen["labels"] = [a.text() for a in menu.actions()]
        QTest.keyClick(menu, Qt.Key.Key_Escape)

    QTimer.singleShot(0, spy)
    sheet.contextMenuEvent(_FakeContextEvent(pos))
    return seen.get("labels", [])


# ===========================================================================
# ComponentRegion drawing/geometry
# ===========================================================================

def test_component_region_bounding_rect_grows_with_port_labels():
    sheet = _sheet()
    narrow = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    wide = sheet.add_component_region(
        "F", "formula", {"inputs": "alpha, beta, gamma", "expr": "alpha"}, QPointF(400, 0))
    # "value" has no input ports/labels; "formula" has three long input-port labels, so its
    # bounding rect's left margin (reserved for input port terminals + labels) is strictly wider.
    assert narrow.boundingRect().left() == 0.0   # no input ports -> no left margin at all
    assert wide.boundingRect().left() < 0.0       # input ports reserve space to the left of x=0


def test_component_region_port_at_hits_terminals_and_misses_body():
    sheet = _sheet()
    f = sheet.add_component_region("F", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(0, 0))
    a_local = f._input_pos(0)
    b_local = f._input_pos(1)
    out_local = f._output_pos(0)
    assert f.port_at(a_local) == ("input", "a")
    assert f.port_at(b_local) == ("input", "b")
    assert f.port_at(out_local) == ("output", "result")
    # Well inside the box, away from any terminal: no hit.
    body_centre = f.boundingRect().center()
    assert f.port_at(body_centre) is None


def test_component_region_paint_does_not_raise_for_both_kinds_error_and_ok():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(300, 0))
    sheet.recalculate()
    assert not v._has_error   # Value with a literal expr always evaluates
    assert f._has_error       # Formula with nothing wired: unconnected-input error
    for region in (v, f):
        image = QImage(200, 100, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        try:
            region.paint(painter, QStyleOptionGraphicsItem())
        finally:
            painter.end()


# ===========================================================================
# Drag-to-connect (real mousePressEvent/mouseMoveEvent/mouseReleaseEvent)
# ===========================================================================

def test_drag_to_connect_output_to_input_creates_a_wire():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))

    out_pos = v.port_scene_pos("output", "value")
    in_pos = f.port_scene_pos("input", "a")

    sheet.mousePressEvent(_mouse_event(out_pos))
    assert sheet._wire_drag == (v, "value")
    sheet.mouseMoveEvent(_mouse_event(in_pos))
    sheet.mouseReleaseEvent(_mouse_event(in_pos))

    assert sheet._wire_drag is None
    assert len(sheet._wires) == 1
    wire = sheet._wires[0]
    assert isinstance(wire, WireItem)
    assert wire.source is v and wire.source_port == "value"
    assert wire.dest is f and wire.dest_port == "a"


def test_drag_to_connect_released_over_empty_canvas_creates_no_wire():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    out_pos = v.port_scene_pos("output", "value")

    sheet.mousePressEvent(_mouse_event(out_pos))
    assert sheet._wire_drag is not None
    sheet.mouseMoveEvent(_mouse_event(QPointF(900, 900)))
    sheet.mouseReleaseEvent(_mouse_event(QPointF(900, 900)))

    assert sheet._wire_drag is None
    assert sheet._wire_drag_item is None
    assert sheet._wires == []


def test_drag_to_connect_only_starts_from_an_output_port_not_an_input():
    sheet = _sheet()
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(0, 0))
    in_pos = f.port_scene_pos("input", "a")

    sheet.mousePressEvent(_mouse_event(in_pos))
    # Pressing on an input port terminal must not start a wire drag -- it falls through to the
    # ordinary selection/move handling instead.
    assert sheet._wire_drag is None


# ===========================================================================
# Exact-port right-click "Connect…" path
# ===========================================================================

def test_exact_port_right_click_connect_dialog_creates_wire():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    out_pos = v.port_scene_pos("output", "value")

    from livesheet.gui import componentdialog

    def fake_exec(self):
        self.list_widget.setCurrentRow(0)
        return QDialog.DialogCode.Accepted

    orig = componentdialog.ConnectDialog.exec
    componentdialog.ConnectDialog.exec = fake_exec
    try:
        _open_menu_and_pick(sheet, out_pos, "Connect…")
    finally:
        componentdialog.ConnectDialog.exec = orig

    assert len(sheet._wires) == 1
    wire = sheet._wires[0]
    assert wire.source is v and wire.dest is f and wire.dest_port == "a"


# ===========================================================================
# D1 fix: right-clicking a ComponentRegion's body (not its exact port pixel)
# ===========================================================================

def test_d1_body_right_click_offers_connect_and_defaults_to_first_output():
    """D1 fix (docs/board/reviews/009-component-wiring-core.md): right-clicking anywhere on a
    ComponentRegion's body -- not its exact ~7px port terminal -- now also offers "Connect…",
    defaulting to the component's first output port. Before the fix, only an exact-port hit
    offered this action at all."""
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    body_centre = v.mapToScene(v.boundingRect().center())
    assert "Connect…" in _menu_labels_at(sheet, body_centre)

    from livesheet.gui import componentdialog

    def fake_exec(self):
        self.list_widget.setCurrentRow(0)
        return QDialog.DialogCode.Accepted

    orig = componentdialog.ConnectDialog.exec
    componentdialog.ConnectDialog.exec = fake_exec
    try:
        _open_menu_and_pick(sheet, body_centre, "Connect…")
    finally:
        componentdialog.ConnectDialog.exec = orig

    # Reaching the dialog required no pixel-precise port targeting: a plain right-click anywhere
    # on V's body was enough, defaulting to V's only output port ("value").
    assert len(sheet._wires) == 1
    wire = sheet._wires[0]
    assert wire.source is v and wire.source_port == "value"
    assert wire.dest is f and wire.dest_port == "a"


def test_d1_body_right_click_on_a_component_with_no_ports_offers_no_connect():
    """A component whose kind is unrecognised (no known ports at all, see spec 009's edge
    cases) must not offer a "Connect…" action with nothing sensible to default to."""
    sheet = _sheet()
    v = sheet.add_component_region("V", "mystery-kind-unused-by-this-build", {}, QPointF(0, 0))
    body_centre = v.mapToScene(v.boundingRect().center())
    assert "Connect…" not in _menu_labels_at(sheet, body_centre)


# ===========================================================================
# "Insert > Component…" menu entry
# ===========================================================================

def test_insert_component_menu_entry_opens_dialog_and_places_formula_component():
    _ensure_app()
    win = MainWindow()
    insert_menu = next(a.menu() for a in win.menuBar().actions()
                        if a.menu() and a.menu().title() == "&Insert")
    action = next((a for a in insert_menu.actions() if "Component" in a.text()), None)
    assert action is not None

    from livesheet.gui import componentdialog

    def fake_exec(self):
        self._fields = ComponentFields(name="FormulaOne", kind="formula",
                                        formula_inputs="a, b", formula_expr="a + b")
        return QDialog.DialogCode.Accepted

    orig = componentdialog.AddComponentDialog.exec
    componentdialog.AddComponentDialog.exec = fake_exec
    try:
        action.trigger()
    finally:
        componentdialog.AddComponentDialog.exec = orig

    names = [c.component_name for c in win.sheet.component_regions()]
    assert names == ["FormulaOne"]
    placed = win.sheet.component_regions()[0]
    assert placed.component_kind == "formula"
    assert placed._inputs == ["a", "b"]
    assert placed._outputs == ["result"]
    win.sheet.set_modified(False)
