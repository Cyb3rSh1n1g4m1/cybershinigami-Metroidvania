from badgeware import screen, io, brushes, shapes
import st
import world
from reaper import Inp

# The game's title screen (title.gd), scaled 640x360 -> 160x120: x*0.25, y/3.
# Left: the hannya logo. Right column: dark plate with yellow hairlines, the
# red 死神 mark (romaji fallback, like the game without a CJK face), the
# wordmark with cyan/magenta ghost offsets, the logline, the START/CONTINUE/
# QUIT menu with the acid caret, console rules, and the hint line.
ITEMS = ["START", "CONTINUE", "QUIT"]
HAS_SAVE = False
sel = 0
_rain = []           # (x, y, speed, glyph) columns

# -- the autoplay script (seconds into the demo, action) -----------------------
SCRIPT = [
    (1.0, "spawn:worm"), (2.2, "attack"), (3.2, "jump"), (4.0, "spawn:drone"),
    (4.4, "jump"), (4.75, "jump"), (5.6, "spawn:worm"), (6.0, "dash"),
    (7.0, "spawn:worm"), (7.2, "hold"), (7.85, "release"), (9.0, "spawn:drone"),
    (9.4, "jump"), (9.75, "jump"), (10.1, "attack"), (11.2, "spawn:worm"),
    (11.9, "attack"), (12.3, "attack"),
]
DEMO_LEN = 13.5
i_script = 0
holding = False


def reset():
    global i_script, holding
    i_script = 0
    holding = False


def script_input(t):
    global i_script, holding
    i = Inp()
    while i_script < len(SCRIPT) and SCRIPT[i_script][0] <= t:
        act = SCRIPT[i_script][1]
        i_script += 1
        if act.startswith("spawn:"):
            world.spawn(act[6:])
        elif act == "jump":
            i.jump = True
        elif act == "dash":
            i.dash = True
        elif act == "attack":
            i.attack_pressed = True
        elif act == "hold":
            i.attack_pressed = True
            holding = True
        elif act == "release":
            holding = False
    i.attack_held = holding
    return i


# -- title screen ----------------------------------------------------------------
def enabled(i):
    return i != 1 or HAS_SAVE


def move(step):
    global sel
    n = len(ITEMS)
    i = sel
    for _ in range(n):
        i = (i + step) % n
        if enabled(i):
            break
    sel = i


def _rain_init():
    seed = 0x29
    for c in range(12):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        _rain.append([6 + c * 13, (seed % 140) - 20, 14 + (seed >> 8) % 30,
                      "0123456789ABCDEF$#<>"[(seed >> 4) % 20]])


def draw_rain(dt):
    if not _rain:
        _rain_init()
    screen.font = st.font_small
    for col in _rain:
        col[1] += col[2] * dt
        if col[1] > st.H + 10:
            col[1] = -24.0
        for k in range(3):                     # head bright, tail fading — quiet
            screen.brush = brushes.color(143, 232, 255, 120) if k == 0                 else brushes.color(107, 138, 15, 100 - k * 35)
            screen.text(col[3], col[0], int(col[1]) - k * 8)


def draw_title(t, dt):
    screen.blit(st.title_bg, 0, 0)
    draw_rain(dt)
    screen.blit(st.logo, 4, 22)

    # the plate: PLATE(248,34,384,104) -> (62,11,96,40) — four lines of the
    # badge font need 40px, not the scaled 35
    screen.brush = brushes.color(5, 8, 15, 210)
    screen.draw(shapes.rectangle(62, 11, 96, 40))
    screen.brush = brushes.color(252, 238, 10, 140)
    screen.draw(shapes.rectangle(62, 11, 96, 1))
    screen.brush = brushes.color(252, 238, 10, 90)
    screen.draw(shapes.rectangle(62, 51, 96, 1))

    screen.font = st.font_small
    screen.brush = st.RED
    screen.text("SHINIGAMI", 64, 13)                  # 死神, romaji fallback
    # wordmark with the chromatic ghosts: shadow, cyan left, magenta right, yellow
    screen.brush = st.SHADOW
    screen.text("CYB3R$H1N1G4M1", 65, 23)
    screen.brush = brushes.color(53, 198, 244, 200)
    screen.text("CYB3R$H1N1G4M1", 63, 22)
    screen.brush = brushes.color(224, 31, 38, 190)
    screen.text("CYB3R$H1N1G4M1", 65, 22)
    screen.brush = st.YELLOW
    screen.text("CYB3R$H1N1G4M1", 64, 22)
    screen.brush = st.CYAN
    screen.text("hv 0x0029", 64, 32)
    screen.brush = st.WHITE
    screen.text("descends the stack", 64, 41)

    # console rules under the plate (Chrome)
    screen.brush = brushes.color(53, 198, 244, 56)
    screen.draw(shapes.rectangle(45, 54, 70, 1))
    screen.brush = brushes.color(198, 240, 42, 180)
    screen.draw(shapes.rectangle(78, 54, 4, 1))

    # menu panel + items: MENU(280,174,step 26) -> (70,60,step 10)
    screen.brush = brushes.color(0, 0, 0, 140)
    screen.draw(shapes.rectangle(62, 57, 62, 33))
    screen.brush = brushes.color(198, 240, 42, 90)
    screen.draw(shapes.rectangle(62, 57, 1, 33))
    screen.draw(shapes.rectangle(62, 57, 10, 1))
    for i, item in enumerate(ITEMS):
        if not enabled(i):
            screen.brush = brushes.color(74, 85, 104, 220)
        elif i == sel:
            screen.brush = st.ACID
        else:
            screen.brush = brushes.color(143, 232, 255, 140)
        screen.text(item, 70 + (1 if i == sel else 0), 60 + i * 10)
    if int(io.ticks / 400) % 2:
        screen.brush = st.ACID
        screen.text(">", 65, 60 + sel * 10)

    screen.brush = st.SLATE
    screen.text("[up/dn] select   [A] exec", 22, 111)
