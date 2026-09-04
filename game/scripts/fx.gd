extends Node
## Autoload "Fx" — the entire hit-feel kit (DESIGN.md §8): hitstop, shake, burst,
## plus sprite-strip VFX playback (square cells only).

var _strip_cache := {}


func frames(path: String, count: int, fps: float, loop: bool) -> SpriteFrames:
	# square-cell horizontal strip -> cached SpriteFrames
	var key := "%s|%d|%f|%s" % [path, count, fps, loop]
	if _strip_cache.has(key):
		return _strip_cache[key]
	var f := SpriteFrames.new()
	f.remove_animation("default")
	f.add_animation("a")
	f.set_animation_speed("a", fps)
	f.set_animation_loop("a", loop)
	var tex: Texture2D = load(path)
	var cell := tex.get_height()
	for i in count:
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(i * cell, 0, cell, cell)
		f.add_frame("a", at)
	_strip_cache[key] = f
	return f


func play_strip(pos: Vector2, path: String, count: int, fps: float,
		rot := 0.0, flip := false) -> void:
	# fire-and-forget one-shot VFX
	var s := AnimatedSprite2D.new()
	s.sprite_frames = frames(path, count, fps, false)
	s.rotation = rot
	s.flip_h = flip
	s.global_position = pos
	get_tree().current_scene.add_child(s)
	s.play("a")
	s.animation_finished.connect(s.queue_free)


func wave(pos: Vector2, dir: int, path: String, count: int, fps: float,
		travel := 70.0, secs := 0.22) -> void:
	# a projected slash: the strip plays once while the whole sprite flies
	# forward and fades — the Strider-style wave (DESIGN.md §16.2 SIGKILL)
	var s := AnimatedSprite2D.new()
	s.sprite_frames = frames(path, count, fps, false)
	s.flip_h = dir < 0
	s.global_position = pos
	get_tree().current_scene.add_child(s)
	s.play("a")
	var t := s.create_tween()
	t.set_parallel(true)
	t.tween_property(s, "global_position:x", pos.x + dir * travel, secs)
	t.tween_property(s, "modulate:a", 0.0, secs).set_delay(secs * 0.4)
	t.chain().tween_callback(s.queue_free)


func charge_aura(parent: Node2D) -> CPUParticles2D:
	# energy CONVERGING on the body — the battojutsu gather before FORCED
	# ENTRY. Caller frees it when the draw releases.
	var p := CPUParticles2D.new()
	p.amount = 14
	p.lifetime = 0.45
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 26.0
	p.radial_accel_min = -260.0
	p.radial_accel_max = -180.0
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 8.0
	p.gravity = Vector2.ZERO
	p.scale_amount_min = 1.0
	p.scale_amount_max = 2.0
	p.color = Color("35c6f4")
	parent.add_child(p)
	return p


func hitstop(frames := 3) -> void:
	Engine.time_scale = 0.05
	await get_tree().create_timer(frames / 60.0, true, false, true).timeout
	Engine.time_scale = 1.0


func shake(amount := 2.0) -> void:
	var cam := get_viewport().get_camera_2d()
	if cam == null:
		return
	var t := create_tween()
	for i in 4:
		t.tween_property(cam, "offset",
			Vector2(randf_range(-amount, amount), randf_range(-amount, amount)), 0.02)
	t.tween_property(cam, "offset", Vector2.ZERO, 0.02)


func burst(pos: Vector2, color: Color) -> void:
	var p := CPUParticles2D.new()
	p.one_shot = true
	p.emitting = true
	p.amount = 12
	p.lifetime = 0.35
	p.explosiveness = 1.0
	p.spread = 180.0
	p.initial_velocity_min = 60.0
	p.initial_velocity_max = 140.0
	p.gravity = Vector2(0, 400)
	p.color = color
	p.position = pos
	get_tree().current_scene.add_child(p)
	get_tree().create_timer(1.0).timeout.connect(p.queue_free)


func ghost(src: AnimatedSprite2D) -> void:
	# dash afterimage: frozen copy of the current frame, cyan, fading fast
	var g := Sprite2D.new()
	g.texture = src.sprite_frames.get_frame_texture(src.animation, src.frame)
	g.flip_h = src.flip_h
	g.global_position = src.global_position
	g.rotation = src.global_rotation
	g.modulate = Color(0.21, 0.78, 0.96, 0.45)  # CYAN, half-faded
	get_tree().current_scene.add_child(g)
	var t := create_tween()
	t.tween_property(g, "modulate:a", 0.0, 0.18)
	t.tween_callback(g.queue_free)


func slash(pos: Vector2, angle_deg: float, flip: bool) -> void:
	# Blade cut arc — the real slash_light sprite strip, 3f @ 24fps
	play_strip(pos, "res://art/effects/slash_light.png", 3, 24.0,
		deg_to_rad(angle_deg), flip)
