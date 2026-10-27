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
