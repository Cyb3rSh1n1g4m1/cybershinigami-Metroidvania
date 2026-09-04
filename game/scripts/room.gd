extends Node2D
## Data-driven room. Feed it an ASCII map (equal-length rows) before adding it to
## the tree; it builds collision + visuals on a 16px grid.
##   '#' solid   '=' one-way platform   '^' hazard   '.' empty
## Horizontally adjacent tiles of the same glyph merge into one wide shape, so a
## floor is one body per row-run, not one body per tile.

const TILE := 16
const TILESET := "res://art/tileset.png"

# atlas cell per glyph — only read when TILESET exists on disk
const ATLAS := {"#": Vector2i(0, 0), "=": Vector2i(1, 0), "^": Vector2i(2, 0)}
# a solid tile with nothing solid above it is an exposed surface and gets the
# lit-edge tile instead — that rim is what makes platforms read against the city
const TOP_CELL := Vector2i(3, 0)
# ColorRect fallback colours (palette): world grey, cyan-blue platform, red hazard
const FILL := {"#": Color("4a5568"), "=": Color("2b6fe8"), "^": Color("e01f26")}

var map: Array[String] = []

var _painted := false  # true once a real tileset drew the visuals


func _ready() -> void:
	if map.is_empty():
		return
	# a short row is a typo, not a design: it silently moves collision instead of failing
	for row in map:
		assert(row.length() == map[0].length(), "room map rows must be equal length")
	var tex := _texture()
	if tex != null:
		_draw_tiles(tex)
		_painted = true
	for y in map.size():
		for run in _runs(map[y], "#"):
			_body(_rect(run, y), false)
		for run in _runs(map[y], "="):
			_body(_rect(run, y), true)
		for run in _runs(map[y], "^"):
			_hazard(_rect(run, y))


func _runs(row: String, glyph: String) -> Array[Vector2i]:
	# horizontal runs of glyph as (start_col, length) — one shape per run
	var out: Array[Vector2i] = []
	var x := 0
	while x < row.length():
		if row[x] != glyph:
			x += 1
			continue
		var start := x
		while x < row.length() and row[x] == glyph:
			x += 1
		out.append(Vector2i(start, x - start))
	return out


func _rect(run: Vector2i, y: int) -> Rect2:
	return Rect2(run.x * TILE, y * TILE, run.y * TILE, TILE)


func _body(r: Rect2, one_way: bool) -> void:
	if one_way:
		# the platform tile is a floating deck: its lit surface sits 4px below
		# the cell top (the rows above are transparent). Collision must land
		# ON the deck, not on the empty air above it — without this the
		# character stood 4px over every one-way platform.
		r.position.y += 4.0
		r.size.y -= 4.0
	var body := StaticBody2D.new()
	body.collision_layer = 1  # world
	body.collision_mask = 0
	body.position = r.position + r.size / 2.0
	var shape := CollisionShape2D.new()
	var box := RectangleShape2D.new()
	box.size = r.size
	shape.shape = box
	shape.one_way_collision = one_way  # land on top, jump up through
	body.add_child(shape)
	add_child(body)
	if not _painted:
		_paint(r, FILL["=" if one_way else "#"])


func _hazard(r: Rect2) -> void:
	var area := Area2D.new()
	area.collision_layer = 0
	area.collision_mask = 2  # player only — enemies walk over spikes
	area.position = r.position + r.size / 2.0
	var shape := CollisionShape2D.new()
	var box := RectangleShape2D.new()
	box.size = r.size
	shape.shape = box
	area.add_child(shape)
	# ponytail: one hit per entry, same contract as worm.gd's hurtbox — standing
	# still inside a hazard never re-ticks. Fine until there is a health system.
	area.body_entered.connect(func(b: Node) -> void:
		if b.has_method("hurt"):
			b.hurt(area.global_position))
	add_child(area)
	if not _painted:
		_paint(r, FILL["^"])


func _paint(r: Rect2, color: Color) -> void:
	var v := ColorRect.new()
	v.position = r.position
	v.size = r.size
	v.color = color
	add_child(v)


func _texture() -> Texture2D:
	if not ResourceLoader.exists(TILESET):
		return null
	var tex: Texture2D = load(TILESET)
	if tex == null or tex.get_width() < TILE or tex.get_height() < TILE:
		return null
	return tex


func _draw_tiles(tex: Texture2D) -> void:
	var cols := tex.get_width() / TILE
	var rows := tex.get_height() / TILE
	var src := TileSetAtlasSource.new()
	src.texture = tex
	src.texture_region_size = Vector2i(TILE, TILE)
	var cell := {}
	var made := {}
	for glyph in ATLAS:
		var c: Vector2i = ATLAS[glyph]
		if c.x >= cols or c.y >= rows:
			c = Vector2i.ZERO  # tileset smaller than the legend — everyone shares tile 0
		cell[glyph] = c
		if not made.has(c):
			made[c] = true
			src.create_tile(c)
	var top_cell := TOP_CELL
	if top_cell.x >= cols or top_cell.y >= rows:
		top_cell = cell.get("#", Vector2i.ZERO)
	elif not made.has(top_cell):
		made[top_cell] = true
		src.create_tile(top_cell)
	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE, TILE)
	ts.add_source(src, 0)
	var layer := TileMapLayer.new()
	layer.tile_set = ts
	for y in map.size():
		for x in map[y].length():
			var glyph: String = map[y][x]
			if not cell.has(glyph):
				continue
			var c: Vector2i = cell[glyph]
			if glyph == "#" and (y == 0 or map[y - 1][x] != "#"):
				c = top_cell            # exposed surface: use the lit rim
			layer.set_cell(Vector2i(x, y), 0, c)
	add_child(layer)
