import time
from subprocess import Popen, DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP

from win32con import HWND_TOP, SWP_SHOWWINDOW

from util.controller.simulator import BlueStack
from util.win32.monitor import get_monitors


def initialize_simulator(window_name, launch_cmd):
    Popen(launch_cmd, close_fds=False, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    time.sleep(3)
    bs = BlueStack(window_name)
    return bs


def set_to_fullscreen(simulator: BlueStack):
    monitor = get_monitors()[0]

    # set position to monitor 1
    l, t, w, h = monitor.rect.left, monitor.rect.top, int(monitor.rect.width * .75), int(monitor.rect.height * .75)
    simulator.window_sim.set_window_pos(HWND_TOP, l, t, w, h, SWP_SHOWWINDOW)
    time.sleep(1)

    simulator.set_to_fullscreen(monitor.rect.width, monitor.rect.height - 1)


def launch(window_name, launch_cmd):
    simulator = initialize_simulator(window_name, launch_cmd)
    set_to_fullscreen(simulator)
    return simulator
