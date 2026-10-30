# Decisions and open questions

## Decided
- 2026-10-27 Agents + skills live in the repo (.claude/agents, .claude/skills)
- 2026-10-27 Licence: dual MIT OR Apache-2.0 (Theo decided both)
- 2026-10-27 IP: clean-room from public docs only
- 2026-10-27 First milestone focus: engineering calculations

## Open
- Product name check: "LiveSheet" trademark search
- Notation review: README uses :=, ≡, → (common math notation, but review ≡ global and "→ keyword" against IP policy)
- Own file extension/format stays .lsheet (JSON)

## Open after specs 001-003 (2026-10-27)
- Notation review must now also cover: `to`/`step`/`table` (001), `[1,2;3,4]` + 1-based indexing (002), `vary/settle/least/most` + trailing `in <name>` (003)
- README roadmap line `i := 0..10` conflicts with 001 (`to`/`step`); recommend change roadmap to `to`/`step`
- 001: ranges only usable inside `table` for now; cap of 10000 values OK?
- 002: `[12x12 matrix]` placeholder above 10x10 OK? NumPy allowed in 002b? LU/QR/SVD need multi-result syntax (later)
- 003: scipy (BSD-3, ~40-60 MB with numpy) as dependency? Recommended yes; names vary/settle/least/most OK? GUI freeze on slow models accepted for now?
- Spec numeric examples were hand-derived, not yet run: tester must verify them against SymPy/SciPy before developer relies on them

## Decided 2026-10-27 (after specs)
- README roadmap uses `to`/`step`, not `..`
- scipy approved (BSD-3); names vary/settle/least/most OK; 1-based indexing OK; `[NxN matrix]` placeholder >10x10 OK
- Order: 001 -> 002a -> 003; tester verifies spec numbers first; tester opens/closes the real windows itself
- 2026-10-27 numpy approved as direct dependency (BSD-3)
- 2026-10-27 `f(M) := det(M)` (deferred matrix evaluation in function bodies) postponed to backlog; unit mismatch in `C := A + B` reported at display only

- 2026-10-27 GUI layout: results/tables/grids may overlap regions below them for now; backlog item 'push-down layout / reserved result space' (M2). Wide symbolic grids: no wrapping yet.
- 2026-10-27 Save As/Export default to last-used folder or Documents; consider unique default name
- 003 spec fix: example message for infeasible `x^2 + 1 == 0` is 5.0e-01 under the spec's own normalisation

## Open 2026-10-28 (spec 004 plots) — manager recommendation in brackets
- Renderer: QPainter directly vs matplotlib vs pyqtgraph [QPainter: no new dependency, one path for screen/PDF/PNG]
- Text-spec editing (`plot / over / show ...`) for phase A, form dialog later [yes]
- Plot keywords `over`, `show`, `xlim`, `ylim`, `xunit`, `yunit`, `against`, `mode polar` [OK; include in the pre-1.0 notation review]
- `.lsheet` version 2 only when a plot is present [yes]
- Second y axis: separate spec later [yes, two plots meanwhile]
- Default display unit = unit the formatter prints for the first point [yes, consistent with `=`]
- Defaults 101 points, 400 x 260 [OK]
- Plot may overlap regions below until backlog 20 [accept for phase A]
- PNG/SVG export of one plot [backlog extra]
- Manager decision: phase A1 (engine only, renderer-independent) may start on these recommendations

## Decided 2026-10-28 (Theo, plot editing UI)
- Spec 005 (inline placeholder slots drawn directly on the chart's axes) is superseded, not implemented. Reason: spec 004's own IP check had deliberately avoided that exact interaction style (live placeholder editing on an inline chart's axes) as a known patent-sensitive technique in this product category.
- Replacement direction: a pop-up dialog after `Insert > Plot` / double-click, with labelled fields (Function(s), Variable(s), X min/max, Y min/max) that compiles to the same `plot`/`over`/`show`/`xlim`/`ylim` text spec 004 already parses. A labelled-field dialog is a generic, ubiquitous UI pattern (Excel chart wizard, MATLAB, LibreOffice Calc, any properties dialog), materially lower IP risk than inline chart-axis placeholders; spec 004 itself already named a dialog-based editor as a natural safe follow-up.
- mathcad-specialist writing a new spec for this dialog-based design (replacing 005).

## Decided 2026-10-28 (Theo, spec 006 plot dialog)
- Variable(s) is one field (name + sampling settings), not literally several x-variables: confirmed.
- X unit / Y unit as two extra fields beyond the four Theo named: confirmed, keep.
- Title / X label / Y label as three more optional fields rather than raw-text-only: confirmed, keep.
- Apply updates the live region beside/behind the dialog, no embedded preview inside the dialog itself: accepted for now.
- (Remaining lower-stakes items — error-attribution heuristic, the extended "representable" rule, keeping "Use dialog..." in the raw editor — follow the specialist's own recommendations, all "keep/accept", not separately queried.)
- IP: manager agrees with the specialist's own-assessment pass — a modal field dialog is generic chrome, materially lower risk than spec 005's inline placeholders; no vendor layout/wording used. Not legal advice.
- Spec 006 is approved; assigned to developer.

## Decided 2026-10-28 (Theo, spec 004)
- Renderer: QPainter directly (no new dependency)
- `.lsheet` version 2 only when a plot is present
- Plots may overlap regions below until backlog 20 (push-down layout)
- Other 004 questions follow the manager recommendations above unless Theo says otherwise

## Decided 2026-10-29 (Theo, spec 007 main window)
- Side panel tab names confirmed: Symbols / Outline / Data (not "Datasets"). Backlog 7a/8a build their content into Outline/Data.
- Spec 007 fully approved (IP check pass, all open questions resolved); assigned to developer.

## Decided 2026-10-29 (manager, spec 008 matrix dialog)
- IP check: pass, manager's own review agrees with specialist's self-assessment — generic size-picker/grid-of-cells dialog, no vendor material, lower risk than spec 006 (no live-preview/Apply at all).
- Accepted all 6 of the specialist's own recommendations without separately querying Theo (all low-stakes, well-justified): (1) double-click keeps its existing universal "start inline edit" meaning for every math region; the new Grid dialog is reached only via "Edit as grid..." (context menu) and Insert > Matrix/"Matrix here" — not a double-click override, since MathRegion (unlike PlotRegion) holds free text that may or may not be a matrix; (2) no in-place "Use dialog..." button inside the compact single-line inline editor; (3) a post-commit engine error (e.g. undefined symbol) surfaces on the region itself, not back inside the dialog — no per-field live attribution since there's no Apply/preview to attribute to; (4) grid-size cap 1-20 x 1-20; (5) "Define as" offers both `:=` and `≡` (Global); (6) cursor-position insertion into an open expression is out of scope for this slice.
- Spec 008 fully approved; queued for developer behind spec 007 (main window, in progress) per "developer works one spec at a time."

## Decided 2026-10-29 (Theo, modeling/wiring feature)
- IP approach: base the visual "place components and wire them together" feature on generic, decades-old public-domain concepts (block diagrams, signal-flow graphs, spreadsheet dependency graphs, pipe-and-filter architecture) rather than cloning any specific named commercial dataflow/wiring product. No new vendor added to docs/IP-POLICY.md; no legal review needed for this route.
- User-authored script components run via QJSEngine (PySide6/QtQml), reusing the already-approved PySide6 dependency rather than adding a new JS engine; sandboxed by default (no filesystem/network access unless explicitly bound later).
- "Other LiveSheet" components are nested sub-components: a whole .lsheet file embedded as a reusable block with its own inputs/outputs, wireable like any other component (not just a single value read from another file). Touches the .lsheet format (recursion/versioning) — flagged for the spec to work out.
- New dedicated agent: modeling-specialist (writes specs only, like the other specialists), backed by a new modeling-concepts skill grounded only in the generic concepts above.

## Decided 2026-10-29 (manager, spec 007 implementation)
- Accepted both of the developer's disclosed deviations: (1) criterion 12's "Calculating…" is shown via a post-pass QTimer.singleShot(0,...) flash rather than literally live during the (synchronous, UI-thread) recalculate() call -- the only honest option without moving recalculation off the UI thread, which is out of scope for this chrome-only spec; satisfies the criterion's intent (no flicker under 300ms, visible indicator over it). Flagging as a possible future follow-up (move recalculation off the UI thread) only if Theo notices it mattering in practice -- not blocking. (2) criterion 16's "Follow System" test path uses an injectable scheme_reader since QStyleHints.setColorScheme() doesn't reliably take effect under the offscreen QPA platform; production code always uses the real OS reader. Both low-stakes, well-justified; not separately queried to Theo.
- Spec 007 implementation accepted; assigning independent review to tester.

## Decided 2026-10-29 (manager + Theo, spec 009 component-wiring core)
- IP check: pass, manager's own review agrees. Accepted without separately querying Theo (low-stakes, well-justified): (1) no sheet-variable integration in this foundation spec; (2) gui-specialist was unreachable, specialist's own call (plain Insert > Component… entry, no new View toggle) accepted; (4) no component resizing yet; (5) `required=False` input ports specified but unexercised, fine; (6) backlog 33's cross-file recursion/cycle-detection format caveat noted for the modeling-specialist to revisit when writing that spec.
- Theo's call (genuine IP-risk judgement, same category as the 2026-10-28 spec 005->006 decision): keep BOTH wire-creation paths in phase W2 -- the generic "Connect..." dialog AND the drag-output-to-input-terminal gesture. Reasoning: the drag gesture is a generic, cross-category diagramming convention (flowchart/circuit/UML editors), materially lower risk than spec 005's rejected inline chart-axis placeholder editing; the dialog alone already covers every acceptance criterion so the drag gesture adds only convenience, no required functionality.
- Spec 009 fully approved; queued for developer behind spec 008 (matrix dialog, in progress) per "developer works one spec at a time."

## Decided 2026-10-29 (Theo + manager, spec 010 ODE solving)
- Keywords confirmed: `ode`, `start`, `evolve`/`evolve symbolic`/`evolve numeric`.
- Prime-mark notation (`y'(0)`, `y''(0)`) confirmed, scoped only to `start` lines.
- Manager accepted the remaining open questions without separately querying Theo (low-stakes, well-justified): (3) factor spec 004's `over` sub-grammar into a shared helper, developer's call on exact placement; (4) two-point boundary-value problems stay out of scope, no follow-up planned yet; (5) phase B binds the numeric solution as a usable function from the start (table + callable), not deferred to a phase C; (6) no satisfied/violated-style per-region marks for `ode`/`start` lines; (7) an implicit-only closed form is treated as "no closed form found" (falls back to numeric / errors in forced-symbolic mode).
- IP check: pass, manager's own review agrees — SymPy `dsolve`/SciPy `solve_ivp` are already-approved BSD dependencies used per their own documented API; `Odesolve` and `solve` (already used) both avoided; tag idiom reuses spec 003's already-reviewed construct. Carries forward spec 003's existing open flag (no formal patent search on the "named group of tagged regions solved on demand" idiom, now shared by two features) and the pre-1.0 legal-review note — nothing new, no additional action now.
- Spec 010 fully approved; queued for developer behind specs 008 (matrix dialog, in progress) and 009 (component-wiring core).
- Process note: specs 009/010 both initially targeted spec number 009 (two specialists dispatched in overlapping windows); both self-resolved via renumbering + a stale one-line pointer at the old path, same pattern spec 008 used for its own 007/008 collision. Working as a fallback; no process change needed for now.

## Decided 2026-10-29 (manager, spec 008 implementation)
- Accepted the developer's one disclosed judgement call: committing the dialog's compiled text into an existing region via the region's own start_editing()/QTextCursor-replace/finish_editing() path (not a direct RegionData.text set), so the pretty on-screen display refreshes immediately via _leave_edit_display() -- matches the spec's own "reuse start_editing()/finish_editing() as-is" architecture note. No separate query to Theo needed.
- Full suite 994 passed, 2 xfailed, 0 failed (934 baseline + 60 new tests), run 3x for stability.
- Spec 008 implementation accepted; assigning independent review to tester.

## Open 2026-10-30 (developer, spec 010 ODE solving, acceptance criterion 7)
- Criterion 7's first scenario (`ode diff(y(t), t) + y(t)/tau == 0 in decay`, `tau := 4 s`,
  `start y(0) == 10 in decay` with no unit on the value, `evolve in decay` -> expected
  "error starts Units do not match") could not be reproduced with a principled unit check,
  verified by actually running the equation through real SymPy's `dsolve` and this engine's
  `units.measure()` (mathcad-specialist and tester never read vendor docs, but the developer
  is allowed to exercise the already-approved sympy/scipy dependencies directly to verify a
  spec's own hand-derived numeric claims, same as the tester already does for every spec):
  - `dsolve` itself solves both the `10 m` (criterion 1) and `10` (criterion 7) variants fine;
    it does not perform or need any unit check.
  - Full dimensional analysis of `diff(y,t) + y(t)/tau == 0`: matching the two additive terms
    forces the independent variable's dimension to equal tau's dimension (time), a constraint
    that is completely independent of y's own dimension (y's dimension cancels from both
    sides identically). So by rigorous analysis, y(0) being length (criterion 1) or
    dimensionless (criterion 7) are equally self-consistent -- there is no real mismatch to
    detect in the dimensionless case specifically.
  - Every cruder heuristic tried (e.g. "assume the independent variable is dimensionless, so
    diff(y,t) must have the same dimension as y itself") that *would* flag criterion 7 also
    incorrectly flags criterion 1 as an error, contradicting its expected "ok" status (both
    use the exact same equation and the exact same point "0").
  - Separately found: `sp.dsolve([eq1, eq2], [x(t), v(t)], ics={...with sympy.physics.units
    Quantities directly...})` for a *coupled* system raises `NotAlgebraic` from inside
    SymPy's own constant-solving step -- so criterion 3's free-fall system cannot literally
    "pass Quantity-valued `ics` straight to `dsolve`" as the spec's prose describes. Developer
    is instead stripping to SI magnitudes before `dsolve`/`solve_ivp` and reattaching units
    afterward (same pattern `engine/solver.py` already uses for spec 003's unknowns), which
    avoids the crash and is also the only way found to make unit handling work at all for a
    coupled system.
  - mathcad-specialist was unreachable for a quick chat clarification (not currently running);
    question asked here instead, per "stop and ask instead of guessing". Developer is
    proceeding with the rest of spec 010 using a correct, principled unit check (per-function
    dimension from its own order-0 condition; independent-variable dimension only from an
    `over` line when one is given, otherwise left free like any other user-defined function's
    parameter) and will document criterion 7's first scenario as a known, disclosed deviation
    (no error raised there) in `docs/board/log.md` rather than guess a check that would also
    incorrectly break criterion 1. Needs Theo/manager/specialist review: is criterion 7 a
    hand-derivation mistake (plausible, flagged generally for every spec's hand-derived
    numbers since 2026-10-27), or is there a different intended mechanism the developer is
    missing?
