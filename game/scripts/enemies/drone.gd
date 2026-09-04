extends EnemyBase
## KEYLOGGER — a flyer that never attacks. It trails you and watches; three
## continuous seconds of line of sight and your session is captured. Kill it first.

const SPEED := 34.0
const KEEP_DIST := 96.0     # never closes past this — it only needs to see you
const HOVER_HEIGHT := 48.0
const BOB_SPEED := 2.2
const BOB_VEL := 26.0
const LOG_TIME := 3.0

var t := 0.0
var watch := 0.0
var alerted := false


func _init() -> void:
	health = 2


func _ready() -> void:
	super()
	setup_visual("res://art/enemies/drone.png", 6, 8.0, Vector2(48, 48), Color("35c6f4"))
	Audio.attach_loop(self, "drone_hum", -14.0)


func _physics_process(delta: float) -> void:
	t += delta
	var p := player()
	if p == null:
		return

	if not alerted:
		if _sees(p):
			watch += delta
			if watch >= LOG_TIME:
				_capture()
		else:
			watch = 0.0

	# flyer: velocity is set outright every frame, so gravity never applies
	var dx := p.global_position.x - global_position.x
	face(1 if dx > 0.0 else -1)  # it watches you, so it faces you even while holding station
	var vx := signf(dx) * SPEED if absf(dx) > KEEP_DIST else 0.0
	var want_y := p.global_position.y - HOVER_HEIGHT
	var vy := clampf((want_y - global_position.y) * 2.0, -SPEED, SPEED)
	velocity = Vector2(vx, vy + sin(t * BOB_SPEED) * BOB_VEL)
	move_and_slide()


func _sees(p: Node2D) -> bool:
	var q := PhysicsRayQueryParameters2D.create(global_position, p.global_position, 1)
	return get_world_2d().direct_space_state.intersect_ray(q).is_empty()


func _capture() -> void:
	alerted = true
	Audio.play_at("drone_alert", global_position)
	flash(Color("8fe8ff"), 0.4)
	Fx.shake(1.0)
	Game.toast.emit("KEYLOGGER: session captured")
