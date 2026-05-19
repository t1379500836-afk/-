"""
全局热键管理器 - 支持后台热键监听
"""
import keyboard
from typing import Callable, Dict, List


class HotkeyManager:
    """全局热键管理器"""

    def __init__(self):
        self._hotkeys: Dict[str, Callable] = {}
        self._registered_keys: List[str] = []

    def register(self, hotkey: str, callback: Callable) -> bool:
        """
        注册热键

        Args:
            hotkey: 热键字符串，如 "f6", "ctrl+c", "alt+f4"
            callback: 回调函数

        Returns:
            是否注册成功
        """
        try:
            # 清理旧的热键
            if hotkey in self._registered_keys:
                self.unregister(hotkey)

            keyboard.add_hotkey(hotkey, callback, suppress=True)
            self._hotkeys[hotkey] = callback
            self._registered_keys.append(hotkey)
            return True
        except Exception as e:
            print(f"注册热键失败 {hotkey}: {e}")
            return False

    def unregister(self, hotkey: str) -> None:
        """取消注册热键"""
        try:
            if hotkey in self._registered_keys:
                keyboard.remove_hotkey(hotkey)
                self._registered_keys.remove(hotkey)
                self._hotkeys.pop(hotkey, None)
        except Exception as e:
            print(f"取消热键失败 {hotkey}: {e}")

    def unregister_all(self) -> None:
        """取消所有热键"""
        for hotkey in list(self._registered_keys):
            self.unregister(hotkey)

    def is_registered(self, hotkey: str) -> bool:
        """检查热键是否已注册"""
        return hotkey in self._registered_keys