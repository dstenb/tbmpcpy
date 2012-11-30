from list import *
import traceback

class Song():

    def __init__(self, d):
        self.artist = d.get("artist", "unknown")
        self.album = d.get("album", "unknown")
        self.title = d.get("title", "unknown")
        self.genre = d.get("genre", "unknown")
        self.time = int(d.get("time", 0))
        self.pos = int(d.get("pos", 0))
        self.songid = int(d.get("id", -1))


class StatusListener():

    def current_changed(self):
        self

    def option_changed(self, o, b):
        self

    def playlist_changed(self):
        self

    def state_changed(self, state):
        self


class Status():

    def __init__(self, playlist):
        self.playlist = playlist
        self.mode = { "random" : False,
                "repeat" : False,
                "single" : False,
                "consume" : False
        }
        self.current = None
        self.state = ""
        self.listeners = [ ]

    def _set_current(self, pos):
        try:
            self.current = self.playlist[pos]
        except:
            print("oops")
            self.current = None
        print(self.current)
        for o in self.listeners:
            o.current_changed()

    def _set_mode(self, m, b):
        self.mode[m] = b
        for o in self.listeners:
            o.mode_changed(m, b)

    def _set_state(self, state):
        self.state = state

        for o in self.listeners:
            o.state_changed(state)

    def _set_playlist(self, _songs, version):
        print("set_playlist")
        songs = [ ]
        for d in _songs: songs.append(Song(d))
        self.playlist.update(songs, version)
        for o in self.listeners:
            o.playlist_changed()

    def add_listener(self, o):
        self.listeners.append(o)

    def update(self, mpd):
        results = mpd.status()

        # Update playlist if necessary
        if int(results["playlist"]) > self.playlist.version:
            self._set_playlist(mpd.playlistinfo(), int(results["playlist"]))

        # Update state
        if results["state"] != self.state:
            self._set_state(results["state"])

        # Update mode
        self._set_mode("random", bool(int(results["random"])))
        self._set_mode("repeat", bool(int(results["repeat"])))
        self._set_mode("single", bool(int(results["single"])))

        # Update current song if necessary
        curr_id = int(results.get("songid", -1))
        prev_id = self.current.songid if self.current else -1

        print curr_id
        print prev_id
        if curr_id != prev_id:
            self._set_current(int(results.get("song", -1)))
