from games.azur_lane.manager import Gateway
from util.win32 import win32gui
from util.win32.monitor import set_process_dpi_awareness
from util.window import GameWindow

set_process_dpi_awareness(2, silent=True)


class Bluestack:
    def __init__(self, window_name: str):
        self.window_sim = GameWindow(window_name=window_name)
        self.window_ctl = GameWindow(window_hwnd=win32gui.FindWindowEx(self.window_sim.hwnd, None, None, None))
        self.gateway = Gateway(self.window_ctl)
