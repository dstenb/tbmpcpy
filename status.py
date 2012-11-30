from list import *
from wrapper import *
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


def _get_bool(d, v, de=0):
    return bool(int(d.get(v, de)))


class Status:

    def __init__(self, mpdw):
        self.mpdw = mpdw
        self.browser = Browser()
        self.playlist = Playlist()
        self.options = {"consume": False,
                "random": False,
                "repeat": False,
                "single": False,
                "xfade": False}
        self.current = None
        self.state = ""
        self.listeners = []

    def _set_current(self, pos):
        try:
            self.current = self.playlist[pos] if pos >= 0 else None
        except:
            self.current = None
        for o in self.listeners:
            o.current_changed()

    def _set_option(self, opt, b):
        if self.options[opt] != b:
            self.options[opt] = b
            for o in self.listeners:
                o.option_changed(opt, b)

    def _set_playlist(self, _songs, version):
        songs = []
        for d in _songs:
            songs.append(Song(d))
        self.playlist.set(songs, version)
        for o in self.listeners:
            o.playlist_changed()

    def _set_state(self, state):
        if self.state != state:
            self.state = state
            for o in self.listeners:
                o.state_changed(state)

    def add_listener(self, o):
        self.listeners.append(o)

    def init(self):
        results = self.mpdw.status()
        print(results)
        self._set_playlist(self.mpdw.playlist(), int(results["playlist"]))
        self._set_state(results.get("state", "unknown"))
        self._update_options(results)
        self._set_current(int(results.get("song", -1)))

    def _update_options(self, results):
        print(":: updating changes")
        self._set_option("consume", _get_bool(results, "consume"))
        self._set_option("random", _get_bool(results, "random"))
        self._set_option("repeat", _get_bool(results, "repeat"))
        self._set_option("single", _get_bool(results, "single"))
        self._set_option("xfade", _get_bool(results, "xfade"))

    def _update_playlist(self, results):
        print(":: updating playlist")
        self._set_playlist(self.mpdw.playlist(), int(results["playlist"]))

    def _update_player(self, results):
        print(":: updating player")

        # Update state
        self._set_state(results.get("state", "unknown"))

        # Update current song if necessary
        curr_id = int(results.get("songid", -1))
        prev_id = self.current.songid if self.current else -1

        return curr_id != prev_id

    def update(self, changes):
        if len(changes) == 0:
            return

        results = self.mpdw.status()
        update_current = False
        print(results)

        if "playlist" in changes:
            self._update_playlist(results)
            update_current = True

        if "player" in changes:
            update_current = self._update_player(results) or update_current

        if update_current:
            self._set_current(int(results.get("song", -1)))

        if "options" in changes:
            self._update_options(results)

        if "output" in changes:
            print(":: updating output")
            # TODO

        if "stored_playlist" in changes:
            print(":: updating stored_playlist")
            # TODO
