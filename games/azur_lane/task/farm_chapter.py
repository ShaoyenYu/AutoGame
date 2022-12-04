import datetime as dt
import time

from games.azur_lane.interface import scene
from games.azur_lane.task.base import BaseTask, wait, switch_scene, Config
from util.controller.component import CyclicQueue
from util.window import GameWindow

__all__ = ["TaskFarmChapter"]


class TaskFarmChapter(BaseTask):
    name = "FarmChapter"
    mkdir = True

    def __init__(self, window: GameWindow):
        super().__init__(window)
        self.event_handler.set_events("can_run_after_battle")

        self.config.set_all(
            Config("team_one", None, default_value="4,5", introduction="Fleet to use for team one"),
            Config("team_two", None, default_value="6", introduction="Fleet to use for team two"),
            Config("target_stage", None, default_value="13-4", introduction="Target stage to farm"),
            Config("duty_01", None, default_value="8", introduction="Team one duty"),
            Config("max_farm_time", None, default_value=20, introduction="Max times to farm", value_type=int),
            Config("base_dir", None, default_value=f"{self.base_dir}", introduction="Basic directory to save results"),
        )
        self.config.set_config_from_input()

        self.state.update(**{
            "team_one": CyclicQueue(self.config["team_one"]),
            "team_two": CyclicQueue(self.config["team_two"]),
            "duty_01": CyclicQueue(self.config["duty_01"]),
            "cur_chapter": None,
            "cur_farm_time": 0,
        })

        # hotfix
        from pathlib import Path
        self.save_dir = Path(f"{self.config['base_dir']}/{self.config['target_stage']}")
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

    @wait("can_run")
    def switch_to_chapter(self, target_chapter_no):
        self.state["cur_chapter"] = self.scene_cur.recognize_chapter_title(self.window)

        delta_no = target_chapter_no - self.state["cur_chapter"]
        for _ in range(abs(delta_no)):
            if delta_no > 0:
                self.window.left_click([(1807, 513), (1889, 645)], sleep=.3)
            else:
                self.window.left_click([(46, 512), (122, 663)], sleep=.3)

    @wait("can_run")
    def scene_main_to_scene_anchor_aweigh(self):
        switch_scene(self.window, scene.SceneMain, scene.SceneAnchorAweigh)

    @wait("can_run")
    def from_anchor_aweigh_to_campaign_chapter(self, target_chapter_no=13):
        switch_scene(self.window, scene.SceneAnchorAweigh, scene.SceneCampaignChapter)
        if self.scene_cur.at(scene.SceneCampaignChapter):
            self.switch_to_chapter(target_chapter_no)

    @wait("can_run")
    def from_campaign_chapter_to_stage_info(self):
        chapter_no, stage_no = (int(x) for x in self.config["target_stage"].split("-"))
        if self.scene_cur.at(scene.SceneCampaignChapter) and self.state["cur_chapter"] == chapter_no:
            self.scene_cur.goto(self.window, scene.PopupStageInfo, sleep=1, chapter_no=self.config["target_stage"])

    @wait("can_run")
    def from_stage_info_to_fleet_selection(self):
        if self.scene_cur.at(scene.PopupStageInfo):
            self.scene_cur.set_automation(self.window, turn_on=True)
            self.scene_cur.goto(self.window, scene.PopupFleetSelectionArbitrate)

    @wait("can_run")
    def from_fleet_selection_to_duty_selection(self):
        if self.scene_cur.at(scene.PopupFleetSelectionArbitrate):
            self.scene_cur.choose_team(
                self.window,
                team_one=self.state["team_one"].next(), team_two=self.state["team_two"].next(),
            )

            self.scene_cur.goto(self.window, scene.PopupFleetSelectionDuty)

    @wait("can_run")
    def from_duty_selection_to_campaign(self):
        if self.scene_cur.at(scene.PopupFleetSelectionDuty):
            self.scene_cur.set_duty_marine(self.window, team_one=self.state["duty_01"].next())
            self.scene_cur.goto(self.window, scene.SceneCampaign)

    @wait("can_run")
    def wait_for_farming(self):
        if self.scene_cur.at(scene.SceneBattle):
            time.sleep(5)
        elif self.scene_cur.at(scene.SceneCampaign):
            time.sleep(5)

    @wait("can_run")
    def from_campaign_info_to_campaign(self):
        switch_scene(self.window, scene.PopupCampaignInfo, scene.SceneCampaign)

    @wait("can_run")
    def save_result(self):
        if self.scene_cur.at(scene.PopupCampaignReward):
            x, y, w, h = scene.am.get_image_xywh("CampaignChapter.Label_TotalRewards_without_META")
        elif self.scene_cur.at(scene.PopupCampaignRewardWithMeta):
            x, y, w, h = scene.am.get_image_xywh("CampaignChapter.Label_TotalRewards_with_META")
        else:
            return

        time.sleep(5)
        file = f"{self.save_dir}/{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.window.screenshot(x, y, w, h, save_path=file)
        self.state["cur_farm_time"] += 1
        self.scene_cur.goto(self.window, scene.SceneCampaign, sleep=1)
        self.event_handler.wait("can_run_after_battle")

    def execute(self):
        self.scene_main_to_scene_anchor_aweigh()
        self.from_anchor_aweigh_to_campaign_chapter(target_chapter_no=int(self.config["target_stage"].split("-")[0]))
        self.from_campaign_chapter_to_stage_info()
        self.from_stage_info_to_fleet_selection()
        self.from_fleet_selection_to_duty_selection()
        self.from_duty_selection_to_campaign()
        self.wait_for_farming()
        self.save_result()
        self.from_campaign_info_to_campaign()

    def run(self) -> None:
        while self.state["cur_farm_time"] < self.config["max_farm_time"]:
            try:
                self.execute()
                time.sleep(1)

            except Exception as e:
                self.logger.error(e)
            time.sleep(1)
        self.logger.info("finished")
