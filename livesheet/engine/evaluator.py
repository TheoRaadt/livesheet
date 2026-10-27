"""Worksheet evaluation: run statements top-to-bottom with a shared namespace."""

from __future__ import annotations

import tokenize
from dataclasses import dataclass
from typing import Hashable, Iterable

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

from .formatting import format_expr, format_number, format_value
from .syntax import Statement, StatementError, parse_statement
from .units import UNITS, UnitError, dims_to_text, measure

TRANSFORMS = standard_transformations + (implicit_multiplication, convert_xor)


def _log(x, base=10):
    """Mathcad convention: log is base 10, ln is natural."""
    return sp.log(x, base)


def _builtins() -> dict:
    g: dict = {}
    exec("from sympy import Integer, Float, Rational, Symbol, Function", g)  # noqa: S102 - needed by parse_expr
    g.update({
        # elementary
        "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
        "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "atan2": sp.atan2,
        "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
        "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
        "exp": sp.exp, "ln": sp.log, "log": _log, "log10": lambda x: sp.log(x, 10),
        "sqrt": sp.sqrt, "root": sp.root, "abs": sp.Abs, "sign": sp.sign,
        "floor": sp.floor, "ceil": sp.ceiling, "mod": sp.Mod,
        "Max": sp.Max, "Min": sp.Min, "max": sp.Max,
        "factorial": sp.factorial, "binomial": sp.binomial, "Gamma": sp.gamma,
        "re": sp.re, "im": sp.im, "conj": sp.conjugate, "arg": sp.arg,
        # calculus / CAS
        "diff": sp.diff, "integrate": sp.integrate, "limit": sp.limit,
        "sum": sp.summation, "product": sp.product, "series": sp.series,
        "solve": sp.solve, "expand": sp.expand, "factor": sp.factor,
        "simplify": sp.simplify, "Eq": sp.Eq,
        # constants
        "pi": sp.pi, "e": sp.E, "I": sp.I, "oo": sp.oo, "inf": sp.oo,
    })
    return g


BUILTINS = _builtins()


@dataclass
class RegionResult:
    status: str             # ok | error | empty
    output: str = ""        # text shown next to the input, e.g. "= 12.5 m/s"
    error: str = ""
    defines: str = ""       # name defined by this region, if any


class Engine:
    """Evaluates worksheet regions in reading order."""

    def __init__(self, significant: int = 6):
        self.significant = significant

    # -- parsing -------------------------------------------------------------

    def parse(self, text: str, env: dict) -> sp.Expr:
        text = text.strip()
        if not text:
            raise StatementError("Empty expression")
        if text.count("==") == 1:
            lhs, rhs = text.split("==")
            return sp.Eq(self.parse(lhs, env), self.parse(rhs, env))
        local = dict(env)
        try:
            return parse_expr(text, local_dict=local, global_dict=dict(BUILTINS),
                              transformations=TRANSFORMS, evaluate=True)
        except (SyntaxError, tokenize.TokenError, sp.SympifyError):
            raise StatementError("Syntax error") from None
        except TypeError as exc:
            raise StatementError(_type_error_text(exc)) from None

    # -- evaluation ----------------------------------------------------------

    def evaluate(self, regions: Iterable[tuple[Hashable, str]]) -> dict[Hashable, RegionResult]:
        """Evaluate ``(key, source)`` pairs given in reading order."""
        regions = list(regions)
        results: dict[Hashable, RegionResult] = {}
        statements: dict[Hashable, Statement] = {}

        for key, source in regions:
            try:
                statements[key] = parse_statement(source)
            except StatementError as exc:
                results[key] = RegionResult("error", error=str(exc))

        # Pass 1: global definitions, in reading order, visible to every region.
        env: dict = dict(UNITS)
        for key, _ in regions:
            st = statements.get(key)
            if st is not None and st.kind == "global":
                results[key] = self._run(st, env)

        # Pass 2: everything else, in reading order.
        for key, _ in regions:
            st = statements.get(key)
            if st is None or st.kind == "global":
                continue
            results[key] = self._run(st, env)
        return results

    def _run(self, st: Statement, env: dict) -> RegionResult:
        try:
            if st.kind == "empty":
                return RegionResult("empty")
            if st.kind in ("define", "global"):
                value = self._define(st, env)
                out = ""
                if st.show:
                    out = "= " + self._numeric(value, st.unit, env)
                return RegionResult("ok", out, defines=st.name)
            if st.kind == "evaluate":
                value = self.parse(st.expr, env)
                return RegionResult("ok", "= " + self._numeric(value, st.unit, env))
            if st.kind == "symbolic":
                return RegionResult("ok", "→ " + self._symbolic(st, env))
            if st.kind == "expression":
                self.parse(st.expr, env)  # validate only
                return RegionResult("ok")
            raise StatementError(f"Unknown statement kind {st.kind}")
        except (StatementError, UnitError) as exc:
            return RegionResult("error", error=str(exc))
        except ZeroDivisionError:
            return RegionResult("error", error="Division by zero")
        except Exception as exc:  # noqa: BLE001 - surface any engine failure in the region
            msg = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            return RegionResult("error", error=msg[:160])

    def _define(self, st: Statement, env: dict):
        if st.params:
            params = [sp.Symbol(p) for p in st.params]
            local = dict(env)
            local.update({p.name: p for p in params})
            body = self.parse(st.expr, local)
            value = sp.Lambda(tuple(params), body)
        else:
            value = self.parse(st.expr, env)
        env[st.name] = value
        return value

    def _numeric(self, value, unit_text: str, env: dict) -> str:
        if isinstance(value, sp.Lambda):
            raise StatementError("A function needs arguments to be evaluated")
        if isinstance(value, (bool, sp.logic.boolalg.BooleanAtom)):
            return "true" if bool(value) else "false"
        if isinstance(value, sp.Rel):
            return format_expr(value, self.significant)
        if isinstance(value, (list, tuple)):
            return "{" + ", ".join(self._numeric(v, "", env) for v in value) + "}"
        if isinstance(value, sp.MatrixBase):
            raise StatementError("Matrices are not supported yet")
        _check_defined(value)

        meas = measure(value)
        if unit_text:
            unit_val = self.parse(unit_text, env)
            _check_defined(unit_val)
            target = measure(unit_val)
            if target.dims != meas.dims:
                raise UnitError(f"Units do not match: result is {dims_to_text(meas.dims) or 'dimensionless'}")
            number = format_number(meas.magnitude / target.magnitude, self.significant)
            return f"{number} {_unit_label(unit_text)}"
        number = format_number(meas.magnitude, self.significant)
        unit = dims_to_text(meas.dims)
        return f"{number} {unit}" if unit else number

    def _symbolic(self, st: Statement, env: dict) -> str:
        # Variables named by keywords (solve, x) must stay symbolic.
        free_names = set()
        for words in st.keywords:
            if words[0] in ("solve", "collect", "series", "partfrac", "diff", "integrate", "limit"):
                free_names.update(w.split("=")[0].strip() for w in words[1:2])
        local = {k: v for k, v in env.items() if k not in free_names}
        value = self.parse(st.expr, local)
        for words in st.keywords:
            value = self._apply_keyword(value, words, local)
        return format_value(value, self.significant)

    def _apply_keyword(self, value, words: list[str], env: dict):
        kw, args = words[0].lower(), words[1:]

        def sym(i, default=None):
            if len(args) > i:
                return self.parse(args[i], {k: v for k, v in env.items() if k != args[i]})
            if default is not None:
                return default
            free = sorted(getattr(value, "free_symbols", []), key=str)
            if len(free) == 1:
                return free[0]
            raise StatementError(f"'{kw}' needs a variable, e.g. → {kw}, x")

        if kw == "simplify":
            return sp.simplify(value)
        if kw == "expand":
            return sp.expand(value)
        if kw == "factor":
            return sp.factor(value)
        if kw == "together":
            return sp.together(value)
        if kw in ("partfrac", "apart"):
            return sp.apart(value, sym(0))
        if kw == "collect":
            return sp.collect(sp.expand(value), sym(0))
        if kw == "solve":
            var = sym(0)
            sols = sp.solve(value, var)
            if not sols:
                raise StatementError("No solution found")
            return sols[0] if len(sols) == 1 else list(sols)
        if kw == "float":
            digits = int(args[0]) if args else self.significant
            return sp.N(value, digits)
        if kw == "diff":
            return sp.diff(value, sym(0))
        if kw == "integrate":
            return sp.integrate(value, sym(0))
        if kw == "series":
            var = sym(0)
            order = int(args[1]) if len(args) > 1 else 6
            return sp.series(value, var, 0, order).removeO()
        if kw == "substitute":
            if not args or "=" not in args[0]:
                raise StatementError("Use → substitute, x = value")
            out = value
            for a in args:
                name, rhs = a.split("=", 1)
                out = out.subs(sp.Symbol(name.strip()), self.parse(rhs, env))
            return out
        raise StatementError(f"Unknown keyword '{kw}'")


def _check_defined(value) -> None:
    free = getattr(value, "free_symbols", set())
    undef = sorted({str(s) for s in free} | {f.func.__name__ for f in value.atoms(AppliedUndef)}) \
        if isinstance(value, sp.Basic) else []
    if undef:
        names = ", ".join(undef)
        raise StatementError(f"{names} {'is' if len(undef) == 1 else 'are'} not defined")


def _unit_label(text: str) -> str:
    out = text.strip().replace("**", "^").replace("*", "·")
    for digit, sup in zip("23456789", "²³⁴⁵⁶⁷⁸⁹"):
        out = out.replace("^" + digit, sup)
    return out


def _type_error_text(exc: TypeError) -> str:
    msg = str(exc)
    if "not callable" in msg:
        return "Not a function: " + msg.split("'")[1] if "'" in msg else "Not a function"
    if "positional argument" in msg or "takes" in msg:
        return "Wrong number of arguments"
    return msg
