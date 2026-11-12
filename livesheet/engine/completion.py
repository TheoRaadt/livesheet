"""Name completion for math regions (spec 024). Qt-free: pure text in, candidates out.

Builtin names are read from ``evaluator.BUILTINS`` on every request, so a newly registered
function is offered without touching this module.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Iterable

from . import dataio, evaluator
from .syntax import parse_statement

MIN_PREFIX = 2
_HIDDEN = {"Integer", "Float", "Rational", "Symbol", "Function"}

# Hints for entries whose Python signature says nothing useful (mostly SymPy-backed ones).
SIGNATURE_OVERRIDES: dict[str, str] = {
    "sin": "sin(x)", "cos": "cos(x)", "tan": "tan(x)", "cot": "cot(x)", "sec": "sec(x)",
    "csc": "csc(x)", "asin": "asin(x)", "acos": "acos(x)", "atan": "atan(x)",
    "atan2": "atan2(y, x)", "sinh": "sinh(x)", "cosh": "cosh(x)", "tanh": "tanh(x)",
    "asinh": "asinh(x)", "acosh": "acosh(x)", "atanh": "atanh(x)",
    "exp": "exp(x)", "ln": "ln(x)", "sqrt": "sqrt(x)", "root": "root(x, n)",
    "abs": "abs(x)", "sign": "sign(x)", "floor": "floor(x)", "ceil": "ceil(x)",
    "mod": "mod(a, b)", "Max": "Max(a, b, ...)", "Min": "Min(a, b, ...)",
    "max": "max(a, b, ...)", "min": "min(a, b, ...)",
    "factorial": "factorial(n)", "binomial": "binomial(n, k)", "Gamma": "Gamma(x)",
    "re": "re(z)", "im": "im(z)", "conj": "conj(z)", "arg": "arg(z)",
    "diff": "diff(expr, x)", "integrate": "integrate(expr, (x, a, b))",
    "limit": "limit(expr, x, point)", "sum": "sum(expr, k, a, b)",
    "product": "product(expr, k, a, b)", "series": "series(expr, x, point, n)",
    "solve": "solve(eq, x)", "expand": "expand(expr)", "factor": "factor(expr)",
    "simplify": "simplify(expr)", "Eq": "Eq(left, right)",
}


@dataclass(frozen=True)
class Candidate:
    name: str
    kind: str            # function | constant | user_function | variable | data
    signature: str = ""


@dataclass(frozen=True)
class Completion:
    start: int
    prefix: str
    candidates: list[Candidate] = field(default_factory=list)


def _public(name: str) -> bool:
    return not name.startswith("_") and name not in _HIDDEN


def signature_for(name: str) -> str:
    if name in SIGNATURE_OVERRIDES:
        return SIGNATURE_OVERRIDES[name]
    fn = evaluator.BUILTINS.get(name)
    if fn is None or not callable(fn):
        return ""
    try:
        sig = inspect.signature(inspect.unwrap(fn))
    except (TypeError, ValueError):
        return ""
    parts = []
    for p in sig.parameters.values():
        label = p.name.rstrip("_") or p.name
        if p.kind is p.VAR_POSITIONAL:
            label = "*" + label
        elif p.kind is p.VAR_KEYWORD:
            label = "**" + label
        elif p.default is not p.empty:
            label = f"{label}={p.default}"
        parts.append(label)
    return f"{name}({', '.join(parts)})"


def builtin_candidates() -> list[Candidate]:
    return [Candidate(n, "function" if callable(f) else "constant", signature_for(n))
            for n, f in evaluator.BUILTINS.items() if _public(n)]


_USER_CACHE: dict[str, Candidate | None] = {}


def _user_candidate(source: str) -> Candidate | None:
    if source in _USER_CACHE:
        return _USER_CACHE[source]
    cand: Candidate | None = None
    try:
        st = parse_statement(source)
        if st.kind in ("define", "global") and st.name:
            if st.params:
                cand = Candidate(st.name, "user_function", f"{st.name}({', '.join(st.params)})")
            else:
                cand = Candidate(st.name, "variable")
        elif st.kind == "range" and st.name:
            cand = Candidate(st.name, "variable")
    except Exception:
        cand = None
    if len(_USER_CACHE) > 5000:
        _USER_CACHE.clear()
    _USER_CACHE[source] = cand
    return cand


def user_candidates(sources: Iterable[str]) -> list[Candidate]:
    seen: dict[str, Candidate] = {}
    for src in sources:
        c = _user_candidate(src)
        if c is not None and c.name not in seen:
            seen[c.name] = c
    return list(seen.values())


def dataset_candidates(datasets: Iterable[dataio.Dataset]) -> list[Candidate]:
    """Name candidates for imported datasets (spec 030 A). Metadata only, no matrices built."""
    out: list[Candidate] = []
    for ds in datasets:
        numbers = [c for c in ds.columns if c.kind == "number"]
        for col in numbers:
            hint = f"{len(col.values)} values" + (f", {col.unit}" if col.unit else "")
            out.append(Candidate(dataio.column_variable_name(ds, col), "data", hint))
        if dataio.combined_matrix_available(ds):
            rows = len(numbers[0].values)
            out.append(Candidate(ds.name, "data", f"{rows} x {len(numbers)} matrix"))
    return out


def _is_ident(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def run_start(text: str, caret: int) -> int:
    """Start of the identifier run that ends at ``caret`` (``caret`` itself when there is none)."""
    start = caret
    while start > 0 and _is_ident(text[start - 1]):
        start -= 1
    return start


def word_at(text: str, caret: int) -> tuple[int, str] | None:
    """The identifier run ending at ``caret`` if a popup is allowed for it (rules 1-3)."""
    if caret < 0 or caret > len(text):
        return None
    if caret < len(text) and _is_ident(text[caret]):
        return None
    start = caret
    while start > 0 and _is_ident(text[start - 1]):
        start -= 1
    run = text[start:caret]
    if len(run) < MIN_PREFIX or not (run[0].isalpha() or run[0] == "_"):
        return None
    if start > 0 and text[start - 1] == ".":
        return None
    return start, run


def complete(text: str, caret: int | None = None,
             user_sources: Iterable[str] = (),
             datasets: Iterable[dataio.Dataset] = ()) -> Completion | None:
    if caret is None:
        caret = len(text)
    word = word_at(text, caret)
    if word is None:
        return None
    start, prefix = word
    data: dict[str, Candidate] = {}
    for c in dataset_candidates(datasets):
        data.setdefault(c.name, c)
    users = [c for c in user_candidates(user_sources) if c.name not in data]
    taken = {c.name for c in users}
    pool = users + list(data.values()) + [
        c for c in builtin_candidates() if c.name not in taken and c.name not in data]
    low = prefix.lower()
    hits = [c for c in pool if c.name.lower().startswith(low)]
    if not hits or all(c.name == prefix for c in hits):
        return None

    def rank(c: Candidate):
        group = 0 if c.name in taken else 1 if c.name in data else 2
        return (not c.name.startswith(prefix), group, len(c.name), c.name)

    hits.sort(key=rank)
    return Completion(start, prefix, hits)


def accept(text: str, caret: int, candidate: Candidate) -> tuple[str, int]:
    start = run_start(text, caret)
    insert = candidate.name
    if candidate.kind in ("function", "user_function") and text[caret:caret + 1] != "(":
        insert += "("
    return text[:start] + insert + text[caret:], start + len(insert)
