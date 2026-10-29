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
