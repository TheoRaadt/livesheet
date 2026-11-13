# Review: spec 034 phase 1A (electrical library, engine part)

Date: 2026-11-13. Tester. Scope: `livesheet/engine/electrical.py` (17 functions), units VA, var, mH, uH, nH, pF. GUI buttons and phase 1B are not shipped yet and were not reviewed.

Tests: `tests/test_spec034_review.py`, 22 pass and 2 strict xfail (defects below). All numeric expectations were recomputed with `math`/sympy formulas written independently of the implementation, not copied from it. The spec's own numbers (criteria 5-18, 36) were also re-run and all agree.

## Coverage
- Registry: exactly 17 names, no overlap with BUILTINS/UNITS; autocomplete candidates and signatures present for all 17; argument names avoid E, I, L, g, e, j and bare unit letters; wrong argument count (too many, zero).
- Strict units: bare number rejected in every dimensional slot of all 17 functions (message text for the first, substrings for the rest); wrong dimension; angle with a unit; turns with a unit; mixed compatible units (kV/ohm/kohm/mV/mA).
- Numerics: RMS/peak and round trip, P/S/Q with positive and negative phi, power factor (plain number is radians), power triangle (full precision inside the engine), resistor networks incl. scalar-as-vector and kohm display, dividers, three-phase and round trip, transformer incl. power conservation.
- SI: bare `=` prints W for all power functions; `= VA` and `= var` labels; `= V` on a power is rejected.
- Positivity errors, no traceback text, undefined names.
- E, I, L, g: library never uses them; user-defined `E := 230 V`, `L := 3 mH`, `I := 2 A`, `g := 3 m/s^2` feed the functions normally; bare E, L, g stay "not defined"; `I` stays the imaginary unit.
- New units mH, uH, nH, pF; sums and derived (`2 pi 50 Hz 10 mH = ohm`, `10 pF 10 V = C`); S and j not added (per spec).

## Defects
No blocker, no high.

### Medium
None.

### Low
- 034-1A-1: a zero result loses its unit, so a requested display unit fails. `average_power(230 V, 10 A, pi/2) = W` gives "Units do not match: result is dimensionless" (also `reactive_power(230 V, 10 A, 0) = var`). Bare `=` shows `= 0`, so only unit-forced display breaks. Root cause is the known engine behaviour "zero with unit drops its unit" (spec edge-case note); the formula multiplies `cos(pi/2)=0` by the unit. Likely fix: return `sp.Integer(0)` wrapped so the dimension survives, or accept the limitation and document it in the manual. Realistic case: an ideal resistive load has Q = 0. Strict xfail `test_zero_power_can_be_displayed_in_w`.
- 034-1A-2: a 2-D matrix or a row such as `[1 ohm 2 ohm]` gives a garbled error "R must be a resistance, not kg²·m⁴/(s⁶·A⁴)" (the elements are read as an implicit product), where the code intends "R must be a vector". Use the column syntax `[a; b]` or commas (`[10 ohm, 20 ohm]` works). Strict xfail `test_matrix_argument_message_is_readable`.
- 034-1A-3 (note, not a code defect): `0 ohm` as an argument gives "R1 needs a unit of resistance, for example 1 ohm", which is misleading for zero (engine drops the zero's unit). Spec accepts this limitation; the manual should say zero is rejected either way. `-0.0` style inputs behave the same.

### Observations
- `kVA`, `kvar`, `MVA` are not defined (spec only requires VA and var); power engineers will type `kVA` immediately. Suggest a follow-up or backlog item.
- `5 var` and `3 VA` are plain aliases of W: `3 var + 2 W = 5 W`, so VA and var are labels only, as the spec says. Not distinguishable by dimension (accepted by spec).
- Displayed values are rounded to 6 significant digits, so identities checked from displayed numbers need rel 1e-5 (the power triangle test is done inside the engine instead).
- Negative Vin/Itot/Vp/Ip are accepted deliberately (signed sources); negative phi accepted.
- Spec section "Phase 1B" and criteria 19-35 and GUI-1..6 are out of scope for this review.

## IP
No red flags. Function names, argument names and message wording are original; formulas are generic textbook relations. No vendor names or copied strings in electrical.py or the new test file. No Qt import in the engine module (checked by the developer's test and by inspection).

## GUI run
Phase 1A has no GUI part (the Electrical tab buttons belong to the GUI-1 section, not shipped). I did not launch the app in this pass: no computer-use tools were available in this session. Engine behaviour was exercised through `Engine().evaluate`. A GUI smoke test (type `average_power(230 V, 10 A, pi/3) = W` in a math region, check the autocomplete popup shows the signature) should be done by the next session that has computer access.

## Verdict
PASS with 2 low defects and 1 limitation note. Acceptable to merge phase 1A; fix or document 034-1A-1 before the manual is written.
