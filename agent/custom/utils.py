from random import randint
from typing import Iterable
from time import sleep
import os
import random
from PIL import Image
from maa.context import Context
from maa.define import RectType
from utils.logger import logger

from utils import get_format_timestamp
from utils import bdc, root, jL, jD
from utils.logger import log_dir


def save_screenshot(context: Context):
    # image array(BGR)
    screen_array = context.tasker.controller.cached_image

    # Check resolution aspect ratio
    height, width = screen_array.shape[:2]
    aspect_ratio = width / height
    target_ratio = 16 / 9
    # Allow small deviation (within 1%)
    if abs(aspect_ratio - target_ratio) / target_ratio > 0.01:
        logger.error(f"当前模拟器分辨率不是16:9! 当前分辨率: {width}x{height}")

    # BGR2RGB
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
    """重新截图并进行 OCR 识别"""
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
        logger.debug(f"OCR 识别成功: {reco_detail.best_result.text}")  # type: ignore
        return reco_detail.best_result.box  # type: ignore
    else:

        # 提前提取所有文本，避免重复生成列表
        filtered_texts = [
            res.text  # ty:ignore[unresolved-attribute]
            for res in reco_detail.filtered_results
        ]

        result = None
        logger.debug(f"OCR 绝对匹配尝试: {expected} in {filtered_texts}")
        for target in expected:
            if target in filtered_texts:
                # 找到第一个匹配的结果
                result = next(
                    res
                    for res in reco_detail.filtered_results
                    if res.text == target  # ty:ignore[unresolved-attribute]
                )
                logger.debug(
                    f"OCR 绝对匹配成功: {target} in {reco_detail.filtered_results} with {result}"
                )
                break

        if result is not None:
            logger.debug(f"OCR 绝对匹配成功: {expected}")
            return result.box
        else:
            logger.debug(f"{expected} 绝对匹配失败：{reco_detail.filtered_results}")
            return None


def wait_for_freezes(context: Context, wait_for_freezes: int = 200):
    context.run_task(
        "wait_for_freezes", {"wait_for_freezes": {"wait_for_freezes": wait_for_freezes}}
    )


def validate_config(context: Context):
    if len(list(root.glob("*.exe"))) == 0:
        return
    fp = [p for p in (root).glob("*.json") if p.name.startswith("in")][0]
    logger.info(f"验证配置文件: {fp}")
    config = jL(fp.open(encoding="utf-8"))
    config.update(
        {
            bdc("bmFtZQ=="): bdc("TWFhQXV0b05hcnV0bw=="),
            bdc("Z2l0aHVi"): bdc(
                "aHR0cHM6Ly9naXRodWIuY29tL2R1b3J1YS9uYXJ1dG9tb2JpbGU="
            ),
            bdc("bWlycm9yY2h5YW5fcmlk"): bdc("TWFhQXV0b05hcnV0bw=="),
        }
    )
    jD(config, fp.open("w", encoding="utf-8"), ensure_ascii=False, indent=4)


def click(context: Context, x: int, y: int, w: int = 1, h: int = 1):
    context.tasker.controller.post_click(
        random.randint(x, x + w - 1), random.randint(y, y + h - 1)
    ).wait()


def validate_mfa(context: Context):
    fps = [p for p in (root / "config").glob("*.json") if p.name.startswith("c")]
    if len(fps) != 0:
        fp = fps[0]
    else:
        return
    mfa = jL(fp.open(encoding="utf-8"))
    if mfa.get(bdc("RG93bmxvYWRDREs="), "") == "":
        mfa.update(
            {
                bdc("RG93bmxvYWRTb3VyY2VJbmRleA=="): 0,
            }
        )

    mfa.update(
        {
            bdc("RW5hYmxlQXV0b1VwZGF0ZVJlc291cmNl"): True,
            bdc("RW5hYmxlQXV0b1VwZGF0ZU1GQQ=="): True,
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
    """
    快速滑动屏幕
    :param context: 上下文对象
    :param start_x: 起始点X坐标
    :param start_y: 起始点Y坐标
    :param end_x: 终点X坐标
    :param end_y: 终点Y坐标
    :param duration: 滑动持续时间，不建议低于200，单位毫秒
    :param end_hold: 滑动结束后是否急停，防止惯性滑动
    :param after_swipe_delay: 滑动完成后的延迟时间，单位毫秒

    如果要防止滑动动画存在惯性，end_hold参数需设置为0
    反之，如果要利用惯性滑动，需要将end_hold设为非0值
    """

    # 滑动参数增加随机噪声
    # 以防魔方真投入
    context.run_action(
        "custom_swipe",
        pipeline_override={
            "custom_swipe": {
                # 疑似有闭包问题
                # 采用手动随机而不是maafw自带的随机
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
    """
    点击并等待屏幕静止
    :param context: 上下文对象
    :param x: 点击点X坐标
    :param y: 点击点Y坐标
    :param w: 点击点宽度范围
    :param h: 点击点高度范围
    :param post_wait_freezes: 点击后等待屏幕静止的时间，单位毫秒
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
