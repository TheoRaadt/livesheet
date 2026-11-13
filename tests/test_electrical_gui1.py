"""Spec 034 GUI-1: Electrical tab sub-groups and the 36 function insertion buttons."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import inspect
import re

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from livesheet.engine import Engine
from livesheet.engine.electrical import ELEC_BUILTINS
from livesheet.gui.sidepanel import MATH_TOKENS, TAB_CATEGORIES, TAB_ORDER, SidePanel

_app = QApplication.instance() or QApplication([])

NEW_CATS = ("AC Power", "Three-Phase", "Transformers", "Resistor Networks",
            "Phasors & Impedance", "Transients & Resonance", "Filters")
COUNTS = [6, 4, 3, 4, 9, 7, 3]
ROWS = [t for c in NEW_CATS for t in MATH_TOKENS if t[0] == c]


def _panel(sink=None) -> SidePanel:
    return SidePanel((sink if sink is not None else []).append)


def _call_parts(token: str) -> tuple[str, list[str]]:
    m = re.fullmatch(r"(\w+)\((.*)\)", token)
    assert m, token
    return m.group(1), [a.strip() for a in m.group(2).split(",")]


def test_structure_and_counts() -> None:
    assert TAB_CATEGORIES["Electrical"] == ("DC Circuits", "Power") + NEW_CATS
    assert [len([t for t in ROWS if t[0] == c]) for c in NEW_CATS] == COUNTS
    assert len(ROWS) == 36 == len(ELEC_BUILTINS)
    panel = _panel()
    w = panel.tabs.widget(TAB_ORDER.index("Electrical"))
    assert [lab.text() for lab in w.findChildren(QLabel)] == list(
        TAB_CATEGORIES["Electrical"])
    assert len(w.findChildren(QPushButton)) == 11 + 36


def test_tab_order_unchanged() -> None:
    assert TAB_ORDER.index("Mechanical") + 1 == TAB_ORDER.index("Electrical")
    assert TAB_ORDER.index("Electrical") + 1 == TAB_ORDER.index("Chemical")


def test_regression_dc_and_power_unchanged() -> None:
    base = [t[1] for t in MATH_TOKENS if t[0] in ("DC Circuits", "Power")]
    assert base[0] == "Vs := Is * R" and base[-1] == "E := P * t" and len(base) == 11


@pytest.mark.parametrize("row", ROWS, ids=[r[1] for r in ROWS])
def test_button_inserts_exact_token_and_has_tooltip(row) -> None:
    sink: list[str] = []
    panel = _panel(sink)
    btn = panel.symbol_buttons[row[1]]
    assert btn.toolTip() == row[3] and row[3].isascii()
    btn.click()
    assert sink == [row[2]]


def test_gui3_examples() -> None:
    sink: list[str] = []
    panel = _panel(sink)
    panel.symbol_buttons["average power"].click()
    panel.symbol_buttons["phasor"].click()
    assert sink == ["average_power(Vrms, Irms, phi)", "phasor(mag, phi)"]


def test_every_button_maps_to_registry_function_once() -> None:
    names = []
    for _c, _l, token, _t in ROWS:
        name, args = _call_parts(token)
        assert name in ELEC_BUILTINS, name
        n_params = len(inspect.signature(ELEC_BUILTINS[name]).parameters)
        assert len(args) == n_params, (token, n_params)
        names.append(name)
    assert sorted(names) == sorted(ELEC_BUILTINS)


def test_labels_unique_and_no_vendor_words() -> None:
    labels = [t[1] for t in MATH_TOKENS]
    assert len(labels) == len(set(labels))
    for _c, label, token, tip in ROWS:
        low = (label + token + tip).lower()
        assert not any(w in low for w in ("mathcad", "ptc", "maple", "mathematica", "matlab"))


def test_placeholders_avoid_bare_unit_letters() -> None:
    bad = {"V", "A", "F", "H", "C", "T", "W", "S", "L", "e"}
    for _c, _l, token, _t in ROWS:
        assert not (set(_call_parts(token)[1]) & bad), token


# Plausible values for each placeholder, so the token evaluates to a real number.
_VALUES = {
    "Vpk": "325 V", "Vrms": "230 V", "Irms": "5 A", "phi": "0.5", "Vph": "230 V",
    "Vline": "400 V", "Iph": "5 A", "VL": "400 V", "IL": "5 A", "Vp": "230 V", "Ip": "2 A",
    "Np": "100", "Ns": "50", "Zs": "8 ohm", "Vin": "12 V", "R1": "100 ohm", "R2": "200 ohm",
    "Itot": "2 A", "R": "1000 ohm", "Lind": "10 mH", "Ccap": "1 uF", "f_hz": "50 Hz",
    "mag": "10 V", "z": "3 ohm", "Vs_step": "12 V", "t_s": "2 ms",
}
_VECTOR = {"R": "[100 ohm, 200 ohm]", "z": "[3 ohm, 4 ohm]"}
_VECTOR_FUNCS = {"resistors_series", "resistors_parallel", "impedance_series",
                 "impedance_parallel"}


def _filled(token: str) -> str:
    name, args = _call_parts(token)
    vals = [(_VECTOR[a] if name in _VECTOR_FUNCS else _VALUES[a]) for a in args]
    if name in ("phasor_magnitude", "phasor_angle"):
        vals = ["3 V + 4 V*I"]
    return f"{name}({', '.join(vals)})"


@pytest.mark.parametrize("row", ROWS, ids=[r[1] for r in ROWS])
def test_filled_token_evaluates(row) -> None:
    src = f"x := {_filled(row[2])}"
    res = Engine().evaluate([(0, src)])[0]
    assert res.status != "error", (src, res.error)


@pytest.mark.parametrize("row", ROWS, ids=[r[1] for r in ROWS])
def test_unfilled_token_parses_and_reports_undefined(row) -> None:
    res = Engine().evaluate([(0, row[2] + " =")])[0]
    assert res.status == "error"
    assert "not defined" in res.error, (row[2], res.error)
