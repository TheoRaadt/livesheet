"""Component/wire creation dialogs (spec 009): the same generic modal-dialog-with-labelled-
fields chrome already used by ``plotdialog.py``/``matrixdialog.py`` -- a kind dropdown plus that
kind's own small set of fields for "Add Component", and a plain pick-from-a-list dialog for
"Connect…". Neither dialog is a bespoke canvas interaction; both are ordinary ``QDialog``s with
OK/Cancel, fully keyboard-navigable.

``ComponentFields``, ``fields_to_config`` and ``validate_component_fields`` are Qt-free and safe
to unit test without a display. ``AddComponentDialog``/``ConnectDialog`` are the Qt widgets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

_KIND_LABELS = ("Value", "Formula")
_KIND_BY_LABEL = {"Value": "value", "Formula": "formula"}
_LABEL_BY_KIND = {v: k for k, v in _KIND_BY_LABEL.items()}

_NAME_RE = re.compile(r"^[^\W\d]\w*$")

_ERROR_TEXT = "color: #c62828;"


# -- field model and config (de)compilation: Qt-free ------------------------------------------

@dataclass
class ComponentFields:
    """One in-memory snapshot of every field the "Add Component" dialog shows."""

    name: str = ""
    kind: str = "value"             # "value" | "formula"
    value_expr: str = ""
    formula_inputs: str = ""
    formula_expr: str = ""


def fields_to_config(fields: ComponentFields) -> dict[str, str]:
    if fields.kind == "formula":
        return {"inputs": fields.formula_inputs.strip(), "expr": fields.formula_expr.strip()}
    return {"expr": fields.value_expr.strip()}


@dataclass
class ComponentFieldError:
    field: str   # "name" | "value_expr" | "formula_inputs" | "formula_expr" | "kind"
    message: str


def validate_component_fields(fields: ComponentFields) -> ComponentFieldError | None:
    """Spec 009's own pre-creation checks; ``None`` when everything is fine. The engine, not this
    function, is the source of truth for whether an expression is actually valid -- these are
    just the checks needed before a port/config dict can be built at all."""
    name = fields.name.strip()
    if not name:
        return ComponentFieldError("name", "Name is required")
    if not _NAME_RE.match(name):
        return ComponentFieldError(
            "name", "Name must start with a letter and contain only letters, digits, underscore")
    if fields.kind == "value":
        if not fields.value_expr.strip():
            return ComponentFieldError("value_expr", "Expression is required")
    elif fields.kind == "formula":
        names = [n.strip() for n in fields.formula_inputs.split(",") if n.strip()]
        if not names:
            return ComponentFieldError("formula_inputs", "At least one input name is required")
        for n in names:
            if not _NAME_RE.match(n):
                return ComponentFieldError("formula_inputs", f"'{n}' is not a valid input name")
        if len(set(names)) != len(names):
            return ComponentFieldError("formula_inputs", "Input names must be unique")
        if not fields.formula_expr.strip():
            return ComponentFieldError("formula_expr", "Expression is required")
    else:
        return ComponentFieldError("kind", f"Unknown kind '{fields.kind}'")
    return None


# -- "Add Component" dialog --------------------------------------------------------------------

class AddComponentDialog(QDialog):
    """Kind dropdown (only "Value" and "Formula" exist in this spec) followed by that kind's own
    labelled fields. OK commits nothing until ``result_fields()`` is read back by the caller
    (mirrors ``MatrixDialog``'s new-insertion flow: nothing is created on the canvas until OK)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Component")
        self.setModal(True)
        self._fields = ComponentFields()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(list(_KIND_LABELS))
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        form.addRow("Kind:", self.kind_combo)
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        layout.addLayout(form)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        self._stack.addWidget(self._build_value_page())
        self._stack.addWidget(self._build_formula_page())

        self.banner_label = QLabel("")
        self.banner_label.setStyleSheet(_ERROR_TEXT)
        self.banner_label.setWordWrap(True)
        self.banner_label.setVisible(False)
        layout.addWidget(self.banner_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

        self._on_kind_changed(0)

    def _build_value_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.value_expr_edit = QLineEdit()
        form.addRow("Expression:", self.value_expr_edit)
        return page

    def _build_formula_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.formula_inputs_edit = QLineEdit()
        form.addRow("Input names (comma-separated):", self.formula_inputs_edit)
        self.formula_expr_edit = QLineEdit()
        form.addRow("Expression:", self.formula_expr_edit)
        return page

    def _on_kind_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    def _collect(self) -> ComponentFields:
        kind = _KIND_BY_LABEL[self.kind_combo.currentText()]
        return ComponentFields(
            name=self.name_edit.text(),
            kind=kind,
            value_expr=self.value_expr_edit.text(),
            formula_inputs=self.formula_inputs_edit.text(),
            formula_expr=self.formula_expr_edit.text(),
        )

    def accept(self) -> None:
        self.banner_label.setVisible(False)
        fields = self._collect()
        err = validate_component_fields(fields)
        if err is not None:
            self.banner_label.setText(err.message)
            self.banner_label.setVisible(True)
            return
        self._fields = fields
        super().accept()

    def result_fields(self) -> tuple[str, str, dict[str, str]]:
        """``(name, kind, config)`` of the last successful OK."""
        return self._fields.name.strip(), self._fields.kind, fields_to_config(self._fields)


# -- "Connect…" dialog --------------------------------------------------------------------------

class ConnectDialog(QDialog):
    """A plain list of candidate ports the user picks from (the other sheet-compatible ports:
    outputs, if started from an input; inputs, if started from an output), then OK. Needs no
    dragging at all and is fully keyboard-navigable (spec 009's primary, always-available way to
    create a wire)."""

    def __init__(self, region, side: str, port: str,
                 candidates: list[tuple[object, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect…")
        self.setModal(True)
        self._candidates = candidates

        layout = QVBoxLayout(self)
        other_side = "input" if side == "output" else "output"
        layout.addWidget(QLabel(
            f"Connect {region.component_name}.{port} ({side}) to a candidate {other_side}:"))
        self.list_widget = QListWidget()
        for comp, p in candidates:
            self.list_widget.addItem(f"{comp.component_name}.{p}")
        layout.addWidget(self.list_widget)
        if candidates:
            self.list_widget.setCurrentRow(0)
        else:
            layout.addWidget(QLabel("No compatible ports available."))

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setDefault(True)
        self.ok_btn.setEnabled(bool(candidates))
        self.ok_btn.clicked.connect(self.accept)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

    def chosen(self) -> tuple[object, str] | None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._candidates):
            return None
        return self._candidates[row]


__all__ = [
    "AddComponentDialog", "ConnectDialog", "ComponentFields", "ComponentFieldError",
    "fields_to_config", "validate_component_fields",
]
