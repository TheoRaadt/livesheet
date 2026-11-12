"""Qt-free LaTeX-subset scanner and parser used by text regions (spec 032)."""

from .errors import TexError
from .parse import parse, parse_cached
from .scan import MAX_SPAN_CHARS, MAX_SPANS, ScanResult, Span, display_text, scan

__all__ = ["TexError", "parse", "parse_cached", "scan", "display_text", "ScanResult", "Span",
           "MAX_SPAN_CHARS", "MAX_SPANS"]
