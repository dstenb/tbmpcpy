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

    def __init__(self, tb, status):
        self.tb = tb
        self.status = status
        self.sel = 0
        self.start = 0

    def draw(self):
        l = len(self.status.playlist)
        print("draw")
        for y in range(self.h):
            pos = y + self.start
            print(pos)
            c = [termbox.WHITE, termbox.BLACK]
            if y == self.sel:
                c = [termbox.BLACK, termbox.WHITE]
            if y < l:
                # TODO
                song = self.status.playlist[pos]
                if song is self.status.current:
                    c[0] = termbox.YELLOW
                left = " %s - %s (%s)" % (song.artist, song.title, song.album)
                left = unicode(left, "utf-8")
                right = " [%s] " % length_str(song.time).rjust(5)
                right = unicode(right, "utf-8")
                self.change_cells(0, y, left, c[0], c[1], self.w - 9)
                self.change_cells(self.w - 9, y, right, c[0], c[1])
            else:
                self.change_cells(0, y, "", c[0], c[1], self.w)

    def fix_bounds(self):
        if len(self.status.playlist) > 0:
            self
            if (self.sel - self.start) + 2 >= self.h:
                self.start = self.sel - self.h
            if self.sel < self.start:
                self.start = self.sel
            self.start = min(max(0, self.start), len(self.status.playlist) - 1)
            self.sel = min(max(0, self.sel), len(self.status.playlist) - 1)

    def current_changed(self):
        self.fix_bounds()

    def playlist_updated(self):
        if len(self.status.playlist) > 0 and self.sel == -1:
            self.start = self.sel = 0
        else:
            self.start = self.sel = -1
        self.fix_bounds()

    def select(self, index, rel=False):
        print(self.status.playlist.songs)
        if rel:
            self.sel += index
        else:
            self.sel = index
        self.fix_bounds()


class CurrentSongUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        status.add_listener(self)

    def draw(self):
        c = (termbox.BLACK, termbox.GREEN)
        self.change_cells(0, 0, self.line(self.status.current),
                c[0], c[1], self.w)

    def line(self, song):
        state_dict = {"play":  ">", "stop" : "[]", "pause" : "||"}
        line = " " + state_dict.get(self.status.state, "hej")
        if song:
            line += " %s - %s - %s" % (song.artist, song.title, song.album)
        return(unicode(line, "utf-8"))


class PlayerInfoUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        self.status.add_listener(self)

    def draw(self):
        def sy(m):
            symbols = { "random" : "r",
                    "repeat" : "R",
                    "single" : "s",
                    "consume" : "c"
            }

            return symbols[m] if self.status.mode[m] else "-"

        c = ( termbox.BLACK, termbox.GREEN)
        line = " [%s%s%s%s] " % (sy("random"), sy("repeat"), sy("single"),
                sy("consume"))
        self.change_cells(0, 0, line, c[0], c[1], self.w)


class BottomUI(Drawable):

    def draw(self):
        self.components = []

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

    def exit(self):
        if self.termbox:
            self.termbox.close()
        if self.connected:
            self.mpd.disconnect()

    def key_event(self, ch, key, mode):

        if ch == "q":
            sys.exit(0)
        elif ch == "j":
            self.playlist_ui.select(1, True)
        elif ch == "k":
            self.playlist_ui.select(-1, True)
        elif ch == "P":
            self.play(self, self.playlist_ui.selected())
        elif ch == "p":
            self.playpause()
        elif ch == "s":
            self.stop()
        elif ch == "/":
            self.command.set_search()
        elif ch == ":":
            self

    def play(self, id):
        if self.connected:
            self.mpd.play(self, id)

    def playpause(self):
        if self.connected:
            if self.status.state == "play":
                self.mpd.pause()
            else:
                self.mpd.play()

    def setup(self):
        self.termbox = termbox.Termbox()
        self.playlist = Playlist()
        self.status = Status(self.playlist)

        # Setup MPD
        self.mpd = MPDClient()
        self.connect()

        # Setup UI
        self.playlist_ui = PlaylistUI(self.termbox, self.status)

        self.ui = UI(self.termbox)
        self.ui.set_top(PlayerInfoUI(self.termbox, self.status))
        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))
        self.ui.set_main(self.playlist_ui)

    def stop(self):
        if self.connected:
            self.mpd.stop()

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
