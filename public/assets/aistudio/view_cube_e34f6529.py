# -*- coding: utf-8 -*-
"""Куб-навигатор (overlay поверх 3D-вида)."""

import math
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (QPainter, QPen, QColor, QBrush, QFont,
                         QPolygonF, QVector3D)
from PyQt5.QtWidgets import QWidget


class ViewCube(QWidget):
    """Небольшой 3D-куб в углу. Клик по грани/углу меняет ракурс."""

    view_requested = pyqtSignal(float, float)   # (azimuth, elevation)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(False)
        self.hover_zone = None
        self._azimuth = -35.0
        self._elevation = 35.0
        self._face_polys = {}
        self._corner_circles = {}

        self.face_views = {
            "TOP": (0.0, 89.9), "BOTTOM": (0.0, -89.9),
            "FRONT": (0.0, 0.0), "BACK": (180.0, 0.0),
            "LEFT": (-90.0, 0.0), "RIGHT": (90.0, 0.0),
        }
        self.iso_views = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    key = ("N" if sy > 0 else "F") + "_" + \
                          ("R" if sx > 0 else "L") + "_" + \
                          ("T" if sz > 0 else "B")
                    az = math.degrees(math.atan2(-sx, -sy)) - 90
                    if az < -180: az += 360
                    if az > 180: az -= 360
                    horiz = math.hypot(sx, sy)
                    el = math.degrees(math.atan2(sz, horiz))
                    self.iso_views[key] = (az, el)

    # ---------- public ----------
    def set_camera_angles(self, az, el):
        self._azimuth = float(az)
        self._elevation = float(el)
        self.update()

    # ---------- painting ----------
    def _project(self, x, y, z, size=34):
        az = math.radians(self._azimuth)
        el = math.radians(self._elevation)
        ca, sa = math.cos(az), math.sin(az)
        ce, se = math.cos(el), math.sin(el)
        sx = x * (-sa) + y * ca
        sy = x * (-ca * se) + y * (-sa * se) + z * ce
        cx = self.width() / 2
        cy = self.height() / 2
        return QPointF(cx + sx * size, cy - sy * size)

    def _look_vector(self):
        az = math.radians(self._azimuth)
        el = math.radians(self._elevation)
        return QVector3D(
            math.sin(az) * math.cos(el),
            -math.cos(az) * math.cos(el),
            math.sin(el))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        corners = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    key = ("N" if sy > 0 else "F") + "_" + \
                          ("R" if sx > 0 else "L") + "_" + \
                          ("T" if sz > 0 else "B")
                    corners[key] = (sx, sy, sz)
        pts = {k: self._project(*v) for k, v in corners.items()}

        edges = []
        for k1 in corners:
            for k2 in corners:
                if k1 >= k2:
                    continue
                d = sum(abs(a - b) for a, b in zip(corners[k1], corners[k2]))
                if d == 2:
                    edges.append((k1, k2))

        look = self._look_vector()
        face_verts = {
            "TOP":    ["F_R_T", "N_R_T", "N_L_T", "F_L_T"],
            "BOTTOM": ["F_R_B", "N_R_B", "N_L_B", "F_L_B"],
            "FRONT":  ["F_L_T", "F_R_T", "F_R_B", "F_L_B"],
            "BACK":   ["N_L_T", "N_R_T", "N_R_B", "N_L_B"],
            "LEFT":   ["F_L_T", "N_L_T", "N_L_B", "F_L_B"],
            "RIGHT":  ["F_R_T", "N_R_T", "N_R_B", "F_R_B"],
        }
        face_normals = {"TOP": (0, 0, 1), "BOTTOM": (0, 0, -1),
                        "FRONT": (0, -1, 0), "BACK": (0, 1, 0),
                        "LEFT": (-1, 0, 0), "RIGHT": (1, 0, 0)}

        def fd(name):
            return QVector3D.dotProduct(QVector3D(*face_normals[name]), look)

        sorted_faces = sorted(face_verts.keys(), key=fd)
        self._face_polys = {}
        for name in sorted_faces:
            verts = [pts[k] for k in face_verts[name]]
            poly = QPolygonF(verts)
            self._face_polys[name] = poly
            facing = fd(name) > 0.01
            if facing:
                base = QColor(210, 214, 230, 235)
            else:
                base = QColor(70, 72, 88, 130)
            if self.hover_zone == name and facing:
                base = QColor(255, 200, 60, 245)
            p.setPen(QPen(QColor(20, 20, 30), 1))
            p.setBrush(QBrush(base))
            p.drawPolygon(poly)
            if facing:
                c = poly.boundingRect().center()
                p.setPen(QColor(20, 20, 30))
                p.setFont(QFont("Arial", 6, QFont.Bold))
                short = {"TOP": "T", "BOTTOM": "B", "FRONT": "F",
                         "BACK": "Bk", "LEFT": "L", "RIGHT": "R"}[name]
                p.drawText(QRectF(c.x() - 8, c.y() - 8, 16, 16),
                           Qt.AlignCenter, short)

        self._corner_circles = {}
        for key, pt in pts.items():
            v = QVector3D(*corners[key])
            if QVector3D.dotProduct(v, look) > 0.1:
                r = 5
                self._corner_circles[key] = (pt, r)
                col = QColor(255, 200, 60, 245) if self.hover_zone == key \
                    else QColor(180, 182, 200, 220)
                p.setPen(QPen(QColor(20, 20, 30), 1))
                p.setBrush(QBrush(col))
                p.drawEllipse(pt, r, r)

        p.setPen(QPen(QColor(20, 20, 30), 1))
        for k1, k2 in edges:
            p.drawLine(pts[k1], pts[k2])
        p.end()

    # ---------- picking ----------
    def _pick_zone(self, pos):
        for key, (pt, r) in self._corner_circles.items():
            if (pos - pt).manhattanLength() <= r * 2:
                return key
        for name, poly in self._face_polys.items():
            if poly.containsPoint(QPointF(pos), Qt.OddEvenFill):
                return name
        return None

    def mouseMoveEvent(self, ev):
        z = self._pick_zone(ev.pos())
        if z != self.hover_zone:
            self.hover_zone = z
            self.update()

    def leaveEvent(self, ev):
        self.hover_zone = None
        self.update()

    def mousePressEvent(self, ev):
        z = self._pick_zone(ev.pos())
        if z is None:
            return
        if z in self.face_views:
            az, el = self.face_views[z]
        elif z in self.iso_views:
            az, el = self.iso_views[z]
        else:
            return
        self.view_requested.emit(az, el)