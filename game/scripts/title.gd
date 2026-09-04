extends Control
## Title screen — the game's entry point (project.godot run/main_scene).
##
## The composition is built in code rather than authored in title.tscn: the
## wordmark font has to be assembled at runtime from ThemeDB.fallback_font (no
## font file ships yet) and the backdrop is procedural, so a hand-authored tree
## would only ever hold half the screen and the two halves would drift.

const GAME_SCENE := "res://scenes/rooms/greybox.tscn"
const TITLE_ART := "res://art/ui/title_art.png"
# the persona's own hannya sigil, drawn in ASCII (Hackerverse assets)
const ASCII_MASK := "res://art/ui/mask_ascii.txt"
# the full-colour persona logo — the title screen's hero
const LOGO := "res://art/ui/logo.png"
const WORDMARK := "CYB3R$H1N1G4M1"
const SUBTITLE := "hv 0x0029 — a death god descends the stack"
const HINT := "[w/s | stick] select    [space | A] exec"

const ACID := Color("c6f02a")
const CYAN := Color("35c6f4")
const PALE := Color("8fe8ff")
const RED := Color("e01f26")
const SLATE := Color("4a5568")
# Cyberpunk 2077 / Edgerunners signature yellow. The wordmark was acid green, the
# same hue as the logo's 死神 mark, so the two blended into one another. Yellow is
# the one hue absent from the logo (blue mane, red mask, green kanji), so it reads
# as a separate object at a glance.
const CP_YELLOW := Color("fcee0a")
# The fringe colours are pulled from the CHARACTER, not from a generic cyberpunk
# swatch: cyan is his hair tip, red is his mask. Yellow leads because it is the one
# hue he does not wear, so it separates from him while the fringe ties back to him.
const CP_CYAN := Color("35c6f4")     # ponytail tip
const CP_MAGENTA := Color("e01f26")  # hannya mask

# 640x360 layout. Every number is an integer on purpose: the project scales the
# viewport by whole numbers, and a half-pixel here is a smeared row on a 1080p screen.
# The type lives in a RIGHT COLUMN so the mask can keep the left half at full
# height. Full-width centred type ran straight across the mane and was unreadable.
const COL_X := 254
const PLATE := Rect2(248, 34, 384, 104)
const KANJI_Y := 40
const TITLE_Y := 62
const SUB_Y := 116
const RULE_Y := 146
const PANEL := Rect2(248, 158, 384, 104)
const CARET_X := 262
const MENU_X := 280
const MENU_Y0 := 174
const MENU_STEP := 26
const HINT_Y := 338
# the ASCII sigil sits centre-left, behind the type, filling the dead space the
# menu panel (x 248+) leaves open on that side
const ASCII_POS := Vector2i(22, 106)
# logo sits left of the menu panel (x 248+), vertically centred in 360
const LOGO_POS := Vector2i(14, 44)

const ITEM_TEXT: Array[String] = ["START", "CONTINUE", "QUIT"]
const IDX_START := 0
const IDX_CONTINUE := 1
const IDX_QUIT := 2

# ponytail: no save system exists, so CONTINUE is permanently dimmed and skipped
# by the cursor. Ceiling: when saves land this becomes one FileAccess.file_exists.
const HAS_SAVE := false

var _sel := IDX_START
var _locked := false
var _t := 0.0
var _labels: Array[Label] = []
var _glow: Array[Label] = []
var _ghosts: Array[Node2D] = []
var _ascii: Label
var _logo: TextureRect
var _wordmark: CanvasItem   # the sheared yellow wordmark layer; _animate flickers it
var _caret: Label


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_background()
	var chrome := Chrome.new()
	chrome.rule_y = RULE_Y
	chrome.panel = PANEL
	add_child(chrome)
	_build_wordmark()
	_build_menu()
	add_child(Scanlines.new())   # last child, so the CRT sits over the type too
	_refresh()
	Audio.music("title")   # silent until audio/music/title.* exists (§14b.5)


func _process(delta: float) -> void:
	_t += delta
	_animate()
	if _locked:
		return
	# Polled, not _unhandled_input: a joypad axis fires a motion event on every
	# tick it is held, which walks the cursor down the menu at 60 items/sec.
	# is_action_just_pressed is edge-triggered for sticks and keys alike.
	if Input.is_action_just_pressed("aim_up"):
		_move(-1)
	elif Input.is_action_just_pressed("aim_down"):
		_move(1)
	elif Input.is_action_just_pressed("jump") or Input.is_action_just_pressed("attack"):
		_confirm()


# -- menu -------------------------------------------------------------------

func _enabled(i: int) -> bool:
	return i != IDX_CONTINUE or HAS_SAVE


func _move(step: int) -> void:
	var n := ITEM_TEXT.size()
	var i := _sel
	for _pass in n:                     # skip over disabled rows, wrap at the ends
		i = wrapi(i + step, 0, n)
		if _enabled(i):
			break
	if i == _sel:
		return
	_sel = i
	_refresh()
	_play_ui_sound("move")


func _confirm() -> void:
	if not _enabled(_sel):
		return
	_play_ui_sound("confirm")
	match _sel:
		IDX_START:
			_locked = true
			# START means a fresh run: pause.gd defers this wipe to the title
			# screen, and without it quit-to-title leaked the previous run's
			# abilities and soul bytes into the "new" game
			Game.reset_run()
			Transition.go(GAME_SCENE)
		IDX_QUIT:
			_locked = true
			Transition.quit_game()


func _play_ui_sound(id: String) -> void:
	# the one place the title makes noise; ids arrive as "move" / "confirm"
	Audio.play("menu_" + id)


func _refresh() -> void:
	for i in _labels.size():
		var l := _labels[i]
		var col := Color(PALE, 0.55)
		if not _enabled(i):
			col = Color(SLATE, 0.85)
		elif i == _sel:
			col = ACID
		l.add_theme_color_override("font_color", col)
		# nudge, not scale: a fractional scale on text is a blurred row, and there
		# is no integer scale small enough to read as a hover
		l.position.x = MENU_X + (3 if i == _sel else 0)


func _animate() -> void:
	# the sign breathes, and now and then it browns out for a frame
	# the mis-registration jitters by a pixel now and then, like a bad signal
	var jitter := 1.0 if fposmod(_t, 2.9) < 0.08 else 0.0
	for i in _ghosts.size():
		var g := _ghosts[i]
		g.modulate.a = 0.66 + 0.10 * sin(_t * 1.9 + i)
		var side := -1.0 if i == 0 else 1.0
		g.position.x = COL_X + side * 3.0 + SHEAR * 38.0 + jitter * side * 2.0
	if _wordmark != null:
		_wordmark.modulate.a = 0.55 if fposmod(_t, 4.3) < 0.05 else 1.0
	if _ascii != null:
		# the sigil breathes out of phase with the wordmark and drops out briefly,
		# so the screen reads as a terminal that is only just holding the signal
		var a := 0.10 + 0.05 * sin(_t * 1.3)
		_ascii.modulate.a = 0.03 if fposmod(_t, 6.7) < 0.07 else a
	if _logo != null:
		# the logo pulses faintly and drops a frame now and then, same failing-CRT
		# language as the wordmark but slower, so they never blink together
		_logo.modulate.a = 0.62 if fposmod(_t, 5.9) < 0.06 else 0.90 + 0.06 * sin(_t * 1.7)
	_caret.visible = _enabled(_sel)
	_caret.position = Vector2(CARET_X + (1 if sin(_t * 5.0) > 0.0 else 0),
		MENU_Y0 + _sel * MENU_STEP)
	_caret.modulate.a = 0.45 + 0.55 * absf(sin(_t * 3.4))


# -- composition ------------------------------------------------------------

func _build_background() -> void:
	if ResourceLoader.exists(TITLE_ART):
		var art := TextureRect.new()
		art.texture = load(TITLE_ART)
		art.set_anchors_preset(Control.PRESET_FULL_RECT)
		art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		art.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(art)
	else:
		add_child(Backdrop.new())
	add_child(MatrixRain.new())   # over the art, under the sigil and the type
	_build_logo()


func _build_logo() -> void:
	## The hero is the persona's OWN logo art — the full-colour hannya with the
	## blue mane, red horns and 死神 mark. It supersedes the ASCII sigil as the
	## centrepiece; the ASCII now rides at very low alpha as texture behind it, so
	## both of the persona's marks are present without competing.
	if ResourceLoader.exists(LOGO):
		var tex: Texture2D = load(LOGO)
		var logo := TextureRect.new()
		logo.texture = tex
		logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
		logo.size = Vector2(tex.get_width(), tex.get_height())
		# centre-right of the sigil, left of the menu panel, vertically centred
		logo.position = Vector2(LOGO_POS)
		logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
		logo.modulate = Color(1, 1, 1, 0.92)
		add_child(logo)
		_logo = logo
	_build_ascii_mask()


func _build_ascii_mask() -> void:
	## The ASCII hannya from the Hackerverse assets, kept as a faint texture layer
	## behind the logo — a terminal rendering of the same face the logo shows.
	if not ResourceLoader.exists(ASCII_MASK):
		return
	var txt := FileAccess.get_file_as_string(ASCII_MASK)
	if txt.is_empty():
		return

	var mask := Label.new()
	mask.text = txt
	mask.add_theme_font_size_override("font_size", 5)
	mask.add_theme_constant_override("line_spacing", -1)  # ASCII wants tight rows
	mask.autowrap_mode = TextServer.AUTOWRAP_OFF
	mask.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	# Sits BEHIND the wordmark and menu because _build_background runs first —
	# a watermark the type reads over, not a competing element.
	mask.set_anchors_preset(Control.PRESET_TOP_LEFT)
	mask.position = Vector2(ASCII_POS)
	mask.size = Vector2(340, 220)
	mask.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mask.modulate = Color(ACID, 0.13)
	add_child(mask)
	_ascii = mask

	# a dim red copy 1px behind gives the glyphs an oni undertone without a shader
	var under := Label.new()
	under.text = txt
	under.add_theme_font_size_override("font_size", 5)
	under.add_theme_constant_override("line_spacing", -1)
	under.autowrap_mode = TextServer.AUTOWRAP_OFF
	under.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	under.set_anchors_preset(Control.PRESET_TOP_LEFT)
	under.position = mask.position + Vector2(1, 1)
	under.size = mask.size
	under.mouse_filter = Control.MOUSE_FILTER_IGNORE
	under.modulate = Color(RED, 0.09)
	add_child(under)
	move_child(under, mask.get_index())


func _build_wordmark() -> void:
	add_child(Plate.new(PLATE))

	var kanji := _kanji_font()
	if kanji != null:
		_col_line("死神", KANJI_Y, 15, RED, 6, kanji)
	else:
		# ponytail: no CJK face resolved on this machine. Romaji stands in rather
		# than a row of tofu. Ceiling: bundle a font and delete this branch.
		_col_line("SHINIGAMI", KANJI_Y + 2, 10, RED, 8)

	# The wordmark is SHEARED, not just italicised: a hard slant on a heavy
	# condensed face is what gives the reference type its slashing, cut-with-a-blade
	# character. Godot Controls have no skew, so each layer rides inside a Node2D
	# carrying a shear Transform2D.
	var tech := _tech_font(2)
	_shear_line(WORDMARK, TITLE_Y + 2, 30, Color(0, 0, 0, 0.9), tech, 3.0)     # shadow
	var gc := _shear_line(WORDMARK, TITLE_Y, 30, Color(CP_CYAN, 0.8), tech, -3.0)
	var gm := _shear_line(WORDMARK, TITLE_Y, 30, Color(CP_MAGENTA, 0.75), tech, 3.0)
	_ghosts.append(gc)
	_ghosts.append(gm)
	# the flicker must drive the VISIBLE yellow layer — it used to point at an
	# invisible empty label, so the brown-out never showed
	_wordmark = _shear_line(WORDMARK, TITLE_Y, 30, CP_YELLOW, tech, 0.0)

	_col_line(SUBTITLE, SUB_Y, 10, CP_CYAN, 1, _tech_font(1, 500))
	_line(HINT, HINT_Y, 8, SLATE, 2, _tech_font(2, 500))


func _col_line(text: String, y: int, size: int, col: Color, spacing := 0,
		font: Font = null) -> Label:
	## Same as _line but confined to the right column, so nothing can stray back
	## over the mask.
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	l.position = Vector2(COL_X, y)
	l.size = Vector2(PLATE.size.x - 12, size + 10)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_font_override("font", font if font != null else _ui_font(spacing))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	add_child(l)
	return l


const SHEAR := 0.20   # ~11 degrees: aggressive without becoming unreadable


func _shear_line(text: String, y: int, size: int, col: Color, font: Font,
		dx: float) -> Node2D:
	var holder := Node2D.new()
	# y_axis tilted left means upper rows sit further right than lower ones — an
	# italic slant applied geometrically rather than by picking an oblique face
	holder.transform = Transform2D(Vector2(1, 0), Vector2(-SHEAR, 1),
		Vector2(COL_X + dx + SHEAR * (size + 8), y))
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	l.size = Vector2(PLATE.size.x + 40, size + 10)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	holder.add_child(l)
	add_child(holder)
	return holder


class Plate extends Control:
	## The title's ground: a near-black bar with a yellow hairline top and bottom
	## and a couple of tick marks, so it reads as a HUD element rather than a box.
	var rect: Rect2

	func _init(r := Rect2()) -> void:
		rect = r
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		draw_rect(rect, Color(0.02, 0.03, 0.06, 0.82), true)
		# hairlines span the PLATE's x-range, not [0, size.x] — the old code
		# started at the screen's left edge, slashing a yellow line across the
		# hannya logo and stopping mid-screen short of the plate itself
		var x0 := rect.position.x
		var x1 := rect.position.x + rect.size.x
		var y0 := rect.position.y
		var y1 := rect.position.y + rect.size.y
		draw_line(Vector2(x0, y0), Vector2(x1, y0), Color("fcee0a", 0.55), 1.0)
		draw_line(Vector2(x0, y1), Vector2(x1, y1), Color("fcee0a", 0.35), 1.0)
		# no corner ticks: the CP2077 bracket motif read as four stray cyan
		# dashes floating around the title rather than as brackets


func _build_menu() -> void:
	for i in ITEM_TEXT.size():
		var l := Label.new()
		l.text = ITEM_TEXT[i]
		l.position = Vector2(MENU_X, MENU_Y0 + i * MENU_STEP)
		l.size = Vector2(120, 20)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		l.add_theme_font_override("font", _ui_font(1))
		l.add_theme_font_size_override("font_size", 14)
		add_child(l)
		_labels.append(l)
	_caret = Label.new()
	_caret.text = ">"
	_caret.size = Vector2(16, 20)
	_caret.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_caret.add_theme_font_override("font", _ui_font(0))
	_caret.add_theme_font_size_override("font_size", 14)
	_caret.add_theme_color_override("font_color", ACID)
	add_child(_caret)


func _line(text: String, y: int, size: int, col: Color, spacing := 0,
		font: Font = null) -> Label:
	# full-width and centre-aligned, so horizontal placement is the engine's job
	# and never a magic x that drifts when the text changes
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.position = Vector2(0, y)
	l.size = Vector2(640, size + 10)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_font_override("font", font if font != null else _ui_font(spacing))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	add_child(l)
	return l


func _ui_font(spacing: int) -> FontVariation:
	# no font file ships yet, so the engine default carries the whole screen on
	# size, tracking and colour alone
	var fv := FontVariation.new()
	fv.base_font = ThemeDB.fallback_font
	fv.spacing_glyph = spacing
	return fv


func _tech_font(spacing: int, weight := 700) -> Font:
	## Bahnschrift is Windows' DIN 1451 cut — an industrial signage face, which is
	## the same lineage Cyberpunk 2077 draws its UI type from. Franklin Gothic and
	## Impact stand in on machines without it.
	## ponytail: loaded from the OS, not bundled. Ceiling: ship a licensed face
	## before release — a system font cannot be redistributed with the game.
	var sf := SystemFont.new()
	sf.font_names = PackedStringArray(["Bahnschrift", "Bahnschrift SemiCondensed",
		"DIN", "Franklin Gothic Medium", "Impact", "Segoe UI Black", "Arial Black"])
	sf.allow_system_fallback = true
	var fv := FontVariation.new()
	fv.base_font = sf
	fv.spacing_glyph = spacing
	fv.variation_opentype = {"wght": weight}
	return fv


func _kanji_font() -> Font:
	# 死神 is not in the engine's default face — it has to come from the OS
	var sf := SystemFont.new()
	sf.font_names = PackedStringArray(["Yu Gothic UI", "Meiryo", "MS Gothic",
		"Yu Mincho", "Microsoft YaHei", "Noto Sans CJK JP", "Noto Sans JP"])
	sf.allow_system_fallback = true
	if not (sf.has_char(0x6b7b) and sf.has_char(0x795e)):   # 死 神
		return null
	var fv := FontVariation.new()
	fv.base_font = sf
	fv.spacing_glyph = 10
	return fv


# -- procedural screen ------------------------------------------------------

class Backdrop extends Control:
	## Neon on void (DESIGN.md §1): a flat black field, a drifting starfield, a
	## two-rank city silhouette and slow spirit motes. No gradients anywhere — the
	## design doc rules them out and flat colour is what makes the acid green bite.
	##
	## Self-contained by intent. scripts/parallax.gd solves the scrolling-room
	## version of this and shares no useful code with a screen that never moves.

	const W := 640.0
	const H := 360.0
	const FAR_BASE := 318.0
	const NEAR_BASE := 348.0
	const STAR_COUNT := 190
	const MOTE_COUNT := 26
	const STAR_DRIFT := 2.0        # px/sec left; slow enough to read as weather
	const SEED := 20260729

	const VOID := Color("000000")
	const DEEP := Color("0a0e1f")
	const TOWER := Color("1e33d9")
	const CYAN := Color("35c6f4")
	const ACID := Color("c6f02a")
	const RED := Color("e01f26")

	var _far: Array[Rect2] = []
	var _near: Array[Rect2] = []
	var _win := PackedVector2Array()
	var _win_col := PackedColorArray()
	var _star := PackedVector2Array()
	var _star_col := PackedColorArray()
	var _mote := PackedVector2Array()
	var _mote_a := PackedFloat32Array()
	var _t := 0.0

	func _ready() -> void:
		set_anchors_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		var rng := RandomNumberGenerator.new()
		rng.seed = SEED                        # fixed: the same skyline every boot
		for i in STAR_COUNT:
			_star.append(Vector2(rng.randf() * W, rng.randf() * FAR_BASE))
			var c := CYAN if rng.randf() < 0.78 else ACID
			c.a = rng.randf_range(0.20, 0.85)
			_star_col.append(c)
		_far = _rank(rng, FAR_BASE, 40.0, 128.0, true)
		_near = _rank(rng, NEAR_BASE, 26.0, 78.0, false)
		for i in MOTE_COUNT:
			_mote.append(Vector2(rng.randf() * W, rng.randf() * H))
			_mote_a.append(rng.randf_range(0.30, 0.80))
		set_process(true)

	func _rank(rng: RandomNumberGenerator, base: float, h_min: float, h_max: float,
			lit: bool) -> Array[Rect2]:
		# blocks marching left to right; only the far rank gets windows, because a
		# lit foreground would stop reading as a silhouette
		var out: Array[Rect2] = []
		var x := -10.0
		while x < W:
			var w := rng.randf_range(20.0, 56.0)
			var h := rng.randf_range(h_min, h_max)
			out.append(Rect2(floorf(x), floorf(base - h), floorf(w), floorf(h)))
			if lit:
				for _i in int(h / 18.0):
					_win.append(Vector2(
						floorf(x + rng.randf_range(3.0, w - 4.0)),
						floorf(base - h + rng.randf_range(4.0, h - 5.0))))
					var c := CYAN if rng.randf() < 0.82 else RED
					c.a = rng.randf_range(0.25, 0.80)
					_win_col.append(c)
			x += w + rng.randf_range(2.0, 12.0)
		return out

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		draw_rect(Rect2(0.0, 0.0, W, H), VOID)
		for i in _star.size():
			var p: Vector2 = _star[i]
			var c: Color = _star_col[i]
			c.a *= 0.5 + 0.5 * sin(_t * 1.3 + float(i))
			draw_rect(Rect2(floorf(fposmod(p.x - _t * STAR_DRIFT, W)), p.y,
				1.0, 1.0), c)
		for r in _far:
			draw_rect(r, DEEP)
			draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 1.0),
				Color(TOWER, 0.55))          # 1px lip, or the block vanishes into black
		for i in _win.size():
			draw_rect(Rect2(_win[i], Vector2.ONE), _win_col[i])
		for r in _near:
			draw_rect(r, VOID)
			draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 1.0),
				Color(CYAN, 0.16))
		draw_rect(Rect2(0.0, NEAR_BASE, W, H - NEAR_BASE), VOID)
		draw_rect(Rect2(0.0, NEAR_BASE, W, 1.0), Color(ACID, 0.20))
		for i in _mote.size():
			var m: Vector2 = _mote[i]
			var y := floorf(fposmod(m.y - _t * (6.0 + float(i % 4)), H))
			var x := floorf(m.x + sin(_t * 0.7 + float(i)) * 3.0)
			var c := ACID
			c.a = _mote_a[i] * (0.55 + 0.45 * sin(_t * 1.9 + float(i)))
			draw_rect(Rect2(x, y, 1.0, 1.0), c)
			if i % 5 == 0:                   # every fifth mote carries a faint bloom
				c.a *= 0.30
				draw_rect(Rect2(x - 1.0, y - 1.0, 3.0, 3.0), c)


class Chrome extends Control:
	## Static console furniture: the rule under the subtitle, and the panel the
	## menu sits in so type never has to compete with the skyline behind it.
	## Drawn once and never invalidated.

	var rule_y := 144
	var panel := Rect2(248, 160, 144, 98)

	func _ready() -> void:
		set_anchors_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var acid := Color("c6f02a")
		var cyan := Color("35c6f4")
		draw_rect(Rect2(180.0, float(rule_y), 280.0, 1.0), Color(cyan, 0.22))
		draw_rect(Rect2(312.0, float(rule_y), 16.0, 1.0), Color(acid, 0.70))
		draw_rect(panel, Color(0.0, 0.0, 0.0, 0.55))
		draw_rect(Rect2(panel.position.x, panel.position.y, 1.0, panel.size.y),
			Color(acid, 0.45))
		# corner ticks rather than a closed frame: a full box reads as a dialog and
		# starts arguing with the wordmark for attention
		draw_rect(Rect2(panel.position.x, panel.position.y, 10.0, 1.0), Color(acid, 0.35))
		draw_rect(Rect2(panel.position.x, panel.end.y - 1.0, 10.0, 1.0), Color(acid, 0.35))
		draw_rect(Rect2(panel.end.x - 10.0, panel.position.y, 10.0, 1.0), Color(cyan, 0.25))
		draw_rect(Rect2(panel.end.x - 10.0, panel.end.y - 1.0, 10.0, 1.0), Color(cyan, 0.25))


class Scanlines extends Control:
	## CRT overlay: a 1px darkening on every other row, plus one slow bright sweep.
	## The lines are drawn once — only the sweep node moves, so this costs nothing
	## per frame beyond setting a position.

	var _sweep: ColorRect
	var _t := 0.0

	func _ready() -> void:
		set_anchors_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		_sweep = ColorRect.new()
		_sweep.color = Color(1.0, 1.0, 1.0, 0.035)
		_sweep.size = Vector2(640, 18)
		_sweep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_sweep)
		set_process(true)

	func _process(delta: float) -> void:
		_t += delta
		_sweep.position = Vector2(0.0, floorf(fposmod(_t * 26.0, 420.0) - 24.0))

	func _draw() -> void:
		var c := Color(0.0, 0.0, 0.0, 0.14)
		for y in range(0, 360, 2):
			draw_rect(Rect2(0.0, float(y), 640.0, 1.0), c)


class MatrixRain extends Node2D:
	## Falling glyph columns — the matrix motif from the persona's animated profile
	## art, done procedurally rather than as video: it animates forever, costs one
	## draw call, and scales with the viewport instead of being baked at 512px.
	##
	## Columns are seeded once so the field is stable across a session, but each
	## column falls at its own speed and wraps independently, so nothing visibly
	## loops.

	const COLS := 52
	const GLYPHS := "01ABCDEF0123456789$#%&*+=<>/|~^:;"
	const TRAIL := 9          # glyphs per column, head brightest
	const ACID := Color("c6f02a")
	const PALE := Color("8fe8ff")

	var _x: Array[float] = []
	var _y: Array[float] = []
	var _spd: Array[float] = []
	var _chars: Array = []
	var _font: Font
	var _t := 0.0

	func _ready() -> void:
		# NO z_index override. -1 sorted the rain behind every z-0 sibling —
		# including the opaque full-screen art, which made it invisible. Tree
		# order already does the right thing: added after the art, before the
		# sigil/logo/type, so it sits exactly where the composition comment says.
		_font = ThemeDB.fallback_font
		var rng := RandomNumberGenerator.new()
		rng.seed = 0x0029          # the handle, because why not
		for i in COLS:
			_x.append(float(int(i * (640.0 / COLS))))
			_y.append(rng.randf_range(-360.0, 360.0))
			_spd.append(rng.randf_range(18.0, 74.0))
			var col: Array[String] = []
			for j in TRAIL:
				col.append(GLYPHS[rng.randi_range(0, GLYPHS.length() - 1)])
			_chars.append(col)
		set_process(true)

	func _process(delta: float) -> void:
		_t += delta
		for i in COLS:
			_y[i] += _spd[i] * delta
			if _y[i] > 420.0:
				_y[i] = -float(TRAIL) * 9.0
		# reroll one glyph somewhere each frame: the field shimmers without the cost
		# of rerolling COLS*TRAIL characters every tick
		var c := int(_t * 37.0) % COLS
		var r := int(_t * 61.0) % TRAIL
		_chars[c][r] = GLYPHS[randi() % GLYPHS.length()]
		queue_redraw()

	func _draw() -> void:
		for i in COLS:
			for j in TRAIL:
				var y: float = _y[i] - j * 9.0
				if y < -8.0 or y > 368.0:
					continue
				# head is a pale hot glyph, the tail fades to dim acid green
				var f := 1.0 - float(j) / float(TRAIL)
				var col := PALE if j == 0 else ACID
				col.a = (0.30 if j == 0 else 0.16) * f
				draw_string(_font, Vector2(_x[i], y), _chars[i][j],
					HORIZONTAL_ALIGNMENT_LEFT, -1, 8, col)
