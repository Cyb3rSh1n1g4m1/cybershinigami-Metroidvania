"""Slice the nano-banana canon sprite sheet into normalized game frames.

Pipeline: detect row bands -> split cells -> flood-remove white bg from the
edges (interior whites like the haori survive) -> snap every pixel to the
locked 15-color palette -> scale to a uniform figure height -> plant on a
96x96 canvas with feet at the shared baseline y=84.

Run: python slice_canon.py   ->  canon_frames/pose_rRcC.png + row contact strips
"""
from collections import deque
from PIL import Image
import pathlib

SRC = pathlib.Path("../reference/gen_spritesheet.png")
OUT = pathlib.Path("canon_frames")
OUT.mkdir(exist_ok=True)

PALETTE = [
    (10, 14, 31), (30, 51, 217), (43, 111, 232), (53, 198, 244),
    (143, 232, 255), (143, 17, 22), (224, 31, 38), (198, 240, 42),
    (107, 138, 15), (255, 255, 255), (74, 85, 104),
    (74, 42, 26), (133, 84, 52), (176, 122, 74),
]

img = Image.open(SRC).convert("RGB")
W, H = img.size
px = img.load()
print(f"source {W}x{H}")


def colored(x, y):
    r, g, b = px[x, y]
    return max(r, g, b) - min(r, g, b) > 25 and max(r, g, b) > 40


def nonwhite(x, y):
    r, g, b = px[x, y]
    return r < 215 or g < 215 or b < 215


# ---- 1. row bands: colored OR heavy dark density (keeps black legs in-band;
# thin label text stays below the dark threshold)
bands, start = [], None
for y in range(H):
    c = sum(1 for x in range(0, W, 2) if colored(x, y))
    d = sum(1 for x in range(0, W, 2) if nonwhite(x, y))
    dense = c > 8 or d > 90
    if dense and start is None:
        start = y
    elif not dense and start is not None:
        if y - start > 60:
            bands.append((start, y))
        start = None
if start is not None and H - start > 60:
    bands.append((start, H))

# extend each band downward until a real white gap (3 consecutive near-empty
# rows) — keeps sparse black boots that fall under the density threshold
ext = []
for i, (y0, y1) in enumerate(bands):
    limit = bands[i + 1][0] - 1 if i + 1 < len(bands) else H
    empty_run = 0
    y = y1
    while y < limit and empty_run < 3:
        d = sum(1 for x in range(0, W, 2) if nonwhite(x, y))
        empty_run = empty_run + 1 if d < 8 else 0
        y += 1
    ext.append((y0, min(y, limit)))
bands = ext
print(f"row bands: {bands}")

# ---- 2. split each band into cells at colored-projection gaps
cells = []
for bi, (y0, y1) in enumerate(bands):
    col_density = [sum(1 for y in range(y0, y1) if colored(x, y)) for x in range(W)]
    in_cell, cs = False, 0
    gap = 0
    for x in range(W):
        if col_density[x] > 2:
            if not in_cell:
                in_cell, cs = True, x
            gap = 0
        elif in_cell:
            gap += 1
            if gap >= 12:
                if x - gap - cs > 40:
                    cells.append((bi, cs, y0, x - gap, y1))
                in_cell = False
    if in_cell and W - cs > 40:
        cells.append((bi, cs, y0, W, y1))
print(f"cells: {len(cells)}")


SATURATED = [p for p in PALETTE if max(p) - min(p) > 30]


def snap(c):
    r, g, b = c
    sat = max(c) - min(c)
    if sat < 32:                       # neutral pixel: never snap to a skin tone
        v = max(c)
        if v > 200:
            return (255, 255, 255)
        if v > 60:
            return (74, 85, 104)       # GREY
        return (10, 14, 31)            # INK
    return min(SATURATED, key=lambda p: sum((a - b) ** 2 for a, b in zip(p, c)))


# ---- 3. per cell: bg-flood, palette snap
# scale anchors to the TALLEST figure per row so crouch/prone poses stay low
FIG_H = 76
BASELINE = 84
figs = []       # (band, fig image)
for bi, x0, y0, x1, y1 in cells:
    crop = img.crop((x0, y0, x1, y1)).convert("RGBA")
    cw, ch = crop.size
    cpx = crop.load()
    # flood white/near-white background from the border
    bg = [[False] * ch for _ in range(cw)]
    q = deque()
    for x in range(cw):
        for y in (0, ch - 1):
            q.append((x, y))
    for y in range(ch):
        for x in (0, cw - 1):
            q.append((x, y))
    while q:
        x, y = q.popleft()
        if not (0 <= x < cw and 0 <= y < ch) or bg[x][y]:
            continue
        r, g, b, _ = cpx[x, y]
        # tolerant: catches the anti-aliasing halo, not just pure white
        if r > 185 and g > 185 and b > 185 and max(r, g, b) - min(r, g, b) < 26:
            bg[x][y] = True
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    # halo sweep: any near-white pixel adjacent to background is halo too
    for _ in range(2):
        edge = [(x, y) for x in range(cw) for y in range(ch)
                if not bg[x][y]
                and cpx[x, y][0] > 170 and cpx[x, y][1] > 170 and cpx[x, y][2] > 170
                and max(cpx[x, y][:3]) - min(cpx[x, y][:3]) < 30
                and any(0 <= x + dx < cw and 0 <= y + dy < ch and bg[x + dx][y + dy]
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in edge:
            bg[x][y] = True
    # apply: bg -> transparent, rest -> palette snap
    minx, miny, maxx, maxy = cw, ch, 0, 0
    for x in range(cw):
        for y in range(ch):
            if bg[x][y]:
                cpx[x, y] = (0, 0, 0, 0)
            else:
                r, g, b, _ = cpx[x, y]
                cpx[x, y] = (*snap((r, g, b)), 255)
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    if maxx <= minx or maxy <= miny:
        continue
    figs.append((bi, crop.crop((minx, miny, maxx + 1, maxy + 1))))

counts = {}
row_max = {}
for bi, fig in figs:
    row_max[bi] = max(row_max.get(bi, 1), fig.height)
for bi, fig in figs:
    scale = FIG_H / row_max[bi]                    # per-row anchor
    nw = max(1, round(fig.width * scale))
    nh = max(1, round(fig.height * scale))
    fig = fig.resize((nw, nh), Image.NEAREST)
    cell96 = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    cell96.paste(fig, ((96 - nw) // 2, BASELINE - nh))  # feet share the baseline
    ci = counts.get(bi, 0)
    counts[bi] = ci + 1
    cell96.save(OUT / f"pose_r{bi}c{ci}.png")

print(f"per-row counts: {counts}")

# ---- 4. contact strips per row + 4x previews
for bi, n in counts.items():
    strip = Image.new("RGBA", (96 * n, 96), (0, 0, 0, 0))
    for ci in range(n):
        strip.paste(Image.open(OUT / f"pose_r{bi}c{ci}.png"), (ci * 96, 0))
    strip.save(OUT / f"row{bi}.png")
    strip.resize((strip.width * 4, 384), Image.NEAREST).save(OUT / f"row{bi}_4x.png")
    print(f"row{bi}.png  {n}f")
