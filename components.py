#!/usr/bin/python
# -*- encoding: utf-8 -*-

import math

from config import *

from browser import *
from command import *
from common import *
from status import *
from ui import *

from sys import maxsize

class MainComponent(Component):

    def __init__(self, tb, islist=False):
        super(MainComponent, self).__init__(tb)
        self.islist = islist

    def is_list(self):
        return self.islist

    def search(self, s):
        pass

    def select(self, index, rel=False):
        pass

    def selected(self):
        pass


class ProgressBarUI(Component, StatusListener):

    def __init__(self, tb, status):
        super(ProgressBarUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        self.status.add_listener(self)

    def draw(self):
        elapsed = self.status.progress.elapsed()
        if elapsed >= 0 and elapsed <= 1:
            self.change_cells_format(0, 0, self._format_playing(elapsed))
        else:
            self.change_cells_format(0, 0, self._format_stopped())

    def _format_playing(self, elapsed):
        ew = max(0, int(elapsed * self.w))
        f = Format()
        f.add(symbol_progress_c.rjust(ew, symbol_progress_e),
                *color_progress_elapsed)
        f.add(u"".ljust(self.w - ew, symbol_progress_r),
                *color_progress_remaining)
        f.set_bold()
        return f

    def _format_stopped(self):
        f = Format()
        f.add(u"".ljust(self.w, symbol_progress_r), *color_progress_remaining)
        f.set_bold()
        return f


class MessageUI(Component, MessageListener):

    def __init__(self, tb, msg):
        super(MessageUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.msg = msg
        self.msg.add_listener(self)

    def text(self):
        return " %s: %s" % (text_msg_prefix[self.msg.level], self.msg.text)

    def draw(self):
        if self.msg.has_message():
            f = Format()
            f.add(self.text(), *color_msg[self.msg.level])
            self.change_cells_format(0, 0, f)

    def message_changed(self, unused_msg):
        self.show() if self.msg.has_message() else self.hide()


class ListUI(MainComponent, ListListener):

    def __init__(self, tb, list):
        super(ListUI, self).__init__(tb, True)
        self.list = list
        self.start = 0

    def _fix_bounds(self):
        if len(self.list) > 0:
            if (self.list.sel - self.start) >= self.h:
                self.start = self.list.sel - self.h + 1
            if self.list.sel < self.start:
                self.start = self.list.sel
            self.start = min(max(0, self.start), len(self.list) - 1)

    def _handle_resize(self):
        self._fix_bounds()

    def draw(self):
        length = len(self.list)
        empty = Format("".ljust(self.w))
        for y in xrange(self.h):
            p = y + self.start
            f = self._format(self.list[p], y, p) if p < length else empty
            self.change_cells_format(0, y, f)

    def list_changed(self, l):
        self._fix_bounds()

    def list_selected_changed(self, l):
        self._fix_bounds()

    def search(self, s):
        self.list.search(s)

    def select(self, index, rel=False):
        self.list.select(index, rel)

    def selected(self):
        return self.list.selected()


def playtime_str(time):
    return ", ".join(filter(lambda s: not s.startswith("0"),
            ["%i days" % (time / (24 * 60 * 60)),
            "%i hours" % (time / (60 * 60) % 24),
            "%i minutes" % (time / 60 % 60),
            "%i seconds" % (time % (60))]))


class PlaylistUI(ListUI, StatusListener):

    def __init__(self, tb, status):
        super(PlaylistUI, self).__init__(tb, status.playlist)
        self.status = status
        self.list.add_listener(self)

    def draw(self):
        length = len(self.list)
        numw = 0
        if length > 0:
            numw = int(math.floor(math.log10(len(self.list)))) + 2
        for y in xrange(self.h):
            pos = y + self.start
            if pos < length:
                left, right = format_playlist_song(self.list[pos], pos,
                        pos == self.list.sel,
                        self.list[pos] == self.status.current,
                        self.w, numw)
                self.change_cells_format(0, y, left)
                self.change_cells_format(self.w - len(right.s), y, right)

    def list_search_started(self, unused_ref):
        pass

    def list_search_stopped(self, unused_ref):
        pass


class TextComponent(MainComponent):

    def __init__(self, tb, tlist):
        super(TextComponent, self).__init__(tb, False)
        self.tlist = tlist
        self.start = 0

    def _fix_bounds(self):
        if len(self.tlist) > 0:
            self.start = max(0, min((len(self.tlist) - self.h, self.start)))

    def _handle_resize(self):
        self._fix_bounds()

    def _format(self, i, y, p):
        f = Format()
        f.add("%i " % p, termbox.YELLOW, termbox.BLACK)
        f.add(i, termbox.WHITE, termbox.BLACK)
        return f

    def draw(self):
        length = len(self.tlist)
        empty = Format("".ljust(self.w))
        for y in xrange(self.h - 1):
            p = y + self.start
            f = self._format(self.tlist[p], y, p) if p < length else empty
            self.change_cells_format(0, y, f)
        # TODO

    def set_start(self, start, rel=False):
        self.start = (self.start + start) if rel else start
        self._fix_bounds()


class BrowserBar(Component, BrowserListener):

    def __init__(self, tb, browser):
        super(BrowserBar, self).__init__(tb)
        self.browser = browser
        self.browser.add_listener(self)

    def draw(self):
        f = Format()
        f.add(" Browse > ", termbox.WHITE | termbox.BOLD, termbox.BLACK)
        if self.browser.search_active():
            f.add("Filter: ", termbox.WHITE, termbox.BLACK)
            if len(self.node) > 0:
                f.add(self.node.string, termbox.WHITE, termbox.BLACK)
            else:
                f.add(self.node.string, termbox.RED, termbox.BLACK)
        else:
            f.add(self.browser.path_str(" > "), termbox.WHITE, termbox.BLACK)
        self.change_cells_format(0, 0, f)

    def browser_node_changed(self, browser):
        self.node = self.browser.curr_node

    def browser_search_started(self, browser):
        self.node = self.browser.curr_node

    def browser_search_stopped(self, browser):
        self.node = self.browser.curr_node


class PlaylistBar(Component, ListListener):

    def __init__(self, tb, playlist):
        super(PlaylistBar, self).__init__(tb)
        self.playlist = playlist
        self.playlist.add_listener(self)
        self.length_str = ""
        self.search_active = False
        self.search_string = ""

    def draw(self):
        f = Format()
        f.add(" Playlist ", termbox.WHITE | termbox.BOLD, termbox.BLACK)
        if self.search_active:
            f.add("Filter: ", termbox.WHITE, termbox.BLACK)
            if len(self.playlist) > 0:
                f.add(self.search_string, termbox.WHITE, termbox.BLACK)
            else:
                f.add(self.search_string, termbox.RED, termbox.BLACK)
        else:
            f.add(self.length_str, termbox.WHITE, termbox.BLACK)
        self.change_cells_format(0, 0, f)

    def list_changed(self, unused_list):
        self.length_str = "(%i items" % len(self.playlist)
        if self.playlist.playtime > 0:
            self.length_str += ", %s)" % playtime_str(self.playlist.playtime)
        else:
            self.length_str += ")"

    def list_search_started(self, unused_list):
        self.search_active = True
        self.search_string = self.playlist.search_string

    def list_search_stopped(self, unused_list):
        self.search_active = False


class BrowserUI(MainComponent, BrowserListener):

    def __init__(self, tb, browser):
        super(BrowserUI, self).__init__(tb, True)
        self.browser = browser
        self.browser.add_listener(self)
        self.start = 0
        self.node = None

    def _fix_bounds(self):
        if len(self.node) > 0:
            if (self.node.sel - self.start) >= self.h:
                self.start = self.node.sel - self.h + 1
            if self.node.sel < self.start:
                self.start = self.node.sel
            self.start = min(max(0, self.start), len(self.node) - 1)

    def _handle_resize(self):
        self._fix_bounds()

    def draw(self):
        if not self.node:
            return
        length = len(self.node)
        numw = 0
        if length > 0:
            numw = int(math.floor(math.log10(len(self.node)))) + 2
        empty = Format("".ljust(self.w))
        for y in xrange(self.h):
            pos = y + self.start
            if pos < length:
                f = format_browser_item(self.node[pos], pos,
                        pos == self.node.sel, self.w, numw)
                self.change_cells_format(0, y, f)

    def browser_node_changed(self, browser):
        self.node = self.browser.curr_node
        self._fix_bounds()

    def browser_selected_changed(self, browser):
        self._fix_bounds()

    def browser_search_started(self, browser):
        self.node = self.browser.curr_node
        self._fix_bounds()

    def browser_search_stopped(self, browser):
        self.node = self.browser.curr_node
        self._fix_bounds()

    def search(self, s):
        self.browser.search(s)

    def select(self, index, rel=False):
        self.browser.select(index, rel)

    def selected(self):
        return self.browser.selected()


class CurrentSongUI(Component, StatusListener):

    def __init__(self, tb, status):
        super(CurrentSongUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        status.add_listener(self)

        self.state_changed(status.state)

    def draw(self):
        song_line = self._song_format(self.status.current)
        self.change_cells_format(0, 0, song_line)

    def _song_format(self, song):
        f = Format()
        f.add(" " + symbol_player_states.get(self.status.state, ""),
                termbox.WHITE, termbox.BLACK)
        if song:
            f.add(" %s - %s - %s" % (song.artist, song.title, song.album),
                    termbox.WHITE, termbox.BLACK)
        return f

    def state_changed(self, s):
        self.show() if s in ["play", "pause"] else self.hide()


class CommandLineUI(Component, CommandLineListener):

    # TODO: sub of component
    class MatchedWin(object):

        def __init__(self, tb, matched, maxh=5):
            self.tb = tb
            self.matched = matched
            self.start = 0
            self.sel = 0
            self.h = min(maxh, len(matched))
            self.w = tb.width()

        def _fix_bounds(self):
            if len(self.matched) > 0:
                if self.sel < 0:
                    self.sel = -1
                    self.start = 0
                else:
                    self.sel = min(self.sel, len(self.matched) - 1)
                    if (self.sel - self.start) >= self.h:
                        self.start = self.sel - self.h + 1
                    if self.sel < self.start:
                        self.start = self.sel
                    self.start = min(max(0, self.start),
                            len(self.matched) - 1)

        def format(self):
            length = len(self.matched)
            empty = Format("".ljust(self.w))
            for y in xrange(self.h):
                pos = y + self.start
                f = Format()
                if y < length:
                    def format_desc(d):
                        return "(" + d + ")" if d else ""
                    f.add("%3i " % (pos + 1), *color_cmdline_number)
                    f.add("%s " % self.matched[pos].name,
                            *color_cmdline_name)
                    f.add(format_desc(self.matched[pos].description),
                            *color_cmdline_description)
                    if pos == self.sel:
                        f.set_bold()
                    yield f

        def select(self, index):
            self.sel = index
            self._fix_bounds()

    def __init__(self, tb, command):
        super(CommandLineUI, self).__init__(tb)
        self.command = command
        self.matched = None
        self.matchedw = None
        self.cl = None
        self.lines = [":"]
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)

    def draw(self):
        if self.matchedw:
            clh = self.matchedw.h
            for i, f in enumerate(self.matchedw.format()):
                self.change_cells_format(0, i, f)
        else:
            clh = 0
        for y, l in enumerate(self.lines, clh):
            f = Format()
            f.add(l, termbox.WHITE, termbox.BLACK)
            self.change_cells_format(0, y, f)

    def fix_cursor(self):
        if self.visible:
            self.tb.set_cursor(len(self.lines[-1]), self.y + self.h - 1)
        else:
            self.tb.hide_cursor()

    def fix_height(self):
        h = self.matchedw.h if self.matchedw else 0
        h += len(self.lines)
        self.set_pref_dim(-1, h)

    def line_changed(self, unused_cl):
        line = ":" + self.cl.buf
        self.lines = [line[i:i + self.w] for i in range(0, len(line), self.w)]
        self.fix_height()
        self.fix_cursor()

    def matched_changed(self, unused_cl):
        if self.cl.matched:
            self.matchedw = self.MatchedWin(self.tb, self.cl.matched)
            self.set_pref_dim(-1, self.matchedw.h + 1)
        else:
            self.matchedw = None
            self.set_pref_dim(-1, 1)

    def matched_selected_changed(self, unused_cl):
        self.matchedw.select(self.cl.matched.pos)

    def set_command_line(self, cl):
        if self.cl:
            self.cl.remove_listener(self)
        self.cl = cl
        self.cl.add_listener(self)

    def set_dim(self, x, y, w, h, set_stored=True, notify=True):
        if self.matchedw:
            self.matchedw.w = w
        super(CommandLineUI, self).set_dim(x, y, w, h, set_stored, notify)
