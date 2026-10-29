# 007 Main window chrome and layout polish

Source inspiration (concept only, nothing copied):
- https://en.wikipedia.org/wiki/Toolbar, https://en.wikipedia.org/wiki/Status_bar,
  https://en.wikipedia.org/wiki/Menu_bar — general, vendor-neutral descriptions of these
  three chrome elements as they exist across essentially all desktop GUI toolkits, public, checked
  2026-10-29.
- https://en.wikipedia.org/wiki/Dark_mode — general description of light/dark theming and
  following an OS-level appearance setting, public, checked 2026-10-29.
- https://www.nngroup.com/articles/ten-usability-heuristics/ — Jakob Nielsen's ten usability
  heuristics (consistency and standards, visibility of system status, aesthetic/minimalist
  design, recognition rather than recall), general and vendor-neutral, public, checked 2026-10-29.
  Concept only: "one command, reachable the same way everywhere" and "show system status" are
  used below; no text is quoted beyond the heuristic names.
- https://m3.material.io/foundations — Material Design 3 foundations (layout, spacing scale,
  elevation, limited accent colour), an openly published, CC BY 4.0-licensed general design
  system (licence checked 2026-10-29; CC BY permits this kind of reuse, unlike an NC/SA licence).
  Used only for the generic ideas "small consistent spacing scale" and "one accent colour used
  sparingly," never for any specific widget shape, icon, or colour value — those are this spec's
  own choices.
- `.claude/skills/gui-concepts/SKILL.md` — the team's own idea checklist, itself distilled from
  the kinds of general, product-agnostic sources above.
- No Mathcad, Mathematica, Maple or other vendor software, documentation or screenshot was read
  or consulted for this spec. No specific competitor's toolbar layout, icon set, colour palette,
  panel taxonomy or chrome arrangement is described or used anywhere below.

Scope note: this spec covers the main window's *chrome* — toolbars, menu organisation, a new
dockable side panel's shell, status bar, and application-level theming — not the free-form
canvas's content model (regions, their data, evaluation order). Where the side panel needs
placeholder tabs for features that do not exist yet (document outline/ToC, dataset browser), this
spec only builds the empty shell; backlog items 7a and 8a own what goes inside them.

Size: three phases, about 4.5 days total.
- **Phase G1 (toolbars + status bar + first-run hint)**: a new "Standard" toolbar, View-menu
  toggles for both toolbars, `QMainWindow` state persistence, three new status-bar indicators, and
  the empty-canvas hint. About 1.5 days.
- **Phase G2 (side panel shell)**: the dockable, tabbed side panel (`Symbols` tab functional,
  `Outline`/`Data` tabs as placeholders), View-menu toggle, persistence. About 2 days.
- **Phase G3 (theming)**: application-level light/dark/follow-system palette switch for standard
  Qt chrome, persisted preference. About 1 day.

---

## User story
As a LiveSheet user, I want the main window to read as one coherent, modern desktop application —
predictable places for file/view controls, a quick way to reach symbol insertion without hunting
through menus, a single consistent place where future panels (outline, dataset browser) will
appear, and a status bar that tells me at a glance whether my sheet currently evaluates cleanly —
rather than a single toolbar and a bare status bar bolted onto a canvas.

## Behaviour (own words)

### Toolbars
- A new **Standard** toolbar (`objectName "standard-toolbar"`) sits above today's **Math**
  toolbar (`objectName "math-toolbar"`, unchanged content) in the top toolbar area. It holds, in
  order: New, Open, Save, a separator, Export PDF, a separator, Recalculate — the exact same
  `QAction` objects already created for the File/Calculate menu entries, so a toolbar click and
  the matching menu click are always the same command (Nielsen's "consistency and standards").
- Both toolbars are ordinary, movable `QToolBar`s: a user may drag one to another toolbar area, or
  float it, using the toolkit's own chrome; nothing bespoke is added for dragging or floating.
- `View` gains two checkable entries, "Standard Toolbar" and "Math Toolbar", each toggling that
  toolbar's visibility independently.
- Toolbar position and visibility persist across restarts via `QMainWindow.saveState()` /
  `restoreState()`, stored in the existing `QSettings` object under a new key `"window_state"`,
  restored at startup the same way `"geometry"` already is.

### Side panel
- `View` gains a checkable "Side Panel" entry (checked by default on first launch) toggling a new
  `QDockWidget` (`objectName "side-panel-dock"`), docked to the window's left edge by default,
  containing a `QTabWidget` (`objectName "side-panel-tabs"`) with three tabs: **Symbols**,
  **Outline**, **Data**.
  - **Symbols**: the same set of insertable tokens as today's Math toolbar (same labels, tokens,
    tooltips), presented as a scrollable vertical list grouped under small category headers
    (Constants, Operators, Calculus, Statements). Clicking an entry calls the exact same
    `insert_token`/action as the matching Math toolbar button — a second reachable path to an
    existing command, not a second implementation of it (same consistency idea as the toolbar
    button).
  - **Outline** and **Data**: each shows only a centred, muted one-line placeholder (own wording,
    e.g. "Document outline will appear here once headings are available." /
    "Imported datasets will appear here once available.") and no interactive content. This spec
    adds no outline or dataset logic at all; it only reserves the tab so that backlog 7a (headings/
    ToC) and 8a (dataset import) have one obvious, pre-existing place to slot their panel content
    into, instead of inventing their own dock later.
- The dock has a minimum width of 120 px and a maximum of 320 px (an ordinary `QDockWidget` size
  policy); the canvas view keeps at least 400 px of width at the window's minimum size, so the
  panel can never fully obscure the canvas.
- Dock open/closed state, width, and active tab persist across restarts via the same
  `saveState()`/`restoreState()` mechanism as the toolbars.

### Status bar
- The status bar's permanent (right-hand) area shows, left to right: an evaluation-status label
  (`objectName "status-eval-label"`), a precision label (`objectName "status-precision-label"`),
  then the existing zoom label (`objectName "status-zoom-label"`, previously unnamed). The
  existing transient message area on the left (`statusBar().showMessage(...)`, e.g. "Saved x.lsheet")
  is unchanged.
- **Evaluation status**: reads "Ready" after any `Worksheet.recalculate()` pass that leaves zero
  regions in `"error"` status; reads "N error" / "N errors" when one or more regions are left in
  `"error"` status (same count `recalculate()` already computes for its transient message, just
  also kept visible as a permanent indicator instead of disappearing after the transient message
  times out — the point raised by Nielsen's "visibility of system status"). If a single pass takes
  longer than 300 ms (measured), the label reads "Calculating…" for the duration of that pass
  before switching to its Ready/error text; passes under 300 ms never show "Calculating…", so
  ordinary fast recalculations never flicker (gui-concepts: "progress indication for anything over
  ~300ms").
- **Precision**: always reads "{engine.significant} sig. figs"; updates immediately when
  `Calculate > Result Precision…` changes it. Clicking the label opens the same dialog as that menu
  entry (same consistency idea again).
- **Zoom**: unchanged behaviour, only gains an `objectName` for testability.

### Empty-canvas ("first-run") hint
- A worksheet with zero regions — a brand-new document, or an existing one emptied back to zero —
  shows a single muted line of hint text near the crosshair's starting position (own wording, e.g.
  "Click to place the cursor, then start typing"), painted as part of `Worksheet`'s background
  drawing. It is not a region, is never stored in the `.lsheet` file, and is excluded from PDF
  export the same way the crosshair already is (`export_pdf` already hides the crosshair while
  rendering).
- The hint disappears the instant any region exists (even one still being edited) and reappears
  automatically if the sheet is emptied again.

### Theming
- `View` gains an "Appearance" submenu with three mutually exclusive checkable entries: "Follow
  System" (default), "Light", "Dark".
- Selecting "Light" or "Dark" applies a corresponding `QPalette` to the running `QApplication`
  immediately, no restart needed; Qt's own standard palette propagation restyles menus, toolbars,
  the side panel, dialogs, the status bar and scrollbars. Selecting "Follow System" re-reads the
  OS-level colour scheme at the moment of selection and applies the matching palette.
- The chosen value persists in `QSettings` under `"appearance"` and is applied before the window
  is first shown on the next launch (no visible flash of the non-chosen theme).
- Out of scope for this spec: recolouring anything the canvas paints itself — grid lines, region
  borders, the crosshair, plot chart colours. Those are drawn with their own literal colours today
  and are left untouched here; see Edge cases and Open question 3. This spec only restyles the
  standard, toolkit-drawn chrome.

## Syntax proposal (own keywords)
N/A — this is window chrome, not sheet syntax. No change to `livesheet/engine/syntax.py`, the
`.lsheet` statement grammar, or any evaluator keyword.

## Acceptance criteria

Toolbars & menu
1. On first launch (no `"window_state"` in `QSettings`), the window shows two stacked toolbars in
   the top toolbar area: `"standard-toolbar"` above `"math-toolbar"` (unchanged content), both
   visible and movable.
2. `"standard-toolbar"` contains, in order: New, Open, Save, separator, Export PDF, separator,
   Recalculate — the same `QAction` objects already wired to the File/Calculate menu entries
   (toolbar click and menu click invoke the identical slot, verified by identity, not just by
   label).
3. `View` has two new independent checkable entries, "Standard Toolbar" and "Math Toolbar"; toggling
   one does not change the other's visibility.
4. Dragging `"math-toolbar"` to a different toolbar area (e.g. below Standard, or to the window's
   left edge) and restarting the app restores it to the dragged position, via
   `saveState()`/`restoreState()` keyed under `"window_state"`.

Side panel
5. `View` has a checkable "Side Panel" entry (checked by default on first launch) toggling
   `"side-panel-dock"`, docked left by default, containing `"side-panel-tabs"` with exactly three
   tabs in order: Symbols, Outline, Data.
6. The Symbols tab lists the same tokens as the Math toolbar (same labels, inserted token strings,
   tooltips); clicking an entry triggers the identical inserted-token string as the matching
   toolbar button for at least the `π`, `√`, `d/dx`, and `:=` entries.
7. The Outline and Data tabs show only their one-line placeholder message and contain no other
   widget; this spec's tests assert no outline/dataset state exists anywhere after exercising them.
8. Closing the Side Panel (dock close button or the View entry) and restarting restores it closed;
   reopening it, resizing it, picking a non-default tab, and restarting restores width and active
   tab.
9. The dock enforces a 120-320 px width range; at the window's minimum size the canvas view retains
   at least 400 px of width.

Status bar
10. The permanent status-bar area shows, left to right, `"status-eval-label"`,
    `"status-precision-label"`, `"status-zoom-label"`; the existing transient message area is
    unaffected by this spec.
11. After a `recalculate()` pass leaving zero error-status regions, `"status-eval-label"` reads
    "Ready". After a pass leaving errors, it reads "N error"/"N errors" matching
    `recalculate()`'s own count.
12. A pass measured to take longer than 300 ms shows "Calculating…" in `"status-eval-label"` for
    its duration before switching to Ready/N-errors; a pass under 300 ms never shows
    "Calculating…".
13. `"status-precision-label"` always reads "{engine.significant} sig. figs" and updates the moment
    `Calculate > Result Precision…` changes the value; clicking the label opens that same dialog.
14. Loading a document containing one region with an undefined-name error shows
    `"status-eval-label"` as "1 error" immediately after `load_document`'s initial `recalculate()`
    runs, with no further user action.

Theming
15. `View > Appearance` has three mutually exclusive entries, "Follow System" (default on first
    launch), "Light", "Dark".
16. Selecting "Light" or "Dark" applies that palette to the running `QApplication` immediately
    (verified via `QApplication.palette()` role values before/after); selecting "Follow System"
    re-reads the OS colour scheme at that moment.
17. The chosen Appearance value persists under `"appearance"` in `QSettings` and is applied before
    the window is shown on the next launch.
18. No canvas-painted colour (grid, region border, crosshair, plot colours) changes value as a
    result of any Appearance selection in this spec.

Empty-canvas hint
19. A worksheet with zero regions shows exactly one muted hint line near the crosshair's starting
    position; the hint text is never written into `RegionData`/the saved `.lsheet` file.
20. The hint disappears the moment any region exists (including one still mid-edit) and reappears
    once the sheet is emptied back to zero regions (e.g. Select All then Delete).
21. `export_pdf` output never contains the hint, on a sheet with zero regions, by the same
    suppression mechanism already used for the crosshair.

## Edge cases
- Narrow window widths overflow toolbar buttons into Qt's own standard toolbar overflow chevron;
  no bespoke icon-collapsing logic is added.
- A toolbar or the side panel dragged fully outside the window floats using Qt's own
  floating-toolbar/dock chrome; nothing custom is added for that.
- High-DPI displays and multi-monitor setups rely on Qt's existing automatic scaling; no
  per-platform code is added by this spec.
- Changing Appearance while a modal dialog (Plot dialog, Save/Open dialog, Result Precision
  dialog) is already open does not forcibly repaint that open dialog; it restyles the next time
  any dialog of that kind is shown, to avoid a flash mid-interaction.
- A side-panel width narrower than its 120 px minimum (dragged thin, then the window shrunk
  further) is clamped by `QDockWidget`'s own size constraints, not a bespoke resize handler.
- Printing/exporting while the side panel is open never includes the panel in the PDF; `export_pdf`
  already renders only the `Worksheet` scene, not window chrome, so this needs no new code, only a
  regression check.

## IP check
Pass. Every element here — a standard/application toolbar plus a separate tool-specific toolbar,
a dockable tabbed side panel, permanent status-bar indicators for background state, window-state
persistence via the host toolkit's own save/restore mechanism, an application-level light/dark/
follow-system theme switch, and a muted hint on an empty canvas — is a generic desktop-application
convention documented across countless unrelated products (browsers, office suites, IDEs,
spreadsheets) and in the general, vendor-neutral sources cited above; none of it is traceable to
one specific competitor's distinctive chrome arrangement, icon set, colour palette, or panel
taxonomy. The three-tab grouping (Symbols/Outline/Data) is this spec's own naming, chosen to match
LiveSheet's own three forward-looking panel needs (today's symbol palette, and empty stubs for
backlog 7a/8a), not copied from any one product's panel structure. No vendor name, icon, or literal
colour value is used anywhere in this spec. Nothing here is a novel interaction *technique* on the
canvas itself (per ip-cleanroom rule 6's patent-sensitivity concern, as applied in spec 006): every
behaviour described is either standard toolkit chrome (toolbars, docks, status bar, palettes) or,
for the one canvas-adjacent item (the empty-canvas hint), a passive, non-interactive background
label with no live/placeholder-editing behaviour at all — not the kind of on-canvas interaction
style flagged for engineering-calculation tools elsewhere in this project. No known IP or patent
concern; not legal advice.

## Fits current architecture?
- `livesheet/gui/main_window.py`: add the Standard toolbar (reusing the existing File/Calculate
  `QAction`s), the new View-menu entries (two toolbar toggles, Side Panel toggle, Appearance
  submenu), two new `QSettings` keys (`"window_state"` via `saveState()`/`restoreState()`,
  `"appearance"` as a string), the three new status-bar permanent widgets and their wiring to a new
  `Worksheet` signal (below), and `objectName`s on the existing zoom label.
- `livesheet/gui/worksheet.py`: add a new signal, e.g. `evaluationFinished(int errors, int total,
  float elapsed_ms)`, emitted at the end of `recalculate()` in addition to (not instead of) the
  existing `statusMessage` emit — purely additive, no change to evaluation order or results.
  `drawBackground` (or the nearest existing scene-background paint hook) gains the empty-canvas
  hint, gated on `len(self.regions()) == 0`, excluded from `export_pdf` via the same
  show/hide-around-render pattern already used for `self.crosshair`.
- New `livesheet/gui/sidepanel.py`: `SidePanel(QDockWidget)` holding the three-tab `QTabWidget`.
  Recommend factoring the Math toolbar's existing `(label, token, tip)` tuples out of
  `_build_actions` into one small shared constant (e.g. `MATH_TOKENS`) that both the toolbar and
  the new Symbols tab read, so the two surfaces cannot silently drift apart.
- New `livesheet/gui/theme.py`: palette definitions for light/dark, a `detect_system_scheme()`
  helper, and `apply_theme(app, mode)`, called from `main_window.py` at startup and from the
  Appearance submenu handlers.
- `livesheet/document.py`, `livesheet/engine/*`: unchanged. No `.lsheet` format change, no
  `RegionData` change, no evaluator/formatting change; `FORMAT_VERSION` is untouched.
- Tests: new `tests/test_main_window_chrome.py` covering criteria 1-21 via `objectName` lookups,
  `QSettings` round-trips of `"window_state"`/`"appearance"`, label text after a scripted
  `recalculate()` (including an injected slow pass to exercise criterion 12's 300 ms threshold),
  and dock min/max width. These run headless under `QT_QPA_PLATFORM=offscreen` like the project's
  existing GUI tests, except the real-OS-colour-scheme branch of criterion 16 ("Follow System"),
  which is exercised with a stubbed/injected scheme reader rather than the real OS call. The tester
  should also do a real-window pass on Theo's Mac: drag/dock both toolbars and the side panel and
  confirm they come back in the same place after a restart, toggle Appearance and visually confirm
  menus/toolbars/dialogs restyle, watch the eval-status label during a deliberately large/slow
  sheet, and confirm the first-run hint appears on a brand-new sheet and after deleting everything,
  and is absent from an exported PDF.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. A command-palette/searchable-menu entry point (gui-concepts suggests one for discoverability)
   is left out of this spec to keep scope bounded. [Recommend a separate, later spec if Theo wants
   it; not needed for the chrome to feel complete today.]
2. The evaluation-status label is passive (no click-to-jump-to-the-first-erroring-region action)
   since that would reach into the canvas content model, which this spec treats as out of scope.
   [Recommend a small follow-up spec if Theo wants that jump-to behaviour; flagging rather than
   quietly including it.]
3. Full canvas-painted theming (grid lines, region borders, crosshair colour, plot chart palette)
   is deferred past this spec; recolouring the canvas's own drawing sits closer to the visual-
   identity/content-model side of the app than pure window chrome. [Recommend a dedicated
   "canvas look tokens" follow-up spec once this chrome-level theming has shipped and been used for
   a while.]
4. The side panel's default dock side (left) and its three tab names (Symbols/Outline/Data) are
   this spec's own naming choice, and will likely stick once backlog 7a/8a build their real content
   into the Outline/Data tabs. [Recommend confirming these names read well to Theo now, before
   7a/8a start depending on them — e.g. whether "Data" should instead read "Datasets".]
5. The 300 ms "show a busy indicator" threshold (criterion 12) is this spec's own number, taken
   from the generic "progress indication for anything over ~300ms" idea in gui-concepts rather than
   from any measured LiveSheet recalculation time. [Recommend accepting it as a reasonable default;
   easy to retune later if real sheets recalculate slower than expected.]
