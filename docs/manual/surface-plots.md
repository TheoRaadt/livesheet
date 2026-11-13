# 3-D surface plots

A 3-D surface plot draws a quantity that depends on two variables as a height surface, for example
a stress over the width and depth of a plate. You describe it in plain text, in the same spirit as
a 2-D plot written as text, and the picture redraws whenever a number above it changes.

## Inserting one

1. Choose **Insert > 3-D plot**. A new plot region appears at the crosshair with the starter text

   ```
   surface
   over 
   across 
   show 
   ```

   and a hint: "Empty 3-D plot: double-click to edit. Add an 'over' line, an 'across' line and one
   'show' line." No dialog opens; 3-D plots are text only.
2. Double-click the region to edit its text. Fill in the three lines (see below).
3. Click elsewhere (or press Esc) and the surface is drawn.

The first line of the region must be exactly `surface`. A math region that says `surface := 3` is
still an ordinary definition of a name `surface`.

## The lines

| Line | Meaning |
|---|---|
| `over NAME from A to B points N` | The first horizontal axis. |
| `across NAME from A to B points N` | The second horizontal axis. |
| `show EXPRESSION` | The height. Exactly one line. |
| `draw mesh` or `draw wire` | Filled, shaded cells (the default) or wire lines only. |
| `view AZ EL` | Viewing angles in degrees, for example `view 40 30` (the default). |
| `xunit U`, `yunit U`, `zunit U` | Show an axis in another unit of the same kind. |
| `xlim LO to HI`, `ylim ...`, `zlim ...` | Fixed axis limits; either end may be `auto`. |
| `title TEXT`, `xlabel TEXT`, `ylabel TEXT`, `zlabel TEXT` | Your own chart and axis texts. |

`over` and `across` each appear exactly once, and need different names. Besides the
`NAME from A to B points N` form, each can name a range variable (`t := 0 s to 2 s step 1 s`) or a
vector you defined above. `points` is optional and means 25 by default; the most you can use is
100 (and a range variable or vector may hold at most 100 values). Values may run up or down.

Inside `show`, the `over` name and the `across` name stand for the current sample values, even if
you defined the same names elsewhere on the sheet (those definitions are not changed).

Units work as in 2-D plots: each axis takes the unit of its values, `zunit kN` and the like pick a
display unit of the same kind, and labels get the unit in square brackets.

## Worked example

```
surface
over x from 0 to 2 points 3
across y from 0 to 2 points 3
show x + 2*y
```

The region reports `surface 3 x 3 points` as its summary and draws a tilted plane whose height
runs from 0 to 6. With `zlim 0 to 4` added, cells whose corners reach above 4 are left out whole,
so the edge of the surface is jagged at a fixed limit. Cells are also left out where the height is
undefined: with `over x from -1 to 1 points 3` and `show 1/x` the column at `x = 0` is simply a gap.

## Turning, zooming and resetting the view

- **Rotate**: press inside the chart and drag. Moving right turns the surface to the right
  (increases the azimuth) and moving up tilts it up (increases the elevation), half a degree per
  pixel. The elevation stops at -90 and 90 degrees; the azimuth wraps around.
- **Zoom**: roll the mouse wheel over the chart. Each notch changes the size by 10 percent, between
  a quarter and four times the starting size. Rolling the wheel outside the chart scrolls the sheet
  as usual.
- **Move the region**: because a drag inside the chart turns it, move the whole region by pressing
  on its frame, just outside the chart, and dragging. The resize handle works as before.
- **Reset 3-D view**: right-click the region and choose **Reset 3-D view** to go back to the
  `view` line (or to azimuth 40, elevation 30, normal size if there is none).

The turned and zoomed view is saved with the sheet, separately from the text, and wins over the
`view` line. If you edit the `view` line itself, the saved view is cleared and the line applies.
While you drag a surface with more than 40 points per axis, it is drawn as wire lines only and
fills in again when you let go.

## Printing

Export PDF draws the surface as vector graphics, so it stays sharp when zoomed. Like other plots, a
tall 3-D plot can overlap regions below it; LiveSheet does not push them down.

## Errors

Messages appear in the plot frame in red. See [3-D surface plots in the error
reference](errors.md#3-d-surface-plots).
