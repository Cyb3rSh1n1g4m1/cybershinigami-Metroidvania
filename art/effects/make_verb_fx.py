"""Effects for the §16.2 verbs — pixel-art strips into game/art/effects/.

  swing_arc.png   3f 48x48  — the green slash cue on every light cut
  wave_slash.png  4f 96x48  — SIGKILL's projected wave, Strider-style:
                              SOLID white body, lime rim, olive edge
  slam_ring.png   4f 96x48  — CORE DUMP's expanding ground shockwave
  dust_cloud.png  5f 96x48  — CORE DUMP's impact dust, billowing out
  dj_ring.png     4f 64x64  — Privilege Escalation's rising cyan ring

Palette only, hard pixels. Run: python make_verb_fx.py
"""
import math
import pathlib
import random

from PIL import Image

OUT = pathlib.Path(__file__).parents[2] / "game" / "art" / "effects"
rng = random.Random(0x0029)

ACID = (198, 240, 42, 255)
ACID_DIM = (107, 138, 15, 255)
CYAN = (53, 198, 244, 255)
PALE = (143, 232, 255, 255)
WHITE = (255, 255, 255, 255)
SLATE = (74, 85, 104, 255)
SLATE_L = (118, 130, 150, 255)


def strip(name, w, h, n, draw, save=True):
    im = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for f in range(n):
        cell = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw(cell.load(), w, h, f, n)
        im.paste(cell, (f * w, 0))
    if not save:                     # retired: still drawn so the shared
        return                       # rng stream (and later strips) stay identical
    im.save(OUT / f"{name}.png")
    print(f"ok: {name}.png  {n}f {w}x{h}")


def put(px, w, h, x, y, c):
    if 0 <= x < w and 0 <= y < h:
        px[x, y] = c


def swing_arc(px, w, h, f, n):
    """A fast thin crescent — the light cut's read. White edge leads frame 1."""
    cx, cy = w * 0.3, h * 0.5
    r = 15 + f * 4
    col = [WHITE, ACID, ACID_DIM][f]
    for deg in range(-55, 56):
        a = math.radians(deg)
        for t in range(2):
            x = int(cx + (r + t) * math.cos(a))
            y = int(cy + (r + t) * math.sin(a))
            put(px, w, h, x, y, col)
        if f == 0 and abs(deg) < 35:
            put(px, w, h, int(cx + (r + 2) * math.cos(a)),
                int(cy + (r + 2) * math.sin(a)), WHITE)


def wave(px, w, h, f, n):
    """Strider wave: a SOLID horizontal body — white core filling most of it,
    lime rim, olive outline — flying tip-forward with an eroding tail."""
    scale = (0.55, 1.0, 1.0, 0.8)[f]
    erode = (0.0, 0.0, 0.35, 0.65)[f]
    hmax = 15.0 * scale
    for x in range(w):
        u = x / (w - 1)
        # asymmetric profile: blunt bright front (right), long tapering tail
        hh = hmax * math.sin(math.pi * min(1.0, u ** 0.55)) if u > 0.02 else 0.0
        if hh < 0.8:
            continue
        for dy in range(-int(hh), int(hh) + 1):
            y = int(h * 0.5) + dy
            ay = abs(dy) / max(hh, 1e-6)
            if erode > 0.0 and u < 0.6 and rng.random() < erode * (1.0 - u):
                continue                     # the tail dissolves into streaks
            if ay < 0.62:
                c = WHITE
            elif ay < 0.88:
                c = ACID
            else:
                c = ACID_DIM
            put(px, w, h, x, y, c)
    if f < 3:                                # speed streaks trailing the tail
        for s in range(4):
            y = int(h * 0.5 + (s - 1.5) * 4)
            for x in range(2 + s * 3, 16 + s * 2):
                if rng.random() < 0.6:
                    put(px, w, h, x, y, ACID_DIM)


def slam(px, w, h, f, n):
    cy = h - 8
    r = 8 + f * 12
    col = [WHITE, ACID, ACID_DIM, ACID_DIM][f]
    for deg in range(0, 181, 2):
        a = math.radians(deg)
        x = int(w * 0.5 + r * math.cos(a))
        y = int(cy - r * 0.32 * math.sin(a))
        put(px, w, h, x, y, col)
        put(px, w, h, x, y + 1, col)


def dust(px, w, h, f, n):
    """Billowing impact dust: puffs pushed outward and up, thinning."""
    spread = 10 + f * 9
    rise = f * 3
    count = (7, 9, 8, 6, 4)[f]
    for i in range(count):
        side = -1 if i % 2 == 0 else 1
        cx = w * 0.5 + side * rng.uniform(spread * 0.3, spread)
        cy = h - 10 - rng.uniform(0, 4) - rise * rng.uniform(0.5, 1.0)
        pr = rng.uniform(3, 6) * (1.0 - f * 0.12)
        col = SLATE_L if rng.random() < 0.35 else SLATE
        for dx in range(-int(pr), int(pr) + 1):
            for dy in range(-int(pr), int(pr) + 1):
                if dx * dx + dy * dy <= pr * pr:
                    put(px, w, h, int(cx + dx), int(cy + dy * 0.7), col)
        put(px, w, h, int(cx), int(cy - pr * 0.7), SLATE_L)


def ring(px, w, h, f, n):
    cx, cy = w * 0.5, h * 0.62 - f * 3
    r = 5 + f * 7
    col = [WHITE, CYAN, CYAN, PALE][f]
    for deg in range(0, 360, 3):
        a = math.radians(deg)
        x = int(cx + r * math.cos(a))
        y = int(cy + r * 0.45 * math.sin(a))
        put(px, w, h, x, y, col)
        if f < 2:
            put(px, w, h, x, y - 1, PALE)


strip("swing_arc", 48, 48, 3, swing_arc)
strip("wave_slash", 96, 48, 4, wave, save=False)   # retired: crescent.png replaced it
strip("slam_ring", 96, 48, 4, slam, save=False)    # retired: green ring cut from CORE DUMP
strip("dust_cloud", 96, 48, 5, dust)
strip("dj_ring", 64, 64, 4, ring)
