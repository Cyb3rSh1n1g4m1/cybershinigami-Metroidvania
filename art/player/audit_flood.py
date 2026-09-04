"""Single-variable ablation of the FLOOD classification in slice_sheets.py.

Copy of audit_slice.py with the border-flood background test switchable via a
command-line flag. ONLY the flood classification changes; the halo, pocket and
despeckle passes, and every DAMAGE METRIC definition, are untouched so numbers
stay comparable to the audit_slice.py baseline (eroded 11.21%, mask 0.00%,
white 9.46%, noise 0.16%).

Settings (sys.argv[1], default "baseline"):
  baseline : cell_is_bg = near_any(fills, 26) | is_bg          (as shipped)
  a_tol16  : cell_is_bg = near_any(fills, 16) | is_bg
  b_tol34  : cell_is_bg = near_any(fills, 34) | is_bg
  c_satadj : baseline test, but a pixel may NOT flood if any 4-neighbour is
             strongly saturated (max(c)-min(c) > SAT_SPREAD). Fill colours are
             near-neutral; the mask crimsons / olive wraps are not, so this
             stops the flood one pixel short of saturated art.

DAMAGE METRICS (per cell, pre-scale pixel grid = the inset cell) — identical
to audit_slice.py, NEVER varied with the setting:
  source figure pixels : inset-cell pixels NOT within tol 26 (per-channel) of
                         either of that cell's two ring-fill colours, and not
                         part of residual border hairlines.
  eroded               : source figure pixels transparent in the cleaned
                         pre-scale figure.
  mask_eroded          : eroded pixels within tol 30 of any mask crimson
                         (224,31,38) (143,17,22) (130,13,31) (89,27,30).
  white_eroded         : eroded pixels with min(r,g,b) > 185.
  noise_kept           : pixels kept opaque that ARE within tol 12 of a fill.

Run: python audit_flood.py [baseline|a_tol16|b_tol34|c_satadj]  (cwd: art/player)

This script only READS the source sheet; it never writes into sheet_frames/.
"""
from collections import deque
import pathlib
import sys

import numpy as np
from PIL import Image

SETTING = sys.argv[1] if len(sys.argv) > 1 else "baseline"
assert SETTING in ("baseline", "a_tol16", "b_tol34", "c_satadj"), SETTING

# Strongly-saturated spread threshold for c_satadj. Must sit ABOVE the spread
# of any ring-fill colour (cream/olive/white bands are near-neutral) and BELOW
# the art we are protecting: mask crimson (224,31,38) spread 193, (89,27,30)
# spread 62, olive hilt wrap (107,138,15) spread 123.
SAT_SPREAD = 60

REF = pathlib.Path("../reference")
AUDIT_OUT = pathlib.Path("sheet_frames_audit_flood") / SETTING
AUDIT_OUT.mkdir(parents=True, exist_ok=True)

NAME = "sheet_mega"
GRID = {"sheet_mega": (6, 5)}          # same assertion as slice_sheets.py

MASK_CRIMSONS = [(224, 31, 38), (143, 17, 22), (130, 13, 31), (89, 27, 30)]

# pass tags
T_KEPT, T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE = 0, 1, 2, 3, 4
PASS_NAMES = {T_FLOOD: "flood", T_HALO: "halo",
              T_POCKET: "pocket", T_DESPECKLE: "despeckle"}


def near_mask(a, colour, tol):
    """Vectorized twin of slice_sheets.near(): per-channel abs diff <= tol."""
    return (np.abs(a.astype(np.int16) - np.array(colour, np.int16)) <= tol).all(axis=2)


def near_any_mask(a, colours, tol):
    m = np.zeros(a.shape[:2], bool)
    for c in colours:
        m |= near_mask(a, c, tol)
    return m


def audit():
    print(f"FLOOD ABLATION SETTING: {SETTING}"
          + (f" (SAT_SPREAD={SAT_SPREAD})" if SETTING == "c_satadj" else ""))
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

    results = []            # per-cell metric dicts
    panels = {}             # cell idx -> (src_arr, bg, tag, eroded_mask)

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
        near12 = near_any_mask(cell, cell_bgs, 12)
        near8 = near_any_mask(cell, cell_bgs, 8)
        isbg = is_bg_mask(cell)

        mx = cell.max(axis=2).astype(np.int16)
        mn = cell.min(axis=2).astype(np.int16)

        # ======== THE SINGLE ABLATED VARIABLE: flood classification ========
        if SETTING == "a_tol16":
            flood_near = near_any_mask(cell, cell_bgs, 16)
        elif SETTING == "b_tol34":
            flood_near = near_any_mask(cell, cell_bgs, 34)
        else:                              # baseline and c_satadj
            flood_near = near26
        cell_is_bg = flood_near | isbg
        if SETTING == "c_satadj":
            sat = (mx - mn) > SAT_SPREAD
            adj_sat = np.zeros_like(sat)
            adj_sat[1:, :] |= sat[:-1, :]
            adj_sat[:-1, :] |= sat[1:, :]
            adj_sat[:, 1:] |= sat[:, :-1]
            adj_sat[:, :-1] |= sat[:, 1:]
            cell_is_bg &= ~adj_sat
        # ===================================================================

        if dark_bg:
            halo_extra = (mx < 9) | ((mx < 150) & (mx - mn < 7))
            pure_extra = (mx < 4) | ((mx >= 68) & (mx < 94) & (mx - mn < 5))
        else:
            halo_extra = (mn > 170) & (mx - mn < 30)
            pure_extra = (mn > 242) & (mx - mn < 8)
        halo_ok = near52 | halo_extra
        pure_bg = near8 | pure_extra

        bg = np.zeros((ch, cw), bool)
        tag = np.zeros((ch, cw), np.uint8)

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
                tag[y, x] = T_FLOOD
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
            tag[edge] = T_HALO

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
                        tag[y, x] = T_POCKET

        # --- PASS 4: despeckle components < 12 px
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
                if len(comp) < 12:
                    for x, y in comp:
                        bg[y, x] = True
                        tag[y, x] = T_DESPECKLE

        # ---------- DAMAGE METRICS (FIXED definitions, never ablated) ----------
        # residual border hairlines: near-solid dark rows/cols within 10px of
        # the inset-cell edge (the drawn dividers drift; the 5px inset does not
        # always clear them). Only their DARK pixels are excluded.
        dark = mx < 110
        hairline = np.zeros((ch, cw), bool)
        for y in list(range(min(10, ch))) + list(range(max(0, ch - 10), ch)):
            if dark[y].mean() >= 0.8:
                hairline[y] |= dark[y]
        for x in list(range(min(10, cw))) + list(range(max(0, cw - 10), cw)):
            if dark[:, x].mean() >= 0.8:
                hairline[:, x] |= dark[:, x]

        src_fig = ~near26 & ~hairline
        eroded = src_fig & bg
        mask_red = near_any_mask(cell, MASK_CRIMSONS, 30)
        mask_eroded = eroded & mask_red
        white_eroded = eroded & (mn > 185)
        noise_kept = ~bg & near12

        n_src = int(src_fig.sum())
        kills = {p: int((eroded & (tag == p)).sum())
                 for p in (T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE)}
        results.append({
            "cell": idx,
            "fills": cell_bgs,
            "src": n_src,
            "eroded": int(eroded.sum()),
            "mask_eroded": int(mask_eroded.sum()),
            "white_eroded": int(white_eroded.sum()),
            "noise_kept": int(noise_kept.sum()),
            "kills": kills,
        })
        panels[idx] = (cell.copy(), bg.copy(), eroded.copy())

    # ---------- REPORT ----------
    def pct(n, d):
        return 100.0 * n / d if d else 0.0

    hdr = (f"{'cell':>4} {'srcfig':>7} {'eroded':>7} {'ero%':>6} "
           f"{'maskero':>7} {'mask%':>6} {'whitero':>7} {'white%':>6} "
           f"{'noise':>6} {'noise%':>6}  {'flood':>6} {'halo':>6} "
           f"{'pocket':>6} {'despk':>6}  fills")
    print()
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        k = r["kills"]
        print(f"{r['cell']:>4} {r['src']:>7} {r['eroded']:>7} "
              f"{pct(r['eroded'], r['src']):>6.2f} "
              f"{r['mask_eroded']:>7} {pct(r['mask_eroded'], r['src']):>6.2f} "
              f"{r['white_eroded']:>7} {pct(r['white_eroded'], r['src']):>6.2f} "
              f"{r['noise_kept']:>6} {pct(r['noise_kept'], r['src']):>6.2f}  "
              f"{k[T_FLOOD]:>6} {k[T_HALO]:>6} {k[T_POCKET]:>6} "
              f"{k[T_DESPECKLE]:>6}  {r['fills']}")

    tot_src = sum(r["src"] for r in results)
    tot_ero = sum(r["eroded"] for r in results)
    tot_mask = sum(r["mask_eroded"] for r in results)
    tot_white = sum(r["white_eroded"] for r in results)
    tot_noise = sum(r["noise_kept"] for r in results)
    tot_kills = {p: sum(r["kills"][p] for r in results)
                 for p in (T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE)}
    print("-" * len(hdr))
    print(f"SETTING {SETTING} TOTAL src figure px {tot_src} | eroded {tot_ero} "
          f"({pct(tot_ero, tot_src):.2f}%) | mask_eroded {tot_mask} "
          f"({pct(tot_mask, tot_src):.2f}%) | white_eroded {tot_white} "
          f"({pct(tot_white, tot_src):.2f}%) | noise_kept {tot_noise} "
          f"({pct(tot_noise, tot_src):.2f}%)")
    print("PER-PASS KILLS (eroded figure px only): "
          + ", ".join(f"{PASS_NAMES[p]} {tot_kills[p]}"
                      for p in (T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE)))

    # ---------- 3-up comparisons for the 5 worst cells ----------
    worst = sorted(results, key=lambda r: pct(r["eroded"], r["src"]),
                   reverse=True)[:5]
    print("\nWORST 5 CELLS by eroded%:")
    for r in worst:
        k = r["kills"]
        dom = max(k, key=k.get)
        print(f"  cell {r['cell']:2d}: eroded {pct(r['eroded'], r['src']):.2f}% "
              f"(dominant pass: {PASS_NAMES[dom]}, "
              f"mask {pct(r['mask_eroded'], r['src']):.2f}%, "
              f"white {pct(r['white_eroded'], r['src']):.2f}%)")
        cell, bg, eroded = panels[r["cell"]]
        ch, cw = bg.shape
        # panel 1: source inset cell
        p1 = cell
        # panel 2: cleaned figure over a dark backdrop
        p2 = np.full_like(cell, 44)
        p2[~bg] = cell[~bg]
        # panel 3: dimmed source with eroded figure pixels in magenta
        p3 = (cell.astype(np.float32) * 0.35).astype(np.uint8)
        p3[eroded] = (255, 0, 255)
        gap = np.full((ch, 6, 3), 128, np.uint8)
        strip = np.concatenate([p1, gap, p2, gap, p3], axis=1)
        out = Image.fromarray(strip).resize(
            (strip.shape[1] * 2, strip.shape[0] * 2), Image.NEAREST)
        path = AUDIT_OUT / f"worst_cell_{r['cell']:02d}.png"
        out.save(path)
        print(f"           -> {path}")

    return results, tot_kills


if __name__ == "__main__":
    audit()
