"""GUI smoke tests (run headless with QT_QPA_PLATFORM=offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.pretty import display_source, pretty_source_html  # noqa: E402
from livesheet.gui.regions import MathRegion, TextRegion  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    app.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()


def _typing(win, app):
    vp = win.view.viewport()

    def click(x, y):
        QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, win.view.mapFromScene(x, y))
        app.processEvents()

    def typ(text):
        QTest.keyClicks(vp, text)
        app.processEvents()

    def key(k, mod=Qt.KeyboardModifier.NoModifier):
        QTest.keyClick(vp, k, mod)
        app.processEvents()

    return click, typ, key


def test_type_definitions_and_evaluate(win, app):
    click, typ, key = _typing(win, app)
    click(50, 50)
    typ("a:3 m")
    key(Qt.Key.Key_Return)
    typ("a*2=")
    key(Qt.Key.Key_Return)
    win.sheet.recalculate()
    regs = win.sheet.ordered_regions()
    assert [r.source for r in regs] == ["a:= 3 m", "a*2="]
    assert regs[1].result.output == "= 6 m"
    assert regs[1].pos().y() > regs[0].pos().y()


def test_moving_region_changes_order(win, app):
    sheet = win.sheet
    from PySide6.QtCore import QPointF

    d = sheet.add_region("math", QPointF(40, 40), "x := 2")
    e = sheet.add_region("math", QPointF(40, 100), "x =")
    sheet.recalculate()
    assert e.result.output == "= 2"
    e.setPos(40, 0)
    sheet.recalculate()
    assert e.result.status == "error"
    assert d.result.status == "ok"


def test_text_region_and_delete(win, app):
    click, typ, key = _typing(win, app)
    click(60, 300)
    typ('"Note')
    key(Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    texts = [r for r in win.sheet.regions() if isinstance(r, TextRegion)]
    assert len(texts) == 1 and texts[0].editor.toPlainText() == "Note"
    texts[0].setSelected(True)
    key(Qt.Key.Key_Delete)
    assert not [r for r in win.sheet.regions() if isinstance(r, TextRegion)]


def test_empty_region_removed_after_editing(win, app):
    win.sheet.insert_region("math")
    region = win.sheet.editing_region()
    region.finish_editing()
    assert region not in win.sheet.regions()


def test_save_open_roundtrip(win, app, tmp_path):
    from PySide6.QtCore import QPointF

    win.sheet.add_region("math", QPointF(40, 40), "y := 7 kg")
    win.sheet.add_region("math", QPointF(40, 90), "y =")
    path = tmp_path / "w.lsheet"
    assert win._write(path)
    win.sheet.clear_sheet()
    win.open_path(path)
    maths = [r for r in win.sheet.ordered_regions() if isinstance(r, MathRegion)]
    assert [m.source for m in maths] == ["y := 7 kg", "y ="]
    assert maths[1].result.output == "= 7 kg"
    assert not win.sheet.modified


def test_export_pdf(win, app, tmp_path):
    from PySide6.QtCore import QPointF

    win.sheet.add_region("math", QPointF(40, 40), "1 + 1 =")
    win.sheet.add_region("math", QPointF(40, 2500), "2 + 2 =")  # forces a second page
    out = tmp_path / "w.pdf"
    export_pdf(win.sheet, str(out))
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") >= 1


def test_pretty_display():
    assert pretty_source_html("x^2 := alpha") == "x<sup>2</sup> := α"
    assert display_source("v = km/hr") == "v"
    assert display_source("(x+1)^2 ->") == "(x+1)^2"
    assert display_source("x^2 - 1 → factor") == "x^2 - 1 → factor"
