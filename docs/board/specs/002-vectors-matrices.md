# 002 Vectors and matrices

Source inspiration (concept only, nothing copied):
- https://docs.sympy.org/latest/modules/matrices/matrices.html (BSD-licensed library docs; used only to confirm which operations exist and how shape errors surface), accessed 2026-10-27.
- Textbook linear algebra (determinant, inverse, eigenvalues, linear systems) is public-domain mathematics; the "worksheet with matrices of quantities" idea is taken from the high-level checklist in .claude/skills/mathcad-concepts. No vendor help text, examples or UI were read for this spec.

Size: too big for one slice, so this file holds two specs with a hard phase boundary.
- **002a Core** (about 3 days): literals, indexing, arithmetic, products, transpose, determinant, inverse, trace, square linear solve, constructors, units, symbolic entries, result formatting.
- **002b Eigen-analysis and decompositions** (about 2 days): eigenvalues, eigenvectors, rank, norm, least squares. Starts only after 002a is merged; it reuses 002a's value type, formatting and error style.

Interop with spec 001 (range variables, written in parallel): this spec must not depend on 001's details. Only two contact points, both optional:
1. An index may be any scalar expression that evaluates to an integer. If 001 later makes a range variable usable inside `A[i, 1]`, no change to 002 is needed; 002 itself never defines or iterates ranges.
2. A matrix value is a plain immutable SymPy matrix in the namespace (`env`), so 001 may produce or consume vectors without 002 knowing.
Anything about "tables of results" or iterating over a matrix belongs to 001.

---

# 002a Core vectors and matrices

User story:
As an engineer I write `K := [2, -1; -1, 2]*N/m`, `F := [10; 20]*N`, and `solve_system(K, F) =` gives the displacements with the right unit, without leaving the worksheet. I can also keep symbols in a matrix and ask for `det(M) →`.

Behaviour (own words):
- A matrix is a rectangular grid of scalar values (numbers, quantities with units, or symbolic expressions). A vector is a matrix with one column (column vector) or one row (row vector). There is no separate vector type.
- Literal: square brackets, elements separated by commas, rows separated by semicolons. `[1, 2, 3]` is a 1x3 row; `[1; 2; 3]` is a 3x1 column; `[1, 2; 3, 4]` is 2x2. Elements are full scalar expressions (`[1 m, 2*3 m]`, `[a+1, sin(0.5)]`). Commas are mandatory (spaces are implicit multiplication in this grammar).
- Indexing is 1-based (first row/column is 1). Bracket after a name or `)` or `]` means index; bracket anywhere else means literal. `A[i, j]` gives one element; `A[i, :]` the whole row i (a row vector); `A[:, j]` the whole column j (a column vector). A vector accepts one index `v[k]` (works for both orientations). Indices must be integers within range.
- Elementwise-at-the-matrix-level operations: `+`, `-` between equal shapes; `*` by a scalar on either side; `/` by a scalar. Matrix times matrix with `*` is the matrix product (inner sizes must agree). `A^n` for integer n is repeated product (`A^0` is the identity, `A^-1` the inverse, negative n is inverse powers). Non-integer powers are errors.
- Not allowed (each gives an error, see below): matrix + scalar, matrix / matrix, scalar / matrix, matrix as a function argument to scalar functions (`sin(A)`), comparing matrices with `==`.
- Functions (own names): `det(A)`, `inv(A)`, `transpose(A)`, `trace(A)`, `solve_system(A, b)` (solves A x = b for square invertible A; b is a vector or a matrix with the same number of rows), `dot(u, v)` (same length, any orientation), `cross(u, v)` (length 3), `hadamard(A, B)` (entry-by-entry product, equal shapes), `eye(n)`, `zeros(r, c)`, `ones(r, c)`, `diag(v)` (square matrix with vector on the diagonal), `nrows(A)`, `ncols(A)`, `len(v)`.
- Units: each element carries its own units. Whole-matrix operations are dimension-checked as the underlying scalar arithmetic is: sums need equal dimensions per position, products multiply dimensions. A matrix is "homogeneous" if all elements share one dimension. `inv` of a homogeneous matrix gives the inverse dimension; `det` of an n x n homogeneous matrix gives dimension^n; `solve_system(K, F)` gives dim(F)/dim(K). A matrix with mixed dimensions is legal to store and index; `det`, `inv`, `solve_system` and `trace` on mixed matrices produce a "Units do not match" error if the underlying sums mix dimensions (do not invent special rules).
- Symbolic entries: undefined names inside a matrix are symbols. Definitions (`M := [a, b; c, d]`) succeed. All operations above work symbolically when entries are symbolic. `M =` (numeric) fails with the existing "... not defined" error listing every undefined name. `→` shows exact results. Existing symbolic keywords (`simplify`, `expand`, `factor`, `together`, `float, n`, `substitute, x = 2`) apply entry by entry to a matrix. Keywords that need a single scalar problem (`solve`, `diff`, `integrate`, `series`, `collect`, `partfrac`) on a matrix give an error instead of guessing.
- Result formatting (numeric `=` and symbolic `→`): one text line that uses the same bracket syntax as the input, so a result can be copied back as input. Elements are separated by `, `, rows by `; `. Numbers use the existing 6-significant-digit rule (`format_number`), exact rationals print as decimals for `=` and as fractions for `→`. If the matrix is homogeneous, the unit is printed once after the closing bracket, SI-simplified like scalars (`[1, 2; 3, 4] m`); the optional target unit after `=` (`F = kN`) converts every element. If the matrix is mixed, each element prints its own unit inside the brackets. Scalar results (`det`, `trace`, `dot`, an indexed element) print exactly as scalars do today. Matrices larger than 10 rows or 10 columns print as a placeholder `[12x12 matrix]` (a table view is a GUI follow-up).

Syntax proposal (own keywords):
- Grammar change (explicit): a pre-parse step in `Engine.parse` (after `normalize`) that (1) rewrites a bracket literal `[a, b; c, d]` into a matrix construction and (2) rewrites `X[i, j]`, `X[i, :]`, `X[:, j]`, `X[k]` into a call of an internal 1-based `index` helper. `parse_statement` and the statement grammar (`:=`, `≡`, `=`, `→`) are unchanged: the first `=` handling, the `→` keyword split and `_parse_lhs` already cope because the bracket text sits inside the expression part. The pre-parse must be bracket-aware (a `;` or `,` inside brackets is never a statement separator, and `:` inside brackets is only a slice marker).
- `A[i, j] := value` (element assignment) is NOT supported; `_parse_lhs` already rejects it with a clear message and that message is the expected behaviour.
- Function names above are added to the evaluator builtins. A user definition with the same name wins, as with units today.
- Value storage: immutable SymPy matrices in `env`. `_numeric` replaces its "Matrices are not supported yet" branch; `_check_defined` must inspect matrix elements.

Acceptance criteria (a "region" below is one math region; `X =` means the output text after the evaluation):
Literals and formatting
1. `A := [1, 2; 3, 4] =` outputs `= [1, 2; 3, 4]`.
2. `[1, 2, 3] =` outputs `= [1, 2, 3]`; `[1; 2; 3] =` outputs `= [1; 2; 3]`.
3. `[0.5, 1/3] =` outputs `= [0.5, 0.333333]`; `[0.5, 1/3] →` outputs `→ [1/2, 1/3]`.
4. `[1, 2; 3] =` is an error: `Rows have different lengths (2 and 1)`. `[] =` is an error: `Empty matrix`.
5. `eye(12) =` outputs `= [12x12 matrix]`; `nrows(eye(12)) =` outputs `= 12`.
Indexing
6. With A as in 1: `A[2, 1] =` gives `= 3`; `A[1, :] =` gives `= [1, 2]`; `A[:, 2] =` gives `= [2; 4]`; `v := [5; 6; 7]` then `v[3] =` gives `= 7`, and `[5, 6, 7][2] =` gives `= 6`.
7. `A[0, 1] =` is an error `Index 0 out of range 1..2`; `A[1, 3] =` is an error `Index 3 out of range 1..2`; `A[1] =` is an error `A matrix needs two indices`; `A[1.5, 1] =` is an error `Index must be an integer`.
Arithmetic
8. `A + A =` gives `= [2, 4; 6, 8]`; `A - A =` gives `= [0, 0; 0, 0]`; `2*A =` and `A*2 =` give `= [2, 4; 6, 8]`; `A/2 =` gives `= [0.5, 1; 1.5, 2]`.
9. `A*A =` gives `= [7, 10; 15, 22]`; `A^2 =` gives the same; `A^0 =` gives `= [1, 0; 0, 1]`; `A^-1 =` gives `= [-2, 1; 1.5, -0.5]`.
10. `[1, 2, 3]*[1; 2; 3] =` gives `= 14` (1x3 times 3x1 is a 1x1 matrix, printed as a scalar); `[1; 2; 3]*[1, 2, 3] =` is a 3x3 matrix whose element (3,3) is 9.
11. `hadamard(A, [5, 6; 7, 8]) =` gives `= [5, 12; 21, 32]`. `dot([1, 2, 3], [4, 5, 6]) =` gives `= 32`. `cross([1, 0, 0], [0, 1, 0]) =` gives `= [0, 0, 1]`.
12. `transpose(A) =` gives `= [1, 3; 2, 4]`; `transpose([1, 2, 3]) =` gives `= [1; 2; 3]`; `trace(A) =` gives `= 5`.
13. `eye(3)`, `zeros(2, 3)`, `ones(1, 2)`, `diag([1, 2, 3])` give the obvious matrices; `zeros(2, 3) =` gives `= [0, 0, 0; 0, 0, 0]`.
Determinant, inverse, solve
14. `det(A) =` gives `= -2`. `det([1, 2; 2, 4]) =` gives `= 0` (a singular matrix has a determinant, only `inv` fails).
15. `inv(A) =` equals `A^-1` of 9. `inv(A)*A =` gives `= [1, 0; 0, 1]` (exact entries, so no rounding noise).
16. `b := [5; 6]` then `solve_system(A, b) =` gives `= [-4; 4.5]`. Check `A*solve_system(A, b) =` returns `= [5; 6]`.
17. Float tolerance: `inv([1.0, 2.0; 2.0, 4.0])` is an error `Matrix is singular` (rank deficiency with relative tolerance 1e-12 for float entries; exact zero determinant for exact entries). `inv([1, 2; 3, 4.0000000000001])` succeeds.
18. 3x3 check: `det([2, 0, 1; 1, 3, 2; 1, 1, 2]) =` gives `= 6`; `det([2, 0, 1; 1, 3, 2; 1, 1, 1]) =` gives `= 0` and `inv` of that matrix is the error `Matrix is singular`.
Units
19. `det([1, 2; 3, 4]*m) =` gives `= -2 m²`.
20. `K := [2, -1; -1, 2]*N/m`, `F := [10; 20]*N`, `x := solve_system(K, F)`, `x =` gives `= [13.3333; 16.6667] m`; `x = mm` gives `= [13333.3; 16666.7] mm`. `K*x =` gives `= [10; 20] N`.
21. `[1 m, 2 km] =` gives `= [1, 2000] m`; `[1 m, 2 s] =` gives `= [1 m, 2 s]`; `[1, 2]*m + [1, 2]*s =` is an error `Units do not match`.
22. `dot([1, 2]*m, [3, 4]*N) =` gives `= 11 J`. `inv([2, 0; 0, 4]*m) =` gives `= [0.5, 0; 0, 0.25] 1/m` rendered with the existing unit text rules (dimension length^-1).
23. `[1, 2]*m =` with target unit: `[1, 2]*m = cm` gives `= [100, 200] cm`; target of the wrong dimension (`= s`) gives the existing `Units do not match: result is length` style error.
Symbolic
24. `M := [a, b; c, d]` produces no error and no output; `M =` is an error listing `a, b, c, d are not defined`.
25. `det(M) →` is equal (symbolic difference zero) to `a*d - b*c`. `inv(M) →` is equal to `[d, -b; -c, a]/(a*d - b*c)` entry by entry. `transpose(M) → ` swaps b and c.
26. `[1, x; 2, 3]` with x undefined: `det([1, x; 2, 3]) →` equals `3 - 2*x`. With `x := 2` defined above, `det([1, x; 2, 3]) =` gives `= -1`.
27. `M*M → expand` entry (1,1) equals `a**2 + b*c`. `[x, x]*2 → ` equals `[2*x, 2*x]`.
28. `M → solve, a` is an error `'solve' does not apply to matrices`.
Errors (exact text is the contract; one line, no stack trace)
29. `A + [1, 2, 3; 4, 5, 6] =` error `Matrix sizes do not match: 2x2 and 2x3`.
30. `A*[1, 2, 3] =` (2x2 times 1x3) error `Cannot multiply 2x2 by 1x3`.
31. `det([1, 2, 3; 4, 5, 6]) =` error `Matrix must be square (got 2x3)`; same text for `inv`, `trace`, `A^2` on non-square.
32. `inv([1, 2; 2, 4]) =` and `solve_system([1, 2; 2, 4], [1; 2]) =` error `Matrix is singular`.
33. `solve_system(A, [1; 2; 3]) =` error `Right-hand side has 3 rows, matrix has 2`.
34. `A + 1 =` error `Cannot add a scalar to a matrix`; `1/A =` and `A/A =` error `Cannot divide by a matrix; use inv(...)`; `sin(A) =` error `sin() does not accept a matrix`; `A^0.5 =` error `Matrix power must be an integer`.
35. `cross([1, 2], [3, 4]) =` error `cross() needs vectors of length 3`; `dot([1, 2], [1, 2, 3]) =` error `dot() needs vectors of equal length`.
36. `eye(0)` and `zeros(-1, 2)` error `Size must be a positive integer`; any dimension above 200 errors `Size too large (max 200)`.
Regression
37. All existing tests in tests/test_engine.py, test_document.py and test_gui.py still pass; `.lsheet` files are unchanged (regions store text).
38. Evaluation order still top-to-bottom, left-to-right: a matrix defined below its use is "not defined" at the use.

Edge cases:
- A variable called `T` (Tesla) is not the transpose operator; transpose is only the function `transpose(...)`. A user-defined `eye := 3` shadows the function, as with unit names.
- Nested brackets (matrix inside a matrix) are an error `Nested matrices are not supported`. Block matrices are a non-goal.
- 1x1 results of matrix products collapse to scalars (acceptance 10). Literal `[5]` stays a 1x1 matrix; `[5][1] =` gives `= 5`.
- Slices keep orientation: `A[1, :]` is a row, `A[:, 1]` a column.
- Complex entries are allowed and use the existing complex formatting (`1 + 2i`).
- Large symbolic matrices (above about 6x6) may be slow; no performance guarantee, but numeric 50x50 `inv` and `det` with float entries must finish in under 2 s.
- Empty cells such as `[1, , 3]` or a trailing `;` (`[1, 2;]`) are syntax errors `Empty matrix element`.
- Named function definitions may take matrices (`f(M) := det(M)`), and function bodies may contain literals.

IP check: pass. Matrix notation `[a, b; c, d]` with comma/semicolon is long-standing generic mathematical-software notation, not a vendor keyword; 1-based indexing is the usual mathematical convention (no `ORIGIN`-style setting is copied). All function names are generic textbook terms (`det`, `inv`, `transpose`, `trace`, `dot`, `cross`, `eye`, `zeros`, `ones`, `diag`) or own names (`solve_system`, `hadamard`, `nrows`, `ncols`); vendor names for linear solve, row/column count and identity construction were deliberately avoided, and determinant bars `|A|` and subscript indexing are deliberately not used. No vendor text or examples used; all numeric examples are made up here. No known patented UI technique is involved. Open point for the manager: see open questions 1 and 4.

Fits current architecture?
- `livesheet/engine/evaluator.py`: new pre-parse step in `Engine.parse`, new builtins, matrix branch in `_numeric` (currently raises "Matrices are not supported yet"), `_check_defined` and `_apply_keyword` entry-wise handling.
- `livesheet/engine/formatting.py`: new `format_matrix` (numeric and symbolic modes) plus placeholder rule; reuse `format_number`, `format_expr`.
- `livesheet/engine/units.py`: new helper to measure a matrix element-wise and report a common dimension (or "mixed"); `measure` itself stays scalar.
- `livesheet/engine/syntax.py`: no grammar change to statements; at most a test that brackets survive `normalize`.
- gui/: no change (result is text). `document.py`: no change.
- Dependency: SymPy only (already present, BSD).

---

# 002b Eigen-analysis and decompositions (phase 2, start after 002a is merged)

User story:
As an engineer I analyse a stiffness or covariance matrix: I want its eigenvalues (natural frequencies squared), eigenvectors, rank and norm, and I want to fit an overdetermined linear system in the least-squares sense.

Behaviour (own words):
- `eigenvalues(A)` returns a column vector with every eigenvalue of a square matrix, repeated by multiplicity. Numeric order (when all values are numeric): ascending by real part, ties by imaginary part. Symbolic order is unspecified (tests compare as multisets). With `=` and exact entries, eigenvalues are computed numerically with tolerance 1e-10 (relative); with `→` they are exact when SymPy can find closed forms, otherwise the region shows an error (`No closed form found; use =`).
- `eigenvectors(A)` returns a square matrix whose columns are unit-length (Euclidean) eigenvectors, column k belonging to the k-th entry of `eigenvalues(A)`. Sign convention: the first non-zero component of each column is positive. Eigenvectors are dimensionless. For repeated eigenvalues with a full set of vectors, any orthonormal basis of that eigenspace is acceptable only if it is deterministic (same input, same output). Defective matrices give an error.
- `rank(A)` is the number of linearly independent rows (exact for exact entries; tolerance 1e-10 times the largest singular value for float entries).
- `norm(v)` is the Euclidean length of a vector, keeping the vector's unit; `norm(A)` for a matrix is the Frobenius norm (square root of the sum of squared magnitudes), also keeping the unit if homogeneous. Mixed-dimension input is an error `Units do not match`.
- `solve_least_squares(A, b)` for A with at least as many rows as columns and full column rank returns the x that minimises norm(A x - b). For square invertible A it equals `solve_system`. Unit rule is the same as `solve_system`.
- Units: for a homogeneous matrix, eigenvalues carry that unit; eigenvectors are dimensionless; rank is dimensionless.
- Non-goals for 002b: LU/QR/SVD/Cholesky as multi-valued outputs (would need a "several results" syntax; needs a decision first), matrix exponential and other matrix functions, sparse matrices, complex-Hermitian special handling.

Syntax proposal (own keywords): functions only, no grammar change: `eigenvalues`, `eigenvectors`, `rank`, `norm`, `solve_least_squares`.

Acceptance criteria:
1. `eigenvalues([2, 1; 1, 2]) =` gives `= [1; 3]`. `eigenvalues([4, 1; 2, 3]) =` gives `= [2; 5]`. `eigenvalues(eye(3)) =` gives `= [1; 1; 1]`.
2. `eigenvalues([0, -1; 1, 0]) =` gives two purely imaginary values ordered by imaginary part: elements equal -i then +i; formatting is whatever `format_number` produces for each element.
3. `eigenvalues([2, 1; 1, 2]*kPa) =` gives `= [1000; 3000] Pa`.
4. Symbolic: `eigenvalues([a, 0; 0, d]) →` contains a and d (compare as multiset); `eigenvalues([1, 2; 3, 4]) →` exact values are `(5 - sqrt(33))/2` and `(5 + sqrt(33))/2`, `=` gives `= [-0.372281; 5.37228]`.
5. `eigenvectors([2, 1; 1, 2]) =` gives `= [0.707107, 0.707107; -0.707107, 0.707107]` (columns for eigenvalues 1 and 3). `eigenvectors([2, 0; 0, 3]) =` gives `= [1, 0; 0, 1]`. Property check on a random 4x4 symmetric float matrix: `A*V - V*diag(eigenvalues(A))` has max absolute entry below 1e-9.
6. `rank([1, 2; 3, 4]) =` gives `= 2`; `rank([1, 2; 2, 4]) =` gives `= 1`; `rank(zeros(3, 3)) =` gives `= 0`; `rank([1, 2, 3; 4, 5, 6; 7, 8, 9]) =` gives `= 2`.
7. `norm([3; 4]) =` gives `= 5`; `norm([3; 4]*m) =` gives `= 5 m`; `norm([1, 2; 3, 4]) =` gives `= 5.47723`; `norm([1 m, 2 s]) =` is an error `Units do not match`.
8. `solve_least_squares([1, 1; 1, 2; 1, 3], [1; 2; 2]) =` gives `= [0.666667; 0.5]`. For square A=[1, 2; 3, 4], b=[5; 6] it gives the same as `solve_system` (`[-4; 4.5]`). Units: `solve_least_squares([1, 1; 1, 2; 1, 3]*N/m, [1; 2; 2]*N) =` gives `= [0.666667; 0.5] m` (both components have dimension length).
Errors
9. `eigenvalues([1, 2, 3; 4, 5, 6]) =` error `Matrix must be square (got 2x3)`.
10. `eigenvectors([1, 1; 0, 1]) =` error `Matrix is defective: not enough independent eigenvectors`.
11. `solve_least_squares([1, 2; 2, 4; 3, 6], [1; 2; 3]) =` error `Matrix does not have full column rank`; `solve_least_squares([1, 2, 3; 4, 5, 6], [1; 2]) =` error `Need at least as many rows as columns`.
12. Scalar arguments: `rank(5) =` is an error `rank() needs a matrix`; `norm(-5) =` gives `= 5` (absolute value).
Edge cases:
- Matrices of size up to 8x8 with exact rational entries must finish `eigenvalues(...) =` under 2 s; above that only float entries are guaranteed.
- Eigenvalues of a matrix with a symbolic entry and `=` give the standard "not defined" error.
- A matrix containing both exact and float entries is treated as float.

IP check: pass. Eigenvalue/eigenvector/rank/norm/least squares are standard mathematics. Function names are descriptive English or own (`solve_least_squares`); the common short vendor names for eigen-analysis were avoided on purpose. Sign convention and ordering are own choices, not copied from any tool.

Fits current architecture?
- `evaluator.py` builtins only; `formatting.py` reuses `format_matrix` from 002a; `units.py` reuses the homogeneous-matrix helper from 002a. SymPy provides the algorithms (`Matrix.eigenvals`, `eigenvects`, `rank`, `norm`); numeric path may use `sympy.N` with tolerance, no NumPy dependency needed (decision for the developer; adding NumPy is permissive-licensed but is a new dependency, see open question 3).

---

# Open questions for the manager (copy to docs/board/decisions.md if accepted)
1. Index base: 1-based (math convention, chosen here) versus 0-based (Python). Switchable per worksheet is explicitly NOT proposed (more state). Theo to confirm.
2. Output separator and bracket style `[1, 2; 3, 4]` (round-trippable) versus a 2-D grid. Grid rendering is a GUI/typesetting follow-up (backlog item 18); is the `[12x12 matrix]` placeholder acceptable until then?
3. NumPy: allowed for 002b performance (BSD) or stay SymPy-only?
4. Notation review: matrix literal `[ ; ]` and bracket indexing are generic notation, but the manager should confirm in the same pass as the existing notation review of `≡` and `→`.
5. Multi-valued results (LU, QR, SVD) need a syntax decision (e.g. tuple assignment `(Q, R) := qr(A)`); deferred out of 002b.
6. Should unit mismatches in `C := A + B` (definition only, no `=`) be reported at the definition or only when displayed? Spec acceptance only requires the error at display; reporting at definition is preferred if cheap.
7. Elementwise application of scalar functions (`sqrt` over a vector) is left out; it overlaps backlog item 12 (map over lists, mathematica-specialist). Coordinate before adding.
