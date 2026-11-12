"""Layout and painting of parsed LaTeX-subset formulas (spec 032).

The parser (``livesheet.texmath``) knows nothing about Qt. This module turns its tree into a
tree of boxes (width, ascent, descent, children) using font metrics and paints them with
``QPainter`` only, so on screen, under zoom and on a PDF writer the output is vector.

All numeric constants are LiveSheet's own, expressed as fractions of the font size ("em").
Vertical offsets in boxes are in "y down" form relative to the box baseline.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPyTextObject,
    QTextCharFormat,
    QTextDocument,
    QTextFormat,
    QFontDatabase,
    QGuiApplication,
    QTransform,
)

from ..texmath import TexError, tables
from ..texmath.parse import parse_cached

# ``livesheet.texmath.parse`` is also a function name in the package namespace.
P = importlib.import_module("livesheet.texmath.parse")

log = logging.getLogger(__name__)

MATH_FAMILIES = ["STIX Two Math", "Cambria Math", "STIX Two Text", "Times New Roman", "serif"]
MONO_FAMILIES = ["Menlo", "Consolas", "DejaVu Sans Mono", "monospace"]

TEX_OBJ_TYPE = QTextFormat.ObjectTypes.UserObject.value + 1
TEX_PROP_INDEX = QTextFormat.Property.UserProperty.value + 1

K = 4                      # fonts are created K times larger and painted scaled down by 1/K
ASC, DESC = 0.76, 0.22     # ascent / descent of a glyph box (em)
XHEIGHT = 0.45
AXIS = 0.25                # height of the math axis above the baseline
RULE = 0.06                # fraction rule / radical thickness
MIN_PX = 8.0               # smallest script size in pixels (6 pt at 96 dpi)
SCRIPT_SCALE = (1.0, 0.7, 0.5)
THIN, MEDIUM, THICK = 3 / 18, 4 / 18, 5 / 18


# -- context ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class Ctx:
    base: float            # pixel size of the surrounding text
    level: int = 0         # script depth (0 = full size)
    display: bool = False  # display style (large operators with limits above/below)

    @property
    def size(self) -> float:
        if self.level == 0:
            return self.base
        factor = SCRIPT_SCALE[min(self.level, len(SCRIPT_SCALE) - 1)]
        return max(self.base * factor, min(self.base, MIN_PX))

    def script(self) -> "Ctx":
        return Ctx(self.base, self.level + 1, False)

    def with_display(self, display: bool) -> "Ctx":
        return Ctx(self.base, self.level, display)


# -- fonts -------------------------------------------------------------------------------------

BUNDLED_FONT = Path(__file__).resolve().parent / "fonts" / "STIXTwoMath-Regular.otf"
_font_state: dict[str, object] = {"done": False, "id": -1}


def ensure_math_font() -> int:
    """Register the bundled STIX Two Math font once (spec 032, L2). Returns the application
    font id, or -1 when it could not be loaded; then the system chain in ``MATH_FAMILIES`` is
    used (logged once). Needs a ``QGuiApplication``; without one nothing is recorded."""
    if _font_state["done"]:
        return int(_font_state["id"])      # type: ignore[arg-type]
    if QGuiApplication.instance() is None:
        return -1
    _font_state["done"] = True
    font_id = -1
    try:
        font_id = QFontDatabase.addApplicationFont(str(BUNDLED_FONT))
    except Exception:
        log.exception("loading the bundled math font failed")
    if font_id < 0:
        log.warning("bundled math font %s could not be loaded; using system fonts", BUNDLED_FONT)
    _font_state["id"] = font_id
    return font_id


_FONTS: dict[tuple, tuple[QFont, QFontMetricsF]] = {}


def _font(size: float, italic: bool = False, mono: bool = False,
          bold: bool = False) -> tuple[QFont, QFontMetricsF]:
    ensure_math_font()
    px = max(1, round(size * K))
    key = (px, italic, mono, bold)
    hit = _FONTS.get(key)
    if hit is None:
        f = QFont()
        f.setFamilies(MONO_FAMILIES if mono else MATH_FAMILIES)
        f.setPixelSize(px)
        f.setItalic(italic)
        f.setBold(bold)
        hit = (f, QFontMetricsF(f))
        _FONTS[key] = hit
    return hit


# -- boxes -------------------------------------------------------------------------------------

class Box:
    """A laid-out piece of a formula. ``children`` are ``(dx, dy, box)`` with ``dy`` measured
    downwards from this box's baseline."""

    kind = "box"

    def __init__(self, width: float = 0.0, ascent: float = 0.0, descent: float = 0.0):
        self.width = width
        self.ascent = ascent
        self.descent = descent
        self.children: list[tuple[float, float, Box]] = []

    @property
    def height(self) -> float:
        return self.ascent + self.descent

    def paint(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        self.paint_self(painter, x, y, color)
        for dx, dy, child in self.children:
            child.paint(painter, x + dx, y + dy, color)

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        pass


class GlyphBox(Box):
    kind = "glyph"

    def __init__(self, text: str, size: float, italic: bool = False, ink: bool = False,
                 mono: bool = False, bold: bool = False):
        font, fm = _font(size, italic, mono, bold)
        width = fm.horizontalAdvance(text) / K
        if ink:
            r = fm.tightBoundingRect(text)
            super().__init__(width, max(0.0, -r.top() / K), max(0.0, r.bottom() / K))
        else:
            super().__init__(width, ASC * size, DESC * size)
        self.text = text
        self.size = size
        self.font = font
        self.italic, self.bold, self.mono = italic, bold, mono

    def ink_ascent(self) -> float:
        """Height of the visible ink above the baseline (not the nominal font ascent)."""
        _f, fm = _font(self.size, self.italic, self.mono, self.bold)
        return max(0.0, -fm.tightBoundingRect(self.text).top() / K)

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        painter.save()
        painter.translate(x, y)
        painter.scale(1.0 / K, 1.0 / K)
        painter.setFont(self.font)
        painter.setPen(color)
        painter.drawText(QPointF(0, 0), self.text)
        painter.restore()


class SpaceBox(Box):
    kind = "space"


class HBox(Box):
    kind = "row"


class ScriptBox(Box):
    kind = "script"

    def __init__(self, base: Box, sup: Box | None, sub: Box | None, sup_shift: float, sub_shift: float):
        super().__init__()
        self.base, self.sup, self.sub = base, sup, sub
        self.sup_shift = sup_shift      # baseline of the superscript, raised by this much
        self.sub_shift = sub_shift      # baseline of the subscript, lowered by this much


class StackBox(Box):
    kind = "limits"


class FracBox(Box):
    kind = "frac"

    def __init__(self):
        super().__init__()
        self.num: Box
        self.den: Box
        self.num_dy = 0.0      # baseline offsets (y down)
        self.den_dy = 0.0
        self.rule_dy = 0.0     # centre of the rule (y down, negative = above baseline)
        self.thickness = 0.0
        self.rule_w = 0.0

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        if self.thickness > 0:
            painter.fillRect(QRectF(x, y + self.rule_dy - self.thickness / 2, self.rule_w, self.thickness), color)


class SqrtBox(Box):
    kind = "sqrt"

    def __init__(self):
        super().__init__()
        self.body: Box
        self.index: Box | None = None
        self.path = QPainterPath()
        self.thickness = 1.0

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        _stroke(painter, self.path, x, y, color, self.thickness)


class PathBox(Box):
    """A stretched delimiter drawn as a path (so it is vector on every output)."""

    kind = "delim"

    def __init__(self, text: str, size: float, top: float, bottom: float):
        w = _delim_width(text, size)
        super().__init__(w, max(0.0, -top), max(0.0, bottom))
        self.text = text
        self.top, self.bottom = top, bottom
        self.thickness = max(0.7, RULE * size * 1.1)
        self.path = delim_path(text, w, top, bottom)

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        _stroke(painter, self.path, x, y, color, self.thickness)


def _stroke(painter: QPainter, path: QPainterPath, x: float, y: float, color: QColor, width: float) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.translate(x, y)
    painter.drawPath(path)
    painter.restore()


# -- delimiters --------------------------------------------------------------------------------

_LEFT_FORMS = {"(": "(", ")": "(", "[": "[", "]": "[", "{": "{", "}": "{", "⟨": "⟨", "⟩": "⟨",
               "⌊": "⌊", "⌋": "⌊", "⌈": "⌈", "⌉": "⌈"}
_RIGHT = frozenset(")]}⟩⌋⌉")


def _delim_width(text: str, size: float) -> float:
    return size * {"(": 0.34, ")": 0.34, "[": 0.30, "]": 0.30, "{": 0.42, "}": 0.42, "|": 0.16,
                   "‖": 0.26, "⟨": 0.30, "⟩": 0.30, "⌊": 0.30, "⌋": 0.30, "⌈": 0.30, "⌉": 0.30,
                   "/": 0.40}.get(text, 0.3)


def delim_path(text: str, w: float, y0: float, y1: float) -> QPainterPath:
    """Path of a delimiter in a box of width ``w`` spanning ``y0..y1`` (y down)."""
    h = y1 - y0
    mid = (y0 + y1) / 2
    p = QPainterPath()
    form = _LEFT_FORMS.get(text)
    if text in ("|", "‖"):
        xs = [w / 2] if text == "|" else [w * 0.33, w * 0.67]
        for xx in xs:
            p.moveTo(xx, y0)
            p.lineTo(xx, y1)
        return p
    if text == "/":
        p.moveTo(w * 0.85, y0)
        p.lineTo(w * 0.15, y1)
        return p
    if form == "(":
        p.moveTo(w * 0.85, y0)
        p.cubicTo(w * 0.05, y0 + h * 0.25, w * 0.05, y1 - h * 0.25, w * 0.85, y1)
    elif form == "[":
        p.moveTo(w * 0.85, y0)
        p.lineTo(w * 0.2, y0)
        p.lineTo(w * 0.2, y1)
        p.lineTo(w * 0.85, y1)
    elif form == "{":
        p.moveTo(w * 0.9, y0)
        p.quadTo(w * 0.55, y0, w * 0.55, y0 + h * 0.15)
        p.lineTo(w * 0.55, mid - h * 0.07)
        p.quadTo(w * 0.55, mid, w * 0.1, mid)
        p.quadTo(w * 0.55, mid, w * 0.55, mid + h * 0.07)
        p.lineTo(w * 0.55, y1 - h * 0.15)
        p.quadTo(w * 0.55, y1, w * 0.9, y1)
    elif form == "⟨":
        p.moveTo(w * 0.8, y0)
        p.lineTo(w * 0.2, mid)
        p.lineTo(w * 0.8, y1)
    elif form == "⌊":
        p.moveTo(w * 0.2, y0)
        p.lineTo(w * 0.2, y1)
        p.lineTo(w * 0.8, y1)
    elif form == "⌈":
        p.moveTo(w * 0.2, y1)
        p.lineTo(w * 0.2, y0)
        p.lineTo(w * 0.8, y0)
    if text in _RIGHT:
        p = QTransform(-1, 0, 0, 1, w, 0).map(p)
    return p


def _delim_box(text: str, ctx: Ctx, needed: float) -> Box | None:
    """Box for a delimiter that must span ``needed`` (a total height centred on the axis)."""
    if not text:
        return None
    s = ctx.size
    line = (ASC + DESC) * s
    if needed <= 1.4 * line:
        scale = max(1.0, min(1.4, needed / line))
        g = GlyphBox(text, s * scale)
        g.kind = "delim"
        return g
    return PathBox(text, s, -(AXIS * s + needed / 2), -AXIS * s + needed / 2)


# -- layout ------------------------------------------------------------------------------------

def _atom_class(node) -> str:
    if isinstance(node, P.Sym):
        return node.kind
    if isinstance(node, (P.Word, P.BigOp)):
        return "op"
    if isinstance(node, P.Script):
        return _atom_class(node.base)
    if isinstance(node, P.SizedDelim):
        return node.kind
    return "ord"


_SPACING = {
    ("ord", "op"): THIN, ("ord", "bin"): MEDIUM, ("ord", "rel"): THICK,
    ("op", "ord"): THIN, ("op", "op"): THIN, ("op", "rel"): THICK,
    ("bin", "ord"): MEDIUM, ("bin", "op"): MEDIUM, ("bin", "open"): MEDIUM,
    ("rel", "ord"): THICK, ("rel", "op"): THICK, ("rel", "open"): THICK,
    ("close", "op"): THIN, ("close", "bin"): MEDIUM, ("close", "rel"): THICK,
    ("punct", "ord"): THIN, ("punct", "op"): THIN, ("punct", "rel"): THIN,
    ("punct", "open"): THIN, ("punct", "close"): THIN, ("punct", "punct"): THIN,
    ("open", "bin"): 0.0,
}


def _gap(left: str, right: str, ctx: Ctx) -> float:
    if ctx.level > 0:
        return 0.0
    return _SPACING.get((left, right), 0.0)


def _layout_row(row: P.Row, ctx: Ctx) -> Box:
    if row.style:
        ctx = ctx.with_display(row.style == "display")
    box = HBox()
    x = 0.0
    prev: str | None = None
    for item in row.items:
        if isinstance(item, P.Space):
            x += item.em * ctx.size
            continue
        cls = _atom_class(item)
        child = layout_node(item, ctx)
        if prev is not None:
            x += _gap(prev, cls, ctx) * ctx.size
        box.children.append((x, 0.0, child))
        x += child.width
        box.ascent = max(box.ascent, child.ascent)
        box.descent = max(box.descent, child.descent)
        prev = cls
    box.width = x
    return box


def limits_above(op: P.BigOp, display: bool) -> bool:
    """True when the op's scripts sit above/below it (rather than at the side)."""
    if op.limits == "limits":
        return True
    if op.limits == "nolimits":
        return False
    return display and not op.integral


def _layout_op(op: P.BigOp, ctx: Ctx) -> Box:
    s = ctx.size
    if op.word:
        return GlyphBox(op.text, s)
    big = ctx.display and ctx.level == 0
    factor = (1.7 if op.integral else 1.45) if big else (1.15 if op.integral else 1.0)
    g = GlyphBox(op.text, s * factor, ink=True)
    centre = (g.ascent - g.descent) / 2          # ink centre above the glyph baseline
    dy = centre - AXIS * s                         # lower the glyph so the centre sits on the axis
    box = HBox(g.width, g.ascent - dy, g.descent + dy)
    box.kind = "op"
    box.children.append((0.0, dy, g))
    return box


def _layout_script(node: P.Script, ctx: Ctx) -> Box:
    s = ctx.size
    if isinstance(node.base, P.BigOp):
        base = _layout_op(node.base, ctx)
        above = limits_above(node.base, ctx.display)
    else:
        base = layout_node(node.base, ctx)
        above = False
    sctx = ctx.script()
    prime_only = isinstance(node.sup, P.Sym) and set(node.sup.text) == {"\u2032"}
    # the prime glyph already sits high in its em box: draw it at full size on the baseline
    sup = layout_node(node.sup, ctx if prime_only else sctx) if node.sup is not None else None
    sub = layout_node(node.sub, sctx) if node.sub is not None else None
    if above:
        return _layout_limits(base, sup, sub, s)
    xh = XHEIGHT * s
    plain = isinstance(node.base, (P.Sym, P.Word)) and base.kind in ("glyph",)
    up = down = 0.0
    if sup is not None:
        up = 0.0 if prime_only else max(0.40 * s, sup.descent + 0.25 * xh)
        if not plain and not prime_only:
            up = max(up, base.ascent - 0.2 * s)
    if sub is not None:
        down = max(0.18 * s, sub.ascent - 0.8 * xh)
        if not plain:
            down = max(down, base.descent + 0.08 * s)
    if sup is not None and sub is not None:
        gap = (up - sup.descent) - (sub.ascent - down)
        min_gap = 0.16 * s
        if gap < min_gap:
            down += min_gap - gap
    box = ScriptBox(base, sup, sub, up, down)
    pad = (0.14 if isinstance(node.base, P.BigOp) and node.base.integral else 0.03) * s
    box.children.append((0.0, 0.0, base))
    width = base.width
    asc, desc = base.ascent, base.descent
    if sup is not None:
        box.children.append((base.width + pad, -up, sup))
        width = max(width, base.width + pad + sup.width)
        asc = max(asc, up + sup.ascent)
    if sub is not None:
        box.children.append((base.width + pad, down, sub))
        width = max(width, base.width + pad + sub.width)
        desc = max(desc, down + sub.descent)
    box.width, box.ascent, box.descent = width, asc, desc
    return box


def _layout_limits(base: Box, sup: Box | None, sub: Box | None, s: float) -> Box:
    gap = 0.12 * s
    width = max(base.width, sup.width if sup else 0.0, sub.width if sub else 0.0)
    box = StackBox(width, base.ascent, base.descent)
    box.base, box.sup, box.sub = base, sup, sub          # type: ignore[attr-defined]
    box.children.append(((width - base.width) / 2, 0.0, base))
    if sup is not None:
        dy = -(base.ascent + gap + sup.descent)
        box.children.append(((width - sup.width) / 2, dy, sup))
        box.ascent = -dy + sup.ascent
    if sub is not None:
        dy = base.descent + gap + sub.ascent
        box.children.append(((width - sub.width) / 2, dy, sub))
        box.descent = dy + sub.descent
    return box


def _layout_frac(node: P.Frac, ctx: Ctx) -> Box:
    s = ctx.size
    display = node.style == "display" or (node.style is None and ctx.display)
    pctx = ctx.with_display(False) if display else ctx.script()
    num = layout_node(node.num, pctx)
    den = layout_node(node.den, pctx)
    box = FracBox()
    box.num, box.den = num, den
    t = RULE * s if node.rule else 0.0
    gap = (0.20 if display else 0.12) * s
    if not node.rule:
        gap = 0.10 * s
    margin = 0.10 * s if node.rule else 0.05 * s
    inner = max(num.width, den.width)
    box.width = inner + 2 * margin
    box.rule_w = box.width
    box.thickness = t
    axis = AXIS * s
    box.rule_dy = -axis
    box.num_dy = -(axis + t / 2 + gap + num.descent)
    box.den_dy = -axis + t / 2 + gap + den.ascent
    box.children.append(((box.width - num.width) / 2, box.num_dy, num))
    box.children.append(((box.width - den.width) / 2, box.den_dy, den))
    box.ascent = max(-box.num_dy + num.ascent, ASC * s)
    box.descent = max(box.den_dy + den.descent, DESC * s)
    return box


def _layout_sqrt(node: P.Sqrt, ctx: Ctx) -> Box:
    s = ctx.size
    body = layout_node(node.body, ctx)
    t = RULE * s
    gap = 0.12 * s
    top = -(body.ascent + gap + t / 2)             # centre line of the top rule
    bottom = body.descent + 0.06 * s
    h = bottom - top
    sign_w = 0.55 * s
    index = None
    ix = 0.0
    if node.index is not None:
        index = layout_node(node.index, Ctx(ctx.base, 2, False))
        ix = max(0.0, index.width - 0.3 * sign_w)
    box = SqrtBox()
    box.body, box.index, box.thickness = body, index, max(0.7, t)
    pad = 0.08 * s
    total_w = ix + sign_w + body.width + pad
    p = QPainterPath()
    mid_y = bottom - 0.40 * h
    p.moveTo(ix, mid_y)
    p.lineTo(ix + sign_w * 0.25, mid_y - 0.04 * h)
    p.lineTo(ix + sign_w * 0.55, bottom)
    p.lineTo(ix + sign_w, top)
    p.lineTo(total_w, top)
    box.path = p
    box.children.append((ix + sign_w, 0.0, body))
    box.ascent = body.ascent + gap + t
    if index is not None:
        idy = bottom - 0.62 * h
        box.children.append((0.0, idy, index))
        box.ascent = max(box.ascent, -idy + index.ascent)
    box.descent = bottom
    box.width = total_w
    return box


def _layout_delimited(node: P.Delimited, ctx: Ctx) -> Box:
    s = ctx.size
    body = layout_node(node.body, ctx)
    axis = AXIS * s
    needed = 2 * max(body.ascent - axis, body.descent + axis, 0.0)
    needed = max(needed, (ASC + DESC) * s)
    left = _delim_box(node.left, ctx, needed)
    right = _delim_box(node.right, ctx, needed)
    box = HBox()
    box.kind = "delimited"
    x = 0.04 * s
    parts = [left, body, right]
    for part in parts:
        if part is None:
            continue
        box.children.append((x, 0.0, part))
        x += part.width + 0.04 * s
        box.ascent = max(box.ascent, part.ascent)
        box.descent = max(box.descent, part.descent)
    box.width = x
    return box


def _layout_sized(node: P.SizedDelim, ctx: Ctx) -> Box:
    s = ctx.size
    needed = node.factor * s
    text = node.text.strip()
    return _delim_box(text, ctx, needed) or SpaceBox()


class AccentBox(Box):
    """Accent marks, over/underlines and braces: stroked and filled paths (vector)."""

    kind = "accent"

    def __init__(self):
        super().__init__()
        self.strokes = QPainterPath()
        self.fills = QPainterPath()
        self.thickness = 1.0

    def paint_self(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        if not self.strokes.isEmpty():
            _stroke(painter, self.strokes, x, y, color, self.thickness)
        if not self.fills.isEmpty():
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.translate(x, y)
            painter.fillPath(self.fills, color)
            painter.restore()


class MatrixBox(Box):
    kind = "matrix"

    def __init__(self):
        super().__init__()
        self.cells: list[list[Box]] = []
        self.col_x: list[float] = []


def _ink_top(box: Box) -> float:
    """Distance of the visible top of ``box`` above its baseline (single glyphs: their ink)."""
    if isinstance(box, GlyphBox):
        return box.ink_ascent()
    if isinstance(box, HBox) and len(box.children) == 1 and box.children[0][1] == 0.0:
        return _ink_top(box.children[0][2])
    return box.ascent


def _styled_glyph(node: P.Sym, size: float) -> Box:
    mapped = tables.style_text(node.text, node.style)
    _f, fm = _font(size)
    if mapped != node.text and all(fm.inFontUcs4(ord(c)) for c in mapped):
        return GlyphBox(mapped, size)
    # no glyph for the styled form: plain characters with a synthetic bold/italic
    return GlyphBox(node.text, size, node.italic, bold=node.style in ("bf", "bs", "bb"))


def _layout_matrix(node: P.Matrix, ctx: Ctx) -> Box:
    s = ctx.size
    cctx = ctx.with_display(False)
    cells = [[layout_node(c, cctx) for c in row] for row in node.rows]
    ncols = len(cells[0]) if cells else 0
    widths = [max((row[c].width for row in cells), default=0.0) for c in range(ncols)]
    gaps = _column_gaps(node.env, ncols, s)
    col_x: list[float] = []
    x = 0.0
    for c in range(ncols):
        col_x.append(x)
        x += widths[c] + gaps[c]
    grid_w = max(0.0, x - (gaps[-1] if gaps else 0.0))
    # rows: a strut keeps single-line rows evenly spaced
    asc = [max(ASC * s, max(b.ascent for b in row)) for row in cells]
    desc = [max(DESC * s, max(b.descent for b in row)) for row in cells]
    row_gap = 0.22 * s
    base_y: list[float] = []
    y = 0.0
    for i in range(len(cells)):
        if i:
            y += desc[i - 1] + row_gap + asc[i]
        base_y.append(y)
    top = -asc[0]
    bottom = base_y[-1] + desc[-1]
    offset = -AXIS * s - (top + bottom) / 2          # centre the grid on the math axis
    box = MatrixBox()
    box.kind = "matrix"
    box.cells, box.col_x = cells, col_x
    left = _delim_box(node.left, ctx, bottom - top) if node.left else None
    right = _delim_box(node.right, ctx, bottom - top) if node.right else None
    pad = 0.10 * s
    x0 = 0.04 * s
    if left is not None:
        box.children.append((x0, 0.0, left))
        x0 += left.width + pad
    aligns = node.aligns or "c"
    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            mode = aligns[c % len(aligns)] if node.env != "array" else aligns[min(c, len(aligns) - 1)]
            dx = {"l": 0.0, "r": widths[c] - cell.width}.get(mode, (widths[c] - cell.width) / 2)
            box.children.append((x0 + col_x[c] + dx, base_y[r] + offset, cell))
    x0 += grid_w
    if right is not None:
        x0 += pad
        box.children.append((x0, 0.0, right))
        x0 += right.width
    box.width = x0 + 0.04 * s
    box.ascent = max([-(top + offset)] + [p.ascent for _x, _y, p in box.children if p in (left, right)])
    box.descent = max([bottom + offset] + [p.descent for _x, _y, p in box.children if p in (left, right)])
    return box


def _column_gaps(env: str, ncols: int, s: float) -> list[float]:
    if env == "aligned":
        return [(THICK if c % 2 == 0 else 2.0) * s for c in range(ncols)]
    if env == "cases":
        return [1.0 * s] * ncols
    return [0.9 * s] * ncols


def _brace_path(width: float, depth: float, up: bool) -> QPainterPath:
    """A horizontal curly brace ``width`` wide whose tip points up (or down)."""
    vertical = delim_path("{", depth, 0.0, width)         # tip on the left, runs along y
    if up:
        tr = QTransform(0, 1, 1, 0, 0, 0)                  # (x, y) -> (y, x): tip moves up
    else:
        tr = QTransform(0, -1, 1, 0, 0, depth)             # tip moves down
    return tr.map(vertical)


def _layout_accent(node: P.Accent, ctx: Ctx) -> Box:
    s = ctx.size
    body = layout_node(node.body, ctx)
    label = layout_node(node.label, ctx.script()) if node.label is not None else None
    width = max(body.width, label.width if label else 0.0)
    bx = (width - body.width) / 2
    cx = width / 2
    box = AccentBox()
    box.thickness = max(0.7, RULE * s)
    box.width, box.ascent, box.descent = width, body.ascent, body.descent
    box.children.append((bx, 0.0, body))
    kind = node.kind
    p, f = box.strokes, box.fills
    if kind in ("hat", "tilde", "bar", "vec", "dot", "ddot"):
        yb = -(_ink_top(body) + 0.10 * s)                  # bottom of the mark
        w = min(0.5 * s, max(0.3 * s, body.width * 0.8))
        if kind == "hat":
            h = 0.16 * s
            p.moveTo(cx - w / 2, yb)
            p.lineTo(cx, yb - h)
            p.lineTo(cx + w / 2, yb)
            top = yb - h
        elif kind == "tilde":
            h = 0.09 * s
            p.moveTo(cx - w / 2, yb)
            p.cubicTo(cx - w / 4, yb - 2.2 * h, cx - w / 8, yb - 2.2 * h, cx, yb - h)
            p.cubicTo(cx + w / 8, yb + 0.2 * h, cx + w / 4, yb + 0.2 * h, cx + w / 2, yb - 1.2 * h)
            top = yb - 2.0 * h
        elif kind == "bar":
            w = max(0.3 * s, body.width * 0.9)
            p.moveTo(cx - w / 2, yb - 0.04 * s)
            p.lineTo(cx + w / 2, yb - 0.04 * s)
            top = yb - 0.06 * s
        elif kind == "vec":
            w = max(0.4 * s, body.width * 0.9)
            y = yb - 0.05 * s
            p.moveTo(cx - w / 2, y)
            p.lineTo(cx + w / 2, y)
            p.moveTo(cx + w / 2 - 0.09 * s, y - 0.06 * s)
            p.lineTo(cx + w / 2, y)
            p.lineTo(cx + w / 2 - 0.09 * s, y + 0.06 * s)
            top = y - 0.07 * s
        else:
            r = 0.045 * s
            xs = [cx] if kind == "dot" else [cx - 0.1 * s, cx + 0.1 * s]
            for xx in xs:
                f.addEllipse(QPointF(xx, yb - 0.04 * s - r), r, r)
            top = yb - 0.04 * s - 2 * r
        box.ascent = max(box.ascent, -top)
    elif kind == "overline":
        y = -(body.ascent + 0.10 * s)
        p.moveTo(bx, y)
        p.lineTo(bx + body.width, y)
        box.ascent = max(box.ascent, -y + box.thickness)
    elif kind == "underline":
        y = body.descent + 0.12 * s
        p.moveTo(bx, y)
        p.lineTo(bx + body.width, y)
        box.descent = max(box.descent, y + box.thickness)
    else:
        _layout_brace(box, node, body, label, bx, width, s)
    return box


def _layout_brace(box: AccentBox, node: P.Accent, body: Box, label: Box | None, bx: float,
                  width: float, s: float) -> None:
    depth = 0.22 * s
    up = node.kind == "overbrace"
    gap = 0.08 * s
    if up:
        top = -(body.ascent + gap + depth)
        path = _brace_path(body.width, depth, True)
        path.translate(bx, top)
        box.strokes.addPath(path)
        box.ascent = -top
        if label is not None:
            dy = top - 0.08 * s - label.descent
            box.children.append(((width - label.width) / 2, dy, label))
            box.ascent = -dy + label.ascent
    else:
        top = body.descent + gap
        path = _brace_path(body.width, depth, False)
        path.translate(bx, top)
        box.strokes.addPath(path)
        box.descent = top + depth
        if label is not None:
            dy = top + depth + 0.08 * s + label.ascent
            box.children.append(((width - label.width) / 2, dy, label))
            box.descent = dy + label.descent


def layout_node(node, ctx: Ctx) -> Box:
    if isinstance(node, P.Row):
        return _layout_row(node, ctx)
    if isinstance(node, P.Sym):
        if node.style:
            return _styled_glyph(node, ctx.size)
        g = GlyphBox(node.text, ctx.size, node.italic)
        if node.italic and node.text in ("f", "\u03b2", "\u03b3", "\u03b6", "\u03c8"):
            g.width += 0.10 * ctx.size       # italic overhang: keep a following ( or script clear
        return g
    if isinstance(node, P.Word):
        return GlyphBox(node.text, ctx.size)
    if isinstance(node, P.TextRun):
        return GlyphBox(node.text, ctx.size)
    if isinstance(node, P.Space):
        return SpaceBox(node.em * ctx.size)
    if isinstance(node, P.Script):
        return _layout_script(node, ctx)
    if isinstance(node, P.Frac):
        return _layout_frac(node, ctx)
    if isinstance(node, P.Sqrt):
        return _layout_sqrt(node, ctx)
    if isinstance(node, P.BigOp):
        return _layout_op(node, ctx)
    if isinstance(node, P.Delimited):
        return _layout_delimited(node, ctx)
    if isinstance(node, P.SizedDelim):
        return _layout_sized(node, ctx)
    if isinstance(node, P.Matrix):
        return _layout_matrix(node, ctx)
    if isinstance(node, P.Accent):
        return _layout_accent(node, ctx)
    raise TexError("internal error in formula", 0)


# -- public entry points -----------------------------------------------------------------------

_CACHE: "OrderedDict[tuple, Box]" = OrderedDict()
CACHE_LIMIT = 500
_logged_internal = False


def parse_source(source: str) -> P.Row:
    """Parse with the shared cache; any non-TexError becomes ``internal error in formula``."""
    global _logged_internal
    try:
        return parse_cached(source)
    except TexError:
        raise
    except Exception:
        if not _logged_internal:
            _logged_internal = True
            log.exception("internal error while parsing a formula")
        raise TexError("internal error in formula", 0) from None


def layout_formula(source: str, size: float, display: bool = False) -> Box:
    """Parse and lay out ``source`` at ``size`` pixels. Raises :class:`TexError` only."""
    global _logged_internal
    key = (source, round(size * 100), display)
    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE.move_to_end(key)
        return hit
    tree = parse_source(source)
    try:
        box = layout_node(tree, Ctx(float(size), 0, display))
    except TexError:
        raise
    except Exception:
        if not _logged_internal:
            _logged_internal = True
            log.exception("internal error while laying out a formula")
        raise TexError("internal error in formula", 0) from None
    _CACHE[key] = box
    if len(_CACHE) > CACHE_LIMIT:
        _CACHE.popitem(last=False)
    return box


def walk(box: Box):
    """Yield ``box`` and every descendant."""
    yield box
    for _dx, _dy, child in box.children:
        yield from walk(child)


def find_box(box: Box, kind: str) -> Box | None:
    return next((b for b in walk(box) if b.kind == kind), None)


# -- inline object for QTextDocument -----------------------------------------------------------

@dataclass
class FormulaItem:
    box: Box
    display: bool
    k: float               # (ascent - descent) / 2 of the surrounding text font


class FormulaObject(QPyTextObject):
    """Draws formula boxes inline in a ``QTextDocument``. ``lookup(index)`` returns the
    FormulaItem for the span index stored in the character format."""

    def __init__(self, lookup: Callable[[int], FormulaItem | None], color: Callable[[], QColor]):
        super().__init__()
        self._lookup = lookup
        self._color = color

    def _item(self, fmt: QTextCharFormat) -> FormulaItem | None:
        try:
            return self._lookup(int(fmt.property(TEX_PROP_INDEX)))
        except Exception:
            return None

    def intrinsicSize(self, doc: QTextDocument, pos: int, fmt: QTextCharFormat) -> QSizeF:
        item = self._item(fmt)
        if item is None:
            return QSizeF(0.0, 0.0)
        box = item.box
        # The object is vertically centred on the line's text centre, k above the baseline;
        # choose its height so that both ascent and descent of the formula fit.
        h = max(2 * (box.ascent - item.k), 2 * (box.descent + item.k), 1.0)
        return QSizeF(box.width, h)

    def drawObject(self, painter: QPainter, rect: QRectF, doc: QTextDocument, pos: int,
                   fmt: QTextCharFormat) -> None:
        try:
            item = self._item(fmt)
            if item is None:
                return
            baseline = rect.center().y() + item.k
            block = doc.findBlock(pos)
            if block.isValid():
                layout = block.layout()
                line = layout.lineForTextPosition(pos - block.position())
                if line.isValid():
                    baseline = layout.position().y() + line.y() + line.ascent()
            item.box.paint(painter, rect.left(), baseline, self._color())
        except Exception:
            log.exception("formula paint failed")
