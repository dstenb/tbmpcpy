class WrongArgException(Exception):

    def __init__(self, arg, description):
        pass


class Command(object):

    def __init__(self, res, name="a", desc="tjo"):
        self.res = res
        self.name = name
        self.description = desc

    def autocomplete(self, n, text):
        return [text]

    def execute(self, *args):
        pass


class CommandLine(object):

    def __init__(self, commands={}):
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

    def split(self):
        s = self.buf.split(" \t")
        return s[0] if len(s) > 0 else None, s[1:]

    def _autocomplete_clear(self):
        self.matched = None
        self.matched_pos = 0

    def _autocomplete_commands(self, start):
        if start:
            self.matched = filter(lambda k: k.startswith(start),
                    self.commands.keys())
        else:
            self.matched = self.commands.keys()

        if start and not start in self.matched:
            self.matched.insert(0, start)

        self.matched.sort()

        if len(self.matched) > 1:
            self.matched_pos = 1
            self.buf = self.matched[self.matched_pos]

    def _autocomplete_arg(self):
        pass

    def _autocomplete_next(self):
        self.matched_pos += 1
        if self.matched_pos >= len(self.matched):
            self.matched_pos = 0
        self.buf = self.matched[self.matched_pos]

    def autocomplete(self):
        cmd, args = self.split()

        if len(args) == 0 and not self.buf.endswith(" "):
            if self.matched:
                self._autocomplete_next()
            else:
                self._autocomplete_commands(cmd)
        else:
            self._autocomplete_arg(args)

cl = CommandLine({"aba": 1, "b": 2, "abba": 3})

cl.add("a")
print(cl.buf)
cl.autocomplete()
print(cl.buf)
cl.autocomplete()
print(cl.buf)
cl.autocomplete()
print(cl.buf)
cl.autocomplete()
print(cl.buf)
