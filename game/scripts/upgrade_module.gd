extends Area2D
## Character upgrade module (DESIGN.md §4). A pedestal with an artifact floating
## above it; walking in triggers an acquisition sequence, then it stays spent.
##
## Set `id` before adding to the tree. Everything else is looked up from CATALOG,
## so a room only needs the id.

const SHEET := "res://art/objects/upgrade_modules.png"
const PEDESTAL := "res://art/objects/upgrade_pedestal.png"
const CELL := 96          # both sheets are sliced into square cells

# id -> [module cell, display name, terminal blurb, accent colour]
const CATALOG := {
	"dash": [0, "PING SWEEP", "probe the gap — cross it before it answers", "35c6f4"],
	"double_jump": [1, "PRIVILEGE ESCALATION", "escalate: reach what root can reach", "c6f02a"],
	"ranged": [2, "PACKET INJECTION", "send a payload it cannot refuse", "ff2d95"],
	"tunnel": [3, "TUNNEL", "there was never a wall, only a route", "b026ff"],
	"integrity": [4, "INTEGRITY MODULE", "+1 integrity — harder to terminate", "ffd400"],
	"souls": [5, "SOUL CAPACITY", "hold more of what you reap", "c6f02a"],
	# §16.2 verbs. Cells reuse existing artifact art until the sheet grows.
	"heavy": [3, "SIGKILL", "hold the cut — the drawn blade cannot be refused", "e01f26"],
	"charge": [0, "FORCED ENTRY", "hold longer — pass through everything, cutting", "35c6f4"],
	"slam": [2, "CORE DUMP", "from the root jump, bring the kernel down", "c6f02a"],
}

@export var id := "double_jump"

var _t := 0.0
var _taken := false
var _artifact: Node2D
var _plinth: Sprite2D
var _accent := Color("35c6f4")
var _glow: Array[Node] = []    # active-state dressing, freed when taken


func _ready() -> void:
	var entry: Array = CATALOG.get(id, CATALOG["double_jump"])
	_accent = Color(entry[3])

	# already owned from a previous visit — show it spent, do not offer it again
	if Game.has(id):
		_taken = true

	var shape := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 20.0
	shape.shape = c
	add_child(shape)
	collision_layer = 0
	collision_mask = 2  # player only
	body_entered.connect(_on_touch)

	# Geometry: the module origin sits 28px above the greybox floor, and the
	# pedestal art fills ~87px of its 96px cell. Drawn full-size and centred at
	# +16 it sank 31px below the floor line. Scaled to 0.45 (same as the
	# artifact) its base lands exactly on the floor and its top sits just under
	# the hovering artifact — a waist-height plinth, fully above ground.
	_plinth = Sprite2D.new()
	_plinth.position = Vector2(0, 8)
	_plinth.scale = Vector2(0.45, 0.45)
	add_child(_plinth)
	_build_plinth()

	_artifact = _build_artifact(entry[0])
	_artifact.position = Vector2(0, -18)
	add_child(_artifact)

	# The "active" glow, drawn rather than baked: a lit bar on the plinth top, a
	# narrow shaft fading upward, and a pool on the ground. Three thin rects read
	# as light; one big filled rect reads as a bug.
	if not _taken:
		var bar := ColorRect.new()
		bar.size = Vector2(26, 2)
		bar.position = Vector2(-13, -13)   # the plinth's lit top edge
		bar.color = _accent
		add_child(bar)
		_glow.append(bar)

		for i in 5:                       # stacked slices, each fainter than the last
			var seg := ColorRect.new()
			seg.size = Vector2(10.0 - i * 1.2, 5)
			seg.position = Vector2(-seg.size.x * 0.5, -17.0 - i * 5.0)
			seg.color = _accent
			seg.modulate.a = 0.16 - i * 0.028
			add_child(seg)
			_glow.append(seg)

		var pool := ColorRect.new()
		pool.size = Vector2(40, 6)
		pool.position = Vector2(-20, 24)   # hugging the floor line at +28
		pool.color = _accent
		pool.modulate.a = 0.12
		add_child(pool)
		_glow.append(pool)

		# reuse the shrine's prompt so every interactable reads the same
		var prompt := InteractPrompt.new("TAKE", 40.0)
		prompt.position = Vector2(0, -46)
		add_child(prompt)
		_glow.append(prompt)


func _build_plinth() -> void:
	# cell 0 idle, 1 active, 2 spent — fall back to a drawn plinth without art
	if ResourceLoader.exists(PEDESTAL):
		var tex: Texture2D = load(PEDESTAL)
		var at := AtlasTexture.new()
		at.atlas = tex
		# Cells: 0 idle, 1 "active", 2 spent, 3 tall variant. Cell 1 is DELIBERATELY
		# unused — the generator drew its light shaft as a filled teal rectangle,
		# which rendered in game as a translucent box hanging over the plinth. The
		# idle cell is clean, and the glow below is drawn in code instead.
		var cell := 2 if _taken else 0
		at.region = Rect2(cell * CELL, 0, CELL, tex.get_height())
		_plinth.texture = at
		return
	# ponytail: drawn plinth until upgrade_pedestal.png lands
	var body := ColorRect.new()
	body.size = Vector2(30, 16)
	body.position = Vector2(-15, 4)
	body.color = Color("4a5568")
	_plinth.add_child(body)
	var ring := ColorRect.new()
	ring.size = Vector2(24, 3)
	ring.position = Vector2(-12, 2)
	ring.color = Color("0a0e1f") if _taken else _accent
	_plinth.add_child(ring)


func _build_artifact(cell: int) -> Node2D:
	var n := Node2D.new()
	if ResourceLoader.exists(SHEET):
		var tex: Texture2D = load(SHEET)
		var s := Sprite2D.new()
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(cell * CELL, 0, CELL, tex.get_height())
		s.texture = at
		s.scale = Vector2(0.45, 0.45)   # sheet cells are hero-sized; this is a pickup
		n.add_child(s)
	else:
		# ponytail: angular gem stands in until upgrade_modules.png lands
		var halo := ColorRect.new()
		halo.size = Vector2(20, 20)
		halo.position = Vector2(-10, -10)
		halo.rotation = PI / 4.0
		halo.color = _accent
		halo.modulate.a = 0.35
		n.add_child(halo)
		var core := ColorRect.new()
		core.size = Vector2(11, 11)
		core.position = Vector2(-5.5, -5.5)
		core.rotation = PI / 4.0
		core.color = Color.WHITE
		n.add_child(core)
	if _taken:
		n.modulate = Color(0.25, 0.25, 0.3, 0.45)   # dead husk left behind
	return n


func _process(delta: float) -> void:
	if _taken:
		return
	_t += delta
	_artifact.position.y = -18.0 + sin(_t * 2.2) * 2.5      # slow hover
	_artifact.rotation = sin(_t * 0.9) * 0.12               # gentle tilt
	_artifact.modulate.a = 0.82 + 0.18 * sin(_t * 4.0)      # pulse


func _on_touch(body: Node) -> void:
	if _taken or not body.is_in_group("player"):
		return
	_taken = true
	var entry: Array = CATALOG.get(id, CATALOG["double_jump"])
	Game.grant(id)
	_apply(body)

	# acquisition beat: freeze, flash, rise, announce
	Fx.hitstop(8)
	Fx.shake(4.0)
	Fx.burst(global_position, _accent)
	Game.toast.emit("MODULE INSTALLED · %s" % entry[1])
	# the blurb lands a beat later so it reads as a second terminal line
	var blurb: String = entry[2]
	get_tree().create_timer(1.5).timeout.connect(
		func(): Game.toast.emit("> %s" % blurb))

	_build_plinth()                                          # swap to spent
	# the active-state dressing goes with the artifact — leaving it made the
	# spent pedestal keep its glow bar, light shaft, ground pool and TAKE prompt
	for g in _glow:
		g.queue_free()
	_glow.clear()
	var t := create_tween()
	t.set_parallel(true)
	t.tween_property(_artifact, "position:y", -46.0, 0.55)
	t.tween_property(_artifact, "scale", Vector2(1.6, 1.6), 0.55)
	t.tween_property(_artifact, "modulate:a", 0.0, 0.55)
	t.chain().tween_callback(_artifact.queue_free)
	set_process(false)


func _apply(player: Node) -> void:
	# stat modules take effect immediately; movement abilities are gated in player.gd
	match id:
		"integrity":
			if "max_integrity" in player:
				player.max_integrity += 1
				player.integrity = player.max_integrity
		"souls":
			pass  # ponytail: no soul cap exists yet — the module reserves the slot
		_:
			pass
