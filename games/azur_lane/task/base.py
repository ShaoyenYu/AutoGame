from pathlib import Path

from games.azur_lane import logger_azurlane
from games.azur_lane.config import DIR_USR_AUTO_GAME_AZURLANE
from util.concurrent import PauseEventHandler
from util.window import GameWindow


def wait(*to_wait):
    def _wait(f):
        def wrapper(*args, **kwargs):
            this = args[0]  # type: BaseTask
            this.event_handler.wait(*to_wait)
            return f(*args, **kwargs)

        return wrapper

    return _wait


def switch_scene(window: GameWindow, scene_from, scene_to):
    if window.scene_cur.at(scene_from):
        has_arrived = window.scene_cur.goto(window, scene_to)
        return has_arrived
    return False


class Config:
    def __init__(self, name, value=None, default_value=None, introduction="", value_type=str):
        self.name = name
        self.value = value_type(value) if value is not None else None
        self.default_value = default_value
        self.introduction = introduction
        self.value_type = value_type

    def __repr__(self):
        return f"config name {self.name}, value {self.value}"


class ConfigManager:
    def __init__(self, *configs: Config):
        self.configs = {config.name: config for config in configs}

    def __getitem__(self, item):
        return self.configs[item].value

    def set_all(self, *configs: Config):
        for config in configs:
            self.configs[config.name] = config

    def set_config_from_input(self, source=input):
        for config_name, config in self.configs.items():
            if config.value is not None:
                continue
            input_value = source(f"Set config {config_name}: ") or config.default_value
            config.value = config.value_type(input_value)
        self.show_configs()

    def show_configs(self):
        print(f"Curren config:")
        for cfg in self.configs.values():
            print(f"  {cfg}")


class BaseTask:
    name = ""
    mkdir = False

    state = {}
    pause_events = (
        "can_run", "can_run_after_battle"
    )
    config = ConfigManager()
    logger = logger_azurlane

    def __init__(self, window: GameWindow = None):
        self.event_handler = PauseEventHandler(*self.pause_events)
        self.window = window

        self.base_dir = f"{DIR_USR_AUTO_GAME_AZURLANE}/{self.name}"
        if self.mkdir:
            Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self.event_handler.resume()

    def reverse(self, event_names):
        self.event_handler.reverse(event_names)

    @property
    def scene_cur(self):
        return self.window.scene_cur

    @property
    def scene_prev(self):
        return self.window.scene_prev
