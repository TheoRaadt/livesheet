"""Display-notation tests for diff(...)/integrate(...) call shapes (pretty.py).

This is a pure GUI display change: the stored source text, the text shown while
editing, and engine evaluation are unaffected. See the task note for context: the
toolbar's d/dx and integral buttons insert ``diff(``/``integrate(`` literally; this
makes the *displayed* (non-editing) rendering of those calls use standard calculus
notation instead of showing the raw call text.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtWidgets import QApplication  # noqa: E402

from livesheet.gui.pretty import display_source, pretty_source_html  # noqa: E402
from livesheet.gui.regions import MathRegion  # noqa: E402

# --- bare pretty_source_html ------------------------------------------------------


def test_plain_derivative_notation():
    assert pretty_source_html("diff(x^2, x)") == "d/dx (x<sup>2</sup>)"
    assert pretty_source_html("diff(x, x)") == "d/dx (x)"


def test_plain_integral_notation():
    assert pretty_source_html("integrate(x^2, x)") == "∫ x<sup>2</sup> dx"


def test_nested_exponent_inside_derivative_and_integral():
    # EXPR keeps its own superscript formatting inside the d/dx (...) / ∫ ... dx wrapper.
    assert pretty_source_html("diff(x^3 + x^2, x)") == "d/dx (x<sup>3</sup> + x<sup>2</sup>)"
    assert pretty_source_html("integrate(x^3 - x^2, x)") == "∫ x<sup>3</sup> - x<sup>2</sup> dx"


def test_nth_derivative_notation():
    assert pretty_source_html("diff(x^3, x, 2)") == "d<sup>2</sup>/dx<sup>2</sup> (x<sup>3</sup>)"


def test_definite_integral_notation():
    assert pretty_source_html("integrate(x^2, (x, 0, 2))") == "∫<sub>0</sub><sup>2</sup> x<sup>2</sup> dx"


def test_definite_integral_notation_with_units_in_bounds():
    assert (
        pretty_source_html("integrate(x^2, (x, 0 m, 2 m))")
        == "∫<sub>0 m</sub><sup>2 m</sup> x<sup>2</sup> dx"
    )


def test_nested_diff_inside_integrate():
    assert pretty_source_html("integrate(diff(x^3, x), x)") == "∫ d/dx (x<sup>3</sup>) dx"


def test_postfix_keyword_form_is_left_untouched():
    # Only the function-call forms get the new notation; "-> diff, x" keeps the arrow.
    assert pretty_source_html("x^2 -> diff, x") == "x<sup>2</sup> → diff, x"
    assert pretty_source_html("x^2 -> integrate, x") == "x<sup>2</sup> → integrate, x"


def test_unrecognised_call_shapes_pass_through_unchanged():
    # diff with a single argument isn't one of the documented shapes; leave it alone.
    assert pretty_source_html("diff(x^2)") == "diff(x<sup>2</sup>)"


def test_calculus_notation_applied_to_display_source_result():
    # display_source strips the trailing "=" / bare "->"/"→" before pretty-printing,
    # exactly as MathRegion._show_display does.
    assert pretty_source_html(display_source("diff(x^2, x) =")) == "d/dx (x<sup>2</sup>)"
    assert pretty_source_html(display_source("integrate(x^2, (x, 0, 2)) ->")) == (
        "∫<sub>0</sub><sup>2</sup> x<sup>2</sup> dx"
    )


# --- through an actual MathRegion --------------------------------------------------


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_math_region_shows_calculus_notation_when_not_editing(app):
    region = MathRegion("diff(x^2, x) =")
    assert not region.editing
    # toPlainText() flattens <sup> styling to its plain character; the raised
    # rendering is confirmed via the actual superscript HTML Qt produces for it.
    assert region.editor.toPlainText() == "d/dx (x2)"
    html = region.editor.toHtml()
    assert "d/dx (x" in html
    assert 'vertical-align:super' in html


def test_math_region_shows_integral_notation_when_not_editing(app):
    region = MathRegion("integrate(x^2, (x, 0, 2)) ->")
    assert not region.editing
    assert region.editor.toPlainText() == "∫02 x2 dx"
    html = region.editor.toHtml()
    assert "∫" in html and " x" in html and " dx" in html
    assert 'vertical-align:sub' in html
    assert 'vertical-align:super' in html


def test_math_region_shows_raw_text_while_editing(app):
    source = "diff(x^2, x) ="
    region = MathRegion(source)
    region.start_editing()
    assert region.editing
    assert region.editor.toPlainText() == source
    region.finish_editing()
    assert not region.editing
    assert region.editor.toPlainText() == "d/dx (x2)"
