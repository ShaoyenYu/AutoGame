import time
from threading import Thread

from games.azur_lane import logger_azurlane
from games.azur_lane.interface.scene import *
from games.azur_lane.task import *
from util.window import GameWindow


class SceneManager:
    SCENES_REGISTERED = {x.name: x for x in globals().values() if type(x) is Scene.__class__ and issubclass(x, Scene)}

    logger = logger_azurlane

    def __init__(self, game_window: GameWindow):
        self.window = game_window
        self.config = {"interval": 1}
        self.refresher = Thread(target=self.refresh_scene)
        self.refresher.start()

    def set_config(self, attribute: str, value):
        self.config[attribute] = value

    def refresh_scene(self):
        while True:
            self.detect_scene()
            time.sleep(self.config["interval"])

    @property
    def scene_cur(self):
        return self.window.scene_cur

    @property
    def scene_prev(self):
        return self.window.scene_prev

    def at(self, scene_name: str):
        return self.scene_cur.at(self.SCENES_REGISTERED[scene_name])

    def goto(self, scene_name: str, sleep=1, *args, **kws):
        has_arrived = self.scene_cur.goto(self.window, dest := self.SCENES_REGISTERED[scene_name], sleep, *args, **kws)
        return has_arrived

    def update_scenes(self, scene_cur, scene_prev=None):
        if self.window.scene_cur.at(scene_cur):
            return
        self.window.scene_prev, self.window.scene_cur = scene_prev or self.window.scene_cur, scene_cur
        self.logger.info(f"switch scene ({self.window.scene_prev} --> {self.window.scene_cur})")

    def detect_scene(self):
        self.update_scenes(self._detect_scene(self.window))
        return self.window.scene_cur

    @classmethod
    def _detect_scene(cls, window):
        for scene in cls.SCENES_REGISTERED.values():
            if hasattr(scene, "at_this_scene") and scene.at_this_scene(window):
                return scene
        return SceneUnknown


class TaskManager:
    TASKS_REGISTERED = {
        x.name: x for x in globals().values() if type(x) is BaseTask.__class__ and issubclass(x, BaseTask)
    }

    def __init__(self, game_window: GameWindow):
        self.game_window = game_window
        self.tasks = {task_name: task_class(self.game_window) for task_name, task_class in self.TASKS_REGISTERED.items()}

    # should provide task manage api here.
    def resume_task(self, task):
        pass

    def pause_tsk(self):
        pass

    def stop_task(self):
        pass


class Gateway:
    def __init__(self, game_window):
        self.window = game_window
        self.task_manager = TaskManager(self.window)
        self.scene_manager = SceneManager(self.window)