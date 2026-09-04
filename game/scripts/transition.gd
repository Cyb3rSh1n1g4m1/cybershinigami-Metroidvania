extends Node
## Autoload "Transition" — scene routing. The fade itself belongs to UI
## (scripts/ui_kit.gd), which already owns the overlay layer; what lives here is
## the ordering around a swap and the re-entrancy guard, neither of which UI has.
## Deliberately does NOT own a ColorRect: a second veil on layer 128 would sort
## against UI's by tree order, which is not a thing to rely on.
##
##   Transition.go("res://scenes/rooms/greybox.tscn")
##   Transition.quit_game()
##
## Input-free by design. The ESC key belongs to the Pause autoload, which polls it
## and swaps scenes itself; a stopgap ESC->title handler used to live here and now
## would only fire alongside the menu opening.

const FADE := 0.28

var _busy := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS  # a transition must survive a paused tree


func go(path: String, dur := FADE) -> void:
	if _busy:
		return                               # mashing START must not queue two swaps
	_busy = true
	await UI.fade_out(dur).finished
	get_tree().paused = false                # no scene may inherit a pause
	var err := get_tree().change_scene_to_file(path)
	if err != OK:
		push_error("Transition: cannot load %s (error %d)" % [path, err])
	# change_scene_to_file is deferred. Without this frame the veil lifts on the
	# outgoing scene and you watch the old room for a frame before the new one.
	await get_tree().process_frame
	await UI.fade_in(dur).finished
	_busy = false


func quit_game(dur := FADE) -> void:
	if _busy:
		return
	_busy = true
	await UI.fade_out(dur).finished
	get_tree().quit()
