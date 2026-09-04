"""World objects for Cybershinigami: save shrine, fast-travel torii,
guardian statues, hanging spirit lantern.

Every sprite is built the same three ways, so the whole set stays coherent:
  1. paint the solid structure using only the locked palette
  2. detail_pass() adds the 1px INK contour and top/bottom edge shading
  3. paint glow elements (scanline, motes, portal shimmer) on top -- drawn
     after the contour so free-floating spirit light never picks up an
     outline and reads as pure emitted light

Run: python make_objects.py  ->  <name>.png + <name>_8x.png previews
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


class Pen:
    """Frame-local drawing surface. All coordinates are relative to the
    frame's left edge, so every sprite is authored as if it owned 0,0."""

    def __init__(self, px, ox, w, h):
        self.px, self.ox, self.w, self.h = px, ox, w, h

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[self.ox + x, y] = (*c, 255)

    def clear(self, x, y):
        """Knock a pixel out of the silhouette -- used for chipped stone,
        so the contour pass traces the damage instead of a clean edge."""
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[self.ox + x, y] = (0, 0, 0, 0)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, c)

    def row(self, y, x0, x1, c):
        self.rect(x0, y, x1, y, c)

    def col(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def rows(self, table, c):
        """table: [(y, x0, x1), ...] -- the readable way to author a curve."""
        for y, x0, x1 in table:
            self.row(y, x0, x1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def get(self, x, y):
        """Read a pixel back as RGBA. Shading passes that run after the
        contour need this to tell stone from seam from empty space."""
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[self.ox + x, y]
        return (0, 0, 0, 0)

    def mote(self, x, y, big=True):
        """Spirit ember: bright core, dim halo. Glow pass only."""
        self.put(x, y, GREEN)
        if big:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.put(x + dx, y + dy, GREEN_DEEP)

    # ------------------------------------------------------------ dithering
    # The player sprite softens every colour step with a 2px checkerboard on
    # the (x + y) parity lattice -- roughly 2.4% of its lit pixels. The world
    # assets stepped straight from tone to tone, so they read flatter than the
    # hero standing in front of them. These put the same grain on a boundary.

    def dith(self, x, y, c, phase=0, thin=None):
        """One cell of a 2px checkerboard -- a 50% screen.

        A transition needs both of its ranks: one dithered line sitting
        between two solid fields is a dotted line, and it takes two adjacent
        ranks in opposite parity to actually read as a checkerboard.

        `thin` is the coordinate along the band's own axis (y for an upright
        band, x for a flat one). Passing it drops every other pair of cells,
        halving coverage while leaving the checker intact in the pairs that
        survive. Both ranks must be thinned on the same axis or they stop
        interlocking and the band falls apart into speckle."""
        if (x + y) % 2 != phase:
            return
        if thin is not None and (thin // 2) % 2:
            return
        self.put(x, y, c)

    def dith_row(self, y, x0, x1, c, phase=0, thin=False):
        for x in range(x0, x1 + 1):
            self.dith(x, y, c, phase, x if thin else None)

    def dith_col(self, x, y0, y1, c, phase=0, thin=False):
        for y in range(y0, y1 + 1):
            self.dith(x, y, c, phase, y if thin else None)


# ---------------------------------------------------------------- detail pass
# Stone has no lighter grey in the palette, so top-facing stone catches
# CYAN_PALE -- it doubles as the spirit-light rim the statues call for.
LIGHT = {GREY: CYAN_PALE, INK: GREY, RED_DARK: RED, GREEN_DEEP: GREEN,
         BLUE_DEEP: BLUE_MID, BLUE_MID: CYAN, CYAN: CYAN_PALE}
SHADE = {GREY: INK, RED: RED_DARK, CYAN_PALE: CYAN, CYAN: BLUE_MID,
         GREEN: GREEN_DEEP, WHITE: GREY, BLUE_MID: BLUE_DEEP}


def detail_pass(img):
    """Contour + edge light. Decisions read from a snapshot so newly written
    outline pixels never feed back into the next pixel's decision."""
    px = img.load()
    w, h = img.size
    orig = [[px[x, y] for y in range(h)] for x in range(w)]

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and orig[x][y][3] > 0

    for x in range(w):
        for y in range(h):
            if orig[x][y][3] > 0:
                c = orig[x][y][:3]
                if not solid(x, y - 1) and c in LIGHT:        # lit top edge
                    px[x, y] = (*LIGHT[c], 255)
                elif not solid(x, y + 1) and c in SHADE:      # shaded underside
                    px[x, y] = (*SHADE[c], 255)
            elif (solid(x - 1, y) or solid(x + 1, y)
                  or solid(x, y - 1) or solid(x, y + 1)):
                px[x, y] = (*INK, 255)                        # 1px contour


def export(name, fw, fh, count, structure, after=None):
    """`after` runs once per frame *after* the contour pass. Two kinds of work
    belong there: free-floating glow, which must not pick up an outline, and
    interior shading, which must not be re-read as a silhouette edge."""
    strip = Image.new("RGBA", (fw * count, fh), (0, 0, 0, 0))
    px = strip.load()
    for i in range(count):
        structure(Pen(px, i * fw, fw, fh), i)
    detail_pass(strip)
    if after:
        for i in range(count):
            after(Pen(px, i * fw, fw, fh), i)
    # Guard before writing: a failed palette check must never leave a bad PNG
    # on disk for the importer to pick up.
    used = {px[x, y][:3] for x in range(strip.width) for y in range(fh)
            if px[x, y][3] > 0}
    bad = used - ALLOWED
    assert not bad, f"{name}: off-palette {bad}"
    strip.save(f"{name}.png")
    strip.resize((strip.width * 8, fh * 8), Image.NEAREST).save(f"{name}_8x.png")
    print(f"ok: {name}.png  {count}f  {strip.width}x{fh}")


# =============================================================== 1. SHRINE
# Snapshot station save point: torii silhouette wrapped around a terminal.
# Stone plinth, red gate frame, cyan CRT face, scanline sweep, spirit motes.
SHRINE_TEXT = [(50, 35, 48), (54, 35, 57), (58, 35, 44), (62, 35, 53),
               (66, 35, 46), (70, 35, 59)]

# Motes drift upward and thin out over the 4 frames.
SHRINE_MOTES = [[(28, 15, 1), (45, 9, 1), (63, 13, 1), (71, 6, 0)],
                [(29, 12, 1), (46, 6, 1), (62, 10, 1), (70, 3, 0)],
                [(27, 9, 1), (44, 4, 0), (64, 7, 1), (72, 1, 0)],
                [(28, 6, 1), (45, 2, 0), (63, 4, 0), (70, 12, 1)]]


def shrine_structure(p, f):
    # --- stone plinth, two steps, chipped front corners. Each step darkens
    #     into its own shadow through a dithered GREY -> INK band instead of
    #     relying on the single contour row underneath it.
    p.rect(16, 85, 79, 92, GREY)
    p.rect(21, 77, 74, 85, GREY)
    p.dith_row(91, 16, 79, INK, thin=True)
    p.dith_row(90, 16, 79, INK, thin=True)
    for x, y in ((16, 85), (17, 85), (16, 86), (79, 85), (78, 85), (79, 86),
                 (21, 77), (74, 77)):
        p.clear(x, y)

    # --- gate pillars, lit face RED / shadow face RED_DARK, with neon inlay.
    #     The turn from lit to shadow face is dithered rather than stepped, so
    #     the timber reads round the way the player's hair does.
    for x0 in (19, 69):
        p.rect(x0, 24, x0 + 7, 81, RED)
        p.rect(x0 + 5, 24, x0 + 7, 81, RED_DARK)
        p.dith_col(x0 + 4, 24, 81, RED_DARK, thin=True)
        p.dith_col(x0 + 3, 24, 81, RED_DARK, thin=True)
    p.col(21, 30, 79, CYAN)
    p.col(71, 30, 79, CYAN)

    # --- nuki (tie beam)
    p.rect(14, 32, 81, 39, RED)
    p.rect(14, 37, 81, 39, RED_DARK)
    p.dith_row(36, 14, 81, RED_DARK, thin=True)
    p.dith_row(35, 14, 81, RED_DARK, thin=True)

    # --- kasagi: curved top lintel, ends sweeping up; shimaki beam beneath
    for x in range(6, 91):
        t = (x - 48) / 42
        top = 19 - round(5 * t * t)
        p.col(x, top, top + 4, RED)
        p.col(x, top + 5, top + 8, RED_DARK)
        p.dith(x, top + 4, RED_DARK, thin=x)
        p.dith(x, top + 3, RED_DARK, thin=x)

    # --- terminal housing, seated between the pillars
    p.rect(27, 42, 68, 81, GREY)
    p.rect(30, 45, 65, 76, INK)          # bezel
    p.rect(32, 47, 63, 74, CYAN)         # screen
    for y, x0, x1 in SHRINE_TEXT:        # scrolling data rows
        p.row(y, x0, x1, BLUE_MID)
    p.rect(34, 78, 36, 79, GREEN)        # status LEDs
    p.rect(39, 78, 41, 79, GREEN_DEEP)
    p.rect(60, 78, 62, 79, CYAN)

    # --- seams: gate and terminal read as set *onto* the stone, not fused
    p.row(82, 22, 73, INK)
    p.row(85, 21, 74, INK)


def shrine_glow(p, f):
    # --- scanline sweeping down the screen, one step per frame
    sy = 49 + f * 7
    p.row(sy, 32, 63, CYAN_PALE)
    p.row(sy + 1, 32, 63, CYAN_PALE)
    for x in range(32, 64, 2):           # dithered trailing edge
        p.put(x, sy + 2, CYAN_PALE)
    for x in range(33, 64, 4):           # dithered leading edge
        p.put(x, sy - 1, CYAN_PALE)

    # --- spirit motes rising off the gate
    for x, y, big in SHRINE_MOTES[f]:
        p.mote(x, y, big=bool(big))


# =============================================================== 2. TORII
# Fast-travel gate. Pillars lean inward, double lintel curves up at the
# ends, and the opening holds a dashed cyan portal shimmer.
def torii_structure(p, _):
    # --- foot stones, darkening into a dithered GREY -> INK base shadow.
    #     Both ranks are needed: one dithered row against solid neighbours is
    #     a dotted line, it takes a 2px band to read as a checkerboard.
    for x0 in (19, 80):
        p.rect(x0, 85, x0 + 28, 92, GREY)
        p.dith_row(91, x0, x0 + 28, INK, thin=True)
        p.dith_row(90, x0, x0 + 28, INK, thin=True)
        p.clear(x0, 85)
        p.clear(x0 + 28, 85)

    # --- pillars: 2px inward lean from base to top. The lit face turns into
    #     the shadow face through a 2px dither so the post reads cylindrical.
    for y in range(24, 91):
        lean = round(2 * (1 - (y - 24) / 66))
        p.row(y, 25 + lean, 39 + lean, RED)
        p.row(y, 35 + lean, 39 + lean, RED_DARK)      # shadow side
        p.dith(34 + lean, y, RED_DARK, thin=y)
        p.dith(33 + lean, y, RED_DARK, thin=y)
        p.row(y, 88 - lean, 102 - lean, RED)
        p.row(y, 98 - lean, 102 - lean, RED_DARK)
        p.dith(97 - lean, y, RED_DARK, thin=y)
        p.dith(96 - lean, y, RED_DARK, thin=y)

    # --- nuki (tie beam) and gakuzuka (centre strut)
    p.rect(59, 38, 68, 53, RED)
    p.rect(65, 38, 68, 53, RED_DARK)
    p.rect(17, 52, 110, 62, RED)
    p.rect(17, 59, 110, 62, RED_DARK)
    p.dith_row(58, 17, 110, RED_DARK, thin=True)
    p.dith_row(57, 17, 110, RED_DARK, thin=True)

    # --- kasagi + shimaki: parallel curved beams, ends flaring up and out
    for x in range(4, 125):
        t = (x - 64) / 60
        top = 16 - round(7 * t * t)
        p.col(x, top, top + 7, RED)
        p.col(x, top + 8, top + 13, RED_DARK)
        p.dith(x, top + 7, RED_DARK, thin=x)
        p.dith(x, top + 6, RED_DARK, thin=x)
    for x in (4, 5, 6, 122, 123, 124):                # thickened end caps
        t = (x - 64) / 60
        top = 16 - round(7 * t * t)
        p.col(x, top - 1, top + 15, RED_DARK)
        p.col(x, top - 1, top + 6, RED)


def torii_glow(p, _):
    # --- portal shimmer: dashed rain columns, densest at the centre of the
    #     gap. Both openings speak the same language -- the upper pane used to
    #     be scattered single dots, which read as dirt on the sprite next to
    #     the rain below it. It is now the same columns, same modulus, just
    #     thinning out as they climb away from the tie beam.
    cols = [43, 48, 53, 58, 63, 68, 73, 78, 84]
    for k, x in enumerate(cols):
        near = 1.0 - abs(x - 63) / 24.0
        dens = 2 + round(3 * near)                    # 2..5 hits out of 9
        for y in range(63, 92):
            if (y * 5 + k * 7) % 9 < dens:
                p.put(x, y, CYAN)
            elif (y * 3 + k * 5) % 17 == 0:
                p.put(x, y, CYAN_PALE)
        for y in range(30, 52):                       # upper opening
            if 56 < x < 71:                           # gakuzuka blocks it
                continue
            rise = (y - 29) / 22.0                    # 0 at the lintel, 1 at
            thin = round(dens * rise * 0.7)           # the nuki below
            if thin and (y * 5 + k * 7) % 9 < thin:
                p.put(x, y, CYAN)
            elif rise > 0.55 and (y * 3 + k * 5) % 17 == 0:
                p.put(x, y, CYAN_PALE)

    # --- shimmer pooling on the ground line
    for x in range(42, 86, 3):
        p.put(x, 90, CYAN)
        if x % 2 == 0:
            p.put(x + 1, 91, CYAN_PALE)


# =============================================================== 3. STATUES
# Two weathered guardians. Same plinth, same stone treatment: GREY mass,
# INK cracks, chipped silhouette, CYAN_PALE rim from the detail pass.
def plinth(p):
    p.rect(24, 78, 71, 86, GREY)
    p.rect(19, 86, 76, 92, GREY)
    for x, y in ((19, 86), (20, 86), (19, 87), (76, 86), (75, 86), (76, 87),
                 (24, 78), (25, 78), (71, 78)):
        p.clear(x, y)
    p.line(30, 88, 36, 92, INK)                       # cracks
    p.line(58, 87, 63, 92, INK)
    p.row(83, 28, 40, INK)
    p.row(83, 50, 67, INK)


# Seated meditating figure -- head, torso and crossed legs as row tables.
SEATED_HEAD = [(24, 43, 52), (25, 41, 54), (26, 40, 55), (27, 39, 56),
               (28, 39, 56), (29, 38, 57), (30, 38, 57), (31, 38, 57),
               (32, 38, 57), (33, 38, 57), (34, 39, 56), (35, 39, 56),
               (36, 40, 55), (37, 41, 54), (38, 42, 53)]

# Legs stay narrower than the plinth so a shoulder of stone shows either
# side -- that gap is what makes the figure read as sitting *on* something.
SEATED_LEGS = [(64, 34, 61), (65, 33, 62), (66, 32, 63), (67, 31, 64),
               (68, 30, 65), (69, 29, 66), (70, 29, 66), (71, 28, 67),
               (72, 28, 67), (73, 28, 67), (74, 28, 67), (75, 28, 67),
               (76, 29, 66), (77, 29, 66)]


def statue_seated(p):
    plinth(p)
    p.rows(SEATED_LEGS, GREY)                         # crossed legs
    p.rect(34, 58, 61, 67, GREY)                      # lap + folded forearms
    p.rect(37, 48, 58, 60, GREY)                      # torso, narrowed waist
    p.rect(31, 47, 37, 61, GREY)                      # upper arms at the sides
    p.rect(58, 47, 64, 61, GREY)
    p.rect(31, 43, 64, 49, GREY)                      # shoulders
    p.rect(43, 38, 52, 45, GREY)                      # neck
    p.rows(SEATED_HEAD, GREY)
    p.rect(43, 19, 52, 25, GREY)                      # ushnisha topknot
    p.rect(45, 16, 50, 20, GREY)

    # --- seams: without these the whole figure fuses into one grey lump
    p.col(37, 50, 59, INK)                            # arm / torso
    p.col(58, 50, 59, INK)
    p.row(61, 35, 60, INK)                            # forearms across the lap
    p.row(67, 33, 62, INK)                            # lap meets knees
    p.line(47, 68, 34, 76, INK)                       # crossed shins, peak
    p.line(48, 68, 61, 76, INK)                       # rising to the centre
    p.row(69, 43, 52, INK)                            # crossed ankles
    p.row(78, 29, 66, INK)                            # figure meets plinth

    # --- serene face: closed eyes, small mouth
    p.row(30, 41, 45, INK)
    p.row(30, 50, 54, INK)
    p.put(40, 29, INK)
    p.put(55, 29, INK)
    p.col(47, 31, 33, INK)                            # nose ridge
    p.row(35, 45, 50, INK)

    # --- weathering
    p.line(52, 32, 54, 37, INK)                       # cheek fracture
    p.line(35, 52, 40, 58, INK)
    p.line(57, 50, 60, 58, INK)
    p.line(30, 71, 36, 75, INK)
    p.line(62, 70, 67, 74, INK)

    # --- chipped silhouette
    for x, y in ((31, 43), (32, 43), (31, 44), (64, 43), (63, 43), (64, 44),
                 (38, 27), (39, 26), (57, 33), (29, 71), (29, 72),
                 (66, 74), (66, 75), (45, 16), (50, 16), (43, 19)):
        p.clear(x, y)


def statue_guardian(p):
    plinth(p)
    # --- legs planted on the plinth
    p.rect(34, 62, 45, 77, GREY)
    p.rect(50, 62, 61, 77, GREY)
    p.rect(31, 54, 64, 64, GREY)                      # hips / armour skirt
    p.rect(34, 38, 61, 56, GREY)                      # torso
    p.rect(28, 32, 67, 39, GREY)                      # broad shoulders
    p.rect(43, 29, 52, 34, GREY)                      # neck
    p.rect(40, 13, 55, 29, GREY)                      # head
    p.rect(37, 9, 58, 14, GREY)                       # helmet crest
    p.rect(45, 5, 50, 10, GREY)                       # crest fin

    # --- staff, drawn before the hand so the fingers close over it
    p.rect(68, 12, 71, 84, GREY)                      # shaft
    p.rect(64, 3, 75, 13, GREY)                       # ringed finial
    for x, y in ((64, 3), (75, 3), (64, 13), (75, 13)):
        p.clear(x, y)                                 # round the ring
    p.rect(67, 6, 72, 10, INK)                        # ring void
    p.rect(67, 30, 72, 33, GREY)                      # binding collar
    p.row(31, 67, 72, INK)

    # --- arms: right hand gripping the staff, left arm hanging in a fist
    p.rect(61, 41, 72, 48, GREY)
    p.col(64, 42, 47, INK)                            # knuckles
    p.col(68, 42, 47, INK)
    p.col(61, 42, 47, INK)                            # arm / torso seam
    p.rect(28, 38, 34, 56, GREY)
    p.rect(26, 55, 34, 62, GREY)                      # left fist
    p.col(34, 40, 62, INK)                            # arm / torso / skirt seam
    p.row(55, 27, 33, INK)                            # wrist

    # --- stern face under a shadowed helmet brim
    p.row(14, 40, 55, INK)
    p.row(19, 41, 45, INK)
    p.row(20, 42, 44, INK)
    p.row(19, 50, 54, INK)
    p.row(20, 51, 53, INK)
    p.col(47, 21, 23, INK)
    p.row(25, 44, 51, INK)
    p.put(43, 26, INK)
    p.put(52, 26, INK)

    # --- armour plates, hem, and weathering cracks
    p.row(45, 35, 60, INK)
    p.row(52, 35, 60, INK)
    p.col(47, 45, 52, INK)
    p.row(64, 32, 63, INK)                            # skirt hem
    p.line(38, 40, 42, 51, INK)
    p.line(56, 58, 60, 63, INK)
    p.line(37, 67, 41, 76, INK)
    p.line(53, 65, 57, 72, INK)
    p.line(30, 34, 33, 39, INK)
    p.row(78, 34, 45, INK)                            # legs meet plinth
    p.row(78, 50, 61, INK)

    # --- chipped silhouette
    for x, y in ((28, 32), (29, 32), (28, 33), (67, 32), (66, 32), (67, 33),
                 (40, 13), (55, 13), (55, 20), (31, 54), (64, 54), (64, 55),
                 (34, 77), (61, 76), (45, 5), (50, 5), (37, 9), (58, 9),
                 (26, 55), (26, 62)):
        p.clear(x, y)


def statue_structure(p, i):
    (statue_seated if i == 0 else statue_guardian)(p)


def stone_volume(p, _):
    """Mid-shade pass. The guardians were a single flat GREY mass -- three
    colours, three quarters of it one tone -- so they read as cut card next to
    the player. Stone is opaque, so its volume has to come from where light
    lands: every horizontal surface catches CYAN_PALE, every undercut drops to
    INK, and both arrive through the player's 2px checkerboard rather than a
    hard band, because the palette has no intermediate grey to step through.

    Runs after the contour pass, and only ever repaints pixels that are still
    GREY. The rim light, the seams, the cracks and the chipped silhouette all
    survive untouched -- this fills the flat interior those details enclose.

    Two rules, deliberately lopsided. Shadow does the modelling: stone sitting
    on top of a structural step -- a hem, a plinth course, an armour plate,
    the silhouette itself -- drops into an INK undercut, and the right-hand
    side of a wide mass darkens to match the upper-left key light the rest of
    the project uses. Light is only a glint: CYAN_PALE is the brightest colour
    on the sprite, so it goes on at a quarter screen and only where stone
    genuinely faces the sky. Lighting every internal seam as well turns the
    whole figure into lace.

    A step is told from a detail by how far it runs. Structural seams are
    drawn as long rows; eyes, mouths and weathering cracks are 1-8px marks.
    Shadowing under everything is what erased the seated guardian's face.

    The undercut is ONE rank deep, not a fading stack of three. Three ranks
    measured 5.28% on the project's own dither metric (the one in
    enemies/make_enemies.py measure()) against 0.80% for player_idle and
    2.31% for the guardian enemy -- it made this the grainiest sprite in the
    game by more than 2x, and the wash of texture swallowed the crisp armour
    plate lines on the standing figure. One rank lands at 1.56%, level with
    the guardian, and the shadows still read.
    """
    STEP = 10          # an INK run this wide is a surface, not an engraving
    MASS = 6           # a stone run this wide has a side to turn away

    lit = [[p.get(x, y)[3] > 0 for y in range(p.h)] for x in range(p.w)]
    stone = [[lit[x][y] and p.get(x, y)[:3] == GREY for y in range(p.h)]
             for x in range(p.w)]                         # snapshot: painted
    ink = [[lit[x][y] and p.get(x, y)[:3] == INK for y in range(p.h)]
           for x in range(p.w)]                           # pixels must not
                                                          # move the surfaces
    def run(grid, x, y, dx):
        n = 0
        while 0 <= x + dx * (n + 1) < p.w and grid[x + dx * (n + 1)][y]:
            n += 1
        return n

    def step_below(x, y):
        """Is the stone at (x, y) sitting on a real step?"""
        if y + 1 >= p.h:
            return True
        if not lit[x][y + 1]:
            return True                                   # open sky beneath
        if not ink[x][y + 1]:
            return False
        return run(ink, x, y + 1, -1) + run(ink, x, y + 1, 1) + 1 >= STEP

    for x in range(p.w):
        tops = [y for y in range(p.h) if lit[x][y]]
        ytop = tops[0] if tops else None
        for y in range(p.h):
            if not stone[x][y]:
                continue
            if step_below(x, y):
                p.dith(x, y, INK, phase=1)                # undercut shadow
            elif (run(stone, x, y, 1) <= 1
                  and run(stone, x, y, -1) + 2 >= MASS):
                p.dith(x, y, INK, phase=1, thin=y)        # side turning away
            elif ytop is not None and 1 <= y - ytop <= 2:
                p.dith(x, y, CYAN_PALE, thin=x)           # sky-facing glint


# =============================================================== 4. LANTERN
# Hanging stone lantern with a green spirit flame that reshapes each frame.
LANTERN_ROOF = [(13, 20, 27), (14, 19, 28), (15, 18, 29), (16, 16, 31),
                (17, 14, 33), (18, 12, 35), (19, 10, 37), (20, 8, 39),
                (21, 6, 41), (22, 5, 42)]

# Flames authored bottom-up as (y, x0, x1). Height, lean and waver all change.
# Every row must stay inside the centre pane (x 19..28) or the mullions drawn
# after them slice the flame and orphan the offcut in a side pane.
FLAMES = [
    [(40, 21, 27), (39, 20, 28), (38, 20, 28), (37, 20, 28), (36, 20, 27),
     (35, 21, 27), (34, 21, 26), (33, 21, 26), (32, 22, 25), (31, 22, 25),
     (30, 22, 24), (29, 23, 24), (28, 23, 23)],
    [(40, 20, 28), (39, 19, 28), (38, 19, 28), (37, 19, 28), (36, 20, 28),
     (35, 21, 28), (34, 22, 27), (33, 22, 26), (32, 23, 26), (31, 24, 25)],
    [(40, 21, 27), (39, 20, 28), (38, 20, 28), (37, 21, 28), (36, 21, 28),
     (35, 22, 28), (34, 22, 28), (33, 23, 27), (32, 23, 27), (31, 24, 26),
     (30, 24, 26), (29, 25, 26), (28, 25, 25), (27, 25, 25)],
]

# Embers escaping the vent, per frame. Kept clear of the chain and its contour
# (x 21..26 above y 8, x 20..27 across the jewel) so they read as free-floating
# spirit light instead of green blemishes stuck on the stone.
LANTERN_MOTES = [[(18, 6, 1), (29, 3, 0)],
                 [(17, 3, 1), (30, 7, 1), (19, 10, 0)],
                 [(16, 1, 0), (28, 4, 1), (31, 9, 0)]]


# Spirit fire is drawn one way across the whole project -- effects/soul.png
# and the soul_byte icon both build it as a GREEN body, a GREEN_DEEP base and
# bottom-facing rim, and a small WHITE core sitting low in the bulb. The
# lantern used to be an outlined blob instead: GREEN_DEEP everywhere with a
# GREEN inset, no hot core at all, so the same fire read as a different
# substance depending on where you met it. This is the shared anatomy.
CORE_HW = [0, 1, 1, 1, 0]                 # widths 1,3,3,3,1 -- soul's profile


def flame(p, rows):
    """Paint a flame from a bottom-up [(y, x0, x1), ...] silhouette table."""
    base = max(y for y, _, _ in rows)
    span = {y: (x0, x1) for y, x0, x1 in rows}
    for y, x0, x1 in rows:
        p.row(y, x0, x1, GREEN)                       # body
    for y in (base - 1, base):                        # base sits in its own
        if y in span:                                 # shadow
            p.row(y, *span[y], GREEN_DEEP)
    if base - 2 in span:                              # rim of the row above
        x0, x1 = span[base - 2]
        p.put(x0, base - 2, GREEN_DEEP)
        p.put(x1, base - 2, GREEN_DEEP)
    for j, hw in enumerate(CORE_HW):                  # hot core, low in the
        y = base - 6 + j                              # bulb, following the
        if y not in span:                             # flame's lean
            continue
        x0, x1 = span[y]
        if x1 - x0 < 2 * hw + 2:                      # never breach the body
            continue
        cx = (x0 + x1) // 2
        p.row(y, cx - hw, cx + hw, WHITE)


def lantern_structure(p, f):
    # --- chain and hanging ring
    p.rect(22, 0, 25, 11, GREY)
    for y in (2, 5, 8):
        p.rect(23, y, 24, y, INK)
    p.rect(21, 8, 26, 13, GREY)                       # finial jewel
    p.rect(23, 9, 24, 10, INK)

    # --- kasa (roof), widening down, corners sweeping up 2px thick so the
    #     upturn stays fused to the eave instead of breaking into specks
    p.rows(LANTERN_ROOF, GREY)
    p.rows([(22, 4, 5), (21, 3, 4), (20, 2, 3), (19, 2, 3)], GREY)
    p.rows([(22, 42, 43), (21, 43, 44), (20, 44, 45), (19, 44, 45)], GREY)
    p.row(23, 7, 40, INK)                             # eave shadow lip

    # --- hibukuro (fire box); the void runs the full inner width and the
    #     mullions sit hard against the jambs, leaving a centre pane (x 19..28)
    #     wide enough to hold the widest flame frame without clipping it
    p.rect(14, 24, 33, 44, GREY)
    p.rect(16, 27, 31, 41, INK)                       # window void
    flame(p, FLAMES[f])
    p.col(18, 27, 41, GREY)                           # lattice mullions
    p.col(29, 27, 41, GREY)

    # --- chudai (base) tapering to a drop finial
    p.rect(15, 44, 32, 48, GREY)
    p.rect(18, 48, 29, 52, GREY)
    p.rect(21, 52, 26, 55, GREY)
    p.rect(23, 55, 24, 57, GREY)
    p.row(46, 18, 29, INK)                            # carved groove
    for x, y in ((14, 24), (33, 24), (15, 44), (32, 44)):
        p.clear(x, y)


def lantern_glow(p, f):
    for x, y, big in LANTERN_MOTES[f]:
        p.mote(x, y, big=bool(big))


# =============================================================== build
export("shrine", 96, 96, 4, shrine_structure, shrine_glow)
export("torii", 128, 96, 1, torii_structure, torii_glow)
export("statue", 96, 96, 2, statue_structure, stone_volume)
export("lantern", 48, 64, 3, lantern_structure, lantern_glow)
