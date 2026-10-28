package com.example.sim

import com.example.core.FormulaEval
import com.example.core.ProgramInterp
import com.example.model.*
import kotlin.math.*

class Simulator(
    val toolsList: List<Tool>,
    val variables: Map<String, Double> = emptyMap(),
    val stock: Stock? = null,
    val settings: SimSettings = SimSettings(),
    val functionsList: List<FunctionDef> = emptyList(),
    val preamble: List<Command> = emptyList(),
    val postamble: List<Command> = emptyList()
) {
    val tools = toolsList.associateBy { it.number }
    val functions = functionsList.associateBy { it.name }
    private val fml = FormulaEval(variables)

    private fun n(v: Any?): Double = fml.resolveNumber(v)

    data class TraceResult(
        val segments: List<Segment>,
        val bounds: Bounds3D,
        val stats: SimulationStats,
        val heightMap: HeightMap?
    )

    fun trace(
        commands: List<Command>,
        upto: Int,
        checkCollisions: Boolean = true,
        stepLimit: Int? = null
    ): TraceResult {
        var cutLen = 0.0
        var rapidLen = 0.0
        var zMin = 0.0
        var collisionCount = 0
        val collisions = mutableListOf<CollisionInfo>()
        var executedSteps = 0

        val segs = mutableListOf<Segment>()
        val pos = doubleArrayOf(0.0, 0.0, 0.0) // x, y, z
        val rot = doubleArrayOf(0.0, 0.0, 0.0) // a, b, c
        var curTool: Tool? = tools.values.firstOrNull()
        var spindleOn = false
        var incremental = false
        var unitsScale = 1.0
        val wcsOff = doubleArrayOf(0.0, 0.0, 0.0)
        val g92Off = doubleArrayOf(0.0, 0.0, 0.0)
        var g92Active = true
        val g52Off = doubleArrayOf(0.0, 0.0, 0.0)
        var polar = false

        var minX = 0.0
        var minY = 0.0
        var minZ = 0.0
        var maxX = 10.0
        var maxY = 10.0
        var maxZ = 10.0

        val minToolD = tools.values.filter { it.diameter > 0 }.minOfOrNull { it.diameter } ?: 3.0
        val vxy = if (settings.autoVoxelXy) max(minToolD / 3.0, 0.1) else max(settings.voxelXy, 0.1)
        val vz = max(settings.voxelZ, 0.2)

        var hm: HeightMap? = null
        if (stock != null) {
            val b = stock.bounds()
            hm = HeightMap(b[0], b[1], b[2], b[3], b[4], b[5], voxelXy = vxy, voxelZ = vz)
            minX = min(minX, b[0]); maxX = max(maxX, b[2])
            minY = min(minY, b[1]); maxY = max(maxY, b[3])
            minZ = min(minZ, b[5]); maxZ = max(maxZ, b[4])
        }

        fun updateBounds(x: Double, y: Double, z: Double = pos[2]) {
            minX = min(minX, x); maxX = max(maxX, x)
            minY = min(minY, y); maxY = max(maxY, y)
            minZ = min(minZ, z); maxZ = max(maxZ, z)
        }

        fun totalOff(): DoubleArray {
            val gx = if (g92Active) g92Off[0] else 0.0
            val gy = if (g92Active) g92Off[1] else 0.0
            val gz = if (g92Active) g92Off[2] else 0.0
            return doubleArrayOf(
                wcsOff[0] + gx + g52Off[0],
                wcsOff[1] + gy + g52Off[1],
                wcsOff[2] + gz + g52Off[2]
            )
        }

        fun resolve(px: Double, py: Double, pz: Double): DoubleArray {
            val off = totalOff()
            return if (incremental) {
                doubleArrayOf(
                    pos[0] + px * unitsScale,
                    pos[1] + py * unitsScale,
                    pos[2] + pz * unitsScale
                )
            } else {
                doubleArrayOf(
                    px * unitsScale + off[0],
                    py * unitsScale + off[1],
                    pz * unitsScale + off[2]
                )
            }
        }

        fun checkCollision(seg: Segment) {
            if (hm == null || !checkCollisions) return
            val radius = seg.toolD / 2.0
            val len = hypot(seg.x1 - seg.x0, seg.y1 - seg.y0)
            val step = max(hm.dx * 0.5, 0.2)
            val n = max(2, (len / step).toInt() + 1)
            var inside = false

            for (i in 0..n) {
                val t = i.toDouble() / n
                val px = seg.x0 + (seg.x1 - seg.x0) * t
                val py = seg.y0 + (seg.y1 - seg.y0) * t
                val pz = seg.z0 + (seg.z1 - seg.z0) * t
                val hmax = hm.maxHeightInDisc(px, py, radius)
                if (pz < hmax - 1e-4) {
                    inside = true
                    break
                }
            }

            if (!inside) return
            val reason = if (seg.rapid) {
                if (settings.ignoreRapidInMaterial) return
                "RAPID в материале"
            } else if (!seg.spindleOn) {
                "FEED при выключенном шпинделе"
            } else {
                return
            }

            seg.collision = true
            seg.collisionReason = reason
            collisionCount++
            collisions.add(CollisionInfo(seg.cmdIndex, reason, seg.x1, seg.y1, seg.z1))
        }

        fun applyCut(seg: Segment) {
            if (hm == null || seg.collision || !seg.spindleOn) return
            val radius = seg.toolD / 2.0
            if (seg.drill) {
                hm.cutDrill(seg.x1, seg.y1, seg.z0, seg.z1, radius)
            } else if (seg.arc) {
                val r = hypot(seg.x0 - seg.cx, seg.y0 - seg.cy)
                val a0 = atan2(seg.y0 - seg.cy, seg.x0 - seg.cx)
                var a1 = atan2(seg.y1 - seg.cy, seg.x1 - seg.cx)
                if (abs(a1 - a0) < 1e-7) {
                    a1 = a0 + if (!seg.cw) 2 * Math.PI else -2 * Math.PI
                }
                hm.cutArc(seg.cx, seg.cy, r, a0, a1, seg.z0, seg.z1, radius, seg.cw)
            } else if (!seg.rapid) {
                hm.cutLine(seg.x0, seg.y0, seg.z0, seg.x1, seg.y1, seg.z1, radius)
            }
        }

        fun doArc(ccx: Double, ccy: Double, ex: Double, ey: Double, ez: Double, cw: Boolean, dia: Double, col: String, idx: Int) {
            val a0 = atan2(pos[1] - ccy, pos[0] - ccx)
            var a1 = atan2(ey - ccy, ex - ccx)
            var da = a1 - a0
            if (cw) {
                while (da > 0) da -= 2 * Math.PI
            } else {
                while (da < 0) da += 2 * Math.PI
            }
            val seg = Segment(
                pos[0], pos[1], pos[2], ex, ey, ez, dia, col,
                rapid = false, arc = true, cx = ccx, cy = ccy, cw = cw,
                spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps
            )
            checkCollision(seg)
            applyCut(seg)
            segs.add(seg)
            val r = hypot(pos[0] - ccx, pos[1] - ccy)
            cutLen += abs(da) * r
            zMin = min(zMin, ez)
            updateBounds(ex, ey, ez)
            updateBounds(ccx - r, ccy - r, ez)
            updateBounds(ccx + r, ccy + r, ez)
        }

        val liveVars = variables.toMutableMap()
        val interp = ProgramInterp(commands, liveVars, maxSteps = (stepLimit ?: 100000) * 2, functions = functions)

        fun onCmd(cmd: Command, idx: Int) {
            if (idx >= 0 && idx > upto - 1) return
            executedSteps++
            if (stepLimit != null && stepLimit > 0 && executedSteps > stepLimit) return

            val m = cmd.mnemonic
            val p = cmd.params
            fml.vars = interp.vars

            when (m) {
                "ABS" -> { incremental = false; return }
                "INC" -> { incremental = true; return }
                "UNITS_IN", "UNITS_IN2" -> { unitsScale = 25.4; return }
                "UNITS_MM", "UNITS_MM2" -> { unitsScale = 1.0; return }
                "POLAR_ON" -> { polar = true; return }
                "POLAR_OFF" -> { polar = false; return }
                "SPIN" -> {
                    spindleOn = (n(p["on"] ?: 1).toInt()) != 0
                    return
                }
                "TOOL" -> {
                    val tNum = n(p["tool"] ?: 1).toInt()
                    curTool = tools[tNum] ?: curTool
                    return
                }
                "G10" -> {
                    val l = n(p["l"] ?: 2).toInt()
                    if (l == 2 || l == 20) {
                        wcsOff[0] = n(p["x"] ?: 0)
                        wcsOff[1] = n(p["y"] ?: 0)
                        wcsOff[2] = n(p["z"] ?: 0)
                    }
                    return
                }
                "G92SET" -> {
                    g92Off[0] = pos[0] - n(p["x"] ?: 0)
                    g92Off[1] = pos[1] - n(p["y"] ?: 0)
                    g92Off[2] = pos[2] - n(p["z"] ?: 0)
                    g92Active = true
                    return
                }
                "G92CLR" -> {
                    g92Off[0] = 0.0; g92Off[1] = 0.0; g92Off[2] = 0.0
                    g92Active = true
                    return
                }
                "LOCAL_OFF" -> {
                    g52Off[0] = n(p["x"] ?: 0)
                    g52Off[1] = n(p["y"] ?: 0)
                    g52Off[2] = n(p["z"] ?: 0)
                    return
                }
                "HOME_BASE" -> {
                    pos[0] = 0.0; pos[1] = 0.0; pos[2] = 0.0
                    return
                }
            }

            val ct = curTool
            val dia = ct?.diameter ?: 3.0
            val col = ct?.color ?: "#3399FF"

            when (m) {
                "RAPID", "FEED" -> {
                    val px = n(p["x"] ?: pos[0])
                    val py = n(p["y"] ?: pos[1])
                    val pz = n(p["z"] ?: pos[2])
                    val npos = resolve(px, py, pz)
                    val nx = npos[0]; val ny = npos[1]; val nz = npos[2]
                    if ("a" in p) rot[0] = n(p["a"])
                    if ("b" in p) rot[1] = n(p["b"])
                    if ("c" in p) rot[2] = n(p["c"])

                    val isRapid = (m == "RAPID")
                    val seg = Segment(
                        pos[0], pos[1], pos[2], nx, ny, nz, dia, col,
                        rapid = isRapid, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps
                    )
                    checkCollision(seg)
                    applyCut(seg)
                    segs.add(seg)

                    val dist = hypot(nx - pos[0], ny - pos[1])
                    if (isRapid) {
                        rapidLen += dist
                    } else {
                        cutLen += dist
                        zMin = min(zMin, nz)
                    }
                    pos[0] = nx; pos[1] = ny; pos[2] = nz
                    updateBounds(nx, ny, nz)
                }
                "ARC_CW", "ARC_CCW" -> {
                    val npos = resolve(n(p["x"] ?: pos[0]), n(p["y"] ?: pos[1]), n(p["z"] ?: pos[2]))
                    val ccx = n(p["cx"] ?: pos[0])
                    val ccy = n(p["cy"] ?: pos[1])
                    doArc(ccx, ccy, npos[0], npos[1], npos[2], m == "ARC_CW", dia, col, idx)
                    pos[0] = npos[0]; pos[1] = npos[1]; pos[2] = npos[2]
                }
                "DRILL", "PECK", "CHIP", "BORE", "THREAD_R", "BORE_STD", "BORE_SPINDLE", "BORE_BACK", "BORE_MANUAL", "BORE_FINE" -> {
                    val npos = resolve(n(p["x"] ?: pos[0]), n(p["y"] ?: pos[1]), n(p["z"] ?: -5))
                    val hx = npos[0]; val hy = npos[1]; val hz = npos[2]

                    // rapid to hole location
                    val segR = Segment(pos[0], pos[1], pos[2], hx, hy, pos[2], dia, col, rapid = true, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps)
                    checkCollision(segR)
                    segs.add(segR)
                    rapidLen += hypot(hx - pos[0], hy - pos[1])
                    pos[0] = hx; pos[1] = hy

                    // plunge drill
                    val segD = Segment(hx, hy, pos[2], hx, hy, hz, dia, col, rapid = false, drill = true, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps)
                    checkCollision(segD)
                    applyCut(segD)
                    segs.add(segD)
                    cutLen += abs(hz - pos[2])
                    zMin = min(zMin, hz)
                    pos[2] = hz

                    // retract to safe clear height
                    val zClear = max(5.0, (hm?.zTop ?: 0.0) + 2.0)
                    val segU = Segment(hx, hy, hz, hx, hy, zClear, dia, col, rapid = true, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps)
                    checkCollision(segU)
                    segs.add(segU)
                    rapidLen += abs(zClear - hz)
                    pos[2] = zClear
                    updateBounds(hx, hy, zClear)
                }
                "POCKET_CW", "POCKET_CCW" -> {
                    val cw = (m == "POCKET_CW")
                    val capR = n(p["i"] ?: 10.0)
                    val targetZ = n(p["z"] ?: -2.0)
                    val cx = pos[0]; val cy = pos[1]
                    val step = max(dia * 0.5, 0.5)
                    var curR = dia * 0.5
                    var first = true

                    while (curR <= capR + 1e-7) {
                        if (first) {
                            val segIn = Segment(cx, cy, pos[2], cx, cy, targetZ, dia, col, rapid = false, drill = true, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps)
                            checkCollision(segIn)
                            applyCut(segIn)
                            segs.add(segIn)
                            pos[2] = targetZ
                            first = false
                        }
                        doArc(cx, cy, cx + curR, cy, targetZ, cw, dia, col, idx)
                        if (curR + step <= capR + 1e-7) {
                            doArc(cx, cy, cx + curR + step, cy, targetZ, cw, dia, col, idx)
                        }
                        curR += step
                    }
                    pos[0] = cx + curR - step; pos[1] = cy; pos[2] = targetZ
                    zMin = min(zMin, targetZ)
                    updateBounds(cx - capR, cy - capR, targetZ)
                    updateBounds(cx + capR, cy + capR, targetZ)
                }
                "PROBE" -> {
                    val npos = resolve(n(p["x"] ?: pos[0]), n(p["y"] ?: pos[1]), n(p["z"] ?: pos[2]))
                    val seg = Segment(pos[0], pos[1], pos[2], npos[0], npos[1], npos[2], dia, col, rapid = false, spindleOn = spindleOn, cmdIndex = idx, executedIndex = executedSteps)
                    checkCollision(seg)
                    applyCut(seg)
                    segs.add(seg)
                    cutLen += hypot(npos[0] - pos[0], npos[1] - pos[1])
                    pos[0] = npos[0]; pos[1] = npos[1]; pos[2] = npos[2]
                    updateBounds(npos[0], npos[1], npos[2])
                }
            }
        }

        // Run preamble
        if (preamble.isNotEmpty()) {
            val preInterp = ProgramInterp(preamble, liveVars, maxSteps = 50000, functions = functions)
            preInterp.run { c, _ -> onCmd(c, -1) }
        }

        // Run main commands up to requested index
        interp.run(0, upto, stepLimit = stepLimit) { c, i ->
            onCmd(c, i)
        }

        // Run postamble
        if (postamble.isNotEmpty()) {
            val postInterp = ProgramInterp(postamble, interp.vars, maxSteps = 50000, functions = functions)
            postInterp.run { c, _ -> onCmd(c, -1) }
        }

        val pad = max(maxX - minX, maxY - minY) * 0.08 + 5.0
        val bounds = Bounds3D(minX - pad, minY - pad, minZ - 2.0, maxX + pad, maxY + pad, maxZ + 10.0)

        val feedRate = (curTool?.feed ?: 200.0).coerceAtLeast(10.0)
        val estTime = (cutLen / feedRate) + (rapidLen / 1500.0)

        val stats = SimulationStats(
            cutLen = cutLen,
            rapidLen = rapidLen,
            zMin = zMin,
            collisionCount = collisionCount,
            collisions = collisions,
            executedSteps = executedSteps,
            estTimeMinutes = estTime,
            removedVolumeCm3 = (hm?.removedVolume ?: 0.0) / 1000.0,
            a = rot[0],
            b = rot[1],
            c = rot[2]
        )

        return TraceResult(segs, bounds, stats, hm)
    }
}
