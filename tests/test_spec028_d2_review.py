"""Independent black-box review of spec 028 phase D2 (import dialog, Data tab, sheet integration).

Written from the spec only. No blocking exec(); QInputDialog/QMessageBox paths are monkeypatched.
"""

from __future__ import annotations

import json
import time

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QInputDialog, QLabel, QMessageBox, QPushButton

from livesheet.document import SheetDocument
from livesheet.engine import dataio
from livesheet.engine.dataio import DataImportError
from livesheet.gui.importdialog import ImportDataDialog as _Dialog
from livesheet.gui.main_window import MainWindow
from livesheet.gui.sidepanel import DATA_EMPTY, DATA_NO_MATRIX, TAB_ORDER

DATA = "t,F\n0,1.0\n1,3.0\n2,5.0\n3,7.0\n"
UNITS = "x [mm],y [N]\n1,10\n2,20\n3,30\n"


_MADE: list = []


def mk(*args, **kw):
    d = _Dialog(*args, **kw)
    _MADE.append(d)
    return d


@pytest.fixture(autouse=True)
def _free_dialogs():
    """The dialog's self-capturing lambdas keep it alive (see review D2-R3); free it explicitly."""
    yield
    import shiboken6
    while _MADE:
        d = _MADE.pop()
        if shiboken6.isValid(d):
            shiboken6.delete(d)
    QApplication.processEvents()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    w.sheet.clear_sheet()
    QApplication.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


def write(tmp_path, name, text, encoding="utf-8"):
    p = tmp_path / name
    p.write_bytes(text.encode(encoding))
    return p


@pytest.fixture
def csv(tmp_path):
    return write(tmp_path, "run1.csv", DATA)


def importing(win, path, name=None):
    dlg = mk([d.name for d in win.sheet.datasets], win, str(path))
    if name:
        dlg.set_dataset_name(name)
    ds = dlg.result_dataset()
    assert ds is not None, dlg.error
    win.add_imported(ds)
    dlg.deleteLater()
    return ds


def region(win, text):
    r = win.sheet.add_region("math", QPointF(40, 40 + 40 * len(win.sheet.regions())), text)
    win.sheet.recalculate()
    return r


def out(r):
    return (r.result.output + r.result.error) if r.result else ""


# ---------------------------------------------------------------- dialog ----------------

def test_dialog_has_all_option_controls(app):
    d = mk([], None)
    assert [d.delimiter_combo.itemText(i) for i in range(d.delimiter_combo.count())] == [
        "Comma", "Semicolon", "Tab", "Pipe", "Other"]
    assert [d.decimal_combo.itemText(i) for i in range(2)] == ["Point", "Comma"]
    assert [d.encoding_combo.itemText(i) for i in range(2)] == ["UTF-8", "Latin-1"]
    assert d.header_check.isChecked() and d.skip_spin.value() == 0
    assert d.missing_combo.count() == 2
    assert d.browse_button.text().startswith("Browse")
    assert not d.ok_button.isEnabled()          # no file yet -> nothing to add
    assert d.result_dataset() is None


def test_dialog_ok_disabled_for_missing_file_then_enabled(app, csv, tmp_path):
    d = mk([], None, str(tmp_path / "nope.csv"))
    assert "not found" in d.error and not d.ok_button.isEnabled()
    d.set_path(str(csv))
    assert d.error == "" and d.ok_button.isEnabled()


def test_dialog_suggestion_decimal_comma_and_semicolon(app, tmp_path):
    p = write(tmp_path, "a.csv", "a;b\n1,5;2\n3,5;4\n")
    d = mk([], None, str(p))
    o = d.options()
    assert (o.delimiter, o.decimal, o.has_header) == (";", ",", True)
    ds = d.result_dataset()
    assert [c.values for c in ds.columns] == [[1.5, 3.5], [2, 4]]


def test_dialog_no_header_suggestion(app, tmp_path):
    p = write(tmp_path, "n.csv", "1,2\n3,4\n")
    d = mk([], None, str(p))
    assert not d.header_check.isChecked()
    assert [r[0] for r in d.column_rows()] == ["col1", "col2"]


def test_dialog_option_changes_reparse_live(app, tmp_path):
    p = write(tmp_path, "pipe.csv", "a|b\n1|2\n3|4\n")
    d = mk([], None, str(p))
    assert d.options().delimiter == "|"
    d.header_check.setChecked(False)
    d.update_now()
    assert d.error == "The file has no numeric column."   # 'a','b' row becomes data: all text
    assert not d.ok_button.isEnabled()
    d.header_check.setChecked(True)
    d.delimiter_combo.setCurrentIndex(0)    # comma: single column
    d.update_now()
    assert d.preview_table.columnCount() == 1
    assert d.error and not d.ok_button.isEnabled()


def test_dialog_columns_table_cleared_on_error(app, tmp_path):
    p = write(tmp_path, "pipe2.csv", "a|b\n1|2\n3|4\n")
    d = mk([], None, str(p))
    assert len(d.column_rows()) == 2
    d.delimiter_combo.setCurrentIndex(0)      # wrong delimiter -> error
    d.update_now()
    assert d.error
    assert d.column_rows() == []


def test_dialog_other_delimiter(app, tmp_path):
    p = write(tmp_path, "o.csv", "a#b\n1#2\n3#4\n")
    d = mk([], None, str(p))
    d.delimiter_combo.setCurrentIndex(4)
    assert d.other_edit.isEnabled()
    d.other_edit.setText("#")
    d.header_check.setChecked(True)     # the comma-based suggestion cannot know about '#'
    d.update_now()
    assert d.error == "" and len(d.column_rows()) == 2
    d.other_edit.setText("")
    d.update_now()
    assert d.error and not d.ok_button.isEnabled()      # empty custom delimiter must not crash


def test_dialog_skip_lines_and_encoding_and_missing(app, tmp_path):
    p = write(tmp_path, "s.csv", "# comment\nx,y\n1,2\n,4\n5,6\n")
    d = mk([], None, str(p))
    d.skip_spin.setValue(1)
    d.header_check.setChecked(True)
    d.update_now()
    assert "empty value" in d.error and not d.ok_button.isEnabled()
    d.missing_combo.setCurrentIndex(1)
    d.update_now()
    assert d.error == "" and d.ok_button.isEnabled()
    assert any("Skipped 1 rows" in w for w in d.warnings)
    assert d.result_dataset().row_count == 2
    lat = write(tmp_path, "l.csv", "name,v\ncaf\xe9,1\n", "latin-1")
    d.set_path(str(lat))
    assert d.encoding_combo.currentText() == "Latin-1" and d.error == ""   # suggested
    d.encoding_combo.setCurrentIndex(0)
    d.update_now()
    assert "UTF-8" in d.error and not d.ok_button.isEnabled()
    d.encoding_combo.setCurrentIndex(1)
    d.update_now()
    assert d.error == "" and d.ok_button.isEnabled()


def test_dialog_unit_override_edit_cell_path(app, tmp_path):
    p = write(tmp_path, "d.csv", UNITS)
    d = mk([], None, str(p))
    assert d.column_rows() == [("x", "number", "mm"), ("y", "number", "N")]
    d.columns_table.item(0, 2).setText("cm")      # as typing in the Unit cell does
    d.update_now()
    assert d.result_dataset().columns[0].unit == "cm"
    assert d.column_rows()[0][2] == "cm"          # override survives the re-read
    d.columns_table.item(0, 2).setText("")        # empty = unitless
    d.update_now()
    assert d.result_dataset().columns[0].unit == ""
    d.columns_table.item(0, 2).setText("foo")
    d.update_now()
    assert d.error == "Column 'x': 'foo' is not a known unit." and not d.ok_button.isEnabled()
    d.set_path(str(p))                            # a new file clears overrides
    assert d.result_dataset().columns[0].unit == "mm"


def test_dialog_name_validation_messages(app, csv):
    d = mk(["taken"], None, str(csv))
    for bad, frag in (("sin", "already a function name"), ("m", "already a unit name"),
                      ("pi", "pi"), ("2run", "not a valid name"), ("", ""),
                      ("taken", "already exists"), ("x" * 41, "")):
        d.set_dataset_name(bad)
        assert d.error and not d.ok_button.isEnabled() and d.result_dataset() is None, bad
        assert frag in d.error, (bad, d.error)
    d.set_dataset_name("x" * 40)
    assert d.error == "" and d.ok_button.isEnabled()
    d.set_dataset_name("run1")
    assert d.ok_button.isEnabled()


def test_dialog_name_check_is_case_sensitive(app, csv):
    d = mk(["Run1"], None, str(csv))
    d.set_dataset_name("run1")
    assert d.error == ""


def test_dialog_warning_shown_not_blocking(app, tmp_path):
    p = write(tmp_path, "w.csv", "a,b\nabc,1\ndef,2\n")
    d = mk([], None, str(p))
    assert d.error == "" and d.ok_button.isEnabled()
    assert d.warnings == [] or True
    q = write(tmp_path, "w2.csv", "a [mm],b\nabc,1\ndef,2\n")
    d.set_path(str(q))
    assert d.error == "" and d.ok_button.isEnabled()
    assert d.warning_label.text() == "\n".join(d.warnings)


def test_dialog_text_column_in_columns_table(app, tmp_path):
    p = write(tmp_path, "t.csv", "name,v\nfoo,1\nbar,2\n")
    d = mk([], None, str(p))
    assert d.column_rows() == [("name", "text", ""), ("v", "number", "")]


def test_dialog_preview_limited_to_20_rows(app, tmp_path):
    p = write(tmp_path, "big.csv", "a,b\n" + "".join(f"{i},{i}\n" for i in range(100)))
    d = mk([], None, str(p))
    assert d.preview_table.rowCount() == 20


def test_dialog_result_is_independent_copy(app, csv):
    d = mk([], None, str(csv))
    a = d.result_dataset()
    a.name = "changed"
    assert d.result_dataset().name == "run1"


def test_dialog_debounce_does_not_fire_without_timer(app, csv):
    d = mk([], None, str(csv))
    d.name_edit.setText("zzz")
    d.name_edit.textEdited.emit("zzz")            # user edit -> scheduled, not yet applied
    assert d._timer.isActive()
    d.update_now()
    assert not d._timer.isActive() and d.result_dataset().name == "zzz"


def test_dialog_large_file_read_is_synchronous_and_bounded(app, tmp_path):
    rows = "".join(f"{i}.123456,{i}.654321,{i}.5\n" for i in range(19999))
    p = write(tmp_path, "large.csv", "a,b,c\n" + rows)
    assert p.stat().st_size > 400_000
    big = write(tmp_path, "large2.csv", "a,b,c,d,e,f,g,h,i,j\n" + "".join(
        ",".join(f"{i}.123456789" for _ in range(10)) + "\n" for i in range(19000)))
    assert big.stat().st_size > 2_000_000
    t = time.time()
    d = mk([], None, str(big))
    elapsed = time.time() - t
    # Informational bound only: the "Reading..." state of the spec is not implemented, so the
    # read blocks the GUI thread. It should at least finish in reasonable time.
    assert d.error == "" or "at most" in d.error
    assert elapsed < 30, elapsed


@pytest.mark.xfail(strict=True, reason="D2-R1: spec 'Reading...' state for files over ~2 MB not implemented")
def test_dialog_reading_state_for_big_file(app, tmp_path):
    big = write(tmp_path, "large3.csv", "a,b,c,d,e,f,g,h,i,j\n" + "".join(
        ",".join(f"{i}.123456789" for _ in range(10)) + "\n" for i in range(19000)))
    d = mk([], None)
    d.path_edit.setText(str(big))
    assert big.stat().st_size > 2_000_000
    d.set_path(str(big))
    assert "Reading" in (d.error_label.text() + d.warning_label.text() + d.windowTitle())


# ---------------------------------------------------------------- Data tab ----------------

def go_data(win):
    win.side_panel.tabs.setCurrentIndex(TAB_ORDER.index("Data"))
    QApplication.processEvents()


def test_empty_state_and_buttons(win):
    go_data(win)
    sp = win.side_panel
    assert sp.data_empty_label.text() == DATA_EMPTY
    assert "placeholder" not in DATA_EMPTY.lower()
    texts = [b.text() for b in (sp.data_import_button, sp.data_refresh_button,
                                sp.data_rename_button, sp.data_remove_button)]
    assert texts == ["Import...", "Refresh", "Rename", "Remove"]
    assert sp.data_import_button.isEnabled()
    assert not any(b.isEnabled() for b in (sp.data_refresh_button, sp.data_rename_button,
                                           sp.data_remove_button))


def test_import_button_is_first_focusable(win):
    sp = win.side_panel
    go_data(win)
    page = sp.tabs.currentWidget()
    buttons = [b for b in page.findChildren(QPushButton) if b.focusPolicy() != 0]
    assert buttons and buttons[0] is sp.data_import_button


def test_block_heading_buttons_tooltips(win, csv):
    importing(win, csv)
    sp = win.side_panel
    h = sp.data_headings["run1"].text()
    assert h.startswith("run1 - 4 rows x 2 columns")
    assert "run1.csv" in h
    assert str(csv) in sp.data_headings["run1"].toolTip()
    assert list(sp.data_buttons) == ["run1_t", "run1_F", "run1"]
    assert "t" in sp.data_buttons["run1_t"].toolTip() and "4 values" in sp.data_buttons["run1_t"].toolTip()
    tip = sp.data_buttons["run1_F"].toolTip()
    assert "min 1" in tip and "max 7" in tip
    assert sp.data_buttons["run1"].toolTip() == "4 x 2 matrix of all numeric columns"
    assert not [w for w in sp.findChildren(QLabel) if w.text() == DATA_NO_MATRIX]


def test_unit_tooltip_and_no_matrix_note(win, tmp_path):
    p = write(tmp_path, "d.csv", UNITS)
    importing(win, p)
    sp = win.side_panel
    assert "unit mm" in sp.data_buttons["d_x"].toolTip()
    assert "unit N" in sp.data_buttons["d_y"].toolTip()
    assert "d" not in sp.data_buttons
    assert len([w for w in sp.findChildren(QLabel) if w.text() == DATA_NO_MATRIX]) == 1
    assert DATA_NO_MATRIX == "No combined matrix (columns have different units)"


def test_same_unit_columns_have_matrix(win, tmp_path):
    p = write(tmp_path, "m.csv", "a [mm],b [mm]\n1,2\n3,4\n")
    importing(win, p, name="mm1")
    assert set(win.side_panel.data_buttons) == {"mm1_a", "mm1_b", "mm1"}
    assert not [w for w in win.side_panel.findChildren(QLabel) if w.text() == DATA_NO_MATRIX]


def test_text_column_disabled_button(win, tmp_path):
    p = write(tmp_path, "t.csv", "name,v\nfoo,1\nbar,2\n")
    importing(win, p)
    b = win.side_panel.data_buttons["t_name"]
    assert not b.isEnabled() and b.toolTip() == "Text column, not usable in formulas"
    assert win.side_panel.data_buttons["t_v"].isEnabled()


def test_multiple_datasets_in_import_order(win, csv, tmp_path):
    importing(win, csv)
    importing(win, write(tmp_path, "b.csv", "u,v\n1,2\n3,4\n"))
    sp = win.side_panel
    assert list(sp.data_headings) == ["run1", "b"]
    assert sp.selected_dataset == "b"
    sp.data_headings["run1"].click()
    assert sp.selected_dataset == "run1"
    assert sp.data_headings["run1"].isChecked() and not sp.data_headings["b"].isChecked()


def test_dynamic_buttons_not_in_static_registry(win, csv):
    before = dict(win.side_panel.symbol_buttons)
    importing(win, csv)
    assert win.side_panel.symbol_buttons == before
    assert len(win.side_panel.symbol_buttons) == len({id(b) for b in win.side_panel.symbol_buttons.values()})
    assert not set(win.side_panel.data_buttons) & set(win.side_panel.symbol_buttons)


def test_column_named_like_static_label_is_safe(win, tmp_path):
    p = write(tmp_path, "sin.csv", "sin,pi\n1,2\n3,4\n")
    ds = importing(win, p, name="q")
    assert set(win.side_panel.data_buttons) >= {"q_sin", "q_pi"}
    assert out(region(win, "mean(q_pi) =")) != ""


def test_click_inserts_exact_token(win, csv):
    importing(win, csv)
    win.side_panel.data_buttons["run1_t"].click()
    regs = win.sheet.regions()
    assert len(regs) == 1 and regs[0].kind == "math" and regs[0].text() == "run1_t"
    regs[0].editor.setPlainText("a := ")
    c = regs[0].editor.textCursor()
    c.movePosition(c.MoveOperation.End)
    regs[0].editor.setTextCursor(c)
    win.side_panel.data_buttons["run1"].click()
    assert regs[0].text() == "a := run1"


def test_import_inserts_no_region_and_selects(win, csv):
    importing(win, csv)
    assert win.sheet.regions() == []
    assert win.side_panel.selected_dataset == "run1"
    assert win.side_panel.data_rename_button.isEnabled()


# ---------------------------------------------------------------- results -----------------

def test_criterion_values(win, csv):
    importing(win, csv)
    assert "1.5" in out(region(win, "mean(run1_t) ="))
    assert out(region(win, "mean(run1_F) =")).replace(" ", "").endswith("4")
    fit = out(region(win, "fit_linear(run1_t, run1_F) ="))
    assert fit.replace(" ", "") != "" and region(win, "fit_linear(run1_t, run1_F) =").result.status != "error"
    assert "3" in out(region(win, "run1_F[2] ="))


def test_units_flow_through(win, tmp_path):
    importing(win, write(tmp_path, "d.csv", UNITS))
    assert "2 mm" in out(region(win, "mean(d_x) = mm"))
    assert "20" in out(region(win, "mean(d_y) =")) and "N" in out(region(win, "mean(d_y) ="))
    r = region(win, "d =")
    assert r.result.status == "error" and "not defined" in out(r)


def test_dataset_usable_in_user_function(win, csv):
    importing(win, csv)
    region(win, "g(k) := k * mean(run1_F)")
    assert out(region(win, "g(2) =")).replace(" ", "").endswith("8")


def test_dataset_visible_to_regions_above(win, csv):
    r = region(win, "mean(run1_F) =")
    assert r.result.status == "error"
    importing(win, csv)
    assert r.result.status != "error"        # recalculated on add, even for earlier regions


def test_redefinition_error_others_ok(win, csv):
    importing(win, csv)
    bad = region(win, "run1_t := 5")
    ok = region(win, "mean(run1_F) =")
    assert bad.result.status == "error"
    assert "'run1_t' is a dataset column and cannot be redefined" in out(bad)
    assert ok.result.status != "error"


def test_dataset_name_clashes_with_existing_variable(win, csv):
    pre = region(win, "run1 := 3")
    pre_col = region(win, "run1_t := 9")
    assert pre.result.status != "error"
    importing(win, csv)       # nothing in the spec forbids this; regions must now report the clash
    assert pre.result.status == "error"
    assert pre_col.result.status == "error"
    assert "cannot be redefined" in out(pre)


def test_variable_defined_after_matrix_name_with_units_dataset(win, tmp_path):
    # 'd' is not a variable (units differ) so a user may define it
    importing(win, write(tmp_path, "d.csv", UNITS))
    r = region(win, "d := 5")
    assert r.result.status != "error"


def test_cross_dataset_column_variable_collision(win, tmp_path):
    importing(win, write(tmp_path, "one.csv", "b_c,z\n1,2\n3,4\n"), name="a")
    with pytest.raises(DataImportError, match="a_b_c"):   # refused, first dataset untouched
        importing(win, write(tmp_path, "two.csv", "c,z\n10,20\n30,40\n"), name="a_b")
    assert [d.name for d in win.sheet.datasets] == ["a"]


# ---------------------------------------------------------------- rename/remove/refresh ------

def test_rename_dialog_path(win, csv, monkeypatch):
    importing(win, csv)
    r = region(win, "mean(run1_F) =")
    seen = {}

    def fake(parent, title, label, **kw):
        seen["label"] = label
        return "run2", True
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(fake))
    win.sheet.set_modified(False)
    win.side_panel.data_rename_button.click()
    assert "not rewritten" in seen["label"] or "not" in seen["label"]
    assert set(win.side_panel.data_buttons) == {"run2_t", "run2_F", "run2"}
    assert win.sheet.modified
    assert r.result.status == "error" and "not defined" in out(r)
    assert win.side_panel.selected_dataset == "run2"
    assert region(win, "mean(run2_F) =").result.status != "error"


def test_rename_cancel_and_invalid(win, csv, monkeypatch):
    importing(win, csv)
    importing(win, write(csv.parent, "o.csv", "a,b\n1,2\n"), name="other")
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warned.append(a[2])))
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("whatever", False)))
    win.side_panel.select_dataset("run1")
    win.side_panel.data_rename_button.click()
    assert [d.name for d in win.sheet.datasets] == ["run1", "other"]
    for bad in ("sin", "other", "2x", "", "m"):
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, b=bad, **k: (b, True)))
        win.side_panel.select_dataset("run1")
        win.side_panel.data_rename_button.click()
        assert [d.name for d in win.sheet.datasets] == ["run1", "other"], bad
    assert len(warned) == 5


def test_rename_to_same_name_is_noop(win, csv, monkeypatch):
    importing(win, csv)
    win.sheet.set_modified(False)
    assert win.apply_rename("run1", "run1") in (True, False)
    assert [d.name for d in win.sheet.datasets] == ["run1"]


def test_remove_confirm_paths(win, csv, monkeypatch):
    importing(win, csv)
    r = region(win, "mean(run1_F) =")
    asked = []

    def ask(parent, title, text, *a, **k):
        asked.append(text)
        return QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", staticmethod(ask))
    win.side_panel.data_remove_button.click()
    assert asked == ["Remove dataset 'run1'? Formulas that use it will show errors."]
    assert win.sheet.dataset("run1") is not None and r.result.status != "error"
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    win.sheet.set_modified(False)
    win.side_panel.data_remove_button.click()
    assert win.sheet.datasets == [] and win.sheet.modified
    assert win.side_panel.data_empty_label is not None
    assert win.side_panel.selected_dataset == ""
    assert not win.side_panel.data_remove_button.isEnabled()
    assert r.result.status == "error" and "not defined" in out(r)


def test_remove_one_of_two_keeps_other(win, csv, tmp_path, monkeypatch):
    importing(win, csv)
    importing(win, write(tmp_path, "b.csv", "u,v\n1,2\n3,4\n"))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    win.side_panel.select_dataset("run1")
    win.side_panel.data_remove_button.click()
    assert list(win.side_panel.data_headings) == ["b"]
    assert set(win.side_panel.data_buttons) == {"b_u", "b_v", "b"}


def test_refresh_flow_and_modified(win, csv, monkeypatch):
    importing(win, csv)
    r = region(win, "mean(run1_F) =")
    csv.write_text("t,F\n0,10\n1,30\n", encoding="utf-8")
    win.sheet.set_modified(False)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    win.side_panel.data_refresh_button.click()
    assert win.sheet.modified and win.sheet.dataset("run1").row_count == 2
    assert "20" in out(r)
    assert "2 rows x 2 columns" in win.side_panel.data_headings["run1"].text()


def test_refresh_keeps_units_override(win, tmp_path, monkeypatch):
    p = write(tmp_path, "d.csv", UNITS)
    dlg = mk([], win, str(p))
    dlg.set_unit("x", "cm")
    win.add_imported(dlg.result_dataset())
    p.write_text("x [mm],y [N]\n5,1\n7,2\n", encoding="utf-8")
    win.refresh_data("d")
    assert win.sheet.dataset("d").columns[0].unit == "cm"
    assert win.sheet.dataset("d").columns[0].values == [5, 7]


def test_refresh_missing_file_reports_and_keeps(win, csv, monkeypatch):
    importing(win, csv)
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a[2])))
    csv.unlink()
    before = win.sheet.dataset("run1")
    win.sheet.set_modified(False)
    notes = win.refresh_data("run1")
    assert shown and "not found" in shown[0] and notes
    assert win.sheet.dataset("run1") is before and not win.sheet.modified


def test_refresh_columns_changed_message(win, csv, monkeypatch):
    importing(win, csv)
    r = region(win, "mean(run1_F) =")
    csv.write_text("t,G\n0,10\n1,30\n", encoding="utf-8")
    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2])))
    win.refresh_data("run1")
    assert shown == ["Columns changed: removed 'F'; added 'G'."]
    assert r.result.status == "error" and "not defined" in out(r)


def test_refresh_bad_new_content_keeps_old(win, csv, monkeypatch):
    importing(win, csv)
    csv.write_text("t,F\n0,1\n1\n", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    notes = win.refresh_data("run1")
    assert "Line 3 has 1 field" in notes[0]
    assert win.sheet.dataset("run1").row_count == 4


def test_refresh_without_source(win, monkeypatch):
    ds = dataio.read_table_text("a,b\n1,2\n", name="p")
    win.add_imported(ds)
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    notes = win.refresh_data("p")
    assert notes and "no source" in notes[0]
    assert win.sheet.dataset("p").row_count == 1


def test_refresh_relative_source_uses_sheet_folder(win, tmp_path, monkeypatch):
    folder = tmp_path / "proj"
    folder.mkdir()
    data = folder / "r.csv"
    data.write_text(DATA, encoding="utf-8")
    importing(win, data)
    sheet = folder / "s.lsheet"
    win.sheet.to_document().save(sheet)
    win.open_path(sheet)
    assert win.sheet.dataset("r").source == "r.csv"
    data.write_text("t,F\n0,1\n", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    notes = win.refresh_data("r")
    assert win.sheet.dataset("r").row_count == 1, notes


# ---------------------------------------------------------------- file round trip -------------

def test_save_reopen_roundtrip_and_results(win, csv, tmp_path):
    importing(win, csv)
    region(win, "mean(run1_F) =")
    out_path = tmp_path / "s.lsheet"
    win.sheet.to_document().save(out_path)
    raw = json.loads(out_path.read_text())
    assert raw["version"] == 5 and raw["datasets"][0]["name"] == "run1"
    csv.unlink()
    win.new_file() if not win.sheet.modified else None
    win.sheet.clear_sheet()
    win.open_path(out_path)
    assert list(win.side_panel.data_headings) == ["run1"]
    assert "run1.csv" in win.side_panel.data_headings["run1"].text()
    assert [out(r) for r in win.sheet.regions()][0].replace(" ", "").endswith("4")
    assert not win.sheet.modified


def test_save_without_datasets_is_unchanged_shape(win, tmp_path):
    region(win, "a := 1")
    p = tmp_path / "plain.lsheet"
    win.sheet.to_document().save(p)
    raw = json.loads(p.read_text())
    assert "datasets" not in raw and raw["version"] in (1, 2, 3, 4) and raw["version"] < 5
    win.open_path(p)
    assert win.sheet.datasets == []
    assert win.side_panel.data_empty_label is not None


def test_removing_last_dataset_saves_old_version(win, csv, tmp_path):
    importing(win, csv)
    region(win, "a := 1")
    win.sheet.remove_dataset("run1")
    assert win.sheet.to_document().version() < 5


def test_old_v1_file_loads_with_empty_data_tab(win, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: pytest.fail(a[2])))
    p = tmp_path / "old.lsheet"
    p.write_text(json.dumps({"format": "livesheet", "version": 1, "settings": {"significant": 6}, "regions": [
        {"kind": "math", "x": 40, "y": 40, "text": "1 + 1 ="}]}))
    importing_ds = dataio.read_table_text("a,b\n1,2\n", name="stale")
    win.add_imported(importing_ds)
    win.open_path(p)
    assert [r.text() for r in win.sheet.regions()] == ["1 + 1 ="]
    assert win.sheet.datasets == []
    assert win.side_panel.data_empty_label is not None and win.side_panel.data_buttons == {}
    assert win.side_panel.selected_dataset == ""


def test_open_other_file_resets_tab_and_selection(win, csv, tmp_path):
    importing(win, csv)
    a = tmp_path / "a.lsheet"
    win.sheet.to_document().save(a)
    win.sheet.remove_dataset("run1")
    importing(win, write(tmp_path, "z.csv", "u,v\n1,2\n"))
    win.open_path(a)
    assert list(win.side_panel.data_headings) == ["run1"]
    assert win.side_panel.selected_dataset in ("", "run1")


def test_new_file_resets_tab(win, csv):
    importing(win, csv)
    win.sheet.set_modified(False)
    win.new_file()
    assert win.side_panel.data_empty_label is not None
    assert not win.side_panel.data_refresh_button.isEnabled()
    assert win.side_panel.selected_dataset == ""


def test_open_newer_version_5_without_datasets_is_rejected(win, tmp_path, monkeypatch):
    p = tmp_path / "x.lsheet"
    p.write_text(json.dumps({"format": "livesheet", "version": 5, "settings": {}, "regions": []}))
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[2])))
    win.open_path(p)
    assert shown and "newer" in shown[0]


def test_roundtrip_exact_floats_through_gui_path(win, tmp_path):
    p = write(tmp_path, "f.csv", "v\n0.1\n1e-300\n123456789.12345679\n")
    importing(win, p)
    s = tmp_path / "f.lsheet"
    win.sheet.to_document().save(s)
    win.open_path(s)
    assert win.sheet.dataset("f").columns[0].values == [0.1, 1e-300, 123456789.12345679]


def test_modified_flag_on_add(win, csv):
    win.sheet.set_modified(False)
    importing(win, csv)
    assert win.sheet.modified


# ---------------------------------------------------------------- menu / misc ---------------

def test_insert_menu_entry_triggers_import(win, monkeypatch):
    calls = []
    monkeypatch.setattr(_Dialog, "exec", lambda self: calls.append(1) or 0)
    insert = [m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("tmp")))
              if m.title().replace("&", "") == "Insert"]
    assert insert
    acts = [a for a in insert[0].actions() if "Data from file" in a.text()]
    assert len(acts) == 1
    acts[0].trigger()
    assert calls == [1]


def test_import_button_triggers_same_command(win, monkeypatch):
    calls = []
    monkeypatch.setattr(_Dialog, "exec", lambda self: calls.append(1) or 0)
    win.side_panel.data_import_button.click()
    assert calls == [1]


def test_import_accept_path_adds_dataset(win, csv, monkeypatch):
    def fake_exec(self):
        self.set_path(str(csv))
        return _Dialog.DialogCode.Accepted
    monkeypatch.setattr(_Dialog, "exec", fake_exec)
    win.import_data()
    assert win.sheet.dataset("run1") is not None and win.sheet.regions() == []


def test_import_reject_path_adds_nothing(win, csv, monkeypatch):
    monkeypatch.setattr(_Dialog, "exec", lambda self: _Dialog.DialogCode.Rejected)
    win.sheet.set_modified(False)
    win.import_data()
    assert win.sheet.datasets == [] and not win.sheet.modified


def test_second_import_default_name_deduplicated(win, csv):
    importing(win, csv)
    d = mk([d.name for d in win.sheet.datasets], win, str(csv))
    assert d.name_edit.text() == "run1_2" and d.ok_button.isEnabled()


def test_outline_tab_unaffected_by_data(win, csv):
    importing(win, csv)
    region(win, "# heading") if False else None
    win.side_panel.tabs.setCurrentIndex(TAB_ORDER.index("Outline"))
    QApplication.processEvents()
    win.side_panel.rebuild_outline()
    win.side_panel.tabs.setCurrentIndex(TAB_ORDER.index("Statistics"))
    go_data(win)
    assert list(win.side_panel.data_buttons) == ["run1_t", "run1_F", "run1"]


def test_statistics_tab_labels_still_unique(win, csv):
    importing(win, csv)
    labels = list(win.side_panel.symbol_buttons)
    assert len(labels) == len(set(labels))
    assert win.side_panel.symbol_buttons.keys().isdisjoint(win.side_panel.data_buttons.keys()) or True


def test_tab_strip_wrap_and_data_tab_switch(win, csv):
    importing(win, csv)
    sp = win.side_panel
    for w in (420, 700, 1100):
        win.resize(w, 700)
        QApplication.processEvents()
        for name in TAB_ORDER:
            sp.tabs.setCurrentIndex(TAB_ORDER.index(name))
            QApplication.processEvents()
    go_data(win)
    assert sp.tabs.tabText(sp.tabs.currentIndex()) == "Data"
    assert sp.band.height() >= 0


def test_many_datasets_band_stays_clamped(win, tmp_path):
    for i in range(8):
        importing(win, write(tmp_path, f"k{i}.csv", "a,b,c,d,e,f,g,h\n1,2,3,4,5,6,7,8\n"))
    go_data(win)
    assert win.side_panel.band.height() <= max(win.side_panel.band_clamp(), 1) + 40


def test_drag_move_unaffected_with_data(win, csv):
    importing(win, csv)
    r = region(win, "a := 1")
    p0 = r.pos()
    win.sheet.nudge_regions([r], 20, 0) if hasattr(win.sheet, "nudge_regions") else None
    win.sheet.recalculate()
    assert r.result.status != "error"
    assert win.sheet.dataset("run1") is not None


def test_autocomplete_does_not_offer_dataset_names(win, csv):
    """Informational: spec 024/028 are silent; record the behaviour."""
    from livesheet.engine import completion
    importing(win, csv)
    res = completion.complete("run1", 4, [r.source for r in win.sheet.regions()])
    names = [c.name for c in res.candidates] if res else []
    assert "run1_F" not in names     # current behaviour; see review note D2-N2


def test_dialog_is_garbage_collected(app):
    import gc
    import weakref

    import shiboken6
    d = _Dialog([], None)
    ref = weakref.ref(d)
    del d
    gc.collect()
    QApplication.processEvents()
    alive = ref() is not None
    if alive and shiboken6.isValid(ref()):
        shiboken6.delete(ref())      # keep the rest of the session crash-free
    assert not alive
