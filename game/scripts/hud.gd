extends CanvasLayer
## HUD (M5) — INTEGRITY pips, SOUL BYTES, toast line, ability row.
## Built in code like the rest of the room. Sized for the 640x360 viewport: every
## offset is a whole pixel and nothing is scaled, so it stays pixel-crisp at x3.

const MARGIN := 6.0

const PIP_W := 8.0
const PIP_H := 10.0
const PIP_PITCH := 10.0
const PIP_MAX := 10          # DESIGN.md §3.1 ceiling — the row is laid out for it
const DRAIN := 0.45          # a lost pip flashes white, then its fill falls away
const FLASH_CUT := 0.62      # fx above this is still the white flash

const CYAN := Color("35c6f4")
const ACID := Color("c6f02a")
const RED := Color("e01f26")
const SHELL := Color("0a0e1f")
const EDGE := Color("4a5568")

# One terminal glyph per module id. Keys are the ids Game.grant actually
# receives — upgrade_module.gd's CATALOG keys, NOT the flavor names those
# modules display (dash is granted as "dash" but shown as "PING SWEEP"; keying
# on flavor names left every chip a "?"). Unknown ids still get "?".
const ABILITY_GLYPH := {
	"dash": ">",
	"double_jump": "^",
	"ranged": "*",
	"tunnel": "~",
	"integrity": "+",
	"souls": "$",
	"heavy": "!",
	"charge": "»",
	"slam": "v",
}

# screen-edge damage flash. e01f26 in linear-ish float, alpha driven by `amt`.
const VIGNETTE := """
shader_type canvas_item;
uniform float amt = 0.0;
void fragment() {
	vec2 d = abs(UV - vec2(0.5)) * 2.0;
	float e = max(d.x, d.y);
	COLOR = vec4(0.878, 0.122, 0.149, smoothstep(0.45, 1.0, e) * amt);
}
"""

var _cur := 5
var _max := 5
var _fx := PackedFloat32Array()   # per-pip damage effect, 1.0 -> 0.0
var _pulse := 0.0
var _shown := 0.0                 # soul counter's animated value

var _pips: Control
var _souls: Label
var _toast: Label
var _abilities: HBoxContainer
var _vig: ShaderMaterial
var _souls_tween: Tween
var _toast_tween: Tween
var _vig_tween: Tween


func _ready() -> void:
	layer = 10                                   # above every gameplay layer
	_fx.resize(PIP_MAX)

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	# damage vignette first so it sits behind the readouts
	var shader := Shader.new()
	shader.code = VIGNETTE
	_vig = ShaderMaterial.new()
	_vig.shader = shader
	var glass := ColorRect.new()
	glass.material = _vig
	glass.set_anchors_preset(Control.PRESET_FULL_RECT)
	glass.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(glass)

	var tag := _label(8, EDGE)
	tag.text = "INTEGRITY"
	_place(tag, 0.0, 0.0, Rect2(MARGIN, MARGIN - 3.0, 90.0, 11.0))
	root.add_child(tag)

	_pips = Control.new()
	_place(_pips, 0.0, 0.0, Rect2(MARGIN, MARGIN + 9.0, PIP_MAX * PIP_PITCH, PIP_H))
	_pips.draw.connect(_draw_pips)
	root.add_child(_pips)

	# ponytail: 魂 needs a CJK face and Godot's built-in font has none, so it draws
	# as a notdef box. Ceiling: one .ttf in the project and a default_font override.
	_souls = _label(10, ACID)
	_souls.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_place(_souls, 1.0, 0.0, Rect2(-126.0 - MARGIN, MARGIN - 4.0, 126.0, 14.0))
	root.add_child(_souls)

	_abilities = HBoxContainer.new()
	_abilities.alignment = BoxContainer.ALIGNMENT_END
	_abilities.add_theme_constant_override("separation", 3)
	_place(_abilities, 1.0, 0.0, Rect2(-166.0 - MARGIN, MARGIN + 12.0, 166.0, 11.0))
	root.add_child(_abilities)

	_toast = _label(8, CYAN)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.modulate.a = 0.0
	_place(_toast, 0.5, 1.0, Rect2(-160.0, -28.0, 320.0, 12.0))
	root.add_child(_toast)

	# Method callables, not lambdas: Game outlives the room, and Godot drops every
	# connection whose target object is freed — so this HUD needs no _exit_tree
	# teardown. (The placeholder HUD greybox.gd used to build connected capture
	# lambdas here, which is the pattern that leaves a connection behind.)
	Game.souls_changed.connect(_on_souls)
	Game.toast.connect(_on_toast)
	Game.ability_gained.connect(_on_ability)
	_shown = float(Game.soul_bytes)
	_set_souls(_shown)
	for id in Game.abilities:
		_add_ability(str(id), false)

	# The player's _ready runs before the room builds this HUD, so read the opening
	# values directly — waiting on integrity_changed would miss the first emit.
	var p := get_tree().get_first_node_in_group("player") as Player
	if p != null:
		_max = p.max_integrity
		_cur = p.integrity
		p.integrity_changed.connect(_on_integrity)
		p.died.connect(_on_died)
	_pips.queue_redraw()


func _process(delta: float) -> void:
	_pulse += delta
	var live := _cur == 1                        # last pip pulses, so keep redrawing
	for i in _fx.size():
		if _fx[i] > 0.0:
			_fx[i] = maxf(_fx[i] - delta / DRAIN, 0.0)
			live = true
	if live:
		_pips.queue_redraw()


# -- integrity ---------------------------------------------------------------

func _draw_pips() -> void:
	for i in mini(_max, PIP_MAX):
		var x := i * PIP_PITCH
		var ring := _block(x, 0.0, PIP_W, PIP_H)
		_pips.draw_colored_polygon(ring, SHELL)
		ring.append(ring[0])                     # close the outline
		_pips.draw_polyline(ring, EDGE, 1.0)
		if i < _cur:
			var col := CYAN
			if _cur == 1 and i == 0:
				col = CYAN.lerp(RED, 0.5 + 0.5 * sin(_pulse * 9.0))
			_pips.draw_colored_polygon(
				_block(x + 1.0, 1.0, PIP_W - 2.0, PIP_H - 2.0), col)
		elif _fx[i] > FLASH_CUT:
			_pips.draw_colored_polygon(
				_block(x + 1.0, 1.0, PIP_W - 2.0, PIP_H - 2.0), Color.WHITE)
		elif _fx[i] > 0.0:
			# fill level falls out of the block, whole pixels only
			var h := maxf(floorf((PIP_H - 2.0) * _fx[i] / FLASH_CUT), 1.0)
			_pips.draw_rect(Rect2(x + 1.0, PIP_H - 1.0 - h, PIP_W - 2.0, h), CYAN)


func _block(x: float, y: float, w: float, h: float) -> PackedVector2Array:
	# angular segment: top-left and bottom-right corners cut back 2px
	return PackedVector2Array([
		Vector2(x + 2.0, y),
		Vector2(x + w, y),
		Vector2(x + w, y + h - 2.0),
		Vector2(x + w - 2.0, y + h),
		Vector2(x, y + h),
		Vector2(x, y + 2.0),
	])


func _on_integrity(cur: int, max_cur: int) -> void:
	_max = max_cur
	if cur < _cur:
		for i in range(maxi(cur, 0), mini(_cur, PIP_MAX)):
			_fx[i] = 1.0
		_flash(0.5, 0.4)
	_cur = cur
	_pips.queue_redraw()


func _on_died() -> void:
	_flash(0.9, 1.5)


func _flash(peak: float, secs: float) -> void:
	if _vig_tween != null and _vig_tween.is_valid():
		_vig_tween.kill()
	_vig.set_shader_parameter("amt", peak)
	_vig_tween = create_tween()
	_vig_tween.tween_property(_vig, "shader_parameter/amt", 0.0, secs)


# -- souls, toast, abilities -------------------------------------------------

func _on_souls(total: int) -> void:
	if _souls_tween != null and _souls_tween.is_valid():
		_souls_tween.kill()
	_souls_tween = create_tween()
	_souls_tween.tween_method(_set_souls, _shown, float(total), 0.4)
	_souls.modulate = Color(1.8, 1.8, 1.8)       # blown out, settles back to acid
	create_tween().tween_property(_souls, "modulate", Color.WHITE, 0.25)


func _set_souls(v: float) -> void:
	_shown = v
	_souls.text = "魂 %d" % roundi(v)


func _on_toast(msg: String) -> void:
	if _toast_tween != null and _toast_tween.is_valid():
		_toast_tween.kill()
	_toast.text = msg
	_toast.modulate.a = 0.0
	_toast_tween = create_tween()
	_toast_tween.tween_property(_toast, "modulate:a", 1.0, 0.14)
	_toast_tween.tween_interval(1.7)
	_toast_tween.tween_property(_toast, "modulate:a", 0.0, 0.5)


func _on_ability(id: String) -> void:
	_add_ability(id, true)


func _add_ability(id: String, flash: bool) -> void:
	var glyph := "?"
	if ABILITY_GLYPH.has(id):
		glyph = str(ABILITY_GLYPH[id])
	var box := StyleBoxFlat.new()
	box.bg_color = ACID
	var chip := _label(8, Color.BLACK)
	chip.text = glyph
	chip.custom_minimum_size = Vector2(11.0, 11.0)
	chip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	chip.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	chip.add_theme_stylebox_override("normal", box)
	_abilities.add_child(chip)
	if flash:
		chip.modulate = Color(3.0, 3.0, 3.0)
		create_tween().tween_property(chip, "modulate", Color.WHITE, 0.5)


# -- layout ------------------------------------------------------------------

func _label(size: int, col: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	return l


func _place(c: Control, ax: float, ay: float, r: Rect2) -> void:
	## One anchor corner plus a whole-pixel rect measured from it. Keeps the HUD
	## in the corners if the viewport ever changes without touching any number here.
	c.anchor_left = ax
	c.anchor_right = ax
	c.anchor_top = ay
	c.anchor_bottom = ay
	c.offset_left = r.position.x
	c.offset_top = r.position.y
	c.offset_right = r.position.x + r.size.x
	c.offset_bottom = r.position.y + r.size.y
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
