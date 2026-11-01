# Plots

A plot draws one or more expressions against a variable that runs over a range. You build it with
a small form (the Plot dialog) instead of typing the chart's specification by hand.

## Inserting a plot

1. Choose **Insert > Plot**, or right-click an empty spot on the sheet and choose **Plot here**.
   The Plot dialog opens immediately at the spot you clicked.
2. A new, still-empty plot region appears on the sheet behind the dialog; it stays empty (no
   chart yet) until you click **Apply** or **OK**.
3. If you click **Cancel** without ever clicking **Apply**, the plot region is removed and nothing
   is left on the sheet.

Double-clicking an existing plot re-opens this same dialog, pre-filled from what the plot
currently shows, as long as that plot can be expressed with the dialog's own fields (see
"Editing a plot started as text" below). If it can't, double-click opens the plain text editor
instead, exactly as it always has.

## The dialog's fields

- **Function(s)** — one box per expression you want drawn as a trace (a line on the chart), in
  the order you want them. Click **Add function** for another box (up to 20); each box has its own
  **Remove** button. A box you leave blank is simply skipped — you don't have to delete it.
- **Variable(s)** — the variable the chart's horizontal axis runs over. Switch between:
  - **Use existing** — type the name of a range variable or a vector you already defined higher
    up the sheet.
  - **Sample a new range** — type a name, a "From" value, a "To" value and, if you want something
    other than the default of 101, a number of sample points (between 2 and 10000).
- **Axis limits** (Y min/max, X min/max) — type a plain number, a number with a unit (for example
  `8 s`), or leave a box blank for automatic. Leaving both boxes on one axis blank keeps that axis
  fully automatic.
- **Axis units** (X unit, Y unit) — the unit you want that axis displayed in, independent of the
  limits. Leave blank to let LiveSheet pick the display unit automatically.
- **Title and axis labels** — optional text for the chart's title, and for the X and Y axis
  labels. Leave any of them blank to use LiveSheet's own default labelling.

## Applying your changes

- **Apply** writes your current fields onto the plot region and recalculates it right away, so you
  can see the chart update (beside or behind the dialog) while you keep adjusting fields. The
  dialog stays open.
- **OK** does the same thing as Apply, then closes the dialog.
- **Cancel** on a brand-new plot (nothing ever applied) removes the region entirely. Cancel on a
  plot that already existed before you opened the dialog puts back exactly what it showed before
  you started editing — any changes you made during this dialog session, even an earlier Apply,
  are discarded.

## A worked example

Suppose you already have, higher up the sheet, a range variable `t` running from `0 s` to `10 s`,
and a speed `v := 5 m/s` defined above it. To chart the distance `v*t`:

1. **Insert > Plot**.
2. In **Variable(s)**, keep "Use existing" and type `t`.
3. In **Function(s)**, type `v*t` in the first box.
4. In **Axis limits**, type X min `2 s`, X max `8 s`, Y min `0 m`, Y max `40 m`.
5. In **Axis units**, type X unit `ms` if you'd rather see the x-axis in milliseconds.
6. Click **OK**.

You now have a chart of `v*t` against `t`, zoomed in to the 2-8 second window, with the y-axis
running from 0 m to 40 m.

If you'd rather sample your own range instead of using an existing variable — for example, to
chart `sin(x)` over one period without defining `x` anywhere else on the sheet — switch
**Variable(s)** to "Sample a new range", type name `x`, From `0`, To `6.283` (two pi), Points `5`,
and put `sin(x)` in **Function(s)**.

## Editing a plot started as text

If you typed a plot's specification directly (using the plain text editor) and it uses only the
things the dialog's fields can express, a **Use dialog...** button appears so you can switch to
the dialog instead. From inside the dialog, an **Edit as text...** button does the reverse: it
closes the dialog and opens the plain text editor on the plot's current specification. Some plot
features (for example a logarithmic axis or a custom marker style) can only be reached through the
text editor; for those, no **Use dialog...** button appears and double-clicking the plot opens the
text editor directly.

## Errors

Mistakes you can make while filling in the dialog, and problems with the expressions themselves
once they're evaluated, are shown either next to the field they belong to or as a banner above the
dialog's buttons when no single field is clearly at fault. See [Error messages](errors.md#plots)
for the exact wording, what causes each one, and how to fix it.
