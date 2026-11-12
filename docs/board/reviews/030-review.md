# Review: spec 030 (dataset names in autocomplete; evaluation-order hint)

Tester: independent black-box tests from the spec.
Tests added: tests/test_spec030_review.py (engine, 33 tests + 2 xfail defects), tests/test_spec030_gui_review.py (6 GUI tests, offscreen).
Result: full suite 3391 passed, 2 skipped, 12 xfailed (before the final GUI file edit); the two new files then pass (xfails are the defect below).
Real-window check: not done in this run (no computer-use tools were available); needs Theo's manual check, notably the error tooltip/clipping of the longer hint.

## Defects (ranked)
1. MEDIUM: hint is skipped for identifiers starting with a non-ASCII letter. `order_hint` anchors on `[A-Za-z_]\w*`.
   Repro: `Engine().evaluate([("a","w := α + 1 ="),("b","α := 5")])` gives `α is not defined` (no hint).
   Same for `σ_y`. `x_1` and `x₁` work. Greek names are common in engineering sheets, so the feature silently does
   nothing there. Also a mixed message such as `x, ğ are not defined` loses the hint for `x`. Fix: use a Unicode-aware
   identifier pattern (`[^\W\d]\w*`). Tests (xfail, non-strict): test_b_greek_name_hint, test_b_greek_subscript_name_hint.
2. LOW (spec error, not code): A12 `tr` is said to give exactly `trial_F, trial_t`, but builtins `trace`, `transpose` also match.
   Spec should say `tri`.

## Judgement of the developer's deviations
- Spec fixtures `y = 2*x`: right. In this syntax that is not a definition (result `y is not defined`, unchanged), so the
  tests must use `y := 2*x =`. A plain `y := 2*x` is lazy and raises nothing. Correct deviation; spec fixtures need fixing.
- A9 caret 15 vs 16: right. `m = mean(run1_F` has 15 characters; the spec arithmetic was wrong.
- B7: right in substance. With lazy `y`, region c reports `x is not defined` with no hint (x is defined earlier than c),
  which satisfies the intent "no hint for names defined earlier". The wording `y is not defined` in the spec cannot occur.
- Prefix `tri` instead of `tr`: right (see defect 2).
- Other spec fixtures (B3, B4, B6, B9, B11) likewise need the `:= ... =` form; B9 uses `x := 1 to 3`.

## Coverage verified
A1-A10 engine (names, kinds, hints incl. unitless, text column, order, groups, exact-case, live-list vanishing,
Qt-free import in a fresh interpreter, accept without paren, clash once as data, perf with 5x100 columns, generator input).
A11-A14 GUI (popup content, Tab accept, remove, rename, save/reload without CSV, TextRegion no popup).
B1-B13, B15 (hint exact text, plural/singular chosen by undefined count, global no hint, self reference, function, range,
bare-unit path, dataset never later, idempotent helper, anchored match leaves other text, ASCII one-liner, move region clears error, tooltip carries full text).

## Gaps
Not tested: model/solve/plot-row and matrix-cell paths for the hint; wrapping/clipping of the long error in a narrow region
visually (tooltip exists in regions.py lines ~502, 761); popup tag rendering pixels.

## IP red flags
None. Wording and tags are own; no vendor names or text seen in the diff.
