class List(object):

    def __init__(self, items=[], listeners=[]):
        self.items = items
        self.listeners = listeners

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def _notify(self):
        for o in self.listeners:
            o.list_changed(self)

    def add_listener(self, o):
        self.listeners.append(o)

    def set_list(self, items):
        self.items = items
        self._notify()


class Path(object):

    def __init__(self):
        self.list = [ ]

    def push(self, s):
        self.list.append(s)

    def pop(self):
        if len(self.list) > 0:
            del self.list[-1]

    def __str__(self):
        return "/".join(self.list)


class Browser(List):

    def __init__(self):
        super(Browser, self).__init__(["Albums", "Singles", "Mixes"])


class Playlist(List):

    def __init__(self):
        super(Playlist, self).__init__()
        self.version = 0

    def set_list(self, items, version):
        self.items = items
        self.version = version
        self._notify()
