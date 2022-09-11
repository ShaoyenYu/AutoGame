import time

import numpy as np

from games.azur_lane import logger_azurlane
from games.azur_lane.interface.scene.asset_manager import am
from lib.dummy_paddleocr import load_recognizer
from util import game_cv
from util.proto import TwoDimArrayLike
from util.win32.window import parse_int_bgr2rgb

ocr_paddle = load_recognizer()


def goto_scene_main(window):
    window.left_click(am.rect("AnchorAweigh.Button_BackToMain"), sleep=1)


def auto_retry(max_retry, retry_interval=.1):
    def _auto_retry(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                for _ in range(max_retry):
                    try:
                        return f(*args, **kwargs)
                    except:
                        time.sleep(retry_interval)
                        continue
                return None

        return wrapper

    return _auto_retry


class SceneMeta(type):
    def __repr__(cls):
        return f"{cls.__name__}"


class SceneRecognizer:
    @classmethod
    def at(cls, scene) -> bool:
        """

        Args:
            scene:

        Returns:

        """
        return cls is scene

    @classmethod
    def at_this_scene(cls, window):
        return cls.at_this_scene_impl(window)

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        """Custom method to implement"""
        pass

    @staticmethod
    def compare_with_pixels(window, pixels: TwoDimArrayLike, tolerance=0) -> bool:
        """

        Args:
            window:
            pixels: 2-D array-like
                e.g [[x1, y1, BGR_1], [x2, y2, BGR_2], ...]
            tolerance: int, default 0
                tolerance for R, G, B

        Returns:

        """
        real = np.apply_along_axis(lambda xy: window.pixel_from_window(*xy, as_int=True), axis=1, arr=pixels[:, 0:2])
        return (np.array(parse_int_bgr2rgb(real ^ pixels[:, 2])).T <= tolerance).all()

    @staticmethod
    def compare_with_template(window, rect: list, template, threshold=1.00) -> bool:
        lt, rb = rect
        origin = window.screenshot(lt[0], lt[1], rb[0] - lt[0], rb[1] - lt[1])
        min_value, max_value, min_loc, max_loc = game_cv.match_single_template(origin, template)
        print(min_value, max_value)
        return min_value >= threshold


class SceneRouter:
    ways = {}

    @classmethod
    def ways_to(cls, scene_name):
        try:
            f = cls.ways[scene_name]
            if type(f) is classmethod:
                return getattr(cls, f.__func__.__name__)
            elif callable(f):
                return f

        except Exception as e:
            print("error: ", cls)
            print(e)
            raise e


class Scene(SceneRecognizer, SceneRouter, metaclass=SceneMeta):
    name = ""
    window = None
    logger = logger_azurlane

    def __init__(self, window):
        self.window = window

    def __repr__(self):
        return f"{self.name} @ {self.window}"

    @classmethod
    def goto(cls, window, next_scene, sleep=0, *args, **kwargs):
        if not cls.at_this_scene(window=window):
            cls.logger.warning(f"scene changed unexpectedly (expected->{cls}, cur->{window.scene_cur})")
            return False

        cls.ways_to(next_scene.name)(window, *args, **kwargs)

        if sleep > 0:
            time.sleep(sleep)

        if has_arrived := next_scene.at_this_scene_impl(window):
            window.scene_prev, window.scene_cur = window.scene_cur, next_scene
        return has_arrived


class SceneUnknown(Scene):
    name = "Scene.Unknown"
