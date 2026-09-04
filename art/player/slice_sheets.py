"""Slice the three themed canon sheets into normalized 96x96 game frames.

Same pipeline as slice_canon.py but generalized: grid-free sheets with wide
gutters, so cells are found purely by projection gaps. Emits one PNG per pose
plus per-sheet contact strips for review.

Run: python slice_sheets.py   ->  sheet_frames/<sheet>_NN.png + <sheet>_contact_4x.png
"""
from collections import deque
from PIL import Image
import pathlib

REF = pathlib.Path("../reference")
OUT = pathlib.Path("sheet_frames")
OUT.mkdir(exist_ok=True)

SHEETS = ["sheet_locomotion", "sheet_combat", "sheet_traversal", "sheet_runcycle",
          "sheet_attack8", "sheet_air8", "sheet_idle8", "sheet_mega"]

# Sheets whose frames are laid out along an ARC rather than a grid: the poses
# overlap vertically, so row-band detection collapses them into one band.
# Slice these by column gaps across the full image height instead.
ARC_LAYOUT = {"sheet_air8"}

# Last resort for arc layouts whose poses also overlap HORIZONTALLY, so no gap
# exists to split on. The poses are evenly spaced, so cut N equal columns and
# take the content bbox inside each. Value is the known frame count.
# sheet_mega is ONE generation containing every core animation, so its character
# proportions are consistent by construction — the fix for the body-size drift
# that per-sheet scaling cannot solve. Its cells carry a drawn dark background,
# so gap detection is unreliable and the 8x4 grid is asserted instead.
EVEN_SPLIT = {"sheet_air8": 8, "sheet_attack8": 8}

# EXPLICIT GRID (cols, rows). Deriving the split from detected bands guessed 10x3
# on an 8x4 sheet and cut every figure in half. When the grid is known, assert it
# rather than inferring it — inference only earns its place where the layout is
# genuinely unknown.
GRID = {"sheet_mega": (6, 5)}

PALETTE = [
    (10, 14, 31), (30, 51, 217), (43, 111, 232), (53, 198, 244),
    (143, 232, 255), (143, 17, 22), (224, 31, 38), (198, 240, 42),
    (107, 138, 15), (255, 255, 255), (74, 85, 104),
    (74, 42, 26), (133, 84, 52), (176, 122, 74),
]
SATURATED = [p for p in PALETTE if max(p) - min(p) > 30]
FIG_H, BASELINE = 76, 84

# HEAD-SIZE NORMALISATION.
#
# Scaling each sheet so its TALLEST pose hits a fixed height is wrong: a crouch is
# legitimately short and a stretched fall legitimately tall, so the tallest pose is
# a different fraction of body height in every sheet. Measured result was the
# character growing and shrinking between animations — mask height ran 19px in
# crouch against 15px in idle, a 22% size pop.
#
# The head does NOT change size between poses, and this character's head is a
# distinctively RED hannya mask. So: measure the mask in every frame, take each
# sheet's MEDIAN (robust against poses where the mask is edge-on or foreshortened),
# and scale the sheet so that median matches TARGET_MASK_H. Body size then holds
# across every animation by construction rather than by hand-tuned multipliers.
TARGET_MASK_H = 16          # px, measured from the idle sheet
MASK_REDS = [(224, 31, 38), (143, 17, 22)]


def _is_mask_red(c):
    return any(abs(c[0] - r) < 30 and abs(c[1] - g) < 30 and abs(c[2] - b) < 30
               for r, g, b in MASK_REDS)


def mask_box(img):
    """(w, h) bbox of the LARGEST CONNECTED red component — the mask itself.
    A union bbox over every red pixel gets stretched to double size by one or
    two stray red accents elsewhere on the body."""
    px = img.load()
    w, h = img.size
    pts = set()
    for x in range(w):
        for y in range(h):
            if px[x, y][3] > 0 and _is_mask_red(px[x, y][:3]):
                pts.add((x, y))
    if not pts:
        return (0, 0)
    best = []
    while pts:
        stack = [pts.pop()]
        comp = []
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for dx in (-2, -1, 0, 1, 2):        # radius 2 bridges 1px gaps
                for dy in (-2, -1, 0, 1, 2):
                    n = (cx + dx, cy + dy)
                    if n in pts:
                        pts.discard(n)
                        stack.append(n)
        if len(comp) > len(best):
            best = comp
    xs = [p[0] for p in best]
    ys = [p[1] for p in best]
    return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def mask_height(img):
    """Largest bbox dimension of the mask. Not the height: a head is roughly
    square, so a rotated pose compresses height while width holds. The larger
    dimension survives rotation, which keeps foreshortened poses honest."""
    bw, bh = mask_box(img)
    return max(bw, bh)


def mask_is_square(img, thresh=0.68):
    """True when the mask is NOT heavily foreshortened, so its size can be
    trusted for a per-frame scale correction."""
    bw, bh = mask_box(img)
    if bw == 0 or bh == 0:
        return False
    return min(bw, bh) / float(max(bw, bh)) >= thresh


def median(vals):
    v = sorted(vals)
    return v[len(v) // 2] if v else 0


def _hsv(c):
    r, g, b = (v / 255.0 for v in c)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    return h, (0.0 if mx == 0 else d / mx), mx


_PAL_HSV = [(p, _hsv(p)) for p in SATURATED]


def snap(c):
    sat = max(c) - min(c)
    if sat < 32:                       # neutral: never snap to skin
        v = max(c)
        return (255, 255, 255) if v > 200 else (74, 85, 104) if v > 60 else (10, 14, 31)
    if max(c) < 72:
        # very dark but tinted: garment shadow. SATURATED has no dark entry
        # (INK's spread is 21, under the filter), so without this floor a navy
        # shadow's hue matched royal blue and lit up patches inside black cloth
        return (10, 14, 31)
    h0, s0, v0 = _hsv(c)
    if 200 <= h0 <= 260 and v0 < 0.62 and s0 < 0.55:
        # DESATURATED mid-value blue: fabric sheen, not ponytail. Slate misses
        # the SATURATED filter (its spread is exactly 30), so these leapt to
        # royal blue and lit patches inside the black tracksuit and hakama.
        # Saturation is the separator — measured: ponytail root 0.84-0.88,
        # garment sheen 0.24-0.36. A value-only test greyed the ponytail.
        return (74, 85, 104)
    # hue-first match, same as the enemy slicer: RGB distance put the mask's
    # crimson HIGHLIGHTS (123,55,66 — hue 350) onto skin brown (133,84,52 — hue
    # 25) because they are close in RGB space and far apart on the hue wheel
    h, s, v = _hsv(c)

    def cost(entry):
        _, (ph, ps, pv) = entry
        dh = abs(h - ph)
        dh = min(dh, 360 - dh) / 180.0        # circular, normalized
        return dh * 3.0 + abs(v - pv) * 1.0 + abs(s - ps) * 0.4

    return min(_PAL_HSV, key=cost)[0]


def slice_sheet(name):
    img = Image.open(REF / f"{name}.png").convert("RGB")
    W, H = img.size
    px = img.load()

    # auto-detect background polarity from the corners (sheets come back either way)
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    dark_bg = sum(max(c) for c in corners) / 4 < 110
    print(f"{name}: {'dark' if dark_bg else 'light'} background")

    def is_bg(c):
        r, g, b = c
        if dark_bg:
            # bg is essentially pure black (max<=1); INK cloth is (10,14,31).
            # Threshold must sit between them or the black tracksuit gets eaten.
            if max(r, g, b) < 6:
                return True
            # Some sheets draw a NEUTRAL dark-grey cell fill instead of true black
            # — sheet_mega uses (18,18,18). That is brighter than the pure-black
            # test allows, but it is grey where INK is blue-tinted (max-min 21),
            # so neutrality separates them without eating the tracksuit.
            if max(r, g, b) < 26 and max(r, g, b) - min(r, g, b) < 6:
                return True
            # sheet_mega's fix generations came back with a MID-grey fill
            # (~80,80,80) — too bright for the dark tests, too dark for the light
            # one, so it survived and palette-snapped to slate. The band must hug
            # the measured fill (79-84): a wide 40-140 window classified garment
            # SHADOWS as background and the pocket pass ate chunks out of the
            # figure's interior.
            return 64 <= max(r, g, b) < 100 and max(r, g, b) - min(r, g, b) < 6
        return r > 185 and g > 185 and b > 185 and max(r, g, b) - min(r, g, b) < 26

    def ink(x, y):
        return not is_bg(px[x, y])

    # a near-solid row is a drawn divider rule, not artwork — treat it as empty
    # or it bridges every column and the whole row collapses into one cell
    bar_rows = set()
    for y in range(H):
        d = sum(1 for x in range(0, W, 2) if ink(x, y))
        if d > (W / 2) * 0.9:
            bar_rows.add(y)

    # --- row bands
    bands, start = [], None
    for y in range(H):
        d = 0 if y in bar_rows else sum(1 for x in range(0, W, 2) if ink(x, y))
        dense = d > 4
        if dense and start is None:
            start = y
        elif not dense and start is not None:
            if y - start > 40:
                bands.append((start, y))
            start = None
    if start is not None and H - start > 40:
        bands.append((start, H))
    if name in ARC_LAYOUT:
        bands = [(0, H)]        # one band: let the column pass do all the work

    # --- cells within each band
    cells = []
    for y0, y1 in bands:
        cd = [sum(1 for y in range(y0, y1) if y not in bar_rows and ink(x, y))
              for x in range(W)]
        in_c, cs, gap = False, 0, 0
        # a thin trailing arc tail is not enough to count as a frame's body —
        # requiring a few px keeps wide green slash arcs from bridging gutters
        thresh = 3
        for x in range(W):
            if cd[x] > thresh:
                if not in_c:
                    in_c, cs = True, x
                gap = 0
            elif in_c:
                gap += 1
                if gap >= 14:
                    if x - gap - cs > 30:
                        cells.append((cs, y0, x - gap, y1))
                    in_c = False
        if in_c and W - cs > 30:
            cells.append((cs, y0, W, y1))

    if name in GRID:
        cols, rows = GRID[name]
        cells = []
        cw_step = W / float(cols)
        ch_step = H / float(rows)
        for r in range(rows):
            for c in range(cols):
                cells.append((int(c * cw_step), int(r * ch_step),
                              int((c + 1) * cw_step), int((r + 1) * ch_step)))
        print(f"{name}: asserted {cols}x{rows} grid = {len(cells)} cells")
    elif name in EVEN_SPLIT and len(cells) != EVEN_SPLIT[name]:
        want = EVEN_SPLIT[name]
        per = max(1, want // max(1, len(bands)))
        forced = []
        for y0, y1 in bands:
            step = W / float(per)
            for i in range(per):
                forced.append((int(i * step), y0, int((i + 1) * step), y1))
        print(f"{name}: auto-split found {len(cells)} != {want}; forcing "
              f"{per} even columns x {len(bands)} band(s)")
        cells = forced

    # drop divider bars: some sheets separate rows with a solid full-width rule,
    # which reads as one enormous "pose" and wrecks the per-row height anchor
    kept = []
    for x0, y0, x1, y1 in cells:
        if (x1 - x0) > W * 0.5 and (y1 - y0) < 40:
            print(f"{name}: dropped divider bar {x1 - x0}x{y1 - y0}")
            continue
        kept.append((x0, y0, x1, y1))
    cells = kept

    # --- extract, clean, normalize
    figs = []
    for x0, y0, x1, y1 in cells:
        crop = img.crop((x0, y0, x1, y1)).convert("RGBA")
        cw, ch = crop.size
        cpx = crop.load()

        # PER-CELL FILL. A generation came back with alternating cream/olive row
        # fills plus pure white behind two cells — three different fills in one
        # sheet, none matching a single global polarity test. For asserted-grid
        # sheets, each cell samples its own border ring: the ring's dominant
        # colour IS that cell's background. The 1px dark outline the prompt
        # demands seals every garment, so even a white haori on a white fill
        # survives the border flood.
        cell_bgs = []
        if name in GRID:
            # inset past the drawn row-divider hairlines; also puts the ring
            # inside this cell's own band when band edges drift off the grid
            inset = 5
            crop = crop.crop((inset, inset, cw - inset, ch - inset))
            cw, ch = crop.size
            cpx = crop.load()
            ring = ([cpx[x, 0][:3] for x in range(cw)]
                    + [cpx[x, ch - 1][:3] for x in range(cw)]
                    + [cpx[0, y][:3] for y in range(ch)]
                    + [cpx[cw - 1, y][:3] for y in range(ch)])
            buckets = {}
            for c in ring:
                buckets.setdefault((c[0] // 8, c[1] // 8, c[2] // 8), []).append(c)
            # top TWO ring colours both count as fill: a cell whose drawn band
            # edge drifts across the grid line samples the neighbouring band's
            # colour as dominant while its own interior fill comes second. The
            # 1px outline seals real garments, so an extra fill colour cannot
            # eat the figure — at worst it removes a neighbour's crossing sliver,
            # which is contamination we want gone anyway.
            ranked = sorted(buckets.values(), key=len, reverse=True)
            for members in ranked[:2]:
                if len(members) >= len(ring) * 0.12:
                    cell_bgs.append(tuple(round(sum(v) / len(members))
                                          for v in zip(*members)))

        def near(c, b, tol):
            return all(abs(c[i] - b[i]) <= tol for i in range(3))

        def near_any(c, tol):
            return any(near(c, b, tol) for b in cell_bgs)

        # NEAR-WHITE FILL cells (the lying and kneeling poses): colour cannot
        # separate the white haori from the white fill — the flood ate straight
        # through the coat and the pocket pass finished the sealed remainder,
        # leaving a skeleton. The separation there must be TOPOLOGICAL:
        #   - the flood may not cross a 1px-dilated DARK BARRIER (the drawn
        #     outline), so a leak through a gap in the hem cannot spread inside
        #   - global is_bg is excluded (its light test matches coat whites)
        #   - the pocket pass is skipped: trapped white background inside a
        #     white-coat silhouette is invisible — keeping it costs nothing,
        #     removing it risks the coat
        # NEAR-NEUTRAL bright only: the cream fill (227,230,205) also clears a
        # bare min>=200 test, which routed the idle row down this path — where
        # the pocket pass is off — and the sealed ponytail/haori wedge survived
        # into the game. True white fills are flat AND neutral (spread < 12).
        white_fill = bool(cell_bgs) and any(min(b) >= 200 and max(b) - min(b) < 12
                                            for b in cell_bgs)
        barrier = None
        if white_fill:
            dark = [[max(cpx[x, y][:3]) < 120 for y in range(ch)]
                    for x in range(cw)]
            barrier = [[False] * ch for _ in range(cw)]
            for x in range(cw):
                for y in range(ch):
                    if dark[x][y]:
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < cw and 0 <= ny < ch:
                                    barrier[nx][ny] = True

        def cell_is_bg(c):
            if white_fill:
                # TIGHT tolerance: the fill is flat, the coat's shaded whites
                # differ by 10+. At tol 26 the flood reached the coat's pure-
                # white CORE through a bright corridor the dark barrier missed
                # — measured: 1025 light px kept at tol 26 vs the coat's ~2000
                return near_any(c, 10)
            return near_any(c, 26) or is_bg(c)

        bg = [[False] * ch for _ in range(cw)]
        q = deque()
        for x in range(cw):
            q.extend(((x, 0), (x, ch - 1)))
        for y in range(ch):
            q.extend(((0, y), (cw - 1, y)))
        while q:
            x, y = q.popleft()
            if not (0 <= x < cw and 0 <= y < ch) or bg[x][y]:
                continue
            if barrier is not None and barrier[x][y]:
                continue
            if cell_is_bg(cpx[x, y][:3]):
                bg[x][y] = True
                q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

        if white_fill:
            # the barrier leaves a 1px fill-coloured fringe hugging the outline;
            # ONE bounded sweep removes it (only fill-coloured pixels touching
            # flood-reached background — it cannot creep past the dark outline)
            fringe = [(x, y) for x in range(cw) for y in range(ch)
                      if not bg[x][y] and near_any(cpx[x, y][:3], 10)
                      and any(0 <= x + dx < cw and 0 <= y + dy < ch
                              and bg[x + dx][y + dy]
                              for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
            for x, y in fringe:
                bg[x][y] = True

        # WARM SHADOW SWEEP. The sheet draws soft cream drop-shadows behind the
        # figures; they sit just beyond the fill tolerance and survive as pale
        # blobs (glaring on the game's dark background — invisible on any
        # light-backed audit, which is how they kept slipping through). They
        # are WARM-light (r well above b); the haori's whites are neutral or
        # blue-leaning, the hilts too dark, so this test cannot touch either.
        def warm(c):
            return min(c) > 150 and c[0] - c[2] >= 12

        if name in GRID:
            q2 = deque((x, y) for x in range(cw) for y in range(ch)
                       if not bg[x][y] and warm(cpx[x, y][:3])
                       and any(0 <= x + dx < cw and 0 <= y + dy < ch
                               and bg[x + dx][y + dy]
                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))))
            while q2:
                x, y = q2.popleft()
                if bg[x][y]:
                    continue
                bg[x][y] = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < cw and 0 <= ny < ch and not bg[nx][ny] \
                            and warm(cpx[nx, ny][:3]):
                        q2.append((nx, ny))

        if white_fill:
            # RECLAIM ENCLOSED BACKGROUND. In these cells the coat interior IS
            # the fill colour — only the drawn outline separates them, and the
            # ragged hem has gaps, so the flood gets inside at ANY tolerance.
            # Topology is the only signal left: a flooded pixel with kept
            # pixels in all four orthogonal directions is INSIDE the
            # silhouette. Reclaiming it is visually free here (white on white)
            # and restores the coat body wholesale; genuine outside fill fails
            # the test because at least one ray escapes to the border.
            # two iterations: pixels whose ray escaped through the same hem gap
            # become enclosed once their neighbours are reclaimed
            for _ in range(2):
                left = [[False] * ch for _ in range(cw)]
                right = [[False] * ch for _ in range(cw)]
                up = [[False] * ch for _ in range(cw)]
                down = [[False] * ch for _ in range(cw)]
                for y in range(ch):
                    seen_k = False
                    for x in range(cw):
                        left[x][y] = seen_k
                        seen_k = seen_k or not bg[x][y]
                    seen_k = False
                    for x in range(cw - 1, -1, -1):
                        right[x][y] = seen_k
                        seen_k = seen_k or not bg[x][y]
                for x in range(cw):
                    seen_k = False
                    for y in range(ch):
                        up[x][y] = seen_k
                        seen_k = seen_k or not bg[x][y]
                    seen_k = False
                    for y in range(ch - 1, -1, -1):
                        down[x][y] = seen_k
                        seen_k = seen_k or not bg[x][y]
                changed = 0
                for x in range(cw):
                    for y in range(ch):
                        if bg[x][y] and left[x][y] and right[x][y] \
                                and up[x][y] and down[x][y] \
                                and not warm(cpx[x, y][:3]):
                            # never resurrect swept shadow pixels
                            bg[x][y] = False
                            changed += 1
                if changed == 0:
                    break


        def halo(c):                   # anti-aliasing fringe toward the bg color
            if near_any(c, 52):
                return True
            if dark_bg:
                # near-black fringe, or the neutral fringe of a mid-grey fill.
                # Spread must stay under 7: the haori's blue-grey shading spreads
                # 8, and a looser test chewed ragged bites out of its edges.
                return max(c) < 9 or (max(c) < 150 and max(c) - min(c) < 7)
            return min(c) > 170 and max(c) - min(c) < 30

        # HALO EROSION — DISABLED for asserted-grid sheets. Ablation: turning it
        # off cut total figure erosion 11.21% -> 9.44% (recovering all 4464
        # halo-killed figure pixels) while noise_kept stayed flat at 0.16%
        # (397 -> 402 px, far under the 0.5% budget). Softer settings did worse:
        # tol 52 -> 30 only reached 10.36%, 1 sweep only 11.12%. The per-cell
        # ring fills plus the 1px outline already contain the flood cleanly, so
        # the halo bought nothing but chewed edges here. Non-GRID sheets keep
        # the pass unchanged.
        if name not in GRID:
            for _ in range(2):
                edge = [(x, y) for x in range(cw) for y in range(ch)
                        if not bg[x][y] and halo(cpx[x, y][:3])
                        and any(0 <= x + dx < cw and 0 <= y + dy < ch and bg[x + dx][y + dy]
                                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
                for x, y in edge:
                    bg[x][y] = True

        # SEALED POCKETS. The border flood cannot reach background trapped inside
        # the silhouette — e.g. the gap between the ponytail and the haori, closed
        # off where they touch. Left alone it snaps to opaque WHITE and shows in
        # game as a bright blob. Distinguish from the (also white) haori by AREA:
        # a pocket is tiny, the garment is not.
        def is_pure_bg(c):
            # STRICTER than is_bg: trapped background is the sheet's flat paper
            # white, while the haori is shaded off-white. The loose test cannot
            # tell them apart, so pocket detection uses this one.
            if white_fill:
                # pocket pass OFF for near-white fills — see the barrier note:
                # here the fill match IS the coat, and the sealed-coat-interior
                # is exactly what this pass would delete
                return False
            if name in GRID:
                # Fill match with room for the pocket's own shading: at tol 8
                # the shaded interior of the ponytail/haori gap survived and
                # rendered in game as the white wedge behind the character.
                # Tol 24 is safe here BECAUSE white fills never reach this
                # line — the one place a loose fill match could eat garment
                # (coat, mask teeth on a white fill) returns False above.
                # Also sweep WARM-light pixels: a sealed pocket keeps the
                # fill's warm shadow gradient, which no fill tolerance covers,
                # and the figure's own whites are neutral or blue-leaning.
                return near_any(c, 24) or warm(c)
                # (NO paper-white fallback here: it was the dominant eroder —
                # 21250 of 28080 eroded figure px entered through it, because
                # the haori's brightest highlights satisfy min>242/spread<8.
                # On a per-cell-filled sheet, trapped background is the cell's
                # own fill; the fill match above covers every real pocket.)
            if near_any(c, 8):
                return True
            if dark_bg:
                return max(c) < 4 or (68 <= max(c) < 94 and max(c) - min(c) < 5)
            return min(c) > 242 and max(c) - min(c) < 8

        seen = [[False] * ch for _ in range(cw)]
        max_pocket = max(200, int(cw * ch * 0.05))   # strict colour test makes a big cap safe
        for sx in range(cw):
            for sy in range(ch):
                if bg[sx][sy] or seen[sx][sy] or not is_pure_bg(cpx[sx, sy][:3]):
                    continue
                comp, stack = [], [(sx, sy)]
                seen[sx][sy] = True
                while stack:
                    x, y = stack.pop()
                    comp.append((x, y))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < cw and 0 <= ny < ch and not seen[nx][ny]
                                and not bg[nx][ny] and is_pure_bg(cpx[nx, ny][:3])):
                            seen[nx][ny] = True
                            stack.append((nx, ny))
                    if len(comp) > max_pocket:
                        break            # too big to be a pocket — it is the garment
                # GRID sheets also need a MINIMUM: a handful of sealed warm-ish
                # shading pixels inside the coat matched the loose fill test and
                # punched pinholes. A real pocket (the ponytail/haori wedge) is
                # tens-to-hundreds of pixels; shading clumps are single digits.
                min_pocket = 30 if name in GRID else 0
                if min_pocket <= len(comp) <= max_pocket:
                    for x, y in comp:
                        bg[x][y] = True
        # DESPECKLE: orphan anti-aliasing dots that survived the flood become
        # isolated bright pixels once snapped. Keep only components big enough
        # to be artwork (the figure, a detached sword tip, an effect arc).
        lab = [[False] * ch for _ in range(cw)]
        for sx in range(cw):
            for sy in range(ch):
                if bg[sx][sy] or lab[sx][sy]:
                    continue
                comp, stack = [], [(sx, sy)]
                lab[sx][sy] = True
                while stack:
                    x, y = stack.pop()
                    comp.append((x, y))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < cw and 0 <= ny < ch and not lab[nx][ny] \
                                and not bg[nx][ny]:
                            lab[nx][ny] = True
                            stack.append((nx, ny))
                # FILL-GATED for asserted-grid sheets: only remove a small
                # component when every pixel sits within tol 20 of a cell fill
                # colour — a fill-coloured speck is orphaned background, but a
                # detached sword tip or mask fragment is art. Ablation: this
                # gate recovers all 36 despeckle-killed figure pixels while
                # noise_kept stays byte-identical at 397 px (0.16%), strictly
                # dominating both plain disable (noise 424) and threshold 6
                # (only 9 px recovered). Non-GRID sheets keep the plain
                # size-only rule.
                if len(comp) < 12 and (name not in GRID or
                                       all(near_any(cpx[x, y][:3], 20)
                                           for x, y in comp)):
                    for x, y in comp:
                        bg[x][y] = True

        minx, miny, maxx, maxy = cw, ch, 0, 0
        for x in range(cw):
            for y in range(ch):
                if bg[x][y]:
                    cpx[x, y] = (0, 0, 0, 0)
                else:
                    if name in GRID:
                        # NO palette snap for the single-generation sheet: it was
                        # prompted with the strict palette and lands near it, but
                        # its soft shading straddles snap boundaries — snapping
                        # turned the white haori into blue/slate patchwork and
                        # scattered bright stray pixels along every edge.
                        c3 = cpx[x, y][:3]
                        cpx[x, y] = (c3[0], c3[1], c3[2], 255)
                    else:
                        cpx[x, y] = (*snap(cpx[x, y][:3]), 255)
                    minx, miny = min(minx, x), min(miny, y)
                    maxx, maxy = max(maxx, x), max(maxy, y)
        if maxx > minx and maxy > miny:
            figs.append(crop.crop((minx, miny, maxx + 1, maxy + 1)))

    if not figs:
        print(f"{name}: no cells found")
        return 0
    uniform = name in GRID
    if uniform:
        # ONE generation holding every animation: its proportions are consistent
        # by construction, so apply ONE scale to every frame — anchored on the
        # first cell, a full standing idle, hitting FIG_H. Head-target scaling
        # would be wrong here: this generation's head-to-body ratio differs from
        # the old sheets', and forcing the mask to 16px pushed bodies past the
        # baseline and cropped heads at the cell top.
        scale = FIG_H / float(figs[0].height)
        print(f"{name}: uniform scale from idle height {figs[0].height}px "
              f"-> {scale:.3f}")
    else:
        # scale from HEAD SIZE, not from the tallest pose — see the note at the top
        heads = [h for h in (mask_height(f) for f in figs) if h > 0]
        med = median(heads)
        if med > 0:
            scale = float(TARGET_MASK_H) / float(med)
            print(f"{name}: median mask {med}px -> scale {scale:.3f} "
                  f"(heads {min(heads)}-{max(heads)})")
        else:
            # no mask visible anywhere (should not happen) — fall back to the old rule
            scale = FIG_H / max(f.height for f in figs)
            print(f"{name}: NO MASK FOUND, falling back to tallest-pose scaling")
    for i, fig in enumerate(figs):
        s = scale
        # PER-FRAME CORRECTION. A single sheet-wide scale still lands heads at
        # target +/-2px through rounding, and at the game's x3 integer scaling that
        # is 6 visible screen pixels. Measure this frame's head after the sheet
        # scale and nudge it onto target. Skipped when the mask is foreshortened
        # (prone, head thrown back) — there the measurement is not a size signal.
        # (skipped for uniform GRID sheets — a per-frame nudge would reintroduce
        # exactly the cross-pose drift the single-generation sheet exists to kill)
        if not uniform and mask_is_square(fig):
            probe_w = max(1, round(fig.width * s))
            probe_h = max(1, round(fig.height * s))
            probe = fig.resize((probe_w, probe_h), Image.NEAREST)
            got = mask_height(probe)
            if got > 0:
                s *= float(TARGET_MASK_H) / float(got)
        nw, nh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
        cell = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        cell.paste(fig.resize((nw, nh), Image.NEAREST),
                   ((96 - nw) // 2, BASELINE - nh))
        cell.save(OUT / f"{name}_{i:02d}.png")

    contact = Image.new("RGBA", (96 * len(figs), 96), (0, 0, 0, 0))
    for i in range(len(figs)):
        contact.paste(Image.open(OUT / f"{name}_{i:02d}.png"), (i * 96, 0))
    contact.resize((contact.width * 4, 384), Image.NEAREST).save(
        OUT / f"{name}_contact_4x.png")
    print(f"{name}: {len(figs)} poses")
    return len(figs)


total = sum(slice_sheet(s) for s in SHEETS)
print(f"total poses: {total}")
