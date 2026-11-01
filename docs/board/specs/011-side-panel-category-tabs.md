# 011 Side-panel category tabs, Greek-letter palette, and subscript quick-insert
(remove Math toolbar duplication)

Source inspiration (concept only, nothing copied):
- https://blog.wolfram.com/2009/01/21/quick-starting-mathematica-with-palettes/ (Wolfram's own
  blog, wolfram.com domain) and https://reference.wolfram.com/language/guide/PalettesMenu.html
  (Wolfram Language reference) — general, public description of Mathematica's "Basic Math
  Assistant" palette as one of several separately named, separately opened palette windows
  (reached from a flat Palettes menu, not a single tab bar inside the main window), whose contents
  are grouped by mathematical topic (the blog post describes groupings including basic
  constants/commands, algebra, calculus, and matrix commands). Public, checked 2026-10-30. Concept
  used: *grouping insertable math building blocks by topic rather than one flat list*. Not used:
  Mathematica's own tab/section names, its separate floating-palette-window mechanism, its icon
  set, or its specific template-button layout.
- https://www.maplesoft.com/support/training/PDF/MapleQuickStart.pdf (Maplesoft's own domain) —
  general, public description of Maple's palettes as several separately titled, simultaneously
  visible, independently collapsible panels stacked in one sidebar (e.g. categories for general
  expression templates, symbols, matrices, units, and several kinds of operators/relations —
  shown all at once, each expandable/collapsible, rather than one panel at a time). Public,
  checked 2026-10-30. Concept used: *a sidebar is a reasonable, long-established home for a
  library of insertable math building blocks, organised by topic*. Not used: Maple's simultaneous
  multi-panel ("many panels visible at once, each collapsible") layout, its specific category
  names, or its units-palette structure — this spec deliberately keeps LiveSheet's existing
  exclusive-tab-selection mechanism (exactly one tab's content visible at a time) instead.
- https://blogs.mathworks.com/loren/2012/10/01/the-matlab-r2012b-desktop-part-3-matlab-apps/
  (MathWorks' own blog, mathworks.com domain) — general, public description of MATLAB's Apps
  Gallery grouping installed apps into named topical categories, one of which bundles
  statistics-related and optimization-related apps together under one heading. Public, checked
  2026-10-30. Concept used only: *statistics and optimization are commonly treated as adjacent,
  closely related topics within a math-tool's own category taxonomy* — this is reflected only in
  this spec's tab **ordering** (Statistics next to Optimization), not in any literal MATLAB
  category name, icon, gallery-grid layout, or toolstrip/ribbon chrome (MATLAB's gallery opens
  whole interactive apps/windows, a different interaction from this spec's one-click
  insert-a-token mechanism).
- `.claude/skills/gui-concepts/SKILL.md` — the team's own idea checklist (dockable side panels,
  consistency: "one way to do a given action, reachable the same way everywhere").
- `docs/board/specs/007-main-window.md` — this project's own prior spec, which already shipped the
  single dockable, tabbed side panel (`SidePanel`/`side-panel-tabs`) and the shared
  `MATH_TOKENS` list this spec restructures. This spec is a follow-up to 007, not a new chrome
  concept.
- No Mathcad, Mathematica, Maple, MATLAB or other vendor software, installed application, help
  file, example worksheet, screenshot, or non-public document was read for this spec; everything
  above is from currently, publicly published vendor documentation/blog pages on the vendor's own
  domain, read only by this specialist per `.claude/skills/ip-cleanroom/SKILL.md`.
- **Addendum 1 (folded in after the manager relayed two follow-up requests from Theo mid-task):**
  this spec also now covers (a) quick-insert buttons for the Greek alphabet in the Elements tab,
  and (b) a quick-insert Subscript button in the Algebra tab, plus (c) a bounded set of new
  `Ctrl+Shift+<letter>` keyboard shortcuts for part of the Greek alphabet. No *additional* vendor
  research applies to either addition: the Greek alphabet and subscript notation are universal
  mathematical notation, explicitly on `docs/IP-POLICY.md`'s own "Allowed" list ("standard
  math/engineering notation... and common function names"), and both reuse mechanisms LiveSheet
  already ships today with zero engine change — `engine/formatting.py`'s `GREEK` dict (already
  maps English names like `"alpha"`/`"lambda"`/`"Omega"` to glyphs for *display*) and
  `gui/pretty.py`'s `_SUB_RE` (already renders `x_1` as x₁ for *display*) are read-only here, not
  modified; this spec only adds new ways to *type* text that already displayed correctly. The
  keyboard-shortcut mechanism itself (a `QAction` with a `Ctrl+Shift+<letter>` shortcut calling
  `insert_token`) is this project's own already-shipped pattern (see the Insert menu's existing
  quick-insert entries and the now-removed Math toolbar), not read from any vendor.
- **Addendum 2 (Theo's decision, 2026-10-30, resolving what was originally open question 6):**
  Theo asked for full lowercase-Greek-alphabet shortcut coverage, via the fallback this spec itself
  flagged — a second, currently-unused modifier combination, `Ctrl+Alt+<letter>`, added *alongside*
  (not instead of) the 12 `Ctrl+Shift+<letter>` shortcuts from Addendum 1. See the "Greek letters"
  behaviour section and acceptance criteria 14-16 below for the full 23-letter table and the
  uppercase-letters-stay-click-only call this addendum also makes explicit.
- Chemistry notation (also raised by Theo in the same conversation) is **explicitly out of scope**
  for this spec; the manager is scoping that separately with Theo before dispatching any spec work
  on it.

Scope note: this spec is about the side panel's **tab mechanism**, migrating today's Math
toolbar/Symbols-tab content into it, adding empty placeholder tabs for categories that do not exist
yet, and — per the addenda above — adding a Greek-letter palette (with two layers of keyboard
shortcuts) and a subscript quick-insert next to the content this spec was already migrating. It
does **not** design the actual Statistics (backlog 29) or Optimization (backlog 30) features, the
Outline/Data tab content (backlog 7a/8a, already out of scope per spec 007), chemistry notation
(separately scoped, see above), or anything about the component-wiring canvas (backlog M6) — those
remain separate, future specs that simply get an obvious tab to slot their own content into later,
the same placeholder pattern Outline/Data already use today.

Size: one phase, about 2 days (GUI-only restructuring of already-shipped chrome plus a bounded
new-token/new-shortcut addition; no new widget types, no engine/document change).

---

## User story
As a LiveSheet user, I want exactly one place to find an insertable math building block — grouped
by the kind of thing it is (basic elements, algebra, calculus, and, as LiveSheet grows, statistics
and optimization) — instead of the same buttons appearing twice: once in a crowded single-row
toolbar across the top of the window, and again, regrouped, in the side panel's Symbols tab. I want
new categories like Statistics and Optimization to already have an obvious home waiting for them
once those features exist, the same way Outline and Data already do today. I also want to type
Greek letters and subscripted variable names (both of which LiveSheet's display already renders
correctly once I type the right English word or an underscore) by clicking a button or pressing a
memorable keyboard shortcut, instead of having to remember and spell out the English word every
time — and I want that shortcut coverage to reach the *whole* Greek alphabet, not just part of it.

## Behaviour (own words)

### What is removed
- The **Math** toolbar (`main_window.py`, `objectName "math-toolbar"`) is removed entirely: the
  `QToolBar` itself, its "Text" button, its `MATH_TOKENS` button loop, the `addToolBarBreak()` that
  stacked it under Standard, and its "Math Toolbar" checkable entry in the `View` menu.
- The Standard toolbar (`objectName "standard-toolbar"`) is **unchanged** — it keeps New, Open,
  Save, Export PDF, Recalculate exactly as spec 007 left it, and keeps its own "Standard Toolbar"
  `View`-menu toggle.
- Nothing in the `Insert` menu changes. Its four existing quick-insert entries (":=  Definition",
  "≡  Global definition", "=  Evaluate", "→  Symbolic") already call `insert_token` directly and are
  out of scope for this spec — they are a menu, not a toolbar, and Theo's instruction was specific
  to the Math toolbar.

### The new side-panel tab structure
The side panel (`SidePanel`/`side-panel-tabs`, unchanged dock: left-docked by default, 120-320 px
wide, same `View > Side Panel` toggle) now has **seven** tabs, in this fixed order:

1. **Elements** — today's "Statements" tokens (`:=`, `≡`, `=`, `→`) together with today's
   "Constants" tokens (`π`, `e`, `i`), **plus** the new Greek-letter palette described below: the
   small set of symbols/operators reached for on almost every line regardless of what kind of math
   is being done, independent of any particular math domain. Because this tab now bundles three
   originally distinct groups (Statements, Constants, Greek letters) rather than mapping 1:1 from
   one of today's old categories, it keeps the same small grey sub-header labels the old Symbols
   tab already used, one per group, so a long tab stays scannable — the only functional tab that
   keeps sub-headers, for exactly this reason.
2. **Algebra** — today's "Operators" tokens (`√`, `ⁿ√`, `x²`), **plus** the new Subscript token
   described below. This is also the natural future home for backlog 10 (assumptions on symbols)
   and backlog 11 (user rewrite rules / pattern replace) once those ship — both are
   standard-curriculum "algebra" topics, not a new category of their own. No sub-headers (these
   four tokens are all "operator-shaped" building blocks, not three distinct groups).
3. **Calculus** — today's "Calculus" tokens (`d/dx`, `∫`), unchanged. Natural future home for more
   calculus content (e.g. limit/series snippets, and backlog 14's ODE keywords once spec 010 ships
   — solving differential equations is conventionally grouped under calculus, not a category of its
   own).
4. **Statistics** — empty placeholder tab, reserved for backlog 29 (descriptive statistics,
   probability distributions, hypothesis tests, regression).
5. **Optimization** — empty placeholder tab, reserved for backlog 30 (general nonlinear/constrained
   optimization beyond today's solve blocks).
6. **Outline** — unchanged placeholder tab (backlog 7a), same message as today.
7. **Data** — unchanged placeholder tab (backlog 8a), same message as today.

Every token's **label, inserted token string, and tooltip** that already existed today is carried
over byte-for-byte from today's `MATH_TOKENS` list — only which tab a token appears under, and the
fact that a tab's content is now organised as whole categories rather than several grouped under
one "Symbols" tab, changes. The new Greek-letter and Subscript tokens described below are the only
genuinely new entries this spec adds. Clicking any token button — old or new — still calls the
exact same `insert_token(token)` callback it does today (same mechanism as the old Math toolbar and
today's Symbols tab): a region is created/focused and the token string is inserted at the cursor,
unchanged behaviour.

The three functional tabs (Elements/Algebra/Calculus) each show their tokens as the same kind of
scrollable, vertically stacked list of bordered buttons the Symbols tab already uses today. The two
new placeholder tabs (Statistics/Optimization) use the exact same placeholder presentation
Outline/Data already use: a centred, muted, word-wrapped one-line message, own wording, e.g.
"Statistical tools (descriptive statistics, distributions, hypothesis tests, regression) will
appear here once available." / "Optimization tools (nonlinear and constrained optimization) will
appear here once available." No interactive content, no `insert_token` wiring, on either new
placeholder tab.

### Greek letters
The Elements tab gains a "Greek letters" group, one button per name the engine's own
`engine/formatting.py` `GREEK` dict already maps to a glyph for display — reusing that dict's keys
exhaustively (every key gets a button; nothing is cherry-picked), except the duplicate alias
`"lamda"` (the dict has both `"lamda"` and `"lambda"` mapped to the same glyph λ; only one button,
spelled `"lambda"`, is added, since a second button for the same glyph/same inserted text would be
a pointless duplicate) and except lowercase `"pi"` (already a Constants button inserting the exact
same text today, unaffected by this spec). That leaves:
- **23 lowercase buttons**, in Greek-alphabet order: α β γ δ ε ζ η θ ι κ λ μ ν ξ ο ρ σ τ υ φ χ ψ ω
  (alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa, lambda, mu, nu, xi, omicron,
  rho, sigma, tau, upsilon, phi, chi, psi, omega). Each button's label is the glyph; clicking it
  inserts the plain English name text (e.g. the `α` button inserts `"alpha"`) — exactly the text a
  user could already type by hand today to get the same glyph in the non-editing display, so there
  is nothing for the engine to learn that it does not already know.
- **10 uppercase buttons**, for the dict's existing uppercase entries: Γ Δ Θ Λ Ξ Π Σ Φ Ψ Ω (Gamma,
  Delta, Theta, Lambda, Xi, Pi, Sigma, Phi, Psi, Omega). Same mechanism: the `Π` button inserts
  `"Pi"`, distinct from the already-existing lowercase `π`/`"pi"` Constants button (uppercase Pi
  the letter/product-notation symbol is a different thing from the lowercase constant π, exactly as
  the engine already treats them as two different case-sensitive names).

**Keyboard shortcuts, layer 1 — `Ctrl+Shift+<letter>` (12 of 23 lowercase letters).** Theo first
asked for a `Ctrl+Shift+<letter>` shortcut to insert a Greek letter directly. Two real constraints
make full, one-shortcut-per-Greek-letter coverage impossible under this one modifier alone, not
just inconvenient, so this layer resolves them with one simple, memorable rule rather than ad hoc
exceptions:
- There are only 26 Latin letters, and 5 are already bound to other `Ctrl+Shift+` commands today
  (`A` Select All Regions, `P` Insert Plot, `M` Insert Matrix, `C` Insert Component, `E` Export
  PDF), leaving 21 free letters.
- There are 23 distinct lowercase Greek letters needing a key. **21 free letters cannot cover 23
  Greek letters**, full stop — this is true regardless of how cleverly the remaining letters are
  assigned, before even considering that English transliterations collide with each other on top
  of that (epsilon/eta both start with `e`, theta/tau both `t`, phi/psi both `p`, omicron/omega both
  `o` — and `e`/`p` are also two of the 5 letters already claimed by the app).

Rather than inventing non-mnemonic arbitrary key assignments to squeeze in a few more under this one
modifier, this layer gives a `Ctrl+Shift+<letter>` shortcut only to the Greek letters whose **first
letter is both unique among the 23 Greek names and not already used by an existing app shortcut** —
a simple, fully memorable rule with no exceptions and no cherry-picking:

| Shortcut | Inserts | Greek letter |
|---|---|---|
| Ctrl+Shift+B | `"beta"` | β |
| Ctrl+Shift+G | `"gamma"` | γ |
| Ctrl+Shift+D | `"delta"` | δ |
| Ctrl+Shift+Z | `"zeta"` | ζ |
| Ctrl+Shift+I | `"iota"` | ι |
| Ctrl+Shift+K | `"kappa"` | κ |
| Ctrl+Shift+L | `"lambda"` | λ |
| Ctrl+Shift+N | `"nu"` | ν |
| Ctrl+Shift+X | `"xi"` | ξ |
| Ctrl+Shift+R | `"rho"` | ρ |
| Ctrl+Shift+S | `"sigma"` | σ |
| Ctrl+Shift+U | `"upsilon"` | υ |

These 12 keys are each used by exactly one Greek letter and by nothing else in the app.

**Keyboard shortcuts, layer 2 — `Ctrl+Alt+<letter>` (all 23 lowercase letters, Theo's decision,
Addendum 2).** `Ctrl+Alt+` was confirmed unused anywhere in `livesheet/gui/` before this spec (no
existing `Ctrl+Alt+...` shortcut of any kind), so it is an entirely free modifier combination with
26 full slots for 23 letters — enough room to resolve every within-Greek collision with a real
letter instead of leaving anything unbound. This layer exists **alongside, not instead of**, layer
1 above: all 12 letters that appear in both tables insert the same Greek letter either way, so a
user who already learned a `Ctrl+Shift+` shortcut keeps it working unchanged.

Rule: use the first letter wherever it is unique among the 23 names (15 letters: alpha, beta, chi,
delta, epsilon, gamma, iota, kappa, lambda, mu, nu, rho, sigma, upsilon, xi, zeta — note this list
differs slightly from layer 1's 12 because layer 1 also had to dodge the app's 5 pre-existing
`Ctrl+Shift+` letters, which do not apply to this entirely fresh modifier). For the four pairs that
share a first letter, keep one member on that natural letter (epsilon, theta, phi, omicron — chosen
as the more commonly used plain variable name of each pair in general engineering use) and give the
other member a distinct, still-free letter: a visual look-alike mnemonic where a genuine one exists
(lowercase eta's uppercase form Η resembles Latin `H`; lowercase omega `ω` is commonly read as a
stacked/rounded `w` shape), and, for the two names with no such visual trick available (tau, psi),
simply the next still-free letter in alphabetical order — stated plainly as an arbitrary pick rather
than inventing a mnemonic that would be no easier to remember than no mnemonic at all:

| Shortcut | Inserts | Greek letter | Note |
|---|---|---|---|
| Ctrl+Alt+A | `"alpha"` | α | first letter |
| Ctrl+Alt+B | `"beta"` | β | first letter |
| Ctrl+Alt+C | `"chi"` | χ | first letter |
| Ctrl+Alt+D | `"delta"` | δ | first letter |
| Ctrl+Alt+E | `"epsilon"` | ε | first letter (kept over eta) |
| Ctrl+Alt+G | `"gamma"` | γ | first letter |
| Ctrl+Alt+H | `"eta"` | η | uppercase Η looks like Latin H |
| Ctrl+Alt+I | `"iota"` | ι | first letter |
| Ctrl+Alt+K | `"kappa"` | κ | first letter |
| Ctrl+Alt+L | `"lambda"` | λ | first letter |
| Ctrl+Alt+M | `"mu"` | μ | first letter |
| Ctrl+Alt+N | `"nu"` | ν | first letter |
| Ctrl+Alt+O | `"omicron"` | ο | first letter (kept over omega) |
| Ctrl+Alt+P | `"phi"` | φ | first letter (kept over psi) |
| Ctrl+Alt+Q | `"psi"` | ψ | arbitrary (no visual/phonetic trick available) |
| Ctrl+Alt+R | `"rho"` | ρ | first letter |
| Ctrl+Alt+S | `"sigma"` | σ | first letter |
| Ctrl+Alt+T | `"theta"` | θ | first letter (kept over tau) |
| Ctrl+Alt+U | `"upsilon"` | υ | first letter |
| Ctrl+Alt+W | `"omega"` | ω | lowercase ω resembles a stacked "w" |
| Ctrl+Alt+X | `"xi"` | ξ | first letter |
| Ctrl+Alt+Y | `"tau"` | τ | arbitrary (no visual/phonetic trick available) |
| Ctrl+Alt+Z | `"zeta"` | ζ | first letter |

All 23 lowercase Greek letters now have exactly one `Ctrl+Alt+<letter>` shortcut each; `F`, `J`,
`V` are the 3 letters left over (26 − 23), not bound to anything by this spec.

**Uppercase Greek letters stay click-only** — no `Ctrl+Alt+Shift+<letter>` or any other third
shortcut layer is added for them in this spec. Reasoning: Theo's follow-up request (Addendum 2) was
specifically about reaching full coverage of the lowercase alphabet (the 23 letters used constantly
as plain variable names); the 10 uppercase letters are used far more narrowly, each as one specific,
fixed symbol (Δ difference, Σ summation, Ω a product/other specific meaning depending on context),
so a whole extra shortcut layer for 10 rarely-needed symbols is a disproportionate amount of new
shortcut surface for the benefit — left as a possible small follow-up only if real usage shows
otherwise, not included here.

### Subscript
The Algebra tab gains one new button, label `xₙ`, tooltip "Subscript", inserting the single
character `_` — the same kind of literal-text insertion the existing `x²` button (inserts `"^2"`)
already does, reusing the exact same `insert_token` mechanism. This does **not** touch `[`/`]` at
all — `[` remains exactly spec 002a's reviewed vector/matrix indexing operator, unrelated to this
button. Typing a name right after the inserted `_` (e.g. `x` then click, then type `1` to get
`x_1`) already displays as a subscript today via `gui/pretty.py`'s existing `_SUB_RE` rendering;
this button only saves typing the underscore character itself.

### Persistence
Dock open/closed state and width persist exactly as spec 007 already specified (no change). Active
tab persistence (`QSettings` key `"side_panel_tab"`) continues to store a plain tab index, now in
the range 0-6 instead of 0-2 — see Edge cases for what happens to a value saved before this spec.

## Syntax proposal (own keywords)
N/A — this is side-panel chrome and keyboard shortcuts only. No change to
`livesheet/engine/syntax.py`, the `.lsheet` statement grammar, or any evaluator keyword. No
`.lsheet` document-format change. `engine/formatting.py`'s `GREEK` dict and `gui/pretty.py`'s
`_SUB_RE` are read, not modified.

## Acceptance criteria
1. `MainWindow` has no `math_toolbar` attribute and no `QToolBar` named `"math-toolbar"` exists
   anywhere in the window; `View` has no "Math Toolbar" entry. `"standard-toolbar"` is present,
   unchanged, with its own "Standard Toolbar" `View` entry still present and still independent.
2. `"side-panel-tabs"` has exactly 7 tabs, in order: Elements, Algebra, Calculus, Statistics,
   Optimization, Outline, Data.
3. The Elements tab contains exactly 40 clickable entries: the 7 carried over from today's
   "Statements"/"Constants" entries (labels/tokens/tooltips identical to today's `MATH_TOKENS`:
   `:=`/`":= "`, `≡`/`"≡ "`, `=`/`" ="`, `→`/`" → "`, `π`/`"pi"`, `e`/`"e"`, `i`/`"I"`) plus 33 new
   Greek-letter entries (23 lowercase + 10 uppercase, see tables above); clicking `π` inserts `"pi"`
   exactly as the old Math-toolbar/Symbols-tab `π` button already did; clicking the new `α` button
   inserts `"alpha"`; clicking the new `Ω` button inserts `"Omega"`.
4. The Algebra tab contains exactly 4 clickable entries: the 3 carried over from today's
   "Operators" entries (`√`/`"sqrt("`, `ⁿ√`/`"root("`, `x²`/`"^2"`) plus the new Subscript entry
   (`xₙ`/`"_"`); clicking `√` inserts `"sqrt("`; clicking the new `xₙ` button inserts `"_"`.
5. The Calculus tab contains exactly 2 clickable entries, identical to today's "Calculus" entries
   (`d/dx`/`"diff("`, `∫`/`"integrate("`); clicking `d/dx` inserts `"diff("`.
6. The Statistics and Optimization tabs each contain exactly one non-interactive, centred, muted
   placeholder label and no `QPushButton` or other clickable widget; clicking anywhere inside either
   tab never calls `insert_token` and never creates or modifies a region.
7. The Outline and Data tabs are unchanged from spec 007: same placeholder message text, same
   absence of interactive content, now appearing 6th and 7th instead of 2nd and 3rd.
8. The total number of clickable token buttons across Elements+Algebra+Calculus is 46 (40 + 4 + 2):
   today's 12 original `MATH_TOKENS` entries, carried over unchanged, plus the 33 new Greek entries
   and the 1 new Subscript entry this spec adds — nothing dropped, nothing duplicated.
9. Opening/closing the side panel, resizing it within 120-320 px, and selecting a non-default tab,
   then restarting, restores the dock's open state, width, and active tab index exactly as spec
   007's criterion 8 already specifies — now exercised across indices 0-6 instead of 0-2.
10. A previously saved `"window_state"` blob that still names `"math-toolbar"` (saved before this
    spec, e.g. from a toolbar drag/visibility toggle) loads without error or crash —
    `restoreState()` silently skips a named toolbar/dock that no longer exists, which is standard,
    already-documented `QMainWindow` behaviour, not new code this spec must add.
11. `Ctrl+Shift+B` pressed while editing/creating a math region inserts `"beta"` at the cursor,
    identically to clicking the Elements tab's `β` button. The same holds for `Ctrl+Shift+G/D/Z/
    I/K/L/N/X/R/S/U` and their respective Greek letters (gamma/delta/zeta/iota/kappa/lambda/nu/xi/
    rho/sigma/upsilon).
12. `Ctrl+Shift+A` still triggers "Select All Regions" exactly as before this spec (not alpha);
    `Ctrl+Shift+P`/`M`/`C`/`E` still trigger Insert Plot/Matrix/Component/Export PDF exactly as
    before. None of the 5 pre-existing `Ctrl+Shift+` shortcuts change meaning, and no new
    `Ctrl+Shift+` shortcut is bound to `A`, `P`, `M`, `C`, or `E`.
13. Typing the word `alpha` by hand into a math region (no button, no shortcut) still displays as α
    in the non-editing view exactly as it does today — this spec adds no engine code and changes no
    existing display behaviour for any Greek word or subscript already typed by hand.
14. `Ctrl+Alt+<letter>` pressed while editing/creating a math region inserts the corresponding
    lowercase Greek name at the cursor for all 23 letters in the layer-2 table above — e.g.
    `Ctrl+Alt+A` inserts `"alpha"`, `Ctrl+Alt+H` inserts `"eta"`, `Ctrl+Alt+T` inserts `"theta"`,
    `Ctrl+Alt+W` inserts `"omega"`, `Ctrl+Alt+Y` inserts `"tau"`, `Ctrl+Alt+Q` inserts `"psi"`. All
    23 lowercase Greek letters are reachable by a `Ctrl+Alt+` shortcut; `Ctrl+Alt+F`,
    `Ctrl+Alt+J`, `Ctrl+Alt+V` are not bound to anything.
15. No `Ctrl+Alt+<letter>` shortcut collides with any existing `Ctrl+Shift+<letter>` shortcut or
    any other pre-existing shortcut in the app (`Ctrl+Alt+` was entirely unused before this spec,
    confirmed by its absence anywhere in `livesheet/gui/` today). For the 12 letters that carry a
    meaning under both layers (B, G, D, Z, I, K, L, N, X, R, S, U), both shortcuts insert the same
    Greek letter — a user gets the identical result regardless of which modifier they used.
16. Uppercase Greek letters have no `Ctrl+Alt+` (or any other new) keyboard shortcut in this spec;
    all 10 remain reachable only by clicking their Elements-tab button.

## Edge cases
- **Tab-index remap on upgrade**: a `"side_panel_tab"` value saved before this spec (0, 1, or 2,
  meaning Symbols/Outline/Data under the *old* 3-tab layout) resolves to a *different* tab under the
  new 7-tab order (0=Elements, 1=Algebra, 2=Calculus) the first time a user opens an upgraded build.
  This is a one-time, purely cosmetic surprise (the panel still opens on some real tab, nothing
  crashes, nothing is lost) that self-corrects the moment the user clicks any tab, since the index is
  rewritten on every `currentChanged` signal; no migration code is proposed for this low-stakes case
  (see Open question 4).
- A narrow 120 px side panel with 7 tab labels, and an Elements tab with 40 entries, relies on Qt's
  own standard tab-bar overflow (scroll arrows / elide) and the existing `QScrollArea` the Symbols
  tab already used for a long button list — the same "no bespoke collapsing logic" posture spec 007
  already took for toolbar overflow; no custom tab-bar or list rendering is added by this spec.
- Switching tabs while a math region is mid-edit does not call `insert_token` and does not steal
  focus from the region being edited; only an explicit button click or keyboard shortcut does.
- A document containing zero math regions (first launch, or an emptied sheet) is unaffected: all
  three functional tabs still render their full token list regardless of canvas content, exactly as
  the old Symbols tab did; a Greek-letter shortcut (either layer) pressed with nothing being edited
  creates/focuses a new math region first, exactly like every existing `insert_token`-backed
  shortcut already does.
- Removing the Math toolbar removes its implicit second toolbar row; `MainWindow`'s existing
  `_repair_floating_toolbars()` safety net (spec 007 D1 fix) only ever needs to consider
  `standard_toolbar` now, since there is no second toolbar to stack under or to detect as
  erroneously floating — the developer should simplify or remove that helper's two-toolbar logic
  accordingly, rather than leaving it referencing a toolbar that no longer exists.
- `Ctrl+Shift+T` and `Ctrl+Shift+O` (free of any app-shortcut collision but ambiguous *within* the
  Greek alphabet under layer 1 — theta/tau and omicron/omega respectively) are simply not bound to
  anything under layer 1, consistent with layer 1's stated rule; this is unaffected by layer 2's
  full coverage, since layer 2 lives entirely under the separate `Ctrl+Alt+` modifier and does not
  retroactively fill in layer 1's gaps.
- `Ctrl+Alt+F`, `Ctrl+Alt+J`, `Ctrl+Alt+V` (the 3 letters left over once all 23 Greek letters are
  assigned under layer 2) fall through to whatever Qt's default handling of an unbound shortcut is
  (nothing happens), not a crash; they are not reserved for any future purpose by this spec.

## IP check
Pass. The only idea taken from the research above — organise a library of insertable math-building
blocks into named, switchable topic groups instead of one long flat list, so a growing tool can add
new groups over time — is documented, in some form, across all three products looked at, which is
exactly the kind of genuinely cross-product convention `.claude/skills/ip-cleanroom/SKILL.md` asks
for; nothing below is traceable to one of them specifically.

- **vs. Mathematica**: Mathematica's "Basic Math Assistant" is one of several separately named,
  separately opened *palette windows* reached from a flat `Palettes` menu (`PalettesMenu.html`
  itself describes a flat list of differently purposed palettes, not a single in-window tab bar);
  each such palette's own internal grouping (the 2009 blog post's "basic commands, algebra,
  calculus, matrix commands" wording) is not reproduced here — this spec uses none of Mathematica's
  own section names ("Basic Commands", "Expressions and Equations", "Linear Algebra and Matrices"
  are not used anywhere; "Elements" was Theo's own suggested wording for the basics group, arrived
  at before this research, not read from any Wolfram source), no separate floating-window mechanism
  (LiveSheet reuses its own already-shipped single dock), and no palette-button icon/template
  layout.
- **vs. Maple**: Maple's palettes are several separately titled, *simultaneously visible*,
  independently collapsible panels stacked in one sidebar — a fundamentally different interaction
  (show every category panel at once, expand/collapse each) from this spec's *exclusive*
  single-tab-at-a-time selection, which LiveSheet already had (Symbols/Outline/Data) before this
  spec and simply extends. None of Maple's specific category names (its Expression/Symbol/Matrix/
  Units/Relational/Operators/Arrows/Negated/Large-Operators split) are used; this spec's "Algebra"
  tab bundles operators and (eventually) rewrite rules/assumptions together rather than Maple's much
  finer per-operator-type split, and this spec has no Units palette at all.
- **vs. MATLAB**: MATLAB's Apps Gallery groups whole interactive *apps* (entire windows/workflows,
  opened by clicking a large icon in a gallery grid under a toolstrip button) into named domain
  categories, one of which — per the MathWorks blog cited above — bundles statistics- and
  optimization-related apps together; this is a different widget (icon gallery vs. a dockable
  tabbed panel), a different interaction (open a whole app/window vs. insert one token into the
  active region), and uses no MATLAB terminology beyond the fact that this spec's Statistics and
  Optimization tabs sit next to each other in the tab order — reflecting only the generic,
  cross-product observation that those two topics are commonly treated as neighbours in a math
  tool's own taxonomy, not any MATLAB-specific category name, icon, or gallery layout. ("Statistics"
  and "Optimization" as plain English words were already this project's own backlog item names,
  chosen on 2026-10-29 in `docs/board/backlog.md`, before this research pass.)
- **Greek letters and subscript (addenda 1 and 2)**: the Greek alphabet and subscript notation are
  universal mathematical notation used identically across every CAS/engineering tool and every
  mathematics textbook; `docs/IP-POLICY.md` explicitly allows "standard math/engineering notation"
  and "common function names" as free to use. No vendor's specific palette glyph set, button
  layout, icon, or keyboard-shortcut scheme was consulted for either addendum — the glyph↔English-
  name mapping is LiveSheet's own, already-shipped `engine/formatting.py` `GREEK` dict (not newly
  invented by this spec), and both keyboard-shortcut tables (the 12-letter `Ctrl+Shift+` table and
  the 23-letter `Ctrl+Alt+` table) are this spec's own, newly derived resolutions of purely internal
  constraints — English-transliteration collisions within the Greek alphabet itself, and collisions
  with LiveSheet's own pre-existing shortcuts — with no relationship to any vendor's shortcut
  scheme, since no vendor's Greek-letter-shortcut documentation was read or needed to derive either
  table.

No vendor name, icon, literal tab/menu label, or keyword set from any of the three products is used
anywhere in this spec. Nothing here is a novel on-canvas interaction technique (ip-cleanroom rule
6): a dockable panel with a tab bar and a scrollable list of ordinary click-to-insert buttons, plus
ordinary `QAction` keyboard shortcuts, is exactly the "boring, generic toolkit chrome" rule 6
prefers over anything bespoke — the same category of chrome spec 007 already used and the manager
already IP-approved. Not legal advice.

## Fits current architecture?
- **`livesheet/gui/sidepanel.py`**: restructure the existing `MATH_TOKENS`/`CATEGORY_ORDER`
  constants into the new 7-tab layout described above — every existing `(category, label, token,
  tip)` tuple's values are unchanged; only the mapping from old category name to new tab changes.
  Add the 33 new Greek-letter tuples (reading `engine/formatting.GREEK`'s keys directly, so the
  glyph/name list cannot drift from the display-side mapping — importing the dict rather than
  retyping its contents) and the 1 new Subscript tuple. Two new placeholder tabs
  (Statistics/Optimization) reuse the existing `_build_placeholder_tab(message)` helper verbatim,
  the same way Outline/Data already do — no new placeholder-rendering code needed. Exact
  constant/variable naming is the developer's choice; the data this spec requires is: an ordered
  list of 7 tab specs, each either (a) a tab name plus its list of `(label, token, tip)` entries,
  optionally further split into named sub-groups for the one tab (Elements) that needs sub-headers,
  or (b) a tab name plus a placeholder message string.
- **`livesheet/gui/main_window.py`**: delete the Math-toolbar construction block (the `QToolBar`
  itself, its "Text" action, its `MATH_TOKENS` loop, the `addToolBarBreak()` call stacking it under
  Standard) and its "Math Toolbar" `View`-menu toggle; leave the Standard toolbar, its `QAction`
  reuse, and its own `View`-menu toggle untouched. Simplify `_repair_floating_toolbars()` (spec 007
  D1's safety net) to consider only `standard_toolbar`, since there is no second toolbar to stack
  under or recover from floating anymore. Add 12 new `QAction`s with a `Ctrl+Shift+<letter>`
  shortcut (layer 1 table) and 23 new `QAction`s with a `Ctrl+Alt+<letter>` shortcut (layer 2
  table), each calling `insert_token` with the Greek name's text — same `_action(...)` helper and
  same pattern every existing shortcut in this file already uses; none of these 35 actions need a
  visible menu entry of their own (they exist purely as shortcuts; a developer may still choose to
  list them somewhere discoverable, e.g. as disabled-but-visible menu entries showing the shortcut,
  which is a presentation detail this spec does not mandate). No change to the `Insert` menu's
  existing quick-insert entries.
- **`livesheet/engine/formatting.py`, `livesheet/gui/pretty.py`**: unchanged, read-only sources for
  the Greek-letter/subscript button data; no new display logic needed since both already render
  the inserted text correctly today.
- **`livesheet/document.py`, `livesheet/engine/*`**: unchanged. No format-version bump, no
  `RegionData` change, no evaluator/formatting change — this is a GUI-chrome-only spec, identical in
  scope-shape to spec 007.
- Tests: new `tests/test_side_panel_categories.py` covering criteria 1-10 and 13 via
  `objectName`/tab-text lookups, token-label/token-string/tooltip equality checks against today's
  known values plus the new Greek/Subscript entries, a click-and-assert-inserted-text check for at
  least one entry per functional tab, a "no clickable widget, no `insert_token` call" check for the
  two new placeholder tabs, and a `QSettings`-injected stale `"math-toolbar"`-naming `"window_state"`
  blob loaded into a fresh `MainWindow` to exercise criterion 10's upgrade-safety claim. New
  `tests/test_greek_shortcuts.py` (or folded into the same file) covering criteria 11-12 and 14-16:
  every one of the 12 layer-1 and 23 layer-2 shortcuts via `QTest.keyClick`/`QAction.shortcut()`
  equality, an explicit regression check that the 5 pre-existing `Ctrl+Shift+` shortcuts still
  resolve to their original slots (identity check, not just label), and a check that no
  `Ctrl+Alt+<letter>` shortcut string appears twice or collides with any `Ctrl+Shift+` entry's
  underlying `QKeySequence`. Runs headless under `QT_QPA_PLATFORM=offscreen` like the project's
  existing GUI tests. The tester should also do a real-window pass on Theo's Mac: open the side
  panel, click through all 7 tabs, insert at least one token from each functional tab (including a
  Greek letter and the Subscript button) into a real math region, confirm the Math toolbar is
  genuinely gone from the top of the window, press a sample of both shortcut layers directly
  (including at least one of the four resolved-collision letters, e.g. `Ctrl+Alt+H` for eta and
  `Ctrl+Alt+W` for omega), confirm the 5 pre-existing `Ctrl+Shift+` shortcuts still do their
  original job, and confirm an existing on-disk LiveSheet preferences file (saved by a
  pre-spec-011 build, i.e. one that still has `"math-toolbar"` persisted) opens without error.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Mapping of today's 4 categories onto the new tabs, and the full initial tab list/order.**
   Recommendation (justified above from the research): fold "Statements" and "Constants" together
   into one **Elements** tab (Theo's own suggested word for "the basics you reach for on every
   line, independent of math domain"); rename "Operators" to **Algebra** (keeping its 3 existing
   tokens, and giving backlog 10/11 — assumptions, rewrite rules — an obvious future home); keep
   **Calculus** as its own tab, unchanged content; append empty **Statistics** and **Optimization**
   placeholder tabs (backlog 29/30, in that order, mirroring how those two topics are commonly
   neighbours in other math tools' own category taxonomies per the MATLAB research above); keep
   **Outline** and **Data** last, unchanged. Full order: Elements, Algebra, Calculus, Statistics,
   Optimization, Outline, Data (7 tabs). [Recommend accepting this exact mapping and order; the one
   visible change from today users would notice immediately is the "Operators" -> "Algebra" rename,
   flagged separately as open question 3 below in case Theo would rather keep "Operators" as a
   label even though its grouping now also anticipates backlog 10/11.]
2. **Should Outline/Data stay in the same tab bar, or be restructured (e.g. a second dock, or a
   nested tab-of-tabs)?** Recommendation: keep them in the exact same single `QTabWidget`/dock,
   simply appended after the five math-category tabs rather than interleaved — this is the
   mechanism spec 007 already shipped and IP-approved (one dockable panel, one tab bar, gui-concepts'
   "collapsible/dockable side panels" idea), and a second dock or a nested tab level would add real
   complexity (more screen real estate at the panel's already-tight 120-320 px width, or a two-level
   tab-switching UI with no established generic precedent strongly favouring it) for no behavioural
   benefit at this stage — nothing currently needs Outline/Data to be visible *simultaneously* with
   a math-category tab. [Recommend accepting; revisit only if a future spec genuinely needs
   simultaneous visibility of, say, Outline and a category tab, which nothing today requires.]
3. **The "Operators" -> "Algebra" rename** (open question 1's one user-visible label change beyond
   pure regrouping): [Recommend accepting "Algebra" since it names the *topic* (matching
   Calculus/Statistics/Optimization's naming style and giving backlog 10/11 a coherent home) rather
   than the *mechanism* (today's "Operators"); flagging explicitly in case Theo would rather keep
   the existing "Operators" label purely to minimise visible change for existing users.]
4. **Tab-index remap on upgrade** (see Edge cases): a pre-spec-011 saved `"side_panel_tab"` value
   will point at a different tab after this ships, self-correcting on the next click. [Recommend
   accepting as a one-time, low-stakes cosmetic quirk; no migration code proposed.]
5. **Tab-bar presentation at narrow widths** (7 labels in a 120-320 px dock, and a 40-entry Elements
   tab): this spec relies on Qt's own standard tab-bar overflow/elide behaviour and the existing
   scroll-area mechanism rather than specifying a particular visual fallback (e.g.
   vertical/side-oriented tabs, or collapsible Greek-letter sub-groups). [Recommend accepting Qt's
   default top-horizontal tab bar and a flat scrollable list, matching today's look; flag as a
   presentation detail the developer may revisit without needing a spec change, since no
   acceptance criterion depends on tab-bar orientation or sub-group collapsing.]
6. **RESOLVED (Theo, 2026-10-30) — Greek-letter keyboard-shortcut coverage.** Originally flagged as
   a genuine scope-limiting judgement call (only 12 of 23 lowercase letters would get a dedicated
   shortcut, none of the uppercase letters would). Theo chose full lowercase coverage via this
   spec's own flagged fallback: a second, previously-unused modifier combination, `Ctrl+Alt+
   <letter>`, added alongside the original 12 `Ctrl+Shift+` shortcuts (both layers described in
   full above, with their own resolution rule for the four within-Greek first-letter collisions).
   Uppercase Greek letters stay click-only (this specialist's own call per Theo's framing of the
   request as being about lowercase coverage specifically; reasoning given in the "Greek letters"
   behaviour section above) — no further manager/Theo confirmation needed on this point unless
   Theo disagrees with that one remaining call. Nothing further open here.
