import sys
import os

sys.path.insert(0, "/system/apps/cybershinigami")
os.chdir("/system/apps/cybershinigami")

import random
from badgeware import screen, io, shapes, run, State
import st
import gfx
import world
import attract
from reaper import Reaper, Inp

# CYB3R$H1N1G4M1 on the badge. TITLE is the game's title screen (menu live);
# 8 idle seconds start the DEMO autoplay of every verb; any button returns to
# the title. START -> PLAY (A attack / hold = SIGKILL crescent, B jump, C
# dash); 20 idle seconds in PLAY hand back to the demo. QUIT leaves the app.
# Small modules on purpose: MicroPython compiles each file in RAM.

TITLE, DEMO, PLAY, OVER = 0, 1, 2, 3
TITLE_IDLE = 8.0
mode = TITLE
t_mode = 0
idle_since = 0
hiscore = 0


def real_input():
    i = Inp()
    i.jump = io.BUTTON_B in io.pressed
    i.dash = io.BUTTON_C in io.pressed
    i.attack_pressed = io.BUTTON_A in io.pressed
    i.attack_held = io.BUTTON_A in io.held
    return i


def enter(m):
    global mode, t_mode
    mode = m
    t_mode = io.ticks
    if m in (DEMO, PLAY):
        st.reaper = Reaper()
        st.enemies.clear()
        st.souls.clear()
        st.fx.clear()
        attract.reset()


def update():
    global idle_since, hiscore
    dt = min(0.05, io.ticks_delta / 1000.0)
    t = (io.ticks - t_mode) / 1000.0
    if io.pressed:
        idle_since = io.ticks

    if mode == TITLE:
        if io.BUTTON_UP in io.pressed:
            attract.move(-1)
        elif io.BUTTON_DOWN in io.pressed:
            attract.move(1)
        elif io.BUTTON_A in io.pressed or io.BUTTON_C in io.pressed:
            if attract.sel == 0:
                enter(PLAY)
                return
            if attract.sel == 2:
                return True                    # leaves run(): back to the launcher
        elif io.ticks - idle_since > TITLE_IDLE * 1000:
            enter(DEMO)
            return
        attract.draw_title(t, dt)

    elif mode == DEMO:
        if io.pressed:
            enter(TITLE)
            return
        if t > attract.DEMO_LEN:
            enter(DEMO)
            return
        st.speed = 62.0
        st.reaper.update(dt, attract.script_input(t))
        world.update(dt)
        world.draw()
        world.hud(hiscore)
        screen.brush = st.SHADOW
        screen.draw(shapes.rectangle(0, st.H - 12, st.W, 12))
        if int(io.ticks / 600) % 2:
            screen.font = st.font_small
            screen.brush = st.YELLOW
            world.center("AUTOPLAY - ANY BUTTON", st.H - 10)

    elif mode == PLAY:
        if io.ticks - idle_since > 20000:
            enter(DEMO)
            return
        st.speed = min(110.0, 62.0 + t * 1.6)
        if st.reaper.dead <= 0.0 and random.random() < dt * (0.55 + t * 0.02):
            world.spawn("worm" if random.random() < 0.65 else "drone")
        st.reaper.update(dt, real_input())
        world.update(dt)
        world.draw()
        world.hud(hiscore)
        if st.reaper.dead > 1.2:
            if st.reaper.souls > hiscore:
                hiscore = st.reaper.souls
                try:
                    State.save("cyber_hiscore", {"hi": hiscore})
                except Exception:
                    pass
            enter(OVER)

    else:
        world.draw()
        screen.brush = st.SHADOW
        screen.draw(shapes.rectangle(0, 30, st.W, 52))
        screen.font = st.font_big
        screen.brush = st.RED
        world.center("TERMINATED", 36)
        screen.font = st.font_small
        screen.brush = st.WHITE
        world.center("%d SOUL BYTES REAPED" % st.reaper.souls, 58)
        if int(io.ticks / 500) % 2:
            screen.brush = st.ACID
            world.center("A: RETRY   B: TITLE", 70)
        if io.BUTTON_A in io.pressed:
            enter(PLAY)
        elif io.BUTTON_B in io.pressed or t > 8.0:
            enter(TITLE)


def init():
    global hiscore, idle_since
    gfx.load()
    try:
        wrap = {"hi": 0}
        State.load("cyber_hiscore", wrap)
        hiscore = int(wrap.get("hi", 0))
    except Exception:
        pass
    idle_since = io.ticks
    enter(TITLE)


def on_exit():
    pass


if __name__ == "__main__":
    init()
    run(update)
