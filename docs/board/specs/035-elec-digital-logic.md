# 035 Electrical library phase 2: digital-logic functions on 0/1 values (engine + GUI)

Status: IP-reviewed by manager 2026-11-13 (generic textbook formulas, own names, no vendor keywords/tables; APPROVED once Theo answers the open questions; developer must re-run every hand-computed criterion through Engine()). Original: NOT yet IP-reviewed. Specialist proposal. Developer-ready only after (a) manager IP review, (b) a re-run of every numeric example in the acceptance criteria against the live engine (the values were computed by hand in this session; the specialist had no code-execution tool, so the re-run is a hard gate), and (c) open question 1 (zero rule) and open question 2 (0/1 convention) are decided.

Spec-numbering note: 035 is the next free number after 034 (2026-11-13). This is phase 2 of the electrical library overview (spec 034, "Phase plan" row 2). It follows spec 034's conventions: strict units, SI results, own error wording, the General rules of 034, and the 1A/1B/GUI-1 split (here: engine part and GUI part).

Source inspiration (concept only, nothing copied):
- Boolean algebra, AND / OR / NOT as 0/1 operations and the De Morgan laws: https://en.wikipedia.org/wiki/Boolean_algebra (research note docs/board/research/elec-eng-topics.md, accessed 2026-11-12) and https://en.wikipedia.org/wiki/De_Morgan%27s_laws (fetched 2026-11-13; facts only: the two laws are stated as NOT(P AND Q) = NOT P OR NOT Q and NOT(P OR Q) = NOT P AND NOT Q; the article mentions no NAND or NOR).
- Truth table: a table with one row per input combination, the standard way to list all 2^n input combinations (generic notation).
- Subject-area noun only: "digital logic" from the 034 research note outline (item 8). No vendor manual, catalogue, menu, keyword or example was used.

User story:
As an electrical engineer writing a calculation sheet, I want logic gates on 0/1 values and vectors of them, a truth-table generator and a way to check that two logic expressions give the same results, so that I can document combinational logic and verify De Morgan style identities inside a worksheet, with the same unit and error discipline as the rest of the electrical library.

## Behaviour (own words)

### General rules (this spec; the same zero rule is inherited by specs 036 and 037)
1. Calling convention: ordinary positional function calls in a math region. No keyword arguments. Argument names (a, b, x, y, n) are documentation shown in autocomplete call hints.
2. Bit values: every logic input is a plain number that must equal 0 or 1. An input may be a scalar or a column vector (for example `[0; 1; 1]`). The vector syntax is the engine's existing one (spec 002).
3. No units on logic values. A unit on a bit input is an error ("must be a plain 0 or 1, not V"). A unit that is dropped by the engine because the value is zero (for example `0 V`) is accepted as the bit 0, since the engine cannot tell it apart from a bare 0 (see open question 1 for the general zero rule).
4. Results are plain numbers 0 or 1 (never a unit, never True/False). A vector input gives a vector result of the same length, in the shape of the first argument.
5. Functions are pure: no state, no `.lsheet` change.
6. Error text is LiveSheet's own: `<function>: <argument> <problem>`, never a Python traceback.
7. Logic functions are not a replacement for a boolean type. Comparison results (True/False from `x > 3`) are rejected as inputs in this phase (open question 2).

### Function list (engine, developer-ready)
Notation: bit = a plain 0 or 1; bit vector = a column of bits of equal length. All results are bits or bit vectors.

| # | Function | Arguments | Formula (entry by entry) | Result |
|---|---|---|---|---|
| L1 | `logic_not(a)` | a: bit or bit vector | 1 - a | bit vector (same length as a) |
| L2 | `logic_and(a, b)` | a, b: bit or bit vector, same number of entries | a b | bit vector |
| L3 | `logic_or(a, b)` | same as L2 | a + b - a b | bit vector |
| L4 | `logic_nand(a, b)` | same as L2 | 1 - a b | bit vector |
| L5 | `logic_nor(a, b)` | same as L2 | 1 - (a + b - a b) | bit vector |
| L6 | `logic_xor(a, b)` | same as L2 | a + b - 2 a b (1 when exactly one input is 1) | bit vector |
| L7 | `logic_xnor(a, b)` | same as L2 | 1 - (a + b - 2 a b) | bit vector |
| L8 | `logic_equivalent(x, y)` | x, y: bit or bit vector, same number of entries | 1 when every entry of x equals the matching entry of y; 0 otherwise | bit (one value, not a vector) |
| L9 | `logic_truth_table(n)` | n: plain whole number from 1 to 8 | 2^n rows. Row i (counting from 0) holds the n binary digits of i, most significant digit in the first column | matrix of bits, 2^n rows by n columns |

Notes on the table:
- L8 is the check helper for identities such as De Morgan. There is no separate "De Morgan" function: write the two sides with L1-L5 and compare them with L8 (see acceptance criteria 11-13). This keeps one general mechanism instead of a special-purpose one.
- L9 row order: for n = 2 the rows are 00, 01, 10, 11; for n = 3 the rows are 000 to 111 in counting order. The first column is the most significant bit.
- Phase 2 is combinational only (no state, no clock, no flip-flops). Sequential logic is out of scope.

## Unit prerequisites
None. Logic values are dimensionless. No change to `livesheet/engine/units.py`.

## Acceptance criteria (phase 2)

### Engine part (Qt-free, `livesheet/engine/digital_logic.py`, merged into the evaluator's builtins like `ELEC_BUILTINS`)
Tests use `Engine().evaluate(...)` on single statements or small sheets. Logic results are exact integers, so the tolerance is exact equality. All values below were computed by hand from the truth tables (exact integer arithmetic, no rounding involved); re-run required.

Shared test inputs (define them in the test sheet first):
- `a := [0; 0; 1; 1]`
- `b := [0; 1; 0; 1]`
These are the two input columns of `logic_truth_table(2)` (rows 00, 01, 10, 11).

Registration and naming
1. All 9 names are callable in a math region and appear in the existing function-name autocomplete with their argument names: `logic_not(a)`, `logic_and(a, b)`, `logic_or(a, b)`, `logic_nand(a, b)`, `logic_nor(a, b)`, `logic_xor(a, b)`, `logic_xnor(a, b)`, `logic_equivalent(x, y)`, `logic_truth_table(n)`. Typing `logic_` lists all nine.
2. No name equals a `BUILTINS` key, a `UNITS` key, or a `syntax.py` keyword (test by set intersection).
3. `digital_logic.py` imports no PySide6. `.lsheet` format unchanged.
4. Wrong argument count gives the existing "Wrong number of arguments" message, for example `logic_not(1, 0)`.

Truth tables on the shared inputs (display via bare `=`, which prints the integer entries)
5. `logic_not(a) =` gives the column [1; 1; 0; 0].
6. `logic_and(a, b) =` gives [0; 0; 0; 1]. `logic_or(a, b) =` gives [0; 1; 1; 1].
7. `logic_nand(a, b) =` gives [1; 1; 1; 0]. `logic_nor(a, b) =` gives [1; 0; 0; 0].
8. `logic_xor(a, b) =` gives [0; 1; 1; 0]. `logic_xnor(a, b) =` gives [1; 0; 0; 1].
9. Scalars: `logic_not(0) =` gives 1; `logic_not(1) =` gives 0; `logic_and(1, 1) =` gives 1; `logic_xor(1, 1) =` gives 0; `logic_nand(1, 1) =` gives 0.
10. Result shape: the result has the shape of the first argument (a 4-entry column input gives a 4-entry column result).

De Morgan style identities (check helper L8)
11. First law: `logic_equivalent(logic_not(logic_and(a, b)), logic_or(logic_not(a), logic_not(b))) =` gives 1. (Left side [1; 1; 1; 0]; right side [1; 1; 1; 0].)
12. Second law: `logic_equivalent(logic_not(logic_or(a, b)), logic_and(logic_not(a), logic_not(b))) =` gives 1. (Left side [1; 0; 0; 0]; right side [1; 0; 0; 0].)
13. Negative control: `logic_equivalent(logic_and(a, b), logic_or(a, b)) =` gives 0 (AND is [0; 0; 0; 1], OR is [0; 1; 1; 1]).
14. Scalars: `logic_equivalent(1, 1) =` gives 1; `logic_equivalent(1, 0) =` gives 0.

Truth-table helper (L9)
15. `logic_truth_table(1) =` gives the 2 by 1 matrix [0; 1].
16. `logic_truth_table(2) =` gives the 4 by 2 matrix with rows [0 0], [0 1], [1 0], [1 1].
17. `logic_truth_table(3) =` gives 8 rows. Row 5 (counting from 1) is [1 0 0]; the first column is [0;0;0;0;1;1;1;1] and the last column alternates [0;1;0;1;0;1;0;1].
18. `logic_truth_table(8)` gives 256 rows by 8 columns; the last row is all ones (display placeholder "[256x8 matrix]" per spec 002 is expected). Test by reading the matrix entries, not the display.
19. Table columns match the shared inputs: column 1 of `logic_truth_table(2)` is `a` and column 2 is `b` (check by reading the matrix entries; no indexing syntax is needed).

Errors (no result, LiveSheet message, no traceback)
20. Entry not 0 or 1: `logic_and(2, 1)` gives `logic_and: a must contain only 0 or 1, found 2`.
21. Non-integer bit: `logic_not(0.5)` gives `logic_not: a must contain only 0 or 1, found 0.5`.
22. Vector with a bad entry: `logic_and([1; 1; 2], [1; 0; 1])` gives `logic_and: a must contain only 0 or 1, found 2` (first offending entry).
23. Unit on a bit: `logic_not(1 V)` gives `logic_not: a must be a plain 0 or 1, not V`.
24. Length mismatch: `logic_and([1; 0], [1; 0; 1])` gives `logic_and: a and b must have the same number of entries (2 and 3)`.
25. Length mismatch in the check helper: `logic_equivalent([1; 0; 1; 1], [1; 0])` gives `logic_equivalent: x and y must have the same number of entries (4 and 2)`.
26. Matrix instead of vector: `logic_not([1 0; 0 1])` gives `logic_not: a must be a vector`.
27. Truth-table size: `logic_truth_table(0)` gives `logic_truth_table: n must be a whole number from 1 to 8, found 0`; `logic_truth_table(9)` gives the same with `found 9`; `logic_truth_table(2.5)` gives `... found 2.5`.
28. Truth-table unit: `logic_truth_table(3 V)` gives `logic_truth_table: n must be a plain number, not V`.
29. Undefined name: with nothing defined, `logic_and(p, q)` gives `p, q are not defined`.

### GUI part (Electrical tab, separate sub-group; same mechanism as spec 034 GUI-1)
GUI-1. The Electrical tab gains one new sub-header "Digital Logic", appended after the spec 034 groups (Electrical order: DC Circuits, Power, AC Power, Three-Phase, Transformers, Resistor Networks, Phasors & Impedance, Transients & Resonance, Filters, Digital Logic). The tab stays one tab; TAB_ORDER unchanged.
GUI-2. Exactly 9 new buttons, one per function L1-L9, with the label, inserted text and tooltip in GUI-4. Each button calls the existing `insert_token(token)` callback. No new widget type, no dialog, no on-canvas editing.
GUI-3. Clicking "AND" inserts `logic_and(a, b)` at the cursor.
GUI-4. Button list (label | inserted text | tooltip; values are dimensionless, so the tooltips state the input and result form and say that no unit applies):
- "NOT" | `logic_not(a)` | Each entry becomes 1 - a. a is a 0/1 value or column; result 0 or 1.
- "AND" | `logic_and(a, b)` | Entrywise AND of two 0/1 columns of equal length; result 0 or 1 per entry.
- "OR" | `logic_or(a, b)` | Entrywise OR of two 0/1 columns of equal length.
- "NAND" | `logic_nand(a, b)` | Entrywise NOT of AND.
- "NOR" | `logic_nor(a, b)` | Entrywise NOT of OR.
- "XOR" | `logic_xor(a, b)` | Entrywise exclusive OR: 1 when exactly one input is 1.
- "XNOR" | `logic_xnor(a, b)` | Entrywise NOT of XOR: 1 when the inputs are equal.
- "same results?" | `logic_equivalent(x, y)` | 1 if every entry of x equals that of y, else 0. Use to check identities such as De Morgan's laws.
- "truth table" | `logic_truth_table(n)` | All 2^n input rows for n inputs (n from 1 to 8); first column is the most significant bit.
Placeholder names (a, b, x, y, n) are not unit letters, so an unfilled template gives "is not defined" instead of a silent unit (same landmine as spec 018 and 034 GUI-4).
GUI-5. No button calls anything except `insert_token`. No `.lsheet` change. No keyboard shortcut for the new buttons (click only, as in spec 020/034).
GUI-6. Regression: the existing DC Circuits, Power and spec 034 buttons are unchanged in label, text and order. The Electrical tab total becomes 47 + 9 = 56 buttons.
GUI-7. Tests that count the Electrical tab's sub-groups or buttons (spec 020, spec 022 and spec 034 GUI-1 tests) are adapted by the developer to the new totals, as spec 034 GUI-1 did; the adaptation keeps the original prefix checks.

## Syntax proposal (own keywords)
None. Function calls and the existing column-vector syntax only. No grammar change.

## Implementation placement (developer)
- `livesheet/engine/digital_logic.py` (new, Qt-free): `LOGIC_BUILTINS` with the 9 names, each with an explicit Python signature (argument names for autocomplete hints, as spec 034's builtins do), merged in `evaluator._builtins()` next to `ELEC_BUILTINS` (evaluator line 88 pattern).
- Argument checks: the bit check is a new argument kind. Specs 036 and 037 also need a plain-number kind, a temperature kind and the zero rule. The developer may move the shared argument checker out of `livesheet/engine/electrical.py` into a small Qt-free helper module and import it from both files. No change to any 034 function name, result or message except the zero rule if open question 1 is accepted.
- `livesheet/gui/sidepanel.py`: a new token list `_LOGIC_TOKENS` (9 tuples: category, label, token, tooltip) appended to `MATH_TOKENS`; the category "Digital Logic" appended to `TAB_CATEGORIES["Electrical"]` after the existing ones. TAB_ORDER unchanged.
- Tests: `tests/test_digital_logic.py` (developer); independent black-box `tests/test_digital_logic_blackbox.py` (tester, from this spec only); GUI button checks in the tester's file.

## Edge cases
- Empty vector: `logic_and([], [])` is rejected by the engine's own "Empty matrix" error before the function runs (same quirk as spec 034 1B-3). The function's own message "needs at least one entry" is implemented but is only reachable programmatically.
- Zero entries: 0 is a valid bit. A zero with a unit (`0 V`) loses its unit in the engine and is read as the bit 0 (general rule 3).
- Bits given as floats (`1.0`, `0.0`) are accepted and returned as integers 1 and 0.
- Very long vectors: no cap on the length of a bit vector (the truth table is capped at n = 8 only). A large vector is limited only by the engine's own matrix limits.
- Logic results used in arithmetic: the results are plain numbers and can be used in ordinary expressions (for example `logic_and(a, b) + 1`).
- Symbolic inputs (an undefined name) fail with the engine's "is not defined" message before the function runs (criterion 29).
- L8 with two differently sized arguments: rejected by the length check (criterion 25).

## IP check
Pass, pending manager review. Own function names (logic_ prefix), argument names, error wording and button labels. The functions are the standard two-valued logic operators and the De Morgan identities, stated in public encyclopaedic sources (Wikipedia "Boolean algebra" per the research note of 2026-11-12, and "De Morgan's laws" fetched 2026-11-13; facts only, CC BY-SA 4.0 sources, nothing copied). Truth-table row ordering is the standard counting convention. No vendor manual, catalogue, menu, keyword, example worksheet or table was used. No new UI type; buttons use the existing insertion mechanism. No on-canvas editing and no drawn-surface interaction, so no patent-sensitive interaction style is involved (IP-POLICY rule 6 not triggered). Not legal advice; legal review before 1.0 is a standing item.

## Verification status (specialist)
- The worked values are exact integer truth tables, checked by hand row by row (each identity is evaluated for all four input rows in criteria 11-13).
- No code-execution tool was available to the specialist in this session. The engine re-run of every criterion is a hard gate before developer dispatch.

## Fits current architecture?
- `livesheet/engine/digital_logic.py` (new, Qt-free), merged like `ELEC_BUILTINS`.
- Argument checker shared with `electrical.py` (small refactor, see Implementation placement).
- No `units.py` change, no `.lsheet` change, no new dependency (plain integer arithmetic; SymPy matrices already used by spec 002).
- GUI: one token list and one sub-group in the existing Electrical tab (spec 034 GUI-1 pattern).

## Open questions for Theo (copy to docs/board/decisions.md if accepted)
1. Zero rule (shared with specs 036 and 037). Today a zero with a unit (`0 V`, `0 ohm`) loses its unit in the engine, and a bare zero in a dimensional slot gives "needs a unit of ..." (backlog 81 item 1B-1). Proposed rule: a zero in a dimensional slot is read as the value 0; slots that need a positive value give "must be greater than zero", and slots that allow zero accept it. A nonzero bare number keeps the "needs a unit" message. Recommendation: accept; it also changes spec 034's bare-zero message on positive slots (manager to decide whether to apply it to 034 and 033 too).
2. Bit convention: 0 and 1 numbers only (recommended), no True/False type. Comparison results are rejected in phase 2.
3. No separate De Morgan function (recommended): the identity is checked with logic_equivalent on two written sides. Alternative: a dedicated check function, which would be a special-purpose helper for one identity.
4. Truth-table cap of 8 inputs (256 rows) (recommended); larger tables wait for a later display plan.
5. The `logic_` name prefix (recommended, avoids short words such as `and`/`or` that a user may type in prose).

## Phases 3 and 4 (other specs)
Specs 036 (operational amplifiers) and 037 (semiconductors) follow in that order; each gets its own developer slice. The GUI part of each is written into its own spec.
