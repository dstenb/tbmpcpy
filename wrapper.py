from mpd import (MPDClient, CommandError)
from socket import error as SocketError


class Changes:

    def __init__(self):
        self.changes = []

    def add(self, *args):
        for s in args:
            if not s in self.changes:
                self.changes.append(s)

    def get(self):
        c = self.changes
        self.changes = []
        return c


class MPDWrapper():

    def __init__(self, host, port):
        self.mpd = MPDClient(use_unicode=True)
        self.changes = Changes()
        self.host = host
        self.port = port
        self.connected = False
        self.in_idle = False

    def auth(self, password):
        if self.connected:
            try:
                self.mpd.password(password)
            except CommandError:
                return False
        return True

    def connect(self):
        try:
            self.mpd.connect(self.host, self.port)
            self.connected = True
        except SocketError:
            self.connected = False
        return self.connected

    def disconnect(self):
        if self.connected:
            self.mpd.disconnect()
            self.connected = False

    def fileno(self):
        return self.mpd.fileno()

    def get_changes(self):
        return self.changes.get() if not self.in_idle else []

    def has_changes(self):
        return len(self.changes.changes)

    def idle(self):
        if self.connected and not self.in_idle:
            self.in_idle = True
            self.mpd.send_idle()
        return self.in_idle

    def noidle(self, block=False):
        changes = []
        if self.connected and self.in_idle:
            self.in_idle = False
            if not block:
                self.mpd.send_noidle()
            self.changes.add(*self.mpd.fetch_idle())

    def playlist(self):
        if self.connected:
            return self.mpd.playlistinfo()
        return None

    def player(self, cmd, *args):
        if self.connected:
            self.changes.add("player")
            self.noidle()
            getattr(self.mpd, cmd)(*args)

    def option(self, cmd, *args):
        if self.connected:
            self.changes.add("options")
            self.noidle()
            getattr(self.mpd, cmd)(*args)

    def status(self):
        if self.connected:
            self.noidle()
            return self.mpd.status()
        return None

    def ls(self, path):
        if self.connected:
            self.noidle()
            return self.mpd.lsinfo(path)
        return []

    def add(self, s):
        if self.connected:
            self.changes.add("playlist")
            self.noidle()
            self.mpd.add(s)

    def add_and_play(self, s):
        if self.connected:
            self.changes.add("playlist", "player")
            self.noidle()
            self.mpd.playid(self.mpd.addid(s))
