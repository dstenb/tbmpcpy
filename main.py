#!/usr/bin/python
# -*- encoding: utf-8 -*-

import select
import sys
import termbox
import traceback

from common import *
from components import *
from list import *
from states import *
from status import *
from ui import *
from wrapper import *


class UI(VerticalLayout):

    def __init__(self, termbox, status, msg):
        super(UI, self).__init__(termbox)

        def create(name, cls, show, *args):
            o = cls(*args)
            o.show() if show else o.hide()
            setattr(self, name, o)
            return o

        self.add_bottom(create("current_song", CurrentSongUI, True, termbox,
            status))
        self.add_bottom(create("progress_bar", ProgressBarUI, True, termbox,
            status))
        self.add_bottom(create("message", MessageUI, False, termbox, msg))

        create("playlist", PlaylistUI, False, termbox, status)


class Main(object):

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.mpd = MPDWrapper(cfg["host"], cfg["port"])

    def event_loop(self):
        while True:
            self.ui.draw()

            active = []
            fds = [sys.stdin]
            if self.mpd.connected:
                fds.append(self.mpd)
                self.mpd.idle()

            try:
                active, _, _ = select.select(fds, [], [], 1)
            except select.error, err:
                if err[0] == 4:
                    self.handle_tb_event(self.termbox.peek_event(10))
                else:
                    raise err

            curr = time_in_millis()

            # Update elapsed time if playing (rough estimate)
            if self.status.is_playing():
                self.status.progress.update(curr)
            else:
                self.status.progress.set_last(curr)
            self.msg.update(curr)

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

    def handle_tb_event(self, event):
        if event:
            (type, ch, key, mod, w, h) = event

            if type == termbox.EVENT_RESIZE:
                self.ui.set_size(w, h)
            elif type == termbox.EVENT_KEY:
                self.state.key_event(ch, key, mod)

    def setup(self):
        self.termbox = termbox.Termbox()
        self.mpd.connect()
        self.status = Status(self.mpd)
        self.status.init()
        self.msg = Message()

        self.ui = UI(self.termbox, self.status, self.msg)

        args = [self, self.mpd, self.status, self.ui, self.msg]
        self.state = PlaylistState(*args)


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
