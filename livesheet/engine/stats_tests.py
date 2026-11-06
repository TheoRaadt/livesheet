"""Hypothesis tests (spec 017, phase S2): one-sample t, Welch two-sample t, chi-square fit.

Regions join a test through a trailing ``in <name>`` tag, collected by ``evaluator.py``'s
``_run_model`` and handed to ``build()`` here, parallel in spirit to ``truss.py``. Nothing
here imports the GUI. ``scipy.stats`` supplies the reference distributions.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sympy as sp

from .matrices import _is_scalar, _is_vector
from .statistics import _vector
from .syntax import Statement, StatementError
from .units import UnitError, measure

if TYPE_CHECKING:  # pragma: no cover
    from .evaluator import Engine

DEFAULT_LEVEL = 0.05
CLAIM_FORMS = ('Use "claim mean == <value>" ("<" or ">" for one-sided), '
               '"claim mean1 == mean2", or "claim fits"')

_CLAIM_RE = re.compile(r"^(mean1|mean)\s*(==|<|>)(?!=)\s*(.+)$", re.DOTALL)


@dataclass
class Claim:
    kind: str          # "one" | "two" | "fits"
    op: str            # "==" | "<" | ">" ("" for fits)
    value_text: str    # one-sample: the claimed value expression
    text: str          # the user's claim text, whitespace-collapsed


@dataclass
class Sample:
    values: list[float]    # SI magnitudes
    dims: tuple


@dataclass
class Model:
    name: str
    samples: list[Sample]
    claim: Claim
    alpha: float
    expected: list[float] | None = None
    value: float | None = None            # one-sample: claimed mean (SI)


@dataclass
class Outcome:
    statistic: float
    df: float
    pvalue: float
    alpha: float
    reject: bool


# -- single-line readers (also used for early validation at the tagged line itself) ----

def parse_claim(text: str) -> Claim:
    clean = " ".join(text.split())
    if clean == "fits":
        return Claim("fits", "", "", clean)
    mt = _CLAIM_RE.match(clean)
    if mt is None:
        raise StatementError(CLAIM_FORMS)
    word, op, rhs = mt.group(1), mt.group(2), mt.group(3).strip()
    if word == "mean1":
        if rhs != "mean2":
            raise StatementError(CLAIM_FORMS)
        return Claim("two", op, "", clean)
    if rhs.startswith("="):
        raise StatementError(CLAIM_FORMS)
    return Claim("one", op, rhs, clean)


def read_sample(engine: "Engine", text: str, env: dict) -> Sample:
    value = engine.parse(text, env)
    ok = (_is_vector(value) if isinstance(value, sp.MatrixBase) else _is_scalar(value))
    if not ok:
        raise StatementError("sample must be a vector")
    _, values, dims = _vector("sample", value)
    return Sample(values, dims)


def read_expected(engine: "Engine", text: str, env: dict) -> list[float]:
    value = engine.parse(text, env)
    ok = (_is_vector(value) if isinstance(value, sp.MatrixBase) else _is_scalar(value))
    if not ok:
        raise StatementError("expected must be a vector")
    _, values, dims = _vector("expected", value)
    if dims:
        raise StatementError("expected values must be dimensionless")
    if any(v <= 0 for v in values):
        raise StatementError("expected values must be positive")
    return values


def read_level(engine: "Engine", text: str, env: dict) -> float:
    meas = measure(engine.parse(text, env))
    if meas.dims or isinstance(meas.magnitude, sp.MatrixBase):
        raise StatementError("level must be a number between 0 and 1")
    try:
        alpha = float(meas.magnitude)
    except (TypeError, ValueError):
        raise StatementError("level must be a number between 0 and 1") from None
    if not 0 < alpha < 1:
        raise StatementError("level must be between 0 and 1")
    return alpha


def check_line(engine: "Engine", st: Statement, env: dict, earlier: list[Statement]) -> None:
    """Validate one tagged line when it is registered (the heavy work waits for ``verdict``)."""
    if st.kind == "model_claim":
        parse_claim(st.expr)
    elif st.kind == "model_setting":
        read_level(engine, st.expr, env)
    elif st.kind == "model_sample":
        read_sample(engine, st.expr, env)
    elif st.kind == "model_expected":
        expected = read_expected(engine, st.expr, env)
        samples = [m for m in earlier if m.kind == "model_sample"]
        if len(samples) == 1:
            try:
                n = len(read_sample(engine, samples[0].expr, env).values)
            except (StatementError, UnitError):
                return
            _check_lengths(len(expected), n)


def _check_lengths(n_expected: int, n_sample: int) -> None:
    if n_expected != n_sample:
        raise StatementError(f"expected has {n_expected} values but sample has {n_sample}")


# -- model assembly ----------------------------------------------------------------------

def build(engine: "Engine", name: str, regions: list[Statement], env: dict) -> Model:
    sample_sts = [s for s in regions if s.kind == "model_sample"]
    expected_sts = [s for s in regions if s.kind == "model_expected"]
    claim_sts = [s for s in regions if s.kind == "model_claim"]
    level_sts = [s for s in regions if s.kind == "model_setting" and s.name == "level"]

    claim = parse_claim(claim_sts[0].expr) if claim_sts else None
    if not sample_sts:
        raise StatementError(f'No sample declared for hypothesis test "{name}"')
    if len(sample_sts) > 2:
        raise StatementError(f'hypothesis test "{name}" has {len(sample_sts)} sample lines, '
                             "expected 1 or 2")
    if claim is None:
        raise StatementError(f'No claim declared for hypothesis test "{name}"')
    if len(claim_sts) > 1:
        raise StatementError(f'Claim already declared for hypothesis test "{name}"')
    if len(level_sts) > 1:
        raise StatementError(f'Level already declared for hypothesis test "{name}"')
    if len(expected_sts) > 1:
        raise StatementError(f'Expected values already declared for hypothesis test "{name}"')

    wanted = 2 if claim.kind == "two" else 1
    if len(sample_sts) != wanted:
        word = "two" if wanted == 2 else "one"
        plural = "lines" if wanted == 2 else "line"
        raise StatementError(f'claim "{claim.text}" needs {word} sample {plural}, '
                             f"found {len(sample_sts)}")
    if claim.kind == "fits" and not expected_sts:
        raise StatementError('claim "fits" needs an expected line')
    if claim.kind != "fits" and expected_sts:
        _report_expected_problem(engine, expected_sts[0], sample_sts[0], env)
        raise StatementError(f'claim "{claim.text}" does not use an expected line')

    samples = [read_sample(engine, s.expr, env) for s in sample_sts]
    alpha = read_level(engine, level_sts[0].expr, env) if level_sts else DEFAULT_LEVEL
    model = Model(name, samples, claim, alpha)
    if claim.kind == "fits":
        model.expected = read_expected(engine, expected_sts[0].expr, env)
        _check_lengths(len(model.expected), len(samples[0].values))
    elif claim.kind == "one":
        model.value = _claimed_value(engine, claim, samples[0], env)
    return model


def _report_expected_problem(engine: "Engine", expected_st: Statement,
                             sample_st: Statement, env: dict) -> None:
    """Surface a more useful cause (bad expected values or a length mismatch) before the
    generic "does not use an expected line" message."""
    expected = read_expected(engine, expected_st.expr, env)
    _check_lengths(len(expected), len(read_sample(engine, sample_st.expr, env).values))


def _claimed_value(engine: "Engine", claim: Claim, sample: Sample, env: dict) -> float:
    meas = measure(engine.parse(claim.value_text, env, keep_units=True))
    if isinstance(meas.magnitude, sp.MatrixBase):
        raise StatementError("claimed mean must be a single value")
    if tuple(meas.dims) != tuple(sample.dims):
        raise UnitError("Units do not match")
    try:
        return float(meas.magnitude)
    except (TypeError, ValueError):
        raise StatementError("claimed mean must be a real number") from None


# -- the tests ---------------------------------------------------------------------------

def solve(model: Model) -> Outcome:
    kind = model.claim.kind
    try:
        if kind == "one":
            statistic, df, p = _one_sample(model)
        elif kind == "two":
            statistic, df, p = _welch(model)
        else:
            statistic, df, p = _chi_square(model)
    except OverflowError:
        raise StatementError("Result too large") from None
    return Outcome(statistic, df, p, model.alpha, p <= model.alpha)


def _mean_var(values: list[float]) -> tuple[float, float]:
    n = len(values)
    m = sum(values) / n
    return m, sum((v - m) ** 2 for v in values) / (n - 1)


def _need_two(model: Model, *lengths: int) -> None:
    if any(n < 2 for n in lengths):
        raise StatementError(f'"{model.name}" needs at least 2 values per sample')


def _tail(t: float, df: float, op: str) -> float:
    from scipy import stats

    if op == "==":
        return min(1.0, 2 * float(stats.t.sf(abs(t), df)))
    return float(stats.t.cdf(t, df) if op == "<" else stats.t.sf(t, df))


def _one_sample(model: Model):
    values = model.samples[0].values
    n = len(values)
    _need_two(model, n)
    m, var = _mean_var(values)
    if var == 0:
        raise StatementError(f'"{model.name}" sample has zero variance; the t statistic is undefined')
    t = (m - model.value) / math.sqrt(var / n)
    df = n - 1
    return t, float(df), _tail(t, df, model.claim.op)


def _welch(model: Model):
    a, b = model.samples
    if tuple(a.dims) != tuple(b.dims):
        raise UnitError("Units do not match")
    n1, n2 = len(a.values), len(b.values)
    _need_two(model, n1, n2)
    m1, v1 = _mean_var(a.values)
    m2, v2 = _mean_var(b.values)
    s1, s2 = v1 / n1, v2 / n2
    if s1 + s2 == 0:
        raise StatementError(f'"{model.name}" samples have zero variance; the t statistic is undefined')
    t = (m1 - m2) / math.sqrt(s1 + s2)
    df = (s1 + s2) ** 2 / (s1 ** 2 / (n1 - 1) + s2 ** 2 / (n2 - 1))
    return t, df, _tail(t, df, model.claim.op)


def _chi_square(model: Model):
    from scipy import stats

    sample = model.samples[0]
    if sample.dims:
        raise UnitError("Units do not match: sample counts must be dimensionless")
    observed, expected = sample.values, model.expected
    _need_two(model, len(observed))
    if sum(observed) == 0:
        raise StatementError(f'"{model.name}" sample counts must not all be zero')
    scale = sum(observed) / sum(expected)
    expected = [e * scale for e in expected]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
    df = len(observed) - 1
    return chi2, float(df), float(stats.chi2.sf(chi2, df))
