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

# Known gotcha: macOS native menu bar steals keyboard focus (2026-10-28)
A region created via a `QAction` triggered from the (native, on macOS) menu bar or a `QMenu.exec()`
can end up with `item.hasFocus()` true at the Qt-scene level while the `QGraphicsView` widget itself
never regains real OS keyboard focus — so real typed keystrokes never arrive, even though headless/
offscreen tests (which don't exercise native menu interaction the same way) don't catch it. This bit
`Worksheet.insert_region()`. Fix pattern: before calling `region.start_editing()` (or any editor-focus
call) after a menu-triggered action, explicitly call `self.views()[0].setFocus(Qt.FocusReason.OtherFocusReason)`
on the view first. Apply the same pattern to any new menu-triggered action that immediately opens an
editor or dialog expecting real keyboard input.

# Known gotcha: shared `.venv` hard-aborts on Qt offscreen init (recurring across sessions, 2026-10-29)
Multiple independent sessions (at least 5 now) have hit a transient failure where every PySide6 test,
including unrelated pre-existing ones, crashes with `Fatal Python error: Aborted` deep inside
`QApplication`/`QGuiApplicationPrivate::createPlatformIntegration` the moment `QT_QPA_PLATFORM=offscreen`
tries to initialize -- not a clean "platform plugin not found" message, a hard native abort. A *targeted*
fix (reinstalling just PySide6) does **not** reliably fix it. Deleting and recreating `.venv` from scratch
(`rm -rf .venv && python3 -m venv .venv && pip install -e ".[dev]"`, same as the project's own setup command)
has fixed it every single time it's been tried. Root cause is still unconfirmed but is most consistent with
multiple agents/sessions sharing one `.venv`'s Qt plugin directory concurrently (a reinstall mid-run has been
caught in the act once, mtimes advancing live). If `pytest` aborts like this, don't debug Qt config -- just
recreate `.venv` and move on; flag the recurrence in docs/board/log.md so the pattern stays visible.

# Known gotcha: `.lsheet` backward compatibility breaks easily when adding dataclass fields (2026-10-29)
Adding a new optional field to `RegionData` or a new top-level list to `SheetDocument` (e.g. spec 009's
`component_name`/`component_kind`/`config`/`wires`) must be gated on actually-in-use, not just given a
default value -- a default-valued field still needs its own `to_dict()`/`to_json()` logic to *omit the key
entirely* when unused, matching the existing plot-only-when-used `w`/`h`/version-2 pattern, or old sheets
stop round-tripping byte-identical. Two places this bites, both found the hard way: (1) the writer itself
must conditionally omit the key, not just write an empty/default value (`"wires": []` is just as breaking as
`"wires": [...]` to a byte-identical-resave test); (2) any *test* that builds its own comparison baseline via
`dataclasses.asdict(region)` will pick up the new field unconditionally regardless of the real writer's own
conditional logic, since `asdict()` doesn't know about that convention -- the test's baseline needs the same
"pop this key before comparing" treatment already applied to `w`/`h` when plot support was added. Forgetting
either half silently breaks `tests/test_document.py`'s backward-compat invariants.

# Known gotcha: a `QMainWindow` toolbar can get stuck floating after a drag (2026-10-29)
A `QToolBar` dragged by the user can end up `isFloating() == True` instead of cleanly redocked; that bit then
survives `saveState()`/`restoreState()` round-trips (including in the user's real on-disk `QSettings`), and a
toolbar restored as floating renders squashed/clipped/overlapping the docked area on next launch -- looks like
a one-off paint glitch but isn't (survives window moves and visibility toggles). Fix pattern used for spec 007's
D1: `setFloatable(False)` on toolbars that should only ever be repositioned between docked areas, never torn
off (still `movable`, so drag-to-reorder between areas is unaffected) plus a repair step right after
`restoreState()` in `__init__` that resets the whole toolbar layout to its default stacked arrangement if a
toolbar is still found floating (covers old/corrupted saved-state bytes that `setFloatable` can't retroactively
fix). Apply the same two-part pattern to any new toolbar.
