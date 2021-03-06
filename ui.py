import sys
import termbox


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


class Drawable(object):

    def __init__(self, tb, x=0, y=0, w=1, h=1):
        self.tb = tb
        self.x, self.y, self.w, self.h = x, y, w, h

    def change_cells_format(self, ix, y, format, w=-1, pad=u" "):
        fg, bg = termbox.WHITE, termbox.BLACK
        ix += self.x

        for x, c in enumerate(format.s):
            fg, bg = format.colors[x]
            if self.x + x >= 0 and self.y + y >= 0:
                self.tb.change_cell(ix + x, self.y + y, ord(c), fg, bg)
        for x in xrange(ix + len(format.s), ix + max(w, len(format.s))):
            if self.x + x >= 0 and self.y + y >= 0:
                self.tb.change_cell(self.x + x, self.y + y, ord(pad), fg, bg)

    def draw(self):
        pass

    def get_dim(self):
        return [self.x, self.y, self.w, self.h]


class ComponentListener(object):

    def dim_changed(self, o):
        print ("%s: dim_changed: %i %i %i %i" % (str(o), o.x, o.y, o.w, o.h))

    def preferred_dim_changed(self, o):
        print ("%s: preferred_dim_changed: %i %i" % (str(o), o.prefw, o.prefh))

    def visibility_changed(self, o):
        print ("%s: visibility_changed: %r" % (str(o), o.visible))


class Component(Drawable):

    def __init__(self, tb):
        super(Component, self).__init__(tb)
        self.listeners = []
        self.visible = True
        self.prefw, self.prefh = -1, -1

    def _handle_resize(self):
        pass

    def add_listener(self, o):
        if not o in self.listeners:
            self.listeners.append(o)

    def remove_listener(self, o):
        if o in self.listeners:
            self.listeners.remove(o)

    def notify(self, func, *args):
        for o in self.listeners:
            getattr(o, func)(self, *args)

    def set_dim(self, x, y, w, h, set_stored=True, notify=True):
        if set_stored:
            self.stored_dim = [x, y, w, h]
        if self.visible:
            self.x, self.y, self.w, self.h = x, y, w, h
            if notify:
                self.notify("dim_changed")
            self._handle_resize()

    def set_pref_dim(self, w, h):
        self.prefw, self.prefh = w, h
        self.notify("preferred_dim_changed")

    def show(self):
        if not self.visible:
            self.visible = True
            self.set_dim(*self.stored_dim, notify=False)
            self.notify("visibility_changed")

    def hide(self):
        if self.visible:
            self.visible = False
            self.stored_dim = [self.x, self.y, self.w, self.h]
            self.set_dim(-1, -1, 0, 0, False, False)
            self.notify("visibility_changed")

    def toggle_visibility(self):
        self.hide() if self.visible else self.show()


class SolidComponent(Component):

    def __init__(self, tb, c):
        super(SolidComponent, self).__init__(tb)
        self.c = c

    def draw(self):
        for y in xrange(self.h):
            f = Format()
            f.add(str(y) + "\\" * self.w, self.c, termbox.BLACK)
            self.change_cells_format(0, y, f)


class VerticalLayout(Component, ComponentListener):

    def __init__(self, tb):
        super(VerticalLayout, self).__init__(tb)
        self.set_pref_dim(-1, -1)
        self.top = []
        self.main = None
        self.bottom = []

        self.top_strut = 0
        self.bottom_strut = 0

    def draw(self):
        self.tb.clear()
        if self.main:
            self.main.draw()
        for c in self.top:
            if c.visible:
                c.draw()
        for c in self.bottom:
            if c.visible:
                c.draw()
        self.tb.present()

    def add_top(self, c):
        c.add_listener(self)
        self.top.append(c)
        self.fix()

    def fix_top(self):
        y = 0
        for c in self.top:
            if c.visible:
                h = max(c.prefh, 1)
                c.set_dim(0, y, self.w, h, True, False)
                y += h
        self.top_strut = y

    def remove_top(self, c):
        c.remove_listener(self)
        self.top.remove(c)
        self.fix()

    def add_bottom(self, c):
        c.add_listener(self)
        self.bottom.append(c)
        self.fix()

    def fix_bottom(self):
        y = 0
        for c in reversed(self.bottom):
            if c.visible:
                h = max(c.prefh, 1)
                y += h
                c.set_dim(0, self.h - y, self.w, h, True, False)
        self.bottom_strut = y

    def remove_bottom(self, c):
        c.remove_listener(self)
        self.bottom.remove(c)
        self.fix()

    def fix_main(self):
        if self.main:
            self.main.set_dim(0, self.top_strut, self.w, self.h -
                    self.top_strut - self.bottom_strut, True, False)
            self.main.show()  # Force main to be shown

    def set_main(self, c):
        if self.main:
            self.main.remove_listener(self)
        c.add_listener(self)
        self.main = c
        self.fix()

    def fix(self):
        self.fix_top()
        self.fix_bottom()
        self.fix_main()

    def set_size(self, w, h):
        self.w = w
        self.h = h
        self.fix()

    def dim_changed(self, o):
        if not (o in self.top or o in self.bottom or o == self.main):
            print("unknown " + str(o))
            sys.exit(0)
        self.fix()

    def preferred_dim_changed(self, o):
        if not (o in self.top or o in self.bottom or o == self.main):
            print("unknown " + str(o))
            sys.exit(0)
        self.fix()

    def visibility_changed(self, o):
        if not (o in self.top or o in self.bottom or o == self.main):
            print("unknown " + str(o))
            sys.exit(0)
        self.fix()
