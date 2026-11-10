# 028 Data import core: CSV / delimited text -> datasets on the sheet, and the Data tab

Implements the "prerequisites" list at the end of spec 026 (items 1-3) and backlog 8 / 8a(i)
(CSV part). Backlog 32 (wireable data-source component) is a later layer on top of this, not part
of it (see "Deliberately NOT specified").

Source inspiration (concept only, nothing copied):
- The CSV convention itself: widely published, decades-old, informal "comma-separated values" practice
  (quote a field that contains the delimiter, header line optional, blank lines ignored), plus the
  Python standard library's own `csv` module documentation as the reader's behaviour reference
  (https://docs.python.org/3/library/csv.html, to be re-read by the developer; stdlib, PSF licence,
  no new dependency). Public format knowledge, no vendor product.
- Generic spreadsheet "import text file" wizard idea (pick delimiter, decimal mark, first row is a
  header, preview the first rows before accepting) common to every spreadsheet and statistics
  package; used as an idea only, no layout or wording of any product.
- Own prior material: spec 009 (components), 013 (modal import dialog with labelled fields, the
  low-risk UI shape), 017 (statistics functions consume plain vectors), 026 (Data tab
  prerequisites), engine/units.py, document.py (version policy), docs/manual/statistics.md and
  matrices.md. No vendor software, help text or example was consulted.

Scope and size: two phases, each shippable alone.
- D1 (engine + file format, no GUI, about 1.5-2 days): `engine/dataio.py`, evaluator seeding,
  `document.py` version 5 with a `datasets` section.
- D2 (GUI, about 1.5-2 days): import dialog, Data tab listing, insert/rename/refresh/remove.
No new dependency. Excel, JSON, remote/URL sources and wiring components are out (see below).

## User story
As an engineer with measurements in a CSV file, I want to import it once, see its columns in the
Data tab, click a column to drop its name into a formula, and use it in `mean`, `fit_linear`,
`plot` and friends with the right units, and have the sheet keep working when it is sent to a
colleague who does not have my file.

## Decisions (with reasons)

1. Reader is a new Qt-free module `livesheet/engine/dataio.py`, stdlib `csv` only. The evaluator
   itself still does no file I/O: it only receives already-read, in-memory dataset objects. This keeps
   the engine deterministic and testable and leaves the file handling in one small module.
2. A dataset is a named set of columns, injected into the evaluation environment as ordinary
   variables (column vectors, plus one matrix when sensible). No new value type, no new statement
   syntax, no `read_csv(...)` function. Reason: every existing function (mean, fit_linear, predict,
   plot, indexing, matrix functions) already works on vectors; a second access path through file
   reading inside a formula would re-read the disk on every recalculation, make results depend on
   the file system and make the sheet unportable.
3. Storage: embed by default. The numbers are copied into the `.lsheet`, together with the source
   path as an informational label and the import options, so the sheet is self-contained and
   reproducible and "Refresh from file" can re-read it on request. A purely linked mode (path only,
   data read on open) is NOT in this spec; the schema leaves room for it (see format section).
   Reason: linked data breaks silently when files move, makes results change under the user's feet,
   and is the harder failure mode to explain; embedding is the safe default and refresh gives
   most of the benefit of linking.
4. Units come from the header text: `name [unit]` (square brackets only), overridable per column in
   the import dialog. Parentheses are NOT interpreted (they are too common as ordinary header text).
5. Missing and non-numeric cells are never guessed silently (see rules), consistent with the
   engine's practice of not guessing an unstated unit.

## Behaviour (own words)

### Engine reader API (`livesheet/engine/dataio.py`, no PySide6, stdlib `csv` + existing engine modules)
Names are the developer's to refine; behaviour is fixed here.

- `ImportOptions`: delimiter (one of `,` `;` tab `|` or a single custom character), decimal mark
  (`.` default, or `,`), has_header (bool), skip_lines (leading lines to ignore, default 0; for
  preamble/comment lines), encoding (`utf-8` default, `latin-1` selectable), missing
  (`error` default, or `skip_rows`: drop every row that has an empty cell in a numeric column and report how
  many).
- `suggest_options(path) -> ImportOptions`: reads at most the first 20 non-blank lines (after
  decoding with UTF-8, a leading byte-order mark ignored). Delimiter: the candidate (tried in the
  order `,` `;` tab `|`) that gives the same field count, greater than 1, on the most of those
  lines; ties go to the earlier candidate; none qualifies -> a single column and `,`. Decimal mark:
  `,` when the delimiter is not `,` and at least one cell matches digits-comma-digits while no cell
  matches digits-dot-digits, else `.`. Header: true when the first line has at least one cell that
  does not parse as a number and the second line has at least one cell that does. Pure suggestion;
  the dialog shows it and the user can change it.
- `preview(path, options, max_rows=20) -> list of rows of raw strings`: for the dialog; never
  raises on a bad number, only on file/encoding problems.
- `read_table(path, options) -> Dataset` and `read_table_text(text, options) -> Dataset`
  (the second is for tests and embedding). A `Dataset` holds: name (set by the caller), source
  string, options used, ordered columns, and a list of warning strings. Each column holds: `name`
  (identifier-safe, see below), `label` (the header text as written, without the unit part),
  `unit` (text, empty if none), `kind` (`number` or `text`) and `values` (floats/ints for
  `number`, strings for `text`).
- `dataset_variables(dataset) -> dict[str, sympy expression]`: what the evaluator adds to its
  environment (see "How columns become vectors").
- `validate_dataset_name(name, existing_names)`: raises `DataImportError` for an invalid name.
- All failures raise `DataImportError(ValueError)` with one of the messages below. The module never
  writes files and never opens anything except the path it is given.

### Parsing rules
- Blank lines are ignored. Cells are trimmed of surrounding spaces. Quoting follows the stdlib csv
  default (double quote, doubled to escape), so a quoted field may contain the delimiter.
- A row with a different field count than the first data/header row is an error (no padding or
  truncating).
- A cell is a number if, after replacing the decimal mark `,` by `.` when that option is set, it is
  an ordinary decimal literal (optional sign, digits, optional fraction, optional exponent like
  `1e-3`). Thousands separators, currency signs, percent signs, `inf`/`nan` and hexadecimal are not
  numbers.
- Per column: if every non-empty cell is a number, the column is `number`; empty cells in it are
  "missing" (rule below). If any non-empty cell is not a number the whole column is `text` (all
  cells kept as strings, empty ones as empty strings) and the dataset gets the warning
  "Column 'F' is read as text because line 5 holds 'abc'." (first offending line only). Text
  columns are listed but never become variables (the engine has no string value).
- Missing values (empty cell in a `number` column): `missing=error` raises the error below naming
  the first one; `skip_rows` drops those rows from all columns and adds a warning "Skipped 3 rows
  with missing values." If skipping leaves zero rows, error "No complete rows left."
- Integer typing: a `number` column whose every cell is written as an integer (no `.`, `,` decimal
  or exponent) holds exact integers, otherwise floats; this matches how a typed `[1, 2, 3]` behaves
  and keeps whole-number arguments (binomial `k`) valid.
- A dataset needs at least one `number` column and at least one data row; otherwise errors below.
- Limits (constants in the module, easy to change): at most 20,000 data rows, 100 columns and
  200,000 numeric cells. Over the limit -> error naming the limit.

### Header, column names and units
- If `has_header` is false, columns are named `col1`, `col2`, ... and have no unit.
- Header text `x [mm]`: the part in the last pair of square brackets is the unit, the rest (trimmed)
  is the label. The unit text must parse with the engine's existing unit grammar to a pure unit (a
  product/quotient/power of known units such as `mm`, `N/m`, `kg*m/s^2`; no numeric factor, no
  variables); otherwise error "Column 'x': 'foo' is not a known unit." The per-column unit given in
  the dialog (or by editing a stored dataset) replaces the header unit and is checked the same way;
  the empty string means unitless.
- Column name (the identifier part of a variable) from the label: ASCII letters, digits and `_` are
  kept, every other character becomes `_`, runs of `_` collapse, leading/trailing `_` are removed;
  an empty result becomes `col<k>` (k = 1-based column position); a leading digit gets a `c`
  prefix; a repeat of an earlier name in the same file gets `_2`, `_3`, ... appended. The original
  label stays in `label` for display. (Example: `Force [N]` -> name `Force`, unit `N`;
  `2nd mode` -> `c2nd_mode`.)
- A unit applies to a `number` column only; a bracket on a text column is ignored with a warning.

### Dataset names
A dataset name must be an identifier (letters, digits, `_`, not starting with a digit), at most 40
characters, unique within the sheet (case-sensitive), and must not be a known unit, built-in function
or constant name (`sin`, `pi`, `m`, `mean`, ...). The default name offered is the file's stem passed
through the same sanitising rule as column names, de-duplicated with `_2`... Errors below.

### How columns become vectors/matrices (evaluator environment)
For dataset `run1` with `number` columns `t` and `F` the environment gains:
- `run1_t`, `run1_F`: column vectors (n x 1 matrices, same kind as a typed `[a; b; c]`). Elements
  are exact integers or floats per the typing rule, multiplied by the column's unit expression (as
  `cadprofile` already does for its `outline` port) so unit-bearing data behaves like typed
  unit-bearing data. Hence `mean(run1_F)` keeps N, `fit_linear(run1_t, run1_F)` yields coefficients
  with the usual unit rules of spec 017, and `plot` takes them via "Use existing".
- `run1`: an n x k matrix of all `number` columns in file order, defined only when every `number`
  column has the same unit (including all unitless). If units differ it is not defined, and the Data
  tab shows "No combined matrix (columns have different units)". Reason: a matrix with mixed
  units has no consistent meaning in the existing unit checks; avoiding it is safer than inventing
  rules.
- Indexing `run1_F[2]` and `length`-style helpers that already work on vectors work unchanged.
- These variables are part of the global environment of the sheet: visible to every region regardless
  of position (they are inputs, not statements), like the unit table. They are seeded in
  `Engine.evaluate` right after the unit table, before the pass that collects global definitions;
  `Engine.evaluate` gains an optional `datasets` argument (default none, so every existing caller and test is
  unaffected).
- A math region that tries to define a name equal to a dataset variable (`run1_t := 5`) gets the
  error below instead of silently shadowing. Using the dataset variables inside user-function bodies
  must work the same as any other global (developer: confirm with the backlog 62 stats-in-function fix
  in mind).
- Component formulas (spec 009 `engine/wiring.py`) do NOT see dataset variables in this spec.

### The .lsheet format (backward compatible)
Policy mirrors versions 2-4: a new version number is written only when the new content exists.
- New constant: format version 5 ("datasets"), written only when the sheet holds at least one
  dataset. Highest version read becomes 5. `SheetDocument.version()` returns 5 when
  `datasets` is non-empty, and otherwise exactly what it returns today. A sheet without datasets is
  byte-for-byte unchanged on save (same JSON shape, no `datasets` key), so all existing files and
  tests keep passing. A version-5 file also carries page breaks/wires/plots in the existing keys; 5
  is a superset of 4.
- Older LiveSheet builds reading a version-5 file refuse it with the existing message "This file was
  made with a newer LiveSheet version" (intended: opening and re-saving it would silently drop the
  data). Reading rule symmetry with version 3: a file that declares version 5 but holds no datasets
  is treated as newer/foreign and rejected the same way.
- New top-level key `datasets`, a list; each entry:
  - `name` (string), `source` (string, informational: path of the file imported; stored relative to
    the folder of the `.lsheet` when the file is below it, else as given; empty for pasted/test
    data), `storage` (string, always `"embedded"` in this spec; the reader must accept only that value
    and reject others as "newer", leaving room for a later `"linked"`),
  - `options`: `delimiter`, `decimal`, `has_header` (bool), `skip_lines`, `encoding`, `missing`
    (as in ImportOptions; used by Refresh),
  - `columns`: list of `{name, label, unit, kind, values}`; `values` is a JSON array of numbers for
    `number` and strings for `text`. Floats are written with Python's default shortest round-trip
    form, so a save/load cycle preserves every value exactly.
- Loading is strict for datasets (unlike wires): a dataset entry that is structurally invalid
  (missing key, values not all numbers/strings, columns of unequal length, bad name) raises
  `DocumentError("Invalid dataset in file: ...")`, because dropping it would silently lose data.
- Data are never executed or interpreted at load time beyond this validation; file paths in `source`
  are never opened on load.
- Future nesting (M6 item 33): a nested sub-sheet carries its own datasets with the same schema;
  not specified here.

### Error and warning messages (own wording; reader unless stated)
- `Cannot open 'data.csv': file not found.` / `Cannot read 'data.csv': <system reason>.`
- `'data.csv' is not valid UTF-8 text; try the Latin-1 encoding option.`
- `The file has no data rows.`
- `The file has no numeric column.`
- `Line 3 has 1 field, but the first line has 2.`
- `Column 'F' has an empty value at line 4; fill it in or choose to skip incomplete rows.`
- `Column 'x': 'foo' is not a known unit.`
- `The file has 30000 rows; LiveSheet reads at most 20000.` (similarly for columns and cells)
- `No complete rows left.`
- Dataset name: `'sin' is already a function name; choose another dataset name.`,
  `'m' is already a unit name; ...`, `A dataset named 'run1' already exists.`,
  `'2run' is not a valid name: use letters, digits and _, not starting with a digit.`
- Evaluator: `'run1_t' is a dataset column and cannot be redefined; rename the variable or the dataset.`
- Using the combined matrix when undefined: the ordinary "run1 is not defined" error; the Data tab
  carries the reason.
- Warnings (non-fatal, shown in the dialog and stored nowhere): text-column fallback, skipped rows,
  ignored unit on a text column.

### GUI phase D2

**Import dialog** (modal, labelled fields, OK/Cancel; same low-risk generic shape as spec 013's
dialog; nothing drawn on the canvas):
1. File row with Browse... (standard file picker, filter "Delimited text (*.csv *.tsv *.txt)" plus
   "All files").
2. Options: Delimiter combo (Comma, Semicolon, Tab, Pipe, Other + one-character field), Decimal
   combo (Point, Comma), "First row is a header" checkbox, "Skip first N lines" spin box, Encoding
   combo (UTF-8, Latin-1), "Incomplete rows" combo (Report an error, Skip them). Changing the file
   fills these from `suggest_options`; the user can then change any of them.
3. Preview table of the first 20 rows as the current options would split them.
4. Columns table below the preview: one row per detected column with the column name, kind
   (number/text) and an editable Unit cell prefilled from the header.
5. Dataset name field, prefilled and validated live. Inline message line (red) shows the first
   error, a grey line shows warnings; OK is disabled while an error exists. Reading happens when
   the dialog values change, debounced; for files over about 2 MB a "Reading..." state is shown.
6. OK adds the dataset to the sheet (embedded), selects it in the Data tab and does not insert any
   region.

Reachable from: the Data tab's Import... button and the menu entry Insert > Data from file...
(same command, one way to do it).

**Data tab** (replaces the placeholder; the same band container as the other tabs):
- Top row: buttons Import..., Refresh, Rename, Remove (the last three act on the selected dataset;
  disabled when nothing is selected). Empty state text (replaces the old placeholder): "No data
  yet. Import a CSV file to use its columns in formulas." plus the Import button.
- Below, one block per dataset in the order imported: a small heading "run1 - 4 rows x 2 columns -
  data.csv" (the tooltip shows the full source path and the import options), then one button per
  column. Number columns: label = the variable name (`run1_t`), tooltip = "Column t, 4 values, unit N
  (min 1, max 7)". Clicking inserts the variable name at the caret via the existing `insert_token`
  path, exactly like every other tab button. Text columns appear as disabled buttons with the tooltip
  "Text column, not usable in formulas". If the combined matrix exists a button for `run1` is shown
  with tooltip "4 x 2 matrix of all numeric columns".
- Dynamic buttons live in their own container and are NOT part of the static `symbol_buttons`
  label registry, so a column name can never clash with a static label.
- Refresh: re-reads the stored `source` (resolved relative to the sheet's folder, or absolute) with
  the stored options and per-column units, replaces the dataset's values, keeps the name, shows
  warnings such as "Columns changed: removed 'F'; added 'G'." If the file cannot be read the dataset
  is left unchanged and the error is shown. Unsaved sheet + relative source -> uses the stored
  string as given. Regions that use removed columns show the ordinary "not defined" error.
- Rename: validated like a new name; formulas using the old variable names are NOT rewritten
  (they become "not defined" errors), stated in the confirm text.
- Remove: confirm dialog "Remove dataset 'run1'? Formulas that use it will show errors." Add, refresh,
  rename and remove each trigger a full sheet recalculation and mark the document modified; if the
  window has an undo stack they are single undoable steps (developer: if the stack cannot hold
  non-region edits, state this in the log and make Remove ask for confirmation, which it does
  anyway).
- The tab never shows the values themselves (no grid editor in this spec; the user can still write
  `run1_t =` to see a vector, or `run1 =` for the matrix, with the existing "larger than 10
  elements prints a placeholder" rule).
- Keyboard: the buttons follow the same tab-order/Enter behaviour as other tabs; Import is the
  first focusable item.

## Syntax proposal
None. Datasets surface as plain variables `<dataset>_<column>` and `<dataset>`. Only the two error
texts above are new evaluator behaviour.

## Acceptance criteria
Reader and environment tests use `read_table_text` and the Engine only (no GUI, no real files except
two `tmp_path` ones).
1. Text `t,F\n0,1.0\n1,3.0\n2,5.0\n3,7.0` with auto-suggested options: delimiter `,`, has_header true.
   Dataset `run1` gives columns `t` (integers) and `F` (floats). `mean(run1_t) =` gives `1.5`,
   `mean(run1_F) =` gives `4`, `fit_linear(run1_t, run1_F) =` gives `[1; 2]`, `run1_F[2] =` gives `3`
   (1-based indexing as already defined by spec 002; developer confirms the exact index base and printing).
   `run1 =` is a 4 x 2 matrix.
2. Units: `x [mm],y [N]\n1,10\n2,20\n3,30` as dataset `d`: columns `x` (unit `mm`, label `x`) and `y`
   (unit `N`). Note (manager-approved 2026-11-10): dataset data behaves exactly like typed unit data, so
   a bare `mean(d_x) =` prints SI (`0.002 m`); the explicit `= mm` form gives `2 mm`. `mean(d_x) = mm` gives `2 mm`, `mean(d_y) =` gives `20 N`. Matrix `d` is not defined
   (different units); `d =` gives the ordinary not-defined error. Overriding the unit of `x` to `cm`
   changes `mean(d_x) = cm` to `2 cm`. Header `x [foo]` -> `Column 'x': 'foo' is not a known unit.`
3. Decimal comma: `a;b\n1,5;2\n3,5;4` suggests delimiter `;`, decimal `,`, header true;
   `d_a` equals `[1.5; 3.5]`, `d_b` equals `[2; 4]`. With decimal forced to `.` the column `a` is text
   with warning "Column 'a' is read as text because line 2 holds '1,5'." and `d_a` is not defined.
4. No header: `1,2\n3,4` with has_header false gives names `col1`, `col2`; with auto-suggest
   (first line fully numeric) has_header is false.
5. Naming rule: headers `Force [N]`, `2nd mode`, `a b`, `a_b`, `` (empty), `Force` repeated twice
   give names `Force`, `c2nd_mode`, `a_b`, `a_b_2`, `col5`, `Force_2` (in that column order, the
   fifth column being the empty one; test builds a six-column file). Labels keep the original text
   without the unit part.
6. Quoting: `"name, full",v\n"a,b",1` is read as two fields on the first line (text column, number
   column).
7. Errors: ragged file `a,b\n1,2\n3` -> `Line 3 has 1 field, but the first line has 2.`; empty
   cell `a,b\n1,2\n,4` -> `Column 'a' has an empty value at line 3; fill it in or choose to skip incomplete rows.`;
   with `missing=skip_rows` the result has one row and the warning "Skipped 1 rows with missing
   values."; header-only file -> `The file has no data rows.`; all-text file -> `The file has no
   numeric column.`; a latin-1 file read as UTF-8 -> the encoding message; missing path ->
   `Cannot open ... file not found.`; 20,001 rows -> the limit message.
8. Dataset names: `sin`, `m`, `pi`, `2run`, an empty string and a duplicate each raise the matching
   message; `run1` accepted; a name over 40 characters rejected.
9. Redefinition: with dataset `run1`, the region `run1_t := 5` gives the "cannot be redefined"
   error; every other region still evaluates.
10. Using data in a user function: `g(k) := k * mean(run1_F)` then `g(2) =` gives `8`.
11. Format: a sheet without datasets saves with the same `version()` and JSON shape as before
    (existing document tests unchanged and green). A sheet with one dataset saves as version 5,
    round-trips through `to_json`/`from_json` with identical column names, labels, units, kinds
    and bit-identical float values (e.g. 0.1, 1e-300, 123456789.12345679), together with page
    breaks and a plot present in the same sheet. A file with `"version": 5` and no `datasets` raises
    "newer LiveSheet version"; `"version": 6` still raises it; a dataset whose columns have unequal
    lengths raises `DocumentError("Invalid dataset in file: ...")`; a dataset with `storage`
    other than `"embedded"` is rejected as newer. Removing the last dataset makes the sheet save as
    its previous version again.
12. GUI (D2, offscreen tests plus a manual check by the tester on the real app): the Data tab no longer
    shows the placeholder text; with no datasets it shows the empty-state text and an Import button;
    after importing the criterion-1 text via the dialog (test drives the dialog's model/API, not
    native file pickers), the tab shows the heading "run1 - 4 rows x 2 columns" and buttons
    `run1_t`, `run1_F` (and `run1`); clicking `run1_F` on an empty sheet creates a math region whose
    source is exactly `run1_F`; with the caret after `a := ` it gives `a := run1_F`. Refresh after the
    file changed on disk updates values; Refresh with the file deleted leaves values unchanged and
    shows the error; Remove deletes the buttons and the next recalculation shows "not defined" in
    dependent regions; saving and reopening the sheet (without the CSV present) shows the same tab
    and the same results. The dialog's OK is disabled while any error message is shown. Static
    `symbol_buttons` still has unique labels and is unaffected by dynamic buttons.

## Edge cases
- Large pasted/ugly data: only the limits above; no streaming.
- Header-only first line with fewer fields than data rows -> the ragged-row error on the first data
  row.
- UTF-8 byte-order mark is ignored; `\r\n` and `\n` both work (stdlib csv with `newline=""`).
- Duplicate or reserved-looking column names never fail the import (renamed by the rule); only
  dataset names can be rejected.
- Column names can look like unit names (e.g. a column `m`): safe, because variables always carry the
  dataset prefix.
- A text column with unit brackets: bracket ignored, warning.
- Locale: the app's locale is never consulted; delimiter and decimal mark are explicit options.
- Files with several tables, merged cells, formulas: out of scope (those are spreadsheet formats).
- Security/privacy: the reader opens only the user-chosen path; `source` is stored only as an
  informational string and never opened on load; a shared sheet exposes the source path text (relative
  when possible).

## Deliberately NOT specified here
- Excel, JSON and other formats (backlog 8a(i) lists JSON; a second reader function with the same
  `Dataset` output can be added later without format change).
- Linked storage (`"storage": "linked"`), automatic reload on file change, URL sources.
- A wireable "data table" component kind exposing a dataset's columns as output ports (backlog 32);
  needs spec 009 plumbing and decisions about dataset-by-name references. Component formulas do not
  see dataset variables.
- Editing values in a grid, export to CSV (backlog 8 second half), tables/dates/string values in
  formulas, column selection at import, more than one table per dataset.
- Statistics-tab or manual text changes (documenter after acceptance: a new manual page "Importing
  data" and an errors.md section from the messages above; main-window.md Data tab sentences).

## IP check
Pass. CSV is a generic, decades-old public interchange convention (like DXF/PDF already treated in
specs 012/013); the reader is stdlib-only; the import-dialog pattern is the generic text-import
wizard idea found in every spreadsheet and statistics tool, expressed as a plain modal dialog with
labelled fields and a standard list/table, not an on-canvas interaction (ip-cleanroom rule 6 posture:
boring toolkit chrome). `name [unit]` header convention, `<dataset>_<column>` naming, "datasets",
"Refresh" and all message texts are own wording; no vendor keyword set, file format, label set or
example data. No patent-sensitive technique. Open IP question: none.

## Fits current architecture?
Yes. New engine module `livesheet/engine/dataio.py` (no PySide6); small additive change to
`Engine.evaluate` (optional argument, seeds the environment); `livesheet/document.py` gains a
`DatasetData` section and version 5 (additive, existing files untouched); GUI work (dialog, Data tab,
menu entry) in `livesheet/gui/` is D2 only. No new dependency.

## Open questions (for the manager / Theo)
1. Embedded default with Refresh, linked mode deferred: confirm? (Linked later is non-breaking.)
2. Limits 20,000 rows / 100 columns / 200,000 numeric cells: acceptable, or should big files be
   supported (needs a faster numeric path than sympy matrices)?
3. Combined matrix only when all units match, otherwise omitted: acceptable?
4. Strict (error) versus lenient (drop) loading of a broken dataset entry: spec says strict.
5. Should the stored `source` be a relative path when below the sheet's folder (portable) or always
   absolute? Spec says relative when possible; it reveals folder names in shared sheets.
6. Do you want JSON import (backlog 8a(i)) in D2 or as its own spec; and Excel via openpyxl
   (backlog 32, needs a licence check) later?
7. Dataset variables not visible in component formulas yet: acceptable until backlog 32?
