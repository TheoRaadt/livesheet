"""Parser for the supported LaTeX math subset (Qt-free). Produces a small immutable tree.

Every problem raises :class:`TexError`; nothing is silently ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from typing import NamedTuple, Union

from .errors import TexError
from .scan import MAX_SPAN_CHARS
from . import tables

MAX_DEPTH = 32

Node = Union["Sym", "Word", "TextRun", "Space", "Row", "Script", "Frac", "Sqrt", "BigOp",
             "Delimited", "SizedDelim", "Matrix", "Accent"]


@dataclass(frozen=True)
class Sym:
    text: str
    kind: str = "ord"        # ord bin rel open close punct
    italic: bool = False
    style: str = ""          # "", "rm", "bf", "it", "bb", "cal", "bs" (font commands, L2)


@dataclass(frozen=True)
class Word:
    """Upright named function such as ``sin``."""
    text: str


@dataclass(frozen=True)
class TextRun:
    text: str


@dataclass(frozen=True)
class Space:
    em: float


@dataclass(frozen=True)
class Row:
    items: tuple = ()
    style: str | None = None       # None, "display" or "text"


@dataclass(frozen=True)
class Script:
    base: "Node"
    sup: "Node | None" = None
    sub: "Node | None" = None


@dataclass(frozen=True)
class Frac:
    num: "Node"
    den: "Node"
    style: str | None = None       # None (follow context), "display" or "text"
    rule: bool = True              # False for binomials


@dataclass(frozen=True)
class Sqrt:
    body: "Node"
    index: "Node | None" = None


@dataclass(frozen=True)
class BigOp:
    text: str
    word: bool = False
    integral: bool = False
    limits: str = "auto"           # auto, limits, nolimits


@dataclass(frozen=True)
class Delimited:
    left: str
    right: str
    body: "Node"


@dataclass(frozen=True)
class SizedDelim:
    text: str
    kind: str                      # open, close, ord
    factor: float


@dataclass(frozen=True)
class Matrix:
    """``rows`` is a tuple of equally long tuples of cell nodes. ``aligns`` is the column
    alignment pattern (``c``, ``l``/``r`` for cases/array/aligned), cycled over the columns."""
    rows: tuple
    env: str
    left: str = ""
    right: str = ""
    aligns: str = "c"


@dataclass(frozen=True)
class Accent:
    body: "Node"
    kind: str                       # hat bar vec dot ddot tilde overline underline overbrace underbrace
    label: "Node | None" = None     # script of a brace


class _Tok(NamedTuple):
    kind: str      # "cmd" or "char"
    val: str
    pos: int


def _is_ws(ch: str) -> bool:
    return ch.isspace()


class _Parser:
    def __init__(self, src: str):
        self.s = src
        self.i = 0
        self.depth = 0

    # -- lexer ----------------------------------------------------------------------------

    def _skip_ws(self) -> None:
        s, n = self.s, len(self.s)
        while self.i < n and _is_ws(s[self.i]):
            self.i += 1

    def _read(self) -> _Tok | None:
        """Read the next token starting at ``self.i`` (whitespace skipped); advances."""
        self._skip_ws()
        s, n = self.s, len(self.s)
        if self.i >= n:
            return None
        pos = self.i
        ch = s[pos]
        if ch != "\\":
            self.i += 1
            return _Tok("char", ch, pos)
        if pos + 1 >= n:
            raise TexError("incomplete command at end of formula", pos)
        nxt = s[pos + 1]
        if nxt.isalpha() and nxt.isascii():
            j = pos + 1
            while j < n and s[j].isalpha() and s[j].isascii():
                j += 1
            self.i = j
            return _Tok("cmd", s[pos + 1:j], pos)
        self.i = pos + 2
        return _Tok("cmd", nxt, pos)

    def peek(self) -> _Tok | None:
        save = self.i
        try:
            return self._read()
        finally:
            self.i = save

    def take(self) -> _Tok | None:
        return self._read()

    # -- rows -----------------------------------------------------------------------------

    def parse_row(self, stops: frozenset[str]) -> Row:
        items: list = []
        style: str | None = None
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.kind == "char" and tok.val == "}":
                if "}" in stops:
                    break
                raise TexError("unexpected }", tok.pos)
            if tok.kind == "char" and tok.val == "]" and "]" in stops:
                break
            if tok.kind == "char" and tok.val == "&" and "&" in stops:
                break
            if tok.kind == "cmd" and tok.val in ("\\", "end") and tok.val in stops:
                break
            if tok.kind == "cmd" and tok.val == "right":
                if "right" in stops:
                    break
                raise TexError("\\right without \\left", tok.pos)
            if tok.kind == "cmd" and tok.val in ("displaystyle", "textstyle"):
                self.take()
                if items or style is not None:
                    raise TexError(f"\\{tok.val} must be at the start of a group", tok.pos)
                style = "display" if tok.val == "displaystyle" else "text"
                continue
            if tok.kind == "cmd" and tok.val in ("limits", "nolimits"):
                self.take()
                if not items or not isinstance(items[-1], BigOp):
                    raise TexError(f"\\{tok.val} must follow a big operator", tok.pos)
                items[-1] = replace(items[-1], limits=tok.val)
                node = self._scripts(items.pop())
                items.append(node)
                continue
            if tok.kind == "char" and tok.val in "^_'":
                atom: Node = Row(())
            else:
                atom = self.parse_atom()
            # \limits may follow directly
            nxt = self.peek()
            if isinstance(atom, BigOp) and nxt and nxt.kind == "cmd" and nxt.val in ("limits", "nolimits"):
                self.take()
                atom = replace(atom, limits=nxt.val)
            items.append(self._scripts(atom))
        return Row(tuple(_fix_binary(items)), style)

    def _scripts(self, base: Node) -> Node:
        sup = sub = None
        primes = 0
        while True:
            tok = self.peek()
            if tok is None or tok.kind != "char":
                break
            if tok.val == "^":
                self.take()
                if sup is not None:
                    raise TexError("double superscript", tok.pos)
                sup = self._script_arg("^", tok.pos)
            elif tok.val == "_":
                self.take()
                if sub is not None:
                    raise TexError("double subscript", tok.pos)
                sub = self._script_arg("_", tok.pos)
            elif tok.val == "'":
                self.take()
                primes += 1
            else:
                break
        if primes:
            prime = Sym("′" * primes, "ord")
            sup = prime if sup is None else Row((prime, sup))
        if sup is None and sub is None:
            return base
        return Script(base, sup, sub)

    def _script_arg(self, mark: str, pos: int) -> Node:
        tok = self.peek()
        if tok is None or self._ends_arg(tok):
            raise TexError(f"{mark} needs an argument", pos)
        return self._arg_node()

    @staticmethod
    def _ends_arg(tok: _Tok) -> bool:
        if tok.kind == "char":
            return tok.val in "}^_&"
        return tok.val in ("right", "end", "\\")

    def _arg_node(self) -> Node:
        tok = self.peek()
        if tok is not None and tok.kind == "char" and tok.val == "{":
            return self.parse_group()
        return self.parse_atom(single=True)

    def parse_group(self) -> Row:
        open_tok = self.take()
        assert open_tok is not None and open_tok.val == "{"
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise TexError(f"formula too deeply nested (limit {MAX_DEPTH})", open_tok.pos)
        row = self.parse_row(frozenset("}"))
        close = self.take()
        if close is None:
            raise TexError("missing closing }", open_tok.pos)
        self.depth -= 1
        return row

    # -- atoms ----------------------------------------------------------------------------

    def parse_atom(self, single: bool = False) -> Node:
        tok = self.take()
        assert tok is not None
        if tok.kind == "cmd":
            return self.parse_command(tok)
        ch = tok.val
        if ch == "{":
            self.i = tok.pos
            return self.parse_group()
        if ch == "$":
            raise TexError("stray $", tok.pos)
        if ch == "%":
            raise TexError("% is not supported", tok.pos)
        if ch == "&":
            raise TexError("unsupported: &", tok.pos)
        if ch.isdigit():
            return self._number(tok, single)
        if ch in tables.CHARS:
            text, kind = tables.CHARS[ch]
            return Sym(text, kind)
        if ch.isalpha():
            return Sym(ch, "ord", italic=ch.isascii() or "α" <= ch <= "ω")
        if ch.isascii():
            raise TexError(f"unsupported character {ch}", tok.pos)
        return Sym(ch, tables.KIND_BY_CHAR.get(ch, "ord"))

    def _number(self, tok: _Tok, single: bool) -> Node:
        text = tok.val
        if not single:
            s, n = self.s, len(self.s)
            while self.i < n and (s[self.i].isdigit()
                                  or (s[self.i] == "." and self.i + 1 < n and s[self.i + 1].isdigit())):
                text += s[self.i]
                self.i += 1
        return Sym(text, "ord")

    def parse_command(self, tok: _Tok) -> Node:
        name, pos = tok.val, tok.pos
        if name in tables.SYMBOLS:
            text, kind = tables.SYMBOLS[name]
            return Sym(text, kind, italic=name in tables.GREEK_NAMES and text.islower())
        if name in tables.SPACES:
            return Space(tables.SPACES[name])
        if name in tables.FUNCTIONS:
            return Word(name)
        if name in tables.BIG_OPERATORS:
            text, word, integral = tables.BIG_OPERATORS[name]
            return BigOp(text, word, integral)
        if name in ("frac", "dfrac", "tfrac"):
            return self._frac(name, pos)
        if name == "binom":
            return self._binom(name, pos)
        if name == "sqrt":
            return self._sqrt(pos)
        if name == "left":
            return self._left(pos)
        if name in tables.SIZED:
            return self._sized(name, pos)
        if name == "text":
            return self._text(pos)
        if name == "begin":
            return self._begin(pos)
        if name in tables.ACCENTS:
            return self._accent(name, pos)
        if name in tables.FONT_COMMANDS:
            (body,) = self._need_args(name, pos, 1, "an argument")
            return _restyle(body, tables.FONT_COMMANDS[name])
        if name == "operatorname":
            return self._operatorname(pos)
        if name == "bmod":
            return Sym("mod", "bin")
        if name == "pmod":
            (arg,) = self._need_args(name, pos, 1, "an argument")
            return Row((Space(1.0), Sym("(", "open"), Word("mod"), Space(1 / 3), arg,
                        Sym(")", "close")))
        if name == "end":
            raise TexError("unexpected \\end", pos)
        if name == "\\":
            raise TexError("unsupported: \\\\", pos)
        if name in tables.UNSUPPORTED:
            raise TexError(f"unsupported: \\{name}", pos)
        raise TexError(f"unknown command \\{name}", pos)

    # -- structures -----------------------------------------------------------------------

    def _need_args(self, name: str, pos: int, count: int, word: str) -> list[Node]:
        out: list[Node] = []
        for _ in range(count):
            tok = self.peek()
            if tok is None or self._ends_arg(tok):
                raise TexError(f"\\{name} needs {word}", pos)
            out.append(self._arg_node())
        return out

    def _frac(self, name: str, pos: int) -> Node:
        num, den = self._need_args(name, pos, 2, "two arguments")
        style = {"dfrac": "display", "tfrac": "text"}.get(name)
        return Frac(num, den, style)

    def _binom(self, name: str, pos: int) -> Node:
        num, den = self._need_args(name, pos, 2, "two arguments")
        return Delimited("(", ")", Row((Frac(num, den, None, rule=False),)))

    def _sqrt(self, pos: int) -> Node:
        index = None
        self._skip_ws()
        if self.i < len(self.s) and self.s[self.i] == "[":
            br = self.take()
            assert br is not None
            self.depth += 1
            if self.depth > MAX_DEPTH:
                raise TexError(f"formula too deeply nested (limit {MAX_DEPTH})", br.pos)
            index = self.parse_row(frozenset("]"))
            close = self.take()
            if close is None:
                raise TexError("missing closing ]", br.pos)
            self.depth -= 1
        (body,) = self._need_args("sqrt", pos, 1, "an argument")
        return Sqrt(body, index)

    def _delim(self, name: str, pos: int) -> str:
        tok = self.take()
        if tok is None:
            raise TexError(f"\\{name} needs a delimiter", pos)
        if tok.kind == "cmd" and tok.val in tables.CMD_DELIMS:
            return tables.CMD_DELIMS[tok.val]
        if tok.val in tables.DELIMITERS:
            return tables.DELIMITERS[tok.val]
        raise TexError(f"\\{name} needs a delimiter", pos)

    def _left(self, pos: int) -> Node:
        left = self._delim("left", pos)
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise TexError(f"formula too deeply nested (limit {MAX_DEPTH})", pos)
        body = self.parse_row(frozenset(["right"]))
        tok = self.take()
        if tok is None:
            raise TexError("missing \\right for \\left", pos)
        right = self._delim("right", tok.pos)
        self.depth -= 1
        return Delimited(left, right, body)

    def _sized(self, name: str, pos: int) -> Node:
        text = self._delim(name, pos)
        kind = "open" if text in ("(", "[", "{", "⟨", "⌊", "⌈") else \
            "close" if text in (")", "]", "}", "⟩", "⌋", "⌉") else "ord"
        return SizedDelim(text or " ", kind, tables.SIZED[name])

    def _braced_name(self, cmd: str, pos: int) -> str:
        self._skip_ws()
        if self.i >= len(self.s) or self.s[self.i] != "{":
            raise TexError(f"\\{cmd} needs an environment name", pos)
        end = self.s.find("}", self.i)
        if end < 0:
            raise TexError("missing closing }", self.i)
        name = self.s[self.i + 1:end].strip()
        self.i = end + 1
        return name

    def _column_spec(self, pos: int) -> str:
        self._skip_ws()
        if self.i >= len(self.s) or self.s[self.i] != "{":
            raise TexError("\\begin{array} needs a column specification", pos)
        end = self.s.find("}", self.i)
        if end < 0:
            raise TexError("missing closing }", self.i)
        spec = "".join(self.s[self.i + 1:end].split())
        self.i = end + 1
        if not spec or any(c not in "lcr" for c in spec):
            raise TexError("array column specification may only use l, c and r", pos)
        return spec

    def _begin(self, pos: int) -> Node:
        env = self._braced_name("begin", pos)
        left = right = ""
        if env in tables.MATRIX_ENVS:
            left, right = tables.MATRIX_ENVS[env]
            aligns = "c"
        elif env == "cases":
            left, aligns = "{", "l"
        elif env == "aligned":
            aligns = "rl"
        elif env == "array":
            aligns = self._column_spec(pos)
        else:
            raise TexError(f"\\begin{{{env}}} is not supported", pos)
        rows = self._env_rows(env, pos)
        ncols = max(len(r) for r in rows)
        if env == "array" and ncols > len(aligns):
            raise TexError("array row has more cells than its column specification", pos)
        empty = Row(())
        grid = tuple(tuple(r) + (empty,) * (ncols - len(r)) for r in rows)
        return Matrix(grid, env, left, right, aligns)

    def _env_rows(self, env: str, pos: int) -> list[list[Node]]:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise TexError(f"formula too deeply nested (limit {MAX_DEPTH})", pos)
        too_big = f"matrix too large (limit {tables.MAX_MATRIX} x {tables.MAX_MATRIX})"
        rows: list[list[Node]] = [[]]
        stops = frozenset(["&", "\\", "end"])
        while True:
            rows[-1].append(self.parse_row(stops))
            tok = self.take()
            if tok is None:
                raise TexError(f"missing \\end{{{env}}}", pos)
            if tok.kind == "char":                       # "&": next cell
                if len(rows[-1]) >= tables.MAX_MATRIX:
                    raise TexError(too_big, tok.pos)
                continue
            if tok.val == "\\":                          # next row
                if len(rows) >= tables.MAX_MATRIX:
                    raise TexError(too_big, tok.pos)
                rows.append([])
                continue
            name = self._braced_name("end", tok.pos)
            if name != env:
                raise TexError(f"\\end{{{name}}} does not match \\begin{{{env}}}", tok.pos)
            break
        self.depth -= 1
        if len(rows) > 1 and len(rows[-1]) == 1 and rows[-1][0] == Row(()):
            rows.pop()                                   # a trailing row separator
        return rows

    def _accent(self, name: str, pos: int) -> Node:
        (body,) = self._need_args(name, pos, 1, "an argument")
        label = None
        if name in ("overbrace", "underbrace"):
            mark = "^" if name == "overbrace" else "_"
            tok = self.peek()
            if tok is not None and tok.kind == "char" and tok.val == mark:
                self.take()
                label = self._script_arg(mark, tok.pos)
        return Accent(body, name, label)

    def _operatorname(self, pos: int) -> Node:
        self._skip_ws()
        s = self.s
        if self.i >= len(s) or s[self.i] != "{":
            raise TexError("\\operatorname needs an argument", pos)
        end = s.find("}", self.i)
        if end < 0:
            raise TexError("missing closing }", self.i)
        name = s[self.i + 1:end].strip()
        if not name or not all(c.isalnum() or c in " *" for c in name):
            raise TexError("\\operatorname needs a plain name", pos)
        self.i = end + 1
        return Word(name)

    def _text(self, pos: int) -> Node:
        self._skip_ws()
        s, n = self.s, len(self.s)
        if self.i >= n or s[self.i] != "{":
            raise TexError("\\text needs an argument", pos)
        start = self.i
        self.i += 1
        depth = 1
        out: list[str] = []
        while self.i < n:
            ch = s[self.i]
            if ch == "\\" and self.i + 1 < n and s[self.i + 1] in "{}$%&#_\\ ":
                out.append(s[self.i + 1])
                self.i += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return TextRun("".join(out).replace("\xa0", " ").replace("\n", " "))
            out.append(ch)
            self.i += 1
        raise TexError("missing closing }", start)


def _restyle(node: Node, style: str) -> Node:
    """Apply a font command to the symbols of ``node`` (inner font commands win)."""
    if isinstance(node, Sym):
        if node.style:
            return node
        italic = style in ("it", "bs") and any(c.isalpha() for c in node.text)
        return replace(node, style=style, italic=italic)
    if isinstance(node, Row):
        return replace(node, items=tuple(_restyle(x, style) for x in node.items))
    if isinstance(node, Script):
        return Script(_restyle(node.base, style),
                      None if node.sup is None else _restyle(node.sup, style),
                      None if node.sub is None else _restyle(node.sub, style))
    if isinstance(node, Frac):
        return replace(node, num=_restyle(node.num, style), den=_restyle(node.den, style))
    if isinstance(node, Sqrt):
        return Sqrt(_restyle(node.body, style), None if node.index is None else _restyle(node.index, style))
    if isinstance(node, Delimited):
        return replace(node, body=_restyle(node.body, style))
    if isinstance(node, Matrix):
        return replace(node, rows=tuple(tuple(_restyle(c, style) for c in r) for r in node.rows))
    if isinstance(node, Accent):
        return replace(node, body=_restyle(node.body, style),
                       label=None if node.label is None else _restyle(node.label, style))
    return node


def _kind_of(node: Node) -> str:
    if isinstance(node, Sym):
        return node.kind
    if isinstance(node, (Word, BigOp)):
        return "op"
    if isinstance(node, Script):
        return _kind_of(node.base)
    return "ord"


def _fix_binary(items: list) -> list:
    """A binary operator at the start/end of a group or after another operator is a sign."""
    out: list = []
    for idx, item in enumerate(items):
        if isinstance(item, Sym) and item.kind == "bin":
            prev = next((x for x in reversed(out) if not isinstance(x, Space)), None)
            nxt = next((x for x in items[idx + 1:] if not isinstance(x, Space)), None)
            if (prev is None or _kind_of(prev) in ("bin", "rel", "open", "punct", "op")
                    or nxt is None):
                item = replace(item, kind="ord")
        out.append(item)
    return out


def parse(source: str) -> Row:
    """Parse a formula. Raises :class:`TexError` with the problem and its offset."""
    if len(source) > MAX_SPAN_CHARS:
        raise TexError(f"formula too long (limit {MAX_SPAN_CHARS} characters)", 0)
    p = _Parser(source)
    try:
        row = p.parse_row(frozenset())
    except RecursionError:
        raise TexError(f"formula too deeply nested (limit {MAX_DEPTH})", 0) from None
    if p.peek() is not None:   # parse_row only stops early on terminators it was not given
        tok = p.peek()
        raise TexError("unexpected " + (tok.val if tok.kind == "char" else "\\" + tok.val), tok.pos)
    return row


@lru_cache(maxsize=500)
def parse_cached(source: str) -> Row:
    return parse(source)
