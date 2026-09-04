extends EnemyBase
## ZERO-DAY GUARDIAN — heavy. One committed sweep, so the whole fight is a loop:
## read the tell -> dodge or dash through -> punish while it hangs open.
##
## FINAL TIMINGS (one commit = 1.58s, then 0.40s before it can wind again):
##   PATROL  30px/s, turns at walls AND at ledges (down-probe 26px ahead).
##           Winds when the player is inside 96px across / 72px up-down.
##   WIND    0.55s. Planted, leaning back. modulate climbs white -> acid-green
##           while the pulse rate rises with k^2, so the tell INTENSIFIES into
##           the commit instead of fading out of it.
##   SWING   0.28s, which quantises to 18 physics frames (0.300s) at 60Hz.
##           Accelerates at 2400px/s^2 to a 300px/s cap, 69px of travel. The
##           blade (46x46, +12..+58 ahead of its CURRENT position) is tested
##           every physics frame, once per swing, so the damage lands mid-lunge
##           — measured first contact is 24px into the drive up close and 34px
##           from the 96px trigger edge, never from the plant. The swept corridor
##           reaches 122px past the plant: retreating clears it (~68px of player
##           travel during the wind carries you from 96px out to ~164px) and
##           dashing through beats it. Standing still does not, and a jump only
##           does frame-perfectly: clearing a 46px blade needs the feet 54px up
##           against a 60px apex, ~0.22s of clearance against ~0.21s of exposure.
##           The drive aborts if the floor runs out 44px ahead — the blade still
##           sweeps, so backing onto a lip does not disarm it.
##   OPEN    0.75s. Skids to a stop, slumps forward, dims to steel — a different
##           colour from the tell — and take_hit doubles. At the player's 0.18s
##           attack cooldown 3 hits kill it from health 6, so a clean read is a
##           clean kill. The dim lifts over the last ~0.2s: the window is
##           visibly closing.

const SPEED := 30.0
const PATROL_ACCEL := 240.0
const TRIGGER_RANGE := 96.0
const TRIGGER_HEIGHT := 72.0

const WIND_TIME := 0.55
const SWING_TIME := 0.28
const OPEN_TIME := 0.75
const RECOVER_TIME := 0.40

const LUNGE_ACCEL := 2400.0
const LUNGE_SPEED := 300.0
const OPEN_DRAG := 900.0

const BLADE_SIZE := Vector2(46.0, 46.0)
const BLADE_OFFSET := 35.0   # +12..+58 ahead of centre: a mid-height horizontal cut
const BLADE_Y := 1.0

const PROBE_AHEAD := 26.0    # past the 22px half-width, so it reads the next tile
const PROBE_LUNGE := 44.0    # the lunge covers ground faster, so it looks further
const PROBE_DROP := 18.0     # one 16px tile of drop still counts as floor

const ACID := Color("c6f02a")
const SLUMP := Color("4a5568")

enum { PATROL, WIND, SWING, OPEN }

var state := PATROL
var timer := 0.0
var dir := -1
var vulnerable := false
var swing_hit := false
var half_h := 32.0  # half the collision box, read off the scene in _ready


func _init() -> void:
	health = 6


func _ready() -> void:
	super()
	setup_visual("res://art/enemies/guardian.png", 6, 6.0, Vector2(96, 96), Color("0a0e1f"))
	# ponytail: "green edge" = a green rect drawn behind a slightly smaller body
	if visual is ColorRect:
		var body: ColorRect = visual
		var edge := ColorRect.new()
		# derived from the body rect, which setup_visual already sat on the collision
		# bottom — hardcoding -48 here would re-sink the placeholder by 16px
		edge.size = body.size
		edge.position = body.position
		edge.color = Color("c6f02a")
		add_child(edge)
		move_child(edge, body.get_index())
		body.size = edge.size - Vector2(8, 8)
		body.position = edge.position + Vector2(4, 4)
	half_h = half_height(96.0)
	face(dir)
	_look(Color.WHITE, 0.0)


func _physics_process(delta: float) -> void:
	apply_gravity(delta)
	timer -= delta

	match state:
		PATROL:
			_patrol(delta)
		WIND:
			_wind()
		SWING:
			_swing(delta)
		OPEN:
			_open(delta)

	move_and_slide()
	if state == PATROL and is_on_wall():
		dir *= -1
		face(dir)


func _patrol(delta: float) -> void:
	var p := player()
	if timer <= 0.0 and p \
			and absf(p.global_position.x - global_position.x) < TRIGGER_RANGE \
			and absf(p.global_position.y - global_position.y) < TRIGGER_HEIGHT:
		dir = 1 if p.global_position.x > global_position.x else -1
		face(dir)  # commits to you as it plants, before the tell plays
		state = WIND
		timer = WIND_TIME
		swing_hit = false
		velocity.x = 0.0
		Audio.play_at("guardian_telegraph", global_position)
		Audio.music("boss_bruteforce")   # the encounter owns the soundtrack
		return

	# ledge check runs BEFORE the step, so it turns at the lip instead of walking off
	if not _floor_ahead(dir * PROBE_AHEAD):
		if _floor_ahead(-dir * PROBE_AHEAD):
			dir *= -1
			face(dir)
		else:
			# ponytail: stranded on a stub with floor on neither side — stand still
			# rather than flip every frame. Ceiling: it never steps down off a ledge.
			velocity.x = 0.0
			_look(Color.WHITE, 0.0)
			return

	velocity.x = move_toward(velocity.x, dir * SPEED, PATROL_ACCEL * delta)
	_look(Color.WHITE, 0.0)


func _wind() -> void:
	velocity.x = 0.0
	# the tell INTENSIFIES: colour drives toward acid-green while the pulse both
	# quickens (k^2) and brightens, peaking on the frame it commits
	var k := clampf(1.0 - timer / WIND_TIME, 0.0, 1.0)
	var pulse := 0.5 + 0.5 * sin(k * k * 34.0)   # ~1 beat early, ~5 beats late
	var glow := 1.0 + 1.1 * k * pulse
	var c := Color.WHITE.lerp(ACID, 0.35 + 0.65 * k)
	_look(Color(c.r * glow, c.g * glow, c.b * glow, 1.0), -0.12 * k)  # leans back to coil

	if timer <= 0.0:
		state = SWING
		timer = SWING_TIME
		swing_hit = false
		Fx.shake(3.0)   # the moment of commitment
		Audio.play_at("guardian_slam", global_position)


func _swing(delta: float) -> void:
	if _floor_ahead(dir * PROBE_LUNGE):
		velocity.x = move_toward(velocity.x, dir * LUNGE_SPEED, LUNGE_ACCEL * delta)
	else:
		velocity.x = 0.0   # ledge ahead: abort the drive, the blade still sweeps

	_blade()
	_look(Color(ACID.r * 1.6, ACID.g * 1.6, ACID.b * 1.6, 1.0), 0.20)

	if timer <= 0.0:
		state = OPEN
		timer = OPEN_TIME
		vulnerable = true
		Audio.play_at("guardian_stagger", global_position)


func _open(delta: float) -> void:
	velocity.x = move_toward(velocity.x, 0.0, OPEN_DRAG * delta)   # skid, not a hard stop
	var o := clampf(1.0 - timer / OPEN_TIME, 0.0, 1.0)
	var wake := smoothstep(0.72, 1.0, o)   # last ~0.2s it straightens and brightens back
	_look(SLUMP.lerp(Color.WHITE, wake), 0.22 - 0.10 * wake)

	if timer <= 0.0:
		state = PATROL
		timer = RECOVER_TIME
		vulnerable = false


func take_hit(dmg: int, from_dir: int) -> void:
	super(dmg * (2 if vulnerable else 1), from_dir)


func die() -> void:
	Audio.music("region1_perimeter")   # the encounter is over; the city returns
	super()


func _blade() -> void:
	# damage window == the visible lunge: re-queried every SWING frame from where
	# the body is NOW, capped at one landed hit per swing
	if swing_hit:
		return
	var q := PhysicsShapeQueryParameters2D.new()
	var box := RectangleShape2D.new()
	box.size = BLADE_SIZE
	q.shape = box
	q.transform = Transform2D(0.0, global_position + Vector2(dir * BLADE_OFFSET, BLADE_Y))
	q.collision_mask = 2  # player only
	for hit: Dictionary in get_world_2d().direct_space_state.intersect_shape(q):
		if hit.collider.has_method("hurt"):
			# ponytail: overlap counts as a connect, so dashing through spends the
			# swing and takes the hitstop as a slow-mo near-miss. Ceiling: hurt()
			# returns nothing, so a true "did it land" needs a signal on the player.
			hit.collider.hurt(global_position)
			swing_hit = true
			Fx.shake(4.0)
			Fx.hitstop(3)
			return


func _floor_ahead(step: float) -> bool:
	# short down-probe just past the leading edge. Mask 1 is world geometry only,
	# so the guardian (layer 4) and the player (layer 2) never answer it.
	var from := global_position + Vector2(step, half_h - 6.0)
	var q := PhysicsRayQueryParameters2D.create(from, from + Vector2(0.0, PROBE_DROP), 1)
	return not get_world_2d().direct_space_state.intersect_ray(q).is_empty()


func _look(tint: Color, lean: float) -> void:
	# visual is an AnimatedSprite2D once the strip exists and a ColorRect before it;
	# facing lives in EnemyBase.face(), which also protects the flip offset
	if visual == null:
		return
	if visual is ColorRect:
		(visual as ColorRect).color = tint
		return  # the placeholder's edge rect is a sibling, so leaning would split them
	var s := visual as AnimatedSprite2D
	s.modulate = tint
	s.rotation = lean * dir
