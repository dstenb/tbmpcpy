#!/usr/bin/python
# -*- encoding: utf-8 -*-

import math

from browser import *
from command import *
from common import *
from status import *
from ui import *

# Progress bar formatting
marker_c, marker_e, marker_r = u"╼", u"─", u"·"
color_elapsed = (termbox.WHITE, termbox.BLACK)
color_remaining = (termbox.BLACK, termbox.BLACK)


class MainComponent(Component):

    def __init__(self, tb, islist=False):
        super(MainComponent, self).__init__(tb)
        self.islist = islist

    def is_list(self):
        return self.islist

    def select(self, index, rel=False):
        if self.is_list():
            self.list.select(index, rel)

    def selected(self):
        if self.is_list():
            return self.list.selected()
        return None

    def search_start(self, d):
        if self.is_list():
            return self._search_start(d)
        return None  # TODO raise exception for debugging

    def search_next(self):
        if self.is_list():
            return self._search_next()
        return None  # TODO raise exception for debugging

    def search_prev(self):
        if self.is_list():
            return self._search_prev()
        return None  #TODO raise exception for debugging


class ProgressBarUI(Component, StatusListener):

    def __init__(self, tb, status):
        super(ProgressBarUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        status.add_listener(self)

    def draw(self):
        elapsed = self.status.progress.elapsed()
        if elapsed >= 0 and elapsed <= 1:
            self.change_cells_format(0, 0, self._format_playing(elapsed))
        else:
            self.change_cells_format(0, 0, self._format_stopped())

    def _format_playing(self, elapsed):
        ew = max(0, int(elapsed * self.w))
        f = Format()
        f.add(marker_c.rjust(ew, marker_e), *color_elapsed)
        f.add(u"".ljust(self.w - ew, marker_r), *color_remaining)
        f.set_bold()
        return f

    def _format_stopped(self):
        f = Format()
        f.add(u"".ljust(self.w, marker_r), *color_remaining)
        f.set_bold()
        return f


class MessageUI(Component, MessageListener):

    def __init__(self, tb, msg):
        super(MessageUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.msg = msg
        self.msg.add_listener(self)

    def get_colors(self):
        colors = {"info": (termbox.WHITE, termbox.BLACK),
                "warning": (termbox.YELLOW, termbox.BLACK),
                "error": (termbox.RED, termbox.BLACK)}
        return colors[self.msg.level]

    def text(self):
        prefix = {"info": "Info", "warning": "Warning", "error": "Error"}
        return " %s: %s" % (prefix[self.msg.level], self.msg.text)

    def draw(self):
        if self.msg.has_message():
            f = Format()
            f.add(self.text(), *self.get_colors())
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

    def _format(self, o, y, p):
        s = "%5i %5i %s" % (p, y, str(o))
        return Format(s.ljust(self.w), termbox.RED if p == self.list.sel else
                termbox.WHITE)

    def draw(self):
        length = len(self.list)
        empty = Format("".ljust(self.w))
        for y in range(self.h):
            pos = y + self.start
            f = self._format(self.list[pos], y, pos) if y < length else empty
            self.change_cells_format(0, y, f)

    def list_changed(self, l):
        self._fix_bounds()

    def list_selected_changed(self, l):
        self._fix_bounds()


def length_str(time):
    m = time / 60
    s = time % 60

    if m <= 0:
        return "--:--"
    elif m > 99:
        return str(m) + "m"
    return str(m).zfill(2) + ":" + str(s).zfill(2)


class PlaylistUI(ListUI, StatusListener):

    def __init__(self, tb, status):
        super(PlaylistUI, self).__init__(tb, status.playlist)
        self.status = status
        self.list.add_listener(self)

    def _format(self, song, unused_y, pos):
        left, right = Format(), Format()

        numw = 0
        if len(self.list) > 0:
            numw = int(math.floor(math.log10(len(self.list)))) + 2
        left.add(str(pos + 1).rjust(numw), termbox.BLUE, termbox.BLACK)
        left.add(" %s - %s (%s)" % (song.artist, song.title, song.album),
                termbox.WHITE, termbox.BLACK)
        right.add(" [%s]" % length_str(song.time), termbox.BLUE, termbox.BLACK)

        if pos == self.list.sel:
            left.set_color(termbox.BLACK, termbox.WHITE)
            right.set_color(termbox.BLACK, termbox.WHITE)
            left.add("".ljust(max(0, self.w - len(left.s))),
                    termbox.BLACK, termbox.WHITE)
        if song is self.status.current:
            left.set_bold()
            right.set_bold()
            left.replace(0, ">", termbox.BLUE, termbox.BLACK)
        return left, right

    def draw(self):
        length = len(self.list)
        for y in range(self.h):
            pos = y + self.start
            if pos < length:
                left, right = self._format(self.list[pos], y, pos)
                self.change_cells_format(0, y, left)
                self.change_cells_format(self.w - len(right.s), y, right)


class BrowserUI(ListUI, ListListener):

    def __init__(self, tb, browser):
        super(BrowserUI, self).__init__(tb, browser)
        self.list.add_listener(self)

    def _format(self, song, unused_y, pos):
        f = Format()

        numw = 0
        if len(self.list) > 0:
            numw = int(math.floor(math.log10(len(self.list)))) + 2
        num_str = "%s " % str(pos + 1)
        f.add(num_str.rjust(numw + 1), termbox.BLUE, termbox.BLACK)
        f.add(unicode(song), termbox.WHITE, termbox.BLACK)

        if pos == self.list.sel:
            f.set_color(termbox.BLACK, termbox.WHITE)
            f.add("".ljust(max(0, self.w - len(f.s))),
                    termbox.BLACK, termbox.WHITE)
        return f


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
        state_dict = {"play":  u">", "stop": "[]", "pause": u"||"}
        f.add(" " + state_dict.get(self.status.state, ""),
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
            for y in range(self.h):
                pos = y + self.start
                f = Format()
                if y < length:
                    def format_desc(d):
                        return "(" + d + ")" if d else ""
                    f.add("%3i " % (pos + 1), termbox.BLUE, termbox.BLACK)
                    f.add("%s " % self.matched[pos].name,
                            termbox.WHITE, termbox.BLACK)
                    f.add(format_desc(self.matched[pos].description),
                        termbox.WHITE, termbox.BLACK)
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
            self.tb.set_cursor(len(self.lines[-1]), self.y + self.h -1)
        else:
            self.tb.hide_cursor()

    def fix_height(self):
        h = self.matchedw.h if self.matchedw else 0
        h += len(self.lines)
        self.set_pref_dim(-1, h)

    def line_changed(self, unused_cl):
        line = ":" + self.cl.buf
        self.lines = [line[i:i+self.w] for i in range(0, len(line), self.w)]
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
