package com.example.core

import com.example.model.Command
import com.example.model.FunctionDef
import com.example.model.FunctionParam

data class ParamDef(
    val name: String,
    val type: String, // "int", "float", "str", "op"
    val defaultVal: Any,
    val description: String = ""
)

data class CommandDef(
    val mnemonic: String,
    val description: String,
    val params: List<ParamDef>,
    val group: String
)

object CommandsDef {
    val GROUPS = mapOf(
        "MOTION" to "Движение (G0–G3, G12, G13, G31)",
        "CANNED" to "Циклы сверления/резьбы (G73, G80–G89)",
        "PLANE" to "Плоскости и единицы (G17–G21, G90, G91)",
        "COMPENSATION" to "Коррекции (G40–G49)",
        "OFFSET" to "Смещения/масштаб/повороты (G10, G54–G59, G92)",
        "POLAR" to "Полярные координаты (G15, G16)",
        "FEED" to "Режимы подачи (G93–G97)",
        "RETURN" to "Возвраты (G28, G30, G98, G99)",
        "SPINDLE" to "Шпиндель (M3–M5)",
        "COOLANT" to "Охлаждение (M7–M9)",
        "PROGRAM" to "Программа (M0, M1, M2, M30)",
        "TOOL" to "Инструмент (T, M6)",
        "SUB" to "Подпрограммы (M98, M99)",
        "PSEUDO" to "Псевдокод (IF, GOTO, VAR, CALL_FUNC)",
        "MISC" to "Прочее"
    )

    val DEFINITIONS = mapOf(
        "TOOL" to CommandDef("TOOL", "Выбрать инструмент", listOf(ParamDef("tool", "int", 1, "Номер фрезы")), "TOOL"),
        "RAPID" to CommandDef("RAPID", "Быстрое перемещение (G0)", listOf(
            ParamDef("x", "float", 0.0, "Координата X"),
            ParamDef("y", "float", 0.0, "Координата Y"),
            ParamDef("z", "float", 0.0, "Координата Z"),
            ParamDef("a", "float", 0.0, "Ось A (угол)"),
            ParamDef("b", "float", 0.0, "Ось B"),
            ParamDef("c", "float", 0.0, "Ось C")
        ), "MOTION"),
        "FEED" to CommandDef("FEED", "Рабочее перемещение (G1)", listOf(
            ParamDef("x", "float", 0.0, "Координата X"),
            ParamDef("y", "float", 0.0, "Координата Y"),
            ParamDef("z", "float", 0.0, "Координата Z"),
            ParamDef("f", "float", 200.0, "Подача (мм/мин)"),
            ParamDef("a", "float", 0.0, "Ось A"),
            ParamDef("b", "float", 0.0, "Ось B"),
            ParamDef("c", "float", 0.0, "Ось C")
        ), "MOTION"),
        "ARC_CW" to CommandDef("ARC_CW", "Дуга по часовой (G2)", listOf(
            ParamDef("x", "float", 0.0, "Конечный X"),
            ParamDef("y", "float", 0.0, "Конечный Y"),
            ParamDef("z", "float", 0.0, "Конечный Z"),
            ParamDef("cx", "float", 0.0, "Центр дуги X"),
            ParamDef("cy", "float", 0.0, "Центр дуги Y"),
            ParamDef("f", "float", 200.0, "Подача")
        ), "MOTION"),
        "ARC_CCW" to CommandDef("ARC_CCW", "Дуга против часовой (G3)", listOf(
            ParamDef("x", "float", 0.0, "Конечный X"),
            ParamDef("y", "float", 0.0, "Конечный Y"),
            ParamDef("z", "float", 0.0, "Конечный Z"),
            ParamDef("cx", "float", 0.0, "Центр дуги X"),
            ParamDef("cy", "float", 0.0, "Центр дуги Y"),
            ParamDef("f", "float", 200.0, "Подача")
        ), "MOTION"),
        "DWELL" to CommandDef("DWELL", "Пауза (G4)", listOf(ParamDef("sec", "float", 1.0, "Время в сек")), "MISC"),
        "DRILL" to CommandDef("DRILL", "Сверление (G81/G80)", listOf(
            ParamDef("x", "float", 0.0, "Координата X"),
            ParamDef("y", "float", 0.0, "Координата Y"),
            ParamDef("z", "float", -5.0, "Глубина отверстия Z"),
            ParamDef("r", "float", 1.0, "Плоскость отвода R"),
            ParamDef("f", "float", 60.0, "Подача сверления")
        ), "CANNED"),
        "PECK" to CommandDef("PECK", "Сверление с отводом (G83)", listOf(
            ParamDef("x", "float", 0.0, "Координата X"),
            ParamDef("y", "float", 0.0, "Координата Y"),
            ParamDef("z", "float", -5.0, "Глубина Z"),
            ParamDef("r", "float", 1.0, "Плоскость отвода R"),
            ParamDef("q", "float", 1.0, "Глубина одного прохода Q"),
            ParamDef("f", "float", 60.0, "Подача")
        ), "CANNED"),
        "CHIP" to CommandDef("CHIP", "Сверление с ломкой стружки (G73)", listOf(
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", -5.0, "Z"),
            ParamDef("r", "float", 1.0, "R"),
            ParamDef("q", "float", 1.0, "Q"),
            ParamDef("f", "float", 60.0, "F")
        ), "CANNED"),
        "BORE" to CommandDef("BORE", "Расточка с выдержкой (G82)", listOf(
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", -5.0, "Z"),
            ParamDef("r", "float", 1.0, "R"),
            ParamDef("p", "float", 0.5, "Пауза P"),
            ParamDef("f", "float", 60.0, "F")
        ), "CANNED"),
        "CANCEL" to CommandDef("CANCEL", "Отмена цикла (G80)", emptyList(), "CANNED"),
        "SPIN" to CommandDef("SPIN", "Шпиндель (M3/M4/M5)", listOf(
            ParamDef("on", "int", 1, "1 = Вкл, 0 = Выкл"),
            ParamDef("rpm", "int", 8000, "Обороты (об/мин)"),
            ParamDef("ccw", "int", 0, "1 = Против часовой (M4), 0 = По часовой (M3)")
        ), "SPINDLE"),
        "COOL" to CommandDef("COOL", "Охлаждение (M7/M8/M9)", listOf(
            ParamDef("on", "int", 1, "1 = Вкл, 0 = Выкл"),
            ParamDef("mist", "int", 0, "1 = Туман M7, 0 = Струя M8")
        ), "COOLANT"),
        "CLAMP" to CommandDef("CLAMP", "Зажим/разжим (M10/M11)", listOf(
            ParamDef("on", "int", 1, "1 = Зажать M10, 0 = Разжать M11")
        ), "MISC"),
        "WCS" to CommandDef("WCS", "Система координат (G54..G59)", listOf(
            ParamDef("num", "int", 54, "Номер системы (54-59)")
        ), "OFFSET"),
        "MACHINE" to CommandDef("MACHINE", "Машинные координаты (G53)", listOf(
            ParamDef("x", "float", 0.0, "Машинный X"),
            ParamDef("y", "float", 0.0, "Машинный Y"),
            ParamDef("z", "float", 0.0, "Машинный Z")
        ), "OFFSET"),
        "G10" to CommandDef("G10", "Установка смещения (G10)", listOf(
            ParamDef("l", "int", 2, "Режим L"),
            ParamDef("p", "int", 1, "Номер P"),
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", 0.0, "Z")
        ), "OFFSET"),
        "G92SET" to CommandDef("G92SET", "Смещение нуля (G92)", listOf(
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", 0.0, "Z")
        ), "OFFSET"),
        "G92CLR" to CommandDef("G92CLR", "Сброс смещения (G92.1)", emptyList(), "OFFSET"),
        "PLANE_XY" to CommandDef("PLANE_XY", "Плоскость XY (G17)", emptyList(), "PLANE"),
        "PLANE_XZ" to CommandDef("PLANE_XZ", "Плоскость XZ (G18)", emptyList(), "PLANE"),
        "PLANE_YZ" to CommandDef("PLANE_YZ", "Плоскость YZ (G19)", emptyList(), "PLANE"),
        "UNITS_IN" to CommandDef("UNITS_IN", "Дюймы (G20)", emptyList(), "PLANE"),
        "UNITS_MM" to CommandDef("UNITS_MM", "Миллиметры (G21)", emptyList(), "PLANE"),
        "CUTCOMP_OFF" to CommandDef("CUTCOMP_OFF", "Отмена коррекции фрезы (G40)", emptyList(), "COMPENSATION"),
        "CUTCOMP_L" to CommandDef("CUTCOMP_L", "Коррекция фрезы слева (G41)", listOf(ParamDef("d", "int", 1, "Номер корректора D")), "COMPENSATION"),
        "CUTCOMP_R" to CommandDef("CUTCOMP_R", "Коррекция фрезы справа (G42)", listOf(ParamDef("d", "int", 1, "Номер корректора D")), "COMPENSATION"),
        "TOOLCOMP_P" to CommandDef("TOOLCOMP_P", "Коррекция длины + (G43)", listOf(
            ParamDef("h", "int", 1, "Номер H"),
            ParamDef("z", "float", 0.0, "Z")
        ), "COMPENSATION"),
        "TOOLCOMP_OFF" to CommandDef("TOOLCOMP_OFF", "Отмена длины (G49)", emptyList(), "COMPENSATION"),
        "SCALE_ON" to CommandDef("SCALE_ON", "Масштабирование (G51)", listOf(
            ParamDef("x", "float", 1.0, "Масштаб X"),
            ParamDef("y", "float", 1.0, "Масштаб Y"),
            ParamDef("z", "float", 1.0, "Масштаб Z")
        ), "OFFSET"),
        "SCALE_OFF" to CommandDef("SCALE_OFF", "Отмена масштаба (G50)", emptyList(), "OFFSET"),
        "LOCAL_OFF" to CommandDef("LOCAL_OFF", "Локальное смещение (G52)", listOf(
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", 0.0, "Z")
        ), "OFFSET"),
        "ROT_ON" to CommandDef("ROT_ON", "Поворот системы (G68)", listOf(
            ParamDef("x", "float", 0.0, "Центр X"),
            ParamDef("y", "float", 0.0, "Центр Y"),
            ParamDef("angle", "float", 0.0, "Угол в градусах")
        ), "OFFSET"),
        "ROT_OFF" to CommandDef("ROT_OFF", "Отмена поворота (G69)", emptyList(), "OFFSET"),
        "POLAR_ON" to CommandDef("POLAR_ON", "Полярные координаты (G16)", emptyList(), "POLAR"),
        "POLAR_OFF" to CommandDef("POLAR_OFF", "Отмена полярных (G15)", emptyList(), "POLAR"),
        "ABS" to CommandDef("ABS", "Абсолютные координаты (G90)", emptyList(), "PLANE"),
        "INC" to CommandDef("INC", "Инкрементальные координаты (G91)", emptyList(), "PLANE"),
        "EXACT" to CommandDef("EXACT", "Точный останов (G61)", emptyList(), "PLANE"),
        "SMOOTH" to CommandDef("SMOOTH", "Сглаживание траектории (G64)", emptyList(), "PLANE"),
        "HOME" to CommandDef("HOME", "Возврат в референтную точку (G28)", emptyList(), "RETURN"),
        "HOME_BASE" to CommandDef("HOME_BASE", "Базовые оси станка (G28.1)", emptyList(), "RETURN"),
        "PROBE" to CommandDef("PROBE", "Поиск касания щупом (G31)", listOf(
            ParamDef("x", "float", 0.0, "X"),
            ParamDef("y", "float", 0.0, "Y"),
            ParamDef("z", "float", 0.0, "Z"),
            ParamDef("f", "float", 100.0, "Подача щупа")
        ), "MOTION"),
        "POCKET_CW" to CommandDef("POCKET_CW", "Круглый карман по часовой (G12)", listOf(
            ParamDef("i", "float", 10.0, "Радиус кармана I"),
            ParamDef("j", "float", 10.0, "Шаг спирали J"),
            ParamDef("z", "float", -2.0, "Глубина Z"),
            ParamDef("f", "float", 200.0, "Подача F")
        ), "CANNED"),
        "POCKET_CCW" to CommandDef("POCKET_CCW", "Круглый карман против часовой (G13)", listOf(
            ParamDef("i", "float", 10.0, "Радиус кармана I"),
            ParamDef("j", "float", 10.0, "Шаг спирали J"),
            ParamDef("z", "float", -2.0, "Глубина Z"),
            ParamDef("f", "float", 200.0, "Подача F")
        ), "CANNED"),
        "VAR" to CommandDef("VAR", "Присвоить переменную", listOf(
            ParamDef("name", "str", "#100", "Имя переменной (#100 или W)"),
            ParamDef("value", "str", "0", "Значение или формула")
        ), "PSEUDO"),
        "VAR_ADD" to CommandDef("VAR_ADD", "Прибавить к переменной", listOf(
            ParamDef("name", "str", "#100", "Имя переменной"),
            ParamDef("delta", "str", "1", "Приращение")
        ), "PSEUDO"),
        "LABEL" to CommandDef("LABEL", "Метка перехода", listOf(
            ParamDef("name", "str", "L1", "Имя метки (например LOOP)")
        ), "PSEUDO"),
        "IF" to CommandDef("IF", "Условный переход", listOf(
            ParamDef("lhs", "str", "#100", "Левая часть"),
            ParamDef("op", "op", "EQ", "Условие: EQ, NE, GT, LT, GE, LE"),
            ParamDef("rhs", "str", "0", "Правая часть"),
            ParamDef("target", "str", "L1", "Целевая метка")
        ), "PSEUDO"),
        "GOTO" to CommandDef("GOTO", "Безусловный переход", listOf(
            ParamDef("target", "str", "L1", "Метка для перехода")
        ), "PSEUDO"),
        "SUB_CALL" to CommandDef("SUB_CALL", "Вызов подпрограммы (M98)", listOf(
            ParamDef("name", "str", "1000", "Номер подпрограммы P"),
            ParamDef("repeat", "int", 1, "Повторов L")
        ), "SUB"),
        "SUB_RET" to CommandDef("SUB_RET", "Возврат из подпрограммы (M99)", emptyList(), "SUB"),
        "CALL_FUNC" to CommandDef("CALL_FUNC", "Вызов функции библиотеки", listOf(
            ParamDef("name", "str", "", "Имя функции из библиотеки"),
            ParamDef("mode", "str", "inline", "Режим (inline или m98)")
        ), "PSEUDO"),
        "END" to CommandDef("END", "Конец программы (M30)", emptyList(), "PROGRAM"),
        "STOP" to CommandDef("STOP", "Останов программы (M0/M1)", listOf(
            ParamDef("optional", "int", 0, "1 = Опциональный M1, 0 = Точный M0")
        ), "PROGRAM"),
        "#" to CommandDef("#", "Комментарий", listOf(
            ParamDef("text", "str", "", "Текст комментария")
        ), "MISC")
    )

    fun buildSeedFunctions(): List<FunctionDef> {
        return listOf(
            FunctionDef(
                name = "TOOL_CHANGE",
                title = "Безопасная смена инструмента",
                description = "Останов шпинделя, охлаждения, отвод на Z10, спуск инструмента.",
                params = listOf(
                    FunctionParam("t", "1", "Номер инструмента"),
                    FunctionParam("rpm", "8000", "Обороты шпинделя")
                ),
                body = listOf(
                    Command("SPIN", mapOf("on" to 0, "rpm" to 0, "ccw" to 0)),
                    Command("COOL", mapOf("on" to 0, "mist" to 0)),
                    Command("RAPID", mapOf("x" to 0, "y" to 0, "z" to 10)),
                    Command("TOOL", mapOf("tool" to "{t}")),
                    Command("SPIN", mapOf("on" to 1, "rpm" to "{rpm}", "ccw" to 0))
                )
            ),
            FunctionDef(
                name = "DRILL_GRID",
                title = "Матрица отверстий сеткой",
                description = "Сверлит nx × ny отверстий с шагом step, начиная от (x0, y0).",
                params = listOf(
                    FunctionParam("x0", "0", "Начальный X"),
                    FunctionParam("y0", "0", "Начальный Y"),
                    FunctionParam("nx", "3", "Число отверстий по X"),
                    FunctionParam("ny", "3", "Число отверстий по Y"),
                    FunctionParam("step", "10", "Шаг между отверстиями"),
                    FunctionParam("depth", "-5", "Глубина сверления Z"),
                    FunctionParam("f", "80", "Подача сверления")
                ),
                body = listOf(
                    Command("VAR", mapOf("name" to "#310", "value" to "0")),
                    Command("LABEL", mapOf("name" to "ROW")),
                    Command("VAR", mapOf("name" to "#311", "value" to "0")),
                    Command("LABEL", mapOf("name" to "COL")),
                    Command("RAPID", mapOf("x" to "{x0 + #311*step}", "y" to "{y0 + #310*step}", "z" to 5)),
                    Command("DRILL", mapOf("x" to "{x0 + #311*step}", "y" to "{y0 + #310*step}", "z" to "{depth}", "f" to "{f}")),
                    Command("VAR_ADD", mapOf("name" to "#311", "delta" to "1")),
                    Command("IF", mapOf("lhs" to "#311", "op" to "LT", "rhs" to "{nx}", "target" to "COL")),
                    Command("VAR_ADD", mapOf("name" to "#310", "delta" to "1")),
                    Command("IF", mapOf("lhs" to "#310", "op" to "LT", "rhs" to "{ny}", "target" to "ROW"))
                )
            ),
            FunctionDef(
                name = "POCKET_RECT",
                title = "Прямоугольный карман зигзагом",
                description = "Фрезерует прямоугольник x0..x1, y0..y1 с шагом строк step на глубине z.",
                params = listOf(
                    FunctionParam("x0", "0", "Начало X"),
                    FunctionParam("y0", "0", "Начало Y"),
                    FunctionParam("x1", "50", "Конец X"),
                    FunctionParam("y1", "50", "Конец Y"),
                    FunctionParam("step", "3", "Шаг строк"),
                    FunctionParam("z", "-1", "Глубина"),
                    FunctionParam("f", "150", "Подача")
                ),
                body = listOf(
                    Command("VAR", mapOf("name" to "#320", "value" to "0")),
                    Command("LABEL", mapOf("name" to "ROW")),
                    Command("RAPID", mapOf("x" to "{x0}", "y" to "{y0 + #320*step}", "z" to 5)),
                    Command("FEED", mapOf("x" to "{x0}", "y" to "{y0 + #320*step}", "z" to "{z}", "f" to "{f}")),
                    Command("FEED", mapOf("x" to "{x1}", "y" to "{y0 + #320*step}", "z" to "{z}", "f" to "{f}")),
                    Command("RAPID", mapOf("x" to "{x1}", "y" to "{y0 + #320*step}", "z" to 5)),
                    Command("VAR_ADD", mapOf("name" to "#320", "delta" to "1")),
                    Command("IF", mapOf("lhs" to "{y0 + #320*step}", "op" to "LE", "rhs" to "{y1}", "target" to "ROW"))
                )
            )
        )
    }
}
