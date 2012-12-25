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


class Match(object):

    def __init__(self, list):
        self.list = list
        self.pos = 0

    def current(self):
        if len(self.list) > 0:
            return self.list[self.pos]
        return None

    def select_next(self):
        self.pos += 1
        if self.pos >= len(self.list):
            self.pos = 0
        return self.current()


class CommandLine(Listenable):

    def __init__(self, commands={}):
        super(CommandLine, self).__init__()
        self.buf = ""
        self.commands = commands
        self.matched = None
        self.matched_pos = 0

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
        s = self.buf.split(" \t")
        return s[0] if len(s) > 0 else None, s[1:]

    def _autocomplete_clear(self):
        self.matched = None
        self.matched_pos = 0
        self.notify("matched_changed", self)

    def _autocomplete_commands(self, start):
        self.matched = []
        if start:
            if not start in self.commands:
                self.matched.append((start, None))
            for k, v in self.commands.iteritems():
                if k.startswith(start):
                    self.matched.append((k, v))
        else:
            self.matched = self.commands.items()
            self.matched.insert(0, ("", None))

        self.matched.sort(key=lambda v: v[0])

        if len(self.matched) > 1:
            self.matched_pos = 1
            self.buf = self.matched[self.matched_pos][0]
        else:  # No matches
            self.matched = None
            self.matched_pos = 0
        print(self.matched)
        self.notify("matched_changed", self)
        if self.matched:
            self.notify("matched_selected_changed", self)

    def _autocomplete_arg(self, cmd, args):
        pass

    def _autocomplete_next(self):
        self.matched_pos += 1
        if self.matched_pos >= len(self.matched):
            self.matched_pos = 0

        if self.matched[self.matched_pos]:
            self.buf = self.matched[self.matched_pos][0]
        else:
            self.buf = ""
        self.notify("matched_selected_changed", self)

    def autocomplete(self):
        cmd, args = self.split()

        if len(args) == 0 and not self.buf.endswith(" "):
            if self.matched:
                self._autocomplete_next()
            else:
                self._autocomplete_commands(cmd)
        else:
            self._autocomplete_arg(cmd, args)

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
