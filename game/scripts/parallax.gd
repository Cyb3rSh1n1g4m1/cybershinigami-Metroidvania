extends ParallaxBackground
## Scrolling city backdrop. Three depths on CanvasLayer -100, so it draws behind
## every gameplay node and owns no collision, no input, no physics.
## Art is optional: a missing bg texture is replaced by a procedural stand-in, so
## the room always renders.

const FAR_TEX := "res://art/bg/bg_far.png"
const MID_TEX := "res://art/bg/bg_mid.png"
const TORII_TEX := "res://art/bg/torii.png"

const TILE := Vector2(640, 360)  # one viewport = one procedural tile
const HORIZON := 344.0           # greybox floor line — towers stand on it

const DEEP := Color("0a0e1f")
const TOWER := Color("1e33d9")
const CYAN := Color("35c6f4")
const ACID := Color("c6f02a")

const STAR_COUNT := 260
const MOTE_COUNT := 28
const STAR_SEED := 20260729
const TOWER_SEED := 1116

var _sky_ref: GradientTexture2D


func _ready() -> void:
	layer = -100  # ParallaxBackground's own default, pinned so it is not an accident

	# night sky gradient, screen-locked rather than parallaxed: no seam can ever show
	var grad := Gradient.new()
	grad.offsets = PackedFloat32Array([0.0, 0.55, 1.0])
	grad.colors = PackedColorArray([Color("05070f"), DEEP, Color("18143a")])
	var gtex := GradientTexture2D.new()
	gtex.gradient = grad
	gtex.fill_from = Vector2(0, 0)
	gtex.fill_to = Vector2(0, 1)   # vertical: darkest overhead, warmer near the city
	gtex.width = 1
	gtex.height = 64
	var sky := TextureRect.new()
	sky.texture = gtex
	sky.set_anchors_preset(Control.PRESET_FULL_RECT)
	sky.stretch_mode = TextureRect.STRETCH_SCALE
	sky.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(sky)
	_sky_ref = gtex  # keep the generated texture referenced for the node's lifetime

	# moon: effectively fixed. A single landmark high in the sky is what tells the
	# eye the backdrop is one place rather than a repeating strip.
	var moon_layer := _add_layer(0.03)
	moon_layer.motion_mirroring = Vector2.ZERO  # never repeats — there is one moon
	moon_layer.add_child(_moon())

	# clouds behind the moon, then in front: the pass-over is what sells depth
	var cloud_back := _add_layer(0.06)
	_clouds(cloud_back, 4211, 0.55, 6.0, 0.30)
	var cloud_front := _add_layer(0.11)
	_clouds(cloud_front, 9137, 0.85, 10.0, 0.22)

	# far: distant glow art when it exists, plus the starfield that always draws
	var far := _add_layer(0.15, FAR_TEX)
	far.add_child(_starfield(far.motion_mirroring.x))

	# THE torii — one, never repeated. It lives in its own layer rather than in
	# the tiled skyline art, because anything inside a repeating tile repeats,
	# and a landmark that appears twice stops being a landmark.
	if ResourceLoader.exists(TORII_TEX):
		var gate := _add_layer(0.13)
		gate.motion_mirroring = Vector2.ZERO
		var s := Sprite2D.new()
		s.texture = load(TORII_TEX)
		s.centered = false
		s.position = Vector2(880.0, HORIZON - 150.0)
		gate.add_child(s)

	# mid: real skyline art, or blocky stand-in towers until it lands
	var mid := _add_layer(0.4, MID_TEX)
	if not ResourceLoader.exists(MID_TEX):
		mid.add_child(_towers(mid.motion_mirroring.x))

	# near: spirit motes only — no art planned at this depth
	var near := _add_layer(0.7)
	near.add_child(_motes())


func _moon() -> Node2D:
	# drawn, not textured: a crisp disc with a bitten edge and a soft halo
	var n := Moon.new()
	n.position = Vector2(352.0, 44.0)
	return n


func _clouds(layer: ParallaxLayer, seed_v: int, alpha: float, drift: float,
		scale_y: float) -> void:
	# wispy horizontal banks that slide across the sky independently of the camera
	var c := Clouds.new()
	c.seed_v = seed_v
	c.alpha = alpha
	c.drift = drift
	c.squash = scale_y
	c.span = layer.motion_mirroring.x if layer.motion_mirroring.x > 0.0 else TILE.x
	layer.add_child(c)


class Moon:
	extends Node2D

	func _draw() -> void:
		var r := 15.0
		# halo first, widest and faintest
		for i in 5:
			var t := float(i) / 5.0
			draw_circle(Vector2.ZERO, r + 5.0 + t * 16.0,
				Color(0.56, 0.91, 1.0, 0.05 * (1.0 - t)))
		draw_circle(Vector2.ZERO, r, Color(0.90, 0.94, 1.0, 0.95))
		# bite out of the upper-right: a gibbous reads more deliberate than a disc
		draw_circle(Vector2(7.0, -6.0), r * 0.78, Color("0a0e1f"))
		# maria, so it is not a featureless blob
		draw_circle(Vector2(-5.0, 3.0), 3.4, Color(0.72, 0.80, 0.94, 0.75))
		draw_circle(Vector2(-1.0, 7.0), 2.1, Color(0.72, 0.80, 0.94, 0.6))
		draw_circle(Vector2(-8.0, -4.0), 1.7, Color(0.72, 0.80, 0.94, 0.5))


class Clouds:
	extends Node2D

	var seed_v := 0
	var alpha := 0.6
	var drift := 8.0        # px/sec, independent of the camera
	var squash := 0.3
	var span := 640.0
	var _bands: Array = []
	var _t := 0.0

	func _ready() -> void:
		var rng := RandomNumberGenerator.new()
		rng.seed = seed_v
		# each band is a row of overlapping ellipses — cheap, and it reads wispy
		for i in rng.randi_range(5, 7):
			var y := rng.randf_range(8.0, 96.0)
			var puffs: Array = []
			var x := rng.randf_range(0.0, span)
			var w := rng.randf_range(70.0, 190.0)
			var n := int(w / 14.0)
			for j in n:
				puffs.append(Vector3(x + j * 14.0,
					y + rng.randf_range(-4.0, 4.0),
					rng.randf_range(9.0, 17.0)))
			_bands.append(puffs)
		set_process(true)

	func _process(delta: float) -> void:
		_t += delta * drift
		queue_redraw()

	func _draw() -> void:
		var col := Color(0.30, 0.28, 0.55, alpha * 0.5)
		var lit := Color(0.42, 0.40, 0.68, alpha * 0.5)
		for band in _bands:
			for p in band:
				# wrap twice so a band is always entering as another leaves
				for rep in [-1.0, 0.0, 1.0]:
					var px: float = fposmod(p.x + _t, span) + rep * span
					if px < -220.0 or px > span + 220.0:
						continue
					var c := lit if p.z > 14.0 else col
					draw_circle(Vector2(px, p.y), p.z, c)
					draw_circle(Vector2(px, p.y - p.z * squash * 0.5),
						p.z * 0.72, c)


func _add_layer(motion: float, tex_path := "") -> ParallaxLayer:
	var l := ParallaxLayer.new()
	l.motion_scale = Vector2(motion, motion)
	var width := TILE.x
	if not tex_path.is_empty() and ResourceLoader.exists(tex_path):
		var s := Sprite2D.new()
		s.texture = load(tex_path)
		s.centered = false
		l.add_child(s)
		width = float(s.texture.get_width())
	l.motion_mirroring = Vector2(width, 0.0)  # repeats forever as the camera pans
	add_child(l)
	return l


func _starfield(width: float) -> Field:
	# fixed seed: the same sky every run
	var f := Field.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = STAR_SEED
	for i in STAR_COUNT:
		f.pts.append(Vector2(rng.randf() * width, rng.randf() * HORIZON))
		var c := CYAN if rng.randf() < 0.72 else ACID
		c.a = rng.randf_range(0.25, 0.9)
		f.cols.append(c)
	return f


func _towers(width: float) -> Field:
	# ponytail: rectangles with lit windows stand in until art/bg/bg_mid.png exists
	var f := Field.new()
	f.block_color = Color(TOWER, 0.35)
	var rng := RandomNumberGenerator.new()
	rng.seed = TOWER_SEED
	var x := 0.0
	while x < width:
		# clamp to the mirror seam: a tower crossing it is redrawn over the first
		# tower of the next tile and composites to a bright band every `width` px
		var w := minf(rng.randf_range(18.0, 46.0), width - x)
		var h := rng.randf_range(40.0, 120.0)
		f.blocks.append(Rect2(x, HORIZON - h, w, h))
		for i in int(h / 20.0):
			f.pts.append(Vector2(x + rng.randf_range(3.0, w - 3.0),
				HORIZON - h + rng.randf_range(4.0, h - 4.0)))
			var c := CYAN
			c.a = rng.randf_range(0.3, 0.85)
			f.cols.append(c)
		x += w + rng.randf_range(2.0, 10.0)
	return f


func _motes() -> Field:
	var f := Field.new()
	f.drift = 6.0  # px/sec upward — slow enough to read as distance
	f.span_y = TILE.y
	var rng := RandomNumberGenerator.new()
	rng.seed = STAR_SEED + 1
	for i in MOTE_COUNT:
		f.pts.append(Vector2(rng.randf() * TILE.x, rng.randf() * TILE.y))
		var c := ACID
		c.a = rng.randf_range(0.35, 0.75)
		f.cols.append(c)
	return f


class Field extends Node2D:
	## One procedural backdrop tile: solid blocks, then 1px lights.
	## drift > 0 makes the lights rise and pulse; otherwise this draws once and idles.
	var blocks: Array[Rect2] = []
	var block_color := Color.BLACK
	var pts := PackedVector2Array()
	var cols := PackedColorArray()
	var drift := 0.0
	var span_y := 360.0
	var _t := 0.0

	func _ready() -> void:
		set_process(drift > 0.0)

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		for r in blocks:
			draw_rect(r, block_color)
		for i in pts.size():
			var p: Vector2 = pts[i]
			var c: Color = cols[i]
			if drift > 0.0:
				p.y = fposmod(p.y - _t * drift, span_y)
				p.x += sin(_t * 0.6 + i) * 2.0
				c.a *= 0.55 + 0.45 * sin(_t * 1.7 + i)
			draw_rect(Rect2(p.floor(), Vector2.ONE), c)
