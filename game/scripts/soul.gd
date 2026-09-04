extends Area2D
## Hitodama soul byte — drifts free for a beat, then homes to the reaper.

var t := 0.0


func _ready() -> void:
	var s := AnimatedSprite2D.new()
	s.sprite_frames = Fx.frames("res://art/effects/soul.png", 4, 8.0, true)
	add_child(s)
	s.play("a")
	var shape := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 7.0
	shape.shape = c
	add_child(shape)
	collision_layer = 0
	collision_mask = 2  # player only
	body_entered.connect(_on_touch)


func _physics_process(delta: float) -> void:
	t += delta
	var player := get_tree().get_first_node_in_group("player")
	if t > 0.5 and player:
		var speed := minf(90.0 + (t - 0.5) * 260.0, 380.0)  # accelerating homing
		global_position = global_position.move_toward(player.global_position, speed * delta)
	else:
		position.y += sin(t * 7.0) * 0.35  # free bob


func _on_touch(body: Node) -> void:
	if body.is_in_group("player"):
		Game.soul_bytes += 1
		Audio.play_soul()   # chained collects climb in pitch (§14b.3)
		Fx.burst(global_position, Color("c6f02a"))
		queue_free()
