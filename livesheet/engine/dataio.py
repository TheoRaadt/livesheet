"""Delimited-text (CSV) reader and the in-memory dataset model (spec 028, phase D1).

No GUI and no evaluator state here: this module reads text into a ``Dataset`` and turns a dataset
into plain variables for the evaluation environment. Only the stdlib ``csv`` module is used; the
module never writes files and opens nothing except the path it is given.
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import sympy as sp
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

from .units import UNITS, UnitError, measure

MAX_ROWS = 20_000
MAX_COLUMNS = 100
MAX_NUMERIC_CELLS = 200_000
MAX_NAME_LENGTH = 40
SNIFF_LINES = 20

DELIMITER_CANDIDATES = (",", ";", "\t", "|")
ENCODINGS = ("utf-8", "latin-1")
MISSING_MODES = ("error", "skip_rows")

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_BRACKET_RE = re.compile(r"^(.*)\[([^\]]*)\]\s*$", re.DOTALL)
_NUMBER_POINT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_NUMBER_COMMA = re.compile(r"[+-]?(?:[0-9]+(?:,[0-9]*)?|,[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_INT_RE = re.compile(r"[+-]?[0-9]+\Z")
_COMMA_DECIMAL_CELL = re.compile(r"[+-]?[0-9]+,[0-9]+\Z")
_POINT_DECIMAL_CELL = re.compile(r"[+-]?[0-9]+\.[0-9]+\Z")
_EXPONENT_FORM = re.compile(r"(?:\^|\*\*)\s*\(?\s*-?\s*[0-9]+(?:\s*/\s*[0-9]+)?\s*\)?")
_UNIT_TRANSFORMS = standard_transformations + (convert_xor,)


class DataImportError(ValueError):
    """Any reader / dataset failure; the message is shown to the user as is."""


# -- model --------------------------------------------------------------------

@dataclass(frozen=True)
class ImportOptions:
    delimiter: str = ","
    decimal: str = "."
    has_header: bool = True
    skip_lines: int = 0
    encoding: str = "utf-8"
    missing: str = "error"

    def __post_init__(self) -> None:
        if len(self.delimiter) != 1 or self.delimiter in "\"\r\n":
            raise DataImportError("The delimiter must be a single character other than a quote.")
        if self.decimal not in (".", ","):
            raise DataImportError("The decimal mark must be '.' or ','.")
        if self.decimal == self.delimiter:
            raise DataImportError("The delimiter and the decimal mark must differ.")
        if isinstance(self.skip_lines, bool) or not isinstance(self.skip_lines, int) \
                or self.skip_lines < 0:
            raise DataImportError("The number of lines to skip must be 0 or more.")
        if self.encoding not in ENCODINGS:
            raise DataImportError(f"Unsupported encoding '{self.encoding}'.")
        if self.missing not in MISSING_MODES:
            raise DataImportError(f"Unknown handling of incomplete rows '{self.missing}'.")
        if not isinstance(self.has_header, bool):
            raise DataImportError("'has_header' must be true or false.")

    def to_dict(self) -> dict:
        return {"delimiter": self.delimiter, "decimal": self.decimal,
                "has_header": self.has_header, "skip_lines": self.skip_lines,
                "encoding": self.encoding, "missing": self.missing}

    @classmethod
    def from_dict(cls, raw: object) -> "ImportOptions":
        if not isinstance(raw, dict):
            raise DataImportError("options must be an object")
        try:
            return cls(raw["delimiter"], raw["decimal"], raw["has_header"], raw["skip_lines"],
                       raw["encoding"], raw["missing"])
        except KeyError as exc:
            raise DataImportError(f"options lack {exc}") from None
        except TypeError as exc:
            raise DataImportError(f"bad options: {exc}") from None


@dataclass
class Column:
    name: str
    label: str
    unit: str = ""
    kind: str = "number"           # "number" | "text"
    values: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "label": self.label, "unit": self.unit,
                "kind": self.kind, "values": list(self.values)}


@dataclass
class Dataset:
    name: str = ""
    source: str = ""
    options: ImportOptions = field(default_factory=ImportOptions)
    columns: list[Column] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.columns[0].values) if self.columns else 0

    def to_dict(self) -> dict:
        return {"name": self.name, "source": self.source, "storage": "embedded",
                "options": self.options.to_dict(),
                "columns": [c.to_dict() for c in self.columns]}

    @classmethod
    def from_dict(cls, raw: object) -> "Dataset":
        """Strict structural validation (a broken dataset must not be silently dropped)."""
        if not isinstance(raw, dict):
            raise DataImportError("dataset entry is not an object")
        try:
            name, source = raw["name"], raw["source"]
            raw_cols = raw["columns"]
            options = ImportOptions.from_dict(raw["options"])
        except KeyError as exc:
            raise DataImportError(f"missing key {exc}") from None
        if not isinstance(name, str) or not isinstance(source, str):
            raise DataImportError("name and source must be text")
        _check_name_syntax(name)
        if not isinstance(raw_cols, list) or not raw_cols:
            raise DataImportError(f"dataset '{name}' has no columns")
        columns = [_column_from_dict(c) for c in raw_cols]
        seen: set[str] = set()
        for col in columns:
            if col.name in seen:
                raise DataImportError(f"dataset '{name}' repeats column '{col.name}'")
            seen.add(col.name)
        if len({len(c.values) for c in columns}) != 1:
            raise DataImportError(f"columns of dataset '{name}' have unequal lengths")
        if not columns[0].values:
            raise DataImportError(f"dataset '{name}' has no rows")
        if not any(c.kind == "number" for c in columns):
            raise DataImportError(f"dataset '{name}' has no numeric column")
        return cls(name, source, options, columns, [])


def _column_from_dict(raw: object) -> Column:
    if not isinstance(raw, dict):
        raise DataImportError("column entry is not an object")
    try:
        name, label, unit, kind, values = (raw["name"], raw["label"], raw["unit"],
                                           raw["kind"], raw["values"])
    except KeyError as exc:
        raise DataImportError(f"column lacks {exc}") from None
    if not all(isinstance(t, str) for t in (name, label, unit, kind)):
        raise DataImportError("column name, label, unit and kind must be text")
    if not _NAME_RE.match(name):
        raise DataImportError(f"bad column name '{name}'")
    if kind not in ("number", "text"):
        raise DataImportError(f"unknown column kind '{kind}'")
    if not isinstance(values, list):
        raise DataImportError(f"values of column '{name}' are not a list")
    if kind == "number":
        for v in values:
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or (isinstance(v, float) and not math.isfinite(v)):
                raise DataImportError(f"column '{name}' holds a non-numeric value")
        if unit:
            _unit_expr(name, unit)
    elif not all(isinstance(v, str) for v in values):
        raise DataImportError(f"text column '{name}' holds a non-text value")
    return Column(name, label, unit, kind, list(values))


# -- units and names ----------------------------------------------------------

def _unit_expr(column: str, text: str) -> sp.Expr:
    """Pure unit expression for ``text`` or DataImportError."""
    bad = DataImportError(f"Column '{column}': '{text}' is not a known unit.")
    if re.search(r"[0-9+\-]", _EXPONENT_FORM.sub("", text)):
        raise bad
    try:
        expr = parse_expr(text, local_dict=dict(UNITS), transformations=_UNIT_TRANSFORMS)
    except Exception:  # noqa: BLE001 - any parse failure means "not a unit"
        raise bad from None
    if not isinstance(expr, sp.Expr) or expr.free_symbols \
            or expr.atoms(sp.NumberSymbol, sp.Function) or expr.has(sp.I):
        raise bad
    try:
        measure(expr)
    except (UnitError, Exception):  # noqa: BLE001
        raise bad from None
    return expr


def sanitize_identifier(text: str) -> str:
    """Identifier-safe form of ``text`` (empty string when nothing usable is left)."""
    out = re.sub(r"[^A-Za-z0-9_]", "_", text)
    out = re.sub(r"_+", "_", out).strip("_")
    if out and out[0].isdigit():
        out = "c" + out
    return out


def _unique(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    k = 2
    while f"{name}_{k}" in used:
        k += 1
    return f"{name}_{k}"


def _check_name_syntax(name: str) -> None:
    if not _NAME_RE.match(name):
        raise DataImportError(f"'{name}' is not a valid name: use letters, digits and _, "
                              "not starting with a digit.")
    if len(name) > MAX_NAME_LENGTH:
        raise DataImportError(f"'{name}' is not a valid name: at most {MAX_NAME_LENGTH} "
                              "characters.")


def validate_dataset_name(name: str, existing_names=()) -> None:
    """Raise DataImportError unless ``name`` can name a new dataset."""
    from .evaluator import BUILTINS   # late import: evaluator imports this module

    _check_name_syntax(name)
    if name in set(existing_names):
        raise DataImportError(f"A dataset named '{name}' already exists.")
    if name in UNITS:
        raise DataImportError(f"'{name}' is already a unit name; choose another dataset name.")
    if name in BUILTINS:
        kind = "a function" if callable(BUILTINS[name]) else "a constant"
        raise DataImportError(f"'{name}' is already {kind} name; choose another dataset name.")


def default_dataset_name(path: str | Path, existing_names=()) -> str:
    """Name offered for a file: its stem, sanitised, valid and unique."""
    base = sanitize_identifier(Path(str(path)).stem)[:MAX_NAME_LENGTH].strip("_") or "data"
    used = set(existing_names)
    candidate, k = base, 2
    while True:
        try:
            validate_dataset_name(candidate, used)
            return candidate
        except DataImportError:
            candidate = f"{base[:MAX_NAME_LENGTH - len(str(k)) - 1]}_{k}"
            k += 1


# -- low-level reading --------------------------------------------------------

def _is_number(cell: str, decimal: str) -> bool:
    pattern = _NUMBER_COMMA if decimal == "," else _NUMBER_POINT
    if not pattern.match(cell):
        return False
    if _INT_RE.match(cell):
        return True      # exact integer, however large
    try:
        return math.isfinite(float(cell.replace(",", ".")))
    except ValueError:
        return False


def _decode(data: bytes, encoding: str, label: str) -> str:
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        raise DataImportError(f"'{label}' is not valid UTF-8 text; try the Latin-1 encoding "
                              "option.") from None
    return text[1:] if text.startswith("﻿") else text


def _read_bytes(path: str | Path) -> bytes:
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        raise DataImportError(f"Cannot open '{path}': file not found.") from None
    except OSError as exc:
        raise DataImportError(f"Cannot read '{path}': {exc.strerror or exc}.") from None


def _rows(text: str, delimiter: str, skip_lines: int):
    """Yield ``(line_number, cells)`` for each non-blank record; cells are trimmed."""
    lines = text.splitlines(keepends=True)[skip_lines:]
    reader = csv.reader(io.StringIO("".join(lines), newline=""), delimiter=delimiter)
    try:
        for row in reader:
            cells = [c.strip() for c in row]
            if not any(cells) and len(cells) <= 1:
                continue
            yield skip_lines + reader.line_num, cells
    except csv.Error as exc:
        raise DataImportError(f"The text cannot be split into fields: {exc}.") from None


def _sniff_delimiter(lines: list[str]) -> str:
    best, best_score = None, 0
    for cand in DELIMITER_CANDIDATES:
        counts: dict[int, int] = {}
        for line in lines:
            try:
                n = len(next(csv.reader([line], delimiter=cand), []))
            except csv.Error:
                continue
            if n > 1:
                counts[n] = counts.get(n, 0) + 1
        score = max(counts.values(), default=0)
        if score > best_score:
            best, best_score = cand, score
    return best or ","


def suggest_options_text(text: str) -> ImportOptions:
    """Suggest options from the first non-blank lines of ``text`` (pure suggestion)."""
    lines = [ln for ln in text.splitlines() if ln.strip()][:SNIFF_LINES]
    delimiter = _sniff_delimiter(lines)
    rows = [[c.strip() for c in next(csv.reader([ln], delimiter=delimiter), [])] for ln in lines]
    cells = [c for row in rows for c in row]
    decimal = "."
    if delimiter != "," and any(_COMMA_DECIMAL_CELL.match(c) for c in cells) \
            and not any(_POINT_DECIMAL_CELL.match(c) for c in cells):
        decimal = ","
    header = (len(rows) >= 2
              and any(c and not _is_number(c, decimal) for c in rows[0])
              and any(_is_number(c, decimal) for c in rows[1]))
    return ImportOptions(delimiter=delimiter, decimal=decimal, has_header=header)


def suggest_options(path: str | Path) -> ImportOptions:
    data = _read_bytes(path)
    try:
        text = _decode(data, "utf-8", str(path))
        encoding = "utf-8"
    except DataImportError:
        text, encoding = data.decode("latin-1"), "latin-1"
    return replace(suggest_options_text(text), encoding=encoding)


def preview(path: str | Path, options: ImportOptions, max_rows: int = 20) -> list[list[str]]:
    text = _decode(_read_bytes(path), options.encoding, str(path))
    out: list[list[str]] = []
    for _, cells in _rows(text, options.delimiter, options.skip_lines):
        out.append(cells)
        if len(out) >= max_rows:
            break
    return out


# -- table building -----------------------------------------------------------

def _split_header(cell: str) -> tuple[str, str]:
    match = _BRACKET_RE.match(cell)
    if not match:
        return cell.strip(), ""
    return match.group(1).strip(), match.group(2).strip()


def _build_columns(header: list[str], k: int, options: ImportOptions
                   ) -> tuple[list[str], list[str], list[str]]:
    """Return (names, labels, header_units) for ``k`` columns."""
    names: list[str] = []
    labels: list[str] = []
    units: list[str] = []
    used: set[str] = set()
    for i in range(k):
        if options.has_header:
            label, unit = _split_header(header[i])
            name = sanitize_identifier(label) or f"col{i + 1}"
        else:
            label, unit, name = f"col{i + 1}", "", f"col{i + 1}"
        name = _unique(name, used)
        used.add(name)
        names.append(name)
        labels.append(label)
        units.append(unit)
    return names, labels, units


def read_table_text(text: str, options: ImportOptions | None = None, name: str = "",
                    source: str = "", units: dict[str, str] | None = None) -> Dataset:
    """Parse ``text`` into a Dataset. ``units`` overrides column units by column name."""
    options = options or ImportOptions()
    if text.startswith("﻿"):
        text = text[1:]
    records = list(_rows(text, options.delimiter, options.skip_lines))
    if not records:
        raise DataImportError("The file has no data rows.")
    width = len(records[0][1])
    if width > MAX_COLUMNS:
        raise DataImportError(f"The file has {width} columns; LiveSheet reads at most "
                              f"{MAX_COLUMNS}.")
    for line, cells in records[1:]:
        if len(cells) != width:
            first = "1 field" if len(cells) == 1 else f"{len(cells)} fields"
            raise DataImportError(f"Line {line} has {first}, but the first line has {width}.")
    header = records[0][1] if options.has_header else []
    body = records[1:] if options.has_header else records
    if not body:
        raise DataImportError("The file has no data rows.")
    if len(body) > MAX_ROWS:
        raise DataImportError(f"The file has {len(body)} rows; LiveSheet reads at most "
                              f"{MAX_ROWS}.")
    names, labels, header_units = _build_columns(header, width, options)
    return _assemble(name, source, options, body, names, labels, header_units, units or {})


def _classify(body, j: int, name: str, decimal: str) -> tuple[bool, str | None]:
    """(is_number, warning). A column is numeric when all non-empty cells are numbers."""
    for line, cells in body:
        cell = cells[j]
        if cell and not _is_number(cell, decimal):
            return False, f"Column '{name}' is read as text because line {line} holds '{cell}'."
    return True, None


def _convert(cell: str, decimal: str, as_int: bool):
    if as_int:
        return int(cell)
    value = float(cell.replace(",", ".") if decimal == "," else cell)
    if not math.isfinite(value):
        raise DataImportError(f"The value '{cell[:20]}...' is too large to read as a "
                              "decimal number.")
    return value


def _assemble(name, source, options, body, names, labels, header_units, overrides) -> Dataset:
    warnings: list[str] = []
    width = len(names)
    numeric: list[bool] = []
    for j in range(width):
        ok, warn = _classify(body, j, names[j], options.decimal)
        numeric.append(ok)
        if warn:
            warnings.append(warn)
    if not any(numeric):
        raise DataImportError("The file has no numeric column.")
    n_numeric = sum(numeric)
    if len(body) * n_numeric > MAX_NUMERIC_CELLS:
        raise DataImportError(f"The file has {len(body) * n_numeric} numeric cells; LiveSheet "
                              f"reads at most {MAX_NUMERIC_CELLS}.")
    body = _handle_missing(body, names, numeric, options, warnings)
    columns: list[Column] = []
    for j in range(width):
        unit = overrides.get(names[j], header_units[j]).strip()
        if not numeric[j]:
            if unit and names[j] not in overrides:
                warnings.append(f"Column '{names[j]}' is text; its unit '{unit}' is ignored.")
            columns.append(Column(names[j], labels[j], "", "text", [c[j] for _, c in body]))
            continue
        if unit:
            _unit_expr(names[j], unit)
        cells = [c[j] for _, c in body]
        as_int = all(_INT_RE.match(c) for c in cells)
        columns.append(Column(names[j], labels[j], unit, "number",
                              [_convert(c, options.decimal, as_int) for c in cells]))
    return Dataset(name, source, options, columns, warnings)


def _handle_missing(body, names, numeric, options, warnings):
    bad = [(line, j) for line, cells in body for j in range(len(names))
           if numeric[j] and not cells[j]]
    if not bad:
        return body
    if options.missing == "error":
        line, j = bad[0]
        raise DataImportError(f"Column '{names[j]}' has an empty value at line {line}; "
                              "fill it in or choose to skip incomplete rows.")
    dropped = {line for line, _ in bad}
    kept = [rec for rec in body if rec[0] not in dropped]
    warnings.append(f"Skipped {len(body) - len(kept)} rows with missing values.")
    if not kept:
        raise DataImportError("No complete rows left.")
    return kept


def read_table(path: str | Path, options: ImportOptions | None = None,
               name: str = "", units: dict[str, str] | None = None) -> Dataset:
    options = options or ImportOptions()
    text = _decode(_read_bytes(path), options.encoding, str(path))
    return read_table_text(text, options, name=name, source=str(path), units=units)


def set_column_units(dataset: Dataset, units: dict[str, str]) -> Dataset:
    """Copy of ``dataset`` with new units for the named number columns (validated)."""
    columns = []
    for col in dataset.columns:
        if col.kind == "number" and col.name in units:
            unit = units[col.name].strip()
            if unit:
                _unit_expr(col.name, unit)
            col = replace(col, unit=unit)
        columns.append(col)
    return replace(dataset, columns=columns)


# -- evaluator environment ----------------------------------------------------

def _scaled(value, unit_expr: sp.Expr | None):
    num = sp.Integer(value) if isinstance(value, int) else sp.Float(value)
    return num if unit_expr is None else num * unit_expr


def column_variable_name(dataset: Dataset, column: Column) -> str:
    return f"{dataset.name}_{column.name}"


def combined_matrix_available(dataset: Dataset) -> bool:
    numbers = [c for c in dataset.columns if c.kind == "number"]
    return bool(numbers) and len({c.unit for c in numbers}) == 1


def variable_names(dataset: Dataset) -> set[str]:
    """Names of the evaluator variables ``dataset`` defines."""
    names = {column_variable_name(dataset, c) for c in dataset.columns if c.kind == "number"}
    if combined_matrix_available(dataset):
        names.add(dataset.name)
    return names


def check_variable_conflicts(dataset: Dataset, others) -> None:
    """Raise DataImportError if ``dataset`` would define a variable another dataset defines."""
    mine = variable_names(dataset)
    for other in others:
        if other is dataset or other.name == dataset.name:
            continue
        clash = sorted(mine & variable_names(other))
        if clash:
            raise DataImportError(f"Variable '{clash[0]}' would be defined by both dataset "
                                  f"'{other.name}' and dataset '{dataset.name}'.")


def dataset_variables(dataset: Dataset) -> dict[str, sp.Basic]:
    """Variables the evaluator adds for ``dataset``: ``<name>_<col>`` vectors and ``<name>``."""
    if not _NAME_RE.match(dataset.name):
        raise DataImportError(f"'{dataset.name}' is not a valid name: use letters, digits and _, "
                              "not starting with a digit.")
    out: dict[str, sp.Basic] = {}
    numbers = [c for c in dataset.columns if c.kind == "number"]
    scaled: list[list] = []
    for col in numbers:
        unit = _unit_expr(col.name, col.unit) if col.unit else None
        items = [_scaled(v, unit) for v in col.values]
        scaled.append(items)
        out[column_variable_name(dataset, col)] = sp.Matrix(items)
    if combined_matrix_available(dataset):
        rows = list(zip(*scaled))
        out[dataset.name] = sp.Matrix([list(r) for r in rows])
    return out


__all__ = [
    "Column", "DataImportError", "check_variable_conflicts", "variable_names", "Dataset", "ImportOptions", "MAX_COLUMNS", "MAX_NUMERIC_CELLS",
    "MAX_ROWS", "combined_matrix_available", "dataset_variables", "default_dataset_name",
    "preview", "read_table", "read_table_text", "sanitize_identifier", "set_column_units",
    "suggest_options", "suggest_options_text", "validate_dataset_name",
]
