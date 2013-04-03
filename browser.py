#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile, IGNORECASE
import traceback

from common import Listenable
from list import List
from status import Song
from wrapper import MPDWrapper


class Path(object):

    def __init__(self, s=""):
        self.list = []

        for o in s.split("/"):
            self.push(o)

    def __str__(self):
        return "/".join(self.list)

    def copy(self):
        return Path(unicode(self))

    def name(self):
        if len(self.list) > 0:
            return self.list[-1]
        return None

    def pop(self):
        if len(self.list) > 0:
            del self.list[-1]

    def push(self, s):
        if len(s) > 0:
            self.list.append(s)


class BrowserNode(object):

    def __init__(self, mpd, parent, ntype):
        self.mpd = mpd
        self.parent = parent
        self.ntype = ntype


class SongNode(BrowserNode):

    def __init__(self, mpd, data, parent):
        super(SongNode, self).__init__(mpd, parent, "song")
        self.data = data
        self.path = Path(data.file)

    def __str__(self):
        return "%s - %s (%s)" % (self.data.artist,
                self.data.title, self.data.album)


class PlaylistNode(BrowserNode):

    def __init__(self, mpd, data, parent):
        super(PlaylistNode, self).__init__(mpd, parent, "playlist")
        self.data = data
        self.path = Path(data)

    def __str__(self):
        return self.data


class InternalNode(BrowserNode):

    def __init__(self, mpd, parent, ntype):
        self.mpd = mpd
        self.parent = parent
        self.ntype = ntype
        self.children = []
        self.sel = -1

    def __getitem__(self, index):
        return self.children[index]

    def __len__(self):
        return len(self.children)

    def find_next(self, reg):
        rl = compile(reg, IGNORECASE)
        # TODO beautify
        for i in range(self.sel + 1, len(self)) + range(0, self.sel):
            if rl.search(unicode(self[i])):
                return i
        return -1

    def select(self, index, rel=False):
        self.sel = (self.sel + index) if rel else index
        self.sel = min(max(0, self.sel), len(self) - 1)
        return self.sel

    def select_node(self, node):
        self.select(self.children.index(node))

    def selected(self):
        if self.sel >= 0:
            return self.children[self.sel]
        return None


class DirectoryNode(InternalNode):

    def __init__(self, mpd, path, parent):
        super(DirectoryNode, self).__init__(mpd, parent, "directory")
        self.path = path

    def __str__(self):
        return self.path.name() + "/"

    def load(self):
        children = []

        try:
            for v in self.mpd.ls(unicode(self.path)):
                if "directory" in v:
                    c = DirectoryNode(self.mpd, Path(v["directory"]), self)
                    c.load()
                    children.append(c)
                elif "playlist" in v:
                    c = PlaylistNode(self.mpd, v["playlist"], self)
                    #children.append(c)
                elif "file" in v:
                    c = SongNode(self.mpd, Song(v), self)
                    children.append(c)
        except:
            traceback.print_exc()
            raise

        # Add links to root and previous directory
        if self.parent != None:
            children.insert(0, LinkNode(self.mpd, self, Path(), "/"))
            children.insert(1, LinkNode(self.mpd, self,
                self.parent.path.copy(), "../"))

        self.children = children
        self.select(0)

    def lookup(self, name):
        for n in self.children:
            if n.path.name() and n.path.name() == name:
                return n
        return None


class SearchNode(InternalNode):

    def __init__(self, mpd, s):
        super(InternalNode, self).__init__(mpd, None, "search")
        self.string = s
        self.rl = map(lambda s: compile(s, IGNORECASE), self.string.split())
        self.path = Path()

    def _search(self, node):
        for n in node.children:
            if n.ntype == "directory":
                self._search(n)
            elif n.ntype == "song" and n.data.matches_all(self.rl):
                self.children.append(n)

    def search(self, tree):
        self.children = []
        self._search(tree)
        self.select(0)


class LinkNode(BrowserNode):

    def __init__(self, mpd, parent, path, name=None):
        super(LinkNode, self).__init__(mpd, parent, "link")
        self.name = name if name != None else path.name()
        self.path = path

    def __str__(self):
        return self.name


class Browser(Listenable):

    def __init__(self, mpd):
        super(Browser, self).__init__()
        self.mpd = mpd
        self.tree = DirectoryNode(mpd, Path(), None)
        self.curr_node = None
        self.prev_node = None
        self.search_node = None

    def _set_selected(self, node):
        if node:
            self.curr_node = node
            self.notify("browser_node_changed", self)

    def enter(self):
        selnode = self.curr_node.selected()

        if selnode != None:
            if selnode.ntype == "song":
                self.mpd.add_and_play(selnode.data.file)
            elif selnode.ntype == "playlist":
                print(selnode.data)  # TODO
            elif selnode.ntype == "directory":
                self._set_selected(selnode)
            elif selnode.ntype == "link":
                self.curr_node.select(0)
                self.go_to(selnode.path)

    def find_next(self, reg):
        return self.curr_node.find_next(reg)

    def go_to(self, path):
        node = self.tree
        for p in path.list:
            node = node.lookup(p)
            if node == None:
                return False
        if node.ntype == "song":
            node.parent.select_node(node)
            self._set_selected(node.parent)
        elif node.ntype == "directory":
            self._set_selected(node)
        return True

    def go_up(self):
        if self.curr_node and self.curr_node.parent:
            self.curr_node.select(0)  # Restore selected for current node
            self._set_selected(self.curr_node.parent)

    def load(self):
        self.tree.load()
        if self.search_active():
            self.search(None)
        self._set_selected(self.tree)

    def path_str(self, delim="/"):
        if self.curr_node != None:
            return delim.join(self.curr_node.path.list)
        return ""

    def _search_start(self, s):
        self.search_node = SearchNode(self.mpd, s)
        self.search_node.search(self.tree)
        self.prev_node = self.curr_node
        self.curr_node = self.search_node
        self.notify("browser_search_started", self)

    def _search_stop(self):
        self.curr_node = self.prev_node
        self.search_node = None
        self.notify("browser_search_stopped", self)

    def search(self, s):
        if self.curr_node is self.search_node:
            self._search_stop()
        if s != None:
            self._search_start(s)

    def search_active(self):
        return self.search_node != None

    def select(self, index, rel=False):
        self.curr_node.select(index, rel)
        self.notify("browser_selected_changed", self)

    def selected(self):
        return self.curr_node.selected()


class BrowserListener(object):

    def browser_node_changed(self, browser):
        pass

    def browser_selected_changed(self, browser):
        pass

    def browser_search_started(self, browser):
        pass

    def browser_search_stopped(self, browser):
        pass
