# Review: spec 022 window-wide wrapping tab strip (tester, 2026-11-03)

Result: PASS with 1 minor defect (extreme font), 1 known gap (accessible role), real-window pass NOT done.

Tests: tests/test_spec022_tab_strip_review.py (46 tests, written from the spec, independent of
tests/test_wrapping_tab_strip.py). Full suite (QT_QPA_PLATFORM=offscreen, ~/livesheet-venv):
2125 passed, 8 xfailed (before: developer reported 2079 passed; +46 = mine).

## Per criterion
1 Unchanged model: PASS (names/order/count; old tests pass unedited where tabs-only).
2 Placement and span at 600/1000/1600: PASS (below toolbar, above band, above canvas; span within margin).
3 Full labels: PASS. 4 All visible, no scroll arrows, inside strip rect: PASS (native bar hidden).
5 W=600: PASS (2 rows, equals greedy count, Elements first). 6 W=1000: PASS (1 row). 7 W=1600: PASS (1 row).
8 Justification: PASS at 400/600/800/1000/1600 (row sum + gaps = strip width +-1, last row included; equal heights).
9 Order after resize sequence: PASS.
10 Highlight: PASS (exactly one checked == currentIndex for k=0..9; fill and underline pixels differ in light and dark).
11 Click: PASS (currentChanged exactly once with k; re-click emits nothing; band page visible).
12 Keyboard: PASS (Right x2, Left, End, Home, edge no-ops, no signal on no-op; 2-row Down picks closest centre, Up from row 1 and Down from last row do nothing; Space/Return/Enter on focused unselected button selects once; strip is one tab stop). Ctrl+Tab page stepping not tested (spec says only "where the tab model provides").
13 Resize relayout: PASS (1600-1000-600-1000-1600: rows non-decreasing while narrowing, geometry identical on return, band directly under strip, canvas under band; per-step relayout in 40 px decrements matches greedy).
14 Band content: PASS (40 Elements buttons, 3 headers each on own row, alpha inserts `alpha`; Mechanical headers + "Resultant (2 forces)" in full; Algebra 4 w/o header, Calculus 2).
15 Placeholders: PASS (no QPushButton, single message label).
16 Stable band height: PASS at 600/1000/1600 (band height and canvas top constant over 10 tabs; clamp respected). Scroll-inside-band: only checked softly (Chemical page is a QScrollArea, strip height unchanged); not forced into overflow.
17 First tabs reachable: PASS (alpha, `sqrt(`, `diff(` found via click on each page at all three widths).
18 Dock retired: PASS (no side-panel-dock; canvas at left edge; View > Side Panel hides/shows strip+band together, canvas moves up, saved tab restored). Stale window_state from a real QMainWindow with a dock named side-panel-dock, and garbage bytes: load without error.
19 Persistence: PASS (tab 8 restored in tabs, strip highlight and band; saved 99 and -5 are clamped, exactly one highlight; hidden state persists).
20 Many tabs: PASS (11th/12th appear in order, work; removing one reflows, one highlight).
21 Minimum width: PASS at default font (window refuses < widest button + margins; all clickable). See D1.
22 Theming/accessibility: PASS (accessibleName = label; strip name "Side panel categories"; palette follows light/dark live; focus ring changes the rendering in both). Known gap G1 below.
23 Insert unchanged: PASS (mouse clicks on tabs and programmatic selection leave the edited region and its focus; band button inserts at cursor: "x+" -> "x+alpha"; startup restore does not steal focus).

## Defects
D1 (minor, edge case, spec "Very large UI font"): with an extreme font (app font 60 pt, window requested 100x700)
the window gets minimum width 504 (correct, widest button 496) but the strip is squeezed to 273 px while it needs
970 px for 9 rows, so buttons from row 3 on lie outside the strip rect (clipped/overlapping the band).
Spec says the band shrinks first, never the strip. Cause (probably): window minimum height uses the strip's non-
height-for-width minimumSizeHint (one row). Repro: scratch script sets app font 60 pt, `MainWindow()`, resize(100, 700),
compare `strip.height()` with `strip.heightForWidth(strip.width())`. At 11 pt and 13 pt, even in 400x150/400x330 windows,
the strip got its full height (OK). Low priority.

## Known gaps / notes
G1 No QAccessible "tab" role / selected state on TabStripButton (developer-disclosed; accessible names only). Spec says
"where supported"; not testable headlessly. Recommend a follow-up (QAccessibleInterface subclass or QAbstractButton
role override).
G2 Real-window pass on the Mac NOT done: the computer_* tools were not available in this session. Substitute: offscreen
`QWidget.grab()` screenshots at 600x600 (Elements, 2 strip rows, Greek letters in band, selected tab bold with blue
underline) and 1200x600 (Mechanical, single row justified, both group headers inline, no clipped labels). They looked
correct. Still to do by a human or a computer-use run: drag-resize 600-1600, arrow-key through tabs, token insert from
each functional tab, light/dark, View > Side Panel toggle, relaunch restore, real old preferences file.
G3 Weak spots in my own tests: criterion 10/22 colour checks compare grabbed pixels (cue exists, not which cue);
hasFocus() in the offscreen platform makes the focus-ring check conditional.

## Review of the developer's changed existing tests (no coverage weakened)
- test_main_window_chrome.py: criterion 5 now asserts dock is None, panel visible, panel above canvas, names, action text/checked
  (dock-area check had no equivalent left). Criterion 8 closed-state: still checked, plus action unchecked. Criterion 8 tab
  persistence: dock-width asserts removed (spec-mandated). Criterion 9: width caps removed, 400 px canvas minimum kept.
- test_main_window_blackbox.py: same pattern; criterion 8 still proves reopen after restart restores tab. Criterion 9 now
  checks canvas >= 400 at minimumSizeHint; the 120/320 caps removed (spec-mandated).
- test_spec011_side_panel_greek_blackbox.py: width-forcing test deleted, other persistence tests kept. All removals are
  dock-specific and covered by spec 022 criteria; nothing else was loosened.
- Observation: no test of the dock's "floating/moved" behaviour remains, which is correct since it no longer exists.

## IP red flags
None seen. tabstrip.py is generic flow/tab code with own naming; no vendor names, strings, colours (palette-derived), assets.
