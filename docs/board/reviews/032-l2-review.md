# Spec 032 phase L2 independent review (tester)

Date: 2026-11-13. Spec: docs/board/specs/032-latex-text-regions.md (L2 part: criteria 14, 28-30, sections 3 L2, 12, Bundled font).
Tests: tests/test_spec032_l2_review.py (318 cases, all pass, about 1.3 s). Written from the spec only; expectations are
structural relations (row order, alignment edges, ascent/descent growth, 12 vs 24 pt ratio within 5%), not copied from
the developer tests. No vendor docs read. No chat clarification with the developer was needed.

## Verdict: PASS, no blockers, no high or medium defects. Three low/cosmetic notes and two coverage gaps.

## What was checked
- Parser: all six matrix environments and their delimiters, ragged rows padded, empty cells, trailing `\\`, nested
  matrices, mismatch / missing `\end` / unsupported environment messages and offsets (criterion 14), `equation`/`align`
  wrappers still unsupported, 50x50 limit (50 ok, 51 error both directions), nesting limit with 40 nested
  environments gives TexError (no RecursionError), `cases`, `aligned`, `array{lcr}` (bad column spec, too many cells),
  all 10 accents (+ "needs an argument" message, brace labels), 6 font commands over 40 characters each (never an
  error, so the `\mathbb`/`\mathcal` fallback rule holds), `\bmod`, `\pmod`, `\operatorname`, out-of-scope commands
  still `unsupported: \x`, L1 messages unchanged, `livesheet.texmath` still imports no PySide6 (subprocess check).
- Layout: matrix width/height/row and column ordering, rows do not overlap (with fractions in cells), grid centred on
  the axis, brackets grow with height and become path boxes, `cases` brace plus left-aligned first column, `aligned`
  right/left alternation, `array` l/c/r edges, accent marks sit above the letter and inside the box, over/underline
  and braces grow the box, labels extend it, scale ratio 2.0 within 5% for matrix/cases/brace/blackboard formulas,
  scripts on and inside matrices, empty matrices, 1500-case L2-token fuzz (only TexError escapes).
- Font (criterion 30): file present, OTTO header, SHA-256 of the .otf and OFL.txt equal the values in
  livesheet/gui/fonts/README.md (README records the project publishes no archive checksum), OFL text contains
  "SIL OPEN FONT LICENSE Version 1.1" and the copyright, `addApplicationFont` id >= 0, family is exactly
  "STIX Two Math" (unrenamed) and listed in `QFontDatabase.families()`, it is first in the chain and is the family
  Qt actually resolves for layout fonts, every code point in the symbol table exists in the bundled font (QRawFont),
  forced load failure (missing file) returns -1 and formulas still lay out, pyproject package-data lists the font and
  OFL.txt, third-party notice mentions STIX and OFL.
- Window (criteria 28, 29): View toggle exists, checkable, default on; off => raw display, `text()` unchanged,
  sheet not modified, no scanning (no error tint or caption for `$\foo$`), on again typesets, setting persisted and
  honoured by a new window and by regions added later; toggle changed while a region is editing applies after it
  finishes; file bytes identical with the toggle off/on. Insert items: in the Insert menu with Ctrl+Alt+4 and
  Ctrl+Alt+Shift+4, no duplicate shortcut anywhere in the window, a real Ctrl+Alt+4 key event inserts `$$`; inline on
  empty text gives `$$` caret 1, display gives `$$$$` caret 2, selection wraps (`$abc$`, `$$abc$$`), mid-text insert,
  one undo step, typing then leaving edit state typesets, empty delimiters stay plain text without error, selected but
  not editing starts editing at the end, nothing selected (and a selected math region) creates a text region in edit
  state with the delimiters, items disabled (and commands inert) while a math region is edited, re-enabled afterwards.
- PDF with matrix, accent, brace, blackboard, cases and an invalid span: completes, `%PDF`, no image objects.
- Visual check of rendering through an offscreen QImage (matrix, cases, aligned, vmatrix, braces, accents, font
  commands). Rendering looks correct; see notes.

## Defects
None above low.

### L2-1 (low, cosmetic) Delimiters sit tight against cell content
In `\begin{pmatrix} 1 & 2 \\ 3 & x^2 \end{pmatrix}` and bmatrix the first/last column digits almost touch the
brackets; for `cases` the `x^2` touches the left brace. Repro: render `layout_formula(r"\begin{bmatrix}1\\2\\3\\4\end{bmatrix}", 22, True)`.
Spec gives no number, so not a spec violation; suggest slightly larger padding (the code uses 0.10 em).

### L2-2 (low, cosmetic) Over/underbrace label nearly touches the brace tip
`\overbrace{a+b+c}^{n}` and `\underbrace{d+e}_{m}`: gap between label and tip about 0.08 em; reads tight at 22 px.

### L2-3 (low, cosmetic) `aligned` column gap is small
`\begin{aligned} a &= b+c \\ dd &= e \end{aligned}`: the relation after `&` is separated from the left column only by
the thick-space gap, so `dd= e` looks cramped next to `a = b+c`. Common practice puts relation spacing on both sides.

### Observations (not defects)
- `\overbrace{a}^{x}^{y}` is accepted as brace label `x` plus a superscript `y` on the whole brace. Reasonable.
- A single `A`-`Z` after `\mathbb`/`\mathcal` maps through Unicode double-struck/script code points, bold fallback
  exists only when the font lacks the glyph; confirmed no error for any letter or digit.
- Layout `ascent` of a glyph is the nominal font ascent, so `\hat{x}` does not enlarge the box (mark fits under the
  nominal ascent). Intended; the mark is verified above the ink of the letter.
- The developer edited tests/test_spec011_side_panel_greek_blackbox.py (criterion 15 skips Ctrl+Alt+4). This is
  justified (a digit is not a Greek-letter shortcut) and was logged by the developer; the manager should confirm
  it accepts a changed old test. No other collision exists (checked by the window-wide shortcut scan).

## Coverage gaps
1. Real GUI check was NOT done: this session has no computer-use tools (no computer_* functions), so I could not
   launch LiveSheet on the Mac and open/close windows, dialogs, the View toggle, Insert shortcut under macOS
   (Cmd+Opt+4 vs the OS screenshot shortcuts Cmd+Shift+3/4/5 which are different, but the OS-level clash on
   Windows/Linux remains unverified, as the developer also reported). Needs a manual run: light/dark, zoom, double
   click on a typeset matrix puts caret in source, export PDF and zoom into it.
2. "Visible placeholder box for a code point no font has" (font failure section) is not tested; no obvious way to
   trigger it black-box.
3. Raw HTML round-trip with L2 formulas containing `&amp;` was covered by View-toggle and PDF tests only, not by
   the full save/load file test (L1 review file covers byte-identity for generic content).

## IP red flags
None. Symbol names, matrix/accent command names are standard notation; error messages match the spec's own
wording; the font is the unmodified STIX Two Math with OFL.txt and recorded hashes (source URL in README is the
official repository, as required). No vendor names, help text or example worksheet content found in
livesheet/texmath or gui/texlayout.py. One process note: the README says the font hash is binding and the archive
hash may vary; the tester could not re-download to re-verify the archive hash and did not need to.

## Result of runs
`QT_QPA_PLATFORM=offscreen pytest tests/test_spec032_l2_review.py` : 318 passed. Full suite: 4435 passed, 2 skipped, 15 xfailed (87 s).
