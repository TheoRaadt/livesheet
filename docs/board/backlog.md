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
8. Cross-worksheet references, CSV import/export
9. Equation numbering, input validation / warnings, tolerance display

M3 CAS depth
10. Assumptions on symbols (real, positive, integer)  (mathematica-specialist)
11. User rewrite rules / pattern replace              (mathematica-specialist)
12. Lists + map/fold over lists                        (mathematica-specialist)
13. Interactive sliders bound to variables             (mathematica-specialist)
14. ODE solving, numeric and symbolic                 (mathcad/mathematica)

M4 Usability
15. Context menu of valid operations on a selected expression  (maple-specialist)
16. Guided assistants (ODE, curve fit, unit conversion)        (maple-specialist)
17. Toolboxes/packages loaded on demand                        (maple-specialist)
18. Real 2-D math typesetting                                  (developer)
19. Code export to Python                                      (maple-specialist)

Proposed extras (not yet approved): plugin API, standard constants/material library, step-by-step solution display, LaTeX export, Jupyter-style headless run (`livesheet run file.lsheet`), CI on GitHub Actions (macOS/Linux/Windows), packaged installers, i18n (NL/EN), accessibility.

Added 2026-10-27: 20. Push-down layout / reserved space for tall results (GUI)  21. f(M):=det(M) deferred matrix evaluation  22. Clearer message when a symbol is defined elsewhere in the sheet (e.g. 'x is defined above as 5')  23. LU/QR/SVD multi-result syntax (002b+)  24. Wrap long results (matrices, `⇒` solve lines, tables) / soft-wrap result text in the GUI
