# Optimization

LiveSheet can solve equations numerically and find the smallest or largest value of an expression
while limits hold. You describe the problem in a few one-line regions that share a **model name**,
then add one result line.

## How a model is written

Each line ends with `in <name>`, where `<name>` is the model's name (the Optimization tab's buttons
use `m1`). Lines with the same name belong together. The result line (`settle`, `least` or `most`)
goes below the others and shows the answer.

| Line | Meaning |
|---|---|
| `vary x from 1 in m1` | Declares an unknown `x` with starting guess 1. The guess's unit gives the unknown its unit (`vary t from 1 s in m1`). Several unknowns are separated by commas. |
| `x^2 == 4 in m1` | An equation the answer must satisfy. |
| `x <= 10 in m1`, `x >= 0 in m1` | Limits. `a <= x <= b` also works. |
| `accuracy 1e-8 in m1` | Optional. Tolerance; default 1e-8. |
| `steps 200 in m1` | Optional. Iteration limit; default 200. |
| `settle in m1` | Solves the equations and limits from your starting guess and defines the unknowns. |
| `least x^2 in m1` | Finds the smallest value of the expression while all limits hold. |
| `most x in m1` | Finds the largest value of the expression while all limits hold. |

The starting guess is part of the problem, and LiveSheet only finds a local answer near it. If a
problem has several answers, try different guesses. Limit and equation lines show a check mark
when satisfied.

## The Optimization tab

The **Optimization** tab has one button per line above, in three groups: *Unknowns and
constraints* (`vary`, `equation ==`, `limit <=`, `limit >=`), *Settings (optional)* (`accuracy`,
`steps`) and *Results* (`settle`, `least`, `most`). Click a button once per line, each in its own
region, and rename `m1` and `x` consistently on every line. A button only inserts text; any
mistake is reported when the sheet recalculates.

## Worked example

Four regions, top to bottom:

```
vary x from 1 in m1
x^2 == 4 in m1
x >= 0 in m1
settle in m1
```

The last line shows `x = 2`. To find the smallest and largest values of `x` within limits, use
`x >= 0 in m1`, `x <= 10 in m1` and finish with `most x in m1` (result 10) or `least x^2 in m1`
(result about 0).

Error messages for models are listed in [Error messages](errors.md#optimization-solve-models).
