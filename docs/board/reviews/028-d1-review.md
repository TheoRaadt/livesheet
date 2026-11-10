# Review: spec 028 phase D1 (engine reader + .lsheet v5)

Tester: independent black-box tests from the written spec. File: tests/test_spec028_d1_review.py
(212 cases). Result: 209 passed, 1 skipped, 2 strict xfail (real defects). Developer file
tests/test_dataio_028.py: 49 passed. Engine verified Qt-free (subprocess import check).

## Coverage
Delimiters (, ; tab | custom), decimal comma/point incl. exponent, quoting (embedded delimiter,
newline, doubled quote), BOM, CRLF, Latin-1 vs UTF-8 (+ suggest), ragged/blank-line line numbers,
header-only/empty, missing cells error/skip (count, all-columns drop, none left), text columns and
exact warning, int vs float typing, non-number forms (1,000 quoted, $, %, hex, inf, nan, 1e, =1+1),
header units (forms, last bracket pair, parentheses not units, bad-unit list incl. injection
strings, override, set_column_units, text column unit warning), naming rule (criterion 5 + edge
cases), limits exactly at/over (rows, columns, cells, numeric-only counting), suggest_options rules
(tie, 20-line window, decimal, header), dataset-name errors with exact texts, environment variables
(shapes, text omitted, matrix omitted for differing units), mean/stdev/fit_linear/predict/
r_squared/indexing, user function bodies, redefinition error, engine reuse, version rules
(v5 only with datasets, v5 empty and v6 rejected, storage != embedded rejected, 25 malformed entry
variants -> DocumentError, duplicates, NaN/Infinity), exact float round trip with page break and plot,
relative source, examples written identically to the pre-D1 writer (git HEAD baseline).

## Defects
D1-R1 (low/medium): a unit SUM is accepted as a column unit. Repro:
`read_table_text("x [mm+m],y\n1,2", ImportOptions(), name="d")` succeeds; `d_x` becomes
`1001*meter/1000`. Spec: unit must be a product/quotient/power of known units. Expected:
`Column 'x': 'mm+m' is not a known unit.` Test: test_unit_sum_rejected (strict xfail).

D1-R2 (low): an integer cell beyond float range (e.g. "1" followed by 400 zeros) makes the
column text ("no numeric column"), because _is_number also requires float() to be finite, while the
spec says integer columns hold exact integers. Test: test_very_long_number_cell (strict xfail).
Judge by Theo whether to fix or to document as a limit.

## Spec deviation / questions (not reader defects)
S1 Criterion 2 literally says `mean(d_x) =` gives `2 mm`. Actual: `= 0.002 m`; `mean(d_x) = mm`
gives `2 mm`. Typed `mean([1 mm; 2 mm; 3 mm]) =` also prints `0.002 m` (engine's SI-by-default
rule), and the spec decision is that dataset data behave like typed data, so the implementation is
consistent with the decision; the criterion text is what is wrong. Recommend amending criterion 2
to `mean(d_x) = mm` (pinned by test_criterion2_literal_spec_text_mean_without_target_unit).
S2 A single field over 131072 characters is refused with "The text cannot be split into fields:
field larger than field limit (131072)." (clean DataImportError, not a crash). Not in the spec;
acceptable, but could be a named limit.
S3 Spec 10 says `length`-style helpers work on vectors; `length` is not defined in the engine
(pre-existing, not D1).
S4 combined matrix is omitted when unit TEXT differs even if dimensionally compatible (m vs mm);
matches spec ("same unit").
S5 Pre-existing: examples/demo.lsheet is written with float coordinates (40.0), so a re-save is not
byte-identical to the file in the repo; the D1 writer output is identical to the pre-D1 writer.

## Gaps
GUI is D2 and not tested here. Performance at the 200,000-cell limit through Engine.evaluate
(sympy Matrix of 200k elements) was not timed; only reader limits are tested. Component formulas
not seeing datasets is only sanity-checked. No IP red flags in dataio.py/document.py (stdlib csv,
own wording, no vendor names).
