# 013 DXF profile import, phase 1: single closed straight-sided loop -> section properties

Implements backlog milestone M6 item 35 (research note: `docs/board/specs/012-cad-import-and-fem-
research.md`, Part A), framed there as a natural extension of backlog 32 ("data-source components:
CSV/other open tabular formats... as wireable components") from tabular data to vector geometry —
recommend the manager/Theo read it as backlog **32b** if a label is wanted, not a new unrelated
milestone.

Source inspiration (concept only, nothing copied — all already consulted and dated in the research
note above; dates repeated here for this spec's own IP-check trail, not re-fetched):
- Autodesk's own published DXF format reference index
  (https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-DXF/files/index.htm, accessed 2026-10-30)
  and Wikipedia's "AutoCAD DXF" overview (https://en.wikipedia.org/wiki/AutoCAD_DXF, accessed
  2026-10-30) — read as interoperability reference for a documented, openly-published interchange
  format, the same posture as reading a CSV or PDF format description, not as a vendor product's
  UI/workflow/branding. The word "AutoCAD" appears only in this nominative, factual sentence (and
  the research note it continues from) about whose format DXF historically is — it never appears in
  any LiveSheet product string, menu, dialog, error message, config key, or identifier below; "DXF"
  itself is used the same way LiveSheet already uses "CSV"/"PDF" (a generic format name, not a
  product name), per the manager's confirmation of the research note's A.7 open question.
- ezdxf's own PyPI project page and changelog (https://pypi.org/project/ezdxf/, accessed
  2026-10-30) — licence (MIT) and version (1.4.5) check for a dependency actually used, not studied
  for design ideas.
- Wikipedia, "Shoelace formula" (https://en.wikipedia.org/wiki/Shoelace_formula, accessed
  2026-10-30) — public-domain polygon-area identity, the base case of the property formulas below.
- A public derivation of polygon section properties from Green's theorem
  (https://leancrew.com/all-this/2018/01/greens-theorem-and-section-properties, accessed
  2026-10-30), cross-checked against MathWorld's general polygon-properties treatment (accessed
  2026-10-30) — both textbook-level, decades-old statics/mechanics-of-materials material, agreeing
  on the same formulas; not tied to any named product.
- `docs/board/specs/009-component-wiring-core.md` and `.claude/skills/modeling-concepts/SKILL.md` —
  this spec plugs a new `component_kind` into spec 009's already-approved, generic
  `ComponentRegion`/port/wire contract; it adds no new wiring mechanism or interaction technique of
  its own.
- No named commercial CAD product's UI, icon set, workflow, tutorials, or example drawings were
  read or used as a source.

Scope note: this is **phase 1 of 2** for backlog 35. It restricts the imported geometry to the
simplest well-formed case — **one closed, straight-sided `LWPOLYLINE`/`POLYLINE` entity** — so the
new component kind, its config/output-port shape, the engineering-property math, and the dialog/
wiring plumbing can all be built and tested end to end without first solving curve tessellation or
multi-loop assembly. A follow-up, `docs/board/specs/014-dxf-profile-geometry-extensions.md`, adds
`ARC`/`CIRCLE` entities, polyline "bulge" (curved) segments, loop assembly from separate `LINE`
entities, and multi-loop composite (hole) sections — each a materially different *geometry-assembly*
problem from this phase's property *math*, and roughly comparable in size to each other; splitting
here is slightly narrower than the research note's own A.8.4 suggestion (which only separated
"`LWPOLYLINE`-only" from "add `ARC`/`CIRCLE` + multi-loop" and did not call out `LINE`-chaining
separately) — flagged explicitly in Open questions below for the manager to confirm this
restructuring. Estimated size: about 2-2.5 days (new dependency wiring, a new engine module with its
own pure-math unit tests, a new `_PORTS`/`_COMPUTE` entry, a new dialog page, DXF test fixtures
generated at test time via ezdxf's own write API).

---

## User story
As a LiveSheet user doing a mechanical-engineering calculation, I want to point a component at a
`.dxf` drawing file containing a closed cross-section outline and get its area, centroid, second
moments of area, polar moment, radii of gyration and section moduli as ordinary wireable numbers —
so that a beam or column's real cross-section (drawn once in a CAD tool) can feed straight into the
rest of a LiveSheet calculation instead of being retyped or recomputed by hand.

## Behaviour (own words)

### A new component kind: `"cad-profile"`
This spec adds one new value to the `component_kind` string spec 009 already made free-form —
`"cad-profile"` (own, non-vendor name) — plugged into the exact same `ComponentRegion`/port/wire
contract every other kind uses. Nothing about the wiring mechanism, cycle detection, topological
evaluation order, or error-state painting changes; this is "just" a new source kind, like spec 009's
own "Value" placeholder but reading a file instead of a typed expression.

- **Input ports**: none — a pure source component, exactly like "Value".
- **Configuration** (flat strings, per spec 009's existing `config: dict[str, str]` contract):
  - `path` — the `.dxf` file's path. Required.
  - `layer` — optional. If non-blank, only entities on that exact DXF layer name (group code 8) are
    considered; if blank, entities from every layer are considered (across the whole file's model
    space — `BLOCK`/`INSERT` entities are not traversed in this phase or the next, see Edge cases).
  - `unit` — optional. If non-blank, must name one of the engine's own existing linear length units
    (`engine/units.py`'s `UNITS` table: `m`, `km`, `cm`, `mm`, `um`, `nm`, `inch`, `ft`, `yd`, `mi`)
    and overrides whatever the file's own header says. If blank, the unit is read from the file's
    `$INSUNITS` header variable (see table below) — this is the same "default suggestion the user
    can see and override" posture the research note recommended (A.2), not a silent guess.
- **Output ports** (fixed list, in this declaration order — not config-dependent, unlike "Formula"'s
  input-port list): `area`, `centroid_x`, `centroid_y`, `Ixx`, `Iyy`, `Ixy`, `J`, `rx`, `ry`,
  `Sx_top`, `Sx_bottom`, `Sy_left`, `Sy_right`, `outline`.

### `$INSUNITS` resolution table (own naming of a publicly documented header field, A.2)
| `$INSUNITS` code | meaning | engine unit name |
|---|---|---|
| 1 | inch | `inch` |
| 2 | feet | `ft` |
| 4 | millimetre | `mm` |
| 5 | centimetre | `cm` |
| 6 | metre | `m` |
| 7 | kilometre | `km` |
| 10 | yard | `yd` |
| 3 | mile | `mi` |
| 0, 8, 9, missing, or any other code | unitless / microinch / mil / unrecognised | *(no mapping)* |

If `unit` is blank and the file's own `$INSUNITS` falls in the last row (including simply not being
present at all — the research note's forum-sourced finding that not every file sets it, A.2), this
component is in the error state "Drawing has no usable unit information; set 'unit' in this
component's configuration, e.g. 'mm'." rather than silently assuming a unit — consistent with the
engine's existing practice of never guessing an unstated unit.

### Finding the one closed loop (this phase's scope boundary)
After applying the `layer` filter, this phase looks only at `LWPOLYLINE`/`POLYLINE` entities whose
`closed` flag is set **and** every one of whose segments has a zero bulge (i.e. every segment is a
straight line, no arc-replacing-a-segment encoding) — a "closed, straight-sided polyline," the
simplest unambiguous case. Standalone `LINE`, `ARC`, `CIRCLE` entities, and any polyline with a
nonzero bulge or that is not marked closed, are recognised as present but out of this phase's scope
(see error states) rather than silently ignored, so the error message tells the user this is a
"not yet" rather than a "nothing here."

- **Exactly one** such closed, straight-sided polyline candidate on the filtered entity set: that is
  the profile. Its vertex list (in file order, each an `(x, y)` pair in the file's own local
  coordinate system, Z ignored — see Edge cases) is the loop used for all the property math below.
- **Zero** candidates, but at least one `ARC`, `CIRCLE`, bulged-segment, or standalone `LINE` entity
  is present on the filtered set: error "This profile uses curved segments or separate line
  segments, not yet supported by this component (phase 1 supports one closed straight-sided
  polyline entity only)." — this is exactly the gap spec 014 fills.
- **Zero** candidates and none of the above either (e.g. the filtered set is empty, or contains only
  non-geometric entities like text/dimensions): error "No closed profile found (phase 1 supports one
  closed straight-sided polyline entity only)."
- **More than one** candidate: error "Multiple closed profiles found on this drawing; set 'layer' to
  pick one." (Spec 014 changes this rule for the specific case of one outer loop plus contained hole
  loops — see that spec's own Behaviour section for exactly how the two specs interact.)
- A candidate with fewer than 3 distinct vertices or a signed area of exactly zero (collinear
  points): error "Profile has zero area."

### Section properties (shoelace-formula family, public-domain statics)
Given the resolved vertex list `(x_i, y_i)`, `i = 0..n-1` (indices wrap, `(x_n, y_n) = (x_0, y_0)`),
and `C_i = x_i*y_{i+1} - x_{i+1}*y_i`, computed in the file's own raw numeric coordinates (before any
unit is attached):

- `area = (1/2) * sum(C_i)` — signed; this phase does not reject a clockwise-wound single loop (its
  area is simply negative-of-what-a-CCW-winding-would-give before the absolute value used for
  display — the port's actual output is the **absolute** area; a negative sign is only meaningful
  once spec 014 introduces holes, so this phase reports `abs(area)` on `area`'s own output port and
  uses the raw signed value only internally for the centroid/moment formulas below, which need it).
- `centroid_x = (1/(6*area_signed)) * sum((x_i + x_{i+1}) * C_i)`, `centroid_y` the same shape with
  `y`. (Using the *signed* area here, not the absolute value, is required for the formula to be
  correct regardless of winding direction.)
- `Ixx_O = (1/12) * sum((y_i^2 + y_i*y_{i+1} + y_{i+1}^2) * C_i)`, `Iyy_O` the same shape with `x`,
  `Ixy_O = (1/24) * sum((2*x_i*y_i + x_i*y_{i+1} + x_{i+1}*y_i + 2*x_{i+1}*y_{i+1}) * C_i)` — second
  moments about the file's own coordinate origin.
- Centroidal moments via the parallel-axis theorem: `Ixx = Ixx_O - area_signed*centroid_y^2`,
  `Iyy = Iyy_O - area_signed*centroid_x^2`, `Ixy = Ixy_O - area_signed*centroid_x*centroid_y`.
- `J = Ixx + Iyy` (perpendicular-axis theorem).
- `rx = sqrt(Ixx / abs(area_signed))`, `ry = sqrt(Iyy / abs(area_signed))`.
- Extreme-fibre distances from the centroid, taken over every vertex in the loop:
  `c_top = max(y_i) - centroid_y`, `c_bottom = centroid_y - min(y_i)`,
  `c_left = centroid_x - min(x_i)`, `c_right = max(x_i) - centroid_x`.
- Section modulus: `Sx_top = Ixx / c_top`, `Sx_bottom = Ixx / c_bottom`, `Sy_left = Iyy / c_left`,
  `Sy_right = Iyy / c_right` — **four separate output ports**, a deliberate, resolved design decision
  (see "Design decisions" below), not left as an open question.
- `outline`: the raw vertex list itself, as an N×2 value (see "Fits current architecture?" for its
  exact representation) — also a resolved decision, see below.

### Design decisions resolved for this spec (were open questions in the research note, A.8)
1. **Section modulus: four ports, not one.** A general (asymmetric) profile genuinely has a
   different distance from centroid to extreme fibre on each of its four sides, so `Sx_top` ≠
   `Sx_bottom` and `Sy_left` ≠ `Sy_right` in the common case (the acceptance criteria below exercise
   exactly this with a right triangle). Collapsing to one value (e.g. "the smaller of top/bottom," a
   common simplified hand-calculation convention) would silently discard a real number an engineer
   may need — e.g. checking both the tension and compression side of a bending member — for the sake
   of saving three output ports, and ports are cheap in this mechanism (spec 009's contract has no
   per-port cost beyond a name). Decided: four ports. Flagging the decision explicitly per the
   task's instruction, in case the manager prefers the simpler one-value convention instead.
2. **`outline` is exposed now, not deferred.** It reuses the existing matrix-with-units value shape
   (see "Fits current architecture?") at no extra mechanism cost, and the research note itself
   flagged this as "a cheap, low-risk addition worth considering" (A.6) for a future plot region to
   draw. **Important caveat, not glossed over**: no `PlotRegion` can actually consume a component's
   output today — spec 009's own open question 1 states components do not read/write ordinary sheet
   variables or regions at all yet. This port is specified now, and is wireable like any other
   output, but has no real consumer until that gap is closed by a future spec. Flagging so the
   manager doesn't read this as "plotting an imported profile already works."

## Syntax proposal (own keywords)
N/A for sheet statement syntax, same as spec 009: this is a new component kind on the existing
canvas/graph contract, not a new statement kind in `engine/syntax.py`. The three config fields
(`path`, `layer`, `unit`) are plain strings edited through the "Add Component" dialog's own labelled
fields (see below), not parsed by `Engine.parse`.

## Acceptance criteria
Worked example used throughout: a DXF file containing exactly one closed, straight-sided
`LWPOLYLINE` with vertices `(0, 0)`, `(40, 0)`, `(0, 20)` (a right triangle, counter-clockwise
wound), `$INSUNITS = 4` (millimetres). Hand-derived via the formulas above (cross-checked twice):
`area = 400`, `centroid_x = 40/3 = 13.3333`, `centroid_y = 20/3 = 6.66667`, `Ixx = 80000/9 = 8888.89`,
`Iyy = 320000/9 = 35555.6`, `Ixy = -80000/9 = -8888.89`, `J = 400000/9 = 44444.4`,
`rx = sqrt(200/9) = 4.71405`, `ry = sqrt(800/9) = 9.42809`, `c_top = 40/3`, `c_bottom = 20/3`,
`c_left = 40/3`, `c_right = 80/3`, giving `Sx_top = 666.667`, `Sx_bottom = 1333.33`,
`Sy_left = 2666.67`, `Sy_right = 1333.33` (all in mm/mm²/mm³/mm⁴ as applicable, 6-significant-digit
display per the engine's existing `format_number` convention).

1. A sheet with no `cad-profile` component behaves identically to today — adding this kind is purely
   additive to `wiring.py`'s `_PORTS`/`_COMPUTE` dicts, nothing about `Worksheet.recalculate()`,
   `document.py`, or any other kind's behaviour changes.
2. Add a `cad-profile` component `P1` with `config = {"path": "<fixture>", "layer": "", "unit": ""}`
   pointing at the worked example above. `P1` is not in an error state; its output ports equal the
   values above (`area = 400 mm²`, … `outline` = the 3×2 vertex list `[0, 0; 40, 0; 0, 20]` mm, rows
   in file order).
3. Same fixture but with `$INSUNITS` absent from the file entirely and `config.unit = "mm"` set
   explicitly: identical results to criterion 2 — the override substitutes cleanly for a missing
   header.
4. A fixture containing the same triangle on layer `"profile"` plus an unrelated closed
   straight-sided square on layer `"scrap"`; `config.layer = "profile"` selects only the triangle
   (same values as criterion 2); `config.layer = "scrap"` selects only the square.
5. `config.path = ""`: error state "No DXF file path set."
6. The layer+scrap fixture from criterion 4 with `config.layer = ""` (no filter): error state
   "Multiple closed profiles found on this drawing; set 'layer' to pick one."
7. A fixture containing one standalone `CIRCLE` entity and nothing else: error state "This profile
   uses curved segments or separate line segments, not yet supported by this component (phase 1
   supports one closed straight-sided polyline entity only)."
8. The worked-example fixture with `$INSUNITS` absent and `config.unit = ""`: error state "Drawing
   has no usable unit information; set 'unit' in this component's configuration, e.g. 'mm'."
9. The worked-example fixture with `config.unit = "banana"`: error state "Unknown length unit
   'banana'; use one of LiveSheet's existing length units, e.g. 'mm', 'm', 'inch'."
10. Wire `P1.area -> F1.a` where `F1` is a "Formula" component (spec 009) with input `a` and
    `expr = "a"`. `F1.result` evaluates to the same `400 mm²` value as `P1.area` — the new kind's
    outputs need zero special-casing anywhere downstream of the wiring graph.
11. Save a sheet containing `P1` to `.lsheet`, close, reopen: `P1`'s kind, name, and all three config
    values round-trip exactly, and its outputs recompute to the same values with no user action,
    writing/reading `FORMAT_VERSION_COMPONENTS = 3` exactly as spec 009 already does (no format
    version bump from this spec — `component_kind` was already a free-form string).

## Edge cases
- A `path` that exists but is not a valid DXF file (wrong format, truncated, corrupted): ezdxf's own
  parse failure is caught and reported as "Could not read DXF file: not a valid DXF file." — no
  crash, same error-state convention as every other failure mode here.
- A `path` that does not exist or cannot be opened (permissions, etc.): "Could not open DXF file:
  <OS error message, truncated to the existing 160-character convention `wiring.py` already uses>."
- Z-coordinates (DXF group code 30) on any entity are read and **ignored**; every entity is treated
  as flattened onto its own X/Y plane regardless of any Z value present — consistent with "2D
  cross-section" being this feature's entire scope, not validated or rejected if Z varies across a
  loop's vertices.
- A self-intersecting (non-simple) closed polyline: the shoelace-formula family assumes a simple
  polygon. This phase does not detect self-intersection; a self-intersecting input produces a
  mathematically meaningless but non-crashing numeric answer. Flagged as a known limitation, not
  fixed here (self-intersection detection is a separate computational-geometry check, not attempted
  in either this phase or spec 014).
- The file is re-read and re-parsed on every recalculation pass, same as "Value"/"Formula" re-parse
  their `expr` every pass — no caching in this phase. Acceptable for this phase's scope; flagged as a
  possible future optimisation only if real files turn out large enough to matter.
- `BLOCK`/`INSERT` entities anywhere in the file are never traversed (not resolved, not flattened,
  not treated as an error) — entities inside a block definition are simply invisible to this
  component's entity search, exactly like today's "no rendering, no block resolution" scope (A.6).
- Feeding a `cad-profile` output with units into an incompatible operation (e.g. a "Formula"
  component computing `area + 1`, mixing mm² with a dimensionless `1`) fails with the engine's
  existing "Units do not match" message — no special-casing needed, because this kind's outputs are
  ordinary unit-bearing SymPy values (see "Fits current architecture?").

## IP check
Pass, with one new-dependency flag for explicit sign-off. All sources above are either (a) a
vendor's own *published, documented interchange format* read for interoperability — the same
category of activity as reading CSV/PDF, not decompilation or reverse-engineering, and explicitly
not on IP-POLICY's forbidden-formats list (Mathcad/Mathematica/Maple's *proprietary, undocumented*
formats) — or (b) decades-old, textbook, public-domain statics/mechanics-of-materials mathematics,
cross-checked across two independent sources, not distinctive to any one software product. The word
"AutoCAD" appears only once above, nominatively, describing DXF's origin, consistent with
IP-POLICY's "factual comparison in docs is OK, keep it minimal and nominative" clause, and does not
appear in any product-facing string below (component-kind label "CAD profile (DXF)," config keys
`path`/`layer`/`unit`, every error message) — "DXF" alone is used the same way "CSV"/"PDF" already
are. **New dependency flag**: this spec adds `ezdxf` (MIT, 1.4.5, confirmed via the research note) as
a new core runtime dependency — not yet on the project's approved-dependency list (`decisions.md`,
2026-10-27 covers numpy/scipy only) — so needs the same explicit manager/Theo sign-off those got
before a developer installs it; only the base `ezdxf` package, never the optional `ezdxf[draw]`
extras (which pull in `numpy`-adjacent drawing helpers and `PyQt5` — a second, redundant Qt binding
that must never sit alongside PySide6). `ezdxf`'s own transitive dependencies (`numpy`, already
approved; `pyparsing`, `fonttools`, both MIT; `typing_extensions`, Python Software Foundation
Licence) are all permissive — no GPL/AGPL anywhere in the chain (recommend the developer re-verify
the live licence at actual `pip install` time regardless, per the research note's own "don't trust
memory" instinct). No vendor UI, icon set, workflow, help text, example drawing, or branding is
referenced or implied-as-compatible anywhere in this spec. Not legal advice.

## Fits current architecture?
- **`pyproject.toml`**: add `"ezdxf>=1.4,<2"` to `dependencies` (core, not an optional extra).
- **New `livesheet/engine/cadprofile.py`** (GUI-independent, no PySide6 import, consistent with
  `engine/`'s existing boundary):
  - `INSUNITS_TO_UNIT: dict[int, str]` — the table above, own naming of a publicly documented header
    field.
  - `CadProfileError(ValueError)` — this kind's own exception type for every error message above.
  - `read_profile(path: str, layer: str, unit: str) -> tuple[list[tuple[float, float]], str]`:
    opens the file via `ezdxf.readfile(path)`, applies the `layer` filter, finds the one closed
    straight-sided polyline candidate per the rules above (raising `CadProfileError` for every
    zero/multiple/scope-boundary case), resolves the unit (override, or `$INSUNITS` via the table,
    or `CadProfileError`), and returns `(vertices, resolved_unit_name)`.
  - `section_properties(vertices: list[tuple[float, float]]) -> SectionProperties` — a
    `@dataclass` with every output above as a plain `float` field, implementing exactly the formulas
    in "Behaviour," as a **pure function over plain floats**, with no `ezdxf`, no SymPy, no `Engine`
    dependency at all. This keeps the actual engineering math independently unit-testable against
    the hand-worked triangle numbers without needing a DXF file, ezdxf, or the wiring graph — the
    acceptance criteria's numeric example is this function's own first unit test.
- **`livesheet/engine/wiring.py`**:
  - `_PORTS["cad-profile"] = lambda config: ([], ["area", "centroid_x", "centroid_y", "Ixx", "Iyy",
    "Ixy", "J", "rx", "ry", "Sx_top", "Sx_bottom", "Sy_left", "Sy_right", "outline"])`.
  - `_COMPUTE["cad-profile"] = _compute_cad_profile`: calls `cadprofile.read_profile(...)` then
    `cadprofile.section_properties(...)`, and builds each scalar output as a plain SymPy expression
    — the raw float magnitude times the appropriate power of `UNITS[resolved_unit]` (power 1 for
    `centroid_x`/`centroid_y`/`rx`/`ry`, 2 for `area`, 3 for the four `S*` ports, 4 for
    `Ixx`/`Iyy`/`Ixy`/`J`) — **exactly the same value shape `Engine.parse` already produces** for a
    plain measurement literal like `12 mm`, so `format_output`, `measure()`, and a downstream
    "Formula" component's environment need zero special-casing for this kind (criterion 10 exercises
    this directly). `outline` is built as an `sp.Matrix` with one row per vertex, each row
    `[x*UNITS[resolved_unit], y*UNITS[resolved_unit]]` — the same unit-bearing-matrix value shape
    spec 002 already defines for a mixed/homogeneous matrix of quantities.
  - `evaluate()`'s existing `except (StatementError, UnitError):` clause gains `CadProfileError`
    (imported from `cadprofile`) to the tuple — a one-line, additive change; everything else in that
    function (topological order, upstream-error propagation, unknown-kind handling) is untouched.
- **`livesheet/document.py`**: no change. `RegionData.component_kind` is already a free-form string
  and `config: dict[str, str]` is already generic (spec 009's own design intent for exactly this —
  see that spec's open question 6); `FORMAT_VERSION_COMPONENTS` stays at `3`.
- **`livesheet/gui/componentdialog.py`**:
  - `_KIND_LABELS` gains `"CAD profile (DXF)"`; `_KIND_BY_LABEL["CAD profile (DXF)"] = "cad-profile"`.
  - `ComponentFields` gains `cad_path: str = ""`, `cad_layer: str = ""`, `cad_unit: str = ""`.
  - `fields_to_config` gains a `kind == "cad-profile"` branch returning
    `{"path": fields.cad_path.strip(), "layer": fields.cad_layer.strip(), "unit":
    fields.cad_unit.strip()}`.
  - `validate_component_fields` gains a branch requiring `cad_path` non-blank ("File path is
    required") — mirroring how "Formula"'s `expr` is only checked for non-blankness here, not
    evaluability; whether the path actually opens/parses is an evaluation-time concern, same
    division of labour spec 009 already uses.
  - `AddComponentDialog._build_cad_profile_page()`: three labelled fields in a `QFormLayout` — a
    "Path:" row with a `QLineEdit` plus a "Browse…" button opening a standard
    `QFileDialog.getOpenFileName(self, "Open DXF file", "", "DXF files (*.dxf)")` (the same generic
    file-chooser chrome the app already uses for Open/Save As — not a new interaction style, no new
    dependency); a "Layer (optional):" row, plain `QLineEdit`; a "Unit (optional):" row, plain
    `QLineEdit` with placeholder text `"auto from file"` so the override-vs-default relationship is
    visible without a separate help dialog.
- **Tests**:
  - `tests/test_cadprofile.py`: `section_properties()` against the hand-worked triangle numbers
    above, plus a degenerate (collinear/zero-area) case — pure-Python, no DXF file, no Qt.
  - `tests/test_wiring_cadprofile.py`: engine-level, covering acceptance criteria 2-11 through
    `wiring.evaluate(...)`. Fixture `.dxf` files are **generated at test time via ezdxf's own write
    API** (`ezdxf.new()`, `.modelspace().add_lwpolyline(...)`, `doc.header['$INSUNITS'] = ...`,
    `doc.saveas(tmp_path / "...")`) — never a hand-authored raw-tagged-text file and never anyone
    else's example file, so there is no copied-content question at all; this also keeps the fixtures
    trivially correct (ezdxf's own writer guarantees well-formed output).
  - GUI-level: extend `tests/test_wiring_gui.py` with the new dialog page's field round-trip (kind
    selection, Browse-button file dialog mocked the same way existing Open/Save-As tests already
    mock `QFileDialog`, OK → config dict), headless under `QT_QPA_PLATFORM=offscreen`.
  - Tester's real-window pass: place a "CAD profile (DXF)" component, Browse to a small on-disk test
    file, confirm the output values and the error states (bad path, bad unit) render live, wire
    `area` into a "Formula" component and confirm the value flows through.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **New dependency sign-off**: `ezdxf` needs the same explicit go-ahead numpy/scipy received
   2026-10-27 before a developer installs it — this is Theo's call, not mine to make. [Recommend
   approving: MIT, clean permissive dependency chain, already verified twice (research note +
   re-stated above).]
2. **Section modulus (four ports) and `outline` (exposed now)**: both decided above rather than
   left open, per the task's instruction; flagging the decisions themselves for visibility in case
   the manager wants the simpler one-section-modulus-value convention, or wants `outline` deferred
   until a consumer exists.
3. **Phase split narrower than the research note's own suggestion**: this spec restricts phase 1 to
   a single closed straight-sided `LWPOLYLINE`/`POLYLINE` only, pushing `LINE`-entity chaining into
   spec 014 alongside curve tessellation and multi-loop holes — the research note's A.8.4 only
   separated "`LWPOLYLINE`-only" from "add `ARC`/`CIRCLE` + multi-loop" and did not call out
   `LINE`-chaining as its own concern. Flagging this restructuring explicitly (reasoning: `LINE`-
   chaining is a graph-assembly problem of comparable complexity to curve tessellation, not closer
   in kind to this phase's "given a clean polygon, compute its properties" math) for the
   manager/Theo to confirm rather than silently deviating from the earlier recommendation.
