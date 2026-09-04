"""Slice fx_crescent.png (4 crescent phases on white) into crescent.png —
4 uniform 64px cells for Fx.wave. White cores are sealed by green rims, so:
border-flood the white bg, then reclaim enclosed whites (the §spritedrift
white-on-white topology rules). Frames split by COLUMN GAPS so frame 4's
detached sparks stay with their crescent. ONE scale for all four cells keeps
the born-small -> full -> dissolve size progression.

Run: python slice_crescent.py
"""
import pathlib
from collections import deque

from PIL import Image

SRC = pathlib.Path(__file__).parents[1] / "reference" / "fx_crescent.png"
OUT = pathlib.Path(__file__).parents[2] / "game" / "art" / "effects" / "crescent.png"
CELL = 64

img = Image.open(SRC).convert("RGBA")
W, H = img.size
px = img.load()


def is_white(c):
    return min(c[0], c[1], c[2]) > 235 and max(c[0], c[1], c[2]) - min(c[0], c[1], c[2]) < 15


bg = [[False] * H for _ in range(W)]
q = deque()
for x in range(W):
    q.extend(((x, 0), (x, H - 1)))
for y in range(H):
    q.extend(((0, y), (W - 1, y)))
while q:
    x, y = q.popleft()
    if not (0 <= x < W and 0 <= y < H) or bg[x][y]:
        continue
    if is_white(px[x, y][:3]):
        bg[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

# NO reclaim pass: the rims fully seal the hot cores, so the border flood
# never reaches them and they survive naturally. Ray-reclaim over-filled the
# crescents' open mouths (concave shapes defeat the 4-ray enclosure test).

# frames by column gaps
cols = [any(not bg[x][y] for y in range(H)) for x in range(W)]
ranges, start = [], None
for x in range(W):
    if cols[x] and start is None:
        start = x
    elif not cols[x] and start is not None:
        if x - start > 12:
            ranges.append((start, x))
        start = None
if start is not None:
    ranges.append((start, W))
# detached sparks can sit a small gap away from their crescent — merge ranges
# whose separation is smaller than a real inter-frame gutter
merged = [ranges[0]]
for r in ranges[1:]:
    if r[0] - merged[-1][1] < 45:
        merged[-1] = (merged[-1][0], r[1])
    else:
        merged.append(r)
ranges = merged
assert len(ranges) == 4, f"expected 4 frames, found {len(ranges)}"

crops = []
for x0, x1 in ranges:
    ys = [y for x in range(x0, x1) for y in range(H) if not bg[x][y]]
    y0, y1 = min(ys), max(ys) + 1
    c = img.crop((x0, y0, x1, y1)).convert("RGBA")
    cp = c.load()
    for x in range(c.width):
        for y in range(c.height):
            if bg[x0 + x][y0 + y]:
                cp[x, y] = (0, 0, 0, 0)
    crops.append(c)

scale = (CELL - 6) / max(c.height for c in crops)   # ONE scale: keep progression
strip = Image.new("RGBA", (CELL * 4, CELL), (0, 0, 0, 0))
for i, c in enumerate(crops):
    nw, nh = max(1, round(c.width * scale)), max(1, round(c.height * scale))
    r = c.resize((nw, nh), Image.NEAREST)
    strip.paste(r, (i * CELL + (CELL - nw) // 2, (CELL - nh) // 2), r)
strip.save(OUT)
print(f"ok: crescent.png  4f {CELL}px cells (scale {scale:.2f})")
