---
name: user-manual-writing
description: How the documenter agent writes and updates LiveSheet's end-user manual (how-to guides and the error-message reference) in docs/manual. Use whenever a spec is fully done (developer implementation + tester review both accepted by the manager) and the manual needs to catch up with it.
---
1. Only document a spec once the manager has accepted BOTH the developer's implementation and the tester's independent review (see docs/board/log.md / docs/board/decisions.md). A spec still in progress, or with an open defect, is not done yet — wait.
2. Sources, in this strict order, and no others:
   - The approved spec in docs/board/specs/NNN-*.md (what the feature is supposed to do).
   - The manager's decisions.md entry and the developer's/tester's log.md handoff lines for that spec (disclosed deviations, accepted judgement calls — the manual must describe what actually shipped, not the original spec text where the two differ).
   - The actual shipped code and tests (grep for exact error-message strings, exact keyword/syntax spellings, exact function names) — never invent or paraphrase an error string from memory; quote it exactly as the code raises it.
3. NEVER read vendor documentation, help text, tutorials, example worksheets, or any other vendor material, for any reason, even "just for phrasing inspiration." Unlike the specialists (who may read public vendor docs for *concept* research per ip-cleanroom), this agent writes the one category of content IP-POLICY names explicitly as forbidden to copy — "help text" — so it must stay fully clean-room with zero vendor exposure. Everything here is written from LiveSheet's own spec/code/tests, in LiveSheet's own words.
4. Structure:
   - `docs/manual/README.md` — index/table of contents, one line per page, linking to every how-to page and to `errors.md`.
   - `docs/manual/<topic>.md` — one how-to page per feature area (name the topic after the spec's own short-name where sensible, e.g. `plots.md`, `solve-blocks.md`; group closely related specs into one page rather than one page per spec number). Written for the end user: what you want to do, the exact syntax/steps, a short worked example with real numbers, what the result looks like. Second person, plain language, no developer/engine jargon.
   - `docs/manual/errors.md` — one consolidated table/list of every user-facing error message LiveSheet can show, grouped by feature area: the exact message text (or pattern, where it includes a variable like a symbol name), what causes it, how to fix it. Keep it append-only across specs (add new rows, don't restructure existing ones without reason) so it stays one reliable place to search.
5. When a spec's implementation changes an already-documented feature (a later spec, or a bugfix), update the existing page/rows in place rather than leaving stale text — the manual must always match the current shipped behaviour, not a historical snapshot.
6. Append one line to docs/board/log.md per update: which spec, which manual pages/rows were added or changed.
7. Not a spec, not a review: never write to docs/board/specs/ or docs/board/reviews/, never touch production code under livesheet/ or tests/.
