"""The dockable side panel: a tabbed Symbols/Outline/Data shell (spec 007, phase G2).

``MATH_TOKENS`` is the single shared list of insertable math tokens read by both the Math
toolbar (``main_window.py``) and the Symbols tab below, so the two surfaces cannot drift apart.
Each entry is ``(category, label, token, tip)``; the Math toolbar iterates it in order (ignoring
category, to keep its current, unchanged button order); the Symbols tab groups entries by
category under small headers, in the fixed order Constants, Operators, Calculus, Statements.
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

MATH_TOKENS: list[tuple[str, str, str, str]] = [
    ("Statements", ":=", ":= ", "Definition"),
    ("Statements", "≡", "≡ ", "Global definition"),
    ("Statements", "=", " =", "Evaluate numerically"),
    ("Statements", "→", " → ", "Evaluate symbolically"),
    ("Operators", "√", "sqrt(", "Square root"),
    ("Operators", "ⁿ√", "root(", "Nth root: root(expr, n)"),
    ("Operators", "x²", "^2", "Square"),
    ("Constants", "π", "pi", "Pi"),
    ("Constants", "e", "e", "Euler's number"),
    ("Constants", "i", "I", "Imaginary unit"),
    ("Calculus", "d/dx", "diff(", "Derivative: diff(expr, x)"),
    ("Calculus", "∫", "integrate(", "Integral: integrate(expr, x) or (x, a, b)"),
]

CATEGORY_ORDER = ("Constants", "Operators", "Calculus", "Statements")

OUTLINE_PLACEHOLDER = "Document outline will appear here once headings are available."
DATA_PLACEHOLDER = "Imported datasets will appear here once available."


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
    """Dockable, tabbed side panel: Symbols (functional), Outline/Data (placeholder shells)."""

    def __init__(self, insert_token: Callable[[str], None], parent: QWidget | None = None):
        super().__init__("Side Panel", parent)
        self.setObjectName("side-panel-dock")
        self.setMinimumWidth(120)
        self.setMaximumWidth(320)
        self._insert_token = insert_token
        self.symbol_buttons: dict[str, QPushButton] = {}

        self.tabs = QTabWidget()
        self.tabs.setObjectName("side-panel-tabs")
        self.tabs.addTab(self._build_symbols_tab(), "Symbols")
        self.tabs.addTab(_build_placeholder_tab(OUTLINE_PLACEHOLDER), "Outline")
        self.tabs.addTab(_build_placeholder_tab(DATA_PLACEHOLDER), "Data")
        self.setWidget(self.tabs)

    def _build_symbols_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        for category in CATEGORY_ORDER:
            items = [t for t in MATH_TOKENS if t[0] == category]
            if not items:
                continue
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


__all__ = ["SidePanel", "MATH_TOKENS", "CATEGORY_ORDER", "OUTLINE_PLACEHOLDER", "DATA_PLACEHOLDER"]
