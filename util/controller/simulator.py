import time

from win32con import VK_F11

from games.azur_lane.manager import Gateway
from util.win32 import win32gui
from util.win32.monitor import set_process_dpi_awareness
from util.window import GameWindow

set_process_dpi_awareness(2, silent=True)


class BlueStack:
    def __init__(self, window_name: str):
        self.window_sim = GameWindow(window_name=window_name)
        self.window_ctl = GameWindow(window_hwnd=win32gui.FindWindowEx(self.window_sim.hwnd, None, None, None))
        self.gateway = Gateway(self.window_ctl)

    def set_to_fullscreen(self, width, height):
        # set simulator to full screen, default hotkey is F11
        cw, ch = 0, 0
        while cw != width or ch != height:
            self.window_ctl.press_key(VK_F11, 0x0000000000570001)  # 0x0000000000570001: scan_code=57, repeat=1
            time.sleep(.5)
            l, t, r, b = self.window_ctl.get_window_rect()
            cw, ch = r - l, b - t
            print(f"resetting: {cw, ch}")
            time.sleep(1)
