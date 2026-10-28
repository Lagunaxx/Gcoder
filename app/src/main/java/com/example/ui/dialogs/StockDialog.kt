package com.example.ui.dialogs

import androidx.compose.foundation.layout.*
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
import com.example.model.Stock

@Composable
fun StockDialog(
    initialStock: Stock,
    onDismiss: () -> Unit,
    onConfirm: (Stock) -> Unit
) {
    var sizeX by remember { mutableStateOf(initialStock.x.toString()) }
    var sizeY by remember { mutableStateOf(initialStock.y.toString()) }
    var sizeZ by remember { mutableStateOf(initialStock.z.toString()) }

    var posX by remember { mutableStateOf(initialStock.px.toString()) }
    var posY by remember { mutableStateOf(initialStock.py.toString()) }
    var posZ by remember { mutableStateOf(initialStock.pz.toString()) }

    var visible by remember { mutableStateOf(initialStock.visible) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF1E293B),
            tonalElevation = 8.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = "Параметры заготовки",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )

                Spacer(modifier = Modifier.height(14.dp))

                Text("Размеры заготовки (мм):", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(
                        value = sizeX,
                        onValueChange = { sizeX = it },
                        label = { Text("Длина X") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    OutlinedTextField(
                        value = sizeY,
                        onValueChange = { sizeY = it },
                        label = { Text("Ширина Y") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    OutlinedTextField(
                        value = sizeZ,
                        onValueChange = { sizeZ = it },
                        label = { Text("Высота Z") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text("Положение заготовки (смещение нуля):", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(
                        value = posX,
                        onValueChange = { posX = it },
                        label = { Text("Смещение X") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    OutlinedTextField(
                        value = posY,
                        onValueChange = { posY = it },
                        label = { Text("Смещение Y") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    OutlinedTextField(
                        value = posZ,
                        onValueChange = { posZ = it },
                        label = { Text("Верх Z") },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = visible,
                        onCheckedChange = { visible = it },
                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Отображать заготовку в 3D", color = Color(0xFFE2E8F0), fontSize = 14.sp)
                }

                Spacer(modifier = Modifier.height(18.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    OutlinedButton(onClick = onDismiss, modifier = Modifier.height(48.dp)) {
                        Text("Отмена", color = Color(0xFF94A3B8))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            val x = sizeX.toDoubleOrNull() ?: 100.0
                            val y = sizeY.toDoubleOrNull() ?: 120.0
                            val z = sizeZ.toDoubleOrNull() ?: 15.0
                            val px = posX.toDoubleOrNull() ?: 0.0
                            val py = posY.toDoubleOrNull() ?: 0.0
                            val pz = posZ.toDoubleOrNull() ?: 0.0
                            onConfirm(initialStock.copy(x = x, y = y, z = z, px = px, py = py, pz = pz, visible = visible))
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        modifier = Modifier.height(48.dp)
                    ) {
                        Text("Применить", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
