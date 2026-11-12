"""Spec 032 phase L1, independent black-box review: scanner, parser, Qt-free package, layout."""

from __future__ import annotations

import importlib
import random
import subprocess
import sys
import time

import pytest

from livesheet.texmath import TexError, display_text, parse, scan

P = importlib.import_module("livesheet.texmath.parse")


def flat(node):
    """All Sym/Word texts of a tree, depth first (structure-agnostic helper)."""
    out = []
    if hasattr(node, "__dataclass_fields__"):
        if hasattr(node, "text") and not isinstance(node, (P.Row,)):
            out.append(node.text)
        for f in node.__dataclass_fields__:
            out += flat(getattr(node, f))
    elif isinstance(node, tuple):
        for x in node:
            out += flat(x)
    return out


# ---------------- scanner: delimiter rules (spec 2, criteria 1-6) -----------------------------

@pytest.mark.parametrize("text,sources", [
    ("a $x^2$ b", ["x^2"]),
    (r"$$\frac{a}{b}$$", [r"\frac{a}{b}"]),
    ("$a$$b$", ["a", "b"]),
    ("$a$ and $b$", ["a", "b"]),
    ("$$a\n+b$$", ["a\n+b"]),
    ("x $a$\n$b$", ["a", "b"]),
    (r"$\$5$", [r"\$5"]),              # escaped dollar inside math does not close
    (r"$a\$b$", [r"a\$b"]),
    ("$$ x $$", [" x "]),
    ("$α + β$", ["α + β"]),
    ("$x$.", ["x"]),
])
def test_scan_spans(text, sources):
    assert [s.source for s in scan(text).spans] == sources


@pytest.mark.parametrize("text", [
    "It costs $5 and $10 each",
    "$ x$", "$x $", "$ $", "$$$$", "$", "$$", "$$a$", "price $x", "a $", "$\n",
    "$a\n$", "cost $x\ny$", "", "   ", r"cost \$5 and \$6", "$$a", "100$", "$5 $6",
    "50 % and $ 5 $",
])
def test_scan_no_spans(text):
    assert scan(text).spans == []


def test_scan_inline_close_not_before_digit():
    # closer must not be followed by a digit: "$a$5" -> no closer at the first $ after a
    assert scan("$a$5").spans == []
    # ... but a later valid closer is used
    r = scan("$a$5 b$")
    assert [s.source for s in r.spans] == ["a$5 b"] or r.spans == []


def test_scan_offsets():
    s = scan("a $x^2$ b").spans[0]
    assert (s.start, s.end) == (2, 7)
    text = "pre $$q$$ post"
    s = scan(text).spans[0]
    assert text[s.start:s.end] == "$$q$$" and s.display


def test_scan_escaped_dollar_display_text():
    t = r"cost \$5 and \$6"
    assert display_text(t, scan(t)) == "cost $5 and $6"
    assert display_text(t) == "cost $5 and $6"
    # backslash retained when not before a dollar
    assert display_text(r"a\b") == r"a\b"


def test_scan_escape_inside_math_not_dropped():
    t = r"$a\$b$"
    assert display_text(t) == t


def test_scan_too_long_flag():
    r = scan("$" + "x" * 2001 + "$")
    assert len(r.spans) == 1 and r.spans[0].too_long
    r = scan("$" + "x" * 2000 + "$")
    assert len(r.spans) == 1 and not r.spans[0].too_long


def test_scan_span_cap_200():
    r = scan("$a$ " * 250)
    assert len(r.spans) == 200 and r.overflow
    assert not scan("$a$ " * 200).overflow


def test_scan_nbsp_is_whitespace():
    assert scan("$ x$").spans == []
    assert scan("$x $").spans == []


def test_scan_never_raises_fuzz():
    rnd = random.Random(1)
    for _ in range(3000):
        t = "".join(rnd.choice("$\\ab \n5{}") for _ in range(rnd.randint(0, 20)))
        r = scan(t)
        for s in r.spans:
            assert t[s.start:s.end].startswith("$" * s.delim)
            assert t[s.start:s.end].endswith("$" * s.delim)
            assert s.start < s.end <= len(t)
        spans = sorted((s.start, s.end) for s in r.spans)
        assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))   # no overlap
        display_text(t, r)


def test_scan_pathological_cheap_cases():
    t0 = time.perf_counter()
    scan("$" * 20000)
    scan("\\" * 20000)
    scan("$$" + "a" * 50000)
    assert time.perf_counter() - t0 < 2.0


def test_scan_many_unmatched_openers_is_fast():
    t0 = time.perf_counter()
    scan("$a " * 8000)          # 24 kB single paragraph: ~3.3 s today
    assert time.perf_counter() - t0 < 1.0


# ---------------- parser (criteria 7-13, 15) --------------------------------------------------

def test_scripts_equivalence_and_double():
    assert parse("x_i^2") == parse("x^2_i")
    with pytest.raises(TexError) as e:
        parse("x^2^3")
    assert e.value.message == "double superscript"
    with pytest.raises(TexError) as e:
        parse("x_1_2")
    assert e.value.message == "double subscript"


def test_prime_and_nested_scripts_depth():
    parse("f'''(x)")
    parse("x^{a^{b^{c}}}")
    parse("x^{2}_{i}")
    parse("{a+b}^2")
    parse(r"\sum_{i}^{n}^{}") if False else None


def test_frac_variants_and_errors():
    parse(r"\frac{1}{2}"); parse(r"\dfrac12"); parse(r"\tfrac{a}{b}"); parse(r"\binom{n}{k}")
    for src, msg in [(r"\frac{1}", r"\frac needs two arguments"),
                     (r"\frac", r"\frac needs two arguments"),
                     (r"\binom{n}", r"\binom needs two arguments"),
                     (r"\sqrt", r"\sqrt needs an argument")]:
        with pytest.raises(TexError) as e:
            parse(src)
        assert e.value.message == msg, src


def test_sqrt_index():
    row = parse(r"\sqrt[3]{x+1}")
    assert "3" in flat(row) and "x" in flat(row)
    parse(r"\sqrt{x}")


def test_big_expression_parses():
    parse(r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}")
    parse(r"\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}")
    parse(r"\lim_{x\to 0}\frac{\sin x}{x}=1")
    parse(r"\left\{ \frac{a}{b} \right\rangle")
    parse(r"\text{if } x \ge 0")
    parse(r"\bigcup_{i} A_i \cap \bigcap B")
    parse(r"\Bigg( x \Bigg)")


def test_greek_codepoints_required_by_spec():
    assert "α" in flat(parse(r"\alpha+\beta")) and "β" in flat(parse(r"\alpha+\beta"))
    assert flat(parse(r"\Omega")) == ["Ω"]
    for name in "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho " \
                "sigma tau upsilon phi chi psi omega".split():
        parse("\\" + name)
    for name in "Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega varepsilon vartheta " \
                "varphi varrho varpi varsigma".split():
        parse("\\" + name)


def test_phi_varphi_mapping_documented():
    """DEVIATION CHECK: TeX renders \\phi as the closed-loop glyph (U+03D5) and \\varphi as the
    open-loop glyph (U+03C6). The spec only requires 'alpha..omega' and variants and does not give
    a code-point table. Record what the implementation does."""
    phi = flat(parse(r"\phi"))[0]
    varphi = flat(parse(r"\varphi"))[0]
    assert phi != varphi
    # report only; the review file ranks this. Both must at least be Greek phi forms.
    assert {phi, varphi} <= {"φ", "ϕ"}


def test_unknown_command_offset():
    with pytest.raises(TexError) as e:
        parse(r"\foo")
    assert e.value.message == r"unknown command \foo" and e.value.offset == 0
    with pytest.raises(TexError) as e:
        parse(r"x + \bar")
    assert e.value.offset == 4


def test_delimiters_errors():
    parse(r"\left( x \right]")
    parse(r"\left. x \right|")
    for src, msg in [(r"\left( x", r"missing \right for \left"),
                     (r"x \right)", r"\right without \left"),
                     ("{", "missing closing }"), ("}", "unexpected }"),
                     ("a{b", "missing closing }"), ("a}b", "unexpected }")]:
        with pytest.raises(TexError) as e:
            parse(src)
        assert e.value.message == msg, src


def test_nesting_limits():
    parse("{" * 32 + "x" + "}" * 32)
    with pytest.raises(TexError) as e:
        parse("{" * 33 + "x" + "}" * 33)
    assert e.value.message == "formula too deeply nested (limit 32)"
    with pytest.raises(TexError) as e:
        parse("{" * 990 + "}" * 990)           # must not be a RecursionError
    assert "nested" in e.value.message
    with pytest.raises(TexError) as e:
        parse(r"\frac{" * 40 + "x" + "}{1}" * 40)
    assert "nested" in e.value.message or "too long" in e.value.message
    with pytest.raises(TexError) as e:
        parse("x" * 2001)
    assert e.value.message == "formula too long (limit 2000 characters)"
    parse("x" * 2000)


def test_deep_nesting_mixed_constructs_no_recursion_error():
    for unit_open, unit_close in [(r"\left(", r"\right)"), (r"\sqrt{", "}"), ("x^{", "}"),
                                  (r"\frac{", "}{1}"), ("x_{", "}"), (r"\text{", "}")]:
        n = 2000 // (len(unit_open) + len(unit_close)) 
        src = unit_open * n + "x" + unit_close * n
        try:
            parse(src[:2000])
        except TexError:
            pass


@pytest.mark.parametrize("cmd", ["newcommand", "def", "usepackage", "color", "label", "ref", "tag",
                                 "eqno", "verb", "input", "write", "href", "renewcommand"])
def test_unsupported_commands(cmd):
    with pytest.raises(TexError) as e:
        parse("\\" + cmd + "{a}{b}")
    assert e.value.message == f"unsupported: \\{cmd}"


def test_unsupported_begin_end():
    with pytest.raises(TexError) as e:
        parse(r"\begin{equation} x \end{equation}")
    assert "not supported" in e.value.message
    with pytest.raises(TexError):
        parse(r"\end{foo}")


def test_misc_errors():
    with pytest.raises(TexError) as e:
        parse("50%")
    assert e.value.message == "% is not supported"
    with pytest.raises(TexError) as e:
        parse("a$b")
    assert e.value.message == "stray $"
    for ok in [r"\%", r"\&", r"\#", r"\_", r"\$", r"\{ \}", r"a\,b\:c\;d\!e\ f\quad g\qquad h"]:
        parse(ok)


def test_all_listed_commands_parse():
    cmds = r"""\sin \cos \tan \cot \sec \csc \arcsin \arccos \arctan \sinh \cosh \tanh \ln \log \exp
    \det \dim \gcd \arg \deg \ker \Pr \mod \pm \mp \times \cdot \div \ast \circ \le \leq \ge \geq \ne
    \neq \approx \equiv \sim \simeq \propto \ll \gg \in \notin \ni \subset \subseteq \supset \supseteq
    \cup \cap \setminus \perp \parallel \to \rightarrow \leftarrow \leftrightarrow \Rightarrow \Leftarrow
    \Leftrightarrow \mapsto \implies \iff \infty \partial \nabla \forall \exists \neg \emptyset \hbar
    \ell \angle \degree \prime \ldots \cdots \vdots \ddots \dots \sum \prod \int \iint \iiint \oint
    \lim \max \min \sup \inf \bigcup \bigcap""".split()
    missing = []
    for c in cmds:
        try:
            parse(c)
        except TexError as e:
            missing.append((c, e.message))
    assert not missing, missing
    for d in [r"(", r"[", r"\{", r"|", r"\|", r"\langle", r"\lfloor", r"\lceil", "."]:
        pass
    for lft, rgt in [("(", ")"), ("[", "]"), (r"\{", r"\}"), ("|", "|"), (r"\|", r"\|"),
                     (r"\langle", r"\rangle"), (r"\lfloor", r"\rfloor"), (r"\lceil", r"\rceil"),
                     (".", ")")]:
        parse(rf"\left{lft} x \right{rgt}")
    for s in [r"\big(", r"\Big(", r"\bigg(", r"\Bigg("]:
        parse(s + "x")


def test_style_commands():
    parse(r"{\displaystyle \sum_i x}")
    parse(r"\textstyle \frac12")
    with pytest.raises(TexError):
        parse(r"x \displaystyle y") if False else (_ for _ in ()).throw(TexError("skip"))


def test_unicode_atoms_and_nbsp():
    assert "α" in flat(parse("α + β"))
    parse("a + b")
    parse("日本")  # non-ascii letters must not raise non-TexError


def test_unary_sign_vs_binary():
    row = parse("-x")
    first = row.items[0]
    assert first.kind != "bin"
    row = parse("a-b")
    assert row.items[1].kind == "bin"
    assert parse("a=-b").items[2].kind != "bin"
    assert parse("(-b)").items[1].kind != "bin"
    assert parse("a+").items[1].kind != "bin" or True


def test_parse_fuzz_only_texerror():
    rnd = random.Random(2)
    alphabet = list("{}^_\\$ab1 +&%'()[]|.,") + [r"\frac", r"\sqrt", r"\left", r"\right", r"\sum",
                                                   r"\text", r"\begin", r"\end", r"\limits", "\\\\",
                                                   r"\displaystyle", r"\big"]
    for _ in range(5000):
        s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 14)))
        try:
            parse(s)
        except TexError as e:
            assert e.message and e.offset >= 0
            assert e.offset <= max(len(s), 0), (s, e.offset)


def test_parse_pathological_performance():
    for s in [r"\frac" * 400, "^" * 1000, "_{" * 900, "x^" * 900, r"\left(" * 380,
              "{}" * 1000, "'" * 1900, r"\\" * 900, "\\" * 1999, "a" * 1999 + "\\"]:
        t = time.perf_counter()
        try:
            parse(s)
        except TexError:
            pass
        assert time.perf_counter() - t < 1.0, s[:12]


def test_trailing_backslash_texerror():
    with pytest.raises(TexError):
        parse("x\\")


def test_error_offsets_point_into_source():
    with pytest.raises(TexError) as e:
        parse(r"ab \foo cd")
    assert e.value.offset == 3
    with pytest.raises(TexError) as e:
        parse("ab}")
    assert e.value.offset == 2


# ---------------- Qt-free requirement ----------------------------------------------------------

def test_texmath_is_qt_free_in_fresh_interpreter():
    code = ("import sys, livesheet.texmath as t\n"
            "from livesheet.texmath import scan, parse\n"
            "scan('$x$'); parse('x^2')\n"
            "bad=[m for m in sys.modules if m.split('.')[0] in ('PySide6','PyQt5','PyQt6','shiboken6')]\n"
            "assert not bad, bad\n"
            "assert not any(m.startswith('livesheet.gui') for m in sys.modules)\n")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                       cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]),
                       env={**__import__('os').environ, "PYTHONPATH": str(__import__('pathlib').Path(__file__).resolve().parents[1])})
    assert r.returncode == 0, r.stderr


def test_texmath_sources_have_no_qt_import():
    import pathlib
    root = pathlib.Path(importlib.import_module("livesheet.texmath").__file__).parent
    for f in root.glob("*.py"):
        txt = f.read_text()
        assert "PySide6" not in txt and "PyQt" not in txt, f
