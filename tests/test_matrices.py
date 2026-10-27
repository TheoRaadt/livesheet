"""Spec 002a: vectors and matrices (engine level)."""

import re
import time

import pytest
import sympy as sp

from livesheet.engine import Engine
from livesheet.engine.evaluator import MAX_SHOWN
from livesheet.engine.units import dims_to_text, measure

A = "A := [1, 2; 3, 4]"


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def out(*sources) -> str:
    res = run(*sources)[-1]
    assert res.status == "ok", res.error
    return res.output


def err(*sources) -> str:
    res = run(*sources)[-1]
    assert res.status == "error", res.output
    return res.error


def nums(text: str) -> list[float]:
    """All numbers inside a result text (for tolerance comparisons)."""
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


# -- literals and formatting -------------------------------------------------

def test_literal_define_and_show():
    assert out("A := [1, 2; 3, 4] =") == "= [1, 2; 3, 4]"
    res = run(A)[0]
    assert res.status == "ok" and res.output == "" and res.defines == "A"


def test_row_and_column_literals():
    assert out("[1, 2, 3] =") == "= [1, 2, 3]"
    assert out("[1; 2; 3] =") == "= [1; 2; 3]"


def test_fractions_numeric_and_symbolic():
    assert out("[0.5, 1/3] =") == "= [0.5, 0.333333]"
    # deviation: a float literal stays a float in the symbolic view
    assert out("[1/2, 1/3] →") == "→ [1/2, 1/3]"
    assert out("[0.5, 1/3] →") == "→ [0.5, 1/3]"


def test_literal_errors():
    assert err("[1, 2; 3] =") == "Rows have different lengths (2 and 1)"
    assert err("[] =") == "Empty matrix"
    assert err("[1, , 3] =") == "Empty matrix element"
    assert err("[1, 2;] =") == "Empty matrix element"
    assert err("[[1, 2], 3] =") == "Nested matrices are not supported"


def test_nested_matrix_value_is_error():
    assert err(A, "[A, 1] =") == "Nested matrices are not supported"


def test_large_matrix_placeholder():
    assert out("eye(12) =") == "= [12x12 matrix]"
    assert out("nrows(eye(12)) =") == "= 12"
    assert out("eye(12) →") == "→ [12x12 matrix]"
    assert out("eye(10) =").startswith("= [1, 0")
    assert MAX_SHOWN == 10


# -- indexing ------------------------------------------------------------------

def test_indexing():
    assert out(A, "A[2, 1] =") == "= 3"
    assert out(A, "A[1, :] =") == "= [1, 2]"
    assert out(A, "A[:, 2] =") == "= [2; 4]"
    assert out("v := [5; 6; 7]", "v[3] =") == "= 7"
    assert out("[5, 6, 7][2] =") == "= 6"
    assert out("[5][1] =") == "= 5"
    assert out("[5] =") == "= [5]"
    assert out("w := [5, 6, 7]", "w[1] =") == "= 5"


def test_index_expression_and_nesting():
    assert out(A, "i := 2", "A[i, i - 1] + A[1, 1] =") == "= 4"
    assert out(A, "A[1, :][2] =") == "= 2"


def test_index_errors():
    assert err(A, "A[0, 1] =") == "Index 0 out of range 1..2"
    assert err(A, "A[1, 3] =") == "Index 3 out of range 1..2"
    assert err(A, "A[3, 1] =") == "Index 3 out of range 1..2"
    assert err(A, "A[1] =") == "A matrix needs two indices"
    assert err(A, "A[1.5, 1] =") == "Index must be an integer"
    assert err(A, "A[1, 1, 1] =") == "Too many indices"
    assert err("x := 3", "x[1] =") == "Only matrices can be indexed"


def test_element_assignment_is_rejected():
    assert "Cannot define" in err(A, "A[1, 1] := 5")


# -- arithmetic ------------------------------------------------------------------

def test_sum_difference_scalar():
    assert out(A, "A + A =") == "= [2, 4; 6, 8]"
    assert out(A, "A - A =") == "= [0, 0; 0, 0]"
    assert out(A, "2*A =") == "= [2, 4; 6, 8]"
    assert out(A, "A*2 =") == "= [2, 4; 6, 8]"
    assert out(A, "A/2 =") == "= [0.5, 1; 1.5, 2]"
    assert out(A, "-A =") == "= [-1, -2; -3, -4]"


def test_products_and_powers():
    assert out(A, "A*A =") == "= [7, 10; 15, 22]"
    assert out(A, "A^2 =") == "= [7, 10; 15, 22]"
    assert out(A, "A^0 =") == "= [1, 0; 0, 1]"
    assert out(A, "A^-1 =") == "= [-2, 1; 1.5, -0.5]"
    assert out(A, "A^-2 =") == out(A, "inv(A)*inv(A) =")


def test_row_times_column_is_scalar():
    assert out("[1, 2, 3]*[1; 2; 3] =") == "= 14"
    big = run("M := [1; 2; 3]*[1, 2, 3]", "M[3, 3] =", "M =")
    assert big[1].output == "= 9"
    assert big[2].output == "= [1, 2, 3; 2, 4, 6; 3, 6, 9]"


def test_hadamard_dot_cross():
    assert out(A, "hadamard(A, [5, 6; 7, 8]) =") == "= [5, 12; 21, 32]"
    assert out("dot([1, 2, 3], [4, 5, 6]) =") == "= 32"
    assert out("dot([1, 2, 3], [4; 5; 6]) =") == "= 32"
    assert out("cross([1, 0, 0], [0, 1, 0]) =") == "= [0, 0, 1]"


def test_transpose_trace():
    assert out(A, "transpose(A) =") == "= [1, 3; 2, 4]"
    assert out("transpose([1, 2, 3]) =") == "= [1; 2; 3]"
    assert out(A, "trace(A) =") == "= 5"


def test_constructors():
    assert out("eye(3) =") == "= [1, 0, 0; 0, 1, 0; 0, 0, 1]"
    assert out("zeros(2, 3) =") == "= [0, 0, 0; 0, 0, 0]"
    assert out("ones(1, 2) =") == "= [1, 1]"
    assert out("diag([1, 2, 3]) =") == "= [1, 0, 0; 0, 2, 0; 0, 0, 3]"
    assert out("ncols(zeros(2, 3)) =") == "= 3"
    assert out("len([1, 2, 3]) =") == "= 3"


# -- determinant, inverse, solve -----------------------------------------------------

def test_det():
    assert out(A, "det(A) =") == "= -2"
    assert out("det([1, 2; 2, 4]) =") == "= 0"


def test_inverse():
    assert out(A, "inv(A) =") == out(A, "A^-1 =") == "= [-2, 1; 1.5, -0.5]"
    assert out(A, "inv(A)*A =") == "= [1, 0; 0, 1]"


def test_solve_system():
    assert out(A, "b := [5; 6]", "solve_system(A, b) =") == "= [-4; 4.5]"
    assert out(A, "b := [5; 6]", "A*solve_system(A, b) =") == "= [5; 6]"
    two = run(A, "B := [5, 1; 6, 2]", "solve_system(A, B) =")[-1]
    assert two.status == "ok" and nums(two.output) == [-4, 0, 4.5, 0.5]


def test_float_singular_tolerance():
    assert err("inv([1.0, 2.0; 2.0, 4.0]) =") == "Matrix is singular"
    res = run("inv([1, 2; 3, 4.0000000000001]) =")[0]
    assert res.status == "ok"
    assert nums(res.output)[0] == pytest.approx(-2, rel=1e-6)


def test_3x3():
    assert out("det([2, 0, 1; 1, 3, 2; 1, 1, 2]) =") == "= 6"
    assert out("det([2, 0, 1; 1, 3, 2; 1, 1, 1]) =") == "= 0"
    assert err("inv([2, 0, 1; 1, 3, 2; 1, 1, 1]) =") == "Matrix is singular"


def test_numeric_50x50_float_is_fast():
    import random

    random.seed(1)
    rows = "; ".join(", ".join(f"{random.random():.6f}" for _ in range(50)) for _ in range(50))
    start = time.time()
    res = run(f"M := [{rows}]", "d := det(M)", "N2 := inv(M)", "nrows(N2) =")
    assert all(r.status == "ok" for r in res), [r.error for r in res]
    assert time.time() - start < 2


# -- units -------------------------------------------------------------------------

def test_det_with_units():
    assert out("det([1, 2; 3, 4]*m) =") == "= -2 m²"


def test_stiffness_system():
    setup = ["K := [2, -1; -1, 2]*N/m", "F := [10; 20]*N", "x := solve_system(K, F)"]
    text = out(*setup, "x =")
    assert text.endswith("] m") and nums(text) == pytest.approx([13.3333, 16.6667])
    text = out(*setup, "x = mm")
    assert text.endswith("] mm") and nums(text) == pytest.approx([13333.3, 16666.7])
    assert out(*setup, "K*x =") == "= [10; 20] N"


def test_matrix_unit_display():
    assert out("[1 m, 2 km] =") == "= [1, 2000] m"
    assert out("[1 m, 2 s] =") == "= [1 m, 2 s]"
    assert "Units do not match" in err("[1, 2]*m + [1, 2]*s =")
    assert out("[1, 2]*m = cm") == "= [100, 200] cm"
    assert err("[1, 2]*m = s").startswith("Units do not match: result is")


def test_dot_and_inverse_units():
    assert out("dot([1, 2]*m, [3, 4]*N) =") == "= 11 J"
    inv_dims = dims_to_text(measure(sp.Integer(1) / sp.physics.units.meter).dims)
    assert out("inv([2, 0; 0, 4]*m) =") == f"= [0.5, 0; 0, 0.25] {inv_dims}"


# -- symbolic ----------------------------------------------------------------------

M = "M := [a, b; c, d]"


def _plain(text: str) -> str:
    return text.replace("^", "**").replace("·", "*").replace("²", "**2").replace("³", "**3")


def parse_matrix(text: str) -> sp.Matrix:
    body = text.split("→", 1)[1].strip()
    rows = [[sp.sympify(_plain(c), locals={"d": sp.Symbol("d")})
             for c in r.split(",")] for r in body.strip("[]").split(";")]
    return sp.Matrix(rows)


def test_symbolic_definition_and_numeric_error():
    res = run(M)[0]
    assert res.status == "ok" and res.output == ""
    assert err(M, "M =") == "a, b, c, d are not defined"


def test_symbolic_det_inv_transpose():
    a, b, c, d = sp.symbols("a b c d")
    det_text = _plain(out(M, "det(M) →").split("→", 1)[1])
    assert sp.simplify(sp.sympify(det_text) - (a * d - b * c)) == 0
    # the entry text may print greek-free names; parse entry by entry
    want = sp.Matrix([[d, -b], [-c, a]]) / (a * d - b * c)
    got = parse_matrix(out(M, "inv(M) →"))
    assert all(sp.simplify(x - y) == 0 for x, y in zip(got, want))
    assert parse_matrix(out(M, "transpose(M) →")) == sp.Matrix([[a, c], [b, d]])


def test_symbolic_with_undefined_and_defined_name():
    x = sp.Symbol("x")
    text = out("det([1, x; 2, 3]) →").split("→", 1)[1].replace("·", "*")
    assert sp.simplify(sp.sympify(text) - (3 - 2 * x)) == 0
    assert out("x := 2", "det([1, x; 2, 3]) =") == "= -1"


def test_symbolic_expand_and_scalar_multiple():
    a, b, c = sp.symbols("a b c")
    got = parse_matrix(out(M, "M*M → expand"))
    assert sp.expand(got[0, 0] - (a**2 + b * c)) == 0
    assert out("[x, x]*2 →") in ("→ [2·x, 2·x]", "→ [2x, 2x]")


def test_keyword_errors_on_matrix():
    assert err(M, "M → solve, a") == "'solve' does not apply to matrices"
    assert err(M, "M → diff, a") == "'diff' does not apply to matrices"


def test_float_and_substitute_keywords_entrywise():
    assert out("[1/3, 2/3] → float, 3") == "→ [0.333, 0.667]"
    assert out(M, "M → substitute, a = 1, b = 2, c = 3, d = 4") == "→ [1, 2; 3, 4]"


# -- errors ----------------------------------------------------------------------

def test_shape_errors():
    assert err(A, "A + [1, 2, 3; 4, 5, 6] =") == "Matrix sizes do not match: 2x2 and 2x3"
    assert err(A, "A - [1, 2, 3; 4, 5, 6] =") == "Matrix sizes do not match: 2x2 and 2x3"
    assert err(A, "A*[1, 2, 3] =") == "Cannot multiply 2x2 by 1x3"


@pytest.mark.parametrize("call", ["det", "inv", "trace"])
def test_not_square(call):
    assert err(f"{call}([1, 2, 3; 4, 5, 6]) =") == "Matrix must be square (got 2x3)"


def test_not_square_power():
    assert err("[1, 2, 3; 4, 5, 6]^2 =") == "Matrix must be square (got 2x3)"


def test_singular_errors():
    assert err("inv([1, 2; 2, 4]) =") == "Matrix is singular"
    assert err("solve_system([1, 2; 2, 4], [1; 2]) =") == "Matrix is singular"
    assert err("[1, 2; 2, 4]^-1 =") == "Matrix is singular"


def test_rhs_rows():
    assert err(A, "solve_system(A, [1; 2; 3]) =") == "Right-hand side has 3 rows, matrix has 2"


def test_scalar_mixing_errors():
    assert err(A, "A + 1 =") == "Cannot add a scalar to a matrix"
    assert err(A, "1 + A =") == "Cannot add a scalar to a matrix"
    assert err(A, "A - 1 =") == "Cannot add a scalar to a matrix"
    assert err(A, "1/A =") == "Cannot divide by a matrix; use inv(...)"
    assert err(A, "A/A =") == "Cannot divide by a matrix; use inv(...)"
    assert err(A, "sin(A) =") == "sin() does not accept a matrix"
    assert err(A, "A^0.5 =") == "Matrix power must be an integer"
    assert err(A, "A == A =") == "Cannot compare matrices with =="


def test_vector_function_errors():
    assert err("cross([1, 2], [3, 4]) =") == "cross() needs vectors of length 3"
    assert err("dot([1, 2], [1, 2, 3]) =") == "dot() needs vectors of equal length"
    assert err("det(5) =") == "det() needs a matrix"


@pytest.mark.parametrize("src", ["eye(0)", "zeros(-1, 2)", "ones(2, 0)", "eye(1.5)"])
def test_size_errors(src):
    assert err(src + " =") == "Size must be a positive integer"


def test_size_too_large():
    assert err("eye(201) =") == "Size too large (max 200)"
    assert err("zeros(2, 300) =") == "Size too large (max 200)"
    assert out("nrows(eye(200)) =") == "= 200"


# -- regression ----------------------------------------------------------------------

def test_order_top_to_bottom():
    res = run("v[1] =", "v := [1; 2]")
    assert res[0].status == "error" and res[0].error == "Only matrices can be indexed"


def test_shadowing_functions_and_names():
    assert out("eye := 3", "eye =") == "= 3"
    assert out("T := 2 s", "T =") == "= 2 s"


def test_other_statements_unaffected():
    assert out("x := 5 m =") == "= 5 m"
    assert out("(x+1)^2 →") == "→ (x + 1)²"
    assert out("max(2, 3) =") == "= 3"
    assert out("sqrt(16) =") == "= 4"


def test_index_inside_table_columns():
    res = run("v := [10; 20; 30]", "i := 1 to 3", "table i, v[i]")[-1]
    assert res.status == "ok" and res.rows == [["1", "10"], ["2", "20"], ["3", "30"]]


def test_function_with_matrix_parameter_is_unsupported_but_clean():
    # deviation from the spec edge case: det(M) is evaluated at definition time, M is a scalar symbol there
    res = run("f(M) := det(M)")[0]
    assert res.status == "error" and res.error == "det() needs a matrix"
    assert out("g(x) := [x, 2*x]", "g(2) =") == "= [2, 4]"
