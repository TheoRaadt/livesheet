"""Symbol and command tables for the LaTeX subset (Qt-free). Own list of ordinary mathematical
notation; code points are standard Unicode."""

from __future__ import annotations

# name -> (text, atom class). Classes: ord, bin, rel, open, close, punct.
SYMBOLS: dict[str, tuple[str, str]] = {}


def _add(kind: str, pairs: str) -> None:
    for item in pairs.split():
        name, ch = item.split("=")
        SYMBOLS[name] = (ch, kind)


_GREEK_LOWER = ("alpha=α beta=β gamma=γ delta=δ epsilon=ϵ zeta=ζ eta=η theta=θ iota=ι kappa=κ "
                "lambda=λ mu=μ nu=ν xi=ξ pi=π rho=ρ sigma=σ tau=τ upsilon=υ phi=ϕ chi=χ psi=ψ "
                "omega=ω varepsilon=ε vartheta=ϑ varphi=φ varrho=ϱ varpi=ϖ varsigma=ς")
_GREEK_UPPER = "Gamma=Γ Delta=Δ Theta=Θ Lambda=Λ Xi=Ξ Pi=Π Sigma=Σ Upsilon=Υ Phi=Φ Psi=Ψ Omega=Ω"
_add("ord", _GREEK_LOWER)
_add("ord", _GREEK_UPPER)
GREEK_NAMES = frozenset(n for item in (_GREEK_LOWER + " " + _GREEK_UPPER).split() for n in [item.split("=")[0]])

_add("bin", "pm=± mp=∓ times=× cdot=⋅ div=÷ ast=∗ circ=∘ cup=∪ cap=∩ setminus=∖")
_add("rel", "le=≤ leq=≤ ge=≥ geq=≥ ne=≠ neq=≠ approx=≈ equiv=≡ sim=∼ simeq=≃ propto=∝ ll=≪ gg=≫ "
            "in=∈ notin=∉ ni=∋ subset=⊂ subseteq=⊆ supset=⊃ supseteq=⊇ perp=⊥ parallel=∥ "
            "to=→ rightarrow=→ leftarrow=← leftrightarrow=↔ Rightarrow=⇒ Leftarrow=⇐ "
            "Leftrightarrow=⇔ mapsto=↦ implies=⟹ iff=⟺")
_add("ord", "infty=∞ partial=∂ nabla=∇ forall=∀ exists=∃ neg=¬ emptyset=∅ hbar=ℏ ell=ℓ "
            "angle=∠ degree=° prime=′ ldots=… dots=… cdots=⋯ vdots=⋮ ddots=⋱")
# L2 extra symbols: only characters with a plain Unicode code point
_add("bin", "land=∧ wedge=∧ lor=∨ vee=∨ oplus=⊕ ominus=⊖ otimes=⊗ star=⋆ bullet=∙ cdotp=⋅ "
            "uplus=⊎ sqcup=⊔ sqcap=⊓ amalg=⨿")
_add("rel", "cong=≅ asymp=≍ doteq=≐ prec=≺ succ=≻ preceq=⪯ succeq=⪰ nsubseteq=⊈ nsupseteq=⊉ "
            "vdash=⊢ dashv=⊣ models=⊨ nless=≮ ngtr=≯ nleq=≰ ngeq=≱ nsim=≁ "
            "uparrow=↑ downarrow=↓ updownarrow=↕ Uparrow=⇑ Downarrow=⇓ nearrow=↗ searrow=↘ "
            "swarrow=↙ nwarrow=↖ hookrightarrow=↪ hookleftarrow=↩ longrightarrow=⟶ "
            "longleftarrow=⟵ longleftrightarrow=⟷ Longrightarrow=⟹ Longleftarrow=⟸ "
            "Longleftrightarrow=⟺ longmapsto=⟼")
_add("ord", "aleph=ℵ beth=ℶ Re=ℜ Im=ℑ wp=℘ top=⊤ bot=⊥ lnot=¬ varnothing=∅ complement=∁ "
            "dagger=† ddagger=‡ S=§ P=¶ copyright=© sharp=♯ flat=♭ natural=♮ imath=ı jmath=ȷ ")
_add("open", "langle=⟨ lfloor=⌊ lceil=⌈ lbrace={")
_add("close", "rangle=⟩ rfloor=⌋ rceil=⌉ rbrace=}")

# escaped characters (\{ is an opening brace symbol, \} a closing one)
SYMBOLS["{"] = ("{", "open")
SYMBOLS["}"] = ("}", "close")
SYMBOLS["|"] = ("‖", "ord")
for _c in "%&#_$":
    SYMBOLS[_c] = (_c, "ord")

# plain characters
CHARS: dict[str, tuple[str, str]] = {
    "+": ("+", "bin"), "-": ("−", "bin"), "*": ("∗", "bin"),
    "=": ("=", "rel"), "<": ("<", "rel"), ">": (">", "rel"), ":": (":", "rel"),
    "(": ("(", "open"), "[": ("[", "open"), ")": (")", "close"), "]": ("]", "close"),
    "|": ("|", "ord"), "/": ("/", "ord"), "!": ("!", "ord"), ".": (".", "ord"),
    ",": (",", "punct"), ";": (";", "punct"),
}

# spaces in em
SPACES: dict[str, float] = {",": 3 / 18, ":": 4 / 18, ";": 5 / 18, "!": -3 / 18, " ": 1 / 3,
                            "quad": 1.0, "qquad": 2.0}

FUNCTIONS = frozenset("sin cos tan cot sec csc arcsin arccos arctan sinh cosh tanh ln log exp "
                      "det dim gcd arg deg ker Pr mod".split())

# name -> (text, is_word, integral). Words are upright names; the rest are symbols.
BIG_OPERATORS: dict[str, tuple[str, bool, bool]] = {
    "sum": ("∑", False, False), "prod": ("∏", False, False),
    "int": ("∫", False, True), "iint": ("∬", False, True), "iiint": ("∭", False, True),
    "oint": ("∮", False, True), "bigcup": ("⋃", False, False), "bigcap": ("⋂", False, False),
    "lim": ("lim", True, False), "max": ("max", True, False), "min": ("min", True, False),
    "sup": ("sup", True, False), "inf": ("inf", True, False),
}

# delimiter token (char or command name) -> displayed text ("" is the null delimiter)
DELIMITERS: dict[str, str] = {
    "(": "(", ")": ")", "[": "[", "]": "]", "|": "|", ".": "", "/": "/", "<": "⟨", ">": "⟩",
    "{": "{", "}": "}", "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋",
    "lceil": "⌈", "rceil": "⌉", "lbrace": "{", "rbrace": "}", "lvert": "|", "rvert": "|",
}
CMD_DELIMS = {"|": "‖", "Vert": "‖", "vert": "|"}

SIZED = {"big": 1.2, "Big": 1.8, "bigg": 2.4, "Bigg": 3.0}

UNSUPPORTED = frozenset("newcommand renewcommand def usepackage color textcolor label ref tag eqno "
                        "verb input write href includegraphics documentclass".split())

# environments: name -> (left delimiter, right delimiter)
MATRIX_ENVS: dict[str, tuple[str, str]] = {
    "matrix": ("", ""), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
    "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"),
}
MAX_MATRIX = 50

ACCENTS = frozenset("hat bar vec dot ddot tilde overline underline overbrace underbrace".split())

# font command -> style tag stored on symbols
FONT_COMMANDS = {"mathrm": "rm", "mathbf": "bf", "mathit": "it", "mathbb": "bb",
                 "mathcal": "cal", "boldsymbol": "bs"}

_BB_HOLES = {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"}
_CAL_HOLES = {"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ", "L": "ℒ", "M": "ℳ", "R": "ℛ"}


def _alnum(ch: str, upper: int, lower: int, digit: int | None, holes: dict[str, str]) -> str:
    if "A" <= ch <= "Z":
        return holes.get(ch) or chr(upper + ord(ch) - ord("A"))
    if "a" <= ch <= "z":
        return chr(lower + ord(ch) - ord("a"))
    if "0" <= ch <= "9" and digit is not None:
        return chr(digit + ord(ch) - ord("0"))
    return ch


def _greek(ch: str, upper: int, lower: int) -> str:
    if "Α" <= ch <= "Ω" and ch != "\u03a2":
        return chr(upper + ord(ch) - ord("Α"))
    if "α" <= ch <= "ω":
        return chr(lower + ord(ch) - ord("α"))
    return ch


def style_char(ch: str, style: str) -> str:
    """Map one character to the mathematical-alphanumeric code point of ``style`` ("bf", "bs",
    "bb", "cal"); characters without such a form are returned unchanged. ``rm`` and ``it`` use
    the ordinary characters (the font is switched instead)."""
    if style == "bf":
        out = _alnum(ch, 0x1D400, 0x1D41A, 0x1D7CE, {})
        return _greek(out, 0x1D6A8, 0x1D6C2) if out == ch else out
    if style == "bs":
        out = _alnum(ch, 0x1D468, 0x1D482, 0x1D7CE, {})
        return _greek(out, 0x1D71C, 0x1D736) if out == ch else out
    if style == "bb":
        return _alnum(ch, 0x1D538, 0x1D552, 0x1D7D8, _BB_HOLES)
    if style == "cal":
        return _alnum(ch, 0x1D49C, ord(ch), None, _CAL_HOLES) if "A" <= ch <= "Z" else ch
    return ch


def style_text(text: str, style: str) -> str:
    return "".join(style_char(c, style) for c in text)


KIND_BY_CHAR: dict[str, str] = {}
for _text, _kind in list(SYMBOLS.values()) + list(CHARS.values()):
    KIND_BY_CHAR.setdefault(_text, _kind)
