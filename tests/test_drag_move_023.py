"""Spec 023: drag-to-move regions, nudging, Esc-cancel. Real mouse events on the view's viewport."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402

NO = Qt.KeyboardModifier.NoModifier
LEFT = Qt.MouseButton.LeftButton


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    app.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


class Mouse:
    def __init__(self, win, app):
        self.win, self.app = win, app
        self.view, self.vp, self.ws = win.view, win.view.viewport(), win.sheet

    def pt(self, scene_x, scene_y) -> QPoint:
        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)
        return self.view.mapFromScene(QPointF(scene_x, scene_y))

    def press(self, p):
        QTest.mousePress(self.vp, LEFT, NO, p)
        self.app.processEvents()

    def move(self, p):
        QTest.mouseMove(self.vp, p)
        self.app.processEvents()

    def release(self, p):
        QTest.mouseRelease(self.vp, LEFT, NO, p)
        self.app.processEvents()

    def drag(self, start: QPoint, dx: int, dy: int, steps: int = 8):
        self.press(start)
        for i in range(1, steps + 1):
            self.move(start + QPoint(dx * i // steps, dy * i // steps))
        self.release(start + QPoint(dx, dy))

    def send(self, etype, p, buttons=LEFT):
        ev = QMouseEvent(etype, QPointF(p), self.vp.mapToGlobal(QPointF(p)), LEFT, buttons, NO)
        QApplication.sendEvent(self.vp, ev)
        self.app.processEvents()


@pytest.fixture
def m(win, app, monkeypatch):
    import livesheet.gui.worksheet as wsmod
    monkeypatch.setattr(wsmod, "EDGE_SCROLL_STEP", 0)   # edge scrolling has its own test
    return Mouse(win, app)


def test_edge_scroll_is_bounded_and_scrolls(win, app):
    mouse = Mouse(win, app)
    r = _math(mouse.ws, 100, 100)
    p = mouse.pt(108, 110)
    bottom = mouse.vp.rect().height() - 5
    mouse.press(p)
    mouse.move(p + QPoint(0, 60))
    before = mouse.view.verticalScrollBar().value()
    mouse.move(QPoint(p.x(), bottom))
    assert mouse.view.verticalScrollBar().value() == before + 20
    mouse.release(QPoint(p.x(), bottom))


def body(r):
    """A view point inside the region's text."""
    return r.pos() + QPointF(8, 10)


def _math(ws, x, y, text="a := 1"):
    r = ws.add_region("math", QPointF(x, y), text)
    ws.recalculate()
    return r


def _grab(m, r, dx, dy, steps=8):
    b = body(r)
    m.drag(m.pt(b.x(), b.y()), dx, dy, steps)


def test_root_cause_click_then_drag_arrives_as_double_click(m):
    """Step 0 regression. Theo: select by click, then press-and-drag does nothing. Qt delivers
    that second press as a DOUBLE-CLICK event, which used to start editing (no move)."""
    r = _math(m.ws, 100, 100)
    p = m.pt(*(lambda b: (b.x(), b.y()))(body(r)))
    QTest.mouseClick(m.vp, LEFT, NO, p)
    m.app.processEvents()
    assert r.isSelected() and not r.editing
    m.send(QEvent.Type.MouseButtonDblClick, p)          # the quick second press
    assert not r.editing
    for i in range(1, 9):
        m.send(QEvent.Type.MouseMove, p + QPoint(6 * i, 3 * i))
    m.send(QEvent.Type.MouseButtonRelease, p + QPoint(48, 24), buttons=Qt.MouseButton.NoButton)
    assert (r.pos().x(), r.pos().y()) == (150, 120)   # 48 x 24 px drag, snapped
    assert not r.editing


def test_real_double_click_still_edits(m):
    r = _math(m.ws, 100, 100)
    p = m.pt(*(lambda b: (b.x(), b.y()))(body(r)))
    QTest.mouseClick(m.vp, LEFT, NO, p)
    m.send(QEvent.Type.MouseButtonDblClick, p)
    assert not r.editing                     # deferred to release
    m.send(QEvent.Type.MouseButtonRelease, p, buttons=Qt.MouseButton.NoButton)
    assert r.editing
    assert (r.pos().x(), r.pos().y()) == (100, 100)


def test_d1_basic_move(m):
    r = _math(m.ws, 100, 100)
    _grab(m, r, 53, 27)
    assert (r.pos().x(), r.pos().y()) == (150, 130)
    assert r.isSelected() and m.ws.modified
    assert not m.ws._timer.isActive()   # recalculated immediately


def test_d2_click_is_not_a_drag(m):
    r = _math(m.ws, 100, 100)
    _grab(m, r, 2, 2, steps=2)
    assert (r.pos().x(), r.pos().y()) == (100, 100)
    assert r.isSelected() and not m.ws.modified


def test_d3_clamp(m):
    r = _math(m.ws, 100, 100)
    _grab(m, r, -500, -500)
    assert (r.pos().x(), r.pos().y()) == (0, 0)
    r2 = _math(m.ws, 100, 300, "b := 2")
    m.ws.clearSelection()
    _grab(m, r2, -500, 30)
    assert (r2.pos().x(), r2.pos().y()) == (0, 330)


def test_d4_live_order(m):
    ws = m.ws
    p = _math(ws, 300, 50, "a := 1")
    q = _math(ws, 10, 200, "a =")
    assert "not defined" in q.result.error
    _grab(m, p, -290, 50)
    assert (p.pos().x(), p.pos().y()) == (10, 100)
    assert q.result.status != "error" and "1" in q.result.output
    _grab(m, p, 290, -50)
    assert (p.pos().x(), p.pos().y()) == (300, 50)
    assert q.result.status == "error"


def test_d5_group_move_and_group_clamp(m):
    ws = m.ws
    r1, r2 = _math(ws, 100, 100), _math(ws, 200, 150, "b := 2")
    r1.setSelected(True), r2.setSelected(True)
    _grab(m, r1, 40, 20)
    assert (r1.pos().x(), r1.pos().y()) == (140, 120)
    assert (r2.pos().x(), r2.pos().y()) == (240, 170)
    ws.clearSelection()
    r1.setPos(10, 10), r2.setPos(200, 150)
    r1.setSelected(True), r2.setSelected(True)
    _grab(m, r1, -100, -100)
    assert (r1.pos().x(), r1.pos().y()) == (0, 0)
    assert (r2.pos().x(), r2.pos().y()) == (190, 140)


def test_d6_mixed_kinds_and_marker(m):
    ws = m.ws
    mr = _math(ws, 100, 100)
    tr = ws.add_region("text", QPointF(300, 100), "note")
    pr = ws.add_region("plot", QPointF(100, 300), "")
    cr = ws.add_component_region("V1", "value", {"expr": "1"}, QPointF(500, 100))
    marker = ws._add_marker(2000)
    items = [mr, tr, pr, cr]
    starts = [QPointF(i.pos()) for i in items]
    for i in items:
        i.setSelected(True)
    marker.setSelected(True)
    m.drag(m.pt(mr.pos().x() + 8, mr.pos().y() + 10), 30, 20)
    for i, s in zip(items, starts):
        assert i.pos() == s + QPointF(30, 20)
    assert marker.y == 2000


def test_d7_escape_cancels(m):
    ws = m.ws
    r = _math(ws, 100, 100)
    ws.set_modified(False)
    p = m.pt(*(lambda b: (b.x(), b.y()))(body(r)))
    m.press(p)
    for i in range(1, 9):
        m.move(p + QPoint(10 * i, 8 * i))
    assert (r.pos().x(), r.pos().y()) == (180, 160)
    QTest.keyClick(m.vp, Qt.Key.Key_Escape)
    m.app.processEvents()
    assert (r.pos().x(), r.pos().y()) == (100, 100)
    assert not ws.modified
    m.move(p + QPoint(100, 100))
    m.release(p + QPoint(100, 100))
    assert (r.pos().x(), r.pos().y()) == (100, 100)
    assert not ws.modified


def test_escape_without_drag_still_leaves_editing(m):
    r = _math(m.ws, 100, 100)
    r.start_editing()
    m.app.processEvents()
    QTest.keyClick(m.vp, Qt.Key.Key_Escape)
    m.app.processEvents()
    assert not r.editing


def test_d8_page_break(m):
    ws = m.ws
    ws._add_marker(1220)
    r = _math(ws, 10, 100)
    other = _math(ws, 10, 200, "b := 2")
    _grab(m, r, 0, 1200)
    assert (r.pos().x(), r.pos().y()) == (10, 1300)
    assert (other.pos().x(), other.pos().y()) == (10, 200)
    assert ws.page_markers()[0].y == 1220
    assert ws.ordered_regions()[-1] is r


def test_d9_edit_versus_move(m):
    ws = m.ws
    r = _math(ws, 100, 100)
    r.start_editing()
    m.app.processEvents()
    # drag inside the text: selects text, never moves
    inside = r.mapToScene(r.content_rect().center())
    m.drag(m.pt(inside.x(), inside.y()), 20, 0)
    assert (r.pos().x(), r.pos().y()) == (100, 100) and r.editing
    # ring: just outside the 3-unit padding, left edge
    ring = r.mapToScene(QPointF(r.content_rect().left() - 5, r.content_rect().center().y()))
    assert r.in_grip(r.mapFromScene(ring))
    m.drag(m.pt(ring.x(), ring.y()), 30, 20)
    assert (r.pos().x(), r.pos().y()) == (130, 120)
    assert r.editing and r.source == "a := 1"
    assert r.editor.hasFocus() or ws.focusItem() is r.editor


def test_d10_priorities(m):
    ws = m.ws
    pr = ws.add_region("plot", QPointF(100, 300), "")
    pr.setSelected(True)
    h = pr.mapToScene(pr.handle_rect().center())
    w0, h0 = pr.size_w, pr.size_h
    m.drag(m.pt(h.x(), h.y()), 40, 30)
    assert (pr.pos().x(), pr.pos().y()) == (100, 300)
    assert (pr.size_w, pr.size_h) != (w0, h0)
    # empty canvas: nothing moves
    r = _math(ws, 100, 100)
    m.drag(m.pt(600, 500), 30, 30)
    assert (r.pos().x(), r.pos().y()) == (100, 100)


def test_component_output_port_starts_wire_not_move(m):
    ws = m.ws
    c = ws.add_component_region("V1", "value", {"expr": "1"}, QPointF(100, 100))
    port = c.port_scene_pos("output", "value")
    m.press(m.pt(port.x(), port.y()))
    assert ws._wire_drag is not None
    m.move(m.pt(port.x() + 40, port.y() + 40))
    m.release(m.pt(port.x() + 40, port.y() + 40))
    assert (c.pos().x(), c.pos().y()) == (100, 100)


def test_d11_zoom(m):
    r = _math(m.ws, 100, 100)
    m.view.set_zoom(2.0)
    m.app.processEvents()
    _grab(m, r, 100, 0)
    assert (r.pos().x(), r.pos().y()) == (150, 100)


def test_d12_nudge(m):
    ws = m.ws
    r = _math(ws, 100, 100)
    r.setSelected(True)
    ws.set_modified(False)
    QTest.keyClick(m.vp, Qt.Key.Key_Right)
    assert (r.pos().x(), r.pos().y()) == (110, 100) and ws.modified
    QTest.keyClick(m.vp, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    assert (r.pos().x(), r.pos().y()) == (110, 150)
    r.setPos(0, 100)
    ws.set_modified(False)
    QTest.keyClick(m.vp, Qt.Key.Key_Left)
    assert r.pos().x() == 0 and not ws.modified
    r2 = _math(ws, 50, 100, "b := 2")
    r2.setSelected(True)
    QTest.keyClick(m.vp, Qt.Key.Key_Left)
    assert (r.pos().x(), r2.pos().x()) == (0, 50)
    QTest.keyClick(m.vp, Qt.Key.Key_Right)
    assert (r.pos().x(), r2.pos().x()) == (10, 60)


def test_d13_wires_follow(m):
    ws = m.ws
    v = ws.add_component_region("V1", "value", {"expr": "1"}, QPointF(100, 100))
    f = ws.add_component_region("F1", "formula", {"inputs": "a", "expr": "a"}, QPointF(400, 100))
    assert ws.try_connect((v, "value"), (f, "a")) is None
    wire = ws._wires[0]
    b = v.pos() + QPointF(20, 5)
    start = m.pt(b.x(), b.y())
    m.press(start)
    for i in range(1, 7):
        m.move(start + QPoint(7 * i, 5 * i))
        assert wire.endpoints() == (v.port_scene_pos("output", "value"),
                                    f.port_scene_pos("input", "a"))
        assert wire.path().elementAt(0).x == pytest.approx(v.port_scene_pos("output", "value").x())
    m.release(start + QPoint(42, 30))


def test_d14_batching(m, monkeypatch):
    ws = m.ws
    regs = [_math(ws, 20 + (i % 20) * 30, 20 + (i // 20) * 30, f"v{i} := {i}") for i in range(200)]
    for r in regs:
        r.setSelected(True)
    calls = {"rect": 0, "wires": 0, "recalc": 0}
    orig = (ws._update_rect, ws._sync_all_wires, ws.schedule_recalc)
    monkeypatch.setattr(ws, "_update_rect", lambda: (calls.__setitem__("rect", calls["rect"] + 1), orig[0()] if False else orig[0]())[1])
    monkeypatch.setattr(ws, "_sync_all_wires", lambda: (calls.__setitem__("wires", calls["wires"] + 1), orig[1]())[1])
    monkeypatch.setattr(ws, "schedule_recalc", lambda: (calls.__setitem__("recalc", calls["recalc"] + 1), orig[2]())[1])
    b = body(regs[0])
    start = m.pt(b.x(), b.y())
    m.press(start)
    for i in range(1, 6):
        m.move(start + QPoint(10 * i, 0))
    assert calls == {"rect": 5, "wires": 5, "recalc": 5}
    m.release(start + QPoint(50, 0))


def test_d15_cursor(m):
    r = _math(m.ws, 100, 100)
    b = body(r)
    p = m.pt(b.x(), b.y())
    r.update_cursor(r.mapFromScene(b))            # what the hover handlers call
    assert r.cursor().shape() == Qt.CursorShape.OpenHandCursor
    pr = m.ws.add_region("plot", QPointF(100, 300), "")
    pr.update_cursor(pr.handle_rect().center())   # resize handle keeps its own cursor
    assert pr.cursor().shape() == Qt.CursorShape.ArrowCursor
    m.press(p)
    for i in range(1, 6):
        m.move(p + QPoint(6 * i, 0))
    assert m.vp.cursor().shape() == Qt.CursorShape.ClosedHandCursor
    m.release(p + QPoint(30, 0))
    assert m.vp.cursor().shape() != Qt.CursorShape.ClosedHandCursor


def test_d16_roundtrip(m, tmp_path):
    ws = m.ws
    r = _math(ws, 100, 100)
    _grab(m, r, 53, 27)
    doc = ws.to_document()
    mine = [d for d in doc.regions if d.text == "a := 1"][0]
    assert (mine.x, mine.y) == (150, 130)
    path = tmp_path / "t.lsheet"
    doc.save(path)
    ws.load_document(SheetDocument.load(path))
    assert [(r.pos().x(), r.pos().y()) for r in ws.regions()] == [(150, 130)]


def test_demo_file_positions_unchanged(m):
    from pathlib import Path
    demo = Path(__file__).resolve().parent.parent / "examples" / "demo.lsheet"
    doc = SheetDocument.load(demo)
    before = sorted((d.x, d.y, d.kind) for d in doc.regions)
    m.ws.load_document(doc)
    after = sorted((d.x, d.y, d.kind) for d in m.ws.to_document().regions)
    assert before == after


def test_d17_move_regions_call_counts(m, monkeypatch):
    ws = m.ws
    calls = []
    orig = ws.move_regions
    monkeypatch.setattr(ws, "move_regions", lambda *a, **k: (calls.append(1), orig(*a, **k))[1])
    r = _math(ws, 100, 100)
    _grab(m, r, 53, 27)
    assert len(calls) == 1
    _grab(m, r, 2, 2, steps=2)          # click
    assert len(calls) == 1
    QTest.keyClick(m.vp, Qt.Key.Key_Right)
    QTest.keyClick(m.vp, Qt.Key.Key_Right)
    assert len(calls) == 3
    b = body(r)
    p = m.pt(b.x(), b.y())             # cancelled drag
    m.press(p)
    for i in range(1, 6):
        m.move(p + QPoint(10 * i, 0))
    QTest.keyClick(m.vp, Qt.Key.Key_Escape)
    m.release(p + QPoint(50, 0))
    assert len(calls) == 3
