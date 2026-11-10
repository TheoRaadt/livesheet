"""Tests for spec 022 (window-wide wrapping tab strip + horizontal button band), criteria 2-23.
Criterion 1 (unchanged tab model) is covered by the existing side-panel test files.

Row counts are derived from the buttons' own ``sizeHint()`` widths by greedy fill, never
hard-coded, because widths depend on the platform font.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QWidget,
)

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.sidepanel import MATH_TOKENS, OUTLINE_EMPTY, PLACEHOLDER_TABS, TAB_ORDER  # noqa: E402
from livesheet.gui.tabstrip import GAP, greedy_rows  # noqa: E402
from livesheet.gui.theme import MODE_DARK, MODE_LIGHT, apply_theme  # noqa: E402

WIDTHS = (600, 1000, 1600)
MARGIN = 4


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(mw_module, "QSettings",
                        lambda *_a, **_k: QSettings(ini, QSettings.Format.IniFormat))
    return ini


@pytest.fixture(autouse=True)
def restore_light_theme():
    yield
    apply_theme(QApplication.instance(), MODE_LIGHT)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _window(width: int = 1000, height: int = 800) -> MainWindow:
    _app()
    win = MainWindow()
    win.sheet.set_modified(False)
    win.resize(width, height)
    win.show()
    QApplication.processEvents()
    return win


def _resize(win: MainWindow, width: int, height: int = 800) -> None:
    win.resize(width, height)
    QApplication.processEvents()
    QApplication.processEvents()


def _close(win: MainWindow) -> None:
    win.sheet.set_modified(False)
    win.close()


def _origin(win: MainWindow, widget: QWidget) -> QPoint:
    return widget.mapTo(win, QPoint(0, 0))


def _buttons(win):
    return win.side_panel.strip.buttons()


def _expected_rows(win) -> list[list[int]]:
    strip = win.side_panel.strip
    return greedy_rows([b.sizeHint().width() for b in _buttons(win)], strip.width(), GAP)


def _visual_rows(win) -> list[list[int]]:
    by_y: dict[int, list[int]] = {}
    for i, b in enumerate(_buttons(win)):
        by_y.setdefault(b.y(), []).append(i)
    return [sorted(by_y[y], key=lambda i: _buttons(win)[i].x()) for y in sorted(by_y)]


def _inner_buttons(page: QWidget) -> list[QPushButton]:
    return page.findChildren(QPushButton)


# -- 2 placement -------------------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c2_placement_under_toolbar_above_canvas_full_width(width):
    win = _window(width)
    panel = win.side_panel
    toolbar_bottom = _origin(win, win.standard_toolbar).y() + win.standard_toolbar.height()
    strip, band = panel.strip, panel.band
    assert _origin(win, strip).y() >= toolbar_bottom
    assert _origin(win, band).y() >= _origin(win, strip).y() + strip.height()
    assert _origin(win, win.view).y() >= _origin(win, band).y() + band.height()
    for w in (strip, band):
        left = _origin(win, w).x()
        assert left <= MARGIN + 1
        assert left + w.width() >= win.centralWidget().width() - MARGIN - 1
    _close(win)


# -- 3, 4 labels and visibility ------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c3_full_labels(width):
    win = _window(width)
    tabs = win.side_panel.tabs
    for i, b in enumerate(_buttons(win)):
        assert b.text() == tabs.tabText(i) == TAB_ORDER[i]
        assert b.width() >= b.fontMetrics().horizontalAdvance(b.text())
        assert b.width() >= b.sizeHint().width()
    _close(win)


@pytest.mark.parametrize("width", WIDTHS)
def test_c4_all_visible_no_scroll_arrows(width):
    win = _window(width)
    strip = win.side_panel.strip
    bar = win.side_panel.tabs.tabBar()
    assert not bar.isVisible()
    assert len(_buttons(win)) == 10
    for b in _buttons(win):
        assert b.isVisible()
        assert strip.rect().contains(b.geometry())
    _close(win)


# -- 5-7 row counts ------------------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c5_c6_c7_row_counts_equal_greedy_fill(width):
    win = _window(width)
    rows = _visual_rows(win)
    assert rows == _expected_rows(win)
    assert rows[0][0] == 0   # row 1 starts with Elements
    total = sum(b.sizeHint().width() for b in _buttons(win)) + GAP * 9
    assert (len(rows) == 1) == (total <= win.side_panel.strip.width())
    if width >= 1000:
        assert len(rows) == 1   # sanity at the reference font: ~750 px of buttons
    _close(win)


# -- 8 justification -----------------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c8_rows_justified_equal_height(width):
    win = _window(width)
    strip = win.side_panel.strip
    for row in _visual_rows(win):
        bs = [_buttons(win)[i] for i in row]
        assert abs(sum(b.width() for b in bs) + GAP * (len(bs) - 1) - strip.width()) <= 1
    assert len({b.height() for b in _buttons(win)}) == 1
    _close(win)


# -- 9 order -------------------------------------------------------------------------------------

def test_c9_order_stable_over_resizes():
    win = _window(1600)
    for w in (1000, 600, 800, 450, 1600):
        _resize(win, w)
        ordered = [i for row in _visual_rows(win) for i in row]
        assert ordered == list(range(10))
        assert [_buttons(win)[i].text() for i in ordered] == list(TAB_ORDER)
    _close(win)


# -- 10 active highlight -------------------------------------------------------------------------

def test_c10_exactly_one_selected_matches_current_index():
    win = _window(1000)
    tabs = win.side_panel.tabs
    for k in range(10):
        tabs.setCurrentIndex(k)
        QApplication.processEvents()
        selected = [i for i, b in enumerate(_buttons(win)) if b.isChecked()]
        assert selected == [k]
    _close(win)


@pytest.mark.parametrize("mode", [MODE_LIGHT, MODE_DARK])
def test_c10_selected_rendering_differs_in_two_ways(mode):
    win = _window(1000)
    apply_theme(_app(), mode)
    QApplication.processEvents()
    b0, b1 = _buttons(win)[0], _buttons(win)[1]
    win.side_panel.tabs.setCurrentIndex(0)
    QApplication.processEvents()
    img0 = b0.grab().toImage()
    img1 = b1.grab().toImage()
    accent = b0.palette().color(b0.palette().ColorRole.Highlight)
    # cue 1: heavy underline in the accent colour only on the selected button
    assert QColor(img0.pixel(b0.width() // 2, b0.height() - 2)) == accent
    assert QColor(img1.pixel(b1.width() // 2, b1.height() - 2)) != accent
    # cue 2: the fill (tint) differs from the unselected fill
    assert QColor(img0.pixel(3, 3)) != QColor(img1.pixel(3, 3))
    _close(win)


# -- 11 click ------------------------------------------------------------------------------------

def test_c11_click_selects_once_and_reclick_is_silent():
    win = _window(1000)
    tabs = win.side_panel.tabs
    spy = QSignalSpy(tabs.currentChanged)
    for k in (4, 2, 9, 0):
        before = spy.count()
        _buttons(win)[k].click()
        QApplication.processEvents()
        assert tabs.currentIndex() == k
        assert tabs.currentWidget() is tabs.widget(k)
        assert win.side_panel.tabs.currentWidget().isVisible()
        assert spy.count() == before + 1
        assert spy.at(spy.count() - 1)[0] == k
        again = spy.count()
        _buttons(win)[k].click()
        assert spy.count() == again
        assert _buttons(win)[k].isChecked()
    _close(win)


# -- 12 keyboard ---------------------------------------------------------------------------------

def _key(win, button, key):
    QTest.keyClick(button, key)
    QApplication.processEvents()


def test_c12_arrow_home_end_navigation():
    win = _window(1600)
    tabs = win.side_panel.tabs
    spy = QSignalSpy(tabs.currentChanged)
    b = _buttons(win)
    b[0].setFocus()
    _key(win, b[0], Qt.Key.Key_Right)
    _key(win, b[1], Qt.Key.Key_Right)
    assert tabs.currentIndex() == 2
    _key(win, b[2], Qt.Key.Key_Left)
    assert tabs.currentIndex() == 1
    _key(win, b[1], Qt.Key.Key_End)
    assert tabs.currentIndex() == 9
    n = spy.count()
    _key(win, b[9], Qt.Key.Key_Right)
    assert tabs.currentIndex() == 9 and spy.count() == n
    _key(win, b[9], Qt.Key.Key_Home)
    assert tabs.currentIndex() == 0
    n = spy.count()
    _key(win, b[0], Qt.Key.Key_Left)
    assert tabs.currentIndex() == 0 and spy.count() == n
    _close(win)


def test_c12_up_down_and_space_enter_in_two_rows():
    win = _window(600)
    rows = _visual_rows(win)
    assert len(rows) >= 2
    tabs = win.side_panel.tabs
    b = _buttons(win)
    start = rows[0][1]
    tabs.setCurrentIndex(start)
    cx = b[start].geometry().center().x()
    expected = min(rows[1], key=lambda k: abs(b[k].geometry().center().x() - cx))
    _key(win, b[start], Qt.Key.Key_Down)
    assert tabs.currentIndex() == expected
    _key(win, b[expected], Qt.Key.Key_Down)
    if len(rows) == 2:
        assert tabs.currentIndex() == expected
    tabs.setCurrentIndex(start)
    _key(win, b[start], Qt.Key.Key_Up)
    assert tabs.currentIndex() == start   # nothing above row 1
    # Space / Enter on a focused, unselected button select it, once
    spy = QSignalSpy(tabs.currentChanged)
    b[3].setFocus()
    _key(win, b[3], Qt.Key.Key_Space)
    assert tabs.currentIndex() == 3 and spy.count() == 1
    b[5].setFocus()
    _key(win, b[5], Qt.Key.Key_Return)
    assert tabs.currentIndex() == 5 and spy.count() == 2
    _close(win)


# -- 13 resize relayout --------------------------------------------------------------------------

def test_c13_resize_relayout_is_repeatable_and_stacked():
    win = _window(1600)
    seen: dict[int, tuple] = {}
    counts = []
    for w in (1600, 1000, 600, 1000, 1600):
        _resize(win, w)
        rows = _visual_rows(win)
        snapshot = (len(rows), [(b.x(), b.y(), b.width()) for b in _buttons(win)])
        if w in seen:
            assert seen[w] == snapshot
        seen[w] = snapshot
        counts.append(len(rows))
        panel = win.side_panel
        strip_bottom = _origin(win, panel.strip).y() + panel.strip.height()
        band_top = _origin(win, panel.band).y()
        assert 0 <= band_top - strip_bottom <= 4
        band_bottom = band_top + panel.band.height()
        assert 0 <= _origin(win, win.view).y() - band_bottom <= MARGIN + 1
    assert counts[0] <= counts[1] <= counts[2]
    assert counts[2] >= counts[3] >= counts[4]
    _close(win)


# -- 14 band content -----------------------------------------------------------------------------

def test_c14_elements_band_content_and_alpha_inserts():
    win = _window(1600)
    tabs = win.side_panel.tabs
    tabs.setCurrentIndex(0)
    page = tabs.widget(0)
    assert len(_inner_buttons(page)) == 40
    headers = {l.text(): l for l in page.findChildren(QLabel)}
    assert {"Statements", "Constants", "Greek letters"} <= set(headers)
    ys = [headers[h].y() for h in ("Statements", "Constants", "Greek letters")]
    assert ys == sorted(set(ys))   # each starts a new row
    for h in headers.values():
        for btn in _inner_buttons(page):
            assert not (btn.y() == h.y() and btn.x() < h.x())   # header is first on its row
    win.side_panel.symbol_buttons["α"].click()
    assert win.sheet.editing_region().source == "alpha"
    _close(win)


def test_c14_mechanical_headers_and_full_label():
    win = _window(1000)
    win.side_panel.tabs.setCurrentIndex(5)
    page = win.side_panel.tabs.widget(5)
    texts = {l.text() for l in page.findChildren(QLabel)}
    assert {"Statics", "Strength of Materials"} <= texts
    btn = win.side_panel.symbol_buttons["Resultant (2 forces)"]
    assert btn.width() >= btn.sizeHint().width()
    assert btn.fontMetrics().horizontalAdvance(btn.text()) <= btn.width()
    _close(win)


def test_c14_algebra_and_calculus_counts_no_header():
    win = _window(1000)
    tabs = win.side_panel.tabs
    assert len(_inner_buttons(tabs.widget(1))) == 4
    assert len(_inner_buttons(tabs.widget(2))) == 2
    assert not tabs.widget(1).findChildren(QLabel)
    assert not tabs.widget(2).findChildren(QLabel)
    _close(win)


# -- 15 placeholders -----------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(PLACEHOLDER_TABS))
def test_c15_placeholder_tabs(name):
    win = _window(1000)
    i = TAB_ORDER.index(name)
    win.side_panel.tabs.setCurrentIndex(i)
    page = win.side_panel.tabs.widget(i)
    assert not page.findChildren(QPushButton)
    labels = page.findChildren(QLabel)
    assert len(labels) == 1 and labels[0].text() == PLACEHOLDER_TABS[name]
    assert page.isVisible()
    _close(win)


# -- 16 stable band height -----------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c16_band_height_and_canvas_top_stable_across_tabs(width):
    win = _window(width)
    panel = win.side_panel
    heights, tops = set(), set()
    for k in range(10):
        panel.tabs.setCurrentIndex(k)
        QApplication.processEvents()
        heights.add(panel.band.height())
        tops.add(_origin(win, win.view).y())
    assert len(heights) == 1 and len(tops) == 1
    assert panel.band.height() <= panel.band_clamp()
    _close(win)


def test_c16_tall_page_scrolls_inside_band_strip_unaffected():
    win = _window(420, 600)
    panel = win.side_panel
    clamp = panel.band_clamp()
    assert panel.band.height() <= clamp
    needed = max(panel._page_height(panel.tabs.widget(i), panel.width() - 2 * MARGIN)
                 for i in range(panel.tabs.count()))
    assert needed > clamp   # narrow window: the Chemical page is taller than the clamp
    assert panel.band.height() == clamp
    chem = panel.tabs.widget(7)
    panel.tabs.setCurrentIndex(7)
    QApplication.processEvents()
    assert isinstance(chem, QScrollArea)
    assert chem.verticalScrollBar().maximum() > 0
    strip = panel.strip
    assert strip.height() == strip.heightForWidth(strip.width())
    _close(win)


# -- 17 first tabs reachable ---------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
def test_c17_first_tabs_reachable(width):
    win = _window(width)
    for idx, label in ((0, "α"), (1, "√"), (2, "d/dx")):
        b = _buttons(win)[idx]
        assert b.isVisible() and win.side_panel.strip.rect().contains(b.geometry())
        QTest.mouseClick(b, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert win.side_panel.tabs.currentIndex() == idx
        assert win.side_panel.symbol_buttons[label].isVisibleTo(win.side_panel.tabs)
    token = next(t for _c, lab, t, _tip in MATH_TOKENS if lab == "d/dx")
    assert token.startswith("diff(")
    _close(win)


# -- 18 dock retired -----------------------------------------------------------------------------

def test_c18_dock_retired_and_toggle_hides_both():
    win = _window(1000)
    assert win.findChild(QDockWidget, "side-panel-dock") is None
    assert _origin(win, win.view).x() == 0
    top_shown = _origin(win, win.view).y()
    panel = win.side_panel
    win.side_panel.tabs.setCurrentIndex(3)
    panel.toggleViewAction().trigger()
    QApplication.processEvents()
    assert not panel.strip.isVisible() and not panel.band.isVisible()
    assert _origin(win, win.view).y() < top_shown
    panel.toggleViewAction().trigger()
    QApplication.processEvents()
    assert panel.strip.isVisible() and panel.band.isVisible()
    assert panel.tabs.currentIndex() == 3
    assert _origin(win, win.view).y() == top_shown
    _close(win)


def test_c18_view_menu_entry_is_side_panel():
    win = _window(1000)
    action = win.side_panel.toggleViewAction()
    assert action.text() == "Side Panel" and action.isCheckable()
    assert any(a is action for m in win.menuBar().actions() if m.menu()
               for a in m.menu().actions())
    _close(win)


def test_c18_stale_window_state_naming_dock_loads(isolated_settings):
    _app()
    old = QMainWindow()
    dock = QDockWidget("Side Panel", old)
    dock.setObjectName("side-panel-dock")
    old.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    state = old.saveState()
    QSettings(isolated_settings, QSettings.Format.IniFormat).setValue("window_state", state)
    win = _window(1000)
    assert win.side_panel.strip.isVisible()
    _close(win)


# -- 19 persistence ------------------------------------------------------------------------------

def test_c19_selected_tab_persists_and_band_shows_it():
    win = _window(1000)
    win.side_panel.tabs.setCurrentIndex(8)
    _close(win)
    win2 = _window(1000)
    assert win2.side_panel.tabs.currentIndex() == 8
    assert [i for i, b in enumerate(_buttons(win2)) if b.isChecked()] == [8]
    page = win2.side_panel.tabs.currentWidget()
    assert page.isVisible()
    assert page.findChildren(QLabel)[0].text() == OUTLINE_EMPTY
    _close(win2)


@pytest.mark.parametrize("saved,expected", [(99, 9), (-5, 0)])
def test_c19_out_of_range_saved_index_is_clamped(isolated_settings, saved, expected):
    QSettings(isolated_settings, QSettings.Format.IniFormat).setValue("side_panel_tab", saved)
    win = _window(1000)
    assert win.side_panel.tabs.currentIndex() == expected
    assert [i for i, b in enumerate(_buttons(win)) if b.isChecked()] == [expected]
    _close(win)


# -- 20 many tabs --------------------------------------------------------------------------------

def test_c20_appending_and_removing_tabs_reflows():
    win = _window(600)
    tabs = win.side_panel.tabs
    tabs.addTab(QWidget(), "Eleventh")
    tabs.addTab(QWidget(), "Twelfth")
    QApplication.processEvents()
    assert [b.text() for b in _buttons(win)][-2:] == ["Eleventh", "Twelfth"]
    assert [i for row in _visual_rows(win) for i in row] == list(range(12))
    assert _visual_rows(win) == _expected_rows(win)
    _buttons(win)[11].click()
    assert tabs.currentIndex() == 11 and tabs.currentWidget() is tabs.widget(11)
    tabs.removeTab(11)
    tabs.removeTab(10)
    QApplication.processEvents()
    assert len(_buttons(win)) == 10
    assert _visual_rows(win) == _expected_rows(win)
    assert sum(b.isChecked() for b in _buttons(win)) == 1
    _close(win)


# -- 21 minimum width ----------------------------------------------------------------------------

def test_c21_minimum_width_every_tab_clickable():
    win = _window(1000)
    widest = max(b.sizeHint().width() for b in _buttons(win))
    assert win.minimumSizeHint().width() >= widest + 2 * MARGIN
    win.resize(win.minimumSizeHint().width(), 800)
    QApplication.processEvents()
    QApplication.processEvents()
    strip = win.side_panel.strip
    for i, b in enumerate(_buttons(win)):
        assert b.width() > 0 and b.height() > 0
        assert b.text() == TAB_ORDER[i]
        assert b.width() >= b.sizeHint().width()
        QTest.mouseClick(b, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert win.side_panel.tabs.currentIndex() == i
    assert len(_visual_rows(win)) <= 10
    assert strip.height() == strip.heightForWidth(strip.width())
    _close(win)


# -- 22 theming and accessibility ----------------------------------------------------------------

def test_c22_theme_switch_updates_without_restart_and_a11y_names():
    win = _window(1000)
    strip = win.side_panel.strip
    assert strip.accessibleName() == "Side panel categories"
    for i, b in enumerate(_buttons(win)):
        assert b.accessibleName() == TAB_ORDER[i]
    b = _buttons(win)[1]
    apply_theme(_app(), MODE_LIGHT)
    QApplication.processEvents()
    light = b.grab().toImage()
    apply_theme(_app(), MODE_DARK)
    QApplication.processEvents()
    dark = b.grab().toImage()
    assert light != dark
    _close(win)


def test_c22_focus_ring_distinct_on_focused_button():
    win = _window(1000)
    win.activateWindow()
    b = _buttons(win)[0]
    unfocused = b.grab().toImage()
    b.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    if not b.hasFocus():
        pytest.skip("offscreen platform did not grant focus")
    assert b.grab().toImage() != unfocused
    _close(win)


# -- 23 insert behaviour -------------------------------------------------------------------------

def test_c23_band_button_inserts_at_cursor_and_tab_switch_keeps_region():
    win = _window(1000)
    region = win.sheet.insert_region("math")
    region.editor.setPlainText("x")
    cursor = region.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    region.editor.setTextCursor(cursor)
    QTest.mouseClick(_buttons(win)[1], Qt.MouseButton.LeftButton)   # switch tab by click
    QApplication.processEvents()
    assert win.sheet.editing_region() is region
    win.side_panel.symbol_buttons["√"].click()
    assert region.source.startswith("x")
    assert region.source != "x"
    assert win.sheet.editing_region() is region
    _close(win)


def test_strip_keeps_full_height_with_huge_font_in_short_window():
    """Review D1: at 60 pt in a short window the band shrinks first, never the strip."""
    app = _app()
    old = app.font()
    big = app.font()
    big.setPointSize(60)
    app.setFont(big)
    try:
        win = MainWindow()
        win.resize(100, 700)
        win.show()
        for _ in range(3):
            QApplication.processEvents()
        strip = win.side_panel.strip
        assert strip.height() >= strip.heightForWidth(strip.width())
        last = strip.buttons()[-1]
        assert last.geometry().bottom() < strip.height()
        _close(win)
    finally:
        app.setFont(old)
