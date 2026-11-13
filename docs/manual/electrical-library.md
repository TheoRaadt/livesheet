# Electrical engineering functions

LiveSheet has 17 ready-made functions for resistor networks, RMS and peak values, AC power,
balanced three-phase systems and ideal transformers. You call them like any function in a math
region, for example `average_power(230 V, 10 A, pi/3) = W`. They appear in the autocomplete list
with their argument names (see [Autocomplete](autocomplete.md)).

## The rules every function follows

- **Units are strict.** Voltages, currents and resistances must carry a unit of that kind; a bare
  number such as `voltage_divider(12, ...)` is an error. Any prefixed form works (`1 kohm`,
  `0.012 kV`, `10 mA`) and units can be mixed.
- **Angles are in radians.** Write a plain number or a `pi` expression: `pi/3`, `0.5`, `1 rad`. A
  number written with the `deg` unit is converted for you (`power_factor(60 deg)` is 0.5). Any
  other unit on an angle is an error.
- **Numbers of turns** (transformers) are plain positive numbers, no unit.
- **Resistances, RMS and peak voltages and currents, and turns must be greater than zero.** The
  source values `Vin`, `Itot`, `Vp` and `Ip` and the angles may be zero or negative.
- **Results are SI.** Power results are in watts: a bare `=` prints `W`. Ask for `VA` for apparent
  power and `var` for reactive power by writing `= VA` or `= var`; they are labels for the same
  quantity as watts, so LiveSheet accepts either label on any power value.
- The functions assume sinusoidal steady state, balanced three-phase loads and an ideal
  transformer. They never use the names `E`, `I`, `L` or `g` for their own arguments, so your own
  definitions with those names work normally.

## Resistor networks

| Function | Gives |
|---|---|
| `resistors_series(R)` | the total of a list of resistances |
| `resistors_parallel(R)` | the combined resistance of a list in parallel |
| `voltage_divider(Vin, R1, R2)` | the voltage across `R2` |
| `current_divider(Itot, R1, R2)` | the current through `R1` |

A list is written with commas or semicolons: `[10 ohm, 22 ohm, 33 ohm]` or
`[10 ohm; 22 ohm; 33 ohm]`. Do not separate the entries with spaces only (`[10 ohm 22 ohm]`): that
reads as one product and gives a confusing message. A single resistance is also accepted.

Examples: `resistors_series([10 ohm; 22 ohm; 33 ohm]) = ohm` gives `65 ohm`;
`resistors_parallel([100 ohm; 200 ohm; 300 ohm]) = ohm` gives `54.5455 ohm`;
`voltage_divider(12 V, 1 kohm, 3 kohm) = V` gives `9 V`.

## RMS and peak

| Function | Gives |
|---|---|
| `rms_from_peak(Vpk)` | the peak divided by the square root of 2 |
| `peak_from_rms(Vrms)` | the RMS value times the square root of 2 |

Example: `peak_from_rms(230 V) = V` gives `325.269 V`.

## AC power

| Function | Gives |
|---|---|
| `average_power(Vrms, Irms, phi)` | real power, Vrms Irms cos(phi) |
| `apparent_power(Vrms, Irms)` | Vrms Irms |
| `reactive_power(Vrms, Irms, phi)` | Vrms Irms sin(phi); positive for an inductive load |
| `power_factor(phi)` | cos(phi), a plain number |

Example: with a 60 degree phase angle (`pi/3`), `average_power(230 V, 10 A, pi/3) = W` gives
`1150 W`, `apparent_power(230 V, 10 A) = VA` gives `2300 VA`, and
`reactive_power(230 V, 10 A, pi/3) = var` gives `1991.86 var`.

## Balanced three-phase

| Function | Gives |
|---|---|
| `wye_line_voltage(Vph)` | line voltage from the phase voltage |
| `wye_phase_voltage(Vline)` | phase voltage from the line voltage |
| `delta_line_current(Iph)` | line current from the phase current of a delta load |
| `three_phase_power(VL, IL, phi)` | the square root of 3 times VL IL cos(phi) |

Example: `three_phase_power(400 V, 10 A, pi/6) = W` gives `6000 W`.

## Ideal transformer

| Function | Gives |
|---|---|
| `transformer_secondary_voltage(Vp, Np, Ns)` | Vp Ns / Np |
| `transformer_secondary_current(Ip, Np, Ns)` | Ip Np / Ns |
| `reflected_impedance(Zs, Np, Ns)` | Zs (Np / Ns)^2, seen from the primary |

Example: `transformer_secondary_voltage(230 V, 1000, 100) = V` gives `23 V`.

## New units

These units are new: `mH`, `uH` and `nH` (inductance), `pF` (capacitance), and `VA` and `var`
(power labels). For example `1 mH = H` gives `0.001 H`. `kVA` and `kvar` do not exist yet; write
`1.5 kW` or use `= VA` on the value instead.

## Zero results and zero arguments

- **A zero result loses its unit.** When a power comes out as exactly zero, for instance an ideal
  resistive load at `reactive_power(230 V, 10 A, 0)`, or `average_power(230 V, 10 A, pi/2)`, asking
  for a unit with `= W` or `= var` fails with `Units do not match: result is dimensionless`. Write
  a bare `=` instead, which shows `= 0`.
- **`0 ohm` is rejected as an argument.** Zero is never a valid resistance here, and LiveSheet
  drops the unit of a literal zero, so you get `R1 needs a unit of resistance, for example 1 ohm`.
  Use a small positive resistance instead.

## If something goes wrong

See [Electrical engineering functions in the error reference](errors.md#electrical-engineering-functions).
