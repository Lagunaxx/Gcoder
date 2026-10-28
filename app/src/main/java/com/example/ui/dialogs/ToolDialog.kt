package com.example.ui.dialogs

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.model.Tool

@Composable
fun ToolDialog(
    initialTool: Tool? = null,
    onDismiss: () -> Unit,
    onConfirm: (Tool) -> Unit
) {
    var number by remember { mutableStateOf((initialTool?.number ?: 1).toString()) }
    var name by remember { mutableStateOf(initialTool?.name ?: "Фреза 3мм") }
    var diameter by remember { mutableStateOf((initialTool?.diameter ?: 3.0).toString()) }
    var feed by remember { mutableStateOf((initialTool?.feed ?: 200.0).toString()) }
    var rpm by remember { mutableStateOf((initialTool?.rpm ?: 8000).toString()) }
    var colorHex by remember { mutableStateOf(initialTool?.color ?: "#38BDF8") }

    val presetColors = listOf(
        "#38BDF8", "#3B82F6", "#6366F1", "#A855F7",
        "#EC4899", "#EF4444", "#F97316", "#F59E0B",
        "#10B981", "#14B8A6", "#06B6D4", "#84CC16"
    )

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF1E293B),
            tonalElevation = 8.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = if (initialTool == null) "Новый инструмент" else "Параметры инструмента",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )

                Spacer(modifier = Modifier.height(14.dp))

                Row(modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(
                        value = number,
                        onValueChange = { number = it },
                        label = { Text("№ инструмента (T)") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    OutlinedTextField(
                        value = diameter,
                        onValueChange = { diameter = it },
                        label = { Text("Диаметр D (мм)") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Название (напр. Концевая фреза 3мм)") },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                )

                Spacer(modifier = Modifier.height(8.dp))

                Row(modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(
                        value = feed,
                        onValueChange = { feed = it },
                        label = { Text("Подача F (мм/мин)") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    OutlinedTextField(
                        value = rpm,
                        onValueChange = { rpm = it },
                        label = { Text("Обороты RPM") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text("Цвет фрезы в симуляции:", color = Color(0xFF94A3B8), fontSize = 12.sp)
                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    presetColors.take(6).forEach { hex ->
                        val isSel = colorHex.equals(hex, ignoreCase = true)
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .background(parseColor(hex), CircleShape)
                                .border(if (isSel) 3.dp else 1.dp, if (isSel) Color.White else Color.Transparent, CircleShape)
                                .clickable { colorHex = hex }
                        )
                    }
                }
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    presetColors.drop(6).forEach { hex ->
                        val isSel = colorHex.equals(hex, ignoreCase = true)
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .background(parseColor(hex), CircleShape)
                                .border(if (isSel) 3.dp else 1.dp, if (isSel) Color.White else Color.Transparent, CircleShape)
                                .clickable { colorHex = hex }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    OutlinedButton(onClick = onDismiss, modifier = Modifier.height(48.dp)) {
                        Text("Отмена", color = Color(0xFF94A3B8))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            val num = number.toIntOrNull() ?: 1
                            val dia = diameter.toDoubleOrNull() ?: 3.0
                            val f = feed.toDoubleOrNull() ?: 200.0
                            val r = rpm.toIntOrNull() ?: 8000
                            onConfirm(Tool(num, name, dia, f, r, colorHex))
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        modifier = Modifier.height(48.dp)
                    ) {
                        Text("Сохранить", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

private fun parseColor(hex: String): Color {
    return try {
        val clean = hex.removePrefix("#")
        val colorInt = clean.toLong(16)
        Color((0xFF000000 or colorInt).toInt())
    } catch (_: Exception) {
        Color(0xFF38BDF8)
    }
}
