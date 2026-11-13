"""Independent black-box review of spec 034 GUI-1 (Electrical tab, 36 insertion buttons).

Written from docs/board/specs/034-elec-eng-library-overview.md (GUI-1..GUI-6) only. Expected
numbers are recomputed here with plain ``math``/``cmath``, not taken from the implementation.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cmath
import math
import re

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea

from livesheet.engine import Engine
from livesheet.engine.evaluator import _builtins
from livesheet.engine.units import UNITS, is_unit_name
from livesheet.gui.main_window import MainWindow
from livesheet.gui.regions import MathRegion
from livesheet.gui.sidepanel import MATH_TOKENS, TAB_CATEGORIES, TAB_ORDER, SidePanel

_app = QApplication.instance() or QApplication([])

# (group, label, inserted text) typed in from GUI-4, in spec order.
SPEC = [
    ("AC Power", "rms from peak", "rms_from_peak(Vpk)"),
    ("AC Power", "peak from RMS", "peak_from_rms(Vrms)"),
    ("AC Power", "average power", "average_power(Vrms, Irms, phi)"),
    ("AC Power", "apparent power", "apparent_power(Vrms, Irms)"),
    ("AC Power", "reactive power", "reactive_power(Vrms, Irms, phi)"),
    ("AC Power", "power factor", "power_factor(phi)"),
    ("Three-Phase", "wye line voltage", "wye_line_voltage(Vph)"),
    ("Three-Phase", "wye phase voltage", "wye_phase_voltage(Vline)"),
    ("Three-Phase", "delta line current", "delta_line_current(Iph)"),
    ("Three-Phase", "three-phase power", "three_phase_power(VL, IL, phi)"),
    ("Transformers", "secondary voltage", "transformer_secondary_voltage(Vp, Np, Ns)"),
    ("Transformers", "secondary current", "transformer_secondary_current(Ip, Np, Ns)"),
    ("Transformers", "reflected impedance", "reflected_impedance(Zs, Np, Ns)"),
    ("Resistor Networks", "series resistance", "resistors_series(R)"),
    ("Resistor Networks", "parallel resistance", "resistors_parallel(R)"),
    ("Resistor Networks", "voltage divider", "voltage_divider(Vin, R1, R2)"),
    ("Resistor Networks", "current divider", "current_divider(Itot, R1, R2)"),
    ("Phasors & Impedance", "phasor", "phasor(mag, phi)"),
    ("Phasors & Impedance", "phasor magnitude", "phasor_magnitude(z)"),
    ("Phasors & Impedance", "phasor angle", "phasor_angle(z)"),
    ("Phasors & Impedance", "resistor impedance", "impedance_resistor(R)"),
    ("Phasors & Impedance", "inductor impedance", "impedance_inductor(f_hz, Lind)"),
    ("Phasors & Impedance", "capacitor impedance", "impedance_capacitor(f_hz, Ccap)"),
    ("Phasors & Impedance", "series impedance", "impedance_series(z)"),
    ("Phasors & Impedance", "parallel impedance", "impedance_parallel(z)"),
    ("Phasors & Impedance", "angular frequency", "angular_frequency(f_hz)"),
    ("Transients & Resonance", "RC time constant", "rc_time_constant(R, Ccap)"),
    ("Transients & Resonance", "RL time constant", "rl_time_constant(Lind, R)"),
    ("Transients & Resonance", "RC charge voltage", "rc_charge_voltage(Vs_step, t_s, R, Ccap)"),
    ("Transients & Resonance", "RL current rise", "rl_current_rise(Vs_step, t_s, R, Lind)"),
    ("Transients & Resonance", "resonant frequency", "resonant_frequency(Lind, Ccap)"),
    ("Transients & Resonance", "series RLC Q", "series_rlc_quality_factor(R, Lind, Ccap)"),
    ("Transients & Resonance", "series RLC bandwidth", "series_rlc_bandwidth(R, Lind)"),
    ("Filters", "RC low-pass cutoff", "rc_lowpass_cutoff(R, Ccap)"),
    ("Filters", "RC low-pass gain", "rc_lowpass_gain(f_hz, R, Ccap)"),
    ("Filters", "RC high-pass gain", "rc_highpass_gain(f_hz, R, Ccap)"),
]
GROUPS = ["AC Power", "Three-Phase", "Transformers", "Resistor Networks",
          "Phasors & Impedance", "Transients & Resonance", "Filters"]
GROUP_COUNTS = [6, 4, 3, 4, 9, 7, 3]
PLACEHOLDERS = ["Vpk", "Vrms", "Irms", "phi", "Vph", "Vline", "Iph", "VL", "IL", "Vp", "Ip", "Np",
                "Ns", "Zs", "Vin", "R1", "R2", "Itot", "R", "Lind", "Ccap", "f_hz", "mag", "z",
                "Vs_step", "t_s"]

DC_POWER = [t for t in MATH_TOKENS if t[0] in ("DC Circuits", "Power")]


def _by_label():
    return {t[1]: t for t in MATH_TOKENS}


def _new_rows():
    return [t for g in GROUPS for t in MATH_TOKENS if t[0] == g]


# ---------------------------------------------------------------- structure (GUI-1, GUI-2, GUI-6)

def test_spec_table_is_36_with_expected_counts():
    assert len(SPEC) == 36
    assert [sum(1 for s in SPEC if s[0] == g) for g in GROUPS] == GROUP_COUNTS


def test_tab_categories_and_order_unchanged():
    assert TAB_CATEGORIES["Electrical"] == ("DC Circuits", "Power", *GROUPS)
    assert list(TAB_ORDER) == ["Elements", "Algebra", "Calculus", "Statistics", "Optimization",
                         "Mechanical", "Electrical", "Chemical", "Outline", "Data"]


def test_widget_headers_buttons_in_spec_order():
    panel = SidePanel(lambda _t: None)
    page = panel.tabs.widget(TAB_ORDER.index("Electrical"))
    flow = page.widget() if isinstance(page, QScrollArea) else page
    seq: list[tuple[str, str]] = []
    for child in flow.children():
        if isinstance(child, QLabel):
            seq.append(("H", child.text()))
        elif isinstance(child, QPushButton):
            seq.append(("B", child.text()))
    headers = [t for k, t in seq if k == "H"]
    assert headers == ["DC Circuits", "Power", *GROUPS]
    # buttons grouped under their header, in spec order, labels exact
    cur, got = None, {}
    for k, t in seq:
        if k == "H":
            cur = t
            got[cur] = []
        else:
            got[cur].append(t)
    for g in GROUPS:
        assert got[g] == [s[1] for s in SPEC if s[0] == g], g
    assert len(got["DC Circuits"]) == 7 and len(got["Power"]) == 4
    assert sum(len(v) for v in got.values()) == 47


def test_tokens_in_math_tokens_match_spec_exactly_and_in_order():
    rows = _new_rows()
    assert [(r[0], r[1], r[2]) for r in rows] == SPEC


def test_labels_unique_across_all_tabs():
    labels = [t[1] for t in MATH_TOKENS]
    assert len(labels) == len(set(labels))


def test_dc_and_power_buttons_unchanged_gui6():
    assert len(DC_POWER) == 11
    assert [t[1] for t in DC_POWER] == [t[2] for t in DC_POWER]       # label == text (spec 020)
    assert DC_POWER[0][2] == "Vs := Is * R" and DC_POWER[6][0] == "DC Circuits"
    assert DC_POWER[7][2] == "P := Vs * Is" and DC_POWER[-1][2] == "E := P * t"
    assert [t[0] for t in DC_POWER] == ["DC Circuits"] * 7 + ["Power"] * 4


def test_other_tabs_unaffected():
    assert TAB_CATEGORIES["Mechanical"] == ("Statics", "Strength of Materials")
    assert [sum(1 for t in MATH_TOKENS if t[0] == c) for c in TAB_CATEGORIES["Mechanical"]] == [6, 9]
    assert len(TAB_CATEGORIES["Chemical"]) == 5
    assert sum(sum(1 for t in MATH_TOKENS if t[0] == c) for c in TAB_CATEGORIES["Chemical"]) == 21
    panel = SidePanel(lambda _t: None)
    new_labels = {s[1] for s in SPEC}
    for name in ("Mechanical", "Chemical", "Elements", "Algebra", "Calculus", "Statistics",
                 "Optimization"):
        page = panel.tabs.widget(TAB_ORDER.index(name))
        flow = page.widget() if isinstance(page, QScrollArea) else page
        texts = {b.text() for b in flow.findChildren(QPushButton)}
        assert not (texts & new_labels), name
    mech = panel.tabs.widget(TAB_ORDER.index("Mechanical")).widget().findChildren(QPushButton)
    assert len(mech) == 15


# ---------------------------------------------------------------- tooltips (GUI-4, SI rule)

IMPERIAL = re.compile(r"\b(inch|in\.|ft|feet|lb|lbf|psi|ksi|mil|btu|degf|deg|rpm|hp)\b", re.I)


@pytest.mark.parametrize("row", SPEC, ids=[s[1] for s in SPEC])
def test_tooltip_present_ascii_si_only(row):
    panel = SidePanel(lambda _t: None)
    tip = panel.symbol_buttons[row[1]].toolTip()
    assert tip.strip() and tip.isascii()
    assert not IMPERIAL.search(tip), tip
    for bad in ("mathcad", "maple", "mathematica", "matlab", "ptc"):
        assert bad not in tip.lower()


TIP_MUST = {
    "average power": ("W", "rad"), "apparent power": ("VA",), "reactive power": ("var", "lagging"),
    "power factor": ("dimensionless",), "wye line voltage": ("V",),
    "three-phase power": ("alanced", "W"), "secondary voltage": ("turn",),
    "secondary current": ("turn",), "reflected impedance": ("turn", "ohm"),
    "phasor angle": ("rad",), "inductor impedance": ("Hz", "H"),
    "capacitor impedance": ("Hz", "F"), "angular frequency": ("rad/s",),
    "resonant frequency": ("Hz",), "series RLC bandwidth": ("Hz",),
    "RC low-pass cutoff": ("Hz",), "series RLC Q": ("dimensionless",),
    "RC low-pass gain": ("dimensionless",), "RC charge voltage": ("s", "V"),
    "series resistance": ("ohm",), "voltage divider": ("V", "ohm"),
    "current divider": ("A", "ohm"),
}


@pytest.mark.parametrize("label", list(TIP_MUST))
def test_tooltip_states_units_named_in_gui4(label):
    tip = _by_label()[label][3]
    for needle in TIP_MUST[label]:
        assert needle in tip, (label, needle, tip)


# ---------------------------------------------------------------- placeholders (GUI-4 last para)

@pytest.mark.parametrize("name", PLACEHOLDERS)
def test_placeholder_is_not_a_unit_or_engine_special(name):
    assert name not in UNITS and not is_unit_name(name), name
    assert name not in _builtins(), name
    assert name not in {"E", "I", "L", "g", "e", "pi", "oo", "inf"}
    res = Engine().evaluate([(0, f"{name} =")])[0]
    assert res.status == "error" and "not defined" in res.error, (name, res.output, res.error)


def test_placeholder_set_is_exactly_spec_list_and_used_in_tokens():
    used = set()
    for _g, _l, tok in SPEC:
        used |= {a.strip() for a in re.fullmatch(r"\w+\((.*)\)", tok).group(1).split(",")}
    assert used == set(PLACEHOLDERS)


@pytest.mark.parametrize("row", SPEC, ids=[s[1] for s in SPEC])
def test_unfilled_token_reports_undefined_not_silent_value(row):
    res = Engine().evaluate([(0, row[2] + " =")])[0]
    assert res.status == "error" and "not defined" in res.error, res.output


# ---------------------------------------------------------------- insert + fill + evaluate

S3 = math.sqrt(3)
PHI = 0.5
# label -> (substitutions, display unit, expected value as float/complex)
_TWO_PI = 2 * math.pi
CASES = {
    "rms from peak": ({"Vpk": "325 V"}, "V", 325 / math.sqrt(2)),
    "peak from RMS": ({"Vrms": "230 V"}, "V", 230 * math.sqrt(2)),
    "average power": ({"Vrms": "230 V", "Irms": "5 A", "phi": "0.5"}, "W", 230 * 5 * math.cos(PHI)),
    "apparent power": ({"Vrms": "230 V", "Irms": "5 A"}, "VA", 1150.0),
    "reactive power": ({"Vrms": "230 V", "Irms": "5 A", "phi": "0.5"}, "var",
                       1150 * math.sin(PHI)),
    "power factor": ({"phi": "0.5"}, None, math.cos(PHI)),
    "wye line voltage": ({"Vph": "230 V"}, "V", 230 * S3),
    "wye phase voltage": ({"Vline": "400 V"}, "V", 400 / S3),
    "delta line current": ({"Iph": "5 A"}, "A", 5 * S3),
    "three-phase power": ({"VL": "400 V", "IL": "5 A", "phi": "0.5"}, "W",
                          S3 * 400 * 5 * math.cos(PHI)),
    "secondary voltage": ({"Vp": "230 V", "Np": "100", "Ns": "50"}, "V", 115.0),
    "secondary current": ({"Ip": "2 A", "Np": "100", "Ns": "50"}, "A", 4.0),
    "reflected impedance": ({"Zs": "8 ohm", "Np": "100", "Ns": "50"}, "ohm", 32.0),
    "series resistance": ({"R": "[100 ohm; 200 ohm; 300 ohm]"}, "ohm", 600.0),
    "parallel resistance": ({"R": "[100 ohm; 200 ohm; 300 ohm]"}, "ohm",
                            1 / (1 / 100 + 1 / 200 + 1 / 300)),
    "voltage divider": ({"Vin": "12 V", "R1": "1 kohm", "R2": "3000 ohm"}, "V", 9.0),
    "current divider": ({"Itot": "10 mA", "R1": "1 kohm", "R2": "1 kohm"}, "mA", 5.0),
    "phasor": ({"mag": "10 V", "phi": "0.5"}, "V", cmath.rect(10, 0.5)),
    "phasor magnitude": ({"z": "(3 V + 4 V*I)"}, "V", 5.0),
    "phasor angle": ({"z": "(3 V + 4 V*I)"}, None, math.atan2(4, 3)),
    "resistor impedance": ({"R": "2.2 kohm"}, "ohm", 2200.0),
    "inductor impedance": ({"f_hz": "50 Hz", "Lind": "10 mH"}, "ohm",
                           complex(0, _TWO_PI * 50 * 0.01)),
    "capacitor impedance": ({"f_hz": "50 Hz", "Ccap": "1 uF"}, "ohm",
                            complex(0, -1 / (_TWO_PI * 50 * 1e-6))),
    "series impedance": ({"z": "[3 ohm; 4 ohm; 5 ohm]"}, "ohm", 12.0),
    "parallel impedance": ({"z": "[3 ohm; 6 ohm]"}, "ohm", 2.0),
    "angular frequency": ({"f_hz": "50 Hz"}, None, _TWO_PI * 50),
    "RC time constant": ({"R": "1 kohm", "Ccap": "10 uF"}, "s", 0.01),
    "RL time constant": ({"Lind": "0.5 H", "R": "10 ohm"}, "s", 0.05),
    "RC charge voltage": ({"Vs_step": "12 V", "t_s": "0.01 s", "R": "1 kohm", "Ccap": "10 uF"}, "V",
                          12 * (1 - math.exp(-1))),
    "RL current rise": ({"Vs_step": "12 V", "t_s": "0.05 s", "R": "10 ohm", "Lind": "0.5 H"}, "A",
                        1.2 * (1 - math.exp(-1))),
    "resonant frequency": ({"Lind": "0.01 H", "Ccap": "10 uF"}, "Hz",
                           1 / (_TWO_PI * math.sqrt(0.01 * 10e-6))),
    "series RLC Q": ({"R": "10 ohm", "Lind": "0.01 H", "Ccap": "10 uF"}, None,
                     math.sqrt(0.01 / 10e-6) / 10),
    "series RLC bandwidth": ({"R": "10 ohm", "Lind": "0.01 H"}, "Hz", 10 / (_TWO_PI * 0.01)),
    "RC low-pass cutoff": ({"R": "1 kohm", "Ccap": "1 uF"}, "Hz", 1 / (_TWO_PI * 1e-3)),
    "RC low-pass gain": ({"f_hz": "1591.549 Hz", "R": "1 kohm", "Ccap": "1 uF"}, None,
                         1 / math.sqrt(1 + (_TWO_PI * 1591.549 * 1e-3) ** 2)),
    "RC high-pass gain": ({"f_hz": "159.1549 Hz", "R": "1 kohm", "Ccap": "1 uF"}, None,
                          (_TWO_PI * 159.1549 * 1e-3) / math.sqrt(1 + (_TWO_PI * 159.1549 * 1e-3) ** 2)),
}


def test_every_button_has_a_case():
    assert set(CASES) == {s[1] for s in SPEC}


def _fill(text: str, subs: dict[str, str]) -> str:
    # whole-identifier replacement, longest names first (R vs R1/R2, Vp vs Vpk, ...)
    def rep(m: re.Match) -> str:
        return subs.get(m.group(0), m.group(0))
    return re.sub(r"[A-Za-z_]\w*(?=\s*[,)])", lambda m: rep(m), text)


_NUM = re.compile(r"^=\s*(.+?)(?:\s+([^\s\d+\-.][^\s]*))?$")


def _parse(output: str) -> complex:
    body = output.strip()
    assert body.startswith("="), body
    body = body[1:].strip()
    # split off a trailing unit token (anything after the last digit/i)
    m = re.match(r"^([0-9eE+\-.\s]*?i?)\s*(?:[A-Za-zΩ°µ][^\s]*|s⁻¹)?$", body)
    assert m, body
    num = m.group(1).replace(" ", "").replace("i", "j")
    return complex(num)


@pytest.mark.parametrize("label", [s[1] for s in SPEC])
def test_button_inserts_into_real_math_region_and_evaluates(label):
    subs, unit, expected = CASES[label]
    win = MainWindow()
    try:
        win.sheet.set_modified(False)
        win.side_panel.tabs.setCurrentIndex(TAB_ORDER.index("Electrical"))
        win.side_panel.symbol_buttons[label].click()
        region = win.sheet.editing_region()
        assert isinstance(region, MathRegion)
        token = next(s[2] for s in SPEC if s[1] == label)
        assert region.source.strip() == token                      # GUI-3: exact text
        filled = _fill(token, subs) + (f" = {unit}" if unit else " =")
        res = Engine().evaluate([(0, filled)])[0]
        assert res.status == "ok", (filled, res.error)
        got = _parse(res.output)
        assert got == pytest.approx(expected, rel=2e-5, abs=1e-9), (filled, res.output)
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_filled_region_recalculates_inside_real_worksheet():
    win = MainWindow()
    try:
        win.side_panel.symbol_buttons["voltage divider"].click()
        region = win.sheet.editing_region()
        region.editor.setPlainText("voltage_divider(12 V, 1 kohm, 3 kohm) = V")
        region.finish_editing()
        win.sheet.recalculate()
        assert region.result is not None and region.result.status == "ok"
        assert "9" in region.result.output and region.result.output.rstrip().endswith("V")
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_insertion_is_plain_text_no_format_change():
    import json
    win = MainWindow()
    try:
        win.side_panel.symbol_buttons["power factor"].click()
        doc = win.sheet.to_document()
        assert doc.version() == 1
        data = json.loads(doc.to_json())
        assert [r["kind"] for r in data["regions"]] == ["math"]
        assert data["regions"][0]["text"].strip() == "power_factor(phi)"
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_second_click_appends_to_same_region():
    win = MainWindow()
    try:
        win.side_panel.symbol_buttons["phasor"].click()
        n = len(win.sheet.regions())
        win.side_panel.symbol_buttons["power factor"].click()
        assert len(win.sheet.regions()) == n
        src = win.sheet.editing_region().source
        assert "phasor(mag, phi)" in src and "power_factor(phi)" in src
    finally:
        win.sheet.set_modified(False)
        win.close()


# ---------------------------------------------------------------- layout / narrow width

# 180 px overflows on the pre-existing DC buttons and other tabs too (not a GUI-1 defect).
@pytest.mark.parametrize("width", [260, 420])
def test_narrow_panel_wraps_buttons_without_horizontal_overflow(width):
    panel = SidePanel(lambda _t: None)
    panel.resize(width, 400)
    panel.show()
    try:
        panel.tabs.setCurrentIndex(TAB_ORDER.index("Electrical"))
        _app.processEvents()
        page = panel.tabs.currentWidget()
        assert isinstance(page, QScrollArea)
        assert not page.horizontalScrollBar().isVisible()
        inner = page.widget()
        _app.processEvents()
        assert inner.width() <= page.viewport().width() + 1
        for b in inner.findChildren(QPushButton):
            r = b.geometry()
            # a button wider than the panel is clipped by design; no button may start off-screen
            assert r.left() >= 0 and r.left() < inner.width(), (b.text(), r)
            if b.sizeHint().width() < inner.width() - 12:
                assert r.right() <= inner.width() + 1, (b.text(), r, inner.width())
    finally:
        panel.close()


def test_main_window_narrow_still_clickable():
    win = MainWindow()
    try:
        win.resize(360, 500)
        win.show()
        _app.processEvents()
        win.side_panel.tabs.setCurrentIndex(TAB_ORDER.index("Electrical"))
        win.side_panel.symbol_buttons["RC low-pass gain"].click()
        assert win.sheet.editing_region().source.strip() == "rc_lowpass_gain(f_hz, R, Ccap)"
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_side_panel_has_no_search_box():
    """Informational: the panel has no search field, so there is nothing to check for GUI-1."""
    from PySide6.QtWidgets import QLineEdit
    panel = SidePanel(lambda _t: None)
    assert not panel.findChildren(QLineEdit)
