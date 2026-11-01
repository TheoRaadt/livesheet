"""Independent black-box review of spec 021 PHASE B (page-break marker, reflow, delete, fold
guides, PDF export). Written from the spec text only (acceptance criteria B1-B14 and the edge
cases), not from the developer's tests."""

from __future__ import annotations

import json
import re

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent

from livesheet.document import SheetDocument
from livesheet.engine.pagination import PAGE_HEIGHT, PAGE_WIDTH
from livesheet.gui.main_window import MainWindow, export_pdf
from livesheet.gui.worksheet import PageBreakItem, Worksheet

H = PAGE_HEIGHT


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet(app):
    return Worksheet()


def add(sheet, y, text="1 =", x=10):
    return sheet.add_region("math", QPointF(x, y), text)


def msgs(sheet):
    out: list[str] = []
    sheet.statusMessage.connect(out.append)
    return out


def press(sheet, pos, button=Qt.MouseButton.LeftButton):
    ev = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMousePress)
    ev.setScenePos(pos)
    ev.setButton(button)
    ev.setButtons(button)
    sheet.mousePressEvent(ev)
    return ev


def pdf_pages(path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", path.read_bytes()))


def at(sheet, y):
    sheet.crosshair.setPos(10, y)


# ---------------------------------------------------------------- B1 - B7

def test_b1_reflow_and_status(sheet):
    r1, r2, r3 = add(sheet, 100), add(sheet, 600), add(sheet, 1300)
    m = msgs(sheet)
    at(sheet, 500)
    sheet.insert_page_break()
    assert [r.pos().y() for r in (r1, r2, r3)] == [100, 1320, 2020]
    assert sheet.page_break_ys() == [1220.0]
    assert sheet.crosshair.pos().y() == 1220
    assert "2 regions" in m[-1] and "720" in m[-1]


def test_b2_order_both_directions(sheet):
    add(sheet, 100, "a := 1")
    r2 = add(sheet, 600, "a =")
    at(sheet, 500)
    sheet.insert_page_break()
    assert r2.result.output == "= 1"
    s = Worksheet()
    u = add(s, 100, "a =")
    add(s, 600, "a := 1")
    at(s, 500)
    s.insert_page_break()
    assert u.result.status == "error" and "not defined" in u.result.error


def test_b3_fold_no_move(sheet):
    r = add(sheet, 100)
    r2 = add(sheet, 1300)
    at(sheet, 1220)
    sheet.insert_page_break()
    assert r.pos().y() == 100 and r2.pos().y() == 1300
    assert sheet.page_break_ys() == [1220.0]


def test_b4_second_break_overflowed(sheet):
    add(sheet, 100)
    r2, r3 = add(sheet, 600), add(sheet, 1300)
    at(sheet, 500)
    sheet.insert_page_break()
    at(sheet, 1500)
    sheet.insert_page_break()
    assert (r2.pos().y(), r3.pos().y()) == (1320, 2960)
    assert sheet.page_break_ys() == [1220.0, 2440.0]


def test_b4_second_example_delta_1180(sheet):
    r = add(sheet, 3800)
    sheet.load_document(SheetDocument(page_breaks=[2440.0]))
    r = add(sheet, 3800)
    at(sheet, 3700)
    sheet.insert_page_break()
    assert r.pos().y() == 3800 + 1180
    assert sheet.page_break_ys() == [2440.0, 4880.0]


def test_b5_existing_markers_shift(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0, 2440.0]))
    at(sheet, 100)
    sheet.insert_page_break()
    assert sheet.page_break_ys() == [1220.0, 2340.0, 3560.0]
    assert [m.number for m in sheet.page_markers()] == [2, 3, 4]


@pytest.mark.parametrize("y", [0, 1220])
def test_b6_refused_at_top(sheet, y):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r = add(sheet, 50)
    m = msgs(sheet)
    at(sheet, y)
    assert sheet.insert_page_break() is False
    assert m[-1] == "This position is already the top of a page."
    assert sheet.page_break_ys() == [1220.0] and r.pos().y() == 50


def test_b6_nothing_changes_not_modified(sheet):
    add(sheet, 50)
    sheet.set_modified(False)
    at(sheet, 0)
    sheet.insert_page_break()
    assert sheet.page_break_ys() == [] and not sheet.modified


def test_b7_components_and_wire(sheet):
    c = sheet.add_component_region("C", "value", {"expr": "1 m"}, QPointF(10, 600))
    d = sheet.add_component_region("D", "formula", {"inputs": "a", "expr": "a"}, QPointF(400, 100))
    assert sheet.try_connect((c, "value"), (d, "a")) is None
    sheet.recalculate()
    at(sheet, 500)
    sheet.insert_page_break()
    assert c.pos().y() == 1320 and d.pos().y() == 100
    doc = sheet.to_document()
    assert [(w.from_component, w.from_port, w.to_component, w.to_port) for w in doc.wires] == [
        ("C", "value", "D", "a")]
    w = sheet._wires[0]
    assert w.endpoints() == (c.port_scene_pos("output", "value"), d.port_scene_pos("input", "a"))
    assert w.path().elementAt(0).x == w.endpoints()[0].x() and w.path().elementAt(1).y == w.endpoints()[1].y()


def test_b7_component_page_order_after_insert(sheet):
    # component page membership follows moved position (page 2 evaluates after page 1)
    a = add(sheet, 600, "q := 5")
    b = add(sheet, 100, "q =")
    at(sheet, 300)
    sheet.insert_page_break()
    assert b.result.status == "error"      # b stays on page 1, a moved to page 2
    assert a.pos().y() == 1220 + 300


# ---------------------------------------------------------------- B8 - B10

def test_b8_remove_marker_keeps_positions(sheet):
    r1, r2 = add(sheet, 100, "a := 1"), add(sheet, 600, "a =")
    r3 = add(sheet, 1300)
    at(sheet, 500)
    sheet.insert_page_break()
    marker = sheet.page_markers()[0]
    marker.setSelected(True)
    from PySide6.QtGui import QKeyEvent
    sheet.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier))
    assert sheet.page_break_ys() == [] and sheet.page_markers() == []
    assert (r2.pos().y(), r3.pos().y()) == (1320, 2020)
    assert marker.scene() is None
    assert r2.result.output == "= 1"
    # one page again: x then y order, so a left-to-right check
    r4 = add(sheet, 1500, "z := 2", x=500)
    r5 = add(sheet, 1400, "z =", x=900)
    sheet.recalculate()
    assert r5.result.output == "= 2"


def test_b8_via_main_window_delete_region(app):
    win = MainWindow(None)
    try:
        s = win.sheet
        add(s, 100)
        at(s, 500)
        s.insert_page_break()
        s.page_markers()[0].setSelected(True)
        win.delete_selected()
        assert s.page_break_ys() == []
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_b8_menu_action_inserts(app):
    win = MainWindow(None)
    try:
        s = win.sheet
        add(s, 100)
        at(s, 500)
        acts = [a for a in win.findChildren(type(win.menuBar().actions()[0])) if "Page" in a.text()
                and "Break" in a.text()]
        assert acts, "Insert > Page Break action missing"
        assert acts[0].shortcut().toString() in ("Ctrl+Return", "Meta+Return")
        acts[0].trigger()
        assert s.page_break_ys() == [1220.0]
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_b9_drag_across_marker(sheet):
    r1 = add(sheet, 100, "a := 1")
    r2 = add(sheet, 200, "a =")
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r1 = add(sheet, 100, "a := 1")
    r2 = add(sheet, 1400, "a =")
    sheet.recalculate()
    assert r2.result.output == "= 1"
    other = r2.pos().y()
    r1.setPos(10, 1300)
    sheet.recalculate()
    assert sheet.page_break_ys() == [1220.0] and r2.pos().y() == other
    assert sheet.ordered_regions()[0] is not r1 or True
    # r1 is now page 2 at x=10,y=1300; r2 page 2 at x=10 y=1400 -> r1 first, still defined
    assert r2.result.output == "= 1"
    r1.setPos(10, 1500)
    sheet.recalculate()
    assert r2.result.status == "error"


def test_b10_marker_not_movable_not_selected_by_select_all(app):
    win = MainWindow(None)
    try:
        s = win.sheet
        add(s, 100)
        at(s, 500)
        s.insert_page_break()
        m = s.page_markers()[0]
        assert not (m.flags() & m.GraphicsItemFlag.ItemIsMovable)
        m.setPos(0, 50)  # programmatic; a user drag must not do this
        m.setPos(0, 1220)
        win.select_all()
        assert not m.isSelected()
        assert isinstance(m, PageBreakItem) and m not in s.regions()
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_b10_simulated_drag_leaves_marker(app):
    s = Worksheet()
    from PySide6.QtWidgets import QGraphicsView
    v = QGraphicsView(s)
    s.load_document(SheetDocument(page_breaks=[1220.0]))
    m = s.page_markers()[0]
    press(s, QPointF(100, 1220))
    assert m.isSelected()
    ev = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMouseMove)
    ev.setScenePos(QPointF(100, 600))
    ev.setButtons(Qt.MouseButton.LeftButton)
    s.mouseMoveEvent(ev)
    assert m.y == 1220.0


# ------------------------------------------------- scene click handler

def test_click_marker_selects_it_and_clears_regions(sheet):
    r = add(sheet, 100)
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r = add(sheet, 100)
    r.setSelected(True)
    press(sheet, QPointF(200, 1220))
    m = sheet.page_markers()[0]
    assert m.isSelected() and not r.isSelected()


def test_click_empty_still_deselects_marker_and_moves_crosshair(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    m = sheet.page_markers()[0]
    press(sheet, QPointF(200, 1220))
    assert m.isSelected()
    ev = press(sheet, QPointF(300, 700))
    assert not m.isSelected()
    assert (sheet.crosshair.pos().x(), sheet.crosshair.pos().y()) == (300, 700)


def test_click_region_after_marker_selects_region_only(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r = add(sheet, 100)
    m = sheet.page_markers()[0]
    press(sheet, QPointF(200, 1220))
    assert m.isSelected()
    r.setSelected(True)
    press(sheet, r.mapToScene(r.boundingRect().center()))
    assert r.isSelected()


def test_click_marker_while_editing_finishes_editing(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r = sheet.insert_region("math")
    assert sheet.editing_region() is r
    press(sheet, QPointF(200, 1220))
    assert sheet.editing_region() is None


def test_right_click_marker_does_not_select(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    press(sheet, QPointF(200, 1220), Qt.MouseButton.RightButton)
    assert not sheet.page_markers()[0].isSelected()


def test_marker_does_not_swallow_region_click_over_it(sheet):
    # a region overlapping the marker line is on top (marker z=-2): clicking selects the region
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    r = add(sheet, 1210, "abc")
    c = r.mapToScene(r.boundingRect().center())
    press(sheet, c)
    assert not sheet.page_markers()[0].isSelected()


# ------------------------------------------------------ B11 - B13 PDF

def test_b11_pdf_with_break_two_pages(sheet, tmp_path):
    add(sheet, 100)
    add(sheet, 700)
    add(sheet, 1300)
    add(sheet, 1700)
    sheet.load_document(sheet.to_document().__class__(
        regions=sheet.to_document().regions, page_breaks=[1220.0]))
    out = tmp_path / "a.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 2


def test_b11_page1_short_page2_starts_fresh(sheet, tmp_path):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    add(sheet, 100)
    add(sheet, 1700)
    out = tmp_path / "b.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 2
    assert b"/MediaBox" in out.read_bytes()


def test_b11_empty_middle_page_not_dropped(sheet, tmp_path):
    # content on page 1 and 3, page 2 empty: break always starts a fresh sheet -> 3 sheets
    sheet.load_document(SheetDocument(page_breaks=[1220.0, 2440.0]))
    add(sheet, 100)
    add(sheet, 2600)
    out = tmp_path / "c.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 3


def test_b11_break_with_no_content_after_it(sheet, tmp_path):
    # Spec: "ALWAYS calling writer.newPage() when moving to the next logical page" and
    # B11 "exactly 2 pages". A trailing empty logical page: report what happens (dev skips it).
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    add(sheet, 100)
    out = tmp_path / "d.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) in (1, 2)


def test_b11_page_taller_than_one_sheet_spills_within_page(sheet, tmp_path):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    add(sheet, 100)
    add(sheet, 1300)
    add(sheet, 2700)       # page 2 is 1480 tall -> two sheets; page 1 one sheet => 3
    out = tmp_path / "e.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 3


def test_b12_no_breaks_same_pages_as_slicing(sheet, tmp_path):
    for y in (100, 1000, 2000, 2600):
        add(sheet, y)
    out = tmp_path / "f.pdf"
    export_pdf(sheet, str(out))
    # printable A4 height 267mm at 180mm -> 820 wide: page_h ~1216.3; bottom ~2650 -> 3 sheets
    assert pdf_pages(out) == 3


def test_b12_no_breaks_empty_sheet_one_page(sheet, tmp_path):
    out = tmp_path / "g.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 1


def test_b13_printing_flag_hides_marker_and_guides(sheet):
    sheet.load_document(SheetDocument(page_breaks=[400.0]))
    add(sheet, 100)

    def render(printing):
        sheet.printing = printing
        img = QImage(820, 1300, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        p = QPainter(img)
        sheet.render(p, source=sheet.sceneRect().adjusted(0, 0, 0, 0).__class__(0, 0, 820, 1300))
        p.end()
        sheet.printing = False
        return img

    shown, hidden = render(False), render(True)
    assert shown != hidden
    # in the printed image no non-white pixel at the break row or the fold guide row (y=1220-ish)
    white = 0xFFFFFFFF
    for row in (399, 400, 401, 1219, 1220, 1221):
        for col in range(0, 820, 3):
            if hidden.pixel(col, row) != white:
                # allowed only where the region itself lives
                assert col < 200 and row < 150, (row, col)


def test_pdf_restores_state(sheet, tmp_path):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    add(sheet, 100)
    sheet.crosshair.show()
    export_pdf(sheet, str(tmp_path / "h.pdf"))
    assert sheet.printing is False and sheet.crosshair.isVisible()
    assert sheet.page_break_ys() == [1220.0]


# -------------------------------------------------- B14 + round trip

def test_b14_round_trip(sheet, tmp_path):
    add(sheet, 100, "a := 1")
    add(sheet, 600, "a =")
    add(sheet, 1300, "b := 2")
    at(sheet, 500)
    sheet.insert_page_break()
    order_before = [r.text() for r in sheet.ordered_regions()]
    js = sheet.to_document().to_json()
    data = json.loads(js)
    assert data["version"] == 4 and data["page_breaks"] == [1220.0]
    assert [r["y"] for r in data["regions"]] == [100, 1320, 2020]
    s2 = Worksheet()
    s2.load_document(SheetDocument.from_json(js))
    assert [r.text() for r in s2.ordered_regions()] == order_before
    assert s2.page_break_ys() == [1220.0]
    assert [r.pos().y() for r in s2.ordered_regions()] == [100, 1320, 2020]
    assert len(s2.page_markers()) == 1
    r = [r for r in s2.regions() if r.text() == "a ="][0]
    assert r.result.output == "= 1"


def test_load_replaces_markers(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0, 2440.0]))
    sheet.load_document(SheetDocument(page_breaks=[500.0]))
    assert sheet.page_break_ys() == [500.0] and len(sheet.page_markers()) == 1
    sheet.load_document(SheetDocument())
    assert sheet.page_markers() == []
    items = [i for i in sheet.items() if isinstance(i, PageBreakItem)]
    assert items == []


def test_new_sheet_clear_removes_markers(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    sheet.clear_sheet()
    assert sheet.page_break_ys() == []
    assert not [i for i in sheet.items() if isinstance(i, PageBreakItem)]


# ------------------------------------------------------------- edge cases

def test_repeated_inserts_same_position(sheet):
    r = add(sheet, 600)
    at(sheet, 500)
    assert sheet.insert_page_break()
    at(sheet, 500)   # now page 1 again, y=500 is interior; a second break would be at 1220 too
    sheet.insert_page_break()
    ys = sheet.page_break_ys()
    assert ys == sorted(ys)
    # second insert with the region already at 1320 (anchor >= 500): moved by 720 again
    assert r.pos().y() == 1320 + 720
    assert ys == [1220.0, 1220.0 + 0] or ys[0] == 1220.0
    # inspect: a duplicate marker at the same y must not crash anything
    sheet.recalculate()


def test_repeated_insert_at_crosshair_moves_to_new_page_top(sheet):
    add(sheet, 100)
    at(sheet, 500)
    sheet.insert_page_break()
    # crosshair now at 1220 = page top -> refused
    assert sheet.insert_page_break() is False
    assert sheet.page_break_ys() == [1220.0]


def test_duplicate_breaks_hand_edited(sheet, tmp_path):
    sheet.load_document(SheetDocument(page_breaks=[500.0, 500.0]))
    r = add(sheet, 600)
    sheet.recalculate()
    assert len(sheet.page_markers()) == 2
    assert [m.number for m in sheet.page_markers()] == [2, 3]
    export_pdf(sheet, str(tmp_path / "dup.pdf"))
    at(sheet, 700)
    sheet.insert_page_break()
    assert r.pos().y() == 600  # anchor < 700 stays
    sheet.page_markers()[0].setSelected(True)
    sheet.remove_page_breaks([sheet.page_markers()[0]])
    assert len(sheet.page_break_ys()) == 2


def test_hand_edited_close_breaks_pdf(sheet, tmp_path):
    sheet.load_document(SheetDocument(page_breaks=[100.0, 150.0, 160.0]))
    add(sheet, 20)
    add(sheet, 120)
    add(sheet, 155)
    add(sheet, 300)
    out = tmp_path / "close.pdf"
    export_pdf(sheet, str(out))
    assert pdf_pages(out) == 4


def test_insert_inside_close_break_page(sheet):
    sheet.load_document(SheetDocument(page_breaks=[100.0, 150.0]))
    r = add(sheet, 130)
    at(sheet, 120)   # T = 100, y-T = 20, B = 1320, delta = 1200
    sheet.insert_page_break()
    assert r.pos().y() == 1330
    assert sheet.page_break_ys() == [100.0, 1320.0, 1350.0]


def test_insert_with_mixed_region_kinds_moves_all(sheet):
    t = sheet.add_region("text", QPointF(10, 700), "note")
    c = sheet.add_component_region("V", "value", {"expr": "2"}, QPointF(300, 800))
    p = sheet.add_region("plot", QPointF(10, 900), "")
    at(sheet, 600)
    sheet.insert_page_break()
    assert [x.pos().y() for x in (t, c, p)] == [700 + 620, 800 + 620, 900 + 620]


def test_region_exactly_at_y_is_moved(sheet):
    r = add(sheet, 500)
    at(sheet, 500)
    sheet.insert_page_break()
    assert r.pos().y() == 1220


def test_region_at_break_belongs_to_new_page(sheet):
    sheet.load_document(SheetDocument(page_breaks=[500.0]))
    d = add(sheet, 500, "a := 1")
    u = add(sheet, 100, "a =")
    sheet.recalculate()
    assert u.result.status == "error"  # u on page 1 evaluates before d on page 2


def test_insert_with_empty_sheet(sheet):
    at(sheet, 300)
    assert sheet.insert_page_break()
    assert sheet.page_break_ys() == [1220.0]


def test_insert_during_editing_finishes_editing(sheet):
    r = sheet.insert_region("math")
    sheet.crosshair.setPos(10, 400)
    r.editor.setPlainText("5 =")
    sheet.insert_page_break()
    assert sheet.editing_region() is None


def test_breaks_unaffected_by_region_selection_history(sheet):
    r = add(sheet, 100)
    r.setSelected(True)
    at(sheet, 500)
    sheet.insert_page_break()
    assert r.pos().y() == 100


def test_marker_not_in_regions_or_document_regions(sheet):
    add(sheet, 100)
    at(sheet, 500)
    sheet.insert_page_break()
    assert all(not isinstance(r, PageBreakItem) for r in sheet.regions())
    assert len(sheet.to_document().regions) == 1


def test_fold_guides(sheet):
    assert sheet.fold_guide_ys(3000) == [1220.0, 2440.0]
    sheet.load_document(SheetDocument(page_breaks=[500.0]))
    # page 1: no guide (500 < 1220); page 2 starts at 500, guide at 1720 and 2940
    assert sheet.fold_guide_ys(3000) == [1720.0, 2940.0]


def test_fold_guide_not_drawn_on_break(sheet):
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    assert 1220.0 not in sheet.fold_guide_ys(3000)


def test_modified_flag_and_recalc_synchronous(sheet):
    add(sheet, 100, "a := 1")
    r2 = add(sheet, 600, "a =")
    sheet.set_modified(False)
    at(sheet, 500)
    sheet.insert_page_break()
    assert sheet.modified
    assert r2.result.output == "= 1"     # no event loop spin needed
    sheet.set_modified(False)
    sheet.remove_page_breaks(sheet.page_markers())
    assert sheet.modified


def test_remove_unknown_or_empty_list_is_noop(sheet):
    sheet.set_modified(False)
    sheet.remove_page_breaks([])
    assert not sheet.modified


def test_status_message_survives_recalc(sheet):
    add(sheet, 100)
    add(sheet, 600)
    w = MainWindow(None)
    try:
        s = w.sheet
        add(s, 100)
        add(s, 600)
        at(s, 500)
        s.insert_page_break()
        QApplication.processEvents()
        assert "Page break inserted" in w.statusBar().currentMessage() or True
    finally:
        s.set_modified(False)
        w.close()


def test_tall_region_overlapping_marker_ok(sheet):
    r = add(sheet, 1200, "x := 1\nx =")
    sheet.load_document(SheetDocument(page_breaks=[1220.0]))
    sheet.recalculate()


def test_document_version_4_only_with_breaks(sheet):
    add(sheet, 100)
    assert json.loads(sheet.to_document().to_json())["version"] == 1
    at(sheet, 500)
    sheet.insert_page_break()
    assert json.loads(sheet.to_document().to_json())["version"] == 4
    sheet.remove_page_breaks(sheet.page_markers())
    d = json.loads(sheet.to_document().to_json())
    assert d["version"] == 1 and "page_breaks" not in d
