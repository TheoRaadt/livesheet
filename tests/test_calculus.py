"""Black-box tests for the calculus keywords (tester, requested directly by Theo, not from a
docs/board/specs/ file -- diff/integrate/limit/series/collect/partfrac/apart predate the
spec-driven workflow and are already implemented in livesheet/engine/evaluator.py).

Expected values in this file are derived independently from standard calculus rules (power,
product, quotient and chain rule; substitution and integration by parts; standard limit forms;
Taylor/Maclaurin series) and cross-checked against SymPy itself -- already a project dependency,
and the most reliable ground truth available, per the project's own testing guidance. No
WebSearch tool was available in this tester session, so no external page was fetched for this
file; nothing here is copied from, or checked against, docs/calculus-10th-edition-anton.pdf or
docs/Engineering With Mathcad.pdf (neither was opened).

xfail(strict=True) marks an open defect, see docs/board/reviews/calculus-coverage.md.
"""

import math

import pytest

from livesheet.engine import Engine


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def out(*sources):
    r = run(*sources)[-1]
    assert r.status == "ok", r.error
    return r.output


def err(*sources):
    r = run(*sources)[-1]
    assert r.status == "error", r.output
    return r.error


def numeric(output: str) -> float:
    """Parse '= 11 m/s' / '= 8/3' / '= 28.8 km/hr' style output into a plain float, ignoring unit."""
    text = output.split(None, 1)[1] if output.startswith(("=", "→")) else output
    text = text.split(" ", 1)[0]
    if "/" in text:
        n, d = text.split("/")
        return float(n) / float(d)
    return float(text)


# --- derivatives --------------------------------------------------------------------------------

def test_diff_polynomial():
    assert out("5 x^4 - 3 x^2 + 7 -> diff, x") == "→ 20·x³ - 6·x"
    assert out("x^3 -> diff, x -> diff, x") == "→ 6·x"
    assert out("x^2 -> diff, x -> diff, x") == "→ 2"


def test_diff_product_rule():
    # d/dx(x e^x) = e^x + x e^x
    assert out("x*exp(x) -> diff, x") == "→ x·exp(x) + exp(x)"


def test_diff_quotient_rule():
    # d/dx(sin(x)/x) = cos(x)/x - sin(x)/x^2
    assert out("sin(x)/x -> diff, x") == "→ cos(x)/x - sin(x)/x²"


def test_diff_chain_rule():
    assert out("sin(x^2) -> diff, x") == "→ 2·x·cos(x²)"
    assert out("exp(3 x + 1) -> diff, x") == "→ 3·exp(3·x + 1)"


def test_diff_trig_identity_checked_numerically():
    # d/dx tan(x) = sec(x)^2 = tan(x)^2 + 1; SymPy's canonical form is tan(x)**2 + 1, check both
    # the symbolic form and, independently, the numeric value at a point against math.cos/sin.
    assert out("tan(x) -> diff, x") == "→ tan(x)² + 1"
    val = numeric(out("tan(x) -> diff, x -> substitute, x = 0.3"))
    assert val == pytest.approx(1 / math.cos(0.3) ** 2, rel=1e-5)  # display is 6 significant digits


def test_diff_exp_and_ln():
    assert out("ln(x) -> diff, x") == "→ 1/x"
    # bare 'log' is base 10 by this project's own convention (see evaluator._log), so its
    # derivative carries the ln(10) factor. A float substitution forces full numeric evaluation.
    val = numeric(out("log(x) -> diff, x -> substitute, x = 5.0 -> float"))
    assert val == pytest.approx(1 / (5 * math.log(10)), rel=1e-5)


def test_diff_sqrt_and_power_tower():
    assert out("sqrt(x) -> diff, x") == "→ 1/(2·√(x))"
    # d/dx(x^x) = x^x (ln(x) + 1); at x = 2 that is 4*(ln(2) + 1)
    val = numeric(out("x^x -> diff, x -> substitute, x = 2.0"))
    assert val == pytest.approx(4 * (math.log(2) + 1), rel=1e-5)


def test_diff_with_respect_to_named_variable():
    assert out("x^2*y^3 -> diff, y") == "→ 3·x²·y²"


def test_diff_auto_detects_single_free_variable():
    assert out("3 x + 1 -> diff") == "→ 3"


def test_diff_zero_for_unrelated_variable():
    assert out("x^2 -> diff, z") == "→ 0"


def test_diff_ambiguous_variable_gives_friendly_error():
    assert err("x^2 + y^2 -> diff") == "'diff' needs a variable, e.g. → diff, x"


# --- integrals -----------------------------------------------------------------------------------

def test_integrate_polynomial():
    assert out("x^3 - 2 x -> integrate, x") == "→ x⁴/4 - x²"
    assert out("x -> integrate, x -> integrate, x") == "→ x³/6"


def test_integrate_needs_substitution():
    # u = x^2: d(x^2) = 2x dx, so integral of x e^(x^2) is e^(x^2)/2
    assert out("x*exp(x^2) -> integrate, x") == "→ exp(x²)/2"


def test_integrate_needs_integration_by_parts():
    assert out("x*exp(x) -> integrate, x") == "→ (x - 1)·exp(x)"
    assert out("x*sin(x) -> integrate, x") == "→ -x·cos(x) + sin(x)"


def test_integrate_rational_gives_arctan():
    assert out("1/(x^2 + 1) -> integrate, x") == "→ atan(x)"


def test_integrate_definite_function_form():
    assert out("integrate(2 x, (x, 0, 3)) →") == "→ 9"
    assert out("integrate(x^2, (x, 0, 2)) →") == "→ 8/3"


def test_integrate_natural_log_value_is_correct_even_though_label_is_ambiguous():
    # Whatever the displayed name (see the xfail below for the 'log' vs 'ln' labeling defect),
    # differentiating the result of integrate(1/x, x) must give back 1/x: a label-independent,
    # purely numeric cross-check.
    val = numeric(out("1/x -> integrate, x -> diff, x -> substitute, x = 7.0"))
    assert val == pytest.approx(1 / 7, rel=1e-5)


# --- limits ----------------------------------------------------------------------------------------
# Only the function-call form limit(expr, x, point[, dir]) works; see the xfail below for the
# missing '-> limit, x' keyword form.

def test_limit_removable_discontinuity():
    assert out("limit(sin(x)/x, x, 0) →") == "→ 1"
    assert out("limit((x^2 - 1)/(x - 1), x, 1) →") == "→ 2"


def test_limit_at_infinity():
    assert out("limit(1/x, x, oo) →") == "→ 0"
    assert out("limit(sin(x)/x, x, oo) →") == "→ 0"
    assert out("limit(exp(-x^2/2), x, oo) →") == "→ 0"


def test_limit_definition_of_e():
    assert out("limit((1 + 1/x)^x, x, oo) →") == "→ e"


def test_limit_one_sided():
    assert out("limit(1/x, x, 0, '+') →") == "→ ∞"
    assert out("limit(1/x, x, 0, '-') →") == "→ -∞"


def test_limit_wrong_argument_shapes():
    assert "argument" in err("limit(x) →").lower()
    assert "argument" in err("limit(x, x) →").lower()


# --- series (Maclaurin via the keyword: point is fixed at 0, order is the 2nd argument) -----------

def test_series_exp():
    assert out("exp(x) -> series, x, 5") == "→ x⁴/24 + x³/6 + x²/2 + x + 1"
    assert out("exp(x) -> series, x") == "→ x⁵/120 + x⁴/24 + x³/6 + x²/2 + x + 1"


def test_series_sin_and_cos():
    assert out("sin(x) -> series, x, 6") == "→ x⁵/120 - x³/6 + x"
    assert out("cos(x) -> series, x, 4") == "→ 1 - x²/2"


def test_series_geometric():
    assert out("1/(1 - x) -> series, x, 5") == "→ x⁴ + x³ + x² + x + 1"


def test_series_order_zero_and_one():
    assert out("exp(x) -> series, x, 0") == "→ 0"
    assert out("exp(x) -> series, x, 1") == "→ 1"


def test_series_negative_order_is_an_error():
    assert "nonnegative" in err("exp(x) -> series, x, -1")


def test_series_about_an_explicit_point_function_form():
    # cos(x) near x = pi/2: cos(pi/2 + h) ~= -h, i.e. the linear term is -(x - pi/2).
    text = out("series(cos(x), x, pi/2, 2) →")
    assert "π/2 - x" in text and "O(" in text


# --- engineering: calculus combined with units -----------------------------------------------------

def test_kinematics_velocity_and_acceleration_from_position():
    sheet = ["x0 := 5 m", "v0 := 3 m/s", "accel := 2 m/s^2",
             "x0 + v0*t + accel*t^2/2 -> diff, t -> substitute, t = 4 s"]
    assert out(*sheet) == "→ 11·m/s"  # 3 m/s + 2 m/s^2 * 4 s = 11 m/s
    sheet2 = ["x0 := 5 m", "v0 := 3 m/s", "accel := 2 m/s^2",
              "x0 + v0*t + accel*t^2/2 -> diff, t -> diff, t"]
    assert out(*sheet2) == "→ 2·m/s²"  # constant acceleration recovered


def test_user_defined_position_function_differentiates_to_velocity():
    assert out("x(t) := 5 m + 3 (m/s)*t", "x(t) -> diff, t") == "→ 3·m/s"


def test_momentum_from_kinetic_energy_derivative():
    # d/dv (1/2 m v^2) = m v -- momentum
    assert out("mass := 2 kg", "mass*v^2/2 -> diff, v -> substitute, v = 3 (m/s)") == "→ 6·kg·m/s"


def test_force_recovered_from_work_derivative():
    # d/dx (F x) = F
    assert out("F := 10 N", "xdist := 5 m", "F*xdist -> diff, xdist") == "→ 10·kg·m/s²"  # = 10 N in base units


def test_integral_of_rate_gives_accumulated_quantity_with_correct_unit():
    # accel (m/s^2) integrated over a time interval -> a velocity (m/s), with correct conversion
    assert out("accel := 2 m/s^2", "integrate(accel, (t, 0 s, 4 s)) =") == "= 8 m/s"
    assert out("accel := 2 m/s^2", "integrate(accel, (t, 0 s, 4 s)) = km/hr") == "= 28.8 km/hr"


def test_integral_of_power_gives_energy():
    # power (W) integrated over time -> energy (J = W*s)
    assert out("P := 100 W", "integrate(P, (t, 0 s, 10 s)) =") == "= 1000 J"
    assert out("P := 100 W", "integrate(P, (t, 0 s, 10 s)) = kJ") == "= 1 kJ"


# --- error paths -----------------------------------------------------------------------------------

def test_diff_wrong_argument_shapes():
    assert "argument" in err("diff() →").lower()


def test_diff_numeric_variable_is_rejected():
    assert "number" in err("diff(x^2, 5) →").lower()


def test_calculus_keyword_on_matrix_is_rejected():
    assert "does not apply to matrices" in err("M := [a, b; c, d]", "M -> limit, a")
    assert "does not apply to matrices" in err("M := [a, b; c, d]", "M -> series, a")


def test_calculus_result_with_free_variable_cannot_be_evaluated_numerically():
    assert "not defined" in err("diff(x^3, x) =")


def test_unknown_calculus_like_keyword_still_reports_clearly():
    assert "Unknown keyword" in err("x → frobnicate")


# --- formerly-defects (fixed; see docs/board/reviews/calculus-coverage.md and docs/board/log.md) ---

def test_limit_keyword_pipeline_form():
    # C1: '-> limit, x' keyword form; point defaults to 0, like diff/integrate's single variable.
    assert out("sin(x)/x -> limit, x") == "→ 1"


def test_limit_keyword_pipeline_form_with_explicit_point():
    # C1 extension: an explicit point as a 2nd keyword argument.
    assert out("1/x -> limit, x, oo") == "→ 0"


def test_natural_log_result_should_be_labelled_ln_not_log():
    # C2: a natural log result must display as 'ln', not 'log' (which means base 10 here).
    assert out("1/x -> integrate, x") == "→ ln(x)"


def test_diff_function_call_ambiguous_variable_gives_friendly_error():
    # C3: diff() called directly (not via the '-> diff' keyword) with more than one free
    # variable and no explicit variable must give the same friendly message as the keyword form.
    msg = err("diff(x^2 + y^2) →")
    assert msg == "'diff' needs a variable, e.g. → diff, x"


def test_integrate_function_call_ambiguous_variable_gives_friendly_error():
    # C3, same class of problem for integrate().
    msg = err("integrate(x^2 + y^2) →")
    assert msg == "'integrate' needs a variable, e.g. → integrate, x"


def test_series_function_call_ambiguous_variable_gives_friendly_error():
    # C3, same class of problem for series().
    msg = err("series(x^2 + y^2) →")
    assert msg == "'series' needs a variable, e.g. → series, x"


def test_series_non_integer_order_gives_clean_error():
    # C4: a non-integer series order must give a clean message, not a raw int() ValueError.
    msg = err("exp(x) -> series, x, 2.5")
    assert "int(" not in msg
    assert "whole number" in msg
