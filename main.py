#!/usr/bin/python
# -*- encoding: utf-8 -*-


import sys
import termbox
import time
import traceback

from mpd import (MPDClient, CommandError)
from socket import error as SocketError

from ui import *
from playlist import *
from status import *


UPDATE_RATE = 2000


def time_in_millis():
    return int(round(time.time() * 1000))


def length_str(time):
    m = time / 60
    s = time % 60

    if m > 99:
        return str(m) + "m"
    return str(m).zfill(2) + ":" + str(s).zfill(2)


class PlaylistUI(Drawable, StatusListener):

    def __init__(self, tb, pl):
        self.tb = tb
        self.pl = pl
        self.sel = None
        self.start = None
        self.song = None

    def draw(self):
        l = len(self.pl)

        for y in range(self.h):
            c = [termbox.WHITE, termbox.BLACK]
            if y == self.sel:
                c = [termbox.BLACK, termbox.WHITE]
            if y < l:
                # TODO
                song = self.pl[y]
                if song == self.pl.current:
                    c[0] |= termbox.BOLD
                line = " " + song.artist + " - " + song.title + " "
                line += "(" + song.album + ")"
                line = unicode(line, "utf-8")
                right = "[" + length_str(song.time).rjust(5) + "]"
                self.change_cells(0, y, line, c[0], c[1], self.w - 9)
                self.change_cells(self.w - 8, y, right, c[1], c[0])
            else:
                self.change_cells(0, y, "", c[0], c[1], self.w)

    def fix_bounds(self):
        self # TODO

    def current_changed(self, song):
        self.fix_bounds()

    def playlist_updated(self):
        self.fix_bounds()


class CurrentSongUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.song = None
        status.add_listener(self)

    def current_changed(self, song):
        self.song = song

    def draw(self):
        c = ( termbox.BLACK, termbox.GREEN)
        line = ""
        if self.song:
            line = " " + self.song.artist + " - "
            line += self.song.album + " - " + self.song.title
            line = unicode(line, "utf-8")
        self.change_cells(0, 0, line, c[0], c[1], self.w)


class PlayerInfoUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_prev_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)

    def draw(self):
        self


class Main:

    def __init__(self, cfg):
        self.termbox = None
        self.mpd = None
        self.cfg = cfg
        self.connected = False

    def connect(self):
        try:
            self.mpd.connect(self.cfg['host'], self.cfg['port'])
            self.connected = True
        except SocketError:
            self.connected = False

    def exit(self):
        if self.termbox:
            self.termbox.close()
        if self.connected:
            self.mpd.disconnect()

    def setup(self):
        self.termbox = termbox.Termbox()
        self.playlist = Playlist()
        self.status = Status(self.playlist)

        # Setup MPD
        self.mpd = MPDClient()
        self.connect()

        # Setup UI
        self.ui = UI(self.termbox)
        #self.ui.set_top(PlaybarUI(self.termbox))
        self.ui.set_main(PlaylistUI(self.termbox, self.playlist))
        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))

    def event_loop(self):

        sleep = UPDATE_RATE
        self.ui.draw()
        self.update()
        last = time_in_millis()

        while True:
            self.ui.draw()
            event = self.termbox.peek_event(sleep)

            if event:
                (type, ch, key, mod, w, h) = event

                if type == termbox.EVENT_RESIZE:
                    self.ui.update_size(w, h)
                elif type == termbox.EVENT_KEY:
                    self.key_event(ch, key, mod)

            curr = time_in_millis()
            tdiff = curr - last

            if tdiff >= UPDATE_RATE:
                self.update()
                last = curr
                sleep = UPDATE_RATE
            else:
                sleep = UPDATE_RATE - tdiff

    def key_event(self, ch, key, mode):

        if self.command.active:
            self.command.key_event(ch, key, mode)
        else:
            sys.exit(0)

    def update(self):
        try:
            self.status.update(self.mpd)
        except:
            # TODO: fix error support
            traceback.print_exc()
            sys.exit(0)


def redirect_std(path):
    log_file = open(path, "w")
    sys.stdout = log_file
    sys.stderr = log_file

    return log_file

def main():
    log_file = redirect_std("log")

    colors = { "pl_normal" : (termbox.WHITE, termbox.BLACK),
            "pl_selected" : (termbox.BLUE, termbox.BLACK),
            "pl_current" : (termbox.YELLOW, termbox.BLACK)
    }

    cfg = { "host" : "localhost",
            "port" : 6600,
            "pass" : None
    }

    m = Main(cfg)
    try:
        m.setup()
        m.event_loop()
    except:
        traceback.print_exc()

    m.exit()
    log_file.close()

if __name__ == "__main__":
    main()
