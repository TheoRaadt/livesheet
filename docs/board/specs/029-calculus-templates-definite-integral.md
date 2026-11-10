# 029 Calculus tab: complete insert templates and a definite-integral button

Closes backlog 64. Small GUI slice (about 0.5-1 day), plus a handful of test and doc corrections.
No engine change is required (see "Engine behaviour today"); no new dependency.

Source inspiration (concept only, nothing copied):
- Standard mathematical notation for indefinite and definite integrals, derivatives and limits
  (textbook convention, no source text used).
- The generic "insert a complete template and pre-select the first part to replace" convention
  common to code editors and equation editors in general (often called snippets or tab stops).
  Only the generic idea is used: plain text goes into the existing text editor and one span is
  selected. No on-canvas placeholder boxes, no live drawing on the sheet.
- Qt text-cursor selection API (QTextCursor setPosition with KeepAnchor), public Qt documentation;
  the developer re-reads it. Consulted 2026-11-10 as a concept check only (not fetched in this
  session).
- Own prior material: sidepanel.py (`MATH_TOKENS`, `TAB_CATEGORIES`), main_window.insert_token,
  gui/pretty.py, tests/test_calculus.py and tests/test_pretty_calculus.py, spec 024 (insertion
  convention for functions), spec 022 (tab strip and button band).
No vendor software, help text or example was consulted.

## User story
As an engineer I click the integral button and get a complete, valid `integrate(f, x)` with `f`
selected, so I just type my integrand and the region never shows a Syntax error. I click a second
button next to it for a definite integral with bounds `a` and `b` (numbers, symbols, bounds with
units such as `0 m`, or `oo`), and the same applies to `d/dx` and the other buttons that used to
leave an open bracket.

## What exists today (investigated)
- `MATH_TOKENS` rows are 4-tuples `(category, label, token, tip)`. A button click calls
  `SidePanel._insert_token(token)` which is `MainWindow.insert_token(token)`: it takes the editing
  math region (or creates one) and does `region.editor.textCursor().insertText(token)` then
  `setFocus()`. The caret ends after the inserted text. There is NO way to place the caret or a
  selection inside the inserted text. `symbol_buttons` is keyed by the button label (labels must be
  unique).
- Tokens ending in an unclosed bracket today: Algebra `sqrt(` and `root(`, Calculus `diff(` and
  `integrate(`. No other Elements, Algebra, Calculus, Statistics, Optimization, formula-tab or Data
  token leaves a bracket open (statistics rows are already complete such as `mean(v)`). There are no
  `limit`, `series`, `sum` or `product` buttons today.
- A region whose text is a bare expression (no `=`, `→`, `:=`) is only validated, so an
  unfinished `integrate(` shows "Syntax error", while a complete `integrate(f, x)` shows no result
  and no error.
- `pretty.py` already renders `diff(f, x)`, `diff(f, x, n)`, `integrate(f, x)` and
  `integrate(f, (x, a, b))` (including units and `oo`) once the region is not being edited. `limit`,
  `sqrt`, `root` get no calculus layout (sqrt shows as `√(`).

## Behaviour (own words)

### 1. Buttons (Calculus tab, in this order)
| label | token inserted (closed, valid text) | tooltip (own wording) |
|---|---|---|
| `d/dx` | `diff(f, x)` | Derivative of f with respect to x. Type your expression over f; rename x if needed. |
| `∫` | `integrate(f, x)` | Indefinite integral of f with respect to x. |
| `∫ₐᵇ` | `integrate(f, (x, a, b))` | Definite integral of f for x from a to b. Bounds can be numbers, names, values with units such as 0 m, or oo for infinity. |
| `lim` | `limit(f, x, 0)` | Limit of f as x approaches 0. Change 0 to another value, or to oo for infinity. |

`∫ₐᵇ` is the new definite-integral button, placed right after `∫`. `lim` is a small addition so
the audit is consistent (the function-call form is already engine-supported); `series`, `sum`,
`product` buttons are NOT added here (open question 4). If the glyph pair in `∫ₐᵇ` does not render in
the default macOS font the developer falls back to the label `∫ a..b` (labels only need to be
unique and readable; tests use the label constant from sidepanel, not a literal).

### 2. Consistent rule for every formerly open-bracket token
Every token that used to end in an unclosed bracket becomes a complete, closed template. The first
part the user must fill is selected after insertion, so typing replaces it.

| label | old token | new token | selected after insert |
|---|---|---|---|
| `√` | `sqrt(` | `sqrt(x)` | `x` |
| `ⁿ√` | `root(` | `root(x, n)` | `x` |
| `d/dx` | `diff(` | `diff(f, x)` | `f` |
| `∫` | `integrate(` | `integrate(f, x)` | `f` |
| `∫ₐᵇ` | (new) | `integrate(f, (x, a, b))` | `f` |
| `lim` | (new) | `limit(f, x, 0)` | `f` |

Unchanged: `x²` (`^2`), `xₙ` (`_`), every Greek, constant, statement, formula-tab and statistics
token. Decision: all six change together (one rule: "a button never leaves the region
syntactically broken"); the algebra pair is included although backlog 64 only named calculus
(open question 1; it forces updating five existing assertions, listed below).

### 3. Caret and selection mechanism (minimal change)
Keep the `MATH_TOKENS` 4-tuple shape and keep `insert_token(token: str)` unchanged for callers
(menu items, Greek shortcuts, Data buttons, every test that spies on it). Add ONE new module-level
mapping in `gui/sidepanel.py`:

`TOKEN_SELECTION: dict[str, tuple[int, int]]` mapping a token string to the (start, end) offsets,
relative to the start of the inserted text, of the span to select after insertion. Offsets (token
text unchanged, so the engine round-trip tests of every token keep working):
- `sqrt(x)` -> (5, 6); `root(x, n)` -> (5, 6); `diff(f, x)` -> (5, 6);
  `integrate(f, x)` -> (10, 11); `integrate(f, (x, a, b))` -> (10, 11); `limit(f, x, 0)` -> (6, 7).
A token without an entry behaves exactly as today (caret after the text).

`MainWindow.insert_token` change: after `insertText(token)` (done as one edit, so one undo step
removes the whole template), look the token up in `TOKEN_SELECTION`; if present, set the editor's
text cursor to position `insert_start + start`, then move to `insert_start + end` keeping the anchor
(selection), and `setTextCursor` it. `insert_start` is the cursor position before insertion (the
start of the replaced selection if one existed). Insertion in the middle of existing text works
the same way (e.g. `y := |` then `∫` gives `y := integrate(f, x)` with `f` selected).

If text was selected before the click, behaviour is unchanged from today: the selection is
replaced by the template (open question 3 asks whether to wrap it instead).
Moving between the remaining parts (`x`, `a`, `b`) is done with the mouse or arrow keys in this
slice; open question 2 proposes Tab-to-next-part as a follow-up.

### 4. Bounds with units, symbolic and infinite bounds (engine behaviour today)
No engine change needed. Basis: existing passing tests in tests/test_calculus.py (marked "tested")
and reading evaluator.py/units.py (marked "derived, to be pinned"). I had no way to run
`Engine().evaluate` in this session (no shell tool), so every "derived" line below must be
confirmed by the developer's first test run; if one differs, the real output wins and this spec is
amended in docs/board/log.md.

| source (a region each) | expected output | basis |
|---|---|---|
| `integrate(2*x, (x, 0, 3)) →` | `→ 9` | tested |
| `integrate(x^2, (x, 0, 2)) →` | `→ 8/3` | tested |
| `integrate(x^2 - 2*x, (x, 0, 3)) =` | `= 0` | derived: 9 - 9. NOTE: the example in backlog 64's chat gave 3; the correct value is 0 |
| `integrate(x^2 - 2*x, (x, 0, 2)) →` | `→ -4/3` | derived |
| `integrate(x^2 + 2*x, (x, 0, 3)) =` | `= 18` | derived |
| `accel := 2 m/s^2` then `integrate(accel, (t, 0 s, 4 s)) =` | `= 8 m/s` | tested |
| same, with `= km/hr` | `= 28.8 km/hr` | tested |
| `P := 100 W` then `integrate(P, (t, 0 s, 10 s)) =` | `= 1000 J` | tested |
| `k := 2 N/m` then `integrate(k*x, (x, 0 m, 3 m)) =` | `= 9 J` | derived (x is unitless, the bounds carry the length) |
| `integrate(exp(-x), (x, 0, oo)) →` and `=` | `→ 1` and `= 1` | derived (`oo` is a built-in constant) |
| `integrate(1/x^2, (x, 1, oo)) =` | `= 1` | derived |
| `integrate(exp(-x^2), (x, -oo, oo)) =` | number equal to sqrt(pi) = 1.7724538509 (compare with tolerance 1e-6, not as text) | derived |
| `integrate(x^2, (x, 0, b)) →` | `→ b³/3` | derived |
| `integrate(x^2, (x, 0, b)) =` | error containing `not defined` | derived (same class as the tested `diff(x^3, x) =`) |
| `b := 3`, `integrate(x^2, (x, 0, b)) =` | `= 9` | derived |
| `limit(sin(x)/x, x, 0) →` | `→ 1` | tested |
| `limit(1/x, x, oo) →` | `→ 0` | tested |

Findings and gaps (all reported, none fixed here):
- G1 (docs): the manual (docs/manual/main-window.md lines 115-116) and the autocomplete signature
  hint (engine/completion.py `SIGNATURE_OVERRIDES["integrate"]` = `integrate(expr, x, a, b)`) say
  bounds are written `x, a, b`. The working and pretty-printed form is `integrate(expr, (x, a, b))`;
  the flat form probably fails inside SymPy (unverified). Fix both texts in this slice (hint text
  and manual wording only; no behaviour change).
- G2 (engine, not fixed): the integration variable name is substituted from the sheet if it is
  defined (e.g. after `x := 2`, `integrate(x^2, x)` becomes an integral over a number and gives a
  SymPy-flavoured error, as `diff(x^2, 5)` gives a message containing "number"). The keyword form
  `→ integrate, x` avoids this. Not fixed; mention in the manual; open question 6.
- G3 (engine, not fixed): bounds of different dimension (for example `1 m` to `3 s`) are expected
  to fail only when the result mixes dimensions; a lone zero bound loses its unit. No new
  validation is added.
- G4 (pretty): `limit`, `root`, `sqrt` are not drawn in textbook layout. Out of scope.

### 5. Pretty rendering of the definite form (gui/pretty.py)
No change required: `_render_calc_call` already produces `∫<sub>a</sub><sup>b</sup> expr dx`.
New tests pin the shapes the new templates produce (exact HTML strings in the criteria below).
`oo` shows as `∞`; `-oo` as `-∞`; unit bounds keep their text (`0 m`). While the region is being
edited the raw text is shown, so the freshly inserted template is visible as typed text.

## Acceptance criteria (headless-testable)
Run with `QT_QPA_PLATFORM=offscreen`, `MainWindow` as in tests/test_side_panel_categories.py;
"click" = `win.side_panel.symbol_buttons[label].click()` on a blank sheet; `r` =
`win.sheet.editing_region()`; `sel = r.editor.textCursor()`.

A. Token table (sidepanel data)
1. Calculus category rows are, in order, `(d/dx, diff(f, x))`, `(∫, integrate(f, x))`,
   `(∫ₐᵇ, integrate(f, (x, a, b)))`, `(lim, limit(f, x, 0))`; Algebra rows are `(√, sqrt(x))`,
   `(ⁿ√, root(x, n))`, `(x², ^2)`, `(xₙ, _)`. Labels in `symbol_buttons` are unique.
2. No token anywhere in `MATH_TOKENS` has more `(` than `)` (balance check over all rows).
3. Every key of `TOKEN_SELECTION` is a `MATH_TOKENS` token, and `token[s:e]` is `x` for `sqrt(x)`
   and `root(x, n)`, `f` for `diff(f, x)`, `integrate(f, x)`, `integrate(f, (x, a, b))` and
   `limit(f, x, 0)`.

B. Insertion and selection
4. Click `∫`: `r.source == "integrate(f, x)"`, `sel.selectedText() == "f"`,
   `(sel.selectionStart(), sel.selectionEnd()) == (10, 11)`. Same pattern for `d/dx`
   (`diff(f, x)`, (5, 6)), `∫ₐᵇ` (`integrate(f, (x, a, b))`, (10, 11)), `lim` (`limit(f, x, 0)`,
   (6, 7)), `√` (`sqrt(x)`, (5, 6)), `ⁿ√` (`root(x, n)`, (5, 6)).
5. After click `∫ₐᵇ`, `r.editor.textCursor().insertText("x^2")` leaves `r.source ==
   "integrate(x^2, (x, a, b))"`, and the editor still has focus semantics unchanged (region still
   in editing mode).
6. Insert in the middle: region text `y := ` caret at end, click `∫`: source `y := integrate(f, x)`,
   selection (15, 16)... i.e. selected text `f` and start == 5 + 10.
7. A token with no `TOKEN_SELECTION` entry (click `x²` on text `x`) gives `x^2` with the caret at the
   end and an empty selection, as before. Greek `alpha` via `win.insert_token("alpha")` unchanged.
8. Clicking a button with no editing region creates a math region and does the same as 4.
9. With text selected (`abc`) and a click on `d/dx`, the result is `diff(f, x)` (selection replaced)
   with `f` selected.
10. `win.insert_token` spied (as in tests/test_spec011_side_panel_greek_blackbox.py): the side
    panel still calls it with exactly the token string (no extra arguments).

C. Engine: no syntax error and the documented results
11. For each of the six templates, `Engine().evaluate([(0, template)])[0]` has status `ok` and
    empty output (bare expression, nothing shown, no Syntax error).
12. The engine rows of the table in section 4 give the stated outputs (rows marked "derived" may be
    corrected once, by the developer, to the real output if the reason is a formatting detail;
    a numerically different value is a defect to report).
13. Error case: `integrate(x^2, (x, 0)) →` returns status `error` with a non-empty message that
    does not contain a Python traceback or the substring `Traceback`.
14. Error case: `integrate(x^2, (x, 0, b)) =` returns an error containing `not defined`.

D. Pretty (`pretty_source_html`)
15. `integrate(f, x)` -> `∫ f dx`
16. `integrate(f, (x, a, b))` -> `∫<sub>a</sub><sup>b</sup> f dx`
17. `integrate(exp(-x), (x, 0, oo))` -> `∫<sub>0</sub><sup>∞</sup> exp(-x) dx`
18. `integrate(x^2, (x, 0 m, 3 m))` -> `∫<sub>0 m</sub><sup>3 m</sup> x<sup>2</sup> dx`
19. `integrate(f, (x, -oo, oo))` -> `∫<sub>-∞</sub><sup>∞</sup> f dx`
20. `diff(f, x)` -> `d/dx (f)`; `limit(f, x, 0)` stays `limit(f, x, 0)`; `sqrt(x)` -> `√(x)`.
21. A MathRegion with source `integrate(f, (x, a, b))` that is not being edited has display HTML
    equal to item 16 (follow the pattern in tests/test_pretty_calculus.py).

E. Existing tests that must be updated by the developer (token text only; labels unchanged)
- tests/test_spec011_side_panel_greek_blackbox.py: `EXPECTED_ALGEBRA` (line ~126),
  `EXPECTED_CALCULUS` (~129), and the two `region.source.strip() == "sqrt("` / `"diff("` asserts
  (~300, ~352).
- tests/test_side_panel_categories.py lines ~111 and ~124 (`sqrt(`, `diff(`).
- tests/test_spec022_tab_strip_review.py ~419 (tokens `sqrt(`, `diff(`).
- tests/test_wrapping_tab_strip.py ~436 (`token.startswith("diff(")` still passes; no change).
- Calculus tab now has 4 buttons: grep for "Calculus 2" style button counts (spec 022 criterion
  mentions "Calculus 2") and update.

F. Docs the documenter updates after acceptance
docs/manual/main-window.md Calculus bullet (templates, selected part, the four buttons, bounds
with units and `oo`, correct bounds syntax), errors.md only if new messages appear (none planned),
and the G1 hint text.

## Edge cases
- Template inserted while the editor already holds text and a popup (spec 024) is open: insertion
  is a plain editor edit; the popup follows its normal refresh and closes on a non-word position.
- Undo: the template insertion is one undo step (a single edit block).
- Placeholders are real letters, not special characters: if the user forgets to replace `f`, the
  region still saves and reloads as ordinary text; evaluating gives the usual "not defined" error.
- Saved files are unaffected (tokens only insert text); `.lsheet` format unchanged.
- Zoom, theming and wrapping tab strip: one extra button flows in the existing FlowLayout.
- The variable named `x` colliding with a user definition of `x`: see G2.

## IP check
Pass. Content is standard mathematical notation and plain code text (`integrate`, `diff`, `limit`
are already this project's own function names). The "complete template with the first part
selected" is a generic text-editor convention common across editors; it is implemented as ordinary
text in the existing editor, not as drawn placeholder boxes or live on-canvas editing (the
patent-sensitive style avoided per IP-POLICY rule 6; the boring toolkit-chrome version is used
deliberately). Button labels are generic maths glyphs; tooltip wording is own. No vendor keyword
set, layout or help text used. No vendor names appear in this spec.

## Fits current architecture?
- gui/sidepanel.py: four edited rows, one new row (and one for `lim`), new `TOKEN_SELECTION`
  dict; no change to `_build_functional_tab`.
- gui/main_window.py `insert_token`: about 8 lines (selection after insert).
- engine/completion.py: one hint string (G1). No other engine change, nothing in document.py.
- gui/pretty.py: no code change.
- tests: updates listed in E plus a new tests/test_spec029_calculus_templates.py.

## Open questions for Theo
1. Include `√` and `ⁿ√` in the closed-template change (recommended, one rule), or only the calculus
   buttons? (Costs updating about five existing test assertions.)
2. Add Tab (when no completion popup is open) to jump to the next remaining part (`x`, `a`, `b`)?
   Needs a small per-region list of remaining parts; deferred unless wanted.
3. When text is selected and a template button is clicked, wrap the selection into the first part
   instead of replacing it (more convenient, small extra rule)?
4. Add more buttons now (`series`, sum, product) in the same style, or later?
5. Your example `integrate(x^2 - 2x, (x, 0, 3)) = 3` is actually 0 (9 - 9); is another integrand
   intended (this spec uses `x^2 + 2*x` = 18 and `x^2 - 2*x` = 0 / -4/3)?
6. Should the integration variable be protected from a sheet definition of the same name (G2),
   as the keyword form already does? Separate engine item if yes.
