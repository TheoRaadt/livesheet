"""Spec 021 phase B: page-break marker, reflow, delete, fold guides, PDF export (B1-B14)."""

from __future__ import annotations

import re

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from livesheet.document import FORMAT_VERSION_PAGES, SheetDocument
from livesheet.engine.pagination import PAGE_HEIGHT, PAGE_WIDTH
from livesheet.gui.main_window import MainWindow, export_pdf, pdf_strips
from livesheet.gui.worksheet import PageBreakItem, Worksheet

H = PAGE_HEIGHT


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet(app):
    return Worksheet()


def _add(sheet, y, text="1 =", x=10):
    return sheet.add_region("math", QPointF(x, y), text)


def _msgs(sheet):
    out: list[str] = []
    sheet.statusMessage.connect(out.append)
    return out


def _ys(sheet):
    return sorted(r.pos().y() for r in sheet.regions())


def _pdf_pages(path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", path.read_bytes()))


def test_b1_interior_insert_with_reflow(sheet):
    r1, r2, r3 = _add(sheet, 100), _add(sheet, 600), _add(sheet, 1300)
    msgs = _msgs(sheet)
    sheet.crosshair.setPos(10, 500)
    assert sheet.insert_page_break()
    assert (r1.pos().y(), r2.pos().y(), r3.pos().y()) == (100, 1320, 2020)
    assert sheet.page_break_ys() == [1220.0]
    assert sheet.crosshair.pos().y() == 1220 and sheet.crosshair.pos().x() == 10
    assert msgs[-1] == "Page break inserted; moved 2 regions down by 720 units."
    assert sheet.modified


def test_b2_order_after_insert(sheet):
    r1, r2 = _add(sheet, 100, "a := 1"), _add(sheet, 600, "a =")
    sheet.crosshair.setPos(10, 500)
    sheet.insert_page_break()
    assert r2.result.output == "= 1"
    # reversed roles: page-2 defines, page-1 uses
    s2 = Worksheet()
    u, d = _add(s2, 100, "a ="), _add(s2, 600, "a := 1")
    s2.crosshair.setPos(10, 500)
    s2.insert_page_break()
    assert u.result.status == "error" and "not defined" in u.result.error


def test_b3_insert_on_fold_moves_nothing(sheet):
    r = _add(sheet, 100)
    sheet.crosshair.setPos(10, 1220)
    sheet.insert_page_break()
    assert r.pos().y() == 100 and sheet.page_break_ys() == [1220.0]


def test_b4_second_break_on_overflowed_page(sheet):
    r2, r3 = _add(sheet, 1320), _add(sheet, 2020)
    sheet._add_marker(1220.0)
    sheet.insert_page_break(1500)
    assert (r2.pos().y(), r3.pos().y()) == (1320, 2960)
    assert sheet.page_break_ys() == [1220.0, 2440.0]
    s = Worksheet()
    s._add_marker(1220.0)
    s._add_marker(2440.0)
    s.insert_page_break(3700)
    assert s.page_break_ys() == [1220.0, 2440.0, 4880.0]
    # delta = 1180 verified through a region at the insertion row
    s2 = Worksheet()
    s2._add_marker(2440.0)
    r = _add(s2, 3700)
    s2.insert_page_break(3700)
    assert r.pos().y() == 3700 + 1180


def test_b5_existing_markers_move(sheet):
    sheet._add_marker(1220.0)
    sheet._add_marker(2440.0)
    sheet.insert_page_break(100)
    assert sheet.page_break_ys() == [1220.0, 2340.0, 3560.0]
    assert [m.number for m in sheet.page_markers()] == [2, 3, 4]


def test_b6_refused_at_page_top(sheet):
    _add(sheet, 100)
    msgs = _msgs(sheet)
    sheet._add_marker(1220.0)
    for y in (1220, 0):
        assert sheet.insert_page_break(y) is False
        assert msgs[-1] == "This position is already the top of a page."
    assert sheet.page_break_ys() == [1220.0] and _ys(sheet) == [100]


def test_b7_components_and_wires(sheet):
    c = sheet.add_component_region("C", "formula", {"inputs": "x", "expr": "x"}, QPointF(10, 600))
    d = sheet.add_component_region("D", "value", {"expr": "3"}, QPointF(400, 100))
    assert sheet.try_connect((d, "value"), (c, "x")) is None
    assert len(sheet._wires) == 1
    wires_before = len(sheet._wires)
    doc_before = [(w.from_component, w.from_port, w.to_component, w.to_port)
                  for w in sheet.to_document().wires]
    sheet.insert_page_break(500)
    assert (c.pos().y(), d.pos().y()) == (1320, 100)
    assert len(sheet._wires) == wires_before
    assert [(w.from_component, w.from_port, w.to_component, w.to_port)
            for w in sheet.to_document().wires] == doc_before
    for w in sheet._wires:
        start, end = w.endpoints()
        assert start == w.source.port_scene_pos("output", w.source_port)
        assert end == w.dest.port_scene_pos("input", w.dest_port)


def test_b8_remove_marker_regions_stay(sheet):
    r2, r3 = _add(sheet, 600), _add(sheet, 1300)
    sheet.insert_page_break(500)
    marker = sheet.page_markers()[0]
    marker.setSelected(True)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    sheet.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier))
    assert sheet.page_break_ys() == []
    assert (r2.pos().y(), r3.pos().y()) == (1320, 2020)
    assert marker.scene() is None


def test_b9_drag_across_marker(sheet):
    r1, other = _add(sheet, 100), _add(sheet, 700, x=400)
    sheet.insert_page_break(500)
    before = (other.pos().y(), sheet.page_break_ys())
    r1.setPos(10, 1300)
    assert (other.pos().y(), sheet.page_break_ys()) == before
    from livesheet.engine.pagination import page_index
    assert page_index(r1.pos().y(), sheet.page_break_ys()) == 1


def test_b10_marker_not_movable_not_in_select_all_delete_region(app):
    win = MainWindow()
    r = _add(win.sheet, 100)
    win.sheet.insert_page_break(500)
    marker = win.sheet.page_markers()[0]
    assert not marker.flags() & marker.GraphicsItemFlag.ItemIsMovable
    marker.setPos(0, 50)  # programmatic; user cannot drag (no ItemIsMovable flag)
    marker.setPos(0, 1220)
    win.select_all()
    assert r.isSelected() and not marker.isSelected()
    win.sheet.clearSelection()
    marker.setSelected(True)
    win.delete_selected()
    assert win.sheet.page_break_ys() == [] and r.scene() is win.sheet


def test_insert_menu_action_with_shortcut(app):
    win = MainWindow()
    acts = [a for m in win.menuBar().findChildren(type(win.menuBar().actions()[0].menu()))
            for a in m.actions() if a.text() == "Page &Break"]
    assert acts and acts[0].shortcut().toString() == "Ctrl+Return"
    win.sheet.crosshair.setPos(10, 500)
    acts[0].trigger()
    assert win.sheet.page_break_ys() == [1220.0]


def test_b14_round_trip(sheet, tmp_path):
    _add(sheet, 100, "a := 1"), _add(sheet, 600, "a ="), _add(sheet, 1300)
    sheet.insert_page_break(500)
    doc = sheet.to_document()
    assert doc.version() == FORMAT_VERSION_PAGES == 4
    path = tmp_path / "s.lsheet"
    doc.save(path)
    s2 = Worksheet()
    s2.load_document(SheetDocument.load(path))
    assert _ys(s2) == [100, 1320, 2020] and s2.page_break_ys() == [1220.0]
    assert [r.text() for r in s2.ordered_regions()] == [r.text() for r in sheet.ordered_regions()]
    assert len(s2.page_markers()) == 1


def test_clear_sheet_removes_markers(sheet):
    sheet.insert_page_break(500)
    sheet.clear_sheet()
    assert sheet.page_break_ys() == [] and not [i for i in sheet.items() if isinstance(i, PageBreakItem)]


def test_fold_guides(sheet):
    assert sheet.fold_guide_ys(3000) == [1220, 2440]
    sheet._add_marker(1500.0)
    assert sheet.fold_guide_ys(4000) == [1220, 2720, 3940]
    assert sheet.fold_guide_ys(1400) == [1220]


def _render(sheet, printing):
    sheet.setSceneRect(0, 0, PAGE_WIDTH + 40, 1400)
    sheet.crosshair.hide()
    img = QImage(900, 1400, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    p = QPainter(img)
    sheet.printing = printing
    try:
        sheet.render(p)
    finally:
        p.end()
        sheet.printing = False
    return img


def test_b13_marker_and_guides_hidden_when_printing(sheet):
    sheet._add_marker(600.0)
    shown = _render(sheet, False)
    hidden = _render(sheet, True)
    assert shown != hidden
    white = QImage(hidden.size(), hidden.format())
    white.fill(0xFFFFFF)
    assert hidden == white


def test_pdf_strips_unchanged_without_breaks():
    assert pdf_strips([], 2610.0, 1214.7) == [(0.0, 1214.7), (1214.7, 1214.7), (2429.4, 1214.7)]
    assert pdf_strips([], 100.0, 1214.7) == [(0.0, 1214.7)]


def test_b11_pdf_with_breaks(sheet, tmp_path):
    _add(sheet, 100)
    _add(sheet, 1700)
    sheet._add_marker(1220.0)
    strips = pdf_strips(sheet.page_break_ys(), 1810.0, float(H))
    assert len(strips) == 2 and strips[1][0] == 1220.0
    out = tmp_path / "b.pdf"
    export_pdf(sheet, str(out))
    assert _pdf_pages(out) == 2
    assert not sheet.printing


def test_pdf_strips_overflowing_page_and_empty_tail():
    s = pdf_strips([1220.0], 3000.0, float(H))
    assert [t for t, _ in s] == [0.0, 1220.0, 2440.0]
    assert pdf_strips([1220.0], 800.0, float(H)) == [(0.0, 800.0)]
    assert len(pdf_strips([500.0, 500.0], 900.0, float(H))) == 2


def test_b12_pdf_without_breaks_page_count(sheet, tmp_path):
    _add(sheet, 100)
    _add(sheet, 2590)
    out = tmp_path / "n.pdf"
    export_pdf(sheet, str(out))
    assert _pdf_pages(out) == 3   # page_h ~1214.7: 2600 content -> 3 sheets, as before
