# -*- coding: utf-8 -*-
"""Парсер G-кода с полной поддержкой RS-274-адресов."""

import re
from gcode_editor.core.models import Command


class GCodeParser:
    # Полный список G-кодов (RS-274 + Mach3)
    G_MAP = {
        # движение
        "0":"RAPID","00":"RAPID","1":"FEED","01":"FEED",
        "2":"ARC_CW","02":"ARC_CW","3":"ARC_CCW","03":"ARC_CCW",
        "4":"DWELL","04":"DWELL",
        "12":"POCKET_CW","13":"POCKET_CCW",
        "31":"PROBE",
        # циклы
        "73":"CHIP","80":"CANCEL","81":"DRILL","82":"BORE","83":"PECK",
        "84":"THREAD_R","85":"BORE_STD","86":"BORE_SPINDLE",
        "87":"BORE_BACK","88":"BORE_MANUAL","89":"BORE_FINE",
        # плоскости / единицы
        "17":"PLANE_XY","18":"PLANE_XZ","19":"PLANE_YZ",
        "20":"UNITS_IN","21":"UNITS_MM","70":"UNITS_IN2","71":"UNITS_MM2",
        # коррекции
        "40":"CUTCOMP_OFF","41":"CUTCOMP_L","42":"CUTCOMP_R",
        "43":"TOOLCOMP_P","44":"TOOLCOMP_M","49":"TOOLCOMP_OFF",
        # смещения / масштаб / повороты
        "10":"G10",
        "50":"SCALE_OFF","51":"SCALE_ON","52":"LOCAL_OFF","53":"MACHINE",
        "54":"WCS","55":"WCS","56":"WCS","57":"WCS","58":"WCS","59":"WCS",
        "68":"ROT_ON","69":"ROT_OFF",
        "92":"G92SET","92.1":"G92CLR","92.2":"G92SUSP","92.3":"G92RES",
        # режимы
        "61":"EXACT","64":"SMOOTH",
        "90":"ABS","91":"INC","90.1":"ARC_ABS","91.1":"ARC_INC",
        "93":"FEED_INV","94":"FEED_IPM","95":"FEED_IPR",
        "96":"CSS","97":"RPM_FIX",
        # возвраты
        "28":"HOME","28.1":"HOME_BASE","30":"HOME2",
        "98":"RET_INIT","99":"RET_R",
        # полярные
        "15":"POLAR_OFF","16":"POLAR_ON",
    }
    M_MAP = {
        0:"STOP",1:"STOP",2:"END",30:"END",
        3:"SPIN",4:"SPIN",5:"SPIN",6:"TOOL",
        7:"COOL",8:"COOL",9:"COOL",10:"CLAMP",11:"CLAMP",
        47:"REWIND",48:"OVR_ON",49:"OVR_OFF",98:"SUB_CALL",99:"SUB_RET",
    }

    # Все RS-274 адреса
    _ADDRS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def parse(self, text):
        commands = []
        warnings = []
        # состояние
        cx_ = cy_ = cz_ = 0.0
        ca_ = cb_ = cc_ = 0.0
        cur_feed = 200.0
        spindle_on = False
        cool_on = False

        labels = {}
        for m in re.finditer(r"^\s*N\s*(\d+)\b", text, re.MULTILINE):
            labels[int(m.group(1))] = f"L{m.group(1)}"

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("%"):
                cm = re.search(r"\(([^)]*)\)", raw_line)
                if cm:
                    commands.append(Command("#", {}, cm.group(1).strip()))
                continue
            for cm in re.finditer(r"\(([^)]*)\)", line):
                commands.append(Command("#", {}, cm.group(1).strip()))
            line = re.sub(r"\([^)]*\)", "", line).strip()
            if not line:
                continue

            vm = re.match(r"^(#\d+|#<[A-Za-z_]\w*>)\s*=\s*(.+)$", line)
            if vm:
                rhs = vm.group(2).strip()
                add_m = re.match(
                    r"^\[\s*(#\d+|#<[A-Za-z_]\w*>)\s*\+\s*(.+?)\s*\]$", rhs)
                if add_m and add_m.group(1) == vm.group(1):
                    commands.append(Command("VAR_ADD", {
                        "name": vm.group(1), "delta": add_m.group(2).strip()}))
                else:
                    commands.append(Command("VAR", {
                        "name": vm.group(1), "value": rhs}))
                continue

            im = re.match(
                r"^IF\s*\[([^\]]+)\]\s*GOTO\s*(\d+)\s*$", line, re.IGNORECASE)
            if im:
                parts = im.group(1).strip().split()
                lhs = parts[0] if parts else "#100"
                op = parts[1] if len(parts) > 1 else "EQ"
                rhs = parts[2] if len(parts) > 2 else "0"
                commands.append(Command("IF", {
                    "lhs": lhs, "op": op, "rhs": rhs,
                    "target": f"L{im.group(2)}"}))
                continue

            gm = re.match(r"^GOTO\s*(\d+)\s*$", line, re.IGNORECASE)
            if gm:
                commands.append(Command("GOTO", {"target": f"L{gm.group(1)}"}))
                continue

            tokens = line.split()
            gcodes = []
            mcode = None
            n_label = None
            # все адреса
            coords = {k.lower(): None for k in self._ADDRS}
            tool = None
            for tok in tokens:
                if not tok:
                    continue
                letter = tok[0].upper()
                if letter not in self._ADDRS:
                    continue
                try:
                    val = float(tok[1:])
                except (ValueError, IndexError):
                    continue
                if letter == "G":
                    gcodes.append(tok[1:])
                elif letter == "M":
                    mcode = int(val)
                elif letter == "N":
                    n_label = int(val)
                elif letter == "T":
                    tool = int(val)
                else:
                    coords[letter.lower()] = val

            if n_label is not None and n_label in labels:
                commands.append(Command("LABEL", {"name": labels[n_label]}))

            if mcode is not None:
                self._emit_mcode(mcode, coords, commands, warnings,
                                 state={"spindle": spindle_on, "cool": cool_on})
                # обновление состояния
                if mcode in (3, 4):
                    spindle_on = True
                elif mcode == 5:
                    spindle_on = False
                elif mcode in (7, 8):
                    cool_on = True
                elif mcode == 9:
                    cool_on = False
                if mcode == 6 and tool is not None:
                    commands.append(Command("TOOL", {"tool": tool}))
                continue

            for g in gcodes:
                key = g if g in self.G_MAP else None
                if key is None:
                    try:
                        key = str(int(float(g)))
                    except ValueError:
                        pass
                if key is None or key not in self.G_MAP:
                    warnings.append(f"G{g} не поддержан")
                    continue
                mnem = self.G_MAP[key]
                self._emit_gcode(mnem, key, coords, commands, warnings,
                                 state={"cx": cx_, "cy": cy_, "cz": cz_,
                                        "ca": ca_, "cb": cb_, "cc": cc_,
                                        "f": cur_feed, "tool": tool})
                # обновляем состояние
                if mnem in ("RAPID", "FEED", "ARC_CW", "ARC_CCW",
                            "PROBE"):
                    cx_ = coords["x"] if coords["x"] is not None else cx_
                    cy_ = coords["y"] if coords["y"] is not None else cy_
                    cz_ = coords["z"] if coords["z"] is not None else cz_
                    ca_ = coords["a"] if coords["a"] is not None else ca_
                    cb_ = coords["b"] if coords["b"] is not None else cb_
                    cc_ = coords["c"] if coords["c"] is not None else cc_
                    if coords["f"] is not None:
                        cur_feed = coords["f"]
                elif mnem in ("DRILL", "PECK", "CHIP", "BORE",
                              "THREAD_R", "BORE_STD", "BORE_SPINDLE",
                              "BORE_BACK", "BORE_MANUAL", "BORE_FINE"):
                    cz_ = 5.0
                elif mnem == "G10":
                    l = int(coords.get("l") or 2)
                    if l in (2, 20):
                        # установка координат смещения
                        pass
        return commands, warnings

    # ---------------- M ----------------
    def _emit_mcode(self, mcode, coords, commands, warnings, state):
        mnem = self.M_MAP.get(mcode)
        if mnem == "SPIN":
            if mcode == 5:
                if state["spindle"]:
                    commands.append(Command("SPIN",
                        {"on": 0, "rpm": 0, "ccw": 0}))
            else:
                rpm = int(coords.get("s") or 8000)
                commands.append(Command("SPIN", {
                    "on": 1, "rpm": rpm,
                    "ccw": 1 if mcode == 4 else 0}))
        elif mnem == "COOL":
            if mcode == 9:
                if state["cool"]:
                    commands.append(Command("COOL", {"on": 0, "mist": 0}))
            else:
                commands.append(Command("COOL", {
                    "on": 1, "mist": 1 if mcode == 7 else 0}))
        elif mnem == "CLAMP":
            commands.append(Command("CLAMP", {"on": 1 if mcode == 10 else 0}))
        elif mnem == "STOP":
            commands.append(Command("STOP",
                {"optional": 1 if mcode == 1 else 0}))
        elif mnem == "END":
            commands.append(Command("END", {}))
        elif mnem == "REWIND":
            commands.append(Command("REWIND", {}))
        elif mnem == "OVR_ON":
            commands.append(Command("OVR_ON", {}))
        elif mnem == "OVR_OFF":
            commands.append(Command("OVR_OFF", {}))
        elif mnem == "SUB_CALL":
            commands.append(Command("SUB_CALL", {
                "name": str(int(coords.get("p") or 1000)),
                "repeat": int(coords.get("l") or 1)}))
        elif mnem == "SUB_RET":
            commands.append(Command("SUB_RET", {}))
        else:
            warnings.append(f"M{mcode} не поддержан")

    # ---------------- G ----------------
    def _emit_gcode(self, mnem, key, coords, commands, warnings, state):
        cx_, cy_, cz_ = state["cx"], state["cy"], state["cz"]
        ca_, cb_, cc_ = state["ca"], state["cb"], state["cc"]
        f_default = state["f"]

        def g(k, default=None):
            v = coords.get(k)
            return v if v is not None else default

        if mnem in ("RAPID", "FEED"):
            x = g("x", cx_)
            y = g("y", cy_)
            z = g("z", cz_)
            a = g("a", ca_)
            b = g("b", cb_)
            c = g("c", cc_)
            if mnem == "FEED":
                f = g("f", f_default)
                commands.append(Command("FEED",
                    {"x": x, "y": y, "z": z, "a": a, "b": b, "c": c, "f": f}))
            else:
                commands.append(Command("RAPID",
                    {"x": x, "y": y, "z": z, "a": a, "b": b, "c": c}))
            return

        if mnem in ("ARC_CW", "ARC_CCW"):
            x = g("x", cx_); y = g("y", cy_); z = g("z", cz_)
            f = g("f", f_default)
            ccx = cx_ + (g("i") or 0)
            ccy = cy_ + (g("j") or 0)
            commands.append(Command(mnem, {
                "x": x, "y": y, "z": z, "cx": ccx, "cy": ccy, "f": f}))
            return

        if mnem == "DWELL":
            p_ms = g("p") or 0
            commands.append(Command("DWELL", {"sec": p_ms / 1000.0}))
            return

        if mnem == "WCS":
            commands.append(Command("WCS", {"num": int(key)}))
            return

        if mnem in ("RAPID", "CANCEL"):
            commands.append(Command(mnem, {}))
            return

        if mnem in ("ABS","INC","PLANE_XY","PLANE_XZ","PLANE_YZ",
                    "UNITS_IN","UNITS_MM","UNITS_IN2","UNITS_MM2",
                    "ARC_ABS","ARC_INC",
                    "FEED_INV","FEED_IPM","FEED_IPR","EXACT","SMOOTH",
                    "RET_INIT","RET_R","HOME","HOME2","HOME_BASE",
                    "POLAR_OFF","POLAR_ON",
                    "SCALE_OFF","ROT_OFF","CUTCOMP_OFF","TOOLCOMP_OFF",
                    "G92CLR","G92SUSP","G92RES"):
            commands.append(Command(mnem, {}))
            return

        if mnem == "G10":
            l = int(g("l") or 2)
            p = int(g("p") or 1)
            commands.append(Command("G10", {
                "l": l, "p": p,
                "x": g("x") or 0.0,
                "y": g("y") or 0.0,
                "z": g("z") or 0.0}))
            return

        if mnem == "PROBE":
            commands.append(Command("PROBE", {
                "x": g("x", cx_), "y": g("y", cy_),
                "z": g("z", cz_), "f": g("f", f_default)}))
            return

        if mnem in ("POCKET_CW", "POCKET_CCW"):
            commands.append(Command(mnem, {
                "i": g("i") or 10.0, "j": g("j") or 10.0,
                "z": g("z") or -2.0, "f": g("f") or 200.0}))
            return

        if mnem in ("DRILL", "PECK", "CHIP", "BORE",
                    "THREAD_R", "BORE_STD", "BORE_SPINDLE",
                    "BORE_BACK", "BORE_MANUAL", "BORE_FINE"):
            d = {
                "x": g("x", cx_), "y": g("y", cy_),
                "z": g("z", -5.0), "r": g("r", 1.0),
                "f": g("f", 60.0),
            }
            if mnem in ("PECK", "CHIP"):
                d["q"] = g("q") or 1.0
            if mnem in ("BORE", "THREAD_R", "BORE_MANUAL", "BORE_FINE"):
                d["p"] = (g("p") or 0.0) / 1000.0
            commands.append(Command(mnem, d))
            return

        if mnem == "CUTCOMP_L":
            commands.append(Command("CUTCOMP_L",
                {"d": int(g("d") or 1)}))
            return
        if mnem == "CUTCOMP_R":
            commands.append(Command("CUTCOMP_R",
                {"d": int(g("d") or 1)}))
            return
        if mnem == "TOOLCOMP_P":
            commands.append(Command("TOOLCOMP_P",
                {"h": int(g("h") or 1), "z": g("z") or 0.0}))
            return
        if mnem == "TOOLCOMP_M":
            commands.append(Command("TOOLCOMP_M",
                {"h": int(g("h") or 1)}))
            return
        if mnem == "SCALE_ON":
            commands.append(Command("SCALE_ON", {
                "x": g("x") or 1.0,
                "y": g("y") or 1.0,
                "z": g("z") or 1.0}))
            return
        if mnem == "LOCAL_OFF":
            commands.append(Command("LOCAL_OFF", {
                "x": g("x") or 0.0,
                "y": g("y") or 0.0,
                "z": g("z") or 0.0}))
            return
        if mnem == "ROT_ON":
            commands.append(Command("ROT_ON", {
                "x": g("x") or 0.0,
                "y": g("y") or 0.0,
                "angle": g("r") or g("p") or 0.0}))
            return
        if mnem == "CSS":
            commands.append(Command("CSS", {"v": g("s") or 100.0}))
            return
        if mnem == "RPM_FIX":
            commands.append(Command("RPM_FIX",
                {"rpm": int(g("s") or 8000)}))
            return
        if mnem == "G92SET":
            commands.append(Command("G92SET", {
                "x": g("x") or 0.0,
                "y": g("y") or 0.0,
                "z": g("z") or 0.0}))
            return