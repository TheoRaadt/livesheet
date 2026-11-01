# Review 010: ODE solving, initial-value problems, symbolic with numeric fallback (tester, black-box)

Spec: `docs/board/specs/010-ode-solving.md` (backlog item 14), phases A (symbolic via SymPy
`dsolve`+`ics`, units, binding, errors) and B (numeric fallback via SciPy `solve_ivp`, `over`
sampling, binding of the numeric case, settings). Both phases were implemented together by the
developer and independently verified by the manager (`QT_QPA_PLATFORM=offscreen pytest -q`: 1160
passed, 2 xfailed, 0 failed at the time) and accepted — see `docs/board/decisions.md`'s "Decided
2026-10-30 (manager, spec 010 implementation)" entry. New/changed files under test:
`livesheet/engine/odesolver.py` (new), `livesheet/engine/sampling.py` (new), `livesheet/engine/
syntax.py`, `livesheet/engine/evaluator.py`, `livesheet/engine/plotting.py`. Developer's own tests:
`tests/test_odesolver.py` (31 cases).

Process note on this review's own starting point, for the record: a previous tester session was
started on this exact task last session and was killed mid-tool-call when Theo hit his usage limit.
It never got to log a handoff or write a review, but it *had* already written (and, per the file's
own header comment, derived independently from the spec's own acceptance criteria and worked
examples, "before reading `livesheet/odesolver.py`'s own `tests/test_odesolver.py`") an untracked
`tests/test_ode_blackbox.py` with 38 cases, already all green, sitting in the working tree when
this session started. Per this project's own IP-cleanroom instinct of not blindly trusting work left
behind without re-verifying it, this review audited that file line by line against the spec's own
wording (not against the developer's `test_odesolver.py`, which was deliberately not consulted
again either) before extending it, rather than accepting it on faith: independently re-derived and
checked the file's own hand-computed numbers (exponential decay, SHO `cos`/`sin`, free-fall `g`),
re-ran its own direct `scipy.integrate.solve_ivp` cross-check for the pendulum (criterion 14) by
hand, and independently re-verified its criterion 7 and criterion 18 "spec has a flaw/typo" claims
from scratch against real SymPy myself (below) rather than trusting either the file's comments or
the manager's decisions.md entry. Found it accurate and well-targeted at the spec's own criteria;
extended it with 6 new cases this session: a real headless-GUI pass (3 cases, see below), a missing
default-points check (1 case), and two newly-found defects (2 cases, see Defects). Final file:
`tests/test_ode_blackbox.py`, 44 cases.

## Independent re-verification of criterion 7's drop (from scratch, not trusting prior analysis)

Criterion 7 as literally written: `start y(0) == 10 in decay` (criterion 1's model, `tau := 4 s`,
dimensionless `y(0)` this time) should give `"Units do not match"`. Both the developer and the
manager found this does not reproduce, reasoning that `y`'s own dimension cancels out of the
equation's only real dimensional constraint. Re-derived this independently, outside LiveSheet
entirely, with a bare `sympy.physics.units` call (not through the engine's own `measure()`/
`Measured` wrapper at all, to rule out a tester-copies-the-same-blind-spot risk):

```python
import sympy as sp
from sympy.physics.units import second, meter
from sympy.physics.units.systems.si import SI

t = sp.Symbol('t', real=True)
tau = 4*second
y = sp.Function('y')
eq = sp.Eq(sp.Derivative(y(t), t) + y(t)/tau, 0)

sol_a = sp.dsolve(eq, y(t), ics={y(0): 10*meter})   # criterion 1, dimensioned
sol_b = sp.dsolve(eq, y(t), ics={y(0): 10})         # criterion 7, dimensionless
```
Result: `sol_a = Eq(y(t), 10*meter*exp(-t/(4*second)))`, `sol_b = Eq(y(t), 10*exp(-t/(4*second)))`
— `dsolve` succeeds identically either way, no exception, no inconsistency raised by SymPy's own
dimensional system at any point. Further, substituting a concrete time into each and running
`SI._collect_factor_and_dimension` directly confirms both are internally dimensionally
self-consistent (`sol_a` carries `Dimension(length)`, `sol_b` carries `Dimension(1)` — whatever
dimension `y`'s own initial condition happened to declare, carried through unchanged, never
checked against anything else). This matches the mathematical reasoning given in decisions.md
exactly: for this specific homogeneous linear first-order ODE, the equation only constrains `tau`
and `t` to share a dimension (both appear as `.../tau` and `d/dt` next to each other); `y`'s own
dimension never appears in a constraint by itself, so any dimension (including none) is equally
"consistent" for `y(0)`. **Independently confirmed: criterion 7's premise does not hold under real
SymPy; the manager's drop of this criterion is correct**, and no sound, general unit check could
single out this specific case as an error without also rejecting criterion 1's own passing case
(verified above: the same `dsolve` call with `10*meter` and with `10` both succeed, so a check
cannot distinguish "the good case" from "the bad case" by any property of the solve step itself).

One side-finding from doing this check myself rather than trusting the write-up: while confirming
*this* criterion's premise doesn't hold, I found a **different, real gap** in the same area —
unit-consistency checking *across* a single function's several initial-condition orders (not
addressed by criterion 7 or 8, which only ever vary one single condition) is missing entirely. See
Defects below; this is a genuine implementation gap, not a second case of "the spec's own example
was unverified", and I checked it is clearly distinct from criterion 7's issue before reporting it.

## Tests added

`tests/test_ode_blackbox.py` (44 cases, inherited+audited 38 + 6 new this session, all pass),
written from spec 010's own acceptance criteria 1-18, its edge cases, and the worked examples, using
only `Engine().evaluate()`, `parse_statement()`, and (for the new GUI cases) `Worksheet`/
`add_region`/`recalculate()`/`SheetDocument` — never the developer's own `odesolver.py` internals
directly. Deliberately different exercise paths vs. `tests/test_odesolver.py`:
- Every numeric example is hand-derived from the closed-form fact being tested (`5*exp(-2t)`,
  `cos(t)`, free-fall `-0.5*g*t²`) rather than quoting the spec's own pre-computed decimal strings
  without re-deriving them; criterion 14 (pendulum energy conservation) is additionally cross-checked
  against a direct, independent `scipy.integrate.solve_ivp` call made in the test file itself (not
  through LiveSheet at all) — this project's testing skill's own recommended "independent route"
  using an already-approved dependency as a calculator, not a new one.
- A genuine, deliberately different unit-mismatch probe beyond criterion 7 itself: a model where the
  *equation's own* coefficient actually is dimensionless (`diff(y(t),t) + y(t) == 0`, as opposed to
  criterion 1/7's `y(t)/tau`), confirming a *real* inconsistency (here surfacing only once `t` is
  used with an actual unit) is still caught downstream, same "checked at use" pattern already
  accepted for spec 003.
- Three new headless-but-real-GUI-code-path cases (`test_gui_*`): a numeric `evolve` region driven
  through a real `Worksheet`/`MathRegion`/`recalculate()`, checked to render through the exact same
  `format_table`-based HTML the `table` statement already uses, not just checked at the
  `RegionResult` level; a symbolic `evolve` region's bound function used by a real `PlotRegion` in
  the same `Worksheet`, confirmed to produce a real trace; and a full `.lsheet` save/load round trip
  of an ODE sheet through a real temp file and `Worksheet.load_document()`, confirmed the reloaded
  sheet still evaluates (not just that the text survives).
- Two new defect-reproduction cases (cross-order IC dimension mismatch, symbolic and numeric) — see
  Defects.
- One new case for `over`'s default point count (101) when the `points` word is omitted entirely
  (not just given its own default inside the sub-grammar), which neither test file previously
  exercised explicitly.

Coverage: all 18 numbered acceptance criteria (including both the closed-form and numeric-fallback
sides of criteria 5/6/18), the parsing criterion (13), every edge case named in the spec's own "Edge
cases" section (unknown function in `start`, two-point boundary rejection, the `evolve` trailing-word
error, an implicit-only closed form treated as a failure, a purely-imaginary-root oscillator still
rendering as real `sin`/`cos`), plus: a higher-order single equation's first-order-system reduction
cross-checked numerically against its own known closed form (SHO vs `cos`); the `over`-start-point-
must-match-the-shared-initial-point rule (not explicitly numbered in the spec but required by its
own wording, and not in the developer's own test file either — confirmed working); a duplicate-order
condition (`y(0)==1, y(0)==2`) silently keeping the *last* value with no warning (see Defects, minor
item); a missing-middle-order gap (`y(0)`, `y''(0)` given, `y'(0)` missing for a 2nd-order equation)
correctly rejected with the "one condition of each order 0..N-1" wording.

## Results

`QT_QPA_PLATFORM=offscreen pytest -q`, run three times for stability from a clean shell: **1258
passed, 2 xfailed, 0 failed** every time (1252 going into this session — which already included the
previous tester's untracked 38 — plus this session's 6 new cases, 0 regressions). Isolated run of
just this spec's own file: `tests/test_ode_blackbox.py`, 44 passed.

Environment note (not a code defect, the same recurring hazard already logged several times in
`docs/board/log.md`): mid-session, the full suite hard-failed collection on ~30 unrelated files with
`ModuleNotFoundError: No module named 'livesheet'` despite `pip show livesheet` resolving fine
directly; no concurrent `pip`/reinstall process was visible via `ps aux` at the time. Recreating
`.venv` from scratch (the project's own documented fix) resolved it immediately, consistent with
every prior session that hit this. Separately, later in the session, two unrelated tests in
`tests/test_spec011_side_panel_greek_blackbox.py` failed once and then passed on the very next
re-run with no change on my part — this file did not exist at the start of this session and was
evidently being actively written by a concurrent tester session on spec 011 (per this task's own
framing: "this count also includes unrelated spec-011 work in progress elsewhere"); confirmed this
spec's own two test files (`tests/test_ode_blackbox.py`, `tests/test_odesolver.py`, 75 cases
together) pass in isolation regardless, and are unaffected by and unrelated to that transient
failure.

## Acceptance criteria

1. PASS. First-order decay with units: `y(t) =` present in the closed-form output;
   `y(4 s) = 3.67879 m` (abs 1e-4, matches `10*exp(-1)` independently); `y(0 s) = 10 m` exactly.
2. PASS. Second order SHO: `y(pi) = -1` (abs 1e-6), `y(pi/2) = 0` (abs 1e-6), matching `cos(t)`.
3. PASS. Coupled free fall: `x(2 s)` and `v(2 s)` both `≈ -19.6133` (abs 1e-2 against the spec's
   `-19.62`; independently recomputed as `-0.5*g*t²`/`-g*t` with this project's own `g = 9.80665
   m/s²`).
4. PASS. A region above the model referencing `y` sees it as a free symbol, not an error, not an
   older binding; a region below sees the bound callable (`y(2 s)` evaluates); `y(t) ->` shows `t`
   free in the formula.
5. PASS. `evolve symbolic` byte-identical output to plain `evolve` whenever a closed form exists,
   checked for both the decay and free-fall models.
6. PASS. No closed form (pendulum): `evolve symbolic` gives `"No closed-form solution found..."`;
   plain `evolve`/`evolve numeric` with no `over` line give the *superseding* (since both phases
   shipped together, a disclosed and accepted deviation) `'over t from ... to ... is needed to
   solve "pend" numerically'` instead of phase A's placeholder text, which per the developer's own
   report never actually exists in the shipped system.
7. DROPPED, independently re-verified from scratch above — see the dedicated section. Confirmed:
   does not reproduce under real SymPy; correctly accepted by the manager as an unverified flaw in
   the spec's own worked example, not an implementation gap.
8. PASS. Missing condition: `'"sho" needs 2 initial condition(s) for y, has 1'`. Extra condition:
   `'"sho" needs 2 initial condition(s) for y, has 3'`, both exact-string matches.
9. PASS. Mismatched independent variable (`t` vs `s`) across two `ode` lines of one model: exact
   error `'All equations of "bad" must use the same independent variable'`.
10. PASS. `ode y(t) + diff(y(t), t) == 0` (derivative not alone on the left): error starts
    `"Write the highest derivative alone on the left"`.
11. PASS. No `evolve` below `ode`/`start`: `'No result region for ODE system "noresult" below this
    region'` on every region of that incomplete model; an `ode` line placed below `evolve` is
    confirmed unused (the model solves with only the equations declared above the result).
12. PASS. A plain define/evaluate sheet is unaffected; a solve-block model (spec 003) and an ODE
    system with different tags coexist on one sheet without interacting.
13. PASS. All four parsing shapes (`model_ode`, `model_ic` with its exact `conditions` tuple list,
    `model_over` with all four fields, `model_result` with `goal="ode_numeric"`) match exactly.
14. PASS. Pendulum numeric fallback: output starts `"⇒ numeric solution, 101 points"`, 101 rows;
    energy `0.5*omega² - cos(theta)` (omega derived from the table's own `theta` column via central
    differences, not from any internal state) stays within 1e-3 of `-cos(0.2)` throughout, and
    `|theta| <= 0.2 + 1e-3` holds for every row. Additionally cross-checked against a direct,
    independent `scipy.integrate.solve_ivp` call (same tolerance), matching to within 1e-4.
15. PASS. `forced` model: numeric table at `t = 0, 0.5, 1, 1.5, 2` matches `5*exp(-2t)` to abs 1e-4,
    and matches the spec's own quoted decimals (`5, 1.83940, 0.67668, 0.24894, 0.09158`) to the same
    tolerance; a 2-point grid gives the same `t=2` value within tolerance, confirming point-count
    independence of accuracy.
16. PASS. After a numeric `evolve`: `t =` errors the usual "range variable" way; `table t, y(t)`
    gives the same 5 rows the `evolve` region's own table reports; `y(1) = 0.67668` (abs 1e-4); a
    `plot` with `over t`/`show y(t)` produces one 5-point trace.
17. PASS. Looser `accuracy 1e-3` still passes the pendulum's own energy check; `steps 1` (far too few)
    gives an error starting `"Not converged"`.
18. PASS, including the spec's own typo in its worked example. `evolve in pend` with no `over` line
    gives the exact `'over t from ... to ... is needed to solve "pend" numerically'`; forcing
    `evolve numeric` on the `decay` model (which *has* a closed form) still produces a numeric table
    — independently reproduced that the spec's own literal example line, `over tau from 0 s to 8 s
    in decay`, errors (`'"over" must use the independent variable "t"'`, since `tau` is a parameter
    of that model, not its independent variable `t`), and that the corrected `over t from 0 s to 8 s
    in decay` gives the stated numeric result. This is a genuine error in the spec's own prose
    example, not an implementation defect — confirmed independently, not merely carried over from
    the developer's report.

## Edge cases

All PASS as specified: a `start`/`over` line naming a function with no `ode` equation
(`'"z" is not an equation of ODE system "m1"'`); two-point boundary conditions rejected
(`'All initial conditions of "m2" must be given at the same point'`); `evolve fast` (unrecognised
trailing word) rejected with the exact `"evolve takes 'symbolic', 'numeric' or nothing"`; an
implicit-only closed form (`y*y' == -t`, sign-ambiguous in `y`) correctly treated as "no closed form
found", same as a genuine `NotImplementedError`; `accuracy`/`steps` validation errors for an
out-of-range value; a purely-imaginary-root oscillator (`diff(y,t,2) + 4*y == 0`) still renders as a
real, usable `sin`/`cos` formula, not raw complex numbers; `evolve` placed textually above its own
model's `ode`/`start` lines does not look ahead — it sees no equations at all, the same strict
reading-order rule spec 003 already established; the multi-function output separator is confirmed to
be `"; "`, not `", "` (`"x(t) = ...; v(t) = ..."`, never `"x(t) = ..., v(t) = ..."`).

Two additional edge cases found and checked this session, not named by the spec but implied by its
own wording:
- `over`'s starting point must equal the model's shared initial-condition point (the spec's own
  "Also directly reports an inline table..." + "`over` line... Declares both the reporting grid...
  and (by matching `X` against the model's independent-variable name) a consistency check" wording
  implies this); confirmed rejected with `'"over" must start at the shared initial point of
  "pendX"'` when given a different starting point.
- `start y(0) == 1, y(0) == 2 in dupe` (the same order given twice for one function): **not**
  rejected — silently keeps the *last* value (`2`) with no warning or error, count-checked as if
  only one condition existed (which, after the dict collapses the duplicate key, it does). Noted as
  a minor finding below, not a blocking defect.

## Defects

**D1 (moderate) — a single function's initial conditions at different derivative orders are never
checked against each other for dimensional consistency, in either solving path, despite the spec's
own architecture section explicitly asking for this check.**

Spec text ("Fits current architecture?" > `engine/odesolver.py`): *"unit handling (checking the
equation's and each condition's dimensions **once, symbolically, before calling into SymPy/
SciPy**) uses the existing `units.measure`/`UnitError`, same one-time-check spirit as `solver.py`'s
own dimension handling."* This describes an up-front check across a model's conditions, not merely
"whatever SymPy happens to error on afterward."

This is a *different* gap from criterion 7 (which only ever varies a single condition on a model
where no cross-value dimensional constraint exists at all). Here, two conditions **of the same
function**, at different orders, are given genuinely incompatible dimensions — a case no property
of "this one equation has no real constraint on `y`" can excuse, since the two conditions are
combined with each other directly by the characteristic-equation solution (e.g. `A*cos(t) + B*sin(t)`
with `A`, `B` fixed by `y(0)` and `y'(0)` respectively) regardless of the equation's own unit
structure.

Symbolic repro (minimal):
```python
from livesheet.engine import Engine
res = Engine().evaluate(enumerate([
    "ode diff(y(t), t, 2) + y(t) == 0 in shoX",
    "start y(0) == 1 m, y'(0) == 1 in shoX",   # 1 m vs a bare, nonzero 1 (dimensionless)
    "evolve in shoX",
]))
print(res[2].output)
# => "⇒ y(t) = m·cos(t) + sin(t)"   -- status "ok", no error anywhere, but this formula adds a
#    metre-valued term to a dimensionless term: no single unit describes "y" here, it is simply
#    wrong, and will itself error ("Units do not match") only if and when it is later evaluated
#    at a NONZERO point (e.g. `y(1 s) =`) -- never at the `evolve` region that built it.
```
Numeric repro (worse: never errors at all, anywhere):
```python
res = Engine().evaluate(enumerate([
    "ode diff(y(t), t, 2) + y(t) == 0 in shoNum",
    "start y(0) == 1 m, y'(0) == 2 s in shoNum",  # 2 SECONDS used as an initial slope/velocity
    "over t from 0 to 1 points 3 in shoNum",
    "evolve numeric in shoNum",
]))
print(res[-1].output, res[-1].rows)
# => "⇒ numeric solution, 3 points", rows [['0', '1 m'], ['0.5', '1.83643 m'], ['1', '2.22324 m']]
#    -- status "ok", a perfectly plausible-looking table, built by silently discarding the "s" unit
#    and using the bare magnitude 2 as the initial slope. `odesolver.solve_numeric`'s own
#    `func_dims[name] = value.dims` is only ever set `if order == 0`; every higher-order
#    condition's declared unit is read (for its magnitude) and then never checked against anything.
```
Reproduced in `tests/test_ode_blackbox.py::test_defect_symbolic_cross_order_ic_dimension_mismatch_not_caught_at_solve_time`
and `::test_defect_numeric_higher_order_ic_dimension_never_checked` (both pass as *confirmations of
the gap*, documenting the current behaviour for the manager/developer to decide on, not xfails).

Suggested fix for the developer (not applied by this review, per instruction): when gathering a
function's conditions in `odesolver.build()`, derive the *expected* dimension of each higher order
from the order-0 condition's own dimension divided by the independent variable's assumed dimension
(itself inferred from, e.g., the `over` line's or another equation's use, when available), and raise
`UnitError("Units do not match")` up front if a given condition's parsed dimension conflicts; at
minimum, for the numeric path, explicitly re-derive `func_dims` from *every* order's condition (not
just order 0) and reject a mismatch there, since that path currently has no cross-check of any kind.

**Minor finding (not filed as a defect; informational) — a duplicate derivative order in one `start`
line silently keeps the last value.** `start y(0) == 1, y(0) == 2 in dupe` on a first-order model
gives `y(t) = 2*exp(-t)` with no error or warning that the first `y(0) == 1` was silently discarded
(`odesolver.build()`'s `conditions[fname][order] = (point_text, value_text)` is a plain dict
assignment, so a repeated key simply overwrites). Likely a simple copy/paste typo scenario for a
real user (e.g. writing `y(0) == 1, y(0) == 2` instead of `y(0) == 1, y'(0) == 2`), worth a cheap
"duplicate order N for <f>" check, but low severity — does not corrupt or mis-render anything, just
silently keeps the last-written value, matching ordinary last-assignment-wins behaviour already
accepted project-wide for a repeated plain `x := 1 ... x := 2` definition.

## Process note

The manager's own `docs/board/decisions.md` entry ("Decided 2026-10-30 (manager, spec 010
implementation)") correctly discusses criterion 7 by name and content throughout, but the
*companion* `docs/board/log.md` entry from the same date mislabels the same discussion as
**"Criterion 2 (manager's own call...)"** — criterion 2 is the unrelated second-order SHO closed-form
case; the described content (the dimensionless `y(0)` drop) is unambiguously criterion 7's. A minor,
easily-corrected cross-reference typo in the log, not a code defect, but flagged here since this
project's process explicitly treats `decisions.md`/`log.md` as the durable record future sessions
read; worth a one-line fix next time that entry is touched.

## IP red flags

None found. Grepped `livesheet/engine/odesolver.py`, `livesheet/engine/sampling.py`, and the touched
parts of `livesheet/engine/syntax.py`/`evaluator.py`/`plotting.py` for vendor names (including the
specific policy-forbidden `Odesolve` construct named only in the spec's own clean-room paragraph)
and found none anywhere in code, comments, or user-facing strings. All new keywords (`ode`, `start`,
`over`, `evolve`/`evolve symbolic`/`evolve numeric`) and error strings (`"Write the highest
derivative alone on the left: ..."`, `'Use "start f(point) == value" ...'`, `"<name>" needs N initial
condition(s) for <f>, has M`, `"All equations of ... must use the same independent variable"`, `"No
closed-form solution found for ODE system ..."`, `"over ... is needed to solve ... numerically"`,
`"Not converged: ..."`) are original and generic, consistent with the spec's own IP check. The one
pre-existing nominative mention found by the grep, `# Mathcad convention: log is base 10, ln is
natural` in `evaluator.py`, predates this spec entirely (an existing comment on the unrelated `_log`
builtin, not touched by spec 010's diff) and is the same already-accepted nominative-mention pattern
used elsewhere in this codebase's comments — not a new flag. The small prime-mark notation
(`y'(0)`, `y''(0)`) the spec itself flagged for the manager is implemented exactly as specced,
scoped only to `start` lines, confirmed by grep that `'` is not used anywhere else in the grammar.
The two open patent-search/pre-1.0-legal-review flags the spec itself carried forward from spec 003
are unchanged by this review (no new information either way) and remain open for the project's own
pre-1.0 process, not something a test review can resolve.

## Coverage gaps

- **No real-window/computer-use pass this session.** This session's tool set did not include any
  `computer_*` tool (confirmed by checking the available tool definitions directly, not assumed) —
  unlike some earlier reviews in this series that explicitly had computer-use access, this one did
  not, so Theo's standing instruction to also drive the real app on his Mac (open a sheet, type an
  `ode`/`start`/`evolve` model, watch the numeric table and the plot render on screen, open/close the
  window) could not be carried out this session. Everything in this review was verified headlessly
  (`QT_QPA_PLATFORM=offscreen`), including three new tests (`test_gui_numeric_ode_result_renders_
  as_a_real_table_region`, `test_gui_symbolic_ode_result_usable_in_a_real_plot_region`,
  `test_gui_lsheet_round_trip_of_an_ode_sheet`) that exercise the real `Worksheet`/`MathRegion`/
  `PlotRegion`/`SheetDocument` production code paths end to end (not just `Engine().evaluate()`
  directly) — this is a materially stronger check than the engine-only black box above, but it is
  still not the same as watching pixels on a real screen. A real pass should still specifically
  watch: a numeric `evolve` region's inline table rendering (column alignment, monospace font, the
  `⇒ numeric solution, N points` line above it); a plot fed by a bound ODE function's trace actually
  drawing a curve, not just reporting the right point count; and the `⚠` error marker/colour for one
  of the error cases above (e.g. the "Not converged" case) actually appearing on a region in a real
  window.
- D1's numeric-path variant (cross-order IC dimension never checked) means there may be *other*,
  not-yet-found cases where a unit mistake in an ODE model's conditions produces a plausible-looking
  but silently wrong result rather than an error; this review found and reported the two clearest
  repros but did not attempt an exhaustive search of the space (e.g. a 3rd-order equation with three
  conditions in three different, mutually-inconsistent units was not tried).
- The documenter has explicitly not yet touched spec 010 (confirmed in `docs/board/log.md`'s
  2026-10-30 documenter entry: "did not touch spec 010 ... which is implemented but not yet
  independently reviewed"), so there is no end-user manual page for `ode`/`start`/`over`/`evolve`
  yet to cross-check error-message wording against; not a gap in this review, just noting the next
  step is still open.
- Performance/long-run behaviour (the spec's own flagged "GUI thread freeze on a slow model" known
  limitation, explicitly out of scope "not solved here") was not probed — consistent with the spec
  itself deferring it, not a defect.

## Recommendation

Spec 010 (ODE solving, phases A+B) is functionally sound: all 18 numbered acceptance criteria hold
under independent black-box testing except the one already-accepted drop (criterion 7), which this
review re-verified from scratch against real SymPy and confirms is correctly dropped — the manager's
mathematical reasoning is sound and not an implementation gap. The spec's own worked-example typo in
criterion 18 (`over tau ...` instead of `over t ...`) was likewise independently reproduced and
confirmed to be the spec's error, not the implementation's. One genuine, moderate defect was found
and is new to this review (D1: a single function's several initial-condition orders are never
dimensionally cross-checked, in either the symbolic or numeric path, despite the spec's own
architecture section asking for exactly this check up front) — not a blocker for any of the 18
numbered criteria, but a real correctness gap worth a developer follow-up, especially for the
numeric path's variant which never surfaces any error at all. One minor, non-blocking finding
(duplicate-order conditions silently keep the last value) is noted for awareness. The full suite is
stable at 1258 passed / 2 xfailed / 0 failed across three consecutive runs (1252 going in, 6 new this
session). No IP red flags found in the new/changed code. A real-window manual pass on Theo's Mac is
still needed before calling spec 010 fully verified end-to-end — this session had no computer-use
tool available to do it, so it remains an open, explicitly-flagged gap rather than something silently
skipped.
