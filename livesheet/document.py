"""Worksheet document model and the ``.lsheet`` file format (JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_NAME = "livesheet"
FORMAT_VERSION = 1              # written for sheets without plots or components
FORMAT_VERSION_PLOT = 2         # written when the sheet holds a plot (no components)
FORMAT_VERSION_COMPONENTS = 3   # written when the sheet holds a component or wire; highest we read
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

    def to_dict(self) -> dict:
        data = {"kind": self.kind, "x": self.x, "y": self.y, "text": self.text}
        if self.kind == "plot":
            data["w"] = float(self.w)
            data["h"] = float(self.h)
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


@dataclass
class SheetDocument:
    regions: list[RegionData] = field(default_factory=list)
    significant: int = 6
    wires: list[WireData] = field(default_factory=list)

    def ordered(self) -> list[RegionData]:
        """Regions in reading order: top to bottom, then left to right."""
        return sorted(self.regions, key=lambda r: (r.y, r.x))

    def version(self) -> int:
        """Format version to write: 3 only when a component or wire is present, else the
        existing plot-or-not logic (2 / 1), completely unchanged for component-free sheets."""
        if any(r.kind == "component" for r in self.regions) or self.wires:
            return FORMAT_VERSION_COMPONENTS
        has_plot = any(r.kind == "plot" for r in self.regions)
        return FORMAT_VERSION_PLOT if has_plot else FORMAT_VERSION

    def to_json(self) -> str:
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
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "SheetDocument":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"Not a valid LiveSheet file: {exc}") from None
        if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
            raise DocumentError("Not a LiveSheet file")
        if int(data.get("version", 0)) > FORMAT_VERSION_COMPONENTS:
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
                    config))
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
        settings = data.get("settings", {}) or {}
        sig = int(settings.get("significant", 6))
        # Version 3 is only meaningful when the file actually holds a component or a wire
        # (mirrors version()'s write-side policy: 3 is written only when needed). A file that
        # declares version 3 but has no component/wire content isn't a file this build's
        # component support actually produced, so it's treated the same as "newer than what
        # this build understands" rather than silently accepted.
        version = int(data.get("version", 0))
        if version >= FORMAT_VERSION_COMPONENTS and not (
            any(r.kind == "component" for r in regions) or wires
        ):
            raise DocumentError("This file was made with a newer LiveSheet version")
        return cls(regions=regions, significant=max(2, min(15, sig)), wires=wires)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SheetDocument":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
