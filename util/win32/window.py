import time
from typing import Optional, Tuple

import cv2 as cv
import numpy as np
import pywintypes
from PIL import Image

from util.win32 import T_PyCDC, win32api, win32gui, win32con, win32ui
from util.win32.datatypes import Rect


def parse_rgb_int2tuple(rgb_int: int):
    return rgb_int & 0xff, (rgb_int >> 8) & 0xff, (rgb_int >> 16) & 0xff


def parse_rgb_tuple2int(rgb_tuple: tuple):
    return rgb_tuple[0] | rgb_tuple[1] << 8 | rgb_tuple[2] << 16


def get_pixel(hwnd_dc: int, x, y, as_int=False):
    rgb_int = win32gui.GetPixel(hwnd_dc, x, y)
    if as_int:
        return rgb_int
    return parse_rgb_int2tuple(rgb_int)


def create_data_bitmap(x, y, width, height, dc: T_PyCDC, cdc: T_PyCDC = None):
    """

    Args:
        x: int
            left-top coordinate
        y: int
            left-top coordinate
        width: int
            width of rectangle to capture
        height: int
            height to rectangle to capture
        dc: PyCDC
            source device context
        cdc: PyCDC
            compatible device context to copy bit data into;

    Returns:

    """
    if cdc is None:
        cdc = dc.CreateCompatibleDC()

    data_bitmap = win32ui.CreateBitmap()  # create monochrome bitmaps, should call DeleteObject when it's no longer used
    data_bitmap.CreateCompatibleBitmap(dc, width, height)  # create color bitmaps

    # The SelectObject function selects an object into the specified device context (DC).
    # The new object replaces the previous object of the same type.
    cdc.SelectObject(data_bitmap)
    cdc.BitBlt((0, 0), (width, height), dc, (x, y), win32con.SRCCOPY)

    return data_bitmap


def image_from_bitmap(bitmap, form="array"):
    """
    Decode image from bitarray, the result can be formed as PIL Image or an Numpy array.

    Args:
        bitmap:
        form: str, optional {"image", "array"}

    Returns:

    """
    bitmap_w, bitmap_height = ((_ := bitmap.GetInfo())[k] for k in ("bmWidth", "bmHeight"))

    if form == "array":
        # BGRX to RGB
        image_array = cv.cvtColor(
            np.frombuffer(bitmap.GetBitmapBits(True), dtype="uint8").reshape(bitmap_height, bitmap_w, 4),
            cv.COLOR_BGR2RGB,
        )
        return image_array

    elif form == "image":
        image = Image.frombuffer(
            "RGB", (bitmap_w, bitmap_height), bitmap.GetBitmapBits(True), 'raw', *('BGRX', 0, 1)
        )
        return image
    raise NotImplementedError


def screenshot(src_dc, dst_dc, x, y, width, height, form="array", save_path=None) -> Image:
    """

    Args:
        src_dc:
        dst_dc:
        x: int
            left-top x coordinate of source
        y: int
            left-top y coordinate of source
        width: int
            width to capture
        height: int
            height to capture
        form: str, optional {"array", "image"}
        save_path: str

    Returns:

    """

    data_bitmap = create_data_bitmap(x, y, width, height, src_dc, dst_dc)  # create bitmap

    image = image_from_bitmap(data_bitmap, form=form)  # generate image from bitmap

    if save_path:
        data_bitmap.SaveBitmapFile(dst_dc, save_path)

    win32gui.DeleteObject(data_bitmap.GetHandle())  # release bitmap after using
    return image


def screenshot_by_hwnd(hwnd, x, y, width, height, form="array", save_path=None) -> Image:
    """
    To store an image temporarily, your application must call CreateCompatibleDC to create a DC that is compatible with
    the current window DC. After you create a compatible DC, you create a bitmap with the appropriate dimensions by
    calling the CreateCompatibleBitmap function and then select it into this device context by calling the SelectObject
    function.

    After the compatible device context is created and the appropriate bitmap has been selected into it, you can capture
    the image. The BitBlt function captures images. This function performs a bit block transfer that is, it copies data
    from a source bitmap into a destination bitmap. However, the two arguments to this function are not bitmap handles.
    Instead, BitBlt receives handles that identify two device contexts and copies the bitmap data from a bitmap selected
    into the source DC into a bitmap selected into the target DC. In this case, the target DC is the compatible DC, so
    when BitBlt completes the transfer, the image has been stored in memory. To redisplay the image, call BitBlt a
    second time, specifying the compatible DC as the source DC and a window (or printer) DC as the target DC.

    Args:
        hwnd:
        x:
        y:
        width:
        height:
        form:
        save_path:

    Returns:

    """

    hwDC = win32gui.GetWindowDC(hwnd)
    DC = win32ui.CreateDCFromHandle(hwDC)
    cDC = DC.CreateCompatibleDC()

    img = screenshot(DC, cDC, width, height, x, y, form, save_path)

    DC.DeleteDC()
    cDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwDC)
    return img


class ScreenUtilityMixin:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.hw_dc: Optional[int] = None
        self.dc: T_PyCDC = None
        self.cdc: T_PyCDC = None

    def create_dc(self):
        self.hw_dc = win32gui.GetWindowDC(self.hwnd)  # use ReleaseDC after calling
        self.dc = win32ui.CreateDCFromHandle(self.hw_dc)  # use DeleteDC after calling
        self.cdc = self.dc.CreateCompatibleDC()  # use DeleteDC after calling

    def release_dc(self):
        try:
            self.dc.DeleteDC()
            self.cdc.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, self.hw_dc)
        except win32ui.error as e:
            print(f"{e}: dc: {self.dc}, cdc: {self.cdc}")

    def screenshot(self, x=0, y=0, width=None, height=None, form="array", save_path=None):
        self.create_dc()
        result = screenshot(self.dc, self.cdc, x, y, width, height, form, save_path)
        self.release_dc()
        return result

    def pixel_from_window(self, x, y, as_int=False):
        """

        Args:
            x: int
            y: int
            as_int: bool, default False
                If true, return rgb as an integer, of which the binary is 24-bit.

        Returns:

        """
        hw_dc = win32gui.GetWindowDC(self.hwnd)
        try:
            rgb = get_pixel(hw_dc, x, y, as_int)
        except pywintypes.error:  # this error occurs when using ALT + TAB, don't know how to fix.
            print("failed to get pixel, retrying...")
            win32gui.ReleaseDC(self.hwnd, hw_dc)
            time.sleep(.1)
            rgb = self.pixel_from_window(x, y, as_int)
        else:
            win32gui.ReleaseDC(self.hwnd, hw_dc)
        return rgb

    def pixel_from_image(self, image: np.ndarray, x, y, as_int=False):
        raise NotImplementedError


class MouseMixin:
    def __init__(self, hwnd):
        self.hwnd = hwnd

    def left_click(self, coordinate: Tuple[int, int], sleep=0):
        pos = win32api.MAKELONG(*coordinate)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, pos)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, pos)

        if sleep > 0:
            time.sleep(sleep)

    def left_drag(self, start, end, duration, interval=.05, sleep=0):
        """

        Args:
            start: Tuple[int, int]
                start position;
            end: Tuple[int, int]
                end position;
            duration: Union[float, int]
                total time to execute drag;
            interval: Union[float, int]
                interval to move mouse(should less than duration)

        Returns:

        """
        pos_start = pos_next = win32api.MAKELONG(*start)
        pos_end = win32api.MAKELONG(*end)

        offset_x, offset_y = end[0] - start[0], end[1] - start[1]
        cur_times, total_times = 0, int(duration // interval)
        remain_interval = duration - total_times * interval

        dx, dy = offset_x // total_times, offset_y // total_times

        dxy = dx + dy * (2 ** 16)  # transform x, y into 32-bit integer, higher 16 bit is y, and lower 16 bit is x.
        remain_xy = (offset_x % total_times) + (offset_y % total_times) * (2 ** 16)

        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, pos_start)
        for _ in range(total_times):
            pos_next += dxy
            win32api.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, pos_next)
            time.sleep(interval)

        if remain_xy > 0:
            pos_next += remain_xy
            win32api.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, pos_next)

        if remain_interval > 0:
            time.sleep(remain_interval)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, pos_end)

        if sleep > 0:
            time.sleep(sleep)


class Window(ScreenUtilityMixin, MouseMixin):
    def __init__(self, **kwargs):
        """

        Args:
            **kwargs:
                window_hwnd: int
                window_name: str
                window_pos: tuple[int, int]
        """
        if (window_handle := kwargs.get("window_hwnd")) is not None:
            self.hwnd = window_handle
        elif (window_name := kwargs.get("window_name")) is not None:
            self.hwnd = win32gui.FindWindow(0, window_name)
        elif (window_pos := kwargs.get("window_pos")) is not None:
            self.hwnd = win32gui.WindowFromPoint(window_pos)
        self.rect = None
        self.get_window_rect()

        ScreenUtilityMixin.__init__(self, self.hwnd)
        MouseMixin.__init__(self, self.hwnd)

    def get_window_text(self):
        return win32gui.GetWindowText(self.hwnd)

    def get_window_rect(self):
        self.rect = Rect(*win32gui.GetWindowRect(self.hwnd))
        return self.rect

    def set_window_pos(self, insert_after, x, y, cx, cy, flags):
        """

        Args:
            insert_after: PyHANDLE
                Window that hWnd will be placed below. Can be a window handle or one of HWND_BOTTOM,
                HWND_NOTOPMOST, HWND_TOP, or HWND_TOPMOST
            x: int
                New X coord
            y: int
                New Y coord
            cx: int
                New width of window
            cy: int
                New height of window
            flags:
                Combination of win32con.SWP_* flags

        Returns:

        """

        win32gui.SetWindowPos(self.hwnd, insert_after, x, y, cx, cy, flags)
        self.rect = self.get_window_rect()

    def screenshot(self, x=0, y=0, width=None, height=None, form="array", save_path=None):
        return super().screenshot(
            x, y, width or self.rect.width, height or self.rect.height,
            form,
            save_path
        )

    def __repr__(self):
        rect = self.get_window_rect()
        return f"{self.get_window_text()}[{self.hwnd}, {rect.width:<4}*{rect.height:<4}]"
