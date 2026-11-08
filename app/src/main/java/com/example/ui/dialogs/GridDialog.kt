package com.example.ui.dialogs

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.GridOn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import java.util.Locale
import kotlin.math.roundToInt

@Composable
fun GridDialog(
    initialSizeMm: Double,
    stockWidth: Double = 100.0,
    stockHeight: Double = 80.0,
    onDismiss: () -> Unit,
    onConfirm: (Double) -> Unit
) {
    // Direct input text field for user-entered grid cell size (in millimeters)
    var textValue by remember {
        mutableStateOf(String.format(Locale.US, "%.2f", initialSizeMm).trimEnd('0').trimEnd('.'))
    }

    val parsedValue = textValue.replace(',', '.').toDoubleOrNull()
    val isValid = parsedValue != null && parsedValue in 0.1..20.0

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF1E293B),
            tonalElevation = 8.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                // Header with Grid icon
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.GridOn,
                        contentDescription = null,
                        tint = Color(0xFF38BDF8),
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Размер ячейки сетки",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Задайте точный размер ячейки дискретизации (мм) для симуляции фрезерования и карты высот.",
                    color = Color(0xFF94A3B8),
                    fontSize = 12.sp,
                    lineHeight = 16.sp
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Direct numeric input field
                OutlinedTextField(
                    value = textValue,
                    onValueChange = { textValue = it },
                    label = { Text("Размер ячейки (мм)") },
                    placeholder = { Text("Например: 1.0 или 0.75") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    isError = !isValid && textValue.isNotBlank(),
                    supportingText = {
                        if (!isValid && textValue.isNotBlank()) {
                            Text("Допустимый диапазон: от 0.1 до 20.0 мм", color = Color(0xFFEF4444), fontSize = 11.sp)
                        } else if (isValid && parsedValue != null) {
                            val nx = (stockWidth / parsedValue).roundToInt().coerceIn(10, 100)
                            val ny = (stockHeight / parsedValue).roundToInt().coerceIn(10, 100)
                            Text("Расчетная плотность: ~$nx × $ny точек на заготовку", color = Color(0xFF34D399), fontSize = 11.sp)
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF38BDF8),
                        unfocusedBorderColor = Color(0xFF475569)
                    )
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Stepper adjustment buttons for quick fine-tuning
                Text(
                    text = "Быстрая подстройка величины:",
                    color = Color(0xFF94A3B8),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    val steps = listOf(-0.5, -0.1, +0.1, +0.5)
                    steps.forEach { delta ->
                        Button(
                            onClick = {
                                val current = parsedValue ?: initialSizeMm
                                val updated = (current + delta).coerceIn(0.1, 20.0)
                                textValue = String.format(Locale.US, "%.2f", updated).trimEnd('0').trimEnd('.')
                            },
                            modifier = Modifier
                                .weight(1f)
                                .height(34.dp),
                            contentPadding = PaddingValues(0.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334155)),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text(
                                text = if (delta > 0) "+${delta} мм" else "${delta} мм",
                                fontSize = 11.sp,
                                color = Color.White
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Action buttons: Cancel / Apply
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Отмена", color = Color(0xFF94A3B8))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            if (isValid && parsedValue != null) {
                                onConfirm(parsedValue)
                            }
                        },
                        enabled = isValid,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF0284C7),
                            disabledContainerColor = Color(0xFF334155)
                        ),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Применить", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
