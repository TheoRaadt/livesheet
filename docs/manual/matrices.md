# Vectors and matrices

You can type a vector or matrix directly as bracket notation (`[1, 2; 3, 4]`), but the Matrix
dialog builds the same notation for you from a size picker and a fillable grid, so you don't have
to count commas and semicolons by hand.

## Inserting a new vector or matrix

1. Choose **Insert > Matrix…**, or right-click an empty spot on the sheet and choose
   **Matrix here**. The **Rows** and **Columns** step opens, defaulting to 2x2 (each can be set
   anywhere from 1 to 20).
2. Click **Next**. A grid of that many blank boxes opens, one per cell, filled left to right, top
   to bottom.
3. Type a value into every cell — a plain number, a fraction (`1/3`), a name, or a short
   expression (`a+1`, `sin(0.5)`).
4. Optionally:
   - Use **Add row**/**Remove row** and **Add column**/**Remove column** to resize the grid (you
     can go back and forth between the Rows/Columns step and the grid with **Back**; cells that
     still fit the new shape keep their values, new cells start blank).
   - Switch **Name** to "Define as" to give the matrix a name, and pick `:=` (an ordinary
     definition) or `≡` (a global definition).
   - Fill in **Scale/unit factor** to multiply the whole matrix by a trailing factor (handy for a
     unit, e.g. `N/m`).
   - Switch **Show result** to "Show numeric result (=)" (optionally with a **Display unit**) or
     "Show symbolic result (→)" if you want the matrix's value printed on the sheet.
5. Click **OK**. A new region appears on the sheet with your matrix as its text, ready to keep
   typing or to click away and commit.
6. Click **Cancel** at either step to leave the sheet exactly as it was — nothing is created.

## A worked example

To build the 2x2 stiffness matrix `K := [2, -1; -1, 2]*N/m`:

1. **Insert > Matrix…**, keep Rows=2/Columns=2, click **Next**.
2. Fill the grid, row by row: `2`, `-1`, `-1`, `2`.
3. Switch **Name** to "Define as", type `K`, keep `:=`.
4. Type `N/m` in **Scale/unit factor**.
5. Click **OK**.

LiveSheet writes `K := [2, -1; -1, 2]*N/m` onto the sheet, exactly as if you had typed it
yourself.

## Editing an existing matrix

Right-click a math region that holds nothing but a single bracket literal (optionally with a
leading name/`:=`/`≡`, a trailing `*factor`, and a trailing `=`/`→`) and choose **Edit as grid...**
to open the same dialog, pre-filled from what's already there. Clicking **OK** writes your changes
back; clicking **Cancel** leaves the region exactly as it was.

A region combined with anything else — added to another term, passed into a function, or holding
more than one bracket literal — can't be opened this way; its context menu simply won't offer
**Edit as grid...**, and you keep editing it as plain text, same as always. Double-clicking any
math region always starts the plain text editor, whether or not it holds a matrix — the Grid
dialog is only reached through **Insert > Matrix…**, **Matrix here**, or **Edit as grid...**.

The Grid step's own **Edit as text** button discards anything you changed in the dialog and opens
the region's ordinary text editor instead (for a brand-new insertion, it behaves exactly like
**Cancel** — nothing is created).

## Errors

The dialog checks a few things itself before writing anything (a blank cell, a comma or semicolon
typed inside a single cell, a blank name when "Define as" is chosen); anything else — an undefined
name, a unit mismatch, a nested bracket literal — only shows up once your matrix is actually
committed and evaluated, the same as if you'd typed it directly. See
[Error messages](errors.md#vectors-and-matrices) for the exact wording of each one.
