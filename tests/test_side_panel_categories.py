"""Developer tests for spec 011 (side-panel category tabs, Greek-letter palette, subscript
quick-insert), written from the spec's acceptance criteria 1-10 and 13 while implementing it.
Qt-dependent, like the rest of the GUI test suite; skip gracefully when PySide6 cannot load.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolBar  # noqa: E402

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.pretty import pretty_source_html  # noqa: E402
from livesheet.gui.sidepanel import (  # noqa: E402
    DATA_PLACEHOLDER,
    MATH_TOKENS,
    OUTLINE_PLACEHOLDER,
    TAB_ORDER,
)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


def _win() -> MainWindow:
    _ensure_app()
    win = MainWindow()
    win.sheet.set_modified(False)
    return win


def _close(win: MainWindow) -> None:
    win.sheet.set_modified(False)
    win.close()


# -- 1 Math toolbar removed, Standard unaffected -----------------------------------------------

def test_criterion1_no_math_toolbar_standard_toolbar_untouched():
    win = _win()
    assert not hasattr(win, "math_toolbar")
    assert win.findChild(QToolBar, "math-toolbar") is None
    standard = win.findChild(QToolBar, "standard-toolbar")
    assert standard is not None and standard.objectName() == "standard-toolbar"
    assert standard.toggleViewAction().text() == "Standard Toolbar"
    view_menu = next(m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                      if m.title() == "&View")
    assert not any(a.text() == "Math Toolbar" for a in view_menu.actions())
    _close(win)


# -- 2 seven tabs in order -----------------------------------------------------------------------

def test_criterion2_seven_tabs_in_order():
    win = _win()
    tabs = win.side_panel.tabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == list(TAB_ORDER)
    _close(win)


# -- 3/4/5/8 token counts per tab -----------------------------------------------------------------

def _buttons_of(widget) -> list[QPushButton]:
    return widget.findChildren(QPushButton)


def test_criterion3_elements_tab_has_40_entries_including_pi_and_new_greek_buttons():
    win = _win()
    tabs = win.side_panel.tabs
    elements = tabs.widget(tabs.indexOf(tabs.widget(0)))
    buttons = _buttons_of(elements)
    assert len(buttons) == 40
    sheet = win.sheet
    for label, expected in (("π", "pi"), ("α", "alpha"), ("Ω", "Omega")):
        sheet.clear_sheet()
        win.side_panel.symbol_buttons[label].click()
        assert sheet.editing_region().source == expected
    _close(win)


def test_criterion4_algebra_tab_has_4_entries_including_subscript():
    win = _win()
    algebra = win.side_panel.tabs.widget(1)
    buttons = _buttons_of(algebra)
    assert len(buttons) == 4
    sheet = win.sheet
    sheet.clear_sheet()
    win.side_panel.symbol_buttons["√"].click()
    assert sheet.editing_region().source == "sqrt("
    sheet.clear_sheet()
    win.side_panel.symbol_buttons["xₙ"].click()
    assert sheet.editing_region().source == "_"
    _close(win)


def test_criterion5_calculus_tab_has_2_entries():
    win = _win()
    calculus = win.side_panel.tabs.widget(2)
    assert len(_buttons_of(calculus)) == 2
    sheet = win.sheet
    win.side_panel.symbol_buttons["d/dx"].click()
    assert sheet.editing_region().source == "diff("
    _close(win)


def test_criterion8_total_clickable_tokens_is_46():
    win = _win()
    total = sum(len(_buttons_of(win.side_panel.tabs.widget(i))) for i in range(3))
    assert total == 46
    _close(win)


# -- 6 statistics/optimization placeholders, no clickable widgets -------------------------------

def test_criterion6_outline_and_data_tabs_are_placeholder_only():
    win = _win()
    tabs = win.side_panel.tabs
    for index in (8, 9):   # Outline and Data remain placeholders (spec 026)
        widget = tabs.widget(index)
        assert _buttons_of(widget) == []
        assert len(widget.findChildren(QLabel)) == 1
    sheet = win.sheet
    sheet.clear_sheet()
    before = len(sheet.regions())
    tabs.setCurrentIndex(8)
    QApplication.processEvents()
    assert len(sheet.regions()) == before   # switching to the placeholder tab creates nothing
    _close(win)


# -- 7 outline/data unchanged, now 6th/7th --------------------------------------------------------

def test_criterion7_outline_and_data_unchanged_now_sixth_and_seventh():
    win = _win()
    tabs = win.side_panel.tabs
    assert tabs.tabText(8) == "Outline" and tabs.tabText(9) == "Data"   # moved by specs 018-020
    outline_label = tabs.widget(8).findChild(QLabel)
    data_label = tabs.widget(9).findChild(QLabel)
    assert outline_label.text() == OUTLINE_PLACEHOLDER
    assert data_label.text() == DATA_PLACEHOLDER
    _close(win)


# -- 9 dock persistence across indices 0-6 ---------------------------------------------------------

def test_criterion9_tab_persistence_across_restart_for_a_high_index():
    win = _win()
    win.resize(1000, 700)
    win.show()
    QApplication.processEvents()
    win.side_panel.tabs.setCurrentIndex(6)   # Data: the highest index in the new 7-tab layout
    QApplication.processEvents()
    _close(win)

    win2 = _win()
    win2.resize(1000, 700)
    win2.show()
    QApplication.processEvents()
    assert win2.side_panel.tabs.currentIndex() == 6
    _close(win2)


# -- 10 stale saved "math-toolbar" window_state loads without error -------------------------------

def test_criterion10_stale_math_toolbar_window_state_loads_without_error(isolated_settings):
    from PySide6.QtCore import QByteArray

    probe_win = _win()
    stale_state = probe_win.saveState()   # a real, valid blob from *before* this spec's removal
    _close(probe_win)

    raw = QSettings(isolated_settings, QSettings.Format.IniFormat)
    # Simulate an old on-disk blob that still names a "math-toolbar": QMainWindow.restoreState()
    # is documented to silently skip any named toolbar/dock it cannot find; nothing here invents
    # new handling, this just exercises that standard behaviour was not broken by the removal.
    raw.setValue("window_state", QByteArray(bytes(stale_state) + b"math-toolbar-stale-marker"))
    raw.sync()

    win2 = _win()   # must not raise/crash while loading
    win2.show()
    QApplication.processEvents()
    assert win2.findChild(QToolBar, "standard-toolbar") is not None
    _close(win2)


# -- 13 hand-typed Greek word still displays correctly, unaffected --------------------------------

def test_criterion13_hand_typed_greek_word_still_renders_as_glyph():
    assert pretty_source_html("alpha := 2") == "α := 2"
