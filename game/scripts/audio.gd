extends Node
## Autoload "Audio" — every sound goes through here (DESIGN.md §14b).
## Missing files are silent no-ops, so gameplay hooks can land before any WAV
## exists and each new sound starts working the moment its file appears.

const SFX_DIR := "res://audio/sfx/"
const MUSIC_DIR := "res://audio/music/"
const POOL_SIZE := 10

# ids routed off the default SFX bus (§14b.1). The reaper's own verbs get the
# Player bus so the blade never gets buried; UI ignores in-world ducking.
const BUS := {
	"step_a": "Player", "step_b": "Player", "jump": "Player",
	"double_jump": "Player", "land": "Player", "dash": "Player",
	"turn": "Player", "swing_chudan": "Player", "swing_jodan": "Player",
	"swing_gedan": "Player", "heavy_draw": "Player", "hurt": "Player",
	"death": "Player", "respawn": "Player",
	"menu_move": "UI", "menu_confirm": "UI", "menu_back": "UI",
	"pause_open": "UI", "pause_close": "UI", "toast_blip": "UI",
}

var _pool: Array[AudioStreamPlayer] = []
var _cache := {}
var _music: AudioStreamPlayer
var _music_track := ""
var _duck: Tween
var _chain := 0
var _chain_timer := 0.0
# combat layer (§14b.2): rides ON TOP of the region track, phase-locked —
# same bpm and length, started at the region player's playback position
var _combat: AudioStreamPlayer
var _combat_heat := 0.0


func _ready() -> void:
	# keep running while the tree is paused, or the pause menu's own
	# open/move/confirm sounds die with the gameplay they interrupted
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in POOL_SIZE:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_pool.append(p)
	_music = AudioStreamPlayer.new()
	_music.bus = &"Music"
	add_child(_music)
	_combat = AudioStreamPlayer.new()
	_combat.bus = &"Music"
	_combat.volume_db = -40.0
	add_child(_combat)
	Game.toast.connect(_on_toast)


func _process(delta: float) -> void:
	_chain_timer -= delta
	if _chain_timer <= 0.0:
		_chain = 0
	# combat layer fade: in fast when heat rises, out slow once it cools
	_combat_heat = maxf(_combat_heat - delta, 0.0)
	if _combat.playing:
		var target := 0.0 if _combat_heat > 0.0 else -40.0
		var rate := 60.0 if _combat_heat > 0.0 else 14.0
		_combat.volume_db = move_toward(_combat.volume_db, target, rate * delta)
		if _combat.volume_db <= -39.0 and _combat_heat <= 0.0:
			_combat.stop()


func combat_ping() -> void:
	## Any blow given or taken counts as engagement; the layer drops out ~4s
	## after the last one (§14b.2 "drops out 4s after the last enemy").
	_combat_heat = 4.0
	if _combat.playing or _music_track != "region1_perimeter":
		return
	var s := _stream_music("combat")
	if s == null:
		return
	_combat.stream = s
	_combat.volume_db = -40.0
	# phase-lock: combat.wav is authored at the region loop's exact length
	_combat.play(_music.get_playback_position())


func _stream(id: String) -> AudioStream:
	if _cache.has(id):
		return _cache[id]
	var path := SFX_DIR + id + ".wav"
	var s: AudioStream = null
	if ResourceLoader.exists(path):
		s = load(path)
	_cache[id] = s   # cache the miss too: one exists() per id per session
	return s


func play(id: String, pitch := 1.0) -> void:
	var s := _stream(id)
	if s == null:
		return
	for p in _pool:
		if not p.playing:
			_fire(p, s, id, pitch)
			return
	_fire(_pool[0], s, id, pitch)   # every voice busy: steal one


func _fire(p: AudioStreamPlayer, s: AudioStream, id: String, pitch: float) -> void:
	var bus_name: String = BUS.get(id, "SFX")
	p.stream = s
	p.bus = bus_name
	p.pitch_scale = pitch
	p.play()


func play_at(id: String, pos: Vector2, pitch := 1.0) -> void:
	## Positional one-shot; frees itself when done.
	var s := _stream(id)
	if s == null:
		return
	var root := get_tree().current_scene
	if root == null:            # mid-transition: fall back to flat playback
		play(id, pitch)
		return
	var p := AudioStreamPlayer2D.new()
	var bus_name: String = BUS.get(id, "SFX")
	p.stream = s
	p.bus = bus_name
	p.pitch_scale = pitch
	p.max_distance = 640.0
	root.add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()


func play_soul() -> void:
	## §14b.3: each soul in a quick chain lands slightly higher, so reaping a
	## crowd plays as an arpeggio rather than a machine-gunned single note.
	play("soul_collect", 1.0 + 0.07 * float(mini(_chain, 8)))
	_chain += 1
	_chain_timer = 0.8


func _force_loop(s: AudioStream) -> AudioStream:
	## Godot imports plain WAVs with looping DISABLED (it looks for a loop
	## marker inside the file; ours have none). Force engine-level looping —
	## the files are authored with sample-exact loop points.
	if s is AudioStreamWAV:
		var w := s as AudioStreamWAV
		var bpf := 2 if w.format == AudioStreamWAV.FORMAT_16_BITS else 1
		if w.stereo:
			bpf *= 2
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_begin = 0
		w.loop_end = w.data.size() / bpf
	elif s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	elif s is AudioStreamMP3:
		(s as AudioStreamMP3).loop = true
	return s


func _stream_music(track: String) -> AudioStream:
	# mp3 first: an authored song (e.g. from Suno) supersedes the procedural
	# wav of the same track name without deleting the generator's output
	for ext: String in ["mp3", "ogg", "wav"]:
		var path := MUSIC_DIR + track + "." + ext
		if ResourceLoader.exists(path):
			return _force_loop(load(path))
	return null


func music(track: String) -> void:
	if track == _music_track:
		return
	_music_track = track
	_combat.stop()          # the layer belongs to the region track only
	_combat_heat = 0.0
	if track.is_empty():
		_music.stop()
		return
	var s := _stream_music(track)
	if s == null:
		_music.stop()   # track named before its file exists: silence, not a crash
		return
	_music.stream = s
	_music.play()


func attach_loop(parent: Node2D, id: String, volume_db := 0.0) -> void:
	## A looping positional sound that lives and dies with its owner —
	## a drone's rotors, a shrine's room tone.
	var s := _stream(id)
	if s == null:
		return
	var p := AudioStreamPlayer2D.new()
	p.stream = _force_loop(s)
	p.volume_db = volume_db
	p.max_distance = 480.0
	p.bus = &"SFX"
	p.autoplay = true
	parent.add_child(p)


func _on_toast(_msg: String) -> void:
	## §14b.1: Music ducks −6dB while a toast is on screen, then eases back.
	play("toast_blip")
	var idx := AudioServer.get_bus_index("Music")
	if idx < 0:
		return
	if _duck != null:
		_duck.kill()
	AudioServer.set_bus_volume_db(idx, -6.0)
	_duck = create_tween()
	_duck.tween_interval(2.0)
	_duck.tween_method(
		func(v: float) -> void: AudioServer.set_bus_volume_db(idx, v),
		-6.0, 0.0, 0.6)
