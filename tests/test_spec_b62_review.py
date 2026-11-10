"""Independent review of backlog 62: statistics builtins inside user-function bodies."""

import pytest

from livesheet.engine.evaluator import Engine


def last(*lines):
    res = Engine().evaluate(list(enumerate(lines)))
    return res[len(lines) - 1]


def out(*lines):
    r = last(*lines)
    assert r.status == "ok", r.error
    return r.output


def err(*lines):
    r = last(*lines)
    assert r.status == "error"
    return r.error


def test_units_preserved_through_body():
    assert out("f(u):=mean([u,1 m])", "f(1 m) =") == "= 1 m"
    assert out("f(a):=median([a,3 m,5 m])", "f(1 m) =") == "= 3 m"


def test_unit_mismatch_is_clean_error():
    assert err("f(u):=mean([u,2])", "f(1 m) =") == "Units do not match"


def test_unit_argument_rejection_matches_direct_message():
    direct = err("normal_cdf(1 m, 0, 1) =")
    assert err("f(a):=normal_cdf(a,0,1)", "f(1 m) =") == direct


def test_seeded_sample_in_body_matches_direct():
    for fn, body, direct in [
        ("normal", "normal_sample(u,1,3,7)", "normal_sample(0,1,3,7)"),
        ("uni", "uniform_sample(0,u,2,1)", "uniform_sample(0,5,2,1)"),
    ]:
        arg = "0" if fn == "normal" else "5"
        assert out(f"f(u):={body}", f"f({arg}) =") == out(f"{direct} =")


def test_seeded_sample_deterministic_and_count_parameter():
    a = out("f(u):=normal_sample(0,1,u,1)", "f(2) =")
    assert a == out("f(u):=normal_sample(0,1,u,1)", "f(2) =")
    assert a.count(";") == 1


def test_stats_of_sample_in_body_matches_direct():
    assert out("f(u):=mean(normal_sample(0,1,u,1))", "f(5) =") == out("mean(normal_sample(0,1,5,1)) =")


def test_wrong_arg_count_inside_body_is_clean():
    for body in ("normal_cdf(u)", "normal_cdf(u,0,1,5)", "mean(u,u)", "normal_sample(u,1,3)"):
        e = err(f"f(u):={body}", "f(3) =")
        assert e == "Wrong number of arguments"
        assert "TypeError" not in e and "positional" not in e


def test_wrong_arg_count_calling_user_function():
    assert err("f(u):=mean([u,1])", "f() =") == "Wrong number of arguments"
    assert err("f(u):=mean([u,1])", "f(1,2) =") == "Wrong number of arguments"


def test_engine_error_in_body_is_clean():
    assert err("f(u):=stdev([u])", "f(3) =") == "stdev() needs at least 2 values"


def test_zero_args_in_body_reports_arg_count():
    assert err("f(u):=mean()", "f(3) =") == "Wrong number of arguments"


def test_too_many_args_in_body_reports_arg_count():
    assert err("f(u):=mean(u,u,u)", "f(3) =") == "Wrong number of arguments"
    assert err("f(u):=normal_cdf(u,0,1,2)", "f(3) =") == "Wrong number of arguments"


def test_wrong_arg_count_in_nested_body_reports_arg_count():
    assert err("f(u):=mean()", "g(v):=f(v)+1", "g(3) =") == "Wrong number of arguments"
    assert err("f(u):=mean(u,u,u)", "g(v):=f(v)+1", "g(3) =") == "Wrong number of arguments"


def test_other_body_errors_still_say_not_defined():
    assert err("f(u):=u+zz", "f(3) =") != "Wrong number of arguments"


def test_nested_user_functions():
    lines = ("g(u):=mean([u,1])", "h(v):=g(v)+g(v+1)")
    assert out(*lines, "h(1) =") == out("mean([1,1])+mean([2,1]) =")
    assert out("g(u):=mean([u,1])", "h(v):=g(v)*2", "k(w):=h(w)+1", "k(3) =") == "= 5"


def test_scalar_and_vector_results_match_direct():
    assert out("f(u):=mean(u)", "f(3) =") == out("mean(3) =")
    assert out("f(a,b):=stdev([a,b,5])", "f(1,2) =") == out("stdev([1,2,5]) =")


def test_reevaluation_after_redefinition():
    assert out("f(u):=mean([u,1])", "f(3) =", "f(5) =") == "= 3"
