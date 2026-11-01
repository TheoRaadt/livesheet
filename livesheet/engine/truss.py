"""2D pin-jointed truss analysis: direct stiffness method (spec 015, phase F1).

Regions join a model through a trailing ``in <name>`` tag, collected by
``evaluator.py``'s ``_run_model`` and handed to ``build()`` here, parallel in spirit
to ``solver.py``/``odesolver.py``. ``numpy.linalg.solve`` does the one direct linear
solve (no iteration, so there is no ``accuracy``/``steps`` setting to read, unlike
those two modules).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import sympy as sp
from sympy.core.function import AppliedUndef

from . import matrices
from .matrices import LMat, attach_units
from .syntax import Statement, StatementError
from .units import Measured, UnitError, UNITS, measure

if TYPE_CHECKING:  # pragma: no cover
    from .evaluator import Engine

_LENGTH_DIMS = measure(UNITS["m"]).dims
_AREA_DIMS = measure(UNITS["m"] ** 2).dims
_PRESSURE_DIMS = measure(UNITS["Pa"]).dims
_FORCE_DIMS = measure(UNITS["N"]).dims


@dataclass
class Model:
    name: str
    coords: list[tuple[float, float]]          # SI metres, one (x, y) per node
    elements: list[tuple[int, int]]             # 0-based node index pairs, one per element
    area: list[float]                           # SI m^2, one per element
    modulus: list[float]                        # SI Pa, one per element
    supports: dict[tuple[int, str], float] = field(default_factory=dict)
    # (0-based node, axis letter) -> prescribed SI displacement (0.0 for a bare fix)
    loads: dict[tuple[int, str], float] = field(default_factory=dict)
    # (0-based node, axis letter) -> SI force

    @property
    def n_nodes(self) -> int:
        return len(self.coords)

    @property
    def n_elements(self) -> int:
        return len(self.elements)


@dataclass
class Outcome:
    n_nodes: int
    n_elements: int
    displacement: LMat     # Nx2, length unit
    reaction: LMat         # Nx2, force unit
    force: LMat            # Mx1, force unit, tension positive
    stress: LMat           # Mx1, pressure unit
    max_displacement: Measured


def _check_defined(value) -> None:
    free = getattr(value, "free_symbols", set())
    undef = sorted({str(s) for s in free} | {f.func.__name__ for f in value.atoms(AppliedUndef)}) \
        if isinstance(value, sp.Basic) else []
    if undef:
        names = ", ".join(undef)
        raise StatementError(f"{names} {'is' if len(undef) == 1 else 'are'} not defined")


# -- build: gather nodes/elements/area/modulus/support/load regions into one Model ------

def build(engine: "Engine", model: str, regions: list[Statement], env: dict) -> Model:
    nodes_st = elements_st = area_st = modulus_st = None
    support_sts: list[Statement] = []
    load_sts: list[Statement] = []
    for st in regions:
        if st.kind == "model_truss_nodes":
            if nodes_st is not None:
                raise StatementError(f'Node coordinates already declared for truss model "{model}"')
            nodes_st = st
        elif st.kind == "model_truss_elements":
            if elements_st is not None:
                raise StatementError(f'Element connectivity already declared for truss model "{model}"')
            elements_st = st
        elif st.kind == "model_truss_area":
            if area_st is not None:
                raise StatementError(f'Cross-section area already declared for truss model "{model}"')
            area_st = st
        elif st.kind == "model_truss_modulus":
            if modulus_st is not None:
                raise StatementError(f'Elastic modulus already declared for truss model "{model}"')
            modulus_st = st
        elif st.kind == "model_support":
            support_sts.append(st)
        elif st.kind == "model_load":
            load_sts.append(st)

    if nodes_st is None:
        raise StatementError(f'No node coordinates declared for truss model "{model}"')
    if elements_st is None:
        raise StatementError(f'No element connectivity declared for truss model "{model}"')
    if area_st is None:
        raise StatementError(f'No cross-section area declared for truss model "{model}"')
    if modulus_st is None:
        raise StatementError(f'No elastic modulus declared for truss model "{model}"')

    coords = _read_nodes(engine, nodes_st.expr, env)
    elements = _read_elements(engine, elements_st.expr, env, len(coords))
    _check_lengths(elements, coords)
    area = _read_per_element("area", "cross-section area", "an area",
                             area_st.expr, engine, env, len(elements), _AREA_DIMS)
    modulus = _read_per_element("modulus", "elastic modulus", "a pressure",
                                modulus_st.expr, engine, env, len(elements), _PRESSURE_DIMS)
    supports = _read_supports(engine, model, support_sts, env, len(coords))
    loads = _read_loads(engine, model, load_sts, env, len(coords))
    return Model(model, coords, elements, area, modulus, supports, loads)


def _read_nodes(engine: "Engine", expr: str, env: dict) -> list[tuple[float, float]]:
    value = engine.parse(expr, env)
    if not isinstance(value, sp.MatrixBase):
        _check_defined(value)
        raise StatementError("node coordinates must be a matrix")
    _check_defined(value)
    if value.cols != 2:
        raise StatementError(f"node coordinates must have 2 columns (got {value.cols})")
    if value.rows < 1:
        raise StatementError("node coordinates must have at least 1 row")
    mag, dims = matrices.split_units(value)
    if dims != _LENGTH_DIMS:
        raise UnitError("Units do not match: node coordinates must be a length")
    return [(float(mag[r, 0]), float(mag[r, 1])) for r in range(mag.rows)]


def _read_elements(engine: "Engine", expr: str, env: dict, n_nodes: int) -> list[tuple[int, int]]:
    value = engine.parse(expr, env)
    if not isinstance(value, sp.MatrixBase):
        _check_defined(value)
        raise StatementError("element connectivity must be a matrix")
    _check_defined(value)
    if value.cols != 2:
        raise StatementError(f"element connectivity must have 2 columns (got {value.cols})")
    if value.rows < 1:
        raise StatementError("element connectivity must have at least 1 row")
    elements: list[tuple[int, int]] = []
    for k in range(value.rows):
        pair = []
        for c in range(2):
            meas = measure(value[k, c])
            if meas.dims:
                raise UnitError("Units do not match: element node index must be dimensionless")
            num = meas.magnitude
            if not num.is_Integer:
                raise StatementError(f"Element {k + 1}: node index must be a whole number")
            node1 = int(num)
            if node1 < 1 or node1 > n_nodes:
                raise StatementError(f"Element {k + 1}: node {node1} is out of range 1..{n_nodes}")
            pair.append(node1 - 1)
        elements.append((pair[0], pair[1]))
    return elements


def _check_lengths(elements: list[tuple[int, int]], coords: list[tuple[float, float]]) -> None:
    for k, (i, j) in enumerate(elements, start=1):
        dx = coords[j][0] - coords[i][0]
        dy = coords[j][1] - coords[i][1]
        if math.hypot(dx, dy) <= 1e-12:
            raise StatementError(f"Element {k} has zero length (nodes {i + 1} and {j + 1} coincide)")


def _read_per_element(word: str, label: str, unit_phrase: str, expr: str, engine: "Engine",
                      env: dict, n_elements: int, expected_dims: tuple) -> list[float]:
    value = engine.parse(expr, env)
    if isinstance(value, sp.MatrixBase):
        _check_defined(value)
        if not (value.rows == 1 or value.cols == 1):
            raise StatementError(f"{word} must be a scalar or a vector")
        vals = list(value)
        n = len(vals)
        if n not in (1, n_elements):
            raise StatementError(f"{word} has {n} values but there are {n_elements} elements "
                                 "(use one value or exactly one per element)")
        mags = [_checked_dims(v, expected_dims, label, unit_phrase) for v in vals]
        return mags * n_elements if n == 1 else mags
    _check_defined(value)
    mag = _checked_dims(value, expected_dims, label, unit_phrase)
    return [mag] * n_elements


def _checked_dims(value, expected_dims: tuple, label: str, unit_phrase: str) -> float:
    meas = measure(value)
    if meas.dims != expected_dims:
        raise UnitError(f"Units do not match: {label} must be {unit_phrase}")
    return float(meas.magnitude)


def _node_index(value, word: str, n_nodes: int) -> int:
    meas = measure(value)
    if meas.dims:
        raise UnitError(f"Units do not match: {word} node index must be dimensionless")
    num = meas.magnitude
    if not num.is_Integer:
        raise StatementError(f"{word} node index must be a whole number")
    node1 = int(num)
    if node1 < 1 or node1 > n_nodes:
        raise StatementError(f"{word} references node {node1}, out of range 1..{n_nodes}")
    return node1 - 1


def _read_supports(engine: "Engine", model: str, support_sts: list[Statement], env: dict,
                   n_nodes: int) -> dict[tuple[int, str], float]:
    fixed: dict[tuple[int, str], float] = {}
    for st in support_sts:
        node_val = engine.parse(st.node, env)
        _check_defined(node_val)
        node0 = _node_index(node_val, "support", n_nodes)
        for axis, value_text in st.axes:
            key = (node0, axis)
            if key in fixed:
                raise StatementError(f'Node {node0 + 1} has "{axis}" fixed twice in truss model "{model}"')
            if value_text:
                value = engine.parse(value_text, env, keep_units=True)
                _check_defined(value)
                meas = measure(value)
                if meas.dims != _LENGTH_DIMS and not (meas.magnitude == 0 and not meas.dims):
                    raise UnitError(f'Units do not match: support value for "{axis}" must be a length')
                fixed[key] = float(meas.magnitude)
            else:
                fixed[key] = 0.0
    return fixed


def _read_loads(engine: "Engine", model: str, load_sts: list[Statement], env: dict,
                n_nodes: int) -> dict[tuple[int, str], float]:
    loads: dict[tuple[int, str], float] = {}
    loaded_by: dict[int, Statement] = {}
    for st in load_sts:
        node_val = engine.parse(st.node, env)
        _check_defined(node_val)
        node0 = _node_index(node_val, "load", n_nodes)
        owner = loaded_by.get(node0)
        if owner is not None and owner is not st:
            raise StatementError(f'Node {node0 + 1} is loaded by more than one "load" line in truss model "{model}"')
        loaded_by[node0] = st
        for axis, value_text in st.axes:
            value = engine.parse(value_text, env, keep_units=True)
            _check_defined(value)
            meas = measure(value)
            if meas.dims != _FORCE_DIMS and not (meas.magnitude == 0 and not meas.dims):
                raise UnitError(f'Units do not match: load "f{axis}" must be a force')
            loads[(node0, axis)] = loads.get((node0, axis), 0.0) + float(meas.magnitude)
    return loads


# -- solve: assembly, DOF elimination, numpy.linalg.solve, post-processing --------------

def _element_geometry(model: Model):
    for (i, j), area, modulus in zip(model.elements, model.area, model.modulus):
        xi, yi = model.coords[i]
        xj, yj = model.coords[j]
        dx, dy = xj - xi, yj - yi
        length = math.hypot(dx, dy)
        yield (i, j), area, modulus, length, dx / length, dy / length


def _assemble(model: Model):
    import numpy as np

    ndof = 2 * model.n_nodes
    k_global = np.zeros((ndof, ndof))
    geometry = list(_element_geometry(model))
    for (i, j), area, modulus, length, c, s in geometry:
        k = modulus * area / length
        k_local = k * np.array([
            [c * c, c * s, -c * c, -c * s],
            [c * s, s * s, -c * s, -s * s],
            [-c * c, -c * s, c * c, c * s],
            [-c * s, -s * s, c * s, s * s],
        ])
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        for a in range(4):
            for b in range(4):
                k_global[dofs[a], dofs[b]] += k_local[a, b]
    return k_global, geometry


def solve(model: Model) -> Outcome:
    import numpy as np

    k_global, geometry = _assemble(model)
    ndof = 2 * model.n_nodes

    force = np.zeros(ndof)
    for (node0, axis), value in model.loads.items():
        force[2 * node0 + (0 if axis == "x" else 1)] += value

    prescribed: dict[int, float] = {}
    for (node0, axis), value in model.supports.items():
        prescribed[2 * node0 + (0 if axis == "x" else 1)] = value

    free = [d for d in range(ndof) if d not in prescribed]
    pres = sorted(prescribed)
    k_ff = k_global[np.ix_(free, free)]
    k_fp = k_global[np.ix_(free, pres)]
    u_p = np.array([prescribed[d] for d in pres])
    f_f = force[free] - (k_fp @ u_p if pres else 0.0)

    try:
        u_f = np.linalg.solve(k_ff, f_f) if free else np.array([])
    except np.linalg.LinAlgError:
        raise StatementError(f'Stiffness matrix is singular: truss model "{model.name}" is '
                             "unstable or underconstrained") from None

    displacement = np.zeros(ndof)
    for d, v in zip(free, u_f):
        displacement[d] = v
    for d in pres:
        displacement[d] = prescribed[d]

    reaction = k_global @ displacement - force

    forces: list[float] = []
    stresses: list[float] = []
    for (i, j), area, modulus, length, c, s in geometry:
        elongation = (displacement[2 * j] - displacement[2 * i]) * c \
            + (displacement[2 * j + 1] - displacement[2 * i + 1]) * s
        axial = modulus * area / length * elongation
        forces.append(axial)
        stresses.append(axial / area)

    n = model.n_nodes
    disp_rows = [[displacement[2 * i], displacement[2 * i + 1]] for i in range(n)]
    reac_rows = [[reaction[2 * i], reaction[2 * i + 1]] for i in range(n)]
    max_disp = max(math.hypot(displacement[2 * i], displacement[2 * i + 1]) for i in range(n)) if n else 0.0

    return Outcome(
        n_nodes=n,
        n_elements=model.n_elements,
        displacement=attach_units(_matrix(disp_rows), _LENGTH_DIMS),
        reaction=attach_units(_matrix(reac_rows), _FORCE_DIMS),
        force=attach_units(_matrix([[f] for f in forces]), _FORCE_DIMS),
        stress=attach_units(_matrix([[sv] for sv in stresses]), _PRESSURE_DIMS),
        max_displacement=Measured(sp.Float(max_disp), _LENGTH_DIMS),
    )


def _matrix(rows: list[list[float]]) -> sp.ImmutableDenseMatrix:
    flat = [sp.Float(float(v)) for row in rows for v in row]
    return sp.ImmutableDenseMatrix(len(rows), len(rows[0]), flat)
