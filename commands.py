import sys

from command import *


class NextCommand(Command):

    def __init__(self, res):
        super(NextCommand, self).__init__(res, "next",
                "Play next song in playlist")

    def execute(self, *args):
        try:
            self.res["mpd"].player("next")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'next' command")


class PrevCommand(Command):

    def __init__(self, res):
        super(PrevCommand, self).__init__(res, "prev",
                "Play previous song in playlist")

    def execute(self, *args):
        try:
            self.res["mpd"].player("previous")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'prev' command")


class StopCommand(Command):

    def __init__(self, res):
        super(StopCommand, self).__init__(res, "stop",
                "Stop playing")

    def execute(self, *args):
        try:
            self.res["mpd"].player("stop")
        except CommandError:
            raise CommandExecutionError("Couldn't execute 'stop' command")

class ToggleCommand(Command):

    def __init__(self, res):
        super(ToggleCommand, self).__init__(res, "toggle",
                "Play/pause")

    def execute(self, *args):
        if self.res["status"].state != "play":
            self.res["mpd"].player("play")
        else:
            self.res["mpd"].player("pause")


class QuitCommand(Command):

    def __init__(self, res):
        super(QuitCommand, self).__init__(res, "quit",
                "Close the program")

    def execute(self, *args):
        sys.exit(args[0] if len(args) > 0 else 0)
