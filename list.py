from common import Listenable


class List(Listenable):

    def __init__(self, items=[]):
        super(List, self).__init__()
        self.items = items
        self.real_items = items
        self.sel = -1
        self.search_mode = False
        self.search_string = ""

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

    def _search(self):
        pass

    def _search_start(self, s):
        self.search_mode = True
        self.search_string = s
        self.set_list(self.real_items)
        self.notify("list_search_started", self)

    def _search_stop(self):
        self.search_mode = False
        self.set_list(self.real_items)
        self.notify("list_search_stopped", self)

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
        self.notify("list_changed", self)

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self._fix_sel()
        self.notify("list_selected_changed", self)

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
