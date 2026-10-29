"""Developer tests for spec 009, phase W1 (engine-level component/wire graph), written from the
spec's acceptance criteria 1-11 and edge cases while implementing ``livesheet/engine/wiring.py``.
Pure Python/SymPy, no PySide6 import -- this module must stay GUI-independent, like the rest of
``livesheet/engine``. The tester writes an independent black-box review separately.
"""

from __future__ import annotations

import pytest

from livesheet.engine.evaluator import Engine
from livesheet.engine.wiring import (
    ComponentResult,
    ComponentSpec,
    WireSpec,
    evaluate,
    format_output,
    has_cycle,
    input_ports,
    known_kind,
    output_ports,
    topo_sort,
    would_create_cycle,
)


@pytest.fixture
def engine() -> Engine:
    return Engine()


# ===========================================================================
# The two placeholder kinds: ports (Qt-free, data-model only)
# ===========================================================================

def test_value_kind_has_no_inputs_one_output():
    assert input_ports("value", {}) == []
    assert output_ports("value", {}) == ["value"]
    assert known_kind("value")


def test_formula_kind_ports_from_comma_separated_inputs():
    config = {"inputs": "a, b", "expr": "a + b"}
    assert input_ports("formula", config) == [("a", True), ("b", True)]
    assert output_ports("formula", config) == ["result"]
    assert known_kind("formula")


def test_unknown_kind_has_no_ports_and_is_not_known():
    assert input_ports("csv", {}) == []
    assert output_ports("csv", {}) == []
    assert not known_kind("csv")


# ===========================================================================
# Criterion 1: an empty component list is a true no-op
# ===========================================================================

def test_criterion1_empty_components_returns_empty_dict(engine):
    assert evaluate([], [], engine) == {}


# ===========================================================================
# Criterion 2: a Value component evaluates its expression
# ===========================================================================

def test_criterion2_value_component_evaluates_expression(engine):
    specs = [ComponentSpec("V1", "value", {"expr": "12 m/s"})]
    results = evaluate(specs, [], engine)
    v1 = results["V1"]
    assert v1.status == "ok"
    assert format_output(v1.outputs["value"]) == "12 m/s"


# ===========================================================================
# Criteria 3-4: Formula with one input connected, then both connected
# ===========================================================================

def test_criterion3_formula_with_one_unconnected_required_input_errors(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "12 m/s"}),
        ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"}, y=20),
    ]
    wires = [WireSpec("V1", "value", "F1", "a")]
    results = evaluate(specs, wires, engine)
    f1 = results["F1"]
    assert f1.status == "error"
    assert f1.error == "Input 'b' is not connected."
    assert f1.outputs == {}


def test_criterion4_formula_with_both_inputs_connected_computes_result(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "12 m/s"}),
        ComponentSpec("V2", "value", {"expr": "3 m/s"}, y=20),
        ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"}, y=40),
    ]
    wires = [WireSpec("V1", "value", "F1", "a"), WireSpec("V2", "value", "F1", "b")]
    results = evaluate(specs, wires, engine)
    f1 = results["F1"]
    assert f1.status == "ok"
    assert format_output(f1.outputs["result"]) == "15 m/s"


# ===========================================================================
# Criterion 5: one-connection-per-input is a wire-creation-time rule
# (the engine-level primitive it is built from: the GUI's try_connect refuses a second wire into
# an already-connected input before ever calling evaluate(); evaluate() itself just takes
# whichever WireSpec entries it is given, so this is exercised at the GUI layer -- see
# tests/test_wiring_gui.py)
# ===========================================================================

# ===========================================================================
# Criterion 6 / cycle detection: self-cycle and a 2-node cycle
# ===========================================================================

def test_criterion6_self_cycle_is_detected():
    assert would_create_cycle(["F1"], set(), ("F1", "F1"))


def test_criterion6_two_node_cycle_is_detected():
    names = ["F1", "F2"]
    edges = {("F1", "F2")}
    assert would_create_cycle(names, edges, ("F2", "F1"))


def test_no_cycle_for_independent_components():
    names = ["V1", "F1"]
    edges = set()
    assert not would_create_cycle(names, edges, ("V1", "F1"))


# ===========================================================================
# Criterion 7 (engine-level half): removing a wire from the wires list makes the input
# unconnected again on the next evaluate() call (deletion cascading itself is a GUI concern,
# tested in test_wiring_gui.py)
# ===========================================================================

def test_criterion7_removing_a_wire_reverts_to_unconnected_error(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "12 m/s"}),
        ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"}, y=20),
        ComponentSpec("V2", "value", {"expr": "3 m/s"}, y=40),
    ]
    wires = [WireSpec("V1", "value", "F1", "a"), WireSpec("V2", "value", "F1", "b")]
    assert evaluate(specs, wires, engine)["F1"].status == "ok"
    # V1 "deleted": its spec and the wire from it are both gone.
    specs2 = [s for s in specs if s.name != "V1"]
    wires2 = [w for w in wires if w.from_component != "V1"]
    f1 = evaluate(specs2, wires2, engine)["F1"]
    assert f1.status == "error"
    assert f1.error == "Input 'a' is not connected."


# ===========================================================================
# Criterion 8: a unit mismatch inside a kind's own calculation uses the exact engine error text
# ===========================================================================

def test_criterion8_unit_mismatch_uses_existing_engine_error_text(engine):
    specs = [
        ComponentSpec("Va", "value", {"expr": "1 m"}),
        ComponentSpec("Vb", "value", {"expr": "1 s"}, y=20),
        ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"}, y=40),
    ]
    wires = [WireSpec("Va", "value", "F1", "a"), WireSpec("Vb", "value", "F1", "b")]
    f1 = evaluate(specs, wires, engine)["F1"]
    assert f1.status == "error"

    plain_region_result = engine.evaluate([(1, "a := 1 m"), (2, "b := 1 s"), (3, "a + b =")])
    assert f1.error == plain_region_result[3].error == "Units do not match"


# ===========================================================================
# Criterion 9: deterministic reading-order tie-break among components the wiring graph does
# not otherwise order
# ===========================================================================

def test_criterion9_reading_order_tie_break_no_wire_between_components():
    names = ["V4", "V3"]
    pos_v3_above_v4 = {"V3": (0.0, 0.0), "V4": (20.0, 0.0)}
    order, remainder = topo_sort(names, pos_v3_above_v4, set())
    assert order == ["V3", "V4"]
    assert remainder == set()

    pos_v4_above_v3 = {"V3": (20.0, 0.0), "V4": (0.0, 0.0)}
    order2, _ = topo_sort(names, pos_v4_above_v3, set())
    assert order2 == ["V4", "V3"]


def test_tie_break_does_not_override_a_real_wiring_dependency():
    # F1 depends on V1 via a wire, even though F1 is placed above V1 on the canvas.
    names = ["F1", "V1"]
    pos = {"F1": (0.0, 0.0), "V1": (100.0, 0.0)}
    edges = {("V1", "F1")}
    order, remainder = topo_sort(names, pos, edges)
    assert order == ["V1", "F1"]
    assert remainder == set()


# ===========================================================================
# Defensive cycle handling at evaluation time (hand-edited/corrupted file safety net)
# ===========================================================================

def test_defensive_cycle_at_evaluation_time_marks_every_node_in_it(engine):
    specs = [
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a"}),
        ComponentSpec("F2", "formula", {"inputs": "a", "expr": "a"}, y=20),
    ]
    wires = [WireSpec("F1", "result", "F2", "a"), WireSpec("F2", "result", "F1", "a")]
    results = evaluate(specs, wires, engine)
    for name in ("F1", "F2"):
        assert results[name].status == "error"
        assert results[name].error == "Part of a circular connection; this wire needs to be removed."


# ===========================================================================
# Error states: upstream failure propagation, unknown kind
# ===========================================================================

def test_upstream_error_propagates_to_downstream_input(engine):
    specs = [
        ComponentSpec("F0", "formula", {"inputs": "x", "expr": "x"}),   # x never connected: errors
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a"}, y=20),
    ]
    wires = [WireSpec("F0", "result", "F1", "a")]
    results = evaluate(specs, wires, engine)
    assert results["F0"].status == "error"
    assert results["F1"].status == "error"
    assert results["F1"].error == "Input 'a': upstream component has an error."


def test_unknown_kind_reports_its_own_error_and_does_not_crash(engine):
    specs = [ComponentSpec("X1", "csv", {})]
    results = evaluate(specs, [], engine)
    assert results["X1"].status == "error"
    assert results["X1"].error == "Unknown component kind 'csv'."


def test_unknown_kind_component_still_lets_other_components_evaluate(engine):
    specs = [
        ComponentSpec("X1", "csv", {}),
        ComponentSpec("V1", "value", {"expr": "1 m"}, y=20),
    ]
    results = evaluate(specs, [], engine)
    assert results["X1"].status == "error"
    assert results["V1"].status == "ok"


# ===========================================================================
# Edge case: a component with zero wires behaves exactly like a freshly-placed one
# ===========================================================================

def test_edge_value_with_zero_wires_just_evaluates(engine):
    results = evaluate([ComponentSpec("V1", "value", {"expr": "9.81 m/s^2"})], [], engine)
    assert results["V1"].status == "ok"


def test_edge_formula_with_zero_wires_shows_unconnected_error(engine):
    results = evaluate(
        [ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"})], [], engine)
    assert results["F1"].status == "error"
    assert results["F1"].error == "Input 'a' is not connected."


# ===========================================================================
# Edge case: a kind's own calculation can fail on otherwise-valid inputs (syntax error)
# ===========================================================================

def test_formula_syntax_error_in_expression_reported_as_error(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "1 m"}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a +"}, y=20),
    ]
    wires = [WireSpec("V1", "value", "F1", "a")]
    f1 = evaluate(specs, wires, engine)["F1"]
    assert f1.status == "error"
    assert f1.error  # some error text; exact wording is the engine's own syntax-error message


def test_formula_division_by_zero_matches_plain_math_region_behaviour(engine):
    # SymPy's own convention (also used today by a plain math region): a symbolic ``x/0``
    # evaluates to "complex infinity" rather than raising -- same non-error "undefined" display
    # both places, not a new error-text path invented for components.
    specs = [
        ComponentSpec("V1", "value", {"expr": "1 m"}),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a / 0"}, y=20),
    ]
    wires = [WireSpec("V1", "value", "F1", "a")]
    f1 = evaluate(specs, wires, engine)["F1"]
    assert f1.status == "ok"
    assert format_output(f1.outputs["result"]) == "undefined"


# ===========================================================================
# Edge case: a component with no output connected downstream still evaluates and keeps its value
# ===========================================================================

def test_unreferenced_output_still_evaluates(engine):
    results = evaluate([ComponentSpec("V1", "value", {"expr": "5 m"})], [], engine)
    assert results["V1"].status == "ok"
    assert format_output(results["V1"].outputs["value"]) == "5 m"


# ===========================================================================
# Components do not see sheet variables (open question 1, accepted): only UNITS/constants and
# wired inputs are visible.
# ===========================================================================

def test_value_component_cannot_see_sheet_variables(engine):
    # "foo" is not a unit/constant and not wired in -- parsing should fail the same way an
    # undefined name does in a plain math region, not silently succeed.
    results = evaluate([ComponentSpec("V1", "value", {"expr": "foo + 1"})], [], engine)
    assert results["V1"].status == "error"


def test_formula_component_only_sees_its_own_wired_inputs_not_other_components_outputs(engine):
    specs = [
        ComponentSpec("V1", "value", {"expr": "1 m"}),
        ComponentSpec("V2", "value", {"expr": "2 m"}, y=20),
        ComponentSpec("F1", "formula", {"inputs": "a", "expr": "a + V2"}, y=40),
    ]
    # Only V1 is wired to F1.a; "V2" is not a name F1 can see just because V2 exists on the sheet.
    wires = [WireSpec("V1", "value", "F1", "a")]
    f1 = evaluate(specs, wires, engine)["F1"]
    assert f1.status == "error"


# ===========================================================================
# ComponentResult dataclass defaults
# ===========================================================================

def test_component_result_defaults():
    r = ComponentResult("ok")
    assert r.error == ""
    assert r.outputs == {}
