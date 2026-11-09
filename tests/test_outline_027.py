"""Spec 027: Outline tab (headings = text regions whose first paragraph is entirely bold)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from livesheet.gui.main_window import MainWindow
from livesheet.gui.sidepanel import OUTLINE_EMPTY, OUTLINE_PLACEHOLDER

OUTLINE = 8


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module", autouse=True)
def isolated_settings(tmp_path_factory, app):
    old = QSettings.defaultFormat()
    d = tmp_path_factory.mktemp("qs027")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(d))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(d))
    yield
    QSettings.setDefaultFormat(old)


@pytest.fixture
def win(app):
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    w.sheet.clear_sheet()
    QApplication.processEvents()
    yield w
    w.close()


def bold_text(sheet, y, text, bold_chars=None, x=40):
    r = sheet.add_region("text", QPointF(x, y), "")
    cur = QTextCursor(r.editor.document())
    fmt = cur.charFormat()
    for i, ch in enumerate(text):
        f = cur.charFormat()
        f.setFontWeight(QFont.Weight.Bold if bold_chars is None or i < bold_chars
                        else QFont.Weight.Normal)
        cur.insertText(ch, f)
    return r


def plain_text(sheet, y, text):
    return bold_text(sheet, y, text, bold_chars=0)


def labels(win):
    win.side_panel.tabs.setCurrentIndex(OUTLINE)
    QApplication.processEvents()
    win.side_panel.rebuild_outline()
    return [b.text() for b in win.side_panel.outline_buttons]


def test_ac1_detection(win):
    s = win.sheet
    bold_text(s, 40, "Intro")
    plain_text(s, 120, "Some prose")
    res = bold_text(s, 200, "Results", bold_chars=2)
    s.add_region("math", QPointF(40, 280), "x:1")
    assert labels(win) == ["Intro"]
    cur = QTextCursor(res.editor.document())
    cur.select(QTextCursor.SelectionType.Document)
    f = cur.charFormat()
    f.setFontWeight(QFont.Weight.Bold)
    cur.mergeCharFormat(f)
    assert labels(win) == ["Intro", "Results"]


def test_ac2_order_and_pages(win):
    s = win.sheet
    bold_text(s, 300, "A")
    bold_text(s, 100, "B")
    assert labels(win) == ["B", "A"]
    assert not [l for l in win.side_panel.findChildren(QLabel) if l.text().startswith("Page")]
    c = bold_text(s, 700, "C")
    s._add_marker(500)
    labels(win)
    pages = [l.text() for l in win.side_panel.tabs.widget(OUTLINE).findChildren(QLabel)]
    assert pages == ["Page 1", "Page 2"]
    assert [b.text() for b in win.side_panel.outline_buttons] == ["B", "A", "C"]


def test_ac3_elide(win):
    bold_text(win.sheet, 40, "x" * 50)
    out = labels(win)
    assert len(out[0]) == 32 and out[0].endswith("…")
    assert win.side_panel.outline_buttons[0].toolTip().startswith("x" * 50)


def test_ac4_click_selects_and_scrolls(win):
    s = win.sheet
    for i in range(30):
        plain_text(s, 40 + i * 100, f"p{i}")
    target = bold_text(s, 2400, "Far")
    s._update_rect()
    labels(win)
    zoom = win.view.zoom()
    win.side_panel.outline_buttons[0].click()
    QApplication.processEvents()
    assert target.isSelected()
    assert win.view.zoom() == zoom
    vis = win.view.mapToScene(win.view.viewport().rect()).boundingRect()
    top = target.sceneBoundingRect().top()
    assert vis.top() <= top <= vis.top() + vis.height() / 4


def test_ac5_empty_state(win):
    labels(win)
    page = win.side_panel.tabs.widget(OUTLINE)
    assert [l.text() for l in page.findChildren(QLabel)] == [OUTLINE_EMPTY]
    assert page.findChildren(QPushButton) == []
    assert OUTLINE_PLACEHOLDER == OUTLINE_EMPTY


def test_ac6_refresh_debounce_and_idle(win, monkeypatch):
    s = win.sheet
    r = bold_text(s, 40, "Old")
    labels(win)
    cur = QTextCursor(r.editor.document())
    cur.select(QTextCursor.SelectionType.Document)
    f = cur.charFormat()
    f.setFontWeight(QFont.Weight.Bold)
    cur.insertText("New", f)
    r.editing = True   # contentChanged is emitted while editing
    r._on_contents_changed()
    QTest.qWait(500)
    assert [b.text() for b in win.side_panel.outline_buttons] == ["New"]
    win.side_panel.tabs.setCurrentIndex(0)
    calls = []
    orig = win.side_panel.rebuild_outline
    monkeypatch.setattr(win.side_panel, "rebuild_outline", lambda: calls.append(1) or orig())
    bold_text(s, 200, "Other")
    r._on_contents_changed()
    QTest.qWait(500)
    assert calls == []


def test_ac7_load_and_stale(win):
    s = win.sheet
    bold_text(s, 40, "Saved")
    doc = s.to_document()
    before = doc.to_json()
    s.clear_sheet()
    s.load_document(doc)
    assert labels(win) == ["Saved"]
    assert s.to_document().to_json() == before
    region = s.headings()[0][0]
    s.remove_regions([region])
    assert s.reveal_region(region) is False
    win.side_panel.outline_buttons[0].click()   # stale entry: no exception
    assert labels(win) == []


def test_other_tabs_untouched(win):
    tabs = win.side_panel.tabs
    assert tabs.tabText(OUTLINE) == "Outline" and tabs.tabText(9) == "Data"
    assert len(tabs.widget(9).findChildren(QLabel)) == 1
