# 036 Electrical library phase 3: ideal operational-amplifier functions (engine + GUI)

Status: IP-reviewed by manager 2026-11-13 (generic textbook formulas, own names, no vendor keywords/tables; APPROVED once Theo answers the open questions; developer must re-run every hand-computed criterion through Engine()). Original: NOT yet IP-reviewed. Specialist proposal. Developer-ready only after (a) manager IP review, (b) a re-run of every numeric example in the acceptance criteria against the live engine (the values were computed by hand in this session; the specialist had no code-execution tool, so the re-run is a hard gate), (c) spec 035's zero rule (open question 1 of spec 035) is decided, because criteria 17, 25, 29 and 31 depend on it, and (d) spec 035 is merged, because the shared argument checker is introduced there.

Spec-numbering note: 036 is the next free number after 035 (2026-11-13). This is phase 3 of the electrical library overview (spec 034, "Phase plan" row 3). It follows spec 034's conventions (strict units, SI results, own error wording, the General rules of 034) and the GUI-1 pattern (engine part, then GUI part).

Source inspiration (concept only, nothing copied):
- https://en.wikipedia.org/wiki/Operational_amplifier_applications (fetched 2026-11-13; also the research note of 2026-11-12). Facts only: ideal inverting gain -Rf/Rin, ideal non-inverting gain 1 + Rf/Rg, ideal summing amplifier output -Rf (V1/R1 + ... + Vn/Rn), and the ideal-device assumptions (infinite open-loop gain, infinite differential input impedance, no input current, virtual short between the inputs). No sentence copied.
- Clipping to the supply rails (saturation) is the generic idea that a real output cannot exceed its supply; stated as a textbook fact.

User story:
As an electrical engineer writing a calculation sheet, I want the ideal gain of inverting, non-inverting and summing op-amp circuits, the output after clipping at the supply rails, and a check that tells me whether a given input saturates the amplifier, so that I can size resistors and see clipping without re-deriving formulas, with V, ohm and rail values checked by dimension.

## Behaviour (own words)

### General rules (this spec)
1. Calling convention: ordinary positional function calls in a math region. No keyword arguments. Argument names are documentation (shown in autocomplete call hints).
2. Dimension check per argument, as in spec 034: `Rf`, `Rin`, `Rg`, `Rk` are resistances (ohm); `Vin`, `Vk` are voltages (V); `Vrail` is a voltage (V). `gain` is a plain number (no unit). A bare number in a dimensional slot is an error ("needs a unit of voltage, for example 1 V"). A unit in the plain-number slot is an error.
3. Sign and range rules: `Rf`, `Rin`, `Rg`, `Rk` and `Vrail` must be greater than zero. `Vin` and the entries of `Vk` may be negative or zero. `gain` may be any plain number, positive or negative.
4. Zero rule (spec 035 general rule; open question 1 of spec 035): a zero in a positive-only slot gives "must be greater than zero"; a zero in a slot that allows zero is accepted. A zero with a unit is read as the value zero, because the engine drops the unit of zero.
5. Results: resistor-ratio gains are plain numbers (no unit). Output voltages are in V (SI). A saturation check returns the bit 1 or 0 (plain number).
6. Vector arguments (`Vk`, `Rk`) use the engine's column-vector syntax (`[1 V; 2 V]`, spec 002). A scalar is accepted as a one-entry vector.
7. Functions are pure: no state, no `.lsheet` change.
8. Error text is LiveSheet's own: `<function>: <argument> <problem>`, never a Python traceback.
9. Ideal device (stated, not enforced): infinite open-loop gain, infinite input impedance, no input bias or offset, no finite bandwidth, no slew limit, no output current limit. The functions state the ideal result; a real device differs. The manual must say so.

### Function list (engine, developer-ready)
| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| O1 | `opamp_inverting_gain(Rf, Rin)` | Rf, Rin: ohm (positive) | -Rf / Rin | plain number |
| O2 | `opamp_noninverting_gain(Rf, Rg)` | Rf, Rg: ohm (positive) | 1 + Rf / Rg | plain number |
| O3 | `opamp_summing_output(Vk, Rk, Rf)` | Vk: vector of V (any sign, zero allowed); Rk: vector of ohm (positive); Rf: ohm (positive); Vk and Rk have the same number of entries | -Rf (sum over k of Vk / Rk) | V |
| O4 | `opamp_output(Vin, gain, Vrail)` | Vin: V (any sign); gain: plain number (any sign); Vrail: V (positive) | min(max(gain Vin, -Vrail), +Vrail): the ideal output, clipped to the symmetric rails | V |
| O5 | `opamp_is_saturated(Vin, gain, Vrail)` | same as O4 | 1 when |gain Vin| is greater than Vrail (the output would clip); 0 otherwise. Equal to the rail counts as not saturated | bit (plain 0 or 1) |

Notes on the table:
- O1 and O2 are the ideal closed-loop gains of the two basic configurations; O3 is the ideal inverting summing amplifier, where each input k has the gain -Rf/Rk.
- O4 uses symmetric rails (+Vrail and -Vrail). Asymmetric rails are out of scope (open question 2).
- O3 does not clip (open question 3). Rail clipping is done by O4 for a single gain, or by comparing the O3 result with +/- Vrail by hand.
- O5 is a check, not a model: it tells the user whether the O4 result is clipped.

## Unit prerequisites
None. Gains are plain numbers; outputs use the existing `V` unit. No change to `livesheet/engine/units.py`.

## Acceptance criteria (phase 3)

### Engine part (Qt-free, `livesheet/engine/opamp.py`, merged into the evaluator's builtins like `ELEC_BUILTINS`)
Tests use `Engine().evaluate(...)`. Voltages use explicit display units (`= V`), and the tolerance is 1e-6 relative unless stated. Millivolt inputs in the boundary cases are exact rationals (`1200 mV` is exactly 6/5 V), so the boundary is not decided by floating-point noise. Values were computed by hand (exact fractions where possible; 47/22 is written to 6 significant digits). A bare `=` on a zero voltage prints the bare 0 (the engine drops the unit of zero; known quirk, spec 034 1A-1).

Registration and naming
1. All 5 names are callable in a math region and appear in the function-name autocomplete with their argument names: `opamp_inverting_gain(Rf, Rin)`, `opamp_noninverting_gain(Rf, Rg)`, `opamp_summing_output(Vk, Rk, Rf)`, `opamp_output(Vin, gain, Vrail)`, `opamp_is_saturated(Vin, gain, Vrail)`. Typing `opamp_` lists all five.
2. No name equals a `BUILTINS` key, a `UNITS` key, or a `syntax.py` keyword (set intersection test).
3. `opamp.py` imports no PySide6. `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" message, for example `opamp_output(1 V, 2)`.

Gains (O1, O2)
5. `opamp_inverting_gain(10 kohm, 1 kohm) =` gives -10.
6. `opamp_inverting_gain(4.7 kohm, 2.2 kohm) =` gives -2.13636 (47/22 = 2.136363..., negative sign).
7. `opamp_noninverting_gain(9 kohm, 1 kohm) =` gives 10.
8. `opamp_noninverting_gain(1 kohm, 1 kohm) =` gives 2.

Summing (O3)
9. `opamp_summing_output([1 V; 2 V], [10 kohm; 20 kohm], 10 kohm) = V` gives -2 V. (Check: -10000 (1/10000 + 2/20000) = -2.)
10. `opamp_summing_output([-1 V; 0.5 V], [10 kohm; 10 kohm], 20 kohm) = V` gives 1 V. (Check: -20000 (-1/10000 + 0.5/10000) = +1, a negative input and a positive input.)
11. Single entry, scalar form: `opamp_summing_output(200 mV, 4 kohm, 10 kohm) = V` gives -0.5 V.
12. Consistency with O1: `opamp_summing_output(200 mV, 4 kohm, 10 kohm) = V` equals `opamp_inverting_gain(10 kohm, 4 kohm) * 200 mV = V` (both -0.5 V; -2.5 times 0.2 V).

Output with rails (O4)
13. `opamp_output(200 mV, -10, 12 V) = V` gives -2 V (not clipped).
14. `opamp_output(1.5 V, -10, 12 V) = V` gives -12 V (ideal -15 V, clipped at the negative rail).
15. `opamp_output(-1.5 V, -10, 12 V) = V` gives 12 V (ideal +15 V, clipped at the positive rail).
16. Boundary, exactly on the rail: `opamp_output(1200 mV, -10, 12 V) = V` gives -12 V (ideal -12 V is equal to the rail, so the output is -12 V either way).
17. Zero input: `opamp_output(0 V, 5, 12 V) =` gives 0 (bare, no unit; zero result loses its unit, spec 034 1A-1). Use the bare `=` form.

Saturation check (O5)
18. `opamp_is_saturated(1.5 V, -10, 12 V) =` gives 1 (|-15| > 12).
19. `opamp_is_saturated(200 mV, -10, 12 V) =` gives 0 (|-2| is not greater than 12).
20. Boundary: `opamp_is_saturated(1200 mV, -10, 12 V) =` gives 0 (|-12| is equal to the rail, not greater).
21. `opamp_is_saturated(1201 mV, -10, 12 V) =` gives 1 (|-12.01| is greater than 12).
22. Consistency: for every case of criteria 13-16 and 18-21, O5 returns 1 exactly when the O4 output differs from gain times Vin (the output was clipped), and 0 when it does not.

Errors (no result, LiveSheet message, no traceback)
23. Zero feedback-input resistor (zero rule): `opamp_inverting_gain(10 kohm, 0 ohm)` gives `opamp_inverting_gain: Rin must be greater than zero`.
24. Negative resistor: `opamp_inverting_gain(10 kohm, -1 kohm)` gives `opamp_inverting_gain: Rin must be greater than zero`.
25. Wrong dimension: `opamp_inverting_gain(10 V, 1 kohm)` gives `opamp_inverting_gain: Rf must be a resistance, not V`.
26. Bare number in a resistance slot: `opamp_noninverting_gain(9, 1 kohm)` gives `opamp_noninverting_gain: Rf needs a unit of resistance, for example 1 ohm`.
27. Bare voltage: `opamp_output(1.5, -10, 12 V)` gives `opamp_output: Vin needs a unit of voltage, for example 1 V`.
28. Unit on the gain: `opamp_output(1 V, 10 V, 12 V)` gives `opamp_output: gain must be a plain number, not V`.
29. Rail must be positive: `opamp_output(1 V, -10, -12 V)` gives `opamp_output: Vrail must be greater than zero`; with a zero rail (`0 V`): the same message (zero rule).
30. Vector length mismatch: `opamp_summing_output([1 V; 2 V], [10 kohm], 10 kohm)` gives `opamp_summing_output: Vk and Rk must have the same number of entries (2 and 1)`.
31. Zero summing resistor (zero rule): `opamp_summing_output(1 V, 0 ohm, 10 kohm)` gives `opamp_summing_output: Rk must be greater than zero`.
32. Wrong dimension in the feedback slot: `opamp_summing_output(1 V, 4 kohm, 10 V)` gives `opamp_summing_output: Rf must be a resistance, not V`.
33. Undefined name: with nothing defined, `opamp_is_saturated(Vx, 2, 12 V)` gives `Vx is not defined`.

### GUI part (Electrical tab, separate sub-group; same mechanism as spec 034 GUI-1)
GUI-1. The Electrical tab gains one new sub-header "Operational Amplifiers", appended after the spec 034 groups and after spec 035's "Digital Logic" (Electrical order: ..., Filters, Digital Logic, Operational Amplifiers). The tab stays one tab; TAB_ORDER unchanged.
GUI-2. Exactly 5 new buttons, one per function O1-O5, with the label, inserted text and tooltip in GUI-4. Each button calls the existing `insert_token(token)` callback. No new widget type, no dialog, no on-canvas editing.
GUI-3. Clicking "inverting gain" inserts `opamp_inverting_gain(Rf, Rin)` at the cursor.
GUI-4. Button list (label | inserted text | tooltip; SI only, each tooltip states the units of inputs and result):
- "inverting gain" | `opamp_inverting_gain(Rf, Rin)` | Ideal inverting gain -Rf/Rin. Rf, Rin in ohm; result is a plain number.
- "non-inverting gain" | `opamp_noninverting_gain(Rf, Rg)` | Ideal non-inverting gain 1 + Rf/Rg. Rf, Rg in ohm; result is a plain number.
- "summing output" | `opamp_summing_output(Vk, Rk, Rf)` | Ideal inverting summing output -Rf sum(Vk/Rk). Vk in V (vector, any sign), Rk in ohm (vector, positive), Rf in ohm; result in V. No rail clipping.
- "output with rails" | `opamp_output(Vin, gain, Vrail)` | Ideal output gain Vin, clipped to +/- Vrail. Vin in V, gain a plain number, Vrail in V (positive); result in V.
- "rail saturation check" | `opamp_is_saturated(Vin, gain, Vrail)` | 1 when |gain Vin| exceeds Vrail (the output would clip), else 0. Vin in V, gain a plain number, Vrail in V.
Placeholder names (Rf, Rin, Rg, Vk, Rk, Vin, gain, Vrail) are not unit letters, so an unfilled template gives "is not defined" instead of a silent unit (same landmine as spec 018 and 034 GUI-4).
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change. No keyboard shortcut (click only, as in spec 020/034).
GUI-6. Regression: the existing buttons of the Electrical tab (DC Circuits, Power, spec 034 groups, spec 035 group) are unchanged in label, text and order. After this spec the Electrical tab has 56 + 5 = 61 buttons.
GUI-7. Tests that count the Electrical tab's sub-groups or buttons are adapted by the developer to the new totals (as in spec 034 GUI-1); the original prefix checks are kept.

## Syntax proposal (own keywords)
None. Function calls and the existing column-vector syntax only. No grammar change.

## Implementation placement (developer)
- `livesheet/engine/opamp.py` (new, Qt-free): `OPAMP_BUILTINS` with the 5 names, each with an explicit Python signature (argument names for autocomplete hints), merged in `evaluator._builtins()` next to `ELEC_BUILTINS` and `LOGIC_BUILTINS` (spec 035).
- Shared argument checker from spec 035 (plain-number kind and zero rule). Spec 035 is merged first; the developer must not copy the checker.
- Output clipping: `min(max(...))` on the SI magnitudes. The result must be a real number (a non-real input is an error; see edge cases).
- `livesheet/gui/sidepanel.py`: a new token list `_OPAMP_TOKENS` (5 tuples) appended to `MATH_TOKENS`; the category "Operational Amplifiers" appended to `TAB_CATEGORIES["Electrical"]` after "Digital Logic". TAB_ORDER unchanged.
- Tests: `tests/test_opamp.py` (developer); independent black-box `tests/test_opamp_blackbox.py` (tester, from this spec only); GUI button checks in the tester's file.

## Edge cases
- Ideal assumptions (general rule 9) are stated in the tooltip and the manual; they are not enforced.
- Gain of zero: `opamp_output(1 V, 0, 12 V)` gives the bare 0 (zero result loses its unit). Not an error: a zero gain is a valid ideal result.
- Very large gain: no warning; the output clips (criteria 14-15 pattern).
- Empty vector: `opamp_summing_output([], [], 10 kohm)` is rejected by the engine's "Empty matrix" error before the function runs (same quirk as spec 034 1B-3); the function's own "needs at least one entry" message is implemented for programmatic callers.
- Complex inputs (for example a phasor voltage): rejected with "must be a real number". The op-amp functions are DC/ideal; AC gain with frequency is out of scope (a later phase).
- `opamp_is_saturated` on a gain of exactly 0: always 0 (zero output never exceeds a positive rail).
- Summing with a negative resistor: rejected (criterion 31 pattern); summing with a zero input voltage is accepted (zero allowed in Vk).

## IP check
Pass, pending manager review. Own function names (opamp_ prefix), argument names, error wording and button labels. The formulas are the textbook ideal-op-amp relations (inverting, non-inverting, summing amplifier) and the ideal-device assumptions, stated in the public Wikipedia article "Operational amplifier applications" (fetched 2026-11-13, facts only, CC BY-SA 4.0; no sentence copied). Rail clipping is generic textbook content. No vendor manual, catalogue, menu, keyword, example circuit or table was used. No new UI type; buttons use the existing insertion mechanism. No on-canvas editing, so no patent-sensitive interaction is involved (IP-POLICY rule 6 not triggered). Not legal advice; legal review before 1.0 is a standing item.

## Verification status (specialist)
- Hand-computed exact values: criteria 5-8 (gains), 9-12 (summing; 12 is an identity check), 13-21 (rails and saturation, exact millivolt rationals at the boundary), 23-33 (messages follow the 034 pattern).
- No code-execution tool was available to the specialist in this session. The engine re-run of every criterion is a hard gate before developer dispatch.

## Fits current architecture?
- `livesheet/engine/opamp.py` (new, Qt-free), merged like `ELEC_BUILTINS`.
- Uses the shared argument checker from spec 035 (no copy).
- No `units.py` change, no `.lsheet` change, no new dependency (SymPy arithmetic; `min`/`max` on real magnitudes).
- GUI: one token list and one sub-group in the existing Electrical tab (spec 034 GUI-1 pattern).

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Ideal-device model only (recommended): no offset, bias, bandwidth, slew rate, finite gain or output current limit. Real-device corrections would be a separate spec.
2. Symmetric supply rails only (+Vrail, -Vrail) (recommended). Asymmetric rails (for example 0 to 5 V single supply) would need two rail arguments and a separate spec.
3. O3 summing output does not clip (recommended). A clipped summing output would be a new function or an extra argument (the rail), to decide when the GUI needs it.
4. Saturation boundary: a value exactly on the rail is not saturated (recommended, criteria 16 and 20).
5. Further op-amp circuits (difference amplifier, integrator, differentiator, voltage follower) are not in phase 3. Recommendation: add the difference amplifier in a follow-up if asked; the others need time-domain input.

## Phase 4 (other spec)
Spec 037 (semiconductors) follows; its own developer slice.
