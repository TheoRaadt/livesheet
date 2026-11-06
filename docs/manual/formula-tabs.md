# Formula tabs: Mechanical, Electrical, Chemical

Three tabs in the tab strip hold ready-made formulas for common engineering calculations. One
click puts the formula on your sheet; you then give its names your own values. This page covers
the tabs, how to use them, the SI-only rule, and a trap to watch for with unit names. For the
strip and button band themselves, see [The main window](main-window.md).

## The tabs

The tab strip sits under the toolbar; if it is hidden, show it with **View > Side Panel**. The full tab order is: Elements, Algebra,
Calculus, Statistics, Optimization, **Mechanical**, **Electrical**, **Chemical**, Outline, Data.

Each formula tab groups its buttons under small grey headings:

| Tab | Headings (buttons) | Total |
|---|---|---|
| Mechanical | Statics (6), Strength of Materials (9) | 15 |
| Electrical | DC Circuits (7), Power (4) | 11 |
| Chemical | Stoichiometry & Composition (4), Ideal Gas & Thermodynamic State (5), Mass & Energy Balances (4), Fluid & Heat/Mass Transport (4), Reaction Kinetics (4) | 21 |

Hover over a button to see its tooltip. The tooltip names the formula, says what each symbol
means, and gives the SI unit each symbol is expected to have (for example "P in N; d in m").

### Mechanical

Statics: Resultant (2 forces), Force x-component, Force y-component, Moment of a force, Static
friction limit, Centroid of 2 point masses.

Strength of Materials: Axial (normal) stress, Normal strain, Hooke's law (axial), Axial elongation,
Bending stress, Transverse shear stress, Average shear stress, Linear thermal expansion, Factor of
safety.

### Electrical

DC Circuits: Ohm's law in its three forms, resistors in series, resistors in parallel, voltage
divider, current divider. Power: power from voltage and current, from current and resistance, from
voltage and resistance, and energy from power and time. On these buttons the label is exactly the
text that gets inserted (for example `Vs := Is * R`).

### Chemical

Stoichiometry & Composition: amount of substance, mass fraction, mole fraction, molar
concentration. Ideal Gas & Thermodynamic State: gas constant `R`, ideal gas law `PV=nRT`, gas
density `rho_gas`, sensible heat `Q_sens`, latent heat `Q_lat`. Mass & Energy Balances: `m-dot
bal.`, `comp. bal.`, `dm/dt`, `energy bal.`. Fluid & Heat/Mass Transport: `Re`, `Q_cond`, `Q_conv`,
`J_diff`. Reaction Kinetics: `rate law`, `Arrhenius`, `half-life`, `conversion`.

## Inserting a formula

1. Click in the sheet where you want the formula, or leave nothing selected.
2. Click the button in the tab. If you were not editing a math region, LiveSheet creates one; the
   formula text is inserted at the cursor.
3. The text is an ordinary definition such as `sigma := P/Ac`. It has no numbers or units in it.
4. Define the names it uses (see below), above or to the left of the formula.

Clicking a button never changes anything else on the sheet. You can click the same button twice,
but then two lines define the same name; the later one wins, as with any definition you type by
hand.

## Filling in the names

The inserted formula uses placeholder names such as `P`, `Ac`, `sigma`. Define each one it needs
in its own region, with a number and an SI unit:

```
P := 1000 N
Ac := 50 mm^2
sigma := P/Ac
sigma = MPa
```

The last line shows `= 20 MPa`.

To use your own names instead, edit the text of the inserted region: click into it and retype the
name, on both sides of any place it appears. For example change `sigma := P/Ac` to
`stress := Load/Area`, then define `Load` and `Area`. If you rename a name that other lines use,
rename it there too.

If you leave a name undefined, LiveSheet tells you. A template inserted alone on a fresh sheet and
followed by `sigma =` shows `Ac, P are not defined`. (On the Electrical tab, if neither `Is` nor
`R` is defined, the message is `Is, R are not defined`.)

## SI units only

The formulas, the tooltips and the examples on these tabs all use SI units (N, m, Pa, kg, s, K,
mol, J, W, V, A, ohm and prefixed forms such as MPa, kJ, mm). Nothing on these tabs uses pounds,
feet, psi or similar.

This is a rule about what the tabs offer, not a restriction on you. The inserted formula carries no
units, so LiveSheet would accept other units you attach to your values. If you mix units that
cannot be combined, you get the usual `Units do not match` message (see [Error
messages](errors.md)). The Chemical tab's `R` button is the only one that contains a number: it
inserts `R_gas := 8.314 J/(mol*K)`.

## Showing the result in the unit you want

A bare `name =` shows the result in base SI units, which is sometimes not what you expect. To get a
specific unit, end the line with `= unit`. These forms are the reliable ones:

| You write | You see |
|---|---|
| `Q_sens =` | `= 1.2558x10^6 J` (shown with a power of ten) |
| `Q_sens = kJ` | `= 1255.8 kJ` |
| `Q_rate =` | `= 400000 W` |
| `Q_rate = kW` | `= 400 kW` |
| `M =` | `= 30 J` |
| `M = N*m` | `= 30 N*m` |
| `sigma = MPa` | for example `= 20 MPa` (a bare `sigma =` shows `= 2x10^7 Pa`) |

The `M = N*m` note matters: a moment of force and energy have the same base dimension, so a bare
`M =` shows `J` (joules). The result is correct; ask for `N*m` explicitly to see moment-style units.
The Moment of a force button's tooltip says the same.

## Worked examples

Mechanical, axial elongation (`dL := P*L0/(Ac*E)`):

```
P := 5000 N
L0 := 2 m
Ac := 100 mm^2
E := 200 GPa
dL := P*L0/(Ac*E)
dL = mm
```

Result: `= 0.5 mm`.

Electrical, parallel resistors (`R_total := 1 / (1/R1 + 1/R2)`):

```
R1 := 100 ohm
R2 := 100 ohm
R_total := 1 / (1/R1 + 1/R2)
R_total =
```

Result: `= 50 ohm` (shown with the ohm symbol).

Chemical, ideal gas law (`P_gas := n_gas * R_gas * T_gas / V_gas`):

```
R_gas := 8.314 J/(mol*K)
n_gas := 2 mol
T_gas := 300 K
V_gas := 0.05 m^3
P_gas := n_gas * R_gas * T_gas / V_gas
P_gas =
```

Result: about `99768 Pa`.

## Names that look like units

Some single letters are also units: `F` (farad), `A` (ampere), `V` (volt), `N` (newton), `W`
(watt), `T` (tesla), `C`, `H`, `L`, `J`, `K`, and `I` (the imaginary unit). That is why the tab
formulas use names like `P`, `Ac`, `Fv`, `Ix`, `Fn`, `Vs`, `Is` instead of the textbook `F`, `A`,
`V`, `I`, `N`. If you rename a placeholder to one of these single letters, read the section on
unit names below first.

## Unit names on their own

A bare unit name that you have not defined is now reported as undefined. For example, if you write

```
sigma := F/A
```

without defining `F` and `A` first, you see `F is not defined`, instead of a quietly meaningless
number (LiveSheet used to read them as the farad and the ampere). See the matching rows in [Error
messages](errors.md).

### The message wording

The message `F is not defined` is worded for the usual case, a variable you forgot. If you really
meant `F` as the unit farad, the message is misleading. The fix is the same: write a number in
front of the unit, such as `5 F`.

### What stops working

The check treats an expression that has no digit and only untouched unit names as a forgotten
variable, because `F/A` (two forgotten variables) and `m/s` (a unit) look the same. So these no
longer work:

- Unit aliases: `u := m/s`, `dist := m`, `kph := km/hr`. Instead, write the unit with a number,
  for example `u := 1 m/s`. Then `5*u` is a speed of 5 m/s.
- Bare conversions: `m = mm`, `kN = N`. Instead write the quantity: `1 m = mm` shows `= 1000 mm`.
- `g =`: the name `g` is standard gravity, not grams. See below.
- A matrix made only of bare unit names, such as `z := [N m]`. Put a number with each unit.

Unit names you have defined yourself are fine (`F := 10 N` then `F/A` uses your `F`), and anything
with a number in it is fine (`5 N`, `3 m/s`, `2*N`).

### `g` is standard gravity; grams are `gm`

In LiveSheet `g` is a unit, standard gravity (9.80665 m/s^2), not grams. Grams are written `gm`.
This matters for molar masses on the Chemical tab: `M_A := 28.97 g/mol` silently means an
acceleration per mole, not a mass per mole. Write `28.97 gm/mol` (or `0.02897 kg/mol`).

### Cases that are still not caught

The check is deliberately narrow. These are not reported, and still give a number computed from
the unit values:

- `m^2` on its own.
- Expressions mixing your own names with unit names: if `P` is defined but `A` is not, `P/A` is
  not reported (`A` is read as the ampere).
- Any expression that contains a digit, such as `F^2/A` or `2*F/A`.
- Unit names inside function calls, such as `sqrt(F/A)`, and inside function definitions.
- Expressions that also use the built-in constants `e`, `pi` or `I`.
- Symbolic results (`->`).

So the safest habit is to define every name in a formula before using it, and to avoid single-letter
names that are also units.
