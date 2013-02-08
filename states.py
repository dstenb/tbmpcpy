# -*- encoding: utf-8 -*-

from command import *
from commands import *
from components import *
from search import *
from status import *
from ui import *
import math
import sys


class Keybindings:
    def __init__(self, _ch={}, _key={}):
        self.by_ch = _ch
        self.by_key = _key

    def add_ch(self, ch, cpair):
        self.by_ch[ch] = cpair

    def add_ch_list(self, ch_list):
        self.by_ch.update(ch_list)

    def add_key(self, key, cpair):
        self.by_key[key] = cpair

    def add_key_list(self, key_list):
        self.by_key.update(key_list)

    def get(self, ch, key):
        p = self.by_ch.get(ch, None) or self.by_key.get(key, None)
        return p


class State(object):

    def __init__(self, listener, mpd, status, ui, msg, browser,
            default_keys=False):
        self.listener = listener
        self.mpd = mpd
        self.status = status
        self.browser = browser
        self.ui = ui
        self.msg = msg

        by_ch, by_key = {}, {}

        if default_keys:
            res = ResourceTuple(self.mpd, self.status, self.ui, self.browser)
            by_ch = {
                    # Application commands
                    "q": (QuitCommand(res), ()),

                    # Player control
                    "P": (ToggleCommand(res), ()),
                    "s": (StopCommand(res), ()),
                    "n": (NextCommand(res), ()),
                    "p": (PrevCommand(res), ()),

                    # States
                    "1": (ChangeStateCommand(self), ("playlist", )),
                    "2": (ChangeStateCommand(self), ("browser", )),
                    ":": (ChangeStateCommand(self), ("command", )),

                    # Launch commands
                    "c": (EnterCommand(self), ("consume ", True)),
                    "x": (EnterCommand(self), ("crossfade ", True))
            }
            by_key = {}

        self.bindings = Keybindings(by_ch, by_key)

    def activate(self, unused_args={}):
        pass

    def deactivate(self, state=None, d={}):
        if state:
            self.listener.change_state(state, d)
        else:
            self.listener.prev_state()

    def key_event(self, ch, key, unused_mod):
        t = self.bindings.get(ch, key)
        if t:
            cmd, args = t
            try:
                cmd.execute(*args)
            except CommandExecutionError, err:
                self.msg.error(unicode(err), 2)


class StateListener:

    def change_state(self, s, args={}):
        pass

    def prev_state(self, args={}):
        pass


class StateCommand(Command):
        def __init__(self, state):
            self.state = state


class ChangeStateCommand(StateCommand):
    def execute(self, new_state=None, d={}):
        self.state.deactivate(new_state, d)


class EnterCommand(StateCommand):
    def execute(self, start_string, autocomplete):
        d = {"start_string": start_string,
                "autocomplete": autocomplete}
        self.state.deactivate("command", d)


class PlaylistState(State):

    def __init__(self, *args):
        super(PlaylistState, self).__init__(*args, default_keys=True)

        self.search = PlaylistSearch(self.status.playlist)

        res = ResourceTuple(self.mpd, self.status, self.ui, self.browser)

        self.bindings.add_ch_list({
            "j": (MainRelativeSelectCommand(res), ("1", )),
            "k": (MainRelativeSelectCommand(res), ("-1", )),
            "g": (MainSelectCommand(res), ("1", )),
            "G": (MainSelectCommand(res), (str(sys.maxsize), )),
            "C": (PlaylistClearCommand(res), ()),
            "d": (PlaylistDeleteCommand(res), ()),
            "/": (ChangeStateCommand(self), ("search",
                {"search": self.search}))
        })
        self.bindings.add_key_list({
            termbox.KEY_ENTER: (PlayCommand(res), ()),
            termbox.KEY_ESC: (MainSearchCommand(res), ()),
            termbox.KEY_ARROW_DOWN: (MainRelativeSelectCommand(res), ("1", )),
            termbox.KEY_ARROW_UP: (MainRelativeSelectCommand(res), ("-1", )),
            termbox.KEY_TAB: (ChangeStateCommand(self), ("browser", ))
        })

    def activate(self, unused_args={}):
        self.ui.set_main(self.ui.playlist)
        self.ui.show_top(self.ui.playlist_bar)

#        if self.search.active:
#            self.ui.search.set_search(self.search)
#            self.ui.search.show()


class CommandState(State):

    def __init__(self, *args):
        super(CommandState, self).__init__(*args, default_keys=False)

        self.bindings.add_key_list({
            termbox.KEY_ARROW_DOWN: (self.IterCommand(self), (1, )),
            termbox.KEY_ARROW_UP: (self.IterCommand(self), (-1, )),
            termbox.KEY_ENTER: (self.ExecuteCommand(self), ()),
            termbox.KEY_BACKSPACE2: (self.RemoveLastCommand(self), ()),
            termbox.KEY_SPACE: (self.AddCommand(self), (" ", )),
            termbox.KEY_TAB: (self.AutocompleteCommand(self), (True, )),
            termbox.KEY_ESC: (ChangeStateCommand(self), ())
        })

        self._setup_commands()

    class AutocompleteCommand(StateCommand):
        def execute(self, down):
            self.state.commandline.autocomplete(down)

    class ExecuteCommand(StateCommand):
        def execute(self):
            self.state.execute()

    class AddCommand(StateCommand):
        def execute(self, s):
            self.state.commandline.add(s)

    class IterCommand(StateCommand):
        def execute(self, dir):
            if self.state.commandline.autocompleted():
                self.state.commandline.autocomplete(dir > 0)
            else:
                pass  # TODO: handle commandline history

    class RemoveLastCommand(StateCommand):
        def execute(self):
            self.state.commandline.remove_last()

    def _setup_commands(self):
        res = ResourceTuple(self.mpd, self.status, self.ui, self.browser)

        self.commands = {
                "clear": PlaylistClearCommand(res),
                "consume": boolean_option_command(res, "consume"),
                "crossfade": CrossfadeOptionCommand(res),
                "next": NextCommand(res),
                "playpause": ToggleCommand(res),
                "previous": PrevCommand(res),
                "q": QuitCommand(res),
                "quit": QuitCommand(res),
                "search": MainSearchCommand(res),
                "random": boolean_option_command(res, "random"),
                "repeat": boolean_option_command(res, "repeat"),
                "single": boolean_option_command(res, "single"),
                "stop": StopCommand(res),
                "update": BrowserUpdateCommand(res)
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

    def deactivate(self, s=None, d={}):
        self.commandline.clear()
        self.ui.command.hide()
        self.ui.command.fix_cursor()
        self.listener.prev_state()

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
        except CommandExecutionError, err:
            self.msg.error(unicode(err), 2)

        self.deactivate()

    def key_event(self, ch, key, unused_mod):
        t = self.bindings.get(ch, key)
        if t:
            cmd, args = t
            try:
                cmd.execute(*args)
            except CommandExecutionError, err:
                self.msg.error(unicode(err), 2)
        elif ch:
            self.commandline.add(ch)


class SearchState(State):

    def __init__(self, *args):
        super(SearchState, self).__init__(*args, default_keys=False)

        self.bindings.add_ch_list({
        })
        self.bindings.add_key_list({
            termbox.KEY_BACKSPACE2: (self.RemoveLastCommand(self), ()),
            termbox.KEY_SPACE: (self.AddCommand(self), (" ", )),
            termbox.KEY_ENTER: (self.ChangeStateCommand(self), (False, )),
            termbox.KEY_ESC: (self.ChangeStateCommand(self), (True, ))
        })

    class AddCommand(StateCommand):
        def execute(self, s):
            self.state.search.add(s)

    class ChangeStateCommand(StateCommand):
        def execute(self, clear):
            if clear:
                self.state.search.clear()
            self.state.deactivate()

    class RemoveLastCommand(StateCommand):
        def execute(self):
            self.state.search.remove_last()

    def activate(self, args={}):
        if not (self.ui.main and self.ui.main.is_list()):
            self.deactivate()
        self.search = args["search"]
        self.ui.search.set_search(self.search)
        self.ui.search.show()

    def deactivate(self, state=None, d={}):
        self.ui.search.hide()
        self.ui.search.fix_cursor()
        self.listener.prev_state()

    def key_event(self, ch, key, unused_mod):
        t = self.bindings.get(ch, key)
        if t:
            cmd, args = t
            try:
                cmd.execute(*args)
            except CommandExecutionError, err:
                self.msg.error(unicode(err), 2)
        elif ch:
            self.search.add(ch)


class BrowserState(State):

    def __init__(self, *args):
        super(BrowserState, self).__init__(*args, default_keys=True)

        self.search = BrowserSearch(self.browser)

        res = ResourceTuple(self.mpd, self.status, self.ui, self.browser)

        self.bindings.add_ch_list({
            "j": (MainRelativeSelectCommand(res), ("1", )),
            "k": (MainRelativeSelectCommand(res), ("-1", )),
            "g": (MainSelectCommand(res), ("1", )),
            "G": (MainSelectCommand(res), (str(sys.maxsize), )),
            "u": (BrowserGoUpCommand(res), ()),
            "U": (BrowserUpdateCommand(res), ()),
            "/": (ChangeStateCommand(self), ("search",
                {"search": self.search}))
        })
        self.bindings.add_key_list({
            termbox.KEY_ENTER: (BrowserEnterCommand(res), ()),
            termbox.KEY_ESC: (MainSearchCommand(res), ()),
            termbox.KEY_SPACE: (BrowserAddCommand(res), ()),
            termbox.KEY_BACKSPACE2: (BrowserGoUpCommand(res), ()),
            termbox.KEY_ARROW_DOWN: (MainRelativeSelectCommand(res), ("1", )),
            termbox.KEY_ARROW_UP: (MainRelativeSelectCommand(res), ("-1", )),
            termbox.KEY_TAB: (ChangeStateCommand(self), ("playlist", ))
        })

    def activate(self, unused_args={}):
        self.ui.set_main(self.ui.browser)
        self.ui.show_top(self.ui.browser_bar)
