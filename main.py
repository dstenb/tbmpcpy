#!/usr/bin/python
# -*- encoding: utf-8 -*-

import getopt
import select
import sys
import termbox
import traceback

from browser import *
from common import *
from components import *
from help import *
from list import *
from search import *
from states import *
from status import *
from ui import *
from wrapper import *


MPD_RECONNECT = 10000
MPD_UPDATE = 2000


class UI(VerticalLayout):

    def __init__(self, termbox, status, msg, browser):
        super(UI, self).__init__(termbox)
        self.set_dim(0, 0, termbox.width(), termbox.height())

        def create(name, cls, show, *args):
            o = cls(*args)
            o.show() if show else o.hide()
            setattr(self, name, o)
            return o

        top = [["browser_bar", BrowserBar, True, termbox, browser],
                ["playlist_bar", PlaylistBar, True, termbox, status.playlist]]

        main = [["playlist", PlaylistUI, False, termbox, status],
                ["browser", BrowserUI, False, termbox, browser],
                ["help", TextComponent, False, termbox, help_text, "Help",
                    True]]

        bottom = [["current_song", CurrentSongUI, True, termbox, status],
                ["progress_bar", ProgressBarUI, True, termbox, status],
                ["message", MessageUI, False, termbox, msg],
                ["command", CommandLineUI, False, termbox, None],
                ["search", SearchUI, False, termbox]]

        for v in top:
            self.add_top(create(*v))

        for v in main:
            create(*v)

        for v in bottom:
            self.add_bottom(create(*v))

    def show_top(self, o):
        for oc in self.top:
            oc.show() if (oc is o) else oc.hide()


class Main(object):

    def __init__(self, cfg):
        self.mpd = MPDWrapper(cfg["host"], cfg["port"])
        self.termbox = None
        self.cfg = cfg
        self.states = {}
        self.pstate = None
        self.state = None

    def change_state(self, s, args={}):
        if s in self.states:
            self.pstate = self.state
            self.state = self.states[s]
            self.state.activate(args)

    def prev_state(self, args={}):
        if self.pstate:
            self.pstate, self.state = self.state, self.pstate
            self.state.activate(args)

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
        ts = time_in_millis()
        retry_conn = False
        retry_ts, idle_ts = ts, ts

        while True:
            self.ui.draw()

            # Handle MPD connection
            if self.mpd.connected:
                self.mpd.idle()
            elif not retry_conn:
                retry_conn = True
                retry_ts = ts
            elif (ts - retry_ts) >= MPD_RECONNECT:
                retry_conn = False
                self.connect()
                self.auth()
                self.browser.load()
                self.status.init()

            # Handle termbox events
            ev = self.termbox.peek_event(1000)
            while ev:
                (etype, ch, key, mod, w, h) = ev

                if etype == termbox.EVENT_RESIZE:
                    self.ui.set_size(w, h)
                elif etype == termbox.EVENT_KEY:
                    self.state.key_event(ch, key, mod)

                if self.mpd.has_changes():
                    break
                ev = self.termbox.peek_event()
                if ev:
                    self.ui.draw()

            ts = time_in_millis()

            # Update elapsed time if playing (rough estimate)
            if self.status.is_playing():
                self.status.progress.update(ts)
            else:
                self.status.progress.last = ts

            # Update message timer
            self.msg.update(ts)

            # Update MPD data if necessary
            if (ts - idle_ts) >= MPD_UPDATE or self.mpd.has_changes():
                idle_ts = ts
                self.mpd.noidle()
                changes = self.mpd.get_changes()
                if "database" in changes:
                    self.browser.load()
                    self.msg.info("Database updated!", 4)
                    pass  # TODO: update database
                if "stored_playlist" in changes:
                    pass  # TODO: update stored playlists
                self.status.update(changes)

    def exit(self):
        if self.termbox:
            self.termbox.close()
        self.mpd.disconnect()

    def setup(self):
        self.termbox = termbox.Termbox()
        self.msg = Message()
        self.status = Status(self.mpd, self.msg)
        self.browser = Browser(self.mpd)
        self.ui = UI(self.termbox, self.status, self.msg, self.browser)
        self.connect()
        self.auth()

        self.browser.load()
        self.status.init()

        args = [self, self.mpd, self.status, self.ui, self.msg, self.browser]
        self.states = {"playlist": PlaylistState(*args),
                "browser": BrowserState(*args),
                "command": CommandState(*args),
                "search": SearchState(*args),
                "find": FindNextState(*args),
                "help": HelpState(*args)}
        self.change_state("playlist")


_stdout = sys.stdout
_stderr = sys.stderr


def redirect_std(path):
    log_file = open(path, "w")
    sys.stdout = log_file
    sys.stderr = log_file
    return log_file


def stop_redirect(log_file):
    log_file.close()
    sys.stdout = _stdout
    sys.stderr = _stderr


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
    except SystemExit:
        pass
    except:
        m.exit()
        stop_redirect(log_file)
        traceback.print_exc()
    finally:
        m.exit()
        stop_redirect(log_file)

if __name__ == "__main__":
    main()
