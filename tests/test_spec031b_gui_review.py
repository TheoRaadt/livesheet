"""Spec 031 phase B: interaction review tests driven through a real MainWindow with synthetic mouse,
wheel, key and context-menu events on the view's viewport (written from the spec only)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QEvent, QRectF, QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QContextMenuEvent, QKeyEvent, QMouseEvent, QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.plotregion import PlotRegion  # noqa: E402
from livesheet.gui.regions import MathRegion  # noqa: E402

SPEC = "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\nshow x + 2*y"
PLOT2D = "plot\nover x from 0 to 1\nshow x"
POS = (60, 60)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(1000, 760)
    w.show()
    app.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


class Mouse:
    """Synthetic pointer on the view viewport; coordinates are scene points."""

    def __init__(self, win):
        self.win = win
        self.vp = win.view.viewport()

    def vpos(self, scene_pt):
        return QPointF(self.win.view.mapFromScene(QPointF(*scene_pt)))

    def _send(self, kind, scene_pt, button=Qt.MouseButton.LeftButton, buttons=Qt.MouseButton.LeftButton,
              mods=Qt.KeyboardModifier.NoModifier):
        p = self.vpos(scene_pt)
        g = QPointF(self.vp.mapToGlobal(p.toPoint()))
        ev = QMouseEvent(kind, p, g, button, buttons, mods)
        QApplication.sendEvent(self.vp, ev)
        QApplication.processEvents()

    def press(self, pt):
        self._send(QEvent.Type.MouseButtonPress, pt)

    def move(self, pt, held=True):
        self._send(QEvent.Type.MouseMove, pt, Qt.MouseButton.NoButton,
                   Qt.MouseButton.LeftButton if held else Qt.MouseButton.NoButton)

    def release(self, pt):
        self._send(QEvent.Type.MouseButtonRelease, pt, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def dbl(self, pt):
        self._send(QEvent.Type.MouseButtonDblClick, pt)

    def drag(self, a, b, steps=4):
        self.press(a)
        for k in range(1, steps + 1):
            self.move((a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps))
        self.release(b)

    def wheel(self, scene_pt, delta, mods=Qt.KeyboardModifier.NoModifier):
        p = self.vpos(scene_pt)
        g = QPointF(self.vp.mapToGlobal(p.toPoint()))
        ev = QWheelEvent(p, g, QPoint(0, 0), QPoint(0, delta), Qt.MouseButton.NoButton, mods,
                         Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(self.vp, ev)
        QApplication.processEvents()


def add(win, text=SPEC, pos=POS, size=None):
    reg = win.sheet.add_region("plot", QPointF(*pos), text, size)
    win.sheet.recalculate()
    QApplication.processEvents()
    return reg


def at(reg, lx, ly):
    """Scene point of a region-local point."""
    return (reg.pos().x() + lx, reg.pos().y() + ly)


# ------------------------------------------------------------------ B1 / B2 rotate by mouse

def test_b1_rotate_right_and_up(win):
    reg, m = add(win), Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 140, 100))
    a, e, z = reg.effective_view()
    assert a == pytest.approx(60.0, abs=1e-9) and e == pytest.approx(30.0, abs=1e-9)
    m.drag(at(reg, 100, 100), at(reg, 100, 80))
    a, e, z = reg.effective_view()
    assert a == pytest.approx(60.0, abs=1e-9) and e == pytest.approx(40.0, abs=1e-9)
    assert z == pytest.approx(1.0)


def test_b0_press_in_chart_does_not_move_region(win):
    reg, m = add(win), Mouse(win)
    p0 = QPointF(reg.pos())
    m.drag(at(reg, 200, 130), at(reg, 230, 130))
    assert reg.pos() == p0
    assert reg.isSelected()


def test_b0_unselected_region_also_rotates_not_moves(win):
    reg, m = add(win), Mouse(win)
    win.sheet.clearSelection()
    assert not reg.isSelected()
    p0 = QPointF(reg.pos())
    m.drag(at(reg, 200, 130), at(reg, 240, 130))
    assert reg.pos() == p0
    assert reg.effective_view()[0] == pytest.approx(60.0, abs=1e-9)


def test_b2_clamp_and_wrap_by_mouse(win):
    reg, m = add(win), Mouse(win)
    reg.set_stored_view(40, 85, 1.0)
    m.drag(at(reg, 100, 100), at(reg, 100, 80))
    assert reg.effective_view()[1] == 90.0
    reg.set_stored_view(40, -85, 1.0)
    m.drag(at(reg, 100, 100), at(reg, 100, 120))
    assert reg.effective_view()[1] == -90.0
    reg.set_stored_view(175, 30, 1.0)
    m.drag(at(reg, 100, 100), at(reg, 120, 100))
    assert reg.effective_view()[0] == pytest.approx(-175.0, abs=1e-9)


def test_rotation_follows_screen_pixels_when_canvas_zoomed(win):
    win.view.set_zoom(2.0)
    QApplication.processEvents()
    reg, m = add(win), Mouse(win)
    # 20 scene units are 40 screen pixels -> 20 degrees
    m.drag(at(reg, 100, 100), at(reg, 120, 100))
    assert reg.effective_view()[0] == pytest.approx(60.0, abs=1e-6)


def test_path_independent_total_azimuth(win):
    """Wandering path with the same net displacement gives the same azimuth (no drift)."""
    reg, m = add(win), Mouse(win)
    m.press(at(reg, 100, 100))
    for pt in [(130, 100), (90, 100), (170, 100), (110, 100), (140, 100)]:
        m.move(at(reg, *pt))
    m.release(at(reg, 140, 100))
    assert reg.effective_view()[0] == pytest.approx(40 + 20.0, abs=1e-9)


def test_click_without_drag_changes_nothing(win):
    reg, m = add(win), Mouse(win)
    win.sheet.set_modified(False)
    m.press(at(reg, 100, 100))
    m.release(at(reg, 100, 100))
    assert not reg.has_stored_view()
    assert not win.sheet.modified
    assert reg.isSelected()
    assert not reg.rotating


def test_move_without_button_does_not_rotate(win):
    reg, m = add(win), Mouse(win)
    m.move(at(reg, 100, 100), held=False)
    m.move(at(reg, 150, 100), held=False)
    assert not reg.has_stored_view()


def test_rotating_flag_lifecycle(win):
    reg, m = add(win), Mouse(win)
    m.press(at(reg, 100, 100))
    m.move(at(reg, 110, 100))
    assert reg.rotating
    m.release(at(reg, 110, 100))
    assert not reg.rotating


def test_escape_mid_rotate_does_not_crash_and_flag_clears(win):
    """Spec does not define Esc for rotate; observed behaviour is recorded in the review."""
    reg, m = add(win), Mouse(win)
    m.press(at(reg, 100, 100))
    m.move(at(reg, 140, 100))
    QTest.keyClick(win.view.viewport(), Qt.Key.Key_Escape)
    m.release(at(reg, 140, 100))
    assert not reg.rotating
    assert -180 <= reg.effective_view()[0] < 180


def test_two_regions_independent_views(win):
    r1 = add(win, pos=(60, 60))
    r2 = add(win, pos=(60, 400))
    m = Mouse(win)
    m.drag(at(r1, 100, 100), at(r1, 140, 100))
    assert r1.has_stored_view() and not r2.has_stored_view()
    m.wheel(at(r2, 100, 100), 120)
    assert r2.effective_view()[2] == pytest.approx(1.1)
    assert r1.effective_view()[2] == pytest.approx(1.0)


def test_modified_flag_set_by_rotate_zoom_and_reset(win):
    reg, m = add(win), Mouse(win)
    win.sheet.set_modified(False)
    m.drag(at(reg, 100, 100), at(reg, 110, 100))
    assert win.sheet.modified
    win.sheet.set_modified(False)
    m.wheel(at(reg, 100, 100), 120)
    assert win.sheet.modified
    win.sheet.set_modified(False)
    reg.reset_view()
    assert win.sheet.modified
    win.sheet.set_modified(False)
    reg.reset_view()                     # nothing stored: not a modification
    assert not win.sheet.modified


# ------------------------------------------------------------------ B3 wheel

def test_b3_wheel_zoom_by_mouse(win):
    reg, m = add(win), Mouse(win)
    m.wheel(at(reg, 100, 100), 120)
    assert reg.effective_view()[2] == pytest.approx(1.1, abs=1e-9)
    m.wheel(at(reg, 100, 100), -120)
    assert reg.effective_view()[2] == pytest.approx(1.0, abs=1e-9)
    for _ in range(20):
        m.wheel(at(reg, 100, 100), 120)
    assert reg.effective_view()[2] == 4.0
    reg.reset_view()
    for _ in range(20):
        m.wheel(at(reg, 100, 100), -120)
    assert reg.effective_view()[2] == 0.25


def test_wheel_outside_chart_not_consumed(win):
    reg, m = add(win), Mouse(win)
    m.wheel((900, 650), 120)                 # empty canvas
    m.wheel(at(reg, -2, 100), 120)           # frame ring
    m.wheel(at(reg, 100, 280), 120)          # below the chart
    assert not reg.has_stored_view()


def test_wheel_on_other_region_does_not_zoom_plot(win):
    reg = add(win)
    mr = win.sheet.add_region("math", QPointF(60, 400), "a := 2")
    win.sheet.recalculate()
    Mouse(win).wheel((mr.pos().x() + 5, mr.pos().y() + 5), 120)
    assert not reg.has_stored_view()


def test_wheel_does_not_zoom_2d_plot(win):
    reg = add(win, PLOT2D)
    Mouse(win).wheel(at(reg, 100, 100), 120)
    assert not reg.has_stored_view()
    assert reg.view_zoom is None


def test_wheel_zero_delta_ignored(win):
    reg = add(win)
    Mouse(win).wheel(at(reg, 100, 100), 0)
    assert not reg.has_stored_view()


def test_ctrl_wheel_inside_chart_zooms_canvas_documented(win):
    """Spec silent on Ctrl+wheel inside a 3-D chart; recorded: the canvas zoom wins (no crash)."""
    reg, m = add(win), Mouse(win)
    z0 = win.view.zoom()
    m.wheel(at(reg, 100, 100), 120, Qt.KeyboardModifier.ControlModifier)
    assert win.view.zoom() >= z0
    assert reg.effective_view()[2] == pytest.approx(1.0)


# ------------------------------------------------------------------ ring / handle / hit-testing

def test_ring_move_selected(win):
    reg, m = add(win), Mouse(win)
    reg.setSelected(True)
    p0 = QPointF(reg.pos())
    m.drag(at(reg, -2, 100), (p0.x() - 2 + 40, p0.y() + 100 + 20))
    assert reg.pos().x() == pytest.approx(p0.x() + 40) and reg.pos().y() == pytest.approx(p0.y() + 20)
    assert not reg.has_stored_view()
    assert win.sheet.modified


def test_ring_move_not_yet_selected(win):
    reg, m = add(win), Mouse(win)
    win.sheet.clearSelection()
    assert not reg.isSelected()
    p0 = QPointF(reg.pos())
    m.drag(at(reg, -2, 100), (p0.x() - 2 + 30, p0.y() + 100))
    assert reg.pos().x() == pytest.approx(p0.x() + 30)
    assert not reg.has_stored_view()
    assert reg.isSelected()


@pytest.mark.parametrize("local", [(-5, 100), (200, -5), (405, 100), (200, 265), (-2, -2), (403, 263), (-1, 100),
                                   (200, -1)])
def test_ring_points_all_sides_move(win, local):
    reg, m = add(win), Mouse(win)
    p0 = QPointF(reg.pos())
    start = at(reg, *local)
    m.drag(start, (start[0] + 20, start[1] + 10))
    assert (reg.pos() - p0).x() == pytest.approx(20) and (reg.pos() - p0).y() == pytest.approx(10)
    assert not reg.has_stored_view()


def test_outside_ring_does_neither(win):
    reg, m = add(win), Mouse(win)
    p0 = QPointF(reg.pos())
    start = at(reg, -9, 100)               # 9 units outside the chart edge: beyond padding + grip
    m.drag(start, (start[0] + 30, start[1]))
    assert reg.pos() == p0
    assert not reg.has_stored_view()


def test_ring_move_esc_restores_position(win):
    reg, m = add(win), Mouse(win)
    p0 = QPointF(reg.pos())
    a = at(reg, -2, 100)
    m.press(a)
    for k in range(1, 5):
        m.move((a[0] + 10 * k, a[1]))
    assert reg.pos() != p0
    QTest.keyClick(win.view.viewport(), Qt.Key.Key_Escape)
    m.release((a[0] + 40, a[1]))
    assert reg.pos() == p0


def test_resize_handle_resizes_not_rotates_or_moves(win):
    reg, m = add(win), Mouse(win)
    reg.setSelected(True)
    p0, (w0, h0) = QPointF(reg.pos()), (reg.size_w, reg.size_h)
    m.drag(at(reg, w0 - 4, h0 - 4), at(reg, w0 - 4 + 60, h0 - 4 + 40))
    assert (reg.size_w, reg.size_h) == (w0 + 60, h0 + 40)
    assert reg.pos() == p0
    assert not reg.has_stored_view()


def test_resize_handle_unselected_3d(win):
    reg, m = add(win), Mouse(win)
    win.sheet.clearSelection()
    w0, h0 = reg.size_w, reg.size_h
    m.drag(at(reg, w0 - 4, h0 - 4), at(reg, w0 - 4 + 20, h0 - 4))
    assert reg.size_w == w0 + 20
    assert not reg.has_stored_view()


def test_just_inside_handle_boundary_rotates(win):
    reg, m = add(win), Mouse(win)
    w0, h0 = reg.size_w, reg.size_h
    m.drag(at(reg, w0 - 20, h0 - 20), at(reg, w0 - 20 + 10, h0 - 20))
    assert reg.has_stored_view() and (reg.size_w, reg.size_h) == (w0, h0)


def test_rotating_after_resize_uses_new_chart_rect(win):
    reg, m = add(win), Mouse(win)
    reg.set_size(600, 400)
    m.drag(at(reg, 550, 350), at(reg, 560, 350))
    assert reg.effective_view()[0] == pytest.approx(45.0)


def test_spec023_2d_plot_still_moves_from_inside(win):
    reg, m = add(win, PLOT2D), Mouse(win)
    p0 = QPointF(reg.pos())
    m.drag(at(reg, 200, 130), at(reg, 230, 150))
    assert (reg.pos() - p0).x() == pytest.approx(30) and (reg.pos() - p0).y() == pytest.approx(20)
    assert not reg.has_stored_view()


def test_spec023_2d_plot_resize_still_works(win):
    reg, m = add(win, PLOT2D), Mouse(win)
    reg.setSelected(True)
    w0, h0 = reg.size_w, reg.size_h
    m.drag(at(reg, w0 - 4, h0 - 4), at(reg, w0 + 36, h0 - 4))
    assert reg.size_w == w0 + 40


def test_spec023_math_region_still_moves(win):
    mr = win.sheet.add_region("math", QPointF(60, 300), "a := 2")
    win.sheet.recalculate()
    m = Mouse(win)
    p0 = QPointF(mr.pos())
    start = (p0.x() + 5, p0.y() + 5)
    m.drag(start, (start[0] + 30, start[1]))
    assert mr.pos().x() == pytest.approx(p0.x() + 30)


def test_empty_starter_3d_region_still_rotates_harmlessly(win):
    """Hint-state region (no surface): drag is a rotate session; no crash. Observation in the review."""
    reg = add(win, "surface\nover \nacross \nshow ")
    m = Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 120, 100))
    assert not reg.rotating


def test_error_state_3d_region_does_not_crash(win):
    reg = add(win, "surface\nover x from 0 to 1\nshow x")
    m = Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 120, 100))
    m.wheel(at(reg, 100, 100), 120)
    assert not reg.rotating


# ------------------------------------------------------------------ editing interplay

def test_double_click_in_chart_opens_editor(win):
    reg, m = add(win), Mouse(win)
    pt = at(reg, 200, 130)
    m.press(pt)
    m.release(pt)
    m.dbl(pt)
    m.release(pt)
    assert reg.editing
    assert not reg.has_stored_view()
    reg.finish_editing()


def test_double_click_then_drag_rotates_not_edit(win):
    reg, m = add(win), Mouse(win)
    a = at(reg, 200, 130)
    m.press(a)
    m.release(a)
    m.dbl(a)
    m.move((a[0] + 20, a[1]))
    m.release((a[0] + 20, a[1]))
    assert not reg.editing
    assert reg.effective_view()[0] == pytest.approx(50.0, abs=1e-9)


def test_double_click_on_ring_edits_or_nothing_no_crash(win):
    reg, m = add(win), Mouse(win)
    pt = at(reg, -2, 100)
    m.press(pt)
    m.release(pt)
    m.dbl(pt)
    m.release(pt)
    assert not reg.has_stored_view()
    if reg.editing:
        reg.finish_editing()


def test_editing_region_press_in_text_does_not_rotate(win):
    reg, m = add(win), Mouse(win)
    reg.start_editing()
    QApplication.processEvents()
    m.drag(at(reg, 60, 20), at(reg, 100, 20))
    assert not reg.has_stored_view()
    assert reg.editing
    reg.finish_editing()


def test_rotates_at_false_while_editing_and_for_2d(win):
    reg = add(win)
    assert reg.rotates_at(QPointF(100, 100))
    reg.start_editing()
    assert not reg.rotates_at(QPointF(100, 100))
    reg.finish_editing()
    two = add(win, PLOT2D, pos=(60, 400))
    assert not two.rotates_at(QPointF(100, 100))


def test_use_dialog_control_hidden_for_surface(win):
    reg = add(win)
    reg.start_editing()
    assert not reg._use_dialog_proxy.isVisible()
    reg.finish_editing()


def test_editing_commit_with_view_change_resets_after_rotate(win):
    """B6 through the real mouse + editor path."""
    reg, m = add(win, SPEC + "\nview 10 10"), Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 140, 100))
    assert reg.effective_view()[0] == pytest.approx(30.0)      # text view 10 + 20
    reg.start_editing()
    reg.editor.setPlainText(SPEC + "\nview 20 15")
    reg.finish_editing()
    win.sheet.recalculate()
    assert not reg.has_stored_view()
    assert reg.effective_view() == (20.0, 15.0, 1.0)


# ------------------------------------------------------------------ B5 context menu

def _context(win, scene_pt, pick):
    """Open the real context menu at ``scene_pt``; ``pick`` is the entry text to trigger (None = Esc).
    Returns the list of entry texts."""
    seen = []

    def drive():
        menu = QApplication.activePopupWidget()
        assert menu is not None
        acts = [a for a in menu.actions() if a.text()]
        seen.extend(a.text() for a in acts)
        target = next((a for a in acts if a.text() == pick), None)
        if target is None:
            QTest.keyClick(menu, Qt.Key.Key_Escape)
        else:
            menu.setActiveAction(target)
            QTest.keyClick(menu, Qt.Key.Key_Enter)

    QTimer.singleShot(0, drive)
    vp = win.view.viewport()
    p = win.view.mapFromScene(QPointF(*scene_pt))
    ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, p, vp.mapToGlobal(p))
    QApplication.sendEvent(vp, ev)
    QApplication.processEvents()
    return seen


def test_b5_reset_entry_removes_stored_view(win):
    reg = add(win, SPEC + "\nview 10 10")
    reg.set_stored_view(60, 40, 1.1)
    seen = _context(win, at(reg, 200, 130), "Reset 3-D view")
    assert "Reset 3-D view" in seen
    assert not reg.has_stored_view()
    assert reg.effective_view() == (10.0, 10.0, 1.0)


def test_b5_reset_without_text_view_goes_to_default(win):
    reg = add(win)
    reg.set_stored_view(-100, -20, 3.0)
    _context(win, at(reg, 200, 130), "Reset 3-D view")
    assert reg.effective_view() == (40.0, 30.0, 1.0)


def test_b5_entry_present_even_without_stored_view_and_on_ring(win):
    reg = add(win)
    assert "Reset 3-D view" in _context(win, at(reg, 200, 130), None)
    assert "Reset 3-D view" in _context(win, at(reg, -2, 100), None)


def test_b5_entry_absent_for_2d_math_and_canvas(win):
    two = add(win, PLOT2D, pos=(60, 400))
    mr = win.sheet.add_region("math", QPointF(500, 60), "a := 2")
    win.sheet.recalculate()
    assert "Reset 3-D view" not in _context(win, at(two, 200, 100), None)
    assert "Reset 3-D view" not in _context(win, (mr.pos().x() + 5, mr.pos().y() + 5), None)
    assert "Reset 3-D view" not in _context(win, (800, 600), None)


def test_b5_dismissing_menu_keeps_view(win):
    reg = add(win)
    reg.set_stored_view(60, 40, 1.1)
    _context(win, at(reg, 200, 130), None)
    assert reg.effective_view() == (60.0, 40.0, 1.1)


# ------------------------------------------------------------------ B9 drag preview

@pytest.fixture
def modes(monkeypatch):
    import livesheet.gui.surfaceview as sv
    seen = []
    real = sv.layout_surface

    def spy(data, rect, az, el, zoom, mode):
        seen.append(mode)
        return real(data, rect, az, el, zoom, mode)

    monkeypatch.setattr(sv, "layout_surface", spy)
    return seen


def grid_spec(n, draw=""):
    return (f"surface\nover x from 0 to 1 points {n}\nacross y from 0 to 1 points {n}\nshow x*y"
            + (f"\ndraw {draw}" if draw else ""))


def repaint(win):
    # Paint the scene the way the window does (not printing): render it into an image.
    img = QImage(700, 500, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    win.sheet.render(p, QRectF(0, 0, 700, 500), QRectF(0, 0, 700, 500))
    p.end()


def test_b9_large_grid_wire_during_drag_then_mesh(win, modes):
    reg, m = add(win, grid_spec(60)), Mouse(win)
    repaint(win)
    modes.clear()
    m.press(at(reg, 100, 100))
    m.move(at(reg, 110, 100))
    repaint(win)
    assert modes and set(modes) == {"wire"}, modes
    modes.clear()
    m.release(at(reg, 110, 100))
    repaint(win)
    assert modes and set(modes) == {"mesh"}, modes


def test_b9_release_uses_regions_wire_draw_mode(win, modes):
    reg, m = add(win, grid_spec(60, "wire")), Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 110, 100))
    modes.clear()
    repaint(win)
    assert set(modes) == {"wire"}


def test_b9_small_grid_keeps_mesh_during_drag(win, modes):
    reg, m = add(win, grid_spec(25)), Mouse(win)
    repaint(win)
    m.press(at(reg, 100, 100))
    m.move(at(reg, 110, 100))
    modes.clear()
    repaint(win)
    assert modes and set(modes) == {"mesh"}, modes
    m.release(at(reg, 110, 100))


def test_b9_wheel_zoom_is_not_a_drag_preview(win, modes):
    reg, m = add(win, grid_spec(60)), Mouse(win)
    modes.clear()
    m.wheel(at(reg, 100, 100), 120)
    repaint(win)
    assert modes and set(modes) == {"mesh"}


@pytest.mark.parametrize("n,wire", [(40, False), (41, True), (42, True)])
def test_b9_boundary_points_vs_cells_observation(win, modes, n, wire):
    """Spec: 'more than 40 cells per axis'. n points = n-1 cells, so strictly 41 points (40 cells) should
    stay mesh and 42 points should switch. Observed: switches at 41 points (see review, defect 031B-4)."""
    reg, m = add(win, grid_spec(n)), Mouse(win)
    repaint(win)
    m.press(at(reg, 100, 100))
    m.move(at(reg, 110, 100))
    modes.clear()
    repaint(win)
    got_wire = set(modes) == {"wire"}
    m.release(at(reg, 110, 100))
    if n == 41:
        pytest.xfail("DEFECT 031B-4 (ambiguity): 41 points = 40 cells switches to wire") if got_wire else None
    assert got_wire == wire


# ------------------------------------------------------------------ B4 / B10 save + reopen through the window

def test_b4_save_reopen_via_window(win, tmp_path):
    reg, m = add(win), Mouse(win)
    m.drag(at(reg, 100, 100), at(reg, 140, 100))
    m.drag(at(reg, 100, 100), at(reg, 100, 80))
    m.wheel(at(reg, 100, 100), 120)
    path = tmp_path / "b4.lsheet"
    win.sheet.to_document().save(path)
    win2 = MainWindow()
    try:
        win2.open_path(path)
        QApplication.processEvents()
        (r2,) = [r for r in win2.sheet.regions() if isinstance(r, PlotRegion)]
        assert r2.view_az == pytest.approx(60.0) and r2.view_el == pytest.approx(40.0)
        assert r2.view_zoom == pytest.approx(1.1)
        # rotating the reopened region continues from the stored view
        m2 = Mouse(win2)
        win2.show()
        QApplication.processEvents()
        m2.drag(at(r2, 100, 100), at(r2, 120, 100))
        assert r2.effective_view()[0] == pytest.approx(70.0)
    finally:
        win2.sheet.set_modified(False)
        win2.close()


def test_stored_view_survives_move_by_ring_and_recalc(win):
    reg, m = add(win), Mouse(win)
    reg.set_stored_view(60, 40, 1.1)
    m.drag(at(reg, -2, 100), at(reg, 28, 100))
    win.sheet.recalculate()
    assert reg.effective_view() == (60.0, 40.0, 1.1)


def test_changing_input_above_updates_surface_keeps_view(win):
    win.sheet.add_region("math", QPointF(60, 20), "k := 2")
    reg = add(win, "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\nshow k*x + y",
              pos=(60, 100))
    reg.set_stored_view(60, 40, 1.1)
    win.sheet.recalculate()
    z1 = reg.result.surface.zs
    mr = [r for r in win.sheet.regions() if isinstance(r, MathRegion)][0]
    mr.start_editing()
    mr.editor.setPlainText("k := 5")
    mr.finish_editing()
    win.sheet.recalculate()
    assert reg.result.surface.zs != z1
    assert reg.effective_view() == (60.0, 40.0, 1.1)
    assert Engine  # silence unused import
