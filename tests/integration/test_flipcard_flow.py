"""
FlipCard 集成测试 — end-to-end flow through the MAA recognition hook.

Each test:
    1. Builds a "truth grid" (4x4 of 0=unflipped / 1=purple / 2=orange / 3=fail).
    2. Injects it through a ``FakeContext`` that answers ``run_recognition``
       in exactly the way the real MAA pipeline would for ``card_0`` /
       ``card_1`` / ``card_wait`` tasks.
    3. Invokes ``FlipCardRecognition().analyze(ctx, argv)``.
    4. Asserts on the resulting ``AnalyzeResult.box`` / ``detail``, proving
       that screenshot-->grid-->strategy-->click ROI is wired up correctly.

Covered scenarios:
    - Grid reconstruction (all-unflipped + mixed).
    - Recognition failure falls back to the tip-click ROI.
    - Victory detection for rows/cols/main-diag/sub-diag.
    - Initial-state selection (single-diag-orange and double-diag-orange).
    - Growth-phase scoring (row > col > diag tie-break, orange-zeroed row).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# conftest.py has already installed maa stubs and configured sys.path.
from custom.constants import CARD_4X4_ROI, FLIP_TIP_CLICK_ROI
from custom.flipcard.recognition import FlipCardRecognition


# ---------------------------------------------------------------------------
# FakeContext — drives get_card_type() via the MAA Context.run_recognition API
# ---------------------------------------------------------------------------
_ROI_TO_RC: dict[tuple[int, int, int, int], tuple[int, int]] = {
    tuple(CARD_4X4_ROI[r][c]): (r, c) for r in range(4) for c in range(4)
}

# Which MAA task should "hit" for each truth-grid cell value.
#   1 = purple  -> "card_0"
#   2 = orange  -> "card_1"
#   0 = unflip  -> "card_wait"
#   3 = fail    -> no task hits (all three return miss)
_HIT_TASK = {1: "card_0", 2: "card_1", 0: "card_wait"}


class FakeContext:
    """Answers ``run_recognition`` based on a caller-supplied 4x4 truth grid."""

    def __init__(self, truth_grid: list[list[int]]) -> None:
        self.truth_grid = truth_grid
        self.calls: list[tuple[str, tuple[int, int, int, int]]] = []

    def run_recognition(self, task_name: str, image, pipeline_override: dict):
        roi = tuple(pipeline_override[task_name]["roi"])
        self.calls.append((task_name, roi))
        rc = _ROI_TO_RC.get(roi)
        if rc is None:
            return MagicMock(hit=False)
        cell = self.truth_grid[rc[0]][rc[1]]
        return MagicMock(hit=_HIT_TASK.get(cell) == task_name)


def _argv(image=None):
    arg = MagicMock()
    arg.image = image if image is not None else MagicMock(name="screenshot")
    return arg


def _roi(r: int, c: int) -> list[int]:
    return CARD_4X4_ROI[r][c]


# ---------------------------------------------------------------------------
# 1. Grid reconstruction from mocked board recognition
# ---------------------------------------------------------------------------
class TestBoardRecognition:
    """Verify that ``analyze()`` correctly assembles the CardGrid from the
    per-cell MAA ``run_recognition`` calls."""

    def test_all_unflipped_triggers_initial_state_diagonal(self):
        ctx = FakeContext([[0] * 4 for _ in range(4)])
        result = FlipCardRecognition().analyze(ctx, _argv())

        # With no orange, _get_initial_move picks the first diagonal cell (0,0).
        assert result.detail["action"] == "flip_initial"
        assert result.detail["flip_pos"] == (1, 1)
        assert result.box.x == _roi(0, 0)[0]
        assert result.box.y == _roi(0, 0)[1]

    def test_every_cell_is_probed(self):
        """16 cells × up to 3 tasks. Unflipped cells need all 3 probes."""
        ctx = FakeContext([[0] * 4 for _ in range(4)])
        FlipCardRecognition().analyze(ctx, _argv())

        # All 16 ROIs must appear in the probe history.
        probed_rois = {roi for _, roi in ctx.calls}
        assert len(probed_rois) == 16
        # Each unflipped cell is probed by all three tasks.
        assert len(ctx.calls) == 16 * 3


# ---------------------------------------------------------------------------
# 2. Recognition-failure fallback
# ---------------------------------------------------------------------------
class TestRecognitionFailure:
    def test_single_fail_cell_triggers_tip_click(self):
        truth = [[3, 0, 0, 0]] + [[0] * 4 for _ in range(3)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())

        assert result.detail["action"] == "click_tip"
        assert result.detail["tip_roi"] == FLIP_TIP_CLICK_ROI
        assert result.box.x == FLIP_TIP_CLICK_ROI[0]
        assert result.box.y == FLIP_TIP_CLICK_ROI[1]


# ---------------------------------------------------------------------------
# 3. Victory detection — rows, cols, both diagonals
# ---------------------------------------------------------------------------
class TestVictory:
    def test_purple_row_is_win(self):
        truth = [[1, 1, 1, 1]] + [[0] * 4 for _ in range(3)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["is_win"] is True
        assert result.detail["has_valid_target"] is False

    def test_purple_column_is_win(self):
        truth = [[1, 0, 0, 0] for _ in range(4)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["is_win"] is True

    def test_main_diagonal_is_win(self):
        truth = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["is_win"] is True

    def test_sub_diagonal_is_win(self):
        truth = [
            [0, 0, 0, 1],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [1, 0, 0, 0],
        ]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["is_win"] is True

    def test_orange_line_is_not_a_win(self):
        """Only purple counts toward victory — 4 orange in a row must NOT win."""
        truth = [[2, 2, 2, 2]] + [[0] * 4 for _ in range(3)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        # Must not be victory. Should produce a valid flip action instead.
        assert "is_win" not in result.detail or result.detail["is_win"] is not True


# ---------------------------------------------------------------------------
# 4. Initial-state move selection
# ---------------------------------------------------------------------------
class TestInitialStateSelection:
    def test_single_diag_orange_picks_other_diag_priority1(self):
        # Orange at (0,0) blocks main-diag and row 0 and col 0.
        # Priority-1 sub-diag cells (not in orange row/col, not on blocked diag):
        #   (1,2) and (2,1). First in iteration order => (1,2).
        truth = [[2, 0, 0, 0]] + [[0] * 4 for _ in range(3)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["action"] == "flip_initial"
        assert result.detail["flip_pos"] == (2, 3)  # 1-indexed (1,2)

    def test_both_diagonals_orange_picks_non_orange_row_col(self):
        # Orange at (0,0) and (0,3) blocks both diagonals and row 0 + cols {0,3}.
        # First unflipped cell with r not in {0} and c not in {0,3} => (1,1).
        truth = [[2, 0, 0, 2]] + [[0] * 4 for _ in range(3)]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["action"] == "flip_initial"
        assert result.detail["flip_pos"] == (2, 2)  # 1-indexed (1,1)


# ---------------------------------------------------------------------------
# 5. Growth-phase scoring
# ---------------------------------------------------------------------------
class TestGrowthScoring:
    def test_completes_row_with_three_purple(self):
        # Row 0 has 3 purples; (0,3) is the only way to reach max_score=3.
        truth = [
            [1, 1, 1, 0],
            [1, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["action"] == "flip_growth"
        assert result.detail["flip_pos"] == (1, 4)  # 1-indexed (0,3)

    def test_orange_zeros_row_score_and_algorithm_skips_to_row_1(self):
        # Row 0 is poisoned by orange at (0,0) even though it still holds
        # 2 purples. Row 1 has 2 purples; (1,2) wins the tie because it
        # lies on the sub-diagonal (is_diag bonus).
        truth = [
            [2, 1, 1, 0],
            [1, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["action"] == "flip_growth"
        assert result.detail["flip_pos"] == (2, 3)  # 1-indexed (1,2)

    def test_row_direction_wins_tie_over_col(self):
        # (0,3) row_score=3 (row 0 has 3 purples), col_score=0.
        # (0,3) on sub-diag but diag_score=0.
        # Every other unflipped cell has max_score <= 2.
        # row > col ordering guarantees row-direction choice on ties.
        truth = [
            [1, 1, 1, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["flip_pos"] == (1, 4)

    @pytest.mark.parametrize(
        "truth, expected",
        [
            # Column with 3 purples, (3,0) completes it. No row/diag contender at 3.
            (
                [
                    [1, 0, 0, 0],
                    [1, 0, 0, 0],
                    [1, 0, 0, 0],
                    [0, 0, 0, 0],
                ],
                (4, 1),
            ),
            # Main-diagonal with 3 purples, (3,3) completes it.
            (
                [
                    [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 0],
                ],
                (4, 4),
            ),
        ],
    )
    def test_highest_single_direction_score_wins(self, truth, expected):
        result = FlipCardRecognition().analyze(FakeContext(truth), _argv())
        assert result.detail["flip_pos"] == expected
