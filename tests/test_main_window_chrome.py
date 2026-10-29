"""Developer tests for spec 007 (main window chrome: toolbars, status bar, side panel,
theming, empty-canvas hint), written from the spec's acceptance criteria 1-21 while
implementing it. Qt-dependent, like the rest of the GUI test suite; skip gracefully when
PySide6 cannot load.

Every test isolates ``QSettings`` to a private, per-test ini file (via the ``isolated_settings``
autouse fixture) so running this suite never reads or writes the real LiveSheet application's own
on-disk preferences (window layout, theme choice) -- those new persistence keys did not exist
before this spec.
"""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication, QDockWidget, QLabel, QMainWindow, QToolBar  # noqa: E402

from livesheet.document import RegionData, SheetDocument  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.sidepanel import MATH_TOKENS  # noqa: E402
from livesheet.gui.theme import MODE_DARK, MODE_LIGHT, MODE_SYSTEM, apply_theme  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Redirect every ``QSettings("LiveSheet", "LiveSheet")`` call made inside main_window.py to
    a private ini file for this test only."""
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


def _make_window() -> MainWindow:
    _ensure_app()
    win = MainWindow()
    win.sheet.set_modified(False)
    return win


def _close(win: MainWindow) -> None:
    win.sheet.set_modified(False)
    win.close()


# ---------------------------------------------------------------------------
# Toolbars & menu (criteria 1-4)
# ---------------------------------------------------------------------------

def test_criterion1_two_stacked_toolbars_on_first_launch():
    win = _make_window()
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    math_tb = win.findChild(QToolBar, "math-toolbar")
    assert standard is not None and math_tb is not None
    assert standard.isVisible() and math_tb.isVisible()
    assert standard.isMovable() and math_tb.isMovable()
    _close(win)


def test_criterion2_standard_toolbar_actions_are_the_same_objects_in_order():
    win = _make_window()
    tb = win.findChild(QToolBar, "standard-toolbar")
    actions = tb.actions()
    assert [a.isSeparator() for a in actions] == [False, False, False, True, False, True, False]
    non_separators = [a for a in actions if not a.isSeparator()]
    assert non_separators == [win.action_new, win.action_open, win.action_save,
                               win.action_export_pdf, win.action_recalculate]
    _close(win)


def test_criterion3_toolbar_view_toggles_are_independent():
    win = _make_window()
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    math_tb = win.findChild(QToolBar, "math-toolbar")
    standard_action = standard.toggleViewAction()
    math_action = math_tb.toggleViewAction()
    assert standard_action.text() == "Standard Toolbar"
    assert math_action.text() == "Math Toolbar"
    standard_action.trigger()
    assert not standard.isVisible()
    assert math_tb.isVisible()   # toggling one did not affect the other
    _close(win)


def test_criterion4_dragged_toolbar_position_persists_across_restart():
    win = _make_window()
    math_tb = win.findChild(QToolBar, "math-toolbar")
    win.addToolBar(Qt.ToolBarArea.BottomToolBarArea, math_tb)   # simulate a user drag
    _close(win)   # closeEvent persists saveState() under "window_state"

    win2 = _make_window()
    math_tb2 = win2.findChild(QToolBar, "math-toolbar")
    assert win2.toolBarArea(math_tb2) == Qt.ToolBarArea.BottomToolBarArea
    _close(win2)


def _bytes_from_a_toolbar_left_floating() -> "QByteArray":
    """Build a throwaway, production-independent 2-toolbar window (same objectNames, same
    addToolBar()/addToolBarBreak() shape as MainWindow's own setup) and drive a real QTest
    press/move/release drag of the second toolbar's own handle, which this environment's
    offscreen QPA platform reliably lands as a *floating* toolbar rather than a clean redock
    (confirmed independently: this is also the exact state found in a real on-disk LiveSheet
    preferences file left over from a tester's real-mouse drag session, see docs/board/log.md).
    Returns the resulting ``saveState()`` bytes: a "corrupted" layout a real drag can produce,
    used below to check that loading it back does not leave MainWindow in that broken state."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QAction
    from PySide6.QtTest import QTest

    probe = QMainWindow()
    standard = QToolBar("Standard", probe)
    standard.setObjectName("standard-toolbar")
    for label in ("New", "Open", "Save"):
        standard.addAction(QAction(label, probe))
    math_tb = QToolBar("Math", probe)
    math_tb.setObjectName("math-toolbar")
    for label in ("pi", "sqrt", "d/dx"):
        math_tb.addAction(QAction(label, probe))
    probe.addToolBar(standard)
    probe.addToolBarBreak()
    probe.addToolBar(math_tb)
    probe.resize(900, 600)
    probe.show()
    QApplication.processEvents()

    start_local = QPoint(5, 5)
    QTest.mousePress(math_tb, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start_local)
    QApplication.processEvents()
    start_global = math_tb.mapToGlobal(start_local)
    for step in range(1, 9):   # walk the press point upward, as a real drag would
        target_local = math_tb.mapFromGlobal(start_global - QPoint(0, step * 4))
        QTest.mouseMove(math_tb, target_local)
        QApplication.processEvents()
    QTest.mouseRelease(math_tb, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert math_tb.isFloating(), "fixture precondition: the probe drag must produce a floating toolbar"
    state = probe.saveState()
    probe.close()
    return state


def test_d1_a_toolbar_left_floating_by_a_drag_does_not_squash_on_restart(isolated_settings):
    """Regression for spec 007 review D1 (docs/board/reviews/007-main-window.md): a live
    drag-reorder of the Math toolbar was found to be able to leave it *floating* instead of
    cleanly redocked (confirmed both via a real `QTest` drag here and, independently, in an
    actual on-disk LiveSheet preferences file left over from a tester's real-mouse session). A
    floating toolbar's saved bytes get replayed by `restoreState()` on every future launch
    regardless of the `setFloatable(False)` guard (that guard only stops a *new* detach; it does
    not retroactively validate old/corrupted saved bytes), rendering it overlapping the docked
    toolbar area -- the squashed/clipped/overlapping symptom the tester reported. MainWindow
    must detect this on load and repair it to the normal stacked, non-floating layout."""
    corrupted_state = _bytes_from_a_toolbar_left_floating()

    # Write directly into the isolated ini file this test's own MainWindow instances read from
    # (not via a constructed+closed MainWindow -- closeEvent() would immediately overwrite
    # "window_state" with that window's own, uncorrupted saveState(), destroying the fixture).
    raw_settings = QSettings(isolated_settings, QSettings.Format.IniFormat)
    raw_settings.setValue("window_state", corrupted_state)
    raw_settings.sync()

    win2 = _make_window()
    win2.show()
    QApplication.processEvents()
    standard = win2.findChild(QToolBar, "standard-toolbar")
    math_tb = win2.findChild(QToolBar, "math-toolbar")
    assert not standard.isFloating() and not math_tb.isFloating()
    assert win2.toolBarArea(standard) == Qt.ToolBarArea.TopToolBarArea
    assert win2.toolBarArea(math_tb) == Qt.ToolBarArea.TopToolBarArea
    # Properly stacked: same x, same width, math directly below standard, no overlap.
    assert standard.geometry().width() == math_tb.geometry().width()
    assert standard.geometry().x() == math_tb.geometry().x()
    assert math_tb.geometry().top() >= standard.geometry().bottom()
    _close(win2)


def test_toolbars_are_movable_but_not_floatable():
    """`setFloatable(False)` is the actual fix for D1's root cause (a live in-area reorder could
    detach a toolbar into a floating window instead of redocking it); movability (needed for
    criterion 4's drag-to-relocate) must still hold."""
    win = _make_window()
    standard = win.findChild(QToolBar, "standard-toolbar")
    math_tb = win.findChild(QToolBar, "math-toolbar")
    assert standard.isMovable() and math_tb.isMovable()
    assert not standard.isFloatable() and not math_tb.isFloatable()
    _close(win)


# ---------------------------------------------------------------------------
# Side panel (criteria 5-9)
# ---------------------------------------------------------------------------

def test_criterion5_side_panel_dock_tabs_and_default_dock_side():
    win = _make_window()
    win.show()
    QApplication.processEvents()
    dock = win.findChild(QDockWidget, "side-panel-dock")
    assert dock is not None
    assert win.dockWidgetArea(dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    tabs = win.side_panel.tabs
    assert tabs.objectName() == "side-panel-tabs"
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Symbols", "Outline", "Data"]
    side_panel_action = dock.toggleViewAction()
    assert side_panel_action.text() == "Side Panel"
    assert side_panel_action.isChecked()   # checked by default on first launch
    _close(win)


def test_criterion6_symbols_tab_matches_math_toolbar_for_key_tokens():
    win = _make_window()
    sheet = win.sheet
    for label in ("π", "√", "d/dx", ":="):
        sheet.clear_sheet()
        expected_token = next(tok for _cat, lab, tok, _tip in MATH_TOKENS if lab == label)
        btn = win.side_panel.symbol_buttons[label]
        btn.click()
        region = sheet.editing_region()
        assert region is not None
        assert region.source == expected_token
    _close(win)


def test_criterion7_outline_and_data_tabs_are_placeholder_only():
    win = _make_window()
    tabs = win.side_panel.tabs
    for index, name in ((1, "Outline"), (2, "Data")):
        assert tabs.tabText(index) == name
        widget = tabs.widget(index)
        labels = widget.findChildren(QLabel)
        assert len(labels) == 1 and labels[0].text()
    # no outline/dataset state exists anywhere on the window or the sheet
    assert not any("outline" in n.lower() for n in dir(win) if not n.startswith("_"))
    assert not any("dataset" in n.lower() for n in dir(win.sheet) if not n.startswith("_"))
    _close(win)


def test_criterion8_side_panel_closed_state_persists_across_restart():
    win = _make_window()
    win.side_panel.toggleViewAction().trigger()   # close it
    assert not win.side_panel.isVisible()
    _close(win)

    win2 = _make_window()
    assert not win2.side_panel.isVisible()
    _close(win2)


def test_criterion8_side_panel_tab_and_width_persist_across_restart():
    win = _make_window()
    win.resize(1000, 700)
    win.show()
    QApplication.processEvents()
    win.side_panel.tabs.setCurrentIndex(2)
    win.resizeDocks([win.side_panel], [200], Qt.Orientation.Horizontal)
    QApplication.processEvents()
    width_before = win.side_panel.width()
    _close(win)

    win2 = _make_window()
    win2.resize(1000, 700)
    win2.show()
    QApplication.processEvents()
    assert win2.side_panel.tabs.currentIndex() == 2
    assert abs(win2.side_panel.width() - width_before) <= 10
    _close(win2)


def test_criterion9_dock_width_range_and_canvas_minimum():
    win = _make_window()
    assert win.side_panel.minimumWidth() == 120
    assert win.side_panel.maximumWidth() == 320
    assert win.view.minimumWidth() >= 400
    _close(win)


# ---------------------------------------------------------------------------
# Status bar (criteria 10-14)
# ---------------------------------------------------------------------------

def test_criterion10_status_bar_permanent_widget_order():
    win = _make_window()
    eval_label = win.findChild(QLabel, "status-eval-label")
    precision_label = win.findChild(QLabel, "status-precision-label")
    zoom_label = win.findChild(QLabel, "status-zoom-label")
    assert eval_label is not None and precision_label is not None and zoom_label is not None
    win.show()
    QApplication.processEvents()
    assert eval_label.x() < precision_label.x() < zoom_label.x()
    _close(win)


def test_criterion11_eval_label_ready_and_error_counts():
    win = _make_window()
    win._on_evaluation_finished(0, 3, 10.0)
    assert win._eval_label.text() == "Ready"
    win._on_evaluation_finished(1, 3, 10.0)
    assert win._eval_label.text() == "1 error"
    win._on_evaluation_finished(2, 3, 10.0)
    assert win._eval_label.text() == "2 errors"
    _close(win)


def test_criterion12_calculating_shown_only_when_pass_exceeds_300ms():
    win = _make_window()
    win._on_evaluation_finished(0, 1, 50.0)
    assert win._eval_label.text() == "Ready"   # under threshold: straight to final, no flicker

    win._on_evaluation_finished(0, 1, 450.0)
    assert win._eval_label.text() == "Calculating…"   # over threshold: shown first
    QApplication.processEvents()
    assert win._eval_label.text() == "Ready"   # then the final text
    _close(win)


def test_criterion12_real_slow_recalculate_pass_shows_calculating(monkeypatch):
    """An injected slow pass (the engine's own evaluate() made artificially slow) exercises the
    300 ms threshold end-to-end through the real Worksheet.recalculate() -> evaluationFinished
    signal, not just the label-update method in isolation."""
    win = _make_window()
    sheet = win.sheet
    sheet.add_region("math", QPointF(0, 0), "x := 1")
    real_evaluate = sheet.engine.evaluate

    def slow_evaluate(items):
        time.sleep(0.35)
        return real_evaluate(items)

    monkeypatch.setattr(sheet.engine, "evaluate", slow_evaluate)
    sheet.recalculate()
    assert win._eval_label.text() == "Calculating…"
    QApplication.processEvents()
    assert win._eval_label.text() == "Ready"
    _close(win)


def test_criterion13_precision_label_text_and_updates_via_dialog():
    win = _make_window()
    assert win._precision_label.text() == f"{win.sheet.significant} sig. figs"
    win.sheet.set_significant(9)
    win._refresh_precision_label()
    assert win._precision_label.text() == "9 sig. figs"
    _close(win)


def test_criterion13_clicking_precision_label_opens_the_same_dialog(monkeypatch):
    win = _make_window()
    calls = []

    def fake_get_int(*_args, **_kwargs):
        calls.append(True)
        return (11, True)

    monkeypatch.setattr("livesheet.gui.main_window.QInputDialog.getInt", fake_get_int)
    win._precision_label.clicked.emit()
    assert calls == [True]
    assert win.sheet.significant == 11
    assert win._precision_label.text() == "11 sig. figs"
    _close(win)


def test_criterion14_load_document_with_error_shows_one_error_immediately(tmp_path):
    win = _make_window()
    doc = SheetDocument(regions=[RegionData("math", 0, 0, "undefined_name_xyz =")], significant=6)
    path = tmp_path / "doc.lsheet"
    doc.save(path)
    win.open_path(path)
    assert win._eval_label.text() == "1 error"
    _close(win)


# ---------------------------------------------------------------------------
# Theming (criteria 15-18)
# ---------------------------------------------------------------------------

def test_criterion15_appearance_menu_three_exclusive_entries_default_system():
    win = _make_window()
    assert set(win._appearance_actions) == {MODE_SYSTEM, MODE_LIGHT, MODE_DARK}
    assert win._appearance_actions[MODE_SYSTEM].isChecked()
    assert not win._appearance_actions[MODE_LIGHT].isChecked()
    assert not win._appearance_actions[MODE_DARK].isChecked()
    group = win._appearance_actions[MODE_LIGHT].actionGroup()
    assert group is not None and group.isExclusive()
    _close(win)


def test_criterion16_selecting_light_or_dark_changes_app_palette_immediately():
    win = _make_window()
    app = QApplication.instance()
    win._set_appearance(MODE_DARK)
    dark_window = app.palette().color(QPalette.ColorRole.Window)
    win._set_appearance(MODE_LIGHT)
    light_window = app.palette().color(QPalette.ColorRole.Window)
    assert dark_window != light_window
    _close(win)


def test_criterion16_follow_system_rereads_scheme_at_selection_time(monkeypatch):
    win = _make_window()
    app = QApplication.instance()
    monkeypatch.setattr(mw_module, "apply_theme",
                         lambda a, m: apply_theme(a, m, scheme_reader=lambda _a: MODE_DARK))
    win._set_appearance(MODE_SYSTEM)
    dark_window = app.palette().color(QPalette.ColorRole.Window)

    monkeypatch.setattr(mw_module, "apply_theme",
                         lambda a, m: apply_theme(a, m, scheme_reader=lambda _a: MODE_LIGHT))
    win._set_appearance(MODE_SYSTEM)
    light_window = app.palette().color(QPalette.ColorRole.Window)
    assert dark_window != light_window
    _close(win)


def test_criterion17_appearance_persists_and_is_checked_as_default_next_launch():
    win = _make_window()
    win._set_appearance(MODE_DARK)
    assert win.settings.value("appearance") == MODE_DARK
    _close(win)

    win2 = _make_window()
    assert win2._appearance_actions[MODE_DARK].isChecked()
    _close(win2)


def test_criterion17_persisted_theme_applied_before_window_construction_no_flash():
    app = _ensure_app()
    settings = mw_module.QSettings()
    settings.setValue("appearance", MODE_DARK)
    apply_theme(app, settings.value("appearance", MODE_SYSTEM, type=str))   # what run() does
    before = app.palette().color(QPalette.ColorRole.Window)
    win = MainWindow()   # constructing the window must not reset the already-applied palette
    assert app.palette().color(QPalette.ColorRole.Window) == before
    _close(win)


def test_criterion18_canvas_painted_colors_unaffected_by_appearance():
    win = _make_window()
    sheet = win.sheet

    def crosshair_pixel() -> QColor:
        image = QImage(40, 40, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        sheet.crosshair.setPos(20, 20)
        sheet.render(painter, QRectF(0, 0, 40, 40), QRectF(0, 0, 40, 40))
        painter.end()
        return image.pixelColor(20, 13)   # a point on the crosshair's vertical arm

    win._set_appearance(MODE_LIGHT)
    light_pixel = crosshair_pixel()
    win._set_appearance(MODE_DARK)
    dark_pixel = crosshair_pixel()
    assert light_pixel.name() == dark_pixel.name() == "#d32f2f"
    _close(win)


# ---------------------------------------------------------------------------
# Empty-canvas hint (criteria 19-21)
# ---------------------------------------------------------------------------

def test_criterion19_hint_painted_only_on_a_zero_region_sheet(monkeypatch):
    win = _make_window()
    sheet = win.sheet
    calls = []
    monkeypatch.setattr(sheet, "_paint_empty_hint", lambda painter: calls.append(True))
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    sheet.drawBackground(painter, QRectF(0, 0, 10, 10))
    painter.end()
    assert calls == [True]
    _close(win)


def test_criterion19_hint_never_written_to_the_saved_document():
    win = _make_window()
    doc = win.sheet.to_document()
    assert doc.regions == []
    assert "Click to place the cursor" not in doc.to_json()
    _close(win)


def test_criterion20_hint_disappears_mid_edit_and_reappears_once_emptied():
    win = _make_window()
    sheet = win.sheet
    assert sheet.should_show_hint()
    region = sheet.insert_region("math")   # starts editing immediately, still empty
    assert region.editing
    assert not sheet.should_show_hint()
    region.finish_editing()                # empty region is discarded -> back to zero regions
    assert sheet.should_show_hint()
    _close(win)


def test_criterion21_export_pdf_excludes_hint_on_empty_sheet(tmp_path, monkeypatch):
    win = _make_window()
    calls = []
    monkeypatch.setattr(win.sheet, "_paint_empty_hint", lambda painter: calls.append(True))
    out = tmp_path / "out.pdf"
    export_pdf(win.sheet, str(out))
    assert calls == []
    assert out.exists()
    _close(win)
