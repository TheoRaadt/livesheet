"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSettings, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QKeySequence,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..document import FILE_SUFFIX, DocumentError, SheetDocument
from .icons import glyph_icon
from .toolbarstyle import ToolbarStyler
from .paths import default_save_path, remembered_dir
from .regions import MathRegion
from .sidepanel import SidePanel
from .theme import MODE_DARK, MODE_LIGHT, MODE_SYSTEM, apply_theme
from ..engine.pagination import PAGE_HEIGHT
from .worksheet import PAGE_WIDTH, PageBreakItem, Worksheet, WorksheetView

APPEARANCE_MODES = ((MODE_SYSTEM, "Follow System"), (MODE_LIGHT, "Light"), (MODE_DARK, "Dark"))

FILE_FILTER = f"LiveSheet worksheets (*{FILE_SUFFIX});;All files (*)"

# Spec 011's two Greek-letter keyboard-shortcut layers: letter -> the GREEK name it inserts.
# Layer 1 (Ctrl+Shift+<letter>): only letters that are both unique among the 23 lowercase Greek
# names and not already claimed by an existing Ctrl+Shift+ app shortcut. The spec's own list of
# already-claimed letters (A/P/M/C/E) missed one: "Save As" resolves QKeySequence::StandardKey
# .SaveAs to "Ctrl+Shift+S" on this platform (a Qt standard key, not a literal string, so it
# does not show up by grepping the codebase for "Ctrl+Shift+") -- confirmed by a real
# QApplication raising "Ambiguous shortcut overload" the moment both existed. "S" (sigma) is
# therefore excluded here too, by the spec's own stated rule, the same way A/P/M/C/E already are;
# sigma stays fully reachable via layer 2's Ctrl+Alt+S instead. Flagged as a developer-found
# deviation from the spec's own table (see docs/board/log.md).
GREEK_SHORTCUTS_CTRL_SHIFT: tuple[tuple[str, str], ...] = (
    ("B", "beta"), ("G", "gamma"), ("D", "delta"), ("Z", "zeta"), ("I", "iota"), ("K", "kappa"),
    ("L", "lambda"), ("N", "nu"), ("X", "xi"), ("R", "rho"), ("U", "upsilon"),
)
# Layer 2 (Ctrl+Alt+<letter>, Theo's decision): full coverage of all 23 lowercase Greek names,
# under a modifier combination otherwise unused anywhere in livesheet/gui/.
GREEK_SHORTCUTS_CTRL_ALT: tuple[tuple[str, str], ...] = (
    ("A", "alpha"), ("B", "beta"), ("C", "chi"), ("D", "delta"), ("E", "epsilon"), ("G", "gamma"),
    ("H", "eta"), ("I", "iota"), ("K", "kappa"), ("L", "lambda"), ("M", "mu"), ("N", "nu"),
    ("O", "omicron"), ("P", "phi"), ("Q", "psi"), ("R", "rho"), ("S", "sigma"), ("T", "theta"),
    ("U", "upsilon"), ("W", "omega"), ("X", "xi"), ("Y", "tau"), ("Z", "zeta"),
)

HELP_HTML = """
<h3>LiveSheet syntax</h3>
<p>Click anywhere to place the red cross, then start typing. One statement per math region;
regions are calculated page by page, left to right and then top to bottom.</p>
<table cellspacing="6">
<tr><td><code>x := 5 m</code></td><td>definition (typing <b>:</b> inserts <code>:=</code>)</td></tr>
<tr><td><code>f(x, y) := x^2 + y</code></td><td>function definition</td></tr>
<tr><td><code>g ≡ 9.81 m/s^2</code></td><td>global definition, visible everywhere (type <b>~</b> or <b>::</b>)</td></tr>
<tr><td><code>x =</code></td><td>numeric result</td></tr>
<tr><td><code>v = km/hr</code></td><td>numeric result in a chosen unit</td></tr>
<tr><td><code>a := 2 m =</code></td><td>define and show</td></tr>
<tr><td><code>(x+1)^2 →</code></td><td>symbolic result (type <code>-&gt;</code> or Ctrl+.)</td></tr>
<tr><td><code>x^2 - 1 → factor</code></td><td>keywords: simplify, expand, factor, collect, x, solve, x,
partfrac, x, float, n, diff, x, integrate, x, series, x, n, substitute, x = 2</td></tr>
<tr><td><code>x^2 == 4 → solve, x</code></td><td>equations use <code>==</code></td></tr>
<tr><td><code>"</code></td><td>start a text region (Ctrl+Enter ends it)</td></tr>
</table>
<p><b>Functions:</b> sin cos tan asin acos atan atan2 sinh cosh tanh exp ln log (base 10) sqrt root
abs floor ceil mod Max Min factorial binomial re im conj arg diff integrate limit sum product solve.</p>
<p><b>Units:</b> m km cm mm um inch ft mi · kg gm mg tonne lb · s ms min hr day yr ·
N kN MN lbf · Pa kPa MPa GPa bar mbar atm psi · J kJ MJ Wh kWh MWh cal · W kW MW ·
A mA V kV ohm Ω C F uF Wb T H · Hz kHz MHz rpm · K mol cd · L mL ha · rad deg ·
g (standard gravity). Your own definitions override unit names.</p>
<p><b>Keys:</b> Enter ends a math region · Esc stops editing · double-click edits ·
drag to move · Delete removes selected · arrows move cross or selection · F9 recalculates ·
Ctrl+wheel zooms.</p>
"""


class _ClickableLabel(QLabel):
    """A plain status-bar label that also reacts to a left click (spec 007's precision label)."""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, path: str | None = None):
        super().__init__()
        self.sheet = Worksheet(self)
        self.view = WorksheetView(self.sheet, self)
        central = QWidget()
        self._central_layout = QVBoxLayout(central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)
        self._central_layout.addWidget(self.view)
        self.setCentralWidget(central)
        self.path: Path | None = None
        self.settings = QSettings("LiveSheet", "LiveSheet")

        self._eval_label = QLabel("Ready")
        self._eval_label.setObjectName("status-eval-label")
        self._precision_label = _ClickableLabel()
        self._precision_label.setObjectName("status-precision-label")
        self._precision_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._precision_label.clicked.connect(self.set_precision)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setObjectName("status-zoom-label")
        self.statusBar().addPermanentWidget(self._eval_label)
        self.statusBar().addPermanentWidget(self._precision_label)
        self.statusBar().addPermanentWidget(self._zoom_label)
        self._refresh_precision_label()
        self.sheet.statusMessage.connect(lambda m: self.statusBar().showMessage(m))
        self.sheet.modifiedChanged.connect(lambda _: self._update_title())
        self.sheet.evaluationFinished.connect(self._on_evaluation_finished)
        self.view.zoomChanged.connect(lambda z: self._zoom_label.setText(f"{round(z * 100)}%"))

        self._build_actions()
        self.resize(PAGE_WIDTH + 120, 900)
        self._update_title()
        if path:
            self.open_path(Path(path))
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        window_state = self.settings.value("window_state")
        if window_state is not None:
            self.restoreState(window_state)
            self._repair_floating_toolbars()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        panel = getattr(self, "side_panel", None)
        if panel is not None:   # the band's height clamp depends on the window height
            panel.update_band_height()

    def _repair_floating_toolbars(self) -> None:
        """Defend against a corrupted saved layout (spec 007 D1; simplified by spec 011's removal
        of the Math toolbar, so there is now only one toolbar to validate): a toolbar that a live
        drag left floating -- rather than cleanly redocked -- gets its saved state replayed by
        ``restoreState()`` on every future launch, including the "floating" bit, independent of
        the `setFloatable(False)` guard set at construction time (that guard only stops a *new*
        drag from detaching a toolbar; it does not retroactively validate bytes an old/corrupted
        session already saved). If restoring the saved state left the Standard toolbar floating,
        its layout is reset to the one default, known-good arrangement.
        """
        if not self.standard_toolbar.isFloating():
            return
        self.removeToolBar(self.standard_toolbar)
        self.addToolBar(self.standard_toolbar)
        self.standard_toolbar.show()

    # -- UI construction --------------------------------------------------------

    def _action(self, text, slot, shortcut=None, tip=None) -> QAction:
        act = QAction(text, self)
        act.triggered.connect(slot)
        if shortcut is not None:
            act.setShortcut(shortcut)
        if tip:
            act.setStatusTip(tip)
        return act

    def _build_actions(self) -> None:
        SK = QKeySequence.StandardKey
        mb = self.menuBar()

        m = mb.addMenu("&File")
        self.action_new = self._action("&New", self.new_file, SK.New)
        m.addAction(self.action_new)
        self.action_open = self._action("&Open…", self.open_file, SK.Open)
        m.addAction(self.action_open)
        self.recent_menu = m.addMenu("Open &Recent")
        self._refresh_recent()
        m.addSeparator()
        self.action_save = self._action("&Save", self.save_file, SK.Save)
        m.addAction(self.action_save)
        m.addAction(self._action("Save &As…", self.save_file_as, SK.SaveAs))
        self.action_export_pdf = self._action("&Export PDF…", self.export_pdf, "Ctrl+Shift+E")
        m.addAction(self.action_export_pdf)
        m.addSeparator()
        m.addAction(self._action("&Quit", self.close, SK.Quit))

        m = mb.addMenu("&Edit")
        m.addAction(self._action("&Delete Region", self.delete_selected, None))
        m.addAction(self._action("Select &All Regions", self.select_all, "Ctrl+Shift+A"))

        m = mb.addMenu("&Insert")
        m.addAction(self._action("&Math Region", lambda: self.sheet.insert_region("math"), "Ctrl+M"))
        m.addAction(self._action("&Text Region", lambda: self.sheet.insert_region("text"), "Ctrl+T"))
        m.addAction(self._action("&Plot", lambda: self.sheet.insert_region("plot"), "Ctrl+Shift+P"))
        m.addAction(self._action("&Matrix…",
                                  lambda: self.sheet.insert_matrix_at(self.sheet.crosshair.pos()),
                                  "Ctrl+Shift+M"))
        m.addAction(self._action("&Component…",
                                  lambda: self.sheet.insert_component_at(self.sheet.crosshair.pos()),
                                  "Ctrl+Shift+C"))
        m.addAction(self._action("Page &Break", lambda: self.sheet.insert_page_break(), "Ctrl+Return"))
        m.addSeparator()
        for label, token in ((":=  Definition", ":= "), ("≡  Global definition", "≡ "),
                             ("=  Evaluate", " ="), ("→  Symbolic", " → ")):
            m.addAction(self._action(label, lambda _=False, t=token: self.insert_token(t)))

        m = mb.addMenu("&Calculate")
        self.action_recalculate = self._action("&Recalculate", self.sheet.recalculate, "F9")
        m.addAction(self.action_recalculate)
        m.addAction(self._action("Result &Precision…", self.set_precision))

        view_menu = mb.addMenu("&View")
        view_menu.addAction(self._action("Zoom &In", lambda: self.view.set_zoom(self.view.zoom() * 1.1), SK.ZoomIn))
        view_menu.addAction(self._action("Zoom &Out", lambda: self.view.set_zoom(self.view.zoom() / 1.1), SK.ZoomOut))
        view_menu.addAction(self._action("&Actual Size", lambda: self.view.set_zoom(1.0), "Ctrl+0"))

        m = mb.addMenu("&Help")
        m.addAction(self._action("&Syntax && Keys", self.show_help, SK.HelpContents))
        m.addAction(self._action("&About LiveSheet", self.show_about))

        # -- toolbars (spec 007, phase G1): the Standard toolbar reuses the exact File/Calculate
        # QAction objects above, so a toolbar click and the matching menu click are always the
        # identical command, not two separate implementations of it.
        self.standard_toolbar = QToolBar("Standard", self)
        self.standard_toolbar.setObjectName("standard-toolbar")
        # Movable (can be dragged to reorder/relocate) but not floatable: letting a toolbar
        # become a free-floating window is what let a live in-area drag drop it into a broken,
        # overlapping-with-the-docked-area floating state (see docs/board/log.md, spec 007 D1).
        # Reordering between docked positions still works with floating disabled.
        self.standard_toolbar.setFloatable(False)
        self.addToolBar(self.standard_toolbar)
        self.standard_toolbar.addAction(self.action_new)
        self.standard_toolbar.addAction(self.action_open)
        self.standard_toolbar.addAction(self.action_save)
        self.standard_toolbar.addSeparator()
        self.standard_toolbar.addAction(self.action_export_pdf)
        self.standard_toolbar.addSeparator()
        self.standard_toolbar.addAction(self.action_recalculate)
        # Spec 025: own vector icons + short labels; menus keep their text-only look.
        for act, glyph in ((self.action_new, "new"), (self.action_open, "open"),
                           (self.action_save, "save"), (self.action_export_pdf, "export"),
                           (self.action_recalculate, "recalculate")):
            act.setIcon(glyph_icon(glyph))
        self.toolbar_styler = ToolbarStyler(self.standard_toolbar, {
            self.action_new: "New", self.action_open: "Open", self.action_save: "Save",
            self.action_export_pdf: "Export PDF", self.action_recalculate: "Recalculate"})

        # -- Greek-letter keyboard shortcuts (spec 011 addenda 1/2): no visible menu entry of
        # their own (purely keyboard shortcuts), registered directly on the window so they fire
        # regardless of which menu/toolbar/dock has focus.
        for letter, name in GREEK_SHORTCUTS_CTRL_SHIFT:
            self.addAction(self._action(name, lambda _=False, t=name: self.insert_token(t),
                                        f"Ctrl+Shift+{letter}"))
        for letter, name in GREEK_SHORTCUTS_CTRL_ALT:
            self.addAction(self._action(name, lambda _=False, t=name: self.insert_token(t),
                                        f"Ctrl+Alt+{letter}"))

        # -- side panel (phase G2) --------------------------------------------------
        self.side_panel = SidePanel(self.insert_token, self)
        self.side_panel.attach_sheet(self.sheet, self.view)
        self._central_layout.insertWidget(0, self.side_panel)   # strip+band above the canvas
        self.view.setMinimumWidth(400)
        # The active tab and the panel's visibility are tracked in our own settings keys.
        tabs = self.side_panel.tabs
        saved_tab = self.settings.value("side_panel_tab", 0, type=int)
        tabs.setCurrentIndex(min(max(saved_tab, 0), tabs.count() - 1))
        visible = self.settings.value("side_panel_visible", True, type=bool)
        self.side_panel.setVisible(visible)
        self.side_panel.toggleViewAction().toggled.connect(
            lambda v: self.settings.setValue("side_panel_visible", v))
        self.side_panel.tabs.currentChanged.connect(
            lambda i: self.settings.setValue("side_panel_tab", i))

        view_menu.addSeparator()
        standard_toggle = self.standard_toolbar.toggleViewAction()
        standard_toggle.setText("Standard Toolbar")
        view_menu.addAction(standard_toggle)
        side_panel_toggle = self.side_panel.toggleViewAction()
        side_panel_toggle.setText("Side Panel")
        view_menu.addAction(side_panel_toggle)

        # -- appearance (phase G3) --------------------------------------------------
        appearance_menu = view_menu.addMenu("Appearance")
        appearance_group = QActionGroup(self)
        appearance_group.setExclusive(True)
        current = self.settings.value("appearance", MODE_SYSTEM, type=str)
        self._appearance_actions: dict[str, QAction] = {}
        for mode, label in APPEARANCE_MODES:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(mode == current)
            act.triggered.connect(lambda _checked=False, m=mode: self._set_appearance(m))
            appearance_group.addAction(act)
            appearance_menu.addAction(act)
            self._appearance_actions[mode] = act

    # -- commands ------------------------------------------------------------------

    def insert_token(self, token: str) -> None:
        region = self.sheet.editing_region()
        if not isinstance(region, MathRegion):
            region = self.sheet.insert_region("math")
        region.editor.textCursor().insertText(token)
        region.editor.setFocus()

    def delete_selected(self) -> None:
        self.sheet.remove_regions([r for r in self.sheet.regions() if r.isSelected()])
        self.sheet.remove_page_breaks(
            [i for i in self.sheet.selectedItems() if isinstance(i, PageBreakItem)])

    def select_all(self) -> None:
        for r in self.sheet.regions():
            r.setSelected(True)

    def set_precision(self) -> None:
        digits, ok = QInputDialog.getInt(self, "Result precision", "Significant digits:",
                                         self.sheet.significant, 2, 15)
        if ok:
            self.sheet.set_significant(digits)
            self._refresh_precision_label()

    def _refresh_precision_label(self) -> None:
        self._precision_label.setText(f"{self.sheet.significant} sig. figs")

    def _on_evaluation_finished(self, errors: int, total: int, elapsed_ms: float) -> None:
        """Update the permanent evaluation-status indicator (spec 007, phase G1).

        A pass measured at over 300 ms flashes "Calculating…" for one event-loop tick before the
        final Ready/N-errors text, rather than literally live during the (synchronous, blocking)
        pass itself -- genuine mid-pass progress would need the engine call to be interruptible or
        run off the UI thread, which this chrome-only spec does not add. A pass under the
        threshold goes straight to its final text with no flicker.
        """
        text = "Ready" if errors == 0 else f"{errors} error" if errors == 1 else f"{errors} errors"
        if elapsed_ms > 300:
            self._eval_label.setText("Calculating…")
            QTimer.singleShot(0, lambda: self._eval_label.setText(text))
        else:
            self._eval_label.setText(text)

    def _set_appearance(self, mode: str) -> None:
        self.settings.setValue("appearance", mode)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, mode)

    def new_file(self) -> None:
        if not self._maybe_save():
            return
        self.sheet.clear_sheet()
        self.sheet.recalculate()
        self.sheet.set_modified(False)
        self.path = None
        self._update_title()

    def open_file(self) -> None:
        if not self._maybe_save():
            return
        start = str(self.path.parent) if self.path else str(Path.home())
        name, _ = QFileDialog.getOpenFileName(self, "Open worksheet", start, FILE_FILTER)
        if name:
            self.open_path(Path(name))

    def open_path(self, path: Path) -> None:
        try:
            doc = SheetDocument.load(path)
        except (OSError, DocumentError) as exc:
            QMessageBox.critical(self, "Open failed", f"Could not open {path.name}:\n{exc}")
            return
        self.sheet.load_document(doc)
        self._refresh_precision_label()
        QTimer.singleShot(0, self._scroll_home)
        self.path = path
        self._add_recent(path)
        self._update_title()

    def save_file(self) -> bool:
        if self.path is None:
            return self.save_file_as()
        return self._write(self.path)

    def _default_save(self, suffix: str) -> Path:
        """Suggested path for a save dialog: last used folder or Documents, never an existing file."""
        docs = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        last = self.settings.value("last_dir", "", type=str)
        return default_save_path(self.path, last, Path(docs or Path.home()), suffix)

    def _remember_dir(self, saved: Path) -> None:
        folder = remembered_dir(saved)
        if folder:
            self.settings.setValue("last_dir", folder)

    def save_file_as(self) -> bool:
        start = str(self._default_save(FILE_SUFFIX))
        name, _ = QFileDialog.getSaveFileName(self, "Save worksheet", start, FILE_FILTER)
        if not name:
            return False
        path = Path(name)
        if path.suffix != FILE_SUFFIX:
            path = path.with_suffix(FILE_SUFFIX)
        self._remember_dir(path)
        return self._write(path)

    def _write(self, path: Path) -> bool:
        editing = self.sheet.editing_region()
        if editing is not None:
            editing.finish_editing()
        try:
            self.sheet.to_document().save(path)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        self.path = path
        self.sheet.set_modified(False)
        self._add_recent(path)
        self._update_title()
        self.statusBar().showMessage(f"Saved {path.name}", 3000)
        return True

    def export_pdf(self) -> None:
        start = str(self._default_save(".pdf"))
        name, _ = QFileDialog.getSaveFileName(self, "Export PDF", start, "PDF (*.pdf)")
        if name:
            self._remember_dir(Path(name))
            export_pdf(self.sheet, name)
            self.statusBar().showMessage(f"Exported {Path(name).name}", 3000)

    def show_help(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("LiveSheet help")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(HELP_HTML)
        box.exec()

    def show_about(self) -> None:
        QMessageBox.about(self, "About LiveSheet",
                          f"<b>LiveSheet {__version__}</b><br>Live math worksheets with a SymPy engine."
                          "<br><a href='https://github.com/TheoRaadt/livesheet'>github.com/TheoRaadt/livesheet</a>")

    # -- housekeeping ----------------------------------------------------------------

    def _scroll_home(self) -> None:
        self.view.verticalScrollBar().setValue(0)
        self.view.horizontalScrollBar().setValue(0)

    def _update_title(self) -> None:
        name = self.path.name if self.path else "Untitled"
        self.setWindowTitle(f"{name}{' •' if self.sheet.modified else ''} — LiveSheet")

    def _maybe_save(self) -> bool:
        if not self.sheet.modified:
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes", "Save changes to this worksheet?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_file()
        return answer == QMessageBox.StandardButton.Discard

    def _recent(self) -> list[str]:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            value = [value]
        return [v for v in (value or []) if Path(v).exists()]

    def _add_recent(self, path: Path) -> None:
        items = [str(path)] + [p for p in self._recent() if p != str(path)]
        self.settings.setValue("recent", items[:8])
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        self.recent_menu.clear()
        for p in self._recent():
            self.recent_menu.addAction(self._action(Path(p).name, lambda _=False, q=p: self._open_recent(q)))
        self.recent_menu.setEnabled(bool(self.recent_menu.actions()))

    def _open_recent(self, path: str) -> None:
        if self._maybe_save():
            self.open_path(Path(path))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save():
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState())
            event.accept()
        else:
            event.ignore()


def pdf_strips(breaks: list[float], bottom: float, page_h: float) -> list[tuple[float, float]]:
    """The (top, height) scene strips to print, one per sheet (spec 021). Without breaks: the
    continuous canvas sliced into ``page_h`` strips. With breaks: each logical page is sliced from
    its own top and never spills into the next page; a break always starts a fresh sheet. Empty
    logical pages after the first are skipped."""
    if not breaks:
        out: list[tuple[float, float]] = []
        top = 0.0
        while True:
            out.append((top, page_h))
            top += page_h
            if top >= bottom:
                return out
    starts = [0.0] + list(breaks)
    out = []
    for i, start in enumerate(starts):
        end = min(starts[i + 1], bottom) if i + 1 < len(starts) else bottom
        if i and end <= start:
            continue
        top = start
        while True:
            out.append((top, min(page_h, max(end - top, 0.0)) if end > top else page_h))
            top += page_h
            if top >= end:
                break
    return out


def export_pdf(sheet: Worksheet, filename: str) -> None:
    """Render the worksheet to an A4 PDF, splitting it over pages."""
    editing = sheet.editing_region()
    if editing is not None:
        editing.finish_editing()
    sheet.clearSelection()
    cross_visible = sheet.crosshair.isVisible()
    sheet.crosshair.hide()

    writer = QPdfWriter(filename)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
    writer.setResolution(144)
    painter = QPainter(writer)
    target = QRectF(painter.viewport())
    breaks = sheet.page_break_ys()
    scale = target.width() / PAGE_WIDTH
    if breaks:
        # A logical page is up to PAGE_HEIGHT tall and must fit one sheet (spec 021).
        scale = min(scale, target.height() / PAGE_HEIGHT)
        page_h = float(PAGE_HEIGHT)
    else:
        page_h = target.height() / scale
    bottom = max((r.sceneBoundingRect().bottom() for r in sheet.regions()), default=0) + 10
    sheet.printing = True
    try:
        for i, (top, height) in enumerate(pdf_strips(breaks, bottom, page_h)):
            if i:
                writer.newPage()
            source = QRectF(0, top, PAGE_WIDTH, height)
            if breaks:
                dest = QRectF(0, 0, PAGE_WIDTH * scale, height * scale)
            else:
                dest = QRectF(0, 0, target.width(), target.height())
            sheet.render(painter, dest, source)
    finally:
        painter.end()
        sheet.printing = False
        sheet.crosshair.setVisible(cross_visible)


def run(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("LiveSheet")
    app.setOrganizationName("LiveSheet")
    settings = QSettings("LiveSheet", "LiveSheet")
    apply_theme(app, settings.value("appearance", MODE_SYSTEM, type=str))
    path = next((a for a in argv[1:] if not a.startswith("-")), None)
    win = MainWindow(path)
    win.show()
    return app.exec()
