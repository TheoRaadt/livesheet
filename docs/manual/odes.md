# Differential equations (ode / start / over / evolve)

This feature lets you write one or more ordinary differential equations with their starting
conditions directly on the sheet, in whatever units your problem uses, and ask LiveSheet for a
solution. When an exact formula exists, you get a closed-form answer you can use anywhere a
function is usable on the sheet (evaluate it at a point, put it in a table, chart it). When no
exact formula exists, LiveSheet automatically falls back to a numeric answer instead of giving up
— a table of sampled points that is still usable as a function, so you never have to leave the
sheet or decide up front whether your problem has a closed form.

## How the pieces fit together

A differential-equation problem needs several pieces of information that don't fit on one line:
the equation (or several, for a coupled system), the starting conditions, and — for a numeric
answer — the range you want it reported over. LiveSheet handles this the same way it handles any
other multi-line calculation on a free-form sheet: you write each piece as its own one-line region,
anywhere on the canvas, and tag every region that belongs together with a trailing `in <name>`.
LiveSheet collects every region sharing the same tag, in calculation order (left to right, then top
to bottom, page by page; see [Pages and page breaks](pages.md)), and solves them together once it reaches a dedicated result line for that tag. You can mix
tagged regions for different problems freely on the same sheet — only the shared tag name groups
them.

For a differential-equation system, the tagged region kinds are `ode`, `start`, `over` (only needed
for a numeric answer), `accuracy`/`steps` (optional settings), and the result line, `evolve`.

## Writing one equation, or a system of them

```
ode diff(y(t), t) + y(t)/tau == 0 in decay
```

An `ode` line's left-hand side must be exactly one derivative, alone, written with `diff`:
`diff(y(t), t)` for a first derivative, or `diff(y(t), t, 2)` for a second derivative (and so on).
`y` is the unknown function you're solving for, and `t` is the variable you're differentiating with
respect to (the "independent variable" — usually time, but it can be any name). Everything after
`==` can be any expression in `t`, in parameters you've defined elsewhere, and — for a coupled
system — in other functions of the same system.

To write a higher-order equation or a coupled system, use several `ode` lines with the same tag:

```
ode diff(x(t), t) == v(t) in fall
ode diff(v(t), t) == -g in fall
```

Every `ode` line of one tag must differentiate with respect to the same variable name. Mixing `t`
in one line and `s` in another, for the same tag, is rejected.

## Giving the starting point

```
start y(0) == 10 m in decay
```

One `start` line can give several conditions, separated by commas, and for several functions at
once. Mark a derivative's initial value with a prime after the function name — one prime per
order, the same mark you'd use writing it by hand: `y'(0) == 0` for the first derivative's value,
`y''(0) == 0` for the second, and so on. You need exactly one condition for every order from 0 up
to one less than the equation's own highest order — for a second-order equation that means the
value `y(0)` and the slope `y'(0)`, no more and no less — and every condition (across every
function of that tag) must be given at the same point.

## A sampling range — only needed for a numeric answer

```
over t from 0 to 1 points 101 in pend
```

Same shape as a plot's own `over` line (see [Plots](plots.md)): a name (the same name as your
equations' independent variable), a start and end value, and optionally `points N` (defaults to
101 when left out). This line declares both the grid LiveSheet reports a numeric answer on, and a
consistency check — it must start at the same point your `start` line's conditions are given at.
You don't need an `over` line at all when a closed form is found and you didn't force a numeric
answer.

## Settings: accuracy and steps

```
accuracy 1e-3 in pend
steps 20000 in pend
```

Optional, and only relevant to a numeric answer (ignored once a closed form is used). `accuracy`
is the numeric solver's relative tolerance — smaller means stricter, default `1e-6`. `steps` is the
maximum number of internal steps the solver is allowed to take before giving up — default `10000`.
These are different defaults from the numbers used by other solving features elsewhere on the
sheet; tune them here if a model needs tighter accuracy or a bigger step budget.

## Asking for the answer

```
evolve in decay            try an exact formula first; fall back to numeric if none is found
evolve symbolic in decay   exact formula only — error if none exists
evolve numeric in decay    numeric answer only, skipping the exact-formula attempt
```

Write exactly one `evolve` line below every region of a given tag (same rule as everywhere else on
the sheet: a region only sees tagged regions that are calculated before it: further left, or in the same column higher up,
on the same page or an earlier one). Any `ode`,
`start`, `over`, `accuracy` or `steps` line for a tag that has no `evolve` line below it is left
with an error — LiveSheet doesn't know whether to wait for more, so it tells you where to add the
missing `evolve` line.

## Worked example: an exact formula

An object's temperature (or anything else that decays exponentially) satisfies `dy/dt = -y/tau`.
Write:

```
ode diff(y(t), t) + y(t)/tau == 0 in decay
tau := 4 s
start y(0) == 10 m in decay
evolve in decay
```

The `evolve` line's result starts with `⇒` and shows the formula LiveSheet worked out, one clause
per function:

```
⇒ y(t) = 10·m·exp(-t/(4·s))
```

`y` is now bound exactly like a function you defined yourself with `y(t) := ...` — you can use it
in any later region on the sheet. For example, below the `evolve` line:

```
y(4 s) =        ->  = 3.67879 m
y(0 s) =        ->  = 10 m
```

`t` itself is **not** bound to any one value afterward — there's no single "the" value of an
independent variable — so a region above the result that mentions `y` or `t` sees them as whatever
(if anything) they meant before, undisturbed by this model.

## Worked example: an automatic numeric answer

Not every equation has an exact formula. A simple pendulum, `d²θ/dt² = -sin(θ)`, is a classic
example:

```
ode diff(theta(t), t, 2) + sin(theta(t)) == 0 in pend
start theta(0) == 0.2, theta'(0) == 0 in pend
over t from 0 to 1 points 101 in pend
evolve in pend
```

Plain `evolve` tries an exact formula first, doesn't find one for this equation, and automatically
falls back to a numeric answer instead of erroring — you don't have to know in advance which kind
of answer your equation has. The result reads:

```
⇒ numeric solution, 101 points
```

and the region also shows an inline table — one row per sampled point of `t`, one column per
function — the same table rendering the `table` statement already uses elsewhere on the sheet.

A simpler numeric example you can check by hand: the same kind of decay as the first example, but
with no units, so the numbers are easy to verify directly:

```
ode diff(y(t), t) + 2*y(t) == 0 in forced
start y(0) == 5 in forced
over t from 0 to 2 points 5 in forced
evolve numeric in forced
```

`evolve numeric` skips the exact-formula attempt entirely. The result is

```
⇒ numeric solution, 5 points
```

with a 5-row table at `t = 0, 0.5, 1, 1.5, 2` and `y ≈ 5, 1.83940, 0.67668, 0.24894, 0.09158` — the
same values exponential decay `5·e^(-2t)` gives by hand.

## Using a numeric answer afterward

A numeric `evolve` binds its independent variable as an ordinary sampled range (the same kind of
thing `t := 0 to 2` already produces) and each function as a usable function, exactly like the
exact-formula case:

```
y(1) =                     ->  = 0.67668
table t, y(t)               gives the same 5 rows the evolve region's own table shows
```

```
plot
over t
show y(t)
```

draws one trace using the same bound function. Because the function and the range both come from
the same model, this all works without retyping any numbers.

## Forcing a numeric answer on an equation that does have an exact formula

`evolve numeric` always skips the exact-formula attempt, even for an equation that would have
solved exactly — useful if you'd rather see a table than a formula, or you want to sanity-check the
numeric solver against a known answer. It still needs an `over` line, the same as any other numeric
answer.

## A note on units in your starting conditions

LiveSheet checks that your equation's and your starting conditions' units are consistent with each
other wherever that check is possible, and reports `Units do not match` style errors (see
[Error messages](errors.md#differential-equations)) when it finds a real inconsistency — for
example, giving two derivative orders of the same function in units that don't agree with each
other given how many times the independent variable's own unit divides in.

One case is deliberately **not** flagged, and this is expected, checked behaviour rather than a gap:
for some equations (the exponential-decay example above is one of them), the unknown function's own
unit never actually appears in any constraint the equation itself imposes — only `tau` and `t` need
to share a unit for that particular equation. In that situation, giving `y(0)` with no unit at all
is just as mathematically consistent as giving it in metres, so LiveSheet accepts both; there is no
sound check that could reject the unitless case without also wrongly rejecting the metres case. If
you want your answer to come out in a particular unit, give your starting condition in that unit —
LiveSheet will carry it through unchanged.

## Errors

See [Error messages](errors.md#differential-equations) for the exact wording of every message this
feature can show you, what causes it, and how to fix it.
