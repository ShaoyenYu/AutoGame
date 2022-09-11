import time
from queue import Queue
from threading import Thread, Event

import pyautogui as pag
from pynput import keyboard

from util.win32 import common, monitor, win32gui
from util.win32.window import parse_int_bgr2rgb, parse_tuple_rgb2bgr

monitor.set_process_dpi_awareness(2, silent=True)


class PixelDetector:
    monitors = monitor.get_monitors()
    config = {"adjust_coordinate": True, "method": 1}
    cur_pixel_info = dict()

    @classmethod
    def adjust_coordinate(cls, x, y):
        for mon in cls.monitors:
            if mon.rect.left <= x < mon.rect.right and mon.rect.top <= y <= mon.rect.bottom:
                cls.cur_pixel_info["monitor"] = mon
                return x - mon.rect.left, y - mon.rect.top

    @classmethod
    def get_pixel_rgb(cls, coordinate, hwnd):
        hdc = win32gui.GetWindowDC(hwnd)
        if cls.config["method"] == 1:
            try:
                rgb_int = win32gui.GetPixel(hdc, *coordinate)
                win32gui.ReleaseDC(hwnd, hdc)
            except:
                win32gui.ReleaseDC(hwnd, hdc)
                rgb_int = None
        elif cls.config["method"] == 2:
            try:
                rgb_int = parse_tuple_rgb2bgr(pag.pixel(*coordinate))
            except OSError:
                rgb_int = None
            except Exception:
                raise

        return rgb_int

    @classmethod
    def update_pixel_info(cls):
        p = pag.position()
        coordinate_global = p.x, p.y

        hwnd_client = win32gui.WindowFromPoint(coordinate_global)
        coordinate_client = win32gui.ScreenToClient(hwnd_client, coordinate_global)

        rgb_int = cls.get_pixel_rgb(coordinate_client, hwnd_client)
        rgb_tuple = parse_int_bgr2rgb(rgb_int) if rgb_int is not None else None

        cls.cur_pixel_info.update(
            hwnd_client=hwnd_client,
            rgb_int=rgb_int, rgb_tuple=rgb_tuple,
            coordinate_global=coordinate_global, coordinate_client=coordinate_client,
            coordinate_global_mod=cls.adjust_coordinate(p.x, p.y),
        )

    @classmethod
    def tell_pixel_info(cls):
        def pretty_format(it, space):
            return ", ".join((f"{s:>{space}}" for s in it))
        try:
            pixel_info = cls.cur_pixel_info.copy()
            hwnd_client = pixel_info['hwnd_client']
            coordinate_global_to_use = "coordinate_global_mod" if cls.config["adjust_coordinate"] else "coordinate_global"
            text_coordinate_global = pretty_format(pixel_info[coordinate_global_to_use], 4)
            text_coordinate_client = pretty_format(pixel_info["coordinate_client"], 4)
            text_rgb_tuple = pretty_format(pixel_info["rgb_tuple"] or ('', '', ''), 3)

            print("=" * 128)
            print(f"【{win32gui.GetWindowText(hwnd_client)}】@{hwnd_client} @{pixel_info['monitor']}")
            print(f"Global: ({text_coordinate_global})  "
                  f"Client: ({text_coordinate_client})  "
                  f"RGB: ({text_rgb_tuple}) {rgb_int if (rgb_int := pixel_info['rgb_int']) is not None else ''}")
        except Exception as e:
            print(e)

    @classmethod
    def copy_pixel_info(cls):
        pixel_info = cls.cur_pixel_info.copy()
        common.set_text(f"{[*pixel_info['coordinate_client'], pixel_info['rgb_int']]},")


class PausableThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_can_run = Event()
        self.interval = 1
        self.pixel_detector = PixelDetector

    def start(self) -> None:
        super().start()
        self.resume()

    def run(self) -> None:
        while True:
            self.status_can_run.wait()
            try:
                self.pixel_detector.update_pixel_info()
                self.pixel_detector.tell_pixel_info()
                time.sleep(self.interval)
            finally:
                pass

    def pause(self):
        self.status_can_run.clear()
        print("paused")

    def resume(self):
        self.status_can_run.set()
        print("resumed")

    def is_paused(self):
        return not self.status_can_run.is_set()

    def set_interval(self):
        self.status_can_run.clear()
        self.interval = float(input("set a new interval: "))
        self.status_can_run.set()

    def set_method(self):
        self.status_can_run.clear()
        self.pixel_detector.config["method"] = int(input("set a new method(1-all screen; 2-current screen): "))
        self.status_can_run.set()


class Manager(Thread):
    def __init__(self):
        super().__init__()
        self.input_keys = Queue()
        self._job_thread = PausableThread()
        self._listener_keyboard = keyboard.Listener(on_release=self.on_keyboard_release)

    def start(self):
        super().start()
        self._job_thread.start()
        self._listener_keyboard.start()

    def run(self) -> None:
        binding_ops = {
            "f4": PixelDetector.copy_pixel_info,
            "f7": self._job_thread.set_method,
            "f8": self._job_thread.set_interval,
            "f12": lambda: self._job_thread.resume() if self._job_thread.is_paused() else self._job_thread.pause(),
        }

        while True:
            key = self.input_keys.get(block=True)
            key_name = self.get_key_name(key)
            if (op := binding_ops.get(key_name)) is not None:
                print(f"{key_name} pressed")
                op()

    @staticmethod
    def get_key_name(key):
        return key.name if hasattr(key, 'name') else key

    def on_keyboard_release(self, key):
        self.input_keys.put(key, block=False)


if __name__ == '__main__':
    job = Manager()
    job.start()
