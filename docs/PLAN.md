# LiveSheet plan

Vision: an open-source (permissive licence) live worksheet that combines
- the engineering-calculation workflow of Mathcad-style tools (units, solve blocks, print-quality documents),
- the symbolic depth of Mathematica-style tools (rules, assumptions, lists, interactivity),
- the usability of Maple-style tools (context actions, assistants, exact+float, toolboxes),
as an original implementation on SymPy + PySide6, clean-room (see IP-POLICY.md).

## Team (Claude Code subagents in .claude/agents)
| Agent | Role | Writes |
|---|---|---|
| manager (main session) | prioritises, IP-reviews specs, delegates, merges, commits | board/backlog, decisions |
| mathcad-specialist | engineering-calc specs | board/specs |
| mathematica-specialist | CAS/notebook specs | board/specs |
| maple-specialist | usability/education specs | board/specs |
| developer | the only agent that changes production code | livesheet/, tests for own code |
| tester | independent black-box tests + review | tests/, board/reviews |

Communication: subagents see only their delegation prompt, so they exchange work via docs/board (specs, reviews, log, decisions) and the manager relays; SendMessage continues an agent with its history. Peer-to-peer messaging needs Claude Code "agent teams"; optional later.

## Skills (.claude/skills)
mathcad-concepts, mathematica-concepts, maple-concepts (idea maps from public product descriptions), ip-cleanroom, spec-writing, livesheet-dev, livesheet-testing.

## Cycle per feature
spec (specialist) -> IP review (manager) -> implement (developer) -> test + review (tester) -> fix -> merge.
Parallel allowed for independent specs; developer works one spec at a time.

## Milestones
M1 Engineering core · M2 Document quality · M3 CAS depth · M4 Usability (see board/backlog.md)

## Risks
IP/trademark (policy + review), GPL contamination, SymPy speed on large sheets (cache, incremental recalculation), Qt typesetting effort, scope creep.
