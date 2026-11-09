"""Independent black-box review tests for spec 025 (larger Standard toolbar).

Settings are isolated: QSettings default format is switched to INI under a temp dir for the
whole module, so MainWindow's QSettings("LiveSheet","LiveSheet") never touches ~/Library.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QImage, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

from livesheet.gui.main_window import MainWindow

TBS = Qt.ToolButtonStyle
PLIST = Path.home() / "Library/Preferences/com.livesheet.LiveSheet.plist"


def _digest() -> str | None:
    return hashlib.md5(PLIST.read_bytes()).hexdigest() if PLIST.exists() else None


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module", autouse=True)
def isolated_settings(tmp_path_factory, app):
    before = _digest()
    old_fmt = QSettings.defaultFormat()
    d = tmp_path_factory.mktemp("qsettings025")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(d))
    yield
    QSettings.setDefaultFormat(old_fmt)
    assert _digest() == before, "test run modified the user's real LiveSheet settings"


@pytest.fixture
def win(app):
    w = MainWindow()
    w.addToolBar(Qt.ToolBarArea.TopToolBarArea, w.standard_toolbar)
    w.show()
    QApplication.processEvents()
    yield w
    w.close()


def acts(w):
    return [w.action_new, w.action_open, w.action_save, w.action_export_pdf, w.action_recalculate]


def btns(w):
    return [b for a in acts(w) if isinstance(b := w.standard_toolbar.widgetForAction(a), QToolButton)]


def width(w, n):
    w.resize(n, 700)
    QTest.qWait(20)
    QApplication.processEvents()


def tab_h():
    f = QFont(QApplication.font())
    f.setBold(True)
    return QFontMetrics(f).height() + 12


def style(w):
    return w.standard_toolbar.toolButtonStyle()


# 1 -----------------------------------------------------------------------------
def test_all_actions_have_icons(win):
    for a in acts(win):
        assert not a.icon().isNull()


def test_icon_size_default_and_larger_font(win):
    f = QFontMetrics(QApplication.font()).height()
    expected = max(20, min(32, (round(20 * f / 15) // 2) * 2))
    assert win.standard_toolbar.iconSize() == QSize(expected, expected)
    assert 20 <= expected <= 32


def test_icon_size_grows_with_font(app):
    old = QApplication.font()
    try:
        f = QFont(old)
        f.setPixelSize(19)
        QApplication.setFont(f)
        w = MainWindow()
        w.addToolBar(Qt.ToolBarArea.TopToolBarArea, w.standard_toolbar)
        w.show()
        QApplication.processEvents()
        h = QFontMetrics(QApplication.font()).height()
        exp = max(20, min(32, (round(20 * h / 15) // 2) * 2))
        assert w.standard_toolbar.iconSize() == QSize(exp, exp)
        assert exp >= 24 or h < 17
        w.close()
    finally:
        QApplication.setFont(old)


# 2 -----------------------------------------------------------------------------
def test_button_heights(win):
    bs = btns(win)
    assert len(bs) == 5
    for b in bs:
        assert b.sizeHint().height() >= 32
        assert b.sizeHint().height() >= tab_h() + 4


def test_taller_than_band_buttons(win):
    from PySide6.QtWidgets import QPushButton
    band = [b for b in win.findChildren(QPushButton) if b.isVisibleTo(win) and b.text()]
    if not band:
        pytest.skip("no band buttons found")
    tallest = max(b.sizeHint().height() for b in band)
    for b in btns(win):
        assert b.sizeHint().height() > tallest


# 3 -----------------------------------------------------------------------------
def test_wide_layout(win):
    width(win, 1000)
    assert style(win) == TBS.ToolButtonTextBesideIcon
    tb = win.standard_toolbar
    for b in btns(win):
        assert b.isVisible()
        assert tb.rect().contains(b.geometry())
    ext = tb.findChild(QToolButton, "qt_toolbar_ext_button")
    assert ext is None or not ext.isVisible()


def test_labels_text_beside_icon(win):
    width(win, 1000)
    assert [b.text().replace("&", "") for b in btns(win)] == [
        "New", "Open", "Save", "Export PDF", "Recalculate"]


# 4 -----------------------------------------------------------------------------
def test_narrow_icon_only_tooltips(win):
    width(win, 480)
    assert style(win) == TBS.ToolButtonIconOnly
    for b in btns(win):
        assert b.isVisible()
    tips = [b.toolTip() for b in btns(win)]
    assert tips[2] == "Save (" + win.action_save.shortcut().toString(
        win.action_save.shortcut().SequenceFormat.NativeText) + ")"
    assert tips[3].startswith("Export PDF (") and tips[3].endswith(")")
    assert tips[4].startswith("Recalculate (") and "F9" in tips[4]
    assert [b.accessibleName() for b in btns(win)] == [
        "New", "Open", "Save", "Export PDF", "Recalculate"]


def test_accessible_names_in_wide_style(win):
    width(win, 1000)
    assert [b.accessibleName() for b in btns(win)] == [
        "New", "Open", "Save", "Export PDF", "Recalculate"]


# 5 -----------------------------------------------------------------------------
def test_hysteresis(win):
    width(win, 1000)
    s = win.toolbar_styler.wide_width
    assert 250 < s < 900                       # spec: about 520
    changes = []
    last = style(win)
    for w in [1000, s + 40, s + 5, s - 2, s - 20, s + 5, s + 20, s + 23, s + 24 + 1, 1000]:
        width(win, int(w))
        cur = style(win)
        if cur != last:
            changes.append((w, cur))
            last = cur
    assert [c[1] for c in changes] == [TBS.ToolButtonIconOnly, TBS.ToolButtonTextBesideIcon]
    # went back to wide only at/above sum + 24
    assert changes[1][0] >= s + 24
    # window width equal to the toolbar's budget: window frame may differ, so only check bands
    width(win, s + 10)
    width(win, s - 30)
    assert style(win) == TBS.ToolButtonIconOnly
    width(win, s + 10)
    assert style(win) == TBS.ToolButtonIconOnly
    width(win, s + 30)
    assert style(win) == TBS.ToolButtonTextBesideIcon


def test_spec_sequence_one_change_per_crossing(win):
    seq = [1000, 540, 500, 540, 1000]
    seen = []
    for n in seq:
        width(win, n)
        seen.append(style(win))
    flips = sum(1 for a, b in zip(seen, seen[1:]) if a != b)
    assert flips <= 2


# 6 -----------------------------------------------------------------------------
def test_minimum_width_not_raised_and_no_overlap(win):
    tb = win.standard_toolbar
    with_tb = win.minimumSizeHint().width()
    tb.hide()
    QApplication.processEvents()
    without = win.minimumSizeHint().width()
    tb.show()
    QApplication.processEvents()
    assert with_tb == without
    width(win, 1)                                # clamps to the smallest allowed
    assert win.width() >= win.minimumWidth()
    rects = [b.geometry() for b in btns(win) if b.isVisible()]
    for i, r in enumerate(rects):
        for q in rects[i + 1:]:
            assert not r.intersects(q)
    ext = tb.findChild(QToolButton, "qt_toolbar_ext_button")
    if ext is not None and ext.isVisible():
        hidden = [a for a in acts(win) if not (tb.widgetForAction(a) and tb.widgetForAction(a).isVisible())]
        assert hidden  # extension shown only when something is hidden


# 7/8 ---------------------------------------------------------------------------
def test_actions_identity_and_trigger(win):
    got = [a for a in win.standard_toolbar.actions() if not a.isSeparator()]
    assert got == acts(win)
    hits = []
    win.action_recalculate.triggered.connect(lambda *_: hits.append(1))
    width(win, 1000)
    QTest.mouseClick(win.standard_toolbar.widgetForAction(win.action_recalculate), Qt.MouseButton.LeftButton)
    assert hits == [1]


def test_separators_kept(win):
    kinds = [a.isSeparator() for a in win.standard_toolbar.actions()]
    assert kinds == [False, False, False, True, False, True, False]


def test_menu_icons_hidden(win):
    for a in acts(win):
        assert a.isIconVisibleInMenu() is False


def test_toolbar_properties_unchanged(win):
    tb = win.standard_toolbar
    assert tb.objectName() == "standard-toolbar"
    assert tb.isMovable() and not tb.isFloatable()
    assert tb.toggleViewAction().text().replace("&", "") == "Standard Toolbar"


# 9 -----------------------------------------------------------------------------
def _dominant(img: QImage) -> QColor | None:
    counts: dict[int, int] = {}
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 200:
                counts[c.rgb()] = counts.get(c.rgb(), 0) + 1
    return QColor(max(counts, key=counts.get)) if counts else None


def _icon_img(icon: QIcon, edge=20, dpr=2.0, mode=QIcon.Mode.Normal) -> QImage:
    pm = icon.pixmap(QSize(edge, edge), dpr, mode)
    return pm.toImage()


@pytest.mark.parametrize("idx", range(5))
def test_hidpi_pixmap_size_and_nonblank(win, idx):
    pm = acts(win)[idx].icon().pixmap(QSize(20, 20), 2.0)
    assert pm.width() == 40 and pm.height() == 40
    img = pm.toImage()
    assert any(img.pixelColor(x, y).alpha() > 0 for x in range(40) for y in range(40))


@pytest.mark.parametrize("idx", range(5))
def test_icon_ratio_1_and_3(win, idx):
    ic = acts(win)[idx].icon()
    for dpr in (1.0, 1.5, 3.0):
        pm = ic.pixmap(QSize(20, 20), dpr)
        assert pm.width() == round(20 * dpr)


def _with_palette(app, text: QColor, window: QColor):
    old = app.palette()
    p = QPalette(old)
    for g in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        p.setColor(g, QPalette.ColorRole.ButtonText, text)
        p.setColor(g, QPalette.ColorRole.WindowText, text)
        p.setColor(g, QPalette.ColorRole.Text, text)
        p.setColor(g, QPalette.ColorRole.Window, window)
        p.setColor(g, QPalette.ColorRole.Button, window)
    app.setPalette(p)
    return old


def test_dark_vs_light_glyph_colours(win, app):
    old = app.palette()
    try:
        _with_palette(app, QColor(20, 20, 20), QColor(240, 240, 240))
        light = _dominant(_icon_img(win.action_save.icon()))
        _with_palette(app, QColor(235, 235, 235), QColor(30, 30, 30))
        dark = _dominant(_icon_img(win.action_save.icon()))
    finally:
        app.setPalette(old)
    assert light is not None and dark is not None
    assert light.lightness() < 100 and dark.lightness() > 150


def test_disabled_mode_uses_disabled_group(win, app):
    old = app.palette()
    try:
        p = QPalette(old)
        p.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(200, 60, 60))
        app.setPalette(p)
        normal = _dominant(_icon_img(win.action_new.icon()))
        dis = _dominant(_icon_img(win.action_new.icon(), mode=QIcon.Mode.Disabled))
    finally:
        app.setPalette(old)
    assert normal is not None and dis is not None
    assert normal != dis


def test_disabled_action_still_renders(win):
    win.action_export_pdf.setEnabled(False)
    try:
        img = _icon_img(win.action_export_pdf.icon(), mode=QIcon.Mode.Disabled)
        assert _dominant(img) is not None
    finally:
        win.action_export_pdf.setEnabled(True)


def test_glyphs_are_distinct(win):
    imgs = [_icon_img(a.icon(), 20, 1.0) for a in acts(win)]
    for i in range(5):
        for j in range(i + 1, 5):
            assert imgs[i] != imgs[j]


# edge cases --------------------------------------------------------------------
def test_hide_show_recomputes_style(win):
    width(win, 480)
    win.standard_toolbar.hide()
    width(win, 1000)
    win.standard_toolbar.show()
    QApplication.processEvents()
    assert style(win) == TBS.ToolButtonTextBesideIcon


def test_left_dock_is_icon_only_then_back(win):
    width(win, 1000)
    win.addToolBar(Qt.ToolBarArea.LeftToolBarArea, win.standard_toolbar)
    win.standard_toolbar.show()
    QApplication.processEvents()
    assert style(win) == TBS.ToolButtonIconOnly
    win.addToolBar(Qt.ToolBarArea.TopToolBarArea, win.standard_toolbar)
    win.standard_toolbar.show()
    QApplication.processEvents()
    width(win, 1000)
    assert style(win) == TBS.ToolButtonTextBesideIcon


def test_menus_have_no_visible_icons(win):
    for m in (a.menu() for a in win.menuBar().actions() if a.menu()):
        for a in m.actions():
            if a in acts(win):
                assert not a.isIconVisibleInMenu()


# IP: the module is plain geometry ----------------------------------------------
def test_icons_module_has_no_raster_or_file_loading():
    src = (Path(__file__).parent.parent / "livesheet/gui/icons.py").read_text()
    for bad in (".png", ".svg", ".ico", "QPixmap(\"", "QIcon(\"", "fromTheme", "QFileIconProvider"):
        assert bad not in src
