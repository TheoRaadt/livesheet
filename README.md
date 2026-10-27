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
    formatting.py  number/expression output
  gui/          PySide6 front end (canvas, regions, main window)
  document.py   .lsheet file format
tests/          pytest suite (GUI tests run headless)
examples/       demo worksheet
```

Run the tests with:

```sh
QT_QPA_PLATFORM=offscreen pytest
```

## Roadmap

- Undo/redo for region operations
- Range variables and vectors/matrices (`i := 0..10`, `[1, 2; 3, 4]`)
- 2-D plot regions
- Real 2-D math typesetting (fractions, roots, integrals)
- Solve blocks (`given … find`)
- Temperature units with offsets (°C, °F)

## License

Dual-licensed under either the MIT license ([LICENSE-MIT](LICENSE-MIT)) or the Apache License 2.0 ([LICENSE-APACHE](LICENSE-APACHE)), at your option.
