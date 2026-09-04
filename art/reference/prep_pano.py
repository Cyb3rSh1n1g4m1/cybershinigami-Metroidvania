"""Build non-repeating parallax panoramas from three distinct segments each.

The old approach mirror-folded ONE image, which made the backdrop visibly
symmetrical and duplicated every landmark. Here three separately-generated
segments are concatenated in order, so nothing repeats across the room's whole
scroll distance. The giant torii is NOT in this art at all — it ships as its own
single sprite so there can only ever be one.

Run: python prep_pano.py
"""
from collections import deque
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
    if max(c) - min(c) < 32:
        v = max(c) / 255.0
        return min(NEUT, key=lambda e: abs(v - e[1]))[0]
    h, s, v = _hsv(c)

    def cost(e):
        _, (ph, ps, pv) = e
        dh = abs(h - ph)
        dh = min(dh, 360 - dh) / 180.0
        return dh * 3.0 + abs(v - pv) + abs(s - ps) * 0.4
    return min(SAT, key=cost)[0]


def sky_mask(im):
    """Flood the empty sky from the top so it can be punched to alpha 0.

    Polarity is detected, not assumed: segments come back with black OR light
    skies. A light-sky segment run through a black-only test stays fully opaque
    and paints a solid slab over the moon, clouds, and neighbouring segments —
    that is the grey block bug.
    """
    w, h = im.size
    px = im.load()
    top = [px[x, y] for x in range(0, w, 7) for y in range(0, 6)]
    light = sum(max(c) for c in top) / max(1, len(top)) > 90

    def is_sky(c):
        return min(c) > 150 if light else max(c) <= 26

    mask = [[False] * h for _ in range(w)]
    q = deque((x, 0) for x in range(w))
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or mask[x][y]:
            continue
        if not is_sky(px[x, y]):
            continue
        mask[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return mask, light


def find_lights(im):
    w, h = im.size
    px = im.load()
    return [(x, y, px[x, y]) for x in range(w) for y in range(h)
            if max(px[x, y]) > 150 and max(px[x, y]) - min(px[x, y]) > 60]


def add_glow(im, srcs, strength, radius):
    w, h = im.size
    px = im.load()
    glow = [[(0.0, 0.0, 0.0) for _ in range(h)] for _ in range(w)]
    emitters = {(x, y) for x, y, _ in srcs}   # a lamp does not light itself
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
                continue
            c, g = px[x, y], glow[x][y]
            px[x, y] = (min(255, int(c[0] + g[0])),
                        min(255, int(c[1] + g[1])),
                        min(255, int(c[2] + g[2])))


_GS = VIEW_H / 270.0
LAYERS = {
    "bg_far": (["bg_far_a", "bg_far_b", "bg_far_c"], 0.42, 0.026, int(round(5 * _GS))),
    "bg_mid": (["bg_mid_a", "bg_mid_b", "bg_mid_c"], 0.62, 0.055, int(round(7 * _GS))),
}

for name, (segments, dim, gstr, grad) in LAYERS.items():
    prepared = []
    for seg in segments:
        src = pathlib.Path(f"{seg}.png")
        if not src.exists():
            print(f"  !! missing {src}, skipping")
            continue
        im = Image.open(src).convert("RGB")
        w, h = im.size
        nw = max(1, round(w * VIEW_H / h))
        im = im.resize((nw, VIEW_H), Image.NEAREST)

        # NO PALETTE SNAP HERE, deliberately. The 12-colour lock exists so the
        # CHARACTER reads consistently; forcing it on the city collapsed magenta
        # and orange into red and purple into blue, which is exactly what made
        # the backdrop feel dead. The city keeps its own colour; separation from
        # the foreground comes from the dim pass below, not from a shared palette.
        px = im.load()
        sky, light_sky = sky_mask(im)
        lights = find_lights(im)
        for x in range(nw):
            for y in range(VIEW_H):
                c = px[x, y]
                px[x, y] = (int(c[0] * dim + 10 * (1 - dim)),
                            int(c[1] * dim + 14 * (1 - dim)),
                            int(c[2] * dim + 31 * (1 - dim)))
        add_glow(im, lights, gstr, grad)

        rgba = im.convert("RGBA")
        rp = rgba.load()
        for x in range(nw):
            for y in range(VIEW_H):
                if sky[x][y] and (light_sky or max(rp[x, y][:3]) < 34):
                    rp[x, y] = (0, 0, 0, 0)
        prepared.append(rgba)
        cols = len({rp[x, y][:3] for x in range(0, nw, 3)
                    for y in range(0, VIEW_H, 3) if rp[x, y][3] > 0})
        print(f"  {seg}: {nw}x{VIEW_H}, {len(lights)} lights, {cols} colours kept")

    if not prepared:
        continue
    total = sum(p.width for p in prepared)
    pano = Image.new("RGBA", (total, VIEW_H), (0, 0, 0, 0))
    x = 0
    for p in prepared:
        pano.paste(p, (x, 0))
        x += p.width
    pano.save(OUT / f"{name}.png")
    print(f"{name}: {len(prepared)} segments -> {total}x{VIEW_H} panorama "
          f"(no mirroring, nothing repeats)")

# --- the single giant torii, as its own sprite
t = pathlib.Path("torii_landmark.png")
if t.exists():
    im = Image.open(t).convert("RGB")
    w, h = im.size
    nh = 150                                  # tall enough to break the skyline
    nw = max(1, round(w * nh / h))
    im = im.resize((nw, nh), Image.NEAREST)
    px = im.load()
    # polarity again: this sheet comes back on black OR white. Assuming black
    # kept a white slab around the gate, which rendered as an opaque box on the
    # skyline. Detect from the corners, then flood the field from the border so
    # the gap BETWEEN the pillars is cleared too, not just the outside.
    corners = [px[0, 0], px[nw - 1, 0], px[0, nh - 1], px[nw - 1, nh - 1]]
    light_field = sum(max(c) for c in corners) / 4 > 110

    def is_field(c):
        return min(c) > 170 if light_field else max(c) < 26

    field = [[False] * nh for _ in range(nw)]
    q = deque([(x, 0) for x in range(nw)] + [(x, nh - 1) for x in range(nw)] +
              [(0, y) for y in range(nh)] + [(nw - 1, y) for y in range(nh)])
    while q:
        x, y = q.popleft()
        if not (0 <= x < nw and 0 <= y < nh) or field[x][y]:
            continue
        if not is_field(px[x, y]):
            continue
        field[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    op = out.load()
    kept = 0
    for x in range(nw):
        for y in range(nh):
            if field[x][y] or is_field(px[x, y]):
                continue
            s = snap(px[x, y])
            op[x, y] = (int(s[0] * 0.55 + 4), int(s[1] * 0.55 + 6),
                        int(s[2] * 0.55 + 14), 255)   # dimmed to sit far away
            kept += 1
    out.save(OUT / "torii.png")
    print(f"torii.png: {nw}x{nh}, {'light' if light_field else 'dark'} field, "
          f"{kept} px kept")
