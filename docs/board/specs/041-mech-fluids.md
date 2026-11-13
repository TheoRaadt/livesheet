# 041 Mechanical library phase 3a: fluid statics, flow rates, Reynolds number, pipe losses

Status: IP-reviewed by manager 2026-11-13 (generic textbook formulas, own names, no vendor keywords/tables; APPROVED once Theo answers the open questions; developer must re-run every hand-computed criterion through Engine()). Original: NOT yet IP-reviewed. Specialist proposal (mathcad-specialist, 2026-11-13).
Parent: spec 033 (library overview, "General rules" 1-9, phase 1 builder in livesheet/engine/mecheng.py).
Sibling: spec 040 (phase 2). Phase 3b (implicit Colebrook friction factor) is an outline only at the end.

Numbers: NO execution tool was available to the specialist in this session. Every value below was computed
by hand (pi to 8 digits, standard gravity 9.80665 m/s^2 as fixed in this spec) and cross-checked where a
second route exists (a ratio, an identity between two functions, or a pressure-equals-density-times-gravity
check). The developer must re-run every criterion through `Engine().evaluate(...)` before this spec is
treated as final; a mismatch beyond tolerance goes back to the specialist (spec 033 process).

Source inspiration (concept and formulas only; nothing copied):
- Public Wikipedia articles listed in docs/board/research/mech-eng-topics.md (accessed 2026-11-12, CC BY-SA
  4.0, facts only): Darcy-Weisbach equation (head loss; laminar friction factor 64/Re), Hagen-Poiseuille
  equation (laminar pipe pressure drop), Reynolds number, Bernoulli's principle (documented only, see below).
- Hydrostatic pressure, mean velocity and dynamic pressure are general textbook fluid mechanics.
  The specialist did not re-fetch the listed pages in this session; the manager should confirm them during
  IP review (see IP check).

User story:
As an engineer checking a pipe or a tank, I want hydrostatic pressure, flow rates, velocities, the Reynolds
number and pipe pressure losses as ready-made functions, called with my own values and units, dimensions
checked and results in SI, so that I do not mix up litres per second with cubic metres per second or bar
with Pa, and do not re-derive Darcy or Hagen-Poiseuille each time.

## Behaviour (own words)

### Inherited rules
All general rules 1-9 of spec 033 apply: positional calls, dimension check per argument, bare number in a
dimensional slot is an error, dimensionless slot with a unit is an error, SI results, pure functions,
LiveSheet's own error wording `<function>: <argument> <problem>`, SI-only (no imperial units, no
non-SI-prefixed unit names in examples; litres are not used in examples, and `L` is never an argument name).
Spec 040 Addition A (bound "not negative") is used here for the depth argument.

### Specific rules
A. Standard gravity g0 = 9.80665 m/s^2 is written into the two functions that need gravity
   (`hydrostatic_pressure`, `darcy_head_loss`). The engine's `g` unit is NOT used (spec 018 single-letter
   trap, spec 033 OQ4 recommendation; Theo to confirm, OQ1).
B. Dimension vocabulary additions (same `_DIMS` table as phase 1 / spec 040):

   | Name | SI unit expression | Hint example |
   |---|---|---|
   | density | kg/m^3 | 1 kg/m^3 |
   | velocity | m/s | 1 m/s |
   | volume flow | m^3/s | 1 m^3/s |
   | mass flow | kg/s | 1 kg/s |
   | dynamic viscosity | Pa*s | 1 Pa*s |
   | kinematic viscosity | m^2/s | 1 m^2/s |

   Equal base dimensions: `mass flow` and spec 040's `damping coefficient` are both kg/s, and
   `dynamic viscosity` (Pa*s) is kg/(m s). The check compares base dimensions, so these are interchangeable.
   Stated in the manual, not fixed here.
C. Gauge pressure only. `hydrostatic_pressure` returns the pressure above the free surface (no atmospheric
   term). The manual says so.
D. Validity (stated, not enforced; no warning mechanism exists, backlog 9): Hagen-Poiseuille and the
   64/Re friction factor are laminar results (commonly quoted upper Reynolds limit around 2000 to 2300,
   depending on source). Darcy-Weisbach with a given friction factor is valid for any regime, the friction
   factor carries the regime. The functions do not check the regime.
E. Bernoulli's equation is documented in the manual as a formula, not as a function in phase 3a (see OQ5).

## Phase 3a: function list (developer-ready)

Notation: rho density, vel velocity, flow volume flow, area area, dia pipe diameter (length),
pipe_len pipe length, mu dynamic viscosity, nu kinematic viscosity, fric Darcy friction factor (dimensionless),
Re Reynolds number (dimensionless), depth depth below the free surface (length). Results SI.

Pressure and flow:

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| P1 | `hydrostatic_pressure(rho, depth)` | rho: density; depth: length, must not be negative | p = rho g0 depth, g0 = 9.80665 m/s^2 | pressure (gauge) |
| P2 | `mean_velocity(flow, area)` | flow: volume flow; area: area | v = Q/A | velocity |
| P3 | `volume_flow(vel, area)` | vel: velocity; area: area | Q = v A | volume flow |
| P4 | `mass_flow(rho, flow)` | rho: density; flow: volume flow | m_dot = rho Q | mass flow |
| P5 | `dynamic_pressure(rho, vel)` | rho: density; vel: velocity | q = rho v^2/2 | pressure |

Dimensionless groups:

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| D1 | `reynolds_number(rho, vel, dia, mu)` | rho: density; vel: velocity; dia: length; mu: dynamic viscosity | Re = rho v d/mu | dimensionless |
| D2 | `reynolds_number_kinematic(vel, dia, nu)` | vel; dia; nu: kinematic viscosity | Re = v d/nu | dimensionless |
| D3 | `laminar_friction_factor(Re)` | Re: dimensionless, greater than zero | fric = 64/Re (laminar Darcy friction factor) | dimensionless |

Pipe losses (fully developed flow in a straight circular pipe):

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| L1 | `laminar_pipe_pressure_drop(mu, pipe_len, flow, dia)` | mu: dynamic viscosity; pipe_len: length; flow: volume flow; dia: length | dp = 128 mu L Q/(pi d^4) (Hagen-Poiseuille, laminar) | pressure |
| L2 | `darcy_pressure_drop(fric, pipe_len, dia, rho, vel)` | fric: dimensionless; pipe_len, dia: length; rho: density; vel: velocity | dp = fric (L/d) rho v^2/2 | pressure |
| L3 | `darcy_head_loss(fric, pipe_len, dia, vel)` | as L2 without rho | h_f = fric (L/d) v^2/(2 g0), metres of fluid | length |

Phase 3a total: 11 functions (P1-P5, D1-D3, L1-L3).

Phase 3b (outline only, separate spec 041b later; not in this slice):
`colebrook_friction_factor(Re, rough_rel)`: implicit relation 1/sqrt(fric) = -2 log10(rough_rel/3.7 +
2.51/(Re sqrt(fric))) for turbulent flow, solved with a bracketed root finder (scipy, already approved, BSD).
Needs its own acceptance criteria computed with the root finder, not by hand (the specialist will not hand-derive
a root). rough_rel is the relative roughness (dimensionless, no unit).

## Syntax proposal (own keywords)
None. Function calls only, existing grammar. No `.lsheet` change. Example calls:
`hydrostatic_pressure(1000 kg/m^3, 2 m)`, `darcy_head_loss(0.02, 100 m, 0.1 m, 2 m/s)`.

## Implementation placement (developer)
- New module `livesheet/engine/fluids.py` (Qt-free), exposing `FLUID_BUILTINS` with the 11 names. It reuses
  the builder, the bound option and the dimension table of `livesheet/engine/mecheng.py` (spec 040 Addition A
  and F added there; one dimension table, not two).
- `livesheet/engine/evaluator.py` `_builtins()`: `g.update(FLUID_BUILTINS)` after `MECH_BUILTINS`, same
  pattern as the existing merges.
- Development rule: no name equals a `BUILTINS` key, `UNITS` key or `syntax.py` keyword; test in code. The
  names `reynolds_number`, `mass_flow` and the others must not collide with spec 040 names.
- Argument names in hints: as the function table (`flow`, `depth`, `pipe_len`, `fric`, `Re`, ...).

## Acceptance criteria

Tolerance 1e-5 relative unless stated. Where the display rounds to 6 significant digits, the test calls the
builtin directly and compares to 1e-9 relative. Display units are requested explicitly.

### Registration and naming
1. All 11 names are callable in a math region and appear in the existing autocomplete with their argument
   names (spec 024), no change to autocomplete code.
2. No name equals a `BUILTINS`, `UNITS` or `syntax.py` keyword; no name equals a spec 033 or spec 040 name
   (set intersection empty, test in code).
3. `fluids.py` imports no PySide6 (grep-level test). `.lsheet` unchanged.
4. Wrong argument count: `darcy_head_loss(0.02, 100 m, 0.1 m)` gives the existing "Wrong number of arguments"
   family of error, no traceback.

### Unit rules
5. Bare number in a dimensional slot: `hydrostatic_pressure(1000, 2 m)` gives
   `hydrostatic_pressure: rho needs a unit of density, for example 1 kg/m^3`.
6. Wrong dimension: `mean_velocity(1 kg, 2000 mm^2)` gives `mean_velocity: flow must be a volume flow, not kg`.
7. Dimensionless slot with a unit: `darcy_head_loss(0.02 m, 100 m, 0.1 m, 2 m/s)` gives
   `darcy_head_loss: fric must be dimensionless`.
8. Pressure as viscosity: `reynolds_number(1000 kg/m^3, 1.25 m/s, 25 mm, 1 Pa)` gives
   `reynolds_number: mu must be a dynamic viscosity, not Pa`.
9. Mixed input units are accepted and results are SI: `hydrostatic_pressure(1000 kg/m^3, 2000 mm) = kPa`
   gives 19.6133 kPa (same as criterion 10).

### Pressure and flow (hand values; tolerance 1e-5)
10. `hydrostatic_pressure(1000 kg/m^3, 2 m) = kPa` gives 19.6133 kPa (1000 x 9.80665 x 2 = 19613.30 Pa).
11. `mean_velocity(0.0025 m^3/s, 2000 mm^2) = m/s` gives 1.25 m/s (2000 mm^2 = 0.002 m^2).
12. `volume_flow(1.25 m/s, 2000 mm^2) = m^3/s` gives 0.0025 m^3/s. Check: criterion 12 divided by criterion 11
    area gives back 1.25 (identity P2/P3 within 1e-9).
13. `mass_flow(1000 kg/m^3, 0.0025 m^3/s) = kg/s` gives 2.5 kg/s.
14. `dynamic_pressure(1000 kg/m^3, 1.25 m/s) = Pa` gives 781.25 Pa (0.5 x 1000 x 1.5625).

### Dimensionless groups (tolerance 1e-5)
15. `reynolds_number(1000 kg/m^3, 1.25 m/s, 25 mm, 0.001 Pa*s)` (bare) gives 31250 (1000 x 1.25 x 0.025 / 0.001).
16. `reynolds_number_kinematic(1.25 m/s, 25 mm, 1e-6 m^2/s)` (bare) gives 31250. Check: equals criterion 15
    (both are the same number when mu = rho nu, within 1e-9).
17. `laminar_friction_factor(1000)` (bare) gives 0.064.

### Pipe losses (tolerance 1e-5)
18. `laminar_pipe_pressure_drop(0.001 Pa*s, 10 m, 0.0001 m^3/s, 20 mm) = Pa` gives 254.648 Pa
    (128 x 0.001 x 10 x 1e-4 = 1.28e-4; pi x (0.02)^4 = 5.0265e-7; ratio 254.648 = 800/pi).
19. Identity check of L1 against L2: with v = Q/(pi d^2/4) = 0.318310 m/s (criterion 18 inputs), Re = 6366.20
    (1000 x 0.318310 x 0.02 / 0.001) and fric = laminar_friction_factor(Re) = 0.0100531,
    `darcy_pressure_drop(0.0100531, 10 m, 20 mm, 1000 kg/m^3, 0.318310 m/s) = Pa` gives 254.648 Pa (same value
    as criterion 18). This holds because Darcy with 64/Re reduces to Hagen-Poiseuille. Tolerance 1e-4 relative
    (the friction factor is typed to 6 digits). The Reynolds number here is above the laminar range; the
    identity is algebraic, not a regime statement.
20. `darcy_pressure_drop(0.02, 100 m, 0.1 m, 1000 kg/m^3, 2 m/s) = kPa` gives 40 kPa
    (0.02 x 1000 x 1000 x 4 / 2).
21. `darcy_head_loss(0.02, 100 m, 0.1 m, 2 m/s) = m` gives 4.07886 m (80 / 19.6133).
    Check: rho g0 x criterion 21 value = criterion 20 value (1000 x 9.80665 x 4.078865 = 40000 Pa within 1e-6).

### Errors (each gives a LiveSheet message, no traceback, no result)
22. Negative depth: `hydrostatic_pressure(1000 kg/m^3, -2 m)` gives
    `hydrostatic_pressure: depth must not be negative`.
23. Zero or negative positive-only input: `mean_velocity(-0.0025 m^3/s, 2000 mm^2)` gives
    `mean_velocity: flow must be greater than zero`. (Negative flow is rejected; it is a magnitude here.)
24. Bare number in velocity slot: `darcy_head_loss(0.02, 100 m, 0.1 m, 2)` gives
    `darcy_head_loss: vel needs a unit of velocity, for example 1 m/s`.
25. Re out of range: `laminar_friction_factor(-100)` gives `laminar_friction_factor: Re must be greater than zero`.
26. Undefined name inside a call: `darcy_head_loss(fric, pipe_len, dia, vel)` with nothing defined gives the
    existing `fric, pipe_len, dia, vel are not defined` message.

## Edge cases
- Hydrostatic pressure at depth 0: the result is a zero pressure; the engine drops the unit of a zero (backlog
  81), so `= Pa` on a zero result fails. Tests use depth 2 m, and the manual notes this for zero depth.
- Standard gravity 9.80665 m/s^2 is the defined value; a user wanting another local gravity multiplies the
  result by their own factor (not supported as an argument in this phase).
- Pipe loss functions assume a straight circular pipe, fully developed flow, constant properties, no minor
  losses (fittings, bends, valves are not in phase 3a).
- Darcy-Weisbach head loss and pressure drop use the same fric; they differ by rho g0 only (criterion 21 check).
- `laminar_friction_factor` is only the laminar branch; the turbulent friction factor needs phase 3b.
- Velocity and flow are magnitudes; the functions reject zero and negative positive-only inputs.
- Mixed units: `dia` as 25 mm and 0.025 m give the same Reynolds number (criterion 15 check, mixed-unit form).

## GUI-1 (Mechanical tab, same mechanism as spec 034 GUI-1; after spec 040's GUI-1)
GUI-1. The Mechanical tab keeps its existing groups and spec 040's new sub-headers, and gains three
sub-headers in this order: "Pressure & Flow", "Dimensionless Numbers", "Pipe Losses". TAB_ORDER unchanged.
GUI-2. Exactly 11 new buttons, one per phase 3a function. Each calls `insert_token(token)`. No new widget,
no dialog, no on-canvas editing, no keyboard shortcut.
GUI-3. Button list (label | inserted text | tooltip; SI only, each tooltip states input and result units):
- Pressure & Flow: "hydrostatic pressure" | `hydrostatic_pressure(rho, depth)` | gauge p = rho g0 depth; rho in kg/m^3, depth in m; result Pa. | "mean velocity" | `mean_velocity(flow, area)` | m/s from m^3/s and m^2. | "volume flow" | `volume_flow(vel, area)` | m^3/s from m/s and m^2. | "mass flow" | `mass_flow(rho, flow)` | kg/s from kg/m^3 and m^3/s. | "dynamic pressure" | `dynamic_pressure(rho, vel)` | Pa from kg/m^3 and m/s.
- Dimensionless Numbers: "Reynolds number" | `reynolds_number(rho, vel, dia, mu)` | dimensionless; rho kg/m^3, vel m/s, dia m, mu Pa*s. | "Reynolds, kinematic" | `reynolds_number_kinematic(vel, dia, nu)` | nu in m^2/s. | "laminar friction factor" | `laminar_friction_factor(Re)` | 64/Re, laminar only; dimensionless.
- Pipe Losses: "laminar pipe pressure drop" | `laminar_pipe_pressure_drop(mu, pipe_len, flow, dia)` | Pa; laminar only. | "Darcy pressure drop" | `darcy_pressure_drop(fric, pipe_len, dia, rho, vel)` | Pa. | "Darcy head loss" | `darcy_head_loss(fric, pipe_len, dia, vel)` | m of fluid.
GUI-4. Placeholder names avoid unit letters and the engine's specials (L, g, E, I, C, e, T, N, m, s, A, V, W, K,
F, H, J, Pa): rho, depth, flow, area, vel, dia, mu, nu, Re, pipe_len, fric. `pipe_len` and `flow` are plain
words. An unfilled template gives "... is not defined".
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change.
GUI-6. Regression: the existing Mechanical groups and spec 040 buttons are unchanged in label, text and order.

## Phase 3b (outline only; needs its own spec 041b)
- `colebrook_friction_factor(Re, rough_rel)`, implicit, turbulent only (Re above the laminar range).
- Root finder: scipy `brentq` on a bracket (BSD-3, approved). Bracket and tolerance stated in 041b.
- Criteria computed with the root finder (not by hand), with a laminar-range error message.
- Requires a second check against an open-source numerical oracle (not shipped), per the ip-cleanroom rule 7(d).

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Standard gravity: write 9.80665 m/s^2 into `hydrostatic_pressure` and `darcy_head_loss` (proposed) or use
   the engine's `g` (spec 018 trap). Recommendation: explicit constant (as spec 033 OQ4). Confirm.
2. Gauge pressure only in `hydrostatic_pressure`, no atmospheric term. Confirm.
3. Include the laminar friction factor `64/Re` (D3) in phase 3a? Recommendation: yes; it is the link between
   Darcy and Hagen-Poiseuille and needs no solver.
4. Millipascal-second: `mPa` is not a defined unit (only Pa, kPa, MPa, GPa). Example users would write
   `0.001 Pa*s`. Add `mPa` to units.py as a separate small decision? Recommendation: yes, separate decision.
5. Bernoulli's equation: documented in the manual only, no function in phase 3a. Confirm, or add a
   head-sum function in phase 3b.
6. No flow-regime warning (backlog 9). The manual states the validity limits (Addition D). Confirm.
7. Phase 3b (Colebrook, root finder) as a separate spec 041b after 041 is accepted. Confirm timing.
8. Size: 11 functions in one slice, about 2 days (spec 033). Confirm.
9. Hand-computed numbers: the specialist could not run them. The developer re-runs all criteria; mismatches
   return to the specialist. Confirm this step before IP review.

## IP check
Pass, pending manager review. Own function names, argument names, GUI wording and tooltips. Formulas are
generic textbook relations: hydrostatic pressure, flow continuity (Q = vA), mass flow, dynamic pressure,
Reynolds number, the laminar friction factor 64/Re, Hagen-Poiseuille pipe pressure drop, Darcy-Weisbach head
loss and pressure drop, and (phase 3b only) the Colebrook relation. Facts taken from the public Wikipedia pages
listed in docs/board/research/mech-eng-topics.md (accessed 2026-11-12, CC BY-SA 4.0, facts only) and from
general fluid mechanics. No vendor manual, menu, keyword, example problem, table or numbering used. No
copyrighted table, no standards data (no pipe-schedule, roughness or fluid-property table: all example
viscosities and densities are round numbers chosen for the examples, not material data). No new UI technique.
Caveat: the listed pages were not re-fetched in this session; the manager confirms each formula during IP
review. Not legal advice; legal review before 1.0 is a standing item.

## Fits current architecture?
- `livesheet/engine/fluids.py` (new, Qt-free) with `FLUID_BUILTINS`, merged in `evaluator._builtins()` after
  `MECH_BUILTINS`, the same pattern as the phase 1 and electrical merges.
- `livesheet/engine/mecheng.py` (phase 1 / 040 file): reused builder; dimension table gains the six fluids
  entries (density, velocity, volume flow, mass flow, dynamic viscosity, kinematic viscosity).
- `livesheet/engine/units.py`: unchanged unless OQ4 is approved (then only `mPa` is added).
- `livesheet/gui/sidepanel.py`: 11 tuples in one token list; three new sub-headers in
  `TAB_CATEGORIES["Mechanical"]` after spec 040's sub-headers.
- No `.lsheet` change, no new dependency in 3a (3b uses scipy, already approved).
- Tests: `tests/test_fluids.py` (developer, from this spec); independent black-box file by the tester from this
  spec only; GUI button checks in the tester's file.
