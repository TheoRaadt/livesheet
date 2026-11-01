# Review 022: formula tabs (specs 018/019/020) and bare-unit-name hardening

Reviewer: testing agent. Tests written from the specs and decisions.md only.
New test files: tests/test_formula_tabs_review_022.py (141 tests),
tests/test_bare_unit_check_review_022.py (54 pass + 6 strict xfail).

## Results
- Full suite (QT_QPA_PLATFORM=offscreen): 2032 passed, 8 xfailed, 0 failed
  (manager's earlier run: 1837 passed, 2 xfailed; difference = my new files and the
  developer's files; the 6 extra xfails are my documented regressions below).
- No production code changed. Nothing committed.

## Real app: COULD NOT drive it
No computer_* tools were available in this session. I did launch `livesheet examples/demo.lsheet`
on the Mac (process started, no crash in log) but `screencapture` failed ("could not create image
from display", no screen permission), so I could not see or operate it. I killed it (verified no
livesheet process remains). Substitute: rendered the SidePanel offscreen to PNG and looked at the
Chemical tab (5 grey sub-headers, 21 buttons, labels readable, no clipping at 300 px). Mechanical
render was saved but not inspected. A human pass on the real window (click one button per
sub-category into a region; New/Open/Save, Export PDF, zoom) is still outstanding.

## Part 1: formula tabs - PASS
Verified: tab order (10 tabs, Outline/Data moved to 8/9, first five unchanged); sub-header counts
2/2/5 headers with 6+9, 7+4, 4+5+4+4+4 = 15/11/21 buttons in the spec's order; label/token/tooltip
tables; every one of the 47 buttons inserted through a real MainWindow gives the exact token;
buttons call only insert_token; document stays format version 1; all labels unique across the
panel (symbol_buttons is keyed by label); every worked example of 018 (5-16, 18), 019 (3-7) and 020
(4-7) via Engine, plus numeric cross-checks of the remaining templates; every template alone
followed by `name =` errors "not defined" (criterion 10), except the R_gas constant by design; no
template name collides with UNITS/BUILTINS.

Developer deviations, verdict:
- ASCII labels `rho_gas`, `m-dot bal.`: ACCEPT. Cosmetic, documented, uniqueness preserved.
- ASCII tooltips (`N*m` for the middle dot, `-` for em dash, quotes dropped around 30*deg): ACCEPT.
- Moment tooltip gains the "bare M = shows J" warning: REQUIRED by criterion 16 note, correct.
- "Average shear stress" tooltip dropped the spec's design-note parenthesis: ACCEPT (it was
  rationale, not user text). Minor deviation from "exact tooltip".
- Criterion-17 regression test (naive `sigma := F/A` gives ok) dropped: ACCEPT, it is now
  obsolete. I added the inverse (test_m17_regression_landmine_now_closed_with_naive_names).
- Corrected explicit-unit forms from decisions.md used: correct. Note `Q_sens = J` prints
  `1.2558x10^6 J` (spec said 1255800 J; formatter uses exponent).

Usability note (pre-existing, not a defect of the tabs): `g` is standard gravity in UNITS; grams
are `gm`. `28.97 g/mol` in the chemical templates silently means m/s^2/mol. Worth a manual note
or a tooltip hint.

## Part 2: _check_bare_units - mostly sound, with regressions
Rule: error only when the expression has no digit and every identifier is an untouched UNITS
name. Still works (tested): `5 N`, `10 m`, `3 m/s`, `2*N`, `N*2`, `x := kN`-style unit field
(`x = kN` with x defined), user shadowing (F, A, m, s defined before use), `:::=`/global
definitions, function parameters, matrices with a number/user name, ranges, tables, solve blocks,
plots, `I`, `e`, `pi`, demo.lsheet (only its intentional `L + F` unit-mismatch error remains).
Still errors: `sigma := F/A` ("F is not defined"), `F =`, `F/A =`, `V*A =`, `N*N =`, `(N) =`.
Dependents cascade ("W is not defined").

### Defects (legitimate pre-change usage that now errors) - all pinned as strict xfail
D1 (medium). Unit-alias definitions: `u := m/s` then `v := 5 u` (also `dist := m`, `kph := km/hr`,
  `gram := g`) used to work; the definition now errors "m is not defined", and every use
  cascades "u is not defined". Probably the most plausible real-world breakage.
D2 (low-medium). Bare unit conversion factors: `m = mm`, `kN = N`, `N*m = J` printed `= 1000 mm`
  etc.; now "m is not defined". (`1 m = mm` still works.)
D3 (low). `g =` no longer shows standard gravity (9.80665 m/s^2); `x := g` errors. `a*g` with a
  defined still works.
D4 (low). Matrix literal of unit names `z := [N m]` now errors.
D5 (wording). The message "m is not defined" is misleading for a valid unit; a hint such as
  "m is a unit; write a number before it" would help. Also inconsistent: `N^2 =` is ok but
  `N*N =` errors.
Suggest: either exempt definitions whose whole right side is a unit expression (D1) or
  accept and document in the manual; Theo should decide.

### Known gaps (silent, by design; confirmed)
`m^2 =`; `P/A` with P user-defined; any expression containing a digit (`F^2/A`, `2*F/A`);
function-call wrappers (`sqrt(F/A)`); builtin constants mixed in (`e*F`, `I*A`); symbolic
arrows (`F/A ->`); function bodies (`f(x) := F/A`, `f(2) =` is ok). The mechanical `P/Ac` and
other tab templates are safe only because their names are not unit names.

### test_matrices_blackbox.py change
Legitimately obsolete: the old test asserted `A =` gives `= 1 A` and its own comment said it
only documented the name clash; Theo's 2026-11-01 decision reverses that. The second assertion
(matrix then `A =`) is kept. The other changed test files only shift tab indexes 7 -> 10 tabs,
no weakening.

## IP red flags
None seen: formulas are textbook, labels/tooltips own wording, no vendor names (grep-tested).

## Coverage gaps
No real-window click-through (see above); tooltip wrap/elision at 120 px not checked; undo, PDF
export and zoom not exercised by this review.
