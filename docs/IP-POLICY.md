# LiveSheet IP policy (clean-room)

Goal: take the best *ideas* from worksheet/CAS tools without infringing anyone's rights.

## Allowed
- Mathematical methods, algorithms and concepts (not protected: ideas, methods, math notation).
- Describing *what a feature does for the user* in our own words, based on PUBLIC documentation.
- Standard math/engineering notation (:=, integral signs, arrows) and common function names (sin, solve, diff).
- Own code only, or dependencies with a permissive licence (MIT/BSD/Apache-2.0, e.g. SymPy, PySide6 under LGPL as dynamic dependency).

## Forbidden
- Copying code, help-text, tutorials, example worksheets, icons, screenshots, layouts or file-format internals from Mathcad, Mathematica or Maple.
- Using the names Mathcad, Mathematica, Maple, Wolfram, PTC, Maplesoft in product name, UI, marketing or file extensions. (Factual comparison in docs is OK; keep it minimal and nominative.)
- Decompiling, reverse-engineering, or reading proprietary binaries/installed files of those programs.
- Implementing their proprietary file formats (.mcdx, .xmcd, .nb, .mw) without a separate legal review.
- GPL/AGPL dependencies (licence decision: MIT or Apache-2.0).
- Reproducing their proprietary keyword set 1:1 as a compatibility layer (e.g. `Given/Find`, Wolfram Language names like `Manipulate`). Use own names.

## Process
1. Specialist agents write *behavioural specs* (what / why / acceptance criteria) from public docs, with source URL and access date. No quotes beyond a few words.
2. Developer agent implements from the spec only, never from the vendor docs.
3. Manager reviews each spec for IP red flags before it goes to the developer.
4. Open points go to docs/board/decisions.md for a human (Theo) decision.

Not legal advice: have a lawyer review before a public 1.0 release.
