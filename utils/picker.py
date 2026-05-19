"""
坐标拾取器 - 通过F4快捷键捕获屏幕坐标
"""
import threading
import time
import ctypes
from typing import Tuple, Optional, Callable
import pyautogui

# Windows API
user32 = ctypes.windll.user32


class CoordinatePicker:
    """坐标拾取器"""

    def __init__(self):
        self._active: bool = False
        self._captured_position: Optional[Tuple[int, int]] = None
        self._pick_thread: Optional[threading.Thread] = None
        self._on_captured: Optional[Callable] = None
        self._exit_event = threading.Event()

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self, on_captured: Callable[[int, int], None]) -> bool:
        """
        启动拾取模式

        Args:
            on_captured: 捕获到坐标后的回调，参数为 (x, y)

        Returns:
            是否成功启动
        """
        if self._active:
            return False

        self._on_captured = on_captured
        self._active = True
        self._exit_event.clear()

        self._pick_thread = threading.Thread(target=self._pick_loop, daemon=True)
        self._pick_thread.start()
        return True

    def stop(self) -> None:
        """停止拾取模式"""
        self._active = False
        self._exit_event.set()
        if self._pick_thread and self._pick_thread.is_alive():
            self._pick_thread.join(timeout=0.5)

    def _pick_loop(self) -> None:
        """拾取循环 - 监听F4按键"""
        import keyboard

        while self._active and not self._exit_event.is_set():
            try:
                # 使用keyboard库监听F4
                if keyboard.is_pressed('f4'):
                    x, y = pyautogui.position()
                    self._captured_position = (x, y)
                    if self._on_captured:
                        self._on_captured(x, y)
                    # 等待按键释放，避免重复触发
                    time.sleep(0.3)
            except Exception as e:
                print(f"坐标拾取错误: {e}")
                time.sleep(0.1)

    def get_last_position(self) -> Optional[Tuple[int, int]]:
        """获取最后捕获的坐标"""
        return self._captured_position