package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.CommandsDef
import com.example.core.FormulaEval
import com.example.core.GCodeGenerator
import com.example.core.GCodeParser
import com.example.model.*
import com.example.sim.Simulator
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class MainViewModel(application: Application) : AndroidViewModel(application) {

    // Main program state
    val tools = MutableStateFlow<List<Tool>>(listOf(
        Tool(1, "End mill 3мм", 3.0, 200.0, 8000, "#38BDF8"),
        Tool(2, "Drill 5мм", 5.0, 80.0, 4000, "#F59E0B")
    ))

    val variables = MutableStateFlow<List<UserVar>>(listOf(
        UserVar("W", "60"),
        UserVar("L", "100"),
        UserVar("STEP", "5"),
        UserVar("PASS", "{W//STEP + 1}"),
        UserVar("DEPTH", "-1")
    ))

    val stock = MutableStateFlow(
        Stock(mode = "box", x = 100.0, y = 120.0, z = 15.0, px = 0.0, py = 0.0, pz = 0.0, color = "#7080B0", visible = true)
    )

    val commands = MutableStateFlow<List<Command>>(emptyList())

    val functions = MutableStateFlow<List<FunctionDef>>(CommandsDef.buildSeedFunctions())

    val preamble = MutableStateFlow<List<Command>>(listOf(
        Command("UNITS_MM"),
        Command("ABS"),
        Command("PLANE_XY")
    ))

    val postamble = MutableStateFlow<List<Command>>(listOf(
        Command("SPIN", mapOf("on" to 0)),
        Command("COOL", mapOf("on" to 0)),
        Command("RAPID", mapOf("z" to 20.0)),
        Command("END")
    ))

    val settings = MutableStateFlow(SimSettings())

    val gcodeLines = MutableStateFlow<List<String>>(emptyList())
    val simulationSegments = MutableStateFlow<List<Segment>>(emptyList())
    val simulationBounds = MutableStateFlow(Bounds3D())
    val simulationStats = MutableStateFlow(SimulationStats())
    val collisionIndices = MutableStateFlow<Set<Int>>(emptySet())
    val evaluatedVars = MutableStateFlow<Map<String, Double>>(emptyMap())
    val heightMap = MutableStateFlow<com.example.sim.HeightMap?>(null)

    // Selection & Playback
    val selectedCommandIndex = MutableStateFlow(0)
    val currentStepIndex = MutableStateFlow(0)
    val isPlaying = MutableStateFlow(false)
    val speedMultiplier = MutableStateFlow(1.0f)

    private var fullHeightMap: com.example.sim.HeightMap? = null
    private var playbackJob: Job? = null

    init {
        loadDemoProject()
    }

    fun recalculate() {
        viewModelScope.launch {
            val currentVars = variables.value
            val (env, _) = FormulaEval.buildEnv(currentVars)
            evaluatedVars.value = env

            val curCommands = commands.value
            val curTools = tools.value
            val curSettings = settings.value

            // 1. Generate G-Code
            try {
                val gen = GCodeGenerator(
                    toolsList = curTools,
                    variables = env,
                    unrollLoops = curSettings.unrollLoops,
                    functionsList = functions.value,
                    preamble = preamble.value,
                    postamble = postamble.value
                )
                gcodeLines.value = gen.generate(curCommands)
            } catch (e: Exception) {
                gcodeLines.value = listOf("%", "(Ошибка генератора: ${e.message})", "%")
            }

            // 2. Run 3D Simulator
            try {
                val sim = Simulator(
                    toolsList = curTools,
                    variables = env,
                    stock = stock.value,
                    settings = curSettings,
                    functionsList = functions.value,
                    preamble = preamble.value,
                    postamble = postamble.value
                )
                val upto = if (selectedCommandIndex.value in curCommands.indices) {
                    selectedCommandIndex.value + 1
                } else {
                    curCommands.size
                }

                val result = sim.trace(
                    commands = curCommands,
                    upto = upto,
                    checkCollisions = true,
                    stepLimit = if (curSettings.stepLimit > 0) curSettings.stepLimit else null
                )

                simulationSegments.value = result.segments
                simulationBounds.value = result.bounds
                simulationStats.value = result.stats
                collisionIndices.value = result.stats.collisions.map { it.cmdIndex }.toSet()
                fullHeightMap = result.heightMap
                heightMap.value = result.heightMap

                // sync playback step
                if (currentStepIndex.value >= result.segments.size) {
                    currentStepIndex.value = maxOf(0, result.segments.size - 1)
                }
            } catch (e: Exception) {
                simulationSegments.value = emptyList()
                heightMap.value = null
            }
        }
    }

    fun selectCommand(index: Int) {
        selectedCommandIndex.value = index
        recalculate()
    }

    fun addCommand(cmd: Command) {
        val list = commands.value.toMutableList()
        val cur = selectedCommandIndex.value
        val insertAt = if (cur in list.indices) cur + 1 else list.size
        list.add(insertAt, cmd)
        commands.value = list
        selectedCommandIndex.value = insertAt
        recalculate()
    }

    fun editCommand(index: Int, cmd: Command) {
        if (index in commands.value.indices) {
            val list = commands.value.toMutableList()
            list[index] = cmd
            commands.value = list
            recalculate()
        }
    }

    fun deleteCommand(index: Int) {
        if (index in commands.value.indices) {
            val list = commands.value.toMutableList()
            list.removeAt(index)
            commands.value = list
            selectedCommandIndex.value = (index - 1).coerceAtLeast(0)
            recalculate()
        }
    }

    fun moveCommand(index: Int, delta: Int) {
        val list = commands.value.toMutableList()
        val target = index + delta
        if (index in list.indices && target in list.indices) {
            val item = list.removeAt(index)
            list.add(target, item)
            commands.value = list
            selectedCommandIndex.value = target
            recalculate()
        }
    }

    fun duplicateCommand(index: Int) {
        if (index in commands.value.indices) {
            val list = commands.value.toMutableList()
            list.add(index + 1, list[index].copy())
            commands.value = list
            selectedCommandIndex.value = index + 1
            recalculate()
        }
    }

    // Playback controls
    fun togglePlayPause() {
        if (isPlaying.value) {
            pausePlayback()
        } else {
            startPlayback()
        }
    }

    fun startPlayback() {
        val total = simulationSegments.value.size
        if (total == 0) return
        if (currentStepIndex.value >= total - 1) {
            currentStepIndex.value = 0
            updateHeightMapForStep(0)
        }
        isPlaying.value = true
        playbackJob?.cancel()
        playbackJob = viewModelScope.launch {
            while (isPlaying.value && currentStepIndex.value < simulationSegments.value.size - 1) {
                val delayMs = (50f / speedMultiplier.value).toLong().coerceAtLeast(10L)
                delay(delayMs)
                val nextStep = currentStepIndex.value + 1
                currentStepIndex.value = nextStep
                updateHeightMapForStep(nextStep)
            }
            isPlaying.value = false
        }
    }

    fun pausePlayback() {
        isPlaying.value = false
        playbackJob?.cancel()
    }

    fun setStepIndex(step: Int) {
        pausePlayback()
        val total = simulationSegments.value.size
        val targetStep = step.coerceIn(0, maxOf(0, total - 1))
        currentStepIndex.value = targetStep
        updateHeightMapForStep(targetStep)
    }

    fun rewind() {
        pausePlayback()
        currentStepIndex.value = 0
        updateHeightMapForStep(0)
    }

    fun fastForward() {
        pausePlayback()
        val total = simulationSegments.value.size
        currentStepIndex.value = maxOf(0, total - 1)
        heightMap.value = fullHeightMap
    }

    private fun updateHeightMapForStep(step: Int) {
        val st = stock.value
        val segs = simulationSegments.value
        if (segs.isEmpty() || fullHeightMap == null) {
            heightMap.value = fullHeightMap
            return
        }
        if (step >= segs.size - 1) {
            heightMap.value = fullHeightMap
            return
        }
        val b = st.bounds()
        val hm = com.example.sim.HeightMap(
            b[0], b[1], b[2], b[3], b[4], b[5],
            voxelXy = if (settings.value.autoVoxelXy) 1.5 else settings.value.voxelXy,
            voxelZ = settings.value.voxelZ
        )
        for (i in 0..step.coerceIn(0, segs.size - 1)) {
            val s = segs[i]
            if (s.spindleOn && !s.collision) {
                val radius = s.toolD / 2.0
                if (s.drill) {
                    hm.cutDrill(s.x1, s.y1, s.z0, s.z1, radius)
                } else if (s.arc) {
                    hm.cutArc(
                        s.cx, s.cy, kotlin.math.hypot(s.x0 - s.cx, s.y0 - s.cy),
                        kotlin.math.atan2(s.y0 - s.cy, s.x0 - s.cx),
                        kotlin.math.atan2(s.y1 - s.cy, s.x1 - s.cx),
                        s.z0, s.z1, radius, s.cw
                    )
                } else if (!s.rapid) {
                    hm.cutLine(s.x0, s.y0, s.z0, s.x1, s.y1, s.z1, radius)
                }
            }
        }
        heightMap.value = hm
    }

    fun updateShadingMode(mode: ShadingMode) {
        settings.value = settings.value.copy(shadingMode = mode)
    }

    fun updateTransparency(transparency: Float) {
        settings.value = settings.value.copy(transparency = transparency)
    }

    fun toggleShowToolpath(show: Boolean) {
        settings.value = settings.value.copy(showToolpath = show)
    }

    fun toggleShowMaterial(show: Boolean) {
        settings.value = settings.value.copy(showMaterial = show)
    }

    fun updateGridSize(sizeMm: Double) {
        settings.value = settings.value.copy(voxelXy = sizeMm.coerceIn(0.3, 10.0), autoVoxelXy = false)
        recalculate()
    }

    fun setSpeed(mult: Float) {
        speedMultiplier.value = mult
    }

    // Tools
    fun addTool(tool: Tool) {
        tools.value = tools.value + tool
        recalculate()
    }

    fun editTool(tool: Tool) {
        tools.value = tools.value.map { if (it.number == tool.number) tool else it }
        recalculate()
    }

    fun deleteTool(tool: Tool) {
        if (tools.value.size > 1) {
            tools.value = tools.value.filter { it.number != tool.number }
            recalculate()
        }
    }

    // Variables
    fun addVariable(v: UserVar) {
        variables.value = variables.value + v
        recalculate()
    }

    fun editVariable(v: UserVar) {
        variables.value = variables.value.map { if (it.name == v.name) v else it }
        recalculate()
    }

    fun deleteVariable(v: UserVar) {
        variables.value = variables.value.filter { it.name != v.name }
        recalculate()
    }

    // Stock
    fun updateStock(st: Stock) {
        stock.value = st
        recalculate()
    }

    // Settings
    fun updateSettings(st: SimSettings) {
        settings.value = st
        recalculate()
    }

    fun insertFunctionCall(fn: FunctionDef) {
        val p = mutableMapOf<String, Any>(
            "name" to fn.name,
            "mode" to "inline"
        )
        fn.params.forEach { prm ->
            p["p_${prm.name}"] = prm.defaultVal
        }
        addCommand(Command("CALL_FUNC", p))
    }

    fun newProject() {
        commands.value = emptyList()
        selectedCommandIndex.value = 0
        currentStepIndex.value = 0
        recalculate()
    }

    fun loadDemoProject() {
        tools.value = listOf(
            Tool(1, "End mill 3мм", 3.0, 200.0, 8000, "#38BDF8"),
            Tool(2, "Drill 5мм", 5.0, 80.0, 4000, "#F59E0B")
        )
        variables.value = listOf(
            UserVar("W", "60"),
            UserVar("L", "100"),
            UserVar("STEP", "5"),
            UserVar("PASS", "{W//STEP + 1}"),
            UserVar("DEPTH", "-1")
        )
        stock.value = Stock(
            mode = "box", x = 100.0, y = 120.0, z = 15.0, px = 0.0, py = 0.0, pz = 0.0, color = "#7080B0", visible = true
        )
        commands.value = listOf(
            Command("UNITS_MM"),
            Command("ABS"),
            Command("SPIN", mapOf("on" to 1, "rpm" to 8000, "ccw" to 0)),
            Command("TOOL", mapOf("tool" to 1)),
            Command("RAPID", mapOf("x" to 0.0, "y" to 0.0, "z" to 5.0)),
            Command("#", emptyMap(), "Фрезерование кармана зигзагом"),
            Command("VAR", mapOf("name" to "#200", "value" to "0")),
            Command("LABEL", mapOf("name" to "LOOP")),
            Command("RAPID", mapOf("x" to 0.0, "y" to "{#200*STEP}", "z" to 5.0)),
            Command("FEED", mapOf("x" to 0.0, "y" to "{#200*STEP}", "z" to "{DEPTH}", "f" to 150.0)),
            Command("FEED", mapOf("x" to "{L}", "y" to "{#200*STEP}", "z" to "{DEPTH}", "f" to 150.0)),
            Command("RAPID", mapOf("x" to "{L}", "y" to "{#200*STEP}", "z" to 5.0)),
            Command("VAR_ADD", mapOf("name" to "#200", "delta" to "1")),
            Command("IF", mapOf("lhs" to "#200", "op" to "LT", "rhs" to "{PASS}", "target" to "LOOP")),
            Command("#", emptyMap(), "Сверление центровочного отверстия"),
            Command("RAPID", mapOf("x" to "{W/2}", "y" to "{L/2}", "z" to 5.0)),
            Command("TOOL", mapOf("tool" to 2)),
            Command("DRILL", mapOf("x" to "{W/2}", "y" to "{L/2}", "z" to -8.0, "f" to 60.0)),
            Command("RAPID", mapOf("x" to 0.0, "y" to 0.0, "z" to 10.0)),
            Command("END")
        )
        selectedCommandIndex.value = commands.value.size - 1
        currentStepIndex.value = 0
        recalculate()
    }

    // Project Save / Load using JSON in app internal storage
    fun saveProjectToFile(filename: String = "last_project.gcp"): Boolean {
        return try {
            val root = JSONObject()
            val toolsArr = JSONArray()
            tools.value.forEach { t ->
                val o = JSONObject()
                o.put("number", t.number)
                o.put("name", t.name)
                o.put("diameter", t.diameter)
                o.put("feed", t.feed)
                o.put("rpm", t.rpm)
                o.put("color", t.color)
                toolsArr.put(o)
            }
            root.put("tools", toolsArr)

            val varsArr = JSONArray()
            variables.value.forEach { v ->
                val o = JSONObject()
                o.put("name", v.name)
                o.put("value", v.value)
                varsArr.put(o)
            }
            root.put("variables", varsArr)

            val st = stock.value
            val stObj = JSONObject()
            stObj.put("x", st.x); stObj.put("y", st.y); stObj.put("z", st.z)
            stObj.put("px", st.px); stObj.put("py", st.py); stObj.put("pz", st.pz)
            stObj.put("visible", st.visible); stObj.put("color", st.color)
            root.put("stock", stObj)

            val cmdsArr = JSONArray()
            commands.value.forEach { c ->
                val o = JSONObject()
                o.put("mnemonic", c.mnemonic)
                o.put("raw", c.raw)
                val paramsObj = JSONObject()
                c.params.forEach { (k, v) -> paramsObj.put(k, v) }
                o.put("params", paramsObj)
                cmdsArr.put(o)
            }
            root.put("commands", cmdsArr)

            val file = File(getApplication<Application>().filesDir, filename)
            file.writeText(root.toString(2))
            true
        } catch (_: Exception) {
            false
        }
    }

    fun loadProjectFromFile(filename: String = "last_project.gcp"): Boolean {
        return try {
            val file = File(getApplication<Application>().filesDir, filename)
            if (!file.exists()) return false
            val text = file.readText()
            val root = JSONObject(text)

            val newTools = mutableListOf<Tool>()
            val toolsArr = root.optJSONArray("tools")
            if (toolsArr != null) {
                for (i in 0 until toolsArr.length()) {
                    val o = toolsArr.getJSONObject(i)
                    newTools.add(
                        Tool(
                            number = o.getInt("number"),
                            name = o.getString("name"),
                            diameter = o.getDouble("diameter"),
                            feed = o.getDouble("feed"),
                            rpm = o.getInt("rpm"),
                            color = o.optString("color", "#38BDF8")
                        )
                    )
                }
            }

            val newVars = mutableListOf<UserVar>()
            val varsArr = root.optJSONArray("variables")
            if (varsArr != null) {
                for (i in 0 until varsArr.length()) {
                    val o = varsArr.getJSONObject(i)
                    newVars.add(UserVar(o.getString("name"), o.getString("value")))
                }
            }

            val stObj = root.optJSONObject("stock")
            val newStock = if (stObj != null) {
                Stock(
                    x = stObj.getDouble("x"), y = stObj.getDouble("y"), z = stObj.getDouble("z"),
                    px = stObj.getDouble("px"), py = stObj.getDouble("py"), pz = stObj.getDouble("pz"),
                    visible = stObj.optBoolean("visible", true), color = stObj.optString("color", "#7080B0")
                )
            } else Stock()

            val newCmds = mutableListOf<Command>()
            val cmdsArr = root.optJSONArray("commands")
            if (cmdsArr != null) {
                for (i in 0 until cmdsArr.length()) {
                    val o = cmdsArr.getJSONObject(i)
                    val m = o.getString("mnemonic")
                    val raw = o.optString("raw", "")
                    val pObj = o.optJSONObject("params")
                    val pMap = mutableMapOf<String, Any>()
                    if (pObj != null) {
                        for (key in pObj.keys()) {
                            pMap[key] = pObj.get(key)
                        }
                    }
                    newCmds.add(Command(m, pMap, raw))
                }
            }

            if (newTools.isNotEmpty()) tools.value = newTools
            variables.value = newVars
            stock.value = newStock
            commands.value = newCmds
            selectedCommandIndex.value = maxOf(0, newCmds.size - 1)
            recalculate()
            true
        } catch (_: Exception) {
            false
        }
    }

    fun parseAndLoadGCode(text: String): Pair<Int, Int> {
        val (cmds, warns) = GCodeParser().parse(text)
        if (cmds.isNotEmpty()) {
            commands.value = cmds
            selectedCommandIndex.value = cmds.size - 1
            recalculate()
        }
        return Pair(cmds.size, warns.size)
    }
}
