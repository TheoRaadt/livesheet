# Review: spec 023 drag-to-move regions (tester, 2026-11-09)

Tests: tests/test_spec023_review.py (56 black-box cases, real QTest mouse/key events on the view
viewport, offscreen). Developer tests (tests/test_drag_move_023.py) not duplicated.
Full suite: 2567 passed, 10 xfailed (pre-existing), 0 failed.

## Covered
- Theo's case: click-select, then a quick press typed as MouseButtonDblClick, then drag: moves, no
  editor; a dbl-click-typed press with a tiny move edits on release; plot region same sequence
  moves and opens no dialog; no editor appears after the drag ends.
- Plain drag (selection replaced), 4 px threshold, snap stepping during drag, out-and-back not
  modified, right/middle button, result area as grab target, pointer outside viewport.
- Group: rubber band then drag, Select All, off-grid offsets preserved, per-axis group clamp,
  member click without drag leaves everything unmodified.
- Esc: group cancel, modified restored (False and True), results restored after an order change,
  Esc before the threshold, second drag after a cancel, focus-out as Esc, cursor restored.
- Nudge: four directions, Shift = 50, group clamp with Shift, blocked axis does not set modified,
  re-evaluation after nudge, ignored while editing, crosshair Shift+arrow, marker untouched.
- Edit mode: ring drag keeps text/editing, text drag never moves, far-outside press is canvas,
  dragging another region finishes the edit.
- Priorities: plot body moves, handle resizes (selected and unselected), component body drag with
  wires following, marker in selection stays, dragging a marker moves no region.
- Order/page break: live order change, recalculation while the pointer pauses (debounce), cross a
  break and back (keyboard back-route), region deleted / document loaded mid-drag, equal positions.
- Zoom 0.5 / 2.0 (threshold in view pixels), cursors (open hand, closed hand outside region, I-beam),
  .lsheet round trip (version stays 1), `move_regions` call count and (region, old, new) payload.

## Defects
None found. Two failures during authoring were test bugs (fixed).

## Gaps / not verified
- Computer-use tools were NOT available to this agent: no real-app (GUI) run was done. Manual
  check still needed on the Mac: click-then-drag on a selected region, Esc mid-drag, open/closed
  hand cursors (offscreen only proves the cursor shape set on the viewport), edge scrolling feel
  (tested only in the developer's bounded-step test; my tests disable it).
- Real trackpad double-click timing is simulated by sending MouseButtonDblClick directly.
- Hover cursor is checked via Region.cursor(), not via real hover events from a window system.
- Multi-view (several QGraphicsViews on one scene) not tested.

## IP
No red flags: generic move/nudge/Esc conventions, no vendor names or strings in the diff.
