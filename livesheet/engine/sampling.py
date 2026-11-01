"""Shared ``NAME from A to B [points N]`` sampling-range text-splitting.

Spec 004's own ``over`` line (inside a ``plot`` block) and spec 010's own ``over``
line (an ODE system's reporting grid) use the identical shape; this tiny module
holds just the shared splitting so neither duplicates the same regex. No engine
imports here (kept dependency-free to avoid any import cycle between ``syntax.py``
and ``plotting.py``); each caller raises its own error text on a ``None`` result.
"""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"^[^\W\d]\w*$")


def split_top(text: str, words: tuple[str, ...]) -> list[tuple[str, str]]:
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


def split_sampling(text: str) -> tuple[str, str, str, str] | None:
    """Split ``NAME from A to B [points N]`` into (name, start_text, end_text, points_text);
    ``None`` when ``text`` does not have this shape (the caller raises its own error)."""
    parts = split_top(text, ("from", "to", "points"))
    words = [w for w, _ in parts[1:]]
    head = parts[0][1]
    if words[:2] != ["from", "to"] or words not in (["from", "to"], ["from", "to", "points"]):
        return None
    if not _IDENT_RE.match(head):
        return None
    texts = [t for _, t in parts[1:]]
    if not all(texts):
        return None
    return head, texts[0], texts[1], (texts[2] if len(texts) > 2 else "")
