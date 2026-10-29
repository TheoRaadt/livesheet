"""Dialog-based plot configuration (spec 006): a labelled form that compiles to exactly the
text spec 004's engine already parses (``plot``/``over``/``show``/``xunit``/``yunit``/``xlim``/
``ylim``/``title``/``xlabel``/``ylabel``). No engine change; this is a GUI-only presentation
layer on top of ``livesheet.engine.plotting``.

``PlotFields``, ``compile_plot_fields`` and ``decompose_plot_text`` are Qt-free and safe to unit
test without a display. ``PlotDialog`` is the actual Qt widget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
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
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..engine.plotting import MAX_TRACES
from .plotregion import STARTER_TEXT

# -- field model and text (de)compilation: Qt-free -----------------------------------------

_ALL_SINGLE_KEYWORDS = ("xunit", "yunit", "xlim", "ylim", "title", "xlabel", "ylabel")
_ALL_KEYWORDS = ("over", "show") + _ALL_SINGLE_KEYWORDS


@dataclass
class PlotFields:
    """One in-memory snapshot of every field the dialog shows."""

    functions: list[str] = field(default_factory=lambda: [""])
    var_mode: str = "existing"     # "existing" | "sample"
    var_name: str = ""
    var_from: str = ""
    var_to: str = ""
    var_points: str = ""
    x_min: str = ""
    x_max: str = ""
    y_min: str = ""
    y_max: str = ""
    x_unit: str = ""
    y_unit: str = ""
    title: str = ""
    x_label: str = ""
    y_label: str = ""


def _split_top(text: str, words: tuple[str, ...]) -> list[tuple[str, str]]:
    """Split ``text`` at top-level whitespace-delimited ``words``: [("", head), (word, piece), ...].

    Same small, generic algorithm as the engine's own plot-option splitter (bracket-depth aware),
    kept as a local copy here since the GUI layer must not import engine-private helpers.
    """
    pieces: list[tuple[str, list[str]]] = [("", [])]
    depth = 0
    for token in re.split(r"(\s+)", text):
        if token.strip() and depth == 0 and token in words:
            pieces.append((token, []))
            continue
        pieces[-1][1].append(token)
        depth += sum(token.count(c) for c in "([{") - sum(token.count(c) for c in ")]}")
    return [(word, "".join(parts).strip()) for word, parts in pieces]


def _normalize_limit(text: str) -> str:
    """Blank, or the literal word 'auto' (any case), both mean automatic."""
    t = text.strip()
    return "" if not t or t.lower() == "auto" else t


def _compile_over(fields: PlotFields) -> str:
    if fields.var_mode == "sample":
        text = f"{fields.var_name.strip()} from {fields.var_from.strip()} to {fields.var_to.strip()}"
        points = fields.var_points.strip()
        if points:
            text += f" points {points}"
        return text
    return fields.var_name.strip()


def _compile_limit(min_text: str, max_text: str) -> str:
    lo, hi = _normalize_limit(min_text), _normalize_limit(max_text)
    if not lo and not hi:
        return ""
    return f"{lo or 'auto'} to {hi or 'auto'}"


def compile_plot_fields(fields: PlotFields) -> str:
    """Fields to spec 004 text, in the fixed order the spec's 'Compiling' section defines.

    Never raises: blank/invalid field content simply compiles to the corresponding blank or
    literal text (the engine, not this function, is the source of truth for validity).
    """
    lines = ["plot", "over " + _compile_over(fields)]
    for fn in fields.functions:
        fn = fn.strip()
        if fn:
            lines.append("show " + fn)
    if fields.x_unit.strip():
        lines.append("xunit " + fields.x_unit.strip())
    if fields.y_unit.strip():
        lines.append("yunit " + fields.y_unit.strip())
    xlim = _compile_limit(fields.x_min, fields.x_max)
    if xlim:
        lines.append("xlim " + xlim)
    ylim = _compile_limit(fields.y_min, fields.y_max)
    if ylim:
        lines.append("ylim " + ylim)
    if fields.title.strip():
        lines.append("title " + fields.title.strip())
    if fields.x_label.strip():
        lines.append("xlabel " + fields.x_label.strip())
    if fields.y_label.strip():
        lines.append("ylabel " + fields.y_label.strip())
    return "\n".join(lines)


def _decompose_over(text: str, fields: PlotFields) -> None:
    parts = _split_top(text, ("from", "to", "points"))
    words = [w for w, _ in parts[1:]]
    head = parts[0][1]
    if head and words[:2] == ["from", "to"] and words in (["from", "to"], ["from", "to", "points"]):
        fields.var_mode = "sample"
        fields.var_name = head
        fields.var_from = parts[1][1]
        fields.var_to = parts[2][1]
        fields.var_points = parts[3][1] if len(parts) > 3 else ""
        return
    fields.var_mode = "existing"
    fields.var_name = text


def _decompose_limit(text: str) -> tuple[str, str] | None:
    parts = _split_top(text, ("to",))
    if len(parts) != 2 or not parts[0][1] or not parts[1][1]:
        return None
    lo, hi = parts[0][1], parts[1][1]
    return ("" if lo.lower() == "auto" else lo), ("" if hi.lower() == "auto" else hi)


def decompose_plot_text(text: str) -> PlotFields | None:
    """Inverse of ``compile_plot_fields``; ``None`` when ``text`` is not representable.

    Representable (spec 006, 'Advanced/raw-text fallback'): one ``over`` line, one to twenty
    ``show`` lines, at most one each of ``xunit``/``yunit``/``xlim``/``ylim``/``title``/``xlabel``/
    ``ylabel``, and nothing else.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0] != "plot":
        return None
    over_text: str | None = None
    shows: list[str] = []
    singles: dict[str, str] = {}
    for raw in lines[1:]:
        parts = raw.split(None, 1)
        kw = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        if kw not in _ALL_KEYWORDS:
            return None
        if kw == "show":
            if not rest:
                return None
            shows.append(rest)
        elif kw == "over":
            if over_text is not None:
                return None
            over_text = rest
        else:
            if kw in singles:
                return None
            singles[kw] = rest
    if not over_text or not (1 <= len(shows) <= MAX_TRACES):
        return None

    fields = PlotFields(functions=list(shows))
    _decompose_over(over_text, fields)
    fields.x_unit = singles.get("xunit", "")
    fields.y_unit = singles.get("yunit", "")
    if "xlim" in singles:
        lohi = _decompose_limit(singles["xlim"])
        if lohi is None:
            return None
        fields.x_min, fields.x_max = lohi
    if "ylim" in singles:
        lohi = _decompose_limit(singles["ylim"])
        if lohi is None:
            return None
        fields.y_min, fields.y_max = lohi
    fields.title = singles.get("title", "")
    fields.x_label = singles.get("xlabel", "")
    fields.y_label = singles.get("ylabel", "")
    return fields


def _fields_blank(fields: PlotFields) -> bool:
    if any(f.strip() for f in fields.functions):
        return False
    texts = (fields.var_name, fields.var_from, fields.var_to, fields.var_points,
             fields.x_min, fields.x_max, fields.y_min, fields.y_max,
             fields.x_unit, fields.y_unit, fields.title, fields.x_label, fields.y_label)
    return not any(t.strip() for t in texts)


# -- dialog-side validation (checked before any engine call) ------------------------------

def _validate_points_text(text: str) -> str | None:
    """Spec 004's exact wording, checked by the dialog itself (edge cases)."""
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return "points must be between 2 and 10000"
    if value != int(value) or not 2 <= value <= 10000:
        return "points must be between 2 and 10000"
    return None


_NUM_UNIT_RE = re.compile(r"^\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)\s*([^\s]*)\s*$")


def _parse_plain_limit(text: str) -> tuple[float, str] | None:
    """A plain 'NUMBER [UNIT]' with no further parsing; ``None`` when not directly comparable."""
    text = text.strip()
    if not text or text.lower() == "auto":
        return None
    m = _NUM_UNIT_RE.match(text)
    if not m:
        return None
    try:
        return float(m.group(1)), m.group(2).strip()
    except ValueError:
        return None


def _direct_compare_violation(min_text: str, max_text: str) -> bool:
    """True when both boxes parse as plain numbers in the *same* unit text and min is not below
    max; the dialog only checks this directly-comparable case itself, deferring anything needing
    unit conversion to the engine (spec 006, Error handling)."""
    lo, hi = _parse_plain_limit(min_text), _parse_plain_limit(max_text)
    if lo is None or hi is None:
        return False
    (lo_val, lo_unit), (hi_val, hi_unit) = lo, hi
    if lo_unit != hi_unit:
        return False
    return not lo_val < hi_val


# -- engine-error attribution heuristic ----------------------------------------------------

_UNDEFINED_RE = re.compile(r"^([\w, ]+?) (?:is|are) not defined$")


def _contains_name(text: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", text) is not None


def _name_candidates(names: list[str], fields: PlotFields) -> set:
    candidates: set = set()
    for i, fn in enumerate(fields.functions):
        if fn.strip() and any(_contains_name(fn, n) for n in names):
            candidates.add(("function", i))
    var_tokens = [fields.var_name, fields.var_from, fields.var_to]
    if any(t.strip() and any(_contains_name(t, n) for n in names) for t in var_tokens):
        candidates.add("variable")
    return candidates


def attribute_error(message: str, fields: PlotFields) -> object:
    """Which field an engine error message most likely belongs to: ``("function", idx)``,
    ``"variable"``, ``"xlim"``, ``"ylim"``, ``"xunit"``, ``"yunit"``, or ``None`` for the
    dialog-wide banner. A heuristic (spec 006), not a guaranteed exact mapping."""
    if "traces have different units" in message:
        return None
    if "xunit" in message:
        return "xunit"
    if "yunit" in message:
        return "yunit"
    if "xlim" in message:
        return "xlim"
    if "ylim" in message:
        return "ylim"
    if ("range variable or a vector" in message or "over needs" in message
            or "sampling limits" in message.lower()):
        return "variable"
    quoted = re.findall(r"'([^']*)'", message)
    row_hits = [i for i, fn in enumerate(fields.functions) if fn.strip() and fn.strip() in quoted]
    if len(row_hits) == 1:
        return ("function", row_hits[0])
    if len(row_hits) > 1:
        return None
    m = _UNDEFINED_RE.match(message.strip())
    if m:
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        candidates = _name_candidates(names, fields)
        return next(iter(candidates)) if len(candidates) == 1 else None
    if ("Units do not match" in message or "limit is" in message
            or "Axis limits must be finite" in message
            or "lower limit must be below upper limit" in message):
        x_set = bool(fields.x_min.strip() or fields.x_max.strip())
        y_set = bool(fields.y_min.strip() or fields.y_max.strip())
        if x_set and not y_set:
            return "xlim"
        if y_set and not x_set:
            return "ylim"
        return None
    return None


# -- Qt widget -------------------------------------------------------------------------------

class _FunctionEdit(QLineEdit):
    """A Function(s) row: shows the full text while focused, an elided version otherwise
    (spec 006 edge case: wide text elides when not focused, never wraps)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        super().setText(text)

    def full_text(self) -> str:
        return self.text() if self.hasFocus() else self._full_text

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self._refresh_display()

    def focusInEvent(self, event) -> None:
        self.blockSignals(True)
        self.setText(self._full_text)
        self.blockSignals(False)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._full_text = self.text()
        super().focusOutEvent(event)
        self._refresh_display()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.hasFocus():
            self._refresh_display()

    def _refresh_display(self) -> None:
        avail = max(0, self.width() - 10)
        elided = self.fontMetrics().elidedText(self._full_text, Qt.TextElideMode.ElideRight, avail)
        self.blockSignals(True)
        super().setText(elided)
        self.blockSignals(False)


_ERROR_STYLE = "color: #c62828;"


class PlotDialog(QDialog):
    """The dialog widget (spec 006, phases D1/D2)."""

    def __init__(self, region, scene, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot")
        self.setModal(True)
        self.region = region
        self.scene = scene
        self._is_new_session = not getattr(region, "has_baseline", False)
        self._original_text = region.source
        self._last_good_text = region.source
        self._rows: list[dict] = []

        self._build_ui()
        fields = decompose_plot_text(region.source) if region.source.strip() else None
        self._populate_from_fields(fields or PlotFields())
        self._clear_errors()

    # -- UI construction ----------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        functions_box = QGroupBox("Function(s)")
        f_layout = QVBoxLayout(functions_box)
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.rows_container)
        scroll.setMaximumHeight(160)
        f_layout.addWidget(scroll)
        self.add_function_btn = QPushButton("Add function")
        self.add_function_btn.clicked.connect(lambda: self._add_row(""))
        f_layout.addWidget(self.add_function_btn)
        self.functions_error_label = QLabel("")
        self.functions_error_label.setStyleSheet(_ERROR_STYLE)
        f_layout.addWidget(self.functions_error_label)
        layout.addWidget(functions_box)

        variable_box = QGroupBox("Variable(s)")
        v_layout = QVBoxLayout(variable_box)
        self.var_mode_combo = QComboBox()
        self.var_mode_combo.addItems(["Use existing", "Sample a new range"])
        v_layout.addWidget(self.var_mode_combo)
        self.var_stack = QStackedWidget()
        self.var_mode_combo.currentIndexChanged.connect(self.var_stack.setCurrentIndex)

        existing_page = QWidget()
        existing_form = QFormLayout(existing_page)
        self.var_existing_edit = QLineEdit()
        existing_form.addRow("Name:", self.var_existing_edit)
        self.var_stack.addWidget(existing_page)

        sample_page = QWidget()
        sample_form = QFormLayout(sample_page)
        self.var_sample_name_edit = QLineEdit()
        self.var_sample_from_edit = QLineEdit()
        self.var_sample_to_edit = QLineEdit()
        self.var_sample_points_edit = QLineEdit()
        sample_form.addRow("Name:", self.var_sample_name_edit)
        sample_form.addRow("From:", self.var_sample_from_edit)
        sample_form.addRow("To:", self.var_sample_to_edit)
        sample_form.addRow("Points (optional):", self.var_sample_points_edit)
        self.var_stack.addWidget(sample_page)

        v_layout.addWidget(self.var_stack)
        self.variable_error_label = QLabel("")
        self.variable_error_label.setStyleSheet(_ERROR_STYLE)
        v_layout.addWidget(self.variable_error_label)
        layout.addWidget(variable_box)

        limits_box = QGroupBox("Axis limits")
        limits_layout = QFormLayout(limits_box)
        self.y_min_edit, self.y_max_edit = QLineEdit(), QLineEdit()
        self.x_min_edit, self.x_max_edit = QLineEdit(), QLineEdit()
        y_row = QHBoxLayout()
        y_row.addWidget(self.y_min_edit)
        y_row.addWidget(QLabel("to"))
        y_row.addWidget(self.y_max_edit)
        x_row = QHBoxLayout()
        x_row.addWidget(self.x_min_edit)
        x_row.addWidget(QLabel("to"))
        x_row.addWidget(self.x_max_edit)
        limits_layout.addRow("Y min/max:", _wrap(y_row))
        self.ylim_error_label = QLabel("")
        self.ylim_error_label.setStyleSheet(_ERROR_STYLE)
        limits_layout.addRow("", self.ylim_error_label)
        limits_layout.addRow("X min/max:", _wrap(x_row))
        self.xlim_error_label = QLabel("")
        self.xlim_error_label.setStyleSheet(_ERROR_STYLE)
        limits_layout.addRow("", self.xlim_error_label)
        layout.addWidget(limits_box)

        units_box = QGroupBox("Axis units")
        units_layout = QFormLayout(units_box)
        self.x_unit_edit = QLineEdit()
        self.y_unit_edit = QLineEdit()
        units_layout.addRow("X unit:", self.x_unit_edit)
        self.xunit_error_label = QLabel("")
        self.xunit_error_label.setStyleSheet(_ERROR_STYLE)
        units_layout.addRow("", self.xunit_error_label)
        units_layout.addRow("Y unit:", self.y_unit_edit)
        self.yunit_error_label = QLabel("")
        self.yunit_error_label.setStyleSheet(_ERROR_STYLE)
        units_layout.addRow("", self.yunit_error_label)
        layout.addWidget(units_box)

        labels_box = QGroupBox("Title and axis labels")
        labels_layout = QFormLayout(labels_box)
        self.title_edit = QLineEdit()
        self.x_label_edit = QLineEdit()
        self.y_label_edit = QLineEdit()
        labels_layout.addRow("Title:", self.title_edit)
        labels_layout.addRow("X label:", self.x_label_edit)
        labels_layout.addRow("Y label:", self.y_label_edit)
        layout.addWidget(labels_box)

        self.banner_label = QLabel("")
        self.banner_label.setStyleSheet(_ERROR_STYLE)
        self.banner_label.setWordWrap(True)
        layout.addWidget(self.banner_label)

        buttons = QHBoxLayout()
        self.edit_text_btn = QPushButton("Edit as text...")
        self.edit_text_btn.clicked.connect(self._edit_as_text_clicked)
        buttons.addWidget(self.edit_text_btn)
        buttons.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_btn)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply_clicked)
        buttons.addWidget(self.apply_btn)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

    # -- Function(s) rows -----------------------------------------------------------------

    def _add_row(self, text: str = "") -> None:
        if len(self._rows) >= MAX_TRACES:
            return
        edit = _FunctionEdit(text)
        remove_btn = QPushButton("Remove")
        row_line = QHBoxLayout()
        row_line.setContentsMargins(0, 0, 0, 0)
        row_line.addWidget(edit)
        row_line.addWidget(remove_btn)
        error_label = QLabel("")
        error_label.setStyleSheet(_ERROR_STYLE)
        error_label.setVisible(False)
        wrapper = QWidget()
        col = QVBoxLayout(wrapper)
        col.setContentsMargins(0, 0, 0, 0)
        col.addLayout(row_line)
        col.addWidget(error_label)
        row = {"wrapper": wrapper, "edit": edit, "remove": remove_btn, "error": error_label}
        remove_btn.clicked.connect(lambda: self._remove_row(row))
        self._rows.append(row)
        self.rows_layout.addWidget(wrapper)
        self._update_add_button()

    def _remove_row(self, row: dict) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        self.rows_layout.removeWidget(row["wrapper"])
        row["wrapper"].setParent(None)
        row["wrapper"].deleteLater()
        self._update_add_button()

    def _update_add_button(self) -> None:
        self.add_function_btn.setEnabled(len(self._rows) < MAX_TRACES)

    # -- field collection / population ------------------------------------------------------

    def _collect_fields(self) -> PlotFields:
        fields = PlotFields()
        fields.functions = [row["edit"].full_text() for row in self._rows]
        if self.var_mode_combo.currentIndex() == 0:
            fields.var_mode = "existing"
            fields.var_name = self.var_existing_edit.text()
        else:
            fields.var_mode = "sample"
            fields.var_name = self.var_sample_name_edit.text()
            fields.var_from = self.var_sample_from_edit.text()
            fields.var_to = self.var_sample_to_edit.text()
            fields.var_points = self.var_sample_points_edit.text()
        fields.x_min = self.x_min_edit.text()
        fields.x_max = self.x_max_edit.text()
        fields.y_min = self.y_min_edit.text()
        fields.y_max = self.y_max_edit.text()
        fields.x_unit = self.x_unit_edit.text()
        fields.y_unit = self.y_unit_edit.text()
        fields.title = self.title_edit.text()
        fields.x_label = self.x_label_edit.text()
        fields.y_label = self.y_label_edit.text()
        return fields

    def _populate_from_fields(self, fields: PlotFields) -> None:
        for row in list(self._rows):
            self._remove_row(row)
        for fn in (fields.functions or [""]):
            self._add_row(fn)
        if not self._rows:
            self._add_row("")
        if fields.var_mode == "sample":
            self.var_mode_combo.setCurrentIndex(1)
            self.var_sample_name_edit.setText(fields.var_name)
            self.var_sample_from_edit.setText(fields.var_from)
            self.var_sample_to_edit.setText(fields.var_to)
            self.var_sample_points_edit.setText(fields.var_points)
        else:
            self.var_mode_combo.setCurrentIndex(0)
            self.var_existing_edit.setText(fields.var_name)
        self.x_min_edit.setText(fields.x_min)
        self.x_max_edit.setText(fields.x_max)
        self.y_min_edit.setText(fields.y_min)
        self.y_max_edit.setText(fields.y_max)
        self.x_unit_edit.setText(fields.x_unit)
        self.y_unit_edit.setText(fields.y_unit)
        self.title_edit.setText(fields.title)
        self.x_label_edit.setText(fields.x_label)
        self.y_label_edit.setText(fields.y_label)

    # -- error display --------------------------------------------------------------------

    def _clear_errors(self) -> None:
        for lbl in (self.banner_label, self.variable_error_label, self.xlim_error_label,
                    self.ylim_error_label, self.xunit_error_label, self.yunit_error_label,
                    self.functions_error_label):
            lbl.setText("")
            lbl.setVisible(False)
        for row in self._rows:
            row["error"].setText("")
            row["error"].setVisible(False)

    def _set_banner(self, message: str) -> None:
        self.banner_label.setText(message)
        self.banner_label.setVisible(True)

    def _set_variable_error(self, message: str) -> None:
        self.variable_error_label.setText(message)
        self.variable_error_label.setVisible(True)

    def _set_xlim_error(self, message: str) -> None:
        self.xlim_error_label.setText(message)
        self.xlim_error_label.setVisible(True)

    def _set_ylim_error(self, message: str) -> None:
        self.ylim_error_label.setText(message)
        self.ylim_error_label.setVisible(True)

    def _set_xunit_error(self, message: str) -> None:
        self.xunit_error_label.setText(message)
        self.xunit_error_label.setVisible(True)

    def _set_yunit_error(self, message: str) -> None:
        self.yunit_error_label.setText(message)
        self.yunit_error_label.setVisible(True)

    def _set_functions_error(self, message: str) -> None:
        self.functions_error_label.setText(message)
        self.functions_error_label.setVisible(True)

    def _set_function_error(self, idx: int, message: str) -> None:
        if 0 <= idx < len(self._rows):
            self._rows[idx]["error"].setText(message)
            self._rows[idx]["error"].setVisible(True)
        else:
            self._set_banner(message)

    def _show_attributed_error(self, message: str, fields: PlotFields) -> None:
        target = attribute_error(message, fields)
        if isinstance(target, tuple) and target[0] == "function":
            self._set_function_error(target[1], message)
        elif target == "variable":
            self._set_variable_error(message)
        elif target == "xlim":
            self._set_xlim_error(message)
        elif target == "ylim":
            self._set_ylim_error(message)
        elif target == "xunit":
            self._set_xunit_error(message)
        elif target == "yunit":
            self._set_yunit_error(message)
        else:
            self._set_banner(message)

    # -- validation -------------------------------------------------------------------------

    def _validate_local(self, fields: PlotFields) -> bool:
        ok = True
        if not any(fn.strip() for fn in fields.functions):
            self._set_functions_error("At least one function is required")
            ok = False
        if fields.var_mode == "existing":
            if not fields.var_name.strip():
                self._set_variable_error("Variable(s) is required")
                ok = False
        else:
            if not fields.var_name.strip() or not fields.var_from.strip() or not fields.var_to.strip():
                self._set_variable_error("Variable(s) is required")
                ok = False
            else:
                msg = _validate_points_text(fields.var_points)
                if msg:
                    self._set_variable_error(msg)
                    ok = False
        if (fields.x_min.strip() or fields.x_max.strip()) and _direct_compare_violation(
                fields.x_min, fields.x_max):
            self._set_xlim_error("lower limit must be below upper limit")
            ok = False
        if (fields.y_min.strip() or fields.y_max.strip()) and _direct_compare_violation(
                fields.y_min, fields.y_max):
            self._set_ylim_error("lower limit must be below upper limit")
            ok = False
        return ok

    # -- commit / cancel ----------------------------------------------------------------------

    def _commit(self) -> bool:
        self._clear_errors()
        fields = self._collect_fields()
        if not self._validate_local(fields):
            return False
        text = compile_plot_fields(fields)
        self.region.source = text
        self.scene.set_modified()
        self.scene.recalculate()
        result = self.region.result
        if result is not None and result.status == "error":
            self._show_attributed_error(result.error, fields)
            self.region.source = self._last_good_text
            self.scene.recalculate()
            return False
        self._last_good_text = text
        return True

    def _apply_clicked(self) -> None:
        self._commit()

    def accept(self) -> None:
        if self._is_new_session and not any(fn.strip() for fn in self._collect_fields().functions):
            # Criterion 28: a brand-new region with an empty Function(s) list has nothing valid
            # to apply, so OK simply discards the region exactly like Cancel would.
            self.reject()
            return
        if self._commit():
            self.region.has_baseline = True
            super().accept()

    def reject(self) -> None:
        if self._is_new_session:
            self.scene.remove_regions([self.region])
        else:
            self.region.source = self._original_text
            self.scene.recalculate()
        super().reject()

    def _edit_as_text_clicked(self) -> None:
        fields = self._collect_fields()
        if self._is_new_session and _fields_blank(fields):
            text = STARTER_TEXT
        else:
            text = compile_plot_fields(fields)
        self.region.source = text
        self.region._set_editor_text()
        QDialog.reject(self)   # close without the Cancel button's discard/revert logic
        self.region.start_editing()


def _wrap(layout) -> QWidget:
    """A plain QWidget wrapper so a QHBoxLayout can be added as a QFormLayout field widget."""
    w = QWidget()
    w.setLayout(layout)
    w.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    return w


__all__ = [
    "PlotDialog", "PlotFields", "compile_plot_fields", "decompose_plot_text", "attribute_error",
]
