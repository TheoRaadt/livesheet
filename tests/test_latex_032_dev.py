"""Spec 032 phase L1: LaTeX math in text regions (developer tests)."""

from __future__ import annotations

import json
import random
import time

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from livesheet.gui.regions import TextRegion
from livesheet.gui.texlayout import find_box, layout_formula, limits_above, walk
from livesheet.gui.worksheet import Worksheet, heading_text
from livesheet.texmath import TexError, display_text, parse, scan
import importlib

P = importlib.import_module("livesheet.texmath.parse")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet(app):
    return Worksheet()


# -- scanner -----------------------------------------------------------------------------------

def test_scan_inline_and_display():
    r = scan("a $x^2$ b")
    assert [(s.source, s.start, s.end, s.display) for s in r.spans] == [("x^2", 2, 7, False)]
    r = scan(r"$$\frac{a}{b}$$")
    assert len(r.spans) == 1 and r.spans[0].display and r.spans[0].source == r"\frac{a}{b}"


def test_scan_plain_text_cases():
    assert scan("It costs $5 and $10 each").spans == []
    assert scan("$ x$").spans == [] and scan("$x $").spans == []
    r = scan(r"cost \$5 and \$6")
    assert r.spans == [] and display_text(r"cost \$5 and \$6", r) == "cost $5 and $6"
    assert scan("price $x").spans == []
    assert scan("").spans == [] and scan("$").spans == [] and scan("$$$$").spans == []


def test_scan_adjacent_and_unterminated():
    assert [s.source for s in scan("$a$$b$").spans] == ["a", "b"]
    assert scan("$$a$").spans == []


def test_scan_paragraph_breaks():
    assert len(scan("$$a\n+b$$").spans) == 1
    assert scan("$a\n$").spans == []


def test_scan_too_long_and_limit():
    r = scan("$" + "x" * 2001 + "$")
    assert len(r.spans) == 1 and r.spans[0].too_long
    r = scan("$a$ " * 205)
    assert len(r.spans) == 200 and r.overflow


# -- parser ------------------------------------------------------------------------------------

def test_parse_scripts():
    row = parse(r"x^2")
    sc = row.items[0]
    assert isinstance(sc, P.Script) and sc.base.text == "x" and sc.sup.text == "2"
    assert parse("x_i^2") == parse("x^2_i")
    with pytest.raises(TexError, match="double superscript"):
        parse("x^2^3")
    with pytest.raises(TexError, match="double subscript"):
        parse("x_1_2")


def test_parse_frac_sqrt():
    assert isinstance(parse(r"\frac{1}{2}").items[0], P.Frac)
    with pytest.raises(TexError) as ei:
        parse(r"\frac{1}")
    assert ei.value.message == r"\frac needs two arguments"
    sq = parse(r"\sqrt[3]{x+1}").items[0]
    assert isinstance(sq, P.Sqrt) and sq.index.items[0].text == "3"
    with pytest.raises(TexError, match="needs an argument"):
        parse(r"\sqrt")


def test_parse_sum_and_limits_style():
    row = parse(r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}")
    op = row.items[0].base
    assert isinstance(op, P.BigOp)
    assert limits_above(op, True) and not limits_above(op, False)
    assert not limits_above(parse(r"\int_0^1").items[0].base, True)
    assert limits_above(parse(r"\int\limits_0^1").items[0].base, False)
    assert not limits_above(parse(r"\sum\nolimits_0^1").items[0].base, True)


def test_parse_symbols_and_errors():
    row = parse(r"\alpha+\beta")
    assert row.items[0].text == "α" and row.items[2].text == "β"
    assert parse(r"\Omega").items[0].text == "Ω"
    with pytest.raises(TexError) as ei:
        parse(r"\foo")
    assert ei.value.message == r"unknown command \foo" and ei.value.offset == 0
    with pytest.raises(TexError, match=r"unsupported: \\newcommand"):
        parse(r"\newcommand{\x}{1}")


def test_parse_delimiters_and_braces():
    assert isinstance(parse(r"\left( x \right]").items[0], P.Delimited)
    with pytest.raises(TexError, match=r"missing \\right for \\left"):
        parse(r"\left( x")
    with pytest.raises(TexError, match=r"\\right without \\left"):
        parse(r"x \right)")
    with pytest.raises(TexError, match=r"missing closing }"):
        parse("{")
    with pytest.raises(TexError, match=r"unexpected }"):
        parse("}")
    with pytest.raises(TexError, match="deeply nested"):
        parse("{" * 33 + "}" * 33)
    parse("{" * 32 + "}" * 32)
    with pytest.raises(TexError, match="too long"):
        parse("x" * 2001)


def test_parse_misc():
    with pytest.raises(TexError, match="% is not supported"):
        parse("%")
    with pytest.raises(TexError, match="stray"):
        parse("a$b")
    t = parse(r"\text{a b} \$").items
    assert t[0].text == "a b"
    # unary sign: leading and after an operator, no binary class
    assert parse("-x").items[0].kind == "ord"
    assert parse("a-b").items[1].kind == "bin"
    assert parse("a=-b").items[2].kind == "ord"


# -- layout ------------------------------------------------------------------------------------

def test_layout_scripts(app):
    sb = find_box(layout_formula("x^2", 16), "script")
    assert sb.sup.height < sb.base.height and sb.sup_shift > 0
    sb = find_box(layout_formula("x_2", 16), "script")
    assert sb.sub_shift > 0 and sb.sup is None


def test_layout_fraction(app):
    fb = find_box(layout_formula(r"\frac{a}{bcdef}", 16), "frac")
    assert fb.width >= max(fb.num.width, fb.den.width)
    assert fb.num_dy + fb.num.descent < fb.rule_dy < fb.den_dy - fb.den.ascent


def test_layout_scales_with_size(app):
    src = r"\frac{a}{b}+\sqrt{x^2+y^2}"
    ratio = layout_formula(src, 24).width / layout_formula(src, 12).width
    assert abs(ratio - 2.0) / 2.0 < 0.05


def test_layout_display_vs_inline_limits(app):
    inline = layout_formula(r"\sum_{i=1}^n i", 16, False)
    disp = layout_formula(r"\sum_{i=1}^n i", 16, True)
    assert find_box(disp, "limits") is not None and find_box(inline, "limits") is None
    assert disp.ascent > inline.ascent


def test_layout_fuzz_never_raises_other(app):
    rnd = random.Random(7)
    for _ in range(1000):
        s = "".join(rnd.choice("{}^_\\$ab1 +&") for _ in range(rnd.randint(1, 16)))
        try:
            layout_formula(s, 14)
        except TexError:
            pass


def test_layout_tall_delimiters_use_paths(app):
    box = layout_formula(r"\left(\frac{a}{b}\right)", 16)
    assert any(type(b).__name__ == "PathBox" for b in walk(box))
    small = layout_formula(r"\left(a\right)", 16)
    assert not any(type(b).__name__ == "PathBox" for b in walk(small))


# -- region behaviour --------------------------------------------------------------------------

HTML = "<p>a $x^2$ b</p>"


def make(sheet, html):
    return sheet.add_region("text", QPointF(40, 40), html)


def objects(region):
    return region.editor.toPlainText().count("￼")


def test_display_state_and_text_unchanged(sheet):
    r = make(sheet, HTML)
    assert objects(r) == 1
    assert r.text() == HTML
    assert not r.is_empty()


def test_heading_text_is_raw_source(sheet):
    r = make(sheet, "<p><b>$x$</b></p>")
    assert objects(r) == 1
    assert heading_text(r) == "$x$"


def test_edit_roundtrip_identical_and_not_modified(sheet):
    r = make(sheet, HTML)
    sheet.set_modified(False)
    before = r.text()
    r.start_editing()
    assert r.editor.toPlainText() == "a $x^2$ b"
    r.finish_editing()
    assert r.text() == before == HTML
    assert objects(r) == 1
    assert not sheet.modified


def test_typing_updates_typeset_object(sheet):
    r = make(sheet, HTML)
    r.start_editing()
    cur = r.editor.textCursor()
    cur.setPosition(5)           # after "a $x^"
    r.editor.setTextCursor(cur)
    r.editor.textCursor().insertText("3")
    r.finish_editing()
    assert objects(r) == 1
    assert "$x^32$" in r.text()
    assert sheet.modified


def test_no_math_text_behaviour_unchanged(sheet):
    r = make(sheet, "<p>plain $5 text</p>")
    assert objects(r) == 0
    assert r.text() == r.editor.toHtml()
    r.start_editing()
    r.finish_editing()
    assert objects(r) == 0


def test_escaped_dollar_display_and_edit(sheet):
    r = make(sheet, r"<p>cost \$5</p>")
    assert r.editor.toPlainText() == "cost $5"
    r.start_editing()
    assert r.editor.toPlainText() == r"cost \$5"


def test_invalid_span_display(sheet):
    r = make(sheet, r"<p>$\foo$ and $y$</p>")
    assert objects(r) == 1                      # the valid one is typeset
    assert r.editor.toPlainText().startswith(r"$\foo$ and ")
    assert r._has_error
    assert r.caption_text.startswith(r"LaTeX: unknown command \foo")
    assert r.toolTip()
    r.start_editing()
    assert not r._has_error


def test_caption_more_and_numbers(sheet):
    r = make(sheet, r"<p>$\foo$ $\bar$</p>")
    assert r.caption_text.endswith("(+1 more)") and "formula 1" in r.caption_text


def test_caption_clears_while_editing(sheet, app):
    r = make(sheet, "")
    r.start_editing()
    r.editor.textCursor().insertText(r"$\foo$")
    QTest.qWait(400)
    assert r.caption_text.startswith("LaTeX: unknown command")
    cur = QTextCursor(r.editor.document())
    cur.setPosition(1)
    cur.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    cur.insertText("x")
    QTest.qWait(300)
    assert r.caption_text == ""
    assert not r._caption.isVisible()


def test_display_math_gets_own_block(sheet):
    r = make(sheet, "<p>before $$\\frac{a}{b}$$ after</p>")
    doc = r.editor.document()
    assert doc.blockCount() == 3
    assert r.text().count("$$") == 2
    r.start_editing()
    assert doc.blockCount() == 1


def test_save_roundtrip_version_one(sheet, tmp_path):
    make(sheet, HTML)
    text = sheet.to_document().to_json()
    assert json.loads(text)["version"] == 1
    from livesheet.document import SheetDocument
    again = SheetDocument.from_json(text)
    assert again.regions[0].text == HTML
    assert again.to_json() == text


def test_click_maps_to_source(sheet):
    r = make(sheet, "<p>a $x^2$ b</p>")
    edit = r._edits[0]
    rect = r._object_rect(edit)
    assert rect is not None
    left = r.editor.mapToScene(QPointF(rect.left() + rect.width() * 0.2, rect.center().y()))
    right = r.editor.mapToScene(QPointF(rect.left() + rect.width() * 0.8, rect.center().y()))
    assert r._caret_target(left) == 3 and r._caret_target(right) == 6
    # ordinary text after the formula maps back through the shift
    after = r.editor.mapToScene(QPointF(rect.right() + 2, rect.center().y()))
    assert r._caret_target(after) >= 7
    r.start_editing(left)
    assert r.editor.textCursor().position() == 3
    r.finish_editing()
    r.start_editing(right)
    assert r.editor.textCursor().position() == 6


def test_performance_fifty_spans(sheet):
    body = " ".join(r"$\frac{a_%d}{b_%d}+\sqrt{x^2+y^2}$" % (i, i) for i in range(50))
    t = time.perf_counter()
    r = make(sheet, f"<p>{body}</p>")
    assert objects(r) == 50
    assert time.perf_counter() - t < 1.0


def test_export_pdf_with_valid_and_invalid(sheet, tmp_path):
    from livesheet.gui.main_window import export_pdf
    make(sheet, r"<p>$x^2$ and $\foo$ and $$\frac{1}{2}$$</p>")
    out = tmp_path / "f.pdf"
    export_pdf(sheet, str(out))
    assert out.read_bytes().startswith(b"%PDF")
    assert not sheet.printing


def test_caption_hidden_when_printing(sheet):
    from PySide6.QtGui import QImage, QPainter
    r = make(sheet, r"<p>$\foo$</p>")
    sheet.printing = True
    img = QImage(400, 200, QImage.Format.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    sheet.render(p)
    p.end()
    sheet.printing = False
    assert r._has_error


def test_raw_document_cached_and_inactive(sheet):
    r = make(sheet, HTML)
    assert r.raw_document() is r.raw_document()
    assert r.raw_document().toPlainText() == "a $x^2$ b"
    r2 = make(sheet, "<p>nothing</p>")
    assert r2.raw_document() is r2.editor.document()


def test_greek_follows_tex_appearance():
    def g(name):
        return parse("\\" + name).items[0].text
    assert g("phi") == "ϕ" and g("varphi") == "φ"
    assert g("epsilon") == "ϵ" and g("varepsilon") == "ε"
    assert g("theta") == "θ" and g("vartheta") == "ϑ"
    assert g("rho") == "ρ" and g("varrho") == "ϱ"
    assert g("sigma") == "σ" and g("varsigma") == "ς"
    assert g("pi") == "π" and g("varpi") == "ϖ"
    assert g("kappa") == "κ"


def test_scan_linear_on_unmatched_openers():
    for unit in ("$a ", "$a\n", "$$a\\\\ "):
        t0 = time.perf_counter()
        r = scan(unit * 20000)
        assert time.perf_counter() - t0 < 1.0
        if unit == "$a ":
            assert r.spans == []
    assert [s.source for s in scan("$a  $a $b$").spans] == ["a  $a $b"]


def test_cosmetic_primes_and_integral_limits(app):
    box = layout_formula("f'(x)", 16)
    sb = find_box(box, "script")
    assert sb.sup_shift == 0.0
    assert layout_formula(r"\int_0^\infty", 16, True).width > layout_formula(r"\int_0^1", 16, True).width - 5
