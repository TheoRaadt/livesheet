# LiveSheet

A live math worksheet: place math and text anywhere on a page, and results update as you type.
Units are checked automatically, and you get symbolic algebra from [SymPy](https://www.sympy.org).
The GUI is built with [PySide6](https://doc.qt.io/qtforpython-6/) (Qt).

LiveSheet takes ideas from the worksheet style of tools like Mathcad. It uses its own syntax and file format,
and all of its code is original.

![status](https://img.shields.io/badge/status-early%20MVP-orange)

## Quick start (macOS / Linux)

```sh
git clone https://github.com/TheoRaadt/livesheet.git
cd livesheet
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
livesheet examples/demo.lsheet
```

Windows: use `.venv\Scripts\activate` instead of `source …`.

## How it works

Click anywhere to place the red cross, then start typing. Each math region holds one statement.
Regions are calculated **top to bottom, then left to right**, so moving a region can change the result.

| Type this | Meaning |
|---|---|
| `x := 5 m` | definition (typing `:` inserts `:=`) |
| `f(x, y) := x^2 + y` | function definition |
| `g ≡ 9.81 m/s^2` | global definition, visible everywhere (type `~` or `::`) |
| `x =` | numeric result, simplified to SI (`N`, `J`, `Pa`, …) |
| `v = km/hr` | numeric result in a unit you choose |
| `a := 2 m =` | define and show the value |
| `(x+1)^2 →` | symbolic result (type `->` or Ctrl+.) |
| `x^2 - 1 → factor` | symbolic keyword |
| `x^2 == 4 → solve, x` | equations use `==` |
| `"` | start a text region (Ctrl+Enter ends it, Ctrl+B/I/U for formatting) |

**Symbolic keywords:** `simplify`, `expand`, `factor`, `together`, `collect, x`, `partfrac, x`,
`solve, x`, `float, n`, `diff, x`, `integrate, x`, `series, x, n`, `substitute, x = 2`.
You can chain them: `expr → expand → factor`.

**Functions:** `sin cos tan asin acos atan atan2 sinh cosh tanh exp ln log` (base 10) `sqrt root abs floor ceil
mod Max Min factorial binomial re im conj arg diff integrate limit sum product solve`.

**Units:** `m km cm mm um inch ft mi`, `kg gm mg tonne lb`, `s ms min hr day yr`, `N kN MN lbf`,
`Pa kPa MPa GPa bar mbar atm psi`, `J kJ MJ Wh kWh MWh cal`, `W kW MW`, `A mA V kV ohm Ω C F uF Wb T H`,
`Hz kHz MHz rpm`, `K mol cd`, `L mL ha`, `rad deg`, and `g` (standard gravity).
Angles are dimensionless. If you define a variable with a unit's name (`s := 3`), your definition wins.

**Keys:** Enter ends a math region · Esc stops editing · double-click to edit · drag to move ·
Delete removes the selection · arrow keys move the cross or the selection · F9 recalculates ·
Ctrl+wheel zooms.

## Ranges and tables

| Type this | Meaning |
|---|---|
| `t := 0 s to 10 s step 2 s` | range variable (start, end, optional step; units must match) |
| `table t, v*t in m` | one row per range value; columns are expressions, optional `in UNIT` |

A range can only be used inside `table` for now. Limit: 10000 values.

## Vectors and matrices

| Type this | Meaning |
|---|---|
| `A := [1, 2; 3, 4]` | matrix literal (commas required; `;` starts a new row) |
| `A[1, 2]`, `A[1, :]`, `A[:, 2]` | 1-based indexing and slices |
| `A*B`, `A+B`, `A^2`, `k*A` | arithmetic, matrix product, integer powers |
| `det inv transpose trace dot cross hadamard eye zeros ones diag nrows ncols len` | functions |
| `solve_system(K, F)` | solve K x = F |

Entries keep their units, symbolic entries work with `→`. Matrices up to 10x10 show as an aligned grid,
larger ones as `[NxM matrix]`. Symbolic `det`/`inv`/`solve_system` are limited to 5x5.

## Solving numerically (models)

A model is a name. Regions tagged `in <name>` belong to it; the `settle`/`least`/`most` region below them solves it.

```
vary t from 1 s in fall            unknowns with start values (units come from the start value)
g*t^2/2 == h in fall               equation (also <=, >=, <, >, and a <= x <= b)
accuracy 1e-9 in fall              optional settings (accuracy, steps)
settle in fall                     => t = 2.01962 s
least  w*d in fit / most w*d in fit   minimise / maximise an objective
```

Constraint regions show a check mark when satisfied, a cross on the worst violation.
Local optima only. Uses SciPy (imported on first use).

## Files

Worksheets are saved as `.lsheet` files. These are readable JSON, so they work well with git diffs.
**File → Export PDF** renders the sheet to A4 pages.

## Project layout

```
livesheet/
  engine/       GUI-independent calculation engine
    syntax.py      statement parsing (:=, ≡, =, →)
    evaluator.py   evaluation order, namespaces, symbolic keywords
    units.py       unit namespace and dimension checking
    formatting.py  number/expression output, tables and matrix grids
    matrices.py    matrix literals, indexing, linear algebra
    solver.py      numeric solve models (vary/settle/least/most)
  gui/          PySide6 front end (canvas, regions, main window)
  document.py   .lsheet file format
docs/           PLAN, IP-POLICY, agent board (specs, reviews, backlog, decisions)
.claude/        agent and skill definitions (clean-room team)
tests/          pytest suite (GUI tests run headless)
examples/       demo worksheet
```

Run the tests with:

```sh
QT_QPA_PLATFORM=offscreen pytest
```

## Roadmap

See docs/board/backlog.md. Next: undo/redo, 2-D plots, push-down layout for tall results, eigenvalues/rank/least squares (002b),
temperature units, real 2-D math typesetting.

## License

Dual-licensed under either the MIT license ([LICENSE-MIT](LICENSE-MIT)) or the Apache License 2.0 ([LICENSE-APACHE](LICENSE-APACHE)), at your option.
