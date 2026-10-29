# Review 009: component-and-wiring canvas core (tester, black-box)

Spec: docs/board/specs/009-component-wiring-core.md (backlog item 31), phases W1 (data model +
topological evaluation) and W2 (canvas drawing + dialogs). Commit under test: `288c307`
("Implement specs 006-009, calculus fixes C1-C4, and GUI polish"), already committed by the
manager before this review, per the task's own framing -- this is the independent review that was
always supposed to happen for this spec but was skipped because the implementing developer
session was interrupted before ever logging or requesting one. New files: `livesheet/engine/
wiring.py`, `livesheet/gui/componentdialog.py`; changed: `livesheet/document.py`,
`livesheet/gui/regions.py`, `livesheet/gui/worksheet.py`, `livesheet/gui/main_window.py`.
Developer's own tests: `tests/test_wiring_core.py` (26 tests, engine layer only -- see Coverage
gaps/Process note below, this is the one real gap this review found that isn't a code defect).

## Tests added

`tests/test_wiring_blackbox.py`: 54 cases, all pass. Written from spec 009's own acceptance
criteria 1-11 and Edge cases, using only the names the spec itself calls out (`ComponentSpec`,
`WireSpec`, `ComponentResult`, `topo_sort`, `has_cycle`, `would_create_cycle`, `evaluate`,
`known_kind`, `input_ports`, `output_ports`, `format_output`; `Worksheet.try_connect`;
`RegionData`'s `component_name`/`component_kind`/`config`; `SheetDocument.wires`;
`FORMAT_VERSION_COMPONENTS`; `AddComponentDialog`/`ConnectDialog`/`ComponentFields`/
`fields_to_config`/`validate_component_fields`). `tests/test_wiring_core.py` was read only after
drafting these cases, to check for coverage gaps, not consulted while writing them -- it turned
out to cover a different half of the spec almost entirely (see Process note).

Deliberately different exercise paths vs. the developer's own tests:
- Criteria 5-6 (one-connection-per-input, fan-out, cycle rejection) are exercised through the
  real, end-to-end GUI path (`Worksheet.try_connect` on real `ComponentRegion` scene items), not
  only the engine-level `wiring.would_create_cycle` helper in isolation (also checked separately).
- Criterion 7 and the "deleting a wire leaves the components alone" edge case go through
  `Worksheet.remove_regions`/the real `keyPressEvent` Delete-key path on a selected `WireItem`,
  not a direct `_wires.remove(...)` call.
- Both wire-creation paths (drag-to-connect and the "Connect..." dialog) are driven through the
  real `Worksheet.mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent`/`contextMenuEvent`
  handlers via minimal event stand-ins (a real `QGraphicsSceneMouseEvent` for mouse events, so a
  fall-through to Qt's own default handling also works; the same `QTimer.singleShot`-inside-the-
  nested-event-loop technique already used by `tests/test_matrix_dialog_blackbox.py` for the real,
  unpatched `QMenu.exec()` call) -- not by calling the private `_begin_wire_drag`/
  `_open_connect_dialog` helpers directly.
- The format round-trip (criterion 10) and the version-gating regression (criterion 11 -- the
  exact area the manager found and a developer already fixed once) are re-verified independently:
  a real `Worksheet.to_document()`/`SheetDocument.save()`/`.load()`/`Worksheet.load_document()`
  cycle through an actual temp file, a direct check that a component-free document's JSON has no
  top-level `"wires"` key at all, and a from-scratch check that a bare declared `version: 3` with
  no component/wire content is rejected -- not trusting the fix report, re-deriving it from the
  spec's own wording.
- Two tests re-check "components do not read/write ordinary sheet variables" (accepted open
  question 1) at the real `Worksheet.recalculate()` level in both directions (a component cannot
  see a math region's variable; a math region cannot see a component's output by name), not only
  at the engine layer the developer's own tests already covered.
- The "Insert > Component..." entry and both dialogs are exercised through a real `MainWindow`/
  `QAction` lookup by menu text and real `QDialog` widgets with field text set directly, mirroring
  how prior reviews (006/007/008) checked their own menu entries and dialogs.

Coverage: all 11 acceptance criteria, plus: fan-out from one output to several inputs; a
self-loop and a two-node cycle rejected both at the data-model level (`would_create_cycle`
directly) and end-to-end through `Worksheet.try_connect`; the reading-order tie-break confirmed
both independent of a real dependency edge and *subordinate* to one (a wired dependency always
wins over canvas position); a dangling wire reference, duplicate component names, and an
unrecognised `component_kind` all handled per the spec's edge cases on load; dragging onto empty
canvas; a moved component's wire endpoints tracking it live; a wire's colour switching to the
error colour and back as its destination's error state changes; drag-to-connect confirmed to only
start from an output port, never an input; PDF export with components+wires present not crashing;
`ComponentRegion`'s use of the ordinary `Region` selection/deletion mechanics and `WireItem`'s
correct exclusion from `regions()`/`ordered_regions()`; the "Connect..." dialog's own candidate
list and empty-candidate-disables-OK behaviour; `AddComponentDialog`/`validate_component_fields`/
`fields_to_config` for both kinds, including every validation message.

## Results

Baseline (`QT_QPA_PLATFORM=offscreen pytest -q` from a clean shell, matching commit `288c307`):
**1065 passed, 2 xfailed, 0 failed**, as reported by the manager. After adding
`tests/test_wiring_blackbox.py`: **1119 passed, 2 xfailed, 0 failed** (1065 + 54 new, no
regressions, no new xfails), stable across three consecutive full-suite runs.

Environment note (not a code defect, matches a hazard already logged several times in
`docs/board/log.md`): mid-session, every PySide6 GUI test (including pre-existing, unrelated
ones) started hard-aborting the interpreter at `QApplication([])` construction with a fatal
`qt.qpa.fonts`-adjacent abort inside `createPlatformIntegration`, reproducible even by re-running
an already-passing, unrelated test file alone. No concurrent `pip`/reinstall process was visible
via `ps aux` and the Qt dylib mtimes were not changing, so this was not an active reinstall race
this time, just the same previously-logged opaque Qt-platform-plugin-loader state going bad
mid-session. Recreating `.venv` from scratch (the project's own documented setup command) fixed it
immediately, consistent with every prior session that hit this -- a targeted reinstall has never
been reported to fix it, only a full recreation. Flagging again since this is now the fourth or
fifth independent session to hit this exact symptom in this shared sandbox.

## Acceptance criteria

1. PASS. `wiring.evaluate([], [], engine) == {}` directly, and a real `Worksheet.recalculate()`
   on a component-free sheet folds exactly 0 components into `evaluationFinished`'s total and
   leaves `component_regions()`/`_wires` empty.
2. PASS. A "Value" component with `expr = "12 m/s"` evaluates to a measured `12 m/s` (magnitude
   and base dimensions cross-checked independently via `measure()`, not just string comparison);
   not in an error state.
3. PASS. `F1` (`a, b` inputs, `expr = "a + b"`) wired only `V1.value -> F1.a`: error state, exact
   message `"Input 'b' is not connected."`, no `result` output present.
4. PASS. Wiring `V2.value -> F1.b` as well clears the error; `result` evaluates to `15 m/s`
   (12 + 3, cross-checked via `measure()`).
5. PASS. Wiring `V2.value` into the already-connected `F1.a` is rejected with the exact message
   `"Input 'a' on F1 is already connected — disconnect it first."`; the existing `V1 -> F1.a` wire
   is confirmed unchanged (same `WireItem`, same source) afterward. Fan-out (one output to many
   inputs) confirmed fine as a separate, explicit edge case.
6. PASS. Both the self-loop case (`F1.result -> F1.a` on itself) and the two-node case
   (`F2.result -> F1`'s input after `F1 -> F2` already exists) are rejected with the exact message
   `"This connection would create a circular dependency."`, at both the data-model level
   (`would_create_cycle`) and end-to-end through `Worksheet.try_connect`; no wire is created either
   way, confirmed by wire count before/after.
7. PASS. Deleting `V1` removes the `V1 -> F1.a` wire with it (confirmed via `remove_regions`);
   `F1` returns to the error state `"Input 'a' is not connected."`; an unrelated `V2 -> F1.b` wire
   is confirmed to survive untouched.
8. PASS. `a = 1 m, b = 1 s, expr = "a + b"` gives the exact error text `"Units do not match"` --
   cross-checked to be byte-identical to what a plain math region `1 m + 1 s =` produces through
   `Engine.evaluate` directly, and to what `measure()`/`UnitError` raise on their own, confirming
   no separate component-specific error-text path exists.
9. PASS. `topo_sort` with two independent (no-wire) components gives the component placed higher
   on the canvas first; swapping their `(y, x)` positions swaps only the tie-broken order, confirmed
   deterministic across repeated calls with identical input. A second check confirms the tie-break
   never overrides a real dependency edge (the upstream node always comes first even when drawn
   below its downstream node) -- the tie-break only applies between otherwise-unordered nodes, per
   the spec's own wording.
10. PASS. `V1`, `V2`, `F1` and both their wires survive an actual `to_document()` ->
    `SheetDocument.save()` -> `.load()` -> `Worksheet.load_document()` round trip through a real
    temp file; `F1.result` evaluates to `15 m/s` with no further action. A second, stronger check
    confirms a second save/load cycle on the already-reloaded sheet produces byte-identical
    `regions`/`wires` JSON (no drift from re-serializing a loaded sheet).
11. PASS, **including the exact regression area the manager found and a developer already
    fixed once** -- re-verified from scratch rather than trusted: a version-1 file with no
    `"wires"` key loads with `wires == []`; a component-free sheet (with or without a plot) writes
    version 1/2 exactly as before, with no top-level `"wires"` key and no `component_name`/
    `component_kind`/`config` keys on any region; a sheet with a component (even with zero wires)
    writes version 3 but still omits the empty `"wires"` key; a sheet with an actual wire writes
    version 3 with that wire present; a *declared* version 3 with no component/wire content in the
    file is rejected the same way a too-new version always has been (`"This file was made with a
    newer LiveSheet version"`); a genuine version-3 file with a real component loads fine.

## Edge cases

All PASS: a zero-wire "Value" simply evaluates, a zero-wire "Formula" shows the unconnected-input
error for its first unmet required input; a wire naming a component/port that no longer exists is
silently dropped on load (confirmed via a hand-built `SheetDocument` with a dangling `WireData`,
no exception, zero wires created); two components sharing a name on load are disambiguated to
`"Comp1"`/`"Comp1 (2)"`; a region with an unrecognised `component_kind` loads without a
`DocumentError`, survives with its name/kind/config/wires intact, and shows `"Unknown component
kind '...'."`  only at evaluation time; a component with no downstream wiring still evaluates and
keeps its value (`status == "ok"`); dragging from an output port and releasing over empty canvas
creates no wire and leaves `_wire_drag` cleared; moving a component updates only the endpoint on
its side of each attached wire, confirmed by comparing `WireItem.endpoints()` before/after a
`moved` signal; a wire's pen colour switches to `COLOR_ERROR` the instant its destination enters
the error state and back to `COLOR_FRAME` once the error clears.

## Defects

**D1 (moderate) -- the "Connect…" dialog is reachable only via a right-click precisely on a port
terminal; no keyboard-reachable toolbar/menu alternative exists, contradicting the spec's own
"fully keyboard-navigable" claim for this path.**

Spec text (Behaviour > Wires, path 2): *"right-click a port (**or use a "Connect…" toolbar/menu
action with a component selected**)* to open a small modal dialog ... **This path needs no
dragging at all and is fully keyboard-navigable.**" The spec names two alternative trigger
mechanisms for the same dialog and explicitly frames the whole point of including this path as
accessibility/keyboard-navigability (also echoed in the IP check: *"a generic, keyboard-reachable
dialog rather than requiring any particular pointer gesture, for accessibility"*).

Actual: `Worksheet.contextMenuEvent` only offers the `"Connect…"` action when the right-click
`scenePos()` lands within `ComponentRegion.port_at()`'s 7-pixel tolerance of an actual port
terminal (`livesheet/gui/worksheet.py`, `port_hit = region.port_at(...)` then `menu.addAction("Connect…") if port_hit is not None else None`). There is no second trigger anywhere else: no
`"Connect…"`/`"Connect"`-named `QAction` exists in any menu or toolbar in `main_window.py` (grepped
and confirmed via `findChildren`), and no "with a component selected" variant exists either --
selecting a whole `ComponentRegion` and right-clicking its body (not its exact port pixel) shows
only `"Plot here"`, never `"Connect…"`.

Practical consequence: reaching the dialog requires a mouse precise enough to land within ~7px of
a port terminal; there is no way to open it from the keyboard alone (Qt's keyboard-triggered
context-menu event, e.g. Shift+F10/Menu key, does not reliably land on a specific small terminal
either). This does not block any acceptance criterion (all 11 are satisfiable via the drag gesture
or by constructing/driving `ConnectDialog` directly, which is how both the developer's and this
review's own tests exercise it), but it is a genuine gap against the spec's own explicit wording
and its own stated accessibility rationale for including this path at all.

Minimal repro (headless, `QT_QPA_PLATFORM=offscreen`):
```python
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
app = QApplication.instance() or QApplication([])
from livesheet.gui.worksheet import Worksheet

sheet = Worksheet()
v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))

class FakeEvent:
    def __init__(self, pos): self._pos = pos
    def accept(self): pass
    def scenePos(self): return self._pos
    def screenPos(self):
        from PySide6.QtCore import QPoint
        return QPoint(0, 0)

# Right-click the component's own body, NOT its tiny port terminal:
body_centre = v.mapToScene(v.boundingRect().center())
# -> contextMenuEvent's menu never contains "Connect…" here, and there is no other way to
#    reach ConnectDialog without a mouse precise enough to hit the ~7px port terminal.
```
Reproduced in `tests/test_wiring_blackbox.py::test_connect_action_only_appears_when_right_click_lands_on_a_port_terminal`
and `::test_no_toolbar_or_menu_action_offers_connect_with_a_component_merely_selected` (both pass
as *confirmations of the gap*, not xfails, since nothing here crashes or contradicts a numbered
acceptance criterion -- they document the behaviour for the manager to decide whether to assign a
fix).

Suggested fix for the developer (not applied by this review, per instruction): add a "Connect…"
entry to a component's own right-click menu whenever a `ComponentRegion` (not just a bare port hit)
is right-clicked and has at least one port, defaulting to its first output (or first input) port,
mirroring how `"Edit as grid..."` (spec 008) is offered for a whole `MathRegion` rather than
requiring a pixel-precise hit; alternatively/additionally, an `Edit`/`Insert`-menu `"Connect…"`
action enabled only when exactly one `ComponentRegion` is selected, matching the spec's own
"toolbar/menu action with a component selected" wording literally.

## Process note (not a code defect, but a real coverage gap in the developer's own deliverable)

The spec's own "Fits current architecture?" section explicitly calls for *"GUI-level coverage in a
new `tests/test_wiring_gui.py` or an extension of `tests/test_main_window_chrome.py` (component/
wire creation via both paths, deletion cascading to wires, `.lsheet` round-trip of components+
wires, the version-3-only-when-used rule)"*, in addition to the engine-level `tests/
test_wiring_core.py`. Only the latter exists: `tests/test_wiring_core.py` has 26 tests, all at the
Qt-free `livesheet/engine/wiring.py` layer (ports, topo sort, cycle detection, the two kinds'
compute functions, error states) -- genuinely thorough for that layer, including good cases this
review also independently re-derived (division-by-zero, syntax errors, the two "components don't
see sheet variables" directions). There is no `tests/test_wiring_gui.py`, and grepping every other
test file in `tests/` for `Component`/`wiring`/`WireItem`/`ComponentRegion` turns up nothing
relevant either. Before this review, **zero automated tests existed anywhere for the entire phase
W2 GUI surface** -- `componentdialog.py`, `ComponentRegion`'s canvas drawing, `Worksheet.
try_connect`/drag-to-connect/`contextMenuEvent`'s `"Connect…"` entry, the `.lsheet` round-trip
through the real `Worksheet`, and the `"Insert > Component…"` menu entry. This is consistent with
the task's own framing (a developer session interrupted before it was ever logged, let alone
reviewed) -- the W2 half of the developer's own test-writing task appears to simply not have
happened yet. `tests/test_wiring_blackbox.py` (this review) now covers that surface independently,
but the project's normal process expects the *developer* to also leave their own GUI-level
regression tests behind; recommend the manager assign a short follow-up to the developer to add
`tests/test_wiring_gui.py` per the spec's own instruction, independent of whether D1 above also
gets fixed in the same pass.

## IP red flags

None found. Grepped `livesheet/engine/wiring.py`, `livesheet/gui/componentdialog.py`, and the
touched parts of `livesheet/gui/regions.py`/`livesheet/gui/worksheet.py`/`livesheet/gui/
main_window.py` for vendor names (including the specific tools named only in the spec's own "clean
room" paragraph) and found none. All field/button/menu wording (`"Add Component"`, `"Connect…"`,
`"Kind:"`, `"Name:"`, `"Expression:"`, `"Input names (comma-separated):"`, `"No compatible ports
available."`, `"&Component…"`) and error strings (`"Input '...' is not connected."`, `"Input '...'
on ... is already connected — disconnect it first."`, `"This connection would create a circular
dependency."`, `"Part of a circular connection; this wire needs to be removed."`, `"Unknown
component kind '...'."`, `"Name is required"`, `"At least one input name is required"`, `"Input
names must be unique"`) are original and generic, consistent with the spec's own IP check. No
icon/asset files are used anywhere in the new code (every port is drawn with `QPainter.
drawEllipse`/`drawText`, no `QIcon`/`.png`/`.svg`), matching the spec's claim that no vendor icon
set was used. The port/wire visual language described in the spec (named terminals at a box's left/
right edge, a directed line with an arrowhead, an error-coloured connector reusing the existing
`COLOR_ERROR`) is implemented exactly as described and does not go beyond it -- no extra visual
flourish (e.g. no connector-routing style, no custom cursor, no port-shape coding) was added beyond
what the spec's own IP check already assessed as generic/decades-old. One pre-existing item **not
introduced by this spec**, already fixed before this spec's work started (confirmed in
`docs/board/log.md`, 2026-10-29): the `Crosshair` class's former `"Mathcad style"` docstring in
`livesheet/gui/worksheet.py` -- re-checked here and confirmed it now reads `"Red insertion cross
marking where the next region will be placed."`, no regression.

## Coverage gaps

- **No real-window/computer-use pass this session**, per the task's own instruction that this is
  a standing, expected gap right now -- not pursued further. Everything above was verified
  headlessly (`QT_QPA_PLATFORM=offscreen`) through Qt's own programmatic event-dispatch APIs
  (direct `contextMenuEvent`/`mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent`/
  `keyPressEvent` calls with real or minimal stand-in event objects), which exercises the same
  production code a real mouse/keyboard interaction would reach, but is not the same as watching
  it on screen. A real pass should still cover: placing a component via `Insert > Component…`;
  connecting two components both by dragging an output port to an input port and via the
  right-click `"Connect…"` dialog; watching the error-colouring (both the box's fill and its wires)
  appear/clear live as inputs are wired/unwired; attempting a cycle and seeing the rejection
  message; deleting a component and watching its wires disappear with it; save/reload through the
  real File menu.
- The exact pixel size of the port-hit tolerance (7px, `ComponentRegion.port_at`'s default) was
  exercised functionally (hits within it work, a click on the body elsewhere does not) but not
  measured against what a real trackpad/mouse click precision would feel like in practice -- this
  is the same territory as Defect D1 above.
- Keyboard-only Tab-order navigation across the two dialogs' fields was not separately exercised;
  both are ordinary `QFormLayout`/`QListWidget` chrome, same reasoning as prior reviews (006/007/
  008) for not re-testing Qt's own default Tab order.
- `format_output` (named in the spec's own "Fits current architecture?" list and exercised
  directly in this review and the developer's own tests) is not currently called anywhere in the
  GUI -- `ComponentRegion.paint()` draws ports and labels but never a computed value on the box
  itself. This matches the spec's own edge case ("kept available ... for a future 'inspect value'
  affordance") rather than being a defect, but is worth noting as intentionally-unused
  infrastructure rather than dead code, in case a future reviewer wonders why it exists.
- Visual rendering correctness (exact pixel layout of the box/port labels/summary line, whether
  long port names or long config summaries overlap anything) was exercised only at the geometry/
  state level (`boundingRect()`, `_box_w`/`_box_h`, label margins), not by rendering to an image
  and inspecting pixels the way review 007 did for the empty-canvas hint; this spec's own text
  explicitly defers a resizable/overflow-aware layout to a later spec, so this is a lower-priority
  gap than the others above.

## Recommendation

Spec 009 is functionally sound: all 11 acceptance criteria plus every edge case hold exactly as
specified under independent black-box testing (`tests/test_wiring_blackbox.py`, 54 cases), the
format-version regression the manager found is confirmed properly fixed when re-derived from
scratch rather than trusted, and the full suite is stable at 1119 passed / 2 xfailed / 0 failed
(1065 baseline + 54 new, three consecutive runs). One real defect was found (D1: the "Connect…"
dialog's only trigger is a pixel-precise right-click on a port terminal, with no keyboard-reachable
toolbar/menu alternative despite the spec's explicit wording and accessibility rationale for this
path) -- not a blocker for any numbered criterion, but a genuine spec-vs-implementation gap worth
a small developer follow-up. Separately, and arguably more important for the project's process
going forward: the developer's own GUI-level test suite for this spec (`tests/test_wiring_gui.py`,
explicitly called for in the spec's own architecture section) was never written, so before this
review the entire W2 GUI surface had zero automated coverage of its own -- recommend the manager
assign that follow-up alongside D1. No IP red flags found in the new/changed code. A real-window
manual pass is still needed before calling spec 009 fully verified end-to-end, per the project's
standing testing rule; not pursued this session per the task's own instruction that no computer_*
tool is expected to be available right now.
