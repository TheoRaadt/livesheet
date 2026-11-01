# 022 Side-panel tab strip: full-width, always-visible, wrapping rows

Source inspiration (concept only, nothing copied):
- General, long-established toolkit convention that a tab bar with more tabs than fit on one line
  can either scroll/elide (what Qt's default horizontal tab bar does) or wrap onto several rows
  (the classic "multi-row tab bar" found in many desktop toolkits and in dialogs with many pages).
  No specific product's tab chrome was consulted; the user-facing behaviour is defined by Theo's
  own request plus the project's gui-concepts checklist (".claude/skills/gui-concepts/SKILL.md":
  "full keyboard navigation", "clear focus/selection states", "screen-reader-friendly labels on
  custom widgets", "light and dark variants from the same token set").
- General, public usability heuristics: visibility of system state (every option visible at once,
  no hidden items behind scroll arrows), recognition over recall, and "do not truncate labels".
  Heuristics writing only; no URL-specific text is reproduced.
- Own prior specs: `docs/board/specs/007-main-window.md` (single dockable tabbed side panel) and
  `docs/board/specs/011-side-panel-category-tabs.md` (tab list, `side-panel-tabs`, Open question 5
  explicitly deferred narrow-width tab presentation to "Qt's default overflow" -- this spec now
  replaces that deferral), and the Mechanical/Electrical/Chemical tab specs 018-020, which grew the
  strip from 7 to 10 tabs.
- No Mathcad, Mathematica, Maple, MATLAB or other vendor software, help file, screenshot or
  non-public document was read for this spec.

Scope note: this spec changes only how the side panel's tab *strip* is laid out and operated. It does
not change the tab names, their order, their content, the token data, shortcuts, the dock's
open/closed persistence, or any engine/document behaviour.

Size: one phase, about 1-2 days (GUI-only; one new small custom widget plus wiring in
`livesheet/gui/sidepanel.py`; no engine, no document-format change).

---

## User story
As a LiveSheet user, I want the side panel's tab strip to use the panel's whole width and to show
every tab, always, with its full name -- so that I never have to scroll a tab strip to find a tab
and never see a clipped label such as "Mech...". When the panel is too narrow to fit all tabs on one
line, I want the tabs to continue on extra rows below (like a multi-row tab bar), pushing the tab's
content area down, rather than hiding some tabs. I noticed that the first tabs (Elements, Algebra,
Calculus) seemed to disappear in a narrow panel (I "missed the Math panel"); they must always be
visible and reachable.

## Diagnosis (why the first tabs disappear today)
The strip is Qt's stock `QTabWidget` tab bar. With 10 tabs in a 120-320 px dock it cannot show them
all, so it (a) elides long labels and (b) shows small scroll arrows and scrolls the strip, which can
leave the leftmost tabs (Elements, Algebra, Calculus) scrolled out of view. The Math toolbar that
used to hold these items was removed by spec 011, so the only way to reach them is the tab strip.
This spec treats that scrolling as the cause of Theo's remark (see Open question 1).

## Behaviour (own words)

### Layout of the strip
- The strip sits at the top of the side panel, spans the panel's full inner width (no side margins
  beyond a small uniform inset equal to the panel's own content margin), and is followed
  immediately below by the content area (the existing per-tab page).
- It is a **wrapping flow of tab buttons**: tabs are placed left to right in the fixed tab order; when
  the next tab's full-width button no longer fits on the current row, it starts a new row below.
  This is a simple greedy fill, in order. Tab order is never rearranged to pack rows better.
- Every tab button always shows its **complete label** (no ellipsis, no clipping, no abbreviation).
  The label font and size are the application's normal UI font (resizable with OS text size).
- **No scroll arrows, no overflow menu, no hidden tab** in any panel width the dock allows.
- **Rows are justified**: after rows are formed, each row's buttons are widened equally so that the
  row exactly fills the strip width (the last row is justified too, so the strip reads as a tidy
  block rather than a ragged one). Spacing between buttons is a fixed small gap (suggest 2 px) and
  between rows a fixed small gap (suggest 2 px).
- **Rows never reorder when a tab is selected.** The active tab keeps its position; the strip does
  not rotate the active tab's row next to the content (a behaviour of some older multi-row bars
  that makes tab positions jump). Stable positions support muscle memory.
- Strip height = rows x button height + gaps. The strip reports a height-for-width size, so when
  the available width changes, the row count and strip height change and the content area below
  gets the remaining height. The content area keeps its existing scroll area for long token lists.
- Minimum strip width = the widest single tab button (currently "Optimization"), so a label can never
  be clipped. The side panel's minimum width (today 120 px) must be at least that value at the
  current UI font; if the UI font is large enough that "Optimization" needs more than 120 px, the
  dock's minimum width grows to fit (labels win over the 120 px figure). See Open question 2 for the
  maximum width.

### Tab button appearance and states
- Each tab is a flat, checkable button (exactly one checked at a time) with consistent padding and a
  small rounded or squared border, in LiveSheet's own style. Three visible states: normal, hover,
  and selected.
- **Selected state** must be clearly distinguishable without relying on colour alone: it uses the
  application's accent/highlight colour for fill or underline AND a second cue (bolder weight, or a
  heavier border/underline). Colours come from the active palette/theme tokens, so light and dark
  themes both work and the selected tab is legible in both. No hard-coded colours that break in
  dark mode.
- **Keyboard focus** is shown with a visible focus ring on the focused tab button, distinct from the
  selected highlight (a tab can be selected without having focus, and vice versa).
- Tooltip: none needed (label is fully visible); do not add tooltips that merely repeat the label.

### Interaction
- **Click**: a single left click on a tab button selects that tab and shows its content, as a
  normal tab does. Clicking the already-selected tab does nothing (no flicker, no signal).
- **Keyboard**: the strip is a single tab stop (roving focus). When it has focus:
  Left / Right arrow move to the previous / next tab in tab order and select it immediately;
  Up / Down arrow move to the tab on the row above / below that is horizontally closest (if there is
  no row in that direction, nothing happens); Home / End select the first / last tab. Space or Enter
  on a focused-but-unselected tab selects it. Selecting by keyboard follows the same path as a click.
  Left on the first tab and Right on the last tab do nothing (no wrap-around).
  The existing standard tab-widget shortcuts for stepping through pages (Ctrl+Tab, Ctrl+Shift+Tab,
  and platform equivalents, where the tab widget already provides them) must keep working.
- Switching tabs by any means must not steal focus from a math region being edited on the canvas;
  clicking a tab button may take focus into the strip (acceptable), but programmatic changes
  (e.g. restoring the saved tab at startup) must not.
- **Accessibility**: each tab button exposes its label as its accessible name and a "tab" role if
  the toolkit supports it, plus its selected state; the strip exposes an accessible name such as
  "Side panel categories".

### Data and API compatibility (must keep working unchanged)
Existing code and tests rely on the following; all must behave exactly as today:
- `SidePanel.tabs` is still an object found via `findChild(QTabWidget, "side-panel-tabs")` --
  i.e. it must remain a `QTabWidget` (or subclass) whose `objectName` is `"side-panel-tabs"`.
- `tabs.count()`, `tabs.tabText(i)`, `tabs.widget(i)`, `tabs.indexOf(w)`, `tabs.currentIndex()`,
  `tabs.setCurrentIndex(i)`, and the `currentChanged(int)` signal keep their meaning. Specifically,
  `currentChanged` is emitted exactly once per actual change of the selected tab, with the new
  index, whether the change came from a click, the keyboard, or `setCurrentIndex`; it is not
  emitted when re-selecting the already-current tab. `MainWindow` still persists the index under
  the `QSettings` key `"side_panel_tab"` and restores it at startup (index range 0-9).
- Tab names and order stay exactly: Elements, Algebra, Calculus, Statistics, Optimization,
  Mechanical, Electrical, Chemical, Outline, Data (`TAB_ORDER` unchanged). `symbol_buttons`,
  `MATH_TOKENS`, `TAB_CATEGORIES`, `PLACEHOLDER_TABS` unchanged.
- Adding a tab later (a future spec) only requires adding a name to the same list; the strip
  relayouts automatically for any tab count (the wrap logic is not hard-wired to 10).

### Suggested structure (not mandated; developer's choice)
Because Qt's stock `QTabWidget`/`QTabBar` on macOS does not wrap tab rows natively, the visible strip
is a custom widget. One workable arrangement: the dock's content is a container with a vertical
layout holding (1) the wrapping strip widget (a flow layout of checkable buttons in a button group,
implementing height-for-width) and (2) the existing `QTabWidget`, kept as the page holder with its
own native tab bar hidden (`tabBar().hide()`), the strip and the hidden bar kept in sync through
`currentChanged` / `setCurrentIndex` (guarding against signal loops). This keeps `tabs.*` API, the
`side-panel-tabs` object name and `findChild(QTabWidget, ...)` all intact. An equally acceptable
alternative is a `QTabWidget` subclass that supplies its own strip; the acceptance criteria below
are written against observable behaviour, not this structure. The strip should expose two small
inspectable members for tests: a way to read the current row count, and each tab button's geometry
(exact names are the developer's choice; objectName of the strip suggested `side-panel-tab-strip`).

## Syntax proposal (own keywords)
N/A. GUI chrome only. No change to `livesheet/engine/*`, the `.lsheet` format, or any keyword.

## Acceptance criteria
Notation: strip width W is the width available to the strip inside the panel. Button widths depend
on the platform UI font, so row counts below are the *expected result for the reference font* and
the test computes them from the buttons' own `sizeHint()` widths (greedy fill with the gap above);
the numbers in the table are approximate sanity checks, not hard-coded asserts.

1. Tab list: `tabs.count() == 10` and `[tabText(i)] == [Elements, Algebra, Calculus, Statistics,
   Optimization, Mechanical, Electrical, Chemical, Outline, Data]` (unchanged; existing tests in
   `test_main_window_chrome.py`, `test_side_panel_categories.py`, `test_formula_tabs_018_020.py`
   keep passing without edits).
2. Full labels: at every tested width, each strip button's displayed text equals its tab's
   `tabText` exactly (no "..." and no truncation), and each button's width >= its text's
   `sizeHint()` width (label not clipped).
3. All visible: at every tested width, every one of the 10 buttons is visible (`isVisible()` true
   for a shown panel) and its geometry lies fully inside the strip rectangle (left >= 0, right <= W).
   No scroll-arrow buttons exist (`QTabBar.usesScrollButtons()` false on any native bar that is
   still shown, or no native bar shown at all).
4. Panel width 120 px: the widest label ("Optimization") still fits; expected about 9-10 rows
   (roughly one tab per row, with possibly the two shortest adjacent tabs, e.g. Outline + Data,
   sharing a row). Row count must equal the greedy-fill count computed from `sizeHint()`s, rows <= 10.
5. Panel width 300 px: expected about 3-4 rows (the 10 labels total roughly 750 px of button width at
   the reference font). Row count equals the greedy-fill count; first row contains Elements first.
6. Panel width 600 px (strip tested directly, or dock allowed to reach that width, see Open
   question 2): expected 2 rows (1 row only if the font is small enough for all 10 to fit).
   Row count equals the greedy-fill count.
7. Justification: at each tested width, in every row the sum of button widths plus gaps equals W
   within 1 px (rows span the full width, last row included), and all buttons in the strip have the
   same height.
8. Order: reading the buttons by (row, x) always gives the 10 names in the fixed tab order; the
   order is identical at 120, 300 and 600 px and after any resize sequence.
9. Active highlight: exactly one button is in the selected (checked) state at any time and it is
   the button for `tabs.currentIndex()`; after `setCurrentIndex(k)` for each k in 0..9 the selected
   button is button k, and its rendering differs from an unselected button's in at least two ways
   (fill/underline colour and weight/border), in both a light and a dark palette.
10. Click switching: clicking button k (via `QTest.mouseClick` on its centre) makes
    `tabs.currentIndex() == k`, shows page k (`tabs.currentWidget() is tabs.widget(k)`) and emits
    `currentChanged` exactly once with k. Clicking the already-selected button emits nothing.
11. Keyboard switching: with the strip focused and tab 0 selected, Right x2 selects tab 2
    (Calculus), Left selects tab 1, End selects tab 9 (Data), Home selects tab 0, Right on tab 9
    leaves 9 selected, Left on tab 0 leaves 0 selected. In a layout with at least 2 rows, Down from a
    tab in row 1 selects a tab in row 2 whose horizontal centre is the closest to the original
    tab's centre; Up from row 1 does nothing. Each change emits `currentChanged` once.
    Space/Enter on a focused, unselected button selects it.
12. Dock resize relayout: with the panel shown, resizing it from 300 px to 120 px increases the row
    count (never decreases), resizing back to 300 px restores the earlier row count and button
    positions exactly, and the strip's height changes accordingly; the content area's top edge sits
    immediately below the strip's bottom edge at every width, with no overlap and no gap > 4 px.
    Relayout happens on the resize event itself (no extra user action needed) and while the user
    drags the dock separator.
13. Persistence unchanged: selecting tab 8 (Outline), closing and re-creating `MainWindow` with the
    same settings restores tab 8 as selected, and both the stack page and the strip highlight show
    it (existing assertion in the chrome tests, indexes 2 and 8/9 still valid).
14. Many tabs: appending an 11th and a 12th tab programmatically (`tabs.addTab(widget, "Extra")`)
    in a test appears in the strip, in order, with no code change, and the layout stays valid
    (extends criteria 3, 7, 8). Removing a tab removes its button and re-flows.
15. Narrow-width robustness: at the minimum panel width, no exception, no zero-size button, and
    switching through all 10 tabs by click still shows each page.
16. First tabs reachable (Theo's complaint): at 120, 300 and 600 px, the Elements, Algebra and
    Calculus buttons are visible and their centres are inside the visible strip region, and clicking
    each shows its tab's content (Elements page has the Greek-letter buttons, Algebra has `sqrt(`,
    Calculus has `diff(`).
17. Theming: switching the application palette between light and dark (or re-polishing the widget)
    updates tab colours without restart; selected and unselected states remain distinguishable in
    both. Focus ring visible on the focused button in both.
18. Accessibility: each button has `accessibleName()` equal to its tab label; the strip has an
    accessible name (suggested "Side panel categories").

## Edge cases
- Very large OS/UI font: buttons grow, more rows form; if the widest label exceeds the dock's
  current minimum width, the dock's minimum width is raised to fit (labels never clipped). The
  content area may then become short; it keeps its scroll area.
- Very short window: the strip can take up to 10 rows at 120 px; the content area below shrinks and
  scrolls. The strip itself never scrolls and never gets clipped by the content area (the strip is
  allotted its height first). If the window is so short that the strip alone does not fit, the dock
  as a whole is clipped by the window, which is acceptable.
- Floating (undocked) side panel: same behaviour; relayout on the floating window's resize.
- Disabled or hidden tab (a future feature): a disabled tab's button is shown disabled and not
  selectable; a hidden tab is removed from the flow (not leaving a gap). Not exercised by any current
  tab.
- Selecting a tab programmatically at startup (restoring `"side_panel_tab"`) must not emit a second
  settings write beyond the normal one and must not steal canvas focus.
- A stored `"side_panel_tab"` index outside 0..count-1 (hand-edited settings) is clamped to the
  valid range by existing behaviour; the strip never shows zero or two selected tabs.
- Right-to-left layouts: the flow mirrors (first tab at the right); tab order in the logical list
  is unchanged. Not required to be tested now.
- Placeholder tabs (Statistics, Optimization, Outline, Data) behave exactly like functional tabs
  for selection; their content is unchanged.

## IP check
Pass. A wrapping/multi-row tab bar is generic toolkit chrome that has existed in desktop toolkits
for decades and across many unrelated applications and dialogs; it is not tied to any
engineering-calculation product, and no vendor's layout, icon set, colour palette or ribbon
arrangement was consulted. The behaviours specified (greedy flow, justified rows, roving-focus
arrow-key navigation, accent-plus-second-cue selected state) are standard accessibility/usability
practice and Theo's own request. No on-canvas interaction technique is introduced (ip-cleanroom
rule 6): this is ordinary dock chrome. No vendor names, text, icons, CSS/QSS, or code used. Theo's
phrase "like a word processor ribbon" is used only as a loose description of "tabs continue on
further rows"; this spec does not reproduce any ribbon (groups, galleries, collapsing commands) and
defines no ribbon-like chrome. Not legal advice.

## Fits current architecture?
- `livesheet/gui/sidepanel.py` only: replace the visible stock tab bar of `SidePanel.tabs` (current
  lines: `QTabWidget` created, tabs added in `TAB_ORDER`, `self.setWidget(self.tabs)`) with the
  custom wrapping strip + page holder described above. `TAB_ORDER`, `TAB_CATEGORIES`,
  `MATH_TOKENS`, `PLACEHOLDER_TABS`, `_build_functional_tab`, `symbol_buttons` untouched.
- `livesheet/gui/main_window.py`: no change required (it already uses `side_panel.tabs`
  `setCurrentIndex` / `currentChanged` and `QSettings["side_panel_tab"]`). The `SidePanel` dock's
  `setMaximumWidth(320)` may need review (Open question 2).
- Theming: use the existing palette/theme tokens in `livesheet/gui/theme.py` rather than hard-coded
  colours (developer to check for existing accent token names).
- No engine, no document, no dependency changes.
- Tests: new `tests/test_side_panel_wrapping_tabs.py` covering criteria 1-18 under
  `QT_QPA_PLATFORM=offscreen` (row counts computed from `sizeHint()`s so they are font-independent;
  widths 120/300/600 set via `resize()` on the shown panel or the strip). Existing tab tests must
  pass unchanged. The tester also does a real-window pass on Theo's Mac: open the side panel, drag
  the dock separator between its minimum and maximum width and confirm tabs wrap and unwrap smoothly,
  that no label is truncated and no scroll arrows appear, that Elements/Algebra/Calculus are always
  visible, click and arrow-key through all 10 tabs, check light and dark appearance, and relaunch to
  confirm the saved tab is restored.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **"I miss the Math panel."** This spec treats Theo's remark as caused by the first tabs
   (Elements, Algebra, Calculus -- the successors of the removed Math toolbar, spec 011) being
   scrolled out of sight in a narrow panel by the stock tab strip. If instead Theo meant a *separate*
   Math panel/toolbar (for example the removed Math toolbar, or a dedicated dock for math
   insertions), that is a different feature and needs a new request; nothing here reintroduces a
   Math toolbar or splits the side panel. [Recommend asking Theo to confirm after seeing this fix.]
2. **Dock maximum width.** `SidePanel` is currently capped at 320 px (`setMaximumWidth(320)`), so a
   600 px panel cannot occur in the real window; criterion 6 therefore tests the strip directly at
   600 px. Should the cap be raised (for example to 600 px or removed) so users can widen the panel
   until all tabs sit on one or two rows? [Recommend raising it to about 600 px; trivial change,
   but a layout decision for Theo.]
3. **Justified vs. natural-width rows.** The spec justifies every row (buttons stretch to fill the
   width, last row too). Alternative: natural-width buttons, left-aligned, ragged right edge.
   [Recommend justified, matching "uses the full width"; easy to change.]
4. **Active row behaviour.** The spec keeps tab positions fixed when a tab is selected (rows never
   rotate). Some older multi-row bars move the active row next to the content; rejected here for
   stability. [Recommend accepting.]
5. **Row count at 120 px.** At the narrowest width nearly every tab gets its own row (9-10 rows,
   a tall strip eating most of the panel height). If Theo finds that too tall, a later option is to
   lower the dock's minimum width bound upward (e.g. 160 px) or reduce button padding; not part of
   this spec. [Flag only.]
6. **Handoff-log append.** The specialist toolset had no append tool for the long
   `docs/board/log.md`; the manager should add the handoff line (given in the report) if not
   already added.
