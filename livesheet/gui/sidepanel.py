"""The dockable side panel: a tabbed Elements/Algebra/Calculus/Statistics/Optimization/
Outline/Data shell (spec 007 phase G2; restructured into 7 category tabs by spec 011).

``MATH_TOKENS`` is the single list of insertable math tokens -- same ``(category, label, token,
tip)`` shape spec 007 shipped, now also carrying the 33 new Greek-letter entries (read straight
from ``engine/formatting.py``'s own ``GREEK`` dict, so the glyph/name list cannot drift from the
display-side mapping) and the 1 new Subscript entry. ``TAB_CATEGORIES`` maps each of the three
functional tabs to the ``MATH_TOKENS`` categories it shows; only a tab backed by more than one
category (today: Elements) keeps the small grey sub-header labels the old Symbols tab used.
``PLACEHOLDER_TABS`` gives the four non-functional tabs' messages, in ``TAB_ORDER``.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..engine.formatting import GREEK

# 23 lowercase + 10 uppercase buttons, in the dict's own (Greek-alphabet) insertion order; the
# "lamda"/"lambda" alias pair collapses to one button (spelled "lambda"); lowercase "pi" is not
# a GREEK key at all (it is already the Constants tab's own "pi" button).
_GREEK_LOWER = [(name, glyph) for name, glyph in GREEK.items() if name.islower() and name != "lamda"]
_GREEK_UPPER = [(name, glyph) for name, glyph in GREEK.items() if not name.islower()]

MATH_TOKENS: list[tuple[str, str, str, str]] = [
    ("Statements", ":=", ":= ", "Definition"),
    ("Statements", "≡", "≡ ", "Global definition"),
    ("Statements", "=", " =", "Evaluate numerically"),
    ("Statements", "→", " → ", "Evaluate symbolically"),
    ("Constants", "π", "pi", "Pi"),
    ("Constants", "e", "e", "Euler's number"),
    ("Constants", "i", "I", "Imaginary unit"),
    *[("Greek letters", glyph, name, name) for name, glyph in _GREEK_LOWER + _GREEK_UPPER],
    ("Algebra", "√", "sqrt(", "Square root"),
    ("Algebra", "ⁿ√", "root(", "Nth root: root(expr, n)"),
    ("Algebra", "x²", "^2", "Square"),
    ("Algebra", "xₙ", "_", "Subscript"),
    ("Calculus", "d/dx", "diff(", "Derivative: diff(expr, x)"),
    ("Calculus", "∫", "integrate(", "Integral: integrate(expr, x) or (x, a, b)"),
]

# Each functional tab's MATH_TOKENS categories, in display order; a tab listing more than one
# category keeps sub-headers (today, only Elements bundles three originally distinct groups).
TAB_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Elements": ("Statements", "Constants", "Greek letters"),
    "Algebra": ("Algebra",),
    "Calculus": ("Calculus",),
}

STATISTICS_PLACEHOLDER = ("Statistical tools (descriptive statistics, distributions, hypothesis "
                          "tests, regression) will appear here once available.")
OPTIMIZATION_PLACEHOLDER = ("Optimization tools (nonlinear and constrained optimization) will "
                            "appear here once available.")
OUTLINE_PLACEHOLDER = "Document outline will appear here once headings are available."
DATA_PLACEHOLDER = "Imported datasets will appear here once available."

PLACEHOLDER_TABS: dict[str, str] = {
    "Statistics": STATISTICS_PLACEHOLDER,
    "Optimization": OPTIMIZATION_PLACEHOLDER,
    "Outline": OUTLINE_PLACEHOLDER,
    "Data": DATA_PLACEHOLDER,
}

TAB_ORDER: tuple[str, ...] = (
    "Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Outline", "Data",
)


def _build_placeholder_tab(message: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(message)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    label.setStyleSheet("color: #9a9a9a;")
    layout.addWidget(label)
    return widget


class SidePanel(QDockWidget):
    """Dockable, tabbed side panel: Elements/Algebra/Calculus (functional), Statistics/
    Optimization/Outline/Data (placeholder shells)."""

    def __init__(self, insert_token: Callable[[str], None], parent: QWidget | None = None):
        super().__init__("Side Panel", parent)
        self.setObjectName("side-panel-dock")
        self.setMinimumWidth(120)
        self.setMaximumWidth(320)
        self._insert_token = insert_token
        self.symbol_buttons: dict[str, QPushButton] = {}

        self.tabs = QTabWidget()
        self.tabs.setObjectName("side-panel-tabs")
        for name in TAB_ORDER:
            if name in TAB_CATEGORIES:
                self.tabs.addTab(self._build_functional_tab(TAB_CATEGORIES[name]), name)
            else:
                self.tabs.addTab(_build_placeholder_tab(PLACEHOLDER_TABS[name]), name)
        self.setWidget(self.tabs)

    def _build_functional_tab(self, categories: tuple[str, ...]) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        show_headers = len(categories) > 1
        for category in categories:
            items = [t for t in MATH_TOKENS if t[0] == category]
            if not items:
                continue
            if show_headers:
                header = QLabel(category)
                header.setStyleSheet("color: #7a7a7a; font-weight: bold; font-size: 11px;")
                layout.addWidget(header)
            for _category, label, token, tip in items:
                btn = QPushButton(label)
                btn.setStyleSheet(
                    "QPushButton { border: 1px solid rgba(128, 128, 128, 110);"
                    " border-radius: 4px; padding: 3px 6px; }"
                    "QPushButton:hover { border-color: rgba(128, 128, 128, 180); }"
                )
                btn.setToolTip(tip)
                btn.clicked.connect(lambda _checked=False, t=token: self._insert_token(t))
                layout.addWidget(btn)
                self.symbol_buttons[label] = btn
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        return scroll


__all__ = [
    "SidePanel", "MATH_TOKENS", "TAB_CATEGORIES", "TAB_ORDER", "PLACEHOLDER_TABS",
    "OUTLINE_PLACEHOLDER", "DATA_PLACEHOLDER", "STATISTICS_PLACEHOLDER", "OPTIMIZATION_PLACEHOLDER",
]
