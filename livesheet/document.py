"""Worksheet document model and the ``.lsheet`` file format (JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import os

from .engine import dataio
from .engine.dataio import DataImportError, Dataset
from .engine.pagination import order_key

FORMAT_NAME = "livesheet"
FORMAT_VERSION = 1              # written for sheets without plots or components
FORMAT_VERSION_PLOT = 2         # written when the sheet holds a plot (no components)
FORMAT_VERSION_COMPONENTS = 3   # written when the sheet holds a component or wire
FORMAT_VERSION_PAGES = 4        # written when the sheet has page breaks
FORMAT_VERSION_DATASETS = 5     # written when the sheet holds a dataset (spec 028); highest we read
STORAGE_EMBEDDED = "embedded"
DEFAULT_PLOT_SIZE = (400.0, 260.0)
FILE_SUFFIX = ".lsheet"


class DocumentError(ValueError):
    pass


@dataclass
class RegionData:
    kind: str          # "math" | "text" | "plot" | "component"
    x: float
    y: float
    text: str          # math: source text; text: HTML; plot: spec lines; component: unused
    w: float | None = None   # plot width (scene units); only plot regions carry w/h
    h: float | None = None
    # Used only when kind == "component" (spec 009); empty/unused otherwise.
    component_name: str = ""
    component_kind: str = ""       # e.g. "value", "formula"
    config: dict[str, str] = field(default_factory=dict)
    # Saved camera of a 3-D plot region (spec 031 phase B): all three or none; only written for
    # plot regions whose text is a ``surface`` spec, so older sheets round-trip unchanged.
    view_az: float | None = None
    view_el: float | None = None
    view_zoom: float | None = None

    def __post_init__(self):
        if self.kind not in ("math", "text", "plot", "component"):
            raise DocumentError(f"Unknown region kind '{self.kind}'")
        if self.kind == "plot":
            if self.w is None:
                self.w = DEFAULT_PLOT_SIZE[0]
            if self.h is None:
                self.h = DEFAULT_PLOT_SIZE[1]
        else:
            self.w = self.h = None
        if self.kind == "component":
            # Flat string-to-string mapping (spec 009): coerce defensively, never raise here --
            # an unrecognised component_kind *value* is a run-time evaluation concern, not a
            # document-parse-time structural error (see spec 009's edge cases).
            self.config = {str(k): str(v) for k, v in (self.config or {}).items()}
        else:
            self.component_name = ""
            self.component_kind = ""
            self.config = {}
        if not self.has_view():
            self.view_az = self.view_el = self.view_zoom = None

    def has_view(self) -> bool:
        """True when a complete saved 3-D view is present on a ``surface`` plot region."""
        lines = [ln.strip() for ln in self.text.splitlines() if ln.strip()]
        return (self.kind == "plot" and bool(lines) and lines[0] == "surface"
                and None not in (self.view_az, self.view_el, self.view_zoom))

    def to_dict(self) -> dict:
        data = {"kind": self.kind, "x": self.x, "y": self.y, "text": self.text}
        if self.kind == "plot":
            data["w"] = float(self.w)
            data["h"] = float(self.h)
        if self.has_view():
            data["view_az"] = float(self.view_az)
            data["view_el"] = float(self.view_el)
            data["view_zoom"] = float(self.view_zoom)
        if self.kind == "component":
            data["component_name"] = self.component_name
            data["component_kind"] = self.component_kind
            data["config"] = dict(self.config)
        return data


@dataclass
class WireData:
    """One component-to-component connection (spec 009): plain strings, matched against
    ``component_name``/port names at load/connect time, never Python object identity."""

    from_component: str
    from_port: str
    to_component: str
    to_port: str

    def to_dict(self) -> dict:
        return {
            "from_component": self.from_component, "from_port": self.from_port,
            "to_component": self.to_component, "to_port": self.to_port,
        }


def _optional_float(raw: object) -> float | None:
    """Lenient: a missing or malformed number is treated as absent."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    return value if value == value and abs(value) != float("inf") else None


def _parse_page_breaks(raw: object) -> list[float]:
    """Lenient: non-numeric or malformed entries are dropped; result is sorted ascending."""
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        value = float(item)
        if value == value and abs(value) != float("inf"):
            out.append(value)
    return sorted(out)


def _relative_source(source: str, base_dir: str | Path | None) -> str:
    """Source label relative to the sheet folder when the file lies below it, else unchanged."""
    if not source or base_dir is None or not os.path.isabs(source):
        return source
    try:
        rel = Path(source).resolve().relative_to(Path(base_dir).resolve())
    except (ValueError, OSError):
        return source
    return rel.as_posix()


def _dataset_to_dict(dataset: Dataset, base_dir: str | Path | None) -> dict:
    data = dataset.to_dict()
    data["source"] = _relative_source(dataset.source, base_dir)
    return data


def _parse_datasets(raw: object) -> list[Dataset]:
    """Strict: a broken dataset is a load error, never silently dropped."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise DocumentError("Invalid dataset in file: 'datasets' is not a list")
    out: list[Dataset] = []
    for entry in raw:
        if isinstance(entry, dict) and entry.get("storage", STORAGE_EMBEDDED) != STORAGE_EMBEDDED:
            raise DocumentError("This file was made with a newer LiveSheet version")
        try:
            if isinstance(entry, dict) and "storage" not in entry:
                raise DataImportError("missing key 'storage'")
            dataset = Dataset.from_dict(entry)
        except DataImportError as exc:
            raise DocumentError(f"Invalid dataset in file: {exc}") from None
        if any(d.name == dataset.name for d in out):
            raise DocumentError(f"Invalid dataset in file: duplicate name '{dataset.name}'")
        try:
            dataio.check_variable_conflicts(dataset, out)
        except DataImportError as exc:
            raise DocumentError(f"Invalid dataset in file: {exc}") from None
        out.append(dataset)
    return out


@dataclass
class SheetDocument:
    regions: list[RegionData] = field(default_factory=list)
    significant: int = 6
    wires: list[WireData] = field(default_factory=list)
    page_breaks: list[float] = field(default_factory=list)   # y-coordinates, ascending
    datasets: list[Dataset] = field(default_factory=list)    # embedded data (spec 028)

    def ordered(self) -> list[RegionData]:
        """Regions in evaluation order: page by page, left to right, then top to bottom.
        The sort is stable, so regions at an identical position keep their list order."""
        breaks = sorted(self.page_breaks)
        return sorted(self.regions, key=lambda r: order_key(r.x, r.y, breaks))

    def version(self) -> int:
        """Format version to write: 4 only when page breaks exist, else 3 only when a component or wire is present, else the
        existing plot-or-not logic (2 / 1), completely unchanged for component-free sheets.
        5 (datasets) takes precedence and is a superset of 4."""
        if self.datasets:
            return FORMAT_VERSION_DATASETS
        if self.page_breaks:
            return FORMAT_VERSION_PAGES
        if any(r.kind == "component" for r in self.regions) or self.wires:
            return FORMAT_VERSION_COMPONENTS
        has_plot = any(r.kind == "plot" for r in self.regions)
        return FORMAT_VERSION_PLOT if has_plot else FORMAT_VERSION

    def to_json(self, base_dir: str | Path | None = None) -> str:
        data = {
            "format": FORMAT_NAME,
            "version": self.version(),
            "settings": {"significant": self.significant},
            "regions": [r.to_dict() for r in self.ordered()],
        }
        # Mirrors the existing plot-only-when-used policy for "w"/"h": the "wires" key is
        # written only when there actually are wires, so a component-free sheet round-trips
        # through exactly the same JSON shape it always has.
        if self.wires:
            data["wires"] = [w.to_dict() for w in self.wires]
        if self.page_breaks:
            data["page_breaks"] = [float(b) for b in sorted(self.page_breaks)]
        if self.datasets:
            data["datasets"] = [_dataset_to_dict(d, base_dir) for d in self.datasets]
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "SheetDocument":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"Not a valid LiveSheet file: {exc}") from None
        if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
            raise DocumentError("Not a LiveSheet file")
        if int(data.get("version", 0)) > FORMAT_VERSION_DATASETS:
            raise DocumentError("This file was made with a newer LiveSheet version")
        regions = []
        for raw in data.get("regions", []):
            try:
                w, h = raw.get("w"), raw.get("h")
                config = raw.get("config") or {}
                if not isinstance(config, dict):
                    config = {}
                regions.append(RegionData(
                    str(raw["kind"]), float(raw["x"]), float(raw["y"]), str(raw["text"]),
                    None if w is None else float(w), None if h is None else float(h),
                    str(raw.get("component_name", "")), str(raw.get("component_kind", "")),
                    config, _optional_float(raw.get("view_az")),
                    _optional_float(raw.get("view_el")), _optional_float(raw.get("view_zoom"))))
            except (KeyError, TypeError, ValueError) as exc:
                raise DocumentError(f"Invalid region in file: {exc}") from None
        # Wires are parsed leniently (spec 009 edge cases): a version-1/2 file simply has no
        # "wires" key (-> []); a structurally malformed wire entry is dropped, not fatal, so a
        # hand-edited or corrupted file still opens. Whether a wire's named component/port still
        # *exists* is checked later, where the live components are known (livesheet/gui/worksheet.py).
        wires = []
        for raw in data.get("wires", []) or []:
            try:
                wires.append(WireData(
                    str(raw["from_component"]), str(raw["from_port"]),
                    str(raw["to_component"]), str(raw["to_port"])))
            except (KeyError, TypeError, ValueError):
                continue
        page_breaks = _parse_page_breaks(data.get("page_breaks"))
        datasets = _parse_datasets(data.get("datasets"))
        settings = data.get("settings", {}) or {}
        sig = int(settings.get("significant", 6))
        # Version 3 is only meaningful when the file actually holds a component or a wire
        # (mirrors version()'s write-side policy: 3 is written only when needed). A file that
        # declares version 3 but has no component/wire content isn't a file this build's
        # component support actually produced, so it's treated the same as "newer than what
        # this build understands" rather than silently accepted.
        version = int(data.get("version", 0))
        if version == FORMAT_VERSION_COMPONENTS and not (
            any(r.kind == "component" for r in regions) or wires
        ):
            raise DocumentError("This file was made with a newer LiveSheet version")
        if version == FORMAT_VERSION_DATASETS and not datasets:
            raise DocumentError("This file was made with a newer LiveSheet version")
        return cls(regions=regions, significant=max(2, min(15, sig)), wires=wires,
                   page_breaks=page_breaks, datasets=datasets)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(Path(path).resolve().parent), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SheetDocument":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
