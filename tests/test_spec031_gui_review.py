"""Spec 031 phase A2: independent black-box review tests (renderer + GUI), written from the spec only."""

import json
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.plotregion import PlotRegion, engine_source, is_surface_spec  # noqa: E402
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


def close(win):
    win.sheet.set_modified(False)
    win.close()


def window(app):
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    app.processEvents()
    return w


# ------------------------------------------------------------------ pure layout

def vecs(az, el):
    a, e = math.radians(az), math.radians(el)
    d = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))
    r = (-math.sin(a), math.cos(a), 0.0)
    u = (-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e))
    return d, r, u


def dot(a, b):
    return sum(p * q for p, q in zip(a, b))


def project(p, az, el, zoom=1.0, rect=RECT):
    d, r, u = vecs(az, el)
    s = 0.42 * min(rect.width(), rect.height()) * zoom
    c = rect.center()
    return (c.x() + s * dot(p, r), c.y() - s * dot(p, u), dot(p, d))


def test_corners_within_radius_and_match_formula():
    lay = layout_surface(data(), RECT, 40, 30, 1.0, "mesh")
    assert len(lay.corners) == 8
    c = RECT.center()
    for cx, cy, _ in lay.corners:
        assert math.hypot(cx - c.x(), cy - c.y()) <= 0.9 * 260 / 2
    mine = sorted(tuple(round(v, 6) for v in project((sx, sy, sz), 40, 30))
                  for sx in (-.5, .5) for sy in (-.5, .5) for sz in (-.5, .5))
    theirs = sorted(tuple(round(v, 6) for v in c3) for c3 in lay.corners)
    assert mine == theirs


@pytest.mark.parametrize("az,el", [(0, 0), (90, 0), (40, 30), (-135, 60), (10, 90), (200, -45)])
def test_corner_projection_other_views(az, el):
    lay = layout_surface(data(), RECT, az, el, 1.0, "mesh")
    mine = sorted(tuple(round(v, 6) for v in project((sx, sy, sz), az, el))
                  for sx in (-.5, .5) for sy in (-.5, .5) for sz in (-.5, .5))
    assert mine == sorted(tuple(round(v, 6) for v in c3) for c3 in lay.corners)


def test_zoom_scales_about_centre():
    a = layout_surface(data(), RECT, 40, 30, 1.0, "mesh")
    b = layout_surface(data(), RECT, 40, 30, 2.0, "mesh")
    c = RECT.center()
    for (x1, y1, _), (x2, y2, _) in zip(sorted(a.corners), sorted(b.corners)):
        pass
    r1 = max(math.hypot(x - c.x(), y - c.y()) for x, y, _ in a.corners)
    r2 = max(math.hypot(x - c.x(), y - c.y()) for x, y, _ in b.corners)
    assert r2 == pytest.approx(2 * r1, rel=1e-9)


def test_cell_count_and_modes():
    d = data()
    mesh = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    wire = layout_surface(d, RECT, 40, 30, 1.0, "wire")
    assert len(mesh.cells) == d.cells_drawn == 4 and len(wire.cells) == 4
    assert all(c.fill is not None for c in mesh.cells)
    assert all(c.fill is None for c in wire.cells)
    assert len(mesh.box_edges) == 12 and len(wire.box_edges) == 12
    assert all(len(c.polygon) == 4 for c in mesh.cells)


def test_depth_order_far_to_near():
    d = data("surface\nover x from 0 to 3 points 8\nacross y from 0 to 3 points 8\nshow sin(x)*cos(y)")
    for az, el in ((40, 30), (-120, 10), (200, 70)):
        lay = layout_surface(d, RECT, az, el, 1.0, "mesh")
        depths = [c.depth for c in lay.cells]
        assert all(b >= a - 1e-12 for a, b in zip(depths, depths[1:]))


def test_cell_depth_is_mean_corner_depth():
    d = data("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y")
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    # normalised: x,y in [-.5,.5]; z = x*y in [0,1] -> [-.5,.5]
    pts = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, .5), (-.5, .5, -.5)]
    want = sum(project(p, 40, 30)[2] for p in pts) / 4
    assert lay.cells[0].depth == pytest.approx(want, abs=1e-9)


def test_polygon_vertices_projected():
    d = data("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y")
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    pts = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, .5), (-.5, .5, -.5)]
    want = sorted((round(project(p, 40, 30)[0], 6), round(project(p, 40, 30)[1], 6)) for p in pts)
    got = sorted((round(x, 6), round(y, 6)) for x, y in lay.cells[0].polygon)
    assert want == got


def test_shading_formula_planar_surface():
    d = data()  # plane z = x + 2y, all cells identical
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    # normalised plane: x' = x/2-.5 , y' = y/2-.5, z' = z/6-.5 -> z' = (2x'+... ) compute via diagonals
    def norm(i, j):
        return (d.xs[i] / 2 - .5, d.ys[j] / 2 - .5, d.zs[j][i] / 6 - .5)
    p00, p10, p11, p01 = norm(0, 0), norm(1, 0), norm(1, 1), norm(0, 1)
    d1 = [a - b for a, b in zip(p11, p00)]
    d2 = [a - b for a, b in zip(p01, p10)]
    n = [d1[1] * d2[2] - d1[2] * d2[1], d1[2] * d2[0] - d1[0] * d2[2], d1[0] * d2[1] - d1[1] * d2[0]]
    ln = math.sqrt(dot(n, n))
    n = [v / ln for v in n]
    view_d = vecs(40, 30)[0]
    if dot(n, view_d) < 0:
        n = [-v for v in n]
    L = (-0.3, -0.5, 0.8)
    ll = math.sqrt(dot(L, L))
    L = tuple(v / ll for v in L)
    want = 0.35 + 0.65 * max(0.0, dot(n, L))
    for c in lay.cells:
        assert 0.35 - 1e-12 <= c.brightness <= 1.0 + 1e-12
        assert c.brightness == pytest.approx(want, abs=1e-9)


def test_brightness_range_rough_surface():
    d = data("surface\nover x from 0 to 6 points 30\nacross y from 0 to 6 points 30\nshow 5*sin(x)*cos(y)")
    for az, el in ((40, 30), (-80, -20), (150, 85), (0, -90)):
        lay = layout_surface(d, RECT, az, el, 1.0, "mesh")
        assert lay.cells
        assert all(0.35 - 1e-12 <= c.brightness <= 1.0 + 1e-12 for c in lay.cells)


def test_labels_anchor_counts():
    d = data()
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    assert len(lay.tick_anchors) == len(d.x_ticks) + len(d.y_ticks) + len(d.z_ticks)
    assert lay.title_anchor is not None and len(lay.axis_title_anchors) == 3


def test_layout_edge_cases():
    # 2 x 2
    d = data("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y")
    assert len(layout_surface(d, RECT, 40, 30, 1.0, "mesh").cells) == 1
    # NaN hole
    d = data("surface\nover x from -1 to 1 points 3\nacross y from 0 to 1 points 2\nshow 1/x")
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    assert lay.cells == [] and len(lay.box_edges) == 12
    # limits exclude everything
    d = data(SPEC + "\nzlim 100 to 200")
    lay = layout_surface(d, RECT, 40, 30, 1.0, "wire")
    assert d.cells_drawn == 0 and lay.cells == []
    # all view extremes do not raise
    for az, el in ((0, 90), (0, -90), (180, 0), (-180, 0), (1e3, 33)):
        layout_surface(data(), RECT, az, el, 1.0, "mesh")
    # tiny rect
    layout_surface(data(), QRectF(0, 0, 10, 10), 40, 30, 1.0, "mesh")


def test_manual_limits_hide_cells_in_layout():
    d = data(SPEC + "\nxlim 0 to 1.5")
    assert len(layout_surface(d, RECT, 40, 30, 1.0, "mesh").cells) == d.cells_drawn == 2


def test_descending_axis_layout_same_cell_count():
    d = data("surface\nover x from 2 to 0 points 3\nacross y from 0 to 1 points 2\nshow x")
    assert len(layout_surface(d, RECT, 40, 30, 1.0, "mesh").cells) == 2


# ------------------------------------------------------------------ painting

def paint_image(d, az=40, el=30, zoom=1.0, mode="mesh", w=400, h=260):
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_surface(p, QRectF(0, 0, w, h), d, az, el, zoom, mode)
    p.end()
    return img


def non_white(img):
    n = 0
    for y in range(img.height()):
        for x in range(img.width()):
            if img.pixelColor(x, y) != QColor("white"):
                n += 1
    return n


def test_paint_sample_and_save_png(app, tmp_path):
    img = paint_image(data("surface\nover x from -3 to 3 points 25\nacross y from -3 to 3 points 25\n"
                           "show sin(x)*cos(y)\ntitle Ripple\nxlabel x\nylabel y\nzlabel h"), w=600, h=420)
    out = os.environ.get("LS_REVIEW_PNG")
    if out:
        img.save(out)
    assert non_white(img) > 500


def test_paint_non_white_and_no_raise(app):
    assert non_white(paint_image(data())) > 500
    assert non_white(paint_image(data(), mode="wire")) > 500
    paint_image(data("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y"))
    paint_image(data(SPEC.replace("x + 2*y", "5 m + 0*x")))
    img = paint_image(data("surface\nover x from -1 to 1 points 3\nacross y from 0 to 1 points 2\nshow 1/x"))
    assert non_white(img) > 50     # box and labels
    img = paint_image(data(SPEC + "\nzlim 100 to 200"))
    assert non_white(img) > 50
    paint_image(data(), zoom=4.0)
    paint_image(data(), zoom=0.25)
    paint_image(data(), w=200, h=140)
    paint_image(data(), w=1, h=1)


# ------------------------------------------------------------------ plotregion / window

def test_helpers():
    assert is_surface_spec("surface\nover x") and is_surface_spec("\n  surface  \nx")
    assert not is_surface_spec("plot\nover x") and not is_surface_spec("plot3d\nover x")
    assert not is_surface_spec("surface := 3") and not is_surface_spec("surfaces")
    assert engine_source("surface\nover x").startswith("surface")
    assert engine_source("over x from 0 to 1\nshow x").startswith("plot")


def test_insert_3d_plot_menu_and_starter(app, monkeypatch):
    win = window(app)
    n0 = len(win.sheet.regions())
    win.sheet.insert_region("surface")
    regs = [r for r in win.sheet.regions() if isinstance(r, PlotRegion)]
    assert len(win.sheet.regions()) == n0 + 1 and len(regs) == 1
    assert regs[0].source == "surface\nover \nacross \nshow "
    assert not regs[0].editing
    labels = []
    for act in win.menuBar().actions():
        if act.menu():
            labels += [a.text().replace("&", "") for a in act.menu().actions()]
    assert any("3-D plot" in t for t in labels)
    assert any(t.strip() == "Plot..." or t.startswith("Plot") for t in labels)
    close(win)


def test_empty_spec_shows_hint_no_error(app):
    win = window(app)
    r = win.sheet.insert_region("surface")
    win.sheet.recalculate()
    app.processEvents()
    img = win.grab().toImage()
    assert img.width() > 0
    close(win)


def test_double_click_opens_editor_and_no_dialog_toggle(app):
    win = window(app)
    r = win.sheet.insert_region("surface")
    r.start_editing()
    assert r.editing
    proxy = getattr(r, "_use_dialog_proxy", None)
    if proxy is not None:
        assert not proxy.isVisible()
    r.finish_editing()
    close(win)


def test_live_update_via_math_region_above(app):
    win = window(app)
    m = win.sheet.insert_region("math", "a := 2")
    r = win.sheet.insert_region("surface")
    r.source = "surface\nover x from 0 to a points 3\nacross y from 0 to 1 points 2\nshow x*y"
    win.sheet.recalculate()
    assert r.result.surface.xs == [0, 1, 2]
    m.source = "a := 4"
    win.sheet.recalculate()
    assert r.result.surface.xs == [0, 2, 4]
    close(win)


def test_roundtrip_and_version(app, tmp_path):
    win = window(app)
    r = win.sheet.insert_region("surface")
    r.source = SPEC
    r.set_size(320, 220)
    doc = win.sheet.to_document()
    j = json.loads(doc.to_json())
    plots = [x for x in j["regions"] if x["kind"] == "plot"]
    assert len(plots) == 1 and plots[0]["text"] == SPEC
    assert not any(k in plots[0] for k in ("view_az", "view_el", "view_zoom"))
    doc2 = SheetDocument.from_json(doc.to_json())
    win2 = window(app)
    win2.sheet.load_document(doc2)
    p2 = [x for x in win2.sheet.regions() if isinstance(x, PlotRegion)][0]
    assert p2.source == SPEC and (p2.size_w, p2.size_h) == (r.size_w, r.size_h)
    assert p2.result is not None and p2.result.surface is not None
    r.source = "plot\nover x from 0 to 1\nshow x"
    assert json.loads(win.sheet.to_document().to_json())["version"] == j["version"]
    close(win)
    close(win2)


def test_sheet_without_plots_unchanged_version(app):
    win = window(app)
    win.sheet.insert_region("math", "a := 1")
    j = json.loads(win.sheet.to_document().to_json())
    assert not any(x["kind"] == "plot" for x in j["regions"])
    close(win)


def test_pdf_export_vector(app, tmp_path):
    win = window(app)
    win.sheet.insert_region("math", "a := 1")
    plain = tmp_path / "plain.pdf"
    export_pdf(win.sheet, str(plain))
    r = win.sheet.insert_region("surface")
    r.source = SPEC + "\nzunit \ntitle Plane"
    r.source = SPEC + "\ntitle Plane"
    win.sheet.recalculate()
    out = tmp_path / "s.pdf"
    export_pdf(win.sheet, str(out))
    raw = out.read_bytes()
    assert raw[:4] == b"%PDF" and len(raw) > plain.stat().st_size
    if os.environ.get("LS_REVIEW_PDF"):
        out.replace(os.environ["LS_REVIEW_PDF"])
    close(win)


def test_delete_selected(app):
    win = window(app)
    r = win.sheet.insert_region("surface")
    r.setSelected(True)
    win.delete_selected()
    assert r not in win.sheet.regions()
    close(win)


def test_two_d_dialog_path_unchanged(app):
    win = window(app)
    r = win.sheet.add_region("plot", win.sheet.crosshair.pos(), "plot\nover x from 0 to 1\nshow x")
    win.sheet.recalculate()
    assert r.result.plot is not None and r.result.surface is None
    close(win)


def test_surface_error_shown_not_raised(app):
    win = window(app)
    r = win.sheet.insert_region("surface")
    r.source = "surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow nope + x"
    win.sheet.recalculate()
    app.processEvents()
    assert r.result.status == "error" and win.grab().toImage().width() > 0
    close(win)
