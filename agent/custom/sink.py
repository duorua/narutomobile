"""
分辨率检查器

在任务开始时检查模拟器分辨率是否为 16:9，如果不是则停止任务并输出警告。

Copy from M9A
"""

from maa.agent.agent_server import AgentServer
from maa.event_sink import NotificationType
from maa.tasker import Tasker, TaskerEventSink
from utils.logger import logger

TARGET_RATIO = 16.0 / 9.0
TOLERANCE = 0.02


def is_aspect_ratio_16x9(width: int, height: int) -> bool:
    """检查给定的尺寸是否大约为 16:9（横屏或竖屏皆可）。"""
    if width <= 0 or height <= 0:
        return False

    ratio = calculate_aspect_ratio(width, height)
    return abs(ratio - TARGET_RATIO) <= TARGET_RATIO * TOLERANCE


def calculate_aspect_ratio(width: int, height: int) -> float:
    """计算宽高比，始终返回 较大/较小 的比值以统一横竖屏方向。"""
    w = float(width)
    h = float(height)

    if w > h:
        return w / h
    return h / w


@AgentServer.tasker_sink()
class AspectRatioChecker(TaskerEventSink):
    """分辨率检查器：任务开始时校验设备分辨率是否为 16:9，不符则停止。"""

    def on_tasker_task(
        self,
        tasker: Tasker,
        noti_type: NotificationType,
        detail: TaskerEventSink.TaskerTaskDetail,
    ):
        if noti_type != NotificationType.Starting:
            return

        if detail.entry == "MaaTaskerPostStop":
            logger.debug("收到 PostStop 事件，跳过分辨率检查")
            return

        logger.debug(
            f"任务开始前检查分辨率 - task_id: {detail.task_id}, entry: {detail.entry}"
        )

        controller = tasker.controller
        if controller is None:
            logger.error("无法获取控制器")
            return

        try:
            img = controller.cached_image
            if img is None:
                img = controller.post_screencap().wait().get()
        except Exception as e:
            logger.error(f"无法获取截图: {e}")
            return

        if img is None:
            logger.error("无法获取截图")
            return

        height, width = img.shape[:2]
        logger.debug(f"截图尺寸: {width} x {height}")

        if not is_aspect_ratio_16x9(width, height):
            actual_ratio = calculate_aspect_ratio(width, height)
            logger.error(
                f"当前分辨率比例不匹配！任务已停止。"
                f"当前: {width}x{height} (比例: {actual_ratio:.4f})，"
                f"MaaAutoNarto 仅支持 16:9 比例，推荐调整为: 1920x1080"
            )
            tasker.post_stop()
        else:
            logger.debug(f"分辨率检查通过: {width}x{height} (16:9)")
