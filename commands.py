import sys

from command import *
from wrapper import *


#### Playback control commands ####
class NextCommand(Command):

    def __init__(self, res):
        super(NextCommand, self).__init__(res, "next",
                "Play next song in playlist")

    def execute(self, *unused_args):
        try:
            self.res.mpd.player("next")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'next' command")


class PrevCommand(Command):

    def __init__(self, res):
        super(PrevCommand, self).__init__(res, "prev",
                "Play previous song in playlist")

    def execute(self, *unused_args):
        try:
            self.res.mpd.player("previous")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'prev' command")


class StopCommand(Command):

    def __init__(self, res):
        super(StopCommand, self).__init__(res, "stop",
                "Stop playing")

    def execute(self, *unused_args):
        try:
            self.res.mpd.player("stop")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'stop' command")


class ToggleCommand(Command):

    def __init__(self, res):
        super(ToggleCommand, self).__init__(res, "toggle",
                "Play/pause")

    def execute(self, *unused_args):
        if self.res.status.state != "play":
            self.res.mpd.player("play")
        else:
            self.res.mpd.player("pause")


#### Playback options commands ####
class BooleanOptionCommand(Command):

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
            self.res.mpd.option(self.cmd, 1 if args[0] == "true" else 0)
        except CommandError:
            raise CommandExecutionError("Couldn't execute '%s' command" %
                    self.cmd)


def boolean_option_command(res, name):
    d = {"consume": ["consume", "consume", "Set consume mode"],
            "single": ["single", "single", "Set single mode"],
            "random": ["random", "random", "Set random mode"],
            "repeat": ["repeat", "repeat", "Set random mode"]}
    return BooleanOptionCommand(res, *d[name])


#### Application-specific commands ####
class QuitCommand(Command):

    def __init__(self, res):
        super(QuitCommand, self).__init__(res, "quit",
                "Close the program")

    def execute(self, *args):
        sys.exit(args[0] if len(args) > 0 else 0)
