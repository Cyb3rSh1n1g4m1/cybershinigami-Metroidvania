"""Slice the upgrade-module and pedestal sheets into uniform square cells.

Both are drawn as a row of separate artifacts on black. The game indexes them by
cell, so every cell must be the SAME width and each artifact centred in its own.

Run: python slice_objects.py
"""
from collections import deque
from PIL import Image
import pathlib

REF = pathlib.Path("../reference")
GAME = pathlib.Path("../../game/art/objects")
GAME.mkdir(parents=True, exist_ok=True)
CELL = 96

# (reference sheet, shipped name, cells) — the shrine sheet ships as shrine.png
JOBS = [("upgrade_modules", "upgrade_modules", 6),
        ("upgrade_pedestal", "upgrade_pedestal", 4),
        ("shrine_v2", "shrine", 4)]


def slice_row(name, out, want):
    img = Image.open(REF / f"{name}.png").convert("RGBA")
    W, H = img.size
    px = img.load()
    def is_bg(c):
        # MIXED POLARITY is real: the shrine sheet came back with white paper
        # around black panels, so a white-only test left the panels as opaque
        # black boxes behind the art. Treat BOTH extremes as background — INK
        # cloth is (10,14,31), max 31, so it survives the dark threshold.
        return min(c[:3]) > 214 or max(c[:3]) < 26

    # column projection -> one span per artifact
    mass = [sum(1 for y in range(0, H, 2) if not is_bg(px[x, y])) for x in range(W)]
    spans, inrun, s, gap = [], False, 0, 0
    for x in range(W):
        if mass[x] > 1:
            if not inrun:
                inrun, s = True, x
            gap = 0
        elif inrun:
            gap += 1
            if gap >= 12:
                if x - gap - s > 12:
                    spans.append((s, x - gap))
                inrun = False
    if inrun and W - s > 12:
        spans.append((s, W - 1))

    if len(spans) != want:
        print(f"{name}: found {len(spans)} spans, wanted {want} — forcing even split")
        step = W / float(want)
        spans = [(int(i * step), int((i + 1) * step) - 1) for i in range(want)]

    sheet = Image.new("RGBA", (CELL * want, CELL), (0, 0, 0, 0))
    for i, (x0, x1) in enumerate(spans):
        cell = img.crop((x0, 0, x1 + 1, H))
        cp = cell.load()
        cw, ch = cell.size
        # flood the field so the transparent middle of the Tunnel ring clears too
        seen = [[False] * ch for _ in range(cw)]
        q = deque([(x, 0) for x in range(cw)] + [(x, ch - 1) for x in range(cw)] +
                  [(0, y) for y in range(ch)] + [(cw - 1, y) for y in range(ch)])
        while q:
            x, y = q.popleft()
            if not (0 <= x < cw and 0 <= y < ch) or seen[x][y] or not is_bg(cp[x, y]):
                continue
            seen[x][y] = True
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        mnx, mny, mxx, mxy = cw, ch, 0, 0
        for x in range(cw):
            for y in range(ch):
                if seen[x][y] or is_bg(cp[x, y]):
                    cp[x, y] = (0, 0, 0, 0)
                else:
                    mnx, mny = min(mnx, x), min(mny, y)
                    mxx, mxy = max(mxx, x), max(mxy, y)
        if mxx <= mnx or mxy <= mny:
            continue
        art = cell.crop((mnx, mny, mxx + 1, mxy + 1))
        sc = min((CELL - 8) / art.width, (CELL - 8) / art.height)
        nw, nh = max(1, round(art.width * sc)), max(1, round(art.height * sc))
        art = art.resize((nw, nh), Image.NEAREST)
        sheet.paste(art, (i * CELL + (CELL - nw) // 2, (CELL - nh) // 2))

    sheet.save(GAME / f"{out}.png")
    sheet.resize((sheet.width * 3, CELL * 3), Image.NEAREST).save(f"{out}_3x.png")
    print(f"ok: {out}.png  {want} cells x {CELL}px")


for name, out, want in JOBS:
    slice_row(name, out, want)
