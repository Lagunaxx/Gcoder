package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
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

@Composable
fun PlayController(
    currentStep: Int,
    totalSteps: Int,
    isPlaying: Boolean,
    speedMultiplier: Float,
    onStepChange: (Int) -> Unit,
    onPlayPauseToggle: () -> Unit,
    onRewind: () -> Unit,
    onFastForward: () -> Unit,
    onSpeedChange: (Float) -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = Color(0xFF1E293B),
        tonalElevation = 4.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 6.dp)
        ) {
            // Slider and step numbers
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Шаг: $currentStep / ${maxOf(0, totalSteps - 1)}",
                    color = Color(0xFF94A3B8),
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.width(110.dp)
                )

                Slider(
                    value = if (totalSteps > 1) currentStep.toFloat() else 0f,
                    onValueChange = { onStepChange(it.toInt()) },
                    valueRange = 0f..maxOf(1f, (totalSteps - 1).toFloat()),
                    modifier = Modifier.weight(1f),
                    colors = SliderDefaults.colors(
                        thumbColor = Color(0xFF38BDF8),
                        activeTrackColor = Color(0xFF0284C7),
                        inactiveTrackColor = Color(0xFF334155)
                    )
                )
            }

            // Controls row: Rewind, Step-, Play/Pause, Step+, End, Speed
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Rewind to start
                    IconButton(
                        onClick = onRewind,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.SkipPrevious, contentDescription = "В начало", tint = Color.White)
                    }

                    // Step back
                    IconButton(
                        onClick = { onStepChange(maxOf(0, currentStep - 1)) },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.FastRewind, contentDescription = "Шаг назад", tint = Color(0xFFCBD5E1))
                    }

                    Spacer(modifier = Modifier.width(4.dp))

                    // Play/Pause Big Button
                    FilledIconButton(
                        onClick = onPlayPauseToggle,
                        modifier = Modifier.size(44.dp),
                        colors = IconButtonDefaults.filledIconButtonColors(
                            containerColor = if (isPlaying) Color(0xFFF59E0B) else Color(0xFF0284C7)
                        )
                    ) {
                        Icon(
                            if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                            contentDescription = if (isPlaying) "Пауза" else "Пуск",
                            tint = Color.White,
                            modifier = Modifier.size(24.dp)
                        )
                    }

                    Spacer(modifier = Modifier.width(4.dp))

                    // Step forward
                    IconButton(
                        onClick = { onStepChange(minOf(maxOf(0, totalSteps - 1), currentStep + 1)) },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.FastForward, contentDescription = "Шаг вперед", tint = Color(0xFFCBD5E1))
                    }

                    // To end
                    IconButton(
                        onClick = onFastForward,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(Icons.Default.SkipNext, contentDescription = "В конец", tint = Color.White)
                    }
                }

                // Speed buttons (1x, 2x, 5x)
                Row(
                    modifier = Modifier
                        .background(Color(0xFF0F172A), RoundedCornerShape(8.dp))
                        .padding(2.dp)
                ) {
                    val speeds = listOf(1f, 2f, 5f)
                    for (sp in speeds) {
                        val active = speedMultiplier == sp
                        TextButton(
                            onClick = { onSpeedChange(sp) },
                            contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp),
                            modifier = Modifier
                                .height(28.dp)
                                .background(
                                    if (active) Color(0xFF0284C7) else Color.Transparent,
                                    RoundedCornerShape(6.dp)
                                )
                        ) {
                            Text(
                                text = "${sp.toInt()}x",
                                color = if (active) Color.White else Color(0xFF94A3B8),
                                fontSize = 11.sp,
                                fontWeight = if (active) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    }
                }
            }
        }
    }
}
