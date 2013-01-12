#!/usr/bin/python
# -*- encoding: utf-8 -*-

from ui import Format


from termbox import BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE
from termbox import BOLD, UNDERLINE


#### Symbols
symbol_progress_e = u"─"
symbol_progress_c = u"╼"
symbol_progress_r = u"·"
symbol_player_states = {
        "play": ">",
        "stop": "[]",
        "pause": "||"
}

#### Colors
color_playlist_number = (YELLOW, BLACK)
color_playlist_line = (WHITE, BLACK)
color_playlist_time = (RED, BLACK)
color_playlist_selected = (WHITE, CYAN)

# Browser
color_browser_number = (YELLOW, BLACK)
color_browser_line = (WHITE, BLACK)
color_browser_selected = (WHITE, CYAN)

# Progress bar
color_progress_elapsed = (WHITE, BLACK)
color_progress_remaining = (BLACK, BLACK)

# Message
color_msg = {
        "info": (WHITE, BLACK),
        "warning": (YELLOW, BLACK),
        "error": (RED, BLACK)
}

# Command line
color_cmdline_number = (MAGENTA, BLACK)
color_cmdline_name = (WHITE, BLACK)
color_cmdline_description = (WHITE, BLACK)

#### Text strings
text_msg_prefix = {
        "info": "Info",
        "warning": "Warning",
        "error": "Error"
}


def length_str(time):
    m = time / 60
    s = time % 60

    if m <= 0 and s <= 0:
        return "--:--"
    elif m > 99:
        return str(m) + "m"
    return str(m).zfill(2) + ":" + str(s).zfill(2)


#### Formatting functions
def format_browser_item(node, pos, selected, w, numw):
    f = Format()

    f.add(str(pos + 1).rjust(numw), *color_browser_number)
    f.add(" " + unicode(node), *color_browser_line)

    if selected:
        f.set_color(*color_browser_selected)
        f.add("".ljust(max(0, w - len(f.s))),
                *color_browser_selected)
    return f


def format_playlist_song(song, pos, selected, current, w, numw):
    left, right = Format(), Format()

    left.add(str(pos + 1).rjust(numw), *color_playlist_number)
    left.add(" %s - %s" % (song.artist, song.title),
            *color_playlist_line)
    right.add(" [%s]" % length_str(song.time), *color_playlist_time)

    if selected:
        left.set_color(*color_playlist_selected)
        right.set_color(*color_playlist_selected)
        left.add("".ljust(max(0, w - len(left.s))),
                *color_playlist_selected)
    if current:
        left.set_bold()
        right.set_bold()
        left.replace(0, ">", BLUE, BLACK)
    return left, right
