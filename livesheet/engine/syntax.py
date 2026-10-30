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

# ``ode`` line: the left side of the single top-level ``==`` must *start* with a pure
# ``diff(F(X), X)`` or ``diff(F(X), X, N)`` term (one of its top-level additive terms,
# the first one); the rest of the left side, if any, follows as an ordinary ``+``/``-``.
_ODE_LHS_RE = re.compile(
    rf"^diff\(\s*({_IDENT})\(\s*({_IDENT})\s*\)\s*,\s*({_IDENT})\s*(?:,\s*(\d+)\s*)?\)"
)
_ODE_SHAPE_ERROR = "Write the highest derivative alone on the left: diff(name(t), t[, n]) == ..."

# ``start`` line: one condition per comma-separated item, ``f(point) == value`` with an
# optional run of prime marks on ``f`` giving the derivative order (0 when absent).
_START_ITEM_RE = re.compile(rf"^({_IDENT})('*)\(\s*(.+?)\s*\)\s*==\s*(.+)$", re.DOTALL)
_START_SHAPE_ERROR = 'Use "start f(point) == value" (optionally f\'(point) == ..., ...)'

# ``over`` sub-grammar, shared between spec 004's plot blocks and this ODE ``over`` line:
# ``NAME from A to B [points N]``.
_SAMPLING_WORDS = ("from", "to", "points")
_SAMPLING_ERROR = "over needs 'NAME from A to B [points N]'"

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
    conditions: list[tuple[str, int, str, str]] = field(default_factory=list)
    # model_ic: one 4-tuple per condition (function name, derivative order, point text, value text)
    over_points: str = ""        # model_over: the sampling count text ("" means default)


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


# -- shared with engine/plotting.py's own ``over`` line (spec 004) ----------------------

def split_top_words(text: str, words: tuple[str, ...]) -> list[tuple[str, str]]:
    """Split ``text`` at top-level whitespace-delimited ``words``: [("", head), (word, piece), ...]."""
    pieces: list[tuple[str, list[str]]] = [("", [])]
    depth = 0
    for token in re.split(r"(\s+)", text):
        if token.strip() and depth == 0 and token in words:
            pieces.append((token, []))
            continue
        pieces[-1][1].append(token)
        depth += sum(token.count(c) for c in "([{") - sum(token.count(c) for c in ")]}")
    return [(word, "".join(parts).strip()) for word, parts in pieces]


def parse_sampling_clause(text: str) -> tuple[str, str, str, str]:
    """Split ``NAME from A to B [points N]`` into ``(name, a_text, b_text, n_text)``;
    ``n_text`` is ``""`` when ``points`` is omitted. Shared by spec 004's ``plot`` blocks'
    own ``over`` line and this module's ODE ``over`` line."""
    parts = split_top_words(text, _SAMPLING_WORDS)
    words = [w for w, _ in parts[1:]]
    head = parts[0][1]
    if words[:2] != ["from", "to"] or words not in (["from", "to"], ["from", "to", "points"]):
        raise StatementError(_SAMPLING_ERROR)
    if not _IDENT_RE.match(head):
        raise StatementError("over needs a name before 'from'")
    texts = [t for _, t in parts[1:]]
    if not all(texts):
        raise StatementError(_SAMPLING_ERROR)
    return head, texts[0], texts[1], (texts[2] if len(texts) > 2 else "")


# -- ODE systems: ``ode``/``start``/``over``/``evolve`` tagged regions (spec 010) --------

def parse_ode_equation(text: str) -> tuple[str, str, int, str, str]:
    """Split an ``ode`` line's equation text into ``(function, variable, order, lhs, rhs)``.

    The left side of the equation's single top-level ``==`` must *start* with a pure
    ``diff(F(X), X)`` or ``diff(F(X), X, N)`` term (the highest derivative being defined by
    this line); anything else on the left follows as an ordinary ``+``/``-`` addend. Raises
    ``StatementError`` with a clear message otherwise.
    """
    if text.count("==") != 1:
        raise StatementError(_ODE_SHAPE_ERROR)
    lhs, rhs = (part.strip() for part in text.split("=="))
    mt = _ODE_LHS_RE.match(lhs)
    if mt is None or mt.group(2) != mt.group(3) or not rhs:
        raise StatementError(_ODE_SHAPE_ERROR)
    tail = lhs[mt.end():].lstrip()
    if tail and tail[0] not in "+-":
        raise StatementError(_ODE_SHAPE_ERROR)
    order = int(mt.group(4)) if mt.group(4) else 1
    return mt.group(1), mt.group(2), order, lhs, rhs


def _parse_start(rest: str) -> list[tuple[str, int, str, str]]:
    conditions = []
    for part in _split_top_level(rest):
        part = part.strip()
        mt = _START_ITEM_RE.match(part)
        if mt is None:
            raise StatementError(_START_SHAPE_ERROR)
        conditions.append((mt.group(1), len(mt.group(2)), mt.group(3).strip(), mt.group(4).strip()))
    if not conditions:
        raise StatementError(_START_SHAPE_ERROR)
    return conditions


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
    if keyword == "ode":
        if not rest:
            raise StatementError(_ODE_SHAPE_ERROR)
        parse_ode_equation(rest)  # validate shape now; function/order/variable re-derived at solve time
        return Statement("model_ode", model=name, expr=rest)
    if keyword == "start":
        if not rest:
            raise StatementError(_START_SHAPE_ERROR)
        return Statement("model_ic", model=name, conditions=_parse_start(rest))
    if keyword == "over":
        if not rest:
            raise StatementError(_SAMPLING_ERROR)
        head, a_text, b_text, n_text = parse_sampling_clause(rest)
        return Statement("model_over", model=name, name=head, expr=a_text, range_end=b_text,
                         over_points=n_text)
    if keyword == "evolve":
        goal_word = rest.strip()
        if goal_word not in ("", "symbolic", "numeric"):
            raise StatementError("evolve takes 'symbolic', 'numeric' or nothing")
        goal = {"": "ode_auto", "symbolic": "ode_symbolic", "numeric": "ode_numeric"}[goal_word]
        return Statement("model_result", model=name, goal=goal)
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
