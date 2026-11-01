# Review 011: side-panel category tabs, Greek-letter palette, Subscript quick-insert (tester, black-box)

Spec: `docs/board/specs/011-side-panel-category-tabs.md`. Decisions: `docs/board/decisions.md`,
"Decided 2026-10-30 (Theo + manager, spec 011 side-panel category tabs)". Implementation verified
by the developer (log.md, 2026-10-30): Math toolbar removed from `livesheet/gui/main_window.py`;
`livesheet/gui/sidepanel.py` restructured to 7 tabs (`TAB_ORDER`/`TAB_CATEGORIES`/
`PLACEHOLDER_TABS`); 33 new Greek-letter buttons + 1 new Subscript button in `MATH_TOKENS`; two
new keyboard-shortcut layers (`GREEK_SHORTCUTS_CTRL_SHIFT`, `GREEK_SHORTCUTS_CTRL_ALT`) added to
`main_window.py`. One developer-disclosed deviation from the spec's own written table: layer 1 has
11 `Ctrl+Shift+<letter>` shortcuts, not the spec's originally-written 12, because `Ctrl+Shift+S` is
already claimed by "Save As" via `QKeySequence::StandardKey.SaveAs` (a Qt standard key, not a
literal string, so it didn't show up in the spec's own grep-based "already claimed" list of
A/P/M/C/E). Developer's own tests: `tests/test_greek_shortcuts.py`, `tests/
test_side_panel_categories.py`, plus in-place updates to `tests/test_main_window_blackbox.py`/
`tests/test_main_window_chrome.py`.

## Tests added

`tests/test_spec011_side_panel_greek_blackbox.py`: 113 cases, all pass. Written directly from
spec 011's own acceptance criteria 1-16 and Edge cases, with every expected value (token labels/
tokens/tooltips, the 23 lowercase + 10 uppercase Greek names, both shortcut tables) hand-
transcribed from the spec text itself, not imported from `engine.formatting.GREEK` or `gui.
sidepanel.MATH_TOKENS` — a label/token/shortcut mismatch here means the implementation disagrees
with the spec, not merely with itself. Written and run independently of the developer's own
`tests/test_greek_shortcuts.py`/`tests/test_side_panel_categories.py`; those two files were not
opened while drafting these tests, per the task's instruction (only their test-function *names*
were seen via a `grep -n "def test_"` directory scan while deciding where to put a new file, not
their contents or assertions).

The one thing this task specifically asked to verify independently rather than trust (not the
developer's log.md entry, not their test file): that `Ctrl+Shift+S` really is already claimed by
Save As, that sigma really is excluded from layer 1 as a result, and that the count is really 11,
not 12. `test_layer1_count_and_membership_derived_from_first_principles` re-derives the expected
layer-1 letter set **algorithmically from scratch** — computing which of the 23 Greek names have a
first letter that is both unique among those 23 names and not already bound to some other,
non-Greek action currently live on a real `MainWindow` (found by actually inspecting every
registered `QAction`'s `shortcut()`, not a hardcoded "A/P/M/C/E" list) — and compares that
derivation to what is actually wired up. This independently reproduced the exact 11-letter set
(B, G, D, Z, I, K, L, N, X, R, U) with no sigma, and separately confirmed `QKeySequence(QKeySequence
.StandardKey.SaveAs).toString() == "Ctrl+Shift+S"` on this platform/environment by direct
inspection (not by reading the developer's comment claiming it) — see Acceptance criteria 11/12
below for the detail.

Coverage: all 16 numbered acceptance criteria, each with at least one dedicated test (several with
parametrized per-letter/per-name tests covering every row of both shortcut tables and every Greek
button individually, 23+10 = 33 separate parametrized cases); plus the "Operators"->"Algebra"
rename with an explicit check that the string `"Operators"` is not a tab name anywhere; a
codebase-wide grep for any stray `"math-toolbar"`/`"Operators"`/old `"Symbols"`-tab wording left in
production code (none found — see Coverage gaps for the one place old wording *does* still exist,
which is not production code); five of the spec's own Edge cases (switching tabs mid-edit doesn't
insert or steal focus; an empty document still shows the full token list on every functional tab;
a Greek shortcut with nothing being edited creates a region first; the 120-320px clamp under a
real, shown, laid-out window; the stale pre-spec-011 `side_panel_tab` index self-correcting on the
next click).

## Results

Baseline (`QT_QPA_PLATFORM=offscreen pytest -q`, this file absent, 3 consecutive runs for
stability): **1258 passed, 2 xfailed, 0 failed** (1260 collected). After adding `tests/
test_spec011_side_panel_greek_blackbox.py` (113 new tests): **1371 passed, 2 xfailed, 0 failed**
(1258 + 113, no regressions), stable across 3 consecutive full-suite runs.

Environment note, not a code defect: an initial, very first run this session (before this file was
ever added or removed) reported `1252 passed, 2 xfailed` — 6 fewer than the `1258` figure every
subsequent run (with this review's file absent) reproduced stably. This is not actually a
discrepancy once cross-checked against `docs/board/log.md`'s own history: the `1252` figure matches
the suite's state *before* the spec-010 tester review's own session, which added 6 new tests to
`tests/test_ode_blackbox.py` (log.md, 2026-10-30, "... extended it rather than rewriting it: +6
cases this session ... QT_QPA_PLATFORM=offscreen pytest -q: 1258 passed, 2 xfailed, 0 failed,
stable across 3 consecutive runs (1252 going into this session, 6 new)"). Those 6 tests are already
present on disk from that already-completed, already-logged session, so `1258` is the correct,
current, pre-this-review baseline; the one `1252` result this session was most likely a stale
first-run artifact (e.g. a `.pyc`/collection-cache effect from `.venv` not having been touched yet
this session) rather than any real file being added or removed between runs — not investigated
further since it was not reproducible and does not change which number is the real baseline.
`1258`/`1260` is used as "baseline" throughout this review.

## Acceptance criteria

1. PASS. No `math_toolbar` attribute, no `QToolBar` named `"math-toolbar"` anywhere in the window,
   no `"Math Toolbar"` text in any menu. `"standard-toolbar"` present and unaffected, with its own
   `"Standard Toolbar"` `View` entry still present.
2. PASS. `"side-panel-tabs"` has exactly 7 tabs, in the exact order Elements, Algebra, Calculus,
   Statistics, Optimization, Outline, Data.
3. PASS. Elements has exactly 40 buttons: the 7 carried-over Statements/Constants entries present
   and clickable; `π` still inserts `"pi"`; all 23 lowercase and all 10 uppercase Greek buttons
   present under their correct glyph label and each one clicked inserts its correct English name
   (33 separate parametrized checks, e.g. `α`->`"alpha"`, `Ω`->`"Omega"`); exactly one `λ`-glyph
   button exists (the `"lamda"`/`"lambda"` alias collapsed correctly) and exactly one `π`-glyph
   button exists (no duplicate for the already-existing Constants entry); the Statements/
   Constants/Greek-letters sub-headers are present.
4. PASS. Algebra has exactly 4 buttons (`√`, `ⁿ√`, `x²`, `xₙ`), tab renamed from `"Operators"` to
   `"Algebra"` (`"Operators"` confirmed absent from every tab name); `√` still inserts `"sqrt("`;
   the new `xₙ` button has tooltip `"Subscript"` and inserts a bare `"_"`; confirmed separately
   that no Algebra button ever inserts a literal `[` or `]` (the spec's explicit "does not touch
   `[`/`]`" claim).
5. PASS. Calculus unchanged, exactly 2 buttons (`d/dx`, `∫`); `d/dx` still inserts `"diff("`.
6. PASS. Statistics and Optimization each have exactly one non-interactive, centred (`AlignCenter`
   bit set), word-wrapped `QLabel` and zero `QPushButton`/clickable widgets; a real `QTest.
   mouseClick` dispatched at the placeholder label's centre never calls `insert_token` (mocked and
   asserted) and never changes the region list.
7. PASS. Outline is tab index 5, Data is tab index 6 (6th/7th as required); both still placeholder-
   only (zero `QPushButton`, exactly one `QLabel` each).
8. PASS. Elements+Algebra+Calculus total exactly 46 buttons, all 46 labels distinct (nothing
   dropped, nothing duplicated).
9. PASS. Dock width (resized to 200px while shown/laid-out) and a non-default active tab index (6,
   "Data" — specifically chosen because that index was out of range under the old 3-tab layout)
   both survive a close/reopen cycle through real `QSettings`; the dock's closed state also
   survives a close/reopen cycle; the 120-320px clamp holds in both directions on a real, shown,
   laid-out window (not just the trivially-true unlaid-out default).
10. PASS. A synthetic "pre-spec-011" `saveState()` blob genuinely built from a throwaway
    `QMainWindow` with a toolbar actually named `"math-toolbar"` (not a hand-constructed byte
    string) loads into a real `MainWindow()` without raising, and the resulting window has no
    `"math-toolbar"` `QToolBar` and its real `"standard-toolbar"` intact.
11. PASS, **and independently re-derived rather than trusted** (see Tests added above): all 11
    actual layer-1 `Ctrl+Shift+<letter>` shortcuts (B/G/D/Z/I/K/L/N/X/R/U) each insert their correct
    Greek name, individually parametrized; the from-scratch derivation of "which letters should get
    a layer-1 shortcut" lands on exactly this same 11-member set with no sigma, confirming the
    spec's originally-written 12-row table (which still includes an `S`/sigma row) is the thing
    that needed correcting, not the implementation.
12. PASS. `Ctrl+Shift+A` resolves to exactly one action, text `"Select &All Regions"` (not
    `"alpha"`), and triggering it selects all regions as before; `Ctrl+Shift+P/M/C/E` each resolve
    to exactly one action with their original Plot/Matrix/Component/Export-PDF text; **the specific
    regression this task asked to independently confirm**: `Ctrl+Shift+S` resolves to exactly one
    action whose text contains both `"Save"` and `"As"` (never `"sigma"`), and no action named
    `"sigma"` anywhere in the window has that shortcut; no second, new action was added on any of
    the 5 reserved letters.
13. PASS. Hand-typing `"alpha"` into a fresh math region with no button/shortcut, through
    `start_editing()`/`setPlainText()`/`finish_editing()`, still displays `α` in the rendered text
    exactly as before; hand-typing `"x_1"` still renders its subscript (the literal `"_1"`
    substring is gone from the displayed text, confirming the subscript rendering fired, not merely
    that no crash occurred).
14. PASS. All 23 lowercase Greek letters are reachable via `Ctrl+Alt+<letter>`, each individually
    parametrized and confirmed to insert its correct name (including the four resolved-collision
    letters: `Ctrl+Alt+H`->`"eta"`, `Ctrl+Alt+W`->`"omega"`, `Ctrl+Alt+Y`->`"tau"`, `Ctrl+Alt+Q`-
    >`"psi"`); `Ctrl+Alt+F`/`J`/`V` resolve to zero actions (confirmed unbound, not merely untested).
15. PASS. No two distinct actions anywhere on the window share one `QKeySequence` (checked across
    *every* registered `QAction`, not just the Greek ones — zero ambiguous shortcuts found); for
    the 11 letters present in both layers, both resolve to the identical Greek name; every
    `Ctrl+Alt+<letter>` action found on the window is one of the 23 Greek-letter actions (nothing
    else uses that modifier combination).
16. PASS. None of the 10 uppercase Greek-named actions (by text, e.g. `"Gamma"`, `"Omega"`) carry
    any shortcut at all; all 10 remain click-only via their Elements-tab button.

## Edge cases

All PASS: switching tabs mid-edit neither calls `insert_token` nor clears the editing region's
focus/content; an empty document (zero regions) still shows the full 40/4/2-entry token lists on
all three functional tabs; a Greek-letter shortcut pressed with nothing being edited creates a new
math region first, same as every other `insert_token`-backed shortcut; a stale `"side_panel_tab"`
value of `2` (meant `"Data"` under the old 3-tab layout) resolves to `"Calculus"` under the new
7-tab order without crashing, and the stored value self-corrects to whatever tab is clicked next —
exactly the "cosmetic, self-correcting, nothing lost" behaviour the spec's own Edge-cases section
describes.

## Defects

None found. All 16 acceptance criteria and every edge case this review exercised hold exactly as
specified.

## IP red flags

None found. Grepped `livesheet/gui/sidepanel.py`, `livesheet/gui/main_window.py`, and `livesheet/
engine/formatting.py` (read-only source for the Greek glyph map) for `mathcad`/`mathematica`/
`maple`/`matlab`/`wolfram`/`mupad`/`maxima` (case-insensitive) and found none. No vendor tab/
section names (`"Basic Commands"`, `"Expressions and Equations"`, Maple's palette names, MATLAB's
gallery category names) appear anywhere; `"Elements"`/`"Algebra"`/`"Statistics"`/`"Optimization"`
are the project's own plain-English words, matching the spec's own IP check. No icon/asset files
are used for the new Greek/Subscript buttons (plain `QPushButton` text glyphs, same mechanism the
pre-existing Symbols-tab buttons already used). No stray old names (`"math-toolbar"`,
`"Operators"` as a tab name, the old 3-tab `"Symbols"` grouping) were found anywhere in production
code (`livesheet/`) — the one place old wording *does* still exist is a documentation file, not
code; see Coverage gaps below.

## Coverage gaps

- **No real-window/computer-use pass this session.** This session's available tool set has no
  `computer_*` tool (confirmed by checking the tool list provided at session start — Read, Edit,
  Write, Bash, SendMessage, SubagentHandback only), so Theo's instruction to open/close the real
  app, click through all 7 tabs, try both Greek shortcut layers by actually pressing the keys, and
  confirm Save As still works via a real keystroke on Theo's Mac could not be carried out this
  session. Everything in this review was verified headlessly (`QT_QPA_PLATFORM=offscreen`) through
  Qt's own programmatic APIs (`QAction.trigger()`, `QPushButton.click()`, a real `QTest.
  mouseClick`, real `QSettings`/`saveState()`/`restoreState()` round trips) — this exercises the
  same production code a real mouse/keyboard interaction would reach, including every registered
  `QAction`'s actual `QKeySequence`, but a `QAction.trigger()` call is not the same as a real OS-
  level key-press event reaching the window through the platform's input stack, and nothing here
  was watched on an actual screen. A real pass should still cover: opening the side panel and
  clicking through all 7 tabs by eye; clicking a Greek-letter button and the new Subscript button
  into a real math region and watching the display render; pressing a sample of both shortcut
  layers directly with the keyboard (including at least one of the four resolved-collision letters,
  e.g. `Ctrl+Alt+H` for eta); pressing `Cmd+Shift+S`/`Ctrl+Shift+S` and confirming the real Save As
  file dialog opens (not a sigma insertion); confirming the Math toolbar is genuinely gone from the
  top of the window to the eye, not just absent from `findChild`; opening an actual on-disk
  LiveSheet preferences file saved by a pre-spec-011 build (if one still exists on Theo's machine)
  and confirming it opens without error.
- **The end-user manual (`docs/manual/main-window.md`) still describes the pre-spec-011 state**
  (Math toolbar, "Math Toolbar" `View` entry, a 3-tab side panel named Symbols/Outline/Data, with
  Symbols' sub-headers listed as "Constants, Operators, Calculus, Statements"). This is expected,
  not a defect: per `CLAUDE.md`'s own workflow, the documenter updates the manual only once the
  manager has accepted both the implementation and this tester review — which has not happened
  yet. Flagging here only so this is not mistaken for a leftover "stray old name" in the sense this
  task's acceptance-criteria wording cared about (that check was scoped to production code, where
  nothing stray was found); the manual itself still needs its own pass once this review and the
  implementation are both accepted.
- `QAction.trigger()` was used throughout in place of `QTest.keyClick` for exercising keyboard
  shortcuts. An early attempt to drive a real `QTest.keyClick(win, ...)` against a shown,
  activated `MainWindow` in a bare (non-pytest) script hung indefinitely in this sandbox and had to
  be killed; the same construction works fine inside the project's actual pytest suite elsewhere
  (e.g. existing tests already use `.click()`/`QTest.mouseClick` successfully), so this looks like
  an artifact of driving Qt event delivery outside pytest's own harness in this environment, not a
  defect in the shortcut wiring itself — `QAction.shortcut()` equality plus `.trigger()` still
  exercises the real, identical `QAction` object a genuine key-press would resolve to and fire, just
  not the OS-level key-event delivery path itself. Noted here as a second, narrower instance of the
  same "cannot always drive a real blocking/native Qt interaction headlessly" territory this
  project's own testing skill already documents for `QMenu.exec()`.
- The exact visual appearance of the 7-tab bar at the narrowest 120px width (label elision/overflow
  behaviour) and the 40-entry Elements tab's scroll behaviour were not visually inspected (only
  their structural widget counts were), consistent with the spec's own position that this relies on
  Qt's default behaviour and is not covered by a numbered acceptance criterion.

## Recommendation

Spec 011 is functionally sound: all 16 acceptance criteria and every edge case this review
exercised hold exactly as specified under independent black-box testing (`tests/
test_spec011_side_panel_greek_blackbox.py`, 113 cases), the full suite is stable at 1371 passed /
2 xfailed / 0 failed (1258 baseline + 113 new, three consecutive runs), and the one thing this task
specifically asked to verify independently — that `Ctrl+Shift+S` is Save As, sigma is excluded from
layer 1 as a result, and the real layer-1 count is 11 rather than the spec's own originally-written
12 — was re-derived from scratch and confirmed correct, not merely trusted from the developer's own
log entry or test file. No defects and no IP red flags found. The only two real gaps are the
missing real-window/computer-use pass (no `computer_*` tool available this session, flagged
explicitly per standing project practice) and the end-user manual's expected, process-correct
staleness (documenter's job, once this review and the implementation are both accepted) — neither
blocks accepting spec 011's implementation on the strength of this review.
