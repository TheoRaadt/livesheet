"""Worksheet document model and the ``.lsheet`` file format (JSON)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

FORMAT_NAME = "livesheet"
FORMAT_VERSION = 1
FILE_SUFFIX = ".lsheet"


class DocumentError(ValueError):
    pass


@dataclass
class RegionData:
    kind: str          # "math" | "text"
    x: float
    y: float
    text: str          # math: source text; text: HTML

    def __post_init__(self):
        if self.kind not in ("math", "text"):
            raise DocumentError(f"Unknown region kind '{self.kind}'")


@dataclass
class SheetDocument:
    regions: list[RegionData] = field(default_factory=list)
    significant: int = 6

    def ordered(self) -> list[RegionData]:
        """Regions in reading order: top to bottom, then left to right."""
        return sorted(self.regions, key=lambda r: (r.y, r.x))

    def to_json(self) -> str:
        data = {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "settings": {"significant": self.significant},
            "regions": [asdict(r) for r in self.ordered()],
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
        if int(data.get("version", 0)) > FORMAT_VERSION:
            raise DocumentError("This file was made with a newer LiveSheet version")
        regions = []
        for raw in data.get("regions", []):
            try:
                regions.append(RegionData(str(raw["kind"]), float(raw["x"]), float(raw["y"]), str(raw["text"])))
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
