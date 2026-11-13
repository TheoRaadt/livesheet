"""Spec 032 phase L2, independent black-box review (matrices, accents, font commands, View
toggle, Insert formula items, bundled STIX Two Math font). Written from the spec only."""

from __future__ import annotations

import hashlib
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase, QKeySequence, QRawFont, QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.texmath import TexError, parse, scan  # noqa: E402
from livesheet.texmath import parse as parse_mod  # noqa: E402
from livesheet.texmath import tables  # noqa: E402

P = sys.modules["livesheet.texmath.parse"]
ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "livesheet" / "gui" / "fonts"
OBJ = "￼"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def err(src):
    with pytest.raises(TexError) as ei:
        parse(src)
    return ei.value


# ============================== parser: environments (criterion 14) ===========================

ENVS = {"matrix": ("", ""), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
        "Bmatrix": ("{", "}"), "vmatrix": ("|", "|")}


@pytest.mark.parametrize("env,delims", list(ENVS.items()))
def test_matrix_envs_delimiters(env, delims):
    m = parse(rf"\begin{{{env}}} 1 & 2 \\ 3 & 4 \end{{{env}}}").items[0]
    assert (m.left, m.right) == delims
    assert len(m.rows) == 2 and all(len(r) == 2 for r in m.rows)


def test_Vmatrix_double_bar():
    m = parse(r"\begin{Vmatrix} a \end{Vmatrix}").items[0]
    assert m.left == m.right and m.left in ("‖", "∥", "||")


def test_ragged_rows_padded_and_empty_cells():
    m = parse(r"\begin{matrix} 1 & 2 & 3 \\ 4 \\ & 5 \end{matrix}").items[0]
    assert [len(r) for r in m.rows] == [3, 3, 3]
    assert m.rows[2][0].items == ()          # empty cell allowed


def test_trailing_row_separator_not_a_row():
    m = parse(r"\begin{matrix} 1 \\ 2 \\ \end{matrix}").items[0]
    assert len(m.rows) == 2


def test_mismatch_error():
    e = err(r"\begin{pmatrix} 1 & 2 \end{matrix}")
    assert e.message == r"\end{matrix} does not match \begin{pmatrix}"


def test_unsupported_env_error():
    assert err(r"\begin{foo} x \end{foo}").message == r"\begin{foo} is not supported"


@pytest.mark.parametrize("env", ["equation", "align", "table", "tabular", "gather"])
def test_wrapper_envs_unsupported(env):
    assert err(rf"\begin{{{env}}} x \end{{{env}}}").message == rf"\begin{{{env}}} is not supported"


def test_missing_end():
    assert err(r"\begin{matrix} 1 & 2").message == r"missing \end{matrix}"


def test_stray_end_and_amp_outside_env():
    assert err(r"x \end{matrix}").message
    assert err("a & b").message           # & outside an environment is an error, not ignored


def test_nested_matrices_ok():
    parse(r"\begin{pmatrix} \begin{pmatrix} 1 \end{pmatrix} & 2 \end{pmatrix}")


def test_matrix_limit_50_by_50():
    ok = r"\begin{matrix}" + "&".join("1" * 1 for _ in range(50)) + r"\end{matrix}"
    parse(ok)
    wide = r"\begin{matrix}" + "&".join("1" for _ in range(51)) + r"\end{matrix}"
    tall = r"\begin{matrix}" + r"\\".join("1" for _ in range(51)) + r"\end{matrix}"
    for s in (wide, tall):
        err(s)
    parse(r"\begin{matrix}" + r"\\".join("1" for _ in range(50)) + r"\end{matrix}")


def test_nesting_limit_envs_no_recursion_error():
    deep = r"\begin{matrix}" * 40 + "1" + r"\end{matrix}" * 40
    e = err(deep)
    assert "nested" in e.message and "32" in e.message
    err("{" * 40 + "x" + "}" * 40)


def test_cases_aligned_array():
    c = parse(r"\begin{cases} x & y \\ z & w \end{cases}").items[0]
    assert c.left == "{" and c.right == "" and len(c.rows[0]) == 2
    a = parse(r"\begin{aligned} a &= b \\ c &= d \end{aligned}").items[0]
    assert a.aligns.startswith("rl")
    r = parse(r"\begin{array}{lcr} 1 & 2 & 3 \end{array}").items[0]
    assert r.aligns == "lcr"


@pytest.mark.parametrize("src", [r"\begin{array}{lx} 1&2 \end{array}",
                                 r"\begin{array}{|l|} 1 \end{array}",
                                 r"\begin{array} 1 \end{array}"])
def test_array_bad_column_spec(src):
    err(src)


def test_array_too_many_cells():
    err(r"\begin{array}{l} 1 & 2 \end{array}")


# ============================== parser: accents, fonts, operators =============================

ACC = "hat bar vec dot ddot tilde overline underline overbrace underbrace".split()


@pytest.mark.parametrize("name", ACC)
def test_accent_parses_and_needs_arg(name):
    node = parse(rf"\{name}{{x+y}}").items[0]
    assert isinstance(node, P.Accent) and node.kind == name
    assert err(rf"\{name}").message == rf"\{name} needs an argument"


@pytest.mark.parametrize("name,mark", [("overbrace", "^"), ("underbrace", "_")])
def test_brace_label(name, mark):
    node = parse(rf"\{name}{{a+b}}{mark}{{n}}").items[0]
    assert isinstance(node, P.Accent) and node.label is not None


def test_accent_then_script():
    s = parse(r"\hat{x}^2").items[0]
    assert isinstance(s, P.Script) and isinstance(s.base, P.Accent)


@pytest.mark.parametrize("cmd", ["mathrm", "mathbf", "mathit", "mathbb", "mathcal", "boldsymbol"])
@pytest.mark.parametrize("ch", list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcxyz0189"))
def test_font_commands_never_error(cmd, ch):
    parse(rf"\{cmd}{{{ch}}}")


def test_font_command_missing_arg():
    assert err(r"\mathbf").message == r"\mathbf needs an argument"


def test_font_command_over_structure():
    parse(r"\mathbf{\frac{a}{b}}")
    parse(r"\boldsymbol{\alpha} + \mathcal{L}")


def test_bmod_pmod_operatorname():
    parse(r"a \bmod b")
    parse(r"a \equiv b \pmod{n}")
    parse(r"\operatorname{rank} A")
    assert err(r"\pmod").message
    assert err(r"\operatorname").message
    err(r"\operatorname{}")


def test_still_unsupported_after_l2():
    for cmd in ["newcommand", "color", "usepackage", "label", "def", "verb", "href"]:
        assert err(rf"\{cmd}{{a}}").message == rf"unsupported: \{cmd}"


def test_l1_errors_unchanged():
    assert err(r"\foo").message == r"unknown command \foo"
    assert err(r"\frac{1}").message == r"\frac needs two arguments"
    assert err("{").message == "missing closing }"
    assert err("x^2^3").message == "double superscript"


def test_texmath_package_is_qt_free():
    code = ("import sys, livesheet.texmath as t; t.parse(r'\\begin{pmatrix}1\\end{pmatrix}');"
            "sys.exit(any(m.startswith('PySide6') for m in sys.modules))")
    assert subprocess.run([sys.executable, "-c", code], cwd=ROOT).returncode == 0


# ============================== scanner interplay with L2 =====================================

def test_matrix_across_lines_in_display_span():
    t = "$$\\begin{pmatrix}\n1 & 2 \\\\\n3 & 4\n\\end{pmatrix}$$"
    sp = scan(t).spans
    assert len(sp) == 1 and sp[0].display


def test_inline_matrix_with_dollar_free_content():
    assert len(scan(r"see $\begin{bmatrix}1&2\end{bmatrix}$ ok").spans) == 1


# ============================== layout ========================================================

@pytest.fixture
def lay(app):
    from livesheet.gui import texlayout
    return texlayout


def boxes(box, kind=None):
    out = [box] + [b for _x, _y, b in box.children]
    res = []
    stack = [box]
    while stack:
        b = stack.pop()
        res.append(b)
        stack += [c for _x, _y, c in b.children]
    return [b for b in res if kind is None or b.kind == kind]


def glyph_texts(box):
    return [b.text for b in boxes(box, "glyph")]


def test_matrix_layout_geometry(lay):
    plain = lay.layout_formula(r"\begin{matrix} 1 & 2 \\ 3 & 4 \end{matrix}", 16, True)
    paren = lay.layout_formula(r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}", 16, True)
    one = lay.layout_formula("1", 16, True)
    assert plain.width >= 2 * one.width
    assert plain.height > 1.6 * one.height          # two rows
    assert paren.width > plain.width                # brackets add width
    assert paren.height >= plain.height - 1e-6
    m = lay.find_box(plain, "matrix")
    ys = sorted({round(dy, 3) for dx, dy, c in m.children})
    assert len(ys) == 2 and ys[0] < ys[1]
    xs = sorted({round(dx, 3) for dx, dy, c in m.children})
    assert len(xs) == 2 and xs[0] < xs[1]


def test_matrix_rows_do_not_overlap(lay):
    m = lay.find_box(lay.layout_formula(
        r"\begin{matrix} \frac{a}{b} \\ \frac{c}{d} \\ x \end{matrix}", 16, True), "matrix")
    cells = sorted(m.children, key=lambda t: t[1])
    for (_x1, y1, b1), (_x2, y2, b2) in zip(cells, cells[1:]):
        if y2 > y1 + 1e-6:
            assert y1 + b1.descent <= y2 - b2.ascent + 1e-6


def test_matrix_centred_on_axis(lay):
    box = lay.layout_formula(r"\begin{matrix} a \\ b \\ c \end{matrix}", 20, True)
    # centred: ascent and descent within 25% of each other
    assert abs(box.ascent - box.descent) < 0.25 * box.height


def test_tall_matrix_stretches_brackets_as_paths(lay):
    box = lay.layout_formula(r"\begin{bmatrix} 1 \\ 2 \\ 3 \\ 4 \end{bmatrix}", 16, True)
    ds = boxes(box, "delim")
    assert len(ds) == 2 and all(d.height >= 0.9 * (box.height) - 1 for d in ds)


def test_cases_left_aligned_columns_and_brace(lay):
    box = lay.layout_formula(r"\begin{cases} i & x \\ mmmmm & yy \end{cases}", 16, True)
    m = lay.find_box(box, "matrix")
    cells = [(dx, dy, c) for dx, dy, c in m.children if c.kind != "delim"]
    col0 = [(dx, dy, c) for dx, dy, c in cells if dx < 30 or True]
    by_row = {}
    for dx, dy, c in cells:
        by_row.setdefault(round(dy, 2), []).append((dx, c))
    rows = [sorted(v, key=lambda t: t[0]) for _k, v in sorted(by_row.items())]
    assert abs(rows[0][0][0] - rows[1][0][0]) < 0.01          # first column left edges equal
    assert boxes(box, "delim"), "cases has a left brace"
    assert col0


def test_aligned_right_then_left(lay):
    m = lay.find_box(lay.layout_formula(
        r"\begin{aligned} i &= x \\ mmmmm &= yy \end{aligned}", 16, True), "matrix")
    by_row = {}
    for dx, dy, c in m.children:
        by_row.setdefault(round(dy, 2), []).append((dx, c))
    rows = [sorted(v, key=lambda t: t[0]) for _k, v in sorted(by_row.items())]
    r0, r1 = rows
    right0 = r0[0][0] + r0[0][1].width
    right1 = r1[0][0] + r1[0][1].width
    assert abs(right0 - right1) < 0.01            # column 1 right-aligned
    assert abs(r0[1][0] - r1[1][0]) < 0.01        # column 2 left-aligned
    assert r0[0][1].width < r1[0][1].width


@pytest.mark.parametrize("mode", "lcr")
def test_array_alignment(lay, mode):
    m = lay.find_box(lay.layout_formula(
        rf"\begin{{array}}{{{mode}}} i \\ mmmmm \end{{array}}", 16, True), "matrix")
    cells = sorted(m.children, key=lambda t: t[1])
    (x0, _y0, b0), (x1, _y1, b1) = cells[0], cells[1]
    assert b0.width < b1.width
    if mode == "l":
        assert abs(x0 - x1) < 0.01
    elif mode == "r":
        assert abs((x0 + b0.width) - (x1 + b1.width)) < 0.01
    else:
        assert abs((x0 + b0.width / 2) - (x1 + b1.width / 2)) < 0.01


def test_accent_geometry(lay):
    base = lay.layout_formula("x", 20)
    hat = lay.layout_formula(r"\hat{x}", 20)
    und = lay.layout_formula(r"\underline{x}", 20)
    ovl = lay.layout_formula(r"\overline{x}", 20)
    assert ovl.ascent > base.ascent
    mark = lay.find_box(hat, "accent").strokes.boundingRect()
    xg = [b for b in boxes(hat, "glyph")][0]
    assert mark.bottom() < -xg.ink_ascent() + 1e-6        # mark sits above the letter's ink
    assert mark.top() >= -hat.ascent - 1e-6               # and inside the formula box
    assert und.descent > base.descent
    assert abs(hat.width - base.width) < 0.5 * base.width + 1
    wide = lay.layout_formula(r"\overline{abcdef}", 20)
    inner = lay.layout_formula("abcdef", 20)
    assert wide.width >= inner.width - 1e-6
    assert lay.find_box(hat, "accent") is not None


def test_braces_with_labels(lay):
    body = lay.layout_formula("a+b+c", 20)
    ob = lay.layout_formula(r"\overbrace{a+b+c}", 20)
    obl = lay.layout_formula(r"\overbrace{a+b+c}^{n}", 20)
    ub = lay.layout_formula(r"\underbrace{a+b+c}", 20)
    ubl = lay.layout_formula(r"\underbrace{a+b+c}_{n}", 20)
    assert ob.ascent > body.ascent and obl.ascent > ob.ascent
    assert ub.descent > body.descent and ubl.descent > ub.descent
    assert ob.width >= body.width - 1e-6


def test_font_command_glyphs(lay):
    assert "ℝ" in glyph_texts(lay.layout_formula(r"\mathbb{R}", 16))
    g = [b for b in boxes(lay.layout_formula(r"\mathrm{d}", 16), "glyph")]
    assert g and not any(b.italic for b in g)
    assert any(b.italic for b in boxes(lay.layout_formula("d", 16), "glyph"))
    cal = glyph_texts(lay.layout_formula(r"\mathcal{L}", 16))
    assert cal and cal != ["L"]                     # script capital, not the plain letter
    bf = lay.layout_formula(r"\mathbf{x}", 16)
    gl = boxes(bf, "glyph")
    assert gl and (any(b.bold for b in gl) or glyph_texts(bf) != ["x"])


@pytest.mark.parametrize("cmd", ["mathrm", "mathbf", "mathit", "mathbb", "mathcal", "boldsymbol"])
def test_font_commands_layout_all_letters(lay, cmd):
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
        b = lay.layout_formula(rf"\{cmd}{{{ch}}}", 16)
        assert b.width > 0


def test_operatorname_upright_and_mod(lay):
    b = lay.layout_formula(r"\operatorname{rank} A", 16)
    assert not any(g.italic for g in boxes(b, "glyph") if "rank" in g.text)
    assert lay.layout_formula(r"a \bmod b", 16).width > lay.layout_formula("a b", 16).width
    assert lay.layout_formula(r"a \pmod{n}", 16).width > lay.layout_formula("a n", 16).width


@pytest.mark.parametrize("src", [
    r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}",
    r"\begin{cases} x & y \\ z & w \end{cases}",
    r"\overbrace{a+b}^{n} + \hat{x}",
    r"\mathbb{R}^{n \times m}",
])
def test_scale_ratio_within_5_percent(lay, src):
    a, b = lay.layout_formula(src, 12, True), lay.layout_formula(src, 24, True)
    assert b.width / a.width == pytest.approx(2.0, rel=0.05)


def test_scripts_on_matrix_and_inside_cells(lay):
    box = lay.layout_formula(r"\begin{pmatrix} x^2 & 1 \\ 0 & x_i \end{pmatrix}^T", 16, True)
    assert lay.find_box(box, "script") is not None
    plain = lay.layout_formula(r"\begin{pmatrix} x^2 & 1 \\ 0 & x_i \end{pmatrix}", 16, True)
    assert box.width > plain.width


def test_empty_matrix_and_cells_layout(lay):
    lay.layout_formula(r"\begin{matrix}\end{matrix}", 16)
    lay.layout_formula(r"\begin{matrix} & \\ & \end{matrix}", 16)


def test_fuzz_l2_tokens_only_texerror(lay):
    rnd = random.Random(2026)
    toks = [r"\begin{pmatrix}", r"\end{pmatrix}", r"\begin{cases}", r"\end{cases}", r"\begin{array}{lc}",
            r"\end{array}", r"\begin{aligned}", r"\end{aligned}", r"\hat", r"\overbrace", r"\underbrace",
            r"\mathbb", r"\mathcal", r"\mathbf", r"\boldsymbol", r"\operatorname", r"\pmod", r"\bmod",
            "{", "}", "^", "_", "&", r"\\", "a", "1", "x", r"\frac", r"\sqrt", r"\left(", r"\right)", " "]
    for _ in range(1500):
        s = "".join(rnd.choice(toks) for _ in range(rnd.randint(1, 14)))
        try:
            lay.layout_formula(s, 14, rnd.random() < 0.5)
        except TexError:
            pass


# ============================== bundled font (criterion 30) ===================================

def test_font_files_and_checksums(app):
    otf = FONT_DIR / "STIXTwoMath-Regular.otf"
    ofl = FONT_DIR / "OFL.txt"
    readme = (FONT_DIR / "README.md").read_text()
    assert otf.is_file() and ofl.is_file()
    assert otf.read_bytes()[:4] == b"OTTO"
    h = hashlib.sha256(otf.read_bytes()).hexdigest()
    assert h in readme
    assert hashlib.sha256(ofl.read_bytes()).hexdigest() in readme
    txt = ofl.read_text(errors="replace")
    assert "SIL OPEN FONT LICENSE Version 1.1" in txt and "STIX" in txt
    assert "Copyright" in txt


def test_font_registers_and_family_listed(app):
    from livesheet.gui import texlayout
    fid = texlayout.ensure_math_font()
    assert fid >= 0
    fam = QFontDatabase.applicationFontFamilies(fid)
    assert fam == ["STIX Two Math"]                # unmodified, not renamed
    assert "STIX Two Math" in QFontDatabase.families()
    assert texlayout.MATH_FAMILIES[0] == "STIX Two Math"
    assert "Times New Roman" in texlayout.MATH_FAMILIES or "serif" in texlayout.MATH_FAMILIES


def test_font_used_for_rendering(app):
    from PySide6.QtGui import QFontInfo
    from livesheet.gui import texlayout
    f, _fm = texlayout._font(20)
    assert QFontInfo(f).family() == "STIX Two Math"


def test_all_table_symbols_have_glyph_in_bundled_font(app):
    from livesheet.gui import texlayout
    texlayout.ensure_math_font()
    raw = QRawFont(str(FONT_DIR / "STIXTwoMath-Regular.otf"), 20)
    assert raw.isValid()
    missing = []
    for name, (text, _k) in tables.SYMBOLS.items():
        if text.strip() and not all(raw.supportsCharacter(ord(c)) for c in text if not c.isspace()):
            missing.append((name, text))
    assert not missing, missing[:20]


def test_font_failure_falls_back(app, monkeypatch):
    from livesheet.gui import texlayout as tl
    monkeypatch.setattr(tl, "BUNDLED_FONT", FONT_DIR / "does-not-exist.otf")
    monkeypatch.setattr(tl, "_font_state", {"done": False, "id": -1})
    monkeypatch.setattr(tl, "_FONTS", {})
    monkeypatch.setattr(tl, "_CACHE", type(tl._CACHE)())
    assert tl.ensure_math_font() == -1
    box = tl.layout_formula(r"\begin{pmatrix} \alpha & 1 \end{pmatrix}", 16)
    assert box.width > 0


def test_package_data_and_notice():
    py = (ROOT / "pyproject.toml").read_text()
    assert "fonts/*.otf" in py and "fonts/OFL.txt" in py
    notice = ""
    for n in ("README.md", "NOTICE", "NOTICE.md", "THIRD_PARTY_NOTICES.md"):
        p = ROOT / n
        if p.exists():
            notice += p.read_text()
    assert "STIX" in notice and re.search(r"OFL|Open Font License", notice)


# ============================== window: View toggle and Insert items ==========================

@pytest.fixture
def window(app, tmp_path, monkeypatch):
    from livesheet.gui import main_window as mw
    ini = str(tmp_path / "s.ini")
    monkeypatch.setattr(mw, "make_settings", lambda: QSettings(ini, QSettings.Format.IniFormat))
    w = mw.MainWindow()
    w.sheet.set_modified(False)
    w.ini = ini
    yield w
    w.sheet.set_modified(False)
    w.close()


def find_action(w, text_part):
    acts = [a for a in w.findChildren(type(w.menuBar().actions()[0])) if text_part in a.text().replace("&", "")]
    assert acts, text_part
    return acts[0]


def menu_of(w, title):
    for a in w.menuBar().actions():
        if a.text().replace("&", "") == title:
            return a.menu()
    raise AssertionError(title)


def n_obj(r):
    return r.editor.toPlainText().count(OBJ)


def test_view_toggle_exists_checked_by_default(window):
    acts = [a for a in menu_of(window, "View").actions() if "Typeset LaTeX in text regions" in a.text().replace("&", "")]
    assert len(acts) == 1 and acts[0].isCheckable() and acts[0].isChecked()


def test_insert_items_in_insert_menu_with_shortcuts(window):
    items = {a.text().replace("&", ""): a for a in menu_of(window, "Insert").actions()}
    a, b = items["Formula (inline)"], items["Formula (display)"]
    assert a.shortcut() == QKeySequence("Ctrl+Alt+4")
    assert b.shortcut() == QKeySequence("Ctrl+Alt+Shift+4")


def test_no_shortcut_collisions(window):
    seen = {}
    for act in window.findChildren(type(window.menuBar().actions()[0])):
        for sc in act.shortcuts() or ([act.shortcut()] if not act.shortcut().isEmpty() else []):
            key = sc.toString()
            if key:
                seen.setdefault(key, set()).add(act.text())
    for key in ("Ctrl+Alt+4", "Ctrl+Alt+Shift+4"):
        assert len(seen[key]) == 1, (key, seen[key])


def test_toggle_off_raw_text_unchanged_not_modified(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>a $x^2$ b</p>")
    sh.set_modified(False)
    before = r.text()
    assert n_obj(r) == 1
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    assert n_obj(r) == 0 and "$x^2$" in r.editor.toPlainText()
    assert r.text() == before and not sh.modified
    act.setChecked(True)
    assert n_obj(r) == 1 and r.text() == before and not sh.modified


def test_toggle_persisted_across_windows(window, monkeypatch):
    from livesheet.gui import main_window as mw
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    window.settings.sync()
    ini = window.ini
    monkeypatch.setattr(mw, "make_settings", lambda: QSettings(ini, QSettings.Format.IniFormat))
    w2 = mw.MainWindow()
    try:
        a2 = [a for a in menu_of(w2, "View").actions() if "Typeset" in a.text()][0]
        assert not a2.isChecked()
        r = w2.sheet.add_region("text", QPointF(40, 40), "<p>$x$</p>")
        assert n_obj(r) == 0                      # new regions respect the setting
    finally:
        w2.sheet.set_modified(False)
        w2.close()


def test_toggle_off_no_scanning_no_error(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>$\\foo$ and $x$</p>")
    assert r._has_error
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    assert not r._has_error and not r._caption.isVisible()
    assert n_obj(r) == 0


def test_toggle_off_edit_cycle_text_stable(window):
    sh = window.sheet
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    r = sh.add_region("text", QPointF(40, 40), "<p>a $x^2$ b</p>")
    sh.set_modified(False)
    t = r.text()
    r.start_editing(); r.finish_editing()
    assert r.text() == t and not sh.modified and n_obj(r) == 0


def test_toggle_while_editing_applies_after_finish(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>a $x^2$ b</p>")
    r.start_editing()
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    assert r.editor.toPlainText() == "a $x^2$ b"
    r.finish_editing()
    sh.set_modified(False)
    assert n_obj(r) == 0, "setting changed while editing must hold once editing ends"


def test_toggle_roundtrip_file_bytes(window, tmp_path):
    sh = window.sheet
    sh.add_region("text", QPointF(40, 40), "<p>a $x^2$ b</p>")
    j1 = sh.to_document().to_json()
    act = [a for a in menu_of(window, "View").actions() if "Typeset" in a.text()][0]
    act.setChecked(False)
    j2 = sh.to_document().to_json()
    act.setChecked(True)
    j3 = sh.to_document().to_json()
    assert j1 == j2 == j3


# -- Insert formula -----------------------------------------------------------------------------

def trigger(w, display):
    items = {a.text().replace("&", ""): a for a in menu_of(w, "Insert").actions()}
    items["Formula (display)" if display else "Formula (inline)"].trigger()


def test_insert_inline_empty_caret(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "")
    r.start_editing()
    trigger(window, False)
    assert r.editor.toPlainText() == "$$" and r.editor.textCursor().position() == 1


def test_insert_display_empty_caret(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "")
    r.start_editing()
    trigger(window, True)
    assert r.editor.toPlainText() == "$$$$" and r.editor.textCursor().position() == 2


def test_insert_wraps_selection(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>abc</p>")
    r.start_editing()
    c = r.editor.textCursor(); c.select(QTextCursor.SelectionType.Document); r.editor.setTextCursor(c)
    trigger(window, False)
    assert r.editor.toPlainText() == "$abc$"
    r.finish_editing()
    assert n_obj(r) == 1
    r.start_editing()
    c = r.editor.textCursor(); c.select(QTextCursor.SelectionType.Document); r.editor.setTextCursor(c)
    trigger(window, True)
    assert r.editor.toPlainText() == "$$$abc$$$"


def test_insert_wraps_selection_display(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>abc</p>")
    r.start_editing()
    c = r.editor.textCursor(); c.select(QTextCursor.SelectionType.Document); r.editor.setTextCursor(c)
    trigger(window, True)
    assert r.editor.toPlainText() == "$$abc$$"
    r.finish_editing()
    assert n_obj(r) == 1


def test_insert_mid_text_and_single_undo(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>abcd</p>")
    r.start_editing()
    c = r.editor.textCursor(); c.setPosition(2); r.editor.setTextCursor(c)
    trigger(window, False)
    assert r.editor.toPlainText() == "ab$$cd" and r.editor.textCursor().position() == 3
    r.editor.document().undo()
    assert r.editor.toPlainText() == "abcd"


def test_insert_then_type_then_typeset(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "")
    r.start_editing()
    trigger(window, False)
    r.editor.textCursor().insertText("x^2")
    r.finish_editing()
    assert n_obj(r) == 1 and "$x^2$" in r.text()


def test_insert_empty_delimiters_stay_plain(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "")
    r.start_editing()
    trigger(window, False)
    r.finish_editing()
    assert n_obj(r) == 0 and not r._has_error


def test_insert_on_selected_not_editing_starts_editing_at_end(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>abc</p>")
    sh.clearSelection()
    r.setSelected(True)
    assert not r.editing
    trigger(window, False)
    assert r.editing
    assert r.editor.toPlainText() == "abc$$"
    assert r.editor.textCursor().position() == 4


def test_insert_with_nothing_selected_creates_text_region(window):
    sh = window.sheet
    sh.clearSelection()
    n0 = len(sh.regions())
    trigger(window, True)
    assert len(sh.regions()) == n0 + 1
    r = sh.editing_region()
    assert isinstance(r, __import__("livesheet.gui.regions", fromlist=["TextRegion"]).TextRegion)
    assert r.editor.toPlainText() == "$$$$" and r.editor.textCursor().position() == 2


def test_insert_with_math_region_selected_not_editing_creates_text_region(window):
    from livesheet.gui.regions import MathRegion, TextRegion
    sh = window.sheet
    m = sh.add_region("math", QPointF(40, 40), "x := 1")
    sh.clearSelection(); m.setSelected(True)
    n0 = len(sh.regions())
    trigger(window, False)
    assert len(sh.regions()) == n0 + 1
    assert isinstance(sh.editing_region(), TextRegion)
    assert isinstance(m, MathRegion)


def test_insert_disabled_while_math_region_edited(window):
    sh = window.sheet
    m = sh.add_region("math", QPointF(40, 40), "x := 1")
    m.start_editing()
    ins = menu_of(window, "Insert")
    ins.aboutToShow.emit()
    items = {a.text().replace("&", ""): a for a in ins.actions()}
    assert not items["Formula (inline)"].isEnabled()
    assert not items["Formula (display)"].isEnabled()
    n0, txt = len(sh.regions()), m.editor.toPlainText()
    items["Formula (inline)"].trigger()
    window.insert_formula(True)
    assert len(sh.regions()) == n0 and m.editor.toPlainText() == txt
    m.finish_editing()
    ins.aboutToShow.emit()
    assert items["Formula (inline)"].isEnabled() and items["Formula (display)"].isEnabled()


def test_insert_disabled_while_plot_region_edited(window):
    sh = window.sheet
    try:
        p = sh.add_region("plot", QPointF(40, 40), "")
    except Exception:
        pytest.skip("plot region cannot be created headless")
    p.start_editing()
    if sh.editing_region() is None:
        pytest.skip("plot region has no edit state")
    ins = menu_of(window, "Insert")
    ins.aboutToShow.emit()
    items = {a.text().replace("&", ""): a for a in ins.actions()}
    assert not items["Formula (inline)"].isEnabled()


def test_shortcut_key_event_inserts(window, app):
    sh = window.sheet
    window.show()
    app.processEvents()
    r = sh.add_region("text", QPointF(40, 40), "")
    r.start_editing()
    r.editor.setFocus()
    mods = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
    QTest.keyClick(window, Qt.Key.Key_4, mods)
    app.processEvents()
    assert r.editor.toPlainText() == "$$"


def test_insert_does_not_dirty_sheet_until_edit_ends_unchanged(window):
    sh = window.sheet
    r = sh.add_region("text", QPointF(40, 40), "<p>abc</p>")
    sh.set_modified(False)
    r.start_editing(); r.finish_editing()
    assert not sh.modified


# ============================== PDF with L2 content ===========================================

def test_export_pdf_l2_vector(window, tmp_path):
    from livesheet.gui.main_window import export_pdf
    sh = window.sheet
    sh.add_region("text", QPointF(40, 40),
                  r"<p>$$\begin{pmatrix} 1 &amp; 2 \\ 3 &amp; 4 \end{pmatrix} + \hat{x} + "
                  r"\overbrace{a+b}^{n} + \mathbb{R}$$ and $\begin{cases}x&amp;y\end{cases}$ "
                  r"$\begin{foo}$</p>")
    out = tmp_path / "o.pdf"
    export_pdf(sh, str(out))
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/Subtype /Image" not in data and b"/Subtype/Image" not in data
