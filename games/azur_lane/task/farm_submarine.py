import time

from games.azur_lane.interface import scene
from games.azur_lane.task.base import BaseTask, wait, switch_scene

__all__ = ["TaskFarmSubmarineSOS"]


class TaskFarmSubmarineSOS(BaseTask):
    name = "FarmSubmarineSOS"

    remain_rescue_times = None

    @wait("can_run")
    def scene_main_to_scene_anchor_aweigh(self):
        switch_scene(self.window, scene.SceneMain, scene.SceneAnchorAweigh)

    @wait("can_run")
    def scene_anchor_aweigh_to_popup_rescue_sos(self):
        if self.scene_cur.at(scene.SceneAnchorAweigh):
            self.remain_rescue_times = self.scene_cur.recognize_rescue_times(self.window)
            print(f"remain rescue times: {self.remain_rescue_times}")
            if self.remain_rescue_times > 0:
                self.scene_cur.goto(self.window, scene.PopupRescueSOS)
            elif self.remain_rescue_times == 0:
                print("finished.")
                self.scene_cur.goto(self.window, scene.SceneMain)

    @wait("can_run")
    def popup_rescue_sos_to_campaign_chapter(self):
        if self.scene_cur.at(scene.PopupRescueSOS):
            if scene.PopupRescueSOS.is_signal_found(self.window):
                print("signal found")
            else:
                print("signal not found")
            self.scene_cur.goto(self.window, scene.SceneCampaignChapter, sleep=1)

    @wait("can_run")
    def scene_campaign_chapter_to_popup_stage_info(self):
        if self.scene_cur.at(scene.SceneCampaignChapter):
            if not self.scene_cur.goto(self.window, scene.PopupStageInfo, sleep=1, chapter_no="3-5"):
                print("not arrived")
                self.scene_cur.goto(self.window, scene.SceneAnchorAweigh)

    @wait("can_run")
    def popup_stage_info_to_popup_fleet_selection(self):
        switch_scene(self.window, scene.PopupStageInfo, scene.PopupFleetSelectionArbitrate)

    @wait("can_run")
    def popup_fleet_selection_to_scene_campaign(self):
        if self.scene_cur.at(scene.PopupFleetSelectionArbitrate):
            self.scene_cur.choose_team(self.window, team_one=1, team_two=3)
            self.scene_cur.goto(self.window, scene.SceneCampaign)

    @wait("can_run")
    def attack_enemy(self):
        if self.scene_cur.at(scene.SceneCampaign):
            if self.scene_cur.attack_enemies(self.window):
                time.sleep(8)

    @wait("can_run")
    def scene_formation_to_scene_battle(self):
        switch_scene(self.window, scene.PopupInfoAutoBattle, scene.SceneBattleFormation)
        switch_scene(self.window, scene.SceneBattleFormation, scene.SceneBattle)

    @wait("can_run")
    def from_checkpoint_to_campaign(self):
        switch_scene(self.window, scene.PopupGetShip, scene.SceneCampaign)
        switch_scene(self.window, scene.SceneBattleCheckpoint00, scene.SceneCampaign)

        switch_scene(self.window, scene.SceneBattleCheckpoint01, scene.SceneGetItems)
        switch_scene(self.window, scene.SceneGetItems, scene.SceneBattleResult)
        switch_scene(self.window, scene.SceneBattleResult, scene.SceneCampaign)

    @wait("can_run")
    def from_campaign_info_to_campaign(self):
        switch_scene(self.window, scene.PopupCampaignInfo, scene.SceneCampaign)

    def execute(self):
        self.scene_main_to_scene_anchor_aweigh()
        self.scene_anchor_aweigh_to_popup_rescue_sos()
        self.popup_rescue_sos_to_campaign_chapter()
        self.scene_campaign_chapter_to_popup_stage_info()
        self.popup_stage_info_to_popup_fleet_selection()
        self.popup_fleet_selection_to_scene_campaign()
        self.attack_enemy()
        self.scene_formation_to_scene_battle()
        self.from_checkpoint_to_campaign()
        self.from_campaign_info_to_campaign()

        while self.scene_cur.at(scene.SceneBattle):
            time.sleep(2)

    def run(self) -> None:
        while True:
            try:
                self.execute()
            except Exception as e:
                print(e)
            time.sleep(1)
