"""Qt-free input rules for math regions (kept separate so they can be tested without a GUI)."""

from __future__ import annotations


def colon_edit(before: str) -> tuple[int, str]:
    """What typing ``:`` does after ``before``: ``(characters to delete, text to insert)``.

    Inside open brackets a colon is a slice marker (``A[1, :]``); a colon right after a
    just-typed ``:=`` turns it into a global definition ``≡``; otherwise ``:`` becomes ``:=``.
    """
    if before.count("[") > before.count("]"):
        return 0, ":"
    if before.endswith(":= "):
        return 3, "≡ "
    if before.endswith(":=") or before.endswith("::"):
        return 2, "≡ "
    if before.endswith(":"):
        return 1, "≡ "
    return 0, ":= "
