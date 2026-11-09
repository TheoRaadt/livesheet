"""Spec 017 phase S3: linear / polynomial regression (engine level)."""

import numpy as np
import pytest

from livesheet.engine import Engine

X4 = "x := [0, 1, 2, 3]"
NOISY = "y := [1, 2, 2, 4]"
LINE = "y := [1, 3, 5, 7]"
XP = "x := [0, 1, 2, 3, 4]"
YP = "y := [1, 2, 5, 10, 17]"


def run(*sources):
    return Engine().evaluate(enumerate(sources))[len(sources) - 1]


def out(*sources) -> str:
    r = run(*sources)
    assert r.status == "ok", r.error
    return r.output


def err(*sources) -> str:
    r = run(*sources)
    assert r.status == "error", r.output
    return r.error


def test_perfect_line():
    assert out(X4, LINE, "fit_linear(x, y) =") == "= [1; 2]"
    assert out(X4, LINE, "r_squared(fit_linear(x, y), x, y) =") == "= 1"


def test_noisy_line_matches_numpy():
    assert out(X4, NOISY, "fit_linear(x, y) =") == "= [0.9; 0.9]"
    assert np.allclose(np.polyfit([0, 1, 2, 3], [1, 2, 2, 4], 1), [0.9, 0.9])
    assert out(X4, NOISY, "predict(fit_linear(x, y), 4) =") == "= 4.5"
    assert out(X4, NOISY, "r_squared(fit_linear(x, y), x, y) =") == "= 0.852632"


def test_units():
    xs, ys = "x := [0, 1, 2, 3] s", "y := [1, 3, 5, 7] m"
    assert out(xs, ys, "fit_linear(x, y) =") == "= [1 m; 2 m/s]"
    assert out(xs, ys, "predict(fit_linear(x, y), 4 s) =") == "= 9 m"
    assert out(xs, ys, "r_squared(fit_linear(x, y), x, y) =") == "= 1"
    assert err(xs, ys, "predict(fit_linear(x, y), 4 m) =") == "Units do not match"


def test_poly_exact():
    assert out(XP, YP, "fit_poly(x, y, 2) =") == "= [1; 0; 1]"
    assert out(XP, YP, "predict(fit_poly(x, y, 2), 5) =") == "= 26"
    assert out(XP, YP, "r_squared(fit_poly(x, y, 2), x, y) =") == "= 1"


def test_poly_units_per_term():
    r = out("x := [0, 1, 2, 3, 4] s", "y := [1, 2, 5, 10, 17] m", "fit_poly(x, y, 2) =")
    assert r == "= [1 m; 0 m/s; 1 m/s²]"


def test_poly_degree_one_equals_linear():
    assert out(X4, NOISY, "fit_poly(x, y, 1) =") == out(X4, NOISY, "fit_linear(x, y) =")


def test_predict_vector_and_hand_coefficients():
    assert out(XP, YP, "predict(fit_poly(x, y, 2), x) =") == "= [1, 2, 5, 10, 17]"
    assert out("predict([1; 2], 3) =") == "= 7"
    assert out("predict([1, 2], [1; 2]) =") == "= [3; 5]"


def test_float_data():
    r = out("x := [0.5, 1.5, 2.2, 3.1]", "y := [1.1, 2.9, 5.2, 7.0]", "fit_linear(x, y) =")
    ref = np.polyfit([0.5, 1.5, 2.2, 3.1], [1.1, 2.9, 5.2, 7.0], 1)
    nums = [float(t) for t in r.strip("= []").split(";")]
    assert nums == pytest.approx([ref[1], ref[0]], rel=1e-4)


@pytest.mark.parametrize("src,msg", [
    (["fit_linear([1, 2, 3], [1, 2]) ="], "Vectors must have the same length (3 and 2)"),
    (["fit_linear([1], [1]) ="], "fit_linear() needs at least 2 points"),
    ([X4, NOISY, "fit_poly(x, y, 5) ="], "degree 5 needs at least 6 points, has 4"),
    ([X4, NOISY, "fit_poly(x, y, 0) ="], "degree must be a positive integer"),
    ([X4, NOISY, "fit_poly(x, y, 1.5) ="], "degree must be a positive integer"),
    (["predict([1, 2], [1, 2; 3, 4]) ="], "predict() needs a scalar or vector x"),
    (["predict(5, 1) ="], "predict() needs a vector of coefficients"),
    (["fit_linear([1, 1, 1], [1, 2, 3]) ="], "Matrix does not have full column rank"),
    (["r_squared([1; 2], [1, 2, 3], [5, 5, 5]) ="],
     "r_squared() is undefined when y is constant"),
    (["fit_linear(q, [1, 2]) ="], "q is not defined"),
])
def test_errors(src, msg):
    assert err(*src) == msg


def test_degree_equal_points_minus_one_allowed():
    assert out(X4, NOISY, "predict(fit_poly(x, y, 3), x) =") == "= [1, 2, 2, 4]"


# ---- S3 review D1/D2: ill-conditioned x must be accurate or a clean error ----

def _exact_ref(xs, ys, d):
    import sympy as sp
    a = sp.Matrix([[sp.Rational(x) ** k for k in range(d + 1)] for x in xs])
    b = sp.Matrix([sp.Rational(str(y)) for y in ys])
    return [float(v) for v in (a.T * a).LUsolve(a.T * b)]


def _parse(t: str) -> float:
    t = t.strip().replace("\u2212", "-")
    if "\u00d7" in t:
        mant, exp = t.split("\u00d710")
        exp = exp.translate(str.maketrans("\u207b\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079", "-0123456789"))
        return float(mant) * 10 ** int(exp)
    return float(t)


def _coeffs(xs, ys, d, fmt=str):
    r = run(f"x := [{', '.join(fmt(v) for v in xs)}]",
            f"y := [{', '.join(str(v) for v in ys)}]", f"c := fit_poly(x, y, {d})",
            "c =")
    assert r.status == "ok", r.error
    return r


@pytest.mark.parametrize("off,d,n", [(10000, 2, 6), (1000000, 2, 6), (1000, 3, 8), (100000, 3, 8)])
@pytest.mark.parametrize("as_float", [False, True])
def test_large_offset_matches_exact(off, d, n, as_float):
    xs = [off + i for i in range(n)]
    ys = [1, 3.1, 4.9, 7.2, 8.8, 11.1, 13.2, 14.9][:n]
    fmt = (lambda v: f"{v}.0") if as_float else str
    r = _coeffs(xs, ys, d, fmt)
    vals = [_parse(t) for t in r.output.strip("= []").replace(";", ",").split(",")]
    assert vals == pytest.approx(_exact_ref(xs, ys, d), rel=1e-5)


def test_first_repro_values():
    r = _coeffs([10000 + i for i in range(6)], [1, 3.1, 4.9, 7.2, 8.8, 11.1], 2)
    ref = _exact_ref([10000 + i for i in range(6)], [1, 3.1, 4.9, 7.2, 8.8, 11.1], 2)
    assert ref[0] == pytest.approx(337351, rel=1e-4) and ref[1] == pytest.approx(-69.4493, rel=1e-4)


def test_float_linear_1e6():
    xs = [1000000 + i for i in range(5)]
    r = run("x := [1000000.0, 1000001.0, 1000002.0, 1000003.0, 1000004.0]",
            "y := [1, 3, 5, 7, 9]", "fit_linear(x, y) =")
    assert r.status == "ok", r.error


def test_rank_deficient_still_errors_float_and_exact():
    assert err("fit_poly([5.0, 5.0, 6.0], [1, 2, 3], 2) =") == "Matrix does not have full column rank"
    assert err("fit_poly([100000, 100000, 100001], [1, 2, 3], 2) =") == "Matrix does not have full column rank"


def test_exact_inputs_stay_exact():
    assert out("fit_linear([0, 1, 2], [1, 3, 5]) =") == "= [1; 2]"
