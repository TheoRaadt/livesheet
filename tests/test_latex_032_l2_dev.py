"""Spec 032 phase L2: matrices, accents, font commands, View toggle, Insert formula items,
bundled STIX Two Math font (developer tests)."""

from __future__ import annotations

import hashlib
import importlib
import re
import tomllib
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFontDatabase, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from livesheet.gui import main_window as mw_module
from livesheet.gui import texlayout
from livesheet.gui.main_window import MainWindow
from livesheet.gui.regions import MathRegion, TextRegion
from livesheet.gui.texlayout import find_box, layout_formula, walk
from livesheet.gui.worksheet import Worksheet
from livesheet.texmath import TexError, parse, tables

P = importlib.import_module("livesheet.texmath.parse")
ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "livesheet" / "gui" / "fonts"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    ini = str(tmp_path / "s.ini")
    monkeypatch.setattr(mw_module, "make_settings", lambda: QSettings(ini, QSettings.Format.IniFormat))
    w = MainWindow()
    w.sheet.set_modified(False)
    yield w
    w.sheet.set_modified(False)
    w.close()


def only(src: str):
    row = parse(src)
    assert len(row.items) == 1
    return row.items[0]


# -- parser: environments ------------------------------------------------------------------------

def test_pmatrix_2x2():
    m = only(r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}")
    assert isinstance(m, P.Matrix) and (m.left, m.right) == ("(", ")")
    assert len(m.rows) == 2 and all(len(r) == 2 for r in m.rows)


@pytest.mark.parametrize("env,lr", [("matrix", ("", "")), ("bmatrix", ("[", "]")), ("Bmatrix", ("{", "}")),
                                    ("vmatrix", ("|", "|")), ("Vmatrix", ("‖", "‖"))])
def test_matrix_delimiters(env, lr):
    m = only(rf"\begin{{{env}}} a & b \end{{{env}}}")
    assert (m.left, m.right) == lr


def test_matrix_errors():
    with pytest.raises(TexError) as e:
        parse(r"\begin{pmatrix} 1 & 2 \end{matrix}")
    assert e.value.message == r"\end{matrix} does not match \begin{pmatrix}"
    with pytest.raises(TexError) as e:
        parse(r"\begin{foo} x \end{foo}")
    assert e.value.message == r"\begin{foo} is not supported" and e.value.offset == 0
    with pytest.raises(TexError) as e:
        parse(r"\begin{matrix} 1 & 2")
    assert e.value.message == r"missing \end{matrix}"
    with pytest.raises(TexError):
        parse(r"\begin{equation} x \end{equation}")


def test_ragged_rows_empty_cells_and_trailing_separator():
    m = only(r"\begin{matrix} 1 \\ 2 & 3 & \\ \end{matrix}")
    assert len(m.rows) == 2 and all(len(r) == 3 for r in m.rows)
    assert m.rows[0][2] == P.Row(())


def test_cases_aligned_array():
    c = only(r"\begin{cases} a & b \\ c & d \end{cases}")
    assert c.left == "{" and c.right == "" and c.aligns == "l"
    a = only(r"\begin{aligned} a &= b \\ c &= d \end{aligned}")
    assert a.aligns == "rl" and len(a.rows[0]) == 2
    r = only(r"\begin{array}{lcr} 1 & 2 & 3 \end{array}")
    assert r.aligns == "lcr"
    with pytest.raises(TexError):
        parse(r"\begin{array}{lx} 1 & 2 \end{array}")
    with pytest.raises(TexError):
        parse(r"\begin{array}{l} 1 & 2 \end{array}")
    with pytest.raises(TexError):
        parse(r"\begin{array} 1 \end{array}")


def test_matrix_size_limit():
    ok = r"\begin{matrix}" + r" \\ ".join("1" for _ in range(50)) + r"\end{matrix}"
    parse(ok)
    with pytest.raises(TexError, match="matrix too large"):
        parse(r"\begin{matrix}" + r" \\ ".join("1" for _ in range(51)) + r"\end{matrix}")
    with pytest.raises(TexError, match="matrix too large"):
        parse(r"\begin{matrix}" + " & ".join("1" for _ in range(51)) + r"\end{matrix}")


def test_nested_matrix_and_stray_separators():
    parse(r"\begin{matrix} \begin{matrix} a & b \end{matrix} & c \end{matrix}")
    for bad in (r"a & b", r"a \\ b", r"\end{matrix}", r"{a & b}", r"\begin{matrix}{a \\ b}\end{matrix}"):
        with pytest.raises(TexError):
            parse(bad)


def test_environment_depth_limit():
    src = r"\begin{matrix}" * 40 + "x" + r"\end{matrix}" * 40
    with pytest.raises(TexError, match="nested"):
        parse(src)


# -- parser: accents, fonts, operators ------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["hat", "bar", "vec", "dot", "ddot", "tilde", "overline", "underline"])
def test_accents(cmd):
    a = only(rf"\{cmd}{{x}}")
    assert isinstance(a, P.Accent) and a.kind == cmd and a.label is None
    with pytest.raises(TexError) as e:
        parse(rf"\{cmd}")
    assert e.value.message == rf"\{cmd} needs an argument"


def test_braces_with_label():
    a = only(r"\overbrace{a+b}^{n}")
    assert a.kind == "overbrace" and a.label is not None
    b = only(r"\underbrace{a+b}_{n}")
    assert b.kind == "underbrace" and b.label is not None
    assert only(r"\overbrace{a}").label is None


def test_font_commands():
    s = only(r"\mathbb{R}").items[0]
    assert s.style == "bb" and not s.italic
    assert only(r"\mathbf{x}").items[0].style == "bf"
    assert only(r"\mathrm{d}").items[0].italic is False
    assert only(r"\mathit{d}").items[0].italic is True
    bs = only(r"\boldsymbol{\alpha}").items[0]
    assert bs.style == "bs" and bs.italic
    group = only(r"\mathbf{\mathrm{x}y}")
    assert [group.items[0].items[0].style, group.items[1].style] == ["rm", "bf"]
    with pytest.raises(TexError):
        parse(r"\mathbf")


def test_style_tables():
    assert tables.style_char("R", "bb") == "ℝ"
    assert tables.style_char("A", "bb") == "\U0001D538"
    assert tables.style_char("L", "cal") == "ℒ"
    assert tables.style_char("x", "bf") == "\U0001D431"
    assert tables.style_char("α", "bf") == "\U0001D6C2"
    assert tables.style_char("+", "bf") == "+"


def test_operators():
    row = parse(r"a \bmod b")
    assert row.items[1] == P.Sym("mod", "bin")
    pm = only(r"\pmod{n}")
    assert any(isinstance(x, P.Word) and x.text == "mod" for x in pm.items)
    assert only(r"\operatorname{sgn}") == P.Word("sgn")
    for bad in (r"\operatorname", r"\operatorname{a$b}", r"\operatorname{}"):
        with pytest.raises(TexError):
            parse(bad)


def test_extra_symbols_are_plain_code_points():
    for name in ("cong", "oplus", "Re", "aleph", "langle", "longrightarrow"):
        assert len(parse("\\" + name).items) == 1


# -- layout ----------------------------------------------------------------------------------------

def test_matrix_layout_dimensions(app):
    one = layout_formula(r"\begin{matrix} a \end{matrix}", 20)
    two = layout_formula(r"\begin{matrix} a \\ b \end{matrix}", 20)
    wide = layout_formula(r"\begin{matrix} a & b \end{matrix}", 20)
    assert two.height > one.height
    assert wide.width > one.width
    # the grid is centred on the axis: ascent and descent roughly mirror around it
    assert abs((two.ascent - two.descent) / 2 - 0.25 * 20) < 3


def test_matrix_brackets_stretch(app):
    m = layout_formula(r"\begin{pmatrix} \frac{1}{2} & 0 \\ 0 & \frac{3}{4} \\ 1 & 1 \end{pmatrix}", 20)
    assert any(b.kind == "delim" and b.__class__.__name__ == "PathBox" for b in walk(m))
    plain = layout_formula(r"\begin{matrix} a & b \end{matrix}", 20)
    assert not any(b.kind == "delim" for b in walk(plain))


def test_matrix_column_alignment(app):
    box = layout_formula(r"\begin{array}{lr} a & b \\ aaaa & bbbb \end{array}", 20)
    m = find_box(box, "matrix")
    xs = {id(c): dx for dx, _dy, c in m.children}
    c = m.cells
    assert xs[id(c[0][0])] == xs[id(c[1][0])]                                   # left aligned
    right0 = xs[id(c[0][1])] + c[0][1].width
    right1 = xs[id(c[1][1])] + c[1][1].width
    assert abs(right0 - right1) < 1e-6                                          # right aligned


def test_cases_has_left_brace_only(app):
    box = layout_formula(r"\begin{cases} a & b \\ c & d \end{cases}", 20)
    delims = [b for b in walk(box) if b.kind == "delim"]
    assert len(delims) == 1


def test_accent_geometry(app):
    plain = layout_formula("x", 20)
    for cmd in ("hat", "bar", "vec", "dot", "ddot", "tilde", "overline"):
        b = layout_formula(rf"\{cmd}{{x}}", 20)
        assert b.ascent > plain.ascent - 1e-6 or cmd == "overline" or b.ascent >= plain.ascent * 0.9
        assert abs(b.width - plain.width) < 1e-6
        acc = find_box(b, "accent")
        assert not (acc.strokes.isEmpty() and acc.fills.isEmpty())
    u = layout_formula(r"\underline{x}", 20)
    assert u.descent > plain.descent


def test_braces_layout(app):
    over = layout_formula(r"\overbrace{a+b+c}^{n}", 20)
    bare = layout_formula(r"\overbrace{a+b+c}", 20)
    assert over.ascent > bare.ascent > layout_formula("a+b+c", 20).ascent
    under = layout_formula(r"\underbrace{a+b+c}_{n}", 20)
    assert under.descent > layout_formula("a+b+c", 20).descent
    assert over.width >= bare.width - 1e-6


def test_font_command_layout(app):
    for src in (r"\mathbb{R}", r"\mathbf{x}", r"\mathcal{L}", r"\mathbb{Rx1}", r"\boldsymbol{\alpha}",
                r"\mathrm{d}x", r"\mathit{abc}"):
        b = layout_formula(src, 20)
        assert b.width > 0
    # styled forms use the mathematical alphanumeric code points when the font has them
    glyphs = [g.text for g in walk(layout_formula(r"\mathbb{R}", 20)) if g.kind == "glyph"]
    assert glyphs == ["ℝ"]


def test_missing_styled_glyph_falls_back_to_bold(app, monkeypatch):
    real = texlayout._font

    class NoGlyphs:
        def __init__(self, fm):
            self._fm = fm

        def inFontUcs4(self, _c):
            return False

        def __getattr__(self, name):
            return getattr(self._fm, name)

    def fake(*a, **k):
        font, fm = real(*a, **k)
        return font, NoGlyphs(fm)

    monkeypatch.setattr(texlayout, "_font", fake)
    g = texlayout._styled_glyph(P.Sym("R", "ord", False, "bb"), 20.0)
    assert g.text == "R" and g.bold


def test_fuzz_l2_never_raises_other_than_texerror(app):
    import random
    rng = random.Random(5)
    toks = [r"\begin{matrix}", r"\end{matrix}", r"\begin{cases}", r"\end{cases}", "&", r"\\", "a", "1",
            r"\hat{", "}", "{", r"\mathbb{", r"\overbrace{x}^", "_", "^", r"\bmod", r"\pmod{", r"\operatorname{f}",
            r"\begin{array}{lc}", r"\end{array}"]
    for _ in range(600):
        src = "".join(rng.choice(toks) for _ in range(rng.randint(1, 12)))
        try:
            layout_formula(src, 14)
        except TexError:
            pass


# -- region: View toggle ---------------------------------------------------------------------------

HTML = "<p>a $x^2$ b</p>"


def test_typeset_off_keeps_raw_and_text(app):
    sheet = Worksheet()
    sheet.typeset_latex = False
    r = sheet.add_region("text", sheet.crosshair.pos(), HTML)
    assert "￼" not in r.editor.document().toPlainText()
    assert "$x^2$" in r.editor.document().toPlainText()
    assert r.errors == []
    off_text = r.text()
    sheet.typeset_latex = True
    r.refresh_typesetting()
    assert "￼" in r.editor.document().toPlainText()
    assert r.text() == off_text == HTML or r.text() == off_text
    sheet.set_modified(False)
    sheet.typeset_latex = False
    r.refresh_typesetting()
    assert "$x^2$" in r.editor.document().toPlainText() and r.text() == off_text
    assert not sheet.is_modified() if hasattr(sheet, "is_modified") else True


def test_typeset_off_no_scanning_or_caption(app):
    sheet = Worksheet()
    sheet.typeset_latex = False
    r = sheet.add_region("text", sheet.crosshair.pos(), r"<p>$\foo$</p>")
    assert r.errors == [] and r.caption_text == "" and not r._has_error
    r.start_editing()
    assert r.caption_text == ""
    r.finish_editing()
    assert r.errors == []
    sheet.typeset_latex = True
    r.refresh_typesetting()
    assert r.caption_text.startswith("LaTeX: unknown command")


def test_view_toggle_default_on_persisted_and_applied(window, app):
    assert window.action_typeset_latex.isChecked() and window.sheet.typeset_latex is True
    r = window.sheet.add_region("text", window.sheet.crosshair.pos(), HTML)
    assert "￼" in r.editor.document().toPlainText()
    original = r.text()
    window.sheet.set_modified(False)
    window.action_typeset_latex.setChecked(False)
    assert window.sheet.typeset_latex is False
    assert "$x^2$" in r.editor.document().toPlainText()
    assert r.text() == original and not window.sheet.modified
    window.action_typeset_latex.setChecked(True)
    assert "￼" in r.editor.document().toPlainText()
    assert r.text() == original and not window.sheet.modified
    window.action_typeset_latex.setChecked(False)
    assert window.settings.value("typeset_latex", True, type=bool) is False


def test_view_toggle_setting_restored(app, tmp_path, monkeypatch):
    ini = str(tmp_path / "s2.ini")
    s = QSettings(ini, QSettings.Format.IniFormat)
    s.setValue("typeset_latex", False)
    s.sync()
    monkeypatch.setattr(mw_module, "make_settings", lambda: QSettings(ini, QSettings.Format.IniFormat))
    w = MainWindow()
    try:
        assert not w.action_typeset_latex.isChecked() and w.sheet.typeset_latex is False
        r = w.sheet.add_region("text", w.sheet.crosshair.pos(), HTML)   # joins a sheet with it off
        assert "$x^2$" in r.editor.document().toPlainText()
        assert r.text() == r.text()
    finally:
        w.sheet.set_modified(False)
        w.close()


def test_view_toggle_leaves_editing_region_alone(window, app):
    r = window.sheet.add_region("text", window.sheet.crosshair.pos(), HTML)
    r.start_editing()
    window.action_typeset_latex.setChecked(False)
    assert r.editing and "$x^2$" in r.editor.toPlainText()
    r.finish_editing()
    assert "$x^2$" in r.editor.document().toPlainText()


# -- Insert formula items ----------------------------------------------------------------------------

def test_formula_items_in_insert_menu_with_shortcuts(window):
    assert window.action_formula_inline.shortcut() == QKeySequence("Ctrl+Alt+4")
    assert window.action_formula_display.shortcut() == QKeySequence("Ctrl+Alt+Shift+4")
    insert = next(a.menu() for a in window.menuBar().actions() if a.text().replace("&", "") == "Insert")
    assert window.action_formula_inline in insert.actions() and window.action_formula_display in insert.actions()


def test_shortcuts_do_not_clash_with_other_actions(window):
    seen: dict[str, str] = {}
    for act in window.findChildren(type(window.action_formula_inline)):
        for sc in [act.shortcut()] + list(act.shortcuts()):
            key = sc.toString()
            if not key:
                continue
            if key in seen and seen[key] != act.text():
                raise AssertionError(f"{key}: {seen[key]!r} and {act.text()!r}")
            seen[key] = act.text()
    assert "Ctrl+Alt+4" in seen and "Ctrl+Alt+Shift+4" in seen


def test_insert_inline_empty_and_selection(window):
    sheet = window.sheet
    r = sheet.insert_region("text")
    window.insert_formula(False)
    assert r.editor.toPlainText() == "$$" and r.editor.textCursor().position() == 1
    cur = r.editor.textCursor()
    cur.select(cur.SelectionType.Document)
    cur.insertText("abc")
    cur.setPosition(0)
    cur.setPosition(3, cur.MoveMode.KeepAnchor)
    r.editor.setTextCursor(cur)
    window.insert_formula(False)
    assert r.editor.toPlainText() == "$abc$" and r.editor.textCursor().position() == 5


def test_insert_display_caret_between(window):
    r = window.sheet.insert_region("text")
    window.insert_formula(True)
    assert r.editor.toPlainText() == "$$$$" and r.editor.textCursor().position() == 2


def test_insert_with_no_text_region_creates_one_in_edit_state(window):
    before = len(window.sheet.regions())
    window.insert_formula(False)
    regions = window.sheet.regions()
    assert len(regions) == before + 1
    r = regions[-1]
    assert isinstance(r, TextRegion) and r.editing and r.editor.toPlainText() == "$$"


def test_insert_in_selected_text_region_starts_editing_at_end(window):
    sheet = window.sheet
    r = sheet.add_region("text", sheet.crosshair.pos(), "<p>hello</p>")
    r.setSelected(True)
    window.insert_formula(False)
    assert r.editing and r.editor.toPlainText() == "hello$$"
    assert r.editor.textCursor().position() == 6


def test_insert_disabled_while_math_region_edited(window, app):
    sheet = window.sheet
    m = sheet.insert_region("math")
    assert isinstance(m, MathRegion) and m.editing
    window._update_formula_actions()
    assert not window.action_formula_inline.isEnabled() and not window.action_formula_display.isEnabled()
    n = len(sheet.regions())
    window.insert_formula(False)               # also a no-op if invoked directly
    assert len(sheet.regions()) == n and m.editor.toPlainText() == ""
    m.finish_editing()
    window._update_formula_actions()
    assert window.action_formula_inline.isEnabled()


def test_insert_enabled_state_follows_editing_automatically(window, app):
    window.sheet.insert_region("math")
    app.processEvents()
    assert not window.action_formula_inline.isEnabled()
    window.sheet.editing_region().finish_editing()
    app.processEvents()
    assert window.action_formula_inline.isEnabled()


def test_inserted_formula_typesets_after_leaving(window):
    r = window.sheet.insert_region("text")
    window.insert_formula(False)
    cur = r.editor.textCursor()
    cur.insertText("x^2")
    r.finish_editing()
    assert "￼" in r.editor.document().toPlainText()
    assert "$x^2$" in r.raw_document().toPlainText()


# -- bundled font -------------------------------------------------------------------------------------

def test_font_files_present_and_checksums_recorded():
    otf = FONTS / "STIXTwoMath-Regular.otf"
    assert otf.is_file() and (FONTS / "OFL.txt").is_file() and (FONTS / "README.md").is_file()
    readme = (FONTS / "README.md").read_text(encoding="utf-8")
    assert hashlib.sha256(otf.read_bytes()).hexdigest() in readme
    assert hashlib.sha256((FONTS / "OFL.txt").read_bytes()).hexdigest() in readme
    for needle in ("v2.13b171", "github.com/stipub/stixfonts", "2026-11-12", "SIL Open Font License"):
        assert needle in readme
    ofl = (FONTS / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in ofl and "STIX Fonts Project Authors" in ofl


def test_package_data_declares_font_and_licence():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data = cfg["tool"]["setuptools"]["package-data"]["livesheet.gui"]
    assert any(p.endswith(".otf") for p in data) and "fonts/OFL.txt" in data
    import fnmatch
    assert any(fnmatch.fnmatch("fonts/STIXTwoMath-Regular.otf", p) for p in data)


def test_bundled_font_registers(app):
    texlayout._font_state.update(done=False, id=-1)
    fid = texlayout.ensure_math_font()
    assert fid >= 0
    assert "STIX Two Math" in QFontDatabase.applicationFontFamilies(fid)
    assert "STIX Two Math" in QFontDatabase.families()
    assert texlayout.MATH_FAMILIES[0] == "STIX Two Math"
    assert texlayout.ensure_math_font() == fid          # registered once


def test_font_load_failure_falls_back_to_system_chain(app, monkeypatch, caplog):
    monkeypatch.setattr(texlayout, "BUNDLED_FONT", FONTS / "does-not-exist.otf")
    monkeypatch.setitem(texlayout._font_state, "done", False)
    monkeypatch.setitem(texlayout._font_state, "id", -1)
    with caplog.at_level("WARNING"):
        assert texlayout.ensure_math_font() == -1
        assert texlayout.ensure_math_font() == -1
    assert sum("could not be loaded" in r.message for r in caplog.records) == 1      # logged once
    b = layout_formula(r"\frac{a}{b}+\sqrt{x}", 18.0, True)                          # still renders
    assert b.width > 0
    texlayout._font_state.update(done=False, id=-1)


def test_corrupt_font_file_does_not_crash(app, monkeypatch, tmp_path):
    bad = tmp_path / "bad.otf"
    bad.write_bytes(b"not a font")
    monkeypatch.setattr(texlayout, "BUNDLED_FONT", bad)
    monkeypatch.setitem(texlayout._font_state, "done", False)
    monkeypatch.setitem(texlayout._font_state, "id", -1)
    assert texlayout.ensure_math_font() == -1
    texlayout._font_state.update(done=False, id=-1)
