#!/usr/bin/python
# -*- encoding: utf-8 -*-


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
