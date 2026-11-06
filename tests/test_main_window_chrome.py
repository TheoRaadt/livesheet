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

def test_criterion1_standard_toolbar_present_math_toolbar_removed_spec011():
    """Spec 011 criterion 1: the Math toolbar is gone entirely; Standard is unaffected."""
    win = _make_window()
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    assert standard is not None
    assert standard.isVisible() and standard.isMovable()
    assert win.findChild(QToolBar, "math-toolbar") is None
    assert not hasattr(win, "math_toolbar")
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


def test_criterion3_standard_toolbar_toggle_still_present_and_independent_spec011():
    """Spec 011 criterion 1: Standard keeps its own 'Standard Toolbar' View entry, unaffected by
    the Math toolbar's removal; there is no 'Math Toolbar' entry anywhere in View."""
    win = _make_window()
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    standard_action = standard.toggleViewAction()
    assert standard_action.text() == "Standard Toolbar"
    view_menu = next(m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                      if m.title() == "&View")
    assert not any(a.text() == "Math Toolbar" for a in view_menu.actions())
    standard_action.trigger()
    assert not standard.isVisible()
    _close(win)


def test_criterion4_dragged_toolbar_position_persists_across_restart():
    win = _make_window()
    standard = win.findChild(QToolBar, "standard-toolbar")
    win.addToolBar(Qt.ToolBarArea.BottomToolBarArea, standard)   # simulate a user drag
    _close(win)   # closeEvent persists saveState() under "window_state"

    win2 = _make_window()
    standard2 = win2.findChild(QToolBar, "standard-toolbar")
    assert win2.toolBarArea(standard2) == Qt.ToolBarArea.BottomToolBarArea
    _close(win2)


def _bytes_from_a_toolbar_left_floating() -> "QByteArray":
    """Build a throwaway, production-independent window with the same single toolbar objectName
    as MainWindow's own (post spec-011) setup, and drive a real QTest press/move/release drag of
    its handle, which this environment's offscreen QPA platform reliably lands as a *floating*
    toolbar rather than a clean redock (confirmed independently: this is also the exact state
    found in a real on-disk LiveSheet preferences file left over from a tester's real-mouse drag
    session, see docs/board/log.md). Returns the resulting ``saveState()`` bytes: a "corrupted"
    layout a real drag can produce, used below to check that loading it back does not leave
    MainWindow in that broken state."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QAction
    from PySide6.QtTest import QTest

    probe = QMainWindow()
    standard = QToolBar("Standard", probe)
    standard.setObjectName("standard-toolbar")
    for label in ("New", "Open", "Save"):
        standard.addAction(QAction(label, probe))
    probe.addToolBar(standard)
    probe.resize(900, 600)
    probe.show()
    QApplication.processEvents()

    start_local = QPoint(5, 5)
    QTest.mousePress(standard, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start_local)
    QApplication.processEvents()
    start_global = standard.mapToGlobal(start_local)
    for step in range(1, 9):   # walk the press point upward, as a real drag would
        target_local = standard.mapFromGlobal(start_global - QPoint(0, step * 4))
        QTest.mouseMove(standard, target_local)
        QApplication.processEvents()
    QTest.mouseRelease(standard, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert standard.isFloating(), "fixture precondition: the probe drag must produce a floating toolbar"
    state = probe.saveState()
    probe.close()
    return state


def test_d1_a_toolbar_left_floating_by_a_drag_does_not_squash_on_restart(isolated_settings):
    """Regression for spec 007 review D1 (docs/board/reviews/007-main-window.md), simplified by
    spec 011's removal of the Math toolbar (only one toolbar left to validate): a live
    drag-reorder was found to be able to leave a toolbar *floating* instead of cleanly redocked
    (confirmed both via a real `QTest` drag here and, independently, in an actual on-disk
    LiveSheet preferences file left over from a tester's real-mouse session). A floating
    toolbar's saved bytes get replayed by `restoreState()` on every future launch regardless of
    the `setFloatable(False)` guard (that guard only stops a *new* detach; it does not
    retroactively validate old/corrupted saved bytes). MainWindow must detect this on load and
    repair it to the normal, non-floating layout."""
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
    assert not standard.isFloating()
    assert win2.toolBarArea(standard) == Qt.ToolBarArea.TopToolBarArea
    _close(win2)


def test_toolbars_are_movable_but_not_floatable():
    """`setFloatable(False)` is the actual fix for D1's root cause (a live in-area reorder could
    detach a toolbar into a floating window instead of redocking it); movability (needed for
    criterion 4's drag-to-relocate) must still hold."""
    win = _make_window()
    standard = win.findChild(QToolBar, "standard-toolbar")
    assert standard.isMovable()
    assert not standard.isFloatable()
    _close(win)


# ---------------------------------------------------------------------------
# Side panel (criteria 5-9)
# ---------------------------------------------------------------------------

def test_criterion5_side_panel_strip_tabs_and_no_dock_spec022():
    """Spec 022: the dock is retired; strip + band sit above the canvas, full width."""
    win = _make_window()
    win.show()
    QApplication.processEvents()
    assert win.findChild(QDockWidget, "side-panel-dock") is None
    assert win.side_panel.isVisible()
    assert win.side_panel.y() < win.view.y()
    tabs = win.side_panel.tabs
    assert tabs.objectName() == "side-panel-tabs"
    assert [tabs.tabText(i) for i in range(tabs.count())] == \
        ["Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical", "Electrical", "Chemical", "Outline", "Data"]
    side_panel_action = win.side_panel.toggleViewAction()
    assert side_panel_action.text() == "Side Panel"
    assert side_panel_action.isChecked()   # checked by default on first launch
    _close(win)


def test_criterion6_functional_tab_buttons_insert_the_expected_token():
    win = _make_window()
    sheet = win.sheet
    for label in ("π", "√", "d/dx", ":=", "α", "xₙ", "Ω"):
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
    for index, name in ((8, "Outline"), (9, "Data")):
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
    assert win.side_panel.isHidden()
    _close(win)

    win2 = _make_window()
    assert win2.side_panel.isHidden()
    assert not win2.side_panel.toggleViewAction().isChecked()
    _close(win2)


def test_criterion8_side_panel_tab_persists_across_restart():
    win = _make_window()
    win.resize(1000, 700)
    win.show()
    QApplication.processEvents()
    win.side_panel.tabs.setCurrentIndex(2)
    QApplication.processEvents()
    _close(win)

    win2 = _make_window()
    win2.resize(1000, 700)
    win2.show()
    QApplication.processEvents()
    assert win2.side_panel.tabs.currentIndex() == 2
    _close(win2)


def test_criterion9_canvas_minimum_width_kept_without_dock_caps_spec022():
    win = _make_window()
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
