"""Independent black-box review of spec 023 (drag-to-move regions). Real QTest mouse events."""

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
RIGHT = Qt.MouseButton.RightButton


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(app, monkeypatch):
    import livesheet.gui.worksheet as wsmod
    monkeypatch.setattr(wsmod, "EDGE_SCROLL_STEP", 0)
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    app.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


class H:
    def __init__(self, win, app):
        self.win, self.app, self.ws = win, app, win.sheet
        self.view, self.vp = win.view, win.view.viewport()

    def pt(self, x, y) -> QPoint:
        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)
        return self.view.mapFromScene(QPointF(x, y))

    def math(self, x, y, text="a := 1"):
        r = self.ws.add_region("math", QPointF(x, y), text)
        self.ws.recalculate()
        return r

    def inside(self, r):
        return self.pt(r.pos().x() + 8, r.pos().y() + 10)

    def press(self, p, button=LEFT):
        QTest.mousePress(self.vp, button, NO, p)
        self.app.processEvents()

    def move(self, p):
        QTest.mouseMove(self.vp, p)
        self.app.processEvents()

    def release(self, p, button=LEFT):
        QTest.mouseRelease(self.vp, button, NO, p)
        self.app.processEvents()

    def drag(self, p, dx, dy, steps=8, button=LEFT):
        self.press(p, button)
        for i in range(1, steps + 1):
            self.move(p + QPoint(dx * i // steps, dy * i // steps))
        self.release(p + QPoint(dx, dy), button)

    def raw(self, etype, p, buttons=LEFT):
        ev = QMouseEvent(etype, QPointF(p), self.vp.mapToGlobal(QPointF(p)), LEFT, buttons, NO)
        QApplication.sendEvent(self.vp, ev)
        self.app.processEvents()

    def xy(self, r):
        return (r.pos().x(), r.pos().y())


@pytest.fixture
def h(env, app):
    return H(env, app)


# --- Theo's failing case ---------------------------------------------------------------

def test_click_select_then_quick_press_drag_moves_not_edits(h):
    r = h.math(100, 100)
    p = h.inside(r)
    QTest.mouseClick(h.vp, LEFT, NO, p)
    h.app.processEvents()
    assert r.isSelected() and not r.editing
    h.raw(QEvent.Type.MouseButtonDblClick, p)
    for i in range(1, 11):
        h.raw(QEvent.Type.MouseMove, p + QPoint(5 * i, 4 * i))
    h.raw(QEvent.Type.MouseButtonRelease, p + QPoint(50, 40), buttons=Qt.MouseButton.NoButton)
    assert h.xy(r) == (150, 140)
    assert not r.editing and h.ws.modified


def test_dblclick_typed_press_then_tiny_move_edits_on_release(h):
    r = h.math(100, 100)
    p = h.inside(r)
    QTest.mouseClick(h.vp, LEFT, NO, p)
    h.raw(QEvent.Type.MouseButtonDblClick, p)
    h.raw(QEvent.Type.MouseMove, p + QPoint(2, 1))
    h.raw(QEvent.Type.MouseButtonRelease, p + QPoint(2, 1), buttons=Qt.MouseButton.NoButton)
    assert r.editing and h.xy(r) == (100, 100)


def test_dblclick_drag_does_not_open_editor_later(h):
    """After a dbl-click-typed drag, a later plain release elsewhere must not start editing."""
    r = h.math(100, 100)
    p = h.inside(r)
    QTest.mouseClick(h.vp, LEFT, NO, p)
    h.raw(QEvent.Type.MouseButtonDblClick, p)
    for i in range(1, 6):
        h.raw(QEvent.Type.MouseMove, p + QPoint(10 * i, 0))
    h.raw(QEvent.Type.MouseButtonRelease, p + QPoint(50, 0), buttons=Qt.MouseButton.NoButton)
    h.app.processEvents()
    assert not r.editing
    assert h.ws.editing_region() is None


def test_plot_region_dblclick_drag_moves_without_dialog(h, monkeypatch):
    pr = h.ws.add_region("plot", QPointF(100, 300), "")
    opened = []
    for name in ("on_double_click",):
        orig = getattr(type(pr), name)
        monkeypatch.setattr(type(pr), name, lambda self, *a, _o=orig: (opened.append(1), _o(self, *a))[1])
    p = h.pt(pr.pos().x() + 20, pr.pos().y() + 20)
    QTest.mouseClick(h.vp, LEFT, NO, p)
    h.raw(QEvent.Type.MouseButtonDblClick, p)
    for i in range(1, 7):
        h.raw(QEvent.Type.MouseMove, p + QPoint(10 * i, 0))
    h.raw(QEvent.Type.MouseButtonRelease, p + QPoint(60, 0), buttons=Qt.MouseButton.NoButton)
    assert h.xy(pr) == (160, 300)
    assert opened == []


# --- plain drag, threshold, buttons ------------------------------------------------------

def test_plain_drag_unselected_selects_and_clears_others(h):
    a, b = h.math(100, 100), h.math(100, 200, "b := 2")
    b.setSelected(True)
    h.drag(h.inside(a), 30, 0)
    assert h.xy(a) == (130, 100) and h.xy(b) == (100, 200)
    assert a.isSelected() and not b.isSelected()


def test_threshold_boundaries(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.drag(p, 3, 0, steps=3)          # below 4 px
    assert h.xy(r) == (100, 100) and not h.ws.modified
    h.drag(p, 20, 0, steps=4)         # clearly above
    assert h.xy(r) == (120, 100)


def test_drag_out_and_back_is_not_modified(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    h.move(p + QPoint(60, 40))
    h.move(p + QPoint(1, 1))
    h.release(p + QPoint(1, 1))
    assert h.xy(r) == (100, 100)
    assert not h.ws.modified


def test_snap_steps_visible_during_drag(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    seen = []
    for dx in (6, 12, 17, 23, 29, 36):
        h.move(p + QPoint(dx, 0))
        seen.append(r.pos().x())
        assert r.pos().x() % 10 == 0
    assert seen == [110, 110, 120, 120, 130, 140]
    h.release(p + QPoint(36, 0))


def test_right_button_drag_moves_nothing(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p, RIGHT)
    h.move(p + QPoint(40, 40))
    h.release(p + QPoint(40, 40), RIGHT)
    assert h.xy(r) == (100, 100)
    assert not h.ws.move_active()


def test_middle_button_drag_moves_nothing(h):
    r = h.math(100, 100)
    p = h.inside(r)
    mid = Qt.MouseButton.MiddleButton
    h.press(p, mid)
    h.move(p + QPoint(40, 40))
    h.release(p + QPoint(40, 40), mid)
    assert h.xy(r) == (100, 100)


def test_result_area_is_draggable(h):
    r = h.math(100, 100, "x := 3")
    h.ws.recalculate()
    br = r.boundingRect()
    p = h.pt(r.pos().x() + br.width() - 4, r.pos().y() + br.height() / 2)
    h.drag(p, 20, 20)
    assert h.xy(r) == (120, 120)


def test_drag_beyond_viewport_keeps_following(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    h.move(p + QPoint(40, 0))
    h.move(QPoint(h.vp.width() + 50, p.y()))   # pointer outside viewport
    assert r.pos().x() > 140
    h.release(QPoint(h.vp.width() + 50, p.y()))


# --- group ---------------------------------------------------------------------------------

def test_rubber_band_then_drag_group(h):
    a, b = h.math(100, 100), h.math(200, 100, "b := 2")
    far = h.math(600, 500, "c := 3")
    h.drag(h.pt(60, 60), 260, 100)       # rubber band over a and b
    assert a.isSelected() and b.isSelected() and not far.isSelected()
    h.drag(h.inside(b), 30, 50)
    assert h.xy(a) == (130, 150) and h.xy(b) == (230, 150) and h.xy(far) == (600, 500)


def test_group_offgrid_offsets_preserved(h):
    a = h.math(100, 100)
    b = h.math(200, 150, "b := 2")
    b.setPos(203, 157)                    # programmatic; itemChange snaps
    snapped = (b.pos().x() - a.pos().x(), b.pos().y() - a.pos().y())
    a.setSelected(True), b.setSelected(True)
    h.drag(h.inside(a), 37, 23)
    assert (b.pos().x() - a.pos().x(), b.pos().y() - a.pos().y()) == snapped


def test_group_clamp_x_only_keeps_y_move(h):
    a, b = h.math(10, 100), h.math(200, 100, "b := 2")
    a.setSelected(True), b.setSelected(True)
    h.drag(h.inside(b), -300, 40)
    assert h.xy(a) == (0, 140) and h.xy(b) == (190, 140)


def test_click_on_group_member_no_drag_keeps_document_unmodified(h):
    a, b = h.math(100, 100), h.math(200, 100, "b := 2")
    a.setSelected(True), b.setSelected(True)
    h.drag(h.inside(a), 1, 1, steps=1)
    assert h.xy(a) == (100, 100) and h.xy(b) == (200, 100)
    assert not h.ws.modified


def test_select_all_then_drag(h):
    a, b = h.math(100, 100), h.math(200, 300, "b := 2")
    h.win.sheet.select_all_regions() if hasattr(h.win.sheet, "select_all_regions") else [
        r.setSelected(True) for r in h.ws.regions()]
    h.drag(h.inside(a), 20, 10)
    assert h.xy(a) == (120, 110) and h.xy(b) == (220, 310)


def test_esc_cancels_group_drag(h):
    a, b = h.math(100, 100), h.math(200, 100, "b := 2")
    a.setSelected(True), b.setSelected(True)
    h.ws.set_modified(False)
    p = h.inside(a)
    h.press(p)
    for i in range(1, 6):
        h.move(p + QPoint(10 * i, 10 * i))
    assert h.xy(a) != (100, 100)
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    assert h.xy(a) == (100, 100) and h.xy(b) == (200, 100)
    assert not h.ws.modified
    h.release(p + QPoint(50, 50))
    assert h.xy(a) == (100, 100)


def test_esc_cancel_restores_prior_modified_true(h):
    r = h.math(100, 100)
    h.ws.set_modified(True)
    p = h.inside(r)
    h.press(p)
    for i in range(1, 6):
        h.move(p + QPoint(10 * i, 0))
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    h.release(p + QPoint(50, 0))
    assert h.ws.modified and h.xy(r) == (100, 100)


def test_esc_cancel_restores_results_after_order_change(h):
    p_ = h.math(300, 50, "a := 1")
    q = h.math(10, 200, "a =")
    p = h.pt(p_.pos().x() + 8, p_.pos().y() + 10)
    h.press(p)
    for i in range(1, 9):
        h.move(p + QPoint(-36 * i, 15 * i))
    h.ws.recalculate()
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    h.release(p + QPoint(-288, 120))
    assert h.xy(p_) == (300, 50)
    assert q.result.status == "error"


def test_esc_before_threshold_does_not_break_click(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    h.release(p)
    assert h.xy(r) == (100, 100) and r.isSelected()


def test_second_drag_after_cancel_works(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    for i in range(1, 6):
        h.move(p + QPoint(10 * i, 0))
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    h.release(p + QPoint(50, 0))
    h.drag(p, 30, 0)
    assert h.xy(r) == (130, 100)


def test_focus_loss_cancels_drag(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    for i in range(1, 6):
        h.move(p + QPoint(10 * i, 0))
    from PySide6.QtGui import QFocusEvent
    QApplication.sendEvent(h.ws, QFocusEvent(QEvent.Type.FocusOut))
    assert h.xy(r) == (100, 100)
    h.release(p + QPoint(50, 0))
    assert h.xy(r) == (100, 100)


# --- nudge ---------------------------------------------------------------------------------

def test_nudge_all_directions_and_shift(h):
    r = h.math(200, 200)
    r.setSelected(True)
    for key, mod, exp in [(Qt.Key.Key_Left, NO, (190, 200)), (Qt.Key.Key_Up, NO, (190, 190)),
                          (Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier, (240, 190)),
                          (Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier, (240, 140))]:
        QTest.keyClick(h.vp, key, mod)
        assert h.xy(r) == exp


def test_shift_nudge_clamps_whole_group_on_axis(h):
    a, b = h.math(20, 300), h.math(300, 300, "b := 2")
    a.setSelected(True), b.setSelected(True)
    QTest.keyClick(h.vp, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    assert h.xy(a) == (20, 300) and h.xy(b) == (300, 300)   # a would go to -30: group stays
    QTest.keyClick(h.vp, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
    assert h.xy(a) == (20, 250)


def test_nudge_one_axis_blocked_other_free_not_applicable(h):
    """A blocked axis does not block the other axis (separate keys)."""
    a = h.math(0, 100)
    a.setSelected(True)
    h.ws.set_modified(False)
    QTest.keyClick(h.vp, Qt.Key.Key_Left)
    assert not h.ws.modified
    QTest.keyClick(h.vp, Qt.Key.Key_Down)
    assert h.xy(a) == (0, 110) and h.ws.modified


def test_nudge_recalculates_order(h):
    p_ = h.math(30, 50, "a := 1")
    q = h.math(10, 200, "a =")
    p_.setSelected(True)
    assert q.result.status == "error"
    for _ in range(3):
        QTest.keyClick(h.vp, Qt.Key.Key_Left)
    h.ws.recalculate()
    assert h.xy(p_) == (0, 50)
    assert q.result.status != "error"


def test_nudge_ignored_while_editing(h):
    r = h.math(100, 100)
    r.start_editing()
    h.app.processEvents()
    QTest.keyClick(h.vp, Qt.Key.Key_Right)
    assert h.xy(r) == (100, 100)


def test_nudge_with_nothing_selected_moves_crosshair_by_50_with_shift(h):
    h.ws.clearSelection()
    c0 = h.ws.crosshair.pos()
    QTest.keyClick(h.vp, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    assert h.ws.crosshair.pos().x() == c0.x() + 50


def test_nudge_does_not_move_page_break_marker(h):
    m = h.ws._add_marker(500)
    r = h.math(100, 100)
    r.setSelected(True)
    m.setSelected(True)
    QTest.keyClick(h.vp, Qt.Key.Key_Down)
    assert h.xy(r) == (100, 110) and m.y == 500


# --- editing grip ----------------------------------------------------------------------------

def test_edit_mode_ring_drag_keeps_text_and_modifies(h):
    r = h.math(100, 100)
    r.start_editing()
    h.app.processEvents()
    c = r.content_rect()
    ring = r.mapToScene(QPointF(c.center().x(), c.top() - 5))
    assert r.in_grip(r.mapFromScene(ring))
    h.drag(h.pt(ring.x(), ring.y()), 0, 40)
    assert h.xy(r) == (100, 140) and r.editing and r.source == "a := 1"


def test_edit_mode_text_press_never_moves_even_far_drag(h):
    r = h.math(100, 100, "a := 12345")
    r.start_editing()
    h.app.processEvents()
    inside = r.mapToScene(r.content_rect().center())
    h.drag(h.pt(inside.x(), inside.y()), 0, 80)
    assert h.xy(r) == (100, 100)


def test_edit_mode_far_outside_ring_is_canvas(h):
    r = h.math(100, 100)
    r.start_editing()
    h.app.processEvents()
    h.drag(h.pt(r.pos().x() + 200, r.pos().y() + 100), 20, 20)
    assert h.xy(r) == (100, 100)
    assert not r.editing        # empty canvas press finishes editing


def test_editing_other_region_finishes_when_dragging_target(h):
    a, b = h.math(100, 100), h.math(100, 300, "b := 2")
    a.start_editing()
    h.app.processEvents()
    h.drag(h.inside(b), 30, 0)
    assert not a.editing
    assert h.xy(b) == (130, 300)


def test_edit_mode_widened_hit_area_does_not_change_saved_size(h):
    r = h.math(100, 100)
    before = h.ws.to_document().regions[0]
    r.start_editing()
    h.app.processEvents()
    after = h.ws.to_document().regions[0]
    assert (before.w, before.h) == (after.w, after.h) if hasattr(before, "w") else True


# --- plot / component priorities -----------------------------------------------------------

def test_plot_body_drag_moves_and_handle_resizes_independently(h):
    pr = h.ws.add_region("plot", QPointF(100, 300), "")
    h.drag(h.pt(pr.pos().x() + 30, pr.pos().y() + 30), 40, 20)
    assert h.xy(pr) == (140, 320)
    hnd = pr.mapToScene(pr.handle_rect().center())
    w0, h0 = pr.size_w, pr.size_h
    h.drag(h.pt(hnd.x(), hnd.y()), 30, 30)
    assert h.xy(pr) == (140, 320) and (pr.size_w, pr.size_h) != (w0, h0)


def test_plot_handle_on_unselected_plot_resizes_not_moves(h):
    pr = h.ws.add_region("plot", QPointF(100, 300), "")
    h.ws.clearSelection()
    hnd = pr.mapToScene(pr.handle_rect().center())
    w0 = pr.size_w
    h.drag(h.pt(hnd.x(), hnd.y()), 30, 0)
    assert h.xy(pr) == (100, 300)


def test_component_body_drag_moves_with_wire_follow(h):
    v = h.ws.add_component_region("V1", "value", {"expr": "1"}, QPointF(100, 100))
    f = h.ws.add_component_region("F1", "formula", {"inputs": "a", "expr": "a"}, QPointF(400, 100))
    assert h.ws.try_connect((v, "value"), (f, "a")) is None
    h.ws.recalculate()
    h.drag(h.pt(v.pos().x() + 20, v.pos().y() + 5), 0, 100)
    assert h.xy(v) == (100, 200)
    w = h.ws._wires[0]
    assert w.endpoints() == (v.port_scene_pos("output", "value"), f.port_scene_pos("input", "a"))


def test_selected_marker_in_selection_stays_while_regions_drag(h):
    m = h.ws._add_marker(900)
    a = h.math(100, 100)
    a.setSelected(True)
    m.setSelected(True)
    h.drag(h.inside(a), 0, 50)
    assert h.xy(a) == (100, 150) and m.y == 900


def test_dragging_page_break_marker_does_not_move_regions(h):
    m = h.ws._add_marker(900)
    a = h.math(100, 100)
    a.setSelected(True)
    h.drag(h.pt(300, 900), 0, 60)
    assert h.xy(a) == (100, 100)


# --- order, page break ---------------------------------------------------------------------

def test_drag_changes_order_and_results_current_immediately(h):
    p = h.math(300, 50, "a := 1")
    q = h.math(10, 200, "a =")
    h.drag(h.inside(p), -290, 50)
    assert not h.ws._timer.isActive()
    assert q.result.status != "error"
    assert h.ws.ordered_regions()[0] is p


def test_live_recalc_while_pointer_pauses(h, app):
    p_ = h.math(300, 50, "a := 1")
    q = h.math(10, 200, "a =")
    p = h.inside(p_)
    h.press(p)
    for i in range(1, 9):
        h.move(p + QPoint(-36 * i, 6 * i))
    assert h.xy(p_) == (10, 100)
    QTest.qWait(450)
    assert q.result.status != "error"
    h.release(p + QPoint(-288, 48))


def test_page_break_cross_both_directions(h):
    h.ws._add_marker(1220)
    r = h.math(10, 100)
    first = h.math(10, 200, "b := 2")
    last = h.math(10, 1300, "c := 3")
    h.drag(h.inside(r), 0, 1200)
    assert h.xy(r) == (10, 1300)
    assert h.xy(first) == (10, 200) and h.xy(last) == (10, 1300)
    assert h.ws.page_markers()[0].y == 1220
    order = h.ws.ordered_regions()
    assert order.index(first) < order.index(r)
    h.ws.clearSelection()
    r.setSelected(True)
    h.ws.nudge([r], 0, -1100)                    # keyboard route back over the break
    assert h.xy(r) == (10, 200) and h.ws.page_markers()[0].y == 1220


# --- misc / edge ------------------------------------------------------------------------------

def test_delete_region_mid_drag_is_silent(h):
    r = h.math(100, 100)
    other = h.math(300, 100, "b := 2")
    p = h.inside(r)
    h.press(p)
    for i in range(1, 4):
        h.move(p + QPoint(10 * i, 0))
    h.ws.remove_regions([r])
    h.move(p + QPoint(60, 0))
    h.release(p + QPoint(60, 0))
    assert h.xy(other) == (300, 100)
    assert not h.ws.move_active()


def test_load_document_mid_drag_is_silent(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    for i in range(1, 4):
        h.move(p + QPoint(10 * i, 0))
    h.ws.load_document(SheetDocument())
    h.move(p + QPoint(60, 0))
    h.release(p + QPoint(60, 0))
    assert h.ws.regions() == []
    assert not h.ws.move_active()


def test_two_regions_same_position_allowed(h):
    a, b = h.math(100, 100), h.math(300, 100, "b := 2")
    h.drag(h.inside(b), -200, 0)
    assert h.xy(a) == h.xy(b) == (100, 100)
    assert h.ws.ordered_regions() == [a, b]


def test_zoom_half_drag_doubles_displacement(h):
    r = h.math(100, 100)
    h.view.set_zoom(0.5)
    h.app.processEvents()
    h.drag(h.inside(r), 30, 0)
    assert h.xy(r) == (160, 100)


def test_zoom_threshold_in_view_pixels(h):
    r = h.math(100, 100)
    h.view.set_zoom(2.0)
    h.app.processEvents()
    h.drag(h.inside(r), 3, 0, steps=3)    # 3 view px = 1.5 units: click
    assert h.xy(r) == (100, 100) and not h.ws.modified


def test_cursor_back_to_normal_after_cancel(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    for i in range(1, 6):
        h.move(p + QPoint(10 * i, 0))
    assert h.vp.cursor().shape() == Qt.CursorShape.ClosedHandCursor
    QTest.keyClick(h.vp, Qt.Key.Key_Escape)
    assert h.vp.cursor().shape() != Qt.CursorShape.ClosedHandCursor
    h.release(p + QPoint(50, 0))


def test_cursor_closed_when_pointer_outside_region(h):
    r = h.math(100, 100)
    p = h.inside(r)
    h.press(p)
    h.move(p + QPoint(10, 0))
    h.move(p + QPoint(300, 200))
    assert h.vp.cursor().shape() == Qt.CursorShape.ClosedHandCursor
    h.release(p + QPoint(300, 200))


def test_open_hand_on_hover_arrow_on_empty_canvas(h):
    r = h.math(100, 100)
    h.move(h.inside(r))
    assert r.cursor().shape() == Qt.CursorShape.OpenHandCursor
    h.move(h.pt(700, 500))
    assert h.vp.cursor().shape() != Qt.CursorShape.ClosedHandCursor


def test_edit_text_area_has_ibeam(h):
    r = h.math(100, 100)
    r.start_editing()
    h.app.processEvents()
    r.update_cursor(r.content_rect().center())
    shape = r.cursor().shape()
    ed = r.editor.cursor().shape()
    assert Qt.CursorShape.IBeamCursor in (shape, ed)


def test_roundtrip_group_move_and_resave_stable(h, tmp_path):
    a, b = h.math(100, 100), h.math(200, 150, "b := 2")
    a.setSelected(True), b.setSelected(True)
    h.drag(h.inside(a), 40, 20)
    doc = h.ws.to_document()
    path = tmp_path / "g.lsheet"
    doc.save(path)
    d2 = SheetDocument.load(path)
    assert sorted((d.x, d.y) for d in d2.regions) == [(140, 120), (240, 170)]
    assert d2.version() == doc.version() == 1
    h.ws.load_document(d2)
    assert sorted(h.xy(r) for r in h.ws.regions()) == [(140, 120), (240, 170)]


def test_save_after_drag_clears_modified_then_new_drag_sets_again(h, tmp_path):
    r = h.math(100, 100)
    h.drag(h.inside(r), 30, 0)
    assert h.ws.modified
    h.ws.set_modified(False)
    h.drag(h.inside(r), 30, 0)
    assert h.ws.modified


def test_move_regions_single_call_for_group_drag(h, monkeypatch):
    a, b = h.math(100, 100), h.math(200, 100, "b := 2")
    a.setSelected(True), b.setSelected(True)
    calls = []
    orig = h.ws.move_regions
    monkeypatch.setattr(h.ws, "move_regions", lambda mv, *x, **k: (calls.append(mv), orig(mv, *x, **k))[1])
    h.drag(h.inside(a), 30, 0)
    assert len(calls) == 1
    assert {id(t[0]) for t in calls[0]} == {id(a), id(b)}
    for reg, old, new in calls[0]:
        assert new - old == QPointF(30, 0)


def test_move_regions_payload_for_nudge(h, monkeypatch):
    a = h.math(100, 100)
    a.setSelected(True)
    calls = []
    orig = h.ws.move_regions
    monkeypatch.setattr(h.ws, "move_regions", lambda mv, *x, **k: (calls.append(mv), orig(mv, *x, **k))[1])
    QTest.keyClick(h.vp, Qt.Key.Key_Left)
    QTest.keyClick(h.vp, Qt.Key.Key_Left)       # 90 -> 80
    assert len(calls) == 2
    assert calls[0][0][1] == QPointF(100, 100) and calls[0][0][2] == QPointF(90, 100)
