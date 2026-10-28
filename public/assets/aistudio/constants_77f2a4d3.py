# -*- coding: utf-8 -*-
"""Константы UI (ре-экспорт + DisplayMode для совместимости)."""

from gcode_editor.core.constants import (   # noqa: F401
    APP_NAME, APP_ORG,
    ShadingMode, LightingMode, LightKind, LightType,
)


class DisplayMode:
    """Оставлено для обратной совместимости.
    В новом UI — это независимые чекбоксы show_toolpath / show_material."""
    TOOLPATH = "toolpath"
    MATERIAL = "material"


__all__ = [
    "APP_NAME", "APP_ORG",
    "ShadingMode", "LightingMode", "LightKind", "LightType",
    "DisplayMode",
]