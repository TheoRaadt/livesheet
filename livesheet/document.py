"""Worksheet document model and the ``.lsheet`` file format (JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_NAME = "livesheet"
FORMAT_VERSION = 1          # written for sheets without plots
FORMAT_VERSION_PLOT = 2     # written when the sheet holds a plot; highest version we read
DEFAULT_PLOT_SIZE = (400.0, 260.0)
FILE_SUFFIX = ".lsheet"


class DocumentError(ValueError):
    pass


@dataclass
class RegionData:
    kind: str          # "math" | "text" | "plot"
    x: float
    y: float
    text: str          # math: source text; text: HTML; plot: spec lines joined with newlines
    w: float | None = None   # plot width (scene units); only plot regions carry w/h
    h: float | None = None

    def __post_init__(self):
        if self.kind not in ("math", "text", "plot"):
            raise DocumentError(f"Unknown region kind '{self.kind}'")
        if self.kind == "plot":
            if self.w is None:
                self.w = DEFAULT_PLOT_SIZE[0]
            if self.h is None:
                self.h = DEFAULT_PLOT_SIZE[1]
        else:
            self.w = self.h = None

    def to_dict(self) -> dict:
        data = {"kind": self.kind, "x": self.x, "y": self.y, "text": self.text}
        if self.kind == "plot":
            data["w"] = float(self.w)
            data["h"] = float(self.h)
        return data


@dataclass
class SheetDocument:
    regions: list[RegionData] = field(default_factory=list)
    significant: int = 6

    def ordered(self) -> list[RegionData]:
        """Regions in reading order: top to bottom, then left to right."""
        return sorted(self.regions, key=lambda r: (r.y, r.x))

    def version(self) -> int:
        """Format version to write: 2 only when the sheet contains a plot."""
        has_plot = any(r.kind == "plot" for r in self.regions)
        return FORMAT_VERSION_PLOT if has_plot else FORMAT_VERSION

    def to_json(self) -> str:
        data = {
            "format": FORMAT_NAME,
            "version": self.version(),
            "settings": {"significant": self.significant},
            "regions": [r.to_dict() for r in self.ordered()],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "SheetDocument":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"Not a valid LiveSheet file: {exc}") from None
        if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
            raise DocumentError("Not a LiveSheet file")
        if int(data.get("version", 0)) > FORMAT_VERSION_PLOT:
            raise DocumentError("This file was made with a newer LiveSheet version")
        regions = []
        for raw in data.get("regions", []):
            try:
                w, h = raw.get("w"), raw.get("h")
                regions.append(RegionData(
                    str(raw["kind"]), float(raw["x"]), float(raw["y"]), str(raw["text"]),
                    None if w is None else float(w), None if h is None else float(h)))
            except (KeyError, TypeError, ValueError) as exc:
                raise DocumentError(f"Invalid region in file: {exc}") from None
        settings = data.get("settings", {}) or {}
        sig = int(settings.get("significant", 6))
        return cls(regions=regions, significant=max(2, min(15, sig)))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SheetDocument":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
