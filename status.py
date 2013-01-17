from re import compile, IGNORECASE

from browser import *
from common import *
from list import *
from wrapper import *
import traceback


class Playlist(List):

    def __init__(self, mpd):
        super(Playlist, self).__init__()
        self.mpd = mpd
        self.version = 0
        self.playtime = 0

    def init(self, _songs, version):
        self.version = version
        self.set_list(map(lambda d: Song(d), _songs))

    def _handle_set(self):
        self.playtime = 0
        for v in self.items:
            self.playtime += v.time

    def update(self, changelist, version, real_len):
        lookup = {}

        for s in self.real_items:
            lookup[s.songid] = s

        if len(changelist) > 0:
            del self.real_items[int(changelist[0]["cpos"]):]

        for s in changelist:
            sid = int(s["id"])
            if sid in lookup:
                song = lookup[sid]
                song.pos = int(s["cpos"])  # Update song pos to correct one
                self.real_items.append(song)
            else:
                self.real_items.append(self.mpd.playlist_song(sid))

        # Detect songs removed from the back of the list
        if real_len < len(self):
            del self.real_items[(real_len - len(self)):]
        self.version = version
        self.set_list(self.real_items)

    def _search(self):
        rl = map(lambda s: compile(s, IGNORECASE), self.search_string.split())
        return filter(lambda s: s.matches_all(rl), self.real_items)


class Progress(object):

    def __init__(self):
        self.elapsed_time = 0
        self.total_time = 0
        self.last = time_in_millis()

    def elapsed(self):
        if self.total_time > 0:
            return (self.elapsed_time / float(self.total_time))
        return -1

    def update(self, ts):
        self.elapsed_time += (ts - self.last) / 1000.0
        self.last = ts


class StatusListener():

    def current_changed(self):
        pass

    def option_changed(self, o, b):
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
        self.playlist = Playlist(mpd)
        self.progress = Progress()
        self.options = {
                "consume": False,
                "random": False,
                "repeat": False,
                "single": False,
                "xfade": 0
        }
        self.current = None
        self.state = ""
        self.listeners = []

    def _set_current(self, pos):
        self.current = self.mpd.current_song()
        self.progress.total_time = self.current.time if self.current else 0

        for o in self.listeners:
            o.current_changed()

    def _set_elapsed(self, t):
        self.progress.elapsed_time = t

    def _set_option(self, opt, b):
        if self.options[opt] != b:
            self.options[opt] = b
            for o in self.listeners:
                o.option_changed(opt, b)

    def _set_playlist(self, songs, version):
        self.playlist.init(songs, version)

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
        self._set_playlist(self.mpd.plchanges(0), int(results["playlist"]))
        self._set_state(results.get("state", "unknown"))
        self._set_current(int(results.get("song", -1)))
        self._set_elapsed(int(results.get("elapsed", "0").split(".")[0]))
        self._update_options(results)

    def _update_options(self, results):
        self._set_option("consume", _get_bool(results, "consume"))
        self._set_option("random", _get_bool(results, "random"))
        self._set_option("repeat", _get_bool(results, "repeat"))
        self._set_option("single", _get_bool(results, "single"))
        self._set_option("xfade", _get_int(results, "xfade", -1))

    def _update_playlist(self, results):
        changelist = self.mpd.plchangesposid(self.playlist.version)
        real_len = int(results["playlistlength"])
        version = int(results["playlist"])
        self.playlist.update(changelist, version, real_len)

    def _update_player(self, results):
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
