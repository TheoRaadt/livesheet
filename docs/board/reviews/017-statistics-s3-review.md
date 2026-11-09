# Review: spec 017 phase S3 (regression), independent black-box

Date: 2026-11-06. Tester. Tests: `tests/test_spec017_s3_review.py` (75 pass, 6 strict xfail documenting defects). Full suite: 2450 passed, 15 xfailed. I did not read `tests/test_regression.py`; I read `livesheet/engine/statistics.py` (regression part) and `solve_least_squares` only after the first behaviour probes, to locate the cause of D1/D2.
Oracles: numpy.polyfit/polyval, and exact rational normal equations (SymPy) for conditioning cases. No chat clarifications with the developer.

## Verdict
PASS WITH CONDITIONS. All 10 acceptance criteria, units, shapes, errors and sheet use behave as specified. One high-severity defect (silent wrong coefficients on offset x data) and two lesser ones; none is a spec deviation, but D1 is a correctness hazard for typical engineering data (years, kilometre posts, large timestamps).

## Defects
### D1 HIGH: silently wrong coefficients for ill-conditioned fits (no error, no warning)
Repro (integer x, float y, degree 2):
`x := [10000,10001,10002,10003,10004,10005]`, `y := [1,3.1,4.9,7.2,8.8,11.1]`, `fit_poly(x, y, 2) =`
Actual `[-0.000399088; -1.99594; 0.000199604]`. Exact (and numpy) `[337351; -69.4493; 0.00357143]`. Even the sign is wrong.
Also: x = 1e6+i, degree 2 (actual `-3.99e-6; -1.997; 1.997e-6`, exact `3.57e9; -7140.9; 0.00357`); x = 1000+i (8 points), degree 3 (actual `[0.056; 18.8; -0.038; 1.9e-5]`, exact `[4.10e6; -12245.7; 12.18; -0.00404]`). Degree 1 stays accurate up to x = 1e6; degree 2 is fine at x = 3000, bad at 1e4.
Cause (seen in code): monomials `x^k` of raw x go straight into `np.linalg.lstsq` (cond about 1e16 or worse), and the rank gate passes. The spec's own criteria don't cover this, but the right outcomes are accurate (centre/scale x internally, then shift the coefficients back, or fit in exact rationals) or a clean error.
Tests: `test_integer_x_offset_quadratic_never_silently_wrong`, `test_offset_x_cubic_never_silently_wrong` (xfail strict).

### D2 MEDIUM: float-typed x gives the false error `Matrix does not have full column rank`
`x := [10000.0,10001.0,...,10005.0]`, same y, `fit_poly(x, y, 2) =` errors; the identical integer-typed x does not (see D1, it returns garbage instead). Fails cleanly but misleading (the data are full rank). Same for x = 1e5 (degree 2/3), x = 1e6 (degree 1, float-typed). Inconsistent between integer and float input. Test: `test_float_typed_x_offset_not_rejected_as_rank_deficient` (xfail strict).

### D3 MEDIUM (shared with S1, not S3-specific): stats builtins are unusable in a user-function body
`c := fit_linear([0,1,2,3],[1,2,2,4])`, `h(u) := predict(c, u)`, `h(10) =` gives `u is not defined` (the definition line itself errors). Same for S1: `h(u) := mean([u, 1])`. `dot`/`det` work in bodies. The spec's user story ("use the fitted formula directly in a later expression") is only met by calling `predict(c, 10)` directly, not through a named model function. Test: `test_predict_inside_user_function` (xfail strict).

### Minor
- M1: `fit_linear(x, y) = m/mm` with x in mm, y in m gives `Units do not match: result is m` (the vector's first element decides). Same pre-existing display-unit behaviour; informational.
- M2: `fit_linear(3, 4)` reports `needs at least 2 points` rather than `needs a vector`; acceptable.

## Judgement of the developer's choices
- Check order (length, degree validity, point count; fit_linear length before count): sensible and tested; matches the spec's listed texts.
- Non-integer degree (1.5, 0.5, -1) and matrix degree all give `degree must be a positive integer`; 2.0 is accepted as integer-valued. Good. A unit-bearing degree gives a clean separate error.
- r_squared unit rule: dims of prediction and y must match else `Units do not match`, constant check after that. Reasonable; result dimensionless and correct with units (0.852632).
- predict keeps x's shape (row stays row, column stays column, scalar stays scalar). Good; matrix x is rejected with the spec text; 1xN or Nx1 coefficients both accepted, hand-built coefficient vectors work.
- The one invented text `predict() needs a vector of coefficients`: fine, consistent with neighbours; fires for a scalar and for a matrix. Needs an entry in the manual's error reference.
- mm vs m disclosure confirmed: slope prints plain `2000`, values correct in SI (`predict(.., 4 mm) = 9 m`, `predict(.., 4 m) = 8001 m`). Acceptable but surprising; documenter should mention.

## Verified OK
Criteria 1-10 exact texts; noisy fit and r_squared 0.852632 (matches numpy); degrees 1-4 vs polyfit (rel 2e-5); exact integer fits print exact `[1; 0; 1]`; unsorted/duplicate x; degree = n-1 interpolation allowed, n rejected; row/column mixes; per-term units (`[1 m; 2 m/s; 0 m/s²]`, dimensionless x or y); predict with unit scalar and vector x, missing unit gives `Units do not match`; tiny/huge scales (1e-6, 1e9); year-like x (1990..2020) degrees 1-2; 2000-point cubic fast; use in a sheet (define, later use, `c[1]`, `len(c)`, arithmetic, `mean` of the result), save/load roundtrip; `solve_least_squares` and S1 unaffected.

## Coverage gaps
- Real app NOT launched: no computer-use tools available to this agent, so no visual check of printing or dialogs. S3 adds no GUI.
- Plot integration of predict (spec says plotting-free) not tested.
- Symbolic data (`a` in y) only checked for no crash.
- `.lsheet` has no new format surface.

## IP red flags
None. Names are plain English, error texts are the spec's or generic; no vendor strings seen.
