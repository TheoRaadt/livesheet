# 014 DXF profile import, phase 2: curved entities, line-chaining and composite (hole) sections

Builds on `docs/board/specs/013-dxf-profile-import-core.md` (read that spec first — this one does
not repeat its config contract, output-port list, or property-math formulas; it only extends *which
raw DXF geometry can be turned into one or more closed loops* before 013's already-specified math
runs on them). Still backlog M6 item 35 / "32b" (see 013's own framing note).

Source inspiration (concept only, nothing copied — continuing the same, already-dated research
trail as 013; no new sources read for this spec beyond re-applying what was already cited):
- Autodesk's own published DXF format reference index and Wikipedia's "AutoCAD DXF" overview (same
  two citations as spec 013, accessed 2026-10-30) — specifically the publicly documented meaning of
  the `LWPOLYLINE` "bulge" value (group code 42: `bulge = tan(included_angle / 4)` for the arc that
  replaces an otherwise-straight segment from one vertex to the next, a signed value — positive for
  a counter-clockwise arc, negative for clockwise) and of `ARC`/`CIRCLE` entities (centre, radius,
  start/end angle in degrees). Read as interoperability reference for a documented format, same
  posture as spec 013; "AutoCAD" again appears only in this nominative sentence, never in any
  product-facing string below.
- General curve-flattening ("tessellate an arc into short straight segments") and composite-section
  ("outer boundary minus hole, by summing signed sub-areas") are both decades-old, generic ideas
  already cited in the research note (A.4, A.6) and in `.claude/skills/modeling-concepts/SKILL.md`'s
  broader framing — not tied to any one CAD or CAS vendor.
- `docs/board/specs/013-dxf-profile-import-core.md` for the component kind, config contract, and
  property-math formulas this spec extends rather than repeats.

Scope note: this phase adds, to the single `"cad-profile"` component kind — **no new config keys,
no new output ports, no `.lsheet` format change** beyond what 013 already made:
(a) standalone `ARC` and `CIRCLE` entities, tessellated into straight segments;
(b) `LWPOLYLINE`/`POLYLINE` segments with a nonzero bulge (an arc replacing a straight segment),
tessellated the same way;
(c) loop assembly from a set of separate `LINE` entities that chain end-to-end into one closed loop;
(d) more than one closed loop on the same drawing forming one composite (hollow/tube/box) section —
exactly one outer loop plus zero or more holes.
Estimated size: about 2.5-3 days (three independent geometry-assembly algorithms — tessellation,
chaining, composite validation — each with its own edge cases and tests, on top of 013's
already-built property math, which needs only a shape change from "one loop" to "a list of loops").

---

## User story
As a LiveSheet user, I want to import a cross-section drawn with arcs, circles, or separate line
segments — or a hollow section like a tube or a box beam, drawn as an outer boundary with one or
more holes — and get the same area/centroid/second-moment/section-modulus numbers spec 013 already
gives for a simple straight-sided outline, without having to redraw my section as a single
hand-closed polyline first.

## Behaviour (own words)

### Tessellating `ARC` and `CIRCLE` entities (own fixed, deterministic rule — not a library default)
Because LiveSheet does not install ezdxf's optional drawing/rendering extras (013's IP check), no
third-party tessellation routine is used or available; this spec defines its own small, fully
deterministic rule so results are exactly reproducible and independently testable:

- The maximum angular step is a fixed internal constant, **10 degrees per segment**, not exposed as
  user configuration in this phase (see Open questions).
- For a `CIRCLE` entity (centre `(cx, cy)`, radius `r`): `segment_count = ceil(360 / 10) = 36`
  vertices, sampled at angles `k * (360 / segment_count)` degrees for `k = 0..35`, measured
  counter-clockwise from the direction of the entity's own local +X axis (i.e. `k = 0` is the point
  at `(cx + r, cy)`) — a full closed loop of 36 points on its own, no separate "closing" point (the
  same "N points for an N-gon, wrap implicitly" convention `LWPOLYLINE` vertex lists already use).
- For an `ARC` entity (centre, radius, `start_angle`, `end_angle`, both in degrees, arc always
  running counter-clockwise from start to end per the DXF convention): let
  `included = (end_angle - start_angle) mod 360` (so a full-circle-equivalent `ARC` is treated the
  same as `360`); `segment_count = max(1, ceil(included / 10))`; sample `segment_count + 1` points
  at `start_angle + j * (included / segment_count)` for `j = 0..segment_count`, which lands exactly
  on the true start and end points (important so the arc's flattened chain connects cleanly to
  whatever straight geometry meets it, with no gap or overlap).
- A `LWPOLYLINE`/`POLYLINE` segment with a nonzero bulge `b` between vertex `v0` and the next vertex
  `v1` is converted to its equivalent arc (`included_angle = 4 * atan(|b|)`, direction
  counter-clockwise if `b > 0` else clockwise, centre and radius derived from `v0`, `v1` and
  `included_angle` by the standard chord/sagitta relationship) and tessellated by the same rule as a
  standalone `ARC`, contributing its `segment_count - 1` intermediate points between the existing
  `v0`/`v1` vertices already in the loop's vertex list (no duplicate endpoints).
- A `CIRCLE` of radius 10 (any unit) therefore tessellates to a 36-gon of area `0.5 * 36 * 10^2 *
  sin(10°) ≈ 312.567` (same unit²) rather than the continuous-circle value `π*10^2 ≈ 314.159` — a
  small (~0.5%), expected, documented discretisation difference from this spec's own fixed 10°
  step, not a bug, and exactly what the acceptance criteria below check for.

### Assembling a loop from separate `LINE` entities
After the `layer` filter, every standalone `LINE` entity's two endpoints are treated as nodes in an
undirected graph (one edge per `LINE`), with two endpoints considered "the same node" when they
match within a fixed internal tolerance (`1e-6` in the file's own native drawing units, not exposed
as config in this phase — see Open questions). A set of `LINE` entities assembles into exactly one
closed loop when: there is exactly one connected component, every node has degree exactly 2, and
walking the graph from any node returns to it after visiting every node exactly once (i.e. it is a
single simple cycle, not, e.g., a figure-eight or an open chain with one dangling end). If these
conditions hold, the loop's vertex order is the walk order. Otherwise: error "Could not assemble a
single closed loop from LINE entities on this layer." — not a crash, not a best-effort guess.

### Multiple closed loops: composite (outer + holes) sections
Once tessellation and `LINE`-chaining above produce the full set of candidate closed loops on the
filtered entity set (this now includes loops from a closed straight-sided `LWPOLYLINE` as in 013,
loops containing tessellated arcs/bulges, and loops assembled from chained `LINE` entities, all
treated uniformly from this point on), this phase changes how more than one candidate is handled —
**superseding spec 013's own "2+ candidates is always ambiguous" rule (013's acceptance criterion
6) for exactly the case this composite check accepts**:

1. If there is only one candidate loop: behaves exactly as spec 013 already specifies (single-loop
   case, winding sign only matters internally for the centroid/moment formulas, `area`'s own output
   is the absolute value).
2. If there are two or more candidate loops, this phase first checks whether they form a valid
   **single outer loop plus zero or more holes**:
   - The loop with the largest `abs(signed_area)` is the candidate **outer** loop; it must be wound
     **counter-clockwise** (`signed_area > 0`).
   - Every other loop is a candidate **hole**; each must be wound **clockwise**
     (`signed_area < 0`), and each one's own axis-aligned bounding box must sit entirely inside the
     outer loop's bounding box (a cheap containment sanity check — not a full point-in-polygon test;
     see Open questions for why this is a deliberately conservative middle ground).
   - If every check above passes, the composite section is computed: area, centroid and every
     second-moment-family output are the ordinary **signed sum** across all loops (A.4's own
     "composite section = sum of signed sub-areas" idea — 013's formulas are unchanged, they are
     just applied once per loop and summed before the parallel-axis/extreme-fibre steps, see "Fits
     current architecture?"). `area`'s own output port is still the absolute value of that signed
     sum (same convention as the single-loop case).
   - If any check fails (a second loop also wound counter-clockwise, i.e. two candidate outers; a
     clockwise loop not contained in the outer's bounding box), this is reported as one of the two
     new error states below — **not** 013's generic "multiple profiles found" message, since a more
     exact diagnosis is now available:
     - A loop other than the single largest is also counter-clockwise, or the one largest loop is
       clockwise: "Loop winding does not match the outer/hole convention (outer counter-clockwise,
       inner clockwise); check this profile's winding direction."
     - A clockwise loop's bounding box is not fully contained in the outer's: "A hole loop extends
       outside the outer profile's boundary."
3. Multiple separate outer bodies (e.g. two unconnected rectangles, each possibly with its own
   holes, on the same drawing) are explicitly **out of scope** for this phase — they fail the "only
   one counter-clockwise loop allowed" check above and surface as the winding-mismatch error, even
   though a human would read the drawing as "two separate valid profiles, not one profile with a
   winding mistake." Flagged as a known limitation in Open questions, not silently handled.

### `outline` with multiple loops
When the composite path above produces more than one loop, the `outline` output port (013) is the
single N_total×2 matrix formed by concatenating every loop's own tessellated vertex list, outer loop
first, then each hole loop in the order it was found — there is no way to tell from the matrix alone
where one loop's vertices end and the next begin. Flagged explicitly as a limitation in Open
questions (not fixed here, since `outline` has no real consumer yet regardless — see 013's own open
question 2) rather than silently leaving the shape ambiguous without saying so.

## Syntax proposal (own keywords)
N/A — same as 013, no new statement syntax; this phase only changes what spec 013's existing
`"cad-profile"` kind can parse out of a DXF file's geometry.

## Acceptance criteria
1. **Full circle, tessellation only**: a fixture containing one standalone `CIRCLE` entity, centre
   `(0, 0)`, radius `10`, `$INSUNITS = 4` (mm), nothing else. `area = 312.567 mm²` (the 36-gon value
   above, not `π*10² = 314.159`), `centroid_x = 0`, `centroid_y = 0`; `P1` is not in an error state.
2. **Bulge arc, tessellation + implicit closing segment**: a fixture with one closed `LWPOLYLINE`
   of exactly two vertices, `(-10, 0)` with bulge `1.0` and `(10, 0)` with bulge `0`, `$INSUNITS = 4`
   (mm) — bulge `1.0` is exactly a 180° (semicircular) arc (`tan(45°) = 1`), so vertex `(-10, 0)`'s
   segment to `(10, 0)` is the upper semicircle (counter-clockwise from `(-10,0)` through `(0,10)`
   to `(10,0)`) and the closing segment back is the straight diameter. Hand-derived:
   `area = 900 * sin(10°) ≈ 156.283 mm²` (compare the continuous half-disk's `0.5*π*10² ≈ 157.080`,
   same ~0.5% discretisation gap as criterion 1, for the same reason).
3. **`LINE`-chaining**: a fixture with four separate `LINE` entities forming a 40×20 mm rectangle —
   `(0,0)-(40,0)`, `(40,0)-(40,20)`, `(40,20)-(0,20)`, `(0,20)-(0,0)` — on one layer, `$INSUNITS = 4`.
   Chained into one closed loop; `area = 800 mm²`, `centroid_x = 20 mm`, `centroid_y = 10 mm`,
   `Ixx = 26666.7 mm⁴` (`40*20³/12`), `Iyy = 106667 mm⁴` (`20*40³/12`) — independently cross-checked
   against the standard rectangle second-moment formulas, not just 013's own shoelace formulas.
4. **`LINE`-chaining failure**: the same four `LINE` entities but with the third one shortened so it
   no longer reaches `(0,20)` (leaving a gap): error "Could not assemble a single closed loop from
   LINE entities on this layer."
5. **Composite (hole) section**: a fixture with the 40×20 mm outer rectangle from criterion 3 (as a
   single closed straight-sided `LWPOLYLINE`, counter-clockwise) plus a second closed
   straight-sided `LWPOLYLINE`, a 10×10 mm square from `(15,5)` to `(25,15)` (centred inside the
   outer rectangle), wound clockwise — both on the same layer, no `layer` filter needed.
   `area = 700 mm²` (`800 - 100`); `centroid_x = 20 mm`, `centroid_y = 10 mm` (unchanged from the
   outer rectangle alone, by symmetry — both shapes share the same centroid); `Ixx = 25833.3 mm⁴`
   (`26666.7 - 10*10³/12`), `Iyy = 105833.3 mm⁴` (`106667 - 10*10³/12`, the hole's `Ixx`/`Iyy` are
   equal to each other since it is a square).
6. **Winding mismatch**: the same fixture as criterion 5 but with the hole square also wound
   counter-clockwise: error "Loop winding does not match the outer/hole convention (outer
   counter-clockwise, inner clockwise); check this profile's winding direction."
7. **Containment failure**: the same fixture as criterion 5 but with the hole square moved to
   `(35,5)-(45,15)` (sticking out past the outer rectangle's right edge, `x = 40`): error "A hole
   loop extends outside the outer profile's boundary."
8. **013 regression check**: every acceptance criterion in spec 013 still passes unmodified after
   this spec's changes — 013's single-loop, straight-sided-only cases are the `len(loops) == 1`
   special case of this spec's more general loop-assembly/composite path, not a separate code path
   that could silently diverge.

## Edge cases
- Multiple separate outer bodies on one drawing (see "Behaviour" point 3 above): explicitly out of
  scope, surfaces as the winding-mismatch error even though a human would read it differently.
  Flagged in Open questions, not fixed.
- A hole loop that is itself degenerate (zero area, e.g. collinear points): same "Profile has zero
  area"-style check as 013 applies, now applied per-loop before the composite assembly runs, so one
  bad hole doesn't silently distort the composite sum.
- An `ARC`/`CIRCLE`/bulge whose radius is extremely small relative to the fixed 10° tessellation
  step still produces a numerically valid (if visually coarse) polygon — no minimum-radius
  validation is added in this phase.
- A `LWPOLYLINE` that mixes some zero-bulge (straight) and some nonzero-bulge (arc) segments is
  fully supported here (013 only handled the all-straight case) — straight segments contribute their
  two endpoints directly, bulge segments contribute their tessellated intermediate points, in the
  same single combined vertex list.
- Self-intersection detection remains out of scope for both loops and the composite assembly, same
  limitation 013 already flagged — not revisited here.

## IP check
Pass, no new dependency beyond 013's already-flagged `ezdxf` (bulge/arc/circle data is exposed by
ezdxf's own `LWPOLYLINE`/`ARC`/`CIRCLE` entity APIs, already confirmed available in the research
note's A.3). The bulge-value formula (`tan(included_angle/4)`) is read from DXF's own published,
documented group-code meaning (same interoperability posture as every other DXF field used in this
feature, cited above and in 013); curve tessellation and composite-section-by-signed-summation are
both generic, decades-old ideas (A.4, A.6) independent of any named CAD or CAS vendor. "AutoCAD"
appears only nominatively, in the source citation above, and nowhere in any product-facing string.
No vendor UI, icon, workflow, or example drawing was read or used as a source. Not legal advice.

## Fits current architecture?
- **`livesheet/engine/cadprofile.py`** (extends 013's module, no new file):
  - `read_profile`'s candidate-finding step gains: `ARC`/`CIRCLE` tessellation, bulge-segment
    tessellation inside `LWPOLYLINE` vertex processing, and a `LINE`-chaining assembly pass — each
    its own small, independently testable pure function over coordinates (no ezdxf objects passed
    into the chaining/tessellation math itself, same "pure function over floats" discipline 013's
    `section_properties` already established).
  - `section_properties` is generalised from `vertices: list[tuple[float, float]]` to
    `loops: list[list[tuple[float, float]]]` — computing each output as the signed sum across loops
    before the centroid-divide/parallel-axis/extreme-fibre steps (exactly the composite-section
    maths in "Behaviour" above); 013's existing single-loop call becomes `section_properties([one_
    loop])`, so **013's own acceptance criteria require no code-path change**, only a wrapping list
    — directly supporting this spec's own criterion 8 regression check.
  - New `assemble_loops(entities, layer) -> list[list[tuple[float, float]]]` replaces 013's
    "find the one candidate" step with "find every candidate loop" (straight polylines, bulge
    polylines, tessellated standalone arcs/circles, and `LINE`-chained loops, uniformly), followed by
    the outer/hole validation step described above, raising `CadProfileError` for every failure mode
    listed in "Behaviour" and "Acceptance criteria."
  - `read_profile` calls `assemble_loops` and, for the single-loop case, behaves exactly as 013
    already specifies (unit resolution, the zero/one/many-candidate messages where they still apply
    — "zero candidates" and "unit resolution" are unchanged by this spec; only the ">1 candidate"
    branch is replaced by the composite check above).
- **`livesheet/engine/wiring.py`**: no change beyond 013's own — `_compute_cad_profile` already
  calls `cadprofile.read_profile(...)`/`cadprofile.section_properties(...)` without caring how many
  loops were involved internally; `CadProfileError`'s new messages are already caught by 013's
  widened `except` clause.
- **`livesheet/document.py`**, **`livesheet/gui/componentdialog.py`**: no change — same config keys,
  same dialog fields as 013; this spec is purely an `engine/cadprofile.py` extension.
- **Tests**:
  - `tests/test_cadprofile.py` gains: the circle/bulge tessellation numbers (criteria 1-2, pure
    functions, no DXF file needed to test the tessellation math itself), the `LINE`-chaining graph
    logic (valid rectangle, and the broken-chain failure), and the composite outer/hole validation
    logic (valid hole, winding mismatch, containment failure) — each as a focused pure-Python test
    independent of ezdxf/the wiring graph, mirroring 013's own test structure.
  - `tests/test_wiring_cadprofile.py` gains the same criteria exercised end to end through
    `wiring.evaluate(...)`, with fixtures again generated at test time via ezdxf's own write API
    (`add_arc`, `add_circle`, `add_line`, `add_lwpolyline` with explicit bulge values) — never a
    hand-authored or copied file, same discipline as 013.
  - Tester's real-window pass: import a drawing with a circular or bulged profile and one with a
    hole, confirm the component's outputs and the new error messages render live.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Fixed, non-configurable 10°-per-segment tessellation step**: a judgment call made here rather
   than left open, flagged for visibility — a future spec could expose a `tessellation-degrees`
   config key if real drawings need finer control (e.g. very small-radius fillets in a section with
   otherwise large overall dimensions), but that is not attempted now to keep this phase's scope
   from growing further.
2. **The outer/hole composite rule (largest-counter-clockwise-loop + bounding-box-contained
   clockwise holes) is a deliberately conservative middle ground**, explicitly not full
   point-in-polygon containment and explicitly not supporting multiple disconnected outer bodies on
   one drawing (see "Behaviour" point 3 and its Edge case). This is the single judgment call in this
   spec most likely to need revisiting once real mechanical drawings are tried against it — flagging
   clearly rather than presenting it as the only possible design.
3. **`LINE`-chaining's fixed `1e-6`-native-unit coordinate-matching tolerance**: may need tuning once
   real, possibly imprecisely-exported files are tried (DXF files generated by different CAD tools
   or round-tripped through conversions sometimes have small endpoint gaps); not exposed as
   configuration in this phase; flagged as a number to watch rather than a settled constant.
4. **`outline`'s multi-loop concatenated-matrix shape** (no way to tell, from the matrix alone, where
   one loop's vertices end and the next begin): flagged above as a real limitation, acceptable only
   because `outline` has no actual consumer yet (013's own open question 2) — whoever eventually
   wires a `cad-profile` output into a `PlotRegion` will need to revisit this, possibly by splitting
   into per-loop ports or by introducing some structured value type the engine does not have today.
