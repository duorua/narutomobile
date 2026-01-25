import json
from maa.define import Rect
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
from numpy import ndarray
from typing import List, Tuple, Dict, Optional, Any
import re

from utils.logger import logger
from utils.counter import counter


def correct_senryoku_text(source_text: str) -> int | None:
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
    """
    获取战力
    """
    reco_detail = context.run_recognition(
        "GetSenryokuText",
        image,
        {
            "GetSenryokuText": {"roi": roi},
        },
    )

    if reco_detail is None or not reco_detail.hit:
        logger.debug(reco_detail)
        logger.warning("无法读取到战力！")
        return None

    source_text = str(reco_detail.best_result.text)  # type: ignore
    return correct_senryoku_text(source_text)


@AgentServer.custom_recognition("IsCounterOverflow")
class IsCounterOverflow(CustomRecognition):
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        max_hit = int(param.get("max_hit", "0"))

        if max_hit <= 0:
            logger.error("max_hit 参数错误，请检查")
            context.tasker.post_stop()
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        task_id = argv.task_detail.task_id
        now_count = counter.get_count(task_id)
        if now_count >= max_hit:
            logger.debug(f"计数器溢出！最大值: {max_hit} 当前值: {now_count} ")
            logger.info("达到最大执行次数")
            return CustomRecognition.AnalyzeResult(box=None, detail={})
        logger.debug(f"计数器状态： 最大值: {max_hit} 当前值: {now_count} ")
        return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})


@AgentServer.custom_recognition("IsInNinjiaGuide")
class IsInNinjiaGuide(CustomRecognition):
    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        reco_detail = context.run_recognition("in_ninjia_guide", argv.image, {})
        if reco_detail and reco_detail.hit:
            # GoIntoEntryByGuide不需要这个box
            return CustomRecognition.AnalyzeResult(
                box=Rect(0, 0, 1, 1),
                detail={},
            )
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("FindToChallenge")
class FindToChallenge(CustomRecognition):
    """
    在积分赛中寻找可以挑战的对象
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        fource_battle = json.loads(argv.custom_recognition_param).get(
            "fource_battle", False
        )
        if fource_battle:
            logger.info("当前配置：强制挑战")
        else:
            logger.info("当前配置：非强制挑战")

        logger.info("尝试读取我方小队战力...")
        team_senryoku = get_senryoku(context, argv.image, [271, 337, 178, 29])
        if team_senryoku is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={},
            )

        enemy_list_roi = [714, 207, 248, 431]

        logger.info("尝试读取敌方小队战力...")

        reco_detail = context.run_recognition(
            "GetSenryokuText",
            argv.image,
            {
                "GetSenryokuText": {"roi": enemy_list_roi},
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
                enemySenryoku_list.append(correct_senryoku_text(match.group()))
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
        targets = [
            [986, 195, 92, 39],
            [987, 312, 92, 39],
            [988, 430, 92, 39],
            [987, 548, 92, 39],
        ]

        return CustomRecognition.AnalyzeResult(
            box=targets[idx],
            detail={},
        )


@AgentServer.custom_recognition("FindPlantableFlower")
class FindPlantableFlower(CustomRecognition):
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

            current_seeds = self.get_seed_count(
                context=context, image=argv.image, roi=seed_roi
            )
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
        invalid_box = Rect(
            0, 0, 1, 1
        )  # 直接返回None的box会重试，所以我返回一个不影响的box
        return CustomRecognition.AnalyzeResult(
            box=invalid_box, detail={"has_valid_target": False}
        )

    def get_seed_count(
        self, context: Context, image: ndarray, roi: list[int]
    ) -> int | None:
        """
        在选花界面中寻找可以种的花
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
    """
    识别单张卡牌类型
    return: 0=未翻开 1=紫色牌 2=橙色牌 3=识别失败（如触发牌已经翻开的提示，或者被奖励遮盖）
    """
    # 识别紫色牌
    purple_reco = context.run_recognition("card_0", image, {"card_0": {"roi": roi}})
    if purple_reco and purple_reco.hit:
        return 1

    # 识别橙色牌
    orange_reco = context.run_recognition("card_1", image, {"card_1": {"roi": roi}})
    if orange_reco and orange_reco.hit:
        return 2

    # 识别未翻开牌
    wait_reco = context.run_recognition("card_wait", image, {"card_wait": {"roi": roi}})
    if wait_reco and wait_reco.hit:
        return 0

    # 识别失败
    logger.warning(f"卡牌ROI{roi} 识别失败,应该是触发提示，或者被奖励遮盖")
    return 3


@AgentServer.custom_recognition("FlipCard")
class FlipCard(CustomRecognition):
    """
    4x4翻牌游戏算法逻辑(优先同方向生长)
    规则：
    1. 胜利判定：仅统计紫色牌数量,连续4个判定胜利;
    2. 初始状态：优先选橙色不在的对角线牌，双对角线橙色则选横竖无橙色牌；
    3. 紫色生长：
       - 按“单一方向（行/列/对角线）的最高紫色数”评分；
       - 同最高分下，优先选该方向内的位置（比如行分数最高→优先选该行）；
       - 有橙色的方向（行/列/对角线),紫色数直接计0;
       - 同分数+同方向下，优先选对角线位置（双对角线橙色时忽略）；
    4.你违反了规则
    """

    # 地图
    CARD_4X4_ROI = [
        [
            [206, 94, 145, 109],
            [357, 94, 145, 111],
            [508, 94, 148, 111],
            [661, 94, 145, 111],
        ],
        [
            [206, 212, 145, 111],
            [360, 212, 143, 108],
            [510, 212, 143, 108],
            [661, 212, 145, 111],
        ],
        [
            [204, 328, 145, 111],
            [360, 328, 143, 111],
            [510, 328, 143, 111],
            [661, 328, 145, 111],
        ],
        [
            [206, 447, 143, 111],
            [357, 444, 145, 111],
            [510, 447, 143, 111],
            [661, 447, 145, 111],
        ],
    ]
    TIP_CLICK_ROI = [1035, 229, 103, 93]  # 识别失败点击ROI
    MAIN_DIAG = [(0, 0), (1, 1), (2, 2), (3, 3)]  # 主对角线（左上-右下）
    SUB_DIAG = [(0, 3), (1, 2), (2, 1), (3, 0)]  # 副对角线（右上-左下）
    ALL_DIAG = MAIN_DIAG + SUB_DIAG  # 所有对角线位置

    def _get_orange_info(self, card_state_grid: List[List[int]]) -> Dict[str, Any]:
        """提取橙色牌信息(只要有1个橙色就标记该对角线)"""
        orange_pos = []
        orange_rows = set()
        orange_cols = set()
        orange_diags = set()
        is_both_diag_orange = False

        # 遍历所有牌，标记橙色位置/行/列/对角线
        for row in range(4):
            for col in range(4):
                if card_state_grid[row][col] == 2:
                    orange_pos.append((row, col))
                    orange_rows.add(row)
                    orange_cols.add(col)
                    # 只要对角线有1个橙色，就标记该对角线为橙色
                    if (row, col) in self.MAIN_DIAG:
                        orange_diags.add("main")
                    if (row, col) in self.SUB_DIAG:
                        orange_diags.add("sub")

        # 判断是否双对角线都有橙色
        if "main" in orange_diags and "sub" in orange_diags:
            is_both_diag_orange = True
            logger.info("检测到双对角线都有橙色，忽略对角线优先级")

        return {
            "orange_pos": orange_pos,
            "orange_rows": orange_rows,
            "orange_cols": orange_cols,
            "orange_diags": orange_diags,
            "is_both_diag_orange": is_both_diag_orange,
        }

    def _is_initial_state(self, card_state_grid: List[List[int]]) -> bool:
        """判断是否初始状态（除橙色外全未翻牌）"""
        for row in range(4):
            for col in range(4):
                if card_state_grid[row][col] not in [0, 2]:
                    return False
        return True

    def _get_valid_initial_pos(
        self, card_state_grid: List[List[int]], orange_info: Dict
    ) -> Tuple[int, int]:
        """初始状态选最优翻牌位置"""
        all_unflip = [
            (r, c) for r in range(4) for c in range(4) if card_state_grid[r][c] == 0
        ]
        if not all_unflip:
            return all_unflip[0]

        # 双对角线橙色 → 优先选横竖无橙色的未翻牌
        if orange_info["is_both_diag_orange"]:
            valid_unflip = [
                (r, c)
                for (r, c) in all_unflip
                if r not in orange_info["orange_rows"]
                and c not in orange_info["orange_cols"]
            ]
            if valid_unflip:
                logger.info(f"双对角线橙色，选横竖无橙色的未翻牌：{valid_unflip[0]}")
                return valid_unflip[0]
            return all_unflip[0]

        # 单对角线橙色 → 优先选另一对角线无橙色的牌
        diag_unflip = [pos for pos in all_unflip if pos in self.ALL_DIAG]
        if not diag_unflip:
            return all_unflip[0]

        priority1 = []  # 不在橙色行/列+不在橙色对角线
        priority2 = []  # 不在橙色行/列
        priority3 = []  # 其他对角线牌

        for r, c in diag_unflip:
            in_orange_row_col = (r in orange_info["orange_rows"]) or (
                c in orange_info["orange_cols"]
            )
            in_orange_diag = False
            if (r, c) in self.MAIN_DIAG and "main" in orange_info["orange_diags"]:
                in_orange_diag = True
            if (r, c) in self.SUB_DIAG and "sub" in orange_info["orange_diags"]:
                in_orange_diag = True

            if not in_orange_row_col and not in_orange_diag:
                priority1.append((r, c))
            elif not in_orange_row_col:
                priority2.append((r, c))
            else:
                priority3.append((r, c))

        if priority1:
            logger.info(f"初始状态选优先级1对角线牌:{priority1[0]}")
            return priority1[0]
        elif priority2:
            logger.info(f"初始状态选优先级2对角线牌:{priority2[0]}")
            return priority2[0]
        elif priority3:
            logger.info(f"初始状态选优先级3对角线牌:{priority3[0]}")
            return priority3[0]
        return diag_unflip[0]

    def _calc_single_dir_score(
        self, pos: Tuple[int, int], card_state_grid: List[List[int]], orange_info: Dict
    ) -> Dict[str, int | str]:
        """
        计算单一方向的分数（非叠加）：行/列/对角线各自的分数
        return: {"row_score": 行分数, "col_score": 列分数, "diag_score": 对角线分数, "max_score": 最高分}
        """
        r, c = pos
        orange_rows = orange_info["orange_rows"]
        orange_cols = orange_info["orange_cols"]
        orange_diags = orange_info["orange_diags"]

        # 1. 行分数：有橙色则0，否则该行紫色数
        row_score = 0
        if r not in orange_rows:
            row_score = sum(1 for col in range(4) if card_state_grid[r][col] == 1)

        # 2. 列分数：有橙色则0，否则该列紫色数
        col_score = 0
        if c not in orange_cols:
            col_score = sum(1 for row in range(4) if card_state_grid[row][c] == 1)

        # 3. 对角线分数：有橙色则0，否则所属对角线的紫色数
        diag_score = 0
        # 主对角线
        if (r, c) in self.MAIN_DIAG and "main" not in orange_diags:
            diag_score = sum(
                1 for (x, y) in self.MAIN_DIAG if card_state_grid[x][y] == 1
            )
        # 副对角线（若同时在两个对角线，取最大值,不过应该不会出现这种情况）
        if (r, c) in self.SUB_DIAG and "sub" not in orange_diags:
            sub_score = sum(1 for (x, y) in self.SUB_DIAG if card_state_grid[x][y] == 1)
            diag_score = max(diag_score, sub_score)

        # 4. 单一方向最高分
        max_score = max(row_score, col_score, diag_score)

        return {
            "row_score": row_score,
            "col_score": col_score,
            "diag_score": diag_score,
            "max_score": max_score,
            # 标记最高分所属方向（用于优先选同方向位置）
            "max_dir": (
                "row"
                if row_score == max_score
                else ("col" if col_score == max_score else "diag")
            ),
        }

    def _get_best_growth_pos_by_score(
        self, card_state_grid: List[List[int]], orange_info: Dict
    ) -> Optional[Tuple[int, int]]:
        """
        优先同方向生长
        """
        all_unflip = [
            (r, c) for r in range(4) for c in range(4) if card_state_grid[r][c] == 0
        ]
        if not all_unflip:
            return None

        # 计算每个未翻牌的单一方向分数
        pos_data = []
        for pos in all_unflip:
            dir_scores = self._calc_single_dir_score(pos, card_state_grid, orange_info)
            max_score: int = dir_scores["max_score"]  # type: ignore
            max_dir = dir_scores["max_dir"]
            # 排序权重：1. 最高分降序 → 2. 最高分方向（行>列>对角线）→ 3. 对角线优先 → 4. 行列号升序
            dir_priority = 0 if max_dir == "row" else (1 if max_dir == "col" else 2)
            is_diag = (
                1
                if (pos in self.ALL_DIAG and not orange_info["is_both_diag_orange"])
                else 0
            )
            pos_data.append((-max_score, dir_priority, -is_diag, pos))

        # 排序规则：
        # 1. -max_score → 最高分降序；
        # 2. dir_priority → 行>列>对角线；
        # 3. -is_diag → 对角线优先；
        # 4. pos → 行列号升序；
        pos_data.sort()
        best_pos = pos_data[0][3]
        best_score = -pos_data[0][0]

        # 日志输出单一方向分数
        logger.info("未翻牌评分详情（优先同方向生长，行>列>对角线）：")
        for idx, item in enumerate(pos_data[:3]):
            max_score = -item[0]
            dir_priority = item[1]
            max_dir = (
                "行" if dir_priority == 0 else ("列" if dir_priority == 1 else "对角线")
            )
            is_diag = "*" if -item[2] == 1 else " "
            pos = item[3]
            logger.info(
                f"  候选{idx+1}:({pos[0]+1},{pos[1]+1}) {is_diag} 最高分={max_score} 最高分方向={max_dir}"
            )
        logger.info(f"最终选择：({best_pos[0]+1},{best_pos[1]+1}) 最高分={best_score}")

        return best_pos

    def _check_victory(self, card_state_grid: List[List[int]]) -> bool:
        """胜利判定：仅统计紫色牌(1)数量,连续4个才胜利"""
        # 检查行
        for r in range(4):
            purple_count = sum(1 for col in range(4) if card_state_grid[r][col] == 1)
            if purple_count == 4:
                logger.info(f"检测到第{r+1}行4个紫色连成一线,胜利!")
                return True
        # 检查列
        for c in range(4):
            purple_count = sum(1 for row in range(4) if card_state_grid[row][c] == 1)
            if purple_count == 4:
                logger.info(f"检测到第{c+1}列4个紫色连成一线,胜利!")
                return True
        # 检查主对角线
        main_purple = sum(1 for i in range(4) if card_state_grid[i][i] == 1)
        if main_purple == 4:
            logger.info("检测到主对角线4个紫色连成一线,胜利!")
            return True
        # 检查副对角线
        sub_purple = sum(1 for i in range(4) if card_state_grid[i][3 - i] == 1)
        if sub_purple == 4:
            logger.info("检测到副对角线4个紫色连成一线,胜利!")
            return True
        return False

    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 开始检测翻牌游戏状态=====")

        # 步骤1：识别卡牌状态
        card_state_grid = []
        has_recognize_fail = False
        for row in range(4):
            row_state = []
            for col in range(4):
                roi = self.CARD_4X4_ROI[row][col]
                card_type = get_card_type(context, argv.image, roi)
                row_state.append(card_type)
                if card_type == 3:
                    has_recognize_fail = True
            card_state_grid.append(row_state)
        logger.info(f"当前卡牌状态网格：\n{card_state_grid}")

        # 步骤2：处理识别失败
        if has_recognize_fail:
            logger.info(f"检测到识别失败,点击提示ROI:{self.TIP_CLICK_ROI}")
            tip_box = Rect(*self.TIP_CLICK_ROI)
            return CustomRecognition.AnalyzeResult(
                box=tip_box,
                detail={"action": "click_tip", "tip_roi": self.TIP_CLICK_ROI},
            )

        # 步骤3：检查胜利
        if self._check_victory(card_state_grid):
            invalid_box = Rect(0, 0, 1, 1)
            return CustomRecognition.AnalyzeResult(
                box=invalid_box, detail={"has_valid_target": False, "is_win": True}
            )

        # 步骤4：提取橙色信息
        orange_info = self._get_orange_info(card_state_grid)
        logger.info(
            f"橙色牌信息：位置{[(x+1,y+1) for x,y in orange_info['orange_pos']]}，阻挡行{orange_info['orange_rows']},"
            f"阻挡列{orange_info['orange_cols']}，阻挡对角线{orange_info['orange_diags']}，双对角线橙色：{orange_info['is_both_diag_orange']}"
        )

        # 步骤5：初始状态选牌
        if self._is_initial_state(card_state_grid):
            best_pos = self._get_valid_initial_pos(card_state_grid, orange_info)
            best_roi = self.CARD_4X4_ROI[best_pos[0]][best_pos[1]]
            logger.info(
                f"初始状态选择翻牌位置：({best_pos[0]+1},{best_pos[1]+1}),ROI={best_roi}"
            )
            flip_box = Rect(*best_roi)
            return CustomRecognition.AnalyzeResult(
                box=flip_box,
                detail={
                    "has_valid_target": False,
                    "action": "flip_initial",
                    "flip_pos": (best_pos[0] + 1, best_pos[1] + 1),
                    "flip_roi": best_roi,
                },
            )

        # 步骤6：按单一方向最高分选最优生长位置
        best_growth_pos = self._get_best_growth_pos_by_score(
            card_state_grid, orange_info
        )
        if not best_growth_pos:
            logger.warning("无未翻牌可翻")
            invalid_box = Rect(0, 0, 1, 1)
            return CustomRecognition.AnalyzeResult(
                box=invalid_box,
                detail={"has_valid_target": False, "reason": "no_unflip_card"},
            )

        best_roi = self.CARD_4X4_ROI[best_growth_pos[0]][best_growth_pos[1]]
        logger.info(
            f"紫色生长选择翻牌位置：({best_growth_pos[0]+1},{best_growth_pos[1]+1}),ROI={best_roi}"
        )
        flip_box = Rect(*best_roi)
        return CustomRecognition.AnalyzeResult(
            box=flip_box,
            detail={
                "has_valid_target": False,
                "action": "flip_growth",
                "flip_pos": (best_growth_pos[0] + 1, best_growth_pos[1] + 1),
                "flip_roi": best_roi,
            },
        )


def get_token_count(context: Context, image: ndarray, roi: list[int]) -> int | None:
    """
    独立读取指定ROI的纯数字(调用custom_ocr)
    :param context: MAA上下文
    :param image: 屏幕图像
    :param roi: 识别区域 [x, y, w, h]
    :return: 解析后的整型数字,失败返回None
    """
    # 调用custom_ocr
    reco_detail = context.run_recognition(
        "custom_ocr", image, {"custom_ocr": {"roi": roi}}
    )

    if reco_detail is None or not reco_detail.hit:
        logger.warning(f"[find_bonds_without_enough_token] ROI{roi} 未识别到任何文本")
        return None

    # 提取并清洗识别文本（仅保留数字）
    source_text = str(reco_detail.best_result.text).strip()  # type: ignore
    logger.debug(
        f"[find_bonds_without_enough_token] ROI{roi} 原始识别文本：{source_text}"
    )

    # 正则提取纯数字（过滤所有非数字字符）
    num_match = re.search(r"\d+", source_text)
    if not num_match:
        logger.warning(
            f"[find_bonds_without_enough_token] ROI{roi} 未提取到有效数字，原始文本：{source_text}"
        )
        return None

    try:
        token_count = int(num_match.group())
        logger.info(
            f"[find_bonds_without_enough_token] ROI{roi} 解析到token数量:{token_count}"
        )
        return token_count
    except ValueError:
        logger.warning(
            f"[find_bonds_without_enough_token] ROI{roi} 数字转换失败，提取字符串：{num_match.group()}"
        )
        return None


@AgentServer.custom_recognition("find_bonds_without_enough_token")
class FindBondsWithoutEnoughToken(CustomRecognition):
    """
    固定读取ROI的纯数字
    数字 < 5 → 返回识别通过(非空box)
    数字 ≥ 5 或识别失败 → 返回识别未通过(空box)
    """

    TOKEN_CHECK_ROI = [846, 639, 111, 80]

    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行find_bonds_without_enough_token节点 =====")

        # 读取token数量
        token_count = get_token_count(context, argv.image, self.TOKEN_CHECK_ROI)

        # 逻辑1：识别失败 → 返回未通过（空box）
        if token_count is None:
            logger.warning(
                "[find_bonds_without_enough_token] token数量识别失败,返回未通过"
            )
            return CustomRecognition.AnalyzeResult(
                box=None, detail={"token_count": None, "passed": False}
            )

        # 逻辑2：数字 < 5 → 返回通过（非空box，用无效Rect表示）
        if token_count < 5:
            logger.info(
                f"[find_bonds_without_enough_token] token数量{token_count}<5,返回识别通过"
            )
            # 返回非空box表示节点识别通过
            pass_box = Rect(0, 0, 1, 1)
            return CustomRecognition.AnalyzeResult(
                box=pass_box, detail={"token_count": token_count, "passed": True}
            )

        # 逻辑3：数字 ≥ 5 → 返回未通过（空box）
        logger.info(
            f"[find_bonds_without_enough_token] token数量{token_count}≥5，返回识别未通过"
        )
        return CustomRecognition.AnalyzeResult(
            box=None, detail={"token_count": token_count, "passed": False}
        )


def get_flip_ticket_count(
    context: Context, image: ndarray, roi: list[int], text_modifier=lambda x: x
) -> int | None:
    """
    独立读取指定ROI的翻牌卷数量(调用custom_oc)，支持自定义文本修改
    :param context: MAA上下文
    :param image: 屏幕图像
    :param roi: 识别区域 [x, y, w, h]
    :param text_modifier: 文本修改函数，入参原始识别文本，返回修改后文本（用于去掉前缀/替换字符等）
    :return: 解析后的整型数字,失败返回None
    """

    reco_detail = context.run_recognition(
        "custom_ocr", image, {"custom_ocr": {"roi": roi}}
    )

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
        logger.warning(
            f"[get_flip_ticket_count] ROI{roi} 未提取到有效数字，修改后文本：{modified_text}"
        )
        return None

    # 数字转换（异常捕获）
    try:
        ticket_count = int(num_match.group())
        logger.info(f"[get_flip_ticket_count] ROI{roi} 解析到翻牌卷数量:{ticket_count}")
        return ticket_count
    except ValueError:
        logger.warning(
            f"[get_flip_ticket_count] ROI{roi} 数字转换失败，提取字符串：{num_match.group()}"
        )
        return None


@AgentServer.custom_recognition("FindAccessoryFlipTicket")
class FindAccessoryFlipTicket(CustomRecognition):
    """
    秘境饰品翻牌卷识别
    """

    # 饰品翻牌卷ROI
    ACCESSORY_TICKET_ROI = [550, 481, 171, 238]

    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行饰品翻牌卷识别 FindAccessoryFlipTicket =====")

        # 调用独立识别函数，传入ROI+自定义文本修改（lambda x: x[1:] if x else x是去掉第一个字符，无修改则改为lambda x:x）
        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.ACCESSORY_TICKET_ROI,
            text_modifier=lambda x: x,
        )

        # 逻辑1：识别失败 → 返回未通过（空box）
        if ticket_count is None:
            logger.warning(
                "[FindAccessoryFlipTicket] 饰品翻牌卷数量识别失败,返回未通过"
            )
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        # 逻辑2：数量>0 → 返回通过（非空无效Rect）
        if ticket_count > 0:
            logger.info(
                f"[FindAccessoryFlipTicket] 饰品翻牌卷数量{ticket_count}>0,返回识别通过"
            )
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        # 逻辑3：数量≤0 → 返回未通过（空box）
        logger.info(
            f"[FindAccessoryFlipTicket] 饰品翻牌卷数量{ticket_count}≤0,返回识别未通过"
        )
        return CustomRecognition.AnalyzeResult(box=None, detail={})


@AgentServer.custom_recognition("FindGearFlipTicket")
class FindGearFlipTicket(CustomRecognition):
    """
    忍具翻牌卷识别:和上面的饰品翻牌差不多
    """

    # 忍具翻牌卷ROI
    GEAR_TICKET_ROI = [436, 483, 138, 236]

    def analyze(
        self, context: Context, argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        logger.info("===== 执行忍具翻牌卷识别 FindGearFlipTicket =====")

        ticket_count = get_flip_ticket_count(
            context=context,
            image=argv.image,
            roi=self.GEAR_TICKET_ROI,
            text_modifier=lambda x: x,
        )

        if ticket_count is None:
            logger.warning("[FindGearFlipTicket] 忍具翻牌卷数量识别失败,返回未通过")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if ticket_count > 0:
            logger.info(
                f"[FindGearFlipTicket] 忍具翻牌卷数量{ticket_count}>0,返回识别通过"
            )
            return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={})

        logger.info(
            f"[FindGearFlipTicket] 忍具翻牌卷数量{ticket_count}≤0,返回识别未通过"
        )
        return CustomRecognition.AnalyzeResult(box=None, detail={})
