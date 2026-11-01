"""Independent black-box tests for spec 021 phase A (page-aware evaluation order), written from
the spec only. Does not rely on tests/test_pagination_order.py."""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from livesheet.document import DocumentError, RegionData, SheetDocument
from livesheet.engine import Engine, wiring
from livesheet.engine.pagination import (GRID_UNIT, PAGE_HEIGHT, PAGE_WIDTH, order_key,
                                         page_index)
from livesheet.gui.worksheet import Worksheet


def _sheet() -> Worksheet:
    QApplication.instance() or QApplication([])
    return Worksheet()


def _m(x, y, text):
    return RegionData("math", x, y, text)


def _eval(regions, breaks=()):
    doc = SheetDocument(regions=list(regions), page_breaks=list(breaks))
    ordered = doc.ordered()
    res = Engine().evaluate(enumerate(r.text for r in ordered))
    return {ordered[i].text: (v.error if v.status == "error" else v.output)
            for i, v in res.items()}


def _raw(version, regions=(), **extra):
    d = {"format": "livesheet", "version": version, "regions": list(regions)}
    d.update(extra)
    return json.dumps(d)


MATH = {"kind": "math", "x": 10, "y": 10, "text": "a := 1"}


# ---- constants / helpers (A6) ----------------------------------------------------------

def test_constants():
    assert (PAGE_WIDTH, PAGE_HEIGHT, GRID_UNIT) == (820, 1220, 10)


def test_a6_page_index():
    assert page_index(499.0, [500.0]) == 0
    assert page_index(500.0, [500.0]) == 1
    assert page_index(10.0, []) == 0
    assert page_index(1300.0, [500.0, 1200.0]) == 2


def test_a6_order_key():
    assert order_key(400.0, 50.0, [500.0]) == (0, 40, 5)
    assert order_key(10.0, 600.0, [500.0]) == (1, 1, 60)
    assert order_key(10.0, 600.0) == (0, 1, 60)


def test_page_index_duplicate_breaks_count_twice():
    assert page_index(600, [500, 500]) == 2
    assert page_index(499, [500, 500]) == 0


def test_page_index_unsorted_breaks_still_counts():
    assert page_index(1300, [1200.0, 500.0]) == 2


def test_order_key_grid_snapping_removes_float_noise():
    assert order_key(100.0000001, 49.9999999) == order_key(100.0, 50.0)


# ---- A1-A4 engine level -----------------------------------------------------------------

def test_a1():
    assert _eval([_m(10, 300, "a := 1"), _m(400, 10, "a =")])["a ="] == "= 1"


def test_a2():
    assert _eval([_m(10, 50, "a := 2"), _m(300, 50, "a =")])["a ="] == "= 2"


def test_a3():
    assert _eval([_m(50, 10, "a := 3"), _m(50, 200, "a =")])["a ="] == "= 3"


def test_a4_page_dominates():
    out = _eval([_m(10, 600, "b := 5"), _m(400, 50, "b =")], breaks=[500])
    assert "b is not defined" in out["b ="]


def test_a4_without_break_is_single_page():
    out = _eval([_m(10, 600, "b := 5"), _m(400, 50, "b =")])
    assert out["b ="] == "= 5"


def test_region_exactly_on_break_belongs_to_next_page():
    # definer at y=500 exactly (page 2), user at y=499 (page 1) with larger... smaller x? use x
    out = _eval([_m(400, 500, "c := 7"), _m(10, 490, "c =")], breaks=[500])
    assert "c is not defined" in out["c ="]
    # user exactly on break (page 2), definer on page 1 with larger x: definer first
    out = _eval([_m(500, 100, "d := 7"), _m(10, 500, "d =")], breaks=[500])
    assert out["d ="] == "= 7"


def test_two_breaks_same_y_do_not_crash_and_empty_page():
    doc = SheetDocument(regions=[_m(10, 10, "a := 1"), _m(10, 700, "a =")],
                        page_breaks=[500, 500])
    out = _eval(doc.regions, [500, 500])
    assert out["a ="] == "= 1"
    rt = SheetDocument.from_json(doc.to_json())
    assert rt.page_breaks == [500.0, 500.0]


def test_page_3_after_page_2_chain():
    out = _eval([_m(300, 1300, "z =" ), _m(10, 700, "z := 4"), _m(500, 10, "w := 1")],
                breaks=[500, 1200])
    assert out["z ="] == "= 4"


def test_unsorted_page_breaks_on_document_are_sorted_for_order():
    out = _eval([_m(10, 1300, "q := 1"), _m(400, 50, "q =")], breaks=[1200, 500])
    assert "q is not defined" in out["q ="]


def test_ordered_sub_grid_noise_ties_keep_list_order():
    regs = [_m(100.0, 50.0, "t1 := 1"), _m(100.0000001, 50.0000001, "t1 =")]
    assert [r.text for r in SheetDocument(regions=regs).ordered()] == ["t1 := 1", "t1 ="]
    regs.reverse()
    assert [r.text for r in SheetDocument(regions=regs).ordered()] == ["t1 =", "t1 := 1"]


# ---- A5 creation-sequence tie-break ------------------------------------------------------

def test_a5_tie_break_creation_order_and_roundtrip(tmp_path):
    sheet = _sheet()
    w1 = sheet.add_region("math", QPointF(10, 10), "p := 1")
    w2 = sheet.add_region("math", QPointF(10, 100), "p =")
    w2.setPos(QPointF(200, 200))
    w1.setPos(QPointF(200, 200))   # moved last, selected last: still created first
    for _ in range(3):
        assert sheet.ordered_regions() == [w1, w2]
        sheet.recalculate()
    assert w2.result.output == "= 1"
    w2.setSelected(True)
    w1.setSelected(True)
    w2.setZValue(10)
    assert sheet.ordered_regions() == [w1, w2]
    path = tmp_path / "t.lsheet"
    sheet.to_document().save(path)
    s2 = _sheet()
    s2.load_document(SheetDocument.load(path))
    assert [r.text() for r in s2.ordered_regions()] == ["p := 1", "p ="]
    s2.recalculate()
    assert s2.ordered_regions()[1].result.output == "= 1"


def test_creation_sequence_survives_moving_then_new_region_after_load(tmp_path):
    sheet = _sheet()
    a = sheet.add_region("math", QPointF(10, 10), "k := 1")
    b = sheet.add_region("math", QPointF(10, 10), "k =")   # same snapped spot
    assert sheet.ordered_regions() == [a, b]
    path = tmp_path / "t.lsheet"
    sheet.to_document().save(path)
    s2 = _sheet()
    s2.load_document(SheetDocument.load(path))
    first, second = s2.ordered_regions()
    c = s2.add_region("math", QPointF(10, 10), "k2")   # created after load, tied
    assert s2.ordered_regions() == [first, second, c]
    first.setPos(QPointF(300, 10))
    first.setPos(QPointF(10, 10))
    assert s2.ordered_regions() == [first, second, c]


def test_reordered_file_with_ties_loaded_in_file_order():
    raw = _raw(1, [{"kind": "math", "x": 50, "y": 50, "text": "n := 9"},
                   {"kind": "math", "x": 50, "y": 50, "text": "n ="}])
    s = _sheet()
    s.load_document(SheetDocument.from_json(raw))
    assert [r.text() for r in s.ordered_regions()] == ["n := 9", "n ="]
    assert s.ordered_regions()[1].result.output == "= 9"


def test_gui_page_break_loaded_changes_worksheet_order():
    s = _sheet()
    doc = SheetDocument(regions=[_m(10, 600, "b := 5"), _m(400, 50, "b =")], page_breaks=[500])
    s.load_document(doc)
    assert s.page_break_ys() == [500.0]
    users = [r for r in s.regions() if r.text() == "b ="]
    assert "not defined" in users[0].result.error


def test_gui_region_exactly_on_break_page_2():
    s = _sheet()
    s.load_document(SheetDocument(regions=[_m(500, 100, "d := 7"), _m(10, 500, "d =")],
                                  page_breaks=[500]))
    users = [r for r in s.regions() if r.text() == "d ="]
    assert users[0].result.output == "= 7"


def test_gui_save_load_order_stable_with_breaks(tmp_path):
    s = _sheet()
    s.load_document(SheetDocument(
        regions=[_m(10, 700, "a := 1"), _m(400, 50, "b := 2"), _m(10, 50, "c := 3"),
                 _m(10, 1300, "d := a + b")], page_breaks=[500, 1200]))
    before = [r.text() for r in s.ordered_regions()]
    p = tmp_path / "x.lsheet"
    s.to_document().save(p)
    data = json.loads(p.read_text())
    assert data["version"] == 4 and data["page_breaks"] == [500.0, 1200.0]
    assert [r["text"] for r in data["regions"]] == before
    s2 = _sheet()
    s2.load_document(SheetDocument.load(p))
    assert [r.text() for r in s2.ordered_regions()] == before
    assert s2.page_break_ys() == [500.0, 1200.0]


def test_new_sheet_clears_page_breaks():
    s = _sheet()
    s.load_document(SheetDocument(regions=[_m(10, 10, "a := 1")], page_breaks=[500]))
    s.clear_sheet()
    assert s.page_break_ys() == []
    assert s.to_document().page_breaks == []


# ---- A7 file format ----------------------------------------------------------------------

def test_a7_roundtrip_and_version():
    doc = SheetDocument(regions=[_m(10, 10, "a := 1")], page_breaks=[500.0, 1200.0])
    data = json.loads(doc.to_json())
    assert data["version"] == 4
    assert data["page_breaks"] == [500.0, 1200.0]
    assert SheetDocument.from_json(doc.to_json()).page_breaks == [500.0, 1200.0]


@pytest.mark.parametrize("v", [1, 2, 3])
def test_a7_old_versions_have_no_breaks(v):
    regs = [MATH]
    if v == 2:
        regs = [{"kind": "plot", "x": 0, "y": 0, "text": "plot(x)"}]
    if v == 3:
        regs = [{"kind": "component", "x": 0, "y": 0, "text": "", "component_name": "V",
                 "component_kind": "value", "config": {"expr": "1"}}]
    assert SheetDocument.from_json(_raw(v, regs)).page_breaks == []


def test_a7_no_breaks_no_key_and_old_versions_written():
    d1 = json.loads(SheetDocument(regions=[_m(1, 1, "a")]).to_json())
    assert d1["version"] == 1 and "page_breaks" not in d1
    d2 = json.loads(SheetDocument(regions=[RegionData("plot", 0, 0, "x")]).to_json())
    assert d2["version"] == 2 and "page_breaks" not in d2


def test_breaks_only_file_v4_loads():
    doc = SheetDocument.from_json(_raw(4, [MATH], page_breaks=[100]))
    assert doc.page_breaks == [100.0]


def test_breaks_plus_component_writes_v4():
    comp = RegionData("component", 0, 0, "", component_name="V", component_kind="value",
                      config={"expr": "1"})
    assert SheetDocument(regions=[comp], page_breaks=[10]).version() == 4


def test_breaks_below_v4_version_still_honoured_then_saved_as_v4():
    doc = SheetDocument.from_json(_raw(1, [MATH], page_breaks=[300]))
    assert doc.page_breaks == [300.0]
    assert json.loads(doc.to_json())["version"] == 4


def test_version_5_rejected():
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(_raw(5))


def test_version_3_without_components_still_rejected():
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(_raw(3, [MATH]))


def test_version_3_with_only_breaks_and_no_components_rejected_per_spec():
    # spec: "declared version 3 but no component/wire content is rejected" stays as is
    with pytest.raises(DocumentError):
        SheetDocument.from_json(_raw(3, [MATH], page_breaks=[100]))


def test_version_4_bare_no_content_is_accepted_leniently():
    # spec: no analogous guard for version 4
    SheetDocument.from_json(_raw(4, [MATH]))


@pytest.mark.parametrize("raw,expected", [
    ("oops", []), (5, []), (None, []), ({"a": 1}, []),
    (["x", None, [1], {"y": 1}, True, False, 300, 100.5, "200"], [100.5, 300.0]),
    ([float("nan")], []),
    ([3, 1, 2], [1.0, 2.0, 3.0]),
    ([], []),
])
def test_malformed_page_breaks_lenient(raw, expected):
    doc = SheetDocument.from_json(_raw(4, [MATH], page_breaks=raw))
    assert doc.page_breaks == expected


def test_infinity_literal_in_json_dropped():
    text = _raw(4, [MATH]).replace("}", ', "page_breaks": [Infinity, -Infinity, 50]}', 1) \
        if False else None
    raw = '{"format":"livesheet","version":4,"regions":[],"page_breaks":[Infinity,50]}'
    assert SheetDocument.from_json(raw).page_breaks == [50.0]


def test_ordered_does_not_mutate_inputs():
    doc = SheetDocument(regions=[_m(400, 10, "b"), _m(10, 300, "a")], page_breaks=[500, 100])
    doc.ordered()
    assert doc.page_breaks == [500, 100]
    assert [r.text for r in doc.regions] == ["b", "a"]


def test_to_json_sorts_breaks():
    d = json.loads(SheetDocument(page_breaks=[900, 100]).to_json())
    assert d["page_breaks"] == [100.0, 900.0]


# ---- wiring (A8-A11) ---------------------------------------------------------------------

@pytest.fixture
def order_log(monkeypatch):
    log: list[str] = []
    orig = wiring._COMPUTE["value"]

    def rec(config, inputs, engine):
        log.append(config["tag"])
        return orig({"expr": "1"}, inputs, engine)
    monkeypatch.setitem(wiring._COMPUTE, "value", rec)
    return log


def _v(name, x, y):
    return wiring.ComponentSpec(name, "value", {"expr": "1", "tag": name}, x, y)


def test_a8_wiring_tiebreak_flip(order_log):
    wiring.evaluate([_v("VL", 10, 300), _v("VR", 400, 10)], [], Engine())
    assert order_log == ["VL", "VR"]


def test_a8_same_x_y_decides(order_log):
    wiring.evaluate([_v("B", 10, 300), _v("A", 10, 10)], [], Engine())
    assert order_log == ["A", "B"]


def test_a9_wire_dominates(order_log):
    vl = wiring.ComponentSpec("VL", "formula", {"inputs": "a", "expr": "a", "tag": "VL"}, 10, 300)
    orig = wiring._COMPUTE["formula"]

    def rec(config, inputs, engine):
        order_log.append("VL")
        return orig(config, inputs, engine)
    wiring._COMPUTE["formula"] = rec
    try:
        res = wiring.evaluate([vl, _v("VR", 400, 10)],
                              [wiring.WireSpec("VR", "value", "VL", "a")], Engine())
    finally:
        wiring._COMPUTE["formula"] = orig
    assert order_log == ["VR", "VL"]
    assert res["VL"].status == "ok"


def test_a10_page_aware(order_log):
    specs = [_v("K1", 400, 50), _v("K2", 10, 600)]
    wiring.evaluate(specs, [], Engine(), page_breaks=[500.0])
    assert order_log == ["K1", "K2"]
    order_log.clear()
    wiring.evaluate(specs, [], Engine())
    assert order_log == ["K2", "K1"]


def test_a10_unsorted_breaks_and_positional_keyword(order_log):
    specs = [_v("K1", 400, 50), _v("K2", 10, 600), _v("K3", 5, 1300)]
    wiring.evaluate(specs, [], Engine(), page_breaks=[1200.0, 500.0])
    assert order_log == ["K1", "K2", "K3"]


def test_wiring_component_on_break_is_next_page(order_log):
    wiring.evaluate([_v("K1", 400, 100), _v("K2", 10, 500)], [], Engine(), page_breaks=[500])
    assert order_log == ["K1", "K2"]


def test_a11_empty_specs():
    assert wiring.evaluate([], [], Engine()) == {}
    assert wiring.evaluate([], [], Engine(), page_breaks=[1.0]) == {}


def test_topo_sort_accepts_two_tuple_and_three_tuple_keys():
    names = ["a", "b"]
    assert wiring.topo_sort(names, {"a": (2, 0), "b": (1, 0)}, set())[0] == ["b", "a"]
    assert wiring.topo_sort(names, {"a": (0, 2, 0), "b": (0, 1, 0)}, set())[0] == ["b", "a"]
    # missing name falls back, must not raise with 3-tuple keys alongside
    order, rem = wiring.topo_sort(["a", "z"], {"a": (0, 5, 5)}, set())
    assert set(order) == {"a", "z"} and not rem


def test_gui_worksheet_components_use_page_breaks_and_flip():
    s = _sheet()
    doc = SheetDocument(regions=[
        RegionData("component", 400, 50, "", component_name="K1", component_kind="value",
                   config={"expr": "1 m"}),
        RegionData("component", 10, 600, "", component_name="K2", component_kind="value",
                   config={"expr": "2 m"})], page_breaks=[500])
    s.load_document(doc)
    names = [r.component_name for r in s.ordered_regions()]
    assert names == ["K1", "K2"]
    s.load_document(SheetDocument(regions=doc.regions))
    assert [r.component_name for r in s.ordered_regions()] == ["K2", "K1"]


# ---- A12 + examples ---------------------------------------------------------------------

def test_a12_engine_evaluate_explicit_list_unchanged():
    res = Engine().evaluate([(0, "a := 2"), (1, "a =")])
    assert res[1].output == "= 2"


def test_demo_example_has_no_errors_with_new_order():
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "examples" / "demo.lsheet"
    s = _sheet()
    s.load_document(SheetDocument.load(p))
    s.recalculate()
    errs = [(r.text(), r.result.error) for r in s.regions()
            if getattr(r, "result", None) is not None and r.result.status == "error"]
    # the demo ends with a deliberate unit-mismatch line "L + F ="
    assert [e for e in errs if not e[0].startswith("L + F")] == []
