package com.example.ui.tabs

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.Tool

@Composable
fun ToolsTab(
    tools: List<Tool>,
    onAddTool: () -> Unit,
    onEditTool: (Tool) -> Unit,
    onDeleteTool: (Tool) -> Unit,
    onExportCsv: () -> Unit,
    onImportCsv: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
    ) {
        // Toolbar
        Surface(
            color = Color(0xFF1E293B),
            tonalElevation = 2.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 8.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    onClick = onAddTool,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.height(40.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Инструмент", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = onExportCsv, modifier = Modifier.size(40.dp)) {
                        Icon(Icons.Default.FileDownload, contentDescription = "Экспорт CSV", tint = Color(0xFF38BDF8))
                    }
                    IconButton(onClick = onImportCsv, modifier = Modifier.size(40.dp)) {
                        Icon(Icons.Default.FileUpload, contentDescription = "Импорт CSV", tint = Color(0xFFF59E0B))
                    }
                }
            }
        }

        // Tools List
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            items(tools) { tool ->
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFF1E293B),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 3.dp)
                        .clickable { onEditTool(tool) }
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Tool color dot
                        Box(
                            modifier = Modifier
                                .size(24.dp)
                                .background(parseColor(tool.color), CircleShape)
                                .border(1.5.dp, Color.White.copy(alpha = 0.5f), CircleShape)
                        )

                        Spacer(modifier = Modifier.width(10.dp))

                        // Details
                        Column(modifier = Modifier.weight(1f)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = "T${tool.number}: ${tool.name}",
                                    color = Color.White,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "Ø ${tool.diameter} мм • F: ${tool.feed.toInt()} мм/мин • ${tool.rpm} об/мин",
                                color = Color(0xFF94A3B8),
                                fontSize = 12.sp
                            )
                        }

                        IconButton(
                            onClick = { onEditTool(tool) },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(Icons.Default.Edit, contentDescription = "Изменить", tint = Color(0xFF38BDF8), modifier = Modifier.size(18.dp))
                        }

                        if (tools.size > 1) {
                            IconButton(
                                onClick = { onDeleteTool(tool) },
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(Icons.Default.Delete, contentDescription = "Удалить", tint = Color(0xFFEF4444), modifier = Modifier.size(18.dp))
                            }
                        }
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
