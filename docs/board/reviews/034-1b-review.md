# Review: spec 034 phase 1B (electrical library, engine part, 19 functions)

Date: 2026-11-13. Tester. Scope: C1-C9, T1-T4, S1-S3, F1-F3 in `livesheet/engine/electrical.py` (`ELEC_BUILTINS` = 36). GUI-1 buttons are not implemented and not reviewed.

Tests: `tests/test_spec034_1b_review.py`: 95 pass, 5 strict xfail (defects below). Every expected value is recomputed with `math` / `cmath` in the test, not copied from the implementation or from the spec's printed numbers (the spec numbers were also spot-checked and agree). The developer's annotations were not trusted; items 1-7 were each re-verified (all confirmed, see below).

## Coverage
- Registry: exact 36-name set pinned (see the subset-relaxation judgement below); no overlap with BUILTINS/UNITS; autocomplete candidates and signatures for all 19 (e.g. `rc_charge_voltage(Vs, t, R, C)`).
- Phasors: re/im/magnitude/angle round trip for 7 angles over all four quadrants; principal range (3pi/2 -> -pi/2, 5pi/2 -> pi/2, -3pi/2 -> pi/2, negative real axis -> +pi, +-pi/2); kV / mA prefix handling; manual complex `3 ohm + 4 I ohm`; unit-bearing and zero angles rejected.
- Impedances: R real; L has +j X, C has -j X (three f/L, f/C pairs each); real part exactly 0; prefix equivalence (kHz, mH, nF).
- Series/parallel with complex values, three-branch RLC parallel, scalar-as-vector, series RLC at resonance gives pure R (magnitude = R), X_L/R = Q, angle sign flips above/below f0; unit errors in vector entries.
- Transients: tau values, v_C and i(t) at several t, t = 5 tau, t >> tau (steady state Vs and Vs/R), ms inputs, display in ms; t = 0 bare prints 0; negative t, bare t, wrong dimensions.
- Resonance: f0, Q, B, f0/B = Q to 1e-9 in math and 1e-5 through displayed numbers; reactances cancel at f0; pF / uH extremes.
- Filters: cutoff, gain at cutoff (both LP and HP = 1/sqrt2), five frequencies, LP^2 + HP^2 = 1, kHz/nF equivalent inputs.
- Strict units: for all 14 functions with scalar dimensional slots, every slot gets a bare number (message must start `fn: `, contain "needs a unit of" and "for example") and a wrong-dimension value (kg), plus argument-count errors; phasor/z slots checked separately. No traceback or SymPy text in any error.
- E, I, L, g: user variables of those names feed the functions; bare E, L stay undefined; no function argument is an engine-reserved name except the spec's documented L and C (see observation).
- Composition: results stored in variables and reused; I = V/Z with a phasor and complex Z gives the right magnitude in A.

## Defects (no blocker, no high, no medium)

### Low
- 034-1B-1 (= known 034-1A-1, now also in 1B): a zero result loses its unit, so a forced display unit fails. `rc_charge_voltage(12 V, 0 s, 1 kohm, 10 uF) = V` and `rl_current_rise(12 V, 0 s, 10 ohm, 0.5 H) = A` give "Units do not match: result is dimensionless". Bare `=` prints 0. The t = 0 case is exactly the first thing a user will try. Still present for 1A: `average_power(230 V, 10 A, pi/2) = W` fails. Strict xfail `test_transient_t_zero_can_be_displayed_in_V`, `test_zero_unit_drop_known_1A_defect_still_present`. Document in the manual (already done for 1A) or fix in the unit layer.
- 034-1B-2: zero frequency / zero time give a misleading message. `impedance_inductor(0 Hz, 1 H)` and `rc_lowpass_gain(0 Hz, 1 kohm, 1 uF)` say "f needs a unit of frequency, for example 1 Hz" (the engine drops the unit of the zero). DC (f = 0) is a legitimate case for gains and inductors; the spec only requires f > 0 for the capacitor and filter cutoff. Either accept 0 for these (like t) or give an "f must be greater than zero" message. Strict xfail `test_zero_frequency_message_is_not_misleading`.
- 034-1B-3: `impedance_parallel([1 ohm; -1 ohm]) =` (ideal parallel LC at resonance, an open circuit) returns status ok with the text `= undefined` instead of an error such as "z: parallel combination is an open circuit". Strict xfail `test_parallel_of_opposite_reactances_gives_open_circuit_marker`.
- 034-1B-4 (cosmetic): "L must be a inductance, not V" (also "a inductance" in any inductance slot). Use "an". Strict xfail `test_grammar_a_inductance`. (The developer already noted this as item 6.)

### Spec deviations accepted as engine limits (agree with developer annotations 1-4)
- Criterion 34: `impedance_parallel([])` gives engine message "Empty matrix", not "impedance_parallel: needs at least one impedance"; the function's own message exists and is verified by a direct call. Pinned by `test_empty_vector_message_is_engine_level_not_function_level`.
- Criterion 35: `rc_time_constant(R, C)` gives "R is not defined" because `C` is the coulomb unit. Spec wording ("C, R are not defined") cannot hold; `Ccap` gives "Ccap, R are not defined". Spec text should be corrected.
- Criterion 20: "real part 0" cannot be tested with a unit; tested without unit (value exactly 0).
- Criterion 19/23 1e-9 tolerance: not observable through a 6-digit display; I used 1e-5 through the engine and the developer's direct-call test covers 1e-9.

### Observations (not defects)
- Argument names `L` and `C` are in the hint of 1B functions (spec table names them) although `C` is the coulomb unit and `L` is a typical user variable. A user variable `L := 0.1 H` works normally (tested); only the placeholder-name landmine from GUI-4 matters (`Ccap`, `Lind`), still to be implemented in GUI-1.
- `phasor(mag, phi)` accepts any unit including none, and `phasor_magnitude(5)` accepts a bare number; per the spec ("any unit of magnitude").
- `angular_frequency(...) = rad` is rejected ("result is s^-1"); `= Hz` is accepted (same dimension). Accepted by spec (open question 6).
- A phasor with a negative real argument e.g. `phasor(-10 V, 0)` is accepted (signed amplitude), phase becomes pi. Reasonable.

## Judgement: relaxed 1A name test (exact set -> subset)
Acceptable. The 1A file pins the 17 names via `<=` and still checks collisions over the full registry; the exact-36 set equality now lives in `test_registry_is_exactly_36_names` here (and the developer's `test_electrical.py` count 17 -> 36). Together a stray, renamed or missing name still fails a test. Recommendation: when phases 2-3 add names, update only that single equality test.

## IP
No red flags. Function names, argument names and message wording are original; formulas are generic textbook relations (impedance of R/L/C, time constants, resonance, first-order RC filter). No vendor names or copied strings in the module or tests. No Qt import in the engine module. No `.lsheet` change.

## GUI run
GUI-1 (Electrical tab buttons) is not implemented, and no computer-use tools were available in this session, so the real application was not launched. Engine behaviour was exercised through `Engine().evaluate` including autocomplete signatures. A GUI smoke test (type `rc_charge_voltage(12 V, 10 ms, 1 kohm, 10 uF) = V` in a math region; check the autocomplete popup and that a complex result like `impedance_series(...)` prints legibly) is still owed for a session with computer access and again after GUI-1.

## Verdict
PASS. 4 low defects (1 known carry-over), 0 blocker/high/medium. Phase 1B engine part is acceptable to merge; fix or document 034-1B-1/-2/-3 before the manual page for 1B is written, and correct spec criteria 34/35 wording.
