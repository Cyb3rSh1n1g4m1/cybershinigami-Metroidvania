"""Badge REPL probe: soft-reset to a clean heap, interrupt main.py, then
measure the REAL budget an app gets and the true cost of each asset.

    python repl_probe.py COM4
"""
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM4"
ser = serial.Serial(PORT, 115200, timeout=0.5)


def rd(wait=0.6):
    time.sleep(wait)
    out = b""
    while ser.in_waiting:
        out += ser.read(ser.in_waiting)
        time.sleep(0.05)
    return out.decode("utf-8", "replace")


def send(line, wait=1.0):
    ser.write((line + "\r\n").encode())
    return rd(wait)


ser.write(b"\x03")
rd(0.5)
ser.write(b"\x04")                 # soft reset: fresh heap, main.py starts
time.sleep(4.0)                    # let boot.py mount /system and the cinematic start
for _ in range(3):                 # interrupt the cinematic / menu
    ser.write(b"\x03")
    time.sleep(0.4)
print(rd(0.5)[-400:])
print(send("import os; print('ROOT', os.listdir('/')); print('SYSTEM', os.listdir('/system')); print('APPS', os.listdir('/system/apps'))", 2.0))
print(send("import gc; gc.collect(); print('BASELINE free', gc.mem_free(), 'alloc', gc.mem_alloc())"))

STEPS = [
    "import sys, os; sys.path.insert(0, '/system/apps/cybershinigami'); os.chdir('/system/apps/cybershinigami')",
    "from badgeware import screen, Image, PixelFont, SpriteSheet, io, brushes, shapes, run, State",
    "gc.collect(); print('after imports', gc.mem_free())",
    "img = Image.load('assets/player.png'); gc.collect(); print('player Image.load', gc.mem_free(), img.width, img.height, 'palette', img.has_palette)",
    "before = gc.mem_free(); win = img.window(0, 0, 40, 40); gc.collect(); print('window cost', before - gc.mem_free())",
    "screen.blit(win, 10, 10); print('blit from window ok')",
    "before = gc.mem_free(); sh = SpriteSheet('assets/player.png', 6, 7); gc.collect(); print('SpriteSheet cost', before - gc.mem_free())",
    "before = gc.mem_free(); an = sh.animation(0, 0, 6); gc.collect(); print('animation(6) cost', before - gc.mem_free(), type(an.frame(0)))",
    "del sh, an; gc.collect(); print('freed', gc.mem_free())",
    "before = gc.mem_free(); bg = Image.load('assets/bg_far.png'); gc.collect(); print('bg_far cost', before - gc.mem_free(), bg.has_palette)",
    "before = gc.mem_free(); f1 = PixelFont.load('/system/assets/fonts/nope.ppf'); gc.collect(); print('font cost', before - gc.mem_free())",
    "print('FINAL free', gc.mem_free())",
]
for s in STEPS:
    r = send(s, 2.5)
    # echo comes back first, then results, then the prompt — print the middle
    lines = [ln for ln in r.replace("\r", "").split("\n")
             if ln.strip() and not ln.strip().startswith(">>>") and ln.strip() != s.strip()]
    print("\n".join(lines) if lines else "(no output)")

ser.close()
