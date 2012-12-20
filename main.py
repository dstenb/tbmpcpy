#!/usr/bin/python
# -*- encoding: utf-8 -*-

import getopt
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


MPD_RECONNECT = 10


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
        self.add_bottom(create("command", CommandUI, False, termbox, None))

        create("playlist", PlaylistUI, False, termbox, status)


class Main(object):

    def __init__(self, cfg):
        self.termbox = None
        self.cfg = cfg
        self.states = {}
        self.mpd = MPDWrapper(cfg["host"], cfg["port"])

    def change_state(self, s):
        if s in self.states:
            self.state = self.states[s]
            self.state.activate()

    def auth(self):
        if self.mpd.connected and self.cfg["password"]:
            if not self.mpd.auth(self.cfg["password"]):
                self.msg.error("Couldn't auth!", 3)
                return False
        return True

    def connect(self):
        if self.mpd.connect():
            self.msg.info("Connected to %s:%s!" %
                    (self.mpd.host, self.mpd.port), 1)
        else:
            self.msg.error("Couldn't connect to %s:%s" %
                    (self.mpd.host, self.mpd.port), 3)

    def event_loop(self):
        curr = time_in_millis()
        retry_conn = False
        retry_timestamp = curr
        while True:
            self.ui.draw()

            active = []
            fds = [sys.stdin]
            if self.mpd.connected:
                fds.append(self.mpd)
                self.mpd.idle()
            elif not retry_conn:
                retry_conn = True
                retry_timestamp = curr
            elif (curr - retry_timestamp) >= MPD_RECONNECT * 1000:
                retry_conn = False
                self.connect()
                self.auth()

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
        self.msg = Message()
        self.status = Status(self.mpd, self.msg)
        self.ui = UI(self.termbox, self.status, self.msg)
        self.connect()
        self.auth()

        self.status.init()

        args = [self, self.mpd, self.status, self.ui, self.msg]
        self.states = { "playlist": PlaylistState(*args),
                "command": CommandState(*args) }
        self.change_state("playlist")


def redirect_std(path):
    log_file = open(path, "w")
    sys.stdout = log_file
    sys.stderr = log_file
    return log_file


def usage(cmd):
    print "Usage: %s [OPTIONS]..." % cmd
    print
    print("Mandatory arguments to long options are %s" %
            "mandatory for short options too.")
    print
    print "-h, --help       print this message."
    print "-p, --password   MPD password"


def main(argv=None):

    cfg = {"host": "localhost",
            "port": 6600,
            "password": None
    }

    if argv is None:
        argv = sys.argv

    cmd = argv[0]

    try:
        opts, argv = getopt.getopt(argv[1:], "p:h", ["help", "password="])
    except getopt.GetoptError as e:
        print(e)
        usage(cmd)
        sys.exit()

    printer = None

    for o, a in opts:
        if o in ("-h", "--help"):
            usage(cmd)
            sys.exit()
        elif o in ("-p", "--password"):
            cfg["password"] = a

    log_file = redirect_std("log")

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
