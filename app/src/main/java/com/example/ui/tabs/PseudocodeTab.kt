package com.example.ui.tabs

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
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
import com.example.core.CommandsDef
import com.example.model.Command

@Composable
fun PseudocodeTab(
    commands: List<Command>,
    selectedIndex: Int,
    collisionCommandIndices: Set<Int>,
    onSelectIndex: (Int) -> Unit,
    onAddCommand: () -> Unit,
    onEditCommand: (Int) -> Unit,
    onDeleteCommand: (Int) -> Unit,
    onMoveCommand: (Int, Int) -> Unit,
    onDuplicateCommand: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()

    LaunchedEffect(selectedIndex) {
        if (selectedIndex in commands.indices) {
            listState.animateScrollToItem(selectedIndex.coerceAtLeast(0))
        }
    }

    Column(modifier = modifier.fillMaxSize().background(Color(0xFF0F172A))) {
        // Quick Action Bar for Commands (touch-first)
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
                    onClick = onAddCommand,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.height(40.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Команда", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = { if (selectedIndex >= 0) onEditCommand(selectedIndex) },
                        enabled = selectedIndex in commands.indices,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            Icons.Default.Edit,
                            contentDescription = "Изменить",
                            tint = if (selectedIndex in commands.indices) Color(0xFF38BDF8) else Color(0xFF475569)
                        )
                    }

                    IconButton(
                        onClick = { if (selectedIndex >= 0) onDuplicateCommand(selectedIndex) },
                        enabled = selectedIndex in commands.indices,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            Icons.Default.ContentCopy,
                            contentDescription = "Дублировать",
                            tint = if (selectedIndex in commands.indices) Color(0xFFCBD5E1) else Color(0xFF475569)
                        )
                    }

                    IconButton(
                        onClick = { if (selectedIndex > 0) onMoveCommand(selectedIndex, -1) },
                        enabled = selectedIndex > 0,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            Icons.Default.ArrowUpward,
                            contentDescription = "Вверх",
                            tint = if (selectedIndex > 0) Color(0xFFCBD5E1) else Color(0xFF475569)
                        )
                    }

                    IconButton(
                        onClick = { if (selectedIndex in 0 until commands.size - 1) onMoveCommand(selectedIndex, 1) },
                        enabled = selectedIndex in 0 until commands.size - 1,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            Icons.Default.ArrowDownward,
                            contentDescription = "Вниз",
                            tint = if (selectedIndex in 0 until commands.size - 1) Color(0xFFCBD5E1) else Color(0xFF475569)
                        )
                    }

                    IconButton(
                        onClick = { if (selectedIndex in commands.indices) onDeleteCommand(selectedIndex) },
                        enabled = selectedIndex in commands.indices,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            Icons.Default.Delete,
                            contentDescription = "Удалить",
                            tint = if (selectedIndex in commands.indices) Color(0xFFEF4444) else Color(0xFF475569)
                        )
                    }
                }
            }
        }

        // Commands List
        if (commands.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.Code, contentDescription = null, tint = Color(0xFF475569), modifier = Modifier.size(48.dp))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Программа пуста", color = Color(0xFF94A3B8), fontSize = 16.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Нажмите «+ Команда», чтобы добавить перемещение", color = Color(0xFF64748B), fontSize = 12.sp)
                }
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                itemsIndexed(commands) { index, cmd ->
                    val isSelected = index == selectedIndex
                    val hasCollision = index in collisionCommandIndices
                    val def = CommandsDef.DEFINITIONS[cmd.mnemonic]
                    val group = def?.group ?: "MISC"

                    val groupColor = when (group) {
                        "MOTION" -> Color(0xFF0284C7)
                        "CANNED" -> Color(0xFF8B5CF6)
                        "TOOL", "SPINDLE" -> Color(0xFFF59E0B)
                        "PSEUDO" -> Color(0xFF10B981)
                        "OFFSET", "PLANE" -> Color(0xFFEC4899)
                        else -> Color(0xFF64748B)
                    }

                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = when {
                            hasCollision -> Color(0x33EF4444)
                            isSelected -> Color(0xFF1E293B)
                            else -> Color(0xFF131D31)
                        },
                        border = when {
                            hasCollision -> androidx.compose.foundation.BorderStroke(1.5.dp, Color(0xFFEF4444))
                            isSelected -> androidx.compose.foundation.BorderStroke(1.5.dp, Color(0xFF38BDF8))
                            else -> null
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 2.dp)
                            .clickable {
                                onSelectIndex(index)
                            }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 10.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Line Number
                            Text(
                                text = "N%03d".format((index + 1) * 10),
                                color = if (isSelected) Color(0xFF38BDF8) else Color(0xFF64748B),
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                modifier = Modifier.width(42.dp)
                            )

                            // Mnemonic Badge
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = groupColor.copy(alpha = 0.2f),
                                border = androidx.compose.foundation.BorderStroke(1.dp, groupColor),
                                modifier = Modifier.padding(horizontal = 4.dp)
                            ) {
                                Text(
                                    text = cmd.mnemonic,
                                    color = groupColor,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = FontFamily.Monospace,
                                    modifier = Modifier.padding(horizontal = 5.dp, vertical = 2.dp)
                                )
                            }

                            Spacer(modifier = Modifier.width(6.dp))

                            // Parameters & Description
                            Column(modifier = Modifier.weight(1f)) {
                                if (cmd.mnemonic == "#") {
                                    Text(
                                        text = "; ${cmd.params["text"] ?: cmd.raw}",
                                        color = Color(0xFF94A3B8),
                                        fontSize = 12.sp,
                                        fontStyle = androidx.compose.ui.text.font.FontStyle.Italic
                                    )
                                } else {
                                    val paramStr = cmd.params.entries.joinToString(" ") { (k, v) ->
                                        if (v is Double) "$k=%.2f".format(v).trimEnd('0').trimEnd('.') else "$k=$v"
                                    }
                                    if (paramStr.isNotEmpty()) {
                                        Text(
                                            text = paramStr,
                                            color = Color.White,
                                            fontSize = 12.sp,
                                            fontFamily = FontFamily.Monospace,
                                            fontWeight = FontWeight.Medium
                                        )
                                    } else {
                                        Text(
                                            text = def?.description ?: cmd.mnemonic,
                                            color = Color(0xFFCBD5E1),
                                            fontSize = 12.sp
                                        )
                                    }
                                }
                            }

                            // Collision Warning Badge
                            if (hasCollision) {
                                Icon(
                                    Icons.Default.Warning,
                                    contentDescription = "Коллизия",
                                    tint = Color(0xFFEF4444),
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
