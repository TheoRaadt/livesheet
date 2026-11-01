"""Spec 010 (ODE solving) independent black-box tests (tester). Written from
docs/board/specs/010-ode-solving.md's own acceptance criteria and worked examples,
before reading livesheet/odesolver.py's own tests/test_odesolver.py. Expected numbers
are hand-derived (exp/cos/sin closed forms) and cross-checked against an independent
SciPy ``solve_ivp`` call in this file (not through LiveSheet), per the testing skill's
"independent route" rule. See docs/board/reviews/010-ode-solving.md for the review
write-up (including the from-scratch recheck of criteria 7 and 18)."""

import math
import re

import pytest

from livesheet.engine import Engine, parse_statement


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def ok(*sources):
    r = last(*sources)
    assert r.status == "ok", r.error
    return r


def err(*sources):
    r = last(*sources)
    assert r.status == "error", f"expected error, got status={r.status!r} output={r.output!r}"
    return r.error


def num(output: str) -> float:
    """Pull the one trailing number out of an '= 3.67879 m'-style output."""
    mt = re.search(r"(-?[\d.]+(?:[eE][-+]?\d+)?)", output)
    assert mt, output
    return float(mt.group(1))


# -- criterion 1: first order, units --------------------------------------------------

def test_c1_first_order_units():
    r = ok(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve in decay",
    )
    assert "y(t) =" in r.output
    r2 = last(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve in decay",
        "y(4 s) =",
    )
    assert r2.status == "ok"
    assert num(r2.output) == pytest.approx(10 * math.exp(-1), abs=1e-4)
    assert "m" in r2.output
    r3 = last(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve in decay",
        "y(0 s) =",
    )
    assert r3.status == "ok"
    assert num(r3.output) == pytest.approx(10.0, abs=1e-4)


# -- criterion 2: second order ---------------------------------------------------------

def test_c2_second_order():
    base = (
        "ode diff(y(t), t, 2) + y(t) == 0 in sho",
        "start y(0) == 1, y'(0) == 0 in sho",
        "evolve in sho",
    )
    r1 = last(*base, "y(pi) =")
    assert r1.status == "ok"
    assert num(r1.output) == pytest.approx(-1.0, abs=1e-6)
    r2 = last(*base, "y(pi/2) =")
    assert r2.status == "ok"
    assert num(r2.output) == pytest.approx(0.0, abs=1e-6)


# -- criterion 3: coupled linear system (free fall) ------------------------------------

def test_c3_coupled_system_free_fall():
    base = (
        "ode diff(x(t), t) == v(t) in fall",
        "ode diff(v(t), t) == -g in fall",
        "start x(0) == 0 m, v(0) == 0 m/s in fall",
        "evolve in fall",
    )
    rx = last(*base, "x(2 s) =")
    assert rx.status == "ok"
    assert num(rx.output) == pytest.approx(-19.62, abs=1e-2)
    rv = last(*base, "v(2 s) =")
    assert rv.status == "ok"
    assert num(rv.output) == pytest.approx(-19.62, abs=1e-2)


# -- criterion 4: binding and scope -----------------------------------------------------

def test_c4_binding_and_scope():
    results = run(
        "z := y",  # above the model: y not yet bound by it
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve in decay",
        "w := y(2 s)",  # below: sees the bound function
        "w =",
        "y(t) ->",  # symbolic, t still free
    )
    assert results[0].status == "ok"  # y unbound there is not an error, just a free symbol
    assert results[5].status == "ok"
    assert results[6].status == "ok"
    assert num(results[6].output) == pytest.approx(10 * math.exp(-0.5), abs=1e-4)
    r = results[7]
    assert r.status == "ok"
    assert "t" in r.output and "exp" in r.output


# -- criterion 5: evolve symbolic matches plain evolve ---------------------------------

def test_c5_evolve_symbolic_matches_plain():
    plain = ok(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve in decay",
    )
    symbolic = ok(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "evolve symbolic in decay",
    )
    assert plain.output == symbolic.output

    plain3 = ok(
        "ode diff(x(t), t) == v(t) in fall",
        "ode diff(v(t), t) == -g in fall",
        "start x(0) == 0 m, v(0) == 0 m/s in fall",
        "evolve in fall",
    )
    symbolic3 = ok(
        "ode diff(x(t), t) == v(t) in fall",
        "ode diff(v(t), t) == -g in fall",
        "start x(0) == 0 m, v(0) == 0 m/s in fall",
        "evolve symbolic in fall",
    )
    assert plain3.output == symbolic3.output


# -- criterion 6: no closed form (phase A wording superseded by phase B, see review) ---

PEND = (
    "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend",
    "start theta(0) == 0.2, theta'(0) == 0 in pend",
)


def test_c6_no_closed_form_symbolic_forced_errors():
    e = err(*PEND, "evolve symbolic in pend")
    assert e.startswith("No closed-form solution found")


def test_c6_no_closed_form_auto_and_numeric_need_over():
    # Phase B is implemented alongside phase A, so plain `evolve`/`evolve numeric` on a
    # closed-form failure now attempt the numeric fallback instead of stopping at the
    # phase-A-only "not available yet" message -- and since no `over` line exists here,
    # criterion 18's own wording for exactly this case is what actually fires.
    e1 = err(*PEND, "evolve in pend")
    assert e1 == 'over t from ... to ... is needed to solve "pend" numerically'
    e2 = err(*PEND, "evolve numeric in pend")
    assert e2 == 'over t from ... to ... is needed to solve "pend" numerically'


# -- criterion 7: units mismatch (see review for the from-scratch recheck) ------------

def test_c7_dimensionless_ic_on_homogeneous_equation_does_not_error():
    """Spec says this should raise 'Units do not match'; independently reproduced: it
    does not, and no sound unit check can make it error without also rejecting
    criterion 1's own success case. Documented as a dropped/flawed worked example, not
    a failing test here -- see docs/board/reviews/010-ode-solving.md."""
    r = last(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 in decay",
        "evolve in decay",
    )
    assert r.status == "ok"
    assert "y(t) =" in r.output


def test_c7_variant_wrong_dims_caught_downstream():
    """A genuine dimensional inconsistency (one that *does* constrain the equation) is
    still caught -- just at the point the formula is actually evaluated, the same
    "checked at display time" pattern this project already accepted for spec 003."""
    e = err(
        "ode diff(y(t), t) + y(t) == 0 in test2",  # dimensionless coefficient on y
        "start y(0) == 5 in test2",
        "evolve in test2",
        "y(4 s) =",  # t used with a unit now contradicts the dimensionless coefficient
    )
    assert "dimensionless" in e


# -- criterion 8: condition-count errors ------------------------------------------------

def test_c8_missing_condition():
    e = err(
        "ode diff(y(t), t, 2) + y(t) == 0 in sho",
        "start y(0) == 1 in sho",
        "evolve in sho",
    )
    assert e == '"sho" needs 2 initial condition(s) for y, has 1'


def test_c8_extra_condition():
    e = err(
        "ode diff(y(t), t, 2) + y(t) == 0 in sho",
        "start y(0) == 1, y'(0) == 0, y''(0) == 0 in sho",
        "evolve in sho",
    )
    assert e == '"sho" needs 2 initial condition(s) for y, has 3'


# -- criterion 9: independent-variable mismatch -----------------------------------------

def test_c9_independent_variable_mismatch():
    e = err(
        "ode diff(y(t), t) == -y(t) in bad",
        "ode diff(z(s), s) == -z(s) in bad",
        "start y(0) == 1, z(0) == 1 in bad",
        "evolve in bad",
    )
    assert e == 'All equations of "bad" must use the same independent variable'


# -- criterion 10: equation-shape error -------------------------------------------------

def test_c10_equation_shape_error():
    r = last("ode y(t) + diff(y(t), t) == 0 in shape")
    assert r.status == "error"
    assert r.error.startswith("Write the highest derivative alone on the left")


# -- criterion 11: missing result / ordering --------------------------------------------

def test_c11_missing_result_region():
    results = run(
        "ode diff(y(t), t) == -y(t) in noresult",
        "start y(0) == 1 in noresult",
    )
    for r in results:
        assert r.status == "error"
        assert r.error == 'No result region for ODE system "noresult" below this region'


def test_c11_ode_region_below_evolve_is_unused():
    results = run(
        "ode diff(y(t), t) == -y(t) in m7",
        "start y(0) == 1 in m7",
        "evolve in m7",
        "ode diff(y(t), t) == -2*y(t) in m7",  # placed after the result: not used
        "y(1) =",
    )
    assert results[2].status == "ok"
    assert results[4].status == "ok"
    assert num(results[4].output) == pytest.approx(math.exp(-1), abs=1e-5)


# -- criterion 12: isolation and compatibility ------------------------------------------

def test_c12_sheet_without_ode_unaffected():
    # Spot-check: an ordinary definition/evaluation sheet behaves the same with the new
    # odesolver module imported; the existing test_engine.py/test_solve.py suites (not
    # reproduced here) are the real backstop for this criterion.
    r = last("x := 5 m", "x =")
    assert r.status == "ok"
    assert num(r.output) == pytest.approx(5.0, abs=1e-9)


def test_c12_solve_block_and_ode_system_different_tags_no_interaction():
    results = run(
        "vary x from 0 in q",
        "x^2 - 5*x + 6 == 0 in q",
        "settle in q",
        "ode diff(y(t), t) == -y(t) in m6",
        "start y(0) == 1 in m6",
        "evolve in m6",
    )
    assert results[2].status == "ok" and "x = 2" in results[2].output
    assert results[5].status == "ok" and "y(t) =" in results[5].output


# -- criterion 13: parsing ----------------------------------------------------------------

def test_c13_parsing():
    st = parse_statement("ode diff(y(t), t, 2) + y(t) == 0 in sho")
    assert st.kind == "model_ode"
    assert st.model == "sho"

    st = parse_statement("start y(0) == 1, y'(0) == 0 in sho")
    assert st.kind == "model_ic"
    assert st.conditions == [("y", 0, "0", "1"), ("y", 1, "0", "0")]

    st = parse_statement("over t from 0 to 1 points 101 in pend")
    assert st.kind == "model_over"
    assert st.name == "t"
    assert st.expr == "0"
    assert st.range_end == "1"
    assert st.over_points == "101"

    st = parse_statement("evolve numeric in pend")
    assert st.kind == "model_result"
    assert st.goal == "ode_numeric"


# -- criterion 14: automatic numeric fallback, energy conservation ----------------------

def test_c14_pendulum_numeric_fallback_energy_conservation():
    r = ok(*PEND, "over t from 0 to 1 points 101 in pend", "evolve in pend")
    assert r.output.startswith("⇒ numeric solution, 101 points")
    assert r.columns == ["t", "theta"]
    assert len(r.rows) == 101

    def tofloat(cell: str) -> float:
        return float(cell.replace("=", "").strip())

    ts = [tofloat(row[0]) for row in r.rows]
    thetas = [tofloat(row[1]) for row in r.rows]
    assert ts[0] == pytest.approx(0.0, abs=1e-9)
    assert ts[-1] == pytest.approx(1.0, abs=1e-9)

    # derive omega via central differences of the reported theta column (black-box: no
    # access to the model's internal state, only the public table)
    h = ts[1] - ts[0]
    omega = [0.0] * len(ts)
    for i in range(1, len(ts) - 1):
        omega[i] = (thetas[i + 1] - thetas[i - 1]) / (2 * h)
    omega[0] = (thetas[1] - thetas[0]) / h
    omega[-1] = (thetas[-1] - thetas[-2]) / h

    e0 = -math.cos(0.2)
    for theta, om in zip(thetas, omega):
        energy = 0.5 * om ** 2 - math.cos(theta)
        assert energy == pytest.approx(e0, abs=1e-3)
        assert abs(theta) <= 0.2 + 1e-3


def test_c14_cross_check_against_independent_scipy_call():
    """Cross-check against scipy.integrate.solve_ivp called directly (not through
    LiveSheet) -- an independent route, not just hand arithmetic."""
    import numpy as np
    from scipy.integrate import solve_ivp

    def rhs(t, state):
        theta, omega = state
        return [omega, -math.sin(theta)]

    ts = np.linspace(0, 1, 101)
    sol = solve_ivp(rhs, (0, 1), [0.2, 0.0], t_eval=ts, rtol=1e-6)
    assert sol.success

    r = ok(*PEND, "over t from 0 to 1 points 101 in pend", "evolve in pend")
    thetas = [float(row[1].replace("=", "").strip()) for row in r.rows]
    assert thetas == pytest.approx(list(sol.y[0]), abs=1e-4)


# -- criterion 15: numeric cross-check against a known closed form ----------------------

def test_c15_numeric_matches_closed_form():
    r = ok(
        "ode diff(y(t), t) + 2*y(t) == 0 in forced",
        "start y(0) == 5 in forced",
        "over t from 0 to 2 points 5 in forced",
        "evolve numeric in forced",
    )
    expected_t = [0, 0.5, 1, 1.5, 2]
    expected_y = [5 * math.exp(-2 * t) for t in expected_t]
    got_t = [float(row[0].replace("=", "").strip()) for row in r.rows]
    got_y = [float(row[1].replace("=", "").strip()) for row in r.rows]
    assert got_t == pytest.approx(expected_t, abs=1e-6)
    assert got_y == pytest.approx(expected_y, abs=1e-4)
    assert got_y == pytest.approx([5, 1.83940, 0.67668, 0.24894, 0.09158], abs=1e-4)


def test_c15_sparse_grid_same_accuracy():
    r2 = ok(
        "ode diff(y(t), t) + 2*y(t) == 0 in forced2",
        "start y(0) == 5 in forced2",
        "over t from 0 to 2 points 2 in forced2",
        "evolve numeric in forced2",
    )
    assert len(r2.rows) == 2
    last_y = float(r2.rows[-1][1].replace("=", "").strip())
    assert last_y == pytest.approx(5 * math.exp(-4), abs=1e-4)


def test_c15_over_without_points_word_defaults_to_101():
    """`over t from A to B in <name>` with no `points` word at all (not just `points`
    with its own default inside the sub-grammar) still gives spec 004's own 101 default."""
    r = ok(*PEND, "over t from 0 to 1 in pend", "evolve in pend")
    assert r.output.startswith("⇒ numeric solution, 101 points")
    assert len(r.rows) == 101


# -- criterion 16: binding and reuse of the numeric result -------------------------------

def test_c16_binding_and_reuse():
    base = (
        "ode diff(y(t), t) + 2*y(t) == 0 in forced",
        "start y(0) == 5 in forced",
        "over t from 0 to 2 points 5 in forced",
        "evolve numeric in forced",
    )
    r_table = ok(*base, "table t, y(t)")
    assert r_table.columns == ["t", "y(t)"]
    assert len(r_table.rows) == 5
    r_evolve, r_table_full = run(*base, "table t, y(t)")[3], run(*base, "table t, y(t)")[4]
    assert r_table_full.rows == r_evolve.rows  # same 5 rows reported by evolve itself

    r_t = last(*base, "t =")
    assert r_t.status == "error"
    assert "range variable" in r_t.error

    r_y1 = ok(*base, "y(1) =")
    assert num(r_y1.output) == pytest.approx(5 * math.exp(-2), abs=1e-4)
    assert num(r_y1.output) == pytest.approx(0.67668, abs=1e-4)

    r_plot = ok(*base, "plot\nover t\nshow y(t)")
    assert r_plot.plot is not None
    assert len(r_plot.plot.traces) == 1
    assert len(r_plot.plot.traces[0].x) == 5
    assert len(r_plot.plot.traces[0].y) == 5


# -- criterion 17: settings ---------------------------------------------------------------

def test_c17_accuracy_setting_looser_tolerance_still_passes():
    r = ok(
        "accuracy 1e-3 in pend2",
        "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend2",
        "start theta(0) == 0.2, theta'(0) == 0 in pend2",
        "over t from 0 to 1 points 101 in pend2",
        "evolve in pend2",
    )
    assert r.output.startswith("⇒ numeric solution, 101 points")


def test_c17_steps_too_low_errors():
    e = err(
        "steps 1 in pend3",
        "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend3",
        "start theta(0) == 0.2, theta'(0) == 0 in pend3",
        "over t from 0 to 1 points 101 in pend3",
        "evolve in pend3",
    )
    assert e.startswith("Not converged")


# -- criterion 18: `over` required for the auto/numeric path, and the spec's own typo --

def test_c18_over_required_for_auto_and_numeric():
    e1 = err(*PEND, "evolve in pend")
    assert e1 == 'over t from ... to ... is needed to solve "pend" numerically'


def test_c18_forcing_numeric_honoured_even_with_closed_form():
    r = ok(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "over t from 0 s to 8 s in decay",
        "evolve numeric in decay",
    )
    assert r.output.startswith("⇒ numeric solution")


def test_c18_spec_own_example_has_a_typo_reproduced():
    """The spec's own criterion 18 text uses `over tau from 0 s to 8 s in decay` --
    but tau is a parameter of this model, not its independent variable (`t` is).
    Independently reproduced: that literal line errors; the model's actual independent
    variable (`t`) is what `over` must use. See docs/board/reviews/010-ode-solving.md."""
    e = err(
        "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "tau := 4 s",
        "start y(0) == 10 m in decay",
        "over tau from 0 s to 8 s in decay",
        "evolve numeric in decay",
    )
    assert e == '"over" must use the independent variable "t"'


# -- edge cases named in the spec ---------------------------------------------------------

def test_edge_condition_for_undeclared_function():
    e = err(
        "ode diff(y(t), t) == -y(t) in m1",
        "start y(0) == 1, z(0) == 2 in m1",
        "evolve in m1",
    )
    assert e == '"z" is not an equation of ODE system "m1"'


def test_edge_two_point_boundary_conditions_rejected():
    e = err(
        "ode diff(y(t), t, 2) + y(t) == 0 in m2",
        "start y(0) == 1, y'(1) == 0 in m2",
        "evolve in m2",
    )
    assert e == 'All initial conditions of "m2" must be given at the same point'


def test_edge_over_sampling_limits_unit_mismatch():
    e = err(
        "ode diff(y(t), t) + y(t)/tau == 0 in m4",
        "tau := 4 s",
        "start y(0) == 10 m in m4",
        "over t from 0 to 8 s in m4",
        "evolve numeric in m4",
    )
    assert "Units do not match" in e


def test_edge_evolve_bad_trailing_word():
    e = err(
        "ode diff(y(t), t) == -y(t) in m5",
        "start y(0) == 1 in m5",
        "evolve fast in m5",
    )
    assert e == "evolve takes 'symbolic', 'numeric' or nothing"


def test_edge_implicit_only_solution_treated_as_no_closed_form():
    """y*y' == -t is dsolve-able only to an implicit relation (sign ambiguity in y);
    per the spec's open question 7, this counts as 'no closed form', same as a genuine
    NotImplementedError case."""
    e = err(
        "ode diff(y(t), t) == -t/y(t) in impl",
        "start y(0) == 1 in impl",
        "evolve symbolic in impl",
    )
    assert e.startswith("No closed-form solution found")


def test_edge_settings_validation_errors():
    e1 = err(
        "accuracy 2 in badset",
        "ode diff(y(t), t) == -y(t) in badset",
        "start y(0) == 1 in badset",
        "evolve in badset",
    )
    assert e1 == "accuracy must be a positive number below 1"
    e2 = err(
        "steps 0 in badset2",
        "ode diff(y(t), t) == -y(t) in badset2",
        "start y(0) == 1 in badset2",
        "evolve in badset2",
    )
    assert e2 == "steps must be a whole number of at least 1"


def test_edge_evolve_region_before_its_ode_lines_sees_nothing():
    """Ordering is strict: an `evolve` placed above its model's `ode`/`start` lines
    does not somehow look ahead to collect them."""
    results = run(
        "evolve in late",
        "ode diff(y(t), t) == -y(t) in late",
        "start y(0) == 1 in late",
    )
    assert results[0].status == "error"
    assert results[0].error == 'No equations declared for ODE system "late"'


def test_edge_symbolic_multi_function_output_uses_semicolon_separator():
    """Spec: '\"; \" rather than spec 003's \", \" list separator' between a multi-
    function system's clauses."""
    r = ok(
        "ode diff(x(t), t) == v(t) in fall",
        "ode diff(v(t), t) == -g in fall",
        "start x(0) == 0 m, v(0) == 0 m/s in fall",
        "evolve in fall",
    )
    assert "x(t) =" in r.output and "v(t) =" in r.output
    assert "; v(t) =" in r.output
    assert ", v(t) =" not in r.output


def test_edge_higher_order_numeric_matches_closed_form_cos():
    """Cross-check the first-order-system reduction used for the numeric path on a
    genuinely higher-order (2nd order) single equation, against the known cos(t)
    closed form."""
    r = ok(
        "ode diff(y(t), t, 2) + y(t) == 0 in sho2",
        "start y(0) == 1, y'(0) == 0 in sho2",
        "over t from 0 to 3.14159265 points 50 in sho2",
        "evolve numeric in sho2",
    )
    ts = [float(row[0].replace("=", "").strip()) for row in r.rows]
    ys = [float(row[1].replace("=", "").strip()) for row in r.rows]
    for t, y in zip(ts, ys):
        assert y == pytest.approx(math.cos(t), abs=1e-4)


# -- D1 fix (developer follow-up, see docs/board/log.md): cross-order IC dimension -----
# -- mismatch is now rejected up front ---------------------------------------------------
#
# Not one of the spec's 18 numbered acceptance criteria (which only exercise a single
# wrong-dimensioned condition on a model where no real constraint exists at all, see
# criterion 7 above). The review found that the spec's own "Fits current architecture?"
# section's "checking the equation's and each condition's dimensions once, symbolically,
# before calling into SymPy/SciPy" did not in fact happen across a single function's
# several initial-condition orders, for either solving path (defect D1). These two cases,
# originally written to document the bug (`test_defect_...`, asserting the buggy "succeeds
# anyway" behaviour), are updated here by the developer to assert the now-fixed behaviour:
# `odesolver.build()` cross-checks every function's higher-order conditions against its
# own order-0 condition's dimension once, up front, raising "Units do not match" before
# any SymPy/SciPy call is made.

def test_fix_d1_symbolic_cross_order_ic_dimension_mismatch_caught_up_front():
    """y(0) in metres, y'(0) dimensionless (nonzero): a real, generalisable dimensional
    inconsistency between the two conditions of ONE function. Previously this built and
    displayed a formula that adds a metre-valued term to a dimensionless term (clearly
    bogus -- no single unit can describe "y" here), with no error at solve time, only
    surfacing later if and when the formula was evaluated at a nonzero point. Now the
    `evolve` region itself errors up front instead."""
    e = err(
        "ode diff(y(t), t, 2) + y(t) == 0 in shoX",
        "start y(0) == 1 m, y'(0) == 1 in shoX",
        "evolve in shoX",
    )
    assert "Units do not match" in e


def test_fix_d1_numeric_higher_order_ic_dimension_now_checked():
    """y(0) in metres, y'(0) in SECONDS (not m/s -- a plain unit typo, unrelated to the
    function's own dimension and not merely "zero so it doesn't matter", see criterion 7's
    own reasoning above). Previously the numeric path only ever recorded the dimension of
    each function's *order-0* condition and silently discarded every higher order's own
    declared unit, using only its bare magnitude as the internal initial slope -- no error
    was raised anywhere. Now the mismatch is rejected before `solve_ivp` is even called."""
    e = err(
        "ode diff(y(t), t, 2) + y(t) == 0 in shoNum",
        "start y(0) == 1 m, y'(0) == 2 s in shoNum",
        "over t from 0 to 1 points 3 in shoNum",
        "evolve numeric in shoNum",
    )
    assert "Units do not match" in e


def test_fix_d1_minor_duplicate_order_condition_now_rejected():
    """Minor finding noted alongside D1: a duplicate same-order condition for one function
    (`y(0) == 1, y(0) == 2`) used to silently keep the last value with no warning. Now
    rejected the same "declared twice" way spec 003's own duplicate-guess check
    (`solver.declare`) already rejects a repeated `vary` guess."""
    e = err(
        "ode diff(y(t), t) + y(t) == 0 in dupe",
        "start y(0) == 1, y(0) == 2 in dupe",
        "evolve in dupe",
    )
    assert e == '"y" is declared twice in model "dupe"'


def test_edge_complex_free_oscillator_still_formats():
    # diff(y,t,2) + 4*y == 0: characteristic roots are purely imaginary (+-2i); SymPy's
    # own dsolve for real ICs normally expresses this in real sin/cos, not raw complex
    # numbers -- confirm it still produces a usable, real-valued closed form.
    r = ok(
        "ode diff(y(t), t, 2) + 4*y(t) == 0 in osc",
        "start y(0) == 1, y'(0) == 0 in osc",
        "evolve in osc",
    )
    assert "y(t) =" in r.output
    r2 = last(
        "ode diff(y(t), t, 2) + 4*y(t) == 0 in osc",
        "start y(0) == 1, y'(0) == 0 in osc",
        "evolve in osc",
        "y(0) =",
    )
    assert r2.status == "ok"
    assert num(r2.output) == pytest.approx(1.0, abs=1e-6)


# -- headless GUI-level pass (QT_QPA_PLATFORM=offscreen): a real Worksheet/MathRegion/ ---
# -- PlotRegion recalculation, not just Engine().evaluate() directly --------------------
#
# These exercise the same production GUI code a visible window would (region text ->
# Worksheet.recalculate() -> MathRegion.set_result()/PlotRegion.set_result() -> table/
# chart rendering), through Qt's own offscreen platform plugin. They are NOT a substitute
# for watching the real app on screen -- see the review's "Coverage gaps" section, this
# session had no computer-use tool available to do that pass.

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.gui.worksheet import Worksheet  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_gui_numeric_ode_result_renders_as_a_real_table_region():
    _app()
    sheet = Worksheet()
    lines = [
        "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pendG",
        "start theta(0) == 0.2, theta'(0) == 0 in pendG",
        "over t from 0 to 1 points 11 in pendG",
        "evolve in pendG",
    ]
    for i, text in enumerate(lines):
        sheet.add_region("math", QPointF(0, i * 40), text)
    sheet.recalculate()
    regions = sorted(sheet.regions(), key=lambda r: r.pos().y())
    evolve_region = regions[-1]
    assert evolve_region.result is not None
    assert evolve_region.result.status == "ok"
    assert evolve_region.result.output.startswith("⇒ numeric solution, 11 points")
    # The region's on-screen result item is the same table-rendering path `table`
    # statements use (format_table), confirmed non-empty and containing the header.
    html = evolve_region.result_item.toHtml()
    assert "theta" in html and "<pre" in html


def test_gui_symbolic_ode_result_usable_in_a_real_plot_region():
    _app()
    sheet = Worksheet()
    lines = [
        "ode diff(y(t), t) + y(t)/tau == 0 in decayG",
        "tau := 4 s",
        "start y(0) == 10 m in decayG",
        "evolve in decayG",
    ]
    for i, text in enumerate(lines):
        sheet.add_region("math", QPointF(0, i * 40), text)
    plot = sheet.add_region("plot", QPointF(0, 200), "plot\nover t from 0 s to 8 s\nshow y(t)")
    sheet.recalculate()
    assert plot.result is not None
    assert plot.result.status == "ok", plot.result.error
    assert plot.result.plot is not None
    assert len(plot.result.plot.traces) == 1
    assert len(plot.result.plot.traces[0].x) == 101  # default point count


def test_gui_lsheet_round_trip_of_an_ode_sheet():
    """An ODE sheet is just plain-text regions (spec's own "unchanged" claim for
    document.py); confirm a real save/load cycle through Worksheet preserves it and the
    reloaded sheet still evaluates."""
    import tempfile
    from pathlib import Path

    from livesheet.document import SheetDocument

    _app()
    sheet = Worksheet()
    for i, text in enumerate(["ode diff(y(t), t) == -y(t) in rtg", "start y(0) == 1 in rtg",
                               "evolve in rtg", "y(1) ="]):
        sheet.add_region("math", QPointF(0, i * 40), text)
    sheet.recalculate()
    doc = sheet.to_document()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ode_roundtrip.lsheet"
        doc.save(str(path))
        reloaded = SheetDocument.load(str(path))
    sheet2 = Worksheet()
    sheet2.load_document(reloaded)
    sheet2.recalculate()
    texts = sorted((r.pos().y(), r.source) for r in sheet2.regions())
    assert [t for _, t in texts] == [
        "ode diff(y(t), t) == -y(t) in rtg", "start y(0) == 1 in rtg",
        "evolve in rtg", "y(1) =",
    ]
    last_region = max(sheet2.regions(), key=lambda r: r.pos().y())
    assert last_region.result is not None and last_region.result.status == "ok"
    assert num(last_region.result.output) == pytest.approx(math.exp(-1), abs=1e-5)
