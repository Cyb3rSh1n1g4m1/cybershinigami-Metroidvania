"""Procedural [slice] SFX — the ~13 constantly-firing sounds (DESIGN.md §14b.3).

stdlib only (wave + math + random), 16-bit mono 44.1kHz WAV into game/audio/sfx/.
Deterministic: same script, same bytes. Tune one parameter, re-run, hear it.

Design rule (§14b): the world is machinery, the player is folklore — player
sounds get a physical, thumpy base; UI and world sounds stay pure and synthetic.

Run: python make_sfx.py
"""
import math
import pathlib
import random
import struct
import wave

SR = 44100
OUT = pathlib.Path(__file__).resolve().parents[2] / "game" / "audio" / "sfx"
rng = random.Random(0x0029)


def write(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    k = 0.89 / peak                       # normalize with headroom
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * k)) * 32767))
                    for s in samples)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    print(f"ok: {name}.wav  {len(samples) * 1000 // SR}ms")


def n_samples(ms):
    return int(SR * ms / 1000)


def decay(n, half_ms):
    """Exponential decay envelope; half_ms = time to fall to 50%."""
    k = math.log(2) / (SR * half_ms / 1000)
    return [math.exp(-k * i) for i in range(n)]


def sine(n, f0, f1=None):
    """Sine with optional exponential frequency sweep f0 -> f1."""
    f1 = f1 if f1 is not None else f0
    out, phase = [], 0.0
    for i in range(n):
        f = f0 * (f1 / f0) ** (i / max(1, n - 1))
        phase += 2 * math.pi * f / SR
        out.append(math.sin(phase))
    return out


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def lp(xs, cutoff):
    """One-pole low-pass."""
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


def metallic(n, f0, half_ms, ratios=(1.0, 2.76, 5.40, 8.93)):
    """Inharmonic partials — reads as struck metal, not a tone. The default
    ratios are bell-like; tighter ratios (1.34, 2.1...) read as blade steel."""
    parts = [gain(sine(n, f0 * r), 1.0 / (i + 1)) for i, r in enumerate(ratios)]
    return shape(mix(*parts), decay(n, half_ms))


def adsr(n, att_ms, half_ms):
    att = max(1, n_samples(att_ms))
    return [min(1.0, i / att) * e for i, e in enumerate(decay(n, half_ms))]


def thump(n, f0, f1, half_ms, drive=3.0):
    """A weighted low punch: falling pitch, saturated for harmonics — the
    'weight' every impact needs under it."""
    return clip(shape(sine(n, f0, f1), decay(n, half_ms)), drive)


def resonant_sweep(xs, f0, f1, q, curve=1.0):
    """Noise through a GLIDING high-Q bandpass (RBJ biquad). Noise-excited
    resonance is what metal friction actually is — breathy and bright with no
    pure tone anywhere. Sine partials in the same role read as whistling."""
    out = []
    x1 = x2 = y1 = y2 = 0.0
    n = len(xs)
    for i, x in enumerate(xs):
        f = f0 * (f1 / f0) ** ((i / max(1, n - 1)) ** curve)
        w = 2 * math.pi * f / SR
        alpha = math.sin(w) / (2 * q)
        y = (alpha * (x - x2) + 2 * math.cos(w) * y1 - (1 - alpha) * y2) / (1 + alpha)
        x2, x1 = x1, x
        y2, y1 = y1, y
        out.append(y)
    return out


def whoosh_sweep(n, c0, c1, curve=1.0):
    """Air displacement: noise through a MOVING one-pole — the filter motion is
    what reads as something travelling."""
    out, y = [], 0.0
    for i, x in enumerate(noise(n)):
        c = c0 + (c1 - c0) * (i / n) ** curve
        a = 1.0 - math.exp(-2 * math.pi * c / SR)
        y += a * (x - y)
        out.append(y)
    return out


# -- player: physical, thumpy ------------------------------------------------

def step(name, thump_hz, cutoff):
    n = n_samples(60)
    scuff = shape(lp(noise(n), cutoff), decay(n, 14))
    thump = shape(sine(n, thump_hz, thump_hz * 0.7), decay(n, 22))
    write(name, mix(gain(scuff, 0.5), gain(thump, 0.9)))


step("step_a", 66, 1000)
step("step_b", 58, 800)

# jump = the dash's air language, rising and SHORT — at 150ms it read as a
# second dash; 95ms keeps it a hop, clearly distinct.
n = n_samples(95)
henv = [math.sin(math.pi * (i / n) ** 0.8) for i in range(n)]   # early swell
sn = n_samples(10)
write("jump", mix(
    shape(hp(whoosh_sweep(n, 500, 2600, 1.4), 300), henv),
    gain(shape(hp(noise(sn), 2500), decay(sn, 3)), 0.5)))       # cloth snap

n = n_samples(110)
write("land", mix(
    gain(shape(sine(n, 62, 40), decay(n, 30)), 1.0),
    gain(shape(lp(noise(n), 500), decay(n, 18)), 0.5)))

n = n_samples(220)
hump = [math.sin(math.pi * i / n) ** 2 for i in range(n)]      # swell-and-fade
write("dash", shape(hp(whoosh_sweep(n, 2400, 400), 250), hump))


# -- blade: the anime katana cut. NO sine partials anywhere — glided sines are
# whistles. The sound is AIR leading (two sharp offset swish layers) with a
# metallic SCRAPE riding it: noise through gliding high-Q resonances.

def swing(name, s0, s1, w0, w1c):
    m = n_samples(230)
    src = noise(m)
    # decay 40ms, not 110: a longer tail left the resonance ringing alone at its
    # top frequency after the air died — a squeak. The scrape must end INSIDE
    # the swish.
    scrape = shape(mix(
        gain(resonant_sweep(src, s0, s1, 30), 1.0),
        gain(resonant_sweep(src, s0 * 1.5, s1 * 1.5, 22), 0.3)), adsr(m, 10, 40))
    sw_n = n_samples(130)
    h = [math.sin(math.pi * i / sw_n) ** 3 for i in range(sw_n)]  # sharp air cut
    swish = shape(hp(whoosh_sweep(sw_n, w0, w1c, 0.7), 350), h)
    sw2_n = n_samples(150)
    h2 = [math.sin(math.pi * i / sw2_n) ** 3 for i in range(sw2_n)]
    swish2 = shape(hp(whoosh_sweep(sw2_n, w0 * 0.7, w1c * 0.8), 300), h2)
    off = n_samples(15)
    swish2 = [0.0] * off + swish2                # trailing second layer: doppler
    write(name, mix(gain(swish, 1.0), gain(swish2, 0.6), gain(scrape, 0.55)))


swing("swing_chudan", 900, 2600, 700, 2200)
swing("swing_jodan", 1100, 3100, 800, 2600)   # overhead: fastest-reading
swing("swing_gedan", 700, 2000, 500, 1600)    # low cut: heavier air

# hurt = a THUD first: a heavy body punch is the sound of taking a hit. The
# formant "ugh" stays as a quiet layer inside it — human colour, not the lead.
n = n_samples(240)
_src = clip(sine(n, 130, 80), 6.0)
_voice = shape(mix(
    gain(band(band(_src, 550, 0.35), 550, 0.35), 1.0),
    gain(band(band(_src, 1150, 0.3), 1150, 0.3), 0.6),
    gain(band(band(_src, 2500, 0.3), 2500, 0.3), 0.3)), adsr(n, 6, 45))
write("hurt", clip(mix(
    gain(thump(n_samples(160), 120, 55, 45, drive=3.5), 1.2),   # the thud leads
    gain(_voice, 0.45),
    gain(shape(hp(noise(n), 1600), decay(n, 60)), 0.1)), 1.5))

# -- combat impact: WEIGHT FIRST. The old struck-steel partials rang like bells.
# Architecture: crack transient -> saturated low punch -> mid smack -> one SHORT
# metal snap on top (never a ring), soft-clipped together as glue.

n = n_samples(160)
_tk = n_samples(40)
write("hit", clip(mix(
    gain(shape(noise(n_samples(6)), decay(n_samples(6), 2)), 0.9),      # crack
    gain(thump(n, 150, 55, 45), 1.2),                                    # punch
    gain(shape(band(noise(n_samples(50)), 600, 0.8), decay(n_samples(50), 12)), 0.7),
    gain(shape(mix(sine(_tk, 2200), gain(sine(_tk, 3170), 0.5)), decay(_tk, 9)), 0.25)),
    1.4))

n = n_samples(420)
write("kill", clip(mix(
    gain(shape(noise(n_samples(8)), decay(n_samples(8), 2)), 0.9),
    gain(thump(n, 120, 42, 90, drive=4.0), 1.3),                         # punch
    gain(shape(sine(n, 55, 38), decay(n, 130)), 0.8),                    # sub tail
    gain(shape(band(noise(n_samples(90)), 500, 0.8), decay(n_samples(90), 18)), 0.7),
    gain(shape(hp(noise(n_samples(260)), 3000), decay(n_samples(260), 60)), 0.18)),
    1.3))

# -- pickups / UI: pure, synthetic -------------------------------------------

n = n_samples(150)
write("soul_collect", mix(
    gain(shape(sine(n, 1320), decay(n, 35)), 1.0),
    gain(shape(sine(n, 1980), decay(n, 22)), 0.35)))

n = n_samples(35)
write("menu_move", shape(sine(n, 2400), decay(n, 7)))

a = n_samples(60)
b = n_samples(80)
write("menu_confirm",
      shape(sine(a, 880), decay(a, 18)) + shape(sine(b, 1320), decay(b, 24)))

# =============================================================================
# FULL SET — everything past the [slice] (DESIGN.md 14b.5 step 4).
# Same language throughout: foley-physical for the player, weight-first
# impacts, resonant-noise metal, Japanese timbres (bell, wood, taiko, koto).
# =============================================================================


def pluck(f, dur_s, damp=0.996, tone=3000.0):
    """Karplus-Strong plucked string (same as the music engine): a noise burst
    cycling through a damped averager IS a string."""
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


def bell(n, f0, half_ms):
    """A real small bell (suzu): inharmonic partials, bright, fast attack."""
    return metallic(n, f0, half_ms, ratios=(1.0, 2.0, 2.98, 4.2, 5.43))


def clack(n, f0, half_ms=9):
    """Hyoshigi wood: a resonant knock — noise through a woody mid resonance."""
    return shape(resonant_sweep(noise(n), f0, f0 * 0.94, 9), decay(n, half_ms))


def loopify(xs, fade_ms=60):
    """Blend the tail into the head and trim it — a seamless loop."""
    f = n_samples(fade_ms)
    out = xs[:]
    for i in range(f):
        k = i / f
        out[i] = xs[i] * k + xs[len(xs) - f + i] * (1 - k)
    return out[:len(xs) - f]


def at_ms(buf, smp, ms_pos, g=1.0):
    s0 = n_samples(ms_pos)
    for j, v in enumerate(smp):
        if s0 + j < len(buf):
            buf[s0 + j] += v * g


# -- player / ability --------------------------------------------------------

# double_jump: the NORMAL JUMP sound with a bigger whoosh layered on top —
# no chimes, no bells (they read as UI). Same air language, more of it.
n = n_samples(95)
henv = [math.sin(math.pi * (i / n) ** 0.8) for i in range(n)]
sn = n_samples(10)
jump_base = mix(
    shape(hp(whoosh_sweep(n, 500, 2600, 1.4), 300), henv),
    gain(shape(hp(noise(sn), 2500), decay(sn, 3)), 0.5))
n2 = n_samples(240)
henv2 = [math.sin(math.pi * (i / n2) ** 0.7) for i in range(n2)]
big_whoosh = shape(hp(whoosh_sweep(n2, 300, 1900, 1.2), 200), henv2)
write("double_jump", mix(gain(jump_base, 1.0), gain(big_whoosh, 0.8)))

# fe_charge: the gather — a rising shimmer while energy converges (§16.2)
n = n_samples(420)
write("fe_charge", gain(shape(resonant_sweep(noise(n), 380, 1500, 18, 1.3),
                              [((i / n) ** 1.5) for i in range(n)]), 0.7))

# fe_release: the Hiten-style release — a long bright steel shing tearing
# open over a wide whoosh and a low body. The move's whole sound.
n = n_samples(520)
write("fe_release", clip(mix(
    gain(shape(resonant_sweep(noise(n), 1400, 3400, 25, 0.6), adsr(n, 6, 160)), 1.0),
    gain(shape(resonant_sweep(noise(n), 2100, 5100, 18, 0.6), adsr(n, 8, 120)), 0.45),
    gain(shape(band(noise(n), 1100, 0.7),
               [math.sin(math.pi * i / n) ** 1.5 for i in range(n)]), 0.7),
    gain(thump(n_samples(160), 95, 42, 50), 0.8)), 1.5))

# heavy_draw: the saya scrape — the katana leaving the sheath. A falling
# metallic resonance with a soft click as the guard clears.
n = n_samples(300)
hd = gain(shape(resonant_sweep(noise(n), 950, 320, 16, 0.8), adsr(n, 25, 110)), 1.0)
at_ms(hd, shape(band(noise(n_samples(30)), 1800, 0.7), decay(n_samples(30), 5)), 250, 0.5)
write("heavy_draw", hd)

# slam_impact: CORE DUMP landing — tighter and sharper than the guardian's
# slam, with a metallic ring: the blade hit the floor too.
n = n_samples(420)
write("slam_impact", clip(mix(
    gain(shape(noise(n_samples(8)), decay(n_samples(8), 2)), 1.0),
    gain(thump(n_samples(240), 100, 32, 100, drive=4.5), 1.4),
    gain(shape(sine(n, 46, 26), decay(n, 140)), 0.9),
    gain(metallic(n_samples(200), 620, 60, ratios=(1.0, 1.51, 2.32)), 0.35),
    gain(shape(lp(noise(n_samples(260)), 1000), decay(n_samples(260), 50)), 0.3)), 1.3))

# turn: a beat of cloth as the haori swings around
n = n_samples(85)
write("turn", gain(shape(lp(noise(n), 1400),
                         [math.sin(math.pi * i / n) for i in range(n)]), 0.8))

# death: the heaviest thud in the game, a sub drop, and everything washing away
n = n_samples(650)
write("death", clip(mix(
    gain(shape(noise(n_samples(8)), decay(n_samples(8), 2)), 0.8),
    gain(thump(n_samples(300), 100, 34, 110, drive=4.0), 1.3),
    gain(shape(sine(n, 48, 26), decay(n, 220)), 0.9),
    gain(shape(lp(noise(n), 900), decay(n, 260)), 0.25)), 1.3))

# respawn: a modem handshake RESOLVING — dial blips, FSK warble, hiss, then a
# clean settling tone. Band-limited like a phone line so it reads as a modem.
seg1 = mix(shape(sine(n_samples(70), 941), decay(n_samples(70), 60)),
           shape(sine(n_samples(70), 1336), decay(n_samples(70), 60)))
warb_n = n_samples(260)
warb = [math.sin(2 * math.pi * (980 if (i * 16 // SR) % 2 == 0 else 1180) * i / SR)
        for i in range(warb_n)]
hiss = gain(shape(hp(noise(n_samples(160)), 1200), decay(n_samples(160), 120)), 0.5)
settle_n = n_samples(240)
settle = shape(sine(settle_n, 700, 1050), adsr(settle_n, 40, 140))
line = seg1 + gain(warb, 0.55) + hiss + gain(settle, 0.8)
write("respawn", band(line, 1700, 0.85))

# -- pickups / world ---------------------------------------------------------

# module_install: three-part fanfare over ~1.2s matching the pedestal rise —
# koto arpeggio up the hirajoshi scale, a bell over the top, taiko to seat it
A4, C5, E5 = 440.0, 523.25, 659.26
fan = [0.0] * n_samples(1250)
for f, at in ((A4, 0), (C5, 140), (E5, 280)):
    at_ms(fan, pluck(f, 0.9, damp=0.9965, tone=2600), at, 0.8)
at_ms(fan, bell(n_samples(500), 1560, 90), 430, 0.6)
tk = mix(shape(sine(n_samples(240), 92, 48), decay(n_samples(240), 60)),
         gain(shape(lp(noise(n_samples(240)), 320), decay(n_samples(240), 18)), 0.3))
at_ms(fan, tk, 820, 0.9)
write("module_install", fan)

# snapshot_save: one suzu bell and a breath — the relief moment
n = n_samples(520)
write("snapshot_save", mix(
    gain(bell(n, 1740, 110), 0.9),
    gain(shape(lp(noise(n), 700), decay(n, 200)), 0.12)))

# shrine_hum: loopable room tone — low air and a faint bell shimmer
n = n_samples(3000)
sh = mix(
    gain(lp(noise(n), 240), 0.5),
    gain([math.sin(2 * math.pi * 110 * i / SR) * (0.6 + 0.4 * math.sin(2 * math.pi * i / n))
          for i in range(n)], 0.10))
at_ms(sh, bell(n_samples(900), 1740, 160), 1400, 0.06)
write("shrine_hum", loopify(sh))

# -- enemies -----------------------------------------------------------------

# worm_split: a wet squelch — low noise chew + a falling gulp
n = n_samples(260)
write("worm_split", clip(mix(
    gain(shape(lp(noise(n), 500), decay(n, 40)), 0.9),
    gain(shape(sine(n_samples(140), 300, 90), decay(n_samples(140), 35)), 0.7),
    gain(shape(lp(noise(n_samples(60)), 900), decay(n_samples(60), 8)), 0.6)), 2.0))

# drone_alert: BAD NEWS — two descending dark tones a minor second apart
a_n = n_samples(220)
write("drone_alert", clip(mix(
    shape(sine(a_n, 620), adsr(a_n, 8, 120)),
    gain(shape(sine(a_n, 585), adsr(a_n, 8, 150)), 0.9)), 2.2))

# drone_hum: loopable rotor — low fundamental with a 30Hz flutter
n = n_samples(1500)
write("drone_hum", loopify(mix(
    gain([math.sin(2 * math.pi * 55 * i / SR) for i in range(n)], 0.35),
    gain([math.sin(2 * math.pi * 110 * i / SR) for i in range(n)], 0.2),
    gain([x * (0.6 + 0.4 * math.sin(2 * math.pi * 30 * i / SR))
          for i, x in enumerate(lp(noise(n), 800))], 0.3))))

# husk_shriek: a resonant scream tearing upward, distorted
n = n_samples(420)
write("husk_shriek", clip(mix(
    gain(shape(resonant_sweep(noise(n), 600, 1900, 18, 0.7), adsr(n, 15, 130)), 1.2),
    gain(shape(resonant_sweep(noise(n), 900, 2600, 12), adsr(n, 25, 110)), 0.6)), 3.0))

# guardian_telegraph: 0.6s of tension — an accelerating taiko roll under a rise
tg = [0.0] * n_samples(600)
t_acc = 0.0
step_ms = 130.0
while t_acc < 520:
    hit = mix(shape(sine(n_samples(120), 88, 52), decay(n_samples(120), 30)),
              gain(shape(lp(noise(n_samples(120)), 350), decay(n_samples(120), 10)), 0.3))
    at_ms(tg, hit, int(t_acc), 0.55 + 0.45 * (t_acc / 520.0))
    step_ms *= 0.82
    t_acc += step_ms
rise_n = n_samples(600)
rise = gain(shape(resonant_sweep(noise(rise_n), 300, 1100, 14, 1.3),
                  [((i / rise_n) ** 1.6) for i in range(rise_n)]), 0.5)
write("guardian_telegraph", mix(tg, rise))

# guardian_slam: the arena-shaking one — sub boom, crack, debris
n = n_samples(520)
write("guardian_slam", clip(mix(
    gain(shape(noise(n_samples(10)), decay(n_samples(10), 3)), 1.0),
    gain(thump(n_samples(280), 95, 30, 120, drive=4.5), 1.4),
    gain(shape(sine(n, 42, 24), decay(n, 170)), 1.0),
    gain(shape(lp(noise(n_samples(320)), 1200), decay(n_samples(320), 60)), 0.35)), 1.3))

# guardian_stagger: fail2banned — a metal groan falling over, then the settle
n = n_samples(560)
gs = gain(shape(resonant_sweep(noise(n), 900, 260, 20, 0.8), adsr(n, 20, 170)), 1.0)
at_ms(gs, thump(n_samples(180), 90, 45, 60), 340, 0.8)
write("guardian_stagger", clip(gs, 2.0))

# -- UI ----------------------------------------------------------------------

n = n_samples(35)
write("menu_back", shape(sine(n, 1700), decay(n, 7)))

write("pause_open", gain(clack(n_samples(90), 1150), 0.9))
write("pause_close", gain(clack(n_samples(90), 870), 0.9))

n = n_samples(45)
write("toast_blip", mix(
    gain(shape(hp(noise(n_samples(8)), 2000), decay(n_samples(8), 2)), 0.5),
    gain(shape(sine(n, 340, 300), decay(n, 10)), 0.8)))
