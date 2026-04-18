import json

from maa.agent.agent_server import AgentServer, TaskDetail
from maa.context import Context
from maa.custom_action import CustomAction
from maa.define import RectType
from utils.counter import counter
from utils.logger import logger
from utils.profiler import profiled

from .constants import (
    GUIDE_DEFAULT_LIST_ROI,
    GUIDE_GO_BUTTON_ROI,
    GUIDE_NINJA_GUIDE_BTN_ROI,
    GUIDE_NORMAL_LIST_ROI,
    GUIDE_NORMAL_SCROLL_END,
    GUIDE_NORMAL_SCROLL_START,
    GUIDE_RETURN_LIST_ROI,
    GUIDE_RETURN_SCROLL_END,
    GUIDE_RETURN_SCROLL_START,
    MAX_SCROLL_TO_TOP_RETRIES,
    MAX_SWEEP_ATTEMPTS,
    RETURN_ACCOUNT_CHECK_ROI,
)
from .utils import (
    check_resolution,
    click,
    fast_ocr,
    nonlinear_swipe,
    save_screenshot,
    validate_config,
    validate_mfa,
    wait_for_freezes,
    wait_until_visible,
)


@AgentServer.custom_action("StopTaskList")
class StopTaskList(CustomAction):
    """停止当前任务及后续任务列表。

    MAA 管线 `CustomAction` 注册名: ``"StopTaskList"``。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """调用 ``tasker.post_stop()`` 停止整个任务队列。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``，此 action 不使用其字段。

        Returns:
            ``CustomAction.RunResult(success=False)`` —— 故意返回失败以
            中断 MAA 的后续流程（MAA 依此判定"任务链断开"）。
        """
        context.tasker.post_stop()
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("Screenshot")
class Screenshot(CustomAction):
    """自定义截图动作，保存当前屏幕截图到日志目录。

    MAA 管线 `CustomAction` 注册名: ``"Screenshot"``。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """保存当前屏幕截图，并记录当前任务的调试信息。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``；``argv.task_detail.task_id`` 用于
                查询本次截图对应的任务详情。

        Returns:
            ``CustomAction.RunResult(success=True)``。
        """
        save_screenshot(context)
        task_detail: TaskDetail = context.tasker.get_task_detail(
            argv.task_detail.task_id
        )
        logger.opt(lazy=True).debug(
            "task_id: {tid}, task_entry: {te}, status: {ts}",
            tid=lambda: task_detail.task_id,
            te=lambda: task_detail.entry,
            ts=lambda: task_detail.status._status,
        )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("RetryFailed")
class RetryFaild(CustomAction):
    """在任务失败后执行的诊断收集动作。

    MAA 管线 `CustomAction` 注册名: ``"RetryFailed"``。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """失败重试前的诊断信息收集。

        依次执行：分辨率校验 → 保存失败截图 → 校验 MFA 接口配置 →
        校验 MFA 全局设置。这些步骤帮助定位失败原因（非 16:9 分辨率、
        配置遗漏等）。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``，此 action 不使用其字段。

        Returns:
            ``CustomAction.RunResult(success=True)`` —— 诊断本身总是成功。
        """
        check_resolution(context)
        save_screenshot(context)
        validate_config(context)
        validate_mfa(context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("GoIntoEntry")
class GoIntoEntry(CustomAction):
    """从主界面（忍界页面）查找并点击指定功能入口。

    在当前视口查找失败时，先右滑 2 次扫描右侧区域，再左滑 2 次扫描
    左侧区域；任一阶段命中即点击并返回成功。

    MAA 管线 `CustomAction` 注册名: ``"GoIntoEntry"``。

    Expected ``custom_action_param``:
        ``{"template": "<模板文件名或列表>"}``
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """扫描主界面寻找目标模板并点击。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``；从 ``argv.custom_action_param``
                (JSON 字符串) 读取 ``template`` 字段。

        Returns:
            * 模板匹配成功 → ``RunResult(success=True)``（已完成点击）。
            * ``template`` 字段缺失/格式错误 → 停止 tasker 并
              ``RunResult(success=False)``。
            * 四次滑动后仍未命中 / 用户主动停止任务 →
              ``RunResult(success=False)``。
        """
        target = json.loads(argv.custom_action_param).get("template", "")
        if not isinstance(target, str) and not isinstance(target, list):
            logger.error(f"目标格式错误: {target}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)
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
    ) -> tuple[bool, RectType | None]:
        """对当前缓存截图运行模板匹配，查找功能入口图标位置。

        Args:
            context: MAA 运行时上下文（提供 ``cached_image``）。
            template: 单个模板文件名或模板文件名列表。

        Returns:
            ``(found, box)`` 元组：

            * 命中 → ``(True, Rect)``；
            * 未命中或 ``best_result`` 解析失败 → ``(False, None)``。
        """
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

        return True, reco_detail.best_result.box


@AgentServer.custom_action("GoIntoEntryByGuide")
class GoIntoEntryByGuide(CustomAction):
    """通过"忍界指引"滚动列表进入指定功能，兼容回流账号与普通账号。

    MAA 管线 `CustomAction` 注册名: ``"GoIntoEntryByGuide"``。

    流程：

        1. 通过 OCR 判定当前账号类型（存在"回流"字样 → 回流账号）。
        2. 根据账号类型选择对应的滚动起止坐标与列表 ROI。
        3. 滚动到列表顶部（识别"天赋"作为顶部锚点），最多 ``MAX_SCROLL_TO_TOP_RETRIES`` 次。
        4. 逐屏向下滚动寻找目标入口名，最多 ``MAX_SWEEP_ATTEMPTS`` 次。
        5. 命中后点击，再通过 :func:`wait_until_visible` 自适应等待"前往"按钮。

    Expected ``custom_action_param``:
        ``{"entry_name": "<功能名>"}`` 或 ``{"entry_name": ["名A", "名B"]}``。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """按上述流程进入忍界指引中指定的功能入口。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``；从 ``argv.custom_action_param``
                (JSON 字符串) 读取 ``entry_name`` 字段。

        Returns:
            * 全流程成功 → ``RunResult(success=True)``（已点击"前往"）。
            * ``entry_name`` 为空或格式错误 → 停止 tasker 并返回
              ``RunResult(success=False)``。
            * 滚动到顶失败 / 未找到目标入口 / 等待"前往"超时 / 用户
              主动停止 → ``RunResult(success=False)``。
        """
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
        list_roi = GUIDE_DEFAULT_LIST_ROI

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        box = fast_ocr(context=context, expected=["回流"], roi=RETURN_ACCOUNT_CHECK_ROI)
        if box is None:
            logger.debug("该账号不为回归账号")
            start = GUIDE_NORMAL_SCROLL_START
            end = GUIDE_NORMAL_SCROLL_END
            list_roi = GUIDE_NORMAL_LIST_ROI
        else:
            logger.debug("该账号为回归账号")
            start = GUIDE_RETURN_SCROLL_START
            end = GUIDE_RETURN_SCROLL_END
            list_roi = GUIDE_RETURN_LIST_ROI
            box = fast_ocr(context, expected=["忍界指引"], roi=GUIDE_NINJA_GUIDE_BTN_ROI)
            if box is None:
                return CustomAction.RunResult(success=False)

            click(context, *box)

        wait_for_freezes(context, 300)
        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        # 低等级账号可能聚焦到列表中部（有未解锁项），先滚到顶部作为搜索起点。
        logger.info("滑动到最顶端")
        reached_top = False
        for attempt in range(MAX_SCROLL_TO_TOP_RETRIES):
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

            if fast_ocr(
                context,
                expected=["天赋"],
                roi=list_roi,
                absolutely=True,
            ):
                reached_top = True
                break

            nonlinear_swipe(
                context,
                start_x=end[0],
                start_y=end[1],
                end_x=start[0],
                end_y=start[1],
                end_hold=False,
            )

        if not reached_top:
            logger.error(f"滑动到顶端失败，已尝试 {MAX_SCROLL_TO_TOP_RETRIES} 次")
            return CustomAction.RunResult(success=False)

        max_sweep_attempts = MAX_SWEEP_ATTEMPTS
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
            nonlinear_swipe(
                context,
                start_x=start[0],
                start_y=start[1],
                end_x=end[0],
                end_y=end[1],
            )

        if box is None:
            return CustomAction.RunResult(success=False)

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        click(context, *box)

        # 自适应等待替代固定 sleep：典型耗时 150–300ms，上限 2s。
        box = wait_until_visible(
            context,
            expected=["前往"],
            roi=GUIDE_GO_BUTTON_ROI,
            timeout_s=2.0,
            interval_s=0.15,
            label="前往按钮",
        )
        if box is None:
            return CustomAction.RunResult(success=False)
        else:
            click(context, *box)
            return CustomAction.RunResult(success=True)


@AgentServer.custom_action("CounterIncrement")
class CounterIncrement(CustomAction):
    """按 ``task_id`` 给全局计数器加 1。

    MAA 管线 `CustomAction` 注册名: ``"CounterIncrement"``。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """为当前任务 ``task_id`` 对应的计数器加 1。

        Args:
            context: MAA 运行时上下文（未使用）。
            argv: MAA 传入的 ``RunArg``，使用 ``argv.task_detail.task_id``
                作为计数器键。

        Returns:
            ``CustomAction.RunResult(success=True)``。
        """
        task_id = argv.task_detail.task_id
        counter.increment(task_id)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("NonlinearSwipe")
class NonlinearSwipe(CustomAction):
    """对外暴露非线性滑动（模拟人手滑动轨迹）以反检测。

    MAA 管线 `CustomAction` 注册名: ``"NonlinearSwipe"``。

    Expected ``custom_action_param``:
        JSON 对象，覆盖以下任一默认参数：
        ``start_x`` / ``start_y`` / ``end_x`` / ``end_y``（起止坐标）、
        ``duration`` (ms)、``end_hold`` (bool)、``after_swipe_delay`` (ms)、
        ``steps`` (分段数)。
    """

    @profiled
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """按 JSON 参数执行一次非线性滑动。

        Args:
            context: MAA 运行时上下文。
            argv: MAA 传入的 ``RunArg``；从 ``argv.custom_action_param``
                (JSON 字符串) 读取可选的滑动参数。缺省字段使用内置默认值。

        Returns:
            * 滑动成功 → ``RunResult(success=True)``；
            * 参数解析或底层调用抛出异常 → 记录 error 日志并返回
              ``RunResult(success=False)``（捕获所有 ``Exception``）。
        """
        swipe_params = {
            "start_x": 0,
            "start_y": 0,
            "end_x": 0,
            "end_y": 0,
            "end_hold": False,
            "duration": 150,
            "after_swipe_delay": 300,
            "steps": 5,
        }

        try:
            if argv.custom_action_param:
                swipe_params.update(json.loads(argv.custom_action_param))

            nonlinear_swipe(
                context=context,
                start_x=int(swipe_params["start_x"]),
                start_y=int(swipe_params["start_y"]),
                end_x=int(swipe_params["end_x"]),
                end_y=int(swipe_params["end_y"]),
                duration=int(swipe_params["duration"]),
                end_hold=bool(swipe_params["end_hold"]),
                after_swipe_delay=int(swipe_params["after_swipe_delay"]),
                steps=int(swipe_params["steps"]),
            )
            return CustomAction.RunResult(success=True)

        except Exception as e:
            logger.error(f"非线性滑动执行失败: {str(e)}")
            return CustomAction.RunResult(success=False)
