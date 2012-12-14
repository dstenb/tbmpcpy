# -*- encoding: utf-8 -*-

from status import *
from ui import *
import math
import sys

# Progress bar formatting
marker_c, marker_e, marker_r = u"╼", u"─", u"·"
color_elapsed = (termbox.WHITE, termbox.BLACK)
color_remaining = (termbox.BLACK, termbox.BLACK)


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

    def __init__(self, listener, mpcw, status, termbox, default_keys=False):
        self.listener = listener
        self.mpcw = mpcw
        self.status = status
        self.termbox = termbox
        self.ui = VerticalLayout(self.termbox)

        by_ch, by_key = {}, {}

        if default_keys:
            by_ch = {
                    "q": lambda: sys.exit(0),

                    # Player control
                    "P": lambda: self.mpcw.player("play") if
                      self.status.state != "play" else
                      self.mpcw.player("pause"),
                    "s": lambda: self.mpcw.player("stop"),
                    "n": lambda: self.mpcw.player("next"),
                    "p": lambda: self.mpcw.player("previous"),

                    # States
                    "1": lambda: self.listener.change_state("playlist"),
                    "2": lambda: self.listener.change_state("browser")
            }
            by_key = {}

        self.bindings = Keybindings(by_ch, by_key)

    def draw(self):
        self.ui.draw()

    def key_event(self, ch, key, mod):
        func = self.bindings.get(ch, key)
        if func:
            func()


class StateListener:

    def change_state(self, str):
        self


class CurrentSongUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.set_pref_dim(-1, 2)
        self.set_dim(0, 0, tb.width(), 2)
        self.status = status
        status.add_listener(self)

    def draw(self):
        c = (termbox.WHITE, termbox.BLACK)
        song_line = self._song_format(self.status.current)
        self.change_cells_format(0, 0, song_line)

        elapsed = self.status.progress.elapsed()
        if elapsed >= 0:
            progress = self._progress_bar_format(elapsed)
            self.change_cells_format(0, 1, progress)

    def _progress_bar_format(self, elapsed):
        ew = max(0, int(elapsed * self.w))
        f = Format()
        f.add(marker_c.rjust(ew, marker_e), *color_elapsed)
        f.add(u"".ljust(self.w - ew, marker_r), *color_remaining)
        f.set_bold()
        return f

    # symbols █ ►▮
    def _song_format(self, song):
        f = Format()
        state_dict = {"play":  u">", "stop": "[]", "pause": u"||"}
        f.add(" " + state_dict.get(self.status.state, ""),
                termbox.WHITE, termbox.BLACK)
        if song:
            f.add(" %s - %s - %s" % (song.artist, song.title, song.album),
                    termbox.WHITE, termbox.BLACK)
        return f


class PlayerInfoUI(Drawable, StatusListener):

    def __init__(self, tb, status, custom_str=""):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        self.status.add_listener(self)
        self.custom_str = custom_str

    def _options_format(self):
        f = Format()
        for o, b in sorted(self.status.options.iteritems()):
            f.add(" [" + o + "] ", termbox.WHITE if b else termbox.BLACK,
                    termbox.BLACK)
        f.set_bold()
        return f

    def _string_format(self):
        f = Format()
        f.add(" %s" % self.custom_str, termbox.WHITE, termbox.BLACK)
        return f

    def draw(self):
        options = self._options_format()
        string = self._string_format()
        self.change_cells_format(0, 0, string)
        self.change_cells_format(max(0, self.w - len(options.s)), 0, options)

class PlaylistState(State):

    def __init__(self, _listener, _mpcw, _status, _termbox):
        super(PlaylistState, self).__init__(_listener, _mpcw,
                _status, _termbox, True)

        self.playlist_ui = PlaylistUI(self.termbox, self.status)
        self.ui.set_top(PlayerInfoUI(self.termbox, self.status, "Playlist"))
        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))
        self.ui.set_main(self.playlist_ui)

        self.bindings.add_ch_list({
            "j": lambda: self.playlist_ui.select(1, True),
            "k": lambda: self.playlist_ui.select(-1, True),
            "g": lambda: self.playlist_ui.select(0),
            "G": lambda: self.playlist_ui.select(sys.maxsize),
        })
        self.bindings.add_key_list({
            termbox.KEY_ENTER: lambda:
                self.mpcw.player("play", self.playlist_ui.selected())
                    if self.playlist_ui.selected() >= 0 else False,
            termbox.KEY_ARROW_UP: lambda: self.playlist_ui.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.playlist_ui.select(1, True)
        })


class BrowserUI(ListUI, StatusListener):

    def __init__(self, tb, status):
        super(BrowserUI, self).__init__(tb, status.browser)
        self.status = status
        self.status.add_listener(self)


class BrowserState(State):

    def __init__(self, _listener, _mpcw, _status, _termbox):
        super(BrowserState, self).__init__(_listener, _mpcw,
                _status, _termbox, True)

        self.browser_ui = BrowserUI(self.termbox, self.status)
        self.ui.set_top(PlayerInfoUI(self.termbox, self.status, "Browser"))
        self.ui.set_bottom(CurrentSongUI(self.termbox, self.status))
        self.ui.set_main(self.browser_ui)

        self.bindings.add_ch_list({
            "j": lambda: self.browser_ui.select(1, True),
            "k": lambda: self.browser_ui.select(-1, True),
            "g": lambda: self.browser_ui.select(0),
            "G": lambda: self.browser_ui.select(sys.maxsize),
        })
        self.bindings.add_key_list({
            termbox.KEY_ARROW_UP: lambda: self.browser_ui.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.browser_ui.select(1, True)
        })
