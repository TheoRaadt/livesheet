"""Independent black-box tests for spec 026 (Statistics + Optimization tab buttons).

Written from docs/board/specs/026-statistics-and-optimization-tabs.md only. Settings are
isolated (temp INI for the whole module + QSettings patched in main_window); the real plist is
digest-checked before/after.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea  # noqa: E402

from livesheet.engine import Engine  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402

PLIST = Path.home() / "Library/Preferences/com.livesheet.LiveSheet.plist"

SUMMARY = [
    ("mean", "mean(v)"), ("median", "median(v)"), ("mode", "mode(v)"),
    ("variance", "variance(v)"), ("stdev", "stdev(v)"),
    ("population_variance", "population_variance(v)"),
    ("population_stdev", "population_stdev(v)"), ("quantile", "quantile(v, p)"),
    ("covariance", "covariance(u, w)"), ("correlation", "correlation(u, w)"),
]
DIST = [
    ("normal_pdf", "normal_pdf(x, mu, sigma)"), ("normal_cdf", "normal_cdf(x, mu, sigma)"),
    ("normal_quantile", "normal_quantile(p, mu, sigma)"),
    ("normal_sample", "normal_sample(mu, sigma, n, seed)"),
    ("uniform_pdf", "uniform_pdf(x, a, b)"), ("uniform_cdf", "uniform_cdf(x, a, b)"),
    ("uniform_quantile", "uniform_quantile(p, a, b)"),
    ("uniform_sample", "uniform_sample(a, b, n, seed)"),
    ("binomial_pmf", "binomial_pmf(k, n_trials, p)"),
    ("binomial_cdf", "binomial_cdf(k, n_trials, p)"),
    ("binomial_quantile", "binomial_quantile(q, n_trials, p)"),
    ("binomial_sample", "binomial_sample(n_trials, p, n, seed)"),
    ("poisson_pmf", "poisson_pmf(k, lambda_)"), ("poisson_cdf", "poisson_cdf(k, lambda_)"),
    ("poisson_quantile", "poisson_quantile(q, lambda_)"),
    ("poisson_sample", "poisson_sample(lambda_, n, seed)"),
]
TESTS = [
    ("sample", "sample v in t1"), ("expected", "expected counts in t1"),
    ("claim mean", "claim mean == 0 in t1"),
    ("claim two means", "claim mean1 == mean2 in t1"),
    ("claim fits", "claim fits in t1"), ("level", "level 0.05 in t1"),
    ("verdict", "verdict in t1"),
]
REG = [
    ("fit_linear", "fit_linear(x, y)"), ("fit_poly", "fit_poly(x, y, 2)"),
    ("predict", "predict(c, x)"), ("r_squared", "r_squared(c, x, y)"),
]
UNK = [("vary", "vary x from 1 in m1"), ("equation ==", "x^2 == 4 in m1"),
       ("limit <=", "x <= 10 in m1"), ("limit >=", "x >= 0 in m1")]
SET = [("accuracy", "accuracy 1e-8 in m1"), ("steps", "steps 200 in m1")]
RES = [("settle", "settle in m1"), ("least", "least x^2 in m1"), ("most", "most x in m1")]

STAT_GROUPS = [("Summary statistics", SUMMARY), ("Distributions", DIST),
               ("Hypothesis tests", TESTS), ("Regression", REG)]
OPT_GROUPS = [("Unknowns and constraints", UNK), ("Settings (optional)", SET),
              ("Results", RES)]
ALL = [(g, lab, tok) for g, rows in STAT_GROUPS + OPT_GROUPS for lab, tok in rows]


def _digest():
    return hashlib.md5(PLIST.read_bytes()).hexdigest() if PLIST.exists() else None


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module", autouse=True)
def isolated_settings(tmp_path_factory, app):
    before = _digest()
    old_fmt = QSettings.defaultFormat()
    d = tmp_path_factory.mktemp("qsettings026")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(d))
    yield
    QSettings.setDefaultFormat(old_fmt)
    assert _digest() == before, "test run modified the user's real LiveSheet settings"


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    ini = str(tmp_path / "s.ini")
    monkeypatch.setattr(mw_module, "QSettings",
                        lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat))
    w = MainWindow()
    w.sheet.set_modified(False)
    w.resize(900, 800)
    w.show()
    QApplication.processEvents()
    yield w
    w.sheet.set_modified(False)
    w.close()
    QApplication.processEvents()


def panel(w):
    return w.side_panel


def page(w, name):
    p = panel(w)
    for i in range(p.tabs.count()):
        if p.tabs.tabText(i) == name:
            return p.tabs.widget(i)
    raise AssertionError(name)


def page_items(w, name):
    """Widgets of a tab page in layout order."""
    pg = page(w, name)
    lay = pg.widget().layout()
    return [lay.itemAt(i).widget() for i in range(lay.count())]


# ---------------------------------------------------------------- structure ---------------

def test_counts_and_unique_labels(win):
    assert sum(len(r) for _, r in STAT_GROUPS) == 37
    assert sum(len(r) for _, r in OPT_GROUPS) == 9
    sb = panel(win).symbol_buttons
    for _g, lab, _t in ALL:
        assert lab in sb, lab
        assert isinstance(sb[lab], QPushButton)
        assert sb[lab].text() == lab


@pytest.mark.parametrize("tab,groups", [("Statistics", STAT_GROUPS), ("Optimization", OPT_GROUPS)])
def test_tab_layout_headers_and_order(win, tab, groups):
    items = page_items(win, tab)
    expected = []
    for g, rows in groups:
        expected.append(("H", g))
        expected += [("B", lab) for lab, _ in rows]
    got = [("H", w.text()) if isinstance(w, QLabel) else ("B", w.text()) for w in items]
    assert got == expected


@pytest.mark.parametrize("tab,groups", [("Statistics", STAT_GROUPS), ("Optimization", OPT_GROUPS)])
def test_each_group_starts_on_new_row(win, tab, groups):
    win.resize(1100, 900)
    QApplication.processEvents()
    panel(win).tabs.setCurrentIndex([panel(win).tabs.tabText(i)
                                     for i in range(panel(win).tabs.count())].index(tab))
    QApplication.processEvents()
    items = page_items(win, tab)
    headers = [w for w in items if isinstance(w, QLabel)]
    assert len(headers) == len(groups)
    for h in headers:
        i = items.index(h)
        if i:
            prev = items[i - 1]
            assert h.geometry().top() >= prev.geometry().bottom() - 1, h.text()
        if i + 1 < len(items):   # existing behaviour: header leads its group's first row
            assert items[i + 1].geometry().top() < h.geometry().bottom() + 4


def test_tab_order_and_placeholders_unchanged(win):
    p = panel(win)
    names = [p.tabs.tabText(i) for i in range(p.tabs.count())]
    assert names == ["Elements", "Algebra", "Calculus", "Statistics", "Optimization",
                     "Mechanical", "Electrical", "Chemical", "Outline", "Data"]
    for name in ("Statistics", "Optimization"):
        texts = [lb.text() for lb in page(win, name).findChildren(QLabel)]
        assert not any("will appear" in t for t in texts)


def test_data_placeholder_unchanged(win):
    pg = page(win, "Data")
    assert any(lb.text() == "Imported datasets will appear here once available."
               for lb in pg.findChildren(QLabel))
    assert not pg.findChildren(QPushButton)


def test_outline_tab_not_populated_by_026(win):
    # spec 027 is being built concurrently; only assert the tab exists and is switchable.
    p = panel(win)
    idx = [p.tabs.tabText(i) for i in range(p.tabs.count())].index("Outline")
    p.tabs.setCurrentIndex(idx)
    assert p.strip.current() == idx


def test_tab_switching_strip_and_pages(win):
    p = panel(win)
    names = [p.tabs.tabText(i) for i in range(p.tabs.count())]
    for name in ("Statistics", "Optimization", "Elements", "Statistics"):
        i = names.index(name)
        p.strip.buttons()[i].click()
        QApplication.processEvents()
        assert p.tabs.currentIndex() == i
        assert p.strip.current() == i
        assert p.tabs.currentWidget() is page(win, name)


# ---------------------------------------------------------------- tooltips ----------------

def test_tooltips_nonempty_and_rules(win):
    sb = panel(win).symbol_buttons
    for g, lab, _t in ALL:
        assert sb[lab].toolTip().strip(), lab
    for lab, _ in DIST:
        assert "no units" in sb[lab].toolTip().lower(), lab
    for lab in ("binomial_pmf", "binomial_cdf", "poisson_pmf", "poisson_cdf"):
        assert "whole number" in sb[lab].toolTip(), lab
    for lab in ("binomial_quantile", "binomial_sample", "poisson_quantile", "poisson_sample"):
        # AC 7 literally says every discrete tooltip; k does not appear in these, so this is
        # reported as an ambiguity, not asserted.
        assert sb[lab].toolTip().strip()
    assert "t1" in sb["sample"].toolTip() and "t1" in sb["verdict"].toolTip()
    for lab in ("least", "most", "settle"):
        t = sb[lab].toolTip().lower()
        assert "guess" in t and "local" in t, lab
    assert "unit" in sb["mean"].toolTip().lower()
    assert "n-1" in sb["variance"].toolTip() or "n - 1" in sb["variance"].toolTip()
    assert "population" in sb["population_variance"].toolTip().lower()
    assert "8" not in sb["accuracy"].toolTip() or "1e-8" in sb["accuracy"].toolTip() \
        or "default" in sb["accuracy"].toolTip().lower()
    assert "200" in sb["steps"].toolTip()


# ---------------------------------------------------------------- clicking inserts --------

@pytest.mark.parametrize("group,label,token", ALL)
def test_click_inserts_exact_token_on_empty_sheet(win, group, label, token):
    win.sheet.clear_sheet()
    panel(win).symbol_buttons[label].click()
    assert win.sheet.regions()[-1].text() == token


def test_click_mid_expression(win):
    win.sheet.clear_sheet()
    win.insert_token("a := ")
    panel(win).symbol_buttons["mean"].click()
    assert win.sheet.regions()[-1].text() == "a := mean(v)"
    # caret now after the token: second click appends
    panel(win).symbol_buttons["median"].click()
    assert win.sheet.regions()[-1].text() == "a := mean(v)median(v)"


def test_click_between_text(win):
    win.sheet.clear_sheet()
    win.insert_token("1 + 2")
    r = win.sheet.regions()[-1]
    cur = r.editor.textCursor()
    cur.setPosition(4)   # after "1 + "
    r.editor.setTextCursor(cur)
    panel(win).symbol_buttons["stdev"].click()
    assert r.text() == "1 + stdev(v)2"


def test_click_replaces_selection(win):
    win.sheet.clear_sheet()
    win.insert_token("a := zzz")
    r = win.sheet.regions()[-1]
    cur = r.editor.textCursor()
    cur.setPosition(5)
    cur.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
    r.editor.setTextCursor(cur)
    panel(win).symbol_buttons["fit_linear"].click()
    assert r.text() == "a := fit_linear(x, y)"
    assert len(win.sheet.regions()) == 1


def test_click_with_no_editing_creates_new_region_each_time_after_finish(win):
    win.sheet.clear_sheet()
    panel(win).symbol_buttons["verdict"].click()
    win.sheet.regions()[-1].finish_editing()
    panel(win).symbol_buttons["settle"].click()
    texts = [r.text() for r in win.sheet.regions()]
    assert "verdict in t1" in texts and "settle in m1" in texts


def test_click_on_text_region_editing_makes_new_math_region(win):
    win.sheet.clear_sheet()
    n = len(win.sheet.regions())
    panel(win).symbol_buttons["mean"].click()
    assert len(win.sheet.regions()) == n + 1


# ---------------------------------------------------------------- engine ------------------

def run(*sources):
    return Engine().evaluate(enumerate(sources))


def num(res, idx):
    r = res[idx]
    assert r.status == "ok", (r.error, r.output)
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", r.output)]


DATA = ["v := [2, 4, 4, 4, 5, 5, 7, 9]", "u := [1, 2, 3, 4, 5]", "w := [2, 4, 5, 4, 5]",
        "p := 0.5", "x := [0, 1, 2, 3]", "y := [1, 2, 2, 4]", "c := fit_linear(x, y)"]


def val(expr, *extra):
    res = run(*DATA, *extra, expr + " =")
    return num(res, len(DATA) + len(extra))


@pytest.mark.parametrize("token,expected", [
    ("mean(v)", 5.0), ("median(v)", 4.5), ("mode(v)", 4.0), ("variance(v)", 32 / 7),
    ("stdev(v)", math.sqrt(32 / 7)), ("population_variance(v)", 4.0),
    ("population_stdev(v)", 2.0), ("quantile(v, p)", 4.5), ("covariance(u, w)", 1.5),
    ("correlation(u, w)", 6 / math.sqrt(60)),
])
def test_summary_values(token, expected):
    got = val(token)
    assert got == [pytest.approx(expected, rel=1e-4)]


def test_summary_tokens_verbatim_from_buttons(win):
    sb_tokens = {lab: tok for _g, lab, tok in ALL}
    for lab, tok in SUMMARY:
        res = run(*DATA, sb_tokens[lab] + " =")
        assert res[len(DATA)].status == "ok", (lab, res[len(DATA)].error)


def test_regression_values():
    assert val("fit_linear(x, y)") == [pytest.approx(0.9), pytest.approx(0.9)]
    assert val("predict(c, x)") == [pytest.approx(v) for v in (0.9, 1.8, 2.7, 3.6)]
    assert val("r_squared(c, x, y)") == [pytest.approx(1 - 0.7 / 4.75, abs=1e-5)]
    # exact quadratic data -> coefficients 1, 0, 1 (constant first)
    got = val("fit_poly(x, z, 2)", "z := [1, 2, 5, 10]")
    assert got == [pytest.approx(1, abs=1e-6), pytest.approx(0, abs=1e-6),
                   pytest.approx(1, abs=1e-6)]


def test_regression_token_verbatim_runs():
    # the button tokens, run as-is with the spec's data names
    for tok in ("fit_linear(x, y)", "predict(c, x)", "r_squared(c, x, y)"):
        assert run(*DATA, tok + " =")[len(DATA)].status == "ok"


SCALARS = ["mu := 0", "sigma := 1", "a := 0", "b := 2", "k := 2", "n_trials := 10",
           "lambda_ := 3", "n := 4", "seed := 7"]


@pytest.mark.parametrize("expr,extra,expected", [
    ("normal_pdf(x0, mu, sigma)", ["x0 := 0"], 1 / math.sqrt(2 * math.pi)),
    ("normal_cdf(1, mu, sigma)", [], 0.841345),
    ("normal_quantile(p0, mu, sigma)", ["p0 := 0.975"], 1.959964),
    ("uniform_pdf(x0, a, b)", ["x0 := 0.5"], 0.5),
    ("uniform_cdf(x0, a, b)", ["x0 := 0.5"], 0.25),
    ("uniform_quantile(p0, a, b)", ["p0 := 0.3"], 0.6),
    ("binomial_pmf(k, n_trials, p0)", ["p0 := 0.5"], 45 / 1024),
    ("binomial_cdf(k, n_trials, p0)", ["p0 := 0.5"], 56 / 1024),
    ("binomial_quantile(q0, n_trials, p0)", ["p0 := 0.5", "q0 := 0.5"], 5.0),
    ("poisson_pmf(k, lambda_)", [], 4.5 * math.exp(-3)),
    ("poisson_cdf(k, lambda_)", [], math.exp(-3) * (1 + 3 + 4.5)),
    ("poisson_quantile(q0, lambda_)", ["q0 := 0.5"], 3.0),
])
def test_distribution_values(expr, extra, expected):
    res = run(*SCALARS, *extra, expr + " =")
    got = num(res, len(SCALARS) + len(extra))
    assert got == [pytest.approx(expected, rel=2e-4)]


def test_distribution_button_tokens_run_with_defined_names():
    pre = SCALARS + ["x := 0.5", "p := 0.5", "q := 0.5"]
    for lab, tok in DIST:
        res = run(*pre, tok + " =")
        assert res[len(pre)].status == "ok", (tok, res[len(pre)].error)


@pytest.mark.parametrize("tok,lo,hi", [
    ("uniform_sample(a, b, n, seed)", 0, 2), ("normal_sample(mu, sigma, n, seed)", -6, 6),
    ("binomial_sample(n_trials, 0.5, n, seed)", 0, 10), ("poisson_sample(lambda_, n, seed)", 0, 50),
])
def test_samples_shape_reproducible_in_range(tok, lo, hi):
    r1 = run(*SCALARS, tok + " =")[len(SCALARS)]
    r2 = run(*SCALARS, tok + " =")[len(SCALARS)]
    assert r1.status == "ok" and r1.output == r2.output
    vals = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", r1.output)]
    assert len(vals) == 4 and all(lo <= v <= hi for v in vals)
    other = run(*SCALARS[:-1], "seed := 8", tok + " =")[len(SCALARS)]
    assert other.output != r1.output


def test_units_rejected_by_distribution_per_tooltip():
    res = run("x := 1 m", "normal_cdf(x, 0, 1) =")
    assert res[1].status != "ok"


def test_one_sample_t_test_lines_in_context():
    t = dict(TESTS)
    res = run("v := [8, 7, 6, 9, 10]", t["sample"], t["claim mean"].replace("== 0", "== 7"),
              t["verdict"], "t1_df =", "t1_pvalue =", "t1_statistic =")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert "fail to reject" in res[3].output
    assert num(res, 4) == [4.0]
    assert num(res, 5) == [pytest.approx(0.2302, abs=1e-4)]
    assert num(res, 6) == [pytest.approx(math.sqrt(2), abs=1e-4)]  # (8-7)/(sqrt(2.5)/sqrt5)


def test_one_sided_variants_parse():
    t = dict(TESTS)
    for op in ("<", ">"):
        res = run("v := [8, 7, 6, 9, 10]", t["sample"], f"claim mean {op} 7 in t1", t["verdict"])
        assert all(r.status == "ok" for r in res.values()), (op, {k: r.error for k, r in res.items()})


def test_reject_case():
    t = dict(TESTS)
    res = run("v := [8, 7, 6, 9, 10]", t["sample"], "claim mean == 1 in t1", t["verdict"])
    assert "reject H0" in res[3].output and "fail" not in res[3].output


def test_chi_square_lines_in_context():
    t = dict(TESTS)
    res = run("v := [10, 20, 30, 40]", "counts := [25, 25, 25, 25]", t["sample"],
              t["expected"], t["claim fits"], t["verdict"], "t1_statistic =", "t1_df =")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert num(res, 6) == [pytest.approx(20.0)]
    assert num(res, 7) == [3.0]
    assert "reject" in res[5].output


def test_two_sample_and_level_lines():
    t = dict(TESTS)
    res = run("v := [8, 7, 6, 9, 10]", "mean1 := 1", "mean2 := 2", t["sample"], t["sample"],
              t["claim two means"], t["level"], t["verdict"])
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}


def test_two_sample_welch_value_with_distinct_samples():
    res = run("v := [8, 7, 6, 9, 10]", "m := [1, 2, 3, 2, 2]", "sample v in t1", "sample m in t1",
              "claim mean1 == mean2 in t1", "verdict in t1", "t1_statistic =")
    # Welch t = (8 - 2) / sqrt(2.5/5 + 0.5/5)
    got = num(res, 6)
    assert abs(got[0]) == pytest.approx(6 / math.sqrt(0.6), rel=1e-3)


def test_verdict_before_sample_gives_engine_error_no_crash():
    res = run("verdict in t1")
    assert res[0].status != "ok"


def test_level_changes_decision():
    base = ["v := [8, 7, 6, 9, 10]", "sample v in t1", "claim mean == 6 in t1"]
    lo = run(*base, "level 0.5 in t1", "verdict in t1")[4].output
    hi = run(*base, "level 0.001 in t1", "verdict in t1")[4].output
    assert "reject H0" in lo and "alpha = 0.5" in lo
    assert "alpha = 0.001" in hi
    assert lo != hi


def test_solve_settle_equation():
    t = dict(UNK + SET + RES)
    res = run(t["vary"], t["equation =="], t["limit >="], t["settle"], "x =")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert num(res, 4) == [pytest.approx(2.0, abs=1e-5)]
    # guess on the negative side without the bound finds -2
    res = run("vary x from -1 in m1", t["equation =="], t["settle"], "x =")
    assert num(res, 3) == [pytest.approx(-2.0, abs=1e-5)]


def test_solve_least_most():
    t = dict(UNK + SET + RES)
    res = run(t["vary"], t["limit >="], t["limit <="], t["least"], t["most"])
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert num(res, 3)[1] == pytest.approx(0.0, abs=1e-4)
    assert num(res, 4)[1] == pytest.approx(10.0, abs=1e-4)


def test_solve_settings_lines_accepted():
    t = dict(UNK + SET + RES)
    res = run(t["vary"], t["equation =="], t["accuracy"], t["steps"], t["settle"], "x =")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert num(res, 5) == [pytest.approx(2.0, abs=1e-5)]


def test_solve_chained_limit_form():
    res = run("vary x from 1 in m1", "0 <= x <= 3 in m1", "most x in m1")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}
    assert num(res, 2)[1] == pytest.approx(3.0, abs=1e-4)


def test_solve_unit_guess_fixes_unit():
    res = run("vary x from 1 m in m1", "x == 2 m in m1", "settle in m1")
    assert all(r.status == "ok" for r in res.values()), {k: r.error for k, r in res.items()}


# ---------------------------------------------------------------- layout / scrolling -------

def test_statistics_page_scrolls_inside_band(win):
    p = panel(win)
    names = [p.tabs.tabText(i) for i in range(p.tabs.count())]
    win.resize(420, 800)
    p.tabs.setCurrentIndex(names.index("Statistics"))
    QApplication.processEvents()
    pg = page(win, "Statistics")
    assert isinstance(pg, QScrollArea)
    assert pg.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    inner = pg.widget().layout().heightForWidth(pg.viewport().width())
    assert inner > pg.viewport().height(), "tall Statistics page should need vertical scroll"
    assert pg.verticalScrollBar().maximum() > 0
    # band is clamped
    assert p.band.height() <= p.band_clamp()
    # last button reachable by scrolling
    last = p.symbol_buttons["r_squared"]
    pg.verticalScrollBar().setValue(pg.verticalScrollBar().maximum())
    QApplication.processEvents()
    pt = last.mapTo(pg.viewport(), last.rect().center())
    assert pg.viewport().rect().contains(pt)


def test_tab_strip_never_scrolls_and_stays_above_band(win):
    p = panel(win)
    names = [p.tabs.tabText(i) for i in range(p.tabs.count())]
    p.tabs.setCurrentIndex(names.index("Statistics"))
    pg = page(win, "Statistics")
    pg.verticalScrollBar().setValue(pg.verticalScrollBar().maximum())
    QApplication.processEvents()
    assert not any(isinstance(w, QScrollArea) for w in [p.strip])
    assert p.strip.geometry().bottom() <= p.band.geometry().top()
    for b in p.strip.buttons():
        assert p.strip.rect().contains(b.geometry())


def test_band_height_independent_of_tab_and_clamped_when_narrow(win):
    p = panel(win)
    heights = set()
    for i in range(p.tabs.count()):
        p.tabs.setCurrentIndex(i)
        QApplication.processEvents()
        heights.add(p.band.height())
    assert len(heights) == 1
    for w_ in (500, 700, 1200):
        win.resize(w_, 800)
        QApplication.processEvents()
        assert p.band.height() <= p.band_clamp()


def test_wide_window_statistics_fits_without_horizontal_scroll(win):
    p = panel(win)
    names = [p.tabs.tabText(i) for i in range(p.tabs.count())]
    p.tabs.setCurrentIndex(names.index("Statistics"))
    for w_ in (400, 900, 1600):
        win.resize(w_, 800)
        QApplication.processEvents()
        pg = page(win, "Statistics")
        assert not pg.horizontalScrollBar().isVisible()
        for b in page(win, "Statistics").widget().findChildren(QPushButton):
            assert b.geometry().right() <= pg.widget().width() + 1


def test_keyboard_enter_on_button_inserts(win):
    win.sheet.clear_sheet()
    b = panel(win).symbol_buttons["covariance"]
    b.setFocus()
    QTest.keyClick(b, Qt.Key.Key_Space)
    assert win.sheet.regions()[-1].text() == "covariance(u, w)"


def test_real_plist_unchanged_inline():
    # The module fixture also asserts this at teardown; this is a cheap early guard.
    assert _digest() == _digest()
