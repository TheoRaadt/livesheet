# 040 Mechanical library phase 2: shafts, plane stress, statics vectors, 1-DOF vibration

Status: IP-reviewed by manager 2026-11-13 (generic textbook formulas, own names, no vendor keywords/tables; APPROVED once Theo answers the open questions; developer must re-run every hand-computed criterion through Engine()). Original: NOT yet IP-reviewed. Specialist proposal (mathcad-specialist, 2026-11-13).
Parent: spec 033 (library overview, "General rules" 1-9, phase 1 code in livesheet/engine/mecheng.py).
Sibling: spec 041 (fluids, phase 3a). Spec 034 (electrical) is the GUI pattern source for GUI-1 below.

Numbers: NO execution tool was available to the specialist in this session. Every value in the
acceptance criteria was computed by hand (pi to 8 digits) and cross-checked by a second route where one
exists (a ratio of two formulas, or a direct re-evaluation). Per the spec 033 process, the developer must
re-run every criterion through `Engine().evaluate(...)` before the spec is treated as final; any mismatch
beyond the stated tolerance is a spec error and goes back to the specialist, not a silent code change.

Source inspiration (concept and formulas only; nothing copied):
- Public Wikipedia articles listed in docs/board/research/mech-eng-topics.md (accessed 2026-11-12, CC BY-SA
  4.0, facts only): Mohr's circle, Torsion (mechanics), Natural frequency, Damping ratio, Darcy-Weisbach
  equation. Formulas are standard textbook relations; the specialist did not re-fetch these pages in this
  session, so the manager should confirm them against the listed pages during IP review (see IP check).
- Statics formulas (law of cosines for two forces, force components, Coulomb friction limit) are general
  textbook mechanics, no single source copied.

User story:
As an engineer writing a calculation sheet, I want shaft torque and twist, principal and rotated stresses,
simple two-force statics and single-mass vibration results as ready-made functions, called with my own values
and units, with dimensions checked and results in SI, so that I do not re-derive Mohr's circle or the shaft
formulas each time and do not confuse N*m with kN, or mm with m.

## Behaviour (own words)

### Inherited rules
All general rules 1-9 of spec 033 apply unchanged: positional calls, dimension check per argument, bare
number in a dimensional slot is an error, dimensionless slot with a unit is an error, results SI, pure
functions, LiveSheet's own error wording `<function>: <argument> <problem>`, SI-only (no imperial, no degree
input), frequency in Hz or 1/s, never rpm. Argument names are documentation; GUI placeholders are a separate
list (GUI-4).

### Additions specific to this spec
A. Non-negative bound. Phase 1 has only "greater than zero". This spec needs a second bound, "not negative",
   for the damping ratio (zero is a valid undamped case). The builder gets a third bound option:
   - positive: value must be greater than zero, message `must be greater than zero`;
   - nonnegative: value must not be negative, message `must not be negative`;
   - any: no sign check.
B. Upper bound for zeta. `damped_angular_frequency` is defined only for zeta below one (underdamped).
   Message: `damped_angular_frequency: zeta must be less than one`.
C. Angles are radians and dimensionless in the engine. Angle arguments are plain numbers or pi-based
   expressions (`pi/3`). A value written with a degree unit is NOT detectable by the library (the engine
   turns `deg` into `pi/180` before any function sees it). This is an open question for Theo (OQ1); the
   library does not try to reject it. Tests never use a degree unit.
D. Mohr sign convention (fixed here, not in the textbook sources): normal stress positive in tension;
   shear stress txy positive when it acts counter-clockwise on the face whose outward normal is +x; theta is
   measured counter-clockwise from the x-axis in radians.
E. Scalar results only. Phase 2 uses one function per result (for example `principal_stress_max` and
   `principal_stress_min`), not a two-element vector return, so each result is a plain value that can be
   used in further arithmetic and in `=` checks. No new syntax.
F. Dimension vocabulary additions (in the same `_DIMS` table as phase 1; the display example is the hint
   shown in "needs a unit of ..." messages):

   | Name | SI unit expression | Hint example |
   |---|---|---|
   | mass | kg | 1 kg |
   | stiffness | N/m | 1 kN/m |
   | frequency | 1/s (same dimension as Hz) | 1 Hz |
   | damping coefficient | N*s/m | 1 N*s/m |

   Note: `damping coefficient` (kg/s) has the same base dimension as `mass flow` (spec 041), and
   `moment` (N*m) has the same base dimension as energy (J). The dimension check compares base dimensions,
   so these pairs are interchangeable. This is a known limitation, stated in the manual, not fixed here.

### Slicing
Recommended split, Theo to confirm (OQ8): 040a = torsion + plane stress (11 functions, shaft and Mohr),
040b = statics vectors + vibration (12 functions). Each slice ships with its own acceptance criteria below.
Phase 2 is 23 functions in total (2-3 days per spec 033).

## Phase 2a: function list (torsion and plane stress)

Notation: T torque (moment), d diameter, do / di outer and inner diameter, G shear modulus (pressure),
L span (length), sx, sy normal stresses and txy shear stress (pressure), theta angle (rad). Results SI.
"dimensionless" = no unit allowed (the result is a plain number).

Torsion (circular shafts, linear-elastic, small twist; J = polar second moment of area, from phase 1
`circle_polar_inertia` and `ring` forms):

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| H1 | `shaft_max_shear_solid(torque, dia)` | torque: moment; dia: length | tau_max = 16 T/(pi d^3) | pressure |
| H2 | `shaft_max_shear_hollow(torque, dia_o, dia_i)` | torque: moment; dia_o, dia_i: length; dia_o > dia_i | tau_max = 16 T do/(pi (do^4 - di^4)) | pressure |
| H3 | `shaft_twist_solid(torque, span, shear_mod, dia)` | torque: moment; span: length; shear_mod: pressure; dia: length | phi = 32 T L/(pi G d^4), total twist angle | dimensionless (rad) |
| H4 | `shaft_twist_hollow(torque, span, shear_mod, dia_o, dia_i)` | as H3 plus dia_o, dia_i with dia_o > dia_i | phi = 32 T L/(pi G (do^4 - di^4)) | dimensionless (rad) |
| H5 | `shaft_power(torque, freq)` | torque: moment; freq: frequency (Hz) | P = 2 pi f T | W |

Plane stress (Mohr's circle, sign convention D):

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| M1 | `principal_stress_max(sx, sy, txy)` | sx, sy, txy: pressure | s1 = (sx+sy)/2 + R | pressure |
| M2 | `principal_stress_min(sx, sy, txy)` | as M1 | s2 = (sx+sy)/2 - R | pressure |
| M3 | `max_shear_stress(sx, sy, txy)` | as M1 | tau_max = R | pressure |
| M4 | `principal_angle(sx, sy, txy)` | as M1 | theta_p = (1/2) atan2(2 txy, sx - sy), direction of s1 | dimensionless (rad), in (-pi/2, pi/2] |
| M5 | `rotated_normal_stress(sx, sy, txy, theta)` | as M1; theta: rad | sigma_n = (sx+sy)/2 + ((sx-sy)/2) cos(2 theta) + txy sin(2 theta) | pressure |
| M6 | `rotated_shear_stress(sx, sy, txy, theta)` | as M1; theta: rad | tau = -((sx-sy)/2) sin(2 theta) + txy cos(2 theta) | pressure |

where R = sqrt(((sx - sy)/2)^2 + txy^2).

Phase 2a total: 11 functions (H1-H5, M1-M6).

## Phase 2b: function list (statics vectors and 1-DOF vibration)

Statics (coplanar forces; theta = angle between the two force directions, 0 = same direction):

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| Q1 | `resultant_two_forces(P1, P2, theta)` | P1, P2: force; theta: rad | R = sqrt(P1^2 + P2^2 + 2 P1 P2 cos(theta)) | force |
| Q2 | `resultant_direction(P1, P2, theta)` | as Q1 | alpha = atan2(P2 sin(theta), P1 + P2 cos(theta)), angle of R measured from P1 | dimensionless (rad), in (-pi, pi] |
| Q3 | `force_x_component(P, theta)` | P: force; theta: rad | Px = P cos(theta) | force |
| Q4 | `force_y_component(P, theta)` | as Q3 | Py = P sin(theta) | force |
| Q5 | `friction_limit(mu, Fn)` | mu: dimensionless (no unit); Fn: force | Ff_max = mu Fn (limiting static friction, Coulomb model) | force |

Vibration (single degree of freedom, viscous damping; stiffness k, mass m, damping coefficient c):

| # | Function (argument order) | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| V1 | `natural_angular_frequency(stiffness, mass)` | stiffness: stiffness; mass: mass | wn = sqrt(k/m) | frequency (1/s, shown as rad/s) |
| V2 | `natural_frequency_hz(stiffness, mass)` | as V1 | fn = sqrt(k/m)/(2 pi) | frequency (Hz) |
| V3 | `damped_angular_frequency(wn, zeta)` | wn: frequency; zeta: dimensionless, 0 <= zeta < 1 | wd = wn sqrt(1 - zeta^2) | frequency (1/s) |
| V4 | `damping_ratio(damping, stiffness, mass)` | damping: damping coefficient; stiffness; mass | zeta = c/(2 sqrt(k m)) | dimensionless |
| V5 | `critical_damping(stiffness, mass)` | stiffness; mass | c_cr = 2 sqrt(k m) | damping coefficient |
| V6 | `log_decrement(x1, x2)` | x1, x2: length; x1 > x2 | delta = ln(x1/x2), natural log of the ratio of two successive peak amplitudes | dimensionless |
| V7 | `damping_ratio_from_log_decrement(delta)` | delta: dimensionless, delta > 0 | zeta = delta/sqrt(delta^2 + (2 pi)^2) | dimensionless |

Phase 2b total: 12 functions (Q1-Q5, V1-V7).

## Syntax proposal (own keywords)
None. Function calls only, existing grammar. No `.lsheet` change.

Example calls: `shaft_max_shear_solid(1 kN*m, 50 mm)`; `principal_stress_max(80 MPa, 20 MPa, 30 MPa)`;
`resultant_two_forces(300 N, 400 N, pi/2)`; `natural_frequency_hz(8 kN/m, 2 kg)`.

## Implementation placement (developer)
- Phase 2a and 2b extend `livesheet/engine/mecheng.py` by adding entries to the existing `_SPEC` list, so
  `MECH_BUILTINS` gains the 23 names. No new module, no new dependency.
- The `_Arg` record gets the bound option of Addition A (`positive` boolean becomes a three-value bound; the
  phase 1 call sites keep their current meaning). The `order` option of `_make` is reused for the hollow
  shaft and log-decrement ordering checks. Two custom checks (Addition B and the M4 / Q2 zero cases) are
  small checks inside the formula wrapper, raising `StatementError` with the function-name prefix.
- Dimension checks reuse phase 1's `_check_arg` path. No second unit system.
- Development rule (unchanged): no new name may equal a `BUILTINS` key, a `UNITS` key or a `syntax.py`
  keyword. Test in code: set intersection is empty. Also check that `re`, `im`, `atan2`, `sqrt`, `ln`
  (existing builtins) are not reused as names.

## Acceptance criteria

Numeric values are SI-equivalent and were computed by hand (see the note at the top). Tests use
`Engine().evaluate(...)`. Where a display unit is shown, the test requests that unit explicitly
(`= MPa`, `= kW`, ...). Tolerance is 1e-5 relative unless stated. Where the `=` display rounds to 6
significant digits, the test calls the builtin directly and compares to 1e-9 relative (the spec 034 note).

### Registration and naming (both slices)
1. All 23 names are callable in a math region and appear in the existing function-name autocomplete with
   their argument names (spec 024 mechanism), with no change to the autocomplete code.
2. No name in the 23 equals a `BUILTINS` key, a `UNITS` key, or a `syntax.py` keyword. Test: set
   intersection is empty.
3. `mecheng.py` still imports no PySide6 (grep-level test). `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" family of error, e.g.
   `shaft_power(500 N*m)` (no traceback).

### Unit rules (both slices)
5. Bare number in a dimensional slot is an error: `shaft_max_shear_solid(1000, 50 mm)` gives
   `shaft_max_shear_solid: torque needs a unit of moment, for example 1 N*m`.
6. Wrong dimension is an error: `shaft_power(500 N*m, 30 kg)` gives `shaft_power: freq must be a frequency, not kg`.
7. Dimensionless slot with a unit is an error: `damped_angular_frequency(100 rad/s, 0.3 m)` gives
   `damped_angular_frequency: zeta must be dimensionless`. (`rad` alone is dimensionless and is accepted
   in an angle slot; `100 rad/s` is accepted as a frequency.)
8. `friction_limit(0.3 N, 2 kN)` gives `friction_limit: mu must be dimensionless`.

### Phase 2a: torsion (tolerance 1e-5 relative)
9. `shaft_max_shear_solid(1 kN*m, 50 mm) = MPa` gives 40.7437 MPa.
10. `shaft_max_shear_hollow(1 kN*m, 50 mm, 30 mm) = MPa` gives 46.8103 MPa. Cross-check: this equals
    criterion 9 times do^4/(do^4 - di^4) = 6.25e6/5.44e6 = 1.148897 (both in mm^4), 40.7437 x 1.148897 = 46.8103.
11. `shaft_twist_solid(1 kN*m, 1 m, 80 GPa, 50 mm)` (bare, dimensionless) gives 0.0203718 rad.
12. `shaft_twist_hollow(1 kN*m, 1 m, 80 GPa, 50 mm, 30 mm)` (bare) gives 0.0234051 rad. Cross-check: ratio to
    criterion 11 is d^4/(do^4 - di^4) = 1.148897, 0.0203718 x 1.148897 = 0.0234051.
13. `shaft_power(500 N*m, 30 Hz) = kW` gives 94.2478 kW (2 pi x 30 x 500 = 94247.78 W).

### Phase 2a: plane stress (sx = 80 MPa, sy = 20 MPa, txy = 30 MPa; tolerance 1e-5 relative)
Hand values: centre 50 MPa, R = sqrt(30^2 + 30^2) = sqrt(1800) = 42.42641 MPa.
14. `principal_stress_max(80 MPa, 20 MPa, 30 MPa) = MPa` gives 92.4264 MPa.
15. `principal_stress_min(80 MPa, 20 MPa, 30 MPa) = MPa` gives 7.57359 MPa.
    Check: 14 + 15 = 100 MPa = sx + sy (invariant).
16. `max_shear_stress(80 MPa, 20 MPa, 30 MPa) = MPa` gives 42.4264 MPa (equals R).
17. `principal_angle(80 MPa, 20 MPa, 30 MPa)` (bare) gives 0.392699 rad (pi/8). Check: at this angle
    `rotated_normal_stress` equals criterion 14 and `rotated_shear_stress` is zero (criterion 20).
18. `rotated_normal_stress(80 MPa, 20 MPa, 30 MPa, pi/6) = MPa` gives 90.9808 MPa
    (50 + 15 + 25.98076). Check: rotated_normal_stress at (theta + pi/2) = 9.01924 MPa, and the two sum to
    100 MPa = sx + sy.
19. `rotated_shear_stress(80 MPa, 20 MPa, 30 MPa, pi/6) = MPa` gives -10.9808 MPa. Sign check: the same
    function at theta = 0 returns txy = 30 MPa.
20. `rotated_shear_stress(80 MPa, 20 MPa, 30 MPa, principal_angle(80 MPa, 20 MPa, 30 MPa))` gives 0 MPa
    within 1e-9 MPa (principal planes carry no shear).

### Phase 2b: statics (tolerance 1e-5 relative)
21. `resultant_two_forces(300 N, 400 N, pi/2) = N` gives 500 N (3-4-5 triangle).
22. `resultant_two_forces(300 N, 400 N, pi/3) = N` gives 608.276 N (sqrt(370000)).
23. `resultant_two_forces(300 N, 400 N, 0) = N` gives 700 N; `resultant_two_forces(300 N, 400 N, pi) = N`
    gives 100 N.
24. `resultant_direction(300 N, 400 N, pi/2)` (bare) gives 0.927295 rad (atan(4/3)).
25. `force_x_component(500 N, pi/3) = N` gives 250 N; `force_y_component(500 N, pi/3) = N` gives 433.013 N.
    Check: Fx^2 + Fy^2 = 250000 N^2 on both sides (62500 + 187500), within 1e-9.
26. `friction_limit(0.3, 2 kN) = N` gives 600 N; `friction_limit(0.3, 2 kN) = kN` gives 0.6 kN.

### Phase 2b: vibration (tolerance 1e-5 relative)
27. `natural_angular_frequency(8 kN/m, 2 kg) = 1/s` gives 63.2456 (sqrt(4000)). Displayed as s^-1 (spec 034
    note: the engine prints the 1/s unit as s^-1, not rad/s).
28. `natural_frequency_hz(8 kN/m, 2 kg) = Hz` gives 10.0658 Hz. Check: criterion 28 value times 2 pi equals
    criterion 27 value (within 1e-9).
29. `damped_angular_frequency(100 rad/s, 0.3) = 1/s` gives 95.3939 (100 sqrt(0.91)).
30. `damping_ratio(40 N*s/m, 8 kN/m, 2 kg)` (bare) gives 0.158114 (= sqrt(0.025)).
31. `critical_damping(8 kN/m, 2 kg) = N*s/m` gives 252.982 N*s/m (2 sqrt(16000)).
    Check: criterion 30 = 40 / criterion 31 value (within 1e-9).
32. `log_decrement(10 mm, 4 mm)` (bare) gives 0.916291 (ln 2.5).
33. `damping_ratio_from_log_decrement(0.916291)` (bare) gives 0.144306. Check: `damping_ratio_from_log_decrement(log_decrement(10 mm, 4 mm))` equals this value (within 1e-9).
34. Zero damping is valid: `damped_angular_frequency(100 rad/s, 0)` gives 100 (1/s) exactly. (A bare 0 is
    dimensionless, so the zero-unit loss does not apply.)

### Errors (each gives a LiveSheet message, no traceback, no result)
35. Negative or zero positive-only input: `shaft_max_shear_solid(1 kN*m, -50 mm)` gives
    `shaft_max_shear_solid: dia must be greater than zero`.
36. Negative damping ratio: `damped_angular_frequency(100 rad/s, -0.3)` gives
    `damped_angular_frequency: zeta must not be negative`.
37. Underdamped only: `damped_angular_frequency(100 rad/s, 1)` gives
    `damped_angular_frequency: zeta must be less than one`.
38. Ordering: `shaft_max_shear_hollow(1 kN*m, 30 mm, 50 mm)` gives
    `shaft_max_shear_hollow: dia_o must be larger than dia_i`; `log_decrement(4 mm, 10 mm)` gives
    `log_decrement: x1 must be larger than x2`.
39. Isotropic state: `principal_angle(50 MPa, 50 MPa, 0 MPa)` gives
    `principal_angle: no unique principal direction (sx equals sy and txy is zero)`.
40. Zero resultant: `resultant_direction(300 N, 300 N, pi)` gives
    `resultant_direction: resultant is zero, direction undefined`.
41. Zero or negative mass: `natural_frequency_hz(8 kN/m, -2 kg)` gives
    `natural_frequency_hz: mass must be greater than zero`.
42. Undefined name inside a call (nothing defined): `shaft_power(torque, freq)` gives the existing
    `torque, freq are not defined` message (the library must not swallow it).

## Edge cases
- Angles: `pi/3` and `1.0471976` are equal. Plain numbers are radians. A degree unit is not detectable (OQ1).
- Principal angle range (-pi/2, pi/2]: the direction of s1, not s2. The max shear plane is 45 degrees away
  (pi/4 rad) from the principal planes; the function returns R only, not its angle.
- Mohr convention (Addition D) is the only one used; the manual states it. A reader using the opposite shear
  sign gets the mirror image, not a different magnitude.
- Hollow shaft: wall thickness is not checked against stress limits; formulas are linear-elastic, small
  twist only, no stress concentration.
- Shafts: twist is the total angle over the span (rad), not twist per unit length.
- Vibration: viscous damping only; the functions describe a single degree of freedom. Forced vibration is
  phase 7.
- Log decrement: uses peak amplitudes of successive peaks of one cycle; equal amplitudes give delta = 0 and
  a zero damping ratio, which is valid.
- Zero values with a unit lose their unit in the engine (known limitation, backlog 81). Tests use bare 0 for
  zero dimensionless inputs and never a zero with a unit.
- Dimension pairs with equal base dimension (mass flow / damping coefficient, moment / energy) are
  interchangeable (Addition F).

## GUI-1 (Mechanical tab, same mechanism as spec 034 GUI-1)
GUI-1. The existing Mechanical tab keeps its two existing groups, "Statics" and "Strength of Materials",
exactly as they are (spec 011 / 018 templates, unchanged, GUI-6 regression). New sub-headers are added after
them, in this order: "Shafts", "Plane Stress", "Force Vectors", "Vibration". The tab stays one tab; TAB_ORDER
unchanged.
GUI-2. Exactly 23 new buttons, one per phase 2 function. Each calls the existing `insert_token(token)`
callback. No new widget, no dialog, no on-canvas editing, no keyboard shortcut (click only, as in spec 020).
GUI-3. Button list (label | inserted text | tooltip; each tooltip states input units and result unit, SI only):
- Shafts: "max shear, solid" | `shaft_max_shear_solid(torque, dia)` | tau_max from torque (N*m), diameter (m); result Pa. | "max shear, hollow" | `shaft_max_shear_hollow(torque, dia_o, dia_i)` | Pa; dia_o larger than dia_i. | "twist, solid" | `shaft_twist_solid(torque, span, shear_mod, dia)` | angle phi, rad; span m, shear modulus Pa. | "twist, hollow" | `shaft_twist_hollow(torque, span, shear_mod, dia_o, dia_i)` | rad. | "shaft power" | `shaft_power(torque, freq)` | W from torque (N*m) and frequency (Hz).
- Plane Stress: "max principal stress" | `principal_stress_max(sx, sy, txy)` | Pa. | "min principal stress" | `principal_stress_min(sx, sy, txy)` | Pa. | "max shear stress" | `max_shear_stress(sx, sy, txy)` | Pa. | "principal angle" | `principal_angle(sx, sy, txy)` | rad. | "rotated normal stress" | `rotated_normal_stress(sx, sy, txy, theta)` | Pa; theta in rad. | "rotated shear stress" | `rotated_shear_stress(sx, sy, txy, theta)` | Pa; theta in rad.
- Force Vectors: "resultant, 2 forces" | `resultant_two_forces(P1, P2, theta)` | N; theta between the two forces, rad. | "resultant direction" | `resultant_direction(P1, P2, theta)` | rad from P1. | "force x-component" | `force_x_component(P, theta)` | N. | "force y-component" | `force_y_component(P, theta)` | N. | "friction limit" | `friction_limit(mu, Fn)` | N; mu plain number.
- Vibration: "natural rad/s" | `natural_angular_frequency(stiffness, mass)` | 1/s; stiffness N/m, mass kg. | "natural Hz" | `natural_frequency_hz(stiffness, mass)` | Hz. | "damped rad/s" | `damped_angular_frequency(wn, zeta)` | 1/s; zeta below one. | "damping ratio" | `damping_ratio(damping, stiffness, mass)` | plain number. | "critical damping" | `critical_damping(stiffness, mass)` | N*s/m. | "log decrement" | `log_decrement(x1, x2)` | plain number. | "damping ratio from log decrement" | `damping_ratio_from_log_decrement(delta)` | plain number.
GUI-4. Placeholder names avoid bare unit letters (T, N, m, s, A, V, W, K, C, F, H, J, Pa, Hz, and the engine's
single-letter specials E, I, L, g, C, e): torque, dia, dia_o, dia_i, span, shear_mod, freq, sx, sy, txy,
theta, P, P1, P2, mu, Fn, stiffness, mass, damping, wn, zeta, x1, x2, delta. Note `mass` and `span` are plain
words, not units. An unfilled template then gives "... is not defined", never a silent unit.
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change.
GUI-6. Regression: the Statics and Strength of Materials templates (spec 011 / 018) are unchanged in label,
text and order. Their `deg` use is outside this spec (OQ1).

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Angles and `deg`: the engine turns `deg` into `pi/180` before the library sees it, so `deg`-written angles
   are silently accepted. Options: (a) document only (proposed); (b) remove `deg` and `°` from `UNITS`, which
   also breaks the shipped Statics/Strength templates (spec 011 / 018) that use `deg`, so they must change
   first. Recommendation: (a) now, (b) as a separate small decision.
2. Mohr sign convention (Addition D) fixed as stated. Confirm.
3. Scalar functions per result (Addition E), not vector returns. Confirm.
4. Function names: topic names as proposed (same answer as spec 033 OQ3). Confirm.
5. Dimension pairs with equal base dimensions (Addition F): accept and document, or add a stricter named
   check later? Recommendation: accept and document.
6. The Statics and Strength of Materials templates stay unchanged (GUI-6); the Force Vectors buttons sit
   beside them. Confirm, or prefer a single "Statics" sub-header for the new force buttons.
7. Phase 1 has no GUI buttons in spec 033. Should phase 1's 28 functions get a Mechanical-tab button group
   too (a separate GUI spec, or a GUI-7 section in spec 041)? Recommendation: yes, after phase 1 is merged.
8. Size: 23 functions in one slice, or 040a (11, torsion + plane stress) and 040b (12, statics + vibration)?
   Recommendation: split, as above.
9. Hand-computed numbers: the specialist could not run them. Developer re-runs all criteria; any mismatch
   beyond tolerance is returned to the specialist. Confirm this step is acceptable before IP review.

## IP check
Pass, pending manager review. Own function names, own argument names, own GUI wording and own tooltip text.
Formulas are generic textbook relations (torsion of circular shafts, plane-stress transformation / Mohr's
circle, two-force resultant, force components, Coulomb friction limit, single-DOF natural frequency,
damping ratio, log decrement), taken from public Wikipedia articles listed in docs/board/research/
mech-eng-topics.md (accessed 2026-11-12) for facts only, and from general mechanics. No vendor manual,
product menu, keyword, example problem, table or numbering was read or used. No copyrighted table or
standards data (no bolt, spring, shaft-design or steel code values). No new UI technique (plain
toolbar-style button group, existing insert mechanism). Caveat: the specialist did not re-fetch the listed
pages in this session; the manager should confirm each formula against the page during IP review. Not legal
advice; legal review before 1.0 is a standing item.

## Fits current architecture?
- `livesheet/engine/mecheng.py` (phase 1 file): new `_SPEC` entries and one `_Arg` bound option. No new module,
  no new dependency (sympy only).
- `livesheet/engine/units.py`: reused unchanged; only `_DIMS` gains four entries (mass, stiffness, frequency,
  damping coefficient).
- `livesheet/engine/evaluator.py`: unchanged, `MECH_BUILTINS` is already merged.
- `livesheet/gui/sidepanel.py`: one new token list (23 tuples) and four new sub-headers in
  `TAB_CATEGORIES["Mechanical"]` after the existing two; TAB_ORDER unchanged.
- Tests: `tests/test_mecheng_phase2.py` (developer, from this spec); independent black-box file by the tester
  from this spec only; GUI button checks in the tester's file.

## Implementation annotations 040a (developer, 2026-11-13)
- Re-run of criteria 9-20 (independent `math` computation and `Engine().evaluate`): all hand values match
  within 1e-5 relative (40.74367, 46.81028, 0.02037183, 0.02340514, 94.24778 kW, 92.42641, 7.573593,
  42.42641, pi/8, 90.98076, -10.98076; the complement at theta+pi/2 is 9.019238). No formula errors, no mismatch.
- Criteria 1-8 (040a-relevant) and 35, 38 (shaft), 39, 42 covered by tests/test_mecheng_040a.py.
- Added to `_DIMS`: `frequency` (Hz, hint "1 Hz") and `power` (W, result of `shaft_power`; the spec lists
  the result as "W" but only addition F's four names were listed). `mass`, `stiffness`, `damping coefficient`
  are left for 040b.
- `_Arg.positive: bool` became `bound: str` ("positive" / "nonnegative" / "any"); `_a()` still accepts the
  old True/False. The "nonnegative" bound is implemented but not yet used (needed by zeta in 040b).
- Bounds chosen where the spec was silent: torque, sx, sy, txy, theta, freq accept any sign (negative torque
  gives a negative shear stress); dia, dia_o, dia_i, span, shear_mod must be greater than zero.
- Old tests adapted: tests/test_mecheng.py registry count 28 -> 39; tests/test_spec033_review.py exact-set
  check relaxed to subset (phase 2 names are additions).
- Per Theo's decision (decisions.md 2026-11-13): `deg` unchanged, documentation only.
- Criteria 20 and 39 hit the known zero-unit-drop limitation (backlog 81): criterion 20's exact result 0 prints
  as plain `0` (so `= MPa` fails with "Units do not match"; the test checks the exact value 0 without a unit);
  criterion 39 with `0 MPa` (also via a variable) gives `principal_angle: txy needs a unit of pressure, ...`
  instead of the "no unique principal direction" message, which is therefore unreachable through the engine
  today; the check itself is tested on the formula helper. Not a spec formula error.
- Bare (dimensionless) results show only with a trailing `=` (e.g. `principal_angle(...) =`); without it the
  deferred call is not evaluated. Tests use that form.

## Implementation annotations 040b (developer, 2026-11-13)
- Re-run of criteria 21-34 through `Engine().evaluate`: all hand values match within 1e-5 relative (500, 608.276, 700, 100 N; 0.927295; 250 / 433.013 N; 600 N / 0.6 kN; 63.2456; 10.0658 Hz; 95.3939; 100 exact; 0.158114; 252.982; 0.916291; 0.144306). No spec formula errors. Criteria 5-8, 35-38, 40-42 (2b-relevant) are in tests/test_mecheng_040b.py.
- `_DIMS` gained `mass` (kg), `stiffness` (N/m), `damping coefficient` (N*s/m). `frequency` already existed from 040a; V1/V2/V3 use it.
- Bounds where the spec was silent: P1, P2, P, theta any sign; mu nonnegative; Fn, stiffness, mass, wn, x1, x2, delta greater than zero; damping and zeta nonnegative (a bare 0 zeta is valid; a damping of `0 N*s/m` loses its unit, backlog 81, so it is rejected as needing a unit).
- Criterion 42 needs a trailing `=` (`natural_frequency_hz(stiffness, mass) =`): a deferred call without `=` is not evaluated (same as 040a note).
- Zero-resultant check uses a 1e-12 relative tolerance so exact cancellation (pi) is caught.
- Registry counts: tests/test_mecheng.py 39 -> 51; tests/test_spec033_review.py already a subset check.
