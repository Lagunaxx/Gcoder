# -*- coding: utf-8 -*-
"""Сохранение/загрузка G-кода, проектов, функций и CSV инструментов."""

import csv
import json
import os
from dataclasses import asdict

from gcode_editor.core.models import (
    Tool, Stock, UserVar, Command, FunctionDef, FunctionParam,
    SimSettings, AppSettings, LightingSource, default_lights,
)


def export_gcode(path: str, code_lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(code_lines))
        if code_lines and not code_lines[-1].endswith("\n"):
            f.write("\n")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ============================================================
#                       ПРОЕКТ
# ============================================================

def _lighting_to_dict(ls: LightingSource) -> dict:
    return {
        "kind": ls.kind, "intensity": ls.intensity, "color": ls.color,
        "position": list(ls.position),
        "focal_point": list(ls.focal_point),
        "light_type": ls.light_type,
        "cone_angle": ls.cone_angle,
        "enabled": ls.enabled,
    }


def _lighting_from_dict(d: dict) -> LightingSource:
    return LightingSource(
        kind=d.get("kind", "scene"),
        intensity=float(d.get("intensity", 1.0)),
        color=d.get("color", "#ffffff"),
        position=tuple(d.get("position", (50.0, -50.0, 80.0))),
        focal_point=tuple(d.get("focal_point", (0.0, 0.0, 0.0))),
        light_type=d.get("light_type", "sphere"),
        cone_angle=float(d.get("cone_angle", 30.0)),
        enabled=bool(d.get("enabled", True)),
    )


def _sim_to_dict(s: SimSettings) -> dict:
    return asdict(s)


def _sim_from_dict(d: dict) -> SimSettings:
    s = SimSettings()
    for k, v in d.items():
        if hasattr(s, k):
            try:
                setattr(s, k, v)
            except Exception:
                pass
    return s


def _cmd_to_dict(c: Command) -> dict:
    return {"mnemonic": c.mnemonic, "params": c.params, "raw": c.raw}


def _cmd_from_dict(d: dict) -> Command:
    return Command(d["mnemonic"], d.get("params", {}), d.get("raw", ""))


def _func_to_dict(fn: FunctionDef) -> dict:
    return {
        "name": fn.name, "title": fn.title,
        "description": fn.description,
        "params": [asdict(p) for p in fn.params],
        "body": [_cmd_to_dict(c) for c in fn.body],
    }


def _func_from_dict(d: dict) -> FunctionDef:
    return FunctionDef(
        name=d.get("name", "NEW_FUNC"),
        title=d.get("title", ""),
        description=d.get("description", ""),
        params=[FunctionParam(**p) for p in d.get("params", [])],
        body=[_cmd_from_dict(c) for c in d.get("body", [])],
    )


def save_project(path: str, tools, variables, stock, commands,
                 view, settings: AppSettings):
    data = {
        "version": 4,
        "tools": [asdict(t) for t in tools],
        "variables": [asdict(v) for v in variables],
        "stock": asdict(stock),
        "commands": [_cmd_to_dict(c) for c in commands],
        "view": view,
        "settings": {
            "sim": _sim_to_dict(settings.sim),
            "lights": [_lighting_to_dict(l) for l in settings.lights],
            "lighting_mode": settings.lighting_mode,
            "toolpath_visible": settings.toolpath_visible,
            "material_visible": settings.material_visible,
            "ignore_rapid_in_material": settings.ignore_rapid_in_material,
            "unroll_loops": settings.unroll_loops,
            "step_limit": settings.step_limit,
            "functions": [_func_to_dict(f) for f in settings.functions],
            "preamble": [_cmd_to_dict(c) for c in settings.preamble],
            "postamble": [_cmd_to_dict(c) for c in settings.postamble],
            "code_order": settings.code_order,
            "code_hidden": settings.code_hidden,
            "code_sort_mode": settings.code_sort_mode,
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tools = [Tool(**t) for t in data.get("tools", [])]
    variables = [UserVar(**v) for v in data.get("variables", [])]
    st = data.get("stock")
    stock = Stock(**st) if st else Stock()
    commands = [_cmd_from_dict(c) for c in data.get("commands", [])]
    view = data.get("view", {})

    settings = AppSettings()
    sdata = data.get("settings", {})
    if sdata:
        settings.sim = _sim_from_dict(sdata.get("sim", {}))
        lights_data = sdata.get("lights")
        if lights_data:
            settings.lights = [_lighting_from_dict(x) for x in lights_data]
        settings.lighting_mode = sdata.get("lighting_mode", "headlight")
        settings.toolpath_visible = bool(sdata.get("toolpath_visible", True))
        settings.material_visible = bool(sdata.get("material_visible", False))
        settings.ignore_rapid_in_material = bool(
            sdata.get("ignore_rapid_in_material", False))
        settings.unroll_loops = bool(sdata.get("unroll_loops", False))
        settings.step_limit = int(sdata.get("step_limit", 0))
        settings.functions = [_func_from_dict(x)
                              for x in sdata.get("functions", [])]
        settings.preamble = [_cmd_from_dict(c)
                             for c in sdata.get("preamble", [])]
        settings.postamble = [_cmd_from_dict(c)
                              for c in sdata.get("postamble", [])]
        settings.code_order = list(sdata.get("code_order", []))
        settings.code_hidden = list(sdata.get("code_hidden", []))
        settings.code_sort_mode = sdata.get("code_sort_mode", "custom")

    return tools, variables, stock, commands, view, settings, data


# ============================================================
#             БИБЛИОТЕКА ФУНКЦИЙ (папка / файл)
# ============================================================

def functions_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p = os.path.join(base, "functions")
    os.makedirs(p, exist_ok=True)
    return p


def save_function_file(path: str, fn: FunctionDef):
    data = {"version": 1, "function": _func_to_dict(fn)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_function_file(path: str) -> FunctionDef:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("function", data)
    return _func_from_dict(raw)


def load_functions_dir(path: str = None) -> list:
    path = path or functions_dir()
    result = []
    if not os.path.isdir(path):
        return result
    for name in sorted(os.listdir(path)):
        if not name.lower().endswith(".json"):
            continue
        full = os.path.join(path, name)
        try:
            result.append(load_function_file(full))
        except Exception as e:
            print(f"[functions] skip {name}: {e}")
    return result


def save_functions_to_dir(path: str, functions):
    os.makedirs(path, exist_ok=True)
    for name in os.listdir(path):
        if name.lower().endswith(".json"):
            try:
                os.remove(os.path.join(path, name))
            except Exception:
                pass
    for fn in functions:
        safe = "".join(ch if ch.isalnum() or ch in "_-" else "_"
                       for ch in fn.name) or "func"
        full = os.path.join(path, f"{safe}.json")
        save_function_file(full, fn)


# ============================================================
#                       CSV ИНСТРУМЕНТОВ
# ============================================================

def export_tools_csv(path: str, tools):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["number", "name", "diameter", "feed", "rpm", "color"])
        for t in tools:
            w.writerow([t.number, t.name, t.diameter, t.feed, t.rpm, t.color])


def import_tools_csv(path: str):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    if rows and rows[0] and rows[0][0].strip().lower() == "number":
        rows = rows[1:]
    tools = []
    for r in rows:
        if len(r) < 5:
            continue
        try:
            tools.append(Tool(
                int(float(r[0])), r[1], float(r[2]), float(r[3]),
                int(float(r[4])),
                r[5] if len(r) > 5 and r[5] else "#3399ff"))
        except Exception:
            pass
    return tools