# Importing data

If your measurements live in a CSV (or other delimited text) file, you can bring them into a sheet
once and then use their columns in formulas such as `mean`, `fit_linear`, `predict` and `plot`.
The numbers are copied into the sheet, so you can send the sheet to a colleague who does not have
your file.

You do this with **Insert > Data from file...** (or the **Import...** button in the **Data** tab;
both do the same thing). Nothing is placed on the canvas by the import: the data appears in the
Data tab and its columns become variables you can type or click into any math region.

## Importing a file

1. Choose **Insert > Data from file...**. The **Import data** window opens.
2. Click **Browse...** next to **File:** and pick your file (the picker offers "Delimited text"
   files, `*.csv`, `*.tsv` and `*.txt`, and "All files"). You can also type the path into the box.
3. LiveSheet looks at the start of the file and fills in the options below with its best guess. Check
   the **Preview** table: it shows the first 20 rows as the current options split them. If the
   columns look wrong, change an option; the preview and the **Columns** table update a moment
   later.
4. Check the **Dataset name** (see below), and the **Unit** of each column in the **Columns** table.
5. Click **OK**. If a red message is showing, OK is greyed out until you fix it.

### The options

| Option | What it does |
|---|---|
| **Delimiter** | What separates the cells on a line: Comma, Semicolon, Tab, Pipe, or **Other** with one character of your own typed in the small box beside it. |
| **Decimal mark** | **Point** (`1.5`) or **Comma** (`1,5`). A number is read only with the mark you chose: with **Point**, a cell `1,5` is not a number, and with **Comma**, a cell `1.5` is not. Thousands separators, currency or percent signs, `inf`/`nan` and hexadecimal are not numbers either. |
| **First row is a header** | Tick it when the first line holds column names. If it is not ticked, the columns are called `col1`, `col2`, ... and have no unit. |
| **Skip first N lines** | Ignores that many lines at the very top (for a title or comment lines before the real table). |
| **Encoding** | **UTF-8** (the default) or **Latin-1**. Try Latin-1 if the file comes from older software and LiveSheet says it is not valid UTF-8 text. |
| **Incomplete rows** | What to do when a number column has an empty cell: **Report an error** (the default), or **Skip them** (the whole row is dropped and a grey note tells you how many). |

When you pick a file, LiveSheet suggests these options itself: the delimiter that splits the first
lines into the same number of cells most often, a decimal comma when the cells look like `1,5` and
there is no `1.5` anywhere, and a header when the first line has a non-number and the second line
has a number. These are only suggestions; every option can be changed. LiveSheet never uses your
computer's language settings for this.

Other things to know about how the file is read:

- Blank lines are ignored, cells are trimmed of surrounding spaces, and a cell in double quotes may
  contain the delimiter (`"a,b"`).
- Every line must have the same number of cells as the first line; LiveSheet does not pad or cut.
- A column is a **number** column when every non-empty cell in it is a number. If any cell is not a
  number, the whole column is read as **text** and a grey warning names the first offending line.
  Text columns are listed but cannot be used in formulas.
- A number column whose cells are all whole numbers (`0`, `1`, `2`) holds exact whole numbers;
  otherwise it holds decimal numbers. This matches typing `[1, 2, 3]` by hand.

### Units in the header

Write a unit in square brackets at the end of a column's header, `name [unit]`, for example
`Force [N]` or `x [mm]`. The unit may be a product, quotient or power of LiveSheet's known units
(`mm`, `N/m`, `kg*m/s^2`), without a number in front. Round brackets are never read as a unit.

You can also type a unit into the **Unit** cell of any number column in the **Columns** table; it
replaces the header's unit. Leave it empty for a column without a unit. A unit given for a text
column is ignored, with a grey warning if it came from the header.

### Column names and variable names

Each column gets a name made from its header: letters, digits and `_` are kept, anything else
becomes `_`, repeated underscores are merged, and leading and trailing underscores are removed. An
empty result becomes `col` plus the column's position, a name starting with a digit gets a `c` in
front, and a repeated name gets `_2`, `_3`, ... added. The original header text is kept for display.

| Header | Column name |
|---|---|
| `Force [N]` | `Force` (unit `N`) |
| `2nd mode` | `c2nd_mode` |
| `a b` | `a_b` |
| `a_b` again after that | `a_b_2` |
| empty, fifth column | `col5` |

### The dataset name

At the bottom of the window, **Dataset name** is filled in from the file name (`run1.csv` offers
`run1`). It must start with a letter or `_`, use only letters, digits and `_`, be at most 40
characters long, and be different from every other dataset in the sheet. It may not be the name of a
LiveSheet function, constant or unit (`sin`, `pi`, `m`, `mean` and so on). The name is checked as
you type.

## Using the data in formulas

Each number column becomes a variable named `<dataset>_<column>`, a column vector like one you
would type as `[a; b; c]`, carrying the column's unit. If every number column has the same unit (or
none has a unit), you also get one matrix named just `<dataset>` holding all number columns side
by side, in file order.

**Worked example.** A file `run1.csv`:

```
t,F
0,1.0
1,3.0
2,5.0
3,7.0
```

is imported as dataset `run1`. You now have `run1_t`, `run1_F` and the 4 x 2 matrix `run1`:

```
mean(run1_t) =                      = 1.5
mean(run1_F) =                      = 4
fit_linear(run1_t, run1_F) =        = [1; 2]
run1_F[2] =                         = 3
g(k) := k * mean(run1_F)
g(2) =                              = 8
```

`fit_linear` gives the constant term first, then the slope (see [Statistics](statistics.md)).
`run1_F[2]` is the second value. To plot the data, use `run1_t` and `run1_F` as existing vectors in
the Plot dialog (see [Plots](plots.md)). To see a column or the matrix, write `run1_t =` or
`run1 =`; the usual rule applies that a vector larger than 10 elements prints a short placeholder
rather than every value.

The dataset variables are visible to every region on the sheet, wherever it sits, and also inside
your own functions. They are not visible inside component formulas (see
[Components and wiring](components.md)).

### Printing with units

Imported data behaves exactly like data you typed with units. With the file

```
x [mm],y [N]
1,10
2,20
3,30
```

as dataset `d`:

```
mean(d_x) = mm          = 2 mm
mean(d_y) =             = 20 N
mean(d_x) =             = 0.002 m
```

A bare `=` prints in SI units, so the average of millimetre data shows as `0.002 m`. Ask for the unit
you want after the `=` (`= mm`) to get `2 mm`. Here `d_x` is in mm and `d_y` in N, which are
different units, so there is no combined matrix `d`; writing `d =` gives the usual "not defined"
message. If you change the unit of `x` to `cm` in the import window, `mean(d_x) = cm` gives
`2 cm`.

### Names you cannot define

You cannot define a name that a dataset already provides: `run1_t := 5` is refused (see
[Error messages](errors.md#importing-data)). Every other region still calculates. Two datasets
also cannot provide the same variable name (dataset `a` with column `b_c` and dataset `a_b` with
column `c` would both want `a_b_c`); such an import or rename is refused.

## Limits

LiveSheet reads at most 20,000 data rows, 100 columns and 200,000 number cells (rows times number
columns) from one file. A bigger file is refused with a message naming the limit. Only the first
table in a file is read; there is no way to pick columns during import.

## The Data tab

The **Data** tab (the last tab in the strip; see [The main window](main-window.md)) lists your
datasets.

- **No datasets yet.** It reads "No data yet. Import a CSV file to use its columns in formulas.",
  with the **Import...** button above it.
- **Buttons across the top.** **Import...** opens the import window. **Refresh**, **Rename** and
  **Remove** act on the selected dataset and are greyed out until you select one. Click a dataset's
  heading (the grey line, for example `run1 - 4 rows x 2 columns - run1.csv`) to select it. Hover
  over the heading to see the full source path and the options used. A new import is selected
  automatically.
- **One button per column.** Number columns show their variable name (`run1_t`, `run1_F`). Clicking
  one inserts the name at the caret, like any other tab button, or starts a new math region if you
  are not editing. Hover for the column name, number of values, unit and smallest and largest value.
  Text columns are shown greyed out ("Text column, not usable in formulas"). If the combined matrix
  exists there is also a button with the dataset's own name ("4 x 2 matrix of all numeric columns"
  on hover).
- **No combined matrix.** When the number columns have different units, the grey note "No combined
  matrix (columns have different units)" appears under that dataset's buttons.

The tab never shows the values themselves; write `run1_t =` in a region to see them.

### Refresh

**Refresh** reads the dataset's file again with the options and column units stored in the sheet,
and replaces the values. The name stays. If columns appeared or disappeared, a message says so, for
example `Columns changed: removed 'F'; added 'G'.`; regions that use a removed column then show
"not defined". If the file cannot be read, the dataset is left exactly as it was and the reason is
shown.

### Rename

**Rename** asks for a new name, checked like a new dataset name. Formulas that use the old variable
names are **not** rewritten; they show "not defined" until you change them.

### Remove

**Remove** asks "Remove dataset '<name>'? Formulas that use it will show errors." and, if you
agree, deletes it.

Importing, refreshing, renaming and removing each recalculate the whole sheet and mark the sheet as
changed.

## Saving, sharing and older versions

- The numbers are stored inside the `.lsheet` file, together with the file name they came from
  (shown for information only, and written relative to the sheet's folder when the file lies below
  it) and the import options. Opening a sheet never opens the CSV file, so the sheet works
  without it. Only **Refresh** reads the file again.
- A sheet that holds at least one dataset is saved as file format version 5. **Older LiveSheet
  builds refuse such a file** ("This file was made with a newer LiveSheet version"), because
  opening and saving it again would silently lose the data. A sheet without datasets is saved
  exactly as before and opens everywhere. Removing the last dataset makes the sheet save in its
  previous format again.
- Opening a file whose dataset is damaged (for example columns of different lengths) is refused
  with "Invalid dataset in file: ..." rather than quietly dropping the data.

## Known limitations

- **No undo.** Importing, refreshing, renaming and removing a dataset cannot be undone with Undo.
  Remove asks for confirmation for this reason.
- **Autocomplete** does not yet offer dataset variable names (see [Autocomplete](autocomplete.md));
  click the Data tab button or type the name.
- **Large files** (over about 2 MB) are read in one go, so the import window may pause briefly;
  there is no "Reading..." indicator yet.
- Excel and JSON files, linking to a file instead of copying it, and editing values in a grid are
  not part of this version.
