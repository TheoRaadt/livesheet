# Review 008: dialog-based vector/matrix insertion (tester, black-box)

Spec: docs/board/specs/008-matrix-dialog.md. Commit under test: working tree on top of b862444
(uncommitted: new `livesheet/gui/matrixdialog.py`; changed `livesheet/gui/worksheet.py`,
`livesheet/gui/main_window.py`; developer's own `tests/test_matrix_dialog.py`, 60 tests).

## Pre-existing blocking defect found and fixed in my own test file (not production code)

This review picks up an already-written, uncommitted `tests/test_matrix_dialog_blackbox.py` from
an earlier, interrupted tester session (it already covered all 25 criteria plus edge cases). Before
anything else could be trusted, one bug in that file had to be fixed: three tests
(`..._criterion_1`, `..._criterion_3`, `..._criterion_6`) drove the real
`Worksheet.contextMenuEvent` and tried to intercept its real `menu.exec(event.screenPos())` call
via `mock.patch.object(QMenu, "exec", <fake>)`. That patch does not take effect: `QMenu.exec` is a
Shiboken/C++-backed method, and calling `menu.exec(...)` on a live instance still runs the real,
blocking modal loop even though `QMenu.exec` shows the patched Python function when inspected on
the class directly (confirmed independently with a minimal repro script, isolated from this
project's code, before touching the test file). This is unlike patching `exec` on a pure-Python
`QDialog` subclass such as `MatrixDialog` (used throughout this file and the rest of the suite
successfully) — that is a normal Python MRO override on a class this project defines, and works as
expected; `QMenu` is not such a class.

Fix (test-file only, `tests/test_matrix_dialog_blackbox.py`): replaced the `QMenu.exec` patch with
a `QTimer.singleShot(0, ...)` scheduled *before* the real `menu.exec()` call. The scheduled
callback fires once `menu.exec()`'s own nested event loop starts, finds the live popup via
`QApplication.activePopupWidget()`, and either (a) selects the action matching the wanted visible
text with `QMenu.setActiveAction` and activates it with a real `QTest.keyClick(...,
Qt.Key.Key_Enter)`, so the real `exec()` call returns that actual `QAction`, or (b) for the
"no such entry should exist" case, records the popup's own current action labels and dismisses it
with `QTest.keyClick(..., Qt.Key.Key_Escape)`. Verified this mechanism independently (minimal
script, not project code) before applying it: `menu.exec()` returns the real selected action, no
hang, and the alternate dismiss-path returns `None` with the labels correctly captured. This still
exercises the actual `contextMenuEvent` menu-construction/dispatch code (a real popup is opened,
the real menu's real actions are inspected and really activated/dismissed through Qt's own event
handling) — it does not weaken what criteria 1/3/6 are proving, it only changes how the test
synchronizes with the modal call instead of shortcutting around it.

Confirmed fixed: `QT_QPA_PLATFORM=offscreen pytest -q` (the project's own documented command, no
`--timeout` needed) now completes normally. Ran the full suite four times in a row to be sure:
three runs gave a clean **1063 passed, 2 xfailed** in ~14s each; one run crashed with a fatal
`QApplication`-construction abort inside the unrelated `tests/test_gui.py::app` fixture partway
through (not in my file, not reproducible on three immediate re-runs under otherwise-identical
conditions) — logged under Coverage gaps/Observations below as probable environment contention
(this sandbox may run more than one PySide6/`QT_QPA_PLATFORM=offscreen` process concurrently across
agents), not a defect in this spec or this test file.

No production code was touched to fix this (`livesheet/gui/worksheet.py`'s `contextMenuEvent`,
`livesheet/document.py`, `livesheet/engine/wiring.py`, `livesheet/gui/componentdialog.py` are all
untouched by me, per instruction — those areas were left for a developer fixing unrelated
regressions in parallel).

## Tests added/finished
`tests/test_matrix_dialog_blackbox.py`: 43 collected test items (all pass), written independently
from spec 008's own acceptance criteria 1-25 and edge cases, using only the names the spec itself
calls out (`MatrixDialog`, `MatrixFields`, `compile_matrix_fields`, `decompose_matrix_text`,
`validate_matrix_fields`, plus `cell_has_separator` for the separator-check criterion). Written
independently of the developer's own `tests/test_matrix_dialog.py` (60 tests); that file was only
read afterwards (by the earlier tester session, per its own docstring, and again by me just now)
to check for coverage gaps, not consulted while drafting these cases.

Deliberately different exercise paths vs. the developer's own tests (per the file's docstring):
- Criteria 1/3/6 go through the real `Worksheet.contextMenuEvent`, with a real (now correctly
  synchronized, not patched) `QMenu.exec()` call, rather than calling
  `insert_matrix_at`/`_open_matrix_dialog` directly.
- The `&Matrix…`/`Ctrl+Shift+M` `Insert` menu entry is exercised through a real `MainWindow` and a
  real `QAction.trigger()`, not a direct helper call.
- Criterion 17's accepted judgement call (region committed via `start_editing()`/`finish_editing()`
  rather than a direct `region.source` set, per `docs/board/decisions.md` 2026-10-29) is checked at
  the level that decision actually cares about: the on-screen *pretty* HTML refreshes immediately,
  cross-checked byte-for-byte against an equivalent direct text edit.

Coverage: all 25 acceptance criteria, plus: the real "Matrix here"/"Edit as grid..." canvas
context-menu wiring (not just `insert_matrix_at`/`_open_matrix_dialog` called directly); the real
`&Matrix…` `Insert`-menu `QAction` and its shortcut; Add-column/Remove-row reshaping tracked
through the live grid widgets; row-vector/column-vector/1x1 compile shapes; Cancel at either step
for a brand-new insertion; OK vs. a byte-identical direct-typing round trip (new insertion and
existing-region update, both cross-checked at the `region.editor.toHtml()` level, not just
`region.source`); all three dialog-side validation messages at their exact stated location; the
undefined-symbol-on-commit and mismatched-display-unit-on-commit error paths, cross-checked against
an equivalent directly-typed region; "Edit as text" for both a brand-new insertion (behaves like
Cancel) and an existing region (discards in-dialog changes, opens the real inline editor); the
absence of a reciprocal "Use dialog..." control; save/reload byte-for-byte identity against direct
typing; move/select/single-owner-delete on a dialog-created region; the 1x20/20x1/20x20 grid-size
bounds (including the add/remove button enablement at both ends); going back from Grid to Size and
both growing (keeps+blanks) and shrinking (drops) cells; malformed-cell-expression and
nested-bracket-cell deferral to commit-time engine errors; the three "combined with another
operator" non-representable shapes; the dialog's own no-name-collision-check design choice; and two
further non-representable edge cases (`[]`, jagged rows) not explicitly named in the spec text.

## Results
Full suite (`QT_QPA_PLATFORM=offscreen pytest -q`), run immediately after finishing and fixing
`tests/test_matrix_dialog_blackbox.py`: **1063 passed, 2 xfailed, 0 failed** (stable across three
consecutive runs; see the transient fourth-run crash noted above and under Observations). The 2
xfails are pre-existing and unrelated to spec 008 (not touched by this review).
`tests/test_matrix_dialog.py` (the developer's own 60 tests) and all other existing suites pass
unchanged in the same run — spec 008 is confirmed not to regress anything else.

## Acceptance criteria

### Trigger and pre-fill
1. PASS. `Insert > Matrix`/"Matrix here" (checked through both the real canvas context menu and a
   real `MainWindow`/`QAction.trigger()`) open the Size step at Rows=2/Columns=2; Cancel creates no
   region.
2. PASS. Rows=3/Columns=1 + Next opens a 3x1 grid of blank cells, Name "No name", Show "Don't show
   a result", Scale/unit blank.
3. PASS. Right-clicking `A := [1, 2; 3, 4]` shows "Edit as grid..." (via the real context menu);
   choosing it pre-fills Name "Define as" `A` (`:=`), grid `1,2,3,4` row-major, Scale/unit blank,
   Show "Don't show a result".
4. PASS. `A := [1, 2; 3, 4] =` additionally pre-fills Show "Show numeric result (=)" with a blank
   display-unit box.
5. PASS. `K := [2, -1; -1, 2]*N/m` pre-fills Name `K`, grid `2,-1,-1,2`, Scale/unit `N/m`, Show
   "Don't show a result".
6. PASS. `A + [1, 2, 3; 4, 5, 6]` (two terms) shows no "Edit as grid..." entry via the real context
   menu; double-click still starts ordinary inline editing unchanged.
7. PASS. `M := [a, b; c, d]` pre-fills grid cells `a, b, c, d` as plain text.

### Fields and compile mapping
8. PASS. 2x2 grid `1,2,3,4`, no name, no show, no scale compiles to exactly `[1, 2; 3, 4]`.
9. PASS. Same grid, Name "Define as" `A` (`:=`), Show numeric compiles to `A := [1, 2; 3, 4] =`.
10. PASS. Scale `N/m` + Name "Define as" `K` compiles to `K := [2, -1; -1, 2]*N/m`, matching 002a's
    own example byte for byte.
11. PASS. "Add column" on a 2x2 grid adds one blank cell per row (now 2x3); filling it and then
    "Remove row" always leaves the compiled text matching the grid's current live shape.
12. PASS. Rows=1/Cols=3 `5,6,7` -> `[5, 6, 7]`; Rows=3/Cols=1 `5,6,7` -> `[5; 6; 7]`.
13. PASS. Rows=1/Cols=1 `5` -> `[5]`.

### OK/Cancel, new insertion
14. PASS. Cancel at either the Size or Grid step, for a brand-new insertion, leaves no region on
    the canvas.
15. PASS. OK on a brand-new insertion has the same net effect (`region.source`, `region.result`,
    `region.result.output`) as typing the compiled text directly into a fresh math region.

### OK/Cancel, existing region
16. PASS. "Edit as grid..." + a cell change + Cancel leaves `region.source` and the on-screen HTML
    exactly as before; the region stays in the sheet.
17. PASS, including the accepted judgement call: OK on an existing region updates `region.source`,
    `region.result`, and the on-screen *pretty* HTML immediately — checked to be byte-identical to
    what a direct text edit committing the same new text would have produced, not just that
    `region.source` changed underneath a stale display.

### Errors
18. PASS. A blank cell gives "Every cell must have a value" at that cell's location; OK is refused.
19. PASS. `1, 2` in one cell gives "A cell cannot contain ',' or ';'; use Add column/Add row
    instead" at that cell; `f(a, b)` (comma inside parens) is correctly accepted.
20. PASS. "Define as" with a blank/whitespace-only name gives "Name is required" at the Name field.
21. PASS. An undefined symbolic cell (`Y`) with numeric Show commits and closes the dialog; the
    resulting region's error is identical to a directly-typed `[Y] =` region's
    `"Y" is not defined`-family error.

### Raw-text fallback
22. PASS. "Edit as text" on an existing region discards in-dialog changes, leaves `region.source`
    unchanged, and opens the region's real `start_editing()`; on a brand-new insertion it behaves
    exactly like Cancel (nothing created).
23. PASS. No `_use_dialog_btn`-style control exists on the region or its inline editor; "Edit as
    grid..." from the not-currently-editing context menu is the only way back into the dialog.

### Regression
24. PASS. A dialog-created region round-trips to disk byte-for-byte identical to the same text
    typed directly (`RegionData`/`FORMAT_VERSION` unchanged, no `w`/`h` written).
25. PASS. Move, select, and single-owner delete on a dialog-created region behave exactly like any
    other `MathRegion`.

### Edge cases
- PASS. A fraction and a short expression cell (`1/3`, `sin(0.5)`) compile exactly as typed.
- PASS. Above-20x20 is never representable; exactly 20x20 is accepted at the dialog's own cap.
- PASS. Add/Remove row/column buttons are correctly disabled at both the 1 and 20 bounds.
- PASS. Going back from Grid to Size and growing keeps same-position cells and blanks new ones;
  shrinking drops cells that no longer fit (own design choice, matches spec wording).
- PASS. A malformed cell (`1+`) and a cell containing its own bracket literal (`[1,2]`) both pass
  the dialog's own checks and only fail once committed — the nested-bracket case surfaces exactly
  002a's existing `"Nested matrices are not supported"` message (confirmed against
  `livesheet/engine/matrices.py`'s own literal error string).
- PASS. All three "matrix combined with another operator" shapes (`A := [1,2] + [3,4]`,
  `det([1,2;3,4])`, `f([1,2;3,4])`) are never representable.
- PASS. The dialog performs no name-collision check of its own; a colliding "Define as" name is
  accepted unconditionally by the dialog and left entirely to the existing engine rule.
- PASS (not explicitly named in the spec text, added by this file): an empty bracket literal
  (`A := []`) and jagged rows (`[1, 2; 3]`) are both correctly non-representable.

## Defects
None found in the matrix-dialog implementation itself against the written spec. (The one defect
found and fixed this review was in the test file I was asked to finish, not in production code —
see above.)

## Observations (not defects)
- The one transient full-suite crash (fatal abort constructing a second `QApplication` inside
  `tests/test_gui.py::app`, not reproducible on three immediate re-runs) is most consistent with
  resource contention from more than one `QT_QPA_PLATFORM=offscreen` PySide6 process running
  concurrently in this shared sandbox (e.g. another agent's GUI tests running at the same time),
  not with anything in spec 008 or this review's own test file — the crash site is unrelated code
  neither read nor touched by this review. Worth keeping in mind if it recurs for someone else:
  re-run alone before assuming a real regression.
- `pytest-timeout` (used only transiently, by the previous tester session, to get a stack dump
  confirming the original hang) is still only installed in `.venv`, not declared as a project
  dependency. I did not need it myself once the `QMenu.exec` patch was replaced — the fix makes the
  hang disappear outright, so there's no remaining need for a timeout safety net specific to this
  file. I'd leave the call on whether it's worth proposing as a permanent dev dependency to the
  manager/developer generally (useful insurance against any *future* accidental GUI-test hang,
  but a separate decision from this review).

## Coverage gaps
- **No computer-use/real-display session this run**: the tools available to me for this task did
  not include an interactive display/computer-use tool, so all testing here was headless
  (`QT_QPA_PLATFORM=offscreen`), the same gap already flagged in review 006. Per the spec's own
  "Fits current architecture?" section and the project's testing rule, Theo (or a future tester
  session with computer-use access) should still do a manual pass on the real app covering:
  `Insert > Matrix` and the canvas's "Matrix here" through Size -> Grid -> OK and Cancel at both
  steps; Add/Remove row and column by mouse; both Name modes and both assignment-operator choices;
  all three Show modes including the display-unit box; the three validation messages appearing at
  the right field by eye; "Edit as grid..." appearing/not appearing correctly on representable vs.
  non-representable regions, including while another region is mid-edit; "Edit as text"; and
  save/reload through the real File menu.
- Keyboard-only interaction (Tab order across the grid/buttons) was not separately exercised; this
  is ordinary Qt chrome, not bespoke code, same reasoning as review 006.
- Scrolling behaviour of the Grid step's `QScrollArea` for a tall grid (e.g. 20 rows) was not
  visually exercised, only confirmed present in the widget tree; standard Qt chrome.
- Mouse-driven cell-text editing (actually clicking into a `QLineEdit` and typing, vs. `setText`)
  was not separately simulated; `QLineEdit.setText` exercises the same underlying field-collection
  code path the spec describes, but not literal keystroke-by-keystroke input.

## IP red flags
None observed. All field/group labels ("Rows", "Columns", "Elements", "Add row"/"Remove
row"/"Add column"/"Remove column", "Name", "No name (insert as a value)", "Define as", ":=
Definition", "≡ Global definition", "Scale/unit factor", "Show result", "Don't show a result",
"Show numeric result (=)", "Show symbolic result (→)", "Display unit", "Back", "Edit as text",
"OK"/"Cancel"), the error strings ("Every cell must have a value", "A cell cannot contain ',' or
';'; use Add column/Add row instead", "Name is required"), the `&Matrix…`/`Ctrl+Shift+M` menu
entry and the `MatrixDialog`/`MatrixFields`/`MatrixFieldError`/`compile_matrix_fields`/
`decompose_matrix_text`/`validate_matrix_fields`/`cell_has_separator` names are original, generic
dialog/engineering wording, consistent with the spec's own IP check — no vendor dialog's field
order, icons, or wording appears anywhere in `livesheet/gui/matrixdialog.py` or the touched parts
of `livesheet/gui/worksheet.py`/`livesheet/gui/main_window.py`. The two-step
size-picker-then-grid-of-cells pattern and OK/Cancel/"Edit as text" chrome match the spec's own
already-approved generic-dialog reasoning; nothing in the implementation goes beyond what the spec
described.

## Recommendation
Spec 008 is ready to merge as implemented: all 25 acceptance criteria plus every edge case hold
exactly as specified under black-box testing, and the full suite (including the developer's own 60
tests) passes cleanly together with this file. No defects found in the matrix-dialog code itself.
A real-window manual pass by Theo (listed under Coverage gaps) is still recommended before calling
this fully done, per the project's own testing rule — this review's environment had no
computer-use/display tool available.
