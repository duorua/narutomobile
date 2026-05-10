"""
flipcard 包 — 4x4 翻牌游戏的模块化实现。

组件：
    - CardGrid: 网格状态管理（纯 Python）
    - FlipStrategy: 贪心选牌算法（纯 Python）
    - FlipCardRecognition: MAA 框架集成层

导入 FlipCardRecognition 会触发 @AgentServer.custom_recognition("FlipCard") 注册。
"""

from .recognition import FlipCardRecognition

__all__ = ["FlipCardRecognition"]
