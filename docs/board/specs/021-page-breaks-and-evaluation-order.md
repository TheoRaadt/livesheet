# 021 Page breaks (A4 pagination, with reflow) and left-to-right/top-to-bottom evaluation order

Revision 2 (2026-11-01): Theo decided open question 1 (true word-processor reflow on insert) and
open question 3 (also flip wiring.py's tie-break). This revision adds the reflow mechanism, the
wiring.py change, and splits the work into two shippable phases (A, B).

Source inspiration: https://en.wikipedia.org/wiki/ISO_216 (A4 paper dimensions, 2026-11-01,
concept only; the physical 210mm x 297mm size is a public ISO standard, not any vendor's
property); https://en.wikipedia.org/wiki/Pagination (generic "hard page break" concept common to
essentially every word processor and DTP tool since the 1980s, 2026-11-01, concept only). Neither
page was read for UI, wording or layout. This is Theo's own direct request (docs/board/backlog.md
item 7, 2026-11-01), not drawn from the mathcad-concepts skill's vendor-category list; no named
commercial tool's docs were read for this spec.

User story: as a LiveSheet user preparing a calculation sheet for printing/PDF export, I want to
see and control where my sheet splits into physical A4 pages on the canvas itself, by inserting
and removing page breaks like in a word processor (content after a break starts at the top of the
next page). I also want calculations to run left-to-right then top-to-bottom within each page
(not today's top-to-bottom-then-left-to-right), page by page, top of document to bottom.

## BLOCKING NOTE for the manager (wide blast radius)
Changing the ordering key is a core engine-semantics change (CLAUDE.md's own Architecture line
names today's top-to-bottom-then-left-to-right order explicitly). It is very likely to break many
existing tests that place regions at specific (x, y) coordinates assuming today's (y, x) order.
I did not audit the suite (explicitly not my job), but grep already shows order-sensitive tests in
at least tests/test_document.py, tests/test_plot.py, tests/test_solve.py,
tests/test_solve_blackbox.py, tests/test_ode_blackbox.py, tests/test_truss.py,
tests/test_wiring_core.py and tests/test_wiring_blackbox.py (each names "reading order"), and this
is very likely not exhaustive (any GUI test that creates several regions at hand-picked positions
and relies on evaluation order, and any PDF page-count test, is a candidate). The developer should
budget for updating many tests' region coordinates (not their intent) in phase A, and should treat
those failures as expected fallout, not new defects. Phase B additionally touches PDF export and
moves regions on insert, so tests that count PDF pages are candidates too.
Docs that state the old order also need a pass later (CLAUDE.md Architecture line, README, manual
pages docs/manual/odes.md and docs/manual/truss.md which say "reading order (top to bottom, then
left to right)", the in-app help text in livesheet/gui/main_window.py near line 66, and the
mathcad-concepts / livesheet-dev skills). That doc pass is the documenter's / manager's job after
phase A ships; it is listed here so it is not forgotten.

## Behaviour (own words)

### What already exists today (unchanged unless stated)
- The canvas (livesheet/gui/worksheet.py) is one continuous, unbounded-height scroll,
  PAGE_WIDTH = 820 scene units wide. A single dashed vertical guide line is drawn at
  x = PAGE_WIDTH as a passive visual reference; it constrains nothing.
- Export PDF (livesheet/gui/main_window.py, export_pdf) silently slices this continuous canvas
  into A4 pages: QPdfWriter at QPageSize A4, 15mm margins, 144 DPI; scale =
  printable_width_px / PAGE_WIDTH; page_h = printable_height_px / scale (about 1214.7 scene
  units); then it renders consecutive page_h-tall strips onto successive PDF pages until the
  content bottom is covered. Automatic and invisible until export.
- Evaluation order is top-to-bottom-then-left-to-right in three places that must all change:
  1. livesheet/document.py, SheetDocument.ordered(): sorted by (y, x).
  2. livesheet/gui/worksheet.py, Worksheet.ordered_regions(): sorted by (pos().y(), pos().x());
     its result feeds Engine.evaluate() in Worksheet.recalculate().
  3. livesheet/engine/wiring.py, evaluate(): builds pos_of = {name: (s.y, s.x)} and hands it to
     topo_sort(), which uses it only to break ties between components the wiring graph does not
     otherwise order (a min-heap keyed by pos_of, then by name).
  Engine.evaluate() itself (livesheet/engine/evaluator.py) takes whatever ordered (key, source)
  list it is given and has no opinion on x/y: no change is needed inside it. Its two-pass
  structure (global definitions first, then everything else) is untouched.
- There is NO undo/redo anywhere in the application (grep of livesheet/ finds none; backlog
  item 4 is still open). There is no push-down layout either (backlog item 20): regions and
  results may overlap freely today.
- Regions are QGraphicsObject subclasses (MathRegion, TextRegion, PlotRegion, ComponentRegion in
  livesheet/gui/regions.py and plotregion.py); wires (WireItem) are not regions and have no
  stored position: they recompute their path from their two components' port positions on every
  paint/sync, so moving components moves their wires automatically.

### New shared concept: pages
- A **page break** is a y-coordinate b (a multiple of the 10-unit grid). Zero page breaks = the
  whole sheet is one continuous page, unbounded in height (today's behaviour; every file saved
  before this feature).
- With breaks sorted ascending b1 <= b2 <= ... <= bk: page 1 is y < b1; page j (2 <= j <= k) is
  b(j-1) <= y < bj; the last page is y >= bk. A region exactly on a break's y belongs to the page
  that starts there.
- A region's page is decided by its anchor point (region.pos(), the top-left point already used
  for all position-based sorting), recomputed from its live position at every recalculation. A
  region whose body straddles a break belongs to the page of its anchor.
- Constants (new, in a new Qt-free module livesheet/engine/pagination.py so the engine, document
  and GUI share them): PAGE_WIDTH = 820 (moved/re-exported, value unchanged), PAGE_HEIGHT = 1220,
  GRID_UNIT = 10 (the ordering quantum; equals the canvas grid in livesheet/gui/regions.py).
  PAGE_HEIGHT derivation: printable A4 width = 210mm - 2x15mm = 180mm; printable A4 height =
  297mm - 2x15mm = 267mm; 820 x 267 / 180 = 1216.33, snapped to the nearest grid multiple = 1220.
- Two pure functions in pagination.py (no Qt, no SymPy):
  - page_index(y, breaks) -> int: number of breaks b with b <= y (0-based page number).
  - order_key(x, y, breaks) -> (page_index, round(x / GRID_UNIT), round(y / GRID_UNIT)).
  document.py, worksheet.py and wiring.py all use these so there is one definition of the order.

### Evaluation order (phase A)
- Within one page: sort key (round(x/10), round(y/10)) ascending, i.e. left-to-right, then
  top-to-bottom. Grid rounding avoids float-noise ties.
- Pages evaluate in page order: every page-1 region, then every page-2 region, and so on. The
  page index is the first element of the key, so a page boundary always dominates the x/y
  comparison.
- A break-free sheet is one page, so the order is simply left-to-right then top-to-bottom for
  the whole sheet.
- Tie-break (the same category of ambiguity as backlog item 28): two regions can still tie only
  when page, grid-snapped x and grid-snapped y are all equal (an equal x alone or an equal y
  alone is always resolved by the other coordinate). That exact-position tie is broken by a
  stable creation sequence number: each region gets a monotonically increasing integer when it
  is created in a session (Worksheet keeps the counter; a region loaded from a file gets its
  index in the file's regions list); it is never changed when the region moves. Qt Z-order and
  scene iteration order are never used. Because to_json() writes regions already sorted by the
  new key with a stable sort, tied regions keep their relative order across a save/load round
  trip. This closes backlog item 28 for the old and new order alike.
- Global definitions (the triple-bar operator) are unaffected: Engine.evaluate() just receives
  the new list.

### Component wiring tie-break (phase A, Theo's decision on open question 3)
Exact change in livesheet/engine/wiring.py:
- evaluate(specs, wires, engine) gains an optional keyword parameter page_breaks: Sequence[float]
  = (). Default () keeps every existing call valid.
- pos_of changes from {s.name: (s.y, s.x)} to
  {s.name: order_key(s.x, s.y, page_breaks) for s in specs}. The values are now 3-tuples
  (page, x, y).
- topo_sort(names, pos_of, edges) is otherwise unchanged: it still treats pos_of values as
  opaque comparable keys, still only breaks ties between components the wiring graph leaves
  unordered, still falls back to the component name as the last tie-break (names are unique, so
  no creation sequence is needed for components). Its fallback for a name missing from pos_of
  changes from (0.0, 0.0) to (0, 0, 0) so the key shape stays consistent; its docstring and the
  module docstring change from "(y, x) reading-order key" to "page-aware (x, y) key".
- Worksheet.recalculate() passes page_breaks=self.page_break_ys() (an empty list in phase A,
  since there is no UI yet to create breaks; the data model and the parameter still exist and
  are tested).
- The wiring graph remains the primary ordering rule; only the tie-break flips.
- Tests that call topo_sort directly with hand-built 2-tuple positions keep passing mechanically
  (it is plain tuple comparison); only their comments ("y, x") become outdated. Tests that place
  real components and depend on the tie-break through wiring.evaluate() or Worksheet are the
  ones that will change.

### Page-break marker, insert, reflow, delete (phase B)
- UI: Insert > Page Break (menu label "Page &Break", own naming), default shortcut Ctrl+Return
  (no collision found in main_window.py). It acts at the crosshair's current y (the same
  crosshair-driven placement every other Insert action uses). A page-break marker is a canvas
  item that is not a Region: it has no text and is never evaluated; it is drawn as a full-width
  horizontal rule across PAGE_WIDTH with a small "Page N" label. It is selectable and deletable
  (select it, press Delete, or Edit > Delete Region). It is NOT draggable (to change a break,
  delete it and insert another): this avoids a second, harder reflow path. Select All Regions
  does not select markers.
- Insert algorithm (deterministic, one Worksheet method insert_page_break(y) so a future undo
  command can wrap it as a single step):
  1. Finish any inline editing first (as insert_region does).
  2. y = snapped crosshair y. T = the page top containing y = the greatest existing break b <= y,
     or 0 if none.
  3. If y == T: rejected, nothing changes, status message "This position is already the top of a
     page." (A break at the very top of a page would only create an empty page.)
  4. Otherwise B = T + PAGE_HEIGHT * ceil((y - T) / PAGE_HEIGHT), and delta = B - y (0 <= delta
     < PAGE_HEIGHT). B is the top edge of the next A4 page counted from the current page's top.
     (If the current page has already overflowed one A4 height, B is the next physical A4 sheet
     boundary, matching where export would cut.)
  5. Every region with anchor y' >= y is moved down by delta (setPos; no re-snap needed since
     delta is a grid multiple). "Every region" means all Region subclasses: math, text, plot and
     component regions. Wires are not moved explicitly; they follow their components. Existing
     page-break markers with b' >= y are also moved down by delta, so the page structure below
     the insertion point is preserved. A region whose anchor is exactly y is moved.
  6. The new marker is added at B. Every moved region has y' + delta >= B and every unmoved
     region has y' < y <= B, so page membership is exactly "content after the insertion point
     now starts on the new page".
  7. The crosshair moves to (its x, B) so the next region starts on the new page.
  8. The sheet is marked modified; a recalculation is scheduled; the status bar says
     "Page break inserted; moved N regions down by D units."
  When delta == 0 (y is already exactly on an A4 fold) nothing moves; only the marker is added.
- Delete: removing a marker removes it from the page_breaks list and nothing else. Regions do
  NOT move back up (default chosen: moving them back would need a remembered gap and could
  overlap content the user has since placed; see open question 1). The two pages it separated
  merge for ordering purposes; the order is recomputed immediately.
- Dragging a region across a marker: free, like anywhere else. No snapping to a page, no push of
  other regions, no warning. Page membership (and therefore evaluation order) follows the
  anchor's live position.
- Tall results / tall regions: results are drawn at their region and never affect anchors or
  reflow; a region or result taller than the space before the next break may overlap the marker
  and the next page's content (same free-form overlap convention already accepted elsewhere).
  Reflow only reasons about anchors.
- Overflow of one page beyond PAGE_HEIGHT: content is NOT auto-flowed. There are no automatic
  (soft) page breaks, because they would silently move absolutely-positioned content and change
  evaluation order behind the user's back. Instead each page draws passive dashed fold guide
  lines every PAGE_HEIGHT units from its own top (the previous break, or y=0), in the existing
  dashed guide style, showing where export will cut that page onto extra sheets. A break-free
  sheet gets the same guides from y=0.
- Undo: none exists. Insertion with reflow is therefore not undoable in this slice. Mitigations:
  the status message reports exactly what moved; the whole operation is one method (see above)
  so backlog item 4 can later wrap it as one undo step; the user can Save beforehand. Recorded
  as open question 2.

### PDF export (phase B)
export_pdf is restructured to iterate per logical page. For each page (consecutive boundaries
0, b1, ..., bk, content bottom) it renders strips of that page's own content starting at that
page's top, calling writer.newPage() between strips, and ALWAYS calling writer.newPage() when
moving to the next logical page, even if the previous page's last strip was short (a break always
starts a fresh sheet).
- Scale: for a sheet WITH page breaks, the strip height must equal PAGE_HEIGHT exactly so one
  logical page of up to 1220 units fits one sheet; today's page_h is about 1214.7 (smaller than
  1220), which would spill a sliver onto a second sheet. So with breaks the scale is
  min(printable_width_px / PAGE_WIDTH, printable_height_px / PAGE_HEIGHT) and the strip height is
  PAGE_HEIGHT (a shrink of about 0.4%). For a sheet WITHOUT breaks the existing scale and page_h
  are kept exactly, so existing output is unchanged.
- Page markers, fold guides, grid dots and the crosshair are not drawn in the PDF (the existing
  Worksheet.printing flag suppresses them; the marker and guides must honour it).

## Syntax proposal (own keywords)
Not applicable: no change to the math/text statement grammar. The only new user-facing
vocabulary is the menu action "Page Break" and the .lsheet field name page_breaks.

## .lsheet file format impact
- New SheetDocument field page_breaks: list[float], y-coordinates in ascending order.
- New FORMAT_VERSION_PAGES = 4, written only when page_breaks is non-empty (mirrors the existing
  conditional bumps to 2 for a plot and 3 for a component/wire). Sheets without breaks write
  whatever version they write today, unchanged. The highest version from_json accepts becomes 4.
  The existing "declared version 3 but no component/wire content is rejected" guard stays as it
  is; no analogous guard is added for version 4.
- Reading a file with no "page_breaks" key (versions 1-3) gives page_breaks = [] (one
  continuous page) with the new order applied. No migration. Non-numeric or malformed entries in
  page_breaks are dropped silently (lenient, like malformed wires).
- Loading does not re-run reflow: break positions in the file are honoured as-is (a hand-edited
  file with breaks not on a multiple of PAGE_HEIGHT from the previous break is legal).
- SheetDocument.ordered() uses the new page-aware key (with the stable-sort tie rule), so the
  on-disk region order means "evaluation order" as before. It reads self.page_breaks, so it needs
  no new parameter.

## Acceptance criteria

### Phase A (evaluation-order flip, shared pagination module, file format, wiring tie-break)
Engine-level cases use Engine.evaluate() fed the list produced by SheetDocument.ordered() (or
the pagination helpers); GUI-level cases use a Worksheet with regions placed by scene
coordinates. page_breaks can be set directly on a SheetDocument or via a hand-written file in
phase A (no UI yet).

A1. Order flip, no breaks. Region P at (x=10, y=300): `a := 1`. Region Q at (x=400, y=10): `a =`.
    Old order evaluated Q before P and Q's `a =` gave the error "a is not defined". New order
    evaluates P (x=10) before Q (x=400), so Q shows `= 1`.
A2. Same y, x decides. R at (x=10, y=50): `a := 2`; S at (x=300, y=50): `a =`. S shows `= 2`.
A3. Same x, y decides. U at (x=50, y=10): `a := 3`; V at (x=50, y=200): `a =`. V shows `= 3`.
A4. Page dominates x/y. page_breaks = [500]. C at (x=10, y=600) (page 2): `b := 5`. D at
    (x=400, y=50) (page 1): `b =`. D is on page 1 and evaluates first even though its x is
    larger, so D shows the error "b is not defined".
A5. Exact-position tie-break. Two math regions with no dependency between them, W1 created first
    and W2 created second, both moved to exactly (x=200, y=200): W1 is always ordered before W2
    across repeated recalculations, and across a save then load round trip, independent of Qt
    Z-order and of selection history.
A6. pagination helpers. page_index(499.0, [500.0]) == 0; page_index(500.0, [500.0]) == 1;
    page_index(10.0, []) == 0; page_index(1300.0, [500.0, 1200.0]) == 2.
    order_key(400.0, 50.0, [500.0]) == (0, 40, 5); order_key(10.0, 600.0, [500.0]) == (1, 1, 60).
A7. File round trip. A SheetDocument with page_breaks = [500.0, 1200.0] saves with
    "page_breaks": [500.0, 1200.0] and "version": 4 and reloads with identical page_breaks and
    the same 3-page grouping. A version-1, version-2 and version-3 file with no "page_breaks"
    key loads with page_breaks == []. A sheet with no breaks writes the same version and the
    same JSON shape as before this spec (apart from region order following the new key).
A8. Wiring tie-break flip (no wire between components). Value components VL at (x=10, y=300) and
    VR at (x=400, y=10), no wires: wiring.evaluate evaluates VL first, then VR (old order was VR
    first).
A9. Wiring: a wire still dominates position. Same VL/VR with a wire from VR's output into VL's
    input: order is VR, then VL, regardless of position.
A10. Wiring is page-aware. page_breaks = [500.0]; components K1 at (x=400, y=50) (page 1) and K2
     at (x=10, y=600) (page 2), no wires: order is K1, K2 even though K2 has the smaller x.
     The same call without page_breaks behaves as a single page (order K2, K1).
A11. Component-free sheets: wiring.evaluate with empty specs still returns {} immediately.
A12. Engine.evaluate() is unmodified: tests that call Engine().evaluate() directly with an
     explicit list (no positions involved) pass unchanged.

### Phase B (page-break marker, reflow, delete, fold guides, PDF)
Notation: H = PAGE_HEIGHT = 1220. All coordinates are scene units.

B1. Insert at an interior y with reflow. Sheet with regions R1 at (10, 100), R2 at (10, 600), R3
    at (10, 1300), no breaks; crosshair at y = 500. Insert > Page Break: T = 0, B = 1220,
    delta = 720. Result: R1 stays at y=100; R2 is at y=1320; R3 is at y=2020; page_breaks ==
    [1220.0]; the crosshair is at y = 1220; the status bar reports 2 regions moved by 720.
B2. Order after insert (builds on B1). With R1 `a := 1` and R2 `a =`, R1 is on page 1 and R2 on
    page 2, so R1 evaluates first and R2 shows `= 1`. With the roles reversed (the page-2 region
    defines, the page-1 region uses), the page-1 region shows "a is not defined".
B3. Insert exactly on a fold. No breaks, crosshair y = 1220: B = 1220, delta = 0; no region
    moves; page_breaks == [1220.0].
B4. Second break on an overflowed page. Continuing B1 (breaks [1220.0], R2 at 1320, R3 at 2020),
    crosshair y = 1500: T = 1220, y - T = 280, B = 1220 + 1220 = 2440, delta = 940. R2 (anchor
    1320 < 1500) stays; R3 (anchor 2020 >= 1500) moves to 2960; page_breaks == [1220.0, 2440.0].
    Separately, with T = 2440 and crosshair y = 3700 (y - T = 1260): B = 2440 + 2 x 1220 = 4880,
    delta = 1180.
B5. Existing markers below the insertion point move too. Breaks [1220.0, 2440.0], insert at
    y = 100 (T = 0): B = 1220, delta = 1120. The two existing markers shift by 1120, so
    page_breaks == [1220.0, 2340.0, 3560.0].
B6. Insert refused at a page top. With breaks [1220.0], crosshair y = 1220 (or y = 0): nothing
    changes and the status message is "This position is already the top of a page."
B7. Components and wires. A component C at (10, 600) wired to a component D at (400, 100):
    insert at y = 500 (B1 geometry). C moves to y = 1320; D stays; the wire is unchanged in the
    document (same component and port names) and its drawn endpoints equal the ports' new
    positions after recalculation.
B8. Remove a page break. From the state after B1 (R2 at 1320, R3 at 2020, breaks [1220.0]),
    select the marker and press Delete: page_breaks == []; R2 stays at y=1320 and R3 at y=2020
    (nothing moves back); the sheet is one page again and the order is recomputed by plain
    left-to-right then top-to-bottom.
B9. Drag across a marker. With breaks [1220.0] and R1 at (10, 100): dragging R1 to (10, 1300)
    moves no other region and no marker; R1 is now on page 2 for ordering.
B10. The marker is not draggable and not part of Select All Regions. Attempting to move it
     leaves it at its y; Select All Regions does not include it; Edit > Delete Region deletes it
     when it is the selected item.
B11. PDF with breaks. A sheet with breaks [1220.0], content on page 1 only up to y = 800 and on
     page 2 up to y = 1800: the exported PDF has exactly 2 pages, both A4, and page 2 starts
     with the content at y >= 1220 even though page 1's content ended at 800 (a break always
     starts a fresh sheet).
B12. PDF without breaks (backward compatibility). A break-free sheet with content to y = 2600
     exports to the same number of pages as the unmodified export_pdf produced before this spec
     for that content (same scale, same page_h, same slicing).
B13. PDF suppresses chrome. The marker, its "Page N" label and the fold guides do not appear in
     the PDF (Worksheet.printing set), same mechanism as grid dots and the crosshair.
B14. Round trip with breaks and moved regions. After B1, save and reload: regions at y = 100,
     1320, 2020, page_breaks [1220.0], version 4; evaluation order identical before and after
     reload.

## Edge cases
- A region exactly on a break's y belongs to the page that starts there (stated, not implicit).
- Hand-edited files with two breaks at the same y: allowed; one empty zero-height page; nothing
  crashes.
- Inserting while a region is being edited: editing is finished first.
- Insert when the crosshair is hidden (e.g. after clicking away): the last crosshair position is
  used, the same as every other Insert action.
- A region dragged so its body overlaps a marker: allowed.
- Delete only acts on selected items, as today.
- Loading a file that has page_breaks but a version number below 4: breaks are still honoured
  (lenient); the next save writes version 4.
- Very many breaks: no limit in this slice.

## IP check: pass
A4's physical dimensions (210mm x 297mm) are a public ISO standard (ISO 216), not any vendor's
intellectual property. "A user can insert a manual break that forces subsequent content onto a
new, fixed-size page, pushing following content down" is a decades-old, universal
word-processor/DTP concept, independently documented across essentially every such product (not
characteristic of the engineering-worksheet vendor list in the mathcad-concepts skill); nothing
was drawn from that list and no named commercial tool's docs, UI, icons or wording were read.
The evaluation-order change is internal semantics with no external concept source. The marker and
fold guides are plain, generic, passive canvas chrome plus an ordinary menu action; they are not
the patent-flagged "live placeholder editing drawn directly on a chart's own surface" interaction
style (nothing here is an input slot drawn on a chart). No new dependency. No vendor name, file
format or keyword used.

## Fits current architecture?
- NEW livesheet/engine/pagination.py (Qt-free): PAGE_WIDTH, PAGE_HEIGHT, GRID_UNIT, page_index(),
  order_key(). Phase A.
- livesheet/document.py: page_breaks field, FORMAT_VERSION_PAGES = 4, version(), to_json(),
  from_json() (lenient parse), ordered() uses order_key with a stable sort. Phase A.
- livesheet/engine/wiring.py: evaluate() gains the page_breaks parameter; pos_of built with
  order_key; topo_sort fallback and docstrings updated. Phase A. (ComponentSpec already carries
  x and y; no other wiring change.)
- livesheet/engine/evaluator.py: no change (it consumes the ordered list it is given).
- livesheet/gui/worksheet.py: ordered_regions() uses order_key plus the per-region creation
  sequence (new counter in Worksheet, assigned in add_region / add_component_region and from file
  order in load_document); recalculate() passes page_breaks to wiring.evaluate; page_break_ys()
  accessor; to_document()/load_document() carry page_breaks. Phase A. Phase B adds PageBreakItem
  (non-Region QGraphicsItem, like WireItem), insert_page_break(y) with the reflow above, deletion
  of a selected marker through the existing delete path, and drawBackground() fold guides gated
  on self.printing.
- livesheet/gui/main_window.py: Insert > Page Break (Ctrl+Return); Edit > Delete Region also
  deletes a selected marker; export_pdf() restructured per logical page with the scale rule
  above. Phase B.
- Layering: engine first (pagination, wiring), then document, then GUI, as usual. Phase A is
  shippable on its own (no UI change except the new evaluation order and the creation-sequence
  counter); phase B depends on it.

## Open questions (for Theo / manager)
1. After deleting a page break, should regions that were pushed down stay where they are
   (my default: simple, predictable, no remembered state) or move back up by the amount they
   were pushed? Moving back would need to remember each gap (not stored in the file) and could
   collide with content added since. Low-to-medium stakes; default chosen.
2. No undo exists (backlog item 4). Insert-with-reflow is therefore not undoable in this slice.
   Acceptable, or should backlog item 4 (undo) be pulled ahead of phase B? The reflow is one
   method so undo can wrap it later.
3. Overflow: content taller than one page is not auto-flowed (fold guides plus extra PDF sheets
   only; no automatic soft breaks). Rejected auto-flow because it would silently move
   user-positioned content and change evaluation order. Confirm.
4. Markers are not draggable (delete and re-insert instead) to avoid a second reflow path.
   Confirm, or ask for drag-to-move-with-reflow as a follow-up.
5. PDF scale for sheets with breaks shrinks by about 0.4% so a 1220-unit page fits one A4 sheet
   (today's page_h is about 1214.7). Alternative: PAGE_HEIGHT = 1210 (always fits, no shrink,
   but less faithful to the derived 1216.33). The coordinator specified 1220, so I kept it;
   confirm the shrink is acceptable.
6. Shortcut and menu naming (Ctrl+Return, "Page Break"): my own low-stakes pick.
