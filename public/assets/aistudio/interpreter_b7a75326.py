# -*- coding: utf-8 -*-
"""Интерпретатор псевдокода."""

from gcode_editor.core.formula import FormulaEval


MAX_CALL_DEPTH = 16


class ProgramInterp:
    def __init__(self, commands, variables, max_steps=500000, functions=None):
        self.commands = commands
        self.vars = dict(variables)
        self.fml = FormulaEval(self.vars)
        self.max_steps = max_steps
        self.labels = {}
        for i, c in enumerate(commands):
            if c.mnemonic == "LABEL":
                self.labels[str(c.params.get("name", ""))] = i
        self.functions = dict(functions or {})
        self._call_depth = 0

    def _num(self, v):
        self.fml.vars = self.vars
        return self.fml.resolve_number(v)

    def _cmp(self, a, op, b):
        op = op.upper()
        if op == "EQ": return abs(a - b) < 1e-9
        if op == "NE": return abs(a - b) >= 1e-9
        if op == "GT": return a > b
        if op == "LT": return a < b
        if op == "GE": return a >= b
        if op == "LE": return a <= b
        return False

    def _build_sub_scope(self, fn_name, params):
        saved = dict(self.vars)
        fn = self.functions.get(fn_name)
        if fn is None:
            return saved, saved
        local = dict(saved)
        for prm in fn.params:
            pkey = f"p_{prm.name}"
            val_raw = params.get(pkey, prm.default)
            try:
                fe = FormulaEval(local)
                val = fe.resolve_number(val_raw)
            except Exception:
                val = 0.0
            full = f"#FN_{fn.name}_{prm.name}"
            local[full] = val
            local["#" + prm.name] = val
            local[prm.name] = val
        return local, saved

    def _run_function(self, fn_name, params, callback):
        if self._call_depth >= MAX_CALL_DEPTH:
            return
        fn = self.functions.get(fn_name)
        if fn is None or not fn.body:
            return
        local, saved = self._build_sub_scope(fn_name, params)
        sub = fn.body
        sub_labels = {}
        for i, c in enumerate(sub):
            if c.mnemonic == "LABEL":
                sub_labels[str(c.params.get("name", ""))] = i

        self.vars = local
        self.fml.vars = local
        self._call_depth += 1
        try:
            i = 0
            sub_steps = 0
            while i < len(sub):
                if sub_steps > self.max_steps:
                    break
                sub_steps += 1
                cmd = sub[i]
                m, p = cmd.mnemonic, cmd.params
                if m == "VAR":
                    name = str(p.get("name", "#100"))
                    try:
                        local[name] = self._num(p.get("value", 0))
                    except Exception:
                        local[name] = 0.0
                    i += 1; continue
                if m == "VAR_ADD":
                    name = str(p.get("name", "#100"))
                    try:
                        d = self._num(p.get("delta", 1))
                    except Exception:
                        d = 0.0
                    local[name] = local.get(name, 0.0) + d
                    i += 1; continue
                if m == "LABEL":
                    i += 1; continue
                if m == "IF":
                    try:
                        lhs = self._num(p.get("lhs", 0))
                        rhs = self._num(p.get("rhs", 0))
                        cond = self._cmp(lhs, str(p.get("op", "EQ")), rhs)
                    except Exception:
                        cond = False
                    if cond:
                        t = str(p.get("target", ""))
                        if t in sub_labels:
                            i = sub_labels[t]; continue
                    i += 1; continue
                if m == "GOTO":
                    t = str(p.get("target", ""))
                    if t in sub_labels:
                        i = sub_labels[t]; continue
                    i += 1; continue
                if m == "CALL_FUNC":
                    self._run_function(str(p.get("name", "")),
                                       dict(p), callback)
                    i += 1; continue
                try:
                    callback(cmd, -1)
                except Exception as e:
                    print(f"Callback error in function {fn_name}: {e}")
                i += 1
        finally:
            self._call_depth -= 1
            self.vars = saved
            self.fml.vars = saved

    def run(self, callback, start_index=0, end_index=None, step_limit=None):
        i = start_index
        steps = 0
        limit = step_limit if step_limit is not None else self.max_steps
        end = end_index if end_index is not None else len(self.commands)
        call_stack = []
        while i < end:
            if steps >= limit:
                break
            cmd = self.commands[i]
            steps += 1
            m, p = cmd.mnemonic, cmd.params

            if m == "VAR":
                name = str(p.get("name", "#100"))
                try:
                    self.vars[name] = self._num(p.get("value", 0))
                except Exception:
                    self.vars[name] = 0.0
                i += 1; continue
            if m == "VAR_ADD":
                name = str(p.get("name", "#100"))
                try:
                    d = self._num(p.get("delta", 1))
                except Exception:
                    d = 0.0
                self.vars[name] = self.vars.get(name, 0.0) + d
                i += 1; continue
            if m == "LABEL":
                i += 1; continue
            if m == "IF":
                try:
                    lhs = self._num(p.get("lhs", 0))
                    rhs = self._num(p.get("rhs", 0))
                    cond = self._cmp(lhs, str(p.get("op", "EQ")), rhs)
                except Exception:
                    cond = False
                if cond:
                    t = str(p.get("target", ""))
                    if t in self.labels:
                        i = self.labels[t]; continue
                i += 1; continue
            if m == "GOTO":
                t = str(p.get("target", ""))
                if t in self.labels:
                    i = self.labels[t]; continue
                i += 1; continue
            if m == "CALL_FUNC":
                self._run_function(str(p.get("name", "")), dict(p), callback)
                i += 1; continue
            if m == "SUB_CALL":
                name = str(p.get("name", "1000"))
                repeat = int(p.get("repeat", 1) or 1)
                target = None
                for cand in (f"L{name}", f"SUB_{name}", f"O{name}", name):
                    if cand in self.labels:
                        target = self.labels[cand]
                        break
                if target is None:
                    i += 1; continue
                for _ in range(repeat):
                    call_stack.append(i + 1)
                i = target; continue
            if m == "SUB_RET":
                if call_stack:
                    i = call_stack.pop()
                else:
                    i += 1
                continue
            try:
                callback(cmd, i)
            except Exception as e:
                print(f"Callback error cmd {i}: {e}")
            i += 1
        return steps