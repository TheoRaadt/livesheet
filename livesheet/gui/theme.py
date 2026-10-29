"""Application-level theming (spec 007, phase G3).

Three modes: "system" (follow the OS-level light/dark preference), "light", "dark". Only the
standard, toolkit-drawn chrome (menus, toolbars, dialogs, the status bar, scrollbars) is restyled
here, via a plain ``QPalette`` applied to the whole ``QApplication`` -- nothing the canvas paints
itself (grid, region borders, crosshair, plot colours) is touched, by design (see spec 007, open
question 3).
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

MODE_SYSTEM = "system"
MODE_LIGHT = "light"
MODE_DARK = "dark"
MODES = (MODE_SYSTEM, MODE_LIGHT, MODE_DARK)


def light_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Text, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(220, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(50, 110, 200))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return palette


def dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 32))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 64))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.Text, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 58))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 90, 90))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(70, 130, 220))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return palette


def detect_system_scheme(app: QApplication | None = None) -> str:
    """Read the OS-level light/dark preference via Qt's own style hints."""
    app = app or QApplication.instance()
    if app is None:
        return MODE_LIGHT
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return MODE_DARK
    return MODE_LIGHT


def apply_theme(
    app: QApplication,
    mode: str,
    scheme_reader: Callable[[QApplication | None], str] = detect_system_scheme,
) -> None:
    """Apply the light/dark/follow-system palette to the whole running application.

    ``scheme_reader`` defaults to the real OS reader (``detect_system_scheme``); tests exercise
    the "Follow System" branch headless by passing a stubbed/injected reader instead of touching
    the real OS colour scheme (the offscreen QPA platform used in CI does not reliably honour
    ``QStyleHints.setColorScheme()``, so a real OS call cannot be driven from a test anyway).
    """
    resolved = scheme_reader(app) if mode == MODE_SYSTEM else mode
    app.setPalette(dark_palette() if resolved == MODE_DARK else light_palette())


__all__ = ["MODE_SYSTEM", "MODE_LIGHT", "MODE_DARK", "MODES",
           "light_palette", "dark_palette", "detect_system_scheme", "apply_theme"]
