# Statistics

LiveSheet can summarise a list of measurements (mean, spread, percentiles, how two lists move
together), evaluate four standard probability distributions (normal, uniform, binomial and
Poisson), run hypothesis tests (see [Hypothesis tests](#hypothesis-tests)) and fit a straight line
or a polynomial through paired data (see [Regression](#regression-fitting-a-line-or-curve-to-data)).
Except for the tests, everything here is an ordinary function you type into a math region, the same
way you already type `sin(x)` or `sqrt(x)`. There is nothing to insert and no dialog.

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

## Hypothesis tests

A hypothesis test answers "is the difference I see likely to be real, or could it be chance?".
LiveSheet offers three tests:

- **One-sample t-test**: does the average of one list differ from a value you have in mind?
- **Two-sample (Welch) t-test**: do the averages of two lists differ? Welch's version does not
  assume the two lists are equally spread. It is the only two-sample test offered.
- **Chi-square fit test**: do observed counts match the counts you expected?

A test is written as several separate lines that belong together through a shared name at the end,
`in <name>`, in the same way as the other tagged blocks (such as the
[differential equation](odes.md) and [truss](truss.md) lines). The lines can sit anywhere on the
sheet, but the `verdict` line that runs the test only uses lines for that name that are above it
(reading left to right, then top to bottom). Nothing is calculated until `verdict` is reached.

| Line | Meaning |
|---|---|
| `sample <list> in <name>` | The measurements. One line for a one-sample or chi-square test, exactly two for a two-sample test. |
| `expected <list> in <name>` | Expected counts, only for the chi-square test. |
| `claim <text> in <name>` | What you are testing (the forms are below). Exactly one line. |
| `level <number> in <name>` | The significance level. Optional, at most one line. |
| `verdict in <name>` | Runs the test and shows the decision. Nothing may be written between `verdict` and `in`. |

Each `<list>` is a vector (a single column or row, or a single number), for example
`[12, 14, 11, 15, 13]`, or the name of a vector you defined earlier.

### The claim

The claim states the starting assumption (the "null hypothesis") that the test tries to refute.

| You write | Test | Needs |
|---|---|---|
| `claim mean == <value>` | One-sample t, two-sided: the average equals `<value>`. | One `sample` line, no `expected`. |
| `claim mean < <value>` | One-sample t, one-sided, using the lower tail. | Same. |
| `claim mean > <value>` | One-sample t, one-sided, using the upper tail. | Same. |
| `claim mean1 == mean2` (or `<`, `>`) | Welch two-sample t. `mean1` is the first `sample` line, `mean2` the second, in reading order. | Two `sample` lines, no `expected`. |
| `claim fits` | Chi-square fit of the sample counts to the expected counts. | One `sample` line and one `expected` line. |

`mean`, `mean1`, `mean2` and `fits` are fixed words, not names of your variables. Anything else
(for example `claim mean <= 7`) is refused with a message that lists the three forms.

### Significance level and the verdict

The level is the chance of a false alarm you are willing to accept. If you leave out the `level`
line it is 0.05. It must be greater than 0 and less than 1 (for example `level 0.01 in fit`).

The test produces a p-value: roughly, how likely a difference at least this big would be if the
claim were true. The verdict is

- **reject H0** if the p-value is at or below the level (the data speaks against the claim);
- **fail to reject H0** if it is above the level (the data does not rule the claim out).

"Fail to reject" is deliberate wording: a test can never prove a claim true, only fail to find
evidence against it.

The `verdict` line shows, for example, `⇒ fail to reject H0 (p = 0.2302, alpha = 0.05)`. The
numbers are printed the same way as any other result.

### Results you can reuse

When `verdict` succeeds it defines three plain numbers (no unit) named after your test:
`<name>_statistic` (the t or chi-square value), `<name>_df` (the degrees of freedom) and
`<name>_pvalue`. Type them on a math region like any variable, for example `gauge_pvalue =`. They
exist only after a successful `verdict`; if it shows an error they are not defined.

### Worked example: one measurement list against a target

Five readings should average 7:

```
sample [8, 7, 6, 9, 10] in s1
claim mean == 7 in s1
verdict in s1                    ⇒ fail to reject H0 (p = 0.2302, alpha = 0.05)
s1_statistic =                   = 1.41421
s1_df =                          = 4
s1_pvalue =                      = 0.2302
```

The readings average 8, which is above 7, but with only five readings that is not convincing
(p = 0.2302 is well above 0.05), so you cannot rule out that the true average is 7. For a
one-sided claim, write `claim mean > 7 in s1b` instead; it asks whether the average is above 7.

With units, give the claimed value the same kind of unit as the sample:

```
sample [12, 14, 11, 15, 13] mm in gauge
claim mean == 12 mm in gauge
verdict in gauge
```

### Worked example: two lists

```
sample [1, 2, 3, 4, 5] in ab
sample [2, 3, 4, 5, 6] in ab
claim mean1 == mean2 in ab
verdict in ab                    ⇒ fail to reject H0 (p = 0.346594, alpha = 0.05)
ab_statistic =                   = -1
ab_df =                          = 8
```

The two lists must have the same kind of unit (or none), and each needs at least 2 values.

### Worked example: do the counts match what you expected?

```
sample [10, 20, 30, 40] in fit
expected [25, 25, 25, 25] in fit
claim fits in fit
verdict in fit
fit_statistic =                  = 20
fit_df =                         = 3
fit_pvalue =                     = 0.000169742
```

The p-value is about 0.00017, so at the default level of 0.05 the verdict is `reject H0`: the
counts do not fit an even split. The level changes the decision when it sits on either side of
the p-value. With `level 0.0001 in fit` the verdict is `fail to reject H0`; with
`level 0.001 in fit` it is `reject H0`.

Rules for the chi-square test:

- The `sample` counts must have no unit, at least 2 values, and not all be zero.
- The `expected` values must all be greater than zero, have no unit, and there must be as many as
  sample values. They may be proportions rather than counts: if they do not add up to the same
  total as the sample, they are scaled to it first, so `[1, 1, 1, 1]` gives the same result as
  `[25, 25, 25, 25]` here.
- The degrees of freedom are the number of values minus 1.
- This test only looks at one tail (a large mismatch); there is no `<` or `>` form.

### Good to know

- Both t-tests need at least 2 values in each sample, and a sample whose values are all equal has
  no spread, so the t value cannot be computed and you get an error.
- The words `sample`, `expected`, `claim` and `level` only count as test lines when followed by a
  space, `[` or `(`. A variable called `sample`, `level`, or `sample2` is therefore fine: for
  example `sample2 in g` is not treated as a test line.
- Each line is also checked where it stands, so a bad `claim`, `level` or `expected` line shows
  its own error right away, before `verdict`.

## Regression: fitting a line or curve to data

You have paired measurements, an `x` list and a `y` list of the same length, and you want the
straight line or low-degree curve that comes closest to them (a least-squares fit). Four functions
cover it:

| Function | Gives you |
|---|---|
| `fit_linear(x, y)` | The best straight line `y = c0 + c1*x`, as a vector of its two coefficients. |
| `fit_poly(x, y, degree)` | The best polynomial of the whole-number `degree` you choose (1 or more), as a vector of `degree + 1` coefficients. |
| `predict(c, x)` | The fitted value at `x`, given a coefficient vector `c`. |
| `r_squared(c, x, y)` | A number saying how well the fit follows your data (1 is a perfect fit). |

### The coefficient vector: constant term first

The vector that `fit_linear` and `fit_poly` return is a single column that **starts with the
constant term and goes up in powers of x**: `[c0; c1; c2; ...]` stands for
`c0 + c1*x + c2*x² + ...`. For a line that means `[intercept; slope]`. Note that this is the
opposite order from some other tools, which list the highest power first. `fit_poly(x, y, 1)`
gives exactly the same vector as `fit_linear(x, y)`.

### Worked example: a straight line

Four readings that roughly follow a line:

```
x := [0, 1, 2, 3]
y := [1, 2, 2, 4]
c := fit_linear(x, y)
c =                          = [0.9; 0.9]
predict(c, 4) =              = 4.5
r_squared(c, x, y) =         = 0.852632
```

The line is `y = 0.9 + 0.9*x`. At `x = 4` it predicts 4.5. The `r_squared` of 0.852632 says the line
accounts for about 85 percent of the variation in `y`; a perfect fit gives 1. When your data lies
exactly on a line you get exactly its coefficients: `x := [0, 1, 2, 3]` and `y := [1, 3, 5, 7]` give
`[1; 2]` and an `r_squared` of 1.

### Worked example: a curve

`fit_poly` with `degree` 2 fits a parabola. These five points lie exactly on `y = 1 + x²`:

```
x := [0, 1, 2, 3, 4]
y := [1, 2, 5, 10, 17]
c := fit_poly(x, y, 2)
c =                          = [1; 0; 1]
predict(c, 5) =              = 26
r_squared(c, x, y) =         = 1
```

The coefficients are `[1; 0; 1]`: a constant of 1, no `x` term, and `x²` with factor 1.

The degree must be a whole number, at least 1, and **less than the number of points**. With 4 points
you can ask for degree 3 (the curve then passes through every point, and `r_squared` is 1) but not
degree 4.

### Using predict

`predict(c, x)` accepts a single number or a list for `x`. A list gives back a list of the same
shape: a row stays a row, a column stays a column.

```
predict(c, [0, 1, 2]) =      = [1, 2, 5]
```

(using `c` from the curve example). You can also build the coefficient vector by hand, for example
`predict([1; 2], 3)` evaluates `1 + 2*3` and gives 7. The coefficients must be a single column or
row; `x` may not be a matrix with several rows and columns.

### r_squared

`r_squared(c, x, y)` compares the fitted values with your `y` values. It never has a unit. A fit
that includes a constant term gives a value between 0 and 1. A badly chosen coefficient vector,
for example one you typed by hand, can give a negative number; that is not an error. `x` and `y`
must be the same length. If every `y` is the same value there is nothing to explain and you get an
error (see [Error messages](errors.md)).

### Units

Units carry through the fit. For a fit of `y` against `x`, the coefficient of `x^k` has the unit of
`y` divided by the unit of `x`, to the power `k`:

```
x := [0, 1, 2, 3] s
y := [1, 3, 5, 7] m
fit_linear(x, y) =           = [1 m; 2 m/s]
predict(fit_linear(x, y), 4 s) = 9 m
```

A degree-2 fit of the same kind gives, for example, `[1 m; 0 m/s; 1 m/s²]`. When you call `predict`,
give `x` in the unit you fitted with (or one of the same kind); `predict(..., 4 m)` here fails with
`Units do not match` because a length is not a time. `r_squared` needs the predicted values and your
`y` values to be the same kind of unit, otherwise it reports `Units do not match`.

**When both lists are lengths.** If `x` is in `mm` and `y` is in `m`, the slope is a length divided
by a length, which LiveSheet treats as a plain number. Its value is 2000 for a line that rises 2 m
per mm. It shows as `2000`, not as a unit. The values are still right in base units: a prediction
for `4 mm` comes back in `m`, correct. The same applies to the higher coefficients.

### Exact answers and difficult data

When your `x` and `y` values are whole numbers or fractions, the coefficients are worked out exactly
(you see `[1; 0; 1]`, not `[0.999999; 0; 1.000001]`). With decimal values the answer is accurate to
the printed 6 digits.

Data whose `x` values sit far from zero, such as years, kilometre posts or timestamps, is handled
correctly too. For example:

```
x := [10000, 10001, 10002, 10003, 10004, 10005]
y := [1, 3.1, 4.9, 7.2, 8.8, 11.1]
fit_poly(x, y, 2) =          = [337351; -69.4493; 0.00357143]
```

The constant term is huge because it is the value at `x = 0`, far outside your data. The curve
itself is fine; `predict` and `r_squared` use the same coefficients and give the right values near
your data. If the `x` values are all identical, or too few different values exist for the degree you
asked for, LiveSheet says `Matrix does not have full column rank` instead of guessing.

### Known limitations

- **Not inside your own function.** The statistics functions, including `predict`, cannot yet be
  used in the body of a function you define. `h(u) := predict(c, u)` gives `u is not defined` on
  the definition line. Call them directly on a region instead, as in `predict(c, 10)`. This is a
  known defect that also affects `mean` and the other statistics functions.
- A fit is only as good as its model: `r_squared` close to 1 does not prove the data is truly a
  line or polynomial.

Messages you may meet are listed under "Statistics" in [Error messages](errors.md).
