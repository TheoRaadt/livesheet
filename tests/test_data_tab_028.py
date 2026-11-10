"""Spec 028 phase D2: import dialog, Data tab, sheet integration (no blocking dialogs)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QLabel

from livesheet.document import DocumentError, SheetDocument
from livesheet.engine import dataio
from livesheet.engine.dataio import DataImportError
from livesheet.gui.importdialog import ImportDataDialog
from livesheet.gui.main_window import MainWindow
from livesheet.gui.sidepanel import DATA_EMPTY, DATA_NO_MATRIX, DATA_PLACEHOLDER

DATA = "t,F\n0,1.0\n1,3.0\n2,5.0\n3,7.0\n"


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


@pytest.fixture
def csv(tmp_path):
    p = tmp_path / "run1.csv"
    p.write_text(DATA, encoding="utf-8")
    return p


def import_run1(win, csv, **kw):
    dlg = ImportDataDialog([d.name for d in win.sheet.datasets], win, str(csv))
    ds = dlg.result_dataset()
    assert ds is not None, dlg.error
    win.add_imported(ds)
    dlg.deleteLater()
    return ds


def result_of(win, text):
    r = win.sheet.add_region("math", QPointF(40, 40 + 40 * len(win.sheet.regions())), text)
    win.sheet.recalculate()
    return r.result


# -- dialog -----------------------------------------------------------------------

def test_dialog_suggests_and_previews(app, csv):
    dlg = ImportDataDialog([], None, str(csv))
    assert dlg.name_edit.text() == "run1"
    assert dlg.options().delimiter == "," and dlg.options().has_header
    assert dlg.preview_table.rowCount() == 5
    assert dlg.column_rows() == [("t", "number", ""), ("F", "number", "")]
    assert dlg.error == "" and dlg.ok_button.isEnabled()
    ds = dlg.result_dataset()
    assert ds.name == "run1" and ds.row_count == 4
    dlg.deleteLater()


def test_dialog_ok_disabled_on_errors(app, csv, tmp_path):
    dlg = ImportDataDialog(["run1"], None, str(csv))
    assert dlg.name_edit.text() == "run1_2"   # de-duplicated default
    dlg.set_dataset_name("run1")
    assert "already exists" in dlg.error and not dlg.ok_button.isEnabled()
    assert dlg.result_dataset() is None
    dlg.set_dataset_name("sin")
    assert "function" in dlg.error and not dlg.ok_button.isEnabled()
    dlg.set_dataset_name("good")
    assert dlg.error == "" and dlg.ok_button.isEnabled()
    dlg.set_path(str(tmp_path / "missing.csv"))
    assert "not found" in dlg.error and not dlg.ok_button.isEnabled()
    dlg.deleteLater()


def test_dialog_unit_override_and_bad_unit(app, tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("x [mm],y [N]\n1,10\n2,20\n", encoding="utf-8")
    dlg = ImportDataDialog([], None, str(p))
    assert dlg.column_rows()[0] == ("x", "number", "mm")
    dlg.set_unit("x", "cm")
    assert dlg.result_dataset().columns[0].unit == "cm"
    dlg.set_unit("x", "foo")
    assert "not a known unit" in dlg.error and not dlg.ok_button.isEnabled()
    dlg.deleteLater()


def test_dialog_options_change_reparse(app, tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("a;b\n1,5;2\n3,5;4\n", encoding="utf-8")
    dlg = ImportDataDialog([], None, str(p))
    assert dlg.options().delimiter == ";" and dlg.options().decimal == ","
    dlg.decimal_combo.setCurrentIndex(0)
    dlg.update_now()
    assert dlg.column_rows()[0][1] == "text"
    assert any("read as text" in w for w in dlg.warnings)
    dlg.deleteLater()


# -- sheet integration -----------------------------------------------------------------

def test_data_tab_empty_state(win):
    sp = win.side_panel
    assert DATA_EMPTY == sp.data_empty_label.text()
    assert sp.data_import_button.isEnabled() and not sp.data_refresh_button.isEnabled()
    assert DATA_PLACEHOLDER == DATA_EMPTY


def test_import_builds_buttons_and_marks_modified(win, csv):
    win.sheet.set_modified(False)
    import_run1(win, csv)
    sp = win.side_panel
    assert win.sheet.modified
    assert set(sp.data_buttons) == {"run1_t", "run1_F", "run1"}
    assert sp.data_empty_label is None
    assert "run1 - 4 rows x 2 columns" in sp.data_headings["run1"].text()
    assert sp.selected_dataset == "run1" and sp.data_refresh_button.isEnabled()
    assert not (set(sp.data_buttons) & set(sp.symbol_buttons))
    assert win.sheet.regions() == []   # import inserts no region


def test_click_column_inserts_token(win, csv):
    import_run1(win, csv)
    win.side_panel.data_buttons["run1_F"].click()
    regions = win.sheet.regions()
    assert len(regions) == 1 and regions[0].text() == "run1_F"
    regions[0].editor.setPlainText("a := ")
    c = regions[0].editor.textCursor()
    c.movePosition(c.MoveOperation.End)
    regions[0].editor.setTextCursor(c)
    win.side_panel.data_buttons["run1_F"].click()
    assert regions[0].text() == "a := run1_F"


def test_results_use_datasets(win, csv):
    import_run1(win, csv)
    assert result_of(win, "mean(run1_F) =").status != "error"
    assert "4" in result_of(win, "mean(run1_F) =").output
    assert result_of(win, "run1_t := 5").status == "error"


def test_no_combined_matrix_note(win, tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("x [mm],y [N]\n1,10\n2,20\n", encoding="utf-8")
    import_run1(win, p)
    sp = win.side_panel
    assert set(sp.data_buttons) == {"d_x", "d_y"}
    assert any(isinstance(w, QLabel) and w.text() == DATA_NO_MATRIX for w in sp.findChildren(QLabel))


def test_refresh_updates_and_failure_keeps(win, csv):
    import_run1(win, csv)
    csv.write_text("t,F\n0,10\n1,30\n", encoding="utf-8")
    notes = win.sheet.refresh_dataset("run1")
    assert notes == [] and win.sheet.dataset("run1").row_count == 2
    csv.write_text("t,G\n0,10\n1,30\n", encoding="utf-8")
    notes = win.sheet.refresh_dataset("run1")
    assert any("removed 'F'" in n and "added 'G'" in n for n in notes)
    assert set(win.side_panel.data_buttons) == {"run1_t", "run1_G", "run1"}
    csv.unlink()
    before = win.sheet.dataset("run1")
    with pytest.raises(DataImportError, match="not found"):
        win.sheet.refresh_dataset("run1")
    assert win.sheet.dataset("run1") is before


def test_rename_and_remove(win, csv):
    import_run1(win, csv)
    r = win.sheet.add_region("math", QPointF(40, 40), "mean(run1_F) =")
    win.sheet.recalculate()
    assert r.result.status != "error"
    with pytest.raises(DataImportError, match="function"):
        win.sheet.rename_dataset("run1", "sin")
    assert win.apply_rename("run1", "run2")   # valid: no dialog is shown
    assert set(win.side_panel.data_buttons) == {"run2_t", "run2_F", "run2"}
    assert win.side_panel.selected_dataset == "run2"
    assert r.result.status == "error"          # old names are not rewritten
    win.sheet.remove_dataset("run2")
    assert win.side_panel.data_buttons == {} and win.side_panel.data_empty_label is not None
    assert win.sheet.datasets == []


def test_dataset_select_enables_actions(win, csv):
    import_run1(win, csv)
    sp = win.side_panel
    got = []
    sp.dataRefreshRequested.connect(got.append)
    sp.data_refresh_button.click()
    assert got == ["run1"]


def test_save_reopen_without_csv(win, csv, tmp_path):
    import_run1(win, csv)
    win.sheet.add_region("math", QPointF(40, 40), "mean(run1_F) =")
    win.sheet.recalculate()
    out = tmp_path / "s.lsheet"
    doc = win.sheet.to_document()
    assert doc.version() == 5
    doc.save(out)
    csv.unlink()
    win.open_path(out)
    assert set(win.side_panel.data_buttons) == {"run1_t", "run1_F", "run1"}
    assert not win.sheet.modified
    res = [r.result for r in win.sheet.regions()][0]
    assert res.status != "error" and "4" in res.output
    # relative source after saving next to the data folder
    assert SheetDocument.load(out).datasets[0].source == "run1.csv"


def test_new_file_clears_datasets(win, csv):
    import_run1(win, csv)
    win.sheet.set_modified(False)
    win.new_file()
    assert win.sheet.datasets == [] and win.side_panel.data_buttons == {}


def test_dialog_is_garbage_collected(app):
    import gc
    import weakref
    d = ImportDataDialog([], None)
    ref = weakref.ref(d)
    del d
    gc.collect()
    assert ref() is None


def test_error_clears_columns_table(app, tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("a|b\n1|2\n3|4\n", encoding="utf-8")
    dlg = ImportDataDialog([], None, str(p))
    assert [r[0] for r in dlg.column_rows()] == ["a", "b"]
    dlg.delimiter_combo.setCurrentIndex(0)   # Comma
    dlg.update_now()
    assert dlg.error and dlg.column_rows() == []
    dlg.deleteLater()


def test_variable_collisions_rejected(win, tmp_path):
    a = dataio.read_table_text("b_c,z\n1,2\n", name="a")
    ab = dataio.read_table_text("c,z\n1,2\n", name="a_b")
    win.sheet.add_dataset(a)
    with pytest.raises(DataImportError, match="Variable 'a_b_c' would be defined by both"):
        win.sheet.add_dataset(ab)
    # rename into a collision
    other = dataio.read_table_text("c,z\n1,2\n", name="q")
    win.sheet.add_dataset(other)
    with pytest.raises(DataImportError, match="a_b_c"):
        win.sheet.rename_dataset("q", "a_b")
    assert win.sheet.dataset("q") is other
    # dataset named like another's column variable
    win.sheet.remove_dataset("q")
    r1 = dataio.read_table_text("t,z\n1,2\n", name="run1")
    win.sheet.add_dataset(r1)
    with pytest.raises(DataImportError, match="run1_t"):
        win.sheet.add_dataset(dataio.read_table_text("v,w\n1,2\n", name="run1_t"))


def test_dialog_name_collision_and_document_load(app, tmp_path):
    a = dataio.read_table_text("b_c,z\n1,2\n", name="a")
    p = tmp_path / "c.csv"
    p.write_text("c,z\n1,2\n", encoding="utf-8")
    dlg = ImportDataDialog(["a"], None, str(p), existing_datasets=[a])
    dlg.set_dataset_name("a_b")
    assert "a_b_c" in dlg.error and not dlg.ok_button.isEnabled()
    dlg.deleteLater()
    ab = dataio.read_table_text("c,z\n1,2\n", name="a_b")
    text = SheetDocument(datasets=[a, ab]).to_json()
    with pytest.raises(DocumentError, match="Invalid dataset in file"):
        SheetDocument.from_json(text)
