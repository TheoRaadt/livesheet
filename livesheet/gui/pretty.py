"""Render math-region source as light HTML for display (not while editing)."""

from __future__ import annotations

import html
import re

from ..engine.formatting import GREEK

_SUP_RE = re.compile(r"\^\s*(\([^()]*\)|-?[\w.]+)")
_WORD_RE = re.compile(r"\b[A-Za-z]+\b")
_SUB_RE = re.compile(r"\b([^\W\d_]\w*?)_(\w+)\b")


def _greek(match: re.Match) -> str:
    word = match.group(0)
    if word == "pi":
        return "π"
    if word == "oo":
        return "∞"
    return GREEK.get(word, word)


def pretty_source_html(source: str) -> str:
    text = source.strip().replace("::=", "≡").replace("->", "→")
    # operator spacing on the raw text
    text = re.sub(r"\s*:=\s*", " := ", text)
    text = re.sub(r"\s*≡\s*", " ≡ ", text)
    text = re.sub(r"\s*→\s*", " → ", text)
    text = re.sub(r"\s*==\s*", " == ", text)
    text = re.sub(r"\s*(?<![:<>=!])=(?!=)\s*", " = ", text)
    text = html.escape(text.strip(), quote=False)
    text = _SUB_RE.sub(r"\1<sub>\2</sub>", text)
    text = _WORD_RE.sub(_greek, text)
    text = text.replace("sqrt(", "√(")
    text = _SUP_RE.sub(lambda m: "<sup>" + _strip_parens(m.group(1)) + "</sup>", text)
    text = text.replace("*", "·").replace("==", "<b>=</b>")
    text = text.replace("&lt;=", "≤").replace("&gt;=", "≥")
    # function-call calculus notation (diff(...)/integrate(...)); done last so EXPR has
    # already picked up the sup/sqrt/dot/Greek substitutions above.
    text = _prettify_calculus(text)
    return text


def _strip_parens(s: str) -> str:
    return s[1:-1] if s.startswith("(") and s.endswith(")") else s


_CALC_CALL_RE = re.compile(r"\b(diff|integrate)\(")


def _prettify_calculus(text: str) -> str:
    """Recognise ``diff(expr, var[, n])`` and ``integrate(expr, var)`` /
    ``integrate(expr, (var, a, b))`` call shapes and render them with standard
    calculus notation (``d/dx (...)``, ``∫ ... dx``) instead of the raw call text.

    Only the function-call forms are handled; the ``-> diff, x`` / ``-> integrate, x``
    postfix keyword forms are left untouched (see module docstring / spec note).
    Nested calls (e.g. ``integrate(diff(x^3, x), x)``) are handled by recursing into
    the EXPR argument before building the outer replacement, so it copes with simple
    nesting via balanced-parenthesis scanning rather than a flat regex.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        m = _CALC_CALL_RE.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        open_idx = m.end() - 1  # index of the '(' that opens this call
        close_idx = _matching_paren(text, open_idx)
        if close_idx is None:
            # Unbalanced parens (shouldn't happen for valid source) -- bail out and
            # keep the rest of the text as-is rather than risk mangling it.
            out.append(text[m.start():])
            break
        inner = text[open_idx + 1:close_idx]
        rendered = _render_calc_call(m.group(1), _split_top_level(inner))
        out.append(rendered if rendered is not None else text[m.start():close_idx + 1])
        i = close_idx + 1
    return "".join(out)


def _matching_paren(text: str, open_idx: int) -> int | None:
    """Index of the ``)`` that closes the ``(`` at ``open_idx``, or None if unbalanced."""
    depth = 0
    for idx in range(open_idx, len(text)):
        if text[idx] == "(":
            depth += 1
        elif text[idx] == ")":
            depth -= 1
            if depth == 0:
                return idx
    return None


def _split_top_level(s: str) -> list[str]:
    """Split ``s`` on commas that are not nested inside parentheses."""
    parts = []
    depth = 0
    current: list[str] = []
    for ch in s:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def _render_calc_call(name: str, args: list[str]) -> str | None:
    """Return the prettified HTML for a recognised ``diff``/``integrate`` call shape,
    or None if this arg count/shape isn't one we know how to render (caller then
    leaves the original call text untouched)."""
    if name == "diff":
        if len(args) == 2:
            expr, var = args
            return f"d/d{var} ({_prettify_calculus(expr)})"
        if len(args) == 3:
            expr, var, order = args
            return f"d<sup>{order}</sup>/d{var}<sup>{order}</sup> ({_prettify_calculus(expr)})"
        return None
    if name == "integrate":
        if len(args) == 2:
            expr, var_or_tuple = args
            expr = _prettify_calculus(expr)
            if var_or_tuple.startswith("(") and var_or_tuple.endswith(")"):
                bounds = _split_top_level(var_or_tuple[1:-1])
                if len(bounds) == 3:
                    var, a, b = bounds
                    return f"∫<sub>{a}</sub><sup>{b}</sup> {expr} d{var}"
                return None
            return f"∫ {expr} d{var_or_tuple}"
        return None
    return None


_EVAL_TAIL_RE = re.compile(r"(?<![<>=!:])=(?!=)[^=]*$")


def display_source(source: str) -> str:
    """Source text as shown next to its result (trailing ``=`` / bare ``→`` removed)."""
    text = source.rstrip()
    if text.endswith("->"):
        return text[:-2].rstrip()
    if text.endswith("→"):
        return text[:-1].rstrip()
    if "→" in text or "->" in text:
        return text
    return _EVAL_TAIL_RE.sub("", text).rstrip()
