"""Assemble the game's animation strips from the sliced sheets.

CORE animations all come from sheet_mega (sheet_frames/sheet_mega_00..29): one
6x5 generation holding idle/run/jump/fall/attack/reactions, so the character's
proportions are consistent across every core move BY CONSTRUCTION — the fix for
the body-size drift that per-sheet scaling could never solve.

  mega 00-05 idle | 06-11 run | 12-17 jump cycle | 18-23 katana attack
  mega 24 crouch, 25 dash, 26 hurt, 27 fall-defeated, 28 prone, 29 pray

SPECIALTY moves (attack_up/down, heavy, air_attack, parry, cast, turn)
have no mega cell yet and stay on the older themed sheets. Their bodies are
normalized to the same 76px figure height; their heads run ~16px vs mega's 19px
— a known, deliberate residual until a second mega-style sheet covers them.

Run: python assemble_v2.py
"""
from PIL import Image
import pathlib

SH = pathlib.Path("sheet_frames")
GAME = pathlib.Path("../../game/art/player")

M = "sheet_mega_%02d.png"
L = "sheet_locomotion_%02d.png"
C = "sheet_combat_%02d.png"

MAP = {
    # --- core: single-generation mega sheet, proportion-consistent
    "idle":   [(SH, M % i) for i in range(0, 6)],
    "run":    [(SH, M % i) for i in range(6, 12)],
    # light: starts at the TRAVEL frame so the cut visibly extends forward at
    # once — the cocked/windup cells made it read as a swing that never left
    "attack": [(SH, M % i) for i in (20, 22, 23)],
    # heavy (SIGKILL): the full drama — windup, peak, the crescent-arc cell,
    # extension, recovery. Mega cells so proportions match every other anim;
    # the old combat-sheet frames popped visually and clipped the blade.
    "heavy":  [(SH, M % i) for i in (18, 19, 21, 22, 23)],
    "jump":   [(SH, M % i) for i in (12, 13, 14, 15)],   # coil..apex
    "fall":   [(SH, M % 16)],
    "land":   [(SH, M % 17), (SH, M % 17)],
    "crouch": [(SH, M % 24)],
    "dash":   [(SH, M % 25)],
    "hurt":   [(SH, M % 26)],
    "death":  [(SH, M % i) for i in (27, 28, 28)],
    "pray":   [(SH, M % 29)],
    "double_jump": [(SH, M % 14)],                       # rising tuck
    # --- specialty: no mega cell yet, older sheets
    "attack_up":  [(SH, C % i) for i in (0, 4, 3)],
    "attack_down": [(SH, C % i) for i in (0, 5, 3)],
    "air_attack": [(SH, C % 8)],
    "parry":      [(SH, C % 9)],
    "cast":       [(SH, C % 11)],
    "turn":       [(SH, L % i) for i in (10, 11, 12)],      # alert / turn / walk
}


def load(base, fname):
    p = base / fname
    if not p.exists():
        raise SystemExit(f"missing source frame: {p}")
    return Image.open(p).convert("RGBA")


# anchor-match hook for strips whose head genuinely measures off-median.
# Empty today: air_attack briefly lived here on a 13px reading that turned out
# to be anchor-colour coverage, not a small head — with the full crimson range
# in the anchor list it measures 16px, already in parity. Measure with the
# extended anchors before ever adding an entry.
RESCALE = {}

for name, frames in MAP.items():
    strip = Image.new("RGBA", (96 * len(frames), 96), (0, 0, 0, 0))
    for i, (base, fname) in enumerate(frames):
        fr = load(base, fname)
        s = RESCALE.get(name)
        if s:
            box = fr.getbbox()
            fig = fr.crop(box)
            nw, nh = round(fig.width * s), round(fig.height * s)
            fig = fig.resize((nw, nh), Image.NEAREST)
            fr = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
            # keep the feet where they were: scaled bottom = source bottom
            fr.paste(fig, ((96 - nw) // 2, max(0, box[3] - nh)))
        strip.paste(fr, (i * 96, 0))
    strip.save(f"player_{name}.png")
    strip.resize((strip.width * 6, 576), Image.NEAREST).save(f"player_{name}_6x.png")
    strip.save(GAME / f"player_{name}.png")
    print(f"ok: player_{name}.png  {len(frames)}f")

# bonus: the bare energy bolt from the combat sheet -> a projectile VFX
bolt = load(SH, C % 12)
bolt.save("../effects/bolt.png")
bolt.save("../../game/art/effects/bolt.png")
print("ok: effects/bolt.png  1f")
