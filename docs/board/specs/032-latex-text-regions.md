# 032 LaTeX math in text regions (backlog 69)

Status: IP-reviewed by manager 2026-11-12, phases L1+L2 approved. L3 (live preview) not approved and not scheduled. Written by gui-specialist, spec only, no code.
Phases: L1 (core, shippable alone), L2 (matrices, accents, font commands, View toggle, Insert items, bundled font).

## Decisions recorded (Theo, 2026-11-12)
- Q1 Renderer: own parser plus `QPainter` layout (option A). No new Python dependency.
- Q2 Bundle the STIX Two Math font (SIL OFL 1.1 accepted for a font file). The licence file ships in the package (see "Bundled font").
- Q3 Old sheets: any valid `$...$` pair in an existing text region typesets after the update. Accepted.
- Q4 View toggle default: on.
- Q5 The error caption is not printed to PDF (an invalid span prints as raw source in the error colour).
- Q6 Linking formulas to live values is a separate future spec, not here.
- Q7 Insert formula menu items: yes (shortcut chosen below). No live preview in L1 or L2.
- Q8 Outline tab shows the raw formula source.

Source inspiration: general, public concepts only (concept, never expression), accessed 2026-11-12:
- Typesetting conventions for mathematics (script sizes, fraction bars, radicals, limits placement, atom spacing classes): publicly documented TeX typesetting algorithm descriptions and the general OpenType "MATH" layout concepts; used only as generic typographic ideas. LiveSheet picks its own numeric constants.
- LaTeX math notation as a de-facto open notation for writing formulas in plain text (`$...$`, `$$...$$`, `\frac`, `^`, `_`): treated like any standard mathematical notation under docs/IP-POLICY.md "Allowed".
- Unicode math symbol code points (public Unicode charts) for the glyph table.
- Licence facts: matplotlib licence page (PSF-style, BSD-compatible, https://matplotlib.org/3.6.0/users/project/license.html); STIX Two font licence (SIL OFL 1.1, https://stixfonts.org/ and https://spdx.org/licenses/OFL-1.1.html).
No competitor product, help text or layout was consulted. No KaTeX/MathJax/matplotlib source or symbol tables were read or are to be copied.

## User story
As an engineer or student writing explanations next to my calculations, I type formulas as LaTeX between dollar signs inside an ordinary text region. When I am not editing the region I see properly typeset mathematics; when I click into it I get my raw source back and can edit it. A mistake in my LaTeX never loses my text and never crashes the app: I see my source plus a short message saying what is wrong.

## Current state (delta basis)
- `TextRegion` (livesheet/gui/regions.py) is a rich-text `QGraphicsTextItem` editor. Its saved `text` is `editor.toHtml()` (document.py stores it as the region `text` string; no format change needed, see "Saving").
- Regions are auto-width (no text wrapping, no user resize handle); height follows the content. LiveSheet never moves regions on its own (pages.md).
- `Region` already has `_enter_edit_display()` / `_leave_edit_display()` hooks (used by `MathRegion`). Same pattern applies here.
- Text colour is the fixed token `#222222` on a canvas that is not themed by the app palette (theme.py, spec 007 open question 3); error colour `COLOR_ERROR`, error tint `COLOR_ERROR_BG`, edit tint `COLOR_EDIT_BG`.
- PDF export (`export_pdf`) renders the scene with `QPainter` on a `QPdfWriter` at 144 dpi via `sheet.render`, so anything painted with `QPainter` is vector in the PDF.
- `heading_text()` (worksheet.py) and the Outline tab read `region.editor.document()` directly.
- Dependencies today: sympy, PySide6, scipy, numpy, ezdxf. matplotlib is not a dependency and stays out.

## Behaviour (own words)

### 1. Two display states of a text region
1. Edit state (region focused, as today): the document shows the raw characters exactly as typed, `$`, backslashes and all. Nothing is hidden or auto-converted while typing.
2. Display state (not editing, including selected-but-not-editing): every recognised math span is shown typeset in place of its source characters; ordinary text around it is unchanged (rich formatting, bold/italic/underline, size).
3. Entering edit state (double-click, Enter on a selected region, as today) swaps back to the raw source. Leaving edit state (click elsewhere, Esc, Ctrl+Enter) typesets again.
4. The raw source is always the single source of truth. The typeset view is derived and never written to the file.
5. Click placement: double-clicking on a typeset formula puts the caret inside that formula's raw source, at its start when the click is in its left half and at its end when in its right half. Double-clicking ordinary text puts the caret where it does today. (Developer note: the target offset has to be computed from the typeset layout before the document is swapped to raw source; `Region.start_editing` currently hit-tests after the swap.)

### 2. Delimiters and escaping
- Inline math: `$ ... $`. Display math: `$$ ... $$` (on screen: its own line(s), centred in the region's content width, with extra vertical space above and below; large operators use the "display" limits style, see section 3).
- Scanning works on the region's plain text (paragraph breaks count as `\n`), left to right, once, no nesting:
  1. `\$` outside math is a literal dollar sign; in display state the backslash is dropped and `$` shown. In edit state it stays `\$`.
  2. `$$` opens display math. It ends at the next unescaped `$$`. It may span several paragraphs/lines.
  3. A single `$` opens inline math only if the character right after it is neither whitespace nor end of text. It ends at the next unescaped single `$` on the same paragraph that is not preceded by whitespace and is not immediately followed by a digit. Inline math never spans a paragraph break.
  4. An opener without a valid closer is plain text (no error, no typesetting). Example: `It costs $5 and $10 each` stays plain text; so does a lone `$` at the end of a paragraph.
  5. Empty math (`$$$$`, or `$ $`) is plain text.
  6. Inside math, `\$` is the LaTeX dollar-sign symbol and does not close the span. A bare `$` cannot appear inside inline math (it closes it); inside display math a single `$` is an error ("stray $", see section 5).
- Percent signs and other TeX special characters have no special meaning outside math. Inside math `%` is an error (unsupported), not a comment.
- Typing never inserts closing delimiters automatically (the Insert items in section 12 do, on request).
- Rich formatting inside a span is ignored for the math itself (math is typeset in the math font); the span's size follows the font size of the character at its first `$`, and its colour is the text-region colour.
- Existing sheets: any text region that already contains a valid `$...$` pair starts to typeset after this feature ships (decision Q3). Users keep the old look with `\$` or with the View toggle (L2).

### 3. Supported LaTeX subset
Anything not listed is "unsupported" and produces an error (section 5), never silently ignored. Names follow ordinary, widely published LaTeX math notation; this is not an attempt at full LaTeX.

L1 (core):
- Atoms: digits with decimal point, Latin letters (shown italic), Greek (`\alpha`..`\omega` and the capital forms that exist in Greek: `\Gamma \Delta \Theta \Lambda \Xi \Pi \Sigma \Upsilon \Phi \Psi \Omega`, variants `\varepsilon \vartheta \varphi \varrho \varpi \varsigma`), `+ - = < > ( ) [ ] | / , ; : ! ' .`, `\{ \}`, `\%`, `\&`, `\#`, `\_`, `\$`.
- Grouping with `{ }`; whitespace is ignored; explicit spaces `\,` `\:` `\;` `\!` `\ ` `\quad` `\qquad`.
- Superscript `^`, subscript `_`, both on one base in either order, nested to depth 3 (smaller each level), prime `'` as a raised prime (repeatable). Scripts on a group `{...}`, on a big operator, or on a delimiter-closed group.
- `\frac{a}{b}` (also `\dfrac`, `\tfrac` as display/text size forms), `\sqrt{x}`, `\sqrt[n]{x}`, `\binom{n}{k}`.
- Big operators `\sum \prod \int \iint \iiint \oint \lim \max \min \sup \inf \bigcup \bigcap`: in display math, limits sit above/below (for the `\int` family they sit at the side); in inline math all limits sit at the side. `\limits` / `\nolimits` override.
- Upright named functions: `\sin \cos \tan \cot \sec \csc \arcsin \arccos \arctan \sinh \cosh \tanh \ln \log \exp \det \dim \gcd \arg \deg \ker \Pr \mod`.
- Binary operators and relations: `\pm \mp \times \cdot \div \ast \circ \le \leq \ge \geq \ne \neq \approx \equiv \sim \simeq \propto \ll \gg \in \notin \ni \subset \subseteq \supset \supseteq \cup \cap \setminus \perp \parallel \to \rightarrow \leftarrow \leftrightarrow \Rightarrow \Leftarrow \Leftrightarrow \mapsto \implies \iff`.
- Misc symbols: `\infty \partial \nabla \forall \exists \neg \emptyset \hbar \ell \angle \degree \prime \ldots \cdots \vdots \ddots \dots`.
- Delimiters: `\left` / `\right` with `( ) [ ] \{ \} | \| \langle \rangle \lfloor \rfloor \lceil \rceil .` (stretch to content height), plus fixed sizes `\big \Big \bigg \Bigg`.
- Text inside math: `\text{...}` (upright, ordinary text, spaces kept).
- Style: `\displaystyle`, `\textstyle` at the start of a group.

L2 (second slice):
- Environments `matrix pmatrix bmatrix Bmatrix vmatrix Vmatrix` (rows separated by `\\`, cells by `&`, cells may be empty, ragged rows padded), `cases` (left brace, two columns, second column text-like), `aligned` (columns separated by `&`, alternating right/left alignment, `\\` rows), `array{lcr}` with a column spec of `l`, `c`, `r` only.
- Accents: `\hat \bar \vec \dot \ddot \tilde \overline \underline`, and `\overbrace` / `\underbrace` with one script as label.
- Font commands: `\mathrm \mathbf \mathit \mathbb` (capitals present in the font, otherwise bold capitals, no error) `\mathcal` (script capitals via font fallback), `\boldsymbol`.
- Extra operators: `\bmod \pmod{n}`, `\operatorname{name}`.
- Extra symbols: only symbols that have a plain Unicode code point in the bundled math font; the developer records the final list in the manual.

Explicitly out of scope (error "unsupported"): `\newcommand`, `\def`, any macro definition, packages (`\usepackage`), colour (`\color`), `\label/\ref/\tag/\eqno` (no equation numbering), tables outside the listed environments, `\begin{equation}`/`\begin{align}` wrappers (use `$$` and `aligned`), TikZ, images, `\href`, `\verb`, `\input`, `\write`.

### 4. Layout rules (own constants, generic typographic ideas)
Developer chooses concrete numbers; spec fixes the relations the tests check.
- Three script levels: script size = 70% of the surrounding size, second-level script = 50%; never below 6 pt on screen at 100% zoom.
- Superscript baseline raised so its bottom sits clearly above the base's x-height; subscript lowered; when both exist, a minimum gap between them.
- Fraction: numerator and denominator centred over a rule whose width is the wider of the two plus a small margin; rule thickness about 6% of the font size; in text style the parts are shrunk to script size.
- Radical: sign drawn as a stroked path (not a font glyph) whose height follows the radicand, with a top rule over the radicand; index drawn small at the upper left.
- Atom spacing: three classes (ordinary, binary operator, relation) with thin/medium/thick gaps; a binary operator at the start of a group or right after another operator/relation is treated as a unary sign (no spaces).
- Stretchy delimiters and braces are painted as paths when taller than 1.4 line heights, otherwise as font glyphs.
- Inline math baseline aligns with the surrounding text baseline; the line containing it grows to fit the formula height (ascent and descent), other lines keep their normal height. Lines never overlap each other because of math.
- Display math: own block, centred in content width, 0.6 line-height gap above and below.

### 5. Error handling (invalid LaTeX)
A span is "invalid" when the parser raises a `TexError` (own exception, carries message and 0-based character offset inside the span). Nothing else changes: the text, the other spans and the app all keep working.
- Display of an invalid span: its raw source, including delimiters, in a monospace font at the surrounding size, in `COLOR_ERROR`, with a dotted underline starting at the error offset.
- Region feedback: the region gets the existing error tint (`COLOR_ERROR_BG`) in display state, and a one-line caption directly under the text (small type, `COLOR_ERROR`, prefix "⚠") with the first error: `LaTeX: unknown command \foo (formula 2, character 7)`. With more than one invalid span the caption ends with `(+N more)`. The whole message list is the region tooltip.
- In edit state the same caption appears live while typing, debounced 250 ms after the last key, and clears as soon as the source is valid. No tint while editing (the edit tint stays), only the caption.
- The caption is on-screen only; it is not printed (decision Q5). In the PDF an invalid span prints as its raw source in the error colour.
- Fixed message set (own wording, `\command` shown as typed):
  - `unknown command \foo`
  - `\frac needs two arguments` / `\sqrt needs an argument` (same pattern for `\binom`, accent commands)
  - `missing closing }` / `unexpected }`
  - `missing \right for \left` / `\right without \left`
  - `missing \end{matrix}` / `\begin{foo} is not supported` / `\end{pmatrix} does not match \begin{matrix}`
  - `double superscript` / `double subscript` (`x^2^3`)
  - `stray $` (display math only), `% is not supported`
  - `formula too deeply nested (limit 32)` and `formula too long (limit 2000 characters)`
  - `unsupported: \newcommand` (any command from the out-of-scope list)
- The scanner, parser, layout and paint code must catch every exception; any non-`TexError` exception inside a span is treated as an invalid span with message `internal error in formula`, logged once, never propagated to Qt event handlers.

### 6. Saving (.lsheet, backward compatible)
- No format change, no version bump. The region `text` stays the HTML string from `editor.toHtml()` of the raw-source document, so the LaTeX is stored as plain characters inside it (`<`, `>`, `&` appear HTML-escaped as already today). Older LiveSheet builds open the file and show the raw `$...$` source as ordinary text.
- `TextRegion.text()` must always return the HTML of the raw-source document, also while in display state. The region keeps the raw document (or its HTML) as the canonical copy and builds the typeset display document from it; `text()`, `is_empty()`, `heading_text()` (Outline tab, decision Q8: raw source), dirty checks and the modified flag all read the raw copy, never the display document.
- Toggling edit/display without typing must not mark the sheet modified and must not change the saved bytes: load, enter-edit, leave-edit, save on an untouched region produces an identical `text` string.
- Do not store any cache, rendered image or layout in the file.

### 7. PDF export and printing
- Math is painted through the same `QPainter` code path as on screen, so on a `QPdfWriter` it stays vector (glyphs as text with embedded fonts, rules, radicals and braces as paths). No `QPixmap`/`QImage` caching of math at any point. Layout boxes may be cached; pixels may not.
- Page splitting (pages.md): the existing rule "a region crossing a page boundary shows its lower part on the next sheet" applies unchanged.
- Printed colour is the token text colour; the error caption and tint are not printed (`sheet.printing` is True during export); an invalid span prints in the error colour.
- `export_pdf` already ends editing before rendering, so regions always print in display state.

### 8. Dark mode
- The canvas currently stays light in dark mode (theme.py). Typeset math therefore uses the same colour tokens as the region text (`#222222` today) and not the application palette. If the canvas is themed later, the one token flips and the math follows with no change.
- No colour is hard-coded inside layout/paint code: the painter colour is passed in per paint call. Error uses `COLOR_ERROR`; hover/selection frames stay those of `Region`.
- Contrast: formula text and the error caption keep at least 4.5:1 against their background (region background, edit tint and error tint).
- Chrome added by this spec (the View toggle, the Insert items) uses native toolkit palette, so it follows light/dark like all other chrome.

### 9. Copy, paste, find
- Copy from a selection in edit state yields the raw source. Paste inserts text as-is and never converts anything; pasted `$...$` typesets when the user leaves edit state.
- No copy of the typeset rendering (as image or MathML) in this spec. Existing region copy/duplicate commands copy the raw HTML as today.
- Selecting text across a typeset formula in display state is not supported (display state is not text-selectable today either).

### 10. Region sizing and line height
- Regions remain auto-width and auto-height; no manual resize is added. Display and edit state have different sizes; the frame follows the current state.
- The region's top-left position does not change between states. A taller typeset region can overlap regions placed below it; LiveSheet does not push anything (consistent with pages.md). The manual mentions this.
- Inline math raises the height of only its own line. A paragraph without math keeps today's line height exactly (existing sheets without valid math spans look unchanged).
- Zoom: math scales with the view like every other item and stays crisp (vector).
- Accessibility: the font size setting scales math with it; in display state the region exposes the raw source (not an object-replacement placeholder) as its accessible text.

### 11. Performance
- Parse+layout of one typical span (under 100 characters) in under 5 ms on a developer laptop; a region with 50 spans enters display state in under 250 ms offscreen.
- Typeset only on: load, leaving edit state, font-size change, View toggle change. Never on worksheet recalculation, and never per keystroke (only the 250 ms-debounced error check parses while editing: the span containing the caret, plus all spans once on entering edit state).
- Layout cache keyed by (source, point size, style); at most 500 entries, least-recently-used eviction.
- Hard limits: 2000 characters per span, nesting 32, 200 spans per region (spans beyond that stay raw with the message `too many formulas in this region (limit 200)`), 50 rows x 50 columns per matrix.

### 12. Insert formula items and View toggle (L2)
- Insert menu gets two items: "Formula (inline)" and "Formula (display)". Suggested shortcuts: `Ctrl+Alt+4` and `Ctrl+Alt+Shift+4` ("4" because it carries the dollar sign on common keyboards; in Qt `Ctrl` is Cmd on macOS). Chosen because every `Ctrl+Shift+<letter>` and `Ctrl+Alt+<letter>` combination is reserved for the Greek-letter layers (main_window.py), and `Ctrl+M`, `Ctrl+T`, `Ctrl+Shift+E/A/P/M/C/S`, `Ctrl+.`, `Ctrl+0` are taken. The developer must verify at implementation time that the combination is not an operating-system shortcut on macOS, Windows and Linux and report back; if it clashes, pick the nearest free `Ctrl+Alt+<digit>` and record it in the manual.
- Behaviour: when a text region is being edited, the item inserts `$$` (inline) or `$$$$` (display) at the caret and puts the caret between the delimiters; with a selection it wraps the selection instead. When a text region is selected but not editing, it starts editing at the end first. When no text region is selected, it creates a new text region at the crosshair position (the same way Insert > Text does) in edit state, already containing the delimiters. The items are disabled while a math or plot region is being edited.
- View menu gets a checkable "Typeset LaTeX in text regions", persisted in the existing QSettings, default on. When off, display state shows the raw source and no scanning happens; `text()` is unchanged either way.

## Bundled font (decision Q2)
- Font: STIX Two Math, SIL Open Font License 1.1, copyright The STIX Fonts Project Authors, registered at start-up (`QFontDatabase.addApplicationFont` on a file from the package resources) and placed first in the math font family chain; the existing `MATH_FONT` families stay behind it as fallback.
- The developer must obtain the font file from the official OFL-licensed distribution only, namely the project's own download page `https://stixfonts.org/` or the project repository `https://github.com/stipub/stixfonts`, using a tagged release. Never copy it from a third-party mirror, a font aggregator, another application's installation or a system folder.
- Checksum step (mandatory, written down): after download, compute SHA-256 of the downloaded release archive and of the extracted `.otf`/`.ttf` file; compare the archive checksum with the value published by the project (release notes or checksum file) if one exists; if the project publishes none, record both computed hashes. Store file name, release tag, download URL, download date and both SHA-256 values in `livesheet/gui/fonts/README.md` and in a log.md line. The tester re-computes the SHA-256 of the packaged file and compares it with that record.
- Package the OFL 1.1 licence text and the font's copyright notice as `livesheet/gui/fonts/OFL.txt` (verbatim from the official distribution), and make sure `pyproject.toml` package data includes both the font and the licence file. Do not rename or modify the font (the Reserved Font Name rule); if the project ships a variable or text font alongside the Math font, ship only the Math font file(s) actually used.
- Mention the font and its licence in the project's third-party notices (README or NOTICE file) and in the manual's licence/about section.
- If the font fails to load at run time (file missing, corrupt), log once and fall back to the system chain; formulas still render, with a visible placeholder box for any code point no font has.

## Technical approach
Renderer options and licences:

| Option | Licence | New dependency | Fit |
|---|---|---|---|
| A. Own small parser plus `QPainter` layout (decided) | ours (MIT OR Apache-2.0) | none | One drawing path for screen, PDF, zoom, colour; full control of error messages. |
| B. matplotlib mathtext | PSF-style, BSD-compatible; pulls in pillow, fonttools, kiwisolver, contourpy, cycler, pyparsing, dateutil, packaging | yes, not approved | Rejected: documented subset reportedly has no matrix environments, image or internal glyph API. |
| C. Web engine plus a JS maths library | LGPL / MIT or Apache | yes, huge | Rejected: heavy, awkward in a scene and in PDF export. |
| D. sympy.printing.latex | BSD | none | Prints only, no parse or render; relevant only to a future LaTeX export. |

Design: the parser has no Qt imports and lives in its own package so it is unit-testable like the engine: `livesheet/texmath/` (`scan.py` for delimiters/spans, `parse.py` giving a small immutable tree: atom, group, script, fraction, radical, operator-with-limits, delimited, matrix, text, space, error). `livesheet/gui/texlayout.py` turns the tree into boxes (width, ascent, descent, children) using `QFontMetricsF` and paints them with `QPainter`. `TextRegion` gains the raw/display split, the span map (display position to source offsets) and the caption item. Inline objects are inserted into the display `QTextDocument` through the toolkit's standard inline-object facility (`QTextObjectInterface`), one per span, so ordinary text flow stays Qt's.

Fonts: Qt cannot read OpenType MATH tables, so spacing constants are fixed fractions of the font size, tuned against the bundled STIX Two Math.

## Syntax proposal (own keywords)
No new LiveSheet statement syntax; no change to the math-region grammar (`:=`, `≡`, `=`, `→`). Only text regions interpret `$...$` / `$$...$$`. Math regions do not. LaTeX in a text region is never sent to the engine and does not define variables.

## Acceptance criteria (testable)
Scanner (L1, pure Python):
1. `"a $x^2$ b"` gives one inline span with source `x^2`, covering offsets 2..7.
2. `"$$\frac{a}{b}$$"` gives one display span `\frac{a}{b}`.
3. `"It costs $5 and $10 each"` gives zero spans. `"$ x$"` and `"$x $"` give zero spans. `"cost \$5 and \$6"` gives zero spans and display text `cost $5 and $6`.
4. `"$a$$b$"` gives two inline spans (sources `a` and `b`). `"$$a$"` gives zero spans (unterminated display math).
5. Display span across a paragraph break `"$$a\n+b$$"` gives one span; inline `"$a\n$"` gives zero.
6. Unterminated `"price $x"` gives zero spans; a 2001-character span source gives one span flagged `too long`.
Parser (L1):
7. `x^2` parses to base `x` with superscript `2`; `x_i^2` and `x^2_i` parse to the same tree; `x^2^3` raises `TexError("double superscript")`.
8. `\frac{1}{2}` parses; `\frac{1}` raises `TexError` with message `\frac needs two arguments`.
9. `\sqrt[3]{x+1}` parses with index `3`.
10. `\sum_{i=1}^{n} i = \frac{n(n+1)}{2}` parses without error; in display style the sum has limits above/below, in inline style at the side.
11. `\alpha+\beta` yields atoms with code points U+03B1 and U+03B2; `\Omega` yields U+03A9; `\foo` raises `TexError("unknown command \foo")` with offset 0.
12. `\left( x \right]` parses (mismatched kinds allowed); `\left( x` raises `missing \right for \left`.
13. `{` raises `missing closing }`; `}` raises `unexpected }`; depth-33 nested braces raise the nesting error without a recursion error.
14. (L2) `\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}` gives a 2x2 matrix with round brackets; `\begin{pmatrix} 1 & 2 \end{matrix}` raises the mismatch error; `\begin{foo}` raises `not supported`.
15. `\newcommand{\x}{1}` raises `unsupported: \newcommand`.
Layout (L1, QApplication offscreen):
16. For `x^2`, the superscript box height is less than the base box height and its baseline offset is above the base baseline; for `x_2` it is below.
17. For `\frac{a}{bcdef}` the fraction width is at least the wider of numerator and denominator widths; the rule y lies between numerator bottom and denominator top.
18. Font size 12 and 24 give a width ratio within 5% of 2.0 for the same formula.
19. Fuzz: 1000 random strings over `{}^_\$ab1 +&` produce either a layout or a `TexError`, never another exception.
Region behaviour (L1):
20. A `TextRegion` created from HTML containing `$x^2$`, not editing: the display document contains exactly one inline object; `text()` returns the original HTML unchanged; `is_empty()` is False; a bold first paragraph `$x$` gives `heading_text()` equal to `$x$` (no placeholder character).
21. After `start_editing()` the editor plain text equals the raw text including the `$`; after `finish_editing()` without typing, `text()` is byte-identical and the sheet's modified flag is unchanged.
22. Typing inside a span and leaving edit state updates the typeset object and `text()` contains the new source.
23. A sheet with `$x^2$` in a text region saves with `"version"` 1 when nothing else raises it; loads with the existing loader; saving unchanged text round-trips byte-identically.
24. An invalid span (`$\foo$`): display shows its raw source, `_has_error` is True (tint), caption starts with `LaTeX: unknown command \foo`, tooltip non-empty; another valid span in the same region stays typeset; nothing raises.
25. The caption clears within 300 ms of correcting the source while editing (test timer / `QTest.qWait`).
26. `export_pdf` on a sheet with a typeset and an invalid formula completes without exception, the page count equals that of the same sheet with plain text of the same line count, and the file starts with `%PDF`. No caption item is rendered when `sheet.printing` is True.
27. Performance: a region with 50 spans, each `\frac{a_i}{b_i}+\sqrt{x^2+y^2}`, enters display state in under 250 ms offscreen (CI fail at 1 s).
L2 behaviour:
28. View toggle off: `$x^2$` stays raw in display state and `text()` is unchanged; toggling back on typesets again without marking the sheet modified.
29. Insert "Formula (inline)" in an editing text region with caret in empty text inserts `$$` and puts the caret at offset 1; with `abc` selected it yields `$abc$`. "Formula (display)" gives `$$$$` with the caret at offset 2. With no text region selected a new text region is created in edit state containing the delimiters. Items are disabled while a math region is being edited.
30. Bundled font: the file exists in the package data, `QFontDatabase.addApplicationFont` returns a non-negative id, the family name appears in `QFontDatabase.families()`, `livesheet/gui/fonts/OFL.txt` exists, and the SHA-256 of the font file equals the value recorded in `livesheet/gui/fonts/README.md`.
Manual checks (real window): light and dark appearance, zoom in and out, double-click on a formula puts the caret in the source, long formula, formula at the page-break line, export a PDF and zoom into it (vector, no blur), Insert shortcut works and does not clash with the OS.

## Edge cases
- A span whose font size varies uses the size at the first `$`.
- Empty text region, only `$`, only whitespace: no spans, no error.
- Unicode already in the source (`$α + β$`): letters accepted as atoms.
- Non-breaking space (U+00A0): treated as whitespace in the scanner and parser.
- Very wide formula: region grows wider (no wrapping), same as long plain text today.
- Formula inside a bold heading (Outline tab): shows the raw source.
- Region deleted or moved while a debounce timer is pending: timer is owned by the region and stopped on destruction.
- Font file missing: fallback glyphs, no crash, placeholder box for any missing code point.
- Drag-move of a typeset region (spec 023) is unchanged; the typeset area counts as the movable body.
- `$` inside a plot's or math region's text is untouched.

## IP check
Pass (manager IP review 2026-11-12: PASS).
- Ideas and notation only: LaTeX math notation is a generic, widely published way to write formulas, comparable to treating `sin`, `\int` and `=` as standard notation (IP-POLICY "Allowed"). The command list is limited to ordinary mathematical symbols and structures; it is not a copy of any vendor or library table.
- No competitor worksheet product consulted, no screenshot, help text, example or file format; no vendor names used. The raw/typeset toggle on focus is common to many editors and is expressed here in own words with own error wording.
- Layout constants and the "box and glue" approach are generic typesetting ideas with LiveSheet's own numbers; no source from TeX, KaTeX, MathJax or matplotlib is to be read or copied by the developer.
- Dependencies: no new Python dependency. The bundled STIX Two Math font is SIL OFL 1.1 (font licence, accepted by Theo 2026-11-12), unmodified, licence file shipped, obtained only from the official distribution with recorded checksums. No GPL/AGPL.
- Patent-style check (ip-cleanroom rule 6): plain toggle between raw and rendered text on focus, and ordinary menu items for Insert; no live on-canvas manipulation of the rendered math, no drag handles. Boring toolkit chrome by design.

## Fits current architecture?
- New Qt-free package `livesheet/texmath/` (scan, parse, errors). Never imports PySide6; testable headless. Engine package untouched.
- New `livesheet/gui/texlayout.py` (layout boxes and painting) and `livesheet/gui/fonts/` (font, OFL.txt, README.md with provenance and checksums).
- `livesheet/gui/regions.py`: `TextRegion` gets the raw/display split via the existing `_enter_edit_display` / `_leave_edit_display` hooks, span map, caption child item, debounce timer. `Region.start_editing` needs a small hook so the caret target is computed before swapping documents (section 1.5). `text()`, `is_empty()` read the raw copy.
- `livesheet/gui/worksheet.py`: `heading_text()` reads the raw copy (add a `TextRegion.raw_document()` accessor).
- `livesheet/gui/main_window.py`: `export_pdf` unchanged; `sheet.printing` hides the caption. L2 adds the View toggle (QSettings) and the Insert items.
- `livesheet/document.py`: no change, no version bump.
- Manual (documenter, after acceptance): new page `docs/manual/latex-text.md` (delimiters, supported list, error messages table, shortcuts, bundled font notice), linked from main-window.md and errors.md.

## Phasing
- L1 (about 3 days): scanner, parser core subset, layout/paint, raw/display toggle, click-to-caret, error handling and caption, saving guarantees, PDF vector path; criteria 1-13, 15-27. Until L2 ships the font chain is the system fallback.
- L2 (about 2 days): matrices/cases/aligned/array, accents, font commands, `\operatorname` etc., View toggle, Insert items with shortcuts, bundled font with provenance record; criteria 14, 28-30.
- L3 (live preview under the region while editing): not approved, not scheduled (decision Q7).

## Open questions
None blocking. Items for the developer to report back: whether `Ctrl+Alt+4` / `Ctrl+Alt+Shift+4` clash with an OS shortcut (section 12), and whether the project publishes a checksum for the STIX release.
