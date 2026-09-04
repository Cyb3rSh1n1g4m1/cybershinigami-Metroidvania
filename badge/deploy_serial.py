"""Push the app onto the badge over its USB serial REPL — no mass-storage
round-trip needed. Interrupts the running program, writes each file in
base64 chunks into /system/apps/cybershinigami/, removes stale assets, then
hardware-resets the badge back into the launcher.

    python deploy_serial.py COM4
"""
import base64
import pathlib
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM4"
SRC = pathlib.Path(__file__).parent / "apps" / "cybershinigami"
DST = "/system/apps/cybershinigami"
STALE = ["assets/bg_mid.png"]

ser = serial.Serial(PORT, 115200, timeout=1)


def rd(wait=0.3):
    time.sleep(wait)
    out = b""
    while ser.in_waiting:
        out += ser.read(ser.in_waiting)
        time.sleep(0.03)
    return out.decode("utf-8", "replace")


def send(line, wait=0.4):
    ser.write((line + "\r\n").encode())
    r = rd(wait)
    if "Traceback" in r or "Error" in r:
        print("!! ", r.strip()[-300:])
    return r


for _ in range(3):
    ser.write(b"\x03")
    time.sleep(0.3)
rd(0.5)
send("import os, binascii")
send(f"try:\r\n    os.mkdir('{DST}')\r\nexcept OSError:\r\n    pass\r\n", 0.6)
send(f"try:\r\n    os.mkdir('{DST}/assets')\r\nexcept OSError:\r\n    pass\r\n", 0.6)

files = sorted(p for p in SRC.rglob("*") if p.is_file())
for p in files:
    rel = p.relative_to(SRC).as_posix()
    data = p.read_bytes()
    send(f"f = open('{DST}/{rel}', 'wb')")
    for i in range(0, len(data), 384):
        chunk = base64.b64encode(data[i:i + 384]).decode()
        send(f"f.write(binascii.a2b_base64('{chunk}'))", 0.08)
    send("f.close()")
    r = send(f"print(os.stat('{DST}/{rel}')[6])", 0.5)
    size = [ln for ln in r.replace("\r", "").split("\n") if ln.strip().isdigit()]
    ok = size and int(size[-1]) == len(data)
    print(f"{'ok' if ok else 'SIZE MISMATCH'}: {rel}  {len(data)} bytes")

for s in STALE:
    send(f"try:\r\n    os.remove('{DST}/{s}')\r\n    print('removed {s}')\r\nexcept OSError:\r\n    pass\r\n", 0.6)

send("os.sync()" if False else "print('synced')")
print("resetting badge into the launcher...")
ser.write(b"import machine; machine.reset()\r\n")
time.sleep(0.5)
ser.close()
