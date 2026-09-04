"""Mix Kitsune Circuit stems into the game's music slots.

The stem split IS the layer system: exploration gets the song without its drum
kit, and the combat layer is the Drums stem itself — same song, same cut, so
the phase-locked layering in audio.gd reconstructs the original mix mid-fight.

  region1_perimeter = Bass+Keyboard+Percussion+Synth+Other  cut 8s-136s
  combat            = Drums                                  cut 8s-136s (same)
  shrine            = Keyboard+Other+0.5*Synth               full length, quiet
  boss_bruteforce   = full instrumental                      finale 172s-206s
  title             = untouched (procedural version approved)

One GLOBAL gain (from the full instrumental's peak) scales every mix, so
region+combat sums back to the true balance and shrine stays naturally quiet.

Run: python mix_stems.py
"""
import pathlib
import struct
import wave

import numpy as np

HERE = pathlib.Path(__file__).parent
STEMS = HERE / "stems"
OUT = HERE.parents[1] / "game" / "audio" / "music"


def read_mono(name):
    with wave.open(str(STEMS / name), "rb") as w:
        ch, sw, sr, n = (w.getnchannels(), w.getsampwidth(),
                         w.getframerate(), w.getnframes())
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sw == 3:                                   # 24-bit: unpack by bytes
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = ((b[:, 0].astype(np.int32)) | (b[:, 1].astype(np.int32) << 8)
             | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64) / float(1 << 23)
    else:
        raise SystemExit(f"{name}: unhandled sample width {sw}")
    if ch == 2:
        x = (x[0::2] + x[1::2]) * 0.5
    return x, sr


def write_wav(name, x, sr):
    data = np.clip(x, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"ok: {name}.wav  {len(x) / sr:.1f}s")


def loop_cut(x, sr, t0, t1, fade_s=0.15):
    seg = x[int(t0 * sr):int(t1 * sr)].copy()
    f = int(sr * fade_s)
    ramp = np.linspace(0.0, 1.0, f)
    seg[:f] = seg[:f] * ramp + seg[-f:] * (1.0 - ramp)
    return seg[:-f]


stems = {}
sr = 44100
for f in sorted(STEMS.glob("*.wav")):
    x, sr = read_mono(f.name)
    stems[f.name.split(" ", 1)[1].removesuffix(".wav")] = x
    print(f"read {f.name}  {len(x) / sr:.1f}s")

length = min(len(v) for v in stems.values())
for k in stems:
    stems[k] = stems[k][:length]

inst = sum(stems[k] for k in ("Drums", "Bass", "Keyboard", "Percussion",
                              "Synth", "Other"))
K = 0.85 / np.max(np.abs(inst))          # ONE gain for every mix
print(f"global gain {K:.3f}")

bed = sum(stems[k] for k in ("Bass", "Keyboard", "Percussion", "Synth", "Other"))
write_wav("region1_perimeter", loop_cut(bed * K, sr, 8, 136), sr)
write_wav("combat", loop_cut(stems["Drums"] * K, sr, 8, 136), sr)

quiet = (stems["Keyboard"] + stems["Other"] + 0.5 * stems["Synth"]) * K
write_wav("shrine", loop_cut(quiet, sr, 0, length / sr - 0.01), sr)

write_wav("boss_bruteforce", loop_cut(inst * K, sr, 172, 206), sr)
