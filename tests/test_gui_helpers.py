"""Qt-free GUI helpers (key rules, dialog defaults, grid text) plus a Qt smoke test where Qt loads."""

import os

import pytest

from livesheet.engine import Engine
from livesheet.engine.formatting import format_grid
from livesheet.gui.keys import colon_edit
from livesheet.gui.paths import default_save_path, remembered_dir


def type_colons(text: str) -> str:
    """Simulate typing ``text`` character by character through the colon rule."""
    buf = ""
    for ch in text:
        if ch == ":":
            delete, insert = colon_edit(buf)
            buf = buf[: len(buf) - delete] + insert
        else:
            buf += ch
    return buf


def test_single_colon_becomes_define():
    assert type_colons("x:5") == "x:= 5"


def test_double_colon_becomes_global():
    assert type_colons("k::7") == "k≡ 7"


def test_colon_inside_brackets_is_slice():
    assert type_colons("A[1, :]") == "A[1, :]"
    assert type_colons("A[:, 2]") == "A[:, 2]"
    assert type_colons("A:[1, 2]") == "A:= [1, 2]"


def test_grid_text_is_aligned():
    text = format_grid([["1", "0"], ["0", "10"]])
    assert text.splitlines() == ["⎡ 1   0 ⎤", "⎣ 0  10 ⎦"]
    assert format_grid([["1", "2"]]) == "[ 1  2 ]"
    assert format_grid([["1"], ["2"]], "m").splitlines()[-1].endswith("⎦ m")


def test_engine_sets_grid_for_matrix_results():
    res = Engine().evaluate(enumerate(["eye(10) =", "eye(12) =", "[1, 2; 3, 4]*m =", "[a, b] →", "1 + 1 ="]))
    assert len(res[0].grid) == 10 and all(len(r) == 10 for r in res[0].grid)
    assert res[1].grid == [] and res[1].output == "= [12x12 matrix]"
    assert res[2].grid == [["1", "2"], ["3", "4"]] and res[2].grid_unit == "m"
    assert res[2].output == "= [1, 2; 3, 4] m"
    assert res[3].grid == [["a", "b"]]
    assert res[4].grid == []


def test_grid_does_not_leak_into_next_region():
    res = Engine().evaluate(enumerate(["[1, 2] =", "x := 3"]))
    assert res[1].grid == []


def test_default_save_path_avoids_examples_and_existing_files(tmp_path):
    docs = tmp_path / "Documents"
    docs.mkdir()
    ex = tmp_path / "repo" / "examples"
    ex.mkdir(parents=True)
    current = ex / "demo.lsheet"
    assert default_save_path(current, None, docs, ".lsheet") == docs / "demo.lsheet"
    assert default_save_path(current, str(ex), docs, ".pdf") == docs / "demo.pdf"
    assert default_save_path(None, None, docs, ".lsheet") == docs / "Untitled.lsheet"
    (docs / "demo.lsheet").write_text("x")
    assert default_save_path(current, None, docs, ".lsheet") == docs / "demo copy.lsheet"
    other = tmp_path / "work"
    other.mkdir()
    assert default_save_path(current, str(other), docs, ".pdf") == other / "demo.pdf"


def test_remembered_dir_skips_examples(tmp_path):
    assert remembered_dir(tmp_path / "examples" / "a.pdf") is None
    assert remembered_dir(tmp_path / "a.pdf") == str(tmp_path)


def test_gui_shows_matrix_grid_and_colon_keys():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QApplication

        from livesheet.gui.main_window import MainWindow
    except ImportError as exc:
        pytest.skip(f"Qt not usable here: {exc}")
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        region = win.sheet.add_region("math", QPointF(40, 40), "eye(3) =")
        win.sheet.recalculate()
        app.processEvents()
        shown = region.result_item.toPlainText()
        assert shown.count("\n") == 2 and "⎡" in shown and "⎣" in shown
        assert win._default_save(".lsheet").parent != win.path
    finally:
        win.sheet.set_modified(False)
        win.close()


def _qt_window():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication

        from livesheet.gui.main_window import MainWindow
    except ImportError as exc:  # e.g. missing system GL libraries
        pytest.skip(f"Qt not usable here: {exc}")
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.resize(900, 700)
    win.show()
    app.processEvents()
    return app, win


def _settle(app, win):
    """Let queued events (including deferred destruction) run, then render the view again."""
    from PySide6.QtTest import QTest

    app.processEvents()
    QTest.qWait(50)
    win.view.grab()
    app.processEvents()


MODEL = [
    ("vary t from 1 s in fall", 40, 40),
    ("h := 20 m", 40, 90),
    ("0.5*g*t^2 == h in fall", 40, 140),
    ("settle in fall", 40, 190),
    ("t =", 40, 240),
]


def test_deleting_solve_regions_does_not_crash_the_view():
    """Regression for G4: SIGSEGV in QGraphicsView::paintEvent after deleting a selected result region."""
    app, win = _qt_window()
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtTest import QTest

    try:
        sheet = win.sheet
        regions = {text: sheet.add_region("math", QPointF(x, y), text) for text, x, y in MODEL}
        sheet.recalculate()
        _settle(app, win)
        assert regions["settle in fall"].result.output.startswith("⇒ t = 2.0196")

        # 1. select the result region and press Backspace through the scene's key handler
        result = regions["settle in fall"]
        sheet.clearSelection()
        result.setSelected(True)
        app.processEvents()
        win.view.grab()
        app.sendEvent(sheet, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
        _settle(app, win)
        assert result not in sheet.regions()

        # 2. delete a declaration region through the menu action path
        vary = regions["vary t from 1 s in fall"]
        vary.setSelected(True)
        win.delete_selected()
        _settle(app, win)
        assert vary not in sheet.regions()

        # 3. delete while a region is being edited, then everything else
        edited = regions["h := 20 m"]
        edited.start_editing()
        sheet.remove_regions([edited])
        _settle(app, win)
        sheet.remove_regions(sheet.regions())
        _settle(app, win)
        assert sheet.regions() == []
        QTest.qWait(50)
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_add_and_delete_cycles_with_results_keep_rendering():
    app, win = _qt_window()
    from PySide6.QtCore import QPointF

    try:
        sheet = win.sheet
        for round_ in range(15):
            made = [sheet.add_region("math", QPointF(x, y + 300 * 0), text) for text, x, y in MODEL]
            sheet.recalculate()
            _settle(app, win)
            sheet.remove_regions(made if round_ % 2 else list(reversed(made)))
            _settle(app, win)
        sheet.clear_sheet()
        _settle(app, win)
        assert sheet.regions() == []
    finally:
        win.sheet.set_modified(False)
        win.close()
