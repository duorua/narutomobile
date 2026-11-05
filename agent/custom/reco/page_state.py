"""统一的页面状态识别（PageState）——任务入口路由的公共探针。

设计目标
--------
pipeline 里原来的入口是「先回主界面，再从主界面进功能」，于是像
`get_copper` / `mission_office` / `rich_room` 这些任务，即使玩家已经停在
目标页面，也要先绕一圈回大厅再点进去，浪费 5~15 秒，还可能被弹窗卡住。

本模块把「判断当前在哪个页面」收敛成**一张表 + 一个识别器**：

    PAGE_REGISTRY  页面 ID -> 识别规则（复用现有模板图，不新增素材）
    PageState      按 allowed 列表依次探测，命中即返回成功

pipeline 侧的统一用法（探针节点）：

    "<任务>_entry_route": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "PageState",
                "custom_recognition_param": {"allowed": ["copper_page"]}
            }
        },
        "action": "DoNothing",
        "next": ["<该任务的正文首节点>"]
    }

并把 "<任务>_entry_route" 放到任务 entry 的 next **最前面**：

    命中 -> 直接进正文（不回主界面）
    不命中 -> 父节点 next 继续，走原来的 ninja_guide / back_main_screen_before_task

因为 MaaFW 的 next 是「按顺序试，识别不到就换下一个候选」，所以探针失败
不会中断流程，只是回到原路径 —— 这也是本方案对现有任务零风险的原因。

新增页面：在 PAGE_REGISTRY 里加一行（page_id -> 规则），
新增任务：在 merged.json 加一个上面的探针节点 + entry.next 最前面加一行。
"""

import json

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.define import Rect
from utils.logger import logger

# 探针专用节点名：只作为 run_recognition 的 override 容器，不被任何 next 引用
PROBE_NODE = "page_state_probe"

# ---------------------------------------------------------------------------
# 页面注册表
# ---------------------------------------------------------------------------
# 规则字段直接用 merged.json 里的平铺写法（recognition / template / roi / ...），
# run_recognition 的 override 是节点字段级合并，所以这里的每一项都能原样套用。
# 所有 template 都取自 resource/base/image 下**已被现有节点验证过**的素材，
# roi / threshold / method 也沿用对应节点的取值，尽量不引入新的误判。
PAGE_REGISTRY: dict[str, dict] = {
    # 主界面（同 check_main_screen）
    "main": {
        "recognition": "TemplateMatch",
        "template": ["Startup/main_green_masked.png"],
        "green_mask": True,
        "method": 10001,
        "threshold": 0.9,
    },
    # 秘境房间 / 准备页（同 secret_realm_entry_in_room）
    "secret_realm_room": {
        "recognition": "Or",
        "any_of": [
            {"sub_name": "fight", "recognition": "TemplateMatch", "template": "Secret_realm/fight.png"},
            {"sub_name": "wait", "recognition": "TemplateMatch", "template": "Secret_realm/wait.png"},
        ],
    },
    # 秘境战斗中（同 secret_realm_in_fight 的左上角标记）
    "secret_realm_fight": {
        "recognition": "TemplateMatch",
        "template": "SharedNode/dameeji_ratio.png",
    },
    # 秘境结算（同 secret_realm_win）
    "secret_realm_result": {
        "recognition": "TemplateMatch",
        "template": "Secret_realm/back_to_main_page.png",
    },
    # 决斗场大厅（同 go_to_war 的「前往战斗」按钮）
    "duel_lobby": {
        "recognition": "TemplateMatch",
        "roi": [1069, 506, 190, 190],
        "template": "Weekly_win/go_to_war.png",
    },
    # 决斗场战斗中（同 weekly_win_match_fighting）
    "duel_fight": {
        "recognition": "TemplateMatch",
        "roi": [0, 224, 127, 154],
        "template": "Weekly_win/battle_emoji.png",
        "green_mask": True,
    },
    # 丰饶之间页面（同 challenge_rich_room 的「出战」按钮）
    "rich_room_page": {
        "recognition": "TemplateMatch",
        "roi": [447, 568, 171, 144],
        "template": "Rich_room/fight.png",
        "threshold": 0.9,
        "method": 10001,
    },
    # 任务集会所页面（同 check_in_mission_office）
    "mission_office_page": {
        "recognition": "TemplateMatch",
        "roi": [1130, 0, 149, 204],
        "template": "Mission_office/in_mission_office.png",
    },
    # 招财页面（同 try_get_copper_by_roll 的招财按钮）
    "copper_page": {
        "recognition": "TemplateMatch",
        "roi": [1032, 518, 150, 93],
        "template": "Get_copper/get_roll.png",
        "threshold": 0.95,
        "method": 10001,
    },
    # 奖励中心页面（同 get_copper_in_center_enter）
    "award_center_page": {
        "recognition": "TemplateMatch",
        "roi": [37, 172, 130, 47],
        "template": "SharedNode/check_in_daily_award.png",
    },
    # 通用战斗中（自动战斗标记，很多玩法的 _in_fight 都用它）
    "battle_common": {
        "recognition": "TemplateMatch",
        "roi": [1120, 0, 160, 127],
        "template": "Advanture/stop_button.png",
        "green_mask": True,
    },
}


@AgentServer.custom_recognition("PageState")
class PageState(CustomRecognition):
    """判断当前页面是否属于 allowed 列表。

    参数（custom_recognition_param）::

        {"allowed": ["copper_page"]}                 # 命中即成功
        {"allowed": ["duel_lobby", "duel_fight"]}    # 任一命中即成功
        {"page": "copper_page"}                      # allowed 的别名
        {"quiet": true}                              # 不打印未命中日志

    返回值：命中 -> box=Rect(0,0,1,1)、detail={"page": page_id}
            未命中 -> box=None、detail={"page": None}
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        try:
            param = json.loads(argv.custom_recognition_param) if argv.custom_recognition_param else {}
        except json.JSONDecodeError:
            logger.error(f"[PageState] 参数不是合法 JSON: {argv.custom_recognition_param}")
            return CustomRecognition.AnalyzeResult(box=None, detail={"page": None})

        if not isinstance(param, dict):
            param = {}

        allowed = param.get("allowed") or param.get("page") or []
        if isinstance(allowed, str):
            allowed = [allowed]
        if not isinstance(allowed, list) or not allowed:
            logger.error(f"[PageState] 未提供 allowed 列表，节点={argv.node_name}")
            return CustomRecognition.AnalyzeResult(box=None, detail={"page": None})

        quiet = bool(param.get("quiet", False))

        for page_id in allowed:
            spec = PAGE_REGISTRY.get(str(page_id))
            if spec is None:
                logger.error(f"[PageState] 未注册的页面 ID: {page_id}（可用: {sorted(PAGE_REGISTRY)}）")
                continue

            detail = context.run_recognition(PROBE_NODE, argv.image, {PROBE_NODE: dict(spec)})
            if detail is not None and detail.hit:
                logger.info(f"[PageState] 命中页面: {page_id}（节点={argv.node_name}）")
                return CustomRecognition.AnalyzeResult(box=Rect(0, 0, 1, 1), detail={"page": page_id})

        if not quiet:
            logger.info(f"[PageState] 当前页面不在 {allowed} 中，走原入口流程（节点={argv.node_name}）")
        return CustomRecognition.AnalyzeResult(box=None, detail={"page": None})
