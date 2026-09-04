# Cyb3r$h1n1g4m1 — Game Design Document

**Version** 0.1 · 2026-07-28
**Engine** Godot 4.4+ · **Target** Windows desktop, single player, offline
**Genre** 2D sprite-based Metroidvania
**Logline** A death god of the machine descends the stack, reaping what is already dead.

---

## 1. Concept

You are **Cyb3r$h1n1g4m1** (`hv 0x0029`) — not an intruder, a reaper. You do not
break into the machine; you were always inside it, and you harvest processes that
have already been corrupted. The host is compromised. Something in Ring 0 is
spawning the rot. You descend from the perimeter to the kernel to cut it out.

### Design pillars

1. **The lore is real.** Every enemy, ability, and boss is a real security concept
   whose *mechanic matches its actual behavior*. A worm splits when you're slow. A
   rootkit is invisible until you scan. This is the thing that makes this game not
   a reskin — it's built on domain knowledge you already have and most devs don't.
2. **Movement first.** A Metroidvania lives or dies on the first ten seconds of
   holding right and jumping. Every ability must be fun to use before it is a key
   that opens a door.
3. **Neon on void.** The logo palette is the whole game: black background, acid
   green, electric red, cyan-blue. No mud, no browns, no gradients. Contrast is
   the art direction.
4. **One region finished beats five started.** See §12.

---

## 2. The character

### 2.1 Translating the logo to a sprite

The source logo is a front-facing hannya mask with engraving-level linework. A
side-view 48px sprite can carry roughly six shapes. These are the six:

| Logo element | Sprite translation | Why it survives |
|---|---|---|
| Red horns | Two red horns, swept back | Reads at any size, defines silhouette |
| Blue→cyan flowing hair | Long cyan ponytail, trails behind, animates | Sells motion; the single best readability asset |
| Red hannya face | Red mask covering upper face, white eye-slits | Face detail is impossible at 48px — a mask *is* the face |
| Cyan third eye | Single cyan dot on forehead; **glows when a soul is nearby** | Free mechanic hook from a free art detail |
| Acid-green smoke ribbons | Green trail VFX on dash and attack arcs | Motion, not sprite — costs zero animation frames |
| 死神 characters | UI, title screen, boss-intro cards | Belongs in typography, not on the body |

**Body:** the character is Shaun's digital self — a Black man with deep brown
skin (ramp: `#4A2A1A` / `#855434` / `#B07A4A`, cyan rim light to tie into the
palette). Outfit is streetwear-samurai fusion: black tracksuit with stand-up zip
collar and twin acid-green/cyan racing stripes, sleeves pushed to the elbow so
bare forearms and hands show in every frame; hakama-cut trousers gathered into
tracksuit ankle cuffs; tabi boots; deep-blue obi; and over it all a **white
sleeveless captain's haori** (Bleach-captain style) with a torn ragged hem — the
white panel is the readability anchor against the black world, and its back
carries `0x0029` over 死神 like a division mark.

**Two forms.** The full-face hannya mask (spirit light behind the eye slits and
grin — no face under it, only light... until it comes off) is worn in all
gameplay. **Unmasked** — short natural hair, glasses, goatee, ear stud — appears
at Snapshot shrines, in the pause portrait, on the title screen with mask in
hand, and when the final boss wears his face in phase 3. The reaper is a person;
the game should occasionally prove it.

Silhouette test: fill the sprite 100% black — horns + ponytail + ragged hem +
sheathed katana must still identify the character. If they don't, the design failed.

### 2.2 The weapon — the daishō

Not a scythe. A **daishō** (大小, "big-little") — the paired blades a samurai
actually wore. Two blades map cleanly onto the two POSIX signals:

- **Wakizashi** (short blade) → **SIGTERM**. Fast, tight cuts, 3 hits chain into
  a combo. A polite request, delivered quickly.
- **Katana "KUSANAGI"** (long blade) → **SIGKILL**. Sheathed by default; the heavy
  attack is an **iaidō draw-cut** — windup is the draw, the power is in the
  unsheathing. Long arc, breaks guard, cannot be refused. Costs Cycles.

Both blades are dark steel with an acid-green *hamon* (the temper line along a
real katana's edge) that glows — the folklore detail and the neon detail are the
same line on the blade. Kusanagi (草薙) is one of Japan's three Imperial Regalia
and the most famous sword name in cyberpunk; naming the katana after it puts both
halves of this game's identity in one word.

**The stance system.** The three attack heights are the three real kendo stances,
and the mechanic and the mythology are the same system:

| Input | Stance | Real kendo target | Game use |
|---|---|---|---|
| Up + attack | 上段 **jōdan** — blade above the head | *men* (head) | Anti-air; hits flyers |
| Neutral | 中段 **chūdan** — blade level, the standard guard | *dō* (torso) | Default cut |
| Down + attack | 下段 **gedan** — blade angled low | *kote* (wrists) | Down-forward cut; reaches enemies below a ledge |

Stance names appear nowhere in the UI — they're how the animations are drawn and
how we talk about them. The player just feels three cuts.

---

## 3. Systems

### 3.1 Resources

- **Integrity** (health) — 5 segments at start, max 10. Displayed as a row of
  cyan blocks that corrupt to red glitch-blocks as you take damage.
- **Cycles** (resource) — powers heavy attack, ranged attack, and Kernel Mode.
  Regenerates slowly when idle, faster when you land SIGTERM hits. *Attacking
  refills your resource* — this pushes players toward aggression instead of
  hiding, which is the correct pressure for this genre.
- **Soul Bytes** (currency) — dropped by reaped enemies. Spent on upgrades.
  Dropped on death; recoverable at the death site. Standard, proven, keeps stakes.

> `ponytail:` two resources is the ceiling. If Cycles isn't fun by M5, delete it and
> make heavy attack free with a cooldown. Do not add a third.

### 3.2 Save & travel

- **Snapshot stations** — save points. Restore Integrity, respawn enemies, set
  respawn point. Visually: a VM snapshot terminal, green scanline sweep.
- **SSH terminals** — fast travel between regions. One per region, unlocked on
  arrival. `ssh perimeter@0x0029` flavor text on the transition.
- **Map screen** — rendered as a live network topology / nmap output. Rooms are
  nodes, doors are edges, unexplored nodes show as `?` with a dotted edge.

### 3.3 Shortcuts

Locked doors are **closed ports**. Most open only from the far side — you fight
the long way around, then open a one-way route back to the Snapshot. This is the
cheapest way to make a map feel designed rather than generated.

---

## 4. Ability progression — the Metroidvania spine

Six abilities. Each is a **traversal gate first, combat tool second**. Order is the
critical path; the map is built around it.

| # | Ability | Movement | Combat use | Gate it opens |
|---|---|---|---|---|
| 1 | **Ping Sweep** | Ground dash, 60px burst, i-frames on frames 2-3 | Reveals invisible enemies for 3s | Gaps too wide to jump; rootkit rooms |
| 2 | **Privilege Escalation** | Double jump ("root jump") | Air combo extender | High ledges, vertical shafts |
| 3 | **Packet Injection** | — | Ranged projectile, costs Cycles | Remote switches behind bars |
| 4 | **Tunnel** | Phase through cyan-marked walls | Dodge through enemies | Encrypted walls (cyan hatching) |
| 5 | **Fork Bomb** | — | Drops a decoy that pulls aggro and detonates | Cracked/destructible barriers |
| 6 | **Kernel Mode** | Brief flight + invulnerability, drains Cycles fast | Massive damage window | Ring 0 hazard corridors — the endgame gate |

**Sequence-break allowance:** a skilled player can reach Region 3 with only Ping
Sweep + Privilege Escalation by chaining a dash-jump. Leave that in. Discovered
sequence breaks are the single strongest word-of-mouth feature this genre has.

### Upgrades (Soul Bytes, from vendor NPCs)

Integrity +1 · Cycles capacity +1 · SIGTERM combo 3→4 hits · dash distance +25% ·
soul magnetism (auto-collect radius) · third-eye range (secret detection).

---

## 5. Enemies

Behavior mirrors the real threat. This is the design gimmick — protect it.

| Enemy | Behavior | Teaches |
|---|---|---|
| **Worm** | If not killed within 4s, splits into two half-health copies. Splits recursively. | Urgency; prioritize targets |
| **Trojan** | Renders as a Soul Byte pickup or chest. Attacks when you touch it. | Don't trust the environment |
| **Keylogger** | Never attacks. If it sees you for 2s, it beacons and spawns 3 enemies. Fragile. | Kill order; the quiet one is the problem |
| **Rootkit** | Fully invisible. Only revealed by Ping Sweep. Deals heavy contact damage. | Use your tools, not just your reflexes |
| **DDoS Swarm** | 8-12 weak flyers, no individual threat, lethal in aggregate | Crowd control; SIGKILL's arc |
| **Ransomware** | On sight, begins encrypting platforms one by one — each becomes a hazard. Reverts on death. | Timer pressure without a visible timer |
| **Phish** | Mimics a friendly NPC. Displays a prompt. Interacting damages and teleports you. | Read before you click |
| **Botnet Node** | Respawns infinitely. Only stops when the room's hidden **C2 Node** dies. | Find the source |
| **Zero-Day** | Rare elite. Attack pattern randomized per encounter from a pool of 6. | You cannot pre-memorize everything |

---

## 6. Regions

The map descends the privilege stack. Vertical and hierarchical by nature —
free Metroidvania structure.

### R1 · The Perimeter (DMZ / firewall)
Outer edge. Red barrier walls, packet traffic in the background. Tutorial region:
teaches jump, SIGTERM, Ping Sweep. Sparse enemies. Wide, forgiving platforms.
**Boss: BRUTE.4RCE**

### R2 · The Wire (network layer)
Vertical shafts and horizontal data currents that push the player. Traversal
region — movement puzzles over combat. Introduces Privilege Escalation.
**Boss: P01S0N.DNS**

### R3 · Userland (application layer)
The city. Densest region: most enemies, all vendor NPCs, most secrets. Ornate blue
linework architecture lifted straight from the logo's frame. Introduces Packet
Injection and Tunnel.
**Boss: CRYPT0.L0CK3R**

### R4 · Cold Storage (the registry)
Dark, near-black. Light source is your own third eye and the blade's hamon. Hazard-heavy,
low enemy count, high tension. Introduces Fork Bomb.
**Boss: THE_INSIDER**

### R5 · Ring 0 (kernel space)
Requires Kernel Mode to traverse at all. Short, brutal, no Snapshot stations past
the entrance. Everything here is white-on-black — palette inverts.
**Boss: 0x0000 — THE KERNEL**

---

## 7. Bosses

Each boss's *defeat mechanic* is the real-world defense against that threat. This
is the best idea in this document.

**1. BRUTE.4RCE** — Credential-stuffing golem. Hammers the same three telegraphed
attacks, accelerating each cycle. Dodge five consecutive attacks without being hit
and it **locks itself out** (fail2ban) — collapses, exposing a long damage window.
Teaches the player that patience beats mashing. Perfect tutorial boss.

**2. P01S0N.DNS** — Multi-headed resolver. The arena mirrors and duplicates; heads
give false information — fake platforms dissolve, real ones are unlit. Only one
head is the authoritative resolver. Kill decoys and the real one respawns them.
Find and kill the authoritative head. Ping Sweep reveals which is real for 3s.

**3. CRYPT0.L0CK3R** — Progressively encrypts the arena floor tile by tile; each
encrypted tile becomes a hazard and is gone for the fight. A DPS check expressed as
level geometry instead of a UI timer. Kill it before you run out of standing room.

**4. THE_INSIDER** — Your mirror. Uses exactly the abilities you have unlocked, at
your current upgrade level. A player who over-leveled fights a harder boss. Reads
your inputs with a 4-frame delay and counters. The only boss with no external tell.

**5. 0x0000 — THE KERNEL** — Three phases. P1: conventional fight. P2: arena
becomes Kernel Mode-only, Cycles drain constantly, forced aggression. P3: it wears
your face and the 死神 characters resolve behind it. Final.

**Secret · ZERO_DAY** — Unlocks at 100% map completion. No pattern, no telegraphs,
no published fix. Optional.

---

## 8. Game feel — concrete numbers

Start with these in Godot, then tune. Written for a `CharacterBody2D` at the
internal resolution in §9.

```
Internal resolution   480 × 270   (integer-scaled ×4 to 1920×1080)
Tile size             16 × 16
Character height      ~72 px (4.5 tiles — SotN scale; jump_velocity rescaled to -330)

run_speed             130 px/s
accel_ground          1400 px/s²      # ~0.09s to top speed — responsive, not icy
accel_air              700 px/s²
friction_ground       1800 px/s²

jump_velocity         -300 px/s       # ≈ 50px apex ≈ 3 tiles
gravity_rising         900 px/s²
gravity_falling       1400 px/s²      # asymmetric arc — floaty up, snappy down
max_fall_speed         420 px/s
jump_release_cut       0.40           # velocity.y *= this on early release

coyote_time            0.10 s
jump_buffer            0.12 s
dash_speed             400 px/s
dash_duration          0.15 s         # = 60px
dash_cooldown          0.35 s
dash_iframes           frames 2-3
```

**Non-negotiables:** asymmetric gravity, coyote time, jump buffering, and variable
jump height. These four are why good platformers feel good, they are ~20 lines
total, and no amount of art compensates for their absence.

**Hit feel:** on every landed hit — 3 frames of hitstop, 2px screen shake,
white flash on the enemy sprite, green particle burst. Four cheap effects that do
more for combat than any damage-number system.

---

## 9. Art direction & sprite specification

### 9.0 Theme — neon-noir meets the death god

**One line:** *Cyberpunk 2077's Night City, haunted by Japanese folklore.* The
machine is a megacity; the reaper walking through it is something far older than
the technology it harvests.

The rule that keeps it coherent: **technology is the world, mysticism is the
power.** Everything infrastructural is chrome, neon signage, holo-ads, rain-slick
streets, cables. Everything *yours* — abilities, souls, save points, bosses'
death moments — is folklore: spirit flame, torii gates, hannya masks, calligraphy.
Where the two vocabularies touch is where the game's identity lives.

Concrete translations:

| Element | Cyberpunk layer | Mystical layer |
|---|---|---|
| Snapshot stations | VM terminal, scanline sweep | Small neon **shrine** — torii frame, holographic ema tablets, incense of green code-smoke |
| SSH fast travel | Terminal prompt flavor text | Stepping **through a torii gate** into the wire |
| Region signage | Neon kanji/katakana holo-signs, glitching | 死神 appears only for *you* — bosses, title, death screen |
| Souls | Data fragments | **Hitodama** — floating spirit flames (classic yūrei fire, recolored acid green) |
| Enemies | Corrupted processes, drones, chrome | Each wears a broken **oni mask** variant; the mask shatters on death |
| Bosses | Threat-actor glitch aesthetics | Intro card = ukiyo-e style portrait + neon kanji nameplate |
| Player death | Signal loss, CRT collapse | Sprite burns away as a hannya-mask afterimage |
| City background | CP2077 verticality: megabuilding silhouettes, holo-ads, aircar parallax | A distant **giant torii** on the skyline; cherry-blossom static drifting like snow |
| Corrupted zones | Quarantine warnings, red glitch | **Shimenawa rope** strung as the police tape |
| Vendor NPCs | Black-market stall, holo-inventory | Masked **kitsune** — fox spirits were the merchants of folklore too |

All of it renders in the locked §9.1 palette — red does double duty as oni skin
and neon warning; that overlap *is* the theme. Region flavor: R1 rooftop
perimeter under rain, R3 Userland is the full Night City street canyon (densest
neon), R4 Cold Storage drains the neon out entirely, R5 inverts to white.

**Tone (answers §15 Q1):** straight-faced mythic. Terminals use real command
flavor (`ssh`, `SIGKILL`) played completely straight — the humor is ambient,
never winking. No fourth-wall jokes.

### 9.1 Palette (locked, from the logo)

```
VOID        #000000    background, silhouette
INK         #0A0E1F    background detail
BLUE_DEEP   #1E33D9    hair shadow, haori
BLUE_MID    #2B6FE8    hair midtone
CYAN        #35C6F4    hair light, third eye, circuit trim
CYAN_PALE   #8FE8FF    highlight, rim light
RED_DARK    #8F1116    horn shadow, mask shadow
RED         #E01F26    horns, mask, enemy tells
GREEN_ACID  #C6F02A    blade hamon, UI, 死神, soul VFX
GREEN_DEEP  #6B8A0F    green shadow
WHITE       #FFFFFF    haori, eye-slits, sparks, hitflash
GREY        #4A5568    neutral architecture
SKIN_SHADOW #4A2A1A    skin ramp — shadow
SKIN_BASE   #855434    skin ramp — base
SKIN_LIGHT  #B07A4A    skin ramp — highlight
```

15 colors — 12 world + a 3-step skin ramp. The skin ramp is the only warmth in a
cold palette; that contrast is deliberate — it reads as *living* against the neon.
Do not add a 16th color without deleting one. A locked palette is the single
strongest force keeping a solo project's art coherent across months.

### 9.2 Sprite dimensions

| Asset | Canvas | Notes |
|---|---|---|
| Player | 96 × 96 | SotN parity: figure ~72px (Alucard height, 4.5 tiles); haori + ponytail are half the animated mass; canvas room for the draw-cut arc |
| Small enemy | 32 × 32 | |
| Large enemy | 48 × 48 | |
| Boss | 96-160 px | Multi-part where possible: separate head/arm sprites, animate by rotation instead of redrawing frames — saves enormous work |
| Tileset | 16 × 16 | One PNG per region |
| UI font | Pixel font, 8px | Use an existing free pixel font. Do not draw a font. |

### 9.3 Player animation set — Milestone 3 scope

| Animation | Frames | Priority |
|---|---|---|
| idle | 6 | 1 |
| run | 8 | 3 |
| jump (rise) | 2 | 1 |
| fall | 2 | 1 |
| land | 3 | 2 |
| attack_sigterm | 5 ×3 combo variants | 2 |
| attack_sigkill | 7 | 3 |
| dash | 4 | 2 |
| hurt | 2 | 1 |
| death | 8 | 3 |

**~47 frames** for a complete player character. That's the honest number. Build in
priority order — a prototype is fully playable with priority 1 and 2 only (~27
frames), and the run cycle (the hardest animation in 2D) can wait until the game
is already fun.

### 9.4 Godot export format

One horizontal strip PNG per animation, e.g. `player_run.png` at 384×48 (8 frames).
Load into `AnimatedSprite2D` → `SpriteFrames`. Strips are far easier to re-export
from an animation tool than grid atlases, and Godot handles them identically.

Import settings: **Filter = Nearest, Mipmaps off** on every sprite, or the pixel art
will blur. Set this as a project-wide import default on day one.

---

## 10. Sprite production plan

You have Clip Studio Paint and one logo. Here is the actual path.

**Step 1 — Reference sheet.** Generate a character turnaround (front / side /
three-quarter, full color, non-pixel) from the logo's motifs. Purpose is to lock
the design, not to be used in-game. This is where we decide horn angle, ponytail
length, haori shape, mask coverage.

**Step 2 — Silhouette pass.** Draw the side-view pose as a pure black 48×48
silhouette. Iterate here until it reads. Ten minutes spent here saves ten hours
later.

**Step 3 — Base idle frame.** One 48×48 pixel frame, full palette, side view. This
single frame is the style guide for everything else in the game.

**Step 4 — Animate in Clip Studio.** It has timeline animation and pixel-friendly
tooling. Check your license tier first: **CSP PRO caps animation at 24 frames; EX
is unlimited.** At 8 frames per animation PRO is fine, but confirm before
committing. If the pixel workflow fights you, Aseprite (~$20) is the genre standard
and will pay for itself in a weekend — but try what you own first.

**Step 5 — Enemies by reuse.** Most enemies are palette-swaps and part-swaps of
2-3 base skeletons (walker, flyer, turret). Do not draw nine unique characters.

> `ponytail:` I'll generate reference and placeholder art on request. AI-generated
> frames are useful for reference and grey-boxing, unreliable for frame-to-frame
> animation consistency — the final in-game sprites should be hand-finished by you.

---

## 11. Godot project structure

```
cybershinigami/
├── project.godot
├── scenes/
│   ├── player/        player.tscn, sigkill.tscn
│   ├── enemies/       worm.tscn, trojan.tscn, ...
│   ├── bosses/
│   ├── rooms/         r1_01.tscn, r1_02.tscn, ...
│   └── ui/            hud.tscn, map.tscn, pause.tscn
├── scripts/
│   ├── player.gd
│   ├── state_machine.gd
│   └── globals/       game_state.gd (autoload), save.gd (autoload)
├── art/
│   ├── player/        one strip PNG per animation
│   ├── enemies/
│   └── tilesets/
└── audio/
```

**Key engine notes:**
- `CharacterBody2D` + `move_and_slide()` for the player. Do not use RigidBody2D for
  a platformer character — you will fight the physics engine and lose.
- A simple state machine (idle/run/jump/fall/dash/attack/hurt) as a `_state` string
  and a `match` block. Skip the node-based state machine pattern until the string
  version actually hurts.
- `TileMapLayer` nodes (Godot 4.4+; the old `TileMap` node is deprecated).
- Rooms as separate scenes, loaded on transition. One scene per screen-ish region.
- Save via `ConfigFile` or JSON to `user://`. Godot's built-in, no library needed.
- Two autoloads maximum: game state and save. Resist adding a third.

---

## 12. Milestones

Each milestone is playable. Nothing is built that isn't needed by the next one.

| # | Deliverable | Success test |
|---|---|---|
| **M0** | This document | Done |
| **M1** | Grey-box movement — one room, colored rectangles, no art | Holding right and jumping is fun for 60 seconds with zero art |
| **M2** | SIGTERM + hit feel + one enemy (Worm) | Killing a worm feels good enough to do it again |
| **M3** | Player sprite swap-in, priority 1-2 animations | It looks like Cyb3r$h1n1g4m1 |
| **M4** | **Vertical slice:** 3 rooms, Ping Sweep gate, Snapshot station | The loop lands — blocked, find ability, return, pass |
| **M5** | Region 1 complete + BRUTE.4RCE + HUD + save/load | A stranger can play 20 minutes unassisted |
| **M6+** | One region at a time, in order R2→R5 | Each region ships complete before the next begins |

**M1-M4 is where the game is decided.** If the movement in M1 isn't fun, no amount
of map, lore, or art in M5+ will rescue it. Do not skip ahead to content.

---

## 13. Cut list

Not in v1. Not negotiable without deleting something else:

Multiplayer · dialogue trees (use one-line barks) · voice acting · procedural
generation · crafting · inventory management · skill trees (flat upgrades only) ·
achievements · controller remapping UI (ship a sane default) · difficulty modes ·
localization · anything with the word "system" that isn't in §3 · shaders beyond
one CRT/glitch post-process · a custom level editor (Godot's TileMap editor is the
level editor).

---

## 14. Risks

**Scope.** Metroidvania is the most scope-hungry genre a solo dev can pick — a big
interconnected map is the entire point of the genre and also the thing that kills
projects. Mitigation: §12's rule. One region complete beats five at 60%.

**Art volume.** ~47 frames for the player, plus nine enemies, five bosses, five
tilesets. This is the real cost. Mitigations: shared enemy skeletons, multi-part
boss sprites animated by transform, and the priority ordering in §9.3.

**The run cycle.** It is the hardest animation in 2D and it is also the one you
stare at most. Do it last, after the game is proven fun, when you have the most
practice.

**Motivation.** M1-M4 are the fun part. M6+ is content grinding. Get to a state
where the game is *demoably fun* (M4) before the grind starts — a thing people can
play and react to is what carries a solo project through the middle.

---

## 14b. Audio — music & SFX spec

**Principle:** the world is machinery, the player is folklore. Music is synthetic;
the player's own sounds carry acoustic, physical elements — a real blade, a real
bell, a wooden clack. That split is the §9.0 theme rule expressed in sound.

**Route:** procedural synthesis in Python (stdlib `wave` + `math`, no deps), writing
16-bit mono WAV at 44.1kHz into `game/audio/`. Chosen over generative AI because it
is free, instant, deterministic, revisable one parameter at a time, and suits a
chiptune-adjacent game. If a Suno/Udio key appears later, the music tracks can be
replaced without touching a line of game code — the bus layout below is the contract.

### 14b.1 Buses

| Bus | Contents | Notes |
|---|---|---|
| Master | — | single volume setting |
| Music | region loops, boss, title | ducks −6dB while a toast is on screen |
| SFX | everything the world does | |
| Player | the reaper's own actions | its own bus so the blade never gets buried |
| UI | menu, pause, toasts | unaffected by in-world ducking |

### 14b.2 Music — 5 tracks

**Direction (user-chosen 2026-07-30): lofi hip hop × traditional Japanese** —
swung boom-bap drums, vinyl crackle, Karplus-Strong koto/shamisen plucks, the
hirajoshi scale. Combat and boss carry **Creepy Nuts energy**: harder, faster,
rap-adjacent swagger. (Supersedes the original synthwave direction.)

**Since 2026-07-30 the in-game soundtrack is "Kitsune Circuit"** — Shaun's own
Suno track (lo-fi hip hop × traditional Japanese), stem-split and remixed per
slot by `art/audio/mix_stems.py`: region = the song without its drum kit,
combat = the Drums stem itself (same cut, so the phase-locked layer
reconstructs the full mix mid-fight), shrine = keys/texture stems only, boss =
full instrumental finale. `title` stays procedural (approved). The procedural
tracks below remain as the fallback spec and regenerate via `make_music.py`.

All loop seamlessly (sample-exact loop points, not crossfades — notes render
into a ring buffer so tails wrap across the loop point).

| Track | Where | Character | BPM |
|---|---|---|---|
| `title` | title screen | Sparse swung lofi: crackle, warm plucked bass, the motif stated once on koto, once echoed an octave up. | 72 |
| `region1_perimeter` | Region 1 | Head-nod boom-bap; koto phrases with long rests — space is what survives an hour. | 88 |
| `combat` | arena engagement | **Layered over** the region track, not replacing it: taiko, denser kit, shamisen stabs; drops out 4s after the last enemy. | 88 |
| `shrine` | near a Snapshot station | Calm but whole: a barely-there lofi heartbeat, warm bass roots, two koto phrases, one bell. The relief moment — near-silence alone couldn't stand. | 60 |
| `boss_bruteforce` | BRUTE.4RCE | The Creepy Nuts track: hard swung beat, distorted plucked bass, the motif inverted on bright shamisen. | 96 |

**The motif:** one 5-note hirajoshi phrase (A4 C5 B4 F4 E4, falling home),
stated in `title`, fragmented in `region1`, inverted in `boss`. Recognisable in
all three. This is what makes a soundtrack feel composed rather than assembled.

**SFX lanes (user-picked from the audible sampler 2026-07-30):** blade = STEEL —
real metallic shing over a breathy whoosh, three pitches by stance; impacts are
struck steel with low body. Player movement stays physical foley; UI stays pure
and synthetic.

### 14b.3 SFX — ~30 sounds

Marked **[slice]** = the first-pass batch, the sounds that fire constantly and so
matter most.

**Player** — `step_a`/`step_b` **[slice]** (alternating, on run frames 1 and 5),
`jump` **[slice]**, `double_jump` (rising cyan chime — an ability should *sound*
unlocked), `land` **[slice]**, `dash` **[slice]** (air-displacement whoosh),
`turn` (cloth rustle).

**Combat** — `swing_chudan` / `swing_jodan` / `swing_gedan` **[slice]** (three
pitches so mashing does not machine-gun one sample), `hit` **[slice]** (a wet
metallic crunch), `kill` **[slice]**, `whiff`, `parry` (a bright bell — the best
sound in any game with a parry), `heavy_draw` (iaido: the scrape of the saya).

**Damage** — `hurt` **[slice]**, `death`, `respawn` (a modem handshake, resolving).

**Pickups** — `soul_collect` **[slice]** (short, pitched up slightly per soul in a
chain so collecting many feels like an arpeggio), `module_install` (three-part
fanfare over ~1.2s, matching the pedestal's rise-and-dissolve), `integrity_up`.

**World** — `shrine_hum` (looping, positional), `snapshot_save`, `torii_pass`,
`lantern_flicker`.

**Enemies** — `worm_slither`, `worm_split`, `worm_die`; `drone_hum` (looping),
`drone_alert` (the keylogger's capture — must read as *bad news*); `husk_shuffle`,
`husk_shriek`; `guardian_telegraph` (the 0.6s windup needs an audio tell as much as
a visual one), `guardian_slam`, `guardian_stagger`.

**UI** — `menu_move` **[slice]**, `menu_confirm` **[slice]**, `menu_back`,
`pause_open`, `pause_close`, `toast_blip`.

### 14b.4 Hooks already in place

- `title.gd` `_play_ui_sound(id)` — called with `"move"` and `"confirm"`, currently
  a deliberate no-op. This is the one place the title makes noise.
- `Fx` autoload — the natural home for one-shot positional SFX, alongside `burst`,
  `shake` and `hitstop`, which already fire at every impact moment.
- `Game.toast` — a signal at every announcement, so `toast_blip` and music ducking
  need no new plumbing.

### 14b.5 Order of work

1. **Bus layout + an `Audio` autoload** with `play(id)` / `play_at(id, pos)` /
   `music(track)`. Silent but wired, so hooks can land before any sound exists.
2. **The [slice]** — ~12 SFX. Play it. A bad sound is worse than silence, and
   twelve sounds in context teaches more than thirty in a folder.
3. `title` and `region1_perimeter`.
4. The remaining SFX, by system.
5. `combat` layering, `shrine`, `boss`.

## 15. Open questions

1. ~~**Tone**~~ — **Answered in §9.0:** straight-faced mythic, Cyberpunk 2077
   neon-noir world with Oni/Hannya mysticism as the player's vocabulary.
2. **Combat depth** — is there a parry? A parry is the highest-value combat verb in
   the genre and costs ~15 lines plus 3 frames. Recommend yes, at M2.
3. **Difficulty** — Hollow Knight (punishing, no options) or forgiving? Affects
   Integrity count and enemy damage across the whole game.
4. **Ending** — do you cut out the corruption, or become it? Region 5's palette
   inversion sets up the second.

## 16. M4 plan — Region 1 rooms, combat verbs, BRUTE.4RCE, the economy
*(planned 2026-07-31 with Shaun; supersedes conflicting details above. Plan
first, build after sign-off — nothing in this section exists in code yet.)*

### 16.1 Room chain — five rooms, each enemy owns one

The region is an infiltration: perimeter to core, five rooms. Every room is an
EXPLORATION SPACE, not a corridor — the exit must be found, not walked to.

| # | Room | Enemy | Shape and lesson |
|---|---|---|---|
| R1 | THE PERIMETER | Forkworms | Reworked current greybox. Tight shafts and low ceilings where splitting worms box you in. Teaches: gedan cuts, drop-throughs. |
| R2 | TELEMETRY | Keyloggers | Tall open vertical climb. Drones patrol sight-lines; 3s of being seen = captured (alarm + husk reinforcements drip in). Climb broken by cover. Exit at the TOP, found by reading the drones' patrol gaps. |
| R3 | BOTNET FARM | Husks | Wide horde floor with balconies. Rage-link makes every fight a decision: pick one husk off quietly or wake the floor. Exit behind a breakable wall the horde guards. |
| R4 | THE VAULT | none (safe) | Vendor + shrine + the region map terminal. The breath before the boss. Locked cache doors here open with keys bought below. |
| R5 | AUTH BASTION | BRUTE.4RCE | The boss room. One arena, no exit until the ban lands. |

Exploration rules for every combat room (R1–R3):
- **Two routes to the exit** — one direct and dangerous, one indirect that needs
  a traversal verb (double jump, dash gap, drop-through).
- **One secret** — a soul cache or a module behind optional platforming.
- **One locked cache** ("ENCRYPTED") — opens with a vendor key, restocks the
  backtrack loop.
- The exit is a DOOR (terminal gate), not a screen edge — found, then opened.

### 16.2 New combat verbs (art already assembled)

| Verb | Name | Input | Rules |
|---|---|---|---|
| Heavy slash | **SIGKILL** | hold attack ≥0.35s, release (ground) | `player_heavy` iaido strip. 3 dmg, longer reach, cannot be flinched during the draw. `heavy_draw` saya-scrape SFX on the hold. |
| Charge slash | **FORCED ENTRY** | hold attack ≥0.7s, release (ground or air) | Batto-jutsu draw-dash: ~140px forward, hits EVERYTHING passed through for 3, i-frames for the whole travel, ghost trail. Air version travels flat. Cooldown ~2.5s. This is also the boss's intended dodge verb. |
| Drop slam | **CORE DUMP** | aim_down + attack while airborne AFTER the double jump | Plummets straight down cutting (attack_down art), impact shockwave ~40px (1 dmg + knockback), heavy landing. Only from Privilege Escalation — kernel access earns the crash. |

Acquisition model (Shaun's instinct, adopted): modules TEACH the verb (binary
unlock, the pedestal moment); the vendor UPGRADES it (tiers, soul bytes).
Suggested tiers — T2/T3 per verb, e.g. FORCED ENTRY T2 wider blade, T3 cooldown
resets on kill; SIGKILL T2 4 dmg, T3 breaks guard; CORE DUMP T2 bigger
shockwave, T3 souls pulled to you on impact.

### 16.3 BRUTE.4RCE — the fail2ban fight

The thesis fight: the boss is a brute-force attacker, and it dies to the
real-world defense. **Every attack of his that you dodge THROUGH (i-frames
overlapping his strike — dash or FORCED ENTRY) is a failed authentication
attempt.** Standing back doesn't count; reading the attack and passing through
it does.

- HUD: a terminal line ticks `auth failure 3/5 · src 0x0029` on each clean dodge.
- At **5/5: fail2ban fires.** He locks himself out — 6s stagger, fully
  vulnerable, damage counts double.
- Blade damage outside lockouts is capped (he regenerates above 50%): the sword
  softens him, the ban kills him. Expected: 2–3 lockout cycles.
- Escalation per cycle: cycle 1 = lunge + overhead (current moves); cycle 2
  adds DICTIONARY SWEEP (full-floor rush, must be jumped or FORCED-ENTRY'd);
  cycle 3 adds CREDENTIAL RAIN (telegraphed drop zones).
- His counter RESETS if he lands a hit on you (a successful login empties the
  fail log) — getting hit costs progress, not just integrity.
- Boss music already wired; `guardian_telegraph/slam/stagger` SFX already live.

### 16.4 Soul bytes, THE VAULT vendor, and death

Vendor: **FENCE.SYS** — a masked broker daemon behind a terminal in R4.
Catalogue (prices first-pass, tune in play):

| Ware | Cost | Notes |
|---|---|---|
| Verb tier T2 / T3 | 40 / 80 | per verb, the core sink |
| Integrity +1 | 30, then 45, 60… | repeatable, scaling |
| Soul magnet | 15 | wider pickup radius |
| Decryption key | 20 | opens one ENCRYPTED cache (R1–R3 backtracks) |
| Region map | 10 | reveals room layouts + secret pings on the pause map |

Income: worm 1, drone 2, husk 2, boss 25, caches 5–15.

**DECIDED (2026-07-31, Shaun):** boss = HYBRID (regen above 50%, lockouts are
6s double-damage windows, 2–3 cycles); heavies = HOLD + COOLDOWN (no Cycles —
the §3.1 meter is deferred per its own ponytail note); death = DROP + RECOVER
(bytes drop at the death site as a "core dump", lost if you die again first).

### 16.5 Build order (after sign-off)

1. Verbs first (heavy → charge → slam) — testable in the current room.
2. Room framework: door/exit object + Transition wiring + per-room maps.
3. R1 rework, R2, R3 (one at a time, playable each step).
4. R4 vendor + shrine + map terminal.
5. R5 BRUTE.4RCE.
6. Economy pass: prices, drops, death rule, caches.
