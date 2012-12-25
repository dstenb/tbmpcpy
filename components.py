#!/usr/bin/python
# -*- encoding: utf-8 -*-

import math

from command import *
from common import *
from status import *
from ui import *

# Progress bar formatting
marker_c, marker_e, marker_r = u"╼", u"─", u"·"
color_elapsed = (termbox.WHITE, termbox.BLACK)
color_remaining = (termbox.BLACK, termbox.BLACK)


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

    def message_changed(self, msg):
        self.show() if self.msg.has_message() else self.hide()


class ListUI(Component):

    def __init__(self, tb, list):
        super(ListUI, self).__init__(tb)
        self.list = list
        self.sel = 0
        self.start = 0

    def _fix_bounds(self):
        if len(self.list) > 0:
            self.sel = min(max(0, self.sel), len(self.list) - 1)
            if (self.sel - self.start) >= self.h:
                self.start = self.sel - self.h + 1
            if self.sel < self.start:
                self.start = self.sel
            self.start = min(max(0, self.start), len(self.list) - 1)

    def _format(self, o, y, p):
        s = "%5i %5i %s" % (p, y, str(o))
        return Format(s.ljust(self.w), termbox.RED if p == self.sel else
                termbox.WHITE)

    def draw(self):
        length = len(self.list)
        empty = Format("".ljust(self.w))
        for y in range(self.h):
            pos = y + self.start
            f = self._format(self.list[pos], y, pos) if y < length else empty
            self.change_cells_format(0, y, f)

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self._fix_bounds()

    def selected(self):
        return self.sel


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
        self.status.add_listener(self)

    def _format(self, song, y, pos):
        left, right = Format(), Format()

        numw = 0
        if len(self.list) > 0:
            numw = int(math.floor(math.log10(len(self.list)))) + 2
        num_str = "%s " % str(pos + 1)
        time_str = " [%s] " % length_str(song.time)
        left.add(num_str.rjust(numw + 1), termbox.BLUE, termbox.BLACK)
        left.add(song.artist, termbox.RED, termbox.BLACK)
        left.add(" - ", termbox.WHITE, termbox.BLACK)
        left.add(song.title, termbox.YELLOW, termbox.BLACK)
        left.add(" (", termbox.WHITE, termbox.BLACK)
        left.add(song.album, termbox.GREEN, termbox.BLACK)
        left.add(")", termbox.WHITE, termbox.BLACK)

        right.add(time_str, termbox.BLUE, termbox.BLACK)

        if pos == self.sel:
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

    def playlist_updated(self):
        if len(self.status.playlist) > 0 and self.sel == -1:
            self.start = self.sel = 0
        else:
            self.start = self.sel = -1
        self._fix_bounds()


class CurrentSongUI(Component, StatusListener):

    def __init__(self, tb, status):
        super(CurrentSongUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        status.add_listener(self)

        self.state_changed(status.state)

    def draw(self):
        c = (termbox.WHITE, termbox.BLACK)
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
                self.sel = min(max(0, self.sel), len(self.matched) - 1)
                if (self.sel - self.start) >= self.h:
                    self.start = self.sel - self.h + 1
                if self.sel < self.start:
                    self.start = self.sel
                self.start = min(max(0, self.start), len(self.matched) - 1)

        def format(self):
            length = len(self.matched)
            empty = Format("".ljust(self.w))
            for y in range(self.h):
                pos = y + self.start
                f = Format()
                if y < length:
                    f.add("%3i %s (%s)" % ((pos + 1),
                        self.matched[pos][0],
                        str(self.matched[pos][1].description
                            if self.matched[pos][1] else "None")),  #TODO
                        termbox.WHITE, termbox.BLACK)
                    if pos == self.sel:
                        f.set_color(termbox.BLACK, termbox.WHITE)
                        f.set_bold()
                    yield f

        def select(self, index, rel=False):
            if rel:
                self.sel += index
            else:
                self.sel = index
            self._fix_bounds()

    def __init__(self, tb, command):
        super(CommandLineUI, self).__init__(tb)
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.command = command
        self.matched = None
        self.matchedw = None

    def draw(self):
        if self.matchedw:
            #FUGLY
            for i, f in enumerate(self.matchedw.format()):
                self.change_cells_format(0, i, f)
        c = (termbox.WHITE, termbox.BLACK)
        f = Format()
        f.add(":%s" % self.cl.buf, *c)
        self.change_cells_format(0, self.h - 1, f)

    def matched_changed(self, cl):
        if self.cl.matched:
            self.matchedw = self.MatchedWin(self.tb, self.cl.matched)
            self.set_pref_dim(-1, self.matchedw.h + 1)
        else:
            self.matchedw = None
            self.set_pref_dim(-1, 1)
        pass

    def matched_selected_changed(self, cl):
        self.matchedw.select(self.cl.matched_pos)
