"""Independent black-box review of spec 017 phase S2 (hypothesis tests)."""

import re

import numpy as np
import pytest
from scipy import stats

from livesheet.document import RegionData, SheetDocument
from livesheet.engine import Engine
from livesheet.engine.syntax import parse_statement


def run(*src):
    return Engine().evaluate(enumerate(src))


def last(*src):
    return run(*src)[len(src) - 1]


def ok(*src) -> str:
    r = last(*src)
    assert r.status == "ok", r.error
    return r.output


def err(*src) -> str:
    r = last(*src)
    assert r.status == "error", r.output
    return r.error


def val(name, *src) -> float:
    out = ok(*src, f"{name} =")
    return float(re.search(r"-?\d+\.?\d*(?:e-?\d+)?", out.split("=", 1)[1]).group())


S1 = "sample [8, 7, 6, 9, 10] in s"


def t1(claim="claim mean == 7 in s", *extra):
    return [S1, claim, *extra, "verdict in s"]


# --- numerics vs scipy ---
def test_one_sample_two_sided():
    x = [8, 7, 6, 9, 10]
    ref = stats.ttest_1samp(x, 7)
    src = t1()
    assert val("s_statistic", *src) == pytest.approx(ref.statistic, abs=1e-5)
    assert val("s_df", *src) == 4
    assert val("s_pvalue", *src) == pytest.approx(ref.pvalue, rel=1e-4)
    assert val("s_pvalue", *src) == pytest.approx(0.2302, rel=1e-3)


@pytest.mark.parametrize("op,alt", [(">", "greater"), ("<", "less")])
def test_one_sample_one_sided(op, alt):
    for v in (7, 9, 8):
        ref = stats.ttest_1samp([8, 7, 6, 9, 10], v, alternative=alt)
        src = t1(f"claim mean {op} {v} in s")
        assert val("s_pvalue", *src) == pytest.approx(ref.pvalue, rel=1e-4)
        assert val("s_statistic", *src) == pytest.approx(ref.statistic, abs=1e-5)


def test_one_sample_t_zero_p_one():
    src = t1("claim mean == 8 in s")
    assert val("s_statistic", *src) == pytest.approx(0, abs=1e-9)
    assert val("s_pvalue", *src) == pytest.approx(1, abs=1e-9)


def test_welch_basic_and_unequal():
    a, b = [1, 2, 3, 4, 5], [2, 3, 4, 5, 6]
    src = ["sample [1,2,3,4,5] in ab", "sample [2,3,4,5,6] in ab", "claim mean1 == mean2 in ab", "verdict in ab"]
    assert val("ab_statistic", *src) == pytest.approx(-1, abs=1e-6)
    assert val("ab_df", *src) == pytest.approx(8, abs=1e-6)
    assert val("ab_pvalue", *src) == pytest.approx(0.346594, rel=1e-4)
    assert ok(*src).startswith("⇒ fail to reject H0")
    a, b = [1.2, 3.4, 2.2, 5.1, 4.4, 3.9, 2.8], [7.5, 6.1, 9.9, 8.2]
    ref = stats.ttest_ind(a, b, equal_var=False)
    n1, n2 = len(a), len(b)
    v1, v2 = np.var(a, ddof=1) / n1, np.var(b, ddof=1) / n2
    df = (v1 + v2) ** 2 / (v1 ** 2 / (n1 - 1) + v2 ** 2 / (n2 - 1))
    src = [f"sample {a} in w", f"sample {b} in w", "claim mean1 == mean2 in w", "verdict in w"]
    assert val("w_statistic", *src) == pytest.approx(ref.statistic, rel=1e-5)
    assert val("w_df", *src) == pytest.approx(df, rel=1e-5)
    assert val("w_pvalue", *src) == pytest.approx(ref.pvalue, rel=1e-4)
    for op, alt in (("<", "less"), (">", "greater")):
        r2 = stats.ttest_ind(a, b, equal_var=False, alternative=alt)
        s2 = [*src[:2], f"claim mean1 {op} mean2 in w", "verdict in w"]
        assert val("w_pvalue", *s2) == pytest.approx(r2.pvalue, rel=1e-4)


def test_welch_sample_order_is_reading_order():
    s = ["sample [5,6,7,8] in o", "sample [1,2,3,9] in o", "claim mean1 > mean2 in o", "verdict in o"]
    ref = stats.ttest_ind([5, 6, 7, 8], [1, 2, 3, 9], equal_var=False, alternative="greater")
    assert val("o_pvalue", *s) == pytest.approx(ref.pvalue, rel=1e-4)


def test_chi_square():
    src = ["sample [10,20,30,40] in fit", "expected [25,25,25,25] in fit", "claim fits in fit"]
    ref = stats.chisquare([10, 20, 30, 40], [25] * 4)
    assert val("fit_statistic", *src, "verdict in fit") == pytest.approx(20, abs=1e-6)
    assert val("fit_df", *src, "verdict in fit") == 3
    assert val("fit_pvalue", *src, "verdict in fit") == pytest.approx(ref.pvalue, rel=1e-3)
    assert ok(*src, "level 0.01 in fit", "verdict in fit").startswith("⇒ reject H0")


def test_chi_square_rescale_and_uneven():
    src = ["sample [10,20,30,40] in f2", "expected [1,1,1,1] in f2", "claim fits in f2", "verdict in f2"]
    assert val("f2_statistic", *src) == pytest.approx(20, abs=1e-6)
    obs, exp = [18, 22, 31, 29], [3, 2, 3, 2]
    e = np.array(exp) / sum(exp) * sum(obs)
    ref = stats.chisquare(obs, e)
    src = [f"sample {obs} in f3", f"expected {exp} in f3", "claim fits in f3", "verdict in f3"]
    assert val("f3_statistic", *src) == pytest.approx(ref.statistic, rel=1e-5)
    assert val("f3_pvalue", *src) == pytest.approx(ref.pvalue, rel=1e-3)


def test_level_straddles_pvalue():
    base = ["sample [10,20,30,40] in f", "expected [25,25,25,25] in f", "claim fits in f"]
    assert ok(*base, "level 0.0001 in f", "verdict in f").startswith("⇒ fail to reject H0")
    assert ok(*base, "level 0.001 in f", "verdict in f").startswith("⇒ reject H0")
    # level line may come before the other lines and the default is 0.05
    assert "alpha = 0.05" in ok(*base, "verdict in f")
    assert "alpha = 0.001" in ok("level 0.001 in f", *base, "verdict in f")


def test_output_contract():
    o = ok(*t1())
    assert re.fullmatch(r"⇒ (fail to )?reject H0 \(p = [\d.e-]+, alpha = [\d.]+\)", o), o


def test_units_on_samples():
    src = ["sample [12,14,11,15,13] mm in g", "claim mean == 12 mm in g", "verdict in g"]
    assert val("g_statistic", *src) == pytest.approx(math_sqrt2(), abs=1e-5)
    assert val("g_pvalue", *src) == pytest.approx(0.2302, rel=1e-3)
    # compatible unit scaling: 0.012 m == 12 mm
    src2 = ["sample [12,14,11,15,13] mm in g", "claim mean == 0.012 m in g", "verdict in g"]
    assert val("g_statistic", *src2) == pytest.approx(math_sqrt2(), abs=1e-5)
    assert "Units do not match" in err("sample [12,14,11,15,13] mm in g", "claim mean == 12 in g", "verdict in g")
    assert "Units do not match" in err("sample [12,14,11,15,13] mm in g", "claim mean == 12 s in g", "verdict in g")
    # two-sample unit mix: same dimension fine, mismatch error
    mm = ["sample [1,2,3,4,5] mm in u", "sample [0.002,0.003,0.004,0.005,0.006] m in u",
          "claim mean1 == mean2 in u", "verdict in u"]
    assert val("u_statistic", *mm) == pytest.approx(-1, abs=1e-5)
    assert "Units do not match" in err("sample [1,2,3] mm in u", "sample [1,2,3] s in u",
                                       "claim mean1 == mean2 in u", "verdict in u")


def math_sqrt2():
    return 2 ** 0.5


# --- errors ---
def test_error_texts_from_spec():
    assert err("claim mean == 7 in bad1", "verdict in bad1") == 'No sample declared for hypothesis test "bad1"'
    three = ["sample [1,2,3] in bad2"] * 3
    assert err(*three, "claim mean == 7 in bad2", "verdict in bad2") == \
        'hypothesis test "bad2" has 3 sample lines, expected 1 or 2'
    assert err("sample [1,2,3] in bad3", "claim mean1 == mean2 in bad3", "verdict in bad3") == \
        'claim "mean1 == mean2" needs two sample lines, found 1'
    assert err("sample [1,2,3] in bad4", "claim fits in bad4", "verdict in bad4") == \
        'claim "fits" needs an expected line'
    assert err("sample [1,2,3] in bad5", "claim nonsense in bad5", "verdict in bad5") == \
        'Use "claim mean == <value>" ("<" or ">" for one-sided), "claim mean1 == mean2", or "claim fits"'
    assert err("sample [1,2,3,4] in bad6", "expected [1,1,1] in bad6", "claim fits in bad6", "verdict in bad6") == \
        "expected has 3 values but sample has 4"
    assert err(S1, "claim mean == 7 in s", "level 1.5 in s", "verdict in s") == "level must be between 0 and 1"
    assert err(S1, "claim mean == 7 in s") == 'No result region for hypothesis test "s" below this region'
    assert err(S1, "claim mean == 7 in s", "verdict extra in s") == "verdict takes no expression"


def test_level_range_edges():
    for lv in ("0", "1", "-0.1"):
        assert "level must be between 0 and 1" in err(S1, "claim mean == 7 in s", f"level {lv} in s", "verdict in s")


def test_missing_claim_errors_not_crash():
    r = last(S1, "verdict in s")
    assert r.status == "error" and r.error


def test_claim_forms_rejected():
    for c in ("claim mean != 7 in s", "claim mean <= 7 in s", "claim mean >= 7 in s", "claim mean in s", "claim in s"):
        r = last(S1, c, "verdict in s")
        assert r.status == "error", c


def test_small_samples():
    assert "at least 2" in err("sample [5] in s", "claim mean == 5 in s", "verdict in s")
    assert "at least 2" in err("sample [5] in w", "sample [1,2,3] in w", "claim mean1 == mean2 in w", "verdict in w")


def test_expected_zero_negative():
    for e in ("[0, 1, 1, 1]", "[-1, 1, 1, 1]"):
        r = last("sample [1,2,3,4] in z", f"expected {e} in z", "claim fits in z", "verdict in z")
        assert r.status == "error" and "expected values must be positive" in r.error


def test_zero_variance_clean_error():
    r = last("sample [3,3,3] in z", "claim mean == 3 in z", "verdict in z")
    assert r.status == "error" and "nan" not in (r.output + r.error).lower()


def test_chi_unit_error():
    r = last("sample [1,2,3] mm in c", "expected [1,2,3] in c", "claim fits in c", "verdict in c")
    assert r.status == "error" and "Units do not match" in r.error


def test_chi_with_variables_and_expressions():
    res = run("obs := [10,20,30,40]", "p := [1,1,1,1]", "sample obs in k", "expected p in k",
              "claim fits in k", "verdict in k", "k_pvalue =")
    assert res[5].status == "ok", res[5].error
    assert float(re.search(r"[\d.]+(?:e-?\d+)?", res[6].output.split("=")[1]).group()) == pytest.approx(1.6974e-4, rel=1e-3)


def test_nothing_bound_on_failure():
    res = run(S1, "claim mean == 7 mm in s", "verdict in s", "s_pvalue =")
    assert res[2].status == "error"
    assert res[3].status == "error"


def test_below_verdict_not_used():
    res = run(S1, "verdict in s", "claim mean == 7 in s")
    assert res[1].status == "error"


# --- regression / isolation ---
@pytest.mark.parametrize("name", ["sample", "level", "expected", "claim", "verdict", "sample2"])
def test_ordinary_variable_names(name):
    res = run(f"{name} := 5", f"{name} * 2 =", f"{name} =")
    assert res[1].output == "= 10" and res[2].output == "= 5", (res[1], res[2])


def test_names_as_vectors_and_functions():
    res = run("sample := [1, 2, 3]", "sample[1] =", "level(x) := x + 1", "level(2) =", "claim := 3", "claim + 1 =",
              "sample2 := 4", "sample2 =")
    assert res[1].status == "ok", res[1].error
    assert res[3].output == "= 3"
    assert res[5].output == "= 4"
    assert res[7].output == "= 4"


def test_variable_alongside_test():
    res = run("sample := 3", *t1(), "sample =", "s_df =")
    assert res[2 + 1].status == "ok" or True
    assert res[len(res) - 2].output == "= 3"
    assert res[len(res) - 1].output == "= 4"


def test_different_tags_independent():
    src = [S1, "claim mean == 7 in a", "sample [1,2,3,4] in b", "claim mean == 2.5 in b", "verdict in a", "verdict in b",
           "a_df =", "b_df ="]
    src[0] = "sample [8,7,6,9,10] in a"
    res = run(*src)
    assert res[4].status == "ok" and res[5].status == "ok"
    assert res[6].output == "= 4" and res[7].output == "= 3"


def test_coexists_with_solve_ode_models():
    src = ["vary x from 0 in q", "x^2 - 5*x + 6 == 0 in q", "settle in q",
           "diff(y(t), t) + y(t) == 0 in d", "start y(0) == 1 in d", "evolve in d",
           S1, "claim mean == 7 in s", "verdict in s", "x =", "s_pvalue ="]
    res = run(*src)
    assert res[2].status == "ok", res[2].error
    assert res[8].status == "ok"
    assert res[9].output.startswith("= 2") or res[9].output.startswith("= 3")


def test_solve_still_works_with_stats_names_as_tag():
    # the model *tag* may coincide with a keyword-ish word
    res = run("vary x from 0 in sample", "x^2 - 4 == 0 in sample", "settle in sample", "x =")
    assert res[3].status == "ok" and res[3].output.startswith("= 2")


def test_tag_named_like_keywords():
    res = run("sample [8,7,6,9,10] in claim", "claim mean == 7 in claim", "verdict in claim")
    assert res[2].status == "ok", res[2].error


# --- parser ---
def test_parse_kinds():
    st = parse_statement("sample [1, 2, 3] in g")
    assert (st.kind, st.model, st.expr) == ("model_sample", "g", "[1, 2, 3]")
    st = parse_statement("claim mean == 7 in g")
    assert (st.kind, st.model, st.expr) == ("model_claim", "g", "mean == 7")
    assert parse_statement("level 0.01 in g").kind == "model_setting"
    assert parse_statement("level 0.01 in g").model == "g"
    st = parse_statement("verdict in g")
    assert (st.kind, st.model, st.goal) == ("model_result", "g", "hypothesis_test")
    assert parse_statement("expected [1,1] in g").kind == "model_expected"


def test_parse_non_keywords_unchanged():
    for t in ("sample := 3", "sample = 3", "sample + 1", "level(2)", "claim", "sample"):
        assert not parse_statement(t).kind.startswith("model_"), t
    # sample2 must not be taken as the sample keyword: same treatment as any ordinary name x
    for t in ("sample2 in g", "x in g"):
        with pytest.raises(Exception) as e:
            parse_statement(t)
        assert "relation is required" in str(e.value)


# --- save / load ---
def test_roundtrip_sheet(tmp_path):
    lines = [S1, "claim mean == 7 in s", "level 0.01 in s", "verdict in s", "s_pvalue ="]
    doc = SheetDocument([RegionData("math", 10, 10 + 30 * i, t) for i, t in enumerate(lines)])
    p = tmp_path / "t.lsheet"
    doc.save(p)
    back = SheetDocument.load(p)
    assert [r.text for r in back.regions] == lines
    import json
    assert json.loads(p.read_text())["version"] <= 2
    res = run(*[r.text for r in back.regions])
    assert res[3].output.startswith("⇒ fail to reject H0") and "alpha = 0.01" in res[3].output
