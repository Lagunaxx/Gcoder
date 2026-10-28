# -*- coding: utf-8 -*-
"""Панель визуализации: компактный тулбар + 3D-вид."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QButtonGroup, QLabel, QSlider, QToolButton, QMenu, QAction,
    QActionGroup, QSizePolicy, QFrame,
)

from gcode_editor.core.constants import ShadingMode, LightingMode
from gcode_editor.ui.view_3d import View3D


class VizPanel(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        # ---------------- верхний тулбар ----------------
        bar_widget = QWidget(self)
        bar = QHBoxLayout(bar_widget)
        bar.setContentsMargins(2, 2, 2, 2)
        bar.setSpacing(2)
        bar_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        v.addWidget(bar_widget)

        # --- Меню "Отображение" ---
        self.btn_disp = self._make_menu_button("Отображение",
            "Что показывать в 3D")
        self.menu_disp = QMenu(self.btn_disp)
        self.act_toolpath = QAction("Траектория", self)
        self.act_toolpath.setCheckable(True)
        self.act_toolpath.setChecked(True)
        self.act_material = QAction("Материал", self)
        self.act_material.setCheckable(True)
        self.act_material.setChecked(False)
        self.menu_disp.addAction(self.act_toolpath)
        self.menu_disp.addAction(self.act_material)
        self.btn_disp.setMenu(self.menu_disp)
        bar.addWidget(self.btn_disp)

        # --- Меню "Шейдинг" ---
        self.btn_shading = self._make_menu_button("Шейдинг",
            "Режим отрисовки поверхностей")
        self.menu_shading = QMenu(self.btn_shading)
        self.act_sh_wire = QAction("Каркас", self, checkable=True)
        self.act_sh_transp = QAction("Полупрозрачный", self, checkable=True)
        self.act_sh_flat = QAction("Плоскости", self, checkable=True)
        self.act_sh_smooth = QAction("Сглаживание", self, checkable=True)
        self.act_sh_smooth.setChecked(True)
        grp = QActionGroup(self)
        for a in (self.act_sh_wire, self.act_sh_transp,
                  self.act_sh_flat, self.act_sh_smooth):
            a.setActionGroup(grp)
            self.menu_shading.addAction(a)
        self.act_sh_wire.triggered.connect(
            lambda: self._set_mode(ShadingMode.WIREFRAME))
        self.act_sh_transp.triggered.connect(
            lambda: self._set_mode(ShadingMode.TRANSPARENT))
        self.act_sh_flat.triggered.connect(
            lambda: self._set_mode(ShadingMode.FLAT))
        self.act_sh_smooth.triggered.connect(
            lambda: self._set_mode(ShadingMode.SMOOTH))
        self.btn_shading.setMenu(self.menu_shading)
        bar.addWidget(self.btn_shading)

        # --- Меню "Линии" ---
        self.btn_toolpath_opts = self._make_menu_button("Линии",
            "Толщина линий траектории")
        self.menu_toolpath = QMenu(self.btn_toolpath_opts)
        self.act_rapid_w = QAction("Толщина RAPID…", self)
        self.act_rapid_w.triggered.connect(self._edit_rapid_width)
        self.act_feed_w = QAction("Толщина FEED…", self)
        self.act_feed_w.triggered.connect(self._edit_feed_width)
        self.menu_toolpath.addAction(self.act_rapid_w)
        self.menu_toolpath.addAction(self.act_feed_w)
        self.menu_toolpath.addSeparator()
        self.act_ignore_rapid = QAction("Игнорировать RAPID в материале", self)
        self.act_ignore_rapid.setCheckable(True)
        self.menu_toolpath.addAction(self.act_ignore_rapid)
        self.btn_toolpath_opts.setMenu(self.menu_toolpath)
        bar.addWidget(self.btn_toolpath_opts)

        # --- Меню "Проекция" ---
        self.btn_proj = self._make_menu_button("Проекция",
            "Перспектива / ортография")
        self.menu_proj = QMenu(self.btn_proj)
        self.act_persp = QAction("Перспектива", self, checkable=True)
        self.act_persp.setChecked(True)
        self.act_ortho = QAction("Ортография", self, checkable=True)
        grp2 = QActionGroup(self)
        self.act_persp.setActionGroup(grp2)
        self.act_ortho.setActionGroup(grp2)
        self.act_persp.triggered.connect(lambda: self._set_projection("persp"))
        self.act_ortho.triggered.connect(lambda: self._set_projection("ortho"))
        self.menu_proj.addAction(self.act_persp)
        self.menu_proj.addAction(self.act_ortho)
        self.btn_proj.setMenu(self.menu_proj)
        bar.addWidget(self.btn_proj)

        # --- Меню "Ракурс" ---
        self.btn_view = self._make_menu_button("Ракурс",
            "Быстрые ракурсы и подгонка")
        self.menu_view = QMenu(self.btn_view)
        self.act_v_top = QAction("Сверху", self)
        self.act_v_top.triggered.connect(lambda: self._set_view("top"))
        self.act_v_front = QAction("Спереди", self)
        self.act_v_front.triggered.connect(lambda: self._set_view("front"))
        self.act_v_iso = QAction("Изометрия", self)
        self.act_v_iso.triggered.connect(lambda: self._set_view("iso"))
        self.menu_view.addAction(self.act_v_top)
        self.menu_view.addAction(self.act_v_front)
        self.menu_view.addAction(self.act_v_iso)
        self.menu_view.addSeparator()
        self.act_fit = QAction("Подогнать под экран (Fit)", self)
        self.act_fit.triggered.connect(lambda: self.view3d.fit())
        self.menu_view.addAction(self.act_fit)
        self.btn_view.setMenu(self.menu_view)
        bar.addWidget(self.btn_view)

        # --- Меню "Освещение" ---
        self.btn_lighting = self._make_menu_button("Освещение",
            "Настройка источников света")
        self.menu_lighting = QMenu(self.btn_lighting)
        self.act_light_edit = QAction("Настроить источники…", self)
        self.menu_lighting.addAction(self.act_light_edit)
        self.btn_lighting.setMenu(self.menu_lighting)
        bar.addWidget(self.btn_lighting)
        self.on_lighting_clicked = None
        self.act_light_edit.triggered.connect(
            lambda: self.on_lighting_clicked()
            if callable(self.on_lighting_clicked) else None)

        # --- Меню "Настройки" ---
        self.btn_settings = self._make_menu_button("Настройки",
            "Параметры симуляции")
        self.menu_settings = QMenu(self.btn_settings)
        self.act_sim_settings = QAction("Параметры симуляции…", self)
        self.menu_settings.addAction(self.act_sim_settings)
        self.btn_settings.setMenu(self.menu_settings)
        bar.addWidget(self.btn_settings)
        self.on_settings_clicked = None
        self.act_sim_settings.triggered.connect(
            lambda: self.on_settings_clicked()
            if callable(self.on_settings_clicked) else None)

        bar.addStretch(1)

        # --- Прозрачность (компактно) ---
        bar.addWidget(QLabel("Прозр.:"))
        self.slider_transparency = QSlider(Qt.Horizontal)
        self.slider_transparency.setRange(15, 100)
        self.slider_transparency.setValue(30)
        self.slider_transparency.setFixedWidth(100)
        self.slider_transparency.setFixedHeight(20)
        self.slider_transparency.valueChanged.connect(self._on_transparency)
        bar.addWidget(self.slider_transparency)
        self.lbl_transp = QLabel("30%")
        self.lbl_transp.setFixedWidth(34)
        bar.addWidget(self.lbl_transp)

        # --- Кнопка отстегивания/пристегивания ---
        self.btn_dock_float = QToolButton(self)
        self.btn_dock_float.setText("📌")
        self.btn_dock_float.setToolTip("Отстыковать / пристыковать панель")
        self.btn_dock_float.setFixedSize(24, 24)
        self.btn_dock_float.setStyleSheet(
            "QToolButton{background:#2a2a33;color:#ddd;border:1px solid #444;"
            "border-radius:3px;font-size:13px;padding:0;}"
            "QToolButton:hover{background:#3a3a45;}")
        self.btn_dock_float.clicked.connect(self._on_float_click)
        bar.addWidget(self.btn_dock_float)
        self.on_float_toggle = None

        # ---------------- 3D ----------------
        self.view3d = View3D()
        v.addWidget(self.view3d, 1)

        # ---------------- сигналы ----------------
        self.act_toolpath.toggled.connect(
            lambda s: self.view3d.set_show_toolpath(bool(s)))
        self.act_material.toggled.connect(
            lambda s: self.view3d.set_show_material(bool(s)))

        self.on_toolpath_changed = None
        self.on_material_changed = None
        self.on_widths_changed = None
        self.on_ignore_rapid_changed = None

        self.act_toolpath.toggled.connect(
            lambda s: self.on_toolpath_changed(bool(s))
            if callable(self.on_toolpath_changed) else None)
        self.act_material.toggled.connect(
            lambda s: self.on_material_changed(bool(s))
            if callable(self.on_material_changed) else None)
        self.act_ignore_rapid.toggled.connect(
            lambda s: self.on_ignore_rapid_changed(bool(s))
            if callable(self.on_ignore_rapid_changed) else None)

        # совместимость со старым кодом main_window
        self.chk_ignore_rapid = self.act_ignore_rapid

    # ---------- helpers ----------
    def _make_menu_button(self, text, tip):
        b = QToolButton(self)
        b.setText(text)
        b.setToolTip(tip)
        b.setPopupMode(QToolButton.InstantPopup)
        b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        b.setFixedHeight(24)
        b.setStyleSheet(
            "QToolButton{background:#2a2a33;color:#ddd;border:1px solid #444;"
            "border-radius:3px;padding:2px 8px;}"
            "QToolButton:hover{background:#3a3a45;}"
            "QToolButton::menu-indicator{image:none;}")
        return b

    # ---------- slots ----------
    def _set_mode(self, mode):
        self.view3d.set_shading(mode)

    def _set_view(self, name):
        {"top": self.view3d.set_top,
         "bottom": self.view3d.set_bottom,
         "front": self.view3d.set_front,
         "back": self.view3d.set_back,
         "left": self.view3d.set_left,
         "right": self.view3d.set_right,
         "iso": self.view3d.set_iso}[name]()

    def _set_projection(self, mode):
        self.view3d.set_ortho(mode == "ortho")

    def _on_transparency(self, value):
        self.view3d.set_transparency(value)
        self.lbl_transp.setText(f"{value}%")

    def _edit_rapid_width(self):
        from PyQt5.QtWidgets import QInputDialog
        v, ok = QInputDialog.getDouble(
            self, "Толщина RAPID",
            "Толщина линии RAPID (0.5–12):",
            float(self.view3d.settings.rapid_line_width),
            0.5, 12.0, 1)
        if ok:
            self.view3d.settings.rapid_line_width = v
            self.view3d.refresh_scene()
            if callable(self.on_widths_changed):
                self.on_widths_changed(
                    v, float(self.view3d.settings.feed_line_width))

    def _edit_feed_width(self):
        from PyQt5.QtWidgets import QInputDialog
        v, ok = QInputDialog.getDouble(
            self, "Толщина FEED",
            "Толщина линии FEED (0.5–12):",
            float(self.view3d.settings.feed_line_width),
            0.5, 12.0, 1)
        if ok:
            self.view3d.settings.feed_line_width = v
            self.view3d.refresh_scene()
            if callable(self.on_widths_changed):
                self.on_widths_changed(
                    float(self.view3d.settings.rapid_line_width), v)

    def _on_float_click(self):
        if callable(self.on_float_toggle):
            self.on_float_toggle()

    # ---------- публичное API ----------
    def set_widths(self, rapid_w, feed_w):
        self.view3d.settings.rapid_line_width = float(rapid_w)
        self.view3d.settings.feed_line_width = float(feed_w)

    def set_visibility(self, toolpath: bool, material: bool):
        self.act_toolpath.blockSignals(True)
        self.act_material.blockSignals(True)
        self.act_toolpath.setChecked(bool(toolpath))
        self.act_material.setChecked(bool(material))
        self.act_toolpath.blockSignals(False)
        self.act_material.blockSignals(False)

    def set_data(self, segments, bounds, stock=None, heightmap=None,
                 settings=None, lights=None, lighting_mode=None,
                 show_toolpath=None, show_material=None):
        self.view3d.set_data(
            segments, bounds, stock, heightmap,
            settings=settings, lights=lights,
            lighting_mode=lighting_mode,
            show_toolpath=show_toolpath,
            show_material=show_material)