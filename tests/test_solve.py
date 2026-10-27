"""Spec 003 phase A: solve models (vary / constraints / settle), units, tolerance, errors."""

import math
import re
import time

import pytest

from livesheet.engine import Engine, parse_statement

pytest.importorskip("scipy")


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def numbers(text: str) -> list[float]:
    text = text.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


def values(res) -> list[float]:
    """Numbers after each ``name =`` of a result output."""
    return [float(m) for m in re.findall(r"= (-?[\d.]+(?:e-?\d+)?)", res.output)]


QUAD = ["vary x from 0 in q", "x^2 - 5*x + 6 == 0 in q"]


# -- 1 quadratic -------------------------------------------------------------------

def test_quadratic_two_roots_by_guess():
    res = last(*QUAD, "settle in q")
    assert res.status == "ok" and res.output.startswith("⇒ x = ")
    assert values(res) == [pytest.approx(2, abs=1e-6)]
    res = last("vary x from 10 in q", QUAD[1], "settle in q")
    assert values(res) == [pytest.approx(3, abs=1e-6)]


def test_unknown_is_bound_after_success():
    assert last("vary x from 10 in q", QUAD[1], "settle in q", "x =").output == "= 3"


# -- 2 nonlinear pair -------------------------------------------------------------------

def test_circle_and_hyperbola():
    start = time.time()
    res = last("vary x from 4.2, y from 2.8 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c")
    assert time.time() - start < 1
    assert values(res) == [pytest.approx(4, abs=1e-6), pytest.approx(3, abs=1e-6)]
    res = last("vary x from 2.8, y from 4.2 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c")
    assert values(res) == [pytest.approx(3, abs=1e-6), pytest.approx(4, abs=1e-6)]


def test_residuals_of_pair_are_tiny():
    res = run("vary x from 4.2, y from 2.8 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c",
              "r1 := x^2 + y^2 - 25", "r2 := x*y - 12", "r1 =", "r2 =")
    for r in res[-2:]:
        assert abs(numbers(r.output)[0]) <= 1e-8 * 25


# -- 3 / 4 units and scope ---------------------------------------------------------------

FALL = ["vary t from 1 s in fall", "h := 20 m", "0.5*g*t^2 == h in fall"]


def test_free_fall_time_with_units():
    res = last(*FALL, "settle in fall")
    expected = math.sqrt(2 * 20 / 9.80665)           # independent of the engine
    assert expected == pytest.approx(2.01962, abs=1e-5)  # spec number checked
    assert res.output.endswith(" s")
    assert values(res) == [pytest.approx(expected, abs=1e-4)]


def test_guess_in_other_unit_gives_same_result():
    a = values(last(*FALL, "settle in fall"))[0]
    b = values(last("vary t from 0.01 min in fall", *FALL[1:], "settle in fall"))[0]
    assert b == pytest.approx(a, abs=1e-5)


def test_guess_with_wrong_dimension():
    res = last("vary t from 1 m in fall", *FALL[1:], "settle in fall")
    assert res.status == "error" and res.error.startswith("Units do not match")


def test_binding_follows_reading_order():
    res = run("t =", *FALL, "settle in fall", "t =", "t = min")
    assert res[0].status == "error"                       # above the result region: still undefined
    assert res[-2].output.startswith("= 2.0196") and res[-2].output.endswith(" s")
    assert res[-1].output.endswith(" min")


# -- 5 tolerance --------------------------------------------------------------------------

def test_accuracy_setting():
    res = run("vary x from 10 in q", "accuracy 1e-12 in q", QUAD[1], "settle in q", "r := x^2 - 5*x + 6", "r =")
    assert res[3].status == "ok"
    assert abs(numbers(res[-1].output)[0]) <= 1e-12 * 6


@pytest.mark.parametrize("bad", ["0", "2", "-1", "1"])
def test_accuracy_out_of_range(bad):
    res = run(*QUAD, f"accuracy {bad} in q", "settle in q")
    assert res[-1].status == "error" and res[-1].error == "accuracy must be a positive number below 1"
    assert res[2].status == "error"        # the setting region reports it too


def test_steps_must_be_whole_number():
    res = last(*QUAD, "steps 2.5 in q", "settle in q")
    assert res.error == "steps must be a whole number of at least 1"
    assert last(*QUAD, "steps 0 in q", "settle in q").status == "error"


# -- 6 / 7 failures -----------------------------------------------------------------------

def test_no_solution():
    res = run("vary x from 1 in z", "x^2 + 1 == 0 in z", "settle in z", "x =")
    assert res[2].status == "error" and res[2].error.startswith("No solution found")
    assert '"x^2 + 1 == 0"' in res[2].error
    assert res[3].status == "error" and res[3].error == "x is not defined"


def test_not_converged_with_one_step():
    res = last("vary x from 10 in q", "steps 1 in q", QUAD[1], "settle in q")
    assert res.status == "error" and res.error.startswith("Not converged")
    assert last("vary x from 10 in q", "steps 200 in q", QUAD[1], "settle in q").status == "ok"


# -- 8 error kinds ------------------------------------------------------------------------

def test_unknown_model():
    assert last("settle in nothere").error == 'No unknowns declared for model "nothere"'


def test_duplicate_unknown():
    res = last("vary x from 1 in m", "vary x from 2 in m", "x == 3 in m", "settle in m")
    assert '"x" is declared twice' in res.error


def test_undefined_symbol_in_constraint():
    res = last("vary x from 1 in q", "x + y == 3 in q", "settle in q")
    assert res.error == "y is not defined"


def test_constraint_without_unknown():
    res = last("vary x from 1 in q", "5 == 5 in q", "settle in q")
    assert "does not involve any unknown" in res.error


def test_constraint_unit_mismatch():
    res = last("vary x from 1 s in q", "x == 3 m in q", "settle in q")
    assert res.error.startswith("Units do not match")


def test_constraint_without_result_below():
    res = run("vary x from 1 in q", "x == 2 in q")
    assert [r.error for r in res] == ['No result region for model "q" below this region'] * 2


def test_constraint_below_result_is_not_used():
    res = run("vary x from 0 in q", QUAD[1], "settle in q", "x == 7 in q", "x =")
    assert res[2].status == "ok" and values(res[2]) == [pytest.approx(2, abs=1e-6)]
    assert res[3].error == 'No result region for model "q" below this region'
    assert res[4].output == "= 2"


def test_no_constraints():
    assert "No constraints" in last("vary x from 1 in q", "settle in q").error


def test_broken_region_blocks_result():
    res = run("vary x from 1 in q", "x^2 +* 1 == 0 in q", "settle in q")
    assert res[1].status == "error"
    assert res[2].error == 'Fix the errors in the regions of model "q" first'


def test_cannot_evaluate_at_guess():
    res = last("vary x from 0 in q", "1/x == 2 in q", "settle in q")
    assert res.status == "error" and "Cannot evaluate at the starting guess" in res.error


# -- 9 underdetermined / overdetermined ---------------------------------------------------

def test_underdetermined_picks_point_closest_to_guess():
    res = last("vary x from 0, y from 0 in u", "x + y == 2 in u", "settle in u")
    assert values(res) == [pytest.approx(1, abs=1e-5), pytest.approx(1, abs=1e-5)]


def test_overdetermined_consistent_and_inconsistent():
    ok = last("vary x from 0 in o", "x == 2 in o", "2*x == 4 in o", "settle in o")
    assert values(ok) == [pytest.approx(2, abs=1e-6)]
    bad = last("vary x from 0 in o", "x == 2 in o", "x == 3 in o", "settle in o")
    assert bad.status == "error" and bad.error.startswith("No solution found")


def test_underdetermined_with_units():
    res = last("vary a from 1 m, b from 1 m in u", "a + b == 4 m in u", "settle in u")
    assert res.output.count(" m") == 2 and values(res) == [pytest.approx(2, abs=1e-5)] * 2


# -- 10 isolation / compatibility --------------------------------------------------------

def test_two_models_do_not_interact():
    res = run("vary x from 0 in a", "vary y from 0 in b", "x^2 == 4 in a", "y^2 == 9 in b",
              "settle in b", "settle in a")
    assert values(res[4]) == [pytest.approx(3, abs=1e-5)]
    assert values(res[5]) == [pytest.approx(2, abs=1e-5)]
    assert res[4].output.startswith("⇒ y")


def test_keywords_in_ordinary_regions_still_work():
    res = run("least(3, 4) =", "steps := 3", "steps =", "x := 5 m =", "v = km")
    assert res[0].status == "error"            # `least` is not a function, as before
    assert res[1].status == "ok" and res[2].output == "= 3" and res[3].output == "= 5 m"


def test_result_can_be_repeated_and_used_again():
    res = run(*QUAD, "settle in q", "settle in q", "2*x =")
    assert res[2].output == res[3].output and res[4].output == "= 4"


def test_unknown_may_shadow_a_unit_name():
    res = last("vary s from 1 in q", "s^2 == 9 in q", "settle in q")
    assert values(res) == [pytest.approx(3, abs=1e-6)]


def test_function_in_constraint():
    res = last("f(x) := x^2", "vary y from 1 in q", "f(y) == 16 in q", "settle in q")
    assert values(res) == [pytest.approx(4, abs=1e-6)]


# -- 11 parsing ----------------------------------------------------------------------------

def test_parse_vary():
    st = parse_statement("vary x from 1 m, y from 2 in p")
    assert (st.kind, st.model, st.guesses) == ("model_vary", "p", [("x", "1 m"), ("y", "2")])


def test_parse_settle_and_results():
    st = parse_statement("settle in p")
    assert (st.kind, st.goal, st.model) == ("model_result", "root", "p")
    assert parse_statement("least x^2 in p").goal == "min"
    assert parse_statement("most(x) in p").goal == "max"


def test_parse_chained_and_unicode_relations():
    assert parse_statement("a <= x <= b in p").relations == ["a <= x", "x <= b"]
    assert parse_statement("x ≤ 3 in p") == parse_statement("x <= 3 in p")
    assert parse_statement("x ≥ 3 in p").relations == ["x >= 3"]
    assert parse_statement("x < 3 in p").kind == "model_require"


def test_parse_settings_and_errors():
    st = parse_statement("accuracy 1e-9 in p")
    assert (st.kind, st.name, st.expr) == ("model_setting", "accuracy", "1e-9")
    assert parse_statement("steps 50 in p").name == "steps"
    for text, message in [("settle x in p", "settle takes no expression"),
                          ("least in p", "least/most needs an expression"),
                          ("y in p", 'A relation is required before "in p"'),
                          ("vary x from in p", 'Missing starting guess for "x"'),
                          ("vary x in p", "Use")]:
        with pytest.raises(Exception, match=message):
            parse_statement(text)


def test_untagged_text_parses_as_before():
    assert parse_statement("x := 3 in q").kind == "define"
    assert parse_statement("table t in m").kind == "table"
    assert parse_statement("x == 3").kind == "expression"
    assert parse_statement("v = km/hr").kind == "evaluate"


# -- phase B stays a clear error ----------------------------------------------------------

def test_phase_b_features_are_not_silently_ignored():
    res = last("vary x from 0 in i", "x^2 == 4 in i", "x > 0 in i", "settle in i")
    assert res.status == "error" and "not available yet" in res.error
    res = last("vary x from 0 in i", "x^2 == 4 in i", "least x in i")
    assert res.status == "error" and "not available yet" in res.error


def test_display_of_relations_is_pretty():
    from livesheet.gui.pretty import pretty_source_html

    assert pretty_source_html("x <= 3 in q") == "x ≤ 3 in q"
    assert pretty_source_html("2*(w + d) >= 20 m in plot") == "2·(w + d) ≥ 20 m in plot"


def test_engine_import_does_not_load_scipy():
    import subprocess
    import sys

    code = "import sys, livesheet.engine; print('scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
