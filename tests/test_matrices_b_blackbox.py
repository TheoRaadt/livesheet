"""Spec 002b black-box tests (tester), written from the spec text only. Reference values come
from NumPy / plain mathematics. xfail(strict=True) = open defect, see
docs/board/reviews/002b-eigen.md."""

import re
import time

import numpy as np
import pytest

from livesheet.engine import Engine


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
    return [float(x.replace("−", "-")) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text)]


def lit(m):
    return "[" + "; ".join(", ".join(repr(float(v)) for v in row) for row in m) + "]"


def close(text, expected, tol=1e-5):
    got = nums(text)
    assert got == pytest.approx(list(np.ravel(expected)), abs=tol, rel=1e-5), text


# -- AC1 ---------------------------------------------------------------------------
def test_ac1_eigenvalues_basic():
    assert out("eigenvalues([2, 1; 1, 2]) =") == "= [1; 3]"
    assert out("eigenvalues([4, 1; 2, 3]) =") == "= [2; 5]"
    assert out("eigenvalues(eye(3)) =") == "= [1; 1; 1]"


# -- AC2 ---------------------------------------------------------------------------
def test_ac2_imaginary_order():
    o = out("eigenvalues([0, -1; 1, 0]) =")
    assert o.index("-") < o.index("+") if "+" in o else o.startswith("= [-")
    assert o.count("i") == 2 and o.count(";") == 1
    # same-looking result for the explicit complex route
    assert o.replace(" ", "") == "=[-1i;1i]"


# -- AC3 ---------------------------------------------------------------------------
def test_ac3_units():
    assert out("eigenvalues([2, 1; 1, 2]*kPa) =") == "= [1000; 3000] Pa"


# -- AC4 ---------------------------------------------------------------------------
def test_ac4_symbolic_diag():
    o = out("eigenvalues([a, 0; 0, d]) →")
    assert "a" in o and "d" in o and o.startswith("→")


def test_ac4_exact_closed_form_and_numeric():
    o = out("eigenvalues([1, 2; 3, 4]) →")
    assert o.count("33") == 2
    assert "5/2" in o or "(5" in o
    assert out("eigenvalues([1, 2; 3, 4]) =") == "= [-0.372281; 5.37228]"


# -- AC5 ---------------------------------------------------------------------------
def test_ac5_eigenvectors():
    assert out("eigenvectors([2, 1; 1, 2]) =") == "= [0.707107, 0.707107; -0.707107, 0.707107]"
    assert out("eigenvectors([2, 0; 0, 3]) =") == "= [1, 0; 0, 1]"


@pytest.mark.parametrize("seed", range(6))
def test_ac5_property_symmetric_4x4(seed):
    rng = np.random.default_rng(seed)
    m = rng.uniform(-5, 5, (4, 4))
    a = (m + m.T) / 2
    A = lit(a)
    lam = np.array(nums(out(f"eigenvalues({A}) =")))
    V = np.array(nums(out(f"eigenvectors({A}) ="))).reshape(4, 4)
    assert np.max(np.abs(a @ V - V @ np.diag(lam))) < 1e-4  # printed to 6 digits
    assert np.allclose(lam, np.linalg.eigvalsh(a), atol=1e-4)
    assert np.all(np.diff(lam) >= 0)
    assert np.allclose(np.linalg.norm(V, axis=0), 1, atol=1e-5)
    for k in range(4):  # sign convention
        first = next(x for x in V[:, k] if abs(x) > 1e-9)
        assert first > 0


def test_ac5_residual_via_engine():
    a = np.array([[4, 1, 0.5, 2], [1, 3, 1, 0], [0.5, 1, 5, 1.5], [2, 0, 1.5, 6]])
    r = run(f"A := {lit(a)}", "V := eigenvectors(A)", "L := eigenvalues(A)",
            "R := A*V - V*diag(L)", "norm(R) =")
    assert r[-1].status == "ok", r[-1].error
    m = re.match(r"= (-?[\d.]+)(?:×10([⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+))?", r[-1].output)
    exp = 0
    if m.group(2):
        tr = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")
        exp = int(m.group(2).translate(tr))
    assert float(m.group(1)) * 10 ** exp < 1e-9, r[-1].output


# -- AC6 ---------------------------------------------------------------------------
@pytest.mark.parametrize("src,exp", [
    ("rank([1, 2; 3, 4]) =", "= 2"), ("rank([1, 2; 2, 4]) =", "= 1"),
    ("rank(zeros(3, 3)) =", "= 0"), ("rank([1, 2, 3; 4, 5, 6; 7, 8, 9]) =", "= 2"),
])
def test_ac6_rank(src, exp):
    assert out(src) == exp


def test_rank_float_tolerance_and_nonsquare():
    assert out("rank([1.0, 2.0; 2.0, 4.0000000000001]) =") == "= 1"
    assert out("rank([1, 2, 3; 4, 5, 6]) =") == "= 2"
    assert out("rank([1, 2; 2, 4; 3, 6]) =") == "= 1"


# -- AC7 ---------------------------------------------------------------------------
def test_ac7_norm():
    assert out("norm([3; 4]) =") == "= 5"
    assert out("norm([3; 4]*m) =") == "= 5 m"
    assert out("norm([1, 2; 3, 4]) =") == "= 5.47723"
    assert err("norm([1 m, 2 s]) =") == "Units do not match"


def test_norm_row_vector_and_complex_free():
    assert out("norm([1, 2, 2]) =") == "= 3"
    assert out("norm([0; 0]) =") == "= 0"


# -- AC8 ---------------------------------------------------------------------------
def test_ac8_least_squares():
    assert out("solve_least_squares([1, 1; 1, 2; 1, 3], [1; 2; 2]) =") == "= [0.666667; 0.5]"
    assert out("solve_least_squares([1, 2; 3, 4], [5; 6]) =") == "= [-4; 4.5]"
    assert out("solve_system([1, 2; 3, 4], [5; 6]) =") == "= [-4; 4.5]"
    assert out("solve_least_squares([1, 1; 1, 2; 1, 3]*N/m, [1; 2; 2]*N) =") == "= [0.666667; 0.5] m"


@pytest.mark.parametrize("seed", range(5))
def test_least_squares_vs_normal_equations(seed):
    rng = np.random.default_rng(100 + seed)
    a = rng.uniform(-3, 3, (6, 3)).round(3)
    b = rng.uniform(-3, 3, (6, 1)).round(3)
    x = np.linalg.solve(a.T @ a, a.T @ b)
    close(out(f"solve_least_squares({lit(a)}, {lit(b)}) ="), x)


# -- errors AC9-12 -----------------------------------------------------------------
def test_ac9_not_square():
    assert err("eigenvalues([1, 2, 3; 4, 5, 6]) =") == "Matrix must be square (got 2x3)"


def test_ac10_defective():
    assert err("eigenvectors([1, 1; 0, 1]) =") == "Matrix is defective: not enough independent eigenvectors"


def test_ac11_lsq_errors():
    assert err("solve_least_squares([1, 2; 2, 4; 3, 6], [1; 2; 3]) =") == "Matrix does not have full column rank"
    assert err("solve_least_squares([1, 2, 3; 4, 5, 6], [1; 2]) =") == "Need at least as many rows as columns"


def test_ac12_scalars():
    assert err("rank(5) =") == "rank() needs a matrix"
    assert out("norm(-5) =") == "= 5"


# -- edge cases --------------------------------------------------------------------
def test_8x8_exact_under_2s():
    rows = [[((i * 3 + j * 5) % 7) + (1 if i == j else 0) + (i + j if i == j else 0) for j in range(8)]
            for i in range(8)]
    sym = [[rows[min(i, j)][max(i, j)] for j in range(8)] for i in range(8)]  # symmetric integer
    src = "eigenvalues(" + "[" + "; ".join(", ".join(map(str, r)) for r in sym) + "]) ="
    t = time.time()
    o = out(src)
    assert time.time() - t < 2.0
    assert np.allclose(nums(o), np.linalg.eigvalsh(np.array(sym, float)), atol=1e-4)


def test_8x8_rational_nonsymmetric_under_2s():
    rows = [[f"{(i * 7 + j * 3) % 5 + 1}/{(i + j) % 3 + 1}" for j in range(8)] for i in range(8)]
    src = "eigenvalues([" + "; ".join(", ".join(r) for r in rows) + "]) ="
    t = time.time()
    r = run(src)[0]
    assert time.time() - t < 2.0
    assert r.status == "ok", r.error


def test_symbolic_entry_with_equals_is_not_defined_error():
    e = err("eigenvalues([a, 0; 0, d]) =")
    assert "not defined" in e


def test_mixed_exact_float_is_float():
    o = out("eigenvalues([2, 1.0; 1, 2]) =")
    close(o, [1, 3])
    o = out("eigenvalues([1, 2.0; 3, 4]) →")
    assert "√" not in o and "sqrt" not in o


def test_determinism_repeated_eigenvalues():
    src = "eigenvectors([2, 0, 0; 0, 2, 0; 0, 0, 5]) ="
    a, b = out(src), out(src)
    assert a == b
    V = np.array(nums(a)).reshape(3, 3)
    assert np.allclose(V.T @ V, np.eye(3), atol=1e-5)
    src = "eigenvectors([2, 1, 1; 1, 2, 1; 1, 1, 2]) ="
    assert out(src) == out(src)
    V = np.array(nums(out(src))).reshape(3, 3)
    assert np.allclose(V.T @ V, np.eye(3), atol=1e-5)  # orthonormal basis of the eigenspace


def test_eigenvalues_multiplicity():
    assert out("eigenvalues([2, 0, 0; 0, 2, 0; 0, 0, 5]) =") == "= [2; 2; 5]"
    assert out("eigenvalues([2, 1; 0, 2]) =") == "= [2; 2]"


def test_eigenvectors_nonsymmetric_sign_and_unit():
    V = np.array(nums(out("eigenvectors([4, 1; 2, 3]) ="))).reshape(2, 2)
    assert np.allclose(np.linalg.norm(V, axis=0), 1, atol=1e-5)
    a = np.array([[4, 1], [2, 3]], float)
    assert np.allclose(a @ V, V @ np.diag([2, 5]), atol=1e-5)
    for k in range(2):
        assert next(x for x in V[:, k] if abs(x) > 1e-9) > 0


def test_eigenvectors_dimensionless():
    o = out("eigenvectors([2, 1; 1, 2]*kPa) =")
    assert "Pa" not in o


def test_eigenvalues_negative_values_order():
    assert out("eigenvalues([-1, 0; 0, -3]) =") == "= [-3; -1]"


def test_eigen_of_1x1():
    assert out("eigenvalues([7]) =") == "= [7]" or out("eigenvalues([7]) =") == "= 7"


def test_eigenvalues_mixed_units_error():
    r = run("eigenvalues([1 m, 0; 0, 2 s]) =")[-1]
    assert r.status == "error"


def test_rank_ignores_units():
    assert out("rank([1, 2; 3, 4]*m) =") == "= 2"


def test_norm_of_matrix_with_unit():
    assert out("norm([3, 0; 0, 4]*m) =") == "= 5 m"


def test_norm_via_variable():
    assert out("v := [3; 4]", "norm(v) =") == "= 5"


def test_lsq_with_square_singular_message():
    # developer's choice: singular square A reports the full-column-rank message (consistent with AC11)
    assert err("solve_least_squares([1, 2; 2, 4], [1; 2]) =") == "Matrix does not have full column rank"


def test_lsq_rhs_dimension_mismatch():
    r = run("solve_least_squares([1, 1; 1, 2; 1, 3], [1; 2]) =")[-1]
    assert r.status == "error"


def test_defective_threshold_near_defective_not_rejected():
    # clearly non-defective, nearly equal eigenvalues: 1 and 1+1e-3
    r = run("eigenvectors([1, 0; 0, 1.001]) =")[-1]
    assert r.status == "ok", r.error


@pytest.mark.xfail(strict=True, reason="E1: x := eigenvalues(A) is numeric, so 'x ->' shows floats not closed forms")
def test_definition_then_arrow_gives_exact():
    # Spec: with -> eigenvalues are exact when closed forms exist. A definition is evaluated numerically
    # (developer's choice); judged below in the review.
    o = out("A := [1, 2; 3, 4]", "x := eigenvalues(A)", "x →")
    assert "33" in o or "√" in o
