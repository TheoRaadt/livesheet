---
name: spec-writing
description: How specialist agents write behavioural specs for LiveSheet in docs/board/specs using the board template. Use whenever turning a researched idea into a developer-ready spec.
---
1. Read docs/board/README.md (template) and docs/board/backlog.md; take the next unspecced item.
2. Check what LiveSheet already does (README.md, livesheet/engine/*.py) so the spec only describes the delta.
3. One spec = one shippable slice (about 1-3 days of work). Split larger ideas.
4. Syntax proposals use own keywords and must be parseable by the existing statement grammar (:=, ≡, =, →) or state the grammar change explicitly.
5. Acceptance criteria are numeric and testable, e.g. `A := [1,2;3,4]`, `det(A) =` gives `-2`. Include a unit example and an error case.
6. Always fill the IP check line. Cite public URL + date; never paste vendor text.
7. Name the module(s) affected; prefer engine changes before GUI.
8. Name specs `docs/board/specs/NNN-short-name.md`; append a line to docs/board/log.md.
