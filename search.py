from common import Listenable
from list import *
from ui import *


class Search(Listenable):

    def __init__(self):
        super(Search, self).__init__()
        self.buf = ""
        self.active = False
        self.found = False

    def _set(self, buf):
        self.buf = buf
        self.active = len(self.buf) > 0

    def add(self, ch):
        self._set(self.buf + ch)

    def clear(self):
        self._set("")

    def remove_last(self):
        self._set(self.buf[:-1])


class PlaylistSearch(Search, ListListener):

    def __init__(self, playlist):
        super(PlaylistSearch, self).__init__()
        self.playlist = playlist
        self.playlist.add_listener(self)

    def _set(self, buf):
        super(PlaylistSearch, self)._set(buf)
        if self.playlist != None:
            self.playlist.search(self.buf or None)

    def _update(self):
        self.found = len(self.playlist) > 0
        self.notify("search_changed")

    def list_changed(self, unused):
        self._update()

    def list_search_started(self, unused):
        self._update()

    def list_search_stopped(self, unused):
        self._update()


class SearchUI(Component):

    def __init__(self, tb):
        super(SearchUI, self).__init__(tb)
        self.search = None
        self.lines = []

    def draw(self):
        fg = termbox.WHITE
        if self.search and not self.search.found:
            fg = termbox.RED
        for y, l in enumerate(self.lines):
            f = Format()
            f.add(l, fg, termbox.BLACK)
            self.change_cells_format(0, y, f)

    def fix_cursor(self):
        if self.visible:
            self.tb.set_cursor(len(self.lines[-1]), self.y + self.h - 1)
        else:
            self.tb.hide_cursor()

    def fix_height(self):
        self.set_pref_dim(-1, len(self.lines))

    def _update(self):
        line = "/" + self.search.buf
        self.lines = [line[i:i + self.w] for i in range(0, len(line), self.w)]
        self.fix_height()
        self.fix_cursor()

    def set_search(self, search):
        if self.search != None:
            self.search.remove_listener(self)
        self.search = search
        self.search.add_listener(self)

    def search_changed(self):
        self._update()
