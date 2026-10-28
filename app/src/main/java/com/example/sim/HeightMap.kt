package com.example.sim

import kotlin.math.*

class HeightMap(
    val xMin: Double,
    val yMin: Double,
    val xMax: Double,
    val yMax: Double,
    val zTop: Double,
    val zBottom: Double,
    val voxelXy: Double = 1.0,
    val voxelZ: Double = 1.0
) {
    val w = max(xMax - xMin, 1e-4)
    val h = max(yMax - yMin, 1e-4)

    // Optimal grid resolution for fast real-time 3D rendering on mobile
    val nx = max(1, ceil(w / max(voxelXy, 1.0)).toInt()).coerceIn(20, 80)
    val ny = max(1, ceil(h / max(voxelXy, 1.0)).toInt()).coerceIn(20, 80)

    val dx = w / nx
    val dy = h / ny

    val curZ = Array(nx) { DoubleArray(ny) { zTop } }
    var removedVolume = 0.0
        private set
    var minZ = zTop
        private set

    fun copy(): HeightMap {
        val next = HeightMap(xMin, yMin, xMax, yMax, zTop, zBottom, voxelXy, voxelZ)
        for (i in 0 until nx) {
            System.arraycopy(this.curZ[i], 0, next.curZ[i], 0, ny)
        }
        next.removedVolume = this.removedVolume
        next.minZ = this.minZ
        return next
    }

    private fun idx(x: Double): Int = ((x - xMin) / dx).toInt().coerceIn(0, nx - 1)
    private fun idy(y: Double): Int = ((y - yMin) / dy).toInt().coerceIn(0, ny - 1)

    fun inBounds(x: Double, y: Double): Boolean = x in xMin..xMax && y in yMin..yMax

    fun cutDisc(cx: Double, cy: Double, z: Double, radius: Double) {
        if (radius <= 0.0 || dx <= 0.0) return
        val r2 = radius * radius
        val ix0 = idx(cx - radius)
        val ix1 = idx(cx + radius)
        val iy0 = idy(cy - radius)
        val iy1 = idy(cy + radius)
        val cellArea = dx * dy

        for (ix in ix0..ix1) {
            val px = xMin + (ix + 0.5) * dx
            val diffX = px - cx
            if (diffX * diffX > r2) continue
            for (iy in iy0..iy1) {
                val py = yMin + (iy + 0.5) * dy
                val diffY = py - cy
                if (diffX * diffX + diffY * diffY <= r2) {
                    val old = curZ[ix][iy]
                    if (z < old - 1e-5) {
                        removedVolume += (old - z) * cellArea
                        curZ[ix][iy] = max(z, zBottom)
                        if (z < minZ) minZ = z
                    }
                }
            }
        }
    }

    fun cutLine(x0: Double, y0: Double, z0: Double, x1: Double, y1: Double, z1: Double, radius: Double) {
        val len = hypot(x1 - x0, y1 - y0)
        val step = max(dx * 0.5, 0.2)
        val n = max(1, (len / step).toInt())
        for (i in 0..n) {
            val t = i.toDouble() / n
            cutDisc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t, radius)
        }
    }

    fun cutArc(cx: Double, cy: Double, r: Double, a0: Double, a1: Double, z0: Double, z1: Double, radius: Double, cw: Boolean) {
        var da = a1 - a0
        if (cw) {
            while (da > 0) da -= 2 * Math.PI
        } else {
            while (da < 0) da += 2 * Math.PI
        }
        val arcLen = abs(da) * r
        val step = max(dx * 0.5, 0.2)
        val n = max(1, (arcLen / step).toInt())
        for (i in 0..n) {
            val t = i.toDouble() / n
            val a = a0 + da * t
            cutDisc(cx + r * cos(a), cy + r * sin(a), z0 + (z1 - z0) * t, radius)
        }
    }

    fun cutDrill(cx: Double, cy: Double, zTopDrill: Double, zBottom: Double, radius: Double) {
        cutDisc(cx, cy, zBottom, radius)
    }

    fun maxHeightInDisc(cx: Double, cy: Double, radius: Double): Double {
        if (radius <= 0.0) {
            return if (inBounds(cx, cy)) curZ[idx(cx)][idy(cy)] else -1e9
        }
        val ix0 = idx(cx - radius)
        val ix1 = idx(cx + radius)
        val iy0 = idy(cy - radius)
        val iy1 = idy(cy + radius)
        var maxVal = -1e9
        var inside = false
        val r2 = radius * radius

        for (ix in ix0..ix1) {
            val px = xMin + (ix + 0.5) * dx
            val diffX = px - cx
            if (diffX * diffX > r2) continue
            for (iy in iy0..iy1) {
                val py = yMin + (iy + 0.5) * dy
                val diffY = py - cy
                if (diffX * diffX + diffY * diffY <= r2) {
                    if (inBounds(px, py)) {
                        inside = true
                        val zval = curZ[ix][iy]
                        if (zval > maxVal) maxVal = zval
                    }
                }
            }
        }
        return if (inside) maxVal else -1e9
    }
}
