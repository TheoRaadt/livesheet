# 031 Three-dimensional surface plots (phase A static surface, phase B rotate/zoom, phase C sketch)

Status:
- IP-reviewed by manager 2026-11-12. Header keyword renamed from the former command name `plot3d` to
  `surface` at the manager's required change (ip-cleanroom: no vendor keyword 1:1). Phase A approved.
- Theo approved 2026-11-12: Q3 (saved view stored as new optional region fields `view_az`, `view_el`,
  `view_zoom`) and Q4 (3-D regions rotate on drag inside the chart; the region moves from its frame
  ring, an exception to spec 023 for 3-D regions only). Phase B is therefore approved too.
- Phase C remains a sketch only and needs its own spec and IP review.
- Log note: the handoff line for this spec must be appended to docs/board/log.md by an agent with
  Bash or Edit (see the manager's log entry for 2026-11-12); this file is the record of the decisions.

Supersedes the feasibility note docs/board/specs/016-3d-plots-and-animation-research.md for the
3-D plot part only (016 stays the research record; its animation track is not covered here).

Source inspiration (concept only, nothing copied):
- Wikipedia, "Surface plot" (CC BY-SA 4.0): a function of two variables drawn as a height surface
  over a grid. Concept only. Naming was checked earlier, as recorded in spec 016 (accessed 2026-10-30).
- Wikipedia, "Painter's algorithm" (CC BY-SA 4.0), accessed 2026-11-12: draw polygons from far to
  near so nearer ones overwrite farther ones; known weakness with cyclic overlaps. Concept only.
- Wikipedia, "Orthographic projection" (CC BY-SA 4.0), accessed 2026-11-12: parallel projection,
  no perspective convergence. Concept only.
- Shading by face normal against one fixed light direction ("flat shading"), general computer-
  graphics textbook technique. No source text used.
- Drag-to-orbit and wheel-to-zoom are the general mouse convention of 3-D viewers; described in our
  own words in phase B.
- No vendor product's documentation, screenshot, UI, keyword list or example was read for this spec.

---

## Sizing and phase split

- **Phase A (static surface, APPROVED for dispatch, about 3 days)**
  - A1 engine: `surface` statement recognition, grid sampling, `SurfaceData`, limits, ticks, cell
    visibility, performance rule (about 1 day).
  - A2 renderer and GUI: pure layout function, QPainter drawing (mesh or wireframe, box, labels),
    `Insert > 3-D plot`, region dispatch, PDF through the existing painter path (about 2 days).
  - No `.lsheet` format change in phase A.
- **Phase B (rotate, zoom, saved view, about 1.5 days, APPROVED by Theo 2026-11-12, dispatch after A
  is accepted)**: mouse orbit and wheel zoom in the chart, a saved camera per 3-D plot region as new
  optional region fields, a "Reset 3-D view" menu entry, drag-time preview. Includes the spec 023
  exception in section B.0.
- **Phase C (sketch only, not for dispatch)**: parametric curves, 3-D scatter, several surfaces per
  plot, contour lines, perspective projection, a labelled-field dialog. Each becomes its own spec.

Phase A is the minimal useful 3-D plot: one surface, text spec only, fixed default view, no
interaction. The `view` text line in A gives the user a way to orient the picture before B exists.

---

## User story
As an engineer I want to chart a quantity that depends on two variables, for example a stress over a
plate's width and depth, as a height surface on the sheet. I set the two sample ranges, the
expression, and optionally the axis units and limits, in the same plain text way I already set a 2-D
plot. The surface redraws when a number above it changes, it keeps the units of the values, it saves
with the sheet, and it prints to PDF as vector graphics. In phase B I can turn the picture with the
mouse to read it, and the chosen view is kept with the sheet.

## Behaviour (own words)

### The region
- A 3-D plot is a region of the existing kind `"plot"`, exactly like a 2-D plot. It is recognised by
  its first non-blank line, which is `surface` instead of `plot`. It takes part in reading order and
  never defines a name.
- Its drawn chart is one surface. Phase A draws the surface, its bounding box and the axis labels.
- Size and minimum size are the same as the 2-D plot region (default 400 x 260, minimum 200 x 140,
  grid snapping as spec 004).

### What is drawn
- `over NAME ...` gives the first horizontal axis, `across NAME ...` gives the second horizontal
  axis. Each is either an existing range variable (spec 001) or a vector (spec 002a), or the sampling
  form `NAME from A to B points N` (same sub-grammar as spec 004's `over`, reused, not copied again).
- `show EXPR` gives the height. The grid is evaluated at every pair of sample values: with `xs` the
  sample values of `over` and `ys` the sample values of `across`, the height at grid cell (i, j) is
  `EXPR` with `NAME_over = xs[i]` and `NAME_across = ys[j]`.
- Sample values are kept in the order given (ascending or descending both work). Limits are taken
  from the minimum and maximum, not from the order (same as spec 004).
- The height is drawn as a mesh of quadrilaterals (`draw mesh`, default) or as wire lines only
  (`draw wire`).

### Units
- Each of the three axes has one display unit. The horizontal axes carry the unit of their sample
  values. The height axis carries the unit of `show`. Dimensionless values have an empty unit.
- Defaults are the same as spec 004: the SI-simplified unit text the existing formatter would print
  for the first finite value. `xunit`, `yunit`, `zunit` select another unit of the same dimension.
- Labels: `title`, `xlabel`, `ylabel`, `zlabel` replace the text part. The default text of an axis is
  the name of its `over`/`across` value, or the expression text for the height. The unit part is
  appended in square brackets when not empty, as in spec 004.

### Limits and ticks
- Automatic limits per axis use spec 004's `nice_axis` rule, applied to the sample values (for the two
  horizontal axes) and to the finite height values (for the height axis). Ticks use the same rule.
- `xlim LO to HI`, `ylim LO to HI`, `zlim LO to HI` set manual limits; either side may be `auto`
  (same rules and error wording as spec 004).
- **Cell visibility rule (phase A, normative)**: a grid cell (the quadrilateral between four
  neighbouring grid points) is drawn only when all four of its heights are finite and each of its four
  corners lies inside the manual limits of the three axes (inclusive). A cell that fails is dropped
  whole; there is no partial clipping of a cell. The surface edge is therefore jagged at a manual
  limit. Accepted for phase A.
- The count of drawn cells is part of the result (`cells_drawn`), so the rule can be tested
  without pixels.

### Viewing (phase A: fixed view from text)
- The view is orthographic (no perspective). The default view is azimuth 40 degrees and elevation
  30 degrees.
- Optional line `view AZ EL`: azimuth and elevation in degrees, plain numbers (sign allowed). The
  elevation must lie in [-90, 90]. The line is read once per evaluation and sets the view of the
  region.
- Projection definition, so the developer and tester use the same maths (own statement of the
  standard orthographic setup): with `a` = azimuth and `e` = elevation, the unit viewing direction
  towards the viewer is `d = (cos e cos a, cos e sin a, sin e)`, the screen right vector is
  `r = (-sin a, cos a, 0)` and the screen up vector is `u = (-sin e cos a, -sin e sin a, cos e)`.
  The three vectors are mutually perpendicular unit vectors. The normalised cube is `[-0.5, 0.5]^3`
  after mapping each axis's limits to that range. Screen x = centre_x + S * (p . r), screen y =
  centre_y - S * (p . u), depth = p . d (larger is nearer the viewer).
- Scale: `S = 0.42 * min(W, H) * zoom` where W, H is the size of the chart rectangle in pixels and
  zoom = 1 in phase A. Every projected corner of the cube then lies within `0.9 * min(W, H) / 2` of
  the centre.
- Drawing order: cells are sorted by their mean depth, farthest first, and drawn in that order
  (painter's algorithm). Known artefacts on steep surfaces where cell depths overlap are accepted for
  phase A (open question 8).
- Shading (mesh only): each cell's unit normal is the normalised cross product of its two diagonals,
  oriented towards the viewer. Brightness = 0.35 + 0.65 * max(0, n . L) with the fixed light
  direction `L` = normalised (-0.3, -0.5, 0.8). Fill colour = fixed base colour times brightness (base
  colour is our choice and is not user-settable in phase A).
- Box and labels: the 12 edges of the cube are drawn as thin grey lines. Each horizontal axis gets its
  tick labels and axis title along the floor edge that is nearest to the viewer for that axis. The
  height axis gets its tick labels and title along the vertical edge whose corner is nearest to the
  viewer. Tick labels use the existing number formatter (6 significant digits).

### Errors and states
- A region with an empty spec (`surface` plus bare keywords) shows a hint, not an error, as in
  spec 004. The hint text is: "Empty 3-D plot: double-click to edit. Add an 'over' line, an 'across'
  line and one 'show' line."
- All evaluation errors show the message in the plot frame in the error colour (same presentation as
  spec 004). Errors never raise out of `Engine.evaluate`.

### Performance (normative)
- The height expression is parsed once per evaluation and its dimension is probed once. It is then
  evaluated over the whole grid through a fast path (a compiled function of the two sample values, as
  in spec 004's fast path). If the fast path fails for any reason, a per-point fallback is used, as in
  spec 004. Result must be the same either way.
- Grid per axis is limited to 100 (so at most 10000 cells per plot). Default is 25 per axis.
- Targets measured on the developer's Mac: a 25 x 25 evaluation under 0.5 s; a 100 x 100 evaluation
  under 3 s; the surface layout (cell list, sorting, shading) for 100 x 100 under 0.3 s. The tester
  re-measures and reports; a result within 2x of the target is a pass with a note.

### Saving (.lsheet)
- Phase A: no format change. A 3-D plot region is written as today's `plot` region kind: `text`
  holds the spec lines, `w` and `h` hold the size. The writer's version choice is unchanged (a sheet
  with a plot region already gets the version a 2-D plot gets).
- Phase B adds three optional numeric keys on 3-D plot regions only (see Phase B below).
- Surface results are never stored; they are recomputed on load.

### PDF export
- The surface is drawn through the same `QPainter` path as the screen (`paint_surface`), so PDF
  output is vector polygons and lines and text, not a bitmap. The export path needs no change except
  that the region's paint must be print-safe, as for 2-D plots.

### Phase B: rotate, zoom and saved view (APPROVED by Theo 2026-11-12; dispatch after phase A is accepted)
- **B.0 Interaction ownership (exception to spec 023, approved by Theo 2026-11-12, for 3-D regions only)**:
  for a 3-D plot region that is not being edited, a press inside the chart rectangle starts a rotate drag
  and does not start a move. Moving the region is then done by pressing on its frame ring (the padding ring
  of spec 023, plus its 3-unit outer ring), which for 3-D plots works in both the selected and
  not-yet-selected states. A press on the resize handle still resizes. Spec 023's rule for 2-D plot
  regions and all other regions is unchanged.
- **Rotate**: a left-button drag inside the chart changes the view by 0.5 degrees per screen pixel of
  pointer movement. Moving right increases the azimuth. Moving up increases the elevation. The
  azimuth wraps into [-180, 180). The elevation is clamped to [-90, 90].
- **Zoom**: wheel movement inside the chart multiplies `zoom` by 1.1 per 120 units of vertical wheel
  delta (one standard notch). `zoom` is clamped to [0.25, 4.0]. Wheel outside the chart keeps the
  canvas scroll behaviour.
- **Saved view (approved form: new optional region fields)**: after the first rotate or zoom, the region
  keeps `view_az`, `view_el` and `view_zoom` as optional numeric fields of the region record. They are
  written only for plot regions whose text is a `surface` spec and only once a stored view exists. Absent
  fields mean "use the `view` text line, or the default 40/30 with zoom 1". The orbit is not written back
  into the spec text.
- **Precedence**: stored fields win over the `view` text line. A text edit that changes the `view`
  line clears the stored fields for that region. Phase B adds no other text rewriting.
- **Reset 3-D view**: a region context-menu entry for 3-D plot regions removes the stored fields.
- **Drag preview**: while a rotate drag is in progress and the grid has more than 40 cells per axis,
  the surface is drawn as wire lines only; on release it is drawn in the chosen `draw` mode.
- Zoom and view are not kept for 2-D plot regions in this spec. 2-D plots stay as spec 004.

---

## Syntax proposal (own keywords)

```
surface
over x from -1 m to 1 m points 25     first horizontal axis: range, vector, or sampling
across y from -1 m to 1 m points 25   second horizontal axis (same forms as over)
show EXPR                             one height expression (exactly one line)
draw mesh | wire                      optional, default mesh
view AZ EL                            optional, degrees, default 40 30 (phase A)
xunit U  yunit U  zunit U             optional display units
xlim LO to HI  ylim LO to HI  zlim LO to HI   optional limits; LO or HI may be auto
title TEXT  xlabel TEXT  ylabel TEXT  zlabel TEXT
```

Rules:
- Statement recognition: a text whose first non-blank line, trimmed, equals `surface` and that has no
  `:=`, `≡`, `=` or `→` on that line is a 3-D plot statement. `surface := 3` and `surface =` keep their
  present meaning (a definition of a name `surface`). `plot` (2-D) recognition is unchanged.
- Keyword lines: `over`, `across`, `show`, `draw`, `view`, `xunit`, `yunit`, `zunit`, `xlim`, `ylim`,
  `zlim`, `title`, `xlabel`, `ylabel`, `zlabel`. Anything else is the error `Unknown 3-D plot option
  'word'`.
- `over` and `across` each appear exactly once, `show` exactly once. `over` and `across` must name
  different things.
- `over` and `across` take the same sub-grammar as spec 004's `over` (range name, vector name, or
  `NAME from A to B [points N]`). `points` default 25, allowed 2 to 100.
- `draw` takes exactly one of the words `mesh` or `wire`.
- Phase C adds `mode`, `contour`, `perspective`, and the parametric/scatter forms; none exist in
  phase A or B, so those words are unknown options until then.

Grammar change in `livesheet/engine/syntax.py`: a new statement kind `surface` with `plot_lines`
(keyword, remainder) exactly as `plot`, recognised by the first-line rule above. Existing parsing order
unchanged.

Engine API (new module `livesheet/engine/surface.py`, Qt-free, may import sympy, numpy and
`engine/plotting.py` for `nice_axis`):

```
@dataclass
class SurfaceData:
    title: str
    x_label: str; y_label: str; z_label: str     # text incl. " [unit]"
    x_unit: str; y_unit: str; z_unit: str        # "" when dimensionless
    xs: list[float]                  # display unit, sample positions, given order
    ys: list[float]
    zs: list[list[float]]            # zs[j][i]: row j is the across index, column i the over index; NaN if undefined
    x_limits: tuple[float, float]; y_limits: tuple[float, float]; z_limits: tuple[float, float]
    x_ticks: list[float]; y_ticks: list[float]; z_ticks: list[float]
    draw: str                        # "mesh" | "wire"
    view_az: float; view_el: float   # degrees
    skipped: int                     # grid points whose height is undefined
    cells_drawn: int                 # cells passing the visibility rule
def build_surface(st, env: dict, engine) -> SurfaceData   # raises on any error
```

`RegionResult` gets `surface: SurfaceData | None = None` (default None; existing behaviour
unchanged). `output` is a one-line summary `surface NX x NY points`, for example `surface 3 x 3 points`.

Renderer (new module `livesheet/gui/surfaceview.py`, PySide6 only here):
- `layout_surface(data, rect, az, el, zoom, mode) -> SurfaceLayout` is a pure function: it returns the
  projected cube corners, the drawn cells (polygon, depth, fill colour or none, in draw order), the 12
  box edges and the tick and title anchor points. It does no painting, so it is unit-testable.
- `paint_surface(painter, rect, data, az, el, zoom, mode)` paints a `SurfaceLayout` with `QPainter`
  only. The same function serves screen, PDF and image.
- `PlotRegion` (in `livesheet/gui/plotregion.py`) chooses the surface path when its first non-blank line
  is `surface`. `is_plot_spec` stays for the 2-D case. A new helper `is_surface_spec(text)` (true when
  the first non-blank line is exactly `surface`) is added, and `engine_source` must also pass through
  texts whose first line is `surface`, instead of prefixing `plot`.

## Acceptance criteria

Engine checks use `Engine.evaluate` and read `result.surface` (abbreviated `S`). Floating comparisons
use tolerance 1e-9 unless stated. Matrices are written row by row: `[[row 0], [row 1], ...]`, and
`zs[j][i]` means row j (across index), column i (over index). Every number was hand-derived from the
spec 004 nice-axis rule and the cell rule, and the derivations were re-checked by reasoning (not by
running the engine) during the manager's IP review; the tester re-checks each one against the engine
before sign-off.

### Phase A1: engine (tests/test_surface.py)

A1-1. Basic surface. Region `surface / over x from 0 to 2 points 3 / across y from 0 to 2 points 3 /
show x + 2*y`. Status ok, `defines` empty. `S.xs == [0,1,2]`, `S.ys == [0,1,2]`,
`S.zs == [[0,1,2],[2,3,4],[4,5,6]]`. `S.x_limits == (0,2)`, `S.x_ticks == [0,0.5,1,1.5,2]`,
`S.y_limits == (0,2)`, `S.y_ticks == [0,0.5,1,1.5,2]`, `S.z_limits == (0,6)`,
`S.z_ticks == [0,1,2,3,4,5,6]`. Units all `""`, `S.draw == "mesh"`, `S.view_az == 40`,
`S.view_el == 30`, `S.skipped == 0`, `S.cells_drawn == 4`, `output == "surface 3 x 3 points"`.

A1-2. Units and display unit. Region `surface / over x from 0 m to 2 m points 3 / across y from 0 to 2
points 3 / show 500 N * (x/m) * y / zunit kN`. `S.zs == [[0,0,0],[0,0.5,1],[0,1,2]]`,
`S.z_unit == "kN"`, `S.x_unit == "m"`, `S.y_unit == ""`, `S.z_limits == (0,2)`,
`S.z_ticks == [0,0.5,1,1.5,2]`, `S.z_label == "500 N * (x/m) * y [kN]"`, `S.x_label == "x [m]"`,
`S.y_label == "y"`.

A1-3. Range variable as an axis. Sheet: `t := 0 s to 2 s step 1 s` (above the plot). Region
`surface / over t / across y from 0 to 1 points 2 / show t*y`. `S.xs == [0,1,2]` (unit `s`),
`S.ys == [0,1]`, `S.zs == [[0,0,0],[0,1,2]]`, `S.z_unit == "s"`, `S.x_unit == "s"`,
`S.z_limits == (0,2)`, `S.z_ticks == [0,0.5,1,1.5,2]`.

A1-4. Defaults and caps. `surface / over x from 0 to 1 / across y from 0 to 1 / show x + y` gives
`len(S.xs) == 25`, `len(S.ys) == 25`, `output == "surface 25 x 25 points"`. The same with
`points 100` on both axes is accepted (100 x 100). `points 101` is the error in E3.

A1-5. Manual horizontal limits on the A1-1 sheet with `xlim 0.5 to 1.5`: `S.x_limits == (0.5,1.5)`,
`S.x_ticks == [0.6,0.8,1,1.2,1.4]`. The same sheet with `xlim 0 to 1.5`: `S.cells_drawn == 2` (the
two cells in the interval x 1 to 2 have a corner outside the limit and are dropped whole); `S.zs`
unchanged (all 9 values still present). Also `ylim 0 to 1.5` gives `S.cells_drawn == 2` on the same
sheet, the cells in the interval y 1 to 2 being dropped.

A1-6. Manual height limit on the A1-1 sheet with `zlim 0 to 4`: `S.z_limits == (0,4)`,
`S.z_ticks == [0,0.5,1,1.5,2,2.5,3,3.5,4]` (step 0.5 by the nice-axis rule), `S.cells_drawn == 2`
(the cells whose corner heights reach 5 or 6 are dropped; the two cells with maximum corner height 3
and 4 are kept, since 4 is inside the inclusive limit).

A1-7. Undefined heights. Region `surface / over x from -1 to 1 points 3 / across y from 0 to 1 points 2
/ show 1/x`. `S.xs == [-1,0,1]`, `S.ys == [0,1]`, `S.zs == [[-1,NaN,1],[-1,NaN,1]]`, `S.skipped == 2`,
`S.cells_drawn == 0` (both cells touch the NaN column), `S.z_limits == (-1,1)`,
`S.z_ticks == [-1,-0.5,0,0.5,1]`. Status ok.

A1-8. Constant height. `show 5 m + 0*x` on the A1-1 axes: `S.z_limits` equals `(4.4, 5.6)` within 1e-9,
`S.z_ticks == [4.4,4.6,4.8,5.0,5.2,5.4,5.6]`, `S.z_unit == "m"`, `S.cells_drawn == 4`.

A1-9. No finite height. `show sqrt(x - 10)` over `over x from 0 to 2 points 3`: status error with
message containing `no finite values to plot`; `result.surface is None`.

A1-10. Sampling names shadow only inside the plot. Sheet: `x := 7`, then region
`surface / over x from 0 to 1 points 2 / across y from 0 to 1 points 2 / show x + y`. `S.xs == [0,1]`.
A later math region `x =` still gives `= 7`.

A1-11. Parse once. With a counting wrapper around `Engine.parse`, one evaluation of the A1-4
25 x 25 sheet calls `Engine.parse` on the `show` text at most 2 times, whatever the grid size. The
same check at 100 x 100 is also at most 2.

A1-12. Performance. A 25 x 25 surface of `show x*y` (default sampling) is built in under 0.5 s. A
100 x 100 surface of the same expression is built in under 3 s. Both measured on the developer's
Mac and re-measured by the tester (pass within 2x of the target, with a note).

A1-13. Regression. `plot := 3` then `plot =` still gives `= 3`. `surface := 3` then `surface =` gives
`= 3`. Every existing test in `tests/` passes unchanged. A sheet with no surface region and no 2-D
plot region produces an unchanged `.lsheet`.

A1-14. The 2-D grammar is unaffected: a text starting with `plot` and containing `across` is still a
2-D plot, which rejects `across` with `Unknown plot option 'across'` (spec 004 rule).

### Phase A1: error cases (status error, `surface` is None; the quoted text must appear in the message)

E1. Structure: region with no `over` line -> `surface needs an 'over' line`; no `across` line ->
`surface needs an 'across' line`; no `show` line -> `surface needs a 'show' line`; two `show` lines ->
`surface takes exactly one 'show' line`; two `over` lines -> `only one 'over' line is allowed`
(same wording family as spec 004); `over x` and `across x` on the same name -> `over and across need
different names`.
E2. Unknown option: `colour red` -> `Unknown 3-D plot option 'colour'`.
E3. Points: `over x from 0 to 1 points 1` -> `points must be between 2 and 100`; `points 101` on
either axis -> the same message.
E4. Range too long: sheet `t := 0 to 200 step 1` and `over t` -> `range has more than 100 values for a
3-D plot`. The same range as sampling form in `over` with more than 100 points is also rejected by E3.
E5. Draw word: `draw dots` -> `draw must be mesh or wire`.
E6. View: `view 40 95` -> `elevation must be between -90 and 90`; `view 40` -> `view needs two
numbers: azimuth and elevation`; `view 40 m` -> `view needs two plain numbers`.
E7. Units: `zunit kg` on a seconds height -> `Units do not match`; `zunit s` on a dimensionless height
-> `zunit given but z has no unit`; `xlim 5 m to 10 m` on a seconds axis -> `Units do not match`;
`xlim 2 to 1` -> `lower limit must be below upper limit`.
E8. Shape: `show X` with `X := [1,2,3]` -> `show 'X' needs a single value`; `over X` with a matrix that
is neither a row nor a column -> `over needs a vector (one row or one column)`.
E9. Undefined: `over q` with no `q` defined -> `q is not defined`.
E10. Reading order: a `surface` region above the range definition it uses -> `t is not defined`.
E11. Axis values: a sampling endpoint that is not finite, for example `over x from 0 to 1/0 points 3` (`log(0)` is not usable: the engine raises an unrelated `_log() got an unexpected keyword argument 'evaluate'` for it in 2-D plots too)
-> `Sampling limits must be finite real numbers` (same wording as spec 004). The tester confirms the
exact trigger on the engine before writing the test; if log(0) gives a different error, the test
uses whichever non-finite endpoint the engine accepts as non-finite and the message must be this one.
E12. Nothing raises: every error above comes back as a status error from `Engine.evaluate`.

### Phase A2: renderer and GUI (tests/test_surface_gui.py; Qt parts may skip when PySide6 cannot load)

A2-1. `layout_surface` for the A1-1 data, default view (az 40, el 30, zoom 1) on a 400 x 260 rectangle:
every projected corner of the cube lies within `0.9 * 260 / 2 = 117` pixels of the rectangle centre
(by hand: the cube's corners lie at most 0.866 from its centre, times S = 0.42 * 260 = 109.2, giving
at most about 94.5 pixels). The returned mesh cell list has `cells_drawn` entries (4 for A1-1).
A2-2. Depth order: the cell list returned by `layout_surface` is sorted by depth, farthest first, with
non-decreasing depth values (tolerance 1e-12).
A2-3. Draw modes: `mode="mesh"` returns filled polygons with a fill colour for every drawn cell;
`mode="wire"` returns the same cells as outlines with no fill. Both return the 12 box edges.
A2-4. Shading range: every cell's brightness factor lies in [0.35, 1.0].
A2-5. Labels: the number of tick anchors returned equals `len(x_ticks) + len(y_ticks) + len(z_ticks)`;
the title and three axis-title anchors are returned.
A2-6. `paint_surface(painter, rect, data, ...)` on a 400 x 260 `QImage` filled white leaves more than 500
non-white pixels for the A1-1 data. It does not raise for: a 2 x 2 grid (one cell), the constant surface
of A1-8, the NaN-hole surface of A1-7 (box and labels only), and a surface whose `zlim` excludes every
cell (frame and box still drawn; `cells_drawn == 0`).
A2-7. `Insert > 3-D plot` creates exactly one plot region whose text is
`surface\nover \nacross \nshow ` (starter text) and shows the hint. No dialog opens. Double-clicking
the region opens the raw text editor. The "Use dialog..." control is not shown for a `surface`
region. `Insert > Plot` (2-D) still opens the 2-D dialog, unchanged.
A2-8. Live update: completing the starter text to the A1-1 spec makes the region show the surface.
Changing a number in a math region above it and recalculating updates the surface data on the next
pass without any other action.
A2-9. Save and reopen: text, `w`, `h` round-trip equal. The written version for a sheet with a 3-D plot
is the version the same sheet gets with a 2-D plot in place of it (no new version).
A2-10. PDF: exporting a sheet with one 3-D plot gives a file starting with `%PDF` that is larger than the
same sheet without it. The tester opens the PDF and checks that the surface polygons are vector
(no blur at high zoom), that axis labels and tick labels are readable, and that units appear.
A2-11. Delete: Backspace on a selected 3-D plot region removes it without a crash (regression for G4).
A2-12. Real window (tester, Theo's Mac, computer use): create via Insert > 3-D plot, type the A1-1
spec, check the surface, change a number above and watch the redraw, resize, save, reopen, export PDF,
close. Report each step with pass or fail.

### Phase B: rotate, zoom, saved view (APPROVED by Theo 2026-11-12; tests/test_surface_view.py and the tester's real-window pass)

B.0 Ownership. In a 3-D region that is not being edited, a press inside the chart rectangle does not
move the region. A press on the frame ring (spec 023's padding ring plus its 3-unit outer ring) moves it.
A press on the resize handle resizes. Test: press at the chart centre, drag 30 px right, release:
`region.pos()` unchanged.
B1. Rotate: press at (100, 100) inside the chart, move to (140, 100), release. The azimuth goes from 40
to 60 (change exactly +20.0). Elevation unchanged. Then press at (100, 100), move to (100, 80), release:
elevation goes from 30 to 40 (+10.0). Tolerance 1e-9.
B2. Clamp and wrap: from elevation 85, drag up 20 px -> elevation 90.0. From elevation -85, drag down
20 px -> -90.0. From azimuth 175, drag right 20 px -> azimuth -175.0 (wrap into [-180, 180)).
B3. Zoom: one notch up (wheel vertical delta +120 inside the chart) -> zoom 1.1 (1e-9). One notch down
from there -> zoom 1.0. Twenty notches up from 1.0 -> zoom 4.0 exactly (clamp; not 1.1^20). Twenty
notches down from 1.0 -> zoom 0.25 exactly. Wheel outside the chart is not consumed by the region.
B4. Saved view: after B1 (az 60, el 40) and one zoom notch (zoom 1.1), saving writes `view_az` 60.0,
`view_el` 40.0 and `view_zoom` 1.1 on that region. Reopening draws the same `layout_surface` output
(equal cell list and box). A region that was never rotated or zoomed writes none of the three keys.
B5. Reset: the region context-menu entry "Reset 3-D view" removes the three keys; the next layout uses the
text `view` line, or 40/30 with zoom 1 when there is none.
B6. Precedence: with stored view (60, 40) and text `view 10 10`, the stored view wins. Editing the
`view` line to `view 20 15` and committing clears the stored keys; the layout then uses 20/15.
B7. Version: a sheet whose 3-D region has stored view keys is written with the same version number as
the same sheet with those keys removed (no new version). The developer must first confirm from the
region reader in `document.py` that unknown region keys are ignored. If the reader rejects unknown keys,
this rule is replaced by a version bump, and the manager decides that case before the developer continues.
B8. Redraw time (offscreen, `time.perf_counter`): `layout_surface` plus `paint_surface` for 25 x 25 under
50 ms; for 100 x 100 under 250 ms. Measured by the developer, re-measured by the tester.
B9. Drag preview: during a rotate drag with more than 40 cells per axis, `layout_surface` is called with
`mode="wire"`; on release, it is called with the region's `draw` mode. A 25 x 25 surface always uses its
`draw` mode during a drag.
B10. Real window (tester): rotate with the mouse on the A1-1 surface, zoom with the wheel, move the
region by its frame ring, save, reopen, reset the view, export PDF.

## Edge cases
- A grid of exactly two points per axis gives one cell per axis pair: `layout_surface` must still work.
- Descending sample values draw in the given order; limits come from the minimum and maximum.
- Using the same name for `over` and `across` is rejected by E1 (`over and across need different names`).
- A height that is complex (not NaN-free real) at some grid points counts as undefined (NaN) with the
  same rule as spec 004; it appears in `skipped`.
- Very large or very small magnitudes (1e-9 to 1e9) work with the nice-axis rule; tick labels use the
  existing formatter.
- A surface over a range variable that is also used in a table or 2-D plot above it works; one range
  feeds many plots.
- A `show` expression may call a user function of two arguments, for example `f(x, y)` with the two
  sample names, as a 2-D plot calls a one-argument function. A wrong argument count gives the existing
  error for user functions.
- Nested plot specs, plots inside plots, text regions mentioning `surface` are not special.
- Phase A does not push following regions down (backlog 20 still applies); a tall 3-D plot may overlap
  regions below it.
- The `view` line in phase A sets the view on every evaluation; there is no stored state yet.

---

## Phase C sketch (not for dispatch; each item needs its own spec, criteria and IP review)
- Parametric 3-D curve: `mode curve` with one `over` sample range and three expressions (coordinates
  along each axis). Drawn as a polyline with the same projection code.
- 3-D scatter: `mode scatter` with three equal-length vectors; drawn as dots.
- Several surfaces or curves in one plot, with a legend.
- Contour lines or colour bands by height (a separate feature on the same grid data).
- Perspective projection as an option (`perspective on`).
- Labelled-field dialog for 3-D plots (a follow-on to spec 006 for the 2-D dialog).
- PNG or SVG export of a single 3-D plot.
- Animation of a 3-D surface (see 016 section 4, backlog track H).

---

## IP check
Pass (manager review 2026-11-12, with the header keyword renamed from the former command name to
`surface`; no other change required). Concept-only use of generic material: surface plots of a height
over two variables; orthographic projection; painter's-algorithm depth ordering; flat shading by face
normal; drag-to-orbit and wheel-to-zoom, which is the general mouse convention of 3-D viewers. Each is
described here in our own words, with the public Wikipedia sources above used for naming and concept
only. No sentence was copied, and the CC BY-SA licence of those articles is not carried into our code
or text.

Syntax is our own: `surface`, `across`, `draw`, `view`, `zunit`, `zlim`, `zlabel`, and in phase B
`view_az`, `view_el`, `view_zoom`, with the 2-D keywords of spec 004 reused where they already exist. No
vendor keyword set, no vendor layout and no vendor 3-D UI was read or used. Nothing in phase A or B lets
the user type into the chart or any placeholder on the chart's axes; all editing stays in the plain text
region, and the mouse only changes the view of an already-computed picture. That is a different kind of
interaction from the inline placeholder editing rejected in spec 005. The manager confirmed this reading
for drag-to-orbit inside a chart, and Theo approved the phase B drag ownership on 2026-11-12.

Dependencies: none new. PySide6 (LGPL, dynamic use) provides QPainter. numpy (approved 2026-10-27) may
be used for the projection arithmetic and for vectorised evaluation. matplotlib is not used by the
project and is not proposed. QtDataVisualization and Qt Charts are excluded (GPL or commercial only, per
spec 016 section 2.2). Qt3D is LGPL-available but not recommended (016 section 2.3 reasoning:
rasterised, no vector PDF path, offscreen test risk). Not legal advice.

---

## Fits current architecture?
- `livesheet/engine/syntax.py`: new statement kind `surface` with `plot_lines`, recognised by the
  first-line rule; existing `plot` recognition unchanged.
- `livesheet/engine/surface.py` (new, Qt-free): `SurfaceData`, `build_surface`. Reuses `nice_axis` from
  `engine/plotting.py`, the `sampling.split_top` splitter, the `RangeVar` lookup and dimension-probing
  helpers from `evaluator.py`, and the measure/unit helpers from `units.py`. It follows the constant
  style of `plotting.py` (`DEFAULT_POINTS`/`MAX_POINTS` analogues for 25 and 100). A small helper shared
  with `plotting.py` (the `over` sub-grammar) may be factored out by the developer, as long as 2-D
  results stay unchanged.
- `livesheet/engine/evaluator.py`: dispatch of kind `surface` next to `plot`; `RegionResult.surface`
  (default None). A `surface` statement defines nothing.
- `livesheet/document.py`: phase A no change. Phase B: optional region keys `view_az`, `view_el`,
  `view_zoom`, present only on 3-D plot regions with a stored view. The developer must read the region
  reader and confirm unknown keys are ignored; the version rule in B7 follows from that.
- `livesheet/gui/surfaceview.py` (new, PySide6): `layout_surface` (pure), `paint_surface` (QPainter).
- `livesheet/gui/plotregion.py`: the region picks the surface path when its first line is `surface`;
  `is_surface_spec`; `engine_source` passes `surface` texts through; hint text for the empty 3-D spec;
  phase B: interaction handlers for the chart rectangle and the frame-ring move rule, and the context
  menu entry.
- `livesheet/gui/main_window.py` (and the worksheet's region factory, as for 2-D plots): `Insert > 3-D
  plot` creates the starter region without the 2-D dialog.
- Tests: `tests/test_surface.py` (A1, E-list), `tests/test_surface_gui.py` (A2, Qt parts may skip),
  `tests/test_surface_view.py` (B). The tester's real-window pass is part of A2-12 and B10.
- Threading/evaluation: unchanged. The surface is evaluated in the normal `Engine.evaluate` pass.

## Open questions (decided at manager review and by Theo, 2026-11-12)
1. Phase split: DECIDED. Phase A approved now; phase B approved too (see Q3/Q4); phase C only as separate specs.
2. Text-only editing: DECIDED. 3-D plots are text-only in A and B, with no dialog.
3. Saved view storage: DECIDED by Theo 2026-11-12. Store `view_az`, `view_el`, `view_zoom` as optional region
   fields, not by writing the orbit back into the `view` text line. Rule B7 still needs the developer's reader
   check (if the reader rejects unknown keys, the manager decides the version bump before continuing).
4. Drag ownership: DECIDED by Theo 2026-11-12. Inside a 3-D chart a drag rotates; the region moves from its
   frame ring. This is an exception to spec 023 for 3-D plot regions only.
5. Projection: DECIDED. Orthographic only in A and B; perspective later as an option.
6. Defaults: DECIDED. 25 points per axis, cap 100; default view azimuth 40, elevation 30; 0.5 degrees per pixel;
   1.1 per wheel notch; zoom range 0.25 to 4.
7. Clipping: DECIDED. A cell is dropped whole if any corner is outside a manual limit or undefined, so the edge at
   a limit is jagged.
8. Painter's order: DECIDED for A and B. Centroid depth sort; steep surfaces can show overlap artefacts; a
   grid-aware order is a possible follow-up.
9. Scope: DECIDED. One `show` per 3-D plot (one surface) in A and B; several surfaces in C.
10. Range variables as axes are allowed only with 100 values or fewer. Accepted.
11. gui-specialist was not reachable in earlier sessions (016, 009, 012). The manager may still want them to review
    the phase B mechanics (drag thresholds, cursor shape, context-menu wording) before B is dispatched. The phase A
    GUI parts do not depend on that.
12. Insert entry point: one menu entry `Insert > 3-D plot` in A, no canvas context-menu entry. Accepted.
