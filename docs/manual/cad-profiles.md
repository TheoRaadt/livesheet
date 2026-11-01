# CAD profile import (DXF)

If you've drawn a cross-section — a steel angle, a tube, a custom bracket — in a CAD program and
saved it as a `.dxf` file, you can pull its shape straight into LiveSheet and get its area,
centroid, and bending properties as ordinary numbers, instead of measuring the drawing by hand or
retyping coordinates. This uses the same component/wiring mechanism as
[Components and wiring](components.md): a "CAD profile (DXF)" component reads the file and exposes
its numbers as output ports you can wire into any other component.

## Adding a CAD profile component

1. Choose **Insert > Component…**.
2. Set **Kind** to **CAD profile (DXF)**.
3. Fill in the three fields on that page:
   - **Path:** the `.dxf` file. Click **Browse…** to pick it with the normal file picker, or type
     the path directly.
   - **Layer (optional):** leave blank to look at every layer in the file, or type an exact layer
     name to only look at entities on that layer.
   - **Unit (optional):** leave blank to use the length unit the file itself declares (see "Picking
     the unit" below), or type one of LiveSheet's own length units (`mm`, `cm`, `m`, `km`, `um`,
     `nm`, `inch`, `ft`, `yd`, `mi`) to override it.
4. Give it a **Name:** and click **OK**.

A CAD profile component has no input ports — like "Value", it's a pure source. Its outputs
recompute every time the sheet recalculates, by re-reading the file fresh, so if you edit the
drawing in your CAD program and save it again, the numbers on the sheet update the next time
LiveSheet recalculates.

## What geometry it can read

LiveSheet looks at the entities in the file (after the **Layer** filter, if any) and tries to find
one or more **closed loops** — shapes with no gaps — to compute properties from:

- **A single closed polyline** (a `LWPOLYLINE` or `POLYLINE` entity marked closed). Its straight
  segments are used as-is.
- **Curved segments inside that same polyline** ("bulge" segments — a segment that's actually an
  arc instead of a straight line). These are flattened into a series of short straight segments
  before the area/centroid/moment math runs, in steps of at most 10 degrees of arc per segment.
  That's a small, fixed, and always-the-same rule — it isn't something you configure — and it
  means a curved outline's computed area is very slightly smaller than the true, perfectly smooth
  shape's area (well under 1% off for any reasonably sized arc). A full circle, for example,
  comes out as a 36-sided polygon rather than a mathematically perfect circle.
- **A standalone `CIRCLE` entity**, tessellated the same way (also a 36-gon).
- **A standalone `ARC` entity**, but only if it's a full circle in disguise (its start and end
  angle are the same) — a true partial arc, left open, can't make a closed loop by itself and is
  reported as unsupported (see Errors below).
- **Several separate `LINE` entities that chain end-to-end into one closed loop.** LiveSheet walks
  every `LINE` on the filtered set, matching up endpoints that touch, and if they form exactly one
  simple closed ring (no gaps, no branches, no leftover loose ends), that's your profile.

If more than one closed loop turns up on the same filtered set — say, an outer boundary plus one
or more holes, like a tube's wall or a box beam's cross-section — LiveSheet treats it as a single
**composite** section (see "Single profiles vs. composite sections" below) rather than rejecting it
as ambiguous.

## Picking the unit

If you leave **Unit** blank, LiveSheet reads the length unit straight out of the file's own header
(the `$INSUNITS` setting most CAD programs write):

| The file's unit setting means... | LiveSheet uses |
|---|---|
| inch | `inch` |
| feet | `ft` |
| mile | `mi` |
| millimetre | `mm` |
| centimetre | `cm` |
| metre | `m` |
| kilometre | `km` |
| yard | `yd` |
| anything else, or missing | *(no automatic unit — set **Unit** yourself)* |

If the file doesn't say, or says something LiveSheet doesn't recognise as a length (unitless,
micro-inches, mils), you have to type a unit into the **Unit** field yourself — LiveSheet never
silently guesses one.

## Reading the outputs

A CAD profile component always has these output ports, every one an ordinary unit-bearing number
(or, for `outline`, a matrix) you can wire anywhere a number is expected:

| Port | What it is |
|---|---|
| `area` | The total enclosed area (for a composite section, the outer area minus every hole). |
| `centroid_x`, `centroid_y` | The position of the centroid, in the drawing's own coordinate system. |
| `Ixx`, `Iyy` | The second moment of area about the centroidal x-axis and y-axis — how resistant the shape is to bending about each axis. |
| `Ixy` | The product of inertia about the centroidal axes (zero for a shape symmetric about either axis). |
| `J` | `Ixx + Iyy` — the polar second moment of area. |
| `rx`, `ry` | The radius of gyration about each centroidal axis (`rx = sqrt(Ixx / area)`, same shape for `ry`) — a single-number stand-in for how spread out the area is from that axis, used in buckling calculations. |
| `Sx_top`, `Sx_bottom` | The section modulus for bending about the x-axis, using the distance from the centroid up to the highest point of the outline (`Sx_top`) or down to the lowest point (`Sx_bottom`). |
| `Sy_left`, `Sy_right` | The section modulus for bending about the y-axis, using the distance from the centroid to the leftmost (`Sy_left`) or rightmost (`Sy_right`) point of the outline. |
| `outline` | The raw vertex list(s) used for the calculation, as an N×2 matrix of coordinates, in the drawing's own unit. For a composite section this is every loop's vertices run together, outer loop first, then each hole — there's no marker in the matrix itself showing where one loop ends and the next begins. Nothing in LiveSheet draws this yet; it's there to wire into a future feature. |

`Sx_top`/`Sx_bottom` and `Sy_left`/`Sy_right` are deliberately four separate numbers, not one: for
anything other than a perfectly symmetric shape, the distance from the centroid to the top edge
genuinely differs from the distance to the bottom edge, so the two section moduli differ too — and
an engineer checking both the tension and the compression side of a bent beam needs both.

## Single profiles vs. composite (hole) sections

If LiveSheet finds exactly one closed loop, that's your profile — winding direction (clockwise or
counter-clockwise) doesn't matter, you get the same numbers either way.

If it finds more than one closed loop on the filtered set, it checks whether they form one valid
**outer boundary plus holes**:

- The biggest loop (by area) is treated as the **outer** boundary, and must be wound
  counter-clockwise.
- Every other loop is treated as a **hole**, must be wound clockwise, and must sit entirely inside
  the outer loop's own bounding box.

If both checks pass, `area`, the centroid, and every second-moment output are computed for the
whole composite shape at once (outer minus holes) — see the worked example below. If either check
fails, you get one of the two composite-specific error messages described in Errors.

Two separate, unconnected outer shapes on the same drawing (two independent profiles that happen to
share a file) aren't supported as "two profiles" — LiveSheet will try to treat them as one outer
loop and a hole and, in most cases, report the winding-mismatch error instead. Put each profile in
its own file, or on its own layer and set **Layer** accordingly, if you need to keep them separate.

## Worked example: a right-triangle bracket

Say `bracket.dxf` contains one closed, straight-sided polyline with vertices `(0, 0)`, `(40, 0)`,
`(0, 20)` (millimetres, declared in the file's own unit setting).

1. **Insert > Component…**, Kind **CAD profile (DXF)**, Path `bracket.dxf`, Layer and Unit left
   blank, Name `P1`. Click **OK**.

`P1` shows no error, and its outputs are:

| Port | Value |
|---|---|
| `area` | `400 mm²` |
| `centroid_x` | `13.3333 mm` |
| `centroid_y` | `6.66667 mm` |
| `Ixx` | `8888.89 mm⁴` |
| `Iyy` | `35555.6 mm⁴` |
| `Ixy` | `-8888.89 mm⁴` |
| `J` | `44444.4 mm⁴` |
| `rx` | `4.71405 mm` |
| `ry` | `9.42809 mm` |
| `Sx_top` | `666.667 mm³` |
| `Sx_bottom` | `1333.33 mm³` |
| `Sy_left` | `2666.67 mm³` |
| `Sy_right` | `1333.33 mm³` |

Wire `P1.area` into a "Formula" component with input `a` and expression `a` (see
[Components and wiring](components.md)) and its result is the same `400 mm²` — a CAD profile's
outputs are ordinary numbers everywhere else on the sheet, with no special handling needed.

## Worked example: a hollow box section (composite, with a hole)

Say `box.dxf` contains two closed, straight-sided polylines on one layer: a 40 mm × 20 mm outer
rectangle, wound counter-clockwise, and a 10 mm × 10 mm square hole centred inside it (from
`(15, 5)` to `(25, 15)`), wound clockwise.

Add a CAD profile component pointing at `box.dxf` (no **Layer** filter needed, since there's only
one layer). It resolves without error, as a composite section:

| Port | Value |
|---|---|
| `area` | `700 mm²` (`800 - 100`, the outer rectangle's area minus the hole's) |
| `centroid_x` | `20 mm` |
| `centroid_y` | `10 mm` (unchanged from the outer rectangle alone — both shapes share the same centroid, by symmetry) |
| `Ixx` | `25833.3 mm⁴` |
| `Iyy` | `105833.3 mm⁴` |

If you move the hole so part of it sticks out past the outer rectangle's edge, or redraw it wound
the same direction as the outer rectangle, the component goes into one of the two composite error
states instead (see Errors).

## A profile built from loose LINE segments

You don't need a single polyline — four separate `LINE` entities that happen to form a closed
40 mm × 20 mm rectangle (end-to-end: `(0,0)`–`(40,0)`, `(40,0)`–`(40,20)`, `(40,20)`–`(0,20)`,
`(0,20)`–`(0,0)`) resolve exactly the same way a single closed polyline of the same shape would:
`area = 800 mm²`, `centroid_x = 20 mm`, `centroid_y = 10 mm`, `Ixx = 26666.7 mm⁴`,
`Iyy = 106667 mm⁴`. If one of those four lines doesn't quite reach its neighbour — leaving even a
small gap — LiveSheet can't chain them into a loop and reports the LINE-chaining error instead (see
Errors) rather than guessing how you meant to close it.

## Troubleshooting

- **A self-crossing outline gives a number, but not a meaningful one.** LiveSheet doesn't check
  whether a loop's edges cross themselves. A profile drawn so that two of its own edges cross is a
  known limitation: you won't get a crash or an error, but the area/centroid/moment numbers you get
  back for that shape don't correspond to anything real. Redraw the outline so it doesn't cross
  itself.
- **A degenerate line gives "Profile has zero area." instead of the LINE-chaining message.** A
  single zero-length `LINE` (its two ends are the same point), or two identical, overlapping `LINE`
  entities, both technically "close" into a one- or two-point loop rather than failing the chaining
  check outright — so you'll see `"Profile has zero area."` rather than the chaining error. Either
  message tells you something real is wrong with the drawing; check for a stray zero-length or
  duplicated line segment.
- **A full circle drawn as an `ARC` isn't recognised as one.** LiveSheet only treats a standalone
  `ARC` entity as a closed, full-circle profile when its start angle and end angle match exactly.
  If your drawing software exports that same full circle with a tiny rounding difference between
  the two angles instead of an exact match, LiveSheet won't recognise it as closed, and you'll see
  the curved-geometry error below. Draw a full circle as an actual `CIRCLE` entity instead of an
  `ARC` to avoid this.

## Errors

See [Error messages](errors.md#cad-profile-import-dxf) for the exact wording of every message a
CAD profile component or the "Add Component" dialog can show you, what causes it, and how to fix
it.
