# -*- coding: utf-8 -*-
"""Описание мнемоник псевдокода + RS-274-адреса + группы."""

# RS-274 адреса и их назначение (для UI)
RS274_ADDRESSES = {
    "A": "A-axis of machine",
    "B": "B-axis of machine",
    "C": "C-axis of machine",
    "D": "tool radius compensation number",
    "F": "feedrate",
    "H": "tool length offset index",
    "I": "X-axis offset for arcs",
    "J": "Y-axis offset for arcs",
    "K": "Z-axis offset for arcs",
    "L": "repetitions / key with G10",
    "N": "line number",
    "P": "dwell / key with G10",
    "Q": "feed increment in G83",
    "R": "arc radius / cycle plane",
    "S": "spindle speed / cycle plane",
    "T": "tool selection",
    "X": "X-axis",
    "Y": "Y-axis",
    "Z": "Z-axis",
}

# Группы кодов для сортировки и фильтра
CODE_GROUPS = {
    "MOTION": "Движение (G0–G3, G12, G13, G31, G33, G38.x)",
    "CANNED": "Циклы сверления/резьбы (G73, G74, G76, G80–G89)",
    "PLANE": "Плоскости и единицы (G17–G21, G70, G71, G90.x, G91.x)",
    "COMPENSATION": "Коррекции (G40–G49)",
    "OFFSET": "Смещения/масштаб/повороты (G10, G50–G53, G54–G59, G68, G69, G92)",
    "POLAR": "Полярные координаты (G15, G16)",
    "FEED": "Режимы подачи (G93–G97)",
    "RETURN": "Возвраты (G28, G28.1, G30, G98, G99)",
    "SPINDLE": "Шпиндель (M3–M5, M19)",
    "COOLANT": "Охлаждение (M7–M9)",
    "PROGRAM": "Программа (M0, M1, M2, M30, M47, M48, M49)",
    "TOOL": "Инструмент (T, M6, M61)",
    "SUB": "Подпрограммы (M98, M99)",
    "MISC": "Прочее",
    "PSEUDO": "Псевдокод (IF, GOTO, VAR, CALL_FUNC)",
}

# Основные псевдокоды
COMMAND_DEFS = {
    "TOOL":     ("Выбрать инструмент", [("tool","int",1)], "TOOL"),
    "RAPID":    ("Быстрое перемещение (G0)", [("x","float",0.0),("y","float",0.0),("z","float",0.0),("a","float",0.0),("b","float",0.0),("c","float",0.0)], "MOTION"),
    "FEED":     ("Рабочее перемещение (G1)", [("x","float",0.0),("y","float",0.0),("z","float",0.0),("a","float",0.0),("b","float",0.0),("c","float",0.0),("f","float",200.0)], "MOTION"),
    "ARC_CW":   ("Дуга по часовой (G2)", [("x","float",0.0),("y","float",0.0),("z","float",0.0),("cx","float",0.0),("cy","float",0.0),("f","float",200.0)], "MOTION"),
    "ARC_CCW":  ("Дуга против часовой (G3)", [("x","float",0.0),("y","float",0.0),("z","float",0.0),("cx","float",0.0),("cy","float",0.0),("f","float",200.0)], "MOTION"),
    "DWELL":    ("Пауза (G4)", [("sec","float",1.0)], "MISC"),
    "DRILL":    ("Сверление (G81/G80)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("f","float",60.0)], "CANNED"),
    "PECK":     ("Сверление с отводом (G83)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("q","float",1.0),("f","float",60.0)], "CANNED"),
    "CHIP":     ("Сверление с ломкой (G73)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("q","float",1.0),("f","float",60.0)], "CANNED"),
    "BORE":     ("Расточка (G82)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("p","float",0.5),("f","float",60.0)], "CANNED"),
    "CANCEL":   ("Отмена цикла (G80)", [], "CANNED"),
    "SPIN":     ("Шпиндель (M3/M4/M5)", [("on","int",1),("rpm","int",8000),("ccw","int",0)], "SPINDLE"),
    "COOL":     ("Охлаждение (M7/M8/M9)", [("on","int",1),("mist","int",0)], "COOLANT"),
    "CLAMP":    ("Зажим/разжим (M10/M11)", [("on","int",1)], "MISC"),
    "WCS":      ("Система координат (G54..G59)", [("num","int",54)], "OFFSET"),
    "MACHINE":  ("Машинные координаты (G53)", [("x","float",0.0),("y","float",0.0),("z","float",0.0)], "OFFSET"),
    "G10":      ("Установка смещения/координат (G10)", [("l","int",2),("p","int",1),("x","float",0.0),("y","float",0.0),("z","float",0.0)], "OFFSET"),
    "G92SET":   ("Смещение (G92)", [("x","float",0.0),("y","float",0.0),("z","float",0.0)], "OFFSET"),
    "G92CLR":   ("Сброс смещения (G92.1)", [], "OFFSET"),
    "G92SUSP":  ("Приостановить G92 (G92.2)", [], "OFFSET"),
    "G92RES":   ("Восстановить G92 (G92.3)", [], "OFFSET"),
    "PLANE_XY": ("Плоскость XY (G17)", [], "PLANE"),
    "PLANE_XZ": ("Плоскость XZ (G18)", [], "PLANE"),
    "PLANE_YZ": ("Плоскость YZ (G19)", [], "PLANE"),
    "UNITS_IN": ("Дюймы (G20)", [], "PLANE"),
    "UNITS_MM": ("Миллиметры (G21)", [], "PLANE"),
    "UNITS_IN2": ("Дюймы (G70)", [], "PLANE"),
    "UNITS_MM2": ("Миллиметры (G71)", [], "PLANE"),
    "CUTCOMP_OFF": ("Отмена коррекции (G40)", [], "COMPENSATION"),
    "CUTCOMP_L":   ("Коррекция слева (G41)", [("d","int",1)], "COMPENSATION"),
    "CUTCOMP_R":   ("Коррекция справа (G42)", [("d","int",1)], "COMPENSATION"),
    "TOOLCOMP_P":  ("Коррекция длины + (G43)", [("h","int",1),("z","float",0.0)], "COMPENSATION"),
    "TOOLCOMP_M":  ("Коррекция длины - (G44)", [("h","int",1)], "COMPENSATION"),
    "TOOLCOMP_OFF":("Отмена длины (G49)", [], "COMPENSATION"),
    "SCALE_OFF": ("Отмена масштаба (G50)", [], "OFFSET"),
    "SCALE_ON":  ("Масштабирование (G51)", [("x","float",1.0),("y","float",1.0),("z","float",1.0)], "OFFSET"),
    "LOCAL_OFF": ("Локальное смещение (G52)", [("x","float",0.0),("y","float",0.0),("z","float",0.0)], "OFFSET"),
    "ROT_ON":    ("Поворот (G68)", [("x","float",0.0),("y","float",0.0),("angle","float",0.0)], "OFFSET"),
    "ROT_OFF":   ("Отмена поворота (G69)", [], "OFFSET"),
    "POLAR_ON":  ("Полярные координаты (G16)", [], "POLAR"),
    "POLAR_OFF": ("Отмена полярных (G15)", [], "POLAR"),
    "ABS":       ("Абсолютные (G90)", [], "PLANE"),
    "INC":       ("Инкрементальные (G91)", [], "PLANE"),
    "ARC_ABS":   ("Абсолютный I/J (G90.1)", [], "PLANE"),
    "ARC_INC":   ("Инкрементальный I/J (G91.1)", [], "PLANE"),
    "FEED_INV":  ("Обратное время (G93)", [], "FEED"),
    "FEED_IPM":  ("Подача в мин (G94)", [], "FEED"),
    "FEED_IPR":  ("Подача на оборот (G95)", [], "FEED"),
    "CSS":       ("Постоянная скорость (G96)", [("v","float",100.0)], "FEED"),
    "RPM_FIX":   ("Фикс. обороты (G97)", [("rpm","int",8000)], "FEED"),
    "EXACT":     ("Точный останов (G61)", [], "PLANE"),
    "SMOOTH":    ("Сглаживание (G64)", [], "PLANE"),
    "RET_INIT":  ("Возврат в исходную (G98)", [], "RETURN"),
    "RET_R":     ("Возврат в R (G99)", [], "RETURN"),
    "HOME":      ("Референтная точка (G28)", [], "RETURN"),
    "HOME2":     ("Вторая референтная (G30)", [], "RETURN"),
    "HOME_BASE": ("Базовые оси (G28.1)", [], "RETURN"),
    "PROBE":     ("Пробинг/останов по сигналу (G31)", [("x","float",0.0),("y","float",0.0),("z","float",0.0),("f","float",100.0)], "MOTION"),
    "POCKET_CW": ("Круглый карман по часовой (G12)", [("i","float",10.0),("j","float",10.0),("z","float",-2.0),("f","float",200.0)], "CANNED"),
    "POCKET_CCW":("Круглый карман против часовой (G13)", [("i","float",10.0),("j","float",10.0),("z","float",-2.0),("f","float",200.0)], "CANNED"),
    "THREAD_R":  ("Правая резьба (G84)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("p","float",0.0),("f","float",60.0)], "CANNED"),
    "BORE_STD":  ("Развёртывание (G85)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("f","float",60.0)], "CANNED"),
    "BORE_SPINDLE": ("Растачивание шпинделем (G86)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("f","float",60.0)], "CANNED"),
    "BORE_BACK": ("Обратное растачивание (G87)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("f","float",60.0)], "CANNED"),
    "BORE_MANUAL": ("Растачивание вручную (G88)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("p","float",0.0),("f","float",60.0)], "CANNED"),
    "BORE_FINE": ("Точное растачивание (G89)", [("x","float",0.0),("y","float",0.0),("z","float",-5.0),("r","float",1.0),("p","float",0.0),("f","float",60.0)], "CANNED"),
    "VAR":       ("Присвоить переменную", [("name","str","#100"),("value","str","0")], "PSEUDO"),
    "VAR_ADD":   ("Прибавить", [("name","str","#100"),("delta","str","1")], "PSEUDO"),
    "LABEL":     ("Метка", [("name","str","L1")], "PSEUDO"),
    "IF":        ("Условный переход", [("lhs","str","#100"),("op","str","EQ"),("rhs","str","0"),("target","str","L1")], "PSEUDO"),
    "GOTO":      ("Переход", [("target","str","L1")], "PSEUDO"),
    "SUB_CALL":  ("M98", [("name","str","1000"),("repeat","int",1)], "SUB"),
    "SUB_RET":   ("M99", [], "SUB"),
    "CALL_FUNC": ("Вызов функции из библиотеки", [("name","str",""),("mode","str","inline")], "PSEUDO"),
    "END":       ("Конец (M30)", [], "PROGRAM"),
    "STOP":      ("Стоп (M0/M1)", [("optional","int",0)], "PROGRAM"),
    "REWIND":    ("Перезапуск (M47)", [], "PROGRAM"),
    "OVR_ON":    ("Переопределение вкл (M48)", [], "PROGRAM"),
    "OVR_OFF":   ("Переопределение выкл (M49)", [], "PROGRAM"),
    "#":         ("Комментарий", [("text","str","")], "MISC"),
}

ORDERED_MNEMONICS = list(COMMAND_DEFS.keys())


def get_command_group(mnemonic: str) -> str:
    """Группа для сортировки."""
    d = COMMAND_DEFS.get(mnemonic)
    if not d:
        return "MISC"
    if len(d) > 2:
        return d[2]
    return "MISC"


def get_command_desc(mnemonic: str) -> str:
    d = COMMAND_DEFS.get(mnemonic)
    return d[0] if d else ""


def get_command_fields(mnemonic: str):
    d = COMMAND_DEFS.get(mnemonic)
    return d[1] if d else []