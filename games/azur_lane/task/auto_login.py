import time

from games.azur_lane.interface import scene
from games.azur_lane.task.base import BaseTask, switch_scene
from util.window import GameWindow

__all__ = ["TaskAutoLogin"]


class TaskAutoLogin(BaseTask):
    name = "TaskAutoLogin"

    def __init__(self, window: GameWindow):
        super().__init__(window)

    # main logic
    def from_scene_login_by_account_to_scene_loging_by_third_party(self):
        switch_scene(self.window, scene.SceneLoginByAccount, scene.SceneLoginByThirdParty)

    def from_scene_loging_by_third_party_to_scene_login_by_google(self):
        switch_scene(self.window, scene.SceneLoginByThirdParty, scene.SceneLoginByGoogle)

    def from_scene_login_by_google_to_choose_account(self):
        if self.scene_cur.at(scene.SceneLoginByGoogle):
            self.scene_cur.choose_account(self.window)

    def from_scene_login_to_scene_main(self):
        switch_scene(self.window, scene.SceneLogin, scene.SceneMain)

    # exceptions
    def from_popup_update_hint_to_scene_scene_unknown(self):
        switch_scene(self.window, scene.PopupUpdateHint, scene.SceneUnknown)

    def from_popup_info_to_scene_login(self):
        if self.scene_cur.at(scene.PopupInformationStyle001):
            if self.scene_cur.recognize_text(self.window) == 0:
                switch_scene(self.window, scene.PopupInformationStyle001, scene.SceneLoginByAccount)

    def execute(self):
        self.from_scene_login_by_account_to_scene_loging_by_third_party()
        self.from_scene_loging_by_third_party_to_scene_login_by_google()
        self.from_scene_login_by_google_to_choose_account()
        self.from_scene_login_to_scene_main()

        self.from_popup_info_to_scene_login()
        self.from_popup_update_hint_to_scene_scene_unknown()

    def run(self) -> None:
        while True:
            try:
                self.execute()
                time.sleep(1)

            except Exception as e:
                self.logger.error(e)
            time.sleep(1)
