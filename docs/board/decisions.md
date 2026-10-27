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
