package com.example.ui

import android.content.res.Configuration
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.Command
import com.example.model.Tool
import com.example.model.UserVar
import com.example.ui.components.PlayController
import com.example.ui.components.Touch3DView
import com.example.ui.components.rememberCamera3DState
import com.example.ui.dialogs.*
import com.example.ui.tabs.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel) {
    val context = LocalContext.current
    val configuration = LocalConfiguration.current
    val isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    // State flows
    val tools by viewModel.tools.collectAsState()
    val variables by viewModel.variables.collectAsState()
    val stock by viewModel.stock.collectAsState()
    val commands by viewModel.commands.collectAsState()
    val functions by viewModel.functions.collectAsState()
    val preamble by viewModel.preamble.collectAsState()
    val postamble by viewModel.postamble.collectAsState()
    val settings by viewModel.settings.collectAsState()

    val gcodeLines by viewModel.gcodeLines.collectAsState()
    val segments by viewModel.simulationSegments.collectAsState()
    val bounds by viewModel.simulationBounds.collectAsState()
    val stats by viewModel.simulationStats.collectAsState()
    val collisionIndices by viewModel.collisionIndices.collectAsState()
    val evaluatedVars by viewModel.evaluatedVars.collectAsState()
    val heightMap by viewModel.heightMap.collectAsState()

    val selectedCmdIndex by viewModel.selectedCommandIndex.collectAsState()
    val currentStepIndex by viewModel.currentStepIndex.collectAsState()
    val isPlaying by viewModel.isPlaying.collectAsState()
    val speedMultiplier by viewModel.speedMultiplier.collectAsState()

    // Interactive window split ratio (Requirement 1)
    var splitRatio by remember { mutableFloatStateOf(if (isLandscape) 0.50f else 0.46f) }

    // UI Navigation Tab in Work Area (Requirement 2)
    var activeWorkTab by remember { mutableIntStateOf(0) }
    val workTabTitles = listOf("Псевдокод", "G-код", "Инструменты", "Журнал", "Остальное")

    // Dialogs state
    var showMainMenu by remember { mutableStateOf(false) }
    var showCommandDialog by remember { mutableStateOf(false) }
    var commandToEdit by remember { mutableStateOf<Pair<Int, Command>?>(null) }
    var showToolDialog by remember { mutableStateOf(false) }
    var toolToEdit by remember { mutableStateOf<Tool?>(null) }
    var showVarDialog by remember { mutableStateOf(false) }
    var varToEdit by remember { mutableStateOf<UserVar?>(null) }
    var showStockDialog by remember { mutableStateOf(false) }
    var showHelpDialog by remember { mutableStateOf(false) }
    var showGCodeImportDialog by remember { mutableStateOf(false) }
    var showGridSettingsDialog by remember { mutableStateOf(false) }

    val cameraState = rememberCamera3DState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Mach3 G-Code",
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            color = Color.White
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        if (stats.collisionCount > 0) {
                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = Color(0xFFEF4444)
                            ) {
                                Text(
                                    text = "⛔ ${stats.collisionCount}",
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                )
                            }
                        } else {
                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = Color(0xFF065F46)
                            ) {
                                Text(
                                    text = "✓ OK",
                                    color = Color(0xFF34D399),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                },
                actions = {
                    Button(
                        onClick = { showMainMenu = true },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                        modifier = Modifier
                            .height(38.dp)
                            .padding(end = 8.dp)
                    ) {
                        Icon(Icons.Default.Menu, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Меню", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1E293B),
                    titleContentColor = Color.White
                )
            )
        }
    ) { innerPadding ->
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFF0F172A))
        ) {
            val totalWidth = maxWidth
            val totalHeight = maxHeight
            val density = LocalDensity.current

            if (isLandscape) {
                // Landscape: Horizontal split with interactive draggable vertical divider
                val totalWidthPx = with(density) { totalWidth.toPx() }
                val leftWidth = (totalWidth * splitRatio).coerceIn(200.dp, totalWidth - 250.dp)
                val rightWidth = totalWidth - leftWidth - 20.dp

                Row(modifier = Modifier.fillMaxSize()) {
                    // Left: 3D Simulation + PlayController
                    Column(
                        modifier = Modifier
                            .width(leftWidth)
                            .fillMaxHeight()
                    ) {
                        Box(modifier = Modifier.weight(1f)) {
                            Touch3DView(
                                segments = segments,
                                stock = stock,
                                bounds = bounds,
                                heightMap = heightMap,
                                currentStepIndex = currentStepIndex,
                                gridSizeMm = settings.voxelXy,
                                cameraState = cameraState,
                                showToolpath = settings.showToolpath,
                                showMaterial = settings.showMaterial,
                                shadingMode = settings.shadingMode,
                                transparency = settings.transparency,
                                onToggleToolpath = { viewModel.toggleShowToolpath(it) },
                                onToggleMaterial = { viewModel.toggleShowMaterial(it) },
                                onChangeShadingMode = { viewModel.updateShadingMode(it) },
                                onChangeTransparency = { viewModel.updateTransparency(it) },
                                onChangeGridSize = { viewModel.updateGridSize(it) }
                            )
                        }
                        PlayController(
                            currentStep = currentStepIndex,
                            totalSteps = segments.size,
                            isPlaying = isPlaying,
                            speedMultiplier = speedMultiplier,
                            onStepChange = { viewModel.setStepIndex(it) },
                            onPlayPauseToggle = { viewModel.togglePlayPause() },
                            onRewind = { viewModel.rewind() },
                            onFastForward = { viewModel.fastForward() },
                            onSpeedChange = { viewModel.setSpeed(it) }
                        )
                    }

                    // Draggable Vertical Divider Handle
                    Surface(
                        modifier = Modifier
                            .width(20.dp)
                            .fillMaxHeight()
                            .pointerInput(totalWidthPx) {
                                detectHorizontalDragGestures { _, dragAmount ->
                                    if (totalWidthPx > 0f) {
                                        splitRatio = (splitRatio + dragAmount / totalWidthPx).coerceIn(0.20f, 0.80f)
                                    }
                                }
                            },
                        color = Color(0xFF1E293B)
                    ) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Box(
                                modifier = Modifier
                                    .width(4.dp)
                                    .height(48.dp)
                                    .background(Color(0xFF64748B), RoundedCornerShape(2.dp))
                            )
                        }
                    }

                    // Right: Work Area with Tabs
                    Column(
                        modifier = Modifier
                            .width(rightWidth)
                            .fillMaxHeight()
                    ) {
                        WorkTabsHeader(
                            activeTab = activeWorkTab,
                            titles = workTabTitles,
                            collisionCount = stats.collisionCount,
                            onSelectTab = { activeWorkTab = it }
                        )
                        Box(modifier = Modifier.weight(1f)) {
                            WorkTabContent(
                                activeTab = activeWorkTab,
                                viewModel = viewModel,
                                onAddCommand = { showCommandDialog = true },
                                onEditCommand = { idx ->
                                    commandToEdit = Pair(idx, commands[idx])
                                },
                                onAddTool = {
                                    toolToEdit = null
                                    showToolDialog = true
                                },
                                onEditTool = { t ->
                                    toolToEdit = t
                                    showToolDialog = true
                                },
                                onAddVar = {
                                    varToEdit = null
                                    showVarDialog = true
                                },
                                onEditVar = { v ->
                                    varToEdit = v
                                    showVarDialog = true
                                },
                                onEditStock = { showStockDialog = true },
                                onImportGCode = { showGCodeImportDialog = true }
                            )
                        }
                    }
                }
            } else {
                // Portrait: Vertical split with interactive draggable horizontal divider
                val totalHeightPx = with(density) { totalHeight.toPx() }
                val topHeight = (totalHeight * splitRatio).coerceIn(120.dp, totalHeight - 160.dp)
                val bottomHeight = totalHeight - topHeight - 20.dp

                Column(modifier = Modifier.fillMaxSize()) {
                    // Top: 3D Simulation View + PlayController
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(topHeight)
                    ) {
                        Box(modifier = Modifier.weight(1f)) {
                            Touch3DView(
                                segments = segments,
                                stock = stock,
                                bounds = bounds,
                                heightMap = heightMap,
                                currentStepIndex = currentStepIndex,
                                gridSizeMm = settings.voxelXy,
                                cameraState = cameraState,
                                showToolpath = settings.showToolpath,
                                showMaterial = settings.showMaterial,
                                shadingMode = settings.shadingMode,
                                transparency = settings.transparency,
                                onToggleToolpath = { viewModel.toggleShowToolpath(it) },
                                onToggleMaterial = { viewModel.toggleShowMaterial(it) },
                                onChangeShadingMode = { viewModel.updateShadingMode(it) },
                                onChangeTransparency = { viewModel.updateTransparency(it) },
                                onChangeGridSize = { viewModel.updateGridSize(it) }
                            )
                        }
                        PlayController(
                            currentStep = currentStepIndex,
                            totalSteps = segments.size,
                            isPlaying = isPlaying,
                            speedMultiplier = speedMultiplier,
                            onStepChange = { viewModel.setStepIndex(it) },
                            onPlayPauseToggle = { viewModel.togglePlayPause() },
                            onRewind = { viewModel.rewind() },
                            onFastForward = { viewModel.fastForward() },
                            onSpeedChange = { viewModel.setSpeed(it) }
                        )
                    }

                    // Draggable Horizontal Divider Handle
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(20.dp)
                            .pointerInput(totalHeightPx) {
                                detectVerticalDragGestures { _, dragAmount ->
                                    if (totalHeightPx > 0f) {
                                        splitRatio = (splitRatio + dragAmount / totalHeightPx).coerceIn(0.18f, 0.82f)
                                    }
                                }
                            },
                        color = Color(0xFF1E293B)
                    ) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Box(
                                modifier = Modifier
                                    .width(48.dp)
                                    .height(4.dp)
                                    .background(Color(0xFF64748B), RoundedCornerShape(2.dp))
                            )
                        }
                    }

                    // Bottom: Work Area with Tabs (Requirement 2: Smooth Scrolling Tabs)
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(bottomHeight)
                    ) {
                        WorkTabsHeader(
                            activeTab = activeWorkTab,
                            titles = workTabTitles,
                            collisionCount = stats.collisionCount,
                            onSelectTab = { activeWorkTab = it }
                        )
                        Box(modifier = Modifier.weight(1f)) {
                            WorkTabContent(
                                activeTab = activeWorkTab,
                                viewModel = viewModel,
                                onAddCommand = { showCommandDialog = true },
                                onEditCommand = { idx ->
                                    commandToEdit = Pair(idx, commands[idx])
                                },
                                onAddTool = {
                                    toolToEdit = null
                                    showToolDialog = true
                                },
                                onEditTool = { t ->
                                    toolToEdit = t
                                    showToolDialog = true
                                },
                                onAddVar = {
                                    varToEdit = null
                                    showVarDialog = true
                                },
                                onEditVar = { v ->
                                    varToEdit = v
                                    showVarDialog = true
                                },
                                onEditStock = { showStockDialog = true },
                                onImportGCode = { showGCodeImportDialog = true }
                            )
                        }
                    }
                }
            }
        }
    }

    // Modal Main Menu Sheet
    if (showMainMenu) {
        MainMenuSheet(
            onDismiss = { showMainMenu = false },
            onNewProject = {
                viewModel.newProject()
                Toast.makeText(context, "Создан новый проект", Toast.LENGTH_SHORT).show()
            },
            onLoadDemo = {
                viewModel.loadDemoProject()
                Toast.makeText(context, "Загружен пример фрезерования", Toast.LENGTH_SHORT).show()
            },
            onSaveProject = {
                val ok = viewModel.saveProjectToFile()
                Toast.makeText(context, if (ok) "Проект успешно сохранен!" else "Ошибка сохранения", Toast.LENGTH_SHORT).show()
            },
            onOpenProject = {
                val ok = viewModel.loadProjectFromFile()
                Toast.makeText(context, if (ok) "Проект загружен!" else "Сохраненный проект не найден", Toast.LENGTH_SHORT).show()
            },
            onExportGCode = {
                activeWorkTab = 1
                Toast.makeText(context, "Перейдите во вкладку G-код для экспорта", Toast.LENGTH_SHORT).show()
            },
            onImportGCode = {
                showGCodeImportDialog = true
            },
            onEditStock = { showStockDialog = true },
            onOpenTools = { activeWorkTab = 2 },
            onOpenFunctions = { activeWorkTab = 4 },
            onOpenSettings = { activeWorkTab = 4 },
            onOpenHelp = { showHelpDialog = true },
            onRegenerate = {
                viewModel.recalculate()
                Toast.makeText(context, "Симуляция пересчитана", Toast.LENGTH_SHORT).show()
            }
        )
    }

    // Command Dialog (Add)
    if (showCommandDialog) {
        CommandDialog(
            initialCommand = null,
            functions = functions,
            knownVariables = evaluatedVars,
            onDismiss = { showCommandDialog = false },
            onConfirm = { cmd ->
                viewModel.addCommand(cmd)
                showCommandDialog = false
            }
        )
    }

    // Command Dialog (Edit)
    commandToEdit?.let { (idx, cmd) ->
        CommandDialog(
            initialCommand = cmd,
            functions = functions,
            knownVariables = evaluatedVars,
            onDismiss = { commandToEdit = null },
            onConfirm = { newCmd ->
                viewModel.editCommand(idx, newCmd)
                commandToEdit = null
            }
        )
    }

    // Tool Dialog
    if (showToolDialog) {
        ToolDialog(
            initialTool = toolToEdit,
            onDismiss = { showToolDialog = false },
            onConfirm = { t ->
                if (toolToEdit == null) {
                    viewModel.addTool(t)
                } else {
                    viewModel.editTool(t)
                }
                showToolDialog = false
            }
        )
    }

    // Variable Dialog
    if (showVarDialog) {
        VarDialog(
            initialVar = varToEdit,
            onDismiss = { showVarDialog = false },
            onConfirm = { v ->
                if (varToEdit == null) {
                    viewModel.addVariable(v)
                } else {
                    viewModel.editVariable(v)
                }
                showVarDialog = false
            }
        )
    }

    // Stock Dialog
    if (showStockDialog) {
        StockDialog(
            initialStock = stock,
            onDismiss = { showStockDialog = false },
            onConfirm = { newStock ->
                viewModel.updateStock(newStock)
                showStockDialog = false
            }
        )
    }

    // Help Dialog
    if (showHelpDialog) {
        HelpDialog(onDismiss = { showHelpDialog = false })
    }

    // G-Code Import Dialog
    if (showGCodeImportDialog) {
        var importText by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showGCodeImportDialog = false },
            title = { Text("Импорт G-кода в псевдокод", color = Color.White) },
            text = {
                Column {
                    Text("Вставьте G-код (строки G0, G1, G2, циклы сверления):", color = Color(0xFF94A3B8), fontSize = 12.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = importText,
                        onValueChange = { importText = it },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp),
                        colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val (count, warns) = viewModel.parseAndLoadGCode(importText)
                        showGCodeImportDialog = false
                        Toast.makeText(context, "Импортировано $count команд ($warns предупреждений)", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7))
                ) {
                    Text("Импортировать")
                }
            },
            dismissButton = {
                TextButton(onClick = { showGCodeImportDialog = false }) {
                    Text("Отмена", color = Color(0xFF94A3B8))
                }
            },
            containerColor = Color(0xFF1E293B)
        )
    }
}

@Composable
private fun WorkTabsHeader(
    activeTab: Int,
    titles: List<String>,
    collisionCount: Int,
    onSelectTab: (Int) -> Unit
) {
    val icons: List<ImageVector> = listOf(
        Icons.Default.Code,
        Icons.Default.Terminal,
        Icons.Default.Build,
        Icons.Default.Assessment,
        Icons.Default.MoreHoriz
    )

    ScrollableTabRow(
        selectedTabIndex = activeTab,
        edgePadding = 12.dp,
        containerColor = Color(0xFF1E293B),
        contentColor = Color(0xFF38BDF8),
        modifier = Modifier
            .fillMaxWidth()
            .height(50.dp)
    ) {
        titles.forEachIndexed { index, title ->
            val isSelected = activeTab == index
            Tab(
                selected = isSelected,
                onClick = { onSelectTab(index) },
                text = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = icons.getOrElse(index) { Icons.Default.Circle },
                            contentDescription = null,
                            tint = if (isSelected) Color(0xFF38BDF8) else Color(0xFF94A3B8),
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = title,
                            fontSize = 13.sp,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                        )
                        if (index == 3 && collisionCount > 0) {
                            Spacer(modifier = Modifier.width(4.dp))
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = Color(0xFFEF4444)
                            ) {
                                Text(
                                    text = "$collisionCount",
                                    color = Color.White,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp)
                                )
                            }
                        }
                    }
                }
            )
        }
    }
}

@Composable
private fun WorkTabContent(
    activeTab: Int,
    viewModel: MainViewModel,
    onAddCommand: () -> Unit,
    onEditCommand: (Int) -> Unit,
    onAddTool: () -> Unit,
    onEditTool: (Tool) -> Unit,
    onAddVar: () -> Unit,
    onEditVar: (UserVar) -> Unit,
    onEditStock: () -> Unit,
    onImportGCode: () -> Unit
) {
    val commands by viewModel.commands.collectAsState()
    val selectedIndex by viewModel.selectedCommandIndex.collectAsState()
    val collisionIndices by viewModel.collisionIndices.collectAsState()
    val gcodeLines by viewModel.gcodeLines.collectAsState()
    val settings by viewModel.settings.collectAsState()
    val tools by viewModel.tools.collectAsState()
    val stats by viewModel.simulationStats.collectAsState()
    val variables by viewModel.variables.collectAsState()
    val stock by viewModel.stock.collectAsState()
    val functions by viewModel.functions.collectAsState()
    val preamble by viewModel.preamble.collectAsState()
    val postamble by viewModel.postamble.collectAsState()
    val evaluatedVars by viewModel.evaluatedVars.collectAsState()

    when (activeTab) {
        0 -> {
            PseudocodeTab(
                commands = commands,
                selectedIndex = selectedIndex,
                collisionCommandIndices = collisionIndices,
                onSelectIndex = { viewModel.selectCommand(it) },
                onAddCommand = onAddCommand,
                onEditCommand = onEditCommand,
                onDeleteCommand = { viewModel.deleteCommand(it) },
                onMoveCommand = { idx, delta -> viewModel.moveCommand(idx, delta) },
                onDuplicateCommand = { viewModel.duplicateCommand(it) }
            )
        }
        1 -> {
            GCodeTab(
                gcodeLines = gcodeLines,
                unrollLoops = settings.unrollLoops,
                onToggleUnrollLoops = {
                    viewModel.updateSettings(settings.copy(unrollLoops = it))
                },
                onExportGCode = {
                    // G-Code is visible and copyable on screen
                },
                onImportGCode = onImportGCode
            )
        }
        2 -> {
            ToolsTab(
                tools = tools,
                onAddTool = onAddTool,
                onEditTool = onEditTool,
                onDeleteTool = { viewModel.deleteTool(it) },
                onExportCsv = {},
                onImportCsv = {}
            )
        }
        3 -> {
            LogTab(
                stats = stats,
                onSelectCollision = { cmdIdx ->
                    viewModel.selectCommand(cmdIdx)
                }
            )
        }
        4 -> {
            MoreTab(
                variables = variables,
                stock = stock,
                functions = functions,
                preamble = preamble,
                postamble = postamble,
                settings = settings,
                evaluatedVars = evaluatedVars,
                onAddVar = onAddVar,
                onEditVar = onEditVar,
                onDeleteVar = { viewModel.deleteVariable(it) },
                onEditStock = onEditStock,
                onInsertFunction = { fn -> viewModel.insertFunctionCall(fn) },
                onEditPreamble = {},
                onEditPostamble = {},
                onUpdateSettings = { viewModel.updateSettings(it) }
            )
        }
    }
}
