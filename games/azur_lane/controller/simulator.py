import random
import time
from typing import Dict, Tuple, Union

import numpy as np

from games.azur_lane.config import CONFIG_SCENE
from games.azur_lane.controller import scene
from util.io import load_yaml
from util.win32 import win32gui
from util.win32.monitor import set_process_dpi_awareness
from util.win32.window import Window, parse_rgb_int2tuple

set_process_dpi_awareness(2, silent=True)

SCENES = load_yaml(CONFIG_SCENE)


class AzurLaneWindow(Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scene_prev = self.scene_cur = scene.SceneUnknown(self)
        self.debug = kwargs.get("debug", False)

    @staticmethod
    def gen_random_xy(lt, rb):
        x, y = (random.randint(lt[0], rb[0]), random.randint(lt[1], rb[1])) if random else (lt[0], rb[0])
        return x, y

    def left_click(self, coordinate: Union[Tuple[int, int], Dict[str, list]], sleep=0, add_random=True):
        if isinstance(coordinate, dict):
            x, y = self.gen_random_xy(*coordinate["__Rect"][:2])
        elif isinstance(coordinate, (tuple, list)):
            if isinstance(coordinate[0], (tuple, list)):
                x, y = self.gen_random_xy(*coordinate[:2])
            elif isinstance(coordinate[0], (np.integer, int)):
                x, y = coordinate
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
        super().left_click((x, y), sleep)

    def compare_with_pixel(self, pixels, threshold=1, tolerance=0, debug=False) -> bool:
        correct, wrong = 0, 0
        for x, y, rgb_int in pixels:
            if tolerance == 0:
                pixel = self.pixel_from_window(x, y, as_int=True)
                eq = (pixel == rgb_int)
            else:
                pixel = self.pixel_from_window(x, y, as_int=False)
                rgb_tuple = parse_rgb_int2tuple(rgb_int)
                eq = all((abs(x1 - x2) <= tolerance for x1, x2 in zip(pixel, rgb_tuple)))

            if not eq:
                if debug:
                    print(f"WRONG: {x, y}, RGB: {parse_rgb_int2tuple(rgb_int)}(Required) != {parse_rgb_int2tuple(pixel) if isinstance(pixel, int) else pixel}(Real)")
                wrong += 1
            else:
                correct += 1

        if correct == 0:
            return False
        if wrong == 0:
            return True
        return (correct / (correct + wrong)) >= threshold

    def compare_with_template(self, rect: list, template, threshold=1.00) -> bool:
        lt, rb = rect
        origin = self.screenshot(lt[0], lt[1], rb[0] - lt[0], rb[1] - lt[1])
        min_value, max_value, min_loc, max_loc = scene.match_single_template(origin, template)
        print(min_value, max_value)
        return min_value >= threshold


class Bluestack:
    def __init__(self, window_name: str):
        self.window_sim = AzurLaneWindow(window_name=window_name)
        self.window_ctl = AzurLaneWindow(window_hwnd=win32gui.FindWindowEx(self.window_sim.hwnd, None, None, None))


if __name__ == '__main__':
    w = AzurLaneWindow(window_name="BS_AzurLane")
    while True:
        w.scene_cur.detect_scene()
        print(w.scene_cur)
        time.sleep(1)
