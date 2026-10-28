# 004 Two-dimensional plot regions with unit-aware axes

Source inspiration (concept only, nothing copied):
- https://help.ptc.com/mathcad/en/PTC_Mathcad_Help/about_traces_and_axis_expressions.html (public help page; seen via web-search result summary, 2026-10-28). Concept taken: a plot shows several traces, each an expression of the same independent variable; axis units follow from the values. No text, UI layout, placeholder-based editing, keywords or examples were copied.
- https://help.ptc.com/mathcad/en/PTC_Mathcad_Help/to_define_axes_limits_in_chart_component.html (public help page, same date, same use): only the idea that axis limits can be automatic or set by the user.
- Charting basics (nice tick steps, log axes, polar-to-Cartesian conversion) are general public knowledge. All syntax, numbers and wording below are our own.

Size: split into two phases, four slices of about 2 days each.
- **Phase A (minimal useful XY plot)**: A1 engine (about 2 days), A2 document format + GUI region + rendering + PDF (about 2 days). A2 starts after A1 is merged.
- **Phase B (extras)**: B1 log axes, legend labels, marker style, grid switch (about 2 days); B2 parametric traces and polar mode (about 2 days). Phase B starts after A2 is merged.

Interop: uses range variables from spec 001 (`RangeVar`) and vectors from spec 002a (SymPy matrices in `env`). It does not change either. A plot only reads definitions that are above it in reading order, plus global (`≡`) definitions anywhere, exactly like `table`.

---

# Phase A: minimal useful XY plot

## User story
As an engineer I place a plot on the canvas, say which variable it runs over and which expressions to draw. Axes show the right unit (and I can pick another unit, for example millimetres instead of metres). When I change a number above the plot, the plot redraws at once. Mixing incompatible units gives a clear error instead of a wrong picture. The plot is saved in the sheet file and appears in the exported PDF.

## Behaviour (own words)

### The plot region
A plot is a new kind of canvas region, next to math and text regions. It has a position (top-left, like all regions) and a size (width and height). Its content is a short block of text lines (the "plot spec", see syntax) that the user edits as text, plus the drawn chart. The chart is not editable by mouse in phase A (no dragging of axes, no trace read-out). The region takes part in reading order like any other region (position `y`, then `x`). It never defines a name and never changes values used elsewhere.

### What is plotted
- **Range mode**: `over` names a range variable (spec 001). Every `show` expression is evaluated once per value of that range variable, as a table column would be. The x values are the range values; the y values are the expression results.
- **Sampling mode**: `over x from A to B points N` makes a private range for this plot only: N evenly spaced values from A to B, both ends included (value k is A + k*(B-A)/(N-1), computed from the ends, no accumulated drift). The name `x` exists only inside the plot, it does not become a range variable on the sheet and it shadows a same-named sheet definition inside this plot. `points` is optional, default 101, allowed 2 to 10000. A and B must have the same dimension; B may be below A (the x axis then simply runs over the data in the order given).
- **Vector mode**: `over` names a vector (spec 002a; row or column, orientation does not matter). Every `show` expression must then evaluate to a vector with the same number of elements; point k is (x[k], y[k]). Vector arithmetic from spec 002a (`2*Y`, `Y + Z`, `Y*m/m`) works inside `show`; scalar-only functions applied to vectors keep the error of spec 002a.
- A `show` expression that gives the wrong shape for the mode (a vector in range mode or sampling mode, a scalar in vector mode) is an error.
- Up to 20 traces. Each point whose y (or x) is undefined, infinite, or complex with non-zero imaginary part is not drawn; it leaves a gap in the line. Such points are counted in `PlotData.skipped`. If no finite point remains in any trace the plot is an error.

### Units
- Every axis has one display unit. The x values carry the unit of the `over` values; the y values carry the unit of the `show` expressions. All traces share one y axis, so all traces must have the same dimension (error otherwise); there is no second y axis in this spec.
- Default display unit when no `xunit`/`yunit` line is given: the unit text the existing numeric formatter would print for the first finite point of the first trace (same SI simplification as `=`). Dimensionless values have an empty unit.
- `xunit U` / `yunit U` selects another display unit of the same dimension; all values and limits are converted. A unit of another dimension is the error `Units do not match`. A unit given for a dimensionless axis is the error `xunit given but x has no unit` (same for y).
- Axis label default: the text of the `over` name (x) and, for a single trace, the expression text of that trace (y); with several traces the y label is empty. In both cases the display unit is appended in square brackets when it is not empty, for example `t [s]`. `xlabel`/`ylabel` lines replace the text part, the unit part is still appended. `title` is optional text above the chart.

### Axis limits
- Default is automatic. Automatic limits are computed from the finite data of all traces (after unit conversion) by the "nice axis" rule below. Ticks are computed by the same rule in the engine so that the renderer only draws them.
- `xlim LO to HI` / `ylim LO to HI` set manual limits. Either side may be the word `auto` (`xlim auto to 8 s`): that side is computed by the nice axis rule and the other is used as given. A given limit is a quantity with unit (converted to the axis unit; wrong dimension is `Units do not match`) or a plain number for a dimensionless axis. LO must be strictly below HI (error `lower limit must be below upper limit`). Data outside manual limits stays in `PlotData` and is clipped by the renderer.

### Nice axis rule (normative; the numbers in the acceptance criteria follow from it)
Given a data minimum `lo` and maximum `hi` (after unit conversion):
1. If `lo == hi`: let d = 0.1*|lo|, or d = 1 when lo == 0; use lo - d and hi + d instead.
2. Candidate steps are 1, 2 and 5 times a power of ten. Choose the smallest candidate step s with (hi - lo)/s <= 8.
3. Automatic limits: floor(lo/s)*s and ceil(hi/s)*s (treat a quotient within 1e-9 of an integer as that integer so exact multiples do not widen).
4. Ticks: all multiples of s inside the final limits (inclusive, same 1e-9 rule), ascending, rounded to 12 significant digits so that 0.1*3 prints as 0.3.
5. With manual limits the same step rule is applied to (LO, HI); limits stay as given, ticks are the multiples of s inside them. With one side `auto`, that side is computed from the data by steps 1-3 using the step of the final range, and the step is then recomputed for the final range.

### Live update
`Engine.evaluate` is already re-run for the whole sheet after every change. The plot region is one more entry of that run; its `RegionResult` carries the fresh `PlotData`, and the GUI repaints the chart when a new result arrives. No separate refresh mechanism, no caching beyond what the engine does today. Redefinition below the plot does not affect it (reading order); a global definition anywhere does.

### Saving (.lsheet, own schema)
- New region kind `"plot"`. The plot spec lines are stored in the existing `text` field joined with `\n`. Two new optional numeric fields `w` and `h` (plot size in scene units) are written only for plot regions. Math and text regions are written exactly as today.
- `version` is written as 2 when the sheet contains at least one plot region, otherwise 1, so a sheet without plots is byte-identical to today's output and stays readable by old versions. The reader accepts versions 1 and 2 and rejects higher ones with the existing "newer version" message. A plot region without `w`/`h` loads with the default size 400 x 260.
- Plot results are never stored; they are recomputed on load.

### PDF export
The existing PDF export renders the scene; the plot region draws itself through one function `paint_plot(painter, rect, plot_data)` that works on any `QPainter` (screen, `QPdfWriter`, `QImage`). In the PDF the chart is vector graphics (lines and text, not a bitmap). Pagination logic of the existing export is reused: a plot is not split over pages by design; if it crosses a page break the exporter may leave it as the existing exporter treats other regions (no new rule in this spec).

### Creating and editing in the GUI (phase A2)
- Menu `Insert > Plot` and the canvas context menu entry `Plot here` create a plot region at the clicked position (menu action: at the last known canvas position or the viewport centre) with default size and the starter text `plot` plus two empty option lines `over ` and `show `. The new region is selected and enters text editing.
- Double-click enters editing of the spec text (monospaced, same commit rules as math regions: click elsewhere or Esc ends it; Enter inserts a newline). While editing, the region shows the text; when editing ends the chart is shown.
- A resize handle at the bottom-right corner changes `w`/`h` (minimum 200 x 140, snapped to the same grid as region moves). Moving, selecting, deleting and undo-style behaviour follow the existing region rules (deletion must use the single-owner removal added for G4).
- Error results show the message centred in the plot frame in the error colour; an empty spec shows a short hint text instead of an error.
- Hint: phase A does not push following regions down; a plot may overlap regions placed below it until backlog item 20 exists.

### Rendering approach (recommendation; see open question 1)
Draw with `QPainter` directly in `livesheet/gui/plotview.py`: frame, ticks and tick labels from `PlotData` ticks, grid lines (light), polyline per trace with gaps at NaN, clipping to the plot area, trace colour from a fixed 8-colour palette indexed by `PlotTrace.style_index`. No new dependency, identical drawing on screen/PDF/PNG, vector PDF through the existing `QPdfWriter` path, and the engine stays Qt-free. Estimated cost: about 1 day for the painter code.

## Syntax proposal (own keywords)
A plot spec is plain text, one option per line, all keywords lowercase. The first non-blank line is exactly `plot`. Blank lines are ignored.

```
plot
over t                                   range variable or vector
over x from 0 to 6.28 points 100         private sampling range
show EXPR                                one line per trace (1 to 20)
xunit UNIT        yunit UNIT             display units
xlim LO to HI     ylim LO to HI          limits; LO or HI may be auto
title TEXT        xlabel TEXT    ylabel TEXT
```
Rules:
- Grammar change in `livesheet/engine/syntax.py`: a new statement kind `plot` with fields `plot_lines: list[tuple[str, str]]` (keyword, remainder), default empty. A text is a plot statement only when its first non-blank line, trimmed, equals `plot` and it has no `:=`, `≡`, `=` or `→` on that line. `plot := 3` and `plot =` keep their present meaning; `over`, `show`, `from`, `points` and the other keywords are only special inside a plot spec.
- Keyword lines: `over`, `show`, `xunit`, `yunit`, `xlim`, `ylim`, `title`, `xlabel`, `ylabel`. Anything else is the error `Unknown plot option 'word'`. Phase B adds `as`, `style`, `xscale`, `yscale`, `grid`, `against`, `mode` (before phase B these words are unknown options).
- `show` and `over` take the rest of the line as expression text. `from`, `to`, `points` inside an `over` line and `to` in a limit line are split on whitespace-delimited lowercase words at top level (not inside parentheses), like `to`/`step` in spec 001.
- `over` is required exactly once, `show` at least once.
- Engine API (new module `livesheet/engine/plotting.py`, Qt-free, imports sympy only):

```
@dataclass
class PlotTrace:
    label: str                 # expression text (phase B: label from 'as')
    x: list[float]             # display unit, NaN for undefined
    y: list[float]
    style_index: int           # 0-based trace number, renderer maps to colour
@dataclass
class PlotData:
    title: str
    x_label: str               # text incl. " [unit]"
    y_label: str
    x_unit: str                # "" when dimensionless
    y_unit: str
    traces: list[PlotTrace]
    x_limits: tuple[float, float]
    y_limits: tuple[float, float]
    x_ticks: list[float]
    y_ticks: list[float]
    skipped: int               # points not drawn
def nice_axis(lo, hi, manual_lo=None, manual_hi=None) -> tuple[float, float, list[float]]
```
`RegionResult` gets an optional `plot: PlotData | None = None` (default None; existing behaviour unchanged) and `output` is a one-line summary such as `plot 2 traces, 6 points`. The builder takes the already-parsed statement and the `env`, reusing the table machinery (`RangeVar`, per-value `env` copy, `measure`/dimension probing) but producing floats instead of strings. Evaluating 2 traces x 1000 points must take under 1 s (parse each expression once, probe the dimension once).

## Acceptance criteria
Engine-level via `Engine.evaluate`; `P` means `result.plot` of the plot region. Floating comparisons tolerance 1e-9 unless stated. Each sheet lists regions in reading order; the plot text lines are one region.

Basic range mode
1. Regions `v := 3 m/s`, `t := 0 s to 10 s step 2 s`, and the plot `plot / over t / show v*t`. Status ok, `defines` is empty. One trace; `x == [0,2,4,6,8,10]`; `y == [0,6,12,18,24,30]`; `x_unit == "s"`, `y_unit == "m"`; `x_label == "t [s]"`, `y_label == "v*t [m]"`; `x_limits == (0,10)`, `y_limits == (0,30)`; `x_ticks == [0,2,4,6,8,10]`; `y_ticks == [0,5,10,15,20,25,30]`; `skipped == 0`; `style_index == 0`; `output == "plot 1 traces, 6 points"` (plural form fixed on purpose: "traces").
2. Display unit. Same sheet plus `yunit mm` and `xunit ms`: `y == [0,6000,...,30000]`, `x == [0,2000,...,10000]`, units `"mm"`/`"ms"`, `y_limits == (0,30000)`, `y_ticks` step 5000, `x_ticks` step 2000 from 0 to 10000, labels `"v*t [mm]"` and `"t [ms]"`.
3. Two traces. Same as 1 plus a second line `show 2*v*t`: two traces, second `y == [0,12,...,60]`, `style_index == 1`, `y_limits == (0,60)`, `y_ticks == [0,10,20,30,40,50,60]`, `y_label == "[m]"` (with two traces the text part is empty; no leading space).
4. Sampling mode. Plot `plot / over x from 0 to 6.283185307179586 points 5 / show sin(x)` with nothing else on the sheet: x equals `0, pi/2, pi, 3*pi/2, 2*pi` within 1e-12; y equals `0, 1, 0, -1, 0` within 1e-12; `x_unit == ""`, `y_unit == ""`; `y_limits == (-1,1)`, `y_ticks == [-1,-0.5,0,0.5,1]`; `x_label == "x"`. Without `points`, the same plot has exactly 101 values per trace. `x` is not defined as a sheet name afterwards (a later region `x =` reports the normal not-defined error).
5. Vector mode. `X := [0, 1, 2, 3]`, `Y := [0, 1, 4, 9]*m`, plot `over X / show Y`: `x == [0,1,2,3]`, `y == [0,1,4,9]`, `y_unit == "m"`, `x_limits == (0,3)` with ticks `[0,0.5,1,1.5,2,2.5,3]`, `y_limits == (0,10)` with ticks `[0,2,4,6,8,10]`. Row and column orientation give the same data (`X := [0; 1; 2; 3]` instead). `show 2*Y` gives `y == [0,2,8,18]`.
6. Vector with units on both axes. `X := [0, 1, 2]*s`, `Y := [0, 3, 6]*m`: `x_unit == "s"`, `y_unit == "m"`; `xunit ms` gives `x == [0,1000,2000]`.
Limits
7. Manual limits on sheet 1: `xlim 2 s to 8 s`, `ylim 0 m to 40 m` give `x_limits == (2,8)`, `x_ticks == [2,3,4,5,6,7,8]`, `y_limits == (0,40)`, `y_ticks == [0,5,10,...,40]`; trace data is unchanged (still 6 points; clipping is the renderer's job). `xlim 2000 ms to 8 s` gives the same `x_limits`. With `xunit ms` added, `xlim 2 s to 8 s` gives `(2000, 8000)`.
8. Half-automatic. `xlim auto to 8 s` on sheet 1 gives `x_limits == (0,8)`, ticks `[0,1,...,8]`. `ylim 5 m to auto` gives `y_limits == (5,30)`, y ticks step 5 (5 to 30).
9. Constant trace. Plot `over t / show 5 m` on sheet 1: `y_limits` equals `(4.4, 5.6)` within 1e-9 and `y_ticks` equals `4.4, 4.6, ..., 5.6` (7 values). `show 0 m`: `y_limits == (-1,1)`, ticks `[-1,-0.5,0,0.5,1]`.
10. `nice_axis` unit tests (direct): `(0,10) -> (0,10,[0,2,4,6,8,10])`; `(0,9) -> (0,10,[0,2,...,10])`; `(0,0.7) -> (0,0.7,[0,0.1,...,0.7])` (step 0.1, 7 intervals); `(-3,17) -> (-5,20,[-5,0,5,10,15,20])` (step 2 would give 10 intervals, so step 5); `(1234,1250) -> (1234,1250,[1234,1236,...,1250])` (step 2, 8 intervals); exact multiples must not widen (`(0,30)` with step 5 stays `(0,30)`, not `(0,35)`).
Gaps
11. Undefined points. Plot `over x from -2 to 2 points 5 / show 1/x`: `x == [-2,-1,0,1,2]`, `y == [-0.5,-1,NaN,1,0.5]`, `skipped == 1`, `y_limits == (-1,1)`. A trace that is complex for some points (`show sqrt(x)` over the same x): `y` is NaN for x = -2 and -1, `skipped == 2`.
Live update
12. Evaluate the sheet of criterion 1, then evaluate again with `v := 6 m/s`: second result has `y == [0,12,...,60]` and `y_limits == (0,60)`; the first `PlotData` object is not modified. A definition changed below the plot does not change the plot; a global (`v ≡ 6 m/s`) placed below the plot does.
Errors (status `error`, `plot` is None, message must contain the quoted part)
13. Structure: plot with only `plot` or no `over` -> "over"; no `show` -> "show"; two `over` lines -> "only one 'over'"; `colour red` -> "Unknown plot option 'colour'"; 21 `show` lines -> "too many traces (max 20)".
14. `over q` with `q` undefined -> "q is not defined"; `over 5` -> "range variable or a vector"; `over x from 0 to 1 points 1` -> "points must be between 2 and 10000"; `points 10001` -> same; `over x from 0 s to 1 m` -> "Units do not match".
15. Wrong shape: range mode with `show Y` (a vector) -> "needs a single value"; vector mode with `show 5` -> "needs a vector"; vector mode with traces of length 3 and x of length 4 -> "same length".
16. Units: `xunit kg` with seconds -> "Units do not match"; `yunit s` with metres -> "Units do not match"; two traces `show v*t` and `show t` -> "different units"; `xlim 5 m to 10 m` on a seconds axis -> "Units do not match"; `xunit s` on a dimensionless x -> "xunit given but x has no unit"; `xlim 8 s to 2 s` and `xlim 3 s to 3 s` -> "lower limit must be below upper limit".
17. Nothing to draw: `show sqrt(-1) m` (always complex) -> "no finite values to plot".
18. A plot placed above the range definition it uses -> "t is not defined" (reading order). A name that is a range variable in a `show` outside a range-mode plot is still the existing "t is a range variable" error elsewhere (unchanged).
19. Errors in one trace make the whole plot an error (no partial plots). Errors never raise an exception out of `Engine.evaluate`.
Regression
20. `plot := 3` then `plot =` still gives `= 3`; every existing test in tests/ passes unchanged; a sheet without plot regions produces an unchanged `.lsheet`.

Document format (tests in tests/test_document.py)
21. A `SheetDocument` with one math region and one plot region (`text="plot\nover t\nshow v*t"`, w=420, h=280) round-trips through `to_json`/`from_json` with equal regions; the JSON has `"version": 2` and the plot region carries `"kind": "plot"`, `"w": 420.0`, `"h": 280.0`. A sheet with only math/text regions serialises with `"version": 1` and without `w`/`h` keys, and `examples/demo.lsheet` loaded and re-saved equals its current file content (byte for byte, after the existing formatting).
22. A version-1 file loads as before; a plot region without `w`/`h` loads with 400 x 260; version 3 gives "newer LiveSheet version"; an unknown kind still raises `DocumentError`.
23. Reading order: a plot region at y=300 is evaluated after a math region at y=100 and before one at y=500.

GUI (tests/test_gui*.py, Qt parts may skip when PySide6 cannot load, as today)
24. `paint_plot(painter, rect, data)` on a 400 x 260 `QImage` filled white leaves more than 500 non-white pixels for the data of criterion 1 and does not raise for: a single point, all-constant data, a trace with NaN gaps, manual limits that exclude all data (frame still drawn).
25. `Insert > Plot` adds exactly one region of kind plot with the starter text; editing the text to the sheet of criterion 1 makes `region.result.plot` have 6 points; changing `v` in the math region above updates the plot data without any other action; saving and reloading the sheet gives an equal plot spec and size.
26. Delete of a selected plot region (Backspace) does not crash and removes it from the document (regression for G4).
27. PDF export of a sheet with one plot: the file starts with `%PDF` and is larger than the same sheet without the plot; the manual tester opens it and checks axes, ticks, unit labels and trace(s) visually (vector, no blur when zoomed).

Phase A edge cases
- A range with one value (`b := 2 to 2`) plots one point; a single point has no line; the renderer shows a small dot for isolated points (single points and points between gaps).
- Descending ranges plot in the order given; limits come from min/max, not from order.
- Very large or very small magnitudes (1e-9 .. 1e9) work with the nice axis rule; tick labels use the existing `format_number` (6 significant digits); the renderer may switch to shorter text but does not drop ticks.
- Plot over a range variable that is also used in a table above it works; one range variable can feed many plots.
- A trace expression that calls a user function (`f(t)`) works as in tables.
- Nested plot specs, plots inside plots, text regions mentioning `plot` are not special.
- Empty spec (`plot` only) is not an error in the GUI, it shows the hint; at engine level it returns the "over" error (criterion 13), and the GUI maps that single message to the hint only when the spec has no other lines.
- Performance: 10000 points per trace limit comes from spec 001; with 20 traces that is 200000 points: allowed, not performance-guaranteed beyond criterion "2 traces x 1000 points < 1 s".

---

# Phase B: extras

Each item adds keyword lines (see phase A, they are "unknown option" until implemented).

## B1 Scales, labels, markers, grid
Behaviour:
- `show EXPR as TEXT` sets the trace label (rest of the line after the last top-level ` as `). Default label is the expression text. A legend (list of colour swatch plus label, top-right inside the frame) is drawn when there are 2 or more traces or any trace has an explicit label; `legend off` hides it (`legend on` is the default behaviour above). `PlotTrace.label` and a `PlotData.legend: bool` carry this to the renderer.
- `show EXPR style S` where S is `line` (default), `points` or `both` chooses lines, markers (small filled circles) or both; `PlotTrace.style` is that word. `as` and `style` may be combined in the order `show EXPR as TEXT style S`.
- `xscale log` / `yscale log` (default `linear`). On a log axis only values greater than 0 are drawn; others are skipped and counted in `skipped`. Automatic limits snap outward to powers of ten; ticks are the powers of ten inside the limits; the minor-tick positions (2..9 times a decade) are in `PlotData.x_minor_ticks`/`y_minor_ticks` for the renderer. Manual limits must be greater than 0 (error `log axis needs positive limits`) and are used as given.
- `grid off` hides grid lines (`grid on` default); `PlotData.grid`.
Acceptance criteria (B1):
1. `X := [1, 10, 100, 1000]`, `Y := [2, 4, 8, 16]`, plot `over X / show Y / xscale log`: `x_limits == (1,1000)`, `x_ticks == [1,10,100,1000]`, `y_limits == (2,16)` linear with step 2 ticks `[2,4,...,16]`. Data `3 .. 700` gives limits `(1,1000)`. With `yscale log` and `Y := [0.003, 5, 700]`: `y_limits == (0.001,1000)`, `y_ticks == [0.001,0.01,0.1,1,10,100,1000]`.
2. `X := [0, 1, 10]`, `xscale log`: the point at 0 is skipped, `skipped == 1`, the two other points remain; `xlim 0 to 10` with `xscale log` -> error "log axis needs positive limits".
3. Labels and styles: `show Y as load` gives `label == "load"`; no `as` gives the expression text; `style points` gives `traces[0].style == "points"`; `style dots` -> error "style must be line, points or both"; `legend` is true for 2 traces, false for 1 unlabeled trace, true for 1 labeled trace, false with `legend off`.
4. `grid off` -> `grid == False`, default `True`.
5. Unit label with log axis keeps the unit in brackets; `xunit` conversion happens before the log rule (so `X := [1, 1000]*m`, `xunit km`, `xscale log` gives limits `(0.001, 1)`).
Edge cases: `xscale` or `yscale` word other than `linear`/`log` -> "scale must be linear or log"; a log axis whose finite data is all non-positive -> "no finite values to plot".

Size: about 2 days (engine 1 day, renderer 1 day).

## B2 Parametric and polar
Behaviour:
- `show Y against X`: each trace may have its own x expression, evaluated over the same `over` values (range, sampling or, in vector mode, vectors of equal length). Without `against`, x is the `over` value (phase A behaviour). All traces still share one x axis, so all x expressions must share one dimension (error `different units`); limits are computed from all traces' x data.
- `mode polar`: `over` supplies the angle; each `show` expression is the radius. Points are converted to Cartesian (x = r cos a, y = r sin a) in the display unit of r. The angle must be dimensionless (plain numbers are radians) or a unit that converts to a dimensionless number if the unit system defines an angle unit; anything else is `Units do not match`. In polar mode both axes use the same unit, equal scale (`PlotData.equal_aspect = True`), and the limits are symmetric: `nice_axis(-R, R)` with R the largest |r| (applied to both axes). `against`, `xunit`/`yunit` different from each other, and `xscale`/`yscale log` are errors in polar mode (`not available in polar mode`); a single `unit` line is not added (the unit comes from r; `xunit` and `yunit` must agree or be absent). Negative r is plotted as is (point on the opposite side).
Acceptance criteria (B2):
1. Circle: `over a from 0 to 6.283185307179586 points 5 / show sin(a) against cos(a)`: `traces[0].x == [1,0,-1,0,1]` and `.y == [0,1,0,-1,0]` within 1e-12; `x_limits == (-1,1)`, `y_limits == (-1,1)`.
2. Two traces with different `against` expressions share the x axis: limits cover both traces; `show t against 2 m` mixed with `show t against 3 s` -> "different units".
3. Polar: `mode polar / over a from 0 to 6.283185307179586 points 5 / show 2`: points `(2,0),(0,2),(-2,0),(0,-2),(2,0)` within 1e-12, `x_limits == y_limits == (-2,2)`, `equal_aspect == True`. With `show 2 m`: both units `"m"`, labels contain `[m]`.
4. Polar errors: `over a from 0 s to 1 s` -> "Units do not match"; `show 1 against 2` in polar mode -> "not available in polar mode"; vector mode polar works (`A := [0, 1.5707963267948966]`, `R := [1, 2]` gives points `(1,0)` and `(0,2)` within 1e-12).
5. Unknown mode word -> "mode must be cartesian or polar" (`cartesian` is the default).
Edge cases: `against` with an expression of the wrong shape follows the phase A shape errors; `legend`/`style` apply per trace as in B1; polar with all r equal zero uses the zero-range rule of `nice_axis` (limits `(-1,1)`).

Size: about 2 days (engine 1.5 days, renderer 0.5 day: aspect ratio and symmetric frame).

---

## Out of scope (later specs)
Second y axis, 3-D surface plots, contour/vector-field/bar/histogram plots, interactive zoom/pan/trace read-out, mouse-dragged axes or limits, error bars, annotations on the chart, secondary x axis, PNG/SVG/CSV export of a plot alone, plot of data read from files, animation, themes, user-set colours and line widths, date axes, plotting solve results directly, a dialog-based plot editor (a form on top of the same spec text is a follow-up), push-down layout for tall regions (backlog 20).

## IP check
Pass (manager confirmed 2026-10-28; acceptance numbers of criteria 1-11 recomputed from the nice axis rule). Concept only: a chart with several traces over a shared independent variable, unit-aware axes, automatic or user limits. These are generic charting ideas. Syntax is our own: a text spec with `plot`, `over`, `show`, `xunit`, `yunit`, `xlim`, `ylim`, `title`, `xlabel`, `ylabel` (B: `as`, `style`, `legend`, `xscale`, `yscale`, `grid`, `against`, `mode`); no vendor keyword set and no placeholder-based axis-expression editing (the vendor-style approach of typing expressions into placeholders on the axes of an inline chart is deliberately NOT used; editing is text only). Tick algorithm (1-2-5 steps) is a textbook technique. Colour palette, default sizes and wording are our own. File schema is our own (`kind: "plot"`, `w`, `h`); no vendor file format is touched. Only public help pages were consulted, and only via search result summaries; nothing copied. No known patent concern for plain XY charting; not legal advice.

## Fits current architecture?
- `livesheet/engine/plotting.py` (new, Qt-free): `PlotTrace`, `PlotData`, `nice_axis`, builder `build_plot(statement, env, engine)`. Reuses `RangeVar`, the per-value environment copy, dimension probing and `measure` from the table implementation in `evaluator.py`; unit conversion via the existing target-unit code path (`_format_measured`'s conversion logic should be factored into a helper that returns a float in a given unit rather than text). Vector mode reads SymPy matrices from `env` (spec 002a).
- `livesheet/engine/syntax.py`: new statement kind `plot` with `plot_lines`; recognised only by the first-line rule; existing parsing order unchanged. `evaluator.py`: `RegionResult.plot` (default None), dispatch in `_run_statement` and in the pass that handles global definitions (a plot defines nothing).
- `livesheet/document.py`: `RegionData.kind` accepts `"plot"`, optional `w`/`h` (default None, written only for plots), `FORMAT_VERSION` accepted up to 2, writer picks version 1 or 2 (see Saving).
- `livesheet/gui/`: new `PlotRegion` (in `regions.py` or a new `plotregion.py`) that holds the spec text editor, size handle and calls `paint_plot`; new `plotview.py` with `paint_plot`; `worksheet.py` creates/loads/saves plot regions and feeds their text into the same `Engine.evaluate` call (keyed like other regions) and hands `RegionResult.plot` back; `main_window.py` gets `Insert > Plot` and the export path needs no change except that `PlotRegion.paint` must be print-safe (no widget proxies, only painter calls).
- Dependencies: none new in phase A (numpy and scipy are already dependencies but are not required here). Matplotlib is not needed.
- Tests: `tests/test_plot.py` (engine, criteria 1-20 and `nice_axis`), additions to `tests/test_document.py` (21-23), `tests/test_gui_helpers.py` or a new `tests/test_gui_plot.py` (24-26, skipped when PySide6 cannot load), manual PDF check (27). The tester must also launch the real app, create a plot, edit a number above it and watch the redraw, resize it, save/reopen, and export a PDF.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. Rendering: `QPainter` directly (recommended here: no new dependency, same code path for screen, PDF and image, small and fully ours, but we draw axes/ticks/legend ourselves, about 1 day) versus matplotlib (PSF-style permissive licence, mature tick/legend/log/polar handling, vector PDF of its own, but a large new dependency with transitive packages, a second text/font pipeline that will look different from the canvas, and slower start-up). A third option, pyqtgraph (MIT, depends on numpy), is interactive but raster-oriented and weaker for PDF. Theo to decide; the engine API (`PlotData`) is the same in all cases.
2. Is the text-spec editing model acceptable for phase A (fast, testable, versionable, no vendor-like placeholder UI), with a form dialog as a later follow-up?
3. Keyword review: `over`, `show`, `xlim`, `ylim`, `xunit`, `yunit`, `against`, `mode polar` are own words; please confirm in the same pass as the notation review of spec 001/002.
4. File format: bumping `version` to 2 only for sheets that contain a plot (so plot-free sheets stay byte-identical and readable by older builds). Alternative: always version 2. Confirm the proposal.
5. Dissimilar traces (for example force and displacement) are an error with one y axis here. Is a second y axis wanted soon (new spec) or are two separate plots acceptable?
6. Default auto display unit: "the unit the numeric formatter would print for the first finite point" can differ between runs when the data changes (m versus mm). Alternative: always the unit as written in the expression's base units. Prefer the proposal for consistency with `=`; confirm.
7. Default sampling count 101 and default size 400 x 260 are arbitrary choices; adjust if Theo prefers other values.
8. Overlap with regions below a plot until backlog item 20 (push-down layout) exists: accept for phase A, or schedule item 20 first?
9. Should `paint_plot` also be exposed as "Export plot as PNG/SVG" (cheap with the QPainter approach)? Out of scope here; suggest as backlog extra.
