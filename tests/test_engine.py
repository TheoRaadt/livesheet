import pytest

from livesheet.engine import Engine, StatementError, parse_statement


def run(*lines):
    results = Engine().evaluate(list(enumerate(lines)))
    return [results[i] for i in range(len(lines))]


def out(*lines):
    return run(*lines)[-1].output


def err(*lines):
    res = run(*lines)[-1]
    assert res.status == "error", res
    return res.error


# --- statement syntax ---------------------------------------------------------

@pytest.mark.parametrize("src, kind", [
    ("", "empty"),
    ("x := 5", "define"),
    ("x ≔ 5", "define"),
    ("f(x, y) := x + y", "define"),
    ("g ≡ 9.81", "global"),
    ("g ::= 9.81", "global"),
    ("x =", "evaluate"),
    ("v = km/hr", "evaluate"),
    ("x + 1 →", "symbolic"),
    ("x + 1 -> expand", "symbolic"),
    ("x^2 == 4 → solve, x", "symbolic"),
    ("x + 1", "expression"),
])
def test_statement_kinds(src, kind):
    assert parse_statement(src).kind == kind


def test_define_with_show():
    st = parse_statement("a := 2 m = mm")
    assert (st.kind, st.name, st.expr, st.show, st.unit) == ("define", "a", "2 m", True, "mm")


def test_function_lhs():
    st = parse_statement("f(a, b) := a*b")
    assert st.name == "f" and st.params == ["a", "b"]


@pytest.mark.parametrize("src", ["2x := 3", "f() := 1", "f(1) := 2", ":= 4"])
def test_bad_definitions(src):
    with pytest.raises(StatementError):
        parse_statement(src)


# --- numeric evaluation ---------------------------------------------------------

def test_basic_arithmetic():
    assert out("1 + 2 * 3 =") == "= 7"
    assert out("2^10 =") == "= 1024"
    assert out("1/3 =") == "= 0.333333"


def test_definitions_flow_top_down():
    assert out("x := 4", "y := x^2", "y =") == "= 16"


def test_use_before_definition_is_error():
    first = run("y =", "y := 3")[0]
    assert first.status == "error" and "not defined" in first.error


def test_redefinition_uses_latest_value():
    assert out("x := 1", "x := x + 1", "x =") == "= 2"


def test_globals_visible_everywhere():
    assert out("y = ", "y ≡ 7") == ""  # global region itself shows nothing
    assert run("y =", "y ≡ 7")[0].output == "= 7"


def test_functions():
    assert out("f(x) := x^2 + 1", "f(3) =") == "= 10"
    assert out("a := 2", "f(x) := a x", "f(5) =") == "= 10"


def test_function_needs_arguments():
    assert "arguments" in err("f(x) := x", "f =")


def test_constants_and_functions():
    assert out("pi =") == "= 3.14159"
    assert out("ln(e) =") == "= 1"
    assert out("log(1000) =") == "= 3"
    assert out("sqrt(16) =") == "= 4"
    assert out("sin(30 deg) =") == "= 0.5"


def test_complex_numbers():
    assert out("sqrt(-4) =") == "= 2i"
    assert out("(1 + 2i)(1 - 2i) =") == "= 5"


def test_unicode_input():
    assert out("x := 3", "x² =") == "= 9"
    assert out("2·3 =") == "= 6"
    assert out("π =") == "= 3.14159"


def test_number_formatting():
    assert out("1e-7 =") == "= 1×10⁻⁷"
    assert out("2^100 =") == "= 1.26765×10³⁰"
    assert out("123456 =") == "= 123456"


def test_significant_digits_setting():
    eng = Engine(significant=3)
    assert eng.evaluate([(0, "pi =")])[0].output == "= 3.14"


# --- units ------------------------------------------------------------------------

def test_units_simplify_to_si():
    assert out("v := 100 m / (20 s)", "v =") == "= 5 m/s"
    assert out("10 N * 2 m =") == "= 20 J"
    assert out("5 kg * g =") == "= 49.0333 N"


def test_unit_conversion():
    assert out("v := 36 km/hr", "v = m/s") == "= 10 m/s"
    assert out("p := 2 bar", "p = kPa") == "= 200 kPa"
    assert out("E := 3 kW * 2 hr = kWh") == "= 6 kWh"


def test_unit_mismatch():
    assert "match" in err("1 m + 1 s =")
    assert "match" in err("x := 2 m", "x = kg")


def test_function_argument_must_be_dimensionless():
    assert "dimensionless" in err("sin(3 m) =")
    assert out("abs(-3 m) =") == "= 3 m"


def test_user_definition_overrides_unit():
    assert out("s := 4", "s^2 =") == "= 16"


def test_inverse_units():
    assert out("1/(4 s) =") == "= 0.25 s⁻¹"


# --- symbolic ------------------------------------------------------------------------

def test_symbolic_simplify_and_keywords():
    assert out("(a + b)^2 → expand") == "→ a² + 2·a·b + b²"
    assert out("a^2 - 1 → factor") == "→ (a - 1)·(a + 1)"
    assert out("sin(x)^2 + cos(x)^2 →") == "→ 1"


def test_solve():
    assert out("x^2 == 4 → solve, x") == "→ {-2, 2}"
    assert out("2 y - 6 → solve, y") == "→ 3"


def test_solve_ignores_numeric_definition_of_variable():
    assert out("x := 10", "x^2 - 9 → solve, x") == "→ {-3, 3}"


def test_symbolic_uses_definitions():
    assert out("a := 3", "a b →") == "→ 3·b"


def test_calculus():
    assert out("diff(x^3, x) →") == "→ 3·x²"
    assert out("x^3 → diff, x") == "→ 3·x²"
    assert out("integrate(2 x, (x, 0, 3)) →") == "→ 9"


def test_float_and_substitute():
    assert out("pi → float, 4") == "→ 3.142"
    assert out("x^2 + 1 → substitute, x = 3") == "→ 10"


def test_unknown_keyword():
    assert "Unknown keyword" in err("x → frobnicate")


def test_syntax_error():
    assert err("3 + * 4 =") == "Syntax error"
