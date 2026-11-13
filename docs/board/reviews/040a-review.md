# Review: spec 040a (torsion H1-H5, plane stress M1-M6)

Tester: independent black-box tests in tests/test_spec040a_review.py (27 pass, 1 strict xfail documenting backlog 81). Values cross-checked with plain `math` formulas, not the implementation.

Verdict: PASS. All numeric criteria 9-20, unit/bound/error criteria 5, 6, 35, 38 (shaft), 42 match the spec; no formula or sign defects.

Findings (none are new production defects):
1. Usability, known limit (backlog 81): `0 MPa` loses its unit, so uniaxial/biaxial states such as `principal_stress_max(10 MPa, 0 MPa, 0 MPa)` and `principal_angle(10 MPa, 0 MPa, 0 MPa)` fail with "needs a unit of pressure". Criterion 39 (isotropic message) is unreachable via the engine. Very common input; raise priority of backlog 81.
2. A call with undefined names reports "not defined" only when a trailing `=` is used; without it the deferred call shows status ok and empty output (criterion 42 wording assumes an error). Spec annotation already notes the deferred behaviour.
3. Output is rounded to 5 significant digits for angles (1.1781); tests use 1e-4 there.

Quadrant checks of principal_angle (both signs of txy, compressive states) match 0.5*atan2(2txy, sx-sy). IP: no red flags; own names, generic formulas.
