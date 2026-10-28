"""Spec 004 phase A2 black-box GUI tests: criteria 24-27 and the GUI-relevant "Phase A edge
cases" (empty-spec hint mapping, single-point dot, descending range, text mentioning 'plot' not
special). Written from docs/board/specs/004-plots.md, independent of the implementation; the only
implementation names used are the small public helpers the spec itself describes as the GUI's job
(``STARTER_TEXT``, ``HINT_TEXT``, ``is_blank_spec``), plus the documented engine API (``PlotData``,
``PlotTrace``, ``nice_axis``). Qt-dependent tests skip gracefully when PySide6 cannot load, as the
existing GUI tests (tests/test_gui.py, tests/test_gui_helpers.py) do.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtTest  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QGraphicsScene  # noqa: E402

from livesheet.engine import Engine, RegionResult  # noqa: E402
from livesheet.engine.plotting import PlotData, PlotTrace, nice_axis  # noqa: E402
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.plotregion import HINT_TEXT, STARTER_TEXT, PlotRegion, is_blank_spec  # noqa: E402
from livesheet.gui.plotview import paint_plot  # noqa: E402
from livesheet.gui.regions import COLOR_ERROR  # noqa: E402

SHEET_1 = ["v := 3 m/s", "t := 0 s to 10 s step 2 s"]
PLOT_1 = "plot\nover t\nshow v*t"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _qt_window():
    app = _ensure_app()
    win = MainWindow()
    win.resize(900, 700)
    win.show()
    app.processEvents()
    return app, win


def _settle(app, win):
    from PySide6.QtTest import QTest

    app.processEvents()
    QTest.qWait(50)
    win.view.grab()
    app.processEvents()


def _non_white_pixels(image: QImage) -> int:
    white = QColor("white").rgb()
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixel(x, y) != white:
                count += 1
    return count


def _render(data: PlotData, size: tuple[int, int] = (400, 260)) -> QImage:
    image = QImage(*size, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    try:
        paint_plot(painter, QRectF(0, 0, *size), data)
    finally:
        painter.end()
    return image


# ---------------------------------------------------------------------------
# Criterion 24: paint_plot pixel threshold and robustness
# ---------------------------------------------------------------------------

def test_paint_plot_criterion_1_data_leaves_more_than_500_pixels():
    _ensure_app()
    data = Engine().evaluate(enumerate([*SHEET_1, PLOT_1]))[2].plot
    assert data is not None
    image = _render(data)
    assert _non_white_pixels(image) > 500


def test_paint_plot_single_point_does_not_raise():
    _ensure_app()
    trace = PlotTrace(label="p", x=[3.0], y=[3.0], style_index=0)
    xlo, xhi, xticks = nice_axis(3.0, 3.0)
    ylo, yhi, yticks = nice_axis(3.0, 3.0)
    data = PlotData("", "x", "y", "", "", [trace], (xlo, xhi), (ylo, yhi), xticks, yticks)
    image = _render(data)
    assert _non_white_pixels(image) > 0  # frame plus the single-point dot


def test_paint_plot_all_constant_data_does_not_raise():
    _ensure_app()
    trace = PlotTrace(label="c", x=[0.0, 1.0, 2.0, 3.0], y=[5.0, 5.0, 5.0, 5.0], style_index=0)
    xlo, xhi, xticks = nice_axis(0.0, 3.0)
    ylo, yhi, yticks = nice_axis(5.0, 5.0)
    data = PlotData("", "x", "y", "", "", [trace], (xlo, xhi), (ylo, yhi), xticks, yticks)
    _render(data)  # must not raise


def test_paint_plot_trace_with_nan_gap_does_not_raise():
    _ensure_app()
    trace = PlotTrace(label="g", x=[0.0, 1.0, 2.0, 3.0], y=[0.0, float("nan"), 2.0, 3.0], style_index=0)
    xlo, xhi, xticks = nice_axis(0.0, 3.0)
    ylo, yhi, yticks = nice_axis(0.0, 3.0)
    data = PlotData("", "x", "y", "", "", [trace], (xlo, xhi), (ylo, yhi), xticks, yticks)
    image = _render(data)
    assert _non_white_pixels(image) > 0  # the two separate runs are still drawn


def test_paint_plot_manual_limits_excluding_all_data_still_draws_frame():
    _ensure_app()
    data = Engine().evaluate(enumerate([*SHEET_1, PLOT_1 + "\nxlim 100 s to 200 s"]))[2].plot
    assert data is not None  # out-of-range manual limits are not an engine error
    image = _render(data)
    assert _non_white_pixels(image) > 0  # frame and ticks are drawn even with no visible data


# ---------------------------------------------------------------------------
# Criterion 25: Insert > Plot, editing, live update, save/reload
# ---------------------------------------------------------------------------

def test_insert_plot_menu_action_adds_one_region_with_starter_text():
    app, win = _qt_window()
    try:
        insert_menu = next(a.menu() for a in win.menuBar().actions() if a.text() == "&Insert")
        plot_action = next(a for a in insert_menu.actions() if a.text() == "&Plot")
        assert win.sheet.regions() == []
        plot_action.trigger()
        app.processEvents()
        regions = win.sheet.regions()
        assert len(regions) == 1
        region = regions[0]
        assert region.kind == "plot"
        assert region.source == STARTER_TEXT
        assert region.editing
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_editing_spec_live_update_and_save_reload(tmp_path):
    app, win = _qt_window()
    try:
        sheet = win.sheet
        v_region = sheet.add_region("math", QPointF(40, 40), SHEET_1[0])
        sheet.add_region("math", QPointF(40, 90), SHEET_1[1])

        plot_region = sheet.insert_plot_at(QPointF(40, 150))  # below both math regions
        assert plot_region.source == STARTER_TEXT
        plot_region.editor.setPlainText(PLOT_1)
        assert plot_region.source == PLOT_1
        plot_region.finish_editing()
        _settle(app, win)
        assert plot_region.result is not None and plot_region.result.plot is not None
        assert len(plot_region.result.plot.traces[0].x) == 6

        # "changing v in the math region above updates the plot data without any other action":
        before = plot_region.result.plot
        v_region.start_editing()
        v_region.editor.setPlainText("v := 6 m/s")
        v_region.finish_editing()  # the ordinary editingFinished -> recalculate() path only
        _settle(app, win)
        after = plot_region.result.plot
        assert after is not before
        assert after.traces[0].y[-1] == pytest.approx(60.0)

        plot_region.set_size(440, 300)
        path = tmp_path / "p.lsheet"
        sheet.to_document().save(path)
        win.open_path(path)
        reloaded = next(r for r in win.sheet.regions() if isinstance(r, PlotRegion))
        assert reloaded.source == PLOT_1
        assert (reloaded.size_w, reloaded.size_h) == (440.0, 300.0)
    finally:
        win.sheet.set_modified(False)
        win.close()


# ---------------------------------------------------------------------------
# Criterion 26: delete via Backspace does not crash (regression for G4)
# ---------------------------------------------------------------------------

def test_delete_selected_plot_region_backspace_does_not_crash():
    app, win = _qt_window()
    try:
        sheet = win.sheet
        sheet.add_region("math", QPointF(40, 40), SHEET_1[0])
        sheet.add_region("math", QPointF(40, 90), SHEET_1[1])
        plot_region = sheet.add_region("plot", QPointF(40, 150), PLOT_1)
        sheet.recalculate()
        _settle(app, win)
        assert plot_region.result is not None and plot_region.result.plot is not None

        sheet.clearSelection()
        plot_region.setSelected(True)
        app.processEvents()
        win.view.grab()
        app.sendEvent(sheet, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
        _settle(app, win)

        assert plot_region not in sheet.regions()
        doc = sheet.to_document()
        assert all(r.kind != "plot" for r in doc.regions)
    finally:
        win.sheet.set_modified(False)
        win.close()


# ---------------------------------------------------------------------------
# Criterion 27: PDF export
# ---------------------------------------------------------------------------

def test_pdf_export_with_plot_starts_with_pdf_header_and_is_larger(tmp_path):
    app, win = _qt_window()
    try:
        sheet = win.sheet
        sheet.add_region("math", QPointF(40, 40), SHEET_1[0])
        sheet.add_region("math", QPointF(40, 90), SHEET_1[1])
        sheet.recalculate()
        _settle(app, win)

        without_path = tmp_path / "without_plot.pdf"
        export_pdf(sheet, str(without_path))
        without_bytes = without_path.read_bytes()
        assert without_bytes.startswith(b"%PDF")

        sheet.add_region("plot", QPointF(40, 150), PLOT_1)
        sheet.recalculate()
        _settle(app, win)
        with_path = tmp_path / "with_plot.pdf"
        export_pdf(sheet, str(with_path))
        with_bytes = with_path.read_bytes()
        assert with_bytes.startswith(b"%PDF")
        assert len(with_bytes) > len(without_bytes)
    finally:
        win.sheet.set_modified(False)
        win.close()


# ---------------------------------------------------------------------------
# Phase A edge cases (GUI-relevant)
# ---------------------------------------------------------------------------

def test_is_blank_spec_matches_only_bare_keyword_lines():
    assert is_blank_spec("plot")
    assert is_blank_spec(STARTER_TEXT)  # "plot\nover \nshow "
    assert not is_blank_spec("plot\nover t")
    assert not is_blank_spec("plot\nover t\nshow t")
    assert not is_blank_spec("")  # no 'plot' first line at all


def test_empty_spec_maps_to_hint_not_error(monkeypatch):
    """Spec: 'the GUI maps that single ["over"] message to the hint only when the spec has no
    other lines'. A bare 'plot' spec must show HINT_TEXT, never the raw engine error."""
    _ensure_app()
    from livesheet.gui import plotregion

    calls = []
    monkeypatch.setattr(plotregion, "paint_message",
                        lambda painter, rect, text, color, *a, **kw: calls.append((text, color)))
    scene = QGraphicsScene()
    region = PlotRegion("plot")
    scene.addItem(region)
    region.set_result(RegionResult(status="error", error="A plot needs an 'over' line."))

    image = QImage(60, 60, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    try:
        region.paint(painter, None)
    finally:
        painter.end()

    assert calls, "paint_message was never called for the empty spec"
    text, color = calls[-1]
    assert text == HINT_TEXT and color == "#7a7a7a"


def test_nonblank_spec_error_keeps_error_colour_not_hint(monkeypatch):
    """A spec with real content that still errors (e.g. an undefined name) must show the engine
    error message in the error colour, not the empty-spec hint."""
    _ensure_app()
    from livesheet.gui import plotregion

    calls = []
    monkeypatch.setattr(plotregion, "paint_message",
                        lambda painter, rect, text, color, *a, **kw: calls.append((text, color)))
    scene = QGraphicsScene()
    region = PlotRegion("plot\nover t\nshow nonsense(t)")
    scene.addItem(region)
    region.set_result(RegionResult(status="error", error="t is not defined"))

    image = QImage(60, 60, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    try:
        region.paint(painter, None)
    finally:
        painter.end()

    assert calls and calls[-1] == ("t is not defined", COLOR_ERROR)


def test_text_region_mentioning_plot_is_not_evaluated():
    """'text regions mentioning plot are not special': a text region's content must never be fed
    to the engine, no matter which plot keywords it contains."""
    app, win = _qt_window()
    try:
        sheet = win.sheet
        sheet.add_region("text", QPointF(40, 40), "<p>plot over show xlim ylim title</p>")
        sheet.add_region("math", QPointF(40, 200), "1 + 1 =")
        sheet.recalculate()
        _settle(app, win)
        results = [r.result for r in sheet.regions() if hasattr(r, "result")]
        assert len(results) == 1 and results[0].output == "= 2"
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_variable_named_plot_is_unaffected_inside_a_plot_spec():
    """'plot' is only special as the statement's own first line (criterion 20); a variable of
    that name used inside a 'show' line keeps its ordinary meaning."""
    _ensure_app()
    res = Engine().evaluate(enumerate(["plot := 3 m/s", "t := 0 s to 4 s step 2 s",
                                        "plot\nover t\nshow plot*t"]))
    assert res[2].status == "ok"
    assert res[2].plot.traces[0].y == pytest.approx([0.0, 6.0, 12.0])


def test_descending_range_plot_renders_without_crash():
    """Descending ranges plot in the order given; limits still come from min/max."""
    _ensure_app()
    res = Engine().evaluate(enumerate(["r := 10 to 0 step -5", "plot\nover r\nshow r"]))
    data = res[1].plot
    assert data is not None
    assert data.traces[0].x == pytest.approx([10.0, 5.0, 0.0])
    assert data.x_limits == (0, 10)
    image = _render(data)
    assert _non_white_pixels(image) > 0
