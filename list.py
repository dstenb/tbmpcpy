class List(object):

    def __init__(self, items=[], listeners=[]):
        self.items = items
        self.real_items = items
        self.listeners = listeners
        self.sel = -1
        self.search_mode = False

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def _fix_sel(self):
        if len(self) > 0:
            self.sel = min(max(0, self.sel), len(self) - 1)
        else:
            self.sel = -1

    def _handle_set(self):
        pass

    def _notify(self):
        for o in self.listeners:
            o.list_changed(self)

    def _notify_search_started(self):
        for o in self.listeners:
            o.list_search_started(self)

    def _notify_search_stopped(self):
        for o in self.listeners:
            o.list_search_stopped(self)

    def _notify_selected(self):
        for o in self.listeners:
            o.list_selected_changed(self)

    def add_listener(self, o):
        self.listeners.append(o)

    def _search(self):
        pass

    def _search_start(self, s):
        self.search_mode = True
        self.search_string = s
        self.set_list(self.real_items)
        self._notify_search_started()

    def _search_stop(self):
        self.search_mode = False
        self.set_list(self.real_items)
        self._notify_search_stopped()

    def search(self, s):
        if s == None:
            self._search_stop()
        else:
            self._search_start(s)

    def set_list(self, items):
        self.real_items = items

        if self.search_mode:
            self.items = self._search()
        else:
            self.items = self.real_items
        self._fix_sel()
        self._handle_set()
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


class ListListener(object):

    def list_changed(self, o):
        pass

    def list_selected_changed(self, o):
        pass

    def list_search_started(self, o):
        pass

    def list_search_stopped(self, o):
        pass
