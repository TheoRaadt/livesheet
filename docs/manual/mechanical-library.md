# Mechanical engineering functions

LiveSheet has 28 ready-made functions for the mechanics of materials: properties of simple cross
sections, beam deflection and maximum bending moment, stress and strain, and Euler column
buckling. You call them like any function in a math region, for example
`cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4)`. They appear in the autocomplete list with
their argument names (see [Autocomplete](autocomplete.md)).

## The rules every function follows

- **Arguments are written in the order shown below**, separated by commas, with no names.
- **Units are strict.** An argument that is a length, force, pressure and so on must carry a unit of
  that kind: `rect_area(50, 100 mm)` is an error, not "50 metres". Any unit of the right kind works
  and can be mixed: `0.04 m` and `30 mm` in the same call is fine.
- **Dimensionless arguments (such as the column factor `K`) must not carry a unit.** Write `K` as a
  plain number.
- **Lengths, areas, moduli and thicknesses must be greater than zero.** Loads, moments and the
  distance `c` in `bending_stress` may be zero or negative. Because a zero with a unit loses its
  unit on a LiveSheet sheet, a literal `0 m` is reported as needing a unit.
- **Results are SI.** A bare `=` prints base SI units (metres, not millimetres; a moment shows as
  `J`). Ask for another unit of the same kind after the `=`: `= mm`, `= kN`, `= MPa`, `= N*m`.
- No function in this library takes an angle.

## Cross-section properties

All about the centroidal axis of the shape. `b` is the width and `h` the height; `d` is a diameter;
`do` and `di` are the outer and inner diameter of a ring (`do` must be larger than `di`).

| Function | Gives |
|---|---|
| `rect_area(b, h)` | area, b h |
| `rect_inertia(b, h)` | second moment of area, b h^3 / 12 |
| `rect_section_modulus(b, h)` | section modulus, b h^2 / 6 |
| `circle_area(d)` | area of a solid circle |
| `circle_inertia(d)` | second moment of area, pi d^4 / 64 |
| `circle_polar_inertia(d)` | polar second moment, pi d^4 / 32 |
| `circle_section_modulus(d)` | section modulus, pi d^3 / 32 |
| `ring_area(do, di)` | area of a hollow circle |
| `ring_inertia(do, di)` | second moment of area of a hollow circle |
| `ring_section_modulus(do, di)` | section modulus of a hollow circle |
| `radius_of_gyration(I, A)` | square root of I / A |

Example: `ring_inertia(40 mm, 30 mm) = mm^4` gives `85902.9 mm^4`.

## Beams

Prismatic, linear-elastic beams with small deflection and a single load. `P` is a point force, `w`
a force per length, `L` the span, `E` the elastic modulus and `I` the second moment of area.

| Function | Gives |
|---|---|
| `cantilever_tip_deflection(P, L, E, I)` | deflection under a load at the free end, P L^3 / (3 E I) |
| `cantilever_udl_deflection(w, L, E, I)` | deflection under a uniform load, w L^4 / (8 E I) |
| `simply_supported_center_deflection(P, L, E, I)` | deflection under a midspan load, P L^3 / (48 E I) |
| `simply_supported_udl_deflection(w, L, E, I)` | deflection under a uniform load, 5 w L^4 / (384 E I) |
| `cantilever_tip_max_moment(P, L)` | P L at the fixed end |
| `cantilever_udl_max_moment(w, L)` | w L^2 / 2 at the fixed end |
| `simply_supported_center_max_moment(P, L)` | P L / 4 at midspan |
| `simply_supported_udl_max_moment(w, L)` | w L^2 / 8 at midspan |

Example: `cantilever_tip_deflection(1 kN, 2 m, 200 GPa, 1e-6 m^4) = mm` gives `13.3333 mm`.
Use `= N*m` for the moments: `simply_supported_udl_max_moment(2 kN/m, 2 m) = N*m` gives
`1000 N*m` (a bare `=` would print `J`).

## Stress and strain

| Function | Gives |
|---|---|
| `axial_stress(F, A)` | F / A |
| `axial_strain(dL, L)` | dL / L (no unit) |
| `axial_elongation(F, L, A, E)` | F L / (A E) |
| `bending_stress(M, c, I)` | M c / I, with `c` the distance from the neutral axis |
| `hoop_stress(p, r, t)` | p r / t in a thin-walled cylinder; `p` is gauge pressure, `r` the inner radius, `t` the wall |
| `longitudinal_stress(p, r, t)` | p r / (2 t), the same cylinder |

The hoop and longitudinal formulas assume a thin wall (a radius of about ten times the wall or
more); LiveSheet does not warn when the wall is thicker. Example:
`hoop_stress(2 MPa, 500 mm, 10 mm) = MPa` gives `100 MPa`.

## Columns

| Function | Gives |
|---|---|
| `euler_critical_load(E, I, L, K)` | pi^2 E I / (K L)^2; `K` is the effective-length factor, a plain number |
| `slenderness_ratio(L, K, r)` | K L / r (no unit) |
| `euler_transition_slenderness(E, sy)` | the slenderness above which the Euler formula applies; `sy` is the yield strength |

`euler_critical_load` always returns the Euler value, even for a stocky column below the transition
slenderness, so compare with `euler_transition_slenderness` yourself. Example:
`euler_critical_load(200 GPa, 1e-6 m^4, 2 m, 1) = kN` gives `493.48 kN`.

## Using them in your own functions

They work inside your own definitions: after `f(x) := rect_area(x, 100 mm)`, `f(50 mm) = m^2` gives
`0.005 m^2`.

## If something goes wrong

See [Mechanical engineering functions in the error reference](errors.md#mechanical-engineering-functions).
