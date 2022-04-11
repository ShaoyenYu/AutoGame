import ctypes
import inspect
import threading
from typing import Iterable, Union, Optional, Tuple


class KillableThread(threading.Thread):
    @staticmethod
    def _async_raise(tid, exctype):
        """raises the exception, performs cleanup if needed"""
        if not inspect.isclass(exctype):
            raise TypeError("Only types can be raised (not instances)")
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def _get_my_tid(self):
        """determines this (self's) thread id"""
        if not self.is_alive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """raises the given exception type in the context of this thread"""
        self._async_raise(self._get_my_tid(), exctype)

    def terminate(self):
        """raises SystemExit in the context of the given thread, which should
        cause the thread to exit silently (unless caught)"""
        self.raise_exc(SystemExit)


class PauseEventHandler:
    def __init__(self, *event_names):
        self.events = {}
        self.set_events(*event_names)

    def set_events(self, *event_names):
        for event_name in event_names:
            self.events[event_name] = threading.Event()

    def _broadcast(self, names=None, target=None, reverse=False):
        if isinstance(target, bool) and reverse:
            raise ValueError

        for name, event in self._iter(names):
            event.clear() if ((target is False) or (reverse & event.is_set())) else event.set()
            print(f"set {name} --> {event.is_set()}")

    def _iter(self, names: Optional[Union[str, Iterable[str]]]) -> Iterable[Tuple[str, threading.Event]]:
        if names is None:
            it = iter(self.events.items())
        elif isinstance(names, str):
            it = iter([(names, self.events[names])])
        elif isinstance(names, Iterable):
            it = ((name, self.events[name]) for name in names)
        else:
            raise ValueError
        return it

    def pause(self, names=None):
        return self._broadcast(names, False)

    def resume(self, names=None):
        return self._broadcast(names, True)

    def reverse(self, names=None):
        return self._broadcast(names, reverse=True)

    def wait(self, names=None, timeout: Optional[float] = None):
        for _, event in self._iter(names):
            event.wait(timeout=timeout)
