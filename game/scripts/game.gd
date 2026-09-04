extends Node
## Autoload "Game" — run state. Two members; resist adding more before M5.

signal souls_changed(total: int)
signal toast(msg: String)
signal ability_gained(id: String)

# unlocked abilities (DESIGN.md §4). Empty at run start — the map is gated on these.
var abilities := {}


func has(id: String) -> bool:
	return abilities.has(id)


func grant(id: String) -> void:
	if abilities.has(id):
		return
	abilities[id] = true
	ability_gained.emit(id)

var soul_bytes := 0:
	set(v):
		soul_bytes = v
		souls_changed.emit(v)


func reset_run() -> void:
	## Fresh-run wipe, called by the title screen's START. Without it, quitting to
	## the title and starting again carried the old run's abilities and souls in.
	abilities = {}
	soul_bytes = 0
