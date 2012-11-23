#!/usr/bin/python
# -*- encoding: utf-8 -*-

import select
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

    if m == 0:
        return "--:--"
    elif m > 99:
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
        numw = int(math.floor(math.log10(l))) + 2 if l > 0 else 0
        print("numw")
        print(numw)
        for y in range(self.h):
            pos = y + self.start

            if y < l:
                # TODO
                song = self.status.playlist[pos]
                num_str = "%s " % str(pos + 1)
                time_str = "[%s] " % length_str(song.time).rjust(5)
                format = [ [num_str.rjust(numw), termbox.BLUE, termbox.BLACK],
                    ["%s" % song.artist, termbox.RED, termbox.BLACK],
                    [" - ", termbox.WHITE, termbox.BLACK],
                    ["%s " % song.title, termbox.YELLOW, termbox.BLACK],
                    ["(", termbox.WHITE, termbox.BLACK],
                    ["%s" % song.album, termbox.GREEN, termbox.BLACK],
                    [")", termbox.WHITE, termbox.BLACK],
                    [time_str.rjust(self.w -9), termbox.RED, termbox.BLACK]
                ]

                def set_colors(list, fg, bg):
                    for v in list:
                        v[1] = fg
                        v[2] = bg

                if song is self.status.current:
                    set_colors(format, termbox.WHITE, termbox.BLACK)

                if y == self.sel:
                    set_colors(format, termbox.BLACK, termbox.WHITE)
                self.change_cells_list(0, y, format)
            else:
                self.change_cells(0, y, "", termbox.BLACK, termbox.BLACK, self.w)

    def fix_bounds(self):
        if len(self.status.playlist) > 0:
            self.sel = min(max(0, self.sel), len(self.status.playlist) - 1)
            if (self.sel - self.start) + 2 >= self.h:
                self.start = self.sel - self.h
            if self.sel < self.start:
                self.start = self.sel
            self.start = min(max(0, self.start), len(self.status.playlist) - 1)

    def current_changed(self):
        self.fix_bounds()

    def playlist_updated(self):
        if len(self.status.playlist) > 0 and self.sel == -1:
            self.start = self.sel = 0
        else:
            self.start = self.sel = -1
        self.fix_bounds()

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self.fix_bounds()

    def selected(self):
        return self.sel


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
        state_dict = {"play":  ">", "stop": "[]", "pause": "||"}
        line = " " + state_dict.get(self.status.state, "hej")
        if song:
            line += " %s - %s - %s" % (song.artist, song.title, song.album)
        return line


class PlayerInfoUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        self.status.add_listener(self)

    def draw(self):
        def sy(m):
            symbols = {"random": "r",
                    "repeat": "R",
                    "single": "s",
                    "consume": "c"
            }

            return symbols[m] if self.status.mode[m] else "-"

        c = (termbox.BLACK, termbox.GREEN)
        line = " [%s%s%s%s] " % (sy("random"), sy("repeat"), sy("single"),
                sy("consume"))
        self.change_cells(0, 0, line, c[0], c[1], self.w)


class BottomUI(Drawable):

    def draw(self):
        self.components = []


class Changes:

    def __init__(self):
        self.changes = []

    def add(self, _list):
        for s in _list:
            if not s in self.changes:
                self.changes.append(s)

    def get(self):
        c = self.changes
        self.changes = []
        return c


class MPDWrapper():

    def __init__(self, host, port):
        self.mpd = MPDClient(use_unicode=True)
        self.changes = Changes()
        self.host = host
        self.port = port
        self.connected = False
        self.in_idle = False

    def connect(self):
        try:
            self.mpd.connect(self.host, self.port)
            self.connected = True
        except SocketError:
            self.connected = False
        return self.connected

    def disconnect(self):
        if self.connected:
            self.mpd.disconnect()
            self.connected = False

    def fileno(self):
        return self.mpd.fileno()

    def get_changes(self):
        return self.changes.get() if not self.in_idle else []

    def idle(self):
        if self.connected and not self.in_idle:
            self.in_idle = True
            self.mpd.send_idle()
        return self.in_idle

    def noidle(self, block=False):
        changes = []
        if self.connected and self.in_idle:
            self.in_idle = False
            if not block:
                self.mpd.send_noidle()
            changes = self.mpd.fetch_idle()
            self.changes.add(changes)

    def playlist(self):
        return self.mpd.playlistinfo()

    def player(self, name, *args):
        if self.connected:
            self.noidle()
            getattr(self.mpd, name)(*args)

    def status(self):
        return self.mpd.status()




def _get_bool(d, v, de=0):
    return bool(int(d.get(v, de)))


class MPDStatus:

    def __init__(self, mpcw):
        self.mpcw = mpcw
        self.playlist = Playlist()
        self.mode = {"random": False, "repeat": False,
                "single": False, "consume": False
        }
        self.current = None
        self.state = ""
        self.listeners = []

    def _set_current(self, pos):
        try:
            self.current = self.playlist[pos]
        except:
            self.current = None
        for o in self.listeners:
            o.current_changed()

    def _set_mode(self, m, b):
        if self.mode[m] != b:
            self.mode[m] = b
            for o in self.listeners:
                o.mode_changed(m, b)

    def _set_state(self, state):
        if self.state != state:
            self.state = state
            for o in self.listeners:
                o.state_changed(state)

    def _set_playlist(self, _songs, version):
        songs = []
        for d in _songs:
            songs.append(Song(d))
        self.playlist.update(songs, version)
        for o in self.listeners:
            o.playlist_changed()

    def add_listener(self, o):
        self.listeners.append(o)

    def init(self):
        results = self.mpcw.status()
        self._set_playlist(self.mpcw.playlist(), int(results["playlist"]))
        self._set_state(results.get("state", "unknown"))
        self._set_mode("random", _get_bool(results, "random"))
        self._set_mode("repeat", _get_bool(results, "repeat"))
        self._set_mode("single", _get_bool(results, "single"))
        self._set_current(int(results.get("song", -1)))

    def update(self, changes):
        if len(changes) == 0:
            return

        results = self.mpcw.status()
        print(results)

        if "playlist" in changes:
            print(":: updating playlist")
            self._set_playlist(self.mpcw.playlist(), int(results["playlist"]))

        if "player" in changes:
            print(":: updating player")

            # Update state
            self._set_state(results.get("state", "unknown"))

            # Update current song if necessary
            curr_id = int(results.get("songid", -1))
            prev_id = self.current.songid if self.current else -1

            if curr_id != prev_id:
                self._set_current(int(results.get("song", -1)))

        if "options" in changes:
            print(":: updating changes")
            self._set_mode("random", _get_bool(results, "random"))
            self._set_mode("repeat", _get_bool(results, "repeat"))
            self._set_mode("single", _get_bool(results, "single"))

        if "output" in changes:
            print(":: updating output")
            # TODO

        if "stored_playlist" in changes:
            print(":: updating stored_playlist")
            # TODO


class Keybindings:
    def __init__(self, _ch={}, _key={}):
        self.by_ch = _ch
        self.by_key = _key

    def add_ch(self, ch, func):
        self.by_ch[ch] = func

    def add_key(self, key, func):
        self.by_key[key] = func

    def get(self, ch, key):
        func = self.by_ch.get(ch, None) or self.by_key.get(key, None)
        return func


class Main:

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.connected = False
        self.mpcw = MPDWrapper(cfg["host"], cfg["port"])
        self.changes = Changes()

    def event_loop(self):

        self.status.init()
        self.ui.draw()

        for i in xrange(100):
            self.ui.draw()

            fds = [sys.stdin]
            if self.mpcw.connected:
                fds.append(self.mpcw)
                self.mpcw.idle()

            try:
                active, _, _ = select.select(fds, [], [], 5)
            except select.error, err:
                if err[0] == 4:
                    self.handle_tb_event(self.termbox.peek_event(100))
                    active = []
                else:
                    raise err

            if self.mpcw in active:
                print(":: Mpd")
                self.mpcw.noidle()

            if sys.stdin in active:
                self.handle_tb_event(self.termbox.peek_event(100))

            self.status.update(self.mpcw.get_changes())

    def exit(self):
        if self.termbox:
            self.termbox.close()
        if self.connected:
            self.mpcw.disconnect()

    def handle_tb_event(self, event):
        if event:
            (type, ch, key, mod, w, h) = event

            if type == termbox.EVENT_RESIZE:
                self.ui.update_size(w, h)
            elif type == termbox.EVENT_KEY:
                self.key_event(ch, key, mod)

    def key_event(self, ch, key, mode):
        func = self.bindings.get(ch, key)
        if func:
            func()

    def setup(self):
        self.termbox = termbox.Termbox()
        self.status = MPDStatus(self.mpcw)

        # Setup MPD
        self.mpcw.connect()

        # Setup UI
        self.playlist_ui = PlaylistUI(self.termbox, self.status)

        self.ui = UI(self.termbox)
        self.ui.set_top(PlayerInfoUI(self.termbox, self.status))
        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))
        self.ui.set_main(self.playlist_ui)

        self.bindings = Keybindings(
                {"q": lambda: sys.exit(0),
                  "j": lambda: self.playlist_ui.select(1, True),
                  "k": lambda: self.playlist_ui.select(-1, True),
                  "g": lambda: self.playlist_ui.select(0),
                  "G": lambda: self.playlist_ui.select(sys.maxsize),
                  "P": lambda: self.mpcw.player("play") if
                      self.status.state != "play" else
                      self.mpcw.player("pause"),
                  "s": lambda: self.mpcw.player("stop"),
                  "n": lambda: self.mpcw.player("next"),
                  "p": lambda: self.mpcw.player("previous")
                },
                {
                    termbox.KEY_ENTER: lambda:
                        self.mpcw.player("play", self.playlist_ui.selected())
                        if self.playlist_ui.selected() > 0 else False,
                    termbox.KEY_ARROW_UP: lambda:
                        self.playlist_ui.select(-1, True),
                    termbox.KEY_ARROW_DOWN: lambda:
                        self.playlist_ui.select(1, True),
                })


def redirect_std(path):
    log_file = open(path, "w")
    sys.stdout = log_file
    sys.stderr = log_file

    return log_file


def main():
    log_file = redirect_std("log")

    colors = {"pl_normal": (termbox.WHITE, termbox.BLACK),
            "pl_selected": (termbox.BLUE, termbox.BLACK),
            "pl_current": (termbox.YELLOW, termbox.BLACK)
    }

    cfg = {"host": "localhost",
            "port": 6600,
            "pass": None
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

    #def _player(self, name, *args):
    #    if name in self.player_commands:
    #        if self.connected:
    #            self.noidle()
    #            self.player_commands[name](*args)


        #self.player_commands = {
        #    "next": lambda: self.mpd.next(),
        #    "prev": lambda: self.mpd.previous(),
        #    "play": lambda id: self.mpd.play(id),
        #    "playpause": lambda play: self.mpd.play()
        #        if play else self.mpd.pause(),
        #    "stop": lambda: self.mpd.stop()
        #}

