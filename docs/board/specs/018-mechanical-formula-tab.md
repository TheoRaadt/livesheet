# 018 Mechanical-engineering formula tab (quick-insert, SI units only)

Spec-numbering note: this is being written in parallel with two sibling specs for backlog
items 40 (electrical) and 41 (chemical), which may independently claim 018/019. If a
collision is discovered later, this file follows the project's existing convention (see
specs 008/010/015/016's own notes): the file that was renumbered leaves a one-line stale
pointer stub at its old path, nothing is overwritten.

Source inspiration (concept only, nothing copied):
- Backlog item 39 (M8, Theo's request 2026-11-01) and `docs/board/specs/011-side-panel-
  category-tabs.md` (this project's own already-shipped, already-IP-reviewed tab/
  quick-insert-button mechanism — `MATH_TOKENS`'s `(category, label, token, tip)` shape,
  `TAB_CATEGORIES`, `TAB_ORDER`, `PLACEHOLDER_TABS`, `_build_placeholder_tab`,
  `insert_token`). This spec is a content-and-data follow-up to 011's chrome, exactly the
  way 011 itself said Statistics/Optimization/Outline/Data tabs were left as "an obvious
  home for a future spec's own content to slot into" — reused verbatim here, not a new
  mechanism.
- Generic, standard, centuries-old engineering-mechanics formulas and terminology, the
  common ground of any introductory statics/mechanics-of-materials course or reference,
  independently confirmed against public encyclopedic and course sources (concept/formula
  only; nothing quoted beyond a term's own name): Wikipedia "Stress (mechanics)", "Strain
  (mechanics)" [consulted as "Deformation (physics)"], "Hooke's law", "Bending" (fetched in
  full 2026-11-01, confirms the flexure formula's variable meanings: bending moment,
  distance from neutral axis, second moment of area), "Shear stress" (fetched in full
  2026-11-01, confirms both the average-shear and transverse-beam-shear formulas and their
  variable meanings), "Thermal expansion" (fetched in full 2026-11-01, confirms the linear
  thermal-expansion formula), "Factor of safety", "Friction" (Coulomb's law of dry
  friction), "Torque"/"Moment (physics)", "Resultant force", "Center of mass" (all
  independently well-established, decades-to-centuries-old physics identical across every
  source consulted, accessed 2026-11-01).
- MIT OpenCourseWare, 2.001 "Mechanics & Materials I"
  (https://ocw.mit.edu/courses/mechanical-engineering/2-001-mechanics-materials-i-fall-2006/,
  accessed 2026-11-01) — confirmed only the generic, public curriculum structure ("Part 1:
  Statics — Elements of Equilibrium" followed by stress/strain/linear-elasticity/thermal-
  expansion/failure topics), used here solely as grounding for *this spec's own choice* of
  sub-category split (Statics, then Strength of Materials) in a standard public ME
  curriculum, not any one vendor's own packaged tab/category naming.
- A general web search surfaced several independent public formula-sheet/study-guide
  pages (course notes, flashcard sites) corroborating the same standard formulas and the
  `sigma = P/A` (axial load `P`, area `A`) convention and the Coulomb-friction
  `f_s <= mu_s * N` form; used only as independent corroboration that these are
  standard, widely-taught forms, not copied from any one source, and not from any named
  commercial math/engineering tool's own formula palette, Quick Sheets, or worksheet
  library (none consulted, per the ip-cleanroom skill's explicit instruction).
- Everything below (keyword/variable names, the specific naming workaround described in
  "Why these variable names, not the more obvious ones", categorization, phasing, tooltip
  wording, numeric examples) is this spec's own design, independent of any one source.

Size: one phase, about 1.5-2 days (pure data/content addition to an already-shipped,
already-reviewed GUI mechanism — no new widget type, no engine code change, no
`.lsheet` format change). Deliberately narrow first phase; see "Deferred" below.

---

## User story
As an engineer using LiveSheet for a calculation sheet, I want a side-panel tab of
standard mechanical-engineering formulas (stress, strain, moments, friction, ...) that I
can insert with one click, the same way I already insert `∫` or `√` from the Calculus/
Algebra tabs, instead of having to recall or re-derive a formula's exact symbolic form by
hand every time. I want these formulas to use SI units throughout (no imperial/US
customary units), matching LiveSheet's own existing unit system.

## Behaviour (own words)

### Mechanism: reuse spec 011's existing tab/button plumbing exactly
This is a content addition to the already-shipped, already-approved mechanism from spec
011, not a new one:
- A new functional tab, **Mechanical**, added to `TAB_ORDER` (position: see Open question
  1 — this spec's own recommendation is right after Optimization, before Outline/Data).
- `TAB_CATEGORIES["Mechanical"] = ("Statics", "Strength of Materials")` — two sub-category
  groups in this phase, shown with the same small grey sub-header labels the Elements tab
  already uses (spec 011's existing rule: a tab backed by more than one category keeps
  sub-headers), for the same reason — a 15-button tab stays scannable.
- Each formula is one more `(category, label, token, tip)` tuple appended to the existing
  `MATH_TOKENS` list (or a separate list merged into it at startup — developer's choice,
  same freedom spec 011 already gave for internal data layout). Clicking a formula button
  calls the exact same `insert_token(token)` callback every existing button already uses:
  a region is created/focused and the token text is inserted at the cursor. **No new
  widget, no dialog, no on-canvas placeholder editing** — this keeps the feature inside
  the "boring, generic toolkit chrome" posture ip-cleanroom rule 6 asks for, and it is the
  same mechanism this project already has, so there is nothing new to IP-review on the
  interaction side.

### What a button inserts: a bare symbolic template, not a filled-in example
Per Theo's open design question, this spec's own choice is: **a bare formula template**,
e.g. clicking "Moment of a force" inserts the literal text `M := P*d` — a working `:=`
definition using mnemonic symbol names, with **no numbers and no units attached**, for the
user to make use of by defining `P` and `d` themselves elsewhere on the sheet (in whatever
unit they choose; LiveSheet's existing dimension-checked unit system, not this spec, does
the unit conversion/validation once they do). This mirrors how the user already works
with every other quick-insert token (e.g. clicking `∫` inserts `integrate(` for the user to
complete) — nothing richer (no dialog asking for each symbol's value, no inline
placeholder editing on the canvas) is proposed, consistent with the same patent-caution
posture spec 005 was superseded for. Each button's **tooltip** names the formula in full,
states what every symbol means, and states the **SI unit each symbol is expected to carry**
(e.g. "P in N; d in m; M in N·m") — this is where the "SI units only" instruction actually
shows up, since the inserted *template itself* is deliberately unit-agnostic symbol names
(a definition's right-hand side does not carry a unit by itself; the unit arrives only once
the user assigns an actual value, e.g. `P := 500 N`, to a symbol used by the template).

### Why these variable names, not the more obvious ones
While drafting the formula list, this specialist found a real, already-existing
engine behaviour that any formula-template tab (this one or the parallel electrical/
chemical ones) must design around, not just a style preference:

`livesheet/engine/evaluator.py`'s `Engine.evaluate()` seeds the evaluation namespace with
`env = dict(UNITS)` — i.e. every one of `engine/units.py`'s unit abbreviations (`N`, `A`,
`F`, `V`, `T`, `W`, `C`, `H`, `L`, ... and more) is already bound, before the user defines
anything, to a concrete dimensioned value. `_check_defined()` — the function that produces
the friendly `"<name> is not defined"` error a user would expect to see from an unfilled
template — only inspects the `free_symbols` left over *after* parsing; a bare symbol that
happens to match a `UNITS` key has **no** free symbols left, so it is never reported as
undefined. Concretely: a template using bare `F` for "force" or bare `A` for "area" would,
on a sheet where the user has not yet defined `F`/`A` themselves, silently evaluate `F`
as the Farad unit and `A` as the Ampere unit instead of erroring — producing a
plausible-looking but meaningless dimensioned number with **no error at all**, defeating
the entire "insert the bare formula, fill in the blanks" design this spec relies on. (`I`
has the same problem one level up: it is separately bound in `BUILTINS` as the imaginary
unit `sp.I`, not even via `UNITS`.) Verified directly against this project's own source
(`evaluator.py`'s `_builtins()`/`_check_defined()`/`Engine.evaluate()`), not from any
vendor material.

Because of this, every symbol name used below was deliberately checked against
`engine/units.py`'s `UNITS` dict keys and `evaluator.py`'s `BUILTINS` keys and chosen to
**never** be an exact match (sympy's tokenizer never splits one multi-character identifier
back into known sub-tokens — e.g. `Ac`, `Fn`, `dT` are each safely one token — only a
*bare, exact* name collision is dangerous):
- Generic applied force/load: **`P`** (not `F`, which collides with the Farad unit letter;
  `P` for axial/applied load is itself a standard textbook symbol, confirmed by the public
  sources above, so this is not an invented workaround-only name).
- Cross-sectional area: **`Ac`** (not bare `A`, which collides with the Ampere unit
  letter).
- Transverse shear force: **`Fv`** (not bare `V`, which collides with the Volt unit
  letter; keeps the `F`-prefixed-component family already used by `Fx`/`Fy`/`Fn`/`Ff`
  below).
- Second moment of area: **`Ix`** (not bare `I`, which collides with the reserved
  imaginary-unit constant).
- Normal (contact) force in the friction formula: **`Fn`** (not bare `N`, which collides
  with the Newton unit letter).
- Every other symbol below (`M`, `d`, `theta`, `mu_s`, `x_cg`, `m1`/`x1`/`m2`/`x2`,
  `sigma`, `epsilon`, `E`, `y`, `tau`, `Q`, `b`, `dL`, `L0`, `alpha_t`, `dT`, `n`,
  `sigma_allow`, `sigma_actual`, `sigma_b`, `tau_avg`, `dL_t`, `Fx`, `Fy`, `Ff`, `R`,
  `P1`/`P2`) was individually checked and is **not** an exact `UNITS`/`BUILTINS` key, so
  none of them trigger this behaviour. `theta`/`alpha_t`'s English names also happen to be
  keys in `engine/formatting.py`'s existing `GREEK` display dict (spec 011), so they
  additionally display as θ/α once typed/defined — a free bonus, not something this spec
  needs any code for.
- This spec does **not** propose fixing `_check_defined()` itself (an engine change, out
  of scope for a specialist's behavioural spec, and arguably its own small backlog item
  that would help this tab and the parallel electrical/chemical tabs at once rather than
  three independent naming workarounds) — flagged as Open question 4 below instead.

### Statics (6 buttons)
| Label | Inserted token | Tooltip (own wording) |
|---|---|---|
| Resultant (2 forces) | `R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))` | Resultant of two concurrent forces (law of cosines). P1, P2 in N; theta in rad (or e.g. "30*deg"); R in N. |
| Force, x-component | `Fx := P*cos(theta)` | Horizontal component of a force P at angle theta from the x-axis. P in N; Fx in N. |
| Force, y-component | `Fy := P*sin(theta)` | Vertical component of a force P at angle theta from the x-axis. P in N; Fy in N. |
| Moment of a force | `M := P*d` | Moment of a force P about a point, at perpendicular distance d from its line of action. P in N; d in m; M in N·m. |
| Static friction limit | `Ff := mu_s*Fn` | Maximum static friction force (Coulomb friction model). mu_s dimensionless; Fn (normal contact force) in N; Ff in N. |
| Centroid, 2 point masses | `x_cg := (m1*x1 + m2*x2)/(m1 + m2)` | x-coordinate of the combined centre of mass of two point masses. m1, m2 in kg; x1, x2 in m; x_cg in m. |

### Strength of Materials (9 buttons)
| Label | Inserted token | Tooltip (own wording) |
|---|---|---|
| Axial (normal) stress | `sigma := P/Ac` | Normal stress from an axial load. P in N; Ac (cross-sectional area) in m^2; sigma in Pa. |
| Normal strain | `epsilon := dL/L0` | Strain from an elongation. dL, L0 in m; epsilon dimensionless. |
| Hooke's law (axial) | `sigma := E*epsilon` | Linear-elastic stress-strain relation. E (Young's modulus) in Pa; epsilon dimensionless; sigma in Pa. |
| Axial elongation | `dL := P*L0/(Ac*E)` | Elongation of a bar under axial load. P in N; L0 in m; Ac in m^2; E in Pa; dL in m. |
| Bending stress | `sigma_b := M*y/Ix` | Bending (flexural) stress at distance y from the neutral axis. M in N·m; y in m; Ix (second moment of area) in m^4; sigma_b in Pa. |
| Transverse shear stress | `tau := Fv*Q/(Ix*b)` | Shear stress in a beam from a transverse shear force. Fv in N; Q (first moment of area) in m^3; Ix in m^4; b (section width) in m; tau in Pa. |
| Average shear stress | `tau_avg := P/Ac` | Average shear stress from a force acting parallel to a surface (same shape as axial stress, a distinct physical quantity — deliberately kept as its own button, see Edge cases). P in N; Ac in m^2; tau_avg in Pa. |
| Linear thermal expansion | `dL_t := alpha_t*L0*dT` | Elongation from a temperature change. alpha_t (linear expansion coefficient) in 1/K; L0 in m; dT in K; dL_t in m. |
| Factor of safety | `n := sigma_allow/sigma_actual` | Ratio of allowable to actual stress. sigma_allow, sigma_actual in Pa; n dimensionless. |

Total: 15 new buttons, exactly 2 sub-category headers, 0 engine/document changes.

### Deferred (forward note, not specced here)
Three more sub-categories — **Dynamics** (e.g. kinematics, Newton's second law `F := m*a`-
style, work-energy, impulse-momentum), **Fluid Mechanics** (e.g. Bernoulli's equation,
continuity, Reynolds number, hydrostatic pressure), **Thermodynamics** (e.g. ideal gas law,
first law, heat transfer) — are explicitly out of scope for this phase, the same way this
project phased spec 002 (002a/002b) and spec 017 (S1/S2/S3). Each would become its own
future spec simply adding more `(category, label, token, tip)` tuples and one more
`TAB_CATEGORIES["Mechanical"]` entry to the *same* tab this spec creates — no new mechanism,
same naming-collision check against `UNITS`/`BUILTINS` must be repeated for each (e.g.
Dynamics' `F := m*a` nearly repeats this spec's own `F`-vs-`P` problem and should use `P`/
`Fnet` instead of bare `F`; Thermodynamics will hit `W` (work vs. Watt) and `Q` already
used above for first moment of area in a different formula, needing its own disambiguation
pass). This phase deliberately covers only the two sub-categories a "Mechanical" engineer
reaches for first and most often (every statics/strength-of-materials course sequence)
rather than the whole field in one slice.

## Syntax proposal (own keywords)
N/A — no grammar change. `engine/syntax.py`, the `.lsheet` statement grammar, and the
evaluator are all unchanged; every inserted token is an ordinary `name := expression`
definition the existing parser already accepts (same `:=` already used by every other
quick-insert token and every hand-typed definition today).

## Acceptance criteria
GUI/data (same style as spec 011's criteria 2-5):
1. `"side-panel-tabs"` gains an 8th tab, `"Mechanical"` (position per Open question 1),
   without removing or reordering any of spec 011's 7 existing tabs.
2. The Mechanical tab shows exactly 2 sub-headers, "Statics" and "Strength of Materials",
   in that order, and exactly 15 clickable buttons total (6 under Statics, 9 under
   Strength of Materials), each with the exact label/token/tooltip from the tables above.
3. Clicking "Moment of a force" inserts the literal text `M := P*d` at the cursor (same
   `insert_token` mechanism already verified by spec 011's own tests); clicking "Axial
   (normal) stress" inserts `sigma := P/Ac`.
4. No button on this tab calls anything other than `insert_token`; nothing on this tab
   changes `.lsheet` format version or adds a `RegionData` field.

Engine-level (the inserted text is plain existing syntax; these are run directly against
`Engine.evaluate`, no GUI needed, same style as every prior engine-focused spec):
5. Axial stress: `P := 1000 N`, `Ac := 50 mm^2`, then the inserted `sigma := P/Ac` followed
   by `sigma = MPa` gives `= 20 MPa` (manager's correction: a bare `sigma =` gives the
   engine's own base-SI display, `= 2×10⁷ Pa`, numerically identical but not textually
   "MPa" — verified directly against the running engine 2026-11-01; `= MPa` is the
   existing, already-shipped syntax for requesting that specific display unit, same as
   every other spec's own worked examples that show a non-base-SI unit).
6. Bending stress: `M := 500 N*m`, `y := 0.05 m`, `Ix := 8e-6 m^4`, then
   `sigma_b := M*y/Ix`, `sigma_b = MPa` gives `= 3.125 MPa` (same correction as 5).
7. Transverse shear: `Fv := 2000 N`, `Q := 1.2e-4 m^3`, `Ix := 8e-6 m^4`, `b := 0.02 m`,
   then `tau := Fv*Q/(Ix*b)`, `tau = MPa` gives `= 1.5 MPa` (same correction as 5).
8. Hooke's law: `E := 200 GPa`, `epsilon := 0.001`, then `sigma := E*epsilon`, `sigma = MPa`
   gives `= 200 MPa` (same correction as 5).
9. Axial elongation: `P := 5000 N`, `L0 := 2 m`, `Ac := 100 mm^2`, `E := 200 GPa`, then
   `dL := P*L0/(Ac*E)`, `dL = mm` gives `= 0.5 mm` (same correction as 5, verified: a bare
   `dL =` gives `= 0.0005 m`).
10. Thermal expansion: `alpha_t := 1.2e-5 /K`, `L0 := 2 m`, `dT := 50 K`, then
    `dL_t := alpha_t*L0*dT`, `dL_t = mm` gives `= 1.2 mm` (same correction as 5/9, verified:
    a bare `dL_t =` gives `= 0.0012 m`).
11. Factor of safety (unit cancellation): `sigma_allow := 250 MPa`,
    `sigma_actual := 100 MPa`, then `n := sigma_allow/sigma_actual`, `n =` gives `= 2.5`
    (dimensionless — both units cancel, demonstrating the existing unit system handles
    this template correctly with no special-casing needed).
12. Resultant of two forces (3-4-5 check): `P1 := 3 N`, `P2 := 4 N`, `theta := 90*deg`,
    then `R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))`, `R =` gives `= 5 N`.
13. Force components: `P := 10 N`, `theta := 30*deg`, then `Fx := P*cos(theta)`,
    `Fx =` gives `= 8.66025 N`; `Fy := P*sin(theta)`, `Fy =` gives `= 5 N`.
14. Friction: `mu_s := 0.3`, `Fn := 200 N`, then `Ff := mu_s*Fn`, `Ff =` gives `= 60 N`.
15. Centroid: `m1 := 2 kg`, `x1 := 0 m`, `m2 := 3 kg`, `x2 := 5 m`, then
    `x_cg := (m1*x1 + m2*x2)/(m1 + m2)`, `x_cg =` gives `= 3 m`.
16. Moment: `P := 100 N`, `d := 0.3 m`, then `M := P*d`, `M = N*m` gives `= 30 N·m`
    (manager's correction: a bare `M =` gives `= 30 J` — moment of force and energy share
    the same base-SI dimension, kg·m²/s², and the engine's formatter names that dimension
    "J" by default; verified directly against the running engine 2026-11-01. `= N*m` is
    the existing, already-shipped syntax for requesting that specific display unit; the
    tooltip for this button should also warn the user that a bare `M =` will show "J", not
    "N·m", so they know to ask for `N*m` explicitly if they want torque/moment-style units
    — a real, user-facing quirk of this engine, not specific to this spec).

Error cases (the exact point of the naming-collision workaround above):
17. On a **fresh region, with nothing else defined on the sheet**, the inserted template
    `sigma := P/Ac` followed by `sigma =` gives the existing engine's own
    `"Ac, P are not defined"` error (alphabetical, from `_check_defined`'s existing
    format) — **not** a silent, wrong, unit-mismatched numeric result. This is the
    acceptance criterion that actually exercises why `P`/`Ac` (not `F`/`A`) were chosen;
    the developer/tester should additionally add one regression-documenting test (not a
    user-facing feature) confirming the *opposite*, unwanted behaviour would occur with
    the naive names — `Engine.evaluate` on `"sigma := F/A"` with nothing else defined
    gives status `"ok"` (not an error at all), proving the landmine this spec's naming
    choice avoids is real on today's engine.
18. `P := 5000 N`, `L0 := 2 m`, `Ac := 5 N` (accidentally a force, not an area),
    `E := 200 GPa`, then `dL := P*L0/(Ac*E)`, `dL = mm` gives the existing `UnitError`
    family, `"Units do not match: result is m²·s²/kg"`, not a crash (manager's correction:
    a bare `dL =` alone does **not** raise anything — it has nothing to compare the
    result's dimension against, so it just displays whatever generic dimension the
    mismatched arithmetic happens to produce, `= 1×10⁻⁸ m²·s²/kg`, with status `"ok"`;
    verified directly against the running engine 2026-11-01. The error only fires once a
    specific target unit is requested that the actual dimension can't convert to — `= mm`
    here, since `m²·s²/kg` isn't a length — same pre-existing unit-checking behaviour
    every other spec's own worked examples already rely on, not new code).

## Edge cases
- **"Average shear stress" and "Axial (normal) stress" insert differently-named
  definitions with an identical right-hand-side shape** (`tau_avg := P/Ac` vs.
  `sigma := P/Ac`): this is deliberate, not a copy-paste mistake — both are standard,
  distinct strength-of-materials quantities (a force perpendicular to a surface vs.
  parallel to it) that happen to share the same formula shape in every public source
  consulted; kept as two buttons because a user working through a shear problem should
  not have to notice "this is secretly the same formula as the stress button" to find it.
- **Re-using a template on the same sheet twice** (e.g. both `dL := ...` for axial
  elongation and, separately, wanting thermal elongation too) uses `dL` vs. `dL_t` as
  deliberately *different* synthesized names specifically so both can coexist on one sheet
  without one silently overwriting the other via this project's existing "last definition
  wins" rule — not an accident of naming.
- A long multi-character label/tooltip in a 120-320 px panel relies on Qt's own default
  button/tooltip text handling (wrapping, elision, or simple overflow) exactly the same
  "no bespoke layout logic" posture spec 011's own Edge cases already took for its 7-tab
  bar and 40-entry Elements tab; no acceptance criterion in this spec depends on a
  particular wrap/elide behaviour.
- A user who edits an inserted template's variable names by hand (e.g. renaming `Ac` back
  to `A`) re-triggers exactly the landmine described above — this spec's naming choice
  protects the *button-inserted* text only, not arbitrary hand-typed text; unrelated to
  this spec (every existing quick-insert token already has the same property: it protects
  what it inserts, not what a user later edits it into).
- No `.lsheet` document-format change: a document without this spec's tab/buttons (saved
  by an older build) opens unaffected; a document containing one of these templates'
  *inserted text* is just an ordinary region, indistinguishable after the fact from a
  hand-typed one, so backward/forward compatibility is automatic (same as every prior
  spec that only adds quick-insert chrome, e.g. 011).

## IP check
Pass, with the flags below.
1. All formulas are generic, textbook-standard, decades-to-centuries-old mechanics
   (Newtonian statics, Hooke's law, Euler-Bernoulli beam theory, Coulomb friction,
   linear thermal expansion) — explicitly on `docs/IP-POLICY.md`'s own "Allowed" list
   ("mathematical methods, algorithms and concepts... common function names"); independently
   confirmed identical across every public source consulted (Wikipedia, MIT OCW, generic
   course-note/formula-sheet search results), not distinctive to, invented by, or owned by
   any one software product.
2. No named commercial math/engineering tool's own formula palette, Quick Sheets, or
   worksheet library was read, consulted, or referenced for formula *selection* or
   *categorization* — per this task's explicit instruction, this specialist read only
   Wikipedia, MIT OCW, and generic public course/study-guide material; the two-sub-category
   split (Statics, then Strength of Materials) is grounded in MIT OCW 2.001's own public
   curriculum structure (a standard ME course sequence, not any one vendor's packaged
   category set) and this specialist's own judgement about a well-scoped first phase.
3. Variable names are this project's own choice, not copied from any one source's notation
   1:1 — where a public source's own convention was followed (e.g. `P` for axial load,
   `sigma`/`tau` for stress), it is because that is genuinely the common cross-source
   convention (confirmed independently across Wikipedia and the general search above), not
   because one particular tool uses it; where this project's own engine forced a deviation
   from the single-letter textbook convention (`P` not `F`, `Ac` not `A`, `Fv` not `V`,
   `Ix` not `I`, `Fn` not `N`), that deviation is fully explained above and is specific to
   this project's own `engine/units.py`, not an IP consideration.
4. **SI units only, as instructed**: nothing in this spec's templates, tooltips, or
   numeric examples uses or mentions an imperial/US customary unit or default (no `lbf`,
   `ft`, `psi`, `slug`, `BTU`, etc., anywhere); every tooltip states the expected SI unit
   (`N`, `m`, `Pa`, `kg`, `s`, `K`, `m^4`, `m^3`) and every acceptance-criterion example
   uses only SI/SI-prefixed units already in `engine/units.py`'s existing `UNITS` dict.
   `engine/units.py` itself already defines non-SI units (`ft`, `lbf`, `psi`, etc., for
   general unit-conversion use elsewhere in the app) — this spec does not touch, remove, or
   rely on any of those; it simply never emits them.
5. No GUI/canvas interaction technique beyond spec 011's own already-reviewed "click a
   button, insert text at the cursor" mechanism is used (ip-cleanroom rule 6 is already
   satisfied by 011 and inherited unchanged here — no new on-canvas placeholder editing of
   any kind, consistent with the patent-caution precedent set when spec 005 was superseded).
6. No vendor name, icon, help text, example worksheet, or keyword set from any commercial
   math/engineering tool appears anywhere in this spec.
7. Before a 1.0 release, the IP policy's own legal-review step should include this feature
   too (standing reminder, same as every prior spec).

## Fits current architecture?
- **`livesheet/gui/sidepanel.py`**: append 15 new `(category, label, token, tip)` tuples
  (categories `"Statics"`/`"Strength of Materials"`) to `MATH_TOKENS` (or a separate list
  merged at import time — developer's choice, same freedom spec 011 gave); add
  `TAB_CATEGORIES["Mechanical"] = ("Statics", "Strength of Materials")`; insert
  `"Mechanical"` into `TAB_ORDER` (see Open question 1). No change to
  `_build_functional_tab`/`_build_placeholder_tab`/`insert_token` — the existing functions
  already do everything this spec needs, including the sub-header behaviour (already
  triggered automatically by a tab backed by more than one category).
- **`livesheet/gui/main_window.py`**: no change (no new shortcuts, no new menu entries
  proposed by this spec).
- **`livesheet/engine/*`, `livesheet/document.py`**: no change. Every inserted token is an
  ordinary `name := expression` statement the existing parser/evaluator/unit system already
  handles; no new builtin function, no new keyword, no format-version bump.
- Dependency: **none new** — pure data/content addition reusing spec 011's existing
  mechanism and the existing SI-based `engine/units.py` unit system, per the task's own
  expectation.
- Tests: new `tests/test_mechanical_formula_tab.py` (developer), covering criteria 1-4 via
  the same `objectName`/tab-text/button-label/token/tooltip lookups spec 011's own test
  file already established, plus criteria 5-18 as plain `Engine.evaluate` calls (no GUI
  needed for those, same split spec 017 used between its own GUI-free numeric criteria and
  spec 011's GUI-lookup criteria). Independent tester writes a black-box counterpart from
  this spec, same process as every previous spec; the tester should also do a real-window
  pass on Theo's Mac confirming the new Mechanical tab appears, both sub-headers render,
  and at least one button from each sub-category inserts its exact token into a real math
  region.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Where "Mechanical" sits in `TAB_ORDER`, and how to merge with the parallel
   Electrical (backlog 40) and Chemical (backlog 41) tabs.** This spec's own
   recommendation: `Elements, Algebra, Calculus, Statistics, Optimization, Mechanical,
   Outline, Data`. Since two sibling specialist sessions are adding their own new tabs to
   this exact same list at the same time, three independent specs each editing
   `TAB_ORDER` is a near-certain merge collision once the developer implements all three —
   recommend the manager sequence/merge all three tab-order edits together (e.g. as one
   combined ordering decision — `..., Optimization, Mechanical, Electrical, Chemical,
   Outline, Data`, matching the backlog's own 39/40/41 order) rather than letting three
   specs each assume they're the only new tab being added, and recommend telling the
   developer to implement whichever of 018/019/020 lands last to also reconcile
   `TAB_ORDER` rather than each implementer touching it independently.
2. **Is the chosen first-phase scope (Statics + Strength of Materials, 15 buttons) the
   right size, or should Theo want Dynamics included from the start** (it is arguably just
   as "every ME student's first course" as Statics)? Recommendation: keep Dynamics
   deferred — its most natural formula (`F := m*a`) immediately re-hits the same `F`
   collision problem and deserves its own careful pass rather than being rushed into this
   phase; nothing about this phase's own 15 buttons depends on Dynamics existing yet.
3. **Tooltip-only unit documentation vs. a richer per-symbol display.** This spec chose
   "bare template + tooltip states each symbol's expected SI unit" over any richer
   mechanism (e.g. a dialog listing each symbol with a unit dropdown) specifically to avoid
   adding any new widget/dialog and to stay inside ip-cleanroom rule 6's "boring, generic
   chrome" preference. Confirm this is an acceptable trade-off of discoverability
   (a tooltip is easy to miss) vs. risk/scope, or should a future phase add a richer
   per-symbol affordance (flagged as a possible, not designed, follow-up)?
4. **Should `engine/evaluator.py`'s `_check_defined()` be hardened separately** so that a
   bare name that resolved *only* via the `UNITS` seed (never actually defined by the
   user with `:=`) is also reported as "not defined", rather than relying on every
   formula-tab spec (this one, and the parallel electrical/chemical ones) to work around
   it by avoiding single-letter unit-colliding names? This is a genuine, already-confirmed
   engine behaviour (see criterion 17's regression-documenting test) that pre-dates this
   spec and would help all three formula-tab specs plus any future one; this specialist is
   not proposing the engine change itself (out of scope for a behavioural spec, and a real
   engine-design judgement call: it would change what counts as "defined" for every
   existing sheet, however unlikely a real sheet is to rely on `F`/`A`/`V`/etc. resolving
   as units without ever having been assigned a unit-bearing value by the user) —
   recommend the manager decide whether this becomes its own small backlog item for the
   developer, independent of merging this spec.
5. **Relaying this naming-collision finding to the electrical/chemical specialist
   sessions.** This specialist tried to message both sibling sessions directly (by the
   names `electrical-specialist`/`chemical-specialist`) per the project's "message other
   agents about overlapping work" convention, but neither name resolved (no `ListAgents`
   tool was available to this specialist to look up the correct names/refs). Recommend the
   manager relay this finding (or point them at this spec's "Why these variable names, not
   the more obvious ones" section) to whichever sessions are writing specs 019/020 for
   backlog 40/41, since electrical quantities in particular (V, A, W, C, F, H, T) collide
   with `UNITS` keys even more pervasively than mechanical ones do.
