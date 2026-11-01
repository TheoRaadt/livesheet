# 020 Electrical engineering formula tab, phase E1 (DC Circuits, Power)

Spec-numbering note: originally drafted as 018, renumbered to 020 because spec number 018 was
independently claimed in parallel by the mechanical-formula-tab specialist (backlog 39); 019 was
likewise already taken by the chemical-formula-tab specialist's own renumbered spec (backlog 41).
See the stale stub left at `docs/board/specs/018-electrical-formula-tab.md`.

Source inspiration (concept only, nothing copied):
- Backlog item 40 (M8 Engineering formula reference tabs, Theo's request
  2026-11-01) and `docs/board/specs/011-side-panel-category-tabs.md` (already
  shipped and approved) — this spec adds one more side-panel tab using exactly
  the mechanism spec 011 already established (a tab holding a scrollable,
  vertically stacked list of bordered buttons, grouped under grey sub-header
  labels, each button calling the existing `insert_token(token)` callback). No
  new chrome concept, no new widget type.
- https://en.wikipedia.org/wiki/Outline_of_electrical_engineering (accessed
  2026-11-01) — a generic, encyclopedic topic breakdown of electrical
  engineering as a field (classification, branches, general concepts incl.
  "Electromagnetism", "Physical laws", "Power engineering", etc.). Concept used
  only: that "circuit laws/power/electromagnetism" is a standard, cross-source
  way to group this field's foundational formulas — not any one vendor's
  packaged grouping. This spec's own four sub-categories (DC Circuits, Power,
  AC Circuits, Electromagnetics — the first two in this phase, the last two
  deferred, see Size below) are this specialist's own naming/split, informed
  by but not copied from this outline's section names (it does not use "DC
  Circuits" or "AC Circuits" as section headers at all; those are this spec's
  own, more specific subdivision of its "Electromagnetism"/"Power engineering"
  sections for a formula-insertion context, not an encyclopedia article).
- https://en.wikipedia.org/wiki/Ohm%27s_law and
  https://en.wikipedia.org/wiki/Kirchhoff%27s_circuit_laws and
  https://en.wikipedia.org/wiki/Electric_power (all accessed 2026-11-01) —
  confirmed the standard, textbook-universal forms of Ohm's law (`V=IR`,
  `I=V/R`, `R=V/I`) and electric power (`P=VI`, `P=I²R`, `P=V²/R`) used below.
  These are 19th-century public-domain physics (Ohm 1827, Kirchhoff 1845,
  per the arXiv historical note checked during this spec's own research pass),
  taught identically (to within notation) in every electrical-engineering
  course and textbook; nothing below is specific to any one software product's
  own presentation of them.
- No named commercial math/engineering tool's formula palette, Quick Sheets,
  worksheet library, help page, tutorial, or example worksheet was read for
  this spec, per `.claude/skills/ip-cleanroom/SKILL.md`.
- A sibling mathcad-specialist session (mechanical-formula-tab, backlog 39)
  flagged, mid-task, a real engine landmine affecting all three M8 formula-tab
  specs: `evaluator.py`'s `Engine.evaluate()` seeds its environment with
  `env = dict(UNITS)` — every unit abbreviation in `engine/units.py` (`V`,
  `A`, `W`, `C`, `F`, `H`, `T`, `J`, `N`, `K`, `L`, `g`, ...) and `I` (bound to
  `sp.I`, the imaginary unit, in `BUILTINS`) is already a defined name before
  any user statement runs; `_check_defined()` only flags genuinely leftover
  free symbols, so a bare variable *read* that happens to spell a unit
  abbreviation or `I` never errors — it silently evaluates to that unit's own
  magnitude (or to the imaginary unit) instead. This is checked against
  directly (reading `livesheet/engine/units.py`'s `UNITS` dict and
  `livesheet/engine/evaluator.py`'s `_builtins()` function, not just taken on
  the sibling's word) and addressed below, in Design decision 2 and Open
  question 6 — not proposed as an engine fix here, per the sibling's own
  framing that hardening `_check_defined()` itself is an engine-design call
  for the manager across all three sibling specs at once, not one specialist's
  call to make unilaterally mid-spec.

Size: deliberately scoped to a well-bounded first phase rather than the whole
field. Backlog item 40 itself names "circuits, power, electromagnetics" as
representative sub-areas; this specialist's own call (per the task's explicit
invitation to make this judgement) is to split those into four named
sub-categories — **DC Circuits, Power, AC Circuits, Electromagnetics** — and
ship only the first two as phase **E1** (this spec, about 1.5 days: 11
formula-template buttons across two sub-headers, pure data-table addition to
the already-shipped `sidepanel.py` mechanism, zero engine change). **AC
Circuits** (impedance, reactance, resonant frequency, RMS values, power
factor/apparent-reactive-real power) and **Electromagnetics** (Coulomb's law,
capacitor/inductor energy, parallel-plate capacitance, Faraday's-law EMF,
magnetic force on a current-carrying conductor) are an explicit forward note
for a phase **E2** follow-up spec, not designed here — same two-sub-headers
added later to this same tab, no new mechanism needed for them either (that
follow-up spec will need the same UNITS/BUILTINS collision check again, e.g.
`C` for charge and `H`/`L` for inductance are both unit abbreviations and
`T` is both tesla and a plausible period-of-oscillation symbol — flagged
here so it isn't missed). DC Circuits + Power was chosen as the first slice
because every one of its formulas uses only base SI quantities (`V`, `A`,
`Ω`, `W`, `s`) already fully supported by `livesheet/engine/units.py` today,
with zero new unit symbols needed, and because Ohm's law and basic power
relations are the two most universally reached-for formulas in this field
(confirmed cross-source during research, not just this specialist's own
assumption) — a representative, genuinely useful first slice rather than an
arbitrary alphabetical cut.

---

## User story
As a LiveSheet user doing electrical-engineering calculations, I want a
dedicated place in the side panel to quick-insert standard circuit/power
formulas as editable templates — the same click-to-insert convenience I
already have for operators and calculus notation (spec 011) — instead of
typing out Ohm's-law-family formulas from memory or scratch every time, and I
want everything inserted to stay in SI units (volts, amps, ohms, watts),
never imperial/US customary units, and I want the formula to actually work
correctly the first time I use it, not silently compute something wrong.

## Behaviour (own words)
The side panel gains one new tab, **Electrical**, positioned immediately
after **Optimization** and before **Outline**/**Data** (the same "append
after the existing math-category tabs, before the two structural placeholder
tabs" rule spec 011 already used for Statistics/Optimization) — see Edge
cases and Open question 1 for how this interacts with the two sibling
specs (Mechanical, Chemical) being written in parallel for the same backlog
milestone.

The Electrical tab shows the same kind of scrollable, vertically stacked list
of bordered buttons the Elements/Algebra/Calculus tabs already use, grouped
under grey sub-header labels (the same presentation spec 011 already used for
Elements' three internal groups) — one sub-header per sub-category. This
phase (E1) ships exactly two sub-headers, in this order:

1. **DC Circuits**
2. **Power**

(**AC Circuits** and **Electromagnetics** are deferred to phase E2, see Size
above — not present as empty placeholder sub-headers in this phase; they are
simply added to this same tab by a later spec, the same way spec 011 said the
Calculus tab is "the natural future home for more calculus content" without
reserving a visible stub for it today.)

Each button, like every existing side-panel button, **inserts a bare,
editable formula-template statement** at the cursor via the existing
`insert_token(token)` callback (same mechanism, unchanged) — not a filled-in
numeric example, and not a dialog. This is a deliberate, minimal extension of
the existing mechanism to multi-symbol statement text rather than a single
operator/symbol token (today's tokens insert things like `"sqrt("` or
`" ≡ "`; this spec's tokens insert a complete `name := expression` statement
using LiveSheet's own existing `:=`-definition syntax) — the button's label
text is identical to the exact text it inserts, so what the user sees on the
button is exactly what lands on the sheet, letter for letter. The user is
expected to rename the generic placeholder variable names (`Vs`, `Is`, `R`,
`R1`, `R2`, ...) to their own sheet's actual variable names after inserting,
exactly as already happens today after inserting any multi-character token
like `"sqrt("` or `"diff("` — no new renaming/placeholder-editing mechanism is
introduced (per the patent-risk note in `.claude/skills/mathcad-concepts`,
this spec deliberately does not add any live, on-canvas fill-in-the-blank
interaction; see IP check).

No unit is baked into any inserted template string itself (a template reads
`Vs := Is * R`, never `Vs := Is * R  (* units: V, A, ohm *)` or similar) — SI-
only compliance is expressed by which variable *names* and formulas are
offered (all drawn from quantities LiveSheet's unit system already expresses
in SI: volts/amps/ohms/watts/joules/seconds) and by this spec's own worked
examples below, which only ever assign SI units (`V`, `A`, `ohm`, `W`) to
those variables — never an inch/pound/psi-family unit from
`engine/units.py`'s existing, already-approved (for mechanical contexts)
imperial entries. A user remains free to assign any unit LiveSheet already
understands to any inserted variable, same as for every other quick-inserted
token on the sheet today — this spec does not add or need any new unit-
restriction mechanism; the SI constraint is satisfied by curation of which
formulas/variable names this spec itself offers, not by new engine
enforcement.

### Design decision 1: four sub-categories, two shipped now
Already explained under Size above; repeated here only as a pointer since
it is also the answer to Open question 3 below.

### Design decision 2: `Vs`/`Is` instead of bare `V`/`I`
Checked directly against `livesheet/engine/units.py`'s `UNITS` dict and
`livesheet/engine/evaluator.py`'s `_builtins()` (see the sibling-flagged
landmine noted under Source inspiration above) before finalising every
variable name below, not assumed safe just because `V`/`I`/`R`/`P` are the
textbook-standard symbols for voltage/current/resistance/power:
- Bare `V` collides with the volt unit abbreviation (`UNITS["V"]`) and bare
  `I` collides with the imaginary unit (`BUILTINS["I"] = sp.I`) — both would
  silently evaluate to a wrong, non-error value if read before the user
  defines them, exactly the failure mode the sibling spec flagged. Both are
  avoided everywhere in this spec: every voltage placeholder is named `Vs`
  (source voltage) and every plain current placeholder is named `Is` (source
  current) instead — not in `UNITS` or `BUILTINS`, confirmed by direct
  lookup, and still an immediately recognisable, standard-enough circuit-
  textbook convention (source quantities are routinely subscripted this way)
  rather than an arbitrary rename.
- `R`, `P`, `E`, `t` are all confirmed **not** present in `UNITS` or
  `BUILTINS` (`UNITS` has no `"R"`, `"P"`, `"E"` or `"t"` key; `s` — lower-
  case — is the UNITS second-unit abbreviation, not `t`; `BUILTINS`'s `"e"`
  Euler's-number entry is lower-case and therefore a different, non-colliding
  key from this spec's upper-case `E` for energy) — kept bare, unchanged.
- The already-suffixed names this spec also uses (`R1`, `R2`, `R_total`,
  `V_in`, `V_out`, `I1`, `I_total`) were likewise checked: none of these exact
  multi-character strings is a `UNITS`/`BUILTINS` key (only single-token
  abbreviations like `"V"`/`"A"`/`"kV"` are keys; a name with a digit or
  underscore suffix is never one), so they are unaffected and kept as
  originally drafted.
- This check covers every variable name used anywhere in this phase's 11
  templates and 3 worked examples; none of `Vs`, `Is`, `R`, `R1`, `R2`,
  `R_total`, `V_in`, `V_out`, `I1`, `I_total`, `P`, `E`, `t` collides with any
  `UNITS` or `BUILTINS` key as of the current `livesheet/engine/units.py`/
  `evaluator.py` on disk at spec-writing time.

### DC Circuits (7 entries, in this order)
| Label / inserted text | Tooltip |
|---|---|
| `Vs := Is * R` | Ohm's law — voltage from current and resistance (Vs in volts, Is in amps, R in ohms) |
| `Is := Vs / R` | Ohm's law — current from voltage and resistance |
| `R := Vs / Is` | Ohm's law — resistance from voltage and current |
| `R_total := R1 + R2` | Resistors in series — equivalent resistance of two resistors |
| `R_total := 1 / (1/R1 + 1/R2)` | Resistors in parallel — equivalent resistance of two resistors |
| `V_out := V_in * R2 / (R1 + R2)` | Voltage divider — output voltage measured across R2 |
| `I1 := I_total * R2 / (R1 + R2)` | Current divider — current through the R1 branch of two resistors in parallel |

### Power (4 entries, in this order)
| Label / inserted text | Tooltip |
|---|---|
| `P := Vs * Is` | Electrical power from voltage and current |
| `P := Is^2 * R` | Electrical power from current and resistance |
| `P := Vs^2 / R` | Electrical power from voltage and resistance |
| `E := P * t` | Electrical energy from power and time |

Total: 11 clickable entries in the Electrical tab after this phase.

Clicking any entry behaves exactly like clicking any existing side-panel
button today: a math region is created/focused if none is active, and the
token text is inserted at the cursor — identical mechanism, zero new GUI
behaviour beyond the data (label, token, tooltip) entries themselves. The
existing display pipeline (`gui/pretty.py`) already renders `:=`, `*`, `/`,
`^2` and `name_suffix` subscripts (e.g. `R_total` → R with a "total"
subscript, `V_in`/`V_out`/`I_total` likewise) exactly as it already does for
any hand-typed statement using the same syntax — nothing new to render.

## Syntax proposal (own keywords)
N/A — no grammar change. Every inserted template is an ordinary `name :=
expression` definition statement, already fully supported by
`livesheet/engine/syntax.py`/`evaluator.py` today (the same statement kind
every existing worksheet already uses for `x := 5`). No new keyword, no new
statement kind, no `.lsheet` format change.

## Acceptance criteria
1. `"side-panel-tabs"` gains one additional tab named **Electrical**,
   positioned after Optimization (index 5, pushing Outline/Data to indices
   6/7) in this spec considered on its own — see Open question 1 for the
   final index once Mechanical/Chemical land too.
2. The Electrical tab contains exactly 2 sub-header groups, in order: "DC
   Circuits" (7 entries), "Power" (4 entries); 11 clickable entries total, 0
   placeholder/non-interactive content.
3. Clicking the DC Circuits button labelled `Vs := Is * R` inserts the
   literal text `Vs := Is * R` at the cursor (same `insert_token` mechanism
   as every existing side-panel button); all 11 buttons' inserted text is
   byte-for-byte identical to their label text as tabulated above.
4. **Worked numeric example 1 (Ohm's law, SI units).** After inserting/typing,
   in order:
   ```
   Is := 2 A
   R := 10 ohm
   Vs := Is * R
   ```
   `Vs =` gives `20 V`.
5. **Worked numeric example 2 (parallel resistors, SI units).** After
   inserting/typing, in order:
   ```
   R1 := 100 ohm
   R2 := 100 ohm
   R_total := 1 / (1/R1 + 1/R2)
   ```
   `R_total =` gives `50 Ω` (LiveSheet's own existing preferred-display unit
   for resistance, per `engine/units.py`'s `_PREFERRED_DISPLAY`).
6. **Worked numeric example 3 (power, SI units).** After inserting/typing:
   ```
   Vs := 12 V
   Is := 3 A
   P := Vs * Is
   ```
   `P =` gives `36 W`.
7. **Error case.** Inserting the `P := Is^2 * R` button's text alone (with
   neither `Is` nor `R` defined anywhere above it) and evaluating `P` gives
   LiveSheet's existing, unmodified `"Is" is not defined` error (or `"R" is
   not defined` if `Is` is defined but `R` is not) — the ordinary, already-
   shipped undefined-name error, not a new error message; this spec adds no
   new error text anywhere. (This is exactly the case Design decision 2 above
   exists to make possible: with the original bare `I`/`V` naming, this
   criterion would have failed silently instead of erroring, per the
   sibling-flagged engine landmine.)
8. No imperial/US-customary unit (`inch`, `ft`, `yd`, `mi`, `lb`, `psi`, ...)
   appears in any of this spec's 11 inserted template strings or any of its
   three worked examples; every unit named anywhere in this spec is one of
   `V`, `A`, `ohm`/`Ω`, `W`, `s`, `J`.
9. No change to `livesheet/engine/*` or `livesheet/document.py`: a document
   containing only plain `:=` statements inserted via these new buttons
   round-trips through save/load identically to one typed by hand (no new
   region kind, no new field).
10. None of this spec's 11 template strings, read top to bottom with nothing
    else defined on the sheet, silently produces a plausible-looking wrong
    answer because a bare variable name happens to collide with a
    `UNITS`/`BUILTINS` key — every one either errors with the ordinary
    `"<name>" is not defined` message (if a prerequisite variable is genuinely
    missing) or, once its prerequisites are defined per the worked examples,
    gives the numerically correct answer. This is the direct, spec-level test
    of Design decision 2's own claim.

## Edge cases
- **Variable-name reuse across buttons** (`R1`/`R2` appear in three different
  DC Circuits buttons; `Vs`/`Is`/`R`/`P` repeat across Ohm's-law and Power
  buttons): inserting two templates that both define the same name on the
  same sheet is not a new situation this spec introduces — LiveSheet's
  existing top-to-bottom-then-left-to-right evaluation and last-definition-
  wins behaviour (already true for any hand-typed sheet) applies unchanged;
  the user is expected to rename as needed, exactly as after inserting
  `"sqrt("` twice and needing two different arguments.
- **Sub-category order/position relative to sibling specs.** This spec
  assumes the Electrical tab sits alone, right after Optimization. Two
  sibling specialist sessions are concurrently writing phase-1 specs for
  **Mechanical** (backlog 39) and **Chemical** (backlog 41) formula tabs under
  the same M8 milestone, each of which may make the same "goes right after
  Optimization" assumption independently — see Open question 1; this spec
  does not attempt to guess or pre-reconcile the three-way final order itself.
- **Phase E2's deferred sub-categories are invisible, not stubbed.** Unlike
  spec 011's Statistics/Optimization (whole *tabs* reserved with a visible
  placeholder message because nothing else existed in them yet), this spec's
  Electrical *tab* already has real, usable content (DC Circuits/Power) in
  this phase; AC Circuits/Electromagnetics simply don't exist as sub-headers
  yet, with no placeholder line reserving their place — consistent with how
  spec 011 treated the already-populated Calculus tab's future growth (no
  stub), not how it treated the then-fully-empty Statistics/Optimization
  tabs.
- **`R_total` reused by two different buttons** (series and parallel both
  default to the same result name `R_total`): deliberate — both are "the
  equivalent resistance of two resistors" in the same generic sense, and a
  user only ever inserts one or the other per sheet location, renaming as
  needed; not treated as a naming conflict to avoid, since the two buttons
  are never both clicked into the same unedited spot.
- **The `UNITS`/`BUILTINS` collision landmine is a standing engine property,
  not something this spec's naming choice fixes for anyone else.** Any other,
  future quick-insert content (phase E2, the sibling Mechanical/Chemical
  specs, or a user's own hand-typed sheet) can still hit the exact same
  silent-wrong-answer failure mode by choosing a bare `V`/`A`/`W`/`C`/`F`/`H`/
  `T`/`J`/`N`/`K`/`L`/`g`/`I` name; this spec only avoids it for its own 11
  templates (Design decision 2) and flags it for the manager (Open question
  6) rather than treating its own workaround as a general fix.

## IP check
Pass. Ohm's law and the power relations used here are 19th-century public-
domain physics facts, universally taught with identical formulas (to within
notation) in every source consulted (Wikipedia, and cross-confirmed via the
arXiv historical reference found during search) — `docs/IP-POLICY.md`
explicitly allows "mathematical methods, algorithms and concepts" and
"standard math/engineering notation". The only idea taken from the one
encyclopedic outline consulted is the generic, cross-source observation that
"circuit theory / power / electromagnetism" is a reasonable way to bucket this
field's foundational formulas — not that outline's own section names or
structure (its sections are "Electromagnetism" and "Power engineering" at a
much coarser grain than this spec's four finer sub-categories, and it is an
encyclopedia navigation aid, not a formula-insertion-button design of any
kind). No named commercial math/engineering tool's own formula palette, Quick
Sheets, worksheet library, help page, tutorial, or example worksheet was read
for this spec. No vendor name, icon, or literal section/tab label from any
such product appears anywhere here. The insertion mechanism itself (a button
in a side-panel tab calling `insert_token`) is spec 011's already-IP-approved,
already-shipped mechanism, reused verbatim — not a new interaction. Per the
patent-risk note in `.claude/skills/mathcad-concepts/SKILL.md`, this spec
deliberately keeps the "bare, editable template text, user renames
afterward" design (ip-cleanroom rule 6's "boring, generic toolkit chrome")
rather than any live, on-canvas fill-in-the-blank/placeholder-editing
interaction for the inserted variable names — there is no dialog and no
on-canvas placeholder mechanism of any kind in this spec, so this risk does
not arise at all, not even in a mitigated form. The `Vs`/`Is` naming choice
(Design decision 2) is a correctness fix for an internal engine property, not
an IP-motivated change, and does not affect this assessment either way. Not
legal advice.

## Fits current architecture?
- **`livesheet/gui/sidepanel.py`**: add one new tab to the existing tab-order
  list (spec 011's `TAB_ORDER`/`TAB_CATEGORIES`-equivalent constants,
  whatever the developer named them when implementing 011) with two new
  sub-header groups and 11 `(label, token, tooltip)` tuples, exactly as
  tabulated above — pure data addition, reusing the exact same
  scrollable-list-of-bordered-buttons-with-sub-headers rendering the Elements
  tab already uses (spec 011's own "the only functional tab that keeps
  sub-headers, for exactly this reason" note now applies to a second tab for
  the same reason: multiple distinct groups bundled in one tab for
  scannability).
- **`livesheet/gui/main_window.py`**: no change. No new keyboard shortcuts, no
  new menu entries proposed in this phase (unlike spec 011's Greek-letter
  shortcuts) — these are click-only quick-inserts, matching most of spec
  011's own non-Greek tokens.
- **`livesheet/engine/*`, `livesheet/document.py`**: no change. Every
  inserted template is an ordinary, already-supported `:=` statement over
  already-defined SI units (`V`, `A`, `ohm`, `W`, `s`, `J`); `engine/units.py`
  needs no new unit symbol for this phase (all used units — `V`, `A`,
  `ohm`/`Ω`, `W` — already exist today, confirmed by reading
  `livesheet/engine/units.py` directly before writing this spec), and no
  variable name this spec offers needs any engine-side fix either, per
  Design decision 2's own collision check.
- Tests: a new `tests/test_side_panel_electrical.py` (or folded into
  `tests/test_side_panel_categories.py`) covering criteria 1-3 via
  `objectName`/tab-text/button-label/tooltip lookups against the exact tables
  above, plus `Engine`-level tests for criteria 4-7 and 10 (the three worked
  numeric examples, the undefined-name error case, and a loop over all 11
  templates checked against `UNITS`/`BUILTINS` keys plus an actual
  `Engine().evaluate()` run per template with its own prerequisites
  undefined, asserting an ordinary `"<name>" is not defined` error rather
  than a silently-wrong numeric result) using `Engine().evaluate()` directly,
  no GUI needed for those. Criterion 9 needs no new test beyond the project's
  existing `tests/test_document.py` round-trip tests, which already cover
  plain `:=` statements.

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Final three-way tab order among Electrical, Mechanical (backlog 39,
   sibling spec) and Chemical (backlog 41, sibling spec).** This spec assumes
   Electrical sits alone right after Optimization; the two sibling specialist
   sessions writing those specs in parallel may make the same assumption
   independently, creating a three-way position collision analogous to the
   file-numbering collision already hit and resolved for this very spec (see
   the Spec-numbering note at the top). [Recommend the manager reconcile the
   three specs' tab-order assumptions once all three land — e.g. append all
   three in backlog order (Mechanical, Electrical, Chemical, matching backlog
   items 39/40/41) right after Optimization and before Outline/Data — rather
   than any one specialist guessing the other two's design; flagging
   explicitly rather than silently assuming my own ordering wins.]
2. **Formula-template insertion style: bare template vs. something richer.**
   This spec chose the simplest option (a bare, editable `name :=
   expression` statement, user renames variables afterward, zero new
   mechanism) over a richer alternative (e.g. a small dialog pre-filling
   variable names/units, closer to spec 006/008's dialog pattern). [Recommend
   accepting the bare-template approach for this first phase: it needs zero
   new GUI code beyond data entries (lowest risk, fastest to ship and
   review), matches how every other existing side-panel button already works
   today, and avoids any new on-canvas interaction surface entirely (see IP
   check) — if usage shows users want prefilled per-formula dialogs (e.g. to
   set units once per formula), that would be a natural, separate future
   spec, not a reason to hold this phase back.]
3. **Sub-category split and naming (DC Circuits / Power / AC Circuits /
   Electromagnetics) and which two ship first.** This specialist's own call,
   made explicit per the task's instruction rather than assumed silently:
   DC Circuits + Power ship first (phase E1, this spec) because every formula
   in them needs only base SI quantities already in `engine/units.py` with no
   new unit symbol, and because Ohm's law/power are the two most universally
   reached-for formulas in this field. [Recommend accepting; AC
   Circuits/Electromagnetics become phase E2, a follow-up spec, not designed
   here.]
4. **Variable-name collisions across the 11 templates** (`R1`/`R2` reused
   across three DC Circuits buttons; `R_total` reused by both the series and
   parallel buttons; `Vs`/`Is`/`R`/`P` reused across Ohm's-law and Power
   buttons) are left to the user to rename after inserting, with no new
   renaming mechanism. [Recommend accepting as consistent with how every
   other existing multi-character quick-insert token already behaves; no
   acceptance criterion or test needs to treat this as an error.]
5. **No keyboard shortcuts for any of the 11 new buttons in this phase**
   (click-only, like most of spec 011's own non-Greek tokens). [Recommend
   accepting; a future spec could add shortcuts if usage shows a need, same
   low-stakes deferral spec 011 itself used for its own uppercase Greek
   letters.]
6. **Should `_check_defined()` itself be hardened engine-side** so a bare
   name matching a `UNITS`/`BUILTINS` key is flagged (or at least warned
   about) when read without an explicit prior user definition, instead of
   every formula-tab spec (and every ordinary hand-typed sheet) having to
   work around it name-by-name? Raised by the sibling Mechanical spec,
   independently confirmed here by direct code inspection, not designed or
   proposed as a concrete fix by this spec — this is a cross-cutting engine-
   correctness question affecting all three M8 formula-tab specs (and every
   future one) plus ordinary hand-typed sheets, not a decision any one
   specialist should make unilaterally. [Recommend the manager track this as
   its own, separate engine-hardening item — independent of whether this
   spec, Mechanical's, or Chemical's content specs are themselves approved —
   since fixing it centrally would make every future specialist's naming
   choices safer by default rather than relying on each one remembering to
   check by hand, the way this spec and Mechanical's both had to.]
