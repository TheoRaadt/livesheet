# Review: spec 028 phase D2 (import dialog, Data tab, sheet integration)

Tester: independent black-box tests from the written spec. File: tests/test_spec028_d2_review.py
(70 cases: 66 passed, 4 strict xfail = real defects). Developer file tests/test_data_tab_028.py: all
pass, but see D2-R3 (it segfaults the interpreter at exit). Full suite without the developer's D2 file:
3213 passed, 2 skipped, 13 xfailed, exit code 0.

## Coverage
Dialog: all option controls and their items, suggest-on-choose-file (semicolon/decimal comma, no header),
live re-parse on option change (header, delimiter, Other + custom char, skip lines, encoding, incomplete
rows), preview capped at 20 rows, columns table (kind, unit cell edit as override, empty = unitless, bad
unit message, override cleared by choosing a new file), name validation (sin, m, pi, 2run, empty, duplicate,
41 chars, case sensitivity, default de-duplicated name), OK disabled on every error, warnings do not block,
result_dataset is a copy, debounce timer, ~2 MB read time.
Data tab: empty state text and the 4 buttons (action buttons disabled), Import is first focusable, heading
text/tooltip, one button per column + tooltips (unit, min/max, matrix), no-matrix note, text column disabled
button, several datasets in import order + heading selection, dynamic buttons outside symbol_buttons, a
column called sin/pi is safe, click inserts the exact token (empty sheet and after `a := `), import inserts no
region.
Sheet: mean/fit_linear/index values, units flow, user function, regions above the import recalculate,
redefinition error while other regions evaluate, rename/remove (monkeypatched QInputDialog/QMessageBox: ok,
cancel, 5 invalid names, confirm text exact), refresh (updated, unit override kept, missing file keeps data,
ragged new file keeps data, columns-changed message, no source, relative source resolved from the sheet
folder), modified flag, v5 save/reopen without the CSV, no-dataset file keeps old shape/version, removing
the last dataset returns the old version, v1 file load, version 5 without datasets rejected, new/open reset
the tab and selection, exact floats, Insert menu entry and Import button call the same command, accept and
reject paths, Outline/Statistics tab switching, tab-strip resizing, 8 datasets.

## Defects (strict xfail in the test file)
D2-R1 (low, known to the developer): the "Reading..." state for files over about 2 MB (spec, dialog item 5)
is not implemented. The read is synchronous in the GUI thread. Measured: a 19000 x 10 file (>2 MB) opens in
well under a second offscreen, so the practical effect is small; the spec text is simply unmet. Either
implement or amend the spec. Test: test_dialog_reading_state_for_big_file.
D2-R2 (low): when a read error occurs (for example the wrong delimiter is chosen), the preview is refreshed
but the Columns table keeps the previous rows. Repro: dialog on `a|b\n1|2\n3|4` (suggests `|`, 2 columns), set
Delimiter to Comma: error "The file has no numeric column." but column_rows() still lists a, b.
Test: test_dialog_columns_table_cleared_on_error.
D2-R3 (medium for the test suite, low for the app): ImportDataDialog is never garbage collected. Minimal repro:
`d = ImportDataDialog([], None); ref = weakref.ref(d); del d; gc.collect()` -> ref() is still alive (the
lambdas connected in _build capture self). At interpreter exit this prints "QObject: shared QObject was
deleted directly. The program is malformed and may crash." and in pytest the process dies with exit code 139.
This is the developer's reported segfault: tests/test_data_tab_028.py alone exits 139 every time (3 of 3 runs;
order dependent, e.g. test_dialog_ok_disabled_on_errors then test_dialog_suggests_and_previews), and the
full suite exits 139 with it (2 of 2 runs) but exits 0 without it (and with my file, which frees its dialogs
with shiboken6.delete). All tests pass in those runs; only the process exit crashes, and the crash can surface
in whatever teardown the GC happens to hit, which explains why it was seen in test_spec024_review.py.
Fix options: in the dialog, connect with bound methods/functools.partial instead of closures over self (or
call deleteLater() after exec in MainWindow.import_data, which also stops the dialogs piling up as children
of the main window); in the developer tests, delete the dialogs they create. Test: test_dialog_is_garbage_collected.
D2-R4 (low/medium, spec gap, not covered by the spec's name rules): column variables of different datasets
can collide silently. Dataset `a` with column `b_c` and dataset `a_b` with column `c` both define `a_b_c`;
the last dataset wins and the result depends on import order (verified at engine level too:
Engine.evaluate(..., datasets=[a, b]) gives 20, [b, a] gives 2; no error). Same class: a dataset named
`run1_t` next to `run1` with column `t`. Suggest: validate_dataset_name / add_dataset reject a name whose
variables would clash, or the evaluator reports the ambiguity. Test: test_cross_dataset_column_variable_collision.

## Observations (no defect, for the manager)
O1 Existing user variable with a dataset's name (`run1 := 3` before import): after the import that region
shows "'run1' is a dataset column and cannot be redefined" and the dataset stays (consistent with spec
criterion 9). The import dialog does not warn about it beforehand.
O2 Default dataset name for a file called `m.csv` becomes `m_2` (reserved unit name avoided): good.
O3 Changing the Skip-lines spin box does not re-run the header suggestion, so after skipping a comment
line the user must tick "First row is a header" by hand. Acceptable (spec: suggestion only on file choice).
O4 Autocomplete (spec 024): dataset variables (`run1_F`, `run1`) are NOT offered; only region-defined names
and builtins are. Neither spec requires it; recorded as test_autocomplete_does_not_offer_dataset_names
(pins current behaviour). Suggest a follow-up if wanted: completion.complete() takes user_sources from
region texts only, so datasets would need passing in via Worksheet.
O5 No undo stack exists for dataset edits; Remove asks for confirmation (as the spec allows). The developer
should have stated this in log.md.
O6 Spec criterion 12 says the heading is "run1 - 4 rows x 2 columns"; the implementation appends
" - run1.csv" like the Behaviour section; consistent.

## Environment note (not a LiveSheet defect)
Around 20:56 today every file under .venv got the macOS "hidden" flag (1323 items, `ls -O` shows `hidden`).
Consequences: Qt cannot enumerate its plugin directory ("Could not find the Qt platform plugin offscreen"),
every pytest run aborts at QApplication creation, and the editable-install .pth file is ignored
(ModuleNotFoundError: livesheet outside the repo root). I ran `chflags -R nohidden` on
.venv/lib/python3.14/site-packages/PySide6/Qt/plugins before each run (the flag came back repeatedly, some
process re-applies it). Whoever runs tests next: `chflags -R nohidden .venv` first if the Qt plugin error appears.

## Real application check
Not done: this agent session has no computer-use tools (only shell and file tools), so the real window,
the native Browse... file picker and the Rename/Remove prompts were not driven by hand. Rename/Remove/Refresh
message paths were exercised with monkeypatched QInputDialog/QMessageBox. A human (or a session with
computer-use access) should still open Insert > Data from file..., pick a CSV with Browse..., rename, remove,
refresh, then save/reopen.

## IP check
No vendor names, strings or assets found in importdialog.py, the Data tab code or the tests; messages match
the spec's own wording.
