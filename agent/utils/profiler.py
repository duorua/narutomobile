"""性能分析工具：装饰器 + 上下文管理器，统一记录函数/代码块耗时。

日志格式：``[Profiler] {class_name}.{method} took {elapsed_ms:.2f}ms``。
所有输出走 ``logger.debug``，默认不会污染 INFO 级别日志。

Examples:
    装饰方法::

        from utils.profiler import profiled

        class MyRecognition:
            @profiled
            def analyze(self, context, argv):
                ...

    包裹代码块::

        from utils.profiler import profile_block

        with profile_block("MyRecognition.inner_loop"):
            ...
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from time import monotonic
from typing import Any

from utils.logger import logger


def profiled[F: Callable[..., Any]](func: F) -> F:
    """装饰器：测量被装饰函数/方法的执行耗时并写入 debug 日志。

    若被装饰的是类方法（``args[0]`` 是 ``self``），日志中的 ``class_name``
    取自 ``type(args[0]).__name__``；否则退化为 ``func.__module__``。

    Args:
        func: 任意可调用对象，通常是 ``analyze`` / ``run`` 等入口方法。

    Returns:
        包装后的可调用对象，语义与原函数完全一致（返回值、异常都透传）。
        ``@wraps`` 保留原函数的名称与 docstring。
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (monotonic() - start) * 1000.0
            owner = (
                type(args[0]).__name__ if args else func.__module__
            )
            logger.opt(lazy=True).debug(
                "[Profiler] {o}.{n} took {e:.2f}ms",
                o=lambda: owner,
                n=lambda: func.__name__,
                e=lambda: elapsed_ms,
            )

    return wrapper  # type: ignore[return-value]


@contextmanager
def profile_block(label: str) -> Iterator[None]:
    """上下文管理器：测量 ``with`` 块中代码的执行耗时。

    Args:
        label: 日志标签，推荐形如 ``"ClassName.section_name"``。

    Yields:
        None. 退出 ``with`` 块时输出一条 debug 日志。
    """
    start = monotonic()
    try:
        yield
    finally:
        elapsed_ms = (monotonic() - start) * 1000.0
        logger.opt(lazy=True).debug(
            "[Profiler] {l} took {e:.2f}ms",
            l=lambda: label,
            e=lambda: elapsed_ms,
        )
