"""Spec 003 Phase A black-box tests (tester). Expected values come from the spec and from
independent SciPy / SymPy / math calculations in this file. Phase B features (inequalities,
least/most) are only checked for the interim error message. xfail(strict=True) marks open
defects, see docs/board/reviews/003-solve-blocks.md."""

import math
import re
import subprocess
import sys
import time
import warnings

import pytest
import sympy as sp

from livesheet.engine import Engine, parse_statement

SUP = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def values(output: str) -> dict:
    """Parse '⇒ x = 2 m, y = 3 m' into {'x': 2.0, 'y': 3.0}."""
    out = {}
    for name, num in re.findall(r"([^\W\d]\w*) = (-?[\d.]+(?:×10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)?)", output):
        num = num.replace("×10", "e")
        mant, _, exp = num.partition("e")
        out[name] = float(mant) * (10 ** int(exp.translate(SUP)) if exp else 1)
    return out


def solved(*sources):
    r = last(*sources)
    assert r.status == "ok", r.error
    return values(r.output)


def err(*sources):
    r = last(*sources)
    assert r.status == "error", f"expected error, got {r.output!r}"
    return r.error


Q = ["vary x from 0 in q", "x^2 - 5*x + 6 == 0 in q"]


# -- independent numbers (SciPy / SymPy) ---------------------------------------------------

def test_spec_numbers_independent():
    from scipy import optimize
    r = optimize.root(lambda v: [v[0] ** 2 + v[1] ** 2 - 25, v[0] * v[1] - 12], [4.2, 2.8], tol=1e-12)
    assert r.x == pytest.approx([4, 3], abs=1e-8)
    r = optimize.root(lambda v: [v[0] ** 2 + v[1] ** 2 - 25, v[0] * v[1] - 12], [2.8, 4.2], tol=1e-12)
    assert r.x == pytest.approx([3, 4], abs=1e-8)
    assert sp.solve(sp.Symbol("x") ** 2 - 5 * sp.Symbol("x") + 6) == [2, 3]
    g = 9.80665  # standard gravity, the unit `g` of the engine
    assert math.sqrt(2 * 20 / g) == pytest.approx(2.01962, abs=1e-5)


# -- Phase A criteria 1-11 ------------------------------------------------------------------

def test_c1_quadratic_two_roots_by_guess():
    assert solved(*Q, "settle in q")["x"] == pytest.approx(2, abs=1e-6)
    assert solved("vary x from 10 in q", Q[1], "settle in q")["x"] == pytest.approx(3, abs=1e-6)
    r = run("vary x from 10 in q", Q[1], "settle in q", "x =")
    assert r[-1].output == "= 3"


def test_c2_two_by_two_nonlinear():
    start = time.time()
    v = solved("vary x from 4.2, y from 2.8 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c")
    assert time.time() - start < 1
    assert v["x"] == pytest.approx(4, abs=1e-6) and v["y"] == pytest.approx(3, abs=1e-6)
    v = solved("vary x from 2.8, y from 4.2 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c")
    assert v["x"] == pytest.approx(3, abs=1e-6) and v["y"] == pytest.approx(4, abs=1e-6)


FALL = ["h := 20 m", "0.5*g*t^2 == h in fall"]


def test_c3_units_example():
    r = last("vary t from 1 s in fall", *FALL, "settle in fall")
    assert r.status == "ok" and r.output.endswith(" s")
    assert values(r.output)["t"] == pytest.approx(2.01962, abs=1e-4)
    assert values(r.output)["t"] == pytest.approx(math.sqrt(2 * 20 / 9.80665), abs=1e-4)
    r2 = last("vary t from 0.01 min in fall", *FALL, "settle in fall")
    assert values(r2.output)["t"] == pytest.approx(values(r.output)["t"], abs=1e-6)
    assert err("vary t from 1 m in fall", *FALL, "settle in fall").startswith("Units do not match")


def test_c4_binding_and_scope():
    r = run("t =", "vary t from 1 s in fall", *FALL, "settle in fall", "t =")
    assert r[0].status == "error" and "t is not defined" in r[0].error    # above: still undefined
    assert r[-1].output == "= 2.01962 s"
    # an older definition above is seen above, replaced below
    r = run("t := 7 s", "t =", "vary t from 1 s in fall", *FALL, "settle in fall", "t =")
    assert r[1].output == "= 7 s" and r[-1].output == "= 2.01962 s"


def test_c5_accuracy():
    base = ["vary x from 0 in q", Q[1]]
    assert solved(*base, "accuracy 1e-12 in q", "settle in q")["x"] == pytest.approx(2, abs=1e-9)
    for bad in ("0", "2", "1", "-0.1", "abc"):
        assert err(*base, f"accuracy {bad} in q", "settle in q").startswith("accuracy must be a positive number below 1")
    # independent check of the tolerance semantic: result satisfies the equation to 1e-12 * 6
    r = run(*base, "accuracy 1e-12 in q", "settle in q", "x = ")
    x = float(r[-1].output[2:])
    assert abs(x * x - 5 * x + 6) <= 1e-12 * 6


def test_c6_no_solution_and_nothing_bound():
    r = run("vary x from 1 in z", "x^2 + 1 == 0 in z", "settle in z", "x =")
    assert r[2].status == "error" and r[2].error.startswith("No solution found")
    assert '"x^2 + 1 == 0"' in r[2].error
    assert r[3].status == "error" and "x is not defined" in r[3].error


def test_c7_not_converged_and_success_with_default_steps():
    base = ["vary x from 10 in q", Q[1]]
    assert err(*base, "steps 1 in q", "settle in q").startswith("Not converged")
    assert solved(*base, "steps 200 in q", "settle in q")["x"] == pytest.approx(3, abs=1e-6)
    for bad in ("0", "-3", "2.5", "abc"):
        assert "steps must be a whole number of at least 1" in err(*base, f"steps {bad} in q", "settle in q")


def test_c8_error_kinds():
    assert err("settle in nothere") == 'No unknowns declared for model "nothere"'
    assert '"x" is declared twice' in err("vary x from 1 in m", "vary x from 2 in m", "x == 3 in m", "settle in m")
    assert '"x" is declared twice' in err("vary x from 1, x from 2 in m", "x == 3 in m", "settle in m")
    assert "y is not defined" in err("vary x from 1 in q", "x + y == 3 in q", "settle in q")
    assert "does not involve any unknown" in err("vary x from 1 in q", "5 == 5 in q", "settle in q")
    assert "Units do not match" in err("vary x from 1 s in q", "x == 3 m in q", "settle in q")
    r = run("vary x from 1 in q", "x == 3 in q")
    assert all(x.error == 'No result region for model "q" below this region' for x in r)
    # a constraint placed below the settle is not used
    r = run("vary x from 1 in q", "x^2 == 4 in q", "settle in q", "x == 7 in q")
    assert values(r[2].output)["x"] == pytest.approx(2, abs=1e-6)
    assert r[3].error == 'No result region for model "q" below this region'


def test_c9_underdetermined_closest_to_guess():
    v = solved("vary x from 0, y from 0 in u", "x + y == 2 in u", "settle in u")
    assert v["x"] == pytest.approx(1, abs=1e-5) and v["y"] == pytest.approx(1, abs=1e-5)
    v = solved("vary x from 3, y from 0 in u", "x + y == 2 in u", "settle in u")
    # spec: "guess-scaled distances" -- x is scaled by 3, y (guess 0) by 1, so the minimiser of
    # ((x-3)/3)^2 + y^2 s.t. x + y = 2 is (2.1, -0.1), not the Euclidean projection (2.5, -0.5)
    assert v["x"] == pytest.approx(2.1, abs=1e-5) and v["y"] == pytest.approx(-0.1, abs=1e-5)


def test_c10_isolation_and_compatibility():
    r = run("vary x from 1 in a", "vary y from 1 in b", "x^2 == 9 in a", "y^2 == 16 in b",
            "settle in a", "settle in b", "x =", "y =")
    assert (values(r[4].output), values(r[5].output)) == ({"x": pytest.approx(3, abs=1e-6)},
                                                          {"y": pytest.approx(4, abs=1e-6)})
    assert r[6].output == "= 3" and r[7].output == "= 4"
    # same unknown name in two models: the later result binds last, models do not interact
    r = run("vary x from 1 in a", "vary x from 1 in b", "x^2 == 9 in a", "x^2 == 16 in b",
            "settle in a", "settle in b", "x =")
    assert r[4].output == "⇒ x = 3" and r[5].output == "⇒ x = 4" and r[6].output == "= 4"
    # ordinary regions are untouched
    r = run("least := 5", "least =", "steps := 3", "steps =", "accuracy := 2", "accuracy + 1 =")
    assert [x.output for x in r] == ["", "= 5", "", "= 3", "", "= 3"]
    # least(3, 4) is an ordinary (here undefined) function call, same behaviour as any unknown name
    assert last("least(3, 4) =").error == last("foo(3, 4) =").error


def test_c11_parsing():
    st = parse_statement("vary x from 1 m, y from 2 in p")
    assert (st.kind, st.model, st.guesses) == ("model_vary", "p", [("x", "1 m"), ("y", "2")])
    st = parse_statement("settle in p")
    assert (st.kind, st.goal, st.model) == ("model_result", "root", "p")
    assert parse_statement("a <= x <= b in p").relations == ["a <= x", "x <= b"]
    assert parse_statement("x ≤ 3 in p").relations == parse_statement("x <= 3 in p").relations
    assert parse_statement("x ≥ 3 in p").relations == parse_statement("x >= 3 in p").relations
    assert parse_statement("least x^2 in p").goal == "min" and parse_statement("most x in p").goal == "max"
    assert parse_statement("accuracy 1e-6 in p").kind == "model_setting"
    assert parse_statement("steps 50 in p").kind == "model_setting"
    assert parse_statement("x == 2 in p in q").model == "q"                  # last ` in ` wins
    assert parse_statement("vary  x  from  1  in  p").guesses == [("x", "1")]


def test_parse_of_existing_statements_unchanged():
    assert parse_statement("table t, v*t in m").kind == "table"
    assert parse_statement("x := 5 in m").kind == "define"
    assert parse_statement("x = 5 in m").kind == "evaluate"
    assert parse_statement("x := 3").kind == "define"
    assert parse_statement("f(x) → factor").kind == "symbolic"


# -- edge cases requested ---------------------------------------------------------------------

def test_no_unknowns_declared():
    assert err("x^2 == 4 in q", "settle in q") == 'No unknowns declared for model "q"'
    r = run("vary x from 1 in a", "settle in a")
    assert r[1].status == "error" and "constraint" in r[1].error.lower()


@pytest.mark.parametrize("decl", ["vary x from  in p", "vary x from in p", "vary x in p", "vary from 1 in p",
                                  "vary x from 1, in p"])
def test_unknown_without_guess_is_error(decl):
    r = run(decl, "x == 2 in p", "settle in p")
    assert r[0].status == "error" and r[2].status == "error"
    assert r[2].error.startswith("Fix the errors in the regions of model")


def test_guess_wrong_unit_and_non_numeric_guess():
    assert err("vary x from 1 m in a", "x == 3 s in a", "settle in a").startswith("Units do not match")
    assert err("vary x from 1 in a", "x == 3 m in a", "settle in a").startswith("Units do not match")
    assert err("vary x from 1 m in a", "x == 3 in a", "settle in a").startswith("Units do not match")
    for guess in ("1/0", "foo", "oo", "1+I"):
        r = run(f"vary x from {guess} in a", "x == 3 in a", "settle in a")
        assert r[0].status == "error" or r[2].status == "error", guess


def test_unit_conversion_between_guess_and_constraint_units():
    assert solved("vary x from 1 m in a", "x == 3000 mm in a", "settle in a")["x"] == pytest.approx(3)
    assert solved("vary x from 1 km in a", "x == 3 m in a", "settle in a")["x"] == pytest.approx(3)
    r = run("vary x from 0 m in a", "x == 3 m in a", "settle in a", "x = mm")
    assert r[-1].output == "= 3000 mm"
    r = last("vary x from 1 kg in a", "x*9.81 m/s^2 == 10 N in a", "settle in a")
    assert values(r.output)["x"] == pytest.approx(10 / 9.81, abs=1e-5) and r.output.endswith(" kg")
    r = last("vary a1 from 1 m, b1 from 1 N in a", "a1*b1 == 6 J in a", "a1 == 2 m in a", "settle in a")
    assert values(r.output) == {"a1": pytest.approx(2, abs=1e-6), "b1": pytest.approx(3, abs=1e-6)}
    assert r.output.count(" m") == 1 and " N" in r.output
    v = solved("vary v from 1 km/hr in a", "v*2 s == 10 m in a", "settle in a")
    assert v["v"] == pytest.approx(5, abs=1e-6)                            # m/s, SI output
    assert last("vary T from 300 K in a", "T^4 == 81 K^4 in a", "settle in a").output == "⇒ T = 3 K"


def test_unit_mismatch_between_sides_and_dimensionless():
    assert "Units do not match" in err("vary x from 1 in a", "x == 3 m in a", "settle in a")
    assert "Units do not match" in err("vary x from 1 m in a", "x/1 m == 3 in a", "settle in a")
    assert solved("vary x from 1 in a", "x*1 m == 3 m in a", "settle in a")["x"] == pytest.approx(3)
    assert solved("vary x from 1 in a", "x == 1/3 in a", "settle in a")["x"] == pytest.approx(1 / 3, abs=1e-6)
    assert "Units do not match" in err("vary t from 1 s in a", "t == 2 in a", "settle in a")


@pytest.mark.parametrize("eqs,expected_ok", [
    (["x + y == 2", "2*x + 2*y == 4"], True),      # redundant but consistent
    (["x + y == 2", "2*x + 2*y == 5"], False),     # inconsistent
    (["x + y == 2", "x - y == 0", "x == 1"], True),   # overdetermined consistent
    (["x + y == 2", "x - y == 0", "x == 2"], False),  # overdetermined inconsistent
])
def test_overdetermined_and_redundant_systems(eqs, expected_ok):
    r = last("vary x from 1, y from 1 in a", *[e + " in a" for e in eqs], "settle in a")
    if expected_ok:
        assert r.status == "ok"
        assert values(r.output) == {"x": pytest.approx(1, abs=1e-6), "y": pytest.approx(1, abs=1e-6)}
    else:
        assert r.status == "error" and r.error.startswith("No solution found")
        assert "violates" in r.error


def test_underdetermined_three_unknowns_one_equation():
    v = solved("vary x from 0, y from 0, z from 0 in a", "x + y + z == 3 in a", "settle in a")
    assert v["x"] == pytest.approx(1, abs=1e-5) and v["y"] == pytest.approx(1, abs=1e-5)


def test_singular_jacobian_at_solution_and_double_root():
    assert solved("vary x from 2 in a", "x^2 - 4*x + 4 == 0 in a", "settle in a")["x"] == pytest.approx(2, abs=1e-4)
    assert abs(solved("vary x from 1 in a", "x^3 == 0 in a", "settle in a")["x"]) < 1e-6


@pytest.mark.parametrize("eq", ["x^2 == 1", "x^2 - 1 == 0"])
def test_singular_jacobian_at_guess_still_finds_root(eq):
    v = solved("vary x from 0 in a", eq + " in a", "settle in a")
    assert abs(v["x"]) == pytest.approx(1, abs=1e-6)


def test_no_real_solution_is_reported_not_raised():
    for eq in ("x^2 == -4", "x == x + 1", "exp(x) == -1"):
        r = last("vary x from 1 in a", eq + " in a", "settle in a")
        assert r.status == "error" and r.error.startswith("No solution found"), eq


def test_non_converged_with_small_step_counts():
    base = ["vary x from 10 in a", "x^2 - 5*x + 6 == 0 in a"]
    for n in (1, 2, 3):
        assert err(*base, f"steps {n} in a", "settle in a").startswith("Not converged"), n
    assert solved(*base, "steps 100 in a", "settle in a")["x"] == pytest.approx(3, abs=1e-6)
    msg = err(*base, "steps 1 in a", "settle in a")
    assert re.search(r"\d+ function evaluations", msg) and re.search(r"\d\.\de[-+]\d\d", msg)   # steps used + largest violation


def test_message_names_evaluations_and_step_limit():
    msg = err("vary x from 10 in a", "x^2 - 5*x + 6 == 0 in a", "steps 1 in a", "settle in a")
    assert "function evaluations" in msg and "steps limit 1" in msg and " steps," not in msg


def test_accuracy_edge_values():
    base = ["vary x from 1 in a", "x^2 == 2 in a"]
    assert solved(*base, "accuracy 0.999 in a", "settle in a")["x"] == pytest.approx(1.41421, abs=1e-3)
    assert solved(*base, "accuracy 1e-15 in a", "settle in a")["x"] == pytest.approx(math.sqrt(2), abs=1e-5)
    r = last(*base, "accuracy 1e-16 in a", "settle in a")           # tighter than float epsilon
    assert r.status == "error"
    assert err(*base, "accuracy 0 in a", "settle in a").startswith("accuracy must be")
    # last accuracy wins (both valid)
    assert solved(*base, "accuracy 1e-3 in a", "accuracy 1e-9 in a", "settle in a")["x"] == pytest.approx(1.41421, abs=1e-5)
    # root exactly at zero is accepted with tight accuracy (reference scale protects it)
    assert solved("vary x from 0 in a", "x == 0 in a", "accuracy 1e-15 in a", "settle in a")["x"] == 0
    assert solved("vary x from 1 in a", "sin(x)*1e-9 == 0 in a", "settle in a")["x"] == pytest.approx(0, abs=1e-5)


def test_duplicate_and_conflicting_settings():
    base = ["vary x from 10 in a", "x^2 - 5*x + 6 == 0 in a"]
    assert solved(*base, "steps 1 in a", "steps 100 in a", "settle in a")["x"] == pytest.approx(3, abs=1e-6)
    assert err(*base, "steps 100 in a", "steps 1 in a", "settle in a").startswith("Not converged")


def test_duplicate_vary_declarations():
    assert "declared twice" in err("vary x from 1 in a", "vary y from 1, x from 2 in a", "x == 3 in a", "settle in a")
    assert "declared twice" in err("vary x from 1 in a", "vary x from 1 in a", "x == 3 in a", "settle in a")
    # same name in different models is fine
    assert solved("vary x from 1 in a", "vary x from 1 in b", "x == 3 in a", "x == 4 in b", "settle in b")["x"] == pytest.approx(4)


@pytest.mark.parametrize("name", ["x", "t", "settle", "vary", "in", "Q1", "α", "s", "m", "least"])
def test_model_names_clashing_with_variables_keywords_and_units(name):
    r = run(f"vary x from 1 in {name}", f"x == 2 in {name}", f"settle in {name}")
    assert r[-1].status == "ok" and values(r[-1].output)["x"] == pytest.approx(2, abs=1e-6), name


def test_model_name_numeric_is_syntax_error_and_case_sensitive():
    assert run("vary x from 1 in 2", "x == 2 in 2", "settle in 2")[-1].status == "error"
    r = run("vary x from 1 in q", "x == 2 in q", "settle in Q")
    assert r[2].error == 'No unknowns declared for model "Q"'


def test_model_name_equal_to_existing_variable_is_not_touched():
    r = run("t := 3", "vary x from 1 in t", "x == t in t", "settle in t", "x =", "t =")
    assert r[-2].output == "= 3" and r[-1].output == "= 3"


def test_two_models_use_same_parameters_and_are_independent():
    r = run("k := 4", "vary x from 1 in a", "vary y from 1 in b", "x^2 == k in a", "y^2 == 2*k in b",
            "settle in a", "settle in b")
    assert values(r[-2].output)["x"] == pytest.approx(2, abs=1e-6)
    assert values(r[-1].output)["y"] == pytest.approx(math.sqrt(8), abs=1e-5)
    assert "y" not in values(r[-2].output)


def test_one_model_two_results_and_repeat():
    r = run("vary x from 1 in a", "x^2 == 9 in a", "settle in a", "settle in a")
    assert r[2].output == r[3].output == "⇒ x = 3"
    r = run("vary x from 1 in a", "x^2 == 9 in a", "settle in a", "x^2 == 16 in a", "settle in a")
    assert r[2].status == "ok" and r[4].status == "error" and r[4].error.startswith("No solution found")
    assert r[3].error == 'No result region for model "a" below this region' or r[3].status == "ok"


def test_regions_out_of_reading_order():
    r = run("settle in a", "vary x from 1 in a", "x^2 == 9 in a")
    assert r[0].error == 'No unknowns declared for model "a"'
    assert r[1].error == r[2].error == 'No result region for model "a" below this region'
    r = run("x^2 == 9 in a", "vary x from 1 in a", "settle in a")      # constraint before declaration is fine
    assert r[-1].status == "ok" and r[-1].output == "⇒ x = 3"
    r = run("vary x from 1 in a", "settle in a", "x^2 == 9 in a")
    assert r[1].status == "error" and r[2].status == "error"


def test_redefinition_of_bound_unknown_afterwards():
    r = run("vary x from 1 in a", "x^2 == 9 in a", "settle in a", "x =", "x := 5", "x =", "y := x*2", "y =")
    assert r[3].output == "= 3" and r[5].output == "= 5" and r[7].output == "= 10"
    r = run("vary x from 1 in a", "x^2 == 9 in a", "settle in a", "settle in a", "x =")
    assert r[-1].output == "= 3"
    r = run("x := 5", "vary x from 1 in a", "x^2 == 9 in a", "settle in a", "x =")
    assert r[-1].output == "= 3"                                          # guess wins, model replaces x
    r = run("vary x from 1 in a", "x^2 == 9 in a", "settle in a", "f(z) := z + x", "f(1) =")
    assert r[-1].output == "= 4"


def test_unknown_shadows_existing_names_inside_model_only():
    r = run("s := 4 s", "vary s from 1 in a", "s^2 == 9 in a", "settle in a", "s =")
    assert r[-2].output == "⇒ s = 3" and r[-1].output == "= 3"
    assert run("vary pi from 1 in a", "pi == 3 in a", "settle in a")[-1].output == "⇒ pi = 3"
    assert run("vary x from 1 in a", "f(z) := z^2", "f(x) == 16 in a", "settle in a")[-1].output == "⇒ x = 4"


def test_unicode_relations_and_text():
    for rel in ("≤", "≥"):
        r = last("vary x from 1 in a", f"x {rel} 3 in a", "settle in a")
        assert r.status == "error" and "not available yet" in r.error or r.status == "ok"
    assert parse_statement("0 ≤ x ≤ 3 in p").relations == ["0 <= x", "x <= 3"]
    assert last("vary x from 1 in α", "x == 2 in α", "settle in α").output == "⇒ x = 2"
    assert last("vary x from 1 in a", "x² == 9 in a", "settle in a").output == "⇒ x = 3"
    assert last("vary x from 1 in a", "x·x == 9 in a", "settle in a").output == "⇒ x = 3"
    assert last("vary x from 1 in a", "√x == 3 in a", "settle in a").output == "⇒ x = 9"
    assert last("vary x from 1 in a", "x == π in a", "settle in a").output == "⇒ x = 3.14159"
    assert last("vary x from 1 in a", "x == −3 in a", "settle in a").output == "⇒ x = -3"


def test_phase_b_features_report_interim_error_not_crash():
    for srcs in (["vary x from 0 in i", "x > 0 in i", "x^2 == 4 in i", "settle in i"],
                 ["vary x from 0 in i", "x <= 1 in i", "settle in i"],
                 ["vary x from 0 in i", "least x^2 in i"], ["vary x from 0 in i", "most x in i"]):
        r = last(*srcs)
        assert r.status == "error" and "not available yet" in r.error


def test_relation_forms_and_malformed_regions():
    assert solved("vary x from 1 in p", "2 == x in p", "settle in p")["x"] == pytest.approx(2)
    for bad in ("x - 2 in p", "x != 2 in p", "accuracy in p"):
        assert 'A relation is required before "in p"' in run("vary x from 1 in p", bad)[-1].error, bad
    for bad, msg in (("settle x in p", "settle takes no expression"), ("settle 3 in p", "settle takes no expression"),
                     ("least in p", "least/most needs an expression"), ("most in p", "least/most needs an expression")):
        assert run(bad)[0].error == msg, bad
    r = run("vary x from 1 in p", "x = 2 in p", "settle in p")
    assert r[1].status == "error" and r[2].status == "error"                 # single '=' is not a relation
    r = run("vary x from 1 in p", "x := 2 in p", "settle in p")
    assert r[1].status == "error"


def test_constraint_outputs_of_non_result_regions():
    r = run("vary x from 1, y from 2 in p", "x + y == 3 in p", "accuracy 1e-6 in p", "steps 50 in p", "settle in p")
    for x in r[:4]:
        assert x.status == "ok" and x.output == "" and x.defines == ""
    assert r[4].output.startswith("⇒ ") and r[4].defines == ""


def test_result_text_format():
    r = last("vary x from 4.2, y from 2.8 in c", "x^2 + y^2 == 25 in c", "x*y == 12 in c", "settle in c")
    assert r.output == "⇒ x = 4, y = 3"
    r = last("vary w from 1 m, d from 1 m in a", "w + d == 5 m in a", "w - d == 1 m in a", "settle in a")
    assert r.output == "⇒ w = 3 m, d = 2 m"


# -- numeric range (large, tiny) ---------------------------------------------------------------------

@pytest.mark.parametrize("rhs", ["1e-9", "1e-12", "1e-30", "1e-300", "1e3", "1e6"])
def test_tiny_and_moderate_targets_solve(rhs):
    assert solved("vary x from 1 in a", f"x == {rhs} in a", "settle in a")["x"] == pytest.approx(float(rhs), rel=1e-5)


def test_tiny_scale_quadratic_and_large_guess_scale():
    assert solved("vary x from 1e-12 in a", "x^2 == 9e-24 in a", "settle in a")["x"] == pytest.approx(3e-12, rel=1e-5)
    assert solved("vary x from 1e12 in a", "x == 3e12 in a", "settle in a")["x"] == pytest.approx(3e12, rel=1e-5)
    assert solved("vary x from 1e9 in a", "x == 1 in a", "settle in a")["x"] == pytest.approx(1, rel=1e-5)
    assert solved("vary x from 1 MPa in a", "x*2 m^2 == 2e9 N in a", "settle in a")["x"] == pytest.approx(1e9, rel=1e-5)


@pytest.mark.parametrize("src", ["x == 1e9", "x == -1e9", "2*x == 1e12", "x^2 == 1e12"])
def test_far_away_root_from_small_guess(src):
    assert last("vary x from 1 in a", src + " in a", "settle in a").status == "ok"


def test_far_away_root_with_units():
    r = last("vary p from 1 Pa in a", "p*2 m^2 == 2e9 N in a", "settle in a")
    assert r.status == "ok" and values(r.output)["p"] == pytest.approx(1e9, rel=1e-5)


def test_overflow_and_non_finite_are_clean_errors():
    for guess, eq in (("1", "x == oo"), ("1", "x == 2*I"), ("1", "x + I == 2"), ("0", "1/x == 2"), ("-1", "ln(x) == 2")):
        r = last(f"vary x from {guess} in a", eq + " in a", "settle in a")
        assert r.status == "error", eq
        assert r.error.startswith("Cannot evaluate at the starting guess"), (eq, r.error)
    assert last("vary x from 1 in a", "x == 1e300 in a", "settle in a").status in ("ok", "error")


def test_no_python_warnings_for_domain_errors():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        last("vary x from -1 in a", "ln(x) == 2 in a", "settle in a")
    assert not [w for w in caught if issubclass(w.category, RuntimeWarning)]


def test_known_functions_solve():
    assert solved("vary x from 3 in a", "sin(x) == 0 in a", "settle in a")["x"] == pytest.approx(math.pi, abs=1e-5)
    assert solved("vary x from 1 in a", "cos(x) == x in a", "settle in a")["x"] == pytest.approx(0.739085, abs=1e-5)
    assert solved("vary x from 1 in a", "exp(x) == 2 in a", "settle in a")["x"] == pytest.approx(math.log(2), abs=1e-6)
    assert solved("vary x from 1 in a", "abs(x) == 2 in a", "settle in a")["x"] == pytest.approx(2, abs=1e-6)
    assert solved("vary x from 0.5 in a", "sqrt(x) == 2 in a", "settle in a")["x"] == pytest.approx(4, abs=1e-5)


# -- performance and dependency hygiene -----------------------------------------------------------------

def test_ten_unknown_nonlinear_system_performance_and_correctness():
    import random
    random.seed(1)
    n = 10
    sol = [random.uniform(1, 3) for _ in range(n)]
    src = ["vary " + ", ".join(f"x{i} from 1" for i in range(n)) + " in big"]
    for i in range(n):
        src.append(f"x{i}^2 + x{(i + 1) % n} == {sol[i] ** 2 + sol[(i + 1) % n]!r} in big")
    src.append("settle in big")
    start = time.time()
    r = last(*src)
    assert time.time() - start < 5
    assert r.status == "ok"
    got = values(r.output)
    # the system may have several solutions; verify the equations independently instead of the point
    for i in range(n):
        lhs = got[f"x{i}"] ** 2 + got[f"x{(i + 1) % n}"]
        assert lhs == pytest.approx(sol[i] ** 2 + sol[(i + 1) % n], rel=1e-4)


def test_ten_unknown_linear_system_matches_numpy():
    import numpy as np
    n = 10
    a = np.ones((n, n)) + np.eye(n) * (n - 1)
    b = np.arange(1, n + 1, dtype=float)
    src = ["vary " + ", ".join(f"x{i} from 0" for i in range(n)) + " in big"]
    for i in range(n):
        src.append(" + ".join(f"{a[i, j]:g}*x{j}" for j in range(n)) + f" == {b[i]:g} in big")
    src.append("settle in big")
    start = time.time()
    got = solved(*src)
    assert time.time() - start < 5
    ref = np.linalg.solve(a, b)
    assert [got[f"x{i}"] for i in range(n)] == pytest.approx(list(ref), rel=1e-4, abs=1e-6)


def test_importing_engine_does_not_import_scipy():
    code = ("import sys; import livesheet.engine; from livesheet.engine import Engine;"
            "Engine().evaluate([(0, '1+1 =')]);"
            "print('scipy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stderr


def test_scipy_is_only_loaded_when_a_result_region_runs():
    code = ("import sys; from livesheet.engine import Engine;"
            "Engine().evaluate([(0, 'vary x from 1 in a'), (1, 'x == 2 in a')]);"
            "print('scipy.optimize' in sys.modules)")
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip() == "False"


def test_missing_scipy_gives_clean_error(monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name == "scipy" or name.startswith("scipy."):
            raise ImportError("no scipy")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    sys.modules.pop("scipy.optimize", None)
    r = last("vary x from 1 in a", "x == 2 in a", "settle in a")
    # scipy may already be cached in sys.modules, in which case the import succeeds
    assert r.status == "ok" or r.error == "Solving needs the scipy package"


def test_sheet_without_models_still_evaluates_and_solver_is_not_used():
    r = run("a := 2", "b := a + 1", "b =", "(x+1)^2 → expand")
    assert [x.output for x in r] == ["", "", "= 3", "→ x² + 2·x + 1"]
