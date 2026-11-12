"""Spec 031 phase A2: layout_surface / paint_surface, region dispatch, Insert > 3-D plot, save, PDF."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.plotregion import (SURFACE_HINT_TEXT, SURFACE_STARTER_TEXT, PlotRegion,  # noqa: E402
                                      engine_source, is_blank_spec, is_surface_spec)
from livesheet.gui.surfaceview import layout_surface, paint_surface  # noqa: E402

A11 = "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\nshow x + 2*y"
RECT = QRectF(0, 0, 400, 260)


def data_for(*lines: str):
    text = "\n".join(lines)
    res = Engine().evaluate([(0, text)])[0]
    assert res.status == "ok", res.error
    return res.surface


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def a11():
    return data_for(*A11.split("\n"))


def test_layout_cube_and_cells():
    d = a11()
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    cx, cy = lay.center
    assert (cx, cy) == (200, 130)
    for x, y, _ in lay.corners:
        assert ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= 0.9 * 260 / 2
    assert len(lay.cells) == d.cells_drawn == 4
    assert len(lay.box_edges) == 12


def test_layout_depth_order_and_shading():
    d = data_for("surface", "over x from 0 to 1 points 10", "across y from 0 to 1 points 10",
                 "show sin(6*x)*y")
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    depths = [c.depth for c in lay.cells]
    assert all(b - a >= -1e-12 for a, b in zip(depths, depths[1:]))
    assert all(0.35 - 1e-12 <= c.brightness <= 1.0 + 1e-12 for c in lay.cells)


def test_layout_modes():
    d = a11()
    mesh = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    wire = layout_surface(d, RECT, 40, 30, 1.0, "wire")
    assert all(c.fill is not None for c in mesh.cells)
    assert all(c.fill is None for c in wire.cells)
    assert [c.polygon for c in mesh.cells] == [c.polygon for c in wire.cells]
    assert len(wire.box_edges) == 12


def test_layout_labels():
    d = a11()
    lay = layout_surface(d, RECT, 40, 30, 1.0, "mesh")
    assert len(lay.tick_anchors) == len(d.x_ticks) + len(d.y_ticks) + len(d.z_ticks)
    assert lay.title_anchor is not None and len(lay.axis_title_anchors) == 3
    assert [a.text for a in lay.axis_title_anchors] == ["x", "y", "x + 2*y"]


def test_projection_matches_definition():
    # elevation 90: looking straight down, screen right = (-sin a, cos a, 0), depth = z
    d = a11()
    lay = layout_surface(d, RECT, 0, 90, 1.0, "wire")
    zs = sorted({round(c[2], 9) for c in lay.corners})
    assert zs == [-0.5, 0.5]


def _paint(data, mode="mesh", az=40, el=30):
    img = QImage(400, 260, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_surface(p, QRectF(0, 0, 400, 260), data, az, el, 1.0, mode)
    p.end()
    return img


def _non_white(img: QImage) -> int:
    white = QColor("white").rgb()
    return sum(1 for y in range(img.height()) for x in range(img.width()) if img.pixel(x, y) != white)


def test_paint_draws_and_edge_cases(app):
    assert _non_white(_paint(a11())) > 500
    assert _non_white(_paint(a11(), "wire")) > 500
    two = data_for("surface", "over x from 0 to 1 points 2", "across y from 0 to 1 points 2", "show x*y")
    assert two.cells_drawn == 1
    _paint(two)
    _paint(data_for("surface", "over x from 0 to 2 points 3", "across y from 0 to 2 points 3",
                    "show 5 m + 0*x"))
    _paint(data_for("surface", "over x from -1 to 1 points 3", "across y from 0 to 1 points 2", "show 1/x"))
    none = data_for(*A11.split("\n"), "zlim 100 to 200")
    assert none.cells_drawn == 0
    assert _non_white(_paint(none)) > 100   # frame and box are still drawn


def test_spec_helpers():
    assert is_surface_spec("\n  surface \nover x")
    assert not is_surface_spec("surface := 3")
    assert engine_source(A11) == A11
    assert engine_source("surface := 3").startswith("plot\n")
    assert is_blank_spec(SURFACE_STARTER_TEXT)
    assert not is_blank_spec(A11)


def _close(win):
    win.sheet.set_modified(False)   # no "save changes?" prompt
    win.close()


def _window(app):
    win = MainWindow()
    win.resize(900, 700)
    win.show()
    app.processEvents()
    return win


def test_insert_3d_plot(app):
    win = _window(app)
    before = len(win.sheet.regions())
    win.sheet.insert_region("surface")
    regs = [r for r in win.sheet.regions() if isinstance(r, PlotRegion)]
    assert len(win.sheet.regions()) == before + 1 and len(regs) == 1
    assert regs[0].source == SURFACE_STARTER_TEXT and not regs[0].editing
    assert SURFACE_HINT_TEXT.startswith("Empty 3-D plot")
    labels = [a.text().replace("&", "") for a in win.menuBar().actions()[2].menu().actions()]
    assert "3-D plot" in labels
    _close(win)


def test_live_update_and_use_dialog_hidden(app):
    win = _window(app)
    win.sheet.insert_region("math", "a := 2")
    region = win.sheet.insert_region("surface")
    region.source = ("surface\nover x from 0 to a points 3\nacross y from 0 to 2 points 3\nshow x + 2*y")
    win.sheet.recalculate()
    assert region.result.surface.xs == [0, 1, 2]
    region.start_editing()
    assert not region._use_dialog_proxy.isVisible()
    region.finish_editing()
    _close(win)


def test_save_roundtrip_and_version(app):
    win = _window(app)
    region = win.sheet.insert_region("surface")
    region.source = A11
    region.set_size(300, 200)
    doc = win.sheet.to_document()
    rd = [r for r in doc.regions if r.kind == "plot"][0]
    assert rd.text == A11 and (rd.w, rd.h) == (region.size_w, region.size_h)
    two_d = SheetDocument.from_json(doc.to_json())
    assert [r.text for r in two_d.regions if r.kind == "plot"] == [A11]
    # version: same as the same sheet holding a 2-D plot instead
    region.source = "plot\nover x from 0 to 1\nshow x"
    assert json.loads(win.sheet.to_document().to_json())["version"] == json.loads(doc.to_json())["version"]
    _close(win)


def test_pdf_export(app, tmp_path):
    win = _window(app)
    plain = tmp_path / "a.pdf"
    export_pdf(win.sheet, str(plain))
    region = win.sheet.insert_region("surface")
    region.source = A11
    win.sheet.recalculate()
    out = tmp_path / "b.pdf"
    export_pdf(win.sheet, str(out))
    assert out.read_bytes()[:4] == b"%PDF" and out.stat().st_size > plain.stat().st_size
    _close(win)


def test_delete_selected_surface(app):
    win = _window(app)
    region = win.sheet.insert_region("surface")
    region.setSelected(True)
    win.delete_selected()
    assert region not in win.sheet.regions()
    _close(win)
