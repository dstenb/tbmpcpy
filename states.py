# -*- encoding: utf-8 -*-

from components import *
from status import *
from ui import *
import math
import sys


def length_str(time):
    m = time / 60
    s = time % 60

    if m <= 0:
        return "--:--"
    elif m > 99:
        return str(m) + "m"
    return str(m).zfill(2) + ":" + str(s).zfill(2)


class Keybindings:
    def __init__(self, _ch={}, _key={}):
        self.by_ch = _ch
        self.by_key = _key

    def add_ch(self, ch, func):
        self.by_ch[ch] = func

    def add_ch_list(self, ch_list):
        self.by_ch.update(ch_list)

    def add_key(self, key, func):
        self.by_key[key] = func

    def add_key_list(self, key_list):
        self.by_key.update(key_list)

    def get(self, ch, key):
        func = self.by_ch.get(ch, None) or self.by_key.get(key, None)
        return func


class State(object):

    def __init__(self, listener, mpd, status, ui, msg, default_keys=False):
        self.listener = listener
        self.mpd = mpd
        self.status = status
        self.ui = ui
        self.msg = msg

        by_ch, by_key = {}, {}

        if default_keys:
            by_ch = {
                    "q": lambda: sys.exit(0),

                    # Player control
                    "P": lambda: self.mpd.player("play") if
                      self.status.state != "play" else
                      self.mpd.player("pause"),
                    "s": lambda: self.mpd.player("stop"),
                    "n": lambda: self.mpd.player("next"),
                    "p": lambda: self.mpd.player("previous"),

                    # States
                    "1": lambda: self.listener.change_state("playlist"),
                    "2": lambda: self.listener.change_state("browser"),
                    ":": lambda: self.listener.change_state("command")
            }
            by_key = {}

        self.bindings = Keybindings(by_ch, by_key)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def key_event(self, ch, key, mod):
        func = self.bindings.get(ch, key)
        if func:
            func()


class StateListener:

    def change_state(self, str):
        self


class PlaylistState(State):

    def __init__(self, _listener, _mpd, _status, _ui, _msg):
        super(PlaylistState, self).__init__(_listener, _mpd,
                _status, _ui, _msg, True)

        self.bindings.add_ch_list({
            "j": lambda: self.ui.playlist.select(1, True),
            "k": lambda: self.ui.playlist.select(-1, True),
            "g": lambda: self.ui.playlist.select(0),
            "G": lambda: self.ui.playlist.select(sys.maxsize),
            "w": lambda: self.msg.warning("Can't flumpf the flumpf", 1),
            "e": lambda: self.msg.error("Unable to connect to localhost:6600", 5),
        })
        self.bindings.add_key_list({
            termbox.KEY_ENTER: lambda:
                self.mpd.player("play", self.ui.playlist.selected())
                    if self.ui.playlist.selected() >= 0 else False,
            termbox.KEY_ARROW_UP: lambda: self.ui.playlist.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.ui.playlist.select(1, True)
        })

    def activate(self):
        self.ui.set_main(self.ui.playlist)

    def deactivate(self):
        pass


class CommandState(State):

    def __init__(self, _listener, _mpd, _status, _ui, _msg):
        super(CommandState, self).__init__(_listener, _mpd,
                _status, _ui, _msg, False)

        self.bindings.add_key_list({
            termbox.KEY_ESC: lambda: self.deactivate("playlist")
        })

    def activate(self):
        self.ui.command.show()

    def deactivate(self, new_state):
        self.ui.command.hide()
        self.listener.change_state(new_state)

    def key_event(self, ch, key, mod):
        func = self.bindings.get(ch, key)
        if func:
            func()
        elif ch:
            ch

#class BrowserUI(ListUI, StatusListener):
#
#    def __init__(self, tb, status):
#        super(BrowserUI, self).__init__(tb, status.browser)
#        self.status = status
#        self.status.add_listener(self)
#
#
#class BrowserState(State):
#
#    def __init__(self, _listener, _mpd, _status, _termbox):
#        super(BrowserState, self).__init__(_listener, _mpd,
#                _status, _termbox, True)
#
#        self.browser_ui = BrowserUI(self.termbox, self.status)
#        self.ui.set_top(PlayerInfoUI(self.termbox, self.status, "Browser"))
#        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))
#        self.ui.set_main(self.browser_ui)
#
#        self.bindings.add_ch_list({
#            "j": lambda: self.browser_ui.select(1, True),
#            "k": lambda: self.browser_ui.select(-1, True),
#            "g": lambda: self.browser_ui.select(0),
#            "G": lambda: self.browser_ui.select(sys.maxsize),
#        })
#        self.bindings.add_key_list({
#            termbox.KEY_ARROW_UP: lambda: self.browser_ui.select(-1, True),
#            termbox.KEY_ARROW_DOWN: lambda: self.browser_ui.select(1, True)
#        })
