"""Assemble game animation strips from sliced canon poses (canon_frames/).

Mapping decided by eye against the sheet's rows:
  row0 c0-6   idle          row2 c0-2  jump    row3 c0-2  dash
  row1 c0-7   run           row2 c3-4  fall    row3 c3    crouch
                            row2 c5-8  attack  row3 c3-4  land (squash->stand)
                                               row3 c5-6  hurt
                                               row3 c7-9  death (new)
Also strips the sheet's leftover ground-line rows near the baseline.
Run: python assemble_strips.py
"""
from PIL import Image
import pathlib

SRC = pathlib.Path("canon_frames")
GAME = pathlib.Path("../../game/art/player")

MAP = {
    "idle":   [("r0", i) for i in range(7)],
    "run":    [("r1", i) for i in range(8)],
    "jump":   [("r2", 0), ("r2", 1), ("r2", 2)],
    "fall":   [("r2", 3), ("r2", 4)],
    "attack": [("r2", 5), ("r2", 6), ("r2", 7), ("r2", 8)],
    "dash":   [("r3", 0), ("r3", 1), ("r3", 2)],
    "crouch": [("r3", 3)],
    "land":   [("r3", 3), ("r3", 4)],
    "hurt":   [("r3", 5), ("r3", 6)],
    "death":  [("r3", 7), ("r3", 8), ("r3", 9)],
}

DARKS = {(10, 14, 31), (74, 85, 104)}


def clean_groundline(img):
    """The sheet's ground line survives as a wide flat dark run near the
    baseline — erase any near-baseline row that is a long dark horizontal."""
    px = img.load()
    for y in range(80, 96):
        run, best = 0, 0
        for x in range(96):
            if px[x, y][3] > 0 and px[x, y][:3] in DARKS:
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= 24:
            for x in range(96):
                if px[x, y][3] > 0 and px[x, y][:3] in DARKS:
                    px[x, y] = (0, 0, 0, 0)
    return img


def clean_gridline_vertical(img):
    """A baked-in cell divider is a THIN dark column standing in empty space.
    The character's own black suit is also a tall dark column, so require
    isolation: mostly-empty gutters a few px to each side."""
    px = img.load()

    def empty_frac(xx):
        if not (0 <= xx < 96):
            return 1.0
        return sum(1 for y in range(96) if px[xx, y][3] == 0) / 96.0

    for x in range(96):
        dark = sum(1 for y in range(96)
                   if px[x, y][3] > 0 and px[x, y][:3] in DARKS)
        if dark >= 70 and empty_frac(x - 3) > 0.8 and empty_frac(x + 3) > 0.8:
            left = sum(1 for xx in range(0, x - 1) for y in range(96) if px[xx, y][3] > 0)
            right = sum(1 for xx in range(x + 2, 96) for y in range(96) if px[xx, y][3] > 0)
            lo, hi = (0, x + 1) if left < right else (x, 96)
            for xx in range(lo, hi):
                for y in range(96):
                    px[xx, y] = (0, 0, 0, 0)
            break
    return img


for name, frames in MAP.items():
    strip = Image.new("RGBA", (96 * len(frames), 96), (0, 0, 0, 0))
    for i, (row, ci) in enumerate(frames):
        f = clean_groundline(Image.open(SRC / f"pose_{row[0]}{row[1:]}c{ci}.png").convert("RGBA"))
        f = clean_gridline_vertical(f)
        strip.paste(f, (i * 96, 0))
    strip.save(f"player_{name}.png")
    strip.resize((strip.width * 8, 768), Image.NEAREST).save(f"player_{name}_8x.png")
    strip.save(GAME / f"player_{name}.png")
    print(f"ok: player_{name}.png  {len(frames)}f")
print("done — turn stays procedural (no canon source)")
