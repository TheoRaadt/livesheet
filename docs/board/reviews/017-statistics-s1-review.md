# Review: spec 017 phase S1 (descriptive statistics and distributions)

Reviewer: tester, 2026-11-06. Black-box, from docs/board/specs/017-statistics-core.md (S1 criteria 1-19) and decisions.md. The developer's tests/test_statistics.py was not read. Implementation read only to run it.

## Verdict
PASS. No defects at critical, major or moderate severity. Two minor observations and one known limitation (below). Recommend merge.

## Tests added
tests/test_spec017_s1_review.py: 107 passed, 1 xfailed (the disclosed `0 m` limitation, strict xfail so it flips loudly when fixed). Full suite: 2270 passed, 9 xfailed.
Coverage: criteria 1-19 literally; numerics against numpy/scipy (quantile, cov/corr, normal pdf/cdf/ppf round trip, binomial pmf/cdf for every k over several (n,p), Poisson pmf/cdf/quantile over lambda 0.5..40); quantile definition checked on a q grid; sampling checked statistically (KS test for normal and uniform, chi-square against the exact binomial pmf over all 2000 draws, Poisson mean/variance, degenerate p=0/1); determinism across separate regions, repeated evaluations and fresh Engines; unit propagation (mean/median/mode/stdev/quantile keep the unit, variance squares it, covariance multiplies, correlation dimensionless, wrong display unit rejected); 20 distribution/sampling calls with a unit argument all rejected; error texts for every spec-named error; empty vector, 1-element, constant vector, mixed units, symbolic entry, row vs column vector, 10000-element vector, 1e300 and large-offset values; use inside real sheets (define, `=`, later statements, z-score pipeline, vector arithmetic inside arguments, user definition shadowing a builtin).

## Developer-disclosed items, judged
- Negative / non-integer k is an error (`k must be a non-negative integer`): acceptable. Matches criterion 17 for non-integer; negative is spec-ambiguous (the spec's "k < 0 returns 0" aside contradicts "k a non-negative integer, else an error"). Recommend the spec text be tidied; behaviour is safe and consistent across binomial and Poisson.
- `uniform_quantile` accepts p in [0,1]: acceptable and mathematically sensible (the inverse of a bounded CDF).
- `poisson_quantile(1, lambda)` errors: acceptable (the true quantile is infinite). Error text invented, clear. `poisson_quantile(0, ...)` gives 0.
- Invented error texts: all read well and follow the "X must be ..." family. Not spec-mandated.
- `0 m` loses its unit: confirmed, `normal_cdf(0, 0 m, 1) =` gives `= 0.5` (xfail test). Same family for any zero-with-unit argument. Low severity: a zero-valued unit quantity is rare as a distribution argument and the result is still numerically correct. Root cause is in the generic unit handling (zero drops its unit), not in statistics.py.
- No Statistics-tab buttons: consistent with "gui: no change". Not a defect for S1; flag for a later GUI-discoverability item.

## Defects
None above minor.

Minor 1 (display precision, spec wording): results print with 6 significant digits, so `normal_quantile(0.975, 0, 1) =` prints `= 1.95996`, while criterion 13 writes `= 1.959964`. Value is correct; relative difference 2e-6 versus the spec's stated 1e-6 tolerance if compared on printed text. Spec should say "about 1.95996" or compare the value, not the text. Same for several other criteria (`4.57143`). Not an implementation fault.

Minor 2 (pre-existing, not S1): `(2 m) / (1 m)` is fine, but `2 m / 1 m` evaluates to `2 m²` (a unit literal after `/` is read as a product), so a dimensionless ratio typed without parentheses produces a unit-carrying value that the distribution functions then correctly reject. Reproduce: `x := 2 m / 1 m` then `x =` gives `= 2 m²`. Worth a separate look by the manager; not a statistics defect.

## Observations (no action required)
- `mean`, `median` etc. of exact integers return floats, and `mode` returns the original entry (keeps exact form and unit). Fine.
- Unit of `mode(w) =` bare prints in base SI (`0.004 m`), as for any mm value (spec 018 convention).
- `e` is Euler's number, so `e := []` is silently accepted and later `mean(e)` gives 2.71828 (existing constant-shadowing behaviour, not S1).
- Sampling uses numpy `default_rng(seed)`: reproducible for a given numpy version; sample values for a fixed seed may change across numpy major versions. Worth one sentence in the manual.

## GUI check
Not performed. This agent session has no computer-use (computer_*) tools, so I could not launch LiveSheet on the Mac. Because S1 adds only engine functions (no GUI, no .lsheet change), the headless Engine path used above is the same path the GUI takes; still, Theo's real-window check of a sheet using these functions remains outstanding.

## Coverage gaps
No test of the Statistics formula tab (no buttons exist). No cross-platform check of seeded values. Locale decimal comma input not tested (engine-wide topic).

## IP red flags
None. Function names are plain statistics terms or the project's own `<dist>_pdf/_cdf/_quantile/_sample` family; no copied strings, assets or docs. scipy/numpy are approved BSD dependencies. Error texts are the project's own.
