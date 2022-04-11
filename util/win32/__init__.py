import win32api
import win32con
import win32gui
import win32ui

# Get type PyCDC
_hwDC = win32gui.CreateDC("DISPLAY", None, None)
_DC = win32ui.CreateDCFromHandle(_hwDC)
T_PyCDC = type(_DC)
_DC.DeleteDC()
del _hwDC, _DC
