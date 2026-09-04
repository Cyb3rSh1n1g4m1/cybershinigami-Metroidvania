"""Music tracks — lofi hip hop x traditional Japanese (user direction 2026-07-30,
"Creepy Nuts vibe": swung boom-bap drums, plucked koto/shamisen, vinyl warmth).

stdlib only. 16-bit mono 44.1kHz WAV into game/audio/music/. Loops are
SAMPLE-EXACT: every note renders into a fixed-length ring buffer with wraparound,
so tails spill across the loop point instead of being cut — seamless by
construction, no crossfades (DESIGN.md §14b.2).

The koto is Karplus-Strong plucked-string synthesis — a burst of noise cycled
through a damped averaging filter IS a plucked string; brighter excitation and
lower damping turns it shamisen. The 5-note motif lives in the HIRAJOSHI scale
(A B C E F), stated alone in `title`, buried as fragments in `region1`.

Run: python make_music.py
"""
import math
import pathlib
import random
import struct
import wave

SR = 44100
OUT = pathlib.Path(__file__).resolve().parents[2] / "game" / "audio" / "music"
rng = random.Random(0x0029)

# hirajoshi on A — the scale is what makes it read as Japanese
A1, C2, E2, F1 = 55.0, 65.41, 82.41, 43.65
A3, B3, C4, E4, F4 = 220.0, 246.94, 261.63, 329.63, 349.23
A4, B4, C5, E5, F5 = 440.0, 493.88, 523.25, 659.26, 698.46

# THE MOTIF (§14b.2): five notes, falling home. (note, start-16th, dur-s)
MOTIF = [(A4, 0, 0.5), (C5, 2, 0.5), (B4, 4, 0.7), (F4, 8, 0.7), (E4, 12, 1.4)]


def write(name, buf):
    OUT.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in buf))
    k = 0.72 / peak
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * k)) * 32767))
                    for s in buf)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    print(f"ok: {name}.wav  {len(buf) / SR:.2f}s loop")


def decay(n, half_ms):
    k = math.log(2) / (SR * half_ms / 1000)
    return [math.exp(-k * i) for i in range(n)]


def sine(n, f0, f1=None):
    f1 = f1 if f1 is not None else f0
    out, ph = [], 0.0
    for i in range(n):
        f = f0 * (f1 / f0) ** (i / max(1, n - 1))
        ph += 2 * math.pi * f / SR
        out.append(math.sin(ph))
    return out


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def lp(xs, cutoff):
    a = 1.0 - math.exp(-2 * math.pi * cutoff / SR)
    out, y = [], 0.0
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out


def hp(xs, cutoff):
    low = lp(xs, cutoff)
    return [x - l for x, l in zip(xs, low)]


def shape(xs, env):
    return [x * e for x, e in zip(xs, env)]


def gain(xs, g):
    return [x * g for x in xs]


def mixs(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


# -- instruments -------------------------------------------------------------

def pluck(f, dur_s, damp=0.996, tone=3000.0):
    """Karplus-Strong. damp ~0.996 + darker tone = koto; ~0.993 + bright = shamisen."""
    n = int(SR * dur_s)
    period = max(2, int(SR / f))
    buf = lp(noise(period), tone)
    out, prev, i = [], 0.0, 0
    for _ in range(n):
        x = buf[i]
        y = damp * 0.5 * (x + prev)
        prev = x
        buf[i] = y
        out.append(x)
        i = (i + 1) % period
    return shape(out, decay(n, dur_s * 400))


def kick():
    n = int(SR * 0.13)
    return mixs(shape(sine(n, 110, 40), decay(n, 38)),
                gain(shape(hp(noise(int(SR * 0.006)), 2000), decay(int(SR * 0.006), 2)), 0.4))


def snare():
    n = int(SR * 0.14)
    return lp(mixs(
        gain(shape(hp(noise(n), 1500), decay(n, 22)), 0.7),
        gain(shape(sine(n, 190, 160), decay(n, 28)), 0.5)), 6000)


def hat(open_=False):
    n = int(SR * (0.09 if open_ else 0.03))
    return gain(shape(hp(noise(n), 6500), decay(n, 26 if open_ else 7)), 0.6)


def taiko():
    n = int(SR * 0.24)
    return mixs(shape(sine(n, 92, 48), decay(n, 60)),
                gain(shape(lp(noise(n), 320), decay(n, 18)), 0.3))


def pad(freqs, dur_s, attack_s=2.0):
    n = int(SR * dur_s)
    voices = [gain(sine(n, f * (1 + 0.001 * i)), 1.0 / len(freqs))
              for i, f in enumerate(freqs)]
    env = [min(1.0, i / (SR * attack_s)) * min(1.0, (n - i) / (SR * attack_s))
           for i in range(n)]
    return shape(mixs(*voices), env)


def crackle(n, density=0.00018, floor=0.012):
    """Vinyl: sparse ticks over a faint warm noise bed."""
    out = [rng.uniform(-1, 1) * floor for _ in range(n)]
    i = 0
    while i < n:
        if rng.random() < density:
            amp = rng.uniform(0.08, 0.3)
            for j in range(rng.randint(2, 6)):
                if i + j < n:
                    out[i + j] += amp * (1 - j * 0.3) * rng.choice((-1, 1))
            i += rng.randint(400, 4000)
        else:
            i += 137
    return lp(out, 5200)


# -- sequencer ---------------------------------------------------------------

class Song:
    """Fixed-length ring buffer at bpm/bars; place() wraps tails around the
    loop point, which is what makes the loop seamless."""

    def __init__(self, bpm, bars, swing=0.24):
        self.step = 60.0 / bpm / 4.0          # one 16th note, seconds
        self.swing = swing                     # odd 16ths land late: the head-nod
        self.n = round(SR * bars * 16 * self.step)
        self.buf = [0.0] * self.n

    def place(self, smp, at_16th, g=1.0):
        t = at_16th * self.step
        if int(at_16th) % 2 == 1:
            t += self.swing * self.step
        s0 = round(t * SR)
        for i, v in enumerate(smp):
            self.buf[(s0 + i) % self.n] += v * g

    def every_bar(self, smp, in_bar_16th, g=1.0, bars=range(0, 8)):
        for b in bars:
            self.place(smp, b * 16 + in_bar_16th, g)


# -- title: 72 BPM, sparse, the motif alone ----------------------------------

s = Song(72, 8)
s.place(crackle(s.n), 0, 1.0)
s.place(pad([A3 / 2, E4 / 2], s.n / SR, attack_s=3.0), 0, 0.05)

k, sn, h = kick(), snare(), hat()
for b in range(8):
    s.place(k, b * 16 + 0, 0.8)
    s.place(k, b * 16 + 10, 0.55)          # the swung "and of 3"
    s.place(sn, b * 16 + 8, 0.3)           # barely-there backbeat
    s.place(h, b * 16 + 4, 0.25)
    s.place(h, b * 16 + 12, 0.2)

bassline = [A1, A1, C2, E2, A1, A1, F1, E2]     # two beats each, hirajoshi roots
for b, f in enumerate(bassline):
    s.place(pluck(f, 1.6, damp=0.998, tone=900), b * 16, 0.85)

for note, at, dur in MOTIF:                      # stated once, alone (bar 3)
    s.place(pluck(note, dur * 2.2, damp=0.9965, tone=2600), 2 * 16 + at, 0.7)
for note, at, dur in MOTIF:                      # echoed up an octave (bar 7)
    s.place(pluck(note * 2, dur * 2.0, damp=0.996, tone=2200), 6 * 16 + at, 0.35)

write("title", s.buf)

# -- region1_perimeter: 88 BPM head-nod, must survive an hour ----------------

s = Song(88, 8)
s.place(crackle(s.n, density=0.0001, floor=0.008), 0, 1.0)

k, sn = kick(), snare()
h, ho = hat(), hat(open_=True)
for b in range(8):
    s.place(k, b * 16 + 0, 0.9)
    s.place(k, b * 16 + 7, 0.5)            # boom-bap pickup
    s.place(k, b * 16 + 10, 0.7)
    s.place(sn, b * 16 + 4, 0.65)
    s.place(sn, b * 16 + 12, 0.65)
    for st in (2, 6, 10, 14):
        s.place(h, b * 16 + st, 0.28)
    if b % 2 == 1:
        s.place(ho, b * 16 + 14, 0.3)

groove = [(0, A1, 0.7), (7, A1, 0.35), (10, C2, 0.6),
          (16, A1, 0.7), (23, A1, 0.35), (26, E2, 0.6)]   # 2-bar cell
for cell in range(4):
    for at, f, d in groove:
        s.place(pluck(f, d + 0.5, damp=0.998, tone=850), cell * 32 + at, 0.8)

# koto speaks in bars 1-2 and 5-6, rests in between — space is what survives
riff_a = [(A4, 0, 0.4), (C5, 2, 0.4), (E5, 4, 0.9), (C5, 10, 0.5), (B4, 12, 0.9)]
riff_b = [(B4, 0, 0.4), (C5, 2, 0.4), (A4, 4, 0.9), (F4, 10, 0.5), (E4, 12, 0.9)]
for note, at, dur in riff_a:
    s.place(pluck(note, dur * 2.0, damp=0.9965, tone=2600), 0 * 16 + at, 0.5)
for note, at, dur in riff_b:
    s.place(pluck(note, dur * 2.0, damp=0.9965, tone=2600), 4 * 16 + at, 0.5)

# shamisen accent — brighter, snappier — answers at the turnarounds
for bar, note in ((3, C5), (7, A4)):
    s.place(pluck(note, 0.8, damp=0.993, tone=5200), bar * 16 + 14, 0.45)

write("region1_perimeter", s.buf)

# -- combat: LAYERED over region1 (same bpm, same bars = same length, so the
# two stay phase-locked when started at the region player's position).
# Percussion and stabs only — the region track already owns the harmony.

s = Song(88, 8)
tk = taiko()
k2, sn2 = kick(), snare()
h2 = hat()
for b in range(8):
    s.place(tk, b * 16 + 0, 0.9)
    s.place(tk, b * 16 + 10, 0.7)
    if b % 2 == 1:
        s.place(tk, b * 16 + 14, 0.55)         # answering hit every 2nd bar
    s.place(k2, b * 16 + 2, 0.45)              # extra kicks: urgency
    s.place(k2, b * 16 + 13, 0.45)
    for st in (1, 3, 5, 7, 9, 11, 13, 15):     # driving swung offbeat hats
        s.place(h2, b * 16 + st, 0.22)
    s.place(sn2, b * 16 + 12, 0.3)             # ghost under the main backbeat
# shamisen war-stabs: short, bright, rhythmic — Creepy Nuts swagger
for cell in range(4):
    for at, f in ((4, A4), (6, A4), (12, C5)):
        s.place(pluck(f, 0.35, damp=0.990, tone=5600), cell * 32 + at, 0.5)
write("combat", s.buf)

# -- shrine: 60 BPM, the relief moment. Calm but a SONG — the first cut was
# near-silence and could not stand alone. A barely-there lofi heartbeat, warm
# bass roots and two koto phrases keep it breathing without breaking the calm.

s = Song(60, 8, swing=0.2)
s.place(crackle(s.n, density=0.00012, floor=0.010), 0, 1.0)
s.place(pad([A3 / 2, E4 / 2], s.n / SR, attack_s=4.0), 0, 0.06)

k4, sn4, h4 = kick(), snare(), hat()
for b in range(8):
    s.place(k4, b * 16 + 0, 0.5)               # soft heartbeat
    s.place(k4, b * 16 + 10, 0.3)
    s.place(sn4, b * 16 + 8, 0.18)             # brushed, barely present
    s.place(h4, b * 16 + 12, 0.12)

for b, f in enumerate((A1, A1, F1, E2, A1, A1, C2, E2)):
    s.place(pluck(f, 2.6, damp=0.998, tone=700), b * 16, 0.55)

for note, at, dur in MOTIF:                    # the motif, warm and unhurried
    s.place(pluck(note, dur * 2.6, damp=0.997, tone=2200), 1 * 16 + at, 0.5)
answer = [(E4, 0, 0.6), (F4, 3, 0.6), (A4, 6, 0.9), (C5, 10, 0.6), (A4, 12, 1.2)]
for note, at, dur in answer:                   # an answering phrase, bars 5-6
    s.place(pluck(note, dur * 2.2, damp=0.997, tone=2000), 4 * 16 + at, 0.4)

bell_n = int(SR * 1.6)
bell = [math.sin(2 * math.pi * 1740 * i / SR) * math.exp(-i / (SR * 0.5))
        + 0.4 * math.sin(2 * math.pi * 3480 * i / SR) * math.exp(-i / (SR * 0.3))
        for i in range(bell_n)]
s.place(bell, 7 * 16 + 8, 0.18)                # one bell before the loop turns
write("shrine", s.buf)

# -- boss_bruteforce: 96 BPM, the Creepy Nuts track — hard swung beat,
# distorted plucked bass, the motif INVERTED (mirrored contour) on shamisen.

def dist(xs, drive=3.0):
    return [math.tanh(x * drive) for x in xs]

s = Song(96, 8, swing=0.28)
k3, sn3 = kick(), snare()
h3, ho3 = hat(), hat(open_=True)
tk3 = taiko()
for b in range(8):
    s.place(k3, b * 16 + 0, 1.0)
    s.place(k3, b * 16 + 6, 0.7)
    s.place(k3, b * 16 + 10, 0.9)
    s.place(sn3, b * 16 + 4, 0.9)
    s.place(sn3, b * 16 + 12, 0.9)
    if b % 4 == 3:
        s.place(sn3, b * 16 + 15, 0.5)         # turnaround flam
    for st in range(0, 16, 2):
        s.place(h3, b * 16 + st, 0.3)
    s.place(ho3, b * 16 + 14, 0.35)
    s.place(tk3, b * 16 + 8, 0.6)
bass_cell = [(0, A1, 0.5), (3, A1, 0.3), (6, C2, 0.5), (10, A1, 0.4), (13, E2, 0.5)]
for cell in range(8):
    for at, f, d in bass_cell:
        s.place(dist(pluck(f, d + 0.4, damp=0.998, tone=900), 4.0),
                cell * 16 + at, 0.75)
# the motif mirrored: it fell home to E; here it climbs away from A
INVERTED = [(A4, 0, 0.4), (F4, 2, 0.4), (E4, 4, 0.55), (C5, 8, 0.55), (E5, 12, 1.1)]
for b in (2, 6):
    for note, at, dur in INVERTED:
        s.place(pluck(note, dur * 1.8, damp=0.992, tone=5400), b * 16 + at, 0.55)
write("boss_bruteforce", s.buf)
