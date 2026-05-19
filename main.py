#!/usr/bin/env python3
"""
AutoWorker - 自动化操作工具
支持鼠标/键盘操作录制、回放、坐标拾取、全局热键控制

Usage:
    python main.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def main():
    """程序入口"""
    app = QApplication(sys.argv)
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 设置应用信息
    app.setApplicationName("AutoWorker")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AutoWorker")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    main()