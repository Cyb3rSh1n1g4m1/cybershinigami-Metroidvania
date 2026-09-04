"""Build the game's 16px tile atlas from the generated tileset art.

The generator returns big decorative tiles on white; room.gd wants a compact
atlas of 16x16 cells in a fixed order. Detect the source cells, pick the ones
we need, downscale, palette-snap, and emit the atlas room.gd indexes into.

Atlas order (must match room.gd ATLAS):
  (0,0) solid interior   (1,0) one-way platform
  (2,0) hazard spikes    (3,0) solid TOP (lit edge)

Run: python prep_tileset.py
"""
from PIL import Image
import pathlib

OUT = pathlib.Path(r"D:\Projects\Cybershinigami\game\art\tileset.png")
OUT.parent.mkdir(parents=True, exist_ok=True)
TILE = 16

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


img = Image.open("tileset.png").convert("RGB")
W, H = img.size
px = img.load()


def is_bg(x, y):
    r, g, b = px[x, y]
    return r > 200 and g > 200 and b > 200


# --- find the source cells by projection gaps (same approach as the sprite slicer)
rows, start = [], None
for y in range(H):
    d = sum(1 for x in range(0, W, 2) if not is_bg(x, y))
    if d > 3 and start is None:
        start = y
    elif d <= 3 and start is not None:
        if y - start > 30:
            rows.append((start, y))
        start = None
if start is not None and H - start > 30:
    rows.append((start, H))

cells = []
for y0, y1 in rows:
    cd = [sum(1 for y in range(y0, y1) if not is_bg(x, y)) for x in range(W)]
    inc, cs, gap = False, 0, 0
    for x in range(W):
        if cd[x] > 2:
            if not inc:
                inc, cs = True, x
            gap = 0
        elif inc:
            gap += 1
            if gap >= 8:
                if x - gap - cs > 30:
                    cells.append((cs, y0, x - gap, y1))
                inc = False
    if inc and W - cs > 30:
        cells.append((cs, y0, W, y1))

print(f"source cells found: {len(cells)}")

# indices into the detected grid, chosen by eye from the generated sheet
PICK = {
    "interior": 7,   # plain dark filler
    "oneway":   8,   # thin platform with lit top
    "hazard":   11,  # spikes with red tips
    "top":      1,   # ground with the cyan glowing top edge
}
order = ["interior", "oneway", "hazard", "top"]

atlas = Image.new("RGBA", (TILE * len(order), TILE), (0, 0, 0, 0))
for i, key in enumerate(order):
    idx = PICK[key]
    if idx >= len(cells):
        print(f"  !! {key}: index {idx} out of range, using cell 0")
        idx = 0
    x0, y0, x1, y1 = cells[idx]
    src = img.crop((x0, y0, x1, y1)).convert("RGBA")
    sp = src.load()
    # the source sheet's white paper is background, not a material — drop it first
    # or it survives the downscale and shows as a white block behind the tile
    for x in range(src.width):
        for y in range(src.height):
            r, g, b, _ = sp[x, y]
            if r > 200 and g > 200 and b > 200:
                sp[x, y] = (0, 0, 0, 0)
    t = src.resize((TILE, TILE), Image.NEAREST)
    tp = t.load()
    for x in range(TILE):
        for y in range(TILE):
            if tp[x, y][3] < 128:
                tp[x, y] = (0, 0, 0, 0)
            else:
                tp[x, y] = (*snap(tp[x, y][:3]), 255)
    atlas.paste(t, (i * TILE, 0))
    print(f"  {key}: source cell {idx} -> atlas ({i},0)")

atlas.save(OUT)
atlas.resize((atlas.width * 12, TILE * 12), Image.NEAREST).save("_tileset_12x.png")
print(f"saved {OUT}  ({atlas.width}x{TILE})")
