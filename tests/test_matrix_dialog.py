"""Developer tests for spec 008 (dialog-based vector/matrix insertion), written while
implementing ``livesheet/gui/matrixdialog.py``. The tester will write an independent black-box
review from the spec separately; these tests exist to prove the implementation does what it was
built to do, covering acceptance criteria 1-25.

Qt-free parts (``MatrixFields``, ``compile_matrix_fields``, ``decompose_matrix_text``,
``validate_matrix_fields``, ``cell_has_separator``) are tested without any Qt import.
Qt-dependent parts skip gracefully when PySide6 cannot load, matching tests/test_plot_gui.py and
tests/test_plot_dialog_dev.py.
"""

import pytest

from livesheet.gui.matrixdialog import (
    MatrixFields,
    cell_has_separator,
    compile_matrix_fields,
    decompose_matrix_text,
    validate_matrix_fields,
)

# ===========================================================================
# compile_matrix_fields / decompose_matrix_text / validate_matrix_fields: Qt-free
# ===========================================================================

def test_compile_minimal_two_by_two_criterion_8():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]])
    assert compile_matrix_fields(fields) == "[1, 2; 3, 4]"


def test_compile_define_and_numeric_show_blank_unit_criterion_9():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]],
                           name_mode="define", name="A", assign_op=":=",
                           show_mode="numeric")
    assert compile_matrix_fields(fields) == "A := [1, 2; 3, 4] ="


def test_compile_scale_and_define_matches_002a_example_criterion_10():
    fields = MatrixFields(cells=[["2", "-1"], ["-1", "2"]],
                           name_mode="define", name="K", assign_op=":=", scale="N/m")
    assert compile_matrix_fields(fields) == "K := [2, -1; -1, 2]*N/m"


def test_compile_row_vector_criterion_12():
    fields = MatrixFields(rows=1, cols=3, cells=[["5", "6", "7"]])
    assert compile_matrix_fields(fields) == "[5, 6, 7]"


def test_compile_column_vector_criterion_12():
    fields = MatrixFields(rows=3, cols=1, cells=[["5"], ["6"], ["7"]])
    assert compile_matrix_fields(fields) == "[5; 6; 7]"


def test_compile_one_by_one_criterion_13():
    fields = MatrixFields(rows=1, cols=1, cells=[["5"]])
    assert compile_matrix_fields(fields) == "[5]"


def test_compile_global_definition_uses_equiv_symbol():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]],
                           name_mode="define", name="A", assign_op="≡")
    assert compile_matrix_fields(fields) == "A ≡ [1, 2; 3, 4]"


def test_compile_symbolic_show_suffix():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]], show_mode="symbolic")
    assert compile_matrix_fields(fields) == "[1, 2; 3, 4] →"


def test_compile_numeric_show_with_display_unit():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]], show_mode="numeric",
                           display_unit="kN")
    assert compile_matrix_fields(fields) == "[1, 2; 3, 4] = kN"


def test_decompose_plain_definition_criterion_3():
    fields = decompose_matrix_text("A := [1, 2; 3, 4]")
    assert fields is not None
    assert fields.cells == [["1", "2"], ["3", "4"]]
    assert fields.name_mode == "define" and fields.name == "A" and fields.assign_op == ":="
    assert fields.scale == "" and fields.show_mode == "none"


def test_decompose_trailing_numeric_show_criterion_4():
    fields = decompose_matrix_text("A := [1, 2; 3, 4] =")
    assert fields is not None
    assert fields.name == "A" and fields.show_mode == "numeric" and fields.display_unit == ""


def test_decompose_scale_factor_criterion_5():
    fields = decompose_matrix_text("K := [2, -1; -1, 2]*N/m")
    assert fields is not None
    assert fields.name == "K" and fields.cells == [["2", "-1"], ["-1", "2"]]
    assert fields.scale == "N/m" and fields.show_mode == "none"


def test_decompose_two_terms_not_representable_criterion_6():
    assert decompose_matrix_text("A + [1, 2, 3; 4, 5, 6]") is None


def test_decompose_symbolic_cells_criterion_7():
    fields = decompose_matrix_text("M := [a, b; c, d]")
    assert fields is not None
    assert fields.cells == [["a", "b"], ["c", "d"]]


def test_decompose_rejects_matrix_passed_to_a_function():
    assert decompose_matrix_text("det([1, 2; 3, 4])") is None
    assert decompose_matrix_text("f([1, 2; 3, 4])") is None


def test_decompose_rejects_matrix_combined_with_plus():
    assert decompose_matrix_text("A := [1, 2] + [3, 4]") is None


def test_decompose_rejects_blank_text():
    assert decompose_matrix_text("") is None
    assert decompose_matrix_text("   ") is None


def test_decompose_rejects_empty_matrix_literal():
    assert decompose_matrix_text("[]") is None


def test_decompose_rejects_bigger_than_twenty_by_twenty():
    big_row = ", ".join(str(i) for i in range(21))
    text = "[" + "; ".join([big_row] * 2) + "]"
    assert decompose_matrix_text(text) is None


def test_decompose_accepts_twenty_by_twenty():
    row = ", ".join(str(i) for i in range(20))
    text = "[" + "; ".join([row] * 20) + "]"
    fields = decompose_matrix_text(text)
    assert fields is not None
    assert fields.rows == 20 and fields.cols == 20


def test_decompose_global_definition():
    fields = decompose_matrix_text("A ≡ [1, 2; 3, 4]")
    assert fields is not None
    assert fields.assign_op == "≡"


def test_decompose_symbolic_show():
    fields = decompose_matrix_text("[1, 2; 3, 4] →")
    assert fields is not None
    assert fields.show_mode == "symbolic"


def test_decompose_rejects_arrow_with_keywords():
    assert decompose_matrix_text("[1, 2; 3, 4] → factor") is None


def test_decompose_rejects_jagged_rows():
    assert decompose_matrix_text("[1, 2; 3]") is None


def test_compile_decompose_round_trip_examples():
    for text in ("[1, 2; 3, 4]", "A := [1, 2; 3, 4]", "A := [1, 2; 3, 4] =",
                 "K := [2, -1; -1, 2]*N/m", "M := [a, b; c, d]", "[5]", "[5, 6, 7]",
                 "[5; 6; 7]", "A ≡ [1, 2; 3, 4]", "[1, 2; 3, 4] →"):
        fields = decompose_matrix_text(text)
        assert fields is not None, text
        assert compile_matrix_fields(fields) == text


def test_cell_has_separator_detects_top_level_comma_and_semicolon():
    assert cell_has_separator("1, 2")
    assert cell_has_separator("1; 2")
    assert not cell_has_separator("f(a, b)")
    assert not cell_has_separator("a+1")


def test_validate_blank_cell_criterion_18():
    fields = MatrixFields(cells=[["1", ""], ["3", "4"]])
    err = validate_matrix_fields(fields)
    assert err is not None
    assert err.location == (0, 1)
    assert err.message == "Every cell must have a value"


def test_validate_cell_separator_criterion_19():
    err = validate_matrix_fields(MatrixFields(cells=[["1", "2"], ["3, 4", "5"]]))
    assert err is not None
    assert err.location == (1, 0)
    assert err.message == "A cell cannot contain ',' or ';'; use Add column/Add row instead"


def test_validate_cell_with_function_call_comma_is_fine():
    fields = MatrixFields(cells=[["f(a, b)", "2"], ["3", "4"]])
    assert validate_matrix_fields(fields) is None


def test_validate_name_required_criterion_20():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]], name_mode="define", name="")
    err = validate_matrix_fields(fields)
    assert err is not None
    assert err.location == "name"
    assert err.message == "Name is required"


def test_validate_passes_when_everything_is_fine():
    fields = MatrixFields(cells=[["1", "2"], ["3", "4"]])
    assert validate_matrix_fields(fields) is None


# ===========================================================================
# Qt-dependent: the dialog widget and its wiring into Worksheet/MainWindow
# ===========================================================================

import os  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

import unittest.mock as mock  # noqa: E402

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.gui.matrixdialog import MatrixDialog  # noqa: E402
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


class _FakeEvent:
    """A stand-in for a QGraphicsSceneMouseEvent; only ``accept``/``scenePos`` are used."""

    def accept(self) -> None:
        pass

    def scenePos(self) -> QPointF:
        return QPointF(0, 0)


# -- Trigger and pre-fill (criteria 1-7) ---------------------------------------------------

def test_insert_matrix_at_opens_size_step_with_defaults_and_cancel_criterion_1():
    sheet = _sheet()
    opened = []

    def fake_exec(self):
        opened.append(self)
        self.reject()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        result = sheet.insert_matrix_at(QPointF(80, 80))

    assert result is None
    assert sheet.regions() == []
    dlg = opened[0]
    assert dlg.rows_spin.value() == 2
    assert dlg.cols_spin.value() == 2
    assert dlg._stack.currentIndex() == 0  # the Size step, not the Grid step


def test_next_opens_grid_step_with_blank_cells_criterion_2():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(3)
    dlg.cols_spin.setValue(1)
    dlg._on_next_clicked()

    assert dlg._stack.currentIndex() == 1
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [[""], [""], [""]]
    assert dlg.name_mode_combo.currentIndex() == 0
    assert dlg.show_mode_combo.currentIndex() == 0
    assert dlg.scale_edit.text() == ""


def test_edit_as_grid_prefill_plain_definition_criterion_3():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    dlg = MatrixDialog(sheet, region=region)

    assert dlg._stack.currentIndex() == 1
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2"], ["3", "4"]]
    assert dlg.name_mode_combo.currentIndex() == 1
    assert dlg.name_edit.text() == "A"
    assert dlg.assign_combo.currentIndex() == 0
    assert dlg.scale_edit.text() == ""
    assert dlg.show_mode_combo.currentIndex() == 0


def test_edit_as_grid_prefill_with_numeric_show_criterion_4():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4] =")
    dlg = MatrixDialog(sheet, region=region)

    assert dlg.show_mode_combo.currentIndex() == 1
    assert dlg.display_unit_edit.text() == ""


def test_edit_as_grid_prefill_with_scale_criterion_5():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "K := [2, -1; -1, 2]*N/m")
    dlg = MatrixDialog(sheet, region=region)

    assert dlg.name_edit.text() == "K"
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["2", "-1"], ["-1", "2"]]
    assert dlg.scale_edit.text() == "N/m"
    assert dlg.show_mode_combo.currentIndex() == 0


def test_non_representable_region_has_no_edit_as_grid_entry_criterion_6():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A + [1, 2, 3; 4, 5, 6]")
    assert decompose_matrix_text(region.source) is None
    region.mouseDoubleClickEvent(_FakeEvent())
    assert region.editing  # today's ordinary inline text editing, unchanged


def test_edit_as_grid_prefill_symbolic_cells_criterion_7():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "M := [a, b; c, d]")
    dlg = MatrixDialog(sheet, region=region)

    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["a", "b"], ["c", "d"]]


# -- Fields and compile mapping (criteria 8-13) ---------------------------------------------

def test_insert_matrix_at_creates_region_left_editing_criterion_8():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("1", "2"), ("3", "4"))
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(40, 40))

    assert region is not None and isinstance(region, MathRegion)
    assert region.source == "[1, 2; 3, 4]"
    assert region.editing
    assert region.editor.toPlainText() == "[1, 2; 3, 4]"


def test_ok_new_insertion_define_and_numeric_show_matches_002a_criterion_9():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("1", "2"), ("3", "4"))
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("A")
        self.show_mode_combo.setCurrentIndex(1)
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(40, 40))

    assert region.source == "A := [1, 2; 3, 4] ="
    region.finish_editing()
    sheet.recalculate()
    assert region.result is not None and region.result.status == "ok"
    assert region.result.output == "= [1, 2; 3, 4]"


def test_ok_new_insertion_scale_and_define_matches_002a_example_criterion_10():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("2", "-1"), ("-1", "2"))
        self.scale_edit.setText("N/m")
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("K")
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(40, 40))

    assert region.source == "K := [2, -1; -1, 2]*N/m"


def test_add_column_and_remove_row_track_current_shape_criterion_11():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()
    _fill(dlg, ("1", "2"), ("3", "4"))

    dlg._add_column()
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2", ""], ["3", "4", ""]]

    dlg._remove_row()
    assert [[e.text() for e in row] for row in dlg._cell_edits] == [["1", "2", ""]]
    dlg._cell_edits[0][2].setText("5")
    assert compile_matrix_fields(dlg._collect_fields()) == "[1, 2, 5]"


def test_add_remove_row_column_disabled_at_bounds():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(1)
    dlg.cols_spin.setValue(1)
    dlg._on_next_clicked()
    assert not dlg.remove_row_btn.isEnabled()
    assert not dlg.remove_col_btn.isEnabled()

    dlg.rows_spin.setValue(20)
    dlg.cols_spin.setValue(20)
    dlg._on_next_clicked()
    assert not dlg.add_row_btn.isEnabled()
    assert not dlg.add_col_btn.isEnabled()
    dlg._add_row()    # no-op past the cap
    dlg._add_column()
    assert len(dlg._cell_edits) == 20 and len(dlg._cell_edits[0]) == 20


def test_row_vector_and_column_vector_through_widget_criterion_12():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(1)
    dlg.cols_spin.setValue(3)
    dlg._on_next_clicked()
    _fill(dlg, ("5", "6", "7"))
    assert compile_matrix_fields(dlg._collect_fields()) == "[5, 6, 7]"

    dlg2 = MatrixDialog(sheet, region=None)
    dlg2.rows_spin.setValue(3)
    dlg2.cols_spin.setValue(1)
    dlg2._on_next_clicked()
    _fill(dlg2, ("5",), ("6",), ("7",))
    assert compile_matrix_fields(dlg2._collect_fields()) == "[5; 6; 7]"


def test_one_by_one_through_widget_criterion_13():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg.rows_spin.setValue(1)
    dlg.cols_spin.setValue(1)
    dlg._on_next_clicked()
    _fill(dlg, ("5",))
    assert compile_matrix_fields(dlg._collect_fields()) == "[5]"


# -- OK / Cancel, new insertion (criteria 14-15) --------------------------------------------

def test_cancel_on_size_step_creates_nothing_criterion_14():
    sheet = _sheet()

    def fake_exec(self):
        self.reject()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        result = sheet.insert_matrix_at(QPointF(10, 10))

    assert result is None
    assert sheet.regions() == []


def test_cancel_on_grid_step_creates_nothing_criterion_14():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        self._cell_edits[0][0].setText("1")
        self.reject()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        result = sheet.insert_matrix_at(QPointF(10, 10))

    assert result is None
    assert sheet.regions() == []


def test_ok_same_net_effect_as_typing_directly_criterion_15():
    def via_dialog():
        sheet = _sheet()

        def fake_exec(self):
            self._on_next_clicked()
            _fill(self, ("1", "2"), ("3", "4"))
            self.name_mode_combo.setCurrentIndex(1)
            self.name_edit.setText("A")
            self.show_mode_combo.setCurrentIndex(1)
            self.accept()
            return self.result()

        with mock.patch.object(MatrixDialog, "exec", fake_exec):
            region = sheet.insert_matrix_at(QPointF(0, 0))
        region.finish_editing()
        sheet.recalculate()
        return region.result

    def via_direct_type():
        sheet = _sheet()
        region = sheet.insert_region("math", initial_text="A := [1, 2; 3, 4] =")
        region.finish_editing()
        sheet.recalculate()
        return region.result

    r1, r2 = via_dialog(), via_direct_type()
    assert r1.status == r2.status == "ok"
    assert r1.output == r2.output


# -- OK / Cancel, existing region (criteria 16-17) -------------------------------------------

def test_cancel_on_existing_region_leaves_source_untouched_criterion_16():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    dlg = MatrixDialog(sheet, region=region)
    dlg._cell_edits[1][1].setText("40")

    dlg.reject()

    assert region.source == "A := [1, 2; 3, 4]"
    assert region in sheet.regions()


def test_ok_on_existing_region_updates_source_and_result_criterion_17():
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


# -- Errors (criteria 18-21) -----------------------------------------------------------------

def test_blank_cell_error_criterion_18():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()
    dlg._cell_edits[0][0].setText("1")   # the other three cells left blank

    dlg.accept()

    assert dlg.result() == 0   # dialog stayed open
    assert dlg.banner_label.text() == "Every cell must have a value"
    assert dlg._cell_edits[0][1].styleSheet() != ""
    assert sheet.regions() == []


def test_cell_separator_error_criterion_19():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()
    _fill(dlg, ("1", "1, 2"), ("1", "1"))

    dlg.accept()

    assert dlg.result() == 0
    assert dlg.banner_label.text() == "A cell cannot contain ',' or ';'; use Add column/Add row instead"


def test_name_required_error_criterion_20():
    sheet = _sheet()
    dlg = MatrixDialog(sheet, region=None)
    dlg._on_next_clicked()
    _fill(dlg, ("1", "2"), ("3", "4"))
    dlg.name_mode_combo.setCurrentIndex(1)
    dlg.name_edit.setText("")

    dlg.accept()

    assert dlg.result() == 0
    assert dlg.banner_label.text() == "Name is required"


def test_undefined_symbol_error_surfaces_on_region_criterion_21():
    sheet = _sheet()

    def fake_exec(self):
        self.rows_spin.setValue(1)
        self.cols_spin.setValue(1)
        self._on_next_clicked()
        self._cell_edits[0][0].setText("Y")
        self.show_mode_combo.setCurrentIndex(1)
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(0, 0))

    assert region is not None
    region.finish_editing()
    sheet.recalculate()
    assert region.result is not None and region.result.status == "error"
    assert "not defined" in region.result.error


# -- Raw-text fallback (criteria 22-23) -------------------------------------------------------

def test_edit_as_text_on_existing_region_discards_changes_criterion_22():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    dlg = MatrixDialog(sheet, region=region)
    dlg._cell_edits[0][0].setText("99")

    dlg._edit_as_text_clicked()

    assert region.source == "A := [1, 2; 3, 4]"
    assert region.editing
    assert dlg.result() == QDialog.DialogCode.Rejected


def test_edit_as_text_on_new_insertion_behaves_like_cancel_criterion_22():
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        self._cell_edits[0][0].setText("1")
        self._edit_as_text_clicked()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        result = sheet.insert_matrix_at(QPointF(0, 0))

    assert result is None
    assert sheet.regions() == []


def test_no_use_dialog_control_in_inline_editor_criterion_23():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    region.start_editing()
    assert not hasattr(region, "_use_dialog_btn")


# -- Regression (criteria 24-25) --------------------------------------------------------------

def test_save_reload_roundtrip_byte_for_byte_criterion_24(tmp_path):
    sheet = _sheet()

    def fake_exec(self):
        self._on_next_clicked()
        _fill(self, ("1", "2"), ("3", "4"))
        self.name_mode_combo.setCurrentIndex(1)
        self.name_edit.setText("A")
        self.accept()
        return self.result()

    with mock.patch.object(MatrixDialog, "exec", fake_exec):
        region = sheet.insert_matrix_at(QPointF(0, 0))
    region.finish_editing()
    sheet.recalculate()

    doc = sheet.to_document()
    path = tmp_path / "matrix.lsheet"
    doc.save(path)
    reloaded = SheetDocument.load(path)
    rd = reloaded.regions[0]
    assert rd.kind == "math"
    assert rd.text == "A := [1, 2; 3, 4]"
    assert rd.w is None and rd.h is None

    sheet2 = _sheet()
    sheet2.crosshair.setPos(0, 0)   # match insert_matrix_at's crosshair placement above
    region2 = sheet2.insert_region("math", initial_text="A := [1, 2; 3, 4]")
    region2.finish_editing()
    doc2 = sheet2.to_document()
    path2 = tmp_path / "direct.lsheet"
    doc2.save(path2)
    assert path.read_bytes() == path2.read_bytes()


def test_move_select_delete_unaffected_criterion_25():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    sheet.recalculate()

    region.setPos(QPointF(50, 60))
    assert (region.pos().x(), region.pos().y()) == (50.0, 60.0)

    region.setSelected(True)
    sheet.remove_regions([region])
    assert region not in sheet.regions()
    assert all(rd.kind != "math" or rd.text != "A := [1, 2; 3, 4]"
               for rd in sheet.to_document().regions)


# -- Context menu wiring (Worksheet.contextMenuEvent, "Fits current architecture?") ----------

def test_open_matrix_dialog_helper_used_for_existing_region():
    sheet = _sheet()
    region = sheet.add_region("math", QPointF(0, 0), "A := [1, 2; 3, 4]")
    opened = []
    with mock.patch.object(MatrixDialog, "exec", lambda self: opened.append(self)):
        sheet._open_matrix_dialog(region)
    assert len(opened) == 1
    assert opened[0].region is region
