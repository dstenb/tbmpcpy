import time

def time_in_millis():
    return int(round(time.time() * 1000))


class Listenable(object):
   
    def __init__(self):
        self.listeners = []

    def add_listener(self, o):
        if not o in self.listeners:
            self.listeners.append(o)

    def clear_listeners(self):
        self.listeners = []

    def remove_listener(self, o):
        if o in self.listeners:
            self.listeners.remove(o)

    def notify(self, func, *args):
        for o in self.listeners:
            getattr(o, func)(*args)


class Message(Listenable):

    def __init__(self):
        super(Message, self).__init__()
        self._clear()

    def has_message(self):
        return self.text != None

    def _set(self, text, level, timeout, timestamp):
        assert timeout > 0
        assert level in ["info", "warning", "error"]

        self.text = text
        self.level = level
        self.timeout = timeout
        self.timestamp = timestamp
        self.notify("message_changed", self)

    def _clear(self):
        self.text, self.level, self.timeout, self.timestamp = None, None, 0, 0
        self.notify("message_changed", self)

    def info(self, text, timeout):
        self._set(text, "info", timeout, time_in_millis())

    def warning(self, text, timeout):
        self._set(text, "warning", timeout, time_in_millis())

    def error(self, text, timeout):
        self._set(text, "error", timeout, time_in_millis())

    def update(self, time):
        if self.has_message():
            if (time - self.timestamp) >= self.timeout * 1000:
                self._clear()


class MessageListener(object):

    def message_changed(self, msg):
        pass
