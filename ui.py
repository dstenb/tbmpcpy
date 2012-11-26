#!/usr/bin/python
# -*- encoding: utf-8 -*-

import termbox

SPACE = u" "
HLINE = u"─"


def _cl(s, fg, bg):
    return [[fg, bg] for x in xrange(len(s))]


def _replace_color(colors, new, pos):
    return colors[0:pos] + new + colors[pos + len(new):]


class Format:

    def __init__(self, s="", fg=termbox.WHITE, bg=termbox.BLACK):
        self.s = s
        self.colors = _cl(s, fg, bg)

    def add(self, ns, fg, bg):
        self.s += ns
        self.colors += _cl(ns, fg, bg)

    def replace(self, pos, ns, fg, bg):
        if pos > len(self.s):
            self.add("".ljust(pos - len(self.s)), *self.colors[-1])
            self.add(ns, fg, bg)
        else:
            self.s = self.s[0:pos] + ns + self.s[pos + len(ns):]
            self.colors = _replace_color(self.colors, _cl(ns, fg, bg), pos)

    def set_bold(self):
        for v in self.colors:
            v[0] |= termbox.BOLD

    def set_color(self, fg, bg):
        self.colors = _cl(self.s, fg, bg)


class Drawable:

    def __init__(self, tb):
        self.tb = tb
        self.set_dim(0, 0, 0, 0)
        self.set_pref_dim(-1, -1)

    def change_cell(self, x, y, c, fg, bg):
        if self.x + x < self.tb.width() and self.y + y < self.tb.height():
            self.tb.change_cell(self.x + x, self.y + y, c, fg, bg)

    def change_cells(self, ix, y, us, fg, bg, w=-1, pad=SPACE):
        if w >= 0 and w < len(us):
            us = us[0:w - len(us)]
        for x, c in enumerate(us, ix):
            self.change_cell(x, y, ord(c), fg, bg)
        for x in xrange(ix + len(us), ix + max(w, len(us))):
            self.change_cell(x, y, ord(pad), fg, bg)

    def change_cells_format(self, ix, y, format, w=-1, pad=SPACE):
        fg, bg = termbox.WHITE, termbox.BLACK

        for x, c in enumerate(format.s):
            fg, bg = format.colors[x]
            self.change_cell(x + ix, y, ord(c), fg, bg)
        for x in xrange(ix + len(format.s), ix + max(w, len(format.s))):
            self.change_cell(x, y, ord(pad), fg, bg)

    def draw(self):
        self

    def get_dim(self):
        return [x, y, w, h]

    def set_dim(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def set_pref_dim(self, w, h):
        self.prefw = w
        self.prefh = h


class UI(Drawable):

    def __init__(self, tb):
        self.tb = tb
        self.w = tb.width()
        self.h = tb.height()
        self.t = self.m = self.b = None

    def draw(self):
        self.tb.clear()
        if self.m:
            self.m.draw()
        if self.t:
            self.t.draw()
        if self.b:
            self.b.draw()
        self.tb.present()

    def set_bottom(self, _bottom, update=True):
        self.b = _bottom
        h = max(self.b.prefh, 1)
        self.b.set_dim(0, self.h - h, self.w, h)
        if update:
            self.update()

    def set_main(self, _main, update=True):
        self.m = _main
        if update:
            self.update()

    def set_top(self, _top, update=True):
        self.t = _top
        if self.t:
            self.t.set_dim(0, 0, self.w, max(self.t.prefh, 1))
        if update:
            self.update()

    def update(self):
        y = self.t.h if self.t else 0
        sh = (self.b.h if self.b else 0) + (self.t.h if self.t else 0)
        if (self.m):
            self.m.set_dim(0, y, self.w, self.h - sh)

    def update_size(self, w, h):
        self.w = w
        self.h = h

        self.set_bottom(self.b, False)
        self.set_top(self.t, False)
        self.update()
