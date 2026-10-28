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
    plot                        first line of a plot spec; then ``over``/``show``/... lines
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

_MODEL_TAG_RE = re.compile(rf"^(.*?)\s+in\s+({_IDENT})\s*$", re.DOTALL)
_RELATION_RE = re.compile(r"==|<=|>=|<|>")
_STATEMENT_OPS = (":=", "≡", "::=", "→")

_REPLACEMENTS = [
    ("\u00a0", " "), ("≤", "<="), ("≥", ">="),
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
    model: str = ""               # model_*: model name (the trailing ``in <name>`` tag)
    guesses: list[tuple[str, str]] = field(default_factory=list)  # model_vary: (unknown, guess text)
    goal: str = ""                # model_result: root | min | max
    relations: list[str] = field(default_factory=list)  # model_require: one text per relation
    plot_lines: list[tuple[str, str]] = field(default_factory=list)  # plot: (keyword, remainder)


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

    plot = _parse_plot(source)
    if plot is not None:
        return plot

    table = _parse_table(text)
    if table is not None:
        return table

    model = _parse_model(text)
    if model is not None:
        return model

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


_PLOT_TEXT_KEYWORDS = ("title", "xlabel", "ylabel")


def _parse_plot(source: str) -> Statement | None:
    """A text whose first non-blank line is exactly ``plot`` is a plot spec (one option per line)."""
    lines = [ln.replace("\u00a0", " ").strip() for ln in source.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines or lines[0] != "plot":
        return None
    parsed: list[tuple[str, str]] = []
    for line in lines[1:]:
        word, _, rest = line.partition(" ")
        rest = rest.strip()
        parsed.append((word, rest if word in _PLOT_TEXT_KEYWORDS else normalize(rest).strip()))
    return Statement("plot", plot_lines=parsed)


def _parse_table(text: str) -> Statement | None:
    mt = _TABLE_RE.match(text)
    if mt is None or ":=" in text or "≡" in text:
        return None
    rest = (mt.group(1) or "").strip()
    if rest == "=":
        return None  # ordinary evaluation of a name called 'table'
    if _split_eval(rest) is not None:
        raise StatementError("table takes no '='")
    _check_brackets(rest)
    columns = []
    for part in _split_top_level(rest):
        expr, unit = _split_column_unit(part.strip())
        if expr:
            columns.append((expr, unit))
    if not columns:
        raise StatementError("table needs at least one column")
    return Statement("table", columns=columns)


def _check_brackets(text: str) -> None:
    """Raise a clear StatementError when brackets are unbalanced or misordered."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in text:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs and (not stack or stack.pop() != pairs[ch]):
            raise StatementError("Unbalanced brackets")
    if stack:
        raise StatementError("Unbalanced brackets")


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


# -- solve models: ``... in <name>`` tagged regions --------------------------------------

def _parse_model(text: str) -> Statement | None:
    mt = _MODEL_TAG_RE.match(text)
    if mt is None:
        return None
    body, name = mt.group(1).strip(), mt.group(2)
    if any(op in body for op in _STATEMENT_OPS) or _split_eval(body) is not None:
        return None  # an ordinary statement that happens to end in `in <word>`
    word = re.match(r"^(\w+)", body)
    keyword = word.group(1) if word else ""
    rest = body[len(keyword):].strip() if keyword else body
    if keyword == "vary":
        return Statement("model_vary", model=name, guesses=_parse_guesses(rest))
    if keyword == "settle":
        if rest:
            raise StatementError("settle takes no expression")
        return Statement("model_result", model=name, goal="root")
    if keyword in ("least", "most") and (body[len(keyword):len(keyword) + 1] in ("", " ", "(")):
        if not rest:
            raise StatementError("least/most needs an expression")
        return Statement("model_result", model=name, goal="min" if keyword == "least" else "max", expr=rest)
    if keyword in ("accuracy", "steps") and rest:
        return Statement("model_setting", model=name, name=keyword, expr=rest)
    relations = _split_relations(body)
    if relations is None:
        raise StatementError('A relation is required before "in ' + name + '"')
    return Statement("model_require", model=name, relations=relations)


def _parse_guesses(rest: str) -> list[tuple[str, str]]:
    guesses = []
    for part in _split_top_level(rest):
        mt = re.match(rf"^\s*({_IDENT})\s+from\b(.*)$", part, re.DOTALL)
        if mt is None:
            raise StatementError('Use "vary x from <guess>, y from <guess> in <name>"')
        guess = mt.group(2).strip()
        if not guess:
            raise StatementError(f'Missing starting guess for "{mt.group(1)}"')
        guesses.append((mt.group(1), guess))
    if not guesses:
        raise StatementError('Use "vary x from <guess> in <name>"')
    return guesses


def _split_relations(body: str) -> list[str] | None:
    """Split ``a <= x <= b`` into ``["a <= x", "x <= b"]``; ``None`` when there is no relation."""
    operands, ops, depth, start, i = [], [], 0, 0, 0
    while i < len(body):
        ch = body[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0:
            mt = _RELATION_RE.match(body, i)
            if mt:
                operands.append(body[start:i].strip())
                ops.append(mt.group(0))
                i = start = mt.end()
                continue
        i += 1
    if not ops:
        return None
    operands.append(body[start:].strip())
    if any(not o for o in operands):
        raise StatementError("A relation needs an expression on both sides")
    return [f"{operands[k]} {ops[k]} {operands[k + 1]}" for k in range(len(ops))]
