import time
from multiprocessing import SimpleQueue

from pynput import keyboard

from games.azur_lane import logger_azurlane
from games.azur_lane.interface.scene import SCENES_REGISTERED, SceneUnknown
from games.azur_lane.task import TASKS_REGISTERED
from util.concurrent import KillableThread
from util.window import GameWindow


class SceneManager:
    SCENES_REGISTERED = SCENES_REGISTERED
    logger = logger_azurlane

    def __init__(self, game_window: GameWindow):
        self.window = game_window
        self.config = {"interval": 1}
        self.refresher = KillableThread(target=self.refresh_scene)

    def set_config(self, attribute: str, value):
        self.config[attribute] = value

    def refresh_scene(self):
        while True:
            self._refresh_scene()
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

    def _refresh_scene(self):
        self._update_scene(scene_cur=self._recognize_scene(self.window))
        return self.window.scene_cur

    def _update_scene(self, scene_cur, scene_prev=None):
        if self.window.scene_cur.at(scene_cur):
            return
        self.window.scene_prev, self.window.scene_cur = scene_prev or self.window.scene_cur, scene_cur
        self.logger.info(f"switch scene ({self.window.scene_prev} --> {self.window.scene_cur})")

    @classmethod
    def _recognize_scene(cls, window):
        for scene in cls.SCENES_REGISTERED.values():
            if hasattr(scene, "at_this_scene") and scene.at_this_scene(window):
                return scene
        return SceneUnknown

    def start(self):
        self.refresher.start()

    def close(self):
        self.refresher.terminate()


class TaskManager:
    TASKS_REGISTERED = TASKS_REGISTERED

    def __init__(self, game_window: GameWindow):
        self.game_window = game_window
        self.executors = {}

    # should provide task manage api here.
    def start_task(self, task_name):
        if task_name in self.executors:
            logger_azurlane.warning(f"Task {task_name} already in executor.")
            return False

        task = self.TASKS_REGISTERED[task_name](self.game_window)
        executor = KillableThread(target=task.run, name=f"AutoGame[TaskManager]-{task_name}")
        self.executors[task.name] = (task, executor)
        executor.start()
        task.start()
        return True

    def resume_task(self, task):
        pass

    def pause_tsk(self):
        pass

    def stop_task(self, task_name):
        if task_name not in self.executors:
            logger_azurlane.warning(f"Task {task_name} not running.")
            return False

        task_instance, task_executor = self.executors.pop(task_name)
        task_executor.terminate()
        return True

    def list_task(self):
        for task_name, (task_instance, task_executor) in self.executors.items():
            logger_azurlane.info(f"{task_name} [{'Alive' if task_executor.is_alive() else 'Unknown'}]")

    def get_current_task(self):
        for task_name, (task_instance, task_executor) in self.executors.items():
            if task_executor.is_alive():
                return task_instance, task_executor
        return None, None

    def close(self):
        task_list = list(self.executors.keys())
        for k in task_list:
            _, task_executor = self.executors[k]
            task_executor.terminate()
            self.executors.pop(k)


class InputAdapter:
    MSG_CAN_RUN_AFTER_BATTLE = 1
    MSG_CAN_RUN = 2

    def __init__(self, queue):
        self.queue = queue
        self.keyboard_listener = keyboard.Listener(on_release=self._on_keyboard_release)

    def _on_keyboard_release(self, key):
        if key is keyboard.Key.f9:
            self._put_message(self.MSG_CAN_RUN_AFTER_BATTLE)
        elif key is keyboard.Key.f10:
            self._put_message(self.MSG_CAN_RUN)

    def _put_message(self, message):
        self.queue.put(message)

    def start(self):
        self.keyboard_listener.start()

    def close(self):
        self.keyboard_listener.stop()


class Gateway:
    def __init__(self, game_window):
        self.message_queue = SimpleQueue()

        self.window = game_window
        self.input_adapter = InputAdapter(self.message_queue)
        self.task_manager = TaskManager(self.window)
        self.scene_manager = SceneManager(self.window)
        self.message_handler = KillableThread(target=self.handle_message)

    # consume input messages and change task status
    def handle_message(self):
        translation = {
            self.input_adapter.MSG_CAN_RUN_AFTER_BATTLE: "can_run_after_battle",
            self.input_adapter.MSG_CAN_RUN: "can_run",
        }
        while True:
            msg = self.message_queue.get()
            if (msg_trans := translation.get(msg)) is not None:
                task_instance, _ = self.task_manager.get_current_task()
                if task_instance is None:
                    logger_azurlane.info("No task is running currently.")
                    continue
                task_instance.reverse(msg_trans)

    def start(self):
        self.input_adapter.start()
        self.scene_manager.start()
        self.message_handler.start()

    def close(self):
        self.input_adapter.close()
        self.scene_manager.close()
        self.task_manager.close()
        self.message_handler.terminate()
        logger_azurlane.info("Gateway Terminated.")
