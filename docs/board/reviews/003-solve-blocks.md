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
