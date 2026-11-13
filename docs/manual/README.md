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
  when narrow, and its button band (Elements, Algebra, Calculus, Statistics, Optimization, the
  formula tabs, the Outline tab that lists bold headings and jumps to them, and the Data
  tab for imported datasets), keyboard use, typing Greek letters and
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
- [Optimization](optimization.md) - solving equations and finding a smallest or largest value with
  `vary`/`settle`/`least`/`most` lines, and the Optimization tab's template buttons.
- [Moving regions](moving-regions.md) - dragging regions (click then drag, grabbing the frame
  while editing, moving a group), grid snapping, Esc to cancel, arrow-key and Shift+arrow nudging,
  and how a move changes the calculation order.
- [Autocomplete](autocomplete.md) - the name list that opens after two typed letters in a math
  region (built-in functions, constants, your own names and imported-data names, with call hints), Down/Up to move, Tab
  to accept, Esc to dismiss, and how it interacts with the Greek-letter buttons.
- [Importing data](data-import.md) - Insert > Data from file...: bringing a CSV file into the sheet
  as a dataset (delimiter, decimal mark, header, units like `name [unit]`), using its columns such
  as `run1_t` in `mean`, `fit_linear` and plots, the Data tab (Import, Refresh, Rename, Remove),
  saving data inside the sheet (file format 5), and the limits.
- [3-D surface plots](surface-plots.md) - Insert > 3-D plot, the `surface` text lines (`over`,
  `across`, `show`, `draw`, `view`, units and limits), dragging to rotate, the wheel to zoom,
  moving the region by its frame, and Reset 3-D view.
- [LaTeX formulas in text regions](latex-text.md) - writing `$...$` and `$$...$$` formulas in a text
  region, the Insert > Formula items and shortcuts, the View > Typeset LaTeX switch, the supported
  commands, and what a wrong formula looks like.
- [Mechanical engineering functions](mechanical-library.md) - 28 ready-made functions for cross
  sections, beam deflection and moments, stress and strain, and Euler columns, with strict units
  and SI results.
- [Electrical engineering functions](electrical-library.md) - 17 ready-made functions for resistor
  networks, RMS and peak, AC power, three-phase and transformers, the new units mH, uH, nH, pF, VA
  and var, and the zero-result and `0 ohm` limits.
- [Error messages](errors.md) — every message LiveSheet can show you while using the features
  above, grouped by area, with what causes it and how to fix it.
