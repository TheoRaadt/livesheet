# LiveSheet status (2026-11-06, end of session)

Commits this session: `b44ebfc` (spec 017 S1), `05ee4b4` (spec 017 S2); earlier `b71a0de` (spec 022).
Not pushed. **Spec 017 S3 (regression) is done and verified but NOT committed** (waiting for Theo's
approval; message suggestion: "Add linear and polynomial regression (spec 017 S3)"). Last full suite:
2467 passed, 10 xfailed, 0 failed (`QT_QPA_PLATFORM=offscreen pytest -q`, from ~/livesheet-venv).
Untracked on purpose: the two vendor PDFs in docs/ (ip-cleanroom rule 7); `.idea` files stay out of commits.

## Done and accepted
- **Spec 022** (wrapping window-wide tab strip + button band): done, tester PASS, manual updated.
- **Spec 017 S1** (descriptive statistics, normal/uniform/binomial/Poisson): tester PASS, manual
  docs/manual/statistics.md. Code: livesheet/engine/statistics.py.
- **Spec 017 S2** (one-sample / Welch t-tests, chi-square; sample/expected/claim/level/verdict
  tagged lines): tester PASS, M1/M2 fixed, manual. Code: livesheet/engine/stats_tests.py.
- **Spec 017 S3** (fit_linear, fit_poly, predict, r_squared): tester PASS with conditions; D1
  (silently wrong ill-conditioned fits) and D2 (false rank error on float x) fixed by an exact-
  arithmetic centred fit; manual updated; doc examples re-run against the engine. Reviews:
  docs/board/reviews/017-statistics-s{1,2,3}-review.md. Spec 017 is complete.

## Open, next session (in this order)
1. **Commit spec 017 S3** (Theo's approval).
2. **Real-window check on Theo's Mac** (nobody has had computer use; testers always ran headless):
   wrapping tab strip + band (spec 022), page breaks, PDF export, the three formula tabs, demo.lsheet
   layout, specs 010/011/013/014/015, and the new statistics sheets (hypothesis test: type it, change
   `level`, save, reopen; regression fit).
3. **Crash report from Theo**: app closes when switching a tab when run via PyCharm's Run button;
   fine from the terminal. Need the Run-window text and the tab; check QT_QPA_PLATFORM is empty and
   the interpreter is ~/livesheet-venv. Backlog 44. (Spec 022 changed the tab mechanism since, so it
   may already be gone.)
4. **Backlog 62 (new defect)**: statistics functions (`mean`, `predict`, ...) fail inside a user-
   function body (`h(u) := predict(c, u)` gives `u is not defined`); `dot`/`det` work. Small developer
   fix; documented in the manual as a known limitation until fixed.
5. Statistics side-panel tab still has no buttons (spec 017 said no GUI change); a follow-up GUI spec
   could add them. Outline/Data tab placement deferred (spec 022 Q3).
6. Open spec 021 defaults unconfirmed by Theo: no undo for page-break reflow (undo, backlog 4/43, may
   be worth pulling forward), 0.4% PDF shrink with breaks, deleting a break does not move content back.
7. Standing backlog: M6 data components, spec 016 (3D plots, research only), beam FEM F2, document
   quality items (headers/footers, sections), CAS depth, tab-role accessibility (QAccessible).

## Known engine limitations (documented in the manual)
- Bare-unit check gaps (`m^2`, `P/A`, expressions with digits); unit aliases like `u := m/s` break.
- `0 m` loses its unit (distribution functions accept it); `x := 2 m / 1 m` reads as m^2 (use
  parentheses); `e` is Euler's number; `g` is standard gravity (grams are `gm`).
- Seeded sample values come from numpy's default_rng and may change across numpy major versions.

## Process notes
- Testers must never run `git stash/reset/checkout` (a tester did once; recovered, nothing lost).
- Subagents without a Bash tool (mathcad-specialist, documenter) cannot run examples: the manager
  re-runs printed forms against `Engine().evaluate` before accepting docs.
- Git in the mounted folder may leave .lock files; move them to .git/stale-*.

## How to run
`source ~/livesheet-venv/bin/activate && livesheet` (new empty sheet) or `livesheet file.lsheet`.
PyCharm: interpreter ~/livesheet-venv, run module `livesheet`, no QT_QPA_PLATFORM env var.
