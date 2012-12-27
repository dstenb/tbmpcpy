# -*- encoding: utf-8 -*-

from command import *
from commands import *
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
                    ":": lambda: self.listener.change_state("command"),
                    "/": lambda: self.listener.change_state("search"),

                    # Launch commands
                    "c": lambda: self.deactivate("command",
                        {"start_string": "consume ", "autocomplete": True }),
                    "x": lambda: self.deactivate("command",
                        {"start_string": "crossfade ", "autocomplete": True })
            }
            by_key = {}

        self.bindings = Keybindings(by_ch, by_key)

    def activate(self, unused_args={}):
        pass

    def deactivate(self):
        pass

    def key_event(self, ch, key, unused_mod):
        func = self.bindings.get(ch, key)
        if func:
            func()


class StateListener:

    def change_state(self, s, args={}):
        pass

    def prev_state(self, args={}):
        pass


class PlaylistState(State):

    def __init__(self, *args):
        super(PlaylistState, self).__init__(*args, default_keys=True)

        self.bindings.add_ch_list({
            "j": lambda: self.ui.playlist.select(1, True),
            "k": lambda: self.ui.playlist.select(-1, True),
            "g": lambda: self.ui.playlist.select(0),
            "G": lambda: self.ui.playlist.select(sys.maxsize)
        })
        self.bindings.add_key_list({
            termbox.KEY_ENTER: lambda:
                self.mpd.player("play", self.ui.playlist.selected())
                    if self.ui.playlist.selected() >= 0 else False,
            termbox.KEY_ARROW_UP: lambda: self.ui.playlist.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.ui.playlist.select(1, True)
        })

    def activate(self, unused_args={}):
        self.ui.set_main(self.ui.playlist)

    def deactivate(self, s, d):
        self.listener.change_state(s, d)


class CommandState(State):

    def __init__(self, *args):
        super(CommandState, self).__init__(*args, default_keys=False)

        self.bindings.add_key_list({
            termbox.KEY_ARROW_DOWN: lambda: self.arrow_down(),
            termbox.KEY_ARROW_UP: lambda: self.arrow_up(),
            termbox.KEY_ENTER: lambda: self.execute(),
            termbox.KEY_BACKSPACE2: lambda: self.commandline.remove_last(),
            termbox.KEY_SPACE: lambda: self.commandline.add(" "),
            termbox.KEY_TAB: lambda: self.commandline.autocomplete(),
            termbox.KEY_ESC: lambda: self.deactivate()
        })

        self._setup_commands()

    def _setup_commands(self):
        res = ResourceTuple(self.mpd, self.status, self.ui)

        self.commands = {
                "consume": boolean_option_command(res, "consume"),
                "random": boolean_option_command(res, "random"),
                "repeat": boolean_option_command(res, "repeat"),
                "single": boolean_option_command(res, "single"),
                "crossfade": CrossfadeOptionCommand(res),
                "next": NextCommand(res),
                "previous": PrevCommand(res),
                "playpause": ToggleCommand(res),
                "q": QuitCommand(res),
                "quit": QuitCommand(res),
                "stop": StopCommand(res)
        }

        number_command = MainSelectCommand(res)

        self.commandline = CommandLine(self.commands, number_command)
        self.ui.command.set_command_line(self.commandline)

    def activate(self, args={}):
        self.ui.command.show()
        self.ui.command.fix_cursor()

        if "start_string" in args:
            self.commandline.add(args["start_string"])

        if args.get("autocomplete", False):
            self.commandline.autocomplete()

    def deactivate(self):
        self.commandline.clear()
        self.ui.command.hide()
        self.ui.command.fix_cursor()
        self.listener.prev_state()

    def arrow_down(self):
        if self.commandline.autocompleted():
            self.commandline.autocomplete(True)
        else:
            pass  # TODO: handle commandline history

    def arrow_up(self):
        if self.commandline.autocompleted():
            self.commandline.autocomplete(False)
        else:
            pass  # TODO: handle commandline history

    def execute(self):
        try:
            self.commandline.execute()
        except UnknownCommandException, err:
            self.msg.error("Unknown command: " + unicode(err), 2)
        except MissingArgException, err:
            self.msg.error("Missing argument (%s): " % err.description, 2)
        except WrongArgException, err:
            self.msg.error("Invalid argument '%s' (%s)" %
                    (err.arg, err.description), 2)

        self.deactivate()

    def key_event(self, ch, key, unused_mod):
        func = self.bindings.get(ch, key)
        if func:
            func()
        elif ch:
            self.commandline.add(ch)


class SearchState(State):

    def __init__(self, *args):
        super(SearchState, self).__init__(*args, default_keys=False)

        self.bindings.add_ch_list({
        })
        self.bindings.add_key_list({
            termbox.KEY_ESC: lambda: self.deactivate()
        })

    def activate(self, unused_args={}):
        if not (self.ui.main and self.ui.main.is_list()):
            self.deactivate()

    def deactivate(self, d={}):
        self.listener.prev_state(d)


class BrowserState(State):

    def __init__(self, *args):
        super(BrowserState, self).__init__(*args, default_keys=True)

        self.bindings.add_ch_list({
            "j": lambda: self.ui.browser.select(1, True),
            "k": lambda: self.ui.browser.select(-1, True),
            "g": lambda: self.ui.browser.select(0),
            "G": lambda: self.ui.browser.select(sys.maxsize),
        })
        self.bindings.add_key_list({
            termbox.KEY_ARROW_UP: lambda: self.ui.playlist.select(-1, True),
            termbox.KEY_ARROW_DOWN: lambda: self.ui.playlist.select(1, True)
        })

    def activate(self, unused_args={}):
        self.ui.set_main(self.ui.browser)

    def deactivate(self, s, d):
        self.listener.change_state(s, d)
