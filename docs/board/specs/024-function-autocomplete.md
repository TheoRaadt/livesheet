# 024 Autocompletion of function and variable names in math regions

Source inspiration: generic, cross-application type-ahead / autocomplete list conventions
(popup of prefix matches, Up/Down to move, a key to accept, Esc to dismiss, minimum characters
before opening, list does not take keyboard focus). Public general guidance consulted:
W3C WAI-ARIA Authoring Practices, combobox with list autocomplete example,
https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-autocomplete-list/
(2026-11-09, concept only: arrows wrap at the ends, Esc closes without changing the text,
typing a matching prefix opens the list). No product's docs or UI were read. Theo's own
request (2026-11-09).

User story: while typing in a math region I get a small list of matching function and constant
names (and my own definitions from the sheet), each with a short signature hint, can pick one
with the arrow keys and insert it with Tab, or ignore it and keep typing.

## Current state (read from the code, 2026-11-09)
- The authoritative registry of built-in names is the module-level dict
  `livesheet/engine/evaluator.py: BUILTINS` (built by `_builtins()`: elementary/calculus entries,
  then `MATRIX_BUILTINS` from matrices.py and `STATS_BUILTINS` from statistics.py are merged in).
  It also contains non-user entries that must not be offered: names starting with `_`
  (`_mat`, `_c`, `_row`, `_idx`, `__builtins__`) and the parser helpers `Integer`, `Float`,
  `Rational`, `Symbol`, `Function` (the `_UNWRAPPED` set). Constants (`pi`, `e`, `I`, `oo`, `inf`)
  are non-callable entries.
- Many entries are wrappers (`_scalar_only`, `_needs_variable`, the statistics `_deferred`) whose
  own signature is `*args`; the real parameter names live on the wrapped Python function
  (e.g. `mean(v)`, `predict(coeffs, x)`, `poisson_cdf(k, lambda_)`). SymPy-backed entries
  (`sin`, `diff`, `integrate`, ...) have no useful Python signature.
- User definitions live only in the evaluation `env` of each recalculation, not in a persistent
  registry. `parse_statement()` (engine/syntax.py) returns `Statement(kind, name, params, ...)`
  and is cheap and side-effect free; kinds include define, global and range (the developer
  confirms which kinds carry a defined `name`).
- Math region editing: `MathRegion.handle_key` (regions.py) is the single entry point for
  key presses in the editor (`_Editor.keyPressEvent` forwards to it). While editing, the editor
  shows the RAW source text; pretty-printing (`gui/pretty.py`: Greek names -> glyphs, `sqrt(` ->
  radical, subscripts, calculus notation) happens only after editing ends.
- Greek letters: buttons/shortcuts insert the plain English name (`alpha`) into the text
  programmatically; typing the name by hand is equivalent. `Gamma` is both a Greek name and the
  built-in gamma function.
- Existing keys in a math region: Return/Enter commits the region, `:` and `=` have special
  handling, Ctrl+. inserts an arrow. Tab currently has no special meaning in a math region.
- Known gap: the engine's `BUILTINS` has ~120 entries; only the engine knows them. There is no
  completion code anywhere.

## Behaviour (own words)

### When the popup opens
The popup is evaluated (opened, refreshed or closed) after each editing key that changes the
text by typing: a character key, Backspace, Delete. It is NOT driven by the document's
`contentsChanged`, so programmatic insertions (Greek buttons and shortcuts, tab-band buttons such
as `sqrt(`, formula-tab inserts, the matrix dialog, paste) never open it.
Let `prefix` be the run of identifier characters (letters, digits, `_`) that ends exactly at the
caret, extended leftwards over the whole run. The popup is shown only if ALL hold:
1. the run starts with a letter or `_` (so `2m`, `3.5e`, `10s` are numbers/units in progress: no
   popup; a run preceded by `.` is likewise a number/attribute: no popup);
2. the run is at least 2 characters long (single letters are almost always variables);
3. the caret is at the END of the word: the character to the right of the caret (if any) is not
   an identifier character (editing in the middle of a word never pops up);
4. at least one candidate matches, and it is not the case that the only match is already
   exactly the typed name (nothing left to complete);
5. the region is a MathRegion in editing mode (never Text regions, never plot-spec editing);
6. the popup was not dismissed with Esc for this same word (see below).
A non-identifier character typed (space, operator, `(`, `,`, `:` ...) closes the popup. Caret
movement keys (Left/Right/Home/End), mouse clicks, focus loss, leaving edit mode and Enter all
close it. There is no manual trigger key in this slice (see open question 4).

### Candidates and ranking
- Builtin candidates come from `evaluator.BUILTINS` at the moment of the request (never from a
  second list), excluding names starting with `_` and the `_UNWRAPPED` parser helpers. Each is
  kind `function` if callable, else `constant`.
- User candidates (if cheap, and it is): names defined by OTHER regions on the same sheet,
  from `parse_statement` of each region source: a definition with parameters is kind
  `user_function` (hint `name(p1, p2)`), a plain definition or range variable is kind `variable`.
  Order on the sheet does not matter (a name defined further down is still offered). The region
  being edited is excluded. If a user name equals a builtin name only the user entry is listed.
  Unit names (`m`, `kg`, `MPa`, ...) are NOT candidates in this slice (open question 3).
- Match: case-insensitive prefix match on the typed run. Ranking: (1) exact-case prefix matches
  before case-insensitive-only matches; (2) user-defined before builtin; (3) shorter names first;
  (4) alphabetical. No cap on the list length; the popup shows a window of 8 rows and scrolls.
- Greek names are NOT candidates (they are letters, not engine entries); `Gamma` appears as the
  gamma function because it is in the registry.

### Signature hints
A short string shown in muted text beside each candidate, e.g. `predict(coeffs, x)`.
Resolution order (engine side, `completion.signature_for(name)`):
1. a small hand-written override table `SIGNATURE_OVERRIDES` for entries without a usable
   Python signature (SymPy-backed ones: `sin(x)`, `sqrt(x)`, `root(x, n)`, `diff(expr, x)`,
   `integrate(expr, x)`, `integrate(expr, x, a, b)`, `limit(expr, x, point)`, `sum(expr, k, a, b)`,
   `solve(eq, x)` ... the developer writes these in own words);
2. else derived with `inspect.signature` of the underlying plain Python function, found by
   following `__wrapped__`. To make that work the three wrapper factories (`_scalar_only`,
   `_needs_variable`, statistics `_deferred`) must set `wrapper.__wrapped__ = fn` (a one-line,
   behaviour-neutral engine change). Parameter names are shown with a trailing `_` stripped
   (`lambda_` -> `lambda`); defaults shown as `name=default`;
3. else no hint (the name is still listed).
The overrides table must not duplicate what derivation already gives for statistics/matrix
functions. No hint is ever required to list a candidate, so a newly added builtin appears
immediately even before someone writes a hint for it. A drift test (below) reports builtins
that have no hint so they get one.

### Keys while the popup is open
- Down / Up: move the highlight; wraps (last -> first, first -> last). The first row is
  highlighted when the popup opens.
- Tab: accept the highlighted row (see "Accepting"). Chosen over Enter on purpose: Enter keeps
  its existing meaning of committing the region, so finishing `x := mean` + Enter never
  accidentally rewrites what was typed. With the popup closed, Tab is unchanged.
- Esc: close the popup only. The region stays in editing mode and the text is unchanged; the
  popup stays closed for the rest of that word and reappears when a new word is started. A second
  Esc behaves as today (leaves editing).
- Mouse: clicking a row accepts it; the popup never takes keyboard focus (the caret stays in the
  editor).
- PageUp / PageDown: move the highlight by one window (8 rows). All other keys fall through to
  the editor, then the popup is re-evaluated.

### Accepting: name plus opening parenthesis or just the name
Decision: a `function` or `user_function` is inserted as `name(`; a `constant` or `variable` is
inserted as `name` alone. Justification: nearly every built-in is called with arguments, the
Algebra/Calculus buttons already insert `sqrt(`, `diff(`, `integrate(` including the paren, so the
convention is consistent and saves a keystroke; constants and plain variables are never called.
The editor does not auto-close brackets elsewhere, so no closing `)` is inserted (consistent;
and avoids overtype logic). Exception: if the character right after the caret is already `(`,
only the name is inserted (editing an existing call must not double the paren).
Accepting replaces the typed run (from its start to the caret) with the chosen text, puts the
caret right after it, closes the popup and leaves the region in editing mode. Inserted text is
plain ASCII names exactly as stored in the registry, so the saved source, the engine and the
pretty-printer are unaffected (`Gamma(` later displays as Γ(, `pi` as π, as for hand-typed text).

### Display and popup chrome
- The popup is drawn on the canvas as a scene-level item (not a separate window), anchored just
  below the caret line at the x of the start of the typed run; if it would extend below the
  visible viewport it opens above the line instead. It scales with zoom and is hidden while
  exporting (`Worksheet.printing`). Reason: no OS popup window, no focus theft (the code base
  already has macOS focus workarounds), headless-testable.
- Each row: the candidate name, then the muted hint; a small kind tag for constants and user
  items (e.g. "const", "var"). Highlight row uses the existing selection accent. Width fits the
  longest visible row up to 360 scene units, then text is elided. The raw names are shown, never
  the pretty-printed glyph forms, because the editor itself shows raw text while editing.
- Light/dark: uses the same colour tokens as the other canvas chrome (frame colour constants in
  regions.py); contrast not below the existing hint text.
- Accessibility: the popup exposes `is_open()`, `candidates()` and `highlighted()` for tests and
  for a later screen-reader hook; keyboard access is complete (no mouse needed).

### Interaction with Greek shortcuts and pretty-printing
- Greek insertion (buttons, Ctrl+Shift+letter, Ctrl+Alt+letter) is programmatic, so it never
  opens the popup, and it closes an open one. Typing a Greek name by hand opens the popup only if
  the name prefixes a registry entry (e.g. `Gam` -> `Gamma`); `alpha`, `beta`, `mu` ... match
  nothing and stay silent.
- Because the popup lists raw names and inserts raw names, the pretty display after editing is
  exactly what hand typing the same text would give. Nothing in pretty.py changes.
- The existing `:`/`=`/`~`/Ctrl+. handling in `MathRegion.handle_key` is untouched: those keys
  are non-identifier characters and simply close the popup.

## Engine API (Qt-free; new module livesheet/engine/completion.py; must not import PySide6)
```
@dataclass(frozen=True) class Candidate: name: str; kind: str   # function|constant|user_function|variable
                                         signature: str = ""     # "" when unknown
def builtin_candidates() -> list[Candidate]            # read from evaluator.BUILTINS every call
def user_candidates(sources: Iterable[str]) -> list[Candidate]   # parse_statement, cached per source text
def word_at(text: str, caret: int) -> tuple[int, str] | None     # (start, run) or None (rules 1-3)
def complete(text: str, caret: int, user_sources: Iterable[str] = ()) -> Completion | None
    # Completion(start, prefix, candidates: list[Candidate]) ranked; None when the popup should not show
def accept(text: str, caret: int, candidate: Candidate) -> tuple[str, int]   # (new_text, new_caret)
def signature_for(name: str) -> str
```
`engine/__init__.py` may re-export nothing new; the GUI imports `..engine.completion`.

GUI side: a `CompletionPopup` scene item plus a small controller owned by `MathRegion`;
`Worksheet` provides the other regions' sources (`[r.source for r in regions if r is not region
and isinstance(r, MathRegion)]`). Key handling is added at the top of `MathRegion.handle_key`
(only when the popup is open); the refresh runs after the editor has processed the typed key (a
flag set in `_Editor.keyPressEvent` around `super().keyPressEvent`), not before. If Tab is
swallowed by the view's focus traversal before reaching the editor, the view must let the item see
it while a popup is open (override `focusNextPrevChild` in `WorksheetView` to return False then);
the developer verifies this on macOS.

## Syntax proposal (own keywords)
None. No grammar change, no new statement.

## .lsheet file format impact
None. Completion only edits the text the user would have typed.

## Acceptance criteria
Engine tests (no Qt at all; `import PySide6` must not happen: assert it is absent from
`sys.modules` after importing livesheet.engine.completion in a fresh interpreter). `C(text,caret)`
below means `complete(text, len(text) if caret omitted)`.

E1. Registry-driven. Monkeypatch `evaluator.BUILTINS["zzz_probe"] = lambda x: x`:
    `complete("zzz", 3)` lists `zzz_probe` with kind `function`, with no other code change; after
    removing it, `complete("zzz", 3)` is None.
E2. Statistics names present. For every name in `statistics.STATS_BUILTINS` and every public
    (not `_`-prefixed) name in `matrices.MATRIX_BUILTINS`, `complete(name[:-1], len(name)-1)` (or
    `name[:2]` for 2-char names) contains that name. This is the "never stale" test.
E3. Exclusions. No candidate name starts with `_`; `Integer`, `Float`, `Rational`, `Symbol`,
    `Function` and `__builtins__` never appear (e.g. `complete("Int", 3)` is None).
E4. Ranking. `complete("me", 2)` names, in order: `mean`, `median`. `complete("fit_", 4)` names:
    `fit_poly`, `fit_linear`. `complete("no", 2)` first name: `norm`; the list also contains
    `normal_cdf`, `normal_pdf`, `normal_quantile`, `normal_sample`. `complete("si", 2)` first name
    `sin`. `complete("ma", 2)` lists `max` before `Max` (exact-case first).
E5. Hints. `signature_for("mean") == "mean(v)"`, `"fit_linear" -> "fit_linear(x, y)"`,
    `"predict" -> "predict(coeffs, x)"`, `"normal_cdf" -> "normal_cdf(x, mu, sigma)"`,
    `"poisson_cdf" -> "poisson_cdf(k, lambda)"`, `"binomial_pmf" ->
    "binomial_pmf(k, n_trials, p)"`, and `"normal_sample" -> "normal_sample(mu, sigma, n, seed)"`
    (derived through `__wrapped__`); `signature_for("sin")` is non-empty from the override table.
    The wrapped builtins still behave identically (existing suite stays green).
E6. Drift test. Every public builtin that is callable has a non-empty `signature_for`; the test
    fails with the list of names lacking a hint, and a second assertion fails if
    `SIGNATURE_OVERRIDES` has a key that is not in `BUILTINS` (orphan hint).
E7. Not in numbers. `complete("2m", 2)`, `complete("3.5e", 4)`, `complete("x = 10s", 7)`,
    `complete("a.me", 4)` are all None.
E8. Minimum length. `complete("s", 1)` is None; `complete("si", 2)` is not.
E9. Caret inside a word. `complete("sqrt", 2)` (caret after `sq`) is None.
E10. Nothing left to complete. `complete("mean", 4)` is None; `complete("mea", 3)` lists `mean`.
E11. Accept. `accept("2*me", 4, mean)` == (`"2*mean("`, 7). `accept("x = p", 5, pi)` ->
     (`"x = pi"`, 6) (constant: no paren). `accept("me(1)", 2, mean)` == (`"mean(1)"`, 4)
     (next char is `(`: name only). `accept("1+sq", 4, sqrt)` == (`"1+sqrt("`, 7).
E12. User names. With sources `["rate := 3", "area(w, h) := w*h", "g(x) ≡ x^2", "total ="]`:
     `complete("ar", 2, sources)` first entry is `area`, kind `user_function`, signature
     `"area(w, h)"`; `complete("ra", 2, sources)` first entry is `rate` (kind `variable`, accepted
     without a paren) and also lists `rank`; `complete("to", 2, sources)` has no `total` (an
     evaluate-only line defines nothing). With a source `mean := 3`, `complete("mea", 3,
     sources)` lists `mean` exactly once, kind `variable`. Malformed sources are ignored, not raised.

GUI tests (offscreen; send `QKeyEvent`s through `region.editor.keyPressEvent` so the real
handle_key path runs; the popup exposes `is_open()`, `candidates()` (names) and `highlighted()`):

G1. Open. New MathRegion editing, type `m`, `e`: popup open, `candidates()[:2] == ["mean",
    "median"]`, `highlighted() == 0`. After typing only `m`: closed.
G2. Navigate and accept. Down -> `highlighted() == 1`; Tab -> `region.editor.toPlainText() ==
    "median("`, popup closed, `region.editing` True, caret at the end. Down from the last row
    wraps to row 0; Up from row 0 wraps to the last row.
G3. Esc. Popup open for `me`; Esc -> popup closed, `region.editing` True, text `me`. Typing `a`
    (making `mea`) does NOT reopen it for this word; after typing a space and then `me` again it
    opens. A second Esc then leaves editing.
G4. Enter. Popup open for `me`; Enter -> region commits with `source == "me"`, popup closed (it
    does not accept).
G5. Programmatic insert. `editor.textCursor().insertText("sin")` (what Greek buttons/formula
    inserts do) and the Greek shortcut Ctrl+Alt+A (inserts `alpha`) never open the popup; with
    the popup open, such an insert closes it.
G6. Greek interplay. Typing `alp` -> no popup (nothing matches). Typing `Gam` -> popup with
    `Gamma`; Tab -> source `Gamma(`; after Return the displayed text is the Greek-rendered form
    (`Γ(` appears in the pretty HTML) exactly as for hand-typed `Gamma(`.
G7. Closing events. Typing `(`, a space or an operator closes the popup; Left/Right arrow keys
    close it; leaving edit mode closes it; deleting the region while it is open does not crash.
G8. Number context. Typing `2` `m` `e` -> never opens.
G9. User names from the sheet. Another region `area(w, h) := w*h` exists; typing `ar` in a second
    region opens the popup with `area` first; Tab -> `area(`.
G10. Mid-word edit. Source `sqrt(x)`, caret moved between `sq` and `rt`, type a letter that keeps
     the run `sq?rt`: no popup (rule 3).
G11. Tab outside the popup. With the popup closed, Tab behaves exactly as before this feature
     (record the current behaviour in the test and keep it).
G12. Not offered elsewhere. A TextRegion and a plot-spec editor never show the popup.
G13. Printing. With `Worksheet.printing` set, the popup item is not painted.

## Edge cases
- Very long candidate lists (e.g. typing `_`-less two-letter prefixes): scroll window of 8;
  highlight stays visible (scroll follows the highlight).
- The popup near the right edge of the page: it may extend past the page width line; it is clamped
  to the visible viewport horizontally.
- Undo: none exists; accepting is a plain text edit that the user can retype.
- IME composition or dead keys: popup refresh waits for the committed character.
- A name that is both Greek and a function (`Gamma`) completes as the function; the display
  later renders the glyph. Nothing special-cased.
- Registry entries added later (new engine modules) appear automatically; hints appear once
  added (the drift test flags missing ones).
- Performance: `builtin_candidates()` walks ~120 dict entries and `user_candidates()` parses
  each other region's source once (cached by source text); no evaluation happens, so a keystroke
  stays far below the 300 ms feedback threshold even for hundreds of regions.

## IP check: pass
Prefix-matching autocompletion popups with arrow-key navigation, a commit key and Esc to dismiss
are an ubiquitous editor convention (code editors, shells, search boxes, form comboboxes) and are
documented by neutral standards bodies; nothing is specific to the engineering-worksheet category
or to any named product. The candidate names come from LiveSheet's own engine registry; the
signature hints are derived from LiveSheet's own Python functions or written in own words; no
vendor keyword list, help text or function catalogue was consulted or reproduced. The popup is
generic toolkit-style chrome (a list under the text being typed), not a bespoke on-canvas live
placeholder interaction (ip-cleanroom rule 6). No new dependency.

## Fits current architecture?
- NEW livesheet/engine/completion.py (Qt-free): imports `evaluator.BUILTINS` and
  `syntax.parse_statement` only; does not import PySide6 (acceptance E-block checks).
- livesheet/engine/evaluator.py, statistics.py: three one-line `wrapper.__wrapped__ = fn` edits
  (behaviour-neutral) so signatures are derivable.
- livesheet/gui/regions.py: `MathRegion` owns the controller and the popup key handling at the top
  of `handle_key`; `_Editor.keyPressEvent` marks "typed key" around the default handling.
- livesheet/gui/worksheet.py (or a new livesheet/gui/completion_popup.py): the popup scene item,
  `printing` suppression, supplier of the other regions' sources, view `focusNextPrevChild` tweak
  if Tab is intercepted.
- livesheet/gui/pretty.py, keys.py, document.py: unchanged.
- Order of work: engine module + tests first (E-block), then the GUI (G-block).

## Open questions (for Theo / manager)
1. Accept key: I chose Tab only, keeping Enter = commit region. Should Enter also accept when a
   row was explicitly highlighted with Up/Down (many editors do)? Default: no.
2. Insert `name(` for functions (chosen) versus name only. Confirm the opening parenthesis.
3. Offer unit names (`m`, `kg`, `MPa`) and the model/solve keywords (`vary`, `settle`, ...)
   as candidates? Default: no, to keep the list about functions and the user's own names.
4. A manual trigger (e.g. a modifier+Space) is not included: Ctrl+Space collides with macOS input
   -source switching and Cmd+Space with Spotlight. Add a different manual shortcut later, or never?
5. Minimum of 2 typed characters (e.g. `si`). Would you prefer 3?
6. Signature hints for SymPy-backed functions are a hand-written table (~40 entries); the drift
   test forces adding a hint when a new builtin ships. Acceptable maintenance cost?
