"""Build the game's 16px tile atlas from tileset_v2.png.

room.gd indexes fixed cells, so the atlas order is contractual:
  (0,0) solid interior   (1,0) one-way platform
  (2,0) hazard spikes    (3,0) solid TOP (lit edge)

The generated one-way platform tile is drawn in PERSPECTIVE (its top surface is
visible as a parallelogram), which breaks the game's strict side elevation. Rather
than spend a regeneration on one tile, it is SYNTHESISED here from the lit-top
tile: a thin flat bar with the same lit edge. Same projection, guaranteed.

Run: python prep_tileset2.py
"""
from collections import deque
from PIL import Image
import pathlib

OUT = pathlib.Path(__file__).parents[2] / "game" / "art" / "tileset.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
TILE = 16

img = Image.open("tileset_v2.png").convert("RGBA")
W, H = img.size
px = img.load()


def is_paper(c):
    # the sheet mixes white paper and near-black gaps between tiles
    return (min(c[:3]) > 216) or (max(c[:3]) < 14)


# --- find tile cells by projection over non-paper pixels
def bands(vertical: bool):
    n, m = (H, W) if vertical else (W, H)
    out, start = [], None
    for i in range(n):
        hits = sum(1 for j in range(0, m, 3)
                   if not is_paper(px[j, i] if vertical else px[i, j]))
        dense = hits > 2
        if dense and start is None:
            start = i
        elif not dense and start is not None:
            if i - start > 24:
                out.append((start, i))
            start = None
    if start is not None and n - start > 24:
        out.append((start, n))
    return out


cells = []
for y0, y1 in bands(True):
    for x0, x1 in bands(False):
        sub = sum(1 for x in range(x0, x1, 3) for y in range(y0, y1, 3)
                  if not is_paper(px[x, y]))
        if sub > 40:
            cells.append((x0, y0, x1, y1))
print(f"detected {len(cells)} tile cells")


def extract(idx, size=TILE):
    x0, y0, x1, y1 = cells[idx]
    cell = img.crop((x0, y0, x1, y1))
    cp = cell.load()
    cw, ch = cell.size
    # clear paper from the border inward so tile interiors survive
    q = deque([(x, 0) for x in range(cw)] + [(x, ch - 1) for x in range(cw)] +
              [(0, y) for y in range(ch)] + [(cw - 1, y) for y in range(ch)])
    seen = [[False] * ch for _ in range(cw)]
    while q:
        x, y = q.popleft()
        if not (0 <= x < cw and 0 <= y < ch) or seen[x][y] or not is_paper(cp[x, y]):
            continue
        seen[x][y] = True
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for x in range(cw):
        for y in range(ch):
            if seen[x][y]:
                cp[x, y] = (0, 0, 0, 0)
    return cell.resize((size, size), Image.LANCZOS)


# indices into the detected grid, chosen by eye from tileset_v2.png
IDX_TOP, IDX_INTERIOR, IDX_HAZARD = 0, 1, 7

atlas = Image.new("RGBA", (TILE * 4, TILE), (0, 0, 0, 0))
top = extract(IDX_TOP)
atlas.paste(extract(IDX_INTERIOR), (0, 0))
atlas.paste(extract(IDX_HAZARD), (2 * TILE, 0))
atlas.paste(top, (3 * TILE, 0))

# --- synthesise the one-way platform from the lit-top tile: keep its top 6 rows
# (the lit edge and a sliver of body), leave the rest transparent so the player
# can jump up through it. Guarantees the same projection as every other tile.
oneway = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
oneway.paste(top.crop((0, 0, TILE, 6)), (0, 4))
op = oneway.load()
for x in range(TILE):                       # a couple of support ticks underneath
    if x % 5 == 2:
        for y in range(10, 13):
            op[x, y] = (10, 14, 31, 255)
atlas.paste(oneway, (TILE, 0))

atlas.save(OUT)
atlas.resize((atlas.width * 12, TILE * 12), Image.NEAREST).save("_tileset2_12x.png")
print(f"saved {OUT}  ({atlas.width}x{TILE})  order: interior, oneway, hazard, top")
