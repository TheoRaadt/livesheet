# LiveSheet status (2026-10-29, end of session)

Commits: aca0667 team+policy+licence · f2b6e66 specs · 3d74db5 spec 001 · 364f057 001 fixes · bbcad16 spec 002a ·
5a3f973 002a fixes · c0b25a2 GUI fixes · 280f2c3 003A · b7beb0f 003A fixes · 39f1c5b 003B + G4 fix · 2982a43 spec
002b · ef12bec spec 004 A1 · b862444 spec 004 A2 · **288c307 specs 006-009 + calculus C1-C4 + GUI polish** ·
**cea2cc6 spec 009 D1 fix + GUI tests**. Not pushed to GitHub (17 commits ahead of origin/main).

**This session:** picked up substantial spec 009 (component-wiring core) work left uncommitted/unlogged by an
interrupted prior session, found and fixed two real regressions before committing (document.py writing `wires`/
component fields unconditionally, breaking backward compatibility; spec 007's D1 toolbar-squash defect, root
cause: a toolbar stuck `isFloating()` surviving both headless restore and Theo's real on-disk preferences).
Completed the spec 008 (matrix dialog) review, which had been blocked by a hanging test (`mock.patch.object
(QMenu, "exec", ...)` doesn't intercept a live Qt instance's call — fixed with `QTimer.singleShot` + real
`QTest` key events). Completed the spec 009 independent review (tester), found and fixed D1 (no menu fallback
to the pixel-exact port right-click for "Connect...") plus added the missing `tests/test_wiring_gui.py` the
spec's own architecture section called for. Full suite: **1129 passed, 2 xfailed** (both pre-existing/unrelated:
E1 002b eigenvalues-as-numeric, M3 `f(M):=det(M)`). Two PDFs Theo placed in docs/ (`Engineering With Mathcad.pdf`,
`calculus-10th-edition-anton.pdf`) remain deliberately untracked — never used, never committed, see
ip-cleanroom skill rule 7.

## Done
- Licence: MIT OR Apache-2.0. Clean-room IP policy (docs/IP-POLICY.md). Team: mathcad-specialist,
  gui-specialist, modeling-specialist, developer, tester, manager (CLAUDE.md, docs/PLAN.md).
- 001 ranges and tables, 002a vectors/matrices core, 002b eigen/rank/norm/least squares, 003 solve models
  phase A+B, 004 plots phase A (A1 engine + A2 document/GUI/PDF), 006 dialog-based plot configuration (D1
  fixed), 007 main window chrome (toolbars/side panel/theming; D1 toolbar-squash fixed), 008 dialog-based
  matrix/vector insertion, 009 component-wiring canvas core (D1 Connect-menu fallback fixed). All implemented,
  independently reviewed, and committed.
- Calculus defects C1-C4 fixed (`limit` keyword form, `ln` vs `log` display, friendly ambiguous-variable
  errors, non-integer series-order error); ∫ and d/dx real notation on the sheet; Math toolbar `e`, `i`, ⁿ√.
- Real-app tests on the Mac: 001, 002a, 003A passed after fixes (colon handling, matrix grid, safe Save As
  defaults).

## Open / unverified
- **Standing gap across specs 006/007/008/009: no computer_* tool was available this session for any review,
  so none of their real-window manual passes are done.** Checklist: Insert menus/"here" context-menu entries,
  dialog fill/Apply/OK/Cancel round trips, drag gestures (toolbar reorder, component wiring, plot resize),
  Appearance visual restyle, canvas-colour stability, slow-recalc status label, first-run hint, PDF export +
  vector sharpness, save/reopen. Needs Theo directly or a session with screen/input permissions granted.
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
1. Theo's real-window pass on specs 006/007/008/009 (see checklist above).
2. Spec 010 (ODE solving) — approved, queued, not started.
3. Specs from mathcad-specialist (assumptions, rewrite rules, context menu) for M3/M4; backlog 7a (document
   structure/ToC/index) and 8a (dataset import + reference data); M5 (statistics/optimization, items 29-30);
   M6 (data-source/nested-sheet/script components, items 32-34) once 009's core is verified real-window.

## Tester practicalities (Mac)
LiveSheet runs from ~/livesheet-venv (pip install -e). Terminal is click-only for agents; Theo starts the app. Window must not be in a
full-screen Space unless system key combos are granted. Dialog tests: Cancel only, never save over examples/.
