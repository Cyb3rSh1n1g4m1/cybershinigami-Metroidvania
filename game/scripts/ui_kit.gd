extends CanvasLayer
## Autoload "UI" — the shared machine look every screen borrows from.
## Owns ONE very-high CanvasLayer holding three full-screen overlays (scanlines,
## edge flash, fade) so any scene can transition or flinch without building its own.
## Adds nothing to any other scene; every overlay is invisible until asked for.
##
##   await UI.fade_out(0.4).finished   # black out, then swap scenes
##   UI.scanlines(true)                # CRT grille on
##   await UI.typewriter($Line, "ssh perimeter@0x0029", 24.0).finished
##   panel.add_theme_stylebox_override("panel", UI.terminal_panel())

const ACID := Color("c6f02a")    # UI accent
const SPIRIT := Color("35c6f4")  # data / soul
const DANGER := Color("e01f26")  # damage
const INK := Color("0a0e1f")     # panel fill

const FLASH_SECS := 0.15
const FLASH_ALPHA := 0.30  # low enough to read the fight through it

var _fade: ColorRect
var _scan: TextureRect
var _edge: TextureRect
var _fade_tween: Tween
var _edge_tween: Tween
var _souls_seen := 0


func _ready() -> void:
	layer = 128                              # above HUD, pause menu and title alike
	process_mode = Node.PROCESS_MODE_ALWAYS  # a fade must survive get_tree().paused

	# added in draw order: grille, then flash, then fade on top — a fade to black
	# is supposed to swallow everything, including the overlays.
	_scan = TextureRect.new()
	_scan.texture = _scanline_texture()
	_scan.stretch_mode = TextureRect.STRETCH_TILE
	_scan.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	_scan.visible = false
	_add_overlay(_scan)

	_edge = TextureRect.new()
	_edge.texture = _vignette_texture()
	# The one place nearest filtering is wrong: a two-stop gradient blown up to
	# 640px bands into visible rings. Linear keeps the falloff invisible, and it
	# costs nothing because the texture never animates — only its modulate does.
	_edge.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	_edge.modulate = Color(1, 1, 1, 0)
	_add_overlay(_edge)

	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_add_overlay(_fade)

	# Soul pickups already announce themselves through Game, so listening here
	# means soul.gd needs no edit and every future soul source flashes for free.
	Game.souls_changed.connect(_on_souls_changed)


func _add_overlay(c: Control) -> void:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE  # overlays never eat a click
	add_child(c)


# -- fades ---------------------------------------------------------------------

func fade_out(secs := 0.35) -> Tween:
	## To black. Await the returned tween's `finished` before swapping scenes.
	return _fade_to(1.0, secs)


func fade_in(secs := 0.35) -> Tween:
	## Back to the game.
	return _fade_to(0.0, secs)


func _fade_to(alpha: float, secs: float) -> Tween:
	if _fade_tween != null and _fade_tween.is_valid():
		_fade_tween.kill()  # a fade_in mid-fade_out must win, not average
	_fade_tween = create_tween()
	_fade_tween.tween_property(_fade, "color:a", alpha, maxf(secs, 0.01))
	return _fade_tween


# -- CRT grille ----------------------------------------------------------------

func scanlines(on: bool) -> void:
	## Off by default: it is a look screens opt into, not a tax on gameplay.
	_scan.visible = on


func _scanline_texture() -> ImageTexture:
	# 1x3 tile: two clear rows, one dark. Tiled over 360p that is a 120-line
	# grille, drawn once as a single quad — no shader, no per-frame cost.
	var img := Image.create_empty(1, 3, false, Image.FORMAT_RGBA8)
	img.set_pixel(0, 2, Color(0, 0, 0, 0.16))
	return ImageTexture.create_from_image(img)


# -- screen-space hit feedback -------------------------------------------------

func edge_flash(tint: Color) -> void:
	## A brief coloured bloom around the frame edge — red when the reaper is cut,
	## cyan when a soul lands. Clear through the middle, so nothing is hidden.
	if _edge_tween != null and _edge_tween.is_valid():
		_edge_tween.kill()
	_edge.modulate = Color(tint.r, tint.g, tint.b, 0.0)
	_edge_tween = create_tween()
	_edge_tween.tween_property(_edge, "modulate:a", FLASH_ALPHA, FLASH_SECS * 0.3)
	_edge_tween.tween_property(_edge, "modulate:a", 0.0, FLASH_SECS * 0.7)


func _on_souls_changed(total: int) -> void:
	if total > _souls_seen:  # spending souls must not read as picking one up
		edge_flash(SPIRIT)
	_souls_seen = total


func _vignette_texture() -> GradientTexture2D:
	var g := Gradient.new()
	g.set_offset(0, 0.45)  # the middle 45% stays fully clear
	g.set_color(0, Color(1, 1, 1, 0))
	g.set_offset(1, 1.0)
	g.set_color(1, Color(1, 1, 1, 1))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = 64
	t.height = 64
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t


# -- terminal dressing ---------------------------------------------------------

func typewriter(label: Label, text: String, cps := 30.0) -> Tween:
	## Reveals `text` one character at a time. Bound to the label, so it dies with
	## it. Await the returned tween's `finished` to chain lines.
	label.text = text
	label.visible_ratio = 0.0
	var secs := maxf(float(text.length()) / maxf(cps, 1.0), 0.01)
	var t := label.create_tween()
	t.tween_property(label, "visible_ratio", 1.0, secs)
	return t


func terminal_panel(pad := 6.0) -> StyleBoxFlat:
	## The one panel every screen wears: near-black fill, hairline acid border.
	## Size is not a parameter because a StyleBox has none — it stretches to whatever
	## Control wears it. `pad` is the inner content margin, the only sizing a
	## StyleBoxFlat actually owns.
	var box := StyleBoxFlat.new()
	box.bg_color = Color(INK.r, INK.g, INK.b, 0.92)
	box.set_border_width_all(1)
	box.border_color = Color(ACID.r, ACID.g, ACID.b, 0.55)
	box.set_corner_radius_all(0)  # CRT bezels are square; radii just blur at 360p
	box.set_content_margin_all(pad)
	# ponytail: StyleBoxFlat has no inner-shadow property, so the inset is faked
	# with a tight black halo hugging the border — at 640x360 it reads the same.
	# Ceiling: a true bevel needs a nested Panel or a shader; neither earns its keep.
	box.shadow_color = Color(0, 0, 0, 0.55)
	box.shadow_size = 2
	box.shadow_offset = Vector2.ZERO
	return box
