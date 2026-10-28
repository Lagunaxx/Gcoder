package com.example.core

import com.example.model.Command
import java.util.Locale
import java.util.regex.Pattern

class GCodeParser {

    private val gMap = mapOf(
        "0" to "RAPID", "00" to "RAPID", "1" to "FEED", "01" to "FEED",
        "2" to "ARC_CW", "02" to "ARC_CW", "3" to "ARC_CCW", "03" to "ARC_CCW",
        "4" to "DWELL", "04" to "DWELL", "12" to "POCKET_CW", "13" to "POCKET_CCW",
        "31" to "PROBE", "73" to "CHIP", "80" to "CANCEL", "81" to "DRILL",
        "82" to "BORE", "83" to "PECK", "84" to "THREAD_R", "85" to "BORE_STD",
        "86" to "BORE_SPINDLE", "87" to "BORE_BACK", "88" to "BORE_MANUAL", "89" to "BORE_FINE",
        "17" to "PLANE_XY", "18" to "PLANE_XZ", "19" to "PLANE_YZ",
        "20" to "UNITS_IN", "21" to "UNITS_MM", "40" to "CUTCOMP_OFF",
        "41" to "CUTCOMP_L", "42" to "CUTCOMP_R", "43" to "TOOLCOMP_P",
        "44" to "TOOLCOMP_M", "49" to "TOOLCOMP_OFF", "10" to "G10",
        "50" to "SCALE_OFF", "51" to "SCALE_ON", "52" to "LOCAL_OFF", "53" to "MACHINE",
        "54" to "WCS", "55" to "WCS", "56" to "WCS", "57" to "WCS", "58" to "WCS", "59" to "WCS",
        "68" to "ROT_ON", "69" to "ROT_OFF", "90" to "ABS", "91" to "INC",
        "90.1" to "ARC_ABS", "91.1" to "ARC_INC", "93" to "FEED_INV", "94" to "FEED_IPM",
        "95" to "FEED_IPR", "96" to "CSS", "97" to "RPM_FIX", "61" to "EXACT", "64" to "SMOOTH",
        "28" to "HOME", "28.1" to "HOME_BASE", "30" to "HOME2", "98" to "RET_INIT", "99" to "RET_R",
        "15" to "POLAR_OFF", "16" to "POLAR_ON", "92" to "G92SET", "92.1" to "G92CLR",
        "92.2" to "G92SUSP", "92.3" to "G92RES"
    )

    private val mMap = mapOf(
        0 to "STOP", 1 to "STOP", 2 to "END", 30 to "END",
        3 to "SPIN", 4 to "SPIN", 5 to "SPIN", 6 to "TOOL",
        7 to "COOL", 8 to "COOL", 9 to "COOL", 10 to "CLAMP", 11 to "CLAMP",
        47 to "REWIND", 48 to "OVR_ON", 49 to "OVR_OFF", 98 to "SUB_CALL", 99 to "SUB_RET"
    )

    fun parse(text: String): Pair<List<Command>, List<String>> {
        val commands = mutableListOf<Command>()
        val warnings = mutableListOf<String>()

        var cx = 0.0
        var cy = 0.0
        var cz = 0.0
        var ca = 0.0
        var cb = 0.0
        var cc = 0.0
        var curFeed = 200.0
        var spindleOn = false
        var coolOn = false

        val labelPattern = Pattern.compile("^\\s*N\\s*(\\d+)\\b", Pattern.MULTILINE)
        val lm = labelPattern.matcher(text)
        val labels = mutableMapOf<Int, String>()
        while (lm.find()) {
            val num = lm.group(1).toInt()
            labels[num] = "L$num"
        }

        val commentP = Pattern.compile("\\(([^)]*)\\)")
        val varP = Pattern.compile("^(#\\d+|#<[A-Za-z_]\\w*>)\\s*=\\s*(.+)$")
        val addP = Pattern.compile("^\\[\\s*(#\\d+|#<[A-Za-z_]\\w*>)\\s*\\+\\s*(.+?)\\s*\\]$")
        val ifP = Pattern.compile("^IF\\s*\\[([^\\]]+)\\]\\s*GOTO\\s*(\\d+)\\s*$", Pattern.CASE_INSENSITIVE)
        val gotoP = Pattern.compile("^GOTO\\s*(\\d+)\\s*$", Pattern.CASE_INSENSITIVE)

        for (rawLine in text.lines()) {
            var line = rawLine.trim()
            if (line.isEmpty() || line.startsWith("%")) {
                val cm = commentP.matcher(rawLine)
                if (cm.find()) {
                    commands.add(Command("#", emptyMap(), cm.group(1).trim()))
                }
                continue
            }

            val cm = commentP.matcher(line)
            while (cm.find()) {
                commands.add(Command("#", emptyMap(), cm.group(1).trim()))
            }
            line = commentP.matcher(line).replaceAll("").trim()
            if (line.isEmpty()) continue

            val vm = varP.matcher(line)
            if (vm.matches()) {
                val vName = vm.group(1).trim()
                val rhs = vm.group(2).trim()
                val addM = addP.matcher(rhs)
                if (addM.matches() && addM.group(1) == vName) {
                    commands.add(Command("VAR_ADD", mapOf("name" to vName, "delta" to addM.group(2).trim())))
                } else {
                    commands.add(Command("VAR", mapOf("name" to vName, "value" to rhs)))
                }
                continue
            }

            val im = ifP.matcher(line)
            if (im.matches()) {
                val parts = im.group(1).trim().split("\\s+".toRegex())
                val lhs = parts.getOrNull(0) ?: "#100"
                val op = parts.getOrNull(1) ?: "EQ"
                val rhs = parts.getOrNull(2) ?: "0"
                commands.add(Command("IF", mapOf("lhs" to lhs, "op" to op, "rhs" to rhs, "target" to "L${im.group(2)}")))
                continue
            }

            val gm = gotoP.matcher(line)
            if (gm.matches()) {
                commands.add(Command("GOTO", mapOf("target" to "L${gm.group(1)}")))
                continue
            }

            val tokens = line.split("\\s+".toRegex())
            val gcodes = mutableListOf<String>()
            var mcode: Int? = null
            var nLabel: Int? = null
            var tool: Int? = null
            val coords = mutableMapOf<Char, Double>()

            for (tok in tokens) {
                if (tok.isEmpty()) continue
                val letter = tok[0].uppercaseChar()
                val valStr = tok.substring(1)
                val numVal = valStr.toDoubleOrNull() ?: continue
                when (letter) {
                    'G' -> gcodes.add(valStr)
                    'M' -> mcode = numVal.toInt()
                    'N' -> nLabel = numVal.toInt()
                    'T' -> tool = numVal.toInt()
                    in 'A'..'Z' -> coords[letter.lowercaseChar()] = numVal
                }
            }

            if (nLabel != null && nLabel in labels) {
                commands.add(Command("LABEL", mapOf("name" to labels[nLabel]!!)))
            }

            if (mcode != null) {
                val mnem = mMap[mcode]
                when (mnem) {
                    "SPIN" -> {
                        if (mcode == 5) {
                            if (spindleOn) commands.add(Command("SPIN", mapOf("on" to 0, "rpm" to 0, "ccw" to 0)))
                            spindleOn = false
                        } else {
                            val rpm = coords['s']?.toInt() ?: 8000
                            commands.add(Command("SPIN", mapOf("on" to 1, "rpm" to rpm, "ccw" to if (mcode == 4) 1 else 0)))
                            spindleOn = true
                        }
                    }
                    "COOL" -> {
                        if (mcode == 9) {
                            if (coolOn) commands.add(Command("COOL", mapOf("on" to 0, "mist" to 0)))
                            coolOn = false
                        } else {
                            commands.add(Command("COOL", mapOf("on" to 1, "mist" to if (mcode == 7) 1 else 0)))
                            coolOn = true
                        }
                    }
                    "CLAMP" -> commands.add(Command("CLAMP", mapOf("on" to if (mcode == 10) 1 else 0)))
                    "STOP" -> commands.add(Command("STOP", mapOf("optional" to if (mcode == 1) 1 else 0)))
                    "END" -> commands.add(Command("END"))
                    "SUB_CALL" -> {
                        val p = coords['p']?.toInt() ?: 1000
                        val l = coords['l']?.toInt() ?: 1
                        commands.add(Command("SUB_CALL", mapOf("name" to p.toString(), "repeat" to l)))
                    }
                    "SUB_RET" -> commands.add(Command("SUB_RET"))
                    else -> if (mnem != null) commands.add(Command(mnem)) else warnings.add("M$mcode не поддержан")
                }
                if (mcode == 6 && tool != null) {
                    commands.add(Command("TOOL", mapOf("tool" to tool)))
                }
                continue
            }

            for (g in gcodes) {
                var key = if (g in gMap) g else g.toDoubleOrNull()?.toInt()?.toString()
                if (key == null || key !in gMap) {
                    warnings.add("G$g не поддержан")
                    continue
                }
                val mnem = gMap[key] ?: continue
                when (mnem) {
                    "RAPID", "FEED" -> {
                        val x = coords['x'] ?: cx
                        val y = coords['y'] ?: cy
                        val z = coords['z'] ?: cz
                        val a = coords['a'] ?: ca
                        val b = coords['b'] ?: cb
                        val c = coords['c'] ?: cc
                        if (mnem == "FEED") {
                            val f = coords['f'] ?: curFeed
                            commands.add(Command("FEED", mapOf("x" to x, "y" to y, "z" to z, "a" to a, "b" to b, "c" to c, "f" to f)))
                        } else {
                            commands.add(Command("RAPID", mapOf("x" to x, "y" to y, "z" to z, "a" to a, "b" to b, "c" to c)))
                        }
                        cx = x; cy = y; cz = z; ca = a; cb = b; cc = c
                        coords['f']?.let { curFeed = it }
                    }
                    "ARC_CW", "ARC_CCW" -> {
                        val x = coords['x'] ?: cx
                        val y = coords['y'] ?: cy
                        val z = coords['z'] ?: cz
                        val ccx = cx + (coords['i'] ?: 0.0)
                        val ccy = cy + (coords['j'] ?: 0.0)
                        val f = coords['f'] ?: curFeed
                        commands.add(Command(mnem, mapOf("x" to x, "y" to y, "z" to z, "cx" to ccx, "cy" to ccy, "f" to f)))
                        cx = x; cy = y; cz = z
                    }
                    "DWELL" -> {
                        val pMs = coords['p'] ?: 0.0
                        commands.add(Command("DWELL", mapOf("sec" to pMs / 1000.0)))
                    }
                    "WCS" -> {
                        commands.add(Command("WCS", mapOf("num" to key.toInt())))
                    }
                    "DRILL", "PECK", "CHIP", "BORE", "THREAD_R", "BORE_STD", "BORE_SPINDLE", "BORE_BACK", "BORE_MANUAL", "BORE_FINE" -> {
                        val d = mutableMapOf<String, Any>(
                            "x" to (coords['x'] ?: cx),
                            "y" to (coords['y'] ?: cy),
                            "z" to (coords['z'] ?: -5.0),
                            "r" to (coords['r'] ?: 1.0),
                            "f" to (coords['f'] ?: 60.0)
                        )
                        if (mnem in listOf("PECK", "CHIP")) d["q"] = coords['q'] ?: 1.0
                        if (mnem in listOf("BORE", "THREAD_R", "BORE_MANUAL", "BORE_FINE")) d["p"] = (coords['p'] ?: 0.0) / 1000.0
                        commands.add(Command(mnem, d))
                        cz = 5.0
                    }
                    "POCKET_CW", "POCKET_CCW" -> {
                        commands.add(Command(mnem, mapOf(
                            "i" to (coords['i'] ?: 10.0),
                            "j" to (coords['j'] ?: 10.0),
                            "z" to (coords['z'] ?: -2.0),
                            "f" to (coords['f'] ?: 200.0)
                        )))
                    }
                    else -> {
                        commands.add(Command(mnem))
                    }
                }
            }
        }
        return Pair(commands, warnings)
    }
}
