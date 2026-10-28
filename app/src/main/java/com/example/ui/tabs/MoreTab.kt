package com.example.ui.tabs

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.*

@Composable
fun MoreTab(
    variables: List<UserVar>,
    stock: Stock,
    functions: List<FunctionDef>,
    preamble: List<Command>,
    postamble: List<Command>,
    settings: SimSettings,
    evaluatedVars: Map<String, Double>,
    onAddVar: () -> Unit,
    onEditVar: (UserVar) -> Unit,
    onDeleteVar: (UserVar) -> Unit,
    onEditStock: () -> Unit,
    onInsertFunction: (FunctionDef) -> Unit,
    onEditPreamble: () -> Unit,
    onEditPostamble: () -> Unit,
    onUpdateSettings: (SimSettings) -> Unit,
    modifier: Modifier = Modifier
) {
    var subSection by remember { mutableIntStateOf(0) }
    val subSections = listOf("Переменные", "Заготовка", "Функции", "Начало/Конец", "Настройки")

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
    ) {
        // Horizontal Chip Selector
        ScrollableTabRow(
            selectedTabIndex = subSection,
            edgePadding = 8.dp,
            containerColor = Color(0xFF1E293B),
            contentColor = Color(0xFF38BDF8),
            modifier = Modifier.fillMaxWidth().height(44.dp)
        ) {
            subSections.forEachIndexed { index, label ->
                Tab(
                    selected = subSection == index,
                    onClick = { subSection = index },
                    text = {
                        Text(
                            text = label,
                            fontSize = 12.sp,
                            fontWeight = if (subSection == index) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        // Sub-section content
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp)
        ) {
            when (subSection) {
                0 -> {
                    // Variables Section
                    Column(modifier = Modifier.fillMaxSize()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Именованные переменные", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Button(
                                onClick = onAddVar,
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.height(36.dp),
                                contentPadding = PaddingValues(horizontal = 10.dp)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Переменная", fontSize = 12.sp)
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        if (variables.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text("Нет переменных. Добавьте W, L, STEP...", color = Color(0xFF64748B), fontSize = 13.sp)
                            }
                        } else {
                            LazyColumn(modifier = Modifier.fillMaxSize()) {
                                items(variables) { v ->
                                    val calcVal = evaluatedVars[v.name]
                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = Color(0xFF1E293B),
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 3.dp)
                                            .clickable { onEditVar(v) }
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(10.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = v.name,
                                                color = Color(0xFF38BDF8),
                                                fontFamily = FontFamily.Monospace,
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 13.sp,
                                                modifier = Modifier.width(70.dp)
                                            )
                                            Text(
                                                text = "= ${v.value}",
                                                color = Color.White,
                                                fontFamily = FontFamily.Monospace,
                                                fontSize = 13.sp,
                                                modifier = Modifier.weight(1f)
                                            )
                                            if (calcVal != null) {
                                                Text(
                                                    text = "(%.2f)".format(calcVal),
                                                    color = Color(0xFF4ADE80),
                                                    fontFamily = FontFamily.Monospace,
                                                    fontSize = 12.sp
                                                )
                                            }
                                            Spacer(modifier = Modifier.width(6.dp))
                                            IconButton(
                                                onClick = { onDeleteVar(v) },
                                                modifier = Modifier.size(32.dp)
                                            ) {
                                                Icon(Icons.Default.Delete, contentDescription = "Удалить", tint = Color(0xFFEF4444), modifier = Modifier.size(16.dp))
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                1 -> {
                    // Stock Section
                    Column(modifier = Modifier.fillMaxSize()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Параметры заготовки", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Button(
                                onClick = onEditStock,
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.height(36.dp),
                                contentPadding = PaddingValues(horizontal = 10.dp)
                            ) {
                                Icon(Icons.Default.Edit, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Изменить", fontSize = 12.sp)
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFF1E293B),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("Габариты заготовки:", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("• Длина X: ${stock.x} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Text("• Ширина Y: ${stock.y} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Text("• Высота Z: ${stock.z} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Spacer(modifier = Modifier.height(10.dp))
                                Text("Смещение нуля (G54):", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("• Смещение X: ${stock.px} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Text("• Смещение Y: ${stock.py} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Text("• Верх Z: ${stock.pz} мм", color = Color(0xFFCBD5E1), fontSize = 13.sp)
                                Spacer(modifier = Modifier.height(10.dp))
                                Text("• Статус: ${if (stock.visible) "Отображается в 3D" else "Скрыта"}", color = if (stock.visible) Color(0xFF4ADE80) else Color(0xFF94A3B8), fontSize = 12.sp)
                            }
                        }
                    }
                }
                2 -> {
                    // Functions Library
                    Column(modifier = Modifier.fillMaxSize()) {
                        Text("Библиотека готовых шаблонов", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(8.dp))

                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            items(functions) { fn ->
                                Surface(
                                    shape = RoundedCornerShape(10.dp),
                                    color = Color(0xFF1E293B),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                ) {
                                    Column(modifier = Modifier.padding(12.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(fn.name, color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                            Button(
                                                onClick = { onInsertFunction(fn) },
                                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                                                shape = RoundedCornerShape(6.dp),
                                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                                modifier = Modifier.height(30.dp)
                                            ) {
                                                Text("Вставить в код", fontSize = 11.sp, color = Color.White)
                                            }
                                        }
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(fn.title, color = Color.White, fontWeight = FontWeight.Medium, fontSize = 13.sp)
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(fn.description, color = Color(0xFF94A3B8), fontSize = 11.sp)
                                        Spacer(modifier = Modifier.height(6.dp))
                                        Text(
                                            text = "Параметры: " + fn.params.joinToString(", ") { "${it.name}=${it.defaultVal}" },
                                            color = Color(0xFF64748B),
                                            fontSize = 11.sp,
                                            fontFamily = FontFamily.Monospace
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                3 -> {
                    // Preamble / Postamble
                    Column(modifier = Modifier.fillMaxSize()) {
                        Text("Начало и Конец программы", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(10.dp))

                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFF1E293B),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Начало программы (Preamble):", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    IconButton(onClick = onEditPreamble, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.Edit, contentDescription = null, tint = Color(0xFF38BDF8), modifier = Modifier.size(16.dp))
                                    }
                                }
                                Text(
                                    text = if (preamble.isEmpty()) "Команды по умолчанию (G21, G90, G17)" else preamble.joinToString(", ") { it.mnemonic },
                                    color = Color(0xFFCBD5E1),
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFF1E293B),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Конец программы (Postamble):", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    IconButton(onClick = onEditPostamble, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.Edit, contentDescription = null, tint = Color(0xFF38BDF8), modifier = Modifier.size(16.dp))
                                    }
                                }
                                Text(
                                    text = if (postamble.isEmpty()) "Останов шпинделя (M5), СОЖ (M9), отвод и конец (M30)" else postamble.joinToString(", ") { it.mnemonic },
                                    color = Color(0xFFCBD5E1),
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                    }
                }
                4 -> {
                    // Settings Section
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                    ) {
                        Text("Настройки симуляции", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(10.dp))

                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFF1E293B),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(
                                        checked = settings.showMaterial,
                                        onCheckedChange = { onUpdateSettings(settings.copy(showMaterial = it)) },
                                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF059669))
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Отображать фрезерование (3D снятие материала)", color = Color.White, fontSize = 13.sp)
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(
                                        checked = settings.showToolpath,
                                        onCheckedChange = { onUpdateSettings(settings.copy(showToolpath = it)) },
                                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Отображать траектории (G0/G1/G2)", color = Color.White, fontSize = 13.sp)
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                Text("Режим поверхности (шейдинг):", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                Spacer(modifier = Modifier.height(4.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    val modes = listOf(
                                        Pair(ShadingMode.SOLID, "Сплошной"),
                                        Pair(ShadingMode.WIREFRAME, "Сетка (каркас)"),
                                        Pair(ShadingMode.TRANSPARENT, "Прозрачный")
                                    )
                                    for ((m, label) in modes) {
                                        val isSel = settings.shadingMode == m
                                        FilterChip(
                                            selected = isSel,
                                            onClick = { onUpdateSettings(settings.copy(shadingMode = m)) },
                                            label = { Text(label, fontSize = 11.sp) },
                                            colors = FilterChipDefaults.filterChipColors(
                                                selectedContainerColor = Color(0xFF0284C7),
                                                selectedLabelColor = Color.White
                                            ),
                                            modifier = Modifier.height(32.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                Text("Прозрачность заготовки: ${(settings.transparency * 100).toInt()}%", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                Slider(
                                    value = settings.transparency,
                                    onValueChange = { onUpdateSettings(settings.copy(transparency = it)) },
                                    valueRange = 0.15f..1.0f,
                                    colors = SliderDefaults.colors(thumbColor = Color(0xFF38BDF8), activeTrackColor = Color(0xFF0284C7))
                                )

                                Spacer(modifier = Modifier.height(8.dp))
                                Text("Размер ячейки сетки (детализация): ${"%.1f".format(settings.voxelXy)} мм", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                Slider(
                                    value = settings.voxelXy.toFloat().coerceIn(0.5f, 5.0f),
                                    onValueChange = { onUpdateSettings(settings.copy(voxelXy = it.toDouble(), autoVoxelXy = false)) },
                                    valueRange = 0.5f..5.0f,
                                    colors = SliderDefaults.colors(thumbColor = Color(0xFF38BDF8), activeTrackColor = Color(0xFF0284C7))
                                )
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    listOf(
                                        Pair(0.5, "0.5 мм"),
                                        Pair(1.0, "1.0 мм"),
                                        Pair(1.5, "1.5 мм"),
                                        Pair(3.0, "3.0 мм")
                                    ).forEach { (size, label) ->
                                        val isSel = kotlin.math.abs(settings.voxelXy - size) < 0.1
                                        FilterChip(
                                            selected = isSel,
                                            onClick = { onUpdateSettings(settings.copy(voxelXy = size, autoVoxelXy = false)) },
                                            label = { Text(label, fontSize = 10.sp) },
                                            colors = FilterChipDefaults.filterChipColors(
                                                selectedContainerColor = Color(0xFF059669),
                                                selectedLabelColor = Color.White
                                            ),
                                            modifier = Modifier.height(28.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(6.dp))

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(
                                        checked = settings.ignoreRapidInMaterial,
                                        onCheckedChange = { onUpdateSettings(settings.copy(ignoreRapidInMaterial = it)) },
                                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Игнорировать RAPID в материале", color = Color.White, fontSize = 13.sp)
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(
                                        checked = settings.rapidDash,
                                        onCheckedChange = { onUpdateSettings(settings.copy(rapidDash = it)) },
                                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Отображать G0 (RAPID) пунктиром", color = Color.White, fontSize = 13.sp)
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(
                                        checked = settings.autoVoxelXy,
                                        onCheckedChange = { onUpdateSettings(settings.copy(autoVoxelXy = it)) },
                                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Авто-размер сетки (1/3 диаметра фрезы)", color = Color.White, fontSize = 13.sp)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
