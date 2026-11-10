# LiveSheet status (2026-11-10, end of session)

Pushed to origin/main (up to the STATUS commit of this session). Untracked on purpose: the two vendor PDFs in docs/ (ip-cleanroom rule 7); `.idea` files stay out of commits.
Last full suite: 3326 passed, 2 skipped, 10 xfailed (`QT_QPA_PLATFORM=offscreen pytest -q`, ~/livesheet-venv).

## Done and accepted (all committed)
- Backlog 62 (stats functions in user-function bodies), spec 023 drag-to-move, spec 025 larger toolbar,
  spec 026 Statistics + Optimization tab buttons, spec 027 Outline tab, spec 024 function autocomplete
  (Tab fix + shared QSettings test isolation), spec 028 data import core (D1 engine + .lsheet v5, D2 import dialog
  + Data tab), spec 029 closed calculus templates + definite-integral button (selection after insert, one undo step),
  backlog 63 (arity error in function bodies). All tester-reviewed, defects fixed, manual updated (docs/manual: moving-regions, autocomplete,
  optimization, data-import, statistics, main-window, errors).
- Real-window checks on Theo's Mac have NOT been done for any of these (testers had no computer use).

## Open, next session (in this order)
1. **Real-window check on Theo's Mac**: drag-move (click then drag a selected region, Esc, hand cursors, edge scroll),
   toolbar (wide/narrow, dark mode, docked left), Statistics/Optimization/Outline/Data tabs, autocomplete (type `me`,
   Down, Tab), Calculus tab (definite-integral button: `f` selected so typing replaces it), CSV import (Insert > Data from file..., Browse picker, Rename/Remove/Refresh prompts, save/reopen v5),
   wrapping tab strip, page breaks, PDF export, formula tabs.
2. **Crash report from Theo**: app closes when switching a tab via PyCharm's Run button (backlog 44); need the Run-window
   text and the tab. May be gone since spec 022.
3. Backlog: 66 "Reading..." state for CSV files over 2 MB,
   67 dataset variables in autocomplete, integration variable clashes with a sheet variable of the same name (`x := 5`
   breaks `integrate(x^2, x)`; engine item). Done this session: 62, 63, 64, 65.
4. Evaluation-order error hint ("x, y are not defined" could mention definitions must come earlier), in-app help text
   lacks Shift+arrow nudging, undo (none exists; drag-move and dataset edits shipped without it), `length` function missing.
5. Standing backlog: M6 data components (JSON/Excel import, component formulas seeing datasets, backlog 32), spec 016
   (3D plots, research only), beam FEM F2, document quality (headers/footers, sections), CAS depth, heading levels /
   table of contents (7a), tab-role accessibility.

## Known engine limitations (documented in the manual)
- Bare-unit check gaps (`m^2`, `P/A`, expressions with digits); unit aliases like `u := m/s` break.
- `0 m` loses its unit; `x := 2 m / 1 m` reads as m^2 (use parentheses); `e` is Euler's number; `g` is standard gravity.
- Seeded sample values come from numpy's default_rng and may change across numpy major versions.
- Printed unit values default to SI (`mean(d_x) =` prints 0.002 m; use `= mm`).

## Process notes
- Testers must never run `git stash/reset/checkout`. Tests use the shared isolated QSettings (tests/conftest.py).
- Closing a MainWindow with unsaved changes opens a blocking dialog offscreen: call set_modified(False) first.
- Dialogs must not keep self-capturing lambdas (leaked dialogs segfault at interpreter exit, see 028 D2-R3).
- Plain `pytest` in the project `.venv` can crash (macOS hidden flag); use ~/livesheet-venv or `chflags -R nohidden .venv`.
- Subagents without Bash (specialists, documenter) cannot run examples or append to log.md; the manager re-runs doc examples.
- Git in the mounted folder may leave .lock files; move them to .git/stale-*.

## How to run
`source ~/livesheet-venv/bin/activate && livesheet` (new empty sheet) or `livesheet file.lsheet`.
PyCharm: interpreter ~/livesheet-venv, run module `livesheet`, no QT_QPA_PLATFORM env var.
