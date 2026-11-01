"""Page geometry and the evaluation-order key (spec 021). Qt-free and SymPy-free.

A sheet is one continuous page unless it carries page breaks (y-coordinates). Regions are
evaluated page by page; within a page, left to right and then top to bottom.
"""

from __future__ import annotations

from typing import Sequence

__all__ = ["PAGE_WIDTH", "PAGE_HEIGHT", "GRID_UNIT", "page_index", "order_key"]

PAGE_WIDTH = 820      # scene units; width of the printable A4 area
PAGE_HEIGHT = 1220    # scene units; printable A4 height snapped to the grid
GRID_UNIT = 10        # ordering quantum; equals the canvas grid


def page_index(y: float, breaks: Sequence[float]) -> int:
    """0-based page number of anchor ``y``: the number of breaks ``b`` with ``b <= y``."""
    return sum(1 for b in breaks if b <= y)


def order_key(x: float, y: float, breaks: Sequence[float] = ()) -> tuple[int, int, int]:
    """Evaluation-order key ``(page, grid x, grid y)``: page first, then left to right, then
    top to bottom, with positions snapped to the ordering grid to avoid float-noise ties."""
    return (page_index(y, breaks), round(x / GRID_UNIT), round(y / GRID_UNIT))
