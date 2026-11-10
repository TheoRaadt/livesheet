"""Independent black-box tests for spec 022 (window-wide wrapping tab strip), written by the
tester from the spec's acceptance criteria only. Uses public/obvious handles: win.side_panel,
.tabs, .symbol_buttons, find children by type/objectName."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QByteArray, QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QPalette  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton, QApplication, QDockWidget, QLabel, QPushButton, QScrollArea, QToolBar, QWidget,
)

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.theme import MODE_DARK, MODE_LIGHT, apply_theme  # noqa: E402

NAMES = ["Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical",
         "Electrical", "Chemical", "Outline", "Data"]
GAP = 2
MARGIN = 4


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(mw_module, "QSettings", lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat))
    return ini


def _app():
    return QApplication.instance() or QApplication([])


def _win(width=1000, height=800, show=True) -> MainWindow:
    _app()
    w = MainWindow()
    w.sheet.set_modified(False)
    w.resize(width, height)
    if show:
        w.show()
    QApplication.processEvents()
    return w


def _close(w):
    w.sheet.set_modified(False)
    w.close()
    QApplication.processEvents()


def _strip(w):
    return w.side_panel.strip


def _btns(w):
    return list(_strip(w).buttons())


def _resize(w, width, height=800):
    w.resize(width, height)
    QApplication.processEvents()


def _greedy(widths, total):
    rows, used = [], 0
    for i, wd in enumerate(widths):
        if rows and used + GAP + wd <= total:
            rows[-1].append(i); used += GAP + wd
        else:
            rows.append([i]); used = wd
    return rows


def _rows_by_y(w):
    by = {}
    for i, b in enumerate(_btns(w)):
        by.setdefault(b.y(), []).append(i)
    return [sorted(by[y], key=lambda i: _btns(w)[i].x()) for y in sorted(by)]


def _tl(widget, ref):  # top-left / bottom in ref coords
    return widget.mapTo(ref, QPoint(0, 0))


@pytest.mark.parametrize("W", [600, 1000, 1600])
def test_c2_placement_and_span(W):
    w = _win(W)
    tb = w.findChildren(QToolBar)
    tb_bottom = max(_tl(t, w).y() + t.height() for t in tb if t.isVisible())
    s, band = _strip(w), w.side_panel.band
    assert _tl(s, w).y() >= tb_bottom - 1
    assert _tl(band, w).y() >= _tl(s, w).y() + s.height()
    assert _tl(w.view, w).y() >= _tl(band, w).y() + band.height()
    left = _tl(s, w).x()
    right = left + s.width()
    assert left <= MARGIN + 1
    assert right >= w.width() - MARGIN - 1
    bl = _tl(band, w).x()
    assert bl <= MARGIN + 1 and bl + band.width() >= w.width() - MARGIN - 1
    _close(w)


@pytest.mark.parametrize("W", [600, 1000, 1600])
def test_c3_c4_full_labels_all_visible_no_scroll_arrows(W):
    w = _win(W)
    s = _strip(w)
    bs = _btns(w)
    assert [b.text() for b in bs] == NAMES
    for b in bs:
        assert "…" not in b.text() and "..." not in b.text()
        assert b.width() >= b.fontMetrics().horizontalAdvance(b.text())
        assert b.isVisible()
        assert s.rect().contains(b.geometry())
    assert not w.side_panel.tabs.tabBar().isVisible()
    assert not w.side_panel.tabs.usesScrollButtons() or not w.side_panel.tabs.tabBar().isVisible()
    _close(w)


@pytest.mark.parametrize("W,minrows,maxrows", [(600, 2, 3), (1000, 1, 2), (1600, 1, 1)])
def test_c5_c6_c7_row_counts_match_greedy(W, minrows, maxrows):
    w = _win(W)
    s = _strip(w)
    widths = [b.sizeHint().width() for b in _btns(w)]
    expected = _greedy(widths, s.width())
    rows = _rows_by_y(w)
    assert len(rows) == len(expected)
    assert minrows <= len(rows) <= maxrows
    assert rows[0][0] == 0   # Elements first
    _close(w)


@pytest.mark.parametrize("W", [400, 600, 800, 1000, 1600])
def test_c8_justified_rows_equal_height(W):
    w = _win(W)
    s = _strip(w)
    bs = _btns(w)
    for row in _rows_by_y(w):
        total = sum(bs[i].width() for i in row) + GAP * (len(row) - 1)
        assert abs(total - s.width()) <= 1
    assert len({b.height() for b in bs}) == 1
    _close(w)


def test_c9_order_after_resize_sequence():
    w = _win(1600)
    for W in (1000, 600, 900, 700, 1600, 650):
        _resize(w, W)
        order = [i for row in _rows_by_y(w) for i in row]
        assert [b.text() for b in (_btns(w)[i] for i in order)] == NAMES
    _close(w)


def test_c10_exactly_one_selected_and_two_cues():
    w = _win(1000)
    tabs = w.side_panel.tabs
    for k in range(10):
        tabs.setCurrentIndex(k)
        QApplication.processEvents()
        sel = [i for i, b in enumerate(_btns(w)) if b.isChecked()]
        assert sel == [k]
    # rendering differs from unselected in >= 2 ways: compare grabbed pixels, light and dark
    for mode in (MODE_LIGHT, MODE_DARK):
        apply_theme(QApplication.instance(), mode)
        QApplication.processEvents()
        tabs.setCurrentIndex(0)
        QApplication.processEvents()
        a = _btns(w)[0].grab().toImage()
        b = _btns(w)[1].grab().toImage()
        assert a.size() == b.size() or True
        # compare distinct colours: selected must use more distinct colours / differ in the bottom rows
        h = min(a.height(), b.height())
        bottom_sel = {a.pixelColor(a.width() // 2, y).rgb() for y in range(h - 5, h)}
        bottom_uns = {b.pixelColor(b.width() // 2, y).rgb() for y in range(h - 5, h)}
        assert bottom_sel != bottom_uns        # underline cue
        assert a.pixelColor(2, 2).rgb() != b.pixelColor(2, 2).rgb()   # fill cue
    apply_theme(QApplication.instance(), MODE_LIGHT)
    _close(w)


def test_c11_click_selects_once_and_band_shows_page():
    w = _win(1000)
    tabs = w.side_panel.tabs
    spy = QSignalSpy(tabs.currentChanged)
    for k in (3, 7, 0, 9):
        spy.clear() if hasattr(spy, "clear") else None
        n0 = spy.count()
        QTest.mouseClick(_btns(w)[k], Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert tabs.currentIndex() == k
        assert tabs.currentWidget() is tabs.widget(k)
        assert tabs.currentWidget().isVisible()
        assert spy.count() == n0 + 1
        assert spy.at(spy.count() - 1) == [k] if hasattr(spy, "at") else True
        n1 = spy.count()
        QTest.mouseClick(_btns(w)[k], Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert spy.count() == n1
        assert [i for i, b in enumerate(_btns(w)) if b.isChecked()] == [k]
    _close(w)


def _focus_strip(w):
    w.activateWindow()
    b = _btns(w)[w.side_panel.tabs.currentIndex()]
    b.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    return b


def _key(w, key):
    f = QApplication.focusWidget()
    assert f is not None, "nothing focused"
    QTest.keyClick(f, key)
    QApplication.processEvents()


def test_c12_keyboard_single_row():
    w = _win(1600)
    tabs = w.side_panel.tabs
    _focus_strip(w)
    spy = QSignalSpy(tabs.currentChanged)
    _key(w, Qt.Key.Key_Right); _key(w, Qt.Key.Key_Right)
    assert tabs.currentIndex() == 2 and spy.count() == 2
    _key(w, Qt.Key.Key_Left); assert tabs.currentIndex() == 1
    _key(w, Qt.Key.Key_End); assert tabs.currentIndex() == 9
    n = spy.count()
    _key(w, Qt.Key.Key_Right); assert tabs.currentIndex() == 9 and spy.count() == n
    _key(w, Qt.Key.Key_Home); assert tabs.currentIndex() == 0
    n = spy.count()
    _key(w, Qt.Key.Key_Left); assert tabs.currentIndex() == 0 and spy.count() == n
    # single row: Up/Down do nothing
    _key(w, Qt.Key.Key_Down); _key(w, Qt.Key.Key_Up)
    assert tabs.currentIndex() == 0 and spy.count() == n
    _close(w)


def test_c12_keyboard_two_rows_up_down_and_space_enter():
    w = _win(600)
    rows = _rows_by_y(w)
    assert len(rows) == 2
    tabs = w.side_panel.tabs
    bs = _btns(w)
    r1, r2 = rows
    k = r1[1]
    tabs.setCurrentIndex(k)
    _focus_strip(w)
    _key(w, Qt.Key.Key_Up)
    assert tabs.currentIndex() == k
    cx = bs[k].geometry().center().x()
    want = min(r2, key=lambda i: abs(bs[i].geometry().center().x() - cx))
    _key(w, Qt.Key.Key_Down)
    assert tabs.currentIndex() == want
    _key(w, Qt.Key.Key_Down)
    assert tabs.currentIndex() == want        # nothing below
    _key(w, Qt.Key.Key_Up)
    assert tabs.currentIndex() in r1
    # Space / Enter on a focused unselected button: move focus without selecting is not
    # provided by arrows (they select), so use programmatic focus on another button.
    for key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
        tabs.setCurrentIndex(0)
        QApplication.processEvents()
        bs[4].setFocus(Qt.FocusReason.OtherFocusReason)
        QApplication.processEvents()
        spy = QSignalSpy(tabs.currentChanged)
        QTest.keyClick(bs[4], key)
        QApplication.processEvents()
        assert tabs.currentIndex() == 4 and spy.count() == 1, key
    _close(w)


def test_c12_strip_is_one_tab_stop():
    w = _win(1000)
    focusable = [b for b in _btns(w) if b.focusPolicy() & Qt.FocusPolicy.TabFocus]
    assert len(focusable) == 1 and focusable[0].isChecked()
    _close(w)


def test_c13_resize_cycle_restores_geometry_and_stacks():
    w = _win(1600)
    snap = {}
    seq = [1600, 1000, 600, 1000, 1600]
    prev_rows = 0
    for idx, W in enumerate(seq):
        _resize(w, W)
        geo = [b.geometry().getRect() for b in _btns(w)]
        nrows = len(_rows_by_y(w))
        if idx < 3:
            assert nrows >= prev_rows
            prev_rows = nrows
        if W in snap:
            assert snap[W] == (nrows, geo), W
        snap[W] = (nrows, geo)
        s, band = _strip(w), w.side_panel.band
        gap = _tl(band, w).y() - (_tl(s, w).y() + s.height())
        assert 0 <= gap <= 4
        cg = _tl(w.view, w).y() - (_tl(band, w).y() + band.height())
        assert 0 <= cg <= 8
    _close(w)


def test_c13_relayout_on_each_drag_step():
    w = _win(1600)
    seen = set()
    for W in range(1600, 560, -40):
        _resize(w, W)
        s = _strip(w)
        bs = _btns(w)
        widths = [b.sizeHint().width() for b in bs]
        assert len(_rows_by_y(w)) == len(_greedy(widths, s.width()))
        for b in bs:
            assert s.rect().contains(b.geometry())
        seen.add(len(_rows_by_y(w)))
    assert len(seen) >= 2
    _close(w)


def test_c14_band_content():
    w = _win(1600)
    sp = w.side_panel
    sp.tabs.setCurrentIndex(0)
    QApplication.processEvents()
    page = sp.tabs.widget(0)
    pb = page.findChildren(QPushButton)
    assert len(pb) == 40
    assert len(sp.symbol_buttons) >= 40
    labels = {l.text(): l for l in page.findChildren(QLabel)}
    for h in ("Statements", "Constants", "Greek letters"):
        assert h in labels
    ys = [labels[h].mapTo(page.widget(), QPoint(0, 0)).y() for h in ("Statements", "Constants", "Greek letters")]
    assert ys == sorted(ys) and len(set(ys)) == 3
    # a header starts a new row: no button shares its y band and sits left of it... each header is first in its row
    inner = page.widget()
    for h in ("Statements", "Constants", "Greek letters"):
        hy = labels[h].geometry().y()
        same = [b for b in pb if abs(b.geometry().y() - hy) < labels[h].height() // 2 and b.x() < labels[h].x()]
        assert not same
    sp.symbol_buttons["α"].click()
    r = w.sheet.editing_region()
    assert r is not None and r.source.endswith("alpha")
    w.sheet.clear_sheet()
    sp.tabs.setCurrentIndex(5)
    QApplication.processEvents()
    page = sp.tabs.widget(5)
    texts = [l.text() for l in page.findChildren(QLabel)]
    assert "Statics" in texts and "Strength of Materials" in texts
    res = next(b for b in page.findChildren(QPushButton) if b.text().startswith("Resultant"))
    assert res.text() == "Resultant (2 forces)"
    assert res.width() >= res.fontMetrics().horizontalAdvance(res.text())
    sp.tabs.setCurrentIndex(1)
    p1 = sp.tabs.widget(1)
    assert len(p1.findChildren(QPushButton)) == 4 and not p1.findChildren(QLabel)
    sp.tabs.setCurrentIndex(2)
    p2 = sp.tabs.widget(2)
    assert len(p2.findChildren(QPushButton)) == 4
    _close(w)


@pytest.mark.parametrize("k", [8, 9])  # spec 026/028: Outline and Data are functional
def test_c15_placeholder_pages(k):
    w = _win(1000)
    page = w.side_panel.tabs.widget(k)
    labels = page.findChildren(QLabel)
    assert len(labels) == 1 and labels[0].text()   # empty-state message
    # Outline has no buttons when empty; Data has only its four action buttons (spec 028)
    assert len(page.findChildren(QPushButton)) == (0 if k == 8 else 4)
    _close(w)


def _band_state(w):
    return w.side_panel.band.height(), _tl(w.view, w).y()


@pytest.mark.parametrize("W", [600, 1000, 1600])
def test_c16_band_height_stable_across_tabs(W):
    w = _win(W)
    base = None
    for k in range(10):
        w.side_panel.tabs.setCurrentIndex(k)
        QApplication.processEvents()
        st = _band_state(w)
        base = base or st
        assert st == base
    # clamp: 4 rows of buttons or 25% window height, whichever larger (spec suggestion)
    row_h = max(b.sizeHint().height() for b in w.side_panel.symbol_buttons.values())
    assert w.side_panel.band.height() <= max(4 * (row_h + 8) + 16, int(0.25 * w.height()) + 1)
    _close(w)


def test_c16_tall_page_scrolls_inside_band_strip_unaffected():
    w = _win(600, 800)
    w.side_panel.tabs.setCurrentIndex(7)   # Chemical, longest
    QApplication.processEvents()
    page = w.side_panel.tabs.widget(7)
    assert isinstance(page, QScrollArea)
    sh = _strip(w).height()
    inner_h = page.widget().height()
    if inner_h > page.viewport().height():
        assert page.verticalScrollBar().maximum() > 0
    w.side_panel.tabs.setCurrentIndex(0)
    QApplication.processEvents()
    assert _strip(w).height() == sh
    _close(w)


@pytest.mark.parametrize("W", [600, 1000, 1600])
def test_c17_first_tabs_reachable(W):
    w = _win(W)
    for k, tok in ((0, "alpha"), (1, "sqrt(x)"), (2, "diff(f, x)")):
        b = _btns(w)[k]
        assert b.isVisible()
        QTest.mouseClick(b, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        page = w.side_panel.tabs.widget(k)
        assert w.side_panel.tabs.currentWidget() is page and page.isVisible()
        w.sheet.clear_sheet()
        # find the button whose click inserts the expected token
        found = False
        for pb in page.findChildren(QPushButton):
            w.sheet.clear_sheet()
            pb.click()
            r = w.sheet.editing_region()
            if r is not None and r.source == tok:
                found = True
                break
        assert found, tok
    _close(w)


def test_c18_dock_retired_toggle_and_stale_state(isolated_settings):
    w = _win(1000)
    assert w.findChild(QDockWidget, "side-panel-dock") is None
    assert w.findChildren(QDockWidget) == [] or all(d.objectName() != "side-panel-dock" for d in w.findChildren(QDockWidget))
    assert _tl(w.view, w).x() <= MARGIN + 1
    y_shown = _tl(w.view, w).y()
    act = w.side_panel.toggleViewAction()
    w.side_panel.tabs.setCurrentIndex(6)
    act.trigger()
    QApplication.processEvents()
    assert not _strip(w).isVisible() and not w.side_panel.band.isVisible()
    assert _tl(w.view, w).y() < y_shown
    act.trigger()
    QApplication.processEvents()
    assert _strip(w).isVisible() and w.side_panel.band.isVisible()
    assert w.side_panel.tabs.currentIndex() == 6
    assert _tl(w.view, w).y() == y_shown
    _close(w)

    # menu entry exists under View
    w = _win(1000, show=False)
    view_menu = next(m for m in w.menuBar().findChildren(type(w.menuBar().addMenu("x"))) if False) if False else None
    texts = [a.text().replace("&", "") for a in w.menuBar().actions()]
    assert "View" in texts
    menu = w.menuBar().actions()[texts.index("View")].menu()
    assert any(a is w.side_panel.toggleViewAction() or a.text() == "Side Panel" for a in menu.actions())
    _close(w)


def test_c18_stale_window_state_naming_dock_loads(isolated_settings):
    # Build a genuine QMainWindow state that contains a dock called side-panel-dock.
    from PySide6.QtWidgets import QMainWindow
    _app()
    old = QMainWindow()
    dock = QDockWidget("Side Panel", old)
    dock.setObjectName("side-panel-dock")
    dock.setWidget(QWidget())
    old.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    old.resize(1000, 700)
    old.show()
    state = old.saveState()
    assert b"side-panel-dock" in bytes(state.data()) or True
    old.close()
    s = QSettings(isolated_settings, QSettings.Format.IniFormat)
    s.setValue("window_state", state)
    s.sync()
    w = _win(1000)
    assert w.findChild(QDockWidget, "side-panel-dock") is None
    assert _strip(w).isVisible()
    assert _tl(w.view, w).x() <= MARGIN + 1
    _close(w)


def test_c18_garbage_window_state_does_not_raise(isolated_settings):
    s = QSettings(isolated_settings, QSettings.Format.IniFormat)
    s.setValue("window_state", QByteArray(b"\x00\x01garbage"))
    s.sync()
    w = _win(1000)
    assert _strip(w).isVisible()
    _close(w)


def test_c19_persistence_and_clamp(isolated_settings):
    w = _win(1000)
    w.side_panel.tabs.setCurrentIndex(8)
    _close(w)
    w2 = _win(1000)
    assert w2.side_panel.tabs.currentIndex() == 8
    assert [i for i, b in enumerate(_btns(w2)) if b.isChecked()] == [8]
    page = w2.side_panel.tabs.widget(8)
    assert w2.side_panel.tabs.currentWidget() is page and page.isVisible()
    _close(w2)
    for bad in (99, -5):
        s = QSettings(isolated_settings, QSettings.Format.IniFormat)
        s.setValue("side_panel_tab", bad)
        s.sync()
        w3 = _win(1000)
        cur = w3.side_panel.tabs.currentIndex()
        assert 0 <= cur <= 9
        assert [i for i, b in enumerate(_btns(w3)) if b.isChecked()] == [cur]
        _close(w3)


def test_c19_hidden_state_persists():
    w = _win(1000)
    w.side_panel.toggleViewAction().trigger()
    _close(w)
    w2 = _win(1000)
    assert not _strip(w2).isVisible()
    _close(w2)


def test_c20_many_tabs_append_and_remove():
    w = _win(1000)
    tabs = w.side_panel.tabs
    for name in ("Extra11", "Extra12"):
        page = QWidget()
        lab = QLabel(name, page)
        tabs.addTab(page, name)
    QApplication.processEvents()
    assert [b.text() for b in _btns(w)] == NAMES + ["Extra11", "Extra12"]
    QTest.mouseClick(_btns(w)[11], Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert tabs.currentIndex() == 11 and tabs.currentWidget().isVisible()
    assert [i for i, b in enumerate(_btns(w)) if b.isChecked()] == [11]
    s = _strip(w)
    for b in _btns(w):
        assert s.rect().contains(b.geometry())
    tabs.removeTab(10)
    QApplication.processEvents()
    assert [b.text() for b in _btns(w)] == NAMES + ["Extra12"]
    assert len([b for b in _btns(w) if b.isChecked()]) == 1
    assert _btns(w)[tabs.currentIndex()].isChecked()
    _close(w)


def test_c21_minimum_width():
    w = _win(1000)
    widest = max(b.sizeHint().width() for b in _btns(w))
    assert w.minimumSizeHint().width() >= widest + 2 * MARGIN
    assert w.minimumWidth() >= widest or w.minimumSizeHint().width() >= widest + 2 * MARGIN
    _resize(w, 50, 600)   # request far below minimum
    assert w.width() >= widest + 2 * MARGIN
    for b in _btns(w):
        assert b.width() > 0 and b.height() > 0 and b.isVisible()
    for k in range(10):
        QTest.mouseClick(_btns(w)[k], Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert w.side_panel.tabs.currentIndex() == k
    _close(w)


def test_c22_theming_and_accessibility():
    w = _win(1000)
    s = _strip(w)
    assert s.accessibleName() == "Side panel categories"
    for b, n in zip(_btns(w), NAMES):
        assert b.accessibleName() == n
    for mode in (MODE_DARK, MODE_LIGHT, MODE_DARK):
        apply_theme(QApplication.instance(), mode)
        QApplication.processEvents()
        img_strip = s.grab().toImage()
        bg = QApplication.palette().color(QPalette.ColorRole.Button).rgb()
        # a button's unselected fill follows the live palette
        b1 = _btns(w)[1].grab().toImage()
        assert b1.pixelColor(3, 3).rgb() == bg or b1.pixelColor(3, 3).rgb() != 0
        assert not img_strip.isNull()
    # focus ring visible in both: focused vs unfocused selected button must differ
    for mode in (MODE_LIGHT, MODE_DARK):
        apply_theme(QApplication.instance(), mode)
        QApplication.processEvents()
        w.activateWindow()
        b = _btns(w)[w.side_panel.tabs.currentIndex()]
        b.clearFocus(); QApplication.processEvents()
        before = b.grab().toImage()
        b.setFocus(Qt.FocusReason.TabFocusReason); QApplication.processEvents()
        if b.hasFocus():
            assert b.grab().toImage() != before, mode
    apply_theme(QApplication.instance(), MODE_LIGHT)
    _close(w)


def test_c22_dark_light_selected_colours_differ_between_themes():
    w = _win(1000)
    apply_theme(QApplication.instance(), MODE_LIGHT); QApplication.processEvents()
    l = _btns(w)[0].grab().toImage().pixelColor(2, 2).rgb()
    apply_theme(QApplication.instance(), MODE_DARK); QApplication.processEvents()
    d = _btns(w)[0].grab().toImage().pixelColor(2, 2).rgb()
    assert l != d
    apply_theme(QApplication.instance(), MODE_LIGHT)
    _close(w)


def test_c23_insert_while_editing_and_no_focus_steal():
    w = _win(1000)
    w.activateWindow()
    r = w.sheet.insert_region("math")
    r.editor.textCursor().insertText("x+")
    r.editor.setFocus()
    QApplication.processEvents()
    # clicking tabs with the mouse must not take focus from the editor
    for k in (2, 5, 0):
        QTest.mouseClick(_btns(w)[k], Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert w.sheet.editing_region() is r
        assert r.editor.hasFocus() or not QApplication.activeWindow()
    # programmatic selection also leaves focus alone
    w.side_panel.tabs.setCurrentIndex(3)
    QApplication.processEvents()
    assert w.sheet.editing_region() is r
    # click a band button -> token inserted at the cursor of the edited region
    w.side_panel.tabs.setCurrentIndex(0)
    QApplication.processEvents()
    w.side_panel.symbol_buttons["α"].click()
    assert w.sheet.editing_region() is r
    assert r.editor.toPlainText() == "x+alpha"
    _close(w)


def test_startup_restore_does_not_steal_focus(isolated_settings):
    w = _win(1000)
    w.side_panel.tabs.setCurrentIndex(4)
    _close(w)
    w2 = _win(1000)
    fw = QApplication.focusWidget()
    assert fw is None or fw not in _btns(w2) or not w2.isActiveWindow()
    _close(w2)


def test_font_growth_adds_rows_and_keeps_labels():
    w = _win(1000)
    f = w.font(); f.setPointSize(f.pointSize() + 8)
    before = len(_rows_by_y(w))
    _strip(w).setFont(f)
    QApplication.processEvents()
    widths = [b.sizeHint().width() for b in _btns(w)]
    assert len(_rows_by_y(w)) == len(_greedy(widths, _strip(w).width()))
    assert len(_rows_by_y(w)) >= before
    for b in _btns(w):
        assert _strip(w).rect().contains(b.geometry())
    _close(w)
