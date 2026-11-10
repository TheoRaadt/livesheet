# The main window

LiveSheet's window has a menu bar, one toolbar, a tab strip with a button band under it, and a
status bar, around the free-form canvas where your regions live.

## The toolbar

One toolbar, **Standard**, sits at the top of the window: New, Open, Save, Export PDF and
Recalculate. These are the exact same commands as the matching **File** and **Calculate** menu
entries, so clicking a toolbar button and picking the matching menu entry always do exactly the
same thing. You can drag it to a different edge of the window using the window's ordinary toolbar
handling (it cannot be pulled free into its own floating window). **View > Standard Toolbar** shows
or hides it; wherever you leave it, and whether it's shown or hidden, is remembered the next time
you open LiveSheet.

### How the toolbar looks

Each toolbar button is a small picture with its name beside it: **New**, **Open**, **Save**,
**Export PDF** and **Recalculate**. The buttons are deliberately larger than the buttons in the
button band below, and a little taller than the tabs, so they are easy to hit. The pictures and the
button height grow along with your system's text size, and the pictures are drawn sharply on
high-resolution screens. They also follow Light and Dark appearance.

The **File** and **Calculate** menus do not show these pictures; their entries look the same as
before.

### When the window is narrow

The toolbar never forces the window to be wider. As you make the window narrower:

1. While there is room, every button shows its picture and its name.
2. When the names no longer fit, the buttons switch to **picture only**, at the same size. Hover
   over a button to see its name and shortcut, for example `Save (Ctrl+S)`,
   `Export PDF (Ctrl+Shift+E)` or `Recalculate (F9)`. Screen readers still announce the full name.
3. If even the pictures do not fit, a small **chevron** (`>>`) appears at the right end of the
   toolbar. Click it to see the hidden commands by name.

To keep the toolbar from flickering while you drag the window edge, the names come back only once
the window is a little wider (about 24 pixels) than the width at which they disappeared. If you
drag the toolbar to the left or right edge of the window, it shows pictures only and stacks the
buttons vertically.

There is no separate Math toolbar — every insertable math building block lives in the tab strip
and button band instead, described below, so there is exactly one place to find each one.

## The tab strip and button band

Directly under the toolbar, across the whole width of the window, is a **tab strip** with ten
tabs, in this order: **Elements**, **Algebra**, **Calculus**, **Statistics**, **Optimization**,
**Mechanical**, **Electrical**, **Chemical**, **Outline**, **Data**. Under the strip is the
**button band**, which shows the buttons of whichever tab is selected. There is no panel on the
left edge of the window any more, so the canvas uses the full width.

**View > Side Panel** shows or hides the strip and the band together (the menu entry keeps its
old name). Showing them again brings back the tab you last had selected.

### How the strip behaves

- Every tab always shows its full name. If the window is too narrow to fit all ten tabs on one
  line, the strip continues on a second (or third, ...) row below instead of hiding tabs behind
  scroll arrows. Widen the window and the tabs flow back onto fewer rows.
- Each row is stretched so the tabs fill the full width. Tabs keep their order, and selecting a tab
  never moves it.
- The selected tab is shown in the accent colour with bold text, so it stands out in light and dark
  appearance alike.
- Click a tab to select it. The window cannot be made narrower than the widest tab name needs.

### Using the strip with the keyboard

The strip is one stop in the Tab key order. Once it has keyboard focus:

| Key | What it does |
|---|---|
| Left / Right | Select the previous / next tab (nothing happens at the first / last tab) |
| Up / Down | Select the tab nearest above / below on the row above / below (nothing if there is no row there) |
| Home / End | Select the first / last tab |
| Space or Enter | Select the focused tab |

Switching tabs never takes the keyboard focus away from a region you are editing.

### The button band

- The band shows only the selected tab's buttons, using the window's width: buttons flow left to
  right and wrap to further rows. Tabs with groups (Elements, Statistics, Optimization,
  Mechanical, Electrical, Chemical)
  show each group's small grey heading, and each group starts on a new row. Algebra and Calculus
  have no heading.
- Statistics and Optimization show groups of function and line templates, Outline lists your
  sheet's headings, and only Data still shows just a short grey message (see below).
- The band stays the same height when you switch tabs, so the canvas does not jump. It gets taller
  or shorter only when you resize the window. It never grows past about four rows of buttons (or a
  quarter of the window's height, if that is larger); a tab with more buttons than that scrolls up
  and down inside the band, while the strip itself never scrolls.

The Mechanical, Electrical and Chemical tabs hold ready-made engineering formulas; see
[Formula tabs](formula-tabs.md). Clicking any button in the tabs below inserts it at the cursor in
the math region you're editing (or creating, if nothing is being edited yet) — the same thing
happens whether you click the button or use one of the keyboard shortcuts described further down.

- **Elements** — the handful of symbols and operators you reach for on almost any line, in three
  groups:
  - *Statements*: `:=` (Definition), `≡` (Global definition), `=` (Evaluate numerically), `→`
    (Evaluate symbolically).
  - *Constants*: `π` (inserts `pi`), `e` (Euler's number), `i` (Imaginary unit, inserts `I`).
  - *Greek letters*: one button per Greek letter LiveSheet recognises — 23 lowercase glyph buttons
    (α β γ δ ε ζ η θ ι κ λ μ ν ξ ο ρ σ τ υ φ χ ψ ω, for alpha, beta, gamma, delta, epsilon, zeta,
    eta, theta, iota, kappa, lambda, mu, nu, xi, omicron, rho, sigma, tau, upsilon, phi, chi, psi,
    omega) and 10 uppercase glyph buttons (Γ Δ Θ Λ Ξ Π Σ Φ Ψ Ω, for Gamma, Delta, Theta, Lambda,
    Xi, Pi, Sigma, Phi, Psi, Omega). Clicking a Greek-letter button inserts the plain English name
    (e.g. the `α` button inserts the text `alpha`) — LiveSheet already displays that text as the
    glyph once you move on, so clicking the button is just a shortcut for typing the word yourself.
- **Algebra** — `√` (Square root, inserts `sqrt(`), `ⁿ√` (Nth root, inserts `root(` — use it as
  `root(expr, n)`), `x²` (Square, inserts `^2`), and `xₙ` (Subscript, inserts a single `_`) — see
  "Typing a subscript" below.
- **Calculus** — `d/dx` (Derivative, inserts `diff(` — use it as `diff(expr, x)`) and `∫` (Integral,
  inserts `integrate(` — use it as `integrate(expr, x)` or `integrate(expr, x, a, b)`).
- **Statistics** — 37 buttons in four groups, each inserting a ready-to-edit template: *Summary
  statistics* (10), *Distributions* (16), *Hypothesis tests* (7) and *Regression* (4). Hover a
  button for a one-line meaning. See [Statistics](statistics.md#the-statistics-tab).
- **Optimization** — 9 buttons in three groups for solve models: *Unknowns and constraints*,
  *Settings (optional)* and *Results*. See [Optimization](optimization.md).
- **Outline** — a list of your sheet's headings; click one to jump to it. See
  [The Outline tab](#the-outline-tab) below.
- **Data** — still a placeholder that only says "Imported datasets will appear here once
  available."; it does nothing yet.

The template buttons put readable stand-in names into the line, for example `mean(v)`. After
clicking, replace the stand-ins (`v`) with your own names.

### The Outline tab

The Outline tab is a table of contents for your sheet. It lists every text region whose **first
paragraph is entirely bold**, and clicking an entry takes you to that region.

**Making a heading.** Click into a text region, make its first line bold (select it and press
`Ctrl+B`) and leave editing. If only part of the first paragraph is bold (say just the first
word), the region is not a heading. Math, plot and component regions never appear in the outline.
The outline has one flat list, with no levels.

**Using it.**

1. Click the **Outline** tab. One button appears per heading.
2. Click a button. The region is selected and the canvas scrolls so it sits near the top of the
   window. Your zoom does not change, and if you were typing in a region you keep typing there.

**What the entries look like.** The button shows the heading's text, with extra whitespace
squeezed together; text longer than 32 characters is cut off with an ellipsis (`…`). Hover for the
full text and the page number.

**Order and pages.** Entries are in reading order: page by page (pages are split by
[page breaks](pages.md)), then top to bottom, then left to right. If your sheet has page breaks,
each page that has at least one heading gets a small grey header, "Page 1", "Page 2", and so on.
A sheet without page breaks shows no page headers. Two headings with the same text are both
listed.

**Worked example.** You have three text regions, "Intro" (all bold), "Some prose" (not bold) and
"Results" (bold). The Outline tab shows two buttons, **Intro** and **Results**. Clicking
**Results** jumps to it.

**Empty sheet.** If there is nothing to list, the band shows: "No headings yet. Make the first
line of a text region bold (Ctrl+B) to list it here."

**When it updates.** The list is rebuilt when you select the Outline tab, when a sheet is opened
or cleared, and, while the Outline tab is showing, shortly (about a third of a second) after you
add, delete or move a region, edit text, or change a page break. While another tab is showing,
nothing is recomputed. If you delete a heading, its button disappears at the next update, and
clicking a button for a region that is already gone does nothing.

The outline is worked out from your text; nothing extra is saved in the file.

LiveSheet remembers whether the strip and band are shown and which tab was selected, and restores
both the next time you open it. (If you're upgrading from an older version, the first time you
reopen it the strip may land on a different tab than the one you last had open — purely cosmetic,
and it fixes itself the moment you click any tab. An old saved window layout that mentioned the
left-hand panel is simply ignored.)

### Typing Greek letters

You can get a Greek letter onto your sheet three ways, all equivalent:

1. **Click its button** in the Elements tab's Greek letters group.
2. **Type its English name by hand** anywhere in a math region — for example, typing `alpha`
   displays as α once you move the cursor on. This works whether or not the tab strip is shown.
3. **Use a keyboard shortcut**, while a math region is being created or edited, for the *lowercase*
   letters only (uppercase letters are click-only — there's no shortcut for Γ, Δ, Θ, Λ, Ξ, Π, Σ, Φ,
   Ψ or Ω). There are two separate sets of shortcuts, and both always work — a letter that appears
   in both tables inserts the same Greek letter either way:

   **`Ctrl+Shift+<letter>`** — covers 11 of the 23 lowercase letters. Only letters whose English
   name starts with a letter not already used by another LiveSheet shortcut (such as `Ctrl+Shift+A`
   for Select All Regions) get one here, and only if that starting letter isn't shared by another
   Greek name:

   | Shortcut | Inserts | Letter |
   |---|---|---|
   | Ctrl+Shift+B | beta | β |
   | Ctrl+Shift+G | gamma | γ |
   | Ctrl+Shift+D | delta | δ |
   | Ctrl+Shift+Z | zeta | ζ |
   | Ctrl+Shift+I | iota | ι |
   | Ctrl+Shift+K | kappa | κ |
   | Ctrl+Shift+L | lambda | λ |
   | Ctrl+Shift+N | nu | ν |
   | Ctrl+Shift+X | xi | ξ |
   | Ctrl+Shift+R | rho | ρ |
   | Ctrl+Shift+U | upsilon | υ |

   Note that there is no `Ctrl+Shift+S` for sigma: `Ctrl+Shift+S` is already your system's Save As
   shortcut, so sigma isn't available under this first set at all. Use `Ctrl+Alt+S` instead (next
   table), or click the `σ` button.

   **`Ctrl+Alt+<letter>`** — covers all 23 lowercase letters, with no gaps:

   | Shortcut | Inserts | Letter |
   |---|---|---|
   | Ctrl+Alt+A | alpha | α |
   | Ctrl+Alt+B | beta | β |
   | Ctrl+Alt+C | chi | χ |
   | Ctrl+Alt+D | delta | δ |
   | Ctrl+Alt+E | epsilon | ε |
   | Ctrl+Alt+G | gamma | γ |
   | Ctrl+Alt+H | eta | η |
   | Ctrl+Alt+I | iota | ι |
   | Ctrl+Alt+K | kappa | κ |
   | Ctrl+Alt+L | lambda | λ |
   | Ctrl+Alt+M | mu | μ |
   | Ctrl+Alt+N | nu | ν |
   | Ctrl+Alt+O | omicron | ο |
   | Ctrl+Alt+P | phi | φ |
   | Ctrl+Alt+Q | psi | ψ |
   | Ctrl+Alt+R | rho | ρ |
   | Ctrl+Alt+S | sigma | σ |
   | Ctrl+Alt+T | theta | θ |
   | Ctrl+Alt+U | upsilon | υ |
   | Ctrl+Alt+W | omega | ω |
   | Ctrl+Alt+X | xi | ξ |
   | Ctrl+Alt+Y | tau | τ |
   | Ctrl+Alt+Z | zeta | ζ |

   A handful of these use a letter other than the Greek name's own first letter, because two or
   more Greek names start with the same letter (epsilon/eta, theta/tau, phi/psi, omicron/omega):
   `H` for eta (its uppercase form Η looks like a Latin H), `W` for omega (ω looks like a stacked,
   rounded "w"), and `Y`/`Q` for tau/psi (no natural look-alike for either, so these two are simply
   a free letter picked for them).

**Worked example.** Say you want to define an angle named with the Greek letter alpha and give it
a value of 30 degrees. Click on an empty part of the canvas to place the cursor, then either click
the `α` button in the Elements tab or press `Ctrl+Alt+A`. LiveSheet inserts the text `alpha` into a
new math region. Now type `:= 30 deg` and press Enter. The region shows:

```
α := 30 deg
```

with `α` already rendered as the glyph, even though what you actually typed was the word `alpha`.

### Typing a subscript

The Algebra tab's `xₙ` button (tooltip "Subscript") inserts a single underscore character, `_`, at
the cursor — the same kind of plain text-insertion the `x²` button already does for squaring.
Typing a name right after it turns into a subscript once you move the cursor on, the same way
`alpha` turns into α.

**Worked example.** Say you're defining the first of several velocity values and want it to
display as a subscripted v. Click on the canvas to start a math region, type `v`, then click the
`xₙ` button (or type `_` yourself) and continue typing `1 := 10 m/s`. What you typed was
`v_1 := 10 m/s`; it displays as:

```
v₁ := 10 m/s
```

This subscript button is unrelated to the square brackets `[` and `]` you use to index into a
vector or matrix (see [Vectors and matrices](matrices.md)) — `[`/`]` still work exactly as they did
before, and clicking `xₙ` never inserts a bracket.

## The status bar

The status bar's right-hand side always shows three things, left to right:

- **Evaluation status** — "Ready" once everything on the sheet last recalculated with no errors,
  or "1 error"/"N errors" when one or more regions are currently showing a problem. While a
  recalculation pass is unusually slow (noticeably over a third of a second), it reads
  "Calculating…" for a moment first.
- **Precision** — how many significant figures LiveSheet is currently displaying results with (for
  example "6 sig. figs"). Click it to open the same **Result Precision…** dialog as
  **Calculate > Result Precision…**.
- **Zoom** — your current zoom level as a percentage.

The left-hand side of the status bar still shows short, temporary messages (for example "Saved
myfile.lsheet" right after you save).

## Appearance

**View > Appearance** lets you choose:

- **Follow System** (the default) — matches your operating system's own light/dark setting.
- **Light**
- **Dark**

Switching takes effect immediately, no restart needed, and restyles the window's own chrome —
menus, toolbars, the tab strip and button band, dialogs, the status bar and scrollbars. It does not change
anything the canvas draws itself: grid lines, region borders, the crosshair, and plot colours keep
their own look regardless of which appearance you pick. Your choice is remembered the next time
you open LiveSheet.

## Starting on a blank sheet

A worksheet with nothing on it yet shows one faint line of hint text, "Click to place the cursor,
then start typing", near where the crosshair will place your first region. It disappears the
moment you place anything (even something you haven't finished typing yet), and comes back if you
delete everything again. It's only a visual hint — it's never saved in your file and never
appears in an exported PDF.
