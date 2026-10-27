"""Turn SymPy values into compact, readable text for the worksheet."""

from __future__ import annotations

import math

import sympy as sp
from sympy.printing.str import StrPrinter

_SUP = str.maketrans("0123456789-+/", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ᐟ")

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lamda": "λ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "chi": "χ",
    "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

DEFAULT_SIGNIFICANT = 6


def superscript(value) -> str:
    return str(value).translate(_SUP)


def _fmt_real(v: float, sig: int) -> str:
    if v == 0:
        return "0"
    if math.isinf(v):
        return "∞" if v > 0 else "-∞"
    if math.isnan(v):
        return "NaN"
    a = abs(v)
    if 1e-4 <= a < 1e6:
        decimals = max(0, sig - 1 - math.floor(math.log10(a)))
        text = f"{v:.{decimals}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return "0" if text in ("-0", "") else text
    exp = math.floor(math.log10(a))
    mant = v / 10**exp
    if abs(round(mant, sig - 1)) >= 10:  # rounding pushed mantissa to 10
        exp += 1
        mant = v / 10**exp
    mtext = f"{mant:.{sig - 1}f}".rstrip("0").rstrip(".")
    return f"{mtext}×10{superscript(exp)}"


def format_number(value, sig: int = DEFAULT_SIGNIFICANT) -> str:
    """Format a numeric SymPy value (real or complex)."""
    value = sp.sympify(value)
    if value.is_Integer and abs(value) < 10**6:
        return str(value)
    if value is sp.zoo or value is sp.nan:
        return "undefined"
    if value in (sp.oo, -sp.oo):
        return "∞" if value is sp.oo else "-∞"
    num = sp.N(value, 17)
    re, im = num.as_real_imag()
    re_f, im_f = float(re), float(im)
    scale = max(abs(re_f), abs(im_f), 1e-300)
    if abs(im_f) <= 1e-14 * scale:
        return _fmt_real(re_f, sig)
    if abs(re_f) <= 1e-14 * scale:
        return _fmt_real(im_f, sig) + "i"
    sign = "+" if im_f >= 0 else "-"
    return f"{_fmt_real(re_f, sig)} {sign} {_fmt_real(abs(im_f), sig)}i"


class SheetPrinter(StrPrinter):
    """String printer with unicode powers, unit abbreviations and greek names."""

    def __init__(self, sig: int = DEFAULT_SIGNIFICANT):
        super().__init__({"order": None})
        self.sig = sig

    def _print_Quantity(self, expr):
        return str(expr.abbrev)

    def _print_Symbol(self, expr):
        name = expr.name
        base, _, sub = name.partition("_")
        base = GREEK.get(base, base)
        return base + ("_" + sub if sub else "")

    _print_Dummy = _print_Symbol

    def _print_Float(self, expr):
        from mpmath.libmp import prec_to_dps

        return _fmt_real(float(expr), min(self.sig, prec_to_dps(expr._prec)))

    def _print_Pow(self, expr, rational=False):
        exp = expr.exp
        if exp.is_Integer and 2 <= exp <= 9:
            from sympy.printing.precedence import PRECEDENCE

            base = self.parenthesize(expr.base, PRECEDENCE["Pow"], strict=True)
            return base + superscript(exp)
        return super()._print_Pow(expr, rational)

    def _print_Pi(self, expr):
        return "π"

    def _print_Exp1(self, expr):
        return "e"

    def _print_ImaginaryUnit(self, expr):
        return "i"

    def _print_Infinity(self, expr):
        return "∞"

    def _print_NegativeInfinity(self, expr):
        return "-∞"

    def _print_Equality(self, expr):
        return f"{self._print(expr.lhs)} = {self._print(expr.rhs)}"

    def _print_Abs(self, expr):
        return f"|{self._print(expr.args[0])}|"


def format_expr(expr, sig: int = DEFAULT_SIGNIFICANT) -> str:
    """Pretty one-line text for a symbolic expression."""
    text = SheetPrinter(sig).doprint(expr)
    text = text.replace("**", "^").replace("*", "·").replace("sqrt(", "√(")
    return text


def format_value(expr, sig: int = DEFAULT_SIGNIFICANT) -> str:
    """Format a list / matrix / scalar result."""
    if isinstance(expr, (list, tuple)):
        return "{" + ", ".join(format_expr(e, sig) for e in expr) + "}"
    return format_expr(expr, sig)


def format_table(columns: list[str], rows: list[list[str]]) -> str:
    """Plain monospaced text table: right-aligned cells, two spaces between columns."""
    widths = [len(c) for c in columns]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = ["  ".join(c.rjust(w) for c, w in zip(columns, widths))]
    lines.append("  ".join("-" * w for w in widths))
    lines.extend("  ".join(c.rjust(w) for c, w in zip(row, widths)) for row in rows)
    return "\n".join(lines)


def format_grid(rows: list[list[str]], unit: str = "") -> str:
    """Matrix as a bracketed grid: right-aligned cells of equal column width, unit after the bracket."""
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
    body = ["  ".join(cell.rjust(w) for cell, w in zip(r, widths)) for r in rows]
    n = len(body)
    if n == 1:
        left, right = ["["], ["]"]
    else:
        left = ["⎡"] + ["⎢"] * (n - 2) + ["⎣"]
        right = ["⎤"] + ["⎥"] * (n - 2) + ["⎦"]
    lines = [f"{l} {b} {r}" for l, b, r in zip(left, body, right)]
    if unit:
        lines[-1] += " " + unit
    return "\n".join(lines)
