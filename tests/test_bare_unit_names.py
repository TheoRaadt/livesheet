"""A bare unit-named identifier with nothing marking it as a unit is reported as not defined."""
from livesheet.engine.evaluator import Engine


def run(*sources):
    res = Engine().evaluate(list(enumerate(sources)))
    return [res[i] for i in range(len(sources))]


def test_formula_with_undefined_unit_named_variables_errors():
    r = run("sigma := F/A", "sigma =")
    assert r[0].status == "error" and r[0].error == "F is not defined"
    assert r[1].status == "error" and "not defined" in r[1].error


def test_bare_unit_name_evaluation_errors():
    assert run("F =")[0].error == "F is not defined"


def test_number_unit_statements_still_work():
    assert run("5 N =")[0].output == "= 5 N"
    assert run("x := 10 m", "x =")[1].output == "= 10 m"
    assert run("v := 3 m/s", "v =")[1].output == "= 3 m/s"
    assert run("a := 2 * N", "a =")[1].output == "= 2 N"


def test_user_name_with_unit_name_still_works():
    r = run("w := 4", "w*m =")
    assert r[1].output == "= 4 m"


def test_defined_variable_shadows_unit():
    r = run("F := 100 N", "A := 4 m^2", "sigma := F/A", "sigma =")
    assert r[3].status == "ok" and r[3].output == "= 25 Pa"
    assert run("A := 5", "A =")[1].output == "= 5"


def test_unit_conversion_field_unaffected():
    assert run("x := 5000 N", "x = kN")[1].output == "= 5 kN"
