# 010 ODE solving (initial-value problems, symbolic with numeric fallback)

Source inspiration (concept only, nothing copied):
- Backlog item 14 ("ODE solving, numeric and symbolic") and the concept checklist in
  `.claude/skills/mathcad-concepts` ("Differential-equation solving (initial-value
  problems, numeric)"), which points to the public product page
  https://www.ptc.com/en/products/mathcad (accessed via the repo skill only; no vendor
  help pages, examples, keyword lists or the `Odesolve` construct were read).
- Generic calculus/ODE textbook concepts, already assumed common ground on this
  project (ordinary differential equation, order, initial-value problem, closed-form
  vs. numeric solution, first-order system reduction) — not sourced from any vendor
  document.
- SymPy's own public documentation (BSD-3-Clause, SymPy is an already-approved
  dependency): the ODE how-to guide,
  https://docs.sympy.org/latest/guides/solving/solve-ode.html, accessed 2026-10-29
  (confirms: `dsolve(eqs, funcs, ics=...)` accepts a list of equations and a list of
  unknown functions for coupled systems; `ics` is a dict mapping a function, or one of
  its derivatives, evaluated at a point, to its value; some equations give only an
  implicit solution; equations it cannot handle raise `NotImplementedError`; the page
  itself recommends falling back to numeric solving — e.g. with SciPy — for ODEs it
  cannot solve in closed form).
- SciPy's own public documentation (BSD-3-Clause, SciPy is an already-approved
  dependency): `scipy.integrate.solve_ivp`,
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html,
  accessed 2026-10-29 (confirms: solves a first-order ODE system `dy/dt = f(t, y)`
  from `y(t0) = y0` over `t_span`; step size is chosen adaptively regardless of how
  many points are requested via `t_eval`; `dense_output=True` gives a continuous
  interpolant; default method `RK45`).
- Everything below (keyword names, syntax, phasing, output format, error texts) is
  LiveSheet's own design, and deliberately avoids the policy-forbidden `Odesolve`
  name and any look-alike of it.

## User story
As an engineer I write one or more ordinary differential equations with their initial
conditions on the sheet, in whatever units the problem uses, and ask for a solution.
When SymPy can find a closed form that satisfies the initial conditions, I get a
formula I can use anywhere a function is usable on the sheet (evaluate it at a point,
show it in a table, plot it). When it cannot, I automatically get a numeric
solution — a table of sampled points, and (phase B) the same formula-like usability —
instead of an error, so I never have to leave the worksheet or decide up front whether
my problem has a closed form.

## Behaviour (own words)

### Why a dedicated construct, and why it builds on spec 003's tag idiom
A single ODE is not one expression with a target variable the way `diff`/`integrate`/
`limit`/`series` are (those act on one already-parsed expression via the `->` keyword
chain). Solving an initial-value problem needs several pieces of information that do
not fit in one line: the equation (or several, for a coupled system), the unknown
function name(s), and a set of initial conditions, all referring to each other. This
is exactly the shape spec 003 ("solve blocks") already solved for algebraic systems:
independent single-line regions, anywhere on the canvas, joined only by a shared
`in <name>` tag and collected in reading order; a dedicated result line triggers the
solve and binds the answer by name. This spec reuses that tag idiom and its existing
`model_*` machinery directly, adding new tagged statement kinds for an ODE's pieces
and a new kind of result line, rather than inventing a second, parallel grouping
mechanism. One deliberate difference from spec 003: an ODE's unknown function names
and independent variable are not given in a separate declaration line — they are
read off the equation line itself (`diff(y(t), t, 2)` unambiguously names the unknown
function `y` and the independent variable `t`), so a separate "declare the unknowns"
line would just repeat information already in the equation.

### Writing one ODE or a system
An equation region has the form:
```
ode <derivative-term> == <expression> in <name>
```
`<derivative-term>` must be exactly `diff(F(X), X)` or `diff(F(X), X, N)` — the
existing `diff` builtin already used by this project's `->`-chain and function-call
forms, applied to an as-yet-undefined function `F` of a single variable `X` (SymPy's
own parser already turns an undefined-name function call like `y(t)` into a plain
applied function, and `diff` of that is a symbolic `Derivative`, unevaluated until
`ode`'s own solving step uses it — no grammar change needed for this part). `N`
(default 1 when omitted) is the order being defined by this line; `<expression>` is
any expression in the model's other functions, `X`, parameters and units — it may
reference other dependent functions of the same system for coupling. The restriction
to "pure derivative term alone on the left" keeps parsing simple; an equation written
the other way around is one line of algebra for the user to flip.
A single higher-order equation (`diff(y(t), t, 2) + ... == ...`) and a first-order
system (`diff(x(t), t) == v(t)`, `diff(v(t), t) == ...`) are both just sets of `ode`
lines; several such lines may share the same tag, one per equation. Every `ode` line
of one model must use the same independent-variable name (checked; a mismatch is an
error, not a silent assumption).

### Initial conditions
```
start F(X0) == V0 [, F'(X0) == V1 [, F''(X0) == V2 ...]] in <name>
```
One line may give several conditions for one or more functions, comma-separated. The
prime marks (`'`, `''`, ...) are a small, local, textbook notation (order = number of
primes) understood only on the left side of a `start` condition — they are not a
general grammar change elsewhere on the sheet (the sheet's other derivative notation
stays `diff(f(x), x)`, unchanged). `X0` is the point (an expression, usually a
literal number with an optional unit — all of a model's conditions must share the
same point); `F` with zero primes means the function's own value there. Exactly one
condition of each order `0, 1, ..., (highest order used for F in the model's `ode`
lines) - 1` must be given per function, all at the same point (a classic single-point
initial-value problem; two-point boundary-value problems are out of scope, see open
questions).

### Sampling range (needed only for a numeric result)
```
over X from <A> to <B> [points <N>] in <name>
```
Reuses the exact sub-grammar spec 004's `plot` block already has for its own `over`
line (`NAME from A to B [points N]`); `N` defaults to 101 when omitted, same default
as spec 004. Declares both the reporting grid for a numeric result and (by matching
`X` against the model's independent-variable name) a consistency check. Not needed
when a closed form is found and `over` was not given.

### Settings
`accuracy <number> in <name>` and `steps <integer> in <name>` — the exact same two
settings spec 003 already defines (same literal words, same per-model "last one
above the result wins" rule, same statement kind under the hood: these are generic to
"a numeric iterative process with a tolerance and a step budget", not specific to
either feature). Here `accuracy` is the numeric integrator's relative tolerance
(default `1e-6`) and `steps` its maximum internal step count (default `10000`); both
are ignored when a closed form is used.

### Asking for the solution
```
evolve in <name>              try a closed form; if none is found, solve numerically
evolve symbolic in <name>     closed form only; error if none is found
evolve numeric in <name>      numeric only, skips the closed-form attempt
```
`evolve` is LiveSheet's own word, chosen to read naturally ("evolve the system
forward") while staying clear of `solve` (already the symbolic `->`-chain keyword, as
spec 003 also deliberately avoided it) and of the policy-forbidden `Odesolve`.

### What a successful closed-form result does
- Builds `dsolve([eq, ...], [F(X), ...], ics={...})` (SymPy's own documented ICS dict
  shape: a derivative condition's key is that derivative evaluated at the point, e.g.
  the first-derivative condition becomes the key `Derivative(F(X), X).subs(X, X0)`).
  Units are not stripped first: every quantity in the equations and conditions already
  carries its own unit factor the same way the rest of this engine's expressions do
  (as in spec 003), so `dsolve` just carries them through symbolically as ordinary
  multiplicative factors.
- A result that is an *implicit* relation (SymPy's own documented behaviour for some
  equations: not solved explicitly for `F(X)`) is treated the same as "no closed form
  found" — it is not a usable callable, so this counts as a closed-form failure for
  fallback/error purposes.
- On success, each function `F` is bound in the environment as an ordinary worksheet
  function (`F(x) := <formula>` would create the same kind of value), usable exactly
  like a user-defined function in a later `F(2 s) =`, `F(t) →`, `table`, or a spec
  004 `plot`'s `show F(t)` line — no new code path in `evaluator.py`'s `_numeric`,
  `formatting.py`, or `plotting.py` is needed for this, since all three already just
  call an arbitrary bound `Lambda` with a value.
- Output text: `"⇒ y(t) = <formula>; v(t) = <formula>"` (one clause per function,
  independent-variable name shown as written in the `ode` lines; `"; "` rather than
  spec 003's `", "` list separator, to read unambiguously when a formula itself
  contains commas, e.g. inside `atan2`).

### What a numeric result does (phase B; phase A reports "not available yet")
- Integrates the model's functions as a first-order system from the shared initial
  point to the end of the `over` range (reducing a higher-order single equation to a
  first-order system internally the same standard way `scipy.integrate.solve_ivp`
  itself expects, per its own public docs) with a relative tolerance `accuracy` and a
  step budget `steps`.
- Binds the `over` line's variable as an ordinary range variable (exactly the kind
  `x := 0 s to 10 s` already produces) under its own written name, and each function
  as a callable the same way the closed-form case does (the callable's exact internal
  representation — e.g. a dense interpolant built from the integrator's own
  `dense_output` — is left to the developer; the only required behaviour is that
  calling it at an in-range point returns a value through the existing `measure`/
  `format_number` pipeline unchanged). This makes the numeric case usable in a later
  `table t, y(t), v(t)` region or a spec 004 `plot`'s `over t` / `show y(t)` exactly
  like the closed-form case — the whole point of binding by name instead of only
  printing a table.
- Also directly reports an inline table (`RegionResult.columns`/`rows`, the same
  fields and the same GUI rendering the existing `table` statement already uses):
  one column per function plus the independent variable, one row per `over` point.
  `output` text: `"⇒ numeric solution, <N> points"` (mirrors the existing `table`
  statement's own `"table <n> rows"` wording style).
- `evolve in <name>` (auto) only reaches this path after a closed-form attempt fails
  or gives an implicit result; it then requires an `over` line to exist (clear error
  otherwise, naming the missing line) since there is no other way to pick a reporting
  grid.

### Scope and binding (shared with both results)
- Function and independent-variable names are local to the model while solving (they
  shadow a same-named variable/unit, exactly as spec 003's unknowns do).
- On success, the independent-variable name is **not** bound afterward (there is no
  single "the" value of an independent variable — contrast with spec 003's unknowns,
  which do get a concrete bound value); only its `over`-range RangeVar (numeric
  case) and the function names are bound, visible to regions below the result region
  in reading order (same rule as spec 003). Nothing is bound on failure.
- No result region below a declaration/condition/setting/over region for its model:
  same error family as spec 003 ("No result region for ..."), worded for an ODE
  system rather than a solve model (own wording, not a verbatim reuse).

## Syntax proposal (own keywords) and grammar change
Examples (each line is one region):
```
ode diff(y(t), t) + y(t)/tau == 0 in decay
tau := 4 s
start y(0) == 10 m in decay
evolve in decay                        -> ⇒ y(t) = 10 m·e^(-t/(4 s))
y(4 s) =                               -> = 3.67879 m

ode diff(y(t), t, 2) + y(t) == 0 in sho
start y(0) == 1, y'(0) == 0 in sho
evolve in sho                          -> ⇒ y(t) = cos(t)
y(pi) =                                -> = -1

ode diff(theta(t), t) == omega(t) in pend
ode diff(omega(t), t) == -sin(theta(t)) in pend
start theta(0) == 0.2, omega(0) == 0 in pend
over t from 0 to 1 points 101 in pend
evolve in pend                         -> no closed form -> numeric: table, 101 rows
```
Grammar change (`engine/syntax.py`): extend the existing `_parse_model` dispatcher
(the one already recognising `vary`/`settle`/`least`/`most`/`accuracy`/`steps` inside
a `... in <name>` tagged line, spec 003) with four more leading keywords, reusing the
existing `Statement` dataclass with two new optional fields (`conditions:
list[tuple[str, int, str, str]]` — name, order, point text, value text; and
`over_points: str` — the sampling count text, reusing the existing `range_end` field
for the `over` line's end text and the existing `name` field for its variable name):
- `ode <text>` where `<text>` contains exactly one top-level `==` and its left side
  matches `diff(IDENT(IDENT), IDENT(, N)?)` (a small dedicated regex; mismatch raises
  `"Write the highest derivative alone on the left: diff(name(t), t[, n]) == ..."`)
  → kind `model_ode`, `model=name`, `expr=<text>` (the equation text, re-parsed with
  the engine's normal expression parser at solve time, same deferred-parse pattern
  `model_require`'s relations already use).
- `start <comma list>` where each item matches
  `^([^\W\d]\w*)('*)\(\s*(.+?)\s*\)\s*==\s*(.+)$` → kind `model_ic`, one 4-tuple per
  item in `conditions` (name, `len(primes)`, point text, value text); a non-matching
  item raises `'Use "start f(point) == value" (optionally f\'(point) == ..., ...)"'`.
- `over <text>` reusing spec 004's own `NAME from A to B [points N]` sub-grammar
  (today private to `engine/plotting.py`'s `_split_top`/`_Builder._sampling`; this
  spec asks the developer to factor the small shared regex into `engine/syntax.py`
  or a tiny shared helper module rather than duplicate it) → kind `model_over`,
  `name=<NAME>`, `expr=<A text>`, `range_end=<B text>`, `over_points=<N text or "">`.
- `evolve`, `evolve symbolic`, `evolve numeric` → kind `model_result`,
  `goal="ode_auto" | "ode_symbolic" | "ode_numeric"` respectively; any other trailing
  word after `evolve` raises `"evolve takes 'symbolic', 'numeric' or nothing"`.
- `accuracy`/`steps` keep their existing `model_setting` kind unchanged — shared
  verbatim between spec 003's solve blocks and this spec's ODE systems, since the
  evaluator only needs a number out of them regardless of which family owns the tag
  name; a sheet never needs the same tag name for both kinds of model at once.
No other existing statement form changes meaning; a sheet with no `ode`/`start`/
`over`/`evolve` region is unaffected (same backward-compatibility guarantee spec 003
already gives for its own tag).

## Acceptance criteria (numeric, testable)
Tolerance: absolute 1e-4 unless stated. Evaluate via `Engine().evaluate([...])` with
regions in the given order; "output" is `RegionResult.output` of the result region.

Phase A (symbolic only, units, binding, errors; `evolve numeric` reports "not available yet")
1. First-order, units. `ode diff(y(t), t) + y(t)/tau == 0 in decay`, `tau := 4 s`,
   `start y(0) == 10 m in decay`, `evolve in decay` → status ok, output contains
   `y(t) =`; a following `y(4 s) =` gives `= 3.67879 m` (abs 1e-4; exact value
   `10*exp(-1) m`); `y(0 s) =` gives `= 10 m`.
2. Second order. `ode diff(y(t), t, 2) + y(t) == 0 in sho`,
   `start y(0) == 1, y'(0) == 0 in sho`, `evolve in sho` → `y(pi) =` gives `= -1`
   (abs 1e-6), `y(pi/2) =` gives `= 0` (abs 1e-6).
3. Coupled linear system, closed form exists. `ode diff(x(t), t) == v(t) in fall`,
   `ode diff(v(t), t) == -g in fall`, `start x(0) == 0 m, v(0) == 0 m/s in fall`,
   `evolve in fall` → `x(2 s) =` gives `= -19.62 m` (abs 1e-2, using this project's
   existing `g` constant) and `v(2 s) =` gives `= -19.62 m/s` (abs 1e-2).
4. Binding and scope. After criterion 1, a region above `evolve in decay` that
   mentions `y` still sees it undefined or an older definition (reading order); a
   region below sees the bound function; `y(t) →` (symbolic) shows the formula with
   `t` still free.
5. `evolve symbolic` behaves identically to plain `evolve` whenever a closed form
   exists (criteria 1-3 repeated with `evolve symbolic in <name>` give the same
   output).
6. No closed form, phase A. `ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend`,
   `start theta(0) == 0.2, theta'(0) == 0 in pend`, `evolve in pend` → status error,
   starts `No closed-form solution found`; same model with `evolve symbolic` gives
   the identical error; same model with `evolve numeric` gives a different error
   starting `Numeric ODE solving is not available yet`.
7. Units mismatch. `start y(0) == 10 in decay` (criterion 1's model, no unit this
   time, while `tau` carries `s` so the equation is not unit-consistent for a
   dimensionless `y(0)`) → error starts `Units do not match`. Also:
   `start y(0) == 10 m, y'(0) == 1 in decay` on criterion 2's `sho` model (an extra,
   wrongly-dimensioned condition where only one condition of order 0 is expected
   besides the declared order 1) is covered by criterion 8 (wrong count), not here.
8. Condition-count errors. `sho` model with only `start y(0) == 1 in sho` (missing
   the order-1 condition for a 2nd-order equation) → error
   `"sho" needs 2 initial condition(s) for y, has 1`. Same model with
   `start y(0) == 1, y'(0) == 0, y''(0) == 0 in sho` (one too many) → error
   `"sho" needs 2 initial condition(s) for y, has 3`.
9. Independent-variable mismatch. `ode diff(y(t), t) == -y(t) in bad`,
   `ode diff(z(s), s) == -z(s) in bad` → error
   `All equations of "bad" must use the same independent variable`.
10. Equation-shape error. `ode y(t) + diff(y(t), t) == 0 in shape` (derivative not
    alone on the left) → error starts
    `Write the highest derivative alone on the left`.
11. Missing result / ordering, same wording family as spec 003: an `ode`/`start`
    region with no `evolve` region below it for its tag → error
    `No result region for ODE system "<name>" below this region`; an `ode` region
    placed below `evolve` is not used (result unchanged by it).
12. Isolation and compatibility: a sheet without any `ode`/`start`/`over`/`evolve`
    region evaluates identically to before (existing `tests/test_engine.py`,
    `tests/test_solve.py` unchanged and green); a solve-block model (spec 003) and
    an ODE system with different tag names on the same sheet do not interact.
13. Parsing: `parse_statement("ode diff(y(t), t, 2) + y(t) == 0 in sho")` gives kind
    `model_ode`, `model="sho"`; `"start y(0) == 1, y'(0) == 0 in sho"` gives kind
    `model_ic`, `conditions=[("y", 0, "0", "1"), ("y", 1, "0", "0")]`;
    `"over t from 0 to 1 points 101 in pend"` gives kind `model_over`, `name="t"`,
    `expr="0"`, `range_end="1"`, `over_points="101"`; `"evolve numeric in pend"`
    gives kind `model_result`, `goal="ode_numeric"`.

Phase B (numeric fallback, `over`, binding of the numeric case, settings)
14. Automatic numeric fallback with energy-conservation check (no hand-derived
    reference value needed): the `pend` model from criterion 6 plus
    `over t from 0 to 1 points 101 in pend`, `evolve in pend` → status ok, output
    starts `⇒ numeric solution, 101 points`; for every reported row,
    `0.5*omega^2 - cos(theta)` is within 1e-3 of its value at `t = 0`
    (`-cos(0.2) ≈ -0.98007`, standard conservation of energy for this equation, not
    a tool-derived number); every reported `theta` value satisfies
    `abs(theta) <= 0.2 + 1e-3` (the starting point is a turning point, so the swing
    cannot exceed its own starting amplitude).
15. Numeric cross-check against a known closed form. `ode diff(y(t), t) + 2*y(t) == 0
    in forced`, `start y(0) == 5 in forced`,
    `over t from 0 to 2 points 5 in forced`, `evolve numeric in forced` → table rows
    at `t = 0, 0.5, 1, 1.5, 2` with `y ≈ 5, 1.83940, 0.67668, 0.24894, 0.09158`
    (abs 1e-4; exact values `5*exp(-2t)`, hand-computable); a sparser grid
    (`points 2`, i.e. only the two endpoints) gives the same `t=2` value within the
    same tolerance (confirms the integrator's accuracy does not depend on how many
    points are reported, per `solve_ivp`'s own adaptive-stepping documentation).
16. Binding and reuse. After criterion 15's `evolve numeric in forced`: `t` is bound
    as a range variable (`t =` on the first/only remaining step errors the usual
    "range variable" way, but `table t, y(t)` below gives the same 5 rows as the
    `evolve` region's own table); this model is dimensionless, so `y(1) =` gives
    `= 0.67668` (abs 1e-4); a `plot` region with `over t` / `show y(t)` placed below
    produces one trace with 5 points.
17. Settings. Criterion 14's model with `accuracy 1e-3 in pend` above `evolve` still
    passes the same energy check at a looser tolerance; `steps 1 in pend` (too few
    for 101 reported points over the given span) → error starts `Not converged`.
18. `over` required for the auto/numeric path. Criterion 6's `pend` model without an
    `over` line, `evolve in pend` (closed form fails, no `over` given) → error
    `over t from ... to ... is needed to solve "pend" numerically`. Plain `evolve
    numeric` on a model whose closed form *would* have existed (e.g. criterion 1's
    `decay` model, with an `over tau from 0 s to 8 s in decay` line added) still
    produces a numeric table (forcing numeric is honoured even though a closed form
    exists).

## Edge cases
- A function appearing in `start`/`over` but never given an `ode` equation (typo, or
  belongs to a different tag) → `"<name>" is not an equation of ODE system "<name>"`.
- Two-point boundary conditions (value given at two different points) are not
  supported; detected as "all conditions must share the same point" and rejected
  with a clear error, not silently mishandled — out of scope here (open question 4).
- A dependent function reused as an ordinary variable elsewhere on the sheet:
  shadowed only inside the model while solving, same as spec 003's unknowns.
  Reusing the model's independent-variable name, say `t`, outside the model is
  likewise unaffected until (numeric case) the `evolve` region's own binding,
  exactly like spec 003's reading-order rule for its unknowns.
- Very long integrations: bounded by `steps`, same reasoning and same known
  limitation spec 003 already flagged (GUI thread freeze on a slow model; not solved
  here, see open questions).
- A closed form exists but is enormous (e.g. deeply nested special functions):
  displayed and usable exactly as any other large symbolic result already is; no
  special truncation beyond what `format_expr` already does elsewhere.
- Complex-valued closed forms (e.g. from a characteristic equation with complex
  roots) are accepted and simplified/displayed the normal way `format_number`
  already renders complex numbers; a complex *initial condition* is not supported
  (real-valued conditions only, same restriction as spec 003's unknowns).
- `ode`/`start`/`over`/`accuracy`/`steps` regions show no special per-region mark in
  this spec (`status ok`, empty `output`); a satisfied/violated-style mark (spec
  003's optional phase B idea) is not proposed here — nothing to mark per-region
  before the system is solved as a whole (open question 6).
- Save format: unchanged; regions remain plain text in `.lsheet`.

## IP check
pass (with the flags below). The forbidden word `Odesolve` and any look-alike are
avoided; LiveSheet's own words are `ode`, `start`, `over` (reused verbatim from spec
004's own already-approved `over` sub-grammar), `evolve`, plus the unchanged
`accuracy`/`steps` reused verbatim from spec 003. `solve` is again deliberately
avoided as a region keyword for the same reason spec 003 gave (it is the existing
`->`-chain keyword). The underlying method — SymPy's `dsolve` with an `ics=` dict,
falling back to a first-order-system numeric integrator when no closed form exists —
is exactly SymPy's and SciPy's own public, BSD-licensed, already-approved API and
documented recommendation (cited above); using a documented capability of an approved
dependency the way its own docs recommend is squarely inside "Allowed" (methods,
algorithms, standard notation and already-approved dependencies). The tag idiom
(`in <name>`, independent single-line regions collected in reading order, a dedicated
result line) is not newly invented here — it is spec 003's own already-reviewed
construct, extended with new leading keywords; nothing here is closer to any vendor's
construct than spec 003 already was. No vendor text, example or screenshot was used;
the worked examples (exponential decay, undamped harmonic oscillator, free fall,
simple pendulum) are standard, generically-taught textbook ODEs chosen independently,
not sourced from any vendor's example library. Flags for the manager: (1) the small
prime-mark (`'`, `''`) notation inside `start` lines only is new textbook-standard
notation, not drawn from a vendor's keyword set, but the manager may want to confirm
it reads unambiguously next to the project's unrelated use of `'` nowhere else on the
sheet (none currently); (2) as with spec 003, skill rule 6 — this is a numeric/
symbolic solve construct, not a drawn-on-canvas interaction, so the patent-sensitive
placeholder-editing concern does not apply here, but a general patent search on "named
group of tagged regions solved on demand" has still not been done (same open flag spec
003 already carried, now extended to a second feature built on the same idiom); (3)
before a 1.0 release the IP policy's own legal-review step should include this
feature too.

## Fits current architecture?
- `engine/syntax.py`: extend `_parse_model` (already the exact right place; it already
  tries `vary`/`settle`/`least`/`most`/`accuracy`/`steps` in order) with the four new
  keyword branches above; `Statement` gains `conditions` and `over_points` fields
  (additive, optional, default empty — no existing field or caller affected). The
  `over` sub-grammar (`NAME from A to B [points N]`) should be factored out of
  `engine/plotting.py`'s private `_split_top`/`_Builder._sampling` into a small shared
  helper so this spec's `over` line and spec 004's `plot` block's `over` line do not
  duplicate the same regex twice; this is the one small refactor this spec asks for.
- `engine/evaluator.py`: `Engine._run_model` (already dispatches `model_vary`,
  `model_require`, `model_setting`, `model_result` in reading order via the existing
  `earlier`/`last_result`/`broken_models` bookkeeping) gains two more "earlier member"
  kinds (`model_ode`, `model_ic`; `model_over` reuses the existing `model_setting`-like
  "just register it, nothing to run yet" handling) and, for `model_result`, a branch
  on `st.goal.startswith("ode")` that calls into a new module instead of `solver.py`.
  `Engine.parse`/`Engine._define` are unchanged — binding a solved function is exactly
  `env[name] = sp.Lambda(indep_symbol, formula)`, the same shape `_define` already
  produces for an ordinary `f(x) := ...` region, so `_numeric`, `_symbolic`, `table`
  and `plotting.py`'s `trace()` need no new branch to use it.
- `engine/odesolver.py` (new, GUI-independent, parallel in spirit to `solver.py`):
  `System` dataclass (equations, functions, independent-variable symbol, conditions,
  settings), `build(model, members, env, engine)`, `solve_symbolic(system) ->
  SymbolicOutcome | None` (wraps `sp.dsolve(..., ics=...)`, returns `None` on
  `NotImplementedError` or an implicit result), `solve_numeric(system, over) ->
  NumericOutcome` (wraps `scipy.integrate.solve_ivp`, reduces any order-`N` equation
  to `N` first-order ones internally, the standard textbook substitution). Both
  outcomes carry enough to build the bound `Lambda`s and the result text/table; unit
  handling (checking the equation's and each condition's dimensions once,
  symbolically, before calling into SymPy/SciPy) uses the existing
  `units.measure`/`UnitError`, same one-time-check spirit as `solver.py`'s own
  dimension handling.
- `engine/units.py`: no change; `measure` is used the same way spec 003 already uses
  it.
- `engine/formatting.py`: no change; the solved closed form is an ordinary SymPy
  expression printed by the existing `SheetPrinter`/`format_number` path (`cos`,
  `exp`, `sin` are already handled; no new `_print_*` hook is needed since, by the
  time a formula is displayed, no unevaluated `Derivative` remains in it).
- `engine/plotting.py`: no change needed for either phase; the only touch is the
  `over` sub-grammar extraction mentioned above (and even that can be done by just
  having `odesolver.py`/`syntax.py` import the one regex/helper from `plotting.py`
  if the developer prefers not to move it, at the cost of a slightly odd import
  direction — the developer's call, flagged as open question 3).
- `gui/regions.py`, `gui/pretty.py`: no change required for phase A. For the numeric
  phase B inline table, `RegionResult.columns`/`rows` are already rendered by the
  existing table-drawing code path (the same fields the `table` statement already
  fills); no new GUI code needed. `pretty.py`'s existing `diff(...)`-recognising
  pretty-printing (added for the calculus-coverage work) already renders this spec's
  `ode`/`start` lines' `diff(y(t), t, 2)` sub-expressions as `d²/dt² (y(t))`
  automatically, with zero extra work, which is a pleasant side benefit worth noting
  to the developer.
- `pyproject.toml`: no new dependency (`sympy` and `scipy` are already approved,
  `scipy` already added by spec 003's own implementation).
- `document.py` / `.lsheet`: unchanged (plain text regions).
- Tests: `tests/test_odesolver.py` (new, developer) from the acceptance criteria
  above; independent tester writes a black-box counterpart from this spec, same
  process as every previous spec.

## Open questions for the manager (also candidates for docs/board/decisions.md)
1. Keyword names: are `ode` / `start` / `evolve` acceptable, or does Theo prefer
   different words (e.g. `given`/`initial`/`run` — noting `given` is itself close to
   the policy-forbidden `Given` and should probably stay excluded)?
2. The prime-mark notation (`y'(0)`, `y''(0)`) scoped only to `start` lines: acceptable
   as a small, local, textbook-standard addition, or should conditions instead spell
   out the order as a word/number (e.g. `start order 1 of y at 0 == 2 m/s in name`,
   more verbose but avoids adding `'` to the grammar at all)? Recommendation: keep
   the prime notation — it is exactly how every calculus textbook writes an IVP's
   conditions, and it is scoped to one line kind only.
3. Factor spec 004's `over` sub-grammar into a small shared helper (this spec's
   preference, cleaner) vs. leaving `plotting.py`'s version private and duplicating
   the same ~15-line parsing regex in `syntax.py` (less refactor risk, more
   duplication) — developer's call unless Theo has a preference.
4. Two-point boundary-value problems (conditions at two different independent-
   variable values instead of one) are explicitly out of scope here; worth a
   dedicated follow-up spec later, or not planned at all?
5. Should a successful numeric `evolve` also offer the dense continuous interpolant
   as the *only* representation (always usable like a function, as phase B
   proposes), or is a table-only phase A/B split (defer ALL function-binding of the
   numeric case to a phase C) safer given how new `scipy.integrate.solve_ivp`'s
   `dense_output` is to this codebase? Recommendation: keep as phase B describes
   (bind from the start) — the usability win (works in `plot`/`table` immediately)
   is large relative to the risk, and the exact representation is left to the
   developer regardless.
6. Should `ode`/`start` regions show a satisfied/violated-style mark once `evolve`
   succeeds or fails (mirroring spec 003's optional `✓`/`✗`), deferred to a later
   phase here, or skipped entirely since (unlike spec 003's constraints) there is
   no per-region residual to check once the system has been solved as a whole?
7. Systems of implicit-only closed forms (SymPy's own documented possibility): is
   silently treating them as "no closed form" (falling back to numeric, or erroring
   in forced-symbolic mode) the right call, or should the implicit relation itself be
   shown to the user as a (non-callable) result in forced-symbolic mode instead of an
   error? Recommendation: current behaviour (treat as failure) for a first version;
   showing the implicit relation itself is a reasonable, small follow-up if Theo
   wants it.
