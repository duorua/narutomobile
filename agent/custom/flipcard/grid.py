"""
CardGrid — 4x4 翻牌游戏的网格状态表示与查询。

纯 Python 实现，不依赖 MAA 框架，可直接用于单元测试。

卡牌类型编码:
    0 = 未翻开 (UNFLIPPED)
    1 = 紫色牌 (PURPLE)
    2 = 橙色牌 (ORANGE)
    3 = 识别失败 (RECOGNIZE_FAIL)
"""

from __future__ import annotations

# 卡牌类型常量
UNFLIPPED = 0
PURPLE = 1
ORANGE = 2
RECOGNIZE_FAIL = 3

# 网格尺寸
GRID_SIZE = 4


class OrangeInfo:
    """橙色牌分析结果，记录橙色牌对行/列/对角线的阻挡情况。

    Attributes:
        orange_pos: 所有橙色牌的 (row, col) 位置列表。
        orange_rows: 包含橙色牌的行号集合。
        orange_cols: 包含橙色牌的列号集合。
        orange_diags: 包含橙色牌的对角线名称集合 ("main" / "sub")。
        is_both_diag_orange: 主、副对角线是否都有橙色牌。
    """

    __slots__ = (
        "orange_pos",
        "orange_rows",
        "orange_cols",
        "orange_diags",
        "is_both_diag_orange",
    )

    def __init__(self) -> None:
        self.orange_pos: list[tuple[int, int]] = []
        self.orange_rows: set[int] = set()
        self.orange_cols: set[int] = set()
        self.orange_diags: set[str] = set()
        self.is_both_diag_orange: bool = False


class CardGrid:
    """4x4 翻牌游戏网格的状态管理与几何查询。

    封装了网格状态数据和所有不依赖 MAA 的纯逻辑查询，包括：
    - 对角线几何常量
    - 橙色牌信息提取
    - 初始状态判断
    - 胜利检测（4 个紫色连线）
    - 未翻牌位置查询

    坐标系约定:
        * **内部使用 0-indexed** ``(row, col)``，``row`` / ``col`` ∈ [0, 3]。
          所有常量 (``MAIN_DIAG`` / ``SUB_DIAG`` / ``_VICTORY_LINES``)、所有返
          回值 (``get_unflipped_positions`` / ``OrangeInfo.orange_pos`` 等) 以
          及所有方法入参都遵循 0-indexed。
        * **对外呈现使用 1-indexed**。
          上层 :class:`~.recognition.FlipCardRecognition` 在日志和 ``detail
          .flip_pos`` 中会把 ``(r, c)`` 显示为 ``(r + 1, c + 1)``，方便人类
          对照游戏界面的行/列。``check_victory`` 返回的 ``"第{r + 1}行"``
          同样是 1-indexed 的展示字符串。

    Args:
        grid: 4x4 整数二维列表，每个元素为卡牌类型编码 (0/1/2/3)。行列均
            为 0-indexed。

    Raises:
        ValueError: 网格不是 4x4 或包含无效卡牌类型（当前实现不显式校验，
            由调用方保证；预留给未来的严格模式）。
    """

    # 对角线几何常量
    MAIN_DIAG: list[tuple[int, int]] = [(0, 0), (1, 1), (2, 2), (3, 3)]
    SUB_DIAG: list[tuple[int, int]] = [(0, 3), (1, 2), (2, 1), (3, 0)]
    ALL_DIAG: list[tuple[int, int]] = MAIN_DIAG + SUB_DIAG

    # 所有可能的四连线（行×4 + 列×4 + 对角线×2 = 10 条）
    _VICTORY_LINES: list[list[tuple[int, int]]] = (
        [[(r, c) for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]  # 行
        + [[(r, c) for r in range(GRID_SIZE)] for c in range(GRID_SIZE)]  # 列
        + [MAIN_DIAG]  # 主对角线
        + [SUB_DIAG]  # 副对角线
    )

    def __init__(self, grid: list[list[int]]) -> None:
        self._grid = grid

    @property
    def grid(self) -> list[list[int]]:
        """原始 4x4 网格数据（只读访问）。"""
        return self._grid

    @property
    def has_recognition_failure(self) -> bool:
        """网格中是否存在识别失败的卡牌 (类型 == 3)。"""
        return any(
            self._grid[r][c] == RECOGNIZE_FAIL
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
        )

    def is_initial_state(self) -> bool:
        """判断是否为初始状态：除橙色牌外全部未翻开。

        Returns:
            True 表示网格中只有未翻开 (0) 和橙色 (2) 两种状态。
        """
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self._grid[r][c] not in (UNFLIPPED, ORANGE):
                    return False
        return True

    def check_victory(self) -> str | None:
        """检测是否有 4 个紫色牌连成一线。

        Returns:
            胜利线的描述字符串（如 "第1行"、"主对角线"），未胜利返回 None。
        """
        for r in range(GRID_SIZE):
            if all(self._grid[r][c] == PURPLE for c in range(GRID_SIZE)):
                return f"第{r + 1}行"
        for c in range(GRID_SIZE):
            if all(self._grid[r][c] == PURPLE for r in range(GRID_SIZE)):
                return f"第{c + 1}列"
        if all(self._grid[i][i] == PURPLE for i in range(GRID_SIZE)):
            return "主对角线"
        if all(self._grid[i][GRID_SIZE - 1 - i] == PURPLE for i in range(GRID_SIZE)):
            return "副对角线"
        return None

    def get_unflipped_positions(self) -> list[tuple[int, int]]:
        """获取所有未翻开卡牌的位置。

        Returns:
            (row, col) 元组列表，按行优先顺序排列。
        """
        return [
            (r, c)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self._grid[r][c] == UNFLIPPED
        ]

    def get_orange_info(self) -> OrangeInfo:
        """分析橙色牌的分布情况。

        扫描整个网格，记录橙色牌对行、列、对角线的阻挡信息。
        只要某条对角线上有 1 张橙色牌，该对角线就被标记为"有橙色"。

        Returns:
            OrangeInfo 实例，包含完整的橙色牌分布分析。
        """
        info = OrangeInfo()

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                if self._grid[row][col] != ORANGE:
                    continue

                info.orange_pos.append((row, col))
                info.orange_rows.add(row)
                info.orange_cols.add(col)

                if (row, col) in self.MAIN_DIAG:
                    info.orange_diags.add("main")
                if (row, col) in self.SUB_DIAG:
                    info.orange_diags.add("sub")

        info.is_both_diag_orange = (
            "main" in info.orange_diags and "sub" in info.orange_diags
        )

        return info

    def count_purple_in_line(self, positions: list[tuple[int, int]]) -> int:
        """统计指定位置列表中紫色牌的数量。

        Args:
            positions: 要检查的 (row, col) 位置列表。

        Returns:
            紫色牌 (类型 == 1) 的数量。
        """
        return sum(1 for r, c in positions if self._grid[r][c] == PURPLE)
