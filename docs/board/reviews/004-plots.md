# Review 004: two-dimensional plot regions (tester, black-box)

Spec: docs/board/specs/004-plots.md.

## A1: engine (nice_axis, PlotData, build_plot)

Commit under test: ef12bec. No independent tester review was requested for A1 this session; the
developer's own `tests/test_plot.py` (41 tests, criteria 1-20 + `nice_axis` + edge cases) ran green
as part of the full-suite runs below. Not separately re-derived from the spec by the tester; flag
as an open item if an independent A1 review is wanted later.

## A2: document format, GUI plot region, PDF export

Commit under test: working tree on top of ef12bec (uncommitted: `livesheet/document.py`,
`livesheet/gui/main_window.py`, `livesheet/gui/worksheet.py`, new `livesheet/gui/plotregion.py`,
new `livesheet/gui/plotview.py`).

### Tests added
- `tests/test_document.py`: round-trip tests for criteria 21-23 (version 1/2, default size,
  reading order) were already present in the working tree (developer-written, not by the tester
  this session).
- `tests/test_plot_gui.py` (new, 15 tests, written from the spec only, independent of reading
  `plotregion.py`/`plotview.py`/`worksheet.py` beyond the small public names the spec itself calls
  for as the GUI's job: `STARTER_TEXT`, `HINT_TEXT`, `is_blank_spec`, and the documented engine API
  `PlotData`/`PlotTrace`/`nice_axis`):
  - Criterion 24: `paint_plot` on a 400x260 white `QImage` leaves >500 non-white pixels for the
    criterion-1 data; does not raise for a single point, all-constant data, a trace with a NaN
    gap, and manual limits that exclude all data (frame still drawn, checked by pixel count > 0).
  - Criterion 25: `Insert > Plot` (triggered through the real `QAction`, not by calling
    `insert_region` directly) adds exactly one region of kind `plot` with `STARTER_TEXT`, already
    in edit mode; editing the spec text to the criterion-1 sheet gives 6 points; changing `v` in
    the math region above and only calling `finish_editing()` (the ordinary
    `editingFinished -> recalculate()` path, no extra action) updates the plot's y data to the new
    values; resizing then saving and reloading gives an equal plot spec and size (440 x 300).
  - Criterion 26: Backspace on a selected plot region (sent through the scene's real
    `keyPressEvent`, same event path as the G4 regression test) does not crash and removes the
    region from `to_document()`.
  - Criterion 27: `export_pdf` of a sheet with one plot starts with `%PDF` and is a larger file
    than the same sheet without the plot.
  - Edge cases: `is_blank_spec` only matches a bare `plot` (or `plot` + bare `over`/`show` lines);
    an empty spec always maps to `HINT_TEXT` in the hint colour, even when the engine result is the
    "over" error, by monkeypatching `plotview.paint_message` and calling `PlotRegion.paint`
    directly; a non-blank spec that still errors keeps the error message and `COLOR_ERROR`, not the
    hint; a `TextRegion` containing the words `plot over show xlim ylim title` is never handed to
    the engine (only the one math region in the same sheet produces a result); a variable literally
    named `plot` keeps its ordinary meaning inside a `show` line (`plot := 3 m/s` then
    `plot\nover t\nshow plot*t`); a descending range (`r := 10 to 0 step -5`) plots `x == [10,5,0]`
    with `x_limits == (0,10)` and renders without raising.

### Results
Full suite (`QT_QPA_PLATFORM=offscreen ~/livesheet-venv/bin/python -m pytest -q`, venv
`~/livesheet-venv`): **714 passed, 2 xfailed** (both pre-existing, unrelated to plots), 0 failed.
`tests/test_plot_gui.py` alone: 15 passed.

All of criteria 24-27 and the GUI-relevant "Phase A edge cases" checked above hold as specified.
No defects found in the A2 code under black-box testing.

### Observations (not defects)
- My first draft of the criterion-25 test placed the new plot region at the crosshair's default
  position (40, 40), which happens to equal the position of the first math region in the test
  sheet; with equal `(y, x)` reading-order keys the plot ended up evaluated before the `t`
  definition it needs, producing an (expected, pre-existing, cross-feature) reading-order error.
  This was a bug in my test, not in the plot feature; fixed by placing the plot with
  `insert_plot_at` at a position below both math regions. Not a defect, but worth noting: any
  two regions placed at exactly the same `(y, x)` have an order that depends on internal item
  list order, not on anything the user controls; this is general region-ordering behaviour that
  predates spec 004 and is out of scope here.

### Coverage gaps
- No real-window / computer-use check this session: Qt only ran offscreen
  (`QT_QPA_PLATFORM=offscreen`), as noted in docs/STATUS.md "Tester practicalities". Theo should do
  a manual pass: open LiveSheet, `Insert > Plot` (menu and the canvas context menu "Plot here"),
  type a spec, watch it redraw when changing a number above it, drag the resize handle, save and
  reopen, and export + open a PDF to check axes/ticks/unit labels/vector sharpness when zoomed (the
  spec's own instruction for criterion 27's visual half and for phase A2 generally).
- The canvas context-menu entry "Plot here" itself (`Worksheet.contextMenuEvent`, which calls
  `QMenu.exec()`, a blocking modal) was not exercised through the real context-menu event; I tested
  the underlying `insert_plot_at` it calls instead. Menu-wiring for "Plot here" specifically needs
  the manual pass above.
- Mouse-drag resizing through the actual resize handle (`mousePressEvent`/`mouseMoveEvent` on
  `handle_rect()`) was not simulated; I called the public `set_size` method directly, which is the
  same code path the handle drag ends in, but the drag interaction itself (hit-testing the handle,
  minimum-size/grid-snap while dragging) is untested here.
- A plot region that straddles a PDF page break was not tested (spec explicitly leaves this to the
  existing exporter's rule, "no new rule in this spec"); only a single-page export was checked.
- Very large/small magnitudes (1e-9..1e9) in the GUI renderer, and a sheet with the maximum 20
  traces rendered, were not visually checked here (the underlying numbers are covered by the
  developer's `tests/test_plot.py`, but not through `paint_plot`).

### IP red flags
None observed. Keywords (`over`, `show`, `xunit`, `yunit`, `xlim`, `ylim`, `title`, `xlabel`,
`ylabel`, menu entries `Insert > Plot` / `Plot here`), the fixed 8-colour trace palette, default
sizes (400 x 260, min 200 x 140), and all GUI strings (`STARTER_TEXT`, `HINT_TEXT`) in
`livesheet/gui/plotregion.py` and `livesheet/gui/plotview.py` are original wording, consistent with
the already-passed IP check in the spec file. No vendor names, help text, or file-format strings
found in the A2 code I read.

## Recommendation
Phase A2 looks ready to merge as-is: full suite green, all of criteria 21-27 and the checked edge
cases pass, no defects found. The coverage gaps above (manual GUI pass, context-menu "Plot here",
mouse-drag resize, page-straddling PDF) are follow-up manual/automated checks, not blockers.
