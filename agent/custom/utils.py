import os
import random
from collections.abc import Iterable
from random import randint
from time import sleep

from maa.context import Context
from maa.define import RectType
from notifypy import Notify
from PIL import Image
from utils import get_format_timestamp, jD, jL, logo, root
from utils.logger import log_dir, logger


def save_screenshot(context: Context):
    """把当前缓存截图保存到日志目录（``log_dir``）。

    自动校验分辨率是否为 16:9，以及图像是否是标准的 3 通道 BGR。
    非三通道时跳过 BGR→RGB 转换并发出 warning。

    Args:
        context: MAA 运行时上下文，提供 ``tasker.controller.cached_image``。

    Returns:
        None. 所有异常（截图为空、形状异常等）都以 ``logger.error`` 的形式
        记录后直接返回，不抛出。
    """
    screen_array = context.tasker.controller.cached_image

    if screen_array is None or screen_array.size == 0:
        logger.error("截图为空，无法保存")
        return

    if len(screen_array.shape) < 2:
        logger.error(f"截图维度异常: shape={screen_array.shape}，无法保存")
        return

    height, width = screen_array.shape[:2]
    aspect_ratio = width / height
    target_ratio = 16 / 9
    if abs(aspect_ratio - target_ratio) / target_ratio > 0.01:
        logger.error(f"当前模拟器分辨率不是16:9! 当前分辨率: {width}x{height}")

    if len(screen_array.shape) == 3 and screen_array.shape[2] == 3:
        rgb_array = screen_array[:, :, ::-1]
    else:
        rgb_array = screen_array
        logger.warning("当前截图并非三通道")

    img = Image.fromarray(rgb_array)

    save_dir = log_dir
    os.makedirs(save_dir, exist_ok=True)
    time_str = get_format_timestamp()
    img.save(f"{save_dir}/{time_str}.png")
    logger.info(f"截图保存至 {save_dir}/{time_str}.png")


def fast_ocr(
    context: Context,
    expected: str | list[str],
    roi: tuple[int, int, int, int],
    absolutely=False,
    screenshot_refresh=True,
) -> RectType | None:
    """对指定 ROI 截图并执行 OCR，返回匹配项的 box。

    两种匹配模式：

    * ``absolutely=False`` (默认) —— 使用 MAA 的 ``best_result``，模糊匹配。
    * ``absolutely=True`` —— 精确匹配：仅当 ``filtered_results`` 中存在
      和 ``expected`` **完全相等** 的文本时才命中。

    Args:
        context: MAA 运行时上下文。
        expected: 期望的单段文本或文本列表。
        roi: 识别区域 ``[x, y, w, h]``。
        absolutely: 是否使用绝对精确匹配，默认 ``False``。
        screenshot_refresh: 是否在识别前先刷一次 ``post_screencap``，默认 ``True``。

    Returns:
        命中时返回该文本的 ``box`` (``RectType``)；未命中/识别失败返回
        ``None``。
    """
    if screenshot_refresh:
        context.tasker.controller.post_screencap().wait()
    if not isinstance(expected, Iterable):
        expected = [expected]

    reco_detail = context.run_recognition(
        "custom_ocr",
        context.tasker.controller.cached_image,
        {
            "custom_ocr": {
                "recognition": {
                    "type": "OCR",
                    "param": {"expected": expected, "roi": roi},
                }
            }
        },
    )
    if reco_detail is None:
        return None

    if reco_detail.hit is False or reco_detail.best_result is None:
        return None

    if not absolutely:
        logger.opt(lazy=True).debug(
            "OCR 识别成功: {t}",
            t=lambda: reco_detail.best_result.text,
        )
        return reco_detail.best_result.box
    else:
        filtered_texts = [
            res.text  # ty:ignore[unresolved-attribute]
            for res in reco_detail.filtered_results
        ]

        result = None
        logger.opt(lazy=True).debug(
            "OCR 绝对匹配尝试: {e} in {t}",
            e=lambda: expected,
            t=lambda: filtered_texts,
        )
        for target in expected:
            if target in filtered_texts:
                result = next(
                    res
                    for res in reco_detail.filtered_results
                    if res.text == target  # ty:ignore[unresolved-attribute]
                )
                break

        if result is not None:
            logger.opt(lazy=True).debug(
                "OCR 绝对匹配成功: {e}", e=lambda: expected
            )
            return result.box  # ty:ignore[unresolved-attribute]
        else:
            logger.opt(lazy=True).debug(
                "{e} 绝对匹配失败：{r}",
                e=lambda: expected,
                r=lambda: reco_detail.filtered_results,
            )
            return None


def wait_for_freezes(context: Context, wait_for_freezes: int = 200):
    """阻塞直至屏幕内容连续 ``wait_for_freezes`` 毫秒无变化。

    实际实现由 MAA 管线中的 ``wait_for_freezes`` 任务提供；这里只是一个薄包装。

    Args:
        context: MAA 运行时上下文。
        wait_for_freezes: 连续静止阈值（毫秒），默认 200。

    Returns:
        None.
    """
    context.run_task(
        "wait_for_freezes", {"wait_for_freezes": {"wait_for_freezes": wait_for_freezes}}
    )


def wait_until_visible(
    context: Context,
    expected: str | list[str],
    roi: tuple[int, int, int, int],
    timeout_s: float = 3.0,
    interval_s: float = 0.15,
    absolutely: bool = False,
    label: str = "UI element",
) -> RectType | None:
    """轮询等待 ROI 内出现指定文本，出现即返回 box，超时返回 None。

    替代 ``sleep(N)`` + ``fast_ocr(...)`` 的固定等待模式，
    在 UI 元素已出现时尽早返回以减少空转。

    Args:
        context: MAA 上下文。
        expected: 期望的文本或文本列表（传给 OCR 匹配）。
        roi: 识别区域 [x, y, w, h]。
        timeout_s: 最大等待秒数；到期仍未出现则放弃。
        interval_s: 两次轮询之间的间隔秒数，控制轮询频率避免高 CPU。
        absolutely: 透传给 ``fast_ocr``，是否要求精确匹配。
        label: 供日志使用的元素描述。

    Returns:
        识别到文本时返回该元素的 ``box``；超时或任务停止返回 ``None``。
    """
    from time import monotonic

    deadline = monotonic() + timeout_s
    attempts = 0
    while True:
        attempts += 1

        if context.tasker.stopping:
            logger.info(f"wait_until_visible({label}): 任务停止，提前退出")
            return None

        box = fast_ocr(context, expected, roi, absolutely=absolutely)
        if box is not None:
            elapsed = timeout_s - max(deadline - monotonic(), 0)
            logger.opt(lazy=True).debug(
                "wait_until_visible({l}): 命中，用时{e:.2f}s/{n}次轮询",
                l=lambda: label,
                e=lambda: elapsed,
                n=lambda: attempts,
            )
            return box

        if monotonic() >= deadline:
            logger.warning(
                f"wait_until_visible({label}): "
                f"{timeout_s:.2f}s 内未出现（共 {attempts} 次轮询），放弃等待"
            )
            return None

        sleep(interval_s)


def check_resolution(context: Context):
    """校验模拟器分辨率是否为推荐的 16:9（容差 2%）。

    若比例偏差超过 2%，记录 error 日志（仅警示，不中止任务）。

    Args:
        context: MAA 运行时上下文，需包含 ``tasker.controller.resolution``。

    Returns:
        None.
    """
    resolution = context.tasker.controller.resolution
    if resolution[1] > resolution[0]:
        resolution = (resolution[1], resolution[0])
    if abs((resolution[0] / resolution[1]) - (16.0 / 9.0)) > 0.02:
        logger.error("你可能正在使用非推荐的分辨率！")
        logger.error("推荐使用的分辨率：1920x1080")
        logger.error(f"当前使用的分辨率：{resolution[0]}x{resolution[1]}")


def validate_config(context: Context):
    """修复/对齐 MFA 接口配置 (``in*.json``) 中的项目元数据字段。

    仅在项目根目录存在 ``*.exe`` （即 MFA 绑定环境）时才执行；否则直接返回。
    写回 ``name`` / ``github`` / ``mirrorchyan_rid`` 三个固定字段。

    Args:
        context: MAA 运行时上下文（预留参数，当前未使用）。

    Returns:
        None.
    """
    if len(list(root.glob("*.exe"))) == 0:
        return
    candidates = [p for p in root.glob("*.json") if p.name.startswith("in")]
    if not candidates:
        logger.warning("未找到接口配置文件 (in*.json)，跳过配置验证")
        return
    fp = candidates[0]
    logger.info(f"验证配置文件: {fp}")
    config = jL(fp.open(encoding="utf-8"))
    config.update(
        {
            "name": "MaaAutoNaruto",
            "github": "https://github.com/duorua/narutomobile",
            "mirrorchyan_rid": "MaaAutoNaruto",
        }
    )
    jD(config, fp.open("w", encoding="utf-8"), ensure_ascii=False, indent=4)


def click(context: Context, x: int, y: int, w: int = 1, h: int = 1):
    """在指定矩形区域内随机坐标点击一次（避免落点固定被检测）。

    Args:
        context: MAA 运行时上下文。
        x: 矩形左上角 x。
        y: 矩形左上角 y。
        w: 矩形宽度，默认 1（单像素点击）。
        h: 矩形高度，默认 1。

    Returns:
        None. 调用 ``post_click().wait()``，阻塞直至点击动作完成。
    """
    context.tasker.controller.post_click(
        random.randint(x, x + w - 1), random.randint(y, y + h - 1)
    ).wait()


def validate_mfa(context: Context):
    """对齐 MFA 全局配置 (``config/c*.json``) 中的自动更新开关。

    若尚未设置 ``DownloadCDK``，顺便填上 ``DownloadSourceIndex=0``；
    强制打开 ``EnableAutoUpdateResource`` / ``EnableAutoUpdateMFA``。

    Args:
        context: MAA 运行时上下文（预留参数，当前未使用）。

    Returns:
        None. 若 ``config/`` 下找不到匹配的 ``c*.json``，直接返回。
    """
    fps = [p for p in (root / "config").glob("*.json") if p.name.startswith("c")]
    if len(fps) != 0:
        fp = fps[0]
    else:
        return
    mfa = jL(fp.open(encoding="utf-8"))
    if mfa.get("DownloadCDK", "") == "":
        mfa.update(
            {
                "DownloadSourceIndex": 0,
            }
        )

    mfa.update(
        {
            "EnableAutoUpdateResource": True,
            "EnableAutoUpdateMFA": True,
        }
    )


def fast_swipe(
    context: Context,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int = 300,
    end_hold: bool = True,
    after_swipe_delay: int = 300,
):
    """快速滑动屏幕，起止点带 ±50px 随机扰动、时长 ±100ms 随机扰动。

    Args:
        context: MAA 运行时上下文。
        start_x: 起始点 X 坐标。
        start_y: 起始点 Y 坐标。
        end_x: 终点 X 坐标。
        end_y: 终点 Y 坐标。
        duration: 滑动持续时间（ms），实际会在 ``[duration-100, duration+100]``
            区间内随机；建议 ≥ 200 避免系统丢弃事件。
        end_hold: 是否在滑动末尾停顿以抑制惯性滑动。``True`` 时随机停
            ``100–200ms``；``False`` 则不停顿（``end_hold=0``）。
        after_swipe_delay: 滑动完成后的固定延迟（ms），用于等待动画稳定。

    Returns:
        None. 调用底层 ``context.run_action("custom_swipe", ...)``。

    Notes:
        若要防止惯性滑动，请使用 ``end_hold=True``（默认）；若要利用
        惯性，例如快速翻页，则传 ``end_hold=False``。
    """

    # 手动随机（起止点 ±50px / 时长 ±100ms）规避反作弊，同时绕开 maafw
    # 自带随机的疑似闭包问题。
    context.run_action(
        "custom_swipe",
        pipeline_override={
            "custom_swipe": {
                "begin": [random.randint(start_x - 50, start_x + 50), start_y],
                "end": [random.randint(end_x - 50, end_x + 50), end_y],
                "duration": randint(duration - 100, duration + 100),
                "end_hold": randint(100, 200) if end_hold else 0,
            }
        },
    )
    sleep(after_swipe_delay / 1000)


def click_and_wait_for_freezes(
    context: Context,
    x: int,
    y: int,
    w: int = 1,
    h: int = 1,
    post_wait_freezes: int = 200,
):
    """点击指定区域并阻塞等待屏幕静止。

    Args:
        context: MAA 运行时上下文。
        x: 点击区域左上角 X。
        y: 点击区域左上角 Y。
        w: 点击区域宽度，默认 1。
        h: 点击区域高度，默认 1。
        post_wait_freezes: 点击后要求屏幕连续静止的时长（ms），默认 200。

    Returns:
        None. 底层调用 MAA 管线任务 ``click_and_wait_for_freezes``。
    """
    context.run_task(
        "click_and_wait_for_freezes",
        {
            "click_and_wait_for_freezes": {
                "target": [x, y, w, h],
                "post_wait_freezes": post_wait_freezes,
            }
        },
    )


def nonlinear_swipe(
    context: Context,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int = 150,
    end_hold: bool = False,
    after_swipe_delay: int = 300,
    steps: int = 7,  # 滑动分段
):
    """带缓动曲线的多段非线性滑动（更像真人手指）。

    使用 ``ease-out`` 曲线 ``1 - (1 - t) ** 2`` 把整段滑动切成 ``steps``
    个小段，每段有独立的途径点与时长分配，起止点与总时长都带随机扰动。

    Args:
        context: MAA 运行时上下文。
        start_x: 起始点 X。
        start_y: 起始点 Y。
        end_x: 终点 X。
        end_y: 终点 Y。
        duration: 总时长（ms），实际会在 ``±100ms`` 区间随机。
        end_hold: 是否在末尾停顿抑制惯性，``True`` 时随机 ``100–200ms``。
        after_swipe_delay: 滑动完成后的固定等待（ms）。
        steps: 滑动分段数，默认 7。

    Returns:
        None. 底层调用 ``context.run_action("custom_swipe", ...)``。
    """

    s_x = random.randint(start_x - 50, start_x + 50)
    s_y = random.randint(start_y - 50, start_y + 50)
    e_x = random.randint(end_x - 50, end_x + 50)
    e_y = random.randint(end_y - 50, end_y + 50)
    total_dur = random.randint(duration - 100, duration + 100)
    hold_time = random.randint(100, 200) if end_hold else 0

    points = []
    dur_list = []
    total_prog = 0.0

    for i in range(1, steps + 1):
        t = i / steps
        # ease-out 缓动曲线：起步快、末尾慢，更像真人手指。
        prog = 1 - (1 - t) ** 2
        delta = prog - total_prog
        total_prog = prog

        curr_x = int(s_x + (e_x - s_x) * prog)
        curr_y = int(s_y + (e_y - s_y) * prog)
        points.append([curr_x, curr_y])
        dur_list.append(round(total_dur * delta))

    # 补偿 rounding 误差，保证分段时长之和等于总时长。
    dur_list[-1] += total_dur - sum(dur_list)

    context.run_action(
        "custom_swipe",
        pipeline_override={
            "custom_swipe": {
                "action": "Swipe",
                "begin": [s_x, s_y],
                "end": points,
                "end_hold": hold_time,
                "duration": dur_list,
            }
        },
    )
    sleep(after_swipe_delay / 1000)


def send_notification(title: str = "系统通知", msg: str = "这是一条测试消息"):
    """通过 ``notifypy`` 发送一条跨平台桌面通知。

    Args:
        title: 通知标题，默认 ``"系统通知"``。
        msg: 通知正文，默认 ``"这是一条测试消息"``。

    Returns:
        None.
    """
    Notify(title, msg, "MaaAutoNaruto", logo.__str__()).send()
