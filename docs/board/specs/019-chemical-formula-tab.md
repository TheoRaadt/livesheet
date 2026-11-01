# 019 Chemical engineering formula tab (side-panel quick-insert)

Source inspiration (concept only, nothing copied):
- Backlog item 41 (M8, Theo's request 2026-11-01): a new side-panel tab of categorized,
  quick-insertable standard chemical-engineering formulas, SI units only, same pattern as spec
  011's existing category tabs. Backlog items 39/40 (Mechanical, Electrical) are sibling tabs
  being specced in parallel by other specialist sessions; this spec covers only Chemical, per the
  manager's "stay in your lane" instruction.
- `docs/board/specs/011-side-panel-category-tabs.md` — this project's own prior spec, which
  already shipped the dockable, tabbed side panel (`SidePanel`/`side-panel-tabs`), the
  `MATH_TOKENS`-shaped `(category, label, token, tip)` data convention, the `_build_functional_tab`
  helper (including its existing support for more than one sub-header group inside a single tab,
  used today by the Elements tab), and the placeholder-tab pattern. This spec is a follow-up to
  011's *tab mechanism*, adding one new functional tab; no new widget type, no new interaction
  technique.
- `.claude/skills/mathcad-concepts/SKILL.md` — "Engineering extras: standard-data tables,
  material/constants libraries, annotated/numbered equations" as a generic category-of-idea
  checklist item, used only at that level of generality (a worksheet tool benefits from a
  quick-reference library of standard relationships) — not read for, or copied from, any specific
  vendor's packaged content.
- Standard, long-public, textbook-level physical chemistry / chemical engineering concepts and
  formulas, cross-checked against current public encyclopedic sources (concept and formula only,
  nothing quoted beyond a formula's own conventional name), all accessed 2026-11-01:
  - Wikipedia, "Ideal gas law" (https://en.wikipedia.org/wiki/Ideal_gas_law) — PV = nRT, first
    stated (as a combination of Boyle's/Charles's/Avogadro's/Gay-Lussac's laws) by Clapeyron in
    1834.
  - Wikipedia, "Mole fraction" (https://en.wikipedia.org/wiki/Mole_fraction) and "Mass fraction
    (chemistry)" (https://en.wikipedia.org/wiki/Mass_fraction_(chemistry)) — composition measures
    as a ratio of a component's amount/mass to the mixture total.
  - Wikipedia, "Molar concentration" (https://en.wikipedia.org/wiki/Molar_concentration) — amount
    of substance per unit volume of solution.
  - Wikipedia, "Mass balance" (https://en.wikipedia.org/wiki/Mass_balance) — conservation of mass
    applied to a system boundary (material in = material out + accumulation), the foundation of
    process-engineering balance calculations.
  - Wikipedia, "Rate equation" (https://en.wikipedia.org/wiki/Rate_equation) — empirical power-law
    relationship between reaction rate, rate constant and reactant concentrations, with
    experimentally-determined (not stoichiometry-derived) partial orders.
  - Wikipedia, "Arrhenius equation" (https://en.wikipedia.org/wiki/Arrhenius_equation) — the
    exponential temperature dependence of a rate constant, k = A·exp(-Ea/RT), proposed 1889.
  - Wikipedia, "Reynolds number" (https://en.wikipedia.org/wiki/Reynolds_number) — dimensionless
    ratio of inertial to viscous forces in a flow, Re = ρvD/μ.
  - General, centuries-to-decades-old public thermodynamics/heat-and-mass-transfer concepts,
    taught identically (to within notation) in any introductory textbook: Fourier's law of
    conduction (proportionality between conductive heat flux and a temperature gradient, 1822),
    Newton's law of cooling (convective heat transfer proportional to a surface-to-fluid
    temperature difference), Fick's first law of diffusion (1855; diffusive flux proportional to a
    concentration gradient), sensible/latent heat (energy for a temperature change vs. a
    constant-temperature phase change) and the first law of thermodynamics applied to a
    steady-flow open system (an energy balance across a flowing system's boundary). None of this is
    specific to any one software product or textbook; nothing below is a 1:1 reproduction of any
    single source's own notation, variable names, worked example or packaged formula set.
  - No Mathcad, Mathematica, Maple, MATLAB or other vendor software, installed application, help
    file, example worksheet, "Quick Sheet"/formula-palette content, screenshot, or non-public
    document was read for this spec — the five-category breakdown, the specific formula selection
    within each, and every variable name below are this specialist's own choices, built directly
    from the generic public sources listed above, per `.claude/skills/ip-cleanroom/SKILL.md`.

Hard constraint (Theo, explicit, non-negotiable): **SI units only.** No formula, constant, or
worked example below uses or defaults to an imperial/US-customary unit. The one physical constant
this spec hard-codes (the universal gas constant) is given in SI units (`J/(mol*K)`); every other
template is unit-agnostic algebra that the user completes with whatever SI-consistent units they
assign to each placeholder name, using LiveSheet's own already-shipped unit system
(`livesheet/engine/units.py`, already supports `mol`, `kg`, `Pa`, `K`, `J`, `m^3`, `L`, and more) —
reused unchanged, nothing new added to it.

Size: one phase, about 1-2 days (GUI data-table addition plus one new tab, zero engine change, no
new widget type — same scope-shape as spec 011).

---

## User story
As a LiveSheet user doing a chemical-engineering or physical-chemistry calculation, I want a
"Chemical" tab in the side panel — grouped by sub-topic (stoichiometry, gas/thermodynamic
relationships, mass/energy balances, transport, reaction kinetics) — where clicking a button
inserts a ready-to-fill-in formula template with my own values and units, instead of having to
recall and type out the formula and a sensible set of variable names from memory every time. I want
this to work exactly the way the existing Elements/Algebra/Calculus tabs already do (one click,
text appears at my cursor, I fill in the blanks with SI-unit values), and I want every bundled
formula and constant to be expressed in SI units only.

## Behaviour (own words)

### The new tab
The side panel (`SidePanel`/`side-panel-tabs`) gains one new functional tab, **Chemical**, built
with the exact same mechanism spec 011's Elements tab already uses for a tab that bundles more than
one originally-distinct group: a scrollable, vertically stacked list of bordered buttons, split into
five sub-header groups (small grey labels, same style the Elements tab already uses), one per
sub-category below. Clicking any button calls the exact same `insert_token(token)` callback every
existing side-panel button already calls — a region is created/focused and the literal token text is
inserted at the cursor. No new interaction technique, no dialog, no wizard: this spec deliberately
keeps the "boring, generic" button-list mechanic spec 011 already used and the manager already
IP-approved, per `ip-cleanroom` rule 6.

**Where "Chemical" sits in the tab order** is an open question, not decided by this spec alone —
see Open questions below: backlog items 39 (Mechanical) and 40 (Electrical) are sibling tabs being
specced by other sessions in parallel, and all three new tabs are additions to the same
`TAB_ORDER` tuple/`sidepanel.py` module. This spec assumes "Chemical" is appended after today's
7 tabs (position 8 of however many exist once all three land) but takes no position on its order
*relative to* Mechanical/Electrical — that is the manager's call once all three specs are in hand.

### Template design: a bare, fill-in-the-blanks formula, not a wizard
Each button's token is a **complete, syntactically valid `name := expression` statement** using
this spec's own invented variable names (plain-English-rooted abbreviations with a descriptive
subscript, e.g. `n_A`, `m_sub`, `T_rxn` — never a vendor's own symbol set, and nowhere identical to
any one source's own worked-example notation). The one exception is the gas-constant button, which
inserts a *definition* of a literal SI-valued constant (`R_gas := 8.314 J/(mol*K)`) for the user to
reuse by name in every other gas-law/kinetics template that needs it, rather than repeating the
magic number inline each time. Clicking a button inserts the literal text; nothing is evaluated,
validated, or auto-filled by the click itself — the user then edits the placeholder names (or
leaves them, and defines them elsewhere on the sheet) and attaches whichever SI-consistent units
they want to each value, exactly the way every other quick-insert token and every existing
`:=`/`::=` definition on the sheet already works. This answers the open design question from the
task brief: **bare template, not a richer wizard** — consistent with spec 011's existing mechanism,
requires no new GUI code beyond the data table and the tab itself, and keeps this spec's IP risk at
the same low level as 011's already-approved button-list mechanic (ip-cleanroom rule 6 explicitly
prefers this "boring" option over a bespoke on-canvas assistant).

A side benefit requiring zero new code: several chosen variable names use the Greek-letter English
spellings LiveSheet's display layer already recognises (`rho_gas`, `rho_fluid`, `mu_fluid`) — once
typed, these already render as `ρ_gas`, `ρ_fluid`, `μ_fluid` in the non-editing view today, via the
unmodified `engine/formatting.py` `GREEK` dict and `gui/pretty.py` rendering spec 011 already
shipped. This spec does not depend on that rendering (plain ASCII names work identically for
evaluation), it is simply a side effect worth noting, not a new acceptance criterion.

### Categorisation (this specialist's own call, representative Phase 1 scope)
Five sub-categories, chosen to span the most commonly taught, foundational slice of
chemical-engineering calculation — not an attempt to cover the whole field in one spec (see
Phase 2 forward note below), the same "well-scoped first slice" posture spec 004/002 already took:

1. **Stoichiometry & Composition** — the basic amount/composition relationships every other
   category's formulas build on (amount of substance from mass, mass fraction, mole fraction, molar
   concentration).
2. **Ideal Gas & Thermodynamic State** — the gas constant, ideal gas law, ideal-gas density, and
   the two basic heat quantities (sensible, latent).
3. **Mass & Energy Balances** — conservation-of-mass and conservation-of-energy statements across
   a system boundary: steady-state overall and component mass balances, a dynamic (unsteady) mass
   balance, and a steady-state open-system energy balance.
4. **Fluid & Heat/Mass Transport** — one representative formula each for momentum (Reynolds
   number), heat (conductive flux, convective flux) and mass (diffusive flux) transport — the three
   transport phenomena chemical engineering courses conventionally teach side by side.
5. **Reaction Kinetics** — rate law, Arrhenius temperature dependence, first-order half-life, and
   fractional conversion.

**Phase 2 forward note (deferred, not specced here):** phase-equilibrium relationships (e.g.
Raoult's law, relative volatility), distillation/staged-separation concepts, psychrometrics,
reactor sizing design equations that need integration (CSTR/PFR design equations), multicomponent
mixture average molar mass, further dimensionless groups (Prandtl, Nusselt, Schmidt numbers), and
genuine differential/gradient-form transport laws (true Fourier's-law/Fick's-law gradient notation,
naturally expressed with the existing Calculus tab's `diff(`/`integrate(` tokens rather than this
tab's steady-state algebraic forms) are all left for a follow-up spec, exactly the way spec 011 left
Statistics/Optimization as placeholders for backlog 29/30.

## Syntax proposal (own keywords)
No grammar change. Every token below is already parseable by today's `:=` definition statement and
today's identifier rule (`livesheet/engine/syntax.py`'s `_IDENT = r"[^\W\d]\w*"`, any letter/
underscore start followed by any run of letters/digits/underscores) and today's arithmetic
operators (`+ - * / ^`) and already-supported functions (`exp`, `ln`). No new function, no new
operator, no `.lsheet` format change.

| Sub-category | Button label | Tooltip (own wording) | Inserted token |
|---|---|---|---|
| Stoichiometry & Composition | `n` | Amount of substance from mass and molar mass | `n_A := m_A / M_A` |
| Stoichiometry & Composition | `w` | Mass fraction of a component in a mixture | `w_A := m_A / m_total` |
| Stoichiometry & Composition | `x` | Mole fraction of a component in a mixture | `x_A := n_A / n_total` |
| Stoichiometry & Composition | `c` | Molar concentration (amount per solution volume) | `c_A := n_A / V_sol` |
| Ideal Gas & Thermodynamic State | `R` | Universal gas constant (SI) | `R_gas := 8.314 J/(mol*K)` |
| Ideal Gas & Thermodynamic State | `PV=nRT` | Ideal gas law | `P_gas := n_gas * R_gas * T_gas / V_gas` |
| Ideal Gas & Thermodynamic State | `ρ_gas` | Ideal-gas density from pressure, molar mass, temperature | `rho_gas := P_gas * M_gas / (R_gas * T_gas)` |
| Ideal Gas & Thermodynamic State | `Q_sens` | Sensible heat for a temperature change (no phase change) | `Q_sens := m_sub * c_p * (T_2 - T_1)` |
| Ideal Gas & Thermodynamic State | `Q_lat` | Latent heat for a phase change at constant temperature | `Q_lat := m_sub * L_phase` |
| Mass & Energy Balances | `ṁ bal.` | Steady-state overall mass balance (no accumulation) | `m_out := m_in` |
| Mass & Energy Balances | `comp. bal.` | Steady-state component mass balance with reaction | `m_A_out := m_A_in + m_A_gen - m_A_cons` |
| Mass & Energy Balances | `dm/dt` | Dynamic (unsteady) overall mass balance | `dm_dt := m_in_rate - m_out_rate` |
| Mass & Energy Balances | `energy bal.` | Steady-state open-system energy balance (no KE/PE change) | `Q_rate := m_flow_rate * (h_out - h_in) + W_rate` |
| Fluid & Heat/Mass Transport | `Re` | Reynolds number (inertial/viscous force ratio) | `Re := rho_fluid * v_flow * D_pipe / mu_fluid` |
| Fluid & Heat/Mass Transport | `Q_cond` | Steady 1-D conductive heat flow across a slab | `Q_cond := k_therm * A_surf * (T_hot - T_cold) / L_thick` |
| Fluid & Heat/Mass Transport | `Q_conv` | Convective heat flow at a surface | `Q_conv := h_conv * A_surf * (T_wall - T_fluid)` |
| Fluid & Heat/Mass Transport | `J_diff` | Steady 1-D diffusive molar flux across a film | `J_diff := D_ab * (c_A1 - c_A2) / L_film` |
| Reaction Kinetics | `rate law` | Power-law reaction rate expression | `r_rxn := k_rate * C_A^n_order` |
| Reaction Kinetics | `Arrhenius` | Temperature dependence of a rate constant | `k_rate := A_arr * exp(-E_act / (R_gas * T_rxn))` |
| Reaction Kinetics | `half-life` | Half-life of a first-order reaction | `t_half := ln(2) / k_rate` |
| Reaction Kinetics | `conversion` | Fractional conversion of a reactant | `X_A := (C_A0 - C_A) / C_A0` |

21 buttons total: 4 + 5 + 4 + 4 + 4.

## Acceptance criteria
1. `"side-panel-tabs"` gains an 8th tab named `"Chemical"` (exact position in `TAB_ORDER` relative
   to any already-landed Mechanical/Electrical tab is the manager's call — see Open questions);
   today's 7 tabs (Elements, Algebra, Calculus, Statistics, Optimization, Outline, Data) are
   unchanged in content, order relative to each other, and behaviour.
2. The Chemical tab contains exactly 21 clickable entries, in exactly 5 sub-header groups, in the
   counts given above (4, 5, 4, 4, 4); each group shows its own grey sub-header label (same style
   the Elements tab's "Statements"/"Constants"/"Greek letters" sub-headers already use), reusing
   `_build_functional_tab`'s existing multi-category support unchanged.
3. Clicking the `PV=nRT` button inserts the literal text `P_gas := n_gas * R_gas * T_gas / V_gas`
   at the cursor (same `insert_token` mechanism every existing button already uses). **Worked unit
   example**: given `R_gas := 8.314 J/(mol*K)`, `n_gas := 2 mol`, `T_gas := 300 K`,
   `V_gas := 0.05 m^3`, then `P_gas =` evaluates to approximately `99768 Pa` (≈ 99.8 kPa) — a
   pressure-dimensioned result, confirming the gas-constant/ideal-gas-law pair round-trips through
   LiveSheet's existing SI unit system with no unit error.
4. Clicking the `Q_sens` button inserts `Q_sens := m_sub * c_p * (T_2 - T_1)`. **Worked unit
   example**: given `m_sub := 5 kg`, `c_p := 4186 J/(kg*K)`, `T_1 := 290 K`, `T_2 := 350 K`, then
   `Q_sens =` evaluates to exactly `1255800 J` (1255.8 kJ). **Error case**: if `T_2` is instead
   defined with an incompatible unit (e.g. `T_2 := 350 Pa` by mistake), evaluating `Q_sens =` raises
   LiveSheet's existing `UnitError` ("Units do not match") — this spec adds no new error-handling
   code; it is the units engine's existing behaviour for subtracting incompatible dimensions,
   exercised here through a newly-inserted template rather than hand-typed text.
5. Clicking the `Re` button inserts `Re := rho_fluid * v_flow * D_pipe / mu_fluid`. **Worked
   dimensionless-check example**: given `rho_fluid := 1000 kg/m^3`, `v_flow := 2 m/s`,
   `D_pipe := 0.05 m`, `mu_fluid := 0.001 Pa*s`, then `Re =` evaluates to `100000` with an empty
   dimension set (confirms the formula is genuinely dimensionless, as the public Reynolds-number
   definition requires, and that LiveSheet's own unit system agrees without any new code).
6. Clicking the `energy bal.` button inserts
   `Q_rate := m_flow_rate * (h_out - h_in) + W_rate`. **Worked unit example**: given
   `m_flow_rate := 2 kg/s`, `h_out := 500 kJ/kg`, `h_in := 300 kJ/kg`, `W_rate := 0 kW`, then
   `Q_rate =` evaluates to `400 kW` (400 kJ/s).
7. Clicking the `x` button inserts `x_A := n_A / n_total`. **Worked dimensionless-check example**:
   given `n_A := 3 mol`, `n_total := 10 mol`, then `x_A =` evaluates to `0.3`, dimensionless.
8. For every one of the 21 rows in the table above, the button's label, tooltip, and inserted token
   text exactly match the table (no entry dropped, none duplicated, none altered).
9. Clicking any Chemical-tab button while another math region is mid-edit does not steal focus or
   overwrite that region's content — identical behaviour to every existing side-panel button
   (clicking creates/focuses a region and inserts at the cursor, same as spec 011's tokens).
10. None of the 21 inserted tokens collides with an existing reserved unit symbol as a bare
    identifier (e.g. the molar-concentration template deliberately uses `V_sol`, not bare `V`,
    because bare `V` is already LiveSheet's volt unit symbol in `engine/units.py`'s `UNITS` dict;
    similarly `R_gas`/`T_gas`/`A_surf`/`J_diff`/etc. are all multi-character names, never a bare
    `R`/`T`/`A`/`J`/... that would shadow or be shadowed by an existing unit token).

## Edge cases
- Clicking the same button twice on one sheet inserts the same `name := ...` text twice; if both
  land in scope as two definitions of the same symbol, that is the sheet's existing
  duplicate-definition behaviour (unchanged by this spec, same as any hand-typed duplicate
  definition today) — this spec adds no new duplicate-detection logic.
- A 120 px-wide panel showing 8 tab labels and a 21-entry Chemical tab relies on Qt's existing
  tab-bar overflow/elide and the existing `QScrollArea` mechanism the Elements tab already
  exercises at 40 entries — no new overflow-handling code, same posture as spec 011.
- The gas-constant button (`R_gas := 8.314 J/(mol*K)`) is the only template in this spec that
  hard-codes a numeric literal; every other template is pure placeholder algebra, so there is
  nothing else in this spec for a future SI-value update (e.g. a CODATA revision of R) to touch
  besides that one row — flagged for cross-reference with backlog 8a(ii)'s separate
  constants/steam-tables effort (see Open questions).
- A user who fills in a template with non-SI units today (LiveSheet's unit system already accepts
  `psi`, `lb`, `ft`, etc. for general engineering use) is not prevented by this spec — "SI units
  only" is a constraint on what *this spec itself* ships as literal constants/examples, not a new
  input-validation feature restricting what a user may type; LiveSheet's general-purpose unit
  system is unchanged and continues to accept any unit it already accepts today.
- The `comp. bal.` and `energy bal.` templates assume (as stated in their own tooltips) steady
  state and, for the energy balance, no kinetic/potential energy change — simplifying assumptions
  standard to an introductory treatment, not claimed as universally applicable; a user doing a more
  general balance types their own, unconstrained by this tab.

## IP check
Pass. Every formula above is long-public-domain physical chemistry / chemical engineering
(oldest: Fourier's law, 1822; Fick's laws, 1855; ideal gas law in this form, 1834; Arrhenius
equation, 1889 — all well over a century old; the rest are standard 20th-century engineering
curriculum with no identifiable single originator to attribute). `docs/IP-POLICY.md`'s "Allowed"
list explicitly covers "mathematical methods, algorithms and concepts" and "standard math/
engineering notation... and common function names" — nothing below exceeds that.

- **No vendor's own formula palette, "Quick Sheet," or packaged worksheet library was read.** The
  five-category breakdown (Stoichiometry/Composition, Gas & Thermodynamic State, Mass & Energy
  Balances, Transport, Reaction Kinetics) is this specialist's own grouping, arrived at from the
  generic public sources cited above and ordinary chemical-engineering-curriculum topic boundaries
  (the same topic split any introductory textbook table of contents uses), not copied from any one
  vendor's own category names or button layout.
- **No vendor symbol set or worked example reproduced.** Every variable name (`n_A`, `m_sub`,
  `T_rxn`, `rho_gas`, etc.) was invented for this spec: standard single/double-letter chemistry
  symbols (n, m, M, w, x, c, R, P, T, V, ρ, Q, Re, k, A, h, D, J, Ea, t, X — all centuries-old
  universal notation, explicitly on the IP-POLICY "Allowed" list) combined with this spec's own
  descriptive subscript convention, not reproducing any single source's own notation choices
  (e.g. some textbooks use `y` for mole fraction instead of `x`, use `Cp` instead of `c_p`, or index
  species with numbers instead of letters — this spec picked one self-consistent convention of its
  own rather than copying any one source's).
- **No new on-canvas interaction technique** (ip-cleanroom rule 6): the Chemical tab is exactly the
  same dockable-panel-plus-click-to-insert-button chrome spec 011 already shipped and the manager
  already IP-approved for Elements/Algebra/Calculus — nothing bespoke, nothing drawn on the
  worksheet canvas itself.
- **SI-only hard constraint honoured throughout**: the one hard-coded physical constant
  (`R_gas := 8.314 J/(mol*K)`) and every worked numeric example in this spec use only SI or
  SI-derived units (`mol`, `kg`, `K`, `J`, `Pa`, `m^3`, `m`, `s`, and SI-prefixed derivatives like
  `kJ`, `kW`) — no imperial/US-customary unit (`psi`, `lb`, `°F`, `BTU`, `ft`, etc.) appears
  anywhere in this spec's templates, constants, or examples.
- **No overlap claimed with backlog 8a(ii)**: this spec is about formula *relationships* a user
  fills in with their own numbers; it adds no reference data table (no CODATA constant list, no
  steam-table lookup) — the single `R_gas` literal is a formula input a user could also type by
  hand today, not a new "built-in dataset" feature.

Not legal advice.

## Fits current architecture?
- **`livesheet/gui/sidepanel.py`**: add a new module-level list for this spec's 21 entries — this
  specialist recommends a dedicated name (e.g. `CHEM_TOKENS`, own naming, exact name is the
  developer's choice) rather than appending into the existing `MATH_TOKENS` list, so that this
  spec's data and any sibling Mechanical/Electrical spec's data (items 39/40, specced in parallel
  by other sessions, destined for the same file) stay in clearly separated, independently reviewable
  blocks rather than one another's close neighbours in a single growing list — the developer
  implementing whichever of the three specs lands first should leave an obvious seam (e.g. a
  shared tiny helper that turns a `(sub-category, label, token, tip)` list plus a tab name into a
  `TAB_CATEGORIES` entry) for the other two to slot into without reshaping shared code each time.
  Add one new entry to `TAB_CATEGORIES` (`"Chemical": (...)` naming this spec's 5 sub-category
  strings) and one new entry to `TAB_ORDER` (exact position: see Open questions). No change to
  `_build_functional_tab`, `_build_placeholder_tab`, or any existing tab's data.
- **`livesheet/gui/main_window.py`**: no change — the Chemical tab needs no new menu entry,
  toolbar, or keyboard shortcut; it is reached exactly the way Elements/Algebra/Calculus already
  are, by opening the side panel and selecting its tab.
- **`livesheet/engine/*`**: unchanged. Every template parses with today's grammar
  (`:=`, identifiers, `+ - * / ^`, `exp`, `ln`) and today's unit system
  (`livesheet/engine/units.py`'s existing `UNITS` dict already has `mol`, `kg`, `K`, `J`, `Pa`,
  `m^3`/`m**3`, `L`, and SI-prefixed variants) — no new unit, no new function, no new evaluator
  keyword, no `.lsheet` format-version bump.
- Tests: new `tests/test_chemical_formula_tab.py` covering criteria 1-2 and 8-10 via
  `objectName`/tab-text/sub-header lookups and exact label/token/tooltip-string equality against
  the table above, plus a parse-and-evaluate round trip (construct each of the 21 templates with a
  representative filled-in value set and confirm no unexpected exception) and the worked
  numeric/unit examples in criteria 3, 4 (including its error case), 5, 6, 7 as explicit
  `measure()`/evaluation assertions. The tester should also do a real-window pass on Theo's Mac
  once this ships: open the side panel, switch to the Chemical tab, click through all 5 sub-header
  groups, insert at least one template per group into a real math region, fill in one with concrete
  SI values and confirm the on-screen result looks right (e.g. the ideal-gas-law or sensible-heat
  worked example above), and confirm the tab coexists correctly with whichever of Mechanical/
  Electrical has landed by then (no missing/duplicated/misordered tab).

## Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. **Tab order among the three new M8 tabs.** Mechanical (39) and Electrical (40) are being specced
   in parallel by other sessions; all three append to the same `TAB_ORDER`/`sidepanel.py`. This spec
   takes no position on Chemical's order relative to the other two (only that it comes after today's
   existing 7 tabs). [Recommend the manager decide the final merged order once all three specs are
   in hand — e.g. alphabetical (Chemical, Electrical, Mechanical) is a simple, defensible,
   non-arbitrary tie-break if Theo has no preference — and record the decision in decisions.md so
   whichever spec implements last doesn't have to guess.]
2. **Phase 1 scope boundary** (categorisation and the 21-formula selection above): is this
   specialist's own five-category split and representative-formula choice an acceptable first
   slice, or does Theo want a different emphasis (e.g. more composition/phase-equilibrium content
   before kinetics, or vice versa) before implementation? [Recommend accepting as scoped; the
   Phase 2 forward note above already lists the main deferred topics for a follow-up spec.]
3. **Bare-template insertion mechanism** (vs. a richer dialog/wizard): this spec commits to the
   plain "click inserts literal fill-in-the-blanks text" mechanism, identical to every existing
   side-panel button. [Recommend accepting — matches spec 011's already-approved mechanism exactly,
   avoids any new widget, and keeps IP risk at the same already-cleared level; flagging only because
   the task brief explicitly named this as an open design call.]
4. **`CHEM_TOKENS` as a separate data list vs. appending to `MATH_TOKENS`**: a minor architecture
   call, recommended above to reduce collision risk with the parallel Mechanical/Electrical specs
   touching the same file. [Recommend accepting; the developer may rename the list, this is not a
   behavioural requirement.]
5. **The one hard-coded constant (`R_gas := 8.314 J/(mol*K)`) vs. backlog 8a(ii)'s future
   constants library**: once 8a(ii) ships a built-in CODATA-sourced constants feature, should this
   spec's `R` button be revisited to reference that instead of its own literal? [Not blocking for
   this spec — recommend leaving as a forward note for whoever implements 8a(ii) to reconcile, since
   8a(ii) does not exist yet.]
