#!/usr/bin/python
# -*- encoding: utf-8 -*-

import select
import sys
import termbox
import time
import traceback

from list import *
#from ui import *
#from states import *
from status import *
from wrapper import *

from components import *
from tb import *


def time_in_millis():
    return int(round(time.time() * 1000))


class Main(object):

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.mpd = MPDWrapper(cfg["host"], cfg["port"])
        self.changes = Changes()

    def event_loop(self):
        last = time_in_millis()
        for i in xrange(10):
            self.ui.draw()

            fds = [sys.stdin]
            if self.mpd.connected:
                fds.append(self.mpd)
                self.mpd.idle()

            try:
                active, _, _ = select.select(fds, [], [], 1)
            except select.error, err:
                if err[0] == 4:
                    self.handle_tb_event(self.termbox.peek_event(10))
                    active = []
                else:
                    raise err

            # Update elapsed time if playing (rough estimate)
            if self.status.is_playing():
                curr = time_in_millis()
                diff = (curr - last)
                if diff >= 1000:
                    self.status.progress.elapsed_time += (diff / 1000)
                last = curr
            else:
                last = time_in_millis()

            if self.mpd in active:
                self.mpd.noidle()

            if sys.stdin in active:
                while self.handle_tb_event(self.termbox.peek_event(10)):
                    self.ui.draw()

            self.status.update(self.mpd.get_changes())

    def exit(self):
        if self.termbox:
            self.termbox.close()
        self.mpd.disconnect()

    def handle_key_event(self, ch, key):
        if ch:
            if ch == "q":
                sys.exit(0)
            else:
                self.progress_bar.toggle_visibility()

    def handle_tb_event(self, event):
        if event:
            (type, ch, key, mod, w, h) = event

            if type == termbox.EVENT_RESIZE:
                self.ui.set_size(w, h)
            elif type == termbox.EVENT_KEY:
                self.handle_key_event(ch, key)

    def setup(self):
        self.termbox = termbox.Termbox()
        self.mpd.connect()
        self.status = Status(self.mpd)
        self.status.init()

        self.current_song = CurrentSongUI(self.termbox, self.status)
        self.progress_bar = ProgressBarUI(self.termbox, self.status)
        self.playlist = PlaylistUI(self.termbox, self.status)

        self.ui = VerticalLayout(self.termbox)
        self.ui.add_bottom(self.current_song)
        self.ui.add_bottom(self.progress_bar)
        self.ui.set_main(self.playlist)


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
