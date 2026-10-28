# -*- coding: utf-8 -*-
"""Диалоги: инструмент, заготовка, переменная, команда,
настройки, освещение, библиотека функций, начало/конец кода,
список кодов, справка."""

import copy
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QComboBox, QLabel,
    QGroupBox, QFileDialog, QMessageBox, QTabWidget, QWidget,
    QTextBrowser, QColorDialog, QCheckBox, QListWidget, QListWidgetItem,
    QSlider, QStackedWidget, QPlainTextEdit, QAbstractItemView,
)

from gcode_editor.core.models import (
    Tool, Stock, UserVar, Command, FunctionDef, FunctionParam,
    SimSettings, AppSettings, LightingSource, default_lights,
)
from gcode_editor.core.constants import LightKind, LightType
from gcode_editor.core.commands_def import (
    COMMAND_DEFS, ORDERED_MNEMONICS, CODE_GROUPS,
    get_command_group, get_command_desc,
)
from gcode_editor.io import file_io
from gcode_editor.ui import help_content


# ============================================================
#                        ИНСТРУМЕНТ
# ============================================================

class ToolDialog(QDialog):
    def __init__(self, parent=None, tool=None):
        super().__init__(parent)
        self.setWindowTitle("Инструмент")
        form = QFormLayout(self)
        self.num = QSpinBox(); self.num.setRange(1, 999)
        self.name = QLineEdit()
        self.dia = QDoubleSpinBox(); self.dia.setRange(0.001, 500); self.dia.setDecimals(3)
        self.feed = QDoubleSpinBox(); self.feed.setRange(1, 100000); self.feed.setDecimals(1)
        self.rpm = QSpinBox(); self.rpm.setRange(0, 100000)
        self.color = QLineEdit("#3399ff")
        btn = QPushButton("…"); btn.clicked.connect(self._pick)
        if tool:
            self.num.setValue(tool.number); self.name.setText(tool.name)
            self.dia.setValue(tool.diameter); self.feed.setValue(tool.feed)
            self.rpm.setValue(tool.rpm); self.color.setText(tool.color)
        else:
            self.dia.setValue(3.0); self.feed.setValue(200.0); self.rpm.setValue(8000)
        crow = QHBoxLayout(); crow.addWidget(self.color); crow.addWidget(btn)
        form.addRow("Номер:", self.num); form.addRow("Имя:", self.name)
        form.addRow("Диаметр:", self.dia); form.addRow("Подача:", self.feed)
        form.addRow("Обороты:", self.rpm); form.addRow("Цвет:", crow)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.color.text()), self)
        if c.isValid(): self.color.setText(c.name())

    def get_tool(self):
        return Tool(self.num.value(),
                    self.name.text() or f"T{self.num.value()}",
                    self.dia.value(), self.feed.value(),
                    self.rpm.value(),
                    self.color.text() or "#3399ff")


# ============================================================
#                        ЗАГОТОВКА
# ============================================================

class StockDialog(QDialog):
    def __init__(self, parent=None, stock=None):
        super().__init__(parent)
        self.setWindowTitle("Заготовка")
        self.setMinimumWidth(420)
        s = stock or Stock()
        self.result_stock = None
        v = QVBoxLayout(self)

        pos_box = QGroupBox("Смещение (в G-коде)")
        pb = QFormLayout(pos_box)
        self.px = QDoubleSpinBox(); self.px.setRange(-1e6, 1e6); self.px.setDecimals(2)
        self.py = QDoubleSpinBox(); self.py.setRange(-1e6, 1e6); self.py.setDecimals(2)
        self.pz = QDoubleSpinBox(); self.pz.setRange(-1e6, 1e6); self.pz.setDecimals(2)
        self.px.setValue(s.px); self.py.setValue(s.py); self.pz.setValue(s.pz)
        pb.addRow("Смещение X:", self.px)
        pb.addRow("Смещение Y:", self.py)
        pb.addRow("Верх Z:", self.pz)
        v.addWidget(pos_box)

        box_group = QGroupBox("Размеры параллелепипеда")
        bb = QFormLayout(box_group)
        self.sx = QDoubleSpinBox(); self.sx.setRange(0.1, 1e6); self.sx.setDecimals(2)
        self.sy = QDoubleSpinBox(); self.sy.setRange(0.1, 1e6); self.sy.setDecimals(2)
        self.sz = QDoubleSpinBox(); self.sz.setRange(0.1, 1e6); self.sz.setDecimals(2)
        self.sx.setValue(s.x); self.sy.setValue(s.y); self.sz.setValue(s.z)
        self.color = QLineEdit(s.color)
        btn_color = QPushButton("…"); btn_color.clicked.connect(self._pick_color)
        rc = QHBoxLayout(); rc.addWidget(self.color); rc.addWidget(btn_color)
        self.visible = QCheckBox("Отображать"); self.visible.setChecked(s.visible)
        bb.addRow("Размер X:", self.sx)
        bb.addRow("Размер Y:", self.sy)
        bb.addRow("Толщина Z:", self.sz)
        bb.addRow("Цвет:", rc)
        bb.addRow("", self.visible)
        v.addWidget(box_group)

        bbb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbb.accepted.connect(self._accept); bbb.rejected.connect(self.reject)
        v.addWidget(bbb)
        self._stock = s

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color.text()), self)
        if c.isValid(): self.color.setText(c.name())

    def _accept(self):
        st = Stock(
            mode="box",
            x=self.sx.value(), y=self.sy.value(), z=self.sz.value(),
            px=self.px.value(), py=self.py.value(), pz=self.pz.value(),
            color=self.color.text() or "#7080b0",
            visible=self.visible.isChecked(),
        )
        self.result_stock = st
        self.accept()


# ============================================================
#                        ПЕРЕМЕННАЯ
# ============================================================

class VarDialog(QDialog):
    def __init__(self, parent=None, var=None, known=None):
        super().__init__(parent)
        self.setWindowTitle("Переменная")
        form = QFormLayout(self)
        self.name = QLineEdit(); self.value = QLineEdit()
        self.value.setPlaceholderText("число или формула: 100, {W*2}, {L/STEP+1}")
        if var:
            self.name.setText(var.name); self.value.setText(str(var.value))
        form.addRow("Имя:", self.name)
        form.addRow("Значение / формула:", self.value)
        hint = QLabel("Формулы: {W-10}, {W*L/STEP + 1}, {max(W,L)}, {#200*STEP}\n"
                      "Операции: + - * / // % ** ( ), min, max, abs, sqrt, sin, cos, pi")
        hint.setStyleSheet("color:#555; font-family:Consolas; font-size:10px;")
        form.addRow("", hint)
        if known:
            lbl = QLabel("Уже определены: " + ", ".join(known[:20]))
            lbl.setWordWrap(True); lbl.setStyleSheet("color:#2a6099; font-size:10px;")
            form.addRow("", lbl)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        form.addRow(bb)

    def get_var(self):
        return UserVar(self.name.text().strip(), self.value.text().strip())


# ============================================================
#                       ВЫБОР КОМАНДЫ
# ============================================================

class CommandPickerDialog(QDialog):
    def __init__(self, parent=None, initial=None, variables=None,
                 functions=None, code_order=None, code_hidden=None,
                 sort_mode="custom"):
        super().__init__(parent)
        self.setWindowTitle("Команда псевдокода")
        self.setMinimumWidth(560)
        self.variables = variables or {}
        self.functions = functions or []
        self._functions_by_name = {f.name: f for f in self.functions}
        self._code_order = list(code_order) if code_order else list(ORDERED_MNEMONICS)
        for m in ORDERED_MNEMONICS:
            if m not in self._code_order:
                self._code_order.append(m)
        self._code_hidden = set(code_hidden or [])
        self._sort_mode = sort_mode or "custom"
        self.result_command = None
        self._param_widgets = {}
        self._visible_codes = self._apply_sort(
            [m for m in self._code_order if m not in self._code_hidden])

        outer = QVBoxLayout(self)
        top = QFormLayout()

        self.ed_filter = QLineEdit()
        self.ed_filter.setPlaceholderText("Поиск по имени или описанию…")
        self.ed_filter.textChanged.connect(self._apply_filter)
        top.addRow("Фильтр:", self.ed_filter)

        self.mnem_combo = QComboBox()
        self._fill_combo()
        if initial:
            i = self.mnem_combo.findData(initial.mnemonic)
            if i >= 0:
                self.mnem_combo.setCurrentIndex(i)
        top.addRow("Команда:", self.mnem_combo)

        self.desc_label = QLabel("")
        self.desc_label.setStyleSheet("color:#555; font-style:italic;")
        top.addRow("", self.desc_label)
        outer.addLayout(top)

        self.params_box = QGroupBox("Параметры (формулы: {W}, {L*2}, {#200*STEP})")
        self.params_form = QFormLayout(self.params_box)
        outer.addWidget(self.params_box)

        if self.variables:
            vs = ", ".join(f"{k}={v:g}" for k, v in list(self.variables.items())[:12])
            lbl = QLabel(f"Доступные: {vs}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#2a6099; font-size:10px;")
            outer.addWidget(lbl)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        outer.addWidget(btns)

        self.mnem_combo.currentIndexChanged.connect(
            lambda _=None: self._rebuild_params())
        self._rebuild_params(initial.params if initial else None)

    def _apply_sort(self, items):
        if self._sort_mode == "alpha":
            return sorted(items)
        if self._sort_mode == "desc":
            return sorted(items, key=lambda x: get_command_desc(x).lower())
        if self._sort_mode == "group":
            return sorted(items, key=lambda x: (get_command_group(x), x))
        order = {m: i for i, m in enumerate(self._code_order)}
        return sorted(items, key=lambda x: order.get(x, 9999))

    def _fill_combo(self):
        cur = self.mnem_combo.currentData() if self.mnem_combo.count() else None
        self.mnem_combo.blockSignals(True)
        self.mnem_combo.clear()
        for m in self._visible_codes:
            desc = get_command_desc(m)
            self.mnem_combo.addItem(f"{m}  —  {desc}", m)
        if cur is not None:
            i = self.mnem_combo.findData(cur)
            if i >= 0:
                self.mnem_combo.setCurrentIndex(i)
        self.mnem_combo.blockSignals(False)

    def _apply_filter(self, text):
        t = text.strip().lower()
        base = [m for m in self._code_order if m not in self._code_hidden]
        if t:
            base = [m for m in base
                    if t in m.lower() or t in get_command_desc(m).lower()]
        self._visible_codes = self._apply_sort(base)
        self._fill_combo()

    def _clear_form(self):
        while self.params_form.rowCount():
            self.params_form.removeRow(0)
        self._param_widgets.clear()

    def _rebuild_params(self, prefill=None):
        if not isinstance(prefill, dict):
            prefill = None
        mnem = self.mnem_combo.currentData()
        if mnem is None:
            self.desc_label.setText("")
            self._clear_form()
            return
        desc = get_command_desc(mnem)
        fields = COMMAND_DEFS.get(mnem, ("", [], "MISC"))[1]
        self.desc_label.setText(desc)
        self._clear_form()
        prefill = prefill or {}

        if mnem == "#":
            w = QLineEdit(); w.setText(str(prefill.get("text", "")))
            self.params_form.addRow("текст:", w)
            self._param_widgets["text"] = ("str", w)
            return

        if mnem == "CALL_FUNC":
            cb_fn = QComboBox()
            cb_fn.addItem("— выберите функцию —", "")
            for f in self.functions:
                cb_fn.addItem(f"{f.name} — {f.title or f.name}", f.name)
            cur = str(prefill.get("name", ""))
            i = cb_fn.findData(cur)
            if i >= 0: cb_fn.setCurrentIndex(i)
            self.params_form.addRow("Функция:", cb_fn)

            cb_mode = QComboBox()
            cb_mode.addItem("Инлайн (тело в G-код)", "inline")
            cb_mode.addItem("M98 / M99 (подпрограмма)", "m98")
            cur_mode = str(prefill.get("mode", "inline"))
            j = cb_mode.findData(cur_mode)
            if j >= 0: cb_mode.setCurrentIndex(j)
            self.params_form.addRow("Режим:", cb_mode)

            params_container = QWidget()
            params_form = QFormLayout(params_container)
            params_form.setContentsMargins(0, 0, 0, 0)
            self.params_form.addRow("Параметры:", params_container)
            self._param_widgets["__container__"] = ("str", params_container)

            def _rebuild_fn_params(*_):
                while params_form.rowCount():
                    params_form.removeRow(0)
                for k in [k for k in self._param_widgets if k.startswith("p_")]:
                    del self._param_widgets[k]
                fn_name = cb_fn.currentData()
                fn = self._functions_by_name.get(fn_name)
                if not fn:
                    return
                for prm in fn.params:
                    pkey = f"p_{prm.name}"
                    w = QLineEdit()
                    w.setText(str(prefill.get(pkey, prm.default)))
                    lbl = f"{prm.name} ({prm.description or 'параметр'}):"
                    params_form.addRow(lbl, w)
                    self._param_widgets[pkey] = ("str", w)

            cb_fn.currentIndexChanged.connect(_rebuild_fn_params)
            self._param_widgets["__fn_combo__"] = ("str", cb_fn)
            self._param_widgets["__mode_combo__"] = ("str", cb_mode)
            _rebuild_fn_params()
            return

        for name, typ, default in fields:
            val = prefill.get(name, default)
            if typ in ("float", "int"):
                w = QLineEdit(); w.setText(str(val) if val != "" else "0")
            else:
                if name == "op":
                    w = QComboBox()
                    for op in ["EQ", "NE", "GT", "LT", "GE", "LE"]:
                        w.addItem(op)
                    i = w.findText(str(val).upper())
                    if i >= 0: w.setCurrentIndex(i)
                else:
                    w = QLineEdit(); w.setText(str(val))
            self.params_form.addRow(name + ":", w)
            self._param_widgets[name] = (typ, w)

    def _convert(self, typ, raw):
        s = raw.strip()
        if not s:
            return 0 if typ in ("int", "float") else ""
        try:
            if typ == "int":
                return int(float(s))
            if typ == "float":
                return float(s)
        except ValueError:
            pass
        return s

    def _on_ok(self):
        mnem = self.mnem_combo.currentData()
        if mnem is None:
            return
        params = {}
        if mnem == "CALL_FUNC":
            fn_name = self._param_widgets["__fn_combo__"][1].currentData()
            mode = self._param_widgets["__mode_combo__"][1].currentData()
            if not fn_name:
                QMessageBox.warning(self, "Функция", "Выберите функцию.")
                return
            params["name"] = fn_name
            params["mode"] = mode or "inline"
            for k, (typ, w) in self._param_widgets.items():
                if k.startswith("p_"):
                    params[k] = w.text().strip()
        else:
            for name, (typ, w) in self._param_widgets.items():
                if name in ("__container__", "__fn_combo__", "__mode_combo__"):
                    continue
                if isinstance(w, QComboBox):
                    params[name] = w.currentText()
                else:
                    params[name] = self._convert(typ, w.text())
        self.result_command = Command(mnem, params)
        self.accept()


# ============================================================
#                  НАСТРОЙКИ СИМУЛЯЦИИ
# ============================================================

class SimulationSettingsDialog(QDialog):
    def __init__(self, parent=None, settings: SimSettings = None):
        super().__init__(parent)
        self.setWindowTitle("Настройки симуляции")
        self.setMinimumWidth(520)
        self.result = None
        s = copy.deepcopy(settings) if settings else SimSettings()
        self._settings = s
        v = QVBoxLayout(self)

        vox_box = QGroupBox("Воксельная сетка (тайлы симуляции)")
        vf = QFormLayout(vox_box)
        self.chk_auto_xy = QCheckBox(
            "Тайл по XY = 1/3 диаметра минимального инструмента")
        self.chk_auto_xy.setChecked(s.auto_voxel_xy)
        vf.addRow("", self.chk_auto_xy)

        self.sp_xy = QDoubleSpinBox()
        self.sp_xy.setRange(0.01, 100.0); self.sp_xy.setDecimals(3)
        self.sp_xy.setSingleStep(0.05); self.sp_xy.setValue(s.voxel_xy)
        self.sp_xy.setSuffix(" мм")
        vf.addRow("Размер тайла по XY:", self.sp_xy)

        self.sp_z = QDoubleSpinBox()
        self.sp_z.setRange(0.01, 100.0); self.sp_z.setDecimals(3)
        self.sp_z.setSingleStep(0.05); self.sp_z.setValue(s.voxel_z)
        self.sp_z.setSuffix(" мм")
        vf.addRow("Глубина тайла (Z):", self.sp_z)

        self.sp_mem = QDoubleSpinBox()
        self.sp_mem.setRange(0.05, 0.9); self.sp_mem.setDecimals(2)
        self.sp_mem.setSingleStep(0.05); self.sp_mem.setValue(s.max_memory_fraction)
        self.sp_mem.setSuffix(" от доступной RAM")
        vf.addRow("Лимит памяти:", self.sp_mem)

        self.lbl_vox_info = QLabel("")
        self.lbl_vox_info.setWordWrap(True)
        self.lbl_vox_info.setStyleSheet(
            "color:#2a6099; font-family:Consolas; font-size:10px;")
        vf.addRow("", self.lbl_vox_info)
        v.addWidget(vox_box)

        self.chk_auto_xy.toggled.connect(self._update_vox_enabled)
        self.sp_xy.valueChanged.connect(self._update_vox_info)
        self.sp_z.valueChanged.connect(self._update_vox_info)
        self.sp_mem.valueChanged.connect(self._update_vox_info)

        tp_box = QGroupBox("Отображение траектории")
        tf = QFormLayout(tp_box)
        self.sp_rapid_w = QDoubleSpinBox()
        self.sp_rapid_w.setRange(0.5, 12.0); self.sp_rapid_w.setDecimals(1)
        self.sp_rapid_w.setSingleStep(0.5); self.sp_rapid_w.setValue(s.rapid_line_width)
        tf.addRow("Толщина RAPID:", self.sp_rapid_w)
        self.sp_feed_w = QDoubleSpinBox()
        self.sp_feed_w.setRange(0.5, 12.0); self.sp_feed_w.setDecimals(1)
        self.sp_feed_w.setSingleStep(0.5); self.sp_feed_w.setValue(s.feed_line_width)
        tf.addRow("Толщина FEED:", self.sp_feed_w)
        self.chk_dash = QCheckBox("RAPID — пунктиром")
        self.chk_dash.setChecked(s.rapid_dash)
        tf.addRow("", self.chk_dash)
        v.addWidget(tp_box)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok); bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._update_vox_enabled()
        self._update_vox_info()

    def _update_vox_enabled(self):
        on = not self.chk_auto_xy.isChecked()
        self.sp_xy.setEnabled(on)
        self._update_vox_info()

    def _update_vox_info(self):
        try:
            from gcode_editor.sim.simulator import _available_memory_bytes
            avail = _available_memory_bytes()
        except Exception:
            avail = 2 * 1024 * 1024 * 1024
        frac = float(self.sp_mem.value())
        budget = max(int(avail * frac), 16 * 1024 * 1024)
        self.lbl_vox_info.setText(
            f"Доступно RAM: {avail/1024/1024:.0f} МБ, "
            f"лимит под воксели: {budget/1024/1024:.0f} МБ.\n"
            f"Фактический размер будет автоматически увеличен, "
            f"если сетка не влезет.")

    def _on_ok(self):
        s = self._settings
        s.auto_voxel_xy = self.chk_auto_xy.isChecked()
        s.voxel_xy = self.sp_xy.value()
        s.voxel_z = self.sp_z.value()
        s.max_memory_fraction = self.sp_mem.value()
        s.rapid_line_width = self.sp_rapid_w.value()
        s.feed_line_width = self.sp_feed_w.value()
        s.rapid_dash = self.chk_dash.isChecked()
        self.result = s
        self.accept()


# ============================================================
#                        ОСВЕЩЕНИЕ
# ============================================================

class LightingDialog(QDialog):
    def __init__(self, parent=None, lights=None):
        super().__init__(parent)
        self.setWindowTitle("Освещение")
        self.setMinimumSize(640, 480)
        self.result = None
        self._lights = copy.deepcopy(lights) if lights else default_lights()
        self._current = 0

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(220)
        top.addWidget(self.list, 1)
        self.stack = QStackedWidget()
        top.addWidget(self.stack, 2)
        v.addLayout(top, 1)

        h = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_dup = QPushButton("Дублировать")
        self.btn_del = QPushButton("Удалить")
        h.addWidget(self.btn_add); h.addWidget(self.btn_dup); h.addWidget(self.btn_del)
        h.addStretch(1)
        v.addLayout(h)

        self.chk_enabled = QCheckBox("Включён")
        v.addWidget(self.chk_enabled)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok); bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self.btn_add.clicked.connect(self._add)
        self.btn_dup.clicked.connect(self._dup)
        self.btn_del.clicked.connect(self._del)
        self.list.currentRowChanged.connect(self._select)
        self.chk_enabled.toggled.connect(self._set_enabled)

        self._rebuild_list()
        if self._lights:
            self.list.setCurrentRow(0)

    def _rebuild_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for l in self._lights:
            mark = "" if l.enabled else "  (выкл)"
            self.list.addItem(f"[{l.kind}] {l.light_type}{mark}")
        self.list.blockSignals(False)

    def _clear_stack(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

    def _build_editor(self, ls: LightingSource):
        w = QWidget()
        f = QFormLayout(w)

        cb_kind = QComboBox()
        for k in (LightKind.HEADLIGHT, LightKind.CAMERA, LightKind.SCENE):
            cb_kind.addItem(k)
        i = cb_kind.findText(ls.kind)
        if i >= 0: cb_kind.setCurrentIndex(i)
        f.addRow("Тип источника:", cb_kind)

        cb_type = QComboBox()
        for t in (LightType.SPHERE, LightType.SPOT, LightType.DIRECTIONAL):
            cb_type.addItem(t)
        i = cb_type.findText(ls.light_type)
        if i >= 0: cb_type.setCurrentIndex(i)
        f.addRow("Форма:", cb_type)

        sp_int = QDoubleSpinBox()
        sp_int.setRange(0.0, 10.0); sp_int.setDecimals(2)
        sp_int.setSingleStep(0.1); sp_int.setValue(ls.intensity)
        f.addRow("Интенсивность:", sp_int)

        ed_color = QLineEdit(ls.color)
        btn_color = QPushButton("…")
        row_c = QHBoxLayout(); row_c.addWidget(ed_color); row_c.addWidget(btn_color)
        f.addRow("Цвет:", row_c)

        sp_px = QDoubleSpinBox(); sp_px.setRange(-1e6, 1e6); sp_px.setDecimals(1)
        sp_py = QDoubleSpinBox(); sp_py.setRange(-1e6, 1e6); sp_py.setDecimals(1)
        sp_pz = QDoubleSpinBox(); sp_pz.setRange(-1e6, 1e6); sp_pz.setDecimals(1)
        sp_px.setValue(ls.position[0]); sp_py.setValue(ls.position[1]); sp_pz.setValue(ls.position[2])
        f.addRow("Позиция X:", sp_px); f.addRow("Позиция Y:", sp_py); f.addRow("Позиция Z:", sp_pz)

        sp_fx = QDoubleSpinBox(); sp_fx.setRange(-1e6, 1e6); sp_fx.setDecimals(1)
        sp_fy = QDoubleSpinBox(); sp_fy.setRange(-1e6, 1e6); sp_fy.setDecimals(1)
        sp_fz = QDoubleSpinBox(); sp_fz.setRange(-1e6, 1e6); sp_fz.setDecimals(1)
        sp_fx.setValue(ls.focal_point[0]); sp_fy.setValue(ls.focal_point[1]); sp_fz.setValue(ls.focal_point[2])
        f.addRow("Цель X:", sp_fx); f.addRow("Цель Y:", sp_fy); f.addRow("Цель Z:", sp_fz)

        sp_cone = QDoubleSpinBox()
        sp_cone.setRange(1.0, 170.0); sp_cone.setDecimals(1)
        sp_cone.setValue(ls.cone_angle)
        f.addRow("Угол конуса (spot):", sp_cone)

        def _on_color():
            c = QColorDialog.getColor(QColor(ed_color.text()), self)
            if c.isValid(): ed_color.setText(c.name())
        btn_color.clicked.connect(_on_color)

        def _sync(*_):
            ls.kind = cb_kind.currentText()
            ls.light_type = cb_type.currentText()
            ls.intensity = sp_int.value()
            ls.color = ed_color.text() or "#ffffff"
            ls.position = (sp_px.value(), sp_py.value(), sp_pz.value())
            ls.focal_point = (sp_fx.value(), sp_fy.value(), sp_fz.value())
            ls.cone_angle = sp_cone.value()
            self._rebuild_list()

        for wdg in (cb_kind, cb_type):
            wdg.currentIndexChanged.connect(_sync)
        sp_int.valueChanged.connect(_sync)
        ed_color.textChanged.connect(_sync)
        for wdg in (sp_px, sp_py, sp_pz, sp_fx, sp_fy, sp_fz):
            wdg.valueChanged.connect(_sync)
        sp_cone.valueChanged.connect(_sync)

        return w

    def _select(self, row):
        self._current = max(0, row)
        self._clear_stack()
        if 0 <= self._current < len(self._lights):
            ls = self._lights[self._current]
            self.stack.addWidget(self._build_editor(ls))
            self.chk_enabled.blockSignals(True)
            self.chk_enabled.setChecked(ls.enabled)
            self.chk_enabled.blockSignals(False)

    def _set_enabled(self, val):
        if 0 <= self._current < len(self._lights):
            self._lights[self._current].enabled = bool(val)
            self._rebuild_list()

    def _add(self):
        self._lights.append(LightingSource(kind="scene", intensity=0.5,
                                           color="#ffffff"))
        self._rebuild_list()
        self.list.setCurrentRow(len(self._lights) - 1)

    def _dup(self):
        if 0 <= self._current < len(self._lights):
            new = copy.deepcopy(self._lights[self._current])
            self._lights.append(new)
            self._rebuild_list()
            self.list.setCurrentRow(len(self._lights) - 1)

    def _del(self):
        if 0 <= self._current < len(self._lights) and len(self._lights) > 1:
            del self._lights[self._current]
            self._rebuild_list()
            self.list.setCurrentRow(min(self._current, len(self._lights) - 1))

    def _on_ok(self):
        self.result = self._lights
        self.accept()


# ============================================================
#                 БИБЛИОТЕКА ФУНКЦИЙ
# ============================================================

class FunctionParamDialog(QDialog):
    def __init__(self, parent=None, prm: FunctionParam = None):
        super().__init__(parent)
        self.setWindowTitle("Параметр")
        self.result = None
        f = QFormLayout(self)
        self.ed_name = QLineEdit(prm.name if prm else "")
        self.ed_default = QLineEdit(prm.default if prm else "0")
        self.ed_desc = QLineEdit(prm.description if prm else "")
        f.addRow("Имя:", self.ed_name)
        f.addRow("Значение по умолчанию:", self.ed_default)
        f.addRow("Описание:", self.ed_desc)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _on_ok(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Параметр", "Имя обязательно.")
            return
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            QMessageBox.warning(self, "Параметр",
                "Имя — латиница/цифры/подчёркивание, не с цифры.")
            return
        self.result = FunctionParam(
            name=name,
            default=self.ed_default.text().strip() or "0",
            description=self.ed_desc.text().strip())
        self.accept()


class FunctionEditorDialog(QDialog):
    def __init__(self, parent=None, fn: FunctionDef = None,
                 known_names=None):
        super().__init__(parent)
        self.setWindowTitle("Функция")
        self.setMinimumWidth(720)
        self.setMinimumHeight(600)
        self.result = None
        self._known = set(known_names or [])
        self._fn = copy.deepcopy(fn) if fn else FunctionDef()
        if fn is None:
            self._fn.name = self._unique_default()

        v = QVBoxLayout(self)
        top = QFormLayout()
        self.ed_name = QLineEdit(self._fn.name)
        self.ed_title = QLineEdit(self._fn.title)
        self.ed_desc = QPlainTextEdit()
        self.ed_desc.setPlainText(self._fn.description)
        self.ed_desc.setMaximumHeight(70)
        top.addRow("Имя (уникальное):", self.ed_name)
        top.addRow("Заголовок:", self.ed_title)
        top.addRow("Описание:", self.ed_desc)
        v.addLayout(top)

        gb_params = QGroupBox("Параметры (доступны в теле как {имя})")
        pv = QVBoxLayout(gb_params)
        self.list_params = QListWidget()
        self.list_params.setMaximumHeight(120)
        pv.addWidget(self.list_params)
        ph = QHBoxLayout()
        self.btn_p_add = QPushButton("+ Параметр")
        self.btn_p_edit = QPushButton("Изм")
        self.btn_p_del = QPushButton("−")
        ph.addWidget(self.btn_p_add)
        ph.addWidget(self.btn_p_edit)
        ph.addWidget(self.btn_p_del)
        ph.addStretch(1)
        pv.addLayout(ph)
        self._params = list(self._fn.params)
        self._refresh_params()
        self.btn_p_add.clicked.connect(self._add_param)
        self.btn_p_edit.clicked.connect(self._edit_param)
        self.btn_p_del.clicked.connect(self._del_param)
        v.addWidget(gb_params)

        gb_body = QGroupBox("Тело функции (псевдокод)")
        bv = QVBoxLayout(gb_body)
        self.list_body = QListWidget()
        self.list_body.setFont(QFont("Consolas", 10))
        bv.addWidget(self.list_body)
        bh = QHBoxLayout()
        self.btn_b_add = QPushButton("+ Команда")
        self.btn_b_edit = QPushButton("Изм")
        self.btn_b_del = QPushButton("−")
        self.btn_b_up = QPushButton("▲")
        self.btn_b_down = QPushButton("▼")
        bh.addWidget(self.btn_b_add); bh.addWidget(self.btn_b_edit)
        bh.addWidget(self.btn_b_del)
        bh.addWidget(self.btn_b_up); bh.addWidget(self.btn_b_down)
        bh.addStretch(1)
        bv.addLayout(bh)
        self._body = list(self._fn.body)
        self._refresh_body()
        self.btn_b_add.clicked.connect(self._add_cmd)
        self.btn_b_edit.clicked.connect(self._edit_cmd)
        self.btn_b_del.clicked.connect(self._del_cmd)
        self.btn_b_up.clicked.connect(lambda: self._move_cmd(-1))
        self.btn_b_down.clicked.connect(lambda: self._move_cmd(+1))
        v.addWidget(gb_body, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _unique_default(self):
        base = "NEW_FUNC"
        i = 1
        while f"{base}{i}" in self._known:
            i += 1
        return f"{base}{i}"

    def _refresh_params(self):
        self.list_params.clear()
        for p in self._params:
            self.list_params.addItem(
                f"{p.name} = {p.default}    ({p.description})")

    def _refresh_body(self):
        self.list_body.clear()
        for i, c in enumerate(self._body):
            self.list_body.addItem(c.to_pseudo(i))

    def _add_param(self):
        d = FunctionParamDialog(self)
        if d.exec_() == QDialog.Accepted and d.result:
            self._params.append(d.result)
            self._refresh_params()

    def _edit_param(self):
        r = self.list_params.currentRow()
        if r < 0:
            return
        d = FunctionParamDialog(self, self._params[r])
        if d.exec_() == QDialog.Accepted and d.result:
            self._params[r] = d.result
            self._refresh_params()

    def _del_param(self):
        r = self.list_params.currentRow()
        if r < 0:
            return
        del self._params[r]
        self._refresh_params()

    def _add_cmd(self):
        d = CommandPickerDialog(self, None, {})
        if d.exec_() == QDialog.Accepted and d.result_command:
            self._body.append(d.result_command)
            self._refresh_body()

    def _edit_cmd(self):
        r = self.list_body.currentRow()
        if r < 0:
            return
        d = CommandPickerDialog(self, self._body[r], {})
        if d.exec_() == QDialog.Accepted and d.result_command:
            self._body[r] = d.result_command
            self._refresh_body()

    def _del_cmd(self):
        r = self.list_body.currentRow()
        if r < 0:
            return
        del self._body[r]
        self._refresh_body()

    def _move_cmd(self, delta):
        r = self.list_body.currentRow()
        if r < 0:
            return
        nr = r + delta
        if nr < 0 or nr >= len(self._body):
            return
        self._body[r], self._body[nr] = self._body[nr], self._body[r]
        self._refresh_body()
        self.list_body.setCurrentRow(nr)

    def _on_ok(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Функция", "Укажите имя.")
            return
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            QMessageBox.warning(self, "Функция",
                "Имя — латиница/цифры/подчёркивание, не с цифры.")
            return
        if name in self._known and name != self._fn.name:
            QMessageBox.warning(self, "Функция",
                f"Имя '{name}' уже используется.")
            return
        seen = set()
        for p in self._params:
            if not p.name:
                QMessageBox.warning(self, "Функция",
                    "Имя параметра не может быть пустым.")
                return
            if not p.name.replace("_", "").isalnum() or p.name[0].isdigit():
                QMessageBox.warning(self, "Функция",
                    f"Некорректное имя параметра: {p.name}")
                return
            if p.name in seen:
                QMessageBox.warning(self, "Функция",
                    f"Параметр '{p.name}' повторяется.")
                return
            seen.add(p.name)

        self._fn.name = name
        self._fn.title = self.ed_title.text().strip()
        self._fn.description = self.ed_desc.toPlainText().strip()
        self._fn.params = list(self._params)
        self._fn.body = list(self._body)
        self.result = self._fn
        self.accept()


class FunctionLibraryDialog(QDialog):
    def __init__(self, parent=None, functions=None, on_insert=None):
        super().__init__(parent)
        self.setWindowTitle("Библиотека функций")
        self.setMinimumSize(800, 600)
        self.result = None
        self._functions = copy.deepcopy(functions or [])
        self._on_insert = on_insert
        self._current = -1

        v = QVBoxLayout(self)
        top = QHBoxLayout()

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(240)
        left.addWidget(self.list)
        lh = QHBoxLayout()
        self.btn_new = QPushButton("+ Функция")
        self.btn_edit = QPushButton("Изм")
        self.btn_dup = QPushButton("Дублировать")
        self.btn_del = QPushButton("−")
        lh.addWidget(self.btn_new); lh.addWidget(self.btn_edit)
        lh.addWidget(self.btn_dup); lh.addWidget(self.btn_del)
        lh.addStretch(1)
        left.addLayout(lh)
        top.addLayout(left, 1)

        right = QVBoxLayout()
        self.lbl_info = QLabel("— выберите функцию —")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(
            "background:#f4f4f8; border:1px solid #ccc; padding:6px; "
            "font-family:Consolas; font-size:10px;")
        right.addWidget(self.lbl_info)
        right.addWidget(QLabel("<b>Тело:</b>"))
        self.body_view = QListWidget()
        self.body_view.setFont(QFont("Consolas", 10))
        right.addWidget(self.body_view, 1)
        self.btn_insert = QPushButton("Вставить вызов в псевдокод…")
        right.addWidget(self.btn_insert)
        top.addLayout(right, 2)
        v.addLayout(top, 1)

        ops = QHBoxLayout()
        self.btn_load_dir = QPushButton("Загрузить папку functions/")
        self.btn_save_dir = QPushButton("Сохранить в папку functions/")
        self.btn_import = QPushButton("Импорт файла…")
        self.btn_export = QPushButton("Экспорт файла…")
        ops.addWidget(self.btn_load_dir)
        ops.addWidget(self.btn_save_dir)
        ops.addWidget(self.btn_import)
        ops.addWidget(self.btn_export)
        ops.addStretch(1)
        v.addLayout(ops)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self.list.currentRowChanged.connect(self._select)
        self.btn_new.clicked.connect(self._new)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_dup.clicked.connect(self._dup)
        self.btn_del.clicked.connect(self._del)
        self.btn_insert.clicked.connect(self._insert)
        self.btn_load_dir.clicked.connect(self._load_dir)
        self.btn_save_dir.clicked.connect(self._save_dir)
        self.btn_import.clicked.connect(self._import_file)
        self.btn_export.clicked.connect(self._export_file)

        self._refresh_list()

    def _refresh_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for f in self._functions:
            title = f.title or f.name
            self.list.addItem(f"{f.name} — {title}")
        self.list.blockSignals(False)
        if self._functions:
            self.list.setCurrentRow(min(self._current, len(self._functions) - 1))
        else:
            self._current = -1
            self.lbl_info.setText("— нет функций —")
            self.body_view.clear()

    def _select(self, row):
        self._current = row
        if not (0 <= row < len(self._functions)):
            self.lbl_info.setText("— выберите функцию —")
            self.body_view.clear()
            return
        f = self._functions[row]
        prms = ", ".join(
            f"{p.name}={p.default}" for p in f.params) if f.params else "—"
        self.lbl_info.setText(
            f"<b>{f.name}</b> — {f.title or f.name}<br>"
            f"<i>{f.description or ''}</i><br>"
            f"Параметры: {prms}")
        self.body_view.clear()
        for i, c in enumerate(f.body):
            self.body_view.addItem(c.to_pseudo(i))

    def _new(self):
        known = {f.name for f in self._functions}
        d = FunctionEditorDialog(self, None, known)
        if d.exec_() == QDialog.Accepted and d.result:
            self._functions.append(d.result)
            self._current = len(self._functions) - 1
            self._refresh_list()

    def _edit(self):
        if not (0 <= self._current < len(self._functions)):
            return
        known = {f.name for i, f in enumerate(self._functions)
                 if i != self._current}
        d = FunctionEditorDialog(self, self._functions[self._current], known)
        if d.exec_() == QDialog.Accepted and d.result:
            self._functions[self._current] = d.result
            self._refresh_list()

    def _dup(self):
        if not (0 <= self._current < len(self._functions)):
            return
        new = copy.deepcopy(self._functions[self._current])
        base = new.name + "_COPY"
        i = 1
        names = {f.name for f in self._functions}
        while base in names:
            i += 1
            base = f"{new.name}_COPY{i}"
        new.name = base
        self._functions.append(new)
        self._current = len(self._functions) - 1
        self._refresh_list()

    def _del(self):
        if not (0 <= self._current < len(self._functions)):
            return
        ans = QMessageBox.question(self, "Удалить",
            f"Удалить функцию {self._functions[self._current].name}?",
            QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        del self._functions[self._current]
        self._current = min(self._current, len(self._functions) - 1)
        self._refresh_list()

    def _insert(self):
        if not (0 <= self._current < len(self._functions)):
            return
        if not callable(self._on_insert):
            QMessageBox.information(self, "Вставка",
                "Вызов функции можно добавить через «Добавить команду» → CALL_FUNC.")
            return
        fn = self._functions[self._current]
        self._on_insert(fn)

    def _load_dir(self):
        d = file_io.functions_dir()
        funcs = file_io.load_functions_dir(d)
        if not funcs:
            QMessageBox.information(self, "Загрузка",
                f"В папке {d} нет функций.")
            return
        self._functions = funcs
        self._current = 0
        self._refresh_list()

    def _save_dir(self):
        d = file_io.functions_dir()
        try:
            file_io.save_functions_to_dir(d, self._functions)
            QMessageBox.information(self, "Сохранение",
                f"Сохранено {len(self._functions)} функций в {d}.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт функции", "",
            "Function (*.json *.gfunc.json);;Все (*)")
        if not path:
            return
        try:
            fn = file_io.load_function_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        names = {f.name for f in self._functions}
        if fn.name in names:
            ans = QMessageBox.question(self, "Импорт",
                f"Функция {fn.name} уже есть. Заменить?",
                QMessageBox.Yes | QMessageBox.No)
            if ans == QMessageBox.Yes:
                for i, f in enumerate(self._functions):
                    if f.name == fn.name:
                        self._functions[i] = fn
                        break
            else:
                return
        else:
            self._functions.append(fn)
        self._current = len(self._functions) - 1
        self._refresh_list()

    def _export_file(self):
        if not (0 <= self._current < len(self._functions)):
            return
        fn = self._functions[self._current]
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт функции", f"{fn.name}.json",
            "Function (*.json);;Все (*)")
        if not path:
            return
        try:
            file_io.save_function_file(path, fn)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_ok(self):
        self.result = self._functions
        self.accept()


# ============================================================
#             НАЧАЛО / КОНЕЦ КОДА (PREAMBLE/POSTAMBLE)
# ============================================================

class _CommandListEditor(QWidget):
    def __init__(self, parent=None, commands=None):
        super().__init__(parent)
        self._commands = list(commands or [])
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setFont(QFont("Consolas", 10))
        v.addWidget(self.list, 1)
        h = QHBoxLayout()
        self.btn_add = QPushButton("+ Команда")
        self.btn_edit = QPushButton("Изм")
        self.btn_del = QPushButton("−")
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        for b in (self.btn_add, self.btn_edit, self.btn_del,
                  self.btn_up, self.btn_down):
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._del)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(+1))
        self._refresh()

    def _refresh(self):
        self.list.clear()
        for i, c in enumerate(self._commands):
            self.list.addItem(c.to_pseudo(i))

    def commands(self):
        return list(self._commands)

    def _add(self):
        d = CommandPickerDialog(self, None, {})
        if d.exec_() == QDialog.Accepted and d.result_command:
            self._commands.append(d.result_command)
            self._refresh()

    def _edit(self):
        r = self.list.currentRow()
        if r < 0:
            return
        d = CommandPickerDialog(self, self._commands[r], {})
        if d.exec_() == QDialog.Accepted and d.result_command:
            self._commands[r] = d.result_command
            self._refresh()

    def _del(self):
        r = self.list.currentRow()
        if r < 0:
            return
        del self._commands[r]
        self._refresh()

    def _move(self, delta):
        r = self.list.currentRow()
        if r < 0:
            return
        nr = r + delta
        if nr < 0 or nr >= len(self._commands):
            return
        self._commands[r], self._commands[nr] = \
            self._commands[nr], self._commands[r]
        self._refresh()
        self.list.setCurrentRow(nr)


class PreamblePostambleDialog(QDialog):
    def __init__(self, parent=None, preamble=None, postamble=None):
        super().__init__(parent)
        self.setWindowTitle("Начало / Конец кода")
        self.setMinimumSize(640, 520)
        self.result = None
        v = QVBoxLayout(self)
        tabs = QTabWidget()
        self.ed_pre = _CommandListEditor(self, preamble or [])
        self.ed_post = _CommandListEditor(self, postamble or [])
        tabs.addTab(self.ed_pre, "Начало (preamble)")
        tabs.addTab(self.ed_post, "Конец (postamble)")
        v.addWidget(tabs, 1)
        hint = QLabel(
            "Эти команды добавляются в начале и конце G-кода соответственно — "
            "после '%' в начале и перед финальным '%' в конце. "
            "Пример: инициализация Mach3 (G21 G90 G17), отвод и M30.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555; font-size:10px;")
        v.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _on_ok(self):
        self.result = (self.ed_pre.commands(), self.ed_post.commands())
        self.accept()


# ============================================================
#                    СПИСОК КОДОВ
# ============================================================

class CodeLibraryDialog(QDialog):
    def __init__(self, parent=None, code_order=None, code_hidden=None,
                 sort_mode="custom"):
        super().__init__(parent)
        self.setWindowTitle("Список кодов")
        self.setMinimumSize(720, 620)
        self._all = list(ORDERED_MNEMONICS)
        self._order = list(code_order) if code_order else list(self._all)
        for m in self._all:
            if m not in self._order:
                self._order.append(m)
        self._hidden = set(code_hidden or [])
        self._sort_mode = sort_mode or "custom"
        self._sync_sort()
        self.result = None

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Сортировка:"))
        self.cb_sort = QComboBox()
        self.cb_sort.addItem("Пользовательский порядок", "custom")
        self.cb_sort.addItem("По алфавиту", "alpha")
        self.cb_sort.addItem("По описанию", "desc")
        self.cb_sort.addItem("По группе", "group")
        i = self.cb_sort.findData(self._sort_mode)
        if i >= 0: self.cb_sort.setCurrentIndex(i)
        self.cb_sort.currentIndexChanged.connect(self._on_sort_changed)
        top.addWidget(self.cb_sort)
        top.addStretch(1)
        self.btn_default = QPushButton("Сбросить к дефолту")
        self.btn_default.clicked.connect(self._reset_default)
        top.addWidget(self.btn_default)
        v.addLayout(top)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        v.addWidget(self.list, 1)

        rows = QHBoxLayout()
        self.btn_up = QPushButton("▲ Вверх")
        self.btn_down = QPushButton("▼ Вниз")
        self.btn_toggle = QPushButton("Скрыть/Показать")
        rows.addWidget(self.btn_up)
        rows.addWidget(self.btn_down)
        rows.addWidget(self.btn_toggle)
        rows.addStretch(1)
        v.addLayout(rows)
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        self.btn_toggle.clicked.connect(self._toggle)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._refresh()

    def _sync_sort(self):
        if self._sort_mode == "alpha":
            self._order.sort(key=lambda x: x)
        elif self._sort_mode == "desc":
            self._order.sort(key=lambda x: get_command_desc(x).lower())
        elif self._sort_mode == "group":
            self._order.sort(key=lambda x: (get_command_group(x), x))

    def _on_sort_changed(self):
        self._sort_mode = self.cb_sort.currentData()
        self._sync_sort()
        self._refresh()

    def _refresh(self):
        cur = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        for m in self._order:
            desc = get_command_desc(m)
            grp = get_command_group(m)
            hidden = "  (скрыт)" if m in self._hidden else ""
            self.list.addItem(f"[{grp}] {m} — {desc}{hidden}")
        self.list.blockSignals(False)
        if 0 <= cur < self.list.count():
            self.list.setCurrentRow(cur)

    def _move_up(self):
        r = self.list.currentRow()
        if r <= 0:
            return
        self._order[r], self._order[r-1] = self._order[r-1], self._order[r]
        self._sort_mode = "custom"
        i = self.cb_sort.findData("custom")
        if i >= 0: self.cb_sort.setCurrentIndex(i)
        self._refresh()
        self.list.setCurrentRow(r-1)

    def _move_down(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self._order) - 1:
            return
        self._order[r], self._order[r+1] = self._order[r+1], self._order[r]
        self._sort_mode = "custom"
        i = self.cb_sort.findData("custom")
        if i >= 0: self.cb_sort.setCurrentIndex(i)
        self._refresh()
        self.list.setCurrentRow(r+1)

    def _toggle(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self._order):
            return
        m = self._order[r]
        if m in self._hidden:
            self._hidden.discard(m)
        else:
            self._hidden.add(m)
        self._refresh()
        self.list.setCurrentRow(r)

    def _reset_default(self):
        self._order = list(ORDERED_MNEMONICS)
        self._hidden = set()
        self._sort_mode = "custom"
        i = self.cb_sort.findData("custom")
        if i >= 0: self.cb_sort.setCurrentIndex(i)
        self._refresh()

    def _on_ok(self):
        self.result = (self._order, sorted(self._hidden), self._sort_mode)
        self.accept()


# ============================================================
#                        СПРАВКА
# ============================================================

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка — G-Code редактор")
        self.setMinimumSize(900, 720)
        self.resize(1080, 820)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        title = QLabel("<h2 style='margin:0'>Руководство пользователя</h2>")
        v.addWidget(title)
        tabs = QTabWidget()

        tabs.addTab(self._make_tab(help_content.HELP_INTRO_HTML), "Введение")
        tabs.addTab(self._make_tab(help_content.HELP_QUICKSTART_HTML), "Быстрый старт")
        tabs.addTab(self._make_tab(help_content.HELP_NAV_HTML), "Навигация 3D")
        tabs.addTab(self._make_tab(help_content.HELP_TOOLS_HTML), "Инструменты")
        tabs.addTab(self._make_tab(help_content.HELP_VARS_HTML), "Переменные и формулы")
        tabs.addTab(self._make_tab(help_content.HELP_STOCK_HTML), "Заготовка")
        tabs.addTab(self._make_tab(help_content.HELP_PSEUDOCODE_HTML), "Псевдокод")
        tabs.addTab(self._make_tab(help_content.HELP_FUNCS_HTML), "Библиотека функций")
        tabs.addTab(self._make_tab(help_content.HELP_GCODE_HTML), "G-код")
        tabs.addTab(self._make_tab(help_content.HELP_SIM_HTML), "Симуляция")
        tabs.addTab(self._make_tab(help_content.HELP_VIEW_HTML), "Вид и освещение")
        tabs.addTab(self._make_tab(help_content.HELP_PROJECT_HTML), "Проект")
        tabs.addTab(self._make_tab(help_content.HELP_KEYS_HTML), "Горячие клавиши")
        tabs.addTab(self._make_tab(help_content.HELP_FAQ_HTML), "FAQ")
        tabs.addTab(self._make_tab(help_content.HELP_CODES_HTML), "Список кодов")
        tabs.addTab(self._make_tab(self._pseudocode_html()), "Справочник команд")

        v.addWidget(tabs, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self._tabs = tabs

    def _make_tab(self, html):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(6, 6, 6, 6)
        b = QTextBrowser()
        b.setOpenExternalLinks(False)
        b.setHtml(html)
        b.setStyleSheet(
            "QTextBrowser{background:#1e1e24;color:#ddd;"
            "font-family:'Segoe UI','Arial';font-size:11pt;border:0;}"
            "h2{color:#8ab4f8;} h3{color:#c586c0;margin-top:14px;}"
            "code,kbd{background:#2d2d36;color:#f5d07a;padding:1px 5px;"
            "border-radius:3px;font-family:Consolas,monospace;}"
            "pre{background:#25252d;color:#e0e0e0;padding:8px;border-radius:4px;}"
            "table{border-collapse:collapse;}"
            "td,th{border:1px solid #444;padding:4px 8px;}"
            "th{background:#2a2a33;color:#9cdcfe;}"
            "li{margin:3px 0;}")
        lay.addWidget(b); return w

    def _pseudocode_html(self):
        rows = []
        for m in ORDERED_MNEMONICS:
            d = COMMAND_DEFS[m]
            desc = d[0]
            fields = d[1]
            params = ", ".join(f[0] for f in fields) if fields else "—"
            rows.append(f"<tr><td><code>{m}</code></td><td>{desc}</td>"
                        f"<td><code>{params}</code></td></tr>")
        return ("<h2>Справочник команд псевдокода</h2>"
                "<table><tr><th>Мнемоника</th><th>Описание</th>"
                "<th>Параметры</th></tr>" + "".join(rows) + "</table>")

    def show_tab(self, i):
        self._tabs.setCurrentIndex(i)