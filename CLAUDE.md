# LiveSheet

Open-source live math worksheet: free-form canvas, units, SymPy symbolic engine, PySide6 GUI, own `.lsheet` JSON format. Python 3.10+. Early MVP.

Vision: combine the engineering-calculation workflow of Mathcad-style tools, the symbolic depth of Mathematica-style tools and the usability of Maple-style tools, as an original clean-room implementation. Read docs/PLAN.md and docs/IP-POLICY.md before any feature work.

## Commands
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
- Run: `livesheet examples/demo.lsheet`
- Test: `QT_QPA_PLATFORM=offscreen pytest -q`

## Architecture
- livesheet/engine/: GUI-independent (syntax, evaluator, units, formatting). Never import PySide6 here.
- livesheet/gui/: PySide6 front end. livesheet/document.py: .lsheet format (keep backward compatible).
- Evaluation order: top to bottom, then left to right.

## Manager role (main session)
The main session is the manager and does not write feature code itself. Workflow per feature:
1. mathcad-specialist / mathematica-specialist / maple-specialist write a spec in docs/board/specs/.
2. Manager IP-reviews the spec against docs/IP-POLICY.md.
3. developer implements one approved spec; tester writes independent tests from the spec and reports in docs/board/reviews/.
4. Developer fixes, manager merges and commits.
Agents share state only via docs/board/ (backlog, specs, reviews, log.md, decisions.md). Open questions go to docs/board/decisions.md and are asked to Theo.

## Hard rules
- Clean-room: no vendor code, help text, examples, assets, file formats, names or 1:1 keyword sets. Developer and tester never read vendor docs; only specialists do, from public sources.
- Permissive dependencies only (MIT/BSD/Apache/LGPL-dynamic); no GPL/AGPL.
- Licence: dual MIT OR Apache-2.0.
- Do not commit or push without Theo's approval.

## Conventions
- Communicate with Theo in Dutch; code, docs, commits and comments in English.
- Type hints, small functions, tests for every engine feature.
