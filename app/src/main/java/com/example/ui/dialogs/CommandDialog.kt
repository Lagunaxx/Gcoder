package com.example.ui.dialogs

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.window.Dialog
import com.example.core.CommandsDef
import com.example.model.Command
import com.example.model.FunctionDef

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CommandDialog(
    initialCommand: Command? = null,
    functions: List<FunctionDef> = emptyList(),
    knownVariables: Map<String, Double> = emptyMap(),
    onDismiss: () -> Unit,
    onConfirm: (Command) -> Unit
) {
    var selectedMnemonic by remember { mutableStateOf(initialCommand?.mnemonic ?: "FEED") }
    var searchQuery by remember { mutableStateOf("") }
    val paramValues = remember {
        mutableStateMapOf<String, String>().apply {
            initialCommand?.params?.forEach { (k, v) ->
                put(k, v.toString())
            }
        }
    }
    var commentText by remember { mutableStateOf(initialCommand?.raw ?: (initialCommand?.params?.get("text")?.toString() ?: "")) }

    val cmdDef = CommandsDef.DEFINITIONS[selectedMnemonic]

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.92f),
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF1E293B),
            tonalElevation = 8.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (initialCommand == null) "Добавить команду" else "Изменить команду",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Закрыть", tint = Color(0xFF94A3B8))
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Search Filter for Mnemonics
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Поиск команды (G0, сверление, шпиндель...)", fontSize = 12.sp) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = Color(0xFF94A3B8)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF38BDF8),
                        unfocusedBorderColor = Color(0xFF475569)
                    )
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Horizontal chips / list of filtered commands
                val filteredDefs = CommandsDef.DEFINITIONS.values.filter {
                    searchQuery.isBlank() ||
                            it.mnemonic.contains(searchQuery, ignoreCase = true) ||
                            it.description.contains(searchQuery, ignoreCase = true) ||
                            it.group.contains(searchQuery, ignoreCase = true)
                }

                ScrollableTabRow(
                    selectedTabIndex = filteredDefs.indexOfFirst { it.mnemonic == selectedMnemonic }.coerceAtLeast(0),
                    edgePadding = 0.dp,
                    containerColor = Color(0xFF0F172A),
                    contentColor = Color(0xFF38BDF8),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp)
                ) {
                    filteredDefs.forEach { def ->
                        val isSelected = def.mnemonic == selectedMnemonic
                        Tab(
                            selected = isSelected,
                            onClick = {
                                selectedMnemonic = def.mnemonic
                                // populate default params if empty
                                def.params.forEach { p ->
                                    if (!paramValues.containsKey(p.name)) {
                                        paramValues[p.name] = p.defaultVal.toString()
                                    }
                                }
                            },
                            text = {
                                Text(
                                    text = def.mnemonic,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 12.sp
                                )
                            }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Description card
                cmdDef?.let {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = Color(0xFF0F172A),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Row(modifier = Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Info, contentDescription = null, tint = Color(0xFF38BDF8), modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "${it.mnemonic}: ${it.description}",
                                color = Color(0xFFE2E8F0),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Parameters Form
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .verticalScroll(rememberScrollState())
                ) {
                    if (selectedMnemonic == "#") {
                        OutlinedTextField(
                            value = commentText,
                            onValueChange = { commentText = it },
                            label = { Text("Текст комментария") },
                            modifier = Modifier.fillMaxWidth(),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White
                            )
                        )
                    } else if (selectedMnemonic == "CALL_FUNC") {
                        // Function Picker
                        Text("Выберите функцию:", color = Color(0xFF94A3B8), fontSize = 12.sp)
                        val selectedFnName = paramValues["name"] ?: functions.firstOrNull()?.name ?: ""

                        var expandedFn by remember { mutableStateOf(false) }
                        ExposedDropdownMenuBox(
                            expanded = expandedFn,
                            onExpandedChange = { expandedFn = !expandedFn }
                        ) {
                            OutlinedTextField(
                                value = selectedFnName,
                                onValueChange = {},
                                readOnly = true,
                                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expandedFn) },
                                modifier = Modifier
                                    .menuAnchor()
                                    .fillMaxWidth(),
                                colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                            )
                            ExposedDropdownMenu(
                                expanded = expandedFn,
                                onDismissRequest = { expandedFn = false }
                            ) {
                                functions.forEach { fn ->
                                    DropdownMenuItem(
                                        text = { Text("${fn.name} — ${fn.title}") },
                                        onClick = {
                                            paramValues["name"] = fn.name
                                            fn.params.forEach { p ->
                                                paramValues["p_${p.name}"] = p.defaultVal
                                            }
                                            expandedFn = false
                                        }
                                    )
                                }
                            }
                        }

                        val activeFn = functions.find { it.name == selectedFnName }
                        if (activeFn != null) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Параметры функции:", color = Color(0xFF38BDF8), fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            activeFn.params.forEach { prm ->
                                val pkey = "p_${prm.name}"
                                OutlinedTextField(
                                    value = paramValues[pkey] ?: prm.defaultVal,
                                    onValueChange = { paramValues[pkey] = it },
                                    label = { Text("${prm.name} (${prm.description})") },
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp),
                                    colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                                )
                            }
                        }
                    } else {
                        cmdDef?.params?.forEach { p ->
                            val curVal = paramValues[p.name] ?: p.defaultVal.toString()
                            if (p.type == "op") {
                                // Dropdown for IF operations
                                var expandedOp by remember { mutableStateOf(false) }
                                ExposedDropdownMenuBox(
                                    expanded = expandedOp,
                                    onExpandedChange = { expandedOp = !expandedOp }
                                ) {
                                    OutlinedTextField(
                                        value = curVal,
                                        onValueChange = {},
                                        readOnly = true,
                                        label = { Text("Условие сравнения") },
                                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expandedOp) },
                                        modifier = Modifier
                                            .menuAnchor()
                                            .fillMaxWidth()
                                            .padding(vertical = 4.dp),
                                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                                    )
                                    ExposedDropdownMenu(
                                        expanded = expandedOp,
                                        onDismissRequest = { expandedOp = false }
                                    ) {
                                        listOf("EQ", "NE", "GT", "LT", "GE", "LE").forEach { op ->
                                            DropdownMenuItem(
                                                text = { Text(op) },
                                                onClick = {
                                                    paramValues[p.name] = op
                                                    expandedOp = false
                                                }
                                            )
                                        }
                                    }
                                }
                            } else {
                                OutlinedTextField(
                                    value = curVal,
                                    onValueChange = { paramValues[p.name] = it },
                                    label = { Text("${p.name} — ${p.description}") },
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedTextColor = Color.White,
                                        unfocusedTextColor = Color.White,
                                        focusedBorderColor = Color(0xFF38BDF8),
                                        unfocusedBorderColor = Color(0xFF475569)
                                    )
                                )
                            }
                        }
                    }

                    // Formula hint card
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Поддерживаются формулы: {W/2}, {L*STEP+1}, {#200*5}, min, max, sin, cos, pi",
                        color = Color(0xFF64748B),
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Actions: Cancel & OK
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier.height(48.dp)
                    ) {
                        Text("Отмена", color = Color(0xFF94A3B8))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            val finalParams = mutableMapOf<String, Any>()
                            if (selectedMnemonic == "#") {
                                finalParams["text"] = commentText
                            } else {
                                cmdDef?.params?.forEach { p ->
                                    val strVal = paramValues[p.name] ?: p.defaultVal.toString()
                                    when (p.type) {
                                        "int" -> {
                                            val num = strVal.toIntOrNull()
                                            finalParams[p.name] = num ?: strVal
                                        }
                                        "float" -> {
                                            val num = strVal.toDoubleOrNull()
                                            finalParams[p.name] = num ?: strVal
                                        }
                                        else -> finalParams[p.name] = strVal
                                    }
                                }
                                if (selectedMnemonic == "CALL_FUNC") {
                                    paramValues.forEach { (k, v) ->
                                        finalParams[k] = v
                                    }
                                }
                            }
                            onConfirm(Command(selectedMnemonic, finalParams, commentText))
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        modifier = Modifier.height(48.dp)
                    ) {
                        Icon(Icons.Default.Check, contentDescription = null, tint = Color.White)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Применить", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
