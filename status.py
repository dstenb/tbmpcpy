class StatusListener():

    def current_changed(self, song):
        self

    def mode_changed(self, m, b):
        self

    def playlist_changed(self):
        self

    def state_changed(self, state):
        self


class Status():

    def __init__(self, playlist):
        self.current = None
        self.playlist = playlist

        self.random = False
        self.repeat = False
        self.single = False

        self.listeners = [ ]

        self.state = ""

    def _set_current(self, current):
        if self.current != current:
            self.current = current

            for o in self.listeners:
                o.current_changed(current)

    def _set_mode(self, m, b):
        for o in self.listeners:
            o.mode_changed(m, b)

    def _set_state(self, state):
        self.state = state

        for o in self.listeners:
            o.state_changed(state)

    def _set_playlist(self, songs, version):
        self.playlist.update(songs, version)
        for o in self.listeners:
            o.playlist_changed()

    def add_listener(self, o):
        self.listeners.append(o)

    def update(self, mpd):
        results = mpd.status()

        if results["playlist"] > self.playlist.version:
            self._set_playlist(mpd.playlistinfo(), int(results["playlist"]))

        if results["state"] != self.state:
            self._set_state(results["state"])

        self._set_mode("random", bool(results["random"]))
        self._set_mode("repeat", bool(results["repeat"]))
        self._set_mode("single", bool(results["single"]))

        self._set_current(mpd.currentsong())
