"""
Cybershinigami - UI / inventory icon sheet.

Emits a single horizontal strip of ten 32x32 icons (320x32) plus an 8x
nearest-neighbour preview.  Flat cel-shaded pixel art: hard edges, no
anti-aliasing, no gradients, 1px INK contour on every silhouette.

Order: katana, wakizashi, shuriken, kunai, potion_red, potion_green,
       mask, soul_byte, key_shard, scroll
"""

from collections import deque

from PIL import Image

# --------------------------------------------------------------- palette ---
VOID       = (0, 0, 0)          # transparent / background
INK        = (10, 14, 31)       # contours, dark cloth
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

CELL = 32          # one icon cell, px
MARGIN = 1         # reserved on every side so the INK contour always fits


# ---------------------------------------------------------------- canvas ---
class Cell:
    """A 32x32 grid of RGB tuples; None means transparent."""

    def __init__(self, size=CELL):
        self.size = size
        self.g = [[None] * size for _ in range(size)]

    # -- primitives ---------------------------------------------------------
    def put(self, x, y, c):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.g[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.g[y][x]
        return None

    def row(self, y, x0, x1, c):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.put(x, y, c)

    def col(self, x, y0, y1, c):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.put(x, y, c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.row(y, x0, x1, c)

    def disc(self, cx, cy, r, c):
        rr = r * r
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= rr:
                    self.put(x, y, c)

    def sym(self, y, hw, c, cx=16):
        """Horizontal run symmetric about cx."""
        self.row(y, cx - hw, cx + hw, c)

    # -- composite ----------------------------------------------------------
    def feature(self, pixels, c):
        """Paint an inner detail with a 1px INK halo.

        The halo is only laid down where the canvas is already solid, so a
        detail never bleeds outside the silhouette it sits on.
        """
        pset = set(pixels)
        for (x, y) in pixels:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (x + dx, y + dy)
                    if n not in pset and self.get(*n) is not None:
                        self.put(n[0], n[1], INK)
        for (x, y) in pixels:
            self.put(x, y, c)

    # -- finishing ----------------------------------------------------------
    def bbox(self):
        xs = [x for y in range(self.size) for x in range(self.size)
              if self.g[y][x] is not None]
        ys = [y for y in range(self.size) for x in range(self.size)
              if self.g[y][x] is not None]
        return min(xs), min(ys), max(xs), max(ys)

    def center(self):
        """Recentre the drawn pixels inside the cell."""
        x0, y0, x1, y1 = self.bbox()
        w, h = x1 - x0 + 1, y1 - y0 + 1
        limit = self.size - 2 * MARGIN
        assert w <= limit and h <= limit, f"icon {w}x{h} leaves no room for the contour"
        dx = (self.size - w) // 2 - x0
        dy = (self.size - h) // 2 - y0
        if dx or dy:
            ng = [[None] * self.size for _ in range(self.size)]
            for y in range(self.size):
                for x in range(self.size):
                    if self.g[y][x] is not None:
                        ng[y + dy][x + dx] = self.g[y][x]
            self.g = ng

    def outline(self):
        """1px INK contour around the exterior silhouette only.

        Interior holes (the kunai ring) are flood-excluded so they stay open.
        """
        n = self.size
        seen = [[False] * n for _ in range(n)]
        q = deque()
        for i in range(n):
            for (x, y) in ((i, 0), (i, n - 1), (0, i), (n - 1, i)):
                if self.g[y][x] is None and not seen[y][x]:
                    seen[y][x] = True
                    q.append((x, y))
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < n and 0 <= ny < n and not seen[ny][nx] \
                        and self.g[ny][nx] is None:
                    seen[ny][nx] = True
                    q.append((nx, ny))

        edge = []
        for y in range(n):
            for x in range(n):
                if not seen[y][x]:
                    continue
                touching = any(
                    0 <= x + dx < n and 0 <= y + dy < n
                    and self.g[y + dy][x + dx] is not None
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                )
                if touching:
                    edge.append((x, y))
        for (x, y) in edge:
            self.g[y][x] = INK

    def seal(self):
        """Close 1px transparent slots that poke into the silhouette.

        Where two strokes meet at an angle (the tsuba crossing the hilt, the
        horn joining the skull) the union can leave a single background pixel
        wedged inside the shape, which reads as a nick in the contour on a
        light UI background.  Any transparent pixel with three or more solid
        4-neighbours is filled with the dominant neighbour colour (INK breaks
        ties, since these slots sit inside the contour).

        Deliberately a single pass computed from a snapshot: cascading would
        eat genuine concave detail such as the crook between the horns.
        """
        n = self.size
        snap = [row[:] for row in self.g]
        for y in range(n):
            for x in range(n):
                if snap[y][x] is not None:
                    continue
                near = [snap[y + dy][x + dx]
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= x + dx < n and 0 <= y + dy < n
                        and snap[y + dy][x + dx] is not None]
                if len(near) < 3:
                    continue
                best = max(set(near), key=lambda c: (near.count(c), c == INK))
                self.g[y][x] = best

    def finish(self):
        self.center()
        self.outline()
        self.seal()
        return self


# ------------------------------------------------------------ 1. katana ----
def sword(c, bx, by, blade_len, blade_w, curve_step, hilt_len, hilt_w, guard):
    """Shared blade construction for katana and wakizashi.

    Blade climbs up-right one row per step; each step lays a horizontal run so
    the diagonal band stays solid.  Spine (up-left) is GREY, cutting edge
    (down-right) carries the GREEN hamon.  `curve_step` controls the sori: the
    blade drifts down off the straight 45 line as it nears the tip.
    """
    # Collect the steps before drawing.  Where the sori kicks in two steps land
    # on the same row, and the merged run reaches a pixel further right than the
    # row above it - that 1px bump is the jog that shows up in the hamon near
    # the tip, so the cutting edge is clamped to never retreat going up.
    band = {}
    for t in range(blade_len):
        cx = bx + t
        cy = by - t + min(2, t // curve_step)
        left = blade_len - 1 - t
        w = blade_w if left >= 3 else left + 1      # kissaki taper into a point
        x0, x1 = cx, cx + w - 1
        if cy in band:
            x0, x1 = min(x0, band[cy][0]), max(x1, band[cy][1])
        band[cy] = (x0, x1)

    cap = None
    for cy in sorted(band):                         # top of the blade first
        x0, x1 = band[cy]
        band[cy] = (x0, x1 if cap is None else min(x1, cap))
        cap = band[cy][1]

    for cy, (x0, x1) in band.items():
        c.row(cy, x0, x1, GREY)
    for t in range(blade_len):                      # spine glint (top-facing)
        if blade_len // 3 <= t <= blade_len // 2:
            c.put(bx + t, by - t + min(2, t // curve_step), WHITE)
    for cy, (x0, x1) in band.items():
        if x1 > x0:
            c.put(x1, cy, GREEN)                    # hamon on the true edge

    # hilt: continues down-left from the blade base, INK with a BLUE_DEEP wrap
    hx, hy = bx - 1, by + 1
    for t in range(hilt_len):
        cx, cy = hx - t, hy + t
        c.row(cy, cx - hilt_w + 1, cx, INK)
        if t % 2 == 0:
            c.put(cx - 1, cy, BLUE_DEEP)

    # Tsuba: a bar perpendicular to the blade.  The guard is what makes the
    # silhouette read as a Japanese sword rather than a knife, so it has to be
    # a real crossguard, not a step at the blade base.
    #
    # It is drawn straight THROUGH the blade base rather than started beside
    # it: the hilt runs down-left while the perpendicular runs down-right, so
    # a wing begun off the blade diverges 2px per row and tears off into a
    # floating grey streak.  Passing through solid blade pixels welds both
    # wings by construction.  The bar is 2px thick because a 1px diagonal is
    # only 8-connected - `outline` would thread INK between its pixels and
    # dissolve it.  The habaki collar keeps the GREY guard from melting into
    # the GREY blade.
    bx0, bx1 = band[by]
    c.row(by, bx0, bx1, INK)                        # habaki collar
    for k in range(-guard, guard + 1):
        c.put(bx + k, by + k, GREY)
        c.put(bx + k - 1, by + k, GREY)


def icon_katana():
    c = Cell()
    sword(c, bx=11, by=19, blade_len=15, blade_w=4, curve_step=6,
          hilt_len=8, hilt_w=3, guard=3)
    return c.finish()


# --------------------------------------------------------- 2. wakizashi ----
def icon_wakizashi():
    c = Cell()
    # same construction, ~half the reach and one pixel fatter in the blade
    sword(c, bx=12, by=17, blade_len=9, blade_w=5, curve_step=5,
          hilt_len=5, hilt_w=3, guard=2)
    return c.finish()


# ---------------------------------------------------------- 3. shuriken ----
def icon_shuriken():
    c = Cell()
    cx, cy = 15, 15
    reach = 12

    def half(d):
        return max(0, 3 - d // 4)          # stepped taper 3,3,3,3,2,2,2,2,1,1,1,1,0

    # four arms, generated by rotating the +x arm 90 degrees at a time
    rot = ((1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0))
    for (ax, ay, bx_, by_) in rot:
        for d in range(reach + 1):
            h = half(d)
            for k in range(-h, h + 1):
                x = cx + ax * d + bx_ * k
                y = cy + ay * d + by_ * k
                c.put(x, y, GREY)
            # leading edge catches the light, outer half of the blade only
            if d >= 3:
                x = cx + ax * d + bx_ * (-h)
                y = cy + ay * d + by_ * (-h)
                c.put(x, y, CYAN_PALE)

    c.rect(cx - 1, cy - 1, cx + 1, cy + 1, INK)   # centre hole
    return c.finish()


# ------------------------------------------------------------- 4. kunai ----
def icon_kunai():
    c = Cell()
    cx = 16

    # leaf blade: diamond profile, widest low, tapering to a point at the top
    blade = {4: 0, 5: 0, 6: 1, 7: 1, 8: 2, 9: 2,
             10: 3, 11: 3, 12: 3, 13: 2, 14: 2, 15: 1}
    for y, hw in blade.items():
        c.sym(y, hw, GREY, cx)
    for y in range(6, 14):                       # centre ridge highlight
        c.put(cx, y, WHITE)

    # Grip is GREY, not INK: an INK grip is the same colour as the contour that
    # wraps it, so the whole handle vanishes into the silhouette.  The collar
    # and the cord wrap are the dark bands that break the grey up.
    c.rect(cx - 1, 17, cx + 1, 22, GREY)         # grip
    c.row(16, cx - 1, cx + 1, INK)               # collar under the blade
    c.row(19, cx - 1, cx + 1, INK)               # cord wrap

    # Ring pommel: open eye, INK inner contour, GREY annulus.  The eye is left
    # transparent rather than filled with INK so the ring actually reads as a
    # ring - `outline` only walks the exterior silhouette, so a hole survives.
    ry = 26
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            r2 = dx * dx + dy * dy
            if r2 <= 2:
                continue                         # open eye
            if r2 <= 5:
                c.put(cx + dx, ry + dy, INK)     # inner contour of the ring
            elif r2 <= 13:
                c.put(cx + dx, ry + dy, GREY)    # ring body
    return c.finish()


# ------------------------------------------------------ 5/6. potion vial ----
def flask(liquid, shade):
    c = Cell()
    c.disc(16, 20, 7, liquid)                    # round belly
    c.put(16, 27, None)                          # trim the 1px nub off the base
    c.rect(14, 9, 17, 14, GREY)                  # glass neck
    c.rect(13, 5, 18, 9, GREY)                   # cap
    c.row(5, 13, 18, WHITE)                      # top-facing edge, lighter

    # bottom-facing edges of the belly go dark
    for y in range(20, 28):
        run = [x for x in range(9, 24) if c.get(x, y) == liquid]
        if not run:
            continue
        if y >= 26:
            c.row(y, run[0], run[-1], shade)
        else:
            c.put(run[-1], y, shade)
            c.put(run[0], y, shade)

    # specular glint, upper-left
    c.put(12, 17, WHITE)
    c.put(13, 17, WHITE)
    c.put(12, 18, WHITE)
    return c.finish()


def icon_potion_red():
    return flask(RED, RED_DARK)


def icon_potion_green():
    return flask(GREEN, GREEN_DEEP)


# -------------------------------------------------------------- 7. mask ----
def icon_mask():
    c = Cell()
    cx = 16

    # swept-back horns (left drawn, right mirrored about cx)
    horn = {8: (9, 12), 7: (8, 11), 6: (7, 9), 5: (6, 8), 4: (5, 6), 3: (5, 5)}
    for y, (x0, x1) in horn.items():
        c.row(y, x0, x1, RED)
        c.put(x1, y, RED_DARK)                   # underside of the horn
        c.row(y, 2 * cx - x1, 2 * cx - x0, RED)
        c.put(2 * cx - x1, y, RED_DARK)

    # hannya face: broad brow tapering to a narrow chin
    face = {8: 5, 9: 6, 10: 7, 11: 8, 12: 8, 13: 8, 14: 8, 15: 8, 16: 7,
            17: 7, 18: 6, 19: 6, 20: 6, 21: 5, 22: 5, 23: 4, 24: 3, 25: 1}
    for y, hw in face.items():
        c.sym(y, hw, RED, cx)
        c.put(cx + hw, y, RED_DARK)              # shaded right cheek
        if y >= 24:
            c.sym(y, hw, RED_DARK, cx)           # jaw underside

    # glaring eye slits: thicker at the inner corner so the glare slants down
    eye = [(10, 15), (11, 15), (12, 15), (13, 15), (12, 16), (13, 16)]
    c.feature(eye, WHITE)
    c.feature([(2 * cx - x, y) for (x, y) in eye], WHITE)
    # the halo above each eye is the brow; lift its outer end for the scowl
    c.row(13, 9, 11, INK)
    c.row(13, 21, 23, INK)

    # third eye
    c.feature([(cx, 10), (cx - 1, 11), (cx, 11), (cx + 1, 11), (cx, 12)], CYAN)

    # fanged grin
    grin = [(x, 19) for x in range(12, 21)]
    grin += [(x, 20) for x in range(11, 22)]
    grin += [(x, 21) for x in range(12, 21)]
    grin += [(12, 22), (13, 22), (19, 22), (20, 22), (12, 23), (20, 23)]
    c.feature(grin, WHITE)
    c.row(20, 13, 19, INK)                       # bite line between the teeth
    for x in (14, 18):                           # tooth gaps, symmetric about cx
        c.put(x, 19, INK)
        c.put(x, 21, INK)
    return c.finish()


# --------------------------------------------------------- 8. soul_byte ----
def icon_soul_byte():
    c = Cell()
    cx = 16
    # Compact hitodama - smaller than the world VFX flame so the badge ring has
    # room.  Half-width per row, kept inside |dx| + |y - 16| <= 8 so the flame
    # and its contour never touch the diamond.
    flame = {8: 0, 9: 0, 10: 1, 11: 1, 12: 1, 13: 2, 14: 2, 15: 3,
             16: 3, 17: 4, 18: 4, 19: 4, 20: 4, 21: 3, 22: 2}
    for y, hw in flame.items():
        c.sym(y, hw, GREEN, cx)

    # bottom-facing edges darken
    for y, hw in flame.items():
        if y >= 17:
            c.put(cx + hw, y, GREEN_DEEP)
        if y >= 21:
            c.sym(y, hw, GREEN_DEEP, cx)

    # hot core, biased up inside the bulb
    for y, hw in ((16, 0), (17, 1), (18, 1), (19, 1), (20, 0)):
        c.sym(y, hw, WHITE, cx)

    # The flame has to carry its own contour: the CYAN ring below is a closed
    # loop, so `finish`'s exterior-only outline pass can never reach inside it.
    c.outline()

    # CYAN pixel-diamond.  The world VFX and the lantern use this same green
    # teardrop, so the pickup gets a UI badge around it and reads as inventory
    # rather than as something burning in the level.
    R = 12
    for k in range(-R, R + 1):
        d = R - abs(k)
        c.put(cx + k, 16 - d, CYAN)
        c.put(cx + k, 16 + d, CYAN)
    return c.finish()


# --------------------------------------------------------- 9. key_shard ----
def icon_key_shard():
    c = Cell()
    shard = {4: (18, 18), 5: (17, 19), 6: (16, 20), 7: (15, 21), 8: (14, 22),
             9: (13, 22), 10: (12, 22), 11: (11, 22), 12: (11, 21),
             13: (11, 21), 14: (11, 20), 15: (11, 20), 16: (11, 19),
             17: (12, 19), 18: (12, 18), 19: (12, 18), 20: (13, 17),
             21: (13, 17), 22: (13, 16), 23: (14, 16), 24: (14, 15),
             25: (14, 15), 26: (14, 14)}
    for y, (x0, x1) in shard.items():
        c.row(y, x0, x1, CYAN)

    # facet ridge runs crown to point; lit face left of it, shadow face right
    for y, (x0, x1) in shard.items():
        ridge = 18 - (y - 4) * 4 // 22
        for x in range(x0, min(ridge, x1) + 1):
            c.put(x, y, CYAN_PALE)               # lit facet
        if x1 - 1 >= ridge:
            c.put(x1, y, BLUE_MID)               # shaded facet
            if y >= 12:
                c.put(x1 - 1, y, BLUE_MID)
        if x0 <= ridge <= x1:
            c.put(ridge, y, WHITE)               # facet edge, unbroken
    for (x, y) in ((13, 13), (12, 14)):
        c.put(x, y, WHITE)                       # internal facet glint
    return c.finish()


# ------------------------------------------------------------ 10. scroll ----
def icon_scroll():
    c = Cell()
    # A hanging scroll: a GREY rod across the top with a round cap bulging past
    # each end, and the paper sheet hanging below it.
    #
    # Two earlier versions failed here.  A rectangle flanked by two vertical
    # bars read as a picture frame.  Replacing that with a white "paper
    # cylinder" plus two GREY end-cap discs failed differently: the cylinder's
    # own GREY edge line ran along the same row as the disc centres, so the
    # discs fused into one continuous grey band and stopped reading as circles
    # - the icon became a certificate with two clamps.  The rod bar is
    # therefore kept THINNER than the caps (3 rows against the caps' 7), which
    # is what lets their curve show above and below it.
    ROD_Y, CAP = 9, 3
    c.rect(9, 10, 22, 26, WHITE)                 # sheet hanging below the rod
    c.row(26, 9, 22, GREY)                       # bottom-facing edge of the sheet
    for ty in (14, 17):                          # ruled text, clear of the seal
        c.row(ty, 12, 19, GREY)

    c.rect(6, ROD_Y - 1, 25, ROD_Y + 1, GREY)    # rod bar, 3 rows
    for rx in (6, 25):                           # round caps, 7 rows: they bulge
        c.disc(rx, ROD_Y, CAP, GREY)

    # wax seal, sat well inside the sheet so it never breaks the contour
    seal = [(x, y) for y in range(20, 25) for x in range(14, 19)
            if (x - 16) ** 2 + (y - 22) ** 2 <= 4]
    c.feature(seal, GREEN)
    for (x, y) in seal:
        if y >= 23:                              # bottom-facing rows only
            c.put(x, y, GREEN_DEEP)
    return c.finish()


# ------------------------------------------------------------------ build ---
ICONS = [
    ("katana", icon_katana),
    ("wakizashi", icon_wakizashi),
    ("shuriken", icon_shuriken),
    ("kunai", icon_kunai),
    ("potion_red", icon_potion_red),
    ("potion_green", icon_potion_green),
    ("mask", icon_mask),
    ("soul_byte", icon_soul_byte),
    ("key_shard", icon_key_shard),
    ("scroll", icon_scroll),
]

w, h = CELL * len(ICONS), CELL
strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
px = strip.load()

for i, (name, build) in enumerate(ICONS):
    cell = build()
    ox = i * CELL
    for y in range(CELL):
        for x in range(CELL):
            c = cell.g[y][x]
            if c is not None:
                px[ox + x, y] = (c[0], c[1], c[2], 255)

strip.save("icons.png")
strip.resize((w * 8, h * 8), Image.NEAREST).save("icons_8x.png")   # preview

used = {px[x, y][:3] for x in range(w) for y in range(h) if px[x, y][3] > 0}
assert not (used - ALLOWED), f"off-palette: {used - ALLOWED}"
print(f"ok: icons.png  {len(ICONS)}f  {w}x{h}")
