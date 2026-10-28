2026-10-27 mathcad-specialist -> manager: spec 001 range variables ready (docs/board/specs/001-range-variables.md)
2026-10-27 mathcad-specialist -> manager: spec 002 vectors/matrices ready, phases 002a/002b (docs/board/specs/002-vectors-matrices.md)
2026-10-27 mathcad-specialist -> manager: spec 003 solve blocks ready, phases A/B (docs/board/specs/003-solve-blocks.md)
2026-10-27 manager: IP review pending Theo's answers in decisions.md; developer not started
2026-10-27 developer -> manager: spec 001 implemented (engine+tests, GUI text table untested headless: libEGL missing in VM); see report. Not committed.
2026-10-27 tester -> manager: review 001 done headless (155 pass, 8 xfail = defects D1-D5, spec numbers verified); real-app GUI run BLOCKED: Terminal only click-tier (cannot type), see docs/board/reviews/001-range-variables.md
2026-10-27 developer -> manager: fixed review 001 defects D1,D2,D3,D5 (engine), D4 test now normal; test_gui skips when PySide6 unloadable. Not committed.
2026-10-27 tester -> manager: rerun on 364f057 green (163 pass); GUI run still blocked: Terminal is click-tier even with full control, needs Theo to start app or a non-terminal launcher (reviews/001)
2026-10-27 developer -> manager: spec 002a implemented (engine/matrices.py, tests/test_matrices.py; GUI ':' inside brackets untested, no libEGL). Not committed.
2026-10-27 tester -> manager: review 002a done headless (392 pass, 12 xfail = defects M1-M6, see reviews/002a); GUI part skipped: no LiveSheet window open
2026-10-27 developer -> manager: fixed review 002a M1 (zero units, partial), M4, M5, M6, min(), NBSP; M2 test flipped, M3 xfail kept. Not committed.
2026-10-27 tester -> manager: GUI test attempted with Theo's open LiveSheet: window is in a full-screen Space, background input had no effect; needs Theo to leave full-screen (see reviews/001, 002a)
2026-10-27 tester -> manager: GUI retry blocked again (window off-Space, clicks refused); my earlier x:5 input left a stray region in Theo's UNSAVED demo, Theo must delete it (reviews/001 attempt 4)
2026-10-27 tester -> manager: GUI run done (001, 002a): table/matrix/errors/zoom/dialogs OK; defects G1 '::' broken, G2 eye(10) overlaps, G0 accidental save over demo.lsheet+demo.pdf during dialog test (REPAIRED, demo restored to HEAD, pdf removed); see reviews
2026-10-27 developer -> manager: GUI fixes G0 (save dialog defaults), G1 (:: -> ≡), G2 (matrix grid via RegionResult.grid); tests/test_gui_helpers.py; Qt parts unrun in VM. Not committed.
2026-10-27 tester -> manager: GUI recheck on c0b25a2: G0/G1/G2 PASS (grids render well, dialogs suggest Documents/, cancel writes nothing, git clean); open: tall grids overlap regions placed below, wide symbolic grids run off-window (reviews/001)
2026-10-27 developer -> manager: spec 003 phase A implemented (engine/solver.py, syntax kinds model_*, tests/test_solve.py). Phase B kinds parse but report 'not available yet'. Not committed.
2026-10-27 tester -> manager: spec 003 phase A review on 280f2c3: criteria 1-11 PASS headless; tests/test_solve_blackbox.py 70 pass + 9 strict xfail; defects S1 (far root from small guess), S2 (zero-derivative guess), S3 (numpy warning leak), S4 (steps used > limit); GUI not run; see reviews/003-solve-blocks.md. Not committed.
2026-10-27 developer -> manager: fixed review 003 S1-S4 (retry starts, strict check on retries, warnings suppressed, 'function evaluations' wording). Not committed.
2026-10-27 tester -> manager: spec 003 GUI check on b7beb0f: fall example, errors+colours, dependants, no freeze PASS; long lines run off-window (G3); LiveSheet process vanished after Backspace on selected 'settle' region (G4, unconfirmed, needs repro/traceback); delete/Save-As items not reached; nothing saved, git clean. See reviews/003. Not committed.
2026-10-27 developer -> manager: spec 003 phase B implemented (inequalities, chained, least/most, ✓/✗ marks; tests/test_solve_b.py). Not committed.
2026-10-27 developer -> manager: G4 fix (Worksheet._discard: single-owner deferred destruction); Qt regression tests in test_gui_helpers.py; backlog 24 added. Unverified on Mac. Not committed.
2026-10-27 manager: documentation updated (README, STATUS, PLAN, backlog); session ended pending Mac verification of G4 and 003B GUI check
2026-10-28 developer -> manager: fixed 'table ),a(' leaking IndexError; _parse_table now checks bracket balance in engine/syntax.py and reports 'Unbalanced brackets'; suite run, see report.
2026-10-28 manager: G4 Qt regression tests pass on Theo's Mac (18/18, not skipped); table bracket fix reviewed (not committed, awaiting Theo); spec 002b IP-reviewed: PASS, assigned to developer; plots spec requested from mathcad-specialist
2026-10-28 manager: G4 verified by Theo in the real app (no crash after Backspace on selected settle region): CLOSED
2026-10-28 developer -> manager: spec 002b implemented (eigenvalues, eigenvectors, rank, norm, solve_least_squares in engine/matrices.py; exact mode flag set by evaluator for →; tests/test_matrices_b.py, 25 tests). Not committed.
2026-10-28 mathcad-specialist -> manager: spec 004 plots ready, phases A1/A2 (minimal XY plot, doc format, PDF) and B1/B2 (log/legend/markers, parametric/polar); renderer choice QPainter vs matplotlib is open question 1 (docs/board/specs/004-plots.md)
