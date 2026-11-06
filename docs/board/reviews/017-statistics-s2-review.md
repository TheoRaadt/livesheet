# Review: spec 017 phase S2 (hypothesis tests), independent black-box

Reviewer: tester. Date: 2026-11-06. Verdict: PASS (no blocking defects; 3 minor, 1 note).

Tests: `tests/test_spec017_s2_review.py` (37 tests, written from the spec before reading the developer's tests, which I did not read).
Full suite: `QT_QPA_PLATFORM=offscreen ~/livesheet-venv/bin/pytest -q` -> 2353 passed, 9 xfailed, 0 failed.

## Numerics (independent oracle: scipy.stats / numpy)
- One-sample t: t = 1.414214, df 4, p = 0.2302 (two-sided); one-sided < and > for several claimed values equal scipy `alternative=less/greater`; claimed value = mean gives t = 0, p = 1.
- Welch: criterion 4 (t = -1, df = 8, p = 0.346594); an unequal-size, unequal-variance pair matches scipy and a hand-coded Welch-Satterthwaite df; one-sided variants match; sample 1/2 follow reading order.
- Chi-square: x = 20, df 3, p 1.6974e-4 (scipy), rescaled proportions `[1,1,1,1]` and an uneven rescale case match `scipy.stats.chisquare`.
- level 0.0001 -> fail to reject, 0.001 -> reject, default alpha 0.05, level line before the data lines works.
- Units: mm sample with `12 mm` and `0.012 m` claims give identical t; `12` or `12 s` -> "Units do not match"; mm vs m two-sample compatible (t = -1); mm vs s -> Units do not match.
- Output matches `⇒ (fail to )?reject H0 (p = <v>, alpha = <v>)`.

## Criteria 1-18
All met (error texts 8-16 compared verbatim; parse kinds per criterion 18; names bound only on success; tag below verdict ignored).
Regression: variables/functions named sample, level, expected, claim, verdict, sample2 (scalars, vectors indexed, function definitions) work; tags named like keywords (`in claim`, `in sample`) work; solve (003) and ode (010) regions on the same sheet are unaffected; two independent test tags do not interact; save/load of a sheet with a test region round-trips, version stays <= 2, no format change.

## Judgement of the developer's disclosed choices
1. Per-line validation (errors appear at the offending region, repeated at verdict for claim shape): acceptable and arguably friendlier. Side effect, see M2.
2. `expected` values must be positive: acceptable, matches the spec's edge case (spec only mentions zero where sample is non-zero; the stricter rule also rejects zero where sample is 0; conservative, fine).
3. Keyword only before space / `[` / `(`: acceptable; `sample2 in g` behaves exactly like any ordinary `x in g` ("A relation is required before ..."), which is pre-existing behaviour.
4. Chi-square with units = UnitError: acceptable, matches "both vectors must be dimensionless".
5. ~14 invented error texts: reasonable, plain wording, no vendor flavour. They are not in the spec, so the documenter should list them in errors.md from the code.
6. Chi-square p printed `0.000169742` instead of `1.70e-4`: spec text is a sketch; value is correct and consistent with the engine formatter. Accept (note for the manual).

## Defects
Blocking: none.
- M1 (minor): overflow gives a raw Python text. Repro: `sample [1e300,2e300,3e300] in c`, `claim mean == 0 in c`, `verdict in c` -> error `(34, 'Result too large')`. Expected: a plain engine message (e.g. "Result too large"). No crash, no NaN.
- M2 (minor): when the `expected` line has the wrong length, the verdict region shows a different error than the real cause. Repro: `sample [1,2,3,4] in b`, `expected [1,1,1] in b`, `claim mean == 7 in b`, `verdict in b` -> expected line errors correctly, verdict says `claim "mean == 7" does not use an expected line`. Acceptable (that is also true), but with `claim fits` the verdict repeats the length error, so only the mismatched-claim case is slightly confusing.
- M3 (minor, spec inconsistency, not a code defect): spec sketches `p = 0.2302` yet criteria show `0.230200`; printed output uses 6 significant digits with trailing zeros dropped. Fine.
- Note: `claim mean != 7`, `<=`, `>=` are rejected with the three-forms error (spec lists only ==, <, >). Fine.

## Coverage gaps
- Real app not launched: this agent has no computer-use (computer_*) tools in this session, so the GUI rule could not be satisfied. The change touches no gui/ or document.py code, so risk is low, but a GUI smoke (type a test sheet, change level, save/reopen) is still outstanding for the manager or a session with computer access.
- No test for region ordering across pages or for hypothesis-test regions placed side by side (left-to-right) beyond the plain list order.
- Large-sample performance not measured.

## IP red flags
None seen in stats_tests.py / syntax.py / evaluator.py changes: keywords sample/expected/claim/level/verdict are LiveSheet's own; error texts are original; no vendor names or copied strings.
Reminder: the untracked `docs/Engineering With Mathcad.pdf` and `docs/calculus-10th-edition-anton.pdf` sit in the repo tree; per ip-cleanroom rule 7 the developer/tester must not read them and they must never be committed. I did not open them.

## Process incident (disclosed)
While probing I ran `git stash` once in the working copy, which briefly removed the developer's uncommitted tracked edits (log.md, evaluator.py, syntax.py); I immediately ran `git stash pop` and verified `git status` shows the same modified files, and the full suite is green afterwards. No data lost; no production file edited by me.
