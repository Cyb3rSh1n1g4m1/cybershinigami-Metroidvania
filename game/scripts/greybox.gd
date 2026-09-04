extends Node2D
## M1 grey-box test room. The layout IS the text below — 16px tiles, edit the map.
## Room is 2880x360. Origin top-left.
## Legend (scripts/room.gd): '#' solid  '=' one-way platform  '^' hazard  '.' empty
##
## Three areas, separated by terrain so the room reads as a place, not one floor:
##   A  cols   0- 59  (x    0- 960)  spawn + traversal test: 1/2/3-step staircase,
##                                   the 4-up gated ledge, 48/32/96px gaps, shrine.
##   -- hill,  cols  60- 72          crest 48px over the floor, 16px per step
##   B  cols  73-117  (x 1168-1888)  combat arena: 720px of flat floor, 240px of
##                                   headroom. Guardian + the two husks live here.
##   -- ridge, cols 118-126          crest 48px up, 32px drop off the far side
##   C  cols 127-179  (x 2032-2880)  vertical section: ground climbs in three 16px
##                                   tiers, then a one-way stair to the high perch.
##
## Movement budget (player.gd — tune the map, never those constants): a running
## jump rises 63px and carries ~87px of horizontal travel, and the 18px-wide body
## overhangs both lips, so ~105px is the hard gap ceiling and a 3-tile step (48px)
## is the tallest rise a floor-level jump clears. Rises shrink the reach: 16px up
## still crosses 98px, 32px up crosses 92px, 48px up only 83px. Every gap below is
## inside those numbers except the two rises marked GATED.
const MAP: Array[String] = [
	#000000000011111111112222222222333333333344444444445555555555666666666677777777778888888888999999999900000000001111111111222222222233333333334444444444555555555566666666667777777777
	#012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
	"#..................................................................................................................................................................................#",
	"#..................................................................................................................................................................................#",
	"#..................................................................................................................................................................................#",
	"#..................................................................................................................................................................................#",
	"#..................................................................................................................................................................................#",
	"#.............................................................................................................................................................................=====#",  # C high perch: 160px over the C floor, top of the one-way stair
	"#..................................................................................................................................................................................#",
	"#...............................................................................................................................======................................======.......#",  # C gated perch: 112px over the step at 130-133 — GATED, no move reaches it yet (measured max rise 63px; there is no air-jump in player.gd) | C stair 2
	"#..................................................................................................................................................................................#",
	"#...........................................................................................................................................................======.................#",  # C stair 1
	"#..................................................................................................................................................................................#",
	"#..........................###.....................................................................................................................................................#",  # A: 4 up — GATED from the floor (64px), enter from the 3-step
	"#...................####.........................................###.....................................................####.....................#######..........................#",  # A: 3 up          | hill crest | ridge crest | C tier 3
	"#.............####............................................#########................................................######................############..........................#",  # A: 2 up   | hill | ridge      | C tier 2
	"#.......####......................###...###..###......###...#############.............................................#########...####..#################..........................#",  # A: 1 up; gaps 48/32/96px | hill skirt | ridge skirt | C step + tier 1
	"####################################################################################################################################################################################",  # floor, y=344
]


func _ready() -> void:
	Audio.music("region1_perimeter")   # silent until the track exists (§14b.5)
	# backdrop first — it owns CanvasLayer -100, so it draws behind the whole room
	var bg := ParallaxBackground.new()
	bg.set_script(load("res://scripts/parallax.gd"))
	add_child(bg)

	var room := Node2D.new()
	room.set_script(load("res://scripts/room.gd"))
	room.map = MAP
	# hang the map so its bottom row lands on the 344 floor line (parallax.gd HORIZON)
	room.position.y = 360 - MAP.size() * 16
	add_child(room)
	move_child(room, 0)  # draw behind the player, not over it

	# set dressing hung off the real geometry — lanterns, clutter, distant torii
	var props := Node2D.new()
	props.set_script(load("res://scripts/props.gd"))
	props.map = MAP
	props.position.y = room.position.y
	add_child(props)
	move_child(props, 1)

	# camera stays inside the room — width follows the map, so widening it is one edit
	var cam: Camera2D = $Player/Camera2D
	cam.limit_left = 0
	cam.limit_top = 0
	cam.limit_right = MAP[0].length() * 16
	cam.limit_bottom = 360

	# M2: worms in AREA A, on the floor slots the staircase and ledges leave clear
	var worm_scene := preload("res://scenes/enemies/worm.tscn")
	for x in [300.0, 470.0, 800.0]:
		var w := worm_scene.instantiate()
		w.position = Vector2(x, 336)
		add_child(w)

	# M2: the heavies get AREA B, the drone gets AREA C's airspace.
	# Guardian sits 220px off the nearest husk and 232px off the hill, so it has
	# room to plant, telegraph and lunge (90px trigger, 70px reach) without a husk
	# in the swing. The husks are 200px apart — inside the 300px botnet link, so
	# hitting one visibly enrages the other.
	var spawns := {
		"res://scenes/enemies/drone.tscn": [Vector2(2176, 250)],
		"res://scenes/enemies/husk.tscn": [Vector2(1620, 312), Vector2(1820, 312)],
		"res://scenes/enemies/guardian.tscn": [Vector2(1400, 312)],
	}
	for path in spawns:
		var scene: PackedScene = load(path)
		for pos in spawns[path]:
			var e: Node2D = scene.instantiate()
			e.position = pos
			add_child(e)

	# M4 seed: first Snapshot shrine near spawn
	var shrine := Area2D.new()
	shrine.set_script(load("res://scripts/shrine.gd"))
	shrine.position = Vector2(150, 296)
	add_child(shrine)

	# M4 loop: the modules sit past the arena, and Privilege Escalation is what
	# opens the gated perch back in C — hit the wall, clear the fight, return, pass.
	var modules := {
		"double_jump": Vector2(1820, 316),
		"integrity": Vector2(1240, 316),
		# §16.2 verb pickups — TEST placement in the greybox; final homes come
		# with the R1-R3 room builds
		"heavy": Vector2(600, 316),
		"charge": Vector2(1420, 316),
		"slam": Vector2(1560, 316),
	}
	for mod_id in modules:
		var m := Area2D.new()
		m.set_script(load("res://scripts/upgrade_module.gd"))
		m.id = mod_id
		m.position = modules[mod_id]
		add_child(m)

	# M5 HUD — Integrity pips, Soul Bytes, toast line, ability row. Built last so the
	# Player is already in the tree: hud.gd reads its opening Integrity on _ready.
	var hud := CanvasLayer.new()
	hud.set_script(load("res://scripts/hud.gd"))
	add_child(hud)
