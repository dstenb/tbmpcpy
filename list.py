class List(object):

    def __init__(self, items=[], listeners=[]):
        self.items = items
        self.listeners = listeners
        self.sel = -1

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def _fix_sel(self):
        if len(self) > 0:
            self.sel = min(max(0, self.sel), len(self) - 1)
        else:
            self.sel = -1

    def _notify(self):
        for o in self.listeners:
            o.list_changed(self)

    def _notify_selected(self):
        for o in self.listeners:
            o.list_selected_changed(self)

    def add_listener(self, o):
        self.listeners.append(o)

    def set_list(self, items):
        self.items = items
        self._fix_sel()
        self._notify()

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self._fix_sel()
        self._notify_selected()

    def selected(self):
        if self.sel >= 0:
            return self.items[self.sel]
        return None

    def selected_index(self):
        return self.sel


class ListListener(object):

    def list_changed(self, o):
        pass

    def list_selected_changed(self, o):
        pass
