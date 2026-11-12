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
    surface                     first line of a 3-D surface spec (spec 031), same line form as plot
    plot                        first line of a plot spec; then ``over``/``show``/... lines
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .sampling import split_sampling

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
    conditions: list[tuple[str, int, str, str]] = field(default_factory=list)
    # model_ic: one 4-tuple per condition (function name, derivative order, point text, value text)
    over_points: str = ""        # model_over: the sampling count text (empty means the default)
    node: str = ""               # model_support/model_load: the node-index expression text
    axes: list[tuple[str, str]] = field(default_factory=list)
    # model_support/model_load: one (axis letter, value text or "") pair per fix/fx/fy item


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
    surface = _parse_plot(source, "surface")
    if surface is not None:
        return surface

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


_PLOT_TEXT_KEYWORDS = ("title", "xlabel", "ylabel", "zlabel")


def _parse_plot(source: str, header: str = "plot") -> Statement | None:
    """A text whose first non-blank line is exactly ``plot`` (or ``surface``, spec 031) is a
    plot spec (one option per line)."""
    lines = [ln.replace("\u00a0", " ").strip() for ln in source.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines or lines[0] != header:
        return None
    parsed: list[tuple[str, str]] = []
    for line in lines[1:]:
        word, _, rest = line.partition(" ")
        rest = rest.strip()
        parsed.append((word, rest if word in _PLOT_TEXT_KEYWORDS else normalize(rest).strip()))
    return Statement(header, plot_lines=parsed)


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

_TRUSS_EXPR_KEYWORDS = {
    "nodes": "model_truss_nodes", "elements": "model_truss_elements",
    "area": "model_truss_area", "modulus": "model_truss_modulus",
}


def _parse_model(text: str) -> Statement | None:
    mt = _MODEL_TAG_RE.match(text)
    if mt is None:
        return None
    body, name = mt.group(1).strip(), mt.group(2)
    word = re.match(r"^(\w+)", body)
    keyword = word.group(1) if word else ""
    if any(op in body for op in _STATEMENT_OPS):
        return None  # an ordinary statement that happens to end in `in <word>`
    # ``support``'s own grammar legitimately contains a bare ``=`` (``x = <value>``),
    # unlike every other model keyword, so it alone is exempt from this specific bare-``=``
    # check (not the ``_STATEMENT_OPS`` check above, which still applies to every keyword).
    if keyword != "support" and _split_eval(body) is not None:
        return None  # an ordinary statement that happens to end in `in <word>`
    rest = body[len(keyword):].strip() if keyword else body
    if keyword in _TRUSS_EXPR_KEYWORDS:
        if not rest:
            raise StatementError(f'"{keyword}" needs an expression')
        return Statement(_TRUSS_EXPR_KEYWORDS[keyword], model=name, expr=rest)
    stats = _parse_stats_keyword(keyword, body, rest, name)
    if stats is not None:
        return stats
    if keyword == "support":
        return _parse_support(rest, name)
    if keyword == "load":
        return _parse_load(rest, name)
    if keyword == "resolve":
        if rest:
            raise StatementError("resolve takes no expression")
        return Statement("model_result", model=name, goal="truss")
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
            raise StatementError("ode needs an equation")
        split_ode_equation(rest)   # validates shape only; the full text is re-parsed at solve time
        return Statement("model_ode", model=name, expr=rest)
    if keyword == "start":
        if not rest:
            raise StatementError('Use "start f(point) == value" (optionally f\'(point) == ..., ...)')
        return Statement("model_ic", model=name, conditions=_parse_conditions(rest))
    if keyword == "over":
        parsed = split_sampling(rest) if rest else None
        if parsed is None:
            raise StatementError("over needs 'NAME from A to B [points N]'")
        head, start_text, end_text, points_text = parsed
        return Statement("model_over", model=name, name=head, expr=start_text,
                         range_end=end_text, over_points=points_text)
    if keyword == "evolve":
        goal_word = rest.strip()
        if goal_word == "":
            goal = "ode_auto"
        elif goal_word == "symbolic":
            goal = "ode_symbolic"
        elif goal_word == "numeric":
            goal = "ode_numeric"
        else:
            raise StatementError("evolve takes 'symbolic', 'numeric' or nothing")
        return Statement("model_result", model=name, goal=goal)
    relations = _split_relations(body)
    if relations is None:
        raise StatementError('A relation is required before "in ' + name + '"')
    return Statement("model_require", model=name, relations=relations)


_STATS_EXPR_KEYWORDS = {"sample": "model_sample", "expected": "model_expected",
                        "claim": "model_claim"}


def _parse_stats_keyword(keyword: str, body: str, rest: str, name: str) -> Statement | None:
    """Hypothesis-test lines (spec 017 S2): sample / expected / claim / level / verdict."""
    if keyword == "verdict" and body == "verdict":
        return Statement("model_result", model=name, goal="hypothesis_test")
    if keyword == "verdict" and body[7:8] in (" ", "[", "("):
        raise StatementError("verdict takes no expression")
    if keyword not in (*_STATS_EXPR_KEYWORDS, "level"):
        return None
    if body[len(keyword):len(keyword) + 1] not in (" ", "[", "("):
        return None  # e.g. ``sample2 in g`` is not this keyword
    if keyword == "level":
        return Statement("model_setting", model=name, name="level", expr=rest)
    return Statement(_STATS_EXPR_KEYWORDS[keyword], model=name, expr=rest)


_SUPPORT_SPLIT_RE = re.compile(r"^(.+?)\s+fix\b(.*)$", re.DOTALL)
_SUPPORT_ITEM_RE = re.compile(r"^(x|y)(?:\s*=\s*(.+))?$", re.DOTALL)
_SUPPORT_ERROR = 'Use "support <node> fix x, y" (optionally "x = <value>")'

_LOAD_SPLIT_RE = re.compile(r"\b(?:fx|fy)\b")
_LOAD_ITEM_RE = re.compile(r"^(fx|fy)\s+(.+)$", re.DOTALL)
_LOAD_ERROR = 'Use "load <node> fx <value>, fy <value>" (either or both)'


def _parse_axis_items(items_text: str, item_re: re.Pattern, error: str) -> list[tuple[str, str]]:
    """Split a comma-separated list of ``x``/``y`` (support) or ``fx``/``fy`` (load) items,
    shared by ``model_support`` and ``model_load``; ``item_re`` fixes the accepted shape and
    whether a value is required. The axis letter in the returned pairs is always ``x``/``y``."""
    axes: list[tuple[str, str]] = []
    for part in _split_top_level(items_text):
        part = part.strip()
        mt = item_re.match(part)
        if mt is None:
            raise StatementError(error)
        axis = mt.group(1)
        axis = axis[1] if len(axis) == 2 else axis   # fx/fy -> x/y
        value = (mt.group(2) or "").strip()
        axes.append((axis, value))
    if not axes:
        raise StatementError(error)
    return axes


def _parse_support(rest: str, name: str) -> Statement:
    mt = _SUPPORT_SPLIT_RE.match(rest)
    if mt is None or not mt.group(1).strip():
        raise StatementError(_SUPPORT_ERROR)
    node_text, items_text = mt.group(1).strip(), mt.group(2).strip()
    axes = _parse_axis_items(items_text, _SUPPORT_ITEM_RE, _SUPPORT_ERROR)
    return Statement("model_support", model=name, node=node_text, axes=axes)


def _parse_load(rest: str, name: str) -> Statement:
    mt = _LOAD_SPLIT_RE.search(rest)
    if mt is None or not rest[:mt.start()].strip():
        raise StatementError(_LOAD_ERROR)
    node_text, items_text = rest[:mt.start()].strip(), rest[mt.start():].strip()
    axes = _parse_axis_items(items_text, _LOAD_ITEM_RE, _LOAD_ERROR)
    seen: set[str] = set()
    for axis, _value in axes:
        if axis in seen:
            raise StatementError('"fx"/"fy" given twice on one load line')
        seen.add(axis)
    return Statement("model_load", model=name, node=node_text, axes=axes)


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


# -- ODE systems: ``ode``/``start``/``over``/``evolve`` lines (spec 010) -----------------

_ODE_PREFIX_RE = re.compile(
    rf"^diff\(\s*({_IDENT})\(\s*({_IDENT})\s*\)\s*,\s*({_IDENT})\s*(?:,\s*(\d+)\s*)?\)"
)
_START_ITEM_RE = re.compile(rf"^({_IDENT})('*)\(\s*(.+?)\s*\)\s*==\s*(.+)$", re.DOTALL)
_ODE_SHAPE_ERROR = "Write the highest derivative alone on the left: diff(name(t), t[, n]) == ..."


def _split_top_equation(text: str) -> tuple[str, str] | None:
    """Split ``text`` at its one top-level ``==``; ``None`` when there isn't exactly one."""
    depth, i, found = 0, 0, []
    while i < len(text):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and text[i:i + 2] == "==":
            found.append(i)
            i += 2
            continue
        i += 1
    if len(found) != 1:
        return None
    pos = found[0]
    return text[:pos].strip(), text[pos + 2:].strip()


def split_ode_equation(text: str) -> tuple[str, str, int]:
    """Validate and read an ``ode`` line's equation text (before the trailing ``in <name>``
    tag): (function name, independent-variable name, order). The derivative term must start
    the left side (it may be followed by other additive terms, as the worked examples show);
    raises on any other shape."""
    parts = _split_top_equation(text)
    if parts is None:
        raise StatementError(_ODE_SHAPE_ERROR)
    lhs, _rhs = parts
    mt = _ODE_PREFIX_RE.match(lhs)
    if mt is None:
        raise StatementError(_ODE_SHAPE_ERROR)
    func_name, func_var, indep_name, order_text = mt.groups()
    if func_var != indep_name:
        raise StatementError(_ODE_SHAPE_ERROR)
    return func_name, indep_name, int(order_text) if order_text else 1


def _parse_conditions(rest: str) -> list[tuple[str, int, str, str]]:
    conditions = []
    for item in _split_top_level(rest):
        item = item.strip()
        mt = _START_ITEM_RE.match(item)
        if mt is None:
            raise StatementError('Use "start f(point) == value" (optionally f\'(point) == ..., ...)')
        name, primes, point, value = mt.groups()
        conditions.append((name, len(primes), point.strip(), value.strip()))
    if not conditions:
        raise StatementError('Use "start f(point) == value" (optionally f\'(point) == ..., ...)')
    return conditions


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
