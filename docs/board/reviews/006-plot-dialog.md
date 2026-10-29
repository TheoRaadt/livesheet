# Review 006: dialog-based plot configuration (tester, black-box)

Spec: docs/board/specs/006-plot-dialog.md. Commit under test: working tree on top of b862444
(uncommitted: new `livesheet/gui/plotdialog.py`; changed `livesheet/gui/plotregion.py`,
`livesheet/gui/worksheet.py`; developer's own `tests/test_plot_dialog_dev.py`, 51 tests).

Two developer-flagged judgement calls were followed as instructed, not treated as defects:
1. Points-range checking (2-10000, non-integer) happens dialog-side with the exact wording
   "points must be between 2 and 10000", never deferred to the engine (the Edge-cases reading).
2. `attribute_error()`'s known gap: when both X and Y limit/unit fields are filled at once and the
   engine's message does not name an axis, it falls back to the dialog-wide banner (spec's own
   open question 5, accepted). Single-axis-filled cases were checked to still resolve correctly.

## Tests added
`tests/test_plot_dialog_blackbox.py`: 56 cases (55 pass, 1 strict xfail), written independently
from the spec's acceptance criteria and edge cases, using only `PlotDialog`, `PlotFields`,
`compile_plot_fields`, `decompose_plot_text`, `attribute_error` (the names the spec itself calls
out) plus the dialog's own field/button widgets (the same black-box pattern already used by
tests/test_plot_gui.py and the developer's tests/test_plot_dialog_dev.py). Read
tests/test_plot_dialog_dev.py only after writing my own cases, to avoid pointless duplication; the
two files overlap at the level of "which criterion is covered" but use different concrete sheets,
values, and in several places independently cross-check compiled text against literal spec-004
numeric results (nice_axis limits/ticks, trace y-values) rather than only comparing two code paths
against each other.

Coverage: all 31 acceptance criteria, plus: the "Plot here" entry point specifically (not just
`Insert > Plot`/`insert_region`, which the developer's own tests already cover); the real
double-click routing (not only direct `PlotDialog(...)` construction) for a representable region;
the 20-row Add-button cap counted literally (not just a happy-path fill); a scrambled-line-order
decompose -> canonical-order recompile case; both axes' local min>max check (X and Y); non-integer
`points`; the opposite vector/scalar shape-mismatch direction for edge case 26; `Use dialog...`
round trip pre-fill verification; a byte-level comparison of PDF export from the dialog path vs.
the raw-text path (criterion 31); save/reload through an actual `SheetDocument.save`/`load` round
trip (criterion 29) rather than only checking in-memory region state; resize/move/select/delete on
a dialog-created region (criterion 30).

## Results
Full suite (`source ~/livesheet-venv/bin/activate && QT_QPA_PLATFORM=offscreen pytest -q`), run
right after writing and fixing `tests/test_plot_dialog_blackbox.py`:
**866 passed, 3 xfailed, 0 failed.**

Note on the baseline number quoted in my task (804 passed, 6 xfailed): the actual baseline in the
working tree at that point, *before* adding my file, was **811 passed, 2 xfailed** (confirmed by
re-running the suite with `tests/test_plot_dialog_blackbox.py` moved aside). The difference is
accounted for entirely by docs/board/log.md's own record of an unrelated, already-applied fix
("developer -> manager: fixed calculus-coverage defects C1-C4 ... 811 passed, 2 xfailed") that
landed in this same working tree after the 804/6 number was recorded, and before I started —
nothing to do with spec 006. 811 + 55 (mine) = 866 passed; 2 + 1 (mine, D1 below) = 3 xfailed.
`tests/test_plot.py`, `tests/test_document.py`, `tests/test_plot_gui.py` (spec 004's own criteria
1-27) and `tests/test_plot_dialog_dev.py` all still pass unchanged (173 passed, 1 xfailed when run
together with my new file) — spec 004 is confirmed genuinely unaffected, as spec 006 claims.

A further unrelated, concurrent change landed in the same shared working tree while I was
finishing this review (`gui/pretty.py` calculus display notation, per log.md, unrelated to plots);
re-running the full suite once more immediately before filing this review gives **879 passed,
3 xfailed, 0 failed** — the 3 xfails are the same ones listed above (2 pre-existing + my D1), so
nothing changed for spec 006 specifically between the two runs.

## Acceptance criteria

### Trigger and pre-fill
1. PASS. `Insert > Plot`/"Plot here" (tested through `Worksheet.insert_plot_at`, the exact
   function the canvas context menu calls) open the dialog immediately with Function(s) one blank
   row, Variable(s) empty in existing-name mode, every other field blank; Cancel leaves no region.
2. PASS. Double-click (and direct construction) pre-fills existing-name mode, `t`, row `v*t`,
   everything else blank, for criterion-1's text.
3. PASS. Sampling mode pre-fills `x`/`0`/`6.283185307179586`/`5`, row `sin(x)`.
4. PASS. `xlim`/`ylim` pre-fill `2 s`/`8 s`/`0 m`/`40 m`; unit fields stay blank.
5. PASS. `xscale log`, `mode polar`, `style points`, and (an extra case beyond the spec's one
   example) two `over` lines all route double-click to the existing raw editor, unchanged.

### Fields and compile mapping
6. PASS. Compiles to `plot\nover t\nshow v*t`; `region.result.plot` matches criterion 1's x, y,
   units, labels, limits and ticks exactly (checked against the literal spec-004 numbers, not just
   string-compiled text).
7. PASS. Sampling mode compiles to criterion 4's exact text; y matches `sin` of the five sample
   points within 1e-12, `y_limits`/`y_ticks`/`x_label` match.
8. PASS. "Add function" + second row gives two traces, `style_index == 1`, criterion-3 numbers.
9. PASS. Removing a row shifts the remaining rows up and the remaining `show` order (and
   `style_index`) follows on-screen order; checked via the real "Remove" button click, not only the
   private helper.
10. PASS as implemented, with one spec-wording note (not a defect): "Add function" is disabled
    once 20 rows exist and a 21st row can never be added, so criterion 13's 21-trace case is
    genuinely unreachable from the dialog. However, criterion 10's own wording says "disabled once
    20 **non-blank** rows exist", while the "Fields" section says "disabled once 20 rows exist"
    with no non-blank qualifier. The implementation follows the "Fields" section literally: 19
    filled rows plus 1 left blank (20 rows, only 19 non-blank) already disables "Add". This is a
    spec-internal inconsistency, and the implemented reading is defensible (it is the more
    detailed section, and it still guarantees the 21-trace case is unreachable, which is the
    criterion's actual stated purpose) — flagged for the manager, not asserted as a failure.
11. PASS. Full manual limits reproduce criterion 7's `x_limits`/`x_ticks`/`y_limits`/`y_ticks`.
12. PASS. X max only -> `xlim auto to 8 s`, reproduces criterion 8's half-automatic `(0,8)`; both
    blank omits the line entirely (checked directly on `PlotFields`).
13. PASS. `xunit ms` reproduces criterion 2's x-axis conversion (`[0,2000,...,10000]`, label
    `t [ms]`); clearing it back to blank removes the line (re-opening the dialog on the saved
    text and clearing the box).
14. PASS. Title-only adds `title Speed` and nothing else; all three label fields blank omits all
    three lines (checked directly on `PlotFields`). Also checked: decompose tolerates any input
    line order, but compile always reorders to the fixed canonical order.

### OK / Cancel / Apply
15. PASS. Apply writes and re-evaluates while the dialog stays open (`dlg.result() == 0`,
    i.e. neither Accepted nor Rejected); a subsequent OK with no further field change makes no
    further change to `region.source`/the plot data beyond closing the dialog (`Accepted`).
16. PASS. Cancel on a brand-new region discards it even after a successful Apply during the
    session; no `plot`-kind region remains in `to_document()`.
17. PASS. Cancel on an existing, previously-saved valid plot, after edits and an Apply, reverts
    `RegionData.text` to exactly the pre-dialog saved text; region stays in the sheet.
18. PASS. Two otherwise-identical sessions (Apply-then-OK vs. OK directly) give the same
    `region.source` and the same resulting trace values.

### Errors
19. PASS. `Y` (undefined) in a function row -> `Y is not defined` at that row; dialog stays open
    (`dlg.result() == 0`); region unchanged.
20. PASS. Two rows with different units -> `different units` as the dialog-wide banner, not at
    either row; region's text is left untouched (the failed Apply/OK never wrote it).
21. PASS. Blank Variable(s) with a filled function row -> "Variable(s) is required" at that field,
    `region.source` stays `""` (proves the engine's own `over`-missing error was never produced).
22. PASS. X min `5 m` on a seconds axis -> "Units do not match..." at the X min/max field, banner
    stays empty.
    Additional check (manager-accepted gap, not a defect): X min `5 m` *and* Y min `2 kg` both
    wrong at once -> neither field shows an error, the message goes to the dialog-wide banner
    instead, exactly as the spec's accepted open question 5 describes.
23. PASS. X min `8 s` > X max `2 s` -> "lower limit must be below upper limit" at the X field,
    caught locally (`region.source` stays `""`, confirming no engine call). Also checked the Y
    axis direction (not in the spec's own example): same local message at the Y field.
    Points out of range (`10001`) and non-integer points (`3.5`) both give the dialog's own exact
    "points must be between 2 and 10000" message with no engine call (the Edge-cases reading,
    per the developer's flagged judgement call 1).

### Raw-text fallback
24. PASS. "Edit as text..." on a brand-new region opens the raw editor with `STARTER_TEXT`; on a
    filled-but-not-yet-Applied region it opens with the *current* (unsaved) compiled text, not the
    last-saved text.
25. PASS. "Use dialog..." from the raw editor, when representable, closes the raw editor and opens
    `PlotDialog` pre-filled exactly as double-click would (checked via the real control click with
    `PlotDialog.exec` mocked, not just by calling the underlying check function); when not
    representable, the control is disabled and carries a non-empty tooltip explaining why.

### Edge cases as acceptance criteria
26. PASS. Switching Variable(s) from a vector (`X`, with row `Y`, a vector — valid) to a range
    variable (`t`) leaves the stale row untouched until the next OK/Apply, which then correctly
    surfaces the engine's "show 'Y' needs a single value" at that row; `region.source` is left
    unchanged by the failed attempt. The opposite direction (range mode with a plain-constant row,
    switched to vector mode) correctly surfaces "needs a vector" at the row.
27. PASS. `_FunctionEdit` shows an elided version while unfocused, the full text while focused
    (restored exactly), and elides again on blur; the underlying value itself is never truncated.
    (Native scrolling-while-editing and never-wraps are inherent to a single-line `QLineEdit`
    subclass and were not separately re-tested beyond this.)
28. PARTIAL — see Defect D1 below. The "existing region" half (OK refused with "At least one
    function is required", region/dialog otherwise unchanged) is correctly implemented, checked
    both for a fully-removed row and a present-but-blanked row. The "brand-new region" half (OK
    with an empty Function(s) list should act exactly like Cancel, i.e. silently discard) is not
    implemented: see D1.

### Save/reload and regression
29. PASS. A dialog-created, dialog-resized plot round-trips through an actual
    `SheetDocument.save()`/`SheetDocument.load()` (not just in-memory state): text, `w`, `h` all
    preserved; re-opening the reloaded region in the dialog pre-fills correctly, confirming which
    editing surface it opens into is re-derived from text, not stored.
30. PASS. `set_size` clamping, `setPos`, selection and `remove_regions` on a dialog-created region
    all behave the same as any other `PlotRegion` (spec 004 criteria 25-26 are not re-tested in
    full here since they are untouched code; only the dialog-created-region angle was added).
31. PASS. PDF export from the dialog-created plot and the same plot configured via raw text are
    byte-identical apart from a handful of bytes confined to Qt's own randomly-generated per-export
    `/DocumentID` metadata (confirmed by direct byte-diff inspection); same total length. A second
    check confirms merely constructing a `PlotDialog` (never shown/exec'd) does not change the
    export at all.

## Defects

**D1 (criterion 28, brand-new region half) — moderate.** Spec: "Clicking OK with an empty
Function(s) list ... for a brand-new region this is simply Cancel's discard behaviour ... since
nothing valid was ever applied." Actual: `PlotDialog.accept()` calls `_commit()`, which runs
`_validate_local()` unconditionally regardless of `_is_new_session`; with an empty/blank
Function(s) list this always sets "At least one function is required" (and typically also
"Variable(s) is required") and returns `False`, so `accept()` does nothing further — the dialog
stays open (not closed), its own validation errors visible, and the blank region remains on the
canvas. There is no special case anywhere in `_commit`/`accept` for "brand-new session and fields
blank -> discard like Cancel".

Minimal repro (headless, `QT_QPA_PLATFORM=offscreen`):
```python
sheet = Worksheet()
region = sheet.add_region("plot", QPointF(0, 0), "")   # brand new, nothing applied yet
dlg = PlotDialog(region, sheet)                          # default state: one blank row
dlg.ok_btn.click()
# Expected (spec criterion 28): region discarded, dialog closed, like Cancel.
# Actual: region is still in sheet.regions(); dlg.functions_error_label.text()
#         == "At least one function is required"; dialog not closed (dlg.result() == 0).
```
Reproduced in `tests/test_plot_dialog_blackbox.py::test_ok_with_empty_function_list_on_brand_new_region_discards_it_criterion_28`
(marked `xfail(strict=True)` so the suite stays green; remove the marker once fixed).

Not a blocker for the dialog's core workflow (a user who fills in nothing and clicks OK simply
sees a sensible validation message rather than a silent discard — arguably not confusing in
practice — but it does not match the spec's explicit instruction, and a developer fix is a small,
localized change: special-case `_is_new_session and _fields_blank(fields)` in `accept()`/`_commit()`
to behave like `reject()` before running `_validate_local`).

## Observations (not defects, judgement calls already accepted)
- Dialog-side `points` check and the exact wording, per the developer's flagged judgement call 1:
  confirmed working, no engine call made.
- `attribute_error()`'s both-axes-filled-ambiguous-message gap, per judgement call 2 / spec open
  question 5: confirmed falls back to the banner as expected; single-axis cases resolve correctly.
- Criterion 10's "20 non-blank rows" vs. the "Fields" section's "20 rows" (no qualifier): see
  above, a spec-internal wording inconsistency, not a code defect; worth a one-line clarification
  in the spec or a manager decision on which reading to keep, but does not block merging.

## Coverage gaps
- **No computer-use/real-display session this run**: all testing was headless
  (`QT_QPA_PLATFORM=offscreen`), as the environment available to the tester for this task did not
  include an interactive display tool. Per the spec's own "Fits current architecture?" section,
  Theo should still do a manual pass on the real app covering: `Insert > Plot` opening the dialog
  (menu and canvas "Plot here"); filling/Applying/OK on a fresh plot and watching the chart update
  live beside/behind the dialog; double-clicking both a representable and a non-representable
  existing plot; add/remove function rows via mouse; the unit and limit fields; Cancel on both a
  new and an existing plot; the error banner and per-field messages appearing where expected;
  the "Edit as text..."/"Use dialog..." round trip; save and reload. This is the same gap flagged
  for spec 004's own GUI pass previously (docs/board/reviews/004-plots.md) and still open.
- Keyboard-only interaction (Tab order across fields/buttons, as the spec's edge cases describe
  "nothing bespoke, uses the toolkit's normal Tab order") was not exercised; this is Qt's own
  default behaviour and was not separately simulated.
- Scrolling behaviour for more rows than fit the dialog's visible height (the spec's edge case
  about ordinary host-toolkit scrolling) was not exercised; `QScrollArea` is standard Qt chrome.
- Mouse-drag resizing through the actual resize handle (hit-testing `handle_rect()`) on a
  dialog-created region was not simulated; `set_size()` was called directly (same code path, per
  the spec-004 review's own prior note on this).
- The elide behaviour's "scrolls to keep the caret visible while editing" half was not verified
  beyond confirming the full text is shown while focused; the scroll mechanics are native
  `QLineEdit` behaviour once the full text is restored, not bespoke code.

## IP red flags
None observed. All field labels, button wording ("Add function", "Remove", "Use existing",
"Sample a new range", "Edit as text...", "Use dialog...", "Variable(s) is required", "At least one
function is required", "lower limit must be below upper limit", "points must be between 2 and
10000"), group box titles, and the `PlotDialog`/`PlotFields`/`compile_plot_fields`/
`decompose_plot_text`/`attribute_error` names are original, generic UI/engineering wording,
consistent with the spec's own IP check. No vendor names, help text, keyboard-shortcut schemes, or
file-format strings found in `livesheet/gui/plotdialog.py` or the touched parts of
`livesheet/gui/plotregion.py`/`livesheet/gui/worksheet.py`. The dialog pattern itself (modal form,
OK/Cancel/Apply, add/remove list) is the generic chrome the spec's own IP check already assessed;
nothing in the implementation goes beyond what the spec described.

## Recommendation
Spec 006 is close to ready to merge: 30 of 31 acceptance criteria hold exactly as specified under
black-box testing, spec 004 is confirmed genuinely unaffected (same test files, same results), and
the two developer-flagged judgement calls behave as accepted. One real defect (D1, criterion 28's
brand-new-region discard behaviour) should go back to the developer before merging — it is a
small, localized fix with a clear minimal repro and an xfail test already in place to confirm the
fix. The criterion-10-wording note is worth a one-line manager/spec clarification but is not a
merge blocker. A real-window manual pass by Theo (listed in Coverage gaps) is still needed before
calling phase D1+D2 fully done, per the project's own testing rule.
