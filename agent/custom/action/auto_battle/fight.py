import threading
from collections.abc import Callable

from maa.context import Context
from utils.logger import logger


def fight(
    ctx: Context,
    should_stop: Callable[[Context], bool] | None = None,
    with_ultimate: bool = True,
):
    """
    同步函数，用于自动战斗。
    目前只写了连点器的，后续完善其他功能。
    """
    stop_event = threading.Event()
    result = []

    def click_loop(ctx: Context):
        try:
            while not stop_event.is_set():
                if with_ultimate:
                    # 这里后续看要不要改成手搓adb命令
                    detail = ctx.run_action("click_All_skill")
                else:
                    # 后面再写
                    logger.warning("with_ultimate is False, not implemented")
                    stop_event.set()
                    result.append(False)
                    return

                if (not detail) or (not detail.success):
                    stop_event.set()
                    logger.info("click_loop stop by not detail or not detail.success")
                    result.append(False)
                    return
            logger.info("click_loop stop")
            result.append(True)
        except Exception as e:
            logger.error(f"click_loop error: {e}")
            stop_event.set()
            result.append(False)

    def check_loop(ctx: Context):
        try:
            while not stop_event.is_set():
                ctx.tasker.controller.post_screencap().wait()
                if should_stop and should_stop(ctx):
                    stop_event.set()
                    logger.info("check_loop stop by should_stop")
                    result.append(True)
                    return
                if ctx.tasker.stopping:
                    stop_event.set()
                    logger.info("check_loop stop by tasker.stopping")
                    result.append(False)
                    return

            result.append(False)
            logger.error("check_loop stop by unknown reason")

        except Exception as e:
            logger.error(f"check_loop error: {e}")
            stop_event.set()
            result.append(False)

    click_thread = threading.Thread(target=click_loop, args=(ctx,), name="click_loop")
    check_thread = threading.Thread(target=check_loop, args=(ctx,), name="check_loop")

    click_thread.start()
    check_thread.start()

    click_thread.join()
    check_thread.join()

    return all(result)
