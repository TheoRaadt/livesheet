"""Modal "Import data" dialog (spec 028 phase D2): plain labelled fields, live preview.

All logic lives in plain methods (``set_path``, ``update_now``, ``result_dataset``) so tests can
drive the dialog without ``exec()`` or a native file picker.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..engine import dataio
from ..engine.dataio import DataImportError, ImportOptions

FILE_FILTER = "Delimited text (*.csv *.tsv *.txt);;All files (*)"
DELIMITERS = (("Comma", ","), ("Semicolon", ";"), ("Tab", "\t"), ("Pipe", "|"))
OTHER = "Other"
DEBOUNCE_MS = 200
PREVIEW_ROWS = 20


class ImportDataDialog(QDialog):
    def __init__(self, existing_names=(), parent=None, initial_path: str = "",
                 existing_datasets=()):
        super().__init__(parent)
        self.setWindowTitle("Import data")
        self.setModal(True)
        self.resize(640, 640)
        self._existing = list(existing_names)
        self._existing_datasets = list(existing_datasets)
        self._dataset: dataio.Dataset | None = None
        self._error = ""
        self._warnings: list[str] = []
        self._loading = False
        self._unit_overrides: dict[str, str] = {}
        self._build()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(self.update_now)
        if initial_path:
            self.set_path(initial_path)
        else:
            self.update_now()

    # -- layout --------------------------------------------------------------------

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        form = QFormLayout()
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("import-path")
        self.path_edit.editingFinished.connect(self._path_typed)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse)
        row.addWidget(self.path_edit)
        row.addWidget(self.browse_button)
        form.addRow("File:", row)

        self.delimiter_combo = QComboBox()
        for label, _ch in DELIMITERS:
            self.delimiter_combo.addItem(label)
        self.delimiter_combo.addItem(OTHER)
        self.other_edit = QLineEdit()
        self.other_edit.setMaxLength(1)
        self.other_edit.setFixedWidth(40)
        self.other_edit.setEnabled(False)
        drow = QHBoxLayout()
        drow.addWidget(self.delimiter_combo)
        drow.addWidget(self.other_edit)
        drow.addStretch(1)
        form.addRow("Delimiter:", drow)
        self.decimal_combo = QComboBox()
        self.decimal_combo.addItems(["Point", "Comma"])
        form.addRow("Decimal mark:", self.decimal_combo)
        self.header_check = QCheckBox("First row is a header")
        self.header_check.setChecked(True)
        form.addRow("", self.header_check)
        self.skip_spin = QSpinBox()
        self.skip_spin.setRange(0, 1000)
        form.addRow("Skip first N lines:", self.skip_spin)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "Latin-1"])
        form.addRow("Encoding:", self.encoding_combo)
        self.missing_combo = QComboBox()
        self.missing_combo.addItems(["Report an error", "Skip them"])
        form.addRow("Incomplete rows:", self.missing_combo)
        lay.addLayout(form)

        lay.addWidget(QLabel("Preview"))
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.preview_table, 1)
        lay.addWidget(QLabel("Columns"))
        self.columns_table = QTableWidget(0, 3)
        self.columns_table.setHorizontalHeaderLabels(["Name", "Kind", "Unit"])
        self.columns_table.horizontalHeader().setStretchLastSection(True)
        self.columns_table.itemChanged.connect(self._on_unit_edited)
        lay.addWidget(self.columns_table, 1)

        nrow = QHBoxLayout()
        nrow.addWidget(QLabel("Dataset name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("import-name")
        self.name_edit.textEdited.connect(self._schedule)
        nrow.addWidget(self.name_edit)
        lay.addLayout(nrow)

        self.error_label = QLabel("")
        self.error_label.setObjectName("import-error")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        self.warning_label = QLabel("")
        self.warning_label.setObjectName("import-warnings")
        self.warning_label.setStyleSheet("color: #7a7a7a;")
        self.warning_label.setWordWrap(True)
        lay.addWidget(self.error_label)
        lay.addWidget(self.warning_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                        | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)

        for sig in (self.delimiter_combo.currentIndexChanged, self.decimal_combo.currentIndexChanged,
                    self.header_check.toggled, self.skip_spin.valueChanged,
                    self.encoding_combo.currentIndexChanged, self.missing_combo.currentIndexChanged,
                    self.other_edit.textChanged):
            sig.connect(self._schedule)
        self.delimiter_combo.currentIndexChanged.connect(self._sync_other_edit)

    # -- state <-> widgets ---------------------------------------------------------------

    def _sync_other_edit(self, *_args) -> None:
        self.other_edit.setEnabled(self.delimiter_combo.currentText() == OTHER)

    def _browse(self) -> None:   # pragma: no cover - native picker
        start = str(Path(self.path()).parent) if self.path() else str(Path.home())
        name, _ = QFileDialog.getOpenFileName(self, "Choose data file", start, FILE_FILTER)
        if name:
            self.set_path(name)

    def _path_typed(self) -> None:
        if self.path_edit.text().strip() != getattr(self, "_last_path", ""):
            self.set_path(self.path_edit.text())

    def path(self) -> str:
        return self.path_edit.text().strip()

    def options(self) -> ImportOptions:
        """Options as set in the widgets (DataImportError if inconsistent)."""
        if self.delimiter_combo.currentText() == OTHER:
            delimiter = self.other_edit.text()
        else:
            delimiter = DELIMITERS[self.delimiter_combo.currentIndex()][1]
        return ImportOptions(
            delimiter=delimiter,
            decimal="," if self.decimal_combo.currentIndex() == 1 else ".",
            has_header=self.header_check.isChecked(),
            skip_lines=self.skip_spin.value(),
            encoding="latin-1" if self.encoding_combo.currentIndex() == 1 else "utf-8",
            missing="skip_rows" if self.missing_combo.currentIndex() == 1 else "error",
        )

    def set_options(self, options: ImportOptions) -> None:
        self._loading = True
        try:
            for i, (_l, ch) in enumerate(DELIMITERS):
                if ch == options.delimiter:
                    self.delimiter_combo.setCurrentIndex(i)
                    self.other_edit.clear()
                    break
            else:
                self.delimiter_combo.setCurrentIndex(len(DELIMITERS))
                self.other_edit.setText(options.delimiter)
            self.other_edit.setEnabled(self.delimiter_combo.currentText() == OTHER)
            self.decimal_combo.setCurrentIndex(1 if options.decimal == "," else 0)
            self.header_check.setChecked(options.has_header)
            self.skip_spin.setValue(options.skip_lines)
            self.encoding_combo.setCurrentIndex(1 if options.encoding == "latin-1" else 0)
            self.missing_combo.setCurrentIndex(1 if options.missing == "skip_rows" else 0)
        finally:
            self._loading = False

    def set_path(self, path: str) -> None:
        """Choose a file: fill options from the suggestion and the name from the stem."""
        path = path.strip()
        self._last_path = path
        self.path_edit.setText(path)
        self._unit_overrides = {}
        if path:
            try:
                self.set_options(dataio.suggest_options(path))
            except DataImportError as exc:
                self._dataset = None
                self._clear_tables()
                self._show(str(exc), [])
                self._update_ok()
                return
            self.name_edit.setText(dataio.default_dataset_name(path, self._existing))
        self.update_now()

    def set_dataset_name(self, name: str) -> None:
        self.name_edit.setText(name)
        self.update_now()

    def set_unit(self, column: str, unit: str) -> None:
        """Override the unit of one column (as editing its Unit cell does)."""
        self._unit_overrides[column] = unit
        self.update_now()

    def _on_unit_edited(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 2:
            return
        name_item = self.columns_table.item(item.row(), 0)
        if name_item is not None:
            self._unit_overrides[name_item.text()] = item.text().strip()
            self._schedule()

    def _schedule(self, *_args) -> None:
        if not self._loading:
            self._timer.start()

    # -- reading ---------------------------------------------------------------------------

    def update_now(self) -> None:
        """Re-read and re-validate immediately (the debounce timer calls this)."""
        self._timer.stop()
        error, warnings = "", []
        self._dataset = None
        path = self.path()
        if not path:
            self._clear_tables()
            self._show("Choose a file to import.", [])
            self._update_ok()
            return
        try:
            options = self.options()
            self._fill_preview(path, options)
            ds = dataio.read_table(path, options, name=self.name_edit.text().strip(),
                                   units=dict(self._unit_overrides) or None)
            self._fill_columns(ds)
            warnings = list(ds.warnings)
            dataio.validate_dataset_name(ds.name, self._existing)
            dataio.check_variable_conflicts(ds, self._existing_datasets)
            self._dataset = ds
        except DataImportError as exc:
            error = str(exc)
            self.columns_table.setRowCount(0)   # never show columns of an earlier successful read
        self._show(error, warnings)
        self._update_ok()

    def _fill_preview(self, path: str, options: ImportOptions) -> None:
        rows = dataio.preview(path, options, PREVIEW_ROWS)
        width = max((len(r) for r in rows), default=0)
        self.preview_table.clear()
        self.preview_table.setRowCount(len(rows))
        self.preview_table.setColumnCount(width)
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                self.preview_table.setItem(i, j, QTableWidgetItem(cell))

    def _fill_columns(self, ds: dataio.Dataset) -> None:
        self._loading = True
        try:
            self.columns_table.setRowCount(len(ds.columns))
            for i, col in enumerate(ds.columns):
                name_item = QTableWidgetItem(col.name)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                kind_item = QTableWidgetItem(col.kind)
                kind_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                unit_item = QTableWidgetItem(col.unit)
                if col.kind != "number":
                    unit_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.columns_table.setItem(i, 0, name_item)
                self.columns_table.setItem(i, 1, kind_item)
                self.columns_table.setItem(i, 2, unit_item)
        finally:
            self._loading = False

    def _clear_tables(self) -> None:
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.columns_table.setRowCount(0)

    def column_rows(self) -> list[tuple[str, str, str]]:
        """(name, kind, unit) per detected column, as shown."""
        return [tuple(self.columns_table.item(i, j).text() for j in range(3))
                for i in range(self.columns_table.rowCount())]

    # -- result ------------------------------------------------------------------------------

    def _show(self, error: str, warnings: list[str]) -> None:
        self._error = error
        self._warnings = warnings
        self.error_label.setText(error)
        self.warning_label.setText("\n".join(warnings))

    def _update_ok(self) -> None:
        self.ok_button.setEnabled(self._dataset is not None and not self._error)

    @property
    def error(self) -> str:
        return self._error

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def result_dataset(self) -> dataio.Dataset | None:
        """The dataset OK would add, or None while an error is shown."""
        return replace(self._dataset) if self._dataset is not None and not self._error else None


__all__ = ["ImportDataDialog", "FILE_FILTER"]
