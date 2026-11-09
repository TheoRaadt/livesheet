# 023 Drag-to-move regions (single and multi-selection), nudging, cancel

Source inspiration: generic, cross-application direct-manipulation conventions (press-drag moves
the selected object, a small movement threshold separates a click from a drag, Escape cancels an
in-flight drag, arrow keys as the keyboard alternative to dragging, open/closed hand cursors).
Public general guidance consulted for the conventions: W3C WAI-ARIA Authoring Practices (keyboard
alternatives and Escape-to-cancel conventions, https://www.w3.org/WAI/ARIA/apg/, 2026-11-09,
concept only; the drag-and-drop pattern page itself returned 404 so only the general site
principles were used). No product's docs, layout or wording were read; this is Theo's own request
(2026-11-09).

User story: as a LiveSheet user I can select one or more regions on the canvas and drag them to a
new place with the mouse, see where they will land (snapped to the dotted grid), cancel with Esc,
nudge them with the arrow keys, and watch the results update live, including when the move
changes which region is evaluated first.

## Current state (read from the code, 2026-11-09)
- Regions (livesheet/gui/regions.py, `Region`) already carry `ItemIsMovable | ItemIsSelectable |
  ItemSendsGeometryChanges`; `Region.itemChange` snaps every position to GRID = 10 and clamps to
  x, y >= 0; `moved` is emitted on each position change and `Worksheet._on_moved` marks modified,
  schedules a recalculation (200 ms debounce), grows the scene rect and re-syncs wires.
- The help text in main_window.py already says "drag to move", the arrow keys already nudge the
  selection by one grid cell (`Worksheet.keyPressEvent`), and the view has a rubber-band
  selection (`WorksheetView`, `RubberBandDrag`) for multi-selection; Select All Regions exists.
- Evaluation order (spec 021, shipped): `Worksheet.ordered_regions()` sorts by
  `order_key(x, y, page_breaks)` then creation sequence, using each region's LIVE `pos()`.
  Wires follow their components (`WireItem.sync`). Page-break markers are not draggable.
- .lsheet already stores every region's `x`, `y` (RegionData); `to_document()` writes regions in
  evaluation order. No file-format change is needed.
- There is NO undo/redo (backlog 4 still open; backlog 43 raised its priority; docs/manual/pages.md
  tells users there is no undo).
- Theo reports that, despite the above, dragging a selected region does not move it. The cause
  is not established (see "Step 0").

## Step 0: reproduce and diagnose first (developer, before any design change)
Write a failing headless test that sends a real press/move/release to the view's viewport
(`QTest.mousePress/mouseMove/mouseRelease` on `WorksheetView.viewport()`, not direct
`setPos`) on a non-editing, selected MathRegion, and record in the spec's review/log note WHY it
does not move today (candidates to check: the scene's `mousePressEvent` early paths in
worksheet.py; the view's rubber-band mode swallowing the press; a child item such as the editor or
result item accepting the press; `itemChange` returning a position that cancels small
incremental moves; focus/editing state left over from the last edit). The behaviour below is
required regardless of the cause. If the cause is a one-line bug, still deliver everything below
that is not already true (Esc-cancel, group clamp, cursor, grip while editing, batching, tests).

## Behaviour (own words)

### Modes: move versus edit
- A region is in exactly one of two states, as today: not editing (shown, can be selected and
  moved) or editing (caret in its text, drawn with the solid frame and tinted background).
- Not editing: press anywhere on the region body (text, result, padding) starts a potential
  move. A plain click without moving selects it (no change to the document, no modified flag). A
  double-click or Enter on a single selected region starts editing, exactly as today.
- Editing: a press inside the text area places/extends the caret and never moves the region
  (typing and text selection by mouse keep working untouched). The region's frame is the move
  grip: the ring formed by the existing 3-unit padding plus 3 units just outside it. Press-drag on
  that ring moves the region and leaves it in editing mode with its text and caret intact. The
  hit area may be widened by up to 3 units (boundingRect/shape) while editing; it must not
  change the region's saved size or layout.
- Priority of existing press targets is unchanged and wins over "move": a plot region's resize
  handle resizes; a component's output-port terminal starts a wire drag (spec 009); a press on
  empty canvas still sets the crosshair and starts the rubber band. Page-break markers are never
  moved or included in a move (if a marker is part of the selection it stays put).

### Selection to move
- Unselected region pressed: it becomes the selection (other selection cleared) and is the
  dragged item. Modifier-click selection toggling is whatever the toolkit does today; do not
  change it.
- Pressed region already a member of a multi-selection: dragging moves ALL selected regions
  (math, text, plot and component regions together) by the same displacement, keeping their
  relative layout.
- Rubber band and Select All Regions produce multi-selections; the move works on those.

### The gesture
1. Press on a movable target records the start position of every region to be moved.
2. A drag starts only after the pointer has moved at least 4 screen pixels from the press point
   (zoom independent: compare in view pixels). Below that it is a click.
3. While dragging, the displacement is measured in scene units (so at 200 % zoom a 100 px drag is
   50 units). The pressed ("primary") region's new position is
   `snap(start + displacement)` per axis (the existing GRID = 10 snap, same dotted grid as
   today). Every other region in the move gets the SAME snapped displacement as the primary
   (new = start + snapped delta), so a group keeps its exact internal spacing even if the
   starting positions were not multiples of 10 (hand-edited files).
4. Clamp: no region may end at x < 0 or y < 0. For a group the displacement is clamped as a whole
   (the most-constrained member decides), so the group never distorts at the canvas edge.
5. The regions follow the pointer live (they are really moved each step, not shown as ghosts), so
   the dotted-grid snap is visible as stepping. The primary region is kept inside the visible
   viewport: when the pointer is within about 24 view pixels of an edge the view scrolls to keep
   it visible (`ensureVisible` with a margin is enough; no timer-driven auto-scroll needed).
6. Release commits: positions stay; the sheet is marked modified only if at least one region
   actually ended at a different position than it started; a recalculation runs immediately
   (synchronously, not after the debounce).
7. Esc while the mouse button is still held cancels: every region returns to its start position,
   the modified flag returns to what it was at press time, one recalculation restores the
   original results, and the rest of that press/drag/release produces no move. Esc when no drag
   is in progress keeps today's behaviour (leaves editing). Losing the mouse grab or the window
   losing focus mid-drag is treated as Esc.

### Cursor feedback
- Hovering a movable non-editing region body, or the grip ring of an editing region: open hand.
- During a drag: closed hand (also while the pointer is outside the region).
- Editing region text area: the text (I-beam) cursor. Empty canvas, plot resize handle and port
  terminals keep whatever cursor they have today (the move cursors must not appear there).
- Restore the normal cursor when the hover ends, the drag ends or is cancelled, or the region is
  deleted.

### Live evaluation and evaluation order
- While dragging, `_on_moved` side effects are BATCHED: one notification per mouse-move event for
  the whole group (one scene-rect update, one wire re-sync, one recalc request), not one per
  moved region, so moving 200 regions stays smooth. Recalculation during the drag uses the
  existing 200 ms debounce; results visibly refresh whenever the pointer pauses and always on
  release.
- No engine change. The order is simply recomputed from live positions: left to right, then top
  to bottom within a page (`order_key`, spec 021), ties by creation sequence. A region dragged
  left past a region it depends on will show that region's "not defined" error after the next
  recalculation; dragging it back clears it. Components keep the wiring graph as primary order;
  their wires redraw to the ports' new positions at every step.
- Page breaks (spec 021): page membership follows the anchor (top-left) of each region at its
  live position. Dragging across a break line is free: it moves nothing else, does not snap to a
  page, and gives no warning; after the move the region simply belongs to the other page for
  ordering. The break marker stays where it is.

### Keyboard nudge (the keyboard alternative to dragging)
- Arrow keys with one or more regions selected and none editing: move the whole selection by one
  grid cell (10 units) in that direction. Shift+arrow: by 5 cells (50 units). With nothing
  selected the arrows move the crosshair, as today (Shift+arrow there: also 50 units).
- Group clamp as in the drag: if any member would cross x or y = 0, the whole selection does not
  move on that axis. (Today each region clamps alone and a group distorts; this is a fix.)
- A key press is one move: it recalculates (debounced) and marks modified. Held-key repeat is
  fine. A nudge that changes nothing (clamped) does not set modified.
- Esc has no meaning for a nudge (it is already committed).

### Undo status
There is no undo. This slice does not add it, but MUST be undo-ready: the commit goes through a
single Worksheet method, e.g. `move_regions(moves)` where `moves` is a list of
(region, old_pos, new_pos), called exactly once per completed drag and once per nudge key press,
so backlog 4 can wrap each call as one undo step without touching the gesture code. Esc-cancel is
the only safety net during a drag; Save beforehand is the safety net after. Manual page
docs/manual/pages.md's "no undo" sentence stays true.

## Syntax proposal (own keywords)
None. No statement grammar change.

## .lsheet file format impact
None. Region `x`/`y` are already stored. No version bump. Files saved before this feature load
exactly as before (positions snapped on load by `add_region`, as today). After a move, on-disk
region order may differ because `to_document()` writes regions in evaluation order; that already
means "evaluation order" and is backward compatible.

## Acceptance criteria
Headless (`QT_QPA_PLATFORM=offscreen`), view at zoom 1.0 unless stated, positions in scene units,
real mouse events sent to `WorksheetView.viewport()` via QTest. Region R is a MathRegion
`a := 1` at (100, 100), not editing, unselected.

D1. Basic move. Press inside R, move by (+53, +27), release: R.pos() == (150, 130) (snap of
    153, 127). R is selected, `ws.modified` is True, results are current without waiting.
D2. Click is not a drag. Press, move 2 view pixels, release: R.pos() == (100, 100), R is
    selected, `ws.modified` is False.
D3. Clamp. Drag R by (-500, -500): R.pos() == (0, 0). Dragging by (-500, +30): (0, 130).
D4. Live order. P = `a := 1` at (300, 50); Q = `a =` at (10, 200). Q is first (x = 10) and
    shows "a is not defined". Drag P to (10, 100) (same x as Q, smaller y): after release Q shows
    `= 1` without any extra wait. Dragging P back to (300, 50) restores the error.
D5. Multi-selection. R1 (100, 100) and R2 (200, 150) both selected; drag R1 by (+40, +20):
    R1 == (140, 120), R2 == (240, 170). Group clamp: R1 (10, 10), R2 (200, 150), drag by
    (-100, -100): R1 == (0, 0), R2 == (190, 140) (offsets preserved).
D6. Mixed kinds. A selected TextRegion, PlotRegion and ComponentRegion move together with a math
    region by the same displacement; a selected page-break marker does not move.
D7. Esc cancels. Press on R, move to (+80, +60) (R is visibly at (180, 160) mid-drag), send Esc:
    R.pos() == (100, 100), `ws.modified` equals its value before the press, results equal the
    original; the following mouse move and release leave R at (100, 100). Esc with no drag in
    progress while R is editing still leaves editing as before.
D8. Page break. page_breaks = [1220]; drag R from (10, 100) to (10, 1300): no other region and no
    marker moves; R now sorts after every page-1 region (order_key page 1). Positions of R and
    other regions are otherwise unchanged.
D9. Edit versus move. R in editing mode with text `a := 1`: a press in the text area at the
    caret position and a drag selects text and leaves R.pos() == (100, 100) and `editing` True. A
    press on the frame ring (e.g. 2 units outside the padding) and a drag by (+30, +20) moves R to
    (130, 120); afterwards `R.editing` is True, `R.source == "a := 1"` and the caret is still in the
    editor.
D10. Priorities. Press on a PlotRegion's resize handle resizes it and does not move it; press on a
     ComponentRegion's output-port terminal starts the wire drag and does not move the component;
     press on empty canvas starts a rubber band and moves nothing.
D11. Zoom. With `set_zoom(2.0)` a drag of 100 view pixels moves R by 50 scene units (x: 100 ->
     150).
D12. Nudge. R selected, not editing: Right -> (110, 100); Shift+Down -> (110, 150); Left at x = 0
     leaves x at 0 and does not set modified. Group at the edge: R1 (0, 100), R2 (50, 100) both
     selected, Left: both unchanged (no distortion); Right: (10, 100) and (60, 100).
D13. Wires. Component C wired to D: after each simulated mouse-move step of dragging C,
     `WireItem.endpoints()` equals the ports' current scene positions.
D14. Batching. A selection of 200 math regions dragged with 5 mouse-move events calls the scene's
     per-move side effects (`_update_rect`, `_sync_all_wires`, `schedule_recalc`) exactly 5
     times, not 1000.
D15. Cursor (offscreen may not render cursors; assert on `viewport().cursor().shape()` where the
     platform plugin supports it, otherwise manual check): open hand over R; closed hand during
     the drag; arrow again after release.
D16. File round trip. After D1, `to_document()` has R at x == 150, y == 130, same FORMAT
     version as before; saving and reloading yields R.pos() == (150, 130). A pre-existing sample
     file (examples/demo.lsheet) loads and re-saves with unchanged positions.
D17. Undo-readiness. A spy on `Worksheet.move_regions` sees exactly 1 call for D1, exactly 1 for a
     multi-selection drag, 1 per nudge key press, 0 for a click (D2) and 0 for a cancelled drag
     (D7).

## Edge cases
- Region deleted or sheet cleared/loaded mid-drag: drag state is dropped silently.
- Drag started while another region is editing: that region's editing is finished first (as the
  scene already does on press) and the press then proceeds against the target.
- Result text or plot images are part of the region body for hit-testing; tall results are not
  special-cased.
- Two regions dropped on exactly the same position: allowed; ordered by creation sequence
  (spec 021).
- Hand-edited files with positions off the grid: they are snapped on load; a group move keeps
  the loaded (snapped) relative offsets.
- Right button / middle button never start a move (context menu stays as is).
- Scene rect growth while dragging right/down is automatic through the existing `_update_rect`.

## IP check: pass
Press-drag to move a selected object, a drag threshold, Esc to cancel, arrow keys as a keyboard
alternative and open/closed hand cursors are universal graphical-editor conventions, in use since
the 1980s across drawing tools, file managers, desktop shells and every GUI toolkit's own
guidelines; nothing here is specific to the engineering-worksheet product category and nothing
was taken from a named product. The behaviour is on-canvas direct manipulation of LiveSheet's own
regions only, not "live placeholder editing on a chart" (ip-cleanroom rule 6): no input slot is
drawn on a plot. No new dependency, no assets, no vendor name. No patent-sensitive technique
identified.

## Fits current architecture?
- livesheet/gui/regions.py: `Region` gains the grip/hover/cursor logic and delegates the press /
  move / release to the scene; consider dropping `ItemIsMovable` in favour of the scene-driven
  move (needed for Esc-cancel and for the group-wide clamp and batching) while keeping
  `itemChange`'s snap/clamp for programmatic `setPos`. Programmatic `moveBy`/`setPos` (page-break
  reflow, loading) must keep working unchanged.
- livesheet/gui/worksheet.py: `mousePressEvent/mouseMoveEvent/mouseReleaseEvent/keyPressEvent`
  (move session, Esc, group-clamped nudge, Shift+arrow), new `move_regions()` commit method,
  batching flag around `_on_moved`.
- livesheet/gui/plotregion.py: resize-handle priority must be preserved (its own press override
  must still run first).
- livesheet/gui/main_window.py: help text only if wording changes (Shift+arrow).
- No change in livesheet/engine/, livesheet/document.py or the file format.

## Open questions (for Theo / manager)
1. Is the root cause of "cannot drag" known to Theo (e.g. only after typing, only on macOS
   trackpad, only on results)? Step 0 will find it; any detail helps.
2. Undo (backlog 4/43): fine to ship drag-move without it (Esc during the drag only), or pull
   undo ahead? The spec is undo-ready either way.
3. Shift+arrow = 50 units and the 4-pixel drag threshold are my picks; acceptable?
4. No free (un-snapped) placement, not even with a modifier key: everything stays on the 10-unit
   grid, consistent with the rest of the app. Confirm.
5. Editing-mode grip is a thin ring (6 units). Acceptable, or should an editing region get an
   explicit small drag handle? (I chose the ring: no new chrome.)

## Step 0 result (developer, 2026-11-09)
Plain press-drag with QTest on a selected or unselected, non-editing region DID move it (the stock
`ItemIsMovable` path works), so it was not a hit-testing, rubber-band or `itemChange` snap bug.
Root cause, reproduced with Theo's exact sequence (click to select, then quickly press-and-drag):
the second press arrives from Qt as a DOUBLE-CLICK event. `Region.mouseDoubleClickEvent` started
editing straight away, so the region went into edit mode (text cursor, no move) and the drag did
nothing. The same would have opened the plot dialog (modal) for a plot region.
Clarification implemented: a double-click-typed press is treated like a press (it starts a move
session); the "edit" (or plot dialog) action is deferred to button release and runs only if the
pointer did not move past the 4 px threshold. A real double-click therefore still edits, a
click-then-drag moves. Regression: tests/test_drag_move_023.py::test_root_cause_click_then_drag_arrives_as_double_click.
Other implementation notes: ItemIsMovable removed (scene-driven move); edge scrolling is a bounded
20 px step per mouse event within 24 px of a viewport edge (instead of ensureVisible, which ran away
because the view replays the last mouse move after scrolling; replays are ignored while scrolling).
