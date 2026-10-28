package com.example

import com.example.core.FormulaEval
import com.example.core.GCodeGenerator
import com.example.core.GCodeParser
import com.example.model.Command
import com.example.model.Stock
import com.example.model.Tool
import com.example.model.UserVar
import com.example.sim.Simulator
import org.junit.Assert.*
import org.junit.Test

class ExampleUnitTest {

    @Test
    fun testFormulaEvalBasicAndAdvanced() {
        val vars = mapOf("W" to 60.0, "L" to 100.0, "STEP" to 5.0)
        val fml = FormulaEval(vars)

        assertEquals(60.0, fml.resolveNumber("{W}"), 1e-4)
        assertEquals(120.0, fml.resolveNumber("{W * 2}"), 1e-4)
        assertEquals(13.0, fml.resolveNumber("{W // STEP + 1}"), 1e-4)
        assertEquals(100.0, fml.resolveNumber("{max(W, L)}"), 1e-4)
        assertEquals(3.14159, fml.resolveNumber("{pi}"), 1e-4)
    }

    @Test
    fun testGCodeGenerationAndMapping() {
        val tools = listOf(Tool(1, "Endmill 3mm", 3.0, 200.0, 8000))
        val vars = mapOf("W" to 60.0, "DEPTH" to -2.0)
        val commands = listOf(
            Command("TOOL", mapOf("tool" to 1)),
            Command("RAPID", mapOf("x" to 0.0, "y" to 0.0, "z" to 5.0)),
            Command("FEED", mapOf("x" to "{W}", "y" to 0.0, "z" to "{DEPTH}", "f" to 150.0)),
            Command("END")
        )

        val gen = GCodeGenerator(tools, vars)
        val lines = gen.generate(commands)

        assertTrue(lines.isNotEmpty())
        assertTrue(lines.any { it.contains("T1 M6") })
        assertTrue(lines.any { it.contains("G0 X0.000 Y0.000 Z5.000") })
        assertTrue(lines.any { it.contains("G1 X60.000 Y0.000 Z-2.000 F150.0") })
        assertTrue(lines.any { it.contains("M30") })
    }

    @Test
    fun testGCodeParser() {
        val gcode = """
            %
            N0010 G21
            N0020 G90
            N0030 T1 M6
            N0040 S8000 M3
            N0050 G0 X10.0 Y20.0 Z5.0
            N0060 G1 Z-3.0 F120.0
            N0070 M30
            %
        """.trimIndent()

        val parser = GCodeParser()
        val (cmds, warns) = parser.parse(gcode)

        assertTrue(cmds.isNotEmpty())
        assertTrue(cmds.any { it.mnemonic == "UNITS_MM" })
        assertTrue(cmds.any { it.mnemonic == "ABS" })
        assertTrue(cmds.any { it.mnemonic == "TOOL" })
        assertTrue(cmds.any { it.mnemonic == "RAPID" && it.params["x"] == 10.0 })
        assertTrue(cmds.any { it.mnemonic == "FEED" && it.params["z"] == -3.0 })
        assertTrue(cmds.any { it.mnemonic == "END" })
    }

    @Test
    fun testSimulatorAndCollisionDetection() {
        val tools = listOf(Tool(1, "Endmill 3mm", 3.0, 200.0, 8000))
        val stock = Stock(x = 100.0, y = 100.0, z = 10.0, px = 0.0, py = 0.0, pz = 0.0)

        // RAPID below Z0 into the stock -> should trigger collision!
        val commands = listOf(
            Command("RAPID", mapOf("x" to 10.0, "y" to 10.0, "z" to -5.0))
        )

        val sim = Simulator(tools, stock = stock)
        val result = sim.trace(commands, upto = 1, checkCollisions = true)

        assertEquals(1, result.stats.collisionCount)
        assertEquals("RAPID в материале", result.stats.collisions[0].reason)
    }
}
