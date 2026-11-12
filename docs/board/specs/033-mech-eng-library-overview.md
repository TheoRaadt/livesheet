# 033 Mechanical-engineering function library: overview, roadmap and phase 1

Status: NOT yet IP-reviewed by manager. Specialist proposal. Phase 1 becomes developer-ready only after
(a) manager IP review and (b) a re-run of every numeric example in section "Acceptance criteria" against the
live engine (no Bash was available to the specialist; all numbers below are hand-derived, same process as
spec 017's verification note). Phases 2 to 7 are outline only and each needs its own follow-up spec.
Amended 2026-11-12 for Theo's SI rule (see "General rules", items 5 and 9): results SI, no imperial units.

Spec-numbering note: 033 is the first free number when this file was written (2026-11-12; the highest
existing spec is 032). Backlog item: proposed new item (see "Backlog" at the end). Relates to backlog 39-41
(formula tabs, spec 018-020) and backlog 8a(ii) (steam tables, constants). Sibling: spec 034 (electrical library).

Source inspiration (concept only, nothing copied):
- Research note docs/board/research/mech-eng-topics.md (2026-11-12): subject-area outline, public sources,
  IP statement. Public Wikipedia articles listed there (CC BY-SA 4.0, facts only, accessed 2026-11-12):
  Second moment of area, Euler-Bernoulli beam theory, Deflection (engineering), Euler buckling, Pressure
  vessel, Mohr's circle, Torsion (mechanics), Gear train, Hertzian contact stress, Natural frequency, Damping
  ratio, Bernoulli's principle, Darcy-Weisbach equation, Reynolds number, Hagen-Poiseuille equation, Fourier's
  law, Newton's law of cooling, Stefan-Boltzmann law, Radiative heat transfer, Ideal gas law, Carnot's
  theorem, Thermocouple.
- Subject-area nouns only from a product-listing search summary (see research note 1a). No vendor manual, menu,
  keyword, example, table, numbering or ordering was used.

User story:
As an engineer writing a calculation sheet, I want standard mechanical-engineering formulas (beam
deflection, bending stress, column buckling, pressure-vessel stress, ...) as ready-made functions I can call
in a math region with my own values and units, and get a result with the right units checked, so that I do
not re-type or re-derive the formula each time and do not silently mix up N and kN or mm and m.

## Behaviour (own words)

### General rules for every function in this library (all phases)
1. Calling convention: an ordinary function call in a math region, `name(arg1, arg2, ...)`, positional
   arguments only, no keyword arguments. Argument names below are documentation only (they appear in
   autocomplete call hints, like existing builtins).
2. Dimensions: each argument has a declared dimension (length, area, second moment of area, force, force per
   length, moment, pressure, dimensionless, ...). Every dimensional argument must carry a unit of the right
   dimension. A bare number in a dimensional slot is an ERROR, not silently SI (see Open question 1).
3. Dimensionless arguments (ratios such as K, numbers of coils, slenderness) must NOT carry a unit.
4. Dimensional mismatch is an error. Non-positive lengths, areas, moduli, thicknesses and similar inputs are
   errors ("must be greater than zero"). Specific ordering rules (e.g. outer diameter larger than inner) are
   errors.
5. Results are SI. Every result is returned in SI base units (m, m^2, m^4, m^3, N, Pa, N*m, rad, ...) regardless
   of the input units. Users may ask for a decimal SI-prefixed display unit with the existing `= <unit>`
   syntax (for example `= mm`, `= kN`, `= MPa`, `= N*m`). This is allowed because the prefixed unit is an SI
   unit. A bare `=` prints base SI (for example `m` instead of `mm`), and a bare moment prints as `J` rather
   than `N*m` (existing engine behaviour, documented in spec 018).
6. Functions are pure: no state, no sheet-wide effect, no `.lsheet` change, no GUI change.
7. Error text is LiveSheet's own wording, of the form `<function>: <argument> <problem>`, and never a Python
   traceback. The exact wording below is the proposal; tests should match the quoted fragment.
8. Accuracy: results are exact closed-form textbook formulas in double precision. No table lookup, no
   iteration, no rounding of constants other than the values taken from scipy.constants (see phase 4).
9. SI only (Theo, 2026-11-12). Every input accepts any unit that is dimensionally compatible with it
   (for example `mm` or `m` for a length, `GPa` or `Pa` for a modulus). The library itself defines, accepts in
   examples, and documents no imperial or US customary unit (no inch, foot, pound-force, psi, ksi, mil, BTU,
   degree Fahrenheit, and so on). Angles are radians: this library has no degree input or helper (phase 1
   takes angles only where a formula needs one, and phase 1 has none). Frequency is in Hz, never rpm.

### Phase plan (roadmap)
| Phase | Scope | Size guess | Dependencies | Status |
|---|---|---|---|---|
| 1 | Mechanics-of-materials core: section properties of plane shapes, beam deflection and maximum-moment cases, axial/bending/thin-wall stress, Euler column buckling | 2-3 days | none (numpy/sympy already approved) | developer-ready (detail below) |
| 2 | Torsion and plane stress (shaft shear/twist/power, Mohr's circle principal stress, max shear, rotated stress), statics basics (resultant of two forces, force components, friction limit), 1-DOF vibration (natural frequency, damped frequency, damping ratio, log decrement) | 2-3 days | phase 1 | outline, needs spec 040 |
| 3 | Fluid mechanics: hydrostatic pressure, mean velocity, dynamic pressure, Reynolds number, laminar pipe pressure drop, Darcy-Weisbach head loss with a given friction factor; then (3b) friction factor from the implicit Colebrook relation | 2 days (3a), 1 day (3b) | phase 1; 3b needs a root finder (scipy, already approved) | outline, needs spec 041 |
| 4 | Heat transfer and thermodynamics: conduction, convection, radiation exchange, series thermal resistance, heat rate; ideal-gas four forms, Carnot efficiency | 2 days | phase 1; constants from scipy.constants; backlog 6 for Celsius-input temperatures | outline, needs spec 042 |
| 5 | Machine elements: spur-gear pitch/centre distance/speed ratio/gear trains, helical spring rate and combinations (source to confirm first), Hertz sphere-on-plane contact stress, bolt preload from torque (user-entered stress area), basic bearing life, von Mises combined stress | 3 days | phases 1-2; standards data excluded (section 4 of research note) | outline, needs spec 043 |
| 6 | Reference data: material properties and section tables. Only after a licence decision (Open question 5). Default until then: user-entered values only | depends on licence | Theo decision | outline, blocked on decision |
| 7 | Extra numerical methods: forced vibration and transmissibility, lumped-capacitance transient (reuse spec 010 ODE machinery), Rankine/Otto/Brayton ideal cycles, Johnson column formula | 3+ days | phases 3-5 | outline only |

### Phase 1: function list (developer-ready)
Notation: L = length, A = area, I = second moment of area (L^4), F = force, p = pressure (F/L^2),
w = force per length (F/L), M = moment (F*L). "dimensionless" = no unit allowed. Result dimension in the
last column. All results SI.

Section properties (all about the centroidal axis; plane shapes; no rolled-section tables):
| # | Function (argument order) | Arguments (dimension) | Formula (standard notation) | Result |
|---|---|---|---|---|
| S1 | `rect_area(b, h)` | b, h: L | A = b*h | A |
| S2 | `rect_inertia(b, h)` | b, h: L | I = b*h^3/12 (about the horizontal centroidal axis, b = width, h = height) | L^4 |
| S3 | `rect_section_modulus(b, h)` | b, h: L | S = b*h^2/6 | L^3 |
| S4 | `circle_area(d)` | d: L | A = pi*d^2/4 | A |
| S5 | `circle_inertia(d)` | d: L | I = pi*d^4/64 | L^4 |
| S6 | `circle_polar_inertia(d)` | d: L | J = pi*d^4/32 (polar second moment) | L^4 |
| S7 | `circle_section_modulus(d)` | d: L | S = pi*d^3/32 | L^3 |
| S8 | `ring_area(do, di)` | do, di: L | A = pi*(do^2 - di^2)/4 | A |
| S9 | `ring_inertia(do, di)` | do, di: L | I = pi*(do^4 - di^4)/64 | L^4 |
| S10 | `ring_section_modulus(do, di)` | do, di: L | S = pi*(do^4 - di^4)/(32*do) | L^3 |
| S11 | `radius_of_gyration(I, A)` | I: L^4, A: A | r = sqrt(I/A) | L |

Beams (linear-elastic, prismatic, small deflection; E = elastic modulus (pressure), I = second moment of
area (L^4), L = span/length):
| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| B1 | `cantilever_tip_deflection(P, L, E, I)` | P: F, L: L, E: p, I: L^4 | delta = P*L^3/(3*E*I), load at free end | L |
| B2 | `cantilever_udl_deflection(w, L, E, I)` | w: F/L, L, E, I | delta = w*L^4/(8*E*I), uniform load over the length | L |
| B3 | `simply_supported_center_deflection(P, L, E, I)` | P, L, E, I | delta = P*L^3/(48*E*I), point load at midspan | L |
| B4 | `simply_supported_udl_deflection(w, L, E, I)` | w, L, E, I | delta = 5*w*L^4/(384*E*I), uniform load | L |
| B5 | `cantilever_tip_max_moment(P, L)` | P: F, L: L | M_max = P*L (at the fixed end) | M |
| B6 | `cantilever_udl_max_moment(w, L)` | w: F/L, L | M_max = w*L^2/2 (at the fixed end) | M |
| B7 | `simply_supported_center_max_moment(P, L)` | P: F, L: L | M_max = P*L/4 (midspan) | M |
| B8 | `simply_supported_udl_max_moment(w, L)` | w: F/L, L | M_max = w*L^2/8 (midspan) | M |

Stress and strain:
| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| T1 | `axial_stress(F, A)` | F: F, A: A | sigma = F/A | p |
| T2 | `axial_strain(dL, L)` | dL: L, L: L | eps = dL/L | dimensionless |
| T3 | `axial_elongation(F, L, A, E)` | F, L, A, E: p | dL = F*L/(A*E) | L |
| T4 | `bending_stress(M, c, I)` | M: M, c: L (distance from neutral axis), I: L^4 | sigma = M*c/I | p |
| T5 | `hoop_stress(p, r, t)` | p: pressure (gauge), r: L (inner radius), t: L (wall) | sigma_hoop = p*r/t (thin-walled cylinder) | p |
| T6 | `longitudinal_stress(p, r, t)` | as T5 | sigma_long = p*r/(2*t) | p |

Columns (Euler buckling; K = effective length factor, dimensionless):
| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| C1 | `euler_critical_load(E, I, L, K)` | E: p, I: L^4, L: L, K: dimensionless | P_cr = pi^2*E*I/(K*L)^2 | F |
| C2 | `slenderness_ratio(L, K, r)` | L: L, K: dimensionless, r: L (radius of gyration) | lambda = K*L/r | dimensionless |
| C3 | `euler_transition_slenderness(E, sy)` | E: p, sy: p (yield strength) | lambda_t = sqrt(2*pi^2*E/sy) | dimensionless |

Phase 1 total: 28 functions (S1-S11, B1-B8, T1-T6, C1-C3 is 11+8+6+3 = 28). If the developer's
estimate exceeds 3 days, split into 1a (section + beams, 19 functions) and 1b (stress + column, 9
functions) at the manager's discretion; the acceptance criteria below group the same way.

Formulas are standard textbook relations. Sign conventions: tension positive; all inputs are
magnitudes (a negative load is not rejected in phase 1 except where a rule below says so).

## Syntax proposal (own keywords)
None. Every function is an ordinary call, `name(args)`, using the existing expression grammar. No new
keyword, no new operator, no `.lsheet` format change. Example call: `cantilever_tip_deflection(1 kN, 2 m,
200 GPa, 1e-6 m^4)` (the `1e-6 m^4` form is already used in spec 018).

## Implementation placement (for the developer, phase 1)
- New module `livesheet/engine/mecheng.py`: pure Python + SymPy, no PySide6 import. Exposes one dict
  `MECH_BUILTINS` of the 28 names.
- `livesheet/engine/evaluator.py` `_builtins()`: merge `MECH_BUILTINS` the same way `MATRIX_BUILTINS` and
  `STATS_BUILTINS` are merged today. Each function gets `__wrapped__`/signature/docstring so the existing
  call-hint autocomplete (spec 024) shows its argument names.
- Dimension checks: reuse the dimension inspection already in `livesheet/engine/units.py` (developer to
  confirm which helper gives the dimension of a measured quantity). Do NOT add a second unit system. A
  dimension vocabulary helper inside `mecheng.py` is fine.
- Development rule: no name in the library may equal a `BUILTINS` key, a `UNITS` key or a keyword in
  `syntax.py`. Test this in code, not by eye.

## Acceptance criteria (phase 1 only)
Numeric values are SI-equivalent and worked out by hand; the developer's and tester's tests must use
`Engine().evaluate(...)` (same way spec 017/018 tests do) and compare within the stated tolerance. Where a
display unit is shown, the test requests that unit explicitly (`= mm`, `= kN`, ...), because a bare `=`
prints base SI.

Registration and naming
1. All 28 names are callable in a math region and appear in the existing function-name autocomplete with
   their argument names (spec 024 mechanism), with no change to the autocomplete code.
2. No name in `MECH_BUILTINS` equals a `BUILTINS` key, a `UNITS` key, or a keyword in `syntax.py`.
   Test: set intersection is empty.
3. `livesheet/engine/mecheng.py` imports no PySide6 (grep-level test). `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" family of error (spec 063),
   e.g. `rect_area(50 mm)` (error, not a Python traceback).

Unit rules
5. Bare number in a dimensional slot is an error: `rect_area(50, 100 mm)` gives
   `rect_area: b needs a unit of length, for example 1 mm`.
6. Wrong dimension is an error: `rect_area(50 mm, 100 kg)` gives `rect_area: h must be a length, not kg`.
7. Dimensionless slot with a unit is an error: `euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 1 m)` gives
   `euler_critical_load: K must be dimensionless`.
8. Results are SI and mixed input units are accepted: `ring_inertia(0.04 m, 30 mm) = mm^4` gives
   85902.92 mm^4 (equal to 8.590292e-8 m^4 within 1e-6 relative).
9. SI-only input: every example in this spec and every test uses SI units or SI-prefixed units only. A test
   that passes an imperial unit (for example `rect_area(2 in, 4 in)`) is NOT part of the test suite; the
   tester checks by grep that no imperial unit name appears in `mecheng.py`, its tests, or this spec's
   examples.

Section properties (tolerance 1e-6 relative unless stated)
10. `rect_area(50 mm, 100 mm) = mm^2` gives 5000 mm^2; `rect_inertia(50 mm, 100 mm) = mm^4` gives
    4166666.67 mm^4; `rect_section_modulus(50 mm, 100 mm) = mm^3` gives 83333.33 mm^3.
11. `circle_area(40 mm) = mm^2` gives 1256.637 mm^2; `circle_inertia(40 mm) = mm^4` gives 125663.71 mm^4;
    `circle_polar_inertia(40 mm) = mm^4` gives 251327.41 mm^4 (exactly 2 times criterion 11's
    inertia); `circle_section_modulus(40 mm) = mm^3` gives 6283.185 mm^3.
12. `ring_area(40 mm, 30 mm) = mm^2` gives 549.779 mm^2; `ring_inertia(40 mm, 30 mm) = mm^4` gives
    85902.92 mm^4; `ring_section_modulus(40 mm, 30 mm) = mm^3` gives 4295.146 mm^3.
13. `radius_of_gyration(circle_inertia(40 mm), circle_area(40 mm)) = mm` gives 10 mm (exactly d/4; tolerance
    1e-9 relative). This is the cross-check that the radius is sqrt(I/A) and not I/A.

Beams (tolerance 1e-5 relative)
14. `cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) = mm` gives 13.3333 mm.
15. `simply_supported_center_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) = mm` gives 0.833333 mm.
16. `cantilever_udl_deflection(2 kN/m, 2 m, 200 GPa, 1e-6 m^4) = mm` gives 20 mm;
    `simply_supported_udl_deflection(2 kN/m, 2 m, 200 GPa, 1e-6 m^4) = mm` gives 2.08333 mm.
17. Maximum moments, displayed in `N*m` (a bare `=` would print `J`):
    `cantilever_tip_max_moment(1 kN, 2 m) = N*m` gives 2000 N*m;
    `cantilever_udl_max_moment(2 kN/m, 2 m) = N*m` gives 4000 N*m;
    `simply_supported_center_max_moment(1 kN, 2 m) = N*m` gives 500 N*m;
    `simply_supported_udl_max_moment(2 kN/m, 2 m) = N*m` gives 1000 N*m.
18. Scaling check: `cantilever_tip_deflection(1 kN, 4 m, 200 GPa, 1e-6 m^4)` divided by
    `cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4)` gives exactly 8 (dimensionless result, tolerance
    1e-9).

Stress and strain (tolerance 1e-6 relative)
19. `axial_stress(10 kN, 100 mm^2) = MPa` gives 100 MPa; `axial_elongation(5 kN, 2 m, 100 mm^2, 200 GPa) = mm`
    gives 0.5 mm.
20. `bending_stress(500 N*m, 0.05 m, 8e-6 m^4) = MPa` gives 3.125 MPa; `axial_strain(0.5 mm, 2 m)` gives
    0.00025 (dimensionless, no unit requested).
21. `hoop_stress(2 MPa, 500 mm, 10 mm) = MPa` gives 100 MPa; `longitudinal_stress(2 MPa, 500 mm, 10 mm) = MPa`
    gives 50 MPa (hoop is exactly twice the longitudinal stress).

Columns (tolerance 1e-5 relative; the transition value 1e-4)
22. `euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 1) = kN` gives 493.48 kN (pi^2*2e5/4 N).
23. `euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 0.5) = kN` gives 1973.92 kN (exactly 4 times criterion 22).
24. `slenderness_ratio(2 m, 1, 0.05 m)` gives 40 (dimensionless); `euler_transition_slenderness(200 GPa, 250 MPa)`
    gives 125.6637 (tolerance 1e-4 relative).

Errors (each gives a LiveSheet message, no Python traceback, no result)
25. Zero or negative positive-only input: `circle_inertia(-40 mm)` gives `circle_inertia: d must be greater
    than zero`. Negative K: `euler_critical_load(200 GPa, 1e-6 m^4, 2 m, -1)` gives `euler_critical_load: K
    must be greater than zero`. (Do not use `0 m` as the test value: a zero-valued length with a unit loses its
    unit in the existing engine, see the known limitations in docs/STATUS.md.)
26. Ordering: `ring_inertia(30 mm, 40 mm)` gives `ring_inertia: do must be larger than di`.
27. Undefined name inside a call: with nothing defined, `cantilever_tip_deflection(P, L, E, I)` gives the
    existing `P, L, E, I are not defined` message (the library must not swallow it).
28. Function body: `f(x) := rect_area(x, 100 mm)` then `f(50 mm) = m^2` gives 0.005 m^2. (Developer: confirm
    the engine substitutes the call arguments before the body's units are checked. If it does not, report it
    and do not fix it inside this spec; see Open question 2.)

Edge cases
- Results are exact closed forms, so a test that compares against a rounded hand value must use the stated
  tolerance, not exact equality.
- Thin-wall stress (T5, T6): the formulas assume r/t of about 10 or more (textbook guidance). Phase 1 does not
  reject thick walls and gives no warning (no warning mechanism exists yet, backlog 9). The tooltip / manual
  states the assumption.
- Beams: prismatic, linear-elastic, small deflection, single load case. No combined loads, no reactions list,
  no shear diagram in phase 1.
- Section properties are about the centroidal axis of a symmetric shape; no parallel-axis helper in phase 1.
  Composite sections are a later phase (outline below), and the DXF profile components (specs 013/014) already
  cover arbitrary outlines.
- Column formulas: C1 is valid only in the Euler range (lambda above the transition value C3). Phase 1 does
  not switch to another formula below the transition (a later Johnson-type phase will do so). The result is
  still the Euler value; the manual says so.
- `g` in the engine is standard gravity (known limitation). No phase-1 function uses it, so no conflict.
- Temperature inputs are not in phase 1 (no function takes a temperature).
- Bare numbers as dimensionless factors (K = 1, K = 0.5) are the intended form and are accepted.

IP check
Pass, pending manager review. Own function names and own argument order; formulas are generic textbook
relations (second moments of plane shapes, Euler-Bernoulli beam cases, thin-walled pressure vessel stress,
Euler buckling), each confirmed on a fetched public Wikipedia summary listed in the research note (accessed
2026-11-12). No vendor manual, product menu, keyword, example problem, table, numbering or ordering was read or
used; subject-area nouns only came from a product-listing search summary (research note 1a). No copied text
(CC BY-SA sources used for facts only). No new UI, no canvas interaction, no patent-sensitive technique (plain
function calls). Dimensionally strict input is a LiveSheet design choice, not a copied one. Not legal advice;
legal review before 1.0 is a standing item.

## Phases 2-7 (outline only, each needs its own spec)
Phase 2, torsion, plane stress, statics basics, 1-DOF vibration (spec 040 candidate):
- Solid shaft max shear `shaft_max_shear_solid(T, d) = 16*T/(pi*d^3)`; hollow `shaft_max_shear_ring(T, do, di)
  = 16*T*do/(pi*(do^4 - di^4))`; twist `shaft_twist_solid(T, L, G, d) = 32*T*L/(pi*G*d^4)` (rad); shaft power
  from torque and frequency `shaft_power(T, f) = 2*pi*f*T` (f in Hz).
- Mohr's circle: `principal_stresses(sx, sy, txy)` returns a 2-element vector [s1; s2] (vectors exist; no
  multi-result syntax needed); `max_shear_stress(sx, sy, txy) = R`; `principal_angle(sx, sy, txy)` = half of
  atan2(2*txy, sx - sy) (radians); `rotated_normal_stress(sx, sy, txy, theta)`. Sign convention to be fixed in
  the spec.
- Statics: `resultant_two_forces(P1, P2, theta)` (law of cosines, theta in radians), `force_components(P, theta)`,
  `friction_limit(mu, Fn)`.
- Vibration: `natural_frequency_hz(k, m) = sqrt(k/m)/(2*pi)`, `natural_angular_frequency(k, m)` (rad/s),
  `damped_angular_frequency(wn, zeta) = wn*sqrt(1 - zeta^2)` (rad/s), `log_decrement(x1, x2) = ln(x1/x2)`,
  `damping_ratio_from_log_decrement(delta) = delta/sqrt(delta^2 + (2*pi)^2)`.

Phase 3, fluid mechanics (spec 041 candidate): `hydrostatic_pressure(rho, h)` (uses standard gravity 9.80665
m/s^2 written into the function, not the engine's `g` unit); `mean_velocity(Q, A)`; `dynamic_pressure(rho, v)`;
`reynolds_number(rho, v, D, mu)`; `laminar_pipe_pressure_drop(mu, L, Q, D) = 128*mu*L*Q/(pi*D^4)`;
`darcy_head_loss(f, L, D, v)`; phase 3b: `colebrook_friction_factor(Re, eps_over_D)` (implicit, needs a root
finder, scipy approved). Bernoulli is documented as a formula, not as a solver.

Phase 4, heat transfer and thermodynamics (spec 042 candidate): `conduction_rate(k, A, dT, L) = k*A*dT/L`;
`convection_rate(h, A, dT) = h*A*dT`; `radiation_exchange(eps, A, T1, T2) = eps*sigma*A*(T1^4 - T2^4)` (grey
body in a large enclosure); `conduction_resistance(L, k, A)`, `convection_resistance(h, A)`, `heat_rate(dT, R)`;
`ideal_gas_pressure(n, T, V)`, `ideal_gas_volume(n, T, p)`, `ideal_gas_temperature(p, V, n)`,
`ideal_gas_moles(p, V, T)`; `carnot_efficiency(Th, Tc) = 1 - Tc/Th` (absolute temperatures in K only, Celsius
rejected until backlog 6). sigma and R from scipy.constants (CODATA), in SI units (W/(m^2 K^4), J/(mol K)).

Phase 5, machine elements (spec 043 candidate; each sub-item needs its own source check):
- Spur gears: `pitch_diameter(m, z)`, `centre_distance(m, z1, z2)`, `speed_ratio(z1, z2)`, `gear_train_ratio(...)`
  (list-based, needs vector input).
- Helical spring: rate `spring_rate(G, d, D, N) = G*d^4/(8*D^3*N)`. Source to be fetched and checked first
  (research note section 2).
- Hertz sphere-on-plane: `hertz_max_pressure(F, R_eff, E_eff) = (1/pi)*(6*F*E_eff^2/R_eff^2)^(1/3)`.
- Bolt preload from torque: `preload_from_torque(T, K, d) = T/(K*d)`, K user-entered (stress areas are
  standards data, excluded).
- Bearing life: `basic_life_ball(C, P) = (C/P)^3` (millions of revolutions); roller exponent 10/3.
- Von Mises: `von_mises(sx, sy, txy) = sqrt(sx^2 - sx*sy + sy^2 + 3*txy^2)`.

Phase 6, reference data (blocked on Open question 5): material properties and section tables. Default until a
licence decision: user-entered values only; no shipped table.

Phase 7, extras: forced vibration and transmissibility; lumped-capacitance transient (uses spec 010's ODE
machinery, not a new solver); ideal cycles (Rankine needs steam properties, so after backlog 8a(ii));
Johnson column formula below the transition slenderness.

## Edge cases that span phases
- Steam tables and Rankine cycle depend on backlog 8a(ii) (IAPWS published formulation); this library does
  not duplicate them.
- Formula tabs (specs 018-020) insert text templates; this library provides callable functions. Both may
  coexist; a later pass may let a tab button insert a function call instead of a template, but that is not
  specced here.
- DXF profile components (013/014) already give section properties of arbitrary outlines; phase 1 covers only
  plane shapes typed by the user.
- Existing non-SI text in shipped templates (`deg` in the statics templates of specs 011/018) is outside this
  library; flagged to the manager in the electrical research note, not changed here.

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Strict units (proposed) vs. SI default for bare numbers in dimensional slots. Recommendation: strict, error
   on a bare number, because the feature's purpose is to stop N/kN and mm/m slips. Confirm.
2. A function-body call whose argument is still unresolved symbolic (no unit yet): the dimension check runs
   at the moment of call with a value, so a body like `f(x) := ...` should check at call time. Recommendation:
   check at call time; a symbolic argument with no unit is not an error until it is evaluated.
3. Function naming: own topic-free snake_case names (as proposed) vs. a family prefix (e.g. `me_...`). Recommendation:
   topic names as proposed (more readable at the call site, no prefix to remember).
4. Standard gravity: write 9.80665 m/s^2 into the fluid functions (proposed) vs. rely on the engine's `g`
   (standard gravity by the existing unit table, but a single-letter unit trap, see spec 018). Recommendation:
   explicit constant.
5. Material and section data (phase 6): (a) keep user-entered values only indefinitely, or (b) allow a built-in
   table from a specific public source, and which one? Candidates that need a licence check before anything is
   shipped: NIST thermocouple reference functions (public-domain status to verify), CODATA constants (already
   allowed via scipy.constants), IAPWS-IF97 (published formulation, backlog 8a(ii)). Copyrighted handbook tables
   (materials, rolled sections) are excluded by this proposal. Theo's decision needed before phase 6 is
   specced.
6. Standards-based design checks (pressure-vessel codes, structural steel codes, bolt and spring standards,
   gear rating standards): excluded by this proposal, only textbook formulas are in scope. Confirm, or say which
   standards Theo wants considered for a separate legal review.
7. Whether `mol` (amount of substance, an SI base unit) exists in `units.py`. If not, the ideal-gas functions in
   phase 4 need it added (developer check; a units.py change is a separate small decision). Frequency is Hz
   throughout; rpm is not used (non-SI).
8. Thin-wall and Euler-range validity: warn or silently accept? No warning mechanism exists (backlog 9).
   Recommendation: state it in the manual and tooltip only.
9. Phase 1 size: 28 functions in one slice, or split 1a/1b as described above. Manager's call after the
   developer's estimate.

## Backlog (proposed additions for the manager to place)
- 74. Mechanical-engineering function library, spec 033: phase 1 (mecheng.py, 28 functions), then phases 2-7 as
  separate specs 040-043 and a phase-6 decision. Electrical sibling: spec 034 (backlog 75 proposed).

## Fits current architecture?
- `livesheet/engine/mecheng.py` (new, GUI-free) and a small merge in `livesheet/engine/evaluator.py`'s
  `_builtins()`, same pattern as `MATRIX_BUILTINS`/`STATS_BUILTINS`.
- `livesheet/engine/units.py`: reused for dimension checks, unchanged.
- Autocomplete (spec 024) and error wording: reuse existing mechanisms.
- No GUI change, no `.lsheet` change, no new dependency in phase 1. Phases 3b and 4 use scipy (already approved,
  BSD-3); no other new dependency.
- Tests: new `tests/test_mecheng.py` (developer, from this spec) and an independent black-box file by the tester
  from this spec only.
