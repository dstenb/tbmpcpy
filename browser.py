#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback

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

    def name(self):
        return self.list[-1]

    def pop(self):
        if len(self.list) > 0:
            del self.list[-1]

    def push(self, s):
        self.list.append(s)


class BrowserNode(object):

    def __init__(self, mpd, parent, ntype):
        self.mpd = mpd
        self.parent = parent
        self.ntype = ntype
        self.sel = -1

    def __len__(self):
        return 0

    def load(self):
        pass

    def select(self, index, rel=False):
        pass

    def selected(self):
        pass


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


class DirectoryNode(BrowserNode):

    def __init__(self, mpd, path, parent):
        super(DirectoryNode, self).__init__(mpd, parent, "directory")
        self.children = []
        self.path = path

    def __len__(self):
        return len(self.children)

    def __str__(self):
        return self.path.name() + "/"

    def _fix_sel(self):
        if len(self) > 0:
            self.sel = min(max(0, self.sel), len(self) - 1)
        else:
            self.sel = -1

    def _load(self):
        children = []

        try:
            for v in self.mpd.ls(unicode(self.path)):
                if "directory" in v:
                    c = DirectoryNode(self.mpd, Path(v["directory"]), self)
                    c.load()
                    children.append(c)
                elif "playlist" in v:
                    c = PlaylistNode(self.mpd, v["playlist"], self)
                    children.append(c)
                elif "file" in v:
                    c = SongNode(self.mpd, Song(v), self)
                    children.append(c)
        except:
            traceback.print_exc()
            raise

        # Add links to root and previous directory
        if self.parent != None:
            children.insert(0, LinkNode(self.mpd, None, self, "/"))
            children.insert(1, LinkNode(self.mpd, self.parent, self, "../"))

        self.children = children
        if len(self.children) > 0:
            self.sel = 0

    def load(self):
        self._load()

    def select(self, index, rel=False):
        if rel:
            self.sel += index
        else:
            self.sel = index
        self._fix_sel()
        return self.sel

    def selected(self):
        if self.sel >= 0:
            return self.children[self.sel]
        return None


class LinkNode(BrowserNode):

    def __init__(self, mpd, link, parent, name=None):
        super(LinkNode, self).__init__(mpd, parent, "link")
        self.link = link
        self.name = name if "name" != None else link.path.name()

    def __str__(self):
        return self.name


class Browser(List):

    def __init__(self, mpd):
        super(Browser, self).__init__([])
        self.mpd = mpd
        self.tree = DirectoryNode(mpd, Path(), None)
        self.curr_node = None

    def _set_selected(self, node):
        if node:
            self.curr_node = node
            self.sel = self.curr_node.sel
            self.set_list(self.curr_node.children)

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
                self._set_selected(selnode.link if selnode.link != None
                        else self.tree)

    def go_up(self):
        if self.curr_node and self.curr_node.parent:
            self.curr_node.select(0)  # Restore selected for current node
            self._set_selected(self.curr_node.parent)

    def load(self):
        self.tree.load()
        self._set_selected(self.tree)

    def path_str(self, delim="/"):
        if self.curr_node != None:
            return delim.join(self.curr_node.path.list)
        return ""

    def select(self, index, rel=False):
        if self.curr_node != None:
            self.sel = self.curr_node.select(index, rel)
            self._notify_selected()
