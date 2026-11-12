"""Spec 031 phase B: independent black-box review tests (view maths, saved view, document format,
layout, performance, PDF). Written from the spec text only; GUI event driving is in
test_spec031b_gui_review.py."""

import json
import math
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPointF, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.document import DocumentError, RegionData, SheetDocument  # noqa: E402
from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.plotregion import PlotRegion  # noqa: E402
from livesheet.gui.surfaceview import layout_surface, paint_surface  # noqa: E402

SPEC = "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\nshow x + 2*y"
RECT = QRectF(0, 0, 400, 260)


def data(text=SPEC):
    r = Engine().evaluate([(0, text)])[0]
    assert r.status == "ok", r.error
    return r.surface


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    app.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


def make(win, text=SPEC, pos=(60, 60)):
    reg = win.sheet.add_region("plot", QPointF(*pos), text)
    win.sheet.recalculate()
    return reg


def regions_json(win):
    return json.loads(win.sheet.to_document().to_json())["regions"]


# ------------------------------------------------------------------ rotate maths (region API)

@pytest.mark.parametrize("dx,dy,az,el", [
    (40, 0, 60.0, 30.0),          # B1: right 40 px -> +20 deg
    (0, -20, 40.0, 40.0),         # B1: up 20 px -> +10 deg
    (-40, 0, 20.0, 30.0),
    (0, 20, 40.0, 20.0),
    (10, 10, 45.0, 25.0),
    (1, 0, 40.5, 30.0),           # 0.5 deg per pixel
    (0, 0, 40.0, 30.0),
])
def test_rotate_degrees_per_pixel(app, dx, dy, az, el):
    r = PlotRegion(SPEC)
    r.rotate_by(dx, dy)
    a, e, z = r.effective_view()
    assert a == pytest.approx(az, abs=1e-9)
    assert e == pytest.approx(el, abs=1e-9)
    assert z == pytest.approx(1.0, abs=1e-9)


def test_rotate_fractional_pixels(app):
    r = PlotRegion(SPEC)
    r.rotate_by(0.5, -0.25)
    a, e, _ = r.effective_view()
    assert a == pytest.approx(40.25, abs=1e-9) and e == pytest.approx(30.125, abs=1e-9)


def test_elevation_clamp_top_and_bottom(app):
    r = PlotRegion(SPEC)
    r.set_stored_view(40, 85, 1.0)
    r.rotate_by(0, -20)
    assert r.effective_view()[1] == 90.0
    r.set_stored_view(40, -85, 1.0)
    r.rotate_by(0, 20)
    assert r.effective_view()[1] == -90.0
    r.rotate_by(0, 1000)
    assert r.effective_view()[1] == -90.0
    r.rotate_by(0, -100000)
    assert r.effective_view()[1] == 90.0


@pytest.mark.parametrize("start,dx,expected", [
    (175.0, 20, -175.0),          # B2
    (-175.0, -20, 175.0),
    (179.0, 2, -180.0),           # [-180, 180): 180 maps to -180
    (-180.0, -2, 179.0),
    (0.0, 720, 0.0),              # a full turn
])
def test_azimuth_wrap(app, start, dx, expected):
    r = PlotRegion(SPEC)
    r.set_stored_view(start, 30, 1.0)
    r.rotate_by(dx, 0)
    got = r.effective_view()[0]
    assert -180.0 <= got < 180.0
    assert got == pytest.approx(expected, abs=1e-9)


def test_azimuth_always_in_half_open_range_after_many_steps(app):
    r = PlotRegion(SPEC)
    for k in range(-50, 50):
        r.rotate_by(37.3 * k, 0)
        assert -180.0 <= r.effective_view()[0] < 180.0


def test_text_view_line_az_outside_range_is_wrapped_on_rotate(app):
    r = PlotRegion(SPEC + "\nview 190 20")
    r.set_result(Engine().evaluate([(0, r.source)])[0])
    assert r.effective_view()[:2] == (190.0, 20.0)
    r.rotate_by(2, 0)
    assert r.effective_view()[0] == pytest.approx(-169.0, abs=1e-9)
    assert r.effective_view()[1] == pytest.approx(20.0, abs=1e-9)


def test_rotate_keeps_zoom_and_zoom_keeps_angles(app):
    r = PlotRegion(SPEC)
    r.set_stored_view(10, 20, 2.5)
    r.rotate_by(4, 4)
    a, e, z = r.effective_view()
    assert z == 2.5 and (a, e) == (pytest.approx(12.0), pytest.approx(18.0))
    r.zoom_by(120)
    a2, e2, z2 = r.effective_view()
    assert (a2, e2) == (pytest.approx(a), pytest.approx(e))
    assert z2 == pytest.approx(2.75)


# ------------------------------------------------------------------ zoom maths

def test_zoom_notch_values(app):
    r = PlotRegion(SPEC)
    r.zoom_by(120)
    assert r.effective_view()[2] == pytest.approx(1.1, abs=1e-9)
    r.zoom_by(-120)
    assert r.effective_view()[2] == pytest.approx(1.0, abs=1e-9)


def test_zoom_clamp_exact(app):
    up = PlotRegion(SPEC)
    for _ in range(20):
        up.zoom_by(120)
    assert up.effective_view()[2] == 4.0
    down = PlotRegion(SPEC)
    for _ in range(20):
        down.zoom_by(-120)
    assert down.effective_view()[2] == 0.25


def test_zoom_ten_up_ten_down_returns(app):
    r = PlotRegion(SPEC)
    for _ in range(10):
        r.zoom_by(120)
    assert r.effective_view()[2] == pytest.approx(1.1 ** 10, abs=1e-9)
    for _ in range(10):
        r.zoom_by(-120)
    assert r.effective_view()[2] == pytest.approx(1.0, abs=1e-9)


def test_zoom_fractional_and_multi_notch_delta(app):
    r = PlotRegion(SPEC)
    r.zoom_by(15)                       # trackpad-sized delta
    assert r.effective_view()[2] == pytest.approx(1.1 ** (15 / 120), abs=1e-9)
    r2 = PlotRegion(SPEC)
    r2.zoom_by(240)                     # two notches in one event
    assert r2.effective_view()[2] == pytest.approx(1.21, abs=1e-9)


def test_zoom_zero_delta_no_change(app):
    r = PlotRegion(SPEC)
    r.zoom_by(0)
    assert r.effective_view()[2] == pytest.approx(1.0)


# ------------------------------------------------------------------ signals / reset / precedence

def test_view_changed_signal_emitted_and_reset_semantics(app):
    r = PlotRegion(SPEC)
    n = []
    r.viewChanged.connect(lambda: n.append(1))
    r.reset_view()                      # nothing stored: no signal
    assert n == []
    r.rotate_by(2, 0)
    r.zoom_by(120)
    assert len(n) == 2 and r.has_stored_view()
    r.reset_view()
    assert len(n) == 3 and not r.has_stored_view()
    assert r.effective_view() == (40.0, 30.0, 1.0)


def test_reset_falls_back_to_view_line(app):
    r = PlotRegion(SPEC + "\nview 10 10")
    r.set_result(Engine().evaluate([(0, r.source)])[0])
    r.set_stored_view(60, 40, 1.1)
    assert r.effective_view() == (60.0, 40.0, 1.1)       # stored wins (B6)
    r.reset_view()
    assert r.effective_view() == (10.0, 10.0, 1.0)


def test_edit_view_line_clears_stored_other_edit_keeps(win):
    reg = make(win, SPEC + "\nview 10 10")
    reg.set_stored_view(60, 40, 1.1)
    # editing a different line keeps the stored view
    reg.start_editing()
    reg.editor.setPlainText(reg.source.replace("show x + 2*y", "show x + 3*y"))
    reg.finish_editing()
    assert reg.has_stored_view()
    # committing with no change at all keeps it
    reg.start_editing()
    reg.finish_editing()
    assert reg.has_stored_view()
    # changing the view line clears it
    reg.start_editing()
    reg.editor.setPlainText(reg.source.replace("view 10 10", "view 20 15"))
    reg.finish_editing()
    assert not reg.has_stored_view()
    win.sheet.recalculate()
    assert reg.effective_view() == (20.0, 15.0, 1.0)


def test_removing_or_adding_view_line_clears_stored(win):
    reg = make(win, SPEC + "\nview 10 10")
    reg.set_stored_view(60, 40, 1.1)
    reg.start_editing()
    reg.editor.setPlainText(SPEC)
    reg.finish_editing()
    assert not reg.has_stored_view()
    win.sheet.recalculate()
    reg.set_stored_view(60, 40, 1.1)
    reg.start_editing()
    reg.editor.setPlainText(SPEC + "\nview 5 5")
    reg.finish_editing()
    assert not reg.has_stored_view()


def test_recalculation_does_not_clear_stored_view(win):
    reg = make(win)
    reg.set_stored_view(60, 40, 1.1)
    for _ in range(3):
        win.sheet.recalculate()
    assert reg.effective_view() == (60.0, 40.0, 1.1)


def test_resize_keeps_stored_view(win):
    reg = make(win)
    reg.set_stored_view(60, 40, 1.1)
    reg.set_size(500, 300)
    assert reg.effective_view() == (60.0, 40.0, 1.1)


def test_text_change_to_2d_not_written(win):
    reg = make(win)
    reg.set_stored_view(60, 40, 1.1)
    reg.start_editing()
    reg.editor.setPlainText("plot\nover x from 0 to 1\nshow x")
    reg.finish_editing()
    win.sheet.recalculate()
    d = regions_json(win)
    assert all("view_az" not in r for r in d)


# ------------------------------------------------------------------ .lsheet format

def test_never_rotated_writes_no_keys(win):
    make(win)
    for r in regions_json(win):
        assert not any(k.startswith("view_") for k in r)


def test_saved_keys_values_b4(win):
    reg = make(win)
    reg.rotate_by(40, 0)
    reg.rotate_by(0, -20)
    reg.zoom_by(120)
    (r,) = regions_json(win)
    assert r["view_az"] == pytest.approx(60.0) and r["view_el"] == pytest.approx(40.0)
    assert r["view_zoom"] == pytest.approx(1.1)
    assert all(isinstance(r[k], float) for k in ("view_az", "view_el", "view_zoom"))


def test_zoom_only_writes_all_three_keys(win):
    reg = make(win)
    reg.zoom_by(120)
    (r,) = regions_json(win)
    assert r["view_az"] == 40.0 and r["view_el"] == 30.0 and r["view_zoom"] == pytest.approx(1.1)


def test_version_identical_with_and_without_keys():
    a = SheetDocument(regions=[RegionData("plot", 0, 0, SPEC, 400, 260)])
    b = SheetDocument(regions=[RegionData("plot", 0, 0, SPEC, 400, 260,
                                          view_az=60.0, view_el=40.0, view_zoom=1.1)])
    ja, jb = json.loads(a.to_json()), json.loads(b.to_json())
    assert ja["version"] == jb["version"]
    two_d = SheetDocument(regions=[RegionData("plot", 0, 0, "plot\nover x from 0 to 1\nshow x", 400, 260)])
    assert json.loads(two_d.to_json())["version"] == ja["version"]


def test_round_trip_through_json_and_layout_equal(win, tmp_path):
    reg = make(win)
    reg.rotate_by(40, 0)
    reg.rotate_by(0, -20)
    reg.zoom_by(120)
    path = tmp_path / "v.lsheet"
    win.sheet.to_document().save(path)
    win2 = MainWindow()
    try:
        win2.open_path(path)
        QApplication.processEvents()
        (reg2,) = [r for r in win2.sheet.regions() if isinstance(r, PlotRegion)]
        win2.sheet.recalculate()
        assert reg2.effective_view() == pytest.approx(reg.effective_view())
        d1, d2 = reg.result.surface, reg2.result.surface
        l1 = layout_surface(d1, RECT, *reg.effective_view(), "mesh")
        l2 = layout_surface(d2, RECT, *reg2.effective_view(), "mesh")
        assert [c.polygon for c in l1.cells] == [c.polygon for c in l2.cells]
        assert l1.box_edges == l2.box_edges
        assert not win2.sheet.modified
    finally:
        win2.sheet.set_modified(False)
        win2.close()


def test_reload_then_resave_is_stable(tmp_path):
    doc = SheetDocument(regions=[RegionData("plot", 0.0, 0.0, SPEC, 400.0, 260.0,
                                            view_az=-170.25, view_el=-12.5, view_zoom=0.25)])
    t1 = doc.to_json()
    t2 = SheetDocument.from_json(t1).to_json()
    assert t1 == t2


def test_old_sheet_byte_identical_resave():
    """A sheet without view keys (the shipped demo) re-saves idempotently and gains no key."""
    src = os.path.join(os.path.dirname(__file__), "..", "examples", "demo.lsheet")
    text = open(src, encoding="utf-8").read()
    out = SheetDocument.from_json(text).to_json()
    assert not any(k in out for k in ("view_az", "view_el", "view_zoom"))
    assert SheetDocument.from_json(out).to_json() == out
    a, b = json.loads(text), json.loads(out)
    assert {r["text"] for r in a["regions"]} == {r["text"] for r in b["regions"]}
    assert all(set(r) <= {"kind", "x", "y", "text", "w", "h", "component_name", "component_kind", "config"}
               for r in b["regions"])


def test_pre_phase_b_writer_shape_is_exact():
    """Exact expected bytes for a sheet that never had a stored view (any phase-B leak shows here)."""
    doc = SheetDocument(regions=[RegionData("math", 10.0, 20.0, "a := 2"),
                                 RegionData("plot", 10.0, 60.0, SPEC, 400.0, 260.0)])
    expected = json.dumps({
        "format": "livesheet", "version": 2, "settings": {"significant": 6},
        "regions": [{"kind": "math", "x": 10.0, "y": 20.0, "text": "a := 2"},
                    {"kind": "plot", "x": 10.0, "y": 60.0, "text": SPEC, "w": 400.0, "h": 260.0}],
    }, indent=2, ensure_ascii=False)
    assert doc.to_json() == expected


def test_old_2d_plot_sheet_resave_unchanged_keys():
    two_d = "plot\nover x from 0 to 1\nshow x"
    doc = SheetDocument(regions=[RegionData("plot", 10.0, 20.0, two_d, 300.0, 200.0),
                                 RegionData("math", 10.0, 300.0, "a := 2")])
    t = doc.to_json()
    again = SheetDocument.from_json(t).to_json()
    assert t == again and "view_" not in t


def test_view_keys_on_2d_and_other_regions_are_dropped():
    raw = {"format": "livesheet", "version": 2, "settings": {"significant": 6}, "regions": [
        {"kind": "plot", "x": 0, "y": 0, "text": "plot\nover x from 0 to 1\nshow x", "w": 400, "h": 260,
         "view_az": 1, "view_el": 2, "view_zoom": 3},
        {"kind": "math", "x": 0, "y": 300, "text": "a := 1", "view_az": 1, "view_el": 2, "view_zoom": 3},
        {"kind": "text", "x": 0, "y": 400, "text": "hi", "view_az": 1, "view_el": 2, "view_zoom": 3},
    ]}
    out = SheetDocument.from_json(json.dumps(raw)).to_json()
    assert "view_" not in out


@pytest.mark.parametrize("keys", [
    {"view_az": 10.0},
    {"view_az": 10.0, "view_el": 5.0},
    {"view_az": "x", "view_el": 5.0, "view_zoom": 1.0},
    {"view_az": None, "view_el": 5.0, "view_zoom": 1.0},
    {"view_az": True, "view_el": 5.0, "view_zoom": 1.0},
    {"view_az": [1], "view_el": 5.0, "view_zoom": 1.0},
])
def test_incomplete_or_malformed_view_keys_ignored(keys):
    raw = {"format": "livesheet", "version": 2, "settings": {"significant": 6}, "regions": [
        dict({"kind": "plot", "x": 0, "y": 0, "text": SPEC, "w": 400, "h": 260}, **keys)]}
    doc = SheetDocument.from_json(json.dumps(raw))      # must not raise
    assert not doc.regions[0].has_view()
    assert "view_" not in doc.to_json()


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_view_keys_ignored(bad):
    txt = ('{"format":"livesheet","version":2,"settings":{"significant":6},"regions":[{"kind":"plot",'
           '"x":0,"y":0,"text":' + json.dumps(SPEC) + ',"w":400,"h":260,"view_az":' + bad +
           ',"view_el":5,"view_zoom":1}]}')
    doc = SheetDocument.from_json(txt)
    assert not doc.regions[0].has_view()


def test_out_of_range_view_values_do_not_crash_load_or_paint(win, app, tmp_path):
    raw = {"format": "livesheet", "version": 2, "settings": {"significant": 6}, "regions": [
        {"kind": "plot", "x": 40, "y": 40, "text": SPEC, "w": 400, "h": 260,
         "view_az": 1e9, "view_el": 500.0, "view_zoom": -3.0}]}
    p = tmp_path / "bad.lsheet"
    p.write_text(json.dumps(raw))
    win.open_path(p)
    app.processEvents()
    win.sheet.recalculate()
    (reg,) = [r for r in win.sheet.regions() if isinstance(r, PlotRegion)]
    img = QImage(420, 280, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p2 = QPainter(img)
    reg.paint(p2, None)
    p2.end()
    # rotate / zoom afterwards must bring the values back into the documented ranges
    reg.rotate_by(1, 1)
    a, e, z = reg.effective_view()
    assert -180 <= a < 180 and -90 <= e <= 90
    reg.zoom_by(0)
    assert 0.25 <= reg.effective_view()[2] <= 4.0


def test_unknown_future_region_keys_are_ignored_by_reader():
    raw = {"format": "livesheet", "version": 2, "settings": {"significant": 6}, "regions": [
        {"kind": "plot", "x": 0, "y": 0, "text": SPEC, "w": 400, "h": 260,
         "view_az": 1.0, "view_el": 2.0, "view_zoom": 1.0, "future_key": {"a": 1}}]}
    doc = SheetDocument.from_json(json.dumps(raw))
    assert doc.regions[0].view_az == 1.0


def test_document_invalid_still_raises():
    with pytest.raises(DocumentError):
        SheetDocument.from_json("{}")


# ------------------------------------------------------------------ layout for views / zoom

@pytest.mark.parametrize("az,el", [(0, 0), (-180, 90), (179.99, -90), (40, 30), (90, 89.999), (0, -90)])
def test_layout_degenerate_views_do_not_raise(az, el):
    lay = layout_surface(data(), RECT, az, el, 1.0, "mesh")
    assert len(lay.cells) == 4 and len(lay.box_edges) == 12


@pytest.mark.parametrize("zoom", [0.25, 1.0, 4.0])
def test_layout_scale_proportional_to_zoom(zoom):
    lay = layout_surface(data(), RECT, 40, 30, zoom, "mesh")
    assert lay.scale == pytest.approx(0.42 * 260 * zoom, abs=1e-9)


def test_layout_depends_on_view_but_not_mode_geometry():
    d = data()
    a = layout_surface(d, RECT, 60, 40, 1.1, "mesh")
    b = layout_surface(d, RECT, 60, 40, 1.1, "wire")
    assert [c.polygon for c in a.cells] == [c.polygon for c in b.cells]
    c = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    assert [x.polygon for x in a.cells] != [x.polygon for x in c.cells]


@pytest.mark.parametrize("zoom", [0.25, 4.0])
@pytest.mark.parametrize("el", [-90, 90])
def test_paint_extremes_no_raise_and_draws(zoom, el, app):
    img = QImage(400, 260, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_surface(p, QRectF(0, 0, 400, 260), data(), 40, el, zoom, "mesh")
    p.end()
    white = QColor("white").rgb()
    assert sum(1 for y in range(260) for x in range(400) if img.pixel(x, y) != white) > 100


def test_zoomed_paint_stays_inside_rect(app):
    """Painting is clipped to the chart rect: the 20 px margin around it stays untouched."""
    img = QImage(440, 300, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_surface(p, QRectF(20, 20, 400, 260), data(), 40, 30, 4.0, "mesh")
    p.end()
    white = QColor("white").rgb()
    for x in range(440):
        for y in list(range(0, 19)) + list(range(282, 300)):
            assert img.pixel(x, y) == white
    for y in range(300):
        for x in list(range(0, 19)) + list(range(422, 440)):
            assert img.pixel(x, y) == white


# ------------------------------------------------------------------ performance (B8)

def timed(d, n=3, mode="mesh"):
    best = 1e9
    for _ in range(n):
        img = QImage(400, 260, QImage.Format.Format_RGB32)
        img.fill(QColor("white"))
        p = QPainter(img)
        t0 = time.perf_counter()
        lay = layout_surface(d, RECT, 55, 35, 1.2, mode)
        paint_surface(p, RECT, d, 55, 35, 1.2, mode)
        best = min(best, time.perf_counter() - t0)
        p.end()
        assert lay.cells
    return best


def test_redraw_time_25(app):
    d = data("surface\nover x from 0 to 1 points 25\nacross y from 0 to 1 points 25\nshow sin(6*x)*cos(6*y)")
    t = timed(d)
    print("redraw 25x25 mesh", t)
    assert t < 0.100          # target 50 ms, pass within 2x


def test_redraw_time_100(app):
    d = data("surface\nover x from 0 to 1 points 100\nacross y from 0 to 1 points 100\nshow sin(6*x)*cos(6*y)")
    t = timed(d, n=2)
    print("redraw 100x100 mesh", t)
    assert t < 0.500          # target 250 ms, pass within 2x


def test_redraw_time_100_wire_preview(app):
    d = data("surface\nover x from 0 to 1 points 100\nacross y from 0 to 1 points 100\nshow sin(6*x)*cos(6*y)")
    t = timed(d, n=2, mode="wire")
    print("redraw 100x100 wire", t)
    assert t < 0.500


# ------------------------------------------------------------------ PDF export

def test_pdf_uses_stored_view_and_stays_vector(win, tmp_path):
    reg = make(win)
    p1 = tmp_path / "default.pdf"
    export_pdf(win.sheet, str(p1))
    reg.rotate_by(80, -30)
    reg.zoom_by(120)
    p2 = tmp_path / "rotated.pdf"
    export_pdf(win.sheet, str(p2))
    b1, b2 = p1.read_bytes(), p2.read_bytes()
    assert b1.startswith(b"%PDF") and b2.startswith(b"%PDF")
    assert b"/Subtype /Image" not in b2 and b"/Subtype/Image" not in b2
    assert b1 != b2             # the PDF follows the stored camera
    assert len(b2) > 2000


@pytest.mark.xfail(reason="DEFECT 031B-3: rotating flag leaks wire preview into PDF export (no printing check)", strict=False)
def test_pdf_during_rotate_preview_is_not_wire(win, tmp_path, monkeypatch):
    """The wire preview must never leak into an export: export while `rotating` is stuck True
    on a large grid still uses the region's draw mode."""
    import livesheet.gui.surfaceview as sv
    modes = []
    real = sv.layout_surface

    def spy(data, rect, az, el, zoom, mode):
        modes.append(mode)
        return real(data, rect, az, el, zoom, mode)

    monkeypatch.setattr(sv, "layout_surface", spy)
    reg = make(win, "surface\nover x from 0 to 1 points 50\nacross y from 0 to 1 points 50\nshow x*y")
    reg.rotating = True
    export_pdf(win.sheet, str(tmp_path / "p.pdf"))
    reg.rotating = False
    assert modes and set(modes) == {"mesh"}, modes


# ------------------------------------------------------------------ label collisions under rotation

def _title_overlaps(az, el):
    d = data("surface\nover x from -1 m to 1 m points 5\nacross y from -1 m to 1 m points 5\n"
             "show 500 N*(x/m)*(y/m)*cos(3*x/m)\nzunit N")
    t = layout_surface(d, RECT, az, el, 1.0, "mesh").axis_title_anchors
    boxes = [(a.x - 3.0 * len(a.text), a.y - 6, a.x + 3.0 * len(a.text), a.y + 6) for a in t]
    hit = 0
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = boxes[i], boxes[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                hit += 1
    return hit


@pytest.mark.xfail(reason="DEFECT 031B-2: y and z axis titles overprint in ~22% of reachable views "
                          "(for example az 80, el 45); the phase A declutter only nudges tick labels",
                   strict=False)
def test_axis_titles_do_not_overprint_in_reachable_views():
    bad = [(az, el) for az in range(-180, 180, 10) for el in range(-80, 81, 20) if _title_overlaps(az, el)]
    assert not bad, f"{len(bad)} of 324 sampled views overprint axis titles, e.g. {bad[:5]}"


def test_axis_titles_do_not_overprint_at_default_view():
    assert _title_overlaps(40, 30) == 0
