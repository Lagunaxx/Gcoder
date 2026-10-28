package com.example.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.Bounds3D
import com.example.model.Segment
import com.example.model.ShadingMode
import com.example.model.Stock
import com.example.sim.HeightMap
import kotlin.math.*

class Camera3DState {
    var azimuth by mutableFloatStateOf(-35f)
    var elevation by mutableFloatStateOf(32f)
    var zoom by mutableFloatStateOf(1.0f)
    var panX by mutableFloatStateOf(0f)
    var panY by mutableFloatStateOf(0f)

    fun setTop() {
        azimuth = 0f
        elevation = 89.9f
        panX = 0f
        panY = 0f
    }

    fun setFront() {
        azimuth = 0f
        elevation = 0f
        panX = 0f
        panY = 0f
    }

    fun setIsometric() {
        azimuth = -35f
        elevation = 32f
        panX = 0f
        panY = 0f
    }

    fun reset() {
        setIsometric()
        zoom = 1.0f
        panX = 0f
        panY = 0f
    }
}

@Composable
fun rememberCamera3DState(): Camera3DState {
    return remember { Camera3DState() }
}

@Composable
fun Touch3DView(
    segments: List<Segment>,
    stock: Stock?,
    bounds: Bounds3D,
    heightMap: HeightMap?,
    currentStepIndex: Int,
    gridSizeMm: Double = 1.5,
    cameraState: Camera3DState = rememberCamera3DState(),
    showToolpath: Boolean = true,
    showMaterial: Boolean = true,
    shadingMode: ShadingMode = ShadingMode.SOLID,
    transparency: Float = 0.45f,
    onToggleToolpath: (Boolean) -> Unit = {},
    onToggleMaterial: (Boolean) -> Unit = {},
    onChangeShadingMode: (ShadingMode) -> Unit = {},
    onChangeTransparency: (Float) -> Unit = {},
    onChangeGridSize: (Double) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val textMeasurer = rememberTextMeasurer()
    var showQuickSettings by remember { mutableStateOf(false) }

    // Reusable single Path instance to prevent Skia native memory leaks during 60fps rotation
    val reusablePath = remember { Path() }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, gestureZoom, _ ->
                    // Guard against non-finite float values on quick lift/fling
                    if (gestureZoom.isFinite() && gestureZoom > 0f) {
                        cameraState.zoom = (cameraState.zoom * gestureZoom).coerceIn(0.2f, 8.0f)
                    }

                    if (pan.x.isFinite() && pan.y.isFinite()) {
                        if (abs(gestureZoom - 1f) < 0.05f) {
                            var newAz = (cameraState.azimuth + pan.x * 0.5f) % 360f
                            if (newAz < -180f) newAz += 360f
                            if (newAz > 180f) newAz -= 360f
                            cameraState.azimuth = newAz
                            cameraState.elevation = (cameraState.elevation - pan.y * 0.4f).coerceIn(-89.5f, 89.5f)
                        } else {
                            cameraState.panX = (cameraState.panX + pan.x).coerceIn(-2000f, 2000f)
                            cameraState.panY = (cameraState.panY + pan.y).coerceIn(-2000f, 2000f)
                        }
                    }
                }
            }
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            if (w <= 0 || h <= 0 || !w.isFinite() || !h.isFinite()) return@Canvas

            try {
                val cx = w / 2f + cameraState.panX
                val cy = h / 2f + cameraState.panY

                val minX = stock?.px ?: bounds.minX
                val maxX = (stock?.px?.plus(stock.x)) ?: bounds.maxX
                val minY = stock?.py ?: bounds.minY
                val maxY = (stock?.py?.plus(stock.y)) ?: bounds.maxY
                val minZ = (stock?.pz?.minus(stock.z)) ?: bounds.minZ
                val maxZ = (stock?.pz) ?: bounds.maxZ

                val sceneW = max(abs(maxX - minX), 20.0).toFloat()
                val sceneH = max(abs(maxY - minY), 20.0).toFloat()
                val sceneD = max(abs(maxZ - minZ), 10.0).toFloat()
                val maxDim = maxOf(sceneW, sceneH, sceneD).coerceAtLeast(10f)

                val safeZoom = if (cameraState.zoom.isFinite() && cameraState.zoom > 0f) cameraState.zoom else 1.0f
                val baseScale = ((minOf(w, h) * 0.65f) / maxDim * safeZoom).coerceAtLeast(0.01f)
                val targetX = ((minX + maxX) / 2.0).toFloat()
                val targetY = ((minY + maxY) / 2.0).toFloat()
                val targetZ = ((minZ + maxZ) / 2.0).toFloat()

                val safeAz = if (cameraState.azimuth.isFinite()) cameraState.azimuth else -35f
                val safeEl = if (cameraState.elevation.isFinite()) cameraState.elevation else 32f

                val azRad = Math.toRadians(safeAz.toDouble())
                val elRad = Math.toRadians(safeEl.toDouble())
                val cosAz = cos(azRad).toFloat()
                val sinAz = sin(azRad).toFloat()
                val cosEl = cos(elRad).toFloat()
                val sinEl = sin(elRad).toFloat()

                // Robust projection with strict NaN/Infinity guards
                fun project(x: Double, y: Double, z: Double): Offset {
                    if (!x.isFinite() || !y.isFinite() || !z.isFinite()) return Offset.Zero
                    val dx = (x.toFloat() - targetX) * baseScale
                    val dy = (y.toFloat() - targetY) * baseScale
                    val dz = (z.toFloat() - targetZ) * baseScale

                    val rx = dx * cosAz - dy * sinAz
                    val ry = dx * sinAz + dy * cosAz
                    val rz = dz

                    val screenX = rx
                    val screenY = -ry * sinEl - rz * cosEl

                    val resX = cx + screenX
                    val resY = cy + screenY
                    return if (resX.isFinite() && resY.isFinite()) Offset(resX, resY) else Offset.Zero
                }

                // 1. Draw Background Grid plane
                drawGridPlane(
                    minX = minX.toFloat(), maxX = maxX.toFloat(),
                    minY = minY.toFloat(), maxY = maxY.toFloat(),
                    z = minZ.toFloat(),
                    project = { x, y, z -> project(x.toDouble(), y.toDouble(), z.toDouble()) }
                )

                // 2. Draw Stock Box / Milled Material (HeightMap)
                if (stock != null && stock.visible) {
                    if (showMaterial && heightMap != null) {
                        drawMilledHeightmap(
                            hm = heightMap,
                            stock = stock,
                            shadingMode = shadingMode,
                            transparency = transparency,
                            reusablePath = reusablePath,
                            project = { x, y, z -> project(x, y, z) }
                        )
                    } else {
                        drawStockBox(
                            stock = stock,
                            transparency = transparency,
                            shadingMode = shadingMode,
                            reusablePath = reusablePath,
                            project = { x, y, z -> project(x.toDouble(), y.toDouble(), z.toDouble()) }
                        )
                    }
                }

                // 3. Draw Toolpath Segments safely up to current step
                if (showToolpath && segments.isNotEmpty()) {
                    val safeSegs = segments.toList()
                    val activeLimit = if (currentStepIndex in safeSegs.indices) currentStepIndex else safeSegs.size - 1

                    for (i in 0..activeLimit.coerceAtMost(safeSegs.size - 1)) {
                        val s = safeSegs[i]
                        val p0 = project(s.x0, s.y0, s.z0)
                        val p1 = project(s.x1, s.y1, s.z1)
                        if (!p0.isValid() || !p1.isValid()) continue

                        if (s.rapid) {
                            drawLine(
                                color = if (s.collision) Color(0xFFEF4444) else Color(0xFF38BDF8),
                                start = p0,
                                end = p1,
                                strokeWidth = if (s.collision) 3.5f else 1.8f,
                                pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f), 0f)
                            )
                        } else if (s.arc) {
                            drawArcSegment(
                                seg = s,
                                project = { x, y, z -> project(x, y, z) }
                            )
                        } else {
                            val color = parseHexColor(s.toolColor, Color(0xFF38BDF8))
                            drawLine(
                                color = if (s.collision) Color(0xFFEF4444) else color,
                                start = p0,
                                end = p1,
                                strokeWidth = 3.5f,
                                cap = StrokeCap.Round
                            )
                        }

                        if (s.collision) {
                            drawCircle(
                                color = Color(0xFFEF4444),
                                radius = 9f,
                                center = p1,
                                style = Stroke(width = 3f)
                            )
                        }
                    }

                    // Draw Tool Cutter at active step position
                    val activeSeg = safeSegs.getOrNull(activeLimit)
                    if (activeSeg != null) {
                        drawToolCutter(
                            x = activeSeg.x1,
                            y = activeSeg.y1,
                            z = activeSeg.z1,
                            toolD = activeSeg.toolD,
                            toolColor = parseHexColor(activeSeg.toolColor, Color(0xFFFBBF24)),
                            baseScale = baseScale,
                            project = { x, y, z -> project(x, y, z) }
                        )
                    }
                }

                // 4. Draw Origin Coordinate Axes (0,0,0)
                drawAxes(
                    project = { x, y, z -> project(x.toDouble(), y.toDouble(), z.toDouble()) },
                    axisLen = (maxDim * 0.25f).coerceAtLeast(15f),
                    textMeasurer = textMeasurer
                )

                // 5. Mini Triad
                drawMiniTriad(
                    azimuth = safeAz,
                    elevation = safeEl,
                    origin = Offset(36f, 36f)
                )
            } catch (_: Exception) {
                // Safeguard against Skia rendering anomalies during sudden orientation/pinch shifts
            }
        }

        // Top Toolbar Overlay (Full Touch Control: Shading, Material, Grid, Transparency)
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            shape = RoundedCornerShape(12.dp),
            color = Color(0xDD1E293B),
            tonalElevation = 6.dp
        ) {
            Column(modifier = Modifier.padding(6.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Display toggles: Toolpath & Material (Milling)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FilterChip(
                            selected = showToolpath,
                            onClick = { onToggleToolpath(!showToolpath) },
                            label = { Text("Путь", fontSize = 11.sp) },
                            leadingIcon = {
                                Icon(Icons.Default.Timeline, contentDescription = null, modifier = Modifier.size(14.dp))
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Color(0xFF0284C7),
                                selectedLabelColor = Color.White
                            ),
                            modifier = Modifier.height(32.dp)
                        )

                        Spacer(modifier = Modifier.width(6.dp))

                        FilterChip(
                            selected = showMaterial,
                            onClick = { onToggleMaterial(!showMaterial) },
                            label = { Text("Фрезерование", fontSize = 11.sp) },
                            leadingIcon = {
                                Icon(Icons.Default.Layers, contentDescription = null, modifier = Modifier.size(14.dp))
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Color(0xFF059669),
                                selectedLabelColor = Color.White
                            ),
                            modifier = Modifier.height(32.dp)
                        )
                    }

                    // Shading & Camera Presets
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(
                            onClick = { showQuickSettings = !showQuickSettings },
                            modifier = Modifier.size(34.dp)
                        ) {
                            Icon(
                                Icons.Default.Tune,
                                contentDescription = "Настройка вида",
                                tint = if (showQuickSettings) Color(0xFF38BDF8) else Color.White,
                                modifier = Modifier.size(18.dp)
                            )
                        }

                        IconButton(
                            onClick = { cameraState.setTop() },
                            modifier = Modifier.size(34.dp)
                        ) {
                            Text("XY", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                        }
                        IconButton(
                            onClick = { cameraState.setIsometric() },
                            modifier = Modifier.size(34.dp)
                        ) {
                            Icon(Icons.Default.ViewInAr, contentDescription = "3D", tint = Color.White, modifier = Modifier.size(18.dp))
                        }
                        IconButton(
                            onClick = { cameraState.reset() },
                            modifier = Modifier.size(34.dp)
                        ) {
                            Icon(Icons.Default.CenterFocusStrong, contentDescription = "Сброс", tint = Color.White, modifier = Modifier.size(18.dp))
                        }
                    }
                }

                // Expandable Shading, Grid Cell Size & Transparency Controls
                if (showQuickSettings) {
                    Spacer(modifier = Modifier.height(6.dp))
                    HorizontalDivider(color = Color(0xFF334155), thickness = 1.dp)
                    Spacer(modifier = Modifier.height(6.dp))

                    // Row 1: Shading Mode + Transparency
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Режим:", color = Color(0xFF94A3B8), fontSize = 11.sp)
                            Spacer(modifier = Modifier.width(4.dp))

                            val modes = listOf(
                                Triple(ShadingMode.SOLID, "Сплошной", Icons.Default.Square),
                                Triple(ShadingMode.WIREFRAME, "Сетка", Icons.Default.GridOn),
                                Triple(ShadingMode.TRANSPARENT, "Прозр.", Icons.Default.Opacity)
                            )
                            for ((m, label, icon) in modes) {
                                val isSel = shadingMode == m
                                Box(
                                    modifier = Modifier
                                        .padding(horizontal = 2.dp)
                                        .background(
                                            if (isSel) Color(0xFF0284C7) else Color(0xFF0F172A),
                                            RoundedCornerShape(6.dp)
                                        )
                                        .clickable { onChangeShadingMode(m) }
                                        .padding(horizontal = 5.dp, vertical = 4.dp)
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(icon, contentDescription = null, tint = if (isSel) Color.White else Color(0xFF94A3B8), modifier = Modifier.size(11.dp))
                                        Spacer(modifier = Modifier.width(3.dp))
                                        Text(label, color = if (isSel) Color.White else Color(0xFF94A3B8), fontSize = 10.sp)
                                    }
                                }
                            }
                        }

                        // Transparency Slider
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Прозр.: ${(transparency * 100).toInt()}%", color = Color(0xFFCBD5E1), fontSize = 10.sp)
                            Spacer(modifier = Modifier.width(2.dp))
                            Slider(
                                value = transparency,
                                onValueChange = onChangeTransparency,
                                valueRange = 0.15f..1.0f,
                                modifier = Modifier.width(80.dp),
                                colors = SliderDefaults.colors(
                                    thumbColor = Color(0xFF38BDF8),
                                    activeTrackColor = Color(0xFF0284C7)
                                )
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    // Row 2: Grid Cell Size / Detail Tuning (Requirement 3)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Ячейка сетки:", color = Color(0xFF94A3B8), fontSize = 11.sp)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "%.1f мм".format(gridSizeMm),
                                color = Color(0xFF38BDF8),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        // Grid Presets: 0.5mm (Ultra), 1.0mm (High), 1.5mm (Default), 3.0mm (Fast)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val gridPresets = listOf(
                                Pair(0.5, "0.5"),
                                Pair(1.0, "1.0"),
                                Pair(1.5, "1.5"),
                                Pair(3.0, "3.0")
                            )
                            for ((sizeMm, label) in gridPresets) {
                                val isSelected = abs(gridSizeMm - sizeMm) < 0.1
                                Box(
                                    modifier = Modifier
                                        .padding(horizontal = 2.dp)
                                        .background(
                                            if (isSelected) Color(0xFF059669) else Color(0xFF0F172A),
                                            RoundedCornerShape(4.dp)
                                        )
                                        .clickable { onChangeGridSize(sizeMm) }
                                        .padding(horizontal = 5.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = "$label мм",
                                        color = if (isSelected) Color.White else Color(0xFF94A3B8),
                                        fontSize = 10.sp
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // Coordinates HUD at bottom-left
        val activeSeg = segments.getOrNull(if (currentStepIndex in segments.indices) currentStepIndex else segments.size - 1)
        Surface(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(8.dp),
            shape = RoundedCornerShape(8.dp),
            color = Color(0xB30F172A)
        ) {
            Column(modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)) {
                if (activeSeg != null) {
                    Text(
                        text = "X: %6.2f  Y: %6.2f  Z: %6.2f".format(activeSeg.x1, activeSeg.y1, activeSeg.z1),
                        color = Color(0xFFF1F5F9),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "Фреза: D%.1f мм • %s".format(activeSeg.toolD, if (activeSeg.rapid) "G0 Ускоренный" else "G1 Подача"),
                        color = if (activeSeg.rapid) Color(0xFF38BDF8) else Color(0xFF4ADE80),
                        fontSize = 10.sp
                    )
                } else {
                    Text("Координаты: X: 0.00  Y: 0.00  Z: 0.00", color = Color(0xFF94A3B8), fontSize = 11.sp)
                }
            }
        }
    }
}

private fun Offset.isValid(): Boolean = x.isFinite() && y.isFinite()

private fun DrawScope.drawGridPlane(
    minX: Float, maxX: Float,
    minY: Float, maxY: Float,
    z: Float,
    project: (Float, Float, Float) -> Offset
) {
    val step = max(10f, ceil((maxX - minX) / 10f / 5f) * 5f)
    val gridColor = Color(0x2264748B)

    var curX = floor(minX / step) * step
    while (curX <= maxX) {
        val p0 = project(curX, minY, z)
        val p1 = project(curX, maxY, z)
        if (p0.isValid() && p1.isValid()) {
            drawLine(gridColor, p0, p1, strokeWidth = 1f)
        }
        curX += step
    }

    var curY = floor(minY / step) * step
    while (curY <= maxY) {
        val p0 = project(minX, curY, z)
        val p1 = project(maxX, curY, z)
        if (p0.isValid() && p1.isValid()) {
            drawLine(gridColor, p0, p1, strokeWidth = 1f)
        }
        curY += step
    }
}

private fun DrawScope.drawAxes(
    project: (Float, Float, Float) -> Offset,
    axisLen: Float,
    textMeasurer: TextMeasurer
) {
    val o = project(0f, 0f, 0f)
    val x = project(axisLen, 0f, 0f)
    val y = project(0f, axisLen, 0f)
    val z = project(0f, 0f, axisLen)

    if (o.isValid() && x.isValid()) {
        drawLine(Color(0xFFEF4444), o, x, strokeWidth = 3f)
        drawText(textMeasurer, "X", x + Offset(4f, -8f), style = TextStyle(color = Color(0xFFEF4444), fontSize = 12.sp, fontWeight = FontWeight.Bold))
    }

    if (o.isValid() && y.isValid()) {
        drawLine(Color(0xFF22C55E), o, y, strokeWidth = 3f)
        drawText(textMeasurer, "Y", y + Offset(4f, -8f), style = TextStyle(color = Color(0xFF22C55E), fontSize = 12.sp, fontWeight = FontWeight.Bold))
    }

    if (o.isValid() && z.isValid()) {
        drawLine(Color(0xFF3B82F6), o, z, strokeWidth = 3f)
        drawText(textMeasurer, "Z", z + Offset(4f, -8f), style = TextStyle(color = Color(0xFF3B82F6), fontSize = 12.sp, fontWeight = FontWeight.Bold))
    }
}

private fun DrawScope.drawStockBox(
    stock: Stock,
    transparency: Float,
    shadingMode: ShadingMode,
    reusablePath: Path,
    project: (Float, Float, Float) -> Offset
) {
    val x0 = stock.px.toFloat()
    val y0 = stock.py.toFloat()
    val z0 = (stock.pz - stock.z).toFloat()
    val x1 = (stock.px + stock.x).toFloat()
    val y1 = (stock.py + stock.y).toFloat()
    val z1 = stock.pz.toFloat()

    val corners = arrayOf(
        project(x0, y0, z0),
        project(x1, y0, z0),
        project(x1, y1, z0),
        project(x0, y1, z0),
        project(x0, y0, z1),
        project(x1, y0, z1),
        project(x1, y1, z1),
        project(x0, y1, z1)
    )

    if (corners.all { it.isValid() }) {
        if (shadingMode != ShadingMode.WIREFRAME) {
            val alpha = if (shadingMode == ShadingMode.TRANSPARENT) transparency.coerceIn(0.15f, 0.85f) else 0.85f
            val stockColor = parseHexColor(stock.color, Color(0xFF7080B0)).copy(alpha = alpha)

            reusablePath.rewind()
            reusablePath.moveTo(corners[4].x, corners[4].y)
            reusablePath.lineTo(corners[5].x, corners[5].y)
            reusablePath.lineTo(corners[6].x, corners[6].y)
            reusablePath.lineTo(corners[7].x, corners[7].y)
            reusablePath.close()
            drawPath(reusablePath, color = stockColor)
        }

        val strokeColor = if (shadingMode == ShadingMode.WIREFRAME) Color(0xFF38BDF8) else Color(0x9994A3B8)
        val edges = arrayOf(
            Pair(0, 1), Pair(1, 2), Pair(2, 3), Pair(3, 0),
            Pair(4, 5), Pair(5, 6), Pair(6, 7), Pair(7, 4),
            Pair(0, 4), Pair(1, 5), Pair(2, 6), Pair(3, 7)
        )
        for ((a, b) in edges) {
            drawLine(strokeColor, corners[a], corners[b], strokeWidth = if (shadingMode == ShadingMode.WIREFRAME) 1.8f else 1.2f)
        }
    }
}

/**
 * Robust 3D Milled Workpiece HeightMap renderer with zero allocation during rotation
 */
private fun DrawScope.drawMilledHeightmap(
    hm: HeightMap,
    stock: Stock,
    shadingMode: ShadingMode,
    transparency: Float,
    reusablePath: Path,
    project: (Double, Double, Double) -> Offset
) {
    val zTop = hm.zTop
    val zBot = hm.zBottom
    val curZ = hm.curZ
    val nx = minOf(hm.nx, curZ.size)
    val ny = minOf(hm.ny, curZ.firstOrNull()?.size ?: 0)
    if (nx <= 1 || ny <= 1) return

    val dx = hm.dx
    val dy = hm.dy
    val x0 = hm.xMin
    val y0 = hm.yMin

    val step = if (nx > 45) 2 else 1
    val isWireframe = shadingMode == ShadingMode.WIREFRAME
    val alpha = if (shadingMode == ShadingMode.TRANSPARENT) transparency.coerceIn(0.15f, 0.85f) else 0.90f

    val uncutColor = parseHexColor(stock.color, Color(0xFF7080B0)).copy(alpha = alpha)
    val gridLineColor = if (isWireframe) Color(0xFF38BDF8) else Color(0x4464748B)

    // 1. Draw Stock bounding contours
    val p00Bot = project(x0, y0, zBot)
    val p10Bot = project(x0 + nx * dx, y0, zBot)
    val p11Bot = project(x0 + nx * dx, y0 + ny * dy, zBot)
    val p01Bot = project(x0, y0 + ny * dy, zBot)

    val p00Top = project(x0, y0, zTop)
    val p10Top = project(x0 + nx * dx, y0, zTop)
    val p11Top = project(x0 + nx * dx, y0 + ny * dy, zTop)
    val p01Top = project(x0, y0 + ny * dy, zTop)

    if (p00Bot.isValid() && p10Bot.isValid()) drawLine(Color(0x6694A3B8), p00Bot, p10Bot, strokeWidth = 1.2f)
    if (p10Bot.isValid() && p11Bot.isValid()) drawLine(Color(0x6694A3B8), p10Bot, p11Bot, strokeWidth = 1.2f)
    if (p11Bot.isValid() && p01Bot.isValid()) drawLine(Color(0x6694A3B8), p11Bot, p01Bot, strokeWidth = 1.2f)
    if (p01Bot.isValid() && p00Bot.isValid()) drawLine(Color(0x6694A3B8), p01Bot, p00Bot, strokeWidth = 1.2f)

    if (p00Bot.isValid() && p00Top.isValid()) drawLine(Color(0x6694A3B8), p00Bot, p00Top, strokeWidth = 1.2f)
    if (p10Bot.isValid() && p10Top.isValid()) drawLine(Color(0x6694A3B8), p10Bot, p10Top, strokeWidth = 1.2f)
    if (p11Bot.isValid() && p11Top.isValid()) drawLine(Color(0x6694A3B8), p11Bot, p11Top, strokeWidth = 1.2f)
    if (p01Bot.isValid() && p01Top.isValid()) drawLine(Color(0x6694A3B8), p01Bot, p01Top, strokeWidth = 1.2f)

    // 2. Draw 3D Surface grid and milled facets
    val maxIx = (nx - step).coerceAtLeast(0)
    val maxIy = (ny - step).coerceAtLeast(0)

    for (ix in 0 until maxIx step step) {
        val px = x0 + ix * dx
        val pxNext = x0 + (ix + step) * dx

        for (iy in 0 until maxIy step step) {
            val py = y0 + iy * dy
            val pyNext = y0 + (iy + step) * dy

            val z00 = curZ[ix][iy]
            val z10 = curZ[ix + step][iy]
            val z11 = curZ[ix + step][iy + step]
            val z01 = curZ[ix][iy + step]

            val pt00 = project(px, py, z00)
            val pt10 = project(pxNext, py, z10)
            val pt11 = project(pxNext, pyNext, z11)
            val pt01 = project(px, pyNext, z01)

            if (!pt00.isValid() || !pt10.isValid() || !pt11.isValid() || !pt01.isValid()) continue

            val isCut = (z00 < zTop - 0.05 || z10 < zTop - 0.05 || z11 < zTop - 0.05 || z01 < zTop - 0.05)

            if (!isWireframe) {
                reusablePath.rewind()
                reusablePath.moveTo(pt00.x, pt00.y)
                reusablePath.lineTo(pt10.x, pt10.y)
                reusablePath.lineTo(pt11.x, pt11.y)
                reusablePath.lineTo(pt01.x, pt01.y)
                reusablePath.close()

                val cellColor = if (isCut) {
                    val minLocalZ = minOf(z00, z10, z11, z01)
                    val depthFrac = (((zTop - minLocalZ) / max(0.1, zTop - zBot)).toFloat()).coerceIn(0f, 1f)
                    Color(
                        red = (0.85f - depthFrac * 0.35f).coerceIn(0f, 1f),
                        green = (0.88f - depthFrac * 0.30f).coerceIn(0f, 1f),
                        blue = (0.95f - depthFrac * 0.20f).coerceIn(0f, 1f),
                        alpha = alpha
                    )
                } else {
                    uncutColor
                }

                drawPath(reusablePath, cellColor)
            }

            // Grid mesh lines (always on in Wireframe, or subtle on milled areas)
            if (isWireframe || isCut) {
                val lineCol = if (isCut) Color(0xFF0284C7) else gridLineColor
                val lw = if (isCut) 1.5f else 0.9f
                drawLine(lineCol, pt00, pt10, strokeWidth = lw)
                drawLine(lineCol, pt00, pt01, strokeWidth = lw)
            }
        }
    }
}

private fun DrawScope.drawArcSegment(
    seg: Segment,
    project: (Double, Double, Double) -> Offset
) {
    val r = hypot(seg.x0 - seg.cx, seg.y0 - seg.cy)
    if (r < 1e-4 || !r.isFinite()) return
    val a0 = atan2(seg.y0 - seg.cy, seg.x0 - seg.cx)
    var a1 = atan2(seg.y1 - seg.cy, seg.x1 - seg.cx)
    if (!a0.isFinite() || !a1.isFinite()) return

    var da = a1 - a0
    if (seg.cw) {
        while (da > 0) da -= 2 * Math.PI
    } else {
        while (da < 0) da += 2 * Math.PI
    }

    val n = 16
    var prevP = project(seg.x0, seg.y0, seg.z0)
    val color = parseHexColor(seg.toolColor, Color(0xFF38BDF8))

    for (k in 1..n) {
        val t = k.toDouble() / n
        val a = a0 + da * t
        val curX = seg.cx + r * cos(a)
        val curY = seg.cy + r * sin(a)
        val curZ = seg.z0 + (seg.z1 - seg.z0) * t
        val curP = project(curX, curY, curZ)
        if (prevP.isValid() && curP.isValid()) {
            drawLine(color, prevP, curP, strokeWidth = 3.5f, cap = StrokeCap.Round)
        }
        prevP = curP
    }
}

private fun DrawScope.drawToolCutter(
    x: Double, y: Double, z: Double,
    toolD: Double,
    toolColor: Color,
    baseScale: Float,
    project: (Double, Double, Double) -> Offset
) {
    val tip = project(x, y, z)
    val top = project(x, y, z + 12.0)

    if (tip.isValid() && top.isValid()) {
        drawLine(
            color = toolColor,
            start = tip,
            end = top,
            strokeWidth = (toolD.toFloat() * baseScale * 0.5f).coerceIn(4f, 20f),
            cap = StrokeCap.Round
        )

        drawCircle(
            color = Color(0xFFF59E0B),
            radius = 4.5f,
            center = tip
        )
    }
}

private fun DrawScope.drawMiniTriad(azimuth: Float, elevation: Float, origin: Offset) {
    val azRad = Math.toRadians(azimuth.toDouble())
    val elRad = Math.toRadians(elevation.toDouble())
    val len = 24f

    fun triadProj(x: Float, y: Float, z: Float): Offset {
        val cosAz = cos(azRad).toFloat()
        val sinAz = sin(azRad).toFloat()
        val cosEl = cos(elRad).toFloat()
        val sinEl = sin(elRad).toFloat()

        val rx = x * cosAz - y * sinAz
        val ry = x * sinAz + y * cosAz
        val rz = z

        val sx = rx
        val sy = -ry * sinEl - rz * cosEl
        val rxRes = origin.x + sx * len
        val ryRes = origin.y + sy * len
        return if (rxRes.isFinite() && ryRes.isFinite()) Offset(rxRes, ryRes) else origin
    }

    val px = triadProj(1f, 0f, 0f)
    val py = triadProj(0f, 1f, 0f)
    val pz = triadProj(0f, 0f, 1f)

    if (px.isValid()) drawLine(Color(0xFFEF4444), origin, px, strokeWidth = 3f)
    if (py.isValid()) drawLine(Color(0xFF22C55E), origin, py, strokeWidth = 3f)
    if (pz.isValid()) drawLine(Color(0xFF3B82F6), origin, pz, strokeWidth = 3f)
}

private fun parseHexColor(hex: String?, defaultColor: Color): Color {
    if (hex.isNullOrBlank()) return defaultColor
    return try {
        val clean = hex.removePrefix("#")
        val colorInt = clean.toLong(16)
        if (clean.length == 6) {
            Color((0xFF000000 or colorInt).toInt())
        } else {
            Color(colorInt.toInt())
        }
    } catch (_: Exception) {
        defaultColor
    }
}
