"""Build soundboard.html — every game sound playable inline with its role and a
proposed direction, so the whole soundscape can be directed in one pass.
WAVs are embedded as data URIs; the file is fully self-contained.

Run: python make_soundboard.py
"""
import base64
import pathlib

HERE = pathlib.Path(__file__).parent
SFX = HERE.parents[1] / "game" / "audio" / "sfx"
MUSIC = HERE.parents[1] / "game" / "audio" / "music"

# (id, where it plays, character)
TRACKS = [
    ("title", "title screen", "72 BPM sparse swung lofi — crackle, plucked bass, the motif on koto at bar 3, octave echo at bar 7"),
    ("region1_perimeter", "Region 1", "88 BPM head-nod boom-bap; koto speaks two bars, rests two"),
    ("combat", "layered over region during engagement", "taiko + extra kicks + swung hats + shamisen war-stabs; phase-locked to region"),
    ("shrine", "inside a shrine's radius", "60 BPM near-silence: pad, the motif barely-there, one bell before the loop turns"),
    ("boss_bruteforce", "the guardian encounter", "96 BPM Creepy Nuts energy: hard swung kit, distorted plucked bass, the motif inverted on bright shamisen"),
]

# (id, when it fires, current design, proposed foley direction)
ROWS = [
    ("Blade — LOCKED (steel lane)", [
        ("swing_chudan", "neutral cut", "steel shing + breathy whoosh", "as picked — no change"),
        ("swing_jodan", "overhead cut (aim up)", "same, pitched higher", "as picked — no change"),
        ("swing_gedan", "low cut (aim down)", "same, pitched lower/heavier", "as picked — no change"),
    ]),
    ("Impacts", [
        ("hit", "a cut connects", "struck steel + noise + low body", "keep the steel, add a wetter 'chunk' body — blade meeting mass, not a bell"),
        ("kill", "the killing blow", "deeper steel, 85Hz boom, long ring", "heavier body, a hair of silence before the ring blooms"),
    ]),
    ("Movement", [
        ("step_a", "run contact frame 1", "filtered noise scuff + 66Hz thump", "soft sole on wet concrete — more scuff texture, less tone"),
        ("step_b", "run contact frame 2", "same, darker/lower", "same, slightly different so the gait breathes"),
        ("jump", "leaving the ground", "rising sine sweep + noise", "drop the sweep: cloth snap + a short breath of air"),
        ("land", "touching down", "60Hz thump + noise", "boot thud + cloth settle, two-stage"),
        ("dash", "dash", "swept-filter air whoosh", "fabric whip-crack + air displacement, less 'filter sweep'"),
    ]),
    ("Feedback", [
        ("hurt", "taking damage", "clipped falling buzz", "physical: sharp cloth/impact burst, almost a grunt — no buzz"),
        ("soul_collect", "soul pickup (chains pitch up)", "two-partial sine chime", "a small suzu shrine bell — real bell partials, keeps the chain arpeggio"),
    ]),
    ("UI", [
        ("menu_move", "menu cursor moves", "2.4kHz sine tick", "kept — approved"),
        ("menu_confirm", "menu select", "two rising sine blips", "kept — approved"),
        ("menu_back", "menu back out", "lower tick", "matches menu_move, a step down"),
        ("pause_open", "pause opens", "hyoshigi wood clack", "resonant wooden knock"),
        ("pause_close", "pause closes", "lower wood clack", "same wood, settling"),
        ("toast_blip", "every terminal toast", "keystroke tick + low thock", "quiet — it fires often"),
    ]),
    ("Ability / life cycle", [
        ("double_jump", "air jump (Privilege Escalation)", "two bright bells stepping up over rising air", "an ability should sound unlocked"),
        ("turn", "ground turn-around", "a beat of cloth", "the haori swinging round"),
        ("death", "integrity zero", "heaviest thud + sub drop + wash away", "everything dropping out"),
        ("respawn", "snapshot restore", "modem handshake: dial blips, FSK warble, hiss, settling tone", "band-limited like a phone line"),
        ("module_install", "taking an upgrade", "koto arpeggio + bell + taiko over 1.25s", "matches the pedestal rise"),
        ("snapshot_save", "saving at a shrine", "one suzu bell + a breath", "the relief moment"),
    ]),
    ("World / enemies", [
        ("shrine_hum", "near a shrine (loops)", "room tone + faint bell shimmer", "positional, quiet"),
        ("worm_split", "worm splits in two", "wet squelch + falling gulp", ""),
        ("drone_alert", "keylogger captures you", "two descending dark tones, minor second", "reads as bad news"),
        ("drone_hum", "drone rotors (loops)", "low fundamental + 30Hz flutter", "positional, quiet"),
        ("husk_shriek", "botnet rage-link fires", "resonant scream tearing upward", ""),
        ("guardian_telegraph", "0.6s windup", "accelerating taiko roll under a rising resonance", "the audio tell"),
        ("guardian_slam", "the swing commits", "sub boom + crack + debris", "arena-shaking"),
        ("guardian_stagger", "fail2ban stagger", "metal groan falling over + settle", ""),
    ]),
]

# deliberately NOT built yet
PLANNED = [
    ("whiff", "attack that hits nothing", "covered: the swing IS the whiff; impacts only play on connection"),
    ("parry / heavy_draw", "parry + iaido heavy", "wait on the mechanics shipping — sounds would be orphans"),
    ("torii_pass / lantern_flicker", "ambience one-shots", "no trigger exists in the room yet"),
]


def b64(p):
    return base64.b64encode(p.read_bytes()).decode()


parts = ["""<title>Cybershinigami — soundboard</title>
<style>
  :root { color-scheme: dark; }
  body { background:#0a0e1f; color:#c8d6e5; font:14px/1.5 'Segoe UI',sans-serif;
         max-width:860px; margin:24px auto; padding:0 16px; }
  h1 { color:#fcee0a; font-size:20px; letter-spacing:2px; }
  h2 { color:#35c6f4; font-size:15px; margin:26px 0 8px; border-bottom:1px solid #24304a;
       padding-bottom:4px; letter-spacing:1px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:7px 8px; border-bottom:1px solid #16203a; vertical-align:top; }
  td.id { color:#c6f02a; font-family:Consolas,monospace; white-space:nowrap; }
  td.play { width:200px; }
  audio { width:190px; height:28px; }
  .when { color:#7a8aa8; font-size:12px; }
  .prop { color:#e8d9a0; font-size:13px; }
  .note { color:#7a8aa8; font-size:12px; margin:6px 0 18px; }
</style>
<h1>CYBERSHINIGAMI — SOUNDBOARD</h1>
<p class=note>Use the play control to hear each current sound. The amber text is my
proposed foley direction (matching your steel pick + “less synthetic” note) — reply
per sound with keep / change / your own reference. Nothing regenerates until you say so.</p>
"""]

for section, rows in ROWS:
    parts.append(f"<h2>{section}</h2><table>")
    for sid, when, cur, prop in rows:
        p = SFX / f"{sid}.wav"
        audio = (f'<audio controls preload="auto" '
                 f'src="data:audio/wav;base64,{b64(p)}"></audio>') if p.exists() else "—"
        parts.append(
            f"<tr><td class=play>{audio}</td><td class=id>{sid}</td>"
            f"<td><div class=when>{when}</div><div>{cur}</div>"
            f"<div class=prop>&#8594; {prop}</div></td></tr>")
    parts.append("</table>")

parts.append("<h2>Music — 5 tracks (all seamless loops)</h2><table>")
for tid, where, character in TRACKS:
    # mp3 wins over wav, mirroring the game's Audio._stream_music order
    p = MUSIC / f"{tid}.mp3"
    mime = "audio/mpeg"
    if not p.exists():
        p = MUSIC / f"{tid}.wav"
        mime = "audio/wav"
    audio = (f'<audio controls preload="none" loop '
             f'src="data:{mime};base64,{b64(p)}"></audio>') if p.exists() else "—"
    parts.append(
        f"<tr><td class=play>{audio}</td><td class=id>{tid}</td>"
        f"<td><div class=when>{where}</div><div class=prop>{character}</div></td></tr>")
parts.append("</table>")

parts.append("<h2>Planned — not built yet, direction wanted</h2><table>")
for sid, when, prop in PLANNED:
    parts.append(
        f"<tr><td class=play>&#183;</td><td class=id>{sid}</td>"
        f"<td><div class=when>{when}</div><div class=prop>&#8594; {prop}</div></td></tr>")
parts.append("</table>")

out = HERE / "soundboard.html"
out.write_text("".join(parts), encoding="utf-8")
print(f"ok: {out}  ({out.stat().st_size // 1024} KB)")
