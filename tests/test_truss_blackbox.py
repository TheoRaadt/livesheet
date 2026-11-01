"""Independent black-box tests for spec 015 (FEM phase F1: 2D pin-jointed truss analysis).

Written from docs/board/specs/015-truss-fem.md's own acceptance criteria and edge cases,
using only the public Engine().evaluate()/parse_statement() surface -- never
livesheet/engine/truss.py's internals, and never tests/test_truss.py (the developer's own
test file), which was deliberately not read before writing this file.

The spec's own two worked numeric examples (single bar; symmetric two-bar "A-frame") are
hand-derived in the spec text and explicitly NOT run through any tool while writing the
spec. This file re-derives both independently with a standalone NumPy direct-stiffness
implementation (``_numpy_truss`` below, using ``numpy.linalg.solve`` directly -- an
already-approved dependency used only as a calculator here, never imported by LiveSheet's
own production code) before trusting them as test oracles, rather than relying on the
spec's quoted decimals, the developer's own already-claimed NumPy cross-check, or the
manager's acceptance of it.

Criterion numbers in comments refer to the spec's "Acceptance criteria" section.
"""

from __future__ import annotations

import math
import re

import numpy as np
import pytest

from livesheet.engine import Engine, parse_statement


# -- independent oracle: a standalone direct-stiffness solver, not LiveSheet's own ------

def _numpy_truss(coords, elements, area, modulus, supports, loads):
    """coords: list[(x,y)]; elements: list[(i,j)] 0-based; area/modulus: per-element lists;
    supports/loads: dict[(0-based node, 'x'|'y')] -> prescribed value. Returns
    (displacement Nx2, reaction Nx2, force M, stress M) as plain NumPy arrays."""
    n = len(coords)
    ndof = 2 * n
    k_global = np.zeros((ndof, ndof))
    geometry = []
    for idx, (i, j) in enumerate(elements):
        xi, yi = coords[i]
        xj, yj = coords[j]
        dx, dy = xj - xi, yj - yi
        length = math.hypot(dx, dy)
        c, s = dx / length, dy / length
        area_k, mod_k = area[idx], modulus[idx]
        k = mod_k * area_k / length
        k_local = k * np.array([
            [c * c, c * s, -c * c, -c * s],
            [c * s, s * s, -c * s, -s * s],
            [-c * c, -c * s, c * c, c * s],
            [-c * s, -s * s, c * s, s * s],
        ])
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        for a in range(4):
            for b in range(4):
                k_global[dofs[a], dofs[b]] += k_local[a, b]
        geometry.append((i, j, area_k, mod_k, length, c, s))

    force = np.zeros(ndof)
    for (node, axis), val in loads.items():
        force[2 * node + (0 if axis == "x" else 1)] += val
    prescribed = {}
    for (node, axis), val in supports.items():
        prescribed[2 * node + (0 if axis == "x" else 1)] = val
    free = [d for d in range(ndof) if d not in prescribed]
    pres = sorted(prescribed)
    k_ff = k_global[np.ix_(free, free)]
    k_fp = k_global[np.ix_(free, pres)]
    u_p = np.array([prescribed[d] for d in pres])
    f_f = force[free] - (k_fp @ u_p if pres else 0.0)
    u_f = np.linalg.solve(k_ff, f_f) if free else np.array([])

    u = np.zeros(ndof)
    for d, v in zip(free, u_f):
        u[d] = v
    for d in pres:
        u[d] = prescribed[d]
    reaction = k_global @ u - force

    forces, stresses = [], []
    for (i, j, area_k, mod_k, length, c, s) in geometry:
        elongation = (u[2 * j] - u[2 * i]) * c + (u[2 * j + 1] - u[2 * i + 1]) * s
        axial = mod_k * area_k / length * elongation
        forces.append(axial)
        stresses.append(axial / area_k)
    return u.reshape(n, 2), reaction.reshape(n, 2), np.array(forces), np.array(stresses)


def test_oracle_single_bar_matches_hand_derivation():
    """Criterion 1's numbers, independently re-derived via numpy.linalg.solve directly."""
    u, r, f, s = _numpy_truss(
        coords=[(0.0, 0.0), (2.0, 0.0)], elements=[(0, 1)],
        area=[0.0005], modulus=[200e9],
        supports={(0, "x"): 0.0, (0, "y"): 0.0, (1, "y"): 0.0},
        loads={(1, "x"): 1000.0},
    )
    assert u.flatten().tolist() == pytest.approx([0, 0, 2e-5, 0], abs=1e-9)
    assert f == pytest.approx([1000], abs=1e-6)
    assert s == pytest.approx([2_000_000], abs=1e-3)
    assert r.flatten().tolist() == pytest.approx([-1000, 0, 0, 0], abs=1e-9)


def test_oracle_a_frame_matches_hand_derivation():
    """Criterion 3's numbers, independently re-derived via numpy.linalg.solve directly,
    cross-checked against the spec's own closed-form method-of-joints formulas too."""
    u, r, f, s = _numpy_truss(
        coords=[(0.0, 0.0), (4.0, 0.0), (2.0, 3.0)], elements=[(0, 2), (1, 2)],
        area=[0.0005, 0.0005], modulus=[200e9, 200e9],
        supports={(0, "x"): 0.0, (0, "y"): 0.0, (1, "x"): 0.0, (1, "y"): 0.0},
        loads={(2, "y"): -10000.0},
    )
    f_closed = -math.sqrt(13) / 6 * 10000
    uy3_closed = -13 * math.sqrt(13) * 10000 / (18 * 200e9 * 0.0005)
    assert f == pytest.approx([f_closed, f_closed], abs=1e-6)
    assert u[2, 1] == pytest.approx(uy3_closed, abs=1e-9)
    assert u[2, 0] == pytest.approx(0.0, abs=1e-12)        # symmetry: node 3 ux exactly 0
    assert s == pytest.approx([f_closed / 0.0005, f_closed / 0.0005], abs=1e-3)
    assert r.flatten().tolist() == pytest.approx([3333.33, 5000, -3333.33, 5000, 0, 0], abs=1e-2)
    # the spec's own quoted decimals, now confirmed by an independent route, not just copied
    assert f == pytest.approx([-6009.25, -6009.25], abs=1e-2)
    assert u[2, 1] == pytest.approx(-0.000260401, abs=1e-9)


# -- harness --------------------------------------------------------------------------

def run(*sources):
    res = Engine().evaluate(enumerate(sources))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


_NUM_RE = re.compile(r"-?\d+\.?\d*(?:e-?\d+)?")


def numbers(output: str) -> list[float]:
    """All numbers in a printed matrix/vector result, independent small parser (own
    implementation, not reusing the developer's own helper)."""
    text = output.replace("×10", "e").translate(str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789"))
    return [float(m) for m in _NUM_RE.findall(text)]


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
]


# -- 1-2 single bar -----------------------------------------------------------------------

def test_criterion1_single_bar_tension():
    res = run(*BAR, "load 2 fx 1000 N in bar", "resolve in bar",
              "bar_displacement =", "bar_force =", "bar_stress =", "bar_reaction =")
    resolve = res[-5]
    assert resolve.status == "ok"
    assert resolve.output.startswith('⇒ resolved "bar": 2 nodes, 1 elements')
    assert numbers(res[-4].output) == pytest.approx([0, 0, 2e-5, 0], abs=1e-6)
    assert numbers(res[-3].output) == pytest.approx([1000], abs=1e-2)
    assert numbers(res[-2].output) == pytest.approx([2_000_000], abs=1e-2)
    # node 1's x-reaction balances the load; node 2's x-row (a free dof) is ~0
    reac = numbers(res[-1].output)
    assert reac[0] == pytest.approx(-1000, abs=1e-2)
    assert reac[1:] == pytest.approx([0, 0, 0], abs=1e-6)


def test_criterion2_single_bar_compression():
    res = run(*BAR, "load 2 fx -1000 N in bar", "resolve in bar",
              "bar_force =", "bar_displacement =", "bar_reaction =")
    assert numbers(res[-3].output) == pytest.approx([-1000], abs=1e-2)
    assert numbers(res[-2].output) == pytest.approx([0, 0, -2e-5, 0], abs=1e-6)
    reac = numbers(res[-1].output)
    assert reac[0] == pytest.approx(1000, abs=1e-2)
    assert reac[1:] == pytest.approx([0, 0, 0], abs=1e-6)


# -- 3 symmetric two-bar "A-frame" ---------------------------------------------------------

def test_criterion3_a_frame():
    res = run(*BRACKET, "resolve in bracket", "bracket_displacement =", "bracket_force =",
              "bracket_stress =", "bracket_reaction =")
    resolve = res[-5]
    assert resolve.status == "ok"
    assert "3 nodes, 2 elements" in resolve.output
    disp = numbers(res[-4].output)
    assert disp[:4] == pytest.approx([0, 0, 0, 0], abs=1e-9)
    assert disp[4] == pytest.approx(0.0, abs=1e-9)
    assert disp[5] == pytest.approx(-0.000260401, abs=1e-9)
    assert numbers(res[-3].output) == pytest.approx([-6009.25, -6009.25], rel=1e-5)
    assert numbers(res[-2].output) == pytest.approx([-12018500, -12018500], rel=1e-5)
    assert numbers(res[-1].output) == pytest.approx([3333.33, 5000, -3333.33, 5000, 0, 0], abs=1e-1)


# -- 4 units ------------------------------------------------------------------------------

def test_criterion4_target_unit_conversion():
    res = run(*BRACKET, "resolve in bracket", "bracket_displacement = mm",
              "bracket_force = kN", "bracket_stress = MPa")
    assert numbers(res[-3].output)[-1] == pytest.approx(-0.260401, abs=1e-6)
    assert numbers(res[-2].output) == pytest.approx([-6.00925, -6.00925], rel=1e-5)
    assert numbers(res[-1].output) == pytest.approx([-12.0185, -12.0185], rel=1e-5)


# -- 5-9 unit-mismatch errors (full otherwise-valid model + resolve, since the build()/
#    dimension checks only run at resolve time -- the bare one-line reading of criterion 5
#    would instead hit criterion 20's "no result region" error first; see Coverage notes) --

def test_criterion5_nodes_missing_length_unit():
    res = last("members := [1, 2]", "nodes [0, 0; 1, 0] in bad1", "elements members in bad1",
               "area 0.0005 m^2 in bad1", "modulus 200 GPa in bad1",
               "support 1 fix x, y in bad1", "support 2 fix y in bad1", "resolve in bad1")
    assert res.error == "Units do not match: node coordinates must be a length"


def _otherwise_valid(tag: str, *, override_line: str) -> list[str]:
    lines = [
        "coords := [0, 0; 1, 0] m", "members := [1, 2]",
        f"nodes coords in {tag}", f"elements members in {tag}",
        f"area 0.0005 m^2 in {tag}", f"modulus 200 GPa in {tag}",
        f"support 1 fix x, y in {tag}", f"support 2 fix y in {tag}",
        f"resolve in {tag}",
    ]
    key = override_line.split()[0]
    return [ln for ln in lines if not ln.startswith(f"{key} ")] + [override_line]


def test_criterion6_area_missing_unit():
    res = last(*_otherwise_valid("bad2", override_line="area 5 in bad2"), "resolve in bad2")
    assert res.error == "Units do not match: cross-section area must be an area"


def test_criterion6_area_wrong_dimension():
    res = last(*_otherwise_valid("bad2b", override_line="area 5 m in bad2b"), "resolve in bad2b")
    assert res.error == "Units do not match: cross-section area must be an area"


def test_criterion7_modulus_wrong_dimension():
    res = last(*_otherwise_valid("bad3", override_line="modulus 200 N in bad3"), "resolve in bad3")
    assert res.error == "Units do not match: elastic modulus must be a pressure"


def test_criterion8_load_wrong_dimension():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in bad4",
               "elements members in bad4", "area 0.0005 m^2 in bad4", "modulus 200 GPa in bad4",
               "support 1 fix x, y in bad4", "support 2 fix y in bad4",
               "load 1 fx 5 m in bad4", "resolve in bad4")
    assert res.error == 'Units do not match: load "fx" must be a force'


def test_criterion9_support_value_wrong_dimension():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in bad5",
               "elements members in bad5", "area 0.0005 m^2 in bad5", "modulus 200 GPa in bad5",
               "support 1 fix x = 5 N in bad5", "support 2 fix y in bad5", "resolve in bad5")
    assert res.error == 'Units do not match: support value for "x" must be a length'


# -- 10-11 missing / duplicate declarations ------------------------------------------------

def test_criterion10_missing_declarations():
    assert last("members := [1, 2]", "elements members in m10a", "area 0.0005 m^2 in m10a",
               "modulus 200 GPa in m10a", "support 1 fix x, y in m10a", "support 2 fix y in m10a",
               "resolve in m10a").error == 'No node coordinates declared for truss model "m10a"'
    assert last("coords := [0, 0; 1, 0] m", "nodes coords in m10b", "area 0.0005 m^2 in m10b",
               "modulus 200 GPa in m10b", "support 1 fix x, y in m10b", "support 2 fix y in m10b",
               "resolve in m10b").error == 'No element connectivity declared for truss model "m10b"'
    assert last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m10c",
               "elements members in m10c", "modulus 200 GPa in m10c",
               "support 1 fix x, y in m10c", "support 2 fix y in m10c",
               "resolve in m10c").error == 'No cross-section area declared for truss model "m10c"'
    assert last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m10d",
               "elements members in m10d", "area 0.0005 m^2 in m10d",
               "support 1 fix x, y in m10d", "support 2 fix y in m10d",
               "resolve in m10d").error == 'No elastic modulus declared for truss model "m10d"'


def test_criterion11_duplicate_declarations():
    full = BAR
    assert last(*full, "nodes coords in bar", "resolve in bar").error == \
        'Node coordinates already declared for truss model "bar"'
    assert last(*full, "elements members in bar", "resolve in bar").error == \
        'Element connectivity already declared for truss model "bar"'
    assert last(*full, "area 1 m^2 in bar", "resolve in bar").error == \
        'Cross-section area already declared for truss model "bar"'
    assert last(*full, "modulus 1 GPa in bar", "resolve in bar").error == \
        'Elastic modulus already declared for truss model "bar"'


# -- 12-13 element shape errors -------------------------------------------------------------

def test_criterion12_element_node_out_of_range():
    res = last("coords := [0, 0; 1, 0; 2, 0] m", "bad_members := [1, 5]",
               "nodes coords in m12", "elements bad_members in m12", "area 0.0005 m^2 in m12",
               "modulus 200 GPa in m12", "support 1 fix x, y in m12", "resolve in m12")
    assert res.error == "Element 1: node 5 is out of range 1..3"


def test_criterion13_zero_length_literal_same_index():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 1]", "nodes coords in m13",
               "elements members in m13", "area 0.0005 m^2 in m13", "modulus 200 GPa in m13",
               "support 1 fix x, y in m13", "resolve in m13")
    assert res.error == "Element 1 has zero length (nodes 1 and 1 coincide)"


def test_criterion13_zero_length_different_indices_same_coordinates():
    """Developer implemented this more broadly than the spec's one literal example: two
    *different* node indices that happen to sit at the same coordinates must also error."""
    res = last("coords := [0, 0; 0, 0; 1, 1] m", "members := [1, 2]", "nodes coords in m13b",
               "elements members in m13b", "area 0.0005 m^2 in m13b", "modulus 200 GPa in m13b",
               "support 1 fix x, y in m13b", "resolve in m13b")
    assert res.error == "Element 1 has zero length (nodes 1 and 2 coincide)"


def test_criterion13_no_false_positive_on_tiny_but_nonzero_element():
    """A genuinely short (not zero) element must resolve, not be rejected."""
    res = last("coords := [0, 0; 1e-6, 0] m", "members := [1, 2]", "nodes coords in m13c",
               "elements members in m13c", "area 0.0005 m^2 in m13c", "modulus 200 GPa in m13c",
               "support 1 fix x, y in m13c", "support 2 fix y in m13c", "resolve in m13c")
    assert res.status == "ok"


def test_criterion13_no_false_positive_on_coincident_but_unconnected_nodes():
    """Two nodes that happen to share coordinates, but are never endpoints of the *same*
    element, must not trigger the zero-length check (it is per-element, not per-node-pair).
    Modelled here as two independent bars sharing one coincident corner."""
    res = last(
        "coords := [0, 0; 2, 0; 0, 0; 2, 0] m", "members := [1, 2; 3, 4]",
        "nodes coords in m13e", "elements members in m13e", "area 0.0005 m^2 in m13e",
        "modulus 200 GPa in m13e",
        "support 1 fix x, y in m13e", "support 2 fix y in m13e",
        "support 3 fix x, y in m13e", "support 4 fix y in m13e",
        "load 2 fx 1000 N in m13e", "load 4 fx 1000 N in m13e", "resolve in m13e",
    )
    assert res.status == "ok"
    assert "4 nodes, 2 elements" in res.output


# -- 14 area/modulus count mismatch --------------------------------------------------------

def test_criterion14_area_and_modulus_count_mismatch():
    res = last("coords := [0, 0; 1, 0; 2, 0] m", "members := [1, 2]", "nodes coords in m14",
               "elements members in m14", "area [1, 2, 3] m^2 in m14", "modulus 200 GPa in m14",
               "support 1 fix x, y in m14", "resolve in m14")
    assert res.error == ("area has 3 values but there are 1 elements "
                          "(use one value or exactly one per element)")
    res2 = last("coords := [0, 0; 1, 0; 2, 0] m", "members := [1, 2]", "nodes coords in m14b",
               "elements members in m14b", "area 1 m^2 in m14b", "modulus [1, 2, 3] GPa in m14b",
               "support 1 fix x, y in m14b", "resolve in m14b")
    assert res2.error == ("modulus has 3 values but there are 1 elements "
                           "(use one value or exactly one per element)")


# -- 15 support/load out-of-range node ------------------------------------------------------

def test_criterion15_support_and_load_node_out_of_range():
    res = last(*BAR, "support 9 fix x in bar", "resolve in bar")
    assert res.error == "support references node 9, out of range 1..2"
    res2 = last(*BAR, "load 9 fx 5 N in bar", "resolve in bar")
    assert res2.error == "load references node 9, out of range 1..2"


# -- 16 duplicate node/axis fix --------------------------------------------------------------

def test_criterion16_duplicate_fix_same_line():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m16",
               "elements members in m16", "area 0.0005 m^2 in m16", "modulus 200 GPa in m16",
               "support 1 fix x, x in m16", "resolve in m16")
    assert res.error == 'Node 1 has "x" fixed twice in truss model "m16"'


def test_criterion16_duplicate_fix_two_lines():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m16b",
               "elements members in m16b", "area 0.0005 m^2 in m16b", "modulus 200 GPa in m16b",
               "support 1 fix x in m16b", "support 1 fix x in m16b", "resolve in m16b")
    assert res.error == 'Node 1 has "x" fixed twice in truss model "m16b"'


# -- 17 duplicate load on one node -----------------------------------------------------------

def test_criterion17_duplicate_load_two_lines():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m17",
               "elements members in m17", "area 0.0005 m^2 in m17", "modulus 200 GPa in m17",
               "support 1 fix x, y in m17", "support 2 fix y in m17",
               "load 1 fx 5 N in m17", "load 1 fy 3 N in m17", "resolve in m17")
    assert res.error == 'Node 1 is loaded by more than one "load" line in truss model "m17"'


def test_combined_fx_fy_one_load_line_is_not_a_duplicate():
    """The same node may legally receive both fx and fy on a *single* load line."""
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m17b",
               "elements members in m17b", "area 0.0005 m^2 in m17b", "modulus 200 GPa in m17b",
               "support 1 fix x, y in m17b", "support 2 fix y in m17b",
               "load 2 fx 5 N, fy 3 N in m17b", "resolve in m17b")
    assert res.status == "ok"


# -- 18 singular system -----------------------------------------------------------------------

def test_criterion18_no_supports_singular_minimal():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m18",
               "elements members in m18", "area 0.0005 m^2 in m18", "modulus 200 GPa in m18",
               "load 1 fx 5 N in m18", "resolve in m18")
    assert res.error == ('Stiffness matrix is singular: truss model "m18" is '
                          "unstable or underconstrained")


def test_edge_orphan_node_no_support_no_element_is_singular():
    res = last("coords := [0, 0; 1, 0; 5, 5] m", "members := [1, 2]", "nodes coords in morph",
               "elements members in morph", "area 0.0005 m^2 in morph",
               "modulus 200 GPa in morph", "support 1 fix x, y in morph",
               "support 2 fix y in morph", "resolve in morph")
    assert res.status == "error"
    assert "singular" in res.error


# -- 19 resolve takes no expression ------------------------------------------------------------

def test_criterion19_resolve_trailing_text():
    res = last("resolve extra in m19")
    assert res.error == "resolve takes no expression"


# -- 20 no result region below / load below resolve unused -------------------------------------

def test_criterion20_no_result_region():
    res = last("coords := [0, 0; 1, 0] m", "members := [1, 2]", "nodes coords in m20",
               "elements members in m20")
    assert res.error == 'No result region for truss model "m20" below this region'


def test_criterion20_load_below_resolve_is_unused():
    res = run(*BAR, "load 2 fx 1000 N in bar", "resolve in bar",
              "load 2 fx 999999 N in bar", "bar_force =")
    assert res[-3].status == "ok"   # resolve itself still succeeds
    assert numbers(res[-1].output) == pytest.approx([1000], abs=1e-2)   # unaffected by the later load


# -- 21 isolation / compatibility -----------------------------------------------------------

def test_criterion21_no_truss_tags_sheet_unaffected():
    res = run("x := 5 m", "x =", "y := x^2")
    assert res[0].status == "ok"
    assert res[1].output == "= 5 m"


def test_criterion21_truss_coexists_with_solve_block_and_ode_on_one_sheet():
    sheet = [
        "vary x from 0 in q", "x^2 - 5*x + 6 == 0 in q", "settle in q",
        "tau := 4 s", "ode diff(y(t), t) + y(t)/tau == 0 in decay",
        "start y(0) == 10 m in decay",
        *BAR, "load 2 fx 1000 N in bar",
        "evolve in decay", "resolve in bar",
        "x =", "y(4 s) =", "bar_force =",
    ]
    res = run(*sheet)
    assert res[2].output == "⇒ x = 2"
    assert res[-3].output == "= 2"
    assert "3.67879" in res[-2].output
    assert numbers(res[-1].output) == pytest.approx([1000], abs=1e-2)


def test_criterion21_variable_named_like_a_keyword_without_in_tag_is_unaffected():
    res = run("nodes := 5", "nodes =", "area := 2 m^2", "area =",
              "load := 10 N", "load =", "resolve := 1", "resolve =")
    assert res[1].output == "= 5"
    assert res[3].output == "= 2 m²"
    assert res[5].output == "= 10 N"
    assert res[7].output == "= 1"


@pytest.mark.parametrize("keyword", ["nodes", "elements", "area", "modulus", "load", "resolve"])
def test_other_model_keywords_still_fall_back_to_ordinary_statement_with_bare_equals(keyword):
    """The support-only guard exemption must not leak into any other model keyword: a bare
    ``=`` after one of these words, with a trailing ``in <name>`` tag, must still be treated
    as an ordinary (non-model) statement, exactly as before this spec."""
    st = parse_statement(f"{keyword} = 5 in q")
    assert not st.kind.startswith("model_truss") and st.kind not in ("model_support", "model_load")
    if keyword == "resolve":
        assert st.kind != "model_result"


@pytest.mark.parametrize("op", [":=", "≡", "::=", "→"])
@pytest.mark.parametrize("keyword", ["nodes", "elements", "area", "modulus", "load", "vary",
                                      "settle", "ode", "start", "over", "evolve"])
def test_other_model_keywords_still_fall_back_to_ordinary_definition_with_colon_equals(keyword, op):
    """Same guarantee, for the ':='/'≡'/'::='/'→' operators the pre-existing guard was built
    to catch: a plain definition of a variable whose name happens to equal a model keyword,
    ending in a trailing ' in <name>' tag, must still parse as an ordinary statement for
    every keyword other than 'support' (which has its own, narrower, spec-required exemption
    for its legitimate bare '=' grammar)."""
    st = parse_statement(f"{keyword} {op} 5 in q")
    assert not st.kind.startswith("model_") or st.kind == "model_require"
    # model_require would only trigger for a relational operator, not := /≡ /::= /→; guard
    # the test's own intent by checking no StatementError was raised getting here at all.


# -- 22 parsing -------------------------------------------------------------------------------

def test_criterion22_parsing():
    st = parse_statement("nodes coords in bracket")
    assert st.kind == "model_truss_nodes" and st.model == "bracket" and st.expr == "coords"

    st = parse_statement("support 1 fix x, y = 2 mm in bracket")
    assert st.kind == "model_support"
    assert st.node == "1"
    assert st.axes == [("x", ""), ("y", "2 mm")]

    st = parse_statement("load 3 fy -10000 N in bracket")
    assert st.kind == "model_load"
    assert st.node == "3"
    assert st.axes == [("y", "-10000 N")]

    st = parse_statement("resolve in bracket")
    assert st.kind == "model_result" and st.model == "bracket" and st.goal == "truss"


# -- edge cases named by the spec but not independently numbered ------------------------------

def test_edge_support_settlement_nonzero_value():
    res = last("coords := [0, 0; 2, 0] m", "members := [1, 2]", "nodes coords in mset",
               "elements members in mset", "area 0.0005 m^2 in mset", "modulus 200 GPa in mset",
               "support 1 fix x, y in mset", "support 2 fix x = 1 mm, y in mset",
               "resolve in mset", "mset_displacement =")
    assert res.status == "ok"
    assert numbers(res.output) == pytest.approx([0, 0, 0.001, 0], abs=1e-9)


def test_edge_symbolic_entry_in_coords_rejected():
    res = last("coords := [0, 0; k, 0] m", "members := [1, 2]", "nodes coords in msym",
               "elements members in msym", "area 0.0005 m^2 in msym", "modulus 200 GPa in msym",
               "support 1 fix x, y in msym", "support 2 fix y in msym", "resolve in msym")
    assert res.status == "error"
    assert "k" in res.error and "not defined" in res.error


def test_edge_area_as_row_vector_accepted():
    res = last(
        "coords := [0, 0; 4, 0; 2, 3] m", "members := [1, 3; 2, 3]",
        "nodes coords in rowvec", "elements members in rowvec",
        "area [0.0005, 0.0005] m^2 in rowvec", "modulus 200 GPa in rowvec",
        "support 1 fix x, y in rowvec", "support 2 fix x, y in rowvec",
        "load 3 fy -10000 N in rowvec", "resolve in rowvec",
    )
    assert res.status == "ok"
    assert "3 nodes, 2 elements" in res.output


# -- a known defect found by this review (see docs/board/reviews/015-truss-fem.md) -------------

def test_d1_support_exemption_no_longer_breaks_ordinary_definition_of_a_variable_named_support():
    """D1 FIX CONFIRMED (docs/board/reviews/015-truss-fem.md / decisions.md's "Decided
    2026-10-30 (manager, spec 015 independent review)" entry).

    Previously this test documented a confirmed defect: 'support' was exempted from the
    *entire* "looks like an ordinary statement" guard (not just the narrower bare-'=' check
    the spec's own clean-room note says it actually needs), so a perfectly ordinary
    definition of a variable literally named 'support', ending in ' in <name>', raised a
    confusing parse error instead of defining the variable. The developer's fix keeps the
    pre-existing _STATEMENT_OPS check unconditional for every keyword (including 'support')
    and only skips the bare-'=' / _split_eval check for 'support' specifically -- exactly the
    review's suggested fix. 'support' now has the same parity as every other model keyword.
    """
    for other in ["vary", "settle", "ode", "load", "nodes", "elements", "area", "modulus"]:
        st = parse_statement(f"{other} := 5 in q")
        assert st.kind == "define"   # every other keyword: correctly falls back

    assert parse_statement("support := 5 in q").kind == "define"   # D1: now also falls back

    # the one legitimate reason 'support' needed any exemption at all still works
    st = parse_statement("support 1 fix x = 5 mm in bracket")
    assert st.kind == "model_support" and st.axes == [("x", "5 mm")]
