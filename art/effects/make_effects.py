"""
Cybershinigami - combat VFX sprite generator.

Builds six horizontal sprite strips of flat cel-shaded pixel-art effects:
    slash_light   3f  64x64   fast katana cut arc          (green hamon light)
    slash_heavy   4f  96x96   two-handed cut + shards      (green hamon light)
    spin_slash    5f  96x96   360 degree blade ring        (cyan special)
    beam          4f  96x48   forward energy lance         (cyan tech)
    impact        4f  48x48   hit burst shards             (green)
    soul          4f  24x24   hitodama spirit flame        (green)

Rules obeyed everywhere: locked palette only, no anti-aliasing, no gradients,
hard 1px INK contour around every silhouette, fully transparent background.
"""

import math
from PIL import Image

# --------------------------------------------------------------- palette ---
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

# Concentric shading stacks: (inset_px, fraction_of_thickness, colour),
# ordered outer -> inner.  Inner entries overwrite outer ones, which gives
# crisp 1px rings on thin shapes and a fat hot core on thick ones.
LAY_BLADE = [(0.0, 1.00, GREEN_DEEP),   # acid-green sword cut
             (1.0, 0.80, GREEN),
             (2.0, 0.40, WHITE)]
LAY_RING  = [(0.0, 1.00, BLUE_MID),     # cyan special-move ring
             (1.0, 0.82, CYAN),
             (2.0, 0.45, CYAN_PALE)]
LAY_HOT   = [(0.0, 1.00, CYAN_PALE),    # white-hot spots welded onto the ring
             (0.8, 0.62, WHITE)]
# The fast cut is a thin band, and on a thin band a 1px INK contour eats both
# edges: LAY_BLADE's 0.40 white fraction drops the core below the 0.55px floor
# for most of the arc, which reads as an outlined worm rather than light.  This
# stack holds a white core wherever the half-width clears 1.2px.
LAY_LIT   = [(0.0, 1.00, GREEN_DEEP),
             (0.9, 0.70, GREEN),
             (1.9, 0.45, WHITE)]


# ------------------------------------------------------------- primitives ---
class Frame:
    """A single transparent RGB canvas; None means transparent."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def put(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None


def row(f, x0, x1, y, c):
    """Horizontal run of pixels, inclusive."""
    for x in range(int(x0), int(x1) + 1):
        f.put(x, y, c)


def rect(f, x0, y0, x1, y1, c):
    """Filled axis-aligned block, inclusive."""
    for y in range(int(y0), int(y1) + 1):
        row(f, x0, x1, y, c)


def shade(f, x, y, e, t, layers, dith=0.0):
    """Paint one pixel of a band, `e` px off the band centre, half-width `t`.

    Each layer is inset one pixel from the last so fat bands get crisp 1px
    rings, but an inset never eats more than 30% of the band - that keeps
    thin slivers reading as bright blade light instead of muddy dark edges.

    `dith` breaks the leading `dith` px of each inner ring into a 50%
    checkerboard, so body-to-core lands as grain rather than a hard step -
    the same treatment the player's colour bands get. The outermost layer is
    never dithered: it owns the silhouette, and holing it through would give
    the contour pass edges to trace inside the blade.
    """
    for i, (inset, frac, col) in enumerate(layers):
        lim = min(t - min(inset, t * 0.30), t * frac)
        if lim < 0.55:
            continue
        if e <= lim:
            if i and dith and e > lim - dith and (x + y) % 2:
                continue                   # let the outer ring show through
            f.put(x, y, col)


def outline(f, colour=INK):
    """Add a 1px contour on every transparent pixel touching the silhouette."""
    edge = []
    for y in range(f.h):
        for x in range(f.w):
            if f.px[y][x] is not None:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    if f.get(x + dx, y + dy) is not None:
                        edge.append((x, y))
                        break
                else:
                    continue
                break
    for x, y in edge:
        f.put(x, y, colour)


def taper(tmax, skew=1.0, power=0.55):
    """Thickness profile along an arc: 0 at both ends, `tmax` in the belly.

    skew > 1 pushes the fat part toward the leading end; power < 1 keeps the
    arc broad for longer and then snaps to a point.
    """
    def profile(u):
        uu = u ** skew
        return tmax * (math.sin(math.pi * uu) ** power)
    return profile


def arc(f, cx, cy, R, a0, span, thick, layers, rot=0.0, gaps=(), dith=0.0):
    """Curved blade band of radius R from angle a0 sweeping `span` degrees.

    Angles are degrees CCW with y pointing up on screen; `rot` rotates the
    whole arc about its centre (negative = clockwise, right end dips).
    """
    rr = math.radians(-rot)
    ca, sa = math.cos(rr), math.sin(rr)
    tmax = max(thick(i / 32.0) for i in range(33))
    lo, hi = R - tmax - 1.0, R + tmax + 1.0

    for y in range(f.h):
        for x in range(f.w):
            ux = x + 0.5 - cx
            uy = -(y + 0.5 - cy)          # flip to maths orientation
            dx = ux * ca - uy * sa        # un-rotate the sample point
            dy = ux * sa + uy * ca
            d = math.hypot(dx, dy)
            if d < lo or d > hi:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            da = (ang - a0) % 360.0
            if da > span:
                continue
            u = da / span
            if any(g0 <= u <= g1 for g0, g1 in gaps):
                continue
            t = thick(u)
            e = abs(d - R)
            if t < 0.4 or e > t:
                continue
            shade(f, x, y, e, t, layers, dith)


def shards(f, cx, cy, R, specs, layers, rot=0.0, dith=0.0):
    """Detached speed fragments: (radius offset, angle, span, thickness)."""
    for dR, a0, span, tmax in specs:
        arc(f, cx, cy, R + dR, a0, span, taper(tmax, power=0.5), layers, rot,
            dith=dith)


def disc(f, cx, cy, r, layers):
    """Filled circle; layers are (shrink_px, colour) outer -> inner."""
    rr = int(r) + 2
    for y in range(int(cy) - rr, int(cy) + rr + 1):
        for x in range(int(cx) - rr, int(cx) + rr + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            for shrink, col in layers:
                if d <= r - shrink:
                    f.put(x, y, col)


def spike(f, cx, cy, ang, r0, r1, w0, hot=0.0):
    """Tapered radiating shard from r0 to r1 along `ang` (degrees, y up)."""
    a = math.radians(ang)
    dirx, diry = math.cos(a), -math.sin(a)
    perpx, perpy = math.sin(a), math.cos(a)
    steps = max(4, int((r1 - r0) * 3))
    for i in range(steps + 1):
        s = i / steps
        r = r0 + (r1 - r0) * s
        w = w0 * (1.0 - s) ** 0.7
        px_, py_ = cx + dirx * r, cy + diry * r
        col = GREEN if s < 0.62 else GREEN_DEEP
        k = 0.0
        while k <= max(w, 0.0):
            for sgn in (1, -1):
                x = px_ + perpx * k * sgn
                y = py_ + perpy * k * sgn
                f.put(round(x), round(y), WHITE if s < hot and k < w - 0.9 else col)
            k += 0.5


def lance(f, x0, x1, cy, hmax, sharp=1.7):
    """Horizontal energy spindle: thin tail, fat belly, needle tip at x1.

    Rows thinner than a pixel collapse to a single centre pixel so the tail
    and the needle point stay connected to the body.
    """
    for x in range(int(x0), int(x1) + 1):
        s = (x - x0) / float(x1 - x0)
        h = hmax * (math.sin(math.pi * (s ** sharp)) ** 0.7)
        if h < 0.7:
            f.put(x, cy, CYAN_PALE if s > 0.5 else CYAN)
            continue
        for y in range(int(cy - h - 1), int(cy + h + 2)):
            e = abs(y - cy)
            if e > h:
                continue
            if e <= min(h - 2.0, h * 0.40):
                col = WHITE              # hot core
            elif e <= h - 1.0:
                col = CYAN               # body
            elif y < cy:
                col = CYAN_PALE          # top-facing edge: lighter
            elif y > cy:
                col = BLUE_MID           # bottom-facing edge: darker
            else:
                col = CYAN
            f.put(x, y, col)


def spark(f, x, y, r, core, outer):
    """Small diamond particle."""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if abs(dx) + abs(dy) <= r:
                f.put(x + dx, y + dy, outer)
    f.put(x, y, core)


# ------------------------------------------------------------------ save ---
def save(name, frames):
    """Compose frames into a strip, verify palette, then write 1x + 8x preview."""
    fw, fh = frames[0].w, frames[0].h
    w, h = fw * len(frames), fh
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = strip.load()
    for i, f in enumerate(frames):
        for y in range(fh):
            for x in range(fw):
                c = f.px[y][x]
                if c is not None:
                    px[i * fw + x, y] = (c[0], c[1], c[2], 255)

    # Gate the write: an off-palette build must not leave art on disk, or a
    # crashed run silently ships the bad PNG that was already written.
    used = {px[x, y][:3] for x in range(w) for y in range(h) if px[x, y][3] > 0}
    assert not (used - ALLOWED), f"off-palette: {used - ALLOWED}"

    strip.save(f"{name}.png")
    strip.resize((w * 8, h * 8), Image.NEAREST).save(f"{name}_8x.png")  # preview
    print(f"ok: {name}.png  {len(frames)}f  {w}x{h}")


# ====================================================== 1. slash_light =====
# Fast one-handed katana cut. Tilted crescent, convex side leading up-right.
# Sliver -> full blade arc -> thin fragmented afterimage.
def build_slash_light():
    CX, CY, R, ROT = 30, 52, 27, -16
    A0, SPAN = 20, 140
    DITH = 0.55                    # grain on the body->core step, player profile
    frames = []

    # Thickness: the belly carries ~2px more body than the contour so GREEN and
    # the WHITE core survive the outline.  The low `power` keeps the band broad
    # along almost the whole sweep instead of pinching to contour a few px in
    # from each tip - that pinch is what made the blade read as a worm.

    # f0 - opening sliver: only the leading (right-hand) end of the sweep.
    f = Frame(64, 64)
    arc(f, CX, CY, R, A0, 58, taper(3.2, skew=1.35, power=0.42), LAY_LIT, ROT,
        dith=DITH)
    outline(f)
    frames.append(f)

    # f1 - the cut fully open: broad belly, points at both tips.
    f = Frame(64, 64)
    arc(f, CX, CY, R, A0, SPAN, taper(4.6, skew=1.15, power=0.34), LAY_LIT, ROT,
        dith=DITH)
    outline(f)
    frames.append(f)

    # f2 - thinning afterimage: the leading tip is already gone, what is left
    # is a broken ribbon with a few chips drifting off the outside of the path.
    f = Frame(64, 64)
    # Thinner than the full cut - it is dissipating - but still wide enough to
    # hold a core.  Much past this the apex segment stops reading as a ribbon
    # fragment and turns into a solid wedge.
    arc(f, CX, CY, R + 2, A0 + 14, SPAN - 28, taper(2.3, power=0.32), LAY_LIT, ROT,
        gaps=((0.28, 0.38), (0.64, 0.74)), dith=DITH)
    shards(f, CX, CY, R + 2,
           [(0, A0 + 2, 9, 1.6), (2, A0 + 134, 8, 1.5), (-5, A0 + 60, 7, 1.4)],
           LAY_LIT, ROT, dith=DITH)
    outline(f)
    frames.append(f)

    save("slash_light", frames)


# ====================================================== 2. slash_heavy =====
# Two-handed cut: same construction, far longer and thicker, with detached
# speed shards trailing the left (tail) end of the sweep.
def build_slash_heavy():
    CX, CY, R, ROT = 40, 74, 42, -14
    A0, SPAN = 16, 150
    # The heavy cut is the widest blade band in the set, so its colour steps
    # are the most visible flat edges anywhere in the effects. DITH breaks
    # them into the same checkerboard the player's hair uses.
    DITH = 0.55
    # Shards ride the tail (left) half of the sweep; radii are kept inside the
    # frame because that side of the arc already runs close to the edge.
    TRAIL = [(8, 132, 12, 2.2), (4, 116, 10, 1.8),
             (-7, 126, 12, 1.6), (10, 130, 8, 1.5)]
    frames = []

    # f0 - wind-up sliver at the leading edge.
    f = Frame(96, 96)
    arc(f, CX, CY, R, A0, 58, taper(2.6, skew=1.4), LAY_BLADE, ROT, dith=DITH)
    outline(f)
    frames.append(f)

    # f1 - full cut at maximum weight, big white-hot core.
    f = Frame(96, 96)
    arc(f, CX, CY, R, A0, SPAN, taper(8.0, skew=1.1, power=0.45), LAY_BLADE, ROT,
        dith=DITH)
    outline(f)
    frames.append(f)

    # f2 - arc expands and thins, shards tear off the tail.
    f = Frame(96, 96)
    arc(f, CX, CY, R + 3, A0 - 1, SPAN - 6, taper(5.4, skew=1.05, power=0.45),
        LAY_BLADE, ROT, dith=DITH)
    shards(f, CX, CY, R + 3, TRAIL, LAY_BLADE, ROT, dith=DITH)
    outline(f)
    frames.append(f)

    # f3 - breaking apart: the ribbon survives in two long pieces, the tail
    # shards keep flying outward.
    f = Frame(96, 96)
    arc(f, CX, CY, R + 7, A0 + 6, SPAN - 20, taper(3.4, power=0.30), LAY_BLADE, ROT,
        gaps=((0.40, 0.50),), dith=DITH)
    shards(f, CX, CY, R + 7,
           [(dR + 2, a - 6, sp, tk * 0.8) for dR, a, sp, tk in TRAIL],
           LAY_BLADE, ROT, dith=DITH)
    outline(f)
    frames.append(f)

    save("slash_heavy", frames)


# ======================================================= 3. spin_slash =====
# Special move: a 360 degree blade ring that grows out of a short arc, closes
# into a full circle, then shatters. Cyan reads cooler than the green cuts.
def build_spin_slash():
    CX, CY = 48, 48
    DITH = 0.55                       # grain on every ring step, as above

    def hotspots(f, R, angles, tmax, rot=0):
        for a in angles:
            arc(f, CX, CY, R, a, 13, taper(tmax, power=0.4), LAY_HOT, rot,
                dith=DITH)

    frames = []

    # f0 - the spin begins: a short arc behind the character.
    f = Frame(96, 96)
    arc(f, CX, CY, 22, 200, 100, taper(2.6, skew=1.3), LAY_RING, dith=DITH)
    hotspots(f, 22, [268], 2.2)
    outline(f)
    frames.append(f)

    # f1 - half revolution, wider and heavier.
    f = Frame(96, 96)
    arc(f, CX, CY, 27, 170, 190, taper(3.6, skew=1.2, power=0.5), LAY_RING,
        dith=DITH)
    hotspots(f, 27, [250, 320], 3.0)
    outline(f)
    frames.append(f)

    # f2 - almost closed, only a small mouth left open.
    f = Frame(96, 96)
    arc(f, CX, CY, 32, 140, 300, taper(4.6, skew=1.1, power=0.4), LAY_RING,
        dith=DITH)
    hotspots(f, 32, [200, 300, 30], 3.8)
    outline(f)
    frames.append(f)

    # f3 - complete ring at full extension.
    f = Frame(96, 96)
    arc(f, CX, CY, 37, 0, 360, lambda u: 4.0, LAY_RING, dith=DITH)
    hotspots(f, 37, [15, 105, 195, 285], 3.6)
    outline(f)
    frames.append(f)

    # f4 - the ring breaks apart and flies outward.
    f = Frame(96, 96)
    arc(f, CX, CY, 42, 0, 360, lambda u: 2.4, LAY_RING,
        gaps=((0.05, 0.13), (0.28, 0.36), (0.53, 0.61), (0.78, 0.86)), dith=DITH)
    for dR, a, sp in [(4, 40, 14), (-5, 130, 12), (5, 215, 13), (-4, 305, 11)]:
        arc(f, CX, CY, 42 + dR, a, sp, taper(1.6, power=0.4), LAY_RING,
            dith=DITH)
    outline(f)
    frames.append(f)

    save("spin_slash", frames)


# ============================================================= 4. beam =====
# "Packet Injection": a lance of light fired to the right. Charge dot, two
# travel frames, then dissipation. Trailing particles behind the tail.
def build_beam():
    CY = 24
    frames = []

    # f0 - charge-up: a compact hot dot with converging flare spikes.
    f = Frame(96, 48)
    disc(f, 16, CY, 5.0, [(0.0, BLUE_MID), (1.0, CYAN), (2.8, WHITE)])
    for dx, dy in ((7, 0), (-7, 0), (0, 7), (0, -7),
                   (5, 5), (-5, 5), (5, -5), (-5, -5)):
        f.put(16 + dx, CY + dy, CYAN_PALE)
    for x, y in ((26, 18), (27, 30), (6, 20), (5, 29)):
        spark(f, x, y, 1, CYAN_PALE, CYAN)
    outline(f)
    frames.append(f)

    # f1 - lance forms and starts travelling.
    f = Frame(96, 48)
    lance(f, 6, 64, CY, 5.2)
    for dx, dy in ((-4, -4), (-4, 4), (-9, -3), (-9, 3)):   # head flare chevrons
        f.put(64 + dx, CY + dy, CYAN_PALE)
    for x, y, r in ((3, 18, 1), (2, 30, 1), (9, 14, 0), (8, 34, 0)):
        spark(f, x, y, r, CYAN_PALE, CYAN)
    outline(f)
    frames.append(f)

    # f2 - fully extended, driving off the right of the frame.
    f = Frame(96, 48)
    lance(f, 20, 92, CY, 6.0)
    for dx, dy in ((-5, -5), (-5, 5), (-11, -4), (-11, 4)):
        f.put(92 + dx, CY + dy, CYAN_PALE)
    for x, y, r in ((15, 17, 1), (13, 31, 1), (8, 21, 0), (6, 27, 0), (19, 12, 0)):
        spark(f, x, y, r, CYAN_PALE, CYAN)
    outline(f)
    frames.append(f)

    # f3 - dissipation: the lance breaks into thin segments and motes.
    f = Frame(96, 48)
    lance(f, 46, 78, CY, 2.8)
    lance(f, 82, 93, CY, 1.8)
    lance(f, 28, 40, CY, 1.8)
    for x, y, r in ((20, 18, 1), (34, 32, 1), (52, 14, 1), (66, 34, 1),
                    (80, 16, 0), (44, 36, 0), (14, 26, 0), (90, 31, 0)):
        spark(f, x, y, r, CYAN_PALE, CYAN)
    outline(f)
    frames.append(f)

    save("beam", frames)


# =========================================================== 5. impact =====
# Hit burst: shards radiating from a white core, expanding and thinning.
def build_impact():
    CX, CY = 24, 24
    ANG = [12, 54, 98, 141, 187, 229, 272, 318]
    LONG = [1.00, 0.74, 1.04, 0.82, 0.96, 0.72, 1.04, 0.80]
    # (inner radius, outer radius, base width, hot fraction, green r, white r)
    # Outer radius stays under 21 so shard tips plus contour clear the frame.
    #
    # The core radii are given directly instead of as a shrink off the green
    # disc: `disc` lights a pixel at distance d <= r, and the four pixels
    # nearest the centre sit at d = 0.707, so any white radius under that
    # renders nothing and leaves an INK-filled hole where the hit is hottest.
    # Every frame keeps a white radius >= 1.0 - an impact is brightest in the
    # middle.  The inner shard radius is also held close to the green core so
    # the shards stay welded to it; a wide gap there is what the contour pass
    # floods with INK to make the black-hole centre.
    STEP = [(0.0, 8.0, 2.6, 0.45, 5.0, 3.4),
            (2.2, 14.5, 2.4, 0.30, 4.2, 2.6),
            (4.0, 18.5, 1.7, 0.15, 3.2, 1.8),
            (11.0, 20.5, 1.3, 0.00, 2.6, 1.6)]
    frames = []

    for i, (r0, r1, w0, hot, rg, rw) in enumerate(STEP):
        f = Frame(48, 48)
        for a, lg in zip(ANG, LONG):
            if i == 3:
                lg = 0.55 + 0.45 * lg      # last frame evens out into a ring
            spike(f, CX, CY, a, r0 * lg, r1 * lg, w0 * lg, hot)
        # core last, so it always overwrites the shard bases it sits under
        disc(f, CX, CY, rg, [(0.0, GREEN)])
        disc(f, CX, CY, rw, [(0.0, WHITE)])
        outline(f)
        frames.append(f)

    save("impact", frames)


# ============================================================= 6. soul =====
# Hitodama: a spirit flame dropped as currency. Round white-cored body, a
# wavering flame tip, and a GREEN_DEEP tail that drips off the bottom.
def build_soul():
    # Teardrop silhouette as half-widths per row, pointed tip at the top and a
    # round base at the bottom. Trimming rows off the top makes it flicker.
    BODY = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 3, 2]
    CORE = [0, 1, 1, 1, 0]                  # hot white core, sits above the base
    CX = 12
    # per-frame: bob, rows trimmed off the tip, tip lean, wisp x-offsets,
    # droplet x-offset. The wisp never falls straight down - it wanders.
    STATE = [(0, 0, -1, [0, -1, -1], -2),
             (-1, 0, 0, [0, 0, 1, 1], 1),
             (0, 2, 1, [0, 1], 1),
             (1, 1, 0, [0, -1, 0], -1)]
    frames = []

    for bob, trim, wig, wisp, drop in STATE:
        f = Frame(24, 24)
        base = 15 + bob                      # y of the bottom row of the body
        rows = BODY[:3] + BODY[3 + trim:]    # shorten at the neck, keep the point
        top = base - len(rows) + 1

        # body: flat GREEN fill, leaning toward the tip
        for j, hw in enumerate(rows):
            y = top + j
            k = 1.0 - j / float(len(rows) - 1)          # 1 at the tip, 0 at base
            xo = CX + round(wig * k * k * 2)            # lean lives in the tip
            row(f, xo - hw, xo + hw, y, GREEN)

        # bottom-facing rim of the base reads darker
        for j in (len(rows) - 2, len(rows) - 1):
            row(f, CX - rows[j], CX + rows[j], top + j, GREEN_DEEP)
        f.put(CX - rows[-3], base - 2, GREEN_DEEP)
        f.put(CX + rows[-3], base - 2, GREEN_DEEP)

        # hot core, biased up and to the left inside the bulb
        for j, hw in enumerate(CORE):
            row(f, CX - 1 - hw, CX - 1 + hw, base - 6 + j, WHITE)

        # tail: a thin wisp dripping off the base, then a detached droplet
        for i, dx in enumerate(wisp):
            f.put(CX + dx, base + 1 + i, GREEN_DEEP)
        f.put(CX + drop, base + len(wisp) + 3, GREEN_DEEP)

        outline(f)
        frames.append(f)

    save("soul", frames)


# ============================================================== driver =====
if __name__ == "__main__":
    build_slash_light()
    build_slash_heavy()
    build_spin_slash()
    build_beam()
    build_impact()
    build_soul()
