# -*- coding: utf-8 -*-
"""Стартовые шаблоны функций (создаются при первом запуске)."""

import os

from gcode_editor.core.models import (
    FunctionDef, FunctionParam, Command,
)
from gcode_editor.io import file_io


def build_seed_functions():
    return [
        FunctionDef(
            name="TOOL_CHANGE",
            title="Безопасная смена инструмента",
            description="Останов шпинделя, охлаждения, отвод на Z10, M6.",
            params=[
                FunctionParam("t", "1", "Номер инструмента"),
                FunctionParam("rpm", "8000", "Обороты"),
            ],
            body=[
                Command("SPIN", {"on": 0, "rpm": 0, "ccw": 0}),
                Command("COOL", {"on": 0, "mist": 0}),
                Command("RAPID", {"x": 0, "y": 0, "z": 10}),
                Command("TOOL", {"tool": "{t}"}),
                Command("SPIN", {"on": 1, "rpm": "{rpm}", "ccw": 0}),
            ],
        ),
        FunctionDef(
            name="DRILL_GRID",
            title="Массив отверстий сеткой",
            description="Сверлит nx×ny отверстий с шагом step, начиная с (x0,y0).",
            params=[
                FunctionParam("x0", "0", "Начальный X"),
                FunctionParam("y0", "0", "Начальный Y"),
                FunctionParam("nx", "3", "Число по X"),
                FunctionParam("ny", "3", "Число по Y"),
                FunctionParam("step", "10", "Шаг"),
                FunctionParam("depth", "-5", "Глубина сверления"),
                FunctionParam("f", "80", "Подача сверления"),
            ],
            body=[
                Command("VAR", {"name": "#310", "value": "0"}),
                Command("LABEL", {"name": "ROW"}),
                Command("VAR", {"name": "#311", "value": "0"}),
                Command("LABEL", {"name": "COL"}),
                Command("RAPID", {"x": "{x0 + #311*step}",
                                   "y": "{y0 + #310*step}", "z": 5}),
                Command("DRILL", {"x": "{x0 + #311*step}",
                                   "y": "{y0 + #310*step}",
                                   "z": "{depth}", "f": "{f}"}),
                Command("VAR_ADD", {"name": "#311", "delta": "1"}),
                Command("IF", {"lhs": "#311", "op": "LT",
                                "rhs": "{nx}", "target": "COL"}),
                Command("VAR_ADD", {"name": "#310", "delta": "1"}),
                Command("IF", {"lhs": "#310", "op": "LT",
                                "rhs": "{ny}", "target": "ROW"}),
            ],
        ),
        FunctionDef(
            name="POCKET_RECT",
            title="Прямоугольный карман (зигзаг)",
            description="Фрезерует прямоугольник x0..x1, y0..y1 с шагом step на глубине z.",
            params=[
                FunctionParam("x0", "0", "Начало X"),
                FunctionParam("y0", "0", "Начало Y"),
                FunctionParam("x1", "50", "Конец X"),
                FunctionParam("y1", "50", "Конец Y"),
                FunctionParam("step", "3", "Шаг строк"),
                FunctionParam("z", "-1", "Глубина"),
                FunctionParam("f", "150", "Подача"),
            ],
            body=[
                Command("VAR", {"name": "#320", "value": "0"}),
                Command("LABEL", {"name": "ROW"}),
                Command("RAPID", {"x": "{x0}",
                                   "y": "{y0 + #320*step}", "z": 5}),
                Command("FEED", {"x": "{x0}",
                                  "y": "{y0 + #320*step}",
                                  "z": "{z}", "f": "{f}"}),
                Command("FEED", {"x": "{x1}",
                                  "y": "{y0 + #320*step}",
                                  "z": "{z}", "f": "{f}"}),
                Command("RAPID", {"x": "{x1}",
                                   "y": "{y0 + #320*step}", "z": 5}),
                Command("VAR_ADD", {"name": "#320", "delta": "1"}),
                Command("IF", {"lhs": "{y0 + #320*step}",
                                "op": "LE", "rhs": "{y1}",
                                "target": "ROW"}),
            ],
        ),
    ]


def ensure_seed_functions():
    """Создаёт шаблоны в папке functions/ при первом запуске."""
    d = file_io.functions_dir()
    if not any(n.lower().endswith(".json") for n in os.listdir(d)):
        for fn in build_seed_functions():
            safe = "".join(ch if ch.isalnum() or ch in "_-" else "_"
                           for ch in fn.name) or "func"
            path = os.path.join(d, f"{safe}.json")
            file_io.save_function_file(path, fn)