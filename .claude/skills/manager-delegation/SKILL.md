---
name: manager-delegation
description: Use at the start of any LiveSheet work session, and before touching any production code/test/spec/research file yourself. Checks whether the task belongs to a specialist/developer/tester/documenter agent instead of the main (manager) session. Theo has flagged this is repeatedly forgotten.
---
The main session is the manager (CLAUDE.md "Manager role"). It does not write feature code,
engine/GUI changes, tests, or specs itself. Before using Edit/Write/Bash to do any of that
yourself, stop and dispatch the right agent instead:

1. New feature idea / research -> mathcad-specialist, gui-specialist, or modeling-specialist
   (Agent tool). They write a spec in docs/board/specs/.
2. A spec exists but isn't IP-reviewed -> **this is the manager's own job**, do it yourself
   against docs/IP-POLICY.md, no agent needed.
3. A spec is IP-approved and needs implementing -> developer (Agent tool), never the manager.
4. An implementation needs independent tests/review -> tester (Agent tool), never the manager
   and never the same agent that implemented it.
5. A spec is fully done (implementation + review both accepted) -> documenter (Agent tool).
6. Open questions needing a human call -> docs/board/decisions.md, ask Theo.

Manager-appropriate hands-on actions (fine to do directly, not a delegation gap): running the
existing test suite to verify a report, IP review itself, reading/updating docs/board/*,
updating CLAUDE.md/STATUS.md/backlog.md, light bookkeeping on files no agent is actively
using (e.g. finishing a rename an agent was killed mid-way through), git operations.

Before any Edit/Write/Bash call that would touch livesheet/, tests/, or docs/board/specs/
content itself (not just board bookkeeping), ask: "is this implementation or test-writing work
a developer/tester should do?" If yes, dispatch an agent instead of doing it.
