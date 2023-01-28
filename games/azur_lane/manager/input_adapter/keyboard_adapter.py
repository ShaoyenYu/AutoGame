from pynput import keyboard


class KeyboardInputMixin:
    MSG_EXIT_PROGRAM = 0

    MSG_CAN_RUN_AFTER_BATTLE = 1
    MSG_CAN_RUN = 2

    def __init__(self, queue=None):
        self.queue = queue
        self.keyboard_listener = keyboard.Listener(on_release=self._on_keyboard_release)

    def _on_keyboard_release(self, key):
        if key is keyboard.Key.f9:
            self._put_message(self.MSG_CAN_RUN_AFTER_BATTLE)
        elif key is keyboard.Key.f10:
            self._put_message(self.MSG_CAN_RUN)

    def _put_message(self, message):
        self.queue.put(message)

    def subscribe_to(self, queue):
        self.queue = queue

    def start(self, queue=None):
        if queue is not None:
            self.subscribe_to(queue)
        self.keyboard_listener.start()

    def close(self):
        self.queue.put(self.MSG_EXIT_PROGRAM)
        self.keyboard_listener.stop()
