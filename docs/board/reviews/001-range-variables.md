# Review 001 Range variables and result tables

Spec: docs/board/specs/001-range-variables.md. Reviewed commit 3d74db5 (working tree = HEAD plus the new test file). Tester: tester agent, 2026-10-27.

## Verdict
Part A (headless): PASS with minor defects (D1-D5). Part B (real app on the Mac): NOT DONE, blocked (see GUI session log). The spec cannot be signed off as "tested in the real app" until Part B is done.

## Tests added
tests/test_ranges_blackbox.py: 66 tests (58 pass, 8 xfail strict = open defects below). Expected values are computed in the file with Fraction/SymPy/math, independent of the developer's tests. Covers: spec numbers re-derived, exact-arithmetic sequence checks (no drift up to 10000 values), negative/fractional/descending steps, mixed length units, tolerance edge (0.3/0.1), unit conversions, unicode names/operators/NBSP/unicode minus, keyword case and spacing, name clashes (`total`, `table`, `to`, `step`, unit name `s`), redefinition (range<->scalar, local over global), global ranges (`≡`, `::=`, order), circular/self references, ranges used in other definitions, limits (10000 ok, 10001 error, astronomical counts fast), performance budget, all error messages of criterion 11 plus extra forms, parser fields, engine reuse, significant digits, singular/plural output.

## Results
- Spec numeric examples (criteria 1-10) verified independently: all correct.
- `pytest -q --ignore=tests/test_gui.py`: 155 passed, 1 skipped (developer GUI smoke test skips: no libEGL), 8 xfailed.
- `tests/test_gui.py` cannot even be collected in the VM (module-level `from PySide6.QtTest import QTest` raises ImportError: libEGL). This is a test-file issue (should use pytest.importorskip); it makes the full suite command from the task fail in the VM. Developer's test_ranges.py guards its own GUI test properly.
- GUI test of the table display never ran anywhere yet.

## Defects (minimal repro)
- D1 (minor): `i := 1 to 5 step 0.0` -> error "Range limits must be real numbers"; spec says "step must not be zero" (works for `step 0`, `step 1-1`, `step 0 s`). xfail test_zero_step_float_literal.
- D2 (minor): `table ),a(` (after `a := 1 to 3`) -> error "list index out of range" (python message leaks; negative bracket depth in _split_top_level/_split_column_unit).
- D3 (minor): `i := 1 to oo` / `-oo` / `inf` / `1e309` -> "cannot convert float infinity to integer"; `i := 1 to 1e308` -> error text contains a 300-digit number. Also `i := 1 to 3 step oo` is accepted (1 value). Should be a clean "range limits must be finite" / "too many values".
- D4 (spec deviation, decision for manager): spec edge case says a cell error such as `table i, 1/(i-2)` makes the whole table an error "Division by zero". Engine renders the cell `undefined`, identical to existing `1/(x-2) =` -> `= undefined`. Developer chose consistency with existing evaluation (test_division_by_zero_cell_follows_existing_evaluation). Decide: change spec or code.
- D5 (minor): a multi-line math region `table a,\n a*2` is not recognised as table (error "a is a range variable (use table)"): `_TABLE_RE` has no DOTALL. Only matters if regions can hold newlines (to be checked in the GUI, Part B).
- Observations (not defects): `table a in 1` prints `1 1` (garbage unit "1"); `a-a` / `a*0` for a in metres show `0` (unit lost, same as existing `x-x =`); `x₁` subscript names give "Syntax error" (pre-existing); `°C` unsupported (pre-existing).
- Performance (risk): a 10000-row table takes about 2.8 s in the engine (2 columns, also with units). If the GUI recalculates on every keystroke on the GUI thread, editing a large table or its range will freeze the UI for seconds. To be checked in Part B.

## GUI session log (Part B)
Not executed. Findings so far:
- device_bash runs in a Linux VM; it cannot start or see Mac apps.
- computer_resolve_access("Terminal") returned tier "click": Terminal can be seen and clicked but not typed into, and no keys can be pressed (restrictedTierNote). I therefore cannot create the venv or start `livesheet` from Terminal, and I did not try workarounds (e.g. planting a .command file or driving Finder), because that would circumvent the access tier.
- Not requested/granted: nothing. No app was started, nothing to close, no process left behind (nothing was launched). No computer lock was taken.
- Also unknown: whether python3 exists on the Mac.

What is needed to finish Part B (manager/Theo to decide, one of):
1. Theo starts the app himself once (`~/livesheet-venv/bin/livesheet ~/Documents/Claude/LiveSheet/livesheet/examples/demo.lsheet`); I then request access to the LiveSheet/Python window (tier allowing typing/clicking) and run the GUI checklist, and quit it via its own menu; or
2. Theo grants a way to launch (e.g. a Finder/launcher app or a LiveSheet.app bundle in full-control mode) and I do everything; or
3. Theo accepts a GUI test only via the headless offscreen suite on a machine with libEGL (not possible in the VM).
GUI checklist prepared: open demo; add `v := 3 m/s`, `t := 0 s to 10 s step 2 s`, `table t, v*t in m` and verify 6 rows; error cases (`step 0`, `to 10 m`, `table t in kg`, `t =`); edit/move regions; File menu dialogs (open, save as, Export PDF) then cancel; zoom; try multi-line table text (D5) and a 10000-row table (freeze); quit via menu; `pgrep -f livesheet` must be empty.

## Coverage gaps
- No real GUI run at all (table rendering, monospaced alignment of wide/unicode cells, scrolling of tall tables, recalculation latency).
- No .lsheet round-trip test with range/table regions (document layer unchanged by spec, but never exercised).
- No property tests (hypothesis not a dependency).
- Offset units (degC) not testable (unsupported).

## IP red flags
None found in the code or tests: keywords `to`, `step`, `table`, `in` are the spec's own words; no double-dot notation, no vendor strings, no copied examples. The spec itself cites a vendor help URL (concept only); manager's IP decision on notation (open item in decisions.md) still stands. `max`/`Max` aliases etc. are generic. Not legal advice.
