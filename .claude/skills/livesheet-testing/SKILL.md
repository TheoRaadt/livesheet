---
name: livesheet-testing
description: Test strategy for LiveSheet (spec-driven black-box tests, numeric and unit checks, property tests, GUI headless tests, regression files). Use when writing or reviewing tests.
---
1. Derive tests from the spec's acceptance criteria first; then edge cases (empty region, division by zero, unit mismatch, circular definition, huge numbers, unicode input).
2. Numerics: compare with pytest.approx and an explicit tolerance; cross-check with an independent route (e.g. SymPy exact vs float, or a closed-form value). An actually open-source tool (e.g. Scilab, GPL/CeCILL, installed at /Applications/scilab-*.app on this Mac — run headlessly via `scilab-cli-bin -nb -e "...; quit();"` after `export SCI=.../Contents/share/scilab`) is a good second, independent oracle for hand-derived expected values; use it only as a calculator (never read its docs/examples for problem ideas, never copy its syntax into LiveSheet). Do NOT use a personally/non-commercially licensed program (e.g. a personal Mathematica licence) for this, even just to compute a check value — see ip-cleanroom rule 7. Never source test *problems* from a copyrighted textbook or vendor example file, even to verify well-known facts — write your own problems; the fact itself isn't protected, a curated problem set is.
3. Units: test dimension errors, derived units (N, Pa, J), conversions, offset units once supported.
4. Property tests (hypothesis, if added as dev dependency): round-trip .lsheet save/load, expression -> format -> parse stability.
5. GUI: headless via QT_QPA_PLATFORM=offscreen; test region creation, recalculation order, undo/redo when present.
6. Golden files: tests/golden/*.lsheet with expected results; any change needs reviewer note.
7. Reports go to docs/board/reviews/NNN-name.md: spec id, tests added, results, defects with minimal repro.
8. Run: `QT_QPA_PLATFORM=offscreen pytest -q`.

# Known gotcha: `mock.patch.object` cannot intercept a builtin Qt class's method on a live instance (2026-10-29)
`mock.patch.object(QMenu, "exec", fake_fn)` *looks* like it patched `QMenu.exec` when you inspect the class
afterwards, but calling `menu.exec(pos)` through an actual `QMenu` instance still runs the real, blocking,
native (Shiboken/C++-backed) implementation -- the patch never intercepts, and the test hangs forever with no
error (confirmed with a minimal, isolated repro, not just theory). This is specific to builtin PySide6/Qt
classes used directly; patching an `exec`/similar method on a *pure-Python subclass* of a Qt class (e.g. an
app's own `QDialog` subclass) works completely normally via regular Python MRO override. If you need to drive
a real, unpatched, blocking modal call (`QMenu.exec()`, or anything else that opens a native nested event
loop) from a headless test: schedule a `QTimer.singleShot(0, callback)` *before* making the real call; the
callback fires once the nested loop has started, locates the live popup via `QApplication.activePopupWidget()`,
and drives it with real `QTest` key events (`menu.setActiveAction(action)` + `QTest.keyClick(menu,
Qt.Key.Key_Enter)` to select, or `Qt.Key.Key_Escape` to dismiss) so the real `exec()` call returns the actual
value your test asserts on. This still exercises the real menu-construction/dispatch code end to end --
nothing about what the test proves is weakened, only how it synchronizes with the blocking call.

# Known gotcha: a spec naming several equivalent interaction paths needs each path checked, not just the criteria (2026-10-29)
When a spec describes multiple ways to reach the same feature (e.g. "right-click a port, **or** use a
toolbar/menu action with a component selected" -- spec 009's Connect dialog), it's easy for an independent
review to pass every numbered acceptance criterion while one of the named paths simply doesn't exist in the
implementation, because the criteria themselves are satisfiable via whichever path happens to work (here: the
pixel-exact port right-click, or driving the dialog directly in a test). This slipped through an entire first
review pass. Explicitly re-check each interaction path the spec names by its own wording, independently of
whether the numbered criteria already pass -- especially any path the spec calls out for an accessibility or
robustness reason (here: "needs no dragging... fully keyboard-navigable"), since that's exactly the path most
likely to have been skipped as "redundant" during implementation.
