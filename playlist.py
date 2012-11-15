from ui import *
import math

class Playlist():

    def __init__(self):
        self.songs = []
        self.length = 0
        self.version = 0

    def __getitem__(self, index):
        return self.songs[index]

    def __len__(self):
        return len(self.songs)

    def update(self, songs, version):
        self.songs = songs
        self.version = version
        self.length = len(songs)
