"""Developer tests for spec 011's two Greek-letter keyboard-shortcut layers (acceptance
criteria 11, 12, 14, 15, 16). Qt-dependent; skip gracefully when PySide6 cannot load.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import (  # noqa: E402
    GREEK_SHORTCUTS_CTRL_ALT,
    GREEK_SHORTCUTS_CTRL_SHIFT,
    MainWindow,
)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


def _win() -> MainWindow:
    _ensure_app()
    win = MainWindow()
    win.sheet.set_modified(False)
    return win


def _close(win: MainWindow) -> None:
    win.sheet.set_modified(False)
    win.close()


_KEY = {chr(c): getattr(Qt.Key, f"Key_{chr(c)}") for c in range(ord("A"), ord("Z") + 1)}


# -- 11 layer 1 (Ctrl+Shift+<letter>) inserts the right Greek letter ------------------------------

@pytest.mark.parametrize("letter,name", GREEK_SHORTCUTS_CTRL_SHIFT)
def test_criterion11_ctrl_shift_shortcut_inserts_the_right_greek_name(letter, name):
    win = _win()
    win.show()
    QApplication.processEvents()
    QTest.keyClick(win, _KEY[letter], Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    region = win.sheet.editing_region()
    assert region is not None and region.source == name
    win.sheet.set_modified(False)
    _close(win)


def test_criterion11_table_has_the_documented_letters():
    """11, not the spec's originally-stated 12: "S" (sigma) turned out to already be claimed by
    "Save As" (QKeySequence::StandardKey.SaveAs resolves to Ctrl+Shift+S on this platform) -- a
    real collision the spec's own "already claimed" list (A/P/M/C/E) missed since it is a Qt
    standard key, not a literal string. Excluded by the spec's own stated rule; sigma stays
    reachable via layer 2 (Ctrl+Alt+S). See docs/board/log.md for the full deviation note."""
    letters = {letter for letter, _ in GREEK_SHORTCUTS_CTRL_SHIFT}
    assert letters == set("BGDZIKLNXRU")
    names = {name for _, name in GREEK_SHORTCUTS_CTRL_SHIFT}
    assert names == {"beta", "gamma", "delta", "zeta", "iota", "kappa", "lambda", "nu", "xi",
                     "rho", "upsilon"}


# -- 12 the 5 pre-existing Ctrl+Shift+ shortcuts are unchanged ------------------------------------

def test_criterion12_ctrl_shift_a_still_selects_all_regions_not_alpha():
    win = _win()
    win.show()
    QApplication.processEvents()
    win.sheet.insert_region("math", "1").finish_editing()
    assert len(win.sheet.regions()) == 1

    QTest.keyClick(win, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert all(r.isSelected() for r in win.sheet.regions())   # Select All Regions, not "alpha"
    assert win.sheet.editing_region() is None   # no new region created by the shortcut
    win.sheet.set_modified(False)
    _close(win)


def test_criterion12_insert_plot_matrix_component_shortcuts_unchanged_by_identity():
    win = _win()
    menu_actions = [a for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                    for a in m.actions()]
    by_text = {a.text().replace("&", ""): a for a in menu_actions}
    assert by_text["Plot"].shortcut() == QKeySequence("Ctrl+Shift+P")
    assert by_text["Matrix…"].shortcut() == QKeySequence("Ctrl+Shift+M")
    assert by_text["Component…"].shortcut() == QKeySequence("Ctrl+Shift+C")
    assert by_text["Select All Regions"].shortcut() == QKeySequence("Ctrl+Shift+A")
    assert by_text["Export PDF…"].shortcut() == QKeySequence("Ctrl+Shift+E")
    _close(win)


def test_criterion12_no_new_ctrl_shift_shortcut_on_the_5_reserved_letters():
    reserved = set("APMCE")
    new_letters = {letter for letter, _ in GREEK_SHORTCUTS_CTRL_SHIFT}
    assert not (reserved & new_letters)


def test_regression_save_as_still_works_and_sigma_is_ctrl_alt_only():
    """The developer-found "S" collision (see test_criterion11_table_has_the_documented_letters'
    docstring): Ctrl+Shift+S must still trigger Save As, unambiguously, and sigma is reachable
    only through layer 2."""
    win = _win()
    win.show()
    QApplication.processEvents()
    assert win.action_save.shortcut() == QKeySequence("Ctrl+S")
    file_menu = next(m for m in win.menuBar().findChildren(type(win.menuBar().addMenu("x")))
                      if m.title() == "&File")
    save_as = next(a for a in file_menu.actions() if a.text() == "Save &As…")
    assert save_as.shortcut() == QKeySequence("Ctrl+Shift+S")
    assert "sigma" not in {name for letter, name in GREEK_SHORTCUTS_CTRL_SHIFT}
    assert ("S", "sigma") in GREEK_SHORTCUTS_CTRL_ALT
    _close(win)


# -- 14 layer 2 (Ctrl+Alt+<letter>) covers all 23 lowercase letters -------------------------------

@pytest.mark.parametrize("letter,name", GREEK_SHORTCUTS_CTRL_ALT)
def test_criterion14_ctrl_alt_shortcut_inserts_the_right_greek_name(letter, name):
    win = _win()
    win.show()
    QApplication.processEvents()
    QTest.keyClick(win, _KEY[letter], Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
    region = win.sheet.editing_region()
    assert region is not None and region.source == name
    win.sheet.set_modified(False)
    _close(win)


def test_criterion14_all_23_lowercase_letters_covered_f_j_v_are_not():
    names = {name for _, name in GREEK_SHORTCUTS_CTRL_ALT}
    expected = {"alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota",
               "kappa", "lambda", "mu", "nu", "xi", "omicron", "rho", "sigma", "tau", "upsilon",
               "phi", "chi", "psi", "omega"}
    assert names == expected
    letters = {letter for letter, _ in GREEK_SHORTCUTS_CTRL_ALT}
    assert letters == set("ABCDEGHIKLMNOPQRSTUWXYZ")
    assert not ({"F", "J", "V"} & letters)


# -- 15 no collisions between the two layers or with anything pre-existing ------------------------

def test_criterion15_no_shortcut_string_collisions_and_shared_letters_agree():
    shift_map = dict(GREEK_SHORTCUTS_CTRL_SHIFT)
    alt_map = dict(GREEK_SHORTCUTS_CTRL_ALT)
    shift_strings = {f"Ctrl+Shift+{letter}" for letter in shift_map}
    alt_strings = {f"Ctrl+Alt+{letter}" for letter in alt_map}
    assert not (shift_strings & alt_strings)   # different modifier text, cannot literally collide
    for letter in set(shift_map) & set(alt_map):
        assert shift_map[letter] == alt_map[letter]   # same letter, same Greek name, either layer


def test_criterion15_ctrl_alt_was_unused_before_this_spec():
    import pathlib

    gui_dir = pathlib.Path(__file__).resolve().parents[1] / "livesheet" / "gui"
    for path in gui_dir.glob("*.py"):
        if path.name == "main_window.py":
            continue
        assert "Ctrl+Alt" not in path.read_text()


def test_criterion15_all_registered_window_actions_have_distinct_shortcuts():
    win = _win()
    seen: dict[str, str] = {}
    for action in win.actions():
        text = action.shortcut().toString()
        if not text:
            continue
        assert text not in seen, f"{text} bound to both {seen.get(text)!r} and {action.text()!r}"
        seen[text] = action.text()
    _close(win)


# -- 16 uppercase Greek letters have no new shortcut ----------------------------------------------

def test_criterion16_uppercase_greek_letters_have_no_shortcut():
    bound_names = {name for _, name in GREEK_SHORTCUTS_CTRL_SHIFT} | \
        {name for _, name in GREEK_SHORTCUTS_CTRL_ALT}
    uppercase_names = {"Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega"}
    assert not (bound_names & uppercase_names)
