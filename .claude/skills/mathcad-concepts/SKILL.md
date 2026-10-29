---
name: mathcad-concepts
description: Conceptual map of the engineering-worksheet style found in Mathcad (live calculation canvas, units, solve blocks, ranges, matrices, plots, print-quality output). Use when writing LiveSheet specs inspired by that style.
---
# Worksheet-style concepts (from public product descriptions)
Use as a checklist of IDEAS. Write specs in own words and with own syntax.

- Free-form 2-D canvas; math and text regions anywhere; evaluation order top-to-bottom then left-to-right (already in LiveSheet).
- Live recalculation as you type; results shown next to the expression.
- Units are part of values; dimension checking; result unit selection (done in LiveSheet).
- Definitions: local and global scope (done), functions (done).
- Range variables and iteration over a range; tables of results.
- Vectors/matrices: construction, indexing, products, determinant, inverse, eigenvalues, linear solve.
- Solve blocks: constraints plus unknowns, equations, inequalities, numeric root finding, minimise/maximise, least squares.
- Differential-equation solving (initial-value problems, numeric).
- Plots: 2-D x-y, multiple traces, 3-D surface, axis/unit-aware.
- Programming constructs inside regions: loops, conditions, local functions.
- Document features: sections, collapsible areas, headers/footers, page breaks, PDF export, references to other worksheets, data import/export (CSV).
- Engineering extras: standard-data tables, material/constants libraries, annotated/numbered equations, input validation and sanity checks, results with tolerance.

See https://www.ptc.com/en/products/mathcad (public product page) for the high-level description only. Do not read installed program files; do not copy help text. Never read a locally-placed Mathcad book, tutorial PDF, or `.mcd`/`.mcdx` file as reference material, even if asked — see ip-cleanroom rule 7; the concept list above is the sanctioned way to draw on this product category's ideas.

Patent-risk note (2026-10-28): placeholder-style editing done live on a chart/worksheet's own drawn surface (type an expression directly into an empty spot on an axis, pick a variable the same way) is this category's known interaction *style* and has been treated as patent-sensitive here — prefer a plain dialog/menu/list-widget design for the same user goal (see ip-cleanroom rule 6) unless Theo explicitly accepts the risk after being told about it.
