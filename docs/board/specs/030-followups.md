# 030 Follow-ups: dataset names in autocomplete (backlog 67) and an evaluation-order hint

Two small, independent items. Each is shippable alone, in either order. Both are engine-first with
a thin GUI part.

Source inspiration: generic, cross-application conventions only.
- A: type-ahead lists offer every name the user could legitimately type at that point (the idea
  spec 024 already uses; W3C WAI-ARIA Authoring Practices, combobox with list autocomplete,
  https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-autocomplete-list/,
  2026-11-12, concept only). Candidates that stop existing must stop being offered.
- B: the general UX-writing rule "an error says what happened and what to do next", and the
  familiar "used before it is defined" diagnostic found in spreadsheets, scripting languages and
  compilers. Idea only; no product's wording, help text or UI was consulted. Own prior material:
  specs 024 and 028, docs/manual/errors.md, docs/STATUS.md open item 4.

## Current state (read from the code, 2026-11-12)
- `livesheet/engine/completion.py` (Qt-free): `complete(text, caret, user_sources)` ranks
  `(exact-case prefix first, user-defined before builtin, shorter name, alphabetical)`. Kinds today:
  function, constant, user_function, variable. `accept()` appends `(` only for function and
  user_function.
- `livesheet/gui/regions.py: MathRegion._other_sources()` supplies the other regions' sources and
  `refresh_popup()` calls `completion.complete(text, caret, self._other_sources())` on every typed
  key, with no cache. `livesheet/gui/completion_popup.py` draws `Candidate.name`,
  `Candidate.signature` and a tag from `KIND_TAGS = {"constant": "const", "variable": "var",
  "user_function": "user"}`.
- Datasets (spec 028) live in `Worksheet.datasets` (list of `dataio.Dataset`), changed only by add /
  remove / rename / refresh / load (`datasetsChanged` signal). `dataio.variable_names(dataset)` is a
  cheap, evaluation-free set of the variable names a dataset defines: `<dataset>_<column>` per
  `number` column, plus `<dataset>` only when `combined_matrix_available`. Text columns define
  nothing. Dataset names cannot equal a builtin, unit or constant name (028), and a region may not
  redefine a dataset variable (028 evaluator error).
- "not defined" errors come from `evaluator.py` (`_check_defined`, `_check_bare_units`) and two
  smaller sites in `statistics.py` and `matrices.py`; the text always has the exact form
  `<name> is not defined` or `<n1>, <n2> are not defined` (alphabetical). `Engine.evaluate()`
  receives regions already in evaluation order (left to right, then top to bottom per page); global
  (`≡`) definitions run in pass 1 for every region, everything else in pass 2 in order.

---------------------------------------------------------------------------------------------

# Part A. Dataset variables in name autocomplete (backlog 67)

User story: after importing `run1.csv` I type `ru` in a formula and see `run1`, `run1_t`, `run1_F`
offered, so I do not have to open the Data tab or remember exact column names.

## Behaviour (own words)

### Candidates
- For every dataset on the sheet the candidates are exactly `dataio.variable_names(dataset)`: one
  per `number` column and `<dataset>` only when the combined matrix exists. Text columns are never
  offered; a dataset without a combined matrix does not offer its bare name. The set is always what
  the evaluator would seed because it comes from the same function, never from a second naming rule.
- New candidate kind `data`, popup tag `data`. Accepting inserts the name only, never a paren
  (vectors and matrices are not called); `accept()` needs no change because `data` is not a
  function kind.
- Hint (muted string, stored in `Candidate.signature`):
  - column: `<n> values`, followed by `, <unit>` when the column has a unit, e.g. `4 values, N`
    (the unit text as stored on the column).
  - combined matrix: `<n> x <k> matrix`, e.g. `4 x 2 matrix`.

### How candidates are supplied
- Engine (Qt-free): `completion.dataset_candidates(datasets: Iterable[dataio.Dataset]) ->
  list[Candidate]`, built only from `dataio.variable_names` and column metadata. It must not call
  `dataset_variables` (that builds symbolic matrices; too slow per keystroke).
- `completion.complete(text, caret, user_sources=(), datasets=())` gains the optional keyword
  `datasets` (default empty, so every existing caller and test is unaffected). Importing `dataio`
  into `completion.py` is fine (Qt-free); `PySide6` must still not be imported.
- GUI: `MathRegion.refresh_popup` passes the scene's live `datasets` list (`getattr(scene,
  "datasets", ())`) on every refresh. No snapshot or cache in the GUI or the engine between
  keystrokes; that is what makes removal and rename take effect at once, with nothing to invalidate.

### Ordering
New sort key: `(exact-case prefix first, group, length, name)`, group 0 = names defined by the
sheet's regions (variable, user_function), group 1 = dataset names, group 2 = builtins. Within a
group: shorter first, then plain string (code-point) order as today, so `run1_F` sorts before
`run1_t`. Consequences: `run1` before `run1_F` and `run1_t`; a user variable before a dataset
column that matches the same prefix; dataset names before builtins.
- Clash: if a region's definition has the same name as a dataset variable (possible only while that
  region shows the 028 "cannot be redefined" error) the dataset entry wins and the name appears once.
  A dataset candidate also replaces a builtin entry of the same name (defensive; 028 forbids it).
- All other spec 024 popup rules apply unchanged (2-character minimum, no popup when the only match
  is the exact typed name, number context, etc.).

### Disappearance
Candidates are recomputed from the live list at each refresh:
- Remove a dataset: its names are not offered from the next keystroke.
- Rename `run1` to `trial`: `run1*` names vanish, `trial*` names appear (formulas are not rewritten,
  as in 028).
- Refresh from file that drops a column or changes units: names and the unit hint follow the new data.
- Opening another file replaces `Worksheet.datasets`; the old sheet's names vanish.
- An already open popup need not refresh live: dataset changes go through dialogs or tab buttons,
  which close the popup by focus loss (spec 024 closing events). The next typed key shows the
  current state.

### Display
Same row layout, colour tokens, width and elision rules as spec 024; only the new `data` tag.

## Syntax proposal
None. No .lsheet format impact (nothing stored).

## Acceptance criteria (A)
Fixtures: `run1` read from `t [s],F [N]\n0,1.0\n1,3.0\n2,5.0\n3,7.0` (via `read_table_text`, named
`run1`; columns `t` unit `s`, `F` unit `N`, so units differ and there is NO combined matrix `run1`);
`run2` from `a [N],b [N]\n1,2\n3,4` (same units, combined matrix exists). Corrected accordingly
below.

Engine tests (no Qt):
A1. Names: `{c.name for c in dataset_candidates([run1])} == {"run1_t", "run1_F"}` (no bare `run1`,
    units differ); for `run2` the set is `{"run2_a", "run2_b", "run2"}`. Each equals
    `dataio.variable_names(dataset)`. All have kind `data`.
A2. Hints: `run1_F` signature contains `4 values` and `N`; `run2` signature is `2 x 2 matrix`;
    a unitless column's signature is exactly `<n> values` with no trailing comma or space.
A3. Text column: a dataset `q` from `name,v\nab,1\ncd,2` offers `q_v` and `q`, never `q_name`.
A4. Order: `[c.name for c in complete("ru", 2, datasets=[run1]).candidates]` equals `["run1_F",
    "run1_t"]`. With `datasets=[run2]` and prefix `ru`: `["run2", "run2_a", "run2_b"]` for prefix
    `ru` (the bare name first, shorter). `complete("run2_", 5, datasets=[run2])` names are
    `["run2_a", "run2_b"]`. `complete("run1_t", 6, datasets=[run1])` is None (nothing left).
A5. Groups: sources `["rate := 3"]`, dataset `rab` (one numeric column `u`, so names `rab_u`, `rab`),
    and a monkeypatched builtin `BUILTINS["raz"] = lambda x: x` (as in 024 E1):
    `[c.name for c in complete("ra", 2, ["rate := 3"], [rab]).candidates]` starts with `rate`
    (variable), then `rab`, `rab_u` (dataset), then `raz` (builtin); the probe entry is removed
    after the test.
A6. Exact-case first: with datasets `[run1, Run2x]` (`Run2x` having a column `v`),
    `complete("Ru", 2, datasets=...)` lists `Run2x` (exact case) before `run1_F`.
A7. Vanishing: with `ds = [run1]` (the same list object passed each time), `complete("ru", 2,
    datasets=ds)` is not None; after `ds.remove(run1)` it is None. After replacing it with a renamed
    copy named `trial`: `complete("ru", 2, datasets=ds)` is None and `complete("tri", 3, datasets=ds)`
    lists `trial_F`, `trial_t`.
A8. Default unaffected: all spec 024 E-tests pass unchanged; `PySide6` is absent from
    `sys.modules` after importing `livesheet.engine.completion` in a fresh interpreter.
A9. Accept: `accept("m = mean(ru", 11, <run1_F candidate>)` returns `("m = mean(run1_F", 15)` (no
    paren for kind `data`).
A10. Clash: sources `["run1_t := 5"]` with dataset `run1`: `complete("run1_", 5, [..], [run1])`
     lists `run1_t` once, kind `data`.

GUI tests (offscreen; key events through `region.editor.keyPressEvent`, as the 024 G-block):
A11. After adding `run1` through the worksheet's public add-dataset API (the one 028 D2 uses),
     typing `ru` in a new region opens the popup with `candidates() == ["run1_F", "run1_t"]`; Tab
     makes the source `run1_F`; the region stays in editing mode.
A12. After removing `run1` through the public remove API, typing `ru` in a fresh edit opens no
     popup. After renaming to `trial`, `ru` opens none and `tri` offers `trial_F`, `trial_t`.
A13. A sheet with a dataset, saved and reopened without the CSV present, offers the same names.
A14. A TextRegion still never shows the popup (024 G12 stays green).

## Edge cases (A)
- Many datasets or 100 columns each: plain string building from metadata per keystroke; far below
  the 300 ms threshold; the 8-row scrolling window already handles long lists.
- Names with digits/underscores (`run1_2`) are handled by the 024 identifier-run rule.
- A column named like a unit (`m`) gives `ds_m`; no clash.
- Plot-spec editors do not show the popup (024 rule 5 unchanged).

## IP check (A): pass
Same ubiquitous prefix-completion convention as spec 024; the extra names come from LiveSheet's own
dataset model; hint strings are own wording; generic list chrome, nothing drawn on a chart or live
on the canvas (ip-cleanroom rule 6 posture unchanged). No new dependency. Open IP question: none.

## Fits current architecture? (A)
Yes. `livesheet/engine/completion.py`: `dataset_candidates` plus the optional `datasets` keyword
(imports `dataio`, Qt-free). `livesheet/gui/regions.py: refresh_popup` passes the scene's
`datasets`. `livesheet/gui/completion_popup.py`: add `"data": "data"` to `KIND_TAGS`. No change in
document.py, dataio.py, evaluator.py.

---------------------------------------------------------------------------------------------

# Part B. Evaluation-order hint on "is not defined"

User story: I wrote `y := 2*x =` and put `x := 4` to its right or lower on the page. I get "x is not
defined" although `x` exists on the sheet. The message should say the definition is there but comes
too late.

## Behaviour (own words)

### When the hint appears
A region's final error text is exactly the existing "not defined" form (singular `<name> is not
defined`, plural `<n1>, <n2> are not defined`) AND at least one listed name is defined by a LATER
region in evaluation order (to the right on the same row, or below) through an ordinary
(non-global) definition. Then the hint is added. In every other case the message is byte-for-byte
what it is today.

"Defined by a later region": a region further along the list given to `Engine.evaluate` whose
parsed statement is a non-global `define` (variable, or function with parameters) or non-global
`range` that names it. Exclusions:
- Global definitions (`≡`) are visible everywhere (pass 1): never an ordering error, never hinted.
- Dataset variables, units and builtins are seeded up front and are never "later".
- A name defined by the very region that uses it (`x := x + 1`) is not "later"; the hint needs a
  different, strictly later region.
- A name defined only EARLIER (that definition failed, so the use inherits "not defined") gets no
  hint: the order is fine and the earlier region carries the real error.
- A name defined nowhere (a typo) gets no hint.
- Evaluate-only lines (`total =`) and model/solve/plot argument names define nothing.

### Wording (fixed string so tests can match)
Appended to the existing text after a full stop and one space, one sentence:

`<existing message>. A definition must come before its use (left to right, then top to bottom); defined later: <names>.`

`<names>` = the base message's listed names that are defined later, sorted by plain string order,
separated by `, `. Examples:
- `x is not defined. A definition must come before its use (left to right, then top to bottom); defined later: x.`
- `q, x are not defined. A definition must come before its use (left to right, then top to bottom); defined later: x.`
Constraints:
1. The original message stays an unmodified prefix (everything before `. A definition`), so every
   existing `startswith`/substring assertion keeps passing; is/are is chosen from the number of
   undefined names, not from the number of hinted names.
2. Exactly one hint sentence per message; a message already carrying it is never extended again.
3. Plain ASCII English, one line, no trailing space, no region numbers or coordinates.
4. Names are raw identifiers as typed (not pretty glyphs), same as the base message.
5. The hint is part of `RegionResult.error`; the GUI shows it wherever it shows that error today.

### Where it applies
Every path that ends in the exact anchored text above on a region result, whichever function raised
it (`_check_defined`, `_check_bare_units`, the sites in `statistics.py`/`matrices.py`, formula-tab
inserts, plot function rows, matrix cell expressions, model lines). Mechanism is the developer's
choice; the preferred one is a single post-step in `Engine.evaluate` that sees each region's final
error text and a precomputed map `name -> position of its non-global definition`, applied only when
the text fully matches `^<ident>(, <ident>)* (is|are) not defined$`, so a message with extra wording
can never be changed by accident. A dependent line that inherits another region's error is treated
like any other: hinted only if the name is defined later than the using region.

"To the right" and "below" are the same test, because the engine sees one ordered list; the text
says "left to right, then top to bottom" to match the manual's description of order. Page order
follows the same list.

## Error-reference update (docs/manual/errors.md, done by the documenter after acceptance)
- Add one short section, "The 'defined later' hint", next to the first `is not defined` entry of the
  general math section: the exact shipped sentence (copied from the shipped code or test, character
  for character), a two-region worked example (`y := 2*x =` left of or above `x := 4`, the hint, and
  the fix: move `x := 4` up or to the left, or make it global with `≡`), the note that global
  definitions need no ordering, and pointers to docs/manual/moving-regions.md and pages.md.
- In every other table row that documents `<name> is not defined`, add to the cause cell: "If the
  name is defined further along, the message continues with the 'defined later' hint (see above)."
  Do not repeat the full sentence in each row.
- docs/STATUS.md open item 4 loses the evaluation-order clause when this ships.

## Syntax proposal
None. No .lsheet impact (computed at evaluation time, never stored).

## Acceptance criteria (B)
Engine tests via `Engine().evaluate([(key, source), ...])`, keys in the order listed. `H(names)` below
means the string `. A definition must come before its use (left to right, then top to bottom); defined later: ` + names + `.`
B1. `[("a", "y := 2*x ="), ("b", "x := 4")]`: result `a` is an error exactly `x is not defined` + `H("x")`;
    `b` is ok.
B2. Order fixed: `[("b", "x := 4"), ("a", "y := 2*x =")]`: `a` ok, value 8, no error.
B3. Typo: `[("a", "y = 2*q"), ("b", "x := 4")]`: `a` error is exactly `q is not defined` (no hint).
B4. Mixed: `[("a", "z := x + y + q ="), ("b", "x := 1"), ("c", "y := 2")]`: `a` error is exactly
    `q, x, y are not defined` + `H("x, y")`.
B5. Self reference: `[("a", "x := x + 1")]`: error `x is not defined`, no hint.
B6. Global: `[("a", "y := 2*x ="), ("b", "x ≡ 4")]`: `a` ok, value 8 (existing pass-1 behaviour), no error.
B7. Earlier failing definition: `[("a", "y := 2*x ="), ("b", "x := 4"), ("c", "y =")]`: `a` error is
    `x is not defined` + `H("x")`; `c` error carries no hint (`y` and `x` are both defined earlier than `c`; the exact base text
    of `c` is whatever the engine gives, as `y` is stored lazily).
B8. Function defined later: `[("a", "f(2) ="), ("b", "f(u) := u^2")]`: `a` error is
    `f is not defined` + `H("f")`.
B9. Range variable defined later: the same shape as B1 with the repo's real range-definition syntax
    for `x` in region `b` (the test copies the form from an existing range-variable test); `a`'s
    error is `x is not defined` + `H("x")`, or that region's existing range-use error if the use
    form differs (test adjusts to the form that currently yields "x is not defined" without the
    definition).
B10. Bare-unit path: `[("a", "F/A ="), ("b", "F := 10 N"), ("c", "A := 2 m^2")]`: the base message is
    whatever the engine gives today for `a` (the first bare name, `F is not defined`); the hint
    lists only names that appear in that base message: `F is not defined` + `H("F")`.
B11. Plural both later: `[("a", "z := x + y ="), ("b", "x := 1"), ("c", "y := 2")]`: `a` error is
    `x, y are not defined` + `H("x, y")`.
B12. Dataset and unit names are never "later": with dataset `run1` passed to `evaluate`,
    `mean(run1_t) =` is ok; without it the error is `run1_t is not defined`, no hint, even when a
    later region reads `run1_t`.
B13. No double hint: feeding a result's own error text back through the post-step does not append
    a second hint (unit test on the helper if one exists).
B14. Regression: the whole existing suite is green. Existing tests that compare a "not defined"
    message for equality in a case that now gains a hint are updated by the developer and listed in
    the log line.
GUI (offscreen):
B15. A worksheet with the B1 layout shows the hint text in the region's error display (the
     existing accessor for the error text contains `defined later: x`). Moving the `x := 4`
     region above the user (spec 023 move API) removes the error on the next recalculation.

## Edge cases (B)
- Message length: the hint adds about 90 characters. The developer checks how the error display
  copes on a narrow region (wrap, elide or clip); if it clips without a tooltip, the full text is
  also made available as a tooltip (small GUI follow-up). Open question 2.
- Messages that wrap the base text with extra words are left untouched (anchored match).
- English only, like every engine message. One linear pass over already parsed statements; no
  extra parse or evaluation.

## IP check (B): pass
"Used before it is defined" is a generic diagnostic in compilers, scripting languages and
spreadsheets; the sentence is own wording tied to LiveSheet's own evaluation-order rule (CLAUDE.md,
manual). No vendor message text, help text or terminology was consulted. Pure text; no interaction
style or on-canvas technique; no patent-sensitive element. Open IP question: none.

## Fits current architecture? (B)
Yes, engine only: `livesheet/engine/evaluator.py: Engine.evaluate` post-processes each region's final
error using the already parsed `statements` and their positions. No change to `syntax.py`; the
message producers in `statistics.py` and `matrices.py` stay as they are. GUI: only the tooltip check
in the edge cases. Docs: errors.md by the documenter after acceptance.

---------------------------------------------------------------------------------------------

## Open questions (for the manager / Theo)
1. Part B: should the hint also say where the later definition is ("to the right" vs "below")? The
   engine sees only order, not geometry. Default: no, purely order based.
2. Part B: the longer text may be clipped by the current error display; accept a tooltip follow-up
   by the developer if so? (Testers here lack computer use; the real window needs a manual check.)
3. Part A: unit in the hint (`4 values, N`) as specified, or counts only? Default: with unit.
4. Part A: ordering user variables, then dataset names, then builtins (as specified), or datasets
   ahead of the user's variables? Default as specified.
5. Housekeeping on acceptance: mark backlog 67 DONE and remove the evaluation-order clause from
   STATUS open item 4.
