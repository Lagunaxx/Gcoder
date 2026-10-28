# -*- coding: utf-8 -*-
"""Общие константы."""

APP_NAME = "GCodeEditor"
APP_ORG = "Mach3"


class ShadingMode:
    WIREFRAME = "wireframe"
    TRANSPARENT = "transparent"
    FLAT = "flat"
    SMOOTH = "smooth"


class LightingMode:
    HEADLIGHT = "headlight"
    CUSTOM = "custom"


class LightKind:
    HEADLIGHT = "headlight"
    CAMERA = "camera"
    SCENE = "scene"


class LightType:
    SPHERE = "sphere"
    SPOT = "spot"
    DIRECTIONAL = "directional"