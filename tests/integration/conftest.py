"""
Integration-test fixtures for the FlipCard flow.

Provides real-enough stubs for MAA SDK symbols so that
``FlipCardRecognition`` can be *imported* and *instantiated*:

* ``maa.define.Rect``              — value class with equality.
* ``maa.custom_recognition.CustomRecognition``
                                   — base class with nested ``AnalyzeArg`` /
                                     ``AnalyzeResult``.
* ``maa.agent.agent_server.AgentServer.custom_recognition``
                                   — identity decorator that records registrations.

All other heavy runtime deps (loguru, PIL, notifypy, numpy) are replaced with
``MagicMock`` so imports succeed without a device.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# sys.path: make ``agent/`` importable as a top-level package root
# ---------------------------------------------------------------------------
_AGENT_DIR = str(Path(__file__).resolve().parent.parent.parent / "agent")
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)


# ---------------------------------------------------------------------------
# Minimal real stubs for maa symbols that FlipCardRecognition touches
# ---------------------------------------------------------------------------
class _Rect:
    """Value-style replacement for ``maa.define.Rect``."""

    def __init__(self, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Rect) and self.as_tuple() == other.as_tuple()

    def __repr__(self) -> str:
        return f"Rect{self.as_tuple()}"


class _CustomRecognition:
    """Real base class with nested helpers used by FlipCardRecognition."""

    class AnalyzeArg:
        def __init__(self, image=None) -> None:
            self.image = image

    class AnalyzeResult:
        def __init__(self, box=None, detail=None) -> None:
            self.box = box
            self.detail = detail

        def __repr__(self) -> str:
            return f"AnalyzeResult(box={self.box}, detail={self.detail})"

    def __init__(self) -> None:
        pass


class _AgentServerMeta(type):
    """Returns an identity-decorator factory for any unknown classmethod,
    so decorators such as ``@AgentServer.tasker_sink()`` keep working even
    though we only *use* ``@AgentServer.custom_recognition(...)`` in tests."""

    def __getattr__(cls, item):  # noqa: D401 — dunder proxy
        def factory(*_args, **_kwargs):
            def wrap(target):
                return target
            return wrap
        return factory


class _AgentServer(metaclass=_AgentServerMeta):
    """Records decorator-style recognition / action registrations."""

    recognitions: dict[str, type] = {}
    actions: dict[str, type] = {}

    @classmethod
    def custom_recognition(cls, name: str):
        def wrap(target: type) -> type:
            cls.recognitions[name] = target
            return target
        return wrap

    @classmethod
    def custom_action(cls, name: str):
        def wrap(target: type) -> type:
            cls.actions[name] = target
            return target
        return wrap


# ---------------------------------------------------------------------------
# Install the stubs + heavy-dep mocks into sys.modules BEFORE any test imports
# ---------------------------------------------------------------------------
def _install_module(name: str, attrs: dict | None = None):
    mod = MagicMock()
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_install_module("maa")
_install_module("maa.define", {"Rect": _Rect})
_install_module("maa.agent")
_install_module("maa.agent.agent_server", {"AgentServer": _AgentServer})
_install_module("maa.custom_recognition", {"CustomRecognition": _CustomRecognition})
_install_module("maa.context", {"Context": MagicMock})
_install_module("maa.custom_action")
_install_module("maa.tasker")
_install_module("maa.event_sink")
_install_module("maa.toolkit")

for _mod in ("loguru", "PIL", "PIL.Image", "notifypy", "numpy"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
