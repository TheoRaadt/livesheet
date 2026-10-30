# LiveSheet status (2026-10-30, end of session)

Commits: aca0667 team+policy+licence · f2b6e66 specs · 3d74db5 spec 001 · 364f057 001 fixes · bbcad16 spec 002a ·
5a3f973 002a fixes · c0b25a2 GUI fixes · 280f2c3 003A · b7beb0f 003A fixes · 39f1c5b 003B + G4 fix · 2982a43 spec
002b · ef12bec spec 004 A1 · b862444 spec 004 A2 · 288c307 specs 006-009 + calculus C1-C4 + GUI polish ·
cea2cc6 spec 009 D1 fix + GUI tests · **2df0955 spec 010 ODE solving (phase A+B)** · **aa1a14f spec 010 review
fix pass (clean-room comment fix, D1/D2 notes)**. Pushed to origin/claude/ga-mk3uos (this session's working
branch); not merged to main/GitHub.

**This session:** implemented spec 010 (ODE solving — symbolic `dsolve` with numeric `solve_ivp` fallback),
both phases A and B together per the already-approved spec and decisions.md entries (all 7 open questions
pre-resolved, no new queries to Theo needed). Added `engine/odesolver.py`, extended `engine/syntax.py`'s model
grammar with `ode`/`start`/`over`/`evolve` keywords, and factored the `over` sampling sub-grammar out of
`engine/plotting.py` into a shared helper (spec 004's plot tests unaffected). Independent tester review passed
with no blocking defects; it also caught two pre-existing vendor-name mentions ("Mathcad") in code comments
(`evaluator.py`, `units.py`, present since the first commit) — fixed in a follow-up commit, along with two
documented (not fixed) design notes: D1 (multiprocessing-timeout guard needs `if __name__ == "__main__":` for
standalone `engine/` use) and D2 (~0.6-1.2s blocking cost per `evolve` region, see Open/unverified below).
Full suite: **1182 passed, 2 xfailed, 4 pre-existing/unrelated failures** (confirmed unrelated via git-stash
comparison against the pre-spec-010 commit: `test_50x50_float_performance`, 3× in `test_solve_b.py`; the 2
xfails are the same pre-existing ones noted last session). No real-app manual pass for spec 010 — no
`computer_*` tool available this session (headless sandbox, not Theo's Mac); same standing gap as 006-009.
Two PDFs Theo placed in docs/ (`Engineering With Mathcad.pdf`, `calculus-10th-edition-anton.pdf`) remain
deliberately untracked — never used, never committed, see ip-cleanroom skill rule 7.

## Done
- Licence: MIT OR Apache-2.0. Clean-room IP policy (docs/IP-POLICY.md). Team: mathcad-specialist,
  gui-specialist, modeling-specialist, developer, tester, manager (CLAUDE.md, docs/PLAN.md).
- 001 ranges and tables, 002a vectors/matrices core, 002b eigen/rank/norm/least squares, 003 solve models
  phase A+B, 004 plots phase A (A1 engine + A2 document/GUI/PDF), 006 dialog-based plot configuration (D1
  fixed), 007 main window chrome (toolbars/side panel/theming; D1 toolbar-squash fixed), 008 dialog-based
  matrix/vector insertion, 009 component-wiring canvas core (D1 Connect-menu fallback fixed), 010 ODE solving
  phase A+B (symbolic `dsolve` + numeric `solve_ivp` fallback). All implemented, independently reviewed, and
  committed.
- Calculus defects C1-C4 fixed (`limit` keyword form, `ln` vs `log` display, friendly ambiguous-variable
  errors, non-integer series-order error); ∫ and d/dx real notation on the sheet; Math toolbar `e`, `i`, ⁿ√.
- Real-app tests on the Mac: 001, 002a, 003A passed after fixes (colon handling, matrix grid, safe Save As
  defaults).

## Open / unverified
- **Standing gap across specs 006/007/008/009/010: no computer_* tool was available this or the prior session
  for any review, so none of their real-window manual passes are done.** Checklist: Insert menus/"here"
  context-menu entries, dialog fill/Apply/OK/Cancel round trips, drag gestures (toolbar reorder, component
  wiring, plot resize), Appearance visual restyle, canvas-colour stability, slow-recalc status label, first-run
  hint, PDF export + vector sharpness, save/reopen, and (new, 010) typing an `ode`/`start`/`evolve` model on
  the real canvas and confirming the rendered formula/table. Needs Theo directly or a session with screen/
  input permissions granted.
- Layout: tall tables/grids can overlap regions below; wide results run off-window (backlog 20, 24); plots may
  overlap regions below until backlog 20 (accepted for phase A); reading order is unstable when two regions
  share the exact same position (backlog 28).
- Known limits: zero from SymPy loses its unit; `f(M) := det(M)` unsupported; local optima only; solves run on
  the GUI thread; `diff(EXPR)` 1-arg auto-detect form isn't given the ∫/d-dx display notation (only the 2-/3-arg
  explicit-variable forms are); components don't read/write ordinary sheet variables yet (spec 009, by design).
- Decisions pending: product name trademark check; notation review before 1.0; a short human/legal sanity
  check on specs 006/009's interaction techniques (lower risk than rejected designs, still flagged, see
  decisions.md); lawyer review before public 1.0; whether to push to GitHub.
- Multiple sessions this run hit a recurring "Qt platform plugin offscreen" hard-abort in the shared `.venv`;
  recreating `.venv` fixes it every time (a targeted reinstall doesn't) — likely multiple agents/sessions
  sharing one `.venv` concurrently, not corruption per se. No permanent fix yet, just a known recovery step.
- Spec 010: every `evolve`/`evolve symbolic` region costs roughly 0.6-1.2s of blocking main-thread time for
  the subprocess-spawn timeout guard around `dsolve`, even on the simplest example — so spec 007's
  "Calculating..." indicator will now visibly trigger on sheets that previously wouldn't show it. Not a bug,
  just recorded here for a future session to decide whether it needs optimizing (e.g. a warm worker pool
  instead of spawning fresh each time).

## Next steps
1. Theo's real-window pass on specs 006/007/008/009/010 (see checklist above; now includes 010's own
   `ode`/`start`/`evolve` round trip).
2. Specs from mathcad-specialist (assumptions, rewrite rules, context menu) for M3/M4; backlog 7a (document
   structure/ToC/index) and 8a (dataset import + reference data); M5 (statistics/optimization, items 29-30);
   M6 (data-source/nested-sheet/script components, items 32-34) once 009's core is verified real-window.

## Tester practicalities (Mac)
LiveSheet runs from ~/livesheet-venv (pip install -e). Terminal is click-only for agents; Theo starts the app. Window must not be in a
full-screen Space unless system key combos are granted. Dialog tests: Cancel only, never save over examples/.
