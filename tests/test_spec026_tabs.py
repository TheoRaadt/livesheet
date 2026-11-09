"""Spec 026: Statistics and Optimization side-panel tabs (data-only), plus engine round trips of
every inserted token."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from livesheet.engine import Engine  # noqa: E402
from livesheet.gui.sidepanel import MATH_TOKENS, PLACEHOLDER_TABS, TAB_CATEGORIES, TAB_ORDER  # noqa: E402

STAT_GROUPS = {"Summary statistics": 10, "Distributions": 16, "Hypothesis tests": 7,
               "Regression": 4}
OPT_GROUPS = {"Unknowns and constraints": 4, "Settings (optional)": 2, "Results": 3}


def rows(cat):
    return [r for r in MATH_TOKENS if r[0] == cat]


def tok(label):
    return next(r[2] for r in MATH_TOKENS if r[1] == label)


def ev(*sources):
    res = Engine().evaluate(enumerate(sources))
    return res


def last(*sources):
    return ev(*sources)[len(sources) - 1]


def test_structure():
    assert tuple(TAB_CATEGORIES["Statistics"]) == tuple(STAT_GROUPS)
    assert tuple(TAB_CATEGORIES["Optimization"]) == tuple(OPT_GROUPS)
    assert set(PLACEHOLDER_TABS) == {"Outline", "Data"}
    assert len(TAB_ORDER) == 10
    for g, n in {**STAT_GROUPS, **OPT_GROUPS}.items():
        assert len(rows(g)) == n
    labels = [r[1] for r in MATH_TOKENS]
    assert len(labels) == len(set(labels))


def test_tooltips():
    for g in list(STAT_GROUPS) + list(OPT_GROUPS):
        assert all(r[3].strip() for r in rows(g))
    for r in rows("Distributions"):
        assert "no units" in r[3]
        if r[1].startswith(("binomial", "poisson")) and r[1].endswith(("pmf", "cdf")):
            assert "whole number" in r[3]


def test_gui_insert(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from livesheet.gui import main_window as mw

    ini = str(tmp_path / "s.ini")
    monkeypatch.setattr(mw, "QSettings",
                        lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat))
    QApplication.instance() or QApplication([])
    win = mw.MainWindow()
    win.sheet.set_modified(False)
    win.side_panel.symbol_buttons["fit_linear"].click()
    assert win.sheet.regions()[-1].text() == "fit_linear(x, y)"
    win.sheet.clear_sheet()
    win.insert_token("a := ")
    win.side_panel.symbol_buttons["mean"].click()
    assert win.sheet.regions()[-1].text() == "a := mean(v)"
    win.sheet.set_modified(False)
    win.close()


DATA = ["v := [2, 4, 4, 4, 5, 5, 7, 9]", "u := [1, 2, 3, 4, 5]", "w := [2, 4, 5, 4, 5]",
        "p := 0.5", "x := [0, 1, 2, 3]", "y := [1, 2, 2, 4]", "c := fit_linear(x, y)",
        "mu := 0", "sigma := 1", "a := 0", "b := 1", "k := 2", "n_trials := 10", "q := 0.5",
        "lambda_ := 3", "n := 3", "seed := 1", "n_x := 0"]


@pytest.mark.parametrize("label", [r[1] for r in rows("Summary statistics") + rows("Regression")
                                   + rows("Distributions")])
def test_tokens_evaluate(label):
    token = tok(label)
    if label == "mode":
        pass
    data = DATA + ["x := 0.5"] if label.startswith(("normal", "uniform")) and "sample" not in label \
        and "quantile" not in label else DATA
    if label.startswith(("normal", "uniform")) and "quantile" in label:
        data = DATA + ["p := 0.5"]
    res = last(*data, token + " =")
    assert res.status == "ok", (token, res.error)


def test_known_values():
    assert last(*DATA, "mean(v) =").output.strip().endswith("5")
    assert "4.5" in last(*DATA, "quantile(v, p) =").output
    assert "0.852632" in last(*DATA, "r_squared(c, x, y) =").output
    assert "0.841345" in last(*DATA, "normal_cdf(1, mu, sigma) =").output


def test_hypothesis_tokens():
    s, e, m, v = tok("sample"), tok("expected"), tok("claim mean"), tok("verdict")
    r = ev("v := [8, 7, 6, 9, 10]", s, m.replace("0", "7"), v, "t1_df =", "t1_pvalue =")
    assert all(x.status == "ok" for x in r.values()), r
    assert "4" in r[4].output and "0.2302" in r[5].output
    r = ev("v := [10, 20, 30, 40]", "counts := [25, 25, 25, 25]", s, e, tok("claim fits"), v,
           "t1_statistic =")
    assert all(x.status == "ok" for x in r.values()), r
    assert "20" in r[6].output
    r = ev("v := [8, 7, 6, 9, 10]", "mean1 := 1", "mean2 := 2", s, s, tok("claim two means"),
           tok("level"), v)
    assert all(x.status == "ok" for x in r.values()), {k: x.error for k, x in r.items()}


def test_solve_tokens():
    r = ev(tok("vary"), tok("equation =="), tok("limit >="), tok("settle"), "x =")
    assert all(x.status == "ok" for x in r.values()), {k: x.error for k, x in r.items()}
    assert "2" in r[4].output
    r = ev(tok("vary"), tok("limit >="), tok("limit <="), tok("accuracy"), tok("steps"),
           tok("least"), "x =")
    assert all(x.status == "ok" for x in r.values()), {k: x.error for k, x in r.items()}
    r = ev(tok("vary"), tok("limit >="), tok("limit <="), tok("most"))
    assert all(x.status == "ok" for x in r.values()), {k: x.error for k, x in r.items()}
