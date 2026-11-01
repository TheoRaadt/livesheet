# 015 Finite Element Method, phase F1: 2D pin-jointed truss analysis

Source inspiration (concept only, nothing copied):
- Backlog items 36/B (the feasibility research note, `docs/board/specs/012-cad-import-and-fem-research.md`, Part B) and the concept checklist in `.claude/skills/mathcad-concepts` ("engineering extras", generic worksheet-category ideas). This spec does the one thing the research explicitly flagged as needing a mathcad-specialist pass: the user-facing syntax/workflow for defining and solving a truss on the sheet. The underlying engineering method is unchanged from the research note's own conclusions; nothing below is a new technical finding.
- Wikipedia, "Direct stiffness method" (https://en.wikipedia.org/wiki/Direct_stiffness_method), accessed 2026-10-30 — the generic, textbook-standard name for the truss-element assembly/solve technique used here (also the research note's own primary source, B.2). Independently re-confirmed for this spec: a 2D truss (bar) element's local axial stiffness `(EA/L)*[[1,-1],[-1,1]]` is transformed into the global 4x4 element stiffness via `K_global = Tᵀ k T`, where `T` maps the two global-DOF-pairs at the element's end nodes onto the element's own axis using its direction cosines `(c, s) = ((x_j-x_i)/L, (y_j-y_i)/L)`; expanding this product gives the well-known pattern built from `c²`, `cs`, `s²` blocks. This is centuries-old statics plus a mechanical, generic linear-algebra transformation — not any one software vendor's technique.
- TU Delft / UBC / Jönköping University open course notes, and SciPy's own `scipy.sparse.linalg`/`numpy.linalg.solve` public documentation — all already cited with URLs and access dates in `docs/board/specs/012-cad-import-and-fem-research.md` (B.2, B.3); re-cited here by reference rather than re-quoted, per the ip-cleanroom skill's "no quotes beyond a few words" rule.
- No named commercial or open FEM package's documentation, GUI, workflow, help text or branding was read for this spec (ANSYS, Abaqus, COMSOL, NASTRAN, SolidWorks Simulation, CalculiX, FEniCS, or any other), per the manager's explicit instruction for this feature and the research note's own clean-room boundary (012 §B.1), which this spec continues unchanged.
- Everything below (keyword names, syntax, result-binding convention, output text, error texts) is LiveSheet's own design.

## User story
As a mechanical/structural engineer I type in a handful of node coordinates and the
members connecting them (which I already know how to write today as ordinary
vectors/matrices, spec 002), say which nodes are supported and where loads are
applied, and ask the sheet to resolve the truss — and I get nodal displacements,
member forces and stresses bound by name, so I can use them in later expressions,
tables or plots exactly like any other worksheet result, without leaving the sheet
or hand-assembling a stiffness matrix myself.

## Behaviour (own words)

### Why this reuses spec 003's tag idiom, not a new mechanism
A truss problem needs several pieces of data that belong together and must be
collected before anything can be computed: node coordinates, element connectivity
plus each element's section/material data, zero or more supports, zero or more
loads, and a trigger that does the assembly/solve and reports results. This is
exactly the shape spec 003 ("solve blocks") already solved for algebraic systems,
and spec 010 ("ODE solving") reused unchanged for differential systems: independent
single-statement regions, anywhere on the canvas, joined only by a shared
`in <name>` tag and collected in reading order; a dedicated result line triggers the
computation and binds the answer by name. This spec extends the same `_parse_model`
tag idiom and `Engine._run_model` bookkeeping with new leading keywords, rather than
inventing a third parallel grouping mechanism — the research note itself raised this
exact question (012 §B.8.2) without making the call; this spec makes it: reuse,
for the same reasons spec 010 already gave (one proven, already-reviewed mechanism
for "a named group of tagged regions, solved on demand," not three).

What this spec deliberately does **not** reuse from spec 003/010: `accuracy` and
`steps`. A truss's reduced stiffness system is solved by one direct linear solve
(`numpy.linalg.solve`, per the research note's own B.3/B.5 recommendation for the
tiny first-slice mesh sizes) — there is no iteration and therefore nothing for a
tolerance or a step budget to mean. A near-singular/unconstrained structure is
reported as its own error (see Errors) instead.

### The node/element data itself is just today's existing matrix literals
Per the research note's own sequencing recommendation (012 §B.4), node coordinates
and element connectivity are **not** new syntax at all — they are ordinary matrix
values the user already knows how to write (spec 002), typically defined above the
tagged lines and referenced by name, exactly like spec 003's `h := 20 m` or spec
010's `tau := 4 s`:
```
coords := [0, 0; 4, 0; 2, 3] m
members := [1, 3; 2, 3]
```
`coords` is an Nx2 matrix, one row per node (row number = node number, 1-based, the
same convention spec 002's own indexing already uses), columns `(x, y)`. `members`
is an Mx2 matrix, one row per element, columns the 1-based indices of the two nodes
it connects (row number = element number). Nothing about spec 002's matrix literal,
indexing or unit rules changes; a `coords`/`members` matrix can be written as a
literal, built with a function, or (later, optionally — not this spec) fed by a
wire from some other component. No dependency on backlog 35 (DXF import) for this
slice, confirming the research note's own B.4 conclusion.

### The tagged lines themselves (new, five declaration kinds plus one result kind)
Each line below ends with the usual ` in <name>` tag (spec 003's grammar, unchanged)
and is otherwise an ordinary math region, placed anywhere, in any order, possibly
interleaved with unrelated regions:

1. `nodes <expr> in <name>` — `<expr>` must evaluate to an Nx2 matrix of node
   coordinates with a length unit (homogeneous, per spec 002's own matrix-unit
   rules). Exactly one such line per model.
2. `elements <expr> in <name>` — `<expr>` must evaluate to an Mx2 matrix of 1-based
   node indices (dimensionless integers). Exactly one such line per model. Row `k`
   of `elements` is "element `k`" throughout the rest of this spec.
3. `area <expr> in <name>` — `<expr>` evaluates to either one scalar area (applied
   to every element) or an Mx1 vector (one area per element, in `elements`' own row
   order), with an area unit. Exactly one such line per model.
4. `modulus <expr> in <name>` — same shape as `area` (scalar broadcast or Mx1
   vector), with a pressure/stress unit (Young's modulus `E`). Exactly one such
   line per model.
5. `support <node> fix <axis>[, <axis>] in <name>` — `<node>` is any scalar
   expression giving a 1-based node index (same "any expression that evaluates to
   an integer" rule spec 002's indexing already uses). Each `<axis>` is `x`, `y`,
   `x = <expr>`, or `y = <expr>` — the bare form prescribes a zero displacement
   (a "fixed"/"pinned"/"roller" support, in the research note's own words, 012
   §B.2.5); the `= <expr>` form prescribes any value with a length unit (a known
   support settlement/displacement — the generic case the same DOF-elimination
   technique handles for free, per 012 §B.2.5, not a new algorithm). Any number of
   `support` lines per model, one node and one axis per `fix` item; the same node
   and axis combination given twice (even across different lines) is an error.
6. `load <node> fx <expr>[, fy <expr>] in <name>` (or `fy` first, either order) —
   a concentrated nodal load at `<node>`, components with a force unit. At least
   one of `fx`/`fy` must be given; any number of `load` lines per model, but the
   same node given in two different `load` lines is an error (combine into one
   line instead — kept simple on purpose, no implicit summation).
7. `resolve in <name>` — the result line (parallel to spec 003's `settle` / spec
   010's `evolve`): assembles the global stiffness matrix from `nodes`/`elements`/
   `area`/`modulus`, applies DOF elimination for every `support`, applies every
   `load`, solves, and reports (see Results below). Takes no expression, like
   `settle`.

Everything else about scoping/ordering is identical to spec 003/010: all data for
one `resolve` comes from the model's own tagged regions that are **earlier in
reading order** than the `resolve` region itself; a tagged region below `resolve`
is not used; other variables (`area`, node/element matrices, units) are read from
the environment at the position of the `resolve` region, same reading-order rule
as everywhere else on the sheet.

### What `resolve in <name>` computes and binds
Standard direct stiffness method (012 §B.2, generic, decades-old technique, not
re-derived here beyond the one independently-confirmed formula in the Source
inspiration section above):
1. Build each element's 4x4 global stiffness matrix from its own `(E, A, L, c, s)`
   and scatter-add it into the global stiffness matrix, indexed by its two nodes'
   global DOF numbers (`2*node-1` = that node's x-DOF, `2*node` = its y-DOF, 1-based
   throughout, consistent with every other 1-based index in this project).
2. Partition DOFs into free and prescribed (every DOF not named by a `support` line
   is free, with its load — 0 if no `load` line gave one); eliminate the prescribed
   DOFs (moving their, generally non-zero, contribution to the right-hand side);
   solve the free-free system for the free DOFs' displacements with
   `numpy.linalg.solve`.
3. Recover every element's elongation along its own axis from its two end nodes'
   now-known displacements, its axial force (`(EA/L)*elongation`, tension positive)
   and its axial stress (`force/area`).
4. Recover reaction forces at every prescribed DOF from the full stiffness matrix
   and the full displacement vector (standard DOF-elimination post-processing, 012
   §B.2.5); every free DOF's "reaction" is exactly 0 by construction (its own
   equilibrium was the thing just solved for).

Binding (own convention, not vendor-copied — see IP check item 3): four matrices
are bound under names derived from the model's own tag, the one name the user
chose, the same "bind what was solved for, by name" spirit as spec 003's unknowns
and spec 010's functions, extended to the case where there is no single
user-chosen name per result value:
- `<name>_displacement`: Nx2 matrix, row = node, columns `(ux, uy)`, length unit.
- `<name>_reaction`: Nx2 matrix, same layout, force unit (0 at every free DOF).
- `<name>_force`: Mx1 vector, row = element, axial force, force unit, tension
  positive (matching the sign convention `area`/`modulus` already use row-wise).
- `<name>_stress`: Mx1 vector, same layout, pressure unit.
All four are ordinary matrix/vector values (spec 002), usable immediately in any
later expression, `table`, or (spec 004) `plot` region exactly like any other bound
matrix — printing one, e.g. `truss1_displacement =`, uses spec 002's existing
matrix-result formatting unchanged.

Output text of the `resolve` region itself (one summary line, exact prefix is the
contract, the rest uses the existing number-formatting path):
`"⇒ resolved "<name>": <N> nodes, <M> elements; max |displacement| = <value> <unit>"`
(`<value> <unit>` is the largest `(ux² + uy²)^0.5` over all nodes, formatted via the
existing `format_number`/SI-coherent path, same convention spec 003/010's own result
lines already use). Nothing else is auto-printed; the four bound matrices are how
the user gets the full detail, by design (matches spec 003's own choice not to
auto-print every intermediate value).

### Units
Every quantity keeps its own unit through the whole computation, the same way
spec 002's matrix arithmetic and spec 003's solver already do — nothing is
stripped to bare SI numbers by this spec's own code beyond what `units.measure`
already does for any other dimensioned computation on this project. `nodes` fixes
the length unit; `area` an area unit; `modulus` a pressure unit; `load` components
a force unit; a `support`'s prescribed value (when given) a length unit. Mixing
e.g. `nodes` in metres with a `support` value in millimetres is fine (ordinary unit
conversion, as everywhere else); mixing a length where an area is required is the
"Units do not match" family of error below. Bound results are SI-coherent, the same
convention `solve_system`/`settle`/`evolve` already use.

## Syntax proposal (own keywords) and grammar change
Worked examples (each line one region; blank lines only for readability here, not
required on the sheet):
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
resolve in bracket                 -> ⇒ resolved "bracket": 3 nodes, 2 elements; max |displacement| = 0.00026 m

bracket_displacement =             -> = [0, 0; 0, 0; 0, -0.000260401] m
bracket_force =                    -> = [-6009.25; -6009.25] N
bracket_stress =                   -> = [-12018500; -12018500] Pa
bracket_reaction =                 -> = [3333.33, 5000; -3333.33, 5000; 0, 0] N
```
Grammar change (`engine/syntax.py`): extend the existing `_parse_model` dispatcher
(already trying `vary`/`settle`/`least`/`most`/`accuracy`/`steps`/`ode`/`start`/
`over`/`evolve` in order, specs 003/010) with six more leading keywords. `Statement`
gains two more optional fields (additive only, no existing field or caller
affected, same pattern specs 010/004 already used for their own additions):
`node: str` (the node-index expression text, used by `model_support`/`model_load`)
and `axes: list[tuple[str, str]]` (one `(axis_letter, value_text_or_empty)` pair
per `fix`/`fx`/`fy` item — empty value text means "prescribe zero", used by both
new kinds so a `support`'s bare `x` and a `load`'s `fx <expr>` share one field and
one small shared parsing helper).
- `nodes <expr> in <name>` / `elements <expr> in <name>` / `area <expr> in <name>` /
  `modulus <expr> in <name>` → kinds `model_truss_nodes` / `model_truss_elements` /
  `model_truss_area` / `model_truss_modulus`, `model=name`, `expr=<text>` (deferred-
  parse, exactly like `model_ode`'s equation text — re-parsed as an ordinary
  expression only when `resolve` runs, not at statement-parse time).
- `support <node-expr> fix <item>[, <item>]* in <name>` → kind `model_support`,
  `model=name`, `node=<node-expr text>`, `axes=[(axis, value_or_"")...]`; a small
  dedicated regex splits the leading node-expression text from the literal word
  `fix` (non-greedy, same style as the existing `_MODEL_TAG_RE`/`_parse_guesses`
  patterns), then each comma-separated item must match `^(x|y)(?:\s*=\s*(.+))?$`
  or raise `'Use "support <node> fix x, y" (optionally "x = <value>")'`.
- `load <node-expr> (fx|fy) <expr>[, (fx|fy) <expr>] in <name>` → kind
  `model_load`, same `node`/`axes` shape (axis letter `x`/`y` taken from `fx`/`fy`,
  value text always required here, unlike `support`); a non-matching item raises
  `'Use "load <node> fx <value>, fy <value>" (either or both)'`; the same axis
  given twice in one line's own item list is a parse-time error
  `'"fx"/"fy" given twice on one load line'`.
- `resolve in <name>` → reuses the existing `model_result` kind, `goal="truss"`
  (parallel to `goal="root"` for `settle` and `goal="ode_auto"` for `evolve`); any
  trailing text after `resolve` is an error `"resolve takes no expression"` (same
  wording style as `settle takes no expression`).
No other existing statement form changes meaning; a sheet with no `nodes`/
`elements`/`area`/`modulus`/`support`/`load`/`resolve` region is unaffected (same
backward-compatibility guarantee specs 003/010 already give for their own tags).
`accuracy`/`steps` keep meaning exactly what they already mean for spec 003/010's
models; a truss model simply never uses them (no new keyword clash to worry about,
since truss models don't declare them — using `accuracy 1e-6 in bracket` on a
truss-only tag is accepted the same as it would be on an otherwise-empty tag today,
silently unused, not an error — consistent with spec 003/010 never needing to
reject a *foreign* setting word).

## Acceptance criteria (numeric, testable)
Tolerance: absolute 1e-2 on forces/reactions/stresses (N, Pa), absolute 1e-6 on
displacements (m), unless stated. Evaluate via `Engine().evaluate([...])` with
regions in the given order; "output" is `RegionResult.output` of the `resolve`
region. All numeric examples below are hand-derived from the standard direct
stiffness method (closed-form, not run through any tool during spec-writing); per
this project's established practice (see e.g. decisions.md's note on specs 001-003),
the tester must independently verify them (e.g. against NumPy/SciPy, both
already-approved dependencies) before the developer relies on them.

Single bar (minimal, axial only; d.o.f. elimination checked on the simplest case)
1. `coords := [0, 0; 2, 0] m`, `members := [1, 2]`, `nodes coords in bar`,
   `elements members in bar`, `area 0.0005 m^2 in bar`, `modulus 200 GPa in bar`,
   `support 1 fix x, y in bar`, `support 2 fix y in bar`, `load 2 fx 1000 N in bar`,
   `resolve in bar` → status ok, output starts `⇒ resolved "bar": 2 nodes, 1
   elements`. `bar_displacement =` gives `= [0, 0; 2e-05, 0] m`. `bar_force =`
   gives `= [1000] N` (tension). `bar_stress =` gives `= [2000000] Pa`.
   `bar_reaction =` gives `= [-1000, 0; 0, 0] N` (node 1's x-reaction balances the
   applied load; every other reaction entry is 0, including node 2's x-row, which
   is a free DOF).
2. Same model, `load 2 fx -1000 N in bar` (reversed) → `bar_force =` gives
   `= [-1000] N` (compression), `bar_displacement =` gives
   `= [0, 0; -2e-05, 0] m`, `bar_reaction =` gives `= [1000, 0; 0, 0] N`.

Symmetric two-bar "A-frame" (2D, non-axial load, non-trivial direction cosines,
statically determinate — independently hand-checked two ways: direct stiffness and
classical method-of-joints equilibrium, which agree exactly)
3. `coords := [0, 0; 4, 0; 2, 3] m`, `members := [1, 3; 2, 3]`,
   `nodes coords in bracket`, `elements members in bracket`,
   `area 0.0005 m^2 in bracket`, `modulus 200 GPa in bracket`,
   `support 1 fix x, y in bracket`, `support 2 fix x, y in bracket`,
   `load 3 fy -10000 N in bracket`, `resolve in bracket` → status ok.
   `bracket_displacement =` gives `= [0, 0; 0, 0; 0, -0.000260401] m` (node 3's `ux`
   is exactly 0 by the geometry's left-right symmetry; `uy3 = -13*sqrt(13)*10000 /
   (18*200e9*0.0005) = -2.60401e-4 m`, abs 1e-9).
   `bracket_force =` gives `= [-6009.25; -6009.25] N` (exact closed form
   `F = -sqrt(13)/6 * 10000`, both elements equal by symmetry; compression, i.e.
   the two struts act like the legs of an A-frame under the downward load).
   `bracket_stress =` gives `= [-12018500; -12018500] Pa` (`force / 0.0005 m^2`).
   `bracket_reaction =` gives `= [3333.33, 5000; -3333.33, 5000; 0, 0] N` (row 3 is
   the free node, reaction exactly 0 there; the two support rows balance the
   applied 10000 N: `5000 + 5000 = 10000`, `3333.33 - 3333.33 = 0`).
   Output text contains `3 nodes, 2 elements`.

Units
4. Criterion 3's model, printed in different target units afterward:
   `bracket_displacement = mm` gives `= [0, 0; 0, 0; 0, -0.260401] mm`;
   `bracket_force = kN` gives `= [-6.00925; -6.00925] kN`;
   `bracket_stress = MPa` gives `= [-12.0185; -12.0185] MPa` — all via the existing
   target-unit conversion on `=` that spec 002's own matrices already support,
   unchanged by this spec.
5. `nodes [0, 0; 1, 0] in bad1` (a bare dimensionless matrix, no length unit on the
   coordinates) → error `Units do not match: node coordinates must be a length`.
6. `area 5 in bad2` (bare number, no unit) on an otherwise-valid model → error
   `Units do not match: cross-section area must be an area`. Same pattern with
   `area 5 m in bad2` (wrong dimension, a length instead of an area) → same error
   text.
7. `modulus 200 N in bad3` (force instead of pressure) → error
   `Units do not match: elastic modulus must be a pressure`.
8. `load 1 fx 5 m in bad4` (length instead of force) → error
   `Units do not match: load "fx" must be a force`.
9. `support 1 fix x = 5 N in bad5` (force instead of length) → error
   `Units do not match: support value for "x" must be a length`.

Errors: shape / missing data (exact prefixes are the contract)
10. Missing `nodes` line → `No node coordinates declared for truss model "<name>"`.
    Same family for a missing `elements`/`area`/`modulus` line:
    `No element connectivity declared for truss model "<name>"`,
    `No cross-section area declared for truss model "<name>"`,
    `No elastic modulus declared for truss model "<name>"`.
11. Two `nodes ... in m` lines for the same model → error
    `Node coordinates already declared for truss model "m"`. Same pattern
    (own wording, same shape) for a second `elements`/`area`/`modulus` line.
12. `elements [1, 5] in <name>` with only 3 nodes declared → error
    `Element 1: node 5 is out of range 1..3` (mirrors spec 002's own index-error
    wording style, `"Index 0 out of range 1..2"`).
13. `members := [1, 1]` (an element whose two nodes are the same node) → error
    `Element 1 has zero length (nodes 1 and 1 coincide)`.
14. `area [1, 2, 3] m^2 in <name>` with only 2 elements declared → error
    `area has 3 values but there are 2 elements (use one value or exactly one per
    element)`. Same pattern for `modulus`.
15. `support 9 fix x in <name>` with only 3 nodes declared → error
    `support references node 9, out of range 1..3`. Same pattern (own wording) for
    `load 9 fx 5 N in <name>`.
16. `support 1 fix x, x in <name>` (same axis twice in one line) → error
    `Node 1 has "x" fixed twice in truss model "<name>"`. Two separate `support`
    lines fixing the same node/axis combination give the identical error.
17. `load 1 fx 5 N in <name>` and a second `load 1 fy 3 N in <name>` (same node,
    two different lines) → error
    `Node 1 is loaded by more than one "load" line in truss model "<name>"`.
18. No `support` lines at all for an otherwise-valid model → error
    `Stiffness matrix is singular: truss model "<name>" is unstable or
    underconstrained` (a free-floating structure has no unique solution; this is
    the generic "rigid-body modes present" case, not a special-cased check).
19. `resolve extra in <name>` (trailing text) → error `resolve takes no expression`.
20. A `nodes`/`elements`/`area`/`modulus`/`support`/`load` region with no `resolve`
    region later in reading order for its tag → error
    `No result region for truss model "<name>" below this region` (same wording
    family as spec 003/010's own "No result region for ..." errors); a `load`
    region placed below `resolve` is not used (the resolved result is unchanged by
    it, same reading-order rule as spec 003/010's own constraints/conditions).

Isolation, compatibility, parsing
21. A sheet without any `nodes`/`elements`/`area`/`modulus`/`support`/`load`/
    `resolve` region evaluates identically to before this spec (existing
    `tests/test_engine.py`, `tests/test_solve.py`, `tests/test_odesolver.py`
    unchanged and green). A solve-block model (spec 003), an ODE system (spec 010)
    and a truss model with different tag names on the same sheet do not interact.
    A variable or function the user happens to call `nodes`, `area`, `load`, etc.
    (no trailing ` in <name>`) is completely unaffected, same guarantee spec
    003/010 already give for their own keyword words.
22. Parsing: `parse_statement("nodes coords in bracket")` gives kind
    `model_truss_nodes`, `model="bracket"`, `expr="coords"`;
    `parse_statement("support 1 fix x, y = 2 mm in bracket")` gives kind
    `model_support`, `node="1"`, `axes=[("x", ""), ("y", "2 mm")]`;
    `parse_statement("load 3 fy -10000 N in bracket")` gives kind `model_load`,
    `node="3"`, `axes=[("y", "-10000 N")]`;
    `parse_statement("resolve in bracket")` gives kind `model_result`,
    `model="bracket"`, `goal="truss"`.

## Edge cases
- A `support`'s prescribed non-zero value (`support 4 fix x = 2 mm in <name>`) uses
  the same DOF-elimination math as a zero one — no special-casing; reactions are
  still recovered the same way (see Behaviour, "What resolve computes").
- A node that is declared in `coords` but never referenced by any `elements` row is
  legal (an isolated, unconnected node) but, unless it itself is fully supported,
  leaves the global system singular — reported by the same "Stiffness matrix is
  singular" error as criterion 18, not a separate check.
- A node with **no** support and **no** connecting element at all behaves the same
  way (singular system), not a special "orphan node" error — kept to one error
  family on purpose.
- Non-numeric/symbolic entries anywhere in `coords`/`members`/`area`/`modulus` (an
  undefined symbol) are rejected the same way spec 002 already rejects a symbolic
  matrix under `=` (the usual "... is not defined" error) — this spec's `resolve`
  always evaluates numerically, there is no symbolic/`→` truss result in this
  slice (deliberate: open question 4).
- `area`/`modulus` given as a 1xM row vector instead of an Mx1 column: accepted
  (spec 002's own vector functions already treat row/column vectors of length M
  the same for `len(v)`/indexing purposes; this spec reads values positionally,
  orientation does not matter).
- Very large trusses: no performance guarantee is made by this slice (dense
  `numpy.linalg.solve` on `2N x 2N`, per the research note's own B.3/B.5
  recommendation for "tiny first-slice meshes"); a future phase could move to
  `scipy.sparse.linalg.spsolve` without any syntax change (purely an
  implementation detail inside the new engine module).
- Save format: unchanged; regions remain plain text in `.lsheet` (same as specs
  003/010's own "no format change" note).

## Phase F2 (Euler-Bernoulli beam elements) — forward note only, not specced here
Per the research note's own sizing (012 §B.5: "meaningfully bigger than this
project's usual slice ... closer to spec 009's ~3.5-day two-phase scope") and this
project's "one spec = one shippable slice" rule, this spec covers Phase F1 (2D
truss) only, with full acceptance criteria. Phase F2 (beam elements) needs its own
follow-up spec, written and reviewed once F1 has shipped and been implemented —
not sketched to acceptance-criteria depth here, because it is not a drop-in
addition to F1's own binding shape: a beam-carrying model needs a third DOF per
node (rotation `θ`, alongside `ux`/`uy`), so `<name>_displacement`/
`<name>_reaction` would need a third column, `load`/`support` would need a moment
component (`m`/a prescribed rotation) alongside `fx`/`fy`/`x`/`y`, and
post-processing would add per-element end shear/moment and bending stress
(`M*c/I`) alongside axial force/stress — each a real, separate design decision, not
a trivial reuse. The one thing worth deciding now, so F1's own design does not
paint F2 into a corner: F2 should almost certainly introduce its own leading
keyword (tentatively `beam elements <expr> in <name>` plus `inertia <expr> in
<name>`, mirroring this spec's `elements`/`area`/`modulus` triplet with `inertia`
replacing `area` where axial behaviour isn't modelled, or alongside it for a full
2D "frame" element combining both — the research note's own B.2 already named this
natural extension) rather than overloading this spec's `elements`/`area`/
`modulus` keywords with a type flag, so a model can eventually mix truss and beam
elements without a parsing ambiguity; `resolve in <name>` stays the one trigger
keyword for both. Flagging this choice for the manager/Theo to confirm before F2 is
actually specced, not deciding it now.

## IP check
Pass, with the flags below.
1. No named commercial/open FEM package's docs, UI, workflow, help text or
   branding was read for this spec, continuing the research note's own clean-room
   boundary (012 §B.1/B.7) unchanged — only the generic public sources listed
   above (Wikipedia's Direct stiffness method article, re-confirmed independently
   for this spec; the research note's own already-cited TU Delft/UBC/Jönköping open
   course notes and SciPy/NumPy docs, re-cited by reference, not re-read).
2. Keyword set is LiveSheet's own: `nodes`, `elements`, `area`, `modulus`,
   `support`, `fix`, `load`, `fx`, `fy`, `resolve`. None of these overlaps the
   policy-forbidden vendor keyword list (`Given`/`Find`/`Minerr`/`Minimize`/
   `Maximize`/`Odesolve`); `resolve` was chosen specifically to avoid `solve`
   (already the project's own `->`-chain keyword, the same reason specs 003/010
   both gave for avoiding it) and to avoid anything closer to `Odesolve`.
3. The `<name>_displacement`/`<name>_reaction`/`<name>_force`/`<name>_stress`
   result-binding convention (model-tag-name as a prefix for four fixed result
   matrices) is a genuinely new design choice this spec is making, not drawn from
   any vendor's result-naming scheme (flagged explicitly as open question 1, since
   it is a real judgement call, not an obvious extension of specs 003/010's
   "bind the user's own chosen name" rule — there is no user-chosen name per
   structural quantity to reuse here).
4. The underlying method (direct stiffness: local bar stiffness, direction-cosine
   rotation, scatter-add assembly, DOF elimination, direct linear solve, axial
   force/stress recovery) is centuries-to-decades-old generic statics plus linear
   algebra, independently taught and cited identically (to within notation) across
   every source consulted by the research note and this spec — not distinctive to
   any one software product's implementation, squarely inside IP-POLICY's
   "Allowed: mathematical methods, algorithms and concepts."
5. No GUI/canvas interaction technique is involved anywhere in this spec (no
   drawing, no placeholder editing, no new visual element at all) — ip-cleanroom
   rule 6's patent-sensitivity concern, already flagged and worked around
   elsewhere in this project (specs 005/006), does not apply here; this entire
   first slice is plain-text statement regions, the same category of change as
   specs 001/002/003/010.
6. As with specs 003/010, the generic "named group of tagged regions solved on
   demand" idiom itself has not had a formal patent search — this spec is the
   third feature built on that already-reviewed construct, same standing flag,
   now carried forward rather than repeated as a new concern.
7. No vendor text, example or screenshot was used; the worked examples (a single
   axially-loaded bar, a symmetric two-bar bracket under a point load) are
   textbook-generic statically-determinate truss problems chosen and hand-derived
   independently for this spec, not sourced from any vendor's example library —
   consistent with how specs 001-003/010 built their own numeric examples.
8. Before a 1.0 release, the IP policy's own legal-review step should include this
   feature too (standing reminder, same as every prior spec).

## Fits current architecture?
- `engine/syntax.py`: extend `_parse_model` with the six new leading-keyword
  branches above (`nodes`/`elements`/`area`/`modulus`/`support`/`load`), reusing
  `resolve` → the existing `model_result` kind with a new `goal="truss"` value
  (parallel to `"root"`/`"min"`/`"max"`/`"ode_auto"`/`"ode_symbolic"`/
  `"ode_numeric"`, all already dispatched the same way). Two new additive
  `Statement` fields (`node`, `axes`), same pattern as spec 010's own additions
  (`conditions`, `over_points`); no existing field or caller affected. A small
  shared helper (e.g. `_parse_axis_items`) splits the comma-separated `x`/`y`/
  `fx`/`fy` item lists for both `model_support` and `model_load`, avoiding
  duplicated parsing logic between the two.
- `engine/evaluator.py`: `Engine._run_model` (already dispatching `model_vary`/
  `model_require`/`model_setting`/`model_ode`/`model_ic`/`model_over`/
  `model_result` via its existing `earlier`/`last_result`/`broken_models`
  bookkeeping, specs 003/010) gains `model_truss_nodes`/`model_truss_elements`/
  `model_truss_area`/`model_truss_modulus`/`model_support`/`model_load` as more
  "earlier member" kinds (just registered, nothing run, mirroring how
  `model_over`/`model_setting` are already handled today) and, for
  `model_result`, a new `st.goal == "truss"` branch calling into a new module
  instead of `solver.py`/`odesolver.py`. `Engine.parse`/`Engine._define` are
  unchanged; binding the four result matrices is exactly `env[name] = <SymPy
  Matrix>`, the same shape spec 002's own matrix values already have in `env` —
  `_numeric`, `formatting.py`'s matrix printer and spec 002's existing indexing all
  need zero new code to use them.
- `engine/truss.py` (new, GUI-independent, parallel in spirit to `solver.py`/
  `odesolver.py`): a `Model` dataclass (nodes, elements, area, modulus, supports,
  loads), `build(model, members, env, engine)` (resolves every tagged region's
  deferred expression text against the environment, validates shapes/ranges/units
  once, the same "check once, not per iteration" spirit `solver.py` already uses),
  `solve(model) -> Outcome` (assembly, DOF elimination, `numpy.linalg.solve`,
  post-processing). Unit handling reuses `units.measure`/`UnitError` the same way
  specs 003/010 already do for their own one-time dimension checks.
- `engine/units.py`: no change; `measure` is used the same way specs 002/003/010
  already use it (including on matrix-valued quantities, per spec 002's own
  homogeneous-matrix unit rule).
- `engine/formatting.py`: no change; the four bound results are ordinary SymPy
  matrices printed by spec 002's existing `format_matrix` path; the `resolve`
  region's own one-line summary uses the existing `format_number`/SI-coherent path
  exactly as spec 003/010's result lines already do.
- `engine/matrices.py`: no change; this spec only ever consumes matrix values
  (reading entries, checking shape/homogeneity) through functions that module
  already exposes.
- `pyproject.toml`: no new dependency. NumPy (BSD-3) is already an approved direct
  dependency (decisions.md, 2026-10-27; the research note's own B.3 independently
  confirms SciPy's sparse solvers would also be sufficient for a later, bigger
  phase, but are not needed here).
- `gui/regions.py`, `gui/pretty.py`: no change required — every new statement kind
  is plain text in an existing `MathRegion`, same as specs 001-003/010; no new
  region type, no canvas/wiring involvement (confirming the research note's own
  B.6 conclusion that this feature needs no canvas/wiring mechanism at all).
- `document.py` / `.lsheet`: unchanged (plain text regions, no format version
  change, same as specs 003/010).
- Tests: `tests/test_truss.py` (new, developer, from the acceptance criteria
  above); independent tester writes a black-box counterpart from this spec, same
  process as every previous spec.

## Open questions for the manager (also candidates for docs/board/decisions.md)
1. The `<name>_displacement`/`<name>_reaction`/`<name>_force`/`<name>_stress`
   result-naming convention (model-tag-name as a prefix for four fixed result
   matrices): acceptable as LiveSheet's own convention, or would Theo prefer the
   `resolve` line itself to name the outputs explicitly (e.g.
   `resolve displacement U, reaction R, force F, stress S in <name>`, more
   verbose, more flexible, no synthesized names)? Recommendation: keep the
   synthesized-name default for this first slice (zero extra syntax, and every
   other binding on this project is already "the name the user wrote, used
   verbatim") — an optional explicit-naming extension could be added later
   without breaking this default.
2. Backlog milestone wording (see the manager's own backlog-update task,
   separate from this spec's IP review): propose a new milestone, not folded into
   M6 (per the research note's own B.6 conclusion, re-confirmed above — no
   canvas/wiring mechanism is needed for F1), with this spec covering its first
   item. Suggested wording below.
3. Should `resolve`'s own one-line output additionally include an inline table
   (one row per node/element, mirroring spec 010's numeric-ODE table) in this
   first slice, or is printing the four bound matrices afterward (criteria 1, 3-4)
   sufficient for now? Recommendation: skip the inline table for this slice (kept
   deliberately minimal, matching the research note's own first-slice scoping);
   a later usability spec could add it without any engine change, since the data
   needed already exists in the four bound matrices.
4. This slice has no symbolic (`→`) truss result — `resolve` always solves
   numerically, even if every input happens to be exact/symbolic-free rational
   numbers (unlike spec 002's matrices, which do support exact `→` results).
   Confirm this is acceptable for a first slice (a symbolic stiffness-matrix
   inverse is mathematically possible but of limited practical use at realistic
   problem sizes, and was not requested by the research note); numeric-only, same
   as spec 003's `settle`/`least`/`most`.
5. Phase F2 (beam elements) sequencing/keyword direction (see "Phase F2" section
   above): confirm the `beam elements ... in <name>` / `inertia ... in <name>`
   keyword direction now (so F1's own keyword choices don't block it later), or
   leave it fully open until F2 is actually specced?
