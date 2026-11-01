# 012 CAD-drawing import (DXF) and Finite Element Method — feasibility research note

**Status: research/feasibility note, requested by Theo 2026-10-30, NOT an approved spec.** Neither
part below has acceptance criteria, a phase size that fits the project's usual "~1-3 days" slice, or
a backlog entry yet. This document is the input the manager and Theo need to decide (a) whether to
add backlog items at all, and (b) how to split whatever is approved into spec-sized slices. Nothing
here should be implemented from directly — if approved, a follow-up spec (or specs) will be written
in the usual format and IP-reviewed on its own.

Two independent questions were asked together because they sit on the same conceptual pipeline
("geometry in -> engineering numbers out"), but they are sized very differently and should almost
certainly become separate backlog items / specs (see recommendations at the end of each part).

---

## Part A — Importing CAD drawing data (DXF) as a data-source component

### A.1 Relationship to the existing backlog
Backlog M6 item 32 already covers "data-source components: CSV/other open tabular formats ... and
Excel files ... as wireable components." A DXF file is not tabular data; it is **vector geometry**
(points, lines, curves, closed outlines) rather than rows and columns. This is the same underlying
idea as item 32 — a file reader exposed as a wireable component, per spec 009's `ComponentRegion`/
port/wire contract — applied to a different, richer kind of open file format. Recommend framing any
backlog addition as **32b** ("CAD-drawing data-source component: DXF vector geometry -> section
properties"), not a new unrelated milestone.

### A.2 What DXF actually is (generic, public, decades-old interchange format)
Source: Autodesk's own published DXF reference index (https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-DXF/files/index.htm,
accessed 2026-10-30) and the Wikipedia overview (https://en.wikipedia.org/wiki/AutoCAD_DXF,
accessed 2026-10-30). Reading a vendor's own *published, documented interchange format* in order to
interoperate with it is the same category of activity as reading CSV or PDF — normal file-format
interoperability, not a derivative-work or decompilation concern (contrast with IP-POLICY's
forbidden list, which is about *proprietary, undocumented* formats of named CAS competitors —
Autodesk and DXF are not on that list and the format has been openly published since the 1980s).

- DXF ("Drawing Interchange Format") is a tagged-data text (or binary) format: every value is
  preceded by an integer "group code" naming its meaning (e.g. group code 10/20 = an X/Y
  coordinate, group code 8 = the entity's layer name). Both ASCII and binary variants exist; ASCII
  is a plain text file, directly parseable without any proprietary binary reverse-engineering.
- A DXF file is organised into sections: **HEADER** (drawing-wide settings, each a named variable —
  the relevant one here is `$INSUNITS`, a small integer code for the drawing's linear unit: 0
  unitless, 1 inch, 2 feet, 3 mile, 4 mm, 5 cm, 6 m, 7 km, 8 microinch, 9 mil, 10 yard), **TABLES**
  (named definitions: layers, line types, text styles), **BLOCKS** (reusable groups of entities,
  referenced elsewhere via an `INSERT` entity — the DXF analogue of a symbol/instance, decades-old
  idea, same shape as "a reusable named thing referenced elsewhere" generically), **ENTITIES** (the
  actual drawing objects), **OBJECTS** (non-graphical application data, not relevant here).
- Geometry-bearing entity types relevant to a 2D cross-section: `LINE` (two endpoints), `ARC`
  (centre, radius, start/end angle), `CIRCLE` (centre, radius), `LWPOLYLINE`/`POLYLINE` (an ordered
  vertex list, each segment optionally bulged into a circular arc, with an explicit "closed" flag),
  and `SPLINE` (a parametric curve defined by control points/knots/degree — the general case, most
  complex to turn into a flat polygon). Every entity carries a `layer` name (group code 8), the
  standard DXF way of grouping/filtering entities — the generic "named layer" idea long predates and
  is independent of any one CAD vendor (shared by SVG, PDF, and most 2D drawing formats).
- `$INSUNITS` is a *hint*, not a guarantee: several independently-published forum reports (not
  vendor material — ordinary CAD-interoperability troubleshooting threads) note that not every DXF
  file sets it, and not every reader honours it consistently. Recommend treating it only as a
  **default suggestion** that the user can see and override in the component's own configuration
  (matching spec 009's existing "typed-by-convention, not enforced" port philosophy and the
  engine's existing practice of requiring an explicit unit on a measured value rather than guessing
  one silently).

### A.3 Candidate Python library: ezdxf
- **ezdxf**, current PyPI release 1.4.5 (checked 2026-10-30 at https://pypi.org/project/ezdxf/):
  licensed **MIT** (confirmed via PyPI's own licence classifier and project licence section — it
  switched to MIT in 2014 per its own changelog and has stayed there since). It is an actively
  maintained, general-purpose Python library to read and write DXF files, including the entity
  types listed above, layer/block/unit access.
- Its **core** runtime dependencies (the only ones LiveSheet would actually pull in — its optional
  "drawing add-on" extras, e.g. a Matplotlib/PyQt5-based viewer, are not needed and must explicitly
  **not** be installed, both because they're unneeded and because `PyQt5` would be a second,
  redundant Qt binding alongside the project's existing PySide6 — never add both):
  - `numpy` — BSD-3, already an approved project dependency (decisions.md, 2026-10-27).
  - `pyparsing` — MIT (verified).
  - `fonttools` — MIT (verified).
  - `typing_extensions` — Python Software Foundation Licence, a permissive OSI-approved licence
    (not GPL/AGPL).
  - No GPL/AGPL dependency found anywhere in this chain. All permissive, consistent with CLAUDE.md's
    hard rule. (Recommend the manager/developer re-check the live licence at actual adoption time,
    the same "don't trust memory, verify when it matters" instinct Theo asked for here — dependency
    licences can in principle change between releases, though MIT projects very rarely do.)
  - Only the geometry-*reading* API would be used (iterate entities on a chosen layer, read their
    points/centres/radii, read `$INSUNITS`) — LiveSheet would not use ezdxf's drawing/creation
    features at all for this first slice.
- Alternative noted and rejected for now: `dxfgrabber`, an older read-only DXF library by the same
  author, also MIT, but superseded by/merged into ezdxf and no longer separately maintained — ezdxf
  is the better-supported current choice.

### A.4 The engineering side: section properties from a closed 2D profile
This is standard, decades-old statics/mechanics-of-materials material — computing area and the
geometric moments of a plane region bounded by a polygon via **Green's theorem**, converting a
double (area) integral into a boundary (line) integral over the polygon's edges. This is the same
family of result as the well-known "shoelace formula" for polygon area (a special case of Green's
theorem; see https://en.wikipedia.org/wiki/Shoelace_formula, accessed 2026-10-30), extended to the
first and second moments. Public-domain, textbook-level, not tied to any named product; cross-
checked across two independent public sources (a derivation post at
https://leancrew.com/all-this/2018/01/greens-theorem-and-section-properties and MathWorld's general
polygon-properties treatment, both accessed 2026-10-30) which agree on the same formulas:

For a simple polygon with vertices `(x_i, y_i)`, `i = 0..n-1`, indices wrapping (`(x_n, y_n) =
(x_0, y_0)`), and `C_i = x_i*y_{i+1} - x_{i+1}*y_i`:

- **Area**: `A = (1/2) * sum(C_i)` (signed; positive for a counter-clockwise-wound polygon, negative
  for clockwise — orientation is thus recoverable from the sign, the standard computational-geometry
  convention, not something new).
- **Centroid** (about the origin): `x_c = (1/(6A)) * sum((x_i + x_{i+1}) * C_i)`, similarly for `y_c`
  with `(y_i + y_{i+1})`.
- **Second moments about the origin** (intermediate values): `Ixx_O = (1/12) * sum((y_i^2 + y_i*y_{i+1}
  + y_{i+1}^2) * C_i)`, `Iyy_O` the same shape with `x`, `Ixy_O = (1/24) * sum((2*x_i*y_i + x_i*y_{i+1}
  + x_{i+1}*y_i + 2*x_{i+1}*y_{i+1}) * C_i)`.
- **Centroidal second moments** (parallel-axis theorem, shifting from the origin to the centroid —
  itself a standard, centuries-old mechanics result): `Ixx = Ixx_O - A*y_c^2`, `Iyy = Iyy_O - A*x_c^2`,
  `Ixy = Ixy_O - A*x_c*y_c`.
- **Polar second moment** (perpendicular-axis theorem): `J = Ixx + Iyy`.
- **Radius of gyration**: `rx = sqrt(Ixx/A)`, `ry = sqrt(Iyy/A)`.
- **Section modulus**: `S = I / c`, where `c` is the distance from the centroid to the extreme fibre.
  Because a general (asymmetric) profile has a *different* `c` on each side of each axis, the
  textbook-correct output is really four numbers (`Sx_top`, `Sx_bottom`, `Sy_left`, `Sy_right`), not
  one — flagged as an open design question below rather than silently picking one.
- **Holes / compound sections** (e.g. a tube or box cross-section = outer profile minus inner
  profile): the same formulas handle this "for free" if the inner loop is wound with the *opposite*
  orientation from the outer loop (standard composite-section convention: outer counter-clockwise,
  inner clockwise) and all loops' signed areas/moments are simply summed — this is the ordinary
  statics "composite section = sum of signed sub-areas" idea, not a new algorithm. Recommend
  supporting multiple closed loops from the first slice (same formula, negligible extra cost, and
  hollow/compound sections are extremely common in real mechanical drawings).

### A.5 Component shape (fits spec 009's existing contract, no new mechanism)
This would be one new `component_kind` (tentative name, own, non-vendor: `"cad-profile"`) plugged
into spec 009's existing `ComponentRegion`/port/wire/`config: dict[str,str]` contract — no change to
the wiring mechanism itself, consistent with spec 009's open question 6 ("no further `.lsheet`
format change expected for backlog 32-34... each as new `component_kind` values with their own
`config` keys").
- **Config** (flat strings, per the existing contract): `path` (file path to the `.dxf` file),
  `layer` (optional — restrict to one named layer; "all layers" if blank), `unit` (optional override
  of the file's own `$INSUNITS`, since that header is only a hint per A.2).
- **Input ports**: none for a first slice (a pure source component, like spec 009's "Value" kind).
- **Output ports** (candidates, open question — see below): `area`, `centroid_x`, `centroid_y`,
  `Ixx`, `Iyy`, `Ixy`, `J`, `rx`, `ry`, and — pending the four-values-vs-one decision above —
  either four section-modulus ports or none in the first slice.
- Zero changes needed to the cycle-detection/topological-evaluation machinery; this is "just" a new
  source kind whose compute step calls ezdxf instead of `Engine.parse`.

### A.6 First-slice scope recommendation
**In scope**: a single DXF file containing one or more closed loops built only from `LINE`, `ARC`,
`CIRCLE` and `LWPOLYLINE`/`POLYLINE` entities (arcs/circles tessellated into short line segments at
load time — a standard, generic curve-flattening step, not a new idea), optionally filtered to one
named layer, read via ezdxf, reduced to area/centroid/Ixx/Iyy/Ixy/J/rx/ry (and possibly section
modulus, pending the decision above).

**Explicitly out of scope for a first slice** (each is a real feature, not a shortcut — flagging so
scope creep is visible, not silently assumed away):
- `SPLINE` entities (needs a curve-flattening tolerance/algorithm choice of its own).
- `BLOCK`/`INSERT` (needs recursive block resolution and a transform-composition step).
- Any *rendering* of the imported drawing on the LiveSheet canvas (this slice is a numbers-out
  component, not a CAD viewer) — though exposing the raw flattened point list as one more output
  port, for a later plot-region to draw, would be a cheap, low-risk addition worth considering.
- Non-closed geometry (open polylines/lines that don't form a loop) — reported as a configuration
  error on the component ("Profile is not a closed loop"), the same error-state convention spec 009
  already defines, not a crash.
- Full general-purpose DXF support (dimensions, text, hatches, 3D entities) — this slice only ever
  needs flat 2D outline geometry.

### A.7 IP flags for the manager
1. No AutoCAD UI, icon, workflow, or branding is referenced or implied-as-compatible anywhere in
   this note or should appear in LiveSheet's own UI/wording — this is reading a documented,
   openly-published file format for interoperability, the same posture as CSV/PDF support, not a
   clone of any Autodesk product's behaviour or look.
2. ezdxf (MIT) is a clean, permissively-licensed dependency actually depended on, not a reverse-
   engineered or copied re-implementation of anyone's DXF parser — satisfies CLAUDE.md's hard rule.
   Its own dependencies (numpy, pyparsing, fonttools, typing_extensions) are all permissive too (A.3).
3. **Open question explicitly flagged, per the task's instruction**: is using the bare string "DXF"
   as a supported-format name in LiveSheet's own UI/docs ("Import DXF...", "CAD profile (DXF)")
   itself fine? My own read: yes, by the same reasoning IP-POLICY already accepts for "CSV" — DXF is
   the generic, decades-old published name of an interchange format (like "CSV", "PDF", "JSON"), not
   a product name or marketing term, and IP-POLICY's "Factual comparison in docs is OK; keep it
   minimal and nominative" clause already covers naming a file format you can read. The forbidden
   list (Mathcad/Mathematica/Maple/Wolfram/PTC/Maplesoft) is about *product* names, not format
   names. The word "AutoCAD" itself, by contrast, should **not** appear in LiveSheet's own UI/menu
   wording (only ever in this research note / internal docs as a nominative, factual reference to
   whose format DXF originally is) — recommend the manager confirm this split explicitly rather than
   taking my own call as final, since Theo specifically asked for this to be double-checked.

### A.8 Open questions for the manager (DXF)
1. Section modulus: one value per axis (pick the smaller of top/bottom, a common simplified
   convention) or four values (top/bottom/left/right, textbook-complete but more output ports)?
   [No recommendation yet — a mathcad-specialist formula/workflow review is recommended before this
   becomes a real spec; I tried to reach the mathcad-specialist agent directly (per the task's
   suggestion) and it was not reachable, same experience spec 009 records for the gui-specialist —
   flagging rather than guessing on the specialist's behalf.]
2. Should the raw flattened outline (point list) also be exposed as an output port for later use by
   a plot region, or deferred entirely until there's a concrete consumer for it?
3. Confirm the "DXF"-the-format-name-is-fine-but-not-"AutoCAD"-in-UI-wording split above.
4. Sizing: this is bigger than most single specs (DXF parsing + curve flattening + multi-loop
   composite-section math + a new component kind) — recommend splitting into at least two specs if
   approved: (i) single-closed-loop LWPOLYLINE-only profile -> area/centroid/Ixx/Iyy/Ixy/J/r, (ii) a
   follow-up adding ARC/CIRCLE tessellation and multi-loop (hole) support.

---

## Part B — Finite Element Method (FEM): minimal first-slice feasibility

### B.1 Framing and clean-room boundary (read this before anything else in Part B)
FEM, like the linear algebra behind backlog 002/003, is generic applied mathematics/engineering
theory taught in any university structural-mechanics or numerical-methods course — **not** the
property of any particular software vendor. Per the explicit instruction for this part of the
research: I consulted only generic public course material and encyclopedic sources (Wikipedia's
"Direct stiffness method" article; open university course notes from TU Delft, UBC, and a
Jönköping-University-hosted mechanics course, all cited below with access dates) that describe the
*mathematical method* — element stiffness matrices, assembly, boundary conditions, solving. I did
**not** read, study, or compare against any named commercial or open FEM package's documentation,
GUI, workflow, help text, tutorials, or branding (ANSYS, Abaqus, COMSOL, NASTRAN, SolidWorks
Simulation, CalculiX, FEniCS, or any other). The one place a specific package's name appears below
is a licence check for whether it could ever be a *dependency* — a different, permitted activity
from studying its UI/workflow as design inspiration (ip-cleanroom skill, point 6 and the IP-POLICY
process). Nothing in Part B should be read as drawing on any such package's design.

### B.2 What a minimal, generically-taught FEM workflow requires
Sources consulted (all public, generic course/reference material, accessed 2026-10-30):
- Wikipedia, "Direct stiffness method" (https://en.wikipedia.org/wiki/Direct_stiffness_method) —
  the standard name for exactly the truss/beam-element assembly technique below; describes it as
  "the most common implementation of the finite element method" for skeletal (bar/beam) structures.
- TU Delft open course notes, "Euler-Bernoulli beam elements"
  (https://interactivetextbooks.citg.tudelft.nl/computational-modelling/structural_linear/euler_bernouilli.html)
  — a from-first-principles derivation (strong form -> Galerkin weak form -> cubic shape functions
  -> the classic 4x4 element stiffness matrix), open university course material.
- UBC open course notes, "Euler-Bernoulli Beam Elements" PDF
  (https://civil-terje.sites.olt.ubc.ca/files/2022/01/Euler-Bernoulli-Beam-Elements.pdf) — a second,
  independent derivation of the same element, used here only to cross-check the coefficients.
- A Jönköping-University-hosted open mechanics course, "Systematic Truss Analysis"
  (https://mechanics.ju.se/SystematicTrussAnalysis.html and the companion Python-oriented page) —
  the truss (bar) element, its local-to-global rotation, and global assembly.
- scipy's own public documentation for `scipy.sparse.linalg`
  (https://docs.scipy.org/doc/scipy/reference/sparse.linalg.html) — confirmed directly rather than
  assumed, see B.3.

The generically-taught minimal workflow, in order:
1. **Mesh representation**: a list of **nodes** (each a point in space, here 2D: `x, y`) and a list
   of **elements**, each referencing two node indices plus the element's own material/section data.
   This is the simplest possible mesh — no element interior nodes, no 2D/3D continuum shape
   functions — and maps directly onto data LiveSheet already knows how to represent (a node-
   coordinate matrix and an element-connectivity matrix are just today's existing vector/matrix
   literals, spec 002).
2. **Element types, cheapest first**:
   - **1D truss/bar element** (2 nodes, 1 translational DOF per node along the bar's own axis, but
     2 DOFs per node — x and y — once resolved into global coordinates): local stiffness
     `k_local = (E*A/L) * [[1, -1], [-1, 1]]` (axial stiffness only — a bar carries no bending or
     shear by definition), rotated into global x/y DOFs via the bar's direction cosines (`cos θ`,
     `sin θ` from its own endpoint coordinates) before assembly. By far the simplest element; a
     textbook first example in every treatment found above.
   - **Euler-Bernoulli beam element** (2 nodes, 2 DOFs per node — transverse displacement `v` and
     rotation `θ` — 4 DOFs total per element, no axial DOF in this minimal form): the classic 4x4
     element stiffness matrix `k = (E*I/L^3) * [[12, 6L, -12, 6L], [6L, 4L^2, -6L, 2L^2], [-12, -6L,
     12, -6L], [6L, 2L^2, -6L, 4L^2]]`, the same cubic-shape-function result independently derived
     by both the TU Delft and UBC course notes above (cross-checked, coefficients agree). Combining
     a beam element's bending DOFs with a truss element's axial DOF gives the standard 2D "frame"
     element (6 DOFs: axial + bending at each end) — a natural, still-generic phase-2 extension, not
     attempted in the first slice.
   - **2D plane-stress/plane-strain continuum elements** (triangles/quadrilaterals with their own
     shape functions and numerical/Gauss-point integration) are a credible, much bigger phase-2+
     item — genuinely more complex (element formulation, numerical integration, far more nodes per
     real geometry) and explicitly deferred, consistent with the task's framing.
3. **Material properties**: Young's modulus `E` for both element types; cross-section area `A` for
   truss; second moment of area `I` for beam (a cross-section property — note the direct conceptual
   link back to Part A: a beam's `I` could one day come from a `cad-profile` component's `Ixx`
   output, see B.5). Poisson's ratio only matters once a 2D/3D continuum element exists — not needed
   for truss/beam.
4. **Loads**: concentrated nodal point loads (`Fx`, `Fy` at a node for truss; `Fy`, moment `M` at a
   node for beam) are the simplest case and sufficient for a first slice. Distributed loads along a
   beam element (e.g. a uniform load per unit length) require converting them into statically-
   equivalent nodal loads first — a well-known, generic, but genuinely extra step, recommended for
   phase 2, not the first slice.
5. **Boundary conditions / supports**: a prescribed value (almost always zero — "fixed", "pinned",
   "roller") at specific global DOFs. The standard, generic technique — partition the global DOFs
   into "free" and "constrained," solve only the free-free sub-block of the stiffness matrix against
   the free-DOF load vector, then recover reaction forces from the eliminated rows — is taught
   identically across every source above under names like "DOF elimination" or "static reduction";
   nothing product-specific about it.
6. **Global stiffness assembly**: each element's local stiffness matrix (already rotated into global
   DOF directions for truss elements) is scatter-added into the right rows/columns of one big global
   matrix, indexed by each element's two nodes' global DOF numbers — plain repeated matrix addition,
   conceptually the same "many small contributions summed into one big structure" idea spreadsheets
   and accounting ledgers have used for centuries, nothing new introduced here.
7. **Linear solve**: `K_free * u_free = F_free`.
8. **Post-processing**: nodal displacements come directly out of the solve; a truss element's axial
   force is `(E*A/L) * (elongation along its own axis)` and its stress is `force / A`; a beam
   element's end shear/moment come from its own stiffness matrix times its (now known) end
   displacements, and its bending stress is the classic `M*c/I` (`c` = distance from the neutral
   axis to the extreme fibre — again, the same section-property idea as Part A's `Ixx`/centroid).

### B.3 Numerics: is scipy enough?
Checked directly against scipy's own public docs (not assumed from memory, per the task's
instruction): `scipy.sparse.linalg` provides `spsolve` (direct sparse solve), `cg`/`minres` (for
symmetric positive-definite / symmetric systems — a constrained, well-posed FEM stiffness matrix is
normally SPD) and, for a later modal-analysis phase, `eigsh`/`eigs` (sparse eigenvalue solvers,
including the generalised form `K*phi = lambda*M*phi` modal analysis needs). scipy is already an
approved BSD dependency (decisions.md, 2026-10-27) — **no new dependency is needed** for any of
this, in either the first slice or the credible later phases (modal analysis, larger meshes).
For the *first* slice specifically, meshes will be tiny (a hand-typed truss of a few members has at
most a few dozen DOFs); recommend starting with plain **dense** `numpy.linalg.solve` on the full
(already-reduced) stiffness matrix rather than bringing in sparse-matrix bookkeeping at all — simpler
code, no measurable performance difference at this size — and only moving to
`scipy.sparse.linalg.spsolve` once/if a later phase (e.g. a mesh with hundreds of elements) actually
needs it. Flagging as an implementation-sizing detail for whoever writes the eventual spec, not a
blocking question.

### B.4 Sequencing against Part A (does FEM need DXF import first?)
No. The truss/beam stiffness-assembly-and-solve mechanism itself needs only a list of node
coordinates and an element-connectivity list — exactly the shape of data LiveSheet's existing
vector/matrix literals (spec 002) already produce if the user simply types them in by hand. There is
no technical dependency on Part A at all, and recommend **not** creating one: ship a first FEM slice
with hand-entered geometry (a node-coordinate matrix + an element-connectivity matrix, in the same
spirit as spec 008's dialog-based matrix entry, or just typed literals), independent of whether DXF
import ever ships.

**Meshing arbitrary imported geometry is a separate, much bigger, and explicitly out-of-scope
problem** even once DXF import exists: turning a general imported 2D outline into a *mesh* of many
small elements (triangulation, element-quality control, choosing an element type/density) is a
well-known hard sub-field of FEM in its own right, not a natural extension of either the truss/beam
slice or the DXF profile-to-section-properties slice. The one *legitimate, much smaller* link worth
flagging for later (not now): a DXF `cad-profile` component's `Ixx` output could feed, as an ordinary
wire, into a beam element's `I` configuration — using one *number* an imported drawing produced,
not meshing the drawing's geometry itself. That's a small, natural follow-up once *both* slices
exist; it motivates no scope change to either slice today.

### B.5 Size/complexity estimate and explicit scope
A first slice — 2D truss only, concentrated nodal loads only, DOF-elimination boundary conditions,
dense linear solve, nodal-displacement + axial-force/stress output, hand-entered node/element data —
is **meaningfully bigger than this project's usual ~1-3-day spec slice** (own data model for
nodes/elements/materials/loads/supports, local-to-global rotation, assembly, solve, two kinds of
post-processed output, plus its own tests) — closer to the size of spec 009's ~3.5-day two-phase
foundation spec than to a typical single-phase spec. Recommend splitting, if approved, into at least:
- **Phase F1**: 2D truss only (as just described) — roughly spec-009-sized on its own.
- **Phase F2**: Euler-Bernoulli beam element added (new DOF type, moment/shear/bending-stress
  post-processing, distributed-load-to-equivalent-nodal-load conversion).
- **(Possible later, separately-approved phase)**: 2D plane-stress/plane-strain continuum elements.

**Explicitly out of scope** for the first slice and likely the second: 2D/3D continuum elements and
their shape functions/numerical integration; nonlinear material or geometric behaviour; dynamic,
transient or modal analysis (though B.3 shows the numerics for modal analysis, `eigsh`, are already
available whenever that's wanted); contact; thermal coupling; any automatic meshing of imported
geometry (see B.4); distributed/body loads (gravity, pressure) in the very first phase.

### B.6 Whether this belongs in M6, or elsewhere
FEM's truss/beam mechanism itself is a *numerical engine capability* (own stiffness-matrix/solve
code, no canvas/wiring concept needed at all for Phase F1) — closer in spirit to the existing
linear-algebra (002) and solve-block (003) milestone than to M6's component-wiring-canvas work. Only
the small B.4 link (an `Ixx` output feeding a beam's `I` input as a wire) would ever touch M6's
wiring mechanism, and only once both this and Part A exist. Recommend: a **new backlog milestone**
(numeric structural-analysis capability, mathcad-specialist's territory, same bucket style as M1/M3)
rather than folding it into M6, with a note that a wireable version becomes possible later without
needing a new mechanism (spec 009's existing contract already supports a new `component_kind`
whenever that's wanted).

### B.7 IP flags for the manager (FEM)
1. No named commercial/open FEM package's docs, GUI, workflow, help text or branding was read or
   used as design inspiration (B.1) — only generic public course/reference material about the
   mathematical method itself, the same category as how specs 002/003 were grounded in textbook
   linear algebra, not a competitor's product.
2. **No FEM-specific package is recommended as a dependency at all.** The truss/beam mechanism is
   small enough (a handful of matrix formulas plus assembly/solve, all already achievable with the
   already-approved numpy/scipy) that LiveSheet's own code should implement it directly, rather than
   depending on any existing general-purpose FEM library — this keeps the clean-room boundary
   simplest (zero FEM-package code of any kind, vendor or open-source, ships with LiveSheet) and
   avoids ever needing to resolve a FEM package's licence. For completeness, since the task asked
   about checking specific packages' licences if considered as dependencies: CalculiX is GPL
   (excluded outright per CLAUDE.md's no-GPL/AGPL rule, regardless of any other consideration);
   FEniCS is LGPLv3. Neither is recommended or needed here.
3. Formula set (truss/beam stiffness matrices, DOF elimination, parallel/perpendicular-axis-style
   post-processing) is standard, decades-old, textbook material appearing identically (to within
   notation) across every independent source consulted — not distinctive to any one software
   product's implementation.

### B.8 Open questions for the manager (FEM)
1. Backlog placement (new milestone vs. folding into an existing one) — see B.6, no final call made
   here, flagging for the manager/Theo.
2. User-facing shape of a first slice: a dedicated syntax block (analogous to spec 010's `ode`/
   `start`/`evolve` tag idiom or spec 003's `vary`/`settle` solve-block) that takes node/element/
   material/load/support data and returns displacement/stress results in one place, vs. exposing
   the stiffness-assembly-and-solve step as ordinary vector/matrix operations the user chains by
   hand with today's existing linear-algebra syntax (002), with no new dedicated block at all. I
   tried to reach the mathcad-specialist agent directly (per the task's suggestion, same as for
   Part A's open question 1) and it was not reachable; recommend a mathcad-specialist review of
   exactly this question before a real spec is written, same recommendation as Part A.
3. Units: the engine already tracks units through ordinary expressions; a first FEM spec needs to
   work out how force/length/`E`/stress units flow through the stiffness-matrix arithmetic
   consistently (e.g. `E*A/L` naturally produces a force-per-length stiffness unit) — flagged for
   whoever writes the real spec to work out in detail, not resolved here.

---

## Sources consulted (public, generic concepts only — see inline citations above for exact URLs
and 2026-10-30 access dates)
- Part A: Autodesk's published DXF format reference index (interoperability reference, not a vendor
  product's UI/workflow); Wikipedia "AutoCAD DXF" and "Shoelace formula"; ezdxf's own PyPI page and
  changelog (licence/version check); a public derivation of polygon section properties from Green's
  theorem (leancrew.com) cross-checked against MathWorld's general polygon-properties treatment.
- Part B: Wikipedia "Direct stiffness method"; open university course notes (TU Delft, UBC,
  Jönköping University) describing the generic truss/beam finite-element method; scipy's own public
  `scipy.sparse.linalg` documentation. No named commercial or open FEM package's documentation, UI,
  or workflow was read (see B.1).

## .lsheet format implications
- Part A fits entirely inside spec 009's existing `component_kind`/`config: dict[str,str]` extension
  point — no new `FORMAT_VERSION`, no change to the wire/port mechanism. Only a new `component_kind`
  string and its own small `config` keys (`path`, `layer`, `unit`).
- Part B's first slice (hand-entered truss data, no wiring-canvas involvement) likely needs **no**
  `.lsheet` change beyond whatever new statement-block syntax a real spec proposes (same category of
  change as spec 010's `ode` block, which added new statement syntax but no document-format version
  bump) — to be confirmed when that spec is written. A later wireable FEM component (the small B.4
  link) would, like Part A, fit inside spec 009's existing extension point with no new format
  version.

## IP check (overall)
Pass, both parts, with the open questions above flagged rather than silently resolved. Nothing here
proposes a vendor name, icon, file format internals, or 1:1 keyword set; Part A's dependency (ezdxf)
and its own dependency chain are all permissively licensed; Part B proposes no FEM-package dependency
at all, own-code-only. Not legal advice.
