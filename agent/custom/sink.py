"""
分辨率检查器

在任务开始时检查模拟器分辨率是否为 16:9，如果不是则停止任务并输出警告。

Copy from M9A
"""

from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker, TaskerEventSink
from maa.event_sink import NotificationType

from utils.logger import logger

# 目标宽高比：16:9
TARGET_RATIO = 16.0 / 9.0
# 容差范围（±2%）
TOLERANCE = 0.02


def is_aspect_ratio_16x9(width: int, height: int) -> bool:
    """
    检查给定的尺寸是否大约为 16:9
    同时处理横屏（16:9）和竖屏（9:16）方向
    """
    if width <= 0 or height <= 0:
        return False

    ratio = calculate_aspect_ratio(width, height)

    # 检查比例是否在 16:9 的容差范围内
    return abs(ratio - TARGET_RATIO) <= TARGET_RATIO * TOLERANCE


def calculate_aspect_ratio(width: int, height: int) -> float:
    """
    计算宽高比，始终返回 较大/较小 的比值
    这样可以统一处理横屏和竖屏方向
    """
    w = float(width)
    h = float(height)

    # 始终返回较大值/较小值，以统一方向
    if w > h:
        return w / h
    return h / w


@AgentServer.tasker_sink()
class AspectRatioChecker(TaskerEventSink):
    """
    分辨率检查器
    在任务开始时检查设备分辨率是否为 16:9
    """

    def on_tasker_task(
        self,
        tasker: Tasker,
        noti_type: NotificationType,
        detail: TaskerEventSink.TaskerTaskDetail,
    ):
        # 只在任务开始时检查
        if noti_type != NotificationType.Starting:
            return

        # 忽略停止任务事件
        if detail.entry == "MaaTaskerPostStop":
            logger.debug("收到 PostStop 事件，跳过分辨率检查")
            return

        # 每次任务开始时都检查（不再使用 _checked 标志）
        logger.debug(
            f"任务开始前检查分辨率 - task_id: {detail.task_id}, entry: {detail.entry}"
        )

        # 获取控制器
        controller = tasker.controller
        if controller is None:
            logger.error("无法获取控制器")
            return

        # 获取缓存的图像
        try:
            img = controller.cached_image
            if img is None:
                # 如果没有缓存图像，尝试截图
                img = controller.post_screencap().wait().get()
        except Exception as e:
            logger.error(f"无法获取截图: {e}")
            return

        if img is None:
            logger.error("无法获取截图")
            return

        # 获取图像尺寸
        height, width = img.shape[:2]

        logger.debug(f"截图尺寸: {width} x {height}")

        # 检查宽高比
        if not is_aspect_ratio_16x9(width, height):
            actual_ratio = calculate_aspect_ratio(width, height)
            logger.error(
                f"当前分辨率比例不匹配！任务已停止。"
                f"当前: {width}x{height} (比例: {actual_ratio:.4f})，"
                f"MaaAutoNarto 仅支持 16:9 比例，推荐调整为: 1920x1080"
            )

            # 停止任务
            tasker.post_stop()
        else:
            logger.debug(f"分辨率检查通过: {width}x{height} (16:9)")
