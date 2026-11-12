# LiveSheet status (2026-11-12, end of session 2)

Pushed to origin/main up to commit "Offer dataset names in autocomplete and add evaluation-order hint (spec 030)".
**UNCOMMITTED (waiting for Theo's approval): everything listed under "Built this session, not committed".**
Untracked on purpose: the two vendor PDFs in docs/ (ip-cleanroom rule 7); `.idea` files stay out of commits.
Last full suite (manager run): 4095 passed, 2 skipped, 13 xfailed (`QT_QPA_PLATFORM=offscreen pytest -q`, ~/livesheet-venv).

## Built this session, not committed (code + tests in working tree)
| Item | Spec | Status |
|---|---|---|
| 3-D surface plots, phase A (static `surface` region, Insert > 3-D plot) | 031 | implemented, tester-accepted, NOT documented |
| 3-D plots phase B (drag rotate, wheel zoom, frame-ring move, saved view fields `view_az/el/zoom`, Reset 3-D view, label backing, long-title shortening) | 031 | implemented, tester-accepted, NOT documented |
| LaTeX in text regions L1 (`$..$`, `$$..$$`, own renderer in livesheet/texmath + gui/texlayout.py) | 032 | implemented, tester-accepted (Greek-letter, linear-scan, spacing fixes done), NOT documented |
| LaTeX L2 (matrices, accents, font commands, View toggle, Insert formula Ctrl+Alt+4 / Ctrl+Alt+Shift+4, bundled STIX Two Math font + OFL.txt + checksums in gui/fonts/README.md) | 032 | implemented, NOT independently reviewed, NOT documented |
| Mechanical-engineering library phase 1 (28 functions, livesheet/engine/mecheng.py, SI results) | 033 | implemented, tester-accepted, NOT documented |
| Electrical library phase 1A (17 functions, livesheet/engine/electrical.py; units VA, var, mH, uH, nH, pF) | 034 | implemented, NOT independently reviewed, NOT documented |
| Imperial units removed from engine/units.py (inch, ft, yd, mi, lb, lbf, psi); DXF INSUNITS 1,2,3,10 no longer mapped | backlog 77 | done, NOT documented (Theo: do not document yet) |

Manual pages that still mention removed units (fix when documenting): docs/manual/cad-profiles.md (lines ~21, 63-70), docs/manual/errors.md:156 ("Unknown length unit" text), docs/manual/formula-tabs.md:87.
Kept non-SI-but-metric units: bar, mbar, atm, L, mL, min, hr, day, week, yr, ha, tonne, deg, rad, Wh/kWh/MWh, rpm, g (std gravity), cal, kcal. Ask Theo if any should go.

## Next session, in this order
1. **Theo's call: commit and push** the work above (suggest separate commits per spec: 031, 032, 033, 034-1A, units).
2. Tester for 032 L2 and 034 1A (independent review), then documenter for 031, 032, 033, 034-1A and the units change (manual pages + errors.md).
3. Spec 034 phase 1B (phasors, impedance, time constants, resonance, RC filters) and GUI-1 (36 buttons in the Electrical tab); phases 2-6 of 034 and 2-7 of 033 need own specs (backlog 74, 75).
4. Real-window checks on Theo's Mac (nothing this or the last session was hand-driven): drag-move, toolbar, Statistics/Optimization/Outline/Data tabs, autocomplete (incl. dataset names), CSV import, definite integral button; 3-D plot rotate/zoom/ring-move and Export PDF; LaTeX typeset/edit/leave, View toggle, Insert formula shortcuts (AltGr clash on Windows, workspace switching on some Linux desktops, AZERTY digits), bundled font; mechanical/electrical function autocomplete popup.
5. Backlog: 66, 70 (`log(0)` in plot sampling raises an internal error), 71 done, 72 (accessible text for formulas), 73 (L2 done, remove), 76 (3-D defects: y/z title overprint, wire preview in print, B9 wording 40 cells vs 41 points, view stored for error-only region), PyCharm tab-switch crash report (need Run-window text; backlog 44), integration-variable clash, in-app help lacks Shift+arrow, undo (none), `length` function, spec 033 criterion 26 uses L/I/E symbols (litre/imaginary/Euler) - reword.
6. Standing: M6 data components (JSON/Excel import), beam FEM F2, document quality, CAS depth, heading levels/TOC, tab-role accessibility, `j` imaginary unit and rad/s display name (spec 034 follow-up), siemens unit.

## Done and committed earlier
Specs 023-030 (drag-to-move, toolbar, Statistics/Optimization/Outline/Data tabs, autocomplete incl. dataset names, CSV import, closed calculus templates, evaluation-order hint), backlog 62-65, 67. See docs/board/log.md.

## Known engine limitations (documented in the manual)
- Bare-unit check gaps (`m^2`, `P/A`, expressions with digits); unit aliases like `u := m/s` break.
- `0 m` loses its unit; `x := 2 m / 1 m` reads as m^2 (use parentheses); `e` is Euler's number; `g` is standard gravity; `L` is litre and `I` the imaginary unit (do not use as variable names in the new libraries).
- Seeded sample values come from numpy's default_rng and may change across numpy major versions.
- Printed unit values default to SI (`mean(d_x) =` prints 0.002 m; use `= mm`). No warning mechanism yet (backlog 9), so validity ranges in mecheng are only in docstrings.

## Process notes
- Testers must never run `git stash/reset/checkout`. Tests use the shared isolated QSettings (tests/conftest.py).
- Closing a MainWindow with unsaved changes opens a blocking dialog offscreen: call set_modified(False) first.
- Dialogs must not keep self-capturing lambdas (see 028 D2-R3).
- Plain `pytest` in the project `.venv` can crash (macOS hidden flag); use ~/livesheet-venv or `chflags -R nohidden .venv`. `timeout` does not exist on this Mac.
- Subagents without Bash (specialists, documenter) cannot run examples or append to log.md; the manager appends their log lines and re-runs doc examples.
- Vendor manuals of the commercial engineering packages must never be opened (decisions.md 2026-11-12).
- Git in the mounted folder may leave .lock files; move them to .git/stale-*.

## How to run
`source ~/livesheet-venv/bin/activate && livesheet` (new empty sheet) or `livesheet file.lsheet`.
PyCharm: interpreter ~/livesheet-venv, run module `livesheet`, no QT_QPA_PLATFORM env var.
