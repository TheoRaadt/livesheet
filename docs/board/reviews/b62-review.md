# Review: backlog 62 (stats builtins in user-function bodies)

Tests: tests/test_spec_b62_review.py (12 pass, 1 strict xfail). Black-box, engine level only.
Covered: unit-carrying args (mean/median keep m; mismatch gives "Units do not match"; unit rejection by normal_cdf gives the same message as a direct call), seeded *_sample in bodies equal direct calls and are deterministic, wrong arg counts inside bodies and on user-function calls give "Wrong number of arguments" (no raw TypeError), engine errors pass through, nested user functions, scalar/vector results match direct calls.

Defect B62-R1 (minor, xfail strict): `f(u):=mean()` then `f(3) =` reports "f is not defined"; direct `mean() =` reports "Wrong number of arguments". Expected the latter.

Gaps: no GUI run (engine-only change); unseeded randomness not tested. No IP red flags seen.
