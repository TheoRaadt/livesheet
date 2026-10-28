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

## Decided 2026-10-28 (Theo, spec 004)
- Renderer: QPainter directly (no new dependency)
- `.lsheet` version 2 only when a plot is present
- Plots may overlap regions below until backlog 20 (push-down layout)
- Other 004 questions follow the manager recommendations above unless Theo says otherwise
