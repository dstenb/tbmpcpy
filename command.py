from collections import namedtuple

from common import *


class WrongArgException(Exception):

    def __init__(self, arg, description):
        pass


class UnknownCommandException(Exception):

    def __init__(self, cmd):
        super(UnknownCommandException, self).__init__(cmd)


class CommandExecutionError(Exception):

    def __init__(self, err):
        super(CommandExecutionError, self).__init__(err)


class Command(object):

    def __init__(self, res, name="unknown", description="no description"):
        self.res = res
        self.name = name
        self.description = description

    def autocomplete(self, unused_n, text):
        return [text]

    def execute(self, *args):
        pass


class CommandLineListener(object):

    def matched_changed(self, cl):
        pass


MatchTuple = namedtuple("MatchTuple", "name command")


class Match(object):

    def __init__(self, matches, prefix):
        self.matches = matches
        self.matches.sort(key=lambda v: v[0])
        self.prefixt = MatchTuple(prefix or "", None)
        self.pos = 0

    def __getitem__(self, index):
        return self.matches[index]

    def __len__(self):
        return len(self.matches)

    def current(self):
        if self.pos >= 0:
            return self.matches[self.pos]
        return self.prefixt

    def select_prev(self):
        if self.pos < 0:
            self.pos = len(self.matches) - 1
        else:
            self.pos -= 1
        return self.current()

    def select_next(self):
        self.pos += 1
        if self.pos >= len(self.matches):
            self.pos = -1
        return self.current()


class CommandLine(Listenable):

    def __init__(self, commands={}):
        super(CommandLine, self).__init__()
        self.buf = ""
        self.commands = commands
        self.matched = None

    def add(self, ch):
        self.buf += ch
        self._autocomplete_clear()

    def remove_last(self):
        self.buf = self.buf[:-1]
        self._autocomplete_clear()

    def clear(self):
        self.buf = ""
        self._autocomplete_clear()

    def split(self):
        s = self.buf.split(" ")
        return s[0] if len(s) > 0 else None, s[1:]

    def _autocomplete_clear(self):
        self.matched = None
        self.notify("matched_changed", self)

    def _autocomplete_commands(self, start):
        matches = []
        for k, v in self.commands.iteritems():
            if not start or k.startswith(start):
                matches.append(MatchTuple(k, v))

        if len(matches) > 0:
            self.matched = Match(matches, start)
            self.buf = self.matched.current().name
        else:  # No matches
            self.matched = None
        self.notify("matched_changed", self)
        if self.matched:
            self.notify("matched_selected_changed", self)

    def _autocomplete_arg(self, cmd, args):
        pass

    def _autocomplete_prev(self):
        self.matched.select_prev()
        self.buf = self.matched.current().name
        self.notify("matched_selected_changed", self)

    def _autocomplete_next(self):
        self.matched.select_next()
        self.buf = self.matched.current().name
        self.notify("matched_selected_changed", self)

    def autocomplete(self, n=True):
        cmd, args = self.split()

        if len(args) == 0 and not self.buf.endswith(" "):
            if self.matched:
                if n:
                    self._autocomplete_next()
                else:
                    self._autocomplete_prev()
            else:
                self._autocomplete_commands(cmd)
        else:
            self._autocomplete_arg(cmd, args)

    def autocompleted(self):
        return self.matched != None

    def execute(self):
        cmd, args = self.split()

        if cmd:
            if cmd.isdigit():
                #TODO: handle setting
                pass
            elif cmd in self.commands:
                self.commands[cmd].execute(*args)
                pass
            else:
                raise UnknownCommandException(cmd)
