"""Animation strips at Castlevania SotN parity: 96x96 canvas, ~72px figure.
Every frame is the base figure re-posed by parameters — one source of truth.
Run: python make_frames.py  ->  player_<anim>.png strips + _8x previews
"""
from PIL import Image

INK = (10, 14, 31)
BLUE_DEEP = (30, 51, 217)
BLUE_MID = (43, 111, 232)
CYAN = (53, 198, 244)
CYAN_PALE = (143, 232, 255)
RED_DARK = (143, 17, 22)
RED = (224, 31, 38)
GREEN = (198, 240, 42)
GREEN_DEEP = (107, 138, 15)
WHITE = (255, 255, 255)
GREY = (74, 85, 104)
SKIN_SH = (74, 42, 26)
SKIN = (133, 84, 52)
SKIN_LT = (176, 122, 74)

ALLOWED = {INK, BLUE_DEEP, BLUE_MID, CYAN, CYAN_PALE, RED_DARK, RED, GREEN,
           GREEN_DEEP, WHITE, GREY, SKIN_SH, SKIN, SKIN_LT}
S = 96  # canvas; feet baseline y=84; figure ~x20..x60, center ~x44


def draw_frame(px, ox, *, bob=0, lean=0, pony=(0, 0), legs="stand", hem_flare=0,
               arm="idle"):
    """bob: upper body sink. lean: head/torso x-shift (+ = lunge forward).
    pony: (dx, dy) tail sway. legs: stand|tuck|trail|stride_a|stride_b|lunge|
    stream. arm: idle|windup|strike."""

    def put(x, y, c):
        if 0 <= x < S and 0 <= y < S:
            px[ox + x, y] = (*c, 255)

    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                put(x, y, c)

    def row(y, x0, x1, c):
        rect(x0, y, x1, y, c)

    def col(x, y0, y1, c):
        rect(x, y0, x, y1, c)

    hx, hy = lean, bob
    pdx, pdy = pony

    # ---- ponytail: the character's dominant silhouette element.
    # Two overlapping bezier strands for mass, dithered color bands, taper 11->2.
    def hair_band(t, x, y):
        """indigo -> mid -> cyan -> pale, with 2px checkerboard dithering at
        each transition (the signature pixel-art gradient technique)."""
        for edge, lo, hi in ((0.30, BLUE_DEEP, BLUE_MID),
                             (0.60, BLUE_MID, CYAN),
                             (0.84, CYAN, CYAN_PALE)):
            if abs(t - edge) < 0.035:                         # tight band: texture, not noise
                return lo if (x + y) % 2 == 0 else hi
        if t < 0.30:
            return BLUE_DEEP
        if t < 0.60:
            return BLUE_MID
        return CYAN if t < 0.84 else CYAN_PALE

    def strand(x0, y0, x1, y1, x2, y2, w0, w1, steps=54):
        for i in range(steps + 1):
            t = i / steps
            u = 1 - t
            bx = round(u * u * x0 + 2 * u * t * x1 + t * t * x2)
            by = round(u * u * y0 + 2 * u * t * y1 + t * t * y2)
            wd = max(1, round(w0 + (w1 - w0) * t))
            for k in range(wd):
                gx = bx - wd // 2 + k
                rect(gx, by, gx, by + 1, hair_band(t, gx, by))
            if i % 6 == 0 and 0.15 < t < 0.9:                 # strand sheen
                put(bx + wd // 2, by, CYAN_PALE)
            if i % 9 == 4 and 0.2 < t < 0.85:                 # inner shadow line
                put(bx - wd // 2, by + 1, BLUE_DEEP)

    # main mass — flows down BEHIND the body, not around it
    strand(27 + hx, 17 + hy, 17 + hx + pdx // 2, 42 + hy + pdy // 2,
           24 + hx + pdx, 66 + hy + pdy, 7, 2)
    # secondary strand, offset and thin — splits the tip, adds depth not bulk
    strand(29 + hx, 20 + hy, 21 + hx + pdx // 2, 45 + hy + pdy // 2,
           31 + hx + pdx, 60 + hy + pdy, 3, 1)
    tx, ty = 24 + hx + pdx, 66 + hy + pdy
    for wx, wy in ((4, 2), (-3, 3), (1, 5), (6, 0), (-5, 1)):  # tip wisps
        put(tx + wx, ty + wy, CYAN_PALE)
    rect(27 + hx, 14 + hy, 30 + hx, 18 + hy, GREEN)           # tie band
    put(27 + hx, 14 + hy, GREEN_DEEP)
    put(30 + hx, 18 + hy, GREEN_DEEP)

    # ---- hair mass: crown + short nape lock, sheen streaks
    rect(29 + hx, 12 + hy, 40 + hx, 32 + hy, BLUE_DEEP)
    rect(33 + hx, 9 + hy, 45 + hx, 11 + hy, BLUE_DEEP)
    put(30 + hx, 11 + hy, BLUE_DEEP)
    rect(30 + hx, 33 + hy, 33 + hx, 38 + hy, BLUE_DEEP)       # nape lock
    put(31 + hx, 39 + hy, BLUE_MID)
    col(32 + hx, 15 + hy, 25 + hy, BLUE_MID)                  # sheen streaks
    col(36 + hx, 12 + hy, 18 + hy, BLUE_MID)
    put(38 + hx, 10 + hy, CYAN)                               # crown catch-light
    put(39 + hx, 10 + hy, CYAN)
    put(34 + hx, 28 + hy, BLUE_MID)

    # ---- horns: long, twisted, swept back
    for i, (dx, dy) in enumerate([(0, 0), (-1, 1), (-1, 2), (0, 3), (1, 4),
                                  (1, 5), (2, 6), (3, 7), (3, 8), (4, 9)]):
        c = RED_DARK if i % 3 == 2 else RED
        put(33 + dx + hx, 2 + dy + hy, c)
        put(34 + dx + hx, 2 + dy + hy, c)
    for i, (dx, dy) in enumerate([(0, 0), (-1, 1), (-1, 2), (0, 3), (0, 4),
                                  (1, 5), (2, 6), (2, 7)]):
        c = RED_DARK if i % 3 == 2 else RED
        put(41 + dx + hx, 1 + dy + hy, c)
        put(42 + dx + hx, 1 + dy + hy, c)

    # ---- full-face hannya mask (profile): organic skull contour, not a box.
    # Crown narrow -> brow ridge juts -> snout -> grin band -> jaw curves back in.
    row(10 + hy, 41 + hx, 48 + hx, RED)                       # crown
    row(11 + hy, 40 + hx, 50 + hx, RED)
    rect(39 + hx, 12 + hy, 51 + hx, 13 + hy, RED)
    rect(39 + hx, 14 + hy, 53 + hx, 15 + hy, RED)             # brow ridge juts
    put(54 + hx, 15 + hy, RED_DARK)                           # brow shadow tip
    rect(38 + hx, 16 + hy, 52 + hx, 18 + hy, RED)
    rect(38 + hx, 19 + hy, 54 + hx, 21 + hy, RED)             # snout
    put(55 + hx, 20 + hy, RED); put(55 + hx, 21 + hy, RED_DARK)  # nose tip/nostril
    rect(39 + hx, 22 + hy, 53 + hx, 23 + hy, RED)             # upper lip
    rect(40 + hx, 28 + hy, 52 + hx, 29 + hy, RED)             # lower lip
    rect(41 + hx, 30 + hy, 50 + hx, 31 + hy, RED)             # jaw curves in
    rect(44 + hx, 32 + hy, 49 + hx, 33 + hy, RED)             # chin
    put(43 + hx, 33 + hy, RED_DARK)
    # carve lines (RED_DARK): brow crease, cheek slash, jaw shade
    row(13 + hy, 43 + hx, 49 + hx, RED_DARK)
    put(42 + hx, 20 + hy, RED_DARK); put(43 + hx, 21 + hy, RED_DARK)
    put(44 + hx, 22 + hy, RED_DARK)                           # cheek carve diagonal
    row(31 + hy, 44 + hx, 48 + hx, RED_DARK)
    col(38 + hx, 16 + hy, 27 + hy, RED_DARK)                  # rim shadow
    col(37 + hx, 20 + hy, 26 + hy, CYAN_PALE)                 # ghost leak at rim
    # eye slit under the brow, glaring
    rect(44 + hx, 17 + hy, 52 + hx, 18 + hy, WHITE)
    put(43 + hx, 17 + hy, CYAN_PALE)
    put(53 + hx, 18 + hy, CYAN_PALE)
    # third eye diamond
    put(46 + hx, 11 + hy, CYAN)
    put(45 + hx, 12 + hy, CYAN); put(47 + hx, 12 + hy, CYAN)
    put(46 + hx, 12 + hy, CYAN_PALE)
    put(46 + hx, 13 + hy, CYAN)
    # grin: INK mouth cavity with true hanging + rising fangs
    rect(42 + hx, 24 + hy, 53 + hx, 27 + hy, INK)
    for fx_ in (44, 47, 50, 53):                              # upper fangs hang
        put(fx_ + hx, 24 + hy, WHITE)
        put(fx_ + hx, 25 + hy, WHITE)
    for fx_ in (45, 49, 52):                                  # lower fangs rise
        put(fx_ + hx, 27 + hy, WHITE)
        put(fx_ + hx, 26 + hy, WHITE)
    put(41 + hx, 25 + hy, CYAN_PALE)                          # spirit light in the gaps
    put(48 + hx, 26 + hy, CYAN_PALE)

    # ---- neck
    rect(41 + hx, 34 + hy, 45 + hx, 37 + hy, SKIN)
    put(41 + hx, 37 + hy, SKIN_SH)
    col(45 + hx, 34 + hy, 36 + hy, SKIN_LT)

    # ---- torso: athletic — shoulders wide, waist tapered; tracksuit under vest
    rect(37 + hx, 37 + hy, 49 + hx, 39 + hy, INK)             # collar/shoulder yoke
    put(50 + hx, 38 + hy, GREEN)                              # zip pull
    rect(36 + hx, 40 + hy, 50 + hx, 46 + hy, INK)             # chest, full width
    rect(37 + hx, 47 + hy, 49 + hx, 52 + hy, INK)             # ribs
    rect(38 + hx, 53 + hy, 48 + hx, 58 + hy, INK)             # waist taper
    for zy in range(41, 57, 3):                               # zip line
        put(43 + hx, zy + hy, GREY)

    # ---- haori: worn OPEN over the chest — two white vest panels, black center
    # (canon-sheet construction: white masses on both sides, suit shows between)
    rect(30 + hx, 37 + hy, 37 + hx, 60 + hy, WHITE)           # back/far panel
    for fy in range(39, 59, 4):
        put(30 + hx, fy + hy, GREY)                           # fold shadows
        put(33 + hx, fy + 2 + hy, GREY)
    col(37 + hx, 40 + hy, 58 + hy, CYAN_PALE)                 # inner-edge tint
    rect(46 + hx, 38 + hy, 51 + hx, 58 + hy, WHITE)           # near/front panel
    col(46 + hx, 40 + hy, 56 + hy, CYAN_PALE)                 # inner edge
    put(49 + hx, 43 + hy, GREY); put(48 + hx, 49 + hy, GREY)  # drape folds
    put(50 + hx, 54 + hy, GREY)
    put(51 + hx, 59 + hy, WHITE); put(47 + hx, 59 + hy, WHITE)  # panel hem tears

    # ---- arm
    if arm == "idle":
        rect(45 + hx, 40 + hy, 49 + hx, 47 + hy, INK)
        col(48 + hx, 41 + hy, 46 + hy, GREEN)                 # racing stripes
        col(49 + hx, 41 + hy, 46 + hy, CYAN)
        rect(45 + hx, 48 + hy, 49 + hx, 49 + hy, BLUE_DEEP)   # elbow cuff
        rect(45 + hx, 50 + hy, 48 + hx, 56 + hy, SKIN)        # bare forearm
        col(48 + hx, 50 + hy, 54 + hy, SKIN_LT)
        put(45 + hx, 55 + hy, SKIN_SH)
        rect(45 + hx, 57 + hy, 48 + hx, 60 + hy, SKIN)        # hand
        row(60 + hy, 45 + hx, 47 + hx, SKIN_SH)
        put(48 + hx, 57 + hy, SKIN_LT)                        # knuckle
    elif arm == "windup":                                     # blade cocked behind
        rect(43 + hx, 40 + hy, 46 + hx, 44 + hy, INK)
        rect(40 + hx, 38 + hy, 43 + hx, 40 + hy, BLUE_DEEP)
        rect(37 + hx, 31 + hy, 40 + hx, 37 + hy, SKIN)        # raised forearm
        rect(36 + hx, 29 + hy, 38 + hx, 31 + hy, SKIN_LT)     # fist by the ear
        for i in range(8):                                     # blade back-up
            put(35 - i + hx, 28 - i + hy, GREY)
            put(34 - i + hx, 28 - i + hy, GREY)
        put(26 + hx, 19 + hy, GREEN)                          # hamon tip
        put(25 + hx, 18 + hy, GREEN)
    else:                                                     # strike — full extension
        rect(46 + hx, 40 + hy, 51 + hx, 44 + hy, INK)
        put(50 + hx, 45 + hy, BLUE_DEEP)
        rect(52 + hx, 41 + hy, 57 + hx, 44 + hy, SKIN)
        col(57 + hx, 41 + hy, 43 + hy, SKIN_LT)
        rect(58 + hx, 41 + hy, 60 + hx, 44 + hy, SKIN)        # hand
        col(61 + hx, 40 + hy, 45 + hy, GREY)                  # tsuba
        row(42 + hy, 62 + hx, 88 + hx, GREY)                  # blade
        row(43 + hy, 62 + hx, 88 + hx, GREEN)                 # hamon edge
        put(89 + hx, 42 + hy, WHITE)                          # tip glint

    # ---- obi with knot
    rect(33 + hx, 58 + hy, 50 + hx, 62 + hy, BLUE_DEEP)
    row(60 + hy, 37 + hx, 48 + hx, GREEN)
    rect(34 + hx, 60 + hy, 36 + hx, 63 + hy, BLUE_MID)        # knot


    # ---- haori skirt: broad, billow-waved edge, ragged hem
    f = hem_flare
    rect(28 + hx - f, 61 + hy, 37 + hx, 76 + hy - f, WHITE)
    for wy in range(62 + hy, 76 + hy - f):
        if wy % 3 != 0:
            put(27 + hx - f, wy, WHITE)
        if wy % 4 == 1:
            put(26 + hx - f, wy, WHITE)
        if wy % 5 == 2:
            put(31 + hx - f // 2, wy, GREY)                   # inner fold
    put(30 + hx - f, 77 + hy - f, WHITE)                      # ragged tears
    put(33 + hx, 77 + hy - f, WHITE)
    put(31 + hx - f, 78 + hy - f, WHITE)
    put(35 + hx, 78 + hy - f, WHITE)
    put(34 + hx, 79 + hy - f, WHITE)
    col(37 + hx, 63 + hy, 75 + hy - f, GREY)                  # hem shade edge

    # ---- daisho: near-horizontal behind the waist (canon idle silhouette) —
    # both scabbards thrust through the obi, poking back-left at a shallow slope
    rect(33 + hx, 56 + hy, 35 + hx, 60 + hy, GREY)            # katana tsuba
    for i in range(19):                                        # katana: slope 1:4, 3px thick
        put(32 - i + hx, 56 + i // 4 + hy, INK)
        put(32 - i + hx, 57 + i // 4 + hy, INK)
        put(32 - i + hx, 58 + i // 4 + hy, INK)
    rect(12 + hx, 60 + hy, 13 + hx, 62 + hy, GREEN)           # scabbard tip glow
    rect(35 + hx, 61 + hy, 36 + hx, 63 + hy, GREY)            # wakizashi tsuba
    for i in range(13):                                        # wakizashi: slope 1:3, 3px thick
        put(34 - i + hx, 62 + i // 3 + hy, INK)
        put(34 - i + hx, 63 + i // 3 + hy, INK)
        put(34 - i + hx, 64 + i // 3 + hy, INK)
    rect(20 + hx, 66 + hy, 21 + hx, 67 + hy, GREEN)

    # ---- legs + boots
    if legs == "stand":
        rect(36, 62 + hy, 39, 75, INK)                        # back leg
        rect(40, 62 + hy, 46, 75, INK)                        # front leg
        col(44, 63 + hy, 74, GREEN_DEEP)
        put(44, 68, GREEN); put(44, 69, GREEN)
        col(46, 63 + hy, 74, GREY)                            # front highlight
        rect(39, 76, 46, 78, BLUE_DEEP)                       # ankle cuff
        rect(39, 79, 47, 81, INK)
        put(48, 81, INK)
        rect(39, 82, 48, 83, INK)
        put(38, 81, CYAN_PALE)                                # heel rim light
        row(84, 39, 48, GREY)
    elif legs == "tuck":
        rect(38, 62 + hy, 47, 67, INK)
        put(44, 63, GREEN_DEEP); put(45, 64, GREEN_DEEP)
        rect(34, 68, 44, 71, INK)
        rect(33, 71, 39, 73, BLUE_DEEP)
        rect(31, 74, 38, 76, INK)
        put(30, 75, CYAN_PALE)
        row(77, 31, 38, GREY)
    elif legs == "trail":
        rect(40, 62 + hy, 45, 68, INK)
        col(44, 63, 67, GREEN_DEEP)
        rect(43, 69, 46, 75, INK)                             # front shin down
        rect(43, 76, 49, 78, INK)
        row(79, 43, 49, GREY)
        rect(34, 64, 38, 69, INK)                             # back leg trails
        rect(31, 70, 34, 73, INK)
        rect(29, 73, 33, 75, BLUE_DEEP)
        rect(26, 76, 32, 78, INK)
        put(25, 77, CYAN_PALE)
    elif legs == "stride_a":
        rect(32, 62 + hy, 36, 74, INK)                        # back leg
        rect(31, 75, 35, 77, BLUE_DEEP)
        rect(29, 78, 35, 80, INK)
        row(81, 29, 35, GREY)
        put(28, 79, CYAN_PALE)
        rect(43, 62 + hy, 47, 74, INK)                        # front leg leads
        col(46, 63, 73, GREEN_DEEP)
        put(46, 68, GREEN)
        rect(43, 75, 47, 77, BLUE_DEEP)
        rect(43, 78, 51, 80, INK)
        row(81, 43, 51, GREY)
    elif legs == "stride_b":
        rect(43, 62 + hy, 46, 74, INK)                        # back (was front)
        rect(42, 75, 46, 77, BLUE_DEEP)
        rect(42, 78, 49, 80, INK)
        row(81, 42, 49, GREY)
        rect(35, 62 + hy, 39, 74, INK)                        # front (was back)
        col(38, 63, 73, GREEN_DEEP)
        put(38, 68, GREEN)
        rect(34, 75, 38, 77, BLUE_DEEP)
        rect(32, 78, 39, 80, INK)
        row(81, 32, 39, GREY)
        put(31, 79, CYAN_PALE)
    elif legs == "lunge":
        rect(43, 62 + hy, 49, 68, INK)                        # front thigh drives
        put(47, 64, GREEN_DEEP); put(48, 65, GREEN_DEEP)
        rect(47, 68, 51, 75, INK)                             # front shin
        rect(47, 76, 51, 78, BLUE_DEEP)
        rect(46, 79, 53, 81, INK)                             # planted boot
        row(82, 46, 53, GREY)
        rect(32, 63 + hy, 38, 66, INK)                        # back leg extends
        rect(26, 66, 33, 69, INK)
        rect(23, 69, 27, 71, BLUE_DEEP)
        rect(19, 72, 24, 74, INK)                             # back boot on toe
        put(18, 73, CYAN_PALE)
    elif legs == "pass_a":                                    # run pass: legs crossing, back toe drags
        rect(40, 62 + hy, 45, 75, INK)                        # front leg vertical
        col(44, 63 + hy, 74, GREEN_DEEP)
        rect(39, 76, 45, 78, BLUE_DEEP)
        rect(39, 79, 46, 81, INK)
        rect(39, 82, 46, 83, INK)
        row(84, 39, 46, GREY)
        rect(35, 64 + hy, 38, 76, INK)                        # back leg trailing, toe down
        rect(34, 77, 37, 79, BLUE_DEEP)
        rect(33, 80, 37, 82, INK)                             # toe drag
        put(32, 82, CYAN_PALE)
    elif legs == "pass_b":                                    # mirrored pass
        rect(37, 62 + hy, 42, 75, INK)
        col(41, 63 + hy, 74, GREEN_DEEP)
        rect(36, 76, 42, 78, BLUE_DEEP)
        rect(36, 79, 43, 81, INK)
        rect(36, 82, 43, 83, INK)
        row(84, 36, 43, GREY)
        rect(44, 64 + hy, 47, 76, INK)
        rect(44, 77, 48, 79, BLUE_DEEP)
        rect(45, 80, 49, 82, INK)
        put(50, 82, CYAN_PALE)
    elif legs == "crouch":                                    # folded double, feet planted
        rect(34, 72 + hy, 49, 76 + hy, INK)                   # thighs horizontal
        put(46, 73 + hy, GREEN_DEEP); put(47, 74 + hy, GREEN_DEEP)
        rect(42, 76 + hy, 47, 79, INK)                        # shins vertical
        rect(38, 78, 48, 79, BLUE_DEEP)                       # cuffs pooled
        rect(37, 80, 49, 81, INK)                             # boots
        rect(37, 82, 49, 83, INK)
        put(36, 81, CYAN_PALE)
        row(84, 37, 49, GREY)
    else:                                                     # stream — dash
        rect(28, 64 + hy, 38, 69 + hy, INK)                   # thighs sweep back
        put(35, 66 + hy, GREEN_DEEP); put(34, 67 + hy, GREEN_DEEP)
        rect(18, 66 + hy, 29, 70 + hy, INK)                   # shins trail
        rect(15, 67 + hy, 20, 71 + hy, BLUE_DEEP)
        rect(8, 68 + hy, 16, 72 + hy, INK)                    # boots streaming
        put(7, 70 + hy, CYAN_PALE)
        row(73 + hy, 10, 14, GREY)


ANIMS = {
    # idle: SotN-count breathing loop with ponytail overshoot
    "idle": [dict(bob=0, pony=(0, 0)), dict(bob=0, pony=(0, 0)),
             dict(bob=1, pony=(-1, 1)), dict(bob=2, pony=(-3, 3)),
             dict(bob=2, pony=(-3, 4)), dict(bob=1, pony=(-2, 3)),
             dict(bob=0, pony=(-1, 1)), dict(bob=0, pony=(0, 0))],
    # run: full 8-frame gait — contact / down / pass / up, both sides
    "run": [dict(legs="stride_a", bob=0, pony=(-6, 0), hem_flare=1),
            dict(legs="stride_a", bob=2, pony=(-6, 1), hem_flare=2),
            dict(legs="pass_a", bob=1, pony=(-7, 2), hem_flare=2),
            dict(legs="stand", bob=0, pony=(-7, 0), hem_flare=1),
            dict(legs="stride_b", bob=0, pony=(-6, 0), hem_flare=1),
            dict(legs="stride_b", bob=2, pony=(-6, 1), hem_flare=2),
            dict(legs="pass_b", bob=1, pony=(-7, 2), hem_flare=2),
            dict(legs="stand", bob=0, pony=(-7, 0), hem_flare=1)],
    # jump (no loop): launch -> rise -> apex (hair catches up) -> late
    "jump": [dict(legs="stand", bob=-3, pony=(2, 6), hem_flare=0),
             dict(legs="tuck", bob=0, pony=(-3, 6), hem_flare=2),
             dict(legs="tuck", bob=1, pony=(-2, 3), hem_flare=2),
             dict(legs="tuck", bob=0, pony=(-4, 10), hem_flare=3)],
    # fall: legs trail, hair streams up, hem flutters
    "fall": [dict(legs="trail", pony=(-5, -5), hem_flare=3),
             dict(legs="trail", pony=(-7, -9), hem_flare=4),
             dict(legs="trail", pony=(-7, -11), hem_flare=3)],
    # land (no loop): squash then recover
    "land": [dict(legs="stand", bob=4, pony=(2, 4), hem_flare=2),
             dict(legs="stand", bob=2, pony=(0, 2), hem_flare=0)],
    # hurt: recoil, ponytail thrown forward
    "hurt": [dict(lean=-4, bob=2, pony=(6, -4), legs="stand"),
             dict(lean=-2, bob=0, pony=(4, -2), legs="stand")],
    # attack (no loop): SotN 6-frame — cock, deep cock, cut, hold, recover, settle
    "attack": [dict(lean=-2, bob=0, pony=(4, 0), legs="stand", arm="windup"),
               dict(lean=-3, bob=1, pony=(5, 1), legs="stand", arm="windup", hem_flare=1),
               dict(lean=6, bob=2, pony=(-7, -2), legs="lunge", arm="strike", hem_flare=3),
               dict(lean=5, bob=2, pony=(-8, 0), legs="lunge", arm="strike", hem_flare=2),
               dict(lean=2, bob=1, pony=(-4, 2), legs="lunge", arm="idle", hem_flare=1),
               dict(lean=0, bob=1, pony=(-2, 3), legs="stand", arm="idle", hem_flare=1)],
    # dash: pitched horizontal, legs streaming, hair a flat line
    "dash": [dict(lean=12, bob=6, pony=(-12, -18), legs="stream", hem_flare=4),
             dict(lean=13, bob=6, pony=(-13, -19), legs="stream", hem_flare=4)],
    # crouch: sunk low, ponytail settles high behind (SotN duck)
    "crouch": [dict(bob=10, legs="crouch", pony=(3, -8), hem_flare=1),
               dict(bob=11, legs="crouch", pony=(2, -7), hem_flare=1)],
}


def draw_turn(px, ox, phase):
    """SotN turn-around transition: near-frontal, mask edge-on, hair wrapping.
    phase 0 = mostly frontal, phase 1 = committing to the new direction."""

    def put(x, y, c):
        if 0 <= x < S and 0 <= y < S:
            px[ox + x, y] = (*c, 255)

    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                put(x, y, c)

    def row(y, x0, x1, c):
        rect(x0, y, x1, y, c)

    sh = phase * 2                                            # slide into the turn
    # hair wraps the head, ponytail swings wide across the back
    rect(34 + sh, 10, 47 + sh, 32, BLUE_DEEP)
    rect(36 + sh, 7, 45 + sh, 9, BLUE_DEEP)
    rect(31 + sh, 14, 33 + sh, 30, BLUE_MID)                  # swing blur
    rect(27 + sh, 18, 30 + sh, 40, BLUE_MID)
    rect(25 + sh, 36, 28 + sh, 52, CYAN)
    rect(26 + sh, 50, 28 + sh, 58, CYAN_PALE)
    # horns near-frontal: both visible, short
    put(37 + sh, 4, RED); put(37 + sh, 5, RED); put(36 + sh, 3, RED)
    put(44 + sh, 4, RED); put(44 + sh, 5, RED); put(45 + sh, 3, RED)
    # mask edge-on: thin red sliver + one eye slit catching light
    rect(46 + sh, 13, 48 + sh, 31, RED)
    put(48 + sh, 17, RED_DARK)
    put(47 + sh, 19, WHITE); put(48 + sh, 19, WHITE)          # eye sliver
    put(46 + sh, 26, WHITE)                                   # fang glint
    put(46 + sh, 11, CYAN)                                    # third eye edge-on
    # neck + torso near-frontal, both haori edges visible
    rect(40 + sh, 33, 44 + sh, 37, SKIN)
    rect(37 + sh, 37, 46 + sh, 39, INK)
    rect(36 + sh, 40, 47 + sh, 57, INK)
    put(41 + sh, 44, GREY); put(41 + sh, 50, GREY)            # zip center
    rect(33 + sh, 38, 35 + sh, 58, WHITE)                     # left haori edge
    rect(48 + sh, 38, 50 + sh, 58, WHITE)                     # right haori edge
    put(33 + sh, 44, GREY); put(50 + sh, 48, GREY)
    # arms held in at the sides
    rect(34 + sh, 40, 35 + sh, 48, INK)
    rect(48 + sh, 40, 49 + sh, 48, INK)
    rect(34 + sh, 49, 35 + sh, 55, SKIN)
    rect(48 + sh, 49, 49 + sh, 55, SKIN)
    # obi + skirt frontal
    rect(34 + sh, 58, 49 + sh, 62, BLUE_DEEP)
    row(60, 37 + sh, 46 + sh, GREEN)
    rect(33 + sh, 63, 37 + sh, 76, WHITE)
    rect(46 + sh, 63, 50 + sh, 76, WHITE)
    put(34 + sh, 77, WHITE); put(48 + sh, 77, WHITE)          # ragged hem
    put(36 + sh, 78, WHITE); put(47 + sh, 78, WHITE)
    # legs frontal
    rect(37 + sh, 63, 41 + sh, 75, INK)
    rect(42 + sh, 63, 46 + sh, 75, INK)
    put(41 + sh, 68, GREEN_DEEP); put(42 + sh, 68, GREEN_DEEP)
    rect(37 + sh, 76, 41 + sh, 78, BLUE_DEEP)
    rect(42 + sh, 76, 46 + sh, 78, BLUE_DEEP)
    rect(36 + sh, 79, 41 + sh, 83, INK)
    rect(42 + sh, 79, 47 + sh, 83, INK)
    row(84, 36 + sh, 47 + sh, GREY)

# auto-detail pass: what reads as "hand-drawn" is contour + edge lighting +
# material separation. Applied per-pixel to every frame — one algorithm, all anims.
LIGHT = {BLUE_DEEP: BLUE_MID, BLUE_MID: CYAN, CYAN: CYAN_PALE, INK: GREY,
         SKIN: SKIN_LT, SKIN_SH: SKIN, RED_DARK: RED, GREY: CYAN_PALE}
SHADE = {WHITE: CYAN_PALE, CYAN_PALE: CYAN, BLUE_MID: BLUE_DEEP, CYAN: BLUE_MID,
         SKIN: SKIN_SH, SKIN_LT: SKIN, RED: RED_DARK, GREY: INK,
         GREEN: GREEN_DEEP, BLUE_DEEP: INK}
# materials that should be visually separated where they overlap
FAMILY = {INK: 'cloth_dark', GREY: 'cloth_dark',
          WHITE: 'cloth_light', CYAN_PALE: 'cloth_light',
          BLUE_DEEP: 'hair', BLUE_MID: 'hair', CYAN: 'hair',
          SKIN: 'skin', SKIN_LT: 'skin', SKIN_SH: 'skin',
          RED: 'mask', RED_DARK: 'mask',
          GREEN: 'energy', GREEN_DEEP: 'energy'}


def detail_pass(img):
    px = img.load()
    w, h = img.size
    orig = [[px[x, y] for y in range(h)] for x in range(w)]

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and orig[x][y][3] > 0

    def fam(x, y):
        if not solid(x, y):
            return None
        return FAMILY.get(orig[x][y][:3])

    for x in range(w):
        for y in range(h):
            if orig[x][y][3] > 0:
                c = orig[x][y][:3]
                above, below = fam(x, y - 1), fam(x, y + 1)
                me = FAMILY.get(c)
                if not solid(x, y - 1) and c in LIGHT:        # lit top edge
                    px[x, y] = (*LIGHT[c], 255)
                elif above is not None and above != me and c in SHADE:
                    px[x, y] = (*SHADE[c], 255)               # material seam
                elif not solid(x, y + 1) and c in SHADE:      # shaded bottom edge
                    px[x, y] = (*SHADE[c], 255)
                elif below is not None and below != me and c in LIGHT:
                    px[x, y] = (*LIGHT[c], 255)               # lit over a seam
            else:
                if (solid(x - 1, y) or solid(x + 1, y)
                        or solid(x, y - 1) or solid(x, y + 1)):
                    px[x, y] = (*INK, 255)                    # dark contour outline


def export(name, count, painter):
    strip = Image.new("RGBA", (S * count, S), (0, 0, 0, 0))
    px = strip.load()
    for i in range(count):
        painter(px, i * S, i)
    detail_pass(strip)
    # palette gate BEFORE save — a failing build must not leave bad PNGs on disk
    used = {px[x, y][:3] for x in range(strip.width) for y in range(S) if px[x, y][3] > 0}
    bad = used - ALLOWED
    assert not bad, f"{name}: off-palette {bad}"
    strip.save(f"player_{name}.png")
    strip.resize((strip.width * 8, S * 8), Image.NEAREST).save(f"player_{name}_8x.png")
    print(f"ok: player_{name}.png  {count}f  {strip.width}x{S}")


for name, frames in ANIMS.items():
    export(name, len(frames), lambda px, ox, i, fr=frames: draw_frame(px, ox, **fr[i]))
export("turn", 3, lambda px, ox, i: draw_turn(px, ox, i))
