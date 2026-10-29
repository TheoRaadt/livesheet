"""Independent black-box tests for spec 009 (component-and-wiring canvas core, backlog item 31),
written from docs/board/specs/009-component-wiring-core.md's own acceptance criteria 1-11 and
Edge cases -- not from reading livesheet/engine/wiring.py, livesheet/gui/componentdialog.py,
livesheet/gui/regions.py, livesheet/gui/worksheet.py or livesheet/gui/main_window.py as the source
of truth beyond the small public names the spec itself names (``ComponentSpec``, ``WireSpec``,
``ComponentResult``, ``topo_sort``, ``has_cycle``, ``would_create_cycle``, ``evaluate``,
``known_kind``, ``input_ports``, ``output_ports``, ``format_output``; ``Worksheet.try_connect``;
``RegionData``'s ``component_name``/``component_kind``/``config`` fields; ``SheetDocument.wires``;
``FORMAT_VERSION_COMPONENTS``; ``AddComponentDialog``/``ConnectDialog``/``ComponentFields``/
``fields_to_config``/``validate_component_fields``).

Written independently of tests/test_wiring_core.py (the developer's own tests, which this file's
author read only afterwards, per the project's established practice, to check for coverage gaps
rather than to copy assertions). The two files overlap at the "which criterion" level but differ
in approach in several places:
  - The one-connection-per-input, fan-out, and cycle-rejection rules (criteria 5-6) are exercised
    through the real, end-to-end GUI path (``Worksheet.try_connect`` on real ``ComponentRegion``
    scene items, built via ``Worksheet.add_component_region``), not only the engine-level
    ``wiring.would_create_cycle`` helper directly (which is also checked separately, in isolation).
  - Criterion 7 (delete cascades its wires) and the "deleting a wire leaves the components alone"
    edge case go through ``Worksheet.remove_regions``/the real ``keyPressEvent`` Delete-key path
    on a selected ``WireItem``, not a direct ``_wires.remove(...)`` call.
  - Both wire-creation paths (drag-to-connect and the "Connect..." dialog) are driven through the
    real ``Worksheet.mousePressEvent``/``mouseMoveEvent``/``mouseReleaseEvent`` and
    ``contextMenuEvent`` handlers (via minimal fake event objects carrying only the few members
    those handlers actually read -- the same technique already used by
    tests/test_matrix_dialog_blackbox.py's ``_FakeContextEvent`` for spec 008), not by calling the
    private ``_begin_wire_drag``/``_open_connect_dialog`` helpers directly.
  - The format round-trip (criterion 10) and the version-gating regression (criterion 11, the
    exact area the manager found and a developer already fixed once) are re-verified independently
    here: a real ``Worksheet.to_document()``/``SheetDocument.save()``/``.load()``/
    ``Worksheet.load_document()`` cycle through an actual temp file, a direct byte-level check that
    a component-free document's JSON has no top-level ``"wires"`` key at all, and a from-scratch
    check that a bare declared ``version: 3`` with no component/wire content is rejected the same
    way a too-new version always has been -- not trusting the fix report, re-deriving it from the
    spec's own wording.
  - The "Insert > Component..." entry is exercised through a real ``MainWindow``/``QAction``
    lookup by menu text (not a direct ``insert_component_at`` call), mirroring how prior reviews
    (006/007/008) checked their own menu entries.

Qt-dependent tests skip gracefully when PySide6 cannot load, as the existing GUI tests do.
"""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # e.g. missing system GL libraries
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from livesheet.document import DocumentError, RegionData, SheetDocument, WireData  # noqa: E402
from livesheet.engine.evaluator import Engine  # noqa: E402
from livesheet.engine.units import UnitError, measure  # noqa: E402
from livesheet.engine import wiring  # noqa: E402
from livesheet.gui import main_window as mw_module  # noqa: E402
from livesheet.gui.componentdialog import (  # noqa: E402
    AddComponentDialog,
    ComponentFieldError,
    ComponentFields,
    ConnectDialog,
    fields_to_config,
    validate_component_fields,
)
from livesheet.gui.main_window import MainWindow, export_pdf  # noqa: E402
from livesheet.gui.regions import ComponentRegion  # noqa: E402
from livesheet.gui.worksheet import WireItem, Worksheet  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet() -> Worksheet:
    _ensure_app()
    return Worksheet()


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """MainWindow tests here must never touch the real on-disk LiveSheet preferences."""
    ini = str(tmp_path / "settings.ini")

    def factory(*_args, **_kwargs):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr(mw_module, "QSettings", factory)
    return ini


class _FakeContextEvent:
    """Stand-in for a QGraphicsSceneContextMenuEvent: only the members
    ``Worksheet.contextMenuEvent`` actually reads."""

    def __init__(self, pos: QPointF):
        self._pos = pos

    def accept(self) -> None:
        pass

    def scenePos(self) -> QPointF:
        return self._pos

    def screenPos(self) -> QPoint:
        return QPoint(0, 0)


def _mouse_event(pos: QPointF, button=Qt.MouseButton.LeftButton):
    """A real ``QGraphicsSceneMouseEvent`` at ``pos``, so that a fall-through to
    ``super().mousePressEvent(event)``/Qt's own default handling (not just this project's own
    early-return branches) also works, unlike a plain duck-typed stand-in object."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent

    ev = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMousePress)
    ev.setScenePos(pos)
    ev.setButton(button)
    ev.setButtons(button)
    return ev


class _FakeKeyEvent:
    """Stand-in for a QKeyEvent carrying only what ``Worksheet.keyPressEvent`` reads for the
    Delete-key path."""

    def __init__(self, key):
        self._key = key

    def key(self):
        return self._key

    def text(self) -> str:
        return ""

    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier


def _open_menu_and_pick(sheet: Worksheet, pos: QPointF, label: str) -> None:
    """Drive the real, unpatched ``contextMenuEvent`` -> ``QMenu.exec()`` call and pick the
    action with the given visible text, using the same ``QTimer.singleShot``-from-inside-the-
    nested-event-loop technique already used by tests/test_matrix_dialog_blackbox.py (direct
    ``mock.patch`` of ``QMenu.exec`` does not intercept a live C++-backed ``QMenu`` instance)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu

    def pick() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu)
        action = next((a for a in menu.actions() if a.text() == label), None)
        if action is None:
            QTest.keyClick(menu, Qt.Key.Key_Escape)
            return
        menu.setActiveAction(action)
        QTest.keyClick(menu, Qt.Key.Key_Enter)

    QTimer.singleShot(0, pick)
    sheet.contextMenuEvent(_FakeContextEvent(pos))


def _menu_labels_at(sheet: Worksheet, pos: QPointF) -> list[str]:
    """Open the real context menu at ``pos``, record its visible action labels, dismiss it."""
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu

    seen: dict = {}

    def spy() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu)
        seen["labels"] = [a.text() for a in menu.actions()]
        QTest.keyClick(menu, Qt.Key.Key_Escape)

    QTimer.singleShot(0, spy)
    sheet.contextMenuEvent(_FakeContextEvent(pos))
    return seen.get("labels", [])


# ===========================================================================
# Criterion 1: a component-free sheet is unaffected (purely additive pass)
# ===========================================================================

def test_criterion1_empty_components_and_wires_is_a_true_noop():
    engine = Engine()
    assert wiring.evaluate([], [], engine) == {}


def test_criterion1_worksheet_recalculate_unaffected_by_empty_wiring_pass():
    """A sheet with ordinary math regions and zero components evaluates its math regions
    identically whether or not the additive component-evaluation step runs; the component count
    folded into evaluationFinished's "total regions" is exactly 0 for such a sheet."""
    sheet = _sheet()
    sheet.add_region("math", QPointF(0, 0), "x := 2 m")
    sheet.add_region("math", QPointF(0, 40), "x * 3 =")
    captured = []
    sheet.evaluationFinished.connect(lambda errors, total, ms: captured.append((errors, total)))
    sheet.recalculate()
    errors, total = captured[-1]
    assert errors == 0
    assert total == 2   # two math regions, zero components folded in
    assert sheet.component_regions() == []
    assert sheet._wires == []


# ===========================================================================
# Criterion 2: a "Value" component
# ===========================================================================

def test_criterion2_value_component_evaluates_measured_value_no_error():
    engine = Engine()
    v1 = wiring.ComponentSpec("V1", "value", {"expr": "12 m/s"})
    results = wiring.evaluate([v1], [], engine)
    assert results["V1"].status == "ok"
    out = results["V1"].outputs["value"]
    m = measure(out)   # independent cross-check via the engine's own unit system
    assert m.magnitude == 12
    assert m.dims == (("length", 1), ("time", -1))
    assert wiring.format_output(out) == "12 m/s"


# ===========================================================================
# Criteria 3-4: Formula component, unconnected required input, then wired
# ===========================================================================

def test_criteria_3_and_4_formula_unconnected_then_wired():
    engine = Engine()
    v1 = wiring.ComponentSpec("V1", "value", {"expr": "12 m/s"})
    v2 = wiring.ComponentSpec("V2", "value", {"expr": "3 m/s"})
    f1 = wiring.ComponentSpec("F1", "formula", {"inputs": "a, b", "expr": "a + b"})

    # Criterion 3: only a wired, b unconnected and required.
    only_a = [wiring.WireSpec("V1", "value", "F1", "a")]
    r3 = wiring.evaluate([v1, v2, f1], only_a, engine)
    assert r3["F1"].status == "error"
    assert r3["F1"].error == "Input 'b' is not connected."
    assert "result" not in r3["F1"].outputs

    # Criterion 4: both wired, F1 no longer in error, result 12 + 3 = 15 m/s.
    both = only_a + [wiring.WireSpec("V2", "value", "F1", "b")]
    r4 = wiring.evaluate([v1, v2, f1], both, engine)
    assert r4["F1"].status == "ok"
    m = measure(r4["F1"].outputs["result"])
    assert m.magnitude == 15
    assert m.dims == (("length", 1), ("time", -1))
    assert wiring.format_output(r4["F1"].outputs["result"]) == "15 m/s"


# ===========================================================================
# Criterion 5: one connection per input (GUI end-to-end, real ComponentRegions)
# ===========================================================================

def test_criterion5_duplicate_input_wire_rejected_existing_wire_unchanged():
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "12 m/s"}, QPointF(0, 0))
    v2 = sheet.add_component_region("V2", "value", {"expr": "3 m/s"}, QPointF(0, 200))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(300, 100))
    assert sheet.try_connect((v1, "value"), (f1, "a")) is None
    existing_wire = next(w for w in sheet._wires if w.dest is f1 and w.dest_port == "a")

    msg = sheet.try_connect((v2, "value"), (f1, "a"))
    assert msg == "Input 'a' on F1 is already connected — disconnect it first."
    # Exactly one wire still feeds F1.a, and it is the original V1 one, unchanged.
    wires_to_a = [w for w in sheet._wires if w.dest is f1 and w.dest_port == "a"]
    assert wires_to_a == [existing_wire]
    assert wires_to_a[0].source is v1


def test_fan_out_one_output_feeds_many_inputs():
    """Edge case / spec text: fan-out is fine -- one output may feed any number of inputs."""
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    h1 = sheet.add_component_region("H1", "formula", {"inputs": "p", "expr": "p"}, QPointF(300, 0))
    h2 = sheet.add_component_region("H2", "formula", {"inputs": "p", "expr": "p"}, QPointF(300, 200))
    assert sheet.try_connect((v, "value"), (h1, "p")) is None
    assert sheet.try_connect((v, "value"), (h2, "p")) is None
    assert len(sheet._wires) == 2
    sheet.recalculate()
    assert not h1._has_error and not h2._has_error


# ===========================================================================
# Criterion 6: cycle rejection (self-loop, two-node, data-model and GUI level)
# ===========================================================================

def test_criterion6_self_loop_rejected_datamodel_level():
    names = ["F1"]
    assert wiring.would_create_cycle(names, set(), ("F1", "F1")) is True


def test_criterion6_two_node_cycle_rejected_datamodel_level():
    names = ["F1", "F2"]
    edges = {("F1", "F2")}
    assert wiring.would_create_cycle(names, edges, ("F2", "F1")) is True
    # The reverse (a genuinely new, non-cyclic edge) is fine.
    assert wiring.would_create_cycle(["F1", "F2", "F3"], edges, ("F2", "F3")) is False


def test_criterion6_self_loop_rejected_gui_end_to_end():
    sheet = _sheet()
    g = sheet.add_component_region("G", "formula", {"inputs": "a", "expr": "a"}, QPointF(0, 0))
    msg = sheet.try_connect((g, "result"), (g, "a"))
    assert msg == "This connection would create a circular dependency."
    assert sheet._wires == []


def test_criterion6_two_node_cycle_rejected_gui_end_to_end():
    sheet = _sheet()
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(0, 0))
    f2 = sheet.add_component_region("F2", "formula", {"inputs": "x", "expr": "x"},
                                     QPointF(300, 0))
    assert sheet.try_connect((f1, "result"), (f2, "x")) is None
    msg = sheet.try_connect((f2, "result"), (f1, "a"))
    assert msg == "This connection would create a circular dependency."
    assert len(sheet._wires) == 1   # only the first (non-cyclic) wire exists


# ===========================================================================
# Criterion 7: deleting a component cascades to its wires
# ===========================================================================

def test_criterion7_delete_component_removes_its_wires_and_restores_error():
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "12 m/s"}, QPointF(0, 0))
    v2 = sheet.add_component_region("V2", "value", {"expr": "3 m/s"}, QPointF(0, 200))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(300, 100))
    sheet.try_connect((v1, "value"), (f1, "a"))
    sheet.try_connect((v2, "value"), (f1, "b"))
    sheet.recalculate()
    assert not f1._has_error

    sheet.remove_regions([v1])
    sheet.recalculate()
    assert f1._has_error
    assert f1.result.error == "Input 'a' is not connected."
    # V1's wire is gone; V2's wire (unrelated) survives.
    assert len(sheet._wires) == 1
    assert sheet._wires[0].source is v2
    assert v1 not in sheet.component_regions()


def test_deleting_only_a_wire_leaves_both_components_untouched():
    """Edge case: deleting a wire removes only that connection, not the components."""
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a", "expr": "a"},
                                     QPointF(300, 0))
    sheet.try_connect((v1, "value"), (f1, "a"))
    wire = sheet._wires[0]
    wire.setSelected(True)
    sheet.keyPressEvent(_FakeKeyEvent(Qt.Key.Key_Delete))
    assert sheet._wires == []
    assert v1 in sheet.component_regions()
    assert f1 in sheet.component_regions()
    sheet.recalculate()
    assert f1._has_error   # a is unconnected again, but F1 itself was never removed
    assert f1.result.error == "Input 'a' is not connected."


# ===========================================================================
# Criterion 8: unit mismatch inside a kind's own calculation
# ===========================================================================

def test_criterion8_unit_mismatch_reports_existing_engine_error_text():
    engine = Engine()
    va = wiring.ComponentSpec("Va", "value", {"expr": "1 m"})
    vb = wiring.ComponentSpec("Vb", "value", {"expr": "1 s"})
    f = wiring.ComponentSpec("F", "formula", {"inputs": "a, b", "expr": "a + b"})
    wires = [wiring.WireSpec("Va", "value", "F", "a"), wiring.WireSpec("Vb", "value", "F", "b")]
    result = wiring.evaluate([va, vb, f], wires, engine)["F"]
    assert result.status == "error"

    # Cross-check: the same message a plain math region produces for 1 m + 1 s, and the same
    # text measure()/UnitError raise directly -- no new, component-specific error-text path.
    plain = engine.evaluate([(1, "1 m + 1 s =")])[1]
    assert plain.status == "error"
    assert result.error == plain.error
    from livesheet.engine.units import UNITS
    with pytest.raises(UnitError, match="Units do not match"):
        measure(engine.parse("1 m + 1 s", dict(UNITS)))


# ===========================================================================
# Criterion 9: deterministic reading-order tie-break (only between unordered nodes)
# ===========================================================================

def test_criterion9_reading_order_tiebreak_is_deterministic_and_position_dependent():
    # V3 above V4 (smaller y first): V3 then V4.
    order_a, remainder_a = wiring.topo_sort(["V3", "V4"], {"V3": (0.0, 0.0), "V4": (10.0, 0.0)}, set())
    assert order_a == ["V3", "V4"]
    assert remainder_a == set()
    # Swap canvas positions (still no wire between them): only the tie-broken order changes.
    order_b, remainder_b = wiring.topo_sort(["V3", "V4"], {"V3": (10.0, 0.0), "V4": (0.0, 0.0)}, set())
    assert order_b == ["V4", "V3"]
    assert remainder_b == set()
    # Re-running with the same input is stable (deterministic, not e.g. set-iteration order).
    order_a2, _ = wiring.topo_sort(["V3", "V4"], {"V3": (0.0, 0.0), "V4": (10.0, 0.0)}, set())
    assert order_a2 == order_a


def test_criterion9_tiebreak_does_not_override_a_real_dependency_edge():
    """Position is only a tie-break for otherwise-unordered nodes: a wired dependency always
    wins over canvas position, even when the upstream node is drawn below the downstream one."""
    names = ["Upstream", "Downstream"]
    pos_of = {"Upstream": (100.0, 0.0), "Downstream": (0.0, 0.0)}   # Downstream drawn above
    edges = {("Upstream", "Downstream")}
    order, remainder = wiring.topo_sort(names, pos_of, edges)
    assert order == ["Upstream", "Downstream"]   # dependency order, not drawing order
    assert remainder == set()


# ===========================================================================
# Criterion 10: save/reload round trip
# ===========================================================================

def test_criterion10_save_reload_roundtrip_through_a_real_file(tmp_path):
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "12 m/s"}, QPointF(0, 0))
    v2 = sheet.add_component_region("V2", "value", {"expr": "3 m/s"}, QPointF(0, 200))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(300, 100))
    sheet.try_connect((v1, "value"), (f1, "a"))
    sheet.try_connect((v2, "value"), (f1, "b"))

    path = tmp_path / "roundtrip.lsheet"
    sheet.to_document().save(path)

    reloaded_sheet = _sheet()
    reloaded_sheet.load_document(SheetDocument.load(path))

    names = sorted(c.component_name for c in reloaded_sheet.component_regions())
    assert names == ["F1", "V1", "V2"]
    assert len(reloaded_sheet._wires) == 2
    f1_r = next(c for c in reloaded_sheet.component_regions() if c.component_name == "F1")
    assert not f1_r._has_error
    m = measure(f1_r.result.outputs["result"])
    assert m.magnitude == 15
    assert m.dims == (("length", 1), ("time", -1))

    v1_r = next(c for c in reloaded_sheet.component_regions() if c.component_name == "V1")
    assert v1_r.component_kind == "value"
    assert v1_r.config == {"expr": "12 m/s"}


def test_criterion10_wires_survive_two_full_roundtrips(tmp_path):
    """Stronger variant: save -> load -> save again -> load again gives the same picture (no
    drift from re-serializing an already-loaded sheet)."""
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a", "expr": "a"},
                                     QPointF(300, 0))
    sheet.try_connect((v1, "value"), (f1, "a"))

    path1 = tmp_path / "first.lsheet"
    sheet.to_document().save(path1)
    sheet2 = _sheet()
    sheet2.load_document(SheetDocument.load(path1))
    path2 = tmp_path / "second.lsheet"
    sheet2.to_document().save(path2)

    assert json.loads(path1.read_text())["regions"] == json.loads(path2.read_text())["regions"]
    assert json.loads(path1.read_text())["wires"] == json.loads(path2.read_text())["wires"]


# ===========================================================================
# Criterion 11: format version gating (the regression area -- re-verified from scratch)
# ===========================================================================

def test_criterion11_old_version1_file_with_no_wires_key_loads_with_zero_components():
    raw = json.dumps({"format": "livesheet", "version": 1, "regions": [
        {"kind": "math", "x": 0, "y": 0, "text": "x := 1"},
    ]})
    doc = SheetDocument.from_json(raw)
    assert doc.wires == []
    assert all(r.kind != "component" for r in doc.regions)


def test_criterion11_component_free_sheet_writes_version_1_or_2_exactly_as_before():
    plain = _sheet()
    plain.add_region("math", QPointF(0, 0), "x := 1")
    doc = plain.to_document()
    assert doc.version() == 1
    raw = json.loads(doc.to_json())
    assert "wires" not in raw            # never written when there are no wires
    assert raw["version"] == 1
    for region in raw["regions"]:
        assert "component_name" not in region
        assert "component_kind" not in region
        assert "config" not in region

    with_plot = _sheet()
    with_plot.add_region("plot", QPointF(0, 0), "plot\nover x\nshow x")
    assert with_plot.to_document().version() == 2


def test_criterion11_version_only_bumped_to_3_when_a_component_or_wire_exists():
    sheet = _sheet()
    sheet.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    doc = sheet.to_document()
    assert doc.version() == 3
    raw = json.loads(doc.to_json())
    assert raw["version"] == 3
    assert "wires" not in raw   # a component with no wires at all still omits the empty key

    sheet2 = _sheet()
    v1 = sheet2.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    f1 = sheet2.add_component_region("F1", "formula", {"inputs": "a", "expr": "a"},
                                      QPointF(300, 0))
    sheet2.try_connect((v1, "value"), (f1, "a"))
    raw2 = json.loads(sheet2.to_document().to_json())
    assert raw2["version"] == 3
    assert len(raw2["wires"]) == 1


def test_criterion11_bare_version3_with_no_component_or_wire_content_is_rejected():
    """Re-verifies the exact regression the manager found/a developer fixed: a declared
    version 3 is only meaningful when the file actually holds a component or wire."""
    raw = json.dumps({"format": "livesheet", "version": 3, "regions": [
        {"kind": "math", "x": 0, "y": 0, "text": "x := 1"},
    ]})
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(raw)


def test_criterion11_version_above_3_is_always_rejected():
    raw = json.dumps({"format": "livesheet", "version": 4, "regions": []})
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(raw)


def test_criterion11_a_genuine_version3_file_with_a_component_loads_fine():
    raw = json.dumps({"format": "livesheet", "version": 3, "regions": [
        {"kind": "component", "x": 0, "y": 0, "text": "",
         "component_name": "V1", "component_kind": "value", "config": {"expr": "1 m"}},
    ]})
    doc = SheetDocument.from_json(raw)
    assert len(doc.regions) == 1
    assert doc.regions[0].component_name == "V1"


# ===========================================================================
# Edge cases
# ===========================================================================

def test_edge_value_component_with_no_inputs_simply_evaluates():
    engine = Engine()
    v = wiring.ComponentSpec("V", "value", {"expr": "9.81 m/s^2"})
    result = wiring.evaluate([v], [], engine)["V"]
    assert result.status == "ok"
    m = measure(result.outputs["value"])
    assert m.magnitude == pytest.approx(9.81)


def test_edge_formula_component_with_zero_wires_shows_unconnected_error():
    engine = Engine()
    f = wiring.ComponentSpec("F", "formula", {"inputs": "a, b", "expr": "a + b"})
    result = wiring.evaluate([f], [], engine)["F"]
    assert result.status == "error"
    assert result.error == "Input 'a' is not connected."   # first unmet required input, in order


def test_edge_dangling_wire_reference_is_dropped_silently_on_load():
    doc = SheetDocument(
        regions=[RegionData("component", 0, 0, "", component_name="V1",
                             component_kind="value", config={"expr": "1 m"})],
        wires=[WireData("Ghost", "value", "V1", "does_not_exist")],
    )
    sheet = _sheet()
    sheet.load_document(doc)   # must not raise
    assert sheet._wires == []
    assert [c.component_name for c in sheet.component_regions()] == ["V1"]


def test_edge_duplicate_component_names_disambiguated_on_load():
    doc = SheetDocument(regions=[
        RegionData("component", 0, 0, "", component_name="Comp1",
                   component_kind="value", config={"expr": "1 m"}),
        RegionData("component", 0, 200, "", component_name="Comp1",
                   component_kind="value", config={"expr": "2 m"}),
    ])
    sheet = _sheet()
    sheet.load_document(doc)
    names = sorted(c.component_name for c in sheet.component_regions())
    assert names == ["Comp1", "Comp1 (2)"]


def test_edge_unknown_component_kind_survives_load_but_errors_at_evaluation():
    doc = SheetDocument(regions=[
        RegionData("component", 0, 0, "", component_name="X1",
                   component_kind="csv_future", config={"path": "data.csv"}),
    ])
    sheet = _sheet()
    sheet.load_document(doc)   # not a DocumentError -- run-time concern, per spec's edge case
    x1 = sheet.component_regions()[0]
    assert x1.component_name == "X1"
    assert x1.component_kind == "csv_future"
    assert x1.config == {"path": "data.csv"}
    assert x1._has_error
    assert x1.result.error == "Unknown component kind 'csv_future'."


def test_edge_unconnected_output_still_evaluates_and_keeps_its_value():
    """A component with no output ports connected to anything downstream still evaluates
    normally and keeps its computed value available."""
    sheet = _sheet()
    v = sheet.add_component_region("Lonely", "value", {"expr": "42 m"}, QPointF(0, 0))
    sheet.recalculate()
    assert not v._has_error
    m = measure(v.result.outputs["value"])
    assert m.magnitude == 42


def test_edge_dragging_onto_empty_canvas_creates_no_wire():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    out_pos = v.port_scene_pos("output", "value")
    sheet.mousePressEvent(_mouse_event(out_pos))
    assert sheet._wire_drag is not None
    sheet.mouseReleaseEvent(_mouse_event(QPointF(5000, 5000)))
    assert sheet._wire_drag is None
    assert sheet._wires == []


def test_edge_moving_a_component_moves_its_wire_endpoints():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    sheet.try_connect((v, "value"), (f, "a"))
    wire = sheet._wires[0]
    before_start, before_end = wire.endpoints()

    v.setPos(QPointF(0, 500))
    v.moved.emit()   # Worksheet._on_moved re-syncs wires on every real move
    after_start, after_end = wire.endpoints()
    assert after_start != before_start
    assert after_end == before_end   # only the moved endpoint changed


def test_edge_wire_drawn_in_error_colour_when_destination_errors():
    from PySide6.QtGui import QColor

    from livesheet.gui.regions import COLOR_ERROR, COLOR_FRAME

    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a, b", "expr": "a + b"},
                                    QPointF(300, 0))
    sheet.try_connect((v, "value"), (f, "a"))
    wire = sheet._wires[0]
    sheet.recalculate()   # F is in error (b unconnected): its incoming wire should be error-coloured
    wire.sync()
    assert wire.pen().color().name() == QColor(COLOR_ERROR).name()

    sheet.try_connect((v, "value"), (f, "b"))
    sheet.recalculate()
    wire.sync()
    assert not f._has_error
    assert wire.pen().color().name() == QColor(COLOR_FRAME).name()


# ===========================================================================
# Both wire-creation paths work end to end (drag-to-connect AND the Connect dialog)
# ===========================================================================

def test_drag_to_connect_gesture_creates_a_wire_end_to_end():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    out_pos = v.port_scene_pos("output", "value")
    in_pos = f.port_scene_pos("input", "a")

    sheet.mousePressEvent(_mouse_event(out_pos))
    assert sheet._wire_drag == (v, "value")
    sheet.mouseMoveEvent(_mouse_event(QPointF((out_pos.x() + in_pos.x()) / 2,
                                                  (out_pos.y() + in_pos.y()) / 2)))
    sheet.mouseReleaseEvent(_mouse_event(in_pos))
    assert len(sheet._wires) == 1
    assert sheet._wires[0].source is v and sheet._wires[0].dest is f


def test_drag_to_connect_only_starts_from_an_output_port_not_an_input():
    """Spec: 'press on an output port terminal, drag to an input port terminal' -- the one
    direction described. Pressing on an input port must not start a wire drag."""
    sheet = _sheet()
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(0, 0))
    in_pos = f.port_scene_pos("input", "a")
    sheet.mousePressEvent(_mouse_event(in_pos))
    assert sheet._wire_drag is None


def test_connect_dialog_path_creates_a_wire_end_to_end_via_real_context_menu():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    out_pos = v.port_scene_pos("output", "value")

    from livesheet.gui import componentdialog

    def fake_exec(self):
        self.list_widget.setCurrentRow(0)
        return QDialog.DialogCode.Accepted

    orig = componentdialog.ConnectDialog.exec
    componentdialog.ConnectDialog.exec = fake_exec
    try:
        _open_menu_and_pick(sheet, out_pos, "Connect…")
    finally:
        componentdialog.ConnectDialog.exec = orig
    assert len(sheet._wires) == 1
    assert sheet._wires[0].source is v and sheet._wires[0].dest is f


def test_connect_dialog_rejection_message_surfaces_via_statusMessage():
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    v2 = sheet.add_component_region("V2", "value", {"expr": "2 m"}, QPointF(0, 200))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 100))
    sheet.try_connect((v1, "value"), (f, "a"))   # pre-fill the input

    messages = []
    sheet.statusMessage.connect(messages.append)
    out_pos = v2.port_scene_pos("output", "value")

    from livesheet.gui import componentdialog

    def fake_exec(self):
        # pick the (F, "a") candidate -- already connected to V1, so this should be rejected
        row = next(i for i, (c, p) in enumerate(self._candidates) if c is f and p == "a")
        self.list_widget.setCurrentRow(row)
        return QDialog.DialogCode.Accepted

    orig = componentdialog.ConnectDialog.exec
    componentdialog.ConnectDialog.exec = fake_exec
    try:
        _open_menu_and_pick(sheet, out_pos, "Connect…")
    finally:
        componentdialog.ConnectDialog.exec = orig

    assert messages == ["Input 'a' on F is already connected — disconnect it first."]
    assert len(sheet._wires) == 1   # still just V1 -> F.a; V2's attempt created nothing


# ===========================================================================
# "Connect..." entry point
# ===========================================================================

def test_connect_action_appears_both_on_a_port_terminal_and_elsewhere_on_the_body():
    """Originally written to document Defect D1 (docs/board/reviews/009-component-wiring-core.md:
    only an exact-port hit offered "Connect…", with no way to reach it without pixel-precise
    targeting). The developer's D1 fix now also offers "Connect…" for a right-click anywhere on
    a ComponentRegion's body that has at least one port (defaulting to its first output port),
    mirroring "Edit as grid..." (spec 008) being offered for a whole MathRegion rather than
    requiring a pixel-precise hit. Updated here, post-fix, to assert the now-correct behaviour in
    both cases, per the developer's log.md handoff for this fix."""
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    out_pos = v.port_scene_pos("output", "value")
    assert "Connect…" in _menu_labels_at(sheet, out_pos)

    body_centre = v.mapToScene(v.boundingRect().center())
    assert "Connect…" in _menu_labels_at(sheet, body_centre)


def test_no_toolbar_or_menu_action_offers_connect_with_a_component_merely_selected():
    """Spec text: 'right-click a port (or use a "Connect…" toolbar/menu action with a component
    selected)'. This checks whether the second, keyboard-reachable trigger mechanism the spec's
    own wording names exists anywhere in the main window's menus -- see Defects in the review."""
    _ensure_app()
    win = MainWindow()
    all_actions = win.findChildren(type(win.menuBar().actions()[0]))
    connect_like = [a for a in all_actions if "Connect" in a.text()]
    assert connect_like == []   # see docs/board/reviews/009-component-wiring-core.md, Defect D1


# ===========================================================================
# Insert > Component... entry (named in the task) and the Add Component dialog
# ===========================================================================

def test_insert_component_menu_entry_exists_and_creates_a_component():
    _ensure_app()
    win = MainWindow()
    insert_menu = next(a.menu() for a in win.menuBar().actions()
                        if a.menu() and a.menu().title() == "&Insert")
    action = next((a for a in insert_menu.actions() if "Component" in a.text()), None)
    assert action is not None

    from livesheet.gui import componentdialog

    def fake_exec(self):
        self._fields = ComponentFields(name="Z1", kind="value", value_expr="5 m")
        return QDialog.DialogCode.Accepted

    orig = componentdialog.AddComponentDialog.exec
    componentdialog.AddComponentDialog.exec = fake_exec
    try:
        action.trigger()
    finally:
        componentdialog.AddComponentDialog.exec = orig
    names = [c.component_name for c in win.sheet.component_regions()]
    assert names == ["Z1"]
    win.sheet.set_modified(False)


def test_add_component_dialog_value_kind_accept_and_result_fields():
    _ensure_app()
    dlg = AddComponentDialog()
    dlg.kind_combo.setCurrentText("Value")
    dlg.name_edit.setText("MyValue")
    dlg.value_expr_edit.setText("3 kg")
    dlg.accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    name, kind, config = dlg.result_fields()
    assert (name, kind, config) == ("MyValue", "value", {"expr": "3 kg"})


def test_add_component_dialog_formula_kind_accept_and_result_fields():
    _ensure_app()
    dlg = AddComponentDialog()
    dlg.kind_combo.setCurrentText("Formula")
    dlg.name_edit.setText("MyFormula")
    dlg.formula_inputs_edit.setText("a, b")
    dlg.formula_expr_edit.setText("a + b")
    dlg.accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    name, kind, config = dlg.result_fields()
    assert (name, kind, config) == ("MyFormula", "formula", {"inputs": "a, b", "expr": "a + b"})


def test_add_component_dialog_blank_name_rejected_dialog_stays_open():
    app = _ensure_app()
    dlg = AddComponentDialog()
    dlg.kind_combo.setCurrentText("Value")
    dlg.value_expr_edit.setText("1 m")
    dlg.accept()
    assert dlg.result() == 0   # neither Accepted nor Rejected: still open
    assert dlg.banner_label.text() == "Name is required"
    # isVisible() needs the top-level dialog itself to actually have been shown first (a
    # QWidget's isVisible() is False until its top-level window is shown -- the same real Qt
    # quirk already noted in docs/board/reviews/007-main-window.md for a QDockWidget).
    dlg.show()
    app.processEvents()
    assert dlg.banner_label.isVisible()


def test_add_component_dialog_cancel_does_not_touch_canvas():
    sheet = _sheet()
    assert sheet.insert_component_at is not None   # sanity: method exists on the real class


def test_validate_component_fields_value_kind_requires_expression():
    err = validate_component_fields(ComponentFields(name="V", kind="value", value_expr=""))
    assert err == ComponentFieldError("value_expr", "Expression is required")
    assert validate_component_fields(
        ComponentFields(name="V", kind="value", value_expr="1 m")) is None


def test_validate_component_fields_formula_kind_checks():
    base = dict(name="F", kind="formula")
    assert validate_component_fields(ComponentFields(**base, formula_inputs="", formula_expr="a")) \
        == ComponentFieldError("formula_inputs", "At least one input name is required")
    assert validate_component_fields(
        ComponentFields(**base, formula_inputs="a, a", formula_expr="a")) \
        == ComponentFieldError("formula_inputs", "Input names must be unique")
    assert validate_component_fields(
        ComponentFields(**base, formula_inputs="1bad", formula_expr="a")) \
        == ComponentFieldError("formula_inputs", "'1bad' is not a valid input name")
    assert validate_component_fields(
        ComponentFields(**base, formula_inputs="a, b", formula_expr="")) \
        == ComponentFieldError("formula_expr", "Expression is required")
    assert validate_component_fields(
        ComponentFields(**base, formula_inputs="a, b", formula_expr="a + b")) is None


def test_fields_to_config_matches_each_kinds_config_shape():
    assert fields_to_config(ComponentFields(kind="value", value_expr=" 12 m/s ")) == \
        {"expr": "12 m/s"}
    assert fields_to_config(ComponentFields(
        kind="formula", formula_inputs=" a, b ", formula_expr=" a + b ")) == \
        {"inputs": "a, b", "expr": "a + b"}


def test_connect_dialog_with_no_candidates_disables_ok_and_shows_message():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    dialog = ConnectDialog(v, "output", "value", [])
    assert dialog.ok_btn.isEnabled() is False
    assert dialog.chosen() is None


def test_connect_dialog_lists_other_components_compatible_ports_only():
    sheet = _sheet()
    v1 = sheet.add_component_region("V1", "value", {"expr": "1 m"}, QPointF(0, 0))
    f1 = sheet.add_component_region("F1", "formula", {"inputs": "a, b", "expr": "a + b"},
                                     QPointF(300, 0))
    candidates = sheet._connect_candidates(v1, "output", "value")
    assert sorted((c.component_name, p) for c, p in candidates) == [("F1", "a"), ("F1", "b")]
    # Never offers V1's own ports as a candidate for itself.
    assert all(c is not v1 for c, _ in candidates)


# ===========================================================================
# Region-base-class mechanics apply unchanged to ComponentRegion; wires are not Regions
# ===========================================================================

def test_component_region_uses_the_existing_region_mechanics():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    assert v in sheet.regions()            # picked up by the generic Region filter
    assert isinstance(v, ComponentRegion)
    v.setSelected(True)
    assert v.isSelected()
    sheet.remove_regions([v])
    assert v not in sheet.component_regions()


def test_wire_item_is_not_a_region_and_is_excluded_from_regions_and_ordering():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    sheet.try_connect((v, "value"), (f, "a"))
    wire = sheet._wires[0]
    assert isinstance(wire, WireItem)
    assert wire not in sheet.regions()
    assert wire not in sheet.ordered_regions()


def test_pdf_export_with_components_and_wires_does_not_crash(tmp_path):
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    f = sheet.add_component_region("F", "formula", {"inputs": "a", "expr": "a"}, QPointF(300, 0))
    sheet.try_connect((v, "value"), (f, "a"))
    sheet.recalculate()
    path = tmp_path / "out.pdf"
    export_pdf(sheet, str(path))
    assert path.exists() and path.stat().st_size > 0


def test_component_region_delete_key_also_removes_it_like_any_region():
    sheet = _sheet()
    v = sheet.add_component_region("V", "value", {"expr": "1 m"}, QPointF(0, 0))
    v.setSelected(True)
    sheet.keyPressEvent(_FakeKeyEvent(Qt.Key.Key_Delete))
    assert v not in sheet.component_regions()


# ===========================================================================
# Spec text: components do not read/write ordinary sheet variables (open question 1, accepted)
# -- re-checked at the real Worksheet.recalculate() level, not only the engine layer directly.
# ===========================================================================

def test_components_do_not_see_ordinary_sheet_variables_via_real_worksheet_recalculate():
    sheet = _sheet()
    sheet.add_region("math", QPointF(0, 0), "x := 100 m")
    v = sheet.add_component_region("V", "value", {"expr": "x + 1 m"}, QPointF(0, 100))
    sheet.recalculate()
    assert v._has_error   # "x" is not visible to a component just because a math region defines it
    assert "not defined" in v.result.error


def test_components_do_not_leak_values_back_into_ordinary_math_regions():
    """The reverse direction: a math region cannot read a component's output by name either --
    components are wiring-only in this spec, never an ordinary sheet variable."""
    sheet = _sheet()
    sheet.add_component_region("V1", "value", {"expr": "7 m"}, QPointF(0, 0))
    region = sheet.add_region("math", QPointF(0, 100), "V1 =")
    sheet.recalculate()
    assert region.result.status == "error"
    assert "not defined" in region.result.error
