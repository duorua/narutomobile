import cv2
import numpy as np
from maa.define import Rect
from numpy import ndarray
from utils.logger import logger


def template_match(
    img: ndarray,
    template: ndarray,
    green_mask: bool | tuple[tuple[int, int, int], tuple[int, int, int]] = False,
    roi: Rect | None = None,
) -> tuple[float, Rect]:
    """
    使用python侧cv2进行模板匹配，不会阻塞maafw侧行为
    :param img: 待匹配图片 BGR
    :param template: 模板图片 BGR
    :return: 匹配得分, 匹配位置
    """

    if green_mask is True:
        lower_green = np.array([0, 255, 0], dtype=np.uint8)
        upper_green = np.array([0, 255, 0], dtype=np.uint8)
        color_mask_img = cv2.inRange(template, lower_green, upper_green)
        mask = cv2.bitwise_not(color_mask_img)
    elif isinstance(green_mask, tuple):
        lower_green, upper_green = green_mask
        lower_np = np.array(lower_green, dtype=np.uint8)
        upper_np = np.array(upper_green, dtype=np.uint8)
        color_mask_img = cv2.inRange(template, lower_np, upper_np)
        mask = cv2.bitwise_not(color_mask_img)
    elif green_mask is False:
        mask = None
    else:
        raise ValueError("green_mask 参数错误")

    if roi is not None:
        # 符合 MaaFw 的编写习惯
        if roi.w == 0 or roi.h == 0:
            logger.warning("不要把roi的宽高设置为0！除非你知道自己正在做什么！")
            roi.w, roi.h = img.shape[:2]
        img = img[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]

    result_cv = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED, mask=mask)
    _, max_val_cv, _, max_loc_cv = cv2.minMaxLoc(result_cv)
    # print(f"得分: {max_val_cv:.4f}  位置: x={max_loc_cv[0]}, y={max_loc_cv[1]}")
    x, y = max_loc_cv
    h, w = template.shape[:2]
    return max_val_cv, Rect(x, y, w, h)
