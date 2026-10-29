"""Developer tests for spec 006 (dialog-based plot configuration), written while implementing
``livesheet/gui/plotdialog.py``. The tester will write an independent black-box review from the
spec separately; these tests exist to prove the implementation does what it was built to do.

Qt-free parts (``PlotFields``, ``compile_plot_fields``, ``decompose_plot_text``,
``attribute_error``) are tested without any Qt import. Qt-dependent parts skip gracefully when
PySide6 cannot load, matching tests/test_plot_gui.py and tests/test_gui_helpers.py.
"""

import os

import pytest

from livesheet.gui.plotdialog import (
    PlotFields,
    attribute_error,
    compile_plot_fields,
    decompose_plot_text,
)

# ---------------------------------------------------------------------------
# compile_plot_fields / decompose_plot_text: Qt-free
# ---------------------------------------------------------------------------

def test_compile_minimal_existing_mode():
    fields = PlotFields(functions=["v*t"], var_mode="existing", var_name="t")
    assert compile_plot_fields(fields) == "plot\nover t\nshow v*t"


def test_compile_sampling_mode_with_points():
    fields = PlotFields(functions=["sin(x)"], var_mode="sample", var_name="x",
                         var_from="0", var_to="6.283185307179586", var_points="5")
    assert compile_plot_fields(fields) == (
        "plot\nover x from 0 to 6.283185307179586 points 5\nshow sin(x)")


def test_compile_sampling_mode_without_points_omits_points_word():
    fields = PlotFields(functions=["sin(x)"], var_mode="sample", var_name="x", var_from="0",
                         var_to="1")
    assert "points" not in compile_plot_fields(fields)


def test_compile_skips_blank_function_rows_and_keeps_order():
    fields = PlotFields(functions=["v*t", "", "2*v*t"], var_mode="existing", var_name="t")
    assert compile_plot_fields(fields) == "plot\nover t\nshow v*t\nshow 2*v*t"


def test_compile_both_limits_blank_omits_line():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t")
    assert "xlim" not in compile_plot_fields(fields)
    assert "ylim" not in compile_plot_fields(fields)


def test_compile_half_automatic_limit():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t", x_max="8 s")
    text = compile_plot_fields(fields)
    assert "xlim auto to 8 s" in text


def test_compile_auto_word_same_as_blank():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t",
                         x_min="auto", x_max="8 s")
    assert "xlim auto to 8 s" in compile_plot_fields(fields)


def test_compile_both_limits_filled():
    fields = PlotFields(functions=["v*t"], var_mode="existing", var_name="t",
                         x_min="2 s", x_max="8 s", y_min="0 m", y_max="40 m")
    text = compile_plot_fields(fields)
    assert "xlim 2 s to 8 s" in text and "ylim 0 m to 40 m" in text


def test_compile_unit_and_label_fields():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t",
                         x_unit="ms", title="Speed")
    text = compile_plot_fields(fields)
    assert "xunit ms" in text and "title Speed" in text
    assert "xlabel" not in text and "ylabel" not in text


def test_compile_order_is_fixed():
    fields = PlotFields(functions=["v*t"], var_mode="existing", var_name="t",
                         x_unit="ms", y_unit="mm", x_min="2 s", x_max="8 s",
                         y_min="0 m", y_max="40 m", title="T", x_label="XL", y_label="YL")
    lines = compile_plot_fields(fields).splitlines()
    kws = [ln.split()[0] for ln in lines]
    assert kws == ["plot", "over", "show", "xunit", "yunit", "xlim", "ylim", "title", "xlabel",
                    "ylabel"]


def test_decompose_existing_mode_criterion_2():
    fields = decompose_plot_text("plot\nover t\nshow v*t")
    assert fields is not None
    assert fields.var_mode == "existing" and fields.var_name == "t"
    assert fields.functions == ["v*t"]
    assert fields.x_min == fields.x_max == fields.title == ""


def test_decompose_sampling_mode_criterion_3():
    fields = decompose_plot_text(
        "plot\nover x from 0 to 6.283185307179586 points 5\nshow sin(x)")
    assert fields is not None
    assert fields.var_mode == "sample"
    assert fields.var_name == "x"
    assert fields.var_from == "0"
    assert fields.var_to == "6.283185307179586"
    assert fields.var_points == "5"
    assert fields.functions == ["sin(x)"]


def test_decompose_limits_criterion_4():
    fields = decompose_plot_text(
        "plot\nover t\nshow v*t\nxlim 2 s to 8 s\nylim 0 m to 40 m")
    assert fields is not None
    assert (fields.x_min, fields.x_max) == ("2 s", "8 s")
    assert (fields.y_min, fields.y_max) == ("0 m", "40 m")
    assert fields.x_unit == "" and fields.y_unit == ""


def test_decompose_auto_limit_becomes_blank():
    fields = decompose_plot_text("plot\nover t\nshow t\nxlim auto to 8 s")
    assert fields is not None
    assert fields.x_min == "" and fields.x_max == "8 s"


def test_decompose_rejects_phase_b_keyword_criterion_5():
    assert decompose_plot_text("plot\nover t\nshow t\nxscale log") is None


def test_decompose_rejects_two_over_lines():
    assert decompose_plot_text("plot\nover t\nover s\nshow t") is None


def test_decompose_rejects_no_over_or_no_show():
    assert decompose_plot_text("plot\nshow t") is None
    assert decompose_plot_text("plot\nover t") is None
    assert decompose_plot_text("plot") is None


def test_decompose_rejects_text_not_starting_with_plot():
    assert decompose_plot_text("over t\nshow t") is None


def test_decompose_accepts_twenty_shows_rejects_twentyone():
    lines20 = "\n".join(f"show {i}" for i in range(20))
    assert decompose_plot_text(f"plot\nover t\n{lines20}") is not None
    lines21 = "\n".join(f"show {i}" for i in range(21))
    assert decompose_plot_text(f"plot\nover t\n{lines21}") is None


def test_compile_decompose_round_trip():
    original = ("plot\nover t\nshow v*t\nshow 2*v*t\nxunit ms\nyunit mm\n"
                "xlim 2 s to 8 s\nylim 0 m to 40 m\ntitle Speed\nxlabel X\nylabel Y")
    fields = decompose_plot_text(original)
    assert fields is not None
    assert compile_plot_fields(fields) == original


# ---------------------------------------------------------------------------
# attribute_error: Qt-free heuristic (Error handling section)
# ---------------------------------------------------------------------------

def test_attribute_undefined_name_to_function_row():
    fields = PlotFields(functions=["Y"], var_mode="existing", var_name="t")
    assert attribute_error("Y is not defined", fields) == ("function", 0)


def test_attribute_different_units_is_banner():
    fields = PlotFields(functions=["v*t", "t"], var_mode="existing", var_name="t")
    assert attribute_error("Units do not match: traces have different units", fields) is None


def test_attribute_wrong_shape_quoted_text_to_row():
    fields = PlotFields(functions=["Y"], var_mode="existing", var_name="t")
    assert attribute_error("show 'Y' needs a single value", fields) == ("function", 0)


def test_attribute_over_wrong_kind_to_variable():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="5")
    assert attribute_error("over needs a range variable or a vector", fields) == "variable"


def test_attribute_sampling_units_mismatch_to_variable():
    fields = PlotFields(functions=["x"], var_mode="sample", var_name="x", var_from="0 s",
                         var_to="1 m")
    assert attribute_error("Units do not match: sampling limits have different units",
                            fields) == "variable"


def test_attribute_xunit_message_to_xunit_field():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t", x_unit="s")
    assert attribute_error("xunit given but x has no unit", fields) == "xunit"


def test_attribute_generic_units_mismatch_single_axis_to_xlim():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t", x_min="5 m")
    assert attribute_error("Units do not match: limit is m", fields) == "xlim"


def test_attribute_generic_units_mismatch_both_axes_is_banner():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t",
                         x_min="5 m", y_min="2 kg")
    assert attribute_error("Units do not match: limit is m", fields) is None


def test_attribute_unmatched_message_is_banner():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t")
    assert attribute_error("no finite values to plot", fields) is None


# ---------------------------------------------------------------------------
# Qt-dependent: the dialog widget itself
# ---------------------------------------------------------------------------

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.plotdialog import PlotDialog, _FunctionEdit  # noqa: E402
from livesheet.gui.plotregion import PlotRegion  # noqa: E402
from livesheet.gui.worksheet import Worksheet  # noqa: E402

SHEET_1 = ["v := 3 m/s", "t := 0 s to 10 s step 2 s"]
PLOT_1 = "plot\nover t\nshow v*t"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _ensure_app()
    return Worksheet()


def test_function_edit_elides_when_not_focused_and_restores_when_focused():
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QFocusEvent

    _ensure_app()
    edit = _FunctionEdit("a_very_long_expression_name_that_will_not_fit_in_the_box")
    edit.resize(60, 24)
    edit.show()
    assert edit.full_text() == "a_very_long_expression_name_that_will_not_fit_in_the_box"
    assert edit.text() != edit.full_text()  # elided while not focused
    assert edit.text().endswith("…") or len(edit.text()) < len(edit.full_text())
    # Drive the focus-in/out handlers directly: real OS focus is not reliable headless.
    edit.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
    assert edit.text() == edit.full_text()  # full text restored once focused
    edit.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert edit.text() != edit.full_text()  # elided again once it loses focus


def test_dialog_prefills_from_existing_plot_criterion_2():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    dialog = PlotDialog(region, sheet)
    assert not dialog._is_new_session
    assert dialog.var_mode_combo.currentIndex() == 0
    assert dialog.var_existing_edit.text() == "t"
    assert [row["edit"].full_text() for row in dialog._rows] == ["v*t"]


def test_dialog_prefills_sampling_mode_criterion_3():
    sheet = _sheet()
    text = "plot\nover x from 0 to 6.283185307179586 points 5\nshow sin(x)"
    region = sheet.add_region("plot", QPointF(0, 0), text)
    dialog = PlotDialog(region, sheet)
    assert dialog.var_mode_combo.currentIndex() == 1
    assert dialog.var_sample_name_edit.text() == "x"
    assert dialog.var_sample_from_edit.text() == "0"
    assert dialog.var_sample_to_edit.text() == "6.283185307179586"
    assert dialog.var_sample_points_edit.text() == "5"


def test_ok_compiles_and_applies_criterion_6():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("v*t")
    assert dialog.accept() is None  # accept() returns nothing; dialog closes on success
    assert region.source == "plot\nover t\nshow v*t"
    assert region.result is not None and region.result.status == "ok"
    assert region.result.plot.traces[0].y == pytest.approx([0.0, 6.0, 12.0, 18.0, 24.0, 30.0])
    assert region.has_baseline


def test_apply_keeps_dialog_open_and_updates_region_criterion_15():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("v*t")
    dialog._apply_clicked()
    assert region.result is not None and region.result.plot is not None
    assert not region.has_baseline  # Apply alone does not establish a baseline, only OK does


def test_cancel_on_brand_new_region_discards_it_criterion_16():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("1")
    dialog._apply_clicked()  # even a successful Apply during the session...
    dialog.reject()          # ...Cancel still discards the brand-new region entirely
    assert region not in sheet.regions()


def test_cancel_on_existing_region_reverts_text_criterion_17():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog._rows[0]["edit"].set_full_text("2*v*t")
    dialog._apply_clicked()
    assert region.source != PLOT_1
    dialog.reject()
    assert region.source == PLOT_1
    assert region in sheet.regions()


def test_variable_required_message_without_engine_call_criterion_21():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog._rows[0]["edit"].set_full_text("1")
    ok = dialog._commit()
    assert not ok
    assert dialog.variable_error_label.text() == "Variable(s) is required"
    assert region.source == ""  # engine never called / region untouched


def test_at_least_one_function_required_criterion_28():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog._remove_row(dialog._rows[0])
    assert dialog._rows == []
    ok = dialog._commit()
    assert not ok
    assert dialog.functions_error_label.text() == "At least one function is required"


def test_undefined_function_error_shown_at_row_criterion_19():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    before = region.source
    dialog = PlotDialog(region, sheet)
    dialog._rows[0]["edit"].set_full_text("Y")
    ok = dialog.accept()
    assert dialog.isVisible() or not dialog.result()  # stayed open (accept() did nothing)
    assert dialog._rows[0]["error"].text() == "Y is not defined"
    assert region.source == before  # left unchanged


def test_different_units_shows_banner_criterion_20():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("v*t")
    dialog._add_row("t")
    ok = dialog._commit()
    assert not ok
    assert "different units" in dialog.banner_label.text()


def test_x_min_wrong_unit_shown_at_xlim_field_criterion_22():
    sheet = _sheet()
    for text in SHEET_1:
        sheet.add_region("math", QPointF(0, 0), text)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("v*t")
    dialog.x_min_edit.setText("5 m")
    ok = dialog._commit()
    assert not ok
    assert "Units do not match" in dialog.xlim_error_label.text()


def test_min_above_max_caught_locally_criterion_23():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog.var_existing_edit.setText("t")
    dialog._rows[0]["edit"].set_full_text("1")
    dialog.x_min_edit.setText("8 s")
    dialog.x_max_edit.setText("2 s")
    ok = dialog._commit()
    assert not ok
    assert dialog.xlim_error_label.text() == "lower limit must be below upper limit"
    assert region.source == ""  # dialog's own check: the engine was never actually called


def test_points_out_of_range_caught_locally():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog.var_mode_combo.setCurrentIndex(1)
    dialog.var_sample_name_edit.setText("x")
    dialog.var_sample_from_edit.setText("0")
    dialog.var_sample_to_edit.setText("1")
    dialog.var_sample_points_edit.setText("1")
    dialog._rows[0]["edit"].set_full_text("x")
    ok = dialog._commit()
    assert not ok
    assert dialog.variable_error_label.text() == "points must be between 2 and 10000"


def test_add_function_disabled_at_twenty_rows():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    for _ in range(19):
        dialog._add_row("1")
    assert len(dialog._rows) == 20
    assert not dialog.add_function_btn.isEnabled()
    dialog._add_row("1")
    assert len(dialog._rows) == 20  # the 21st add is a no-op


def test_remove_row_shifts_remaining_rows_up_criterion_9():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog._rows[0]["edit"].set_full_text("a")
    dialog._add_row("b")
    dialog._add_row("c")
    dialog._remove_row(dialog._rows[1])  # remove "b"
    assert [row["edit"].full_text() for row in dialog._rows] == ["a", "c"]


def test_edit_as_text_blank_new_region_uses_starter_text_criterion_24():
    from livesheet.gui.plotregion import STARTER_TEXT

    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dialog = PlotDialog(region, sheet)
    dialog._edit_as_text_clicked()
    assert region.source == STARTER_TEXT
    assert region.editing


def test_edit_as_text_representable_region_uses_current_fields():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    dialog = PlotDialog(region, sheet)
    dialog._rows[0]["edit"].set_full_text("2*v*t")
    dialog._edit_as_text_clicked()
    assert region.source == "plot\nover t\nshow 2*v*t"
    assert region.editing


def test_use_dialog_control_enabled_only_when_representable():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    region.start_editing()
    assert region._use_dialog_btn.isEnabled()
    region.editor.setPlainText("plot\nover t\nshow t\nxscale log")
    assert not region._use_dialog_btn.isEnabled()


def test_double_click_opens_dialog_when_representable():
    import unittest.mock as mock

    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    opened = []
    with mock.patch.object(PlotDialog, "exec", lambda self: opened.append(self)):
        region.mouseDoubleClickEvent(_FakeEvent())
    assert len(opened) == 1
    assert opened[0].region is region


def test_insert_region_plot_then_cancel_leaves_no_region_criterion_1():
    sheet = _sheet()

    def fake_exec(self):
        self.reject()

    import unittest.mock as mock

    with mock.patch.object(PlotDialog, "exec", fake_exec):
        sheet.insert_region("plot")
    assert sheet.regions() == []


def test_double_click_opens_raw_editor_when_not_representable():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "plot\nover t\nshow t\nxscale log")
    region.mouseDoubleClickEvent(_FakeEvent())
    assert region.editing


class _FakeEvent:
    """A stand-in for a QGraphicsSceneMouseEvent; only ``accept``/``scenePos`` may be called."""

    def accept(self) -> None:
        pass

    def scenePos(self):
        from PySide6.QtCore import QPointF
        return QPointF(0, 0)
