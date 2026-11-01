# Review: spec 021 phase A (page-aware evaluation order)

Reviewer: tester. Scope: engine/pagination.py, document.py, gui/worksheet.py, engine/wiring.py.
Tests added: tests/test_pagination_phase_a_blackbox.py (57 tests, written from the spec only;
independent of tests/test_pagination_order.py).
Full suite: 1726 passed, 2 xfailed (developer's 1669 + my 57).
GUI run of the real app: not done for phase A (no UI change besides the new order and help text);
phase B review must do it.

## Coverage
A1-A12 all covered (engine via SheetDocument.ordered(), GUI via Worksheet, wiring via a
recording monkeypatch on wiring._COMPUTE to observe true evaluation order). Edge cases covered:
region exactly on a break (engine, GUI, wiring), duplicate breaks at the same y, unsorted
breaks (document, wiring, page_index), sub-grid float noise ties, v1/v2/v3 files, malformed
page_breaks (string, number, null, dict, bool, nested, NaN, Infinity, numeric strings), breaks
in a pre-v4 file (honoured, saved as v4), v3-without-components still rejected, v5 rejected,
creation-sequence tie-break (moved last / selected last / Z-order raised / save-load /
region created after load / re-moved), save-load order stability with breaks, clear_sheet
resets breaks, wiring page-awareness with and without a wire, topo_sort with 2- and 3-tuple keys.

## Defects
None found in phase A.

## Scrutiny of the developer's changes
1. Version guard >=3 -> ==3 in document.py: legitimate and necessary. With >=3 a v4 file that
   holds only page breaks (no component, no wire) would be rejected as "newer", contradicting
   A7 and the spec's "no analogous guard for version 4". v5+ is still rejected by the first
   check (> FORMAT_VERSION_PAGES), and v3 without component/wire content is still rejected
   (both pinned by my tests). Side effect: a bare v4 file with no breaks and no components now
   loads; spec explicitly says no v4 guard, so this is per spec.
2. tests/test_document.py test_reading_order: region c moved (10,50) -> (310,50). Under the new
   order (10,50) sorts before (300,10), giving a,c,b; the test's intent (a, b, c order with
   y/x mixing) is kept by the coordinate change. Legitimate.
3. tests/test_wiring_blackbox.py: "version above 3 always rejected" became "above 4" with
   version 5. Same intent, shifted with the spec's new highest version. Legitimate. (Pre-existing
   v3-bare test untouched.)
4. examples/demo.lsheet: I, M, sigma moved x 40 -> 300 so they still evaluate after h (x=260
   would otherwise... h at x=260 is left of 300 and I at x=40 would run before h). Only x
   changed, text untouched. My test loads the demo and asserts no errors other than the
   deliberate "L + F =" unit-mismatch line: passes. Legitimate. Note the demo's visual layout
   changed (columns now x=40/260/300/480); worth a glance in the GUI pass.

## Observations (not defects)
- Worksheet.clear_sheet does not reset _seq_counter; harmless (monotonic only).
- load_document assigns sequence by doc.regions file order (as spec says), not by ordered().
  Files written by LiveSheet are already sorted so this is identical; a hand-edited unsorted file
  with exact-position ties uses file order. Tested.
- Stale text still stating the old order (doc pass pending per spec): README.md line 28,
  docs/manual/odes.md (lines 18, 98), docs/manual/truss.md (23, 103), docs/manual/README.md
  line 4, engine/evaluator.py docstrings ("reading order", benign).
- wiring.py diff in the working tree also contains unrelated cad-profile and matrix-format
  work (specs 014/015); not reviewed here.

## IP red flags
None. pagination.py contains only generic ISO A4-derived constants and a sort key.

## Coverage gaps
Phase B items (marker, reflow, PDF) not yet implemented; no real-app GUI run for phase A.
