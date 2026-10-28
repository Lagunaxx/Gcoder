# -*- coding: utf-8 -*-
"""Симулятор обработки и сегменты траектории."""

import math
from dataclasses import dataclass
from typing import Optional

from gcode_editor.core.formula import FormulaEval
from gcode_editor.code.interpreter import ProgramInterp
from gcode_editor.sim.heightmap import HeightMap


@dataclass
class Segment:
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float
    tool_d: float
    tool_color: str
    rapid: bool
    arc: bool = False
    cx: float = 0.0
    cy: float = 0.0
    cw: bool = True
    drill: bool = False
    collision: bool = False
    collision_reason: str = ""
    spindle_on: bool = True
    cmd_index: int = -1
    executed_index: int = -1


def _available_memory_bytes() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except Exception:
        pass
    try:
        import os
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_AVPHYS_PAGES")
            size = os.sysconf("SC_PAGE_SIZE")
            if pages > 0 and size > 0:
                return pages * size
    except Exception:
        pass
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.ullAvailPhys)
    except Exception:
        pass
    return 2 * 1024 * 1024 * 1024


class Simulator:
    def __init__(self, tools, variables=None, stock=None, settings=None,
                 functions=None, preamble=None, postamble=None):
        self.tools = {t.number: t for t in tools}
        self.variables = variables or {}
        self.stock = stock
        self.settings = settings
        self.functions = {f.name: f for f in (functions or [])}
        self.preamble = list(preamble or [])
        self.postamble = list(postamble or [])
        self.fml = FormulaEval(self.variables)

    def _n(self, v):
        return self.fml.resolve_number(v)

    def _resolve_voxel(self, min_tool_d):
        s = self.settings
        if s is None:
            return 0.5, 1.0, False
        if getattr(s, "auto_voxel_xy", True):
            vxy = max(min_tool_d / 3.0, 0.01)
        else:
            vxy = max(float(getattr(s, "voxel_xy", 0.5)), 0.01)
        vz = max(float(getattr(s, "voxel_z", 1.0)), 0.01)
        return vxy, vz, False

    def trace(self, commands, upto, stock=None,
              check_collisions=True, ignore_rapid_in_material=False,
              step_limit=None):
        stats = {"cut_len": 0.0, "rapid_len": 0.0, "zmin": float("inf"),
                 "collision_count": 0, "collisions": [],
                 "executed_steps": 0, "voxel_xy": 0.0, "voxel_z": 0.0,
                 "voxel_limited": False, "voxel_warning": "",
                 "a": 0.0, "b": 0.0, "c": 0.0, "cmd_to_segments": {}}
        segs = []
        cmd_to_segments = {}
        pos = [0.0, 0.0, 0.0]
        rot = [0.0, 0.0, 0.0]
        cur_tool = [None]
        spindle_on = [False]
        incremental = [False]
        units_scale = [1.0]
        wcs_off = [0.0, 0.0, 0.0]
        g92_off = [0.0, 0.0, 0.0]
        g92_saved = [0.0, 0.0, 0.0]
        g92_active = [True]
        g52_off = [0.0, 0.0, 0.0]
        polar = [False]
        minx = [0.0]; miny = [0.0]; maxx = [0.0]; maxy = [0.0]

        min_tool_d = 3.0
        if self.tools:
            min_tool_d = min(
                t.diameter for t in self.tools.values() if t.diameter > 0
            ) or 3.0
        vxy, vz, limited = self._resolve_voxel(min_tool_d)

        hm = None
        S = stock if stock is not None else self.stock
        if S is not None:
            try:
                bx0, by0, bx1, by1, z_top, z_bot = S.bounds()
                w = max(bx1 - bx0, 1e-3)
                h = max(by1 - by0, 1e-3)
                d = max(z_top - z_bot, 1e-3)
                avail = _available_memory_bytes()
                frac = 0.5
                if self.settings is not None:
                    frac = float(getattr(self.settings,
                                         "max_memory_fraction", 0.5))
                budget = max(int(avail * frac), 16 * 1024 * 1024)
                nx = max(1, int(math.ceil(w / vxy)))
                ny = max(1, int(math.ceil(h / vxy)))
                nz = max(1, int(math.ceil(d / vz)))
                total = nx * ny * nz * 8
                if total > budget:
                    scale = (total / budget) ** (1.0 / 3.0)
                    vxy *= scale
                    vz *= scale
                    limited = True
                    nx = max(1, int(math.ceil(w / vxy)))
                    ny = max(1, int(math.ceil(h / vxy)))
                    nz = max(1, int(math.ceil(d / vz)))
                stats["voxel_xy"] = vxy
                stats["voxel_z"] = vz
                stats["voxel_limited"] = limited
                if limited:
                    stats["voxel_warning"] = (
                        f"Воксели ограничены памятью: "
                        f"{vxy:.3f}×{vxy:.3f}×{vz:.3f} мм")
                hm = HeightMap(bx0, by0, bx1, by1, z_top, z_bot,
                               voxel_xy=vxy, voxel_z=vz)
            except Exception as e:
                print("HeightMap init error:", e)
                hm = None

        def upd(x, y):
            minx[0] = min(minx[0], x); miny[0] = min(miny[0], y)
            maxx[0] = max(maxx[0], x); maxy[0] = max(maxy[0], y)

        def total_off():
            g92x = g92_off[0] if g92_active[0] else 0.0
            g92y = g92_off[1] if g92_active[0] else 0.0
            g92z = g92_off[2] if g92_active[0] else 0.0
            return (wcs_off[0] + g92x + g52_off[0],
                    wcs_off[1] + g92y + g52_off[1],
                    wcs_off[2] + g92z + g52_off[2])

        def resolve_raw(px, py, pz):
            if incremental[0]:
                return (pos[0] + px * units_scale[0],
                        pos[1] + py * units_scale[0],
                        pos[2] + pz * units_scale[0])
            off = total_off()
            return (px * units_scale[0] + off[0],
                    py * units_scale[0] + off[1],
                    pz * units_scale[0] + off[2])

        def resolve(px, py, pz):
            if polar[0]:
                r = px
                ang = math.radians(py)
                dx = r * math.cos(ang)
                dy = r * math.sin(ang)
                return resolve_raw(dx, dy, pz)
            return resolve_raw(px, py, pz)

        def check_collision(seg):
            if hm is None or not check_collisions:
                return
            radius = seg.tool_d / 2.0
            L = math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0)
            step = max(hm.dx * 0.5, 0.1)
            n = max(2, int(L / step) + 1)
            inside = False
            for i in range(n + 1):
                t = i / n
                px = seg.x0 + (seg.x1 - seg.x0) * t
                py = seg.y0 + (seg.y1 - seg.y0) * t
                pz = seg.z0 + (seg.z1 - seg.z0) * t
                hmax = hm.max_height_in_disc(px, py, radius)
                if pz < hmax - 1e-6:
                    inside = True
                    break
            if not inside:
                return
            if seg.rapid:
                if ignore_rapid_in_material:
                    return
                reason = "RAPID в материале"
            elif not seg.spindle_on:
                reason = "FEED при выключенном шпинделе"
            else:
                return
            seg.collision = True
            seg.collision_reason = reason
            stats["collision_count"] += 1
            stats["collisions"].append({
                "cmd_index": seg.cmd_index, "reason": reason,
                "x": seg.x1, "y": seg.y1, "z": seg.z1})

        def apply_cut(seg):
            if hm is None or seg.collision or not seg.spindle_on:
                return
            radius = seg.tool_d / 2.0
            if seg.drill:
                hm.cut_drill(seg.x1, seg.y1, seg.z0, seg.z1, radius)
            elif seg.arc:
                r = math.hypot(seg.x0 - seg.cx, seg.y0 - seg.cy)
                a0 = math.atan2(seg.y0 - seg.cy, seg.x0 - seg.cx)
                a1 = math.atan2(seg.y1 - seg.cy, seg.x1 - seg.cx)
                if abs(a1 - a0) < 1e-9:
                    a1 = a0 + (2 * math.pi if not seg.cw else -2 * math.pi)
                hm.cut_arc(seg.cx, seg.cy, r, a0, a1,
                           seg.z0, seg.z1, radius, seg.cw)
            elif seg.rapid:
                return
            else:
                hm.cut_line(seg.x0, seg.y0, seg.z0,
                            seg.x1, seg.y1, seg.z1, radius)

        def do_arc(ccx, ccy, ex, ey, ez, cw, dia, col, idx):
            a0 = math.atan2(pos[1] - ccy, pos[0] - ccx)
            a1 = math.atan2(ey - ccy, ex - ccx)
            da = a1 - a0
            if cw:
                while da > 0: da -= 2 * math.pi
            else:
                while da < 0: da += 2 * math.pi
            seg = Segment(pos[0], pos[1], pos[2], ex, ey, ez, dia, col,
                          False, arc=True, cx=ccx, cy=ccy, cw=cw,
                          spindle_on=spindle_on[0], cmd_index=idx,
                          executed_index=stats["executed_steps"])
            check_collision(seg); apply_cut(seg)
            cmd_to_segments.setdefault(idx, []).append(len(segs))
            segs.append(seg)
            stats["cut_len"] += abs(da) * math.hypot(pos[0] - ccx, pos[1] - ccy)
            stats["zmin"] = min(stats["zmin"], ez)

        live_vars = dict(self.variables)
        interp = ProgramInterp(commands, live_vars,
                               max_steps=(step_limit or 200000) * 2,
                               functions=self.functions)

        def on_cmd(cmd, idx):
            if idx >= 0 and idx > upto - 1:
                return
            stats["executed_steps"] += 1
            if step_limit is not None and stats["executed_steps"] > step_limit:
                return
            m, p = cmd.mnemonic, cmd.params
            self.fml.vars = interp.vars

            if m == "ABS":
                incremental[0] = False; return
            if m == "INC":
                incremental[0] = True; return
            if m == "UNITS_IN":
                units_scale[0] = 25.4; return
            if m == "UNITS_MM":
                units_scale[0] = 1.0; return
            if m == "UNITS_IN2":
                units_scale[0] = 25.4; return
            if m == "UNITS_MM2":
                units_scale[0] = 1.0; return
            if m == "POLAR_ON":
                polar[0] = True; return
            if m == "POLAR_OFF":
                polar[0] = False; return
            if m == "SPIN":
                spindle_on[0] = bool(int(self._n(p.get("on", 1)))); return
            if m == "TOOL":
                cur_tool[0] = self.tools.get(int(self._n(p.get("tool", 1))))
                return
            if m == "WCS":
                return
            if m == "G10":
                l = int(self._n(p.get("l", 2)))
                if l in (2, 20):
                    wcs_off[0] = self._n(p.get("x", 0))
                    wcs_off[1] = self._n(p.get("y", 0))
                    wcs_off[2] = self._n(p.get("z", 0))
                return
            if m == "G92SET":
                g92_off[0] = pos[0] - self._n(p.get("x", 0))
                g92_off[1] = pos[1] - self._n(p.get("y", 0))
                g92_off[2] = pos[2] - self._n(p.get("z", 0))
                g92_active[0] = True
                return
            if m == "G92CLR":
                g92_off[0] = g92_off[1] = g92_off[2] = 0.0
                g92_active[0] = True
                return
            if m == "G92SUSP":
                g92_saved[0], g92_saved[1], g92_saved[2] = \
                    g92_off[0], g92_off[1], g92_off[2]
                g92_active[0] = False
                return
            if m == "G92RES":
                g92_off[0], g92_off[1], g92_off[2] = \
                    g92_saved[0], g92_saved[1], g92_saved[2]
                g92_active[0] = True
                return
            if m == "LOCAL_OFF":
                g52_off[0] = self._n(p.get("x", 0))
                g52_off[1] = self._n(p.get("y", 0))
                g52_off[2] = self._n(p.get("z", 0)); return
            if m == "HOME_BASE":
                pos[0], pos[1], pos[2] = 0.0, 0.0, 0.0; return
            if m == "ROT_ON":
                return

            ct = cur_tool[0]
            dia = ct.diameter if ct else 1.0
            col = ct.color if ct else "#3399ff"

            if m in ("RAPID", "FEED"):
                px = self._n(p.get("x", pos[0]))
                py = self._n(p.get("y", pos[1]))
                pz = self._n(p.get("z", pos[2]))
                nx, ny, nz = resolve(px, py, pz)
                if "a" in p: rot[0] = self._n(p["a"])
                if "b" in p: rot[1] = self._n(p["b"])
                if "c" in p: rot[2] = self._n(p["c"])
                seg = Segment(pos[0], pos[1], pos[2], nx, ny, nz, dia, col,
                              m == "RAPID", spindle_on=spindle_on[0],
                              cmd_index=idx,
                              executed_index=stats["executed_steps"])
                check_collision(seg); apply_cut(seg)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg)
                if m == "RAPID":
                    stats["rapid_len"] += math.hypot(nx - pos[0], ny - pos[1])
                else:
                    stats["cut_len"] += math.hypot(nx - pos[0], ny - pos[1])
                    stats["zmin"] = min(stats["zmin"], nz)
                pos[0], pos[1], pos[2] = nx, ny, nz; upd(nx, ny)

            elif m in ("ARC_CW", "ARC_CCW"):
                ex, ey, ez = resolve(self._n(p.get("x", pos[0])),
                                     self._n(p.get("y", pos[1])),
                                     self._n(p.get("z", pos[2])))
                ccx = self._n(p.get("cx", pos[0]))
                ccy = self._n(p.get("cy", pos[1]))
                do_arc(ccx, ccy, ex, ey, ez,
                       m == "ARC_CW", dia, col, idx)
                pos[0], pos[1], pos[2] = ex, ey, ez
                upd(min(pos[0], ex, ccx), min(pos[1], ey, ccy))
                upd(max(pos[0], ex, ccx), max(pos[1], ey, ccy))

            elif m in ("DRILL","PECK","CHIP","BORE",
                      "THREAD_R","BORE_STD","BORE_SPINDLE",
                      "BORE_BACK","BORE_MANUAL","BORE_FINE"):
                hx, hy, hz = resolve(self._n(p.get("x", pos[0])),
                                     self._n(p.get("y", pos[1])),
                                     self._n(p.get("z", -5)))
                seg_r = Segment(pos[0], pos[1], pos[2], hx, hy, pos[2],
                                dia, col, True, spindle_on=spindle_on[0],
                                cmd_index=idx,
                                executed_index=stats["executed_steps"])
                check_collision(seg_r)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg_r)
                stats["rapid_len"] += math.hypot(hx - pos[0], hy - pos[1])
                pos[0], pos[1] = hx, hy
                seg_d = Segment(hx, hy, pos[2], hx, hy, hz, dia, col,
                                False, drill=True, spindle_on=spindle_on[0],
                                cmd_index=idx,
                                executed_index=stats["executed_steps"])
                check_collision(seg_d); apply_cut(seg_d)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg_d)
                stats["cut_len"] += abs(hz - pos[2])
                stats["zmin"] = min(stats["zmin"], hz)
                pos[2] = hz
                z_clear = max(5.0, hm.z_top + 1.0) if hm is not None else 5.0
                seg_u = Segment(hx, hy, hz, hx, hy, z_clear, dia, col, True,
                                spindle_on=spindle_on[0], cmd_index=idx,
                                executed_index=stats["executed_steps"])
                check_collision(seg_u)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg_u)
                stats["rapid_len"] += abs(z_clear - hz)
                pos[2] = z_clear; upd(hx, hy)

            elif m in ("POCKET_CW", "POCKET_CCW"):
                cw = (m == "POCKET_CW")
                R = self._n(p.get("i", 10.0))
                z = self._n(p.get("z", -2.0))
                cx, cy = pos[0], pos[1]
                step = max(dia * 0.5, 0.5)
                r = dia * 0.5
                first = True
                while r <= R + 1e-9:
                    if first:
                        seg_in = Segment(cx, cy, pos[2], cx, cy, z,
                                         dia, col, False, drill=True,
                                         spindle_on=spindle_on[0],
                                         cmd_index=idx,
                                         executed_index=stats["executed_steps"])
                        check_collision(seg_in); apply_cut(seg_in)
                        cmd_to_segments.setdefault(idx, []).append(len(segs))
                        segs.append(seg_in)
                        pos[2] = z
                        first = False
                    do_arc(cx, cy, cx + r, cy, z, cw, dia, col, idx)
                    if r + step <= R + 1e-9:
                        do_arc(cx, cy, cx + r + step, cy, z, cw, dia, col, idx)
                    r += step
                pos[0], pos[1], pos[2] = cx + r - step, cy, z
                stats["zmin"] = min(stats["zmin"], z)
                upd(cx - R, cy - R); upd(cx + R, cy + R)

            elif m == "PROBE":
                nx, ny, nz = resolve(self._n(p.get("x", pos[0])),
                                     self._n(p.get("y", pos[1])),
                                     self._n(p.get("z", pos[2])))
                seg = Segment(pos[0], pos[1], pos[2], nx, ny, nz, dia, col,
                              False, spindle_on=spindle_on[0], cmd_index=idx,
                              executed_index=stats["executed_steps"])
                check_collision(seg); apply_cut(seg)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg)
                stats["cut_len"] += math.hypot(nx - pos[0], ny - pos[1])
                pos[0], pos[1], pos[2] = nx, ny, nz; upd(nx, ny)

            elif m == "MACHINE":
                nx = self._n(p.get("x", pos[0]))
                ny = self._n(p.get("y", pos[1]))
                nz = self._n(p.get("z", pos[2]))
                seg = Segment(pos[0], pos[1], pos[2], nx, ny, nz, dia, col,
                              True, spindle_on=spindle_on[0], cmd_index=idx,
                              executed_index=stats["executed_steps"])
                check_collision(seg)
                cmd_to_segments.setdefault(idx, []).append(len(segs))
                segs.append(seg)
                stats["rapid_len"] += math.hypot(nx - pos[0], ny - pos[1])
                pos[0], pos[1], pos[2] = nx, ny, nz; upd(nx, ny)

        pre_end = len(self.preamble)
        if pre_end > 0:
            pre_interp = ProgramInterp(self.preamble, live_vars,
                                       max_steps=200000,
                                       functions=self.functions)
            pre_interp.run(on_cmd, 0, pre_end)
        interp.run(on_cmd, 0, upto, step_limit=step_limit or 200000)
        if self.postamble:
            post_interp = ProgramInterp(self.postamble, interp.vars,
                                        max_steps=200000,
                                        functions=self.functions)
            post_interp.run(on_cmd, 0, len(self.postamble))

        if not segs:
            minx[0] = miny[0] = -10; maxx[0] = maxy[0] = 10
        pad = max(maxx[0] - minx[0], maxy[0] - miny[0]) * 0.05 + 1.0
        bounds = (minx[0] - pad, miny[0] - pad, maxx[0] + pad, maxy[0] + pad)
        if stats["zmin"] == float("inf"):
            stats["zmin"] = 0.0
        stats["heightmap"] = hm
        stats["a"], stats["b"], stats["c"] = rot[0], rot[1], rot[2]
        stats["cmd_to_segments"] = cmd_to_segments
        return segs, bounds, stats