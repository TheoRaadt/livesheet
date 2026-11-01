# Review 014: DXF profile import, phase 2 (tester, black-box)

Spec: `docs/board/specs/014-dxf-profile-geometry-extensions.md` -- extends spec 013's single-loop
`"cad-profile"` component with standalone `ARC`/`CIRCLE` tessellation, `LWPOLYLINE`/`POLYLINE`
bulge-segment tessellation, `LINE`-chaining into a closed loop, and composite (outer + holes)
sections. No new dependency, no new config keys/output ports/`.lsheet` change. Implemented by the
developer (see `docs/board/log.md`'s 2026-10-30 "finished spec 014" entry), which also fixed a
real sign bug in `_tessellate_bulge_segment` (`theta = -4*atan(b)` -> `theta = 4*atan(b)`) and
retired/updated 4 stale pre-spec-014 tests in `tests/test_cadprofile_blackbox.py`.

This review picks up a session that was stopped mid-write (see `docs/STATUS.md`'s "In flight:
spec 014" section): no `docs/board/reviews/014-...md` or log.md entry existed for it, but it left
one real artifact, `tests/test_cadprofile_spec014_blackbox.py` (39 cases, all green), plus one
documentation-only note recorded inside that file. Per the task, none of this was taken on trust:
the spec was re-read in full and re-derived from scratch independently, the bulge-direction fix
was re-checked with a *second, differently-derived* formula (not the interrupted session's own),
the 4 retired tests were checked against the spec's own text directly, and a few edge cases
outside both existing test files were probed for defects.

New/changed files under test: `livesheet/engine/cadprofile.py` (extended), `livesheet/engine/
wiring.py` (`outline`'s multi-loop concatenation only). New test files: `tests/
test_cadprofile_spec014_blackbox.py` (39 cases, from the interrupted session, kept and verified,
not re-derived from the implementation) and this review's own `tests/
test_cadprofile_spec014_review_addendum.py` (9 new cases).

## Independent re-derivation of the bulge-direction sign convention (from scratch, second route)

The task specifically asked not to just trust the interrupted session's own derivation. Re-derived
the DXF-documented bulge definition (`bulge = tan(included_angle/4)`, signed: positive = CCW
traversal from `p0` to `p1` around the arc's own centre) via a **different algebraic route** from
the implementation's own `tan(theta/2)`-centre-offset construction: radius from the standard
chord/half-angle relationship `r = d / (2*sin(theta/2))`, centre placed by an explicit signed
offset along the chord's own unit normal, using the independently-stated fact "the centre of a
counter-clockwise arc is always 90 degrees to the left of the direction of travel." Verified this
"left of travel" fact itself by hand, concretely, with a simple chord along +x (not reused from
any test file): a short CCW arc from `(0,0)` to `(2,0)` has its centre *above* the chord (left of
rightward travel) and the arc itself bulges *below* the chord -- i.e. to the right of travel,
away from the centre. Combined with the standard "interior is to the left of travel on a CCW
polygon" fact, this means a positive bulge on a CCW polygon's edge bulges *outward* (to the right
of travel, away from the interior) -- independently confirms the direction the disclosed fix
produces, without reading the fix's own code or docstring derivation first.

Ran this second oracle (`tests/test_cadprofile_spec014_review_addendum.py`'s
`_oracle_bulge_tessellate`) against `_tessellate_bulge_segment` for 6 `(p0, p1, b)` triples,
including the exact asymmetric 013-triangle edge the disclosed bug actually affected (`(0,0)`-
`(40,0)` with bulge `+-0.5`) and a fully generic oblique edge with no symmetry at all (`(3,-2)`-
`(-5,7)`, bulge `+-0.37`) -- every point matches bitwise (`rel=1e-9`). Also independently confirmed
the asymmetric-triangle numeric target: bulging the `(0,0)-(40,0)` edge of the area-400 triangle
outward with bulge `0.5` gives `676.817683` mm^2 (own oracle's own points, own shoelace sum, not
copied from the spec, the developer's log entry, or either existing test file -- matches the
developer's disclosed "~676.8 mm^2" to full precision). This is independent confirmation, by a
second method, that the fix is correct -- not a re-run of the interrupted session's own checks.

## Verifying the 4 retired/updated tests in `tests/test_cadprofile_blackbox.py` against the spec text

Read the spec's own "Multiple closed loops" section directly (not the developer's log-entry
explanation) before deciding:
1. **Two same-layer, same-winding (both CCW) candidates now give the winding-mismatch error, not
   013's generic "multiple profiles found" message.** Spec text, acceptance criterion 2's bullet
   list: "A loop other than the single largest is also counter-clockwise, or the one largest loop
   is clockwise" -> the winding-mismatch error. Two CCW loops: the largest is accepted as a
   candidate outer, but the second being CCW too hits this exact bullet. **Correctly updated.**
2. **A standalone `CIRCLE` now resolves `ok` (tessellated 36-gon), not phase 1's "curved segments
   ... not yet supported" error.** Spec's scope note (a): "standalone `ARC` and `CIRCLE` entities,
   tessellated into straight segments." **Correctly updated.**
3. **A single standalone `LINE` is still an error, but now the more specific `LINE`-chaining
   message.** Spec's own "Behaviour" section: a `LINE` set assembles into a loop only if every
   node has degree exactly 2; one `LINE` gives both its endpoints degree 1 -> the chaining error,
   by the spec's own stated rule, not phase 1's generic message. **Correctly updated.**
4. **A closed `LWPOLYLINE` mixing a straight and a bulge segment now resolves `ok`.** Spec's own
   edge cases: "A `LWPOLYLINE` that mixes some zero-bulge ... and some nonzero-bulge ... segments
   is fully supported here (013 only handled the all-straight case)." **Correctly updated.**

All 4 retirements match the spec's own text exactly, independently confirmed by reading the spec,
not by trusting the developer's log-entry summary of its own changes (which turned out to describe
the same conclusion, but that was checked, not assumed).

## Tests added

`tests/test_cadprofile_spec014_review_addendum.py`, 9 new cases:
- A second, independently-derived bulge-tessellation oracle (different formula from both
  `_tessellate_bulge_segment` and the interrupted session's own test file), bitwise-matched
  against the implementation on 6 `(p0, p1, b)` triples, including a fully asymmetric oblique
  edge with no symmetry to mask a sign flip.
- The exact asymmetric-triangle numeric target the disclosed bug affected, computed independently.
- Two genuinely degenerate `LINE`-chaining inputs not present in either existing test file: a
  single zero-length `LINE` (both endpoints coincide within tolerance) and two duplicate parallel
  `LINE` entities sharing identical endpoints -- both mechanically pass the chaining walk (a
  1-node or 2-node "loop") and must then be rejected cleanly by the downstream zero-area check,
  not crash or silently produce a bogus profile. Confirmed both behave this way (see Coverage
  notes below -- not filed as a defect, since there is no crash and no wrong nonzero answer, just
  a less-specific error message than the `LINE`-chaining one for this bizarre degenerate case).

Kept `tests/test_cadprofile_spec014_blackbox.py` (the interrupted session's 39 cases) as-is after
independently re-deriving its central claims myself (see above) rather than assuming it was
sufficient on its own, per the task's explicit instruction.

## Results

`QT_QPA_PLATFORM=offscreen pytest -q`:
- Baseline confirmed matches the manager's reported state exactly: **1633 passed, 2 xfailed, 0
  failed.**
- After adding this review's 9 new cases: **1642 passed, 2 xfailed, 0 failed** (1642 - 1633 = 9,
  matching the new file's own case count exactly; stable, re-run twice). No regressions anywhere
  else in the suite.

## Acceptance criteria

1. PASS. A standalone `CIRCLE` (centre `(0,0)`, radius `10`, `$INSUNITS=4`) tessellates to a
   36-gon: `area = 312.567 mm^2` (independently re-derived as `36 * 0.5 * 10^2 * sin(10deg)`,
   confirmed `< pi*10^2`), `centroid_x = centroid_y = 0`, `ok` status -- both as a pure function
   and through the full wiring path, in mm/cm/m.
2. PASS. The bulge semicircle example (`(-10,0)` bulge `1.0` to `(10,0)`, bulge `0` back):
   `area = 900*sin(10deg) ~= 156.283 mm^2`, independently re-derived via an 18-triangle
   origin-decomposition. The spec's own prose names the wrong semicircle side for this example
   (documentation-only note, not re-litigated here -- already correctly recorded as non-blocking
   in the existing test file, since the criterion's only numeric check, area, is direction-
   agnostic; independently re-confirmed via this review's own "centre is left of CCW travel"
   derivation, which agrees with the existing note).
3. PASS. Four `LINE` entities forming a 40x20mm rectangle chain into one closed loop (confirmed
   order/direction-independent via a scrambled/reversed-endpoint fixture, not just the spec's own
   forward-order example): `area = 800 mm^2`, `centroid = (20, 10) mm`, `Ixx = 26666.7 mm^4`
   (`40*20^3/12`), `Iyy = 106667 mm^4` (`20*40^3/12`) -- cross-checked against the standard
   rectangle formulas directly, not just the shoelace code path.
4. PASS. The same rectangle with a gap (third `LINE` shortened) errors with the exact text
   `"Could not assemble a single closed loop from LINE entities on this layer."`.
5. PASS. The 40x20 outer rectangle plus a centred 10x10 hole (both `LWPOLYLINE`, outer CCW, hole
   CW): `area = 700 mm^2`, `centroid = (20, 10) mm` unchanged by symmetry, `Ixx = 25833.3 mm^4`,
   `Iyy = 105833.3 mm^4` -- independently re-derived both the spec's own centred-hole case and a
   second, off-centre-hole composite example from scratch with the standard composite-section
   method (sum of sub-areas/moments + parallel-axis theorem), confirming the implementation's
   "sum origin-referenced moments across loops, then centroid-divide once" approach is
   mathematically equivalent, not just numerically coincidental for the symmetric case.
6. PASS. The same fixture with the hole also wound CCW: exact winding-mismatch error text.
   Additionally confirmed the "one largest loop is clockwise" sibling (outer CW, hole CW too)
   hits the same error, per the spec's own bullet listing both triggers.
7. PASS. The hole moved to stick out past the outer rectangle's right edge: exact containment-
   failure error text. Also independently checked the boundary/tie case (hole bbox touching the
   outer's edge exactly) is accepted, a reasonable reading of "entirely inside" the spec's prose
   does not forbid, not filed as a defect.
8. PASS. Spec 013's own worked right-triangle example re-derived independently a second time
   (separately from the 013 review's own numbers) and confirmed unaffected through the full
   wiring path; `section_properties([one_loop])` confirmed bit-identical to the pre-014 single-
   loop call shape, directly supporting the spec's own "013's single-loop case needs no code-path
   change" claim.

## IP red flags

None found. Grepped `livesheet/engine/cadprofile.py`, the touched parts of `livesheet/engine/
wiring.py`, and `livesheet/gui/componentdialog.py` for vendor names (`autocad`, `mathcad`,
`mathematica`, `maple`, case-insensitive); the one hit (`"mathematically"` inside a code comment)
is a false positive, not a vendor reference. No new config keys, output ports, or user-facing
strings beyond the spec's own two new error messages (`"Could not assemble a single closed loop
from LINE entities on this layer."`, `"Loop winding does not match the outer/hole convention
..."`, `"A hole loop extends outside the outer profile's boundary."`), all original wording. No
vendor UI, icon, workflow, or example drawing referenced anywhere in the new/changed code.

## New defects found

**None that block any numbered acceptance criterion.** Two minor, low-severity robustness notes
found while probing edge cases outside both existing test files' coverage, neither of which
crashes or produces a silently-wrong nonzero answer:

- **Degenerate `LINE` inputs get a less-specific error message than expected, but no crash.** A
  single zero-length standalone `LINE` (both endpoints coincide within the `1e-6` chaining
  tolerance) or two duplicate parallel `LINE` entities (identical endpoints) both mechanically pass
  `_assemble_lines_into_loop`'s degree-2/single-cycle walk (producing a 1- or 2-vertex "loop"
  respectively), rather than being rejected by the chaining logic itself with the spec's own
  `"Could not assemble a single closed loop..."` message. They are still caught, cleanly, by the
  downstream `"Profile has zero area."` check inside `section_properties` (the loop never reaches
  the composite path since it's the only candidate) -- so there is no crash and no wrong nonzero
  result, just a different, still-accurate error message for an input degenerate enough that no
  real CAD drawing would plausibly produce it (a drawn, zero-length or exactly-duplicated line
  segment). Not filed as a blocking defect; noted for visibility since the spec's own stated
  intent for `LINE`-chaining failures is specifically the chaining message, and this is a case
  where that intent doesn't quite hold, though the actual user-facing outcome (a clean, accurate
  error, not a crash or wrong answer) is the only thing the spec's acceptance criteria test for.
  Minimal repro: `_assemble_lines_into_loop([((5.0,5.0),(5.0,5.0))])` returns `[(5.0,5.0)]` (not an
  error); `section_properties([[(5.0,5.0)]])` then raises `CadProfileError("Profile has zero
  area.")`.
- **Full-circle `ARC` detection uses exact float equality (`included == 0.0`), no tolerance.** A
  standalone `ARC` is only treated as a closed (full-circle-equivalent) loop candidate when
  `(end_angle - start_angle) % 360.0 == 0.0` exactly. A file written by `ezdxf`'s own API (as every
  fixture in both test files is) always produces bit-exact `0.0`/`360.0` values, so this never
  triggers in any tested fixture -- but a DXF file from a different real-world export pipeline
  with a tiny floating rounding error on `start_angle`/`end_angle` (e.g. `359.9999998` instead of
  `360.0`) would fall through to the "not a closed loop, scope boundary" path instead of being
  recognised as a full circle, even though it is visually and practically one. Not triggered by
  anything in this spec's own fixtures or acceptance criteria (which only use `ezdxf`-generated,
  bit-exact angles), and the spec itself specifies the rule in terms of exact degree values with
  no tolerance of its own to implement against -- so this is a theoretical robustness gap rather
  than a concrete reproduction against the spec as written, flagged for visibility only (same
  general category as the spec's own flagged `LINE`-chaining-tolerance open question, just for a
  case the spec doesn't discuss at all).

## Coverage gaps

- **No real-window/computer-use pass this session.** Checked this session's available tool
  definitions directly (not assumed): no `computer_*` tool was present, so Theo's standing
  instruction to also drive the real app on his Mac (place a "CAD profile (DXF)" component,
  import a drawing with a circular/bulged profile and one with a hole, confirm the outputs and
  the two new error messages render live) could not be carried out. This remains an explicitly
  open gap, not silently skipped -- flagging it to the manager rather than marking spec 014 fully
  verified end-to-end.
- **Equal-area tie-break between candidate outer and hole loops is untested and unspecified.**
  `_validate_composite` picks the outer loop via `max(..., key=lambda i: abs(areas[i]))`, which
  resolves an exact tie by list/entity order (first-seen wins); the spec's own text doesn't
  address the tie case at all (it assumes "the largest" is well-defined). Confirmed this doesn't
  silently produce a wrong answer for any geometry this review could construct (a genuine tie
  with one loop's bbox contained in the other's either passes or fails symmetrically depending on
  which fixture is tried), but a true floating-point-exact tie between two visually-different-size
  loops is extremely unlikely from real drawings; not pursued further as a priority.
- No property-based/fuzz testing of arbitrary polygon shapes with multiple holes against an
  independent computational-geometry library -- all numeric checks here (and in the kept 39-case
  file) are against hand-derived worked examples, not a broad randomized sweep.
- Performance/large-entity-count behaviour of `LINE`-chaining's O(n^2) node-matching loop
  (`node_index`'s linear scan over all existing nodes per new endpoint) was not probed -- plausible
  to matter for a drawing with hundreds of `LINE` segments, but out of this spec's own stated
  scope (no performance claim is made in the spec).

## Recommendation

Spec 014 (DXF profile import, phase 2) is functionally sound: all 8 numbered acceptance criteria
pass under independent black-box testing, with the bulge-direction sign-flip fix independently
re-verified correct via a *second, differently-derived* formula (not a re-run of the interrupted
session's own route) on several genuinely asymmetric shapes -- the exact class of bug this phase
just fixed. The 4 tests retired/updated in `tests/test_cadprofile_blackbox.py` were checked
directly against the spec's own text (not the developer's summary of its own change) and are all
correct. No blocking defects found; two low-severity robustness notes recorded above for
visibility (degenerate zero-length/duplicate `LINE` inputs get a less-specific but still accurate
error; full-circle `ARC` detection has no float tolerance, untriggered by any current fixture). The
suite is stable at 1642 passed / 2 xfailed / 0 failed (1633 baseline + this review's own 9 new
cases, all passing; the kept 39-case file from the interrupted session also verified independently
rather than trusted). No IP red flags found. A real-window manual pass on Theo's Mac is still
needed before calling spec 014 fully verified end-to-end -- this session had no `computer_*` tool
available, confirmed directly, so it remains an open, explicitly-flagged gap rather than something
silently skipped.
