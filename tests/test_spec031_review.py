"""Spec 031 phase A1: independent black-box review tests (engine side), written from the spec only."""

import math
import time

import pytest

from livesheet.engine import Engine

HDR = "surface\nover x from 0 to 2 points 3\nacross y from 0 to 2 points 3\n"


def ev(*srcs):
    return list(Engine().evaluate([(i, s) for i, s in enumerate(srcs)]).values())


def surf(*srcs):
    res = ev(*srcs)[-1]
    assert res.status == "ok", res.error
    return res.surface


def err(*srcs):
    res = ev(*srcs)[-1]
    assert res.status == "error"
    assert res.surface is None
    return res.error


def approx_list(a, b, tol=1e-9):
    assert len(a) == len(b)
    for p, q in zip(a, b):
        assert p == pytest.approx(q, abs=tol)


# ---------------------------------------------------------------- A1 acceptance

def test_a1_1_basic():
    res = ev(HDR + "show x + 2*y")[0]
    assert res.status == "ok" and not res.defines and res.output == "surface 3 x 3 points"
    s = res.surface
    assert s.xs == [0, 1, 2] and s.ys == [0, 1, 2]
    assert s.zs == [[0, 1, 2], [2, 3, 4], [4, 5, 6]]
    assert tuple(s.x_limits) == (0, 2) and s.x_ticks == [0, 0.5, 1, 1.5, 2]
    assert tuple(s.y_limits) == (0, 2) and s.y_ticks == [0, 0.5, 1, 1.5, 2]
    assert tuple(s.z_limits) == (0, 6) and s.z_ticks == [0, 1, 2, 3, 4, 5, 6]
    assert (s.x_unit, s.y_unit, s.z_unit) == ("", "", "")
    assert (s.draw, s.view_az, s.view_el, s.skipped, s.cells_drawn) == ("mesh", 40, 30, 0, 4)
    assert s.title == "" or isinstance(s.title, str)


def test_a1_2_units_display():
    s = surf("surface\nover x from 0 m to 2 m points 3\nacross y from 0 to 2 points 3\n"
             "show 500 N * (x/m) * y\nzunit kN")
    assert s.zs == [[0, 0, 0], [0, 0.5, 1], [0, 1, 2]]
    assert (s.x_unit, s.y_unit, s.z_unit) == ("m", "", "kN")
    assert tuple(s.z_limits) == (0, 2) and s.z_ticks == [0, 0.5, 1, 1.5, 2]
    assert (s.z_label, s.x_label, s.y_label) == ("500 N * (x/m) * y [kN]", "x [m]", "y")


def test_a1_3_range_axis():
    s = surf("t := 0 s to 2 s step 1 s", "surface\nover t\nacross y from 0 to 1 points 2\nshow t*y")
    assert s.xs == [0, 1, 2] and s.ys == [0, 1] and s.zs == [[0, 0, 0], [0, 1, 2]]
    assert (s.z_unit, s.x_unit) == ("s", "s")
    assert tuple(s.z_limits) == (0, 2) and s.z_ticks == [0, 0.5, 1, 1.5, 2]


def test_a1_4_defaults_and_caps():
    base = "surface\nover x from 0 to 1{}\nacross y from 0 to 1{}\nshow x + y"
    res = ev(base.format("", ""))[0]
    assert (len(res.surface.xs), len(res.surface.ys), res.output) == (25, 25, "surface 25 x 25 points")
    res = ev(base.format(" points 100", " points 100"))[0]
    assert res.status == "ok" and len(res.surface.zs) == 100 and len(res.surface.zs[0]) == 100
    assert "points must be between 2 and 100" in err(base.format(" points 101", ""))


def test_a1_5_manual_horizontal_limits():
    s = surf(HDR + "show x + 2*y\nxlim 0.5 to 1.5")
    assert tuple(s.x_limits) == (0.5, 1.5)
    approx_list(s.x_ticks, [0.6, 0.8, 1, 1.2, 1.4])
    s = surf(HDR + "show x + 2*y\nxlim 0 to 1.5")
    assert s.cells_drawn == 2 and s.zs == [[0, 1, 2], [2, 3, 4], [4, 5, 6]]
    assert surf(HDR + "show x + 2*y\nylim 0 to 1.5").cells_drawn == 2


def test_a1_6_manual_height_limit():
    s = surf(HDR + "show x + 2*y\nzlim 0 to 4")
    assert tuple(s.z_limits) == (0, 4)
    approx_list(s.z_ticks, [0, .5, 1, 1.5, 2, 2.5, 3, 3.5, 4])
    assert s.cells_drawn == 2


def test_a1_7_undefined_heights():
    res = ev("surface\nover x from -1 to 1 points 3\nacross y from 0 to 1 points 2\nshow 1/x")[0]
    assert res.status == "ok"
    s = res.surface
    assert s.xs == [-1, 0, 1] and s.ys == [0, 1]
    for row, want in zip(s.zs, ([-1, None, 1], [-1, None, 1])):
        assert row[0] == -1 and math.isnan(row[1]) and row[2] == 1
    assert s.skipped == 2 and s.cells_drawn == 0
    assert tuple(s.z_limits) == (-1, 1) and s.z_ticks == [-1, -0.5, 0, 0.5, 1]


def test_a1_8_constant_height():
    s = surf(HDR + "show 5 m + 0*x")
    approx_list(list(s.z_limits), [4.4, 5.6])
    approx_list(s.z_ticks, [4.4, 4.6, 4.8, 5.0, 5.2, 5.4, 5.6])
    assert s.z_unit == "m" and s.cells_drawn == 4


def test_a1_9_no_finite_height():
    res = ev("surface\nover x from 0 to 2 points 3\nacross y from 0 to 1 points 2\nshow sqrt(x - 10)")[0]
    assert res.status == "error" and "no finite values to plot" in res.error and res.surface is None


def test_a1_10_name_shadow_only_inside_plot():
    out = ev("x := 7", "surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x + y", "x =")
    assert out[1].surface.xs == [0, 1]
    assert out[2].output == "= 7"


@pytest.mark.parametrize("n", [25, 100])
def test_a1_11_parse_once(n):
    eng, calls = Engine(), []
    orig = eng.parse

    def counting(text, env, keep_units=False):
        calls.append(text)
        return orig(text, env, keep_units)
    eng.parse = counting
    src = f"surface\nover x from 0 to 1 points {n}\nacross y from 0 to 1 points {n}\nshow x*y + 3"
    assert eng.evaluate([(0, src)])[0].status == "ok"
    assert calls.count("x*y + 3") <= 2


@pytest.mark.parametrize("n,limit", [(25, 0.5), (100, 3.0)])
def test_a1_12_performance(n, limit):
    src = f"surface\nover x from 0 to 1 points {n}\nacross y from 0 to 1 points {n}\nshow x*y"
    t0 = time.perf_counter()
    assert Engine().evaluate([(0, src)])[0].status == "ok"
    assert time.perf_counter() - t0 < 2 * limit


def test_a1_13_regression_names():
    assert ev("plot := 3", "plot =")[1].output == "= 3"
    assert ev("surface := 3", "surface =")[1].output == "= 3"


def test_a1_14_two_d_grammar_unaffected():
    assert "Unknown plot option 'across'" in ev("plot\nover x from 0 to 1\nacross y\nshow x")[0].error


def test_two_d_plot_still_works():
    res = ev("plot\nover x from 0 to 2 points 3\nshow x^2")[0]
    assert res.status == "ok" and res.surface is None and res.plot is not None


# ---------------------------------------------------------------- header recognition

@pytest.mark.parametrize("head", ["plot3d", "Surface", "surface x", "surf", "3dplot"])
def test_not_a_surface_header(head):
    res = ev(head + "\nover x from 0 to 1 points 3\nacross y from 0 to 1 points 3\nshow x+y")[0]
    assert res.surface is None
    assert res.status == "error"


def test_header_with_surrounding_blanks_ok():
    res = ev("  surface  \n\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y")[0]
    assert res.status == "ok" and res.surface is not None


def test_surface_defines_nothing_and_is_not_a_plot():
    res = ev(HDR + "show x")[0]
    assert res.defines == [] or not res.defines
    assert res.plot is None


# ---------------------------------------------------------------- errors E1..E12

@pytest.mark.parametrize("text,msg", [
    ("surface\nacross y from 0 to 1 points 2\nshow y", "surface needs an 'over' line"),
    ("surface\nover x from 0 to 1 points 2\nshow x", "surface needs an 'across' line"),
    ("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2", "surface needs a 'show' line"),
    (HDR + "show x\nshow y", "surface takes exactly one 'show' line"),
    (HDR + "over z from 0 to 1 points 2\nshow x", "only one 'over' line is allowed"),
    ("surface\nover x from 0 to 1 points 2\nacross x from 0 to 1 points 2\nshow x",
     "over and across need different names"),
    (HDR + "show x\ncolour red", "Unknown 3-D plot option 'colour'"),
    (HDR + "show x\nplot3d on", "Unknown 3-D plot option 'plot3d'"),
    ("surface\nover x from 0 to 1 points 1\nacross y from 0 to 1 points 2\nshow x", "points must be between 2 and 100"),
    ("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 101\nshow x",
     "points must be between 2 and 100"),
    ("surface\nover x from 0 to 1 points 101\nacross y from 0 to 1 points 2\nshow x",
     "points must be between 2 and 100"),
    (HDR + "show x\ndraw dots", "draw must be mesh or wire"),
    (HDR + "show x\nview 40 95", "elevation must be between -90 and 90"),
    (HDR + "show x\nview 40 -95", "elevation must be between -90 and 90"),
    (HDR + "show x\nview 40", "view needs two numbers: azimuth and elevation"),
    (HDR + "show x\nview 40 m", "view needs two plain numbers"),
    (HDR + "show 1 s*x\nzunit kg", "Units do not match"),
    (HDR + "show x\nzunit s", "zunit given but z has no unit"),
    (HDR + "show x\nxlim 2 to 1", "lower limit must be below upper limit"),
    ("surface\nover q\nacross y from 0 to 1 points 2\nshow y", "q is not defined"),
    ("surface\nover x from 0 to 1/0 points 3\nacross y from 0 to 1 points 2\nshow x",
     "Sampling limits must be finite real numbers"),
])
def test_error_cases(text, msg):
    assert msg in err(text)


def test_e7_xlim_unit_mismatch():
    text = ("surface\nover t\nacross y from 0 to 1 points 2\nshow t*y\nxlim 5 m to 10 m")
    assert "Units do not match" in err("t := 0 s to 2 s step 1 s", text)


def test_e4_range_too_long():
    assert "range has more than 100 values for a 3-D plot" in err(
        "t := 0 to 200 step 1", "surface\nover t\nacross y from 0 to 1 points 2\nshow y")


def test_e8_shape():
    assert "show 'X' needs a single value" in err(
        "X := [1,2,3]", "surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow X")
    assert "over needs a vector (one row or one column)" in err(
        "M := [1,2;3,4]", "surface\nover M\nacross y from 0 to 1 points 2\nshow y")


def test_e10_reading_order():
    res = ev("surface\nover t\nacross y from 0 to 1 points 2\nshow t*y", "t := 0 to 2 step 1")[0]
    assert res.status == "error" and res.surface is None and "t is not defined" in res.error


def test_e12_nothing_raises():
    for bad in ["surface\nover", "surface\nover x from\nacross y\nshow", "surface\nshow ((", "surface\n\x00",
                "surface\nover x from a to b points z\nacross y from 0 to 1\nshow x",
                "surface\nover x from 0 to 1 points 2.5\nacross y from 0 to 1\nshow x",
                "surface\nover x from 0 to 1 points -3\nacross y from 0 to 1\nshow x",
                "surface\nover é from 0 to 1\nacross θ from 0 to 1\nshow é*θ"]:
        res = ev(bad)[0]
        assert res.status in ("ok", "error")


def test_empty_bare_keywords_is_error_not_exception():
    res = ev("surface\nover \nacross \nshow ")[0]
    assert res.status == "error" and res.surface is None


# ---------------------------------------------------------------- units and axes

def test_vector_axes_row_and_column_with_units():
    s = surf("v := [1 m, 2 m, 3 m]", "w := [10; 20]", "surface\nover v\nacross w\nshow v/m*w")
    assert s.xs == [1, 2, 3] and s.ys == [10, 20] and s.x_unit == "m"
    assert s.zs == [[10, 20, 30], [20, 40, 60]]


def test_user_function_of_two_args():
    s = surf("f(a,b) := a - b", "surface\nover x from 0 to 2 points 3\nacross y from 0 to 1 points 2\nshow f(x,y)")
    assert s.zs == [[0, 1, 2], [-1, 0, 1]]
    assert "Wrong number of arguments" in err(
        "f(a,b) := a - b", "surface\nover x from 0 to 2 points 3\nacross y from 0 to 1 points 2\nshow f(x)")


def test_display_units_on_horizontal_axes():
    s = surf("surface\nover x from 0 m to 1 m points 2\nacross y from 0 s to 1 s points 2\nshow x*y/m/s\n"
             "xunit cm\nyunit ms")
    assert s.xs == [0, 100] and s.ys == [0, 1000]
    assert (s.x_unit, s.y_unit) == ("cm", "ms")
    assert s.x_label == "x [cm]" and s.y_label == "y [ms]"


def test_xunit_on_dimensionless_rejected():
    assert "xunit given but x has no unit" in err(HDR + "show x\nxunit m")


def test_manual_limit_in_other_unit():
    s = surf("surface\nover x from 0 m to 1 m points 3\nacross y from 0 to 1 points 2\nshow x/m\n"
             "xunit cm\nxlim 0 cm to 50 cm")
    assert tuple(s.x_limits) == (0, 50)
    assert s.cells_drawn == 1    # only the cell between 0 and 50 cm


def test_labels_and_title():
    s = surf(HDR + "show x\ntitle Hello there\nxlabel A\nylabel B\nzlabel C")
    assert (s.title, s.x_label, s.y_label, s.z_label) == ("Hello there", "A", "B", "C")


def test_default_zlabel_is_expression_text():
    assert surf(HDR + "show x*y").z_label == "x*y"


def test_view_and_draw_options():
    s = surf(HDR + "show x\ndraw wire\nview -30 -90")
    assert (s.draw, s.view_az, s.view_el) == ("wire", -30, -90)
    s = surf(HDR + "show x\nview 720 90")
    assert (s.view_az, s.view_el) == (720, 90) or s.view_el == 90


def test_view_twice_rejected():
    assert "only one" in err(HDR + "show x\nview 0 0\nview 1 1")


def test_auto_limit_sides():
    s = surf(HDR + "show x\nzlim auto to 0.5")
    assert s.z_limits[1] == 0.5 and s.z_limits[0] <= 0
    s = surf(HDR + "show x\nxlim auto to auto")
    assert tuple(s.x_limits) == (0, 2)


def test_descending_samples():
    s = surf("surface\nover x from 2 to 0 points 3\nacross y from 0 to 1 points 2\nshow x")
    assert s.xs == [2, 1, 0] and tuple(s.x_limits) == (0, 2)
    assert s.zs[0] == [2, 1, 0] and s.cells_drawn == 2


def test_two_points_one_cell():
    s = surf("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x*y")
    assert s.cells_drawn == 1 and s.zs == [[0, 0], [0, 1]]


def test_complex_height_counts_as_skipped():
    res = ev("surface\nover x from 0 to 1 points 2\nacross y from 0 to 1 points 2\nshow x + sqrt(-1)*y")[0]
    if res.status == "ok":
        assert res.surface.skipped >= 2
        assert math.isnan(res.surface.zs[1][0])


def test_extreme_magnitudes():
    s = surf("surface\nover x from 0 to 1e9 points 3\nacross y from 0 to 1e-9 points 2\nshow x*y")
    assert s.x_ticks[-1] == pytest.approx(1e9) and s.y_ticks[-1] == pytest.approx(1e-9)
    assert s.zs[1][2] == pytest.approx(1.0)


def test_z_closed_form_cross_check():
    s = surf("surface\nover x from -1 to 1 points 5\nacross y from -2 to 2 points 7\nshow x^2 - y^2/4 + sin(x*y)")
    for j, y in enumerate(s.ys):
        for i, x in enumerate(s.xs):
            assert s.zs[j][i] == pytest.approx(x * x - y * y / 4 + math.sin(x * y), abs=1e-9)


def test_fast_and_slow_path_agree():
    # a height using an operation that may defeat a compiled fast path: Piecewise / abs / floor
    s = surf("surface\nover x from -2 to 2 points 5\nacross y from -1 to 1 points 3\nshow abs(x) + floor(y)")
    for j, y in enumerate(s.ys):
        for i, x in enumerate(s.xs):
            assert s.zs[j][i] == pytest.approx(abs(x) + math.floor(y), abs=1e-9)


def test_cells_drawn_counts_manual_limit_inclusive():
    # zlim 0 to 3 on x+2y over 3x3: cells with max corner <= 3 -> only cell (0,0) has corners 0,1,2,3
    s = surf(HDR + "show x + 2*y\nzlim 0 to 3")
    assert s.cells_drawn == 1


def test_recompute_on_change_above():
    a = ev("a := 2", "surface\nover x from 0 to a points 3\nacross y from 0 to 1 points 2\nshow x")[1].surface
    b = ev("a := 4", "surface\nover x from 0 to a points 3\nacross y from 0 to 1 points 2\nshow x")[1].surface
    assert a.xs == [0, 1, 2] and b.xs == [0, 2, 4]
