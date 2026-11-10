"""Independent black-box review tests for spec 029 (calculus templates, definite integral)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from livesheet.engine import Engine  # noqa: E402
from livesheet.engine import completion  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui import sidepanel  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.pretty import pretty_source_html  # noqa: E402
from livesheet.gui.sidepanel import MATH_TOKENS, TAB_CATEGORIES  # noqa: E402

CALC = [
    ("d/dx", "diff(f, x)", (5, 6), "Derivative of f with respect to x"),
    ("∫", "integrate(f, x)", (10, 11), "Indefinite integral of f"),
    ("∫ₐᵇ", "integrate(f, (x, a, b))", (10, 11), "Definite integral of f for x from a to b"),
    ("lim", "limit(f, x, 0)", (6, 7), "Limit of f as x approaches 0"),
]
ALG = [("√", "sqrt(x)", (5, 6)), ("ⁿ√", "root(x, n)", (5, 6))]
ALL = [(a, b, c) for a, b, c, _ in CALC] + ALG


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    ini = str(tmp_path / "s.ini")
    monkeypatch.setattr(mw_module, "QSettings",
                        lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat))


@pytest.fixture
def win():
    QApplication.instance() or QApplication([])
    w = MainWindow()
    w.sheet.set_modified(False)
    yield w
    w.sheet.set_modified(False)
    w.close()


def _rows(cat):
    return [r for r in MATH_TOKENS if r[0] == cat]


def test_calculus_rows_order_tokens_tooltips():
    rows = _rows("Calculus")
    assert [(r[1], r[2]) for r in rows] == [(l, t) for l, t, _, _ in CALC]
    for r, (_, _, _, tip) in zip(rows, CALC):
        assert tip in r[3]
    assert "oo" in rows[2][3] and "unit" in rows[2][3]
    assert "oo" in rows[3][3]


def test_definite_label_fallback_is_unique_and_readable():
    # Spec allows the fallback label "∫ a..b"; whichever is used, it must be unique and non-empty.
    labels = [r[1] for r in MATH_TOKENS]
    lab = _rows("Calculus")[2][1]
    assert lab in ("∫ₐᵇ", "∫ a..b") and labels.count(lab) == 1


def test_algebra_tab_has_closed_templates_and_untouched_tail():
    assert [(r[1], r[2]) for r in _rows("Algebra")] == [
        ("√", "sqrt(x)"), ("ⁿ√", "root(x, n)"), ("x²", "^2"), ("xₙ", "_")]


def test_no_button_inserts_unclosed_bracket():
    bad = [(r[1], r[2]) for r in MATH_TOKENS if r[2].count("(") != r[2].count(")")]
    assert bad == []
    bad = [(r[1], r[2]) for r in MATH_TOKENS
           if r[2].count("[") != r[2].count("]") or r[2].count("{") != r[2].count("}")]
    assert bad == []


@pytest.mark.parametrize("label,tok,span", ALL)
def test_empty_region_insert_and_select(win, label, tok, span):
    win.side_panel.symbol_buttons[label].click()
    r = win.sheet.editing_region()
    c = r.editor.textCursor()
    assert r.source == tok
    assert (c.selectionStart(), c.selectionEnd()) == span
    assert c.selectedText() == tok[span[0]:span[1]]


@pytest.mark.parametrize("label,tok,span", ALL)
def test_after_other_text(win, label, tok, span):
    win.insert_token("y := 2 + ")
    win.side_panel.symbol_buttons[label].click()
    r = win.sheet.editing_region()
    c = r.editor.textCursor()
    off = len("y := 2 + ")
    assert r.source == "y := 2 + " + tok
    assert (c.selectionStart(), c.selectionEnd()) == (off + span[0], off + span[1])


@pytest.mark.parametrize("label,tok,span", ALL)
def test_mid_expression(win, label, tok, span):
    win.insert_token("1 +  + 2")
    r = win.sheet.editing_region()
    c = r.editor.textCursor()
    c.setPosition(4)
    r.editor.setTextCursor(c)
    win.side_panel.symbol_buttons[label].click()
    c = r.editor.textCursor()
    assert r.source == "1 + " + tok + " + 2"
    assert (c.selectionStart(), c.selectionEnd()) == (4 + span[0], 4 + span[1])


@pytest.mark.parametrize("label,tok,span", ALL)
def test_type_over_and_single_undo(win, label, tok, span):
    win.insert_token("z := ")
    r = win.sheet.editing_region()
    r.editor.document().clearUndoRedoStacks()
    win.side_panel.symbol_buttons[label].click()
    r.editor.textCursor().insertText("q")
    assert r.source == "z := " + tok[:span[0]] + "q" + tok[span[1]:]
    r.editor.document().undo()  # undo typing
    assert r.source == "z := " + tok
    r.editor.document().undo()  # undo the whole template in one step
    assert r.source == "z := "


def test_template_with_q_substituted_evaluates():
    e = Engine()
    out = e.evaluate(enumerate(["integrate(x^2 + 2*x, (x, 0, 3)) ="]))
    assert out[0].output == "= 18"


@pytest.mark.parametrize("src,expected", [
    ("integrate(t, (t, 0 s, 4 s)) =", None),
])
def test_unit_bound_no_crash(src, expected):
    r = Engine().evaluate(enumerate([src]))[0]
    assert r.status in ("ok", "error")


def test_gaussian_value():
    r = Engine().evaluate(enumerate(["integrate(exp(-x^2), (x, -oo, oo)) ="]))[0]
    assert abs(float(r.output.split("=")[1].strip()) - 1.7724538509) < 1e-4  # display is 6 significant figures


def test_bad_tuple_lengths_clean_errors():
    for src in ["integrate(x^2, (x, 0, 1, 2)) →", "integrate(x^2, (x, 0, 1, 2, 3)) →",
                "integrate(x^2, ()) →", "integrate(x^2, (3, 0, 1)) →"]:
        r = Engine().evaluate(enumerate([src]))[0]
        assert "Traceback" not in (r.error or ""), src


def test_flat_form_error_text():
    r = Engine().evaluate(enumerate(["integrate(x^2, x, 0, 3) →"]))[0]
    assert r.status == "error" and r.error
    assert "Traceback" not in r.error


@pytest.mark.parametrize("src,html", [
    ("integrate(x^2, (x, 0, 3))", "∫<sub>0</sub><sup>3</sup> x<sup>2</sup> dx"),
    ("integrate(exp(-x^2), (x, -oo, oo))", "∫<sub>-∞</sub><sup>∞</sup> exp(-x<sup>2</sup>) dx"),
    ("integrate(P, (t, 0 s, 10 s))", "∫<sub>0 s</sub><sup>10 s</sup> P dt"),
])
def test_pretty_bounds(src, html):
    assert pretty_source_html(src) == html


def test_completion_hint_and_accept():
    assert completion.signature_for("integrate") == "integrate(expr, (x, a, b))"
    comp = completion.complete("integ", 5)
    assert comp is not None and comp.candidates[0].name == "integrate"
    assert completion.accept("integ", 5, comp.candidates[0]) == ("integrate(", 10)
    assert completion.signature_for("diff") == "diff(expr, x)"


def test_other_tabs_unaffected(win):
    sp = win.side_panel
    expect = {"Elements": ("Statements", "Constants", "Greek letters"),
              "Algebra": ("Algebra",), "Calculus": ("Calculus",)}
    for k, v in expect.items():
        assert TAB_CATEGORIES[k] == v
    names = [sp.tabs.tabText(i) for i in range(sp.tabs.count())]
    for n in ("Elements", "Algebra", "Calculus", "Statistics", "Outline", "Data"):
        assert n in names
    for lab in ("α", "π", "x²", "xₙ"):
        assert lab in sp.symbol_buttons
    win.insert_token("alpha")
    assert win.sheet.editing_region().source == "alpha"
    assert not win.sheet.editing_region().editor.textCursor().hasSelection()


def test_calculus_buttons_count_and_tab_strip(win):
    sp = win.side_panel
    sp.resize(260, 600)
    idx = [sp.tabs.tabText(i) for i in range(sp.tabs.count())].index("Calculus")
    page = sp.tabs.widget(idx)
    btns = [b for b in page.findChildren(QPushButton)]
    assert [b.text() for b in btns] == [l for l, *_ in CALC]
    sp.update_band_height()
    assert sp.band_clamp() >= 0


def test_label_keys_resolve_to_buttons(win):
    for l, *_ in CALC:
        assert l in win.side_panel.symbol_buttons
