"""Statement-level syntax of a math region.

A math region holds exactly one statement::

    x := 5 m              definition
    f(x, y) := x^2 + y    function definition
    g ≡ 9.81 m/s^2        global definition (also ``::=``), visible everywhere
    x =                   numeric evaluation
    v = km/hr             numeric evaluation, shown in the given unit
    a := 2 m =            definition followed by evaluation
    (x+1)^2 →             symbolic evaluation (also ``->``)
    x^2 - 1 → factor      symbolic evaluation with keyword(s)
    x^2 == 4 → solve, x   equations use ``==``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_IDENT = r"[^\W\d]\w*"
_LHS_RE = re.compile(rf"^\s*({_IDENT})\s*(?:\(\s*([^)]*)\))?\s*$")
_IDENT_RE = re.compile(rf"^{_IDENT}$")
# an evaluation '=' is not part of :=, ==, <=, >=, !=
_EVAL_EQ_RE = re.compile(r"(?<![<>=!:])=(?!=)")
_SUPERSCRIPT_RE = re.compile(r"[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_SUP_MAP = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")
_IMAG_RE = re.compile(r"(\d)i\b")
_SQRT_RE = re.compile(r"√\s*(?=\()")
_SQRT_ATOM_RE = re.compile(r"√\s*([\w.]+)")

_REPLACEMENTS = [
    ("≔", ":="), ("->", "→"), ("×", "*"), ("·", "*"), ("⋅", "*"), ("÷", "/"),
    ("−", "-"), ("π", "pi"), ("∞", "oo"), ("µ", "μ"), ("°", "*deg"), ("≠", "!="),
]


class StatementError(ValueError):
    pass


@dataclass
class Statement:
    kind: str                     # empty | define | global | evaluate | symbolic | expression
    name: str = ""                # defined name (define/global)
    params: list[str] = field(default_factory=list)
    expr: str = ""                # right-hand side / expression to evaluate
    show: bool = False            # define followed by '=' (show the value)
    unit: str = ""                # target unit text after '='
    keywords: list[list[str]] = field(default_factory=list)  # symbolic keyword chain


def normalize(text: str) -> str:
    """Map friendly unicode input to parseable ASCII-ish text."""
    for old, new in _REPLACEMENTS:
        text = text.replace(old, new)
    text = _SUPERSCRIPT_RE.sub(lambda mt: "**(" + mt.group(0).translate(_SUP_MAP) + ")", text)
    text = _SQRT_RE.sub("sqrt", text)
    text = _SQRT_ATOM_RE.sub(r"sqrt(\1)", text)
    text = _IMAG_RE.sub(r"\1*I", text)
    text = re.sub(r"\blambda\b", "lamda", text)
    return text


def _split_eval(text: str) -> tuple[str, str] | None:
    matches = list(_EVAL_EQ_RE.finditer(text))
    if not matches:
        return None
    mt = matches[-1]
    return text[: mt.start()].strip(), text[mt.end():].strip()


def _parse_lhs(lhs: str) -> tuple[str, list[str]]:
    mt = _LHS_RE.match(lhs)
    if not mt:
        raise StatementError(f"Cannot define '{lhs.strip()}': left side must be a name or f(x, …)")
    name, params = mt.group(1), mt.group(2)
    plist: list[str] = []
    if params is not None:
        plist = [p.strip() for p in params.split(",") if p.strip()]
        for p in plist:
            if not _IDENT_RE.match(p):
                raise StatementError(f"Invalid parameter name '{p}'")
        if not plist:
            raise StatementError("A function needs at least one parameter")
    return name, plist


def parse_statement(source: str) -> Statement:
    text = normalize(source).strip()
    if not text:
        return Statement("empty")

    for op in ("≡", "::="):
        if op in text:
            lhs, rhs = text.split(op, 1)
            name, params = _parse_lhs(lhs)
            rhs, show, unit = _maybe_trailing_eval(rhs)
            return Statement("global", name, params, rhs, show, unit)

    if ":=" in text:
        lhs, rhs = text.split(":=", 1)
        name, params = _parse_lhs(lhs)
        rhs, show, unit = _maybe_trailing_eval(rhs)
        if not rhs:
            raise StatementError("Missing expression after :=")
        return Statement("define", name, params, rhs, show, unit)

    if "→" in text:
        parts = text.split("→")
        expr = parts[0].strip()
        if not expr:
            raise StatementError("Missing expression before →")
        keywords = []
        for part in parts[1:]:
            words = [w.strip() for w in part.split(",")]
            words = [w for w in words if w]
            keywords.append(words or ["simplify"])
        return Statement("symbolic", expr=expr, keywords=keywords)

    split = _split_eval(text)
    if split is not None:
        expr, unit = split
        if not expr:
            raise StatementError("Missing expression before =")
        return Statement("evaluate", expr=expr, unit=unit)

    return Statement("expression", expr=text)


def _maybe_trailing_eval(rhs: str) -> tuple[str, bool, str]:
    split = _split_eval(rhs)
    if split is None:
        return rhs.strip(), False, ""
    expr, unit = split
    return expr, True, unit
