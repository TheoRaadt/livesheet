"""Spec 030 GUI tests: dataset names in the popup, and the order hint in the region error."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from livesheet.engine import dataio
from test_completion_gui_024 import app, new_region, popup, press, sheet, typ, K  # noqa: F401


def make(name="run1"):
    return dataio.read_table_text("t [s],F [N]\n0,1.0\n1,3.0", name=name)


def test_a11_a12(sheet):
    sheet.add_dataset(make())
    r = new_region(sheet)
    typ(r, "ru")
    ok, p = popup(r)
    assert ok and p.candidates() == ["run1_F", "run1_t"]
    press(r, K.Key_Tab)
    assert r.source == "run1_F" and r.editing
    sheet.remove_dataset("run1")
    r2 = new_region(sheet, y=140)
    typ(r2, "ru")
    assert not popup(r2)[0]
    sheet.add_dataset(make())
    sheet.rename_dataset("run1", "trial")
    r3 = new_region(sheet, y=240)
    typ(r3, "ru")
    assert not popup(r3)[0]
    r4 = new_region(sheet, y=340)
    typ(r4, "tri")
    assert popup(r4)[1].candidates() == ["trial_F", "trial_t"]


def test_b15_hint_in_error(sheet):
    a = sheet.add_region("math", QPointF(40, 40), "y := 2*x =")
    b = sheet.add_region("math", QPointF(40, 140), "x := 4")
    sheet.recalculate()
    assert "defined later: x" in a.result.error
    sheet.move_regions([(b, b.pos(), QPointF(40, -60))])
    sheet.recalculate()
    assert a.result.status == "ok"
