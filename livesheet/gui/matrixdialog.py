"""Dialog-based vector/matrix insertion (spec 008): a size-picker then an editable grid of
cells that compiles to exactly the text spec 002a's engine already parses (``[a, b; c, d]``
bracket literals, its ``:=``/``≡`` assignment operators and ``=``/``→`` display suffixes). No
engine change; this is a GUI-only presentation layer on top of ``livesheet.engine.matrices``.

``MatrixFields``, ``compile_matrix_fields``, ``decompose_matrix_text`` and
``validate_matrix_fields`` are Qt-free and safe to unit test without a display. ``MatrixDialog``
is the actual Qt widget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

MIN_SIZE = 1
MAX_SIZE = 20   # this dialog's own usability cap (spec 008, separate from 002a's 200-size limit)

_NAME_MODES = ("No name (insert as a value)", "Define as")
_ASSIGN_OPS = (":=  Definition", "≡  Global definition")
_SHOW_MODES = ("Don't show a result", "Show numeric result (=)", "Show symbolic result (→)")


# -- field model and text (de)compilation: Qt-free -----------------------------------------

@dataclass
class MatrixFields:
    """One in-memory snapshot of every field the dialog shows."""

    rows: int = 2
    cols: int = 2
    cells: list[list[str]] = field(default_factory=lambda: [["", ""], ["", ""]])
    name_mode: str = "none"      # "none" | "define"
    name: str = ""
    assign_op: str = ":="        # ":=" | "≡"
    scale: str = ""
    show_mode: str = "none"      # "none" | "numeric" | "symbolic"
    display_unit: str = ""


def compile_matrix_fields(fields: MatrixFields) -> str:
    """Fields to 002a text, in the fixed order spec 008's 'Compiling' section defines.

    Never raises: blank/invalid field content simply compiles to the corresponding blank or
    literal text (the engine, not this function, is the source of truth for validity).
    """
    rows_text = "; ".join(", ".join(row) for row in fields.cells)
    text = f"[{rows_text}]"
    if fields.scale.strip():
        text += "*" + fields.scale.strip()
    if fields.show_mode == "numeric":
        unit = fields.display_unit.strip()
        text += " =" + (f" {unit}" if unit else "")
    elif fields.show_mode == "symbolic":
        text += " →"
    if fields.name_mode == "define" and fields.name.strip():
        text = f"{fields.name.strip()} {fields.assign_op} " + text
    return text


_ASSIGN_RE = re.compile(r"^([^\W\d]\w*)\s*(:=|≡)\s*")
# Same shape as the engine's own "an evaluation '=' is not part of :=, ==, <=, >=, !=" rule
# (livesheet/engine/syntax.py's _EVAL_EQ_RE), kept as a local copy: the GUI layer must not import
# engine-private helpers (same convention plotdialog.py already uses for its own local copy).
_EVAL_EQ_RE = re.compile(r"(?<![<>=!:])=(?!=)")


def _split_depth(text: str, sep: str) -> list[str]:
    """Split ``text`` at top-level occurrences of ``sep`` (``(``/``[`` increase depth, ``)``/``]``
    decrease it) -- the same small, generic bracket-aware algorithm 002a's own pre-parse step
    needs for splitting matrix rows/cells, kept as a local copy for the same reason as above."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _matching_close(text: str, open_idx: int) -> int | None:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    return None


def _has_top_level_sign(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch in "+-" and depth == 0:
            return True
    return False


def cell_has_separator(text: str) -> bool:
    """True when ``text`` has a top-level ``,`` or ``;`` (spec 008's cell error check); a cell
    like ``f(a, b)`` is fine (the comma is inside parentheses), ``1, 2`` is not."""
    depth = 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch in ",;" and depth == 0:
            return True
    return False


def _split_suffix(rest: str) -> tuple[str, str, str] | None:
    """``rest`` is the text after the matrix literal's closing ``]``: returns
    ``(factor_text, show_mode, show_arg)``, or ``None`` when not representable."""
    arrow_idx = rest.find("→")
    eq_matches = list(_EVAL_EQ_RE.finditer(rest))
    if arrow_idx != -1:
        if eq_matches:
            return None
        before, after = rest[:arrow_idx], rest[arrow_idx + 1:]
        if after.strip():
            return None
        return before, "symbolic", ""
    if eq_matches:
        if len(eq_matches) != 1:
            return None
        mt = eq_matches[0]
        before, after = rest[:mt.start()], rest[mt.end():]
        return before, "numeric", after.strip()
    return rest, "none", ""


def _parse_factor(factor_raw: str) -> str | None:
    stripped = factor_raw.strip()
    if not stripped:
        return ""
    if not stripped.startswith("*"):
        return None
    scale = stripped[1:].strip()
    if not scale or _has_top_level_sign(scale):
        return None
    return scale


def decompose_matrix_text(text: str) -> MatrixFields | None:
    """Inverse of ``compile_matrix_fields``; ``None`` when ``text`` is not representable.

    Representable (spec 008, 'Advanced/raw-text fallback'): after stripping an optional leading
    ``NAME :=``/``NAME ≡`` assignment, exactly one bracket literal of 002a's matrix/vector
    grammar (at most 20x20, this dialog's own cap), optionally followed by a single ``*FACTOR``
    term with no top-level ``+``/``-``, optionally followed by a trailing ``=``/``=UNIT`` or
    ``→``, and nothing else.
    """
    text = text.strip()
    if not text:
        return None
    fields = MatrixFields()
    m = _ASSIGN_RE.match(text)
    rest = text
    if m:
        fields.name_mode = "define"
        fields.name = m.group(1)
        fields.assign_op = m.group(2)
        rest = text[m.end():]
    rest = rest.lstrip()
    if not rest.startswith("["):
        return None
    close = _matching_close(rest, 0)
    if close is None:
        return None
    inner = rest[1:close]
    if not inner.strip():
        return None   # "[]" is a true empty matrix, not representable as a hand-fillable grid
    after = rest[close + 1:]

    grid: list[list[str]] = []
    for row_text in _split_depth(inner, ";"):
        grid.append([c.strip() for c in _split_depth(row_text, ",")])
    width = len(grid[0])
    if any(len(r) != width for r in grid):
        return None
    if len(grid) > MAX_SIZE or width > MAX_SIZE:
        return None   # bigger than this dialog's own cap; continues to be typed directly

    suffix = _split_suffix(after)
    if suffix is None:
        return None
    factor_raw, show_mode, show_arg = suffix
    scale = _parse_factor(factor_raw)
    if scale is None:
        return None

    fields.rows, fields.cols, fields.cells = len(grid), width, grid
    fields.scale = scale
    fields.show_mode = show_mode
    if show_mode == "numeric":
        fields.display_unit = show_arg
    return fields


# -- dialog-side validation (checked before compiling, no engine call) ---------------------

@dataclass
class MatrixFieldError:
    location: object   # (row, col) 0-based for a cell, or "name" for the Name field
    message: str


def validate_matrix_fields(fields: MatrixFields) -> MatrixFieldError | None:
    """Spec 008's own pre-compile checks, in reading order; ``None`` when everything is fine."""
    for r, row in enumerate(fields.cells):
        for c, cell in enumerate(row):
            if not cell.strip():
                return MatrixFieldError((r, c), "Every cell must have a value")
            if cell_has_separator(cell):
                return MatrixFieldError(
                    (r, c), "A cell cannot contain ',' or ';'; use Add column/Add row instead")
    if fields.name_mode == "define" and not fields.name.strip():
        return MatrixFieldError("name", "Name is required")
    return None


# -- Qt widget -------------------------------------------------------------------------------

_ERROR_BORDER = "border: 1px solid #c62828;"
_ERROR_TEXT = "color: #c62828;"


class MatrixDialog(QDialog):
    """The dialog widget (spec 008, phases M1/M2).

    ``region`` is ``None`` for a brand-new insertion (nothing is created until OK: the caller
    reads back ``compiled_text()`` and creates the region itself, mirroring the existing
    ``Worksheet.insert_region("math", initial_text=...)`` path). For an existing, representable
    math region reached via "Edit as grid...", ``region`` is that region; OK writes the compiled
    text into it via its own ``start_editing()``/``finish_editing()`` cycle, Cancel leaves it
    untouched.
    """

    def __init__(self, scene, region=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Matrix")
        self.setModal(True)
        self.scene = scene
        self.region = region
        self._compiled_text = ""
        self._cell_edits: list[list[QLineEdit]] = []

        self._build_ui()
        fields = MatrixFields()
        if region is not None:
            fields = decompose_matrix_text(region.source) or fields
        self._populate_from_fields(fields)
        if region is not None:
            self._show_grid_step()
        else:
            self._show_size_step()

    def compiled_text(self) -> str:
        """The text last compiled by a successful OK (new-insertion flow only)."""
        return self._compiled_text

    # -- UI construction ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_size_page())
        self._stack.addWidget(self._build_grid_page())

    def _build_size_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        form = QFormLayout()
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(MIN_SIZE, MAX_SIZE)
        self.rows_spin.setValue(2)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(MIN_SIZE, MAX_SIZE)
        self.cols_spin.setValue(2)
        form.addRow("Rows:", self.rows_spin)
        form.addRow("Columns:", self.cols_spin)
        page_layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.size_cancel_btn = QPushButton("Cancel")
        self.size_cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.size_cancel_btn)
        self.next_btn = QPushButton("Next")
        self.next_btn.setDefault(True)
        self.next_btn.clicked.connect(self._on_next_clicked)
        buttons.addWidget(self.next_btn)
        page_layout.addLayout(buttons)
        return page

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)

        cells_box = QGroupBox("Elements")
        cells_layout = QVBoxLayout(cells_box)
        self.grid_container = QWidget()
        self.grid_container.setLayout(QVBoxLayout())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_container)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(260)
        cells_layout.addWidget(scroll)

        row_col_buttons = QHBoxLayout()
        self.add_row_btn = QPushButton("Add row")
        self.add_row_btn.clicked.connect(self._add_row)
        self.remove_row_btn = QPushButton("Remove row")
        self.remove_row_btn.clicked.connect(self._remove_row)
        self.add_col_btn = QPushButton("Add column")
        self.add_col_btn.clicked.connect(self._add_column)
        self.remove_col_btn = QPushButton("Remove column")
        self.remove_col_btn.clicked.connect(self._remove_column)
        for btn in (self.add_row_btn, self.remove_row_btn, self.add_col_btn, self.remove_col_btn):
            row_col_buttons.addWidget(btn)
        cells_layout.addLayout(row_col_buttons)
        page_layout.addWidget(cells_box)

        name_box = QGroupBox("Name")
        name_layout = QFormLayout(name_box)
        self.name_mode_combo = QComboBox()
        self.name_mode_combo.addItems(list(_NAME_MODES))
        self.name_mode_combo.currentIndexChanged.connect(self._on_name_mode_changed)
        name_layout.addRow(self.name_mode_combo)
        self.name_edit = QLineEdit()
        self.assign_combo = QComboBox()
        self.assign_combo.addItems(list(_ASSIGN_OPS))
        name_layout.addRow("Name:", self.name_edit)
        name_layout.addRow("Define as:", self.assign_combo)
        page_layout.addWidget(name_box)

        scale_box = QGroupBox("Scale/unit")
        scale_layout = QFormLayout(scale_box)
        self.scale_edit = QLineEdit()
        scale_layout.addRow("Scale/unit factor:", self.scale_edit)
        page_layout.addWidget(scale_box)

        show_box = QGroupBox("Show result")
        show_layout = QFormLayout(show_box)
        self.show_mode_combo = QComboBox()
        self.show_mode_combo.addItems(list(_SHOW_MODES))
        self.show_mode_combo.currentIndexChanged.connect(self._on_show_mode_changed)
        show_layout.addRow(self.show_mode_combo)
        self.display_unit_edit = QLineEdit()
        show_layout.addRow("Display unit:", self.display_unit_edit)
        page_layout.addWidget(show_box)

        self.banner_label = QLabel("")
        self.banner_label.setStyleSheet(_ERROR_TEXT)
        self.banner_label.setWordWrap(True)
        self.banner_label.setVisible(False)
        page_layout.addWidget(self.banner_label)

        buttons = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._on_back_clicked)
        buttons.addWidget(self.back_btn)
        self.edit_text_btn = QPushButton("Edit as text")
        self.edit_text_btn.clicked.connect(self._edit_as_text_clicked)
        buttons.addWidget(self.edit_text_btn)
        buttons.addStretch(1)
        self.grid_cancel_btn = QPushButton("Cancel")
        self.grid_cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.grid_cancel_btn)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        buttons.addWidget(self.ok_btn)
        page_layout.addLayout(buttons)

        self._on_name_mode_changed(0)
        self._on_show_mode_changed(0)
        return page

    def _show_size_step(self) -> None:
        self._stack.setCurrentIndex(0)

    def _show_grid_step(self) -> None:
        self._stack.setCurrentIndex(1)

    # -- grid management --------------------------------------------------------------------

    def _current_cell_texts(self) -> list[list[str]]:
        return [[e.text() for e in row] for row in self._cell_edits]

    def _rebuild_grid(self, rows: int, cols: int, source: list[list[str]] | None = None) -> None:
        old = source if source is not None else self._current_cell_texts()
        layout = self.grid_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                _clear_layout(item.layout())

        self._cell_edits = []
        for r in range(rows):
            row_layout = QHBoxLayout()
            row_edits: list[QLineEdit] = []
            for c in range(cols):
                text = old[r][c] if r < len(old) and c < len(old[r]) else ""
                edit = QLineEdit(text)
                row_layout.addWidget(edit)
                row_edits.append(edit)
            layout.addLayout(row_layout)
            self._cell_edits.append(row_edits)
        self._update_grid_buttons()

    def _update_grid_buttons(self) -> None:
        rows = len(self._cell_edits)
        cols = len(self._cell_edits[0]) if self._cell_edits else 0
        self.add_row_btn.setEnabled(rows < MAX_SIZE)
        self.remove_row_btn.setEnabled(rows > MIN_SIZE)
        self.add_col_btn.setEnabled(cols < MAX_SIZE)
        self.remove_col_btn.setEnabled(cols > MIN_SIZE)

    def _add_row(self) -> None:
        rows, cols = self._shape()
        if rows < MAX_SIZE:
            self._rebuild_grid(rows + 1, cols)

    def _remove_row(self) -> None:
        rows, cols = self._shape()
        if rows > MIN_SIZE:
            self._rebuild_grid(rows - 1, cols)

    def _add_column(self) -> None:
        rows, cols = self._shape()
        if cols < MAX_SIZE:
            self._rebuild_grid(rows, cols + 1)

    def _remove_column(self) -> None:
        rows, cols = self._shape()
        if cols > MIN_SIZE:
            self._rebuild_grid(rows, cols - 1)

    def _shape(self) -> tuple[int, int]:
        rows = len(self._cell_edits)
        cols = len(self._cell_edits[0]) if self._cell_edits else 1
        return rows, cols

    # -- Size <-> Grid step -------------------------------------------------------------------

    def _on_next_clicked(self) -> None:
        self._rebuild_grid(self.rows_spin.value(), self.cols_spin.value())
        self._show_grid_step()

    def _on_back_clicked(self) -> None:
        rows, cols = self._shape()
        self.rows_spin.setValue(rows)
        self.cols_spin.setValue(cols)
        self._show_size_step()

    # -- Name / Show-result mode switches ----------------------------------------------------

    def _on_name_mode_changed(self, index: int) -> None:
        defining = index == 1
        self.name_edit.setEnabled(defining)
        self.assign_combo.setEnabled(defining)

    def _on_show_mode_changed(self, index: int) -> None:
        self.display_unit_edit.setEnabled(index == 1)

    # -- field collection / population --------------------------------------------------------

    def _collect_fields(self) -> MatrixFields:
        fields = MatrixFields()
        fields.cells = self._current_cell_texts()
        fields.rows = len(fields.cells)
        fields.cols = len(fields.cells[0]) if fields.cells else 0
        if self.name_mode_combo.currentIndex() == 1:
            fields.name_mode = "define"
            fields.name = self.name_edit.text()
            fields.assign_op = ":=" if self.assign_combo.currentIndex() == 0 else "≡"
        else:
            fields.name_mode = "none"
        fields.scale = self.scale_edit.text()
        fields.show_mode = ("none", "numeric", "symbolic")[self.show_mode_combo.currentIndex()]
        fields.display_unit = self.display_unit_edit.text()
        return fields

    def _populate_from_fields(self, fields: MatrixFields) -> None:
        rows = max(MIN_SIZE, fields.rows or 2)
        cols = max(MIN_SIZE, fields.cols or 2)
        self.rows_spin.setValue(min(MAX_SIZE, rows))
        self.cols_spin.setValue(min(MAX_SIZE, cols))
        self._rebuild_grid(rows, cols, source=fields.cells)
        if fields.name_mode == "define":
            self.name_mode_combo.setCurrentIndex(1)
            self.name_edit.setText(fields.name)
            self.assign_combo.setCurrentIndex(0 if fields.assign_op == ":=" else 1)
        else:
            self.name_mode_combo.setCurrentIndex(0)
            self.name_edit.setText("")
        self.scale_edit.setText(fields.scale)
        self.show_mode_combo.setCurrentIndex(
            {"none": 0, "numeric": 1, "symbolic": 2}[fields.show_mode])
        self.display_unit_edit.setText(fields.display_unit)

    # -- error display --------------------------------------------------------------------

    def _clear_errors(self) -> None:
        self.banner_label.setText("")
        self.banner_label.setVisible(False)
        for row in self._cell_edits:
            for e in row:
                e.setStyleSheet("")
        self.name_edit.setStyleSheet("")

    def _show_field_error(self, err: MatrixFieldError) -> None:
        self.banner_label.setText(err.message)
        self.banner_label.setVisible(True)
        if err.location == "name":
            self.name_edit.setStyleSheet(_ERROR_BORDER)
            self.name_edit.setFocus()
        else:
            r, c = err.location
            edit = self._cell_edits[r][c]
            edit.setStyleSheet(_ERROR_BORDER)
            edit.setFocus()

    # -- commit / cancel ----------------------------------------------------------------------

    def accept(self) -> None:
        self._clear_errors()
        fields = self._collect_fields()
        err = validate_matrix_fields(fields)
        if err is not None:
            self._show_field_error(err)
            return
        text = compile_matrix_fields(fields)
        if self.region is not None:
            self._commit_existing(text)
        else:
            self._compiled_text = text
        super().accept()

    def _commit_existing(self, text: str) -> None:
        """Write ``text`` into ``self.region`` through its own start/finish-editing cycle, so the
        normal ``Engine.evaluate`` pass runs exactly as it would after any ordinary text edit
        (spec 008: 'no new evaluation entry point')."""
        region = self.region
        region.start_editing()
        cursor = region.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        region.editor.setTextCursor(cursor)
        region.finish_editing()

    def _edit_as_text_clicked(self) -> None:
        """Discards any in-dialog changes; for an existing region, opens its own inline editor on
        its unchanged text (the dialog never wrote anything to it before OK); for a brand-new
        insertion, behaves exactly like Cancel (nothing was ever created)."""
        if self.region is not None:
            self.region.start_editing()
        self.reject()


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


__all__ = [
    "MatrixDialog", "MatrixFields", "MatrixFieldError",
    "compile_matrix_fields", "decompose_matrix_text", "validate_matrix_fields",
    "cell_has_separator",
]
