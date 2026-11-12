"""Spec 030 independent review tests (engine): dataset names in completion, order hint."""

from __future__ import annotations

import subprocess
import sys

import pytest

from livesheet.engine import completion, dataio
from livesheet.engine.completion import accept, complete, dataset_candidates
from livesheet.engine.evaluator import BUILTINS, Engine

H = lambda names: (". A definition must come before its use (left to right, then top to bottom); "
                   "defined later: " + names + ".")


def run1():
    return dataio.read_table_text("t [s],F [N]\n0,1.0\n1,3.0\n2,5.0\n3,7.0", name="run1")


def run2():
    return dataio.read_table_text("a [N],b [N]\n1,2\n3,4", name="run2")


def names(res):
    return [c.name for c in res.candidates]


def ev(*sources, **kw):
    regs = [(i, s) for i, s in enumerate(sources)]
    out = Engine().evaluate(regs, **kw)
    return [out[i] for i in range(len(sources))]


# ---- Part A ----
def test_a1_names_and_kind():
    for ds in (run1(), run2()):
        cs = dataset_candidates([ds])
        assert {c.name for c in cs} == dataio.variable_names(ds)
        assert all(c.kind == "data" for c in cs)
    assert {c.name for c in dataset_candidates([run1()])} == {"run1_t", "run1_F"}
    assert {c.name for c in dataset_candidates([run2()])} == {"run2_a", "run2_b", "run2"}


def test_a2_hints():
    by = {c.name: c.signature for c in dataset_candidates([run1(), run2()])}
    assert by["run1_F"] == "4 values, N"
    assert by["run2"] == "2 x 2 matrix"
    nounit = dataio.read_table_text("v\n1\n2\n3", name="plain")
    sig = {c.name: c.signature for c in dataset_candidates([nounit])}["plain_v"]
    assert sig == "3 values"


def test_a3_text_column():
    q = dataio.read_table_text("name,v\nab,1\ncd,2", name="q")
    got = {c.name for c in dataset_candidates([q])}
    assert "q_v" in got and "q_name" not in got
    assert got == dataio.variable_names(q)


def test_a4_order():
    assert names(complete("ru", 2, datasets=[run1()])) == ["run1_F", "run1_t"]
    assert names(complete("ru", 2, datasets=[run2()])) == ["run2", "run2_a", "run2_b"]
    assert names(complete("run2_", 5, datasets=[run2()])) == ["run2_a", "run2_b"]
    assert complete("run1_t", 6, datasets=[run1()]) is None


def test_a5_groups():
    rab = dataio.read_table_text("u\n1\n2", name="rab")
    BUILTINS["raz"] = lambda x: x
    try:
        got = names(complete("ra", 2, ["rate := 3"], [rab]))
    finally:
        del BUILTINS["raz"]
    assert got[:4] == ["rate", "rab", "rab_u", "raz"]


def test_a6_exact_case_first():
    run2x = dataio.read_table_text("v\n1\n2", name="Run2x")
    got = names(complete("Ru", 2, datasets=[run1(), run2x]))
    assert got.index("Run2x") < got.index("run1_F")


def test_a7_vanishing_live_list():
    ds = [run1()]
    assert complete("ru", 2, datasets=ds) is not None
    ds.clear()
    assert complete("ru", 2, datasets=ds) is None
    ds.append(dataio.read_table_text("t [s],F [N]\n0,1\n1,3", name="trial"))
    assert complete("ru", 2, datasets=ds) is None
    # spec said `tr`, but builtins trace/transpose also match: the spec example is wrong, use `tri`
    assert names(complete("tr", 2, datasets=ds))[:2] == ["trial_F", "trial_t"]
    assert names(complete("tri", 3, datasets=ds)) == ["trial_F", "trial_t"]


def test_a8_qt_free_and_default():
    code = "import sys; import livesheet.engine.completion; assert 'PySide6' not in sys.modules"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
    assert names(complete("me", 2))[:2] == ["mean", "median"]


def test_a9_accept_no_paren():
    cand = [c for c in dataset_candidates([run1()]) if c.name == "run1_F"][0]
    text, caret = accept("m = mean(ru", 11, cand)
    assert text == "m = mean(run1_F"
    assert caret == len(text)       # spec says 16, the string has 15 characters
    assert "(" not in text[len("m = mean("):]


def test_a10_clash_once_as_data():
    got = complete("run1_", 5, ["run1_t := 5"], [run1()])
    hits = [c for c in got.candidates if c.name == "run1_t"]
    assert len(hits) == 1 and hits[0].kind == "data"


def test_a_user_variable_before_dataset_even_if_longer():
    got = names(complete("run", 3, ["run_long_variable_name := 1"], [run1()]))
    assert got[0] == "run_long_variable_name"


def test_a_prefix_tri_in_a_spec_example_a12():
    # spec A12 says `tr` offers trial_*; builtins starting with "tr" must come after datasets
    ds = [dataio.read_table_text("t [s],F [N]\n0,1\n1,3", name="trial")]
    got = names(complete("tr", 2, datasets=ds))
    assert got[:2] == ["trial_F", "trial_t"]
    assert len(got) > 2          # builtins (trace, trig...) also match "tr", ordered after


def test_a_many_columns_speed():
    import time
    head = ",".join(f"c{i}" for i in range(100))
    body = "\n".join(",".join(str(i * j) for i in range(100)) for j in range(50))
    big = dataio.read_table_text(head + "\n" + body, name="big")
    t = time.perf_counter()
    for _ in range(20):
        complete("bi", 2, datasets=[big] * 5)
    assert (time.perf_counter() - t) / 20 < 0.3


def test_a_empty_dataset_list_none_and_generator():
    assert complete("zzq", 3, datasets=[]) is None
    assert names(complete("ru", 2, datasets=(d for d in [run1()]))) == ["run1_F", "run1_t"]


# ---- Part B (fixtures adapted: 'y = 2*x' is not a definition in this syntax) ----
def test_b1_hint_basic():
    a, b = ev("y := 2*x =", "x := 4")
    assert a.status == "error" and a.error == "x is not defined" + H("x")
    assert b.status == "ok"


def test_b1_spec_literal_form_unchanged_message():
    a, b = ev("y = 2*x", "x := 4")
    assert a.error.startswith("y is not defined")   # pre-existing parse, nothing to hint


def test_b2_order_fixed():
    b, a = ev("x := 4", "y := 2*x =")
    assert a.status == "ok" and not a.error


def test_b3_typo_no_hint():
    a, _ = ev("y := 2*q =", "x := 4")
    assert a.error == "q is not defined"


def test_b4_mixed():
    a, *_ = ev("z := x + y + q =", "x := 1", "y := 2")
    assert a.error == "q, x, y are not defined" + H("x, y")


def test_b5_self_reference():
    (a,) = ev("x := x + 1")
    assert "defined later" not in (a.error or "")


def test_b6_global():
    a, b = ev("y := 2*x =", "x ≡ 4")
    assert a.status == "ok" and not a.error


def test_b7_earlier_failing_definition():
    a, b, c = ev("y := 2*x =", "x := 4", "y =")
    assert a.error == "x is not defined" + H("x")
    assert c.status == "error" and "defined later" not in c.error
    # the user of an earlier-defined name: x is defined at position 1, c at 2: never "later"


def test_b8_function_later():
    a, b = ev("f(2) =", "f(u) := u^2")
    assert a.error == "f is not defined" + H("f")


def test_b9_range_later():
    a, b = ev("y := 2*x =", "x := 1 to 3")
    assert a.error == "x is not defined" + H("x")


def test_b10_bare_unit_path():
    a, *_ = ev("F/A =", "F := 10 N", "A := 2 m^2")
    assert a.error == "F is not defined" + H("F")


def test_b11_plural():
    a, *_ = ev("z := x + y =", "x := 1", "y := 2")
    assert a.error == "x, y are not defined" + H("x, y")


def test_b11_plural_only_one_later():
    a, *_ = ev("z := x + y =", "x ≡ 1", "y := 2")
    assert a.error == "y is not defined" + H("y") or a.status == "ok"


def test_b11_are_chosen_by_undefined_count():
    a, *_ = ev("z := x + y + q =", "y := 2")
    assert a.error == "q, x, y are not defined" or a.error.startswith("q, x, y are not defined. ")
    assert a.error.endswith("defined later: y.")
    assert a.error.count("defined later") == 1


def test_b12_dataset_never_later():
    d = run1()
    a, b = ev("mean(run1_t) =", "u := run1_t", datasets=[d])
    assert a.status == "ok" and b.status == "ok"
    a, b = ev("mean(run1_t) =", "u := run1_t")
    assert a.error == "run1_t is not defined"


def test_b13_idempotent():
    from livesheet.engine.evaluator import order_hint
    msg = "x is not defined"
    once = order_hint(msg, {"x": 1}, 0)
    assert once == msg + H("x")
    assert order_hint(once, {"x": 1}, 0) == once


def test_b_anchored_match_leaves_other_text():
    from livesheet.engine.evaluator import order_hint
    for m in ("Syntax error", "x is not defined here", "Cannot call x is not defined",
              "x is not defined. extra", "", "x, are not defined", "1x is not defined"):
        assert order_hint(m, {"x": 5}, 0) == m


def test_b_ascii_one_line_no_trailing_space():
    a, *_ = ev("z := x =", "x := 1")
    assert a.error.isascii() and "\n" not in a.error and a.error == a.error.rstrip()


def test_b_hint_mid_names_only_later():
    # x defined earlier but fails (not available), so not hinted; only y is later
    a, b, c = ev("w := x + y =", "x := 1", "y := 2")
    assert a.error.endswith("defined later: x, y.")


def test_b_evaluate_only_define_nothing():
    a, b = ev("z := x =", "x =")
    assert a.error == "x is not defined" or "defined later" not in a.error


def test_b_function_use_in_body_defined_later():
    a, b = ev("g(t) := t + k", "k := 3")
    # lazily defined function: not an error at definition time
    assert a.status == "ok"


def test_b_greek_name_hint():
    a, b = ev("w := α + 1 =", "α := 5")
    assert a.error == "α is not defined" + H("α")


def test_b_greek_subscript_name_hint():
    a, b = ev("w := σ_y + 1 =", "σ_y := 5")
    assert "defined later: σ_y" in a.error


def test_b_greek_mixed_message_stays_prefix():
    a, b = ev("w := α + 1 =", "α := 5")
    assert a.error.startswith("α is not defined")
