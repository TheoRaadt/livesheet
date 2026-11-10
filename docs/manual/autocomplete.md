# Autocomplete

While you type in a math region, LiveSheet can show a small list of names that match what you have
typed so far, so you do not have to remember or type every function name in full. You can pick one
from the list or ignore it and keep typing.

## What the list shows

The list appears just under the line you are typing, at the start of the word. Each row has:

- the name, for example `mean`;
- a short grey hint showing how to call it, for example `mean(v)` or `predict(coeffs, x)`;
- for some rows, a small tag in square brackets: `[const]` for constants such as `pi`, `[var]` for
  a variable you defined elsewhere on the sheet, and `[user]` for a function you defined yourself.

It offers three kinds of names:

- **Built-in functions**, for example `sin`, `sqrt`, `diff`, `integrate`, `mean`, `fit_linear`.
- **Constants**, for example `pi` and `e`.
- **Your own names**: variables and functions defined in other regions on the same sheet. It does
  not matter whether the definition is above or below the region you are typing in. A function you
  defined with parameters shows them in its hint, for example `area(w, h)`. A line that only
  evaluates something (such as `total =`) does not define a name, so it is not offered.

If you define a name that is also a built-in name, only your own is listed.

It does **not** offer unit names (`m`, `kg`, `MPa` ...), the solve-model keywords (`vary`,
`settle` ...) or Greek letter names such as `alpha`. The one Greek name that does show up is
`Gamma`, because it is also a built-in function.

Matching ignores capital letters. When several names match, names that match your capitals exactly
come first, then your own names, then shorter names, then alphabetical order. For example, typing
`me` lists `mean` first and `median` next. The list shows 8 rows at a time and scrolls if there are
more.

## When it opens

The list opens after you have typed **two letters** of a word, and only when all of this is true:

- the word starts with a letter (or an underscore), so `2m`, `3.5e` and `10s` never open it;
- the caret is at the **end** of the word. Typing in the middle of an existing word, such as between
  `sq` and `rt` in `sqrt`, does not open it;
- at least one name matches, and you have not already typed a complete name that is the only match
  (typing `mean` in full shows nothing);
- you are editing a math region. Text regions and plot settings never show it.

It updates as you keep typing or press Backspace or Delete. Typing anything that is not part of a
word (a space, an operator, `(`, `,`, `:`) closes it. Moving the caret with the Left or Right arrow
keys, Home or End, clicking elsewhere, or leaving the region also closes it.

## Choosing a name

| Key | What it does |
|---|---|
| Down / Up | Move the highlight. At the last row, Down wraps to the first; at the first row, Up wraps to the last. The first row is highlighted when the list opens. |
| Page Down / Page Up | Move the highlight by one screenful (8 rows), stopping at the ends. |
| Tab | Accept the highlighted row. |
| Esc | Close the list. The region stays open for editing and your text is unchanged. |
| Enter | Finish the region as usual. It does **not** accept the highlighted row. |

You can also **click a row with the mouse** to accept it. The list never takes the keyboard from
you; the caret stays where it was in the region.

Accepting replaces the letters you typed with the full name:

- A function is inserted with its opening bracket, for example `median(`. You then type the
  arguments and the closing `)` yourself.
- A constant or a plain variable is inserted as just the name, for example `pi`.
- If the character right after the caret is already `(` (you are changing the name of an existing
  call), only the name is inserted, so you do not end up with `((`.

After accepting, the caret sits right after the inserted text and you carry on typing.

If you press Esc, the list stays closed for the rest of that word, even as you type more letters of
it. It comes back when you start a new word. Pressing Esc a second time (with no list showing)
leaves editing, as it always did.

Tab only does something special while the list is open. With the list closed, Tab behaves as it did
before.

## Worked example

You want the median of a list of measurements.

1. Click an empty spot on the canvas and start a new math region.
2. Type `x := me`. A list opens with `mean` first
   (hint `mean(v)`) and `median` second.
3. Press Down once. `median` is highlighted.
4. Press Tab. The text becomes `x := median(`, with the caret after the bracket.
5. Type `[3, 1, 2])` and press Enter. The region commits.

If you instead wanted to type `me` as your own variable name, press Esc and keep typing, or just
press Enter. The list does not accept anything on its own.

## Greek letters and autocomplete

The Greek-letter buttons and keyboard shortcuts (see
[Typing Greek letters](main-window.md#typing-greek-letters)), the other tab buttons, the Matrix
dialog and pasted text insert text for you, so they **never open the list**. If a list happens to be
open when one of them inserts text, the list closes.

If you type a Greek name by hand, the list opens only when a built-in name begins with what you
typed. `alp`, `beta` and `mu` show nothing. `Gam` shows `Gamma`; pressing Tab inserts `Gamma(`,
which is shown as `Γ(` once you leave the region, exactly as if you had typed it yourself.

What the list inserts is always plain text, so the saved sheet and the displayed result are the same
as if you had typed the name by hand.

## Exporting

The list is never part of a printed or exported page.

## If something goes wrong

Autocomplete has no error messages of its own. See [Error messages](errors.md#autocomplete).
