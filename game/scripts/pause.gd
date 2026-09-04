extends CanvasLayer
## Autoload "Pause" — pause screen + status readout (DESIGN.md §3.1, §4, §7).
##
## Autoloaded rather than parented to the player: RESTART FROM SNAPSHOT and QUIT TO
## TITLE both reload or swap the current scene, and a menu living inside that scene
## would free itself halfway through its own callback. Autoloading also keeps room
## scripts free of menu wiring — greybox.gd never mentions this file.
##
## process_mode is ALWAYS, not WHEN_PAUSED, because this node also has to catch the
## toggle key while the tree is *running*. The UI subtree below it is WHEN_PAUSED,
## so nothing inside the menu ticks except while the game is actually paused.
## Everything else in the project is the default PAUSABLE — that is what freezes the
## enemies, the hit-flash tweens, the soul drops and the parallax clouds.

const ACID := Color("c6f02a")   # UI accent
const CYAN := Color("8fe8ff")   # values / data
const DIM := Color("4a5568")    # chrome, leader dots, locked entries
const RED := Color("e01f26")    # integrity in the red
const INK := Color("0a0e1f")    # panel fill, and text on a reverse-video bar

const FONT_MAIN := 10
const FONT_SMALL := 8

const INSET := Vector2(40, 26)  # panel margin inside the 640x360 frame
const KEY_W := 300.0            # left column: name + leader dots, clipped at this edge
const VAL_W := 90.0
const OPT_W := 268.0

const TITLE_SCENE := "res://scenes/ui/title.tscn"

# DESIGN.md §4, in unlock order. `id` is the Game.abilities key; only double_jump is
# grantable today (ability_pickup.gd), the other three are here so the list reads as
# a map of what the host *can* hold rather than a list of what you happen to own.
const ABILITIES: Array[Dictionary] = [
	{"id": "dash", "name": "PING SWEEP",
		"desc": "ground dash, 60px burst. i-frames mid-sweep."},
	{"id": "double_jump", "name": "PRIVILEGE ESCALATION",
		"desc": "root jump. one more vector while airborne."},
	{"id": "ranged", "name": "PACKET INJECTION",
		"desc": "ranged payload. spends cycles."},
	{"id": "tunnel", "name": "TUNNEL",
		"desc": "phase through cyan-marked walls."},
]

const OPTIONS: Array[String] = ["RESUME", "RESTART FROM SNAPSHOT", "QUIT TO TITLE"]

var _open := false
var _sel := 0
var _blink := 0.0

var _ui: Control
var _cursor: ColorRect
var _integrity: Label
var _souls: Label
var _caps: VBoxContainer
var _options: Array[Label] = []


func _ready() -> void:
	layer = 100  # above any in-scene HUD CanvasLayer, which sit on the default 1
	process_mode = Node.PROCESS_MODE_ALWAYS
	_bind_pause_action()
	_build()
	_ui.hide()


func _bind_pause_action() -> void:
	## ponytail: the binding is registered here instead of project.godot so the menu
	## drops in without editing the shared input map. Ceiling: move it into
	## project.godot the moment a key-rebinding screen exists — the has_action guard
	## means that edit silently takes over with no change here.
	if InputMap.has_action("pause"):
		return
	InputMap.add_action("pause", 0.2)
	var esc := InputEventKey.new()
	esc.physical_keycode = KEY_ESCAPE
	InputMap.action_add_event("pause", esc)
	var start := InputEventJoypadButton.new()
	start.button_index = JOY_BUTTON_START
	InputMap.action_add_event("pause", start)


# ---------------------------------------------------------------- construction

func _build() -> void:
	_ui = Control.new()
	_ui.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.process_mode = Node.PROCESS_MODE_WHEN_PAUSED
	add_child(_ui)

	var shade := ColorRect.new()
	shade.color = Color(0.0, 0.0, 0.0, 0.72)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.add_child(shade)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.offset_left = INSET.x
	panel.offset_top = INSET.y
	panel.offset_right = -INSET.x
	panel.offset_bottom = -INSET.y
	panel.add_theme_stylebox_override("panel", _frame())
	_ui.add_child(panel)

	var pad := MarginContainer.new()
	for side: String in ["left", "right", "top", "bottom"]:
		pad.add_theme_constant_override("margin_" + side, 10)
	panel.add_child(pad)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 2)
	pad.add_child(col)

	_build_header(col)
	_gap(col, 6)
	_integrity = _stat(col, "integrity")
	_souls = _stat(col, "soul bytes")
	_gap(col, 8)

	col.add_child(_text("root@0x0029:~# cat /proc/self/caps", ACID, FONT_MAIN))
	_gap(col, 2)
	_caps = VBoxContainer.new()
	_caps.add_theme_constant_override("separation", 1)
	col.add_child(_caps)

	var stretch := Control.new()
	stretch.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(stretch)

	for label: String in OPTIONS:
		var o := _text("  " + label, CYAN, FONT_MAIN)
		o.custom_minimum_size.x = OPT_W
		col.add_child(o)
		_options.append(o)

	_gap(col, 6)
	col.add_child(_text("[W/S|STICK] select    [SPACE/J|A/Y] confirm    [ESC|START] close",
		DIM, FONT_SMALL))


func _build_header(col: VBoxContainer) -> void:
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 2)
	col.add_child(head)
	head.add_child(_text("root@0x0029:~# status", ACID, FONT_MAIN))
	_cursor = ColorRect.new()
	_cursor.color = ACID
	_cursor.custom_minimum_size = Vector2(5, 9)
	_cursor.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(_cursor)
	var state := _text("-- process suspended --", DIM, FONT_SMALL)
	state.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	state.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	state.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	head.add_child(state)


func _frame() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(INK.r, INK.g, INK.b, 0.96)
	sb.border_color = ACID
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(0)  # square: a curve at 640x360 is four muddy pixels
	return sb


func _text(s: String, c: Color, size: int) -> Label:
	var l := Label.new()
	l.text = s
	l.add_theme_color_override("font_color", c)
	l.add_theme_font_size_override("font_size", size)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _gap(parent: Node, px: int) -> void:
	var c := Control.new()
	c.custom_minimum_size.y = px
	parent.add_child(c)


func _stat(parent: Node, key: String) -> Label:
	## "integrity ......... 4/5". The leader dots are baked into the left label and
	## clipped at the column edge rather than counted out per row, so the value column
	## lines up under any font — the default theme font is not monospaced.
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	parent.add_child(row)
	var k := _text(key + " " + ".".repeat(120), DIM, FONT_MAIN)
	k.custom_minimum_size.x = KEY_W
	k.clip_text = true
	row.add_child(k)
	var v := _text("", CYAN, FONT_MAIN)
	v.custom_minimum_size.x = VAL_W
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(v)
	return v


func _cap_row(cap: Dictionary) -> void:
	var id: String = cap["id"]
	var unlocked := Game.has(id)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	_caps.add_child(row)

	var name_text: String = cap["name"] if unlocked else _redact(cap["name"])
	var n := _text("  " + name_text, CYAN if unlocked else DIM, FONT_MAIN)
	n.custom_minimum_size.x = KEY_W
	n.clip_text = true
	row.add_child(n)
	row.add_child(_text("[ ONLINE ]" if unlocked else "[ LOCKED ]",
		ACID if unlocked else DIM, FONT_MAIN))

	# a locked row keeps its second line so the list does not jump when one unlocks
	var desc: String = cap["desc"] if unlocked else "not present on this host"
	_caps.add_child(_text("    " + desc, DIM if unlocked else Color(DIM, 0.55),
		FONT_SMALL))


func _redact(s: String) -> String:
	## Same shape, no letters: the player learns a capability exists and roughly how
	## long its name is, nothing else. '?' is the same unknown glyph the map screen
	## uses for unexplored nodes (DESIGN.md §3.2).
	var out := ""
	for ch in s:
		out += " " if ch == " " else "?"
	return out


# ---------------------------------------------------------------------- state

func _player() -> Node:
	return get_tree().get_first_node_in_group("player")


func _refresh() -> void:
	var p := _player()
	var cur := 0
	var top := 0
	if p != null:
		cur = p.integrity
		top = p.max_integrity
	_integrity.text = "%d/%d" % [cur, top]
	_integrity.add_theme_color_override("font_color", RED if cur <= 1 else CYAN)
	_souls.text = str(Game.soul_bytes)

	for c in _caps.get_children():
		_caps.remove_child(c)
		c.queue_free()
	for cap: Dictionary in ABILITIES:
		_cap_row(cap)

	_paint_selection()


func _paint_selection() -> void:
	## Reverse video, the way a curses menu does it — at 640x360 a filled bar reads
	## from across the room in a way a caret or a colour shift does not.
	for i in _options.size():
		var l := _options[i]
		if i == _sel:
			var sb := StyleBoxFlat.new()
			sb.bg_color = ACID
			sb.set_content_margin_all(0)  # no shift between selected and not
			l.add_theme_stylebox_override("normal", sb)
			l.add_theme_color_override("font_color", INK)
		else:
			l.remove_theme_stylebox_override("normal")
			l.add_theme_color_override("font_color", CYAN)


# ---------------------------------------------------------------------- input

func _process(delta: float) -> void:
	if Input.is_action_just_pressed("pause"):
		if _open:
			_close()
		elif _player() != null:  # no player in the tree means a menu scene: stay out
			_show()
		return
	if not _open:
		return

	_blink += delta
	_cursor.visible = fmod(_blink, 1.0) < 0.55

	if Input.is_action_just_pressed("aim_down"):
		_move(1)
	elif Input.is_action_just_pressed("aim_up"):
		_move(-1)
	elif Input.is_action_just_pressed("jump") or Input.is_action_just_pressed("attack"):
		_confirm()


func _move(d: int) -> void:
	_sel = wrapi(_sel + d, 0, OPTIONS.size())
	_paint_selection()
	Audio.play("menu_move")


func _show() -> void:
	_open = true
	_sel = 0
	_blink = 0.0
	_cursor.visible = true
	_refresh()
	_ui.show()
	get_tree().paused = true
	Audio.play("pause_open")    # no-op until the sound lands


func _close() -> void:
	_open = false
	_ui.hide()
	get_tree().paused = false
	Audio.play("pause_close")   # no-op until the sound lands
	# No input scrubbing needed on the way out: confirming happens on an idle frame,
	# and the player only reads input in _physics_process, which cannot run again
	# until the next iteration — by then "just pressed" has already lapsed.


func _confirm() -> void:
	Audio.play("menu_confirm")
	match _sel:
		0:
			_close()
		1:
			_restart()
		2:
			_quit_to_title()


func _restart() -> void:
	var p := _player()
	_close()
	if p == null:
		return
	p.snapshot_restore()
	Game.toast.emit("RESTORED FROM SNAPSHOT · ssh perimeter@0x0029")


func _quit_to_title() -> void:
	_close()  # drops the pause before the swap, so the title never inherits one
	# Run state (Game.abilities, Game.soul_bytes) is deliberately left alone: starting
	# a fresh run belongs to the title screen, and there is no save system to reload.
	#
	# A hard cut, not Transition.go(): that fades for 0.28s first, and this node polls
	# its toggle on PROCESS_MODE_ALWAYS — a second ESC inside the fade would reopen the
	# menu over the outgoing room and leave it stranded on the title. Swapping here is
	# instant, so there is no window to press into.
	get_tree().change_scene_to_file(TITLE_SCENE)
