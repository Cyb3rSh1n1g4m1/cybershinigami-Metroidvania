"""Sound-direction sampler: swing / hit / jump in FOUR style lanes, so the
direction gets chosen by ear instead of by adjective. Writes to sampler/ —
NOT the game folder; the winning lane gets the full [slice] regenerated.

  A_arcade_*   8-bit NES: square waves, hard gates, no noise texture
  B_crunch_*   16-bit SNES: today's designs but decimated + driven, punchier
  C_steel_*    anime foley: real-blade shing, metallic shimmer, breathy body
  D_glitch_*   cyber-glitch: FM zaps, stutter gates, bit-mangled artifacts

Run: python make_sampler.py
"""
import math
import pathlib
import random
import struct
import wave

SR = 44100
OUT = pathlib.Path(__file__).parent / "sampler"
rng = random.Random(0x0029)


def write(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    k = 0.89 / peak
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * k)) * 32767))
                    for s in samples)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    print(f"ok: {name}.wav")


def ms(v):
    return int(SR * v / 1000)


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


def square(n, f0, f1=None):
    return [1.0 if s >= 0 else -1.0 for s in sine(n, f0, f1)]


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


def band(xs, center, width=0.5):
    return hp(lp(xs, center * (1 + width)), center * (1 - width))


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def gain(xs, g):
    return [x * g for x in xs]


def shape(xs, env):
    return [x * e for x, e in zip(xs, env)]


def clip(xs, drive=2.5):
    return [math.tanh(x * drive) for x in xs]


def crush(xs, hold=4, bits=6):
    """Sample-and-hold decimation + bit quantize — instant retro."""
    out, held = [], 0.0
    q = float(2 ** (bits - 1))
    for i, x in enumerate(xs):
        if i % hold == 0:
            held = round(x * q) / q
        out.append(held)
    return out


def gate(xs, hz, duty=0.6):
    """Amplitude stutter — a hard tremolo square."""
    period = SR / hz
    return [x * (1.0 if (i % period) < period * duty else 0.15)
            for i, x in enumerate(xs)]


def fm(n, carrier, ratio, index, half_ms):
    """FM zap: modulator sweeps the carrier; classic digital sting."""
    out, ph = [], 0.0
    env = decay(n, half_ms)
    for i in range(n):
        m = math.sin(2 * math.pi * carrier * ratio * i / SR)
        ph += 2 * math.pi * (carrier + index * carrier * m * env[i]) / SR
        out.append(math.sin(ph) * env[i])
    return out


def metallic(n, f0, half_ms, ratios=(1.0, 2.76, 5.40, 8.93)):
    parts = [gain(sine(n, f0 * r), 1.0 / (i + 1)) for i, r in enumerate(ratios)]
    return shape(mix(*parts), decay(n, half_ms))


# -- A: 8-bit arcade ---------------------------------------------------------

n = ms(90)
write("A_arcade_swing", shape(square(n, 1800, 350), decay(n, 30)))

n = ms(85)
write("A_arcade_hit", crush(shape(noise(n), decay(n, 16)), hold=6, bits=4))

s1, s2, s3 = ms(40), ms(40), ms(60)
write("A_arcade_jump",
      shape(square(s1, 262), decay(s1, 30))
      + shape(square(s2, 392), decay(s2, 30))
      + shape(square(s3, 523), decay(s3, 24)))

# -- B: 16-bit crunch --------------------------------------------------------

n = ms(140)
hump = [math.sin(math.pi * i / n) ** 1.5 for i in range(n)]
write("B_crunch_swing", crush(clip(shape(band(noise(n), 1400, 0.6), hump), 2.0), hold=2))

n = ms(95)
write("B_crunch_hit", crush(clip(mix(
    gain(shape(noise(n), decay(n, 8)), 0.7),
    gain(metallic(n, 280, 28), 0.9)), 2.2), hold=2))

n = ms(130)
write("B_crunch_jump", crush(mix(
    gain(shape(sine(n, 190, 560), decay(n, 45)), 0.8),
    gain(shape(hp(noise(n), 1800), decay(n, 25)), 0.25)), hold=2))

# -- C: anime steel ----------------------------------------------------------

n = ms(200)
shing = metallic(n, 3800, 60, ratios=(1.0, 1.34, 2.1, 2.9))   # high, tight, ringing
whoosh_env = [math.sin(math.pi * i / n) ** 2 for i in range(n)]
write("C_steel_swing", mix(
    gain(shing, 0.55),
    gain(shape(band(noise(n), 1100, 0.7), whoosh_env), 0.8)))

n = ms(220)
write("C_steel_hit", mix(
    gain(shape(noise(n), decay(n, 6)), 0.5),
    gain(metallic(n, 620, 90, ratios=(1.0, 1.51, 2.32, 3.4)), 1.0),
    gain(shape(sine(n, 110, 70), decay(n, 40)), 0.6)))

n = ms(150)
write("C_steel_jump", mix(                       # cloth and breath, barely tonal
    gain(shape(lp(noise(n), 900), [math.sin(math.pi * i / n) for i in range(n)]), 0.9),
    gain(shape(sine(n, 240, 420), decay(n, 60)), 0.2)))

# -- D: cyber-glitch ---------------------------------------------------------

n = ms(130)
write("D_glitch_swing", gate(fm(n, 900, 2.7, 6.0, 45), 38, 0.55))

n = ms(110)
write("D_glitch_hit", mix(
    gain(crush(shape(noise(n), decay(n, 10)), hold=9, bits=3), 0.8),
    gain(fm(n, 320, 5.1, 9.0, 22), 0.9)))

n = ms(140)
write("D_glitch_jump", gate(fm(n, 300, 1.5, 3.0, 70), 52, 0.7))
