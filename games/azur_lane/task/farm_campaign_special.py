import datetime as dt
import time
from pathlib import Path

from games.azur_lane.interface import scene
from games.azur_lane.task.base import BaseTask, wait, switch_scene, Config
from util.window import GameWindow

__all__ = ["TaskFarmCampaignSpecial"]


class CyclicQueue:
    def __init__(self, it):
        self.it = it
        self.length = len(self.it)
        self.it_cyclic = self.cyclic_iter()

    def cyclic_iter(self):
        i = 0
        while True:
            yield self.it[i]
            i = (i + 1) % self.length

    def next(self):
        return next(self.it_cyclic)

    def __next__(self):
        return next(self.it_cyclic)


def split_as_ints(comma_string):
    return [int(x) for x in comma_string.split(",")]


class TaskFarmCampaignSpecial(BaseTask):
    name = "TaskFarmCampaignSpecial"
    mkdir = True

    def __init__(self, window: GameWindow):
        super().__init__(window)

        self.config.set_all(
            Config("team_01", None, default_value="0", introduction="Fleet to use for team one"),
            Config("team_02", None, default_value="1", introduction="Fleet to use for team two"),
            Config("duty_01", None, default_value="8,4", introduction="Tea, one duty"),
            Config("target_stage", None, default_value="B3", introduction="Target stage to farm"),
            Config("max_farm_time", None, default_value="20", introduction="Max times to farm", value_type=int),
            Config("base_dir", None, default_value=f"{self.base_dir}", introduction="Basic directory to save results")
        )
        self.config.set_config_from_input()

        self.state.update(**{
            "team_01": CyclicQueue(split_as_ints(self.config["team_01"])),
            "team_02": CyclicQueue(split_as_ints(self.config["team_02"])),
            "duty_01": CyclicQueue(split_as_ints(self.config["duty_01"])),
            "target_stage": CyclicQueue(self.config["target_stage"].split(",")),
            "cur_farm_time": 0,
        })

        self.cur_target_stage = None

    @property
    def save_dir(self):
        # hotfix
        save_dir = Path(f"{self.base_dir}/{self.config['base_dir']}")
        if self.cur_target_stage is not None:
            save_dir = save_dir / f"{self.cur_target_stage}"
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        return save_dir

    @wait("can_run")
    def scene_main_to_scene_anchor_aweigh(self):
        switch_scene(self.window, scene.SceneMain, scene.SceneAnchorAweigh)

    @wait("can_run")
    def from_anchor_aweigh_to_special_campaign(self):
        switch_scene(self.window, scene.SceneAnchorAweigh, scene.SceneCampaignSpecial)

    @wait("can_run")
    def from_campaign_chapter_to_stage_info(self):
        if self.scene_cur.at(scene.SceneCampaignSpecial) or self.scene_cur.at(scene.SceneCampaignActivity):
            chapter_name = self.scene_cur.recognize_chapter_title(self.window)

            self.cur_target_stage = self.state['target_stage'].next()
            self.scene_cur.goto(
                self.window, scene.PopupStageInfo, sleep=1,
                chapter_no=f"{chapter_name}-{self.cur_target_stage}"
            )

    @wait("can_run")
    def from_stage_info_to_fleet_selection(self):
        if self.scene_cur.at(scene.PopupStageInfo):
            self.scene_cur.set_automation(self.window, turn_on=True)
            self.scene_cur.goto(self.window, scene.PopupFleetSelectionArbitrate)

    @wait("can_run")
    def from_fleet_selection_to_duty_selection(self):
        if self.scene_cur.at(scene.PopupFleetSelectionArbitrate):
            cur_team_01, cur_team_02 = self.state["team_01"].next(), self.state["team_02"].next()
            self.scene_cur.choose_team(self.window, team_one=cur_team_01, team_two=cur_team_02)
            self.scene_cur.goto(self.window, scene.PopupFleetSelectionDuty)
        elif self.scene_cur.at(scene.PopupFleetSelectionFixed):
            self.scene_cur.goto(self.window, scene.PopupFleetSelectionDuty)
        else:
            raise

    @wait("can_run")
    def from_duty_selection_to_campaign(self):
        if self.scene_cur.at(scene.PopupFleetSelectionDuty):
            self.scene_cur.set_duty_marine(self.window, team_one=self.state["duty_01"].next())
            self.scene_cur.show_duty(self.window)
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
        self.logger.info(f"Current Farm Times: {self.state['cur_farm_time']}")
        self.event_handler.wait("can_run_after_battle")

    def execute(self):
        self.scene_main_to_scene_anchor_aweigh()
        self.from_anchor_aweigh_to_special_campaign()
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
