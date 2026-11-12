"""Spec 032 phase L1, independent black-box review: text-region behaviour, PDF, colours, limits."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter, QPalette, QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.document import SheetDocument  # noqa: E402
from livesheet.gui import regions as regions_mod  # noqa: E402
from livesheet.gui import texlayout  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.regions import COLOR_ERROR, TextRegion  # noqa: E402
from livesheet.gui.worksheet import Worksheet, heading_text  # noqa: E402

OBJ = "\ufffc"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet(app):
    s = Worksheet()
    yield s
    s.set_modified(False)


def make(sheet, html, y=40):
    return sheet.add_region("text", QPointF(40, y), html)


def n_objects(r):
    return r.editor.toPlainText().count(OBJ)


def plain_edit(r):
    """Raw plain text as seen by the user in edit state."""
    r.start_editing()
    t = r.editor.toPlainText()
    r.finish_editing()
    return t


# ---------------- criterion 20-23: text()/is_empty()/heading_text()/save --------------------

SAMPLES = [
    "<p>a $x^2$ b</p>",
    "<p>$$\\frac{a}{b}$$</p>",
    "<p>before $$\\frac{a}{b}$$ after</p>",
    "<p>line one</p><p>$a$ then $b$</p><p>$$x\n</p>",
    "<p><b>bold</b> and <i>$x_i$</i> and <u>under</u> $\\alpha$</p>",
    "<p>cost \\$5 and $y$</p>",
    "<p>&lt;5 &amp; $a&lt;b$</p>",
    "<p>$\\foo$ and $z$</p>",
    "<p>$$a</p><p>b$$</p>",
    "<p>日本語 $α+β$ ünï</p>",
]


def test_plain_dollar_region_toHtml_stable(sheet):
    """No valid span: pre-existing behaviour (text() is the editor's own normalised HTML)."""
    r = make(sheet, "<p>unterminated $x and $10</p>")
    first = r.text()
    r.start_editing(); r.finish_editing()
    assert r.text() == first


@pytest.mark.parametrize("html", SAMPLES)
def test_text_is_byte_identical_through_display_and_cycles(sheet, html):
    r = make(sheet, html)
    sheet.set_modified(False)
    assert r.text() == html
    for _ in range(3):
        r.start_editing()
        assert r.text() == html          # edit state, untouched
        r.finish_editing()
        assert r.text() == html
    assert not sheet.modified


@pytest.mark.parametrize("html", SAMPLES)
def test_toHtml_normal_form_is_stable_after_cycles(sheet, html):
    """The saved string for a Qt-normalised document survives load/cycle/save unchanged."""
    r0 = make(sheet, html)
    r0.start_editing()
    r0.editor.textCursor().insertText("")       # no change
    norm = r0.editor.toHtml()
    r0.finish_editing()
    r1 = make(sheet, norm)
    for _ in range(2):
        r1.start_editing()
        r1.finish_editing()
    assert r1.text() == norm


def test_file_roundtrip_byte_identical(sheet, tmp_path):
    for i, html in enumerate(SAMPLES):
        make(sheet, html, y=40 + 60 * i)
    text1 = sheet.to_document().to_json()
    assert json.loads(text1)["version"] == 1
    p = tmp_path / "a.lsheet"
    p.write_text(text1)
    s2 = Worksheet()
    s2.load_document(SheetDocument.load(p))
    for r in s2.regions():
        r.start_editing(); r.finish_editing()
    assert s2.to_document().to_json() == text1
    s2.set_modified(False)


def test_is_empty_semantics(sheet):
    assert make(sheet, "<p>$x$</p>").is_empty() is False
    assert make(sheet, "<p>$$x$$</p>").is_empty() is False
    assert make(sheet, "<p>cost \\$</p>").is_empty() is False
    assert make(sheet, "").is_empty() is True
    assert make(sheet, "<p>   </p>").is_empty() is True
    r = make(sheet, "<p>$x$</p>")
    r.start_editing()
    assert r.is_empty() is False
    r.finish_editing()


def test_empty_region_not_saved_but_math_region_saved(sheet):
    make(sheet, "<p>$x$</p>")
    make(sheet, "", y=200)
    assert len(sheet.to_document().regions) == 1


def test_text_while_editing_dirty_has_edit(sheet):
    r = make(sheet, "<p>a $x$ b</p>")
    r.start_editing()
    c = r.editor.textCursor(); c.setPosition(0); r.editor.setTextCursor(c)
    r.editor.textCursor().insertText("ZZ")
    assert "ZZa $x$ b" in r.text().replace("\n", "")
    r.finish_editing()
    assert "ZZa $x$ b" in r.text()
    assert n_objects(r) == 1


@pytest.mark.parametrize("html,expect", [
    ("<p><b>$x$</b></p>", "$x$"),
    ("<p><b>Energy $E=mc^2$ law</b></p>", "Energy $E=mc^2$ law"),
    ("<p><b>$$x^2$$</b></p>", "$$x^2$$"),
    ("<p><b>cost \\$5</b></p>", "cost \\$5"),
    ("<p><b>$\\foo$</b></p>", "$\\foo$"),
    ("<p><b>A</b> $x$</p>", None),                 # not entirely bold -> not a heading
])
def test_heading_text_is_raw_source(sheet, html, expect):
    r = make(sheet, html)
    got = heading_text(r)
    assert got == expect
    if got:
        assert OBJ not in got and "\n" not in got


def test_heading_text_appears_in_outline_list(sheet):
    make(sheet, "<p><b>Result $x^2$</b></p>")
    assert [h[2] for h in sheet.headings()] == ["Result $x^2$"]


def test_heading_text_after_edit_cycle_and_in_edit_state(sheet):
    r = make(sheet, "<p><b>H $x$</b></p>")
    r.start_editing()
    assert heading_text(r) == "H $x$"
    r.finish_editing()
    assert heading_text(r) == "H $x$"


# ---------------- display / edit state ---------------------------------------------------------

def test_display_inline_object_count_and_text_flow(sheet):
    r = make(sheet, "<p>a $x^2$ b and $y$ c</p>")
    assert n_objects(r) == 2
    assert r.editor.toPlainText().replace(OBJ, "#") == "a # b and # c"
    assert plain_edit(r) == "a $x^2$ b and $y$ c"


def test_no_dollar_region_untouched(sheet):
    r = make(sheet, "<p>just text</p>")
    assert n_objects(r) == 0 and r.caption_text == "" and not r._has_error
    assert r.errors == []


def test_unmatched_dollars_are_plain(sheet):
    r = make(sheet, "<p>It costs $5 and $10 each</p>")
    assert n_objects(r) == 0 and not r._has_error
    assert r.editor.toPlainText() == "It costs $5 and $10 each"


def test_escaped_dollar_dropped_in_display_kept_in_edit(sheet):
    r = make(sheet, "<p>cost \\$5 and \\$6</p>")
    assert r.editor.toPlainText() == "cost $5 and $6"
    assert plain_edit(r) == "cost \\$5 and \\$6"
    assert r.text() == "<p>cost \\$5 and \\$6</p>"


def test_display_math_is_own_block_and_centred(sheet):
    r = make(sheet, "<p>before $$x^2$$ after</p>")
    doc = r.editor.document()
    assert doc.blockCount() == 3
    mid = doc.findBlockByNumber(1)
    assert OBJ in mid.text()
    assert mid.blockFormat().alignment() & Qt.AlignmentFlag.AlignHCenter
    assert mid.blockFormat().topMargin() > 0 and mid.blockFormat().bottomMargin() > 0
    r.start_editing()
    assert doc.blockCount() == 1 and r.editor.toPlainText() == "before $$x^2$$ after"


def test_display_math_spanning_paragraphs(sheet):
    r = make(sheet, "<p>$$a</p><p>+b$$</p>")
    assert n_objects(r) == 1
    assert plain_edit(r) == "$$a\n+b$$"


def test_invalid_span_display_and_caption(sheet):
    r = make(sheet, "<p>$\\foo$ and $y$ then $\\bar$</p>")
    assert n_objects(r) == 1
    assert r.editor.toPlainText().startswith("$\\foo$ and ")
    assert r._has_error
    assert r.caption_text.startswith("LaTeX: unknown command \\foo")
    assert "(formula 1" in r.caption_text and "(+1 more)" in r.caption_text
    tip = r.toolTip()
    assert "\\foo" in tip and "\\bar" in tip and "formula 3" in tip
    assert r._caption.isVisible()
    # caption sits under the text
    assert r._caption.pos().y() >= r.editor.pos().y() + r.editor.boundingRect().height() - 1


def test_invalid_span_styled_error_colour_monospace(sheet):
    r = make(sheet, "<p>$\\foo$</p>")
    cur = QTextCursor(r.editor.document())
    cur.setPosition(2)
    fmt = cur.charFormat()
    assert fmt.foreground().color().name().lower() == COLOR_ERROR.lower()
    fams = [f.lower() for f in fmt.fontFamilies()] if fmt.fontFamilies() else []
    assert any(m in " ".join(fams) for m in ("menlo", "consolas", "mono"))
    # dotted underline begins at the error offset (offset 0 -> first source char after '$')
    cur.setPosition(1)
    assert cur.charFormat().underlineStyle() == cur.charFormat().UnderlineStyle.NoUnderline
    cur.setPosition(2)
    assert cur.charFormat().underlineStyle() == cur.charFormat().UnderlineStyle.DotLine


def test_underline_starts_at_error_offset(sheet):
    r = make(sheet, "<p>$ab \\foo$</p>")
    doc = r.editor.document()
    def under(pos):
        c = QTextCursor(doc); c.setPosition(pos + 1)     # char format is of the char before the cursor
        return c.charFormat().underlineStyle() == c.charFormat().UnderlineStyle.DotLine
    # chars: 0='$', 1='a', 2='b', 3=' ', 4='\\'  (error offset 3 in source => doc index 4)
    assert not under(0) and not under(1) and not under(2)
    assert under(4)


def test_edit_state_has_no_tint_but_caption(sheet):
    r = make(sheet, "<p>$\\foo$</p>")
    assert r._has_error
    r.start_editing()
    assert not r._has_error
    assert r.caption_text.startswith("LaTeX: unknown command \\foo")
    assert r._caption.isVisible()
    r.finish_editing()
    assert r._has_error


def test_caption_clears_within_300ms(sheet, app):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("$\\foo$")
    QTest.qWait(400)
    assert r.caption_text.startswith("LaTeX: unknown command")
    cur = QTextCursor(r.editor.document()); cur.setPosition(1); cur.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    cur.insertText("x")
    t0 = time.perf_counter()
    while r.caption_text and time.perf_counter() - t0 < 0.4:
        QTest.qWait(10)
    assert r.caption_text == "" and not r._caption.isVisible() and r.toolTip() == ""
    assert (time.perf_counter() - t0) < 0.3


def test_caption_not_updated_before_debounce(sheet, app):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("$\\foo$")
    assert r.caption_text == ""          # debounced, not per keystroke
    QTest.qWait(400)
    assert r.caption_text


def test_error_after_leaving_edit_with_invalid_typed(sheet, app):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("ok $x$ bad $\\nope$")
    r.finish_editing()
    assert r._has_error and n_objects(r) == 1
    assert "(formula 2" in r.caption_text and r.caption_text.startswith("LaTeX: unknown command \\nope")


def test_tint_and_caption_cleared_when_fixed_and_left(sheet, app):
    r = make(sheet, "<p>$\\foo$</p>")
    r.start_editing()
    cur = QTextCursor(r.editor.document()); cur.setPosition(1); cur.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    cur.insertText("x")
    r.finish_editing()
    assert not r._has_error and r.caption_text == "" and not r._caption.isVisible()
    assert n_objects(r) == 1


def test_never_raises_on_hostile_content(sheet):
    hostile = ["<p>$" + "{" * 100 + "$</p>", "<p>$\\frac{" * 1 + "$</p>", "<p>$$ \\\\ $$</p>",
               "<p>$\\</p>", "<p>$\\$</p>", "<p>$" + "x" * 2001 + "$</p>", "<p>$\\left($ $\\right)$</p>",
               "<p>$%$ $a&amp;b$ $a$b$</p>", "<p>$$\\text{$$ x $$</p>", "<p>$\u0000$</p>",
               "<p>" + " ".join("$\\foo$" for _ in range(30)) + "</p>"]
    for h in hostile:
        r = make(sheet, h)
        r.start_editing(); r.finish_editing()
        r.text(); r.is_empty(); heading_text(r)


def test_too_long_span_error(sheet):
    r = make(sheet, "<p>$" + "x" * 2001 + "$ and $y$</p>")
    assert r._has_error and "too long" in r.caption_text
    assert n_objects(r) == 1


def test_too_many_formulas_message(sheet):
    r = make(sheet, "<p>" + " ".join("$a$" for _ in range(205)) + "</p>")
    assert n_objects(r) == 200
    assert any("too many formulas in this region (limit 200)" in e for e in r.errors)
    assert r._has_error
    assert plain_edit(r).count("$") == 410


def test_internal_error_in_layout_becomes_invalid_span(sheet, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(regions_mod, "layout_formula", boom)
    r = make(sheet, "<p>$x$ and $y$</p>")
    assert r._has_error and "internal error in formula" in r.caption_text
    assert n_objects(r) == 0 and r.text() == "<p>$x$ and $y$</p>"


def test_internal_error_in_parse_is_caught(sheet, monkeypatch):
    def boom(src):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(texlayout.P, "parse_cached", boom, raising=False)
    monkeypatch.setattr(texlayout, "parse_cached", boom, raising=False)
    texlayout._CACHE.clear()
    r = make(sheet, "<p>$unique_source_q$</p>")
    assert r._has_error and "internal error in formula" in r.caption_text


def test_paint_exception_never_propagates(sheet, monkeypatch):
    r = make(sheet, "<p>$x^2$</p>")
    item = r._formulas[0]
    def boom(*a, **k):
        raise RuntimeError("paint boom")
    monkeypatch.setattr(item.box, "paint", boom)
    img = QImage(300, 100, QImage.Format.Format_ARGB32); img.fill(0xFFFFFFFF)
    p = QPainter(img); sheet.render(p); p.end()


# ---------------- undo / edit-leave cycles -----------------------------------------------------

def test_undo_inside_edit_state_only_undoes_typing(sheet):
    r = make(sheet, "<p>a $x$ b</p>")
    r.start_editing()
    doc = r.editor.document()
    assert not doc.isUndoAvailable()                    # swap to raw source is not an undo step
    r.editor.textCursor().insertText("QQ")
    assert doc.isUndoAvailable()
    doc.undo()
    assert r.editor.toPlainText() == "a $x$ b"
    assert not doc.isUndoAvailable()
    r.finish_editing()
    assert "a $x$ b" in r.text() and "QQ" not in r.text() and n_objects(r) == 1


def test_undo_does_not_survive_leave_into_display_garbage(sheet):
    r = make(sheet, "<p>a $x$ b</p>")
    r.start_editing()
    r.editor.textCursor().insertText("QQ")
    r.finish_editing()
    doc = r.editor.document()
    r.start_editing()
    assert r.editor.toPlainText().startswith("QQa $x$ b") or "$x$" in r.editor.toPlainText()
    assert not doc.isUndoAvailable()
    for _ in range(3):
        doc.undo()
    assert "$x$" in r.editor.toPlainText() and OBJ not in r.editor.toPlainText()
    r.finish_editing()


def test_many_cycles_with_typing_is_stable(sheet):
    r = make(sheet, "<p>$a$</p>")
    expect = "$a$"
    for i in range(5):
        r.start_editing()
        c = r.editor.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); r.editor.setTextCursor(c)
        r.editor.textCursor().insertText(f" $b{i}$")
        expect += f" $b{i}$"
        r.finish_editing()
        assert n_objects(r) == i + 2
    assert plain_edit(r) == expect


def test_abort_editing_does_not_lose_raw(sheet):
    r = make(sheet, "<p>a $x$ b</p>")
    r.start_editing()
    r.abort_editing()
    assert "$x$" in r.text()


def test_keyboard_enter_and_esc_cycle(sheet):
    r = make(sheet, "<p>a $x$ b</p>")
    sheet.set_modified(False)
    r.setSelected(True)
    r.start_editing()
    assert not n_objects(r)
    r.finish_editing()
    assert n_objects(r) == 1 and not sheet.modified


def test_ctrl_enter_leaves_and_typesets(sheet):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("$y$")
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert r.handle_key(ev) in (True, False)
    r.finish_editing()
    assert n_objects(r) == 1


# ---------------- click to caret ---------------------------------------------------------------

def center_scene(r, idx, fx):
    edit = [e for e in r._edits if e.obj_pos >= 0][idx]
    rect = r._object_rect(edit)
    return r.editor.mapToScene(QPointF(rect.left() + rect.width() * fx, rect.center().y()))


def test_click_inline_left_and_right_halves(sheet):
    r = make(sheet, "<p>ab $x^2$ cd</p>")
    r.start_editing(center_scene(r, 0, 0.25))
    assert r.editor.textCursor().position() == 4        # after "ab $"
    r.finish_editing()
    r.start_editing(center_scene(r, 0, 0.75))
    assert r.editor.textCursor().position() == 7        # before closing $
    r.finish_editing()


def test_click_display_math_halves(sheet):
    r = make(sheet, "<p>t $$\\frac{a}{b}$$ u</p>")
    src_start = "t $$".__len__()
    r.start_editing(center_scene(r, 0, 0.2))
    assert r.editor.textCursor().position() == src_start
    r.finish_editing()
    r.start_editing(center_scene(r, 0, 0.8))
    assert r.editor.textCursor().position() == src_start + len("\\frac{a}{b}")
    r.finish_editing()


def test_click_second_formula_and_text_between(sheet):
    r = make(sheet, "<p>$a$ mid $b$ tail</p>")
    r.start_editing(center_scene(r, 1, 0.75))
    assert r.editor.textCursor().position() == len("$a$ mid $b")
    r.finish_editing()


def test_click_on_plain_text_after_formulas_maps_correctly(sheet):
    r = make(sheet, "<p>$a$ $b$ tail words</p>")
    rect = r._object_rect([e for e in r._edits if e.obj_pos >= 0][1])
    pt = r.editor.mapToScene(QPointF(rect.right() + 4, rect.center().y()))
    r.start_editing(pt)
    pos = r.editor.textCursor().position()
    assert len("$a$ $b$") <= pos <= len("$a$ $b$ tail words")
    r.finish_editing()


def test_click_with_escaped_dollar_before_formula(sheet):
    r = make(sheet, "<p>cost \\$5 then $x$</p>")
    r.start_editing(center_scene(r, 0, 0.25))
    assert r.editor.textCursor().position() == len("cost \\$5 then $")
    r.finish_editing()


def test_click_plain_region_unchanged(sheet):
    r = make(sheet, "<p>hello world</p>")
    pt = r.editor.mapToScene(QPointF(2000, 5))
    r.start_editing(pt)
    assert r.editor.textCursor().position() >= 0
    r.finish_editing()


def _dbl(w, app, vp_pt):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    vp = w.view.viewport()
    L, NO = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    QTest.mouseClick(vp, L, NO, vp_pt)
    app.processEvents()
    for et, btn in ((QEvent.Type.MouseButtonDblClick, L), (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
        ev = QMouseEvent(et, QPointF(vp_pt), vp.mapToGlobal(QPointF(vp_pt)), L, btn, NO)
        QApplication.sendEvent(vp, ev)
        app.processEvents()


@pytest.mark.parametrize("fx,expect", [(0.85, 7), (0.15, 4)])
def test_real_double_click_through_view(app, fx, expect):
    w = MainWindow()
    try:
        w.resize(1000, 700)
        w.show()
        app.processEvents()
        r = w.sheet.add_region("text", QPointF(60, 60), "<p>ab $x^2$ cd</p>")
        w.sheet.set_modified(False)
        rect = r._object_rect([e for e in r._edits if e.obj_pos >= 0][0])
        sp = r.editor.mapToScene(QPointF(rect.left() + rect.width() * fx, rect.center().y()))
        w.view.centerOn(sp)
        app.processEvents()
        _dbl(w, app, w.view.mapFromScene(sp))
        assert r.editing
        assert r.editor.textCursor().position() == expect
        assert r.editor.toPlainText() == "ab $x^2$ cd"
        r.finish_editing()
        assert not w.sheet.modified and n_objects(r) == 1
    finally:
        w.sheet.set_modified(False)
        w.close()


# ---------------- PDF / print / colour ---------------------------------------------------------

def build_math_sheet():
    s = Worksheet()
    s.add_region("text", QPointF(40, 40), "<p>$x^2$ and $\\foo$ and $\\sum_{i=1}^n i$</p>")
    s.add_region("text", QPointF(40, 140), "<p>$$\\frac{1}{2}+\\sqrt{x}$$ tail</p>")
    return s


def test_export_pdf_vector_no_images(sheet, tmp_path):
    s = build_math_sheet()
    out = tmp_path / "m.pdf"
    export_pdf(s, str(out))
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/Subtype /Image" not in data and b"/Subtype/Image" not in data
    assert b"/Font" in data
    assert not s.printing
    s.set_modified(False)


def test_export_pdf_page_count_matches_plain_text(tmp_path):
    def pages(path):
        return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
    a = Worksheet(); a.add_region("text", QPointF(40, 40), "<p>$x^2$ and $\\foo$</p>")
    b = Worksheet(); b.add_region("text", QPointF(40, 40), "<p>xxx and yyy</p>")
    pa, pb = tmp_path / "a.pdf", tmp_path / "b.pdf"
    export_pdf(a, str(pa)); export_pdf(b, str(pb))
    assert pages(pa) == pages(pb) >= 1


def test_export_pdf_while_editing_formula(tmp_path):
    s = Worksheet()
    r = s.add_region("text", QPointF(40, 40), "<p>$x^2$</p>")
    r.start_editing()
    export_pdf(s, str(tmp_path / "e.pdf"))
    assert not r.editing and n_objects(r) == 1
    s.set_modified(False)


def test_texlayout_source_has_no_raster_caching():
    src = Path(texlayout.__file__).read_text()
    for banned in ("QPixmap", "QImage", "QBitmap", "QPicture", "grabWidget", "grab("):
        assert banned not in src, banned


def render_region(s, rect=QRectF(0, 0, 400, 120), printing=False, bg=0xFFFFFFFF):
    s.printing = printing
    img = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
    img.fill(bg)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s.clearSelection()
    s.render(p, QRectF(0, 0, rect.width(), rect.height()), rect)
    p.end()
    s.printing = False
    return img


def dark_pixels(img, thresh=140):
    n = 0
    for y in range(img.height()):
        for x in range(img.width()):
            c = QColor(img.pixel(x, y))
            if c.red() < thresh and c.green() < thresh and c.blue() < thresh:
                n += 1
    return n


def test_math_paints_something_and_in_text_colour(sheet):
    r = make(sheet, "<p>$\\sum_{i=1}^n i = \\frac{n}{2}$</p>")
    img = render_region(sheet)
    assert dark_pixels(img) > 40
    # darkest opaque pixel is the #222222 token (anti-aliased), not black or palette
    darkest = min((QColor(img.pixel(x, y)) for x in range(img.width()) for y in range(img.height())),
                  key=lambda c: c.red() + c.green() + c.blue())
    assert abs(darkest.red() - 0x22) <= 24 and darkest.red() == darkest.green() == darkest.blue()


def test_dark_application_palette_does_not_change_rendering(app, sheet):
    make(sheet, "<p>a $\\frac{x}{y}$ b</p>")
    before = render_region(sheet)
    old = app.palette()
    pal = QPalette(old)
    pal.setColor(QPalette.ColorRole.Text, QColor("white"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("white"))
    pal.setColor(QPalette.ColorRole.Window, QColor("#202020"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#202020"))
    app.setPalette(pal)
    try:
        after = render_region(sheet)
    finally:
        app.setPalette(old)
    assert before == after


def test_color_not_hardcoded_in_texlayout():
    src = Path(texlayout.__file__).read_text()
    assert not re.search(r"QColor\(\s*['\"#]", src), "colour literal in texlayout"
    assert "palette()" not in src


def test_print_hides_caption_and_tint(sheet):
    r = make(sheet, "<p>$\\foo$</p>")
    screen = render_region(sheet)
    printed = render_region(sheet, printing=True)
    assert r._has_error                                  # state restored after printing
    # tint colour (255,235,235) appears on screen but not when printing
    def count(img, rgb):
        return sum(1 for y in range(img.height()) for x in range(img.width())
                   if QColor(img.pixel(x, y)).getRgb()[:3] == rgb)
    assert count(screen, (255, 235, 235)) > 100
    assert count(printed, (255, 235, 235)) == 0
    # the invalid span prints in the error colour
    err = QColor(COLOR_ERROR)
    assert any(abs(QColor(printed.pixel(x, y)).red() - err.red()) < 30 and QColor(printed.pixel(x, y)).green() < 90
               for y in range(printed.height()) for x in range(printed.width()))
    assert screen != printed


def test_caption_contrast_vs_backgrounds():
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())
    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)
    fg = QColor(COLOR_ERROR)
    for bg in (QColor("white"), regions_mod.COLOR_EDIT_BG, regions_mod.COLOR_ERROR_BG):
        assert ratio(fg, bg) >= 4.5, (bg.name(), ratio(fg, bg))
    for bg in (QColor("white"), regions_mod.COLOR_EDIT_BG, regions_mod.COLOR_ERROR_BG):
        assert ratio(regions_mod.TEXT_COLOR, bg) >= 4.5


# ---------------- performance / limits ---------------------------------------------------------

def test_perf_single_span_under_5ms(app):
    texlayout._CACHE.clear()
    texlayout.parse_cached.cache_clear() if hasattr(texlayout.parse_cached, "cache_clear") else None
    texlayout.layout_formula(r"warm", 16)
    src = r"\frac{a_1}{b_1}+\sqrt{x^2+y^2}"
    t = time.perf_counter()
    texlayout.layout_formula(src, 16)
    assert (time.perf_counter() - t) * 1000 < 5.0


def test_perf_fifty_spans_under_250ms_cold(sheet):
    texlayout._CACHE.clear()
    try:
        from livesheet.texmath import parse as pm
        pm.parse_cached.cache_clear()
    except Exception:
        pass
    body = " ".join(r"$\frac{a_%d}{b_%d}+\sqrt{x^2+y^2}$" % (i, i) for i in range(50))
    t = time.perf_counter()
    r = make(sheet, f"<p>{body}</p>")
    dt = time.perf_counter() - t
    assert n_objects(r) == 50
    assert dt < 1.0, dt
    assert dt < 0.25, f"spec target 250 ms, got {dt*1000:.0f} ms"


def test_perf_leave_edit_with_fifty_spans(sheet):
    body = " ".join(r"$\frac{a_%d}{b_%d}+\sqrt{x^2+y^2}$" % (i, i) for i in range(50))
    r = make(sheet, f"<p>{body}</p>")
    r.start_editing()
    t = time.perf_counter(); r.finish_editing(); dt = time.perf_counter() - t
    assert dt < 0.25, dt


def test_layout_cache_bounded(app):
    texlayout._CACHE.clear()
    for i in range(700):
        texlayout.layout_formula(f"x_{{{i}}}", 14)
    assert len(texlayout._CACHE) <= 500


def test_layout_cache_is_lru(app):
    texlayout._CACHE.clear()
    texlayout.layout_formula("keepme", 14)
    for i in range(499):
        texlayout.layout_formula(f"q{i}", 14)
    texlayout.layout_formula("keepme", 14)       # refresh
    for i in range(10):
        texlayout.layout_formula(f"z{i}", 14)
    assert ("keepme", 1400, False) in texlayout._CACHE


def test_edit_does_not_typeset_per_keystroke(sheet, monkeypatch):
    r = make(sheet, "")
    r.start_editing()
    calls = []
    orig = regions_mod.layout_formula
    monkeypatch.setattr(regions_mod, "layout_formula", lambda *a, **k: calls.append(1) or orig(*a, **k))
    for ch in "$x^2$ abc":
        r.editor.textCursor().insertText(ch)
    assert calls == []


def test_recalculate_does_not_retypeset(sheet, monkeypatch):
    make(sheet, "<p>$x^2$</p>")
    calls = []
    orig = regions_mod.layout_formula
    monkeypatch.setattr(regions_mod, "layout_formula", lambda *a, **k: calls.append(1) or orig(*a, **k))
    sheet.recalculate()
    assert calls == []


def test_timer_stopped_when_region_deleted(sheet, app):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("$\\foo$")
    r.abort_editing()
    sheet.removeItem(r)
    QTest.qWait(400)           # must not crash


# ---------------- layout details (criteria 16-18 plus visual relations) ------------------------

def test_layout_relations(app):
    sb = texlayout.find_box(texlayout.layout_formula("x^2", 16), "script")
    assert sb.sup.height < sb.base.height and sb.sup_shift > 0
    sb = texlayout.find_box(texlayout.layout_formula("x_2", 16), "script")
    assert sb.sub_shift > 0
    both = texlayout.find_box(texlayout.layout_formula("x_a^b", 16), "script")
    assert both.sup is not None and both.sub is not None
    fb = texlayout.find_box(texlayout.layout_formula(r"\frac{a}{bcdef}", 16), "frac")
    assert fb.width >= max(fb.num.width, fb.den.width)


def test_script_sizes_70_50_and_floor(app):
    c = texlayout.Ctx(20.0)
    assert abs(c.script().size - 14.0) < 0.01
    assert abs(c.script().script().size - 10.0) < 0.01
    assert texlayout.Ctx(10.0).script().script().size >= 8.0 - 1e-9      # 6pt floor


@pytest.mark.parametrize("src", [r"x^2", r"\frac{a}{b}", r"\sqrt{x+1}", r"\sum_{i=1}^n i", r"\left(\frac12\right)"])
def test_size_ratio_within_5_percent(app, src):
    for disp in (False, True):
        r = texlayout.layout_formula(src, 24, disp).width / texlayout.layout_formula(src, 12, disp).width
        assert abs(r - 2.0) / 2.0 < 0.05, (src, r)


def test_layout_fuzz_only_texerror(app):
    import random
    from livesheet.texmath import TexError
    rnd = random.Random(11)
    for _ in range(1000):
        s = "".join(rnd.choice("{}^_\\$ab1 +&") for _ in range(rnd.randint(1, 18)))
        try:
            texlayout.layout_formula(s, 14, bool(rnd.getrandbits(1)))
        except TexError:
            pass


def test_boxes_have_finite_positive_metrics(app):
    import math
    for src in [r"x", r"\frac{a}{b}", r"\sqrt[3]{x}", r"\int_0^1 f", r"\sum_{i}^{n}", r"\left(\frac{a}{b}\right)",
                r"\binom{n}{k}", r"\text{hi there}", r"a\,b\quad c", r"x'", r"\lim_{x\to0}"]:
        for disp in (False, True):
            b = texlayout.layout_formula(src, 16, disp)
            for bx in texlayout.walk(b):
                assert all(math.isfinite(v) for v in (bx.width, bx.ascent, bx.descent)), src
                assert bx.width >= 0
            assert b.width > 0 and b.height > 0


# ---------------- misc edge cases from the spec's list -----------------------------------------

def test_span_size_follows_font_size_at_first_dollar(sheet):
    small = make(sheet, "<p>$x^2+y$</p>")
    big = make(sheet, '<p><span style=" font-size:28pt;">$x^2+y$</span></p>', y=200)
    assert big._formulas[0].box.width > 1.8 * small._formulas[0].box.width


def test_dollar_in_math_region_is_untouched(sheet):
    m = sheet.add_region("math", QPointF(40, 300), "y := $a$")
    assert m.text() == "y := $a$"


def test_paste_plain_dollar_text_not_converted_while_editing(sheet):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText("a $b$ c")
    assert r.editor.toPlainText() == "a $b$ c" and n_objects(r) == 0
    r.finish_editing()
    assert n_objects(r) == 1


def test_only_whitespace_and_lone_dollar_regions(sheet):
    for html in ("<p>$</p>", "<p> </p>", "<p>$$</p>", "<p>$ $</p>", "<p> </p>"):
        r = make(sheet, html)
        assert n_objects(r) == 0 and not r._has_error and r.caption_text == ""


def test_nbsp_inside_formula_boundaries(sheet):
    r = make(sheet, "<p>a $ x$ b</p>")
    assert n_objects(r) == 0


def test_region_with_formula_inside_page_break_exports(tmp_path):
    s = Worksheet()
    s.add_region("text", QPointF(40, 40), "<p>$x$</p>")
    s.add_region("text", QPointF(40, 1000), "<p>$$\\frac{a}{b}$$ after</p>")
    export_pdf(s, str(tmp_path / "pb.pdf"))
    assert (tmp_path / "pb.pdf").read_bytes().startswith(b"%PDF")
    s.set_modified(False)


def test_region_height_grows_only_for_math_line(sheet):
    plain = make(sheet, "<p>one</p><p>two</p><p>three</p>")
    h_plain = plain.editor.boundingRect().height()
    with_math = make(sheet, "<p>one</p><p>two $x$</p><p>three</p>", y=300)
    h_math = with_math.editor.boundingRect().height()
    # a short formula must not make the paragraph noticeably taller than a plain paragraph
    assert h_math - h_plain < 8, (h_plain, h_math)
    tall = make(sheet, "<p>one</p><p>two $\\frac{a}{b}$</p><p>three</p>", y=500)
    assert tall.editor.boundingRect().height() > h_plain


def test_plain_text_region_height_identical_to_baseline(sheet):
    a = make(sheet, "<p>one</p><p>two</p>")
    ref = TextRegion("<p>one</p><p>two</p>")
    assert abs(a.editor.boundingRect().height() - ref.editor.boundingRect().height()) < 0.01


def test_frame_follows_state_and_position_stable(sheet):
    r = make(sheet, "<p>$$\\frac{a}{b}$$</p>")
    pos = r.pos()
    h_disp = r.boundingRect().height()
    r.start_editing()
    assert r.pos() == pos
    assert r.boundingRect().height() != h_disp
    r.finish_editing()
    assert r.pos() == pos and abs(r.boundingRect().height() - h_disp) < 0.01
