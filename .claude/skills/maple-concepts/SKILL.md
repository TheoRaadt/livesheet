---
name: maple-concepts
description: Conceptual map of Maple's usability and education-oriented features (document mode, 2-D math input, context-sensitive operations, tutors, exact plus float arithmetic, procedures, interactive components). Use when writing LiveSheet specs for usability and learning workflows.
---
# Maple-style concepts (from public product descriptions)
IDEAS only. Use own names.

- Two work styles: free "document" with math and text mixed, and a command-oriented worksheet. LiveSheet is canvas-first; consider an optional linear command region.
- 2-D math input with typeset output; click an expression, get a context menu of valid operations (simplify, solve for, differentiate, plot) with the result inserted.
- Exact arithmetic by default (rationals, radicals) with explicit conversion to floating point; control over digits.
- Domain packages as toggles: physics/vector calculus, statistics, linear algebra, units. Idea: LiveSheet "toolboxes" loaded on demand.
- Tutors / assistants: guided dialogs for common tasks (solve an ODE, fit a curve, change of variable).
- Embedded interactive components: sliders, buttons, plots linked to variables.
- Procedures with local variables and control flow; a way to define reusable routines.
- Plotting with interactive rotate/zoom and animation.
- Task templates: ready-made starting calculations by topic.
- Exporting: PDF, HTML, and code generation to other languages (idea: export to Python/C).

Public overview: https://www.maplesoft.com/products/maple/ . Do not copy package/command names as compatibility layer, docs, or examples.
