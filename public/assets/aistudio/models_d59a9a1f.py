# -*- coding: utf-8 -*-
"""Модели данных."""

from dataclasses import dataclass, field, asdict
from typing import List, Tuple


@dataclass
class Tool:
    number: int
    name: str
    diameter: float
    feed: float
    rpm: int
    color: str = "#3399ff"
    length_offset: float = 0.0
    radius_offset: float = 0.0


@dataclass
class Stock:
    mode: str = "box"
    x: float = 120.0
    y: float = 120.0
    z: float = 10.0
    px: float = 0.0
    py: float = 0.0
    pz: float = 0.0
    color: str = "#7080b0"
    visible: bool = True
    file_path: str = ""
    mesh_name: str = ""
    mesh_color: str = "#b0b0c0"
    mesh_scale: float = 1.0
    mesh_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def bounds(self):
        return (self.px, self.py, self.px + self.x, self.py + self.y,
                self.pz, self.pz - self.z)


@dataclass
class UserVar:
    name: str
    value: str


@dataclass
class Command:
    mnemonic: str
    params: dict = field(default_factory=dict)
    raw: str = ""

    def to_pseudo(self, n_index: int = -1) -> str:
        prefix = f"[N{(n_index + 1) * 10:03d}] " if n_index >= 0 else ""
        if self.mnemonic == "#":
            return prefix + "# " + self.raw
        if not self.params:
            return prefix + self.mnemonic
        parts = [self.mnemonic]
        for k, v in self.params.items():
            if isinstance(v, float):
                parts.append(f"{k}={v:g}")
            else:
                parts.append(f"{k}={v}")
        return prefix + " ".join(parts)


@dataclass
class FunctionParam:
    name: str
    default: str = "0"
    description: str = ""


@dataclass
class FunctionDef:
    name: str = "NEW_FUNC"
    title: str = ""
    description: str = ""
    params: List[FunctionParam] = field(default_factory=list)
    body: List[Command] = field(default_factory=list)


@dataclass
class LightingSource:
    kind: str = "scene"
    intensity: float = 1.0
    color: str = "#ffffff"
    position: Tuple[float, float, float] = (50.0, -50.0, 80.0)
    focal_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    light_type: str = "sphere"
    cone_angle: float = 30.0
    enabled: bool = True


@dataclass
class SimSettings:
    auto_voxel_xy: bool = True
    voxel_xy: float = 0.5
    voxel_z: float = 1.0
    max_memory_fraction: float = 0.5
    show_toolpath: bool = True
    show_material: bool = False
    rapid_line_width: float = 1.0
    feed_line_width: float = 3.0
    rapid_dash: bool = True


def default_lights() -> List[LightingSource]:
    return [
        LightingSource(kind="headlight", intensity=1.0, color="#ffffff"),
        LightingSource(kind="scene", intensity=0.5, color="#e0e8ff",
                       position=(100.0, -80.0, 120.0),
                       focal_point=(0.0, 0.0, 0.0),
                       light_type="directional", enabled=True),
        LightingSource(kind="scene", intensity=0.4, color="#ffe8c0",
                       position=(-120.0, 100.0, 80.0),
                       focal_point=(0.0, 0.0, 0.0),
                       light_type="directional", enabled=True),
        LightingSource(kind="camera", intensity=0.3, color="#ffffff"),
    ]


@dataclass
class AppSettings:
    sim: SimSettings = field(default_factory=SimSettings)
    lights: List[LightingSource] = field(default_factory=default_lights)
    lighting_mode: str = "headlight"
    toolpath_visible: bool = True
    material_visible: bool = False
    ignore_rapid_in_material: bool = False
    unroll_loops: bool = False
    step_limit: int = 0
    functions: List[FunctionDef] = field(default_factory=list)
    preamble: List[Command] = field(default_factory=list)
    postamble: List[Command] = field(default_factory=list)
    # Настройки списка кодов (глобально в QSettings, но храним и в AppSettings
    # для удобства переноса)
    code_order: List[str] = field(default_factory=list)
    code_hidden: List[str] = field(default_factory=list)
    code_sort_mode: str = "custom"  # custom | alpha | desc | group