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
        self.change_cells(0, 0, self._line(self.status.current),
                c[0], c[1], self.w)

    def _line(self, song):
        state_dict = {"play":  ">", "stop": "[]", "pause": "||"}
        line = " " + state_dict.get(self.status.state, "")
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
        options = Format()
        for k, v in sorted(self.status.options.iteritems()):
            if v:
                options.add(" [" + k + "] ", termbox.WHITE, termbox.BLACK)
            else:
                options.add(" [" + k + "] ", termbox.BLACK, termbox.BLACK)
        options.set_bold()
        f = Format()
        f.add(" %s" % self.custom_str, termbox.WHITE, termbox.BLACK)
        self.change_cells_format(0, 0, f)
        self.change_cells_format(self.w - len(options.s), 0, options)


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


class ListUI(Drawable):

    def __init__(self, tb, list):
        self.tb = tb
        self.list = list
        self.sel = 0
        self.start = 0

    def _fix_bounds(self):
        if len(self.list) > 0:
            self.sel = min(max(0, self.sel), len(self.list) - 1)
            if (self.sel - self.start) >= self.h:
                self.start = self.sel - self.h + 1
            if self.sel < self.start:
                self.start = self.sel
            self.start = min(max(0, self.start), len(self.list) - 1)

    def _format(self, o, y, p):
        s = "%5i %5i %s" % (p, y, str(o))
        return Format(s.ljust(self.w), termbox.RED if p == self.sel else
                termbox.WHITE)

    def draw(self):
        length = len(self.list)
        empty = Format("".ljust(self.w))
        for y in range(self.h):
            pos = y + self.start
            f = self._format(self.list[pos], y, pos) if y < length else empty
            self.change_cells_format(0, y, f)

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self._fix_bounds()

    def selected(self):
        return self.sel


class PlaylistUI(ListUI, StatusListener):

    def __init__(self, tb, status):
        super(PlaylistUI, self).__init__(tb, status.playlist)
        self.status = status
        self.status.add_listener(self)

    def _format(self, song, y, pos):
        left, right = Format(), Format()

        numw = 0
        if len(self.list) > 0:
            numw = int(math.floor(math.log10(len(self.list)))) + 2
        num_str = "%s " % str(pos + 1)
        time_str = " [%s] " % length_str(song.time)
        left.add(num_str.rjust(numw + 1), termbox.BLUE, termbox.BLACK)
        left.add(song.artist, termbox.RED, termbox.BLACK)
        left.add(" - ", termbox.WHITE, termbox.BLACK)
        left.add(song.title, termbox.YELLOW, termbox.BLACK)
        left.add(" (", termbox.WHITE, termbox.BLACK)
        left.add(song.album, termbox.GREEN, termbox.BLACK)
        left.add(")", termbox.WHITE, termbox.BLACK)

        right.add(time_str, termbox.BLUE, termbox.BLACK)

        if pos == self.sel:
            left.set_color(termbox.BLACK, termbox.WHITE)
            right.set_color(termbox.BLACK, termbox.WHITE)
            left.add("".ljust(max(0, self.w - len(left.s))), termbox.BLACK, termbox.WHITE)
        if song is self.status.current:
            left.set_bold()
            right.set_bold()
            left.replace(0, ">", termbox.BLUE, termbox.BLACK)
        return left, right

    def draw(self):
        length = len(self.list)
        for y in range(self.h):
            pos = y + self.start
            if pos < length:
                left, right = self._format(self.list[pos], y, pos)
                self.change_cells_format(0, y, left)
                self.change_cells_format(self.w - len(right.s), y, right)



    def playlist_updated(self):
        if len(self.status.playlist) > 0 and self.sel == -1:
            self.start = self.sel = 0
        else:
            self.start = self.sel = -1
        self._fix_bounds()


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
