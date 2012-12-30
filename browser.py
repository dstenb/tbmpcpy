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

    def __init__(self, mpd, parent):
        self.mpd = mpd
        self.parent = parent
        self.sel = -1

    def __len__(self):
        return 0

    def load(self):
        pass

    def select(self, index, rel=False):
        pass

    def selected(self):
        pass

    def is_file(self):
        return True

    def is_song(self):
        return False

    def is_playlist(self):
        return False


class SongNode(BrowserNode):

    def __init__(self, mpd, data, parent):
        super(SongNode, self).__init__(mpd, parent)
        self.data = data

    def __str__(self):
        return "%s - %s (%s)" % (self.data.artist,
                self.data.title, self.data.album)

    def is_file(self):
        return True

    def is_song(self):
        return True


class PlaylistNode(BrowserNode):

    def __init__(self, mpd, data, parent):
        super(PlaylistNode, self).__init__(mpd, parent)
        self.data = data

    def __str__(self):
        return self.data

    def is_file(self):
        return True

    def is_playlist(self):
        return True


class DirectoryNode(BrowserNode):

    def __init__(self, mpd, path, parent):
        super(DirectoryNode, self).__init__(mpd, parent)
        self.children = []
        self.path = path
        self.sel = -1

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

    def is_file(self):
        return False


class Browser(List):

    def __init__(self, mpd):
        super(Browser, self).__init__([])
        self.mpd = mpd
        self.tree = DirectoryNode(mpd, Path(), None)

    def _set_selected(self, node):
        if node:
            self.seltree = node
            self.sel = self.seltree.sel
            self.set_list(self.seltree.children)

    def enter(self):
        selnode = self.seltree.selected()

        if selnode != None:
            if selnode.is_song():
                self.mpd.add(selnode.data.file)
            elif selnode.is_playlist():
                print(selnode.data)
            else:
                self._set_selected(selnode)

    def go_up(self):
        if self.seltree:
            self.seltree.select(0)  # Restore selected for current node
        self._set_selected(self.seltree.parent)

    def load(self):
        self.tree.load()
        self._set_selected(self.tree)

    def select(self, index, rel=False):
        self.sel = self.seltree.select(index, rel)
        self._notify_selected()
