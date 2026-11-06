"""Spec 017 phase S2: hypothesis tests (one-sample t, Welch t, chi-square fit).

Criterion numbers refer to docs/board/specs/017-statistics-core.md, S2. The p-values are
cross-checked against scipy.stats directly (the manager re-ran the same values on 2026-11-06).
"""

import math
import re

import pytest
from scipy import stats

from livesheet.engine import Engine, parse_statement


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def num(output: str) -> float:
    return float(re.search(r"-?\d+\.?\d*(?:e-?\d+)?", output.replace("×10", "e")).group(0))


def value(lines, name):
    """Numeric value of a bound result name after the given model lines."""
    return num(last(*lines, f"{name} =").output)


S1 = ["sample [8, 7, 6, 9, 10] in s1", "claim mean == 7 in s1", "verdict in s1"]
AB = ["sample [1, 2, 3, 4, 5] in ab", "sample [2, 3, 4, 5, 6] in ab",
      "claim mean1 == mean2 in ab", "verdict in ab"]
FIT = ["sample [10, 20, 30, 40] in fit", "expected [25, 25, 25, 25] in fit",
       "claim fits in fit"]


# -- 1-2 one-sample --------------------------------------------------------------------

def test_one_sample_values():
    assert value(S1, "s1_statistic") == pytest.approx(math.sqrt(2), abs=1e-3)
    assert value(S1, "s1_df") == 4
    expected = 2 * stats.t.sf(math.sqrt(2), 4)
    assert expected == pytest.approx(1 - 4 / (3 * math.sqrt(3)))
    assert value(S1, "s1_pvalue") == pytest.approx(0.2302, rel=1e-3)


def test_one_sample_level_decision():
    res = run(S1[0], S1[1], "level 0.05 in s1", S1[2])
    assert res[-1].output.startswith("⇒ fail to reject H0")
    assert "alpha = 0.05" in res[-1].output


def test_default_alpha_is_five_percent():
    assert "alpha = 0.05" in last(*S1).output


def test_one_sided():
    lines = ["sample [8, 7, 6, 9, 10] in s1b", "claim mean > 7 in s1b", "verdict in s1b"]
    assert value(lines, "s1b_statistic") == pytest.approx(math.sqrt(2), abs=1e-3)
    assert value(lines, "s1b_pvalue") == pytest.approx(0.1151, rel=1e-3)
    less = ["sample [8, 7, 6, 9, 10] in s1c", "claim mean < 7 in s1c", "verdict in s1c"]
    assert value(less, "s1c_pvalue") == pytest.approx(1 - 0.1151, rel=1e-3)


def test_claim_equal_to_mean_gives_p_one():
    lines = ["sample [8, 7, 6, 9, 10] in z", "claim mean == 8 in z", "verdict in z"]
    assert value(lines, "z_statistic") == 0
    assert value(lines, "z_pvalue") == pytest.approx(1)
    assert last(*lines).output.startswith("⇒ fail to reject H0")


# -- 3 units ---------------------------------------------------------------------------

def test_units():
    lines = ["sample [12, 14, 11, 15, 13] mm in gauge", "claim mean == 12 mm in gauge",
             "verdict in gauge"]
    assert last(*lines).output == "⇒ fail to reject H0 (p = 0.2302, alpha = 0.05)"
    assert value(lines, "gauge_statistic") == pytest.approx(math.sqrt(2), abs=1e-3)
    assert value(lines, "gauge_pvalue") == pytest.approx(0.2302, rel=1e-3)


def test_unit_mismatch():
    res = last("sample [12, 14, 11, 15, 13] mm in gauge2", "claim mean == 12 in gauge2",
               "verdict in gauge2")
    assert res.status == "error" and "Units do not match" in res.error


def test_two_sample_unit_mismatch():
    res = last("sample [1, 2, 3] mm in u", "sample [1, 2, 3] s in u", "claim mean1 == mean2 in u",
               "verdict in u")
    assert res.status == "error" and "Units do not match" in res.error


# -- 4 Welch ---------------------------------------------------------------------------

def test_welch():
    assert value(AB, "ab_statistic") == pytest.approx(-1, abs=1e-3)
    assert value(AB, "ab_df") == pytest.approx(8, abs=1e-3)
    assert value(AB, "ab_pvalue") == pytest.approx(2 * stats.t.sf(1, 8), rel=1e-3)
    assert value(AB, "ab_pvalue") == pytest.approx(0.346594, rel=1e-3)
    assert last(*AB).output.startswith("⇒ fail to reject H0")


def test_welch_unequal_variances_matches_scipy():
    a, b = [1.0, 2.0, 4.0, 8.0, 9.0], [3.0, 3.5, 4.0, 4.5]
    lines = [f"sample {a} in w", f"sample {b} in w", "claim mean1 == mean2 in w", "verdict in w"]
    ref = stats.ttest_ind(a, b, equal_var=False)
    assert value(lines, "w_statistic") == pytest.approx(ref.statistic, rel=1e-4)
    assert value(lines, "w_pvalue") == pytest.approx(ref.pvalue, rel=1e-3)
    assert value(lines, "w_df") == pytest.approx(ref.df, rel=1e-4)


def test_welch_one_sided():
    lines = ["sample [5, 6, 7, 8] in w", "sample [1, 2, 3, 4] in w", "claim mean1 > mean2 in w",
             "verdict in w"]
    ref = stats.ttest_ind([5, 6, 7, 8], [1, 2, 3, 4], equal_var=False, alternative="greater")
    assert value(lines, "w_pvalue") == pytest.approx(ref.pvalue, rel=1e-3)
    assert last(*lines).output.startswith("⇒ reject H0")


def test_sample_order_is_reading_order():
    swapped = [AB[1], AB[0], *AB[2:]]
    assert value(swapped, "ab_statistic") == pytest.approx(1, abs=1e-3)


# -- 5-7 chi-square --------------------------------------------------------------------

def test_chi_square():
    lines = [*FIT, "level 0.01 in fit", "verdict in fit"]
    assert value(lines, "fit_statistic") == pytest.approx(20, abs=1e-3)
    assert value(lines, "fit_df") == 3
    assert value(lines, "fit_pvalue") == pytest.approx(stats.chi2.sf(20, 3), rel=1e-2)
    assert value(lines, "fit_pvalue") == pytest.approx(1.70e-4, rel=1e-2)
    assert last(*lines).output.startswith("⇒ reject H0")


def test_expected_rescaling():
    lines = ["sample [10, 20, 30, 40] in fit2", "expected [1, 1, 1, 1] in fit2",
             "claim fits in fit2", "verdict in fit2"]
    assert value(lines, "fit2_statistic") == pytest.approx(20, abs=1e-3)
    assert value(lines, "fit2_df") == 3


def test_level_changes_decision():
    def lines(tag, alpha):
        return [f"sample [10, 20, 30, 40] in {tag}", f"expected [25, 25, 25, 25] in {tag}",
                f"claim fits in {tag}", f"level {alpha} in {tag}", f"verdict in {tag}"]
    assert last(*lines("fit3", 0.0001)).output.startswith("⇒ fail to reject H0")
    assert last(*lines("fit4", 0.001)).output.startswith("⇒ reject H0")


def test_chi_square_nonuniform_matches_scipy():
    obs, exp = [18, 22, 31, 29], [20, 20, 30, 30]
    lines = [f"sample {obs} in c", f"expected {exp} in c", "claim fits in c", "verdict in c"]
    ref = stats.chisquare(obs, exp)
    assert value(lines, "c_statistic") == pytest.approx(ref.statistic, rel=1e-4)
    assert value(lines, "c_pvalue") == pytest.approx(ref.pvalue, rel=1e-3)


def test_chi_square_units_rejected():
    res = last("sample [10, 20] mm in c", "expected [1, 1] in c", "claim fits in c", "verdict in c")
    assert res.status == "error" and "Units do not match" in res.error


# -- 8-16 errors -----------------------------------------------------------------------

def test_no_sample():
    res = last("claim mean == 7 in bad1", "verdict in bad1")
    assert res.error == 'No sample declared for hypothesis test "bad1"'


def test_three_samples():
    res = last("sample [1, 2] in bad2", "sample [1, 2] in bad2", "sample [1, 2] in bad2",
               "claim mean == 7 in bad2", "verdict in bad2")
    assert res.error == 'hypothesis test "bad2" has 3 sample lines, expected 1 or 2'


def test_two_sample_claim_with_one_sample():
    res = last("sample [1, 2] in bad3", "claim mean1 == mean2 in bad3", "verdict in bad3")
    assert res.error == 'claim "mean1 == mean2" needs two sample lines, found 1'


def test_fits_without_expected():
    res = last("sample [1, 2] in bad4", "claim fits in bad4", "verdict in bad4")
    assert res.error == 'claim "fits" needs an expected line'


FORMS = ('Use "claim mean == <value>" ("<" or ">" for one-sided), '
         '"claim mean1 == mean2", or "claim fits"')


@pytest.mark.parametrize("text", ["nonsense", "mean <= 7", "mean1 == 7", "mean", "fit"])
def test_bad_claim_forms(text):
    res = run("sample [1, 2] in bad5", f"claim {text} in bad5", "verdict in bad5")
    assert res[1].error == FORMS
    assert res[2].error == FORMS


def test_expected_length_mismatch():
    res = run("sample [1, 2, 3, 4] in bad6", "expected [1, 1, 1] in bad6", "claim fits in bad6",
              "verdict in bad6")
    assert res[1].error == "expected has 3 values but sample has 4"
    assert res[3].error == "expected has 3 values but sample has 4"


def test_expected_before_sample_checked_at_verdict():
    res = run("expected [1, 1, 1] in bad6", "sample [1, 2, 3, 4] in bad6", "claim fits in bad6",
              "verdict in bad6")
    assert res[0].status == "ok"
    assert res[3].error == "expected has 3 values but sample has 4"


@pytest.mark.parametrize("alpha", ["1.5", "0", "1", "-0.1"])
def test_bad_level(alpha):
    res = run(*S1[:2], f"level {alpha} in s1", S1[2])
    assert res[2].error == "level must be between 0 and 1"
    assert res[3].error == "level must be between 0 and 1"


def test_no_verdict_below():
    res = run("sample [1, 2, 3] in nv", "claim mean == 2 in nv")
    for r in res:
        assert r.error == 'No result region for hypothesis test "nv" below this region'


def test_verdict_above_lines_not_used():
    res = run("verdict in late", "sample [1, 2, 3] in late", "claim mean == 2 in late")
    assert res[0].status == "error"


def test_verdict_trailing_text():
    assert last("verdict extra in bad8").error == "verdict takes no expression"


def test_too_few_values():
    res = last("sample [5] in one", "claim mean == 2 in one", "verdict in one")
    assert res.error == '"one" needs at least 2 values per sample'
    res = last("sample [1, 2, 3] in two", "sample [4] in two", "claim mean1 == mean2 in two",
               "verdict in two")
    assert res.error == '"two" needs at least 2 values per sample'


def test_expected_zero_rejected_at_its_line():
    res = run("sample [1, 2] in ez", "expected [0, 2] in ez", "claim fits in ez", "verdict in ez")
    assert res[1].error == "expected values must be positive"
    assert res[3].status == "error"


def test_expected_with_unit_rejected():
    res = run("expected [1, 2] m in eu", "verdict in eu")
    assert res[0].error == "expected values must be dimensionless"


def test_zero_variance_is_error_not_nan():
    res = last("sample [3, 3, 3] in zv", "claim mean == 2 in zv", "verdict in zv")
    assert res.status == "error" and "zero variance" in res.error


def test_mean_claim_with_expected_line_is_error():
    res = last("sample [1, 2, 3] in me", "expected [1, 1, 1] in me", "claim mean == 2 in me",
               "verdict in me")
    assert res.status == "error"


def test_two_claims_error():
    res = last("sample [1, 2, 3] in tc", "claim mean == 2 in tc", "claim mean == 3 in tc",
               "verdict in tc")
    assert res.status == "error"


def test_sample_not_a_vector():
    res = run("sample [1, 2; 3, 4] in nm", "claim mean == 2 in nm", "verdict in nm")
    assert res[0].error == "sample must be a vector"


# -- 17-18 isolation and parsing -------------------------------------------------------

def test_parse_kinds():
    st = parse_statement("sample [1, 2, 3] in g")
    assert (st.kind, st.model, st.expr) == ("model_sample", "g", "[1, 2, 3]")
    st = parse_statement("claim mean == 7 in g")
    assert (st.kind, st.model, st.expr) == ("model_claim", "g", "mean == 7")
    st = parse_statement("expected [1, 1] in g")
    assert (st.kind, st.model, st.expr) == ("model_expected", "g", "[1, 1]")
    st = parse_statement("level 0.01 in g")
    assert (st.kind, st.model, st.name, st.expr) == ("model_setting", "g", "level", "0.01")
    st = parse_statement("verdict in g")
    assert (st.kind, st.model, st.goal) == ("model_result", "g", "hypothesis_test")


def test_variables_named_like_keywords_unaffected():
    res = run("sample := [1, 2, 3]", "level := 4", "sample =", "level =", "mean(sample) =")
    assert [r.status for r in res] == ["ok"] * 5
    assert res[3].output == "= 4"
    assert res[4].output == "= 2"
    assert parse_statement("sample2 + 1 == 2 in g").kind == "model_require"


def test_independent_models_and_other_specs_coexist():
    res = run(*S1, *AB, "x := 3", "x^2 - 1 == 0 in other", "settle in other", "x =")
    assert res[2].output.startswith("⇒ fail to reject H0")
    assert res[2 + 4].output.startswith("⇒ fail to reject H0")
    assert res[-1].output == "= 3"


def test_results_not_bound_before_verdict_or_on_failure():
    res = run("sample [1] in nb", "claim mean == 1 in nb", "nb_statistic =", "verdict in nb")
    assert res[2].status == "error"
    assert res[3].status == "error"


# -- review fixes (M1 overflow text, M2 verdict cause) ----------------------------------

def test_overflow_gives_clean_error():
    res = last("sample [1e300, 2e300, 3e300] in c", "claim mean == 0 in c", "verdict in c")
    assert res.error == "Result too large"


def test_verdict_reports_expected_length_mismatch_under_mean_claim():
    res = run("sample [1, 2, 3, 4] in b", "expected [1, 1, 1] in b",
              "claim mean == 7 in b", "verdict in b")
    assert res[1].error == "expected has 3 values but sample has 4"
    assert res[3].error == "expected has 3 values but sample has 4"


def test_verdict_still_says_no_expected_line_when_lengths_match():
    res = last("sample [1, 2, 3, 4] in b", "expected [1, 1, 1, 1] in b",
               "claim mean == 7 in b", "verdict in b")
    assert res.error == 'claim "mean == 7" does not use an expected line'
