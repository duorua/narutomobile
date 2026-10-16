"""Run the real Maa state machine against semantic screen fixtures, without ADB.

Only leaf OCR/template results and device actions are substituted. And/inverse,
next/on_error, JumpBack, max_hit and task success remain native framework logic.
Run with maafw 5.13.0 and MAAFW_BINARY_PATH pointing to its native libraries.
"""

import json
import re
import time
from copy import deepcopy
from pathlib import Path

import pytest

pytest.importorskip("maa", reason="Native Pipeline regressions require the project's maafw runtime")
import numpy as np
from maa.controller import CustomController
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

ROOT = Path(__file__).resolve().parents[1]
PIPELINES = ROOT / "assets/resource/base/pipeline"


class Screen:
    def __init__(self, page="welfare", activity=110, claimed=(), animation_frames=3, via_home=False, dialogs=False):
        self.page = page
        self.activity = activity
        self.claimed = set(claimed)
        self.animation_frames = animation_frames
        self.via_home = via_home
        self.dialogs = dialogs
        self.pending = None
        self.actions = []
        self.finished = False
        self.locked_clicks = []
        self.submit_pending = False

    def texts(self, spec):
        if self.page == "gold":
            return ["我要金币"]
        if self.page == "animation":
            return ["第二次", "第三次"]
        if self.page == "sweep_done":
            return ["扫荡完毕"]
        if self.page == "sweep_continue":
            return ["继续扫荡"]
        if self.page != "welfare":
            return []
        roi = spec.get("roi", [0, 0, 0, 0])
        if len(roi) == 4 and roi[1] >= 430 and 0 < roi[3] < 60:
            return [] if self.activity is None else [str(self.activity)]
        if self.pending:
            return ["确定" if self.pending in (40, 100) else "我知道了"]
        return ["福利站", "今日已签", "活跃任务", "金币", "领取"]

    def matches(self, spec):
        if spec.get("recognition") == "OCR":
            expected = spec.get("expected", [".*"])
            if isinstance(expected, str):
                expected = [expected]
            return any(re.search(pattern, text) for pattern in expected for text in self.texts(spec))
        templates = spec.get("template", [])
        if isinstance(templates, str):
            templates = [templates]
        visible = set()
        if self.page == "home":
            visible.add("Naruto_club/benefit_station.png")
        if self.page == "welfare" and self.pending is None:
            visible.add("Naruto_club/close_club_button.png")
            if self.submit_pending:
                visible.add("Naruto_club/mission_submit.png")
            for value, tier in [(40, "first"), (60, "second"), (100, "third")]:
                suffix = f"club_{tier}_award_done" if value in self.claimed else f"{tier}_award"
                visible.add(f"Naruto_club/{suffix}.png")
        if self.page == "sweep_select":
            visible.add("Use_energy/sweep_button.png")
        if self.page == "low_energy":
            visible.add("Use_energy/energy_not_enough.png")
        return bool(visible.intersection(templates))

    def act(self, name):
        self.actions.append(name)
        if name == "club_submit" and self.submit_pending:
            self.submit_pending = False
            self.page = "gold"
        for value, tier in [(40, "first"), (60, "second"), (100, "third")]:
            if name == f"club_{tier}_award":
                if self.activity is None or self.activity < value:
                    self.locked_clicks.append(value)
                    return False
                if self.dialogs:
                    self.pending = value
                else:
                    self.claimed.add(value)
            if name == f"confirm_club_{tier}_award":
                self.claimed.add(value)
                self.pending = None
        if name == "club_reward_recover" and self.page == "gold":
            self.page = "home" if self.via_home else "welfare"
        if name == "club_reward_reenter" and self.page == "home":
            self.page = "welfare"
        if name == "close_naruto_club":
            self.page = "home"
        if name in ("use_energy_ez_sweep", "use_energy_keep_sweep"):
            self.page = "animation"
        if name == "use_energy_reward_animation":
            self.animation_frames -= 1
            if self.animation_frames <= 0:
                self.page = "sweep_done"
                self.finished = True
        return name not in ("club_reward_failed", "use_energy_failed", "back_main_screen_failed")


@pytest.fixture
def run_pipeline(tmp_path):
    assert Toolkit.init_option(tmp_path)

    def run(entry, screen):
        nodes = {}
        for name in ("Naruto_club.json", "Use_energy.json", "SharedNode.json"):
            nodes.update(json.loads((PIPELINES / name).read_text(encoding="utf-8")))

        def replace_recognition(node):
            kind = node.get("recognition", "DirectHit")
            if kind in ("And", "Or"):
                key = "all_of" if kind == "And" else "any_of"
                for child in node[key]:
                    if isinstance(child, dict):
                        replace_recognition(child)
            elif kind not in ("DirectHit",):
                spec = deepcopy(node)
                node["recognition"] = "Custom"
                node["custom_recognition"] = "FixtureScreen"
                node["custom_recognition_param"] = {"spec": spec}

        for node in nodes.values():
            replace_recognition(node)
            node.update(pre_delay=0, post_delay=0, pre_wait_freezes=0, post_wait_freezes=0, rate_limit=1, timeout=25)
            if node.get("action", "DoNothing") != "StopTask":
                node["action"] = "Custom"
                node["custom_action"] = "FixtureAction"

        # Shared navigation is outside these regressions; reaching it is observable.
        nodes["back_main_screen_and_stop"] = {"action": "StopTask"}
        path = tmp_path / "pipeline.json"
        path.write_text(json.dumps(nodes), encoding="utf-8")
        image = np.zeros((720, 1280, 3), dtype=np.uint8)

        class Controller(CustomController):
            def connect(self):
                return True

            def request_uuid(self):
                return "test-no-device"

            def screencap(self):
                return image

        class Recognition(CustomRecognition):
            def analyze(self, context, argv):
                spec = json.loads(argv.custom_recognition_param)["spec"]
                return CustomRecognition.AnalyzeResult(box=(1, 1, 10, 10) if screen.matches(spec) else None, detail={})

        class Action(CustomAction):
            def run(self, context, argv):
                return screen.act(argv.node_name)

        controller = Controller()
        assert controller.post_connection().wait().succeeded
        resource = Resource()
        assert resource.register_custom_recognition("FixtureScreen", Recognition())
        assert resource.register_custom_action("FixtureAction", Action())
        assert resource.post_pipeline(path).wait().succeeded
        tasker = Tasker()
        assert tasker.bind(resource, controller)
        job = tasker.post_task(entry)
        deadline = time.monotonic() + 5
        while not job.status.done and time.monotonic() < deadline:
            time.sleep(0.005)
        if not job.status.done:
            tasker.post_stop().wait()
            pytest.fail(f"Pipeline exceeded the test deadline: {screen.actions[-12:]}")
        return job.succeeded

    return run


@pytest.mark.parametrize("via_home", [False, True])
def test_club_returns_from_gold_and_claims_all_available_rewards(run_pipeline, via_home):
    screen = Screen(page="gold", via_home=via_home)
    assert run_pipeline("check_club_all_submit", screen)
    assert screen.claimed == {40, 60, 100}
    assert "club_reward_recover" in screen.actions
    assert "award_kale" not in screen.actions


@pytest.mark.parametrize("activity", [0, 39, 40, 59, 60, 99, 100, 110])
def test_club_checks_each_milestone_without_clicking_locked_rewards(run_pipeline, activity):
    screen = Screen(activity=activity, dialogs=True)
    assert run_pipeline("check_club_all_submit", screen)
    assert screen.claimed == {x for x in (40, 60, 100) if activity >= x}
    assert screen.locked_clicks == []


def test_club_already_claimed_does_not_click_again(run_pipeline):
    screen = Screen(claimed=(40, 60, 100))
    assert run_pipeline("check_club_all_submit", screen)
    assert not any(x in screen.actions for x in ("club_first_award", "club_second_award", "club_third_award"))


def test_club_submission_that_opens_gold_returns_to_the_reward_chain(run_pipeline):
    screen = Screen()
    screen.submit_pending = True
    assert run_pipeline("swipe_for_club_submit", screen)
    assert screen.claimed == {40, 60, 100}
    assert screen.actions.index("club_submit") < screen.actions.index("club_reward_recover")


@pytest.mark.parametrize("claimed", [(40,), (60,), (100,)])
def test_club_partial_claims_still_collect_remaining_tiers(run_pipeline, claimed):
    screen = Screen(claimed=claimed)
    assert run_pipeline("check_club_all_submit", screen)
    assert screen.claimed == {40, 60, 100}
    assert sum(x in screen.actions for x in ("club_first_award", "club_second_award", "club_third_award")) == 2


@pytest.mark.parametrize("page,activity", [("unknown", 110), ("welfare", None)])
def test_club_unknown_page_or_unreadable_activity_cannot_succeed(run_pipeline, page, activity):
    screen = Screen(page=page, activity=activity)
    assert not run_pipeline("check_club_all_submit", screen)
    assert screen.claimed == set()


@pytest.mark.parametrize(
    "entry,page", [("use_energy_ez_sweep", "sweep_select"), ("use_energy_keep_sweep", "sweep_continue")]
)
def test_sweep_advances_reward_animation_until_completion(run_pipeline, entry, page):
    screen = Screen(page=page, animation_frames=30)
    assert run_pipeline(entry, screen)
    assert screen.finished
    assert screen.actions.count("use_energy_reward_animation") == 30
    assert "retry_failed" not in screen.actions


def test_sweep_unknown_result_cannot_succeed(run_pipeline):
    screen = Screen(page="unknown")
    assert not run_pipeline("use_energy_finished", screen)


def test_sweep_stuck_animation_has_a_finite_failure(run_pipeline):
    screen = Screen(page="animation", animation_frames=10000)
    assert not run_pipeline("use_energy_reward_animation", screen)
    assert not screen.finished
    assert len(screen.actions) <= 125


def test_sweep_insufficient_energy_is_a_valid_end(run_pipeline):
    screen = Screen(page="low_energy")
    assert run_pipeline("use_energy_finished", screen)
    assert "use_energy_not_enough_sign" in screen.actions
