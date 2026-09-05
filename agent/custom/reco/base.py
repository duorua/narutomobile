import json
import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import Rect
from numpy import ndarray
from utils.counter import counter
from utils.logger import logger
from utils.utils import is_android

from ..utils import get_digit_count


@AgentServer.custom_recognition("IsCounterOverflow")
class IsCounterOverflow(CustomRecognition):
    """
    计数器溢出检测
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        max_hit = int(param.get("max_hit", "0"))

        if max_hit <= 0:
            logger.error("max_hit 参数错误，请检查")
            context.tasker.post_stop()
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        now_count = counter.get_count(argv.task_detail.task_id)
        logger.info(
            f"当前节点名:{argv.node_name};当前任务入口:{argv.task_detail.entry};任务id:{argv.task_detail.task_id}"
        )
        if now_count >= max_hit:
            logger.debug(f"计数器溢出！最大值: {max_hit} 当前值: {now_count} ")
            logger.info("达到最大执行次数")
            return CustomRecognition.AnalyzeResult(box=None, detail={})
        logger.debug(f"计数器状态： 最大值: {max_hit} 当前值: {now_count} ")
        return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})


@AgentServer.custom_recognition("IsInNinjaGuide")
class IsInNinjaGuide(CustomRecognition):
    """
    是否在忍界引导界面
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        reco_detail = context.run_recognition("in_ninja_guide", argv.image, {})
        if reco_detail and reco_detail.hit:
            # GoIntoEntryByGuide不需要这个box
            return CustomRecognition.AnalyzeResult(
                box=Rect(0, 0, 1, 1),
                detail={},
            )
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("FindPlantableFlower")
class FindPlantableFlower(CustomRecognition):
    """
    中山花店
    在选花界面中寻找可以种的花
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        flower_config = [
            (
                [400, 355, 111, 32],
                [440, 298, 37, 41],
            ),
            (
                [509, 355, 103, 29],
                [543, 298, 29, 27],
            ),
            (
                [607, 355, 106, 27],
                [642, 295, 34, 34],
            ),
            (
                [711, 355, 103, 32],
                [749, 300, 29, 29],
            ),
            (
                [810, 256, 143, 140],
                [844, 298, 37, 34],
            ),
        ]

        logger.info("开始检测可种植的花(需10个种子)...")

        # 遍历5种花,依次检查种子数量
        for flower_idx, (seed_roi, btn_roi) in enumerate(flower_config):
            flower_num = flower_idx + 1
            logger.info(f"正在检查第{flower_num}种花...")

            current_seeds = self.get_seed_count(context=context, image=argv.image, roi=seed_roi)
            if current_seeds is None:
                logger.warning(f"第{flower_num}种花:种子数量读取失败,跳过")
                continue

            # 判断种子是否足够(≥10)
            if current_seeds < 10:
                logger.info(f"第{flower_num}种花:种子不足({current_seeds}/10),跳过")
                continue

            # 种子充足,返回按钮位置
            logger.info(f"第{flower_num}种花:种子充足({current_seeds}/10)")
            btn_box = Rect(btn_roi[0], btn_roi[1], btn_roi[2], btn_roi[3])
            return CustomRecognition.AnalyzeResult(
                box=btn_box,
                detail={
                    "flower_num": flower_num,
                    "seed_count": current_seeds,
                    "btn_roi": btn_roi,
                },
            )

        # 无可用种子或全识别失败
        invalid_box = Rect(0, 0, 1, 1)  # 直接返回None的box会重试，所以我返回一个不影响的box
        return CustomRecognition.AnalyzeResult(box=invalid_box, detail={"has_valid_target": False})

    def get_seed_count(self, context: Context, image: ndarray, roi: list[int]) -> int | None:
        """
        在选花界面中寻找可以种的花
        """

        reco_detail = context.run_recognition(
            "GetTextWithNumers",
            image,
            {
                "GetTextWithNumers": {"roi": roi},
            },
        )

        if reco_detail is None:
            logger.warning(f"ROI{roi}:种子数量识别失败(识别器返回None)")
            return None

        if not reco_detail.hit:
            logger.debug(f"ROI{roi}:未识别到种子文本(hit=False)")
            logger.warning(f"ROI{roi}:无法读取到种子数量文本!")
            return None

        if reco_detail.best_result is None:
            logger.warning(f"ROI{roi}:识别到文本但解析失败(best_result为空)")
            return None

        source_text = str(reco_detail.best_result.text).strip().replace(" ", "")  # type: ignore
        logger.debug(f"ROI{roi}:识别到种子文本:{source_text}")

        prefix = "剩余"
        if prefix not in source_text:
            logger.warning(f"ROI{roi}:种子文本无'剩余'关键字,识别文本:{source_text}")
            return None

        colon_index = source_text.find(prefix) + len(prefix)
        if colon_index >= len(source_text) or source_text[colon_index] not in [
            ":",
            "：",
        ]:
            logger.warning(f"ROI{roi}:种子文本格式错误(无有效冒号),识别文本:{source_text}")
            return None

        slash_index = source_text.find("/", colon_index + 1)
        if slash_index == -1:
            logger.warning(f"ROI{roi}:种子文本无'/'分隔符,识别文本:{source_text}")
            return None

        seed_str = source_text[colon_index + 1 : slash_index]
        if not seed_str.isdigit():
            logger.warning(f"ROI{roi}:种子数量不是数字,实际:{seed_str}(识别文本:{source_text})")
            return None

        current_seeds = int(seed_str)
        logger.info(f"ROI{roi}:解析到种子数量:{current_seeds}/10")
        return current_seeds


@AgentServer.custom_recognition("FindBondsWithoutEnoughToken")
class FindBondsWithoutEnoughToken(CustomRecognition):
    """
    羁绊追寻
    固定读取ROI的纯数字
    数字 < 5 ,返回识别通过(非空box)
    数字 ≥ 5 或识别失败,返回识别未通过(空box)
    """

    TOKEN_CHECK_ROI = [846, 639, 111, 80]

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行FindBondsWithoutEnoughToken节点 =====")

        # 读取token数量
        token_count, _ = get_digit_count(context, argv.image, self.TOKEN_CHECK_ROI)

        # 识别失败
        if token_count is None:
            logger.warning("[FindBondsWithoutEnoughToken] token数量识别失败,返回未通过")
            return CustomRecognition.AnalyzeResult(box=None, detail={"token_count": None, "passed": False})

        # 数字 < 5
        if token_count < 5:
            logger.info(f"[FindBondsWithoutEnoughToken] token数量{token_count}<5,返回识别通过")
            # 返回非空box表示节点识别通过
            pass_box = Rect(0, 0, 1, 1)
            return CustomRecognition.AnalyzeResult(box=pass_box, detail={"token_count": token_count, "passed": True})

        # 数字 ≥ 5
        logger.info(f"[FindBondsWithoutEnoughToken] token数量{token_count}≥5,返回识别未通过")
        return CustomRecognition.AnalyzeResult(box=None, detail={"token_count": token_count, "passed": False})


def get_flip_ticket_count(context: Context, image: ndarray, roi: list[int], text_modifier=lambda x: x) -> int | None:
    """
    独立读取指定ROI的翻牌卷数量(调用custom_oc)，支持自定义文本修改
    :param context: MAA上下文
    :param image: 屏幕图像
    :param roi: 识别区域 [x, y, w, h]
    :param text_modifier: 文本修改函数，入参原始识别文本，返回修改后文本（用于去掉前缀/替换字符等）
    :return: 解析后的整型数字,失败返回None
    """

    reco_detail = context.run_recognition("custom_ocr", image, {"custom_ocr": {"roi": roi}})

    # 基础校验：识别器返回None或未命中文本
    if reco_detail is None or not reco_detail.hit:
        logger.warning(f"[get_flip_ticket_count] ROI{roi} 未识别到任何文本")
        return None

    # 提取并清洗原始识别文本
    source_text = str(reco_detail.best_result.text).strip()  # type: ignore
    logger.debug(f"[get_flip_ticket_count] ROI{roi} 原始识别文本：{source_text}")

    # 执行自定义文本修改（似乎python和低代码的OCR不一样,所以这里目前没有修改）
    modified_text = text_modifier(source_text)
    logger.debug(f"[get_flip_ticket_count] ROI{roi} 修改后识别文本：{modified_text}")

    # 正则提取纯数字
    num_match = re.search(r"\d+", modified_text)
    if not num_match:
        logger.warning(f"[get_flip_ticket_count] ROI{roi} 未提取到有效数字，修改后文本：{modified_text}")
        return None

    # 数字转换（异常捕获）
    try:
        ticket_count = int(num_match.group())
        logger.info(f"[get_flip_ticket_count] ROI{roi} 解析到翻牌卷数量:{ticket_count}")
        return ticket_count
    except ValueError:
        logger.warning(f"[get_flip_ticket_count] ROI{roi} 数字转换失败，提取字符串：{num_match.group()}")
        return None


@AgentServer.custom_recognition("FindAccessoryFlipTicket")
class FindAccessoryFlipTicket(CustomRecognition):
    """
    秘境饰品翻牌卷识别
    """

    # 饰品翻牌卷ROI
    ACCESSORY_TICKET_ROI = [550, 481, 171, 238]

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行饰品翻牌卷识别 =====")

        # 调用独立识别函数，传入ROI+自定义文本修改
        # lambda x: x[1:] if x else x是去掉第一个字符，无修改则改为lambda x:x
        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.ACCESSORY_TICKET_ROI,
            text_modifier=lambda x: x,
        )

        if ticket_count is None:
            logger.warning("饰品翻牌卷数量识别失败,返回未通过")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if ticket_count > 0:
            logger.info(f"饰品翻牌卷数量{ticket_count}>0,返回识别通过")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.info(f"饰品翻牌卷数量{ticket_count}≤0,返回识别未通过")
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("FindGearFlipTicket")
class FindGearFlipTicket(CustomRecognition):
    """
    忍具翻牌卷识别:和上面的饰品翻牌差不多
    """

    # 忍具翻牌卷ROI
    GEAR_TICKET_ROI = [436, 483, 138, 236]

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行忍具翻牌卷识别 =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.GEAR_TICKET_ROI,
            text_modifier=lambda x: x,
        )

        if ticket_count is None:
            logger.warning("忍具翻牌卷数量识别失败,返回未通过")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if ticket_count > 0:
            logger.info(f"忍具翻牌卷数量{ticket_count}>0,返回识别通过")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.info(f"忍具翻牌卷数量{ticket_count}≤0,返回识别未通过")
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("SecretRealmTicket")
class SecretRealmTicket(CustomRecognition):
    """
    秘境挑战卷识别:和上面的饰品翻牌差不多
    """

    # 秘境挑战卷ROI
    Secret_Real_Roi = [496, 624, 39, 44]

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行秘境挑战卷识别 SecretRealmTicket =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.Secret_Real_Roi,
            text_modifier=lambda x: x,
        )

        if ticket_count is None:
            logger.warning("[SecretRealmTicket] 秘境挑战卷数量识别失败,返回未通过,可能是挑战卷不够了")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if ticket_count > 0:
            logger.info(f"[SecretRealmTicket] 秘境挑战卷数量{ticket_count}>0,返回识别通过")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.info(f"[SecretRealmTicket] 秘境挑战卷数量{ticket_count}≤0,返回识别未通过")
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("MissionOfficeStrategy")
class MissionOfficeStrategy(CustomRecognition):
    """
    策略
    目前刷新上限 ROI: [1004,614,27,27]
    可接受任务 ROI: [1003,648,22,28]
    判断公式：(目前刷新上限 - 9) * 3 >= 可接受任务
    也就是期望是一次刷新能刷3个神秘箱子任务,紫箱子比较转
    """

    # 资源上限 识别ROI
    MAX_RESOURCE_ROI = [1004, 614, 27, 27]
    # 已获得资源个数 识别ROI
    CURRENT_RESOURCE_ROI = [1003, 648, 22, 28]

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行任务集会所策略选择 MissionOfficeStrategy =====")

        # 目前刷新上限
        max_resource = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.MAX_RESOURCE_ROI,
            text_modifier=lambda x: x,
        )

        # 可接受任务
        current_resource = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.CURRENT_RESOURCE_ROI,
            text_modifier=lambda x: x,
        )

        # 识别失败
        if max_resource is None or current_resource is None:
            logger.warning("[MissionOfficeStrategy] 数字识别失败,返回未通过(安全策略)")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        logger.info(f"[MissionOfficeStrategy] 识别结果：刷新上限={max_resource},可接取={current_resource}")

        condition = (max_resource - 9) * 3 >= current_resource
        if condition:
            logger.info("[MissionOfficeStrategy] 公式条件成立，返回识别通过(贪心策略)")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})
        else:
            logger.info("[MissionOfficeStrategy] 公式条件不成立，返回识别未通过(安全策略)")
            return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("CheckGetCopperRoll")
class CheckGetCopperRoll(CustomRecognition):
    """
    检测招财轮次,识别轮次大于设定轮次+1则通过
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        roi = [104, 468, 40, 31]
        param = json.loads(argv.custom_recognition_param)
        count = int(param.get("count", "1"))
        now_count, _ = get_digit_count(context, argv.image, roi)
        if now_count is None:
            now_count = 66

        if now_count >= count + 1:
            logger.info(f"当前值: {now_count},达到最大执行次数{count}")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.debug(f"招财轮次计数器状态： 最大值: {count} 当前值: {now_count} ")
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("CheckGetCopperCount")
class CheckGetCopperCount(CustomRecognition):
    """
    检测招财次数,识别次数大于设定次数则通过
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        roi = [309, 468, 27, 30]
        param = json.loads(argv.custom_recognition_param)
        count = int(param.get("count", "1"))
        now_count, _ = get_digit_count(context, argv.image, roi)
        if now_count is None:
            now_count = 66

        if now_count >= count:
            logger.info(f"当前值: {now_count},达到最大执行次数{count}")
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.debug(f"招财次数计数器状态： 最大值: {count} 当前值: {now_count} ")
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("CheckBuyEnergyCount")
class CheckBuyEnergyCount(CustomRecognition):
    """
    检测购买体力次数,第一次识别次数-目前识别次数>=传入次数则通过
    """

    start_count = -1

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        roi = [499, 374, 251, 59]
        param = json.loads(argv.custom_recognition_param)
        count = int(param.get("count", "1"))
        if self.start_count == -1:
            value, _ = get_digit_count(context, argv.image, roi)
            self.start_count = value if value else 0

        value, _ = get_digit_count(context, argv.image, roi)
        now_count = value if value else 0

        if self.start_count - now_count >= count:
            logger.info(
                f"当前值:{self.start_count - now_count},达到最大执行次数{count},初始值{self.start_count},识别值{now_count}"  # noqa: E501
            )
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.debug(
            f"购买体力计数器状态: 最大值:{count} 当前值: {self.start_count - now_count},初始值{self.start_count},识别值{now_count}"  # noqa: E501
        )
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("SwitchAccountFindTargetArea")
class SwitchAccountFindTargetArea(CustomRecognition):
    """
    切换账号找目标区
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        target_area = param.get("expected", "521")
        area_roi = context.run_recognition("switch_account_target_area_roi", argv.image)
        for result in area_roi.all_results:
            box = list(result.box)
            reco_detail = context.run_recognition("custom_ocr", argv.image, {"custom_ocr": {"roi": box}})
            if reco_detail and reco_detail.hit:
                try:
                    area_num = reco_detail.best_result.text.strip()
                    if area_num == target_area:
                        return CustomRecognition.AnalyzeResult(box=box, detail={})
                except (AttributeError, ValueError, TypeError):
                    continue
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("CheckIsAndroid")
class CheckIsAndroid(CustomRecognition):
    """
    是否在安卓环境中运行
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        if is_android:
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})
        context.override_pipeline(
            {
                "start_up_switch_social_media_account": {
                    "action": "DoNothing",
                    "focus": {"Node.Action.Starting": '<font color="tomato">安卓端man不能尝试唤起qq</font>'},
                },
                "switch_account_switch_social_media_account": {
                    "action": "DoNothing",
                    "focus": {"Node.Action.Starting": '<font color="tomato">安卓端man不能尝试唤起qq</font>'},
                },
            },
        )
        return CustomRecognition.AnalyzeResult(box=None, detail={})
