# -*- coding: utf-8 -*-
"""Вычислитель формул для параметров команд."""

import math
import re
from typing import Dict, List
from gcode_editor.core.models import UserVar


class FormulaEval:
    ALLOWED_FUNCS = {
        "min": min, "max": max, "abs": abs,
        "round": round, "int": int, "float": float,
        "floor": math.floor, "ceil": math.ceil,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "atan2": math.atan2, "hypot": math.hypot,
    }
    ALLOWED_CONSTS = {"pi": math.pi, "e": math.e, "tau": 2 * math.pi}

    _HASH_NUM_RE = re.compile(r"#(\d+)")
    _HASH_NAME_RE = re.compile(r"#<([A-Za-z_]\w*)>")

    def __init__(self, variables):
        self.vars = dict(variables)
        self.last_error = None

    # ---------- public ----------
    def resolve_number(self, value):
        self.last_error = None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return 0.0
        s = value.strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            pass
        expr = s
        m = re.fullmatch(r"\{(.*)\}", s, re.DOTALL)
        if m:
            expr = m.group(1)
        return self._eval(expr)

    # ---------- internals ----------
    def _subst_hashes(self, expr):
        def _num(mo):
            key = "#" + mo.group(1)
            if key not in self.vars:
                raise ValueError(f"Переменная {key} не определена")
            return repr(float(self.vars[key]))
        def _name(mo):
            key = "#<" + mo.group(1) + ">"
            simple = "#" + mo.group(1)
            for k in (key, simple):
                if k in self.vars:
                    return repr(float(self.vars[k]))
            raise ValueError(f"Переменная {key} не определена")
        expr = self._HASH_NAME_RE.sub(_name, expr)
        expr = self._HASH_NUM_RE.sub(_num, expr)
        return expr

    def _env(self):
        env = dict(self.ALLOWED_FUNCS)
        env.update(self.ALLOWED_CONSTS)
        for k, v in self.vars.items():
            if isinstance(k, str) and re.fullmatch(r"[A-Za-z_]\w*", k):
                try:
                    env[k] = float(v)
                except (TypeError, ValueError):
                    pass
        return env

    def _eval(self, expr):
        expr = self._substitute_braces(expr)
        expr = self._subst_hashes(expr)
        if not re.fullmatch(r"[\s0-9\.\+\-\*/%\(\)eE_,A-Za-z]+", expr):
            raise ValueError(f"Недопустимые символы: {expr!r}")
        try:
            return float(eval(expr, {"__builtins__": {}}, self._env()))
        except Exception as e:
            raise ValueError(f"Формула '{expr}': {e}")

    def _eval_no_braces(self, expr):
        expr = self._subst_hashes(expr)
        if not re.fullmatch(r"[\s0-9\.\+\-\*/%\(\)eE_,A-Za-z]+", expr):
            raise ValueError(f"Недопустимые символы: {expr!r}")
        try:
            return float(eval(expr, {"__builtins__": {}}, self._env()))
        except Exception as e:
            raise ValueError(f"Формула '{expr}': {e}")

    def _substitute_braces(self, expr):
        for _ in range(16):
            m = re.search(r"\{([^{}]*)\}", expr)
            if not m:
                break
            inner = m.group(1).strip()
            val = self._eval_no_braces(inner)   # ← больше не глушим ошибки
            expr = expr[:m.start()] + repr(val) + expr[m.end():]
        if "{" in expr or "}" in expr:
            raise ValueError(f"Несбалансированные скобки: {expr!r}")
        return expr


def build_env(vars_list: List[UserVar]):
    """Возвращает (env: dict, errors: list[str])."""
    raw = {}
    for v in vars_list:
        if v.name:
            raw[v.name] = v.value
    result: Dict[str, float] = {}
    errors: List[str] = []
    for _ in range(32):
        progress = False
        for name, expr in raw.items():
            if name in result:
                continue
            try:
                fe = FormulaEval({**result})
                result[name] = fe.resolve_number(expr)
                progress = True
            except Exception:
                continue
        if not progress:
            break
    for name, expr in raw.items():
        if name not in result:
            try:
                fe = FormulaEval({**result})
                result[name] = fe.resolve_number(expr)
            except Exception as e:
                errors.append(f"{name}: {e}")
                result[name] = 0.0
    return result, errors