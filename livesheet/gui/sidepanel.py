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

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..engine import dataio
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
    ("Algebra", "√", "sqrt(x)", "Square root of x. Type over x to replace it."),
    ("Algebra", "ⁿ√", "root(x, n)", "Nth root of x. Replace x and n."),
    ("Algebra", "x²", "^2", "Square"),
    ("Algebra", "xₙ", "_", "Subscript"),
    ("Calculus", "d/dx", "diff(f, x)",
     "Derivative of f with respect to x. Type your expression over f; rename x if needed."),
    ("Calculus", "∫", "integrate(f, x)", "Indefinite integral of f with respect to x."),
    ("Calculus", "∫ₐᵇ", "integrate(f, (x, a, b))",
     "Definite integral of f for x from a to b. Bounds can be numbers, names, values with "
     "units such as 0 m, or oo for infinity."),
    ("Calculus", "lim", "limit(f, x, 0)",
     "Limit of f as x approaches 0. Change 0 to another value, or to oo for infinity."),
]

# Span (start, end) to select, relative to the inserted text, after a template button inserts
# a complete closed template (spec 029). Tokens without an entry leave the caret after the text.
TOKEN_SELECTION: dict[str, tuple[int, int]] = {
    "sqrt(x)": (5, 6),
    "root(x, n)": (5, 6),
    "diff(f, x)": (5, 6),
    "integrate(f, x)": (10, 11),
    "integrate(f, (x, a, b))": (10, 11),
    "limit(f, x, 0)": (6, 7),
}

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

_SUM = "Summary statistics"
_DIST = "Distributions"
_TESTS = "Hypothesis tests"
_REG = "Regression"
_UNLESS = "Plain numbers only, no units."
_WHOLE = " k is a whole number of 0 or more."
_STAT_TOKENS: list[tuple[str, str, str, str]] = [
    (_SUM, "mean", "mean(v)", "Average of a list. Keeps the list's unit."),
    (_SUM, "median", "median(v)", "Middle value of a list."),
    (_SUM, "mode", "mode(v)", "Most frequent value; ties give the smallest."),
    (_SUM, "variance", "variance(v)", "Sample variance (divides by n-1). Unit squared."),
    (_SUM, "stdev", "stdev(v)", "Sample standard deviation (divides by n-1)."),
    (_SUM, "population_variance", "population_variance(v)",
     "Variance treating the list as the whole population (divides by n)."),
    (_SUM, "population_stdev", "population_stdev(v)",
     "Standard deviation of a whole population (divides by n)."),
    (_SUM, "quantile", "quantile(v, p)",
     "Value a fraction p (0 to 1) of the way through the sorted data."),
    (_SUM, "covariance", "covariance(u, w)", "Sample covariance of two equal-length lists."),
    (_SUM, "correlation", "correlation(u, w)",
     "Correlation of two equal-length lists, between -1 and 1. No unit."),
]


def _dist_rows(fam: str, pdf: str, pdf_args: str, cdf_args: str, q_args: str, s_args: str,
               discrete: bool) -> list[tuple[str, str, str, str]]:
    extra = _WHOLE if discrete else ""
    dens = "mass" if discrete else "density"
    return [
        (_DIST, f"{fam}_{pdf}", f"{fam}_{pdf}({pdf_args})",
         f"Probability {dens}: how likely a value is. {_UNLESS}{extra}"),
        (_DIST, f"{fam}_cdf", f"{fam}_cdf({cdf_args})",
         f"Cumulative: chance of being at or below the value. {_UNLESS}{extra}"),
        (_DIST, f"{fam}_quantile", f"{fam}_quantile({q_args})",
         f"Value below which the chance p lies (inverse of the cumulative). {_UNLESS}"),
        (_DIST, f"{fam}_sample", f"{fam}_sample({s_args})",
         f"Column vector of n reproducible random draws; seed is required. {_UNLESS}"),
    ]


_STAT_TOKENS += (
    _dist_rows("normal", "pdf", "x, mu, sigma", "x, mu, sigma", "p, mu, sigma",
               "mu, sigma, n, seed", False)
    + _dist_rows("uniform", "pdf", "x, a, b", "x, a, b", "p, a, b", "a, b, n, seed", False)
    + _dist_rows("binomial", "pmf", "k, n_trials, p", "k, n_trials, p", "q, n_trials, p",
                 "n_trials, p, n, seed", True)
    + _dist_rows("poisson", "pmf", "k, lambda_", "k, lambda_", "q, lambda_",
                 "lambda_, n, seed", True)
)

_STAT_TOKENS += [
    (_TESTS, "sample", "sample v in t1",
     "A measurement list for test t1. One line for a one-sample or chi-square test, two lines for "
     "a two-sample (Welch) test. Use the same name (t1) on every line of the test; rename it "
     "consistently."),
    (_TESTS, "expected", "expected counts in t1",
     "Expected counts (chi-square test only); must be positive, same length as the sample."),
    (_TESTS, "claim mean", "claim mean == 0 in t1",
     "One-sample t-test: the average equals this value (also < and > for one-sided)."),
    (_TESTS, "claim two means", "claim mean1 == mean2 in t1",
     "Welch two-sample t-test between the first and second sample line (also < and >)."),
    (_TESTS, "claim fits", "claim fits in t1",
     "Chi-square fit of the sample counts to the expected counts."),
    (_TESTS, "level", "level 0.05 in t1", "Significance level; optional, default 0.05."),
    (_TESTS, "verdict", "verdict in t1",
     "Runs test t1 from the lines above it; shows reject / fail to reject H0 and defines "
     "t1_statistic, t1_df, t1_pvalue. Use the same name as the sample lines."),
    (_REG, "fit_linear", "fit_linear(x, y)",
     "Best straight line through paired data; gives [intercept; slope]."),
    (_REG, "fit_poly", "fit_poly(x, y, 2)",
     "Best polynomial of the given degree (1 or more, less than the number of points); constant "
     "term first."),
    (_REG, "predict", "predict(c, x)", "Fitted value(s) at x for a coefficient vector c."),
    (_REG, "r_squared", "r_squared(c, x, y)",
     "How well the fit follows the data (1 is perfect)."),
]

_UNK = "Unknowns and constraints"
_SET = "Settings (optional)"
_RES = "Results"
_OPT_TOKENS: list[tuple[str, str, str, str]] = [
    (_UNK, "vary", "vary x from 1 in m1",
     "Declares unknowns and starting guesses (the guess's unit fixes the unknown's unit); several, "
     "comma separated."),
    (_UNK, "equation ==", "x^2 == 4 in m1", "An equation the solution must satisfy."),
    (_UNK, "limit <=", "x <= 10 in m1", "An upper limit; also usable as a <= x <= b."),
    (_UNK, "limit >=", "x >= 0 in m1", "A lower limit."),
    (_SET, "accuracy", "accuracy 1e-8 in m1", "Relative tolerance; default 1e-8."),
    (_SET, "steps", "steps 200 in m1", "Iteration limit; default 200."),
    (_RES, "settle", "settle in m1",
     "Solves the equations/limits from the guess; binds the unknowns. The starting guess is part "
     "of the problem; only a local solution is found."),
    (_RES, "least", "least x^2 in m1",
     "Smallest value of the expression while all constraints hold. The starting guess is part of "
     "the problem; only a local optimum is found."),
    (_RES, "most", "most x in m1",
     "Largest value of the expression while all constraints hold. The starting guess is part of "
     "the problem; only a local optimum is found."),
]

MATH_TOKENS.extend(_MECH_TOKENS + _ELEC_TOKENS + _CHEM_TOKENS + _STAT_TOKENS + _OPT_TOKENS)

# Each functional tab's MATH_TOKENS categories, in display order; a tab listing more than one
# category keeps sub-headers (today, only Elements bundles three originally distinct groups).
TAB_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Elements": ("Statements", "Constants", "Greek letters"),
    "Algebra": ("Algebra",),
    "Calculus": ("Calculus",),
    "Statistics": (_SUM, _DIST, _TESTS, _REG),
    "Optimization": (_UNK, _SET, _RES),
    "Mechanical": ("Statics", "Strength of Materials"),
    "Electrical": ("DC Circuits", "Power"),
    "Chemical": (_STOI, _GAS, _BAL, _TRANS, _KIN),
}

OUTLINE_EMPTY = ("No headings yet. Make the first line of a text region bold (Ctrl+B) "
                 "to list it here.")
OUTLINE_PLACEHOLDER = OUTLINE_EMPTY   # old name, kept for importers (spec 027)
OUTLINE_LABEL_MAX = 32
OUTLINE_DEBOUNCE_MS = 300
_BUTTON_STYLE = (
    "QPushButton { border: 1px solid rgba(128, 128, 128, 110);"
    " border-radius: 4px; padding: 3px 6px; }"
    "QPushButton:hover { border-color: rgba(128, 128, 128, 180); }"
)
_HEADER_STYLE = "color: #7a7a7a; font-weight: bold; font-size: 11px;"
DATA_EMPTY = "No data yet. Import a CSV file to use its columns in formulas."
DATA_PLACEHOLDER = DATA_EMPTY   # old name, kept for importers (spec 028)
DATA_NO_MATRIX = "No combined matrix (columns have different units)"

PLACEHOLDER_TABS: dict[str, str] = {}

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

    dataImportRequested = Signal()
    dataRefreshRequested = Signal(str)
    dataRenameRequested = Signal(str)
    dataRemoveRequested = Signal(str)

    MARGIN = 4
    BAND_MAX_ROWS = 4
    BAND_MAX_FRACTION = 0.25

    def __init__(self, insert_token: Callable[[str], None], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("side-panel")
        self._insert_token = insert_token
        self.symbol_buttons: dict[str, QPushButton] = {}
        self.outline_buttons: list[QPushButton] = []
        self.data_buttons: dict[str, QPushButton] = {}   # dynamic dataset buttons, by variable name
        self.data_headings: dict[str, QPushButton] = {}  # dataset name -> heading (selector)
        self.selected_dataset = ""
        self._sheet = None
        self._view = None
        self._outline_timer = QTimer(self)
        self._outline_timer.setSingleShot(True)
        self._outline_timer.setInterval(OUTLINE_DEBOUNCE_MS)
        self._outline_timer.timeout.connect(self._rebuild_if_selected)

        self.tabs = _TabModel()
        self.tabs.setObjectName("side-panel-tabs")
        self.tabs.tabBar().hide()
        for name in TAB_ORDER:
            if name in TAB_CATEGORIES:
                self.tabs.addTab(self._build_functional_tab(TAB_CATEGORIES[name]), name)
            elif name == "Outline":
                self._outline_scroll = self._new_outline_scroll(self._outline_message())
                self.tabs.addTab(self._outline_scroll, name)
            elif name == "Data":
                self._data_scroll = self._new_outline_scroll(QWidget())
                self.tabs.addTab(self._data_scroll, name)
                self.rebuild_data()
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
        self.tabs.currentChanged.connect(lambda _i: self._rebuild_if_selected())
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
                header.setStyleSheet(_HEADER_STYLE)
                layout.add_widget(header, new_row=True)
                first = False
            for _category, label, token, tip in items:
                btn = QPushButton(label)
                btn.setStyleSheet(_BUTTON_STYLE)
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

    # -- outline tab (spec 027) -----------------------------------------------------

    @staticmethod
    def _new_outline_scroll(content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _outline_message() -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        label = QLabel(OUTLINE_EMPTY)
        label.setObjectName("outline-empty")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #9a9a9a;")
        lay.addWidget(label)
        return box

    def attach_sheet(self, sheet, view) -> None:
        """Connect the Outline tab to the worksheet and its view."""
        self._sheet = sheet
        self._view = view
        sheet.outlineDirty.connect(self._on_outline_dirty)
        sheet.datasetsChanged.connect(self.rebuild_data)
        self.rebuild_data()

    def _outline_selected(self) -> bool:
        return self.tabs.tabText(self.tabs.currentIndex()) == "Outline"

    def _on_outline_dirty(self) -> None:
        if self._outline_selected():
            self._outline_timer.start()

    def _rebuild_if_selected(self) -> None:
        self._outline_timer.stop()
        if self._outline_selected() and self._sheet is not None:
            self.rebuild_outline()

    @staticmethod
    def _elide(text: str) -> str:
        if len(text) <= OUTLINE_LABEL_MAX:
            return text
        return text[:OUTLINE_LABEL_MAX - 1] + "\u2026"

    def rebuild_outline(self) -> None:
        """Recompute the heading list from the sheet and replace the Outline page content."""
        self.outline_buttons = []
        headings = self._sheet.headings() if self._sheet is not None else []
        if not headings:
            content = self._outline_message()
        else:
            content = QWidget()
            layout = FlowLayout(content, margin=6, spacing=4)
            paged = bool(self._sheet.page_break_ys())
            last_page = None
            for region, page, text in headings:
                if paged and page != last_page:
                    header = QLabel(f"Page {page + 1}")
                    header.setStyleSheet(_HEADER_STYLE)
                    layout.add_widget(header, new_row=True)
                    last_page = page
                btn = QPushButton(self._elide(text))
                btn.setStyleSheet(_BUTTON_STYLE)
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.setToolTip(f"{text}\nPage {page + 1}")
                btn.setAccessibleName(text)
                btn.clicked.connect(lambda _c=False, r=region: self._go_to(r))
                layout.add_widget(btn)
                self.outline_buttons.append(btn)
        self._outline_scroll.setWidget(content)
        self.update_band_height()

    def _go_to(self, region) -> None:
        if self._sheet is not None:
            self._sheet.reveal_region(region)   # a stale region is a silent no-op

    # -- data tab (spec 028) ----------------------------------------------------------

    def select_dataset(self, name: str) -> None:
        self.selected_dataset = name if name in self.data_headings else ""
        for n, btn in self.data_headings.items():
            btn.setChecked(n == self.selected_dataset)
        self._update_data_buttons()

    def _update_data_buttons(self) -> None:
        on = bool(self.selected_dataset)
        for btn in (self.data_refresh_button, self.data_rename_button, self.data_remove_button):
            btn.setEnabled(on)

    def _data_action(self, signal) -> None:
        if self.selected_dataset:
            signal.emit(self.selected_dataset)

    @staticmethod
    def _dataset_heading(ds) -> str:
        shape = f"{ds.row_count} rows x {len(ds.columns)} columns"
        return f"{ds.name} - {shape}" + (f" - {Path(ds.source).name}" if ds.source else "")

    @staticmethod
    def _column_tip(ds, col) -> str:
        if col.kind != "number":
            return "Text column, not usable in formulas"
        unit = f", unit {col.unit}" if col.unit else ""
        return (f"Column {col.name}, {len(col.values)} values{unit} "
                f"(min {min(col.values):g}, max {max(col.values):g})")

    def rebuild_data(self) -> None:
        """Rebuild the Data page from the sheet's datasets (buttons live outside symbol_buttons)."""
        datasets = list(self._sheet.datasets) if self._sheet is not None else []
        self.data_buttons = {}
        self.data_headings = {}
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)
        top = QHBoxLayout()
        self.data_import_button = QPushButton("Import...")
        self.data_refresh_button = QPushButton("Refresh")
        self.data_rename_button = QPushButton("Rename")
        self.data_remove_button = QPushButton("Remove")
        for btn in (self.data_import_button, self.data_refresh_button, self.data_rename_button,
                    self.data_remove_button):
            btn.setStyleSheet(_BUTTON_STYLE)
            top.addWidget(btn)
        top.addStretch(1)
        self.data_import_button.clicked.connect(lambda _c=False: self.dataImportRequested.emit())
        self.data_refresh_button.clicked.connect(
            lambda _c=False: self._data_action(self.dataRefreshRequested))
        self.data_rename_button.clicked.connect(
            lambda _c=False: self._data_action(self.dataRenameRequested))
        self.data_remove_button.clicked.connect(
            lambda _c=False: self._data_action(self.dataRemoveRequested))
        outer.addLayout(top)
        self.data_empty_label = None
        if not datasets:
            self.data_empty_label = QLabel(DATA_EMPTY)
            self.data_empty_label.setObjectName("data-empty")
            self.data_empty_label.setWordWrap(True)
            self.data_empty_label.setStyleSheet("color: #9a9a9a;")
            outer.addWidget(self.data_empty_label)
        for ds in datasets:
            outer.addWidget(self._dataset_block(ds))
        outer.addStretch(1)
        self._data_scroll.setWidget(content)
        self.select_dataset(self.selected_dataset)
        if hasattr(self, "band"):
            self.update_band_height()

    def _dataset_block(self, ds) -> QWidget:
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        heading = QPushButton(self._dataset_heading(ds))
        heading.setFlat(True)
        heading.setCheckable(True)
        heading.setStyleSheet(_HEADER_STYLE + " text-align: left; border: none;")
        opts = ds.options
        heading.setToolTip(f"{ds.source or '(no source file)'}\ndelimiter {opts.delimiter!r}, "
                           f"decimal {opts.decimal!r}, header {opts.has_header}, "
                           f"skip {opts.skip_lines}, {opts.encoding}")
        heading.clicked.connect(lambda _c=False, n=ds.name: self.select_dataset(n))
        self.data_headings[ds.name] = heading
        lay.addWidget(heading)
        row = QWidget()
        flow = FlowLayout(row, margin=0, spacing=4)
        for col in ds.columns:
            var = dataio.column_variable_name(ds, col)
            btn = QPushButton(var)
            btn.setStyleSheet(_BUTTON_STYLE)
            btn.setToolTip(self._column_tip(ds, col))
            if col.kind == "number":
                btn.clicked.connect(lambda _c=False, t=var: self._insert_token(t))
            else:
                btn.setEnabled(False)
            flow.add_widget(btn)
            self.data_buttons[var] = btn
        if dataio.combined_matrix_available(ds):
            nums = sum(c.kind == "number" for c in ds.columns)
            btn = QPushButton(ds.name)
            btn.setStyleSheet(_BUTTON_STYLE)
            btn.setToolTip(f"{ds.row_count} x {nums} matrix of all numeric columns")
            btn.clicked.connect(lambda _c=False, t=ds.name: self._insert_token(t))
            flow.add_widget(btn)
            self.data_buttons[ds.name] = btn
        lay.addWidget(row)
        if not dataio.combined_matrix_available(ds):
            note = QLabel(DATA_NO_MATRIX)
            note.setObjectName("data-no-matrix")
            note.setStyleSheet("color: #9a9a9a; font-size: 11px;")
            lay.addWidget(note)
        return block


__all__ = [
    "SidePanel", "MATH_TOKENS", "TAB_CATEGORIES", "TAB_ORDER", "PLACEHOLDER_TABS",
    "OUTLINE_PLACEHOLDER", "DATA_PLACEHOLDER", "DATA_EMPTY", "DATA_NO_MATRIX"
]
