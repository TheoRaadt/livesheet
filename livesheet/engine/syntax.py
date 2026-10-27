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
    t := 0 s to 10 s step 2 s   range definition (``step`` optional, also ``≡``/``::=``)
    table t, v*t in m           result table over one range variable
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

_RANGE_RE = re.compile(r"^(.+?)\s+to\s+(.+?)(?:\s+step\s+(.+))?$")
_TABLE_RE = re.compile(r"^table(?:\s+(.*))?$", re.DOTALL)
_IN_RE = re.compile(r"\sin\s")

_REPLACEMENTS = [
    ("≔", ":="), ("->", "→"), ("×", "*"), ("·", "*"), ("⋅", "*"), ("÷", "/"),
    ("−", "-"), ("π", "pi"), ("∞", "oo"), ("µ", "μ"), ("°", "*deg"), ("≠", "!="),
]


class StatementError(ValueError):
    pass


@dataclass
class Statement:
    kind: str                     # empty | define | global | evaluate | symbolic | expression | range | table
    name: str = ""                # defined name (define/global)
    params: list[str] = field(default_factory=list)
    expr: str = ""                # right-hand side / expression to evaluate
    show: bool = False            # define followed by '=' (show the value)
    unit: str = ""                # target unit text after '='
    keywords: list[list[str]] = field(default_factory=list)  # symbolic keyword chain
    range_end: str = ""           # range: end expression (``expr`` holds the start)
    range_step: str = ""          # range: step expression, empty means default step
    is_global: bool = False       # range defined with ≡ / ::=
    columns: list[tuple[str, str]] = field(default_factory=list)  # table: (expression, unit text)


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

    table = _parse_table(text)
    if table is not None:
        return table

    for op in ("≡", "::="):
        if op in text:
            lhs, rhs = text.split(op, 1)
            name, params = _parse_lhs(lhs)
            rhs, show, unit = _maybe_trailing_eval(rhs)
            rng = _parse_range(name, params, rhs, show, True)
            if rng is not None:
                return rng
            return Statement("global", name, params, rhs, show, unit)

    if ":=" in text:
        lhs, rhs = text.split(":=", 1)
        name, params = _parse_lhs(lhs)
        rhs, show, unit = _maybe_trailing_eval(rhs)
        if not rhs:
            raise StatementError("Missing expression after :=")
        rng = _parse_range(name, params, rhs, show, False)
        if rng is not None:
            return rng
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


def _parse_range(name: str, params: list[str], rhs: str, show: bool, is_global: bool) -> Statement | None:
    """Return a range statement if ``rhs`` has the form ``START to END [step STEP]``."""
    mt = _RANGE_RE.match(rhs)
    if mt is None:
        return None
    if params:
        raise StatementError("A range cannot have parameters")
    if show:
        raise StatementError("Use table to show a range")
    start, end, step = mt.group(1).strip(), mt.group(2).strip(), (mt.group(3) or "").strip()
    return Statement("range", name, expr=start, range_end=end, range_step=step, is_global=is_global)


def _parse_table(text: str) -> Statement | None:
    mt = _TABLE_RE.match(text)
    if mt is None or ":=" in text or "≡" in text:
        return None
    rest = (mt.group(1) or "").strip()
    if rest == "=":
        return None  # ordinary evaluation of a name called 'table'
    if _split_eval(rest) is not None:
        raise StatementError("table takes no '='")
    columns = []
    for part in _split_top_level(rest):
        expr, unit = _split_column_unit(part.strip())
        if expr:
            columns.append((expr, unit))
    if not columns:
        raise StatementError("table needs at least one column")
    return Statement("table", columns=columns)


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside brackets."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _split_column_unit(col: str) -> tuple[str, str]:
    """Split ``expr in unit`` at the last top-level `` in ``."""
    depth_at = []
    depth = 0
    for ch in col:
        depth_at.append(depth)
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
    last = None
    for mt in _IN_RE.finditer(col):
        if depth_at[mt.start()] == 0:
            last = mt
    if last is None:
        return col, ""
    return col[: last.start()].strip(), col[last.end():].strip()
