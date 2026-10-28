package com.example.core

import com.example.model.UserVar
import java.util.Locale
import java.util.regex.Pattern
import kotlin.math.*

class FormulaEval(var vars: Map<String, Double> = emptyMap()) {

    var lastError: String? = null

    fun resolveNumber(value: Any?): Double {
        lastError = null
        if (value == null) return 0.0
        if (value is Number) return value.toDouble()
        val s = value.toString().trim()
        if (s.isEmpty()) return 0.0

        s.toDoubleOrNull()?.let { return it }

        var expr = s
        if (expr.startsWith("{") && expr.endsWith("}")) {
            expr = expr.substring(1, expr.length - 1).trim()
        }

        return try {
            eval(expr)
        } catch (e: Exception) {
            lastError = e.message
            0.0
        }
    }

    private fun eval(expr: String): Double {
        var processed = substituteBraces(expr)
        processed = substituteHashes(processed)
        val parser = ExpressionParser(processed, vars)
        return parser.parse()
    }

    private fun substituteBraces(expr: String): String {
        var cur = expr
        for (i in 0 until 16) {
            val start = cur.indexOf('{')
            if (start < 0) break
            val end = cur.indexOf('}', start)
            if (end < 0) break
            val inner = cur.substring(start + 1, end).trim()
            val innerVal = ExpressionParser(substituteHashes(inner), vars).parse()
            cur = cur.substring(0, start) + innerVal.toString() + cur.substring(end + 1)
        }
        return cur
    }

    private fun substituteHashes(expr: String): String {
        val hashNum = Pattern.compile("#(\\d+)")
        val hashName = Pattern.compile("#<([A-Za-z_]\\w*)>")

        var res = expr
        val m1 = hashName.matcher(res)
        val sb1 = StringBuffer()
        while (m1.find()) {
            val key = "#<" + m1.group(1) + ">"
            val simple = "#" + m1.group(1)
            val v = vars[key] ?: vars[simple] ?: vars[m1.group(1)] ?: 0.0
            m1.appendReplacement(sb1, v.toString())
        }
        m1.appendTail(sb1)
        res = sb1.toString()

        val m2 = hashNum.matcher(res)
        val sb2 = StringBuffer()
        while (m2.find()) {
            val key = "#" + m2.group(1)
            val v = vars[key] ?: 0.0
            m2.appendReplacement(sb2, v.toString())
        }
        m2.appendTail(sb2)
        return sb2.toString()
    }

    private class ExpressionParser(private val text: String, private val vars: Map<String, Double>) {
        private var pos = -1
        private var ch = 0

        private fun nextChar() {
            ch = if (++pos < text.length) text[pos].code else -1
        }

        private fun eat(charToEat: Int): Boolean {
            while (ch == ' '.code || ch == '\t'.code) nextChar()
            if (ch == charToEat) {
                nextChar()
                return true
            }
            return false
        }

        fun parse(): Double {
            nextChar()
            val x = parseExpression()
            while (ch == ' '.code || ch == '\t'.code) nextChar()
            return x
        }

        private fun parseExpression(): Double {
            var x = parseTerm()
            while (true) {
                when {
                    eat('+'.code) -> x += parseTerm()
                    eat('-'.code) -> x -= parseTerm()
                    else -> return x
                }
            }
        }

        private fun parseTerm(): Double {
            var x = parseFactor()
            while (true) {
                when {
                    eat('*'.code) -> {
                        if (eat('*'.code)) {
                            x = x.pow(parseFactor())
                        } else {
                            x *= parseFactor()
                        }
                    }
                    eat('/'.code) -> {
                        if (eat('/'.code)) {
                            val d = parseFactor()
                            x = if (d != 0.0) floor(x / d) else 0.0
                        } else {
                            val d = parseFactor()
                            x = if (d != 0.0) x / d else 0.0
                        }
                    }
                    eat('%'.code) -> {
                        val d = parseFactor()
                        x = if (d != 0.0) x % d else 0.0
                    }
                    else -> return x
                }
            }
        }

        private fun parseFactor(): Double {
            while (ch == ' '.code || ch == '\t'.code) nextChar()
            if (eat('+'.code)) return +parseFactor()
            if (eat('-'.code)) return -parseFactor()

            var x: Double
            val startPos = pos
            if (eat('('.code)) {
                x = parseExpression()
                eat(')'.code)
            } else if ((ch in '0'.code..'9'.code) || ch == '.'.code) {
                while ((ch in '0'.code..'9'.code) || ch == '.'.code || ch == 'e'.code || ch == 'E'.code) nextChar()
                val numStr = text.substring(startPos, pos)
                x = numStr.toDoubleOrNull() ?: 0.0
            } else if ((ch in 'a'.code..'z'.code) || (ch in 'A'.code..'Z'.code) || ch == '_'.code) {
                while ((ch in 'a'.code..'z'.code) || (ch in 'A'.code..'Z'.code) || (ch in '0'.code..'9'.code) || ch == '_'.code) nextChar()
                val id = text.substring(startPos, pos)
                if (eat('('.code)) {
                    val args = mutableListOf<Double>()
                    if (!eat(')'.code)) {
                        do {
                            args.add(parseExpression())
                        } while (eat(','.code))
                        eat(')'.code)
                    }
                    x = evalFunction(id.lowercase(Locale.ROOT), args)
                } else {
                    x = when (id.lowercase(Locale.ROOT)) {
                        "pi" -> Math.PI
                        "e" -> Math.E
                        "tau" -> Math.PI * 2.0
                        else -> vars[id] ?: vars["#" + id] ?: 0.0
                    }
                }
            } else {
                x = 0.0
                if (ch != -1) nextChar()
            }
            return x
        }

        private fun evalFunction(name: String, args: List<Double>): Double {
            val a0 = args.getOrNull(0) ?: 0.0
            val a1 = args.getOrNull(1) ?: 0.0
            return when (name) {
                "min" -> if (args.size >= 2) min(a0, a1) else a0
                "max" -> if (args.size >= 2) max(a0, a1) else a0
                "abs" -> abs(a0)
                "round" -> round(a0)
                "floor" -> floor(a0)
                "ceil" -> ceil(a0)
                "sqrt" -> if (a0 >= 0) sqrt(a0) else 0.0
                "sin" -> sin(a0)
                "cos" -> cos(a0)
                "tan" -> tan(a0)
                "atan2" -> atan2(a0, a1)
                "hypot" -> hypot(a0, a1)
                "int" -> floor(a0)
                "float" -> a0
                else -> 0.0
            }
        }
    }

    companion object {
        fun buildEnv(varsList: List<UserVar>): Pair<Map<String, Double>, List<String>> {
            val raw = varsList.filter { it.name.isNotBlank() }.associate { it.name to it.value }
            val result = mutableMapOf<String, Double>()
            val errors = mutableListOf<String>()

            for (iter in 0 until 32) {
                var progress = false
                for ((name, expr) in raw) {
                    if (name in result) continue
                    try {
                        val fe = FormulaEval(result)
                        val num = fe.resolveNumber(expr)
                        if (fe.lastError == null) {
                            result[name] = num
                            progress = true
                        }
                    } catch (_: Exception) { }
                }
                if (!progress) break
            }

            for ((name, expr) in raw) {
                if (name !in result) {
                    val fe = FormulaEval(result)
                    val num = fe.resolveNumber(expr)
                    if (fe.lastError != null) {
                        errors.add("$name: ${fe.lastError}")
                    }
                    result[name] = num
                }
            }
            return Pair(result, errors)
        }
    }
}
