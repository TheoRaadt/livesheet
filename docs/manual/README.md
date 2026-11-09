# LiveSheet manual

LiveSheet is a free-form worksheet: you place regions (math, text, plots, matrices, components)
anywhere on the page and LiveSheet keeps everything recalculated as you type, left to right and
then top to bottom (page by page, if you split the sheet with page breaks).

This manual is written from the features actually shipped in LiveSheet, in LiveSheet's own words.
It grows as features ship; a page only appears here once a feature is finished and checked.

## Pages

- [Plots](plots.md) — inserting and editing a chart with the Plot dialog: picking what to plot,
  which variable to run it over, axis limits and units, titles and labels.
- [The main window](main-window.md) — the toolbar (larger icon-and-label buttons, picture-only and
  overflow chevron on narrow windows), the window-wide ten-tab strip that wraps onto more rows
  when narrow, and its button band (Elements, Algebra, Calculus, the formula tabs, and placeholders
  for Statistics/Optimization/Outline/Data), keyboard use, typing Greek letters and
  subscripts, the status bar, and switching between a light, dark or system-following appearance.
- [Vectors and matrices](matrices.md) — building a vector or matrix with the Matrix dialog instead
  of typing brackets by hand, and editing one you already have.
- [Components and wiring](components.md) — placing small self-contained calculation blocks on the
  sheet and connecting them with wires instead of writing one long formula.
- [Differential equations](odes.md) — writing one or more `ode`/`start`/`over` tagged regions and
  getting an exact or numeric `evolve` answer, usable afterward as a function, in a table, or in a
  plot.
- [Truss analysis](truss.md) — describing a 2D pin-jointed truss with `nodes`/`elements`/`area`/
  `modulus`/`support`/`load` tagged regions and getting node displacements, support reactions, and
  each bar's force and stress from a `resolve` line.
- [CAD profile import (DXF)](cad-profiles.md) — pointing a "CAD profile (DXF)" component at a
  `.dxf` cross-section drawing (straight, curved, chained-line, or hollow/composite outlines) and
  getting its area, centroid, second moments and section moduli as wireable numbers.
- [Pages and page breaks](pages.md) - the order LiveSheet calculates your regions in, splitting
  the sheet into A4 pages with Insert > Page Break, and how Export PDF treats those pages.
- [Formula tabs: Mechanical, Electrical, Chemical](formula-tabs.md) - inserting ready-made SI
  engineering formulas (47 buttons) from the tab strip, filling in and renaming their names,
  showing results in the unit you want, and why an undefined unit-named variable such as `F` or `A`
  now gives "is not defined" (including the `g` = standard gravity trap).
- [Statistics](statistics.md) - mean, median, mode, sample and population variance/standard
  deviation, quantiles, covariance and correlation of a list of measurements; normal, uniform,
  binomial and Poisson distribution functions; seeded random samples; and hypothesis tests
  (one-sample t, Welch two-sample t, chi-square fit) with `sample`/`claim`/`level`/`verdict` lines;
  and regression (`fit_linear`, `fit_poly`, `predict`, `r_squared`) to fit a line or polynomial
  through paired data.
- [Moving regions](moving-regions.md) - dragging regions (click then drag, grabbing the frame
  while editing, moving a group), grid snapping, Esc to cancel, arrow-key and Shift+arrow nudging,
  and how a move changes the calculation order.
- [Error messages](errors.md) — every message LiveSheet can show you while using the features
  above, grouped by area, with what causes it and how to fix it.
