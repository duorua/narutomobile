from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JRecognitionType, JOCR
from utils.logger import logger


@AgentServer.custom_recognition("FindRewardsOfClub")
class FindToChallenge(CustomRecognition):
    """
    在俱乐部奖励列表中寻找第一个包含任务关键字的 OCR 结果
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        roi = [41, 478, 640, 242]
        tasks = [
            "今日角斗场胜利",
            "绑定手机号",
            "签到",
            "浏览",
            "点赞",
            "村口",
            "金币助手",
            "卷轴",
            "活动日历",
            "壁纸",
            "忍者",
            "他人主页",
            "游戏内",
        ]
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(roi=roi),
            argv.image,
        )

        if not detail or not detail.hit:
            logger.warning("[FindRewardsOfClub] 未识别到任何文字")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        # OCR 结果顺序没有阅读顺序保证，显式按屏幕坐标从上到下、从左到右检查。
        results = sorted(
            detail.filtered_results or [],
            key=lambda result: (result.box[1], result.box[0]) if result.box else (float("inf"), float("inf")),
        )
        for result in results:
            text = getattr(result, "text", "").strip()
            keyword = next((task for task in tasks if task in text), None)
            if keyword is None:
                continue
            if result.box is not None:
                logger.info(f"[FindRewardsOfClub] 找到任务: {text}")
                return self.find_claim_button(context, argv)

        logger.info("[FindRewardsOfClub] OCR结果中没有包含任务关键字的文本")
        return CustomRecognition.AnalyzeResult(box=None, detail={})

    def find_claim_button(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        # 保留原来的列表 ROI，并向上下各扩展 15 像素作为按钮识别区域。
        list_roi = [524, 458, 164, 262]
        target_roi = [list_roi[0], list_roi[1] - 15, list_roi[2], list_roi[3] + 30]
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(roi=target_roi),
            argv.image,
        )

        if not detail or not detail.hit:
            logger.debug("[FindRewardsOfClub] 未识别到该任务行的按钮文字")
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        button_results = sorted(
            detail.filtered_results or [],
            key=lambda result: (result.box[1], result.box[0]) if result.box else (float("inf"), float("inf")),
        )
        for result in button_results:
            text = getattr(result, "text", "").strip()
            if "已领取" in text:
                logger.info(f"[FindRewardsOfClub] 任务已领取: {text}")
                return CustomRecognition.AnalyzeResult(box=None, detail={"button_text": text})
            elif "去完成" in text:
                logger.info(f"[FindRewardsOfClub] 任务尚未完成: {text}")
                return CustomRecognition.AnalyzeResult(box=None, detail={"button_text": text})
            elif "领取" in text:
                logger.info(f"[FindRewardsOfClub] 找到领取按钮: {text}")
                return CustomRecognition.AnalyzeResult(
                    box=result.box,
                    detail={"button_text": text, "button_roi": target_roi},
                )

        logger.info("[FindRewardsOfClub] 未找到可领取按钮")
        return CustomRecognition.AnalyzeResult(box=None, detail={})
