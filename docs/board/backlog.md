# Backlog (manager-owned; engineering-calc focus first)

M1 Engineering core
1. [DONE 001] Range variables + tables
2. [002a DONE; 002b eigen/rank/least squares TODO] Vectors/matrices + linear algebra
3. [DONE 003 A+B, GUI check of B pending] Solve models (vary/settle/least/most)
4. Undo/redo                            (developer-only, no spec needed)
5. 2-D plot regions, unit-aware axes    (mathcad-specialist)
6. Temperature offset units             (mathcad-specialist)

M2 Document quality
7. Sections, collapsible areas, headers/footers, page breaks
7a. Structured heading levels for text regions (Title, Chapter, Section, Subsection), plus auto-generated Table of Contents and Index functions built from them (Theo's request 2026-10-28; (mathcad-specialist, document-structure spec))
8. Cross-worksheet references, CSV import/export
8a. Data import, two parts (Theo's request 2026-10-28; builds on item 8's CSV import; mathcad-specialist, data-import spec; only permissively-licensed/open-format readers, no vendor database client bundled):
    (i) insert/import common open-source dataset file formats (CSV/JSON and similar widely-used open formats) as vectors/matrices/tables on the sheet;
    (ii) built-in open reference datasets usable directly in calculations: material properties, physical/natural constants, and steam tables (e.g. IAPWS-IF97 water/steam properties) — sourced only from public-domain/standardised scientific data (CODATA constants, published IAPWS formulations), not copied from any vendor's packaged library; supersedes/absorbs the "standard constants/material library" line in Proposed extras below.
9. Equation numbering, input validation / warnings, tolerance display

M3 CAS depth
10. Assumptions on symbols (real, positive, integer)  (mathcad-specialist)
11. User rewrite rules / pattern replace              (mathcad-specialist)
12. Lists + map/fold over lists                        (mathcad-specialist)
13. Interactive sliders bound to variables             (mathcad-specialist)
14. ODE solving, numeric and symbolic                 (mathcad-specialist; Theo's request 2026-10-29, next spec after 008)

M4 Usability
15. Context menu of valid operations on a selected expression  (mathcad-specialist)
16. Guided assistants (ODE, curve fit, unit conversion)        (mathcad-specialist)
17. Toolboxes/packages loaded on demand                        (mathcad-specialist)
18. Real 2-D math typesetting                                  (developer)
19. Code export to Python                                      (mathcad-specialist)

Proposed extras (not yet approved): plugin API, step-by-step solution display, LaTeX export, Jupyter-style headless run (`livesheet run file.lsheet`), CI on GitHub Actions (macOS/Linux/Windows), packaged installers, i18n (NL/EN), accessibility. (Standard constants/material library moved to item 8a(ii) above, now approved for planning.)

Added 2026-10-27: 20. Push-down layout / reserved space for tall results (GUI)  21. f(M):=det(M) deferred matrix evaluation  22. Clearer message when a symbol is defined elsewhere in the sheet (e.g. 'x is defined above as 5')  23. LU/QR/SVD multi-result syntax (002b+)  24. Wrap long results (matrices, `⇒` solve lines, tables) / soft-wrap result text in the GUI
Added 2026-10-28: 25. E1 (002b): definitions like `x := eigenvalues(A)` are stored numerically, so `x →` shows floats instead of the closed form; keep exact values in definitions and evaluate numerically only for `=` (touches evaluator; after 004 A1)  26. Defective-matrix threshold 1e-8 flags nearly-equal distinct eigenvalues (`[1,1;0,1.0000000001]`) as defective  27. Dialog-based vector/matrix insertion (size picker + grid of cells, same low-IP-risk generic-dialog pattern as spec 006's plot dialog, Theo's request 2026-10-28) compiling to today's `[1,2;3,4]` text syntax (002a); no engine/format change expected (mathcad-specialist, after spec 006 ships)  28. Reading-order tie-break: two regions placed at the exact same canvas position have an unstable relative order (broken by QGraphicsScene Z-order, not insertion order); found incidentally during spec 006 development (developer)

M6 Visual modeling / component wiring canvas (Theo's request 2026-10-29; new milestone, modeling-specialist to write specs; grounded only in generic public-domain concepts per decisions.md, no new vendor added to IP-POLICY.md)
31. Component-and-wiring canvas core: place components on the sheet, connect output ports to input ports with wires, evaluate by topological sort of the wiring graph (not the sheet's normal top-to-bottom/left-to-right order); unconnected required input is a visible error state (modeling-specialist)
32. Data-source components: CSV/other open tabular formats (builds on/coordinates with backlog 8/8a's import work) and Excel files (open, permissively-licensed reader only, e.g. openpyxl — licence check before use) as wireable components (modeling-specialist)
33. Nested sub-sheet components: a whole .lsheet file embedded as a reusable block with its own named inputs/outputs, wireable like any other component; touches the .lsheet format (recursion, versioning, cross-file cycle detection) (modeling-specialist)
34. User-script components: small sandboxed JavaScript input-to-output transforms via QJSEngine (PySide6/QtQml, no new dependency), no filesystem/network access by default (modeling-specialist)

M5 Statistics and optimization (Theo's request 2026-10-29; new milestone, mathcad-specialist to write specs; numeric-first, generic textbook terminology, sourced only from public/standard statistical and optimization literature per ip-cleanroom)
29. Statistics: descriptive statistics over vectors/lists (mean, median, mode, variance, std dev, quantiles, correlation/covariance); common probability distributions (PDF/CDF/quantile/sampling for e.g. normal, binomial, Poisson, uniform); basic hypothesis tests (t-test, chi-square); linear/polynomial regression, extending the existing least-squares support (002b)
30. Optimization: general nonlinear and constrained optimization beyond today's solve-block `vary`/`settle`/`least`/`most` (003) — multiple constraints together, bounds, choice of local vs. global method, linear-programming-style problems; own syntax, no vendor solver names
