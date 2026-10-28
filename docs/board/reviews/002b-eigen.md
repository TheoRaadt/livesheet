# Review 002b: eigen-analysis, rank, norm, least squares (tester, black-box)

Commit under test: 2982a43 (working tree). Spec: docs/board/specs/002-vectors-matrices.md, section "# 002b".

## Tests added
tests/test_matrices_b_blackbox.py: 48 test cases (47 pass, 1 strict xfail), written from the spec only (tests/test_matrices_b.py not read). Reference values from NumPy / plain mathematics. Covers acceptance criteria 1-12 one-to-one, plus: random symmetric 4x4 (6 seeds) with A*V = V*diag(lambda), ascending order, unit columns, sign convention; the same residual computed inside the engine (`norm(A*V - V*diag(L))`); least squares vs normal equations (5 random 6x3 systems); 8x8 exact symmetric integer and 8x8 non-symmetric rational under 2 s; symbolic entry with `=`; mixed exact/float; determinism and orthonormality for repeated eigenvalues; multiplicity; eigenvectors dimensionless; norm units (vector, matrix, mixed -> error); rank ignoring units and float tolerance; defective vs near-equal eigenvalues; 1x1; rhs dimension mismatch.

## Results
Full suite (`QT_QPA_PLATFORM=offscreen ~/livesheet-venv/bin/python -m pytest -q`): 653 passed, 2 xfailed (1 mine = E1, 1 older), 0 failed.
All 12 acceptance criteria hold, including exact output strings. 8x8 cases finish well under 2 s.

## Defects
- E1 (low, spec vs implementation, strict xfail `test_definition_then_arrow_gives_exact`): `A := [1, 2; 3, 4]`, `x := eigenvalues(A)`, `x →` shows `→ [-0.372281; 5.37228]`. The same call written directly (`eigenvalues(A) →`) gives the closed form `[5/2 - √(33)/2; 5/2 + √(33)/2]`. Spec only defines `→` on the call itself, so this is a gap, not a clear violation; see judgement below.

## Judgement of the developer's deliberate choices
1. Definitions (`x := eigenvalues(A)`) are always numeric: ACCEPTABLE but surprising (E1). Document in user docs, or decide whether definitions should keep exact values (needs a manager decision; also affects other functions).
2. Eigenvalues/eigenvectors need homogeneous units: ACCEPTABLE, consistent with spec ("for a homogeneous matrix"). `[1 m,2 m;3 s,4 s]` -> `Units do not match`.
3. rank ignores units: ACCEPTABLE (spec: rank is dimensionless; mixed-unit rank is unspecified). `rank([1 m, 2 s; 3, 4]) =` gives 2 with no error; mathematically meaningless but harmless.
4. Singular square A in solve_least_squares reports "Matrix does not have full column rank": ACCEPTABLE and consistent with AC 11.
5. Defective detection by 1e-8 singular-value threshold: ACCEPTABLE with a caveat. `eigenvectors([1, 1; 0, 1.0000000001]) =` is reported defective although eigenvalues differ by 1e-10 (numerically indistinguishable, so an error is defensible). `[1,0;0,1.001]` works.

## Observations (not defects)
- `eigenvectors([0,-1;1,0]) =` gives `[0.707107, 0.707107; 0.707107i, -0.707107i]` (complex, unit columns, first non-zero component positive). Fine.
- `eigenvalues(...) + 1` gives `Cannot add a scalar to a matrix` (002a rule, consistent).
- `rank([a,b;c,d]) →` gives 2 (generic rank); `norm([a;b]) →` gives `√(|a|² + |b|²)`.
- `eigenvalues` of a 5x5 companion matrix with `→` gives `No closed form found; use =` as specified.

## Coverage gaps
- No GUI run this session (no computer-use tool); the Qt tests were not extended for 002b.
- Complex-valued input matrices, matrices larger than 8x8 with float entries (performance), and very large/small magnitudes (1e300) are untested.
- Exact-mode eigenvectors with repeated eigenvalues (`→`) not tested for determinism.

## IP red flags
None. Function names are `eigenvalues`, `eigenvectors`, `rank`, `norm`, `solve_least_squares` (generic English / own). No vendor strings found in the output messages I saw.
