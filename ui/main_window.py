"""
主窗口UI - AutoWorker主界面
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QLabel, QComboBox, QLineEdit,
    QMessageBox, QSplitter, QFrame, QAbstractItemView, QInputDialog,
    QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont

from core.workflow import Workflow, ActionNode, ActionType
from core.executor import Executor
from core.storage import Storage
from utils.hotkey import HotkeyManager
from utils.picker import CoordinatePicker


class SignalEmitter(QObject):
    """信号发射器 - 用于跨线程通信"""
    progress = pyqtSignal(int, int, str)
    completed = pyqtSignal()
    error = pyqtSignal(str)
    coordinate_captured = pyqtSignal(int, int)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("小陶自动化 V1.0.0")
        self.setMinimumSize(1000, 650)

        # 初始化组件
        self.storage = Storage()
        self.all_workflows = self.storage.load_all_workflows()
        self.current_workflow_index = 0

        if not self.all_workflows:
            # 创建默认工作流
            default_wf = Workflow()
            default_wf.name = "默认工作流"
            self.all_workflows.append(default_wf)

        self.executor = Executor()
        self.hotkey_manager = HotkeyManager()
        self.picker = CoordinatePicker()
        self.emitter = SignalEmitter()

        # 连接信号
        self.emitter.progress.connect(self._on_progress)
        self.emitter.completed.connect(self._on_completed)
        self.emitter.error.connect(self._on_error)
        self.emitter.coordinate_captured.connect(self._on_coordinate_captured)

        # 设置执行器回调
        self.executor.set_callbacks(
            on_progress=lambda s, t, n: self.emitter.progress.emit(s, t, n),
            on_complete=lambda: self.emitter.completed.emit(),
            on_error=lambda e: self.emitter.error.emit(e)
        )

        # 当前编辑的节点ID
        self._editing_node_id = None

        # 构建UI
        self._setup_ui()

        # 加载配置的工作流
        self._refresh_workflow_list()
        self._load_current_workflow()
        self._on_type_changed(0)  # 初始化UI可见性
        self._register_hotkeys()

    def _setup_ui(self):
        """构建UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧：操作编辑区
        left_panel = self._create_left_panel()
        # 右侧：工作流列表区
        right_panel = self._create_right_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter)

    def _create_left_panel(self) -> QWidget:
        """创建左侧操作编辑面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 操作类型选择
        type_group = QGroupBox("操作类型")
        type_layout = QVBoxLayout(type_group)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["鼠标左键单击", "鼠标右键单击", "鼠标中键单击", "键盘操作", "文本输入", "延时"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)

        layout.addWidget(type_group)

        # 参数区域
        self.param_group = QGroupBox("参数设置")
        self.param_layout = QVBoxLayout(self.param_group)

        # 鼠标参数
        mouse_widget = QWidget()
        mouse_layout = QHBoxLayout(mouse_widget)
        mouse_layout.setContentsMargins(0, 0, 0, 0)

        mouse_layout.addWidget(QLabel("坐标:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setValue(0)
        mouse_layout.addWidget(self.x_spin)

        mouse_layout.addWidget(QLabel(","))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setValue(0)
        mouse_layout.addWidget(self.y_spin)

        self.pick_btn = QPushButton("拾取坐标 (F4)")
        self.pick_btn.setCheckable(True)
        self.pick_btn.clicked.connect(self._toggle_picker)
        mouse_layout.addWidget(self.pick_btn)

        self.mouse_widget = mouse_widget
        self.param_layout.addWidget(mouse_widget)

        # 键盘参数
        keyboard_widget = QWidget()
        keyboard_layout = QHBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)

        keyboard_layout.addWidget(QLabel("按键:"))

        # 常用按键下拉框
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        common_keys = [
            "↑", "↓", "←", "→",
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "enter", "space", "backspace", "delete", "tab",
            "home", "end", "pageup", "pagedown",
            "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
            "esc", "escape", "insert"
        ]
        self.key_combo.addItems(common_keys)
        self.key_combo.setMinimumWidth(120)
        keyboard_layout.addWidget(self.key_combo)

        self.ctrl_check = QCheckBox("Ctrl")
        keyboard_layout.addWidget(self.ctrl_check)
        self.alt_check = QCheckBox("Alt")
        keyboard_layout.addWidget(self.alt_check)
        self.shift_check = QCheckBox("Shift")
        keyboard_layout.addWidget(self.shift_check)

        self.keyboard_widget = keyboard_widget
        self.param_layout.addWidget(self.keyboard_widget)

        # 文本输入参数
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # 直接输入文本
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("文本:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("输入多个内容用空格分隔，每次循环输入一个")
        text_input_layout.addWidget(self.text_input)
        text_layout.addLayout(text_input_layout)

        # Excel文件
        excel_layout = QHBoxLayout()
        excel_layout.addWidget(QLabel("Excel:"))
        self.excel_input = QLineEdit()
        self.excel_input.setPlaceholderText("选择Excel文件...")
        self.excel_input.setReadOnly(True)
        excel_layout.addWidget(self.excel_input)

        self.excel_btn = QPushButton("浏览")
        self.excel_btn.clicked.connect(self._select_excel_file)
        excel_layout.addWidget(self.excel_btn)

        self.excel_clear_btn = QPushButton("清除")
        self.excel_clear_btn.clicked.connect(self._clear_excel_file)
        excel_layout.addWidget(self.excel_clear_btn)
        text_layout.addLayout(excel_layout)

        # Excel参数
        excel_param_layout = QHBoxLayout()
        excel_param_layout.addWidget(QLabel("列号:"))
        self.excel_col_spin = QSpinBox()
        self.excel_col_spin.setRange(1, 256)
        self.excel_col_spin.setValue(1)
        excel_param_layout.addWidget(self.excel_col_spin)

        excel_param_layout.addWidget(QLabel("从行:"))
        self.excel_row_spin = QSpinBox()
        self.excel_row_spin.setRange(1, 9999)
        self.excel_row_spin.setValue(2)
        excel_param_layout.addWidget(self.excel_row_spin)
        text_layout.addLayout(excel_param_layout)

        self.text_widget = text_widget
        self.param_layout.addWidget(text_widget)

        # 延时参数
        delay_widget = QWidget()
        delay_layout = QHBoxLayout(delay_widget)
        delay_layout.setContentsMargins(0, 0, 0, 0)

        delay_layout.addWidget(QLabel("延时(ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60000)
        self.delay_spin.setValue(1000)
        delay_layout.addWidget(self.delay_spin)

        self.delay_widget = delay_widget
        self.param_layout.addWidget(self.delay_widget)

        layout.addWidget(self.param_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加操作")
        self.add_btn.clicked.connect(self._add_action)
        btn_layout.addWidget(self.add_btn)

        self.update_btn = QPushButton("更新操作")
        self.update_btn.clicked.connect(self._update_action)
        self.update_btn.setEnabled(False)
        btn_layout.addWidget(self.update_btn)

        self.cancel_btn = QPushButton("取消编辑")
        self.cancel_btn.clicked.connect(self._cancel_edit)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # 状态提示
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧工作流列表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 工作流管理区
        wf_group = QGroupBox("工作流管理")
        wf_layout = QVBoxLayout(wf_group)

        # 工作流选择下拉框
        wf_select_layout = QHBoxLayout()
        wf_select_layout.addWidget(QLabel("当前工作流:"))

        self.workflow_combo = QComboBox()
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        wf_select_layout.addWidget(self.workflow_combo)

        wf_layout.addLayout(wf_select_layout)

        # 工作流操作按钮
        wf_btn_layout = QHBoxLayout()
        self.new_wf_btn = QPushButton("新建")
        self.new_wf_btn.clicked.connect(self._create_new_workflow)
        wf_btn_layout.addWidget(self.new_wf_btn)

        self.rename_wf_btn = QPushButton("重命名")
        self.rename_wf_btn.clicked.connect(self._rename_workflow)
        wf_btn_layout.addWidget(self.rename_wf_btn)

        self.delete_wf_btn = QPushButton("删除")
        self.delete_wf_btn.clicked.connect(self._delete_workflow)
        wf_btn_layout.addWidget(self.delete_wf_btn)

        self.save_wf_btn = QPushButton("重新加载")
        self.save_wf_btn.clicked.connect(self._reload_workflows)
        wf_btn_layout.addWidget(self.save_wf_btn)

        wf_layout.addLayout(wf_btn_layout)
        layout.addWidget(wf_group)

        # 工作流步骤列表
        list_group = QGroupBox("工作流步骤")
        list_layout = QVBoxLayout(list_group)

        self.step_list = QListWidget()
        self.step_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.step_list.itemClicked.connect(self._edit_step)
        list_layout.addWidget(self.step_list)

        # 列表操作按钮
        list_btn_layout = QHBoxLayout()
        self.up_btn = QPushButton("↑ 上移")
        self.up_btn.clicked.connect(self._move_up)
        list_btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("↓ 下移")
        self.down_btn.clicked.connect(self._move_down)
        list_btn_layout.addWidget(self.down_btn)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self._edit_selected)
        list_btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._delete_step)
        list_btn_layout.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear_steps)
        list_btn_layout.addWidget(self.clear_btn)

        list_layout.addLayout(list_btn_layout)
        layout.addWidget(list_group)

        # 循环设置
        loop_group = QGroupBox("循环设置")
        loop_layout = QHBoxLayout(loop_group)

        self.infinite_check = QCheckBox("无限循环")
        loop_layout.addWidget(self.infinite_check)

        loop_layout.addWidget(QLabel("循环次数:"))
        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(1, 9999)
        self.loop_spin.setValue(1)
        loop_layout.addWidget(self.loop_spin)

        layout.addWidget(loop_group)

        # 执行控制
        control_group = QGroupBox("执行控制")
        control_layout = QVBoxLayout(control_group)

        exec_btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始 (F6)")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self._start_execution)
        exec_btn_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("暂停 (F8)")
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setEnabled(False)
        exec_btn_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止 (F7)")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_btn.clicked.connect(self._stop_execution)
        self.stop_btn.setEnabled(False)
        exec_btn_layout.addWidget(self.stop_btn)

        control_layout.addLayout(exec_btn_layout)

        # 进度显示
        self.progress_label = QLabel("等待开始...")
        control_layout.addWidget(self.progress_label)

        layout.addWidget(control_group)

        # 热键提示
        hotkey_group = QGroupBox("全局热键")
        hotkey_layout = QVBoxLayout(hotkey_group)
        hotkey_layout.addWidget(QLabel("F6 - 开始执行"))
        hotkey_layout.addWidget(QLabel("F7 - 停止执行"))
        hotkey_layout.addWidget(QLabel("F8 - 暂停/继续"))
        hotkey_layout.addWidget(QLabel("F4 - 拾取坐标"))
        layout.addWidget(hotkey_group)

        return panel

    def _get_current_workflow(self) -> Workflow:
        """获取当前工作流"""
        return self.all_workflows[self.current_workflow_index]

    def _refresh_workflow_list(self):
        """刷新工���流列表"""
        self.workflow_combo.blockSignals(True)
        self.workflow_combo.clear()
        for wf in self.all_workflows:
            self.workflow_combo.addItem(wf.name)
        self.workflow_combo.setCurrentIndex(self.current_workflow_index)
        self.workflow_combo.blockSignals(False)

    def _load_current_workflow(self):
        """加载当前工作流到UI"""
        wf = self._get_current_workflow()
        self.infinite_check.setChecked(wf.infinite_loop)
        self.loop_spin.setValue(wf.loop_count)
        self._refresh_list()

    def _reload_workflows(self):
        """从磁盘重新加载工作流"""
        self.all_workflows = self.storage.load_all_workflows()
        if not self.all_workflows:
            default_wf = Workflow()
            default_wf.name = "默认工作流"
            self.all_workflows.append(default_wf)
        self.current_workflow_index = 0
        self._refresh_workflow_list()
        self._load_current_workflow()
        QMessageBox.information(self, "提示", "已从磁盘重新加载工作流")

    def _auto_save(self):
        """自动保存当前工作流"""
        wf = self._get_current_workflow()
        wf.infinite_loop = self.infinite_check.isChecked()
        wf.loop_count = self.loop_spin.value()
        self.storage.save_workflow(wf)

    def _on_workflow_changed(self, index: int):
        """切换工作流"""
        if index < 0 or index >= len(self.all_workflows):
            return

        # 保存当前工作流的设置
        self._sync_workflow_settings()

        self.current_workflow_index = index
        self._load_current_workflow()

    def _sync_workflow_settings(self):
        """同步UI设置到当前工作流"""
        wf = self._get_current_workflow()
        wf.infinite_loop = self.infinite_check.isChecked()
        wf.loop_count = self.loop_spin.value()

    def _create_new_workflow(self):
        """创建新工作流"""
        name, ok = QInputDialog.getText(self, "新建工作流", "请输入工作流名称:")
        if ok and name.strip():
            name = name.strip()
            # 检查名称是否重复
            for wf in self.all_workflows:
                if wf.name == name:
                    QMessageBox.warning(self, "警告", "工作流名称已存在")
                    return

            new_wf = Workflow()
            new_wf.name = name
            self.all_workflows.append(new_wf)
            self._refresh_workflow_list()
            self.workflow_combo.setCurrentIndex(len(self.all_workflows) - 1)
            self.storage.save_workflow(new_wf)

    def _rename_workflow(self):
        """重命名工作流"""
        wf = self._get_current_workflow()
        name, ok = QInputDialog.getText(self, "重命名工作流", "请输入新名称:", text=wf.name)
        if ok and name.strip():
            name = name.strip()
            # 检查名称是否重复
            for i, w in enumerate(self.all_workflows):
                if i != self.current_workflow_index and w.name == name:
                    QMessageBox.warning(self, "警告", "工作流名称已存在")
                    return

            old_name = wf.name
            wf.name = name
            self._refresh_workflow_list()
            self.storage.save_workflow(wf)
            self.status_label.setText(f"已将「{old_name}」重命名为「{name}」")

    def _delete_workflow(self):
        """删除工作流"""
        if len(self.all_workflows) <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个工作流")
            return

        wf = self._get_current_workflow()
        reply = QMessageBox.question(self, "确认", f"确定删除工作流「{wf.name}」吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_workflow(wf.name)
            del self.all_workflows[self.current_workflow_index]
            self.current_workflow_index = min(self.current_workflow_index, len(self.all_workflows) - 1)
            self._refresh_workflow_list()
            self._load_current_workflow()

    def _on_type_changed(self, index: int):
        """操作类型改变"""
        self.mouse_widget.setVisible(index < 3)
        self.keyboard_widget.setVisible(index == 3)
        self.text_widget.setVisible(index == 4)
        self.delay_widget.setVisible(index == 5)

    def _select_excel_file(self):
        """选择Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "",
            "Excel文件 (*.xlsx *.xls);;所有文件 (*.*)"
        )
        if file_path:
            self.excel_input.setText(file_path)

    def _clear_excel_file(self):
        """清除Excel文件"""
        self.excel_input.clear()

    def _toggle_picker(self, checked: bool):
        """切换拾取模式"""
        if checked:
            self.pick_btn.setText("拾取中... (按F4)")
            self.pick_btn.setStyleSheet("background-color: #FF9800; color: white;")
            self.status_label.setText("拾取模式已激活，移动鼠标到目标位置后按F4")
            self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            self.picker.start(lambda x, y: self.emitter.coordinate_captured.emit(x, y))
        else:
            self.pick_btn.setText("拾取坐标 (F4)")
            self.pick_btn.setStyleSheet("")
            self.status_label.setText("就绪")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self.picker.stop()

    def _on_coordinate_captured(self, x: int, y: int):
        """坐标捕获回调"""
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.pick_btn.setChecked(False)
        self._toggle_picker(False)

    def _get_current_action_type(self) -> ActionType:
        """获取当前选择的操作类型"""
        type_map = {
            0: ActionType.MOUSE_LEFT,
            1: ActionType.MOUSE_RIGHT,
            2: ActionType.MOUSE_MIDDLE,
            3: ActionType.KEYBOARD,
            4: ActionType.KEYBOARD_TEXT,
            5: ActionType.DELAY
        }
        return type_map[self.type_combo.currentIndex()]

    def _create_node_from_ui(self) -> ActionNode:
        """从UI创建节点"""
        action_type = self._get_current_action_type()
        node = ActionNode(action_type=action_type)

        if action_type in [ActionType.MOUSE_LEFT, ActionType.MOUSE_RIGHT, ActionType.MOUSE_MIDDLE]:
            node.x = self.x_spin.value()
            node.y = self.y_spin.value()
        elif action_type == ActionType.KEYBOARD:
            node.key = self.key_combo.currentText().strip().lower()
            # 符号转按键名
            key_map = {"↑": "up", "↓": "down", "←": "left", "→": "right"}
            if node.key in key_map:
                node.key = key_map[node.key]
            node.modifiers = []
            if self.ctrl_check.isChecked():
                node.modifiers.append("ctrl")
            if self.alt_check.isChecked():
                node.modifiers.append("alt")
            if self.shift_check.isChecked():
                node.modifiers.append("shift")
        elif action_type == ActionType.KEYBOARD_TEXT:
            raw_text = self.text_input.text()
            node.text = raw_text
            # 按空格分隔成行列表
            node.text_lines = [line.strip() for line in raw_text.split() if line.strip()]
            node.excel_file = self.excel_input.text()
            node.excel_col = self.excel_col_spin.value()
            node.excel_start_row = self.excel_row_spin.value()
        elif action_type == ActionType.DELAY:
            node.delay_ms = self.delay_spin.value()

        return node

    def _add_action(self):
        """添加操作"""
        node = self._create_node_from_ui()

        if node.action_type == ActionType.KEYBOARD and not node.key:
            QMessageBox.warning(self, "警告", "请输入按键")
            return

        wf = self._get_current_workflow()
        wf.add_node(node)

        # 自动在非延时操作后添加延时节点
        if node.action_type != ActionType.DELAY:
            delay_node = ActionNode(action_type=ActionType.DELAY, delay_ms=1000)
            wf.add_node(delay_node)

        self._refresh_list()
        self._auto_save()

    def _update_action(self):
        """更新操作"""
        if not self._editing_node_id:
            return

        node = self._create_node_from_ui()
        node.id = self._editing_node_id

        if node.action_type == ActionType.KEYBOARD and not node.key:
            QMessageBox.warning(self, "警告", "请输入按键")
            return

        # 找到并替换节点
        wf = self._get_current_workflow()
        for i, n in enumerate(wf.nodes):
            if n.id == self._editing_node_id:
                wf.nodes[i] = node
                break

                self._cancel_edit()
        self._refresh_list()

    def _cancel_edit(self):
        """取消编辑"""
        self._editing_node_id = None
        self.update_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.add_btn.setEnabled(True)

    def _edit_step(self, item: QListWidgetItem):
        """双击编辑步骤"""
        self._edit_selected()

    def _edit_selected(self):
        """编辑选中的步骤"""
        row = self.step_list.currentRow()
        if row < 0 or row >= len(self._get_current_workflow().nodes):
            return

        wf = self._get_current_workflow()
        node = wf.nodes[row]
        self._editing_node_id = node.id

        # 设置UI值
        type_index_map = {
            ActionType.MOUSE_LEFT: 0,
            ActionType.MOUSE_RIGHT: 1,
            ActionType.MOUSE_MIDDLE: 2,
            ActionType.KEYBOARD: 3,
            ActionType.KEYBOARD_TEXT: 4,
            ActionType.DELAY: 5
        }
        self.type_combo.setCurrentIndex(type_index_map[node.action_type])

        if node.action_type in [ActionType.MOUSE_LEFT, ActionType.MOUSE_RIGHT, ActionType.MOUSE_MIDDLE]:
            self.x_spin.setValue(node.x)
            self.y_spin.setValue(node.y)
        elif node.action_type == ActionType.KEYBOARD:
            self.key_combo.setCurrentText(node.key)
            self.ctrl_check.setChecked("ctrl" in node.modifiers)
            self.alt_check.setChecked("alt" in node.modifiers)
            self.shift_check.setChecked("shift" in node.modifiers)
        elif node.action_type == ActionType.KEYBOARD_TEXT:
            self.text_input.setText(node.text)
            self.excel_input.setText(node.excel_file)
            self.excel_col_spin.setValue(node.excel_col)
            self.excel_row_spin.setValue(node.excel_start_row)
        elif node.action_type == ActionType.DELAY:
            self.delay_spin.setValue(node.delay_ms)

        self.update_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.add_btn.setEnabled(False)

    def _delete_step(self):
        """删除步骤"""
        row = self.step_list.currentRow()
        if row < 0:
            return

        wf = self._get_current_workflow()
        if row < len(wf.nodes):
            reply = QMessageBox.question(self, "确认", "确定删除此步骤？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                wf.remove_node(wf.nodes[row].id)
                self._refresh_list()

    def _clear_steps(self):
        """清空所有步骤"""
        reply = QMessageBox.question(self, "确认", "确定清空所有步骤吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._get_current_workflow().clear()
            self._refresh_list()

    def _move_up(self):
        """上移"""
        row = self.step_list.currentRow()
        wf = self._get_current_workflow()
        if row <= 0 or row >= len(wf.nodes):
            return
        wf.move_up(wf.nodes[row].id)
        self._refresh_list()
        self._auto_save()
        self.step_list.setCurrentRow(row - 1)

    def _move_down(self):
        """下移"""
        row = self.step_list.currentRow()
        wf = self._get_current_workflow()
        if row < 0 or row >= len(wf.nodes) - 1:
            return
        wf.move_down(wf.nodes[row].id)
        self._refresh_list()
        self._auto_save()
        self.step_list.setCurrentRow(row + 1)

    def _refresh_list(self):
        """刷新列表"""
        self.step_list.clear()
        wf = self._get_current_workflow()
        for i, node in enumerate(wf.nodes):
            item = QListWidgetItem(f"{i + 1}. {node.display_name}")
            self.step_list.addItem(item)

    def _on_loop_changed(self, value: int):
        """循环次数改变"""
        self._get_current_workflow().loop_count = value

    def _start_execution(self):
        """开始执行"""
        wf = self._get_current_workflow()
        if not wf.nodes:
            QMessageBox.warning(self, "警告", "工作流为空，请先添加操作步骤")
            return

        self._sync_workflow_settings()

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.progress_label.setText("执行中...")

        self.executor.start(wf)

    def _stop_execution(self):
        """停止执行"""
        self.executor.stop()
        self._reset_controls()

    def _toggle_pause(self):
        """切换暂停"""
        if self.executor.is_paused:
            self.executor.resume()
            self.pause_btn.setText("暂停 (F8)")
            self.progress_label.setText("执行中...")
        else:
            self.executor.pause()
            self.pause_btn.setText("继续 (F8)")
            self.progress_label.setText("已暂停")

    def _reset_controls(self):
        """重置控制按钮"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停 (F8)")
        self.progress_label.setText("等待开始...")

    def _on_progress(self, step: int, total: int, name: str):
        """进度回调"""
        self.progress_label.setText(f"步骤 {step}/{total}: {name}")

    def _on_completed(self):
        """完成回调"""
        self.progress_label.setText("执行完成")
        self._reset_controls()

    def _on_error(self, error: str):
        """错误回调"""
        QMessageBox.critical(self, "错误", f"执行出错: {error}")
        self._reset_controls()

    def _register_hotkeys(self):
        """注册全局热键"""
        self.hotkey_manager.register("f6", self._start_execution)
        self.hotkey_manager.register("f7", self._stop_execution)
        self.hotkey_manager.register("f8", self._toggle_pause)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.executor.stop()
        self.picker.stop()
        self.hotkey_manager.unregister_all()
        event.accept()