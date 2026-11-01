"""Independent adversarial review of the bare-unit-name hardening (_check_bare_units).

Rule under test (decisions.md / STATUS item 2, Theo 2026-11-01): a name that is only a unit
because nothing defined it, used as a plain variable, is reported "<name> is not defined"; every
legitimate number-with-unit statement keeps working. Tests marked xfail(strict) document legitimate
pre-change behaviour that the hardening broke (see docs/board/reviews/022-...). Tests marked
GAP document known, accepted gaps (the check stays silent).
"""
from __future__ import annotations

import pytest

from livesheet.engine.evaluator import Engine


def run(*sources):
    res = Engine().evaluate(list(enumerate(sources)))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def out(*sources):
    r = last(*sources)
    assert r.status == "ok", r.error
    return r.output


def err(*sources):
    r = last(*sources)
    assert r.status == "error", r.output
    return r.error


# ------------------------------------------------------------------ must keep working

@pytest.mark.parametrize("src,expected", [
    (["5 N ="], "= 5 N"),
    (["10 m ="], "= 10 m"),
    (["3 m/s ="], "= 3 m/s"),
    (["2*N ="], "= 2 N"),
    (["N*2 ="], "= 2 N"),
    (["1/N ="], "= 1 s²/(kg·m)"),
    (["5 N/ m ="], "= 5 kg/s²"),
    (["2 N + N ="], "= 3 N"),
    (["pi*N ="], "= 3.14159 N"),
    (["9.81 m/s^2 ="], "= 9.81 m/s²"),
    (["x := 10 m", "x ="], "= 10 m"),
    (["x := 5000 N", "x = kN"], "= 5 kN"),
    (["x := 1 m", "x = mm"], "= 1000 mm"),
    (["x := 5 N", "y := x + N", "y ="], "= 6 N"),
    (["w := 4", "w*m ="], "= 4 m"),
    (["w := 4", "m*w ="], "= 4 m"),
    (["a := 5", "a*g ="], "= 49.0333 m/s²"),
    (["R := 8.314 J/(mol*K)", "R ="], "= 8.314 kg·m²/(s²·K·mol)"),
    (["x := 5 N", "y := [x N]", "y ="], "= [5] kg²·m²/s⁴"),
])
def test_unit_with_number_or_user_name_still_works(src, expected):
    assert out(*src) == expected


@pytest.mark.parametrize("src", [["I ="], ["e ="], ["pi ="], ["I*I ="], ["e^2 ="]])
def test_builtin_constants_unaffected(src):
    assert last(*src).status == "ok"


def test_definition_shadows_unit_name():
    assert out("F := 100 N", "A := 4 m^2", "sigma := F/A", "sigma =") == "= 25 Pa"
    assert out("F := 3", "F =") == "= 3"
    assert out("m := 3 kg", "m =") == "= 3 kg"
    assert out("m := 3", "10 m =") == "= 30"           # m is now a number, not metre
    assert out("s := 2", "t := s*m", "t =") == "= 2 m"


def test_global_definitions_shadow():
    assert out("F ::= 3 N", "F =") == "= 3 N"
    assert out("A ::= 2 m^2", "F ::= 4 N", "F/A =") == "= 2 Pa"
    assert out("F ≡ 3 N", "A := 2 m^2", "F/A =") == "= 1.5 Pa"


def test_function_parameter_shadows_unit():
    assert out("f(F) := F", "f(3) =") == "= 3"
    assert out("f(x) := x*N", "f(2) =") == "= 2 N"


def test_matrices_and_vectors_with_units():
    assert out("v := [1 2; 3 4]", "v*N =") .endswith(" N")
    assert out("A := [1 2; 3 4]", "A =") == "= [2; 12]"      # matrix-literal semantic pre-exists
    assert last("[N 1]").status == "ok"


def test_ranges_tables_solve_unaffected():
    assert last("t := 0 s to 10 s step 2 s", "table t").status == "ok"
    assert last("i := 1 to 3", "table i, N").status == "ok"
    r = run("vary x from 1 in q", "x*N == 5 N in q", "settle in q")[-1]
    assert r.status == "ok"
    assert last("t := 0 to 3", "table t, t*m").status == "ok"


def test_demo_sheet_unchanged():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    d = json.loads((root / "examples" / "demo.lsheet").read_text(encoding="utf-8"))
    regs = [(i, r.get("text", "")) for i, r in enumerate(d["regions"]) if r.get("kind") == "math"]
    res = Engine().evaluate(regs)
    # the demo's one intentional error is a unit mismatch (`L + F =`), not "not defined"
    errors = [(t, res[i].error) for i, t in regs if res[i].status == "error"]
    assert all("not defined" not in e for _t, e in errors), errors


# ------------------------------------------------------------------ must still error

def test_formula_with_undefined_unit_named_variables():
    r = run("sigma := F/A", "sigma =")
    assert r[0].status == "error" and r[0].error == "F is not defined"
    assert r[1].status == "error" and "not defined" in r[1].error


@pytest.mark.parametrize("src,name", [
    (["F ="], "F"), (["F/A ="], "F"), (["V*A ="], "V"), (["F = 5"], "F"),
    (["N*N ="], "N"), (["N/N ="], "N"), (["(N) ="], "N"), (["-N ="], "N"), (["N + N ="], "N"),
    (["x := 1", "y := N"], "N"),
])
def test_bare_unit_expressions_error(src, name):
    assert err(*src) == f"{name} is not defined"


def test_error_cascades_to_dependents():
    assert err("W := V*A", "W =") == "W is not defined"
    assert err("q := K", "q =") == "q is not defined"
    assert run("W := V*A")[0].error == "V is not defined"


def test_hardened_error_is_consistent_across_define_and_use():
    r = run("a := F", "b := a*2", "b =")
    assert r[0].status == "error"
    assert r[2].status == "error"


def test_shadow_only_when_defined_before_use():
    r = run("F/A =", "F := 100 N")
    assert r[0].status == "error"                    # F not yet defined above it


def test_user_defined_then_missing_other_still_reports_missing():
    r = last("F := 100 N", "F/Ac =")
    assert r.status == "error" and "Ac" in r.error


# ------------------------------------------------------------------ known gaps (documented, silent)

@pytest.mark.parametrize("src", [
    ["m^2 ="],                         # digit anywhere in the expression disables the check
    ["F^2/A ="], ["2*F/A ="],
    ["sqrt(F/A) ="],                   # a function name is not a UNITS name
    ["e*F ="], ["I*A ="],              # builtin constant mixed in
    ["P := 5 N", "P/A ="],             # one user name + a bare unit letter
])
def test_GAP_known_silent_cases(src):
    assert last(*src).status == "ok"


def test_GAP_symbolic_and_function_body_not_checked():
    assert last("F/A →").status == "ok"
    assert last("f(x) := F/A", "f(2) =").status == "ok"


# ------------------------------------------------------------------ regressions: legitimate before, errors now

@pytest.mark.xfail(strict=True, reason="REGRESSION: unit-alias definitions (`u := m/s`) now error")
def test_unit_alias_definition():
    assert out("u := m/s", "v := 5 u", "v =") == "= 5 m/s"


@pytest.mark.xfail(strict=True, reason="REGRESSION: `dist := m` alias now errors")
def test_unit_alias_single_unit():
    assert out("dist := m", "x := 5 dist", "x =") == "= 5 m"


@pytest.mark.xfail(strict=True, reason="REGRESSION: conversion-factor idiom `m = mm` now errors")
def test_bare_unit_conversion_factor_idiom():
    assert out("m = mm") == "= 1000 mm"


@pytest.mark.xfail(strict=True, reason="REGRESSION: `N*m = J` now errors")
def test_bare_unit_product_conversion_idiom():
    assert out("N*m = J") == "= 1 J"


@pytest.mark.xfail(strict=True, reason="REGRESSION: `g =` (standard gravity) now errors")
def test_bare_g_is_standard_gravity():
    assert out("g =") == "= 9.80665 m/s²"


@pytest.mark.xfail(strict=True, reason="REGRESSION: `z := [N m]` now errors")
def test_matrix_literal_of_unit_names():
    assert last("z := [N m]", "z =").status == "ok"


def test_error_text_for_valid_unit_is_misleading_but_stable():
    # Not a defect of the rule itself; documents the wording the user sees.
    assert err("N =") == "N is not defined"
