"""Spec 024 GUI tests (G-block): the completion popup in math regions."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from livesheet.gui.worksheet import Worksheet, WorksheetView

K = Qt.Key


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet(app):
    s = Worksheet()
    view = WorksheetView(s)
    view.resize(800, 600)
    view.show()
    yield s
    s.set_modified(False)
    view.close()


def new_region(sheet, x=40, y=40, text=""):
    r = sheet.add_region("math", QPointF(x, y), text)
    r.start_editing()
    return r


def press(region, key, text="", mods=Qt.KeyboardModifier.NoModifier):
    ev = QKeyEvent(QEvent.Type.KeyPress, key, mods, text)
    region.editor.keyPressEvent(ev)


def typ(region, s):
    for ch in s:
        key = {" ": K.Key_Space, "(": K.Key_ParenLeft}.get(ch, getattr(K, f"Key_{ch.upper()}", K.Key_unknown)
                                                         if ch.isalnum() else K.Key_unknown)
        press(region, key, ch)


def popup(region):
    p = region.completion_popup()
    return p is not None and p.is_open(), p


def test_g1_open(sheet):
    r = new_region(sheet)
    typ(r, "m")
    assert not popup(r)[0]
    typ(r, "e")
    ok, p = popup(r)
    assert ok and p.candidates()[:2] == ["mean", "median"] and p.highlighted() == 0
    assert p.scene() is sheet


def test_g2_navigate_accept(sheet):
    r = new_region(sheet)
    typ(r, "me")
    _, p = popup(r)
    press(r, K.Key_Down)
    assert p.highlighted() == 1
    press(r, K.Key_Tab)
    assert r.editor.toPlainText() == "median("
    assert not p.is_open() and r.editing
    assert r.editor.textCursor().position() == len("median(")


def test_g2_wrap(sheet):
    r = new_region(sheet)
    typ(r, "me")
    _, p = popup(r)
    n = len(p.candidates())
    press(r, K.Key_Up)
    assert p.highlighted() == n - 1
    press(r, K.Key_Down)
    assert p.highlighted() == 0


def test_g3_escape(sheet):
    r = new_region(sheet)
    typ(r, "me")
    press(r, K.Key_Escape)
    assert not popup(r)[0] and r.editing and r.editor.toPlainText() == "me"
    typ(r, "a")
    assert not popup(r)[0]
    typ(r, " me")
    assert popup(r)[0]
    press(r, K.Key_Escape)
    press(r, K.Key_Escape)
    assert not r.editor.hasFocus()   # second Esc behaves as before (clears editor focus)


def test_g4_enter_commits(sheet):
    r = new_region(sheet)
    typ(r, "me")
    press(r, K.Key_Return, "\r")
    assert r.source == "me" and not r.editing and not popup(r)[0]


def test_g5_programmatic_insert(sheet):
    r = new_region(sheet)
    r.editor.textCursor().insertText("sin")
    assert not popup(r)[0]
    typ(r, "me")
    # editor text is now "sinme": move to a fresh word so the popup is open for "me"
    r2 = new_region(sheet, y=120)
    typ(r2, "me")
    assert popup(r2)[0]
    r2.editor.textCursor().insertText("alpha")
    assert not popup(r2)[0]


def test_g6_greek(sheet):
    r = new_region(sheet)
    typ(r, "alp")
    assert not popup(r)[0]
    r2 = new_region(sheet, y=120)
    typ(r2, "Gam")
    ok, p = popup(r2)
    assert ok and p.candidates()[0] == "Gamma"
    press(r2, K.Key_Tab)
    assert r2.source == "Gamma("


def test_g7_closing(sheet):
    for closer in ("(", " ", "+"):
        r = new_region(sheet)
        typ(r, "me")
        assert popup(r)[0]
        typ(r, closer)
        assert not popup(r)[0]
        r.abort_editing()
    r = new_region(sheet)
    typ(r, "me")
    press(r, K.Key_Left)
    assert not popup(r)[0]
    r = new_region(sheet, y=120)
    typ(r, "me")
    r.finish_editing()
    assert not popup(r)[0]
    r = new_region(sheet, y=200)
    typ(r, "me")
    sheet.remove_regions([r])
    assert not popup(r)[0]


def test_g8_numbers(sheet):
    r = new_region(sheet)
    for ch in "2me":
        typ(r, ch)
        assert not popup(r)[0]


def test_g9_user_names(sheet):
    sheet.add_region("math", QPointF(40, 40), "area(w, h) := w*h")
    r = new_region(sheet, y=120)
    typ(r, "ar")
    ok, p = popup(r)
    assert ok and p.candidates()[0] == "area"
    press(r, K.Key_Tab)
    assert r.editor.toPlainText() == "area("


def test_g10_midword(sheet):
    r = new_region(sheet, text="sqrt(x)")
    cur = r.editor.textCursor()
    cur.setPosition(2)
    r.editor.setTextCursor(cur)
    typ(r, "a")
    assert r.editor.toPlainText() == "sqart(x)" and not popup(r)[0]


def test_g11_tab_without_popup(sheet):
    r = new_region(sheet)
    typ(r, "x")
    press(r, K.Key_Tab, "\t")
    assert not popup(r)[0]
    # recorded current behaviour: the editor's default handling runs, region stays in edit mode
    assert r.editing


def test_g12_text_region(sheet):
    t = sheet.add_region("text", QPointF(40, 40), "")
    t.start_editing()
    for ch in "me":
        press(t, getattr(K, f"Key_{ch.upper()}"), ch)
    assert getattr(t, "completion_popup", lambda: None)() is None


def test_g13_printing(sheet):
    r = new_region(sheet)
    typ(r, "me")
    sheet.printing = True
    from PySide6.QtGui import QImage, QPainter
    img = QImage(400, 300, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    r.completion_popup().paint(p, None)
    p.end()
    assert all(img.pixel(x, y) == 0 for x in range(0, 400, 7) for y in range(0, 300, 7))
    sheet.printing = False


def test_mouse_pick(sheet):
    r = new_region(sheet)
    typ(r, "me")
    p = r.completion_popup()
    p.pick_at(QPointF(10, 1 + 18 * 1 + 5))
    assert r.editor.toPlainText() == "median(" and r.editing


def test_scroll_follows_highlight(sheet):
    for i in range(12):
        sheet.add_region("math", QPointF(400, 20 + 30 * i), f"vq{i} := {i}")
    r = new_region(sheet)
    typ(r, "vq")
    p = r.completion_popup()
    assert len(p.candidates()) > 8
    for _ in range(9):
        press(r, K.Key_Down)
    assert p._top <= p.highlighted() < p._top + 8
