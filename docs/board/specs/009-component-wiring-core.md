# 009 Component-and-wiring canvas core

Source inspiration (concept only, nothing copied):
- Block diagram / signal-flow graph, as used in control theory and electrical engineering for
  roughly a century: named boxes ("blocks") with input and output terminals, connected by directed
  lines; a block's output depends only on the values on its own input terminals, never on where the
  box happens to sit on the page. General textbook-level concept, public domain, no single vendor.
- Pipe-and-filter software-architecture pattern (classic, decades old): a small program is built
  from independent filters, each a transform from input(s) to output(s); the *wiring* between
  filters is just composition — order of connection doesn't matter, only the resulting dependency
  graph does.
- Spreadsheet dependency graph (the mechanism underlying every spreadsheet since VisiCalc-era
  tools, long public domain and not tied to any one product): a cell recomputes only when
  something it depends on changes, dependency order is derived from the references actually drawn
  between cells (not from cell position on the grid), and a circular reference is detected and
  rejected rather than silently looped.
- Kahn's algorithm for topological sorting of a directed acyclic graph (Arthur B. Kahn, 1962) —
  standard, decades-old computer-science technique for computing a valid evaluation order from a
  dependency graph and for detecting that a graph is *not* acyclic when the algorithm cannot finish.
- Generic diagramming conventions shared by many unrelated, long-established tool categories
  (flowchart editors, circuit-diagram/schematic editors, UML/entity-relationship diagram editors):
  terminals drawn at a box's edge, a directed connector drawn between two terminals, deleting a box
  removes its connectors, a connector shown in an alert colour when something about the connection
  is wrong. None of this is distinctive to one named product; it recurs across all of the tool
  categories above.
- `.claude/skills/modeling-concepts/SKILL.md` — the team's own idea checklist, itself distilled
  from the generic sources above (see `docs/board/decisions.md`, 2026-10-29, Theo's decision to
  take this generic-concepts route specifically so this feature needs no new vendor entry in
  `docs/IP-POLICY.md`).
- No named commercial node-based/dataflow/visual-programming/wiring product's documentation,
  screenshots, icon set, specific port-shape convention, colour coding or wiring gesture was read
  or used as a source for this spec.

Scope note: this is the **foundation** spec for milestone M6 (backlog 31 only). It defines what a
"component" and a "wire" are in the abstract — the box/port/wire data model, how wires are created
and removed, cycle detection, and evaluation order — and includes exactly two minimal, generic
placeholder component *kinds* ("Value" and "Formula", described below) solely to make this
mechanism concrete and testable. It deliberately does **not** design the real component kinds:
CSV/other open tabular formats and Excel files (backlog 32), nested `.lsheet` sub-components
(backlog 33) or sandboxed user-script components (backlog 34) are separate, later specs. Those
specs plug new kinds into the same port/wire contract defined here; this spec does not anticipate
their internals beyond naming the extension point.

Size: two phases, about 3.5 days total.
- **Phase W1 (data model + evaluation)**: `ComponentRegion`/`WireData`/`.lsheet` format changes,
  the wiring graph, cycle detection, topological evaluation, the two placeholder kinds. About 2
  days.
- **Phase W2 (canvas + dialogs)**: drawing components/ports/wires on the existing canvas, the
  "Add Component" and "Connect..." dialogs, error-state painting. About 1.5 days.

---

## User story
As a LiveSheet user, I want to place a small box on my sheet that represents a self-contained
calculation step with clearly named inputs and outputs, connect it to other such boxes with a
visible line (the way an engineer would sketch a block diagram), and have LiveSheet work out by
itself in which order to compute them from how they are connected — not from where I happened to
drop them on the page — so that I can build small calculation pipelines (and, in later milestones,
pull in a data file or a reusable sub-sheet) without writing a single top-to-bottom formula chain.

## Behaviour (own words)

### Where components live
Components are placed on the **same** free-form canvas as today's math, text and plot regions —
there is no separate "wiring mode" or second canvas to switch into. A component is a new region
kind (`ComponentRegion`), using the existing `Region` base class (movable, selectable, snapped to
the same grid, deletable with Delete/Backspace like any other region) so all of today's canvas
mechanics (selection, drag-move, undo-free single-owner deletion, PDF export) apply to it
unchanged. A **wire** is not a region: it is a thin connector drawn between two components' ports
and is described below under "Wires".

A sheet containing zero `ComponentRegion`s and zero wires behaves byte-for-byte as it does today:
the existing math/text/plot evaluation pass (`Engine.evaluate`, reading-order top-to-bottom-then-
left-to-right) is completely untouched, and the new component-evaluation pass (below) is simply
called with empty input and returns empty output. Nothing about today's regions, syntax, or
`.lsheet` files without components changes.

### What a component is (the abstraction)
A component is a labelled box with:
- a **name**: a short identifier, unique among components on the sheet, shown in the box's header
  and used to refer to the component in wire records and in error messages (e.g. "Comp3"). The
  user may rename it; renaming updates any wires referencing it (wires store the current name, see
  format section — renaming is a simple field edit, not a reference-rewrite problem, because there
  is exactly one place the name is stored per component).
- a **kind**: which calculation this component performs (e.g. the two placeholder kinds below, or —
  in later specs — "CSV", "Sub-sheet", "Script"). The kind fixes the component's port *names* and
  how its outputs are computed from its inputs; it does not change the port/wire mechanism itself.
- zero or more **input ports**, each with a name (unique among that component's input ports) and a
  `required` flag.
- one or more **output ports**, each with a name (unique among that component's output ports).
- a small amount of **kind-specific configuration** — e.g. the literal expression typed into a
  "Value" component — stored as a flat string-to-string mapping (see format section) so later kinds
  can add their own configuration keys without changing this contract.

A component's computed outputs depend only on the values currently present on its own input ports
(from wires, see below) and its own configuration — never on its position on the canvas, and never
on any other region's value, consistent with the block-diagram/pipe-and-filter idea that a block is
a self-contained transform. (Components in this spec do **not** read or write ordinary sheet
variables defined by math regions; that integration, if wanted, is left to a future spec so this
foundation stays small — see Open questions.)

### Ports, drawn
Each port is drawn as a small named terminal at the component box's edge: input ports along the
left edge, output ports along the right edge, stacked top-to-bottom in the order the kind declares
them, each with its name printed just outside the box — the same left-to-right signal-flow
convention used in block diagrams and circuit schematics generically, not a convention particular
to any one diagramming product. A component box auto-sizes to fit its header, its longest port
label, and its configuration summary; it is not user-resizable in this spec (unlike `PlotRegion`,
which already has a resize handle — components keep things simpler for now).

### Wires
A wire connects exactly one output port to exactly one input port (never output-to-output or
input-to-input). Rules, all enforced the moment a wire is created, not discovered later:
- **One connection per input.** An input port accepts at most one incoming wire. Attempting to wire
  a second output into an already-connected input is rejected immediately with a message ("Input
  'b' on Comp2 is already connected — disconnect it first.") and no wire is created. This mirrors a
  spreadsheet cell holding exactly one formula.
- **Fan-out is fine.** One output port may feed any number of input ports (on the same or different
  components) — the classic block-diagram branch point.
- **No cycles.** Before a wire is added, LiveSheet checks whether adding it would create a cycle in
  the component-level dependency graph (see "Evaluation order" below for how the graph is built).
  If it would — including a component wired to one of its own input ports, a 1-node cycle — the
  wire is rejected immediately with a visible message ("This connection would create a circular
  dependency.") and no wire is created, exactly like a spreadsheet rejecting a circular reference
  rather than silently looping forever.
- **Types are typed-by-convention, not enforced at wire time.** A wire may be drawn between any
  output and any input regardless of what kind of value each currently produces/expects; LiveSheet
  does not maintain a static type system for ports. If the value actually produced by the source
  turns out to be unusable by the destination's calculation, that surfaces as an ordinary
  evaluation error on the destination component (see "Error states" below) — the same way an
  engine function already reports "X is not a function" or a unit mismatch today, reusing the
  existing error-reporting pattern rather than adding a new type-checking subsystem.
- **Deleting a component deletes its wires.** Removing a `ComponentRegion` (Delete/Backspace, same
  as any region) also removes every wire attached to any of its ports.
- **Deleting a wire** removes only that one connection; the two components themselves are
  untouched (their other ports/wires, if any, are unaffected).

Creating a wire (two equivalent, independent paths — the second one deliberately a generic,
keyboard-reachable dialog rather than requiring any particular pointer gesture, for accessibility
and to keep this spec's only canvas-level interaction boring and generic rather than a bespoke
on-canvas technique, per the IP check below):
1. **Drag-to-connect**: press on an output port terminal, drag to an input port terminal, release.
   This is the same generic terminal-to-terminal drag used across unrelated diagram-editor
   categories (flowchart editors, circuit-diagram editors) for as long as such editors have
   existed; while dragging, a line follows the pointer from the source terminal, released over
   empty canvas simply cancels (no wire created).
2. **Connect dialog**: right-click a port (or use a "Connect…" toolbar/menu action with a
   component selected) to open a small modal dialog — the same generic labelled-list dialog chrome
   already used by this project's spec 006 (plot dialog) and spec 008 (matrix dialog) — listing the
   other sheet-compatible ports (outputs, if started from an input; inputs, if started from an
   output) as a plain list the user picks from, then OK. This path needs no dragging at all and is
   fully keyboard-navigable.
   Either path runs through one shared `Worksheet.try_connect(source_port, dest_port)` method that
   performs the one-connection-per-input and no-cycle checks above and either creates the wire or
   reports the rejection message; there is exactly one place these rules are enforced.

A wire is drawn as a line from the centre of its source terminal to the centre of its destination
terminal with a small arrowhead at the destination end (direction is otherwise ambiguous once two
components move relative to each other) — the same directed-edge convention signal-flow diagrams
have used for decades. A wire whose destination component is currently in an error state (below)
is drawn in the same error colour (`COLOR_ERROR`, already defined in `regions.py`) already used for
region error text elsewhere in the app, rather than inventing a new colour.

Placing a component: "Insert > Component…" opens a modal "Add Component" dialog — kind chosen from
a dropdown (only "Value" and "Formula" exist in this spec), followed by that kind's own small set
of labelled fields (for "Value": one expression field; for "Formula": an input-port-names field and
an expression field, see below) — the same generic modal-dialog-with-labelled-fields pattern as
spec 006/008, not a new interaction style. OK places the new, fully-configured component at the
crosshair; Cancel creates nothing.

### The two placeholder kinds (for this spec's own testability only)
These exist only to exercise the port/wire/evaluation mechanism end to end without pre-designing
any of backlog 32-34's real kinds. Both are deliberately the simplest possible examples of the two
textbook block-diagram primitives — a constant/source block and a function block — not a
disguised version of any specific future kind.

- **Value**: zero input ports, one output port named `value`. Configuration: one field, `expr` — a
  short expression in the same syntax `MathRegion` already parses for a plain `evaluate` statement
  (numbers, units, vectors/matrices — see spec 002/`engine/syntax.py`), but evaluated in an
  environment containing only the engine's built-in units/constants, **not** the rest of the
  sheet's variables (components do not see sheet variables, see above). The output port's value is
  whatever that expression evaluates to. Example: `expr = "9.81 m/s^2"` → output `value` carries
  that measured value.
- **Formula**: one or more input ports, named by the user when the component is created (a
  comma-separated list in the dialog, e.g. `a, b`); exactly one output port, fixed name `result`.
  Configuration: one field, `expr` — an expression written in terms of the input port names only
  (e.g. `a + b`), parsed and evaluated with an environment built from nothing but the current,
  resolved values on this component's own input ports (plus the engine's built-in units/
  constants) — again, no visibility into sheet variables. Example: inputs `a = 3 m`, `b = 4 m` with
  `expr = "sqrt(a^2 + b^2)"` → output `result = 5 m`.

Both kinds reuse `Engine.parse` directly (same parser, same unit system, same error types) rather
than inventing a second expression language — see "Fits current architecture?".

### Error states
- **Unconnected required input**: if a component's input port has `required = True` (both
  placeholder kinds mark every one of their input ports required — "Formula" has no optional-port
  concept in this spec) and no wire feeds it, that component's evaluation does not run; the
  component is shown in the same visual error state `MathRegion` already uses for an evaluation
  error (`_has_error = True`, `COLOR_ERROR_BG` fill, same dashed/solid frame convention), with a
  tooltip/inline message "Input 'a' is not connected." This is re-checked on every recalculation,
  so wiring the missing input later clears the error on the next pass, same as fixing an undefined
  name in a math region does today.
- **Upstream error propagation**: if a component's input is wired to an output of a component that
  itself failed to produce a value this pass (unconnected-input error, a kind-specific failure, or
  — defensively, see below — being caught in an unresolved cycle), the downstream component also
  shows an error ("Input 'a': upstream component has an error") instead of running with a missing
  value — the same way any dependency graph's failure propagates to whatever depends on it, and the
  same way today's sheet already reports "x is not defined" rather than guessing a default.
- **Cycle found at evaluation time (defensive, not the normal path)**: wire creation already
  rejects any wire that would introduce a cycle (above), so this should not occur from ordinary use.
  It is still checked again during evaluation (see "Evaluation order") as a safety net for a
  hand-edited or corrupted `.lsheet` file loaded with a cycle already present in its `wires` list;
  every component left over after the topological sort cannot finish is shown in the error state
  with the message "Part of a circular connection; this wire needs to be removed." No crash, no
  infinite loop, consistent with "reject, like a spreadsheet does, not silently loop."
- A kind's own calculation can also fail on otherwise-valid inputs (e.g. "Formula"'s expression has
  a syntax error, or divides by zero) — reported in the component's error state using the exact
  same `StatementError`/`UnitError`/generic-exception handling `Engine._run_statement` already does
  for math regions (see "Fits current architecture?"), not a new error-formatting path.

### Evaluation order
Today's rule — reading order, top to bottom then left to right (`SheetDocument.ordered`,
`Worksheet.ordered_regions`) — continues to apply, unchanged, to math/text/plot regions and to any
ordinary (non-wired) sub-sheet. It is *not* used for components: per backlog 31, components are
evaluated in a **topological order of the wiring graph** instead, computed as follows.

1. Build a directed graph whose nodes are the sheet's `ComponentRegion`s and whose edges go from a
   component with an output wired to another component's input, to that other component — one edge
   per wire (two wires between the same pair of components, on different ports, are two edges; for
   the purpose of finding an order this behaves the same as one, since both demand "upstream before
   downstream").
2. Run Kahn's algorithm: repeatedly take a node with no remaining incoming edges, append it to the
   order, and remove its outgoing edges (decrementing the targets' remaining-incoming-edge count).
   Because the wire-creation check already prevents cycles, this normally always finishes with every
   component placed in the order; see the defensive cycle case above for the hand-edited-file
   exception.
3. **Deterministic tie-break**: whenever more than one node currently has zero remaining incoming
   edges (components with no ordering relationship between them — most components, in a typical
   sheet, have none), pick the one that is earliest in today's existing reading-order key
   `(y, x)` — i.e. the same top-to-bottom-then-left-to-right rule, applied only to *break ties
   between components the wiring graph does not otherwise order*, not as the primary ordering rule.
   This keeps the evaluation order fully deterministic and keeps the visual arrangement of
   unconnected components meaningful, without resurrecting position as the ordering rule for
   components that *are* connected.
4. Evaluate each component in that order: collect its input values (from each connected wire's
   source component's already-computed output, or flag the "not connected"/"upstream error" cases
   above), run its kind's compute step, record its output values (and/or its error).

This pass is independent of, and runs as an additional step alongside (not instead of), the
existing `Engine.evaluate` pass for math/text/plot regions — see "Fits current architecture?" for
exactly where it is called from `Worksheet.recalculate()`.

## Syntax proposal (own keywords)
N/A for sheet statement syntax — components are a canvas/graph concept, not a new statement kind in
`engine/syntax.py`. The two placeholder kinds' configuration fields (`expr` for "Value", `inputs` +
`expr` for "Formula") reuse the *existing* expression syntax `Engine.parse` already accepts for a
plain `evaluate` statement; no new grammar, no new keyword is added to the statement parser.

## Acceptance criteria
1. A sheet with zero `ComponentRegion`s and zero wires: `Worksheet.recalculate()` produces results
   for its math/plot regions identical (same `RegionResult`s) to today's behaviour before this
   spec, and the new component-evaluation call is made with an empty component list and returns an
   empty result mapping — i.e. no measurable behaviour change for component-free sheets.
2. Add a "Value" component `V1` with `expr = "12 m/s"`. Its output port `value` evaluates to a
   measured value of `12 m/s`; `V1` is not in an error state.
3. Add a "Formula" component `F1` with input ports `a, b` and `expr = "a + b"`. Wire `V1.value ->
   F1.a`. `F1.b` is unconnected and required: `F1` is in the error state with message "Input 'b' is
   not connected."; `F1`'s `result` port has no value.
4. Add a second "Value" component `V2` with `expr = "3 m/s"`. Wire `V2.value -> F1.b`. `F1` is no
   longer in an error state; its `result` port evaluates to `15 m/s`.
5. Attempt to wire `V2.value` into `F1.a` (already connected to `V1.value`): rejected immediately
   with "Input 'a' on F1 is already connected — disconnect it first."; `F1.a`'s existing wire from
   `V1` is unchanged.
6. Attempt to wire `F1.result` back into `F1.a` (or, with a second Formula component `F2` wired
   `F1 -> F2`, attempt to wire `F2.result` into `F1`'s any input): rejected immediately with "This
   connection would create a circular dependency."; no wire is created either way.
7. Delete `V1`: the wire `V1.value -> F1.a` is removed with it; `F1.a` becomes unconnected and `F1`
   returns to the error state "Input 'a' is not connected.".
8. Unit mismatch inside a kind's own calculation still reports through the existing engine error
   text: a "Formula" component with inputs `a = 1 m`, `b = 1 s`, `expr = "a + b"` is in the error
   state with the same "Units do not match…" message `Engine.parse`/`measure` already produce for
   that case in a plain math region today (no new error-text path).
9. Reading-order tie-break: two "Value" components `V3` (placed above `V4` on the canvas) with no
   wire between them are evaluated in that reading-order-tie-broken sequence; reordering their
   canvas positions (with still no wire between them) changes only that tie-broken sequence, never
   their computed output values (both are source components with no inputs — this criterion checks
   the *order* recorded internally, not a value change, since neither component's value depends on
   order at all).
10. Save a sheet containing `V1`, `V2`, `F1` and their two wires to a `.lsheet` file, close, reopen:
    all three components, their configuration, their names, and both wires are restored exactly;
    `F1.result` again evaluates to `15 m/s` with no user action beyond opening the file.
11. A `.lsheet` file from before this spec (version 1, no components, no `wires` key at all) still
    loads with zero errors and zero components; a file saved by this spec's code with no components
    present writes `version = 2` (or `1`, if also plot-free) exactly as today — i.e. the version
    number is only bumped to 3 when a component or wire actually exists in the file (see format
    section).

## Edge cases
- A component with zero wires at all (every input, if any, unconnected) behaves exactly like a
  freshly-placed one: "Value" (no inputs) simply evaluates; "Formula" (at least one required input)
  shows the unconnected-input error until wired.
- A wire's source component is deleted and the file is then hand-edited to still list that wire
  (simulating a corrupted file): on load, a wire naming a component or port that no longer exists
  is silently dropped (not written back until the file is saved again) rather than failing to open
  the whole file — the same lenient, don't-refuse-to-open posture already used elsewhere for
  resilience, distinct from the *structural* region-kind validation in `RegionData.__post_init__`,
  which still raises `DocumentError` for a genuinely malformed region record.
- Two components given the same name (e.g. by hand-editing a file, or an unanticipated future race)
  are silently disambiguated on load by appending " (2)", " (3)", … to the later ones — never a
  hard load failure over a name collision.
- A component whose `kind` string is not recognised by this build (e.v.g. a newer LiveSheet file
  opened by an older build, or a corrupted kind string) still loads as a region — the box, its
  name, its configuration and its wires all survive — but shows the error state "Unknown component
  kind 'whatever'." at evaluation time; this is a run-time concern handled by the evaluation pass,
  not a document-parse-time `DocumentError`, so the rest of the sheet is unaffected.
- A component with no output ports connected to anything downstream still evaluates normally and
  keeps its computed value available (e.g. for a future "inspect value" affordance) — exactly like
  a spreadsheet cell nobody currently references is not an error.
- Dragging a wire's source press onto empty canvas (missed the terminal) or releasing over empty
  canvas simply does not create a wire; no partial/dangling wire state is ever persisted.
- Moving a component moves its drawn wires with it (the wire endpoints are computed from the live
  port positions each time the scene repaints), the same as any diagram-editor connector that
  tracks the boxes it connects.

## IP check
Pass, with one deliberate design choice called out for the manager (same move this project already
made once for the plot dialog, spec 005→006 under `docs/board/decisions.md`, 2026-10-28): the
*primary*, always-available way to create a wire in this spec is the generic modal "Connect…"
dialog (a plain list the user picks from, OK/Cancel — the same chrome already approved for specs
006/008), not a bespoke on-canvas gesture. The press-output-drag-to-input gesture is offered too,
but only because that exact terminal-to-terminal drag is a textbook convention shared across many
long-established, unrelated diagram-editor categories (flowchart editors, circuit/schematic
editors, UML/ER diagram editors) that predate and are independent of any single engineering-
calculation vendor — it is not a technique tied to the engineering-calculation-tool category the
way spec 005's inline chart-axis placeholder editing was (see the worked example in
`.claude/skills/ip-cleanroom/SKILL.md`). Because the dialog path alone is sufficient to exercise
every acceptance criterion and is fully keyboard-navigable, nothing in this spec *requires* the
drag gesture to exist; a manager uncomfortable with including it at all can drop it from phase W2
without losing any functionality, only convenience. Everything else — named input/output terminals
on a box's edge, a directed line between two terminals with an arrowhead, an error-coloured
connector, topological-order evaluation of a dependency graph (Kahn's algorithm, 1962), cycle
rejection at the moment a dependency is drawn (the spreadsheet circular-reference idea) — is
generic, decades-old and documented across control theory, software architecture and spreadsheet
design, never traced to one named commercial dataflow/wiring product's specific layout, icon set,
port-shape convention, colour coding or wiring gesture, per Theo's 2026-10-29 decision. No vendor
name, icon, file format, or literal keyword set appears anywhere in this spec. Not legal advice.

## Fits current architecture?
- **`livesheet/document.py`**:
  - `RegionData.kind` gains `"component"` as a fourth allowed value.
  - `RegionData` gains three fields used only when `kind == "component"`: `component_name: str`,
    `component_kind: str` (e.g. `"value"`, `"formula"` — this spec's two kinds only), and
    `config: dict[str, str]` (e.g. `{"expr": "12 m/s"}` or `{"inputs": "a,b", "expr": "a+b"}`). The
    existing `text` field is left empty/unused for component regions (kept only so the dataclass
    doesn't need a second constructor shape); `w`/`h` stay `None` (components auto-size, see above).
  - New `@dataclass WireData`: `from_component: str`, `from_port: str`, `to_component: str`,
    `to_port: str` (all plain strings, matched against `component_name`/port names at load/connect
    time, never Python object identity — so save/reload and renames stay simple).
  - `SheetDocument` gains `wires: list[WireData] = field(default_factory=list)`.
  - `SheetDocument.version()`: new `FORMAT_VERSION_COMPONENTS = 3`, returned when any region has
    `kind == "component"` or `wires` is non-empty; otherwise falls back to today's plot-or-not
    logic (`FORMAT_VERSION_PLOT = 2` / `FORMAT_VERSION = 1`) completely unchanged.
  - `SheetDocument.from_json`'s version guard (`int(data.get("version", 0)) >
    FORMAT_VERSION_PLOT`) is updated to compare against the new `FORMAT_VERSION_COMPONENTS`
    instead, so a version-3 file is the newest this build accepts; a version-1/2 file with no
    `"wires"` key simply yields `wires = []`, per the dangling-reference/lenient-load edge case
    above for anything that *is* present but stale.
  - `RegionData.__post_init__` keeps raising `DocumentError` for a genuinely unrecognised region
    *kind* string (structural validation); an unrecognised `component_kind` *value* inside an
    otherwise well-formed `"component"` region is explicitly **not** validated here — see the edge
    case above, it is a run-time evaluation concern.
- **New `livesheet/engine/wiring.py`** (engine-side, no PySide6 import, consistent with
  `engine/` being GUI-independent): the component/wire graph, Kahn's-algorithm topological sort
  with the reading-order tie-break, cycle detection (reused both at wire-creation time and as the
  defensive evaluation-time check), a `ComponentResult` dataclass (`status: str`, `error: str`,
  `outputs: dict[str, object]` — deliberately parallel to `RegionResult` in `engine/evaluator.py`
  but for a component's several named outputs instead of one printed line), and the two
  placeholder kinds' compute functions, each implemented as a thin wrapper around `Engine.parse`
  (imported from `engine/evaluator.py`) — no second expression parser.
- **`livesheet/engine/evaluator.py`**: unchanged. `Engine.evaluate` keeps its existing signature
  and behaviour; `wiring.py` imports and reuses `Engine.parse` but does not modify `Engine` itself
  (component evaluation builds its own small `env` dict per the "no sheet-variable visibility"
  rule above, rather than touching the `Engine.evaluate` reading-order pipeline).
- **`livesheet/gui/regions.py`**: new `ComponentRegion(Region)` — header (name + kind), auto-sized
  box, drawn input/output port terminals, reuses the existing `_has_error`/`COLOR_ERROR_BG`/
  `COLOR_ERROR` machinery already on the `Region` base class for its error state (no new colour
  constants).
- **`livesheet/gui/worksheet.py`**:
  - New `WireItem` (a plain `QGraphicsItem`/`QGraphicsPathItem`, not a `Region` subclass — it has no
    editable text and must not be picked up by `Worksheet.regions()`'s `isinstance(it, Region)`
    filter or by reading-order sorting) tracking its two endpoint ports and repainting its path from
    their live scene positions.
  - `Worksheet` gains `self._wires: list[WireItem]`, `try_connect(source_port, dest_port) ->
    str | None` (returns an error message on rejection, `None` on success — the one shared place the
    one-connection-per-input and no-cycle rules are enforced for both creation paths above), and
    wire/component removal hooked into the existing `remove_regions`/`_discard` machinery (deleting
    a `ComponentRegion` also discards its attached `WireItem`s).
  - `recalculate()` gains one new, additive step: build the current `(ComponentRegion, WireData)`
    picture from the scene, call `wiring.evaluate(components, wires)` (returns `dict[name,
    ComponentResult]`), and push each result onto its `ComponentRegion`'s error-state/tooltip the
    same way `MathRegion.set_result` already does — this runs in addition to, not instead of, the
    existing `self.engine.evaluate(...)` call for math/plot regions a few lines above it; when there
    are no `ComponentRegion`s this step is a no-op (empty list in, empty dict out), which is what
    guarantees acceptance criterion 1.
  - `to_document()`/`load_document()` extended to round-trip `ComponentRegion`s and `self._wires`
    through `RegionData`/`WireData`, alongside the existing math/text/plot handling already there.
- **New dialogs** (`livesheet/gui/componentdialog.py`, own module, same generic chrome as
  `plotdialog.py`/the matrix-grid dialog): "Add Component" (kind dropdown + kind-specific fields)
  and "Connect…" (a plain list of candidate ports). Both are ordinary modal `QDialog`s with
  labelled widgets, OK/Cancel — no new interaction style.
- **`livesheet/gui/main_window.py`**: one new "Insert > Component…" action opening the "Add
  Component" dialog at the crosshair, mirroring how "Insert > Plot" already works
  (`Worksheet.insert_region`/`_open_plot_dialog`). This spec does not otherwise touch main-window
  chrome (toolbars, side panel, status bar) — see Open questions for the one coordination point
  left for the manager/gui-specialist.
- Tests: a new `tests/test_wiring_core.py` (engine-level: graph building, topological order,
  tie-break, cycle rejection, the two placeholder kinds' compute functions, `ComponentResult`
  error states) plus GUI-level coverage in a new `tests/test_wiring_gui.py` or an extension of
  `tests/test_main_window_chrome.py` (component/wire creation via both paths, deletion cascading to
  wires, `.lsheet` round-trip of components+wires, the version-3-only-when-used rule) run headless
  under `QT_QPA_PLATFORM=offscreen` like the project's existing GUI tests. The tester should also
  do a real-window pass on Theo's Mac: place a couple of components, wire them both ways (drag and
  the Connect dialog), confirm the error-state colouring appears/clears live, try to make a cycle
  and see it rejected, delete a component and watch its wire disappear, save/reopen the file.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Components do not read/write ordinary sheet variables in this spec** — a "Value"/"Formula"
   component's inputs/outputs are visible only to other components via wires, not to math regions
   by name, and vice versa. This keeps the foundation small and avoids deciding a sheet-variable
   naming convention (e.g. `Comp1.value`) before backlog 32-34's real kinds exist to motivate one.
   [Recommend accepting for this spec; flag as the natural next follow-up once a real kind like
   CSV import (32) makes "use this component's output in an ordinary formula" clearly wanted.]
2. **gui-specialist coordination**: I tried to reach the gui-specialist agent directly to ask (a)
   whether "Insert > Component…" fits spec 007's existing Insert menu as-is or should wait for a
   dedicated chrome follow-up, and (b) whether the wiring canvas needs its own View-menu visibility
   toggle; the agent was not reachable when I tried. I made my own call for this spec (plain new
   Insert-menu entry, no new View toggle — wires always render, like region borders do today) but
   flag both as open for the manager/gui-specialist to revisit rather than treating my call as
   final.
3. **The optional drag-to-connect gesture** (see IP check): included here because it is a long-
   established, cross-category diagramming convention, but it is the one piece of this spec closest
   to "a live interaction technique drawn on the canvas," which ip-cleanroom flags for extra
   scrutiny. The spec is written so it can be dropped from phase W2 with zero loss of functionality
   (the Connect dialog alone covers every acceptance criterion) if the manager would rather ship
   phase W2 without it, at least initially. [Recommend keeping it — the generic, cross-category
   terminal-drag convention reads as materially lower risk than spec 005's chart-axis case — but
   flagging the easy fallback explicitly either way.]
4. **Component resizing**: left out of this spec (auto-size only, unlike `PlotRegion`'s resize
   handle) to keep phase W2 small. [Recommend a follow-up once a kind with genuinely variable-size
   content, e.g. backlog 32's CSV preview, makes resizing clearly useful; not needed for the
   mechanism itself.]
5. **Optional (non-required) input ports**: the port model above supports a `required` flag per
   input port, but neither placeholder kind in this spec actually uses `required = False` (both
   mark every input required), so the "optional input with a usable default and no error" behaviour
   is specified in the abstract but not exercised by any acceptance criterion here. [Recommend
   leaving it specified-but-untested for now; a future kind that genuinely wants an optional input
   with a default can exercise it without any format/mechanism change.]
6. **No further `.lsheet` format change expected for backlog 32-34**: this spec's `config: dict[str,
   str]` field and `component_kind` string are designed so CSV/Excel (32), a nested sub-sheet file
   reference (33) and a script source (34) can each be added as new `component_kind` values with
   their own `config` keys, without another `FORMAT_VERSION` bump. The one case I can't fully rule
   out without that spec existing yet is backlog 33's cross-file recursion/cycle detection (a nested
   `.lsheet` component whose own sub-sheet also contains wiring, or that embeds the parent file by
   path) — that may need something this spec doesn't anticipate (e.g. a path-resolution or
   recursion-depth rule). [Flagging now per the task's instruction to work out format implications
   explicitly, rather than silently assuming 33 will fit; recommend the modeling-specialist revisit
   this exact assumption when writing spec 33, and amend this note in decisions.md then if it
   doesn't hold.]
