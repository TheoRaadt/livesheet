# Electrical-engineering topic research (input to spec 034)

Author: mathcad-specialist. Date: 2026-11-12. Status: research note, NOT a spec, NOT IP-reviewed by the manager.
Request (coordinator, relaying Theo, 2026-11-12): learn the subject areas of the electrical application package
of the same commercial product family as the mechanical pack (spec 033), then add sensible subject matter to
LiveSheet's electrical area, clean-room only, and keep everything SI (Theo, 2026-11-12: all inputs accept any
compatible unit, results always SI, no imperial/US customary units anywhere).

## 1. What I used, and what I deliberately did not

### 1a. Product description (subject-area nouns only)
- Used: search-result snippets of listing and catalogue-style pages for the product. They name generic subject
  areas: circuit elements, simple AC and DC circuits, RL/RC/RLC circuits, resonance, transformers, transmission
  lines, motors and generators, network analysis (star-delta transforms, ladder networks), two-port networks.
  Only these generic nouns were taken. No listing or catalogue page was opened.
  Search-result pages seen (not opened): https://www.ebay.com/itm/202649208525 (a manual listed for sale),
  http://cd.textfiles.com/blackphiles/PHILES/HP48_2/48ACS.TXT (a 1992 software catalogue; only its snippet
  appeared). Caveat for the manager: the 1992 catalogue is a vendor-era catalogue page. Only generic nouns were
  taken from its snippet, but the manager may prefer that page be recorded as "seen, not used" to keep the
  source trail clean.
- Also seen in snippets (not opened): equation counts and a "reference pac" of constants. Not used; constants are
  already backlog 8a(ii).

### 1b. Deliberately NOT used
- The vendor's owner's manuals for this pack and its siblings, including any manual hosted on a third-party
  archive. Not opened, read, skimmed or quoted (ip-cleanroom rule 7; docs/board/decisions.md 2026-11-12).
- Any vendor menu, screen layout, keyword or command name, example problem, help text, numbering, ordering or
  equation table.
- The product's own grouping. The outline in section 3 is LiveSheet's own taxonomy.

## 2. Public sources (accessed 2026-11-12)
All Wikipedia articles, licence CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Facts only (the
formulas and what each symbol means); no sentence or table copied.

| Topic | URL | Confirmed |
|---|---|---|
| Electrical impedance | https://en.wikipedia.org/wiki/Electrical_impedance | Z_R = R, Z_L = j w L, Z_C = 1/(j w C); series adds; parallel reciprocals add; j is the imaginary unit (i reserved for current) |
| Phasor | https://en.wikipedia.org/wiki/Phasor | Phasor = complex amplitude; polar A at angle theta and rectangular A cos theta + j A sin theta (Euler's formula) |
| Power factor | https://en.wikipedia.org/wiki/Power_factor | Real power P = |S| cos theta; apparent S = Vrms Irms (volt-ampere, VA); reactive in var; |S|^2 = P^2 + Q^2; power factor = P/|S| = cos theta |
| Root mean square | https://en.wikipedia.org/wiki/Root_mean_square | RMS of a sinusoid = peak / sqrt(2) |
| RLC circuit | https://en.wikipedia.org/wiki/RLC_circuit | Series resonance w0 = 1/sqrt(LC); Q = (1/R) sqrt(L/C); bandwidth delta-w = R/L (series) |
| RC circuit | https://en.wikipedia.org/wiki/RC_circuit | Capacitor charging/discharging exponential, time constant tau = RC |
| RL circuit | https://en.wikipedia.org/wiki/RL_circuit | Time constant tau = L/R; resistor voltage after a step V(1 - e^(-t/tau)) |
| Low-pass filter | https://en.wikipedia.org/wiki/Low-pass_filter | RC cutoff f_c = 1/(2 pi R C); -3 dB at cutoff; first-order roll-off about 20 dB per decade |
| Three-phase electric power | https://en.wikipedia.org/wiki/Three-phase_electric_power | Line-to-line voltage = sqrt(3) x line-to-neutral (wye); delta line current = sqrt(3) x phase current; S = 3 V_phase I_phase |
| Transformer | https://en.wikipedia.org/wiki/Transformer | V_p/V_s = N_p/N_s; I_s/I_p = N_p/N_s (ideal); load impedance referred to primary = turns ratio squared times secondary impedance |
| Operational amplifier applications | https://en.wikipedia.org/wiki/Operational_amplifier_applications | Inverting gain -Rf/Rin; non-inverting gain 1 + Rf/Rg; ideal assumptions (large gain, large input impedance) |
| Shockley diode equation | https://en.wikipedia.org/wiki/Shockley_diode_equation | I = I_S (exp(V/(n V_T)) - 1); V_T = kT/q; ideality factor n |
| Transmission line | https://en.wikipedia.org/wiki/Transmission_line | Lossy characteristic impedance sqrt((R + j w L)/(G + j w C)) (square root lost in the page text); lossless propagation speed 1/sqrt(LC); load reflection coefficient (Z_L - Z0)/(Z_L + Z0) |
| PID controller | https://en.wikipedia.org/wiki/PID_controller | u = Kp e + Ki integral(e) + Kd de/dt |
| Boolean algebra | https://en.wikipedia.org/wiki/Boolean_algebra | AND, OR, NOT; De Morgan laws |

Derived in this note (not a page statement, from the confirmed relations above): high-pass RC gain
|H| = w R C / sqrt(1 + (w R C)^2) (divider across R with Z_C = 1/(j w C)); low-pass RC gain
|H| = 1/sqrt(1 + (w R C)^2); balanced three-phase real power P = sqrt(3) V_L I_L cos(theta) (from S = 3 V_ph I_ph
with V_L = sqrt(3) V_ph and I_L = I_ph for wye). Both derivations are standard textbook algebra; the
manager/tester should check them numerically (spec 034 criteria do).

Not fetched (outline phases only): motor synchronous speed, two-port parameters, star-delta transform formulas,
MOSFET/BJT small-signal models, Bode plots, state-space control. Each needs a source fetch before its spec.

## 3. Subject-area outline (LiveSheet's own taxonomy, generic topics)
1. Resistive networks: series and parallel resistance, voltage and current dividers (already templates in the
   Electrical tab's DC Circuits group, spec 020).
2. AC power: RMS and peak, real/apparent/reactive power, power factor.
3. Phasors and impedance: complex phasors, impedance of R/L/C, series and parallel impedance, angular frequency.
4. Transients: RC and RL time constants and step responses.
5. Resonance and filters: series RLC resonance, quality factor, bandwidth; first-order RC low-pass and high-pass.
6. Three-phase: wye/delta line-to-phase relations, balanced three-phase power.
7. Transformers: ideal turns ratio, current ratio, impedance referral.
8. Digital logic (later): AND/OR/NOT, De Morgan, truth tables as vectors.
9. Operational amplifiers (later): ideal inverting and non-inverting gain, summing amplifier.
10. Semiconductors (later): Shockley diode equation (constants from scipy.constants).
11. Transmission lines (later): characteristic impedance, propagation speed, reflection coefficient.
12. Control basics (later): PID law on sampled error vectors, first-order step response.
13. Network analysis and two-port networks, motors and generators (later; need fetched sources).

Overlaps with what LiveSheet already has: DC circuits and power templates (spec 020, shipped, Electrical tab),
complex numbers in the engine (matrices and formatting handle complex values; `I` is the imaginary unit),
statistics (017), ODE (010) for transients if numeric later.

## 4. Unit gaps found in the current engine (checked 2026-11-12 in livesheet/engine/units.py and evaluator.py)
- Present and usable: V, mV, kV, A, mA, kA, ohm, Ω, kohm, kΩ, Mohm, MΩ, F, uF, μF, nF, H, Hz, kHz, MHz, GHz, W, kW,
  MW, GW, s, ms, C, T, Wb, rad (= 1, dimensionless), deg (= pi/180, dimensionless, non-SI; not used by this spec).
- Missing: volt-ampere (VA), reactive volt-ampere (var): both needed for SI-labelled power results. Siemens (S)
  missing. Millihenry (mH), microhenry (uH), nanohenry (nH), picofarad (pF) missing (SI-prefixed; should be
  added). Angular frequency unit rad/s displays as 1/s because rad is dimensionless in the engine.
- Imaginary unit: only `I` (sp.I) exists; the engineering `j` is not defined. Not needed by the phase 1 functions
  (they build complex values internally); a decision is needed before users type complex expressions.
- Angles: rad and deg are both dimensionless in the engine, so a dimension check cannot tell an angle from a
  plain number. Phase 1 therefore treats an angle argument as radians, uses `pi/3`-style values, and rejects only
  values that carry a non-angle unit.
- Bare unit letters that collide with names a user might type: V, A, F, H, C, T, W, S, L (liter, if defined),
  e (Euler's number). Templates and tests avoid these as variable names (same landmine as spec 018).
- Existing shipped templates use `deg` (spec 011/018 statics: `theta := 30*deg`). Non-SI but accepted by the
  engine. Flagged to the manager; not changed by spec 034.

## 5. IP statement
What I did:
- Took generic subject-area nouns from search-result snippets of listing/catalogue pages (section 1a).
- Read public Wikipedia articles (CC BY-SA 4.0) and used only the formulas and symbol meanings they state, plus
  standard textbook derivations listed in section 2. No text copied.
- Chose LiveSheet's own taxonomy, function names, argument order, error wording and button labels.

What I did NOT do:
- Did not open or quote any vendor manual, catalogue page, or example worksheet, including manuals hosted on
  third-party archives (ip-cleanroom rule 7).
- Did not use any vendor menu, layout, keyword or command, example problem, equation table, numbering or ordering.

Residual risks: the 1992 catalogue snippet (section 1a) is from a vendor-era document; nouns only. Wikipedia CC BY-SA
(facts only). Not legal advice; standing legal review before 1.0.

## 6. Verification status
- Formulas checked against fetched Wikipedia summaries; some pages were partial (noted per row) and the
  remaining formulas were derived by hand.
- Numeric examples in spec 034 were hand-derived (no Bash in this session); the manager or tester must run them
  against the engine before the developer relies on them.
