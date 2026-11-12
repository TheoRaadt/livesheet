# Review: spec 033 phase 1 (mechanical-engineering library, 28 functions)

Tester, 2026-11-12. Tests: tests/test_spec033_review.py (67 pass, 1 xfail documenting a pre-existing issue).
Written from the spec only; expected values computed in plain Python (math) from the textbook formulas, with
mixed input units (mm, cm, m, N, kN, MPa, GPa, cm^4, mm^4). Comparison tolerance 1e-5 (engine prints 6
significant digits).

## Result
No defects in mecheng.py. All 28 formulas match independent values, including radius of gyration (sqrt(I/A):
rect h/sqrt(12), ring sqrt(do^2+di^2)/4, solid circle exactly d/4), transition slenderness sqrt(2 pi^2 E/sy)
(Euler stress at that slenderness equals sy/2), and thin-wall hoop = 2 x longitudinal. Beam sanity: 6 m simply
supported span, 10 kN/m, E 200 GPa, I 8000 cm^4 gives 10.547 mm and 45 kN*m; stress via M*c/I equals M/S.
Scaling laws (L^3 gives 8, L^4 gives 16, 1/I, cantilever/simply-supported 16) hold.

Checked and fine: bare numbers rejected with the spec wording; wrong dimension wording; dimensionless slot
with unit; ring di >= do (also equal after unit conversion) for all three ring functions; negative or zero K,
E, I, A, t, L, sy; zero-with-unit values give an error with no traceback; J accepted as a moment; wrong
argument count (0 and n+1) for sampled functions; undefined names not swallowed; user variables pass
through; user-function bodies (call-time unit check, error wording preserved); E, I, L traps (bare E and I
rejected in dimensional slots, `1 L` rejected as "must be a length"); signature hints for all 28 via
completion.signature_for; Qt-free import in a fresh interpreter; no name collisions with BUILTINS or UNITS;
results usable in arithmetic and variables; negative loads keep their sign (spec: not rejected).

## Findings (ranked)
1. LOW, outside spec 033, needs Theo's decision: livesheet/engine/units.py (pre-existing since the MVP)
   defines inch, ft, yd, lb, lbf and psi. Theo requires SI-only; `axial_stress(10 kN, 100 mm^2) = psi` works.
   mecheng.py itself has no imperial reference. Pinned by a strict xfail test
   (test_no_imperial_units_in_engine_unit_table); remove the xfail if the units are dropped.
2. LOW, spec text: criterion 26 is wrong as written (P, L, E, I: L is litre, I the imaginary unit, E Euler's
   number). Developer already noted it; the behaviour is correct. Spec should use other symbols.
3. INFO: the dimension word "area" yields the awkward message `axial_stress: A must be a area` (article).
   Spec wording rule is `must be a <dim>`, so it matches the spec; consider "an" handling. Cosmetic.
4. INFO coverage gap: the engine prints 6 significant digits, so tests cannot check closer than 1e-5; exactness
   is only confirmed through ratio tests (8, 16, 2, 0.5) and the d/4 case printing exactly `= 10 mm`.
5. INFO: no explicit-warning tests for thin-wall or Euler range (no warning mechanism exists, per spec).

## Not done
GUI rule (launch the real app and exercise windows by hand): I had no computer-use tools in this session, so
no visual check was performed. This phase has no GUI change; autocomplete pick-up was verified headlessly via
completion.signature_for only. A manual look at the autocomplete popup for `rect_` / `euler_` is still open.

## IP red flags
None seen. Own snake_case names, textbook formulas, error wording is LiveSheet's own. No vendor names, tables,
or assets in mecheng.py. (Imperial units in units.py are a policy issue, not an IP one.)

## Transient / unrelated
The full-suite run was started in the background while other developers edit; see the log line for its result.
