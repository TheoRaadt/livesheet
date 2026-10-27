"""Spec 001 black-box tests written by the tester from the spec only.

Expected values come from independent Fraction / SymPy / math calculations in
this file, not from the developer's tests. Cases marked xfail(strict=True) are
open defects listed in docs/board/reviews/001-range-variables.md.
"""

import math
import time
from fractions import Fraction

import pytest
import sympy as sp

from livesheet.engine import Engine, parse_statement
from livesheet.engine.evaluator import MAX_RANGE_VALUES


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def col(result, index=0):
    return [row[index] for row in result.rows]


def mag(cell: str) -> float:
    return float(cell.split()[0].replace("−", "-"))


# -- independent verification of the numeric examples of the spec ---------------

def test_spec_numbers_independent_sympy():
    t = [sp.Integer(2 * k) for k in range(6)]
    assert [3 * x for x in t] == [0, 6, 12, 18, 24, 30]             # criterion 1
    assert sp.Rational(3 * 6, 1000) == sp.Rational(18, 1000)        # criterion 2: 0.018 km
    assert [i**2 for i in range(1, 6)] == [1, 4, 9, 16, 25]         # criterion 3
    assert sp.floor(sp.Rational(1) / sp.Rational(1, 10)) + 1 == 11  # criterion 4, exact
    assert sp.Rational(3, 10) == 3 * sp.Rational(1, 10)
    assert [5 + k * -2 for k in range(sp.floor(sp.Rational(1 - 5, -2)) + 1)] == [5, 3, 1]  # 5
    assert sp.floor(sp.Rational(10, 4)) + 1 == 3                    # criterion 6: 0, 4, 8
    assert [i**2 + 1 for i in (1, 2, 3)] == [2, 5, 10]              # criterion 8
    assert (2 * 1, 2 * 2) == (2, 4)                                 # criterion 10 (kg*s)


@pytest.mark.parametrize("start,end,step", [
    (Fraction(0), Fraction(1), Fraction(1, 10)),
    (Fraction(0), Fraction(3, 10), Fraction(1, 10)),
    (Fraction(0), Fraction(7, 10), Fraction(1, 10)),
    (Fraction(1), Fraction(2), Fraction(1, 3)),
    (Fraction(-3), Fraction(3), Fraction(3)),
    (Fraction(5), Fraction(1), Fraction(-2)),
    (Fraction(1, 2), Fraction(9, 2), Fraction(1, 2)),
])
def test_value_sequence_matches_exact_arithmetic(start, end, step):
    def txt(fr):
        return f"({fr.numerator}/{fr.denominator})"

    res = last(f"x := {txt(start)} to {txt(end)} step {txt(step)}", "table x")
    n = math.floor((end - start) / step) + 1
    assert len(res.rows) == n
    for k, cell in enumerate(col(res)):
        assert mag(cell) == pytest.approx(float(start + k * step), rel=1e-5, abs=1e-12)


def test_no_drift_with_many_fractional_steps():
    res = last("x := 0 to 999.9 step 0.1", "table x")
    assert len(res.rows) == 10000
    assert mag(col(res)[-1]) == pytest.approx(999.9, abs=1e-9)
    assert mag(col(res)[3000]) == pytest.approx(300.0, abs=1e-9)


# -- behaviour beyond the developer's tests ------------------------------------------

def test_negative_fractional_descending_step():
    res = last("x := 1 to 0 step -0.25", "table x")
    assert [mag(c) for c in col(res)] == [1, 0.75, 0.5, 0.25, 0]


def test_negative_start_crossing_zero_has_no_negative_zero():
    res = last("x := -1 to 1 step 0.5", "table x, -x")
    assert [mag(c) for c in col(res)] == [-1, -0.5, 0, 0.5, 1]
    assert [mag(c) for c in col(res, 1)] == [1, 0.5, 0, -0.5, -1]
    assert not any(c.split()[0] == "-0" for c in col(res) + col(res, 1))


def test_descending_with_units():
    assert col(last("a := 5 m to 1 m step -2 m", "table a")) == ["5 m", "3 m", "1 m"]


def test_unit_conversion_of_range_values():
    res = last("t := 0 m to 1 km step 250 m", "table t in km, t in m")
    assert col(res) == ["0 km", "0.25 km", "0.5 km", "0.75 km", "1 km"]
    assert col(res, 1)[-1] == "1000 m"


def test_mixed_start_and_step_units_same_dimension():
    res = last("t := 0 m to 2 m step 50 cm", "table t in cm")
    assert [mag(c) for c in col(res)] == [0, 50, 100, 150, 200]


def test_dimension_mismatch_forms():
    assert "Units do not match" in run("a := 1 to 3 s")[0].error
    assert "Units do not match" in run("a := 1 s to 3 s step 1")[0].error
    assert "Units do not match" in run("a := 1 s to 3 s step 1 m")[0].error


def test_end_inside_tolerance_included():
    # 0.3/0.1 = 2.9999999999999996 in floating point: end must still be included
    assert len(last("x := 0 to 0.3 step 0.1", "table x").rows) == 4


def test_end_clearly_before_grid_not_extended():
    assert len(last("x := 0 to 0.29 step 0.1", "table x").rows) == 3


def test_step_larger_than_span_gives_single_value():
    assert last("x := 2 to 3 step 5", "table x").rows == [["2"]]


def test_expressions_for_start_end_step():
    r = run("n := 4", "x := n to 2*n step n/2", "table x")
    assert r[1].status == "ok"
    assert [mag(c) for c in col(r[2])] == [4, 6, 8]


def test_symbolic_constant_limits():
    res = last("a := 0 to pi step pi/4", "table a, sin(a)")
    assert len(res.rows) == 5
    assert [mag(c) for c in col(res)] == pytest.approx([k * math.pi / 4 for k in range(5)], rel=1e-5)
    assert [mag(c) for c in col(res, 1)] == pytest.approx(
        [math.sin(k * math.pi / 4) for k in range(5)], abs=1e-5)


def test_many_columns_and_duplicate_columns():
    res = last("a := 1 to 3", "table a, a, a^2, a^3, -a")
    assert res.columns == ["a", "a", "a^2", "a^3", "-a"]
    assert res.rows[2] == ["3", "3", "9", "27", "-3"]


def test_header_is_trimmed_text_without_unit_part():
    res = last("a := 1 m to 2 m", "table   a  in  cm ,  a*a   ")
    assert res.columns == ["a", "a*a"]
    assert res.rows[1] == ["200 cm", "4 m²"]


def test_several_target_units_on_same_range():
    res = last("a := 1 s to 2 s", "table a in ms, a in s, a in min")
    assert res.rows[0][:2] == ["1000 ms", "1 s"]
    assert mag(res.rows[0][2]) == pytest.approx(1 / 60, rel=1e-5)


def test_constants_and_other_variables_in_columns():
    res = last("total := 2", "t := 1 to 3", "table total*t, total")
    assert res.rows == [["2", "2"], ["4", "2"], ["6", "2"]]


def test_function_of_range_with_units():
    assert col(last("f(x) := 2*x", "t := 1 s to 2 s", "table f(t)")) == ["2 s", "4 s"]


def test_function_with_parameter_named_like_range():
    res = last("a := 1 to 3", "f(a) := a + 10", "table f(a), f(5)")
    assert res.rows == [["11", "15"], ["12", "15"], ["13", "15"]]


# -- name clashes, redefinition, order ---------------------------------------------

def test_total_and_table_names_still_ordinary():
    r = run("total := 2", "total =", "table := 3", "table =", "table1 := 4", "table1 =")
    assert [x.output for x in r] == ["", "= 2", "", "= 3", "", "= 4"]
    assert all(x.status == "ok" for x in r)


def test_table_name_as_scalar_inside_table_column():
    assert col(last("table := 3", "t := 1 to 3", "table t*table")) == ["3", "6", "9"]


def test_names_to_step_as_plain_variables():
    assert run("to := 3", "step := 4", "to + step =")[-1].output == "= 7"


def test_range_named_like_unit_wins():
    assert col(last("s := 1 to 3", "table s")) == ["1", "2", "3"]


def test_range_named_table_is_a_range_variable():
    r = run("table := 1 to 3", "table =")
    assert r[-1].status == "error" and "range variable" in r[-1].error


def test_redefinition_range_to_scalar_and_back():
    r = run("a := 1 to 3", "a := 7", "a =", "table a")
    assert r[2].output == "= 7"
    assert r[3].status == "error" and "range variable" in r[3].error
    r = run("a := 7", "a := 1 to 3", "table a")
    assert len(r[2].rows) == 3


def test_range_used_before_definition_is_error():
    r = run("table a", "a := 1 to 3")
    assert r[0].status == "error" and "a is not defined" in r[0].error
    assert r[1].status == "ok"


def test_circular_and_self_reference():
    assert "not defined" in run("a := 1 to a")[0].error
    assert run("a := 1 to b", "b := a")[0].status == "error"   # b := a itself is a plain symbol
    r = run("a := 1 to 3", "a := a to 5")
    assert r[1].status == "error" and "range variable" in r[1].error


def test_range_used_in_other_definitions_is_error():
    assert "range variable" in run("a := 1 to 3", "b := 1 to a")[1].error
    assert "range variable" in run("a := 1 to 3", "y := 2*a")[1].error
    assert "range variable" in run("a := 1 to 3", "f(x) := x + a")[1].error


def test_range_limit_from_earlier_scalar_only():
    assert len(last("b := 3", "a := 1 to b", "table a").rows) == 3
    assert last("a := 1 to b", "b := 3", "table a").status == "error"


def test_global_range_variants_and_priority():
    r = run("table k", "k ≡ 1 to 3")
    assert r[0].status == "ok" and len(r[0].rows) == 3
    assert len(run("k ::= 1 to 3", "table k")[1].rows) == 3
    r = run("k ≡ 1 to 3", "table k", "k ≡ 5 to 6", "table k")
    assert [mag(c) for c in col(r[1])] == [5, 6] and [mag(c) for c in col(r[3])] == [5, 6]


def test_global_range_limit_from_global_scalar():
    r = run("table k", "n ≡ 3", "k ≡ 1 to n")
    assert r[0].status == "ok" and len(r[0].rows) == 3


def test_local_redefinition_shadows_global_range():
    assert run("k ≡ 1 to 3", "k := 7", "table k")[2].status == "error"


def test_two_tables_independent_results():
    r = run("a := 1 to 2", "table a", "b := 1 to 4", "table b", "table a")
    assert len(r[1].rows) == 2 and len(r[3].rows) == 4 and len(r[4].rows) == 2


# -- limits, huge counts, performance ------------------------------------------------

def test_count_limit_boundaries():
    assert MAX_RANGE_VALUES == 10000
    assert last("i := 1 to 10000", "table i").status == "ok"
    assert len(last("i := 0 to 9999", "table i").rows) == 10000
    for src in ("i := 1 to 10001", "i := 0 to 10000", "i := 0 to 1 step 1e-5",
                "i := 0 to 1e9", "i := 1 to 100000"):
        res = run(src)[0]
        assert res.status == "error" and "too many values" in res.error, src


def test_astronomical_count_fails_fast():
    start = time.time()
    for src in ("i := 0 to 1 step 10**-400", "i := 0 to 10**400"):
        assert run(src)[0].status == "error"
    assert time.time() - start < 2


def test_huge_count_message_is_readable():
    res = run("i := 1 to 1e308")[0]
    assert res.status == "error" and len(res.error) < 100


@pytest.mark.parametrize("src", ["i := 1 to oo", "i := -oo to 1", "i := 1 to inf"])
def test_infinite_limits_clean_message(src):
    res = run(src)[0]
    assert res.status == "error" and "infinity to integer" not in res.error


def test_max_size_table_performance_budget():
    start = time.time()
    res = last("i := 1 to 10000", "table i, i^2")
    elapsed = time.time() - start
    assert len(res.rows) == 10000
    assert elapsed < 15, f"10000-row table took {elapsed:.1f}s"


# -- error cases ------------------------------------------------------------------------

def test_zero_step_forms():
    for src in ("i := 1 to 5 step 0", "i := 1 to 5 step 1-1", "i := 1 s to 5 s step 0 s"):
        res = run(src)[0]
        assert res.status == "error" and "step must not be zero" in res.error, src


def test_zero_step_float_literal():
    assert "step must not be zero" in run("i := 1 to 5 step 0.0")[0].error


def test_wrong_sign_forms():
    for src in ("i := 1 to 5 step -1", "i := 5 to 1", "i := 0 to 1 step -0.25",
                "t := 0 s to 5 s step -1 s"):
        res = run(src)[0]
        assert res.status == "error" and "wrong sign" in res.error, src


def test_complex_limits_rejected():
    res = run("a := 1+2*I to 3")[0]
    assert res.status == "error" and "real" in res.error


def test_undefined_names_in_limits():
    assert "q is not defined" in run("a := 1 to q")[0].error
    assert "q is not defined" in run("a := q to 3")[0].error
    assert "q is not defined" in run("a := 1 to 3 step q")[0].error


def test_error_range_leaves_name_undefined():
    r = run("a := 1 to 5 step 0", "table a")
    assert r[1].status == "error" and "a is not defined" in r[1].error


def test_undefined_in_one_column_fails_whole_table():
    res = last("a := 1 to 3", "table a, a*b")
    assert res.status == "error" and "b is not defined" in res.error
    assert res.rows == [] and res.columns == []


def test_unit_mismatch_in_target_unit():
    assert "Units do not match" in last("t := 1 s to 3 s", "table t in kg").error
    assert "Units do not match" in last("t := 1 to 3", "table t in s").error
    assert "Units do not match" in last("t := 1 s to 3 s", "table t in ms, t in kg").error


def test_trailing_equals_errors():
    assert "Use table to show a range" in run("t := 0 to 5 =")[0].error
    assert "Use table to show a range" in run("t ≡ 0 to 5 step 1 =")[0].error
    assert "table takes no '='" in last("t := 1 to 3", "table t =").error
    assert "table takes no '='" in last("t := 1 to 3", "table t = 5").error


def test_direct_use_of_range_outside_table():
    for expr in ("t =", "t + 1 =", "2*t =", "t^2 → simplify", "sin(t) ="):
        res = last("t := 1 to 3", expr)
        assert res.status == "error" and "t is a range variable" in res.error, expr


def test_table_without_range_variable_or_two_ranges():
    assert "range variable" in last("table 2 + 3").error
    assert "range variable" in last("x := 5", "table x").error
    assert "one range variable" in last("a := 1 to 3", "b := 1 to 2", "table a, b").error
    assert "one range variable" in last("a := 1 to 3", "b := 1 to 2", "table a*b").error


def test_empty_table_forms():
    for src in ("table", "table ,", "table , ,"):
        res = run(src)[0]
        assert res.status == "error" and "at least one column" in res.error, src


def test_table_bad_syntax_is_clean_error():
    for src in ("table (a", "table a)", "table a in in", "table a in", "table a * "):
        res = last("a := 1 to 3", src)
        assert res.status == "error" and res.rows == [], src


def test_table_unbalanced_brackets_message():
    res = last("a := 1 to 3", "table ),a(")
    assert res.status == "error" and "index" not in res.error


def test_division_by_zero_cell_shows_undefined():
    # decided (D4): consistent with `1/0 =`, the cell shows 'undefined'
    res = last("i := 1 to 3", "table i, 1/(i-2)")
    assert res.status == "ok" and res.rows[1][1] == "undefined"


def test_division_by_zero_cell_consistent_with_plain_evaluation():
    plain = run("x := 2", "1/(x-2) =")[1].output.removeprefix("= ")
    res = last("i := 1 to 3", "table 1/(i-2)")
    assert res.status == "ok" and res.rows[1] == [plain]


# -- syntax / parser level -----------------------------------------------------------------

def test_parse_range_statement_fields():
    st = parse_statement("t ≡ 0 s to 10 s step 2 s")
    assert (st.kind, st.name, st.expr, st.range_end, st.range_step, st.is_global) == (
        "range", "t", "0 s", "10 s", "2 s", True)
    st = parse_statement("t := 1 to 5")
    assert (st.kind, st.range_step, st.is_global) == ("range", "", False)


def test_parse_table_commas_and_in():
    st = parse_statement("table t, max(t, 3 s), f(t, 2) in m")
    assert st.kind == "table"
    assert st.columns == [("t", ""), ("max(t, 3 s)", ""), ("f(t, 2)", "m")]


def test_keywords_case_and_spacing():
    assert last("a := 1 TO 3", "table a").status == "error"            # lower case only
    assert len(last("a := 1  to   3  ", "table a").rows) == 3          # extra blanks
    assert len(last("a:=1 to 3", "table a").rows) == 3                 # no blanks around :=
    assert len(last("a := 1 to 3", "  table   a  ,  a^2  ").rows) == 3
    assert last("a := 1to3", "table a").status == "error"              # whitespace required
    assert len(last("a := 1 to 3", "table\ta").rows) == 3              # tab after table


def test_unicode_names_and_operators():
    assert col(last("α := 1 to 3", "table α²")) == ["1", "4", "9"]
    assert col(last("Δt := 1 to 3", "table Δt·2")) == ["2", "4", "6"]
    assert col(last("ä := 1 to 3", "table ä×ä")) == ["1", "4", "9"]
    assert col(last("日本 := 1 to 3", "table 日本")) == ["1", "2", "3"]
    assert col(last("x ≔ 1 to 3", "table x")) == ["1", "2", "3"]
    assert col(last("x := 1 to 3", "table x")) == ["1", "2", "3"]   # NBSP
    assert col(last("x := 0 to 2", "table √(x+1)"))[0] == "1"
    assert col(last("v := 3 m/s", "t := 0 s to 2 s", "table v·t")) == ["0 m", "3 m", "6 m"]
    assert last("а := 1 to 3", "table a").status == "error"                  # Cyrillic а is not Latin a


def test_unicode_minus_in_range():
    assert col(last("x := 1 to −1 step −1", "table x")) == ["1", "0", "-1"]


def test_table_with_boolean_and_complex_cells():
    assert col(last("a := 1 to 3", "table a < 2")) == ["true", "false", "false"]
    assert col(last("a := 1 to 3", "table a*I"))[0] == "1i"


def test_zero_cells_keep_units():
    res = last("t := 0 s to 2 s", "v := 3 m/s", "table t, v*t")
    assert res.rows[0] == ["0 s", "0 m"]


def test_multiline_table_text():
    res = last("a := 1 to 3", "table a,\n a*2")
    assert res.status == "ok" and len(res.rows) == 3


def test_engine_reusable_without_leakage():
    eng = Engine()
    src = [(0, "a := 1 to 3"), (1, "table a, a^2")]
    assert eng.evaluate(src)[1].rows == eng.evaluate(src)[1].rows
    assert eng.evaluate([(0, "a := 1 to 2"), (1, "table a")])[1].rows == [["1"], ["2"]]
    assert eng.evaluate([(1, "table a")])[1].status == "error"


def test_significant_digits_setting_applies_to_cells():
    res = Engine(significant=3).evaluate([(0, "a := 0 to 1 step 1/3"), (1, "table a")])[1]
    assert col(res) == ["0", "0.333", "0.667", "1"]


def test_output_summary_singular_plural():
    assert last("a := 2 to 2", "table a").output == "table 1 row"
    assert last("a := 2 to 3", "table a").output == "table 2 rows"
