# 037 Electrical library phase 4: ideal diode relations and thermal voltage (engine + GUI)

Status: IP-reviewed by manager 2026-11-13 (generic textbook formulas, own names, no vendor keywords/tables; APPROVED once Theo answers the open questions; developer must re-run every hand-computed criterion through Engine()). Original: NOT yet IP-reviewed. Specialist proposal. Developer-ready only after (a) manager IP review, (b) a re-run of every numeric example in the acceptance criteria against the live engine (the values were computed by hand in this session; the specialist had no code-execution tool, so the re-run is a hard gate), (c) spec 035's zero rule is decided (criteria 9, 20 and 26 depend on it), (d) spec 035 is merged (the shared argument checker and the zero rule are introduced there), and (e) the unit prerequisites below (uA, nA, pA, temperature dimension) are accepted.

Spec-numbering note: 037 is the next free number after 036 (2026-11-13). This is phase 4 of the electrical library overview (spec 034, "Phase plan" row 4). It follows spec 034's conventions (strict units, SI results, own error wording, the General rules of 034) and the GUI-1 pattern.

Source inspiration (concept only, nothing copied):
- https://en.wikipedia.org/wiki/Shockley_diode_equation (fetched 2026-11-13; facts only: the ideal diode current I_D = I_S (exp(V_D/(n V_T)) - 1), thermal voltage V_T = kT/q, ideality factor n between about 1 and 2). The article states the thermal voltage at 300 K as about 25.852 mV; the value in criterion 5 is independently computed and agrees with it.
- Constants: https://docs.scipy.org/doc/scipy/reference/constants.html (fetched 2026-11-13; confirmed names `k` (Boltzmann constant) and `e` (elementary charge) in scipy.constants). Values come from the library at run time; this spec does not restate them.
- Subject-area noun only: "semiconductors" from the 034 research note outline (item 10). No vendor manual, catalogue, menu, keyword or example was used.

User story:
As an electrical engineer writing a calculation sheet, I want the thermal voltage of a junction, the ideal diode current at a given voltage, and the small-signal resistance and forward voltage of a diode at a given current, so that I can check a bias point without looking up constants, with temperature in kelvin and all results in SI.

## Behaviour (own words)

### General rules (this spec)
1. Calling convention: ordinary positional function calls in a math region. No keyword arguments. Argument names are documentation (shown in autocomplete call hints).
2. Dimension check per argument: `Tk` is a temperature (kelvin only); `Vd` is a voltage (any sign); `Isat`, `Id` are currents (A); `n` is a plain number (ideality factor, no unit). A bare number in a temperature, voltage or current slot is an error ("needs a unit of ..."). A unit in the plain-number slot is an error.
3. Sign and range rules: `Tk`, `Isat`, `Id` and `n` must be greater than zero. `Vd` may be negative, zero or positive.
4. Zero rule (spec 035 general rule): a zero in a positive-only slot gives "must be greater than zero"; `Vd` accepts zero (bare 0 or `0 V`, since the engine drops the unit of zero).
5. Constants: the Boltzmann constant k and the elementary charge e come from `scipy.constants` (`k` and `e`; approved dependency). Thermal voltage is V_T = k T / e.
6. Results are SI: V for voltages, A for currents, ohm for the small-signal resistance. The functions return the same value whatever unit the inputs were given in (mV, mA, nA, kohm are accepted and converted).
7. Temperature in kelvin only. Celsius is not accepted (open question 1). An input such as `25 deg` (dimensionless in the engine) is rejected as "needs a unit of temperature".
8. Functions are pure: no state, no `.lsheet` change.
9. Error text is LiveSheet's own: `<function>: <argument> <problem>`, never a Python traceback.
10. Ideal diode (stated, not enforced): Shockley model with ideality factor n; no series resistance, no breakdown, no temperature dependence of the saturation current, no recombination corrections beyond n. The manual says so.

### Function list (engine, developer-ready)
Notation: V_T = thermal voltage (V), computed inside the functions. All results SI.

| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| D1 | `thermal_voltage(Tk)` | Tk: temperature (K, positive) | V_T = k Tk / e | V |
| D2 | `diode_current(Vd, Isat, n, Tk)` | Vd: V (any sign); Isat: A (positive); n: plain number (positive); Tk: K (positive) | I = Isat (exp(Vd / (n V_T)) - 1) | A |
| D3 | `diode_small_signal_resistance(Id, n, Tk)` | Id: A (positive); n: plain (positive); Tk: K (positive) | r = n V_T / Id | ohm |
| D4 | `diode_forward_voltage(Id, Isat, n, Tk)` | Id: A (positive); Isat: A (positive); n: plain (positive); Tk: K (positive) | Vd = n V_T ln(Id / Isat + 1) (exact inverse of D2 for the same Isat, n, Tk) | V |

Notes on the table:
- D3 is the small-signal resistance of the ideal diode at current Id. The exact slope of the Shockley model is n V_T/(Id + Isat); D3 drops Isat, so it is accurate when Id is much larger than Isat (for example 1 mA against 1 pA the difference is about 1e-9 relative). The manual states this.
- D4 is the inverse of D2 for the same Isat, n and Tk: `diode_forward_voltage(diode_current(V, Isat, n, Tk), Isat, n, Tk)` returns V (criterion 15).
- Argument names: Vd, Isat, n, Tk, Id. The argument names avoid unit letters (V, A, K, F, H, C, T, W, S, e, I) so an unfilled template is reported as "not defined" (same landmine as spec 018 and 034 GUI-4).

## Unit prerequisites (engine, phase 4; small units.py change, developer-ready)
The engine has `mA` and `kA`, but no microampere, nanoampere or picoampere, which the reverse saturation currents of real diodes need (typically pA to nA).
1. Add `uA` and `μA` (microampere, same value; `μA` uses the same micro-sign codepoint as the existing `μF` and `μH` entries), `nA` (1e-9 A) and `pA` (1e-12 A), with the same pattern as `uF`/`nF` and `pF` (spec 034 prerequisite 2).
2. Temperature: add a "temperature" dimension to the engine's dimension table with the kelvin unit `K` (already in `UNITS`). No new unit name. `K` is the only accepted temperature unit.
3. Test: `1 nA = A` gives 1e-9 A; `1 pA = A` gives 1e-12 A; `1 uA = A` and `1 μA = A` give 1e-6 A.

## Acceptance criteria (phase 4)

### Engine part (Qt-free, `livesheet/engine/semiconductor.py`, merged into the evaluator's builtins like `ELEC_BUILTINS`)
Tests use `Engine().evaluate(...)` with explicit display units. Tolerance 1e-6 relative unless stated. Values were computed by hand: exact identities where possible; the exponential cases use exponents computed to about 9 significant figures and carry a looser tolerance (1e-4). Hand-computed basis: V_T at 300 K is 300 times k/e = 300 times 8.617333262145e-5 V/K = 0.02585199978643 V (k and e are exact SI values since 2019). Re-run required.

Registration and naming
1. All 4 names are callable in a math region and appear in the function-name autocomplete with their argument names: `thermal_voltage(Tk)`, `diode_current(Vd, Isat, n, Tk)`, `diode_small_signal_resistance(Id, n, Tk)`, `diode_forward_voltage(Id, Isat, n, Tk)`.
2. No name equals a `BUILTINS` key, a `UNITS` key, or a `syntax.py` keyword (set intersection test).
3. `semiconductor.py` imports no PySide6. The constants are read from `scipy.constants` (no hard-coded numbers in the source). `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" message, for example `thermal_voltage(300 K, 1)`.

Thermal voltage (D1)
5. `thermal_voltage(300 K) = mV` gives 25.852 mV (exact value 25.8519998 mV; tolerance 1e-6 relative). Matches the 25.852 mV at 300 K stated in the Wikipedia article (cross-check).
6. `thermal_voltage(350 K) = mV` gives 30.1607 mV (exact value 30.1606664 mV).
7. Proportionality: `thermal_voltage(600 K) =` equals twice `thermal_voltage(300 K) =` (exact proportionality to T).

Diode current (D2)
8. Identity at ln 11: `diode_current(thermal_voltage(300 K) * ln(11), 1 nA, 1, 300 K) = nA` gives 10 nA (since exp(ln 11) = 11, so I = Isat (11 - 1)).
9. Zero bias: `diode_current(0 V, 1 pA, 1, 300 K) =` gives 0 (bare; the engine drops the unit of zero; accepted because Vd allows zero).
10. Hand-computed realistic point: `diode_current(0.6 V, 1 pA, 1, 300 K) = mA` gives 12.0104 mA (about 12.01037 mA; exponent 0.6 / V_T = 23.2090362, exp of it about 1.20104e10). Tolerance 1e-4.
11. Reverse bias saturates: `diode_current(-1 V, 1 pA, 1, 300 K) = pA` gives -1 pA (exp(-38.68) is about 1.6e-17, negligible; tolerance 1e-6).
12. Ideality scaling identity: `diode_current(0.6 V, 1 pA, 2, 300 K) =` equals `diode_current(0.3 V, 1 pA, 1, 300 K) =` (because 0.6 / (2 V_T) = 0.3 / V_T; equal within tolerance 1e-9).

Small-signal resistance (D3)
13. `diode_small_signal_resistance(1 mA, 1, 300 K) = ohm` gives 25.852 ohm (exact 25.8519998 ohm).
14. `diode_small_signal_resistance(1 mA, 2, 300 K) = ohm` gives 51.704 ohm (exact 51.7039996 ohm; doubles with n).

Forward voltage (D4)
15. Round trip: `diode_forward_voltage(diode_current(0.6 V, 1 pA, 1, 300 K), 1 pA, 1, 300 K) = V` gives 0.6 V (tolerance 1e-9 relative, since the two functions are exact inverses).
16. `diode_forward_voltage(1 mA, 1 pA, 1, 300 K) = V` gives 0.535738 V (V_T times ln(1e9 + 1), with ln(1e9 + 1) = 20.7232658; tolerance 1e-5). Note: 1 mA / 1 pA = 1e9.
17. Ideality doubles the forward voltage: `diode_forward_voltage(1 mA, 1 pA, 2, 300 K) =` equals twice the criterion 16 value (1.071476 V; tolerance 1e-5).

Errors (no result, LiveSheet message, no traceback)
18. Bare temperature: `thermal_voltage(300)` gives `thermal_voltage: Tk needs a unit of temperature, for example 1 K`.
19. Wrong dimension: `thermal_voltage(300 V)` gives `thermal_voltage: Tk must be a temperature, not V`.
20. Zero or negative temperature (zero rule): `thermal_voltage(0 K)` and `thermal_voltage(-10 K)` both give `thermal_voltage: Tk must be greater than zero`.
21. Celsius-like input: `thermal_voltage(25 deg)` gives `thermal_voltage: Tk needs a unit of temperature, for example 1 K` (the degree sign is dimensionless in the engine; no Celsius conversion in this phase).
22. Bare voltage: `diode_current(0.6, 1 pA, 1, 300 K)` gives `diode_current: Vd needs a unit of voltage, for example 1 V`.
23. Negative saturation current: `diode_current(0.6 V, -1 pA, 1, 300 K)` gives `diode_current: Isat must be greater than zero`.
24. Ideality zero (plain number, positive slot): `diode_current(0.6 V, 1 pA, 0, 300 K)` gives `diode_current: n must be greater than zero`.
25. Missing temperature unit: `diode_current(0.6 V, 1 pA, 1, 300)` gives `diode_current: Tk needs a unit of temperature, for example 1 K`.
26. Zero current (zero rule): `diode_small_signal_resistance(0 A, 1, 300 K)` gives `diode_small_signal_resistance: Id must be greater than zero`.
27. Wrong dimension in a current slot: `diode_small_signal_resistance(1 V, 1, 300 K)` gives `diode_small_signal_resistance: Id must be a current, not V`.
28. Negative current in the forward-voltage function: `diode_forward_voltage(-1 mA, 1 pA, 1, 300 K)` gives `diode_forward_voltage: Id must be greater than zero`.
29. Undefined name: `diode_current(Vd_x, 1 pA, 1, 300 K)` with nothing defined gives `Vd_x is not defined`.

Unit prerequisites (phase 4)
30. `1 nA = A` gives 1e-9 A; `1 pA = A` gives 1e-12 A; `1 uA = A` and `1 μA = A` give 1e-6 A; `1 nA = pA` gives 1000 pA (consistent SI prefixes).

### GUI part (Electrical tab, separate sub-group; same mechanism as spec 034 GUI-1)
GUI-1. The Electrical tab gains one new sub-header "Semiconductors", appended after the spec 034, 035 and 036 groups (Electrical order: ..., Filters, Digital Logic, Operational Amplifiers, Semiconductors). The tab stays one tab; TAB_ORDER unchanged.
GUI-2. Exactly 4 new buttons, one per function D1-D4, with the label, inserted text and tooltip in GUI-4. Each button calls the existing `insert_token(token)` callback. No new widget type, no dialog, no on-canvas editing.
GUI-3. Clicking "thermal voltage" inserts `thermal_voltage(Tk)` at the cursor.
GUI-4. Button list (label | inserted text | tooltip; SI only, each tooltip states the units of inputs and result):
- "thermal voltage" | `thermal_voltage(Tk)` | Thermal voltage kT/q. Tk in K (kelvin only); result in V.
- "diode current" | `diode_current(Vd, Isat, n, Tk)` | Ideal diode current Isat (exp(Vd/(n V_T)) - 1). Vd in V, Isat in A (positive), n a plain number, Tk in K; result in A.
- "diode small-signal resistance" | `diode_small_signal_resistance(Id, n, Tk)` | Small-signal resistance n V_T/Id. Id in A (positive), n a plain number, Tk in K; result in ohm.
- "diode forward voltage" | `diode_forward_voltage(Id, Isat, n, Tk)` | Forward voltage n V_T ln(Id/Isat + 1) for a current Id. Id and Isat in A (positive), n a plain number, Tk in K; result in V.
Placeholder names (Vd, Isat, n, Tk, Id) are not unit letters, so an unfilled template gives "is not defined" instead of a silent unit (same landmine as spec 018 and 034 GUI-4).
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change. No keyboard shortcut (click only, as in spec 020/034).
GUI-6. Regression: the existing buttons of the Electrical tab (DC Circuits, Power, spec 034 groups, spec 035 and 036 groups) are unchanged in label, text and order. After this spec the Electrical tab has 61 + 4 = 65 buttons.
GUI-7. Tests that count the Electrical tab's sub-groups or buttons are adapted by the developer to the new totals (as in spec 034 GUI-1); the original prefix checks are kept.

## Syntax proposal (own keywords)
None. Function calls only. No grammar change.

## Implementation placement (developer)
- `livesheet/engine/semiconductor.py` (new, Qt-free): `SEMI_BUILTINS` with the 4 names, each with an explicit Python signature (argument names for autocomplete hints), merged in `evaluator._builtins()` next to `ELEC_BUILTINS`, `LOGIC_BUILTINS` and `OPAMP_BUILTINS`. Constants: `from scipy import constants` (scipy is an approved dependency; the lazy-import pattern of `statistics.py` may be used if start-up time matters; developer's call, no behaviour change).
- `livesheet/engine/units.py`: the unit prerequisites only (uA, μA, nA, pA) and the temperature dimension entry for `K`.
- Shared argument checker from spec 035 (positive, plain-number and zero rules); temperature kind added in the shared module.
- `livesheet/gui/sidepanel.py`: a new token list `_SEMI_TOKENS` (4 tuples) appended to `MATH_TOKENS`; the category "Semiconductors" appended to `TAB_CATEGORIES["Electrical"]` after "Operational Amplifiers". TAB_ORDER unchanged.
- Tests: `tests/test_semiconductor.py` (developer); independent black-box `tests/test_semiconductor_blackbox.py` (tester, from this spec only); GUI button checks in the tester's file.

## Edge cases
- Very large forward bias (for example `diode_current(5 V, 1 pA, 1, 300 K)`): the exponential is about 1e84 times Isat (5 / V_T is about 193, and 193 / ln 10 is about 84); the result is large but finite and is returned without warning. No clamping.
- Very small current in D3 (for example 1 pA): the resistance is large (about 2.6e10 ohm at 300 K, n = 1); returned as is.
- Temperature 0 K is rejected (criterion 20); very high temperatures are not checked against any material limit.
- A zero forward voltage is accepted through `Vd` (D2); D4 has no zero-voltage input, since its inputs are currents.
- The engine's own names `e` and `I` keep their engine meaning (Euler's number and the imaginary unit) in user sheets: the constants are used only inside the Python module.
- Ideality factor below 1 or above 2: accepted without warning (open question 4).

## IP check
Pass, pending manager review. Own function names (`thermal_voltage`, `diode_*`), argument names, error wording and button labels. The formulas are the ideal (Shockley) diode relations and the thermal voltage kT/q, as stated in the public Wikipedia article "Shockley diode equation" (fetched 2026-11-13, facts only, CC BY-SA 4.0; no sentence copied). The constants come from `scipy.constants` (BSD-licensed library, approved 2026-10-27; names confirmed on the SciPy documentation page, fetched 2026-11-13). No vendor manual, catalogue, menu, keyword, example or table was used, and no copyrighted table of constants is reproduced in this spec. No new UI type; buttons use the existing insertion mechanism. No on-canvas editing, so no patent-sensitive interaction is involved (IP-POLICY rule 6 not triggered). Not legal advice; legal review before 1.0 is a standing item.

## Verification status (specialist)
- Hand-computed values: criteria 5-6 (thermal voltage: k/e = 8.617333262145e-5 V/K, cross-checked against the Wikipedia value 25.852 mV at 300 K), 10 (about 12.01037 mA, tolerance 1e-4), 13-14 (25.852 and 51.704 ohm), 16-17 (0.535738 V and 1.071476 V).
- Exact identities (criteria 8, 12, 15) need no hand numbers beyond the stated algebra.
- No code-execution tool was available to the specialist in this session. The engine re-run of every criterion is a hard gate before developer dispatch; in particular criterion 10 is hand-computed to about 6 significant figures and must be checked.

## Fits current architecture?
- `livesheet/engine/semiconductor.py` (new, Qt-free), merged like `ELEC_BUILTINS`; constants from `scipy.constants` (approved).
- `livesheet/engine/units.py`: four current-prefix names and a temperature dimension (existing pattern).
- Shared argument checker from spec 035.
- GUI: one token list and one sub-group in the existing Electrical tab (spec 034 GUI-1 pattern).
- No `.lsheet` change, no new dependency.

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Temperature in kelvin only (recommended). Celsius and Fahrenheit input are out of scope; the existing backlog item 6 (Celsius) is the place for a conversion, and this library must not add a non-SI temperature.
2. Constants from `scipy.constants` (recommended, approved dependency), not typed in by hand, so the library follows the library's own CODATA values.
3. Ideal Shockley model only (recommended): no series resistance, breakdown, saturation-current temperature dependence or reverse-recovery. Real-device corrections would be a separate spec.
4. Ideality factor accepted without range warning (recommended; typical values 1 to 2 are stated in the manual, but no check is made).
5. Unit prerequisites uA, μA, nA, pA (recommended: the same prefix pattern as spec 034's henry and farad prefixes). Confirm before the developer adds them to units.py.
6. Zero rule: depends on spec 035 open question 1; criteria 9, 20 and 26 change if it is rejected.
