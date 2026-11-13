# Review: spec 034 GUI-1 (Electrical tab, 36 insertion buttons)

Date: 2026-11-13. Tester. Source of truth: docs/board/specs/034-elec-eng-library-overview.md (GUI-1..GUI-6, GUI-4 table). Developer annotations were re-verified, not trusted.

## Tests added
`tests/test_spec034_gui1_review.py` (173 cases, all passing):
- Structure: 7 new group names and order, counts 6/4/3/4/9/7/3, widget headers and button order in the real SidePanel Electrical page (DC Circuits 7, Power 4, then new groups; 47 buttons), TAB_ORDER unchanged, labels globally unique.
- Labels and inserted text compared against a table typed from GUI-4 (36 rows, exact, ordered).
- Each of the 36 buttons clicked in a real MainWindow: region text equals the token exactly (GUI-3). Placeholders then filled with SI values (incl. kohm, mA, mH, uF, vectors, complex z) and evaluated with a display unit; result compared with an independent recomputation (math/cmath), rel 2e-5. All 36 match.
- Placeholders: none is in UNITS or is_unit_name, none is a builtin or E/I/L/g/e/pi; each alone evaluates to "not defined"; the used set equals the spec's placeholder list; every unfilled token gives "not defined" (no silent unit).
- Tooltips: present, ASCII, no imperial/vendor words, units named for the GUI-4 buttons that specify them (W, rad, VA, var, lagging, rad/s, Hz, turn, balanced...).
- DC/Power (spec 020): 11 buttons, label == text, order, first/last unchanged. Mechanical (6+9 = 15 buttons), Chemical (21) and other tabs contain none of the new labels.
- Plain-text insertion, `.lsheet` version stays 1, second click appends to the same region, recalculation inside a real worksheet, narrow panel (260 and 420 px) wraps without horizontal overflow, narrow MainWindow (360 px) still clickable.

Full-suite and the four related files: `tests/test_spec034_gui1_review.py`, `test_electrical_gui1.py` (developer), `test_formula_tabs_018_020.py`, `test_formula_tabs_review_022.py`: 460 passed. Full-suite run (QT_QPA_PLATFORM=offscreen, ~/livesheet-venv) result is in the hand-back message.

## Defects
Critical: none. Major: none.
Minor:
1. Tooltip wording for GUI-4 buttons the spec did not spell out was written by the developer (annotation 1). All are SI-only and name units; acceptable, but the manager may want the exact wording approved once (IP-neutral, own words).
2. Pre-existing, not GUI-1: at about 180 px panel width the content widget is wider (Electrical 197 vs viewport 148; Mechanical 173; Chemical 209) than the viewport and the horizontal scrollbar is off, so the longest buttons (for example DC "V_out := V_in * R2 / (R1 + R2)", 185 px) are clipped. The new buttons are short enough to wrap; no new regression. Suggest a backlog note.
3. The side panel has no search field, so there is no search behaviour to check.
4. Spec text says "Lind" etc. avoid unit letters; verified true. Note "R" alone is fine (not a unit), but a user who types the token then `C`/`L` in other positions still hits the existing unit landmine (outside GUI-1).

## Judgement of the developer's edits to older tests
- `tests/test_formula_tabs_018_020.py`: Electrical expectation extended to nine headers with counts [7,4,6,4,3,4,9,7,3]; the ASCII/label==token checks restricted to `Electrical[:2]`. Acceptable and it matches the spec (GUI-1 adds groups, GUI-6 keeps the first two). The restriction is correct because new labels are descriptive text, not equal to the token (spec GUI-4). The ASCII check for the new rows is now only covered by my file (done) and the developer's file.
- `tests/test_formula_tabs_review_022.py`: header and count checks use a prefix comparison and `len(buttons) >= len(rows)`. Acceptable but looser than needed: the `>=` would hide an accidental extra button in a tab. Recommendation (non-blocking): make Electrical's total exactly 11 + 36 = 47 and keep exact equality for the other tabs. Exact totals are pinned in my file, so no coverage is lost.
- Neither edit weakens the GUI-6 regression: labels, tokens, tooltips and order of the first 11 are still compared exactly.

## Coverage gaps
- Real application not driven visually by me: the computer_* tools were not available in this session, so the GUI rule (launch the app, click the Electrical tab, resize) is NOT done. Needs a manual or follow-up pass on Theo's Mac.
- No test of rendering (button text truncation, header look) in an actual window; layout checked only geometrically offscreen.
- Evaluation correctness of the engine functions themselves is spec 034 phase 1A/1B (other reviews), only exercised here through the filled tokens.

## IP red flags
None seen: labels, placeholders and tooltips are own wording; no vendor names; formulas are generic textbook relations.

## Verdict
PASS (accept GUI-1), with the non-blocking recommendations above and the visual-run gap.

## log.md line
`2026-11-13 tester: spec 034 GUI-1 reviewed, PASS (173 new tests in tests/test_spec034_gui1_review.py, 36 buttons click+fill+evaluate match independent values; dev edits to 018_020/review_022 tests acceptable, suggest exact 47 total; real-app visual run still outstanding); review in docs/board/reviews/034-gui1-review.md`
