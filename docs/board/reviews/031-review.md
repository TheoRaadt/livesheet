# Review: spec 031 phase A (3-D surface plots)

Tester, 2026-11-12. Scope: phase A only (A1 engine, A2 renderer and GUI). Phase B not implemented, not tested.

## Tests added
- tests/test_spec031_review.py: 69 engine tests (A1-1..A1-14 with the spec's numbers re-verified on the
  engine, E1..E12 error wording, header recognition including `plot3d`, units and display units, vector
  and range axes, descending samples, 2 x 2 grid, extreme magnitudes, closed-form cross-check of the
  heights, parse-once, performance).
- tests/test_spec031_gui_review.py: 31 tests. `layout_surface` is checked against my own implementation of the
  spec's projection maths (cube corners for 6 views, cell polygons, mean depth, depth order, shading
  formula with the fixed light vector, brightness range, anchor counts, zoom scaling), `paint_surface`
  (non-white pixel count, edge cases, 1 x 1 rect), region helpers, Insert menu, starter text, hint, editor,
  live update, save/load round trip and version, PDF export, delete, 2-D regression.
- Optional env vars LS_REVIEW_PNG / LS_REVIEW_PDF make the tests write a sample PNG / PDF for inspection.

## Results
- New files: 100 / 100 pass. No production code touched.
- Every number in A1-1 .. A1-9 matches the engine. E1..E12 messages all contain the quoted text. `plot3d` as
  header gives "Syntax error" (not a surface); `plot3d` as an option line gives
  `Unknown 3-D plot option 'plot3d'`. `Surface` (capital), `surface x`, `surface := 3` are not surface headers.
- Performance (this Mac): 25 x 25 eval 0.010 s, 100 x 100 eval 0.067 s, layout 100 x 100 0.038 s,
  paint incl. layout 0.086 s. All far under target.
- Full suite: 3751 passed, 2 skipped, 12 xfailed in 78 s (includes the spec 032 work in the tree; no failures).

## Defects, ranked (none blocks acceptance)
1. LOW-MEDIUM (readability, spec-compliant): z tick labels and the z title sit on the nearest vertical box
   edge and are drawn after the cells, in dark text over the dark-blue surface. In the 600 x 420 ripple sample
   the z ticks are barely legible and the z title overlaps the surface. Suggest a light halo/background behind
   labels or a lighter base colour. A product decision, not a spec violation.
2. LOW (cosmetic): at the near floor corner the last x tick and the first y tick are anchored almost at the
   same point and overprint ("20" / "3 y" garbling visible in the 520 x 360 Load sample and the ripple sample).
3. LOW (spec wording): an all-bare spec (`surface / over / across / show`) is an engine status error
   ("surface needs an 'over' line"); the hint is shown by the GUI only. The status bar therefore counts
   "1 error" for a freshly inserted 3-D plot. The 2-D plot behaves identically (checked), so not a regression.
4. INFO: the matrix literal in the spec's E8 example is notation only; the engine syntax is `[1,2;3,4]`
   (`[[..]]` gives "Nested matrices are not supported"). Tests use the real syntax.
5. INFO: the chart occupies about 0.42 * min(W,H) radius by spec, so a wide region leaves large empty margins.

No spec violations found in phase A.

## Coverage gaps
- Real-window computer-use pass (A2-12) NOT done: the computer_* tools were not available in this session.
  Substitute: I drove a real `MainWindow` offscreen (insert, edit text, live recalculation from a math region
  above, resize, save, reload, export PDF) and inspected window grabs (hint text, surface with units
  `x [m]`, `500 N * (x/m) * y [kN]`, title) and the PDF. A human or computer-use pass on the Mac is still
  open (menu click, double-click editor, Export PDF dialog).
- PDF inspected structurally only (no image objects; about 2350 line segments and 20 text blocks in the
  stream, so vector). No PDF rasteriser was available to view the page or to test zoom blur.
- Phase B (rotate, zoom, saved view, B.0..B10) is untested because it does not exist yet.
- Painter's-algorithm artefacts on steep surfaces: accepted by spec (Q8), not tested for.

## IP red flags
None found. `grep` for vendor names in engine/surface.py and gui/surfaceview.py: nothing. Keywords are the
spec's own (`surface`, `across`, `zunit`, ...); the former command name `plot3d` is not recognised.

## Transient / unrelated
- Spec 032 (LaTeX text) work is in the tree; the full run had no failures, so no transient spec 032 breakage was seen.
- Note for future tests: `insert_region("plot")` opens the 2-D dialog and blocks a headless test; use
  `add_region("plot", crosshair.pos(), text)` instead.


---

# Phase B (rotate, zoom, saved view, frame-ring move), tester, 2026-11-12

Scope: B.0..B10 plus the phase A defect fixes (label backing, tick nudge, long-title shortening). Written from the spec only.

## Tests added
- tests/test_spec031b_review.py (71 tests + 1 xfail group): rotate maths (0.5 deg/px, fractional px, azimuth wrap into [-180,180), elevation clamp),
  zoom (1.1 per 120, fractional and multi-notch deltas, exact clamps 0.25 and 4.0), stored-view precedence over the `view` line, reset,
  clearing on a changed `view` line (edited, removed, added; unchanged edit keeps it), .lsheet round trip, keys written only on `surface`
  regions, partial / malformed / non-finite keys ignored, unknown future keys ignored, same version with and without keys, exact bytes of a
  pre-phase-B sheet, layout under zoom and degenerate views, B8 redraw time, PDF follows the stored camera and stays vector.
- tests/test_spec031b_gui_review.py (61 tests): real MainWindow driven with synthetic QMouseEvent / QWheelEvent / QContextMenuEvent on the view
  viewport: B1/B2 by mouse, B.0 ownership (selected and not-yet-selected), ring move on all four sides and corners, beyond-ring press does
  nothing, Esc restores a ring move, resize handle (selected and unselected), 2-D plot and math region unchanged (spec 023), double-click
  opens the editor, double-click then drag rotates, editing region never rotates, wheel in/out of chart, canvas zoom 2x (pixel based),
  modified flag, real context menu (Reset entry present for 3-D incl. ring, absent for 2-D/math/canvas), drag preview wire/mesh (B9),
  save/reopen through the window, live update with stored view kept.

## Results
- New files: 131 passed, 3 xfailed (documented defects below). Full suite: 4005 passed, 2 skipped, 13 xfailed, no failures. No production code touched.
- B1..B9 all verified as written. Numbers: azimuth +20 for 40 px, elevation +10 for 20 px up, clamp 90 / -90, wrap 175 -> -175, zoom 1.1, 1.0,
  4.0 and 0.25 exactly; saved keys 60.0 / 40.0 / 1.1; reopened layout polygons and box equal.
- B7 / format: reader uses `raw.get`, so unknown keys never mattered. Checked a second way: the HEAD (pre phase B) `document.py` loaded as a
  second module reads a new file with view keys without error, and its re-save drops them; version is 2 with or without the keys; HEAD writer
  and new writer give byte-identical output for examples/demo.lsheet. Keys on 2-D plot, math and text regions are dropped on load.
- B8 timing (this Mac, layout + paint into a 400 x 260 image, best of 2-3): 25 x 25 mesh 9 ms (target 50), 100 x 100 mesh 145 ms (target
  250), 100 x 100 wire 58 ms. Pass.
- PDF: rotated/zoomed export differs from the default-view export, starts with %PDF, no image objects (vector).
- Native cocoa run (script-driven, not by hand): Insert > "3-D plot" menu action, typed spec, rotate by synthetic mouse, wheel zoom, ring move,
  save, Export PDF (9.6 KB), real context menu "Reset 3-D view", reopen (view restored), close without leaving the app running. PNGs in the
  scratchpad (n1..n6). Rotated and zoomed pictures look right; see defect 1 for the label collision visible in them.

## Defects, ranked (none blocks acceptance)
1. LOW-MEDIUM (readability, new reach through rotation) 031B-2: the y-axis title and the z-axis title are placed on top of each other in about
   22% of sampled views (72 of 324 on a 36 x 9 grid of az/el, for example az 80 / el 45 in the native screenshot: "y [m]" is hidden under the
   z title). The phase A declutter nudges tick labels only. Repro: layout_surface(data, QRectF(0,0,400,260), 80, 45, 1.0, "mesh") with the saddle
   sample: axis_title_anchors y at (115, 202), z at (128, 203). xfail test: test_axis_titles_do_not_overprint_in_reachable_views.
2. LOW 031B-3: PlotRegion paints in wire mode whenever `rotating` is set and the grid is large; it does not check `scene.printing`. A PDF export
   started while a drag is still in progress (keyboard shortcut with the mouse held) would print wire. Repro: reg.rotating = True on a 50 x 50
   surface, export_pdf -> layout_surface called with "wire". xfail test: test_pdf_during_rotate_preview_is_not_wire.
3. LOW (spec wording) 031B-4: B9 says "more than 40 cells per axis"; the code switches at more than 40 points (41 points = 40 cells already wire;
   a 40-cell grid is not "more than 40"). Needs a one-word spec clarification or `> PREVIEW_CELLS + 1`. Test records 40 -> mesh, 42 -> wire and
   xfails the 41 case.
4. LOW 031B-5: a drag or wheel on a 3-D region that only shows the empty hint or an error stores a view and marks the sheet modified (the
   native run wrote view_az/view_el/view_zoom for the bare starter text). Harmless, but invisible and "modified" for nothing.
5. INFO: residual cross-axis tick overlap after the nudge in 8 of 324 sampled views; at zoom 4 many labels lie outside the chart and are clipped
   (expected: clipped to the frame). Same-axis labels are close at el near +-80 (not nudged).
6. INFO / unspecified behaviour recorded (not defects): Esc during a rotate drag does nothing (no revert; the view stays rotated, flag clears on
   release). Ctrl+wheel inside the chart zooms the canvas, not the 3-D view. Cursor over a 3-D chart is the plain arrow. The app has no undo, so
   rotate/zoom are not undoable (they do set the modified flag). Double-click on the frame ring edits (no rotate).

## Coverage gaps
- No computer_* tools in this session: the visual pass was a script driving a real cocoa MainWindow with synthetic events, not clicks by a human or
  the Export PDF / Open / Save file dialogs. A pass by hand on the Mac is still open for the native dialogs and the pointer feel (0.5 deg/px).
- PDF checked structurally (no rasteriser): vector yes, label legibility not inspected.
- Trackpad pixelDelta wheel events (macOS) not exercised; the code reads `event.delta()` (angleDelta) only.
- Painter's artefacts on steep surfaces: accepted by spec Q8.

## IP red flags
None. Names and keys are the spec's own (`view_az`, `view_el`, `view_zoom`, "Reset 3-D view"); no vendor strings in the phase B code paths.

## Transient / unrelated
None seen; the full suite was green with the concurrent LaTeX and mech-eng work in the tree.
