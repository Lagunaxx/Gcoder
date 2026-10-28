package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainMenuSheet(
    onDismiss: () -> Unit,
    onNewProject: () -> Unit,
    onLoadDemo: () -> Unit,
    onSaveProject: () -> Unit,
    onOpenProject: () -> Unit,
    onExportGCode: () -> Unit,
    onImportGCode: () -> Unit,
    onEditStock: () -> Unit,
    onOpenTools: () -> Unit,
    onOpenFunctions: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenHelp: () -> Unit,
    onRegenerate: () -> Unit
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1E293B),
        tonalElevation = 8.dp,
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 32.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Menu, contentDescription = null, tint = Color(0xFF38BDF8))
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("Главное меню", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "Закрыть", tint = Color(0xFF94A3B8))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Section: Проект
            MenuSectionHeader("ПРОЕКТ И ФАЙЛЫ")
            MenuItem(
                icon = Icons.Default.AddBox,
                title = "Новый проект",
                subtitle = "Очистить псевдокод и начать с нуля",
                tint = Color(0xFF38BDF8),
                onClick = { onDismiss(); onNewProject() }
            )
            MenuItem(
                icon = Icons.Default.PlayCircleOutline,
                title = "Загрузить пример (демо)",
                subtitle = "Карман + сверление отверстия",
                tint = Color(0xFF4ADE80),
                onClick = { onDismiss(); onLoadDemo() }
            )
            MenuItem(
                icon = Icons.Default.Save,
                title = "Сохранить проект",
                subtitle = "Сохранить команды, инструменты, переменные",
                tint = Color(0xFFF59E0B),
                onClick = { onDismiss(); onSaveProject() }
            )
            MenuItem(
                icon = Icons.Default.FolderOpen,
                title = "Открыть проект",
                subtitle = "Загрузить ранее сохраненный проект",
                tint = Color(0xFFCBD5E1),
                onClick = { onDismiss(); onOpenProject() }
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Section: G-код и экспорт
            MenuSectionHeader("G-КОД И СТАНОК")
            MenuItem(
                icon = Icons.Default.FileDownload,
                title = "Экспорт G-кода",
                subtitle = "Сохранить файл .tap / .nc / .gcode для станка",
                tint = Color(0xFF38BDF8),
                onClick = { onDismiss(); onExportGCode() }
            )
            MenuItem(
                icon = Icons.Default.FileUpload,
                title = "Импорт G-кода",
                subtitle = "Преобразовать файл G-кода в псевдокод",
                tint = Color(0xFFF59E0B),
                onClick = { onDismiss(); onImportGCode() }
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Section: Настройки и параметры
            MenuSectionHeader("УСТАНОВКИ И НАСТРОЙКИ")
            MenuItem(
                icon = Icons.Default.CropFree,
                title = "Параметры заготовки",
                subtitle = "Размеры X/Y/Z, смещение нуля и цвет",
                tint = Color(0xFFA855F7),
                onClick = { onDismiss(); onEditStock() }
            )
            MenuItem(
                icon = Icons.Default.Build,
                title = "Список инструментов",
                subtitle = "Настройка диаметров, подач и оборотов фрез",
                tint = Color(0xFF38BDF8),
                onClick = { onDismiss(); onOpenTools() }
            )
            MenuItem(
                icon = Icons.Default.AutoStories,
                title = "Библиотека функций",
                subtitle = "Шаблоны сетки отверстий, карманов и смены фрезы",
                tint = Color(0xFF10B981),
                onClick = { onDismiss(); onOpenFunctions() }
            )
            MenuItem(
                icon = Icons.Default.Refresh,
                title = "Пересчитать симуляцию",
                subtitle = "Обновить 3D модель и проверить коллизии",
                tint = Color(0xFF4ADE80),
                onClick = { onDismiss(); onRegenerate() }
            )
            MenuItem(
                icon = Icons.Default.GridOn,
                title = "Настройка сетки (детализация)",
                subtitle = "Размер ячейки, качество и скорость симуляции",
                tint = Color(0xFF38BDF8),
                onClick = { onDismiss(); onOpenSettings() }
            )
            MenuItem(
                icon = Icons.Default.Tune,
                title = "Параметры симулятора",
                subtitle = "Точность сетки, линии перемещений",
                tint = Color(0xFF94A3B8),
                onClick = { onDismiss(); onOpenSettings() }
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Section: Справка
            MenuSectionHeader("ПОМОЩЬ")
            MenuItem(
                icon = Icons.Default.HelpOutline,
                title = "Справка и руководство (F1)",
                subtitle = "Как пользоваться, справочник кодов, советы",
                tint = Color(0xFF38BDF8),
                onClick = { onDismiss(); onOpenHelp() }
            )
        }
    }
}

@Composable
private fun MenuSectionHeader(title: String) {
    Text(
        text = title,
        color = Color(0xFF64748B),
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(vertical = 4.dp, horizontal = 4.dp)
    )
}

@Composable
private fun MenuItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    tint: Color,
    onClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color(0xFF0F172A),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp)
            .clickable(onClick = onClick)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(24.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(title, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                Text(subtitle, color = Color(0xFF94A3B8), fontSize = 11.sp)
            }
            Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color(0xFF475569), modifier = Modifier.size(18.dp))
        }
    }
}
