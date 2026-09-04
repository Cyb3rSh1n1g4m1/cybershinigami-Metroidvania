class_name InteractPrompt
extends Node2D
## Floating "this responds to you" hint: an upward chevron over a key name, fading
## in when the reaper gets close. Add it as a child of the interactable and place
## it — it finds the player and measures from its host on its own, so wiring a new
## interactable is three lines and no signals.
##
##   var prompt := InteractPrompt.new("UP")
##   prompt.position = Vector2(0, -62)
##   add_child(prompt)

const ACID := Color("c6f02a")
const FADE_SECS := 0.18
const BOB_PX := 2.0

var key := "UP"
var radius := 44.0

var _host: Node2D
var _label: Label
var _tween: Tween
var _near := false
var _t := 0.0
var _base_y := 0.0


func _init(key_name := "UP", near_radius := 44.0) -> void:
	key = key_name
	radius = near_radius


func _ready() -> void:
	# Hosts sit where they need to sit — the shrine is at z -5 so it does not hide
	# the player mid-prayer. The hint is a read-out, not scenery: it goes on top.
	z_as_relative = false
	z_index = 20
	modulate.a = 0.0
	_base_y = position.y
	_host = get_parent() as Node2D  # measure from the thing, not from the hint

	_label = Label.new()
	_label.text = key
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label.add_theme_font_size_override("font_size", 8)
	_label.add_theme_color_override("font_color", ACID)
	add_child(_label)
	_label.size = Vector2(40, 10)
	_label.position = Vector2(-20, 0)  # whole pixels, centred on the host


func _draw() -> void:
	# Chevron, drawn once and never redrawn — the fade rides on modulate.
	draw_polyline(PackedVector2Array([
		Vector2(-4, -1), Vector2(0, -5), Vector2(4, -1),
	]), ACID, 1.0)


func _process(delta: float) -> void:
	var p := get_tree().get_first_node_in_group("player") as Node2D
	var from := _host.global_position if _host != null else global_position
	var near := p != null and from.distance_to(p.global_position) < radius
	if near != _near:
		_near = near
		if _tween != null and _tween.is_valid():
			_tween.kill()
		_tween = create_tween()
		_tween.tween_property(self, "modulate:a", 1.0 if near else 0.0, FADE_SECS)
	if not _near and modulate.a <= 0.0:
		return
	_t += delta
	# Whole-pixel bob: a fractional y would smear the glyphs across the 3x upscale.
	position.y = _base_y + roundf(sin(_t * 3.0) * BOB_PX)
