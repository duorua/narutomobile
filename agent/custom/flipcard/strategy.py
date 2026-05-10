"""
FlipStrategy — 4x4 翻牌游戏的贪心选牌算法。

纯 Python 实现，不依赖 MAA 框架，可直接用于单元测试。

算法规则（与原 FlipCard 类完全一致）：
    1. 胜利判定：仅统计紫色牌数量，连续 4 个判定胜利。
    2. 初始状态：优先选橙色不在的对角线牌，双对角线橙色则选横竖无橙色牌。
    3. 紫色生长：
       - 按"单一方向（行/列/对角线）的最高紫色数"评分；
       - 同最高分下，优先选该方向内的位置（行 > 列 > 对角线）；
       - 有橙色的方向，紫色数直接计 0；
       - 同分数 + 同方向下，优先选对角线位置（双对角线橙色时忽略）。
"""

from __future__ import annotations

from utils.logger import logger

from .grid import GRID_SIZE, PURPLE, CardGrid, OrangeInfo


class FlipStrategy:
    """基于贪心算法的翻牌策略。

    提供两种选牌模式：

    * **初始选牌** (``_get_initial_move``)：网格中只有橙色牌被揭示时调用。
      策略优先在「与橙色牌无冲突的对角线」上落子；双对角线均被橙色阻挡时，
      退化为「选择不与任何橙色牌同行/同列的未翻牌」。
    * **生长选牌** (``_get_growth_move``)：中局阶段（已有紫色牌）调用。按
      下述评分规则选择最优位置。

    评分规则（与原 ``FlipCard`` god class 保持一致）:
        对每个未翻位置 ``(r, c)`` 独立计算三个方向得分：

        1. ``row_score`` = 该行已有紫色牌数。若第 ``r`` 行含橙色 → 0。
        2. ``col_score`` = 该列已有紫色牌数。若第 ``c`` 列含橙色 → 0。
        3. ``diag_score``：
              - 若 ``(r, c)`` 在主对角线且主对角线无橙色 →
                ``max(diag_score, 主对角线紫色数)``
              - 若 ``(r, c)`` 在副对角线且副对角线无橙色 →
                ``max(diag_score, 副对角线紫色数)``
              - 其余情况或对应对角线已被橙色污染 → 0。

        ``max_score = max(row, col, diag)``，``max_dir`` 在 ties 上按
        **行 > 列 > 对角线** 的顺序取最先达到 ``max_score`` 的方向。

    位置排序 key（按字典序升序排序取首个）:
        ``(-max_score, dir_priority, -is_diag, (r, c))``，其中：

        * ``-max_score`` → ``max_score`` 越大排越前；
        * ``dir_priority = 0/1/2`` for ``row/col/diag``；
        * ``is_diag = 1`` 当 ``(r, c)`` 在任一对角线 **且** 不处于「双对角
          线均被橙色阻挡」的情况下，否则 ``0``；对角线位置优先但双对角线
          阻挡时退化。
        * 最后按 ``(r, c)`` 字典序兜底（稳定性）。

    胜利判定:
        委托给 :meth:`CardGrid.check_victory`，**仅统计紫色牌**，
        4 个紫色连成一线即为胜利。橙色牌连线不会触发胜利。

    算法不持有任何状态，每次调用 ``get_next_move`` 都基于当前网格独立决策。
    """

    def get_next_move(self, grid: CardGrid) -> tuple[int, int] | None:
        """根据当前网格状态选择最优翻牌位置。

        自动判断是初始阶段还是生长阶段，并调用对应策略。

        Args:
            grid: 当前的 CardGrid 状态。

        Returns:
            (row, col) 元组，表示建议翻牌位置。
            如果没有可翻的牌则返回 None。
        """
        orange_info = grid.get_orange_info()

        if orange_info.is_both_diag_orange:
            logger.info("检测到双对角线都有橙色，忽略对角线优先级")

        if grid.is_initial_state():
            return self._get_initial_move(grid, orange_info)
        else:
            return self._get_growth_move(grid, orange_info)

    def _get_initial_move(
        self, grid: CardGrid, orange_info: OrangeInfo
    ) -> tuple[int, int] | None:
        """初始状态选最优翻牌位置。

        策略优先级：
        1. 双对角线橙色 → 选横竖均无橙色的未翻牌。
        2. 单对角线橙色 → 优先级排序：
           a) 不在橙色行/列 且 不在橙色对角线的对角线牌
           b) 不在橙色行/列的对角线牌
           c) 其他对角线牌
        3. 兜底 → 按行列序选第一张未翻牌。

        Args:
            grid: 当前网格状态。
            orange_info: 橙色牌分析信息。

        Returns:
            (row, col) 元组，或无未翻牌时返回 None。
        """
        all_unflip = grid.get_unflipped_positions()
        if not all_unflip:
            return None

        # 双对角线橙色 → 优先选横竖无橙色的未翻牌
        if orange_info.is_both_diag_orange:
            valid_unflip = [
                (r, c)
                for (r, c) in all_unflip
                if r not in orange_info.orange_rows
                and c not in orange_info.orange_cols
            ]
            if valid_unflip:
                logger.info(f"双对角线橙色，选横竖无橙色的未翻牌：{valid_unflip[0]}")
                return valid_unflip[0]
            return all_unflip[0]

        # 单对角线橙色 → 优先选另一对角线无橙色的牌
        diag_unflip = [pos for pos in all_unflip if pos in grid.ALL_DIAG]
        if not diag_unflip:
            return all_unflip[0]

        priority1: list[tuple[int, int]] = []  # 不在橙色行/列 + 不在橙色对角线
        priority2: list[tuple[int, int]] = []  # 不在橙色行/列
        priority3: list[tuple[int, int]] = []  # 其他对角线牌

        for r, c in diag_unflip:
            in_orange_row_col = (r in orange_info.orange_rows) or (
                c in orange_info.orange_cols
            )
            in_orange_diag = False
            if (r, c) in grid.MAIN_DIAG and "main" in orange_info.orange_diags:
                in_orange_diag = True
            if (r, c) in grid.SUB_DIAG and "sub" in orange_info.orange_diags:
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
        self,
        pos: tuple[int, int],
        grid: CardGrid,
        orange_info: OrangeInfo,
    ) -> dict[str, int | str]:
        """计算指定位置在行/列/对角线三个方向上的单独评分。

        评分规则：
        - 某方向有橙色 → 该方向得分为 0（不可能四连）。
        - 否则 → 该方向已有的紫色牌数量即为得分。

        Args:
            pos: 待评估的 (row, col) 位置。
            grid: 当前网格状态。
            orange_info: 橙色牌分析信息。

        Returns:
            字典，包含 row_score, col_score, diag_score, max_score, max_dir。
        """
        r, c = pos

        # 1. 行分数：有橙色则 0，否则该行紫色数
        row_score = 0
        if r not in orange_info.orange_rows:
            row_score = sum(
                1 for col in range(GRID_SIZE) if grid.grid[r][col] == PURPLE
            )

        # 2. 列分数：有橙色则 0，否则该列紫色数
        col_score = 0
        if c not in orange_info.orange_cols:
            col_score = sum(
                1 for row in range(GRID_SIZE) if grid.grid[row][c] == PURPLE
            )

        # 3. 对角线分数：有橙色则 0，否则所属对角线的紫色数
        diag_score = 0
        if (r, c) in grid.MAIN_DIAG and "main" not in orange_info.orange_diags:
            diag_score = grid.count_purple_in_line(grid.MAIN_DIAG)
        if (r, c) in grid.SUB_DIAG and "sub" not in orange_info.orange_diags:
            sub_score = grid.count_purple_in_line(grid.SUB_DIAG)
            diag_score = max(diag_score, sub_score)

        # 4. 单一方向最高分
        max_score = max(row_score, col_score, diag_score)

        return {
            "row_score": row_score,
            "col_score": col_score,
            "diag_score": diag_score,
            "max_score": max_score,
            "max_dir": (
                "row"
                if row_score == max_score
                else ("col" if col_score == max_score else "diag")
            ),
        }

    def _get_growth_move(
        self, grid: CardGrid, orange_info: OrangeInfo
    ) -> tuple[int, int] | None:
        """紫色生长阶段：按单一方向最高分选择最优翻牌位置。

        排序规则（多关键字）：
        1. 最高分降序（优先选紫色数最多的方向）。
        2. 最高分方向优先级：行 > 列 > 对角线。
        3. 对角线位置优先（双对角线橙色时忽略此规则）。
        4. 行列号升序（稳定性兜底）。

        Args:
            grid: 当前网格状态。
            orange_info: 橙色牌分析信息。

        Returns:
            (row, col) 元组，或无未翻牌时返回 None。
        """
        all_unflip = grid.get_unflipped_positions()
        if not all_unflip:
            return None

        pos_data: list[tuple[int, int, int, tuple[int, int]]] = []
        for pos in all_unflip:
            dir_scores = self._calc_single_dir_score(pos, grid, orange_info)
            max_score: int = dir_scores["max_score"]  # type: ignore
            max_dir = dir_scores["max_dir"]
            dir_priority = (
                0 if max_dir == "row" else (1 if max_dir == "col" else 2)
            )
            is_diag = (
                1
                if (pos in grid.ALL_DIAG and not orange_info.is_both_diag_orange)
                else 0
            )
            pos_data.append((-max_score, dir_priority, -is_diag, pos))

        pos_data.sort()
        best_pos = pos_data[0][3]
        best_score = -pos_data[0][0]

        # 日志输出前 3 名候选评分
        logger.info("未翻牌评分详情（优先同方向生长，行>列>对角线）：")
        for idx, item in enumerate(pos_data[:3]):
            score = -item[0]
            dp = item[1]
            dir_name = (
                "行" if dp == 0 else ("列" if dp == 1 else "对角线")
            )
            diag_marker = "*" if -item[2] == 1 else " "
            p = item[3]
            logger.info(
                f"  候选{idx + 1}:({p[0] + 1},{p[1] + 1}) {diag_marker} "
                f"最高分={score} 最高分方向={dir_name}"
            )
        logger.info(
            f"最终选择：({best_pos[0] + 1},{best_pos[1] + 1}) 最高分={best_score}"
        )

        return best_pos
