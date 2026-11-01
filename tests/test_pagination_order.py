"""Spec 021 phase A: page-aware evaluation order (left to right, then top to bottom, per page)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from livesheet.document import FORMAT_VERSION_PAGES, RegionData, SheetDocument
from livesheet.engine import Engine, wiring
from livesheet.engine.pagination import GRID_UNIT, PAGE_HEIGHT, PAGE_WIDTH, order_key, page_index
from livesheet.gui.worksheet import Worksheet


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _app()
    return Worksheet()


def _doc_results(regions: list[RegionData], breaks=()) -> dict[str, str]:
    """Evaluate through SheetDocument.ordered(); map region text -> output/error."""
    doc = SheetDocument(regions=regions, page_breaks=list(breaks))
    ordered = doc.ordered()
    res = Engine().evaluate(enumerate(r.text for r in ordered))
    return {ordered[i].text: (v.error if v.status == "error" else v.output) for i, v in res.items()}


def _m(x, y, text):
    return RegionData("math", x, y, text)


# -- A1-A4 -----------------------------------------------------------------------------------

def test_a1_left_before_right_even_when_lower():
    out = _doc_results([_m(10, 300, "a := 1"), _m(400, 10, "a =")])
    assert out["a ="] == "= 1"


def test_a2_same_y_x_decides():
    out = _doc_results([_m(10, 50, "a := 2"), _m(300, 50, "a =")])
    assert out["a ="] == "= 2"


def test_a3_same_x_y_decides():
    out = _doc_results([_m(50, 10, "a := 3"), _m(50, 200, "a =")])
    assert out["a ="] == "= 3"


def test_a4_page_dominates_x():
    out = _doc_results([_m(10, 600, "b := 5"), _m(400, 50, "b =")], breaks=[500])
    assert "b is not defined" in out["b ="]


# -- A5 --------------------------------------------------------------------------------------

def test_a5_exact_tie_uses_creation_sequence(tmp_path):
    sheet = _sheet()
    w1 = sheet.add_region("math", QPointF(10, 10), "p := 1")
    w2 = sheet.add_region("math", QPointF(10, 100), "q := 2")
    w1.setPos(200, 200)
    w2.setPos(200, 200)
    for _ in range(3):
        assert sheet.ordered_regions() == [w1, w2]
        sheet.recalculate()
    sheet.clearSelection()
    w2.setSelected(True)
    w2.setZValue(50)
    assert sheet.ordered_regions() == [w1, w2]
    path = tmp_path / "t.lsheet"
    sheet.to_document().save(path)
    sheet2 = _sheet()
    sheet2.load_document(SheetDocument.load(path))
    assert [r.text() for r in sheet2.ordered_regions()] == ["p := 1", "q := 2"]


def test_a5_ties_keep_order_in_document():
    doc = SheetDocument([_m(20, 20, "first"), _m(20, 20, "second"), _m(20, 20, "third")])
    assert [r.text for r in doc.ordered()] == ["first", "second", "third"]


def test_worksheet_order_flip_and_results():
    sheet = _sheet()
    sheet.add_region("math", QPointF(10, 300), "a := 1")
    q = sheet.add_region("math", QPointF(400, 10), "a =")
    sheet.recalculate()
    assert q.result.output == "= 1"


# -- A6 --------------------------------------------------------------------------------------

def test_a6_helpers():
    assert page_index(499.0, [500.0]) == 0
    assert page_index(500.0, [500.0]) == 1
    assert page_index(10.0, []) == 0
    assert page_index(1300.0, [500.0, 1200.0]) == 2
    assert order_key(400.0, 50.0, [500.0]) == (0, 40, 5)
    assert order_key(10.0, 600.0, [500.0]) == (1, 1, 60)
    assert (PAGE_WIDTH, PAGE_HEIGHT, GRID_UNIT) == (820, 1220, 10)


# -- A7 --------------------------------------------------------------------------------------

def test_a7_roundtrip_with_breaks():
    doc = SheetDocument([_m(10, 10, "a"), _m(10, 600, "b"), _m(10, 1300, "c")],
                        page_breaks=[500.0, 1200.0])
    data = json.loads(doc.to_json())
    assert data["version"] == FORMAT_VERSION_PAGES == 4
    assert data["page_breaks"] == [500.0, 1200.0]
    back = SheetDocument.from_json(doc.to_json())
    assert back.page_breaks == [500.0, 1200.0]
    assert [page_index(r.y, back.page_breaks) for r in back.ordered()] == [0, 1, 2]


@pytest.mark.parametrize("version", [1, 2, 3])
def test_a7_old_versions_have_no_breaks(version):
    raw = {"format": "livesheet", "version": version, "regions": []}
    if version == 2:
        raw["regions"] = [{"kind": "plot", "x": 0, "y": 0, "text": "plot", "w": 1, "h": 1}]
    if version == 3:
        raw["wires"] = [{"from_component": "a", "from_port": "o", "to_component": "b", "to_port": "i"}]
    assert SheetDocument.from_json(json.dumps(raw)).page_breaks == []


def test_a7_no_breaks_writes_same_shape():
    doc = SheetDocument([_m(1, 2, "x")])
    data = json.loads(doc.to_json())
    assert data["version"] == 1
    assert "page_breaks" not in data


def test_a7_lenient_parse_and_old_version_honours_breaks():
    raw = {"format": "livesheet", "version": 1, "regions": [],
           "page_breaks": [900, "x", None, True, 100.5, [1]]}
    assert SheetDocument.from_json(json.dumps(raw)).page_breaks == [100.5, 900.0]
    assert SheetDocument.from_json(json.dumps(
        {"format": "livesheet", "version": 1, "regions": [], "page_breaks": "oops"})).page_breaks == []


def test_a7_version_5_rejected_and_bare_v4_accepted():
    from livesheet.document import DocumentError
    with pytest.raises(DocumentError):
        SheetDocument.from_json(json.dumps({"format": "livesheet", "version": 5, "regions": []}))
    SheetDocument.from_json(json.dumps(
        {"format": "livesheet", "version": 4, "regions": [], "page_breaks": [10]}))


def test_worksheet_carries_page_breaks():
    sheet = _sheet()
    doc = SheetDocument([_m(10, 10, "a := 1"), _m(10, 600, "a =")], page_breaks=[500.0])
    sheet.load_document(doc)
    assert sheet.page_break_ys() == [500.0]
    assert sheet.to_document().page_breaks == [500.0]
    sheet.clear_sheet()
    assert sheet.page_break_ys() == []


# -- A8-A11 ----------------------------------------------------------------------------------

@pytest.fixture
def order_log(monkeypatch):
    log: list[list[str]] = []
    real = wiring.topo_sort

    def spy(names, pos_of, edges):
        result = real(names, pos_of, edges)
        log.append(result[0])
        return result

    monkeypatch.setattr(wiring, "topo_sort", spy)
    return log


def _val(name, x, y):
    return wiring.ComponentSpec(name, "value", {"expr": "1 m"}, x, y)


def test_a8_tiebreak_flipped(order_log):
    wiring.evaluate([_val("VR", 400, 10), _val("VL", 10, 300)], [], Engine())
    assert order_log[-1] == ["VL", "VR"]


def test_a9_wire_dominates(order_log):
    vr = _val("VR", 400, 10)
    vl = wiring.ComponentSpec("VL", "formula", {"inputs": "a", "expr": "a"}, 10, 300)
    res = wiring.evaluate([vl, vr], [wiring.WireSpec("VR", "value", "VL", "a")], Engine())
    assert order_log[-1] == ["VR", "VL"]
    assert res["VL"].status == "ok"


def test_a10_page_aware(order_log):
    k1, k2 = _val("K1", 400, 50), _val("K2", 10, 600)
    wiring.evaluate([k1, k2], [], Engine(), page_breaks=[500.0])
    assert order_log[-1] == ["K1", "K2"]
    wiring.evaluate([k1, k2], [], Engine())
    assert order_log[-1] == ["K2", "K1"]


def test_a11_empty_specs():
    assert wiring.evaluate([], [], Engine(), page_breaks=[5.0]) == {}


def test_topo_sort_missing_name_falls_back():
    order, rem = wiring.topo_sort(["b", "a"], {}, set())
    assert order == ["a", "b"] and not rem


# -- A12 -------------------------------------------------------------------------------------

def test_a12_engine_evaluate_takes_explicit_list():
    res = Engine().evaluate([(0, "z := 4"), (1, "z =")])
    assert res[1].output == "= 4"
