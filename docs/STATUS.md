# LiveSheet status (2026-11-09, end of session)

Commits this session: `e97b60e` (backlog 62 fix), `604ffb3` (docs + review tests for 62), plus the
end-of-session commits listed in `git log` (specs 023, 025, 026 and board/manual updates).
Not pushed. Untracked on purpose: the two vendor PDFs in docs/ (ip-cleanroom rule 7); `.idea` files
stay out of commits.

## Done and accepted
- **Backlog 62** (stats functions inside user-function bodies): fixed, tester PASS (B62-R1 minor open as backlog 63), manual updated.
- **Spec 023 drag-to-move**: root cause was a click-then-press arriving as a double-click (started editing instead of
  moving). Fixed; tester PASS (56 tests); manual docs/manual/moving-regions.md. Real-window check still to do.
- **Spec 025 larger Standard toolbar** (own vector icons, icon+label, icon-only on narrow windows): tester PASS;
  manual updated. Real-window check still to do (wide/narrow, dark mode, docked left).
- **Spec 026 Statistics (37) + Optimization (9) tab buttons**: implemented (see log.md for tester status).
- **Spec 027 Outline tab**: developer was mid-work when the session ended; check docs/board/log.md and
  `git status` for its state before relying on it. Tester review and manual update still pending.

## Specs written and IP-approved, not yet implemented
- **024 function autocomplete** (popup, Down/Up, Tab, Esc; engine/completion.py from the real builtin registry).
- **028 data import core** (CSV -> datasets, embedded .lsheet v5, Data tab). Needs Theo's answers to the open
  questions at the end of the spec (embed vs link, size limits, mixed-unit matrix, broken dataset, source path, JSON/Excel).

## Open, next session (in this order)
1. Check 027 state (log.md), run the full suite (`QT_QPA_PLATFORM=offscreen pytest -q`), tester for 027,
   documenter for 026/027 (main-window.md Tab strip text still calls Statistics/Optimization placeholders).
2. **Real-window check on Theo's Mac**: drag-move (click then drag a selected region, Esc, hand cursors, edge scroll),
   toolbar (wide/narrow, dark mode), new Statistics/Optimization/Outline tabs, wrapping tab strip, page breaks,
   PDF export, formula tabs, save/reopen.
3. **Backlog 64 (Theo)**: definite-integral button/template in the Calculus tab (engine already supports
   `integrate(expr, (x, a, b))`; the ∫ button inserts an unclosed `integrate(`).
4. Possible flaky tests: tests/test_spec023_review.py::test_open_hand_on_hover_arrow_on_empty_canvas (order-dependent?)
   and the real-settings check in test_spec025_review (fails if other suites run concurrently). Tester of 026 was asked to look.
5. Evaluation-order error hint: "x, y are not defined" could mention that definitions must come earlier (left to right,
   then top to bottom); candidate backlog item.
6. In-app help text does not mention Shift+arrow nudging (50 units).
7. **Crash report from Theo**: app closes when switching a tab via PyCharm's Run button (backlog 44); need Run-window
   text and the tab. May already be gone since spec 022.
8. Then specs 024 and 028; standing backlog: M6 data components, spec 016, beam FEM F2, document quality, CAS depth,
   undo (no undo exists; drag-move shipped without it), tab-role accessibility.

## Known engine limitations (documented in the manual)
- Bare-unit check gaps (`m^2`, `P/A`, expressions with digits); unit aliases like `u := m/s` break.
- `0 m` loses its unit; `x := 2 m / 1 m` reads as m^2 (use parentheses); `e` is Euler's number; `g` is standard gravity.
- Seeded sample values come from numpy's default_rng and may change across numpy major versions.
- `f(u) := mean()` then `f(3) =` says "f is not defined" (backlog 63).

## Process notes
- Testers must never run `git stash/reset/checkout`. Tests must use an isolated QSettings (temp INI), never the real one.
- Plain `pytest` in the project `.venv` crashes (macOS hidden flag); use `~/livesheet-venv` or `chflags -R nohidden .venv`.
- Subagents without a Bash tool (mathcad-specialist, documenter, gui/modeling-specialist) cannot run examples or append to log.md.
- Git in the mounted folder may leave .lock files; move them to .git/stale-*.

## How to run
`source ~/livesheet-venv/bin/activate && livesheet` (new empty sheet) or `livesheet file.lsheet`.
PyCharm: interpreter ~/livesheet-venv, run module `livesheet`, no QT_QPA_PLATFORM env var.
