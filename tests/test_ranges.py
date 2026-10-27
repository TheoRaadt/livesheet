"""Spec 001: range statements and result tables (engine level)."""

import pytest

from livesheet.engine import Engine, parse_statement
from livesheet.engine.evaluator import MAX_RANGE_VALUES
from livesheet.engine.formatting import format_table


def run(*sources):
    """Evaluate regions in order; return results as a list."""
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def num(cell: str) -> float:
    return float(cell.split()[0])


def values(result) -> list[float]:
    return [num(row[0]) for row in result.rows]


def test_basic_unit_table():
    rng, tab = run("v := 3 m/s", "t := 0 s to 10 s step 2 s", "table t, v*t in m")[1:]
    assert rng.status == "ok" and rng.defines == "t" and rng.output == ""
    assert tab.status == "ok"
    assert tab.columns == ["t", "v*t"]
    assert tab.rows == [["0 s", "0 m"], ["2 s", "6 m"], ["4 s", "12 m"],
                        ["6 s", "18 m"], ["8 s", "24 m"], ["10 s", "30 m"]]
    assert tab.output == "table 6 rows"


def test_target_unit_conversion():
    tab = last("v := 3 m/s", "t := 0 s to 10 s step 2 s", "table v*t in km")
    assert len(tab.rows) == 6
    assert tab.rows[3][0] == "0.018 km"
    assert num(tab.rows[3][0]) == pytest.approx(0.018, abs=1e-9)
    assert tab.columns == ["v*t"]


def test_dimensionless_default_step():
    tab = last("i := 1 to 5", "table i, i^2")
    assert tab.rows == [["1", "1"], ["2", "4"], ["3", "9"], ["4", "16"], ["5", "25"]]


def test_default_step_is_one_in_start_unit():
    assert len(last("t := 0 s to 3 s", "table t").rows) == 4
    assert values(last("t := 0 km to 3 km", "table t in km")) == [0, 1, 2, 3]


def test_fractional_step_no_drift():
    tab = last("x := 0 to 1 step 0.1", "table x")
    assert len(tab.rows) == 11
    assert num(tab.rows[10][0]) == pytest.approx(1, abs=1e-12)
    assert num(tab.rows[3][0]) == pytest.approx(0.3, abs=1e-12)


def test_descending_range():
    assert values(last("n := 5 to 1 step -2", "table n")) == [5, 3, 1]


def test_end_not_on_grid():
    assert values(last("a := 0 to 10 step 4", "table a")) == [0, 4, 8]


def test_single_value():
    assert last("b := 2 to 2", "table b").rows == [["2"]]


def test_user_function_in_column():
    tab = last("f(x) := x^2 + 1", "i := 1 to 3", "table i, f(i)")
    assert tab.rows == [["1", "2"], ["2", "5"], ["3", "10"]]


def test_global_range_after_table():
    tab = run("table k", "k ≡ 1 to 3")[0]
    assert tab.status == "ok" and values(tab) == [1, 2, 3]
    assert run("table k", "k ::= 1 to 3")[0].status == "ok"


def test_two_columns_different_units():
    tab = last("t := 1 s to 2 s", "m := 2 kg", "table t, m*t")
    unit = last("m := 2 kg", "m*1 s =").output.split(" ", 2)[2]
    assert tab.rows == [["1 s", "2 " + unit], ["2 s", "4 " + unit]]


@pytest.mark.parametrize("sources, message", [
    (["t := 0 s to 10 m step 2 s"], "Units do not match"),
    (["t := 0 s to 10 s step 2 m"], "Units do not match"),
    (["i := 1 to 5 step 0"], "step must not be zero"),
    (["i := 1 to 5 step -1"], "wrong sign"),
    (["i := 5 to 1"], "wrong sign"),
    (["i := 1 to 100000"], "too many values"),
    (["table k, k^2"], "k is not defined"),
    (["table 2 + 3"], "range variable"),
    (["i := 1 to 3", "j := 1 to 3", "table i, j"], "one range variable"),
    (["t := 1 s to 3 s", "table t in kg"], "Units do not match"),
    (["t := 0 to 2", "t ="], "t is a range variable"),
    (["t := 0 to 2", "t + 1 ="], "t is a range variable"),
    (["t := 0 to 5 ="], "Use table to show a range"),
    (["t := 0 to 2", "table t, 2*t ="], "table takes no '='"),
    (["table"], "table needs at least one column"),
    (["table ,"], "table needs at least one column"),
    (["t := 0 to 2", "y := 2*t"], "t is a range variable"),
])
def test_errors(sources, message):
    res = last(*sources)
    assert res.status == "error"
    assert message in res.error
    assert res.rows == []


def test_value_limit_boundary():
    assert last(f"i := 1 to {MAX_RANGE_VALUES}").status == "ok"
    tab = last(f"i := 1 to {MAX_RANGE_VALUES}", "table i")
    assert len(tab.rows) == MAX_RANGE_VALUES
    assert last(f"i := 1 to {MAX_RANGE_VALUES + 1}").status == "error"


def test_range_definition_prints_nothing():
    res = run("x := 5 m", "i := 1 to 3")
    assert [r.output for r in res] == ["", ""]


def test_regression_names_to_step_table_in_ordinary_use():
    res = run("total := 2", "table := 3", "table =", "x := 5 m =", "total =")
    assert [r.status for r in res] == ["ok"] * 5
    assert res[2].output == "= 3" and res[3].output == "= 5 m" and res[4].output == "= 2"


def test_redefinition_replaces_range():
    res = run("t := 0 to 2", "table t", "t := 10 to 11", "table t")
    assert len(res[1].rows) == 3 and len(res[3].rows) == 2
    assert values(res[3]) == [10, 11]


def test_cell_error_fails_whole_table():
    # an unknown unit in a column fails the whole table, no partial rows
    res = last("i := 1 to 3", "table i, i in kg")
    assert res.status == "error" and res.rows == []


def test_division_by_zero_cell_follows_existing_evaluation():
    # `1/0 =` currently prints "undefined" (not an error); a table cell behaves the same
    single = last("x := 2", "1/(x-2) =").output
    tab = last("i := 1 to 3", "table i, 1/(i-2)")
    assert tab.rows[1][1] == single.removeprefix("= ")


def test_function_parameter_shadows_range():
    res = run("t := 0 to 2", "f(t) := t^2", "table t, f(3)")
    assert res[1].status == "ok" and res[2].rows[0] == ["0", "9"]


def test_unit_name_collision_user_definition_wins():
    assert values(last("s := 1 to 3", "table s")) == [1, 2, 3]


def test_column_commas_in_parentheses_do_not_split():
    st = parse_statement("table t, max(t, 3 s) in s")
    assert st.kind == "table"
    assert st.columns == [("t", ""), ("max(t, 3 s)", "s")]


def test_parse_range_statement():
    st = parse_statement("t := 0 s to 10 s step 2 s")
    assert (st.kind, st.name, st.expr, st.range_end, st.range_step) == ("range", "t", "0 s", "10 s", "2 s")
    assert parse_statement("k ≡ 1 to 3").is_global
    assert parse_statement("x := 5 m").kind == "define"
    assert parse_statement("table =").kind == "evaluate"


def test_format_table_text():
    text = format_table(["t", "v*t"], [["0 s", "0 m"], ["10 s", "30 m"]])
    assert len(text.splitlines()) == 4
    lines = text.splitlines()
    assert all(len(line) == len(lines[0]) for line in lines)
    assert lines[2].endswith("0 m") and lines[3].endswith("30 m")


def test_gui_shows_table_as_monospaced_text(tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QApplication

        from livesheet.gui.main_window import MainWindow
    except ImportError as exc:  # e.g. missing system GL libraries
        pytest.skip(f"Qt not usable here: {exc}")
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        sheet = win.sheet
        sheet.add_region("math", QPointF(40, 40), "t := 0 s to 4 s step 2 s")
        tab = sheet.add_region("math", QPointF(40, 90), "table t")
        sheet.recalculate()
        app.processEvents()
        shown = tab.result_item.toPlainText()
        assert "0 s" in shown and "2 s" in shown and "4 s" in shown
        assert tab.result.rows == [["0 s"], ["2 s"], ["4 s"]]
    finally:
        win.sheet.set_modified(False)
        win.close()
