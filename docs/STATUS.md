# LiveSheet status (2026-10-27)

Commits: aca0667 team+policy+licence · f2b6e66 specs · 3d74db5 spec 001 · 364f057 001 fixes · bbcad16 spec 002a ·
5a3f973 002a fixes · c0b25a2 GUI fixes · 280f2c3 003A · b7beb0f 003A fixes · 39f1c5b 003B + G4 fix. Not pushed to GitHub.

## Done
- Licence: MIT OR Apache-2.0. Clean-room IP policy (docs/IP-POLICY.md). Team: 3 specialists, developer, tester, manager (CLAUDE.md, docs/PLAN.md).
- 001 ranges and tables, 002a vectors/matrices core, 002b eigen/rank/norm/least squares, 003 solve models phase A+B. About 570 headless tests green (5 Qt tests skip in the VM).
- Real-app tests on the Mac: 001, 002a, 003A passed after fixes (colon handling, matrix grid, safe Save As defaults).

## Open / unverified
- G4: FIXED and verified by Theo on the Mac (2026-10-28).
- 003 phase B has no real-window check by the tester yet.
- Layout: tall tables/grids can overlap regions below; wide results run off-window (backlog 20, 24).
- Known limits: zero from SymPy loses its unit; `f(M) := det(M)` unsupported; local optima only; solves run on the GUI thread.
- Decisions pending: product name trademark check; notation review (`≡`, `→`, `to/step/table`, `[ ]`, vary/settle/least/most) before 1.0; lawyer review before public 1.0; whether to push to GitHub.

## Next steps
1. Tester GUI check of 003B.
2. Tester review of 002b, undo/redo, plots (needs spec), push-down layout.
3. Specs from mathematica-/maple-specialist (assumptions, rewrite rules, context menu) for M3/M4.

## Tester practicalities (Mac)
LiveSheet runs from ~/livesheet-venv (pip install -e). Terminal is click-only for agents; Theo starts the app. Window must not be in a
full-screen Space unless system key combos are granted. Dialog tests: Cancel only, never save over examples/.
