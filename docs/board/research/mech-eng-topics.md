# Mechanical-engineering topic research (input to spec 033)

Author: mathcad-specialist. Date: 2026-11-12. Status: research note, NOT a spec, NOT IP-reviewed by the manager.
Request (Theo, 2026-11-12): learn which engineering subject areas a commercial HP-calculator-era
mechanical-engineering application pack covers, then propose adding as much of that subject matter as
sensible to LiveSheet's mechanical-engineering area, clean-room only.

## 1. What I used, and what I deliberately did not

### 1a. Product description (subject-area nouns only)
- Used: search-result summaries of resale/catalogue-style listings for the product, which name its
  subject areas in general terms: beams, fluid mechanics, heat transfer, mechanics, stress analysis,
  vibration, gas laws, steam tables, thermocouples, and a count of equations. Only these generic
  subject-area nouns were taken. The listing pages themselves were NOT opened (only their search
  snippets were seen). Candidate listing URLs seen in search results, not opened:
  https://www.ebay.com/itm/117373701871 and http://www.adras.com/Sparcom-Mechanical-Engineering-Pac-for-HP-48SX.t1084-182.html
  (accessed 2026-11-12).
- Also seen in a search-result forum snippet (not opened): the words "vector analysis", "constants
  library", "equation library", "reference library". Generic nouns only; vector analysis is already
  covered by LiveSheet's existing `dot`/`cross`, constants are already backlog 8a(ii).

### 1b. Deliberately NOT used
- The vendor's own owner's manuals for this pack and its sibling packs. Search results offered PDFs of
  these manuals hosted on a third-party archive site, and one search answer suggested reading a manual's
  table of contents. I did NOT open, read, skim, or quote any of them. Reason: ip-cleanroom rule 7(a)/(b)
  and docs/IP-POLICY.md "Forbidden" (vendor documentation is not a public source for this project, and
  a freely downloadable copy does not change that). Manager: please record this in decisions.md so no
  later session opens those PDFs.
- No vendor menu names, screen layouts, keyword or command names, example problems, help text,
  numbering, ordering, or data tables from any vendor product.
- The product's own grouping and ordering of topics. The outline in section 3 uses LiveSheet's own
  taxonomy, built from the generic public sources in section 2.

## 2. Public sources consulted (accessed 2026-11-12)
All are Wikipedia articles, licence CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Only
facts (formulas, symbol meanings, which textbook case a formula covers) were used. No sentence or table was
copied. Formulas are not copyrightable facts; no text is reproduced in this project.

| Topic | URL | What was confirmed |
|---|---|---|
| Mechanical engineering overview | https://en.wikipedia.org/wiki/Mechanical_engineering | Generic sub-discipline names (statics, mechanics of materials, fluid mechanics, thermal engineering, heat transfer, vibration, hydraulics, etc.) |
| Second moment of area | https://en.wikipedia.org/wiki/Second_moment_of_area | Rectangle b h^3/12 about the centroidal axis; solid circle pi r^4/4 (= pi d^4/64); parallel-axis theorem |
| Euler-Bernoulli beam theory | https://en.wikipedia.org/wiki/Euler%E2%80%93Bernoulli_beam_theory | Beam equation EI w'''' = q; cantilever tip load deflection PL^3/(3EI); simply supported centre load PL^3/(48EI) |
| Deflection (engineering) | https://en.wikipedia.org/wiki/Deflection_(engineering) | Cantilever uniform load qL^4/(8EI); simply supported uniform load 5qL^4/(384EI) |
| Euler buckling | https://en.wikipedia.org/wiki/Euler_buckling | P_cr = pi^2 E I/(K L)^2 with effective length factor K; slenderness ratio K L / r. NOTE: the page's text writes r = I/A; the standard definition is r = sqrt(I/A). This spec uses sqrt(I/A). |
| Pressure vessel | https://en.wikipedia.org/wiki/Pressure_vessel | Thin-walled cylinder: hoop stress p r/t, longitudinal stress p r/(2t); r inner radius, p gauge pressure |
| Mohr's circle | https://en.wikipedia.org/wiki/Mohr%27s_circle | Plane-stress rotation formula; principal stresses = average +/- R; R = sqrt(((sx-sy)/2)^2 + txy^2); max shear = R |
| Torsion (mechanics) | https://en.wikipedia.org/wiki/Torsion_(mechanics) | Shear stress T r/J; twist angle T L/(G J); J for solid circle pi d^4/32 and annulus pi(Re^4 - Ri^4)/2 |
| Gear train | https://en.wikipedia.org/wiki/Gear_train | Speed ratio of meshing gears = inverse ratio of pitch radii / tooth counts |
| Hertzian contact stress | https://en.wikipedia.org/wiki/Hertzian_contact_stress | Sphere-on-plane maximum contact pressure p0 = (1/pi)(6 F E*^2 / R^2)^(1/3) (page confirmed; used in a later phase only) |
| Natural frequency | https://en.wikipedia.org/wiki/Natural_frequency | Undamped mass-spring angular frequency sqrt(k/m) (square root lost in the page's text; standard form) |
| Damping ratio | https://en.wikipedia.org/wiki/Damping_ratio | Damped frequency wn sqrt(1-zeta^2); log decrement delta from peak ratio; zeta = delta / sqrt(delta^2 + (2 pi)^2) |
| Bernoulli's principle | https://en.wikipedia.org/wiki/Bernoulli%27s_principle | p + rho v^2/2 + rho g z = const along a streamline (steady, incompressible, inviscid) |
| Darcy-Weisbach equation | https://en.wikipedia.org/wiki/Darcy%E2%80%93Weisbach_equation | Head loss f (L/D) v^2/(2g); laminar f = 64/Re; turbulent f depends on Re and roughness |
| Reynolds number | https://en.wikipedia.org/wiki/Reynolds_number | Re = rho u L / mu; pipe-flow laminar below about 2300 |
| Hagen-Poiseuille equation | https://en.wikipedia.org/wiki/Hagen%E2%80%93Poiseuille_equation | Laminar pipe pressure drop 8 mu L Q/(pi R^4) (R = radius) |
| Fourier's law | https://en.wikipedia.org/wiki/Fourier%27s_law | Conduction; integrated plane-wall rate k A dT/L |
| Newton's law of cooling | https://en.wikipedia.org/wiki/Newton%27s_law_of_cooling | Convective rate h A (Ts - T_inf) |
| Stefan-Boltzmann law | https://en.wikipedia.org/wiki/Stefan%E2%80%93Boltzmann_law | Radiated power eps sigma A T^4 |
| Radiative heat transfer | https://en.wikipedia.org/wiki/Radiative_heat_transfer | Net exchange proportional to sigma (T1^4 - T2^4), with emissivity correction for grey surfaces |
| Ideal gas law | https://en.wikipedia.org/wiki/Ideal_gas_law | PV = nRT, R = 8.314 J/(mol K) |
| Carnot's theorem (thermodynamics) | https://en.wikipedia.org/wiki/Carnot%27s_theorem_(thermodynamics) | Maximum efficiency 1 - Tc/Th with absolute temperatures |
| Thermocouple | https://en.wikipedia.org/wiki/Thermocouple | Seebeck effect; output depends on the material pair; standards publish reference tables; cold-junction compensation |

Searched but NOT fetched as a formula source (open point for a later phase):
- Helical spring rate k = G d^4/(8 D^3 N). The Wikipedia "Helical spring" and "Spring (device)" pages do not
  give it. A search surfaced a public university machine-design poster that reproduces a standard textbook
  form (https://www.webpages.uidaho.edu/mindworks/machine_design/posters/pdf/springs.pdf, not fetched yet).
  Must be fetched and checked before any spring spec.

## 3. Subject-area outline (LiveSheet's own taxonomy, generic topics)
The outline below is built from the public sources in section 2, grouped the way an introductory
mechanics-of-materials / thermal-fluids course groups them. It is not the product's grouping.

1. Section properties of plane shapes: rectangle, solid circle, annulus, radius of gyration.
2. Beams (linear elastic, prismatic, small deflection): cantilever and simply supported, point and uniform loads.
3. Stress and strain: axial, bending, thin-walled pressure vessel, plane stress (Mohr's circle).
4. Columns: Euler buckling, effective length factor, slenderness.
5. Shafts: torsion stress and twist, power and torque.
6. Springs: helical spring rate, springs in series and parallel (source to confirm).
7. Gears: speed ratio, pitch diameter, centre distance, gear trains.
8. Contact stress: Hertz sphere-on-plane.
9. Vibration: undamped natural frequency, damping ratio, log decrement, damped frequency.
10. Fluid mechanics: hydrostatic pressure, mean velocity, Reynolds number, Bernoulli, Darcy-Weisbach, laminar pipe flow.
11. Heat transfer: conduction, convection, radiation exchange, thermal resistances in series.
12. Thermodynamics: ideal gas law (four unknowns), Carnot efficiency, cycles (later).
13. Thermocouples: Seebeck output, cold-junction compensation (needs reference data, see section 4).
14. Steam properties: already backlog 8a(ii) (IAPWS-IF97 published formulation); not repeated here.
15. Fasteners and bearings (later): preload-torque relation, basic rating life.
16. Materials data (later): needs a data-licence decision, see section 4.

Overlaps with what LiveSheet already has: truss/FEM (spec 015), DXF section properties (specs 013/014),
statistics (017), ODE (010), the mechanical/electrical/chemical formula tabs (018-020, quick-insert text,
not functions), constants and steam tables (backlog 8a(ii)).

## 4. Data gaps and licence flags (not used, flagged for Theo)
- Material property tables (modulus, density, yield and tensile strength, thermal expansion, Poisson's
  ratio): usually from copyrighted handbooks or proprietary databases. EXCLUDED. Phase 1 uses user-entered
  values only.
- Standard rolled-section tables (I-beams, channels, angles): published by standards bodies and handbook
  publishers, copyrighted. EXCLUDED. User-entered section values only.
- Bolt stress areas, spring-wire tables, gear-rating factors, bearing rating constants: standards-body
  data (ISO, DIN, SAE, AGMA, etc.). EXCLUDED unless a public, permissively-licensed source is found and
  approved.
- Standards-based code checks (pressure-vessel codes, structural steel codes, Eurocodes): EXCLUDED. Only
  generic textbook formulas are in scope.
- Thermocouple reference functions: publicly published by NIST; licence and redistribution terms still
  need checking before any table is shipped. Not a phase-1 item.
- Physical constants (R, sigma, standard gravity): take values from scipy.constants (CODATA, BSD-3, already
  approved) at the time of implementation, never hand-typed from a handbook.

## 5. IP statement
What I did:
- Took generic subject-area nouns from search-result summaries of product listings (section 1a).
- Read public Wikipedia articles (CC BY-SA 4.0), using only the formulas and symbol meanings they state,
  which are generic textbook facts. No text was copied; this note paraphrases only the mathematical content.
- Chose LiveSheet's own taxonomy (section 3), own function names (in spec 033), own argument order and own
  error wording.

What I did NOT do:
- Did not open, read, skim, or quote any vendor manual, tutorial, example worksheet, or help text, from any
  site, including the manual PDFs that search results offered (ip-cleanroom rule 7).
- Did not use any vendor's menu, screen layout, keyword or command names, example problems, numbering, or
  ordering, or any tabulated material or standards data.
- Did not use any open-source engineering project's code or text.

Residual risks: (a) the subject-area list is generic and covers only the nouns above; (b) Wikipedia is
CC BY-SA, so anyone who later copies its prose must keep that in mind (this project copies none); (c) the
Euler-buckling page's r = I/A wording is an error relative to the standard definition, noted above; (d) not
legal advice. A lawyer review is still needed before a public 1.0 release (standing item).

## 6. Verification status
- Formulas were checked against summaries of fetched Wikipedia pages (WebFetch summaries, not the raw text),
  and cross-checked by hand. The numeric examples in spec 033 were hand-derived in this session because no
  Bash/Python run was available to the specialist; they MUST be re-run against the engine by the manager or
  tester before the developer relies on them (same process as spec 017).
