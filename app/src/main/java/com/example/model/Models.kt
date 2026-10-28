package com.example.model

data class Tool(
    val number: Int,
    val name: String,
    val diameter: Double,
    val feed: Double,
    val rpm: Int,
    val color: String = "#3399FF",
    val lengthOffset: Double = 0.0,
    val radiusOffset: Double = 0.0
)

data class Stock(
    val mode: String = "box",
    val x: Double = 100.0,
    val y: Double = 120.0,
    val z: Double = 15.0,
    val px: Double = 0.0,
    val py: Double = 0.0,
    val pz: Double = 0.0,
    val color: String = "#7080B0",
    val visible: Boolean = true
) {
    fun bounds(): DoubleArray {
        return doubleArrayOf(px, py, px + x, py + y, pz, pz - z)
    }
}

data class UserVar(
    val name: String,
    val value: String
)

data class Command(
    val mnemonic: String,
    val params: Map<String, Any> = emptyMap(),
    val raw: String = ""
) {
    fun toPseudo(nIndex: Int = -1): String {
        val prefix = if (nIndex >= 0) "[N%03d] ".format((nIndex + 1) * 10) else ""
        if (mnemonic == "#") {
            return prefix + "# " + (params["text"] ?: raw)
        }
        if (params.isEmpty()) {
            return prefix + mnemonic
        }
        val parts = mutableListOf(mnemonic)
        for ((k, v) in params) {
            when (v) {
                is Double -> {
                    val formatted = if (v % 1.0 == 0.0) v.toLong().toString() else "%.3f".format(v).trimEnd('0').trimEnd('.')
                    parts.add("$k=$formatted")
                }
                is Float -> {
                    val formatted = if (v % 1.0f == 0.0f) v.toLong().toString() else "%.3f".format(v).trimEnd('0').trimEnd('.')
                    parts.add("$k=$formatted")
                }
                else -> parts.add("$k=$v")
            }
        }
        return prefix + parts.joinToString(" ")
    }
}

data class FunctionParam(
    val name: String,
    val defaultVal: String = "0",
    val description: String = ""
)

data class FunctionDef(
    val name: String,
    val title: String = "",
    val description: String = "",
    val params: List<FunctionParam> = emptyList(),
    val body: List<Command> = emptyList()
)
