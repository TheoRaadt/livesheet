"""Errors raised by the LaTeX-subset scanner and parser (Qt-free)."""

from __future__ import annotations


class TexError(Exception):
    """A formula cannot be typeset. ``offset`` is a 0-based character offset inside the
    formula source (without the ``$`` delimiters)."""

    def __init__(self, message: str, offset: int = 0):
        super().__init__(message)
        self.message = message
        self.offset = max(0, int(offset))

    def __str__(self) -> str:
        return self.message
