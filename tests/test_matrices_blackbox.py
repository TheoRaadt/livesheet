"""Spec 002a black-box tests (tester). Expected values come from the spec text and from
independent NumPy / SymPy calculations in this file. xfail(strict=True) = open defect, see
docs/board/reviews/002a-vectors-matrices.md."""

import re
import time

import numpy as np
import pytest
import sympy as sp

from livesheet.engine import Engine

A = "A := [1, 2; 3, 4]"


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def out(*sources):
    r = run(*sources)[-1]
    assert r.status == "ok", r.error
    return r.output


def err(*sources):
    r = run(*sources)[-1]
    assert r.status == "error", f"expected error, got {r.output!r}"
    return r.error


def nums(text):
    """All numbers in an output text (ignores units)."""
    return [float(x.replace("−", "-")) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text)]


def lit(m):
    return "[" + "; ".join(", ".join(repr(float(v)) for v in row) for row in m) + "]"


# -- independent check of the spec numbers (NumPy) ---------------------------------

def test_spec_numbers_independent_numpy():
    a = np.array([[1, 2], [3, 4]], float)
    assert np.allclose(a @ a, [[7, 10], [15, 22]])
    assert np.allclose(np.linalg.inv(a), [[-2, 1], [1.5, -0.5]])
    assert np.allclose(np.linalg.solve(a, [5, 6]), [-4, 4.5])
    assert round(np.linalg.det(a)) == -2
    assert round(np.linalg.det(np.array([[2, 0, 1], [1, 3, 2], [1, 1, 2]], float))) == 6
    assert round(np.linalg.det(np.array([[2, 0, 1], [1, 3, 2], [1, 1, 1]], float))) == 0
    k = np.array([[2, -1], [-1, 2]], float)
    assert np.allclose(np.linalg.solve(k, [10, 20]), [40 / 3, 50 / 3])      # 13.3333, 16.6667 m
    assert np.allclose(np.linalg.solve(k, [10, 20]) * 1000, [13333.3333, 16666.6667])
    assert np.dot([1, 2], [3, 4]) == 11
    assert np.allclose(np.cross([1, 0, 0], [0, 1, 0]), [0, 0, 1])
    assert np.allclose(np.array([[1, 2], [3, 4]]) * [[5, 6], [7, 8]], [[5, 12], [21, 32]])
    m = sp.Matrix(2, 2, sp.symbols("a b c d"))
    assert sp.simplify(m.det() - (m[0] * m[3] - m[1] * m[2])) == 0
    assert (m * m)[0, 0] == m[0] ** 2 + m[1] * m[2]
    assert sp.Matrix([[1, sp.Symbol("x")], [2, 3]]).det() == 3 - 2 * sp.Symbol("x")


# -- spec acceptance criteria 1-38 as a table -------------------------------------------

CASES = [
    ([A + " ="], "= [1, 2; 3, 4]"),
    (["[1, 2, 3] ="], "= [1, 2, 3]"),
    (["[1; 2; 3] ="], "= [1; 2; 3]"),
    (["[0.5, 1/3] ="], "= [0.5, 0.333333]"),
    (["eye(12) ="], "= [12x12 matrix]"),
    (["nrows(eye(12)) ="], "= 12"),
    ([A, "A[2, 1] ="], "= 3"),
    ([A, "A[1, :] ="], "= [1, 2]"),
    ([A, "A[:, 2] ="], "= [2; 4]"),
    (["v := [5; 6; 7]", "v[3] ="], "= 7"),
    (["[5, 6, 7][2] ="], "= 6"),
    ([A, "A + A ="], "= [2, 4; 6, 8]"),
    ([A, "A - A ="], "= [0, 0; 0, 0]"),
    ([A, "2*A ="], "= [2, 4; 6, 8]"),
    ([A, "A*2 ="], "= [2, 4; 6, 8]"),
    ([A, "A/2 ="], "= [0.5, 1; 1.5, 2]"),
    ([A, "A*A ="], "= [7, 10; 15, 22]"),
    ([A, "A^2 ="], "= [7, 10; 15, 22]"),
    ([A, "A^0 ="], "= [1, 0; 0, 1]"),
    ([A, "A^-1 ="], "= [-2, 1; 1.5, -0.5]"),
    (["[1, 2, 3]*[1; 2; 3] ="], "= 14"),
    (["[1; 2; 3]*[1, 2, 3] ="], "= [1, 2, 3; 2, 4, 6; 3, 6, 9]"),
    ([A, "hadamard(A, [5, 6; 7, 8]) ="], "= [5, 12; 21, 32]"),
    (["dot([1, 2, 3], [4, 5, 6]) ="], "= 32"),
    (["dot([1; 2; 3], [4, 5, 6]) ="], "= 32"),
    (["cross([1, 0, 0], [0, 1, 0]) ="], "= [0, 0, 1]"),
    ([A, "transpose(A) ="], "= [1, 3; 2, 4]"),
    (["transpose([1, 2, 3]) ="], "= [1; 2; 3]"),
    ([A, "trace(A) ="], "= 5"),
    (["zeros(2, 3) ="], "= [0, 0, 0; 0, 0, 0]"),
    (["ones(1, 2) ="], "= [1, 1]"),
    (["eye(3) ="], "= [1, 0, 0; 0, 1, 0; 0, 0, 1]"),
    (["diag([1, 2, 3]) ="], "= [1, 0, 0; 0, 2, 0; 0, 0, 3]"),
    ([A, "det(A) ="], "= -2"),
    (["det([1, 2; 2, 4]) ="], "= 0"),
    ([A, "inv(A) ="], "= [-2, 1; 1.5, -0.5]"),
    ([A, "inv(A)*A ="], "= [1, 0; 0, 1]"),
    ([A, "b := [5; 6]", "solve_system(A, b) ="], "= [-4; 4.5]"),
    ([A, "b := [5; 6]", "A*solve_system(A, b) ="], "= [5; 6]"),
    (["inv([1, 2; 3, 4.0000000000001]) ="], "= [-2, 1; 1.5, -0.5]"),
    (["det([2, 0, 1; 1, 3, 2; 1, 1, 2]) ="], "= 6"),
    (["det([2, 0, 1; 1, 3, 2; 1, 1, 1]) ="], "= 0"),
    (["det([1, 2; 3, 4]*m) ="], "= -2 m²"),
    (["K := [2, -1; -1, 2]*N/m", "F := [10; 20]*N", "x := solve_system(K, F)", "x ="],
     "= [13.3333; 16.6667] m"),
    (["K := [2, -1; -1, 2]*N/m", "F := [10; 20]*N", "x := solve_system(K, F)", "x = mm"],
     "= [13333.3; 16666.7] mm"),
    (["K := [2, -1; -1, 2]*N/m", "F := [10; 20]*N", "x := solve_system(K, F)", "K*x ="],
     "= [10; 20] N"),
    (["[1 m, 2 km] ="], "= [1, 2000] m"),
    (["[1 m, 2 s] ="], "= [1 m, 2 s]"),
    (["dot([1, 2]*m, [3, 4]*N) ="], "= 11 J"),
    (["inv([2, 0; 0, 4]*m) ="], "= [0.5, 0; 0, 0.25] m⁻¹"),
    (["[1, 2]*m = cm"], "= [100, 200] cm"),
    (["x := 2", "det([1, x; 2, 3]) ="], "= -1"),
    (["[5][1] ="], "= 5"),
    (["[5] ="], "= [5]"),
    (["[1+2*I, 3] ="], "= [1 + 2i, 3]"),
    ([A, "A[1, :][2] ="], "= 2"),
    ([A, "n := 2", "A[n, n] ="], "= 4"),
    ([A, "A[1+1, 2-1] ="], "= 3"),
    ([A, "A[ 1 , : ] ="], "= [1, 2]"),
    ([A, "A[:, :] ="], "= [1, 2; 3, 4]"),
    ([A, "A[1, :] * A[:, 1] ="], "= 7"),
    ([A, "-A ="], "= [-1, -2; -3, -4]"),
    ([A, "A^-2 ="], "= [5.5, -2.5; -3.75, 1.75]"),
    ([A, "A^(1+1) ="], "= [7, 10; 15, 22]"),
    ([A, "(A) ="], "= [1, 2; 3, 4]"),
    ([A, "f(x) := A*x", "f(2) ="], "= [2, 4; 6, 8]"),
    (["g(x) := [x, 2*x]", "g(3) ="], "= [3, 6]"),
    ([A, "B := A", "B[1,1] ="], "= 1"),
    ([A, "A[1, 1] m ="], "= 1 m"),
    (["[1 m, 2 m; 3 m, 4 m] = cm"], "= [100, 200; 300, 400] cm"),
    (["[1 m, 2 m; 3 m, 4 m]*[1 m; 1 m] ="], "= [3; 7] m²"),
    (["[1 m, 2 m; 3 m, 4 m]/(2 m) ="], "= [0.5, 1; 1.5, 2]"),
    (["[1 m, 2 m] - [1 cm, 2 cm] ="], "= [0.99, 1.98] m"),
    (["[1 m, 2 s]*[1 s; 1 m] ="], "= 3 m·s"),
    (["[1 kN, 2 N] = N"], "= [1000, 2] N"),
    (["trace([1 m, 2 m; 3 m, 4 m]) ="], "= 5 m"),
    (["diag([1 m, 2 m]) ="], "= [1, 0; 0, 2] m"),
    (["cross([1,2,3]*m, [4,5,6]*N) ="], "= [-3, 6, -3] J"),
    (["[x, y] * [x; y] →"], "→ x² + y²"),
    (["len([1, 2, 3]) =", ], "= 3"),
    (["len([1; 2; 3]) ="], "= 3"),
    (["ncols(eye(3)) ="], "= 3"),
    (["eye := 3", "eye ="], "= 3"),
    (["det := 3", "det ="], "= 3"),
    (["zeros := 3", "zeros + 1 ="], "= 4"),
    (["T := 5", "T ="], "= 5"),
    (["eye(200)[7, 7] ="], "= 1"),
    (["eye(12)[3, 3] ="], "= 1"),
    (["det(eye(12)*2) ="], "= 4096"),
]


@pytest.mark.parametrize("sources,expected", CASES, ids=[c[0][-1] for c in CASES])
def test_expected_output(sources, expected):
    assert out(*sources) == expected


ERRORS = [
    (["[1, 2; 3] ="], "Rows have different lengths (2 and 1)"),
    (["[] ="], "Empty matrix"),
    ([A, "A[0, 1] ="], "Index 0 out of range 1..2"),
    ([A, "A[1, 3] ="], "Index 3 out of range 1..2"),
    ([A, "A[3, :] ="], "Index 3 out of range 1..2"),
    ([A, "A[:, 0] ="], "Index 0 out of range 1..2"),
    ([A, "A[-1, 1] ="], "out of range"),
    ([A, "A[1] ="], "A matrix needs two indices"),
    ([A, "A[1.5, 1] ="], "Index must be an integer"),
    ([A, "A[1, 1, 1] ="], "Too many indices"),
    ([A, "A + [1, 2, 3; 4, 5, 6] ="], "Matrix sizes do not match: 2x2 and 2x3"),
    ([A, "A*[1, 2, 3] ="], "Cannot multiply 2x2 by 1x3"),
    (["det([1, 2, 3; 4, 5, 6]) ="], "Matrix must be square (got 2x3)"),
    (["inv([1, 2, 3; 4, 5, 6]) ="], "Matrix must be square (got 2x3)"),
    (["trace([1, 2, 3; 4, 5, 6]) ="], "Matrix must be square (got 2x3)"),
    (["[1, 2, 3; 4, 5, 6]^2 ="], "Matrix must be square (got 2x3)"),
    (["inv([1, 2; 2, 4]) ="], "Matrix is singular"),
    (["inv([1.0, 2.0; 2.0, 4.0]) ="], "Matrix is singular"),
    (["inv([2, 0, 1; 1, 3, 2; 1, 1, 1]) ="], "Matrix is singular"),
    (["solve_system([1, 2; 2, 4], [1; 2]) ="], "Matrix is singular"),
    ([A, "solve_system(A, [1; 2; 3]) ="], "Right-hand side has 3 rows, matrix has 2"),
    ([A, "A + 1 ="], "Cannot add a scalar to a matrix"),
    ([A, "1/A ="], "Cannot divide by a matrix; use inv(...)"),
    ([A, "A/A ="], "Cannot divide by a matrix; use inv(...)"),
    ([A, "sin(A) ="], "sin() does not accept a matrix"),
    ([A, "A^0.5 ="], "Matrix power must be an integer"),
    ([A, "A == A ="], "Cannot compare matrices with =="),
    (["cross([1, 2], [3, 4]) ="], "cross() needs vectors of length 3"),
    (["dot([1, 2], [1, 2, 3]) ="], "dot() needs vectors of equal length"),
    (["eye(0) ="], "Size must be a positive integer"),
    (["zeros(-1, 2) ="], "Size must be a positive integer"),
    (["eye(201) ="], "Size too large (max 200)"),
    (["zeros(2, 201) ="], "Size too large (max 200)"),
    (["[1, 2]*m + [1, 2]*s ="], "Units do not match"),
    (["[1, 2]*m = s"], "Units do not match: result is"),
    (["[[1, 2], [3, 4]] ="], "Nested matrices are not supported"),
    (["[1, , 3] ="], "Empty matrix element"),
    (["[1, 2;] ="], "Empty matrix element"),
    (["M := [a, b; c, d]", "M ="], "a, b, c, d are not defined"),
    (["M := [a, b; c, d]", "M → solve, a"], "'solve' does not apply to matrices"),
    (["M := [a, b; c, d]", "M → diff, a"], "does not apply to matrices"),
    (["M := [a, b; c, d]", "M → integrate, a"], "does not apply to matrices"),
    ([A, "A[1, 2] := 5"], "Cannot define"),
    ([A, "A[1, 2][1] ="], "Only matrices can be indexed"),
    ([A, "n := 5", "n[1] ="], "Only matrices can be indexed"),
    (["trace([1 m, 2 s; 3 m, 4 s]) ="], "Units do not match"),
    (["det(5) ="], "det() needs a matrix"),
    (["inv(5) ="], "inv() needs a matrix"),
]


@pytest.mark.parametrize("sources,message", ERRORS, ids=[f"{e[0][-1]}" for e in ERRORS])
def test_error_text(sources, message):
    got = err(*sources)
    assert message in got
    assert "\n" not in got and "Traceback" not in got


@pytest.mark.parametrize("src", ["B[1] =", "B[1, 2] =", "B[1, :] ="])
def test_indexing_undefined_name_says_not_defined(src):
    assert "B is not defined" in err(src)


def test_order_of_evaluation_matrix_used_before_definition():
    r = run("det(B) =", "B := [1, 2; 3, 4]")
    assert r[0].status == "error" and "B is not defined" in r[0].error
    assert r[1].status == "ok"


def test_order_of_evaluation_defined_before_use_works():
    r = run("B := [1, 2; 3, 4]", "det(B) =")
    assert r[1].output == "= -2"


def test_definition_of_matrix_prints_nothing_and_defines():
    r = run(A)
    assert r[0].status == "ok" and r[0].output == "" and r[0].defines == "A"
    r = run("M := [a, b; c, d]")
    assert r[0].status == "ok" and r[0].output == ""


def test_matrix_named_A_before_definition_is_the_unit_ampere():
    # `A` is a unit until it is defined: documents the name clash with the spec's example name.
    assert out("A =") == "= 1 A"
    assert out(A, "A =") == "= [1, 2; 3, 4]"


def test_redefinition_matrix_to_scalar_and_back():
    assert out(A, "A := 5", "A =") == "= 5"
    assert "Only matrices" in err(A, "A := 5", "A[1] =")
    assert out("A := 5", A, "A[2,2] =") == "= 4"


def test_matrix_builtin_names_shadowed_but_other_names_intact():
    assert out("eye := 3", "eye + 1 =") == "= 4"
    assert out("det := [1, 2]", "det[2] =") == "= 2"
    assert out("nrows := 7", "eye(2) =") == "= [1, 0; 0, 1]"


# -- unit handling and zero entries ---------------------------------------------------------

def test_mixed_dimension_matrix_stores_indexes_and_multiplies():
    assert out("M := [1 m, 2 s]", "M[2] =") == "= 2 s"
    assert out("M := [1 m, 2 s]", "M*3 =") == "= [3 m, 6 s]"
    assert out("[1 m, 2 s] + [1 m, 2 s] =") == "= [2 m, 4 s]"


def test_mixed_units_conversion_target():
    assert out("[1 kN, 2 N] = kN") == "= [1, 0.002] kN"
    assert "Units do not match" in err("[1 m, 2 s] = m")


def test_unit_matrix_power_and_division():
    assert out("[1 m, 2 m; 3 m, 4 m]^2 =") == "= [7, 10; 15, 22] m²"
    assert out("[1 m, 2 m; 3 m, 4 m]^-1 =") == "= [-2, 1; 1.5, -0.5] m⁻¹"
    assert out("[1 m, 2 m; 3 m, 4 m]/2 =") == "= [0.5, 1; 1.5, 2] m"


def test_zero_entries_next_to_units_keep_unit():
    assert out("[0, 1 m] =") == "= [0, 1] m"
    assert out("[1 m, 0 m] =") == "= [1, 0] m"
    assert out("[0, 1 m] + [0 m, 0 m] =") == "= [0, 1] m"


@pytest.mark.parametrize("src,exp", [("[0 m, 0 m] =", "= [0, 0] m"), ("[0, 0]*m =", "= [0, 0] m"),
                                     ("zeros(2, 2)*m =", "= [0, 0; 0, 0] m")])
def test_all_zero_unit_matrix(src, exp):
    assert out(src) == exp


def test_zero_product_keeps_unit():
    assert out("[0 m, 1 m]*[1 m; 0 m] =") == "= 0 m²"


def test_zero_entry_in_mixed_matrix():
    assert out("[0 m, 1 s] =") == "= [0 m, 1 s]"


# -- spec deviations -------------------------------------------------------------------------

def test_symbolic_output_keeps_float_literal():
    # decided (M2): a float literal stays a float, like scalar `0.5 →`
    assert out("[0.5, 1/3] →") == "→ [0.5, 1/3]"


@pytest.mark.xfail(strict=True, reason="M3 (backlog): f(M) := det(M) fails because M is a plain symbol at definition time")
def test_function_taking_a_matrix():
    assert out("f(M) := det(M)", "f([1, 2; 3, 4]) =") == "= -2"


def test_scalar_power_matrix_message():
    assert "Matrix Power not defined" not in err(A, "2^A =")


# -- symbolic -----------------------------------------------------------------------------------

def sym(text):
    return sp.sympify(text.replace("·", "*").replace("²", "**2").replace("→", "").strip())


M = "M := [a, b; c, d]"


def test_symbolic_determinant_and_inverse_equal_closed_form():
    a, b, c, d = sp.symbols("a b c d")
    assert sp.simplify(sym(out(M, "det(M) →")) - (a * d - b * c)) == 0
    inv = out(M, "inv(M) →")
    got = sp.Matrix(2, 2, [sym(x.strip()) for x in re.split(r"[;]|,(?![^()]*\))", inv[3:-1])])
    want = sp.Matrix([[d, -b], [-c, a]]) / (a * d - b * c)
    assert sp.simplify(got - want) == sp.zeros(2, 2)


def test_symbolic_transpose_trace_power_hadamard():
    assert out(M, "transpose(M) →") == "→ [a, c; b, d]"
    assert out(M, "trace(M) →") == "→ a + d"
    assert out(M, "hadamard(M, M) →") == "→ [a², b²; c², d²]"
    assert out(M, "M[2, 1] →") == "→ c"
    assert out(M, "M[1, :] →") == "→ [a, b]"


def test_symbolic_expand_and_substitute_entrywise():
    assert out(M, "M*M → expand").startswith("→ [a² + b·c, a·b + b·d;")
    assert out(M, "M → substitute, a = 2") == "→ [2, b; c, d]"
    assert out("[x, x]*2 →") == "→ [2·x, 2·x]"
    assert out(M, "M^-1 * M → simplify") == "→ [1, 0; 0, 1]"


def test_symbolic_numeric_equals_with_values_defined_before_matrix():
    assert out("a := 1", "b := 2", "c := 3", "d := 4", M, "M =") == "= [1, 2; 3, 4]"
    assert out("a := 1", "M := [a, 2]", "a := 5", "M =") == "= [1, 2]"   # value captured at definition


def test_symbolic_solve_system():
    got = out(M, "solve_system(M, [1; 2]) →")
    assert got.startswith("→ [") and "a·d - b·c" in got


def test_undefined_names_listed_when_partly_defined():
    assert "x" in err("[x, y] ="), "x, y"
    assert err("a := 1", "[a, y] =").endswith("y is not defined")


# -- formatting ----------------------------------------------------------------------------------

def test_placeholder_threshold_10_vs_11():
    assert out("eye(10) =").startswith("= [1, 0,") and ";" in out("eye(10) =")
    assert out("ones(10, 10) =").count(";") == 9
    for src, shape in (("eye(11)", "11x11"), ("zeros(10, 11)", "10x11"), ("zeros(11, 10)", "11x10"),
                       ("zeros(1, 11)", "1x11"), ("eye(12)", "12x12"), ("eye(200)", "200x200")):
        assert out(src + " =") == f"= [{shape} matrix]", src
    assert out("eye(12) →") == "→ [12x12 matrix]"
    assert out("eye(12) = ") == "= [12x12 matrix]"


def test_slices_of_big_matrix_follow_placeholder_rule():
    assert out("eye(12)[3, :] =") == "= [1x12 matrix]"
    assert out("eye(12)[:, 3] =") == "= [12x1 matrix]"
    assert out("eye(12)[2, 2] =") == "= 1"
    assert out("eye(3)[2, :] =") == "= [0, 1, 0]"


def test_big_matrix_remains_usable_in_computations():
    assert out("inv(eye(12))[1,1] =") == "= 1"
    assert out("(eye(12)*3)[2,2] =") == "= 3"
    assert out("solve_system(eye(12), ones(12, 1)) =") == "= [12x1 matrix]"
    assert out("nrows(eye(12)*2) =") == "= 12"
    assert "out of range 1..12" in err("eye(12)[13, 1] =")


def test_number_formatting_in_cells():
    assert out("[1e10, 1e-10] =") == "= [1×10¹⁰, 1×10⁻¹⁰]"
    assert out("[1000000, 1] =") == "= [1×10⁶, 1]"
    assert out("[1/3, 1/7]*7 =") == "= [2.33333, 1]"
    assert out("[sqrt(2), pi] =") == "= [1.41421, 3.14159]"
    assert out("[1, -2.5; -3, 4] =") == "= [1, -2.5; -3, 4]"
    assert out("[I, -I] =") == "= [1i, -1i]"
    assert out("[1+I, 2-I] =") == "= [1 + 1i, 2 - 1i]"
    assert out("[1, 2; 3, 4]*(1+I) =") == "= [1 + 1i, 2 + 2i; 3 + 3i, 4 + 4i]"
    assert out("inv([1, I; -I, 2]) =") == "= [2, -1i; 1i, 1]"


def test_result_text_round_trips_as_input():
    text = out("[1, 2; 3, 4]/4 =")[2:]
    assert out("X := " + text, "X*4 =") == "= [1, 2; 3, 4]"
    text = out("K := [2, -1; -1, 2]*N/m", "K =")
    assert text == "= [2, -1; -1, 2] N/m" or text.startswith("= [2, -1; -1, 2]")


# -- unicode / syntax -----------------------------------------------------------------------------

def test_unicode_in_matrices():
    assert out("[1, 2]·2 =") == "= [2, 4]"
    assert out("[1, 2]×2 =") == "= [2, 4]"
    assert out("[1, 2]*[3; 4] =") == "= 11"
    assert out("[−1, 2] =") == "= [-1, 2]"
    assert out("[π, 0] =").startswith("= [3.14159")
    assert out("[√4, √9] =") == "= [2, 3]"
    assert out("[2², 3²] =") == "= [4, 9]"
    assert out("α := [1, 2; 3, 4]", "α[2, 2] =") == "= 4"
    assert out("Δ := [1, 2; 3, 4]", "det(Δ) =") == "= -2"
    assert out("日本 := [1, 2]", "日本[2] =") == "= 2"
    assert out("A≔[1, 2; 3, 4]", "det(A) =") == "= -2"


def test_whitespace_and_layout_variants():
    assert out("[ 1 ,2 ;3,  4 ] =") == "= [1, 2; 3, 4]"
    assert out("[1,2;3,4]=") == "= [1, 2; 3, 4]"
    assert out("A:=[1,2;3,4]", "A[2,2]=") == "= 4"


def test_missing_comma_is_implicit_multiplication_documented():
    # spec: commas are mandatory because spaces multiply; `[1 2]` is therefore [2]
    assert out("[1 2] =") == "= [2]"


def test_bracket_after_name_with_space_is_not_an_index_documented():
    # `A [1, 1]` (space) is parsed as A times a 1x2 literal; here it gives a size error.
    assert "Cannot multiply" in err(A, "A [1, 1] =")


def test_nested_and_malformed_brackets():
    for src in ("[1, 2", "1, 2]", "[1, [2]]", "[;]", "[,]", "[1;;2]", "[[]]", "[1, 2]]", "[[1, 2]", "A[", "[1,2][",
                "[1, 2][]"):
        r = run(src + " =")[0]
        assert r.status == "error", (src, r.output)
        assert "\n" not in r.error and "Traceback" not in r.error and "list index" not in r.error, (src, r.error)


def test_colon_handling_does_not_break_statements():
    r = run("x := 5", "x =")
    assert r[1].output == "= 5"
    assert run("x:5")[0].status == "error"
    assert out(A, "A[1, :] =") == "= [1, 2]"
    assert out(A, "A[1,:]=") == "= [1, 2]"


def test_semicolon_and_comma_inside_function_call_in_literal():
    assert out("[max(1, 2), 3; 4, Min(5, 6)] =") == "= [2, 3; 4, 5]"
    assert out("[sum(k, (k, 1, 3)), binomial(4, 2)] =") == "= [6, 6]"
    assert out("x := [1, 2]", "[x[1], x[2]] =") == "= [1, 2]"


# -- tables (spec 001) with matrices -----------------------------------------------------------------

def test_table_with_indexing_and_matrix_cells():
    r = run(A, "t := 1 to 2", "table t, A[t, 1], A[1, t]*10")[-1]
    assert r.status == "ok"
    assert r.rows == [["1", "1", "10"], ["2", "3", "20"]]
    r = run(A, "t := 1 to 2", "table det(t*A), trace(t*A)")[-1]
    assert r.rows == [["-2", "5"], ["-8", "10"]]
    r = run(A, "t := 1 to 2", "table t*A")[-1]
    assert r.rows == [["[1, 2; 3, 4]"], ["[2, 4; 6, 8]"]]


def test_table_with_units_and_matrix_solution():
    r = run("K := [2, -1; -1, 2]*N/m", "F := [10; 20]*N", "s := 1 to 2",
            "table s, s*solve_system(K, F)[1] in mm")[-1]
    assert r.status == "ok"
    assert [float(row[1].split()[0]) for row in r.rows] == pytest.approx([13333.3, 26666.7], rel=1e-5)


def test_range_variable_inside_matrix_literal_outside_table_is_error():
    r = run("t := 1 to 2", "[t, 1] =")[-1]
    assert r.status == "error" and "range variable" in r.error
    r = run(A, "t := 1 to 2", "A[t, 1] =")[-1]
    assert r.status == "error" and "range variable" in r.error
    r = run(A, "t := 1 to 2", "y := A*t")[-1]
    assert r.status == "error" and "range variable" in r.error


def test_range_variable_named_like_matrix_function():
    r = run("eye := 1 to 3", "table eye")[-1]
    assert r.status == "ok" and r.rows == [["1"], ["2"], ["3"]]


# -- numeric cross-checks against NumPy (random matrices) -----------------------------------------------

@pytest.mark.parametrize("seed,n", [(0, 2), (1, 3), (2, 5), (3, 8)])
def test_random_float_matrices_vs_numpy(seed, n):
    rng = np.random.default_rng(seed)
    m = rng.uniform(-3, 3, (n, n)) + np.eye(n) * 4
    b = rng.uniform(-3, 3, (n, 1))
    a, bb = lit(m), lit(b)
    det = out("A := " + a, "det(A) =")
    value = float(det[2:].replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")))
    assert value == pytest.approx(np.linalg.det(m), rel=1e-5)
    inv = nums(out("A := " + a, "inv(A) =")) if n <= 10 else []
    assert inv == pytest.approx(np.linalg.inv(m).flatten().tolist(), rel=1e-4, abs=1e-5)
    x = nums(out("A := " + a, "b := " + bb, "solve_system(A, b) ="))
    assert x == pytest.approx(np.linalg.solve(m, b).flatten().tolist(), rel=1e-4, abs=1e-5)
    prod = nums(out("A := " + a, "A*A =")) if n <= 10 else []
    assert prod == pytest.approx((m @ m).flatten().tolist(), rel=1e-4, abs=1e-5)
    assert float(out("A := " + a, "trace(A) =")[2:]) == pytest.approx(np.trace(m), rel=1e-5)


def test_integer_matrix_results_are_exact():
    rng = np.random.default_rng(7)
    m = rng.integers(-5, 6, (4, 4))
    text = "[" + "; ".join(", ".join(str(int(v)) for v in row) for row in m) + "]"
    d = round(np.linalg.det(m.astype(float)))
    assert out("A := " + text, "det(A) =") == f"= {d}"
    sq = (m @ m).tolist()
    assert out("A := " + text, "A*A =") == "= [" + "; ".join(", ".join(str(v) for v in row) for row in sq) + "]"
    if d != 0:
        assert out("A := " + text, "(inv(A)*A)[2, 2] =") == "= 1"
        assert out("A := " + text, "(inv(A)*A)[2, 3] =") == "= 0"


def test_float_singular_tolerance():
    assert "singular" in err("inv([1.0, 2.0; 2.0, 4.0]) =")
    assert "singular" in err("inv([1.0, 2.0; 2.0, 4.0000000000000001]) =")
    assert out("inv([1, 2; 3, 4.0000000000001]) =").startswith("= [")
    assert "singular" in err("solve_system([1.0, 2.0; 2.0, 4.0], [1; 2]) =")


# -- performance -------------------------------------------------------------------------------------------

def test_50x50_float_performance():
    rng = np.random.default_rng(1)
    m = rng.random((50, 50)) + np.eye(50) * 5
    a = lit(m)
    for expr in ("det(A) =", "inv(A) =", "solve_system(A, ones(50, 1)) =", "A*A =", "transpose(A) ="):
        start = time.time()
        r = run("A := " + a, expr)[-1]
        assert r.status == "ok", (expr, r.error)
        assert time.time() - start < 2, expr
    r = run("A := " + a, "det(A) =")[-1]
    mant, exp = r.output[2:].split("×10")
    value = float(mant) * 10 ** int(exp.translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")))
    assert value == pytest.approx(np.linalg.det(m), rel=1e-4)
    assert float(run("A := " + a, "inv(A)[3, 7] =")[-1].output[2:]) == pytest.approx(np.linalg.inv(m)[2, 6], rel=1e-4)


def test_200x200_constructor_and_product_finish_quickly():
    start = time.time()
    assert run("A := ones(200, 200)", "A*A =")[-1].output == "= [200x200 matrix]"
    assert run("A := ones(200, 200)", "(A*A)[1, 1] =")[-1].output == "= 200"
    assert time.time() - start < 5


def test_literal_with_many_elements_parses():
    text = "[" + ", ".join(str(i) for i in range(500)) + "]"
    assert out("len(" + text + ") =") == "= 500"
    assert out(text + "[500] =") == "= 499"


def test_symbolic_6x6_det_is_not_a_freeze():
    s = "[" + "; ".join(", ".join(f"a{i}{j}" for j in range(6)) for i in range(6)) + "]"
    start = time.time()
    res = run("A := " + s, "det(A) →")[1]
    assert time.time() - start < 10
    assert res.status == "error" and "too large for symbolic" in res.error


def test_min_is_a_unit_not_a_function():
    assert err("min(5, 6) =") == "Not a function: min"
    assert out("Min(5, 6) =") == "= 5"


def test_nbsp_is_a_space():
    assert out("[1, 2]\u00a0*m =") == "= [1, 2] m"
