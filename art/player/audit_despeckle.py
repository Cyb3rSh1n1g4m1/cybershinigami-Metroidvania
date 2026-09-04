"""Single-variable ablation of the DESPECKLE pass in slice_sheets.py.

Derived from audit_slice.py (the measurement instrument). Passes 1-3
(border flood, 2-sweep halo erosion, sealed pockets) are computed ONCE per
cell, then each despeckle setting runs on a copy of that state, so every
difference in the metrics is attributable to the despeckle pass alone.

Settings (DESPECKLE_MODES):
  baseline : remove connected components < 12 px           (current pipeline)
  off      : despeckle disabled entirely
  thresh6  : remove connected components < 6 px
  fillgate : remove components < 12 px ONLY if every pixel of the component
             is within tol 20 (per-channel) of one of the cell's fill colours

DAMAGE METRICS are identical to audit_slice.py (see its docstring).

Run: python audit_despeckle.py     (cwd: art/player)
READ-ONLY on the source sheet; writes nothing into sheet_frames/.
"""
from collections import deque
import pathlib

import numpy as np
from PIL import Image

REF = pathlib.Path("../reference")

NAME = "sheet_mega"
GRID = {"sheet_mega": (6, 5)}          # same assertion as slice_sheets.py

MASK_CRIMSONS = [(224, 31, 38), (143, 17, 22), (130, 13, 31), (89, 27, 30)]

DESPECKLE_MODES = ["baseline", "off", "thresh6", "fillgate"]


def near_mask(a, colour, tol):
    """Vectorized twin of slice_sheets.near(): per-channel abs diff <= tol."""
    return (np.abs(a.astype(np.int16) - np.array(colour, np.int16)) <= tol).all(axis=2)


def near_any_mask(a, colours, tol):
    m = np.zeros(a.shape[:2], bool)
    for c in colours:
        m |= near_mask(a, c, tol)
    return m


def despeckle(bg, near20, mode):
    """Run one despeckle setting on a COPY of the pass-3 bg state.
    Returns (bg_after, killed_mask)."""
    bg = bg.copy()
    ch, cw = bg.shape
    killed = np.zeros((ch, cw), bool)
    if mode == "off":
        return bg, killed
    thresh = 6 if mode == "thresh6" else 12
    lab = np.zeros((ch, cw), bool)
    for sx in range(cw):
        for sy in range(ch):
            if bg[sy, sx] or lab[sy, sx]:
                continue
            comp, stack = [], [(sx, sy)]
            lab[sy, sx] = True
            while stack:
                x, y = stack.pop()
                comp.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < cw and 0 <= ny < ch
                            and not lab[ny, nx] and not bg[ny, nx]):
                        lab[ny, nx] = True
                        stack.append((nx, ny))
            if len(comp) < thresh:
                if mode == "fillgate" and not all(near20[y, x] for x, y in comp):
                    continue           # small but NOT fill-coloured: keep it
                for x, y in comp:
                    bg[y, x] = True
                    killed[y, x] = True
    return bg, killed


def audit():
    img = Image.open(REF / f"{NAME}.png").convert("RGB")
    W, H = img.size
    arr_full = np.asarray(img, np.uint8)

    # --- background polarity from corners (identical to slice_sheets.py)
    corners = [tuple(arr_full[0, 0]), tuple(arr_full[0, W - 1]),
               tuple(arr_full[H - 1, 0]), tuple(arr_full[H - 1, W - 1])]
    dark_bg = sum(max(int(v) for v in c) for c in corners) / 4 < 110
    print(f"{NAME}: {'dark' if dark_bg else 'light'} background")

    def is_bg_mask(a):
        mx = a.max(axis=2).astype(np.int16)
        mn = a.min(axis=2).astype(np.int16)
        if dark_bg:
            m = mx < 6
            m |= (mx < 26) & (mx - mn < 6)
            m |= (mx >= 64) & (mx < 100) & (mx - mn < 6)
            return m
        return (a[..., 0] > 185) & (a[..., 1] > 185) & (a[..., 2] > 185) \
            & (mx - mn < 26)

    # --- asserted grid, same arithmetic as slice_sheets.py
    cols, rows = GRID[NAME]
    cells = []
    cw_step = W / float(cols)
    ch_step = H / float(rows)
    for r in range(rows):
        for c in range(cols):
            cells.append((int(c * cw_step), int(r * ch_step),
                          int((c + 1) * cw_step), int((r + 1) * ch_step)))
    print(f"{NAME}: asserted {cols}x{rows} grid = {len(cells)} cells")

    # totals[mode] accumulates across cells
    totals = {m: {"src": 0, "eroded": 0, "mask": 0, "white": 0,
                  "noise": 0, "despk_fig_kills": 0}
              for m in DESPECKLE_MODES}

    for idx, (x0, y0, x1, y1) in enumerate(cells):
        cell = arr_full[y0:y1, x0:x1]
        cw, ch = cell.shape[1], cell.shape[0]

        # --- 5px inset past the drawn divider hairlines (GRID path)
        inset = 5
        cell = cell[inset:ch - inset, inset:cw - inset]
        ch, cw = cell.shape[0], cell.shape[1]

        # --- ring fill sampling, identical bucketing (//8, top 2, >=12% of ring)
        ring = ([tuple(cell[0, x]) for x in range(cw)]
                + [tuple(cell[ch - 1, x]) for x in range(cw)]
                + [tuple(cell[y, 0]) for y in range(ch)]
                + [tuple(cell[y, cw - 1]) for y in range(ch)])
        buckets = {}
        for c in ring:
            c = tuple(int(v) for v in c)
            buckets.setdefault((c[0] // 8, c[1] // 8, c[2] // 8), []).append(c)
        cell_bgs = []
        ranked = sorted(buckets.values(), key=len, reverse=True)
        for members in ranked[:2]:
            if len(members) >= len(ring) * 0.12:
                cell_bgs.append(tuple(round(sum(v) / len(members))
                                      for v in zip(*members)))

        # --- vectorized predicates (exact twins of the per-pixel tests)
        near26 = near_any_mask(cell, cell_bgs, 26)
        near52 = near_any_mask(cell, cell_bgs, 52)
        near20 = near_any_mask(cell, cell_bgs, 20)
        near12 = near_any_mask(cell, cell_bgs, 12)
        near8 = near_any_mask(cell, cell_bgs, 8)
        isbg = is_bg_mask(cell)
        cell_is_bg = near26 | isbg

        mx = cell.max(axis=2).astype(np.int16)
        mn = cell.min(axis=2).astype(np.int16)
        if dark_bg:
            halo_extra = (mx < 9) | ((mx < 150) & (mx - mn < 7))
            pure_extra = (mx < 4) | ((mx >= 68) & (mx < 94) & (mx - mn < 5))
        else:
            halo_extra = (mn > 170) & (mx - mn < 30)
            pure_extra = (mn > 242) & (mx - mn < 8)
        halo_ok = near52 | halo_extra
        pure_bg = near8 | pure_extra

        bg = np.zeros((ch, cw), bool)

        # --- PASS 1: border flood
        q = deque()
        for x in range(cw):
            q.append((x, 0))
            q.append((x, ch - 1))
        for y in range(ch):
            q.append((0, y))
            q.append((cw - 1, y))
        while q:
            x, y = q.popleft()
            if not (0 <= x < cw and 0 <= y < ch) or bg[y, x]:
                continue
            if cell_is_bg[y, x]:
                bg[y, x] = True
                q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

        # --- PASS 2: 2-sweep halo erosion (collect whole edge set, then apply)
        for _ in range(2):
            adj = np.zeros((ch, cw), bool)
            adj[1:, :] |= bg[:-1, :]
            adj[:-1, :] |= bg[1:, :]
            adj[:, 1:] |= bg[:, :-1]
            adj[:, :-1] |= bg[:, 1:]
            edge = ~bg & halo_ok & adj
            bg |= edge

        # --- PASS 3: sealed pockets (exact DFS with the early-break cap quirk)
        seen = np.zeros((ch, cw), bool)
        max_pocket = max(200, int(cw * ch * 0.05))
        for sx in range(cw):                       # x-major, same as original
            for sy in range(ch):
                if bg[sy, sx] or seen[sy, sx] or not pure_bg[sy, sx]:
                    continue
                comp, stack = [], [(sx, sy)]
                seen[sy, sx] = True
                while stack:
                    x, y = stack.pop()
                    comp.append((x, y))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < cw and 0 <= ny < ch and not seen[ny, nx]
                                and not bg[ny, nx] and pure_bg[ny, nx]):
                            seen[ny, nx] = True
                            stack.append((nx, ny))
                    if len(comp) > max_pocket:
                        break                      # too big: it is the garment
                if len(comp) <= max_pocket:
                    for x, y in comp:
                        bg[y, x] = True

        # ---------- DAMAGE METRICS (shared masks) ----------
        dark = mx < 110
        hairline = np.zeros((ch, cw), bool)
        for y in list(range(min(10, ch))) + list(range(max(0, ch - 10), ch)):
            if dark[y].mean() >= 0.8:
                hairline[y] |= dark[y]
        for x in list(range(min(10, cw))) + list(range(max(0, cw - 10), cw)):
            if dark[:, x].mean() >= 0.8:
                hairline[:, x] |= dark[:, x]

        src_fig = ~near26 & ~hairline
        mask_red = near_any_mask(cell, MASK_CRIMSONS, 30)
        white_px = mn > 185

        # --- PASS 4 ablation: each setting from the SAME pass-3 state
        for mode in DESPECKLE_MODES:
            bg_final, killed = despeckle(bg, near20, mode)
            eroded = src_fig & bg_final
            t = totals[mode]
            t["src"] += int(src_fig.sum())
            t["eroded"] += int(eroded.sum())
            t["mask"] += int((eroded & mask_red).sum())
            t["white"] += int((eroded & white_px).sum())
            t["noise"] += int((~bg_final & near12).sum())
            t["despk_fig_kills"] += int((src_fig & killed).sum())

    # ---------- REPORT ----------
    def pct(n, d):
        return 100.0 * n / d if d else 0.0

    hdr = (f"{'setting':>9} {'srcfig':>7} {'eroded':>7} {'ero%':>6} "
           f"{'maskero':>7} {'mask%':>6} {'whitero':>7} {'white%':>6} "
           f"{'noise':>6} {'noise%':>6} {'despk_kills':>11}")
    print()
    print(hdr)
    print("-" * len(hdr))
    for mode in DESPECKLE_MODES:
        t = totals[mode]
        print(f"{mode:>9} {t['src']:>7} {t['eroded']:>7} "
              f"{pct(t['eroded'], t['src']):>6.2f} "
              f"{t['mask']:>7} {pct(t['mask'], t['src']):>6.2f} "
              f"{t['white']:>7} {pct(t['white'], t['src']):>6.2f} "
              f"{t['noise']:>6} {pct(t['noise'], t['src']):>6.2f} "
              f"{t['despk_fig_kills']:>11}")
    return totals


if __name__ == "__main__":
    audit()
