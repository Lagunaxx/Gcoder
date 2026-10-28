# -*- coding: utf-8 -*-
"""Загрузка треугольных мешей STL/OBJ/3MF."""

import os
import struct
from gcode_editor.core.models import PartMesh


class MeshLoader:
    @staticmethod
    def load(path):
        lower = path.lower()
        try:
            if lower.endswith(".stl"):
                return MeshLoader._load_stl(path)
            if lower.endswith(".obj"):
                return MeshLoader._load_obj(path)
            if lower.endswith(".3mf"):
                return MeshLoader._load_3mf(path)
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки {os.path.basename(path)}: {e}")
        raise RuntimeError("Поддерживаются: .stl, .obj, .3mf")

    @staticmethod
    def _is_binary_stl(path):
        with open(path, "rb") as f:
            head = f.read(84)
            if len(head) < 84:
                return False
            try:
                sample = head.decode("ascii", errors="ignore").strip().lower()
                if sample.startswith("solid") and b"facet" in head.lower():
                    return False
            except Exception:
                pass
            count = struct.unpack("<I", head[80:84])[0]
            size = os.path.getsize(path)
            if 84 + count * 50 == size:
                return True
            return count > 0

    @staticmethod
    def _load_stl(path):
        if MeshLoader._is_binary_stl(path):
            return MeshLoader._load_stl_binary(path)
        return MeshLoader._load_stl_ascii(path)

    @staticmethod
    def _load_stl_binary(path):
        tris = []
        with open(path, "rb") as f:
            f.read(80)
            cb = f.read(4)
            if len(cb) < 4:
                raise RuntimeError("Некорректный STL")
            count = struct.unpack("<I", cb)[0]
            for _ in range(count):
                data = f.read(50)
                if len(data) < 50:
                    break
                vals = struct.unpack("<12fH", data)
                tris.append(((vals[3], vals[4], vals[5]),
                             (vals[6], vals[7], vals[8]),
                             (vals[9], vals[10], vals[11])))
        mesh = PartMesh(file_path=path,
                        name=os.path.splitext(os.path.basename(path))[0],
                        triangles=tris)
        mesh.compute_bbox()
        return mesh

    @staticmethod
    def _load_stl_ascii(path):
        tris = []
        cur = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().lower()
                if line.startswith("vertex"):
                    p = line.split()
                    if len(p) >= 4:
                        try:
                            cur.append((float(p[1]), float(p[2]), float(p[3])))
                        except ValueError:
                            continue
                    if len(cur) == 3:
                        tris.append((cur[0], cur[1], cur[2]))
                        cur = []
        mesh = PartMesh(file_path=path,
                        name=os.path.splitext(os.path.basename(path))[0],
                        triangles=tris)
        mesh.compute_bbox()
        return mesh

    @staticmethod
    def _load_obj(path):
        verts = []
        tris = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("v "):
                    p = line.split()
                    if len(p) >= 4:
                        try:
                            verts.append((float(p[1]), float(p[2]), float(p[3])))
                        except ValueError:
                            continue
                elif line.startswith("f "):
                    parts = line.split()[1:]
                    idxs = []
                    for p in parts:
                        s = p.split("/")[0]
                        try:
                            i = int(s)
                        except ValueError:
                            continue
                        if i < 0:
                            i = len(verts) + i
                        else:
                            i -= 1
                        if 0 <= i < len(verts):
                            idxs.append(i)
                    if len(idxs) >= 3:
                        v0 = verts[idxs[0]]
                        for k in range(1, len(idxs) - 1):
                            tris.append((v0, verts[idxs[k]], verts[idxs[k + 1]]))
        mesh = PartMesh(file_path=path,
                        name=os.path.splitext(os.path.basename(path))[0],
                        triangles=tris)
        mesh.compute_bbox()
        return mesh

    @staticmethod
    def _load_3mf(path):
        import zipfile
        import xml.etree.ElementTree as ET
        tris = []
        with zipfile.ZipFile(path, "r") as z:
            names = [n for n in z.namelist() if n.lower().endswith(".model")]
            if not names:
                raise RuntimeError("В 3MF нет .model")
            for name in names:
                with z.open(name) as f:
                    data = f.read()
                root = ET.fromstring(data)
                verts = []
                for el in root.iter():
                    if el.tag.split("}")[-1] == "vertex":
                        try:
                            verts.append((float(el.get("x", "0")),
                                          float(el.get("y", "0")),
                                          float(el.get("z", "0"))))
                        except (TypeError, ValueError):
                            continue
                for el in root.iter():
                    if el.tag.split("}")[-1] == "triangle":
                        try:
                            i1 = int(el.get("v1", "-1"))
                            i2 = int(el.get("v2", "-1"))
                            i3 = int(el.get("v3", "-1"))
                        except (TypeError, ValueError):
                            continue
                        if 0 <= i1 < len(verts) and 0 <= i2 < len(verts) and 0 <= i3 < len(verts):
                            tris.append((verts[i1], verts[i2], verts[i3]))
        mesh = PartMesh(file_path=path,
                        name=os.path.splitext(os.path.basename(path))[0],
                        triangles=tris)
        mesh.compute_bbox()
        return mesh
