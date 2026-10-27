# Agent board (shared blackboard)

Subagents only return a report to the manager and do not see each other's context. This folder is how they "talk":

- `backlog.md`    prioritised feature list (manager owns)
- `specs/NNN-name.md`  behavioural spec written by a specialist (template below)
- `reviews/NNN-name.md` tester findings; developer reads these
- `decisions.md`  open questions + decisions (manager owns, Theo decides)
- `log.md`        append-only one-line handoffs: `YYYY-MM-DD from -> to: message (file)`

## Flow
specialist writes spec -> manager IP-review -> developer implements + unit tests -> tester writes independent tests + review -> developer fixes -> manager merges.

## Spec template
```
# NNN Title
Source inspiration: <public URL, date> (concept only)
User story:
Behaviour (own words):
Syntax proposal (own keywords):
Acceptance criteria: (testable, with numeric examples)
Edge cases:
IP check: pass/fail + note
Fits current architecture? (engine/evaluator.py, units.py, gui/...)
```
