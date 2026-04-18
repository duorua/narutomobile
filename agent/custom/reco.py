import json
import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import Rect
from numpy import ndarray
from utils.counter import counter
from utils.logger import logger
from utils.profiler import profiled

from .constants import (
    ACCESSORY_TICKET_ROI,
    BONDS_TOKEN_CHECK_ROI,
    BONDS_TOKEN_THRESHOLD,
    CHALLENGE_BUTTON_TARGETS,
    ENEMY_LIST_SENRYOKU_ROI,
    FLOWER_CONFIG,
    FLOWER_SEED_THRESHOLD,
    GEAR_TICKET_ROI,
    SECRET_REALM_TICKET_ROI,
    TEAM_SENRYOKU_ROI,
    UNCHALLENGEABLE_SENRYOKU,
)


def correct_senryoku_text(source_text: str) -> int | None:
    """把 OCR 读到的战力文本解析为整数。

    规则：若文本以 ``"万"`` 结尾，去掉"万"并在末尾补 ``"0000"``；然后
    要求剩余部分全部为数字。

    Args:
        source_text: OCR 读到的原始文本，如 ``"5万"`` / ``"12345"``。

    Returns:
        成功 → 解析出的 ``int`` 战力（如 ``"5万" → 50000``）；失败 →
        ``None`` 并记录 warning。
    """
    if source_text.endswith("万"):
        text = source_text[:-1]
        text += "0000"
    else:
        text = source_text

    if text.isdigit():
        logger.info(f"读取到战力：{source_text}")
        return int(text)

    logger.warning(f"战力解析错误：{source_text}")
    return None


def get_senryoku(context: Context, image: ndarray, roi: list[int]) -> int | None:
    """在指定 ROI 内读取战力文本并解析为整数。

    Args:
        context: MAA 运行时上下文。
        image: 传入 MAA 的 BGR 截图数组。
        roi: 识别区域 ``[x, y, w, h]``。

    Returns:
        识别并解析成功 → 战力整数；识别失败或解析失败 → ``None``。
    """
    reco_detail = context.run_recognition(
        "GetSenryokuText",
        image,
        {
            "GetSenryokuText": {"roi": roi},
        },
    )

    if reco_detail is None or not reco_detail.hit:
        logger.opt(lazy=True).debug("战力识别详情: {d}", d=lambda: reco_detail)
        logger.warning("无法读取到战力！")
        return None

    source_text = str(reco_detail.best_result.text)
    return correct_senryoku_text(source_text)


@AgentServer.custom_recognition("IsCounterOverflow")
class IsCounterOverflow(CustomRecognition):
    """检测当前 ``task_id`` 的累计触发次数是否已达到 ``max_hit``。

    MAA 管线 `CustomRecognition` 注册名: ``"IsCounterOverflow"``。

    Expected ``custom_recognition_param``:
        ``{"max_hit": "<int>"}``
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """判定计数器是否溢出。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``；从
                ``argv.custom_recognition_param`` (JSON) 读取 ``max_hit``，
                从 ``argv.task_detail.task_id`` 取计数器键。

        Returns:
            * 未溢出 → ``AnalyzeResult(box=Rect(0,0,1,1), detail={})``
              （非空 box = 识别通过，允许任务继续）。
            * 已溢出 → ``AnalyzeResult(box=None, detail={})``
              （空 box = 识别未通过，MAA 管线据此跳出循环）。
            * ``max_hit <= 0`` 参数错误 → 停止 tasker 并返回 ``box=None``。
        """
        param = json.loads(argv.custom_recognition_param)
        max_hit = int(param.get("max_hit", "0"))

        if max_hit <= 0:
            logger.error("max_hit 参数错误，请检查")
            context.tasker.post_stop()
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        task_id = argv.task_detail.task_id
        now_count = counter.get_count(task_id)
        if now_count >= max_hit:
            logger.info(f"达到最大执行次数 (max={max_hit}, now={now_count})")
            return CustomRecognition.AnalyzeResult(box=None, detail={})
        logger.opt(lazy=True).debug(
            "计数器状态：max={m} now={n}",
            m=lambda: max_hit,
            n=lambda: now_count,
        )
        return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})


@AgentServer.custom_recognition("IsInNinjaGuide")
class IsInNinjaGuide(CustomRecognition):
    """判定当前屏幕是否在"忍界指引"界面。

    MAA 管线 `CustomRecognition` 注册名: ``"IsInNinjaGuide"``。
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """通过底层模板任务 ``in_ninja_guide`` 判定当前画面。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * 命中 → ``AnalyzeResult(box=Rect(0,0,1,1), detail={})``。
              下游 :class:`GoIntoEntryByGuide` 不使用 box，仅依赖识别通过。
            * 未命中 → ``AnalyzeResult(box=None, detail={})``。
        """
        reco_detail = context.run_recognition("in_ninja_guide", argv.image, {})
        if reco_detail and reco_detail.hit:
            # GoIntoEntryByGuide不需要这个box
            return CustomRecognition.AnalyzeResult(
                box=Rect(0, 0, 1, 1),
                detail={},
            )
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("FindToChallenge")
class FindToChallenge(CustomRecognition):
    """积分赛 — 找出 4 支敌方小队中战力最低、且我方可打得过的那支。

    MAA 管线 `CustomRecognition` 注册名: ``"FindToChallenge"``。

    Expected ``custom_recognition_param``:
        ``{"fource_battle": bool}``（原拼写保留）；``True`` 时忽略战力对比
        强制挑战最弱队。
    """

    @profiled
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        """读取我方战力 + 4 支敌队战力 → 挑最弱者。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image`` 和
                ``argv.custom_recognition_param`` 中的 ``fource_battle``。

        Returns:
            * 挑战成立 → ``AnalyzeResult(box=CHALLENGE_BUTTON_TARGETS[idx], detail={})``
              指向目标敌队的"挑战"按钮。
            * 我方战力读取失败 / 敌方战力不足 4 项 / 最弱敌方仍强于我方且
              未开强制战 → ``AnalyzeResult(box=None, detail={})``。
        """
        fource_battle = json.loads(argv.custom_recognition_param).get(
            "fource_battle", False
        )
        if fource_battle:
            logger.info("当前配置：强制挑战")
        else:
            logger.info("当前配置：非强制挑战")

        logger.info("尝试读取我方小队战力...")
        team_senryoku = get_senryoku(context, argv.image, TEAM_SENRYOKU_ROI)
        if team_senryoku is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={},
            )

        logger.info("尝试读取敌方小队战力...")

        reco_detail = context.run_recognition(
            "GetSenryokuText",
            argv.image,
            {
                "GetSenryokuText": {"roi": ENEMY_LIST_SENRYOKU_ROI},
            },
        )

        if (reco_detail is None) or len(reco_detail.filtered_results) < 4:
            logger.warning("无法读取到敌队战力！")
            logger.debug(
                f"识别结果：{reco_detail.all_results if reco_detail else None}"
            )
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={},
            )

        pattern = re.compile(r"\d+万?")
        enemySenryoku_list = []
        for x in reco_detail.filtered_results[:4]:
            match = pattern.search(x.text)  # ty:ignore[unresolved-attribute]
            if match:
                senryoku = correct_senryoku_text(match.group())
                if senryoku:
                    enemySenryoku_list.append(senryoku)
                else:
                    logger.warning(
                        f"无法解析战力文本: {x.text}"  # ty:ignore[unresolved-attribute]
                    )
                    enemySenryoku_list.append(UNCHALLENGEABLE_SENRYOKU)
            else:
                logger.warning(
                    f"无法解析战力文本: {x.text}"  # ty:ignore[unresolved-attribute]
                )
                enemySenryoku_list.append(1145141919810)  # 一个非常大的数，表示无法挑战

        min_enemySenryoku = min(enemySenryoku_list)
        idx = enemySenryoku_list.index(min_enemySenryoku)
        logger.info(f"敌队{idx + 1}战力最低：{min_enemySenryoku/10000}万")

        if (min_enemySenryoku > team_senryoku) and (not fource_battle):
            logger.info("没一个打得过的，溜了溜了。")
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={},
            )

        logger.info(f"挑战敌队{idx + 1}!")

        return CustomRecognition.AnalyzeResult(
            box=CHALLENGE_BUTTON_TARGETS[idx],
            detail={},
        )


@AgentServer.custom_recognition("FindPlantableFlower")
class FindPlantableFlower(CustomRecognition):
    """中山花店 — 找出第一种种子达阈值且可种植的花。

    依次检查 5 种花的种子数量，返回第一个种子数 ≥
    :data:`FLOWER_SEED_THRESHOLD` 的花对应的种植按钮 ROI。

    MAA 管线 `CustomRecognition` 注册名: ``"FindPlantableFlower"``。
    """

    @profiled
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        """按序找第一种种子充足的花并返回其种植按钮。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * 命中 → ``AnalyzeResult(box=Rect(btn_roi),
              detail={flower_num, seed_count, btn_roi})``。
            * 全部花不可种 / OCR 全部失败 →
              ``AnalyzeResult(box=Rect(0,0,1,1), detail={"has_valid_target": False})``。
              这里故意用一个 1×1 的"占位 Rect"避免 MAA 判定为识别失败而重试。
        """
        logger.info(f"开始检测可种植的花(需{FLOWER_SEED_THRESHOLD}个种子)...")

        for flower_idx, (seed_roi, btn_roi) in enumerate(FLOWER_CONFIG):
            flower_num = flower_idx + 1
            logger.info(f"正在检查第{flower_num}种花...")

            current_seeds = self.get_seed_count(
                context=context, image=argv.image, roi=seed_roi
            )
            if current_seeds is None:
                logger.warning(f"第{flower_num}种花:种子数量读取失败,跳过")
                continue

            if current_seeds < FLOWER_SEED_THRESHOLD:
                logger.info(f"第{flower_num}种花:种子不足({current_seeds}/{FLOWER_SEED_THRESHOLD}),跳过")
                continue

            logger.info(f"第{flower_num}种花:种子充足({current_seeds}/{FLOWER_SEED_THRESHOLD})")
            btn_box = Rect(btn_roi[0], btn_roi[1], btn_roi[2], btn_roi[3])
            return CustomRecognition.AnalyzeResult(
                box=btn_box,
                detail={
                    "flower_num": flower_num,
                    "seed_count": current_seeds,
                    "btn_roi": btn_roi,
                },
            )

        # 返回 None box 会让 MAA 重试；这里用 1x1 占位 Rect 表示"识别通过但无目标"。
        invalid_box = Rect(0, 0, 1, 1)
        return CustomRecognition.AnalyzeResult(
            box=invalid_box, detail={"has_valid_target": False}
        )

    def get_seed_count(
        self, context: Context, image: ndarray, roi: list[int]
    ) -> int | None:
        """从 OCR 文本 ``"剩余:N/10"`` 中解析当前种子数量 ``N``。

        需要完整的 ``"剩余"`` 前缀 + 冒号（中英文皆可）+ ``/`` 分隔符。

        Args:
            context: MAA 运行时上下文。
            image: 用于识别的 BGR 截图数组。
            roi: 识别区域 ``[x, y, w, h]``。

        Returns:
            解析成功 → 当前种子数 ``int``；识别或格式校验失败 → ``None``
            并记录 warning。
        """

        reco_detail = context.run_recognition(
            "GetSenryokuText",
            image,
            {
                "GetSenryokuText": {"roi": roi},
            },
        )

        if reco_detail is None:
            logger.warning(f"ROI{roi}:种子数量识别失败(识别器返回None)")
            return None

        if not reco_detail.hit:
            logger.warning(f"ROI{roi}:无法读取到种子数量文本(hit=False)")
            return None

        if reco_detail.best_result is None:
            logger.warning(f"ROI{roi}:识别到文本但解析失败(best_result为空)")
            return None

        source_text = str(reco_detail.best_result.text).strip().replace(" ", "")
        logger.opt(lazy=True).debug(
            "ROI{r}:识别到种子文本:{t}", r=lambda: roi, t=lambda: source_text
        )

        prefix = "剩余"
        if prefix not in source_text:
            logger.warning(f"ROI{roi}:种子文本无'剩余'关键字,识别文本:{source_text}")
            return None

        colon_index = source_text.find(prefix) + len(prefix)
        if colon_index >= len(source_text) or source_text[colon_index] not in [
            ":",
            "：",
        ]:
            logger.warning(
                f"ROI{roi}:种子文本格式错误(无有效冒号),识别文本:{source_text}"
            )
            return None

        slash_index = source_text.find("/", colon_index + 1)
        if slash_index == -1:
            logger.warning(f"ROI{roi}:种子文本无'/'分隔符,识别文本:{source_text}")
            return None

        seed_str = source_text[colon_index + 1 : slash_index]
        if not seed_str.isdigit():
            logger.warning(
                f"ROI{roi}:种子数量不是数字,实际:{seed_str}(识别文本:{source_text})"
            )
            return None

        current_seeds = int(seed_str)
        logger.info(f"ROI{roi}:解析到种子数量:{current_seeds}/10")
        return current_seeds


def get_card_type(context: Context, image: ndarray, roi: list[int]) -> int:
    """识别 4×4 翻牌游戏中单张卡牌的类型。

    依次尝试三套模板：紫色牌 → 橙色牌 → 未翻开牌，命中即返回；
    全部 miss 则认为识别失败（通常是触发"已翻开"提示或被奖励弹窗遮盖）。

    Args:
        context: MAA 运行时上下文。
        image: 用于识别的 BGR 截图数组。
        roi: 卡牌所在 ROI ``[x, y, w, h]``。

    Returns:
        整型卡牌类型编码：

        * ``0`` = 未翻开 (UNFLIPPED)
        * ``1`` = 紫色牌 (PURPLE)
        * ``2`` = 橙色牌 (ORANGE)
        * ``3`` = 识别失败 (RECOGNIZE_FAIL)
    """
    purple_reco = context.run_recognition("card_0", image, {"card_0": {"roi": roi}})
    if purple_reco and purple_reco.hit:
        return 1

    orange_reco = context.run_recognition("card_1", image, {"card_1": {"roi": roi}})
    if orange_reco and orange_reco.hit:
        return 2

    wait_reco = context.run_recognition("card_wait", image, {"card_wait": {"roi": roi}})
    if wait_reco and wait_reco.hit:
        return 0

    logger.warning(f"卡牌ROI{roi} 识别失败,应该是触发提示，或者被奖励遮盖")
    return 3


def recognize_ocr_integer(
    context: Context,
    image: ndarray,
    roi: list[int],
    label: str = "OCR",
    text_modifier=lambda x: x,
) -> int | None:
    """通用 OCR 整数识别：对指定 ROI 跑 OCR 并提取第一个整数。

    Args:
        context: MAA 运行时上下文。
        image: 用于识别的 BGR 截图数组。
        roi: 识别区域 ``[x, y, w, h]``。
        label: 日志标签，用于区分调用来源（如 ``"token_count"``）。
        text_modifier: 可选的 OCR 文本预处理函数，默认为 ``lambda x: x``。
            对 OCR 常见错字（如 "l → 1"）可通过此参数做局部修正。

    Returns:
        * 成功抓取到整数 → 转换后的 ``int``；
        * OCR 未命中 / 没有数字 / 数字转换异常 → ``None`` 并记录 warning。
    """
    reco_detail = context.run_recognition(
        "custom_ocr", image, {"custom_ocr": {"roi": roi}}
    )

    if reco_detail is None or not reco_detail.hit:
        logger.warning(f"[{label}] ROI{roi} 未识别到任何文本")
        return None

    source_text = str(reco_detail.best_result.text).strip()
    modified_text = text_modifier(source_text)
    logger.opt(lazy=True).debug(
        "[{l}] ROI{r} 识别文本：{s}{m}",
        l=lambda: label,
        r=lambda: roi,
        s=lambda: source_text,
        m=lambda: f" -> 修改后：{modified_text}" if modified_text != source_text else "",
    )

    num_match = re.search(r"\d+", modified_text)
    if not num_match:
        logger.warning(f"[{label}] ROI{roi} 未提取到有效数字，文本：{modified_text}")
        return None

    try:
        result = int(num_match.group())
        logger.info(f"[{label}] ROI{roi} 解析到数量: {result}")
        return result
    except ValueError:
        logger.warning(f"[{label}] ROI{roi} 数字转换失败：{num_match.group()}")
        return None


def get_token_count(context: Context, image: ndarray, roi: list[int]) -> int | None:
    """读取指定 ROI 中的 token 数量（OCR 整数识别的薄包装）。

    Args:
        context: MAA 运行时上下文。
        image: BGR 截图。
        roi: 识别区域 ``[x, y, w, h]``。

    Returns:
        成功 → token 整数；失败 → ``None``。
    """
    return recognize_ocr_integer(context, image, roi, label="token_count")


@AgentServer.custom_recognition("find_bonds_without_enough_token")
class FindBondsWithoutEnoughToken(CustomRecognition):
    """羁绊 — token 数量不足检测。

    MAA 管线 `CustomRecognition` 注册名: ``"find_bonds_without_enough_token"``。

    语义：

        * token 数 < :data:`BONDS_TOKEN_THRESHOLD` → 识别通过（需执行补 token 流程）；
        * token 数 ≥ 阈值 或识别失败 → 识别未通过（无需补）。
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """判定 token 数是否低于阈值。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * token < 阈值 →
              ``AnalyzeResult(box=Rect(0,0,1,1), detail={token_count, passed: True})``。
            * token ≥ 阈值 或识别失败 →
              ``AnalyzeResult(box=None, detail={token_count, passed: False})``。
        """
        logger.info("===== 执行find_bonds_without_enough_token节点 =====")

        token_count = get_token_count(context, argv.image, BONDS_TOKEN_CHECK_ROI)

        if token_count is None:
            logger.warning(
                "[find_bonds_without_enough_token] token数量识别失败,返回未通过"
            )
            return CustomRecognition.AnalyzeResult(
                box=None, detail={"token_count": None, "passed": False}
            )

        if token_count < BONDS_TOKEN_THRESHOLD:
            logger.info(
                f"[find_bonds_without_enough_token] "
                f"token数量{token_count}<{BONDS_TOKEN_THRESHOLD},返回识别通过"
            )
            pass_box = Rect(0, 0, 1, 1)
            return CustomRecognition.AnalyzeResult(
                box=pass_box, detail={"token_count": token_count, "passed": True}
            )

        logger.info(
            f"[find_bonds_without_enough_token] "
            f"token数量{token_count}≥{BONDS_TOKEN_THRESHOLD}，返回识别未通过"
        )
        return CustomRecognition.AnalyzeResult(
            box=None, detail={"token_count": token_count, "passed": False}
        )


def get_flip_ticket_count(
    context: Context, image: ndarray, roi: list[int], text_modifier=lambda x: x
) -> int | None:
    """读取指定 ROI 中的翻牌卷数量，支持自定义 OCR 文本预处理。

    Args:
        context: MAA 运行时上下文。
        image: BGR 截图。
        roi: 识别区域 ``[x, y, w, h]``。
        text_modifier: OCR 文本预处理函数，用于修正常见误识别。

    Returns:
        成功 → 翻牌卷数量整数；失败 → ``None``。
    """
    return recognize_ocr_integer(
        context, image, roi, label="flip_ticket", text_modifier=text_modifier
    )


@AgentServer.custom_recognition("FindAccessoryFlipTicket")
class FindAccessoryFlipTicket(CustomRecognition):
    """秘境饰品翻牌卷数量检测。

    MAA 管线 `CustomRecognition` 注册名: ``"FindAccessoryFlipTicket"``。
    数量 > 0 → 识别通过；为 0 或识别失败 → 识别未通过。
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """读取饰品翻牌卷数量并判定是否有可用。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * 数量 > 0 → ``AnalyzeResult(box=Rect(0,0,1,1), detail={})``。
            * 数量 ≤ 0 或识别失败 → ``AnalyzeResult(box=None, detail={})``。
        """
        logger.info("===== 执行饰品翻牌卷识别 =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=ACCESSORY_TICKET_ROI,
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
    """忍具翻牌卷数量检测（逻辑与 :class:`FindAccessoryFlipTicket` 相同）。

    MAA 管线 `CustomRecognition` 注册名: ``"FindGearFlipTicket"``。
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """读取忍具翻牌卷数量并判定是否有可用。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * 数量 > 0 → ``AnalyzeResult(box=Rect(0,0,1,1), detail={})``。
            * 数量 ≤ 0 或识别失败 → ``AnalyzeResult(box=None, detail={})``。
        """
        logger.info("===== 执行忍具翻牌卷识别 =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=GEAR_TICKET_ROI,
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
    """秘境挑战卷数量检测（逻辑与 :class:`FindAccessoryFlipTicket` 相同）。

    MAA 管线 `CustomRecognition` 注册名: ``"SecretRealmTicket"``。
    """

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """读取秘境挑战卷数量并判定是否有可用。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``AnalyzeArg``，使用 ``argv.image``。

        Returns:
            * 数量 > 0 → ``AnalyzeResult(box=Rect(0,0,1,1), detail={})``。
            * 数量 ≤ 0 或识别失败 → ``AnalyzeResult(box=None, detail={})``。
        """
        logger.info("===== 执行秘境挑战卷识别 SecretRealmTicket =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=SECRET_REALM_TICKET_ROI,
            text_modifier=lambda x: x,
        )

        if ticket_count is None:
            logger.warning(
                "[SecretRealmTicket] 秘境挑战卷数量识别失败,返回未通过,可能是挑战卷不够了"
            )
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if ticket_count > 0:
            logger.info(
                f"[SecretRealmTicket] 秘境挑战卷数量{ticket_count}>0,返回识别通过"
            )
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.info(
            f"[SecretRealmTicket] 秘境挑战卷数量{ticket_count}≤0,返回识别未通过"
        )
        return CustomRecognition.AnalyzeResult(box=None, detail={})
