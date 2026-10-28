package com.example.model

enum class ShadingMode {
    SOLID,       // Сплошной с затенением
    WIREFRAME,   // Режим сетки / каркас
    TRANSPARENT  // Полупрозрачный
}

data class Segment(
    val x0: Double,
    val y0: Double,
    val z0: Double,
    val x1: Double,
    val y1: Double,
    val z1: Double,
    val toolD: Double,
    val toolColor: String,
    val rapid: Boolean,
    val arc: Boolean = false,
    val cx: Double = 0.0,
    val cy: Double = 0.0,
    val cw: Boolean = true,
    val drill: Boolean = false,
    var collision: Boolean = false,
    var collisionReason: String = "",
    val spindleOn: Boolean = true,
    val cmdIndex: Int = -1,
    val executedIndex: Int = -1
)

data class CollisionInfo(
    val cmdIndex: Int,
    val reason: String,
    val x: Double,
    val y: Double,
    val z: Double
)

data class SimulationStats(
    val cutLen: Double = 0.0,
    val rapidLen: Double = 0.0,
    val zMin: Double = 0.0,
    val collisionCount: Int = 0,
    val collisions: List<CollisionInfo> = emptyList(),
    val executedSteps: Int = 0,
    val estTimeMinutes: Double = 0.0,
    val removedVolumeCm3: Double = 0.0,
    val a: Double = 0.0,
    val b: Double = 0.0,
    val c: Double = 0.0
)

data class SimSettings(
    val autoVoxelXy: Boolean = true,
    val voxelXy: Double = 1.5,
    val voxelZ: Double = 1.0,
    val showToolpath: Boolean = true,
    val showMaterial: Boolean = true,
    val shadingMode: ShadingMode = ShadingMode.SOLID,
    val transparency: Float = 0.45f,
    val rapidLineWidth: Float = 1.5f,
    val feedLineWidth: Float = 3.5f,
    val rapidDash: Boolean = true,
    val ignoreRapidInMaterial: Boolean = false,
    val unrollLoops: Boolean = false,
    val stepLimit: Int = 0
)

data class Bounds3D(
    val minX: Double = -10.0,
    val minY: Double = -10.0,
    val minZ: Double = -10.0,
    val maxX: Double = 100.0,
    val maxY: Double = 100.0,
    val maxZ: Double = 20.0
)
