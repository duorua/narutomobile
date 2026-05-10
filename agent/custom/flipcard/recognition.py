"""
FlipCardRecognition — MAA 框架集成层。

作为 CustomRecognition 注册到 MaaFramework 管线中，负责：
1. 通过屏幕截图识别 4x4 卡牌状态（调用 get_card_type）。
2. 构建 CardGrid 并委托 FlipStrategy 计算最优翻牌位置。
3. 将策略结果转换为 MAA AnalyzeResult 返回。

本文件是 FlipCard 功能与 MAA 框架之间的唯一耦合点。
"""

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import Rect
from utils.logger import logger
from utils.profiler import profiled

from ..constants import CARD_4X4_ROI, FLIP_TIP_CLICK_ROI
from ..reco import get_card_type
from .grid import GRID_SIZE, CardGrid
from .strategy import FlipStrategy


@AgentServer.custom_recognition("FlipCard")
class FlipCardRecognition(CustomRecognition):
    """周年庆 4x4 翻牌游戏的 MAA 识别处理器。

    整合屏幕识别 → 网格建模 → 贪心策略 → 结果输出的完整流程。
    算法逻辑委托给 :class:`~.strategy.FlipStrategy`，
    网格状态由 :class:`~.grid.CardGrid` 管理。

    MAA 管线注册名: ``"FlipCard"``（与原实现保持一致）。
    """

    def __init__(self) -> None:
        super().__init__()
        self._strategy = FlipStrategy()

    @profiled
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        """分析当前屏幕截图，决定下一步翻牌动作。

        流程：
        1. 对 4x4 网格中的每张卡牌进行图像识别，构建 CardGrid。
        2. 若存在识别失败 → 点击提示区域重试。
        3. 若检测到胜利（4 紫连线）→ 返回胜利标记。
        4. 委托 FlipStrategy 选择最优翻牌位置 → 返回对应 ROI。

        Args:
            context: MAA 上下文，提供截图和识别能力。
            argv: 包含当前截图 (image) 和任务参数的识别参数。

        Returns:
            AnalyzeResult，box 指向建议点击的屏幕区域。
        """
        logger.info("===== 开始检测翻牌游戏状态=====")

        raw_grid: list[list[int]] = []
        for row in range(GRID_SIZE):
            row_state: list[int] = []
            for col in range(GRID_SIZE):
                roi = CARD_4X4_ROI[row][col]
                card_type = get_card_type(context, argv.image, roi)
                row_state.append(card_type)
            raw_grid.append(row_state)

        grid = CardGrid(raw_grid)
        logger.info(f"当前卡牌状态网格：\n{raw_grid}")

        if grid.has_recognition_failure:
            logger.info(f"检测到识别失败,点击提示ROI:{FLIP_TIP_CLICK_ROI}")
            return CustomRecognition.AnalyzeResult(
                box=Rect(*FLIP_TIP_CLICK_ROI),
                detail={"action": "click_tip", "tip_roi": FLIP_TIP_CLICK_ROI},
            )

        victory_line = grid.check_victory()
        if victory_line is not None:
            logger.info(f"检测到{victory_line}4个紫色连成一线,胜利!")
            return CustomRecognition.AnalyzeResult(
                box=Rect(0, 0, 1, 1),
                detail={"has_valid_target": False, "is_win": True},
            )

        orange_info = grid.get_orange_info()
        logger.info(
            f"橙色牌信息：位置{[(x + 1, y + 1) for x, y in orange_info.orange_pos]}，"
            f"阻挡行{orange_info.orange_rows},"
            f"阻挡列{orange_info.orange_cols}，"
            f"阻挡对角线{orange_info.orange_diags}，"
            f"双对角线橙色：{orange_info.is_both_diag_orange}"
        )

        best_pos = self._strategy.get_next_move(grid)

        if best_pos is None:
            logger.warning("无未翻牌可翻")
            return CustomRecognition.AnalyzeResult(
                box=Rect(0, 0, 1, 1),
                detail={"has_valid_target": False, "reason": "no_unflip_card"},
            )

        best_roi = CARD_4X4_ROI[best_pos[0]][best_pos[1]]
        action = "flip_initial" if grid.is_initial_state() else "flip_growth"
        action_label = "初始状态" if action == "flip_initial" else "紫色生长"
        logger.info(
            f"{action_label}选择翻牌位置："
            f"({best_pos[0] + 1},{best_pos[1] + 1}),ROI={best_roi}"
        )

        return CustomRecognition.AnalyzeResult(
            box=Rect(*best_roi),
            detail={
                "has_valid_target": False,
                "action": action,
                "flip_pos": (best_pos[0] + 1, best_pos[1] + 1),
                "flip_roi": best_roi,
            },
        )
