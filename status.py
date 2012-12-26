from common import *
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


class Progress(object):

    def __init__(self):
        self.elapsed_time = 0
        self.total_time = 0
        self.last = time_in_millis()

    def elapsed(self):
        if self.total_time > 0:
            return (self.elapsed_time / float(self.total_time))
        return -1

    def set_elapsed(self, t):
        self.elapsed_time = t

    def set_time(self, t):
        self.total_time = t

    def set_last(self, ts):
        self.last = ts

    def update(self, ts):
        self.elapsed_time += (ts - self.last) / 1000.0
        self.last = ts


class StatusListener():

    def current_changed(self):
        pass

    def option_changed(self, o, b):
        pass

    def playlist_changed(self):
        pass

    def state_changed(self, state):
        pass


def _get_bool(d, v, de=0):
    return bool(int(d.get(v, de)))


def _get_int(d, v, de=0):
    return int(d.get(v, de))


class Status:

    def __init__(self, mpd, msg):
        self.mpd = mpd
        self.msg = msg
        self.browser = Browser()
        self.playlist = Playlist()
        self.progress = Progress()
        self.options = {"consume": False,
                "random": False,
                "repeat": False,
                "single": False,
                "xfade": 0}
        self.current = None
        self.state = ""
        self.listeners = []

    def _set_current(self, pos):
        try:
            self.current = self.playlist[pos] if pos >= 0 else None
        except:
            self.current = None
        self.progress.set_time(self.current.time if self.current else 0)

        for o in self.listeners:
            o.current_changed()

    def _set_elapsed(self, t):
        self.progress.set_elapsed(t)

    def _set_option(self, opt, b):
        if self.options[opt] != b:
            self.options[opt] = b
            for o in self.listeners:
                o.option_changed(opt, b)

    def _set_playlist(self, _songs, version):
        songs = []
        for d in _songs:
            songs.append(Song(d))
        self.playlist.set_list(songs, version)
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
        results = self.mpd.status()
        print(results)
        if not results:
            self.msg.error("Couldn't retrieve MPD status", 1)
            return
        self._set_playlist(self.mpd.playlist(), int(results["playlist"]))
        self._set_state(results.get("state", "unknown"))
        self._update_options(results)
        self._set_current(int(results.get("song", -1)))
        self._set_elapsed(int(results.get("elapsed", "0").split(".")[0]))

    def _update_options(self, results):
        print(":: updating changes")
        self._set_option("consume", _get_bool(results, "consume"))
        self._set_option("random", _get_bool(results, "random"))
        self._set_option("repeat", _get_bool(results, "repeat"))
        self._set_option("single", _get_bool(results, "single"))
        self._set_option("xfade", _get_int(results, "xfade", -1))

    def _update_playlist(self, results):
        print(":: updating playlist")
        playlist = self.mpd.playlist()
        if playlist:
            self._set_playlist(playlist, int(results["playlist"]))
        else:
            self.msg.error("Couldn't retrieve playlist", 1)

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

        results = self.mpd.status()

        if not results:
            self.msg.error("Couldn't retrieve MPD status", 1)
            return
        update_current = False
        print(results)

        self._set_elapsed(int(results.get("elapsed", "0").split(".")[0]))

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

    def is_playing(self):
        return self.state == "play"
