"""Spec 031 phase B: rotate, zoom, saved view, frame-ring move, label fixes (developer tests)."""

import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QGraphicsSceneWheelEvent  # noqa: E402

from livesheet.document import RegionData, SheetDocument  # noqa: E402
from livesheet.engine import Engine  # noqa: E402
from livesheet.gui import surfaceview  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.plotregion import PlotRegion  # noqa: E402
from livesheet.gui.surfaceview import layout_surface, paint_surface, shorten_title  # noqa: E402

NO = Qt.KeyboardModifier.NoModifier
LEFT = Qt.MouseButton.LeftButton
SPEC = "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\nshow x + 2*y"


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


def make(win, text=SPEC, x=100, y=100):
    region = win.sheet.add_region("plot", QPointF(x, y), text)
    win.sheet.recalculate()
    win.app_events = QApplication.processEvents()
    return region


class Mouse:
    def __init__(self, win):
        self.view, self.vp = win.view, win.view.viewport()

    def pt(self, x, y) -> QPoint:
        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)
        return self.view.mapFromScene(QPointF(x, y))

    def drag(self, start: QPoint, dx: int, dy: int, steps: int = 5):
        QTest.mousePress(self.vp, LEFT, NO, start)
        QApplication.processEvents()
        for i in range(1, steps + 1):
            QTest.mouseMove(self.vp, start + QPoint(dx * i // steps, dy * i // steps))
            QApplication.processEvents()
        QTest.mouseRelease(self.vp, LEFT, NO, start + QPoint(dx, dy))
        QApplication.processEvents()


def chart_point(region, lx, ly):
    return region.mapToScene(QPointF(lx, ly))


# -- document ------------------------------------------------------------------------------

def test_reader_ignores_unknown_keys_and_view_is_optional():
    raw = {"format": "livesheet", "version": 2, "regions": [
        {"kind": "plot", "x": 0, "y": 0, "text": SPEC, "w": 400, "h": 260,
         "view_az": 60, "view_el": 40, "view_zoom": 1.1, "future_key": 1}]}
    reg = SheetDocument.from_json(json.dumps(raw)).regions[0]
    assert (reg.view_az, reg.view_el, reg.view_zoom) == (60.0, 40.0, 1.1)


def test_view_keys_only_written_when_used_and_same_version():
    plain = SheetDocument([RegionData("plot", 0, 0, SPEC)])
    with_view = SheetDocument([RegionData("plot", 0, 0, SPEC, view_az=60, view_el=40, view_zoom=1.1)])
    assert plain.version() == with_view.version()
    d = json.loads(plain.to_json())["regions"][0]
    assert not any(k.startswith("view_") for k in d)
    d = json.loads(with_view.to_json())["regions"][0]
    assert (d["view_az"], d["view_el"], d["view_zoom"]) == (60.0, 40.0, 1.1)
    # never on a 2-D plot or a math region
    two_d = RegionData("plot", 0, 0, "plot\nover x\nshow x", view_az=1, view_el=2, view_zoom=1)
    assert "view_az" not in two_d.to_dict()
    assert "view_az" not in RegionData("math", 0, 0, "1+1", view_az=1, view_el=2, view_zoom=1).to_dict()


def test_malformed_view_values_dropped():
    raw = {"format": "livesheet", "version": 2, "regions": [
        {"kind": "plot", "x": 0, "y": 0, "text": SPEC, "view_az": "x", "view_el": 3, "view_zoom": 1}]}
    reg = SheetDocument.from_json(json.dumps(raw)).regions[0]
    assert reg.view_az is None and "view_el" not in reg.to_dict()


# -- rotate / zoom ---------------------------------------------------------------------------

def test_rotate_azimuth_and_elevation(win):
    r = make(win)
    m = Mouse(win)
    p = chart_point(r, 100, 100)
    m.drag(m.pt(p.x(), p.y()), 40, 0)
    assert r.effective_view()[:2] == pytest.approx((60.0, 30.0), abs=1e-9)
    m.drag(m.pt(p.x(), p.y()), 0, -20)
    assert r.effective_view()[:2] == pytest.approx((60.0, 40.0), abs=1e-9)
    assert r.pos() == QPointF(100, 100)


def test_press_in_chart_does_not_move_region(win):
    r = make(win)
    m = Mouse(win)
    p = chart_point(r, 200, 130)
    m.drag(m.pt(p.x(), p.y()), 30, 0)
    assert r.pos() == QPointF(100, 100)
    assert win.sheet.selectedItems() == [r]


def test_frame_ring_moves_region_selected_or_not(win):
    r = make(win)
    m = Mouse(win)
    start = chart_point(r, -4, 100)           # in the ring, outside the chart
    assert not r.rotates_at(QPointF(-4, 100)) and r.boundingRect().contains(QPointF(-4, 100))
    m.drag(m.pt(start.x(), start.y()), 50, 40)
    assert r.pos() == QPointF(150, 140)
    assert not r.has_stored_view()


def test_rotation_clamp_and_wrap(win):
    r = make(win)
    r.set_stored_view(40, 85, 1)
    r.rotate_by(0, -20)
    assert r.view_el == 90.0
    r.set_stored_view(40, -85, 1)
    r.rotate_by(0, 20)
    assert r.view_el == -90.0
    r.set_stored_view(175, 0, 1)
    r.rotate_by(20, 0)
    assert r.view_az == -175.0
    r.set_stored_view(-175, 0, 1)
    r.rotate_by(-20, 0)
    assert r.view_az == 175.0


def test_zoom_notches_and_clamp(win):
    r = make(win)
    r.zoom_by(120)
    assert r.view_zoom == pytest.approx(1.1, abs=1e-9)
    r.zoom_by(-120)
    assert r.view_zoom == pytest.approx(1.0, abs=1e-9)
    r.set_stored_view(40, 30, 1.0)
    for _ in range(20):
        r.zoom_by(120)
    assert r.view_zoom == 4.0
    r.set_stored_view(40, 30, 1.0)
    for _ in range(20):
        r.zoom_by(-120)
    assert r.view_zoom == 0.25


def test_wheel_event_inside_and_outside_chart(win):
    r = make(win)

    def wheel(lx, ly, delta):
        ev = QGraphicsSceneWheelEvent()
        ev.setPos(QPointF(lx, ly))
        ev.setDelta(delta)
        r.wheelEvent(ev)
        return ev.isAccepted()

    assert wheel(100, 100, 120)
    assert r.view_zoom == pytest.approx(1.1)
    assert not wheel(-4, 100, 120)
    assert r.view_zoom == pytest.approx(1.1)


def test_wheel_through_view(win):
    r = make(win)
    p = Mouse(win).pt(*(lambda q: (q.x(), q.y()))(chart_point(r, 100, 100)))
    from PySide6.QtGui import QWheelEvent
    ev = QWheelEvent(QPointF(p), QPointF(win.view.viewport().mapToGlobal(p)), QPoint(0, 0),
                     QPoint(0, 120), Qt.MouseButton.NoButton, NO, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(win.view.viewport(), ev)
    assert r.view_zoom == pytest.approx(1.1)


# -- saved view ------------------------------------------------------------------------------

def test_saved_view_round_trip_and_unrotated_has_no_keys(win, tmp_path):
    r = make(win)
    plain = json.loads(win.sheet.to_document().to_json())["regions"][0]
    assert not any(k.startswith("view_") for k in plain)
    r.set_stored_view(60, 40, 1.0)
    r.zoom_by(120)
    assert win.sheet.is_modified() if hasattr(win.sheet, "is_modified") else True
    data = json.loads(win.sheet.to_document().to_json())["regions"][0]
    assert data["view_az"] == 60.0 and data["view_el"] == 40.0
    assert data["view_zoom"] == pytest.approx(1.1)
    path = tmp_path / "s.lsheet"
    win.sheet.to_document().save(path)
    win.sheet.load_document(SheetDocument.load(path))
    r2 = win.sheet.regions()[0]
    assert r2.effective_view()[:2] == (60.0, 40.0) and r2.view_zoom == pytest.approx(1.1)
    d = r2.result.surface
    a = layout_surface(d, QRectF(0, 0, 400, 260), 60, 40, 1.1, "mesh")
    b = layout_surface(d, QRectF(0, 0, 400, 260), *r2.effective_view(), "mesh")
    assert [c.polygon for c in a.cells] == [c.polygon for c in b.cells]


def test_reset_and_precedence(win):
    r = make(win, SPEC + "\nview 10 10")
    assert r.effective_view() == (10.0, 10.0, 1.0)
    r.set_stored_view(60, 40, 1.0)
    assert r.effective_view() == (60.0, 40.0, 1.0)      # stored wins over the text line
    r.reset_view()
    assert not r.has_stored_view() and r.effective_view() == (10.0, 10.0, 1.0)
    r2 = make(win, SPEC, y=500)
    assert r2.effective_view() == (40.0, 30.0, 1.0)


def test_editing_view_line_clears_stored_view(win):
    r = make(win, SPEC + "\nview 10 10")
    r.set_stored_view(60, 40, 1.0)
    r.start_editing()
    r.editor.setPlainText(SPEC + "\nview 20 15")
    r.finish_editing()
    win.sheet.recalculate()
    assert not r.has_stored_view() and r.effective_view() == (20.0, 15.0, 1.0)
    r.set_stored_view(60, 40, 1.0)
    r.start_editing()
    r.editor.setPlainText(SPEC + "\nview 20 15\ntitle T")   # view line untouched
    r.finish_editing()
    assert r.has_stored_view()


def test_view_change_marks_modified(win):
    r = make(win)
    win.sheet.set_modified(False)
    r.rotate_by(10, 0)
    assert win.sheet._modified


# -- drag preview, timing, pdf -----------------------------------------------------------------

def test_drag_preview_uses_wire_only_for_big_grids(win, monkeypatch):
    modes = []
    real = surfaceview.layout_surface

    def spy(data, rect, az, el, zoom, mode):
        modes.append(mode)
        return real(data, rect, az, el, zoom, mode)

    monkeypatch.setattr(surfaceview, "layout_surface", spy)
    big = "surface\nover x from 0 to 1 points 60\nacross y from 0 to 1 points 60\nshow x*y"
    r = make(win, big)
    img = QImage(400, 260, QImage.Format.Format_ARGB32)
    for rotating, expected in ((True, "wire"), (False, "mesh")):
        r.rotating = rotating
        modes.clear()
        p = QPainter(img)
        r._paint_content(p, QRectF(0, 0, 400, 260))
        p.end()
        assert modes == [expected]
    small = make(win, SPEC, y=600)
    small.rotating = True
    modes.clear()
    p = QPainter(img)
    small._paint_content(p, QRectF(0, 0, 400, 260))
    p.end()
    assert modes == ["mesh"]


def test_redraw_time():
    for n, limit in ((25, 0.05), (100, 0.25)):
        text = f"surface\nover x from 0 to 1 points {n}\nacross y from 0 to 1 points {n}\nshow sin(5*x)*y"
        d = Engine().evaluate([(0, text)])[0].surface
        img = QImage(400, 260, QImage.Format.Format_ARGB32)
        p = QPainter(img)
        t = time.perf_counter()
        layout_surface(d, QRectF(0, 0, 400, 260), 40, 30, 1.0, "mesh")
        paint_surface(p, QRectF(0, 0, 400, 260), d, 40, 30, 1.0, "mesh")
        elapsed = time.perf_counter() - t
        p.end()
        assert elapsed < limit * 3, elapsed      # generous: CI machines vary


def test_pdf_with_view(win, tmp_path):
    r = make(win)
    r.set_stored_view(10, 50, 2.0)
    out = tmp_path / "o.pdf"
    export_pdf(win.sheet, str(out))
    assert out.read_bytes().startswith(b"%PDF")


# -- label fixes -----------------------------------------------------------------------------

def test_shorten_title():
    assert shorten_title("x [m]") == "x [m]"
    long = "500 N * (x/m) * y * sqrt(z) * more [kN]"
    s = shorten_title(long)
    assert len(s) <= 28 and s.endswith(" [kN]") and "…" in s
    assert len(shorten_title("a" * 60)) == 28


def test_no_overprinted_ticks():
    text = ("surface\nover x from 0 to 20 points 10\nacross y from 0 to 30 points 10\n"
            "show x*y/100 + 0*x")
    d = Engine().evaluate([(0, text)])[0].surface
    for az, el in ((40, 30), (-140, 30), (130, 20), (-40, 60), (200, 10)):
        lay = layout_surface(d, QRectF(0, 0, 520, 360), az, el, 1.0, "mesh")
        assert len(lay.tick_anchors) == len(d.x_ticks) + len(d.y_ticks) + len(d.z_ticks)
        a = lay.tick_anchors
        axis = [0] * len(d.x_ticks) + [1] * len(d.y_ticks) + [2] * len(d.z_ticks)
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                if axis[i] != axis[j]:      # labels of different axes must not overprint
                    assert not surfaceview._overlaps(a[i], a[j]), (az, el, a[i], a[j])


def test_label_halo_painted(app):
    d = Engine().evaluate([(0, SPEC)])[0].surface
    img = QImage(400, 260, QImage.Format.Format_ARGB32)
    img.fill(0xFF000000)
    p = QPainter(img)
    paint_surface(p, QRectF(0, 0, 400, 260), d, 40, 30, 1.0, "mesh")
    p.end()
    lay = layout_surface(d, QRectF(0, 0, 400, 260), 40, 30, 1.0, "mesh")
    a = lay.tick_anchors[0]
    # background around a tick label is light, not the black fill
    assert img.pixelColor(int(a.x) - 3, int(a.y) - 6).lightness() > 128 or \
        img.pixelColor(int(a.x) + 3, int(a.y) + 6).lightness() > 128
