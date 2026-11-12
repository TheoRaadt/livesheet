"""Spec 030: dataset names in completion (A) and the evaluation-order hint (B)."""

from __future__ import annotations

import subprocess
import sys

import pytest

from livesheet.engine import dataio
from livesheet.engine.completion import Candidate, accept, complete, dataset_candidates
from livesheet.engine.evaluator import BUILTINS, Engine

HINT = "{msg}. A definition must come before its use (left to right, then top to bottom); defined later: {names}."


def ds(text, name):
    return dataio.read_table_text(text, name=name)


@pytest.fixture
def run1():
    return ds("t [s],F [N]\n0,1.0\n1,3.0\n2,5.0\n3,7.0", "run1")


@pytest.fixture
def run2():
    return ds("a [N],b [N]\n1,2\n3,4", "run2")


def names(res):
    return [c.name for c in res.candidates]


def test_names_and_kinds(run1, run2):
    for d, expect in ((run1, {"run1_t", "run1_F"}), (run2, {"run2_a", "run2_b", "run2"})):
        cands = dataset_candidates([d])
        assert {c.name for c in cands} == expect == dataio.variable_names(d)
        assert all(c.kind == "data" for c in cands)


def test_hints(run1, run2):
    by = {c.name: c.signature for c in dataset_candidates([run1, run2])}
    assert "4 values" in by["run1_F"] and "N" in by["run1_F"]
    assert by["run2"] == "2 x 2 matrix"
    plain = ds("v\n1\n2", "p")
    assert dataset_candidates([plain])[0].signature == "2 values"


def test_text_column():
    q = ds("name,v\nab,1\ncd,2", "q")
    assert {c.name for c in dataset_candidates([q])} == {"q_v", "q"}


def test_order(run1, run2):
    assert names(complete("ru", 2, datasets=[run1])) == ["run1_F", "run1_t"]
    assert names(complete("ru", 2, datasets=[run2])) == ["run2", "run2_a", "run2_b"]
    assert names(complete("run2_", 5, datasets=[run2])) == ["run2_a", "run2_b"]
    assert complete("run1_t", 6, datasets=[run1]) is None


def test_groups():
    rab = ds("u\n1\n2", "rab")
    BUILTINS["raz"] = lambda x: x
    try:
        got = names(complete("ra", 2, ["rate := 3"], [rab]))
    finally:
        del BUILTINS["raz"]
    assert got[:4] == ["rate", "rab", "rab_u", "raz"]


def test_exact_case_first(run1):
    r = ds("v\n1", "Run2x")
    assert names(complete("Ru", 2, datasets=[run1, r]))[0] == "Run2x"


def test_vanishing(run1):
    lst = [run1]
    assert complete("ru", 2, datasets=lst) is not None
    lst.remove(run1)
    assert complete("ru", 2, datasets=lst) is None
    lst.append(ds("t [s],F [N]\n0,1\n1,2", "trial"))
    assert complete("ru", 2, datasets=lst) is None
    assert names(complete("tri", 3, datasets=lst)) == ["trial_F", "trial_t"]


def test_accept_no_paren(run1):
    cand = next(c for c in dataset_candidates([run1]) if c.name == "run1_F")
    assert accept("m = mean(ru", 11, cand) == ("m = mean(run1_F", 15)


def test_clash(run1):
    res = complete("run1_", 5, ["run1_t := 5"], [run1])
    assert names(res).count("run1_t") == 1
    assert next(c for c in res.candidates if c.name == "run1_t").kind == "data"


def test_qt_free():
    out = subprocess.run([sys.executable, "-c",
                          "import sys, livesheet.engine.completion; print('PySide6' in sys.modules)"],
                         capture_output=True, text=True)
    assert out.stdout.strip() == "False"


# ---- Part B ---------------------------------------------------------------------------------

def ev(*sources, datasets=None):
    keys = [chr(97 + i) for i in range(len(sources))]
    return Engine().evaluate(list(zip(keys, sources)), datasets)


def test_b1_b2():
    r = ev("y := 2*x =", "x := 4")
    assert r["a"].error == HINT.format(msg="x is not defined", names="x")
    assert r["b"].status == "ok"
    r = ev("x := 4", "y := 2*x =")
    assert r["b"].status == "ok" and r["b"].error == ""


def test_b3_typo_and_b5_self():
    assert ev("y := 2*q =", "x := 4")["a"].error == "q is not defined"
    assert ev("x := x + 1 =")["a"].error == "x is not defined"


def test_b4_b11_plural():
    r = ev("z := x + y + q =", "x := 1", "y := 2")
    assert r["a"].error == HINT.format(msg="q, x, y are not defined", names="x, y")
    r = ev("z := x + y =", "x := 1", "y := 2")
    assert r["a"].error == HINT.format(msg="x, y are not defined", names="x, y")


def test_b6_global():
    r = ev("y := 2*x =", "x ≡ 4")
    assert r["a"].status == "ok" and "8" in r["a"].output


def test_b7_earlier_failing():
    r = ev("y := 2*x =", "x := 4", "y =")
    assert r["a"].error == HINT.format(msg="x is not defined", names="x")
    assert r["c"].error and "defined later" not in r["c"].error


def test_b8_function():
    r = ev("f(2) =", "f(u) := u^2")
    assert r["a"].error == HINT.format(msg="f is not defined", names="f")


def test_b9_range():
    r = ev("y := 2*x =", "x := 1 to 3")
    assert r["a"].status == "error" and "defined later: x." in r["a"].error


def test_b10_bare_unit():
    r = ev("F/A =", "F := 10 N", "A := 2 m^2")
    assert r["a"].error == HINT.format(msg="F is not defined", names="F")


def test_b12_dataset_not_later(run1):
    assert ev("mean(run1_t) =", datasets=[run1])["a"].status == "ok"
    r = ev("mean(run1_t) =", "z = run1_t")
    assert r["a"].error == "run1_t is not defined"


def test_b13_no_double():
    from livesheet.engine.evaluator import order_hint
    once = order_hint("x is not defined", {"x": 5}, 0)
    assert once != "x is not defined"
    assert order_hint(once, {"x": 5}, 0) == once
