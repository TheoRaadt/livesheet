"""Independent black-box tests for spec 008 (dialog-based vector/matrix insertion), written
from docs/board/specs/008-matrix-dialog.md's own acceptance criteria 1-25 and Edge cases --
not from reading livesheet/gui/matrixdialog.py/worksheet.py/main_window.py as the source of
truth beyond the small public names the spec itself names (``MatrixDialog``, ``MatrixFields``,
``compile_matrix_fields``, ``decompose_matrix_text``, ``validate_matrix_fields``).

Written independently of tests/test_matrix_dialog.py (the developer's own 60 tests); that file
was read afterwards only to check for coverage gaps, not consulted while drafting these cases.
A few deliberately different exercise paths vs. the developer's own tests:
  - Criteria 1/3/6 are additionally driven through the *real* ``Worksheet.contextMenuEvent``,
    including its real, unpatched, modal ``QMenu.exec()`` call -- not a direct call to
    ``insert_matrix_at``/``_open_matrix_dialog`` and not a patched ``QMenu.exec``. ``QMenu.exec``
    is a Shiboken/C++-backed method: ``mock.patch.object(QMenu, "exec", ...)`` silently fails to
    intercept calls made through a live ``QMenu`` instance (verified independently: the patched
    attribute is visible on the class, but ``menu.exec(...)`` still runs the real, blocking modal
    loop) -- unlike patching ``exec`` on a pure-Python ``QDialog`` subclass such as
    ``MatrixDialog`` (used throughout this file and the rest of the test suite), which is a normal
    Python MRO override and works as expected. Instead, a ``QTimer.singleShot(0, ...)`` scheduled
    before the real ``menu.exec()`` call fires once its nested event loop starts; the callback
    finds the live popup via ``QApplication.activePopupWidget()``, selects the action matching the
    visible text with ``QMenu.setActiveAction`` and activates it with a real
    ``QTest.keyClick(..., Qt.Key.Key_Enter)`` (or dismisses with ``Key_Escape`` when no action
    should be chosen) -- so ``menu.exec()`` itself runs for real and returns the actually-selected
    ``QAction``, exercising the real menu-construction/dispatch code in ``contextMenuEvent``.
  - The ``&Matrix…``/``Ctrl+Shift+M`` ``Insert`` menu entry (``main_window.py``) is exercised
    directly through a real ``MainWindow``/``QAction``, which the developer's own tests never did.
  - Criterion 17's accepted judgement call (docs/board/decisions.md, "2026-10-29 (manager, spec
    008 implementation)": commit via the region's own ``start_editing()``/``finish_editing()``
    cycle rather than a direct ``RegionData.text``/``region.source`` set) is checked at the level
    the decision itself cares about: that the on-screen *pretty* HTML the user actually sees
    refreshes immediately to match the new text, not just that ``region.source`` changed.

Qt-dependent tests skip gracefully when PySide6 cannot load, as the existing GUI tests do.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMenu  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.matrixdialog import (  # noqa: E402
    MatrixDialog,
    MatrixFields,
    cell_has_separator,
    compile_matrix_fields,
    decompose_matrix_text,
    validate_matrix_fields,
)
from livesheet.gui.pretty import display_source, pretty_source_html  # noqa: E402
from livesheet.gui.regions import MathRegion  # noqa: E402
from livesheet.gui.worksheet import Worksheet  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _ensure_app()
    return Worksheet()


def _fill(dlg: MatrixDialog, *rows: tuple[str, ...]) -> None:
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            dlg._cell_edits[r][c].setText(text)


class _FakeContextEvent:
    """A stand-in for a QGraphicsSceneContextMenuEvent: only the three members
    ``Worksheet.contextMenuEvent`` actually reads."""

    def __init__(self, pos: QPointF):
        self._pos = pos

    def accept(self) -> None:
        pass

    def scenePos(self) -> QPointF:
        return self._pos

    def screenPos(self) -> QPoint:
        return QPoint(0, 0)


def _schedule_pick_real_menu_action(label: str) -> None:
    """Schedule a callback that fires once the real, about-to-be-opened ``QMenu.exec()`` call in
    ``Worksheet.contextMenuEvent`` starts its own nested event loop: finds the live popup via
    ``QApplication.activePopupWidget()``, and activates the action with the given visible text
    via a real key event so the real (unpatched) ``QMenu.exec()`` call returns that ``QAction``.
    If no action with that text exists, dismisses the menu with Escape (``exec()`` returns
    ``None``), matching what a user would experience for a menu entry that isn't offered."""

    def pick() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu), f"expected an open QMenu popup, got {menu!r}"
        action = next((a for a in menu.actions() if a.text() == label), None)
        if action is None:
            QTest.keyClick(menu, Qt.Key.Key_Escape)
            return
        menu.setActiveAction(action)
        QTest.keyClick(menu, Qt.Key.Key_Enter)

    QTimer.singleShot(0, pick)


def _schedule_record_menu_labels_and_dismiss(seen: dict) -> None:
    """Schedule a callback that records the open real popup menu's own visible action labels
    (into ``seen["labels"]``) and then dismisses it with Escape, so the real ``QMenu.exec()``
    call returns ``None`` without selecting anything."""

    def spy() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu), f"expected an open QMenu popup, got {menu!r}"
        seen["labels"] = [a.text() for a in menu.actions()]
        QTest.keyClick(menu, Qt.Key.Key_Escape)

    QTimer.singleShot(0, spy)


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """MainWindow tests here must never touch the real on-disk LiveSheet preferences."""
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


# ===========================================================================
# Trigger and pre-fill (criteria 1-7)
# ===========================================================================

def test_matrix_here_via_real_context_menu_opens_size_step_criterion_1():
    """Right-clicking blank canvas and choosing the real "Matrix here" QAction (not calling
    insert_matrix_at directly) opens the Size step at Rows=2/Columns=2; Cancel creates nothing."""
    sheet = _sheet()
    opened = []

    def fake_dialog_exec(self):
        opened.append(self)
        self.reject()

    _schedule_pick_real_menu_action("Matrix here")
    with mock.patch.object(MatrixDialog, "exec", fake_dialog_exec):
        sheet.contextMenuEvent(_FakeContextEvent(QPointF(80, 80)))

    assert len(opened) == 1
    dlg = opened[0]
    assert dlg.rows_spin.value() == 2
    assert dlg.cols_spin.value() == 2
    assert dlg._stack.currentIndex() == 0
    assert sheet.regions() == []


def test_insert_matrix_menu_action_in_main_window_has_shortcut_and_wires_to_dialog():
    """The &Insert menu's "&Matrix…" entry (Ctrl+Shift+M) actually triggers the dialog at the
    crosshair's own position when the real QAction is triggered through Qt's own signal, not by
    calling a private helper method directly."""
    win = MainWindow()
    insert_menu = next(
        a.menu() for a in win.menuBar().actions() if a.menu() is not None and a.menu().title() == "&Insert")
    matrix_action = next(a for a in insert_menu.actions() if a.text() == "&Matrix…")
    assert matrix_action.shortcut().toString() == "Ctrl+Shift+M"

    opened = []

    def fake_exec(self):
        opened.append(self)
        self.reject()

    win.sheet.crosshair.setPos(30, 40)
    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        matrix_action.trigger()

    assert len(opened) == 1
    win.sheet.set_modified(False)
    win.close()


def test_grid_step_prefill_blank_cells_name_show_scale_criterion_2():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(3)
    dlg.cols_spin.setValue(1)
    dlg._on_next_clicked()

    assert dlg._stack.currentIndex() == 1
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [[""], [""], [""]]
    assert dlg.name_mode_combo.currentText() == "No name (insert as a value)"
    assert dlg.show_mode_combo.currentText() == "Don't show a result"
    assert dlg.scale_edit.text() == ""


def test_edit_as_grid_via_real_context_menu_prefills_plain_definition_criterion_3():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    opened = []

    def fake_dialog_exec(self):
        opened.append(self)

    _schedule_pick_real_menu_action("Edit as grid...")
    with mock.patch.object(MatrixDialog, "exec", fake_dialog_exec):
        sheet.contextMenuEvent(_FakeContextEvent(QPointF(0, 0)))

    assert len(opened) == 1
    dlg = opened[0]
    assert dlg._stack.currentIndex() == 1
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2"], ["3", "4"]]
    assert dlg.name_mode_combo.currentIndex() == 1
    assert dlg.name_edit.text() == "A"
    assert dlg.assign_combo.currentIndex() == 0
    assert dlg.scale_edit.text() == ""
    assert dlg.show_mode_combo.currentIndex() == 0


def test_edit_as_grid_prefill_trailing_numeric_show_criterion_4():
    fields = decompose_matrix_text("A := [1, 2; 3, 4] =")
    assert fields is not None
    assert fields.cells == [["1", "2"], ["3", "4"]]
    assert fields.name == "A"
    assert fields.assign_op == ":="
    assert fields.show_mode == "numeric"
    assert fields.display_unit == ""


def test_edit_as_grid_prefill_stiffness_example_criterion_5():
    fields = decompose_matrix_text("K := [2, -1; -1, 2]*N/m")
    assert fields is not None
    assert fields.name == "K"
    assert fields.cells == [["2", "-1"], ["-1", "2"]]
    assert fields.scale == "N/m"
    assert fields.show_mode == "none"


def test_two_terms_not_representable_no_edit_as_grid_real_context_menu_criterion_6():
    """A size-mismatch two-term region never shows "Edit as grid..." via the real context menu,
    and double-click keeps starting ordinary inline editing."""
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A + [1, 2, 3; 4, 5, 6]")
    seen_menu: dict = {}

    _schedule_record_menu_labels_and_dismiss(seen_menu)
    sheet.contextMenuEvent(_FakeContextEvent(QPointF(0, 0)))

    assert "Edit as grid..." not in seen_menu["labels"]
    assert not region.editing
    from PySide6.QtCore import QPointF as _QPointF

    class _DblClick:
        def scenePos(self) -> _QPointF:
            return _QPointF(0, 0)

    region.mouseDoubleClickEvent(_DblClick())
    assert region.editing


def test_edit_as_grid_prefill_symbolic_cells_criterion_7():
    fields = decompose_matrix_text("M := [a, b; c, d]")
    assert fields is not None
    assert fields.cells == [["a", "b"], ["c", "d"]]


# ===========================================================================
# Fields and compile mapping (criteria 8-13)
# ===========================================================================

def test_compile_mapping_basic_two_by_two_criterion_8():
    fields = MatrixFields(rows=2, cols=2, cells=[["1", "2"], ["3", "4"]])
    assert compile_matrix_fields(fields) == "[1, 2; 3, 4]"


def test_compile_mapping_define_and_numeric_show_criterion_9():
    fields = MatrixFields(
        rows=2, cols=2, cells=[["1", "2"], ["3", "4"]],
        name_mode="define", name="A", assign_op=":=",
        show_mode="numeric", display_unit="",
    )
    assert compile_matrix_fields(fields) == "A := [1, 2; 3, 4] ="


def test_compile_mapping_scale_and_define_matches_002a_byte_for_byte_criterion_10():
    fields = MatrixFields(
        rows=2, cols=2, cells=[["2", "-1"], ["-1", "2"]],
        name_mode="define", name="K", assign_op=":=",
        scale="N/m",
    )
    assert compile_matrix_fields(fields) == "K := [2, -1; -1, 2]*N/m"


def test_add_column_remove_row_reshape_tracks_current_grid_criterion_11():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()
    _fill(dlg, ("1", "2"), ("3", "4"))

    dlg._add_column()
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2", ""], ["3", "4", ""]]
    dlg._cell_edits[0][2].setText("9")
    dlg._cell_edits[1][2].setText("8")
    assert compile_matrix_fields(dlg._collect_fields()) == "[1, 2, 9; 3, 4, 8]"

    dlg._remove_row()
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2", "9"]]
    assert compile_matrix_fields(dlg._collect_fields()) == "[1, 2, 9]"


def test_row_vector_and_column_vector_criterion_12():
    assert compile_matrix_fields(MatrixFields(rows=1, cols=3, cells=[["5", "6", "7"]])) == "[5, 6, 7]"
    assert compile_matrix_fields(
        MatrixFields(rows=3, cols=1, cells=[["5"], ["6"], ["7"]])) == "[5; 6; 7]"


def test_one_by_one_literal_criterion_13():
    assert compile_matrix_fields(MatrixFields(rows=1, cols=1, cells=[["5"]])) == "[5]"


def test_fraction_and_expression_cells_compile_as_typed_edge_case():
    """Spec's own allowed cell shapes: a fraction and a short expression, exactly as typed."""
    fields = MatrixFields(rows=1, cols=2, cells=[["1/3", "sin(0.5)"]])
    assert compile_matrix_fields(fields) == "[1/3, sin(0.5)]"


# ===========================================================================
# OK / Cancel, new insertion (criteria 14-15)
# ===========================================================================

def test_cancel_at_either_step_creates_nothing_criterion_14():
    for step in ("size", "grid"):
        sheet = _sheet()

        def fake_exec(self, _step=step):
            if _step == "grid":
                self._on_next_clicked()
                self._cell_edits[0][0].setText("1")
            self.reject()

        with mock.patch.object(MatrixDialog, "exec", fake_exec):
            result = sheet.insert_matrix_at(QPointF(10, 10))
        assert result is None
        assert sheet.regions() == []


def test_ok_same_net_effect_as_typing_directly_criterion_15():
    sheet_a = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("3", "1"), ("2", "4"))
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("B")
        self.show_mode_combo.setCurrentIndex(2)   # symbolic ->
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region_a = sheet_a.insert_matrix_at(QPointF(0, 0))
    region_a.finish_editing()
    sheet_a.recalculate()

    sheet_b = _sheet()
    region_b = sheet_b.insert_region("math", initial_text="B := [3, 1; 2, 4] →")
    region_b.finish_editing()
    sheet_b.recalculate()

    assert region_a.source == region_b.source == "B := [3, 1; 2, 4] →"
    assert region_a.result.status == region_b.result.status == "ok"
    assert region_a.result.output == region_b.result.output


# ===========================================================================
# OK / Cancel, existing region (criteria 16-17) + the accepted judgement call
# ===========================================================================

def test_cancel_on_existing_region_leaves_source_and_display_untouched_criterion_16():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    sheet.recalculate()
    before_html = region.editor.toHtml()

    dlg = MatrixDialog(sheet, region=region)
    dlg._cell_edits[1][1].setText("40")
    dlg.reject()

    assert region.source == "A := [1, 2; 3, 4]"
    assert not region.editing
    assert region.editor.toHtml() == before_html
    assert region in sheet.regions()


def test_ok_on_existing_region_updates_source_result_and_on_screen_pretty_display_criterion_17():
    """Criterion 17 plus the accepted judgement call: OK must not only change region.source, it
    must refresh the actual on-screen (non-editing) pretty HTML immediately -- the same HTML a
    direct text edit's own finish_editing() would have produced -- not leave stale text showing
    until some later, unrelated redraw."""
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4] =")
    sheet.recalculate()

    dlg = MatrixDialog(sheet, region=region)
    dlg._cell_edits[1][1].setText("40")
    dlg.accept()

    assert region.source == "A := [1, 2; 3, 40] ="
    assert not region.editing
    assert region.result is not None and region.result.status == "ok"
    assert region.result.output == "= [1, 2; 3, 40]"

    expected_html = pretty_source_html(display_source(region.source)) or "&nbsp;"
    assert expected_html in region.editor.toHtml()
    # the stale "4" (not "40") must not still be the last digit shown in the editor's plain text
    assert region.editor.toPlainText() != "A := [1, 2; 3, 4] ="
    assert "40" in region.editor.toPlainText() or "40" in region.editor.toHtml()


def test_ok_on_existing_region_matches_a_direct_edit_byte_for_byte():
    """Cross-check the judgement call against the alternative it replaced: the resulting
    on-screen HTML after dialog-driven OK must be identical to what directly typing the same new
    text and committing would have produced on an otherwise-identical region."""
    sheet_dialog = _sheet()
    region = sheet_dialog.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4] =")
    sheet_dialog.recalculate()
    dlg = MatrixDialog(sheet_dialog, region=region)
    dlg._cell_edits[1][1].setText("40")
    dlg.accept()

    sheet_direct = _sheet()
    region2 = sheet_direct.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 40] =")
    sheet_direct.recalculate()

    assert region.editor.toHtml() == region2.editor.toHtml()


# ===========================================================================
# Errors (criteria 18-21)
# ===========================================================================

def test_blank_cell_error_message_and_location_criterion_18():
    err = validate_matrix_fields(MatrixFields(rows=2, cols=2, cells=[["1", ""], ["3", "4"]]))
    assert err is not None
    assert err.message == "Every cell must have a value"
    assert err.location == (0, 1)


def test_cell_top_level_separator_error_message_criterion_19():
    assert cell_has_separator("1, 2") is True
    assert cell_has_separator("1; 2") is True
    assert cell_has_separator("f(a, b)") is False   # comma inside parens is fine
    err = validate_matrix_fields(MatrixFields(rows=1, cols=2, cells=[["1, 2", "3"]]))
    assert err is not None
    assert err.message == "A cell cannot contain ',' or ';'; use Add column/Add row instead"
    assert err.location == (0, 0)


def test_blank_name_with_define_as_error_message_criterion_20():
    err = validate_matrix_fields(MatrixFields(
        rows=1, cols=1, cells=[["1"]], name_mode="define", name="   "))
    assert err is not None
    assert err.message == "Name is required"
    assert err.location == "name"


def test_undefined_symbol_surfaces_on_committed_region_same_as_direct_edit_criterion_21():
    sheet_dialog = _sheet()

    def fake_exec(self):
        self.rows_spin.setValue(1)
        self.cols_spin.setValue(1)
        self._on_next_clicked()
        self._cell_edits[0][0].setText("Y")
        self.show_mode_combo.setCurrentIndex(1)
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet_dialog.insert_matrix_at(QPointF(0, 0))
    assert region is not None
    region.finish_editing()
    sheet_dialog.recalculate()

    sheet_direct = _sheet()
    region2 = sheet_direct.insert_region("math", initial_text="[Y] =")
    region2.finish_editing()
    sheet_direct.recalculate()

    assert region.result.status == region2.result.status == "error"
    assert region.result.error == region2.result.error
    assert "not defined" in region.result.error


def test_mismatched_display_unit_on_mixed_matrix_error_edge_case():
    """Error-handling's own listed case: 'Units do not match' for a mismatched display unit on a
    mixed-unit matrix, surfacing on commit exactly as a direct edit would."""
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1 m, 2 kg; 3, 4] = N")
    sheet.recalculate()
    assert region.result.status == "error"
    assert "Units do not match" in region.result.error


# ===========================================================================
# Raw-text fallback (criteria 22-23)
# ===========================================================================

def test_edit_as_text_existing_region_discards_dialog_changes_and_opens_inline_editor_criterion_22():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    dlg = MatrixDialog(sheet, region=region)
    dlg._cell_edits[0][0].setText("999")

    dlg._edit_as_text_clicked()

    assert region.source == "A := [1, 2; 3, 4]"
    assert region.editing
    assert dlg.result() == QDialog.DialogCode.Rejected


def test_edit_as_text_new_insertion_behaves_exactly_like_cancel_criterion_22():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        self._cell_edits[0][0].setText("1")
        self._edit_as_text_clicked()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        result = sheet.insert_matrix_at(QPointF(0, 0))

    assert result is None
    assert sheet.regions() == []


def test_inline_editor_has_no_use_dialog_control_criterion_23():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    region.start_editing()
    # Unlike spec 006's plot raw editor (which does get a reciprocal "Use dialog..." control),
    # this region's own editor item must expose nothing matrix-dialog-specific.
    assert not hasattr(region, "_use_dialog_btn")
    assert not hasattr(region.editor, "_use_dialog_btn")


# ===========================================================================
# Regression (criteria 24-25)
# ===========================================================================

def test_save_reload_roundtrip_identical_to_direct_typing_criterion_24(tmp_path):
    sheet_dialog = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("1", "2"), ("3", "4"))
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("A")
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet_dialog.insert_matrix_at(QPointF(0, 0))
    region.finish_editing()
    sheet_dialog.recalculate()
    doc = sheet_dialog.to_document()
    assert doc.regions[0].w is None and doc.regions[0].h is None

    path = tmp_path / "via_dialog.lsheet"
    doc.save(path)
    reloaded = SheetDocument.load(path)
    assert reloaded.regions[0].kind == "math"
    assert reloaded.regions[0].text == "A := [1, 2; 3, 4]"

    sheet_direct = _sheet()
    sheet_direct.crosshair.setPos(0, 0)
    region2 = sheet_direct.insert_region("math", initial_text="A := [1, 2; 3, 4]")
    region2.finish_editing()
    path2 = tmp_path / "direct.lsheet"
    sheet_direct.to_document().save(path2)

    assert path.read_bytes() == path2.read_bytes()


def test_move_select_delete_single_owner_unaffected_criterion_25():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    sheet.recalculate()

    region.setPos(QPointF(70, 90))
    assert (region.pos().x(), region.pos().y()) == (70.0, 90.0)

    region.setSelected(True)
    sheet.remove_regions([region])
    assert region not in sheet.regions()
    assert sheet.to_document().regions == []


# ===========================================================================
# Edge cases
# ===========================================================================

def test_above_twenty_by_twenty_is_never_representable_edge_case():
    rows = "; ".join(", ".join(str(n) for n in range(21)) for _ in range(2))
    text = f"[{rows}]"
    assert decompose_matrix_text(text) is None


def test_decompose_accepts_exactly_twenty_by_twenty_edge_case():
    row = ", ".join("1" for _ in range(20))
    text = "[" + "; ".join(row for _ in range(20)) + "]"
    fields = decompose_matrix_text(text)
    assert fields is not None
    assert fields.rows == 20 and fields.cols == 20


def test_grid_bounds_disable_add_remove_buttons_at_one_and_twenty():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(1)
    dlg.cols_spin.setValue(1)
    dlg._on_next_clicked()
    assert not dlg.remove_row_btn.isEnabled()
    assert not dlg.remove_col_btn.isEnabled()
    assert dlg.add_row_btn.isEnabled() and dlg.add_col_btn.isEnabled()

    dlg.rows_spin.setValue(20)
    dlg.cols_spin.setValue(20)
    dlg._on_next_clicked()
    assert not dlg.add_row_btn.isEnabled()
    assert not dlg.add_col_btn.isEnabled()
    assert dlg.remove_row_btn.isEnabled() and dlg.remove_col_btn.isEnabled()


def test_going_back_from_grid_to_size_keeps_fitting_cells_blanks_new_ones_own_design_edge_case():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()   # 2x2 default
    _fill(dlg, ("1", "2"), ("3", "4"))
    dlg._on_back_clicked()
    dlg.rows_spin.setValue(3)
    dlg.cols_spin.setValue(3)
    dlg._on_next_clicked()

    grid = [[e.text() for e in row] for row in dlg._cell_edits]
    assert grid[0][:2] == ["1", "2"]
    assert grid[1][:2] == ["3", "4"]
    assert grid[0][2] == "" and grid[2] == ["", "", ""]


def test_going_back_and_shrinking_drops_cells_that_no_longer_fit_edge_case():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(3)
    dlg.cols_spin.setValue(3)
    dlg._on_next_clicked()
    _fill(dlg, ("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9"))
    dlg._on_back_clicked()
    dlg.rows_spin.setValue(2)
    dlg.cols_spin.setValue(2)
    dlg._on_next_clicked()

    grid = [[e.text() for e in row] for row in dlg._cell_edits]
    assert grid == [["1", "2"], ["4", "5"]]


def test_malformed_cell_expression_only_caught_on_commit_not_by_dialog_edge_case():
    """'Cells carry no syntax checking beyond non-blank/no-separator' -- a malformed expression
    like '1+' is accepted by validate_matrix_fields and only fails once the engine evaluates the
    committed text, exactly as a direct edit would."""
    fields = MatrixFields(rows=2, cols=2, cells=[["1+", "2"], ["3", "4"]])
    assert validate_matrix_fields(fields) is None   # dialog itself raises no error

    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), compile_matrix_fields(fields))
    sheet.recalculate()
    assert region.result.status == "error"


def test_nested_bracket_cell_surfaces_002a_nested_matrix_error_on_commit_edge_case():
    """A cell containing its own bracket literal is not specially checked by the dialog; 002a's
    existing 'Nested matrices are not supported' error surfaces once committed."""
    fields = MatrixFields(rows=2, cols=2, cells=[["[1,2]", "2"], ["3", "4"]])
    assert cell_has_separator("[1,2]") is False       # the comma is inside brackets, not top-level
    assert validate_matrix_fields(fields) is None      # dialog's own checks pass

    text = compile_matrix_fields(fields)
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), text)
    sheet.recalculate()
    assert region.result.status == "error"
    assert region.result.error == "Nested matrices are not supported"


@pytest.mark.parametrize("text", [
    "A := [1,2] + [3,4]",
    "det([1,2;3,4])",
    "f([1,2;3,4])",
])
def test_matrix_combined_with_other_operator_never_representable_edge_case(text):
    assert decompose_matrix_text(text) is None


def test_dialog_never_checks_name_collision_own_design_choice_edge_case():
    """The dialog itself performs no collision check; two regions defining the same name is left
    entirely to the existing engine rule (evaluation order top to bottom), unchanged by this
    dialog -- confirmed by inserting a colliding name through the dialog and letting the engine,
    not the dialog, be the one to react (or not)."""
    sheet = _sheet()
    sheet.add_region("math", QPointF(0, 0), "A := 5")

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("1", "2"), ("3", "4"))
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("A")
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(0, 50))
    # the dialog raised no "name already used" error of its own; OK succeeded unconditionally
    assert region is not None
    assert region.source == "A := [1, 2; 3, 4]"


def test_empty_bracket_literal_not_representable_edge_case():
    assert decompose_matrix_text("A := []") is None


def test_jagged_rows_not_representable_edge_case():
    assert decompose_matrix_text("[1, 2; 3]") is None
