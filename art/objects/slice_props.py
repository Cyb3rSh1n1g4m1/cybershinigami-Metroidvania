"""Slice props_fg.png into a uniform 64px prop atlas for the play layer.

Ten foreground objects laid out 5x2 on white. Each is cropped to its own content,
scaled to fit a 64px cell, and BOTTOM-ALIGNED so a prop placed at a floor y sits on
the floor rather than floating.

Run: python slice_props.py
"""
from collections import deque
from PIL import Image
import pathlib

REF = pathlib.Path("../reference")
GAME = pathlib.Path("../../game/art/objects")
GAME.mkdir(parents=True, exist_ok=True)
CELL = 64
WANT = 10

img = Image.open(REF / "props_fg.png").convert("RGBA")
W, H = img.size
px = img.load()


def is_paper(c):
    return min(c[:3]) > 214 or max(c[:3]) < 12


def bands(vertical: bool):
    n, m = (H, W) if vertical else (W, H)
    out, start = [], None
    for i in range(n):
        hits = sum(1 for j in range(0, m, 3)
                   if not is_paper(px[j, i] if vertical else px[i, j]))
        if hits > 2 and start is None:
            start = i
        elif hits <= 2 and start is not None:
            if i - start > 30:
                out.append((start, i))
            start = None
    if start is not None and n - start > 30:
        out.append((start, n))
    return out


cells = []
for y0, y1 in bands(True):
    for x0, x1 in bands(False):
        if sum(1 for x in range(x0, x1, 3) for y in range(y0, y1, 3)
               if not is_paper(px[x, y])) > 60:
            cells.append((x0, y0, x1, y1))
print(f"detected {len(cells)} props (wanted {WANT})")

sheet = Image.new("RGBA", (CELL * max(WANT, len(cells)), CELL), (0, 0, 0, 0))
for i, (x0, y0, x1, y1) in enumerate(cells[:WANT]):
    cell = img.crop((x0, y0, x1, y1))
    cp = cell.load()
    cw, ch = cell.size
    seen = [[False] * ch for _ in range(cw)]
    q = deque([(x, 0) for x in range(cw)] + [(x, ch - 1) for x in range(cw)] +
              [(0, y) for y in range(ch)] + [(cw - 1, y) for y in range(ch)])
    while q:
        x, y = q.popleft()
        if not (0 <= x < cw and 0 <= y < ch) or seen[x][y] or not is_paper(cp[x, y]):
            continue
        seen[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    mnx, mny, mxx, mxy = cw, ch, 0, 0
    for x in range(cw):
        for y in range(ch):
            if seen[x][y]:
                cp[x, y] = (0, 0, 0, 0)
            elif cp[x, y][3] > 0:
                mnx, mny = min(mnx, x), min(mny, y)
                mxx, mxy = max(mxx, x), max(mxy, y)
    if mxx <= mnx or mxy <= mny:
        continue
    art = cell.crop((mnx, mny, mxx + 1, mxy + 1))
    sc = min((CELL - 2) / art.width, (CELL - 2) / art.height)
    nw, nh = max(1, round(art.width * sc)), max(1, round(art.height * sc))
    art = art.resize((nw, nh), Image.NEAREST)
    # bottom-aligned: props are placed by their feet, not their centre
    sheet.paste(art, (i * CELL + (CELL - nw) // 2, CELL - nh))

sheet.save(GAME / "props_fg.png")
sheet.resize((sheet.width * 3, CELL * 3), Image.NEAREST).save("props_fg_3x.png")
print(f"ok: props_fg.png  {min(WANT, len(cells))} cells x {CELL}px, bottom-aligned")
