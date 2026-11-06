"""Spec 017 phase S1: descriptive statistics and probability distributions.

GUI-independent. Data are ordinary vectors (Nx1 or 1xN matrices, or a scalar as a 1x1 vector).
Descriptive functions keep units through ``matrices.split_units``; the distribution functions are
dimensionless only in this version. NumPy / SciPy are the numeric backend.
"""

from __future__ import annotations

from collections import Counter

import sympy as sp

from .matrices import (_DENSE, _has_unit, _is_scalar, _is_vector, smul, unit_of,
                       split_units, wrap)
from .syntax import StatementError

MAX_SAMPLE = 10000
_TIE_TOLERANCE = 1e-12  # absolute tolerance when comparing a cdf with a quantile level


# ---------------------------------------------------------------- argument helpers

def _check_numeric(x) -> None:
    syms = [s for s in x.free_symbols if not s.is_number]
    if syms:
        raise StatementError(f"{sorted(s.name for s in syms)[0]} is not defined")


def _vector(name: str, x):
    """(entries, SI magnitudes as floats, dimension tuple) of a vector or scalar argument."""
    if isinstance(x, sp.MatrixBase):
        if not _is_vector(x):
            raise StatementError(f"{name}() needs a vector")
        m = x
    elif _is_scalar(x):
        m = _DENSE(1, 1, [sp.sympify(x)])
    else:
        raise StatementError(f"{name}() needs a vector")
    for e in m:
        _check_numeric(e)
    mags, dims = split_units(m)
    try:
        values = [float(e) for e in mags]
    except (TypeError, ValueError):
        raise StatementError(f"{name}() needs real numbers") from None
    return list(m), values, dims


def _scale_dims(dims, k: int):
    return tuple((d, e * k) for d, e in dims if e * k != 0)


def _add_dims(a, b):
    exps = dict(a)
    for d, e in b:
        exps[d] = exps.get(d, 0) + e
    return tuple(sorted((d, e) for d, e in exps.items() if e != 0))


def _with_unit(value: float, dims):
    number = sp.Float(value)
    return smul(number, unit_of(dims)) if dims else number


def _at_least(name: str, values: list, n: int) -> None:
    if len(values) < n:
        raise StatementError(f"{name}() needs at least {n} values")


def _real(name: str, x) -> float:
    """A dimensionless real scalar argument as a float."""
    if isinstance(x, sp.MatrixBase):
        raise StatementError(f"{name}() needs a scalar")
    x = sp.sympify(x)
    if _has_unit(x):
        raise StatementError(f"{name}() does not accept a unit in this version")
    _check_numeric(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        raise StatementError(f"{name}() needs real numbers") from None


def _integer(name: str, x, what: str, minimum: int = 0) -> int:
    v = _real(name, x)
    if v != int(v) or v < minimum:
        kind = "non-negative" if minimum == 0 else "positive"
        raise StatementError(f"{what} must be a {kind} integer")
    return int(v)


# ---------------------------------------------------------------- descriptive statistics

def mean(v):
    _, vals, dims = _vector("mean", v)
    return _with_unit(sum(vals) / len(vals), dims)


def median(v):
    import numpy as np

    _, vals, dims = _vector("median", v)
    return _with_unit(float(np.median(vals)), dims)


def mode(v):
    entries, vals, _ = _vector("mode", v)
    counts = Counter(vals)
    top = max(counts.values())
    best = min(val for val, c in counts.items() if c == top)
    return entries[vals.index(best)]


def _sample_spread(name: str, v, ddof: int, root: bool):
    import numpy as np

    _, vals, dims = _vector(name, v)
    if ddof:
        _at_least(name, vals, 2)
    var = float(np.var(vals, ddof=ddof))
    if root:
        return _with_unit(var ** 0.5, dims)
    return _with_unit(var, _scale_dims(dims, 2))


def variance(v):
    return _sample_spread("variance", v, 1, False)


def stdev(v):
    return _sample_spread("stdev", v, 1, True)


def population_variance(v):
    return _sample_spread("population_variance", v, 0, False)


def population_stdev(v):
    return _sample_spread("population_stdev", v, 0, True)


def quantile(v, p):
    import numpy as np

    _, vals, dims = _vector("quantile", v)
    level = _real("quantile", p)
    if not 0 <= level <= 1:
        raise StatementError("p must be between 0 and 1")
    return _with_unit(float(np.quantile(vals, level)), dims)


def _pair(name: str, u, v):
    _, a, da = _vector(name, u)
    _, b, db = _vector(name, v)
    if len(a) != len(b):
        raise StatementError(f"Vectors must have the same length ({len(a)} and {len(b)})")
    _at_least(name, a, 2)
    if len(set(a)) == 1 or len(set(b)) == 1:
        raise StatementError(f"{name}() is undefined when a vector is constant")
    return a, b, da, db


def covariance(u, v):
    import numpy as np

    a, b, da, db = _pair("covariance", u, v)
    return _with_unit(float(np.cov(a, b, ddof=1)[0, 1]), _add_dims(da, db))


def correlation(u, v):
    import numpy as np

    a, b, _, _ = _pair("correlation", u, v)
    return sp.Float(float(np.corrcoef(a, b)[0, 1]))


# ---------------------------------------------------------------- distributions

def _positive(name: str, value, label: str) -> float:
    v = _real(name, value)
    if not v > 0:
        raise StatementError(f"{label} must be positive")
    return v


def _probability(name: str, value, label: str = "p") -> float:
    v = _real(name, value)
    if not 0 <= v <= 1:
        raise StatementError(f"{label} must be between 0 and 1")
    return v


def _open_probability(name: str, value) -> float:
    v = _real(name, value)
    if not 0 < v < 1:
        raise StatementError("p must be strictly between 0 and 1")
    return v


def _normal_args(name: str, mu, sigma):
    return _real(name, mu), _positive(name, sigma, "sigma")


def normal_pdf(x, mu, sigma):
    from scipy import stats

    xv = _real("normal_pdf", x)
    m, s = _normal_args("normal_pdf", mu, sigma)
    return sp.Float(float(stats.norm.pdf(xv, m, s)))


def normal_cdf(x, mu, sigma):
    from scipy import stats

    xv = _real("normal_cdf", x)
    m, s = _normal_args("normal_cdf", mu, sigma)
    return sp.Float(float(stats.norm.cdf(xv, m, s)))


def normal_quantile(p, mu, sigma):
    from scipy import stats

    pv = _open_probability("normal_quantile", p)
    m, s = _normal_args("normal_quantile", mu, sigma)
    return sp.Float(float(stats.norm.ppf(pv, m, s)))


def _uniform_args(name: str, a, b):
    av, bv = _real(name, a), _real(name, b)
    if not av < bv:
        raise StatementError("a must be less than b")
    return av, bv


def uniform_pdf(x, a, b):
    xv = _real("uniform_pdf", x)
    lo, hi = _uniform_args("uniform_pdf", a, b)
    return sp.Float(1.0 / (hi - lo) if lo <= xv <= hi else 0.0)


def uniform_cdf(x, a, b):
    xv = _real("uniform_cdf", x)
    lo, hi = _uniform_args("uniform_cdf", a, b)
    return sp.Float(min(1.0, max(0.0, (xv - lo) / (hi - lo))))


def uniform_quantile(p, a, b):
    pv = _probability("uniform_quantile", p)
    lo, hi = _uniform_args("uniform_quantile", a, b)
    return sp.Float(lo + pv * (hi - lo))


def _binomial_args(name: str, k, n_trials, p):
    kv = _integer(name, k, "k")
    n = _integer(name, n_trials, "n_trials")
    return kv, n, _probability(name, p)


def binomial_pmf(k, n_trials, p):
    from scipy import stats

    kv, n, pv = _binomial_args("binomial_pmf", k, n_trials, p)
    return sp.Float(0.0 if kv > n else float(stats.binom.pmf(kv, n, pv)))


def binomial_cdf(k, n_trials, p):
    from scipy import stats

    kv, n, pv = _binomial_args("binomial_cdf", k, n_trials, p)
    return sp.Float(1.0 if kv >= n else float(stats.binom.cdf(kv, n, pv)))


def _discrete_quantile(dist, level: float, upper: int | None):
    """Smallest integer k with cdf(k) >= level (within an absolute tolerance on exact ties)."""
    k = max(0, int(dist.ppf(level)))
    while k > 0 and dist.cdf(k - 1) >= level - _TIE_TOLERANCE:
        k -= 1
    while (upper is None or k < upper) and dist.cdf(k) < level - _TIE_TOLERANCE:
        k += 1
    return k


def binomial_quantile(q, n_trials, p):
    from scipy import stats

    qv = _probability("binomial_quantile", q, "q")
    n = _integer("binomial_quantile", n_trials, "n_trials")
    pv = _probability("binomial_quantile", p)
    return sp.Integer(_discrete_quantile(stats.binom(n, pv), qv, n))


def poisson_pmf(k, lambda_):
    from scipy import stats

    kv = _integer("poisson_pmf", k, "k")
    lam = _positive("poisson_pmf", lambda_, "lambda_")
    return sp.Float(float(stats.poisson.pmf(kv, lam)))


def poisson_cdf(k, lambda_):
    from scipy import stats

    kv = _integer("poisson_cdf", k, "k")
    lam = _positive("poisson_cdf", lambda_, "lambda_")
    return sp.Float(float(stats.poisson.cdf(kv, lam)))


def poisson_quantile(q, lambda_):
    from scipy import stats

    qv = _real("poisson_quantile", q)
    if not 0 <= qv < 1:
        raise StatementError("q must be at least 0 and less than 1")
    lam = _positive("poisson_quantile", lambda_, "lambda_")
    return sp.Integer(_discrete_quantile(stats.poisson(lam), qv, None))


# ---------------------------------------------------------------- sampling

def _sample_setup(name: str, n, seed):
    import numpy as np

    count = _integer(name, n, "n", minimum=1)
    if count > MAX_SAMPLE:
        raise StatementError(f"n is too large (max {MAX_SAMPLE})")
    s = _integer(name, seed, "seed")
    return count, np.random.default_rng(s)


def _column(values, integer: bool = False):
    conv = sp.Integer if integer else sp.Float
    return wrap(len(values), 1, [conv(x) for x in values])


def normal_sample(mu, sigma, n, seed):
    m, s = _normal_args("normal_sample", mu, sigma)
    count, rng = _sample_setup("normal_sample", n, seed)
    return _column([float(x) for x in rng.normal(m, s, count)])


def uniform_sample(a, b, n, seed):
    lo, hi = _uniform_args("uniform_sample", a, b)
    count, rng = _sample_setup("uniform_sample", n, seed)
    return _column([float(x) for x in rng.uniform(lo, hi, count)])


def binomial_sample(n_trials, p, n, seed):
    trials = _integer("binomial_sample", n_trials, "n_trials")
    pv = _probability("binomial_sample", p)
    count, rng = _sample_setup("binomial_sample", n, seed)
    return _column([int(x) for x in rng.binomial(trials, pv, count)], integer=True)


def poisson_sample(lambda_, n, seed):
    lam = _positive("poisson_sample", lambda_, "lambda_")
    count, rng = _sample_setup("poisson_sample", n, seed)
    return _column([int(x) for x in rng.poisson(lam, count)], integer=True)


STATS_BUILTINS = {
    "mean": mean, "median": median, "mode": mode,
    "variance": variance, "stdev": stdev,
    "population_variance": population_variance, "population_stdev": population_stdev,
    "quantile": quantile, "covariance": covariance, "correlation": correlation,
    "normal_pdf": normal_pdf, "normal_cdf": normal_cdf, "normal_quantile": normal_quantile,
    "normal_sample": normal_sample,
    "uniform_pdf": uniform_pdf, "uniform_cdf": uniform_cdf,
    "uniform_quantile": uniform_quantile, "uniform_sample": uniform_sample,
    "binomial_pmf": binomial_pmf, "binomial_cdf": binomial_cdf,
    "binomial_quantile": binomial_quantile, "binomial_sample": binomial_sample,
    "poisson_pmf": poisson_pmf, "poisson_cdf": poisson_cdf,
    "poisson_quantile": poisson_quantile, "poisson_sample": poisson_sample,
}
