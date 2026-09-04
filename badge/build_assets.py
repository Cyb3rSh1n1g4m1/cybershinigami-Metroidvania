"""Build the badge app's assets from the game's real sprites.

Target: GitHub Universe 2025 badge (Pimoroni Tufty 2350) — 160x120 logical
pixels, 512kB SRAM, MicroPython `badgeware`. Everything is downscaled from the
Godot strips, packed into sprite sheets, and saved as PALETTED PNGs (1 byte per
pixel on the badge instead of 4).

  player.png   6 cols x 7 rows of 40x40 — every verb, indices in PLAYER below
  worm.png     6 x 32x32     drone.png  6 x 24x24
  crescent.png 4 x 32x32     soul.png   4 x 12x12    dust.png 5 x 48x24
  bg_far.png / bg_mid.png    parallax city strips
  logo.png     the hannya, 46x60        icon.png  24x24 launcher icon

Run: python build_assets.py   (from D:/Projects/Cybershinigami/badge)
"""
import pathlib

from PIL import Image

GAME = pathlib.Path("../game/art")
OUT = pathlib.Path("apps/cybershinigami/assets")
OUT.mkdir(parents=True, exist_ok=True)

CELL_SRC, CELL = 96, 40                       # 96px game cells -> 40px badge cells
SCALE = CELL / CELL_SRC

# strip name -> which SOURCE frames to keep, in sheet order. Measured on the
# hardware: an app starts with ~151KB of heap and a single 67KB allocation
# already fails from fragmentation, so this is the runner's frame set only —
# 23 frames, 38KB paletted. Index = running position across this list.
PLAYER = [
    ("run", [0, 1, 3, 4]), ("attack", [0, 1]), ("jump", [0, 2]),
    ("fall", [0]), ("dash", [0]), ("heavy", [0, 2]), ("double_jump", [0]),
    ("hurt", [0]), ("death", [0]), ("iai", [0, 2]), ("land", [0]),
]
COLS = 6


def shrink(img, w, h):
    """Area-average downscale with edge padding + hard alpha (the recipe from
    slice_iai.py): NEAREST at 2.4:1 drops the 1px outlines pixel art needs."""
    img = img.convert("RGBA").copy()
    px = img.load()
    iw, ih = img.size
    for _ in range(2):
        grown = []
        for x in range(iw):
            for y in range(ih):
                if px[x, y][3] == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < iw and 0 <= ny < ih and px[nx, ny][3] > 0:
                            c = px[nx, ny]
                            grown.append((x, y, (c[0], c[1], c[2], 1)))
                            break
        for x, y, c in grown:
            px[x, y] = c
    rgb = img.convert("RGB").resize((w, h), Image.BOX)
    a = img.split()[3].resize((w, h), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = rgb.convert("RGBA")
    out.putalpha(a)
    return out


def palettize(img, colors=64):
    """RGBA -> paletted PNG with transparency (index-based tRNS)."""
    return img.convert("RGBA").quantize(colors=colors, method=Image.Quantize.FASTOCTREE)


def save(name, img):
    p = palettize(img)
    p.save(OUT / name, optimize=True)
    print(f"ok: {name:14s} {img.size[0]}x{img.size[1]}  {(OUT / name).stat().st_size // 1024}KB")


# -- player sheet --------------------------------------------------------------
total = sum(len(fr) for _, fr in PLAYER)
rows = (total + COLS - 1) // COLS
sheet = Image.new("RGBA", (COLS * CELL, rows * CELL), (0, 0, 0, 0))
i = 0
index = {}
for name, frames in PLAYER:
    strip = Image.open(GAME / "player" / f"player_{name}.png").convert("RGBA")
    index[name] = (i, len(frames))
    for f in frames:
        cell = strip.crop((f * CELL_SRC, 0, (f + 1) * CELL_SRC, CELL_SRC))
        small = shrink(cell, CELL, CELL)
        sheet.paste(small, ((i % COLS) * CELL, (i // COLS) * CELL), small)
        i += 1
save("player.png", sheet)
print("player index:", index, "rows:", rows)


# -- enemies / effects ---------------------------------------------------------
def strip_sheet(src, src_cell, dst_cell, count, name, keep=None):
    strip = Image.open(src).convert("RGBA")
    keep = list(range(count)) if keep is None else keep
    out = Image.new("RGBA", (dst_cell * len(keep), dst_cell), (0, 0, 0, 0))
    for i, f in enumerate(keep):
        cell = strip.crop((f * src_cell, 0, (f + 1) * src_cell, strip.height))
        small = shrink(cell, dst_cell, dst_cell)
        out.paste(small, (i * dst_cell, 0), small)
    save(name, out)


strip_sheet(GAME / "enemies/worm.png", 64, 32, 6, "worm.png", keep=[0, 2, 3, 5])
strip_sheet(GAME / "enemies/drone.png", 48, 24, 6, "drone.png", keep=[0, 2, 4])
strip_sheet(GAME / "effects/crescent.png", 64, 32, 4, "crescent.png")
strip_sheet(GAME / "effects/soul.png", 24, 12, 4, "soul.png")
for stale in ("dust.png",):                # dropped: 5.8KB the heap needs more
    if (OUT / stale).exists():
        (OUT / stale).unlink()
        print(f"removed {stale}")

# -- the city: ONE strip. Two layers cost 106KB on a ~151KB heap; one 60px-tall
# strip is 19KB and still scrolls. (bg_mid is the more detailed layer.)
mid = Image.open(GAME / "bg/bg_mid.png").convert("RGBA")
k = 45 / mid.height                          # 240x45 = 10.8KB; wider than the screen, so it wraps
save("bg_far.png", mid.resize((240, 45), Image.BOX))
for stale in ("bg_mid.png",):
    p = OUT / stale
    if p.exists():
        p.unlink()
        print(f"removed {stale}")

# -- logo + icon ---------------------------------------------------------------
logo = Image.open(GAME / "ui/logo.png").convert("RGBA")
save("logo.png", logo.resize((57, 75), Image.LANCZOS))   # 229x300 at the title's 0.25x

# the game's title backdrop (640x360 art), cropped to 4:3 and scaled to the
# badge: the same torii / city / ghost-figure plate the real title sits on
art = Image.open(GAME / "ui/title_art.png").convert("RGBA")
save("title_bg.png", art.crop((80, 0, 560, 360)).resize((160, 120), Image.BOX))
# icon: the mask's face, cropped from the logo's centre, on the badge's 24x24
face = logo.crop((40, 60, 190, 210)).resize((24, 24), Image.LANCZOS)
palettize(face).save(pathlib.Path("apps/cybershinigami/icon.png"), optimize=True)
print("ok: icon.png 24x24")
