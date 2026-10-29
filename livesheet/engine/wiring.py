"""Component/wire graph for the canvas-wiring foundation (spec 009).

GUI-independent, like the rest of ``livesheet/engine``: builds the directed graph implied by a
sheet's components and wires, computes a deterministic evaluation order with Kahn's algorithm
(reusing the existing top-to-bottom/left-to-right reading-order key only to break ties between
components the wiring graph does not otherwise order), detects cycles (reused both when a wire is
about to be created and, defensively, at evaluation time), and implements the two placeholder
component kinds ("value", "formula") as thin wrappers around ``Engine.parse`` -- no second
expression parser.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Callable

from .evaluator import Engine, _check_defined
from .syntax import StatementError
from .units import UNITS, UnitError, measure

__all__ = [
    "ComponentSpec", "WireSpec", "ComponentResult",
    "known_kind", "input_ports", "output_ports",
    "topo_sort", "has_cycle", "would_create_cycle", "evaluate", "format_output",
]


# -- data model --------------------------------------------------------------------------------

@dataclass
class ComponentSpec:
    """One component as seen by the wiring graph: just enough to evaluate it and to break ties
    deterministically -- not a GUI object."""

    name: str
    kind: str
    config: dict[str, str] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0


@dataclass
class WireSpec:
    """One output-port-to-input-port connection, matched by name (never object identity)."""

    from_component: str
    from_port: str
    to_component: str
    to_port: str


@dataclass
class ComponentResult:
    """Parallel to ``RegionResult`` (engine/evaluator.py), but for a component's several named
    output ports instead of one printed line."""

    status: str                                   # "ok" | "error"
    error: str = ""
    outputs: dict[str, object] = field(default_factory=dict)


# -- the two placeholder kinds -------------------------------------------------------------------

def _value_ports(config: dict[str, str]) -> tuple[list[tuple[str, bool]], list[str]]:
    return [], ["value"]


def _formula_ports(config: dict[str, str]) -> tuple[list[tuple[str, bool]], list[str]]:
    names = [n.strip() for n in config.get("inputs", "").split(",") if n.strip()]
    return [(n, True) for n in names], ["result"]


_PORTS: dict[str, Callable[[dict[str, str]], tuple[list[tuple[str, bool]], list[str]]]] = {
    "value": _value_ports,
    "formula": _formula_ports,
}


def known_kind(kind: str) -> bool:
    return kind in _PORTS


def input_ports(kind: str, config: dict[str, str]) -> list[tuple[str, bool]]:
    """``(name, required)`` pairs, in declaration order; ``[]`` for an unrecognised kind."""
    fn = _PORTS.get(kind)
    return fn(config)[0] if fn is not None else []


def output_ports(kind: str, config: dict[str, str]) -> list[str]:
    """Output port names, in declaration order; ``[]`` for an unrecognised kind."""
    fn = _PORTS.get(kind)
    return fn(config)[1] if fn is not None else []


def _compute_value(config: dict[str, str], inputs: dict[str, object], engine: Engine) -> dict[str, object]:
    env = dict(UNITS)
    value = engine.parse(config.get("expr", ""), env)
    _check_defined(value)
    return {"value": value}


def _compute_formula(config: dict[str, str], inputs: dict[str, object], engine: Engine) -> dict[str, object]:
    env = dict(UNITS)
    env.update(inputs)
    value = engine.parse(config.get("expr", ""), env)
    _check_defined(value)
    measure(value)   # trigger the same unit-mismatch check/text a math region's '=' would
    return {"result": value}


_COMPUTE: dict[str, Callable[[dict[str, str], dict[str, object], Engine], dict[str, object]]] = {
    "value": _compute_value,
    "formula": _compute_formula,
}


def format_output(value: object, significant: int = 6) -> str:
    """Compact display text for one output value, reusing the engine's own number/unit
    formatting (same convention as a plain ``evaluate`` statement's result)."""
    from .formatting import format_number
    from .units import dims_to_text

    try:
        m = measure(value)
    except Exception:  # noqa: BLE001 - best-effort display only
        return str(value)
    number = format_number(m.magnitude, significant)
    unit = dims_to_text(m.dims)
    return f"{number} {unit}" if unit else number


# -- graph: topological order (Kahn's algorithm) + cycle detection ------------------------------

def topo_sort(names: list[str], pos_of: dict[str, tuple[float, float]],
              edges: set[tuple[str, str]]) -> tuple[list[str], set[str]]:
    """Kahn's algorithm: returns ``(order, remainder)``. ``remainder`` is the set of nodes that
    could not be placed (non-empty exactly when ``edges`` contains a cycle). Among nodes with no
    remaining incoming edges, the one earliest in ``pos_of`` (today's ``(y, x)`` reading-order
    key) is picked next -- a deterministic tie-break applied only between components the wiring
    graph does not otherwise order, never the primary ordering rule."""
    preds: dict[str, set[str]] = {n: set() for n in names}
    succ: dict[str, list[str]] = {n: [] for n in names}
    for a, b in edges:
        if a not in preds or b not in preds or a in preds[b]:
            continue
        preds[b].add(a)
        succ[a].append(b)
    indeg = {n: len(preds[n]) for n in names}
    heap = [(pos_of.get(n, (0.0, 0.0)), n) for n in names if indeg[n] == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        _, n = heapq.heappop(heap)
        order.append(n)
        for m in succ[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, (pos_of.get(m, (0.0, 0.0)), m))
    remainder = set(names) - set(order)
    return order, remainder


def has_cycle(names: list[str], edges: set[tuple[str, str]]) -> bool:
    _, remainder = topo_sort(names, {}, edges)
    return bool(remainder)


def would_create_cycle(names: list[str], edges: set[tuple[str, str]],
                        candidate: tuple[str, str]) -> bool:
    """True when adding ``candidate`` (an (upstream, downstream) component-name pair) to
    ``edges`` would introduce a cycle -- including a 1-node self-cycle (``candidate[0] ==
    candidate[1]``). Reused both at wire-creation time and, defensively, at evaluation time."""
    return has_cycle(names, edges | {candidate})


# -- evaluation ----------------------------------------------------------------------------------

def evaluate(specs: list[ComponentSpec], wires: list[WireSpec], engine: Engine) -> dict[str, ComponentResult]:
    """Evaluate every component in topological order of the wiring graph (not reading order).

    Called with an empty ``specs``/``wires`` list on a sheet with no components -- returns ``{}``
    immediately, which is what keeps this pass a true no-op for component-free sheets."""
    if not specs:
        return {}
    names = [s.name for s in specs]
    by_name = {s.name: s for s in specs}
    pos_of = {s.name: (s.y, s.x) for s in specs}
    name_set = set(names)
    edges = {(w.from_component, w.to_component) for w in wires
             if w.from_component in name_set and w.to_component in name_set}
    order, remainder = topo_sort(names, pos_of, edges)

    # Defensive-only (see module docstring): wire creation already rejects anything that would
    # create a cycle, so this is a safety net for a hand-edited/corrupted file loaded with one.
    input_src: dict[tuple[str, str], tuple[str, str]] = {}
    for w in wires:
        if w.from_component in name_set and w.to_component in name_set:
            input_src[(w.to_component, w.to_port)] = (w.from_component, w.from_port)

    results: dict[str, ComponentResult] = {}
    for name in remainder:
        results[name] = ComponentResult(
            "error", "Part of a circular connection; this wire needs to be removed.")

    for name in order:
        spec = by_name[name]
        if not known_kind(spec.kind):
            results[name] = ComponentResult("error", f"Unknown component kind '{spec.kind}'.")
            continue
        inputs: dict[str, object] = {}
        error: str | None = None
        for port_name, required in input_ports(spec.kind, spec.config):
            src = input_src.get((name, port_name))
            if src is None:
                if required:
                    error = f"Input '{port_name}' is not connected."
                    break
                continue
            src_name, src_port = src
            src_result = results.get(src_name)
            if src_result is None or src_result.status != "ok" or src_port not in src_result.outputs:
                error = f"Input '{port_name}': upstream component has an error."
                break
            inputs[port_name] = src_result.outputs[src_port]
        if error is not None:
            results[name] = ComponentResult("error", error)
            continue
        try:
            outputs = _COMPUTE[spec.kind](spec.config, inputs, engine)
            results[name] = ComponentResult("ok", "", outputs)
        except (StatementError, UnitError) as exc:
            results[name] = ComponentResult("error", str(exc))
        except ZeroDivisionError:
            results[name] = ComponentResult("error", "Division by zero")
        except Exception as exc:  # noqa: BLE001 - surface any failure in the component, not a crash
            msg = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            results[name] = ComponentResult("error", msg[:160])
    return results
