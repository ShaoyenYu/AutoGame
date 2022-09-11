import datetime as dt
import time
from collections import deque

from games.azur_lane.interface import scene
from games.azur_lane.task.base import BaseTask, wait, switch_scene, Config
from util.window import GameWindow

__all__ = ["TaskFarmChapter"]


class TaskFarmChapter(BaseTask):
    name = "FarmChapter"
    mkdir = True

    def __init__(self, window: GameWindow):
        super().__init__(window)
        self.event_handler.set_events("can_run_after_battle")

        self.config_manager.set_all(
            Config("team_one", None, default_value="4,5", introduction="Fleet to use for team one"),
            Config("target_stage", None, default_value="13-4", introduction="Target stage to farm"),
            Config("max_farm_times", None, default_value="20", introduction="Max times to farm"),
            Config("base_dir", None, default_value=f"{self.base_dir}", introduction="Basic directory to save results")
        )
        self.config_manager.set_config_from_input()

        # hotfix
        from pathlib import Path
        self.save_dir = Path(f"{self.config_manager['base_dir']}/{self.config_manager['target_stage']}")
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

        self.target_stage = self.config_manager["target_stage"]
        self.team_one = deque((int(x) for x in self.config_manager["team_one"].split(",")))
        self.cur_farm_time = 0
        self.max_farm_times = int(self.config_manager["max_farm_times"])
        self.cur_chapter = None

    @wait("can_run")
    def switch_to_chapter(self, target_chapter_no):
        self.cur_chapter = self.scene_cur.recognize_chapter_title(self.window)

        delta_no = target_chapter_no - self.cur_chapter
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
        chapter_no, stage_no = (int(x) for x in self.target_stage.split("-"))
        if self.scene_cur.at(scene.SceneCampaignChapter) and self.cur_chapter == chapter_no:
            self.scene_cur.goto(self.window, scene.PopupStageInfo, sleep=1, chapter_no=self.target_stage)

    @wait("can_run")
    def from_stage_info_to_campaign(self):
        if self.scene_cur.at(scene.PopupStageInfo):
            self.scene_cur.set_automation(self.window, turn_on=True)
            self.scene_cur.goto(self.window, scene.PopupFleetSelectionArbitrate)

        if self.scene_cur.at(scene.PopupFleetSelectionArbitrate):
            self.team_one.append(cur_team := self.team_one.popleft())
            self.scene_cur.choose_team(self.window, team_one=cur_team, team_two=6)
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
        self.cur_farm_time += 1
        self.scene_cur.goto(self.window, scene.SceneCampaign, sleep=1)
        self.event_handler.wait("can_run_after_battle")

    def execute(self):
        self.scene_main_to_scene_anchor_aweigh()
        self.from_anchor_aweigh_to_campaign_chapter(target_chapter_no=13)
        self.from_campaign_chapter_to_stage_info()
        self.from_stage_info_to_campaign()
        self.wait_for_farming()
        self.save_result()
        self.from_campaign_info_to_campaign()

    def run(self) -> None:
        while self.cur_farm_time < self.max_farm_times:
            try:
                self.execute()
                time.sleep(1)

            except Exception as e:
                self.logger.error(e)
            time.sleep(1)
        self.logger.info("finished")
