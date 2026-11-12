"""Spec 030 independent review tests (GUI)."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from livesheet.engine import dataio
from test_completion_gui_024 import app, new_region, popup, press, sheet, typ, K  # noqa: F401


def ds(name="run1"):
    return dataio.read_table_text("t [s],F [N]\n0,1.0\n1,3.0", name=name)


def test_popup_lists_with_tags(sheet):
    sheet.add_dataset(ds())
    r = new_region(sheet)
    typ(r, "run1_")
    ok, p = popup(r)
    assert ok and p.candidates() == ["run1_F", "run1_t"]
    press(r, K.Key_Escape)


def test_accept_inserts_no_paren_enter(sheet):
    sheet.add_dataset(ds())
    r = new_region(sheet)
    typ(r, "run1_t")
    # exact name typed: no popup
    assert not popup(r)[0]
    r2 = new_region(sheet, y=140)
    typ(r2, "run1_F"[:5])
    press(r2, K.Key_Tab)
    assert r2.source == "run1_F" and "(" not in r2.source


def test_remove_then_rename_other_flow(sheet):
    sheet.add_dataset(ds())
    sheet.add_dataset(ds("other"))
    sheet.remove_dataset("run1")
    r = new_region(sheet)
    typ(r, "ru")
    assert not popup(r)[0]
    r2 = new_region(sheet, y=140)
    typ(r2, "ot")
    assert popup(r2)[1].candidates() == ["other_F", "other_t"]


def test_text_region_no_popup(sheet):
    sheet.add_dataset(ds())
    tr = sheet.add_region("text", QPointF(40, 300), "")
    tr.start_editing()
    for ch in "ru":
        press(tr, K.Key_R if ch == "r" else K.Key_U, ch)
    assert getattr(tr, "completion_popup", lambda: None)() is None


def test_save_reload_names_offered(sheet, tmp_path, app):
    from livesheet.document import SheetDocument
    from livesheet.gui.worksheet import Worksheet, WorksheetView
    sheet.add_dataset(ds())
    path = tmp_path / "s.lsheet"
    sheet.to_document().save(path)
    s2 = Worksheet()
    v2 = WorksheetView(s2)
    v2.show()
    try:
        s2.load_document(SheetDocument.load(path))
        assert [d.name for d in s2.datasets] == ["run1"]
        r = new_region(s2)
        typ(r, "ru")
        assert popup(r)[1].candidates() == ["run1_F", "run1_t"]
    finally:
        s2.set_modified(False)
        v2.close()


def test_order_hint_displayed_and_cleared_by_move(sheet):
    a = sheet.add_region("math", QPointF(40, 40), "y := 2*x =")
    b = sheet.add_region("math", QPointF(40, 140), "x := 4")
    sheet.recalculate()
    assert "defined later: x" in a.result.error
    sheet.move_regions([(b, b.pos(), QPointF(40, -60))])
    sheet.recalculate()
    assert a.result.status == "ok"


def test_error_tooltip_has_full_text(sheet):
    a = sheet.add_region("math", QPointF(40, 40), "y := 2*x =")
    sheet.add_region("math", QPointF(40, 140), "x := 4")
    sheet.recalculate()
    tips = [a.toolTip()] + [getattr(w, "toolTip", lambda: "")() for w in a.childItems()
                            if hasattr(w, "toolTip")]
    assert any("defined later: x" in t for t in tips)
