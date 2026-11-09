"""Spec 025: larger Standard toolbar (icons, size rule, narrow-width tiers)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import QApplication, QToolButton

from livesheet.gui.icons import GLYPH_NAMES, glyph_icon, render_glyph
from livesheet.gui.main_window import MainWindow
from livesheet.gui.toolbarstyle import button_height, icon_edge, tab_button_height

TBS = Qt.ToolButtonStyle


class _Wait:
    @staticmethod
    def wait(ms):
        QTest.qWait(ms)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module", autouse=True)
def isolated_settings(tmp_path_factory, app):
    """Keep MainWindow's QSettings out of the user's real preferences."""
    old_fmt = QSettings.defaultFormat()
    d = tmp_path_factory.mktemp("qsettings025b")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(d))
    yield
    QSettings.setDefaultFormat(old_fmt)


@pytest.fixture
def qtbot(app):
    return _Wait()


@pytest.fixture
def win(app):
    w = MainWindow()
    # a previously saved layout may have the toolbar elsewhere; the tests need it on top
    w.addToolBar(Qt.ToolBarArea.TopToolBarArea, w.standard_toolbar)
    w.show()
    QApplication.processEvents()
    yield w
    w.addToolBar(Qt.ToolBarArea.TopToolBarArea, w.standard_toolbar)   # do not persist a test layout
    w.close()


def acts(w):
    return [w.action_new, w.action_open, w.action_save, w.action_export_pdf, w.action_recalculate]


def buttons(w):
    return [b for a in acts(w) if isinstance(b := w.standard_toolbar.widgetForAction(a), QToolButton)]


def at_width(w, qtbot, width):
    w.resize(width, 700)
    qtbot.wait(20)
    QApplication.processEvents()


def test_icons_and_sizes(win):
    tb = win.standard_toolbar
    for a in acts(win):
        assert not a.icon().isNull()
        assert not a.isIconVisibleInMenu()
    edge = icon_edge(QFontMetrics(QApplication.font()).height())
    assert tb.iconSize() == QSize(edge, edge)
    assert icon_edge(15) == 20 and icon_edge(19) == 24 and icon_edge(100) == 32 and icon_edge(5) == 20
    for b in buttons(win):
        assert b.sizeHint().height() >= 32
        assert b.sizeHint().height() >= tab_button_height() + 4
    assert win.toolbar_styler.buttons()[0].sizeHint().height() >= button_height()


def test_taller_than_band_buttons(win):
    from PySide6.QtWidgets import QPushButton
    band = [b.sizeHint().height() for b in win.side_panel.findChildren(QPushButton)]
    assert band
    for b in buttons(win):
        assert b.sizeHint().height() > max(band)


def test_font_growth_resizes_icons(win, qtbot):
    old = QApplication.font()
    try:
        f = QFont(old)
        f.setPixelSize(15)
        QApplication.setFont(f)
        qtbot.wait(20)
        small = win.standard_toolbar.iconSize().width()
        f.setPixelSize(30)
        QApplication.setFont(f)
        qtbot.wait(20)
        assert win.standard_toolbar.iconSize().width() > small
    finally:
        QApplication.setFont(old)


def test_wide_layout(win, qtbot):
    at_width(win, qtbot, 1000)
    tb = win.standard_toolbar
    assert tb.toolButtonStyle() == TBS.ToolButtonTextBesideIcon
    for b in buttons(win):
        assert b.isVisible()
        assert tb.rect().contains(b.geometry())
        assert b.text() in ("New", "Open", "Save", "Export PDF", "Recalculate")


def test_narrow_layout_tooltips(win, qtbot):
    at_width(win, qtbot, 1000)
    min_before = win.minimumWidth()
    total = win.toolbar_styler.wide_width
    at_width(win, qtbot, max(total - 80, win.minimumSizeHint().width()))
    tb = win.standard_toolbar
    if tb.width() >= total:
        pytest.skip("window cannot get narrower than the toolbar's wide width")
    assert tb.toolButtonStyle() == TBS.ToolButtonIconOnly
    labels = ["New", "Open", "Save", "Export PDF", "Recalculate"]
    for a, b, label in zip(acts(win), buttons(win), labels):
        assert b.accessibleName() == label
        keys = a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        assert b.toolTip() == f"{label} ({keys})"
    assert win.minimumWidth() == min_before
    rects = [b.geometry() for b in buttons(win) if b.isVisible()]
    for i, r in enumerate(rects):
        for r2 in rects[i + 1:]:
            assert not r.intersects(r2)


def test_hysteresis(win, qtbot):
    st = win.toolbar_styler
    tb = win.standard_toolbar
    total = st.wide_width
    at_width(win, qtbot, 1000)
    assert tb.toolButtonStyle() == TBS.ToolButtonTextBesideIcon
    seen = []
    for width, expected in ((total + 30, TBS.ToolButtonTextBesideIcon),
                            (total - 10, TBS.ToolButtonIconOnly),
                            (total + 10, TBS.ToolButtonIconOnly),
                            (total + 30, TBS.ToolButtonTextBesideIcon)):
        at_width(win, qtbot, width)
        seen.append(tb.toolButtonStyle())
        assert tb.toolButtonStyle() == expected, width
    assert len(set(seen)) == 2


def test_vertical_always_icon_only(win):
    win.addToolBar(Qt.ToolBarArea.LeftToolBarArea, win.standard_toolbar)
    QApplication.processEvents()
    assert win.standard_toolbar.toolButtonStyle() == TBS.ToolButtonIconOnly


def test_actions_unchanged_and_toolbar_flags(win):
    tb = win.standard_toolbar
    real = [a for a in tb.actions() if not a.isSeparator()]
    assert real == acts(win)
    assert tb.objectName() == "standard-toolbar"
    assert tb.isMovable() and not tb.isFloatable()


def test_pixmap_dpr2_and_palette(qtbot):
    pm = glyph_icon("save").pixmap(QSize(20, 20), 2.0)
    assert (pm.width(), pm.height()) == (40, 40)
    img = pm.toImage()
    assert any(img.pixelColor(x, y).alpha() > 0 for x in range(40) for y in range(40))
    for name in GLYPH_NAMES:
        assert not render_glyph(name, QSize(20, 20)).isNull()

    def dominant(pal_colour: QColor) -> QColor:
        app = QApplication.instance()
        old = app.palette()
        pal = QPalette(old)
        pal.setColor(QPalette.ColorRole.ButtonText, pal_colour)
        app.setPalette(pal)
        try:
            im = render_glyph("new", QSize(40, 40)).toImage()
            for y in range(40):
                for x in range(40):
                    c = im.pixelColor(x, y)
                    if c.alpha() == 255:
                        return c
        finally:
            app.setPalette(old)
        raise AssertionError("no opaque pixel")

    assert dominant(QColor("#202020")) != dominant(QColor("#f0f0f0"))
    off = render_glyph("new", QSize(20, 20), QIcon.Mode.Disabled)
    assert not off.isNull()
