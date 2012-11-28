from status import *
from ui import *
import math
import sys

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
        self.ui = UI(self.termbox)

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
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        status.add_listener(self)

    def draw(self):
        c = (termbox.WHITE, termbox.BLACK)
        self.change_cells(0, 0, self.line(self.status.current),
                c[0], c[1], self.w)

    def line(self, song):
        state_dict = {"play":  ">", "stop": "[]", "pause": "||"}
        line = " " + state_dict.get(self.status.state, "hej")
        if song:
            line += " %s - %s - %s" % (song.artist, song.title, song.album)
        return line


class PlayerInfoUI(Drawable, StatusListener):

    def __init__(self, tb, status, custom_str=""):
        self.tb = tb
        self.set_pref_dim(-1, 1)
        self.set_dim(0, 0, tb.width(), 1)
        self.status = status
        self.status.add_listener(self)
        self.custom_str = custom_str

    def draw(self):
        def sy(m):
            symbols = {"random": "r",
                    "repeat": "R",
                    "single": "s",
                    "consume": "c"
            }

            return symbols[m] if self.status.mode[m] else "-"

        options = ""
        for k, v in self.status.mode.iteritems():
            if v:
                options += " [" + k + "] "
        f = Format()
        f.add(" %s" % self.custom_str, termbox.WHITE, termbox.BLACK)
        f.replace(self.w - len(options), options, termbox.WHITE, termbox.BLACK)
        self.change_cells_format(0, 0, f)


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
        for y in range(self.h):
            pos = y + self.start

            if y < l:
                # TODO
                song = self.status.playlist[pos]
                num_str = "%s " % str(pos + 1)
                time_str = " [%s] " % length_str(song.time)

                f = Format()
                f.add(num_str.rjust(numw + 1), termbox.BLUE, termbox.BLACK)
                f.add(song.artist, termbox.RED, termbox.BLACK)
                f.add(" - ", termbox.WHITE, termbox.BLACK)
                f.add(song.title, termbox.YELLOW, termbox.BLACK)
                f.add(" (", termbox.WHITE, termbox.BLACK)
                f.add(song.album, termbox.GREEN, termbox.BLACK)
                f.add(")", termbox.WHITE, termbox.BLACK)
                f.replace(self.w - 9, time_str, termbox.BLUE, termbox.BLACK)

                if pos == self.sel:
                    f.set_color(termbox.BLACK, termbox.WHITE)
                if song is self.status.current:
                    f.set_bold()
                    f.replace(0, ">", termbox.BLUE, termbox.BLACK)

                self.change_cells_format(0, y, f)
            else:
                self.change_cells_format(0, y, Format("".ljust(self.w)))

    def fix_bounds(self):
        if len(self.status.playlist) > 0:
            self.sel = min(max(0, self.sel), len(self.status.playlist) - 1)
            if (self.sel - self.start) >= self.h:
                self.start = self.sel - self.h + 1
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
                    if self.playlist_ui.selected() > 0 else False,
            termbox.KEY_ARROW_UP: lambda: self.playlist_ui.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.playlist_ui.select(1, True)
        })


class BrowserUI(Drawable, StatusListener):

    def __init__(self, tb, status):
        self.tb = tb
        self.status = status
        self.sel = 0
        self.start = 0

    def draw(self):
        self

    def fix_bounds(self):
        self

    def current_changed(self):
        self

    def select(self, index, rel=False):
        self

    def selected(self):
        self


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
