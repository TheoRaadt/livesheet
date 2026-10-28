"""Spec 002b: eigen-analysis, rank, norm and least squares (engine level)."""

import re
import time

import numpy as np
import pytest
import sympy as sp

from livesheet.engine import Engine


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
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


def _value(text: str) -> float:
    """Number in a result like '= 2.1×10⁻¹⁵' or '= 0.5'."""
    body = text.lstrip("= ").strip()
    if "×10" in body:
        mant, exp = body.split("×10")
        sup = {"⁻": "-", "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
               "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
        return float(mant) * 10 ** int("".join(sup[c] for c in exp))
    return float(body.split()[0])


def _entries(text: str) -> list[str]:
    return [_value(p) for p in re.split(r"[;,]", text.lstrip("= ").strip("[] "))]


def literal(arr) -> str:
    return "[" + "; ".join(", ".join(repr(float(x)) for x in row) for row in arr) + "]"


# -- 1-3 eigenvalues ------------------------------------------------------------

def test_eigenvalues_basic():
    assert out("eigenvalues([2, 1; 1, 2]) =") == "= [1; 3]"
    assert out("eigenvalues([4, 1; 2, 3]) =") == "= [2; 5]"
    assert out("eigenvalues(eye(3)) =") == "= [1; 1; 1]"


def test_eigenvalues_imaginary_ordered_by_imag():
    text = out("eigenvalues([0, -1; 1, 0]) =")
    assert text.index("-1i") < text.index("1i", text.index("-1i") + 2)


def test_eigenvalues_repeated_deterministic():
    first = out("eigenvalues([2, 0, 0; 0, 2, 0; 0, 0, 3]) =")
    assert first == "= [2; 2; 3]"
    assert out("eigenvalues([2, 0, 0; 0, 2, 0; 0, 0, 3]) =") == first


def test_eigenvalues_units():
    assert out("eigenvalues([2, 1; 1, 2]*kPa) =") == "= [1000; 3000] Pa"
    assert err("eigenvalues([1 m, 2 s; 3 m, 4 m]) =") == "Units do not match"


# -- 4 symbolic -------------------------------------------------------------------

def test_eigenvalues_symbolic_multiset():
    text = out("eigenvalues([a, 0; 0, d]) →")
    assert sorted(re.findall(r"[ad]", text)) == ["a", "d"]


def test_eigenvalues_exact_and_numeric():
    text = out("eigenvalues([1, 2; 3, 4]) →")
    assert text.count("√(33)") == 2 and "5/2" in text
    assert out("eigenvalues([1, 2; 3, 4]) =") == "= [-0.372281; 5.37228]"


def test_eigenvalues_no_closed_form():
    big = "[0,1,0,0,0;0,0,1,0,0;0,0,0,1,0;0,0,0,0,1;1,2,3,4,5]"
    assert err(f"eigenvalues({big}) →") == "No closed form found; use ="
    assert out(f"eigenvalues({big}) =").count(";") == 4


def test_eigenvalues_symbolic_with_equals_is_not_defined():
    assert err("eigenvalues([a, 1; 1, 2]) =") == "a is not defined"


# -- 5 eigenvectors ---------------------------------------------------------------

def test_eigenvectors_basic():
    assert out("eigenvectors([2, 1; 1, 2]) =") == "= [0.707107, 0.707107; -0.707107, 0.707107]"
    assert out("eigenvectors([2, 0; 0, 3]) =") == "= [1, 0; 0, 1]"


def test_eigenvectors_sign_convention_nonsymmetric():
    v = np.array(nums(out("eigenvectors([1, 2; 3, 4]) =")), dtype=float).reshape(2, 2)
    assert v[0, 0] > 0 and v[0, 1] > 0
    assert np.allclose(np.linalg.norm(v, axis=0), 1, atol=1e-5)


def test_eigenvectors_property_random_symmetric():
    rng = np.random.default_rng(7)
    b = rng.normal(size=(4, 4))
    a = b + b.T
    res = run(f"A := {literal(a)}", "V := eigenvectors(A)", "L := eigenvalues(A)",
              "R := A*V - V*diag(L)", "norm(R) =")
    assert res[-1].status == "ok", res[-1].error
    assert _value(res[-1].output) < 1e-9


def test_eigenvectors_repeated_full_set_is_orthonormal_and_deterministic():
    src = "eigenvectors([2, 0, 0; 0, 2, 0; 1, 0, 3]) ="
    first = out(src)
    assert out(src) == first
    v = np.array(nums(first), dtype=float).reshape(3, 3)
    assert np.allclose(v[:, :2].T @ v[:, :2], np.eye(2), atol=1e-5)
    res = run("A := [2, 0, 0; 0, 2, 0; 1, 0, 3]", "V := eigenvectors(A)", "A*V - V*diag(eigenvalues(A)) =")
    assert res[-1].status == "ok", res[-1].error
    assert all(abs(float(x)) < 1e-9 for x in _entries(res[-1].output))


def test_eigenvectors_symbolic_exact():
    text = out("eigenvectors([2, 1; 1, 2]) →")
    assert text == "→ [√(2)/2, √(2)/2; -√(2)/2, √(2)/2]"


def test_eigenvectors_complex_columns_have_positive_lead():
    text = out("eigenvectors([0, -1; 1, 0]) =")
    assert text.startswith("= [0.707107, 0.707107;")


# -- 6 rank -----------------------------------------------------------------------

def test_rank():
    assert out("rank([1, 2; 3, 4]) =") == "= 2"
    assert out("rank([1, 2; 2, 4]) =") == "= 1"
    assert out("rank(zeros(3, 3)) =") == "= 0"
    assert out("rank([1, 2, 3; 4, 5, 6; 7, 8, 9]) =") == "= 2"


def test_rank_floats_use_tolerance_and_ignore_units():
    assert out("rank([1.0, 2.0; 2.0, 4.0]) =") == "= 1"
    assert out("rank([1, 2; 3, 4]*m) =") == "= 2"
    assert out("rank([1 m, 2 s; 2 m, 4 s]) =") == "= 1"


# -- 7 norm -----------------------------------------------------------------------

def test_norm():
    assert out("norm([3; 4]) =") == "= 5"
    assert out("norm([3; 4]*m) =") == "= 5 m"
    assert out("norm([1, 2; 3, 4]) =") == "= 5.47723"
    assert err("norm([1 m, 2 s]) =") == "Units do not match"


def test_norm_complex_and_zero_unit():
    assert out("norm([3, 4i]) =") == "= 5"
    assert out("norm([0; 0]*m) =") == "= 0 m"


# -- 8 least squares --------------------------------------------------------------

def test_least_squares():
    assert out("solve_least_squares([1, 1; 1, 2; 1, 3], [1; 2; 2]) =") == "= [0.666667; 0.5]"
    assert out("solve_least_squares([1, 2; 3, 4], [5; 6]) =") == "= [-4; 4.5]"
    assert out("solve_least_squares([1, 2; 3, 4], [5; 6]) =") == out("solve_system([1, 2; 3, 4], [5; 6]) =")


def test_least_squares_units_and_floats():
    assert out("solve_least_squares([1, 1; 1, 2; 1, 3]*N/m, [1; 2; 2]*N) =") == "= [0.666667; 0.5] m"
    assert out("solve_least_squares([1.0, 1; 1, 2; 1, 3], [1; 2; 2]) =") == "= [0.666667; 0.5]"


def test_least_squares_symbolic():
    text = out("solve_least_squares([1, 0; 0, 1; 0, 0], [a; b; c]) →")
    assert text == "→ [a; b]"


# -- 9-12 errors ------------------------------------------------------------------

def test_errors():
    assert err("eigenvalues([1, 2, 3; 4, 5, 6]) =") == "Matrix must be square (got 2x3)"
    assert err("eigenvectors([1, 2, 3; 4, 5, 6]) =") == "Matrix must be square (got 2x3)"
    assert err("eigenvectors([1, 1; 0, 1]) =") == "Matrix is defective: not enough independent eigenvectors"
    assert err("solve_least_squares([1, 2; 2, 4; 3, 6], [1; 2; 3]) =") == "Matrix does not have full column rank"
    assert err("solve_least_squares([1, 2, 3; 4, 5, 6], [1; 2]) =") == "Need at least as many rows as columns"
    assert err("solve_least_squares([1, 2; 3, 4; 5, 6], [1; 2]) =") == "Right-hand side has 2 rows, matrix has 3"
    assert err("rank(5) =") == "rank() needs a matrix"
    assert err("eigenvalues(5) =") == "eigenvalues() needs a matrix"
    assert out("norm(-5) =") == "= 5"


# -- edge cases -------------------------------------------------------------------

def test_exact_8x8_eigenvalues_under_two_seconds():
    rows = "; ".join(", ".join(str((i * 3 + j * 5) % 7 + (4 if i == j else 0)) for j in range(8))
                     for i in range(8))
    start = time.perf_counter()
    text = out(f"eigenvalues([{rows}]) =")
    assert time.perf_counter() - start < 2.0
    assert text.count(";") == 7


def test_mixed_exact_and_float_is_float():
    assert out("eigenvalues([2, 1; 1, 2.0]) =") == "= [1; 3]"


def test_user_definition_shadows_function():
    assert out("rank := 3", "rank =") == "= 3"
