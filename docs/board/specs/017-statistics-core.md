# 017 Statistics: descriptive statistics, distributions, hypothesis tests, regression

Source inspiration (concept only, nothing copied):
- Backlog item 29 (M5 Statistics, Theo's request 2026-10-29) and the generic
  "engineering extras" idea in `.claude/skills/mathcad-concepts` (standard-data
  tables, annotated results) — no vendor statistics package, help page, tutorial or
  example worksheet was read for this spec.
- Generic, standard statistics/probability terminology and formulas, the common
  ground of any introductory statistics textbook and course, independently
  confirmed against public encyclopedic sources (concept and formula only, nothing
  quoted beyond a function's own name): Wikipedia "Descriptive statistics",
  "Variance", "Standard deviation", "Quantile", "Pearson correlation coefficient",
  "Covariance", "Mode (statistics)", "Normal distribution", "Continuous uniform
  distribution", "Binomial distribution", "Poisson distribution", "Student's
  t-test", "Welch's t-test", "Chi-squared test", "Simple linear regression",
  "Polynomial regression", "Coefficient of determination" (all accessed
  2026-11-01). These are centuries-to-decades-old public mathematics, taught
  identically (to within notation) in every source consulted; nothing below is
  specific to any one software product.
- SciPy's own public documentation (BSD-3-Clause; SciPy is an already-approved
  dependency), `scipy.stats` module overview, https://docs.scipy.org/doc/scipy/reference/stats.html,
  accessed 2026-11-01, confirmed only that `scipy.stats` already implements the
  named distributions, descriptive and test functions below as part of its own
  public API — used here only to decide this is a reasonable implementation
  backend to flag as an open question, not to copy any name or example from it.
  LiveSheet's own function/keyword names below were chosen independently (see IP
  check) and do not reuse `scipy.stats`'s own names 1:1 where they differ from
  plain English statistics terms (e.g. SciPy's `rv_continuous.ppf` is this spec's
  own `..._quantile`).
- Everything below (keyword names, syntax, phasing, binding/output convention,
  error texts, numeric examples) is LiveSheet's own design.

Size: too big for one slice (three genuinely different kinds of work: pure
functions on existing vectors, new probability-distribution functions, and a new
tagged-region construct for hypothesis tests). Phased the same way specs 002/010
were, in one file with a hard phase boundary between each part; phase 2 and 3 can
ship independently of each other once phase 1 is merged.
- **S1 Descriptive statistics and distributions** (about 2.5 days): vector
  statistics functions, four probability distributions (normal, uniform, binomial,
  Poisson), each with a PDF/PMF, CDF, quantile and sampling function. Pure
  functions only, no grammar change.
- **S2 Hypothesis tests** (about 2 days, starts after S1 is merged — reuses S1's
  vector statistics internally): one-sample and two-sample t-tests, chi-square
  goodness-of-fit test, as a new tagged-region construct reusing spec 003/010/015's
  `_parse_model`/`in <name>` idiom.
- **S3 Regression** (about 1.5 days, independent of S2, starts after S1 is
  merged): linear and polynomial regression, extending spec 002b's
  `solve_least_squares`. Pure functions only, no grammar change.

Interop with spec 002 (vectors/matrices): a "sample" or "data vector" in this spec
is always just an existing Nx1 or 1xN matrix value (spec 002a) — there is no new
value type. All three phases reuse spec 002's existing vector helpers (`len`,
indexing, unit rules) and spec 002b's `solve_least_squares`; nothing here changes
spec 002's own behaviour.

---

# S1 Descriptive statistics and distributions

User story:
As an engineer I have measured a batch of 20 part dimensions as a vector and want
its mean, spread and a chosen percentile without leaving the sheet; separately, I
want to evaluate a standard probability distribution (e.g. "what fraction of a
normal population falls below this value") the same way I already evaluate `sin`
or `sqrt` today.

Behaviour (own words):
- Descriptive statistics operate on a vector (any Nx1 or 1xN matrix, spec 002's
  existing vector shape; a 1x1 "vector" of a single value is accepted, scalar
  results are the obvious degenerate case). A non-vector (scalar other than 1x1, or
  a matrix with more than one row and more than one column) is an error.
  - `mean(v)`, `median(v)`: the arithmetic mean and the middle value (average of
    the two middle values for even length), keeping `v`'s unit.
  - `mode(v)`: the most frequent value; if several values tie for most frequent
    (including the case where no value repeats, so every value is tied), the
    smallest of the tied values is returned — deterministic, not "first seen" or
    "arbitrary", own choice (flagged as open question 1).
  - `variance(v)`, `stdev(v)`: the *sample* variance/standard deviation (divides
    the sum of squared deviations from the mean by `len(v) - 1`, the usual
    "Bessel's correction" convention for treating `v` as a sample of a larger
    population — flagged as open question 2 together with `population_variance`/
    `population_stdev` below). `variance` squares `v`'s unit (e.g. `m` in, `m²`
    out); `stdev` keeps `v`'s unit. `len(v) < 2` is an error (sample variance is
    undefined for a single point).
  - `population_variance(v)`, `population_stdev(v)`: the same formulas dividing by
    `len(v)` instead of `len(v) - 1` (the "whole population known exactly" case);
    accept `len(v) >= 1`.
  - `quantile(v, p)`: the `p`-th quantile of `v` for `0 <= p <= 1` (`p` dimensionless,
    `p = 0` is the minimum, `p = 1` the maximum, `p = 0.5` equals `median(v)`), by
    linear interpolation between the two nearest order statistics at rank
    `p * (len(v) - 1)` (the common "linear" interpolation convention also used as
    the default by several public statistics packages, not vendor-specific — see
    open question 3 on method choice). Keeps `v`'s unit. `p` outside `[0, 1]` is an
    error.
  - `covariance(u, v)`, `correlation(u, v)`: `u` and `v` must be vectors of equal
    length with `len >= 2`. `covariance` is the sample covariance (deviations'
    products summed, divided by `len - 1`), carrying the product of `u`'s and `v`'s
    units. `correlation` is the Pearson correlation coefficient (covariance
    divided by the product of the two sample standard deviations), dimensionless,
    always in `[-1, 1]`. Either vector having zero variance (all entries equal) is
    an error (correlation/covariance with a constant is undefined by this
    formula).
- Probability distributions: four distributions, each with the same four-function
  shape, dimensionless inputs and outputs only in this phase (a quantity carrying
  a unit anywhere in these functions is an error — see open question 4 on whether
  a later phase should let e.g. `normal_pdf` take `mu`/`sigma` with a shared unit).
  Distribution parameters use the standard textbook parameterisation named below;
  argument order is always "the input value/probability first, then the
  distribution's own parameters", for every function of every distribution, so the
  four functions of one distribution read as a family:
  - Normal (mean `mu`, standard deviation `sigma > 0`): `normal_pdf(x, mu, sigma)`,
    `normal_cdf(x, mu, sigma)`, `normal_quantile(p, mu, sigma)` for
    `0 < p < 1`, `normal_sample(mu, sigma, n, seed)` (see sampling below).
  - Continuous uniform (bounds `a < b`): `uniform_pdf(x, a, b)`,
    `uniform_cdf(x, a, b)`, `uniform_quantile(p, a, b)`,
    `uniform_sample(a, b, n, seed)`.
  - Binomial (trials `n_trials` a non-negative integer, success probability
    `0 <= p <= 1`): `binomial_pmf(k, n_trials, p)`, `binomial_cdf(k, n_trials, p)`,
    `binomial_quantile(q, n_trials, p)` (smallest integer `k` with
    `binomial_cdf(k, n_trials, p) >= q`, the standard discrete-quantile
    convention), `binomial_sample(n_trials, p, n, seed)`. `k` must be a
    non-negative integer `<= n_trials` for `pmf`/`cdf` (non-integer or
    out-of-range `k` is an error, not silently rounded or zero).
  - Poisson (rate `lambda_ > 0`): `poisson_pmf(k, lambda_)`, `poisson_cdf(k, lambda_)`,
    `poisson_quantile(q, lambda_)` (same convention as `binomial_quantile`),
    `poisson_sample(lambda_, n, seed)`. `k` a non-negative integer, else an error.
  - `..._pmf`/`..._pdf` outside the distribution's support (e.g. `k < 0` for
    Poisson once past the integer check, or a `binomial_pmf` with `k` above
    `n_trials`) returns `0`, not an error — the usual convention ("the
    probability of an impossible outcome is zero"), except for the input-shape
    errors named above (non-integer `k`, wrong type, out-of-domain parameter such
    as `sigma <= 0`), which do error.
  - Sampling: `..._sample(..., n, seed)` returns an `n`x1 vector of `n`
    independently drawn values from the distribution (`n` a positive integer,
    `n > 10000` is an error, same ceiling spirit as spec 002's own matrix-size
    cap). `seed` is a required non-negative integer: the same `seed` with the same
    other arguments always reproduces the exact same vector (deterministic,
    matching every other computation on this project — re-evaluating an unchanged
    sheet always gives the same result); a different `seed` gives a different
    (but still reproducible) draw. Making `seed` *optional* with a non-deterministic
    default is explicitly not proposed here (flagged as open question 5, since it
    is a real trade-off between textbook "just sample me something" convenience
    and this project's existing determinism guarantee).

Syntax proposal (own keywords): functions only, no grammar change. Added to the
evaluator builtins exactly like spec 002/002b's own functions; a user-defined name
that collides with one of these wins, same shadowing rule as every existing
built-in.

Acceptance criteria (tolerance: relative 1e-6 unless stated; `v =` etc. as in
prior specs):
Descriptive statistics
1. `v := [2, 4, 4, 4, 5, 5, 7, 9]`: `mean(v) =` gives `= 5`; `median(v) =` gives
   `= 4.5`; `mode(v) =` gives `= 4`.
2. Same `v`: `variance(v) =` gives `= 4.57143` (32/7); `stdev(v) =` gives
   `= 2.1381`; `population_variance(v) =` gives `= 4` (32/8);
   `population_stdev(v) =` gives `= 2`.
3. Same `v`: `quantile(v, 0) =` gives `= 2`; `quantile(v, 1) =` gives `= 9`;
   `quantile(v, 0.5) =` equals `median(v)`; `quantile(v, 0.25) =` gives `= 4`;
   `quantile(v, 0.75) =` gives `= 5.5`.
4. Units: `w := [2, 4, 4, 4, 5, 5, 7, 9] mm`: `mean(w) =` gives `= 5 mm`;
   `variance(w) =` gives `= 4.57143 mm²`; `quantile(w, 0.75) =` gives `= 5.5 mm`.
5. `u := [1, 2, 3, 4, 5]`, `t := [2, 4, 5, 4, 5]`: `covariance(u, t) =` gives
   `= 1.5`; `correlation(u, t) =` gives `= 0.774597`.
6. Units on covariance: `u2 := [1, 2, 3, 4, 5] m`, `t2 := [2, 4, 5, 4, 5] N`:
   `covariance(u2, t2) =` gives `= 1.5 N·m` (= 1.5 J, SI-coherent as usual);
   `correlation(u2, t2) =` gives `= 0.774597` (dimensionless regardless of input
   units).
7. Mode tie-break: `mode([3, 1, 2]) =` gives `= 1` (no repeats, every value tied,
   smallest wins); `mode([5, 5, 2, 2, 9]) =` gives `= 2` (two-way tie at frequency
   2, smallest of the tied values).
Errors
8. `mean(5) =` is accepted (`= 5`, a 1x1 "vector"); `mean([1, 2; 3, 4]) =` is an
   error `mean() needs a vector`; same error family for every function above.
9. `variance([5]) =` is an error `variance() needs at least 2 values`.
10. `quantile(v, 1.5) =` is an error `p must be between 0 and 1`.
11. `correlation([1, 2, 3], [1, 1, 1]) =` is an error
    `correlation() is undefined when a vector is constant`.
12. `correlation([1, 2], [1, 2, 3]) =` is an error
    `Vectors must have the same length (2 and 3)`.
Distributions
13. `normal_pdf(0, 0, 1) =` gives `= 0.398942`; `normal_cdf(0, 0, 1) =` gives
    `= 0.5`; `normal_cdf(1, 0, 1) =` gives `= 0.841345`;
    `normal_quantile(0.975, 0, 1) =` gives `= 1.95996`.
14. `uniform_pdf(5, 0, 10) =` gives `= 0.1`; `uniform_cdf(5, 0, 10) =` gives
    `= 0.5`; `uniform_quantile(0.25, 0, 10) =` gives `= 2.5`;
    `uniform_pdf(-1, 0, 10) =` gives `= 0` (outside support, not an error).
15. `binomial_pmf(2, 5, 0.5) =` gives `= 0.3125`; `binomial_cdf(2, 5, 0.5) =`
    gives `= 0.5`; `binomial_quantile(0.5, 5, 0.5) =` gives `= 2`;
    `binomial_pmf(7, 5, 0.5) =` gives `= 0` (k above n_trials, not an error).
16. `poisson_pmf(2, 3) =` gives `= 0.224042`; `poisson_cdf(2, 3) =` gives
    `= 0.42319`; `poisson_quantile(0.42319, 3) =` gives `= 2`.
17. `normal_pdf(0, 0, -1) =` is an error `sigma must be positive`;
    `binomial_pmf(1.5, 5, 0.5) =` is an error `k must be a non-negative integer`;
    `binomial_pmf(2, 5, 1.5) =` is an error `p must be between 0 and 1`;
    `normal_pdf(5 m, 0, 1) =` is an error
    `normal_pdf() does not accept a unit in this version`.
18. Sampling, determinism (exact values are not hand-derived here — see the note
    below; the tester must independently verify the generator's statistical
    correctness, e.g. against NumPy/SciPy, both already-approved dependencies):
    `normal_sample(0, 1, 5, 1) =` and a second, separately-typed
    `normal_sample(0, 1, 5, 1) =` give identical 5x1 vectors (same seed, same
    result); `normal_sample(0, 1, 5, 2) =` differs from the `seed=1` result in at
    least one entry; `len(normal_sample(0, 1, 2000, 1)) =` gives `= 2000` and
    `mean(normal_sample(0, 1, 2000, 1)) =` is within 0.1 of `0`, and
    `stdev(normal_sample(0, 1, 2000, 1)) =` is within 0.1 of `1` (law-of-large-
    numbers sanity check, not an exact value); `normal_sample(0, 1, 10001, 1) =`
    is an error `n is too large (max 10000)`.
19. `binomial_sample(10, 0.5, 2000, 1) =`: `mean(...)` is within 0.2 of `5`
    (`n_trials * p`); every entry is an integer between `0` and `10` inclusive
    (checked over all 2000 draws).

Edge cases:
- `mean`/`median`/`mode`/`quantile` of a 1-element vector all equal that element.
- `quantile(v, 0)`/`quantile(v, 1)` always equal `min`/`max` regardless of
  interpolation method, so they are not affected by open question 3.
- A vector with symbolic (undefined-symbol) entries: these functions require fully
  numeric input (no symbolic mode); a symbolic entry gives the existing matrix
  "not defined" error family from spec 002, not a new error text.
- Mixed-unit vectors (spec 002's "mixed matrix" case) are rejected the same way
  `det`/`norm` already reject a non-homogeneous matrix: `Units do not match`.
- `normal_quantile(0, ...)`/`normal_quantile(1, ...)` (the open ends of the
  support) are errors `p must be strictly between 0 and 1` (unlike `quantile`
  above, which is a finite-sample function where 0/1 are meaningful ranks).

IP check: pass. All names are plain-English statistics terms already in public
use before any commercial math-software product existed (`mean`, `median`,
`mode`, `variance`, `stdev`, `quantile`, `covariance`, `correlation`) or this
project's own compound names for distribution functions
(`normal_pdf`/`_cdf`/`_quantile`/`_sample`, etc. — chosen as a mechanical,
predictable family, not copied from any one package's own naming, which differs
widely even across public tools: e.g. "ppf" vs. "quantile", "rvs" vs. "sample").
No vendor text, example or help page was read; the worked numeric examples above
are independently hand-computed from the stated formulas (shown inline in the
Behaviour section's own derivations where non-trivial), not sourced from any
vendor's example library. The chosen formula variants (sample vs. population
variance, linear-interpolation quantile, "smallest of tied values" mode) are
generic textbook alternatives, not a specific vendor's default — flagged as open
questions below precisely because they are real judgement calls with more than
one defensible public convention. No GUI/canvas interaction is involved (plain
functions only), so ip-cleanroom rule 6 does not apply to this phase.

Fits current architecture?
- `livesheet/engine/matrices.py` (or a new small `engine/statistics.py` importing
  vector helpers from it — developer's call, flagged as open question 6): new
  functions reusing the existing `_need_vector`/`_numeric_array`/unit-splitting
  helpers already built for spec 002/002b; added to `MATRIX_BUILTINS` or a new
  `STATS_BUILTINS` dict merged into `evaluator.py`'s `_builtins()` the same way.
- `engine/units.py`: no change; `measure`/`UnitError` used the same way spec
  002/002b already use them (squaring a unit for `variance`, multiplying two units
  for `covariance`, rejecting a unit on distribution arguments).
- `engine/formatting.py`: no change; all results here are plain scalars or
  ordinary vectors, printed by the existing scalar/`format_matrix` paths.
- Dependency: numeric implementation can use NumPy/SciPy (`numpy.random`,
  `scipy.stats`), both already-approved (BSD-3-Clause) dependencies — flagged
  explicitly as open question 7 for the manager/Theo rather than assumed, per this
  spec's instructions, even though no *new* dependency would be added.
- `gui/`, `document.py`: no change (new functions only).

---

# S2 Hypothesis tests (starts after S1 is merged)

User story:
As an engineer I have one or two samples of measurements (or a batch of observed
counts against an expected distribution) and want to ask "is the difference I see
likely to be real, or could it plausibly be chance?" at a stated significance
level, and get a plain accept/reject answer alongside the full numbers, without
hand-computing a test statistic.

Behaviour (own words):

### Why this reuses spec 003/010/015's tag idiom
A hypothesis test needs several pieces that belong together before anything can
be computed: one or two samples (or a sample plus an expectation), a precise
statement of what is being tested, a significance level, and a trigger that runs
the test and reports a decision. This is exactly the shape spec 003 ("solve
blocks") introduced and specs 010/015 already reused for their own, unrelated
domains: independent single-statement regions anywhere on the canvas, joined only
by a shared `in <name>` tag, collected in reading order, with a dedicated result
line. This spec extends the same `_parse_model`/`Engine._run_model` mechanism with
new leading keywords, for the same "one proven mechanism, not a fourth parallel
one" reason specs 010/015 already gave.

### The tagged lines
1. `sample <expr> in <name>` — `<expr>` evaluates to a numeric vector (spec 002's
   existing shape, S1's `_need_vector` rule). One line is a one-sample test or a
   chi-square goodness-of-fit test (depending on `claim`, below); exactly two
   lines (any order; first one encountered in reading order is "sample 1", the
   second "sample 2") make a two-sample test. Three or more `sample` lines for one
   model is an error.
2. `expected <expr> in <name>` — `<expr>` evaluates to a dimensionless,
   non-negative numeric vector, same length as the (single) `sample` line's
   vector; only meaningful together with `claim fits` (below). At most one line.
3. `claim <text> in <name>` — exactly one line, naming both the null hypothesis
   and (implicitly) which test applies:
   - `claim mean == <value>` / `claim mean < <value>` / `claim mean > <value>` —
     one-sample Student's t-test: null hypothesis "the population mean equal to
     `<value>`" against the two-sided (`==`) or one-sided (`<`/`>`) alternative
     given by the comparison operator; requires exactly one `sample` line (and no
     `expected` line).
   - `claim mean1 == mean2` / `claim mean1 < mean2` / `claim mean1 > mean2` —
     two-sample Welch's t-test (the standard "unequal variances assumed" variant,
     the more generally applicable of the two classic two-sample t-tests, used
     unconditionally here rather than offering an "equal variances" mode — a
     deliberate scope cut, see open question 1 below); `mean1`/`mean2` refer to
     sample 1 and sample 2's own population means, in reading order — fixed words,
     not a user-chosen name, the same synthesized-name spirit spec 015 already
     used for its own fixed result names; requires exactly two `sample` lines.
   - `claim fits` — chi-square goodness-of-fit test between the single `sample`
     line's counts and the `expected` line's counts/proportions (if `expected`'s
     vector does not sum to the same total as `sample`'s, it is rescaled
     proportionally first — the standard goodness-of-fit convention when
     `expected` is given as proportions rather than raw counts); requires exactly
     one `sample` line and exactly one `expected` line.
   - Any other text after `claim` is a parse error naming the three accepted
     forms.
4. `level <number> in <name>` — the significance level `alpha`, `0 < alpha < 1`;
   at most one line per model; default `0.05` (the universal textbook default)
   when omitted.
5. `verdict in <name>` — the result line (parallel to spec 003's `settle` / spec
   010's `evolve` / spec 015's `resolve`). Takes no expression (trailing text is
   an error, same wording family as the other three). Runs the test selected by
   `claim`, using only tagged regions of this model earlier in reading order (same
   rule as specs 003/010/015).

### What `verdict in <name>` computes and binds
- One-sample t-test: `t = (mean(sample) - value) / (stdev(sample) / sqrt(n))`,
  `df = n - 1` (`n = len(sample)`); `value`'s unit must match `sample`'s (unit
  mismatch is the usual `Units do not match` error); `t` and the p-value are
  dimensionless regardless.
- Two-sample Welch's t-test: `t = (mean1 - mean2) / sqrt(var1/n1 + var2/n2)`
  (`var1`/`var2` the two samples' own sample variances, S1's `variance`), with the
  Welch–Satterthwaite degrees of freedom
  `df = (var1/n1 + var2/n2)^2 / ((var1/n1)^2/(n1-1) + (var2/n2)^2/(n2-1))`
  (textbook-standard, not integer in general). The two samples' units must match
  each other (not checked against anything else).
- Chi-square goodness-of-fit: `chi2 = sum((observed_i - expected_i)^2 / expected_i)`
  over the (possibly rescaled) `expected` vector, `df = len(sample) - 1`. Both
  vectors must be dimensionless (checked).
- p-value: the usual two-sided or one-sided tail probability of the relevant
  reference distribution (Student's t with the stated `df` for both t-tests,
  matching the `==`/`</`>` alternative from `claim`; chi-square with the stated
  `df`, always one-sided/upper-tail for the goodness-of-fit test — there is no
  "direction" to a chi-square goodness-of-fit alternative).
- Decision: "reject" if `p-value <= alpha`, else "fail to reject" (textbook
  convention; "fail to reject" rather than "accept", since a hypothesis test never
  proves the null hypothesis true — standard statistical phrasing, not a vendor
  choice).
- Binding (same synthesized-name convention spec 015 introduced for its own
  truss results, reused verbatim here for the same reason — there is no single
  user-chosen name per output value): `<name>_statistic`, `<name>_df`,
  `<name>_pvalue` (all plain dimensionless scalars).
- Output text of the `verdict` region itself (exact prefix is the contract, rest
  via the existing number-formatting path):
  `"⇒ reject H0 (p = <value>, alpha = <value>)"` or
  `"⇒ fail to reject H0 (p = <value>, alpha = <value>)"`.

### Scope and ordering
Identical to specs 003/010/015: tagged regions are local to the model while
`verdict` runs; nothing is bound until `verdict` succeeds; a tagged region below
`verdict` is not used; a model with tagged regions but no `verdict` region below
them is the same error family as the other three specs
(`No result region for hypothesis test "<name>" below this region`).

Syntax proposal (own keywords) and grammar change:
```
sample [12, 14, 11, 15, 13] mm in gauge
claim mean == 12 mm in gauge
verdict in gauge                 -> ⇒ reject H0 (p = 0.0180, alpha = 0.05)

sample [1, 2, 3, 4, 5] in ab
sample [2, 3, 4, 5, 6] in ab
claim mean1 == mean2 in ab
verdict in ab                    -> ⇒ fail to reject H0 (p = 0.3466, alpha = 0.05)

sample [10, 20, 30, 40] in fit
expected [25, 25, 25, 25] in fit
claim fits in fit
level 0.01 in fit
verdict in fit                   -> ⇒ reject H0 (p = 0.00017, alpha = 0.01)
```
Grammar change (`engine/syntax.py`): extend the existing `_parse_model` dispatcher
(already trying `vary`/`settle`/`least`/`most`/`accuracy`/`steps`/`ode`/`start`/
`over`/`evolve`/`nodes`/`elements`/`area`/`modulus`/`support`/`load`/`resolve`, specs
003/010/015) with five more leading keywords: `sample`, `expected`, `claim`,
`level`, `verdict`. `Statement` needs no new field beyond what already exists
(`expr` holds the deferred-parse vector/claim text exactly like `model_ode`'s
equation text and spec 015's `model_truss_nodes`' expression text); `claim`'s text
is parsed into a (kind, comparison, value-text) tuple only when `verdict` runs,
same deferred-parse pattern as every prior model keyword. No other existing
statement form changes meaning; a sheet with none of these five keywords is
unaffected, same backward-compatibility guarantee every prior model-based spec
already gives.

Acceptance criteria (tolerance: absolute 1e-3 on t/chi2/df, relative 1e-2 on
p-values unless stated; "output" is `RegionResult.output` of the `verdict`
region). The t/chi2/df values below are hand-derived from the formulas above
(shown inline); per this project's established practice (spec 015's own note),
the tester must independently verify the p-values (e.g. against SciPy's `t`/`chi2`
distributions, already an approved dependency) before the developer relies on
them.
1. One-sample t-test. `sample [8, 7, 6, 9, 10] in s1`, `claim mean == 7 in s1`,
   `verdict in s1` → `s1_statistic =` gives `= 1.41421` (`= sqrt(2)`, exact:
   mean 8, sample stdev `sqrt(2.5) = 1.58114`, SE `= stdev/sqrt(5) = 0.707107`,
   `t = 1/0.707107`); `s1_df =` gives `= 4`; `s1_pvalue =` is between `0.2` and
   `0.23` (two-sided t, df=4; tester to pin down the exact figure); with
   `level 0.05 in s1` added above `verdict`, output starts `⇒ fail to reject H0`
   (p well above 0.05).
2. One-sided variant. Same sample, `claim mean > 7 in s1b` → `s1b_statistic =`
   gives the same `= 1.41421`; `s1b_pvalue =` is exactly half of criterion 1's
   two-sided p-value (standard one-sided-from-two-sided halving for a symmetric
   reference distribution when the sample mean is on the claimed side).
3. Units. `sample [12, 14, 11, 15, 13] mm in gauge`, `claim mean == 12 mm in gauge`,
   `verdict in gauge` → mean is `13 mm`, sample variance `2.5 mm²`, stdev
   `1.58114 mm`, SE `0.707107 mm`, `t = (13-12)/0.707107 = 1.41421`; same
   `gauge_statistic =` value as criterion 1 (coincidentally, by construction);
   `claim mean == 12 in gauge2` (same sample, no unit on the claimed value) is an
   error `Units do not match`.
4. Two-sample Welch's t-test. `sample [1, 2, 3, 4, 5] in ab`,
   `sample [2, 3, 4, 5, 6] in ab`, `claim mean1 == mean2 in ab`, `verdict in ab` →
   `ab_statistic =` gives `= -1` (means 3 and 4, both sample variances `2.5`,
   `SE = sqrt(2.5/5 + 2.5/5) = 1`); `ab_df =` gives `= 8` (exact, shown in
   Behaviour); `ab_pvalue =` is well above `0.05`; output starts
   `⇒ fail to reject H0`.
5. Chi-square goodness-of-fit. `sample [10, 20, 30, 40] in fit`,
   `expected [25, 25, 25, 25] in fit`, `claim fits in fit`, `verdict in fit` →
   `fit_statistic =` gives `= 20` (exact, shown in Behaviour); `fit_df =` gives
   `= 3`; `fit_pvalue =` is below `0.001`; output starts `⇒ reject H0`.
6. `expected` rescaling. Same `sample`, `expected [1, 1, 1, 1] in fit2` (unscaled
   proportions, sum 4, not 100) → identical `fit2_statistic =`/`fit2_df =` as
   criterion 5 (rescaled internally to sum 100 first).
7. `level`. Criterion 5's model repeated with `level 0.0001 in fit3` above
   `verdict` → output still starts `⇒ reject H0` (p well below 0.0001 too; use a
   less extreme check: `level 0.0000001 in fit4` on the same data) gives
   `⇒ fail to reject H0` (p, while tiny, is not *that* tiny — tester to confirm the
   exact crossover; the point of this criterion is that `level` actually changes
   the decision, not a specific numeric boundary).
Errors
8. `claim mean == 7 in bad1` with zero `sample` lines → error
   `No sample declared for hypothesis test "bad1"`.
9. `claim mean == 7 in bad2` with three `sample` lines → error
   `hypothesis test "bad2" has 3 sample lines, expected 1 or 2`.
10. `claim mean1 == mean2 in bad3` with only one `sample` line → error
    `claim "mean1 == mean2" needs two sample lines, found 1`.
11. `claim fits in bad4` with no `expected` line → error
    `claim "fits" needs an expected line`.
12. `claim nonsense in bad5` → error
    `Use "claim mean == <value>" ("<" or ">" for one-sided), "claim mean1 == mean2", or "claim fits"`.
13. `expected [1, 1, 1] in bad6` with a `sample` of length 4 → error
    `expected has 3 values but sample has 4`.
14. `level 1.5 in bad7` → error `level must be between 0 and 1`.
15. A model with `sample`/`claim`/etc. but no `verdict` region later in reading
    order → error
    `No result region for hypothesis test "<name>" below this region` (same
    wording family as specs 003/010/015's own "No result region for ..." errors).
16. `verdict extra in bad8` (trailing text) → error `verdict takes no expression`.

Isolation, compatibility, parsing
17. A sheet without any `sample`/`expected`/`claim`/`level`/`verdict` region
    evaluates identically to before this spec (existing engine test suites
    unchanged and green). A solve-block model (003), an ODE system (010), a truss
    model (015) and a hypothesis test with different tag names on the same sheet
    do not interact. A variable or function named `sample`, `level`, etc. (no
    trailing ` in <name>`) is unaffected, same guarantee every prior model-based
    spec already gives.
18. Parsing: `parse_statement("sample [1, 2, 3] in g")` gives kind `model_sample`,
    `model="g"`, `expr="[1, 2, 3]"`; `parse_statement("claim mean == 7 in g")`
    gives kind `model_claim`, `model="g"`, `expr="mean == 7"`;
    `parse_statement("level 0.01 in g")` gives kind `model_setting`,
    `model="g"` (reusing spec 003's existing setting-kind shape, own field names
    for `level` vs. `accuracy`/`steps` left to the developer); `parse_statement("verdict in g")`
    gives kind `model_result`, `model="g"`, `goal="hypothesis_test"`.

Edge cases:
- A one-sample test's claimed value exactly equal to the sample mean gives `t = 0`
  and the maximum possible p-value (`1` for the two-sided case) — "no evidence
  against the null hypothesis at all", not a special error.
- Extremely small samples (`len(sample) == 1` for a one-sample test, or either
  sample having fewer than 2 points for a two-sample test): the underlying `df`
  formula is undefined (division by `n - 1 = 0`); reported as its own error,
  `"<name>" needs at least 2 values per sample`, not a crash or a silent NaN.
- A chi-square goodness-of-fit `expected` entry of exactly `0` while the matching
  `sample` entry is non-zero: division by zero in the formula; reported as
  `expected values must be positive` at the `expected` line's own validation,
  before `verdict` runs, not as a NaN result.
- Save format: unchanged; regions remain plain text in `.lsheet` (same as every
  prior model-based spec).

IP check: pass, with the flags below.
1. The underlying methods (Student's t-test, Welch's t-test with the
   Welch–Satterthwaite degrees-of-freedom approximation, Pearson's chi-square
   goodness-of-fit test) are generic, decades-old, universally-taught statistical
   methods, independently identical across every public source consulted — not
   distinctive to, or patented by, any one software product ("Allowed: mathematical
   methods, algorithms and concepts").
2. Keyword set is LiveSheet's own: `sample`, `expected`, `claim`, `level`,
   `verdict`. None of these is the policy-forbidden `Given`/`Find`/`Minerr`/
   `Minimize`/`Maximize`/`Odesolve`, and none collides with this project's own
   existing leading keywords (`vary`/`settle`/`least`/`most`/`ode`/`start`/
   `over`/`evolve`/`nodes`/`elements`/`area`/`modulus`/`support`/`fix`/`load`/
   `resolve`); `verdict` was deliberately chosen over the more obvious `test` or
   `check` only because those read ambiguously next to this project's own future
   features (e.g. a generic "sanity check"/"validation" feature, backlog item 9),
   not for any IP reason.
3. The `<name>_statistic`/`<name>_df`/`<name>_pvalue` synthesized-binding
   convention is spec 015's own already-reviewed design pattern, reused verbatim
   for the same reason (no single user-chosen name per output value) — not a new
   judgement call this time.
4. No GUI/canvas interaction technique is involved (plain-text tagged regions
   only, same category as specs 001-003/010/015); ip-cleanroom rule 6's
   patent-sensitivity concern does not apply.
5. No vendor text, example or screenshot was used; the worked numeric examples
   (a five-point calibration-style sample, a two-sample comparison, a four-category
   goodness-of-fit check) are generic, independently hand-derived textbook-style
   illustrations, not sourced from any vendor's example library.
6. Before a 1.0 release, the IP policy's own legal-review step should include this
   feature too (standing reminder, same as every prior spec).

Fits current architecture?
- `engine/syntax.py`: extend `_parse_model` with the five new leading-keyword
  branches above, reusing the existing `Statement` fields (`expr`, `model`,
  `goal`) with no new field needed (unlike specs 010/015, which both needed new
  fields) — `claim`'s and `level`'s own sub-text is simple enough to defer-parse
  from the existing `expr` field alone.
- `engine/evaluator.py`: `Engine._run_model` gains `model_sample`/
  `model_expected`/`model_claim` as more "earlier member" kinds (registered,
  nothing run until `verdict`, mirroring `model_setting`'s existing handling) and,
  for `model_result`, a new `st.goal == "hypothesis_test"` branch calling into a
  new module instead of `solver.py`/`odesolver.py`/`truss.py`.
- `engine/stats_tests.py` (new, GUI-independent, parallel in spirit to
  `solver.py`/`odesolver.py`/`truss.py`): a `Model` dataclass (samples, expected,
  claim, alpha), `build(model, members, env, engine)`, `solve(model) -> Outcome`
  (statistic, df, p-value, decision). Reuses S1's `mean`/`variance`/`len` helpers
  directly (no duplicated formula) and `units.measure`/`UnitError` the same
  one-time-check way specs 003/010/015 already use it.
- `engine/formatting.py`, `engine/units.py`: no change; results are plain
  dimensionless scalars via the existing scalar path.
- Dependency: the t/chi-square distribution CDF needed for the p-value can use
  `scipy.stats` (already approved) or be hand-rolled from SciPy's lower-level
  special functions already available transitively through SymPy/SciPy — same
  open question 7 as S1, not repeated as a separate question.
- `gui/`, `document.py`: no change (plain-text regions, no format version change,
  same as every prior model-based spec).
- Tests: `tests/test_stats_tests.py` (new, developer, from the acceptance criteria
  above); independent tester writes a black-box counterpart, same process as
  every previous spec.

---

# S3 Regression (starts after S1 is merged, independent of S2)

User story:
As an engineer I have paired `(x, y)` measurement data as two vectors and want the
best-fit line or low-degree polynomial through them, plus a number that tells me
how good the fit is, so I can use the fitted formula directly in a later
expression, table or plot.

Behaviour (own words):
- `fit_linear(x, y)`: `x` and `y` are vectors of equal length `>= 2`; returns a
  2x1 coefficient vector `[intercept; slope]` from ordinary least-squares fitting
  of `y = intercept + slope*x`, built directly on spec 002b's existing
  `solve_least_squares` (the design matrix is `[1, x_1; 1, x_2; ...]`, so this
  function adds no new numerical method, only the data-shaping and the
  user-facing name — flagged explicitly in the IP check as a deliberately thin
  layer over already-approved spec 002b functionality). `intercept` carries `y`'s
  unit; `slope` carries `y`'s unit divided by `x`'s unit (spec 002's own
  "mixed-unit matrix" convention, already used by, e.g., spec 015's results).
- `fit_poly(x, y, degree)`: same idea for `y = c_0 + c_1*x + c_2*x^2 + ... +
  c_degree*x^degree`, `degree` a positive integer `< len(x)`; returns a
  `(degree + 1)`x1 vector `[c_0; c_1; ...; c_degree]`, **ascending** power order
  (own convention, chosen so `fit_poly(x, y, 1)` returns exactly the same vector
  shape and order as `fit_linear(x, y)` — flagged as open question 1, since
  several public tools order their own polynomial-fit coefficients the other way,
  highest power first, and the manager may prefer matching that instead for
  familiarity). `c_k` carries `y`'s unit divided by `x`'s unit to the `k`-th power
  (`c_0` is `y`'s own unit, `c_1` is `y`-per-`x`, etc.); a mix of units across `x`
  and `y` that cannot form one of these per-term units the normal way (i.e. `x`
  or `y` itself non-homogeneous) is the usual `Units do not match` error.
- `predict(coeffs, x)`: evaluates a fitted polynomial (the coefficient vector from
  either function above, ascending order) at a scalar or vector `x`, i.e. plain
  Horner-style evaluation of `c_0 + c_1*x + c_2*x^2 + ...`; no new numeric method,
  reuses existing scalar/vector arithmetic (sum of `c_k * x^k` terms, each already
  unit-correct from how `coeffs` itself was produced). Works with any coefficient
  vector the user builds by hand too, not only one returned by `fit_linear`/
  `fit_poly`.
- `r_squared(coeffs, x, y)`: the coefficient of determination
  `1 - sum((y_i - predict(coeffs, x_i))^2) / sum((y_i - mean(y))^2)`, dimensionless,
  normally in `[0, 1]` for a fit that includes an intercept term (can be negative
  for a deliberately poor/forced-through-origin fit — not treated as an error,
  that is the formula's own well-known behaviour).

Syntax proposal (own keywords): functions only, no grammar change — added to the
evaluator builtins the same way S1's functions are.

Acceptance criteria (tolerance: relative 1e-4 unless stated):
1. Perfect line. `x := [0, 1, 2, 3]`, `y := [1, 3, 5, 7]` (exactly `y = 1 + 2x`):
   `fit_linear(x, y) =` gives `= [1; 2]`; `r_squared(fit_linear(x, y), x, y) =`
   gives `= 1`.
2. Noisy line (ordinary least squares, hand-derivable via the normal equations).
   `x := [0, 1, 2, 3]`, `y := [1, 2, 2, 4]`: `fit_linear(x, y) =` gives
   `= [0.9; 1]` (slope `= cov(x,y)/var(x) = 2.5/1.66667 = 1.5`... use the
   textbook simple-regression formulas directly: `mean_x = 1.5`, `mean_y = 2.25`,
   `Sxy = sum((x-mean_x)(y-mean_y)) = (-1.5)(-1.25)+(-0.5)(-0.25)+(0.5)(-0.25)+(1.5)(1.75)
   = 1.875+0.125-0.125+2.625 = 4.5`, `Sxx = sum((x-mean_x)^2) = 2.25+0.25+0.25+2.25 = 5`,
   `slope = Sxy/Sxx = 0.9`, `intercept = mean_y - slope*mean_x = 2.25 - 1.35 = 0.9`):
   `fit_linear(x, y) =` gives `= [0.9; 0.9]`; `predict(fit_linear(x, y), 4) =` gives
   `= 4.5`.
3. Units. `x := [0, 1, 2, 3] s`, `y := [1, 3, 5, 7] m`: `fit_linear(x, y) =` gives
   `= [1 m; 2 m/s]` (mixed-unit vector, spec 002's existing per-element-unit print
   rule); `predict(fit_linear(x, y), 4 s) =` gives `= 9 m`.
4. Polynomial, exact fit. `x := [0, 1, 2, 3, 4]`, `y := [1, 2, 5, 10, 17]` (exactly
   `y = 1 + 0x + 1x²`): `fit_poly(x, y, 2) =` gives `= [1; 0; 1]`;
   `predict(fit_poly(x, y, 2), 5) =` gives `= 26`; `r_squared(fit_poly(x, y, 2), x, y) =`
   gives `= 1`.
5. `fit_poly(x, y, 1) =` on criterion 2's data gives the identical `[0.9; 0.9]` as
   `fit_linear` there.
Errors
6. `fit_linear([1, 2, 3], [1, 2]) =` is an error
   `Vectors must have the same length (3 and 2)`.
7. `fit_linear([1], [1]) =` is an error `fit_linear() needs at least 2 points`.
8. `fit_poly(x, y, 5) =` with `len(x) == 4` is an error
   `degree 5 needs at least 6 points, has 4`.
9. `fit_poly(x, y, 0) =` is an error `degree must be a positive integer`.
10. `predict([1, 2], [1, 2; 3, 4]) =` (a matrix, not a scalar/vector, as the `x`
    argument) is an error `predict() needs a scalar or vector x`.

Edge cases:
- `predict(coeffs, x)` with `x` a vector returns a vector of the same length (one
  prediction per entry), reusing spec 002's existing elementwise-friendly
  arithmetic — no special-casing needed beyond what sum-of-terms already does.
- Collinear/degenerate `x` (all entries equal) for `fit_linear`/`fit_poly`: the
  underlying `solve_least_squares` already errors `Matrix does not have full
  column rank` (spec 002b); this spec does not add a second, redundant check.
- `r_squared` with a constant `y` (zero variance) divides by zero in its own
  denominator; reported as `r_squared() is undefined when y is constant`, not a
  NaN.

IP check: pass. "Least-squares line/curve fitting" and "coefficient of
determination" are standard, generic statistical methods and formulas, taught
identically everywhere; `fit_linear`/`fit_poly`/`predict`/`r_squared` are plain
descriptive English names, not reused from any one vendor's own fitting-function
name. This phase is explicitly a thin convenience layer over spec 002b's already
IP-reviewed `solve_least_squares` — no new numerical method is introduced, only
data-shaping (building the design matrix) and formatting, which the IP check
flags as a reason this phase carries essentially no new IP risk beyond what spec
002b already cleared. No vendor text, example or screenshot was used; the worked
examples are small, independently hand-derived datasets (deliberately chosen to
have exact or easily-checked-by-hand answers), not sourced from any vendor's
example library.

Fits current architecture?
- `engine/matrices.py` (or the same new `engine/statistics.py` as S1 — developer's
  call, same open question 6 as S1): `fit_linear`/`fit_poly` build a design matrix
  with existing matrix constructors (`make_matrix`/`ones`-style helpers already in
  this module) and call the existing `solve_least_squares`; `predict`/`r_squared`
  are plain scalar/vector arithmetic through the existing evaluator, no new
  numerical code path.
- `engine/units.py`: no change; reuses spec 002's existing mixed-unit matrix
  handling unchanged.
- `engine/formatting.py`: no change.
- Dependency: none new; built entirely on spec 002b's `solve_least_squares`
  (SymPy-based, already approved).
- `gui/`, `document.py`: no change.
- Tests: `tests/test_regression.py` (new, developer); independent tester
  black-box counterpart, same process as every previous spec.

---

# Open questions for the manager (also candidates for docs/board/decisions.md)
1. S1 `mode`'s tie-break rule (smallest of the tied values, deterministic) and
   S2's choice to always use Welch's t-test for the two-sample case (never
   offering a "pooled/equal-variance" mode): both are real scope cuts rather than
   the only possible design — acceptable, or does Theo want an equal-variance
   two-sample option added too (`claim mean1 == mean2` could take an optional
   trailing word, e.g. `claim mean1 == mean2 pooled`, deferred rather than
   designed here unless wanted)?
2. S1 variance/stdev default to the *sample* (n-1) convention, with separate
   `population_variance`/`population_stdev` functions for the n divisor: confirm
   this naming and default direction (some introductory material instead teaches
   `variance`/`stdev` as the population formula and gives the sample version a
   different name) — this is a real judgement call with defensible arguments
   either way.
3. S1 `quantile`'s interpolation method (linear interpolation between order
   statistics at rank `p*(n-1)`): there are several other standard methods in the
   public statistics literature (nearest-rank, different interpolation constants)
   that give slightly different results for the same `p`; this spec picks the
   single most commonly taught/used one and does not expose a method choice at
   all. Acceptable, or should a later phase add a method argument?
4. S1 distribution functions reject any unit on their arguments in this phase
   (numeric-first, per the backlog's own framing). A later phase could let, e.g.,
   `normal_pdf`/`normal_cdf`/`normal_quantile` accept `mu`/`sigma`/`x` sharing one
   consistent unit (and `normal_sample` return values in that unit) — worth
   planning for now (reserving the argument shape) or safe to decide later with no
   backward-compatibility risk either way (recommendation: decide later, since
   adding unit support to an existing dimensionless-only function is additive,
   not breaking)?
5. S1 sampling functions require an explicit `seed` argument for determinism
   (matching this project's existing "same sheet always evaluates the same way"
   guarantee) rather than offering a non-deterministic default that re-rolls on
   every recalculation. Confirm this is the right trade-off for a worksheet tool —
   recommendation: keep the required `seed` (recalculation-on-every-keystroke
   would otherwise make unrelated edits elsewhere on the sheet appear to change
   numbers in a sampling region, which seems like the wrong default for an
   engineering tool, but a later "volatile/reroll" opt-in could be added without
   breaking this default).
6. Module layout: one new `engine/statistics.py` covering all three phases'
   functions, vs. folding S1/S3's vector functions into the existing
   `engine/matrices.py` and only S2's test machinery into a new
   `engine/stats_tests.py` (mirroring `solver.py`/`odesolver.py`/`truss.py`'s own
   "one new module per tagged-region feature" pattern, while plain functions stay
   wherever they most naturally belong) — developer's call unless Theo has a
   preference.
7. Implementation backend: `numpy.random` and `scipy.stats` already ship with this
   project as approved dependencies (NumPy since 2026-10-27's decision, SciPy
   since spec 003's own implementation) and have public, documented functions
   covering most of S1/S2's formulas directly. Is the developer free to use them
   as the implementation backend for this spec (least new code, most likely to be
   numerically correct), or should the formulas instead be hand-rolled from first
   principles (more code, more chance of a subtle formula bug, but zero reliance
   on a dependency's own distribution-fitting choices)? This spec does not assume
   an answer; recommendation: allow `scipy.stats`/`numpy.random` as the backend,
   since both are already-approved, permissively-licensed, and merely computing a
   standard public formula through them is squarely within "Allowed: already-
   approved dependencies" territory, not a new IP exposure, but the manager/Theo
   should make this call explicitly rather than have it decided implicitly by the
   developer.
8. S2's `claim`/`level` keyword choices, and `verdict` as the trigger word:
   acceptable, or does Theo prefer different words? (`sample` and `expected` seem
   hard to improve on; `claim` and `verdict` are more of a judgement call, chosen
   to read naturally as a sentence — "claim the mean equals 12mm" / "verdict: fail
   to reject".)
