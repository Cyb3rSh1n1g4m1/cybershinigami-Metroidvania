"""
Cybershinigami - enemy sprite generator.

Builds four enemy sprite strips, side view facing RIGHT, transparent RGBA:
    worm.png      4f  64x48  segmented mechanical serpent
    drone.png     4f  48x48  hovering surveillance drone "Keylogger"
    husk.png      4f  64x64  shambling humanoid "Botnet Node"
    guardian.png  4f  96x96  armored elite "Zero-Day"

Style: flat cel-shaded pixel art, hard edges, no AA, no gradients.
Every sprite gets a 1px INK contour around its silhouette (auto outline pass).
Top-facing edges lighter, bottom-facing edges darker.
GREEN = corruption / energy, CYAN = spirit-data-tech, RED = oni material,
WHITE = cloth / bone mask.

Run:  python make_enemies.py
"""

from PIL import Image
import math

# ----------------------------------------------------------------- palette
VOID       = (0, 0, 0)
INK        = (10, 14, 31)
BLUE_DEEP  = (30, 51, 217)
BLUE_MID   = (43, 111, 232)
CYAN       = (53, 198, 244)
CYAN_PALE  = (143, 232, 255)
RED_DARK   = (143, 17, 22)
RED        = (224, 31, 38)
GREEN      = (198, 240, 42)
GREEN_DEEP = (107, 138, 15)
WHITE      = (255, 255, 255)
GREY       = (74, 85, 104)
SKIN_SH    = (74, 42, 26)
SKIN       = (133, 84, 52)
SKIN_LT    = (176, 122, 74)

ALLOWED = {INK, BLUE_DEEP, BLUE_MID, CYAN, CYAN_PALE, RED_DARK, RED,
           GREEN, GREEN_DEEP, WHITE, GREY, SKIN_SH, SKIN, SKIN_LT}


# ------------------------------------------------------------ draw helpers
class Canvas:
    """One sprite frame. All coordinates are inclusive pixel indices."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.img.load()

    # --- primitives -------------------------------------------------
    def put(self, x, y, col):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = (col[0], col[1], col[2], 255)

    def at(self, x, y):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[x, y]
        return (0, 0, 0, 0)

    def solid(self, x, y):
        return self.at(x, y)[3] > 0

    def hline(self, x0, x1, y, col):
        for x in range(int(x0), int(x1) + 1):
            self.put(x, y, col)

    def vline(self, x, y0, y1, col):
        for y in range(int(y0), int(y1) + 1):
            self.put(x, y, col)

    def rect(self, x0, y0, x1, y1, col):
        for y in range(int(y0), int(y1) + 1):
            self.hline(x0, x1, y, col)

    def rrect(self, x0, y0, x1, y1, col):
        """Rect with the four corner pixels knocked off - reads as rounded."""
        self.rect(x0, y0, x1, y1, col)
        for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            if 0 <= cx < self.w and 0 <= cy < self.h:
                self.px[int(cx), int(cy)] = (0, 0, 0, 0)

    def rows(self, table, col):
        """table = [(y, x0, x1), ...] - hand authored silhouettes."""
        for y, x0, x1 in table:
            self.hline(x0, x1, y, col)

    def line(self, x0, y0, x1, y1, col):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, col)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def thick(self, x0, y0, x1, y1, w, col):
        """Line stamped with a square brush of side w (use odd widths)."""
        r = w // 2
        pts = []
        self._collect(x0, y0, x1, y1, pts)
        for px_, py_ in pts:
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    self.put(px_ + ox, py_ + oy, col)

    def _collect(self, x0, y0, x1, y1, out):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            out.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def limb(self, x0, y0, x1, y1, w, col, rim=None, jacket=INK, outer=None):
        """Outlined limb: 1px jacket, colour core, optional top rim light.

        With `outer` given, jacket pixels that land on empty background are
        drawn in that colour instead. outline() already lays an INK contour
        there, so spending INK on both wrapped every 5px limb in two dark
        rings. Jacket pixels landing on solid work stay INK - that is the
        internal contour that keeps a limb off the body it crosses."""
        before = ([[self.solid(x, y) for y in range(self.h)]
                   for x in range(self.w)] if outer is not None else None)
        self.thick(x0, y0, x1, y1, w + 2, jacket)
        self.thick(x0, y0, x1, y1, w, col)
        if outer is not None:
            pts = []
            self._collect(x0, y0, x1, y1, pts)
            rj = (w + 2) // 2
            for px_, py_ in pts:
                for oy in range(-rj, rj + 1):
                    for ox in range(-rj, rj + 1):
                        x, y = px_ + ox, py_ + oy
                        if (0 <= x < self.w and 0 <= y < self.h
                                and not before[x][y]
                                and self.at(x, y)[:3] == jacket):
                            self.put(x, y, outer)
        if rim is not None:
            pts = []
            self._collect(x0, y0, x1, y1, pts)
            r = w // 2
            for i, (px_, py_) in enumerate(pts):
                if i % 3 == 1:                     # dashed - glitchy dead code
                    self.put(px_ - r, py_ - r, rim)

    def disc(self, cx, cy, r, col):
        for dy in range(-r, r + 1):
            span = int(math.sqrt(max(0.0, r * r + 0.35 - dy * dy)))
            self.hline(cx - span, cx + span, cy + dy, col)

    def dither(self, x0, y0, x1, y1, base, col, phase=0):
        """Checkerboard `col` into the `base`-coloured pixels of a box.

        Only repaints pixels that currently read `base`, so it can be laid
        over finished work without eating detail. This is the player
        sprite's signature: every shade transition gets one dithered row
        instead of a hard jump."""
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                if (x + y) % 2 == phase and self.at(x, y)[:3] == base:
                    self.put(x, y, col)

    def top_rim(self, base, hi, box=None):
        """First pixel of `base` scanning down each column becomes `hi`."""
        x0, y0, x1, y1 = box or (0, 0, self.w - 1, self.h - 1)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if self.at(x, y)[:3] == base:
                    self.put(x, y, hi)
                    break

    def bottom_rim(self, base, lo, box=None):
        """Last pixel of `base` scanning down each column becomes `lo`."""
        x0, y0, x1, y1 = box or (0, 0, self.w - 1, self.h - 1)
        for x in range(x0, x1 + 1):
            for y in range(y1, y0 - 1, -1):
                if self.at(x, y)[:3] == base:
                    self.put(x, y, lo)
                    break

    def outline(self, col=INK):
        """1px INK contour hugging the silhouette (8-neighbour)."""
        filled = [[self.solid(x, y) for y in range(self.h)] for x in range(self.w)]
        for x in range(self.w):
            for y in range(self.h):
                if filled[x][y]:
                    continue
                hit = False
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        nx, ny = x + ox, y + oy
                        if 0 <= nx < self.w and 0 <= ny < self.h and filled[nx][ny]:
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    self.put(x, y, col)


def verify(strip, fw, fh, nframes, name):
    """Hard gates that must hold for every strip. Raises, so `python -O`
    (which strips asserts) cannot silently let a bad sheet through."""
    px = strip.load()
    w, h = strip.size

    # 1. locked palette - every opaque pixel must be one of the 15 colours
    used = {px[x, y][:3] for x in range(w) for y in range(h) if px[x, y][3] > 0}
    if used - ALLOWED:
        raise RuntimeError(f"{name}: off-palette {sorted(used - ALLOWED)}")

    # 2. no anti-aliasing / no alpha blending - alpha is strictly 0 or 255
    alphas = {px[x, y][3] for x in range(w) for y in range(h)}
    if alphas - {0, 255}:
        raise RuntimeError(f"{name}: partial alpha {sorted(alphas - {0, 255})}")

    # 3. transparent background, never filled black
    if px[0, 0][3] != 0 or px[w - 1, h - 1][3] != 0:
        raise RuntimeError(f"{name}: background is not transparent")

    # 4. no frame may touch its own canvas edge - catches silent clipping
    for i in range(nframes):
        ox = i * fw
        clipped = (
            any(px[ox + x, 0][3] for x in range(fw))
            or any(px[ox + x, fh - 1][3] for x in range(fw))
            or any(px[ox + 0, y][3] for y in range(fh))
            or any(px[ox + fw - 1, y][3] for y in range(fh))
        )
        if clipped:
            raise RuntimeError(f"{name}: frame {i} touches the canvas edge")


# INK share of lit pixels measured on the pre-relight sheets, kept so every
# run reports the delta.  Measured on this same metric the style baseline,
# player/player_idle.png, is 49.1% INK and 0.8% dither - and every other
# player sheet lands within a point of it.  A relight review quoted the
# player at 38% INK / 2.4% dither; that does not reproduce, so the numbers
# below are the ones to trust when re-tuning.
BASELINE_INK = {"worm": 53.2, "drone": 48.0, "husk": 62.2, "guardian": 59.6}
BASELINE_DITHER = {"worm": 0.6, "drone": 0.7, "husk": 1.8, "guardian": 0.4}

# husk and guardian read as blobs and are held to 45%.  worm and drone already
# sat inside the player's range, so they are only gated against regressing.
TARGET_INK = {"worm": 50.0, "drone": 50.0, "husk": 45.0, "guardian": 45.0}


def measure(strip):
    """INK share of lit pixels, and share of lit pixels sitting in a
    checkerboard (differing from an identical pair of left/right AND
    top/bottom neighbours)."""
    px = strip.load()
    w, h = strip.size
    lit = ink = dith = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if not p[3]:
                continue
            lit += 1
            ink += p[:3] == INK
            if 0 < x < w - 1 and 0 < y < h - 1:
                l, r = px[x - 1, y], px[x + 1, y]
                u, d = px[x, y - 1], px[x, y + 1]
                if (l[3] and r[3] and l[:3] == r[:3] != p[:3]
                        and u[3] and d[3] and u[:3] == d[:3] != p[:3]):
                    dith += 1
    lit = max(lit, 1)
    return 100.0 * ink / lit, 100.0 * dith / lit


def finish(frames, name):
    """Save strip + 8x preview, verify palette, report before/after lighting."""
    fw, fh = frames[0].w, frames[0].h
    strip = Image.new("RGBA", (fw * len(frames), fh), (0, 0, 0, 0))
    for i, c in enumerate(frames):
        strip.paste(c.img, (i * fw, 0))
    w, h = strip.size
    strip.save(f"{name}.png")
    strip.resize((w * 8, h * 8), Image.NEAREST).save(f"{name}_8x.png")   # preview
    px = strip.load()
    used = {px[x, y][:3] for x in range(w) for y in range(h) if px[x, y][3] > 0}
    assert not (used - ALLOWED), f"off-palette: {used - ALLOWED}"
    verify(strip, fw, fh, len(frames), name)
    ink, dith = measure(strip)
    b_ink, b_dith = BASELINE_INK[name], BASELINE_DITHER[name]
    print(f"ok: {name}.png  {len(frames)}f  {w}x{h}   "
          f"INK {b_ink:5.1f}% -> {ink:5.1f}%   "
          f"dither {b_dith:4.1f}% -> {dith:4.1f}%")
    gate = TARGET_INK[name]
    assert ink <= gate, f"{name}: INK share {ink:.1f}% exceeds the {gate}% gate"


# =========================================================================
# 1. WORM - 64x48 x4.  Segmented mechanical serpent, head right, S-curve.
# =========================================================================
# The body is built column by column along a sine spine so the curve stays
# continuous; armour thickness is quantised per segment to keep it chunky.
WORM_HEAD_X = 52           # centre of the head block
WORM_NECK_X = 47           # body columns stop here and tuck under the head
WORM_TAIL_X = 2
WORM_SEG_LEN = 6           # columns per armour segment
WORM_THICK = [4, 4, 4, 3, 3, 2, 2, 1, 1]   # half height, segment 0 = nearest head


def worm_spine(x, f):
    """Undulating centre line. One frame = a quarter of the travelling wave."""
    return 24.0 + 7.0 * math.sin((WORM_HEAD_X - x) * 0.19 + f * math.pi / 2)


# skull silhouette, offsets from the head centre: (dy, x0, x1)
WORM_SKULL = [(-6, -4, 1), (-5, -5, 3), (-4, -6, 5), (-3, -6, 6), (-2, -6, 6),
              (-1, -6, 6), (0, -6, 6), (1, -6, 6), (2, -6, 6), (3, -5, 6),
              (4, -4, 5), (5, -3, 3), (6, -2, 1)]


def worm_horn(c, x0, y0, x1, y1):
    """Two-pixel-thick tapering oni horn, lit along its upper edge."""
    c.line(x0, y0, x1, y1, RED_DARK)
    c.line(x0 + 1, y0 + 1, x1, y1 + 1, RED_DARK)
    c.line(x0, y0 - 1, x1, y1 - 1, RED)
    c.put(x1, y1 - 1, RED)


def worm_head(c, cx, cy, f):
    """Skull chassis wearing a cracked RED oni faceplate, facing right."""
    c.rows([(cy + dy, cx + x0, cx + x1) for dy, x0, x1 in WORM_SKULL], GREY)
    c.hline(cx - 4, cx + 4, cy + 5, INK)                     # jaw shadow
    c.hline(cx - 3, cx + 2, cy + 6, INK)
    c.hline(cx - 4, cx - 2, cy - 6, CYAN_PALE)               # top-facing glint
    c.vline(cx - 6, cy - 2, cy + 2, INK)                     # neck collar seam
    c.vline(cx - 5, cy - 3, cy + 3, RED)

    # two oni horns splayed apart so both read in silhouette
    worm_horn(c, cx - 2, cy - 6, cx - 8, cy - 11)            # sweeps back
    worm_horn(c, cx + 4, cy - 5, cx + 8, cy - 10)            # sweeps forward
    c.put(cx - 1, cy - 6, INK)                               # root notches
    c.put(cx + 3, cy - 5, INK)

    # faceplate clipped to the front of the skull so the silhouette stays round
    for dy, x0, x1 in WORM_SKULL:
        if -4 <= dy <= 4:
            c.hline(cx + max(x0, -3), cx + x1, cy + dy, RED_DARK)
    c.hline(cx + 0, cx + 5, cy - 4, RED)                     # brow ridge, front only
    c.put(cx - 1, cy - 4, RED_DARK)                          # so it stops short of
    c.put(cx - 2, cy - 4, RED_DARK)                          # becoming a red stripe
    c.hline(cx + 0, cx + 6, cy + 2, INK)                     # mouth
    c.hline(cx + 1, cx + 5, cy + 3, RED)                     # lit lower lip
    c.put(cx + 2, cy + 3, INK)                               # fang gaps
    c.put(cx + 4, cy + 3, INK)

    # Two glowing eyes in shallow 2-row sockets.  They used to be 5 rows deep
    # and ran straight into the mouth cavity below, so the whole face read as
    # one hole punched in a red hood; three rows of faceplate now sit between
    # the sockets and the mouth.
    c.rect(cx - 3, cy - 3, cx + 6, cy - 2, INK)              # socket band
    c.hline(cx - 2, cx + 0, cy - 2, RED)                     # far eye
    c.hline(cx + 3, cx + 5, cy - 2, RED)                     # near eye
    c.put(cx - 2, cy - 3, RED)                               # outer ends lift
    c.put(cx + 5, cy - 3, RED)                               # into an angry slant
    c.dither(cx + 0, cy - 1, cx + 6, cy + 0, RED_DARK, RED)  # cheek falloff

    # the mask is broken - crack plus GREEN corruption bleeding out of it
    c.line(cx + 1, cy - 4, cx + 2, cy + 2, INK)
    c.put(cx + 1, cy - 3, GREEN_DEEP)
    c.put(cx + 2, cy + (0 if f % 2 == 0 else 1), GREEN)


def worm_frame(f):
    c = Canvas(64, 48)
    seams = []

    # --- armoured body, one column at a time along the spine --------------
    for x in range(WORM_TAIL_X, WORM_NECK_X):
        dist = WORM_HEAD_X - x
        seg = min(dist // WORM_SEG_LEN, len(WORM_THICK) - 1)
        t = WORM_THICK[seg]
        y = int(round(worm_spine(x, f)))
        # Three-value ramp down each column so the S-curve reads as a tube
        # rather than a flat grey ribbon: lit top bevel, GREY face, warm
        # RED_DARK underside, INK only on the last row as a seam.
        # Parity is taken from the row actually being painted, so the two
        # underside rows land on alternating columns and read as one
        # checkerboard; keying both off the spine y put them on the same
        # columns and gave vertical stripes instead.
        yb = y + t
        c.vline(x, y - t, yb, GREY)
        c.put(x, yb, INK)                                    # underside seam
        if t >= 2 and (x + yb) % 2 == 0:
            c.put(x, yb, RED_DARK)                           # warm bounce
        if t >= 3 and (x + yb - 1) % 2 == 0:
            c.put(x, yb - 1, RED_DARK)                       # dithered shoulder
        if t >= 3 and (x + y - t) % 2 == 0:
            c.put(x, y - t, CYAN_PALE)                       # top-facing bevel
        if t >= 4 and (x + y - t + 1) % 2 == 0:
            c.put(x, y - t + 1, CYAN_PALE)                   # its dithered falloff
        if dist % WORM_SEG_LEN == 0:                         # segment joint
            seams.append((x, y, t))
        elif dist % WORM_SEG_LEN == 3 and t >= 2:            # crown glint
            c.hline(x, x + 1, y - t, CYAN_PALE)

    # RED seam rings between the armour segments
    for x, y, t in seams:
        c.vline(x, y - t, y + t, RED)
        c.put(x, y - t, RED_DARK)
        c.put(x, y + t, RED_DARK)

    worm_head(c, WORM_HEAD_X, int(round(worm_spine(WORM_HEAD_X, f))), f)
    c.outline()

    # GREEN corruption venting from one seam, working its way down the body
    if seams:
        x, y, t = seams[(f + 1) % len(seams)]
        c.vline(x, y - t + 1, y + t - 1, GREEN)
        c.put(x, y + t + 2 + (f % 2), GREEN)
        c.put(x + 1, y - t - 1, GREEN_DEEP)
    return c


# =========================================================================
# 2. DRONE - 48x48 x4.  "Keylogger": pod chassis, blue rotors, one cyan eye.
# =========================================================================
DRONE_BOB = [0, -1, -2, -1]         # vertical hover
DRONE_TILT = [0, 1, 0, -1]          # rotor sweep
DRONE_GLOW = [0, 1, 2, 1]           # eye brightening


def drone_wing(c, x_in, y_in, x_out, y_out):
    """Angular rotor blade: BLUE_DEEP body, BLUE_MID crown, INK underside."""
    c.thick(x_in, y_in, x_out, y_out, 3, BLUE_DEEP)
    c.line(x_in, y_in - 1, x_out, y_out - 1, BLUE_MID)
    c.line(x_in, y_in + 2, x_out, y_out + 2, INK)


def drone_mask(c, cx, top):
    """Tiny cracked WHITE oni mask swinging on a cord under the chassis."""
    c.vline(cx, top - 3, top - 1, INK)                       # cord
    c.rows([(top + 0, cx - 3, cx + 3),
            (top + 1, cx - 4, cx + 4),
            (top + 2, cx - 4, cx + 4),
            (top + 3, cx - 4, cx + 4),
            (top + 4, cx - 4, cx + 4),
            (top + 5, cx - 4, cx + 3),                       # chipped corner
            (top + 6, cx - 3, cx + 2),
            (top + 7, cx - 2, cx + 0)], WHITE)
    c.put(cx - 4, top - 1, WHITE)                            # horn nubs
    c.put(cx + 4, top - 1, WHITE)
    c.rect(cx - 3, top + 2, cx - 2, top + 2, INK)            # eye slits
    c.rect(cx + 2, top + 2, cx + 3, top + 2, INK)
    c.hline(cx - 2, cx + 2, top + 5, INK)                    # grin
    c.dither(cx - 4, top + 3, cx + 4, top + 3, WHITE, GREY)  # mask falls to shade
    c.dither(cx - 4, top + 4, cx + 4, top + 4, WHITE, GREY)
    c.line(cx + 1, top - 1, cx - 1, top + 7, INK)            # the crack
    c.put(cx, top + 3, GREEN)                                # corruption leak
    c.put(cx - 1, top + 6, GREEN_DEEP)


def drone_frame(f):
    c = Canvas(48, 48)
    bob = DRONE_BOB[f]
    tilt = DRONE_TILT[f]
    cy = 17 + bob
    cx = 24

    # antenna with a blinking corruption tip
    c.vline(cx, cy - 11, cy - 9, INK)
    c.put(cx, cy - 12, GREEN if f % 2 == 0 else GREEN_DEEP)

    # rotors, two per side
    drone_wing(c, cx - 10, cy - 4, cx - 20, cy - 7 - tilt)
    drone_wing(c, cx - 10, cy + 2, cx - 19, cy + 6 + tilt)
    drone_wing(c, cx + 10, cy - 4, cx + 20, cy - 7 + tilt)
    drone_wing(c, cx + 10, cy + 2, cx + 19, cy + 6 - tilt)

    # chassis pod
    c.rows([(cy - 8, cx - 6, cx + 6),
            (cy - 7, cx - 8, cx + 8),
            (cy - 6, cx - 10, cx + 10),
            (cy - 5, cx - 11, cx + 11),
            (cy - 4, cx - 11, cx + 11),
            (cy - 3, cx - 11, cx + 11),
            (cy - 2, cx - 11, cx + 11),
            (cy - 1, cx - 11, cx + 11),
            (cy + 0, cx - 11, cx + 11),
            (cy + 1, cx - 11, cx + 11),
            (cy + 2, cx - 11, cx + 11),
            (cy + 3, cx - 10, cx + 10),
            (cy + 4, cx - 9, cx + 9),
            (cy + 5, cx - 7, cx + 7),
            (cy + 6, cx - 5, cx + 5)], GREY)
    c.hline(cx - 7, cx + 7, cy + 5, INK)                     # underside shade
    c.hline(cx - 5, cx + 5, cy + 6, INK)
    c.hline(cx - 5, cx - 2, cy - 8, CYAN_PALE)               # top-facing glint
    c.put(cx - 9, cy - 6, CYAN_PALE)
    c.vline(cx - 11, cy - 3, cy + 1, INK)                    # side panel seams
    c.vline(cx + 11, cy - 3, cy + 1, INK)
    c.rect(cx - 9, cy + 3, cx - 7, cy + 4, INK)              # vent grilles
    c.rect(cx + 7, cy + 3, cx + 9, cy + 4, INK)
    # dithered shade transitions on the pod - the player sprite's signature
    c.dither(cx - 10, cy + 3, cx + 10, cy + 3, GREY, INK)
    c.dither(cx - 11, cy + 4, cx + 11, cy + 4, GREY, INK)
    c.dither(cx - 9, cy - 7, cx + 1, cy - 7, GREY, CYAN_PALE)
    c.dither(cx - 10, cy - 6, cx + 0, cy - 6, GREY, CYAN_PALE)

    # central eye lens
    glow = DRONE_GLOW[f]
    c.disc(cx, cy - 1, 6, INK)                               # socket
    c.disc(cx, cy - 1, 5, BLUE_DEEP)                         # iris ring
    c.disc(cx, cy - 1, 4, CYAN)
    if glow >= 1:
        c.disc(cx, cy - 1, 2, CYAN_PALE)
    else:
        c.disc(cx, cy - 1, 2, BLUE_MID)
    if glow == 2:
        c.hline(cx - 5, cx + 5, cy - 1, CYAN_PALE)           # lens flare
        c.vline(cx, cy - 6, cy + 4, CYAN_PALE)
    c.put(cx - 2, cy - 4, CYAN_PALE)                         # fixed glint
    c.put(cx - 3, cy - 3, CYAN_PALE)

    drone_mask(c, cx, cy + 10)
    c.outline()

    # detached spirit motes, drawn after the contour so they stay bright
    if glow == 2:
        c.put(cx + 13, cy - 1, CYAN)
        c.put(cx - 13, cy - 1, CYAN)
    return c


# =========================================================================
# 3. HUSK - 64x64 x4.  "Botnet Node": hunched rag-wrapped corpse, white mask.
# =========================================================================
# Hunched torso: high rounded back on the left, belly slumping forward right.
HUSK_TORSO = [(24, 28, 34), (25, 27, 36), (26, 26, 37), (27, 26, 38),
              (28, 25, 38), (29, 25, 38), (30, 25, 38), (31, 25, 38),
              (32, 25, 37), (33, 25, 37), (34, 25, 37), (35, 26, 37),
              (36, 26, 36), (37, 26, 36), (38, 26, 36), (39, 27, 36),
              (40, 27, 35), (41, 28, 35), (42, 28, 34)]

# torn cape hanging off the back: (y, x0, x1) - the hem frays as it drops
HUSK_CAPE = [(26, 23, 26), (27, 22, 26), (28, 21, 26), (29, 21, 26),
             (30, 20, 26), (31, 20, 26), (32, 19, 26), (33, 19, 25),
             (34, 20, 25), (35, 19, 25), (36, 20, 24), (37, 19, 24),
             (38, 21, 24), (39, 20, 23), (40, 22, 23), (41, 21, 23)]

HUSK_FRAMES = [
    # dy, near foot, far foot, near hand, far hand   (walk: contact/down x2)
    dict(dy=0, nf=(38, 57), ff=(25, 57), nh=(27, 47), fh=(37, 44)),
    dict(dy=1, nf=(34, 57), ff=(29, 56), nh=(31, 48), fh=(34, 46)),
    dict(dy=0, nf=(27, 57), ff=(38, 57), nh=(37, 44), fh=(27, 47)),
    dict(dy=1, nf=(31, 56), ff=(34, 57), nh=(34, 46), fh=(31, 48)),
]


# (core, rim, jacket, outer) - a three step depth ramp.  Far limbs used to be
# solid INK cores, which is what welded the lower body into one silhouette;
# they now sit one value below the near limbs.  Near limbs keep an INK jacket
# where they cross the body and fall to BLUE_DEEP against open background.
HUSK_NEAR = (BLUE_MID, CYAN_PALE, INK, BLUE_DEEP)
HUSK_FAR = (BLUE_DEEP, None, BLUE_DEEP, None)


def husk_leg(c, hip, foot, near):
    """Thigh + shin with a forward knee break. Far leg stays in shadow."""
    core, rim, jacket, outer = HUSK_NEAR if near else HUSK_FAR
    kx = (hip[0] + foot[0]) // 2 + 2
    ky = (hip[1] + foot[1]) // 2 + 1
    c.limb(hip[0], hip[1], kx, ky, 3, core, rim, jacket, outer)
    c.limb(kx, ky, foot[0], foot[1], 3, core, rim, jacket, outer)
    # boot: lit instep over a coloured body, INK spent only on the sole - it
    # used to be an INK block with a one pixel highlight
    c.rect(foot[0] - 3, foot[1] - 1, foot[0] + 4, foot[1] + 2, outer or jacket)
    c.rect(foot[0] - 2, foot[1] - 1, foot[0] + 3, foot[1] + 1, core)
    c.hline(foot[0] - 2, foot[0] + 3, foot[1] + 2,
            INK if near else jacket)                            # dark sole
    c.hline(foot[0] - 2, foot[0] + 1, foot[1] - 1, rim or core)  # top of the foot


def husk_arm(c, sh, hand, near):
    """Long dangling arm, elbow kicked back - it hangs like dead weight."""
    core, rim, jacket, outer = HUSK_NEAR if near else HUSK_FAR
    ex = (sh[0] + hand[0]) // 2 - 3
    ey = (sh[1] + hand[1]) // 2
    c.limb(sh[0], sh[1], ex, ey, 3, core, rim, jacket, outer)
    c.limb(ex, ey, hand[0], hand[1], 3, core, rim, jacket, outer)
    c.rect(hand[0] - 2, hand[1] - 1, hand[0] + 2, hand[1] + 4, outer or jacket)
    c.rect(hand[0] - 1, hand[1], hand[0] + 1, hand[1] + 3, core)   # fist
    c.hline(hand[0] - 1, hand[0] + 1, hand[1] + 3, INK)            # under-shadow
    c.put(hand[0] - 1, hand[1], rim or core)                       # knuckle catch


def husk_mask(c, dy, f):
    """Cracked WHITE oni mask, GREEN data light pouring out of the split."""
    c.rows([(11, 36, 42), (12, 35, 43), (13, 35, 43), (14, 35, 43),
            (15, 35, 43), (16, 35, 43), (17, 35, 43), (18, 36, 42),
            (19, 36, 42), (20, 37, 41)], WHITE)
    c.put(35, 10, WHITE)                      # horn nubs
    c.put(34, 9, WHITE)
    c.put(43, 10, WHITE)
    c.put(44, 9, WHITE)
    c.rect(36, 14, 37, 15, INK)               # eye holes
    c.rect(40, 14, 41, 15, INK)
    c.hline(37, 41, 18, INK)                  # grin
    c.put(38, 19, INK)
    c.put(40, 19, INK)
    c.line(39, 10, 38, 20, INK)               # the crack
    c.line(39, 12, 42, 11, INK)
    c.put(39, 13, GREEN)                      # corruption bleeding through
    c.put(39, 16, GREEN)
    c.put(38, 18, GREEN_DEEP)
    c.put(41, 11, GREEN_DEEP)
    c.put(36, 14 + (f % 2), GREEN)            # eye socket flicker
    c.vline(35, 21, 25 + dy, INK)             # neck, lit on its near side
    c.vline(36, 21, 25 + dy, BLUE_DEEP)


def husk_frame(f):
    p = HUSK_FRAMES[f]
    dy = p["dy"]
    c = Canvas(64, 64)

    hip_n, hip_f = (32, 42 + dy), (29, 42 + dy)
    sh_n, sh_f = (33, 29 + dy), (29, 27 + dy)

    # --- everything behind the body ---------------------------------------
    husk_leg(c, hip_f, p["ff"], near=False)
    husk_arm(c, sh_f, (p["fh"][0], p["fh"][1] + dy), near=False)
    # The cape was solid INK, which fused it to the torso and the far limbs
    # into one mass.  It is now a rag lit along its top edge, with INK spent
    # on the folds and the outer fray instead of the whole shape.
    for y, x0, x1 in HUSK_CAPE:                      # torn cape off the back
        c.hline(x0, x1, y + dy, BLUE_DEEP)
    c.top_rim(BLUE_DEEP, BLUE_MID, box=(19, 24 + dy, 26, 30 + dy))  # cape shoulder
    c.line(23, 29 + dy, 21, 40 + dy, INK)            # one fold: the rag is barely
    #                                                  7px wide and two read as noise
    c.dither(23, 27 + dy, 26, 32 + dy, BLUE_DEEP, BLUE_MID)  # shoulder falloff
    c.dither(19, 39 + dy, 26, 41 + dy, BLUE_DEEP, INK)   # hem falls into shadow

    # --- rag-wrapped torso -------------------------------------------------
    for y, x0, x1 in HUSK_TORSO:
        c.hline(x0, x1, y + dy, BLUE_DEEP)
    # Lift the torso a full value off the cape.  Both were BLUE_DEEP, so the
    # internal contour alone still left them reading as one mass; lightening
    # the torso separates them without spending any more INK.
    c.top_rim(BLUE_DEEP, BLUE_MID, box=(25, 22 + dy, 38, 34 + dy))
    c.hline(29, 37, 26 + dy, BLUE_MID)                       # lit shoulder shelf
    c.hline(29, 37, 27 + dy, BLUE_MID)
    c.dither(27, 28 + dy, 38, 34 + dy, BLUE_DEEP, BLUE_MID)  # highlight falloff
    c.bottom_rim(BLUE_DEEP, INK, box=(25, 30 + dy, 38, 44 + dy))
    c.line(30, 27 + dy, 28, 34 + dy, BLUE_DEEP)      # cloth folds: BLUE_DEEP
    c.line(29, 34 + dy, 27, 42 + dy, INK)            # while they cross the lit
    c.line(35, 29 + dy, 34, 35 + dy, BLUE_DEEP)      # upper torso, INK once the
    c.line(34, 35 + dy, 33, 41 + dy, INK)            # rag drops into shadow
    c.put(36, 32 + dy, CYAN_PALE)                    # bone showing through
    c.put(36, 36 + dy, CYAN_PALE)
    c.hline(27, 34, 43 + dy, BLUE_DEEP)              # hem shadow, dithered so
    c.dither(27, 43 + dy, 34, 43 + dy, BLUE_DEEP, INK)   # the rag frays off
    # internal contour: the torso's own back edge, so it reads in front of the
    # cape instead of dissolving into it
    for y, x0, x1 in HUSK_TORSO:
        c.put(x0, y + dy, INK)

    # --- head: skull, hood, mask ------------------------------------------
    c.disc(38, 16, 5, INK)                           # skull
    # the cowl is the same rag as the cape, so it gets the same lighting rather
    # than staying a flat INK cap welded to the mask
    c.rows([(9, 33, 41), (10, 31, 42), (11, 30, 34), (12, 29, 33),
            (13, 28, 32), (14, 28, 31), (15, 28, 30), (16, 29, 31),
            (17, 30, 32)], BLUE_DEEP)                # cowl with a torn tail
    c.top_rim(BLUE_DEEP, BLUE_MID, box=(28, 8, 42, 14))   # light on the crown
    c.dither(28, 15, 33, 17, BLUE_DEEP, INK)         # underside of the cowl
    husk_mask(c, dy, f)

    # --- limbs in front ----------------------------------------------------
    husk_leg(c, hip_n, p["nf"], near=True)
    husk_arm(c, sh_n, (p["nh"][0], p["nh"][1] + dy), near=True)

    c.outline()

    # data light escaping the mask, rising and dissipating
    c.put(45 + f % 2, 7 - f % 3, GREEN)
    c.put(47, 10 + (f % 2), GREEN_DEEP)
    c.put(42, 5 + (f % 3), GREEN_DEEP)
    return c


# =========================================================================
# 4. GUARDIAN - 96x96 x4.  "Zero-Day": plated elite, shoulder mask, green axe.
# =========================================================================
GUARD_DY = [0, 1, 2, 1]        # upper body settling under the armour's weight
GUARD_AXE = [0, 1, 2, 1]       # axe head dipping

# --- armour silhouettes, all (y, x0, x1) ---------------------------------
G_HELM = [(10, 44, 51), (11, 42, 53), (12, 41, 54), (13, 41, 54),
          (14, 41, 55), (15, 41, 55), (16, 41, 55), (17, 41, 55),
          (18, 41, 55), (19, 40, 55), (20, 39, 56), (21, 39, 56),
          (22, 38, 57), (23, 38, 57), (24, 39, 56), (25, 40, 55)]

G_CHEST = [(27, 40, 52), (28, 38, 54), (29, 37, 55), (30, 36, 56),
           (31, 36, 56), (32, 35, 57), (33, 35, 57), (34, 35, 57),
           (35, 35, 57), (36, 35, 57), (37, 35, 56), (38, 36, 56),
           (39, 36, 55), (40, 36, 55), (41, 37, 54), (42, 37, 54),
           (43, 38, 53), (44, 38, 53), (45, 39, 52), (46, 39, 52)]

G_PAUL_BACK = [(24, 30, 38), (25, 28, 39), (26, 26, 39), (27, 25, 39),
               (28, 25, 39), (29, 25, 39), (30, 25, 39), (31, 25, 39),
               (32, 25, 39), (33, 25, 39), (34, 25, 39), (35, 25, 39),
               (36, 25, 39), (37, 26, 39), (38, 27, 38), (39, 29, 37),
               (40, 31, 35)]

G_PAUL_FRONT = [(24, 54, 62), (25, 53, 64), (26, 53, 66), (27, 53, 67),
                (28, 53, 67), (29, 53, 67), (30, 53, 67), (31, 53, 67),
                (32, 53, 67), (33, 53, 67), (34, 53, 67), (35, 53, 67),
                (36, 53, 67), (37, 53, 66), (38, 54, 65), (39, 55, 63),
                (40, 57, 61)]

# the axe haft: butt planted on the same ground line as the boots, head dips.
# Everything else about the arm derives from this line.
G_HAFT_BOT = (62, 89)
G_HAFT_TOP = (78, 24)


def haft_x(y, ad):
    """x of the haft centre line at height y, for the current dip."""
    (x0, y0), (x1, y1) = G_HAFT_BOT, (G_HAFT_TOP[0], G_HAFT_TOP[1] + ad)
    return int(round(x0 + (x1 - x0) * (y - y0) / float(y1 - y0)))


def gplate(c, table, dy=0, fill=INK, rim=GREY):
    """Armour plate from a rows table; the top-facing edge catches light."""
    top = {}
    for y, x0, x1 in table:
        c.hline(x0, x1, y + dy, fill)
        for x in range(x0, x1 + 1):
            if x not in top:
                top[x] = y + dy
    for x, y in top.items():
        c.put(x, y, rim)


def gband(c, table, dy=0, pitch=5, face=GREY, seam=INK, hi=CYAN_PALE):
    """Lamellar armour plate: GREY faces divided by 1px INK seams, each band
    lit along its top edge and dithered into the seam beneath it.

    This is the inverse proportion of gplate() - which fills INK and lights a
    single row - and it is what the hip, thigh, shin and boot plates use now.
    Those rows measured 85-100% INK and read as one black bar across the
    sprite rather than as stacked plates."""
    y0 = min(y for y, _, _ in table)
    for y, x0, x1 in table:
        yy, k = y + dy, (y - y0) % pitch
        if k == pitch - 1:
            c.hline(x0, x1, yy, seam)                    # underside of the band
            continue
        c.hline(x0, x1, yy, face)
        if k == pitch - 2:
            c.dither(x0, yy, x1, yy, face, seam, phase=1)    # shoulder into seam
    # One top-facing bevel for the whole plate - lighting every band instead
    # turned the legs into corduroy.  Both rows take the same phase: (x+y)%2
    # already flips per row, so matching phases give a checkerboard and
    # opposite ones would give vertical stripes.
    if hi is not None:
        for y, x0, x1 in table:
            if y in (y0, y0 + 1):
                c.dither(x0, y + dy, x1, y + dy, face, hi)


def gseam(c, table, ys, dy=0, col=GREY):
    """Light named rows of a plate so a tall slab reads as banded armour.
    Rows are indented one pixel so the plate keeps its own dark edge."""
    for y, x0, x1 in table:
        if y in ys:
            c.hline(x0 + 1, x1 - 1, y + dy, col)
        elif y - 1 in ys or y - 2 in ys:
            c.dither(x0 + 1, y + dy, x1 - 1, y + dy, INK, col)


def guard_axe(c, ad):
    """Heavy pole-axe: GREY haft, crescent blade with a GREEN glowing edge.
    The butt stays planted while the head dips, so the whole axe rotates."""
    bx, by = G_HAFT_BOT
    tx, ty = G_HAFT_TOP[0], G_HAFT_TOP[1] + ad
    c.thick(bx, by, tx, ty, 5, INK)
    c.thick(bx, by, tx, ty, 3, GREY)
    c.rect(bx - 2, by, bx + 2, by + 2, INK)                  # butt cap
    c.hline(bx - 1, bx + 1, by, GREY)

    # blade mount collar
    c.rrect(tx - 6, ty - 3, tx + 3, ty + 6, GREY)
    c.hline(tx - 5, tx + 2, ty + 6, INK)
    c.vline(tx - 6, ty - 2, ty + 5, INK)

    # crescent = outer disc minus inner disc, GREEN along the outer edge
    ox, oy, orad = tx - 2, ty - 2, 14
    ix, iy, irad = tx - 13, ty - 3, 12
    for y in range(oy - orad, oy + orad + 1):
        span = int(math.sqrt(max(0.0, orad * orad + 0.35 - (y - oy) ** 2)))
        cut = int(math.sqrt(max(0.0, irad * irad + 0.35 - (y - iy) ** 2))) \
            if abs(y - iy) <= irad else -1
        lo = ix + cut + 1 if cut >= 0 else ox - span
        hi = ox + span
        if hi < lo:
            continue
        c.hline(lo, hi, y, GREY)
        c.put(hi, y, GREEN)                                  # glowing edge
        if hi - 1 >= lo:
            c.put(hi - 1, y, GREEN)
        if hi - 2 >= lo:
            c.put(hi - 2, y, GREEN_DEEP)
        if y > oy and hi - 3 >= lo:
            c.put(lo, y, INK)                                # underside shade


def guard_shoulder_mask(c, x, y):
    """RED oni mask bolted to the back pauldron, cracked and leaking."""
    c.rows([(y + 0, x + 2, x + 9),
            (y + 1, x + 1, x + 10),
            (y + 2, x + 0, x + 11),
            (y + 3, x + 0, x + 11),
            (y + 4, x + 0, x + 11),
            (y + 5, x + 0, x + 11),
            (y + 6, x + 1, x + 10),
            (y + 7, x + 1, x + 10),
            (y + 8, x + 2, x + 9),
            (y + 9, x + 4, x + 7)], RED_DARK)
    c.hline(x + 2, x + 9, y + 0, RED)                        # lit brow
    c.put(x + 1, y + 1, RED)
    c.put(x + 10, y + 1, RED)
    c.rect(x + 1, y + 2, x + 3, y + 4, INK)                  # angry eye slits
    c.rect(x + 8, y + 2, x + 10, y + 4, INK)
    c.rect(x + 1, y + 3, x + 2, y + 4, RED)
    c.rect(x + 9, y + 3, x + 10, y + 4, RED)
    c.hline(x + 3, x + 8, y + 6, INK)                        # tusked grin
    c.put(x + 4, y + 7, INK)
    c.put(x + 7, y + 7, INK)
    c.line(x + 6, y - 1, x + 5, y + 9, INK)                  # the break
    c.put(x + 6, y + 1, GREEN)
    c.put(x + 5, y + 5, GREEN)
    c.put(x + 5, y + 7, GREEN_DEEP)

    # chunky horns curling up off the brow
    c.rect(x + 0, y - 2, x + 1, y - 1, RED_DARK)
    c.rect(x - 1, y - 4, x + 0, y - 3, RED_DARK)
    c.put(x - 1, y - 5, RED)
    c.rect(x + 10, y - 2, x + 11, y - 1, RED_DARK)
    c.rect(x + 11, y - 4, x + 12, y - 3, RED_DARK)
    c.put(x + 12, y - 5, RED)


def guardian_frame(f):
    dy = GUARD_DY[f]
    ad = GUARD_AXE[f]
    c = Canvas(96, 96)

    # --- back arm: GREY mail sleeve reads as a limb against the INK plate --
    c.rect(26, 40 + dy, 34, 58 + dy, GREY)                   # sleeve
    c.hline(26, 34, 58 + dy, INK)
    c.hline(27, 33, 48 + dy, INK)                            # elbow crease
    c.rect(24, 58 + dy, 34, 68 + dy, INK)                    # back gauntlet
    gband(c, [(y, 25, 33) for y in range(59 + dy, 68 + dy)], pitch=4)
    c.hline(25, 33, 58 + dy, GREY)
    c.vline(24, 59 + dy, 67 + dy, GREY)
    c.put(29, 63 + dy, GREEN_DEEP)

    # --- legs: GREY thighs between INK tassets and INK shin plate ---------
    c.rect(36, 64, 44, 78, GREY)                             # back thigh
    c.rect(48, 64, 56, 78, GREY)                             # front thigh
    c.hline(36, 44, 78, INK)
    c.hline(48, 56, 78, INK)
    gband(c, [(y, 35, 45) for y in range(74, 89)])           # back shin plate
    gband(c, [(y, 47, 57) for y in range(74, 89)])           # front shin plate
    gband(c, [(88, 31, 45), (89, 31, 45), (90, 31, 45), (91, 32, 45)], pitch=4)
    gband(c, [(88, 47, 61), (89, 47, 62), (90, 47, 62), (91, 48, 61)], pitch=4)
    c.vline(47, 74, 88, GREY)                                # near shin edge
    c.rect(47, 74, 57, 77, GREY)                             # near knee plate
    c.hline(48, 56, 76, INK)
    c.put(52, 75, GREEN)
    c.hline(36, 44, 75, GREY)                                # far knee, flatter
    c.hline(32, 44, 89, GREY)                                # boot lips
    c.hline(48, 60, 89, GREY)

    # --- tassets and waist -------------------------------------------------
    gband(c, [(53 + dy, 35, 45), (54 + dy, 34, 45)]
          + [(y, 33, 45) for y in range(55 + dy, 68)])       # back tasset
    gband(c, [(53 + dy, 47, 57), (54 + dy, 47, 58)]
          + [(y, 47, 59) for y in range(55 + dy, 68)])       # front tasset
    c.vline(47, 54 + dy, 67, GREY)                           # lit inner edge
    c.rect(40, 46 + dy, 52, 53 + dy, GREY)                   # waist joint
    c.hline(40, 52, 53 + dy, INK)
    c.rect(43, 46 + dy, 48, 52 + dy, INK)                    # buckle
    c.rect(44, 47 + dy, 47, 51 + dy, GREY)                   # lit buckle face
    c.hline(44, 47, 51 + dy, INK)
    c.put(45, 49 + dy, GREEN)

    # --- circuit traces carried down over the hips and thighs.  This whole
    # --- band used to be unlit armour with a single GREEN pixel on it.
    for tx in (39, 51):
        c.vline(tx, 55 + dy, 77, GREEN_DEEP)                 # spine of the trace
        c.hline(tx, tx + 4, 58 + dy, GREEN_DEEP)             # branch across the
        c.vline(tx + 4, 58 + dy, 66, GREEN_DEEP)             # plate
        c.hline(tx - 2, tx, 70, GREEN_DEEP)                  # and onto the thigh
        c.vline(tx - 2, 70, 76, GREEN_DEEP)
        c.put(tx, 56 + dy, GREEN)                            # nodes
        c.put(tx + 4, 62 + dy, GREEN)
        c.put(tx - 2, 74, GREEN)

    # --- chest -------------------------------------------------------------
    gplate(c, G_CHEST, dy)
    gseam(c, G_CHEST, {31, 35, 39, 43}, dy)                  # lamellar chest bands
    c.rect(41, 42 + dy, 51, 45 + dy, GREY)                   # exposed ab joint
    c.hline(41, 51, 45 + dy, INK)
    c.line(42, 31 + dy, 45, 36 + dy, GREY)                   # pectoral seams
    c.line(51, 31 + dy, 48, 36 + dy, GREY)
    c.vline(46, 32 + dy, 41 + dy, GREEN_DEEP)                # circuit spine
    c.put(46, 33 + dy, GREEN)
    c.rect(44, 37 + dy, 48, 40 + dy, INK)                    # core node
    c.rect(45, 38 + dy, 47, 39 + dy, GREEN)
    c.hline(37, 43, 35 + dy, GREEN_DEEP)
    c.hline(49, 55, 35 + dy, GREEN_DEEP)

    # --- gorget and helm ---------------------------------------------------
    c.rect(42, 25 + dy, 52, 30 + dy, GREY)
    c.hline(42, 52, 30 + dy, INK)
    gplate(c, G_HELM, dy)
    c.rect(45, 4 + dy, 49, 10 + dy, INK)                     # crest fin
    c.hline(46, 48, 4 + dy, GREY)
    c.vline(47, 5 + dy, 9 + dy, GREEN_DEEP)
    c.rect(48, 14 + dy, 55, 17 + dy, GREEN_DEEP)             # visor slit
    c.rect(49, 15 + dy, 55, 16 + dy, GREEN)
    c.hline(41, 55, 19 + dy, GREY)                           # neck-guard flare
    c.hline(39, 56, 22 + dy, GREY)
    c.hline(39, 56, 23 + dy, INK)
    c.put(53, 12 + dy, GREY)

    # --- pauldrons over the shoulders --------------------------------------
    gplate(c, G_PAUL_BACK, dy)
    gplate(c, G_PAUL_FRONT, dy)
    gseam(c, G_PAUL_BACK, {29, 34}, dy)                      # lamellar banding
    gseam(c, G_PAUL_FRONT, {29, 34}, dy)
    c.hline(56, 65, 28 + dy, GREEN_DEEP)
    c.put(61, 29 + dy, GREEN)
    guard_shoulder_mask(c, 26, 28 + dy)

    # --- front arm and the axe it holds -------------------------------------
    grip_y = 60
    gx = haft_x(grip_y, ad)
    c.rect(58, 40 + dy, 66, 56 + dy, GREY)                   # sleeve
    c.hline(58, 66, 56 + dy, INK)
    c.hline(59, 65, 48 + dy, INK)                            # elbow crease
    c.thick(62, 54 + dy, gx, grip_y, 7, INK)                 # armoured forearm
    c.thick(62, 54 + dy, gx, grip_y, 5, GREY)                # mail core - INK
    #                                                          on INK is invisible
    c.line(61, 51 + dy, gx - 1, grip_y - 3, GREY)            # top-facing rim

    guard_axe(c, ad)

    c.rect(gx - 5, grip_y - 4, gx + 4, grip_y + 4, INK)      # fist on the haft
    c.rect(gx - 4, grip_y - 4, gx + 3, grip_y + 2, GREY)     # lit knuckle plate
    c.hline(gx - 4, gx + 3, grip_y + 2, INK)                 # underside
    c.dither(gx - 4, grip_y + 1, gx + 3, grip_y + 1, GREY, INK, phase=1)
    c.vline(gx + 4, grip_y - 3, grip_y + 3, GREY)
    c.hline(gx - 4, gx + 3, grip_y - 1, INK)                 # knuckle ridge seam
    c.put(gx, grip_y + 2, GREEN)

    c.outline()

    # spirit light shed by the axe edge and the broken mask
    c.put(93, 24 + ad, GREEN)
    c.put(92, 40 + ad, GREEN_DEEP)
    c.put(24, 27 + dy - (f % 2), GREEN_DEEP)
    return c


# ------------------------------------------------------------------- build
if __name__ == "__main__":
    finish([worm_frame(f) for f in range(4)], "worm")
    finish([drone_frame(f) for f in range(4)], "drone")
    finish([husk_frame(f) for f in range(4)], "husk")
    finish([guardian_frame(f) for f in range(4)], "guardian")
