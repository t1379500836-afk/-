"""
工作流持久化存储 - JSON格式
"""
import json
import os
from typing import List, Optional

from .workflow import Workflow


class Storage:
    """工作流存储管理器"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.expanduser("~"), ".autoworker")
        self.storage_dir = storage_dir
        self.workflows_file = os.path.join(storage_dir, "workflows.json")
        self.config_file = os.path.join(storage_dir, "config.json")

        os.makedirs(self.storage_dir, exist_ok=True)

    def _serialize_workflow(self, workflow: Workflow) -> dict:
        """序列化工作流"""
        return {
            "name": workflow.name,
            "loop_count": workflow.loop_count,
            "infinite_loop": workflow.infinite_loop,
            "nodes": [node.to_dict() for node in workflow.nodes]
        }

    def _deserialize_workflow(self, data: dict) -> Workflow:
        """反序列化工作流"""
        workflow = Workflow()
        workflow.name = data.get("name", "未命名工作流")
        workflow.loop_count = data.get("loop_count", 1)
        workflow.infinite_loop = data.get("infinite_loop", False)

        from .workflow import ActionNode, ActionType
        for node_data in data.get("nodes", []):
            node = ActionNode(
                id=node_data.get("id", ""),
                action_type=ActionType(node_data["action_type"]),
                x=node_data.get("x", 0),
                y=node_data.get("y", 0),
                key=node_data.get("key", ""),
                modifiers=node_data.get("modifiers", []),
                delay_ms=node_data.get("delay_ms", 500),
                enabled=node_data.get("enabled", True)
            )
            workflow.nodes.append(node)

        return workflow

    def save_workflow(self, workflow: Workflow) -> bool:
        """保存工作流"""
        workflows = self.load_all_workflows()

        # 查找是否已存在同名工作流
        existing_idx = None
        for i, wf in enumerate(workflows):
            if wf.name == workflow.name:
                existing_idx = i
                break

        if existing_idx is not None:
            workflows[existing_idx] = workflow
        else:
            workflows.append(workflow)

        return self._save_workflows(workflows)

    def _save_workflows(self, workflows: List[Workflow]) -> bool:
        """保存所有工作流到文件"""
        try:
            data = {
                "workflows": [self._serialize_workflow(wf) for wf in workflows]
            }
            with open(self.workflows_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存工作流失败: {e}")
            return False

    def load_all_workflows(self) -> List[Workflow]:
        """加载所有工作流"""
        if not os.path.exists(self.workflows_file):
            return []

        try:
            with open(self.workflows_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            workflows = []
            for wf_data in data.get("workflows", []):
                workflows.append(self._deserialize_workflow(wf_data))
            return workflows
        except Exception as e:
            print(f"加载工作流失败: {e}")
            return []

    def delete_workflow(self, name: str) -> bool:
        """删除工作流"""
        workflows = self.load_all_workflows()
        workflows = [wf for wf in workflows if wf.name != name]
        return self._save_workflows(workflows)

    def load_config(self) -> dict:
        """加载配置"""
        if not os.path.exists(self.config_file):
            return self._default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._default_config()

    def save_config(self, config: dict) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def _default_config(self) -> dict:
        """默认配置"""
        return {
            "last_workflow": None,
            "hotkeys": {
                "start": "f6",
                "stop": "f7",
                "pause": "f8",
                "pick": "f4"
            }
        }