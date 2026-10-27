# 003 Numeric solve models (unknowns, constraints, settle / least / most)

Source inspiration (concept only, nothing copied):
- Backlog item 3 and the concept checklist in .claude/skills/mathcad-concepts ("solve blocks: constraints plus unknowns, numeric root finding, minimise/maximise"), which points to the public product page https://www.ptc.com/en/products/mathcad (accessed via the repo skill only; no vendor help pages, examples or keyword lists were read for this spec).
- Numerical method reference (BSD-licensed public docs): SciPy optimize.minimize, https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html, accessed 2026-10-27 (which methods accept equality/inequality constraints; result has success flag + message).
- Everything below (names, syntax, output format, error texts, tolerance semantics) is LiveSheet's own design.

## User story
As an engineer I declare some unknowns with starting guesses, state equations and inequalities that must hold, and ask for a solution (or the smallest / largest value of an expression), with units checked, so I can solve nonlinear sizing problems in the worksheet without leaving it. If no solution exists or the solver does not converge, I get a clear message next to the result region.

## Behaviour (own words)

### Concept: a model is a label, not a visual block
A *model* is just a name (an identifier). Any math region can join a model by ending with `in <name>`. Regions stay ordinary single-statement regions: they can be anywhere on the canvas, interleaved with other regions, moved independently, and no frame or grouping container exists. The result region collects every region tagged with its model name that is **earlier in reading order** (top-to-bottom, then left-to-right, same rule as everything else). Regions of other models, or untagged regions, are not affected. Several models can coexist; the same model name can be asked several results (e.g. first `settle`, later `least` using the same unknowns and constraints).

### Region kinds (five new statement kinds)
1. Unknown declaration: `vary x from <guess>, y from <guess> in <name>`
   - Declares the unknowns of the model and their starting values. Guess carries a unit or is dimensionless; this fixes the dimension of the unknown.
   - Several declaration regions may exist per model; the same unknown declared twice is an error.
2. Constraint: `<expr> == <expr> in <name>` (equality), `<expr> <= <expr> in <name>`, `>=` (inequality). Unicode `≤` `≥` accepted. `<` and `>` are accepted and treated as `<=` / `>=` (continuous problems; strict inequality is not distinguishable numerically; shown in the docs/tooltips). A chained form `a <= x <= b in <name>` counts as two constraints.
3. Setting: `accuracy <number> in <name>` (default 1e-8) and `steps <integer> in <name>` (default 200). Last one above the result wins.
4. Result, equations only: `settle in <name>`
5. Result, optimisation: `least <expr> in <name>` and `most <expr> in <name>` (objective to make smallest / largest while all constraints hold).

Notes on the choice of words: `vary`, `from`, `settle`, `least`, `most`, `accuracy`, `steps` and the trailing `in <name>` are LiveSheet inventions. The pair `least` / `most` is chosen to be symmetrical and short.

### What a result region does
- Collects the model's unknowns, constraints and settings from earlier regions, reads all other variables (parameters like `h := 20 m`, functions, units) from the environment at the position of the result region.
- Unknown names are local to the model while it is solved (they shadow an existing variable or unit of the same name inside the model). After a successful result region the unknowns are **bound by name** in the environment as ordinary quantities (like a definition would), so later regions can use `x`, `y` directly and `x =` works. Nothing is bound on failure.
- `settle`:
  - number of equalities == number of unknowns and no inequalities: square root-finding from the guess.
  - otherwise (inequalities present, or fewer equalities than unknowns): find the feasible point closest to the guess (minimise the sum of squared, guess-scaled distances to the guess subject to the constraints). More equalities than unknowns is allowed and succeeds only if they are consistent.
- `least` / `most`: constrained optimisation from the guess, objective must be a scalar with a single dimension (any dimension).
- Several solutions: the solver returns the one it reaches from the guess; the guess is therefore part of the problem statement. Local optimum only; no global search.
- Only real continuous unknowns. No integer unknowns, no complex values.

### Units
- Each unknown has the dimension of its guess. Internally the solver works with dimensionless coherent-SI magnitudes (scaled by the magnitude of the guess, or 1 when the guess is 0) so that `0.01 min` and `0.6 s` as a guess behave identically.
- Both sides of an equality/inequality must have equal dimensions (checked with `units.measure`, once, symbolically, at the guess; error otherwise). The objective of `least`/`most` may have any single dimension; the reported value carries it.
- Results are displayed with the existing formatting path (`format_number`, `dims_to_text`, `engine.significant`), i.e. SI-coherent like `=` does today. The user converts afterwards with the existing `x = km/hr`.

### Tolerance
`accuracy` is a dimensionless, unit-independent relative tolerance `tol`. An equality `l == r` counts as satisfied when `|l - r| <= tol * max(|l|, |r|, ref)` where `ref = |l0| + |r0|` is evaluated at the initial guess (1 SI unit when that is 0). An inequality `l <= r` is satisfied when `l - r <= tol * max(|l|, |r|, ref)`. The result region verifies this independently after the solver returns, so a result is only reported when it passes this check, whatever the solver itself says.

### Errors and failure modes (shown in the result region, status "error")
Exact prefixes are fixed so tests can match them; text after the prefix may include numbers.
- `No solution found: ` the solver stopped within the step limit but the best point violates a constraint beyond tolerance (inconsistent or infeasible). Message names the worst constraint source text and its normalised violation, e.g. `No solution found: closest point violates "x^2 + 1 == 0" by 1.0e+00`.
- `Not converged: ` the step limit was reached. Message gives the steps used and the largest normalised violation, and hints to change the guess or raise `steps`.
- `Unknown model "<name>"`/`No unknowns declared for model "<name>"`.
- `Unknown "<u>" has no starting guess` is impossible by syntax; instead `"<u>" is declared twice in model "<name>"`.
- `Units do not match in constraint "<src>"` (reuse UnitError text style).
- `"<q>" is not defined` for a free symbol in a constraint that is neither unknown nor defined (reuse `_check_defined` style).
- `Constraint "<src>" does not involve any unknown` (equality or inequality with no unknown symbol).
- `Cannot evaluate at the starting guess: <reason>` (division by zero, non-finite).
- `accuracy must be a positive number below 1`, `steps must be a whole number of at least 1`.
- `least/most needs an expression` , `settle takes no expression` (parse-time).
- Declaration/constraint/setting region with no result region later in reading order for that model: that region shows error `No result region for model "<name>" below this region`. (Orders matter: a constraint placed below the result region is not used.)
- If a region of the model above the result region has its own error (e.g. syntax), the result region reports `Fix the errors in the regions of model "<name>" first`.
- scipy missing: `Solving needs the scipy package`.

### Output text in regions
- Declaration, constraint, setting regions: `status ok`, `output ""`, `defines ""` (they show nothing; Phase B may add a satisfied/violated mark, see open questions).
- Result region: `"⇒ x = 2 m, y = 3 m"` (each unknown as `name = value unit`, comma separated, order of declaration; numbers via `format_number`). For `least`/`most` the text continues with `"; value = 12.5 m²"`. `defines` stays empty (it lists one name today; the unknowns are bound through `env` directly). Open question: add a list of names.

## Syntax proposal (own keywords) and grammar change
Examples (each line is one region):
```
vary x from 1, y from 2 in sys
x^2 + y^2 == 25 in sys
x*y == 12 in sys
settle in sys                      -> ⇒ x = 4, y = 3 (from a guess near it)

vary t from 1 s in fall
h := 20 m
0.5*g*t^2 == h in fall
settle in fall                     -> ⇒ t = 2.0196 s

vary w from 1 m, d from 1 m in plot
2*(w + d) <= 20 m in plot
most w*d in plot                   -> ⇒ w = 5 m, d = 5 m; value = 25 m²
```
Grammar change (syntax.py): before the existing checks for `≡`, `::=`, `:=`, `→` and `=`, detect a model tag with `^(.*?)\s+in\s+(IDENT)\s*$` (last ` in ` wins; `settle` has the form `^settle\s+in\s+IDENT$`). Then classify the left part:
- starts with word `vary` followed by `IDENT from <expr>` comma list -> kind `model_vary`;
- starts with `least` or `most` (as a whole word followed by a space or `(`) -> `model_result`, goal `min`/`max`, `expr` = rest;
- exactly `settle` -> `model_result`, goal `root`;
- starts with `accuracy` or `steps` -> `model_setting`;
- otherwise must contain a relation (`==`, `<=`, `>=`, `<`, `>`, chained allowed) -> `model_require`; else StatementError `A relation is required before "in <name>"`.
Statement gets new optional fields: `model: str`, `guesses: list[tuple[str, str]]`, `goal: str`, `relations: list[str]`. `normalize` additionally maps `≤`->`<=`, `≥`->`>=`. Words `vary`, `settle`, `least`, `most`, `accuracy`, `steps` are only special in statement position when the tag is present; `least(a, b)` or a variable called `steps` in ordinary regions keep working (no tag, no change in behaviour).
Existing statements without ` in <name>` at the end parse exactly as before. There is no unit called `in` in `UNITS` (inches are `inch`), so no clash; if a user defines a variable `in`, a trailing ` in <name>` is still taken as a tag (document).

Engine (evaluator.py): `Engine.evaluate` pass 2 currently runs each region independently. Change: pass 2 keeps a per-model list of earlier model regions (in reading order) and runs `settle`/`least`/`most` with them. New module `livesheet/engine/solver.py` (no GUI imports) holds: `Model` dataclass (unknowns, guesses, constraints, settings), `build(model, env, engine)`, `solve(...) -> SolveOutcome`. `Engine.parse` gains inequality relations (`parse_expr` already yields `Le/Ge/Lt/Gt`; verify `evaluate=True` keeps them symbolic). GUI (gui/regions.py): no change in Phase A (one-line math regions already hold the text; the `:` auto `:=` is not triggered because no colon is used). `gui/pretty.py`: developer to check that ` in ` and `<=` render sanely (cosmetic: show `≤` `≥`).

Numerics (suggested, developer may choose equivalents): `scipy.optimize.root(method="hybr")` for the square equality case, `scipy.optimize.minimize(method="SLSQP")` with `eq`/`ineq` constraints for everything else; symbolic expressions turned into callables once (`sympy.lambdify` over the dimensionless scaled unknowns) and dimension-checked once with `units.measure`, never per iteration. Plain floats inside the loop.

New dependency: `scipy>=1.10` (BSD-3-Clause; pulls in `numpy`, BSD-3-Clause). Both are permissive, compatible with MIT OR Apache-2.0. Import lazily inside solver.py so GUI start-up is unchanged. Add to `pyproject.toml` dependencies (production code, developer task). Note for packaging: wheels add roughly 40-60 MB.

## Acceptance criteria (numeric, testable)
Tolerance of comparisons in tests: absolute 1e-6 unless stated. "Output" means `RegionResult.output` of the result region; parse the numbers out of it rather than comparing full strings, except where a string is given. Evaluate by calling `Engine().evaluate([...])` with regions in the order shown.

Phase A (settle, equalities, units, tolerance, errors)
1. Quadratic. `vary x from 0 in q`, `x^2 - 5*x + 6 == 0 in q`, `settle in q` -> status ok, x = 2. Same with guess `10` -> x = 3. A following region `x =` shows `= 3`.
2. 2x2 nonlinear. `vary x from 4.2, y from 2.8 in c`, `x^2 + y^2 == 25 in c`, `x*y == 12 in c`, `settle in c` -> x = 4, y = 3. With guess `2.8` and `4.2` -> x = 3, y = 4. Residuals of both equations <= 1e-8 relative. The whole evaluate call takes < 1 s.
3. Unit example. `vary t from 1 s in fall`, `h := 20 m`, `0.5*g*t^2 == h in fall`, `settle in fall` -> t = 2.01962 s (abs. 1e-4), output text ends with ` s`. Guess `0.01 min` gives the same result within 1e-6 s. Guess `1 m` gives error starting `Units do not match`.
4. Binding and scope. After criterion 3, region `t =` below gives `= 2.0196 s` (6 significant digits as configured) and a region above the result region that mentions `t` still sees it undefined or its older definition (reading order).
5. Tolerance. For case 1 with `accuracy 1e-12 in q` above the result: independent check `|x^2 - 5x + 6| <= 1e-12 * 6`. `accuracy 0 in q` -> error `accuracy must be a positive number below 1`. `accuracy 2` likewise.
6. No solution (equality). `vary x from 1 in z`, `x^2 + 1 == 0 in z`, `settle in z` -> status error, error starts `No solution found`; `x` is not defined afterwards (a later `x =` errors with `x is not defined`).
7. Not converged. Case 1 with guess `10` and `steps 1 in q` -> error starts `Not converged`. Same model with `steps 200` succeeds.
8. Errors by kind: unknown model name in `settle in nothere` -> `No unknowns declared for model "nothere"`; duplicate `vary x from 1 in m` twice -> `"x" is declared twice`; `x + y == 3 in q` with `y` undefined -> `y is not defined`; `5 == 5 in q` -> `does not involve any unknown`; mismatched dimension `x == 3 m in q` with `vary x from 1 s` -> `Units do not match`; constraint region with no result below -> `No result region for model "q" below this region`; constraint placed below the `settle` is not used (solution unchanged).
9. Underdetermined settle. `vary x from 0, y from 0 in u`, `x + y == 2 in u`, `settle in u` -> x = 1, y = 1 (closest to the guess, abs 1e-5).
10. Isolation and compatibility. A sheet without any ` in <name>` region produces identical results to before (existing tests in tests/test_engine.py unchanged and green). Two models `a` and `b` with different unknowns do not interact. Ordinary region `least(3, 4) =` still works (unrelated to the keyword).
11. Parsing: `parse_statement("vary x from 1 m, y from 2 in p")` gives kind `model_vary`, model `p`, guesses `[("x","1 m"),("y","2")]`; `"settle in p"` gives kind `model_result`, goal `root`; `"a <= x <= b in p"` gives two relations; `"x ≤ 3 in p"` equals `"x <= 3 in p"` after normalise.

Phase B (inequalities, optimisation, status marks)
12. Inequality settle. `vary x from 0 in i`, `x^2 == 4 in i`, `x > 0 in i`, `settle in i` -> x = 2; guess `-1` without the inequality gives x = -2; the inequality with guess -1 still gives x = 2 (inequality respected, abs 1e-5).
13. Projection. `vary x from 0, y from 0 in n`, `x + y <= 2 in n`, `least (x-3)^2 + (y-1)^2 in n` -> x = 2, y = 0, value = 2 (abs 1e-5).
14. Unit optimisation. The rectangle example above (`most w*d`, `2*(w + d) <= 20 m`) -> w = 5 m, d = 5 m, value = 25 m² (abs 1e-4); output contains `m²`. Adding `0 m <= w <= 4 m in plot` (chained) -> w = 4 m, d = 6 m, value = 24 m².
15. Infeasible inequalities. `vary x from 0 in f`, `x >= 2 in f`, `x <= 1 in f`, `settle in f` -> error starts `No solution found`, mentions the violated constraint source text. Same with `least x in f`.
16. Unbounded objective. `vary x from 0 in ub`, `most x in ub` (no constraints) -> error (either `Not converged` or `No solution found`; must not hang; wall time < 5 s, step limit enforced).
17. Constraint status marks (optional, may slip to a later spec): after a successful result, constraint regions show output `✓` (satisfied within accuracy) and after failure `✗` on the worst one.

## Phases (total about 3 days)
- Phase A (about 1.5 days): syntax kinds, solver.py (root-finding + closest-feasible via SLSQP for equality only), units, tolerance, errors, binding. Criteria 1-11. Shippable on its own; roadmap line "Solve blocks" can be ticked partially.
- Phase B (about 1.5 days): inequalities, chained relations, `least`/`most`, unbounded/infeasible handling, optional constraint marks. Criteria 12-17.
The developer should implement A first and hand over; B is a separate developer run on the same spec.

## Edge cases
- Guess of 0: scale 1 SI unit for that unknown. Guess with unit and the result closer to zero than tolerance: tolerance is relative to the maximum of both sides and `ref`, so a root at exactly 0 is accepted when `|l-r| <= tol*ref`.
- Unknown named like a unit (`vary s from 1`): local shadowing only inside the model, as for ordinary definitions.
- Unknown also defined earlier (`x := 5`): the guess wins inside the model; after success the model's value replaces `x`.
- Parameters redefined between regions: the environment at the result region is used (reading-order rule).
- Constraint with a function call `f(x) == 2 in p` where `f` is user-defined: allowed (expanded at build time); with a symbolic-only function the lambdify step fails -> `Cannot evaluate at the starting guess`.
- Non-smooth expressions (`abs`, `Max`) accepted; convergence is not guaranteed and failure is reported by the normal errors.
- Very long runtime: the step limit bounds it; GUI recalculation runs in the GUI thread today, so a model that takes seconds will freeze it. Not solved here (see open questions).
- Strict inequalities are non-strict.
- Duplicate result regions for the same model both run, each independently from the declared guesses (not from the previous result).
- Empty guess text (`vary x from  in p`) -> `Missing starting guess for "x"`.
- Save format: nothing changes (regions are plain text in .lsheet).

## IP check
pass (with the flags below). Distinct from the well-known commercial solve-block design in three ways: (a) none of the keyword set is used (the policy-forbidden `Given`, `Find`, `Minerr`, `Minimize`, `Maximize`, `Odesolve`, nor look-alikes); our words are `vary`, `from`, `settle`, `least`, `most`, `accuracy`, `steps`, trailing `in <name>`; (b) there is no visual or ordered block: the vendor construct is a sequence of regions delimited by an opening and a closing keyword region, whereas ours is a set of independent single-line regions joined by a label, collected by reading order, with multiple results per model allowed; (c) unknowns and guesses are declared in a dedicated declaration (not by ordinary definitions above the block), and results are bound by name instead of returned as a function value; tolerance is a per-model labelled setting, not a global constant. What remains common is the idea (unknowns plus constraints plus numeric solve), which the IP policy allows (methods and concepts), and the notation `==`, `<=`, `>=`, which is standard maths and already used in the project. No vendor text, example or screenshot was used: examples (quadratic, circle/hyperbola pair, free-fall time, rectangle in a perimeter budget) are textbook problems chosen independently. Flags for the manager: (1) the manager should confirm the nominative statement in the sources section is acceptable (we read only the repo skill, no vendor pages); (2) skill rule 6: the manager may add a note in decisions.md that the construct "named group of constraint regions solved on demand" is generic, but a patent search has not been done; (3) before 1.0 the legal review the IP policy mentions should include this feature.

## Fits current architecture?
- engine/syntax.py: new statement kinds and fields, tag detection placed before the existing `:=`/`→`/`=` branches (small, additive; backward compatible for text without a trailing ` in <name>`).
- engine/evaluator.py: `Engine.evaluate` pass 2 collects model regions; `_run` gets four new kinds; `Engine.parse` must accept `<=`, `>=`, `<`, `>` relations (`parse_expr` handles them; only `==` has special-casing now). `_numeric` untouched; result text built in solver.py using `format_number` and `dims_to_text`.
- engine/units.py: no change; `measure` used for one-time dimension checks and to obtain SI magnitudes (check that `measure` works with symbols standing for scaled unknowns; otherwise substitute the guess unit factor before measuring).
- engine/solver.py: new, GUI independent.
- gui/regions.py: no change needed for Phase A. Region results already render `RegionResult.output` and errors; long output (`⇒ x = ..., y = ...`) widens the region, acceptable.
- gui/pretty.py: cosmetic check only.
- pyproject.toml: add scipy (production-code change for the developer). Tests: tests/test_solver.py (new) from the acceptance criteria; independent tester writes theirs from this spec.
- document.py / .lsheet: unchanged.

## Open questions for the manager (also candidates for docs/board/decisions.md)
1. scipy as a hard dependency (about 40-60 MB installed, BSD-3) vs. a scipy-free Phase A using `sympy.nsolve` (mpmath, BSD) and an own SQP for Phase B. Recommendation: scipy, lazy import.
2. Keyword names: are `vary / settle / least / most` acceptable, or does Theo prefer others (e.g. `unknown`, `solve numerically`)? The word `solve` is deliberately avoided because it is already the symbolic keyword.
3. Trailing `in <name>` tag vs. a leading `name:` tag. The leading form conflicts with the GUI auto-inserted `:=` on typing `:`, so the trailing form is chosen; confirm.
4. Should result regions also bind a list/vector under one name (waits for the vectors/matrices spec, backlog item 2)? The current design binds each unknown by name only.
5. Recalculation freezes the GUI for slow models (no worker thread today): accept a step limit for now, or schedule a GUI-thread spec?
6. Should constraint regions show a satisfied/violated mark (criterion 17) in Phase B, and should the GUI highlight all regions of a model when one is selected (not specced)?
7. Least-squares fitting, ODE initial-value problems (backlog 14), integer unknowns and global search are out of scope here and need separate specs.
