import sys

from command import *
from components import *
from wrapper import *


ResourceTuple = namedtuple("ResourceTuple", "mpd status ui browser")


class ResCommand(Command):

    def __init__(self, res, name="unknown", description=""):
        super(ResCommand, self).__init__(name, description)

        self.mpd = res.mpd
        self.status = res.status
        self.ui = res.ui
        self.browser = res.browser


#### Playback control commands ####
class NextCommand(ResCommand):

    def __init__(self, res):
        super(NextCommand, self).__init__(res, "next",
                "Play next song in playlist")

    def execute(self, *unused_args):
        try:
            self.mpd.player("next")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'next' command")


class PrevCommand(ResCommand):

    def __init__(self, res):
        super(PrevCommand, self).__init__(res, "prev",
                "Play previous song in playlist")

    def execute(self, *unused_args):
        try:
            self.mpd.player("previous")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'prev' command")


class StopCommand(ResCommand):

    def __init__(self, res):
        super(StopCommand, self).__init__(res, "stop", "Stop playing")

    def execute(self, *unused_args):
        try:
            self.mpd.player("stop")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'stop' command")


class PlayCommand(ResCommand):

    def __init__(self, res):
        super(PlayCommand, self).__init__(res, "play", "Play song")

    def execute(self, *args):
        try:
            if self.status.playlist.sel >= 0:
                self.mpd.player("play", self.status.playlist.sel)
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'play' command")


class ToggleCommand(ResCommand):

    def __init__(self, res):
        super(ToggleCommand, self).__init__(res, "toggle", "Play/pause")

    def execute(self, *unused_args):
        s = "play" if self.status.state != "play" else "pause"
        try:
            self.mpd.player(s)
        except CommandError:
            raise CommandExecutionError("Couldn't execute '%s' command" % s)


#### Playback options commands ####
class BooleanOptionCommand(ResCommand):

    def __init__(self, res, cmd, name, desc):
        super(BooleanOptionCommand, self).__init__(res, name, desc)
        self.cmd = cmd

    def autocomplete(self, n, arg):
        matches = []
        if n == 0:
            if "true".startswith(arg):
                matches.append(MatchTuple("true", None))
            if "false".startswith(arg):
                matches.append(MatchTuple("false", None))
        return matches

    def execute(self, *args):
        if len(args) == 0:
            raise MissingArgException("requires one argument")
        elif args[0] not in ("true", "false"):
            raise WrongArgException(args[0], "expected true/false")
        try:
            self.mpd.option(self.cmd, 1 if args[0] == "true" else 0)
        except CommandError:
            raise CommandExecutionError("Couldn't execute '%s' command" %
                    self.cmd)


class IntegerOptionCommand(ResCommand):

    def __init__(self, res, cmd, name, desc):
        super(IntegerOptionCommand, self).__init__(res, name, desc)
        self.cmd = cmd

    def execute(self, *args):
        if len(args) == 0:
            raise MissingArgException("requires one argument")
        elif not args[0].isdigit():
            raise WrongArgException(args[0], "expected an integer")
        try:
            self.mpd.option(self.cmd, int(args[0]))
        except CommandError:
            raise CommandExecutionError("Couldn't execute '%s' command" %
                    self.cmd)


class CrossfadeOptionCommand(IntegerOptionCommand):

    def __init__(self, res):
        super(CrossfadeOptionCommand, self).__init__(res, "crossfade",
                "crossfade", "Set crossfade")

    def autocomplete(self, n, arg):
        matches = []
        if n == 0:
            current = self.status.options["xfade"]

            if "0".startswith(arg):
                matches.append(MatchTuple("0", "Disable crossfade"))
            if str(current).startswith(arg):
                matches.append(MatchTuple(str(current), "Current value"))
        return matches


def boolean_option_command(res, name):
    d = {"consume": ["consume", "consume", "Set consume mode"],
            "single": ["single", "single", "Set single mode"],
            "random": ["random", "random", "Set random mode"],
            "repeat": ["repeat", "repeat", "Set random mode"]}
    return BooleanOptionCommand(res, *d[name])


#### Playlist commands ####
class PlaylistClearCommand(ResCommand):

    def __init__(self, res):
        super(PlaylistClearCommand, self).__init__(res, "clear",
                "Clear the playlist")

    def execute(self, *args):
        try:
            self.mpd.clear()
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'clear' command")


class PlaylistGoToCurrentCommand(ResCommand):

    def __init__(self, res):
        super(PlaylistGoToCurrentCommand, self).__init__(res, "current",
                "Go to current")

    def execute(self, *args):
        try:
            if self.status.current != None:
                self.status.playlist.select(self.status.current.pos)
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'clear' command")


#### Browser commands ####
class BrowserAddCommand(ResCommand):

    def __init__(self, res):
        super(BrowserAddCommand, self).__init__(res, "add",
                "Add browser items to playlist")

    def execute(self, *args):
        if isinstance(self.ui.main, BrowserUI):
            selected = self.browser.selected()
            if selected != None and selected.ntype in ("directory", "song"):
                self.mpd.add(unicode(selected.path))
                self.browser.select(1, True)


class BrowserUpdateCommand(ResCommand):

    def __init__(self, res):
        super(BrowserUpdateCommand, self).__init__(res, "update",
                "Update the currently selected directory")

    def execute(self, *args):
        if len(args) == 0:
            self.mpd.update(self.browser.path_str("/"))
        else:
            self.mpd.update()


class BrowserEnterCommand(ResCommand):

    def __init__(self, res):
        super(BrowserEnterCommand, self).__init__(res, "etner",
                "Enter directory/load file")

    def execute(self, *args):
        self.browser.enter()


class BrowserGoUpCommand(ResCommand):

    def __init__(self, res):
        super(BrowserGoUpCommand, self).__init__(res, "go_up",
                "Go to the parent directory")

    def execute(self, *unused_args):
        self.browser.go_up()


#### Application-specific commands ####
class MainSelectCommand(ResCommand):

    def __init__(self, res):
        super(MainSelectCommand, self).__init__(res, "", "")

    def execute(self, *args):
        if len(args) == 0:
            raise MissingArgException("requires one argument")
        elif not args[0].isdigit():
            raise WrongArgException(args[0], "expected an integer")
        digit = int(args[0])

        if self.ui.main and self.ui.main.is_list():
            self.ui.main.select(digit - 1)


class MainRelativeSelectCommand(ResCommand):

    def __init__(self, res):
        super(MainRelativeSelectCommand, self).__init__(res, "", "")

    def execute(self, *args):
        if len(args) == 0:
            raise MissingArgException("requires one argument")
        index = int(args[0])

        if self.ui.main and self.ui.main.is_list():
            self.ui.main.select(index, True)


class QuitCommand(ResCommand):

    def __init__(self, res):
        super(QuitCommand, self).__init__(res, "quit", "Close the program")

    def execute(self, *args):
        sys.exit(args[0] if len(args) > 0 else 0)
