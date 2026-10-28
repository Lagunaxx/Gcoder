package com.example.ui.tabs

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun GCodeTab(
    gcodeLines: List<String>,
    unrollLoops: Boolean,
    onToggleUnrollLoops: (Boolean) -> Unit,
    onExportGCode: () -> Unit,
    onImportGCode: () -> Unit,
    modifier: Modifier = Modifier
) {
    val clipboardManager = LocalClipboardManager.current
    val context = LocalContext.current

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
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = unrollLoops,
                        onCheckedChange = onToggleUnrollLoops,
                        colors = CheckboxDefaults.colors(checkedColor = Color(0xFF0284C7))
                    )
                    Text("Развернуть IF/GOTO", color = Color(0xFFCBD5E1), fontSize = 12.sp)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = {
                            val text = gcodeLines.joinToString("\n")
                            clipboardManager.setText(AnnotatedString(text))
                            Toast.makeText(context, "G-код скопирован в буфер", Toast.LENGTH_SHORT).show()
                        },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.ContentCopy, contentDescription = "Копировать", tint = Color(0xFF38BDF8))
                    }

                    IconButton(
                        onClick = onExportGCode,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.FileDownload, contentDescription = "Экспорт G-кода", tint = Color(0xFF4ADE80))
                    }

                    IconButton(
                        onClick = onImportGCode,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.FileUpload, contentDescription = "Импорт G-кода", tint = Color(0xFFF59E0B))
                    }
                }
            }
        }

        // G-Code Display with Line numbers
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            itemsIndexed(gcodeLines) { index, line ->
                val lineTrimmed = line.trim()
                val isComment = lineTrimmed.startsWith("(") || lineTrimmed.startsWith(";")
                val isM30 = lineTrimmed.contains("M30")
                val isRapid = lineTrimmed.contains("G0") || lineTrimmed.contains("G00")
                val isFeed = lineTrimmed.contains("G1") || lineTrimmed.contains("G01")
                val isTool = lineTrimmed.contains("M6") || lineTrimmed.contains("T")

                val textColor = when {
                    isComment -> Color(0xFF64748B)
                    isM30 -> Color(0xFFEF4444)
                    isRapid -> Color(0xFF38BDF8)
                    isFeed -> Color(0xFF4ADE80)
                    isTool -> Color(0xFFFBBF24)
                    else -> Color(0xFFE2E8F0)
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 1.dp)
                ) {
                    Text(
                        text = "%3d".format(index + 1),
                        color = Color(0xFF475569),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        modifier = Modifier.width(32.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = line,
                        color = textColor,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        fontWeight = if (isRapid || isFeed || isTool) FontWeight.SemiBold else FontWeight.Normal
                    )
                }
            }
        }
    }
}
