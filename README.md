<p align="center"><img src="art/behind-the-scenes/banner.png" alt="Cybershinigami: the reaper under the torii, in ASCII" width="100%"></p>

# Cybershinigami

A sprite-based Metroidvania in Godot 4.5 where the enemies and bosses mirror real
security threats and die to their real-world defences. Private repo.

- `DESIGN.md` is the design doc (palette, rooms, verbs, audio, the M4 plan in §16)
- `game/` is the Godot project (open `project.godot` in Godot 4.5)
- `art/` holds the pipelines that produce those assets: sprite slicing, effects,
  procedural SFX, the Kitsune Circuit stem mixes. Only pipeline inputs are
  committed; rejected generations are gone and regenerated outputs are ignored.
- `art/behind-the-scenes/` is the story: the banner, the canon sheets, and what
  the model drift cost
- `badge/` is the GitHub Universe 2025 badge port (Pimoroni Tufty 2350, MicroPython);
  see `badge/README.md` for the deploy workflow and hardware gotchas

Rights notes: the logo art derives from the Cyb3r$h1n1g4m1 persona (KIKRR /
HACKERverse marks), the Bahnschrift face needs licensing before any release, and
Suno commercial rights depend on the plan tier.
