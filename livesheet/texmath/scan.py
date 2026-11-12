"""Finds ``$...$`` and ``$$...$$`` formula spans in plain text (Qt-free).

The scan is a single left-to-right pass without nesting. Offsets are indices into the plain text
passed in (paragraph breaks count as ``\\n``), so they equal text-cursor positions of the
document the text came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_SPAN_CHARS = 2000
MAX_SPANS = 200


@dataclass(frozen=True)
class Span:
    start: int           # offset of the opening delimiter
    end: int             # offset just after the closing delimiter
    source: str          # formula text between the delimiters
    display: bool        # True for $$...$$
    too_long: bool = False

    @property
    def delim(self) -> int:
        return 2 if self.display else 1

    @property
    def src_start(self) -> int:
        return self.start + self.delim

    @property
    def src_end(self) -> int:
        return self.end - self.delim


@dataclass
class ScanResult:
    spans: list[Span] = field(default_factory=list)
    escapes: list[int] = field(default_factory=list)   # offsets of the backslash in "\$" outside math
    overflow: bool = False                              # more than MAX_SPANS spans were found


def _is_space(ch: str) -> bool:
    return ch.isspace()


def _find_display_close(text: str, i: int) -> int:
    """Offset of the closing ``$$`` for a display span opened at ``i``, or -1."""
    n = len(text)
    j = i + 2
    while j < n:
        if text[j] == "\\":
            j += 2
            continue
        if text.startswith("$$", j):
            return j
        j += 1
    return -1


def _find_inline_close(text: str, i: int) -> int:
    """Offset of the closing ``$`` for an inline span opened at ``i``, or -1."""
    n = len(text)
    j = i + 1
    while j < n:
        c = text[j]
        if c == "\n":
            return -1
        if c == "\\" and j + 1 < n and text[j + 1] != "\n":
            j += 2
            continue
        if c == "$" and not _is_space(text[j - 1]) and not (j + 1 < n and text[j + 1].isdigit()):
            return j
        j += 1
    return -1


def scan(text: str) -> ScanResult:
    """Return the formula spans and escaped dollar signs of ``text``."""
    result = ScanResult()
    n = len(text)
    i = 0
    # A failed closer search covers everything after the opener, so later openers cannot
    # succeed either: remember it to keep the scan linear.
    no_display_close = False
    inline_dead_until = -1
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n and text[i + 1] == "$":
            result.escapes.append(i)
            i += 2
            continue
        if c != "$":
            i += 1
            continue
        if text.startswith("$$", i):
            j = -1 if no_display_close else _find_display_close(text, i)
            if j < 0:
                no_display_close = True
                i += 2
                continue
            src = text[i + 2:j]
            end = j + 2
            display = True
        else:
            if i + 1 >= n or _is_space(text[i + 1]):
                i += 1
                continue
            j = -1 if i < inline_dead_until else _find_inline_close(text, i)
            if j < 0:
                if i >= inline_dead_until:
                    nl = text.find("\n", i)
                    inline_dead_until = n if nl < 0 else nl
                i += 1
                continue
            src = text[i + 1:j]
            end = j + 1
            display = False
        if not src.strip():
            i = end
            continue
        if len(result.spans) >= MAX_SPANS:
            result.overflow = True
            break
        result.spans.append(Span(i, end, src, display, len(src) > MAX_SPAN_CHARS))
        i = end
    return result


def display_text(text: str, result: ScanResult | None = None) -> str:
    """``text`` with the backslash of every escaped dollar sign removed (display state)."""
    result = result if result is not None else scan(text)
    drop = set(result.escapes)
    return "".join(ch for k, ch in enumerate(text) if k not in drop)
