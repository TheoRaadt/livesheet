# Review 015: FEM phase F1, 2D pin-jointed truss analysis (tester, black-box)

Spec: `docs/board/specs/015-truss-fem.md` (backlog FEM milestone), phase F1 only (truss/bar
elements, direct stiffness method). Implemented and independently verified once by the
manager (`QT_QPA_PLATFORM=offscreen pytest -q`: `tests/test_truss.py` 42 passed in
isolation; full suite excluding the concurrently-in-flight spec-014 DXF files 1425 passed,
2 xfailed, 0 failed) and accepted for implementation — see `docs/board/decisions.md`'s
"Decided 2026-10-30 (manager, spec 015 implementation)" entry. New/changed files under
test: `livesheet/engine/truss.py` (new), `livesheet/engine/syntax.py`, `livesheet/engine/
evaluator.py`. Developer's own tests: `tests/test_truss.py` (42 cases, not read before
writing this file beyond what the manager's decisions.md entry already quoted).

This review is written entirely from the spec's own wording and acceptance criteria, using
only `Engine().evaluate()`/`parse_statement()` (the public engine surface), never
`livesheet/engine/truss.py`'s internals directly and never `tests/test_truss.py`.

## Independent re-derivation of both worked numeric examples

The spec is explicit that both worked examples (single bar, criterion 1; symmetric two-bar
"A-frame", criterion 3) were hand-derived and never run through any tool while writing the
spec, and that the tester must verify them independently — not by trusting the developer's
own already-claimed NumPy cross-check, nor the manager's acceptance of it. Did this from
scratch with a standalone direct-stiffness implementation (`tests/test_truss_blackbox.py`'s
own `_numpy_truss()`, assembling the global stiffness matrix and calling
`numpy.linalg.solve` directly, never importing `livesheet.engine.truss`):

- **Single bar (criterion 1)**: `_numpy_truss` gives displacement `[[0, 0], [2e-5, 0]]` m,
  force `[1000]` N (tension), stress `[2e6]` Pa, reaction `[[-1000, 0], [1.1e-13, 0]]` N
  (the `1.1e-13` is ordinary floating-point noise on a free DOF that is "exactly 0 by
  construction," not a discrepancy — see Coverage notes). Matches the spec's quoted numbers
  exactly.
- **A-frame (criterion 3)**: `_numpy_truss` gives `uy3 = -0.000260401` m, member force
  `-6009.25` N (both elements, by symmetry), stress `-12018504.25` Pa (`= -12018500` to the
  spec's own 6-significant-digit quoting), reaction `[[3333.33, 5000], [-3333.33, 5000],
  [0, 0]]` N. Independently cross-checked against the spec's own closed-form formulas too
  (`F = -sqrt(13)/6 * 10000`, `uy3 = -13*sqrt(13)*10000/(18*200e9*0.0005)`), computed with
  plain Python `math`, not NumPy — both routes agree with each other and with the spec's
  quoted decimals to full float precision. **Both worked examples confirmed correct; no
  flaw found in the spec's own hand-derivation**, unlike spec 010's criterion 7/18, which
  did have genuine spec-side flaws caught by the same kind of independent check.

See `tests/test_truss_blackbox.py::test_oracle_single_bar_matches_hand_derivation` and
`::test_oracle_a_frame_matches_hand_derivation`.

## Tests added

`tests/test_truss_blackbox.py` (88 cases, all new, all pass), covering:

- Both oracle cross-checks above.
- All 22 numbered acceptance criteria, each as its own test (criteria 5-9's unit-mismatch
  checks built as a full otherwise-valid model + `resolve`, since the dimension checks only
  run inside `build()` at `resolve` time — see the one wording subtlety noted below).
- Criterion 13's zero-length check in all three shapes asked for by this task: the literal
  same-index-twice example; the broader "two *different* node indices at the same
  coordinates" case (confirmed caught, not just the literal example); and two "should NOT
  false-positive" checks — a genuinely tiny-but-nonzero element (`1e-6 m`), and two nodes
  that coincide in space but are never endpoints of the *same* element (modelled as two
  independent bars sharing one coincident corner, each independently well-posed).
- Every unit-mismatch error (5-9), every shape/missing-data error (10-17), the singular-
  system error (18, plus the spec's own two named edge cases: an unconnected orphan node,
  and a node with neither support nor element), the parsing error for trailing text on
  `resolve` (19), the "no result region below" error and "a trailing `load` region is
  unused" behaviour (20), and the four parsing shapes (22).
- **The specific parsing-deviation check this task asked for**: that exempting `support`
  from the "looks like an ordinary statement" guard does not leak into the other six model
  keywords. Two parametrized tests, one per guard mechanism the spec's own grammar can hit:
  `{nodes,elements,area,modulus,load,resolve} = 5 in q` (the bare-`=` sub-case `support`
  itself needed the exemption for) and `{..., vary, settle, ode, start, over, evolve} {:=|
  ≡|::=|→} 5 in q` (the pre-existing `_STATEMENT_OPS` sub-case). All eleven non-`support`
  keywords correctly fall back to an ordinary statement in both cases — **confirmed no
  leakage into the other keywords**. See Defects below for what this check also surfaced
  about `support` itself.
- Isolation (21): a plain sheet with no truss tags unaffected; a solve-block model (spec
  003, `vary`/`settle`), an ODE system (spec 010, `ode`/`start`/`evolve`) and a truss model
  (`nodes`/.../`resolve`) coexisting on one sheet with different tag names, all three
  resolving correctly and independently; a variable literally named `nodes`/`area`/`load`/
  `resolve` with **no** trailing ` in <name>` tag, fully unaffected (spec's own explicit
  scoping of this guarantee).
- Edge cases named by the spec: a non-zero support settlement value; a symbolic/undefined
  entry in `coords` rejected the same way spec 002 rejects it; `area` given as a 1xM row
  vector accepted identically to an Mx1 column; combining `fx`/`fy` on one `load` line is
  *not* treated as the duplicate-load error (only two separate `load` lines on the same
  node are).

Coverage: all 22 numbered acceptance criteria, the three spec-named edge cases checked
above, plus the task's own three specifically-requested checks (independent worked-example
re-derivation, the support-exemption leakage check, and criterion 13's broader-than-specced
behaviour including a false-positive check).

## One wording subtlety in criterion 5 (not a defect)

Criterion 5 is phrased as a single bare line (`nodes [0, 0; 1, 0] in bad1` → the unit
error), unlike criteria 6-9, which each explicitly say "on an otherwise-valid model."
Tested the literal single-line reading directly: it does **not** reproduce the unit error;
it instead gives criterion 20's own "No result region for truss model ... below this
region" error, because `build()`'s dimension checks only run when `resolve` actually calls
into it (per the spec's own architecture section: checks happen once, at `resolve` time,
not per-region) — a model with no `resolve` line at all never reaches that check for any
reason, unit or otherwise. Re-tested with a full otherwise-valid model + `resolve` added:
the exact `"Units do not match: node coordinates must be a length"` text reproduces exactly
as criterion 5 states. This is consistent with criterion 20 itself and with criteria 6-9's
own explicit "otherwise-valid model" phrasing — concluded this is a shorthand in criterion
5's own wording, not an implementation gap, and tested it the same way as 6-9 accordingly.

## Results

`QT_QPA_PLATFORM=offscreen pytest -q`, run multiple times across the session:
- Isolated: `tests/test_truss.py tests/test_truss_blackbox.py` together — **130 passed**
  (42 developer + 88 new), every run, including the final run of this session.
- Full suite excluding the DXF files (`tests/test_cadprofile*.py`,
  `tests/test_wiring_cadprofile.py`), to compare directly against the manager's own
  stated baseline for this spec — **1513 passed, 2 xfailed, 0 failed** = 1425 baseline +
  88 new, 0 regressions, matching exactly, stable across three consecutive runs earlier
  in the session.
- Full suite including the DXF files was **not** stable across the session: an early run
  showed 1571 passed/2 xfailed/0 failed (3 consecutive repeats, all green), but the final
  run before writing this review showed 9 failures, all in `tests/test_cadprofile.py`/
  `tests/test_cadprofile_blackbox.py`/`tests/test_wiring_cadprofile.py` — confirming the
  task's own warning that a concurrent spec-014 (DXF phase 2) developer session is
  actively editing those exact files/tests in this shared working tree. None of the 9
  failures are in any truss-related file; isolated `tests/test_truss.py tests/
  test_truss_blackbox.py` stayed green (130 passed) at the same point in time this final
  full-suite run showed the 9 DXF failures, confirming the two are unrelated. Per this
  task's own instruction, this review's pass/fail reporting focuses on truss-related
  tests (both counts above) and explicitly does not evaluate the DXF work, which belongs
  to a different, concurrently in-progress spec/review.

## Acceptance criteria

1. PASS. Single bar, tension: output starts `⇒ resolved "bar": 2 nodes, 1 elements`;
   `bar_displacement = [0, 0; 2e-05, 0] m`, `bar_force = [1000] N`, `bar_stress =
   [2000000] Pa`, `bar_reaction = [-1000, 0; ~0, 0] N` (node 2's x-row is `1.1e-13`, not
   exactly `0` — floating-point noise well inside tolerance, see below; everything else
   exact). Independently re-derived via NumPy, see above.
2. PASS. Reversed load: compression, `bar_force = [-1000] N`,
   `bar_displacement = [0, 0; -2e-05, 0] m`, `bar_reaction = [1000, 0; 0, 0] N`.
3. PASS. A-frame: `3 nodes, 2 elements` in the output; all four bound matrices match the
   spec's quoted numbers and the independent oracle above to well within tolerance.
4. PASS. Target-unit printing (`mm`/`kN`/`MPa`) matches the spec's own converted numbers
   exactly.
5. PASS (with the wording subtlety above). `Units do not match: node coordinates must be
   a length`, reproduced with a full model + `resolve`.
6. PASS. Both the bare-number and wrong-dimension (length instead of area) cases give the
   identical `Units do not match: cross-section area must be an area`.
7. PASS. `Units do not match: elastic modulus must be a pressure`.
8. PASS. `Units do not match: load "fx" must be a force`.
9. PASS. `Units do not match: support value for "x" must be a length`.
10. PASS. All four missing-declaration errors, exact wording, for `nodes`/`elements`/
    `area`/`modulus`.
11. PASS. All four duplicate-declaration errors, exact wording.
12. PASS. `Element 1: node 5 is out of range 1..3`.
13. PASS, broader than specced, confirmed not a false positive — see the dedicated bullet
    above and Defects (no defect found here, included for completeness per the task).
14. PASS. Both `area`/`modulus` count-mismatch errors, exact wording (including the
    spec's own "1 elements" non-pluralization, already present in the spec's own worked
    example text, not a new issue).
15. PASS. Both `support`/`load` out-of-range-node errors, exact wording.
16. PASS. Both the same-line and two-line duplicate-fix errors, identical exact wording.
17. PASS. Two different `load` lines on the same node: duplicate-load error. One `load`
    line giving both `fx` and `fy` on the same node: **not** an error (correctly treated
    as the single-line, no-implicit-summation case the spec describes).
18. PASS. No-support singular-system error, exact wording; both spec-named edge cases
    (unconnected orphan node; node with neither support nor element) also correctly give
    the same singular error, not a special-cased one.
19. PASS. `resolve extra in m19` → `resolve takes no expression`.
20. PASS. No result region below → exact wording; a `load` region placed below `resolve`
    confirmed unused (the resolved force is unchanged by it).
21. PASS. No-truss-tag sheet unaffected; a solve-block model, an ODE system and a truss
    model with distinct tags coexist on one sheet without interacting (all three verified
    to produce their own correct numeric results in the same `Engine().evaluate()` call);
    a variable named like a keyword with no trailing tag is fully unaffected.
22. PASS. All four parsing shapes match exactly (`model_truss_nodes`, `model_support`
    with its exact `axes` tuple list, `model_load`, `model_result` with `goal="truss"`).

## Defects

**D1 (minor) — the `support` keyword's guard exemption is broader than the spec's own
stated justification, breaking an ordinary definition of a variable literally named
`support` when it ends in a trailing ` in <name>` tag.**

The spec's clean-room note for this parsing deviation says only that `support`'s own
grammar "legitimately contains a bare `=`" and that this is why it alone is exempted from
the "looks like an ordinary statement" guard. The implementation exempts `support` from
the *entire* guard, including the pre-existing `_STATEMENT_OPS` check
(`:=`/`≡`/`::=`/`→`) that every other model keyword still has and that was never part of
the stated justification.

Confirmed empirically that every other model keyword — including every new truss keyword
(`nodes`/`elements`/`area`/`modulus`/`load`) and every pre-existing one (`vary`/`settle`/
`ode`/`start`/`over`/`evolve`) — still correctly falls back to an ordinary `define` for a
plain `<keyword> := 5 in q`, exactly as before this spec:

```python
>>> parse_statement("vary := 5 in q").kind
'define'
>>> parse_statement("load := 5 in q").kind
'define'
>>> parse_statement("nodes := 5 in q").kind
'define'
>>> parse_statement("support := 5 in q")
StatementError: Use "support <node> fix x, y" (optionally "x = <value>")
```

`support` is the one keyword where this now raises instead of defining the variable — a
regression relative to the project's own established pattern (every model keyword already
correctly ignores `:=`/`≡`/`::=`/`→` + a trailing tag, confirmed above for eleven other
keywords old and new). The manager's decisions.md entry calls the exemption "narrowly
scoped (exact keyword-string match on the leading token)" — true in that it only affects
lines starting with the literal word `support`, but not narrowly scoped to the *specific
grammar feature* (bare `=`) that motivated it in the first place.

Severity: low. `support` is an unusual choice for a plain variable name, and the case needs
both `:=` (or `≡`/`::=`/`→`) **and** a trailing ` in <name>` tag the definition wouldn't
otherwise need — the same general "pre-existing, already-accepted risk category" the
manager's own note invokes for every model keyword when a trailing tag is added
unnecessarily. Reporting it anyway because it's a genuine, clean, one-line reproducible
inconsistency specifically introduced by this spec, and because the fix is narrow and
cheap: keep the `_STATEMENT_OPS` check unconditional for every keyword including
`support`, and only skip the `_split_eval` (bare `=`) check for `support` specifically —
e.g.:

```python
if any(op in body for op in _STATEMENT_OPS):
    return None
if keyword != "support" and _split_eval(body) is not None:
    return None
```

Reproduced in `tests/test_truss_blackbox.py::
test_defect_support_exemption_breaks_ordinary_definition_of_a_variable_named_support`
(documents the current behaviour, does not assert the spec-correct one — kept the suite
green per this project's own convention for this kind of finding, same as spec 010's own
D1 review entry).

No other defects found. Criterion 13's broader-than-specced zero-length check (confirmed
PASS above) was already disclosed and accepted by the manager as strictly safer, with no
downside; independently re-confirmed it does not false-positive on either tested
"legitimate" shape (a tiny-but-nonzero element; two coincident-but-unconnected nodes).

## Coverage gaps

- **No real-window/computer-use pass this session.** No `computer_*` tool was available in
  this session's tool set (checked directly against the available tool definitions, same
  as several prior reviews in this series when the same was true). Theo's standing
  instruction to drive the real app on his Mac (type a `nodes`/`elements`/`area`/
  `modulus`/`support`/`load`/`resolve` model on a sheet, watch `resolve`'s one-line output
  and all four `<name>_displacement`/`_reaction`/`_force`/`_stress` matrices render live,
  open/close the window) could not be carried out. Everything in this review was verified
  headlessly via `Engine().evaluate()` only — unlike some earlier truss-adjacent reviews,
  this one did not even add a headless-`Worksheet`/`MathRegion` GUI-code-path test, since
  the spec itself states no new GUI/canvas mechanism is involved (every new statement kind
  is plain text in an existing `MathRegion`) — but a real-window pass should still watch
  the four bound matrices actually display correctly when printed via `=` on a live sheet,
  and that the `resolve` region's own summary line renders with the right unit/precision
  on screen, not just in `RegionResult.output`.
- The `1.1e-13` N floating-point noise on a free DOF's reaction (criterion 1) is not a
  defect (well inside every stated tolerance, and an ordinary consequence of
  `numpy.linalg.solve` rather than exact symbolic elimination), but it does mean a user
  reading `bar_reaction =` literally sees a tiny nonzero number where the spec's prose says
  "exactly 0 by construction." Not something a text-formatting change could or should try
  to fully suppress (it would have to special-case near-zero rounding somewhere, itself a
  judgement call), flagged only as a documentation nuance for the manual, not a code defect.
- This review did not attempt every possible combination of mixed-unit `area`/`modulus`
  vectors (e.g. a per-element vector with one entry in the wrong dimension while the rest
  are fine) or a 3+-element truss with a mix of scalar-broadcast and explicit-vector
  properties on the same model — the spec's own criteria don't number these combinations
  separately, and the scalar/vector and count-mismatch paths were each independently
  exercised, but not every cross-product of the two.
- No performance/large-truss testing was attempted — the spec itself explicitly makes no
  performance guarantee for this slice.

## IP red flags

None found. Grepped `livesheet/engine/truss.py` and the touched parts of
`livesheet/engine/syntax.py`/`evaluator.py` for vendor names (ANSYS, Abaqus, COMSOL,
NASTRAN, SolidWorks, CalculiX, FEniCS, Mathcad, Mathematica, Maple, MATLAB) and found none
anywhere in code, comments, or user-facing strings. The new keyword set (`nodes`,
`elements`, `area`, `modulus`, `support`, `fix`, `load`, `fx`, `fy`, `resolve`) and every
new error string are original and generic, matching the spec's own IP check exactly;
`resolve` correctly avoids both the project's own `solve`/`->`-chain keyword and the
policy-forbidden `Odesolve`. The result-binding convention
(`<name>_displacement`/`_reaction`/`_force`/`_stress`) is plain, self-describing English,
not drawn from any vendor's naming scheme. The underlying method (direct stiffness:
element stiffness, direction-cosine transform, scatter-add assembly, DOF elimination,
direct linear solve, axial force/stress recovery) is the same centuries-to-decades-old
generic statics/linear-algebra content the spec itself documents from Wikipedia and public
course notes — nothing distinctive to one vendor's implementation found in the code. The
two standing, already-carried-forward flags (no formal patent search on the "named group
of tagged regions solved on demand" idiom; pre-1.0 legal review) are unchanged by this
review, same as every prior spec in this series.

## Recommendation

Spec 015 (FEM phase F1, 2D pin-jointed truss) is functionally sound: all 22 numbered
acceptance criteria hold under independent black-box testing, and both of the spec's own
hand-derived worked numeric examples are independently confirmed correct via a standalone
NumPy direct-stiffness implementation (no flaw found, unlike spec 010's own criteria 7/18).
Criterion 13's broader-than-specced zero-length check was independently re-confirmed safe
(no false positive on either tested legitimate shape). One new, low-severity defect (D1)
was found: the `support`-only guard exemption is scoped more broadly than its own stated
justification requires, breaking the ordinary `:=`/`≡`/`::=`/`→`-plus-trailing-tag
fallback that every other model keyword (new and pre-existing) still correctly has for a
variable literally named `support` — a narrow, cheap fix is suggested above. Not a blocker
for any of the 22 numbered criteria. Truss-specific tests are stable: 130 passed in
isolation (42 developer + 88 new), confirmed at the end of the session; the full suite
excluding the concurrently-in-flight spec-014 DXF files is stable at 1513 passed / 2
xfailed / 0 failed across three consecutive runs (exactly 1425 baseline + 88 new, 0
regressions). The DXF files themselves were not stable across this session (an early
full-suite run was green including them, but the session's final run showed 9 failures
confined entirely to `tests/test_cadprofile*.py`/`tests/test_wiring_cadprofile.py`,
confirming active concurrent spec-014 work, not a truss regression) and are out of this
review's scope per the task's own instruction. No IP red flags found.
A real-window manual pass on Theo's Mac remains outstanding — no computer-use tooling was
available this session, so it stays an open, explicitly-flagged gap rather than something
silently skipped.
