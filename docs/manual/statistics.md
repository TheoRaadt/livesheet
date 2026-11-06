# Statistics

LiveSheet can summarise a list of measurements (mean, spread, percentiles, how two lists move
together) and evaluate four standard probability distributions: normal, uniform, binomial and
Poisson. Everything here is an ordinary function you type into a math region, the same way you
already type `sin(x)` or `sqrt(x)`. There is nothing to insert and no dialog.

The **Statistics** tab in the tab strip has no buttons yet. Type the functions by hand.

Results print with 6 significant digits (for example `4.57143`, not `4.571429`). The value inside
the sheet is more precise than what is shown.

## Summarising a list of measurements

A list of measurements is a vector, a single column or a single row, built as described in
[Vectors and matrices](matrices.md). A single number also counts as a list of one value.

Say you measured eight parts:

```
v := [2, 4, 4, 4, 5, 5, 7, 9]
mean(v) =                  = 5
median(v) =                = 4.5
mode(v) =                  = 4
```

| Function | Gives you |
|---|---|
| `mean(v)` | The average. |
| `median(v)` | The middle value; for an even count, the average of the two middle values. |
| `mode(v)` | The most frequent value. If several values tie, you get the smallest of them. |
| `variance(v)` | The sample variance (see below). |
| `stdev(v)` | The sample standard deviation (see below). |
| `population_variance(v)` | The population variance. |
| `population_stdev(v)` | The population standard deviation. |
| `quantile(v, p)` | The value a fraction `p` of the way through the sorted data (see below). |
| `covariance(u, w)` | How two equal-length lists vary together. |
| `correlation(u, w)` | The same, scaled to between -1 and 1. |

### Mode and ties

If two or more values appear equally often, `mode` gives the smallest one. If no value repeats,
every value is tied, so you get the smallest value in the list.

```
mode([5, 5, 2, 2, 9]) =    = 2
mode([3, 1, 2]) =          = 1
```

### Sample or population: which spread do you want?

`variance` and `stdev` treat your list as a **sample** of something larger. They divide by the
number of values minus one (n-1). Use these when your measurements are a batch drawn from a bigger
supply.

`population_variance` and `population_stdev` divide by the number of values (n). Use these only
when your list is the whole population and nothing is left out.

With the list `v` above:

```
variance(v) =              = 4.57143
stdev(v) =                 = 2.13809
population_variance(v) =   = 4
population_stdev(v) =      = 2
```

`variance` and `stdev` need at least 2 values. The two `population_` versions work with 1.

### Percentiles with `quantile`

`quantile(v, p)` takes `p` between 0 and 1. `p = 0` gives the smallest value, `p = 1` the largest,
and `p = 0.5` gives the same as `median`. In between, LiveSheet sorts the data and interpolates
in a straight line between the two nearest values; there is one method and no option to choose
another.

```
quantile(v, 0) =           = 2
quantile(v, 0.25) =        = 4
quantile(v, 0.75) =        = 5.5
quantile(v, 1) =           = 9
```

### Two lists together

`covariance(u, w)` and `correlation(u, w)` need two lists of the same length with at least 2
values each, and neither list may be constant (all values equal).

```
u := [1, 2, 3, 4, 5]
t := [2, 4, 5, 4, 5]
covariance(u, t) =         = 1.5
correlation(u, t) =        = 0.774597
```

The covariance is a sample covariance (divided by n-1). The correlation is always dimensionless.

### Units

The results keep your units: `mean`, `median`, `mode`, `stdev` and `quantile` give the same unit as
the list; `variance` gives the unit squared; `covariance` gives the product of the two lists'
units; `correlation` has no unit. To see the answer in a unit you choose, put it after the `=`:

```
w := [2, 4, 4, 4, 5, 5, 7, 9] mm
mean(w) = mm               = 5 mm
variance(w) = mm^2         = 4.57143 mm²
```

A bare `mean(w) =` shows the answer in base units (`0.005 m`), as for any millimetre value.
A list whose entries have different kinds of unit gives `Units do not match`.

## Probability distributions

Each distribution has the same four functions, and the input value or probability always comes
first, followed by the distribution's own numbers.

| Distribution | Density or mass | Cumulative | Quantile | Sample |
|---|---|---|---|---|
| Normal (mean `mu`, spread `sigma`) | `normal_pdf(x, mu, sigma)` | `normal_cdf(x, mu, sigma)` | `normal_quantile(p, mu, sigma)` | `normal_sample(mu, sigma, n, seed)` |
| Uniform (from `a` to `b`) | `uniform_pdf(x, a, b)` | `uniform_cdf(x, a, b)` | `uniform_quantile(p, a, b)` | `uniform_sample(a, b, n, seed)` |
| Binomial (`n_trials` tries, success chance `p`) | `binomial_pmf(k, n_trials, p)` | `binomial_cdf(k, n_trials, p)` | `binomial_quantile(q, n_trials, p)` | `binomial_sample(n_trials, p, n, seed)` |
| Poisson (rate `lambda_`) | `poisson_pmf(k, lambda_)` | `poisson_cdf(k, lambda_)` | `poisson_quantile(q, lambda_)` | `poisson_sample(lambda_, n, seed)` |

The density or mass function gives how likely a value is; the cumulative function gives the
chance of being at or below it; the quantile function runs the cumulative one backwards (the value
below which a given chance lies).

### Normal

```
normal_pdf(0, 0, 1) =          = 0.398942
normal_cdf(1, 0, 1) =          = 0.841345
normal_quantile(0.975, 0, 1) = = 1.95996
```

The first line says the standard bell curve is 0.398942 high at its centre. The second says about
84.1 percent of a standard normal population lies below 1. The third gives the familiar 1.96.
For a population with mean 10 and spread 2, `normal_cdf(12, 10, 2) =` gives the same 0.841345.
`sigma` must be positive. `normal_quantile` needs `p` strictly between 0 and 1.

### Uniform

```
uniform_pdf(5, 0, 10) =        = 0.1
uniform_cdf(5, 0, 10) =        = 0.5
uniform_quantile(0.25, 0, 10) = = 2.5
uniform_pdf(-1, 0, 10) =       = 0
```

`a` must be less than `b`. A value outside the range from `a` to `b` simply has density 0; that is
not an error.

### Binomial and Poisson

For these two, `k` is a count, so it must be a whole number of zero or more. A negative or
fractional `k` is an error, not rounded.

```
binomial_pmf(2, 5, 0.5) =      = 0.3125
binomial_cdf(2, 5, 0.5) =      = 0.5
binomial_quantile(0.5, 5, 0.5) = = 2
binomial_pmf(7, 5, 0.5) =      = 0
```

Five fair coin tosses give exactly two heads with chance 0.3125. Asking for more heads than there
are tosses gives 0, not an error.

`binomial_quantile` and `poisson_quantile` give the smallest whole number `k` whose cumulative
chance reaches at least the level you ask for.

```
poisson_pmf(2, 3) =            = 0.224042
poisson_cdf(2, 3) =            = 0.42319
poisson_quantile(0.42319, 3) = = 2
```

`poisson_quantile` accepts `q` from 0 up to, but not including, 1, because the value that reaches
a chance of exactly 1 would be infinite. `binomial_quantile` accepts 0 to 1.

### Units are not accepted here

The distribution functions work with plain numbers only. Passing a value with a unit anywhere in
them (`normal_pdf(5 m, 0, 1)`) gives an error. If your data has a unit, turn it into a plain
number first by dividing by the unit with parentheses, `(x) / (1 m)`. This also applies to
`quantile`'s `p`.

## Random samples

`normal_sample`, `uniform_sample`, `binomial_sample` and `poisson_sample` give you a column vector
of `n` random draws, so you can feed it straight into `mean`, `stdev` and the rest.

```
x := normal_sample(0, 1, 2000, 1)
len(x) =                       = 2000
mean(x) =                      (close to 0)
stdev(x) =                     (close to 1)
```

- `n` is the number of draws, a whole number from 1 to 10000.
- `seed` is required, a whole number of zero or more. The same call with the same seed always
  gives the same draws, so your sheet gives the same answers every time you open it. A different
  seed gives a different set of draws.
- The draws come from the random-number generator in NumPy. For a given seed the exact values can
  change if NumPy moves to a new major version, so don't rely on a particular draw (such as
  "the third value is 0.35") surviving a software upgrade. Averages and spreads stay statistically
  the same.
- `binomial_sample` and `poisson_sample` give whole numbers.

## Things to watch for

- **Zero with a unit loses the unit.** `0 m` is treated as a plain 0, so a distribution function
  accepts it instead of rejecting it as having a unit. The number it returns is still correct.
- **Typing a ratio of two quantities.** `x := 2 m / 1 m` gives `2 m²`, not 2, because the second
  `1 m` is read as multiplied rather than divided. Use parentheses: `x := (2 m) / (1 m)`.
  Otherwise the distribution functions will correctly refuse the unit-bearing result.
- **Don't name a variable `e`.** `e` is Euler's number (2.71828). A list named `e` is accepted
  without complaint, but later `mean(e)` quietly returns 2.71828.
- **Your own name wins.** If you define your own variable or function called `mean`, `mode` and so
  on, yours is used in place of the built-in one for the rest of the sheet.

Hypothesis tests (including Welch's two-sample t-test) and curve fitting are not part of LiveSheet
yet.

Messages you may meet are listed under "Statistics" in [Error messages](errors.md).
