# 022 Window-wide wrapping tab strip with a horizontal button band (replaces the narrow side-panel tabs)

Revision note: first draft (2026-11-01) kept the strip inside the 120-320 px side panel. Theo then
clarified (relayed by the coordinator) that the strip must instead span the WHOLE application window
width, directly under the menu bar and above the canvas. This revision replaces the earlier design;
the file name is kept for board continuity.

Source inspiration (concept only, nothing copied):
- General, long-established toolkit convention that a tab bar with more tabs than fit on one line
  can either scroll/elide (Qt's stock horizontal tab bar) or wrap onto several rows (the classic
  multi-row tab bar found in many desktop toolkits and dialogs). Wrapping is a generic widget
  behaviour, not a feature of one product.
- General, public usability heuristics: visibility of system state (every option visible at once,
  nothing hidden behind scroll arrows), recognition over recall, do not truncate labels.
  Heuristics writing only; no text reproduced.
- Project's own `.claude/skills/gui-concepts/SKILL.md`: "clear primary canvas vs. chrome", "full
  keyboard navigation", "clear focus/selection states", "screen-reader-friendly labels on custom
  widgets", "light and dark variants from the same token set".
- Own prior specs: 007-main-window.md (dockable tabbed side panel), 011-side-panel-category-tabs.md
  (tab list; its Open question 5 deferred narrow-width tab presentation to Qt defaults, which this
  spec now replaces), 018-020 (Mechanical/Electrical/Chemical tabs, growing the strip to 10 tabs).
- No Mathcad, Mathematica, Maple, MATLAB or other vendor software, help, screenshot or non-public
  document was read. Theo's phrase "like a ribbon" is taken only as "a tab strip across the window
  whose tabs continue on further rows"; no ribbon features are specified (see IP check).

Scope note: changes WHERE the tab strip and the selected tab's token buttons live and how the strip
lays out. Does not change tab names, order, token data (MATH_TOKENS, TAB_CATEGORIES, labels, tokens,
tooltips), shortcuts, engine, or the .lsheet format.

Size: one phase, about 2-3 days (GUI-only: new strip widget, new flow-layout band, main-window
re-parenting, test updates for the dock removal).

---

## User story
As a LiveSheet user, I want the category tabs (Elements, Algebra, Calculus, Statistics,
Optimization, Mechanical, Electrical, Chemical, Outline, Data) across the full width of the window,
right under the menu bar, with every tab always visible and fully labelled. When the window is too
narrow for one line, I want the tabs to continue on further rows below instead of hiding behind
scroll arrows or clipped labels. I never want Elements, Algebra or Calculus to disappear because a
strip was scrolled. The buttons of the selected tab should be right there under the strip, using the
window's width, so I do not have to squeeze them into a 120 px column.

## Diagnosis
The stock tab bar in the 120-320 px side panel elides labels and scrolls, hiding the leftmost tabs
(Elements, Algebra, Calculus). The Math toolbar that once held them was removed by spec 011, so they
became unreachable until the user found the scroll arrows. Moving the strip to the window's full
width, with wrapping rather than scrolling, removes the cause (see Open question 1 on "Math panel").

## Decisions taken in this spec (with justification)
1. **Where the selected tab's buttons appear: a horizontal "button band" directly under the strip,
   spanning the window width** (chosen), instead of keeping the existing narrow side-panel content
   below the strip. Why: the strip is now window-wide, so its content belongs with it; tokens are
   reached constantly while typing, so keeping them adjacent to the canvas shortens eye/mouse
   travel; a wide band holds 40 Greek/constant buttons in 1-3 rows instead of a 40-row scrolling
   column; and it frees the canvas from a permanent left column. Alternative (keep content in the
   side panel dock, strip window-wide above) is recorded as Open question 2.
2. **The side-panel dock is retired as the tab holder.** All 10 tabs (including Outline and Data)
   live in the strip and their pages show in the band. Why: Theo asked for all 10 tabs visible in the
   window-wide strip; splitting 8 in the strip and 2 in a dock would break the unchanged 10-tab
   model that existing tests and the saved-tab setting rely on. Outline and Data are placeholders
   today (one muted message), which fit in the band. When they get real content (tree, dataset list)
   they will want a tall panel: see Open question 3.

## Behaviour (own words)

### Placement and structure (top to bottom of the window)
menu bar, Standard toolbar (unchanged), **tab strip**, **button band**, canvas/worksheet, status bar.
The strip and band together form one widget that spans the full window width (inner margin small and
uniform, suggest 4 px), is not movable or floatable, and is shown/hidden by the existing
`View > Side Panel` entry (label kept for compatibility; renaming is Open question 5). Whether it is
implemented as a non-movable toolbar-area widget with a toolbar break or as a container above the
canvas in the central layout is the developer's choice; it must sit between the Standard toolbar and
the canvas at every window size.

### The tab strip
- Wrapping flow of tab buttons, left to right in the fixed tab order. When the next tab's full-width
  button no longer fits on the current row it starts a new row below (greedy fill, in order; tabs are
  never reordered to pack better).
- Every tab always shows its complete label (no ellipsis, no clipping). Normal UI font.
- No scroll arrows, no overflow menu, no hidden tab at any window width the window allows.
- Rows are justified: after rows are formed, each row's buttons are widened equally so the row fills
  the strip width exactly (last row too). Fixed small gaps between buttons and rows (suggest 2 px).
  (Open question 4 covers natural-width alternative.)
- Positions are stable: selecting a tab never moves it or rotates rows.
- Strip height = rows x button height + gaps, via height-for-width; relayout happens on every
  window resize event, including during drag-resizing.
- Minimum strip width = widest single tab button ("Optimization" today); the main window's minimum
  width is at least this plus margins, so labels are never clipped (labels win over any smaller
  hand-set window minimum).
- Tab button states: normal, hover, selected (exactly one). Selected state uses the theme accent plus
  a second non-colour cue (bolder weight and/or heavier underline/border), colours taken from the
  active palette/theme tokens so light and dark both work (check `livesheet/gui/theme.py` for
  existing tokens; no hard-coded colours). Keyboard focus ring distinct from the selected look.
- Interaction: click selects (clicking the current tab does nothing). Keyboard: the strip is one tab
  stop with roving focus; Left/Right move to previous/next tab and select it; Up/Down move to the
  horizontally closest tab on the row above/below (nothing if none); Home/End first/last; Space or
  Enter selects a focused unselected tab; no wrap-around at ends. Standard page-stepping shortcuts
  (Ctrl+Tab / Ctrl+Shift+Tab or platform equivalents) work where the tab model provides them.
  Programmatic selection (restoring the saved tab at startup) never steals canvas focus; switching
  tabs never interrupts or steals focus from a region being edited.
- Accessibility: each button's accessible name is its label (role "tab" and selected state where
  supported); the strip's accessible name is "Side panel categories".

### The button band (content of the selected tab)
- Directly under the strip, full width. It shows only the selected tab's page.
- Functional tabs: the page is a wrapping flow of the same bordered click-to-insert buttons used
  today (same labels, tokens, tooltips; clicking still calls `insert_token(token)`), left to right,
  wrapping to further rows at the window width. Tabs with sub-groups (Elements: Statements,
  Constants, Greek letters; Mechanical, Electrical, Chemical groups) show each group's small grey
  header label inline, and each group starts on a new row. Single-category tabs (Algebra,
  Calculus) show no header, as today.
- Placeholder tabs (Statistics, Optimization, Outline, Data): the same muted, centred, wrapped
  one-line message as today, in the band.
- **Band height is stable across tab switches**: it equals the tallest page's required height at the
  current window width, clamped to a maximum (suggest 4 rows of buttons; or about 25 percent of the
  window height if larger). A page taller than the clamp scrolls vertically inside the band (the
  strip never scrolls). Height recomputes on window resize, not on tab selection, so the canvas does
  not jump when switching tabs.
- Buttons keep their natural width (not justified); long labels (e.g. "Resultant (2 forces)") are not
  elided; a button never exceeds the band width.

### What happens to the side-panel dock
- The `QDockWidget` `side-panel-dock` (left, 120-320 px) no longer exists as a dock; there is no
  permanent left column and the canvas gains its width. Its 120/320 px width caps and dock-width
  persistence no longer apply. A stale saved `"window_state"` naming `side-panel-dock` must load
  without error (Qt skips unknown docks).
- `SidePanel` stays as the name of the owning object so `win.side_panel` keeps working (it may become
  a plain QWidget container rather than a QDockWidget). `win.side_panel.tabs` and
  `win.side_panel.symbol_buttons` are unchanged in meaning.

### Compatibility that must hold
- `win.side_panel.tabs` is a `QTabWidget` (or subclass), `objectName == "side-panel-tabs"`, found by
  `findChild(QTabWidget, "side-panel-tabs")`. It remains the model of the 10 pages: `count()`,
  `tabText(i)`, `widget(i)`, `indexOf`, `currentIndex()`, `setCurrentIndex(i)`, and the
  `currentChanged(int)` signal all behave as today. `currentChanged` fires exactly once per real
  change (click, keyboard or code), never for re-selecting the current tab. Its native tab bar is
  hidden; the strip drives it and mirrors it without signal loops. Note: the page widgets of `tabs`
  are displayed in the band, so the `tabs` widget itself is hosted in the band area (page area of
  the QTabWidget with hidden bar), which keeps `tabs.currentWidget()` correct.
- Order and names unchanged: Elements, Algebra, Calculus, Statistics, Optimization, Mechanical,
  Electrical, Chemical, Outline, Data. `MainWindow` keeps persisting the index under `QSettings`
  `"side_panel_tab"` (0-9) and restoring it.
- Adding a tab later needs only a new name/page; the strip re-flows for any count.
- Existing tests that assert dock-specific facts (the `side-panel-dock` object, 120/320 px width
  caps, dock open/close/width persistence from specs 007/011 criteria 8-9) must be updated by the
  tester/developer to the new equivalent (strip+band visibility via `View > Side Panel`, tab-index
  persistence); the developer lists every changed test in the handoff. Tests that only use
  `side_panel.tabs` need no edit.

## Syntax proposal (own keywords)
N/A. GUI chrome only. No change to `livesheet/engine/*`, `.lsheet`, or keywords.

## Acceptance criteria
Notation: W = window content width in px. Button widths depend on the platform font, so row counts
are computed in tests by greedy fill from the buttons' `sizeHint()` widths plus the gap; the
approximate numbers below (10 tab labels total about 750 px of button width at the reference font)
are sanity checks, not hard-coded asserts.

1. Unchanged model: `tabs.count() == 10`; `[tabText(i)]` equals the order above; existing tests in
   test_main_window_chrome.py, test_side_panel_categories.py, test_formula_tabs_018_020.py that use
   only `side_panel.tabs` pass without edits.
2. Placement: the strip's top edge is at or below the Standard toolbar's bottom edge, above the band,
   which is above the canvas; the strip and band span W minus the uniform inner margin (left edge <=
   margin+1, right edge >= W - margin - 1) at W = 600, 1000, 1600.
3. Full labels: at W = 600, 1000, 1600 each strip button's text equals its tab label exactly (no
   ellipsis) and its width >= its text's `sizeHint()` width.
4. All visible: at those widths all 10 buttons are visible and lie fully inside the strip rectangle;
   no scroll-arrow buttons exist (no native bar shown, or `usesScrollButtons()` false).
5. W = 600 px: expected 2 rows (about 750 px of total button width; the number equals the greedy
   count). Row 1 starts with Elements.
6. W = 1000 px: expected 1 row (equals greedy count; a very large font may give 2).
7. W = 1600 px: expected 1 row.
8. Justification: in every row, sum of button widths plus gaps equals the strip width within 1 px
   (including the last row); all buttons have equal height.
9. Order: reading buttons by (row, x) gives the 10 names in tab order at every width and after any
   resize sequence.
10. Active highlight: exactly one button selected at any time, and it is button
    `tabs.currentIndex()`; after `setCurrentIndex(k)` for k in 0..9 the selected button is k; its
    rendering differs from unselected buttons in at least two ways, in light and dark palettes.
11. Click: clicking button k makes `currentIndex() == k`, `currentWidget() is widget(k)`, the band
    shows page k, and `currentChanged` is emitted exactly once with k; clicking the current button
    emits nothing.
12. Keyboard: with the strip focused and tab 0 selected: Right x2 selects tab 2 (Calculus), Left
    selects 1, End selects 9, Home selects 0, Right on 9 and Left on 0 do nothing. In a 2-row layout
    (W = 600) Down from a row-1 tab selects the row-2 tab with the closest horizontal centre; Up from
    row 1 does nothing. Space/Enter on a focused unselected button selects it. One
    `currentChanged` per change.
13. Window resize relayout: resizing the window 1600 -> 1000 -> 600 -> 1000 -> 1600 px: row count
    never decreases while narrowing, and returning to a width restores that width's earlier row count
    and button positions exactly; the band's top edge is directly under the strip's bottom edge
    (gap <= 4 px) and the canvas top is directly under the band at every width; relayout needs no
    user action and also happens during drag-resize.
14. Band content: with Elements selected at W = 1600 the band contains all 40 Elements buttons (7 +
    33 Greek; `symbol_buttons` unchanged), group headers Statements/Constants/Greek letters each
    start a new row, and clicking the alpha button inserts `alpha` (token unchanged). With
    Mechanical selected the Statics and Strength of Materials headers appear and
    "Resultant (2 forces)" is shown in full. Algebra shows 4 buttons without a header, Calculus 2.
15. Placeholder tabs: Statistics, Optimization, Outline, Data show only their existing message in
    the band and contain no `QPushButton`.
16. Stable band height: at a fixed W, selecting each of the 10 tabs in turn leaves the band's height
    and the canvas's top edge unchanged; changing W may change them. Band height never exceeds the
    clamp; a page taller than the clamp has a vertical scrollbar inside the band while the strip
    height is unaffected.
17. First tabs reachable: at W = 600, 1000, 1600 the Elements, Algebra and Calculus buttons are
    visible and clicking each shows its page (Elements has the alpha button, Algebra `sqrt(`,
    Calculus `diff(`).
18. Dock retired: `win.findChild(QDockWidget, "side-panel-dock")` is None; the canvas starts at the
    window's left inner edge (no left column); `View > Side Panel` toggles the visibility of strip +
    band together (hidden: neither visible, canvas moves up; shown again restores the saved tab);
    loading a stale saved `"window_state"` that names `side-panel-dock` raises nothing.
19. Persistence: select tab 8 (Outline), close, recreate `MainWindow` with the same settings: tab 8
    is selected in both `tabs` and the strip highlight and the band shows its message. Out-of-range
    saved index is clamped; never zero or two selected tabs.
20. Many tabs: appending an 11th and 12th tab in a test appears in the strip in order and the band
    works; removing a tab removes its button and re-flows (extends 4, 8, 9).
21. Minimum width: the window's minimum width is >= the widest tab button + margins; at that
    minimum, no exception, no zero-size button, every tab clickable (up to 10 rows).
22. Theming and accessibility: switching light/dark updates strip and band without restart;
    focus ring visible on the focused button in both; each button `accessibleName()` equals its
    label; the strip has an accessible name.
23. Insert behaviour unchanged: clicking any band button while a math region is being edited inserts
    its token at the cursor, exactly as the old side panel did; switching tabs does not move focus
    away from the edited region.

## Edge cases
- Very large UI font: buttons grow, more strip rows; the window minimum width rises to fit the widest
  label. The band clamp may then force the band to scroll. The canvas keeps a reasonable minimum
  height; if the window is too short for strip + band + canvas the band is shrunk first (clamp
  lowers, scroll appears), never the strip.
- Strip rows plus band can take a sizeable share of a short window; accepted, user can hide it via
  `View > Side Panel`.
- A page with a long group (Chemical, 5 groups, 21 buttons) at W = 600 may need several rows; it
  scrolls inside the band if over the clamp.
- Placeholder messages are single lines; band height for them is the same stable band height.
- Disabled or hidden tab (future): disabled shown disabled and not selectable; hidden removed from
  the flow with no gap. Not used today.
- Right-to-left layouts: flow mirrors; logical order unchanged. Not tested now.
- Narrow window plus justification: a row holding one wide tab stretches it to full width; that is
  intended.

## IP check
Pass. A window-wide tab strip with wrapping rows over a band of buttons is generic desktop-toolkit
chrome (multi-row tab bars and wrapping button flows exist across many unrelated applications,
dialogs and toolkits). No vendor's layout, icon set, colour palette, group/gallery arrangement or
command-collapsing behaviour was consulted or reproduced; no ribbon-specific features (contextual
tabs, galleries, collapsing groups, minimising by double-click, quick-access bar) are specified, and
the tab names are LiveSheet's own existing ones. Tab strip + content band is a common pattern with
many precedents (property sheets, settings pages, tabbed toolboxes) and is not a technique tied to
the engineering-calculation-tool category; it is ordinary dock/window chrome and introduces no
on-canvas interaction (ip-cleanroom rule 6). Theo's "like a ribbon" wording is acknowledged; to
stay on the safe side the spec deliberately keeps the interaction minimal and does not copy any
ribbon's behaviours. Manager may still wish to confirm this with Theo (Open question 6). No vendor
text, icons, CSS/QSS or code used. Not legal advice.

## Fits current architecture?
- `livesheet/gui/sidepanel.py`: `SidePanel` stops being a `QDockWidget` (or remains the owner object
  of `tabs`/`symbol_buttons`); `_build_functional_tab` changes from a vertical button list in a
  `QScrollArea` to a wrapping flow (flow layout with inline group headers) in a scroll area bound to
  the band; add the strip widget (flow of checkable buttons, height-for-width, roving focus). Data
  (`MATH_TOKENS`, `TAB_CATEGORIES`, `TAB_ORDER`, `PLACEHOLDER_TABS`) untouched.
- `livesheet/gui/main_window.py`: replace `addDockWidget(LeftDockWidgetArea, side_panel)` and the
  `toggleViewAction` hookup with placing the strip+band between the Standard toolbar and the canvas
  and a `View > Side Panel` checkable action driving its visibility (persisted in settings);
  keep `side_panel.tabs.setCurrentIndex(settings["side_panel_tab"])` and the `currentChanged`
  persistence. Remove any code referencing the dock's width caps.
- `livesheet/gui/theme.py`: use existing tokens; add tokens for tab selected/hover only if needed.
- No engine, document or dependency changes.
- Tests: new `tests/test_wrapping_tab_strip.py` for criteria 2-23 under `QT_QPA_PLATFORM=offscreen`
  (row counts from `sizeHint()` greedy fill; window widths via `resize()` on a shown `MainWindow`);
  update dock-specific assertions in existing tests (list them in the handoff). Tester also does a
  real-window pass on Theo's Mac: drag-resize the window across ~600 to ~1600 px and watch the
  strip wrap/unwrap smoothly with no truncated label or scroll arrow; confirm Elements/Algebra/
  Calculus always visible; click and arrow-key through all 10 tabs; insert a token from each
  functional tab into a region; check that the canvas does not jump when switching tabs; light and
  dark appearance; hide/show via `View > Side Panel`; relaunch and confirm the saved tab restored;
  confirm an old preferences file naming `side-panel-dock` opens cleanly.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **"I miss the Math panel."** Treated as caused by Elements/Algebra/Calculus (successors of the
   removed Math toolbar, spec 011) being scrolled out of sight in the narrow tab strip. If Theo meant
   a separate Math panel/toolbar (e.g. the old Math toolbar or its own dock), that is a different
   feature and needs a new request; this spec reintroduces neither.
2. **Content location.** This spec puts the selected tab's buttons in a window-wide band under the
   strip. Alternative: keep the narrow side-panel dock for the button list and only move the strip
   to the window-wide row (strip then drives the dock). The band is recommended (justified above);
   the alternative would keep dock-related tests and the left column.
3. **Outline and Data future home.** They sit in the strip and show placeholders in the band today.
   Once they have real content (document outline tree, dataset list) they probably need a tall
   panel: recommend then keeping those two tabs in the strip but opening their content in a
   re-introduced left dock (or splitter) via a follow-up spec. Decide now or defer.
4. **Justified vs. natural-width tabs.** Rows are justified to the full width (so at 1600 px each of
   10 tabs is about 160 px wide). Alternative: natural-width, left-aligned, ragged right. Recommend
   justified, matching "menu-wide"; trivial to change.
5. **Menu label.** `View > Side Panel` is kept so existing tests and habits work, although the thing
   is no longer a side panel; consider renaming to "Palette Tabs" (and the `SidePanel` class
   likewise) in a later cleanup. Needs Theo's wording preference.
6. **Ribbon wording / IP.** Theo's "like a ribbon" is treated as loose description only. The manager
   may want to confirm with Theo that no further ribbon-like behaviour (groups, galleries, collapse)
   is wanted; adding such features would need a fresh IP review.
7. **Vertical space.** A 2-row strip plus a band of up to 4 button rows takes noticeable height at
   narrow widths (600 px). The clamp (4 rows or 25 percent of window height) is a suggestion;
   Theo may prefer a tighter or looser value, or a way to collapse the band.
8. **Handoff-log append.** The specialist toolset has no append tool for the long
   docs/board/log.md (rewriting the 138-line file risked losing content), so the manager should add
   the line given in the report.
