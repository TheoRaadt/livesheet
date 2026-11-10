"""Tests for spec 029: closed calculus/algebra templates, selection after insert, definite integral."""

from __future__ import annotations

import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.engine import Engine  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.pretty import pretty_source_html  # noqa: E402
from livesheet.gui.regions import MathRegion  # noqa: E402
from livesheet.gui.sidepanel import MATH_TOKENS, TOKEN_SELECTION, SidePanel  # noqa: E402

TEMPLATES = {
    "√": ("sqrt(x)", (5, 6)),
    "ⁿ√": ("root(x, n)", (5, 6)),
    "d/dx": ("diff(f, x)", (5, 6)),
    "∫": ("integrate(f, x)", (10, 11)),
    "∫ₐᵇ": ("integrate(f, (x, a, b))", (10, 11)),
    "lim": ("limit(f, x, 0)", (6, 7)),
}


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
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


def _cat(name):
    return [(lab, tok) for c, lab, tok, _ in MATH_TOKENS if c == name]


def test_token_tables():
    assert _cat("Calculus") == [("d/dx", "diff(f, x)"), ("∫", "integrate(f, x)"),
                                ("∫ₐᵇ", "integrate(f, (x, a, b))"), ("lim", "limit(f, x, 0)")]
    assert _cat("Algebra") == [("√", "sqrt(x)"), ("ⁿ√", "root(x, n)"), ("x²", "^2"), ("xₙ", "_")]
    labels = [lab for _, lab, _, _ in MATH_TOKENS]
    assert len(labels) == len(set(labels))
    assert all(t.count("(") <= t.count(")") for _, _, t, _ in MATH_TOKENS)


def test_selection_table():
    tokens = {t for _, _, t, _ in MATH_TOKENS}
    for tok, (s, e) in TOKEN_SELECTION.items():
        assert tok in tokens
        assert tok[s:e] == ("x" if tok.startswith(("sqrt", "root")) else "f")
    assert len(TOKEN_SELECTION) == 6


@pytest.mark.parametrize("label", list(TEMPLATES))
def test_click_inserts_and_selects(win, label):
    tok, span = TEMPLATES[label]
    win.side_panel.symbol_buttons[label].click()
    r = win.sheet.editing_region()
    sel = r.editor.textCursor()
    assert r.source == tok
    assert (sel.selectionStart(), sel.selectionEnd()) == span
    assert sel.selectedText() == tok[span[0]:span[1]]


def test_typing_replaces_selection(win):
    win.side_panel.symbol_buttons["∫ₐᵇ"].click()
    r = win.sheet.editing_region()
    r.editor.textCursor().insertText("x^2")
    assert r.source == "integrate(x^2, (x, a, b))"
    assert r.editing


def test_insert_in_middle(win):
    win.insert_token("y := ")
    win.side_panel.symbol_buttons["∫"].click()
    r = win.sheet.editing_region()
    sel = r.editor.textCursor()
    assert r.source == "y := integrate(f, x)"
    assert sel.selectedText() == "f" and sel.selectionStart() == 15


def test_plain_token_no_selection(win):
    win.insert_token("x")
    win.side_panel.symbol_buttons["x²"].click()
    r = win.sheet.editing_region()
    cur = r.editor.textCursor()
    assert r.source == "x^2" and not cur.hasSelection() and cur.position() == 3


def test_selected_text_replaced(win):
    win.insert_token("abc")
    r = win.sheet.editing_region()
    cur = r.editor.textCursor()
    cur.select(cur.SelectionType.Document)
    r.editor.setTextCursor(cur)
    win.side_panel.symbol_buttons["d/dx"].click()
    assert r.source == "diff(f, x)"
    assert r.editor.textCursor().selectedText() == "f"


def test_side_panel_calls_insert_token_with_token_only(win):
    from unittest.mock import Mock
    spy = Mock()
    panel = SidePanel(spy)
    panel.symbol_buttons["d/dx"].click()
    spy.assert_called_once_with("diff(f, x)")
    panel.deleteLater()


# -- engine ------------------------------------------------------------------------------------

def _run(*src):
    res = Engine().evaluate(enumerate(src))
    return res[len(src) - 1]


@pytest.mark.parametrize("tok", [t for t, _ in TEMPLATES.values()])
def test_templates_valid_for_engine(tok):
    r = _run(tok)
    assert r.status == "ok" and r.output == ""


@pytest.mark.parametrize("srcs,out", [
    (["integrate(2*x, (x, 0, 3)) →"], "→ 9"),
    (["integrate(x^2, (x, 0, 2)) →"], "→ 8/3"),
    (["integrate(x^2 - 2*x, (x, 0, 3)) ="], "= 0"),
    (["integrate(x^2 - 2*x, (x, 0, 2)) →"], "→ -4/3"),
    (["integrate(x^2 + 2*x, (x, 0, 3)) ="], "= 18"),
    (["accel := 2 m/s^2", "integrate(accel, (t, 0 s, 4 s)) ="], "= 8 m/s"),
    (["P := 100 W", "integrate(P, (t, 0 s, 10 s)) ="], "= 1000 J"),
    (["k := 2 N/m", "integrate(k*x, (x, 0 m, 3 m)) ="], "= 9 J"),
    (["integrate(exp(-x), (x, 0, oo)) →"], "→ 1"),
    (["integrate(exp(-x), (x, 0, oo)) ="], "= 1"),
    (["integrate(1/x^2, (x, 1, oo)) ="], "= 1"),
    (["integrate(x^2, (x, 0, b)) →"], "→ b³/3"),
    (["b := 3", "integrate(x^2, (x, 0, b)) ="], "= 9"),
    (["limit(sin(x)/x, x, 0) →"], "→ 1"),
    (["limit(1/x, x, oo) →"], "→ 0"),
])
def test_engine_results(srcs, out):
    r = _run(*srcs)
    assert r.status == "ok", r.error
    assert r.output == out


def test_gaussian_integral():
    r = _run("integrate(exp(-x^2), (x, -oo, oo)) =")
    assert r.status == "ok"
    assert abs(float(r.output.lstrip("= ")) - math.sqrt(math.pi)) < 1e-4


def test_undefined_bound_error():
    r = _run("integrate(x^2, (x, 0, b)) =")
    assert r.status == "error" and "not defined" in r.error


def test_bad_bounds_error_clean():
    # Corrected from spec: (x, 0) and 4-tuples are accepted by SymPy (no error); use a 5-tuple.
    r = _run("integrate(x^2, (x, 0, 1, 2, 3)) →")
    assert r.status == "error" and r.error and "Traceback" not in r.error


def test_flat_bounds_form_fails():
    assert _run("integrate(x^2, x, 0, 3) →").status == "error"


# -- pretty ------------------------------------------------------------------------------------

@pytest.mark.parametrize("src,html", [
    ("integrate(f, x)", "∫ f dx"),
    ("integrate(f, (x, a, b))", "∫<sub>a</sub><sup>b</sup> f dx"),
    ("integrate(exp(-x), (x, 0, oo))", "∫<sub>0</sub><sup>∞</sup> exp(-x) dx"),
    ("integrate(x^2, (x, 0 m, 3 m))", "∫<sub>0 m</sub><sup>3 m</sup> x<sup>2</sup> dx"),
    ("integrate(f, (x, -oo, oo))", "∫<sub>-∞</sub><sup>∞</sup> f dx"),
    ("diff(f, x)", "d/dx (f)"),
    ("limit(f, x, 0)", "limit(f, x, 0)"),
    ("sqrt(x)", "√(x)"),
])
def test_pretty(src, html):
    assert pretty_source_html(src) == html


def test_region_display():
    QApplication.instance() or QApplication([])
    r = MathRegion("integrate(f, (x, a, b))")
    assert not r.editing
    assert r.editor.toPlainText() == "∫abf dx" or "∫" in r.editor.toPlainText()
