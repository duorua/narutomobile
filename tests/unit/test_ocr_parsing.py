"""OCR 文本解析逻辑的单元测试（纯函数，无需 MAA 设备）"""

# conftest.py 已处理 sys.path 和外部依赖 mock
import pytest

from custom.reco import correct_senryoku_text


class TestCorrectSenryokuText:
    """战力文本解析测试"""

    def test_plain_number(self):
        assert correct_senryoku_text("12345") == 12345

    def test_wan_suffix(self):
        """'万' 后缀应乘以 10000"""
        assert correct_senryoku_text("5万") == 50000

    def test_wan_with_digits(self):
        assert correct_senryoku_text("12万") == 120000

    def test_single_digit(self):
        assert correct_senryoku_text("1") == 1

    def test_zero(self):
        assert correct_senryoku_text("0") == 0

    def test_non_numeric_returns_none(self):
        assert correct_senryoku_text("abc") is None

    def test_empty_string_returns_none(self):
        assert correct_senryoku_text("") is None

    def test_mixed_text_returns_none(self):
        assert correct_senryoku_text("12ab34") is None

    def test_wan_only_returns_zero(self):
        """只有 '万' 没有数字前缀 → 空前缀拼接'0000' → 0"""
        assert correct_senryoku_text("万") == 0

    def test_large_number(self):
        assert correct_senryoku_text("999999") == 999999

    def test_wan_with_zero(self):
        assert correct_senryoku_text("0万") == 0


class TestConstantsIntegrity:
    """常量模块完整性测试"""

    def test_card_4x4_roi_shape(self):
        from custom.constants import CARD_4X4_ROI

        assert len(CARD_4X4_ROI) == 4, "应有 4 行"
        for row in CARD_4X4_ROI:
            assert len(row) == 4, "每行应有 4 列"
            for roi in row:
                assert len(roi) == 4, "每个 ROI 应有 4 个值 [x, y, w, h]"
                assert all(isinstance(v, int) for v in roi)

    def test_challenge_button_targets_count(self):
        from custom.constants import CHALLENGE_BUTTON_TARGETS

        assert len(CHALLENGE_BUTTON_TARGETS) == 4

    def test_flower_config_count(self):
        from custom.constants import FLOWER_CONFIG

        assert len(FLOWER_CONFIG) == 5
        for seed_roi, btn_roi in FLOWER_CONFIG:
            assert len(seed_roi) == 4
            assert len(btn_roi) == 4

    def test_thresholds_positive(self):
        from custom.constants import (
            FLOWER_SEED_THRESHOLD,
            BONDS_TOKEN_THRESHOLD,
            UNCHALLENGEABLE_SENRYOKU,
        )

        assert FLOWER_SEED_THRESHOLD > 0
        assert BONDS_TOKEN_THRESHOLD > 0
        assert UNCHALLENGEABLE_SENRYOKU > 0
