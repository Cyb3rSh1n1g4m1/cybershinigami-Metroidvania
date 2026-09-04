"""Single-variable HALO-pass ablation for slice_sheets.py's sheet_mega pipeline.

Copy of audit_slice.py with ONLY the halo pass parametrized behind a flag.
Every other pass (flood, pockets, despeckle) and every metric definition is
byte-for-byte the same logic as audit_slice.py.

Variants (sys.argv[1]):
  baseline : halo on, near_any tol 52, 2 sweeps   (sanity check vs audit_slice)
  off      : halo pass disabled entirely
  tol30    : near_any tol lowered 52 -> 30 (halo_extra tests unchanged)
  sweep1   : 1 sweep instead of 2 (tol 52 unchanged)

Run: python audit_halo.py <variant>     (cwd: art/player)

READ-ONLY on the source sheet; writes nothing into sheet_frames/.
"""
from collections import deque
import pathlib
import sys

import numpy as np
from PIL import Image

REF = pathlib.Path("../reference")

NAME = "sheet_mega"
GRID = {"sheet_mega": (6, 5)}          # same assertion as slice_sheets.py

MASK_CRIMSONS = [(224, 31, 38), (143, 17, 22), (130, 13, 31), (89, 27, 30)]

# pass tags
T_KEPT, T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE = 0, 1, 2, 3, 4
PASS_NAMES = {T_FLOOD: "flood", T_HALO: "halo",
              T_POCKET: "pocket", T_DESPECKLE: "despeckle"}

VARIANTS = {
    #            enabled, tol, sweeps
    "baseline": (True, 52, 2),
    "off":      (False, 52, 2),
    "tol30":    (True, 30, 2),
    "sweep1":   (True, 52, 1),
}


def near_mask(a, colour, tol):
    """Vectorized twin of slice_sheets.near(): per-channel abs diff <= tol."""
    return (np.abs(a.astype(np.int16) - np.array(colour, np.int16)) <= tol).all(axis=2)


def near_any_mask(a, colours, tol):
    m = np.zeros(a.shape[:2], bool)
    for c in colours:
        m |= near_mask(a, c, tol)
    return m


def audit(halo_enabled, halo_tol, halo_sweeps, label):
    img = Image.open(REF / f"{NAME}.png").convert("RGB")
    W, H = img.size
    arr_full = np.asarray(img, np.uint8)

    # --- background polarity from corners (identical to slice_sheets.py)
    corners = [tuple(arr_full[0, 0]), tuple(arr_full[0, W - 1]),
               tuple(arr_full[H - 1, 0]), tuple(arr_full[H - 1, W - 1])]
    dark_bg = sum(max(int(v) for v in c) for c in corners) / 4 < 110
    print(f"{NAME}: {'dark' if dark_bg else 'light'} background | "
          f"halo variant={label} enabled={halo_enabled} tol={halo_tol} "
          f"sweeps={halo_sweeps}")

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

    results = []            # per-cell metric dicts

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
        near_halo = near_any_mask(cell, cell_bgs, halo_tol)   # ABLATION VARIABLE
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
        halo_ok = near_halo | halo_extra
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

        # --- PASS 2: halo erosion (ABLATION: enabled / tol / sweep count)
        if halo_enabled:
            for _ in range(halo_sweeps):
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

        # ---------- DAMAGE METRICS (identical to audit_slice.py) ----------
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

    # ---------- REPORT ----------
    def pct(n, d):
        return 100.0 * n / d if d else 0.0

    hdr = (f"{'cell':>4} {'srcfig':>7} {'eroded':>7} {'ero%':>6} "
           f"{'maskero':>7} {'mask%':>6} {'whitero':>7} {'white%':>6} "
           f"{'noise':>6} {'noise%':>6}  {'flood':>6} {'halo':>6} "
           f"{'pocket':>6} {'despk':>6}")
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
              f"{k[T_DESPECKLE]:>6}")

    tot_src = sum(r["src"] for r in results)
    tot_ero = sum(r["eroded"] for r in results)
    tot_mask = sum(r["mask_eroded"] for r in results)
    tot_white = sum(r["white_eroded"] for r in results)
    tot_noise = sum(r["noise_kept"] for r in results)
    tot_kills = {p: sum(r["kills"][p] for r in results)
                 for p in (T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE)}
    print("-" * len(hdr))
    print(f"TOTAL src figure px {tot_src} | eroded {tot_ero} "
          f"({pct(tot_ero, tot_src):.2f}%) | mask_eroded {tot_mask} "
          f"({pct(tot_mask, tot_src):.2f}%) | white_eroded {tot_white} "
          f"({pct(tot_white, tot_src):.2f}%) | noise_kept {tot_noise} "
          f"({pct(tot_noise, tot_src):.2f}%)")
    print("PER-PASS KILLS (eroded figure px only): "
          + ", ".join(f"{PASS_NAMES[p]} {tot_kills[p]}"
                      for p in (T_FLOOD, T_HALO, T_POCKET, T_DESPECKLE)))
    print(f"SUMMARY|{label}|src={tot_src}|eroded={tot_ero}|"
          f"eroded_pct={pct(tot_ero, tot_src):.4f}|mask={tot_mask}|"
          f"mask_pct={pct(tot_mask, tot_src):.4f}|white={tot_white}|"
          f"white_pct={pct(tot_white, tot_src):.4f}|noise={tot_noise}|"
          f"noise_pct={pct(tot_noise, tot_src):.4f}")


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if label not in VARIANTS:
        sys.exit(f"unknown variant {label!r}; pick one of {sorted(VARIANTS)}")
    enabled, tol, sweeps = VARIANTS[label]
    audit(enabled, tol, sweeps, label)
