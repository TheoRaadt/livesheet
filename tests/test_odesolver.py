"""Spec 010: ODE solving (initial-value problems), symbolic with numeric fallback.

Numbers come straight from the spec's own acceptance criteria (hand-derived there, checked
here against SymPy/SciPy); criterion numbers in comments refer to docs/board/specs/010-ode-solving.md.
"""

import math
import re

import pytest

from livesheet.engine import Engine, parse_statement

pytest.importorskip("scipy")


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def number(text: str) -> float:
    text = text.strip().split()[0]
    text = text.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return float(text)


# -- 1 first order, units ---------------------------------------------------------------

DECAY = [
    "ode diff(y(t), t) + y(t)/tau == 0 in decay",
    "tau := 4 s",
    "start y(0) == 10 m in decay",
]


def test_decay_closed_form_and_evaluation():
    res = run(*DECAY, "evolve in decay", "y(4 s) =", "y(0 s) =")
    evolve, at4, at0 = res[-3], res[-2], res[-1]
    assert evolve.status == "ok" and "y(t) =" in evolve.output
    assert at4.status == "ok" and at4.output.endswith(" m")
    assert number(at4.output[2:]) == pytest.approx(10 * math.exp(-1), abs=1e-4)
    assert at0.output == "= 10 m"


# -- 2 second order -----------------------------------------------------------------------

SHO = [
    "ode diff(y(t), t, 2) + y(t) == 0 in sho",
    "start y(0) == 1, y'(0) == 0 in sho",
]


def test_sho_closed_form():
    res = run(*SHO, "evolve in sho", "y(pi) =", "y(pi/2) =")
    assert res[-2].output == "= -1"
    assert number(res[-1].output[2:]) == pytest.approx(0, abs=1e-6)


# -- 3 coupled linear system --------------------------------------------------------------

FALL = [
    "ode diff(x(t), t) == v(t) in fall",
    "ode diff(v(t), t) == -g in fall",
    "start x(0) == 0 m, v(0) == 0 m/s in fall",
]


def test_free_fall_system_closed_form():
    res = run(*FALL, "evolve in fall", "x(2 s) =", "v(2 s) =")
    assert number(res[-2].output[2:]) == pytest.approx(-19.62, abs=1e-2)
    assert number(res[-1].output[2:]) == pytest.approx(-19.62, abs=1e-2)


# -- 4 binding and scope -------------------------------------------------------------------

def test_scope_reading_order_and_symbolic_display():
    res = run("y := 99", *DECAY, "evolve in decay", "y(t) ->")
    before, evolve, symbolic = res[0], res[-2], res[-1]
    assert before.output == ""   # a plain define shows no '=' text
    assert evolve.status == "ok"
    assert symbolic.status == "ok" and "t" in symbolic.output


# -- 5 evolve symbolic matches plain evolve ------------------------------------------------

@pytest.mark.parametrize("model,result", [
    (DECAY, "evolve"), (SHO, "evolve"), (FALL, "evolve"),
])
def test_evolve_symbolic_matches_plain_evolve(model, result):
    model_name = re.search(r"in (\w+)$", model[0]).group(1)
    plain = last(*model, f"evolve in {model_name}")
    symbolic = last(*model, f"evolve symbolic in {model_name}")
    assert plain.output == symbolic.output and plain.status == "ok"


# -- 6 no closed form (phase A) ------------------------------------------------------------

PEND = [
    "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend",
    "start theta(0) == 0.2, theta'(0) == 0 in pend",
]


def test_pendulum_has_no_closed_form():
    assert last(*PEND, "evolve symbolic in pend").error.startswith("No closed-form solution found")
    # NOTE deviation: both phases are implemented together, so plain/`numeric` evolve on a
    # model with no `over` line now gives criterion 18's own, more informative error instead
    # of phase A's placeholder "Numeric ODE solving is not available yet" (which never exists
    # in the finished system - see the handoff report).
    assert last(*PEND, "evolve in pend").error.startswith('over t from ... to ...')
    assert last(*PEND, "evolve numeric in pend").error.startswith('over t from ... to ...')


# -- 7 units mismatch (see handoff report: this criterion's premise does not reproduce) ----

def test_decay_dimensionless_ic_succeeds_no_mismatch():
    """Deviation from criterion 7: verified with real SymPy that a dimensionless y(0) is just
    as dimensionally self-consistent as 10 m for this homogeneous linear ODE (y's own unit
    cancels out of the only dimension-determining comparison in the equation); dsolve succeeds
    either way. No sound unit check can make this specific case fail without also
    false-positiving on criterion 1's own success case. See handoff report for the full
    argument and the manager/tester follow-up this flags."""
    res = last(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay", "tau := 4 s",
        "start y(0) == 10 in decay", "evolve in decay",
    )
    assert res.status == "ok" and "y(t) =" in res.output


# -- 8 condition-count errors --------------------------------------------------------------

def test_condition_count_errors():
    assert last(*SHO[:1], "start y(0) == 1 in sho", "evolve in sho").error == \
        '"sho" needs 2 initial condition(s) for y, has 1'
    assert last(*SHO[:1], "start y(0) == 1, y'(0) == 0, y''(0) == 0 in sho", "evolve in sho").error == \
        '"sho" needs 2 initial condition(s) for y, has 3'


# -- 9 independent-variable mismatch --------------------------------------------------------

def test_independent_variable_mismatch():
    res = last(
        "ode diff(y(t), t) == -y(t) in bad", "ode diff(z(s), s) == -z(s) in bad",
        "start y(0) == 1, z(0) == 1 in bad", "evolve in bad",
    )
    assert res.error == 'All equations of "bad" must use the same independent variable'


# -- 10 equation-shape error -----------------------------------------------------------------

def test_equation_shape_error():
    res = run("ode y(t) + diff(y(t), t) == 0 in shape")[0]
    assert res.error.startswith("Write the highest derivative alone on the left")


# -- 11 missing result / ordering -------------------------------------------------------------

def test_missing_result_region():
    res = run(DECAY[0], DECAY[2])   # the ode and start lines only, no 'tau :=' define in between
    assert all(r.error == 'No result region for ODE system "decay" below this region' for r in res)


def test_ode_region_below_evolve_is_unused():
    res = run("evolve in late", "ode diff(y(t), t) == -y(t) in late", "start y(0) == 1 in late")
    assert res[0].error == 'No equations declared for ODE system "late"'


# -- 12 isolation and compatibility ------------------------------------------------------------

def test_plain_sheet_unaffected():
    res = run("x := 2", "x =", "table t in m")
    assert res[0].status == "ok" and res[1].output == "= 2" and res[2].status == "error"


def test_solve_block_and_ode_system_coexist():
    res = run(
        "vary x from 0 in q", "x^2 - 5*x + 6 == 0 in q", "settle in q",
        *DECAY[:1], DECAY[1], DECAY[2], "evolve in decay",
    )
    assert res[2].output.startswith("⇒ x =") and res[-1].output.startswith("⇒ y(t) =")


# -- 13 parsing ---------------------------------------------------------------------------------

def test_parsing_ode_line():
    st = parse_statement("ode diff(y(t), t, 2) + y(t) == 0 in sho")
    assert st.kind == "model_ode" and st.model == "sho"


def test_parsing_start_line():
    st = parse_statement("start y(0) == 1, y'(0) == 0 in sho")
    assert st.kind == "model_ic"
    assert st.conditions == [("y", 0, "0", "1"), ("y", 1, "0", "0")]


def test_parsing_over_line():
    st = parse_statement("over t from 0 to 1 points 101 in pend")
    assert (st.kind, st.name, st.expr, st.range_end, st.over_points) == \
        ("model_over", "t", "0", "1", "101")


def test_parsing_evolve_line():
    st = parse_statement("evolve numeric in pend")
    assert (st.kind, st.goal, st.model) == ("model_result", "ode_numeric", "pend")


# -- edge cases --------------------------------------------------------------------------------

def test_unknown_function_in_start():
    res = last(
        "ode diff(y(t), t) == -y(t) in m1", "start y(0) == 1, z(0) == 2 in m1", "evolve in m1",
    )
    assert res.error == '"z" is not an equation of ODE system "m1"'


def test_two_point_boundary_value_rejected():
    res = last(
        "ode diff(y(t), t, 2) + y(t) == 0 in bvp", "start y(0) == 1, y'(1) == 0 in bvp", "evolve in bvp",
    )
    assert "same point" in res.error


# -- 14 automatic numeric fallback, energy conservation (phase B) ------------------------------

def test_pendulum_numeric_fallback_energy_conservation():
    res = last(*PEND, "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "ok" and res.output.startswith("⇒ numeric solution, 101 points")
    it, ith = res.columns.index("t"), res.columns.index("theta")
    ts = [number(row[it]) for row in res.rows]
    thetas = [number(row[ith]) for row in res.rows]
    dt = ts[1] - ts[0]
    e0 = -math.cos(0.2)
    for k in range(1, len(ts) - 1):
        omega = (thetas[k + 1] - thetas[k - 1]) / (2 * dt)
        assert 0.5 * omega ** 2 - math.cos(thetas[k]) == pytest.approx(e0, abs=1e-3)
        assert abs(thetas[k]) <= 0.2 + 1e-3


# -- 15 numeric cross-check against a known closed form -----------------------------------------

FORCED = ["ode diff(y(t), t) + 2*y(t) == 0 in forced", "start y(0) == 5 in forced"]


def test_numeric_matches_known_closed_form():
    res = last(*FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced")
    iy, it = res.columns.index("y"), res.columns.index("t")
    for row in res.rows:
        t, y = number(row[it]), number(row[iy])
        assert y == pytest.approx(5 * math.exp(-2 * t), abs=1e-4)


def test_numeric_accuracy_independent_of_reported_points():
    sparse = last(*FORCED, "over t from 0 to 2 points 2 in forced", "evolve numeric in forced")
    iy = sparse.columns.index("y")
    assert number(sparse.rows[-1][iy]) == pytest.approx(5 * math.exp(-4), abs=1e-4)


# -- 16 binding and reuse of the numeric case ----------------------------------------------------

def test_numeric_binds_range_variable_and_function():
    res = run(
        *FORCED, "over t from 0 to 2 points 5 in forced", "evolve numeric in forced",
        "t =", "table t, y(t)", "y(1) =", "plot\nover t\nshow y(t)",
    )
    t_eval, table, y_at_1, plot = res[-4], res[-3], res[-2], res[-1]
    assert "range variable" in t_eval.error
    assert table.status == "ok" and len(table.rows) == 5
    assert number(y_at_1.output[2:]) == pytest.approx(5 * math.exp(-2), abs=1e-4)
    assert plot.status == "ok" and len(plot.plot.traces[0].x) == 5


# -- 17 settings -----------------------------------------------------------------------------------

def test_accuracy_setting_still_passes_energy_check():
    res = last(*PEND, "accuracy 1e-3 in pend", "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "ok"


def test_steps_too_low_does_not_converge():
    res = last(*PEND, "steps 1 in pend", "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert res.status == "error" and res.error.startswith("Not converged")


# -- 18 'over' required for the auto/numeric path --------------------------------------------------

def test_over_required_for_numeric_path():
    res = last(*PEND, "evolve in pend")
    assert res.error == 'over t from ... to ... is needed to solve "pend" numerically'


def test_forced_numeric_overrides_existing_closed_form():
    res = last(*DECAY, "over t from 0 s to 8 s in decay", "evolve numeric in decay")
    assert res.status == "ok" and res.output.startswith("⇒ numeric solution")


# -- own test: higher-order single equation reduced to a first-order numeric system -----------------

def test_sho_numeric_matches_cos():
    res = last(*SHO, "over t from 0 to 3.14159265 points 50 in sho", "evolve numeric in sho")
    iy, it = res.columns.index("y"), res.columns.index("t")
    for row in res.rows:
        t, y = number(row[it]), number(row[iy])
        assert y == pytest.approx(math.cos(t), abs=1e-4)


# -- D1 fix (independent review follow-up): cross-order IC dimensions ----------------------------
#
# docs/board/reviews/010-ode-solving.md's defect D1: a single function's several
# initial-condition orders were never cross-checked against each other for dimensional
# consistency, in either solving path. Fixed in odesolver.build() (once, up front, before
# any SymPy/SciPy call): order 0 fixes a function's own dimension; order N must then be
# order 0's dimension divided by the independent variable's own dimension to the N-th
# power (inferred from an 'over' line's start value when one is declared, dimensionless
# otherwise). A bare, unitless zero is exempt (same "zero fits any dimension" convention
# already used for a shared initial point).

def test_d1_symbolic_cross_order_ic_dimension_mismatch_rejected():
    # y(0) in metres, y'(0) dimensionless (nonzero): no independent variable's dimension
    # could make m and "dimensionless" simultaneously consistent with the same order-0
    # reference, since 1 m's own dimension is never dimensionless to begin with.
    res = last(
        "ode diff(y(t), t, 2) + y(t) == 0 in shoX",
        "start y(0) == 1 m, y'(0) == 1 in shoX",
        "evolve in shoX",
    )
    assert res.status == "error" and "Units do not match" in res.error


def test_d1_numeric_cross_order_ic_dimension_mismatch_rejected():
    # y(0) in metres, y'(0) given in SECONDS instead of the required m/s (t is dimensionless
    # here, from "over t from 0 to 1", so y' must share y's own dimension, metres).
    res = last(
        "ode diff(y(t), t, 2) + y(t) == 0 in shoNum",
        "start y(0) == 1 m, y'(0) == 2 s in shoNum",
        "over t from 0 to 1 points 3 in shoNum",
        "evolve numeric in shoNum",
    )
    assert res.status == "error" and "Units do not match" in res.error


def test_d1_consistent_cross_order_units_still_accepted():
    # The legitimate case the fix must not false-positive on: y in metres, t in seconds (from
    # 'over'), y' correctly given in m/s -- matches the expected m/s = m / s ratio exactly.
    res = last(
        "ode diff(y(t), t, 2) + y(t) == 0 in shoOK",
        "start y(0) == 1 m, y'(0) == 1 m/s in shoOK",
        "over t from 0 s to 1 s points 3 in shoOK",
        "evolve numeric in shoOK",
    )
    assert res.status == "ok" and res.output.startswith("⇒ numeric solution, 3 points")


def test_d1_zero_higher_order_condition_still_exempt():
    # The pre-existing, already-relied-on pattern (SHO/pendulum's own "y'(0) == 0") must
    # keep working: a bare zero carries no real dimensional information either way.
    res = last(*SHO, "evolve in sho")
    assert res.status == "ok" and "y(t) =" in res.output


def test_d1_minor_duplicate_order_condition_rejected():
    # Minor finding alongside D1: a duplicate same-order condition for one function used to
    # silently keep the last value with no warning; now rejected the same "declared twice"
    # way solver.declare() already rejects a repeated 'vary' guess (spec 003).
    res = last(
        "ode diff(y(t), t) + y(t) == 0 in dupe",
        "start y(0) == 1, y(0) == 2 in dupe",
        "evolve in dupe",
    )
    assert res.error == '"y" is declared twice in model "dupe"'


def test_d1_minor_duplicate_order_condition_rejected_across_two_start_lines():
    # Same check, but the duplicate is declared across two separate 'start' lines rather
    # than within one.
    res = last(
        "ode diff(y(t), t, 2) + y(t) == 0 in dupe2",
        "start y(0) == 1 in dupe2",
        "start y'(0) == 0, y'(0) == 1 in dupe2",
        "evolve in dupe2",
    )
    assert res.error == '"y\'" is declared twice in model "dupe2"'
