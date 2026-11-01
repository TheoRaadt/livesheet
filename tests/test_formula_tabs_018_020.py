"""Specs 018/019/020: Mechanical, Electrical and Chemical side-panel formula tabs."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

try:
    import PySide6.QtWidgets  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.skip(f"PySide6 cannot be loaded: {exc}", allow_module_level=True)

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from livesheet.engine.evaluator import Engine
from livesheet.gui.sidepanel import MATH_TOKENS, TAB_CATEGORIES, TAB_ORDER, SidePanel

_app = QApplication.instance() or QApplication([])

FINAL_ORDER = ("Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical",
               "Electrical", "Chemical", "Outline", "Data")


def _panel(inserted: list[str] | None = None) -> SidePanel:
    sink = inserted if inserted is not None else []
    return SidePanel(sink.append)


def _tab(panel: SidePanel, name: str):
    return panel.tabs.widget(TAB_ORDER.index(name))


def _headers(widget) -> list[str]:
    return [lab.text() for lab in widget.findChildren(QLabel)]


def _buttons(widget) -> list[QPushButton]:
    return widget.findChildren(QPushButton)


def _rows(cats: tuple[str, ...]) -> list[tuple[str, str, str, str]]:
    return [t for c in cats for t in MATH_TOKENS if t[0] == c]


def test_tab_order() -> None:
    assert TAB_ORDER == FINAL_ORDER
    panel = _panel()
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == list(FINAL_ORDER)


@pytest.mark.parametrize("tab,cats,counts", [
    ("Mechanical", ("Statics", "Strength of Materials"), [6, 9]),
    ("Electrical", ("DC Circuits", "Power"), [7, 4]),
    ("Chemical", ("Stoichiometry & Composition", "Ideal Gas & Thermodynamic State",
                  "Mass & Energy Balances", "Fluid & Heat/Mass Transport", "Reaction Kinetics"),
     [4, 5, 4, 4, 4]),
])
def test_tab_structure(tab, cats, counts) -> None:
    assert TAB_CATEGORIES[tab] == cats
    panel = _panel()
    widget = _tab(panel, tab)
    assert _headers(widget) == list(cats)
    assert [len([t for t in MATH_TOKENS if t[0] == c]) for c in cats] == counts
    assert len(_buttons(widget)) == sum(counts)


def test_all_tokens_ascii_with_tooltips_and_unique_labels() -> None:
    labels = [t[1] for t in MATH_TOKENS]
    assert len(set(labels)) == len(labels)
    for cats in (TAB_CATEGORIES["Mechanical"], TAB_CATEGORIES["Electrical"],
                 TAB_CATEGORIES["Chemical"]):
        for _c, label, token, tip in _rows(cats):
            assert label.isascii() and token.isascii() and tip.isascii() and tip
            assert ":=" in token


def test_clicks_insert_exact_token() -> None:
    sink: list[str] = []
    panel = _panel(sink)
    for label, token in (("Moment of a force", "M := P*d"),
                         ("Axial (normal) stress", "sigma := P/Ac"),
                         ("Vs := Is * R", "Vs := Is * R"),
                         ("PV=nRT", "P_gas := n_gas * R_gas * T_gas / V_gas"),
                         ("Q_sens", "Q_sens := m_sub * c_p * (T_2 - T_1)")):
        panel.symbol_buttons[label].click()
        assert sink[-1] == token


def test_electrical_label_equals_token() -> None:
    for _c, label, token, _t in _rows(TAB_CATEGORIES["Electrical"]):
        assert label == token


def test_existing_tabs_unchanged() -> None:
    panel = _panel()
    assert len(_buttons(_tab(panel, "Elements"))) + len(_buttons(_tab(panel, "Algebra"))) \
        + len(_buttons(_tab(panel, "Calculus"))) == 46


# -- engine behaviour of the templates ---------------------------------------------------------

def _last(lines: list[str]):
    out = Engine().evaluate(list(enumerate(lines)))
    items = out if isinstance(out, list) else list(out.values())
    return items[-1]


def _txt(lines: list[str]) -> str:
    r = _last(lines)
    return r.output if r.status == "ok" else r.error


@pytest.mark.parametrize("lines,expected", [
    (["P := 1000 N", "Ac := 50 mm^2", "sigma := P/Ac", "sigma = MPa"], "20 MPa"),
    (["M := 500 N*m", "y := 0.05 m", "Ix := 8e-6 m^4", "sigma_b := M*y/Ix", "sigma_b = MPa"],
     "3.125 MPa"),
    (["Fv := 2000 N", "Q := 1.2e-4 m^3", "Ix := 8e-6 m^4", "b := 0.02 m",
      "tau := Fv*Q/(Ix*b)", "tau = MPa"], "1.5 MPa"),
    (["E := 200 GPa", "epsilon := 0.001", "sigma := E*epsilon", "sigma = MPa"], "200 MPa"),
    (["P := 5000 N", "L0 := 2 m", "Ac := 100 mm^2", "E := 200 GPa", "dL := P*L0/(Ac*E)",
      "dL = mm"], "0.5 mm"),
    (["alpha_t := 1.2e-5 /K", "L0 := 2 m", "dT := 50 K", "dL_t := alpha_t*L0*dT", "dL_t = mm"],
     "1.2 mm"),
    (["sigma_allow := 250 MPa", "sigma_actual := 100 MPa", "n := sigma_allow/sigma_actual",
      "n ="], "2.5"),
    (["P1 := 3 N", "P2 := 4 N", "theta := 90*deg",
      "R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))", "R ="], "5 N"),
    (["P := 10 N", "theta := 30*deg", "Fx := P*cos(theta)", "Fx ="], "8.66025 N"),
    (["P := 10 N", "theta := 30*deg", "Fy := P*sin(theta)", "Fy ="], "5 N"),
    (["mu_s := 0.3", "Fn := 200 N", "Ff := mu_s*Fn", "Ff ="], "60 N"),
    (["m1 := 2 kg", "x1 := 0 m", "m2 := 3 kg", "x2 := 5 m",
      "x_cg := (m1*x1 + m2*x2)/(m1 + m2)", "x_cg ="], "3 m"),
    (["P := 100 N", "d := 0.3 m", "M := P*d", "M = N*m"], "30 N"),
    (["Is := 2 A", "R := 10 ohm", "Vs := Is * R", "Vs ="], "20 V"),
    (["R1 := 100 ohm", "R2 := 100 ohm", "R_total := 1 / (1/R1 + 1/R2)", "R_total ="], "50"),
    (["Vs := 12 V", "Is := 3 A", "P := Vs * Is", "P ="], "36 W"),
    (["R_gas := 8.314 J/(mol*K)", "n_gas := 2 mol", "T_gas := 300 K", "V_gas := 0.05 m^3",
      "P_gas := n_gas * R_gas * T_gas / V_gas", "P_gas ="], "99768"),
    (["m_sub := 5 kg", "c_p := 4186 J/(kg*K)", "T_1 := 290 K", "T_2 := 350 K",
      "Q_sens := m_sub * c_p * (T_2 - T_1)", "Q_sens = kJ"], "1255.8 kJ"),
    (["rho_fluid := 1000 kg/m^3", "v_flow := 2 m/s", "D_pipe := 0.05 m", "mu_fluid := 0.001 Pa*s",
      "Re := rho_fluid * v_flow * D_pipe / mu_fluid", "Re ="], "100000"),
    (["m_flow_rate := 2 kg/s", "h_out := 500 kJ/kg", "h_in := 300 kJ/kg", "W_rate := 0 kW",
      "Q_rate := m_flow_rate * (h_out - h_in) + W_rate", "Q_rate = kW"], "400 kW"),
    (["n_A := 3 mol", "n_total := 10 mol", "x_A := n_A / n_total", "x_A ="], "0.3"),
])
def test_worked_examples(lines, expected) -> None:
    r = _last(lines)
    assert r.status == "ok", r.error
    assert expected in r.output


def test_bare_energy_and_heat_forms() -> None:
    assert "1.2558" in _txt(["m_sub := 5 kg", "c_p := 4186 J/(kg*K)", "T_1 := 290 K",
                             "T_2 := 350 K", "Q_sens := m_sub * c_p * (T_2 - T_1)", "Q_sens ="])
    assert "J" in _txt(["P := 100 N", "d := 0.3 m", "M := P*d", "M ="])


def test_undefined_names_error_for_chosen_names() -> None:
    r = _last(["sigma := P/Ac", "sigma ="])
    assert r.status == "error" and "not defined" in r.error
    assert "P" in r.error and "Ac" in r.error
    r = _last(["P := Is^2 * R", "P ="])
    assert r.status == "error" and "not defined" in r.error


def test_unit_mismatch_errors() -> None:
    r = _last(["P := 5000 N", "L0 := 2 m", "Ac := 5 N", "E := 200 GPa", "dL := P*L0/(Ac*E)",
               "dL = mm"])
    assert r.status == "error" and "Units do not match" in r.error
    r = _last(["m_sub := 5 kg", "c_p := 4186 J/(kg*K)", "T_1 := 290 K", "T_2 := 350 Pa",
               "Q_sens := m_sub * c_p * (T_2 - T_1)", "Q_sens = kJ"])
    assert r.status == "error" and "Units do not match" in r.error
