---
name: mathematica-concepts
description: Conceptual map of the symbolic-computation and notebook paradigm found in Mathematica. Use when writing LiveSheet specs for CAS depth, rules and pattern matching, list processing and interactive controls.
---
# Symbolic and notebook concepts (from public product descriptions)
IDEAS only. Use own names for everything.

- Everything is an expression tree; symbolic first, numeric on demand; arbitrary-precision numerics with tracked precision.
- Rewrite rules and pattern matching: user-defined simplification rules (SymPy has `replace`, `Wild`, `match`).
- Functional style: map, fold, apply, pure (anonymous) functions over lists.
- Lists as the central data structure; tables generated from formulas; vectorised operations.
- Symbolic calculus and solving: differentiate, integrate, limits, series, algebraic and differential equations, assumptions on variables (real, positive, integer).
- Notebook structure: cells (input, output, text, section), grouping and outline; re-evaluation of cells.
- Dynamic/interactive controls: sliders bound to variables with instant re-render.
- Plot variety: function, parametric, contour, density, 3-D; automatic plot ranges.
- Built-in knowledge data (constants, units, curated datasets) as lookup.
- Step-by-step explanation of a result is NOT their core idea; treat as a separate LiveSheet feature if wanted.

Public overview: https://www.wolfram.com/mathematica/ . Do not copy function names as compatibility layer, docs, or examples.
