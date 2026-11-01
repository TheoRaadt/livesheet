# The main window

LiveSheet's window has a menu bar, one toolbar, a dockable side panel, and a status bar, on top
of the free-form canvas where your regions live.

## The toolbar

One toolbar, **Standard**, sits at the top of the window: New, Open, Save, Export PDF and
Recalculate. These are the exact same commands as the matching **File** and **Calculate** menu
entries, so clicking a toolbar button and picking the matching menu entry always do exactly the
same thing. You can drag it to a different edge of the window using the window's ordinary toolbar
handling (it cannot be pulled free into its own floating window). **View > Standard Toolbar** shows
or hides it; wherever you leave it, and whether it's shown or hidden, is remembered the next time
you open LiveSheet.

There is no separate Math toolbar — every insertable math building block lives in the side panel
instead, described below, so there is exactly one place to find each one.

## The side panel

**View > Side Panel** shows or hides a dockable panel on the left edge of the window, with ten
tabs, in this order: **Elements**, **Algebra**, **Calculus**, **Statistics**, **Optimization**,
**Mechanical**, **Electrical**, **Chemical**, **Outline**, **Data**. The Mechanical, Electrical and
Chemical tabs hold ready-made engineering formulas; see [Formula tabs](formula-tabs.md). Clicking
any entry in the three tabs below inserts it at the cursor in the
math region you're editing (or creating, if nothing is being edited yet) — the same thing happens
whether you click the button or use one of the keyboard shortcuts described further down.

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
- **Statistics** and **Optimization** — placeholders for now: "Statistical tools (descriptive
  statistics, distributions, hypothesis tests, regression) will appear here once available." and
  "Optimization tools (nonlinear and constrained optimization) will appear here once available."
  They don't do anything yet; they're reserved spots for features that haven't shipped.
- **Outline** and **Data** — placeholders for now ("Document outline will appear here once
  headings are available." and "Imported datasets will appear here once available."); they don't
  do anything yet, and will be filled in once document outlines and dataset import ship.

You can resize the panel (between 120 and 320 pixels wide; the canvas itself always keeps at least
400 pixels), and LiveSheet remembers the panel's open/closed state, its width, and which tab was
active, the next time you open it. (If you're upgrading from a much older version of LiveSheet
that only had three side-panel tabs, the very first time you reopen it the panel may land on a
different tab than the one you last had open — purely cosmetic, and it fixes itself the moment you
click any tab.)

### Typing Greek letters

You can get a Greek letter onto your sheet three ways, all equivalent:

1. **Click its button** in the Elements tab's Greek letters group.
2. **Type its English name by hand** anywhere in a math region — for example, typing `alpha`
   displays as α once you move the cursor on. This works whether or not you ever open the side
   panel.
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
menus, toolbars, the side panel, dialogs, the status bar and scrollbars. It does not change
anything the canvas draws itself: grid lines, region borders, the crosshair, and plot colours keep
their own look regardless of which appearance you pick. Your choice is remembered the next time
you open LiveSheet.

## Starting on a blank sheet

A worksheet with nothing on it yet shows one faint line of hint text, "Click to place the cursor,
then start typing", near where the crosshair will place your first region. It disappears the
moment you place anything (even something you haven't finished typing yet), and comes back if you
delete everything again. It's only a visual hint — it's never saved in your file and never
appears in an exported PDF.
