import time

import cv2
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.define import Rect
from utils import resource_base
from utils.logger import logger

from ...custom_cv import template_match
from .fight import fight


# 画饼
@AgentServer.custom_action("ArenaFight")
class ArenaFight(CustomAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.miss_time = 0

        emoji_template_path = resource_base / "image" / "Weekly_win" / "battle_emoji.png"
        if not emoji_template_path.exists():
            raise FileNotFoundError(f"emoji_template not found:{emoji_template_path}")
        self.emoji_template = cv2.imread(emoji_template_path)

        winner_template_path = resource_base / "image" / "Weekly_win" / "winner.png"
        if not winner_template_path.exists():
            raise FileNotFoundError(f"winner_template not found:{winner_template_path}")
        self.winner_template = cv2.imread(winner_template_path)

    def should_stop(self, ctx: Context) -> bool:
        # 战斗表情是否可见
        score, _ = template_match(
            ctx.tasker.controller.cached_image,
            template=self.emoji_template,  # type: ignore
            roi=Rect(0, 224, 127, 154),
            green_mask=True,
        )
        if score < 0.8:
            logger.info("fight emoji img not found")
            self.miss_time += 1
            time.sleep(0.05)
        else:
            self.miss_time = 0

        if self.miss_time >= 3:
            return True

        # 胜者出现
        score, _ = template_match(
            ctx.tasker.controller.cached_image,
            template=self.winner_template,  # type: ignore
            roi=Rect(412, 427, 239, 177),
        )
        if score > 0.7:
            logger.info("winner img found")
            return True

        return False

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        result = fight(context, self.should_stop)
        return CustomAction.RunResult(success=result)
