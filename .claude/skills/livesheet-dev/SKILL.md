---
name: livesheet-dev
description: Architecture, conventions and commands for developing LiveSheet (Python 3.10+, SymPy engine, PySide6 GUI, .lsheet JSON). Use when implementing or changing code in the livesheet package.
---
# Architecture
- livesheet/engine/: GUI-independent. syntax.py (statement parsing), evaluator.py (evaluation order, namespaces, symbolic keywords), units.py (units, dimension checks), formatting.py (output).
- livesheet/gui/: PySide6 (main_window.py, worksheet.py canvas, regions.py, pretty.py).
- livesheet/document.py: .lsheet JSON format. Keep backward compatible; add a version field before breaking it.
- tests/: pytest; GUI tests headless.
# Rules
- Engine must never import PySide6. New math features land in engine first with unit tests, then GUI.
- Type hints, small functions, no new dependency without a licence check (permissive only).
- Run: `QT_QPA_PLATFORM=offscreen pytest` and fix before reporting.
- One spec per change; do not refactor unrelated code. Do not commit or push.
- Evaluation is top-to-bottom, left-to-right; keep that contract.
- Report deviations from the spec explicitly.
