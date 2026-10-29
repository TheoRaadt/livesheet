"""Independent black-box tests for spec 007 (main window chrome: toolbars, status bar, side
panel, theming, empty-canvas hint), written from docs/board/specs/007-main-window.md's own
acceptance criteria 1-21 and Edge cases -- not from reading main_window.py/worksheet.py/
sidepanel.py/theme.py as the source of truth. Written independently of the developer's own
tests/test_main_window_chrome.py (read only after drafting these, to check for gaps, per the
project's established tester practice -- see docs/board/reviews/006-plot-dialog.md).

Two developer-disclosed deviations (docs/board/decisions.md, "2026-10-29 (manager, spec 007
implementation)") are tested as accepted, not as defects:
1. Criterion 12's "Calculating..." is a post-pass flash (one event-loop tick after a >300ms pass),
   not literally live during the synchronous recalculate() call.
2. Criterion 16's "Follow System" real-OS-scheme branch is exercised via an injectable
   scheme_reader in tests; production always uses the real reader.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPalette  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDockWidget,
    QLabel,
    QPushButton,
    QStatusBar,
    QToolBar,
)

from livesheet.document import RegionData, SheetDocument  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.regions import COLOR_FRAME  # noqa: E402
from livesheet.gui.sidepanel import DATA_PLACEHOLDER, MATH_TOKENS, OUTLINE_PLACEHOLDER  # noqa: E402
from livesheet.gui.theme import (  # noqa: E402
    MODE_DARK,
    MODE_LIGHT,
    MODE_SYSTEM,
    apply_theme,
    dark_palette,
    detect_system_scheme,
    light_palette,
)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never touch the real on-disk LiveSheet preferences; every QSettings("LiveSheet",
    "LiveSheet") call inside main_window.py is redirected to a private ini file."""
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


# ---------------------------------------------------------------------------
# Toolbars & menu (criteria 1-4)
# ---------------------------------------------------------------------------

def test_criterion1_fresh_settings_have_no_window_state_key_yet_both_toolbars_show():
    win = _win()
    assert win.settings.value("window_state") is None   # genuinely first launch
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    math_tb = win.findChild(QToolBar, "math-toolbar")
    assert standard.isVisible() and math_tb.isVisible()
    assert standard.isMovable() and math_tb.isMovable()
    # "stacked... standard-toolbar above math-toolbar": on a fresh window, Standard's row is
    # above Math's row in the top toolbar area.
    assert standard.y() < math_tb.y()
    assert win.toolBarArea(standard) == Qt.ToolBarArea.TopToolBarArea
    assert win.toolBarArea(math_tb) == Qt.ToolBarArea.TopToolBarArea
    _close(win)


def test_criterion2_standard_toolbar_order_labels_and_identity_with_menu_actions():
    win = _win()
    tb = win.findChild(QToolBar, "standard-toolbar")
    actions = tb.actions()
    labels = [a.text().replace("&", "") for a in actions if not a.isSeparator()]
    assert labels == ["New", "Open…", "Save", "Export PDF…", "Recalculate"]
    assert [a.isSeparator() for a in actions] == [False, False, False, True, False, True, False]

    # Find the matching File/Calculate menu actions independently (by text, not by the window's
    # own action_* attributes) and confirm the toolbar button is the *same* QAction object.
    file_menu = next(m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                      if m.title() == "&File")
    new_action = next(a for a in file_menu.actions() if a.text() == "&New")
    assert tb.actions()[0] is new_action
    _close(win)


def test_criterion3_toggling_math_toolbar_leaves_standard_toolbar_untouched():
    win = _win()
    win.show()
    QApplication.processEvents()
    standard = win.findChild(QToolBar, "standard-toolbar")
    math_tb = win.findChild(QToolBar, "math-toolbar")
    math_tb.toggleViewAction().trigger()
    assert not math_tb.isVisible()
    assert standard.isVisible()   # opposite direction from the toggle tested elsewhere
    _close(win)


def test_criterion4_dragged_toolbar_to_left_edge_persists_across_restart():
    win = _win()
    standard = win.findChild(QToolBar, "standard-toolbar")
    win.addToolBar(Qt.ToolBarArea.LeftToolBarArea, standard)
    _close(win)

    win2 = _win()
    standard2 = win2.findChild(QToolBar, "standard-toolbar")
    assert win2.toolBarArea(standard2) == Qt.ToolBarArea.LeftToolBarArea
    _close(win2)


# ---------------------------------------------------------------------------
# Side panel (criteria 5-9)
# ---------------------------------------------------------------------------

def test_criterion5_side_panel_visible_by_default_docked_left_three_tabs_in_order():
    win = _win()
    win.show()
    QApplication.processEvents()
    dock = win.findChild(QDockWidget, "side-panel-dock")
    assert dock.isVisible()
    assert win.dockWidgetArea(dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    tabs = win.findChild(type(win.side_panel.tabs), "side-panel-tabs")
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Symbols", "Outline", "Data"]
    _close(win)


def test_criterion6_symbols_tab_tooltips_match_math_toolbar_tooltips():
    win = _win()
    math_tb = win.findChild(QToolBar, "math-toolbar")
    toolbar_tooltips = {a.text(): a.toolTip() for a in math_tb.actions() if not a.isSeparator()}
    for label in ("π", "√", "d/dx", ":="):
        panel_btn = win.side_panel.symbol_buttons[label]
        assert panel_btn.toolTip() == toolbar_tooltips[label]
    _close(win)


def test_criterion6_clicking_each_required_symbol_matches_the_toolbar_token():
    win = _win()
    sheet = win.sheet
    math_tb = win.findChild(QToolBar, "math-toolbar")
    tb_actions = {a.text(): a for a in math_tb.actions() if not a.isSeparator()}
    for label in ("π", "√", "d/dx", ":="):
        sheet.clear_sheet()
        tb_actions[label].trigger()
        tb_region = sheet.editing_region()
        toolbar_result = tb_region.source
        sheet.clear_sheet()
        win.side_panel.symbol_buttons[label].click()
        panel_region = sheet.editing_region()
        assert panel_region.source == toolbar_result
    _close(win)


def test_criterion7_outline_and_data_tabs_hold_exactly_one_distinct_label_each():
    win = _win()
    tabs = win.side_panel.tabs
    outline_widget = tabs.widget(1)
    data_widget = tabs.widget(2)
    assert [type(w) for w in outline_widget.findChildren(QPushButton)] == []
    assert [type(w) for w in data_widget.findChildren(QPushButton)] == []
    outline_labels = outline_widget.findChildren(QLabel)
    data_labels = data_widget.findChildren(QLabel)
    assert len(outline_labels) == 1 and len(data_labels) == 1
    assert outline_labels[0].text() == OUTLINE_PLACEHOLDER
    assert data_labels[0].text() == DATA_PLACEHOLDER
    assert outline_labels[0].text() != data_labels[0].text()
    # no outline/dataset content exists on the sheet or document after exercising the tabs
    doc = win.sheet.to_document()
    assert "outline" not in doc.to_json().lower()
    assert "dataset" not in doc.to_json().lower()
    _close(win)


def test_criterion8_reopening_after_a_closed_restart_restores_prior_tab_and_width():
    win = _win()
    win.resize(1000, 700)
    win.show()
    QApplication.processEvents()
    win.side_panel.tabs.setCurrentIndex(1)   # Outline, a non-default tab
    win.resizeDocks([win.side_panel], [250], Qt.Orientation.Horizontal)
    QApplication.processEvents()
    width_before = win.side_panel.width()
    win.side_panel.toggleViewAction().trigger()   # close it (simulates the dock close button)
    assert not win.side_panel.isVisible()
    _close(win)

    win2 = _win()
    win2.resize(1000, 700)
    win2.show()
    QApplication.processEvents()
    assert not win2.side_panel.isVisible()   # closed state itself restores closed
    win2.side_panel.toggleViewAction().trigger()   # user reopens it
    QApplication.processEvents()
    assert win2.side_panel.tabs.currentIndex() == 1
    assert abs(win2.side_panel.width() - width_before) <= 10
    _close(win2)


def test_criterion9_dock_width_is_clamped_to_120_320_and_canvas_keeps_400_at_window_minimum():
    win = _win()
    win.show()
    QApplication.processEvents()
    win.resizeDocks([win.side_panel], [5], Qt.Orientation.Horizontal)   # try far below minimum
    QApplication.processEvents()
    assert win.side_panel.width() >= 120
    win.resizeDocks([win.side_panel], [5000], Qt.Orientation.Horizontal)   # try far above maximum
    QApplication.processEvents()
    assert win.side_panel.width() <= 320

    win.resizeDocks([win.side_panel], [320], Qt.Orientation.Horizontal)
    win.resize(win.minimumSizeHint())
    QApplication.processEvents()
    assert win.view.width() >= 400
    _close(win)


# ---------------------------------------------------------------------------
# Status bar (criteria 10-14)
# ---------------------------------------------------------------------------

def test_criterion10_three_permanent_labels_are_children_of_the_status_bar_in_order():
    win = _win()
    bar = win.findChild(QStatusBar)
    eval_label = bar.findChild(QLabel, "status-eval-label")
    precision_label = bar.findChild(QLabel, "status-precision-label")
    zoom_label = bar.findChild(QLabel, "status-zoom-label")
    assert eval_label is not None and precision_label is not None and zoom_label is not None
    win.show()
    QApplication.processEvents()
    assert eval_label.x() < precision_label.x() < zoom_label.x()
    # the existing transient message area is unaffected: showMessage still works alongside them
    bar.showMessage("hello transient")
    assert bar.currentMessage() == "hello transient"
    assert eval_label.text()   # permanent widgets untouched by a transient message
    _close(win)


def test_criterion11_eval_label_reflects_real_recalculate_pass_through_region_text():
    win = _win()
    sheet = win.sheet
    eval_label = win.findChild(QLabel, "status-eval-label")
    sheet.add_region("math", QPointF(0, 0), "totally_undefined_name_zzz =")
    sheet.recalculate()
    QApplication.processEvents()
    assert eval_label.text() == "1 error"

    sheet.clear_sheet()
    sheet.add_region("math", QPointF(0, 0), "x := 2 =")
    sheet.recalculate()
    QApplication.processEvents()
    assert eval_label.text() == "Ready"
    _close(win)


def test_criterion11_error_count_matches_recalculates_own_transient_count():
    win = _win()
    sheet = win.sheet
    messages = []
    sheet.statusMessage.connect(messages.append)
    sheet.add_region("math", QPointF(0, 0), "bad_one_zzz =")
    sheet.add_region("math", QPointF(0, 40), "bad_two_zzz =")
    sheet.add_region("math", QPointF(0, 80), "y := 1 =")
    sheet.recalculate()
    QApplication.processEvents()
    assert "2 with errors" in messages[-1]
    eval_label = win.findChild(QLabel, "status-eval-label")
    assert eval_label.text() == "2 errors"
    _close(win)


def test_criterion12_label_text_sequence_under_and_over_threshold(monkeypatch):
    """Spies on the real QLabel.setText calls made by the eval label during an actual
    recalculate() pass, to check the exact sequence rather than only the end state."""
    import time as time_module

    win = _win()
    sheet = win.sheet
    eval_label = win.findChild(QLabel, "status-eval-label")
    calls: list[str] = []
    real_set_text = eval_label.setText

    def spy(text):
        calls.append(text)
        real_set_text(text)

    monkeypatch.setattr(eval_label, "setText", spy)

    sheet.add_region("math", QPointF(0, 0), "x := 1")
    sheet.recalculate()   # fast pass: must never call setText with "Calculating..."
    assert "Calculating…" not in calls
    assert calls[-1] == "Ready"

    calls.clear()
    real_evaluate = sheet.engine.evaluate

    def slow_evaluate(items):
        time_module.sleep(0.35)
        return real_evaluate(items)

    monkeypatch.setattr(sheet.engine, "evaluate", slow_evaluate)
    sheet.recalculate()   # slow pass: must flash "Calculating..." before the final text
    assert calls == ["Calculating…"]
    QApplication.processEvents()
    assert calls == ["Calculating…", "Ready"]
    _close(win)


def test_criterion13_precision_label_updates_and_menu_clicking_label_are_equivalent(monkeypatch):
    win = _win()
    precision_label = win.findChild(QLabel, "status-precision-label")
    assert precision_label.text() == f"{win.sheet.significant} sig. figs"

    calls = []

    def fake_get_int(*_args, **_kwargs):
        calls.append(1)
        return (10, True)

    monkeypatch.setattr("livesheet.gui.main_window.QInputDialog.getInt", fake_get_int)

    # Route 1: the Calculate menu entry.
    calc_menu = next(m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                      if m.title() == "&Calculate")
    precision_action = next(a for a in calc_menu.actions() if "Precision" in a.text())
    precision_action.trigger()
    assert win.sheet.significant == 10
    assert precision_label.text() == "10 sig. figs"
    assert calls == [1]

    # Route 2: clicking the label itself -- same effect, same underlying dialog call count style.
    def fake_get_int_2(*_args, **_kwargs):
        calls.append(2)
        return (13, True)

    monkeypatch.setattr("livesheet.gui.main_window.QInputDialog.getInt", fake_get_int_2)
    precision_label.clicked.emit()
    assert win.sheet.significant == 13
    assert precision_label.text() == "13 sig. figs"
    assert calls == [1, 2]
    _close(win)


def test_criterion14_opening_a_document_with_one_bad_region_shows_one_error_with_no_further_action(tmp_path):
    win = _win()
    doc = SheetDocument(
        regions=[
            RegionData("math", 0, 0, "x := 1 ="),
            RegionData("math", 0, 60, "unknown_symbol_here ="),
        ],
        significant=6,
    )
    path = tmp_path / "doc.lsheet"
    doc.save(path)
    win.open_path(path)
    eval_label = win.findChild(QLabel, "status-eval-label")
    assert eval_label.text() == "1 error"
    _close(win)


# ---------------------------------------------------------------------------
# Theming (criteria 15-18)
# ---------------------------------------------------------------------------

def test_criterion15_appearance_defaults_to_follow_system_and_entries_are_mutually_exclusive():
    win = _win()
    actions = win._appearance_actions
    assert {MODE_SYSTEM, MODE_LIGHT, MODE_DARK} == set(actions)
    assert actions[MODE_SYSTEM].isChecked()
    actions[MODE_LIGHT].trigger()
    assert actions[MODE_LIGHT].isChecked()
    assert not actions[MODE_SYSTEM].isChecked()
    actions[MODE_DARK].trigger()
    assert actions[MODE_DARK].isChecked()
    assert not actions[MODE_LIGHT].isChecked()
    _close(win)


def test_criterion16_selecting_light_and_dark_apply_exactly_the_documented_palettes():
    win = _win()
    app = QApplication.instance()
    win._set_appearance(MODE_DARK)
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.Base, QPalette.ColorRole.Highlight):
        assert app.palette().color(role) == dark_palette().color(role)
    win._set_appearance(MODE_LIGHT)
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.Base, QPalette.ColorRole.Highlight):
        assert app.palette().color(role) == light_palette().color(role)
    _close(win)


def test_criterion16_follow_system_rereads_at_selection_time_not_at_startup(monkeypatch):
    win = _win()
    app = QApplication.instance()
    win._set_appearance(MODE_LIGHT)   # start from a known, different state

    monkeypatch.setattr(mw_module, "apply_theme",
                         lambda a, m: apply_theme(a, m, scheme_reader=lambda _a: MODE_DARK))
    win._set_appearance(MODE_SYSTEM)
    assert app.palette().color(QPalette.ColorRole.Window) == dark_palette().color(QPalette.ColorRole.Window)
    _close(win)


def test_criterion16_real_detect_system_scheme_runs_without_error_under_offscreen():
    _ensure_app()
    result = detect_system_scheme()
    assert result in (MODE_LIGHT, MODE_DARK)


def test_criterion17_appearance_choice_is_written_to_disk_and_reread_next_launch(isolated_settings):
    win = _win()
    win._set_appearance(MODE_DARK)
    _close(win)
    # Read back with a brand new QSettings pointed at the same ini file, independent of win.settings
    disk_settings = QSettings(isolated_settings, QSettings.Format.IniFormat)
    assert disk_settings.value("appearance") == MODE_DARK

    win2 = _win()
    assert win2._appearance_actions[MODE_DARK].isChecked()
    _close(win2)


def test_criterion17_theme_is_applied_before_the_window_is_constructed():
    app = _ensure_app()
    settings = mw_module.QSettings()
    settings.setValue("appearance", MODE_DARK)
    apply_theme(app, settings.value("appearance", MODE_SYSTEM, type=str))
    before = app.palette().color(QPalette.ColorRole.Window)
    win = MainWindow()   # must not reset the already-applied palette during construction
    assert app.palette().color(QPalette.ColorRole.Window) == before
    assert before == dark_palette().color(QPalette.ColorRole.Window)
    _close(win)


def test_criterion18_canvas_painted_colours_stay_fixed_across_appearance_changes():
    win = _win()
    sheet = win.sheet
    sheet.add_region("math", QPointF(40, 40), "x := 1")

    def render_at(printing: bool) -> QImage:
        image = QImage(100, 100, QImage.Format.Format_RGB32)
        image.fill(QColor("magenta"))   # a colour that appears nowhere in the real palette
        painter = QPainter(image)
        sheet.printing = printing
        sheet.render(painter, QRectF(0, 0, 100, 100), QRectF(0, 0, 100, 100))
        sheet.printing = False
        painter.end()
        return image

    win._set_appearance(MODE_LIGHT)
    light_image = render_at(False)
    win._set_appearance(MODE_DARK)
    dark_image = render_at(False)
    for x in range(0, 100, 5):
        for y in range(0, 100, 5):
            assert light_image.pixelColor(x, y) == dark_image.pixelColor(x, y), (x, y)
    # explicit literal checks against the engine's own known fixed colours
    assert light_image.pixelColor(90, 90).name() == "#ffffff"   # plain canvas background
    _close(win)


# ---------------------------------------------------------------------------
# Empty-canvas hint (criteria 19-21)
# ---------------------------------------------------------------------------

def _render_background(sheet, printing: bool = False) -> QImage:
    """Render just drawBackground's own output (grid/page-edge/hint), not the region items
    themselves -- isolates the hint's own pixels from everything else drawBackground paints,
    since the grid dots and page edge are drawn identically regardless of region count."""
    image = QImage(400, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    sheet.printing = printing
    sheet.drawBackground(painter, QRectF(0, 0, 400, 100))
    sheet.printing = False
    painter.end()
    return image


def test_criterion19_hint_is_visibly_painted_on_a_blank_sheet_and_never_saved():
    win = _win()
    sheet = win.sheet
    assert len(sheet.regions()) == 0
    empty_render = _render_background(sheet)
    sheet.add_region("math", QPointF(0, 0), "x := 1")   # same grid/page-edge, hint now gone
    occupied_render = _render_background(sheet)
    assert empty_render.convertToFormat(QImage.Format.Format_RGB32) != \
        occupied_render.convertToFormat(QImage.Format.Format_RGB32)   # the hint is real pixels

    sheet.clear_sheet()
    doc = sheet.to_document()
    assert doc.regions == []
    assert "click" not in doc.to_json().lower()
    _close(win)


def test_criterion20_hint_gone_mid_edit_and_back_after_select_all_delete_via_menu_actions():
    win = _win()
    sheet = win.sheet

    baseline = _render_background(sheet)   # zero regions: hint shown
    region = sheet.insert_region("math")   # mid-edit, still empty
    assert region.editing and region.is_empty()
    assert _render_background(sheet) != baseline   # hint gone the instant the region exists
    region.editor.textCursor().insertText("5")
    region.finish_editing()
    assert _render_background(sheet) != baseline   # still gone once committed

    win.select_all()          # the menu-level helper, not a direct sheet call
    win.delete_selected()
    QApplication.processEvents()
    assert len(sheet.regions()) == 0
    assert _render_background(sheet) == baseline   # emptied back to zero -> hint reappears, same pixels
    _close(win)


def test_criterion21_export_never_paints_the_hint_even_though_the_live_canvas_does():
    win = _win()
    sheet = win.sheet
    assert len(sheet.regions()) == 0

    live = _render_background(sheet, printing=False)
    exported = _render_background(sheet, printing=True)
    assert live != exported   # the live canvas painted something (the hint) that export did not
    all_white = QImage(400, 100, QImage.Format.Format_RGB32)
    all_white.fill(QColor("#ffffff"))
    assert exported == all_white   # export path: entirely blank, hint fully suppressed
    _close(win)


def test_criterion21_actual_export_pdf_is_identical_whether_side_panel_is_open_or_closed(tmp_path):
    """export_pdf renders only the Worksheet scene, never window chrome (toolbars/side
    panel/status bar); an empty sheet's exported PDF should be byte-identical regardless of
    whether the (chrome-only) side panel happens to be open, modulo Qt's own per-export
    /DocumentID metadata."""
    win = _win()
    win.show()
    QApplication.processEvents()
    assert win.side_panel.isVisible()
    out_open = tmp_path / "open.pdf"
    export_pdf(win.sheet, str(out_open))

    win.side_panel.toggleViewAction().trigger()
    assert not win.side_panel.isVisible()
    out_closed = tmp_path / "closed.pdf"
    export_pdf(win.sheet, str(out_closed))

    data_open = out_open.read_bytes()
    data_closed = out_closed.read_bytes()
    assert len(data_open) == len(data_closed)
    diff_positions = [i for i in range(len(data_open)) if data_open[i] != data_closed[i]]
    # Confirmed by manual byte-diff inspection: every differing byte falls inside Qt's own
    # randomly-generated per-export /DocumentID UUID, which the PDF metadata embeds three times
    # (once plain, twice hex-encoded in the /ID array) -- around 110-120 bytes total, nothing to
    # do with scene content. A generous bound catches a real regression while tolerating this.
    assert len(diff_positions) < 200
    _close(win)
