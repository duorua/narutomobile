import json
from time import sleep
from typing import Optional, Tuple

from maa.agent.agent_server import AgentServer, TaskDetail
from maa.custom_action import CustomAction
from maa.context import Context
from maa.define import RectType

from utils.logger import logger
from utils.counter import counter
from .utils import (
    fast_ocr,
    fast_swipe,
    click,
    save_screenshot,
    validate_config,
    validate_mfa,
    wait_for_freezes,
)


@AgentServer.custom_action("StopTaskList")
class StopTaskList(CustomAction):
    """
    停止当前任务以及后续任务列表
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        context.tasker.post_stop()
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("Screenshot")
class Screenshot(CustomAction):
    """
    自定义截图动作，保存当前屏幕截图到指定目录。

    参数格式:
    {
        "save_dir": "保存截图的目录路径"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        save_screenshot(context)
        task_detail: TaskDetail = context.tasker.get_task_detail(
            argv.task_detail.task_id
        )  # type: ignore
        logger.debug(
            f"task_id: {task_detail.task_id}, task_entry: {task_detail.entry}, status: {task_detail.status._status}"
        )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("RetryFailed")
class RetryFaild(CustomAction):
    """
    重试失败
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        save_screenshot(context)
        validate_config(context)
        validate_mfa(context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("GoIntoEntry")
class GoIntoEntry(CustomAction):
    """
    从主界面获取功能入口
    参数:
    {
        "template": "功能入口的匹配模板"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        target = json.loads(argv.custom_action_param).get("template", "")
        if not isinstance(target, str) and not isinstance(target, list):
            logger.error(f"目标格式错误: {target}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)
        # 检查目标是否为空字符串或空列表
        if (isinstance(target, str) and not target.strip()) or (
            isinstance(target, list) and len(target) == 0
        ):
            logger.error(f"目标为空: {target}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)

        found, box = self.rec_entry(context, target)
        if found and box is not None:
            logger.info("识别到功能入口")
            click(context, *box)
            return CustomAction.RunResult(success=True)

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        # 右滑两次
        for i in range(2):
            logger.info(f"右滑第{i + 1}次")
            context.run_task("main_screen_swipe_to_right")
            context.tasker.controller.post_screencap().wait()
            found, box = self.rec_entry(context, target)
            if found and box is not None:
                logger.info("识别到功能入口")
                click(context, *box)
                return CustomAction.RunResult(success=True)
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

        # 左滑两次
        for i in range(2):
            logger.info(f"左滑第{i + 1}次")
            context.run_task("main_screen_swipe_to_left")
            context.tasker.controller.post_screencap().wait()
            found, box = self.rec_entry(context, target)
            if found and box is not None:
                logger.info("识别到功能入口")
                click(context, *box)
                return CustomAction.RunResult(success=True)
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

        logger.error("获取功能入口失败")
        return CustomAction.RunResult(success=False)

    def rec_entry(
        self, context: Context, template: str | list[str]
    ) -> Tuple[bool, Optional[RectType]]:
        reco_detail = context.run_recognition(
            "click_entry",
            context.tasker.controller.cached_image,
            {
                "click_entry": {
                    "recognition": {
                        "param": {
                            "template": template,
                        }
                    }
                },
            },
        )
        if reco_detail is None or not reco_detail.hit:
            logger.info("未识别到功能入口")
            return False, None

        if reco_detail.best_result is None:
            logger.warning("识别到功能入口但解析失败(best_result为空)")
            return False, None

        return True, reco_detail.best_result.box  # type: ignore


@AgentServer.custom_action("GoIntoEntryByGuide")
class GoIntoEntryByGuide(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        enter_name = json.loads(argv.custom_action_param).get("entry_name", "")
        if enter_name == "":
            logger.error("功能入口名称不能为空!")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)

        if not isinstance(enter_name, str) and not isinstance(enter_name, list):
            logger.error(f"输入错误: {enter_name}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)
        if isinstance(enter_name, str):
            enter_name = [enter_name]

        start = [0, 0]
        end = [0, 0]
        list_roi = (26, 60, 404, 616)

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        box = fast_ocr(context=context, expected=["回流"], roi=(0, 0, 195, 285))
        if box is None:
            logger.debug("该账号不为回归账号")
            start = [70, 500]
            end = [70, 200]
        else:
            logger.debug("该账号为回归账号")
            start = [300, 500]
            end = [300, 200]
            box = fast_ocr(context, expected=["忍界指引"], roi=(6, 886, 249, 173))
            if box is None:
                return CustomAction.RunResult(success=False)

            click(context, *box)

        wait_for_freezes(context, 300)
        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        # 如果等级较低还有东西没解锁就会聚焦到这里
        # 此时需要先划到最顶上
        logger.info("滑动到最顶端")
        for _ in range(10):
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

            if fast_ocr(
                context,
                expected=["天赋"] + enter_name,
                roi=list_roi,
                absolutely=True,
            ):
                break

            fast_swipe(
                context,
                start_x=end[0],
                start_y=end[1],
                end_x=start[0],
                end_y=start[1],
                end_hold=False,
            )

        max_sweep_attempts = 20
        box = None
        logger.info(f"开始查找功能入口: {enter_name}")
        for _ in range(max_sweep_attempts):
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

            box = fast_ocr(context, expected=enter_name, roi=list_roi, absolutely=True)
            if box:
                logger.debug(f"识别到功能入口: {enter_name}")
                break

            logger.debug("未识别到功能入口，滑动页面")
            fast_swipe(
                context,
                start_x=start[0],
                start_y=start[1],
                end_x=end[0],
                end_y=end[1],
            )

        if box is None:
            return CustomAction.RunResult(False)

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        click(context, *box)
        sleep(0.5)

        box = fast_ocr(context, ["前往"], (834, 539, 287, 149))
        if box is None:
            return CustomAction.RunResult(False)
        else:
            click(context, *box)
            return CustomAction.RunResult(True)


@AgentServer.custom_action("CounterIncrement")
class CounterIncrement(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        task_id = argv.task_detail.task_id
        counter.increment(task_id)
        return CustomAction.RunResult(success=True)
