"""
工作流核心数据结构和工作流管理器
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import uuid


class ActionType(Enum):
    """操作类型枚举"""
    MOUSE_LEFT = "mouse_left"
    MOUSE_RIGHT = "mouse_right"
    MOUSE_MIDDLE = "mouse_middle"
    KEYBOARD = "keyboard"
    KEYBOARD_TEXT = "keyboard_text"  # 文本输入
    DELAY = "delay"


class MouseButton(Enum):
    """鼠标按键"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass
class ActionNode:
    """操作节点 - 代表单个操作步骤"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: ActionType = ActionType.MOUSE_LEFT
    x: int = 0
    y: int = 0
    key: str = ""
    modifiers: List[str] = field(default_factory=list)  # ctrl, alt, shift
    delay_ms: int = 500
    enabled: bool = True
    # Excel文本输入相关
    text: str = ""  # 直接输入的文本（原始字符串，空格分隔多行）
    text_lines: List[str] = field(default_factory=list)  # 解析后的文本行列表
    excel_file: str = ""  # Excel文件路径
    excel_col: int = 1  # Excel列号(1-based)
    excel_start_row: int = 2  # 从第几行开始（跳过表头）

    @property
    def display_name(self) -> str:
        """获取显示名称"""
        if self.action_type in [ActionType.MOUSE_LEFT, ActionType.MOUSE_RIGHT, ActionType.MOUSE_MIDDLE]:
            btn_map = {
                ActionType.MOUSE_LEFT: "左键单击",
                ActionType.MOUSE_RIGHT: "右键单击",
                ActionType.MOUSE_MIDDLE: "中键单击"
            }
            return f"{btn_map[self.action_type]} @ ({self.x}, {self.y})"
        elif self.action_type == ActionType.KEYBOARD:
            mods = "+".join(self.modifiers) + "+" if self.modifiers else ""
            return f"按键: {mods}{self.key}"
        elif self.action_type == ActionType.KEYBOARD_TEXT:
            if self.excel_file:
                import os
                filename = os.path.basename(self.excel_file)
                return f"Excel输入: {filename} 第{self.excel_col}列"
            elif self.text_lines:
                count = len(self.text_lines)
                preview = self.text_lines[0][:15] if self.text_lines[0] else ""
                return f"文本输入: {preview}... ({count}行)"
            return f"文本输入: {self.text[:20]}..." if self.text else "文本输入"
        elif self.action_type == ActionType.DELAY:
            return f"延时: {self.delay_ms}ms"
        return "未知操作"

    @property
    def type_display(self) -> str:
        """获取类型显示名"""
        type_map = {
            ActionType.MOUSE_LEFT: "鼠标左键",
            ActionType.MOUSE_RIGHT: "鼠标右键",
            ActionType.MOUSE_MIDDLE: "鼠标中键",
            ActionType.KEYBOARD: "键盘操作",
            ActionType.KEYBOARD_TEXT: "文本输入",
            ActionType.DELAY: "延时"
        }
        return type_map.get(self.action_type, "未知")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "x": self.x,
            "y": self.y,
            "key": self.key,
            "modifiers": self.modifiers,
            "delay_ms": self.delay_ms,
            "enabled": self.enabled,
            "text": self.text,
            "text_lines": self.text_lines,
            "excel_file": self.excel_file,
            "excel_col": self.excel_col,
            "excel_start_row": self.excel_start_row
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActionNode":
        """从字典创建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            action_type=ActionType(data["action_type"]),
            x=data.get("x", 0),
            y=data.get("y", 0),
            key=data.get("key", ""),
            modifiers=data.get("modifiers", []),
            delay_ms=data.get("delay_ms", 500),
            enabled=data.get("enabled", True),
            text=data.get("text", ""),
            text_lines=data.get("text_lines", []),
            excel_file=data.get("excel_file", ""),
            excel_col=data.get("excel_col", 1),
            excel_start_row=data.get("excel_start_row", 2)
        )


class Workflow:
    """工作流管理器"""

    def __init__(self):
        self.nodes: List[ActionNode] = []
        self.loop_count: int = 1  # 循环次数，1表示只执行一次
        self.infinite_loop: bool = False  # 是否无限循环
        self.name: str = "未命名工作流"

    def add_node(self, node: ActionNode) -> None:
        """添加节点"""
        self.nodes.append(node)

    def remove_node(self, node_id: str) -> None:
        """移除节点"""
        self.nodes = [n for n in self.nodes if n.id != node_id]

    def move_up(self, node_id: str) -> None:
        """上移节点"""
        idx = next((i for i, n in enumerate(self.nodes) if n.id == node_id), -1)
        if idx > 0:
            self.nodes[idx], self.nodes[idx - 1] = self.nodes[idx - 1], self.nodes[idx]

    def move_down(self, node_id: str) -> None:
        """下移节点"""
        idx = next((i for i, n in enumerate(self.nodes) if n.id == node_id), -1)
        if idx < len(self.nodes) - 1 and idx >= 0:
            self.nodes[idx], self.nodes[idx + 1] = self.nodes[idx + 1], self.nodes[idx]

    def get_node(self, node_id: str) -> Optional[ActionNode]:
        """获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def clear(self) -> None:
        """清空所有节点"""
        self.nodes.clear()

    def get_execution_count(self) -> int:
        """获取总执行次数"""
        if self.infinite_loop:
            return -1  # 表示无限循环
        return self.loop_count