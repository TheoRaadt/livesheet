# LiveSheet status (2026-11-01, end of day)

Commits this session: `4b14919` (spec 021 page breaks + evaluation order, plus all earlier accepted
work), `c230a01` (formula tabs 018/019/020, bare-unit check, manual). Not pushed. Last full suite:
2032 passed, 8 xfailed, 0 failed (`QT_QPA_PLATFORM=offscreen pytest -q`, from ~/livesheet-venv).
Only the two vendor PDFs in docs/ are untracked on purpose (ip-cleanroom rule 7).

## Done and accepted today
- **Spec 021**: evaluation order is now page by page, left to right, then top to bottom (stable
  creation-order tie-break; closes backlog 28); Insert > Page Break (Ctrl+Return) with Word-style
  reflow, fold guides, per-page A4 PDF export, .lsheet v4 `page_breaks`, wiring tie-break flipped.
  Manual: docs/manual/pages.md. Reviews: docs/board/reviews/021-*.
- **Specs 018/019/020**: Mechanical (15), Electrical (11), Chemical (21) side-panel tabs; order
  Elements, Algebra, Calculus, Statistics, Optimization, Mechanical, Electrical, Chemical, Outline,
  Data. Manual: docs/manual/formula-tabs.md. Review 022: PASS.
- **_check_defined hardening**: a bare unit name that is not defined (`sigma := F/A`) now errors.
  Theo accepted the side effects (unit aliases like `u := m/s`, `m = mm`, `g =` break). Known silent
  gaps: `m^2`, `P/A`, expressions with digits. Documented in the manual.
- **Spec 017 (statistics)**: IP review PASS, all 8 open questions answered (decisions.md). Not built.
- Agent config: mathcad-specialist now runs on the haiku model (.claude/agents/mathcad-specialist.md).

## Open, next session (in this order)
1. **Real-window check on Theo's Mac** (nobody has had computer use): page breaks, PDF export, the
   three new tabs, demo.lsheet layout (three regions moved to x=300), plus specs 010/011/013/014/015.
2. **Crash report from Theo**: app closes when switching a tab when run via PyCharm's Run button;
   fine from the terminal. Ask for the Run-window text and the tab; check PyCharm env vars
   (QT_QPA_PLATFORM must be empty) and interpreter (~/livesheet-venv). Backlog 44.
3. **Spec 022 (wrapping full-window tab strip)**: spec FINAL (window-wide strip + button band, side-panel dock retired, 8 open questions incl. Outline/Data placement, row stretch, band height) written by gui-specialist, manager IP review
   and answering its open questions come next; Theo wants the tab strip across the whole app window
   (under the menu bar), all 10 tabs visible, wrapping to more rows when narrow. Not built.
4. **Spec 017 statistics**: verify its worked examples against the engine, then dispatch S1 when
   Theo says go.
5. Open spec 021 defaults still unconfirmed by Theo: no undo for page-break reflow (undo, backlog
   4/43, may be worth pulling forward), 0.4% PDF shrink with breaks, deleting a break does not move
   content back.
6. Standing backlog: M6 data components, spec 016 (3D plots, research only), beam FEM F2,
   document quality items (headers/footers, sections), CAS depth.

## How to run
`source ~/livesheet-venv/bin/activate && livesheet` (new empty sheet) or `livesheet file.lsheet`.
PyCharm: interpreter ~/livesheet-venv, run module `livesheet`, no QT_QPA_PLATFORM env var.
