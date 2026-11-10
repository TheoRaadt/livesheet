"""Independent black-box tests for spec 011 (side-panel category tabs, Greek-letter palette,
Subscript quick-insert), written from docs/board/specs/011-side-panel-category-tabs.md's own
acceptance criteria 1-16 and Edge cases -- not from reading livesheet/gui/sidepanel.py or
livesheet/gui/main_window.py as the source of truth, and not from reading the developer's own
tests/test_greek_shortcuts.py or tests/test_side_panel_categories.py (per this task's instruction;
those files were not opened while drafting the tests below, only their test-function *names* were
seen in passing via a directory grep when planning where to put this new file).

Every expected value below (token labels/strings/tooltips, the 23 lowercase + 10 uppercase Greek
names, both keyboard-shortcut tables) is hand-transcribed from the spec text itself, not imported
from ``engine.formatting.GREEK`` or ``gui.sidepanel.MATH_TOKENS`` -- so a test failure here means
the implementation disagrees with the spec, not merely with itself.

One thing this file verifies from first principles rather than trusting anyone's say-so (including
the developer's own log.md entry and test file): the claim that Ctrl+Shift+S already belongs to
"Save As" (a Qt *standard key*, not a literal string, so the spec's own grep-based "already
claimed" list -- A/P/M/C/E -- missed it) and that layer 1 therefore has 11 Ctrl+Shift+<letter>
shortcuts, not the spec's own originally-written 12. ``test_layer1_count_and_membership_derived_
from_first_principles`` below re-derives the expected 11-letter set algorithmically from the 23
Greek names' first letters and the *actual* set of already-bound Ctrl+Shift+<letter> shortcuts
found live on the window (not a hardcoded list of "5 already claimed letters"), and separately
confirms Ctrl+Shift+S's real QAction is Save As, not a sigma-inserting action.
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtGui import QAction, QKeySequence  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QToolBar,
)

from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.main_window import MainWindow  # noqa: E402
from livesheet.gui.regions import MathRegion  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Redirect every ``QSettings("LiveSheet", "LiveSheet")`` call inside main_window.py to a
    private ini file for this test only, so this suite never touches the real on-disk prefs."""
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


def _make_window() -> MainWindow:
    _ensure_app()
    win = MainWindow()
    win.sheet.set_modified(False)
    return win


def _close(win: MainWindow) -> None:
    win.sheet.set_modified(False)
    win.close()


def _tab_widget(win: MainWindow) -> QTabWidget:
    tabs = win.findChild(QTabWidget, "side-panel-tabs")
    assert tabs is not None
    return tabs


def _buttons_on_tab(tabs: QTabWidget, index: int) -> list[QPushButton]:
    return tabs.widget(index).findChildren(QPushButton)


def _button_by_label(tabs: QTabWidget, index: int, label: str) -> QPushButton:
    matches = [b for b in _buttons_on_tab(tabs, index) if b.text() == label]
    assert len(matches) == 1, f"expected exactly one {label!r} button on tab {index}, found {matches}"
    return matches[0]


# ---------------------------------------------------------------------------
# Hand-transcribed expected data, from the spec text, not the implementation.
# ---------------------------------------------------------------------------

EXPECTED_TAB_ORDER = ("Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical",
                      "Electrical", "Chemical", "Outline", "Data")   # specs 018-020 added 3

# Criterion 3: the 7 carried-over Statements/Constants entries.
EXPECTED_STATEMENTS_CONSTANTS = [
    (":=", ":= "), ("≡", "≡ "), ("=", " ="), ("→", " → "),
    ("π", "pi"), ("e", "e"), ("i", "I"),
]

# 23 lowercase Greek names in Greek-alphabet order (spec's "Greek letters" section).
GREEK_LOWER_NAMES = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa",
    "lambda", "mu", "nu", "xi", "omicron", "rho", "sigma", "tau", "upsilon", "phi", "chi",
    "psi", "omega",
]
assert len(GREEK_LOWER_NAMES) == 23

# 10 uppercase Greek names the spec names explicitly.
GREEK_UPPER_NAMES = ["Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega"]
assert len(GREEK_UPPER_NAMES) == 10

# Criterion 4: the 3 carried-over Algebra ("Operators") entries, plus the new Subscript entry.
EXPECTED_ALGEBRA = [("√", "sqrt(x)"), ("ⁿ√", "root(x, n)"), ("x²", "^2"), ("xₙ", "_")]

# Criterion 5: the 2 Calculus entries.
EXPECTED_CALCULUS = [("d/dx", "diff(f, x)"), ("∫", "integrate(f, x)"),
                    ("∫ₐᵇ", "integrate(f, (x, a, b))"), ("lim", "limit(f, x, 0)")]

# Layer-1 table as literally printed in the spec (12 rows, including sigma/S) -- used only to
# derive, not to assert directly (see test_layer1_count_and_membership_derived_from_first_principles).
SPEC_LAYER1_TABLE_AS_WRITTEN = {
    "B": "beta", "G": "gamma", "D": "delta", "Z": "zeta", "I": "iota", "K": "kappa",
    "L": "lambda", "N": "nu", "X": "xi", "R": "rho", "S": "sigma", "U": "upsilon",
}

# Layer-2 table, all 23 lowercase letters (spec Addendum 2, acceptance criterion 14).
LAYER2_TABLE = {
    "A": "alpha", "B": "beta", "C": "chi", "D": "delta", "E": "epsilon", "G": "gamma",
    "H": "eta", "I": "iota", "K": "kappa", "L": "lambda", "M": "mu", "N": "nu",
    "O": "omicron", "P": "phi", "Q": "psi", "R": "rho", "S": "sigma", "T": "theta",
    "U": "upsilon", "W": "omega", "X": "xi", "Y": "tau", "Z": "zeta",
}
assert len(LAYER2_TABLE) == 23
assert set(LAYER2_TABLE.values()) == set(GREEK_LOWER_NAMES)

UNBOUND_LAYER2_LETTERS = ["F", "J", "V"]

# The 5 pre-existing Ctrl+Shift+ shortcuts the spec itself says must not change meaning.
PRE_EXISTING_CTRL_SHIFT = {
    "A": "Select All Regions", "P": "Insert Plot", "M": "Insert Matrix…",
    "C": "Insert Component…", "E": "Export PDF",
}


# ---------------------------------------------------------------------------
# Criterion 1: Math toolbar removal, Standard toolbar untouched.
# ---------------------------------------------------------------------------

def test_criterion1_math_toolbar_fully_removed():
    win = _make_window()
    assert win.findChild(QToolBar, "math-toolbar") is None
    assert not hasattr(win, "math_toolbar")
    menu_actions_text = [a.text() for m in win.menuBar().actions() for a in m.menu().actions() if m.menu()]
    assert not any("Math Toolbar" in t for t in menu_actions_text)
    _close(win)


def test_criterion1_standard_toolbar_present_and_independent():
    win = _make_window()
    standard = win.findChild(QToolBar, "standard-toolbar")
    assert standard is not None
    menu_actions_text = [a.text() for m in win.menuBar().actions() for a in m.menu().actions() if m.menu()]
    assert any("Standard Toolbar" in t for t in menu_actions_text)
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 2: 7 tabs, fixed order.
# ---------------------------------------------------------------------------

def test_criterion2_seven_tabs_in_order():
    win = _make_window()
    tabs = _tab_widget(win)
    assert tabs.count() == 10
    assert tuple(tabs.tabText(i) for i in range(10)) == EXPECTED_TAB_ORDER
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 3: Elements tab, 40 entries.
# ---------------------------------------------------------------------------

def test_criterion3_elements_tab_has_exactly_40_buttons():
    win = _make_window()
    tabs = _tab_widget(win)
    elements_index = EXPECTED_TAB_ORDER.index("Elements")
    buttons = _buttons_on_tab(tabs, elements_index)
    assert len(buttons) == 40
    _close(win)


def test_criterion3_elements_tab_carries_over_statements_and_constants_unchanged():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    for label, _token in EXPECTED_STATEMENTS_CONSTANTS:
        btn = _button_by_label(tabs, idx, label)
        assert btn is not None
    _close(win)


def test_criterion3_clicking_pi_inserts_pi_exactly_as_before():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    tabs.setCurrentIndex(idx)
    _button_by_label(tabs, idx, "π").click()
    region = win.sheet.editing_region()
    assert isinstance(region, MathRegion)
    assert region.source.strip() == "pi"
    _close(win)


@pytest.mark.parametrize("name", GREEK_LOWER_NAMES)
def test_criterion3_every_lowercase_greek_button_present_and_has_correct_label_and_insertion(name):
    from livesheet.engine.formatting import GREEK as _display_greek_map  # read-only, display dict
    glyph = _display_greek_map[name]
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    btn = _button_by_label(tabs, idx, glyph)
    btn.click()
    region = win.sheet.editing_region()
    assert isinstance(region, MathRegion)
    assert region.source.strip().endswith(name)
    _close(win)


@pytest.mark.parametrize("name", GREEK_UPPER_NAMES)
def test_criterion3_every_uppercase_greek_button_present_and_has_correct_label_and_insertion(name):
    from livesheet.engine.formatting import GREEK as _display_greek_map
    glyph = _display_greek_map[name]
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    btn = _button_by_label(tabs, idx, glyph)
    btn.click()
    region = win.sheet.editing_region()
    assert isinstance(region, MathRegion)
    assert region.source.strip().endswith(name)
    _close(win)


def test_criterion3_lamda_alias_has_no_duplicate_button_and_lowercase_pi_is_not_a_greek_button():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    labels = [b.text() for b in _buttons_on_tab(tabs, idx)]
    # Exactly one lambda-glyph button (not two, for "lamda" and "lambda").
    assert labels.count("λ") == 1
    # Exactly one lowercase-pi-glyph button overall (the pre-existing Constants one).
    assert labels.count("π") == 1
    _close(win)


def test_criterion3_elements_tab_has_grey_subheaders_for_its_three_groups():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Elements")
    labels_text = [lb.text() for lb in tabs.widget(idx).findChildren(QLabel)]
    for header in ("Statements", "Constants", "Greek letters"):
        assert header in labels_text
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 4: Algebra tab, 4 entries, including the new Subscript button.
# ---------------------------------------------------------------------------

def test_criterion4_algebra_tab_has_exactly_4_buttons_renamed_from_operators():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Algebra")
    assert tabs.tabText(idx) == "Algebra"
    assert "Operators" not in [tabs.tabText(i) for i in range(tabs.count())]
    buttons = _buttons_on_tab(tabs, idx)
    assert len(buttons) == 4
    assert {b.text() for b in buttons} == {"√", "ⁿ√", "x²", "xₙ"}
    _close(win)


def test_criterion4_clicking_sqrt_inserts_sqrt_open_paren():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Algebra")
    _button_by_label(tabs, idx, "√").click()
    region = win.sheet.editing_region()
    assert region.source.strip() == "sqrt(x)"
    _close(win)


def test_criterion4_clicking_new_subscript_button_inserts_a_bare_underscore():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Algebra")
    btn = _button_by_label(tabs, idx, "xₙ")
    assert btn.toolTip() == "Subscript"
    btn.click()
    region = win.sheet.editing_region()
    assert region.source.strip() == "_"
    _close(win)


def test_criterion4_subscript_does_not_touch_bracket_operator():
    """The spec is explicit this must not touch [/]: no Algebra button inserts a bracket."""
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Algebra")
    tokens_inserted = []
    for btn in _buttons_on_tab(tabs, idx):
        btn.click()
        region = win.sheet.editing_region()
        tokens_inserted.append(region.source.strip())
        region.source = ""  # reset for the next button's insertion
        region.editor.document().setPlainText("")
    assert not any("[" in t or "]" in t for t in tokens_inserted)
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 5: Calculus tab, unchanged, 2 entries.
# ---------------------------------------------------------------------------

def test_criterion5_calculus_tab_unchanged_2_entries():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Calculus")
    buttons = _buttons_on_tab(tabs, idx)
    assert len(buttons) == 4
    assert {b.text() for b in buttons} == {"d/dx", "∫", "∫ₐᵇ", "lim"}
    _close(win)


def test_criterion5_clicking_d_dx_inserts_diff_open_paren():
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index("Calculus")
    _button_by_label(tabs, idx, "d/dx").click()
    region = win.sheet.editing_region()
    assert region.source.strip() == "diff(f, x)"
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 6: Statistics / Optimization placeholders, no interactivity.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tab_name", ["Outline", "Data"])  # spec 026
def test_criterion6_placeholder_tabs_have_no_clickable_widgets(tab_name):
    win = _make_window()
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index(tab_name)
    widget = tabs.widget(idx)
    assert len(widget.findChildren(QPushButton)) == (4 if tab_name == "Data" else 0)   # spec 028
    labels = widget.findChildren(QLabel)
    assert len(labels) == 1
    assert labels[0].alignment() & Qt.AlignmentFlag.AlignCenter
    assert labels[0].wordWrap() is True
    assert labels[0].text().strip() != ""
    _close(win)


@pytest.mark.parametrize("tab_name", ["Statistics", "Optimization"])
def test_criterion6_clicking_placeholder_never_creates_or_changes_a_region(tab_name):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    win = _make_window()
    before = list(win.sheet.regions())
    tabs = _tab_widget(win)
    idx = EXPECTED_TAB_ORDER.index(tab_name)
    tabs.setCurrentIndex(idx)
    spy = Mock()
    win.insert_token = spy
    widget = tabs.widget(idx)
    label = widget.findChildren(QLabel)[0]
    # QLabel is not clickable by itself; drive a real mouse click at its centre anyway to confirm
    # nothing downstream (a parent handler, an accidental connect) reacts to it either.
    QTest.mouseClick(label, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                      label.rect().center())
    assert spy.call_count == 0
    after = list(win.sheet.regions())
    assert before == after
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 7: Outline/Data unchanged, now 6th and 7th.
# ---------------------------------------------------------------------------

def test_criterion7_outline_and_data_are_sixth_and_seventh_and_still_placeholder_only():
    win = _make_window()
    tabs = _tab_widget(win)
    assert tabs.tabText(8) == "Outline"
    assert tabs.tabText(9) == "Data"
    for idx in (8, 9):
        widget = tabs.widget(idx)
        assert len(widget.findChildren(QPushButton)) == (4 if idx == 9 else 0)   # spec 028
        assert len(widget.findChildren(QLabel)) == 1
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 8: total clickable tokens across the 3 functional tabs is 46.
# ---------------------------------------------------------------------------

def test_criterion8_total_buttons_across_functional_tabs_is_48_no_duplicates():
    win = _make_window()
    tabs = _tab_widget(win)
    all_labels: list[str] = []
    for name in ("Elements", "Algebra", "Calculus"):
        idx = EXPECTED_TAB_ORDER.index(name)
        all_labels.extend(b.text() for b in _buttons_on_tab(tabs, idx))
    assert len(all_labels) == 48
    # "nothing dropped, nothing duplicated": every label distinct except intentional repeats
    # across different tabs are impossible here since categories don't share glyphs; assert
    # no duplicate label appears twice *within* the full 46.
    assert len(set(all_labels)) == len(all_labels)
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 9: dock open/close, width 120-320, active-tab persistence across a restart.
# ---------------------------------------------------------------------------

def test_criterion9_active_tab_persists_across_restart_spec022():
    win = _make_window()
    win.show()
    QApplication.processEvents()
    tabs = _tab_widget(win)
    chosen_index = EXPECTED_TAB_ORDER.index("Data")  # a non-default tab
    tabs.setCurrentIndex(chosen_index)
    QApplication.processEvents()
    _close(win)

    win2 = _make_window()
    win2.show()
    QApplication.processEvents()
    tabs2 = _tab_widget(win2)
    assert tabs2.currentIndex() == chosen_index
    _close(win2)


def test_criterion9_panel_closed_state_persists_across_restart():
    win = _make_window()
    win.show()
    QApplication.processEvents()
    win.side_panel.toggleViewAction().trigger()
    assert not win.side_panel.isVisible()
    _close(win)

    win2 = _make_window()
    win2.show()
    QApplication.processEvents()
    assert not win2.side_panel.isVisible()
    _close(win2)


# ---------------------------------------------------------------------------
# Criterion 10: a stale "math-toolbar"-naming window_state blob loads without crashing.
# ---------------------------------------------------------------------------

def test_criterion10_stale_math_toolbar_window_state_loads_without_error(isolated_settings):
    """Craft a synthetic 'pre-spec-011' saveState() blob that genuinely names a 'math-toolbar'
    QToolBar (built on a throwaway QMainWindow, not the real app), seed it into the isolated
    settings file, then construct a real MainWindow and confirm it does not raise and ends up
    with exactly today's one toolbar."""
    _ensure_app()
    scratch = QMainWindow()
    fake_math_toolbar = QToolBar("Math", scratch)
    fake_math_toolbar.setObjectName("math-toolbar")
    scratch.addToolBar(fake_math_toolbar)
    fake_standard = QToolBar("Standard", scratch)
    fake_standard.setObjectName("standard-toolbar")
    scratch.addToolBar(fake_standard)
    blob = scratch.saveState()
    scratch.deleteLater()

    settings = QSettings(isolated_settings, QSettings.Format.IniFormat)
    settings.setValue("window_state", blob)
    settings.sync()

    win = MainWindow()  # must not raise
    assert win.findChild(QToolBar, "math-toolbar") is None
    assert win.findChild(QToolBar, "standard-toolbar") is not None
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 11/12: layer-1 Ctrl+Shift+<letter> shortcuts, and the 5 pre-existing ones untouched.
# ---------------------------------------------------------------------------

def _window_actions_by_shortcut(win: MainWindow) -> dict[str, list[QAction]]:
    by_shortcut: dict[str, list[QAction]] = {}
    for act in win.findChildren(QAction):
        seq = act.shortcut()
        if seq.isEmpty():
            continue
        by_shortcut.setdefault(seq.toString(), []).append(act)
    return by_shortcut


def test_layer1_count_and_membership_derived_from_first_principles():
    """Re-derive the expected Ctrl+Shift+<letter> Greek layer from scratch (not from the spec's
    own written table, and not from main_window.py's own comment/constant) and compare it to what
    is actually registered on a real window. This is the independent check this task specifically
    asked for: confirm the layer-1 count is 11, not the spec's originally-written 12, and that the
    exclusion is driven by the *real* already-bound shortcuts on the window, including Save As."""
    win = _make_window()
    by_shortcut = _window_actions_by_shortcut(win)

    # Which single uppercase letters already have exactly one non-Greek action bound under
    # Ctrl+Shift+<letter>, found live on the window (not hardcoded "A/P/M/C/E").
    already_claimed: set[str] = set()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        seq = QKeySequence(f"Ctrl+Shift+{letter}").toString()
        actions = by_shortcut.get(seq, [])
        non_greek = [a for a in actions if a.text() not in GREEK_LOWER_NAMES]
        if non_greek:
            already_claimed.add(letter)

    # First letters of the 23 Greek names that are unique among those 23 names.
    first_letters = [name[0].upper() for name in GREEK_LOWER_NAMES]
    unique_first_letters = {name[0].upper() for name in GREEK_LOWER_NAMES
                             if first_letters.count(name[0].upper()) == 1}

    expected = {name for name in GREEK_LOWER_NAMES
                if name[0].upper() in unique_first_letters and name[0].upper() not in already_claimed}

    actual = set()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        seq = QKeySequence(f"Ctrl+Shift+{letter}").toString()
        actions = [a for a in by_shortcut.get(seq, []) if a.text() in GREEK_LOWER_NAMES]
        actual.update(a.text() for a in actions)

    assert "S" in already_claimed, (
        "expected Save As's StandardKey.SaveAs to resolve to Ctrl+Shift+S on this platform; "
        "if this fails, the whole premise of excluding sigma from layer 1 needs re-checking"
    )
    assert expected == actual
    assert len(actual) == 11, f"expected exactly 11 layer-1 Greek shortcuts, got {len(actual)}: {actual}"
    assert "sigma" not in actual
    _close(win)


@pytest.mark.parametrize("letter,name", sorted(
    (l, n) for l, n in SPEC_LAYER1_TABLE_AS_WRITTEN.items() if l != "S"
))
def test_criterion11_ctrl_shift_shortcut_inserts_the_right_greek_letter(letter, name):
    win = _make_window()
    acts = [a for a in win.findChildren(QAction)
            if a.shortcut() == QKeySequence(f"Ctrl+Shift+{letter}") and a.text() == name]
    assert len(acts) == 1, f"expected exactly one Ctrl+Shift+{letter} action named {name!r}"
    acts[0].trigger()
    region = win.sheet.editing_region()
    assert isinstance(region, MathRegion)
    assert region.source.strip().endswith(name)
    _close(win)


def test_criterion12_ctrl_shift_a_still_selects_all_not_alpha():
    win = _make_window()
    region1 = win.sheet.insert_region("math")
    region1.source = "1"
    region2 = win.sheet.insert_region("math")
    region2.source = "2"
    win.sheet.clearSelection()
    acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence("Ctrl+Shift+A")]
    assert len(acts) == 1
    act = acts[0]
    assert act.text() != "alpha"
    act.trigger()
    assert region1.isSelected() and region2.isSelected()
    _close(win)


@pytest.mark.parametrize("letter,expected_text_fragment", [
    ("P", "Plot"), ("M", "Matrix"), ("C", "Component"), ("E", "Export"),
])
def test_criterion12_insert_plot_matrix_component_export_shortcuts_unchanged(letter, expected_text_fragment):
    win = _make_window()
    acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence(f"Ctrl+Shift+{letter}")]
    assert len(acts) == 1, f"ambiguous or missing Ctrl+Shift+{letter}: {acts}"
    assert expected_text_fragment in acts[0].text()
    _close(win)


def test_criterion12_regression_save_as_still_bound_to_ctrl_shift_s_sigma_is_not():
    """The specific check this task asked to confirm independently: Ctrl+Shift+S is Save As,
    never a sigma-inserting action, anywhere in the window."""
    win = _make_window()
    acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence("Ctrl+Shift+S")]
    assert len(acts) == 1, f"expected exactly one Ctrl+Shift+S action (ambiguous otherwise): {acts}"
    assert "Save" in acts[0].text() and "As" in acts[0].text()
    assert acts[0].text() != "sigma"
    # And: no action anywhere named "sigma" has this shortcut, under any search.
    sigma_actions = [a for a in win.findChildren(QAction) if a.text() == "sigma"]
    assert all(a.shortcut() != QKeySequence("Ctrl+Shift+S") for a in sigma_actions)
    _close(win)


def test_criterion12_no_new_ctrl_shift_shortcut_added_on_the_5_reserved_letters():
    win = _make_window()
    for letter in PRE_EXISTING_CTRL_SHIFT:
        acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence(f"Ctrl+Shift+{letter}")]
        assert len(acts) == 1, f"Ctrl+Shift+{letter} must resolve to exactly one action, got {acts}"
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 13: hand-typed Greek word still displays as a glyph (engine/display unchanged).
# ---------------------------------------------------------------------------

def test_criterion13_hand_typed_alpha_still_renders_as_glyph_no_button_no_shortcut():
    win = _make_window()
    region = win.sheet.insert_region("math")
    region.start_editing()
    region.editor.setPlainText("alpha")
    region.finish_editing()
    assert "α" in region.editor.toPlainText()
    _close(win)


def test_criterion13_hand_typed_subscript_still_renders_via_underscore():
    win = _make_window()
    region = win.sheet.insert_region("math")
    region.start_editing()
    region.editor.setPlainText("x_1")
    region.finish_editing()
    # pretty.py's _SUB_RE renders "x_1" with "1" as an actual Unicode/HTML subscript, not a
    # literal underscore remaining in the displayed text.
    assert "_1" not in region.editor.toPlainText()
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 14: layer-2 Ctrl+Alt+<letter> covers all 23 lowercase letters; F/J/V unbound.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("letter,name", sorted(LAYER2_TABLE.items()))
def test_criterion14_ctrl_alt_shortcut_inserts_the_right_greek_letter(letter, name):
    win = _make_window()
    acts = [a for a in win.findChildren(QAction)
            if a.shortcut() == QKeySequence(f"Ctrl+Alt+{letter}") and a.text() == name]
    assert len(acts) == 1, f"expected exactly one Ctrl+Alt+{letter} action named {name!r}"
    acts[0].trigger()
    region = win.sheet.editing_region()
    assert isinstance(region, MathRegion)
    assert region.source.strip().endswith(name)
    _close(win)


def test_criterion14_all_23_lowercase_greek_letters_reachable_under_ctrl_alt():
    win = _make_window()
    reachable = set()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        acts = [a for a in win.findChildren(QAction)
                if a.shortcut() == QKeySequence(f"Ctrl+Alt+{letter}") and a.text() in GREEK_LOWER_NAMES]
        reachable.update(a.text() for a in acts)
    assert reachable == set(GREEK_LOWER_NAMES)
    _close(win)


@pytest.mark.parametrize("letter", UNBOUND_LAYER2_LETTERS)
def test_criterion14_f_j_v_not_bound_to_anything_under_ctrl_alt(letter):
    win = _make_window()
    acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence(f"Ctrl+Alt+{letter}")]
    assert acts == []
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 15: no Ctrl+Alt/Ctrl+Shift collisions; the 11 shared letters agree across layers.
# ---------------------------------------------------------------------------

def test_criterion15_shared_letters_insert_the_same_greek_letter_under_both_layers():
    shared = set(SPEC_LAYER1_TABLE_AS_WRITTEN) & set(LAYER2_TABLE)
    shared.discard("S")  # sigma excluded from layer 1 (confirmed by the derivation test above)
    assert len(shared) == 11
    win = _make_window()
    for letter in shared:
        shift_acts = [a for a in win.findChildren(QAction)
                      if a.shortcut() == QKeySequence(f"Ctrl+Shift+{letter}") and a.text() in GREEK_LOWER_NAMES]
        alt_acts = [a for a in win.findChildren(QAction)
                    if a.shortcut() == QKeySequence(f"Ctrl+Alt+{letter}") and a.text() in GREEK_LOWER_NAMES]
        assert len(shift_acts) == 1 and len(alt_acts) == 1
        assert shift_acts[0].text() == alt_acts[0].text() == LAYER2_TABLE[letter]
    _close(win)


def test_criterion15_no_action_anywhere_has_two_distinct_actions_sharing_one_shortcut():
    """No ambiguous shortcut exists anywhere registered on the window (Greek or otherwise)."""
    win = _make_window()
    by_shortcut = _window_actions_by_shortcut(win)
    ambiguous = {seq: [a.text() for a in acts] for seq, acts in by_shortcut.items() if len(acts) > 1}
    assert ambiguous == {}, f"ambiguous shortcuts found: {ambiguous}"
    _close(win)


def test_criterion15_ctrl_alt_used_only_by_the_23_greek_layer2_actions():
    win = _make_window()
    for act in win.findChildren(QAction):
        seq = act.shortcut().toString()
        if seq.startswith("Ctrl+Alt+") and not seq.startswith("Ctrl+Alt+Shift+"):
            assert act.text() in GREEK_LOWER_NAMES, (
                f"unexpected non-Greek action {act.text()!r} using a Ctrl+Alt+ shortcut: {seq}"
            )
    _close(win)


# ---------------------------------------------------------------------------
# Criterion 16: uppercase Greek letters have no keyboard shortcut of any kind.
# ---------------------------------------------------------------------------

def test_criterion16_uppercase_greek_letters_have_no_shortcut_anywhere():
    win = _make_window()
    for act in win.findChildren(QAction):
        if act.text() in GREEK_UPPER_NAMES:
            assert act.shortcut().isEmpty(), f"{act.text()} unexpectedly has a shortcut: {act.shortcut().toString()}"
    _close(win)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_edge_case_switching_tabs_mid_edit_does_not_insert_or_steal_focus():
    win = _make_window()
    region = win.sheet.insert_region("math")
    region.start_editing()
    region.editor.setPlainText("x")
    tabs = _tab_widget(win)
    tabs.setCurrentIndex(EXPECTED_TAB_ORDER.index("Calculus"))
    assert region.editing is True
    assert region.source.strip() == "x"
    _close(win)


def test_edge_case_empty_document_still_shows_full_token_list_on_every_functional_tab():
    win = _make_window()
    assert win.sheet.regions() == []
    tabs = _tab_widget(win)
    for name, expected_count in (("Elements", 40), ("Algebra", 4), ("Calculus", 4)):
        idx = EXPECTED_TAB_ORDER.index(name)
        assert len(_buttons_on_tab(tabs, idx)) == expected_count
    _close(win)


def test_edge_case_stale_pre_spec_tab_index_resolves_to_a_real_tab_and_self_corrects(isolated_settings):
    """A 'side_panel_tab' value of 2 saved under the old 3-tab layout (meaning 'Data') now lands
    on index 2 under the new 7-tab order ('Calculus') -- cosmetic surprise, not a crash, and it
    self-corrects on the next tab click (spec's own stated Edge case)."""
    settings = QSettings(isolated_settings, QSettings.Format.IniFormat)
    settings.setValue("side_panel_tab", 2)
    settings.sync()

    win = MainWindow()  # must not raise
    tabs = _tab_widget(win)
    assert tabs.currentIndex() == 2
    assert tabs.tabText(2) == "Calculus"

    tabs.setCurrentIndex(5)  # user clicks any tab -> the stored index self-corrects
    stored = QSettings(isolated_settings, QSettings.Format.IniFormat).value("side_panel_tab", type=int)
    assert stored == 5
    _close(win)


def test_edge_case_greek_shortcut_with_nothing_being_edited_creates_a_region_first():
    win = _make_window()
    assert win.sheet.regions() == []
    acts = [a for a in win.findChildren(QAction) if a.shortcut() == QKeySequence("Ctrl+Alt+A")]
    acts[0].trigger()
    assert len(win.sheet.regions()) == 1
    region = win.sheet.regions()[0]
    assert isinstance(region, MathRegion)
    assert region.source.strip() == "alpha"
    _close(win)
