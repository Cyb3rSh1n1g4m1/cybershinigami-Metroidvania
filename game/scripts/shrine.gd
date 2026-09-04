extends Area2D
## Snapshot station — Interact: stand close, press Up. Sets the respawn point and
## restores Integrity to full, both via player.gd (pray + set_respawn).
## ponytail: nothing is written to disk — the "snapshot" lives in the running process
## only, so quitting loses the run. Ceiling: a real save file, once there is more than
## one room to save a position in.

var _player_near := false


func _ready() -> void:
	z_index = -5  # behind the player: a 96px shrine otherwise hides him while praying
	var s := AnimatedSprite2D.new()
	s.sprite_frames = Fx.frames("res://art/objects/shrine.png", 4, 5.0, true)
	add_child(s)
	s.play("a")
	var shape := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 44.0
	shape.shape = c
	add_child(shape)
	collision_layer = 0
	collision_mask = 2
	Audio.attach_loop(self, "shrine_hum", -10.0)
	body_entered.connect(func(b: Node) -> void:
		if b.is_in_group("player"):
			_player_near = true
			Audio.music("shrine"))     # the relief moment (§14b.2)
	body_exited.connect(func(b: Node) -> void:
		if b.is_in_group("player"):
			_player_near = false
			Audio.music("region1_perimeter"))
	var prompt := InteractPrompt.new("UP", c.radius)  # same reach as the trigger above
	prompt.position = Vector2(0, -62)                 # clear of the 96px shrine cell
	add_child(prompt)


func _physics_process(_delta: float) -> void:
	if _player_near and Input.is_action_just_pressed("aim_up"):
		Audio.play_at("snapshot_save", global_position)
		Fx.burst(global_position + Vector2(0, -20), Color("35c6f4"))
		Fx.shake(1.5)
		Game.toast.emit("SNAPSHOT SAVED · ssh perimeter@0x0029")
		var p := get_tree().get_first_node_in_group("player")
		if p:
			p.pray(1.4)                       # kneel at the shrine
			p.set_respawn(global_position + Vector2(0, -8))  # this is now the checkpoint
