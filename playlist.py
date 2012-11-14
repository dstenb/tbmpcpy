from ui import *
import math

class Playlist():

    def __init__(self):
        self.songs = []
        self.length = 0
        self.version = 0
        self.current = None

    def __getitem__(self, index):
        return self.songs[index]

    def __len__(self):
        return len(self.songs)

    def set_current(self, number):
        prev = self.current
        self.current = None if number == -1 else self.songs[number]

    def update(self, songs, version):
        self.songs = songs
        self.version = version
        self.length = len(songs)
