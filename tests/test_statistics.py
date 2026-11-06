"""Spec 017 phase S1: descriptive statistics and distributions (engine level)."""

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


def num(*sources) -> float:
    return float(re.search(r"-?\d+\.?\d*(?:e-?\d+)?", out(*sources)).group())


def vec(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


def close(actual: float, expected: float, rel: float = 1e-6) -> None:
    assert actual == pytest.approx(expected, rel=rel)


# ---------------------------------------------------------------- descriptive (criteria 1-3)

def test_mean_median_mode():
    assert out(V, "mean(v) =") == "= 5"
    assert out(V, "median(v) =") == "= 4.5"
    assert out(V, "mode(v) =") == "= 4"


def test_variance_and_stdev():
    close(num(V, "variance(v) ="), 32 / 7, 1e-5)
    close(num(V, "stdev(v) ="), (32 / 7) ** 0.5, 1e-5)
    assert out(V, "population_variance(v) =") == "= 4"
    assert out(V, "population_stdev(v) =") == "= 2"


def test_quantile():
    assert out(V, "quantile(v, 0) =") == "= 2"
    assert out(V, "quantile(v, 1) =") == "= 9"
    assert out(V, "quantile(v, 0.5) =") == out(V, "median(v) =")
    assert out(V, "quantile(v, 0.25) =") == "= 4"
    assert out(V, "quantile(v, 0.75) =") == "= 5.5"


def test_row_vector_and_symbolic_free_scalar():
    assert out("mean([1, 2, 3]) =") == "= 2"
    assert out("mean(5) =") == "= 5"


def test_one_element_vector():
    for f in ("mean", "median", "mode"):
        assert out(f"{f}([7]) =") == "= 7"
    assert out("quantile([7], 0.3) =") == "= 7"
    assert out("population_variance([7]) =") == "= 0"


# ---------------------------------------------------------------- units (criteria 4 and 6)

W = "w := [2, 4, 4, 4, 5, 5, 7, 9] mm"


def test_units_explicit_display():
    assert out(W, "mean(w) = mm") == "= 5 mm"
    assert out(W, "variance(w) = mm^2") == "= 4.57143 mm²"
    assert out(W, "quantile(w, 0.75) = mm") == "= 5.5 mm"
    assert out(W, "stdev(w) = mm").endswith("mm")
    assert out(W, "mode(w) = mm") == "= 4 mm"
    assert out(W, "median(w) = mm") == "= 4.5 mm"


def test_bare_equals_shows_base_si():
    assert out(W, "mean(w) =") == "= 0.005 m"


def test_covariance_correlation():
    u, t = "u := [1, 2, 3, 4, 5]", "t := [2, 4, 5, 4, 5]"
    close(num(u, t, "covariance(u, t) ="), 1.5)
    close(num(u, t, "correlation(u, t) ="), 6 / 60 ** 0.5)


def test_covariance_units():
    u, t = "u2 := [1, 2, 3, 4, 5] m", "t2 := [2, 4, 5, 4, 5] N"
    assert out(u, t, "covariance(u2, t2) =") == "= 1.5 J"
    assert out(u, t, "covariance(u2, t2) = N*m") == "= 1.5 N·m"
    close(num(u, t, "correlation(u2, t2) ="), 0.774597)


def test_mode_tie_break():
    assert out("mode([3, 1, 2]) =") == "= 1"
    assert out("mode([5, 5, 2, 2, 9]) =") == "= 2"


def test_mixed_units_rejected():
    assert err("mean([1 m, 2 s]) =") == "Units do not match"


# ---------------------------------------------------------------- descriptive errors (8-12)

def test_vector_errors():
    assert err("mean([1, 2; 3, 4]) =") == "mean() needs a vector"
    for f in ("median", "mode", "variance", "stdev", "population_variance", "population_stdev"):
        assert err(f"{f}([1, 2; 3, 4]) =") == f"{f}() needs a vector"
    assert err("quantile([1, 2; 3, 4], 0.5) =") == "quantile() needs a vector"
    assert err("covariance([1, 2; 3, 4], [1, 2]) =") == "covariance() needs a vector"


def test_symbolic_entries():
    assert err("mean(zz) =") == "zz is not defined"
    assert err("mean([1, qq]) =") == "qq is not defined"


def test_variance_needs_two():
    assert err("variance([5]) =") == "variance() needs at least 2 values"
    assert err("stdev([5]) =") == "stdev() needs at least 2 values"


def test_quantile_range():
    assert err(V, "quantile(v, 1.5) =") == "p must be between 0 and 1"
    assert err(V, "quantile(v, -0.1) =") == "p must be between 0 and 1"


def test_correlation_errors():
    assert err("correlation([1, 2, 3], [1, 1, 1]) =") == \
        "correlation() is undefined when a vector is constant"
    assert err("covariance([1, 1, 1], [1, 2, 3]) =") == \
        "covariance() is undefined when a vector is constant"
    assert err("correlation([1, 2], [1, 2, 3]) =") == "Vectors must have the same length (2 and 3)"
    assert err("correlation([1], [1]) =") == "correlation() needs at least 2 values"


def test_correlation_bounds():
    close(num("correlation([1, 2, 3], [3, 2, 1]) ="), -1.0)


# ---------------------------------------------------------------- distributions (13-17)

def test_normal():
    close(num("normal_pdf(0, 0, 1) ="), 0.3989423)
    assert out("normal_cdf(0, 0, 1) =") == "= 0.5"
    close(num("normal_cdf(1, 0, 1) ="), 0.841345)
    close(num("normal_quantile(0.975, 0, 1) ="), 1.959964, 1e-5)
    close(num("normal_cdf(12, 10, 2) ="), stats.norm.cdf(1.0), 1e-5)
    close(num("normal_quantile(0.9, 10, 2) ="), stats.norm.ppf(0.9, 10, 2), 1e-5)


def test_normal_quantile_open_ends():
    for p in (0, 1):
        assert err(f"normal_quantile({p}, 0, 1) =") == "p must be strictly between 0 and 1"


def test_uniform():
    assert out("uniform_pdf(5, 0, 10) =") == "= 0.1"
    assert out("uniform_cdf(5, 0, 10) =") == "= 0.5"
    assert out("uniform_quantile(0.25, 0, 10) =") == "= 2.5"
    assert out("uniform_pdf(-1, 0, 10) =") == "= 0"
    assert out("uniform_cdf(-1, 0, 10) =") == "= 0"
    assert out("uniform_cdf(11, 0, 10) =") == "= 1"
    assert err("uniform_pdf(1, 5, 5) =") == "a must be less than b"


def test_binomial():
    assert out("binomial_pmf(2, 5, 0.5) =") == "= 0.3125"
    assert out("binomial_cdf(2, 5, 0.5) =") == "= 0.5"
    assert out("binomial_pmf(7, 5, 0.5) =") == "= 0"
    assert out("binomial_cdf(7, 5, 0.5) =") == "= 1"


def test_binomial_quantile_exact_tie():
    assert out("binomial_quantile(0.5, 5, 0.5) =") == "= 2"
    # just above the tie moves to the next integer; level 0 gives 0, level 1 gives n_trials
    assert out("binomial_quantile(0.5001, 5, 0.5) =") == "= 3"
    assert out("binomial_quantile(0, 5, 0.5) =") == "= 0"
    assert out("binomial_quantile(1, 5, 0.5) =") == "= 5"
    assert out("binomial_quantile(0.5, 0, 0.5) =") == "= 0"


def test_binomial_quantile_matches_scipy():
    for q in (0.05, 0.25, 0.5, 0.75, 0.95):
        expected = int(stats.binom.ppf(q, 20, 0.3))
        assert out(f"binomial_quantile({q}, 20, 0.3) =") == f"= {expected}"


def test_poisson():
    close(num("poisson_pmf(2, 3) ="), 0.2240418)
    close(num("poisson_cdf(2, 3) ="), 0.423190, 1e-5)
    assert out("poisson_quantile(0.423190, 3) =") == "= 2"
    assert out("poisson_quantile(0, 3) =") == "= 0"
    for q in (0.1, 0.5, 0.9, 0.99):
        assert out(f"poisson_quantile({q}, 4.5) =") == f"= {int(stats.poisson.ppf(q, 4.5))}"


def test_distribution_errors():
    assert err("normal_pdf(0, 0, -1) =") == "sigma must be positive"
    assert err("binomial_pmf(1.5, 5, 0.5) =") == "k must be a non-negative integer"
    assert err("binomial_pmf(-1, 5, 0.5) =") == "k must be a non-negative integer"
    assert err("binomial_pmf(2, 5, 1.5) =") == "p must be between 0 and 1"
    assert err("binomial_pmf(2, 2.5, 0.5) =") == "n_trials must be a non-negative integer"
    assert err("poisson_pmf(1, 0) =") == "lambda_ must be positive"
    assert err("poisson_pmf(1.5, 2) =") == "k must be a non-negative integer"
    assert err("poisson_quantile(1, 2) =") == "q must be at least 0 and less than 1"
    assert err("binomial_quantile(1.5, 5, 0.5) =") == "q must be between 0 and 1"


def test_units_rejected_everywhere():
    assert err("normal_pdf(5 m, 0, 1) =") == "normal_pdf() does not accept a unit in this version"
    assert err("normal_cdf(0, 1 m, 1) =") == "normal_cdf() does not accept a unit in this version"
    assert err("uniform_cdf(1, 0, 2 s) =") == "uniform_cdf() does not accept a unit in this version"
    assert err("poisson_pmf(2, 3 s) =") == "poisson_pmf() does not accept a unit in this version"
    assert err("quantile([1, 2], 0.5 m) =") == "quantile() does not accept a unit in this version"


def test_matrix_argument_rejected():
    assert err("normal_pdf([1, 2], 0, 1) =") == "normal_pdf() needs a scalar"


def test_user_definition_shadows_builtin():
    assert out("mean := 3", "mean =") == "= 3"


# ---------------------------------------------------------------- sampling (18-19)

def test_sample_deterministic():
    a = out("normal_sample(0, 1, 5, 1) =")
    assert a == out("normal_sample(0, 1, 5, 1) =")
    assert a != out("normal_sample(0, 1, 5, 2) =")
    assert len(vec(a)) == 5


def test_sample_matches_numpy():
    rng = np.random.default_rng(1)
    expected = rng.normal(0, 1, 5)
    for got, want in zip(vec(out("normal_sample(0, 1, 5, 1) =")), expected):
        assert got == pytest.approx(want, abs=1e-5)


def test_sample_statistics():
    close(num("len(normal_sample(0, 1, 2000, 1)) ="), 2000)
    assert abs(num("mean(normal_sample(0, 1, 2000, 1)) =")) < 0.1
    assert abs(num("stdev(normal_sample(0, 1, 2000, 1)) =") - 1) < 0.1


def test_sample_too_large_and_bad_args():
    assert err("normal_sample(0, 1, 10001, 1) =") == "n is too large (max 10000)"
    assert err("normal_sample(0, 1, 0, 1) =") == "n must be a positive integer"
    assert err("normal_sample(0, 1, 5, -1) =") == "seed must be a non-negative integer"
    assert err("normal_sample(0, 1, 5, 1.5) =") == "seed must be a non-negative integer"
    assert err("normal_sample(0, -1, 5, 1) =") == "sigma must be positive"


def test_sample_is_column_vector():
    assert run("x := normal_sample(0, 1, 7, 3)", "len(x) =").output == "= 7"
    assert out("nrows(normal_sample(0, 1, 7, 3)) =") == "= 7"
    assert out("ncols(normal_sample(0, 1, 7, 3)) =") == "= 1"


def test_uniform_sample():
    assert 2.4 < num("mean(uniform_sample(2, 3, 500, 4)) =") < 2.6
    assert err("uniform_sample(3, 2, 5, 1) =") == "a must be less than b"
    assert out("uniform_sample(2, 3, 5, 1) =") == out("uniform_sample(2, 3, 5, 1) =")


def test_binomial_sample():
    assert abs(num("mean(binomial_sample(10, 0.5, 2000, 1)) =") - 5) < 0.2
    from livesheet.engine.statistics import binomial_sample

    entries = [int(e) for e in binomial_sample(10, 0.5, 2000, 1)]
    assert len(entries) == 2000
    assert all(0 <= k <= 10 for k in entries)


def test_poisson_sample():
    assert abs(num("mean(poisson_sample(3, 2000, 1)) =") - 3) < 0.3
    from livesheet.engine.statistics import poisson_sample

    assert all(int(e) >= 0 for e in poisson_sample(3, 100, 1))
    assert out("poisson_sample(3, 4, 9) =") == out("poisson_sample(3, 4, 9) =")


def test_sample_feeds_descriptive_stats():
    s = "x := normal_sample(10, 2, 2000, 5)"
    assert abs(num(s, "mean(x) =") - 10) < 0.3
    assert abs(num(s, "stdev(x) =") - 2) < 0.3
