"""Prepare parallax layers for the 640x360 internal resolution.

The generator returns ~1376x768 art; the game viewport is 640x360, and
parallax.gd draws layers uncentered at origin, so an oversized image shows only
its empty top strip. Downscale to exactly viewport height, palette-snap, then
mirror-fold for a seam-free horizontal tile.

Run: python prep_bg.py
"""
from PIL import Image
import pathlib

OUT = pathlib.Path(r"D:\Projects\Cybershinigami\game\art\bg")
OUT.mkdir(parents=True, exist_ok=True)
VIEW_H = 360

PALETTE = [
    (0, 0, 0), (10, 14, 31), (30, 51, 217), (43, 111, 232), (53, 198, 244),
    (143, 232, 255), (143, 17, 22), (224, 31, 38), (198, 240, 42),
    (107, 138, 15), (255, 255, 255), (74, 85, 104),
]


def _hsv(c):
    r, g, b = (v / 255.0 for v in c)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    return h, (0.0 if mx == 0 else d / mx), mx


SAT = [(p, _hsv(p)) for p in PALETTE if max(p) - min(p) > 30]
NEUT = [(p, max(p) / 255.0) for p in PALETTE if max(p) - min(p) <= 30]


def snap(c):
    if max(c) - min(c) < 32:                     # neutral: match by brightness
        v = max(c) / 255.0
        return min(NEUT, key=lambda e: abs(v - e[1]))[0]
    h, s, v = _hsv(c)

    def cost(e):
        _, (ph, ps, pv) = e
        dh = abs(h - ph)
        dh = min(dh, 360 - dh) / 180.0
        return dh * 3.0 + abs(v - pv) + abs(s - ps) * 0.4
    return min(SAT, key=cost)[0]


def find_lights(im):
    """Locate neon before the layer is dimmed — afterwards nothing is bright
    enough to detect, which is why the far layer bloomed nothing on the first try."""
    w, h = im.size
    px = im.load()
    return [(x, y, px[x, y]) for x in range(w) for y in range(h)
            if max(px[x, y]) > 150 and max(px[x, y]) - min(px[x, y]) > 60]


def add_glow(im, srcs, strength, radius):
    """Neon signs cast light. Bright saturated pixels bleed a soft halo into the
    surrounding dark, which is what stops a flat wall of city art from reading as
    wallpaper. Additive, so it only ever brightens."""
    w, h = im.size
    px = im.load()
    glow = [[(0.0, 0.0, 0.0) for _ in range(h)] for _ in range(w)]
    # A lamp does not light itself. Falloff peaks at d=0, so blooming onto the
    # emitters washes out sign lettering — light only the surroundings.
    emitters = {(x, y) for x, y, _ in srcs}
    for x, y, c in srcs:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                d2 = dx * dx + dy * dy
                if d2 > radius * radius:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                f = (1.0 - (d2 ** 0.5) / radius) ** 2 * strength
                g = glow[nx][ny]
                glow[nx][ny] = (g[0] + c[0] * f, g[1] + c[1] * f, g[2] + c[2] * f)
    for x in range(w):
        for y in range(h):
            if (x, y) in emitters:
                continue                       # keep lettering crisp
            c, g = px[x, y], glow[x][y]
            px[x, y] = (min(255, int(c[0] + g[0])),
                        min(255, int(c[1] + g[1])),
                        min(255, int(c[2] + g[2])))


def sky_mask(im):
    """Flood the empty sky in from the top edge so it can be made TRANSPARENT.

    These layers shipped an OPAQUE black sky, which painted straight over the
    moon and clouds sitting behind them — the sky looked empty even though those
    nodes rendered fine. Flooding only from the top means building interiors,
    also near-black, stay solid.
    """
    from collections import deque
    w, h = im.size
    px = im.load()
    mask = [[False] * h for _ in range(w)]
    q = deque((x, 0) for x in range(w))
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or mask[x][y]:
            continue
        if max(px[x, y]) > 26:            # hit the skyline: stop
            continue
        mask[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return mask


# far layer sits deepest, so it dims hardest and glows least.
# The glow radius is a PIXEL measure, so it must scale with the render height or
# the same number covers proportionally less area on a larger layer.
_GS = VIEW_H / 270.0
DEPTH = {"bg_far": (0.42, 0.026, int(round(5 * _GS))),
         "bg_mid": (0.62, 0.055, int(round(7 * _GS)))}

for name in ("bg_far", "bg_mid"):
    im = Image.open(f"{name}.png").convert("RGB")
    w, h = im.size
    nw = max(1, round(w * VIEW_H / h))
    im = im.resize((nw, VIEW_H), Image.NEAREST)   # NEAREST keeps hard pixel edges

    dim, gstr, grad = DEPTH[name]
    px = im.load()
    cache: dict = {}
    for x in range(nw):
        for y in range(VIEW_H):
            c = px[x, y]
            if c not in cache:
                cache[c] = snap(c)
            px[x, y] = cache[c]

    sky = sky_mask(im)                # capture the sky while it is still pure black
    lights = find_lights(im)          # locate neon while it is still bright

    # atmospheric depth: pull the whole layer toward INK so the player and the
    # platforms stay the brightest things on screen
    for x in range(nw):
        for y in range(VIEW_H):
            c = px[x, y]
            px[x, y] = (int(c[0] * dim + 10 * (1 - dim)),
                        int(c[1] * dim + 14 * (1 - dim)),
                        int(c[2] * dim + 31 * (1 - dim)))

    add_glow(im, lights, gstr, grad)   # then bloom them back over the dark
    print(f"  {name}: dimmed to {int(dim * 100)}%, {len(lights)} light sources bloomed")

    # punch the sky out to alpha 0 so the moon and clouds behind can be seen.
    # glow that bled into the sky is kept — it is light, and it reads as haze.
    rgba = im.convert("RGBA")
    rp = rgba.load()
    cleared = 0
    for x in range(nw):
        for y in range(VIEW_H):
            if sky[x][y] and max(rp[x, y][:3]) < 34:   # still unlit sky
                rp[x, y] = (0, 0, 0, 0)
                cleared += 1

    tile = Image.new("RGBA", (nw * 2, VIEW_H), (0, 0, 0, 0))
    tile.paste(rgba, (0, 0))
    tile.paste(rgba.transpose(Image.FLIP_LEFT_RIGHT), (nw, 0))  # seam-free by construction
    tile.save(OUT / f"{name}.png")
    print(f"{name}: {w}x{h} -> {nw}x{VIEW_H} -> mirrored {nw * 2}x{VIEW_H}, "
          f"{len(set(cache.values()))} colors, {cleared} sky px transparent")
