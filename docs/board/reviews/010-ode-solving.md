# Review 010: ODE solving (tester, black-box)

Spec: `docs/board/specs/010-ode-solving.md` (backlog item 14), phase A (symbolic via SymPy
`dsolve`) + phase B (numeric fallback via SciPy `solve_ivp`), implemented together per the
manager's dispatch. Commit under test: `2df0955273e5c85cd273cb4a9c222865cfeb223b`
("Implement spec 010: ODE solving (symbolic dsolve + numeric solve_ivp fallback)"), branch
`claude/ga-mk3uos`, not yet committed into `main`/reviewed before this session. New file:
`livesheet/engine/odesolver.py`; changed: `livesheet/engine/syntax.py`,
`livesheet/engine/plotting.py` (the `over` sub-grammar refactor), `livesheet/engine/
evaluator.py`. Developer's own tests: `tests/test_odesolver.py` (29 tests) -- read only
after drafting my own tests, to check for coverage gaps, not consulted while writing them.

## Verdict

**Pass**, with no blocking defects against spec 010's 18 numbered acceptance criteria or its
Edge cases section. Two items worth the manager's attention regardless: a real (if narrow)
multiprocessing/library-usage footgun (see D1) and a significant, previously-undersold
performance cost of the chosen symbolic-timeout mechanism (see D2) -- neither blocks a
numbered criterion, but D2 in particular will be visibly felt in the GUI on every sheet with
an `evolve`/`evolve symbolic` region, even the spec's own simplest example. Also two
pre-existing (not introduced by this spec) IP red flags found and reported below.

## Tests added

`tests/test_odesolver_review.py`: 28 tests, all pass, written from `docs/board/specs/
010-ode-solving.md`'s own "Acceptance criteria" (1-18) and "Edge cases" sections, driven only
via `Engine().evaluate([...])` the way the spec's own preamble describes. Numeric
expectations for criteria 1-3, 14-15, 17 were hand-derived independently with plain
`math.exp`/`math.cos` *before* running anything (exponential decay `10*exp(-t/4)`,
`cos(t)` for the undamped oscillator, `-g*t`/`-g*t^2/2` for free fall using this project's
own `g = 9.80665 m/s^2` constant from `livesheet/engine/units.py`, `5*exp(-2t)` for the
forced-decay example, `-cos(0.2) ≈ -0.98007` for the pendulum's energy constant) -- these are
standard, independently derivable textbook facts, not sourced from any vendor example, and
match the spec's own quoted values exactly within its stated tolerances.

Specifically exercises, in addition to the 18 numbered criteria and the Edge cases section:
- An independent re-derivation of deviation 1 (criterion 7's first scenario), confirming by
  direct dimensional analysis that `y`'s own dimension provably cancels out of
  `diff(y,t) + y/tau == 0`'s internal consistency check regardless of whether `y(0)` is given
  as a length or a bare number -- any check that *would* flag the bare-number case also
  incorrectly flags criterion 1's `y(0) == 10 m` case. Confirmed the actual implementation's
  behaviour is "ok" for both (test `test_c7_deviation_criterion7_scenario1_mathematically_
  unreproducible`), consistent with the developer's own disclosed finding, not merely
  trusting it.
- Deviation 2 (the `evolve`/`evolve numeric` wording on a closed-form failure with no `over`
  line): confirmed `evolve symbolic` still gives criterion 6's exact literal wording
  (`"No closed-form solution found for..."`), while `evolve`/`evolve numeric` give the
  `"over ... is needed"` wording instead, exactly as disclosed.
- Deviation 3 (no `dsolve_system`, one function at a time in dependency order): confirmed
  criterion 3's coupled free-fall system still gives the exact expected numbers, *and*
  separately confirmed a genuinely mutually-coupled nonlinear system (not one of the 18
  criteria, `diff(x,t)==y**2`, `diff(y,t)==x**2`) falls back cleanly to a numeric result
  rather than crashing or silently claiming a wrong closed form.
- Deviation 4 (multiprocessing-based `dsolve` timeout): see "Deviation 4, deep-dived" below --
  tested directly for correctness under pytest, process-leak behaviour, and the risk flagged
  in the task (D1 below).
- Deviation 5 (piecewise-linear interpolation for the bound numeric function): confirmed
  directly that evaluating the bound function at an in-between (non-grid) point is
  measurably less accurate than the integrator's own accuracy at a grid point (~13% error at
  `t=0.25` vs <1e-4 at the reported grid points for the `forced` example) -- exactly as
  disclosed, not hidden, but a real sharp edge with no user-visible warning.
- Division by zero, huge numbers (`1e300`), unicode function/variable names (`θ`), complex
  closed forms from a complex-rooted characteristic equation, and the `plot`-block `over`
  sub-grammar (spec 004) continuing to work unchanged after the refactor.

## Results

Fresh `QT_QPA_PLATFORM=offscreen pytest -q` from a clean shell, commit `2df0955`:
**1154 passed, 2 xfailed, 4 failed**. The 4 failures (`tests/test_matrices_blackbox.py::
test_50x50_float_performance`, `tests/test_solve_b.py::test_rectangle_in_a_perimeter_budget`,
`::test_results_are_bound_with_units`, `::test_same_model_gives_several_results`) were
independently re-confirmed pre-existing and unrelated to this spec: checked out the parent
commit (`911addf`, immediately before spec 010's commit) and re-ran exactly those four tests
in isolation -- the three `test_solve_b.py` failures reproduce identically there (same
assertion, same error text); `test_50x50_float_performance` passed on that run (it is a timing
threshold test, flaky either way, not spec-010-related in either direction). Working tree
restored to `2df0955` afterward (`git status` clean, confirmed).

After adding `tests/test_odesolver_review.py`: **1182 passed, 2 xfailed, 4 failed** (same four,
unchanged) -- 1154 + 28 new, 0 regressions, 0 new xfails. Matches the developer's own reported
1154 (1125 baseline + 29 of their own) once the slightly different pre-spec-010 baseline
figures in the log are reconciled (`docs/STATUS.md`'s end-of-prior-session figure was 1129, not
1125 -- a small log/STATUS drift pre-dating this spec, not something this review needs to
resolve, since the actual before/after delta for *this* spec's own changes is independently
confirmed clean either way). Re-ran `tests/test_plot.py`/`tests/test_solve.py`/
`tests/test_engine.py` in isolation as well: all 126 pass unchanged, confirming the `over`
sub-grammar refactor (`parse_sampling_clause`/`split_top_words` moved from `plotting.py` into
`syntax.py`) introduced no behavioural change to spec 004's own plot blocks.

## Acceptance criteria

All 18 PASS under independent testing.

1. PASS. `decay` model: `evolve in decay` gives `status ok`, output contains `y(t) =`;
   `y(4 s) =` gives `3.67879 m` (`10*exp(-1) = 3.678794...`, abs 1e-4); `y(0 s) =` gives
   exactly `= 10 m`.
2. PASS. `sho` model: `y(pi) =` gives `-1` (abs 1e-6), `y(pi/2) =` gives `0` (abs 1e-6)
   (`cos(pi) = -1`, `cos(pi/2) ≈ 6e-17`).
3. PASS. `fall` model: `x(2 s) =` and `v(2 s) =` both give `-19.6133 m`/`-19.6133 m/s`
   using this project's own `g = 9.80665 m/s^2` (`-g*2 = -g*2^2/2` coincide exactly at
   `t=2s`), within the spec's own abs-1e-2 tolerance of its quoted `-19.62`.
4. PASS. `y` is undefined/error above the model; below the model it is bound as a function
   (needs an argument); `y(t) ->` shows the formula with `t` free.
5. PASS. `evolve symbolic` gives byte-identical output to plain `evolve` for criteria 1-3.
6. PASS. `pend`'s nonlinear equation: `evolve`/`evolve symbolic`/`evolve numeric` are all
   errors (none silently succeeds); `evolve symbolic`'s wording matches the spec's quoted
   `"No closed-form solution found"` exactly (the other two differ from the spec's
   phase-A-only wording by design -- disclosed deviation 2, confirmed, see below).
7. The second half (wrong-count case, deferred to criterion 8 by the spec's own text) is
   confirmed `ok`, not an error -- `y(0) == 1 m, y'(0) == 1` on the `sho` model is exactly the
   right *count* (one condition each of order 0 and 1), and the same free-dimension reasoning
   independently confirmed for criterion 1 applies equally to `sho`'s own equation. The first
   half (bare `y(0) == 10`, no unit, expecting `"Units do not match"`) is not reproduced --
   independently re-derived as mathematically unreproducible without also breaking criterion 1
   (see deviation re-check above); agree with the developer's own analysis and the parked
   question in `docs/board/decisions.md`'s 2026-10-30 entry. This looks like a genuine
   hand-derivation mistake in the spec itself, in the same vein as several prior specs'
   hand-derived numbers needing a tester correction -- not an implementation defect.
8. PASS. Missing condition: `"sho" needs 2 initial condition(s) for y, has 1`. One too many:
   `"sho" needs 2 initial condition(s) for y, has 3`. Exact text match both times.
9. PASS. `"All equations of \"bad\" must use the same independent variable"`, exact text.
10. PASS. `"Write the highest derivative alone on the left: ..."`, confirmed on the `ode`
    region's own result (the `evolve` region below it separately shows the generic
    `"Fix the errors in the regions of model ... first"`, which is the expected, already-
    established spec-003-style pattern for a region that failed to parse at all).
11. PASS. No `evolve` below: `"No result region for ODE system \"noresult\" below this
    region"`, exact text. An `ode` region placed below `evolve`: confirmed the result is
    unchanged by it (same closed form as without the extra line) and the misplaced `ode`
    region itself errors (no result below it).
12. PASS. A component-free sheet evaluates normally (`tests/test_engine.py`/`tests/
    test_solve.py` both still 100% green, confirmed above); a solve-block model (spec 003)
    and an ODE system with different tags on the same sheet coexist without interaction.
13. PASS. All four `parse_statement` shapes (`model_ode`/`model_ic`/`model_over`/
    `model_result`) give exactly the fields the spec specifies, confirmed field-by-field.
14. PASS. `pend` + `over t from 0 to 1 points 101`, `evolve in pend`: `status ok`, output
    starts `"⇒ numeric solution, 101 points"`; energy `0.5*omega^2 - cos(theta)` (omega
    derived via `np.gradient` on the reported `theta`/`t` columns, the same reasonable
    reading the developer's own tests use for this ambiguous-in-the-spec quantity) stays
    within 1e-3 of `-cos(0.2) ≈ -0.98007` (independently confirmed this constant too) at every
    row; every `theta` satisfies `abs(theta) <= 0.2 + 1e-3`.
15. PASS. `forced` model, 5-point grid: values `5, 1.83940, 0.67668, 0.24894, 0.09158`
    (independently computed via `5*exp(-2t)` at `t=0,0.5,1,1.5,2`) all match within abs 1e-4.
    A 2-point grid gives the same `t=2` value within the same tolerance, confirming the
    integrator's accuracy doesn't depend on how many points are reported.
16. PASS. `t =` after the numeric `evolve` errors the standard range-variable way
    (`"t is a range variable (use table)"`); `table t, y(t)` below gives byte-identical rows
    to the `evolve` region's own table; `y(1) =` gives `0.67668`; a `plot`/`over t`/`show
    y(t)` region below produces one trace with exactly 5 points.
17. PASS. `accuracy 1e-3` still keeps the pendulum's energy check within a looser (1e-2)
    tolerance; `steps 1` gives `"Not converged: stopped after 10 steps (steps limit 1)"`,
    matching the spec's required `"Not converged"` prefix.
18. PASS. `pend` with no `over` line and plain `evolve`: `"over t from ... to ... is needed to
    solve \"pend\" numerically"`, exact text. `decay` + an added `over` line with `evolve
    numeric`: still produces a numeric table even though a closed form exists, confirming
    forcing numeric is honoured.

## Edge cases

All PASS: a function named in `start` but never given an `ode` equation
(`"\"z\" is not an equation of ODE system \"typo\""`, exact text); a genuine two-point
boundary-value attempt (`start y(0)==1`, `start y'(1)==0`) is rejected with a clear
"same point" error, confirming the bug fix disclosed in `docs/board/log.md`'s latest entry is
real and independently reproducible (re-derived from scratch, not trusted) -- before the fix
this exact construction would have silently slipped through per the log's own description, and
it does not here; the independent-variable name reused as an ordinary variable before the
model is untouched until the numeric `evolve` region's own binding (reading order); a huge
initial condition (`1e300`) does not overflow or crash; a complex-rooted characteristic
equation (`y'' + 2y' + 5y == 0`) is accepted and displayed normally, and the real-valued
initial condition still evaluates cleanly; unicode function/variable names (`θ`) work
end-to-end; a genuinely mutually-coupled nonlinear system falls back to numeric cleanly rather
than crashing (see deviation 3 above); division by zero inside an equation's own text produces
a clear (if not especially friendly -- `"Couldn't solve for initial conditions"`) error rather
than a leaked traceback.

## Deviation 4, deep-dived (multiprocessing-based `dsolve` timeout)

Per the task's specific instruction to check this works and doesn't leak processes or break
under pytest:

- **Works correctly under pytest and the project's own test entry points.** Running the
  pendulum's nonlinear `evolve symbolic` under `QT_QPA_PLATFORM=offscreen pytest -q` reliably
  times out at ~1.1-1.2s and is correctly treated as "no closed form found" -- confirmed across
  repeated runs, including inside the full suite alongside everything else.
- **No leaked/zombie child processes while the parent stays alive.** Ran a long-lived guarded
  script that calls the pendulum's `evolve symbolic` three times in a row and then sleeps;
  `ps` shows no leftover `dsolve`-worker processes while the parent is still running, only the
  standard `multiprocessing.resource_tracker` helper process (expected, benign, shared across
  all uses of the module). `proc.join(1.0)` after `proc.terminate()` correctly reaps the child.
- **D1 (low-moderate): a real footgun for any direct library use of `livesheet.engine.Engine`
  from an unguarded top-level script.** `multiprocessing`'s `spawn` start method re-imports and
  re-executes the *main* module's top-level code inside every child process. The project's own
  two shipped entry points (`livesheet/__main__.py`, and the `livesheet` console-script
  wrapper setuptools generates into `.venv/bin/livesheet`) both correctly guard their top-level
  code with `if __name__ == "__main__":`, so the real, shipped product is **not** affected.
  However, a plain script that imports and calls `Engine().evaluate(...)` at module level
  *without* that guard (a very easy thing to write, and `engine/` is explicitly documented as
  "GUI-independent" -- i.e. advertised as usable standalone) will, the moment it hits a
  `dsolve` call that needs the timeout path, have its own top-level code **re-executed inside
  the spawned child**, with two observed failure shapes depending on exactly how the script is
  invoked -- neither is a clean crash, which makes this worse, not better:
  - Invoked via `python3 -` (script piped on stdin, no real file path): the child's own
    `spawn_main` cannot locate a `<stdin>` module and dies with `FileNotFoundError` *inside the
    child*, before ever calling `dsolve`. The parent only sees the pipe closing early
    (`EOFError` on `parent_conn.recv()`), which `_dsolve_timeout` currently treats exactly like
    an ordinary timeout -- it **silently returns "no closed form found"**, even though the real
    cause was an unrelated spawn failure and the equation may well have had a closed form. This
    is the more concerning of the two shapes: a wrong answer, not an error.
  - Invoked as a real, unguarded `.py` file: the child re-executes the *whole script* from the
    top, which calls `Engine().evaluate(...)` a second time, which itself tries to spawn a
    *third* process -- Python's multiprocessing bootstrapping guard catches this and raises
    `RuntimeError("An attempt has been made to start a new process before the current process
    has finished its bootstrapping phase...")` inside that nested call, which propagates up
    through `evaluator.py`'s broad `except Exception` handler and surfaces as a raw,
    unfriendly `RegionResult.error` string instead of either a real answer or a clean
    LiveSheet-style error -- and the script's own (unguarded) output is visibly printed twice.

  Minimal repro (run as a real file, not via `pytest`/the console script):
  ```python
  # bad_script.py -- no `if __name__ == "__main__":` guard
  from livesheet.engine import Engine
  res = Engine().evaluate(enumerate([
      "ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend",
      "start theta(0) == 0.2, theta'(0) == 0 in pend",
      "evolve symbolic in pend",
  ]))
  print(res[2])
  ```
  Running `python3 bad_script.py` prints the `RegionResult`/error output **twice** (and, on a
  first attempt, raised the multiprocessing bootstrapping `RuntimeError` instead) -- the script
  re-ran itself from inside the child process. This is a well-known, general Python
  `multiprocessing`-with-`spawn` caveat (not specific to this engine), and it does not affect
  LiveSheet's own shipped entry points, so it is not a release blocker; but since `odesolver.py`
  is the first module in this codebase to use `multiprocessing` at all, and `engine/` is
  explicitly meant to be importable standalone, this seems worth a one-line note in
  `engine/odesolver.py`'s own module docstring or `docs/STATUS.md`'s "known limits" so a future
  script/notebook/headless-API author (this project's own stated audience for a GUI-independent
  engine) doesn't lose time to it. Not fixing production code myself, per instruction --
  reporting only.

## D2 (moderate, not previously surfaced this explicitly): the per-solve subprocess-spawn
## overhead is large relative to the actual symbolic work, and affects every `evolve` region

Measured directly (guarded real-file scripts, not `pytest`, to isolate from pytest's own
warm interpreter state): the spec's own simplest example (`decay`, one trivial first-order
linear equation that `dsolve` itself solves in well under a millisecond) takes **~0.6-0.7
seconds wall-clock** end to end through `Engine().evaluate(...)`, purely from spawning a fresh
interpreter subprocess, piping the equation/ICS over, and tearing it down again. The two-
equation coupled `fall` example (deviation 3's one-function-at-a-time dependency-order
approach spawns one subprocess *per function*) takes **~1.2 seconds**. This is not a
correctness defect -- deviation 4's own reasoning (a `threading`-based timeout cannot actually
stop a runaway `dsolve` call, so a process is the only option that can) is sound and was
independently re-confirmed above to work correctly. But the spec's own edge cases section
already flags "GUI thread freeze on a slow model" as a known, accepted limitation for a
*genuinely* slow model; this finding is different and additional: **every** `evolve`/`evolve
symbolic` region, including the fastest, most trivial possible one, now costs over half a
second of blocking UI-thread time purely from process-spawn overhead that a direct (in-process)
`dsolve` call would not have paid at all for these examples. Per spec 007's own "Calculating..."
UX (a >300ms synchronous pass gets a visible flash before "Ready"), this means a sheet with
even one simple `ode`/`evolve` region will visibly flash "Calculating..." on every single
recalculation (every keystroke-triggered re-evaluation of the whole sheet), where a sheet with
only ordinary math/solve-block regions of comparable complexity would not. This seems like a
genuinely new, measurable UX cost worth the manager's attention and Theo's awareness,
separate from (and in addition to) the already-accepted "slow nonlinear model" limitation --
not something I'm asking to be fixed before merge (the correctness tradeoff deviation 4 made is
reasonable), but flagging explicitly since the deviation's own writeup in `docs/board/log.md`
focuses on *why a process is needed to time out slow cases* and doesn't mention that it also
adds this fixed cost to every fast case.

## IP red flags

**None introduced by this spec.** Grepped `livesheet/engine/odesolver.py`, the touched parts
of `livesheet/engine/syntax.py`/`evaluator.py`/`plotting.py`, and `tests/test_odesolver.py` for
vendor names (`Mathcad`, `Maple`, `Mathematica`, `Wolfram`, `MATLAB`, `PTC`, `Odesolve`) --
found none. All new keywords (`ode`, `start`, `over`, `evolve`), field names, and error strings
are original and match the spec's own IP check; `dsolve`/`solve_ivp` are used exactly as
SymPy's/SciPy's own public BSD-licensed docs describe, consistent with the spec's citations.

**Two pre-existing (not introduced by this spec) vendor-name mentions found while grepping the
wider `livesheet/engine/` tree for this review**, in the same category as the `Crosshair`
docstring already found and fixed for spec 009 (`docs/board/log.md`, 2026-10-29) -- apparently
missed by that earlier cleanup pass because they're in different files:
- `livesheet/engine/evaluator.py:32`: `"""Mathcad convention: log is base 10, ln is
  natural."""` (docstring on `_log`).
- `livesheet/engine/units.py:8`: `"Angles are dimensionless (``deg = pi/180``), as in
  Mathcad."` (module docstring).

Both confirmed present since the project's very first commit (`d430428`, `git log -S` on each
exact string), not touched by this spec's changes. Flagging per the task's own instruction to
report IP red flags noticed in the code, even when out of this spec's own scope -- same
remediation as the `Crosshair` fix (describe the convention in LiveSheet's own words, drop the
vendor name) would resolve both.

## Coverage gaps

- **No real-window/computer-use pass this session.** No `computer_*` tool is available in this
  session's tool set (confirmed: not present at all, and this sandbox is a headless Linux VM --
  `uname -a` shows Linux, no `osascript`/`screencapture`, i.e. not Theo's Mac), so I could not
  open LiveSheet, insert an `ode`/`start`/`evolve` region, or watch it evaluate live, per
  CLAUDE.md's testing convention and the task's explicit request not to skip this silently.
  Everything above was verified only through `Engine().evaluate([...])` (headless, programmatic)
  -- this is the same production evaluation path a real GUI region's recalculation uses (no new
  GUI code was needed for this spec per its own architecture section: the numeric case's table
  reuses the existing `table`-statement rendering, confirmed unchanged by the full GUI suite
  passing), but it is not the same as watching it on screen. A real pass should still cover:
  typing an `ode`/`start`/`over`/`evolve` region by hand and watching recalculation (and
  specifically feeling D2's extra latency on a real machine); the pretty-printing of
  `diff(y(t), t, 2)` inside an `ode`/`start` line as `d²/dt² (y(t))` (the spec's own noted
  "pleasant side benefit" of the existing calculus pretty-printer, not separately tested here);
  a numeric `evolve` region's inline table rendering and a `plot` region fed from a bound
  numeric function, visually.
- `format_output`-equivalent concerns don't apply here (no new GUI widget), but the exact
  behaviour of a *very* large/deeply-nested closed-form result's on-screen rendering (the
  spec's own edge case, "displayed and usable exactly as any other large symbolic result
  already is") was not separately re-verified pixel-wise, only that `format_expr` doesn't
  error on a moderately complex complex-valued result (the `cplx` test case above).
- The exact wording of the division-by-zero error (`"Couldn't solve for initial conditions"`)
  is not specified anywhere in the spec and isn't part of any numbered criterion; noted as a
  minor, non-blocking UX rough edge rather than a defect.
- A separate, pre-existing (spec-004-era, confirmed via `git log -S`) minor inconsistency was
  noticed but is **not** a spec 010 defect, only reused faithfully by it: both `plotting.py`'s
  own `over` line and `odesolver.py`'s new `over` line reject `"from 0 to 10 m"`/`"from 0 to
  2 s"` (a bare, unit-less zero mixed with a dimensioned endpoint) as a unit mismatch, instead
  of applying the project's own established "zero fits any dimension" convention used
  elsewhere (e.g. this same spec's own condition-point matching in `odesolver.build()`). Spec
  010's own worked examples always write an explicit unit on both `over` endpoints (`"over t
  from 0 s to 8 s"`), so none of the 18 criteria are affected; flagging only because I noticed
  it while independently exercising `over`, for whichever spec eventually revisits that
  sub-grammar, not assigning it to this spec's defect list.

## Recommendation

Spec 010 is functionally sound: all 18 acceptance criteria plus every edge case in its own
"Edge cases" section hold under independent black-box testing
(`tests/test_odesolver_review.py`, 28 cases), the six disclosed deviations are each
independently verified reasonable and correctly implemented (including a from-scratch
re-derivation of the one genuinely unreproducible criterion, 7's first scenario, confirming the
developer's own mathematical analysis rather than trusting it), the one disclosed bug fix
(two-point boundary rejection) is independently confirmed real and fixed, and the full suite is
stable at 1182 passed / 2 xfailed / 4 pre-existing-and-unrelated failures (1154 + 28 new, 0
regressions, confirmed via an independent before/after checkout rather than trusting the
developer's own git-stash claim). Spec 004's own plot tests (`tests/test_plot.py`) and spec
003's own solve-block tests (`tests/test_solve.py`) both still pass unchanged after the shared
`over` sub-grammar refactor. No defect blocks merging. Two non-blocking findings deserve the
manager's/Theo's attention before or shortly after merge: D1 (a general but real
multiprocessing/`spawn` footgun for any unguarded direct script use of the GUI-independent
`engine/` package -- does not affect LiveSheet's own shipped entry points) and D2 (every
`evolve`/`evolve symbolic` region, even the simplest possible one, now costs roughly 0.6-1.2
seconds of blocking UI-thread time purely from subprocess-spawn overhead, which will visibly
trigger spec 007's "Calculating..." flash on sheets that previously wouldn't have shown it).
Two pre-existing (not spec 010) `"Mathcad"` mentions in code-comment docstrings
(`evaluator.py`/`units.py`) were found and are flagged for the same cleanup already applied to
the `Crosshair` docstring. No real-window/computer-use pass was possible this session (no
`computer_*` tool available, confirmed headless Linux sandbox, not Theo's Mac) -- this is a
standing gap, explicitly called out here rather than skipped silently, same as specs 006-009.
