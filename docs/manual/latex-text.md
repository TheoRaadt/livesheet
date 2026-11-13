# LaTeX formulas in text regions

In a text region you can write formulas in LaTeX notation between dollar signs. While you are not
editing the region, they appear as properly typeset mathematics; when you click into the region you
get your source back and can edit it. Math regions do not read dollar signs, and a LaTeX formula
never defines a variable or takes part in the calculation.

## Writing a formula

- Inline formula, in the middle of a line: `The area is $A = \pi r^2$ for a circle.`
- Display formula, on its own centred line: `$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$`. A display
  formula may run over several lines.

Rules for the dollar signs:

- Write `\$` for a real dollar sign. It shows as `$` when typeset.
- An inline formula needs a non-space character right after the opening `$` and none right before
  the closing `$`, and the closing `$` must not be followed by a digit. So `It costs $5 and $10
  each` stays plain text. Inline formulas never run over a line break.
- A `$` with no partner, or empty math, is simply plain text, with no error.
- A text region that already has a valid `$...$` pair typesets after you update, because the
  feature reads every text region. Use `\$` or the View switch below to keep the old look.

Typesetting happens only when you leave editing (and on opening a sheet, changing the font size, or
changing the View switch), never while you type. Double-clicking a formula puts the caret inside its
source, near the start if you clicked its left half and near the end if you clicked the right half.

## Insert and View menu

- **Insert > Formula (inline)** (Ctrl+Alt+4, that is Cmd+Option+4 on a Mac) puts `$$` at the caret
  and places the caret between the signs. With text selected, it wraps the selection: `abc` becomes
  `$abc$`.
- **Insert > Formula (display)** (Ctrl+Alt+Shift+4) does the same with `$$$$`.
- If a text region is selected but not being edited, the item starts editing it first. If no text
  region is selected, a new text region opens at the crosshair, already holding the signs. The
  items are greyed out while you edit a math or plot region.
- **View > Typeset LaTeX in text regions** is a tick box (on by default and remembered). Off shows
  the raw source everywhere. The saved text is the same either way.

## Supported commands

Anything not listed here is reported as an error rather than ignored.

- **Letters and numbers**: digits, Latin letters (shown italic), Greek letters `\alpha` to
  `\omega`, capitals such as `\Gamma \Delta \Theta \Lambda \Xi \Pi \Sigma \Upsilon \Phi \Psi \Omega`,
  and `\varepsilon \vartheta \varphi \varrho \varpi \varsigma`.
- **Structure**: `{ }` grouping; powers `^`, subscripts `_` (both together, nested), primes `'`;
  `\frac{a}{b}` (also `\dfrac`, `\tfrac`), `\sqrt{x}`, `\sqrt[n]{x}`, `\binom{n}{k}`.
- **Big operators**: `\sum \prod \int \iint \iiint \oint \lim \max \min \sup \inf \bigcup \bigcap`.
  In a display formula the limits sit above and below (beside the sign for integrals); in an inline
  formula they sit at the side. `\limits` and `\nolimits` override.
- **Named functions** (upright): `\sin \cos \tan \cot \sec \csc \arcsin \arccos \arctan \sinh \cosh
  \tanh \ln \log \exp \det \dim \gcd \arg \deg \ker \Pr \mod`, plus `\operatorname{name}`,
  `\bmod`, `\pmod{n}`.
- **Operators and relations**: `\pm \mp \times \cdot \div \ast \circ \le \leq \ge \geq \ne \neq
  \approx \equiv \sim \simeq \propto \ll \gg \in \notin \ni \subset \subseteq \supset \supseteq \cup
  \cap \setminus \perp \parallel`, the arrows `\to \rightarrow \leftarrow \leftrightarrow \Rightarrow
  \Leftarrow \Leftrightarrow \mapsto \implies \iff`, and more such as `\land \lor \oplus \otimes
  \cong \vdash \models`.
- **Symbols**: `\infty \partial \nabla \forall \exists \neg \emptyset \hbar \ell \angle \degree
  \prime \ldots \cdots \vdots \ddots \dots`, and for example `\aleph \Re \Im`.
- **Brackets**: `\left` and `\right` with `( ) [ ] \{ \} | \| \langle \rangle \lfloor \rfloor \lceil
  \rceil` or `.` (nothing), which stretch to fit; fixed sizes `\big \Big \bigg \Bigg`.
- **Spaces**: `\,` `\:` `\;` `\!` `\ ` `\quad` `\qquad`. Ordinary spaces are ignored.
- **Text inside a formula**: `\text{...}` (upright, spaces kept).
- **Style**: `\displaystyle`, `\textstyle` at the start of a group.
- **Tables**: the environments `matrix pmatrix bmatrix Bmatrix vmatrix Vmatrix` (rows split by `\\`,
  cells by `&`), `cases`, `aligned`, and `array{lcr}` (column letters `l`, `c`, `r` only), up to 50
  rows by 50 columns.
- **Accents and braces**: `\hat \bar \vec \dot \ddot \tilde \overline \underline \overbrace
  \underbrace`.
- **Fonts**: `\mathrm \mathbf \mathit \mathbb \mathcal \boldsymbol`.

Not supported: `\newcommand`, `\def`, packages, `\color`, `\label`, `\ref`, `\tag`, equation
numbering, `\begin{equation}` or `\begin{align}` wrappers (use `$$` with `aligned`), pictures and
links.

Limits: 2000 characters per formula, nesting up to 32 levels, 200 formulas per region.

## Worked example

Type, in a text region:

```
The roots are $$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$ for $a \ne 0$.
```

Click outside the region: the quadratic formula appears centred on its own line, and `a \ne 0`
appears inside the sentence.

## When a formula is wrong

A mistake never loses your text. The wrong formula is shown as its source in red, with a dotted
line under it from the position of the problem, the region gets a red tint, and a line under the
text reads for example `LaTeX: unknown command \foo (formula 2, character 7)` (with `(+N more)` when
several are wrong; the tooltip lists them all). While you edit, the same line updates about a
quarter of a second after you stop typing. Other formulas in the region stay typeset. The red line
and tint are not printed. See [LaTeX formulas in the error reference](errors.md#latex-formulas-in-text-regions).

## Saving, printing, other notes

- The file keeps your source text. Opening a saved sheet in an older LiveSheet shows the raw
  `$...$` text. Looking at a region and leaving it again does not change the sheet.
- Export PDF draws the formulas as vector graphics.
- A region with a tall formula grows downwards and can overlap regions below it; nothing is moved
  for you. A bold first line with a formula shows the raw source in the Outline tab.
- Copy gives the source text, and pasted `$...$` typesets when you leave editing.
- The formulas use the bundled STIX Two Math font (SIL Open Font License 1.1).
