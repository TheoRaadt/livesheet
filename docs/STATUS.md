# LiveSheet status (2026-10-28, end of session)

Commits: aca0667 team+policy+licence · f2b6e66 specs · 3d74db5 spec 001 · 364f057 001 fixes · bbcad16 spec 002a ·
5a3f973 002a fixes · c0b25a2 GUI fixes · 280f2c3 003A · b7beb0f 003A fixes · 39f1c5b 003B + G4 fix · 2982a43 spec
002b · ef12bec spec 004 A1 · b862444 spec 004 A2. Not pushed to GitHub.

**Uncommitted at end of session (ready, Theo's commit approval pending):** spec 006 (dialog-based plot
configuration, replacing the superseded spec 005; D1 fixed) · calculus defects C1-C4 fixed (`limit` keyword
form, `ln` vs `log` display, friendly ambiguous-variable errors, non-integer series-order error) · ∫ and d/dx
real notation on the sheet (not just the toolbar) · Math toolbar: `e`, `i`, ⁿ√ buttons · broadened calculus/
engineering test coverage (tests/test_calculus.py) · backlog items 7a (heading levels + ToC/index), 8a (open
dataset import + reference data), 28 (reading-order tie-break) · skill files updated with this session's
lessons (see .claude/skills/). Full suite: **880 passed, 2 xfailed** (both pre-existing/unrelated: E1 002b
eigenvalues-as-numeric, M3 `f(M):=det(M)`). Two PDFs Theo placed in docs/ (`Engineering With Mathcad.pdf`,
`calculus-10th-edition-anton.pdf`) are deliberately left untracked — never used, never committed, see
ip-cleanroom skill rule 7.

## Done
- Licence: MIT OR Apache-2.0. Clean-room IP policy (docs/IP-POLICY.md). Team: 3 specialists, developer, tester, manager (CLAUDE.md, docs/PLAN.md).
- 001 ranges and tables, 002a vectors/matrices core, 002b eigen/rank/norm/least squares, 004 plots phase A (A1 engine + A2 document/GUI/PDF), 003 solve models phase A+B. 006 dialog-based plot configuration (uncommitted, see above).
- Real-app tests on the Mac: 001, 002a, 003A passed after fixes (colon handling, matrix grid, safe Save As defaults).

## Open / unverified
- G4: FIXED and verified by Theo on the Mac (2026-10-28).
- 003 phase B has no real-window check by the tester yet.
- 004 A2 (plot region GUI) black-box reviewed headless only, 0 defects; 006 (plot dialog) black-box reviewed headless only, 1 defect found and fixed (D1). Both need Theo's real-window pass: Insert > Plot menu and "Plot here" opening the dialog, filling/Applying/OK, double-click on existing plots (dialog vs. raw-text fallback), add/remove function rows, unit/limit fields, Cancel on new vs. existing, error messages, Edit-as-text/Use-dialog round trip, drag-resize handle, save/reopen, export + open a PDF and check vector sharpness when zoomed.
- Layout: tall tables/grids can overlap regions below; wide results run off-window (backlog 20, 24); plots may overlap regions below until backlog 20 (accepted for phase A); reading order is unstable when two regions share the exact same position (backlog 28).
- Known limits: zero from SymPy loses its unit; `f(M) := det(M)` unsupported; local optima only; solves run on the GUI thread; `diff(EXPR)` 1-arg auto-detect form isn't given the new ∫/d-dx display notation (only the 2-/3-arg explicit-variable forms are).
- Decisions pending: product name trademark check; notation review (`≡`, `→`, `to/step/table`, `[ ]`, vary/settle/least/most, plot keywords `over/show/xlim/ylim/xunit/yunit`, plot-dialog field labels) before 1.0; a short human/legal sanity check on spec 006's dialog-based interaction (lower risk than spec 005's rejected inline placeholders, but still flagged, see decisions.md); lawyer review before public 1.0; whether to push to GitHub.

## Next steps
1. Theo's commit approval for the uncommitted work above, then Theo's real-window pass on 003B, 004 A2, and 006.
2. Phase B of 004 (log axes, legend, markers, parametric/polar) once 004 A2/006 are merged; undo/redo; push-down layout; backlog 27 (dialog-based vector/matrix insertion, same pattern as 006).
3. Specs from mathcad-specialist (assumptions, rewrite rules, context menu) for M3/M4; mathcad-specialist specs for backlog 7a (document structure/ToC/index) and 8a (dataset import + reference data) when M2 work starts.

## Tester practicalities (Mac)
LiveSheet runs from ~/livesheet-venv (pip install -e). Terminal is click-only for agents; Theo starts the app. Window must not be in a
full-screen Space unless system key combos are granted. Dialog tests: Cancel only, never save over examples/.
