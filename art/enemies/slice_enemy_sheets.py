"""Slice the generated enemy/boss sheets into game-ready animation strips.

Reuses the player slicer's approach (auto bg polarity, flood + halo removal,
palette snap, uniform cell) but sizes cells per enemy.

Run: python slice_enemy_sheets.py
"""
from collections import deque
from PIL import Image
import pathlib

REF = pathlib.Path("../reference")
GAME = pathlib.Path("../../game/art/enemies")
GAME.mkdir(parents=True, exist_ok=True)

PALETTE = [
    (10, 14, 31), (30, 51, 217), (43, 111, 232), (53, 198, 244),
    (143, 232, 255), (143, 17, 22), (224, 31, 38), (198, 240, 42),
    (107, 138, 15), (255, 255, 255), (74, 85, 104),
]
SATURATED = [p for p in PALETTE if max(p) - min(p) > 30]

# ANCHOR NORMALISATION, same principle as the player: scale each enemy from a
# pose-invariant landmark rather than from its tallest frame. Scaling by tallest
# frame lets one rearing or mid-swing pose shrink every other frame in the strip.
# Each anchor is a colour that belongs to a rigid part of the creature.
# An anchor only works if the colour is LOCALISED to one rigid part. Worm and
# drone are deliberately absent: the worm's red seam lines run the whole length of
# its body and the drone's cyan appears in its rotors too, so the "anchor" bbox
# measured the entire creature (276px and 215px) and scaled them to 5% of size.
# Both have a rigid horizontal extent instead, so cell-width fitting is correct
# for them — their measured width was already constant frame to frame.
ANCHORS = {
    "husk":     [(255, 255, 255), (143, 232, 255)],  # cracked white mask
    "guardian": [(224, 31, 38), (143, 17, 22)],      # red oni mask on the shoulder
}


def anchor_size(img, anchors, tol=34):
    """Largest bbox dimension of the anchor's LARGEST CONNECTED COMPONENT.
    Largest dimension, not height: a rotating part compresses one axis while the
    other holds. Largest component, not the union: stray anchor-coloured pixels
    elsewhere on the body double a union bbox and wreck the scale."""
    px = img.load()
    w, h = img.size
    pts = set()
    for x in range(w):
        for y in range(h):
            c = px[x, y]
            if c[3] == 0:
                continue
            for a in anchors:
                if (abs(c[0] - a[0]) < tol and abs(c[1] - a[1]) < tol
                        and abs(c[2] - a[2]) < tol):
                    pts.add((x, y))
                    break
    if not pts:
        return 0
    best = []
    while pts:
        stack = [pts.pop()]
        comp = []
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    n = (cx + dx, cy + dy)
                    if n in pts:
                        pts.discard(n)
                        stack.append(n)
        if len(comp) > len(best):
            best = comp
    xs = [p[0] for p in best]
    ys = [p[1] for p in best]
    return max(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def _median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else 0


# sheet -> (output name, cell size, how many frames to keep)
JOBS = [
    ("enemy_worm_sheet",  "worm",     64, 6),
    ("enemy_drone_sheet", "drone",    48, 6),
    ("enemy_husk_sheet",  "husk",     64, 6),
    ("boss_bruteforce",   "guardian", 96, 6),
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


_PAL_HSV = [(p, _hsv(p)) for p in SATURATED]


def snap(c):
    if max(c) - min(c) < 32:
        v = max(c)
        return (255, 255, 255) if v > 200 else (74, 85, 104) if v > 60 else (10, 14, 31)
    # hue-first match: RGB distance mistakes desaturated indigo for dark red
    h, s, v = _hsv(c)

    def cost(entry):
        _, (ph, ps, pv) = entry
        dh = abs(h - ph)
        dh = min(dh, 360 - dh) / 180.0        # circular, normalized
        return dh * 3.0 + abs(v - pv) * 1.0 + abs(s - ps) * 0.4

    return min(_PAL_HSV, key=cost)[0]


def slice_sheet(src, name, cell, keep):
    img = Image.open(REF / f"{src}.png").convert("RGB")
    W, H = img.size
    px = img.load()
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    dark_bg = sum(max(c) for c in corners) / 4 < 110

    def is_bg(c):
        r, g, b = c
        if dark_bg:
            return max(r, g, b) < 6
        return r > 185 and g > 185 and b > 185 and max(r, g, b) - min(r, g, b) < 26

    def ink(x, y):
        return not is_bg(px[x, y])

    bands, start = [], None
    for y in range(H):
        d = sum(1 for x in range(0, W, 2) if ink(x, y))
        if d > 3 and start is None:
            start = y
        elif d <= 3 and start is not None:
            if y - start > 30:
                bands.append((start, y))
            start = None
    if start is not None and H - start > 30:
        bands.append((start, H))

    cells = []
    for y0, y1 in bands:
        cd = [sum(1 for y in range(y0, y1) if ink(x, y)) for x in range(W)]
        in_c, cs, gap = False, 0, 0
        for x in range(W):
            if cd[x] > 1:
                if not in_c:
                    in_c, cs = True, x
                gap = 0
            elif in_c:
                gap += 1
                if gap >= 12:
                    if x - gap - cs > 24:
                        cells.append((cs, y0, x - gap, y1))
                    in_c = False
        if in_c and W - cs > 24:
            cells.append((cs, y0, W, y1))

    figs = []
    for x0, y0, x1, y1 in cells:
        crop = img.crop((x0, y0, x1, y1)).convert("RGBA")
        cw, ch = crop.size
        cpx = crop.load()
        bg = [[False] * ch for _ in range(cw)]
        q = deque()
        for x in range(cw):
            q.extend(((x, 0), (x, ch - 1)))
        for y in range(ch):
            q.extend(((0, y), (cw - 1, y)))
        while q:
            x, y = q.popleft()
            if not (0 <= x < cw and 0 <= y < ch) or bg[x][y]:
                continue
            if is_bg(cpx[x, y][:3]):
                bg[x][y] = True
                q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

        def halo(c):
            return max(c) < 9 if dark_bg else (min(c) > 170 and max(c) - min(c) < 30)

        for _ in range(2):
            edge = [(x, y) for x in range(cw) for y in range(ch)
                    if not bg[x][y] and halo(cpx[x, y][:3])
                    and any(0 <= x + dx < cw and 0 <= y + dy < ch and bg[x + dx][y + dy]
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
            for x, y in edge:
                bg[x][y] = True
        mnx, mny, mxx, mxy = cw, ch, 0, 0
        for x in range(cw):
            for y in range(ch):
                if bg[x][y]:
                    cpx[x, y] = (0, 0, 0, 0)
                else:
                    cpx[x, y] = (*snap(cpx[x, y][:3]), 255)
                    mnx, mny = min(mnx, x), min(mny, y)
                    mxx, mxy = max(mxx, x), max(mxy, y)
        if mxx > mnx and mxy > mny:
            figs.append(crop.crop((mnx, mny, mxx + 1, mxy + 1)))

    if not figs:
        print(f"{src}: no cells")
        return
    figs = figs[:keep]
    fit = cell - 4
    # anchor-based scale where the landmark is visible; tallest-frame otherwise
    anchors = ANCHORS.get(name)
    anchor_scale = 0.0
    if anchors:
        found = [a for a in (anchor_size(f, anchors) for f in figs) if a > 0]
        if len(found) >= max(2, len(figs) // 2):
            med = _median(found)
            target = fit * 0.22        # landmark reads as ~22% of the cell
            anchor_scale = target / float(med)
            print(f"  {name}: anchor median {med}px -> scale {anchor_scale:.3f} "
                  f"(range {min(found)}-{max(found)})")
    tallest = max(f.height for f in figs)
    strip = Image.new("RGBA", (cell * len(figs), cell), (0, 0, 0, 0))
    for i, f in enumerate(figs):
        s = anchor_scale if anchor_scale > 0.0 else fit / tallest
        nw, nh = max(1, round(f.width * s)), max(1, round(f.height * s))
        if nw > cell:                       # never overflow the cell horizontally
            s *= cell / nw
            nw, nh = max(1, round(f.width * s)), max(1, round(f.height * s))
        strip.paste(f.resize((nw, nh), Image.NEAREST),
                    (i * cell + (cell - nw) // 2, cell - 2 - nh))
    strip.save(GAME / f"{name}.png")
    strip.resize((strip.width * 6, cell * 6), Image.NEAREST).save(f"{name}_6x.png")
    print(f"ok: {name}.png  {len(figs)}f  {cell}px cells")


for src, name, cell, keep in JOBS:
    slice_sheet(src, name, cell, keep)
