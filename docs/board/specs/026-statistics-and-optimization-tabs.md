# 026 Fill the Statistics and Optimization tabs with insert buttons

Source inspiration (concept only, nothing copied):
- General, long-established "insert a function template" palette convention in math/statistics/
  spreadsheet front ends: buttons grouped by task, each inserts a call skeleton whose argument names
  hint at argument order; the tooltip carries the one-line meaning. Generic across many tools.
- General usability heuristics (recognition over recall; chunking related items under small
  headings; consistent labels). Heuristics writing only; no text reproduced.
- Own prior material: specs 003 (solve models), 011/018-020/022 (the button/tab mechanism and the
  formula tabs' template buttons), 017 (statistics), docs/manual/statistics.md, README.md solve
  section. No vendor software, help or example was consulted.

Scope: pure GUI data change in livesheet/gui/sidepanel.py (new MATH_TOKENS rows, two
TAB_CATEGORIES entries, two placeholder entries removed). Reuses the existing button creation,
headers, FlowLayout band, `insert_token` path, tooltips and band-height logic unchanged. No engine
change, no .lsheet change, no new widget, no multi-region insertion. Outline and Data are NOT in this
spec (see 027 and the Data section below).
Size: one phase, about 1 day (data + test updates).

## Honest feasibility summary of the four placeholder tabs
| Tab | Engine/GUI support today | Verdict |
|---|---|---|
| Statistics | Full: descriptive stats, 4 distributions, t-tests/chi-square, regression (spec 017, manual statistics.md) | Feasible now, specified below |
| Optimization | Shipped: numeric solve models `vary / constraint / accuracy / steps / settle / least / most` (spec 003, engine/solver.py with SciPy, README). The old placeholder text ("nonlinear and constrained optimization") describes exactly this. Note: there is no end-user manual page for it yet (documenter gap) | Feasible now, specified below |
| Outline | Text regions are rich text with bold/italic/underline; no "heading" concept, no outline widget. Page breaks are known to the sheet | Feasible GUI-only: spec 027 |
| Data | Nothing: no CSV/table import function, no dataset object, no file I/O in the engine, no dataset section in the .lsheet format | Blocked, keep placeholder; prerequisites below |

## User story
As a user I want the Statistics and Optimization tabs to offer the same click-to-insert help the
Elements/Calculus/formula tabs do, so I do not have to remember function names, argument order or
the tagged-line forms of tests and solve models.

## Behaviour (own words)

### Mechanism (unchanged, just fed more rows)
Each button is a `MATH_TOKENS` row `(category, label, token, tip)`. Clicking inserts `token` at the
caret of the math region being edited (or a new math region), exactly like every other tab. Labels
must be unique across the whole panel (the existing `symbol_buttons` dict is keyed by label; a test
asserts this). Tokens are full templates with readable placeholder names (as the formula tabs do),
not partial "name(" stems, so multi-argument order is visible. After clicking, the user edits the
placeholder names. Tabs with more than one category show the small grey group headings and start
each group on a new row (existing behaviour).

`TAB_CATEGORIES` gains `"Statistics"` and `"Optimization"`; their entries are removed from
`PLACEHOLDER_TABS` and the two placeholder strings are deleted. `TAB_ORDER` is unchanged. Outline and
Data remain placeholders.

### Statistics tab: four groups
Placeholder names follow docs/manual/statistics.md. Label = the function (or line) name; the token is
the template; the tooltip is a one-sentence meaning plus the unit rule in the manual.

Group "Summary statistics" (10 buttons)
| Label | Token | Tooltip (own words) |
|---|---|---|
| mean | `mean(v)` | Average of a list. Keeps the list's unit. |
| median | `median(v)` | Middle value of a list. |
| mode | `mode(v)` | Most frequent value; ties give the smallest. |
| variance | `variance(v)` | Sample variance (divides by n-1). Unit squared. |
| stdev | `stdev(v)` | Sample standard deviation (divides by n-1). |
| population_variance | `population_variance(v)` | Variance treating the list as the whole population (divides by n). |
| population_stdev | `population_stdev(v)` | Standard deviation of a whole population (divides by n). |
| quantile | `quantile(v, p)` | Value a fraction p (0 to 1) of the way through the sorted data. |
| covariance | `covariance(u, w)` | Sample covariance of two equal-length lists. |
| correlation | `correlation(u, w)` | Correlation of two equal-length lists, between -1 and 1. No unit. |

Group "Distributions" (16 buttons, family by family so each family reads as one run: density/mass,
cumulative, quantile, random sample; one group so the tab does not need a header per family)
| Labels (in this order) | Tokens |
|---|---|
| normal_pdf, normal_cdf, normal_quantile, normal_sample | `normal_pdf(x, mu, sigma)`, `normal_cdf(x, mu, sigma)`, `normal_quantile(p, mu, sigma)`, `normal_sample(mu, sigma, n, seed)` |
| uniform_pdf, uniform_cdf, uniform_quantile, uniform_sample | `uniform_pdf(x, a, b)`, `uniform_cdf(x, a, b)`, `uniform_quantile(p, a, b)`, `uniform_sample(a, b, n, seed)` |
| binomial_pmf, binomial_cdf, binomial_quantile, binomial_sample | `binomial_pmf(k, n_trials, p)`, `binomial_cdf(k, n_trials, p)`, `binomial_quantile(q, n_trials, p)`, `binomial_sample(n_trials, p, n, seed)` |
| poisson_pmf, poisson_cdf, poisson_quantile, poisson_sample | `poisson_pmf(k, lambda_)`, `poisson_cdf(k, lambda_)`, `poisson_quantile(q, lambda_)`, `poisson_sample(lambda_, n, seed)` |
Tooltips: pdf/pmf = "how likely a value is", cdf = "chance of being at or below x/k", quantile =
"value below which the chance p/q lies (inverse of the cumulative)", sample = "column vector of n
reproducible random draws; seed is required". Each tooltip adds "plain numbers only, no units"
(the manual: distribution functions reject unit-bearing arguments) and, for the discrete families,
"k is a whole number of 0 or more".

Group "Hypothesis tests (one line each, same name after in)" (7 buttons; each test is several tagged
one-line regions that share the name after `in`; the placeholder name is `t1`)
| Label | Token | Tooltip |
|---|---|---|
| sample | `sample v in t1` | A measurement list for test t1. One line for a one-sample or chi-square test, two lines for a two-sample (Welch) test. Use the same name on every line of the test. |
| expected | `expected counts in t1` | Expected counts (chi-square test only); must be positive, same length as the sample. |
| claim mean | `claim mean == 0 in t1` | One-sample t-test: the average equals this value (also `<` and `>` for one-sided). |
| claim two means | `claim mean1 == mean2 in t1` | Welch two-sample t-test between the first and second sample line (also `<`, `>`). |
| claim fits | `claim fits in t1` | Chi-square fit of the sample counts to the expected counts. |
| level | `level 0.05 in t1` | Significance level; optional, default 0.05. |
| verdict | `verdict in t1` | Runs test t1 from the lines above it; shows reject / fail to reject H0 and defines t1_statistic, t1_df, t1_pvalue. |
The user clicks a button once per line, each in its own region; renaming `t1` consistently on every
line is the user's job (stated in the tooltips of `sample` and `verdict`). The placeholder `counts`
is chosen to avoid `e` (Euler's number), which the manual warns against as a variable name.

Group "Regression" (4 buttons)
| Label | Token | Tooltip |
|---|---|---|
| fit_linear | `fit_linear(x, y)` | Best straight line through paired data; gives [intercept; slope]. |
| fit_poly | `fit_poly(x, y, 2)` | Best polynomial of the given degree (1 or more, less than the number of points); constant term first. |
| predict | `predict(c, x)` | Fitted value(s) at x for a coefficient vector c. |
| r_squared | `r_squared(c, x, y)` | How well the fit follows the data (1 is perfect). |

### Optimization tab: three groups (the shipped solve-model forms from spec 003 / README)
A model is a name; tagged one-line regions belong to it; the result line collects those above it.
Placeholder model name `m1`, unknown `x`.
| Group | Label | Token | Tooltip |
|---|---|---|---|
| Unknowns and constraints | vary | `vary x from 1 in m1` | Declares unknowns and starting guesses (the guess's unit fixes the unknown's unit); several, comma separated. |
| Unknowns and constraints | equation == | `x^2 == 4 in m1` | An equation the solution must satisfy. |
| Unknowns and constraints | limit <= | `x <= 10 in m1` | An upper limit; also usable as `a <= x <= b`. |
| Unknowns and constraints | limit >= | `x >= 0 in m1` | A lower limit. |
| Settings (optional) | accuracy | `accuracy 1e-8 in m1` | Relative tolerance; default 1e-8. |
| Settings (optional) | steps | `steps 200 in m1` | Iteration limit; default 200. |
| Results | settle | `settle in m1` | Solves the equations/limits from the guess; binds the unknowns. |
| Results | least | `least x^2 in m1` | Smallest value of the expression while all constraints hold (local optimum from the guess). |
| Results | most | `most x in m1` | Largest value of the expression while all constraints hold. |
Tooltips on the result buttons remind: the starting guess is part of the problem; only a local
optimum is found.

### Deliberately NOT specified here
- A single "insert hypothesis-test skeleton" or "insert solve-model skeleton" button that creates
  3-5 stacked regions at once. `insert_token` writes into one region and a math region collapses
  newlines to spaces, so a skeleton needs a new multi-region insertion call in the main window and
  decisions about placement/undo. Optional follow-up slice if Theo wants it (open question 1).
- Any change to statistics/solver behaviour, or a Statistics/Optimization dialog.
- Layout changes to the band; see the sizing note below.

### Band height note
Statistics has 4 headers and 37 buttons: roughly 10-12 rows at 1000 px, more than the band clamp (4
rows or 25% of the window). It will scroll inside the band (existing behaviour, as Chemical already
does); the tab strip never scrolls. The band's fixed height is driven by the tallest page, so adding
Statistics may make the band taller than before for a given window height, up to the existing clamp.
Do not change the clamp in this spec; if the band feels cramped, raise it in a separate spec
(open question 2).

## Syntax proposal
None; every token is existing syntax from spec 003 and spec 017.

## Acceptance criteria
1. `TAB_CATEGORIES["Statistics"]` has the four groups above in order; `"Optimization"` has three.
   "Statistics" and "Optimization" are no longer in `PLACEHOLDER_TABS`; Outline and Data still are.
   `TAB_ORDER` is unchanged (10 tabs, same order).
2. Button counts: Summary statistics 10, Distributions 16, Hypothesis tests 7, Regression 4
   (Statistics total 37); Optimization 9. Labels are unique across the whole panel
   (`len(symbol_buttons)` equals the number of MATH_TOKENS rows, i.e. no label shadows another).
3. Clicking `fit_linear` on an empty sheet creates a math region whose source is exactly
   `fit_linear(x, y)`; clicking `mean` while a math region is being edited with the caret after
   `a := ` gives source `a := mean(v)`.
4. Engine round trip (test through the Engine, not the GUI): with `v := [2, 4, 4, 4, 5, 5, 7, 9]`,
   `u := [1, 2, 3, 4, 5]`, `w := [2, 4, 5, 4, 5]`, `p := 0.5`, `x := [0, 1, 2, 3]`,
   `y := [1, 2, 2, 4]`, `c := fit_linear(x, y)`, every Summary statistics and Regression token
   evaluates with `=` without a syntax error: `mean(v) =` gives `5`, `quantile(v, p) =` gives
   `4.5`, `fit_linear(x, y) =` gives `[0.9; 0.9]`, `predict(c, x) =` gives `[0.9; 1.8; 2.7; 3.6]`
   shape-wise a vector of 4 (developer checks exact print), `r_squared(c, x, y) =` gives `0.852632`.
   The `normal_*` tokens evaluate once `mu := 0`, `sigma := 1` and the scalar names are defined
   (e.g. `normal_cdf(1, mu, sigma) =` gives `0.841345`).
5. Test lines: `sample v in t1` + `claim mean == 7 in t1` + `verdict in t1` (with
   `v := [8, 7, 6, 9, 10]`) and `sample v in t1` + `expected counts in t1` + `claim fits in t1` +
   `verdict in t1` (with `v := [10, 20, 30, 40]`, `counts := [25, 25, 25, 25]`), built by taking the
   buttons' tokens verbatim, parse and evaluate; the first gives `t1_df =` 4 and `t1_pvalue =`
   0.2302, the second `t1_statistic =` 20. The `level 0.05 in t1` and `claim mean1 == mean2 in t1`
   (with two `sample` lines) tokens parse.
6. Solve-model tokens: `vary x from 1 in m1`, `x^2 == 4 in m1`, `x >= 0 in m1`, `settle in m1`
   parse and give `x =` 2 (to display precision); `least x^2 in m1` and `most x in m1` with
   `x >= 0` and `x <= 10 in m1` parse (least about 0, most 10). The criterion is "parses and solves
   without a syntax error"; the developer confirms the exact printed values in the engine.
7. Every new token row has a non-empty tooltip; every distribution tooltip contains "no units" and
   every discrete-distribution tooltip contains "whole number".
8. Existing tests that assert Statistics/Optimization show a placeholder label are updated; the
   full suite passes.

## Edge cases
- A user who clicks `verdict` before any `sample` gets the engine's own error; no GUI guard.
- Placeholder names avoid `e`, `i`, `pi`.
- Dark/light, keyboard (tab strip arrows, Enter) and band-height behaviour are inherited unchanged.
- docs/manual/statistics.md ("The Statistics tab ... has no buttons yet") and main-window.md
  (placeholder sentences) become stale: documenter to update after acceptance; also write the
  missing solve-model manual page.

## Data tab: why it stays a placeholder (prerequisites, not a spec)
Missing engine/format pieces, all prerequisites for any useful Data tab:
1. An engine-level way to turn a delimited text file (CSV/TSV) into vectors/matrices: a file-reading
   function or an import step, with decisions on column/header handling, units (e.g. a unit given in
   a header) and number parsing. The engine must stay GUI-independent and today has no file I/O.
2. A decision whether imported data is embedded in the .lsheet (portable, larger, format version
   bump, backward compatible per CLAUDE.md) or linked by path (small, breaks when files move).
3. A dataset notion the panel can list (name, shape, unit, source file); today a vector is just an
   ordinary variable.
The existing DXF import dialog (spec 013) is a precedent for a modal import dialog with labelled
fields, the low-risk UI shape to reuse later. Recommended next step: a "data import core" spec
(engine first), then a Data tab listing datasets with an Insert button. Until then the placeholder
text stays; optionally sharpen it (open question 3).

## IP check
Pass. Insert-template palettes are a generic convention across statistics, CAS and spreadsheet
tools; all tokens are LiveSheet's own syntax from specs 003 and 017 (own keywords vary/settle/least/
most/sample/claim/verdict); tooltips are written fresh from LiveSheet's own manual; no vendor
layout, label set or keyword list is reproduced. No on-canvas interaction is introduced (plain
buttons inserting text). Open IP question: none.

## Fits current architecture?
Yes: livesheet/gui/sidepanel.py data only (MATH_TOKENS, TAB_CATEGORIES, PLACEHOLDER_TABS,
placeholder constants and `__all__`). No engine import of PySide6, no .lsheet change.
