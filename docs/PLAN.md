# LiveSheet plan

Vision: an open-source (permissive licence) live worksheet that combines
- the engineering-calculation workflow of Mathcad-style tools (units, solve blocks, print-quality documents),
- the symbolic depth and usability of CAS/notebook-style tools (rules, assumptions, lists, interactivity, context actions, exact+float),
as an original implementation on SymPy + PySide6, clean-room (see IP-POLICY.md).

## Team (Claude Code subagents in .claude/agents)
| Agent | Role | Writes |
|---|---|---|
| manager (main session) | prioritises, IP-reviews specs, delegates, merges, commits | board/backlog, decisions |
| mathcad-specialist | engineering-calc specs | board/specs |
| gui-specialist | UI/UX layout and interaction-polish specs (general, product-agnostic design guidance) | board/specs |
| modeling-specialist | component/wiring (dataflow) specs, grounded only in generic public-domain concepts | board/specs |
| developer | the only agent that changes production code | livesheet/, tests for own code |
| tester | independent black-box tests + review | tests/, board/reviews |

Communication: subagents start with only their delegation prompt, but since 2026-10-29 every agent also carries ListAgents/SendMessage, so they may message each other directly for quick coordination instead of only relaying through the manager (Theo's request). docs/board (specs, reviews, log, decisions) stays the durable record: the developer only ever implements from a spec that already passed the manager's IP review there, never from chat alone, and any chat clarification that changes something gets written back into docs/board.

## Skills (.claude/skills)
mathcad-concepts, gui-concepts, modeling-concepts (idea maps from public product/design/generic descriptions), ip-cleanroom, spec-writing, livesheet-dev, livesheet-testing.

Note (2026-10-29): the mathematica-specialist and maple-specialist agents and their concept skills were dropped (low output relative to upkeep). The underlying feature ideas stay in the backlog; mathcad-specialist or Theo now originate specs for them.

## Cycle per feature
spec (specialist) -> IP review (manager) -> implement (developer) -> test + review (tester) -> fix -> merge.
Parallel allowed for independent specs; developer works one spec at a time.

## Milestones
M1 Engineering core · M2 Document quality · M3 CAS depth · M4 Usability (see board/backlog.md)

## Risks
IP/trademark (policy + review), GPL contamination, SymPy speed on large sheets (cache, incremental recalculation), Qt typesetting effort, scope creep.

## Status
See docs/STATUS.md (updated 2026-10-28). M1 is well underway: ranges, matrices (core+2b), solve models and plots (engine, GUI region, dialog-based configuration) are built; undo/redo and temperature units remain. M2 (document quality) items added to the backlog (structured headings/ToC/index, open dataset import, reference data).
