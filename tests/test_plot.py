"""Spec 004 phase A1: plot engine (criteria 1-20 and nice_axis)."""

import math
import time

import pytest

from livesheet.engine.evaluator import Engine
from livesheet.engine.plotting import nice_axis
from livesheet.engine.syntax import parse_statement

SHEET = ["v := 3 m/s", "t := 0 s to 10 s step 2 s"]


def run(*texts):
    """Evaluate texts in order; return the results as a list."""
    res = Engine().evaluate(list(enumerate(texts)))
    return [res[i] for i in range(len(texts))]


def plot(*lines, sheet=SHEET, spec_head="plot"):
    out = run(*sheet, "\n".join([spec_head, *lines]))[-1]
    return out


def close(a, b, tol=1e-9):
    assert len(a) == len(b), (a, b)
    for x, y in zip(a, b):
        if isinstance(y, float) and math.isnan(y):
            assert math.isnan(x)
        else:
            assert x == pytest.approx(y, abs=tol), (a, b)


def err(result, text):
    assert result.status == "error" and result.plot is None, result
    assert text in result.error, result.error


# 1
def test_basic_range_mode():
    res = run(*SHEET, "plot\nover t\nshow v*t")
    assert all(r.status == "ok" for r in res)
    r = res[-1]
    assert r.defines == "" and r.output == "plot 1 traces, 6 points"
    p = r.plot
    assert len(p.traces) == 1 and p.skipped == 0 and p.traces[0].style_index == 0
    close(p.traces[0].x, [0, 2, 4, 6, 8, 10])
    close(p.traces[0].y, [0, 6, 12, 18, 24, 30])
    assert (p.x_unit, p.y_unit) == ("s", "m")
    assert (p.x_label, p.y_label) == ("t [s]", "v*t [m]")
    assert p.x_limits == (0, 10) and p.y_limits == (0, 30)
    assert p.x_ticks == [0, 2, 4, 6, 8, 10]
    assert p.y_ticks == [0, 5, 10, 15, 20, 25, 30]


# 2
def test_display_units():
    p = plot("over t", "show v*t", "yunit mm", "xunit ms").plot
    close(p.traces[0].y, [0, 6000, 12000, 18000, 24000, 30000])
    close(p.traces[0].x, [0, 2000, 4000, 6000, 8000, 10000])
    assert (p.x_unit, p.y_unit) == ("ms", "mm")
    assert p.y_limits == (0, 30000) and p.y_ticks == [0, 5000, 10000, 15000, 20000, 25000, 30000]
    assert p.x_ticks == [0, 2000, 4000, 6000, 8000, 10000]
    assert (p.x_label, p.y_label) == ("t [ms]", "v*t [mm]")


# 3
def test_two_traces():
    r = plot("over t", "show v*t", "show 2*v*t")
    p = r.plot
    assert len(p.traces) == 2 and r.output == "plot 2 traces, 6 points"
    close(p.traces[1].y, [0, 12, 24, 36, 48, 60])
    assert p.traces[1].style_index == 1
    assert p.y_limits == (0, 60) and p.y_ticks == [0, 10, 20, 30, 40, 50, 60]
    assert p.y_label == "[m]"


# 4
def test_sampling_mode():
    res = run("plot\nover x from 0 to 6.283185307179586 points 5\nshow sin(x)", "x =")
    p = res[0].plot
    close(p.traces[0].x, [0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi], 1e-12)
    close(p.traces[0].y, [0, 1, 0, -1, 0], 1e-12)
    assert p.x_unit == "" and p.y_unit == "" and p.x_label == "x"
    assert p.y_limits == (-1, 1) and p.y_ticks == [-1, -0.5, 0, 0.5, 1]
    assert res[1].status == "error" and "not defined" in res[1].error
    default = run("plot\nover x from 0 to 1\nshow x")[0].plot
    assert len(default.traces[0].x) == 101


def test_sampling_shadows_sheet_name_and_has_units():
    p = run("x := 7", "plot\nover x from 0 m to 4 m points 3\nshow 2*x")[1].plot
    close(p.traces[0].x, [0, 2, 4])
    close(p.traces[0].y, [0, 4, 8])
    assert p.x_unit == "m" and p.y_unit == "m"
    desc = run("plot\nover x from 4 to 0 points 3\nshow x")[0].plot
    close(desc.traces[0].x, [4, 2, 0])
    assert desc.x_limits == (0, 4)


# 5
@pytest.mark.parametrize("x_def", ["X := [0, 1, 2, 3]", "X := [0; 1; 2; 3]"])
def test_vector_mode(x_def):
    sheet = [x_def, "Y := [0, 1, 4, 9]*m"]
    p = plot("over X", "show Y", sheet=sheet).plot
    close(p.traces[0].x, [0, 1, 2, 3])
    close(p.traces[0].y, [0, 1, 4, 9])
    assert p.y_unit == "m" and p.x_unit == ""
    assert p.x_limits == (0, 3) and p.x_ticks == [0, 0.5, 1, 1.5, 2, 2.5, 3]
    assert p.y_limits == (0, 10) and p.y_ticks == [0, 2, 4, 6, 8, 10]
    close(plot("over X", "show 2*Y", sheet=sheet).plot.traces[0].y, [0, 2, 8, 18])


# 6
def test_vector_units_both_axes():
    sheet = ["X := [0, 1, 2]*s", "Y := [0, 3, 6]*m"]
    p = plot("over X", "show Y", sheet=sheet).plot
    assert (p.x_unit, p.y_unit) == ("s", "m")
    close(plot("over X", "show Y", "xunit ms", sheet=sheet).plot.traces[0].x, [0, 1000, 2000])


# 7
def test_manual_limits():
    p = plot("over t", "show v*t", "xlim 2 s to 8 s", "ylim 0 m to 40 m").plot
    assert p.x_limits == (2, 8) and p.x_ticks == [2, 3, 4, 5, 6, 7, 8]
    assert p.y_limits == (0, 40) and p.y_ticks == [0, 5, 10, 15, 20, 25, 30, 35, 40]
    assert len(p.traces[0].x) == 6
    assert plot("over t", "show v*t", "xlim 2000 ms to 8 s").plot.x_limits == (2, 8)
    assert plot("over t", "show v*t", "xunit ms", "xlim 2 s to 8 s").plot.x_limits == (2000, 8000)


# 8
def test_half_automatic_limits():
    p = plot("over t", "show v*t", "xlim auto to 8 s").plot
    assert p.x_limits == (0, 8) and p.x_ticks == list(range(9))
    q = plot("over t", "show v*t", "ylim 5 m to auto").plot
    assert q.y_limits == (5, 30) and q.y_ticks == [5, 10, 15, 20, 25, 30]


# 9
def test_constant_trace():
    p = plot("over t", "show 5 m").plot
    close(p.y_limits, (4.4, 5.6))
    close(p.y_ticks, [4.4, 4.6, 4.8, 5.0, 5.2, 5.4, 5.6])
    z = plot("over t", "show 0 m").plot
    assert z.y_limits == (-1, 1) and z.y_ticks == [-1, -0.5, 0, 0.5, 1]


# 10
def test_nice_axis():
    assert nice_axis(0, 10) == (0, 10, [0, 2, 4, 6, 8, 10])
    assert nice_axis(0, 9) == (0, 10, [0, 2, 4, 6, 8, 10])
    assert nice_axis(0, 0.7) == (0, 0.7, [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    assert nice_axis(-3, 17) == (-5, 20, [-5, 0, 5, 10, 15, 20])
    assert nice_axis(1234, 1250) == (1234, 1250, list(range(1234, 1251, 2)))
    assert nice_axis(0, 30) == (0, 30, [0, 5, 10, 15, 20, 25, 30])
    with pytest.raises(ValueError):
        nice_axis(0, 1, 3, 3)


def test_nice_axis_extremes():
    for lo, hi in [(0, 1e9), (1e-9, 3e-9), (-1e9, 1e9), (5, 5)]:
        a, b, ticks = nice_axis(lo, hi)
        assert a <= lo <= hi <= b and 2 <= len(ticks) <= 12
    assert nice_axis(0, 0.7)[2][3] == 0.3  # 0.1 * 3 prints as 0.3


# 11
def test_undefined_points():
    p = run("plot\nover x from -2 to 2 points 5\nshow 1/x")[0].plot
    close(p.traces[0].x, [-2, -1, 0, 1, 2])
    close(p.traces[0].y, [-0.5, -1, float("nan"), 1, 0.5])
    assert p.skipped == 1 and p.y_limits == (-1, 1)
    q = run("plot\nover x from -2 to 2 points 5\nshow sqrt(x)")[0].plot
    assert q.skipped == 2 and math.isnan(q.traces[0].y[0]) and math.isnan(q.traces[0].y[1])


# 12
def test_live_update_and_reading_order():
    first = run(*SHEET, "plot\nover t\nshow v*t")[-1].plot
    second = run("v := 6 m/s", SHEET[1], "plot\nover t\nshow v*t")[-1].plot
    close(second.traces[0].y, [0, 12, 24, 36, 48, 60])
    assert second.y_limits == (0, 60)
    close(first.traces[0].y, [0, 6, 12, 18, 24, 30]) and first.y_limits == (0, 30)
    spec = "plot\nover t\nshow v*t"
    below = run(*SHEET, spec, "v := 6 m/s")[2].plot
    assert below.y_limits == (0, 30)
    glob = run(SHEET[1], spec, "v ≡ 6 m/s")[1].plot  # no local v above: the global below is visible
    assert glob.y_limits == (0, 60)


# 13
@pytest.mark.parametrize("lines,text", [
    ([], "over"),
    (["show v*t"], "over"),
    (["over t"], "show"),
    (["over t", "over t", "show v*t"], "only one 'over'"),
    (["over t", "show v*t", "colour red"], "Unknown plot option 'colour'"),
    (["over t"] + ["show v*t"] * 21, "too many traces (max 20)"),
    (["over t", "show v*t", "grid off"], "Unknown plot option 'grid'"),
    (["over t", "show v*t", "xscale log"], "Unknown plot option 'xscale'"),
])
def test_structure_errors(lines, text):
    err(plot(*lines), text)


def test_twenty_traces_ok():
    assert len(plot("over t", *["show v*t"] * 20).plot.traces) == 20


# 14
@pytest.mark.parametrize("over,text", [
    ("over q", "q is not defined"),
    ("over 5", "range variable or a vector"),
    ("over x from 0 to 1 points 1", "points must be between 2 and 10000"),
    ("over x from 0 to 1 points 10001", "points must be between 2 and 10000"),
    ("over x from 0 s to 1 m", "Units do not match"),
])
def test_over_errors(over, text):
    err(plot(over, "show 1"), text)


# 15
def test_shape_errors():
    sheet = SHEET + ["Y := [1, 2, 3]*m"]
    err(plot("over t", "show Y", sheet=sheet), "needs a single value")
    err(plot("over x from 0 to 1 points 3", "show Y", sheet=sheet), "needs a single value")
    vec = ["X := [0, 1, 2, 3]", "Y := [1, 2, 3]"]
    err(plot("over X", "show 5", sheet=vec), "needs a vector")
    err(plot("over X", "show Y", sheet=vec), "same length")


# 16
def test_unit_errors():
    err(plot("over t", "show v*t", "xunit kg"), "Units do not match")
    err(plot("over t", "show v*t", "yunit s"), "Units do not match")
    err(plot("over t", "show v*t", "show t"), "different units")
    err(plot("over t", "show v*t", "xlim 5 m to 10 m"), "Units do not match")
    err(plot("over x from 0 to 1", "show x", "xunit s"), "xunit given but x has no unit")
    err(plot("over x from 0 to 1", "show x", "yunit s"), "yunit given but y has no unit")
    err(plot("over t", "show v*t", "xlim 8 s to 2 s"), "lower limit must be below upper limit")
    err(plot("over t", "show v*t", "xlim 3 s to 3 s"), "lower limit must be below upper limit")


# 17
def test_nothing_to_draw():
    err(plot("over t", "show sqrt(-1) m"), "no finite values to plot")


# 18
def test_reading_order_error():
    res = run("plot\nover t\nshow v*t", *SHEET)
    assert res[0].status == "error" and "not defined" in res[0].error
    err(res[0], "is not defined")


# 19
def test_one_bad_trace_fails_everything():
    err(plot("over t", "show v*t", "show nonsense(t)"), "")
    r = plot("over t", "show v*t", "show 1 +")
    assert r.status == "error" and r.plot is None


# 20
def test_plot_name_still_usable():
    res = run("plot := 3", "plot =")
    assert res[1].output == "= 3"
    assert parse_statement("plot =").kind == "evaluate"
    assert parse_statement("plot := 3").kind == "define"
    assert parse_statement("plot").kind == "plot"
    assert parse_statement("\n  plot  \nover t").kind == "plot"


# edge cases
def test_single_value_range_and_descending():
    p = plot("over b", "show b", sheet=["b := 2 to 2"]).plot
    close(p.traces[0].x, [2]) and p.x_limits[0] < 2 < p.x_limits[1]
    d = plot("over r", "show r", sheet=["r := 10 to 0 step -5"]).plot
    close(d.traces[0].x, [10, 5, 0])
    assert d.x_limits == (0, 10)


def test_titles_labels_and_user_function():
    p = plot("over t", "show f(t)", "title Motion", "xlabel time", "ylabel path",
             sheet=SHEET + ["f(a) := 2*a*v"]).plot
    assert p.title == "Motion" and p.x_label == "time [s]" and p.y_label == "path [m]"
    close(p.traces[0].y, [0, 12, 24, 36, 48, 60])


def test_range_shared_with_table_and_unitless_quantities():
    res = run(*SHEET, "table t, v*t", "plot\nover t\nshow t/s")
    assert res[2].status == "ok" and res[3].plot.y_unit == ""


def test_blank_xunit_and_bad_limit_syntax():
    err(plot("over t", "show v*t", "xlim 3 s"), "xlim needs")
    err(plot("over t", "show v*t", "xunit s", "xunit s"), "only one 'xunit'")


def test_performance():
    start = time.perf_counter()
    p = run("plot\nover x from 0 to 10 points 1000\nshow sin(x)\nshow x^2 + cos(x)")[0].plot
    assert len(p.traces) == 2 and len(p.traces[0].x) == 1000
    assert time.perf_counter() - start < 1.0


def test_point_by_point_fallback(monkeypatch):
    from livesheet.engine import plotting

    def boom(self, value):
        raise RuntimeError("force fallback")

    monkeypatch.setattr(plotting._Builder, "_fast", boom)
    r = plot("over t", "show v*t", "show 0")
    p = r.plot
    close(p.traces[0].y, [0, 6, 12, 18, 24, 30])
    assert p.y_unit == "m" and p.skipped == 0
    err(plot("over t", "show v*t", "show t"), "different units")
