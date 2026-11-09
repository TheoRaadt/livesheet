"""Backlog 62: statistics builtins inside user-function bodies."""

from livesheet.engine.evaluator import Engine


def run(*lines):
    res = Engine().evaluate(list(enumerate(lines)))
    return [res[i] for i in range(len(lines))]


def out(*lines):
    r = run(*lines)[-1]
    assert r.status == "ok", r.error
    return r.output


DATA = ("x := [1;2;3;4]", "y := [2;4;5;8]", "c := fit_linear(x, y)")


def test_mean_with_parameter():
    assert out("h(u) := mean([u, 1])", "h(3) =") == "= 2"


def test_stdev_and_median_with_parameter():
    assert out("s(u) := stdev([u, 2, 5])", "s(1) =") == "= 2.08167"
    assert out("m(u) := median([u, 5, 1])", "m(9) =") == "= 5"


def test_predict_in_body_matches_direct():
    assert out(*DATA, "g(u) := predict(c, u)", "g(10) =") == out(*DATA, "predict(c, 10) =")


def test_normal_cdf_in_body():
    assert out("n(u) := normal_cdf(u, 0, 1)", "n(0) =") == "= 0.5"


def test_stats_with_units():
    assert out("L(a) := mean([a*1 m, 3 m])", "L(1) =") == "= 2 m"


def test_user_function_calling_user_function_with_stats():
    assert out("h(u) := mean([u, 1])", "k(u) := h(u)*2", "k(3) =") == "= 4"


def test_direct_calls_still_work():
    assert out("mean([1,2,3]) =") == "= 2"
    assert out(*DATA, "predict(c, 10) =") == "= 19"


def test_undefined_names_still_reported():
    assert run("mean(zz) =")[0].error == "zz is not defined"
    r = run("n(u) := normal_cdf(u, 0, 1)", "n(q) =")[1]
    assert r.status == "error" and "q is not defined" in r.error
