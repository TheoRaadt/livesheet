# Review spec 029 (calculus templates + definite integral), 2026-11-10

Tests added: tests/test_spec029_review.py (40 cases, black-box from the spec).

## Result
- BLOCKED for GUI cases: in this tester session Qt cannot start (every `QApplication` aborts with
  `Could not find the Qt platform plugin "offscreen" in ""`, also for `minimal`/`cocoa`, also for
  existing tests such as tests/test_side_panel_categories.py, also with sandbox disabled and with
  QT_QPA_PLATFORM_PLUGIN_PATH set). QPluginLoader on libqoffscreen.dylib loads fine, so it is an
  environment issue of this agent process, not a spec 029 defect. Not diagnosed further.
- Non-GUI cases (12 run, all pass): token tables (order, tokens, tooltip text, unique labels, no
  unbalanced ( [ { in any MATH_TOKENS row), engine templates/results, Gaussian ~1.77245 (display
  has 6 significant figures), bad tuple lengths give no Traceback, flat form
  `integrate(x^2, x, 0, 3)` errors cleanly, pretty HTML with bounds/units/oo, completion hint
  `integrate(expr, (x, a, b))` and acceptance `integ` -> `integrate(`.
- GUI cases written but NOT run (unverified): insert + selection in empty region, after text,
  mid-expression for all six buttons; type-over replaces part; undo = template in one step
  (test may need adjusting if Qt merges the type-over with the insert step); other tabs unaffected;
  Calculus page has exactly 4 buttons; wrapping band.
- Real-app GUI check: no computer-use tools available; selection-after-insert on macOS NOT verified.

## Defects
None found. Spec note: spec criterion 13 wording `(x, 0)` is accepted by SymPy (developer already
documented); tests use 5-tuples.

## Gaps
Run `QT_QPA_PLATFORM=offscreen pytest -q tests/test_spec029_review.py` in a working Qt session
and the manual GUI check before accepting. IP: no red flags in the diff (generic glyphs, own
tooltip wording).
