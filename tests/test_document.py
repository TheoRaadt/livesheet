import json

import pytest

from livesheet.document import DocumentError, RegionData, SheetDocument


def test_roundtrip(tmp_path):
    doc = SheetDocument([RegionData("math", 40, 80, "x := 5 m"), RegionData("text", 40, 20, "<b>hi</b>")],
                        significant=4)
    path = tmp_path / "a.lsheet"
    doc.save(path)
    back = SheetDocument.load(path)
    assert back.significant == 4
    # saved in reading order
    assert [r.kind for r in back.regions] == ["text", "math"]
    assert back.regions[1].text == "x := 5 m"


def test_reading_order():
    doc = SheetDocument([RegionData("math", 300, 10, "b"), RegionData("math", 10, 10, "a"),
                         RegionData("math", 10, 50, "c")])
    assert [r.text for r in doc.ordered()] == ["a", "b", "c"]


@pytest.mark.parametrize("text", ["not json", json.dumps({"format": "other"}),
                                  json.dumps({"format": "livesheet", "version": 99})])
def test_rejects_bad_files(text):
    with pytest.raises(DocumentError):
        SheetDocument.from_json(text)


def test_example_file_loads_and_evaluates():
    from pathlib import Path

    from livesheet.engine import Engine

    doc = SheetDocument.load(Path(__file__).parent.parent / "examples" / "demo.lsheet")
    maths = [r for r in doc.ordered() if r.kind == "math"]
    results = Engine().evaluate((i, r.text) for i, r in enumerate(maths))
    errors = [maths[i].text for i, res in results.items() if res.status == "error"]
    assert errors == ["L + F ="]  # the deliberate unit error in the demo


PLOT_TEXT = "plot\nover t\nshow v*t"


def test_plot_roundtrip_version_2():
    doc = SheetDocument([RegionData("math", 40, 100, "v := 3 m/s"),
                         RegionData("plot", 40, 300, PLOT_TEXT, 420, 280)])
    data = json.loads(doc.to_json())
    assert data["version"] == 2
    plot = data["regions"][1]
    assert plot["kind"] == "plot" and plot["w"] == 420.0 and plot["h"] == 280.0
    assert "w" not in data["regions"][0] and "h" not in data["regions"][0]
    back = SheetDocument.from_json(doc.to_json())
    assert back.regions == doc.regions


def test_plot_free_sheet_stays_version_1():
    doc = SheetDocument([RegionData("math", 40, 80, "x := 5 m"), RegionData("text", 40, 20, "hi")])
    data = json.loads(doc.to_json())
    assert data["version"] == 1
    assert all("w" not in r and "h" not in r for r in data["regions"])


def test_demo_resave_unchanged_by_plot_support(tmp_path):
    """Re-saving the demo gives what the pre-plot writer gave (same keys, order, version 1)."""
    from dataclasses import asdict
    from pathlib import Path

    doc = SheetDocument.load(Path(__file__).parent.parent / "examples" / "demo.lsheet")
    old_style = json.dumps({
        "format": "livesheet", "version": 1, "settings": {"significant": doc.significant},
        "regions": [asdict(r) | {} for r in doc.ordered()],
    }, indent=2, ensure_ascii=False)
    old = json.loads(old_style)
    for r in old["regions"]:
        r.pop("w"), r.pop("h")
    assert doc.to_json() == json.dumps(old, indent=2, ensure_ascii=False)
    # and a second save/load cycle is a fixed point
    again = SheetDocument.from_json(doc.to_json()).to_json()
    assert again == doc.to_json()


def test_plot_default_size_and_versions():
    raw = {"format": "livesheet", "version": 2, "regions": [
        {"kind": "plot", "x": 0, "y": 0, "text": PLOT_TEXT}]}
    region = SheetDocument.from_json(json.dumps(raw)).regions[0]
    assert (region.w, region.h) == (400.0, 260.0)
    v1 = {"format": "livesheet", "version": 1, "regions": [{"kind": "math", "x": 0, "y": 0, "text": "a"}]}
    assert SheetDocument.from_json(json.dumps(v1)).regions[0].text == "a"
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(json.dumps({"format": "livesheet", "version": 3}))
    with pytest.raises(DocumentError):
        SheetDocument.from_json(json.dumps({"format": "livesheet", "version": 2, "regions": [
            {"kind": "chart", "x": 0, "y": 0, "text": ""}]}))


def test_plot_reading_order():
    doc = SheetDocument([RegionData("math", 40, 500, "c"), RegionData("plot", 40, 300, PLOT_TEXT),
                         RegionData("math", 40, 100, "a")])
    assert [r.kind for r in doc.ordered()] == ["math", "plot", "math"]
    assert [r.text for r in doc.ordered()][0] == "a"
