package com.example.ui.dialogs

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog

@Composable
fun HelpDialog(onDismiss: () -> Unit) {
    var selectedSection by remember { mutableIntStateOf(0) }
    val sections = listOf("Быстрый старт", "3D навигация", "Команды", "Формулы", "Коллизии")

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF1E293B),
            tonalElevation = 8.dp,
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.85f)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Справка и руководство",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Закрыть", tint = Color(0xFF94A3B8))
                    }
                }

                ScrollableTabRow(
                    selectedTabIndex = selectedSection,
                    edgePadding = 0.dp,
                    containerColor = Color(0xFF0F172A),
                    contentColor = Color(0xFF38BDF8),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp)
                ) {
                    sections.forEachIndexed { idx, title ->
                        Tab(
                            selected = selectedSection == idx,
                            onClick = { selectedSection = idx },
                            text = { Text(title, fontSize = 12.sp) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                Column(
                    modifier = Modifier
                        .weight(1f)
                        .verticalScroll(rememberScrollState())
                ) {
                    when (selectedSection) {
                        0 -> {
                            HelpCard(
                                title = "Что умеет приложение?",
                                text = "Mach3 G-Code — это карманная CAM-система для ЧПУ станков. Вы составляете программу на простом псевдокоде, приложение автоматически переводит её в чистый G-код для Mach3 и сразу показывает 3D симуляцию обработки деталей!"
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            HelpCard(
                                title = "Шаги работы:",
                                text = "1. Задайте инструменты во вкладке «Инструменты» (диаметр, подача, обороты).\n2. Добавьте команды кнопкой «+ Команда» во вкладке «Псевдокод».\n3. Проверьте траекторию в 3D окне сверху и запустите анимацию фрезы кнопкой Play.\n4. Перейдите во вкладку «G-код» и нажмите «Экспорт» или «Копировать» для станка."
                            )
                        }
                        1 -> {
                            HelpCard(
                                title = "Сенсорное управление 3D-видом:",
                                text = "• Вращение: проведите одним пальцем по 3D экрану в любую сторону для свободного 3D обзора.\n• Масштабирование: щипок двумя пальцами (Pinch-to-zoom) приближает или отдаляет деталь.\n• Перемещение: сдвиг двумя пальцами перемещает камеру.\n• Кнопки XY и XZ в верхнем правом углу переключают вид строго сверху или спереди.\n• Кнопка с кубом переключает в красивую изометрию."
                            )
                        }
                        2 -> {
                            HelpCard(
                                title = "Основные команды псевдокода:",
                                text = "• RAPID (G0) — быстрое перемещение на холостом ходу над заготовкой.\n• FEED (G1) — рабочий рез по прямой с подачей F.\n• ARC_CW (G2) / ARC_CCW (G3) — фрезерование дуг и окружностей.\n• DRILL (G81) / PECK (G83) — циклы сверления отверстий с отводом стружки.\n• SPIN (M3/M5) — включение и останов шпинделя.\n• TOOL (T... M6) — смена инструмента.\n• CALL_FUNC — вызов готовых шаблонов (сетка отверстий, карманы, смена инструмента)."
                            )
                        }
                        3 -> {
                            HelpCard(
                                title = "Переменные и формулы:",
                                text = "Любой параметр команды (X, Y, Z, глубина, число шагов) можно задавать формулой в фигурных скобках:\n\n• {W/2} — половина ширины заготовки\n• {#200 * STEP} — умножение шага на счетчик цикла\n• {L - 10} — отступ 10 мм от края\n• {sin(30 * pi / 180) * R} — тригонометрические расчеты"
                            )
                        }
                        4 -> {
                            HelpCard(
                                title = "Автоматический поиск коллизий:",
                                text = "Симулятор контролирует безопасность обработки:\n\n1. ⛔ RAPID в материале: холостое ускоренное перемещение G0 ниже верхней поверхности заготовки.\n2. ⛔ FEED без шпинделя: попытка врезаться в материал при выключенном шпинделе (M5).\n\nВсе коллизии подсвечиваются красным в 3D и перечисляются во вкладке «Журнал»."
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                Button(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7))
                ) {
                    Text("Понятно", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun HelpCard(title: String, text: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFF0F172A),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(title, color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(modifier = Modifier.height(6.dp))
            Text(text, color = Color(0xFFCBD5E1), fontSize = 13.sp, lineHeight = 18.sp)
        }
    }
}
