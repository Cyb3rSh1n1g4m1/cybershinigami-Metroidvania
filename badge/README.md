# Cybershinigami on the GitHub Universe 2025 badge

An auto-running cut of the Metroidvania for the Pimoroni Tufty 2350 badge
(160x120, RP2350, MicroPython `badgeware`). Same sprites as the game,
downscaled and palettized. **Working on the hardware since 2026-09-04.**

```
badge/
  build_assets.py            game sprites -> apps/cybershinigami/assets/
  sim_headless.py            desktop verification: fake clock, scripted keys, screenshots
  repl_probe.py              talk to the badge's REPL over COM4 (heap + tracebacks)
  badge_backup/menu_original original factory launcher, for rollback
  apps/cybershinigami/
    __init__.py              modes + input; st.py shared state; gfx.py asset loading;
    world.py reaper.py attract.py   (small modules ON PURPOSE - see gotchas)
    icon.png                 24x24 launcher icon
    assets/                  paletted PNG sheets (~38KB on flash, ~72KB in RAM)
```

## Hardware facts that cost a day (read before changing anything)

Measured over the REPL on the real badge, MicroPython 1.26 / mpy v6:

- **An app gets ~150KB of heap, not 512KB.** Framebuffers, WiFi and the C
  runtime own the rest. The simulator's memory estimate measures against the
  wrong ceiling.
- **Source is compiled to bytecode in RAM.** One 18KB `__init__.py` failed to
  compile with `MemoryError`; the pre-installed apps are 2-7KB per file. Keep
  every module under ~6KB.
- **A directory shadows a same-named `.py`.** `assets.py` next to `assets/`
  imports the FOLDER on the badge (CPython prefers the file, so the simulator
  hid it). Never name a module after a folder.
- **`Image.window()` is zero-copy (~736 bytes each)** — but 48 of them is
  35KB. Cache windows only for the player; window enemies/effects per blit.
- Paletted PNGs really are 1 byte/pixel. Load the biggest image first while
  the heap is contiguous; `gc.collect()` between loads.
- **`/system` is read-only from MicroPython.** Files only change via USB disk
  mode (RESET twice). `mpremote cp` fails with "Read-only file system".
- The launcher has **no error screen**: any exception in `init()` looks like a
  freeze. Reproduce over the REPL: soft-reset, wait 4s for `/system` to mount,
  Ctrl-C, scrub `sys.path` (`main.py` leaves a `None` in it when interrupted),
  then `__import__` the app and call `init()`/`update()` by hand.
- Git Bash mangles `/system/...` arguments; use `:/system/...` and
  `MSYS_NO_PATHCONV=1` with mpremote.

## What it does

- **TITLE** — the game's title screen at badge scale (title backdrop, hannya
  logo, plate, wordmark, START / CONTINUE / QUIT). Up/down moves the caret,
  `A` executes. CONTINUE is greyed out (no save yet). QUIT returns to the
  launcher. Eight idle seconds start the demo.
- **DEMO (autoplay)** — a 13-second scripted run: the reaper runs the neon
  city and chains every verb — light cut, jump, double jump, dash, the iai
  hold into a SIGKILL crescent, reaping worms and drones for soul bytes.
  Loops forever. Any button returns to the title.
- **PLAY** — an auto-runner. `A` attack (hold 0.4s and release = SIGKILL
  crescent), `B` jump / double jump, `C` dash (i-frames). Three integrity
  pips, souls as score, high score saved on the badge. Twenty idle seconds
  hands control back to the demo.
- **TERMINATED** — `A` retry, `B` back to the title.

## Test on your computer

The official simulator reproduces `badgeware` on Pygame:

```bash
cd D:/Projects/badger-home            # clone of github.com/badger/home
pip install pygame
cp -r D:/Projects/Cybershinigami/badge/apps/cybershinigami badge/apps/
python simulator/badge_simulator.py badge/apps/cybershinigami --perf
```

Keys: `A/Z` = A, `B/X` = B, `C/Space` = C, `H/Esc` = Home, `F12` screenshot.

## Install on the badge

1. Connect the badge over USB-C and press **RESET twice** — it mounts as a
   drive named `BADGER` (the FAT32 `/system/` partition).
2. Copy the whole `apps/cybershinigami/` folder into `/system/apps/`.
3. Eject, press RESET once. The app appears in the launcher.

The factory launcher shows six icons per page; the badge ships with several
apps, so you may need the paginated menu from the `badger/home` repo (copy
`badge/apps/menu/` over `/system/apps/menu/`) to reach the new icon.

## Rebuilding assets

After any change to the game's strips:

```bash
cd D:/Projects/Cybershinigami/badge
python build_assets.py
```

The player sheet is 6 columns x 3 rows of 40x40 cells (18 runner frames);
`PLAYER` in `build_assets.py` and `P` in `gfx.py` must agree on frame order.
Verify on the desktop before a badge round-trip:

```bash
cd D:/Projects/badger-home
cp -r D:/Projects/Cybershinigami/badge/apps/cybershinigami badge/apps/
python D:/Projects/Cybershinigami/badge/sim_headless.py   # screenshots in shots/
```
