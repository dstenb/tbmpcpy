#!/usr/bin/python
# -*- encoding: utf-8 -*-

import select
import sys
import termbox
import time
import traceback

from mpd import (MPDClient, CommandError)
from socket import error as SocketError

from list import *
from ui import *
from states import *
from status import *


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
        self.browser = Browser()
        self.playlist = Playlist()
        self.options = {"consume": False,
                "random": False,
                "repeat": False,
                "single": False,
                "xfade": False}
        self.current = None
        self.state = ""
        self.listeners = []

    def _set_current(self, pos):
        try:
            self.current = self.playlist[pos] if pos >= 0 else None
        except:
            self.current = None
        for o in self.listeners:
            o.current_changed()

    def _set_option(self, opt, b):
        if self.options[opt] != b:
            self.options[opt] = b
            for o in self.listeners:
                o.option_changed(opt, b)

    def _set_playlist(self, _songs, version):
        songs = []
        for d in _songs:
            songs.append(Song(d))
        self.playlist.set(songs, version)
        for o in self.listeners:
            o.playlist_changed()

    def _set_state(self, state):
        if self.state != state:
            self.state = state
            for o in self.listeners:
                o.state_changed(state)

    def add_listener(self, o):
        self.listeners.append(o)

    def init(self):
        results = self.mpcw.status()
        print(results)
        self._set_playlist(self.mpcw.playlist(), int(results["playlist"]))
        self._set_state(results.get("state", "unknown"))
        self._update_options(results)
        self._set_current(int(results.get("song", -1)))

    def _update_options(self, results):
        print(":: updating changes")
        self._set_option("consume", _get_bool(results, "consume"))
        self._set_option("random", _get_bool(results, "random"))
        self._set_option("repeat", _get_bool(results, "repeat"))
        self._set_option("single", _get_bool(results, "single"))
        self._set_option("xfade", _get_bool(results, "xfade"))

    def _update_playlist(self, results):
        print(":: updating playlist")
        self._set_playlist(self.mpcw.playlist(), int(results["playlist"]))

    def _update_player(self, results):
        print(":: updating player")

        # Update state
        self._set_state(results.get("state", "unknown"))

        # Update current song if necessary
        curr_id = int(results.get("songid", -1))
        prev_id = self.current.songid if self.current else -1

        return curr_id != prev_id

    def update(self, changes):
        if len(changes) == 0:
            return

        results = self.mpcw.status()
        update_current = False
        print(results)

        if "playlist" in changes:
            self._update_playlist(results)
            update_current = True

        if "player" in changes:
            update_current = self._update_player(results) or update_current

        if update_current:
            self._set_current(int(results.get("song", -1)))

        if "options" in changes:
            self._update_options(results)

        if "output" in changes:
            print(":: updating output")
            # TODO

        if "stored_playlist" in changes:
            print(":: updating stored_playlist")
            # TODO


class Main(StateListener):

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.connected = False
        self.mpcw = MPDWrapper(cfg["host"], cfg["port"])
        self.changes = Changes()

    def change_state(self, s):
        self.state = self.states[s]

    def event_loop(self):
        self.status.init()
        self.state.draw()

        while True:
            self.state.draw()

            fds = [sys.stdin]
            if self.mpcw.connected:
                fds.append(self.mpcw)
                self.mpcw.idle()

            try:
                active, _, _ = select.select(fds, [], [], 5)
            except select.error, err:
                if err[0] == 4:
                    self.handle_tb_event(self.termbox.peek_event(10))
                    active = []
                else:
                    raise err

            if self.mpcw in active:
                print(":: Mpd")
                self.mpcw.noidle()

            if sys.stdin in active:
                while self.handle_tb_event(self.termbox.peek_event(10)):
                    self.state.draw()

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
                for k, v in self.states.iteritems():
                    v.ui.update_size(w, h)
            elif type == termbox.EVENT_KEY:
                self.state.key_event(ch, key, mod)

    def setup(self):
        self.termbox = termbox.Termbox()
        self.status = MPDStatus(self.mpcw)

        # Setup MPD
        self.mpcw.connect()

        args = [self, self.mpcw, self.status, self.termbox]
        self.states = {"playlist": PlaylistState(*args),
                "browser": BrowserState(*args)}
        self.state = self.states["playlist"]


def redirect_std(path):
    log_file = open(path, "w")
    sys.stdout = log_file
    sys.stderr = log_file

    return log_file


def main():
    log_file = redirect_std("log")

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
