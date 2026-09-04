class_name Player
extends CharacterBody2D
## M1 grey-box player. All numbers from DESIGN.md §8 — tune here, not in scenes.

signal integrity_changed(cur: int, cap: int)
signal died

# -- movement constants (DESIGN.md §8) --
const RUN_SPEED := 130.0
const ACCEL_GROUND := 1400.0
const ACCEL_AIR := 700.0
const FRICTION_GROUND := 1800.0

const JUMP_VELOCITY := -330.0  # 60px apex — rescaled with the 72px figure; 3-tile step clears, 4-tile stays gated
const GRAVITY_RISING := 900.0
const GRAVITY_FALLING := 1400.0
const MAX_FALL_SPEED := 420.0
const JUMP_RELEASE_CUT := 0.40

const COYOTE_TIME := 0.10
const JUMP_BUFFER := 0.12

const DASH_SPEED := 400.0
const DASH_DURATION := 0.15
const DASH_COOLDOWN := 0.35

const ATTACK_COOLDOWN := 0.18   # SIGTERM: fast, chainable by mashing
const HURT_INVULN := 0.8
const DEATH_FREEZE := 1.2       # the death strip is 3f @ 8fps = 0.375s; the rest is a beat

# -- heavy verbs (DESIGN.md §16.2) — their own button: tap = SIGKILL,
# hold FE_HOLD = FORCED ENTRY. A shared button with light attack made the
# charge windows too tight to read.
const FE_HOLD := 0.5
const FE_SPEED := 500.0
const FE_DURATION := 0.28       # ~140px of travel, i-frames throughout
const FE_COOLDOWN := 2.5
const SIGKILL_WINDUP := 0.2     # the draw before the cut lands
const SLAM_SPEED := 620.0

var coyote_timer := 0.0
var jump_buffer_timer := 0.0
var dash_timer := 0.0
var dash_cooldown_timer := 0.0
var attack_cooldown_timer := 0.0
var attack_anim_timer := 0.0
var invuln_timer := 0.0
var flinch_timer := 0.0
var land_timer := 0.0
var turn_timer := 0.0
var attack_anim := "attack"
var pray_timer := 0.0
var double_jump_timer := 0.0
var air_jumps_left := 0
var respawn_point := Vector2.ZERO
var death_timer := 0.0
# heavy-verb state (§16.2)
var heavy_hold := -1.0          # <0 = heavy button not held
var _charge_fx: CPUParticles2D  # converging-energy aura while the draw is held
var heavy_strike_timer := 0.0   # SIGKILL windup: the cut lands when this expires
var fe_timer := 0.0             # FORCED ENTRY travel remaining
var fe_cooldown := 0.0
var _fe_hit := {}               # enemies already cut this dash (one hit each)
var armor_timer := 0.0          # SIGKILL draw: damage still lands, no flinch
var slam_active := false
var did_double_jump := false    # CORE DUMP is only earned by the double jump
# Integrity (DESIGN.md §3.1) — 5 segments at start, 10 is the upgrade ceiling.
# Vars rather than consts: vendor upgrades raise the cap mid-run.
# Both carry setters so one signal covers a lost pip AND a raised cap: upgrade_module.gd
# assigns these fields directly and never has to learn that a readout exists.
var max_integrity := 5:
	set(v):
		max_integrity = v
		integrity_changed.emit(integrity, v)
var integrity := 5:
	set(v):
		integrity = clampi(v, 0, max_integrity)
		integrity_changed.emit(integrity, max_integrity)
# room extents, set by the room on load; generous margins so legal air time is safe
var bounds := Rect2(-64, -600, 4096, 1400)
var was_on_floor := true
var crouching := false
var facing := 1

@onready var sprite: AnimatedSprite2D = $Sprite

# strips are 48x48 frames laid out horizontally (DESIGN.md §9.4)
# canon-sliced strips (slice_sheets.py -> assemble_v2.py)
const STRIPS := {
	# core strips come from the single-generation mega sheet (6f cycles);
	# attack: 6f at 20fps = 0.30s, matching the 0.31s attack_anim_timer
	"idle": ["res://art/player/player_idle.png", 6, 6.0, true],
	"run": ["res://art/player/player_run.png", 6, 12.0, true],
	"jump": ["res://art/player/player_jump.png", 4, 12.0, false],
	"fall": ["res://art/player/player_fall.png", 1, 8.0, true],
	"land": ["res://art/player/player_land.png", 2, 14.0, false],
	"hurt": ["res://art/player/player_hurt.png", 1, 8.0, true],
	"attack": ["res://art/player/player_attack.png", 3, 16.0, false],
	"heavy": ["res://art/player/player_heavy.png", 5, 10.0, false],
	"attack_up": ["res://art/player/player_attack_up.png", 3, 15.0, false],
	"attack_down": ["res://art/player/player_attack_down.png", 3, 15.0, false],
	"air_attack": ["res://art/player/player_air_attack.png", 1, 12.0, false],
	"dash": ["res://art/player/player_dash.png", 1, 12.0, true],
	"turn": ["res://art/player/player_turn.png", 3, 18.0, false],
	"crouch": ["res://art/player/player_crouch.png", 1, 6.0, true],
	"death": ["res://art/player/player_death.png", 3, 8.0, false],
	"double_jump": ["res://art/player/player_double_jump.png", 1, 10.0, false],
	"pray": ["res://art/player/player_pray.png", 1, 4.0, true],
	"iai": ["res://art/player/player_iai.png", 4, 6.0, true],
	"iai_enter": ["res://art/player/player_iai_enter.png", 3, 14.0, false],
}


func _ready() -> void:
	add_to_group("player")
	respawn_point = global_position
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for anim in STRIPS:
		var tex: Texture2D = load(STRIPS[anim][0])
		var count: int = STRIPS[anim][1]
		frames.add_animation(anim)
		frames.set_animation_speed(anim, STRIPS[anim][2])
		frames.set_animation_loop(anim, STRIPS[anim][3])
		for i in count:
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(i * 96, 0, 96, 96)
			frames.add_frame(anim, at)
	sprite.sprite_frames = frames
	sprite.play("idle")
	sprite.frame_changed.connect(_on_frame)


func _on_frame() -> void:
	# §14b: footsteps ride the run cycle's contact frames (0 and 3 of the 6f gait)
	if sprite.animation == "run":
		if sprite.frame == 0:
			Audio.play("step_a")
		elif sprite.frame == 3:
			Audio.play("step_b")


func _update_anim(delta: float) -> void:
	if is_on_floor() and not was_on_floor:
		land_timer = 0.14
		Audio.play("land")
	was_on_floor = is_on_floor()
	land_timer -= delta
	attack_anim_timer -= delta
	turn_timer -= delta
	pray_timer -= delta
	double_jump_timer -= delta

	sprite.rotation = 0.0                      # undo dash pitch

	var next := "idle"
	if pray_timer > 0.0 and is_on_floor():
		next = "pray"
	elif flinch_timer > 0.0:
		# explicit flag, not "invuln_timer is still high": respawn also grants
		# i-frames, and reading them as damage made the reaper reappear flinching
		next = "hurt"
	elif attack_anim_timer > 0.0:
		next = attack_anim
	elif heavy_hold >= 0.0 and is_on_floor():
		# settle INTO the coil (3f, ~0.21s), then hold the breathing loop
		next = "iai_enter" if heavy_hold < 0.21 else "iai"
	elif double_jump_timer > 0.0 and not is_on_floor():
		next = "double_jump"
	elif not is_on_floor():
		next = "jump" if velocity.y < 0.0 else "fall"
	elif land_timer > 0.0:
		next = "land"
	elif turn_timer > 0.0:
		next = "turn"
	elif crouching:
		next = "crouch"
	elif absf(get_real_velocity().x) > 10.0:
		# real velocity, not intended: pushing into a wall keeps velocity.x high
		# while the body does not move, which left the run cycle spinning in place
		next = "run"
	if sprite.animation != next:
		sprite.play(next)


func _do_attack(offset: Vector2, size: Vector2, _cut_angle: float, dmg := 1) -> void:
	## NO separate slash VFX. The attack animation frames already have the green
	## arc drawn into them, so spawning Fx.slash on top produced TWO crescents per
	## swing — and because the arc sprite is flipped about the node origin while the
	## hitbox offset already accounts for facing, the second one could land on the
	## wrong side of the body entirely. The animation owns the arc; impact feedback
	## below fires only when the cut actually connects.
	var query := PhysicsShapeQueryParameters2D.new()
	var shape := RectangleShape2D.new()
	shape.size = size
	query.shape = shape
	query.transform = Transform2D(0.0, global_position + offset)
	query.collision_mask = 4  # enemies only
	var landed := false
	for hit in get_world_2d().direct_space_state.intersect_shape(query):
		if hit.collider.has_method("take_hit"):
			hit.collider.take_hit(dmg, facing)
			landed = true
	if landed:
		Fx.shake(2.0)
		Fx.hitstop(3)
		# feedback at the point of contact, not a second arc through the air
		if ResourceLoader.exists("res://art/effects/impact.png"):
			Fx.play_strip(global_position + offset, "res://art/effects/impact.png",
				4, 26.0)


func _physics_process(delta: float) -> void:
	if death_timer > 0.0:
		_process_death(delta)
		return

	var on_floor := is_on_floor()

	# timers
	coyote_timer = COYOTE_TIME if on_floor else coyote_timer - delta
	if on_floor:
		air_jumps_left = 1                     # refreshed on landing; spent mid-air
	jump_buffer_timer -= delta
	dash_cooldown_timer -= delta
	attack_cooldown_timer -= delta
	invuln_timer -= delta
	flinch_timer -= delta
	if Input.is_action_just_pressed("jump"):
		jump_buffer_timer = JUMP_BUFFER

	fe_cooldown -= delta
	armor_timer -= delta
	if on_floor:
		did_double_jump = false

	# FORCED ENTRY travel — overrides everything, i-frames throughout (§16.2)
	if fe_timer > 0.0:
		fe_timer -= delta
		velocity.x = facing * FE_SPEED
		velocity.y = 0.0
		if sprite.animation != "heavy":
			sprite.play("heavy")           # the draw-CUT plays across the travel
		Fx.ghost(sprite)
		# cut everything passed through, once each
		var q := PhysicsShapeQueryParameters2D.new()
		var shp := RectangleShape2D.new()
		shp.size = Vector2(44, 48)
		q.shape = shp
		q.transform = Transform2D(0.0, global_position)
		q.collision_mask = 4
		for hit in get_world_2d().direct_space_state.intersect_shape(q):
			var body_hit: Object = hit.collider
			if not _fe_hit.has(body_hit) and body_hit.has_method("take_hit"):
				_fe_hit[body_hit] = true
				body_hit.take_hit(3, facing)
				Fx.hitstop(2)
		move_and_slide()
		return

	# CORE DUMP — down+attack airborne, only after the double jump (§16.2)
	if slam_active:
		velocity.x = 0.0
		velocity.y = SLAM_SPEED
		if sprite.animation != "attack_down":
			sprite.play("attack_down")
		var qs := PhysicsShapeQueryParameters2D.new()
		var shs := RectangleShape2D.new()
		shs.size = Vector2(34, 50)
		qs.shape = shs
		qs.transform = Transform2D(0.0, global_position + Vector2(0, 30))
		qs.collision_mask = 4
		for hit in get_world_2d().direct_space_state.intersect_shape(qs):
			if hit.collider.has_method("take_hit"):
				hit.collider.take_hit(2, facing)
		move_and_slide()
		if is_on_floor():
			slam_active = false
			Fx.shake(4.0)
			Fx.hitstop(4)
			Audio.play("slam_impact")
			Fx.play_strip(global_position + Vector2(0, 20),
				"res://art/effects/dust_cloud.png", 5, 16.0)
			Fx.burst(global_position + Vector2(0, 30), Color("c6f02a"))
			var qi := PhysicsShapeQueryParameters2D.new()
			var shi := RectangleShape2D.new()
			shi.size = Vector2(96, 26)          # the landing shockwave
			qi.shape = shi
			qi.transform = Transform2D(0.0, global_position + Vector2(0, 28))
			qi.collision_mask = 4
			for hit in get_world_2d().direct_space_state.intersect_shape(qi):
				if hit.collider.has_method("take_hit"):
					hit.collider.take_hit(1, facing)
			land_timer = 0.2
		return

	if Input.is_action_just_pressed("attack") and not on_floor \
			and did_double_jump and Input.is_action_pressed("aim_down") \
			and Game.has("slam"):
		slam_active = true
		Audio.play("swing_gedan")
		return

	# SIGKILL windup resolving: the draw finishes, the wave cut lands (§16.2,
	# Strider-style — slow, long, and the arc projects forward)
	if heavy_strike_timer > 0.0:
		heavy_strike_timer -= delta
		if heavy_strike_timer <= 0.0:
			Audio.play("swing_gedan")
			_do_attack(Vector2(facing * 58, 0), Vector2(110, 56), 0.0, 3)
			if ResourceLoader.exists("res://art/effects/crescent.png"):
				Fx.wave(global_position + Vector2(facing * 46, -4), facing,
					"res://art/effects/crescent.png", 4, 20.0)

	# heavy button: tap = SIGKILL (ground), hold FE_HOLD = FORCED ENTRY (§16.2)
	if Input.is_action_just_pressed("heavy") and heavy_hold < 0.0 \
			and heavy_strike_timer <= 0.0 and (Game.has("heavy") or Game.has("charge")):
		heavy_hold = 0.0
		Audio.play("heavy_draw")               # the saya scrape: draw begun
		if _charge_fx == null and Game.has("charge"):
			_charge_fx = Fx.charge_aura(self)  # energy converging on the body
	if heavy_hold >= 0.0:
		if Input.is_action_pressed("heavy"):
			var before := heavy_hold
			heavy_hold += delta
			if before < FE_HOLD and heavy_hold >= FE_HOLD \
					and Game.has("charge") and fe_cooldown <= 0.0:
				Audio.play("toast_blip")       # fully drawn: FORCED ENTRY ready
		else:
			if heavy_hold >= FE_HOLD and Game.has("charge") \
					and fe_cooldown <= 0.0:
				fe_timer = FE_DURATION
				fe_cooldown = FE_COOLDOWN
				_fe_hit = {}
				Audio.play("fe_release")
				if ResourceLoader.exists("res://art/effects/crescent.png"):
					Fx.wave(global_position + Vector2(facing * 40, -2), facing,
						"res://art/effects/crescent.png", 4, 16.0, 110.0, 0.3)
			elif Game.has("heavy") and on_floor:
				# SIGKILL: the whole 5-frame draw plays (0.5s); the cut and the
				# projected wave land when the windup expires above
				attack_anim = "heavy"
				attack_anim_timer = 0.5
				armor_timer = 0.6
				heavy_strike_timer = SIGKILL_WINDUP
				sprite.play("heavy")
			heavy_hold = -1.0
			if _charge_fx != null:
				_charge_fx.queue_free()
				_charge_fx = null

	# SIGTERM (wakizashi) — immediate shape query on press: symmetric, no frame lag.
	# Kendo stances: Up = jodan, neutral = chudan, Down = gedan. See DESIGN.md §2.2.
	if Input.is_action_just_pressed("attack") and attack_cooldown_timer <= 0.0:
		attack_cooldown_timer = ATTACK_COOLDOWN
		attack_anim_timer = 0.19   # 3 frames @ 16fps — starts at the travel frame
		# stance-specific attack animation (DESIGN.md §2.2 kendo stances)
		if not is_on_floor():
			attack_anim = "air_attack"
		elif Input.is_action_pressed("aim_up"):
			attack_anim = "attack_up"
		elif Input.is_action_pressed("aim_down"):
			attack_anim = "attack_down"
		else:
			attack_anim = "attack"
		sprite.play(attack_anim)
		match attack_anim:
			"attack_up":
				Audio.play("swing_jodan")
			"attack_down":
				Audio.play("swing_gedan")
			_:
				Audio.play("swing_chudan")   # chudan and the air cut share a voice
		var offset := Vector2(facing * 36, 0)      # chudan — level cut
		var size := Vector2(54, 48)
		var cut_angle := 0.0
		if Input.is_action_pressed("aim_up"):      # jodan — overhead, kesa-giri downward diagonal
			offset = Vector2(facing * 24, -46)
			size = Vector2(50, 44)
			cut_angle = -55.0
		elif Input.is_action_pressed("aim_down"):  # gedan — down-forward cut, reaches ~25px below the feet
			offset = Vector2(facing * 24, 42)
			size = Vector2(66, 44)
			cut_angle = 40.0
		_do_attack(offset, size, cut_angle)
		# the green arc cue — every cut draws its slash in the air (§16.2 note)
		Fx.play_strip(global_position + offset * 0.8,
			"res://art/effects/swing_arc.png", 3, 30.0,
			deg_to_rad(cut_angle) * facing, facing < 0)

	# dash state overrides everything while active (i-frames: see hurt())
	if dash_timer > 0.0:
		dash_timer -= delta
		velocity.x = facing * DASH_SPEED
		velocity.y = 0.0
		if sprite.animation != "dash":
			sprite.play("dash")
		sprite.rotation = 0.35 * facing        # ~20° forward pitch
		Fx.ghost(sprite)                       # afterimage trail every physics frame
		move_and_slide()
		return

	if Input.is_action_just_pressed("dash") and dash_cooldown_timer <= 0.0:
		dash_timer = DASH_DURATION
		dash_cooldown_timer = DASH_COOLDOWN
		Audio.play("dash")
		return

	# crouch: grounded + holding down (SotN duck — no walking while ducked)
	crouching = on_floor and Input.is_action_pressed("aim_down") \
		and attack_anim_timer <= 0.0

	# horizontal
	var dir := Input.get_axis("move_left", "move_right")
	if crouching:
		dir = 0.0
	if dir != 0.0:
		# NOT signi(dir): dir is a float axis, and signi's int parameter truncates
		# any analog value between the deadzone and 1.0 to signi(0) = 0 — facing
		# stuck at 0, dashes froze in place, knockback lost its direction. Only
		# full-strength keyboard input (exactly ±1.0) ever survived it.
		var new_facing := 1 if dir > 0.0 else -1
		if new_facing != facing and on_floor:
			turn_timer = 0.16                  # SotN turn-around transition (3f @ 18fps)
			Audio.play("turn")
		facing = new_facing
		sprite.flip_h = facing < 0
		var accel := ACCEL_GROUND if on_floor else ACCEL_AIR
		velocity.x = move_toward(velocity.x, dir * RUN_SPEED, accel * delta)
	elif on_floor:
		velocity.x = move_toward(velocity.x, 0.0, FRICTION_GROUND * delta)

	# asymmetric gravity
	var gravity := GRAVITY_RISING if velocity.y < 0.0 else GRAVITY_FALLING
	velocity.y = minf(velocity.y + gravity * delta, MAX_FALL_SPEED)

	# jump: buffered press + coyote window
	if jump_buffer_timer > 0.0 and coyote_timer > 0.0:
		velocity.y = JUMP_VELOCITY
		jump_buffer_timer = 0.0
		coyote_timer = 0.0
		Audio.play("jump")
	elif jump_buffer_timer > 0.0 and air_jumps_left > 0 and Game.has("double_jump"):
		# Privilege Escalation (DESIGN.md §4 #2) — one air jump, slightly weaker.
		# 63px ground rise + 54px here = ~117px, clearing the 112px gated perch.
		velocity.y = JUMP_VELOCITY * 0.95
		air_jumps_left -= 1
		did_double_jump = true     # CORE DUMP unlocked for this airtime (§16.2)
		jump_buffer_timer = 0.0
		double_jump_timer = 0.22
		sprite.play("double_jump")
		Fx.burst(global_position + Vector2(0, 28), Color("35c6f4"))
		Fx.play_strip(global_position + Vector2(0, 20),
			"res://art/effects/dj_ring.png", 4, 22.0)
		Audio.play("double_jump")   # no-op until the rising chime lands (§14b.3)

	# variable jump height
	if Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= JUMP_RELEASE_CUT

	move_and_slide()
	_check_bounds()
	_update_anim(delta)


func set_respawn(p: Vector2) -> void:
	respawn_point = p


func _check_bounds() -> void:
	# Falling out of the world used to be unrecoverable: the body kept falling
	# forever while the camera clamped, so the run was simply over.
	if global_position.y < bounds.position.y - 400.0:
		return  # high above the room is legal — jump arcs and the perch live there
	if bounds.has_point(global_position):
		return
	snapshot_restore()
	Game.toast.emit("SIGNAL LOST · restored from snapshot")


func snapshot_restore() -> void:
	## Back to the last Snapshot station with Integrity full. Falling out of the room,
	## running out of Integrity and the pause menu's RESTART FROM SNAPSHOT all land
	## here, so there is exactly one restore path to reason about.
	integrity = max_integrity
	death_timer = 0.0  # the pause menu can restore mid-death; one path clears the freeze
	global_position = respawn_point
	velocity = Vector2.ZERO
	air_jumps_left = 1
	invuln_timer = HURT_INVULN  # a breath of grace on arrival
	# a hit taken just before a bounds-fall or pause-restore leaves these set; the
	# reaper must arrive standing, not flinching or auto-jumping
	flinch_timer = 0.0
	jump_buffer_timer = 0.0
	heavy_hold = -1.0
	heavy_strike_timer = 0.0
	fe_timer = 0.0
	slam_active = false
	Audio.play("respawn")   # no-op until the modem-handshake sound lands
	Fx.burst(respawn_point, Color("35c6f4"))
	Fx.shake(2.0)


func pray(secs: float) -> void:
	pray_timer = secs
	velocity.x = 0.0
	integrity = max_integrity  # a snapshot restores the host, not just its position


func hurt(from_pos: Vector2) -> void:
	# dash and FORCED ENTRY grant i-frames; the death freeze ignores everything
	if invuln_timer > 0.0 or dash_timer > 0.0 or fe_timer > 0.0 \
			or death_timer > 0.0:
		return
	invuln_timer = HURT_INVULN
	Audio.play("hurt")
	integrity -= 1  # setter clamps at 0 and emits, so the pip row reacts on its own
	if armor_timer > 0.0:
		# SIGKILL draw armor: the cut lands, the draw does not stop — damage
		# without flinch or knockback (§16.2 "cannot be flinched")
		sprite.modulate = Color("e01f26")
		var ta := create_tween()
		ta.tween_property(sprite, "modulate", Color.WHITE, 0.3)
		if integrity <= 0:
			_die()
		return
	flinch_timer = 0.35   # damage, so play the flinch
	velocity = Vector2(signf(global_position.x - from_pos.x) * 180.0, -150.0)
	sprite.modulate = Color("e01f26")
	var t := create_tween()
	t.tween_property(sprite, "modulate", Color.WHITE, 0.3)
	Fx.shake(3.0)
	# NO edge flash here. hud.gd already vignettes on integrity_changed, and firing
	# UI.edge_flash as well stacked two red overlays on every hit (measured: HUD
	# shader at 0.458 while UI._edge sat at 0.222). Damage feedback belongs to the
	# HUD, which owns the integrity display — one owner, one flash.
	if integrity <= 0:
		_die()


func _die() -> void:
	## The knockback from the killing blow is deliberately left in place — the reaper
	## is thrown by the hit that finishes him, then slides to a stop under _process_death.
	death_timer = DEATH_FREEZE
	# _update_anim is skipped for the whole freeze, so these never tick down — left set,
	# they resume on respawn and the reaper comes back mid-prayer, mid-swing, mid-flinch,
	# or auto-jumping off a press buffered just before the killing blow.
	pray_timer = 0.0
	attack_anim_timer = 0.0
	flinch_timer = 0.0     # the killing hurt() set this one frame earlier
	jump_buffer_timer = 0.0
	heavy_hold = -1.0
	heavy_strike_timer = 0.0
	fe_timer = 0.0
	slam_active = false
	sprite.play("death")
	Audio.play("death")     # no-op until the sound lands
	died.emit()
	Fx.shake(5.0)
	Fx.burst(global_position, Color("e01f26"))


func _process_death(delta: float) -> void:
	## Terminated: no input, and _update_anim never runs, so the death strip plays out
	## untouched by the animation state machine. Reloading the scene would also throw
	## away cleared enemies, spent modules and the shrine — only the host is restored.
	death_timer -= delta
	velocity.x = move_toward(velocity.x, 0.0, FRICTION_GROUND * delta)
	velocity.y = minf(velocity.y + GRAVITY_FALLING * delta, MAX_FALL_SPEED)
	move_and_slide()
	if death_timer <= 0.0:
		snapshot_restore()
		Game.toast.emit("INTEGRITY ZERO · restored from snapshot")
