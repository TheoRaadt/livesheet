"""Independent black-box review tests for spec 017 phase S1 (statistics). Written from the spec only."""

import math
import re

import numpy as np
import pytest
from scipy import stats

from livesheet.engine import Engine

V = "v := [2, 4, 4, 4, 5, 5, 7, 9]"


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return res[len(sources) - 1]


def out(*sources) -> str:
    r = run(*sources)
    assert r.status == "ok", r.error
    return r.output


def err(*sources) -> str:
    r = run(*sources)
    assert r.status == "error", r.output
    return r.error


_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def nums(text: str) -> list[float]:
    """All numbers in a result text, understanding the printed 1.5×10⁻⁶ form."""
    pat = r"(-?\d+\.?\d*)(?:×10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+))?"
    return [float(m.group(1)) * 10.0 ** int(m.group(2).translate(_SUP)) if m.group(2) else float(m.group(1))
            for m in re.finditer(pat, text)]


def num(*sources) -> float:
    return nums(out(*sources))[0]


def vec(*sources) -> list[float]:
    return nums(out(*sources))


# ------------------------------------------------------------ descriptive, criteria 1-3
def test_c1_mean_median_mode():
    assert out(V, "mean(v) =") == "= 5"
    assert out(V, "median(v) =") == "= 4.5"
    assert out(V, "mode(v) =") == "= 4"


def test_c2_spread():
    assert num(V, "variance(v) =") == pytest.approx(32 / 7, rel=1e-6)
    assert num(V, "stdev(v) =") == pytest.approx(math.sqrt(32 / 7), rel=1e-6)
    assert num(V, "population_variance(v) =") == pytest.approx(4, rel=1e-6)
    assert num(V, "population_stdev(v) =") == pytest.approx(2, rel=1e-6)


@pytest.mark.parametrize("p,exp", [(0, 2), (1, 9), (0.5, 4.5), (0.25, 4), (0.75, 5.5)])
def test_c3_quantile(p, exp):
    assert num(V, f"quantile(v, {p}) =") == pytest.approx(exp, rel=1e-6)


@pytest.mark.parametrize("p", [0.1, 0.33, 0.9, 0.999])
def test_quantile_matches_numpy(p):
    data = [2, 4, 4, 4, 5, 5, 7, 9]
    assert num(V, f"quantile(v, {p}) =") == pytest.approx(np.quantile(data, p), rel=1e-5)


# ------------------------------------------------------------ units, criteria 4 and 6
def test_c4_units():
    w = "w := [2, 4, 4, 4, 5, 5, 7, 9] mm"
    assert out(w, "mean(w) = mm") == "= 5 mm"
    assert out(w, "variance(w) = mm^2") == "= 4.57143 mm²"
    assert out(w, "quantile(w, 0.75) = mm") == "= 5.5 mm"
    assert out(w, "stdev(w) = mm").endswith("mm")
    assert num(w, "stdev(w) = mm") == pytest.approx(2.13809, rel=1e-5)
    assert out(w, "median(w) = mm") == "= 4.5 mm"
    assert out(w, "mode(w) = mm") == "= 4 mm"
    assert out(w, "population_stdev(w) = mm") == "= 2 mm"


def test_bare_equals_on_mm_is_base_si():
    assert out("w := [2, 4, 4, 4, 5, 5, 7, 9] mm", "mean(w) =") == "= 0.005 m"


def test_variance_dimension_in_metres_squared():
    r = out("w := [1, 2, 3] m", "variance(w) = m^2")
    assert r == "= 1 m²"


def test_variance_wrong_display_unit_rejected():
    e = run("w := [1, 2, 3] m", "variance(w) = m")
    assert e.status == "error"


def test_c5_covariance_correlation():
    u, t = "u := [1, 2, 3, 4, 5]", "t := [2, 4, 5, 4, 5]"
    assert num(u, t, "covariance(u, t) =") == pytest.approx(1.5, rel=1e-6)
    assert num(u, t, "correlation(u, t) =") == pytest.approx(6 / math.sqrt(60), rel=1e-6)
    assert num(u, t, "correlation(t, u) =") == pytest.approx(6 / math.sqrt(60), rel=1e-6)


def test_c6_cov_units():
    u2, t2 = "u2 := [1, 2, 3, 4, 5] m", "t2 := [2, 4, 5, 4, 5] N"
    assert out(u2, t2, "covariance(u2, t2) =") == "= 1.5 J"
    assert out(u2, t2, "covariance(u2, t2) = N*m") == "= 1.5 N·m"
    assert out(u2, t2, "correlation(u2, t2) =") == "= 0.774597"


def test_correlation_negative_and_bounds():
    assert num("correlation([1,2,3,4], [8,6,4,2]) =") == pytest.approx(-1, abs=1e-9)
    rng = np.random.default_rng(3)
    a, b = rng.normal(size=30), rng.normal(size=30)
    la = "[" + ", ".join(repr(float(x)) for x in a) + "]"
    lb = "[" + ", ".join(repr(float(x)) for x in b) + "]"
    assert num(f"correlation({la}, {lb}) =") == pytest.approx(np.corrcoef(a, b)[0, 1], rel=1e-5)
    assert num(f"covariance({la}, {lb}) =") == pytest.approx(np.cov(a, b)[0, 1], rel=1e-5)


def test_c7_mode_ties():
    assert out("mode([3, 1, 2]) =") == "= 1"
    assert out("mode([5, 5, 2, 2, 9]) =") == "= 2"
    assert out("mode([-1, -1, 4, 4]) =") == "= -1"


def test_mode_keeps_unit():
    assert out("mode([2 m, 1 m, 1 m]) = m") == "= 1 m"


# ------------------------------------------------------------ errors 8-12
def test_c8_vector_shape():
    assert out("mean(5) =") == "= 5"
    for f in ["mean", "median", "mode", "variance", "stdev", "population_variance", "population_stdev"]:
        assert err(f"{f}([1, 2; 3, 4]) =") == f"{f}() needs a vector"
    assert err("quantile([1, 2; 3, 4], 0.5) =") == "quantile() needs a vector"
    assert err("covariance([1, 2; 3, 4], [1, 2; 3, 4]) =") == "covariance() needs a vector"
    assert err("correlation([1, 2; 3, 4], [1, 2; 3, 4]) =") == "correlation() needs a vector"


def test_c9_c10_c11_c12():
    assert err("variance([5]) =") == "variance() needs at least 2 values"
    assert err("stdev([5]) =") == "stdev() needs at least 2 values"
    assert err("quantile([1, 2, 3], 1.5) =") == "p must be between 0 and 1"
    assert err("quantile([1, 2, 3], -0.1) =") == "p must be between 0 and 1"
    assert err("correlation([1, 2, 3], [1, 1, 1]) =") == "correlation() is undefined when a vector is constant"
    assert err("correlation([1, 1, 1], [1, 2, 3]) =") == "correlation() is undefined when a vector is constant"
    assert err("correlation([1, 2], [1, 2, 3]) =") == "Vectors must have the same length (2 and 3)"
    assert err("covariance([1, 2], [1, 2, 3]) =") == "Vectors must have the same length (2 and 3)"


def test_covariance_needs_two_values_and_constant():
    assert run("covariance([1], [2]) =").status == "error"
    assert run("covariance([1, 2, 3], [4, 4, 4]) =").status == "error"


def test_empty_vector():
    assert run("mean([]) =").status == "error"
    assert run("ev := []", "mean(ev) =").status == "error"


def test_edge_single_element():
    for f in ["mean", "median", "mode"]:
        assert out(f"{f}([7]) =") == "= 7"
    assert out("quantile([7], 0.3) =") == "= 7"
    assert out("population_variance([7]) =") == "= 0"
    assert out("population_stdev([7]) =") == "= 0"


def test_quantile_extremes_equal_min_max():
    assert out("quantile([9, 3, 7, 1], 0) =") == "= 1"
    assert out("quantile([9, 3, 7, 1], 1) =") == "= 9"


def test_symbolic_entry_rejected():
    assert "not defined" in err("mean([a, 2]) =")
    assert "not defined" in err("quantile([1, b], 0.5) =")


def test_mixed_units_rejected():
    assert err("mean([1 m, 2 s]) =") == "Units do not match"
    assert err("x := [1 m, 2 s]", "variance(x) =") == "Units do not match"


def test_order_independent():
    assert out("median([9, 1, 5]) =") == "= 5"
    assert out("median([1, 9, 5, 3]) =") == "= 4"


def test_row_and_column_vectors_equal():
    assert num("variance([1, 2, 4]) =") == num("variance([1; 2; 4]) =")


# ------------------------------------------------------------ distributions 13-17
def test_c13_normal():
    assert num("normal_pdf(0, 0, 1) =") == pytest.approx(0.3989423, rel=1e-6)
    assert out("normal_cdf(0, 0, 1) =") == "= 0.5"
    assert num("normal_cdf(1, 0, 1) =") == pytest.approx(0.8413447, rel=1e-6)
    assert num("normal_quantile(0.975, 0, 1) =") == pytest.approx(1.959964, rel=5e-6)  # prints 6 sig. digits


@pytest.mark.parametrize("x,mu,s", [(1.3, 0.5, 2), (-4, 1, 0.3), (10, 10, 5), (2.5, -1, 1.5)])
def test_normal_vs_scipy(x, mu, s):
    assert num(f"normal_pdf({x}, {mu}, {s}) =") == pytest.approx(stats.norm.pdf(x, mu, s), rel=1e-5)
    assert num(f"normal_cdf({x}, {mu}, {s}) =") == pytest.approx(stats.norm.cdf(x, mu, s), rel=1e-5)


@pytest.mark.parametrize("p", [0.001, 0.1, 0.5, 0.9, 0.999999])
def test_normal_quantile_roundtrip(p):
    q = num(f"normal_quantile({p}, 2, 3) =")
    assert q == pytest.approx(stats.norm.ppf(p, 2, 3), rel=1e-5, abs=1e-9)
    assert num(f"normal_cdf({q!r}, 2, 3) =") == pytest.approx(p, rel=1e-4)


def test_c14_uniform():
    assert num("uniform_pdf(5, 0, 10) =") == pytest.approx(0.1)
    assert num("uniform_cdf(5, 0, 10) =") == pytest.approx(0.5)
    assert num("uniform_quantile(0.25, 0, 10) =") == pytest.approx(2.5)
    assert out("uniform_pdf(-1, 0, 10) =") == "= 0"
    assert out("uniform_pdf(11, 0, 10) =") == "= 0"
    assert out("uniform_cdf(-3, 0, 10) =") == "= 0"
    assert out("uniform_cdf(30, 0, 10) =") == "= 1"
    assert num("uniform_cdf(2, -2, 6) =") == pytest.approx(0.5)


def test_c15_binomial():
    assert num("binomial_pmf(2, 5, 0.5) =") == pytest.approx(0.3125)
    assert num("binomial_cdf(2, 5, 0.5) =") == pytest.approx(0.5)
    assert out("binomial_quantile(0.5, 5, 0.5) =") == "= 2"
    assert out("binomial_pmf(7, 5, 0.5) =") == "= 0"


@pytest.mark.parametrize("n,p", [(10, 0.3), (20, 0.5), (7, 0.9), (1, 0.5), (0, 0.5)])
def test_binomial_vs_scipy_all_k(n, p):
    for k in range(0, n + 1):
        assert num(f"binomial_pmf({k}, {n}, {p}) =") == pytest.approx(stats.binom.pmf(k, n, p), rel=1e-5)
        assert num(f"binomial_cdf({k}, {n}, {p}) =") == pytest.approx(stats.binom.cdf(k, n, p), rel=1e-5)


@pytest.mark.parametrize("n,p", [(10, 0.3), (20, 0.5), (8, 0.25)])
def test_binomial_quantile_definition(n, p):
    """Smallest k with cdf(k) >= q, checked on a q grid that avoids float-equality ambiguity."""
    for q in [0.01, 0.1, 0.33, 0.5, 0.77, 0.99]:
        k = int(num(f"binomial_quantile({q}, {n}, {p}) =") )
        assert stats.binom.cdf(k, n, p) >= q - 1e-12
        if k > 0:
            assert stats.binom.cdf(k - 1, n, p) < q


def test_binomial_quantile_exact_ties():
    # Symmetric cases where cdf(k) is an exact dyadic rational equal to q.
    assert out("binomial_quantile(0.5, 5, 0.5) =") == "= 2"
    assert out("binomial_quantile(0.25, 2, 0.5) =") == "= 0"   # cdf(0) = 0.25
    assert out("binomial_quantile(0.75, 2, 0.5) =") == "= 1"   # cdf(1) = 0.75
    assert out("binomial_quantile(0.0625, 4, 0.5) =") == "= 0"  # 1/16
    assert out("binomial_quantile(0.3125, 4, 0.5) =") == "= 1"  # 5/16


def test_binomial_quantile_bounds():
    assert out("binomial_quantile(0, 5, 0.5) =") == "= 0"
    assert out("binomial_quantile(1, 5, 0.5) =") == "= 5"
    assert out("binomial_quantile(1, 5, 1) =") == "= 5"
    assert out("binomial_quantile(0.5, 5, 0) =") == "= 0"


def test_binomial_p_bounds():
    assert out("binomial_pmf(0, 5, 0) =") == "= 1"
    assert out("binomial_pmf(2, 5, 0) =") == "= 0"
    assert out("binomial_pmf(5, 5, 1) =") == "= 1"
    assert out("binomial_pmf(4, 5, 1) =") == "= 0"
    assert out("binomial_cdf(4, 5, 1) =") == "= 0"
    assert out("binomial_cdf(0, 5, 0) =") == "= 1"
    assert out("binomial_pmf(0, 0, 0.5) =") == "= 1"


def test_c16_poisson():
    assert num("poisson_pmf(2, 3) =") == pytest.approx(0.2240418, rel=1e-6)
    assert num("poisson_cdf(2, 3) =") == pytest.approx(0.4231901, rel=1e-6)
    assert out("poisson_quantile(0.423190, 3) =") == "= 2"


@pytest.mark.parametrize("lam", [0.5, 3, 12.5, 40])
def test_poisson_vs_scipy(lam):
    for k in [0, 1, 2, 5, 10, 30]:
        assert num(f"poisson_pmf({k}, {lam}) =") == pytest.approx(stats.poisson.pmf(k, lam), rel=1e-5, abs=1e-300)
        assert num(f"poisson_cdf({k}, {lam}) =") == pytest.approx(stats.poisson.cdf(k, lam), rel=1e-5)
    for q in [0.01, 0.3, 0.5, 0.9, 0.999]:
        k = int(num(f"poisson_quantile({q}, {lam}) ="))
        assert stats.poisson.cdf(k, lam) >= q - 1e-12
        if k:
            assert stats.poisson.cdf(k - 1, lam) < q


def test_poisson_quantile_zero():
    assert out("poisson_quantile(0, 3) =") == "= 0"


def test_poisson_quantile_exact_tie():
    # lam tiny: cdf(0)=exp(-lam); choose q = cdf(0) in float, tie must give 0 not 1
    lam = 0.7
    q = repr(float(stats.poisson.cdf(0, lam)))
    assert out(f"poisson_quantile({q}, {lam}) =") == "= 0"


def test_c17_errors():
    assert err("normal_pdf(0, 0, -1) =") == "sigma must be positive"
    assert err("normal_pdf(0, 0, 0) =") == "sigma must be positive"
    assert err("binomial_pmf(1.5, 5, 0.5) =") == "k must be a non-negative integer"
    assert err("binomial_pmf(2, 5, 1.5) =") == "p must be between 0 and 1"
    assert err("binomial_pmf(2, 5, -0.1) =") == "p must be between 0 and 1"
    assert err("normal_pdf(5 m, 0, 1) =") == "normal_pdf() does not accept a unit in this version"


@pytest.mark.parametrize("call", [
    "normal_pdf(1 m, 0, 1)", "normal_pdf(1, 1 m, 1)", "normal_pdf(1, 0, 1 m)",
    "normal_cdf(1 m, 0, 1)", "normal_cdf(1, 0, 1 s)", "normal_quantile(0.5 m, 0, 1)",
    "uniform_pdf(1 m, 0, 10)", "uniform_cdf(1, 0 m, 10 m)", "uniform_quantile(0.5, 0, 10 m)",
    "binomial_pmf(2 m, 5, 0.5)", "binomial_cdf(2, 5 m, 0.5)", "binomial_pmf(2, 5, 0.5 m)",
    "poisson_pmf(2 s, 3)", "poisson_cdf(2, 3 s)", "poisson_quantile(0.5, 3 s)",
    "normal_sample(1 m, 1, 5, 1)", "uniform_sample(0, 10 m, 5, 1)", "binomial_sample(5, 0.5, 5 m, 1)",
    "poisson_sample(3 m, 5, 1)", "poisson_sample(3, 5, 1 s)",
])
def test_units_rejected_everywhere(call):
    assert "does not accept a unit" in err(f"{call} =")


def test_unit_dimensionless_ratio_accepted():
    # A dimensionless quotient of units is a plain number, not a unit-carrying quantity.
    assert num("normal_cdf((2 m) / (1 m), 0, 1) =") == pytest.approx(stats.norm.cdf(2), rel=1e-5)


@pytest.mark.xfail(reason="developer-disclosed limitation: '0 m' collapses to 0 before the function sees it", strict=True)
def test_zero_with_unit_rejected():
    assert run("normal_cdf(0, 0 m, 1) =").status == "error"


def test_domain_errors():
    assert err("normal_quantile(0, 0, 1) =") == "p must be strictly between 0 and 1"
    assert err("normal_quantile(1, 0, 1) =") == "p must be strictly between 0 and 1"
    assert run("normal_quantile(-0.5, 0, 1) =").status == "error"
    assert run("uniform_pdf(1, 5, 5) =").status == "error"
    assert run("uniform_pdf(1, 6, 5) =").status == "error"
    assert run("poisson_pmf(2, 0) =").status == "error"
    assert run("poisson_pmf(2, -1) =").status == "error"
    assert run("binomial_pmf(2, -5, 0.5) =").status == "error"
    assert run("binomial_pmf(2, 5.5, 0.5) =").status == "error"
    assert run("binomial_quantile(1.2, 5, 0.5) =").status == "error"
    assert run("poisson_quantile(1.5, 3) =").status == "error"
    assert run("poisson_quantile(-0.1, 3) =").status == "error"
    assert run("poisson_pmf(1.5, 3) =").status == "error"
    assert run("poisson_cdf(-1, 3) =").status == "error"


def test_wrong_arity_and_non_scalars():
    assert run("normal_pdf(0, 0) =").status == "error"
    assert run("normal_pdf([1, 2], 0, 1) =").status == "error"
    assert run("poisson_pmf(2) =").status == "error"
    assert run("normal_sample(0, 1, 5) =").status == "error"  # seed required


def test_undefined_symbol_in_distribution():
    assert "not defined" in err("normal_pdf(zz, 0, 1) =")


def test_pmf_support_outside_conventions():
    # spec: outside the support returns 0 (k > n_trials), not an error
    assert out("binomial_pmf(100, 5, 0.5) =") == "= 0"


# ------------------------------------------------------------ sampling 18-19
def test_c18_determinism_and_difference():
    a = out("normal_sample(0, 1, 5, 1) =")
    b = out("normal_sample(0, 1, 5, 1) =")
    c = out("normal_sample(0, 1, 5, 2) =")
    assert a == b and a != c
    assert a.count(";") == 4  # 5x1 column
    assert vec("normal_sample(0, 1, 5, 1) =") != vec("normal_sample(0, 1, 5, 2) =")


def test_sample_deterministic_within_one_sheet_and_reevaluation():
    srcs = ["a := normal_sample(0, 1, 6, 7)", "b := normal_sample(0, 1, 6, 7)", "a - b ="]
    r = out(*srcs)
    assert all(x == 0 for x in nums(r))
    e = Engine()
    regs = list(enumerate(["s := uniform_sample(0, 1, 4, 5)", "s ="]))
    first = e.evaluate(regs)[1].output
    assert e.evaluate(regs)[1].output == first
    assert Engine().evaluate(regs)[1].output == first


def test_sample_seed_zero_ok_and_different_params_differ():
    assert run("normal_sample(0, 1, 3, 0) =").status == "ok"
    assert out("normal_sample(0, 1, 3, 4) =") != out("normal_sample(0, 2, 3, 4) =")


def test_sample_length_and_stats():
    assert out("len(normal_sample(0, 1, 2000, 1)) =") == "= 2000"
    assert abs(num("mean(normal_sample(0, 1, 2000, 1)) =")) < 0.1
    assert abs(num("stdev(normal_sample(0, 1, 2000, 1)) =") - 1) < 0.1
    assert out("len(normal_sample(0, 1, 10000, 1)) =") == "= 10000"
    assert err("normal_sample(0, 1, 10001, 1) =") == "n is too large (max 10000)"


def test_sample_n_validation():
    for n in ["0", "-3", "2.5"]:
        assert run(f"normal_sample(0, 1, {n}, 1) =").status == "error"
    for s in ["-1", "1.5"]:
        assert run(f"normal_sample(0, 1, 3, {s}) =").status == "error"
    assert out("len(normal_sample(0, 1, 1, 1)) =") == "= 1"


def test_sample_param_errors():
    assert err("normal_sample(0, -1, 3, 1) =") == "sigma must be positive"
    assert run("uniform_sample(3, 3, 3, 1) =").status == "error"
    assert run("binomial_sample(5, 1.5, 3, 1) =").status == "error"
    assert run("binomial_sample(-5, 0.5, 3, 1) =").status == "error"
    assert run("poisson_sample(0, 3, 1) =").status == "error"


def _draw(call: str, n: int = 300) -> list[float]:
    """First n entries of a (long) sample, read through 1-based indexing of a defined vector."""
    srcs = [f"s := {call}"] + [f"s[{i}] =" for i in range(1, n + 1)]
    res = Engine().evaluate(enumerate(srcs))
    return [nums(res[i].output)[0] for i in range(1, n + 1)]


def test_normal_sample_distribution_ks():
    xs = _draw("normal_sample(3, 2, 2000, 11)")
    assert len(xs) == 300
    assert stats.kstest(xs, stats.norm(3, 2).cdf).pvalue > 0.001


def test_uniform_sample_distribution_ks_and_bounds():
    xs = _draw("uniform_sample(-2, 6, 2000, 4)")
    assert min(xs) >= -2 and max(xs) <= 6
    assert stats.kstest(xs, "uniform", args=(-2, 8)).pvalue > 0.001


def test_c19_binomial_sample():
    xs = _draw("binomial_sample(10, 0.5, 2000, 1)", 2000)
    assert len(xs) == 2000
    assert all(x == int(x) and 0 <= x <= 10 for x in xs)
    assert abs(np.mean(xs) - 5) < 0.2
    assert num("mean(binomial_sample(10, 0.5, 2000, 1)) =") == pytest.approx(np.mean(xs), rel=1e-5)
    assert num("quantile(binomial_sample(10, 0.5, 2000, 1), 0) =") == min(xs)
    assert num("quantile(binomial_sample(10, 0.5, 2000, 1), 1) =") == max(xs)
    # chi-square against the exact pmf
    obs = np.bincount([int(x) for x in xs], minlength=11)
    exp = stats.binom.pmf(range(11), 10, 0.5) * 2000
    # merge sparse tails
    o = np.concatenate([[obs[:2].sum()], obs[2:9], [obs[9:].sum()]])
    e = np.concatenate([[exp[:2].sum()], exp[2:9], [exp[9:].sum()]])
    assert stats.chisquare(o, e).pvalue > 0.001


def test_poisson_sample_stats():
    xs = _draw("poisson_sample(4, 2000, 9)", 2000)
    assert all(x == int(x) and x >= 0 for x in xs)
    assert abs(np.mean(xs) - 4) < 0.25
    assert abs(np.var(xs, ddof=1) - 4) < 0.7


def test_binomial_sample_degenerate_p():
    assert all(x == 0 for x in _draw("binomial_sample(10, 0, 50, 1)", 50))
    assert all(x == 10 for x in _draw("binomial_sample(10, 1, 50, 1)", 50))


def test_sample_integer_display():
    assert re.fullmatch(r"= \[(-?\d+; ){4}-?\d+\]", out("binomial_sample(10, 0.5, 5, 3) ="))


# ------------------------------------------------------------ in real sheets
def test_pipeline_define_use_later():
    r = Engine().evaluate(enumerate([
        "data := [12, 15, 11, 14, 13, 16]",
        "m := mean(data)",
        "s := stdev(data)",
        "z := (16 - m) / s",
        "p := normal_cdf(z, 0, 1)",
        "p =",
    ]))
    z = (16 - 13.5) / np.std([12, 15, 11, 14, 13, 16], ddof=1)
    assert r[5].status == "ok"
    assert nums(r[5].output)[0] == pytest.approx(stats.norm.cdf(z), rel=1e-5)


def test_statistics_of_matrix_slices_and_ops():
    # vector expressions and builtin composition
    assert num("mean([1, 2, 3] * 2) =") == pytest.approx(4)
    assert num("stdev([1, 2, 3, 4] + [10, 10, 10, 10]) =") == pytest.approx(np.std([1, 2, 3, 4], ddof=1), rel=1e-5)
    xs = _draw("normal_sample(5, 1, 101, 3)", 101)
    assert num("median(normal_sample(5, 1, 101, 3)) =") == pytest.approx(np.median(xs), rel=1e-5)


def test_unit_vectors_inside_expressions():
    r = out("L := [10, 12, 11] mm", "mean(L) / (1 mm) =")
    assert nums(r)[0] == pytest.approx(11, rel=1e-6)
    r = out("L := [10, 12, 11] mm", "mean(L) + 1 mm = mm")
    assert r == "= 12 mm"
    assert out("L := [10, 12, 11] mm", "stdev(L) / mean(L) =").startswith("= 0.0")


def test_user_definition_shadows_builtin():
    assert out("mean := 5", "mean =") == "= 5"


def test_variable_named_like_function_not_affected():
    assert out("mode := 3", "mode + 1 =") == "= 4"


def test_symbolic_arrow_on_stats_does_not_crash():
    r = run("mean([1, 2, 3]) →")
    assert r.status in ("ok", "error")


def test_correlation_through_samples():
    a, b = _draw("normal_sample(0,1,200,1)", 200), _draw("normal_sample(0,1,200,2)", 200)
    assert num("correlation(normal_sample(0,1,200,1), normal_sample(0,1,200,2)) =") == pytest.approx(
        np.corrcoef(a, b)[0, 1], rel=1e-4)


def test_large_vector_stats_fast():
    r = run("x := normal_sample(0, 1, 10000, 5)", "variance(x) =")
    assert r.status == "ok"
    assert nums(r.output)[0] == pytest.approx(1, abs=0.05)


def test_huge_values_and_precision():
    assert num("mean([1e300, 1e300]) =") == pytest.approx(1e300, rel=1e-9)
    assert num("variance([1000000001, 1000000002, 1000000003]) =") == pytest.approx(1, rel=1e-6)
