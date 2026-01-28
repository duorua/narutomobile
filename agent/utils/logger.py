from pathlib import Path
import sys

from loguru import logger as _logger
from utils import root

# 默认日志目录使用绝对路径
log_dir = root / "debug" / "custom"


def setup_logger(log_dir: Path = log_dir, console_level: str = "INFO"):
    """
    Set up the logger with optional file logging.

    Args:
        log_dir (Path): The directory where log files will be stored.
        console_level (str): The logging level for console output (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
    """
    _logger.remove()  # Remove default logger

    # 定义日志级别的简短格式
    def format_level(record):
        level_map = {
            "INFO": "info",
            "ERROR": "err",
            "WARNING": "warn",
            "DEBUG": "debug",
            "CRITICAL": "critical",
            "SUCCESS": "success",
            "TRACE": "trace",
        }
        record["extra"]["level_short"] = level_map.get(
            record["level"].name, record["level"].name.lower()
        )
        return True

    _logger.add(
        sys.stdout,
        format="<level>{extra[level_short]}</level>:<level>{message}</level>",
        colorize=True,
        level=console_level,
        filter=format_level,
    )

    log_dir.mkdir(parents=True, exist_ok=True)
    _logger.add(
        log_dir / "{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="2 weeks",  # Keep logs for 2 weeks
        compression="zip",  # Compress old logs
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | {message}",
        encoding="utf-8",
        enqueue=True,  # Ensure thread safety
        backtrace=True,  # 包含堆栈跟踪
        diagnose=True,  # 显示诊断信息
    )

    return _logger


def change_console_level(level="DEBUG"):
    """动态修改控制台日志等级"""
    setup_logger(console_level=level)
    _logger.info(f"控制台日志等级已更改为: {level}")


logger = setup_logger()
