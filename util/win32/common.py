import win32api
import win32clipboard
import win32con


def set_text(string):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, string)
    win32clipboard.CloseClipboard()


def paste():
    # keydown
    win32api.keybd_event(17, 0, 0, 0)  # ctrl: 17
    win32api.keybd_event(86, 0, 0, 0)  # v: 86

    # release
    win32api.keybd_event(86, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(17, 0, win32con.KEYEVENTF_KEYUP, 0)
