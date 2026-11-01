# Truss analysis (nodes / elements / support / load / resolve)

This feature lets you describe a 2D pin-jointed truss — a structure built entirely out of
straight bars connecting pin joints, like a bridge truss or a roof truss — directly on the
sheet, and ask LiveSheet to work out how it deflects and what force runs through each bar.
You give it the joint ("node") positions, which nodes each bar ("element") connects, each
bar's cross-section and material, which nodes are supported, and which nodes carry a load.
LiveSheet assembles the structure, solves it, and binds the node displacements, the support
reactions, and each bar's force and stress by name, so you can use them in any later
expression, table or plot exactly like any other worksheet result.

This is a 2D analysis: every node has an x and a y position, every bar only carries axial
load (push/pull along its own length, no bending), and every joint is a pin (it can't
transmit a twisting moment into a bar).

## How the pieces fit together

A truss problem needs several pieces of information that don't fit on one line: the node
positions, the bar connectivity, each bar's area and modulus, the supports, the loads, and a
trigger that solves the structure. LiveSheet handles this the same way it handles any other
multi-line calculation on a free-form sheet: you write each piece as its own one-line region,
anywhere on the canvas, and tag every region that belongs together with a trailing
`in <name>`. LiveSheet collects every region sharing the same tag, in calculation order (left
to right, then top to bottom, page by page; see [Pages and page breaks](pages.md)), and solves them together once it reaches a dedicated result
line for that tag, `resolve`. You can mix tagged regions for different problems freely on the
same sheet — only the shared tag name groups them, and a region below `resolve` is not used
for that solve.

For a truss model, the tagged region kinds are `nodes`, `elements`, `area`, `modulus`,
`support` (any number), `load` (any number), and the result line, `resolve`.

## Node positions and bar connectivity

Node positions and bar connectivity are nothing new — they're ordinary matrices, written
exactly the way you already write any other vector or matrix on the sheet:

```
coords := [0, 0; 4, 0; 2, 3] m
members := [1, 3; 2, 3]

nodes coords in bracket
elements members in bracket
```

`coords` has one row per node, in a length unit, columns `(x, y)` — row 1 is node 1, row 2 is
node 2, and so on. `members` has one row per bar, columns the 1-based numbers of the two
nodes it connects — row 1 is bar ("element") 1, row 2 is bar 2. You can write the matrix as a
literal, like above, or build it any other way LiveSheet already lets you build a matrix.

A `nodes` line and an `elements` line are each required exactly once per model.

## Cross-section and material: area and modulus

```
area 0.0005 m^2 in bracket
modulus 200 GPa in bracket
```

`area` is each bar's cross-section area, in an area unit; `modulus` is each bar's elastic
modulus (how stiff the material is, often called `E`), in a pressure unit. Both are required
exactly once per model. Each can be a single value, applied to every bar, or a list with one
value per bar (in the same row order as `elements`) when your bars aren't all the same.

## Supports

```
support 1 fix x, y in bracket
support 2 fix x in bracket
```

A `support` line pins one or more directions of movement at one node. `<node>` is the node
number; after `fix`, list `x` and/or `y` (comma-separated) for the directions that can't move
at all, or `x = <value>`/`y = <value>` (a length) for a direction that moves a known, fixed
amount instead of staying put — a known support settlement. You can write any number of
`support` lines; fixing the same node and direction twice (even across two different lines)
is an error.

A structure with no supports at all (or not enough to stop it moving or rotating freely)
can't be solved — see [Error messages](errors.md#truss-analysis).

## Loads

```
load 3 fy -10000 N in bracket
```

A `load` line applies a concentrated force at one node. `<node>` is the node number; after
it, give `fx <expr>` and/or `fy <expr>` (either order, comma-separated for both), each a
force. At least one of `fx`/`fy` is required. You can write any number of `load` lines for
different nodes, but giving the same node on two different `load` lines is an error — combine
everything for that node into one line instead.

A node with no `load` line simply carries no applied force (not an error).

## Solving: resolve

```
resolve in bracket
```

Write one `resolve` line below every `nodes`/`elements`/`area`/`modulus`/`support`/`load`
region of a tag (same rule as everywhere else on the sheet: a region only sees tagged regions
calculated before it: further left, or in the same column higher up, on the same page or an
earlier one). `resolve` takes no expression — just the tag. Any text
after the word `resolve` is an error.

`resolve`'s own result line reports the size of the structure and the largest displacement
found anywhere in it:

```
⇒ resolved "bracket": 3 nodes, 2 elements; max |displacement| = 0.00026 m
```

and binds four results by name, derived from the model's own tag:

| Name | Shape | Contents | Unit |
|---|---|---|---|
| `<name>_displacement` | one row per node, columns `(ux, uy)` | how far each node moved | length |
| `<name>_reaction` | one row per node, columns `(x, y)` | the support force needed at each node (0 at every node that isn't supported in that direction) | force |
| `<name>_force` | one row per bar | each bar's own axial force, positive = tension (pulling the bar apart), negative = compression (pushing it together) | force |
| `<name>_stress` | one row per bar | each bar's own axial stress (force divided by its area) | pressure |

These are ordinary matrices — print one with `=`, index into it, put it in a `table`, or plot
it, exactly like any other matrix result on the sheet. `resolve` itself only prints the one
summary line above; the four matrices are where the full detail lives.

A support or free node's reaction is computed from the whole solved structure, so in
practice you may see a tiny nonzero number (far below any unit you'd ever care about, e.g.
`1e-13 N`) at a free node's reaction instead of a mathematically perfect `0` — that's ordinary
floating-point rounding from the numeric solve, not a sign that something is actually being
held there.

## Worked example: a single axially-loaded bar

A single bar, 2 metres long, pinned at both ends, fixed so it can't move at all on the left
and can't move sideways on the right, pulled by 1000 N at the free end:

```
coords := [0, 0; 2, 0] m
members := [1, 2]

nodes coords in bar
elements members in bar
area 0.0005 m^2 in bar
modulus 200 GPa in bar
support 1 fix x, y in bar
support 2 fix y in bar
load 2 fx 1000 N in bar
resolve in bar
```

The result line reads:

```
⇒ resolved "bar": 2 nodes, 1 elements; max |displacement| = 2e-05 m
```

and the four bound matrices:

```
bar_displacement =    ->  = [0, 0; 2e-05, 0] m
bar_force =            ->  = [1000] N
bar_stress =            ->  = [2000000] Pa
bar_reaction =          ->  = [-1000, 0; 0, 0] N
```

Node 2 moves `2e-05 m` to the right (`F*L/(E*A) = 1000*2/(200e9*0.0005)`); the bar carries
`1000 N` of tension; its stress is `1000 N / 0.0005 m^2 = 2000000 Pa`; node 1's x-reaction
(`-1000 N`) exactly balances the applied load.

Reverse the load (`load 2 fx -1000 N in bar`) and the bar goes into compression instead:
`bar_force =` gives `= [-1000] N`, `bar_displacement =` gives `= [0, 0; -2e-05, 0] m`.

## Worked example: a two-bar bracket

Two bars meeting at a point, each pinned to its own fixed support, carrying a downward load
at the point where they meet — like the two legs of an A-frame:

```
coords := [0, 0; 4, 0; 2, 3] m
members := [1, 3; 2, 3]

nodes coords in bracket
elements members in bracket
area 0.0005 m^2 in bracket
modulus 200 GPa in bracket
support 1 fix x, y in bracket
support 2 fix x, y in bracket
load 3 fy -10000 N in bracket
resolve in bracket
```

```
⇒ resolved "bracket": 3 nodes, 2 elements; max |displacement| = 0.00026 m

bracket_displacement =  ->  = [0, 0; 0, 0; 0, -0.000260401] m
bracket_force =          ->  = [-6009.25; -6009.25] N
bracket_stress =          ->  = [-12018500; -12018500] Pa
bracket_reaction =        ->  = [3333.33, 5000; -3333.33, 5000; 0, 0] N
```

The load point (node 3) drops `0.000260401 m`, straight down (its `ux` is exactly 0, by the
left-right symmetry of the shape); both bars carry the same `-6009.25 N` (compression — the
two bars act like the legs of an A-frame being pushed outward and down by the load) and the
same `-12018500 Pa` stress. The two supports' reactions add up to carry the whole `10000 N`
load between them (`5000 + 5000 = 10000`) with their sideways pulls cancelling out
(`3333.33 - 3333.33 = 0`), and node 3 itself — the unsupported node — has zero reaction.

Printed afterward in different units, the same values convert the usual way:

```
bracket_displacement = mm   ->  = [0, 0; 0, 0; 0, -0.260401] mm
bracket_force = kN           ->  = [-6.00925; -6.00925] kN
bracket_stress = MPa         ->  = [-12.0185; -12.0185] MPa
```

## Units

Every quantity keeps its own unit through the whole computation, the same way any other
dimensioned calculation on the sheet does. `nodes` fixes the length unit used for positions
and for displacements; `area` must be an area; `modulus` must be a pressure (an elastic
modulus); a `load`'s `fx`/`fy` must be a force; a `support`'s prescribed value (the
`x = <value>` form) must be a length. Mixing units that are dimensionally consistent is fine
(e.g. `nodes` in metres with a `support` value in millimetres) — the usual unit conversion
applies. Giving a quantity in the wrong kind of unit altogether (a length where an area is
expected, say) is a "Units do not match" error — see
[Error messages](errors.md#truss-analysis).

## A note on numeric-only results

`resolve` always solves the structure numerically, even if every number you typed happens to
be an exact, round value. There's no exact/symbolic truss result — unlike a plain matrix,
where printing with `->` can give you an exact fraction instead of a decimal, a truss's four
bound results are always decimal numbers.

There's also no `accuracy` or `steps` setting for a truss model (unlike differential
equations, see [Differential equations](odes.md)) — a truss is solved with one direct linear
solve, not an iteration, so there's nothing for a tolerance or a step budget to mean. Writing
`accuracy`/`steps` on a truss-only tag is accepted and simply has no effect.

## Errors

See [Error messages](errors.md#truss-analysis) for the exact wording of every message this
feature can show you, what causes it, and how to fix it.
