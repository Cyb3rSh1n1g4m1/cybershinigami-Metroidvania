extends Node2D
## Environment dressing. Purely decorative — no collision, no gameplay effect.
## Reads the room map to find real surfaces, then hangs set dressing off them so
## the level looks inhabited instead of like a collision diagram.

const TILE := 16
const LANTERN := "res://art/objects/lantern.png"
const TORII := "res://art/objects/torii.png"
const STATUE := "res://art/objects/statue.png"

var map: Array[String] = []
var seed_value := 1337


func _ready() -> void:
	z_index = -3  # in front of the parallax, behind the player and the terrain edge
	if map.is_empty():
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value  # fixed: the same dressed room every run

	var w: int = map[0].length()
	var floors := _surfaces()

	# hanging lanterns under overhangs, every so often along a ceiling
	for y in map.size():
		for x in w:
			if map[y][x] != "#":
				continue
			if y + 1 < map.size() and map[y + 1][x] == "." and rng.randf() < 0.045:
				_hang(Vector2(x * TILE + 8, y * TILE + TILE + 10), rng)

	# ground clutter on open floor. Sparser than before because the props are real
	# objects now, not 6px flecks — at 9% the deck looked like a junkyard.
	for s in floors:
		if rng.randf() < 0.045:
			_ground(Vector2(s.x * TILE + 8, s.y * TILE), rng)

	# no scattered torii here by design: there is exactly ONE giant torii, on the
	# far skyline. Repeating the motif at prop scale destroyed its uniqueness.


func _surfaces() -> Array[Vector2i]:
	# every solid tile with open air above it — the walkable skin of the room
	var out: Array[Vector2i] = []
	for y in map.size():
		for x in map[y].length():
			if map[y][x] == "#" and (y == 0 or map[y - 1][x] == "."):
				out.append(Vector2i(x, y))
	return out


func _hang(pos: Vector2, rng: RandomNumberGenerator) -> void:
	# cable + a glowing lantern; the glow is the point, the cable sells the hang
	var drop := rng.randf_range(6.0, 20.0)
	var cable := ColorRect.new()
	cable.size = Vector2(1, drop)
	cable.position = pos + Vector2(0, -drop)
	cable.color = Color("0a0e1f")
	add_child(cable)

	# prefer the hanging-lantern prop cell (5) — it is drawn with its own bracket
	if ResourceLoader.exists(PROPS):
		var at := AtlasTexture.new()
		at.atlas = load(PROPS)
		at.region = Rect2(5 * PROP_CELL, 0, PROP_CELL, PROP_CELL)
		var s := Sprite2D.new()
		s.texture = at
		s.scale = Vector2(0.53, 0.53)
		s.position = pos + Vector2(0, -PROP_CELL * 0.53 * 0.5)
		add_child(s)
	elif ResourceLoader.exists(LANTERN):
		var s := AnimatedSprite2D.new()
		s.sprite_frames = Fx.frames(LANTERN, 3, 4.0, true)
		s.position = pos
		s.scale = Vector2(0.5, 0.5)
		add_child(s)
		s.play("a")
	else:
		var r := ColorRect.new()
		r.size = Vector2(5, 7)
		r.position = pos - Vector2(2.5, 0)
		r.color = Color("c6f02a")
		add_child(r)

	# every lantern throws a soft pool of light so the level reads as lit
	var halo := ColorRect.new()
	halo.size = Vector2(26, 26)
	halo.position = pos - Vector2(13, 10)
	halo.color = Color("c6f02a")
	halo.modulate.a = 0.10
	add_child(halo)


# props_fg.png cells, bottom-aligned in 64px cells (art/objects/slice_props.py):
# 0 vending machine  1 crate stack  2 sign post   3 AC condenser  4 pipe cluster
# 5 hanging lantern  6 fox statue   7 holo panel  8 cable coil    9 water tank
const PROPS := "res://art/objects/props_fg.png"
const PROP_CELL := 64
# cells that read as ground clutter, with the scale each wants. The lantern (5) is
# excluded: it belongs on a cable under an overhang, not standing on the floor.
# Scales are set against the PLAYER, who stands ~76px tall — the previous values
# (0.42-0.70) made a vending machine 27-45px, so the deck read as a doll's house.
# Each number below is the prop's intended real height / 64px cell.
const GROUND_CELLS := [
	[0, 0.97],   # vending machine — chest-and-a-half, ~62px
	[1, 0.75],   # crate stack — waist high, ~48px
	[2, 1.25],   # sign post — taller than the reaper, ~80px
	[3, 0.66],   # AC condenser — knee-to-waist, ~42px
	[4, 0.90],   # pipe cluster — shoulder height, ~58px
	[6, 0.81],   # fox statue on its plinth, ~52px
	[7, 1.06],   # holo panel — head height, ~68px
	[8, 0.41],   # cable coil — ankle height, ~26px
	[9, 1.12],   # water tank on legs — overhead, ~72px
]


func _ground(pos: Vector2, rng: RandomNumberGenerator) -> void:
	if ResourceLoader.exists(PROPS):
		var pick: Array = GROUND_CELLS[rng.randi_range(0, GROUND_CELLS.size() - 1)]
		var tex: Texture2D = load(PROPS)
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(int(pick[0]) * PROP_CELL, 0, PROP_CELL, PROP_CELL)
		var s := Sprite2D.new()
		s.texture = at
		s.scale = Vector2(pick[1], pick[1])
		# cells are bottom-aligned, so the sprite's own bottom lands on the floor
		s.position = pos + Vector2(0, -PROP_CELL * pick[1] * 0.5)
		s.flip_h = rng.randf() < 0.35
		add_child(s)
		return

	# ponytail: drawn clutter until props_fg.png lands
	match rng.randi_range(0, 2):
		0:
			var b := ColorRect.new()
			b.size = Vector2(rng.randf_range(5.0, 9.0), rng.randf_range(6.0, 11.0))
			b.position = pos - Vector2(b.size.x * 0.5, b.size.y)
			b.color = Color("4a5568")
			add_child(b)
		1:
			var p := ColorRect.new()
			p.size = Vector2(3, rng.randf_range(7.0, 13.0))
			p.position = pos - Vector2(1.5, p.size.y)
			p.color = Color("4a5568")
			add_child(p)
			var cap := ColorRect.new()
			cap.size = Vector2(5, 2)
			cap.position = p.position + Vector2(-1, -2)
			cap.color = Color("35c6f4")
			add_child(cap)
		_:
			for i in rng.randi_range(2, 5):
				var d := ColorRect.new()
				d.size = Vector2(2, 1)
				d.position = pos + Vector2(rng.randf_range(-10.0, 10.0), -1)
				d.color = Color("0a0e1f")
				add_child(d)
