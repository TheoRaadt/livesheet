# Review: spec 021 phase B (page-break marker, reflow, delete, fold guides, PDF)

Reviewer: tester (independent, black-box, from docs/board/specs/021-page-breaks-and-evaluation-order.md only).
Date: 2026-11-01.

## Result: PASS, 0 defects, 2 notes on developer deviations

New tests: tests/test_page_breaks_blackbox.py (54 tests; the developer's tests/test_page_breaks_phase_b.py
was not used as a source).
Full suite: `QT_QPA_PLATFORM=offscreen pytest -q` -> 1799 passed, 2 xfailed (1745 developer baseline + 54 new).
All 54 new tests passed on the first real run (one test-code typo of mine fixed; no production issue).

## Coverage by criterion

- B1 reflow numbers, crosshair, status text (2 regions, 720 units): pass.
- B2 order after insert, both directions (define-on-page-1 gives `= 1`; define-on-page-2 gives "not defined"): pass.
- B3 insert exactly on a fold (delta 0, nothing moves, regions below the fold untouched): pass.
- B4 second break on overflowed page (R3 -> 2960, breaks [1220, 2440]) and the 1180 example (T=2440, y=3700 -> 4880): pass.
- B5 existing markers shift; markers renumbered Page 2,3,4: pass.
- B6 refused at y=0 and at a break y; nothing changes, status string exact, sheet not marked modified: pass.
- B7 component + wire: component moves, wire entries unchanged in the document, drawn path endpoints equal the ports' new positions: pass.
- B8 delete: via Delete key on the scene, and via MainWindow.delete_selected (Edit > Delete Region); nothing moves back; marker removed from scene; order recomputed as plain x then y: pass.
- B9 drag across marker: no other region/marker moves, page membership follows live anchor in both directions: pass.
- B10 not movable (flag absent, simulated press+move leaves y), Select All excludes it, not in regions(): pass.
- B11 PDF with breaks: 2 pages; page 1 short + page 2 content still 2 pages; empty MIDDLE page still gets its own sheet (3 sheets); an overflowing logical page spills onto extra sheets only within itself (1+2 = 3): pass.
- B12 PDF without breaks: 2650-unit sheet -> 3 sheets, empty sheet -> 1 page: pass.
- B13 printing flag: rendering with `printing=True` leaves no marker/guide pixels at the break row or the 1220 fold row, rendering with it False differs; export_pdf restores printing=False, crosshair visibility and breaks: pass.
- B14 save/reload: JSON version 4, page_breaks [1220.0], region y 100/1320/2020, order and results identical after reload; load replaces markers; clear_sheet removes markers; version drops back to 1 and the `page_breaks` key disappears when the last break is removed: pass.
- Menu: Insert > Page Break exists, shortcut Ctrl+Return, triggers the insert: pass.

Edge cases pass: repeated inserts (second insert at an interior y moves content and the existing marker again, no crash; insert at the new crosshair is refused as page top), hand-edited duplicate breaks (two markers, numbered 2 and 3, PDF export does not crash, insert/remove still work), hand-edited close breaks [100,150,160] (4 sheets, no crash), insert inside a short page (T=100 -> B=1320, delta 1200), mixed region kinds (math/text/plot/component) all move, region exactly at y moves, region exactly on a break belongs to the later page, empty sheet insert, insert while editing finishes editing, selection history irrelevant, tall region overlapping a marker.

## Scrutiny of the developer's deviations

1. Synchronous recalculation on insert/remove. Acceptable. Results are correct without spinning the event loop
   (tested), the modified flag is set, and the status message is emitted last so it is not overwritten. Spec step 8 said
   "a recalculation is scheduled"; synchronous is observably equivalent except it cannot be coalesced with other pending
   edits. Not a defect, record only.
2. PDF strips clipped per logical page. Matches the spec's per-page iteration (page 2 starts at its own top, a
   break always starts a fresh sheet). One visible consequence, consistent with the spec's overlap convention: a region
   whose anchor is on page 1 but whose body crosses the break is drawn on sheet 1 and its tail also appears at the top
   of sheet 2 (the scene is rendered by rectangle, not by owner). Not specified either way; note only.
3. Empty trailing pages skipped. Does not contradict B11 or B12 (B11 has content on both pages; B12 has no breaks).
   It does deviate from the literal sentence "ALWAYS calling writer.newPage() when moving to the next logical page"
   only for a trailing logical page that has no content at all: e.g. breaks [1220] and content only on page 1 gives
   1 sheet (pdf_strips -> [(0, 810)]), not 2. I consider that sensible (no blank last sheet) but it is a judgment call
   the spec does not state; a spec sentence is recommended. Empty MIDDLE pages are NOT skipped (verified: 3 sheets), which
   matches the "a break always starts a fresh sheet" rule. A page with content that is exactly 1220 tall gives one
   sheet; 1230 gives two (second 10 units), as the spec's slicing implies.
4. Scene-level click handler for marker selection. No regression found: clicking empty canvas after selecting a
   marker deselects it and moves the crosshair; clicking a region selects the region (marker deselected when
   clicked first, region click selects region); clicking a marker while editing finishes the edit; right-click on a
   marker does not select it; a region overlapping the marker line wins the click (marker z=-2). Minor observations
   (not defects): clicking a marker does not move the crosshair, and Ctrl/Shift multi-select with a marker is not
   supported (plain click replaces the selection). A rubber-band drag across the line can select a marker, after which
   Delete removes it (Select All still excludes it, as spec'd).

## Coverage gaps

- Real window not exercised: I have no computer_* / computer-use tool in this session, so I could NOT launch LiveSheet on
  the Mac, open Insert > Page Break, see the marker/"Page N" label/fold guides, or open an exported PDF. This is stated
  explicitly; the standing GUI pass for phase B is still outstanding. Headless paint/render and PDF page counts were
  checked, but PDF page *content* (that page 2 starts with y >= 1220 content) was verified only through pdf_strips
  arithmetic and page counts, not by rasterising the PDF.
- No test for dragging a region with a real QGraphicsView mouse sequence across a marker (programmatic setPos used).
- No test of the marker label text pixels ("Page N") or colour on selection.
- Undo does not exist, so insert-with-reflow cannot be reverted (known, spec open question 2).

## IP red flags

None. New code (PageBreakItem, insert_page_break, pdf_strips) uses generic names; no vendor names, strings,
assets or file-format fields copied. The only new file-format field is `page_breaks`, as specified.

## Defects

None found.
