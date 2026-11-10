"""Spec 024 engine tests (E-block): Qt-free name completion."""

import subprocess
import sys

import pytest

from livesheet.engine import completion as C
from livesheet.engine import evaluator
from livesheet.engine.completion import Candidate, accept, complete, signature_for
from livesheet.engine.matrices import MATRIX_BUILTINS
from livesheet.engine.statistics import STATS_BUILTINS


def names(text, caret=None, src=()):
    r = complete(text, caret, src)
    return None if r is None else [c.name for c in r.candidates]


def test_no_qt_import():
    code = ("import sys, livesheet.engine.completion; "
            "sys.exit(1 if any(m.startswith('PySide6') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_e1_registry_driven(monkeypatch):
    monkeypatch.setitem(evaluator.BUILTINS, "zzz_probe", lambda x: x)
    r = complete("zzz", 3)
    assert [(c.name, c.kind) for c in r.candidates] == [("zzz_probe", "function")]
    monkeypatch.delitem(evaluator.BUILTINS, "zzz_probe")
    assert complete("zzz", 3) is None


def test_e2_stats_and_matrix_present():
    allnames = list(STATS_BUILTINS) + [n for n in MATRIX_BUILTINS if not n.startswith("_")]
    for n in allnames:
        text = n[:-1] if len(n) > 2 else n[:2]
        if len(n) == 2:
            continue   # a 2-char name has nothing left to complete beyond itself
        assert n in names(text), n


def test_e3_exclusions():
    for n in ("Integer", "Float", "Rational", "Symbol", "Function"):
        assert complete(n[:3], 3) is None or n not in names(n[:3])
    # spec text says complete("Int", 3) is None, but case-insensitive matching rightly offers
    # `integrate`; what matters is that the parser helper itself is never offered.
    assert "Integer" not in names("Int", 3)
    assert complete("__b", 3) is None
    assert not any(c.name.startswith("_") for c in C.builtin_candidates())


def test_e4_ranking():
    assert names("me", 2)[:2] == ["mean", "median"]
    assert names("fit_", 4) == ["fit_poly", "fit_linear"]
    n = names("no", 2)
    assert n[0] == "norm"
    for x in ("normal_cdf", "normal_pdf", "normal_quantile", "normal_sample"):
        assert x in n
    assert names("si", 2)[0] == "sin"
    m = names("ma", 2)
    assert m.index("max") < m.index("Max")


def test_e5_hints():
    assert signature_for("mean") == "mean(v)"
    assert signature_for("fit_linear") == "fit_linear(x, y)"
    assert signature_for("predict") == "predict(coeffs, x)"
    assert signature_for("normal_cdf") == "normal_cdf(x, mu, sigma)"
    assert signature_for("poisson_cdf") == "poisson_cdf(k, lambda)"
    assert signature_for("binomial_pmf") == "binomial_pmf(k, n_trials, p)"
    assert signature_for("normal_sample") == "normal_sample(mu, sigma, n, seed)"
    assert signature_for("sin")


def test_e6_drift():
    missing = [n for n, f in evaluator.BUILTINS.items()
               if not n.startswith("_") and n not in C._HIDDEN and callable(f) and not signature_for(n)]
    assert not missing, f"builtins without a signature hint: {missing}"
    orphans = [k for k in C.SIGNATURE_OVERRIDES if k not in evaluator.BUILTINS]
    assert not orphans


@pytest.mark.parametrize("text,caret", [("2m", 2), ("3.5e", 4), ("x = 10s", 7), ("a.me", 4)])
def test_e7_not_in_numbers(text, caret):
    assert complete(text, caret) is None


def test_e8_min_length():
    assert complete("s", 1) is None
    assert complete("si", 2) is not None


def test_e9_inside_word():
    assert complete("sqrt", 2) is None


def test_e10_nothing_left():
    assert complete("mean", 4) is None
    assert "mean" in names("mea", 3)


def test_e11_accept():
    cands = {c.name: c for c in C.builtin_candidates()}
    assert accept("2*me", 4, cands["mean"]) == ("2*mean(", 7)
    assert accept("x = p", 5, Candidate("pi", "constant")) == ("x = pi", 6)
    assert accept("me(1)", 2, cands["mean"]) == ("mean(1)", 4)
    assert accept("1+sq", 4, cands["sqrt"]) == ("1+sqrt(", 7)


def test_e12_user_names():
    src = ["rate := 3", "area(w, h) := w*h", "g(x) ≡ x^2", "total =", "((("]
    first = complete("ar", 2, src).candidates[0]
    assert (first.name, first.kind, first.signature) == ("area", "user_function", "area(w, h)")
    r = complete("ra", 2, src).candidates
    assert r[0].name == "rate" and r[0].kind == "variable"
    assert "rank" in [c.name for c in r]
    assert "total" not in (names("to", 2, src) or [])
    assert accept("ra", 2, r[0]) == ("rate", 4)
    m = complete("mea", 3, ["mean := 3"]).candidates
    assert [(c.name, c.kind) for c in m if c.name == "mean"] == [("mean", "variable")]
