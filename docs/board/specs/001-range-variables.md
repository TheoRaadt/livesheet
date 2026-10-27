# 001 Range variables and result tables

Source inspiration: public help page on range variables in a commercial worksheet tool, https://help.ptc.com/mathcad/en/PTC_Mathcad_Help/range_variables.html (found via web search, 2026-10-27; concept only: "a variable that steps through evenly spaced values, and expressions that are evaluated once per value"). No text, examples, keywords or notation were copied; the syntax below is our own.

## User story
As an engineer I define a variable that runs from a start value to an end value in fixed steps (for example time from 0 s to 10 s in 2 s steps), and I want to see one or more expressions evaluated for every value in a result table, with units checked, so I can inspect a calculation over a parameter sweep without copying formulas.

## Behaviour (own words)
Two new statement kinds, both usable in a normal math region.

1. Range definition: binds a name to an ordered list of evenly spaced values. The name is a "range variable". It is not a normal value: it can only be used inside a table statement (this slice).
2. Table statement: lists one or more column expressions. The engine evaluates every column once for each value of the range variable that the columns use, and returns the cells as text. The first-class output is structured (headers + rows); the GUI may show it as plain monospaced text in this slice.

Value generation: value number k (k = 0, 1, 2, ...) is `start + k*step`, computed from the start and step expressions (not by repeated addition, so no drift). The number of values is `floor((end - start)/step + 1e-9) + 1`. The end value is included when it is reached within that tolerance, otherwise the last value lies before the end. Units are kept: start, end and step must have the same dimension; each value carries the unit expression of the start.

Dimensionless ranges are allowed (`i := 1 to 5`). If `step` is omitted it is 1 in the unit of the start (so `i := 1 to 5` has 5 values, `t := 0 s to 3 s` has 4 values 0 s, 1 s, 2 s, 3 s).

Cells are formatted exactly like the existing numeric result `= ...` (same significant digits, SI simplification, same optional target unit), so the developer should reuse `Engine._numeric`.

## Syntax proposal (own keywords)
Grammar change in `livesheet/engine/syntax.py` (two new statement kinds, both are recognised before the existing `:=`/`→`/`=` rules and do not change them):

```
name := START to END               range definition, step 1
name := START to END step STEP     range definition with step
name ≡  START to END step STEP     global range (also ::=), same rules
table COL1, COL2, ...              result table
table COL1 in UNIT, COL2, ...      per-column target unit (like `v = km/hr`)
```

- Range detection: after `:=`/`≡`/`::=`, the right side matches `^(.+?)\s+to\s+(.+?)(\s+step\s+(.+))?$` (whitespace around `to` and `step` is required, lowercase only). `to`, `step`, `in` and a leading `table` are only special in these two statement forms; elsewhere they stay ordinary identifiers (`table := 3`, `total := 2` keep working because `:=` statements are only treated as ranges when the right side matches the pattern, and `table` is only a table when followed by whitespace and no `:=` or `≡` in the text).
- `table` columns are split on top-level commas (commas inside parentheses do not split, so `table t, max(t, 3 s)` has 2 columns). In a column, the last top-level ` in ` splits expression and target unit.
- `Statement` gains: kind `range` (fields `name`, `expr`=start, new `range_end`, new `range_step`, default empty) and kind `table` (new `columns: list[tuple[str, str]]` of expression and unit text). Existing fields and behaviour are unchanged; `.lsheet` files stay compatible because regions store plain text.
- A trailing evaluation `=` on a range definition or on a table is an error (see below).

Example sheet (reading order):
```
v := 3 m/s
t := 0 s to 10 s step 2 s
table t, v*t in m
```

## Acceptance criteria
Engine-level, via `Engine.evaluate`. "Rows" means the structured result `RegionResult.rows` (list of rows of cell strings) and `RegionResult.columns` (header strings = column text as typed, trimmed); a one-line `output` summary like `table 6 rows` is also set so existing GUI code does not break.

1. Basic unit table. Regions: `v := 3 m/s`, `t := 0 s to 10 s step 2 s`, `table t, v*t in m`. The range region has status ok and `defines == "t"`. The table has columns `["t", "v*t"]` (the `in m` part is not in the header), exactly 6 rows, and rows are `[["0 s","0 m"],["2 s","6 m"],["4 s","12 m"],["6 s","18 m"],["8 s","24 m"],["10 s","30 m"]]`.
2. Target unit conversion. Same sheet with `table v*t in km`: 6 rows, row 4 (t = 6 s) second cell parses to 0.018 km within 1e-9 (cell text `0.018 km`).
3. Dimensionless default step. `i := 1 to 5` then `table i, i^2` gives 5 rows: `[["1","1"],["2","4"],["3","9"],["4","16"],["5","25"]]`.
4. Fractional step has no drift and includes the end. `x := 0 to 1 step 0.1` then `table x` has exactly 11 rows; row 11 parses to 1 within 1e-12; row 4 parses to 0.3 within 1e-12.
5. Descending range. `n := 5 to 1 step -2` then `table n` gives values 5, 3, 1 (3 rows).
6. End not on the grid. `a := 0 to 10 step 4` then `table a` gives values 0, 4, 8 (3 rows; 10 is not included).
7. Single value. `b := 2 to 2` then `table b` gives 1 row `[["2"]]`.
8. User function in a column. `f(x) := x^2 + 1`, `i := 1 to 3`, `table i, f(i)` gives rows `[["1","2"],["2","5"],["3","10"]]`.
9. Global range. `k ≡ 1 to 3` placed after `table k` in reading order still works for the table (global pass runs first), 3 rows.
10. Two columns with different units. `t := 1 s to 2 s`, `m := 2 kg`, `table t, m*t` gives `[["1 s","2 kg·s"],["2 s","4 kg·s"]]` (unit text as produced today by `dims_to_text`; the developer must use the existing formatting and the test must compare against `Engine` output of `m*1 s =` for equality of the unit part).
11. Errors (all give status `error`, no rows; message text must contain the quoted part):
   - `t := 0 s to 10 m step 2 s` -> "Units do not match".
   - `t := 0 s to 10 s step 2 m` -> "Units do not match".
   - `i := 1 to 5 step 0` -> "step must not be zero".
   - `i := 1 to 5 step -1` -> "wrong sign" (also `i := 5 to 1` with default step 1 -> "wrong sign").
   - `i := 1 to 100000` -> "too many values" (limit: more than 10000 values is an error; exactly 10000 is allowed: `i := 1 to 10000` ok).
   - `table k, k^2` with `k` never defined -> "k is not defined".
   - `table 2 + 3` (no range variable used) -> "range variable".
   - `table i, j` with two different range variables -> "one range variable" (tables over two ranges are out of scope).
   - `table t in kg` with `t` in seconds -> "Units do not match".
   - `t =` or `t + 1 =` where `t` is a range variable -> "t is a range variable" (hint: "use table").
   - `t := 0 to 5 =` (trailing evaluation on a range definition) -> error "Use table to show a range".
   - `table t, v*t =` (trailing `=`) -> error "table takes no '='".
   - Empty table `table` or `table ,` -> "table needs at least one column".
12. A range definition itself never prints a result (output is empty), like a plain `x := 5 m`.
13. Regression: all existing tests in `tests/test_engine.py`, `tests/test_document.py` and `tests/test_gui.py` still pass unchanged. In particular `total := 2`, `table := 3` followed by `table =` (an ordinary evaluation of the name `table`) and `x := 5 m =` behave as before.
14. A redefinition later in reading order replaces the range (`t := 0 to 2`, `table t`, `t := 10 to 11`, `table t`: first table 3 rows, second table 2 rows).

## Edge cases
- Range variable name collides with a unit name (`s := 1 to 3`): same rule as today, the user definition wins.
- Using a range variable inside another definition (`y := 2*t`) is out of scope: error "t is a range variable" (no implicit vectorisation in this slice).
- Function parameters named like a range variable shadow the range inside that function body (the function is evaluated per value by substitution of the argument, so `f(t)` works).
- Floating point: dimensionless fractional steps use the tolerance rule above (1e-9 on the count); a range whose end differs from the grid by more than that tolerance is not extended.
- Errors in one cell (for example `table i, 1/(i-2)` for `i := 1 to 3`) follow the existing evaluator behaviour (a division by zero shows `undefined` in that cell, like `1/(x-2) =` does; a unit or syntax error in any cell makes the whole table an error); no partial tables on errors. (Updated 2026-10-27 after tester finding D4.)
- The 10000-value limit is a constant in the engine so it can be changed later.

## Out of scope (later specs)
Vectors/matrices, indexing like `t[2]`, plotting over a range, tables over two ranges, vectorised arithmetic on ranges, symbolic ranges, GUI grid widget and CSV export of tables, ranges inside user functions or sums.

## IP check
Pass (manager to confirm). Concept only (stepping a variable over evenly spaced values and tabulating expressions) is a general mathematical/programming idea. Syntax uses own words `to`, `step`, `table`, `in` and deliberately avoids the double-dot range notation and any vendor keyword set or implicit-table display behaviour. Source text was not copied; only the public help page URL above was consulted for the concept. No known patent concern, but not legal advice; see open question on the `..` notation in the README roadmap.

## Fits current architecture?
- `livesheet/engine/syntax.py`: new kinds `range` and `table`, extra `Statement` fields; existing parsing order unchanged. Small, pure-Python, no sympy.
- `livesheet/engine/evaluator.py`: `RegionResult` gets optional `columns` and `rows` (default empty). Pass 1 (globals) also stores global ranges. A range is stored in a separate per-run mapping (suggested: a small `RangeVar` dataclass in an `env`-adjacent dict, or in `env` guarded by a check) so that normal expressions never see it; any normal expression that names a range variable raises the "is a range variable" error before parsing. Table evaluation: copy `env`, bind the range name to the k-th value, parse and format each column with the existing `parse` and `_numeric`. Units: reuse `measure`/`UnitError`; compare dimensions of start, end and step with `measure(...).dims`. Developer should compute the count with exact sympy arithmetic when inputs are rational and with floats otherwise.
- `livesheet/engine/units.py`, `formatting.py`: no change expected.
- `livesheet/gui/`: minimal in this slice. Where the GUI shows `RegionResult.output`, show `columns` and `rows` as a monospaced multi-line text (columns separated by two spaces, right-aligned). A real grid widget is a follow-up.
- `livesheet/document.py`: no change (plain text regions).
- Tests: new `tests/test_ranges.py` for criteria 1-14; GUI smoke test that the table text appears.
- Size estimate: about 2 days (parser + evaluator + tests 1.5 days, GUI text rendering 0.5 day).
