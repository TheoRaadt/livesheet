# Review 013: DXF profile import, phase 1 (tester, black-box)

Spec: `docs/board/specs/013-dxf-profile-import-core.md` -- a new `"cad-profile"` component kind
that reads a single closed, straight-sided `LWPOLYLINE`/`POLYLINE` loop out of a `.dxf` file and
computes its 2D section properties (area, centroid, `Ixx`/`Iyy`/`Ixy`/`J`, `rx`/`ry`, four
section-modulus ports, `outline`), plugged into spec 009's existing component/wire graph. New
dependency: `ezdxf` (MIT, 1.4.5), approved by Theo 2026-10-30. Implemented by the developer and
independently verified by the manager (1408 passed, 2 xfailed, 0 failed) -- see
`docs/board/decisions.md`'s "Decided 2026-10-30 (manager, spec 013 implementation)" entry. New/
changed files under test: `livesheet/engine/cadprofile.py` (new), `livesheet/engine/wiring.py`,
`livesheet/gui/componentdialog.py`. Developer's own tests: `tests/test_cadprofile.py`,
`tests/test_wiring_cadprofile.py`, plus GUI additions in `tests/test_wiring_gui.py` -- none of
these were read for assertion ideas, only skimmed for API/convention shape (constructor
signatures, fixture-generation style) before writing this review's own, independent file.

## Independent re-derivation of the worked-example triangle (from scratch)

The spec's worked example is a right triangle `(0,0)`, `(40,0)`, `(0,20)`, CCW wound,
`$INSUNITS = 4` (mm). Re-derived its section properties independently with exact
`fractions.Fraction` arithmetic in a standalone script (not importing anything from `livesheet`,
not trusting either the spec's own stated decimals or the implementation's floats), applying the
shoelace-formula-family formulas exactly as the spec's own "Behaviour" section states them:

```
area = 400 (exact)
centroid_x = 40/3, centroid_y = 20/3
Ixx = 80000/9, Iyy = 320000/9, Ixy = -80000/9, J = 400000/9
rx = sqrt(200/9) = 4.714045..., ry = sqrt(800/9) = 9.428090...
c_top = 40/3, c_bottom = 20/3, c_left = 40/3, c_right = 80/3
Sx_top = 666.667, Sx_bottom = 1333.33, Sy_left = 2666.67, Sy_right = 1333.33
```

These match the spec's own stated worked numbers exactly -- the spec's worked example itself has
no flaw (unlike spec 010's own worked example, which did). All numeric assertions in the new test
file compare against these independently re-derived values, not against the spec's text or the
implementation's output.

## Independent re-verification of the clockwise-winding sign-flip fix

The task specifically asked to verify this myself rather than trust the developer's/manager's
own check. Confirmed two ways:
1. Called `cadprofile.section_properties()` directly with a CW-wound version of the same triangle
   (`(0,0)`, `(0,20)`, `(40,0)` -- same polygon, opposite winding, confirmed by hand that its
   shoelace signed area is -400, i.e. genuinely CW) and asserted every one of
   area/centroid_x/centroid_y/Ixx/Iyy/Ixy/J/rx/ry/Sx_top/Sx_bottom/Sy_left/Sy_right is identical
   (within `rel=1e-6`) to the CCW version's. Passes.
2. Repeated the same check through the *whole* wiring path (a real generated CW DXF fixture, via
   `wiring.evaluate()`, not just the pure-math function) -- same result: identical scalar outputs.
   Additionally checked that `outline` (the raw, never-reordered, file-order vertex list) still
   differs in order between the CCW and CW fixtures, since the internal reversal used for the
   moment-formula math is local to `section_properties()` and is never written back into the
   vertex list `wiring.py`'s `_compute_cad_profile` uses to build the `outline` port -- confirmed
   this is in fact what the code does (read `livesheet/engine/wiring.py`'s
   `_compute_cad_profile`: it builds `outline` from the vertex list returned by `read_profile`,
   never from anything `section_properties()` touched). Both checks pass; the developer's fix is
   correct and does not leak into `outline`'s own, intentionally-raw semantics.

## Tests added

New file: `tests/test_cadprofile_blackbox.py`, 32 cases, written from the spec's own acceptance
criteria 1-11, its "Edge cases" section, and the "Behaviour" section's own formulas -- not from
the developer's test files. Every `.dxf` fixture is generated at test time via ezdxf's own write
API (`ezdxf.new()`, `.modelspace().add_lwpolyline(...)`/`.add_polyline2d(...)`/`.add_circle(...)`/
`.add_line(...)`/`.add_text(...)`/`.blocks.new(...)`, `doc.header['$INSUNITS'] = ...`,
`doc.saveas(...)`) -- never a hand-authored raw-tagged-text file.

Coverage:
- Pure math (`section_properties()`): the worked-example triangle (CCW), the same triangle
  reversed (CW, the sign-flip check above), zero-area/collinear rejection, fewer-than-3-distinct-
  vertices rejection, and a self-intersecting polygon (see Defects -- this one currently fails).
- Criterion 1 (purely additive): a sheet with only "value"/"formula" components (no cad-profile
  at all) evaluates normally.
- Criterion 2: the worked-example DXF fixture, all 13 scalar output ports plus `outline`'s exact
  3x2 shape and values, checked against the independently re-derived numbers above.
- Criterion 2 repeated end-to-end for the CW fixture (see above).
- Criterion 3: missing `$INSUNITS`, explicit `unit="mm"` override gives identical results.
- Criterion 4: a two-layer fixture (triangle on `"profile"`, an independently-defined 10x10
  square -- area 100, centroid (5,5), hand-computed separately -- on `"scrap"`); `layer="profile"`
  and `layer="scrap"` each select only their own shape.
- Criterion 5: blank path -> exact error text.
- Criterion 6: blank layer with two candidates -> exact "Multiple closed profiles..." text.
- Criterion 7: a lone `CIRCLE` -> exact "curved segments or separate line segments..." text; plus
  three edge-case variants of the same scope boundary: a lone standalone `LINE`, a bulged-segment
  `LWPOLYLINE`, confirming the same message family.
- Criterion 8: missing `$INSUNITS`, no override -> exact "no usable unit information..." text;
  parametrized over every documented not-directly-mapped `$INSUNITS` code (0, 8, 9, 99) as well.
- Criterion 9: `unit="banana"` -> exact "Unknown length unit 'banana'; ..." text.
- Criterion 10: `P1.area -> F1.a`, `F1` a "Formula" component with `expr="a"` -- `F1.result`
  matches `P1.area`'s magnitude and dimension exactly, through the real `wiring.evaluate()` graph,
  zero special-casing anywhere. A second case feeds `P1.area` into `expr="a + 1"` and confirms the
  existing engine's `"Units do not match"` fires unchanged.
- Criterion 11: a full `.lsheet` save/close/reopen round trip through the real `Worksheet` (not
  just `wiring.evaluate()` directly) -- `add_component_region`, `to_document()`, `SheetDocument.
  save()`/`.load()`, a fresh `Worksheet.load_document()` -- confirms kind/name/config round-trip
  exactly and the outputs recompute automatically with no further user action, headless under
  `QT_QPA_PLATFORM=offscreen`.
- Edge cases from the spec's own "Edge cases" section: a nonexistent path (`"Could not open DXF
  file: ..."`, confirmed `<= 160` chars); a corrupted/non-DXF file (`"Could not read DXF file:
  not a valid DXF file."`); an entity set with nothing geometric at all (lone `TEXT`) and a truly
  empty entity set, both giving the exact "No closed profile found..." text; `BLOCK`/`INSERT`
  entities never traversed (a profile defined only inside a block, referenced via `INSERT`, is
  invisible -- modelspace has only the `INSERT` entity, so the result is "No closed profile
  found..."); Z-coordinates on a 2D `POLYLINE`'s vertices (group code 30) read and ignored,
  giving identical results to the same loop with Z=0 everywhere; both recognised loop entity
  kinds (`LWPOLYLINE` and 2D `POLYLINE`) independently confirmed to work.

## Results

`QT_QPA_PLATFORM=offscreen pytest -q`, run three times for stability:

**Before (baseline, confirmed matches the manager's own report exactly): 1408 passed, 2 xfailed,
0 failed.**

**After adding this review's 32 new cases: 1439 passed, 2 xfailed, 1 failed** (stable across all
three runs; the 1 failure is a new, genuine defect this review found -- see Defects below, not a
flake). 1439 - 1408 = 31 newly passing + 1 newly (and correctly) failing = 32, matching the new
file's own case count exactly. No regressions anywhere else in the suite.

Isolated run of just this review's own file: `tests/test_cadprofile_blackbox.py`, 31 passed, 1
failed.

## Failing case (defect, not a flake)

**`test_section_properties_self_intersecting_does_not_crash`**

- Spec text (Edge cases): *"A self-intersecting (non-simple) closed polyline: ... This phase does
  not detect self-intersection; a self-intersecting input produces a mathematically meaningless
  but **non-crashing** numeric answer."*
- Input: `section_properties([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (14.0, 0.0)])` -- a genuinely
  self-intersecting quadrilateral (two edges cross), with a non-zero signed area (-20; confirmed a
  *symmetric* bowtie's crossing cancels to exactly zero net signed area by hand first, so this
  asymmetric one was chosen specifically to avoid tripping the zero-area check for an unrelated
  reason).
- Expected (per spec): a finite, non-crashing numeric answer (meaningless is fine, a crash is
  not).
- Actual: an uncaught `ValueError: expected a nonnegative input, got -91.66666666666666`, raised
  from `cadprofile.py`'s `rx = math.sqrt(ixx / area_abs)` -- a self-intersecting loop can make the
  (meaningless, by the spec's own admission) `Ixx`/`Iyy` come out **negative**, and neither
  `rx`'s nor `ry`'s `sqrt()` call has any guard against that.
- Through the *whole* component path (`wiring.evaluate()`, same fixture written via ezdxf as a
  real `.dxf` file), this does **not** crash the application -- `wiring.evaluate()`'s broad
  `except Exception` clause catches it and surfaces a `ComponentResult("error", ...)` with the
  raw Python message leaking through: `error = 'expected a nonnegative input, got
  -91.66666666666666'`. So there is no process crash visible to a user, but the component ends up
  in an **error** state with a confusing, internals-leaking message, which contradicts the spec's
  own stated intent of still producing "a mathematically meaningless but non-crashing numeric
  answer" (i.e. an **ok** state with some number, not an **error** state at all).
- Minimal repro (pure function, no DXF needed):
  ```python
  from livesheet.engine.cadprofile import section_properties
  section_properties([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (14.0, 0.0)])
  # ValueError: expected a nonnegative input, got -91.66666666666666
  ```
- Severity: low/moderate. Self-intersecting input is already a documented known limitation the
  spec says is "not fixed here," and the failure mode is a clean, contained error state rather
  than an application crash -- but the *specific* behaviour (error state with a leaked internals
  message, rather than the spec's own stated "non-crashing numeric answer") does not match the
  spec text as written, and a real user drawing an accidentally self-crossing profile in their CAD
  tool would see a cryptic Python exception string rather than a clean "unsupported" message or a
  (meaningless but harmless) number.
- Suggested fix for the developer (not applied by this review, per instruction): either (a) guard
  `rx`/`ry` with `math.sqrt(abs(...))` or similarly tolerant handling so a negative `Ixx`/`Iyy`
  still produces *some* finite number, matching the spec's literal wording, or (b) if the intent
  is instead to treat this as a recognised error case, add an explicit, user-facing
  `CadProfileError` (not a raw `ValueError`) for a negative post-formula `Ixx`/`Iyy`, with
  wording consistent with every other error message's house style -- either resolves the gap
  between the spec's stated behaviour and the current one; this review takes no position on which
  the manager/Theo would prefer, since it isn't specified either way.
- Left as a genuinely failing assertion in the new test file (not `xfail`), per this project's
  convention of keeping a known gap visible in the test run rather than silently marked-expected.

## Acceptance criteria

1. PASS. A sheet with only "value"/"formula" components (no cad-profile referenced at all)
   evaluates exactly as before.
2. PASS. Worked-example triangle, no overrides: all 13 scalar ports plus `outline`'s 3x2 shape
   match the independently re-derived numbers above, within `rel=1e-6`.
3. PASS. Missing `$INSUNITS` + explicit `unit="mm"` gives identical results to criterion 2.
4. PASS. Two-layer fixture: `layer="profile"` selects the triangle (criterion 2's numbers),
   `layer="scrap"` selects the independently-defined square (area 100, centroid (5,5)).
5. PASS. Blank `path` -> exact `"No DXF file path set."`.
6. PASS. Blank `layer` with two candidates on the same fixture -> exact `"Multiple closed profiles
   found on this drawing; set 'layer' to pick one."`.
7. PASS. A lone `CIRCLE` -> exact `"This profile uses curved segments or separate line segments,
   not yet supported by this component (phase 1 supports one closed straight-sided polyline
   entity only)."`.
8. PASS. Missing `$INSUNITS`, no override -> exact `"Drawing has no usable unit information; set
   'unit' in this component's configuration, e.g. 'mm'."`.
9. PASS. `unit="banana"` -> exact `"Unknown length unit 'banana'; use one of LiveSheet's existing
   length units, e.g. 'mm', 'm', 'inch'."`.
10. PASS. `P1.area -> F1.a` (Formula, `expr="a"`): `F1.result` equals `P1.area` exactly (magnitude
    and dimension both checked), through the real wiring graph, zero special-casing. A second
    check (`expr="a + 1"`) confirms the existing `"Units do not match"` still fires unchanged for
    this kind's outputs.
11. PASS. Full `.lsheet` save/close/reopen round trip through a real `Worksheet`: kind, name, and
    all three config values round-trip exactly; outputs recompute to the same values with no
    further user action; `SheetDocument.version() == 3` as specified.

## Edge cases

All PASS except the self-intersecting case (see Defects): nonexistent path, corrupted/non-DXF
file, text-only/empty entity sets, `BLOCK`/`INSERT` non-traversal, Z-coordinate ignored on 2D
`POLYLINE` vertices, both recognised loop entity kinds (`LWPOLYLINE`/2D `POLYLINE`), every
documented not-directly-mapped `$INSUNITS` code, a bulged-segment polyline and a standalone `LINE`
both correctly recognised as the same "curved/separate-line, out of phase-1 scope" case, an
incompatible-unit downstream mix giving the engine's existing message unchanged.

One wording-ambiguity note, not filed as a defect: the spec's general edge-case paragraph says
*"any polyline with a nonzero bulge or that is not marked closed... [is] out of this phase's
scope,"* but the specific "Zero candidates" bullet's enumerated trigger list for the curved-
segments error message only names `ARC`/`CIRCLE`/bulged-segment/standalone `LINE`, not explicitly
"an open (not-closed) polyline." The implementation treats an open polyline the same way (same
error message), which is a reasonable, defensible reading of the general paragraph -- not tested
as a numbered defect since the spec's own wording is the ambiguous part, not the implementation,
but flagged here for the record in case the manager wants the "Zero candidates" bullet's wording
tightened to explicitly list this case too.

## IP red flags

None found. Grepped `livesheet/engine/cadprofile.py`, the touched parts of
`livesheet/engine/wiring.py`, and `livesheet/gui/componentdialog.py` for vendor names
(`autocad`, `mathcad`, `mathematica`, `maple`, case-insensitive) and found none in any code,
comment, or user-facing string. The component-kind label (`"CAD profile (DXF)"`), config keys
(`path`/`layer`/`unit`), and every error message are original, generic wording consistent with
the spec's own IP check -- "DXF" is used the same way "CSV"/"PDF" already are elsewhere in this
codebase, never as a vendor-identifying string. No vendor UI, icon, workflow, or example drawing
referenced anywhere in the new/changed code. Confirmed `wiring.format_output()`'s known,
pre-existing Matrix-value crash (already logged in `docs/board/decisions.md`'s spec-013-
implementation entry and flagged for `backlog.md`) is real and would also affect `outline`'s own
matrix-shaped output if anything ever called `format_output()` on it -- but grepped and confirmed
`format_output()` is not called anywhere in `livesheet/gui/` today (defined, exported, never
invoked), so this stays dormant/inactive for this spec exactly as the manager's note already
said; not a new finding, just independently re-confirmed rather than taken on faith.

## Coverage gaps

- **No real-window/computer-use pass this session.** This session's tool set did not include any
  `computer_*` tool (confirmed by checking the available tool definitions directly, not assumed),
  so Theo's standing instruction to also drive the real app on his Mac (place a "CAD profile
  (DXF)" component, Browse to a small on-disk test file, confirm the output values and error
  states render live, wire `area` into a "Formula" component and confirm the value flows through)
  could not be carried out this session. Everything in this review was verified headlessly
  (`QT_QPA_PLATFORM=offscreen`), including the criterion-11 round trip which exercises the real
  `Worksheet`/`ComponentRegion`/`SheetDocument` production code paths end to end -- a materially
  stronger check than `wiring.evaluate()` alone, but still not the same as watching pixels on a
  real screen. A real pass should specifically watch: the `AddComponentDialog`'s "CAD profile
  (DXF)" page (Path/Layer/Unit fields, the Browse... button's real native file picker, not the
  mocked one this project's existing tests use), a component's port labels/error-state `⚠`
  rendering live on the canvas for the bad-path and bad-unit cases, and a drawn wire from `area`
  into a Formula component's input actually updating the Formula's displayed result on screen.
- The GUI dialog's own field round-trip (kind selection, Browse-button mocking, OK -> config
  dict) was not independently re-tested in this review's new file -- the developer's own
  `tests/test_wiring_gui.py` additions already cover this surface and this review's criterion-11
  test independently re-exercises the same `ComponentRegion`/`Worksheet` machinery from a
  different angle (document round trip rather than dialog field entry), so this was judged
  adequately covered rather than a priority to duplicate a third time; flagged here rather than
  silently skipped.
- Performance/large-file behaviour (the spec's own flagged "re-read and re-parsed every
  recalculation pass, no caching" known limitation) was not probed -- consistent with the spec
  itself deferring it, not a defect.
- No fuzz/property-based testing of arbitrary polygon shapes against an independent
  computational-geometry library; the numeric checks here are all against the one worked example
  (plus the independently-chosen square and self-intersecting quad), not a broad sweep.

## Recommendation

Spec 013 (DXF profile import, phase 1) is functionally sound: all 11 numbered acceptance criteria
pass under independent black-box testing, with every numeric output independently re-derived and
cross-checked (not trusted from the spec's or the implementation's own numbers), and the
developer's disclosed clockwise-winding sign-flip fix independently re-verified as correct both
in isolation and through the full wiring/DXF path. One new, low/moderate-severity defect was
found: a self-intersecting input (an already-documented, not-fixed-here known limitation) can
make `Ixx`/`Iyy` go negative and crash `math.sqrt()` with an uncaught `ValueError`, which
`wiring.evaluate()`'s broad exception handler contains (no application crash) but surfaces as an
error state with a leaked internals message, rather than the spec's stated "non-crashing numeric
answer." Not a blocker for any of the 11 numbered criteria. The full suite is stable at 1439
passed / 2 xfailed / 1 failed across three consecutive runs (1408 passed / 2 xfailed / 0 failed
baseline, +32 new cases: 31 pass, 1 is this review's own documented-and-left-failing defect
repro). No IP red flags found in the new/changed code. A real-window manual pass on Theo's Mac is
still needed before calling spec 013 fully verified end-to-end -- this session had no computer-use
tool available to do it, so it remains an open, explicitly-flagged gap rather than something
silently skipped.
