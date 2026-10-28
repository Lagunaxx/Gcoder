# -*- coding: utf-8 -*-
"""3D-вид на PyVista: траектория, материал из HeightMap, освещение, ViewCube."""

import math
from typing import Optional, List

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor

from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from gcode_editor.core.constants import ShadingMode, LightKind
from gcode_editor.core.models import SimSettings, LightingSource, default_lights
from gcode_editor.ui.view_cube import ViewCube


class View3D(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(self)
        self._layout.addWidget(self.plotter.interactor)

        self.plotter.set_background("#101014", top="#181820")
        try:
            self.plotter.enable_anti_aliasing("ssaa")
        except Exception:
            pass

        self.segments = []
        self.bounds = (-10, -10, 10, 10)
        self.stock = None
        self.heightmap = None

        self.settings = SimSettings()
        self.lights: List[LightingSource] = default_lights()
        self.lighting_mode = "headlight"

        self.show_toolpath = True
        self.show_material = False

        self.azimuth = -35.0
        self.elevation = 35.0
        self.ortho = False
        self._target = (0.0, 0.0, 0.0)
        self._target_initialized = False
        self._fit_after_show = False

        self.shading = ShadingMode.SMOOTH
        self.transparency = 30.0

        self._actors = {}
        self._material_mesh_cache = None
        self._material_cache_key_val = None
        self._first_render_done = False
        self._resizing = False

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(10)
        self._render_timer.timeout.connect(self._safe_render)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self._on_resize_done)

        self.view_cube = ViewCube(self)
        self.view_cube.view_requested.connect(self.animate_to)
        self.view_cube.raise_()

        try:
            self.plotter.camera.AddObserver(
                "ModifiedEvent", self._on_camera_modified)
        except Exception:
            pass

    def set_data(self, segments, bounds, stock=None, heightmap=None,
                 settings: Optional[SimSettings] = None,
                 lights: Optional[List[LightingSource]] = None,
                 lighting_mode: Optional[str] = None,
                 show_toolpath: Optional[bool] = None,
                 show_material: Optional[bool] = None):
        self.segments = segments
        self.bounds = bounds
        self.stock = stock
        self.heightmap = heightmap

        if settings is not None:
            self.settings = settings
        if lights is not None:
            self.lights = lights
        if lighting_mode is not None:
            self.lighting_mode = lighting_mode
        if show_toolpath is not None:
            self.show_toolpath = bool(show_toolpath)
        if show_material is not None:
            self.show_material = bool(show_material)

        if not self._target_initialized:
            if stock is not None:
                bx0, by0, bx1, by1, z_top, z_bot = stock.bounds()
                self._target = ((bx0 + bx1) / 2, (by0 + by1) / 2,
                                (z_top + z_bot) / 2)
            else:
                minx, miny, maxx, maxy = bounds
                self._target = ((minx + maxx) / 2, (miny + maxy) / 2, 0.0)
            self._target_initialized = True
            self._fit_after_show = True

        self._rebuild_scene()
        if self._fit_after_show:
            QTimer.singleShot(60, self._do_initial_fit)

    def _do_initial_fit(self):
        self._fit_after_show = False
        self.fit()

    def update_tool_position(self, x, y, z, tool_d, tool_color):
        try:
            old = self._actors.get("tool")
            if old is not None:
                try:
                    self.plotter.remove_actor(old)
                except Exception:
                    pass
            r = max(0.1, float(tool_d) / 2.0)
            tool = pv.Cylinder(center=(x, y, z + 4.0),
                               direction=(0, 0, 1),
                               radius=r, height=8.0, resolution=24)
            actor = self.plotter.add_mesh(
                tool, color=tool_color or "#ffd166",
                lighting=True, name="tool", reset_camera=False)
            self._actors["tool"] = actor
            self._schedule_render()
        except Exception as e:
            print(f"[View3D] update_tool error: {e}")

    def reset_target(self):
        self._target_initialized = False
        self.azimuth = -35.0
        self.elevation = 35.0

    def set_top(self):    self.animate_to(0.0, 89.9)
    def set_bottom(self): self.animate_to(0.0, -89.9)
    def set_front(self):  self.animate_to(0.0, 0.0)
    def set_back(self):   self.animate_to(180.0, 0.0)
    def set_left(self):   self.animate_to(-90.0, 0.0)
    def set_right(self):  self.animate_to(90.0, 0.0)
    def set_iso(self):    self.animate_to(-35.0, 35.0)

    def animate_to(self, az, el):
        self.azimuth = az
        self.elevation = el
        self._apply_camera()
        self.view_cube.set_camera_angles(az, el)
        self._schedule_render()

    def reset_view(self):
        self._target_initialized = False
        self.set_data(self.segments, self.bounds, self.stock, self.heightmap)
        self.animate_to(-35.0, 35.0)

    def fit(self):
        """Подогнать камеру так, чтобы всё содержимое влезло в видимую область."""
        try:
            self.plotter.reset_camera()
        except Exception:
            pass
        # сохраняем наш ракурс
        self._apply_camera()
        self._schedule_render()

    def set_shading(self, mode):
        self.shading = mode
        self._apply_state()

    def set_show_toolpath(self, val):
        self.show_toolpath = bool(val)
        self._rebuild_scene()

    def set_show_material(self, val):
        self.show_material = bool(val)
        self._material_mesh_cache = None
        self._material_cache_key_val = None
        self._rebuild_scene()

    def set_transparency(self, value):
        self.transparency = float(value)
        if self.shading == ShadingMode.TRANSPARENT:
            self._apply_state()

    def set_ortho(self, ortho: bool):
        self.ortho = bool(ortho)
        try:
            self.plotter.camera.parallel_projection = bool(ortho)
        except Exception:
            pass
        self._schedule_render()

    def set_lights(self, lights, mode=None):
        self.lights = lights
        if mode is not None:
            self.lighting_mode = mode
        self._apply_lights()
        self._safe_render()

    def set_settings(self, settings: SimSettings):
        self.settings = settings
        self._material_mesh_cache = None
        self._material_cache_key_val = None
        self._apply_state()

    def refresh_scene(self):
        self._material_mesh_cache = None
        self._material_cache_key_val = None
        self._rebuild_scene()

    def _apply_lights(self):
        try:
            self.plotter.remove_all_lights()
        except Exception:
            pass

        enabled = [l for l in self.lights if l.enabled]
        if self.lighting_mode == "headlight":
            self._add_light(kind=LightKind.HEADLIGHT, intensity=1.0,
                            color="#ffffff")
            self._add_light(kind=LightKind.CAMERA, intensity=0.35,
                            color="#e8eeff")
            return
        if not enabled:
            self._add_light(kind=LightKind.HEADLIGHT, intensity=1.0,
                            color="#ffffff")
            return
        for l in enabled:
            self._add_light(kind=l.kind, intensity=l.intensity,
                            color=l.color, position=l.position,
                            focal_point=l.focal_point,
                            light_type=l.light_type,
                            cone_angle=l.cone_angle)

    def _add_light(self, kind, intensity, color,
                   position=(0, 0, 1), focal_point=(0, 0, 0),
                   light_type="sphere", cone_angle=30.0):
        try:
            if kind == LightKind.HEADLIGHT:
                light = pv.Light(light_type="headlight")
            elif kind == LightKind.CAMERA:
                light = pv.Light(light_type="camera light")
            else:
                light = pv.Light(position=position,
                                 focal_point=focal_point)
                if light_type == "directional":
                    light.light_type = "directional"
                elif light_type == "spot":
                    light.light_type = "spot"
                    light.cone_angle = float(cone_angle)
                else:
                    light.light_type = "scene light"
            light.intensity = float(intensity)
            try:
                c = QColor(color)
                light.color = (c.redF(), c.greenF(), c.blueF())
            except Exception:
                pass
            self.plotter.add_light(light)
        except Exception as e:
            print(f"[View3D] add_light error: {e}")

    def _apply_state(self):
        if not self._actors:
            self._safe_render()
            return

        wire = (self.shading == ShadingMode.WIREFRAME)
        transparent = (self.shading == ShadingMode.TRANSPARENT)
        flat = (self.shading == ShadingMode.FLAT)
        smooth = (self.shading == ShadingMode.SMOOTH)
        opacity = 1.0 if not transparent \
            else max(0.15, min(1.0, self.transparency / 100.0))

        for name, actor in self._actors.items():
            if actor is None:
                continue
            is_toolpath = name.startswith("toolpath_")
            try:
                prop = actor.GetProperty()
                if wire and not is_toolpath:
                    prop.SetRepresentationToWireframe()
                    prop.SetLineWidth(2.0)
                    prop.SetEdgeVisibility(True)
                    prop.SetOpacity(1.0)
                else:
                    prop.SetRepresentationToSurface()
                    if not is_toolpath:
                        prop.SetLineWidth(1.0)
                        prop.SetEdgeVisibility(False)
                        prop.SetOpacity(opacity)
                    else:
                        prop.SetOpacity(1.0)
                if not is_toolpath:
                    if flat:
                        prop.SetInterpolationToFlat()
                    elif smooth:
                        prop.SetInterpolationToGouraud()
                prop.Modified()
                actor.Modified()
            except Exception as e:
                print(f"[View3D] apply error {name}: {e}")

        try:
            if transparent:
                self.plotter.enable_depth_peeling(number_of_peels=4)
            else:
                self.plotter.disable_depth_peeling()
        except Exception:
            pass

        try:
            self.plotter.renderer.Modified()
        except Exception:
            pass
        self._safe_render()

    def _on_camera_modified(self, *args):
        try:
            cam = self.plotter.camera
            fp = cam.focal_point
            pos = cam.position
            if fp is not None:
                self._target = (float(fp[0]), float(fp[1]), float(fp[2]))
            if pos is not None:
                dx = pos[0] - self._target[0]
                dy = pos[1] - self._target[1]
                dz = pos[2] - self._target[2]
                horiz = math.hypot(dx, dy)
                self.azimuth = math.degrees(math.atan2(dx, dy))
                self.elevation = math.degrees(math.atan2(dz, horiz))
                self.view_cube.set_camera_angles(
                    self.azimuth, self.elevation)
        except Exception:
            pass

    def _rebuild_scene(self):
        try:
            self.plotter.clear()
        except Exception:
            pass
        self._actors = {}

        if self.show_material and self.stock is not None:
            self._build_material_actor()
        elif self.stock is not None and self.stock.visible:
            self._build_stock_actor()

        if self.show_toolpath:
            self._build_toolpath_scene()

        self._build_tool_actor()
        self._build_axes_actor()
        self._apply_lights()

        self.view_cube.set_camera_angles(self.azimuth, self.elevation)
        self.view_cube.raise_()

        self._apply_state()

    def _build_stock_actor(self):
        S = self.stock
        if S is None or not S.visible:
            return
        mesh = self._stock_mesh()
        if mesh is None:
            return
        c = QColor(S.color)
        color = (c.redF(), c.greenF(), c.blueF())
        self._actors["stock"] = self.plotter.add_mesh(
            mesh, color=color, show_edges=True, edge_color="gray",
            lighting=True, name="stock", reset_camera=False)

    def _stock_mesh(self):
        S = self.stock
        if S is None:
            return None
        bx0, by0, bx1, by1, z_top, z_bot = S.bounds()
        cube = pv.Cube(bounds=(bx0, bx1, by0, by1, z_bot, z_top))
        return cube.triangulate()

    def _material_cache_key(self):
        if self.heightmap is None:
            return None
        return (id(self.heightmap),
                self.heightmap.nx, self.heightmap.ny,
                self.heightmap.z_bottom)

    def _build_material_actor(self):
        S = self.stock
        if S is None:
            return
        if self.heightmap is None:
            self._build_stock_actor()
            return

        key = self._material_cache_key()
        if self._material_mesh_cache is None or self._material_cache_key_val != key:
            self._material_mesh_cache = self._build_mesh_from_heightmap()
            self._material_cache_key_val = key

        if self._material_mesh_cache is None:
            self._build_stock_actor()
            return

        c = QColor(S.color)
        color = (c.redF(), c.greenF(), c.blueF())
        self._actors["material"] = self.plotter.add_mesh(
            self._material_mesh_cache, color=color, show_edges=False,
            lighting=True, name="material", reset_camera=False)

    def _build_mesh_from_heightmap(self):
        hm = self.heightmap
        S = self.stock
        if hm is None or S is None:
            return None

        nx, ny = hm.nx, hm.ny
        if nx <= 0 or ny <= 0:
            return None

        bx0, by0, bx1, by1, z_top, z_bot = S.bounds()
        x_min = bx0
        y_min = by0
        dx = (bx1 - bx0) / nx
        dy = (by1 - by0) / ny

        try:
            Z = np.array(hm.cur_z, dtype=np.float64)
            if Z.shape != (nx, ny):
                return None
        except Exception as e:
            print(f"[View3D] heightmap to array error: {e}")
            return None

        verts = []
        faces = []

        def add_quad(p0, p1, p2, p3):
            base = len(verts) // 3
            verts.extend([p0[0], p0[1], p0[2],
                          p1[0], p1[1], p1[2],
                          p2[0], p2[1], p2[2],
                          p3[0], p3[1], p3[2]])
            faces.extend([4, base, base + 1, base + 2, base + 3])

        for i in range(nx):
            x0 = x_min + i * dx
            x1 = x0 + dx
            for j in range(ny):
                y0 = y_min + j * dy
                y1 = y0 + dy
                z = Z[i, j]
                add_quad(
                    (x0, y0, z), (x1, y0, z),
                    (x1, y1, z), (x0, y1, z))

        for i in range(nx - 1):
            x_mid = x_min + (i + 1) * dx
            for j in range(ny):
                y0 = y_min + j * dy
                y1 = y0 + dy
                za = Z[i, j]
                zb = Z[i + 1, j]
                if zb < za - 1e-9:
                    add_quad(
                        (x_mid, y0, zb), (x_mid, y1, zb),
                        (x_mid, y1, za), (x_mid, y0, za))
                elif za < zb - 1e-9:
                    add_quad(
                        (x_mid, y0, za), (x_mid, y1, za),
                        (x_mid, y1, zb), (x_mid, y0, zb))

        for j in range(ny - 1):
            y_mid = y_min + (j + 1) * dy
            for i in range(nx):
                x0 = x_min + i * dx
                x1 = x0 + dx
                za = Z[i, j]
                zb = Z[i, j + 1]
                if zb < za - 1e-9:
                    add_quad(
                        (x0, y_mid, zb), (x1, y_mid, zb),
                        (x1, y_mid, za), (x0, y_mid, za))
                elif za < zb - 1e-9:
                    add_quad(
                        (x0, y_mid, za), (x1, y_mid, za),
                        (x1, y_mid, zb), (x0, y_mid, zb))

        for j in range(ny):
            y0 = y_min + j * dy
            y1 = y0 + dy
            z = Z[0, j]
            if z > z_bot + 1e-9:
                add_quad(
                    (x_min, y0, z_bot), (x_min, y1, z_bot),
                    (x_min, y1, z), (x_min, y0, z))
        x_right = x_min + nx * dx
        for j in range(ny):
            y0 = y_min + j * dy
            y1 = y0 + dy
            z = Z[nx - 1, j]
            if z > z_bot + 1e-9:
                add_quad(
                    (x_right, y0, z), (x_right, y1, z),
                    (x_right, y1, z_bot), (x_right, y0, z_bot))
        for i in range(nx):
            x0 = x_min + i * dx
            x1 = x0 + dx
            z = Z[i, 0]
            if z > z_bot + 1e-9:
                add_quad(
                    (x0, y_min, z), (x1, y_min, z),
                    (x1, y_min, z_bot), (x0, y_min, z_bot))
        y_back = y_min + ny * dy
        for i in range(nx):
            x0 = x_min + i * dx
            x1 = x0 + dx
            z = Z[i, ny - 1]
            if z > z_bot + 1e-9:
                add_quad(
                    (x0, y_back, z_bot), (x1, y_back, z_bot),
                    (x1, y_back, z), (x0, y_back, z))

        add_quad(
            (x_min, y_min, z_bot), (x_min + nx * dx, y_min, z_bot),
            (x_min + nx * dx, y_min + ny * dy, z_bot),
            (x_min, y_min + ny * dy, z_bot))

        if not verts:
            return None

        points = np.array(verts, dtype=np.float64).reshape(-1, 3)
        faces_arr = np.array(faces, dtype=np.int64)
        try:
            poly = pv.PolyData(points, faces_arr)
        except Exception:
            poly = pv.PolyData()
            poly.points = points
            poly.faces = faces_arr
        try:
            poly = poly.triangulate().clean()
        except Exception:
            pass
        return poly

    def _build_toolpath_scene(self):
        if not self.segments:
            return
        groups = {}
        for s in self.segments:
            key = (s.tool_color, bool(s.rapid))
            groups.setdefault(key, []).append(s)

        rapid_w = max(0.5, float(self.settings.rapid_line_width))
        feed_w = max(0.5, float(self.settings.feed_line_width))
        dash = bool(self.settings.rapid_dash)

        for (color, rapid), segs in groups.items():
            if rapid and dash:
                segments_pts = self._dashed_points(segs, dash_len=2.0, gap_len=1.5)
            else:
                segments_pts = []
                for s in segs:
                    if s.arc:
                        segments_pts.extend(self._arc_to_polyline(s))
                    else:
                        segments_pts.append(
                            [(s.x0, s.y0, s.z0), (s.x1, s.y1, s.z1)])
            if not segments_pts:
                continue
            pts = []
            lines = []
            for seg_pts in segments_pts:
                for p in seg_pts:
                    pts.append(p)
                i0 = len(pts) - len(seg_pts)
                for k in range(len(seg_pts) - 1):
                    lines.extend([2, i0 + k, i0 + k + 1])
            if not lines:
                continue
            poly = pv.PolyData()
            poly.points = np.array(pts, dtype=np.float32)
            poly.lines = np.array(lines, dtype=np.int64)
            actor_name = f"toolpath_{'rapid' if rapid else 'feed'}_{color[1:]}"
            try:
                actor = self.plotter.add_mesh(
                    poly, color=color,
                    line_width=(rapid_w if rapid else feed_w),
                    style="wireframe",
                    name=actor_name,
                    render_lines_as_tubes=False,
                    reset_camera=False)
                self._actors[actor_name] = actor
            except Exception as e:
                print(f"[View3D] toolpath add error: {e}")

    def _arc_to_polyline(self, s, max_step_deg=5.0):
        r = math.hypot(s.x0 - s.cx, s.y0 - s.cy)
        if r < 1e-9:
            return [[(s.x0, s.y0, s.z0), (s.x1, s.y1, s.z1)]]
        a0 = math.atan2(s.y0 - s.cy, s.x0 - s.cx)
        a1 = math.atan2(s.y1 - s.cy, s.x1 - s.cx)
        da = a1 - a0
        if s.cw:
            while da > 0: da -= 2 * math.pi
            while da <= -2 * math.pi: da += 2 * math.pi
        else:
            while da < 0: da += 2 * math.pi
            while da >= 2 * math.pi: da -= 2 * math.pi
        if abs(da) < 1e-9:
            da = -2 * math.pi if s.cw else 2 * math.pi
        step = math.radians(max(1.0, float(max_step_deg)))
        n = max(2, int(abs(da) / step) + 1)
        pts = []
        for i in range(n + 1):
            t = i / n
            a = a0 + da * t
            z = s.z0 + (s.z1 - s.z0) * t
            pts.append((s.cx + r * math.cos(a),
                        s.cy + r * math.sin(a), z))
        return [pts]

    def _point_at(self, polyline, seg_lens, distance):
        acc = 0.0
        for k, L in enumerate(seg_lens):
            if acc + L >= distance - 1e-9:
                t = (distance - acc) / L if L > 1e-9 else 0.0
                p0 = polyline[k]
                p1 = polyline[k + 1]
                return (p0[0] + (p1[0] - p0[0]) * t,
                        p0[1] + (p1[1] - p0[1]) * t,
                        p0[2] + (p1[2] - p0[2]) * t)
            acc += L
        return polyline[-1]

    def _dashed_points(self, segs, dash_len=2.0, gap_len=1.5):
        result = []
        for s in segs:
            if s.arc:
                polyline = self._arc_to_polyline(s)[0]
                total = 0.0
                seg_lens = []
                for k in range(len(polyline) - 1):
                    dx = polyline[k+1][0] - polyline[k][0]
                    dy = polyline[k+1][1] - polyline[k][1]
                    dz = polyline[k+1][2] - polyline[k][2]
                    L = math.sqrt(dx*dx + dy*dy + dz*dz)
                    seg_lens.append(L)
                    total += L
                if total <= 1e-6:
                    continue
                n = max(1, int(total / (dash_len + gap_len)))
                step = total / n
                for i in range(n):
                    t0 = i * step
                    t1 = min(i * step + dash_len, total)
                    p0 = self._point_at(polyline, seg_lens, t0)
                    p1 = self._point_at(polyline, seg_lens, t1)
                    if p0 and p1:
                        result.append([p0, p1])
            else:
                L = math.hypot(s.x1 - s.x0, s.y1 - s.y0)
                if L <= 1e-6:
                    continue
                n = max(1, int(L / (dash_len + gap_len)))
                step = L / n
                for i in range(n):
                    t0 = i * step / L
                    t1 = min((i * step + dash_len) / L, 1.0)
                    if t1 <= t0:
                        continue
                    p0 = (s.x0 + (s.x1 - s.x0) * t0,
                          s.y0 + (s.y1 - s.y0) * t0,
                          s.z0 + (s.z1 - s.z0) * t0)
                    p1 = (s.x0 + (s.x1 - s.x0) * t1,
                          s.y0 + (s.y1 - s.y0) * t1,
                          s.z0 + (s.z1 - s.z0) * t1)
                    result.append([p0, p1])
        return result

    def _build_tool_actor(self):
        if not self.segments:
            return
        s = self.segments[-1]
        r = max(0.1, s.tool_d / 2.0)
        x, y, z = s.x1, s.y1, s.z1
        try:
            tool = pv.Cylinder(center=(x, y, z + 4.0),
                               direction=(0, 0, 1),
                               radius=r, height=8.0, resolution=24)
            self._actors["tool"] = self.plotter.add_mesh(
                tool, color="#ffd166", lighting=True, name="tool",
                reset_camera=False)
        except Exception:
            pass

    def _build_axes_actor(self):
        try:
            self.plotter.add_axes(line_width=2, interactive=False)
        except Exception:
            pass

    def _scene_size(self):
        """Размер сцены с учётом заготовки и траектории."""
        sizes = [10.0]
        if self.stock is not None:
            try:
                bx0, by0, bx1, by1, z_top, z_bot = self.stock.bounds()
                sizes.append(abs(bx1 - bx0))
                sizes.append(abs(by1 - by0))
                sizes.append(abs(z_top - z_bot))
            except Exception:
                pass
        if self.bounds is not None:
            try:
                minx, miny, maxx, maxy = self.bounds
                sizes.append(abs(maxx - minx))
                sizes.append(abs(maxy - miny))
            except Exception:
                pass
        if self.segments:
            try:
                xs = [s.x0 for s in self.segments] + [s.x1 for s in self.segments]
                ys = [s.y0 for s in self.segments] + [s.y1 for s in self.segments]
                zs = [s.z0 for s in self.segments] + [s.z1 for s in self.segments]
                sizes.append(max(xs) - min(xs))
                sizes.append(max(ys) - min(ys))
                sizes.append(max(zs) - min(zs))
            except Exception:
                pass
        return max(sizes) if sizes else 10.0

    def _apply_camera(self):
        try:
            cam = self.plotter.camera
            cam.focal_point = self._target
            az = math.radians(self.azimuth)
            el = math.radians(self.elevation)
            size = self._scene_size()
            w = max(1, self.width())
            h = max(1, self.height())
            aspect = w / h
            # базовый дистанс + поправка на узкое окно, чтобы всё влезало
            dist = size * 2.8
            if aspect < 1.0:
                dist /= max(aspect, 0.3)
            x = self._target[0] + dist * math.cos(el) * math.sin(az)
            y = self._target[1] + dist * math.cos(el) * math.cos(az)
            z = self._target[2] + dist * math.sin(el)
            cam.position = (x, y, z)
            try:
                cam.parallel_projection = bool(self.ortho)
            except Exception:
                pass
        except Exception:
            pass

    def _schedule_render(self):
        if self._resizing:
            return
        self._render_timer.start()

    def _safe_render(self):
        if self._resizing:
            return
        try:
            self.plotter.render()
        except Exception as e:
            print(f"[View3D] render error: {e}")
        try:
            rw = self.plotter.render_window
            if rw is not None:
                rw.Render()
        except Exception:
            pass

    def showEvent(self, ev):
        super().showEvent(ev)
        if not self._first_render_done:
            self._first_render_done = True
            QTimer.singleShot(200, self._initial_camera_apply)
            QTimer.singleShot(400, self._safe_render)

    def _initial_camera_apply(self):
        if self._fit_after_show:
            self._do_initial_fit()
        else:
            self._apply_camera()
        self._safe_render()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._resizing = True
        self._render_timer.stop()
        self._resize_timer.start()
        if hasattr(self, "view_cube"):
            m = 10
            self.view_cube.move(
                self.width() - self.view_cube.width() - m, m)
            self.view_cube.raise_()

    def _on_resize_done(self):
        self._resizing = False
        try:
            self.plotter.interactor.resize(
                self.plotter.interactor.size())
        except Exception:
            pass
        # пересчитать distance под новый аспект (target и углы сохраняются)
        self._apply_camera()
        QTimer.singleShot(50, self._safe_render)