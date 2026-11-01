"""Spec 015 phase F1: 2D pin-jointed truss analysis (direct stiffness method).

Numbers come from the spec's own acceptance criteria (hand-derived there); independently
re-verified here against a standalone NumPy implementation of the direct stiffness method
before being used as test oracles (see the developer's handoff in docs/board/log.md).
Criterion numbers in comments refer to docs/board/specs/015-truss-fem.md.
"""

import re

import pytest

from livesheet.engine import Engine, StatementError, parse_statement


def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def cells(output: str) -> list[float]:
    """All numbers in a printed matrix/vector result, in row-major order."""
    text = output.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


BAR = [
    "coords := [0, 0; 2, 0] m",
    "members := [1, 2]",
    "nodes coords in bar",
    "elements members in bar",
    "area 0.0005 m^2 in bar",
    "modulus 200 GPa in bar",
    "support 1 fix x, y in bar",
    "support 2 fix y in bar",
]

BRACKET = [
    "coords := [0, 0; 4, 0; 2, 3] m",
    "members := [1, 3; 2, 3]",
    "nodes coords in bracket",
    "elements members in bracket",
    "area 0.0005 m^2 in bracket",
    "modulus 200 GPa in bracket",
    "support 1 fix x, y in bracket",
    "support 2 fix x, y in bracket",
    "load 3 fy -10000 N in bracket",
    "resolve in bracket",
]


# -- 1-2 single bar (minimal, axial only) ------------------------------------------------

def test_single_bar_tension():
    res = run(*BAR, "load 2 fx 1000 N in bar", "resolve in bar",
             "bar_displacement =", "bar_force =", "bar_stress =", "bar_reaction =")
    resolve = res[-5]
    assert resolve.status == "ok"
    assert resolve.output.startswith('⇒ resolved "bar": 2 nodes, 1 elements')
    disp, force, stress, reaction = res[-4], res[-3], res[-2], res[-1]
    assert cells(disp.output) == pytest.approx([0, 0, 2e-5, 0], abs=1e-9)
    assert cells(force.output) == pytest.approx([1000], abs=1e-2)
    assert cells(stress.output) == pytest.approx([2000000], abs=1e-2)
    assert cells(reaction.output) == pytest.approx([-1000, 0, 0, 0], abs=1e-2)


def test_single_bar_compression():
    res = run(*BAR, "load 2 fx -1000 N in bar", "resolve in bar",
             "bar_force =", "bar_displacement =", "bar_reaction =")
    force, disp, reaction = res[-3], res[-2], res[-1]
    assert cells(force.output) == pytest.approx([-1000], abs=1e-2)
    assert cells(disp.output) == pytest.approx([0, 0, -2e-5, 0], abs=1e-9)
    assert cells(reaction.output) == pytest.approx([1000, 0, 0, 0], abs=1e-2)


# -- 3 symmetric two-bar "A-frame" --------------------------------------------------------

def test_a_frame_statically_determinate():
    res = run(*BRACKET, "bracket_displacement =", "bracket_force =",
             "bracket_stress =", "bracket_reaction =")
    resolve = res[-5]
    assert resolve.status == "ok"
    assert "3 nodes, 2 elements" in resolve.output
    disp, force, stress, reaction = res[-4], res[-3], res[-2], res[-1]
    assert cells(disp.output) == pytest.approx([0, 0, 0, 0, 0, -2.60401e-4], abs=1e-9)
    assert cells(force.output) == pytest.approx([-6009.252125773315, -6009.252125773315], abs=1e-2)
    # the stress magnitude (~1.2e7 Pa) exceeds what 6 significant digits of printed text can
    # carry to an absolute 1e-2 Pa, so this one assertion uses a relative tolerance instead
    assert cells(stress.output) == pytest.approx([-12018504.25154663, -12018504.25154663], rel=1e-5)
    assert cells(reaction.output) == pytest.approx(
        [3333.333333, 5000, -3333.333333, 5000, 0, 0], abs=1e-2)


# -- 4 units ------------------------------------------------------------------------------

def test_units_target_conversion():
    res = run(*BRACKET, "bracket_displacement = mm", "bracket_force = kN", "bracket_stress = MPa")
    disp_mm, force_kn, stress_mpa = res[-3], res[-2], res[-1]
    assert cells(disp_mm.output) == pytest.approx([0, 0, 0, 0, 0, -0.260401], abs=1e-4)
    assert cells(force_kn.output) == pytest.approx([-6.00925, -6.00925], abs=1e-3)
    assert cells(stress_mpa.output) == pytest.approx([-12.0185, -12.0185], abs=1e-3)


# Criteria 5-9 each break exactly one field of an otherwise-valid, complete model: the unit
# check only runs when ``resolve`` builds the model (per the spec's own deferred-parse design,
# like ``model_ode``'s equation text), so each test must supply the rest of a valid model too.

def test_nodes_without_length_unit():
    res = last("nodes [0, 0; 1, 0] in bad1", "elements [1, 2] in bad1", "area 1 m^2 in bad1",
              "modulus 1 Pa in bad1", "resolve in bad1")
    assert res.error == "Units do not match: node coordinates must be a length"


def test_area_without_unit():
    res = last("nodes [0, 0; 1, 0] m in bad2", "elements [1, 2] in bad2", "area 5 in bad2",
              "modulus 1 Pa in bad2", "resolve in bad2")
    assert res.error == "Units do not match: cross-section area must be an area"


def test_area_wrong_dimension():
    res = last("nodes [0, 0; 1, 0] m in bad2", "elements [1, 2] in bad2", "area 5 m in bad2",
              "modulus 1 Pa in bad2", "resolve in bad2")
    assert res.error == "Units do not match: cross-section area must be an area"


def test_modulus_wrong_dimension():
    res = last("nodes [0, 0; 1, 0] m in bad3", "elements [1, 2] in bad3", "area 1 m^2 in bad3",
              "modulus 200 N in bad3", "resolve in bad3")
    assert res.error == "Units do not match: elastic modulus must be a pressure"


def test_load_wrong_dimension():
    res = last("nodes [0, 0; 1, 0] m in bad4", "elements [1, 2] in bad4", "area 1 m^2 in bad4",
              "modulus 1 Pa in bad4", "load 1 fx 5 m in bad4", "resolve in bad4")
    assert res.error == 'Units do not match: load "fx" must be a force'


def test_support_value_wrong_dimension():
    res = last("nodes [0, 0; 1, 0] m in bad5", "elements [1, 2] in bad5", "area 1 m^2 in bad5",
              "modulus 1 Pa in bad5", "support 1 fix x = 5 N in bad5", "resolve in bad5")
    assert res.error == 'Units do not match: support value for "x" must be a length'


# -- 10-11 missing / duplicate declarations ----------------------------------------------

def test_missing_nodes():
    res = last("elements [1, 2] in m1", "area 1 m^2 in m1", "modulus 1 Pa in m1", "resolve in m1")
    assert res.error == 'No node coordinates declared for truss model "m1"'


def test_missing_elements():
    res = last("nodes [0, 0; 1, 0] m in m2", "area 1 m^2 in m2", "modulus 1 Pa in m2", "resolve in m2")
    assert res.error == 'No element connectivity declared for truss model "m2"'


def test_missing_area():
    res = last("nodes [0, 0; 1, 0] m in m3", "elements [1, 2] in m3", "modulus 1 Pa in m3",
              "resolve in m3")
    assert res.error == 'No cross-section area declared for truss model "m3"'


def test_missing_modulus():
    res = last("nodes [0, 0; 1, 0] m in m4", "elements [1, 2] in m4", "area 1 m^2 in m4",
              "resolve in m4")
    assert res.error == 'No elastic modulus declared for truss model "m4"'


def test_duplicate_nodes():
    res = last("nodes [0, 0; 1, 0] m in m", "nodes [0, 0; 1, 0] m in m", "resolve in m")
    assert res.error == 'Node coordinates already declared for truss model "m"'


def test_duplicate_elements():
    res = last("elements [1, 2] in m", "elements [1, 2] in m", "resolve in m")
    assert res.error == 'Element connectivity already declared for truss model "m"'


def test_duplicate_area():
    res = last("area 1 m^2 in m", "area 1 m^2 in m", "resolve in m")
    assert res.error == 'Cross-section area already declared for truss model "m"'


def test_duplicate_modulus():
    res = last("modulus 1 Pa in m", "modulus 1 Pa in m", "resolve in m")
    assert res.error == 'Elastic modulus already declared for truss model "m"'


# -- 12-14 shape errors -------------------------------------------------------------------

def test_element_node_out_of_range():
    res = last("nodes [0, 0; 1, 0; 2, 0] m in n", "elements [1, 5] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "resolve in n")
    assert res.error == "Element 1: node 5 is out of range 1..3"


def test_element_zero_length():
    res = last("nodes [0, 0; 1, 0] m in n", "elements [1, 1] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "resolve in n")
    assert res.error == "Element 1 has zero length (nodes 1 and 1 coincide)"


def test_area_vector_wrong_count():
    res = last("nodes [0, 0; 1, 0; 2, 0] m in n", "elements [1, 2] in n",
              "area [1, 2, 3] m^2 in n", "modulus 1 Pa in n", "resolve in n")
    assert res.error == ("area has 3 values but there are 1 elements "
                         "(use one value or exactly one per element)")


def test_modulus_vector_wrong_count():
    res = last("nodes [0, 0; 1, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus [1, 2, 3] Pa in n", "resolve in n")
    assert res.error == ("modulus has 3 values but there are 1 elements "
                         "(use one value or exactly one per element)")


# -- 15-17 support / load errors -----------------------------------------------------------

def test_support_node_out_of_range():
    res = last("nodes [0, 0; 1, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "support 9 fix x in n", "resolve in n")
    assert res.error == "support references node 9, out of range 1..3"


def test_load_node_out_of_range():
    res = last("nodes [0, 0; 1, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "load 9 fx 5 N in n", "resolve in n")
    assert res.error == "load references node 9, out of range 1..3"


def test_support_same_axis_twice_one_line():
    res = last("nodes [0, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "support 1 fix x, x in n", "resolve in n")
    assert res.error == 'Node 1 has "x" fixed twice in truss model "n"'


def test_support_same_axis_twice_two_lines():
    res = last("nodes [0, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "support 1 fix x in n", "support 1 fix x in n",
              "resolve in n")
    assert res.error == 'Node 1 has "x" fixed twice in truss model "n"'


def test_load_same_node_two_lines():
    res = last(*BAR, "load 2 fx 5 N in bar", "load 2 fy 3 N in bar", "resolve in bar")
    assert res.error == 'Node 2 is loaded by more than one "load" line in truss model "bar"'


def test_load_same_node_one_line_both_axes_ok():
    res = last(*BAR, "load 2 fx 1000 N, fy 0 N in bar", "resolve in bar")
    assert res.status == "ok"


# -- 18 singular / unstable ----------------------------------------------------------------

def test_no_supports_is_singular():
    res = last("nodes [0, 0; 2, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "load 2 fx 5 N in n", "resolve in n")
    assert res.error == 'Stiffness matrix is singular: truss model "n" is unstable or underconstrained'


def test_unconnected_unsupported_node_is_singular():
    res = last("nodes [0, 0; 2, 0; 5, 5] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "support 1 fix x, y in n", "support 2 fix x, y in n",
              "resolve in n")
    assert res.error == 'Stiffness matrix is singular: truss model "n" is unstable or underconstrained'


# -- 19-20 resolve shape / reading order ----------------------------------------------------

def test_resolve_takes_no_expression():
    with pytest.raises(StatementError) as exc:
        parse_statement("resolve extra in n")
    assert str(exc.value) == "resolve takes no expression"


def test_no_result_region_below():
    res = run("nodes [0, 0; 1, 0] m in n", "elements [1, 2] in n")
    assert all(r.error == 'No result region for truss model "n" below this region' for r in res)


def test_region_below_resolve_not_used():
    res = run(*BAR, "load 2 fx 1000 N in bar", "resolve in bar", "load 1 fx 999 N in bar",
             "bar_force =")
    resolve, below, force = res[-3], res[-2], res[-1]
    assert resolve.status == "ok"
    assert below.error == 'No result region for truss model "bar" below this region'
    assert cells(force.output) == pytest.approx([1000], abs=1e-2)


# -- 21 isolation / compatibility ------------------------------------------------------------

def test_plain_variable_named_like_keywords_unaffected():
    res = run("nodes := 5", "nodes + 1 =", "load := 10 N", "load =", "area := 2 m^2", "area =")
    assert res[1].output == "= 6"
    assert res[3].output == "= 10 N"
    assert res[5].output == "= 2 m²"


def test_truss_and_solve_and_ode_models_independent():
    pytest.importorskip("scipy")
    res = run(
        "vary x from 1 in q", "x^2 == 4 in q", "settle in q",
        "ode diff(y(t), t) + y(t)/tau == 0 in decay", "tau := 4 s", "start y(0) == 10 m in decay",
        "evolve in decay",
        *BAR, "load 2 fx 1000 N in bar", "resolve in bar",
    )
    assert res[2].status == "ok"
    assert res[6].status == "ok"
    assert res[-1].status == "ok"


# -- 22 parsing ------------------------------------------------------------------------------

def test_parse_nodes():
    st = parse_statement("nodes coords in bracket")
    assert st.kind == "model_truss_nodes" and st.model == "bracket" and st.expr == "coords"


def test_parse_support():
    st = parse_statement("support 1 fix x, y = 2 mm in bracket")
    assert st.kind == "model_support"
    assert st.node == "1"
    assert st.axes == [("x", ""), ("y", "2 mm")]


def test_parse_load():
    st = parse_statement("load 3 fy -10000 N in bracket")
    assert st.kind == "model_load"
    assert st.node == "3"
    assert st.axes == [("y", "-10000 N")]


def test_parse_resolve():
    st = parse_statement("resolve in bracket")
    assert st.kind == "model_result" and st.model == "bracket" and st.goal == "truss"


# -- D1 (tester review 015): the ``support``-only guard exemption must stay scoped to the
# bare-``=`` check it was actually needed for, not the whole "looks like an ordinary
# statement" guard -- a plain variable called ``support`` must still fall back to ``define``
# exactly like every other model keyword does.

def test_support_keyword_still_falls_back_to_define():
    assert parse_statement("support := 5 in q").kind == "define"


def test_support_with_bare_equals_value_still_parses_as_model_support():
    st = parse_statement("support 1 fix x = 5 mm in bracket")
    assert st.kind == "model_support"
    assert st.node == "1"
    assert st.axes == [("x", "5 mm")]


# -- edge cases --------------------------------------------------------------------------

def test_support_prescribed_nonzero_displacement():
    res = run(*BAR, "support 2 fix x = 1 mm in bar", "resolve in bar", "bar_displacement =")
    resolve, disp = res[-2], res[-1]
    assert resolve.status == "ok"
    assert cells(disp.output)[2] == pytest.approx(1e-3, abs=1e-9)


def test_area_as_row_vector_matches_scalar():
    res_scalar = last(*BRACKET, "bracket_force =")
    res_vector = last(*BRACKET[:4], "area [0.0005, 0.0005] m^2 in bracket", *BRACKET[5:],
                      "bracket_force =")
    assert cells(res_scalar.output) == pytest.approx(cells(res_vector.output), abs=1e-6)


def test_undefined_symbol_in_nodes():
    res = last("nodes [0, 0; x, 0] m in n", "elements [1, 2] in n", "area 1 m^2 in n",
              "modulus 1 Pa in n", "resolve in n")
    assert "is not defined" in res.error
