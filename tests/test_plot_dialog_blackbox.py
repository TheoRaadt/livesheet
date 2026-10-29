"""Independent black-box tests for spec 006 (dialog-based plot configuration), written from
docs/board/specs/006-plot-dialog.md's acceptance criteria and edge cases, not from reading
livesheet/gui/plotdialog.py's internals beyond the small public names the spec itself names
(``PlotDialog``, ``PlotFields``, ``compile_plot_fields``, ``decompose_plot_text``,
``attribute_error``). Where a GUI test needs to look at a widget's state (e.g. a field's
``.text()``, an error label, a row's edit box) this mirrors the pattern already used by
tests/test_plot_gui.py and tests/test_plot_dialog_dev.py, not a departure from black-box style:
the dialog's fields and buttons are exactly the "form" surface the spec describes.

Written independently of tests/test_plot_dialog_dev.py (the developer's own tests); that file was
read afterwards only to avoid pointless duplication, not consulted while designing these cases.
Qt-dependent tests skip gracefully when PySide6 cannot load, as the existing GUI tests do.
"""

import math
import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QEvent, QPointF  # noqa: E402
from PySide6.QtGui import QFocusEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.engine import Engine  # noqa: E402
from livesheet.engine.plotting import MAX_TRACES  # noqa: E402
from livesheet.gui.main_window import export_pdf  # noqa: E402
from livesheet.gui.plotdialog import (  # noqa: E402
    PlotDialog,
    PlotFields,
    _FunctionEdit,
    attribute_error,
    compile_plot_fields,
    decompose_plot_text,
)
from livesheet.gui.plotregion import STARTER_TEXT, PlotRegion  # noqa: E402
from livesheet.gui.worksheet import Worksheet  # noqa: E402

SHEET_1 = ["v := 3 m/s", "t := 0 s to 10 s step 2 s"]
PLOT_1 = "plot\nover t\nshow v*t"  # spec 004 criterion 1's text
SAMPLE_4 = "plot\nover x from 0 to 6.283185307179586 points 5\nshow sin(x)"  # criterion 4's text


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _ensure_app()
    return Worksheet()


def _sheet_with(*texts: str) -> Worksheet:
    sheet = _sheet()
    for text in texts:
        sheet.add_region("math", QPointF(0, 0), text)
    return sheet


class _FakeEvent:
    """A stand-in for a QGraphicsSceneMouseEvent; only ``accept``/``scenePos`` are used."""

    def accept(self) -> None:
        pass

    def scenePos(self) -> QPointF:
        return QPointF(0, 0)


# ===========================================================================
# Trigger and pre-fill (criteria 1-5)
# ===========================================================================

def test_plot_here_opens_dialog_with_all_fields_blank_criterion_1():
    """The canvas 'Plot here' entry (``Worksheet.insert_plot_at``) must land on exactly the same
    blank-dialog state as Insert > Plot: Function(s) one blank row, Variable(s) empty in
    existing-name mode, every other field blank."""
    sheet = _sheet()
    opened = []

    def fake_exec(self):
        opened.append(self)

    import unittest.mock as mock

    with mock.patch.object(PlotDialog, "exec", fake_exec):
        region = sheet.insert_plot_at(QPointF(80, 80))

    assert region.kind == "plot"
    assert region.source == ""
    assert len(opened) == 1
    dlg = opened[0]
    assert [row["edit"].full_text() for row in dlg._rows] == [""]
    assert dlg.var_mode_combo.currentIndex() == 0  # "Use existing" is the default mode
    for box in (dlg.var_existing_edit, dlg.var_sample_name_edit, dlg.var_sample_from_edit,
                dlg.var_sample_to_edit, dlg.var_sample_points_edit, dlg.y_min_edit,
                dlg.y_max_edit, dlg.x_min_edit, dlg.x_max_edit, dlg.x_unit_edit,
                dlg.y_unit_edit, dlg.title_edit, dlg.x_label_edit, dlg.y_label_edit):
        assert box.text() == ""


def test_plot_here_then_cancel_leaves_no_region_criterion_1():
    sheet = _sheet()

    def fake_exec(self):
        self.reject()

    import unittest.mock as mock

    with mock.patch.object(PlotDialog, "exec", fake_exec):
        sheet.insert_plot_at(QPointF(80, 80))

    assert sheet.regions() == []
    assert sheet.to_document().regions == []


def test_double_click_prefills_existing_mode_criterion_2():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    assert dlg.var_mode_combo.currentIndex() == 0
    assert dlg.var_existing_edit.text() == "t"
    assert [row["edit"].full_text() for row in dlg._rows] == ["v*t"]
    for box in (dlg.y_min_edit, dlg.y_max_edit, dlg.x_min_edit, dlg.x_max_edit,
                dlg.x_unit_edit, dlg.y_unit_edit, dlg.title_edit, dlg.x_label_edit,
                dlg.y_label_edit):
        assert box.text() == ""


def test_double_click_prefills_sampling_mode_criterion_3():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), SAMPLE_4)
    dlg = PlotDialog(region, sheet)
    assert dlg.var_mode_combo.currentIndex() == 1
    assert dlg.var_sample_name_edit.text() == "x"
    assert dlg.var_sample_from_edit.text() == "0"
    assert dlg.var_sample_to_edit.text() == "6.283185307179586"
    assert dlg.var_sample_points_edit.text() == "5"
    assert [row["edit"].full_text() for row in dlg._rows] == ["sin(x)"]


def test_double_click_prefills_limits_criterion_4():
    text = PLOT_1 + "\nxlim 2 s to 8 s\nylim 0 m to 40 m"
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), text)
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    assert (dlg.x_min_edit.text(), dlg.x_max_edit.text()) == ("2 s", "8 s")
    assert (dlg.y_min_edit.text(), dlg.y_max_edit.text()) == ("0 m", "40 m")
    assert dlg.x_unit_edit.text() == "" and dlg.y_unit_edit.text() == ""


@pytest.mark.parametrize("extra_line", ["xscale log", "mode polar", "style points"])
def test_double_click_non_representable_opens_raw_editor_criterion_5(extra_line):
    sheet = _sheet()
    text = f"plot\nover t\nshow t\n{extra_line}"
    region = sheet.add_region("plot", QPointF(0, 0), text)
    assert decompose_plot_text(text) is None
    region.mouseDoubleClickEvent(_FakeEvent())
    assert region.editing  # the existing raw multi-line editor opened, unchanged


def test_double_click_on_representable_region_opens_dialog_prefilled():
    """The actual double-click entry point (not a direct ``PlotDialog(...)`` construction):
    routes to the dialog, pre-filled, for a representable region."""
    import unittest.mock as mock

    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    opened = []
    with mock.patch.object(PlotDialog, "exec", lambda self: opened.append(self)):
        region.mouseDoubleClickEvent(_FakeEvent())

    assert len(opened) == 1
    dlg = opened[0]
    assert dlg.region is region
    assert dlg.var_existing_edit.text() == "t"
    assert [row["edit"].full_text() for row in dlg._rows] == ["v*t"]
    assert not region.editing  # the raw editor did not also open


def test_double_click_two_over_lines_also_opens_raw_editor():
    """A second non-representable shape not explicitly named by criterion 5's example: more than
    one 'over' line."""
    sheet = _sheet()
    text = "plot\nover t\nover s\nshow t"
    region = sheet.add_region("plot", QPointF(0, 0), text)
    region.mouseDoubleClickEvent(_FakeEvent())
    assert region.editing


# ===========================================================================
# Fields and compile mapping (criteria 6-14)
# ===========================================================================

def test_ok_minimal_sheet_matches_criterion_1_numbers_exactly():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.accept()

    assert region.source == "plot\nover t\nshow v*t"
    plot = region.result.plot
    assert plot is not None
    trace = plot.traces[0]
    assert trace.x == pytest.approx([0, 2, 4, 6, 8, 10])
    assert trace.y == pytest.approx([0, 6, 12, 18, 24, 30])
    assert plot.x_unit == "s" and plot.y_unit == "m"
    assert plot.x_label == "t [s]" and plot.y_label == "v*t [m]"
    assert plot.x_limits == (0, 10) and plot.y_limits == (0, 30)
    assert plot.x_ticks == pytest.approx([0, 2, 4, 6, 8, 10])
    assert plot.y_ticks == pytest.approx([0, 5, 10, 15, 20, 25, 30])


def test_ok_sampling_mode_matches_criterion_4_numbers_exactly():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.var_mode_combo.setCurrentIndex(1)
    dlg.var_sample_name_edit.setText("x")
    dlg.var_sample_from_edit.setText("0")
    dlg.var_sample_to_edit.setText("6.283185307179586")
    dlg.var_sample_points_edit.setText("5")
    dlg._rows[0]["edit"].set_full_text("sin(x)")
    dlg.accept()

    assert region.source == SAMPLE_4
    plot = region.result.plot
    trace = plot.traces[0]
    expected_x = [0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi]
    expected_y = [0, 1, 0, -1, 0]
    for actual, exp in zip(trace.x, expected_x):
        assert actual == pytest.approx(exp, abs=1e-12)
    for actual, exp in zip(trace.y, expected_y):
        assert actual == pytest.approx(exp, abs=1e-12)
    assert plot.x_unit == "" and plot.y_unit == ""
    assert plot.y_limits == (-1, 1)
    assert plot.y_ticks == pytest.approx([-1, -0.5, 0, 0.5, 1])
    assert plot.x_label == "x"


def test_add_function_row_two_traces_matches_criterion_3():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.add_function_btn.click()
    assert [row["edit"].full_text() for row in dlg._rows] == ["v*t", ""]
    dlg._rows[1]["edit"].set_full_text("2*v*t")
    dlg.accept()

    assert region.source == "plot\nover t\nshow v*t\nshow 2*v*t"
    traces = region.result.plot.traces
    assert len(traces) == 2
    assert traces[1].style_index == 1
    assert traces[1].y == pytest.approx([0, 12, 24, 36, 48, 60])
    assert region.result.plot.y_limits == (0, 60)
    assert region.result.plot.y_ticks == pytest.approx([0, 10, 20, 30, 40, 50, 60])


def test_remove_first_row_shifts_remaining_rows_and_style_index():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg._add_row("2*v*t")
    dlg._add_row("3*v*t")
    dlg._rows[0]["remove"].click()  # remove "v*t" via the real button, not a private call only

    assert [row["edit"].full_text() for row in dlg._rows] == ["2*v*t", "3*v*t"]
    dlg.accept()
    assert region.source == "plot\nover t\nshow 2*v*t\nshow 3*v*t"
    traces = region.result.plot.traces
    assert [t.label for t in traces] == ["2*v*t", "3*v*t"]
    assert [t.style_index for t in traces] == [0, 1]


def test_add_function_disabled_once_twenty_rows_exist_criterion_10():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    for i in range(19):
        dlg._add_row(str(i))
    assert len(dlg._rows) == 20
    assert not dlg.add_function_btn.isEnabled()
    dlg.add_function_btn.click()  # the 21st add, through the real button
    assert len(dlg._rows) == 20


def test_add_function_cap_counts_blank_rows_too_spec_wording_gap():
    """Criterion 10 literally says 'disabled once 20 NON-BLANK rows exist', but the 'Fields'
    section says 'disabled once 20 rows exist' (no non-blank qualifier). The implementation
    follows the 'Fields' wording: with 19 filled rows plus one left blank (20 rows, 19 non-blank),
    Add is already disabled. This is recorded as a spec-wording inconsistency in the review, not
    asserted as a hard failure here (the dialog's behaviour is a defensible reading of the more
    detailed 'Fields' section)."""
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("0")  # fill the default first row too
    for i in range(1, 19):
        dlg._add_row(str(i))
    dlg._add_row("")  # 20th row, left blank: only 19 of 20 rows are non-blank
    assert len(dlg._rows) == 20
    non_blank = sum(1 for r in dlg._rows if r["edit"].full_text().strip())
    assert non_blank == 19
    assert not dlg.add_function_btn.isEnabled()  # disabled despite < 20 non-blank rows


def test_twenty_one_traces_cannot_be_produced_from_the_dialog():
    """Criterion 10's consequence: spec 004 criterion 13's 21-trace 'too many traces' engine error
    can never actually be triggered through this dialog, because the UI itself caps rows at
    MAX_TRACES (20)."""
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    for i in range(MAX_TRACES - 1):
        dlg._add_row(str(i))
    assert len(dlg._rows) == MAX_TRACES
    dlg._add_row(str(MAX_TRACES))  # no-op: cap already reached
    assert len(dlg._rows) == MAX_TRACES


def test_full_manual_limits_matches_criterion_7():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.y_min_edit.setText("0 m")
    dlg.y_max_edit.setText("40 m")
    dlg.x_min_edit.setText("2 s")
    dlg.x_max_edit.setText("8 s")
    dlg.accept()

    assert "xlim 2 s to 8 s" in region.source and "ylim 0 m to 40 m" in region.source
    plot = region.result.plot
    assert plot.x_limits == (2, 8) and plot.x_ticks == pytest.approx([2, 3, 4, 5, 6, 7, 8])
    assert plot.y_limits == (0, 40)
    assert plot.y_ticks == pytest.approx([0, 5, 10, 15, 20, 25, 30, 35, 40])


def test_half_automatic_x_limit_matches_criterion_8():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.x_max_edit.setText("8 s")  # x min left blank
    dlg.accept()

    assert "xlim auto to 8 s" in region.source
    plot = region.result.plot
    assert plot.x_limits == (0, 8)
    assert plot.x_ticks == pytest.approx([0, 1, 2, 3, 4, 5, 6, 7, 8])


def test_both_limit_boxes_blank_omits_the_xlim_line():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t")
    text = compile_plot_fields(fields)
    assert "xlim" not in text and "ylim" not in text


def test_xunit_field_matches_criterion_2_conversion():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.x_unit_edit.setText("ms")
    dlg.accept()

    assert "xunit ms" in region.source
    plot = region.result.plot
    assert plot.x_unit == "ms"
    assert plot.traces[0].x == pytest.approx([0, 2000, 4000, 6000, 8000, 10000])
    assert plot.x_label == "t [ms]"

    # clearing it back to blank removes the xunit line (re-opening the dialog on the saved text)
    dlg2 = PlotDialog(region, sheet)
    assert dlg2.x_unit_edit.text() == "ms"
    dlg2.x_unit_edit.setText("")
    dlg2.accept()
    assert "xunit" not in region.source


def test_title_field_only_adds_title_line_criterion_14():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.title_edit.setText("Speed")
    dlg.accept()

    assert region.source == "plot\nover t\nshow v*t\ntitle Speed"
    assert region.result.plot.title == "Speed"


def test_title_xlabel_ylabel_all_blank_omits_all_three_lines():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t")
    text = compile_plot_fields(fields)
    assert "title" not in text and "xlabel" not in text and "ylabel" not in text


def test_decompose_tolerates_any_line_order_but_compile_is_canonical():
    """The spec: decomposing does not require a fixed line order (only compiling does)."""
    scrambled = ("plot\nylabel Y\nover t\ntitle T\nshow v*t\nxunit ms\nxlabel X\nyunit mm\n"
                 "xlim 2 s to 8 s\nylim 0 m to 40 m")
    fields = decompose_plot_text(scrambled)
    assert fields is not None
    canonical = compile_plot_fields(fields)
    assert canonical.splitlines() == [
        "plot", "over t", "show v*t", "xunit ms", "yunit mm",
        "xlim 2 s to 8 s", "ylim 0 m to 40 m", "title T", "xlabel X", "ylabel Y",
    ]


# ===========================================================================
# OK / Cancel / Apply (criteria 15-18)
# ===========================================================================

def test_apply_updates_region_live_while_dialog_stays_open_criterion_15():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.apply_btn.click()

    assert region.result is not None and region.result.plot is not None
    assert region.result.plot.traces[0].y == pytest.approx([0, 6, 12, 18, 24, 30])
    assert dlg.result() == 0  # neither accepted nor rejected: still logically open


def test_ok_after_apply_makes_no_further_change_criterion_15():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.apply_btn.click()
    source_after_apply = region.source
    plot_after_apply = region.result.plot

    dlg.ok_btn.click()  # no field changed since Apply

    assert region.source == source_after_apply
    assert region.result.plot.traces[0].y == pytest.approx(plot_after_apply.traces[0].y)
    assert dlg.result() == QDialog.DialogCode.Accepted


def test_cancel_on_brand_new_region_discards_it_even_after_a_successful_apply_criterion_16():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("1")
    dlg.apply_btn.click()
    assert region.result is not None and region.result.status == "ok"

    dlg.cancel_btn.click()

    assert region not in sheet.regions()
    assert all(rd.kind != "plot" for rd in sheet.to_document().regions)


def test_cancel_on_existing_saved_plot_reverts_text_after_changes_and_apply_criterion_17():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    saved_before = sheet.to_document().regions[-1].text
    assert saved_before == PLOT_1

    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("2*v*t")
    dlg.y_min_edit.setText("0 m")
    dlg.apply_btn.click()
    assert region.source != PLOT_1  # the session did change the region in between

    dlg.cancel_btn.click()

    assert region.source == PLOT_1
    assert region in sheet.regions()
    assert sheet.to_document().regions[-1].text == PLOT_1


def test_ok_has_same_net_effect_as_apply_then_ok_criterion_18():
    def _run(use_apply_first: bool) -> tuple[str, list[float]]:
        sheet = _sheet_with(*SHEET_1)
        region = sheet.add_region("plot", QPointF(0, 200), "")
        sheet.recalculate()
        dlg = PlotDialog(region, sheet)
        dlg.var_existing_edit.setText("t")
        dlg._rows[0]["edit"].set_full_text("v*t")
        if use_apply_first:
            dlg.apply_btn.click()
        dlg.ok_btn.click()
        return region.source, list(region.result.plot.traces[0].y)

    source_direct, y_direct = _run(use_apply_first=False)
    source_via_apply, y_via_apply = _run(use_apply_first=True)
    assert source_direct == source_via_apply
    assert y_direct == pytest.approx(y_via_apply)


# ===========================================================================
# Errors (criteria 19-23) plus the accepted attribute_error() gap (manager note 2)
# ===========================================================================

def test_undefined_function_row_error_exact_wording_criterion_19():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    before = region.source
    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("Y")

    dlg.ok_btn.click()

    assert dlg.result() == 0  # dialog stayed open
    assert dlg._rows[0]["error"].text() == "Y is not defined"
    assert region.source == before


def test_different_units_two_rows_shows_banner_not_a_row_criterion_20():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg._add_row("t")

    dlg.apply_btn.click()

    assert "different units" in dlg.banner_label.text()
    assert dlg._rows[0]["error"].text() == "" and dlg._rows[1]["error"].text() == ""
    assert region.source == ""  # the failed Apply never wrote the bad text


def test_variable_required_message_without_any_engine_call_criterion_21():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("1")  # Function(s) filled, Variable(s) left blank

    dlg.ok_btn.click()

    assert dlg.variable_error_label.text() == "Variable(s) is required"
    assert region.source == ""  # proves the engine's own 'over'-missing error was never produced


def test_x_min_wrong_unit_attributes_to_xlim_field_criterion_22():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.x_min_edit.setText("5 m")  # sheet 1's x axis is seconds

    dlg.apply_btn.click()

    assert "Units do not match" in dlg.xlim_error_label.text()
    assert dlg.banner_label.text() == ""


def test_x_and_y_both_wrong_unit_falls_back_to_banner_accepted_gap():
    """Manager-accepted gap (spec open question 5): when BOTH axes' limit fields are filled and
    the engine's own message doesn't name an axis, attribute_error() cannot tell which one is at
    fault and falls back to the dialog-wide banner. Documented here as expected, not a defect."""
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.x_min_edit.setText("5 m")   # wrong unit, x axis is seconds
    dlg.y_min_edit.setText("2 kg")  # wrong unit too, y axis is metres

    dlg.apply_btn.click()

    assert dlg.xlim_error_label.text() == ""
    assert dlg.ylim_error_label.text() == ""
    assert "Units do not match" in dlg.banner_label.text()


def test_min_above_max_caught_locally_no_engine_call_criterion_23():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("1")
    dlg.x_min_edit.setText("8 s")
    dlg.x_max_edit.setText("2 s")

    dlg.ok_btn.click()

    assert dlg.xlim_error_label.text() == "lower limit must be below upper limit"
    assert region.source == ""  # the dialog's own check, no engine call


def test_y_min_above_y_max_also_caught_locally():
    """Same local check on the other axis, not covered by criterion 23's X-only example."""
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("1")
    dlg.y_min_edit.setText("40 m")
    dlg.y_max_edit.setText("0 m")

    dlg.ok_btn.click()

    assert dlg.ylim_error_label.text() == "lower limit must be below upper limit"


def test_points_out_of_range_dialog_side_check_exact_wording():
    """Developer/manager note 1: the dialog itself checks points (not deferred to the engine)."""
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.var_mode_combo.setCurrentIndex(1)
    dlg.var_sample_name_edit.setText("x")
    dlg.var_sample_from_edit.setText("0")
    dlg.var_sample_to_edit.setText("1")
    dlg.var_sample_points_edit.setText("10001")
    dlg._rows[0]["edit"].set_full_text("x")

    dlg.ok_btn.click()

    assert dlg.variable_error_label.text() == "points must be between 2 and 10000"
    assert region.source == ""  # engine never actually called


def test_non_integer_points_also_caught_dialog_side():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.var_mode_combo.setCurrentIndex(1)
    dlg.var_sample_name_edit.setText("x")
    dlg.var_sample_from_edit.setText("0")
    dlg.var_sample_to_edit.setText("1")
    dlg.var_sample_points_edit.setText("3.5")
    dlg._rows[0]["edit"].set_full_text("x")

    ok = dlg._commit()

    assert not ok
    assert dlg.variable_error_label.text() == "points must be between 2 and 10000"


# ===========================================================================
# Raw-text fallback (criteria 24-25)
# ===========================================================================

def test_edit_as_text_on_brand_new_region_uses_starter_text_criterion_24():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")
    dlg = PlotDialog(region, sheet)
    dlg.edit_text_btn.click()

    assert region.source == STARTER_TEXT
    assert region.editing


def test_edit_as_text_on_filled_region_uses_current_compiled_text_criterion_24():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("2*v*t")  # changed, not yet Applied

    dlg.edit_text_btn.click()

    assert region.source == "plot\nover t\nshow 2*v*t"
    assert region.editing


def test_use_dialog_round_trip_from_raw_editor_when_representable_criterion_25():
    import unittest.mock as mock

    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    region.start_editing()
    assert region._use_dialog_btn.isEnabled()

    opened = []
    with mock.patch.object(PlotDialog, "exec", lambda self: opened.append(self)):
        region._use_dialog_btn.click()

    # the raw editor closed and the dialog opened, pre-filled as a double-click would
    assert not region.editing
    assert len(opened) == 1
    dlg = opened[0]
    assert dlg.region is region
    assert dlg.var_existing_edit.text() == "t"
    assert [row["edit"].full_text() for row in dlg._rows] == ["v*t"]


def test_use_dialog_control_unavailable_when_not_representable_criterion_25():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), PLOT_1)
    region.start_editing()
    assert region._use_dialog_btn.isEnabled()

    region.editor.setPlainText("plot\nover t\nshow t\nxscale log")

    assert not region._use_dialog_btn.isEnabled()
    assert region._use_dialog_btn.toolTip() != ""  # a short note explaining why


# ===========================================================================
# Edge cases as acceptance criteria (26-28)
# ===========================================================================

def test_switching_variable_mode_revalidates_row_shape_on_next_ok_criterion_26():
    """Spec 004 criterion 5's vector sheet, pre-filled as vector mode with 'show Y' (a vector);
    switching Variable(s) to a range variable makes 'Y' the wrong shape and must surface the
    engine's own 'needs a single value' message at that row on the next OK/Apply, not silently."""
    sheet = _sheet_with("X := [0, 1, 2, 3]", "Y := [0, 1, 4, 9]*m", "t := 0 s to 3 s step 1 s")
    region = sheet.add_region("plot", QPointF(0, 200), "plot\nover X\nshow Y")
    sheet.recalculate()
    assert region.result.status == "ok"
    before_source = region.source

    dlg = PlotDialog(region, sheet)
    assert dlg.var_existing_edit.text() == "X"
    assert dlg._rows[0]["edit"].full_text() == "Y"
    dlg.var_existing_edit.setText("t")  # switch to a range variable; row left as "Y"

    ok = dlg._commit()

    assert not ok
    assert dlg._rows[0]["error"].text() == "show 'Y' needs a single value"
    assert region.source == before_source  # the bad attempt is not written


def test_switching_variable_mode_other_direction_needs_a_vector():
    """The opposite shape mismatch: range mode with a row that is a plain constant, switched to
    vector mode (spec 004 criterion 15's 'vector mode with show 5 -> needs a vector')."""
    sheet = _sheet_with("X := [0, 1, 2, 3]", "t := 0 s to 3 s step 1 s")
    region = sheet.add_region("plot", QPointF(0, 200), "plot\nover t\nshow 5")
    sheet.recalculate()
    assert region.result.status == "ok"

    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("X")  # switch to the vector; row stays "5" (a plain constant)

    ok = dlg._commit()

    assert not ok
    assert "needs a vector" in dlg._rows[0]["error"].text()


def test_function_row_elides_when_unfocused_and_restores_on_focus_criterion_27():
    long_text = "a_very_long_expression_that_does_not_fit_in_the_row_at_all_once_typed_out"
    edit = _FunctionEdit(long_text)
    edit.resize(80, 24)
    edit.show()

    assert edit.full_text() == long_text
    assert edit.text() != long_text  # elided while not focused, never wrapped to a 2nd line

    edit.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
    assert edit.text() == long_text  # full text shown while being edited

    edit.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert edit.text() != long_text  # elided again once focus is lost
    assert edit.full_text() == long_text  # the underlying value itself was never truncated


def test_ok_with_empty_function_list_on_brand_new_region_discards_it_criterion_28():
    sheet = _sheet()
    region = sheet.add_region("plot", QPointF(0, 0), "")  # brand new, nothing applied yet
    dlg = PlotDialog(region, sheet)
    assert [row["edit"].full_text() for row in dlg._rows] == [""]  # the default blank row

    dlg.ok_btn.click()

    assert region not in sheet.regions()  # same discard behaviour as Cancel (criterion 16)
    assert dlg.result() == QDialog.DialogCode.Rejected


def test_ok_with_empty_function_list_on_existing_region_is_refused_criterion_28():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)  # previously-saved, valid plot
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg._remove_row(dlg._rows[0])
    assert dlg._rows == []

    dlg.ok_btn.click()

    assert dlg.functions_error_label.text() == "At least one function is required"
    assert region in sheet.regions()
    assert region.source == PLOT_1  # left exactly as it was


def test_ok_with_all_rows_blank_but_not_removed_on_existing_region_also_refused():
    """Criterion 28's 'no rows, OR ALL ROWS BLANK' phrasing: a present-but-empty row must behave
    the same as zero rows."""
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg._rows[0]["edit"].set_full_text("")  # blanked, not removed

    dlg.apply_btn.click()

    assert dlg.functions_error_label.text() == "At least one function is required"
    assert region.source == PLOT_1


# ===========================================================================
# Save/reload and regression (criteria 29-31)
# ===========================================================================

def test_save_reload_roundtrip_for_a_dialog_created_plot_criterion_29(tmp_path):
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.accept()
    region.set_size(440, 300)

    doc = sheet.to_document()
    path = tmp_path / "dialog_plot.lsheet"
    doc.save(path)
    reloaded_doc = SheetDocument.load(path)

    plot_rd = next(r for r in reloaded_doc.regions if r.kind == "plot")
    assert plot_rd.text == "plot\nover t\nshow v*t"
    assert (plot_rd.w, plot_rd.h) == (440.0, 300.0)

    reloaded_sheet = _sheet()
    reloaded_sheet.load_document(reloaded_doc)
    reloaded_region = next(r for r in reloaded_sheet.regions() if isinstance(r, PlotRegion))
    assert reloaded_region.source == "plot\nover t\nshow v*t"
    # which surface it opens into next is re-derived from the text, not stored:
    assert decompose_plot_text(reloaded_region.source) is not None
    dlg2 = PlotDialog(reloaded_region, reloaded_sheet)
    assert dlg2.var_existing_edit.text() == "t"


def test_resize_move_select_delete_unaffected_for_dialog_created_plot_criterion_30():
    sheet = _sheet_with(*SHEET_1)
    region = sheet.add_region("plot", QPointF(0, 200), "")
    sheet.recalculate()
    dlg = PlotDialog(region, sheet)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.accept()

    region.set_size(50, 50)  # below the minimum, must clamp like any other plot region
    assert (region.size_w, region.size_h) >= (200.0, 140.0)

    region.setPos(QPointF(120, 360))
    assert (region.pos().x(), region.pos().y()) == (120.0, 360.0)

    region.setSelected(True)
    sheet.remove_regions([region])
    assert region not in sheet.regions()
    assert all(r.kind != "plot" for r in sheet.to_document().regions)


def test_pdf_export_from_dialog_path_matches_raw_text_path_criterion_31(tmp_path):
    sheet_dialog = _sheet_with(*SHEET_1)
    region = sheet_dialog.add_region("plot", QPointF(0, 200), "")
    sheet_dialog.recalculate()
    dlg = PlotDialog(region, sheet_dialog)
    dlg.var_existing_edit.setText("t")
    dlg._rows[0]["edit"].set_full_text("v*t")
    dlg.accept()
    sheet_dialog.recalculate()

    sheet_raw = _sheet_with(*SHEET_1)
    sheet_raw.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet_raw.recalculate()

    path_dialog = tmp_path / "dialog.pdf"
    path_raw = tmp_path / "raw.pdf"
    export_pdf(sheet_dialog, str(path_dialog))
    export_pdf(sheet_raw, str(path_raw))
    bytes_dialog = path_dialog.read_bytes()
    bytes_raw = path_raw.read_bytes()

    assert bytes_dialog.startswith(b"%PDF") and bytes_raw.startswith(b"%PDF")
    assert len(bytes_dialog) == len(bytes_raw)
    # The only expected difference between the two exports is Qt's own randomly generated
    # per-export PDF /DocumentID metadata (confirmed by inspection); the drawn content itself
    # (axes, ticks, trace) must be byte-identical. A handful of differing bytes clustered in one
    # small region is consistent with that metadata; a large or scattered diff would mean the
    # dialog path produced visibly different output.
    diffs = sum(1 for a, b in zip(bytes_dialog, bytes_raw) if a != b)
    assert diffs < 200


def test_pdf_export_never_draws_the_dialog_itself():
    """The dialog is a separate top-level widget (spec, 'Fits current architecture?'); exporting
    while a PlotDialog instance exists (but is not shown/exec'd) must not change the export."""
    sheet = _sheet_with(*SHEET_1)
    sheet.add_region("plot", QPointF(0, 200), PLOT_1)
    sheet.recalculate()
    region = next(r for r in sheet.regions() if isinstance(r, PlotRegion))

    import tempfile as _tmp

    without = _tmp.mktemp(suffix=".pdf")
    export_pdf(sheet, without)
    bytes_without_dialog_open = open(without, "rb").read()

    dlg = PlotDialog(region, sheet)  # constructed, never exec()'d/shown

    with_dialog = _tmp.mktemp(suffix=".pdf")
    export_pdf(sheet, with_dialog)
    bytes_with_dialog_constructed = open(with_dialog, "rb").read()

    os.remove(without)
    os.remove(with_dialog)
    assert len(bytes_without_dialog_open) == len(bytes_with_dialog_constructed)
    del dlg


# ===========================================================================
# attribute_error(): a few independent single-axis / single-row sanity checks
# (the ambiguous-both-axes case is covered above as an accepted gap, not here)
# ===========================================================================

def test_attribute_error_single_row_undefined_name():
    fields = PlotFields(functions=["Z"], var_mode="existing", var_name="t")
    assert attribute_error("Z is not defined", fields) == ("function", 0)


def test_attribute_error_xunit_message_routes_to_xunit_not_banner():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t", x_unit="s")
    assert attribute_error("xunit given but x has no unit", fields) == "xunit"


def test_attribute_error_unrelated_message_is_banner_not_misattributed():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t")
    assert attribute_error("no finite values to plot", fields) is None


def test_attribute_error_single_axis_ylim_message_routes_correctly():
    fields = PlotFields(functions=["t"], var_mode="existing", var_name="t", y_max="999 kg")
    assert attribute_error("Units do not match: limit is kg", fields) == "ylim"
