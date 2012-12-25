import termbox
from threading import *
from time import sleep
import traceback

dl = Lock()

l = Lock()
a = "_"

def draw(tb):
    dl.acquire()
    l.acquire()
    b = a
    l.release()

    tb.change_cell(0, 0, ord(b), termbox.WHITE, termbox.BLACK)
    tb.present()
    dl.release()


def threadf_update_loop(tb):
    while True:
        draw(tb)
        l.acquire()
        a = "F"
        l.release()
        sleep(1)

def threadf_tb_loop(tb):
    while True:
        draw(tb)
        event = tb.poll_event()
        if event:
            (type, ch, key, mod, w, h) = event

            if type == termbox.EVENT_RESIZE:
                pass
            elif type == termbox.EVENT_KEY:
                if ch:
                    l.acquire()
                    a = ch
                    l.release()
                else:
                    return

try:
    tb = termbox.Termbox()

    t1 = Thread(target = threadf_tb_loop, args = (tb, ))
    t2 = Thread(target = threadf_update_loop, args = (tb, ))
    t2.daemon = True

    for t in [t1, t2]:
        t.start()
except:
    tb.close()
    traceback.print_exc()
finally:
    tb.close()


