# Review 002a Vectors and matrices core

Spec: docs/board/specs/002-vectors-matrices.md (002a only). Reviewed commit bbcad16 (HEAD). Tester, 2026-10-27.

## Verdict
Part A (headless): PASS with minor defects M1-M6. Part B (GUI): SKIPPED, no LiveSheet window is open (see below).

## Tests added
tests/test_matrices_blackbox.py: about 190 test cases (parametrized: 86 expected outputs, 47 exact error texts, plus targeted tests). Independent expectations come from NumPy 2.2.6 / SymPy in the file, not from the developer's tests. Covers all 38 acceptance criteria, unicode (· × − π √ ² α Δ 日本 ≔), whitespace/layout variants, empty/ragged/nested/malformed literals, indexing out of range (0, negative, too many, float, on scalar), slices incl. `[:, :]`, chained indexing, symbolic entries (det, inv, transpose, trace, power, hadamard, expand, substitute, solve_system), values captured at definition, mixed units and unit conversion, zero entries with units, interaction with spec 001 `table` (matrix indexing and matrix cells per range value), range variables inside literals/indices (error), name clashes (`eye`, `det`, `zeros`, `nrows`, `T`, `A` = ampere before definition), 10/11/12/200 placeholder boundary, numeric round trip, random 2..8 float matrices vs NumPy (det, inv, solve, product, trace), exact integer results, float singular tolerance, 50x50 and 200x200 performance.

## Results
- Spec numeric examples (criteria 8-27) re-computed with NumPy/SymPy: all correct (e.g. K x = F gives 13.3333 / 16.6667 m, det(A) = -2, 3x3 dets 6 and 0).
- Full suite: 392 passed, 3 skipped, 12 xfailed (xfail strict = the defects below), 0 failed. All 38 criteria pass except the deviations M2 and M6.
- Performance: 50x50 float det 0.07 s, inv 0.09 s, solve 0.08 s, A*A 0.6 s, A^3 1.1 s (all < 2 s as required); det of 50x50 matches NumPy to 1e-4 relative. eye(200) and ones(200,200)^2 under 1 s.

## Defects (minimal repro)
- M1 (minor, unit loss on zero): all-zero or zero-result unit matrices lose their unit: `[0 m, 0 m] =` gives `= [0, 0]` (expected `[0, 0] m`); `[0, 0]*m =`, `zeros(2,2)*m =` same; `[0 m, 1 m]*[1 m; 0 m] =` gives `= 0` (expected `0 m²`); `[0 m, 1 s] =` prints `[0, 1] s` (zero gets the other unit / loses its own). Same root cause as scalar `x - x` (SymPy collapses `0*m` to 0); spec 001 worked around it for tables. Mixed-unit solve results show the same effect (`solve_system([1 m, 2 s; 3 m, 4 s], [1; 2]) =` gives `[0; 0.5] s⁻¹`).
- M2 (spec deviation, criterion 3): `[0.5, 1/3] →` gives `→ [0.5, 1/3]`, spec says `→ [1/2, 1/3]`. Floats stay floats (same as scalar `0.5 →`); decision: change spec or code.
- M3 (spec edge case): `f(M) := det(M)` then `f([1, 2; 3, 4]) =` gives error `f is not defined` (the definition fails with `det() needs a matrix`, because the parameter M is a plain symbol at definition time). Spec says "Named function definitions may take matrices (f(M) := det(M))". Functions with fixed matrices in the body (`f(x) := A*x`, `g(x) := [x, 2*x]`) work.
- M4 (minor): `2^A =` gives python/sympy text `Matrix Power not defined`; no spec text for it, should be a clean LiveSheet message.
- M5 (performance risk, no spec guarantee): symbolic 6x6 `det(A) →` takes about 87 s and blocks the GUI thread (test skipped, remove the skip to reproduce). Consider a size/time guard for symbolic matrices.
- M6 (spec 38, wrong message): indexing or calling matrix functions on an undefined name gives the wrong error: `B[1] =` says `Only matrices can be indexed`, `det(B) =` says `det() needs a matrix`; spec wants `B is not defined` (use before definition). Order of evaluation itself is correct (defined-before-use works).
- Pre-existing, not 002a: `min(5, 6) =` gives `can't multiply sequence by non-int of type 'Mul'` (Python builtin leaks; `Min`/`max`/`Max` work). A non-breaking space between `]` and `*` is a Syntax error (NBSP inside ranges `1 to 3` works). Unit `mph` is unknown.
- Observations: `[det([1,2;3,4]), 1] =` and `[x, x] =` (x a vector) give `Nested matrices are not supported` (textual nesting check; acceptable per spec, but a function call that returns a scalar is rejected too). `[1 2]` is `[2]` (implicit multiplication, as the spec warns). `A [1, 1]` with a space is a product, not an index. `A =` before `A` is defined shows `= 1 A` (ampere), since the spec's example name A is a unit; the user definition wins afterwards. `a := 1` placed after `M := [a, b; c, d]` does not retroactively fill M (values captured at definition).

## GUI session log (Part B)
Skipped as instructed. computer_list_apps shows only an installed, not running `com.apple.python3` ("Python", isRunning false); nothing named LiveSheet is running, so there is no window to request access to. I did not launch anything. Not verified: typing `A[1, :]` keeps the colon and `x:5` still becomes `:=` in the GUI (engine side: `x:5` is a Syntax error; the `:=` conversion must be a GUI input feature), matrix result placement next to its input, 10x10 and 12x12 rendering, table display, File menu dialogs. Note for the check: a 10x10 matrix result is one long text line (about 270 characters for eye(10)), which is likely to overlap neighbouring regions in the GUI.

## Coverage gaps
- No real GUI run for spec 002a or 001 yet.
- No .lsheet round trip with matrix regions.
- 002b functions (eigen, rank, norm, least squares) are out of scope and not implemented (`norm` is undefined).
- Complex matrices only lightly tested (inv, det, scalar multiples).

## IP red flags
None. Names (det, inv, transpose, trace, dot, cross, eye, zeros, ones, diag, hadamard, nrows, ncols, len, solve_system) are generic textbook terms or the spec's own; bracket/semicolon notation is generic. No vendor strings in code or tests. Not legal advice.

## Fix round (developer, 2026-10-27)
- M1 fixed for what is feasible: zero entries now keep their unit through literals (`0 m`), scalar multiply/divide, add/subtract, negation, hadamard and matrix products (the zero is kept as an unevaluated product/sum). A matrix whose zeros carry units shows one shared unit, or per-element units if mixed. Known limitation: results computed inside SymPy (`det`, `inv`, `solve_system`, scalar `x - x`) still drop the unit of a zero result, so e.g. `solve_system([1 m, 2 s; 3 m, 4 s], [1; 2])` can show a zero without its unit.
- M2: code stays (float literal stays float); test now asserts that. M3: backlog, xfail kept with note.
- M4: `2^A` gives "A matrix cannot be used as an exponent". M5: `det`, `inv`, `solve_system` on matrices with symbols above 5x5 give "Matrix too large for symbolic evaluation (max 5x5); use numeric entries". M6: indexing or matrix functions on an undefined name give "B is not defined" (so `f(M) := det(M)` now says "M is not defined").
- Non-002a: `min(5, 6)` gives "Not a function: min" (`min` is the unit minute; use `Min`). NBSP is treated as a space.
