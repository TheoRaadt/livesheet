"""Spec 010: ODE solving (initial-value problems), phase A (symbolic) + phase B (numeric).

Criteria numbered as in docs/board/specs/010-ode-solving.md's "Acceptance criteria" section.
"""

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


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def numbers(text: str) -> list[float]:
    text = text.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


def value_of(output: str) -> float:
    return numbers(output.split("=", 1)[1])[0]


# -- 1 first-order, units ------------------------------------------------------------------

def test_criterion1_first_order_with_units():
    res = last(*DECAY, "evolve in decay")
    assert res.status == "ok" and "y(t) =" in res.output
    res = run(*DECAY, "evolve in decay", "y(4 s) =", "y(0 s) =")
    assert res[-2].output.endswith(" m") and value_of(res[-2].output) == pytest.approx(
        10 * math.exp(-1), abs=1e-4)
    assert res[-1].output == "= 10 m"


# -- 2 second order --------------------------------------------------------------------------

def test_criterion2_second_order():
    res = run(*SHO, "evolve in sho", "y(pi) =", "y(pi/2) =")
    assert value_of(res[-2].output) == pytest.approx(-1, abs=1e-6)
    assert value_of(res[-1].output) == pytest.approx(0, abs=1e-6)


# -- 3 coupled linear system ------------------------------------------------------------------

def test_criterion3_coupled_system_free_fall():
    res = run(*FALL, "evolve in fall", "x(2 s) =", "v(2 s) =")
    assert value_of(res[-2].output) == pytest.approx(-19.62, abs=1e-2)
    assert value_of(res[-1].output) == pytest.approx(-19.62, abs=1e-2)
    assert res[-2].output.endswith(" m") and res[-1].output.endswith(" m/s")


# -- 4 binding and scope -----------------------------------------------------------------------

def test_criterion4_binding_follows_reading_order():
    res = run("y =", *DECAY, "evolve in decay", "y =", "y(t) ->")
    assert res[0].status == "error"
    assert res[-2].status == "error"  # bound as a function now: needs an argument
    assert res[-1].output.strip().startswith("→") and "t" in res[-1].output


# -- 5 evolve symbolic matches plain evolve whenever a closed form exists -----------------------

def test_criterion5_evolve_symbolic_matches_evolve():
    assert last(*DECAY, "evolve in decay").output == last(*DECAY, "evolve symbolic in decay").output
    assert last(*SHO, "evolve in sho").output == last(*SHO, "evolve symbolic in sho").output
    assert last(*FALL, "evolve in fall").output == last(*FALL, "evolve symbolic in fall").output


# -- 6 no closed form, phase A -----------------------------------------------------------------

def test_criterion6_no_closed_form_symbolic():
    res = last(*PEND, "evolve symbolic in pend")
    assert res.status == "error" and res.error.startswith("No closed-form solution found")
    assert last(*PEND, "evolve in pend").status == "error"


# -- 8 condition-count errors -------------------------------------------------------------------

def test_criterion8_condition_count_errors():
    res = last("ode diff(y(t), t, 2) + y(t) == 0 in sho", "start y(0) == 1 in sho", "evolve in sho")
    assert res.status == "error"
    assert res.error == '"sho" needs 2 initial condition(s) for y, has 1'
    res = last("ode diff(y(t), t, 2) + y(t) == 0 in sho",
              "start y(0) == 1, y'(0) == 0, y''(0) == 0 in sho", "evolve in sho")
    assert res.error == '"sho" needs 2 initial condition(s) for y, has 3'


# -- 9 independent-variable mismatch -------------------------------------------------------------

def test_criterion9_independent_variable_mismatch():
    res = last("ode diff(y(t), t) == -y(t) in bad", "ode diff(z(s), s) == -z(s) in bad",
              "start y(0) == 1, z(0) == 1 in bad", "evolve in bad")
    assert res.error == 'All equations of "bad" must use the same independent variable'


# -- 10 equation-shape error -----------------------------------------------------------------------

def test_criterion10_equation_shape_error():
    res = last("ode y(t) + diff(y(t), t) == 0 in shape")
    assert res.status == "error"
    assert res.error.startswith("Write the highest derivative alone on the left")


# -- 11 missing result / ordering --------------------------------------------------------------

def test_criterion11_missing_result_region():
    res = run(*DECAY[:1], DECAY[2])
    assert all(r.error == 'No result region for ODE system "decay" below this region' for r in res)


def test_criterion11_ode_below_result_not_used():
    res = run(*DECAY, "evolve in decay", DECAY[0])
    assert res[-2].status == "ok" and "y(t) =" in res[-2].output
    assert res[-1].error == 'No result region for ODE system "decay" below this region'


# -- 12 isolation / compatibility ---------------------------------------------------------------

def test_criterion12_isolation_from_solve_models():
    res = run("vary x from 1 in q", "x^2 == 4 in q", "settle in q",
             *DECAY, "evolve in decay")
    assert res[2].status == "ok" and res[2].output.startswith("⇒ x")
    assert res[-1].status == "ok" and "y(t) =" in res[-1].output


def test_criterion12_sheet_without_ode_is_unaffected():
    res = run("x := 3", "x =")
    assert res[-1].output == "= 3"


# -- 13 parsing -----------------------------------------------------------------------------------

def test_criterion13_parsing():
    st = parse_statement("ode diff(y(t), t, 2) + y(t) == 0 in sho")
    assert (st.kind, st.model) == ("model_ode", "sho")
    st = parse_statement("start y(0) == 1, y'(0) == 0 in sho")
    assert (st.kind, st.conditions) == ("model_ic", [("y", 0, "0", "1"), ("y", 1, "0", "0")])
    st = parse_statement("over t from 0 to 1 points 101 in pend")
    assert (st.kind, st.name, st.expr, st.range_end, st.over_points) == \
        ("model_over", "t", "0", "1", "101")
    st = parse_statement("evolve numeric in pend")
    assert (st.kind, st.goal) == ("model_result", "ode_numeric")


# -- 14 automatic numeric fallback with energy conservation --------------------------------------

def test_criterion14_automatic_numeric_fallback_energy_conservation():
    res = last(*PEND, "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "ok" and res.output.startswith("⇒ numeric solution, 101 points")
    ts = [value_of("= " + row[0]) for row in res.rows]
    thetas = [value_of("= " + row[1]) for row in res.rows]
    omegas = np.gradient(thetas, ts)
    e0 = -math.cos(0.2)
    for theta, omega in zip(thetas, omegas):
        assert abs((0.5 * omega ** 2 - math.cos(theta)) - e0) < 1e-3
        assert abs(theta) <= 0.2 + 1e-3


# -- 15 numeric cross-check against a known closed form -------------------------------------------

def test_criterion15_numeric_matches_closed_form():
    res = last(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced")
    assert res.status == "ok"
    expected = [5, 1.83940, 0.67668, 0.24894, 0.09158]
    for row, exp in zip(res.rows, expected):
        assert value_of("= " + row[1]) == pytest.approx(exp, abs=1e-4)


def test_criterion15_sparser_grid_same_accuracy():
    full = last(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced")
    sparse = last(*FORCED, "over t from 0 to 2 points 2 in forced", "evolve numeric in forced")
    assert value_of("= " + full.rows[-1][1]) == pytest.approx(
        value_of("= " + sparse.rows[-1][1]), abs=1e-4)


# -- 16 binding and reuse (numeric) -----------------------------------------------------------------

def test_criterion16_binding_and_reuse():
    res = run(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced",
             "t =", "table t, y(t)", "y(1) =")
    evolve_result = res[3]
    assert res[-3].status == "error"  # t is a range variable
    assert res[-2].rows == evolve_result.rows
    assert value_of(res[-1].output) == pytest.approx(0.67668, abs=1e-4)


def test_criterion16_plot_over_numeric_function():
    res = last(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced",
              "plot\nover t\nshow y(t)")
    assert res.status == "ok" and res.plot is not None
    assert len(res.plot.traces) == 1 and len(res.plot.traces[0].x) == 5


# -- 17 settings ----------------------------------------------------------------------------------

def test_criterion17_accuracy_setting():
    res = last(*PEND, "accuracy 1e-3 in pend", "over t from 0 to 1 points 101 in pend",
              "evolve in pend")
    assert res.status == "ok"
    ts = [value_of("= " + row[0]) for row in res.rows]
    thetas = [value_of("= " + row[1]) for row in res.rows]
    omegas = np.gradient(thetas, ts)
    e0 = -math.cos(0.2)
    assert max(abs((0.5 * om ** 2 - math.cos(th)) - e0) for th, om in zip(thetas, omegas)) < 1e-2


def test_criterion17_steps_too_small():
    res = last(*PEND, "steps 1 in pend", "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "error" and res.error.startswith("Not converged")


# -- 18 over required for the auto/numeric path ----------------------------------------------------

def test_criterion18_over_required_for_numeric():
    res = last(*PEND, "evolve numeric in pend")
    assert res.status == "error"
    res2 = last(*PEND, "evolve in pend")
    assert res2.status == "error"


def test_criterion18_forced_numeric_even_when_closed_form_exists():
    res = last(*DECAY, "over t from 0 s to 8 s in decay", "evolve numeric in decay")
    assert res.status == "ok" and res.output.startswith("⇒ numeric solution")
    assert value_of("= " + res.rows[0][1]) == pytest.approx(10, abs=1e-4)


# -- 7 units mismatch -----------------------------------------------------------------------------
# Disclosed deviation (see docs/board/log.md and docs/board/decisions.md, 2026-10-30): the
# spec's own first scenario here ("start y(0) == 10 in decay", no unit, expecting an error
# starting "Units do not match") is not reproduced -- verified against real SymPy/this
# engine's own units.measure() that y's own dimension cancels out of this specific equation's
# internal consistency regardless of whether it is given as length or dimensionless, so there
# is no genuine unit mismatch to detect here; a check that *would* flag this case also
# incorrectly flags criterion 1 (same equation, "10 m") as an error. The test below instead
# pins down the actual (correct) behaviour: this scenario succeeds.

def test_criterion7_dimensionless_decay_condition_is_not_an_error():
    res = last("ode diff(y(t), t) + y(t)/tau == 0 in decay", "tau := 4 s",
              "start y(0) == 10 in decay", "evolve in decay")
    assert res.status == "ok" and "y(t) =" in res.output


def test_criterion7_wrong_count_is_covered_by_criterion8_not_a_unit_check():
    # An *extra*, wrongly-dimensioned condition on top of criterion 2's sho model's own two
    # ("y(0) == 1, y'(0) == 0") -- only one condition of order 0 is expected besides the
    # declared order 1, so this is a count issue (criterion 8), not a separate unit check,
    # per the spec's own note (its "in decay" tag on this extra line is a typo for "in sho":
    # "decay" has no equations of its own in this scenario).
    res = last(*SHO, "start y(0) == 10 m, y'(0) == 1 in sho", "evolve in sho")
    assert res.status == "error"
    assert res.error == '"sho" needs 2 initial condition(s) for y, has 4'


# -- edge cases -------------------------------------------------------------------------------------

def test_edge_function_without_equation():
    res = last(*DECAY[:1], "tau := 4 s", "start z(0) == 1 in decay", "evolve in decay")
    assert res.error == '"z" is not an equation of ODE system "decay"'


def test_edge_two_point_boundary_rejected():
    res = last("ode diff(y(t), t, 2) + y(t) == 0 in bvp", "start y(0) == 1 in bvp",
              "start y'(1) == 0 in bvp", "evolve in bvp")
    assert res.status == "error"
    assert res.error == 'All conditions of "bvp" must be given at the same point'


def test_edge_sheet_variable_named_like_model_unaffected_outside():
    res = run(*DECAY, "evolve in decay", "t := 5", "t =")
    assert res[-1].output == "= 5"


def test_engine_import_does_not_load_scipy():
    import subprocess
    import sys

    code = "import sys, livesheet.engine; print('scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
