"""The window-wide side panel (wrapping tab strip + button band, spec 022): a tabbed Elements/Algebra/Calculus/Statistics/Optimization/
Outline/Data shell (spec 007 phase G2; restructured into 7 category tabs by spec 011).

``MATH_TOKENS`` is the single list of insertable math tokens -- same ``(category, label, token,
tip)`` shape spec 007 shipped, now also carrying the 33 new Greek-letter entries (read straight
from ``engine/formatting.py``'s own ``GREEK`` dict, so the glyph/name list cannot drift from the
display-side mapping) and the 1 new Subscript entry. ``TAB_CATEGORIES`` maps each of the three
functional tabs to the ``MATH_TOKENS`` categories it shows; only a tab backed by more than one
category (today: Elements) keeps the small grey sub-header labels the old Symbols tab used.
``PLACEHOLDER_TABS`` gives the four non-functional tabs' messages, in ``TAB_ORDER``.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..engine.formatting import GREEK
from .tabstrip import FlowLayout, TabStrip

# 23 lowercase + 10 uppercase buttons, in the dict's own (Greek-alphabet) insertion order; the
# "lamda"/"lambda" alias pair collapses to one button (spelled "lambda"); lowercase "pi" is not
# a GREEK key at all (it is already the Constants tab's own "pi" button).
_GREEK_LOWER = [(name, glyph) for name, glyph in GREEK.items() if name.islower() and name != "lamda"]
_GREEK_UPPER = [(name, glyph) for name, glyph in GREEK.items() if not name.islower()]

MATH_TOKENS: list[tuple[str, str, str, str]] = [
    ("Statements", ":=", ":= ", "Definition"),
    ("Statements", "≡", "≡ ", "Global definition"),
    ("Statements", "=", " =", "Evaluate numerically"),
    ("Statements", "→", " → ", "Evaluate symbolically"),
    ("Constants", "π", "pi", "Pi"),
    ("Constants", "e", "e", "Euler's number"),
    ("Constants", "i", "I", "Imaginary unit"),
    *[("Greek letters", glyph, name, name) for name, glyph in _GREEK_LOWER + _GREEK_UPPER],
    ("Algebra", "√", "sqrt(", "Square root"),
    ("Algebra", "ⁿ√", "root(", "Nth root: root(expr, n)"),
    ("Algebra", "x²", "^2", "Square"),
    ("Algebra", "xₙ", "_", "Subscript"),
    ("Calculus", "d/dx", "diff(", "Derivative: diff(expr, x)"),
    ("Calculus", "∫", "integrate(", "Integral: integrate(expr, x) or (x, a, b)"),
]

_MECH_TOKENS: list[tuple[str, str, str, str]] = [
    ("Statics", "Resultant (2 forces)", "R := sqrt(P1^2 + P2^2 + 2*P1*P2*cos(theta))",
     "Resultant of two concurrent forces (law of cosines). P1, P2 in N; theta in rad (or e.g. "
     "30*deg); R in N."),
    ("Statics", "Force, x-component", "Fx := P*cos(theta)",
     "Horizontal component of a force P at angle theta from the x-axis. P in N; Fx in N."),
    ("Statics", "Force, y-component", "Fy := P*sin(theta)",
     "Vertical component of a force P at angle theta from the x-axis. P in N; Fy in N."),
    ("Statics", "Moment of a force", "M := P*d",
     "Moment of a force P about a point, at perpendicular distance d from its line of action. "
     "P in N; d in m; M in N*m. Note: a bare 'M =' displays J (same base dimension); write "
     "'M = N*m' to see N*m."),
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

_ELEC_TOKENS: list[tuple[str, str, str, str]] = [
    ("DC Circuits", "Vs := Is * R", "Vs := Is * R",
     "Ohm's law - voltage from current and resistance (Vs in volts, Is in amps, R in ohms)"),
    ("DC Circuits", "Is := Vs / R", "Is := Vs / R",
     "Ohm's law - current from voltage and resistance"),
    ("DC Circuits", "R := Vs / Is", "R := Vs / Is",
     "Ohm's law - resistance from voltage and current"),
    ("DC Circuits", "R_total := R1 + R2", "R_total := R1 + R2",
     "Resistors in series - equivalent resistance of two resistors"),
    ("DC Circuits", "R_total := 1 / (1/R1 + 1/R2)", "R_total := 1 / (1/R1 + 1/R2)",
     "Resistors in parallel - equivalent resistance of two resistors"),
    ("DC Circuits", "V_out := V_in * R2 / (R1 + R2)", "V_out := V_in * R2 / (R1 + R2)",
     "Voltage divider - output voltage measured across R2"),
    ("DC Circuits", "I1 := I_total * R2 / (R1 + R2)", "I1 := I_total * R2 / (R1 + R2)",
     "Current divider - current through the R1 branch of two resistors in parallel"),
    ("Power", "P := Vs * Is", "P := Vs * Is", "Electrical power from voltage and current"),
    ("Power", "P := Is^2 * R", "P := Is^2 * R", "Electrical power from current and resistance"),
    ("Power", "P := Vs^2 / R", "P := Vs^2 / R", "Electrical power from voltage and resistance"),
    ("Power", "E := P * t", "E := P * t", "Electrical energy from power and time"),
]

_STOI = "Stoichiometry & Composition"
_GAS = "Ideal Gas & Thermodynamic State"
_BAL = "Mass & Energy Balances"
_TRANS = "Fluid & Heat/Mass Transport"
_KIN = "Reaction Kinetics"
_CHEM_TOKENS: list[tuple[str, str, str, str]] = [
    (_STOI, "n", "n_A := m_A / M_A", "Amount of substance from mass and molar mass"),
    (_STOI, "w", "w_A := m_A / m_total", "Mass fraction of a component in a mixture"),
    (_STOI, "x", "x_A := n_A / n_total", "Mole fraction of a component in a mixture"),
    (_STOI, "c", "c_A := n_A / V_sol", "Molar concentration (amount per solution volume)"),
    (_GAS, "R", "R_gas := 8.314 J/(mol*K)", "Universal gas constant (SI)"),
    (_GAS, "PV=nRT", "P_gas := n_gas * R_gas * T_gas / V_gas", "Ideal gas law"),
    (_GAS, "rho_gas", "rho_gas := P_gas * M_gas / (R_gas * T_gas)",
     "Ideal-gas density from pressure, molar mass, temperature"),
    (_GAS, "Q_sens", "Q_sens := m_sub * c_p * (T_2 - T_1)",
     "Sensible heat for a temperature change (no phase change)"),
    (_GAS, "Q_lat", "Q_lat := m_sub * L_phase",
     "Latent heat for a phase change at constant temperature"),
    (_BAL, "m-dot bal.", "m_out := m_in", "Steady-state overall mass balance (no accumulation)"),
    (_BAL, "comp. bal.", "m_A_out := m_A_in + m_A_gen - m_A_cons",
     "Steady-state component mass balance with reaction"),
    (_BAL, "dm/dt", "dm_dt := m_in_rate - m_out_rate", "Dynamic (unsteady) overall mass balance"),
    (_BAL, "energy bal.", "Q_rate := m_flow_rate * (h_out - h_in) + W_rate",
     "Steady-state open-system energy balance (no KE/PE change)"),
    (_TRANS, "Re", "Re := rho_fluid * v_flow * D_pipe / mu_fluid",
     "Reynolds number (inertial/viscous force ratio)"),
    (_TRANS, "Q_cond", "Q_cond := k_therm * A_surf * (T_hot - T_cold) / L_thick",
     "Steady 1-D conductive heat flow across a slab"),
    (_TRANS, "Q_conv", "Q_conv := h_conv * A_surf * (T_wall - T_fluid)",
     "Convective heat flow at a surface"),
    (_TRANS, "J_diff", "J_diff := D_ab * (c_A1 - c_A2) / L_film",
     "Steady 1-D diffusive molar flux across a film"),
    (_KIN, "rate law", "r_rxn := k_rate * C_A^n_order", "Power-law reaction rate expression"),
    (_KIN, "Arrhenius", "k_rate := A_arr * exp(-E_act / (R_gas * T_rxn))",
     "Temperature dependence of a rate constant"),
    (_KIN, "half-life", "t_half := ln(2) / k_rate", "Half-life of a first-order reaction"),
    (_KIN, "conversion", "X_A := (C_A0 - C_A) / C_A0", "Fractional conversion of a reactant"),
]

MATH_TOKENS.extend(_MECH_TOKENS + _ELEC_TOKENS + _CHEM_TOKENS)

# Each functional tab's MATH_TOKENS categories, in display order; a tab listing more than one
# category keeps sub-headers (today, only Elements bundles three originally distinct groups).
TAB_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Elements": ("Statements", "Constants", "Greek letters"),
    "Algebra": ("Algebra",),
    "Calculus": ("Calculus",),
    "Mechanical": ("Statics", "Strength of Materials"),
    "Electrical": ("DC Circuits", "Power"),
    "Chemical": (_STOI, _GAS, _BAL, _TRANS, _KIN),
}

STATISTICS_PLACEHOLDER = ("Statistical tools (descriptive statistics, distributions, hypothesis "
                          "tests, regression) will appear here once available.")
OPTIMIZATION_PLACEHOLDER = ("Optimization tools (nonlinear and constrained optimization) will "
                            "appear here once available.")
OUTLINE_PLACEHOLDER = "Document outline will appear here once headings are available."
DATA_PLACEHOLDER = "Imported datasets will appear here once available."

PLACEHOLDER_TABS: dict[str, str] = {
    "Statistics": STATISTICS_PLACEHOLDER,
    "Optimization": OPTIMIZATION_PLACEHOLDER,
    "Outline": OUTLINE_PLACEHOLDER,
    "Data": DATA_PLACEHOLDER,
}

TAB_ORDER: tuple[str, ...] = (
    "Elements", "Algebra", "Calculus", "Statistics", "Optimization", "Mechanical", "Electrical",
    "Chemical", "Outline", "Data",
)


def _build_placeholder_tab(message: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(message)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    label.setStyleSheet("color: #9a9a9a;")
    layout.addWidget(label)
    return widget


class _TabModel(QTabWidget):
    """The tab model (native bar hidden; the window-wide strip drives it). Announces structural
    changes so the strip can rebuild its buttons."""

    structureChanged = Signal()

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self.structureChanged.emit()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self.structureChanged.emit()


class SidePanel(QWidget):
    """Window-wide wrapping tab strip over a horizontal button band (spec 022).

    Elements/Algebra/Calculus/... (functional) and Statistics/Optimization/Outline/Data
    (placeholders) are the pages of ``tabs`` (a QTabWidget with its native bar hidden, hosted in
    the band). The strip mirrors and drives ``tabs``.
    """

    MARGIN = 4
    BAND_MAX_ROWS = 4
    BAND_MAX_FRACTION = 0.25

    def __init__(self, insert_token: Callable[[str], None], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("side-panel")
        self._insert_token = insert_token
        self.symbol_buttons: dict[str, QPushButton] = {}

        self.tabs = _TabModel()
        self.tabs.setObjectName("side-panel-tabs")
        self.tabs.tabBar().hide()
        for name in TAB_ORDER:
            if name in TAB_CATEGORIES:
                self.tabs.addTab(self._build_functional_tab(TAB_CATEGORIES[name]), name)
            else:
                self.tabs.addTab(_build_placeholder_tab(PLACEHOLDER_TABS[name]), name)

        self.strip = TabStrip()
        self.strip.setObjectName("side-panel-strip")
        self.strip.setAccessibleName("Side panel categories")
        self.band = QWidget()
        self.band.setObjectName("side-panel-band")
        band_layout = QVBoxLayout(self.band)
        band_layout.setContentsMargins(0, 0, 0, 0)
        band_layout.addWidget(self.tabs)

        layout = QVBoxLayout(self)
        m = self.MARGIN
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(2)
        layout.addWidget(self.strip)
        layout.addWidget(self.band)

        self._toggle_action = QAction("Side Panel", self)
        self._toggle_action.setCheckable(True)
        self._toggle_action.setChecked(True)
        self._toggle_action.toggled.connect(self.setVisible)

        self.strip.tabRequested.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.strip.set_current)
        self.tabs.structureChanged.connect(self._sync_strip)
        self._sync_strip()

    def toggleViewAction(self) -> QAction:
        """Checkable View-menu action showing/hiding strip and band together."""
        return self._toggle_action

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if self._toggle_action.isChecked() != visible:
            self._toggle_action.blockSignals(True)
            self._toggle_action.setChecked(visible)
            self._toggle_action.blockSignals(False)

    def _sync_strip(self) -> None:
        labels = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        self.strip.set_labels(labels, self.tabs.currentIndex())
        self.update_band_height()

    # -- band height --------------------------------------------------------------

    def _page_height(self, page: QWidget, width: int) -> int:
        if isinstance(page, QScrollArea) and page.widget() is not None:
            inner = page.widget().layout()
            if inner is not None and inner.hasHeightForWidth():
                return inner.heightForWidth(width - 2 * page.frameWidth()) + 2 * page.frameWidth()
        layout = page.layout()
        if layout is not None and layout.hasHeightForWidth():
            return layout.heightForWidth(width)
        return page.sizeHint().height()

    def band_clamp(self) -> int:
        """Maximum band height: 4 button rows or 25% of the window height, whichever is larger."""
        row_h = max((b.sizeHint().height() for b in self.symbol_buttons.values()), default=24)
        rows = self.BAND_MAX_ROWS * (row_h + 4) + 12
        window_h = self.window().height() if self.window() is not None else 0
        return max(rows, int(window_h * self.BAND_MAX_FRACTION))

    def update_band_height(self) -> None:
        """Band height = tallest page at the current width, clamped; independent of the tab."""
        width = max(self.width() - 2 * self.MARGIN, 1)
        needed = max((self._page_height(self.tabs.widget(i), width)
                      for i in range(self.tabs.count())), default=0) + 6
        height = min(needed, self.band_clamp())
        if self.band.height() != height or self.band.minimumHeight() != height:
            self.band.setFixedHeight(height)
            self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_band_height()

    # -- pages --------------------------------------------------------------------

    def _build_functional_tab(self, categories: tuple[str, ...]) -> QWidget:
        container = QWidget()
        layout = FlowLayout(container, margin=6, spacing=4)
        show_headers = len(categories) > 1
        for category in categories:
            items = [t for t in MATH_TOKENS if t[0] == category]
            if not items:
                continue
            first = True
            if show_headers:
                header = QLabel(category)
                header.setStyleSheet("color: #7a7a7a; font-weight: bold; font-size: 11px;")
                layout.add_widget(header, new_row=True)
                first = False
            for _category, label, token, tip in items:
                btn = QPushButton(label)
                btn.setStyleSheet(
                    "QPushButton { border: 1px solid rgba(128, 128, 128, 110);"
                    " border-radius: 4px; padding: 3px 6px; }"
                    "QPushButton:hover { border-color: rgba(128, 128, 128, 180); }"
                )
                btn.setToolTip(tip)
                btn.clicked.connect(lambda _checked=False, t=token: self._insert_token(t))
                layout.add_widget(btn, new_row=first and layout.count() > 0)
                first = False
                self.symbol_buttons[label] = btn
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        return scroll


__all__ = [
    "SidePanel", "MATH_TOKENS", "TAB_CATEGORIES", "TAB_ORDER", "PLACEHOLDER_TABS",
    "OUTLINE_PLACEHOLDER", "DATA_PLACEHOLDER", "STATISTICS_PLACEHOLDER", "OPTIMIZATION_PLACEHOLDER",
]
