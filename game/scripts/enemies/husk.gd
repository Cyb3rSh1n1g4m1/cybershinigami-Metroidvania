class_name BotnetHusk
extends EnemyBase
## BOTNET NODE — a slow shuffling husk. They are networked: damage one and every
## husk within LINK_RANGE wakes up, doubles speed and turns on you for RAGE_TIME.

const SPEED := 26.0
const LINK_RANGE := 300.0
const RAGE_TIME := 4.0

var dir := -1
var rage := 0.0


func _init() -> void:
	health = 3


func _ready() -> void:
	super()
	setup_visual("res://art/enemies/husk.png", 6, 6.0, Vector2(64, 64), Color("1e33d9"))
	face(dir)


func _physics_process(delta: float) -> void:
	rage = maxf(rage - delta, 0.0)
	apply_gravity(delta)
	velocity.x = dir * SPEED * (2.0 if rage > 0.0 else 1.0)
	move_and_slide()
	if is_on_wall():
		dir *= -1
		face(dir)


func take_hit(dmg: int, from_dir: int) -> void:
	for n in get_tree().get_nodes_in_group("enemies"):
		var other := n as BotnetHusk
		if other and other != self \
				and global_position.distance_to(other.global_position) <= LINK_RANGE:
			other.enrage()
	super(dmg, from_dir)


func enrage() -> void:
	if rage <= 0.0:                    # the rage-link hits many at once; one shriek
		Audio.play_at("husk_shriek", global_position)
	rage = RAGE_TIME
	var p := player()
	if p:
		dir = 1 if p.global_position.x > global_position.x else -1
		face(dir)
	flash(Color("e01f26"), 0.3)
