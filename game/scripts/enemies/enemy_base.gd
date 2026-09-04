class_name EnemyBase
extends CharacterBody2D
## Shared enemy body (DESIGN.md §5): health, hit flash + knockback, death drop,
## gravity, player lookup. Layer 4 / mask 1; a "Hurtbox" Area2D child on mask 2
## is wired to the player's hurt() automatically.

const GRAVITY := 1400.0
const MAX_FALL := 420.0

# subclasses set health in _init() so post-instantiate overrides (worm split) still win
var health := 1
var visual: CanvasItem
var base_color := Color.WHITE


func _ready() -> void:
	# husk.gd's rage-link scans group "enemies" — without this line the group
	# was empty and the whole botnet mechanic silently never fired
	add_to_group("enemies")
	var hurtbox := get_node_or_null("Hurtbox") as Area2D
	if hurtbox:
		hurtbox.body_entered.connect(_on_touch)
		# Contact damage must be level-based, not edge-based: body_entered alone
		# meant an overlap that BEGAN during i-frames (dashing into the enemy,
		# resting overlapped after knockback) never dealt damage for as long as
		# the overlap lasted. Poll the overlap; hurt() itself ignores calls while
		# i-frames run, so this deals exactly one hit the moment they expire.
		var poll := Timer.new()
		poll.wait_time = 0.1
		poll.autostart = true
		poll.timeout.connect(func() -> void:
			for b in hurtbox.get_overlapping_bodies():
				_on_touch(b))
		add_child(poll)


func _on_touch(body: Node) -> void:
	if body.has_method("hurt"):
		body.hurt(global_position)
		Audio.combat_ping()


func player() -> Node2D:
	return get_tree().get_first_node_in_group("player") as Node2D


func apply_gravity(delta: float) -> void:
	velocity.y = minf(velocity.y + GRAVITY * delta, MAX_FALL)


func half_height(fallback_h: float) -> float:
	## Half-height of the body's own collision box — the enemy's real footprint.
	## Art cell size and collision height are unrelated numbers, so this has to be
	## read, never assumed. Hurtbox shapes are grandchildren and are skipped.
	for c in get_children():
		var cs := c as CollisionShape2D
		if cs != null and cs.shape is RectangleShape2D:
			var rect := cs.shape as RectangleShape2D
			return rect.size.y * 0.5
	return fallback_h * 0.5  # no shape / not a rect: best guess is the caller's size


func align_to_feet(s: AnimatedSprite2D, fallback_h: float) -> void:
	## A sprite child at (0,0) is CENTERED on the body origin, so a 64px cell puts its
	## feet 32px down while a 16px-tall collision box ends 8px down — the art sinks into
	## the floor by the difference. Push it up until the cell bottom meets the box bottom.
	##
	## Applied via `offset`, not `position`: the node transform stays at the body origin
	## so anything reading the visual's global_position still gets the body. offset.x
	## stays 0 because `centered` is true, which puts the cell's centre on the origin.
	## (flip_h does NOT mirror offset: it flips the texture inside a rect whose position
	## is unchanged, so a non-zero offset.x would shift the art the SAME way facing both
	## directions rather than mirroring. Verified against Sprite2D.is_pixel_opaque().)
	var cell := float(s.sprite_frames.get_frame_texture("a", 0).get_height())
	s.offset = Vector2(0.0, half_height(fallback_h) - cell * 0.5)


func setup_visual(path: String, count: int, fps: float, size: Vector2, color: Color) -> void:
	# ponytail: flat ColorRect stand-in until the strip exists — no per-enemy anim states
	if ResourceLoader.exists(path):
		var s := AnimatedSprite2D.new()
		s.sprite_frames = Fx.frames(path, count, fps, true)
		add_child(s)
		s.play("a")
		visual = s
		align_to_feet(s, size.y)
	else:
		var r := ColorRect.new()
		r.size = size
		# same rule as align_to_feet: bottom edge on the collision bottom, centered in x
		r.position = Vector2(-size.x * 0.5, half_height(size.y) - size.y)
		r.color = color
		add_child(r)
		visual = r
		base_color = color


func face(dir: int) -> void:
	## Source art faces RIGHT, so flip when heading left. No-op for the ColorRect
	## placeholder, which has no flip_h. dir == 0 keeps the last facing.
	if dir == 0 or not (visual is AnimatedSprite2D):
		return
	var s := visual as AnimatedSprite2D
	s.flip_h = dir < 0
	# ponytail: redundant guard — align_to_feet only ever writes offset.y and flip_h
	# never touches offset, so nothing can violate this. Ceiling: it is a free
	# assertion that the cell stays centred; safe to delete if the noise bothers you.
	s.offset.x = 0.0


func flash(c: Color, secs := 0.12) -> void:
	if visual == null:
		return
	var prop := "color" if visual is ColorRect else "modulate"
	visual.set(prop, c)
	create_tween().tween_property(visual, prop, base_color, secs)


func take_hit(dmg: int, from_dir: int) -> void:
	health -= dmg
	global_position.x += from_dir * 6.0
	Audio.combat_ping()
	flash(Color.WHITE)
	DamageNumbers.pop(global_position + Vector2(0, -14), dmg, health <= 0)
	if health <= 0:
		die()
	else:
		Audio.play("hit")   # the kill sound covers the fatal blow


func die() -> void:
	Audio.play("kill")
	Fx.burst(global_position, Color("c6f02a"))
	var soul := Area2D.new()
	soul.set_script(load("res://scripts/soul.gd"))
	get_parent().add_child(soul)
	soul.global_position = global_position + Vector2(0, -8)  # after add_child: parent may be offset
	queue_free()
