# Review: calculus / engineering-calculation correctness coverage (tester, black-box)

Not spec-driven: requested directly by Theo to broaden correctness coverage of the already-
implemented `diff`/`integrate`/`limit`/`series`/`collect`/`partfrac`/`apart` keywords in
`livesheet/engine/evaluator.py` (there is no `docs/board/specs/*.md` for this feature; it predates
the spec-driven workflow). `tests/test_engine.py` previously had 3 lines of coverage for
`diff`/`integrate`; `tests/test_ranges*.py`, `tests/test_matrices*.py`, `tests/test_solve*.py`,
`tests/test_plot*.py` already cover ranges/tables, vectors/matrices, solve blocks and plots and
were not touched.

## Sources used

No WebSearch tool was available in this tester session (the tool was not in my toolset), so no
public page was fetched or read for this review. Every expected value in the new test file was
worked out independently from standard calculus rules (power/product/quotient/chain rule;
u-substitution and integration by parts; standard limit forms; Taylor/Maclaurin series) and
cross-checked against SymPy itself, which is already a project dependency -- the most reliable
ground truth available, per the project's own testing guidance. `docs/calculus-10th-edition-
anton.pdf` and `docs/Engineering With Mathcad.pdf` were never opened, read or referenced.

As a second, fully independent ground truth (per a mid-task request from Theo via the manager),
every derivative/integral/limit/series/engineering-unit expected value used in
`tests/test_calculus.py` was additionally re-derived numerically in Scilab (local install,
`/Applications/scilab-2026.1.0.app`, open source GPL/CeCILL; run headlessly with
`scilab-cli-bin -nb -f <script>`) using plain central finite differences for derivatives,
Scilab's own `integrate()` for definite integrals, direct evaluation close to the limit point for
limits, and direct polynomial-vs-function evaluation for the series truncations -- all written
from scratch for this check, not copied from any Scilab documentation or example. All ~30 values
(derivatives D1-D10, integrals I1-I8, limits L1-L8, series S1-S4, engineering E1-E5) matched the
values independently derived by hand and already used in the test file, to the precision finite
differences allow; no disagreement between SymPy/LiveSheet and Scilab turned up anywhere. (No
Wolfram/Mathematica tool was used, per instruction.)

## Tests added

`tests/test_calculus.py` (new, 43 tests: 39 passing + 4 strict `xfail` documenting open defects),
independent of reading `evaluator.py`'s calculus branch beyond the public keyword syntax already
documented in `livesheet/engine/syntax.py`'s module docstring and demonstrated by the existing
`test_calculus` in `tests/test_engine.py`. Covers:
- Derivatives: polynomials, product rule, quotient rule, chain rule, trig (checked both
  symbolically and numerically against `math.cos`/`math.sin`), `exp`/`ln`/base-10 `log`, `sqrt`,
  a power tower (`x^x`), differentiation w.r.t. a named variable among several, auto-detected
  single free variable, derivative w.r.t. an unrelated variable (0), and the friendly
  "needs a variable" error when two free variables and none is named.
- Integrals: polynomials, an integral needing a u-substitution internally, two needing integration
  by parts, a rational integral giving `atan`, definite integrals via the function-call form, and
  a label-independent numeric cross-check for `integrate(1/x, x)` (differentiate the result back
  and substitute a point, so the test does not depend on how the natural log is spelled -- see
  defect C2 below).
- Limits: a removable discontinuity, limits at infinity (including a Gaussian decay, relevant to
  engineering transients), the `(1+1/x)^x -> e` definition, one-sided limits via the 4th
  `dir` argument, and wrong-argument-count error paths.
- Series: Maclaurin expansion of `exp`/`sin`/`cos`/a geometric series at a few orders, order-0 and
  order-1 edge cases, a negative order (clean existing error), and an explicit non-zero expansion
  point via the function-call form (loose containment check, since that path does not auto-strip
  the `O(...)` term -- noted as a coverage gap below, not a defect).
- Engineering (calculus + units together, this project's own distinguishing territory): velocity
  and acceleration recovered by differentiating a kinematics position expression with unit-bearing
  coefficients and a unit-bearing substitution value; the same via a user-defined `x(t) := ...`
  function; momentum recovered as `d/dv(mass v^2/2)`; force recovered as `d/dx(F x)`; a rate
  (`m/s^2`) integrated over a bounded time interval giving the right accumulated unit (`m/s`), with
  a unit conversion (`km/hr`) cross-check (2 m/s^2 over 4 s = 8 m/s = 28.8 km/hr); power integrated
  over time giving energy (`W*s = J`), with a `kJ` conversion cross-check.
- Error paths: `diff()` with no arguments, a numeric literal where a variable name is expected,
  a calculus keyword applied to a matrix (`-> limit`, `-> series`, extending the existing
  `-> diff`/`-> integrate` matrix-rejection coverage in `tests/test_matrices_blackbox.py`), a
  calculus result with a leftover free variable used in numeric (`=`) context, and the existing
  "Unknown keyword" message for a nonsense keyword.

One thing worth calling out about my own test-writing: my first draft of the momentum/force
engineering tests used `m` as a variable name for mass, which shadowed the built-in unit `m`
(meter) for the rest of that sheet -- by design, per the existing
`test_user_definition_overrides_unit` in `tests/test_engine.py` -- and produced a dimensionally
nonsensical intermediate result (`12 kg^2/s`). That was a bug in my test, not in the engine; fixed
by renaming to `mass`/`accel`/`xdist`.

### Results
`QT_QPA_PLATFORM=offscreen ~/livesheet-venv/bin/python -m pytest -q` (venv `~/livesheet-venv`):
**753 passed, 6 xfailed** (4 mine below, 2 pre-existing and unrelated), 0 failed, 0 skipped.
`tests/test_calculus.py` alone: 39 passed, 4 xfailed.

## Defects (minimal repro, all strict `xfail` in `tests/test_calculus.py`)

- **C1** (medium): the keyword-pipeline form `expr -> limit, x` always fails with
  `Unknown keyword 'limit'`, even though `"limit"` is explicitly listed in
  `evaluator._SCALAR_KEYWORDS` and in the free-variable handling of `Engine._symbolic` (both at
  evaluator.py lines ~67 and ~478) -- i.e. the code clearly intends `limit` to work the same way
  as `diff`/`integrate`/`series` do via `->`, but `Engine._apply_keyword` (the `if kw == ...`
  chain starting around line 519) has no `if kw == "limit":` branch, so it falls through to the
  generic "Unknown keyword" error. The function-call form `limit(expr, x, point)` works correctly
  (verified for ordinary limits, limits at infinity, one-sided limits, and `(1+1/x)^x -> e`); only
  the keyword-chain shorthand is broken. Repro: `sin(x)/x -> limit, x` gives
  `Unknown keyword 'limit'` instead of `1`.
- **C2** (low, cosmetic but genuinely confusing): a natural logarithm produced by `diff`,
  `integrate`, `limit` or `series` (SymPy's `log(x)`, meaning natural log) is displayed as
  `log(x)`, which collides with this project's own stated and tested convention that a bare
  `log(...)` typed by the user means base-10 log (comment "Mathcad convention: log is base 10, ln
  is natural" at the top of `evaluator.py`; `test_constants_and_functions` checks
  `log(1000) = 3`). `livesheet/engine/formatting.py`'s `SheetPrinter` has no `_print_log` override,
  so SymPy's natural-log node always prints as `log`, not `ln`. Repro: `1/x -> integrate, x` shows
  `-> log(x)`, which a user would reasonably (and wrongly, per this app's own notation) read as
  base-10 log of x; it is actually `ln(x)`. The underlying math is correct (I cross-checked the
  value by differentiating the result back and substituting a point, independent of the label);
  only the displayed name is wrong.
- **C3** (low): calling `diff()` directly as a function (not via `-> diff`) on an expression with
  more than one free variable and no variable argument, e.g. `diff(x^2 + y^2) ->`, surfaces a raw,
  multi-line SymPy `ValueError` ("Since there is more than one variable in the expression, the\n
  variable(s) of differentiation must be supplied to differentiate ...") that the generic handler
  in `Engine._run_statement` truncates to its first line only
  (`str(exc).strip().splitlines()[0]`, evaluator.py ~line 312), producing the non-actionable,
  mid-sentence message `"Since there is more than one variable in the expression, the"`. The
  equivalent keyword-pipeline form for the same situation (`x^2 + y^2 -> diff`) already gives the
  correct, complete, friendly message: `'diff' needs a variable, e.g. -> diff, x`. The fix could be
  either to join `str(exc)`'s lines before truncating, or (probably better, since it is one call
  site away) to route the plain `diff`/`integrate`/`limit` builtins through the same
  variable-detection helper `_apply_keyword` already uses via `sym()`.
- **C4** (low): a non-integer series order leaks a raw Python exception straight to the user
  instead of a clean `StatementError`. Repro: `exp(x) -> series, x, 2.5` gives the error text
  `invalid literal for int() with base 10: '2.5'` (from `evaluator.py`'s
  `order = int(args[1]) if len(args) > 1 else 6`, which calls Python's bare `int(...)` with no
  `try`/`except`). A negative order (`exp(x) -> series, x, -1`) already gives a clean, readable
  message ("Number of terms should be nonnegative"), so this is specifically about the `int()`
  parse failing, not about order validation in general.

## Observations (not defects)

- The `-> series, x[, order]` keyword form always expands around `0` (Maclaurin only); there is no
  keyword-syntax way to expand around an arbitrary point. The underlying `sp.series` function is
  reachable directly as a raw call (`series(expr, x, point, order) ->`) and does support an
  arbitrary point, but that path does not auto-strip the trailing `O(...)` term the way the
  keyword form does, and the default is `sp.series`'s own default `x0=0` only when called with 2
  positional args. This looked at first like a bug but is a reasonable, deliberate scope choice
  (every other scalar keyword here, e.g. `diff`, `integrate`, also only takes a single variable
  name, not extra structure); I'm flagging it only as a coverage/feature gap worth a product
  decision, not as a strict `xfail`.
- In symbolic mode (`->`), compound/derived units built from more than one base unit (e.g.
  differentiating `V0*sin(w*t)` with `V0` in volts and `w` in hertz) print as raw SI base-unit
  combinations (`kg*m^2/(A*s^4)`-style) rather than collapsing back to a named derived unit (`V`,
  `Hz`, ...), because in `livesheet/engine/units.py` the preferred-name collapsing
  (`dims_to_text`/`_PREFERRED_DISPLAY`) is only used on the numeric (`Measured`) path, not on plain
  symbolic SymPy expressions built from `UNITS` dict values. This is a real, slightly ugly display
  limitation of mixing derived units with symbolic calculus, but it is not new to calculus and not
  something the spec/convention promises; noting it as a coverage gap rather than a defect.
- No real-window / computer-use GUI check was done this session: the `computer_*` tools described
  in this project's testing instructions were not present in my toolset at all this run, so I could
  not open the real app, type these expressions into a live math region, and watch them render.
  This feature has no new GUI surface of its own (it's typed into the existing math-region text
  box), so the risk is lower than for a GUI-spec review, but a manual pass (type a few of the
  expressions above into a real region and confirm they render/recalculate as expected, especially
  the unicode output: `²`, `·`, `√`, `π`, `∞`) is still a legitimate follow-up for Theo or a future
  tester run with that tool available.

## IP red flags

None observed. I did not open or use `docs/calculus-10th-edition-anton.pdf` or
`docs/Engineering With Mathcad.pdf`. The calculus keyword names (`diff`, `integrate`, `limit`,
`series`, `collect`, `partfrac`, `apart`, `solve`, `simplify`, `expand`, `factor`, `substitute`,
`float`) read during this review are generic mathematical-operation names used across many CAS
tools and libraries (including SymPy itself, whose own public API uses the same names), not a
copied vendor keyword set, and no vendor help text, example worksheets, or proprietary strings
were found in `evaluator.py`, `syntax.py`, `units.py` or `formatting.py` while reading them for
this review.

## Recommendation

The core calculus math is solid: every derivative/integral/limit/series case I independently
worked out and tried (polynomials, product/quotient/chain rule, trig, exp/log, u-substitution,
integration by parts, standard limit forms including one-sided and at-infinity, Maclaurin series,
and calculus combined with units for realistic kinematics/power/momentum engineering
calculations) gives the mathematically correct answer. The four defects above are all in the
surface layer around that correct math (a missing keyword-dispatch branch, a display-label
inconsistency, and two places where an internal exception leaks to the user instead of a clean
message), none of them silently wrong-answer defects. Not a blocker for anything currently
planned; worth a small follow-up fix pass (C1 in particular, since it makes an explicitly declared
keyword completely unusable in its intended shorthand form).
