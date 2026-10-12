import os
import random
import re
from collections.abc import Iterable
from datetime import datetime
from random import randint
from time import sleep

from maa.context import Context
from maa.define import RectType
from notifypy import Notify
from numpy import ndarray
from PIL import Image
from utils import bdc, debug_dir, get_format_timestamp, jD, jL, logo, root
from utils.logger import log_dir, logger


def save_screenshot(context: Context):
    """
    保存截图
    """
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
                logger.debug(f"OCR 绝对匹配成功: {target} in {reco_detail.filtered_results} with {result}")
                break

        if result is not None:
            logger.debug(f"OCR 绝对匹配成功: {expected}")
            return result.box  # ty:ignore[unresolved-attribute]
        else:
            logger.debug(f"{expected} 绝对匹配失败：{reco_detail.filtered_results}")
            return None


def wait_for_freezes(context: Context, wait_for_freezes: int = 200):
    context.run_task("wait_for_freezes", {"wait_for_freezes": {"wait_for_freezes": wait_for_freezes}})


def check_resolution(context: Context):
    resolution = context.tasker.controller.resolution
    if resolution[1] > resolution[0]:
        resolution = (resolution[1], resolution[0])
    if abs((resolution[0] / resolution[1]) - (16.0 / 9.0)) > 0.02:
        logger.error("你可能正在使用非推荐的分辨率！")
        logger.error("推荐使用的分辨率：1920x1080")
        logger.error(f"当前使用的分辨率：{resolution[0]}x{resolution[1]}")


def validate_config(context: Context):
    if len(list(root.glob("*.exe"))) == 0:
        return
    fp = [p for p in (root).glob("*.json") if p.name.startswith("in")][0]
    logger.info(f"验证配置文件: {fp}")
    config = jL(fp.open(encoding="utf-8"))
    config.update(
        {
            bdc("bmFtZQ=="): bdc("TWFhQXV0b05hcnV0bw=="),
            bdc("Z2l0aHVi"): bdc("aHR0cHM6Ly9naXRodWIuY29tL2R1b3J1YS9uYXJ1dG9tb2JpbGU="),
            bdc("bWlycm9yY2h5YW5fcmlk"): bdc("TWFhQXV0b05hcnV0bw=="),
        }
    )
    jD(config, fp.open("w", encoding="utf-8"), ensure_ascii=False, indent=4)


def click(context: Context, x: int, y: int, w: int = 1, h: int = 1):
    context.tasker.controller.post_click(random.randint(x, x + w - 1), random.randint(y, y + h - 1)).wait()


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
    :param duration: 滑动持续时间,不建议低于200,单位毫秒
    :param end_hold: 滑动结束后是否急停,防止惯性滑动
    :param after_swipe_delay: 滑动完成后的延迟时间,单位毫秒

    如果要防止滑动动画存在惯性,end_hold参数需设置为0
    反之,如果要利用惯性滑动,需要将end_hold设为非0值
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
    :param post_wait_freezes: 点击后等待屏幕静止的时间,单位毫秒
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
    """
    非线性滑动,形参参考fast_swipe()
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
        # 非线性进度计算
        t = i / steps
        prog = 1 - (1 - t) ** 2
        delta = prog - total_prog
        total_prog = prog

        # 计算当前坐标
        curr_x = int(s_x + (e_x - s_x) * prog)
        curr_y = int(s_y + (e_y - s_y) * prog)
        points.append([curr_x, curr_y])
        dur_list.append(round(total_dur * delta))

    # 总时长
    dur_list[-1] += total_dur - sum(dur_list)

    context.run_action(
        "custom_swipe",
        pipeline_override={
            "custom_swipe": {
                "action": "Swipe",
                "begin": [s_x, s_y],
                "end": points,  # 途径点
                "end_hold": hold_time,
                "duration": dur_list,  # 分段时间
            }
        },
    )
    sleep(after_swipe_delay / 1000)


def send_notification(title: str = "系统通知", msg: str = "这是一条测试消息"):
    Notify(title, msg, "MaaAutoNaruto", logo.__str__()).send()


def get_digit_count(context: Context, image: ndarray, roi: list[int], default=None) -> tuple[int | None, str | None]:
    """
    独立读取指定ROI的纯数字(小数点和正负号也会去除)
    :param context: MAA上下文
    :param image: 屏幕图像
    :param roi: 识别区域 [x, y, w, h]
    :return: tuple[int, str] (识别到的数字, 识别到的文本)
    """
    # 调用custom_ocr
    reco_detail = context.run_recognition(
        "GetTextWithNumers",
        image,
        {"GetTextWithNumers": {"roi": roi}},
    )

    if reco_detail is None or not reco_detail.hit:
        logger.warning(f"ROI {roi} 未识别到任何带数字的文本")
        return default, None

    # 提取并清洗识别文本,仅保留数字
    source_text = str(
        reco_detail.best_result.text  # ty:ignore[unresolved-attribute]
    ).strip()

    # 正则提取纯数字,过滤所有非数字字符
    nums = re.findall(r"\d+", source_text, re.ASCII)
    if not nums:
        logger.warning(f"ROI {roi} 未提取到有效数字，原始文本：{source_text}")
        return default, source_text

    value = int(nums[0])
    return value, source_text


def cleanup_maafw_bak_logs(keep_count: int) -> datetime | None:
    """
    清理旧的 maafw.bak.*.log 文件,保留最新的 keep_count 个。
    返回最旧备份日志的时间作为后续日志/图片清理的基准;
    无法确定最旧日志时返回 None,调用方应跳过日志/图片清理。
    """
    log_files = list(debug_dir.glob("maafw.bak.*.log"))
    print(f"[日志清理] 找到日志总数: {len(log_files)}")
    if not log_files:
        print("[日志清理] 无符合格式的日志,无法确定最旧日志,跳过日志/图片清理")
        return None

    logs_with_time = []
    for log_path in log_files:
        try:
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        except OSError as e:
            print(f"[日志清理] 无法读取日志修改时间,无法确定最旧日志,跳过日志/图片清理: {log_path.name}: {e}")
            return None
        logs_with_time.append((mtime, log_path))

    logs_with_time.sort(key=lambda x: x[0], reverse=True)
    to_delete_logs = logs_with_time[keep_count:]

    if not to_delete_logs:
        print("[日志清理] 没有需要删除的日志")
        return None

    print(f"[日志清理] 待删除旧日志: {len(to_delete_logs)} 个")
    deleted = 0
    for mtime, log_path in to_delete_logs:
        try:
            log_path.unlink()
            deleted += 1
            print(f"[日志清理] 已删除: {log_path.name} (修改时间 {mtime})")
        except Exception as e:
            print(f"[日志清理] 删除失败 {log_path.name}: {e}")

    if deleted == 0:
        print("[日志清理] 没有成功删除任何 bak 日志,跳过后续清理")
        return None

    # keep_count 可能大于现有日志数，因此直接从保留切片中取最旧一份。
    retained_logs = logs_with_time[:keep_count]
    oldest_log_time = retained_logs[-1][0]
    print(f"[日志清理] 最旧日志时间: {oldest_log_time}")
    return oldest_log_time


def clean_images_in_dirs(base_time: datetime):
    """
    依次清理多个子目录下修改时间早于 base_time 的图片文件
    """
    sub_dirs = ("custom", "on_error", "vision")
    for sub_dir in sub_dirs:
        target_dir = debug_dir / sub_dir
        if not target_dir.exists():
            print(f"[图片清理] 目录不存在,跳过: {target_dir}")
            continue

        img_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        img_files = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in img_extensions]
        total_count = len(img_files)
        if total_count == 0:
            print(f"[图片清理] {sub_dir} 目录下无图片文件,跳过")
            continue

        to_delete = []
        for img_path in img_files:
            try:
                mtime = datetime.fromtimestamp(img_path.stat().st_mtime)
            except OSError as e:
                print(f"[图片清理] 无法读取图片修改时间,跳过: {img_path.name}: {e}")
                continue
            if mtime < base_time:
                to_delete.append((mtime, img_path))

        eligible = len(to_delete)
        if eligible == 0:
            print(f"[图片清理] {sub_dir} 目录下共有 {total_count} 张图片,没有修改时间早于 {base_time} 的图片")
            continue

        deleted = 0
        for mtime, img_path in to_delete:
            try:
                img_path.unlink()
                deleted += 1
                print(f"[图片清理] 删除图片: {img_path.name} (修改时间 {mtime})")
            except Exception as e:
                print(f"[图片清理] 删除失败 {img_path.name}: {e}")

        print(
            f"[图片清理] {sub_dir} 目录下共有 {total_count} 张图片,其中修改时间早于 {base_time} 的有 {eligible} 张,实际删除了 {deleted} 张"  # noqa: E501
        )


def clean_logs_in_dir(base_time: datetime):
    """
    清理 debug/custom 下修改时间早于 base_time 的日志文件
    """
    sub_dir = "custom"
    target_dir = debug_dir / sub_dir
    if not target_dir.exists():
        print(f"[日志清理] 目录不存在,跳过: {target_dir}")
        return

    log_files = list(target_dir.glob("*.log"))
    total_count = len(log_files)
    if total_count == 0:
        print(f"[日志清理] {sub_dir} 目录下无日志文件,跳过")
        return

    to_delete = []
    for log_path in log_files:
        try:
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        except OSError as e:
            print(f"[日志清理] 无法读取日志修改时间,跳过: {log_path.name}: {e}")
            continue
        if mtime < base_time:
            to_delete.append((mtime, log_path))

    eligible = len(to_delete)
    if eligible == 0:
        print(f"[日志清理] {sub_dir} 目录下共有 {total_count} 个日志文件,没有修改时间早于 {base_time} 的日志")
        return

    deleted = 0
    for mtime, log_path in to_delete:
        try:
            log_path.unlink()
            deleted += 1
            print(f"[日志清理] 删除日志: {log_path.name} (修改时间 {mtime})")
        except Exception as e:
            print(f"[日志清理] 删除失败 {log_path.name}: {e}")

    print(
        f"[日志清理] {sub_dir} 目录下共有 {total_count} 个日志文件,其中修改时间早于 {base_time} 的有 {eligible} 个,实际删除了 {deleted} 个"  # noqa: E501
    )
