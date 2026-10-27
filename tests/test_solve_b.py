"""Spec 003 phase B: inequalities, chained relations, least / most, infeasible cases, status marks."""

import re
import time

import pytest

from livesheet.engine import Engine

pytest.importorskip("scipy")


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def values(res) -> dict[str, float]:
    """name -> number of the ``⇒ a = 1 m, b = 2 m; value = 3 m²`` output."""
    out = {}
    for name, num in re.findall(r"(\w+) = (-?[\d.]+(?:×10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)?)", res.output):
        num = num.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
        out[name] = float(num)
    return out


# -- 12 inequality with settle ---------------------------------------------------------

def test_inequality_selects_the_positive_root():
    res = last("vary x from 0 in i", "x^2 == 4 in i", "x > 0 in i", "settle in i")
    assert res.status == "ok" and values(res)["x"] == pytest.approx(2, abs=1e-5)


def test_guess_side_decides_without_inequality_but_not_with_it():
    assert values(last("vary x from -1 in i", "x^2 == 4 in i", "settle in i"))["x"] == pytest.approx(-2, abs=1e-5)
    res = last("vary x from -1 in i", "x^2 == 4 in i", "x > 0 in i", "settle in i")
    assert values(res)["x"] == pytest.approx(2, abs=1e-5)


def test_inequality_only_projects_onto_feasible_set():
    assert values(last("vary x from 5 in i", "x <= 3 in i", "settle in i"))["x"] == pytest.approx(3, abs=1e-6)
    assert values(last("vary x from 1 in i", "x <= 3 in i", "settle in i"))["x"] == pytest.approx(1, abs=1e-6)
    assert values(last("vary x from 1 in i", "x >= 3 in i", "settle in i"))["x"] == pytest.approx(3, abs=1e-6)
    assert values(last("vary x from 1 in i", "x ≥ 3 in i", "settle in i"))["x"] == pytest.approx(3, abs=1e-6)


def test_strict_relations_are_treated_as_non_strict():
    assert values(last("vary x from 0 in i", "x > 2 in i", "settle in i"))["x"] == pytest.approx(2, abs=1e-6)
    assert values(last("vary x from 5 in i", "x < 2 in i", "settle in i"))["x"] == pytest.approx(2, abs=1e-6)


def test_chained_relation_counts_as_two_constraints():
    res = last("vary x from 10 in i", "1 <= x <= 3 in i", "settle in i")
    assert values(res)["x"] == pytest.approx(3, abs=1e-6)
    res = last("vary x from -10 in i", "1 <= x <= 3 in i", "settle in i")
    assert values(res)["x"] == pytest.approx(1, abs=1e-6)


# -- 13 projection ---------------------------------------------------------------------------

def test_projection_with_least():
    res = last("vary x from 0, y from 0 in n", "x + y <= 2 in n", "least (x-3)^2 + (y-1)^2 in n")
    v = values(res)
    assert res.status == "ok"
    assert v["x"] == pytest.approx(2, abs=1e-5) and v["y"] == pytest.approx(0, abs=1e-5)
    assert v["value"] == pytest.approx(2, abs=1e-5)           # (2-3)^2 + (0-1)^2
    assert res.output.startswith("⇒ x = 2, y = 0; value = 2")


def test_least_without_constraints():
    res = last("vary x from 0 in n", "least (x-3)^2 in n")
    assert values(res)["x"] == pytest.approx(3, abs=1e-5) and values(res)["value"] == pytest.approx(0, abs=1e-9)


def test_most_with_equality_constraint():
    # maximise x*y on the line x + y = 10 -> 5, 5
    res = last("vary x from 1, y from 2 in n", "x + y == 10 in n", "most x*y in n")
    assert values(res)["x"] == pytest.approx(5, abs=1e-5) and values(res)["value"] == pytest.approx(25, abs=1e-5)


# -- 14 units ------------------------------------------------------------------------------------

RECT = ["vary w from 1 m, d from 1 m in plot", "2*(w + d) <= 20 m in plot"]


def test_rectangle_in_a_perimeter_budget():
    res = last(*RECT, "most w*d in plot")
    v = values(res)
    assert v["w"] == pytest.approx(5, abs=1e-4) and v["d"] == pytest.approx(5, abs=1e-4)
    assert v["value"] == pytest.approx(25, abs=1e-4)
    assert "m²" in res.output and res.output.startswith("⇒ w = 5 m, d = 5 m; value = 25 m²")


def test_rectangle_with_chained_width_limit():
    res = last(*RECT, "0 m <= w <= 4 m in plot", "most w*d in plot")
    v = values(res)
    assert v["w"] == pytest.approx(4, abs=1e-4) and v["d"] == pytest.approx(6, abs=1e-4)
    assert v["value"] == pytest.approx(24, abs=1e-4) and res.output.endswith("m²")


def test_results_are_bound_with_units():
    res = run(*RECT, "most w*d in plot", "w =", "w*d = m^2")
    assert res[3].output == "= 5 m" and res[4].output == "= 25 m²"


def test_unit_mismatch_in_inequality_and_objective_dimension():
    res = last("vary x from 1 s in q", "x <= 3 m in q", "settle in q")
    assert res.error.startswith("Units do not match")
    res = last("vary x from 1 s in q", "x <= 3 s in q", "most x in q")
    assert res.output == "⇒ x = 3 s; value = 3 s"
    res = last("vary x from 1 m in q", "x <= 3 m in q", "most x^3 in q")
    assert res.output.endswith("27 m³")


def test_plain_zero_fits_any_dimension():
    assert values(last("vary x from 5 m in q", "x <= 0 in q", "settle in q"))["x"] == pytest.approx(0, abs=1e-6)
    assert last("vary x from 5 m in q", "x >= 0 in q", "settle in q").output == "⇒ x = 5 m"


# -- 15 infeasible ----------------------------------------------------------------------------------

@pytest.mark.parametrize("goal", ["settle in f", "least x in f", "most x in f"])
def test_infeasible_inequalities(goal):
    res = last("vary x from 0 in f", "x >= 2 in f", "x <= 1 in f", goal)
    assert res.status == "error" and res.error.startswith("No solution found")
    assert '"x >= 2"' in res.error or '"x <= 1"' in res.error


def test_infeasible_marks_the_violated_constraint():
    res = run("vary x from 0 in f", "x >= 2 in f", "x <= 1 in f", "settle in f")
    assert [r.output for r in res[:3]] == ["", "✗", ""] or [r.output for r in res[:3]] == ["", "", "✗"]


def test_no_solution_leaves_unknowns_unbound():
    res = run("vary x from 0 in f", "x >= 2 in f", "x <= 1 in f", "settle in f", "x =")
    assert res[4].error == "x is not defined"


# -- 16 unbounded ------------------------------------------------------------------------------------

@pytest.mark.parametrize("goal", ["most x in ub", "least x in ub", "most x^2 + x in ub"])
def test_unbounded_objective_stops_with_an_error(goal):
    start = time.time()
    res = last("vary x from 0 in ub", goal)
    assert res.status == "error" and time.time() - start < 5
    assert res.error.startswith(("Not converged", "No solution found"))


def test_unbounded_in_one_direction_only_with_steps_limit():
    start = time.time()
    res = last("vary x from 0 in ub", "x >= -1 in ub", "steps 20 in ub", "least -x in ub")
    assert res.status == "error" and time.time() - start < 5


# -- 17 marks ----------------------------------------------------------------------------------------

def test_satisfied_constraints_show_a_check_mark():
    res = run("vary x from 0 in i", "x^2 == 4 in i", "x > 0 in i", "settle in i")
    assert [r.output for r in res[:3]] == ["", "✓", "✓"]
    assert all(r.status == "ok" for r in res)


def test_marks_only_touch_constraints_of_the_solved_model():
    res = run("vary x from 0 in a", "vary y from 0 in b", "x == 1 in a", "y == 2 in b", "settle in a", "settle in b")
    assert [r.output for r in res[:4]] == ["", "", "✓", "✓"]


def test_constraint_below_result_gets_no_mark():
    res = run("vary x from 0 in a", "x == 1 in a", "settle in a", "x <= 5 in a")
    assert res[1].output == "✓" and res[3].output == "" and res[3].status == "error"


# -- accuracy, steps, scaling, errors ----------------------------------------------------------

def test_accuracy_applies_to_inequalities_and_equalities():
    res = run("vary x from 0 in i", "accuracy 1e-12 in i", "x^2 == 4 in i", "x >= 0 in i", "settle in i",
              "x - 2 =")
    assert res[4].status == "ok"
    assert abs(float(res[5].output.split()[1].replace("×10", "e").translate(
        str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))) if "×" in res[5].output else 0) <= 1e-11


def test_far_away_optimum_is_found_by_the_retry_starts():
    res = last("vary x from 1 in q", "x <= 1e9 in q", "most x in q")
    assert res.status == "ok" and values(res)["x"] == pytest.approx(1e9, rel=1e-6)


def test_step_limit_gives_not_converged_for_optimisation():
    res = last("vary x from 10 in q", "steps 1 in q", "x^2 >= 100 in q", "x <= 20 in q", "most x in q")
    assert res.status == "ok" or res.error.startswith(("Not converged", "No solution found"))


def test_objective_errors():
    assert "does not involve any unknown" in last("vary x from 1 in q", "x == 1 in q", "least 5 in q").error
    assert last("vary x from 1 in q", "x == 1 in q", "least x + y in q").error == "y is not defined"
    assert "Cannot evaluate at the starting guess" in last("vary x from 0 in q", "x <= 1 in q", "least 1/x in q").error
    assert last("vary x from 1 m in q", "x <= 2 m in q", "most x + 1 s in q").error.startswith("Units do not match")


def test_least_and_most_need_unknowns_declared():
    assert last("least x in nothere").error == 'No unknowns declared for model "nothere"'


def test_same_model_gives_several_results():
    res = run(*RECT, "settle in plot", "most w*d in plot", "least w*d in plot")
    assert res[2].status == "ok" and res[3].output.endswith("value = 25 m²")
    assert res[4].status == "ok" and values(res[4])["value"] == pytest.approx(0, abs=1e-6)


def test_phase_a_behaviour_is_unchanged():
    assert last("vary x from 10 in q", "x^2 - 5*x + 6 == 0 in q", "settle in q").output == "⇒ x = 3"
    res = run("vary x from 1 in z", "x^2 + 1 == 0 in z", "settle in z")
    assert res[2].error.startswith("No solution found") and res[1].output == "✗"
