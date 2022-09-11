from collections import deque

from games.azur_lane.task.base import BaseTask, wait, Config
from util.window import GameWindow

__all__ = ["TaskFarmSecret"]


class TaskFarmSecret(BaseTask):
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
