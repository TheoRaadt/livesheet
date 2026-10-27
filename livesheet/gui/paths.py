"""Qt-free default locations for the Save As and Export PDF dialogs."""

from __future__ import annotations

from pathlib import Path


def safe_dir(last_dir: str | None, documents: Path) -> Path:
    """Folder the dialogs start in: the last used one, never an ``examples`` folder."""
    if last_dir:
        folder = Path(last_dir)
        if folder.is_dir() and "examples" not in folder.parts:
            return folder
    return documents


def default_save_path(current: Path | None, last_dir: str | None, documents: Path, suffix: str) -> Path:
    """Suggested file for a save dialog; it never names an existing file."""
    folder = safe_dir(last_dir, documents)
    stem = current.stem if current else "Untitled"
    candidate = folder / (stem + suffix)
    n = 1
    while candidate.exists():
        n += 1
        candidate = folder / f"{stem} copy{'' if n == 2 else ' ' + str(n - 1)}{suffix}"
    return candidate


def remembered_dir(saved: Path) -> str | None:
    """Folder to remember after saving ``saved`` (``None`` for an examples folder)."""
    parent = saved.parent
    return None if "examples" in parent.parts else str(parent)
