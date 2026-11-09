"""Size and layout rules for the Standard toolbar (spec 025)."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QAction, QFont, QFontMetrics, QKeySequence
from PySide6.QtWidgets import QApplication, QToolBar, QToolButton

HYSTERESIS = 24
BASE_ICON = 20


def icon_edge(line_height: int) -> int:
    """Icon edge: 20 px at a 15 px line height, scaled with the font, even, within 20..32."""
    raw = round(BASE_ICON * line_height / 15)
    return max(20, min(32, (raw // 2) * 2))


def tab_button_height() -> int:
    """The tab strip button height (bold line height + 12), as spec 022 computes it."""
    font = QFont(QApplication.font())
    font.setBold(True)
    return QFontMetrics(font).height() + 12


def button_height() -> int:
    return max(32, tab_button_height() + 4)


class ToolbarStyler(QObject):
    """Gives a QToolBar icon+label buttons that fall back to icon-only when space runs out."""

    def __init__(self, toolbar: QToolBar, labels: dict[QAction, str]):
        super().__init__(toolbar)
        self.toolbar = toolbar
        self.labels = labels
        self._wide = True
        self._sum = 0
        for act, label in labels.items():
            act.setIconText(label)
            act.setIconVisibleInMenu(False)
        toolbar.installEventFilter(self)
        if toolbar.parentWidget() is not None:
            toolbar.parentWidget().installEventFilter(self)   # window resizes drive the style
        toolbar.orientationChanged.connect(lambda _o: self.update_style())
        app = QApplication.instance()
        if app is not None and hasattr(app, "fontChanged"):   # Qt >= 6.5
            app.fontChanged.connect(lambda _f: self.refresh())
        self.refresh()

    # -- metrics -----------------------------------------------------------------

    def refresh(self) -> None:
        """Recompute icon size, button size, tooltips and the wide/narrow threshold."""
        tb = self.toolbar
        edge = icon_edge(QFontMetrics(QApplication.font()).height())
        tb.setIconSize(QSize(edge, edge))
        h = button_height()
        tb.setStyleSheet(
            "QToolBar { spacing: 4px; }"
            "QToolBar QToolButton { border: 1px solid transparent; border-radius: 4px;"
            f" padding: 0px 10px; min-height: {h - 2}px; }}"
            "QToolBar QToolButton:hover { border-color: rgba(128, 128, 128, 110); }"
            "QToolBar QToolButton:pressed { background: rgba(128, 128, 128, 60); }"
            "QToolBar QToolButton:focus { border: 1px dotted palette(window-text); }"
        )
        for act, label in self.labels.items():
            keys = act.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            act.setToolTip(f"{label} ({keys})" if keys else label)
            btn = tb.widgetForAction(act)
            if btn is not None:
                btn.setAccessibleName(label)
        self._wide = True
        self._sum = self._wide_width()
        self.update_style()

    def _wide_width(self) -> int:
        """Width of the TextBesideIcon layout, from real size hints."""
        tb = self.toolbar
        old = tb.toolButtonStyle()
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        total = 0
        count = 0
        for act in tb.actions():
            w = tb.widgetForAction(act)
            if w is None:
                continue
            w.ensurePolished()
            total += w.sizeHint().width()
            count += 1
        tb.setToolButtonStyle(old)
        lay = tb.layout()
        margins = lay.contentsMargins() if lay is not None else None
        spacing = max(lay.spacing(), 4) if lay is not None else 4
        total += spacing * max(count - 1, 0)
        if margins is not None:
            total += margins.left() + margins.right()
        return total + 8   # handle / frame slack

    @property
    def wide_width(self) -> int:
        return self._sum

    def update_style(self) -> None:
        tb = self.toolbar
        if tb.orientation() == Qt.Orientation.Vertical:
            self._wide = False
        else:
            avail = self._available_width()
            if self._wide and avail < self._sum:
                self._wide = False
            elif not self._wide and avail >= self._sum + HYSTERESIS:
                self._wide = True
        style = (Qt.ToolButtonStyle.ToolButtonTextBesideIcon if self._wide
                 else Qt.ToolButtonStyle.ToolButtonIconOnly)
        if tb.toolButtonStyle() != style:
            tb.setToolButtonStyle(style)

    def _available_width(self) -> int:
        """Room for the toolbar: the window's width (the toolbar itself shrinks to its hint)."""
        win = self.toolbar.window()
        if win is not None and win is not self.toolbar and not self.toolbar.isFloating():
            return win.width()
        return self.toolbar.width()

    def buttons(self) -> list[QToolButton]:
        return [b for a in self.toolbar.actions()
                if isinstance(b := self.toolbar.widgetForAction(a), QToolButton)]

    # -- events ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        t = event.type()
        if t in (QEvent.Type.FontChange, QEvent.Type.ApplicationFontChange,
                 QEvent.Type.PaletteChange):
            if t != QEvent.Type.PaletteChange:
                self.refresh()
        elif t in (QEvent.Type.Resize, QEvent.Type.Show):
            self.update_style()
        return False
