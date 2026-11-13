# 034 Electrical-engineering function library: overview, roadmap, phase 1 (engine + GUI)

Status: NOT yet IP-reviewed by manager. Specialist proposal. Phase 1 becomes developer-ready only after (a) manager IP review, (b) a re-run of every numeric example in the acceptance criteria against the live engine, and (c) the unit prerequisite in section "Unit prerequisites" is accepted (it changes units.py). Phases 2 to 6 are outline only and each needs its own follow-up spec.

Spec-numbering note: 034 is the next free number after 033 (2026-11-12). Sibling of spec 033 (mechanical library) and follows its conventions (strict units, SI results, own error wording). Relates to spec 020 (Electrical formula tab, shipped: DC Circuits and Power groups) and backlog 8a(ii) (constants).

Source inspiration (concept only, nothing copied):
- Research note docs/board/research/elec-eng-topics.md (2026-11-12): subject-area outline, public sources, unit gap list, IP statement.
- Public Wikipedia articles listed there (CC BY-SA 4.0, facts only, accessed 2026-11-12): Electrical impedance, Phasor, Power factor, Root mean square, RLC circuit, RC circuit, RL circuit, Low-pass filter, Three-phase electric power, Transformer, Operational amplifier applications, Shockley diode equation, Transmission line, PID controller, Boolean algebra.
- Subject-area nouns only from listing and catalogue search snippets (research note 1a). No vendor manual, menu, keyword, example or table was used.

User story:
As an electrical engineer writing a calculation sheet, I want ready-made functions for AC power, impedance, resonance, filters, three-phase and transformer relations, which I can call in a math region or insert from the Electrical tab, with units checked and results in SI, so that I do not re-derive formulas and do not mix up V and kV or Hz and rad/s.

## Theo's SI rule (2026-11-12, applies to all of this spec and to spec 033)
1. Every function input accepts any compatible unit (for example kV for a voltage, mohm for a resistance), checked by dimension.
2. Every result is SI: V, A, ohm, W, VA, var, F, H, Hz, rad/s, s, rad, or dimensionless. Display in a decimal prefix of an SI unit (kV, mH, kohm) is allowed on request with the existing `= <unit>` syntax, because it is an SI-prefixed unit; results are never stored in a non-SI unit.
3. No imperial or US customary unit (inch, ft, lb, lbf, psi, ksi, mil, BTU, degF and similar) appears in any function, example, tooltip, test or doc. The library does not define any. Existing engine units that are non-SI are not used by this library.
4. Angles are radians. Angle inputs take plain numbers or `pi`-based expressions (for example `pi/3`); a value carrying a unit other than rad is an error. No degree helper is included in phase 1 (degrees are a non-SI unit; see Open question 1).

## Behaviour (own words)

### General rules (all phases)
1. Calling convention: ordinary positional function calls in a math region. No keyword arguments. Argument names are documentation (shown in autocomplete call hints).
2. Dimension check per argument (voltage, current, resistance, reactance-like impedance, inductance, capacitance, frequency, time, power, angle, dimensionless, turns). A bare number in a dimensional slot is an error ("needs a unit of voltage, for example 1 V"). A dimensionless slot with a unit is an error.
3. Positive-only inputs (R, L, C, f in capacitor/inductor and filter formulas where zero is undefined, turns, peak/RMS magnitudes where a negative value has no meaning) are errors when not greater than zero. Time t in step responses must not be negative.
4. Results are SI as listed above. Vector arguments (lists of impedances or resistances) use the column-vector syntax already in the engine (`[10 ohm; 22 ohm]`).
5. Functions are pure: no state, no `.lsheet` change.
6. Error text is LiveSheet's own: `<function>: <argument> <problem>`, never a Python traceback.
7. Complex values: functions that return impedance or phasors return complex SI values. Users never need to type `j`; the functions build the imaginary part internally (see Unit prerequisites and Open question 4).

### Phase plan
| Phase | Scope | Size | Depends on | Status |
|---|---|---|---|---|
| 1A | Resistor networks, AC power and RMS, three-phase, transformers (17 functions), plus the unit prerequisites | 2 days | units.py additions (below) | developer-ready (detail below) |
| 1B | Phasors and impedance, angular frequency, RC/RL time constants and step responses, series RLC resonance, RC filters (19 functions) | 2-3 days | 1A's unit prerequisites; engine complex support already present | developer-ready (detail below) |
| GUI-1 | Electrical tab: new sub-groups with 36 insertion buttons (separate part, same mechanism as spec 020/026) | 1 day | 1A and 1B engine parts merged | developer-ready (detail below) |
| 2 | Digital logic: AND/OR/NOT on 0/1 vectors, De Morgan checks, truth-table helpers | 1-2 days | phase 1 | outline, needs spec 035 |
| 3 | Operational amplifiers: ideal inverting and non-inverting gain, summing amplifier, saturation check against supply rails | 2 days | phase 1 | outline, needs spec 036 |
| 4 | Semiconductors: diode Shockley current, thermal voltage (constants from scipy.constants), small-signal resistance | 2 days | phase 1; constants (approved scipy) | outline, needs spec 037 |
| 5 | Transmission lines and control basics: lossless characteristic impedance, propagation speed, reflection coefficient; PID law on sampled vectors; first-order step response | 3 days | phase 1B complex support | outline, needs spec 038 |
| 6 | Network analysis (star-delta, two-port), motors and generators (synchronous speed in rad/s, not rpm) | 3+ days | sources to fetch | outline only |

### Phase 1A: function list (engine, developer-ready)
Notation: V voltage, A current, ohm resistance, W power, VA apparent power, var reactive power, rad angle, Hz frequency. All results SI.

Resistor networks (vector input; also already in DC templates of spec 020 as text):
| # | Function | Arguments (dimension) | Formula | Result |
|---|---|---|---|---|
| R1 | `resistors_series(R)` | R: vector of resistance | R_total = sum R_k | ohm |
| R2 | `resistors_parallel(R)` | R: vector of resistance | 1/R_total = sum 1/R_k | ohm |
| R3 | `voltage_divider(Vin, R1, R2)` | Vin: V; R1, R2: ohm | V_out = Vin R2/(R1 + R2), across R2 | V |
| R4 | `current_divider(Itot, R1, R2)` | Itot: A; R1, R2: ohm | I_1 = Itot R2/(R1 + R2), through R1 | A |

AC magnitudes (peak and RMS):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| M1 | `rms_from_peak(Vpk)` | Vpk: V | V_rms = V_pk/sqrt(2) | V |
| M2 | `peak_from_rms(Vrms)` | Vrms: V | V_pk = sqrt(2) V_rms | V |

AC power (sinusoidal steady state; Vrms, Irms are RMS values; phi = phase angle of the load, rad):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| P1 | `average_power(Vrms, Irms, phi)` | Vrms: V; Irms: A; phi: rad | P = Vrms Irms cos(phi) | W |
| P2 | `apparent_power(Vrms, Irms)` | Vrms: V; Irms: A | S = Vrms Irms | VA |
| P3 | `reactive_power(Vrms, Irms, phi)` | Vrms: V; Irms: A; phi: rad | Q = Vrms Irms sin(phi); positive for a lagging (inductive) load | var |
| P4 | `power_factor(phi)` | phi: rad | pf = cos(phi) | dimensionless |

Three-phase (balanced loads and balanced supply only):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| D1 | `wye_line_voltage(Vph)` | Vph: V (phase-to-neutral) | V_L = sqrt(3) V_ph | V |
| D2 | `wye_phase_voltage(Vline)` | Vline: V | V_ph = V_L/sqrt(3) | V |
| D3 | `delta_line_current(Iph)` | Iph: A (phase current of a delta load) | I_L = sqrt(3) I_ph | A |
| D4 | `three_phase_power(VL, IL, phi)` | VL: V; IL: A; phi: rad | P = sqrt(3) V_L I_L cos(phi) | W |

Transformers (ideal; turns are plain positive numbers, no unit):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| X1 | `transformer_secondary_voltage(Vp, Np, Ns)` | Vp: V; Np, Ns: turns (dimensionless) | V_s = V_p Ns/Np | V |
| X2 | `transformer_secondary_current(Ip, Np, Ns)` | Ip: A; Np, Ns: turns | I_s = I_p Np/Ns | A |
| X3 | `reflected_impedance(Zs, Np, Ns)` | Zs: ohm; Np, Ns: turns | Z_p = Zs (Np/Ns)^2 (impedance seen from the primary) | ohm |

### Phase 1B: function list (engine, developer-ready)
Phasors and impedance (complex SI values; `j` is the imaginary unit; angle in rad):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| C1 | `phasor(mag, phi)` | mag: any unit of magnitude (V or A typical); phi: rad | mag e^(j phi) = mag cos(phi) + j mag sin(phi) | same unit as mag |
| C2 | `phasor_magnitude(z)` | z: complex, magnitude-unit | abs(z) | same unit as z |
| C3 | `phasor_angle(z)` | z: complex | arg(z), in (-pi, pi] | rad |
| C4 | `impedance_resistor(R)` | R: ohm | Z = R | ohm |
| C5 | `impedance_inductor(f, L)` | f: Hz; L: H | Z = j 2 pi f L | ohm |
| C6 | `impedance_capacitor(f, C)` | f: Hz; C: F | Z = 1/(j 2 pi f C) | ohm |
| C7 | `impedance_series(z)` | z: vector of ohm (complex allowed) | Z = sum Z_k | ohm |
| C8 | `impedance_parallel(z)` | z: vector of ohm | 1/Z = sum 1/Z_k | ohm |
| C9 | `angular_frequency(f)` | f: Hz | w = 2 pi f | rad/s |

Transients (step input from zero initial state):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| T1 | `rc_time_constant(R, C)` | R: ohm; C: F | tau = R C | s |
| T2 | `rl_time_constant(L, R)` | L: H; R: ohm | tau = L/R | s |
| T3 | `rc_charge_voltage(Vs, t, R, C)` | Vs: V; t: s (>= 0); R: ohm; C: F | v_C(t) = Vs (1 - e^(-t/(R C))) | V |
| T4 | `rl_current_rise(Vs, t, R, L)` | Vs: V; t: s (>= 0); R: ohm; L: H | i(t) = (Vs/R)(1 - e^(-R t/L)) | A |

Resonance (series RLC):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| S1 | `resonant_frequency(L, C)` | L: H; C: F | f_0 = 1/(2 pi sqrt(L C)) | Hz |
| S2 | `series_rlc_quality_factor(R, L, C)` | R: ohm; L: H; C: F | Q = (1/R) sqrt(L/C) | dimensionless |
| S3 | `series_rlc_bandwidth(R, L)` | R: ohm; L: H | half-power bandwidth in Hz: B = R/(2 pi L) | Hz |

RC filters (first-order):
| # | Function | Arguments | Formula | Result |
|---|---|---|---|---|
| F1 | `rc_lowpass_cutoff(R, C)` | R: ohm; C: F | f_c = 1/(2 pi R C) | Hz |
| F2 | `rc_lowpass_gain(f, R, C)` | f: Hz; R: ohm; C: F | \|H\| = 1/sqrt(1 + (2 pi f R C)^2) | dimensionless |
| F3 | `rc_highpass_gain(f, R, C)` | f: Hz; R: ohm; C: F | \|H\| = (2 pi f R C)/sqrt(1 + (2 pi f R C)^2) | dimensionless |

Phase 1 totals: 1A = 17 functions (R1-R4, M1-M2, P1-P4, D1-D4, X1-X3), 1B = 19 functions (C1-C9, T1-T4, S1-S3, F1-F3). Total 36, which is also the number of GUI buttons.

## Unit prerequisites (engine, phase 1A, small units.py change; developer-ready)
Needed for SI-labelled results. Existing units.py has V, A, ohm, F, H, Hz, W, s and the prefixed kV, mV, mA, kohm, Mohm, uF, nF, kHz, MHz, kW, ms.
1. Add `VA` (volt-ampere) and `var` (reactive volt-ampere) as power-dimension units, both SI-coherent (1 VA = 1 W numerically for dimension purposes; they are displayed by their own names). `P2` returns its result displayable as `= VA`; `P3` as `= var`; `P1` and `D4` as `= W`. Test that `= VA` and `= var` display the labels.
2. Add `mH`, `uH`, `nH` (henry prefixes) and `pF` (farad prefix), same pattern as existing `uF`/`nF`.
3. Do NOT add `S` (siemens) in phase 1; admittance is out of scope (Open question 5).
4. Do NOT add `j` in phase 1 (Open question 4). Complex values are built inside the functions.
5. Angular frequency `rad/s`: the engine's rad is dimensionless, so C9's result prints as `1/s`. Accepted for phase 1 (equal in value and dimension, labelled by the function's tooltip). Open question 6.

## Acceptance criteria (phase 1)

### Engine part (Qt-free, `livesheet/engine/electrical.py`, merged into the evaluator's builtins like spec 033)
Tolerances: 1e-6 relative unless stated. Tests use `Engine().evaluate(...)` with explicit display units (`= V`, `= kohm`, `= mH`, ...), because a bare `=` prints base SI and a bare power prints W. Hand-derived values; re-run required.

Registration and naming
1. All 36 names are callable in a math region and appear in the existing function-name autocomplete with their argument names (spec 024 mechanism, no change to the autocomplete code).
2. No name equals a `BUILTINS` key, a `UNITS` key or a `syntax.py` keyword (test by set intersection).
3. `electrical.py` imports no PySide6. `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" message, e.g. `rc_time_constant(1 kohm)`.

Unit and SI rules
5. Bare number in a dimensional slot: `voltage_divider(12, 1 kohm, 3 kohm)` gives `voltage_divider: Vin needs a unit of voltage, for example 1 V`.
6. Wrong dimension: `voltage_divider(12 V, 1 kohm, 3 A)` gives `voltage_divider: R2 must be a resistance, not A`.
7. Angle rule: `average_power(230 V, 10 A, 60 V)` gives `average_power: phi must be an angle in radians, not V`; `average_power(230 V, 10 A, pi/3) = W` gives 1150 W.
8. Turns rule: `transformer_secondary_voltage(230 V, 1000 A, 100)` gives `transformer_secondary_voltage: Np must be a plain number of turns, not A`.
9. Mixed compatible units accepted, result SI: `voltage_divider(12 V, 1 kohm, 3000 ohm) = V` gives 9 V; `voltage_divider(0.012 kV, 1000 ohm, 3 kohm) = V` gives 9 V.

AC power (1A)
10. `rms_from_peak(325 V) = V` gives 229.8097 V; `peak_from_rms(230 V) = V` gives 325.2691 V.
11. `average_power(230 V, 10 A, pi/3) = W` gives 1150 W; `apparent_power(230 V, 10 A) = VA` gives 2300 VA; `reactive_power(230 V, 10 A, pi/3) = var` gives 1991.858 var; `power_factor(pi/3)` gives 0.5.
12. Power triangle: `apparent_power(230 V, 10 A)^2` equals `average_power(...)^2 + reactive_power(...)^2` for the same inputs (tolerance 1e-9 relative).

Resistor networks (1A)
13. `resistors_series([10 ohm; 22 ohm; 33 ohm]) = ohm` gives 65 ohm; `resistors_parallel([10 ohm; 10 ohm]) = ohm` gives 5 ohm; `resistors_parallel([100 ohm; 200 ohm; 300 ohm]) = ohm` gives 54.54545 ohm.
14. `voltage_divider(12 V, 1 kohm, 3 kohm) = V` gives 9 V; `current_divider(10 mA, 1 kohm, 1 kohm) = mA` gives 5 mA.

Three-phase (1A)
15. `wye_line_voltage(230 V) = V` gives 398.3717 V; `wye_phase_voltage(400 V) = V` gives 230.9401 V; `delta_line_current(10 A) = A` gives 17.32051 A.
16. `three_phase_power(400 V, 10 A, pi/6) = W` gives 6000 W (tolerance 1e-6).

Transformers (1A)
17. `transformer_secondary_voltage(230 V, 1000, 100) = V` gives 23 V; `transformer_secondary_current(2 A, 1000, 100) = A` gives 20 A (power is conserved: 230 V x 2 A = 23 V x 20 A, i.e. 460 W both sides).
18. `reflected_impedance(8 ohm, 1000, 100) = ohm` gives 800 ohm.

Phasors and impedance (1B)
19. `phasor(10 V, pi/6)`: real part `= V` gives 8.660254 V and imaginary part gives 5 V (test via `re()`/`im()` of the result, which exist in the engine); `phasor_magnitude(phasor(10 V, pi/6)) = V` gives 10 V; `phasor_angle(phasor(10 V, pi/6))` gives pi/6 = 0.5235988 rad (tolerance 1e-9).
20. `impedance_inductor(50 Hz, 0.1 H)`: imaginary part `= ohm` gives 31.41593 ohm, real part 0. `impedance_capacitor(50 Hz, 100 uF)`: imaginary part gives -31.83099 ohm.
21. `impedance_series([10 ohm; impedance_inductor(50 Hz, 0.1 H)])` has magnitude 32.96908 ohm (`phasor_magnitude(...) = ohm`).
22. `impedance_parallel([10 ohm; 10 ohm]) = ohm` gives 5 ohm (real, zero imaginary part).
23. `angular_frequency(50 Hz)` gives 314.1593 (in 1/s = rad/s, tolerance 1e-6).

Transients (1B)
24. `rc_time_constant(1 kohm, 10 uF) = s` gives 0.01 s; `rl_time_constant(0.5 H, 10 ohm) = s` gives 0.05 s.
25. `rc_charge_voltage(12 V, 0.01 s, 1 kohm, 10 uF) = V` gives 7.585447 V (= 12(1 - e^-1)); `rl_current_rise(12 V, 0.05 s, 10 ohm, 0.5 H) = A` gives 0.7585447 A.

Resonance (1B)
26. `resonant_frequency(0.01 H, 10 uF) = Hz` gives 503.2921 Hz; `series_rlc_quality_factor(10 ohm, 0.01 H, 10 uF)` gives 3.162278.
27. `series_rlc_bandwidth(10 ohm, 0.01 H) = Hz` gives 159.1549 Hz. Consistency: resonant frequency / bandwidth = Q (503.2921/159.1549 = 3.162278, tolerance 1e-5).

Filters (1B)
28. `rc_lowpass_cutoff(1 kohm, 1 uF) = Hz` gives 159.1549 Hz; `rc_lowpass_gain(159.1549 Hz, 1 kohm, 1 uF)` gives 0.7071068 (tolerance 1e-5).
29. `rc_lowpass_gain(1591.549 Hz, 1 kohm, 1 uF)` gives 0.0995037 (= 1/sqrt(101), tolerance 1e-5).
30. `rc_highpass_gain(159.1549 Hz, 1 kohm, 1 uF)` gives 0.7071068 (equal to the low-pass value at cutoff).

Errors (no result, LiveSheet message, no traceback)
31. `impedance_capacitor(-50 Hz, 100 uF)` gives `impedance_capacitor: f must be greater than zero`.
32. `rc_charge_voltage(12 V, -1 ms, 1 kohm, 10 uF)` gives `rc_charge_voltage: t must not be negative`.
33. `resistors_parallel([-100 ohm; 200 ohm])` gives `resistors_parallel: R must be greater than zero`.
34. `impedance_parallel([])` gives `impedance_parallel: needs at least one impedance`.
35. Undefined name: with nothing defined, `rc_time_constant(R, C)` gives the existing `C, R are not defined` message.

Unit prerequisites (1A)
36. `apparent_power(230 V, 10 A) = VA` displays VA (label, not W); `reactive_power(...) = var` displays var; `mH`, `uH`, `nH`, `pF` parse as prefixed units (`1 mH = H` gives 0.001 H, `1 pF = F` gives 1e-12 F).

### GUI part (Electrical tab, separate section; same mechanism as spec 020 and spec 011)
GUI-1. The existing Electrical tab keeps its two existing groups (DC Circuits, Power, spec 020, unchanged) and gains new sub-headers, in this order: AC Power, Three-Phase, Transformers, Resistor Networks, Phasors & Impedance, Transients & Resonance, Filters. The tab stays one tab; no new tab; TAB_ORDER unchanged.
GUI-2. Exactly 36 new buttons, one per phase 1 function, with the label, inserted text and tooltip given in GUI-4. Each button calls the existing `insert_token(token)` callback. No new widget type, no dialog, no on-canvas editing.
GUI-3. Clicking the AC Power button "average_power" inserts `average_power(Vrms, Irms, phi)` at the cursor; clicking "phasor" inserts `phasor(mag, phi)`.
GUI-4. Button list (label | inserted text | tooltip, SI only; each tooltip states units of inputs and result):
- AC Power: "rms from peak" | `rms_from_peak(Vpk)` | V_rms from V_pk, V; "peak from RMS" | `peak_from_rms(Vrms)` | V_pk from V_rms, V; "average power" | `average_power(Vrms, Irms, phi)` | P in W from V_rms (V), I_rms (A), phi (rad); "apparent power" | `apparent_power(Vrms, Irms)` | S in VA; "reactive power" | `reactive_power(Vrms, Irms, phi)` | Q in var, positive for lagging; "power factor" | `power_factor(phi)` | cos(phi), dimensionless.
- Three-Phase: "wye line voltage" | `wye_line_voltage(Vph)` | V_L = sqrt(3) V_ph, V; "wye phase voltage" | `wye_phase_voltage(Vline)`; "delta line current" | `delta_line_current(Iph)`; "three-phase power" | `three_phase_power(VL, IL, phi)` | balanced, W.
- Transformers: "secondary voltage" | `transformer_secondary_voltage(Vp, Np, Ns)`; "secondary current" | `transformer_secondary_current(Ip, Np, Ns)`; "reflected impedance" | `reflected_impedance(Zs, Np, Ns)` | Np, Ns plain turn counts.
- Resistor Networks: "series resistance" | `resistors_series(R)`; "parallel resistance" | `resistors_parallel(R)`; "voltage divider" | `voltage_divider(Vin, R1, R2)`; "current divider" | `current_divider(Itot, R1, R2)`.
- Phasors & Impedance: "phasor" | `phasor(mag, phi)`; "phasor magnitude" | `phasor_magnitude(z)`; "phasor angle" | `phasor_angle(z)` | rad; "resistor impedance" | `impedance_resistor(R)`; "inductor impedance" | `impedance_inductor(f_hz, Lind)` | f in Hz, L in H; "capacitor impedance" | `impedance_capacitor(f_hz, Ccap)`; "series impedance" | `impedance_series(z)`; "parallel impedance" | `impedance_parallel(z)`; "angular frequency" | `angular_frequency(f_hz)` | rad/s.
- Transients & Resonance: "RC time constant" | `rc_time_constant(R, Ccap)`; "RL time constant" | `rl_time_constant(Lind, R)`; "RC charge voltage" | `rc_charge_voltage(Vs_step, t_s, R, Ccap)`; "RL current rise" | `rl_current_rise(Vs_step, t_s, R, Lind)`; "resonant frequency" | `resonant_frequency(Lind, Ccap)` | Hz; "series RLC Q" | `series_rlc_quality_factor(R, Lind, Ccap)`; "series RLC bandwidth" | `series_rlc_bandwidth(R, Lind)` | Hz.
- Filters: "RC low-pass cutoff" | `rc_lowpass_cutoff(R, Ccap)` | Hz; "RC low-pass gain" | `rc_lowpass_gain(f_hz, R, Ccap)`; "RC high-pass gain" | `rc_highpass_gain(f_hz, R, Ccap)`.
Placeholder names avoid bare unit letters (V, A, F, H, C, T, W, S, L, e), so an unfilled template gives "is not defined" instead of a silent unit (same landmine as spec 018). Names used: Vpk, Vrms, Irms, phi, Vph, Vline, Iph, VL, IL, Vp, Ip, Np, Ns, Zs, Vin, R1, R2, Itot, R, Lind, Ccap, f_hz, mag, z, Vs_step, t_s.
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change. No keyboard shortcut for the new buttons (click only, as in spec 020).
GUI-6. Regression: the existing DC Circuits and Power buttons (spec 020's 11 entries) are unchanged in label, text and order.

## Syntax proposal (own keywords)
None. Function calls only. No grammar change.

## Implementation placement (developer)
- `livesheet/engine/electrical.py` (new, Qt-free): `ELEC_BUILTINS` with the 36 names. Merged in `evaluator._builtins()` like spec 033's `MECH_BUILTINS`.
- `livesheet/engine/units.py`: the unit prerequisites only (VA, var, mH, uH, nH, pF).
- `livesheet/gui/sidepanel.py`: a new token list `_ELEC_FUNC_TOKENS` with the 36 (category, label, token, tooltip) tuples, appended to `MATH_TOKENS`, and the new category names added to `TAB_CATEGORIES["Electrical"]` after the existing two. TAB_ORDER unchanged.
- Tests: `tests/test_electrical.py` (developer); independent black-box `tests/test_electrical_blackbox.py` (tester, from this spec only); GUI button checks in the tester's file.

## Edge cases
- Phasor angle: values are radians; `pi/3` and `1.0471976` are equal; a plain number is radians by definition (no degree conversion).
- Angle range: `phasor_angle` returns (-pi, pi]; a phase of 3 pi/2 is returned as -pi/2.
- Power sign convention: reactive power is positive for lagging (inductive) loads and negative for leading (capacitive) loads. Stated in the tooltip and manual.
- Three-phase functions assume balanced loads and supply; unbalanced cases are out of scope and documented.
- Transformer functions assume an ideal transformer (no losses, no leakage, no magnetising current); they are not a model of a real transformer.
- Zero resistance, zero capacitance or zero inductance: rejected as "must be greater than zero" (LiveSheet's engine drops the unit of a zero with a unit, so tests use negative values for the error cases).
- Complex results: `impedance_series` may return a complex value; `= ohm` displays it as complex. The display of complex values with units is a tester check (criterion 19-21 use `re()`/`im()`/`abs()` where needed).
- Filter formulas use the first-order model only.
- Rounding: displayed values use the engine's 6-significant-digit formatting; tests use the tolerances above.

## IP check
Pass, pending manager review. Own function names, argument order, error wording and button labels. Formulas are generic textbook electrical relations (Ohm and divider laws, RMS, power triangle, three-phase relations, ideal transformer, RC/RL/RLC time constants and resonance, first-order RC filters), each confirmed on a fetched public Wikipedia summary listed in the research note (accessed 2026-11-12) or derived by standard algebra and stated as such. Subject-area nouns only from listing/catalogue search snippets; no vendor manual or catalogue page opened; no vendor menu, keyword, example or table used. No copied text (CC BY-SA sources used for facts only). No new UI type; buttons use the existing insertion mechanism of spec 011. Not legal advice; legal review before 1.0 is a standing item.

## Phases 2-6 (outline only, each needs its own spec)
Phase 2, digital logic (spec 035 candidate): `logic_and(a, b)`, `logic_or(a, b)`, `logic_not(a)` on 0/1 values or vectors; De Morgan identity check helper; truth table as a matrix. Dimensionless; no units.

Phase 3, operational amplifiers (spec 036 candidate): `opamp_inverting_gain(Rf, Rin) = -Rf/Rin`; `opamp_noninverting_gain(Rf, Rg) = 1 + Rf/Rg`; `opamp_output(Vin, gain, Vrail)` clipped to ±Vrail (saturation); summing amplifier with a vector of input resistors. Ideal-device assumptions stated in the manual.

Phase 4, semiconductors (spec 037 candidate): `thermal_voltage(T) = k T/q` with k and q from scipy.constants (CODATA, approved); `diode_current(V, Is, n, T) = Is (exp(V/(n V_T)) - 1)`; `diode_small_signal_resistance(I, n, T) = n V_T/I`. Temperature in kelvin only (no Celsius until backlog 6).

Phase 5, transmission lines and control (spec 038 candidate): lossless `characteristic_impedance(L_per_m, C_per_m) = sqrt(L'/C')` (H/m, F/m); `propagation_speed(L_per_m, C_per_m) = 1/sqrt(L' C')` (m/s); `reflection_coefficient(ZL, Z0) = (ZL - Z0)/(ZL + Z0)`; PID law on sampled error vectors (`pid_output(e, dt, Kp, Ki, Kd)`) with SI gains; first-order step response.

Phase 6, network analysis and machines (spec 039 candidate, sources to fetch first): star-delta conversion, two-port parameters, synchronous speed in rad/s from frequency and pole pairs (no rpm in the library, SI only).

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Degrees: phase 1 has no degree input or helper (radians only, per the SI rule). Does Theo want a `rad_from_deg` helper later, or is `pi/3` style enough? Recommendation: radians only; the existing non-SI `deg` template text (spec 011/018 statics `theta := 30*deg`) is a separate question for the manager (see Open question 8).
2. Display of SI-prefixed units (kV, mH, kohm, MHz): allowed as display units (SI prefixes) while results are stored in SI base form. Recommendation: yes. Confirm, because a strict reading would forbid displaying `= kohm`.
3. New power units: `VA` and `var` added to units.py as separate display names with power dimension (recommended, Theo listed them). Spelling `var` is lowercase and could collide with a variable name a user types; alternative symbol `VAr`. Recommendation: `var` as Theo listed it, with the bare-name collision noted.
4. Imaginary unit: keep `I` (the engine's existing constant) and build complex values inside functions (phase 1), or add `j` as an alias for users typing complex expressions (engineering convention; Wikipedia's impedance page uses j, because i is reserved for current). Recommendation: defer `j` until phase 2; phase 1 does not need it.
5. Admittance and siemens: phase 1 omits S (siemens) and admittance functions. Add `S` now or in phase 5? Recommendation: phase 5, with its own collision check (S is a short letter).
6. Angular frequency display: rad/s prints as 1/s (rad is dimensionless in the engine). Accept, or add a display-only name for rad/s? Recommendation: accept for phase 1; the tooltip says rad/s.
7. Phase size: 1A (17) and 1B (19) may ship as separate developer slices. Recommendation: yes, 1A first (needs the unit prerequisites), then 1B, then GUI-1.
8. Existing non-SI templates: the statics templates of spec 011/018 use `deg` (theta := 30*deg). Should they be changed to radians under the SI rule? That touches shipped code; not in spec 034. Recommendation: separate small follow-up, Theo decides.
9. Placeholder names in the buttons (Vpk, Vrms, Lind, Ccap, ...) are chosen to avoid unit letters. Accept, or prefer different names?

## Fits current architecture?
- `livesheet/engine/electrical.py` (new, Qt-free), merged like the other builtin groups.
- `livesheet/engine/units.py`: four added unit names for power and henry/farad prefixes (existing pattern).
- `livesheet/gui/sidepanel.py`: one extra token list and new sub-categories in the existing Electrical tab (spec 020's pattern).
- No `.lsheet` change, no new dependency (complex arithmetic and sqrt/exp come from SymPy, already approved). Phase 4 uses scipy.constants (already approved).

## Phase 1B implementation annotations (developer, 2026-11-13)
All 19 functions in `livesheet/engine/electrical.py`; every numeric criterion 19-30 re-checked against the live engine and plain math (all values agree within the stated tolerances). Discrepancies and engine quirks (meaning of the spec unchanged):
1. Criterion 20: "real part 0" cannot be tested as `re(impedance_inductor(...)) = ohm`; the engine drops the unit of a zero, so that gives "Units do not match: result is dimensionless". A bare `impedance_inductor(50 Hz, 0.1 H) =` prints `31.4159i Ω`; the imaginary part via `im(...) = ohm` works.
2. Criterion 19/23 tolerance 1e-9 for `phasor_angle` is not observable through `=` (6 significant digits displayed); verified at 1e-9 by calling the builtin directly. `angular_frequency(50 Hz) =` prints `314.159 s⁻¹` as spec'd; `= Hz` prints Hz (same dimension).
3. Criterion 34: `impedance_parallel([])` never reaches the function; the engine rejects the empty bracket first with "Empty matrix" (same for 1A `resistors_parallel([])`). The function's own "needs at least one impedance" message exists but is only reachable programmatically.
4. Criterion 35: `rc_time_constant(R, C)` with nothing defined gives "R is not defined", not "C, R are not defined", because `C` is the coulomb unit and so is never an undefined name. Same landmine as the placeholder note in GUI-4: `Ccap` avoids it.
5. Zero handling (not in spec): a time of `0 s` loses its unit in the engine, so `t` (nonneg) and impedance vector entries / `z` arguments accept a bare 0. `rc_charge_voltage(12 V, 0 s, ...) =` gives 0 (and `= V` fails, same defect as 034-1A-1). `impedance_parallel` with a zero entry gives "z must not contain a zero impedance"; `phasor_angle` of zero gives "z must not be zero".
6. Wording: a dimension error for inductance reads "L must be a inductance, not V" (shared template "must be a <dimension>"); cosmetic, same pattern as 1A.
7. `phasor(mag, phi)` accepts any unit (or none) for `mag` and keeps it; `phasor_magnitude(z)` keeps the unit of z (accepts kV, displays `= kV`). Argument names in hints and errors follow the spec table (f, L, C, Vs, t); GUI placeholder names (f_hz, Lind, Ccap) are a GUI-1 concern.
