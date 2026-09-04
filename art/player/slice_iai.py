"""Slice the approved iai sheets into game strips — the breathing loop and (when
approved) the enter transition. Cells split by column gaps; each cell runs the
white-on-white topology pipeline (dilated dark barrier + enclosed reclaim, warm
excluded); ONE scale per sheet from the coil frame's mask (crouch-family anchor
19px, the mega crouch median); feet on the shared 84px baseline.

Run: python slice_iai.py
"""
import pathlib
from collections import deque

from PIL import Image

REF = pathlib.Path("../reference")
GAME = pathlib.Path("../../game/art/player")
TARGET_MASK = 19.0
BASELINE = 84
REDS = [(224, 31, 38), (143, 17, 22), (123, 21, 35), (89, 27, 30)]

# (source, expected cells, output, which cell anchors the scale)
JOBS = [
    ("iai_loop.png", 4, "player_iai.png", 0),
    ("iai_enter.png", 3, "player_iai_enter.png", 2),
]


def is_bg(c):
    return min(c[0], c[1], c[2]) > 240 and max(c[0], c[1], c[2]) - min(c[0], c[1], c[2]) < 10


def warm(c):
    return min(c[:3]) > 150 and c[0] - c[2] >= 12


def clean_cell(img):
    """Barrier flood + enclosed reclaim on one figure crop; returns RGBA fig."""
    W, H = img.size
    px = img.load()
    dark = [[max(px[x, y][:3]) < 120 for y in range(H)] for x in range(W)]
    barrier = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            if dark[x][y]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H:
                            barrier[nx][ny] = True
    bg = [[False] * H for _ in range(W)]
    q = deque()
    for x in range(W):
        q.extend(((x, 0), (x, H - 1)))
    for y in range(H):
        q.extend(((0, y), (W - 1, y)))
    while q:
        x, y = q.popleft()
        if not (0 <= x < W and 0 <= y < H) or bg[x][y] or barrier[x][y]:
            continue
        if is_bg(px[x, y][:3]):
            bg[x][y] = True
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for _ in range(2):
        left = [[False] * H for _ in range(W)]
        right = [[False] * H for _ in range(W)]
        up = [[False] * H for _ in range(W)]
        down = [[False] * H for _ in range(W)]
        for y in range(H):
            s = False
            for x in range(W):
                left[x][y] = s
                s = s or not bg[x][y]
            s = False
            for x in range(W - 1, -1, -1):
                right[x][y] = s
                s = s or not bg[x][y]
        for x in range(W):
            s = False
            for y in range(H):
                up[x][y] = s
                s = s or not bg[x][y]
            s = False
            for y in range(H - 1, -1, -1):
                down[x][y] = s
                s = s or not bg[x][y]
        changed = 0
        for x in range(W):
            for y in range(H):
                if bg[x][y] and left[x][y] and right[x][y] and up[x][y] \
                        and down[x][y] and not warm(px[x, y]):
                    bg[x][y] = False
                    changed += 1
        if not changed:
            break
    xs = [x for x in range(W) for y in range(H) if not bg[x][y]]
    ys = [y for x in range(W) for y in range(H) if not bg[x][y]]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    fig = img.crop((x0, y0, x1, y1))
    fp = fig.load()
    for x in range(fig.width):
        for y in range(fig.height):
            if bg[x0 + x][y0 + y]:
                fp[x, y] = (0, 0, 0, 0)
    return fig


def mask_dim(fig):
    fp = fig.load()
    pts = set()
    for x in range(fig.width):
        for y in range(fig.height):
            c = fp[x, y]
            if c[3] > 0 and any(abs(c[0] - r) < 34 and abs(c[1] - g) < 34
                                and abs(c[2] - b) < 34 for r, g, b in REDS):
                pts.add((x, y))
    best = []
    while pts:
        stack = [pts.pop()]
        comp = []
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    n = (cx + dx, cy + dy)
                    if n in pts:
                        pts.discard(n)
                        stack.append(n)
        if len(comp) > len(best):
            best = comp
    if not best:
        return 0
    return max(max(p[0] for p in best) - min(p[0] for p in best),
               max(p[1] for p in best) - min(p[1] for p in best)) + 1


def shrink(fig, nw, nh):
    """Area-averaged downscale for big JPEG-noisy renders. NEAREST at 6:1
    sampled noise into mud. Transparent pixels get their RGB padded from
    opaque neighbours first so the averaging never pulls in black fringe;
    alpha is re-hardened afterwards."""
    fig = fig.copy()
    fp = fig.load()
    w, h = fig.size
    for _ in range(3):                       # edge-pad RGB into the void
        grown = []
        for x in range(w):
            for y in range(h):
                if fp[x, y][3] == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and fp[nx, ny][3] > 0:
                            c = fp[nx, ny]
                            grown.append((x, y, (c[0], c[1], c[2], 1)))
                            break
        for x, y, c in grown:
            fp[x, y] = c
    rgb = fig.convert("RGB").resize((nw, nh), Image.BOX)
    alpha = fig.split()[3].resize((nw, nh), Image.BOX).point(
        lambda a: 255 if a >= 112 else 0)
    out_img = rgb.convert("RGBA")
    out_img.putalpha(alpha)
    return out_img


for src, want, out, anchor_i in JOBS:
    path = REF / src
    if not path.exists():
        print(f"skip: {src} (not generated yet)")
        continue
    img = Image.open(path).convert("RGBA")
    W, H = img.size
    px = img.load()
    # gutter test is LOOSER than the cleaning flood: JPEG noise leaves single
    # near-white pixels in the gaps, so demand real content (several strong
    # non-white samples) before a column counts as figure
    def strongly_inked(c):
        return min(c[0], c[1], c[2]) < 200
    # threshold 15: a drawn ground-shadow strip runs under ALL figures at a
    # constant ~8-9 samples per column — the figures themselves run 30-150
    cols = [sum(1 for y in range(0, H, 2) if strongly_inked(px[x, y][:3])) >= 15
            for x in range(W)]
    ranges, start = [], None
    for x in range(W):
        if cols[x] and start is None:
            start = x
        elif not cols[x] and start is not None:
            if x - start > 40:
                ranges.append((start, x))
            start = None
    if start is not None:
        ranges.append((start, W))
    merged = [ranges[0]]
    for r in ranges[1:]:
        if r[0] - merged[-1][1] < 30:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    ranges = merged
    assert len(ranges) == want, f"{src}: expected {want} cells, found {len(ranges)}"

    figs = [clean_cell(img.crop((x0, 0, x1, H))) for x0, x1 in ranges]
    md = mask_dim(figs[anchor_i])
    scale = TARGET_MASK / md            # ONE scale: the sheet is one generation
    strip = Image.new("RGBA", (96 * want, 96), (0, 0, 0, 0))
    for i, fig in enumerate(figs):
        nw, nh = max(1, round(fig.width * scale)), max(1, round(fig.height * scale))
        small = shrink(fig, nw, nh)
        strip.paste(small, (i * 96 + (96 - nw) // 2, BASELINE - nh), small)
    strip.save(GAME / out)
    print(f"ok: {out}  {want}f (anchor mask {md}px -> {TARGET_MASK}, scale {scale:.3f})")
