package com.example.core

import com.example.model.Command
import com.example.model.FunctionDef
import kotlin.math.abs

class ProgramInterp(
    val commands: List<Command>,
    initialVars: Map<String, Double> = emptyMap(),
    val maxSteps: Int = 100000,
    val functions: Map<String, FunctionDef> = emptyMap()
) {
    val vars = initialVars.toMutableMap()
    private val fml = FormulaEval(vars)
    private val labels = mutableMapOf<String, Int>()
    private var callDepth = 0

    init {
        for ((i, c) in commands.withIndex()) {
            if (c.mnemonic == "LABEL") {
                val name = c.params["name"]?.toString() ?: ""
                if (name.isNotEmpty()) {
                    labels[name] = i
                }
            }
        }
    }

    fun num(v: Any?): Double {
        fml.vars = vars
        return fml.resolveNumber(v)
    }

    private fun cmp(a: Double, op: String, b: Double): Boolean {
        return when (op.uppercase()) {
            "EQ" -> abs(a - b) < 1e-7
            "NE" -> abs(a - b) >= 1e-7
            "GT" -> a > b
            "LT" -> a < b
            "GE" -> a >= b
            "LE" -> a <= b
            else -> false
        }
    }

    private fun runFunction(fnName: String, params: Map<String, Any>, callback: (Command, Int) -> Unit) {
        if (callDepth >= 16) return
        val fn = functions[fnName] ?: return
        if (fn.body.isEmpty()) return

        val saved = vars.toMap()
        val local = vars.toMutableMap()

        for (prm in fn.params) {
            val pkey = "p_${prm.name}"
            val raw = params[pkey] ?: prm.defaultVal
            val fe = FormulaEval(local)
            val v = fe.resolveNumber(raw)
            val full = "#FN_${fn.name}_${prm.name}"
            local[full] = v
            local["#" + prm.name] = v
            local[prm.name] = v
        }

        val subLabels = mutableMapOf<String, Int>()
        for ((i, c) in fn.body.withIndex()) {
            if (c.mnemonic == "LABEL") {
                val lName = c.params["name"]?.toString() ?: ""
                if (lName.isNotEmpty()) subLabels[lName] = i
            }
        }

        callDepth++
        vars.clear()
        vars.putAll(local)
        fml.vars = vars

        try {
            var i = 0
            var subSteps = 0
            while (i < fn.body.size && subSteps <= maxSteps) {
                subSteps++
                val cmd = fn.body[i]
                val m = cmd.mnemonic
                val p = cmd.params
                when (m) {
                    "VAR" -> {
                        val name = p["name"]?.toString() ?: "#100"
                        vars[name] = num(p["value"])
                        i++
                    }
                    "VAR_ADD" -> {
                        val name = p["name"]?.toString() ?: "#100"
                        val d = num(p["delta"] ?: 1)
                        vars[name] = (vars[name] ?: 0.0) + d
                        i++
                    }
                    "LABEL" -> i++
                    "IF" -> {
                        val lhs = num(p["lhs"] ?: 0)
                        val rhs = num(p["rhs"] ?: 0)
                        val op = p["op"]?.toString() ?: "EQ"
                        if (cmp(lhs, op, rhs)) {
                            val target = p["target"]?.toString() ?: ""
                            val dest = subLabels[target]
                            if (dest != null) {
                                i = dest
                                continue
                            }
                        }
                        i++
                    }
                    "GOTO" -> {
                        val target = p["target"]?.toString() ?: ""
                        val dest = subLabels[target]
                        if (dest != null) {
                            i = dest
                            continue
                        }
                        i++
                    }
                    "CALL_FUNC" -> {
                        val subName = p["name"]?.toString() ?: ""
                        runFunction(subName, p, callback)
                        i++
                    }
                    else -> {
                        callback(cmd, -1)
                        i++
                    }
                }
            }
        } finally {
            callDepth--
            vars.clear()
            vars.putAll(saved)
            fml.vars = vars
        }
    }

    fun run(startIndex: Int = 0, endIndex: Int? = null, stepLimit: Int? = null, callback: (Command, Int) -> Unit): Int {
        var i = startIndex
        var steps = 0
        val limit = stepLimit ?: maxSteps
        val end = endIndex ?: commands.size
        val callStack = mutableListOf<Int>()

        while (i < end && steps < limit) {
            val cmd = commands[i]
            steps++
            val m = cmd.mnemonic
            val p = cmd.params

            when (m) {
                "VAR" -> {
                    val name = p["name"]?.toString() ?: "#100"
                    vars[name] = num(p["value"])
                    i++
                }
                "VAR_ADD" -> {
                    val name = p["name"]?.toString() ?: "#100"
                    val d = num(p["delta"] ?: 1)
                    vars[name] = (vars[name] ?: 0.0) + d
                    i++
                }
                "LABEL" -> i++
                "IF" -> {
                    val lhs = num(p["lhs"] ?: 0)
                    val rhs = num(p["rhs"] ?: 0)
                    val op = p["op"]?.toString() ?: "EQ"
                    if (cmp(lhs, op, rhs)) {
                        val target = p["target"]?.toString() ?: ""
                        val dest = labels[target]
                        if (dest != null) {
                            i = dest
                            continue
                        }
                    }
                    i++
                }
                "GOTO" -> {
                    val target = p["target"]?.toString() ?: ""
                    val dest = labels[target]
                    if (dest != null) {
                        i = dest
                        continue
                    }
                    i++
                }
                "CALL_FUNC" -> {
                    val fnName = p["name"]?.toString() ?: ""
                    runFunction(fnName, p, callback)
                    i++
                }
                "SUB_CALL" -> {
                    val name = p["name"]?.toString() ?: "1000"
                    val repeat = (p["repeat"] as? Number)?.toInt() ?: 1
                    var target: Int? = null
                    for (cand in listOf("L$name", "SUB_$name", "O$name", name)) {
                        if (cand in labels) {
                            target = labels[cand]
                            break
                        }
                    }
                    if (target != null) {
                        for (r in 0 until repeat) {
                            callStack.add(i + 1)
                        }
                        i = target
                        continue
                    }
                    i++
                }
                "SUB_RET" -> {
                    if (callStack.isNotEmpty()) {
                        i = callStack.removeAt(callStack.size - 1)
                    } else {
                        i++
                    }
                }
                else -> {
                    callback(cmd, i)
                    i++
                }
            }
        }
        return steps
    }
}
