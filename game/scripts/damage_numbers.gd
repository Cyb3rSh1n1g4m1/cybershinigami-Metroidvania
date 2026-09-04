class_name DamageNumbers
extends RefCounted
## Floating combat feedback: a number pops off the hit point, arcs up and fades.
## Acid green for a hit that lands, white and larger for the one that kills.
##
## Static only — no autoload, no scene, no node to place. EnemyBase.take_hit()
## calls it in one line and nothing else in the enemy tree has to know it exists.

const HIT_COLOR := Color("c6f02a")
const KILL_COLOR := Color("ffffff")
const HIT_SIZE := 8   # 12px is LARGE at 640x360 — a routine hit stays smaller
const KILL_SIZE := 12

const BOX_W := 40.0   # fixed box + centre alignment == the number sits on the hit
const LIFE := 0.6


static func pop(pos: Vector2, amount: int, killing := false) -> void:
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null or tree.current_scene == null:
		return  # headless import / teardown: no scene to float over

	var l := Label.new()
	l.text = str(amount)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.z_index = 50  # over the room, the enemy and the player
	l.add_theme_font_size_override("font_size", KILL_SIZE if killing else HIT_SIZE)
	l.add_theme_color_override("font_color", KILL_COLOR if killing else HIT_COLOR)
	# Parented to the scene, not the enemy: a killing blow frees the enemy on the
	# same frame and the number has to outlive it.
	tree.current_scene.add_child(l)
	l.size = Vector2(BOX_W, float(KILL_SIZE))
	var start := (pos - Vector2(BOX_W * 0.5, 8.0)).round()
	l.position = start

	var drift := randf_range(-5.0, 5.0)  # so a mashed combo does not stack one column
	var rise := 18.0 if killing else 13.0
	var t := l.create_tween()
	t.set_parallel(true)
	# One sine hump: up fast, ease over, settle slightly. Every frame is rounded —
	# sub-pixel text smears across the 3x upscale, and pixel steps suit the art.
	t.tween_method(func(k: float) -> void:
			l.position = (start + Vector2(drift * k, -rise * sin(k * PI * 0.85))).round(),
		0.0, 1.0, LIFE)
	t.tween_property(l, "modulate:a", 0.0, LIFE * 0.5).set_delay(LIFE * 0.5)
	t.tween_callback(l.queue_free).set_delay(LIFE)
