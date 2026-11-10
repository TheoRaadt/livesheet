"""Independent black-box tests for spec 027 (Outline tab), written from the spec only.

Hooks used: SidePanel.outline_buttons, tab index 8 ("Outline"), Worksheet.add_region/_add_marker/
remove_regions/to_document/load_document. Settings are isolated (temp INI); windows are closed
with set_modified(False) so no blocking "Save changes?" dialog opens.
"""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QFont, QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402

OUTLINE, DATA = 8, 9


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module", autouse=True)
def isolated_settings(tmp_path_factory, app):
    old = QSettings.defaultFormat()
    d = tmp_path_factory.mktemp("qs027r")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(d))
    yield
    QSettings.setDefaultFormat(old)


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    w.sheet.clear_sheet()
    w.sheet.set_modified(False)
    QApplication.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()
    QApplication.processEvents()


def put(sheet, y, runs, x=40):
    """Text region at (x, y); runs = [(text, weight)] inserted as a single first paragraph, or a
    list containing '\\n' text to start further paragraphs."""
    r = sheet.add_region("text", QPointF(x, y), "")
    cur = QTextCursor(r.editor.document())
    for text, weight in runs:
        f = cur.charFormat()
        f.setFontWeight(weight)
        cur.insertText(text, f)
    return r


B, N = QFont.Weight.Bold, QFont.Weight.Normal


def shown(win):
    win.side_panel.tabs.setCurrentIndex(OUTLINE)
    QApplication.processEvents()
    win.side_panel.rebuild_outline()
    return [b.text() for b in win.side_panel.outline_buttons]


def page_labels(win):
    return [l.text() for l in win.side_panel.tabs.widget(OUTLINE).findChildren(QLabel)]


# ---- heading rule -----------------------------------------------------------------------

@pytest.mark.parametrize("weight,expected", [
    (QFont.Weight.Normal, False), (QFont.Weight.Medium, False),
    (QFont.Weight.DemiBold, True), (QFont.Weight.Bold, True),
    (QFont.Weight.ExtraBold, True), (QFont.Weight.Black, True)])
def test_weight_threshold(win, weight, expected):
    put(win.sheet, 40, [("Title", weight)])
    assert (shown(win) == ["Title"]) is expected


def test_only_first_paragraph_counts(win):
    put(win.sheet, 40, [("Head", B), ("\n", N), ("body text", N)])        # first para bold
    put(win.sheet, 120, [("plain", N), ("\n", N), ("Later bold", B)])     # bold in 2nd para only
    assert shown(win) == ["Head"]


def test_partly_bold_first_paragraph_is_not_heading(win):
    put(win.sheet, 40, [("Bold", B), (" tail", N)])
    assert shown(win) == []


def test_empty_or_whitespace_bold_is_not_heading(win):
    put(win.sheet, 40, [("", B)])
    put(win.sheet, 80, [("   ", B)])
    assert shown(win) == []


def test_whitespace_collapsed(win):
    put(win.sheet, 40, [("A   B \t C", B)])
    assert shown(win) == ["A B C"]


def test_math_and_plot_never_listed(win):
    win.sheet.add_region("math", QPointF(40, 40), "x := 1")
    assert shown(win) == []
    assert "No headings yet" in " ".join(page_labels(win))


def test_malformed_html_no_exception(win):
    for t in ("<b>unclosed", "<<<>>>&bogus;", "<p style='font-weight:700'>x</i>", ""):
        win.sheet.add_region("text", QPointF(40, 40), t)
    shown(win)   # must not raise


# ---- order and pages --------------------------------------------------------------------

def test_same_y_left_to_right(win):
    put(win.sheet, 100, [("Right", B)], x=400)
    put(win.sheet, 100, [("Left", B)], x=40)
    assert shown(win) == ["Left", "Right"]


def test_page_headers_and_new_row(win):
    s = win.sheet
    put(s, 300, [("A", B)])
    put(s, 100, [("B", B)])
    put(s, 700, [("C", B)])
    put(s, 1300, [("D", B)])
    s._add_marker(500)
    s._add_marker(1000)
    assert shown(win) == ["B", "A", "C", "D"]
    assert page_labels(win) == ["Page 1", "Page 2", "Page 3"]
    pg = win.side_panel.tabs.widget(OUTLINE).widget()
    hdr = [l for l in pg.findChildren(QLabel)]
    btn = win.side_panel.outline_buttons
    # each header starts a new row: header y above its first button and not beside previous button
    assert hdr[1].geometry().top() >= btn[1].geometry().bottom() - 1
    assert hdr[2].geometry().top() >= btn[2].geometry().bottom() - 1


def test_page_without_headings_has_no_header(win):
    s = win.sheet
    put(s, 100, [("A", B)])
    put(s, 1300, [("C", B)])
    s._add_marker(500)
    s._add_marker(1000)
    shown(win)
    labels = page_labels(win)
    assert "Page 2" not in labels and "Page 1" in labels


def test_duplicates_listed_twice(win):
    put(win.sheet, 40, [("Same", B)])
    put(win.sheet, 200, [("Same", B)])
    assert shown(win) == ["Same", "Same"]


# ---- elision, tooltip, accessibility ----------------------------------------------------

def test_elide_boundaries(win):
    put(win.sheet, 40, [("a" * 32, B)])
    put(win.sheet, 120, [("b" * 33, B)])
    out = shown(win)
    assert out[0] == "a" * 32
    assert len(out[1]) == 32 and out[1].endswith("…")
    assert win.side_panel.outline_buttons[1].toolTip().count("b") == 33


def test_tooltip_has_page_and_accessible_name(win):
    s = win.sheet
    put(s, 700, [("Second page heading that is quite long indeed", B)])
    s._add_marker(500)
    shown(win)
    btn = win.side_panel.outline_buttons[0]
    assert "Second page heading that is quite long indeed" in btn.toolTip()
    assert "2" in btn.toolTip()
    assert btn.accessibleName() == "Second page heading that is quite long indeed"


# ---- click ------------------------------------------------------------------------------

def test_click_keeps_zoom_and_editing_focus(win):
    s = win.sheet
    editing = s.add_region("math", QPointF(40, 20), "a := 1")
    for i in range(25):
        put(s, 100 + i * 120, [(f"p{i}", N)])
    target = put(s, 3000, [("Far away", B)])
    s._update_rect()
    editing.start_editing()
    QApplication.processEvents()
    assert editing.editing
    focus_before = QApplication.focusWidget()
    zoom = win.view.zoom()
    shown(win)
    win.side_panel.outline_buttons[0].click()
    QApplication.processEvents()
    assert target.isSelected()
    assert win.view.zoom() == zoom
    assert QApplication.focusWidget() is focus_before
    assert editing.editing
    vis = win.view.mapToScene(win.view.viewport().rect()).boundingRect()
    assert vis.contains(target.sceneBoundingRect().topLeft())


def test_click_second_entry_selects_only_it(win):
    s = win.sheet
    a = put(s, 40, [("A", B)])
    b = put(s, 200, [("B", B)])
    shown(win)
    win.side_panel.outline_buttons[0].click()
    win.side_panel.outline_buttons[1].click()
    assert b.isSelected() and not a.isSelected()


def test_stale_entry_click_is_noop(win):
    s = win.sheet
    r = put(s, 40, [("Gone", B)])
    shown(win)
    btn = win.side_panel.outline_buttons[0]
    s.remove_regions([r])
    btn.click()      # must not raise
    QApplication.processEvents()


# ---- empty state ------------------------------------------------------------------------

def test_empty_state_text_exact(win):
    shown(win)
    assert page_labels(win) == [
        "No headings yet. Make the first line of a text region bold (Ctrl+B) to list it here."]
    assert win.side_panel.tabs.widget(OUTLINE).findChildren(QPushButton) == []


def test_empty_state_returns_after_last_heading_deleted(win):
    r = put(win.sheet, 40, [("H", B)])
    assert shown(win) == ["H"]
    win.sheet.remove_regions([r])
    assert shown(win) == []
    assert page_labels(win)[0].startswith("No headings yet")


# ---- refresh ----------------------------------------------------------------------------

def test_selecting_tab_triggers_rebuild_without_manual_call(win):
    put(win.sheet, 40, [("Auto", B)])
    win.side_panel.tabs.setCurrentIndex(0)
    win.side_panel.tabs.setCurrentIndex(OUTLINE)
    QApplication.processEvents()
    assert [b.text() for b in win.side_panel.outline_buttons] == ["Auto"]


def test_debounced_add_and_not_immediate(win):
    s = win.sheet
    win.side_panel.tabs.setCurrentIndex(OUTLINE)
    QApplication.processEvents()
    calls = []
    orig = win.side_panel.rebuild_outline
    win.side_panel.rebuild_outline = lambda: calls.append(time.monotonic()) or orig()
    t0 = time.monotonic()
    put(s, 40, [("One", B)])
    put(s, 100, [("Two", B)])
    put(s, 160, [("Three", B)])
    QApplication.processEvents()
    assert calls == [], "rebuild must be debounced, not synchronous"
    QTest.qWait(600)
    assert len(calls) == 1, f"burst should coalesce into one rebuild, got {len(calls)}"
    assert 0.25 <= calls[0] - t0 <= 0.5
    assert [b.text() for b in win.side_panel.outline_buttons] == ["One", "Two", "Three"]


def test_delete_move_and_pagebreak_refresh(win):
    s = win.sheet
    a = put(s, 40, [("A", B)])
    b = put(s, 200, [("B", B)])
    shown(win)
    s.remove_regions([a])
    QTest.qWait(500)
    assert [x.text() for x in win.side_panel.outline_buttons] == ["B"]
    b.setPos(QPointF(40, 900))
    s._add_marker(500)
    QTest.qWait(500)
    assert "Page 2" in page_labels(win)


def test_no_rebuild_while_other_tab_selected(win):
    s = win.sheet
    shown(win)
    win.side_panel.tabs.setCurrentIndex(0)
    calls = []
    orig = win.side_panel.rebuild_outline
    win.side_panel.rebuild_outline = lambda: calls.append(1) or orig()
    put(s, 40, [("X", B)])
    s.remove_regions([s.regions()[-1]])
    s._add_marker(300)
    QTest.qWait(500)
    assert calls == []


# ---- load / save ------------------------------------------------------------------------

def test_load_lists_and_file_bytes_unchanged(win, tmp_path):
    s = win.sheet
    put(s, 40, [("Saved head", B)])
    put(s, 120, [("body", N)])
    p1, p2 = tmp_path / "a.lsheet", tmp_path / "b.lsheet"
    s.to_document().save(p1)
    s.clear_sheet()
    assert shown(win) == []
    s.load_document(SheetDocument.load(p1))
    assert shown(win) == ["Saved head"]
    s.to_document().save(p2)
    assert p1.read_bytes() == p2.read_bytes()
    assert "outline" not in p1.read_text().lower()


def test_clear_sheet_empties_list(win):
    put(win.sheet, 40, [("H", B)])
    shown(win)
    win.sheet.clear_sheet()
    QTest.qWait(450)
    assert win.side_panel.outline_buttons == []


# ---- performance and neighbours ---------------------------------------------------------

def test_200_headings_rebuild_fast(win):
    for i in range(200):
        put(win.sheet, 40 + i * 30, [(f"Heading number {i}", B)])
    win.side_panel.tabs.setCurrentIndex(OUTLINE)
    QApplication.processEvents()
    t = time.perf_counter()
    win.side_panel.rebuild_outline()
    dt = time.perf_counter() - t
    assert len(win.side_panel.outline_buttons) == 200
    assert dt < 0.25, f"rebuild took {dt * 1000:.0f} ms (spec: about 100 ms)"


def test_tab_order_and_data_still_placeholder(win):
    tabs = win.side_panel.tabs
    names = [tabs.tabText(i) for i in range(tabs.count())]
    assert len(names) == 10 and names[OUTLINE] == "Outline" and names[DATA] == "Data"
    assert len(tabs.widget(DATA).findChildren(QLabel)) == 1
    assert len(tabs.widget(DATA).findChildren(QPushButton)) == 4   # spec 028 action buttons
