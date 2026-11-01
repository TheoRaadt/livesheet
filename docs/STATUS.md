# LiveSheet status (2026-11-01, session stopped — Theo reaching usage limits, asked to stop all agents)

Commits: unchanged since last session (`911addf` is still HEAD; see git log). **Nothing from this
session is committed.** All 4 agents running at the end of this session were stopped via TaskStop
at Theo's request; none got to send their own final handoff report, so everything below about their
state was reconstructed by the manager directly from what they actually left on disk, not assumed
from their last tool call.

## Done and accepted this session (solid, verified, just not committed)
- **Specs 013+014 (DXF profile import, both phases) are now fully done end-to-end**: spec 014's
  independent review was finished (picking up an earlier interrupted session), independently
  spot-checked by the manager (re-derived the bulge-direction fix's key numeric claim directly
  against the code: 676.8176834728116 mm², matches exactly), accepted. Combined manual page
  (docs/manual/cad-profiles.md) written and accepted, including two findings the documenter caught
  by reading the shipped code against the spec text (one dead error message no longer reachable,
  one message whose trigger condition had narrowed) — both independently verified by the manager.
- **Known issue 38 is fixed and closed**: `wiring.py`'s `format_output()` no longer crashes on a
  Matrix-valued component output (it now mirrors `evaluator.py`'s own per-cell matrix-display
  convention). Independently verified by the manager (suite count + direct repro calls). No spec
  was needed, pure bug fix.
- Fixed two stale labels in backlog.md (002b and the 2D-plots item were already done but still
  marked otherwise) found while cross-checking against decisions.md/log.md.
- New M8 milestone added to backlog.md (Theo's request): three new SI-only, categorized side-panel
  formula tabs (Mechanical/Electrical/Chemical), same quick-insert mechanism as spec 011.
- **Spec 018 (Mechanical formula tab) is fully IP-reviewed and approved**, with the manager finding
  and fixing 4 real numeric-example errors in its own acceptance criteria before accepting (see
  below) — the same category of pre-implementation flaw past specs have had (010's criteria 7/18,
  014's semicircle-prose note).

## In flight / left incomplete — next session should pick these up, in this order

### 1. IP-review specs 017 (statistics), 019 (chemical), 020 (electrical) — not yet done
All three are **complete, well-formed specs already on disk**, written by specialist sessions that
were stopped before they could send their own report (confirmed by reading each file directly — all
end cleanly with a full "Open questions" section, none cut off mid-sentence):
- `docs/board/specs/017-statistics-core.md` (732 lines, backlog item 29) — phased S1 (descriptive
  stats + 4 distributions)/S2 (hypothesis tests, new tagged-region construct)/S3 (regression,
  extends 002b's least-squares). 8 open questions recorded in the file, including whether
  `scipy.stats`/`numpy.random` should be the implementation backend.
- `docs/board/specs/019-chemical-formula-tab.md` (350 lines, backlog item 41) — self-resolved a
  numbering collision correctly (found 018 taken by Mechanical, renumbered to 019, left a stale
  stub). 5 open questions recorded.
- `docs/board/specs/020-electrical-formula-tab.md` (457 lines, backlog item 40, phase E1 = DC
  Circuits + Power) — self-resolved the same collision (found both 018 and 019 taken, renumbered to
  020, left its own stale stub). Did receive the manager's relayed naming-collision warning (see
  below) and independently re-confirmed the `_check_defined()` landmine itself.

**Before accepting 019/020, re-run the same numeric-verification pass the manager did on spec 018**:
every one of spec 018's acceptance criteria that claimed a bare `<name> =` would print a
prefixed-unit result (`MPa`, `mm`) turned out to be wrong — the engine only prints a non-base-SI
unit when it's explicitly requested (`sigma = MPa`, not `sigma =`), and one criterion (moment of
force) printed `J` instead of the claimed `N·m` because they share a base-SI dimension. This was
caught by running `Engine().evaluate(enumerate([...]))` directly against each criterion before
accepting, not by reading the spec text and trusting it. **Spec 019/020 almost certainly have the
same class of flaw in any criterion involving a non-base-SI unit** (electrical especially — `kΩ`,
`mA`, `kW`, etc. are exactly the kind of prefixed unit this bug class affects) and have not been
checked yet.

### 2. Engine hardening of `_check_defined()` — barely started, needs a fresh dispatch
Theo decided (asked directly, 2026-11-01): a bare variable name that resolves only because it
matches a `UNITS`/`BUILTINS` key (e.g. typing `F` or `A` with nothing defined) should be reported as
`"not defined"` instead of silently evaluating as that unit. A developer was dispatched with an
explicit, detailed warning that the naive fix (flag any bare UNITS-colliding name) would break
nearly every existing `<number> <unit>` statement in the whole suite (`5 N`, `10 m`, etc. all rely
on exactly this mechanism), and was asked to investigate the real parsing/substitution pipeline for
a safe distinguishing rule, or report back if none exists rather than ship something risky.

**This got only ~2 minutes of work before being stopped** — it reproduced the landmine
(`Engine().evaluate(enumerate(['sigma := F/A', 'sigma =']))` gives `status='ok'`, not an error) and
was about to start investigating `free_symbols` behavior when stopped. **No actual investigation of
the fix happened, no code was touched.** Re-dispatch fresh next session using the same detailed
warning (see docs/board/decisions.md's 2026-11-01 "spec 018" entry for the full writeup of why this
is genuinely tricky, not a one-line fix) — don't try to resume the stopped agent from where it left
off, there's nothing of substance to resume from.

### 3. Spec 018 (Mechanical) itself: fully approved, intentionally held back
Not a problem, just sequencing: spec 018 is fully IP-reviewed and its numeric examples corrected and
verified, but deliberately **not yet dispatched to a developer**, because specs 018/019/020 all
independently want to edit the same `TAB_ORDER` list in `livesheet/gui/sidepanel.py` — once 019/020
are also IP-reviewed, give one developer task all three tab additions together (recommended merged
order: `Elements, Algebra, Calculus, Statistics, Optimization, Mechanical, Electrical, Chemical,
Outline, Data`) rather than three separate merge collisions.

## Standing items (carried forward, unchanged)
- **The real-window manual pass on Theo's Mac** is still outstanding for specs 010, 011, 013, 014,
  and 015 — no session so far has had computer-use tooling available.
- Two untracked vendor PDFs in `docs/` remain deliberately untracked/unused (ip-cleanroom rule 7).
- Backlog beyond M8: item 30 (optimization) still needs a spec; spec 016 (3D plots/animation) is
  still only a research note, renderer choice undecided; Phase F2 (beam elements, FEM) is a forward
  note in spec 015 only, not yet specced; backlog items 7/7a/8/8a/9 (document quality), 10-13/19
  (CAS depth/usability beyond ODEs), 32/33/34/37 (data-source components, nested sub-sheets,
  user-script components, 3D plots — all of M6 except the core wiring mechanism and DXF import) are
  all still unstarted.

## Tester/dev practicalities (Mac)
LiveSheet runs from `~/livesheet-venv` (pip install -e). Concurrent agent sessions sometimes end up
with separate venv instances — if a session hits `ModuleNotFoundError` for a dependency another
agent just added, just `source ~/livesheet-venv/bin/activate && pip install -e ".[dev]"` again in
that session's own shell rather than assuming something is broken (this bit the manager directly
this session — the main session's own shell was NOT using the project venv by default, needed
`source ~/livesheet-venv/bin/activate` before every `pytest`/`python3` call). Terminal is click-only
for agents; Theo starts the app. Window must not be in a full-screen Space unless system key combos
are granted. Dialog tests: Cancel only, never save over examples/.

## Full suite state, last independently confirmed
`QT_QPA_PLATFORM=offscreen pytest -q` (from `~/livesheet-venv`): **1647 passed, 2 xfailed, 0
failed** — confirmed right after the known-issue-38 fix, before any of the stopped work above
(which added no code, only spec/doc files). This is the number to expect at the start of next
session; if it differs, something changed outside this record.
