extends EnemyBase
## Worm (DESIGN.md §5): if not killed within 4s of noticing you, splits into two
## half-health copies. Splits recursively until health would drop below 1.

const SPEED := 40.0
const SPLIT_TIME := 4.0
const SPRITE := "res://art/enemies/worm.png"

var dir := -1
var split_timer := SPLIT_TIME
var aggro := false


func _init() -> void:
	health = 4


func _ready() -> void:
	super()
	# real strip when present; the scene's ColorRect is the fallback
	var body: ColorRect = $Body
	if ResourceLoader.exists(SPRITE):
		body.visible = false
		var s := AnimatedSprite2D.new()
		s.sprite_frames = Fx.frames(SPRITE, 6, 8.0, true)
		add_child(s)
		s.play("a")
		visual = s
		base_color = Color.WHITE
		align_to_feet(s, 16.0)  # 64px cell over a 16px-tall box: sinks 24px without this
	else:
		body.color = Color("e01f26")  # RED
		visual = body
		base_color = body.color
	face(dir)  # dir is set by _split() before add_child, so it is already correct here


func _physics_process(delta: float) -> void:
	# ponytail: aggro = player within 100px, no line-of-sight check
	if not aggro:
		var p := player()
		if p and global_position.distance_to(p.global_position) < 100.0:
			aggro = true

	if aggro:
		split_timer -= delta
		if split_timer <= 0.0 and health > 1:
			_split()
			return

	apply_gravity(delta)
	velocity.x = dir * SPEED
	move_and_slide()
	if is_on_wall():
		dir *= -1
		face(dir)


func _split() -> void:
	Audio.play_at("worm_split", global_position)
	var scene := load("res://scenes/enemies/worm.tscn")
	for offset in [-10.0, 10.0]:
		var w: CharacterBody2D = scene.instantiate()
		w.health = maxi(1, health / 2)
		w.aggro = true
		w.dir = -1 if offset < 0 else 1
		w.scale = scale * 0.8
		get_parent().add_child(w)
		w.global_position = global_position + Vector2(offset, -2)  # after add_child: parent may be offset
	Fx.burst(global_position, Color("e01f26"))
	queue_free()
