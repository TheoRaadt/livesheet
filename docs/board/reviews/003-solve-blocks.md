# Review 003 Solve blocks, Phase A

Spec: docs/board/specs/003-solve-blocks.md (Phase A only). Reviewed commit 280f2c3 (working tree, not committed). Tester, 2026-10-27.

## Verdict
Part A (headless): PASS for all Phase A criteria 1-11, with four defects S1-S4 (none blocks the criteria; S1 and S2 are robustness gaps in the solver). GUI part: NOT RUN by instruction (running app still has old code), see the GUI-check list below.

## Tests added
tests/test_solve_blackbox.py: 79 test cases (70 pass, 9 strict xfail = open defects). Expected numbers come from independent SciPy 1.15.3 / NumPy 2.2.6 / SymPy / math calculations in the file, not from the developer's tests/test_solve.py. Covers: criteria 1-11; parsing of model_vary / model_require / model_setting / model_result (incl. unicode `≤ ≥ ≡`, spacing, malformed regions); no unknowns; unknown without guess; guess with wrong unit; unit conversion of the guess (`0.01 min` vs `0.6 s`); unit mismatch between the sides of a relation; dimensionless equations; over- and under-determined systems; singular Jacobian; non-converged with `steps 1`; `accuracy` edge values (0.999, 1e-15, 1e-16, 0, negative, text); duplicate vary / duplicate settings; model names that clash with variables and units; two models in one sheet (isolation, same unknown name in both); regions out of reading order (result above its definitions, `No result region ... below`); redefinition of a bound unknown afterwards; results do not leak above the result region; `least`, `most`, `steps`, `accuracy` still usable as variable names; Phase B interim errors; tiny (1e-300) and large (1e12) values; output text format; 10-unknown system (solution cross-checked with NumPy, runs in well under 1 s); `import livesheet.engine` does not import scipy (subprocess); scipy loaded only when a result region runs; missing scipy gives the `Solving needs the scipy package` message (monkeypatched).

## Results
- Spec numbers re-computed independently: x^2+y^2=25, xy=12 -> (3,4)/(4,3); x^2-5x+6 -> 2, 3; fall time sqrt(2*20/g) = 2.01962 s with g = 9.80665 m/s^2 (matches criterion 3; spec line 76 shows the rounded 2.0196). All correct.
- Full suite on 280f2c3 plus the new file: 530 passed, 3 skipped (PySide6, no libEGL in the VM), 10 xfailed (9 mine, 1 older), 0 failed.
- Lazy import: confirmed. Performance: 10-unknown nonlinear system solves in a fraction of a second.

## Defects (minimal repro, all strict xfail in the test file)
- S1 (solver robustness, scaling): a root many orders of magnitude from a unit-sized guess is not found. `vary x from 1 in a` / `x == 1e9 in a` / `settle in a` gives `No solution found: closest point violates "x == 1e9" by 1.0e+00`. Fails also for `x == -1e9`, `2*x == 1e12`, `x^2 == 1e12`, and with units (`vary p from 1 Pa`, `p*2 m^2 == 2e9 N`). Works up to 1e8 (`x == 1e8` ok), fails at 1e9. A user with a bad (too small) guess gets an error that does not say so; an automatic retry with a rescaled guess or a hint in the message would help. Severity: medium.
- S2 (stationary guess): a zero derivative at the guess blocks a simple root. `vary x from 0 in a` / `x^2 == 1 in a` / `settle in a` gives `No solution found ... "x^2 == 1" by 1.0e+00`; the same from guess 0.001 gives x = 1. Same for `x^2 - 1 == 0`. Guess 0 is the natural default, so this is likely to be met by users. A small perturbation of the start point on failure would fix it. Severity: medium.
- S3 (warning leak): a NumPy `RuntimeWarning: invalid value encountered in log` is printed to stderr when the guess is outside a function domain (`vary x from -1 in a`, `ln(x) == 2 in a`, `settle in a`). The returned error is clean (`Cannot evaluate at the starting guess: result is not finite`). Wrap the guess evaluation in `numpy.errstate(all="ignore")` / `warnings.catch_warnings`. Severity: low.
- S4 (message): `Not converged: stopped after 5 steps` is reported with `steps 1` (vary x from 10, `x^2 - 5*x + 6 == 0`). The number of steps used exceeds the configured limit, probably the solver's own function-evaluation count or a minimum. Either enforce the limit or word the message ("evaluations"). Severity: low.

## Observations (not defects)
- Under-determined `settle` minimises the guess-scaled distance, as the spec says: `vary x from 3, y from 0`, `x + y == 2` gives x = 2.1, y = -0.1, not the Euclidean projection (2.5, -0.5). Criterion 9 (guess 0,0 -> 1,1) holds. Worth one sentence in user docs because the answer changes when the guess magnitude changes.
- Phase B kinds parse and report `Inequality constraints are not available yet` / `least and most are not available yet`; checked, nothing crashes. `x == x + 1`, `x^2 == -4`, `exp(x) == -1` all give `No solution found`, never an exception.
- `accuracy 1e-16` is rejected with a validation error (tighter than float epsilon); `accuracy 1e-15` is accepted and solves.
- `x^2 + 1e-20 == 0` is accepted as solved (x ~ 1e-10) because the tolerance is relative to the reference scale; that follows the spec's tolerance rule, but users may find it surprising.
- Bound unknowns are plain definitions afterwards; redefining them later in the sheet wins (reading order), and a model result above the redefinition is not affected.

## Coverage gaps
- No GUI run for 003 (running app has old code).
- Phase B (inequalities, `least`/`most`, SLSQP path, `No solution found` for infeasible sets) only checked for the interim message; tests must be added when Phase B lands.
- Solve inside user-defined functions, with matrices/vectors as unknowns, and with range variables or tables are not specified and not tested.
- .lsheet round trip of model regions is not tested (file format handled by the GUI/file layer).
- Complex-valued roots are not supported by spec; only the clean error for `I` at the guess is tested.

## IP red flags
None. Keywords `vary`, `settle`, `least`, `most`, `accuracy`, `steps`, `in <model>` are generic words; the spec states the design is original and the tests contain no vendor syntax or strings. Not legal advice.

## To check in the GUI once the app is restarted on 280f2c3 or later
1. Type the spec example (fall time) region by region: `vary t from 1 s in fall`, `h := 20 m`, `0.5*g*t^2 == h in fall`, `settle in fall`; the result region shows `⇒ t = 2.0196 s` and `t =` below shows `= 2.0196 s`.
2. Typing `vary`, `==`, `<=`, `>=` and unicode `≤ ≥` works in the editor; the `in fall` suffix is not rewritten; `:` handling (`x:5` -> `:=`) does not touch `vary x from 1`.
3. Error display for each message (`No solution found`, `Not converged`, `Units do not match`, `No result region ... below`) is readable and the region colouring matches other errors.
4. Long result lines (10 unknowns) do not overlap neighbouring regions (known layout weakness from reviews 001/002a).
5. UI responsiveness: a slow solve (S1 failure case with `steps 5000`) must not freeze the window for long.
6. Save and reopen a sheet with model regions: statuses and results are recomputed; scipy missing message appears sensibly if scipy is absent.
7. Undo/redo and deleting the result region or a `vary` region re-evaluates dependants (`Fix the errors in the regions of model ...`).
8. Phase B interim errors displayed cleanly; Save As / Export untouched (only Cancel, never write over examples/).

## Decisions for the manager
- Ask the developer to fix S1 and S2 before Phase B (both strongly affect first-time use), S3 and S4 are quick.
- Decide whether the guess-scaled "closest point" semantics should be explained in the user docs.

## Fix round (developer, b7beb0f) and headless recheck
Full suite on b7beb0f: 539 passed, 3 skipped, 1 xfailed (older, not 003). S1-S4 fixed by the developer (no xfail left in tests/test_solve_blackbox.py); the message now says "function evaluations".

## GUI check on b7beb0f (tester, 2026-10-27, real app, demo.lsheet open, nothing saved)
PASS:
- Fall-time example typed region by region (`vary t from 1 s in fall`, `h2 := 20 m` (h is already 200 mm in the demo), `0.5*g*t^2 == h2 in fall`, `settle in fall`, `t =`): result `⇒ t = 2.01962 s` shown right of the result region, blue; `t = 2.01962 s` below. The vary region alone shows red `No result region for model "fall" below this region` until the result region exists.
- Typing `vary`, `==`, `≥` (unicode), `in fall`, `in b1` is kept as typed; `x:5` becomes `x := 5` next to model regions. Note: typed `<=` is displayed as `≤` (pretty-printing); the stored source text was not inspected.
- Errors shown red with warning sign, on the result region: `Units do not match in constraint "d == 3 s"`; `No solution found: closest point violates "w^2 == -4" by 8.0e-01`; `Not converged: stopped after 5 function evaluations (steps limit 1), largest violation 2.5e-01 (try another starting guess or raise steps)`; `Inequality constraints are not available yet` (Phase B interim). A wrong unit on the guess (`1 m`) turns the result region red (`Units do not match in constraint "0.5*g*t^2 == h2"`) and `t =` red (`t is not defined`); restoring `1 s` heals both.
- Dependants: editing `h2 := 20 m` to `40 m` updates the result to `t = 2.85617 s` (both regions) immediately.
- Failing solves (no solution, not converged) return instantly; the window never froze.
- 10-unknown under-determined solve (`vary a1 from 1, ... a10 from 10 in L1`, `a1+...+a10 == 100`) works: `⇒ a1 = 1.11688, a2 = 2.46753, ...`.
OBSERVATIONS / OPEN:
- G3 (layout, minor): long result and error lines are not wrapped; the 10-unknown result line and the Not-converged message run past the right window edge and the canvas gets a horizontal scrollbar. Nothing overlaps neighbours vertically (one text line), but the end of the result cannot be read without horizontal scrolling. Same class as the wide-grid finding in review 001.
- G4 (CRASH or quit, UNCONFIRMED, high priority to reproduce): after the above, I selected the `settle in fall` result region (single click, region frame shown) and pressed Backspace to delete it. The window stayed one more frame, then the LiveSheet process was gone (computer_list_apps: org.python.python not running; app_menu "app not running"). I did not quit the app. Code path: worksheet.keyPressEvent -> remove_regions (removeItem + deleteLater + schedule_recalc). The engine side is fine (headless run of the same sheet without the result region gives only `t is not defined`). I could not see a traceback (Terminal not granted). Possible cause: deleting a result region of a model while its dependants are re-evaluated; or something unrelated (e.g. Theo closed it). Needs a repeat: select `settle in fall` and delete it.
NOT CHECKED (app ended): deleting the vary region / result region and the resulting messages, source text after `<=`, Save As / Export dialogs (not touched, nothing written), zoom (never changed, 100%). Scratch regions were lost with the process; demo.lsheet was never saved, git status is clean (examples/ untouched).

## Manual GUI checklist 003B (for Theo)
Phase B (inequalities, chained relations, least/most, marks). Expected strings were produced headless by the engine on the working tree (2026-10-28). Start with `livesheet examples/demo.lsheet`. Never use Save or Save As on examples/ (cancel any dialog); close at the end with Don't Save / Discard.

1. Type four regions, each on its own line, in order: `vary x from 0 in i` / `x^2 == 4 in i` / `x > 0 in i` / `settle in i`. Expect the two constraints to show a green-ish `✓`, the settle region `⇒ x = 2`. Look at: the marks appear next to the constraint regions, not on the vary region (that one shows nothing).
2. Add a region `x =` below. Expect `= 2`.
3. Edit `x > 0 in i` into `x < 0 in i` (change the character). Expect `⇒ x = -2`, marks stay `✓`. Edit back to `>`; result returns to 2.
4. Select the `settle in i` region (click once) and press Backspace. Expect: no crash, the `x =` region turns red `x is not defined`, the constraint regions show red or no mark; window stays responsive. Then press Cmd+Z if undo exists; otherwise retype `settle in i` and see the result return.
5. Rectangle: `vary w from 1 m, d from 1 m in plot` / `2*(w + d) <= 20 m in plot` / `most w*d in plot`. Expect `⇒ w = 5 m, d = 5 m; value = 25 m²` (the superscript 2 must render). Check the `≤` pretty-printing of typed `<=` and that the line is readable (known: long lines run off to the right).
6. Insert `0 m <= w <= 4 m in plot` above the `most` region. Expect `⇒ w = 4 m, d = 6 m; value = 24 m²` and `✓` on the chained constraint.
7. Projection: `vary x from 0, y from 0 in n` / `x + y <= 2 in n` / `least (x-3)^2 + (y-1)^2 in n`. Expect `⇒ x = 2, y = 0; value = 2`.
8. Infeasible: `vary x from 0 in f` / `x >= 2 in f` / `x <= 1 in f` / `settle in f`. Expect the settle region red with `No solution found: closest point violates "x >= 2" by 5.0e-01` and a `✗` on `x >= 2 in f`. Must return instantly.
9. Unbounded: `vary x from 0 in ub` / `most x in ub`. Expect red `Not converged: stopped after 200 function evaluations ...` within about a second; the window must not freeze (try typing in another region right after).
10. Wrong unit: in step 5 change `20 m` to `20 s`. Expect red `Units do not match ...` on the result region; restore `20 m` and the result heals.
11. Delete the `vary w ... in plot` region (select, Backspace). Expect a red message on the result region (no vary / no unknowns for model "plot"), no crash.
12. Zoom in and out (Cmd + / Cmd -) and resize the window with all of the above visible: marks and results stay attached to their regions and nothing overlaps.
13. Open File > Export PDF, check the preview/dialog opens and the `✓ ✗ ⇒ ²` glyphs appear in the page; Cancel (do not write anywhere inside the repo).
14. Close the window / quit with Don't Save. Afterwards run `git status` in the repo: examples/demo.lsheet must not be listed as modified. Check the process is gone (Activity Monitor or `pgrep -f livesheet`).

Report any crash, any red region that should be healthy, any freeze over 2 s, and any step where the text differs from the expected one.
