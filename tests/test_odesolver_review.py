"""Independent black-box review of spec 010 (ODE solving).

Written from docs/board/specs/010-ode-solving.md's own acceptance criteria (1-18) and its
Edge cases section, exercised only via ``Engine().evaluate([...])`` as the spec's own
"Acceptance criteria" preamble describes -- not by reading livesheet/engine/odesolver.py or
tests/test_odesolver.py first. Numeric expectations (criteria 1-3, 14-15, 17) were
independently hand-derived/cross-checked against plain Python math (``math.exp``,
``math.cos``) before writing the assertions, as the tester's own playbook requires.

Also specifically probes the six disclosed deviations and the one bug fix logged in
docs/board/log.md's latest entry.
"""

from __future__ import annotations

import math
import re

import numpy as np
import pytest

from livesheet.engine import Engine, parse_statement

pytest.importorskip("scipy")

DECAY = ["ode diff(y(t), t) + y(t)/tau == 0 in decay", "tau := 4 s", "start y(0) == 10 m in decay"]
SHO = ["ode diff(y(t), t, 2) + y(t) == 0 in sho", "start y(0) == 1, y'(0) == 0 in sho"]
FALL = ["ode diff(x(t), t) == v(t) in fall", "ode diff(v(t), t) == -g in fall",
        "start x(0) == 0 m, v(0) == 0 m/s in fall"]
PEND = ["ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend",
        "start theta(0) == 0.2, theta'(0) == 0 in pend"]
FORCED = ["ode diff(y(t), t) + 2*y(t) == 0 in forced", "start y(0) == 5 in forced"]

G = 9.80665  # this project's own constant, livesheet/engine/units.py


def run(*sources):
    res = Engine().evaluate(list(enumerate(sources)))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def num(text: str) -> float:
    """First number in an output string, tolerant of superscript exponents/minus signs."""
    text = text.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return float(re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)[0])


def value_of(output: str) -> float:
    return num(output.split("=", 1)[1])


# ---------------------------------------------------------------------------------------
# Phase A: criteria 1-13
# ---------------------------------------------------------------------------------------

def test_c1_first_order_with_units():
    res = run(*DECAY, "evolve in decay", "y(4 s) =", "y(0 s) =")
    assert res[3].status == "ok" and "y(t) =" in res[3].output
    assert value_of(res[4].output) == pytest.approx(10 * math.exp(-1), abs=1e-4)
    assert res[4].output.endswith(" m")
    assert res[5].output == "= 10 m"


def test_c2_second_order():
    res = run(*SHO, "evolve in sho", "y(pi) =", "y(pi/2) =")
    assert value_of(res[-2].output) == pytest.approx(-1, abs=1e-6)
    assert value_of(res[-1].output) == pytest.approx(0, abs=1e-6)


def test_c3_coupled_linear_system_free_fall():
    res = run(*FALL, "evolve in fall", "x(2 s) =", "v(2 s) =")
    expected = -G * 2  # v(t) = -g t ; x(t) = -g t^2 / 2, both equal -g*2 at t=2s specifically
    assert value_of(res[-2].output) == pytest.approx(expected, abs=1e-2)
    assert value_of(res[-1].output) == pytest.approx(expected, abs=1e-2)
    assert res[-2].output.endswith(" m")
    assert res[-1].output.endswith(" m/s")


def test_c4_binding_and_scope():
    res = run("y =", *DECAY, "evolve in decay", "y =", "y(t) ->")
    assert res[0].status == "error"  # above the model: y still undefined
    assert res[-2].status == "error"  # below: y is bound as a function, needs an argument
    assert res[-1].output.strip().startswith("→")
    assert "t" in res[-1].output


def test_c5_evolve_symbolic_matches_plain_evolve():
    res_a = run(*DECAY, "evolve in decay", "y(4 s) =")
    res_b = run(*DECAY, "evolve symbolic in decay", "y(4 s) =")
    assert res_a[-2].output == res_b[-2].output
    assert res_a[-1].output == res_b[-1].output

    res_a = run(*SHO, "evolve in sho", "y(pi) =")
    res_b = run(*SHO, "evolve symbolic in sho", "y(pi) =")
    assert res_a[-1].output == res_b[-1].output

    res_a = run(*FALL, "evolve in fall", "x(2 s) =")
    res_b = run(*FALL, "evolve symbolic in fall", "x(2 s) =")
    assert res_a[-1].output == res_b[-1].output


def test_c6_no_closed_form_phase_a():
    r_auto = last(*PEND, "evolve in pend")
    r_sym = last(*PEND, "evolve symbolic in pend")
    r_num = last(*PEND, "evolve numeric in pend")
    assert r_sym.status == "error" and r_sym.error.startswith("No closed-form solution found")
    # DEVIATION 2 (disclosed): since both phases ship together, the auto/numeric paths now
    # require an `over` line instead of literally reporting phase-A's "not available yet" --
    # confirmed deliberately, not a defect; still require *some* clear error either way.
    assert r_auto.status == "error"
    assert r_num.status == "error"


def test_c7_second_half_is_a_count_not_a_unit_question():
    # The spec's second half of criterion 7 points at criterion 8 (wrong count) rather
    # than asserting an error itself for `y(0) == 10 m, y'(0) == 1` (exactly one condition
    # of order 0 and one of order 1 -- the right *count* for a 2nd-order equation). Given
    # the same dimension-cancellation reasoning independently confirmed below for criterion
    # 1/decay, y's own dimension is equally free in the sho model, so this is expected
    # to evaluate ok, not error -- confirmed directly rather than assumed.
    res = last(*SHO[:1], "start y(0) == 1 m, y'(0) == 1 in sho", "evolve in sho")
    assert res.status == "ok"
    assert res.output.startswith("⇒ y(t) =")


def test_c7_deviation_criterion7_scenario1_mathematically_unreproducible():
    """Independent re-derivation of docs/board/log.md's deviation 1: for
    diff(y,t) + y/tau == 0, y's own dimension provably cancels out of the equation's
    internal consistency check (both additive terms are linear in y with the same
    coefficient-shape), so a bare `y(0) == 10` (no unit) cannot be flagged as a unit
    mismatch by any check that still accepts criterion 1's `y(0) == 10 m` as ok -- both
    assign y the exact same role. We verify this by checking the actual implementation
    treats `y`'s own unit as entirely free (any unit, including none, is accepted)."""
    ok_m = last(*DECAY, "evolve in decay")
    assert ok_m.status == "ok"
    no_unit = ["ode diff(y(t), t) + y(t)/tau == 0 in decay2", "tau := 4 s",
               "start y(0) == 10 in decay2", "evolve in decay2"]
    res = last(*no_unit)
    # Per the spec's own text this "should" be an error; independently re-derived (see
    # module docstring + docs/board/log.md) that no principled check can flag this without
    # also flagging criterion 1 -- so we assert the *actual*, reasoned behaviour (ok, not
    # an error), confirming the developer's disclosed deviation rather than the spec's own
    # (mistaken) hand-derivation. This is NOT a pass/fail re-statement of the spec; it is a
    # recorded, confirmed deviation.
    assert res.status == "ok"
    assert res.output.startswith("⇒ y(t) =")


def test_c8_condition_count_errors():
    res = last(*SHO[:1], "start y(0) == 1 in sho", "evolve in sho")
    assert res.status == "error"
    assert res.error == '"sho" needs 2 initial condition(s) for y, has 1'
    res = last(*SHO[:1], "start y(0) == 1, y'(0) == 0, y''(0) == 0 in sho", "evolve in sho")
    assert res.status == "error"
    assert res.error == '"sho" needs 2 initial condition(s) for y, has 3'


def test_c9_independent_variable_mismatch():
    res = last("ode diff(y(t), t) == -y(t) in bad",
               "ode diff(z(s), s) == -z(s) in bad",
               "start y(0) == 1, z(0) == 1 in bad", "evolve in bad")
    assert res.status == "error"
    assert res.error == 'All equations of "bad" must use the same independent variable'


def test_c10_equation_shape_error():
    res = run("ode y(t) + diff(y(t), t) == 0 in shape", "start y(0) == 1 in shape")
    assert res[0].status == "error"
    assert res[0].error.startswith("Write the highest derivative alone on the left")


def test_c11_missing_result_and_ordering():
    res = last("ode diff(y(t), t) == -y(t) in noresult", "start y(0) == 1 in noresult")
    assert res.status == "error"
    assert res.error == 'No result region for ODE system "noresult" below this region'

    res = run("ode diff(y(t), t) == -y(t) in below", "start y(0) == 1 in below",
              "evolve in below", "ode diff(y(t), t) == -2*y(t) in below")
    assert res[2].status == "ok" and value_of_exp(res[2].output) == "exp(-t)"
    assert res[3].status == "error"  # the ode below evolve has no result below *it*


def value_of_exp(output: str) -> str:
    return output.split("=", 1)[1].strip()


def test_c12_isolation_and_compatibility():
    # a plain sheet with none of this feature's keywords: evaluates exactly as any
    # ordinary sheet (sanity: this is also guaranteed by the untouched existing suites).
    res = run("x := 2 m", "x + 3 m =")
    assert res[0].status == "ok" and res[1].output == "= 5 m"
    # a solve-block model (spec 003) and an ODE system coexist untouched
    res = run("x^2 == 4 in alg", "vary x from 1 in alg", "settle in alg", *DECAY, "evolve in decay")
    assert res[2].status == "ok"
    assert res[-1].status == "ok"


def test_c13_parsing():
    st = parse_statement("ode diff(y(t), t, 2) + y(t) == 0 in sho")
    assert st.kind == "model_ode" and st.model == "sho"

    st = parse_statement("start y(0) == 1, y'(0) == 0 in sho")
    assert st.kind == "model_ic"
    assert st.conditions == [("y", 0, "0", "1"), ("y", 1, "0", "0")]

    st = parse_statement("over t from 0 to 1 points 101 in pend")
    assert st.kind == "model_over"
    assert (st.name, st.expr, st.range_end, st.over_points) == ("t", "0", "1", "101")

    st = parse_statement("evolve numeric in pend")
    assert st.kind == "model_result" and st.goal == "ode_numeric"


# ---------------------------------------------------------------------------------------
# Phase B: criteria 14-18
# ---------------------------------------------------------------------------------------

def test_c14_automatic_numeric_fallback_energy_conservation():
    res = last(*PEND, "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "ok"
    assert res.output.startswith("⇒ numeric solution, 101 points")
    cols = res.columns
    idx_theta = cols.index("theta")
    ts = np.array([num(row[0]) for row in res.rows])
    thetas = np.array([num(row[idx_theta]) for row in res.rows])
    omegas = np.gradient(thetas, ts)
    e0 = -math.cos(0.2)
    assert e0 == pytest.approx(-0.98007, abs=1e-5)  # the spec's own quoted value
    for th, om in zip(thetas, omegas):
        assert abs((0.5 * om * om - math.cos(th)) - e0) < 1e-3
    assert all(abs(th) <= 0.2 + 1e-3 for th in thetas)


def test_c15_numeric_cross_check_against_closed_form():
    res = last(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced")
    assert res.status == "ok"
    expected = [5 * math.exp(-2 * t) for t in (0, 0.5, 1, 1.5, 2)]
    got = [num(row[1]) for row in res.rows]
    for g, e in zip(got, expected):
        assert g == pytest.approx(e, abs=1e-4)

    res_sparse = last(*FORCED, "over t from 0 to 2 points 2 in forced", "evolve numeric in forced")
    assert res_sparse.rows[-1][0] == res.rows[-1][0]
    assert num(res_sparse.rows[-1][1]) == pytest.approx(expected[-1], abs=1e-4)


def test_c16_binding_and_reuse():
    res = run(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced",
              "t =", "table t, y(t)", "y(1) =", "plot\nover t\nshow y(t)")
    evolve_res, t_eq, table_res, y1_res, plot_res = res[3], res[4], res[5], res[6], res[7]
    assert t_eq.status == "error" and "range variable" in t_eq.error
    assert table_res.rows == evolve_res.rows
    assert y1_res.output == "= 0.67668" or value_of(y1_res.output) == pytest.approx(0.67668, abs=1e-4)
    assert plot_res.status == "ok" and plot_res.plot is not None
    assert len(plot_res.plot.traces) == 1
    assert len(plot_res.plot.traces[0].x) == 5


def test_c17_settings_accuracy_and_steps():
    res_loose = last(*PEND, "accuracy 1e-3 in pend", "over t from 0 to 1 points 101 in pend",
                     "evolve in pend")
    assert res_loose.status == "ok"
    cols = res_loose.columns
    idx_theta = cols.index("theta")
    ts = np.array([num(row[0]) for row in res_loose.rows])
    thetas = np.array([num(row[idx_theta]) for row in res_loose.rows])
    omegas = np.gradient(thetas, ts)
    e0 = -math.cos(0.2)
    assert max(abs((0.5 * om * om - math.cos(th)) - e0) for th, om in zip(thetas, omegas)) < 1e-2

    res_fail = last(*PEND, "steps 1 in pend", "over t from 0 to 1 points 101 in pend",
                    "evolve in pend")
    assert res_fail.status == "error" and res_fail.error.startswith("Not converged")


def test_c18_over_required_and_forced_numeric_overrides_closed_form():
    res = last(*PEND, "evolve in pend")
    assert res.status == "error"
    assert res.error == 'over t from ... to ... is needed to solve "pend" numerically'

    res = last(*DECAY, "over t from 0 s to 8 s in decay", "evolve numeric in decay")
    assert res.status == "ok"
    assert res.output.startswith("⇒ numeric solution")


# ---------------------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------------------

def test_edge_function_not_given_an_equation():
    res = last("ode diff(y(t), t) == -y(t) in typo", "start z(0) == 1 in typo", "evolve in typo")
    assert res.status == "error"
    assert res.error == '"z" is not an equation of ODE system "typo"'


def test_edge_two_point_boundary_conditions_rejected():
    res = last("ode diff(y(t), t, 2) + y(t) == 0 in bvp",
               "start y(0) == 1 in bvp", "start y'(1) == 0 in bvp", "evolve in bvp")
    assert res.status == "error"
    assert "same point" in res.error


def test_edge_reused_name_shadowed_only_inside_model():
    # the independent-variable name ("t") used as an ordinary variable *before* the model
    # is unaffected until the numeric `evolve` region's own binding (reading order).
    res = run("t := 7", *FORCED, "t =", "over t from 0 to 2 points 5 in forced",
              "evolve numeric in forced", "t =")
    assert res[0].status == "ok"
    assert res[3].status == "ok" and value_of(res[3].output) == pytest.approx(7, abs=1e-9)
    assert res[-1].status == "error"  # now a range variable, below the evolve region


def test_edge_huge_initial_condition_no_overflow():
    res = run("ode diff(y(t), t) + y(t) == 0 in huge", "start y(0) == 1e300 in huge",
              "evolve in huge", "y(1) =")
    assert res[2].status == "ok"
    assert res[3].status == "ok"


def test_edge_complex_closed_form_accepted_real_condition_shown_normally():
    res = run("ode diff(y(t), t, 2) + 2*diff(y(t), t) + 5*y(t) == 0 in cplx",
              "start y(0) == 1, y'(0) == 0 in cplx", "evolve in cplx", "y(0) =")
    assert res[2].status == "ok"
    assert res[3].output == "= 1"


def test_edge_unicode_function_and_variable_names():
    res = run("ode diff(θ(t), t) == -θ(t) in gk", "start θ(0) == 1 in gk",
              "evolve in gk", "θ(0) =")
    assert res[2].status == "ok"
    assert res[3].output == "= 1"


def test_edge_mutually_coupled_nonlinear_system_falls_back_to_numeric():
    """Not one of the 18 numbered criteria, but the spec's own architecture notes call a
    *mutually* coupled (non-topologically-orderable) system out as falling back to numeric
    rather than attempting dsolve_system (deviation 3). Confirm it doesn't crash and
    doesn't silently claim a (wrong) closed form."""
    res = last("ode diff(x(t), t) == y(t)**2 in circ", "ode diff(y(t), t) == x(t)**2 in circ",
              "start x(0) == 1, y(0) == 1 in circ", "over t from 0 to 0.01 points 3 in circ",
              "evolve in circ")
    assert res.status == "ok"
    assert res.output.startswith("⇒ numeric solution")


def test_edge_division_by_zero_in_equation_does_not_crash():
    res = last("ode diff(y(t), t) + y(t)/0 == 0 in divz", "start y(0) == 1 in divz",
              "evolve in divz")
    # whatever the exact wording, this must not be an unhandled exception / traceback leak
    assert res.status == "error"
    assert res.error and "Traceback" not in res.error


# ---------------------------------------------------------------------------------------
# Spec 004 compatibility: the `over` sub-grammar refactor must not change plot behaviour
# ---------------------------------------------------------------------------------------

def test_plot_over_grammar_unaffected_by_refactor():
    res = run("plot\nover t from 0 to 6.283185307179586 points 5\nshow sin(t)")
    assert res[0].status == "ok"
    assert res[0].plot is not None and len(res[0].plot.traces[0].x) == 5
