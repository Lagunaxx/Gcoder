# -*- coding: utf-8 -*-
"""Сетка высот материала."""

import math


class HeightMap:
    def __init__(self, x_min, y_min, x_max, y_max, z_top, z_bottom,
                 voxel_xy=0.5, voxel_z=1.0):
        self.x_min = float(x_min)
        self.y_min = float(y_min)
        self.x_max = float(x_max)
        self.y_max = float(y_max)
        self.z_top = float(z_top)
        self.z_bottom = float(z_bottom)
        w = max(self.x_max - self.x_min, 1e-6)
        h = max(self.y_max - self.y_min, 1e-6)
        self.voxel_xy = max(float(voxel_xy), 1e-3)
        self.voxel_z = max(float(voxel_z), 1e-3)
        self.nx = max(1, int(math.ceil(w / self.voxel_xy)))
        self.ny = max(1, int(math.ceil(h / self.voxel_xy)))
        self.dx = w / self.nx
        self.dy = h / self.ny
        self.init_z = [[self.z_top] * self.ny for _ in range(self.nx)]
        self.cur_z = [[self.z_top] * self.ny for _ in range(self.nx)]
        self.removed_volume = 0.0
        self.min_z = self.z_top
        self.is_mesh = False

    def _idx(self, x):
        ix = int((x - self.x_min) / self.dx)
        if ix < 0: ix = 0
        if ix >= self.nx: ix = self.nx - 1
        return ix

    def _idy(self, y):
        iy = int((y - self.y_min) / self.dy)
        if iy < 0: iy = 0
        if iy >= self.ny: iy = self.ny - 1
        return iy

    def in_bounds(self, x, y):
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max)

    def _has_material(self, ix, iy):
        return self.init_z[ix][iy] > self.z_bottom + 1e-6

    def cut_disc(self, cx, cy, z, radius):
        if radius <= 0 or self.dx <= 0:
            return
        r2 = radius * radius
        ix0 = self._idx(cx - radius)
        ix1 = self._idx(cx + radius)
        iy0 = self._idy(cy - radius)
        iy1 = self._idy(cy + radius)
        cell_area = self.dx * self.dy
        for ix in range(ix0, ix1 + 1):
            px = self.x_min + (ix + 0.5) * self.dx
            dx = px - cx
            if dx * dx > r2:
                continue
            for iy in range(iy0, iy1 + 1):
                py = self.y_min + (iy + 0.5) * self.dy
                dy = py - cy
                if dx * dx + dy * dy <= r2:
                    if not self._has_material(ix, iy):
                        continue
                    old = self.cur_z[ix][iy]
                    if z < old - 1e-6:
                        self.removed_volume += (old - z) * cell_area
                        self.cur_z[ix][iy] = z
                        if z < self.min_z:
                            self.min_z = z

    def cut_line(self, x0, y0, z0, x1, y1, z1, radius):
        L = math.hypot(x1 - x0, y1 - y0)
        step = max(self.dx * 0.5, 0.05)
        n = max(1, int(L / step))
        for i in range(n + 1):
            t = i / n
            self.cut_disc(x0 + (x1 - x0) * t,
                          y0 + (y1 - y0) * t,
                          z0 + (z1 - z0) * t, radius)

    def cut_arc(self, cx, cy, r, a0, a1, z0, z1, radius, cw):
        if not all(map(math.isfinite, (cx, cy, r, a0, a1, z0, z1, radius))):
            return
        da = a1 - a0
        if cw:
            while da > 0: da -= 2 * math.pi
        else:
            while da < 0: da += 2 * math.pi
        arc_len = abs(da) * r
        step = max(self.dx * 0.5, 0.05)
        n = max(1, int(arc_len / step))
        for i in range(n + 1):
            t = i / n
            a = a0 + da * t
            self.cut_disc(cx + r * math.cos(a), cy + r * math.sin(a),
                          z0 + (z1 - z0) * t, radius)

    def cut_drill(self, cx, cy, z_top_drill, z_bottom, radius):
        if radius <= 0:
            return
        r2 = radius * radius
        ix0 = self._idx(cx - radius)
        ix1 = self._idx(cx + radius)
        iy0 = self._idy(cy - radius)
        iy1 = self._idy(cy + radius)
        cell_area = self.dx * self.dy
        for ix in range(ix0, ix1 + 1):
            px = self.x_min + (ix + 0.5) * self.dx
            dx = px - cx
            if dx * dx > r2:
                continue
            for iy in range(iy0, iy1 + 1):
                py = self.y_min + (iy + 0.5) * self.dy
                dy = py - cy
                if dx * dx + dy * dy <= r2:
                    if not self._has_material(ix, iy):
                        continue
                    old = self.cur_z[ix][iy]
                    if z_bottom < old - 1e-6:
                        self.removed_volume += (old - z_bottom) * cell_area
                        self.cur_z[ix][iy] = z_bottom
                        if z_bottom < self.min_z:
                            self.min_z = z_bottom

    def max_height_in_disc(self, cx, cy, radius):
        if radius <= 0:
            if self.in_bounds(cx, cy):
                return self.cur_z[self._idx(cx)][self._idy(cy)]
            return -1e9
        ix0 = self._idx(cx - radius)
        ix1 = self._idx(cx + radius)
        iy0 = self._idy(cy - radius)
        iy1 = self._idy(cy + radius)
        inside_any = False
        max_z = -1e9
        r2 = radius * radius
        for ix in range(ix0, ix1 + 1):
            px = self.x_min + (ix + 0.5) * self.dx
            dx = px - cx
            if dx * dx > r2:
                continue
            for iy in range(iy0, iy1 + 1):
                py = self.y_min + (iy + 0.5) * self.dy
                dy = py - cy
                if dx * dx + dy * dy <= r2:
                    if self.in_bounds(px, py):
                        inside_any = True
                        zval = self.cur_z[ix][iy]
                        if zval > max_z:
                            max_z = zval
        return max_z if inside_any else -1e9