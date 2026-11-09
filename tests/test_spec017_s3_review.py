"""Independent black-box review of spec 017 phase S3 (regression)."""

import re

import numpy as np
import pytest

from livesheet.document import RegionData, SheetDocument
from livesheet.engine import Engine

SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def run(*src):
    return Engine().evaluate(enumerate(src))


def last(*src):
    return run(*src)[len(src) - 1]


def ok(*src) -> str:
    r = last(*src)
    assert r.status == "ok", r.error
    return r.output


def err(*src) -> str:
    r = last(*src)
    assert r.status == "error", r.output
    return r.error


def nums(out: str) -> list[float]:
    """Numbers of a printed vector/scalar, unit text ignored."""
    body = out.split("=", 1)[1]
    found = re.findall(r"-?\d+\.?\d*(?:×10([⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+))?", body)
    toks = re.finditer(r"(-?\d+\.?\d*)(?:×10([⁻⁰-⁹]+))?(?:e(-?\d+))?", body)
    res = []
    for m in toks:
        v = float(m.group(1))
        if m.group(2):
            v *= 10 ** int(m.group(2).translate(SUP))
        elif m.group(3):
            v *= 10 ** int(m.group(3))
        res.append(v)
    return res


def vec(xs):
    return "[" + ", ".join(repr(float(v)) if not float(v).is_integer() else str(int(v)) for v in xs) + "]"


def fit(xs, ys, deg=None):
    call = "fit_linear(x, y) =" if deg is None else f"fit_poly(x, y, {deg}) ="
    return nums(ok(f"x := {vec(xs)}", f"y := {vec(ys)}", call))


# ------------------------------------------------------------ spec criteria
def test_c1_perfect_line():
    assert ok("x := [0, 1, 2, 3]", "y := [1, 3, 5, 7]", "fit_linear(x, y) =") == "= [1; 2]"
    assert ok("x := [0, 1, 2, 3]", "y := [1, 3, 5, 7]", "r_squared(fit_linear(x, y), x, y) =") == "= 1"


def test_c2_noisy_line_and_r2():
    base = ["x := [0, 1, 2, 3]", "y := [1, 2, 2, 4]"]
    assert ok(*base, "fit_linear(x, y) =") == "= [0.9; 0.9]"
    assert ok(*base, "predict(fit_linear(x, y), 4) =") == "= 4.5"
    assert nums(ok(*base, "r_squared(fit_linear(x, y), x, y) =")) == [pytest.approx(0.852632, rel=1e-5)]


def test_c3_units():
    base = ["x := [0, 1, 2, 3] s", "y := [1, 3, 5, 7] m"]
    assert ok(*base, "fit_linear(x, y) =") == "= [1 m; 2 m/s]"
    assert ok(*base, "predict(fit_linear(x, y), 4 s) =") == "= 9 m"


def test_c4_poly_exact():
    base = ["x := [0, 1, 2, 3, 4]", "y := [1, 2, 5, 10, 17]"]
    assert ok(*base, "fit_poly(x, y, 2) =") == "= [1; 0; 1]"
    assert ok(*base, "predict(fit_poly(x, y, 2), 5) =") == "= 26"
    assert ok(*base, "r_squared(fit_poly(x, y, 2), x, y) =") == "= 1"


def test_c5_poly_degree1_equals_linear():
    base = ["x := [0, 1, 2, 3]", "y := [1, 2, 2, 4]"]
    assert ok(*base, "fit_poly(x, y, 1) =") == ok(*base, "fit_linear(x, y) =") == "= [0.9; 0.9]"


@pytest.mark.parametrize("src,msg", [
    (["fit_linear([1, 2, 3], [1, 2]) ="], "Vectors must have the same length (3 and 2)"),
    (["fit_linear([1], [1]) ="], "fit_linear() needs at least 2 points"),
    (["fit_poly([1, 2, 3, 4], [1, 2, 3, 4], 5) ="], "degree 5 needs at least 6 points, has 4"),
    (["fit_poly([1, 2, 3, 4], [1, 2, 3, 4], 0) ="], "degree must be a positive integer"),
    (["predict([1, 2], [1, 2; 3, 4]) ="], "predict() needs a scalar or vector x"),
    (["fit_linear([2, 2, 2], [1, 2, 3]) ="], "Matrix does not have full column rank"),
    (["r_squared([1, 0], [1, 2, 3], [5, 5, 5]) ="], "r_squared() is undefined when y is constant"),
])
def test_spec_errors(src, msg):
    assert err(*src) == msg


# ------------------------------------------------------------ vs numpy
@pytest.mark.parametrize("deg", [1, 2, 3, 4])
def test_noisy_vs_polyfit(deg):
    rng = np.random.default_rng(deg)
    xs = np.round(np.linspace(-3, 4, 12), 3)
    ys = np.round(1 + 2 * xs - 0.5 * xs**2 + 0.1 * xs**3 + rng.normal(0, 0.3, 12), 4)
    got = fit(xs, ys, deg)
    ref = np.polyfit(xs, ys, deg)[::-1]
    assert got == pytest.approx(ref, rel=2e-5, abs=1e-5)


@pytest.mark.parametrize("deg", [1, 2, 3, 4])
def test_exact_polynomials_float_and_int(deg):
    coeffs = [3, -2, 1, 2, -1][: deg + 1]
    xs = list(range(-2, 6))
    ys = [sum(c * x**k for k, c in enumerate(coeffs)) for x in xs]
    assert fit(xs, ys, deg) == pytest.approx(coeffs, abs=1e-9)
    assert ok(f"x := {vec(xs)}", f"y := {vec(ys)}", f"fit_poly(x, y, {deg}) =") == "= [" + "; ".join(map(str, coeffs)) + "]"


def test_unsorted_and_duplicate_x():
    xs, ys = [3, 1, 2, 1, 3, 0], [7.1, 2.9, 5.2, 3.1, 6.8, 1.0]
    assert fit(xs, ys) == pytest.approx(np.polyfit(xs, ys, 1)[::-1], rel=1e-5)
    xs2, ys2 = sorted(xs), [y for _, y in sorted(zip(xs, ys))]
    # order of the pairs is irrelevant
    assert fit(xs2, ys2) == pytest.approx(fit(xs, ys), rel=1e-9)


def test_overdetermined_equals_interpolation_at_n_points():
    xs, ys = [0, 1, 2, 3], [1, 4, 2, 9]
    got = fit(xs, ys, 3)  # degree == n-1 is the exact interpolant (allowed)
    assert got == pytest.approx(np.polyfit(xs, ys, 3)[::-1], rel=1e-4)
    assert "needs at least 5 points, has 4" in err("fit_poly([0,1,2,3],[1,4,2,9],4) =")


def test_r_squared_matches_formula():
    rng = np.random.default_rng(5)
    xs = np.round(np.linspace(0, 5, 9), 3)
    ys = np.round(2 + 0.7 * xs + rng.normal(0, 0.4, 9), 4)
    c = np.polyfit(xs, ys, 1)
    ref = 1 - np.sum((ys - np.polyval(c, xs)) ** 2) / np.sum((ys - ys.mean()) ** 2)
    out = ok(f"x := {vec(xs)}", f"y := {vec(ys)}", "r_squared(fit_linear(x, y), x, y) =")
    assert nums(out)[0] == pytest.approx(ref, rel=1e-5)


def test_r_squared_negative_for_bad_coeffs_not_an_error():
    # forced through origin with wrong slope: formula gives <0, spec says not an error
    assert nums(ok("r_squared([0, 0], [1, 2, 3], [1, 2, 4]) ="))[0] == pytest.approx(-3.5)


def test_r_squared_hand_built_coefficients_any_length():
    # y = 2 exactly predicted by [2]; y not constant
    assert nums(ok("r_squared([0, 1], [1, 2, 3], [1, 2, 3]) ="))[0] == pytest.approx(1)


def test_r_squared_constant_y_even_with_perfect_prediction():
    assert err("r_squared([5, 0], [1, 2, 3], [5, 5, 5]) =") == "r_squared() is undefined when y is constant"


def test_r_squared_length_mismatch():
    assert err("r_squared([1, 0], [1, 2, 3], [1, 2]) =").startswith("Vectors must have the same length")


# ------------------------------------------------------------ shapes
def test_row_vs_column_inputs_same_result():
    a = ok("fit_linear([3,1,2,1],[7,3,5,3.2]) =")
    assert ok("fit_linear([3;1;2;1],[7;3;5;3.2]) =") == a
    assert ok("fit_linear([3;1;2;1],[7,3,5,3.2]) =") == a
    assert nums(a) == pytest.approx(np.polyfit([3, 1, 2, 1], [7, 3, 5, 3.2], 1)[::-1], rel=1e-5)


def test_fit_returns_column_vector_ascending():
    r = last("x := [0,1,2,3]", "y := [1,3,5,7]", "fit_poly(x, y, 2) =")
    assert r.output.count(";") == 2 and "," not in r.output


def test_predict_keeps_shape_of_x():
    c = ["x := [0,1,2,3]", "y := [1,3,5,7]"]
    assert ok(*c, "predict(fit_linear(x, y), [1, 2]) =") == "= [3, 5]"
    assert ok(*c, "predict(fit_linear(x, y), [1; 2]) =") == "= [3; 5]"
    assert ok(*c, "predict(fit_linear(x, y), 2) =") == "= 5"


def test_predict_accepts_row_or_column_coeffs_and_hand_built():
    assert ok("predict([1, 2], 3) =") == ok("predict([1; 2], 3) =") == "= 7"
    assert ok("predict([1, 0, 2], [0, 1, 2]) =") == "= [1, 3, 9]"
    assert ok("predict([4], 100) =") == "= 4"


@pytest.mark.parametrize("call", ["predict(3, 2) =", "predict([1,2,3;1,2,3], 3) =", "predict(a, 2) ="])
def test_predict_bad_coeffs(call):
    e = err("a := 5", call) if "a," in call else err(call)
    assert e == "predict() needs a vector of coefficients"


def test_predict_matrix_x_rejected():
    assert err("predict([1,2],[1,2;3,4]) =") == "predict() needs a scalar or vector x"


def test_fit_scalar_and_matrix_args():
    assert "needs" in err("fit_linear(3, 4) =")
    assert err("fit_linear([1,2;3,4],[1,2;3,4]) =") == "fit_linear() needs a vector"


def test_complex_and_undefined():
    assert err("fit_linear([1,2],[1,I]) =") == "fit_linear() needs real numbers"
    assert err("fit_linear(q,[1,2]) =") == "q is not defined"


# ------------------------------------------------------------ check order / degree
@pytest.mark.parametrize("deg", ["1.5", "0.5", "-1", "0"])
def test_bad_degree_texts(deg):
    assert err(f"fit_poly([1,2,3,4],[1,2,3,4],{deg}) =") == "degree must be a positive integer"


def test_integer_valued_float_degree_accepted():
    assert ok("fit_poly([1,2,3,4],[1,2,3,4],2.0) =") == "= [0; 1; 0]"


def test_degree_with_unit_rejected_cleanly():
    assert err("fit_poly([1,2,3,4],[1,2,3,4],1 m) =") != ""


def test_check_order_length_then_degree_then_count():
    # length wins over bad degree
    assert err("fit_poly([1,2,3],[1,2],0) =").startswith("Vectors must have the same length")
    # degree validity wins over point count
    assert err("fit_poly([1,2,3],[1,2,3],0) =") == "degree must be a positive integer"
    assert err("fit_poly([1,2,3],[1,2,3],9) =") == "degree 9 needs at least 10 points, has 3"
    # fit_linear: length before count
    assert err("fit_linear([1],[1,2]) =").startswith("Vectors must have the same length")


def test_fit_poly_one_point():
    assert "needs at least" in err("fit_poly([1],[1],1) =")


# ------------------------------------------------------------ units
def test_poly_units_per_term():
    base = ["x := [0, 1, 2, 3] s", "y := [1, 3, 5, 7] m"]
    assert ok(*base, "fit_poly(x, y, 2) =") == "= [1 m; 2 m/s; 0 m/s²]"


def test_dimensionless_x_with_unit_y():
    assert ok("x := [0,1,2,3]", "y := [1,3,5,7] m", "fit_linear(x, y) =") == "= [1; 2] m"
    assert ok("x := [0,1,2,3]", "y := [1,3,5,7] m", "fit_poly(x, y, 2) =") == "= [1; 2; 0] m"


def test_dimensionless_y_with_unit_x():
    assert ok("x := [0,1,2,3] s", "y := [1,3,5,7]", "fit_linear(x, y) =") == "= [1; 2 s⁻¹]"


def test_predict_unit_x_required_when_coeffs_have_units():
    base = ["x := [0,1,2,3] s", "y := [1,3,5,7] m"]
    assert err(*base, "predict(fit_linear(x, y), 4) =") == "Units do not match"
    assert err(*base, "predict(fit_linear(x, y), 4 kg) =") != ""


def test_predict_unit_vector():
    base = ["x := [0,1,2,3] s", "y := [1,3,5,7] m"]
    assert ok(*base, "predict(fit_linear(x, y), [1 s, 2 s]) =") == "= [3, 5] m"


def test_mixed_units_same_dimension_values_correct_in_si():
    # x in mm, y in m: slope m/mm has the dimension of 1; value is 2000, prints plain (disclosed)
    base = ["x := [0,1,2,3] mm", "y := [1,3,5,7] m"]
    assert ok(*base, "fit_linear(x, y) =") == "= [1 m; 2000]"
    assert ok(*base, "predict(fit_linear(x, y), 4 mm) =") == "= 9 m"
    assert ok(*base, "predict(fit_linear(x, y), 4 m) =") == "= 8001 m"
    assert nums(ok(*base, "r_squared(fit_linear(x, y), x, y) ="))[0] == pytest.approx(1)


def test_different_prefix_same_unit_vectors():
    # y in mm and in m give the same fit once converted
    a = ok("x := [0,1,2,3] s", "y := [1000,3000,5000,7000] mm", "fit_linear(x, y) =")
    assert a == "= [1 m; 2 m/s]"


def test_r_squared_unit_rule():
    base = ["x := [0,1,2,3] s", "y := [1,3,5,7] m"]
    assert err(*base, "r_squared(fit_linear(x, y), x, [1,3,5,7] kg) =") != ""
    assert ok(*base, "r_squared(fit_linear(x, y), x, y) =") == "= 1"


def test_r_squared_is_dimensionless_with_units_noisy():
    base = ["x := [0,1,2,3] s", "y := [1,2,2,4] m"]
    assert nums(ok(*base, "r_squared(fit_linear(x, y), x, y) ="))[0] == pytest.approx(0.852632, rel=1e-5)


def test_non_homogeneous_vector_rejected():
    assert err("fit_linear([1 s, 2 m, 3 s], [1, 2, 3]) =") != ""


# ------------------------------------------------------------ conditioning
def test_year_like_x_degree1_and_2():
    xs = list(range(1990, 2021, 5))
    ys = [10, 12, 15, 19, 25, 31, 40]
    for d in (1, 2):
        got = fit(xs, ys, d)
        assert got == pytest.approx(np.polyfit(xs, ys, d)[::-1], rel=1e-3)


def test_tiny_and_huge_scales():
    assert fit([1e-6, 2e-6, 3e-6, 4e-6], [1, 2.1, 2.9, 4]) == pytest.approx([0.05, 9.8e5], rel=1e-4)
    got = fit([1, 2, 3, 4], [1e9, 2.1e9, 2.9e9, 4e9])
    assert got == pytest.approx([5e7, 9.8e8], rel=1e-4)


def _exact(xs, ys, d):
    import sympy as sp
    a = sp.Matrix([[sp.Rational(x) ** k for k in range(d + 1)] for x in xs])
    b = sp.Matrix([sp.Rational(y) for y in ys])
    return [float(v) for v in (a.T * a).LUsolve(a.T * b)]


def _offset_case(off, d):
    xs = [off + i for i in range(8)]
    ys = [1 + 0.5 * i + 0.1 * (-1) ** i + 0.02 * i * i for i in range(8)]
    return xs, ys, _exact(xs, [round(y, 6) for y in ys], d)


def _clean_or_accurate(off, d, rel):
    """Acceptable: an accurate answer or a clean error. Unacceptable: a wrong answer."""
    xs, ys, ref = _offset_case(off, d)
    ys = [round(y, 6) for y in ys]
    r = last(f"x := {vec(xs)}", f"y := {vec(ys)}", f"fit_poly(x, y, {d}) =")
    if r.status == "error":
        return "error", r.error
    return "ok", np.allclose(nums(r.output), ref, rtol=rel)


@pytest.mark.parametrize("off,d", [(10, 1), (100, 2), (1000, 1), (1000, 2), (100, 3)])
def test_offset_x_accurate(off, d):
    kind, v = _clean_or_accurate(off, d, 1e-4)
    assert kind == "ok" and v is True


@pytest.mark.parametrize("off,d", [(1000, 3), (2000, 3)])
def test_offset_x_cubic_never_silently_wrong(off, d):
    kind, v = _clean_or_accurate(off, d, 1e-3)
    assert kind == "error" or v is True


@pytest.mark.parametrize("off", [10000, 1000000])
def test_integer_x_offset_quadratic_never_silently_wrong(off):
    ys = [1, 3.1, 4.9, 7.2, 8.8, 11.1]
    xs = [off + i for i in range(6)]
    ref = _exact_f(xs, ys, 2)
    r = last(f"x := {vec(xs)}", f"y := {vec(ys)}", "fit_poly(x, y, 2) =")
    assert r.status == "error" or np.allclose(nums(r.output), ref, rtol=1e-3)


def _exact_f(xs, ys, d):
    import sympy as sp
    a = sp.Matrix([[sp.Rational(x) ** k for k in range(d + 1)] for x in xs])
    b = sp.Matrix([sp.Rational(str(y)) for y in ys])
    return [float(v) for v in (a.T * a).LUsolve(a.T * b)]


def test_float_typed_x_offset_not_rank_deficient():
    r = last("x := [10000.0,10001.0,10002.0,10003.0,10004.0,10005.0]", "y := [1,3.1,4.9,7.2,8.8,11.1]", "fit_poly(x, y, 2) =")
    assert r.status == "ok", r.error


def test_linear_with_large_offset_is_accurate():
    ys = [1, 3.1, 4.9, 7.2, 8.8, 11.1]
    for off in (3000, 10000, 1000000):
        xs = [off + i for i in range(6)]
        assert fit(xs, ys) == pytest.approx(_exact_f(xs, ys, 1), rel=1e-4)


def test_large_offset_integer_data_exact():
    # integer data goes through the exact path and stays exact
    xs = [10**6 + i for i in range(6)]
    ys = [3 + 2 * x for x in xs]
    assert ok(f"x := {vec(xs)}", f"y := {vec(ys)}", "fit_linear(x, y) =") == "= [3; 2]"


def test_large_offset_fails_cleanly_not_with_crash():
    r = last("x := [1000000,1000001,1000002,1000003]", "y := [1,3,5,7.1]", "fit_linear(x, y) =")
    assert r.status in ("ok", "error") and (r.status == "ok" or r.error)


# ------------------------------------------------------------ in sheets
def test_define_use_later_and_redefine():
    res = run("x := [0,1,2,3]", "y := [1,2,2,4]", "c := fit_linear(x, y)", "c =",
              "predict(c, 10) =", "c[1] =", "len(c) =")
    assert res[3].output == "= [0.9; 0.9]"
    assert res[4].output == "= 9.9"
    assert res[6].output == "= 2"


def test_predict_inside_user_function():
    res = run("c := fit_linear([0,1,2,3],[1,2,2,4])", "h(u) := predict(c, u)", "h(10) =")
    assert res[2].output == "= 9.9"


def test_fit_inside_expression_arithmetic():
    out = ok("x := [0,1,2,3]", "y := [1,3,5,7]", "2 * predict(fit_linear(x, y), 4) + 1 =")
    assert out == "= 19"


def test_fit_with_s1_functions():
    out = ok("x := [1,2,3,4]", "y := [2,4,6,8]", "mean(fit_linear(x, y)) =")
    assert nums(out) == [pytest.approx(1.0, abs=1e-9)]


def test_changing_data_updates_fit():
    base = ["x := [0,1,2,3]", "y := [1,3,5,7]"]
    assert ok(*base, "fit_linear(x, y) =") == "= [1; 2]"
    assert ok("x := [0,1,2,3]", "y := [2,4,6,8]", "fit_linear(x, y) =") == "= [2; 2]"


def test_symbolic_data_does_not_crash():
    r = last("x := [0,1,2,3]", "y := [a,2,3,4]", "fit_linear(x, y) =")
    assert r.status in ("ok", "error")
    r = last("fit_linear([0,1,2],[1,2,3]) -> ")
    assert r.status in ("ok", "error")


def test_roundtrip_sheet(tmp_path):
    lines = ["x := [0,1,2,3]", "y := [1,2,2,4]", "fit_linear(x, y) =", "r_squared(fit_linear(x, y), x, y) ="]
    doc = SheetDocument([RegionData("math", 10, 10 + 30 * i, t) for i, t in enumerate(lines)])
    p = tmp_path / "t.lsheet"
    doc.save(p)
    back = SheetDocument.load(p)
    res = run(*[r.text for r in back.regions])
    assert res[2].output == "= [0.9; 0.9]" and res[3].output.startswith("= 0.85263")


def test_large_vector_fast():
    import time
    n = 2000
    xs = np.linspace(0, 10, n)
    ys = 2 + 3 * xs + np.sin(xs)
    t = time.time()
    r = last(f"x := {vec(np.round(xs, 4))}", f"y := {vec(np.round(ys, 4))}", "fit_poly(x, y, 3) =")
    assert r.status == "ok", r.error
    assert time.time() - t < 20


# ------------------------------------------------------------ regression risk
def test_solve_least_squares_unchanged():
    out = ok("solve_least_squares([1,0;1,1;1,2;1,3],[1;3;5;7]) =")
    assert nums(out) == pytest.approx([1, 2], abs=1e-9)


def test_s1_functions_still_work():
    assert nums(ok("mean([1,2,3,4]) ="))[0] == 2.5
    assert nums(ok("stdev([2,4,4,4,5,5,7,9]) ="))[0] == pytest.approx(2.138090, rel=1e-6)


def test_builtins_registered_names():
    for n in ("fit_linear", "fit_poly", "predict", "r_squared"):
        r = last(f"{n}() =")
        assert r.status == "error" and "not defined" not in r.error and "Unknown" not in r.error, (n, r.error)
