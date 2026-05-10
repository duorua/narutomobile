"""
共享的 test fixtures：mock 掉外部依赖（maa, loguru, PIL, notifypy）
以便纯逻辑单元测试无需安装完整运行环境。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# 将 agent 目录加入 sys.path
agent_dir = str(Path(__file__).resolve().parent.parent.parent / "agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

# Mock 所有外部重依赖
_MOCK_MODULES = [
    "maa", "maa.define", "maa.agent", "maa.agent.agent_server",
    "maa.custom_recognition", "maa.custom_action", "maa.context",
    "maa.tasker", "maa.event_sink", "maa.toolkit",
    "loguru",
    "PIL", "PIL.Image",
    "notifypy",
    "numpy",
]

for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
