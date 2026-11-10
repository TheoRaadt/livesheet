"""Independent black-box review of specs 018 (Mechanical), 019 (Chemical), 020 (Electrical).

Written from the specs (docs/board/specs/018-mechanical-formula-tab.md, 019-..., 020-...) and the
numeric corrections in docs/board/decisions.md (2026-11-01), not from the implementation. The
expected label/token/tooltip tables below are typed in from the specs' tables.

Allowed, documented developer deviations (all ASCII-only requests): the middle dot in "N·m" and the
em dash become "*" and "-"; the double quotes around "30*deg" are dropped; the chemical labels
"rho_gas" (spec: Greek rho glyph) and "m-dot bal." (spec: m with dot accent).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import pytest

try:
    import PySide6.QtWidgets  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from livesheet.engine.evaluator import Engine
from livesheet.gui import main_window as mw_module
from livesheet.gui.main_window import MainWindow
from livesheet.gui.sidepanel import SidePanel
from livesheet.gui.worksheet import MathRegion

_app = QApplication.instance() or QApplication([])

ORDER = ["Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical",
         "Electrical", "Chemical", "Outline", "Data"]

# (sub-header, label, token, tooltip) -- from the spec tables
MECH = [
    ("Statics", "Resultant (2 forces)", "R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))",
     "Resultant of two concurrent forces (law of cosines). P1, P2 in N; theta in rad (or e.g. "
     "30*deg); R in N."),
    ("Statics", "Force, x-component", "Fx := P*cos(theta)",
     "Horizontal component of a force P at angle theta from the x-axis. P in N; Fx in N."),
    ("Statics", "Force, y-component", "Fy := P*sin(theta)",
     "Vertical component of a force P at angle theta from the x-axis. P in N; Fy in N."),
    ("Statics", "Moment of a force", "M := P*d",
     "Moment of a force P about a point, at perpendicular distance d from its line of action. "
     "P in N; d in m; M in N*m."),
    ("Statics", "Static friction limit", "Ff := mu_s*Fn",
     "Maximum static friction force (Coulomb friction model). mu_s dimensionless; Fn (normal "
     "contact force) in N; Ff in N."),
    ("Statics", "Centroid, 2 point masses", "x_cg := (m1*x1 + m2*x2)/(m1 + m2)",
     "x-coordinate of the combined centre of mass of two point masses. m1, m2 in kg; x1, x2 in "
     "m; x_cg in m."),
    ("Strength of Materials", "Axial (normal) stress", "sigma := P/Ac",
     "Normal stress from an axial load. P in N; Ac (cross-sectional area) in m^2; sigma in Pa."),
    ("Strength of Materials", "Normal strain", "epsilon := dL/L0",
     "Strain from an elongation. dL, L0 in m; epsilon dimensionless."),
    ("Strength of Materials", "Hooke's law (axial)", "sigma := E*epsilon",
     "Linear-elastic stress-strain relation. E (Young's modulus) in Pa; epsilon dimensionless; "
     "sigma in Pa."),
    ("Strength of Materials", "Axial elongation", "dL := P*L0/(Ac*E)",
     "Elongation of a bar under axial load. P in N; L0 in m; Ac in m^2; E in Pa; dL in m."),
    ("Strength of Materials", "Bending stress", "sigma_b := M*y/Ix",
     "Bending (flexural) stress at distance y from the neutral axis. M in N*m; y in m; Ix "
     "(second moment of area) in m^4; sigma_b in Pa."),
    ("Strength of Materials", "Transverse shear stress", "tau := Fv*Q/(Ix*b)",
     "Shear stress in a beam from a transverse shear force. Fv in N; Q (first moment of area) "
     "in m^3; Ix in m^4; b (section width) in m; tau in Pa."),
    ("Strength of Materials", "Average shear stress", "tau_avg := P/Ac",
     "Average shear stress from a force acting parallel to a surface. P in N; Ac in m^2; "
     "tau_avg in Pa."),
    ("Strength of Materials", "Linear thermal expansion", "dL_t := alpha_t*L0*dT",
     "Elongation from a temperature change. alpha_t (linear expansion coefficient) in 1/K; L0 "
     "in m; dT in K; dL_t in m."),
    ("Strength of Materials", "Factor of safety", "n := sigma_allow/sigma_actual",
     "Ratio of allowable to actual stress. sigma_allow, sigma_actual in Pa; n dimensionless."),
]

_E = [
    ("DC Circuits", "Vs := Is * R", "Ohm's law - voltage from current and resistance (Vs in volts, "
     "Is in amps, R in ohms)"),
    ("DC Circuits", "Is := Vs / R", "Ohm's law - current from voltage and resistance"),
    ("DC Circuits", "R := Vs / Is", "Ohm's law - resistance from voltage and current"),
    ("DC Circuits", "R_total := R1 + R2", "Resistors in series - equivalent resistance of two "
     "resistors"),
    ("DC Circuits", "R_total := 1 / (1/R1 + 1/R2)", "Resistors in parallel - equivalent "
     "resistance of two resistors"),
    ("DC Circuits", "V_out := V_in * R2 / (R1 + R2)", "Voltage divider - output voltage measured "
     "across R2"),
    ("DC Circuits", "I1 := I_total * R2 / (R1 + R2)", "Current divider - current through the R1 "
     "branch of two resistors in parallel"),
    ("Power", "P := Vs * Is", "Electrical power from voltage and current"),
    ("Power", "P := Is^2 * R", "Electrical power from current and resistance"),
    ("Power", "P := Vs^2 / R", "Electrical power from voltage and resistance"),
    ("Power", "E := P * t", "Electrical energy from power and time"),
]
ELEC = [(c, text, text, tip) for c, text, tip in _E]  # label == token (spec criterion 3)

S1, S2, S3 = "Stoichiometry & Composition", "Ideal Gas & Thermodynamic State", "Mass & Energy Balances"
S4, S5 = "Fluid & Heat/Mass Transport", "Reaction Kinetics"
CHEM = [
    (S1, "n", "n_A := m_A / M_A", "Amount of substance from mass and molar mass"),
    (S1, "w", "w_A := m_A / m_total", "Mass fraction of a component in a mixture"),
    (S1, "x", "x_A := n_A / n_total", "Mole fraction of a component in a mixture"),
    (S1, "c", "c_A := n_A / V_sol", "Molar concentration (amount per solution volume)"),
    (S2, "R", "R_gas := 8.314 J/(mol*K)", "Universal gas constant (SI)"),
    (S2, "PV=nRT", "P_gas := n_gas * R_gas * T_gas / V_gas", "Ideal gas law"),
    (S2, "rho_gas", "rho_gas := P_gas * M_gas / (R_gas * T_gas)",
     "Ideal-gas density from pressure, molar mass, temperature"),
    (S2, "Q_sens", "Q_sens := m_sub * c_p * (T_2 - T_1)",
     "Sensible heat for a temperature change (no phase change)"),
    (S2, "Q_lat", "Q_lat := m_sub * L_phase", "Latent heat for a phase change at constant temperature"),
    (S3, "m-dot bal.", "m_out := m_in", "Steady-state overall mass balance (no accumulation)"),
    (S3, "comp. bal.", "m_A_out := m_A_in + m_A_gen - m_A_cons",
     "Steady-state component mass balance with reaction"),
    (S3, "dm/dt", "dm_dt := m_in_rate - m_out_rate", "Dynamic (unsteady) overall mass balance"),
    (S3, "energy bal.", "Q_rate := m_flow_rate * (h_out - h_in) + W_rate",
     "Steady-state open-system energy balance (no KE/PE change)"),
    (S4, "Re", "Re := rho_fluid * v_flow * D_pipe / mu_fluid",
     "Reynolds number (inertial/viscous force ratio)"),
    (S4, "Q_cond", "Q_cond := k_therm * A_surf * (T_hot - T_cold) / L_thick",
     "Steady 1-D conductive heat flow across a slab"),
    (S4, "Q_conv", "Q_conv := h_conv * A_surf * (T_wall - T_fluid)", "Convective heat flow at a surface"),
    (S4, "J_diff", "J_diff := D_ab * (c_A1 - c_A2) / L_film",
     "Steady 1-D diffusive molar flux across a film"),
    (S5, "rate law", "r_rxn := k_rate * C_A^n_order", "Power-law reaction rate expression"),
    (S5, "Arrhenius", "k_rate := A_arr * exp(-E_act / (R_gas * T_rxn))",
     "Temperature dependence of a rate constant"),
    (S5, "half-life", "t_half := ln(2) / k_rate", "Half-life of a first-order reaction"),
    (S5, "conversion", "X_A := (C_A0 - C_A) / C_A0", "Fractional conversion of a reactant"),
]

TABS = {
    "Mechanical": (MECH, ["Statics", "Strength of Materials"], [6, 9]),
    "Electrical": (ELEC, ["DC Circuits", "Power"], [7, 4]),
    "Chemical": (CHEM, [S1, S2, S3, S4, S5], [4, 5, 4, 4, 4]),
}


def _norm(text: str) -> str:
    return text.replace("·", "*").replace("—", "-").replace('"', "")


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(mw_module, "QSettings",
                        lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat))


def _panel():
    sink: list[str] = []
    return SidePanel(sink.append), sink


def _tab_buttons_and_headers(panel, name):
    """Walk the tab's widget in layout order: ('H', text) / ('B', button) items."""
    scroll = panel.tabs.widget(ORDER.index(name))
    container = scroll.widget()
    lay = container.layout()
    items = []
    for i in range(lay.count()):
        w = lay.itemAt(i).widget()
        if isinstance(w, QLabel):
            items.append(("H", w.text()))
        elif isinstance(w, QPushButton):
            items.append(("B", w))
    return items


# --------------------------------------------------------------- GUI / data: criteria 1-4 / 1-3 / 1-3,8

def test_tab_order_and_older_tabs_unchanged():
    panel, _ = _panel()
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == ORDER


def test_older_tabs_keep_their_buttons():
    panel, _ = _panel()
    labels = {b.text() for b in panel.tabs.widget(0).findChildren(QPushButton)}
    assert {"π", ":=", "α"} <= labels or len(labels) >= 40
    assert len(panel.tabs.widget(0).findChildren(QPushButton)) >= 40
    # new formula buttons must not leak into the older functional tabs
    new_labels = {r[1] for rows in (MECH, ELEC, CHEM) for r in rows}
    for name in ("Elements", "Algebra", "Calculus"):
        have = {b.text() for b in panel.tabs.widget(ORDER.index(name)).findChildren(QPushButton)}
        assert not (have & new_labels), (name, have & new_labels)


@pytest.mark.parametrize("tab", list(TABS))
def test_headers_and_counts(tab):
    rows, headers, counts = TABS[tab]
    panel, _ = _panel()
    items = _tab_buttons_and_headers(panel, tab)
    assert [t for k, t in items if k == "H"] == headers
    assert sum(counts) == len([1 for k, _ in items if k == "B"]) == len(rows)
    # buttons are grouped under their own header, in order
    seq, cur = [], None
    for k, v in items:
        if k == "H":
            cur = v
            seq.append([cur, 0])
        else:
            seq[-1][1] += 1
    assert [n for _, n in seq] == counts


def test_spec_counts_15_11_21():
    assert (len(MECH), len(ELEC), len(CHEM)) == (15, 11, 21)


@pytest.mark.parametrize("tab", list(TABS))
def test_labels_tokens_tooltips_exact_and_ordered(tab):
    rows, headers, _ = TABS[tab]
    panel, sink = _panel()
    buttons = [v for k, v in _tab_buttons_and_headers(panel, tab) if k == "B"]
    assert [b.text() for b in buttons] == [r[1] for r in rows]
    for b, (_cat, label, token, tip) in zip(buttons, rows):
        got_tip = _norm(b.toolTip())
        if label == "Moment of a force":
            # criterion 16: tooltip must additionally warn that a bare "M =" shows J
            assert got_tip.startswith(_norm(tip)), got_tip
            assert "J" in got_tip[len(_norm(tip)):]
        else:
            assert got_tip == _norm(tip), (label, got_tip)
        sink.clear()
        b.click()
        assert sink == [token], label           # only insert_token, with the exact token
        assert token.isascii()
        assert b.text().isascii() and b.toolTip().isascii(), label


def test_all_labels_unique_across_whole_panel():
    # SidePanel.symbol_buttons is keyed by label: a duplicate label would hide a button from lookups
    panel, _ = _panel()
    # The Data page (spec 028) holds its own action/dataset buttons, outside the static registry.
    every = [b.text() for i in range(panel.tabs.count()) if panel.tabs.tabText(i) != "Data"
             for b in panel.tabs.widget(i).findChildren(QPushButton)]
    assert len(every) == len(set(every))
    assert len(panel.symbol_buttons) == len(every)


def test_si_only_no_imperial_units_anywhere():
    import re
    bad = re.compile(r"\b(lbf|lb|ft|inch|in\.|psi|slug|BTU|mph|yd|mi)\b")
    for rows in (MECH, ELEC, CHEM):
        for _c, label, token, tip in rows:
            assert not bad.search(token) and not bad.search(tip), (label, token, tip)


def test_no_vendor_names_in_new_content():
    for rows in (MECH, ELEC, CHEM):
        for _c, label, token, tip in rows:
            low = (label + token + tip).lower()
            for word in ("mathcad", "ptc", "maple", "mathematica", "matlab", "wolfram"):
                assert word not in low


# ------------------------------------------------------- insertion through the real side panel

def _all_rows():
    return [(t, r) for t in TABS for r in TABS[t][0]]


@pytest.mark.parametrize("tab,row", _all_rows(), ids=lambda v: v if isinstance(v, str) else v[1])
def test_clicking_each_button_inserts_exact_token_in_real_window(tab, row):
    win = MainWindow()
    try:
        win.sheet.set_modified(False)
        tabs = win.side_panel.tabs
        tabs.setCurrentIndex(ORDER.index(tab))
        btn = win.side_panel.symbol_buttons[row[1]]
        btn.click()
        region = win.sheet.editing_region()
        assert isinstance(region, MathRegion)
        assert region.source.strip() == row[2]
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_second_click_appends_to_same_region_not_a_new_one():
    win = MainWindow()
    try:
        before = len(win.sheet.regions())
        win.side_panel.symbol_buttons["Moment of a force"].click()
        win.side_panel.symbol_buttons["Axial (normal) stress"].click()
        assert len(win.sheet.regions()) == before + 1
        assert "M := P*d" in win.sheet.editing_region().source
        assert "sigma := P/Ac" in win.sheet.editing_region().source
    finally:
        win.sheet.set_modified(False)
        win.close()


def test_inserted_text_saves_as_plain_version_1_region():
    import json
    win = MainWindow()
    try:
        win.side_panel.symbol_buttons["Hooke's law (axial)"].click()
        doc = win.sheet.to_document()
        assert doc.version() == 1                      # criterion 4: no format-version change
        data = json.loads(doc.to_json())
        assert [r["kind"] for r in data["regions"]] == ["math"]
        assert data["regions"][0]["text"].strip() == "sigma := E*epsilon"
    finally:
        win.sheet.set_modified(False)
        win.close()


# --------------------------------------------------------------------------- Engine: worked examples

def run(*sources):
    res = Engine().evaluate(list(enumerate(sources)))
    return [res[i] for i in range(len(sources))]


def last(*sources):
    return run(*sources)[-1]


def out(*sources):
    r = last(*sources)
    assert r.status == "ok", r.error
    return r.output


def test_m5_axial_stress():
    assert out("P := 1000 N", "Ac := 50 mm^2", "sigma := P/Ac", "sigma = MPa") == "= 20 MPa"
    # the uncorrected bare form is numerically the same in base SI
    assert out("P := 1000 N", "Ac := 50 mm^2", "sigma := P/Ac", "sigma =") == "= 2×10⁷ Pa"


def test_m6_bending_stress():
    assert out("M := 500 N*m", "y := 0.05 m", "Ix := 8e-6 m^4", "sigma_b := M*y/Ix",
               "sigma_b = MPa") == "= 3.125 MPa"


def test_m7_transverse_shear():
    assert out("Fv := 2000 N", "Q := 1.2e-4 m^3", "Ix := 8e-6 m^4", "b := 0.02 m",
               "tau := Fv*Q/(Ix*b)", "tau = MPa") == "= 1.5 MPa"


def test_m8_hooke():
    assert out("E := 200 GPa", "epsilon := 0.001", "sigma := E*epsilon", "sigma = MPa") == "= 200 MPa"


def test_m9_elongation():
    src = ["P := 5000 N", "L0 := 2 m", "Ac := 100 mm^2", "E := 200 GPa", "dL := P*L0/(Ac*E)"]
    assert out(*src, "dL = mm") == "= 0.5 mm"
    assert out(*src, "dL =") == "= 0.0005 m"


def test_m10_thermal():
    src = ["alpha_t := 1.2e-5 /K", "L0 := 2 m", "dT := 50 K", "dL_t := alpha_t*L0*dT"]
    assert out(*src, "dL_t = mm") == "= 1.2 mm"
    assert out(*src, "dL_t =") == "= 0.0012 m"


def test_m11_factor_of_safety():
    assert out("sigma_allow := 250 MPa", "sigma_actual := 100 MPa",
               "n := sigma_allow/sigma_actual", "n =") == "= 2.5"


def test_m12_resultant_3_4_5():
    assert out("P1 := 3 N", "P2 := 4 N", "theta := 90*deg",
               "R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))", "R =") == "= 5 N"


def test_m12b_resultant_parallel_and_opposite():
    base = ["P1 := 3 N", "P2 := 4 N"]
    f = "R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))"
    assert out(*base, "theta := 0*deg", f, "R =") == "= 7 N"
    assert out(*base, "theta := 180*deg", f, "R =") == "= 1 N"


def test_m13_components():
    assert out("P := 10 N", "theta := 30*deg", "Fx := P*cos(theta)", "Fx =") == "= 8.66025 N"
    assert out("P := 10 N", "theta := 30*deg", "Fy := P*sin(theta)", "Fy =") == "= 5 N"


def test_m14_friction():
    assert out("mu_s := 0.3", "Fn := 200 N", "Ff := mu_s*Fn", "Ff =") == "= 60 N"


def test_m15_centroid():
    assert out("m1 := 2 kg", "x1 := 0 m", "m2 := 3 kg", "x2 := 5 m",
               "x_cg := (m1*x1 + m2*x2)/(m1 + m2)", "x_cg =") == "= 3 m"


def test_m16_moment():
    assert out("P := 100 N", "d := 0.3 m", "M := P*d", "M = N*m") == "= 30 N·m"
    assert out("P := 100 N", "d := 0.3 m", "M := P*d", "M =") == "= 30 J"


def test_m_strain_from_template():
    assert out("dL := 1 mm", "L0 := 2 m", "epsilon := dL/L0", "epsilon =") == "= 0.0005"


def test_m_average_shear_matches_axial_shape():
    a = out("P := 10 kN", "Ac := 20 cm^2", "tau_avg := P/Ac", "tau_avg = MPa")
    assert a == "= 5 MPa"


def test_m17_error_fresh_region_template_alone():
    r = run("sigma := P/Ac", "sigma =")
    assert r[1].status == "error" and r[1].error == "Ac, P are not defined"


def test_m17_regression_landmine_now_closed_with_naive_names():
    # Spec 018 criterion 17 (second half) documented that `sigma := F/A` evaluated "ok" silently.
    # After the _check_defined hardening it must error instead (dev dropped this test; inverted here).
    r = run("sigma := F/A", "sigma =")
    assert r[1].status == "error" and "not defined" in r[1].error


def test_m18_wrong_dimension_for_area():
    r = last("P := 5000 N", "L0 := 2 m", "Ac := 5 N", "E := 200 GPa", "dL := P*L0/(Ac*E)",
             "dL = mm")
    assert r.status == "error" and r.error == "Units do not match: result is m²·s²/kg"
    r = last("P := 5000 N", "L0 := 2 m", "Ac := 5 N", "E := 200 GPa", "dL := P*L0/(Ac*E)", "dL =")
    assert r.status == "ok"        # a bare = has nothing to compare against


# ---- Electrical (020)

def test_e4_ohm():
    assert out("Is := 2 A", "R := 10 ohm", "Vs := Is * R", "Vs =") == "= 20 V"


def test_e5_parallel():
    assert out("R1 := 100 ohm", "R2 := 100 ohm", "R_total := 1 / (1/R1 + 1/R2)",
               "R_total =") == "= 50 Ω"


def test_e6_power():
    assert out("Vs := 12 V", "Is := 3 A", "P := Vs * Is", "P =") == "= 36 W"


def test_e7_error_names_plural_form():
    r = run("P := Is^2 * R", "P =")[1]
    assert r.status == "error" and r.error == "Is, R are not defined"
    r = run("Is := 2 A", "P := Is^2 * R", "P =")[2]
    assert r.status == "error" and r.error == "R is not defined"


def test_e_other_templates_numeric():
    assert out("Vs := 12 V", "R := 4 ohm", "Is := Vs / R", "Is =") == "= 3 A"
    assert out("Vs := 12 V", "Is := 3 A", "R := Vs / Is", "R =") == "= 4 Ω"
    assert out("R1 := 100 ohm", "R2 := 220 ohm", "R_total := R1 + R2", "R_total =") == "= 320 Ω"
    assert out("V_in := 10 V", "R1 := 1 kohm", "R2 := 3 kohm", "V_out := V_in * R2 / (R1 + R2)",
               "V_out =") == "= 7.5 V"
    assert out("I_total := 2 A", "R1 := 10 ohm", "R2 := 30 ohm", "I1 := I_total * R2 / (R1 + R2)",
               "I1 =") == "= 1.5 A"
    assert out("Is := 2 A", "R := 5 ohm", "P := Is^2 * R", "P =") == "= 20 W"
    assert out("Vs := 10 V", "R := 5 ohm", "P := Vs^2 / R", "P =") == "= 20 W"
    assert out("P := 100 W", "t := 60 s", "E := P * t", "E = kJ") == "= 6 kJ"


# ---- Chemical (019)

def test_c3_ideal_gas():
    o = out("R_gas := 8.314 J/(mol*K)", "n_gas := 2 mol", "T_gas := 300 K", "V_gas := 0.05 m^3",
            "P_gas := n_gas * R_gas * T_gas / V_gas", "P_gas =")
    assert o.startswith("= 99768") and o.endswith("Pa")


def test_c3_gas_constant_button_token_itself():
    o = out("R_gas := 8.314 J/(mol*K)", "n_gas := 2 mol", "T_gas := 300 K", "V_gas := 0.05 m^3",
            "P_gas := n_gas * R_gas * T_gas / V_gas", "P_gas = kPa")
    assert o == "= 99.768 kPa"


def test_c4_sensible_heat():
    src = ["m_sub := 5 kg", "c_p := 4186 J/(kg*K)", "T_1 := 290 K", "T_2 := 350 K",
           "Q_sens := m_sub * c_p * (T_2 - T_1)"]
    assert out(*src, "Q_sens = kJ") == "= 1255.8 kJ"
    assert out(*src, "Q_sens = J") == "= 1.2558×10⁶ J"   # same value, formatter switches to exponent


def test_c4_sensible_heat_unit_error():
    r = last("m_sub := 5 kg", "c_p := 4186 J/(kg*K)", "T_1 := 290 K", "T_2 := 350 Pa",
             "Q_sens := m_sub * c_p * (T_2 - T_1)", "Q_sens =")
    assert r.status == "error" and "Units do not match" in r.error


def test_c5_reynolds_dimensionless():
    o = out("rho_fluid := 1000 kg/m^3", "v_flow := 2 m/s", "D_pipe := 0.05 m",
            "mu_fluid := 0.001 Pa*s", "Re := rho_fluid * v_flow * D_pipe / mu_fluid", "Re =")
    assert o == "= 100000"


def test_c6_energy_balance():
    o = out("m_flow_rate := 2 kg/s", "h_out := 500 kJ/kg", "h_in := 300 kJ/kg", "W_rate := 0 kW",
            "Q_rate := m_flow_rate * (h_out - h_in) + W_rate", "Q_rate = kW")
    assert o == "= 400 kW"


def test_c7_mole_fraction():
    assert out("n_A := 3 mol", "n_total := 10 mol", "x_A := n_A / n_total", "x_A =") == "= 0.3"


def test_c_remaining_templates_numeric():
    # independent closed-form cross-checks
    assert out("m_A := 18 gm", "M_A := 18 gm/mol", "n_A := m_A / M_A", "n_A = mol") == "= 1 mol"
    assert out("m_A := 2 kg", "m_total := 8 kg", "w_A := m_A / m_total", "w_A =") == "= 0.25"
    assert out("n_A := 2 mol", "V_sol := 4 L", "c_A := n_A / V_sol", "c_A = mol/L") == "= 0.5 mol/L"
    assert out("m_sub := 2 kg", "L_phase := 334 kJ/kg", "Q_lat := m_sub * L_phase",
               "Q_lat = kJ") == "= 668 kJ"
    assert out("m_in := 5 kg/s", "m_out := m_in", "m_out =") == "= 5 kg/s"
    assert out("m_A_in := 5 mol/s", "m_A_gen := 2 mol/s", "m_A_cons := 1 mol/s",
               "m_A_out := m_A_in + m_A_gen - m_A_cons", "m_A_out =") == "= 6 mol/s"
    assert out("m_in_rate := 5 kg/s", "m_out_rate := 3 kg/s", "dm_dt := m_in_rate - m_out_rate",
               "dm_dt =") == "= 2 kg/s"
    assert out("k_therm := 0.5 W/(m*K)", "A_surf := 2 m^2", "T_hot := 400 K", "T_cold := 300 K",
               "L_thick := 0.1 m", "Q_cond := k_therm * A_surf * (T_hot - T_cold) / L_thick",
               "Q_cond = W") == "= 1000 W"
    assert out("h_conv := 10 W/(m^2*K)", "A_surf := 2 m^2", "T_wall := 350 K", "T_fluid := 300 K",
               "Q_conv := h_conv * A_surf * (T_wall - T_fluid)", "Q_conv = W") == "= 1000 W"
    assert out("D_ab := 1e-5 m^2/s", "c_A1 := 2 mol/m^3", "c_A2 := 1 mol/m^3", "L_film := 1 mm",
               "J_diff := D_ab * (c_A1 - c_A2) / L_film", "J_diff =") == "= 0.01 mol/(m²·s)"
    assert out("k_rate := 2 /s", "t_half := ln(2) / k_rate", "t_half =").startswith("= 0.346574 s")
    assert out("C_A0 := 2 mol/L", "C_A := 0.5 mol/L", "X_A := (C_A0 - C_A) / C_A0",
               "X_A =") == "= 0.75"
    assert out("k_rate := 3 mol/(L*s)", "C_A := 2", "n_order := 2", "r_rxn := k_rate * C_A^n_order",
               "r_rxn =") .startswith("= 12000 mol")


def test_c_density_and_arrhenius_closed_form():
    r = last("R_gas := 8.314 J/(mol*K)", "P_gas := 101325 Pa", "M_gas := 28.97 gm/mol",
             "T_gas := 300 K", "rho_gas := P_gas * M_gas / (R_gas * T_gas)", "rho_gas =")
    assert r.status == "ok"
    val = float(r.output.split()[1].replace("×10", "e"))
    assert val == pytest.approx(101325 * 0.02897 / (8.314 * 300), rel=1e-4)
    r = last("R_gas := 8.314 J/(mol*K)", "A_arr := 1e10 /s", "E_act := 50 kJ/mol", "T_rxn := 300 K",
             "k_rate := A_arr * exp(-E_act / (R_gas * T_rxn))", "k_rate =")
    assert r.status == "ok"
    val = float(r.output.split()[1].replace("×10", "e").replace("⁻", "-")
                .translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")))
    assert val == pytest.approx(1e10 * math.exp(-50000 / (8.314 * 300)), rel=1e-3)


# ---- every template alone / criterion 10 (silent-wrong-answer check)

@pytest.mark.parametrize("tab,row", _all_rows(), ids=lambda v: v if isinstance(v, str) else v[1])
def test_template_alone_never_silently_succeeds(tab, row):
    token = row[2]
    name = token.split(":=")[0].strip()
    r = run(token, name + " =")
    assert r[0].status == "ok"                      # the definition itself is accepted
    if name == "R_gas":                              # the one constant: a literal with units
        assert r[1].status == "ok" and "mol" in r[1].output
    else:
        assert r[1].status == "error" and "not defined" in r[1].error, (token, r[1])


def test_names_unique_enough_collisions_with_units_and_builtins():
    from livesheet.engine.evaluator import BUILTINS
    from livesheet.engine.units import UNITS
    import re
    for _t, row in _all_rows():
        ids = set(re.findall(r"(?<![\w.])[^\W\d]\w*", row[2])) - {"sqrt", "cos", "sin", "exp", "ln",
                                                                 "J", "mol", "K"}
        for name in ids:
            assert name not in UNITS, (row[2], name)
            assert name not in BUILTINS, (row[2], name)
