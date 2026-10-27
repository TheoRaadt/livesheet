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
    return text


def _strip_parens(s: str) -> str:
    return s[1:-1] if s.startswith("(") and s.endswith(")") else s


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
