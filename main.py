#!/usr/bin/python
# -*- encoding: utf-8 -*-

import select
import sys
import termbox
import time
import traceback

from list import *
from ui import *
from states import *
from status import *
from wrapper import *


class Main(StateListener):

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.mpdw = MPDWrapper(cfg["host"], cfg["port"])
        self.changes = Changes()

    def change_state(self, s):
        self.state = self.states[s]

    def event_loop(self):
        self.status.init()
        self.state.draw()

        while True:
            self.state.draw()

            fds = [sys.stdin]
            if self.mpdw.connected:
                fds.append(self.mpdw)
                self.mpdw.idle()

            try:
                active, _, _ = select.select(fds, [], [], 5)
            except select.error, err:
                if err[0] == 4:
                    self.handle_tb_event(self.termbox.peek_event(10))
                    active = []
                else:
                    raise err

            if self.mpdw in active:
                print(":: Mpd")
                self.mpdw.noidle()

            if sys.stdin in active:
                while self.handle_tb_event(self.termbox.peek_event(10)):
                    self.state.draw()

            self.status.update(self.mpdw.get_changes())

    def exit(self):
        if self.termbox:
            self.termbox.close()
        self.mpdw.disconnect()

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
        self.status = Status(self.mpdw)

        # Setup MPD
        self.mpdw.connect()

        args = [self, self.mpdw, self.status, self.termbox]
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
