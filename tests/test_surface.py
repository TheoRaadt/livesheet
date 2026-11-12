"""Spec 031 phase A1: surface statement, grid sampling, limits, cell rule (engine only)."""

import math
import time

import pytest

from livesheet.engine import Engine, parse_statement

A = ["surface", "over x from 0 to 2 points 3", "across y from 0 to 2 points 3", "show x + 2*y"]


def run(*srcs: str):
    results = Engine().evaluate([(i, s) for i, s in enumerate(srcs)])
    return results[len(srcs) - 1]


def spec(*lines: str) -> str:
    return "\n".join(lines)


def surf(*extra: str, base=A):
    res = run(spec(*base, *extra))
    assert res.status == "ok", res.error
    return res.surface


def err(*srcs: str) -> str:
    res = run(*srcs)
    assert res.status == "error" and res.surface is None
    return res.error


def test_basic_surface():
    res = run(spec(*A))
    assert res.status == "ok" and res.defines == "" and res.output == "surface 3 x 3 points"
    s = res.surface
    assert s.xs == [0, 1, 2] and s.ys == [0, 1, 2]
    assert s.zs == [[0, 1, 2], [2, 3, 4], [4, 5, 6]]
    assert s.x_limits == (0, 2) and s.x_ticks == [0, 0.5, 1, 1.5, 2]
    assert s.y_limits == (0, 2) and s.y_ticks == [0, 0.5, 1, 1.5, 2]
    assert s.z_limits == (0, 6) and s.z_ticks == [0, 1, 2, 3, 4, 5, 6]
    assert (s.x_unit, s.y_unit, s.z_unit) == ("", "", "")
    assert (s.draw, s.view_az, s.view_el, s.skipped, s.cells_drawn) == ("mesh", 40, 30, 0, 4)


def test_units_and_display_unit():
    s = surf("zunit kN", base=["surface", "over x from 0 m to 2 m points 3",
                               "across y from 0 to 2 points 3", "show 500 N * (x/m) * y"])
    assert s.zs == [[0, 0, 0], [0, 0.5, 1], [0, 1, 2]]
    assert (s.x_unit, s.y_unit, s.z_unit) == ("m", "", "kN")
    assert s.z_limits == (0, 2) and s.z_ticks == [0, 0.5, 1, 1.5, 2]
    assert (s.z_label, s.x_label, s.y_label) == ("500 N * (x/m) * y [kN]", "x [m]", "y")


def test_range_variable_axis():
    res = run("t := 0 s to 2 s step 1 s",
              spec("surface", "over t", "across y from 0 to 1 points 2", "show t*y"))
    s = res.surface
    assert s.xs == [0, 1, 2] and s.ys == [0, 1] and s.zs == [[0, 0, 0], [0, 1, 2]]
    assert s.z_unit == "s" and s.x_unit == "s"
    assert s.z_limits == (0, 2) and s.z_ticks == [0, 0.5, 1, 1.5, 2]


def test_vector_axis():
    res = run("v := [1, 2, 3]", spec("surface", "over v", "across y from 0 to 1 points 2", "show v*10 + y"))
    assert res.status == "ok", res.error
    assert res.surface.zs == [[10, 20, 30], [11, 21, 31]]


def test_defaults_and_caps():
    base = ["surface", "over x from 0 to 1", "across y from 0 to 1", "show x + y"]
    res = run(spec(*base))
    assert len(res.surface.xs) == 25 and res.output == "surface 25 x 25 points"
    big = ["surface", "over x from 0 to 1 points 100", "across y from 0 to 1 points 100", "show x + y"]
    assert run(spec(*big)).surface.cells_drawn == 99 * 99


def test_manual_horizontal_limits():
    s = surf("xlim 0.5 to 1.5")
    assert s.x_limits == (0.5, 1.5) and s.x_ticks == [0.6, 0.8, 1, 1.2, 1.4]
    s = surf("xlim 0 to 1.5")
    assert s.cells_drawn == 2 and s.zs == [[0, 1, 2], [2, 3, 4], [4, 5, 6]]
    assert surf("ylim 0 to 1.5").cells_drawn == 2


def test_manual_height_limit():
    s = surf("zlim 0 to 4")
    assert s.z_limits == (0, 4)
    assert s.z_ticks == [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4] and s.cells_drawn == 2


def test_undefined_heights():
    res = run(spec("surface", "over x from -1 to 1 points 3", "across y from 0 to 1 points 2", "show 1/x"))
    s = res.surface
    assert res.status == "ok" and s.xs == [-1, 0, 1] and s.ys == [0, 1]
    assert s.zs[0][0] == -1 and math.isnan(s.zs[0][1]) and s.zs[1][2] == 1
    assert s.skipped == 2 and s.cells_drawn == 0
    assert s.z_limits == (-1, 1) and s.z_ticks == [-1, -0.5, 0, 0.5, 1]


def test_constant_height():
    s = surf(base=A[:3] + ["show 5 m + 0*x"])
    assert s.z_limits == pytest.approx((4.4, 5.6), abs=1e-9)
    assert s.z_ticks == pytest.approx([4.4, 4.6, 4.8, 5.0, 5.2, 5.4, 5.6], abs=1e-9)
    assert s.z_unit == "m" and s.cells_drawn == 4


def test_no_finite_height():
    assert "no finite values to plot" in err(spec("surface", "over x from 0 to 2 points 3",
                                                  "across y from 0 to 2 points 3", "show sqrt(x - 10)"))


def test_sampling_name_shadows_only_inside():
    results = Engine().evaluate([(0, "x := 7"), (1, spec("surface", "over x from 0 to 1 points 2",
                                                         "across y from 0 to 1 points 2", "show x + y")),
                                 (2, "x =")])
    assert results[1].surface.xs == [0, 1]
    assert results[2].output == "= 7"


def test_parse_once():
    for n in (25, 100):
        eng, calls = Engine(), []
        orig = eng.parse
        eng.parse = lambda text, env, keep_units=False: (calls.append(text), orig(text, env, keep_units))[1]
        src = spec("surface", f"over x from 0 to 1 points {n}", f"across y from 0 to 1 points {n}", "show x*y")
        assert eng.evaluate([(0, src)])[0].status == "ok"
        assert calls.count("x*y") <= 2


def test_performance():
    for n, limit in ((25, 0.5), (100, 3.0)):
        src = spec("surface", f"over x from 0 to 1 points {n}", f"across y from 0 to 1 points {n}", "show x*y")
        t0 = time.perf_counter()
        assert run(src).status == "ok"
        assert time.perf_counter() - t0 < limit * 2


def test_fallback_matches_fast(monkeypatch):
    from livesheet.engine import surface as mod

    fast = surf("zunit kN", base=["surface", "over x from 0 m to 2 m points 3",
                                  "across y from 0 to 2 points 3", "show 500 N * (x/m) * y"])

    def broken(*a, **k):
        raise RuntimeError("no fast path")

    monkeypatch.setattr(mod, "_heights_fast", broken)
    slow = surf("zunit kN", base=["surface", "over x from 0 m to 2 m points 3",
                                  "across y from 0 to 2 points 3", "show 500 N * (x/m) * y"])
    assert slow.zs == fast.zs and slow.z_unit == fast.z_unit


def test_regression_names():
    assert run("plot := 3", "plot =").output == "= 3"
    assert run("surface := 3", "surface =").output == "= 3"
    assert parse_statement("surface := 3").kind == "define"


def test_plot_grammar_unaffected():
    res = run(spec("plot", "over x from 0 to 1", "across y from 0 to 1", "show x"))
    assert res.status == "error" and "Unknown plot option 'across'" in res.error


@pytest.mark.parametrize("lines,text", [
    (["over x from 0 to 1", "show x"], "surface needs an 'across' line"),
    (["across y from 0 to 1", "show y"], "surface needs an 'over' line"),
    (["over x from 0 to 1", "across y from 0 to 1"], "surface needs a 'show' line"),
    (["over x from 0 to 1", "across y from 0 to 1", "show x", "show y"],
     "surface takes exactly one 'show' line"),
    (["over x from 0 to 1", "over x from 0 to 2", "across y from 0 to 1", "show x"],
     "only one 'over' line is allowed"),
    (["over x from 0 to 1", "across x from 0 to 1", "show x"], "over and across need different names"),
    (A[1:] + ["colour red"], "Unknown 3-D plot option 'colour'"),
    (["over x from 0 to 1 points 1", "across y from 0 to 1", "show x"], "points must be between 2 and 100"),
    (["over x from 0 to 1", "across y from 0 to 1 points 101", "show x"], "points must be between 2 and 100"),
    (A[1:] + ["draw dots"], "draw must be mesh or wire"),
    (A[1:] + ["view 40 95"], "elevation must be between -90 and 90"),
    (A[1:] + ["view 40"], "view needs two numbers: azimuth and elevation"),
    (A[1:] + ["view 40 m"], "view needs two plain numbers"),
    (A[1:] + ["zunit s"], "zunit given but z has no unit"),
    (A[1:] + ["xlim 2 to 1"], "lower limit must be below upper limit"),
    (["over x from 0 to 1", "across q", "show x"], "q is not defined"),
])
def test_errors(lines, text):
    assert text in err(spec("surface", *lines))


def test_unit_errors():
    base = ["over t from 0 s to 1 s points 2", "across y from 0 to 1 points 2", "show t"]
    assert "Units do not match" in err(spec("surface", *base, "zunit kg"))
    assert "Units do not match" in err(spec("surface", *base, "xlim 5 m to 10 m"))


def test_shape_errors():
    assert "show 'X' needs a single value" in err(
        "X := [1,2,3]", spec("surface", "over x from 0 to 1", "across y from 0 to 1", "show X"))
    assert "over needs a vector (one row or one column)" in err(
        "Mx := [1, 2; 3, 4]", spec("surface", "over Mx", "across y from 0 to 1", "show y"))


def test_range_too_long_and_reading_order():
    assert "range has more than 100 values for a 3-D plot" in err(
        "t := 0 to 200 step 1", spec("surface", "over t", "across y from 0 to 1", "show y"))
    res = Engine().evaluate([(0, spec("surface", "over t", "across y from 0 to 1", "show y")),
                             (1, "t := 0 to 2 step 1")])
    assert res[0].status == "error" and "t is not defined" in res[0].error


def test_nonfinite_endpoint():
    msg = err(spec("surface", "over x from 0 to 1/0 points 3", "across y from 0 to 1", "show x"))
    assert "Sampling limits must be finite real numbers" in msg


def test_descending_samples():
    s = surf(base=["surface", "over x from 2 to 0 points 3", "across y from 0 to 2 points 3", "show x"])
    assert s.xs == [2, 1, 0] and s.x_limits == (0, 2)
