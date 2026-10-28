# -*- coding: utf-8 -*-
"""Главное окно приложения."""

import math
import re
import time

from PyQt5.QtCore import Qt, QTimer, QSettings, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QColor, QBrush, QTextCursor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QListWidget,
    QPlainTextEdit, QMessageBox, QFileDialog, QAbstractItemView,
    QHeaderView, QGroupBox, QSlider, QCheckBox, QToolBar, QAction,
    QShortcut, QApplication, QDialog, QMenu, QDockWidget, QToolButton,
    QSizePolicy,
)

from gcode_editor.core.models import (
    Tool, Stock, UserVar, Command,
    SimSettings, AppSettings, LightingSource, default_lights,
)
from gcode_editor.core.constants import APP_NAME, APP_ORG
from gcode_editor.core.formula import build_env
from gcode_editor.code.generator import GCodeGenerator
from gcode_editor.code.parser import GCodeParser
from gcode_editor.sim.simulator import Simulator
from gcode_editor.ui.constants import ShadingMode
from gcode_editor.ui.dialogs import (
    ToolDialog, StockDialog, VarDialog, CommandPickerDialog, HelpDialog,
    SimulationSettingsDialog, LightingDialog,
    FunctionLibraryDialog, PreamblePostambleDialog, CodeLibraryDialog,
)
from gcode_editor.ui.highlighter import GCodeHighlighter
from gcode_editor.ui.viz_panel import VizPanel
from gcode_editor.ui import functions_seed
from gcode_editor.io import file_io


class _DockTitleBar(QWidget):
    """Кастомный заголовок: название + булавка (отстегнуть/пристегнуть)."""

    def __init__(self, dock, on_float_toggle=None):
        super().__init__(dock)
        self._dock = dock
        self._on_float_toggle = on_float_toggle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)

        self._label = QLabel(dock.windowTitle(), self)
        self._label.setStyleSheet("font-weight:bold; color:#ddd;")
        self._label.setMinimumWidth(0)
        layout.addWidget(self._label, 1)

        self._btn = QToolButton(self)
        self._btn.setText("📌")
        self._btn.setFixedSize(22, 22)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setToolTip("Отстыковать / пристыковать")
        self._btn.setStyleSheet(
            "QToolButton{background:transparent;border:0;font-size:13px;"
            "padding:0;}"
            "QToolButton:hover{background:rgba(255,255,255,0.15);"
            "border-radius:3px;}")
        self._btn.clicked.connect(self._toggle_float)
        layout.addWidget(self._btn, 0)

        dock.installEventFilter(self)

    def _toggle_float(self):
        d = self._dock
        if d.isFloating():
            d.setWindowFlags(Qt.Widget)
            d.setFloating(False)
            d.show()
        else:
            d.setFloating(True)
            d.setWindowFlags(Qt.Window |
                             Qt.WindowTitleHint |
                             Qt.WindowSystemMenuHint |
                             Qt.WindowMinMaxButtonsHint |
                             Qt.WindowCloseButtonHint)
            d.resize(640, 420)
            d.show()
        if callable(self._on_float_toggle):
            self._on_float_toggle(d, d.isFloating())

    def eventFilter(self, obj, ev):
        if obj is self._dock and ev.type() == QEvent.WindowTitleChange:
            self._label.setText(self._dock.windowTitle())
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Code редактор для Mach3")
        self.resize(1500, 900)
        self.setMinimumSize(900, 600)

        self.settings_q = QSettings(APP_ORG, APP_NAME)

        self.tools = [Tool(1, "End mill 3мм", 3.0, 200.0, 8000, "#3399ff")]
        self.variables = []
        self.commands = []
        self.stock = Stock()

        self.app_settings = AppSettings()
        self._load_global_settings()
        self._ensure_seed_functions()

        self.code_lines = []
        self.gline_to_cmd = {}
        self.cmd_to_glines = {}
        self.last_segments = []
        self.last_bounds = None
        self.last_stats = None

        self._suspend = False
        self._sync_busy = False
        self.auto_update_on_select = True
        self.anim_tool = True

        self._anim_segs = []
        self._anim_idx = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(25)
        self._anim_timer.timeout.connect(self._anim_tick)

        self._dock_widgets = {}
        self._dock_titlebars = {}

        self._viz_float_window = None
        self._viz_parked_widget = None
        self._viz_content = None

        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.GroupedDragging
        )

        self._build_ui()
        self._build_menubar()
        self._build_help_button()
        self._build_pseudo_shortcuts()
        self._build_status_widgets()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._start_generation)

        QTimer.singleShot(0, self._apply_initial_dock_sizes)

        self._refresh_tools()
        self._refresh_vars()
        self._refresh_pseudo()
        self._start_generation()

    def _ensure_seed_functions(self):
        try:
            functions_seed.ensure_seed_functions()
        except Exception as e:
            print("seed functions error:", e)

    def _load_global_settings(self):
        q = self.settings_q
        s = self.app_settings
        s.sim.auto_voxel_xy = self._qbool("sim/auto_voxel_xy", s.sim.auto_voxel_xy)
        s.sim.voxel_xy = self._qfloat("sim/voxel_xy", s.sim.voxel_xy)
        s.sim.voxel_z = self._qfloat("sim/voxel_z", s.sim.voxel_z)
        s.sim.max_memory_fraction = self._qfloat(
            "sim/max_memory_fraction", s.sim.max_memory_fraction)
        s.sim.rapid_line_width = self._qfloat(
            "sim/rapid_line_width", s.sim.rapid_line_width)
        s.sim.feed_line_width = self._qfloat(
            "sim/feed_line_width", s.sim.feed_line_width)
        s.sim.rapid_dash = self._qbool("sim/rapid_dash", s.sim.rapid_dash)
        s.toolpath_visible = self._qbool("view/toolpath", s.toolpath_visible)
        s.material_visible = self._qbool("view/material", s.material_visible)
        s.ignore_rapid_in_material = self._qbool(
            "sim/ignore_rapid", s.ignore_rapid_in_material)
        s.unroll_loops = self._qbool("sim/unroll_loops", s.unroll_loops)
        s.step_limit = int(self._qfloat("sim/step_limit", float(s.step_limit)))
        s.lighting_mode = q.value("lighting/mode", s.lighting_mode, type=str)
        self.auto_update_on_select = self._qbool(
            "sim/auto_update_on_select", True)
        self.anim_tool = self._qbool("sim/anim_tool", True)
        s.code_order = list(q.value("codes/order", [], type=list) or [])
        s.code_hidden = list(q.value("codes/hidden", [], type=list) or [])
        s.code_sort_mode = q.value("codes/sort_mode", "custom", type=str) or "custom"

    def _save_global_settings(self):
        q = self.settings_q
        s = self.app_settings
        q.setValue("sim/auto_voxel_xy", bool(s.sim.auto_voxel_xy))
        q.setValue("sim/voxel_xy", float(s.sim.voxel_xy))
        q.setValue("sim/voxel_z", float(s.sim.voxel_z))
        q.setValue("sim/max_memory_fraction", float(s.sim.max_memory_fraction))
        q.setValue("sim/rapid_line_width", float(s.sim.rapid_line_width))
        q.setValue("sim/feed_line_width", float(s.sim.feed_line_width))
        q.setValue("sim/rapid_dash", bool(s.sim.rapid_dash))
        q.setValue("view/toolpath", bool(s.toolpath_visible))
        q.setValue("view/material", bool(s.material_visible))
        q.setValue("sim/ignore_rapid", bool(s.ignore_rapid_in_material))
        q.setValue("sim/unroll_loops", bool(s.unroll_loops))
        q.setValue("sim/step_limit", int(s.step_limit))
        q.setValue("lighting/mode", s.lighting_mode)
        q.setValue("sim/auto_update_on_select", bool(self.auto_update_on_select))
        q.setValue("sim/anim_tool", bool(self.anim_tool))
        q.setValue("codes/order", s.code_order)
        q.setValue("codes/hidden", s.code_hidden)
        q.setValue("codes/sort_mode", s.code_sort_mode)

    def _qbool(self, key, default):
        v = self.settings_q.value(key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("1", "true", "yes", "on")

    def _qfloat(self, key, default):
        v = self.settings_q.value(key, None)
        if v is None:
            return float(default)
        try:
            return float(v)
        except Exception:
            return float(default)

    def _build_menubar(self):
        mb = self.menuBar()

        m_file = mb.addMenu("Файл")
        self._add_action(m_file, "Сохранить проект…", self.save_project,
                         QKeySequence.Save)
        self._add_action(m_file, "Открыть проект…", self.load_project,
                         QKeySequence.Open)
        m_file.addSeparator()
        self._add_action(m_file, "Пример", self.load_sample)
        m_file.addSeparator()
        self._add_action(m_file, "Экспорт G-кода…", self.export_gcode)
        self._add_action(m_file, "Импорт G-кода…", self.import_gcode)
        m_file.addSeparator()
        self._add_action(m_file, "Экспорт инструментов в CSV…",
                         self.export_tools_csv)
        self._add_action(m_file, "Импорт инструментов из CSV…",
                         self.import_tools_csv)
        m_file.addSeparator()
        self._add_action(m_file, "Заготовка…", self.edit_stock)
        m_file.addSeparator()
        self._add_action(m_file, "Список кодов…", self.open_code_library)
        m_file.addSeparator()
        self._add_action(m_file, "Выход", self.close, QKeySequence.Quit)

        m_lib = mb.addMenu("Библиотека")
        self._add_action(m_lib, "Открыть библиотеку функций…",
                         self.open_function_library)
        m_lib.addSeparator()
        self._add_action(m_lib, "Загрузить из папки functions/",
                         self.load_functions_from_dir)
        self._add_action(m_lib, "Сохранить в папку functions/",
                         self.save_functions_to_dir)
        m_lib.addSeparator()
        self._add_action(m_lib, "Импорт файла…", self.import_function_file)
        self._add_action(m_lib, "Экспорт всех в один файл…",
                         self.export_functions_all)

        m_view = mb.addMenu("Вид")
        self._add_action(m_view, "Сверху", self.viz.view3d.set_top)
        self._add_action(m_view, "Спереди", self.viz.view3d.set_front)
        self._add_action(m_view, "Изометрия", self.viz.view3d.set_iso)
        m_view.addSeparator()
        self._add_action(m_view, "Сбросить камеру", self._reset_camera)
        m_view.addSeparator()
        self._add_action(m_view, "Освещение…", self.open_lighting_dialog)
        m_view.addSeparator()
        self._add_dock_toggle_actions(m_view)
        m_view.addSeparator()
        self._add_action(m_view, "Сбросить раскладку окон",
                         self._reset_dock_layout)

        m_sim = mb.addMenu("Симуляция")
        self._add_action(m_sim, "Настройки…", self.open_settings_dialog)
        self._add_action(m_sim, "Начало / Конец кода…",
                         self.open_preamble_dialog)
        self._add_action(m_sim, "Перегенерировать симуляцию",
                         self.regenerate_simulation)
        self._add_action(m_sim, "Сбросить кэш материала",
                         lambda: self.viz.view3d.refresh_scene())

        m_help = mb.addMenu("Помощь")
        self._add_action(m_help, "Руководство (F1)", lambda: self.open_help(0),
                         QKeySequence(Qt.Key_F1))
        self._add_action(m_help, "Справочник команд",
                         lambda: self.open_help(15))
        m_help.addSeparator()
        self._add_action(m_help, "О программе", self._about)

    def _add_action(self, menu, text, slot, shortcut=None):
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut is not None:
            a.setShortcut(shortcut)
        menu.addAction(a)
        return a

    def _add_dock_toggle_actions(self, menu):
        for key in ("tools", "vars", "pseudo", "gcode",
                    "collisions", "viz"):
            dock = self._dock_widgets.get(key)
            if dock is None:
                continue
            act = dock.toggleViewAction()
            act.setText(dock.windowTitle())
            menu.addAction(act)

    def _reset_camera(self):
        self.viz.view3d.reset_target()
        self.viz.view3d.reset_view()

    def _make_dock(self, key, title, widget, with_titlebar=True):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{key}")
        dock.setFeatures(QDockWidget.DockWidgetMovable |
                         QDockWidget.DockWidgetFloatable)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        if with_titlebar:
            titlebar = _DockTitleBar(dock, on_float_toggle=None)
            dock.setTitleBarWidget(titlebar)
            self._dock_titlebars[key] = titlebar
        self._dock_widgets[key] = dock
        return dock

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # ---------- Инструменты ----------
        tools_widget = QWidget()
        tl = QVBoxLayout(tools_widget)
        tl.setContentsMargins(4, 4, 4, 4)
        self.tool_table = QTableWidget(0, 5)
        self.tool_table.setHorizontalHeaderLabels(["№", "Имя", "D", "F", "RPM"])
        self.tool_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tool_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tool_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tool_table.doubleClicked.connect(self.edit_tool)
        tl.addWidget(self.tool_table, 1)
        row = QHBoxLayout()
        for t, s in [("+", self.add_tool), ("Изм", self.edit_tool), ("−", self.delete_tool)]:
            b = QPushButton(t); b.clicked.connect(s); row.addWidget(b)
        tl.addLayout(row)

        self.dock_tools = self._make_dock("tools", "Инструменты", tools_widget)

        # ---------- Переменные ----------
        vars_widget = QWidget()
        vl = QVBoxLayout(vars_widget)
        vl.setContentsMargins(4, 4, 4, 4)
        self.var_table = QTableWidget(0, 2)
        self.var_table.setHorizontalHeaderLabels(["Имя", "Значение"])
        self.var_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.var_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.var_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.var_table.doubleClicked.connect(self.edit_var)
        vl.addWidget(self.var_table, 1)
        row2 = QHBoxLayout()
        for t, s in [("+", self.add_var), ("Изм", self.edit_var), ("−", self.delete_var)]:
            b = QPushButton(t); b.clicked.connect(s); row2.addWidget(b)
        vl.addLayout(row2)
        self.var_preview = QLabel("")
        self.var_preview.setWordWrap(True)
        self.var_preview.setStyleSheet(
            "color:#2a6099; font-family:Consolas; font-size:10px;")
        self.var_preview.setMaximumHeight(60)
        vl.addWidget(self.var_preview)

        self.dock_vars = self._make_dock("vars", "Переменные", vars_widget)

        # ---------- Псевдокод ----------
        pseudo_widget = QWidget()
        pv = QVBoxLayout(pseudo_widget)
        pv.setContentsMargins(4, 4, 4, 4)

        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.chk_auto_sim = QCheckBox("Обновлять при выборе")
        self.chk_auto_sim.setChecked(self.auto_update_on_select)
        self.chk_auto_sim.toggled.connect(self._on_auto_sim_toggled)
        top_row.addWidget(self.chk_auto_sim)
        self.chk_anim_tool = QCheckBox("Анимация фрезы")
        self.chk_anim_tool.setChecked(self.anim_tool)
        self.chk_anim_tool.setToolTip(
            "Проигрывать движение фрезы по траектории после расчёта")
        self.chk_anim_tool.toggled.connect(self._on_anim_tool_toggled)
        top_row.addWidget(self.chk_anim_tool)
        pv.addLayout(top_row)

        self.pseudo_list = QListWidget()
        self.pseudo_list.setFont(QFont("Consolas", 10))
        self.pseudo_list.itemDoubleClicked.connect(lambda _: self.edit_command())
        self.pseudo_list.itemSelectionChanged.connect(self._on_pseudo_sel)
        self.pseudo_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pseudo_list.customContextMenuRequested.connect(
            self._on_pseudo_context_menu)
        pv.addWidget(self.pseudo_list, 1)

        prow = QHBoxLayout()
        self.btn_pc_add = QPushButton("+ Команда")
        self.btn_pc_edit = QPushButton("Изм")
        self.btn_pc_del = QPushButton("− Удалить")
        self.btn_pc_up = QPushButton("▲")
        self.btn_pc_down = QPushButton("▼")
        for b in (self.btn_pc_add, self.btn_pc_edit, self.btn_pc_del,
                  self.btn_pc_up, self.btn_pc_down):
            prow.addWidget(b)
        prow.addStretch(1)
        pv.addLayout(prow)
        self.btn_pc_add.clicked.connect(self.add_command)
        self.btn_pc_edit.clicked.connect(self.edit_command)
        self.btn_pc_del.clicked.connect(self.delete_command)
        self.btn_pc_up.clicked.connect(lambda: self.move_command(-1))
        self.btn_pc_down.clicked.connect(lambda: self.move_command(+1))

        self.dock_pseudo = self._make_dock("pseudo", "Псевдокод", pseudo_widget)

        # ---------- G-код ----------
        gcode_widget = QWidget()
        gv = QVBoxLayout(gcode_widget)
        gv.setContentsMargins(4, 4, 4, 4)

        opts = QHBoxLayout()
        self.chk_unroll = QCheckBox("Развернуть IF/GOTO")
        self.chk_unroll.setChecked(self.app_settings.unroll_loops)
        self.chk_unroll.toggled.connect(self._on_unroll_changed)
        opts.addWidget(self.chk_unroll)
        opts.addWidget(QLabel("Шаг:"))
        self.slider_step = QSlider(Qt.Horizontal)
        self.slider_step.setRange(1, 300)
        if self.app_settings.step_limit and 1 <= self.app_settings.step_limit < 300:
            self.slider_step.setValue(self.app_settings.step_limit)
        else:
            self.slider_step.setValue(300)
        self.slider_step.setMinimumWidth(120)
        self.slider_step.setSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Fixed)
        self.slider_step.valueChanged.connect(self._on_step_changed)
        opts.addWidget(self.slider_step, 1)
        self.lbl_step = QLabel("все"); opts.addWidget(self.lbl_step)
        self.btn_regen_sim = QPushButton("↻ Перегенерировать")
        self.btn_regen_sim.setToolTip(
            "Пересобрать симуляцию без изменения выбора псевдокоманды")
        self.btn_regen_sim.clicked.connect(self.regenerate_simulation)
        opts.addWidget(self.btn_regen_sim)
        gv.addLayout(opts)

        self.gcode_edit = QPlainTextEdit()
        self.gcode_edit.setFont(QFont("Consolas", 10))
        self.gcode_edit.setReadOnly(True)
        self.gcode_edit.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.gcode_edit.cursorPositionChanged.connect(self._on_gcode_cur)
        self.highlighter = GCodeHighlighter(self.gcode_edit.document())
        gv.addWidget(self.gcode_edit, 1)

        self.stats_label = QLabel("Статистика: —")
        self.stats_label.setStyleSheet("color:#444; font-family:Consolas;")
        self.stats_label.setWordWrap(True)
        gv.addWidget(self.stats_label)

        self.dock_gcode = self._make_dock("gcode", "G-код", gcode_widget)

        # ---------- Журнал коллизий ----------
        coll_widget = QWidget()
        cl = QVBoxLayout(coll_widget)
        cl.setContentsMargins(4, 4, 4, 4)
        self.collision_table = QTableWidget(0, 5)
        self.collision_table.setHorizontalHeaderLabels(
            ["#", "Мнемоника", "X", "Y", "Z / причина"])
        self.collision_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.collision_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.collision_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.collision_table.itemSelectionChanged.connect(self._on_collision_click)
        cl.addWidget(self.collision_table, 1)

        self.dock_collisions = self._make_dock("collisions", "Журнал коллизий",
                                               coll_widget)

        # ---------- 3D ----------
        viz_widget = QWidget()
        vv = QVBoxLayout(viz_widget)
        vv.setContentsMargins(0, 0, 0, 0)
        self.viz = VizPanel()
        self.viz.on_ignore_rapid_changed = self._on_ignore_rapid_changed
        self.viz.on_lighting_clicked = self.open_lighting_dialog
        self.viz.on_settings_clicked = self.open_settings_dialog
        self.viz.on_toolpath_changed = self._on_toolpath_changed
        self.viz.on_material_changed = self._on_material_changed
        self.viz.on_widths_changed = self._on_widths_changed
        self.viz.on_float_toggle = self._toggle_viz_float
        self.viz.act_ignore_rapid.setChecked(
            self.app_settings.ignore_rapid_in_material)
        self.viz.set_visibility(self.app_settings.toolpath_visible,
                                self.app_settings.material_visible)
        self.viz.set_widths(self.app_settings.sim.rapid_line_width,
                            self.app_settings.sim.feed_line_width)
        vv.addWidget(self.viz, 1)

        self._viz_content = viz_widget

        self.dock_viz = self._make_dock("viz", "Визуализация (3D)",
                                        viz_widget, with_titlebar=False)

        # ---------- раскладка ----------
        self._layout_default_docks()

    def _layout_default_docks(self):
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_tools)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_vars)
        self.splitDockWidget(self.dock_tools, self.dock_vars, Qt.Vertical)

        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_pseudo)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_gcode)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_collisions)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_viz)

        self.splitDockWidget(self.dock_pseudo, self.dock_viz, Qt.Horizontal)
        self.splitDockWidget(self.dock_pseudo, self.dock_gcode, Qt.Vertical)
        self.splitDockWidget(self.dock_gcode, self.dock_collisions, Qt.Vertical)

    def _apply_initial_dock_sizes(self):
        try:
            for d in self._dock_widgets.values():
                if d.isFloating():
                    return
            total_w = max(self.width(), 900)
            total_h = max(self.height(), 600)

            left_w = int(total_w * 0.20)
            mid_w = int(total_w * 0.20)
            right_w = total_w - left_w - mid_w

            self.resizeDocks([self.dock_tools, self.dock_vars],
                             [total_h // 2, total_h - total_h // 2],
                             Qt.Vertical)
            h3 = total_h // 3
            self.resizeDocks([self.dock_pseudo, self.dock_gcode,
                              self.dock_collisions],
                             [h3, h3, total_h - 2 * h3], Qt.Vertical)
            self.resizeDocks([self.dock_tools, self.dock_pseudo],
                             [left_w, mid_w + right_w], Qt.Horizontal)
            self.resizeDocks([self.dock_pseudo, self.dock_viz],
                             [mid_w, right_w], Qt.Horizontal)
        except Exception as e:
            print("dock sizes error:", e)

    def _reset_dock_layout(self):
        self._close_viz_float_window()

        for key in ("tools", "vars", "pseudo", "gcode", "collisions", "viz"):
            dock = self._dock_widgets.get(key)
            if dock is None:
                continue
            if dock.isFloating():
                dock.setWindowFlags(Qt.Widget)
                dock.setFloating(False)
            dock.show()
        for d in self._dock_widgets.values():
            try:
                self.removeDockWidget(d)
            except Exception:
                pass
        self._layout_default_docks()
        QTimer.singleShot(0, self._apply_initial_dock_sizes)

    def _toggle_viz_float(self):
        if self._viz_float_window is None:
            self._open_viz_float_window()
        else:
            self._close_viz_float_window()

    def _open_viz_float_window(self):
        try:
            try:
                self.viz.view3d._resizing = True
                self.viz.view3d._render_timer.stop()
            except Exception:
                pass

            self._viz_parked_widget = QWidget()
            self.dock_viz.setWidget(self._viz_parked_widget)

            win = QWidget(None, Qt.Window)
            win.setWindowTitle("Визуализация (3D) — отдельное окно")
            win.setAttribute(Qt.WA_DeleteOnClose, True)
            win.setMinimumSize(400, 300)
            lay = QVBoxLayout(win)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._viz_content)
            self._viz_content.setParent(win)
            self._viz_content.show()
            win.resize(1000, 700)
            win.show()
            self._viz_float_window = win

            win.destroyed.connect(self._on_viz_window_destroyed)

            QApplication.processEvents()
            try:
                self.viz.view3d._resizing = False
                self.viz.view3d.plotter.render()
            except Exception:
                pass
        except Exception as e:
            print(f"[MainWindow] open viz window error: {e}")
            self._viz_float_window = None

    def _close_viz_float_window(self):
        if self._viz_float_window is None:
            return
        try:
            self._viz_float_window.destroyed.disconnect(
                self._on_viz_window_destroyed)
        except Exception:
            pass
        win = self._viz_float_window
        self._viz_float_window = None
        try:
            if self._viz_parked_widget is not None:
                self.dock_viz.setWidget(self._viz_content)
                self._viz_parked_widget = None
                try:
                    self.viz.view3d._resizing = True
                except Exception:
                    pass
                QApplication.processEvents()
                try:
                    self.viz.view3d._resizing = False
                    self.viz.view3d.plotter.render()
                except Exception:
                    pass
        except Exception as e:
            print(f"[MainWindow] return viz to dock error: {e}")
        try:
            win.close()
            win.deleteLater()
        except Exception:
            pass

    def _on_viz_window_destroyed(self, *_):
        self._viz_float_window = None
        try:
            if self._viz_parked_widget is not None:
                self.dock_viz.setWidget(self._viz_content)
                self._viz_parked_widget = None
        except Exception:
            pass

    def _build_status_widgets(self):
        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label, 1)
        self.btn_status_cancel = QPushButton("Отмена")
        self.btn_status_cancel.setFixedWidth(90)
        self.btn_status_cancel.clicked.connect(self._cancel_animation)
        self.btn_status_cancel.setVisible(False)
        self.statusBar().addPermanentWidget(self.btn_status_cancel)

    def _build_pseudo_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Insert), self.pseudo_list,
                  activated=self.add_command)
        QShortcut(QKeySequence(Qt.Key_Delete), self.pseudo_list,
                  activated=self.delete_command)
        QShortcut(QKeySequence("Ctrl+Up"), self.pseudo_list,
                  activated=lambda: self.move_command(-1))
        QShortcut(QKeySequence("Ctrl+Down"), self.pseudo_list,
                  activated=lambda: self.move_command(+1))

    def _on_pseudo_context_menu(self, pos):
        idx = self.pseudo_list.indexAt(pos).row()
        menu = QMenu(self)
        menu.addAction("Добавить команду…", self.add_command)
        act_edit = menu.addAction("Изменить…", self.edit_command)
        act_del = menu.addAction("Удалить", self.delete_command)
        menu.addSeparator()
        act_up = menu.addAction("Переместить вверх", lambda: self.move_command(-1))
        act_down = menu.addAction("Переместить вниз", lambda: self.move_command(+1))
        if idx < 0:
            act_edit.setEnabled(False)
            act_del.setEnabled(False)
            act_up.setEnabled(False)
            act_down.setEnabled(False)
        menu.exec_(self.pseudo_list.mapToGlobal(pos))

    def _build_help_button(self):
        self.help_btn = QPushButton("?", self)
        self.help_btn.setFixedSize(34, 34)
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setToolTip("Справка (F1)")
        self.help_btn.setStyleSheet(
            "QPushButton{background:#3a7bd5;color:white;border:0;border-radius:17px;"
            "font-size:17px;font-weight:bold;}"
            "QPushButton:hover{background:#4a8bf0;}"
            "QPushButton:pressed{background:#2c62b0;}")
        self.help_btn.clicked.connect(lambda: self.open_help(0))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, "help_btn"):
            m = 12
            self.help_btn.move(self.width() - self.help_btn.width() - m,
                               self.height() - self.help_btn.height() - m)
            self.help_btn.raise_()

    def closeEvent(self, ev):
        self._anim_timer.stop()
        self._close_viz_float_window()
        self._save_global_settings()
        super().closeEvent(ev)

    def open_help(self, tab=0):
        dlg = HelpDialog(self); dlg.show_tab(tab); dlg.exec_()

    def _about(self):
        QMessageBox.information(self, "О программе",
            "G-Code редактор для Mach3\n"
            "Визуальный редактор псевдокода, генератор G-кода и симулятор.\n"
            "© 2024")

    def _cancel_animation(self):
        self._anim_timer.stop()
        self._anim_segs = []
        self._anim_idx = 0
        self._update_status("")
        self.btn_status_cancel.setVisible(False)

    def _update_status(self, text=""):
        self.status_label.setText(text)
        running = self._anim_timer.isActive()
        self.btn_status_cancel.setVisible(running)

    def _on_auto_sim_toggled(self, val):
        self.auto_update_on_select = bool(val)
        if self.auto_update_on_select:
            self._schedule_preview()

    def _on_anim_tool_toggled(self, val):
        self.anim_tool = bool(val)

    def regenerate_simulation(self):
        try:
            self.viz.view3d.refresh_scene()
        except Exception:
            pass
        self._schedule_preview(force=True)
        self.statusBar().showMessage("Симуляция перегенерирована", 2000)

    def _on_unroll_changed(self, s):
        self.app_settings.unroll_loops = bool(s)
        self._schedule_preview(force=True)

    def _on_step_changed(self, v):
        self.app_settings.step_limit = 0 if v >= 300 else v
        self.lbl_step.setText("все" if v >= 300 else str(v))
        self._schedule_preview()

    def _on_ignore_rapid_changed(self, s):
        self.app_settings.ignore_rapid_in_material = bool(s)
        self._schedule_preview()

    def _on_toolpath_changed(self, s):
        self.app_settings.toolpath_visible = bool(s)
        self.viz.view3d.set_show_toolpath(bool(s))

    def _on_material_changed(self, s):
        self.app_settings.material_visible = bool(s)
        self.viz.view3d.set_show_material(bool(s))

    def _on_widths_changed(self, rapid_w, feed_w):
        self.app_settings.sim.rapid_line_width = float(rapid_w)
        self.app_settings.sim.feed_line_width = float(feed_w)

    def _current_upto(self):
        pseudo_row = self.pseudo_list.currentRow()
        if pseudo_row >= 0:
            return pseudo_row + 1
        gline = self.gcode_edit.textCursor().blockNumber()
        if gline >= 0 and self.gline_to_cmd:
            idx = -1
            for g in range(gline, -1, -1):
                if g in self.gline_to_cmd:
                    idx = self.gline_to_cmd[g]
                    break
            if idx >= 0:
                return idx + 1
        return len(self.commands)

    def _on_pseudo_sel(self):
        if self._suspend or self._sync_busy:
            return
        row = self.pseudo_list.currentRow()
        if row >= 0 and self.cmd_to_glines:
            glines = self.cmd_to_glines.get(row, [])
            if glines:
                self._select_gline(glines[-1])
        if not self.auto_update_on_select:
            return
        self._schedule_preview()

    def _on_gcode_cur(self):
        if self._suspend or self._sync_busy:
            return
        gline = self.gcode_edit.textCursor().blockNumber()
        cmd_idx = -1
        if self.gline_to_cmd:
            for g in range(gline, -1, -1):
                if g in self.gline_to_cmd:
                    cmd_idx = self.gline_to_cmd[g]
                    break
        if 0 <= cmd_idx < self.pseudo_list.count():
            self._sync_busy = True
            try:
                self.pseudo_list.setCurrentRow(cmd_idx)
                it = self.pseudo_list.item(cmd_idx)
                if it is not None:
                    self.pseudo_list.scrollToItem(it)
            finally:
                QTimer.singleShot(0, self._reset_sync_busy)
        if not self.auto_update_on_select:
            return
        self._schedule_preview()

    def _reset_sync_busy(self):
        self._sync_busy = False

    def _select_gline(self, gline):
        try:
            doc = self.gcode_edit.document()
            block = doc.findBlockByNumber(gline)
            if not block.isValid():
                return
            self._sync_busy = True
            try:
                cur = QTextCursor(block)
                cur.movePosition(QTextCursor.StartOfBlock)
                cur.movePosition(QTextCursor.EndOfBlock,
                                 QTextCursor.KeepAnchor)
                self.gcode_edit.setTextCursor(cur)
                self.gcode_edit.centerCursor()
            finally:
                QTimer.singleShot(0, self._reset_sync_busy)
        except Exception:
            pass

    def _schedule_preview(self, force=False):
        self._preview_timer.start()

    def _start_generation(self):
        self._anim_timer.stop()
        self._anim_segs = []
        self._anim_idx = 0
        self.btn_status_cancel.setVisible(False)

        env, errs = build_env(self.variables)
        upto = self._current_upto()

        try:
            gen = GCodeGenerator(
                self.tools, env,
                unroll_loops=self.app_settings.unroll_loops,
                functions=self.app_settings.functions,
                preamble=self.app_settings.preamble,
                postamble=self.app_settings.postamble)
            self.code_lines = gen.generate(self.commands)
            self.gline_to_cmd = gen.gline_to_cmd
            self.cmd_to_glines = gen.cmd_to_glines
            cur_pseudo = self.pseudo_list.currentRow()
            self._suspend = True
            try:
                self.gcode_edit.setPlainText("\n".join(self.code_lines))
            finally:
                self._suspend = False
            if cur_pseudo >= 0 and cur_pseudo < self.pseudo_list.count():
                self._sync_busy = True
                try:
                    self.pseudo_list.setCurrentRow(cur_pseudo)
                finally:
                    QTimer.singleShot(0, self._reset_sync_busy)
            if gen.warnings:
                self.statusBar().showMessage(
                    "Предупреждения: " + "; ".join(gen.warnings[:3]), 5000)
        except Exception as e:
            self._update_status(f"Ошибка генератора: {e}")
            return

        self._update_status("Симуляция…")
        self.btn_status_cancel.setVisible(False)
        QApplication.processEvents()

        sim = Simulator(
            self.tools, env, stock=self.stock,
            settings=self.app_settings.sim,
            functions=self.app_settings.functions,
            preamble=self.app_settings.preamble,
            postamble=self.app_settings.postamble)
        try:
            segs, bounds, stats = sim.trace(
                self.commands, upto, stock=self.stock,
                check_collisions=True,
                ignore_rapid_in_material=self.app_settings.ignore_rapid_in_material,
                step_limit=self.app_settings.step_limit or None)
        except Exception as e:
            self._update_status(f"Ошибка симулятора: {e}")
            return

        self.last_segments = segs
        self.last_bounds = bounds
        self.last_stats = stats

        heightmap = stats.get("heightmap", None)
        self.viz.view3d.set_data(
            segs, bounds, self.stock, heightmap,
            settings=self.app_settings.sim,
            lights=self.app_settings.lights,
            lighting_mode=self.app_settings.lighting_mode,
            show_toolpath=self.app_settings.toolpath_visible,
            show_material=self.app_settings.material_visible)

        self._update_stats_label(upto, segs, stats, heightmap)
        self._highlight_collision_rows(stats.get("collisions", []))
        self._update_collision_log(stats.get("collisions", []))

        if self.anim_tool and segs:
            self._anim_segs = segs
            self._anim_idx = 0
            s = segs[0]
            self.viz.view3d.update_tool_position(
                s.x0, s.y0, s.z0, s.tool_d, s.tool_color)
            self._update_status("Анимация…")
            self.btn_status_cancel.setVisible(True)
            self._anim_timer.start()
        else:
            self._update_status("")

    def _anim_tick(self):
        if not self._anim_segs:
            self._anim_timer.stop()
            self._update_status("")
            self.btn_status_cancel.setVisible(False)
            return
        n = len(self._anim_segs)
        per_tick = max(1, n // 80)
        end = min(self._anim_idx + per_tick, n)
        for i in range(self._anim_idx, end):
            s = self._anim_segs[i]
            try:
                self.viz.view3d.update_tool_position(
                    s.x1, s.y1, s.z1, s.tool_d, s.tool_color)
            except Exception:
                pass
        self._anim_idx = end
        if self._anim_idx >= n:
            self._anim_timer.stop()
            self._update_status("")
            self.btn_status_cancel.setVisible(False)

    def _update_stats_label(self, upto, segs, stats, heightmap):
        t = sum(math.hypot(s.x1 - s.x0, s.y1 - s.y0) / 200.0
                for s in segs if not s.rapid)
        vol_str = (f"  Снято: {heightmap.removed_volume/1000:.2f}см³"
                   if heightmap else "")
        col_count = stats.get("collision_count", 0)
        col_str = f"  ⛔ КОЛЛИЗИЙ: {col_count}" if col_count else ""
        vox_str = ""
        if stats.get("voxel_xy"):
            vox_str = (f"  Вокс: {stats['voxel_xy']:.2f}×"
                       f"{stats['voxel_xy']:.2f}×{stats['voxel_z']:.2f}мм")
            if stats.get("voxel_limited"):
                vox_str += " ⚠"
        rot_str = ""
        if any(abs(stats.get(k, 0.0)) > 1e-6 for k in ("a", "b", "c")):
            rot_str = (f"  A={stats.get('a',0):.1f}° "
                       f"B={stats.get('b',0):.1f}° "
                       f"C={stats.get('c',0):.1f}°")
        self.stats_label.setStyleSheet(
            "color:#c00000;font-family:Consolas;font-weight:bold;"
            if col_count else
            "color:#444;font-family:Consolas;")
        self.stats_label.setText(
            f"Строк: {upto}/{len(self.commands)}  "
            f"Исполнено: {stats.get('executed_steps', 0)}  "
            f"Рез: {stats.get('cut_len', 0):.1f}мм  "
            f"Ускор: {stats.get('rapid_len', 0):.1f}мм  "
            f"Zmin: {stats.get('zmin', 0):.2f}  ~{t:.1f}мин"
            f"{vol_str}{col_str}{vox_str}{rot_str}")

    def open_code_library(self):
        d = CodeLibraryDialog(self,
            code_order=self.app_settings.code_order,
            code_hidden=self.app_settings.code_hidden,
            sort_mode=self.app_settings.code_sort_mode)
        if d.exec_() == QDialog.Accepted and d.result is not None:
            order, hidden, sort_mode = d.result
            self.app_settings.code_order = order
            self.app_settings.code_hidden = hidden
            self.app_settings.code_sort_mode = sort_mode
            self._save_global_settings()
            self.statusBar().showMessage("Список кодов обновлён", 2500)

    def open_function_library(self):
        dlg = FunctionLibraryDialog(
            self, self.app_settings.functions,
            on_insert=self._insert_call_from_library)
        if dlg.exec_() == QDialog.Accepted and dlg.result is not None:
            self.app_settings.functions = dlg.result
            self._schedule_preview(force=True)

    def _insert_call_from_library(self, fn):
        params = {"name": fn.name, "mode": "inline"}
        for prm in fn.params:
            raw = prm.default
            try:
                val = float(raw)
                params[f"p_{prm.name}"] = val
            except (TypeError, ValueError):
                params[f"p_{prm.name}"] = str(raw)
        cmd = Command("CALL_FUNC", params)
        pos = self.pseudo_list.currentRow()
        if pos < 0:
            self.commands.append(cmd)
            new_pos = len(self.commands) - 1
        else:
            self.commands.insert(pos + 1, cmd)
            new_pos = pos + 1
        self._refresh_pseudo()
        self.pseudo_list.setCurrentRow(new_pos)
        self._schedule_preview(force=True)
        self.statusBar().showMessage(
            f"Вставлен вызов {fn.name} (inline).", 4000)

    def load_functions_from_dir(self):
        funcs = file_io.load_functions_dir()
        if not funcs:
            QMessageBox.information(self, "Загрузка",
                f"Папка {file_io.functions_dir()} пуста.")
            return
        ans = QMessageBox.question(self, "Загрузка",
            f"Найдено {len(funcs)} функций. Заменить текущую библиотеку?",
            QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        self.app_settings.functions = funcs
        self._schedule_preview(force=True)
        self.statusBar().showMessage(
            f"Загружено {len(funcs)} функций из папки.", 3000)

    def save_functions_to_dir(self):
        try:
            file_io.save_functions_to_dir(file_io.functions_dir(),
                                          self.app_settings.functions)
            self.statusBar().showMessage(
                f"Сохранено {len(self.app_settings.functions)} функций.",
                3000)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def import_function_file(self):
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
        names = {f.name for f in self.app_settings.functions}
        if fn.name in names:
            ans = QMessageBox.question(self, "Импорт",
                f"Функция {fn.name} уже есть. Заменить?",
                QMessageBox.Yes | QMessageBox.No)
            if ans == QMessageBox.Yes:
                for i, f in enumerate(self.app_settings.functions):
                    if f.name == fn.name:
                        self.app_settings.functions[i] = fn
                        break
        else:
            self.app_settings.functions.append(fn)
        self._schedule_preview(force=True)
        self.statusBar().showMessage(f"Импортирована {fn.name}", 3000)

    def export_functions_all(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт всех функций", "functions_all.json",
            "Function bundle (*.json);;Все (*)")
        if not path:
            return
        try:
            import json
            data = {"version": 1, "functions": [
                file_io._func_to_dict(f) for f in self.app_settings.functions]}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.statusBar().showMessage("Экспортировано.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def open_settings_dialog(self):
        d = SimulationSettingsDialog(self, self.app_settings.sim)
        if d.exec_() == QDialog.Accepted and d.result is not None:
            self.app_settings.sim = d.result
            self.viz.set_widths(d.result.rapid_line_width,
                                d.result.feed_line_width)
            self.viz.view3d.set_settings(d.result)
            self.viz.view3d.refresh_scene()
            self._schedule_preview()

    def open_lighting_dialog(self):
        d = LightingDialog(self, self.app_settings.lights)
        if d.exec_() == QDialog.Accepted and d.result is not None:
            self.app_settings.lights = d.result
            self.viz.view3d.set_lights(d.result, mode="custom")
            self.app_settings.lighting_mode = "custom"

    def open_preamble_dialog(self):
        d = PreamblePostambleDialog(
            self, self.app_settings.preamble, self.app_settings.postamble)
        if d.exec_() == QDialog.Accepted and d.result is not None:
            self.app_settings.preamble, self.app_settings.postamble = d.result
            self._schedule_preview(force=True)

    def _refresh_tools(self):
        self.tool_table.setRowCount(len(self.tools))
        for i, t in enumerate(self.tools):
            for j, v in enumerate([str(t.number), t.name, f"{t.diameter:g}",
                                   f"{t.feed:g}", str(t.rpm)]):
                it = QTableWidgetItem(v)
                if j == 0:
                    it.setBackground(QColor(t.color))
                self.tool_table.setItem(i, j, it)

    def add_tool(self):
        d = ToolDialog(self)
        if d.exec_() == QDialog.Accepted:
            self.tools.append(d.get_tool())
            self._refresh_tools(); self._schedule_preview(force=True)

    def edit_tool(self):
        r = self.tool_table.currentRow()
        if r < 0:
            return
        d = ToolDialog(self, self.tools[r])
        if d.exec_() == QDialog.Accepted:
            self.tools[r] = d.get_tool()
            self._refresh_tools(); self._schedule_preview(force=True)

    def delete_tool(self):
        r = self.tool_table.currentRow()
        if r < 0:
            return
        if len(self.tools) == 1:
            QMessageBox.warning(self, "Ошибка",
                                "Нужен хотя бы один инструмент.")
            return
        del self.tools[r]
        self._refresh_tools(); self._schedule_preview(force=True)

    def _refresh_vars(self):
        self.var_table.setRowCount(len(self.variables))
        for i, v in enumerate(self.variables):
            it_name = QTableWidgetItem(v.name)
            it_val = QTableWidgetItem(str(v.value))
            it_val.setForeground(QBrush(QColor("#2a6099")))
            self.var_table.setItem(i, 0, it_name)
            self.var_table.setItem(i, 1, it_val)
        try:
            env, errs = build_env(self.variables)
            preview = ", ".join(f"{k}={v:g}" for k, v in list(env.items())[:14])
            if errs:
                preview += "  ⚠ " + "; ".join(errs[:2])
            self.var_preview.setText("= " + preview if preview else "")
        except Exception as e:
            self.var_preview.setText(f"Ошибка: {e}")

    def add_var(self):
        d = VarDialog(self, None, [v.name for v in self.variables])
        if d.exec_() == QDialog.Accepted:
            v = d.get_var()
            if v.name:
                self.variables.append(v)
                self._refresh_vars(); self._schedule_preview(force=True)

    def edit_var(self):
        r = self.var_table.currentRow()
        if r < 0:
            return
        d = VarDialog(self, self.variables[r],
                      [v.name for v in self.variables])
        if d.exec_() == QDialog.Accepted:
            self.variables[r] = d.get_var()
            self._refresh_vars(); self._schedule_preview(force=True)

    def delete_var(self):
        r = self.var_table.currentRow()
        if r < 0:
            return
        del self.variables[r]
        self._refresh_vars(); self._schedule_preview(force=True)

    def _refresh_pseudo(self):
        self._suspend = True
        self.pseudo_list.clear()
        for i, c in enumerate(self.commands):
            self.pseudo_list.addItem(c.to_pseudo(i))
        self._suspend = False

    def _new_command_picker(self, initial=None):
        env, _ = build_env(self.variables)
        return CommandPickerDialog(
            self, initial, env,
            functions=self.app_settings.functions,
            code_order=self.app_settings.code_order,
            code_hidden=self.app_settings.code_hidden,
            sort_mode=self.app_settings.code_sort_mode)

    def add_command(self):
        d = self._new_command_picker(None)
        if d.exec_() == QDialog.Accepted and d.result_command:
            pos = self.pseudo_list.currentRow()
            if pos < 0:
                self.commands.append(d.result_command)
                new_pos = len(self.commands) - 1
            else:
                self.commands.insert(pos + 1, d.result_command)
                new_pos = pos + 1
            self._refresh_pseudo()
            self.pseudo_list.setCurrentRow(new_pos)
            self._schedule_preview(force=True)

    def edit_command(self):
        r = self.pseudo_list.currentRow()
        if r < 0:
            return
        d = self._new_command_picker(self.commands[r])
        if d.exec_() == QDialog.Accepted and d.result_command:
            self.commands[r] = d.result_command
            self._refresh_pseudo()
            self.pseudo_list.setCurrentRow(r)
            self._schedule_preview(force=True)

    def delete_command(self):
        r = self.pseudo_list.currentRow()
        if r < 0:
            return
        del self.commands[r]
        self._refresh_pseudo()
        if self.commands:
            self.pseudo_list.setCurrentRow(
                min(r, len(self.commands) - 1))
        self._schedule_preview(force=True)

    def move_command(self, delta):
        r = self.pseudo_list.currentRow()
        if r < 0:
            return
        nr = r + delta
        if nr < 0 or nr >= len(self.commands):
            return
        self.commands[r], self.commands[nr] = \
            self.commands[nr], self.commands[r]
        self._refresh_pseudo()
        self.pseudo_list.setCurrentRow(nr)
        self._schedule_preview(force=True)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект", "project.gcp",
            "GCode Project (*.gcp *.json);;Все (*)")
        if not path:
            return
        v = self.viz.view3d
        view = {"azimuth": v.azimuth, "elevation": v.elevation,
                "zoom": 1.0, "distance": 200.0, "focal": 50.0,
                "ortho": v.ortho,
                "target": list(v._target),
                "shading": v.shading}
        try:
            file_io.save_project(path, self.tools, self.variables, self.stock,
                                 self.commands, view, self.app_settings)
            self.statusBar().showMessage("Проект сохранён", 2500)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "",
            "GCode Project (*.gcp *.json);;Все (*)")
        if not path:
            return
        try:
            (tools, variables, stock, commands,
             v_data, settings, raw) = file_io.load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.tools = tools or self.tools
        self.variables = variables
        self.stock = stock
        self.commands = commands
        self.app_settings = settings

        if v_data:
            v = self.viz.view3d
            v.azimuth = float(v_data.get("azimuth", -35))
            v.elevation = float(v_data.get("elevation", 35))
            v.ortho = bool(v_data.get("ortho", False))
            t = v_data.get("target")
            if t and len(t) == 3:
                v._target = tuple(float(x) for x in t)
            v.shading = v_data.get("shading", ShadingMode.SMOOTH)
            v._target_initialized = True

        self.viz.act_ignore_rapid.setChecked(
            self.app_settings.ignore_rapid_in_material)
        self.chk_unroll.setChecked(self.app_settings.unroll_loops)
        self.viz.set_visibility(self.app_settings.toolpath_visible,
                                self.app_settings.material_visible)
        self.viz.set_widths(self.app_settings.sim.rapid_line_width,
                            self.app_settings.sim.feed_line_width)
        self.slider_step.blockSignals(True)
        if self.app_settings.step_limit and 1 <= self.app_settings.step_limit < 300:
            self.slider_step.setValue(self.app_settings.step_limit)
            self.lbl_step.setText(str(self.app_settings.step_limit))
        else:
            self.slider_step.setValue(300)
            self.lbl_step.setText("все")
        self.slider_step.blockSignals(False)

        self._refresh_tools(); self._refresh_vars()
        self._refresh_pseudo(); self._schedule_preview(force=True)

    def export_tools_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт инструментов", "tools.csv",
            "CSV (*.csv);;Все (*)")
        if not path:
            return
        try:
            file_io.export_tools_csv(path, self.tools)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def import_tools_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт инструментов", "", "CSV (*.csv);;Все (*)")
        if not path:
            return
        try:
            tools = file_io.import_tools_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        if not tools:
            QMessageBox.warning(self, "Импорт", "Нет валидных строк.")
            return
        self.tools = tools
        self._refresh_tools(); self._schedule_preview(force=True)

    def edit_stock(self):
        d = StockDialog(self, self.stock)
        if d.exec_() == QDialog.Accepted:
            self.stock = d.result_stock
            self.viz.view3d.reset_target()
            self.viz.view3d.refresh_scene()
            self._schedule_preview(force=True)

    def export_gcode(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить G-код", "program.tap",
            "G-Code (*.tap *.nc *.gcode);;Все (*)")
        if not path:
            return
        try:
            file_io.export_gcode(path, self.code_lines)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def import_gcode(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт G-кода", "",
            "G-Code (*.tap *.nc *.gcode *.txt);;Все (*)")
        if not path:
            return
        try:
            text = file_io.read_text(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        cmds, warns = GCodeParser().parse(text)
        if not cmds:
            QMessageBox.warning(self, "Импорт", "Команды не найдены.")
            return
        msg = f"Найдено {len(cmds)} команд, предупреждений {len(warns)}.\n"
        if warns:
            msg += "\n".join(warns[:8])
            if len(warns) > 8:
                msg += "\n…"
        msg += "\n\nЗаменить текущий псевдокод?"
        ans = QMessageBox.question(
            self, "Импорт", msg,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if ans == QMessageBox.Cancel:
            return
        if ans == QMessageBox.Yes:
            self.commands = cmds
        else:
            self.commands.extend(cmds)
        self._refresh_pseudo(); self._schedule_preview(force=True)

    def copy_gcode(self):
        QApplication.clipboard().setText("\n".join(self.code_lines))
        self.statusBar().showMessage("G-код скопирован", 2500)

    def _highlight_collision_rows(self, collisions):
        for i in range(self.pseudo_list.count()):
            it = self.pseudo_list.item(i)
            it.setBackground(QBrush(Qt.transparent))
            it.setForeground(QBrush(QColor("#000000")))
            f = it.font(); f.setBold(False); it.setFont(f); it.setToolTip("")
        if not collisions:
            return
        bad = {}
        for c in collisions:
            bad.setdefault(c["cmd_index"], []).append(c["reason"])
        for idx, reasons in bad.items():
            if 0 <= idx < self.pseudo_list.count():
                it = self.pseudo_list.item(idx)
                it.setBackground(QBrush(QColor(255, 220, 220)))
                it.setForeground(QBrush(QColor(180, 0, 0)))
                f = it.font(); f.setBold(True); it.setFont(f)
                it.setToolTip("Коллизия: " + ", ".join(reasons))

    def _update_collision_log(self, collisions):
        self.collision_table.setRowCount(len(collisions))
        for i, c in enumerate(collisions):
            idx = c["cmd_index"]
            mnem = (self.commands[idx].mnemonic
                    if 0 <= idx < len(self.commands) else "FUNC")
            vals = [str(idx), mnem, f"{c['x']:.3f}", f"{c['y']:.3f}",
                    f"{c['z']:.3f} — {c['reason']}"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j == 4:
                    it.setForeground(QBrush(QColor(180, 0, 0)))
                it.setData(Qt.UserRole, idx)
                self.collision_table.setItem(i, j, it)

    def _on_collision_click(self):
        items = self.collision_table.selectedItems()
        if not items:
            return
        idx = items[0].data(Qt.UserRole)
        if idx is None or idx < 0:
            return
        if idx < self.pseudo_list.count():
            self.pseudo_list.setCurrentRow(idx)
            self.pseudo_list.scrollToItem(self.pseudo_list.item(idx))

    def load_sample(self):
        self.tools = [
            Tool(1, "End mill 3мм", 3.0, 200.0, 8000, "#3399ff"),
            Tool(2, "Drill 5мм", 5.0, 80.0, 4000, "#ffcc00"),
        ]
        self.variables = [
            UserVar("W", "60"), UserVar("L", "100"),
            UserVar("STEP", "5"), UserVar("PASS", "{W//STEP + 1}"),
            UserVar("DEPTH", "-1"),
        ]
        self.stock = Stock(mode="box", x=100, y=120, z=15,
                           px=0, py=0, pz=0, color="#7080b0", visible=True)
        self.commands = [
            Command("UNITS_MM", {}), Command("ABS", {}),
            Command("SPIN", {"on": 1, "rpm": 8000, "ccw": 0}),
            Command("TOOL", {"tool": 1}),
            Command("RAPID", {"x": 0, "y": 0, "z": 5}),
            Command("#", {}, "Фрезерование кармана"),
            Command("VAR", {"name": "#200", "value": "0"}),
            Command("LABEL", {"name": "LOOP"}),
            Command("RAPID", {"x": 0, "y": "{#200*STEP}", "z": 5}),
            Command("FEED", {"x": 0, "y": "{#200*STEP}",
                             "z": "{DEPTH}", "f": 150}),
            Command("FEED", {"x": "{L}", "y": "{#200*STEP}",
                             "z": "{DEPTH}", "f": 150}),
            Command("RAPID", {"x": "{L}", "y": "{#200*STEP}", "z": 5}),
            Command("VAR_ADD", {"name": "#200", "delta": "1"}),
            Command("IF", {"lhs": "#200", "op": "LT", "rhs": "{PASS}",
                           "target": "LOOP"}),
            Command("#", {}, "Сверление в центре"),
            Command("RAPID", {"x": "{W/2}", "y": "{L/2}", "z": 5}),
            Command("TOOL", {"tool": 2}),
            Command("DRILL", {"x": "{W/2}", "y": "{L/2}", "z": -8, "f": 60}),
            Command("RAPID", {"x": 0, "y": 0, "z": 5}),
            Command("END", {}),
        ]
        self.viz.view3d.reset_target()
        self._refresh_tools(); self._refresh_vars()
        self._refresh_pseudo(); self._schedule_preview(force=True)