import random

import numpy as np

from games.azur_lane.interface.scene import SceneUnknown
from util.win32.window import Window


class GameWindow(Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scene_prev = self.scene_cur = SceneUnknown

    @staticmethod
    def gen_random_xy(lt, rb):
        x, y = (random.randint(lt[0], rb[0]), random.randint(lt[1], rb[1]))
        return np.asarray((x, y), dtype=np.uint)

    def left_click(self, position, sleep=0):
        if not isinstance(position, np.ndarray):
            position = np.asarray(position, dtype=np.uint)

        if position.ndim == 2:
            position = self.gen_random_xy(*position)
        elif position.ndim == 1:
            pass
        else:
            raise NotImplementedError

        super().left_click(position, sleep=sleep)
