extends Area2D
## Ability pickup (DESIGN.md §4). Set `id` and `label` before adding to the tree.
## Walk into it: grants the ability, announces it, and disappears.

@export var id := "double_jump"
@export var label := "PRIVILEGE ESCALATION"

var _t := 0.0
var _core: ColorRect


func _ready() -> void:
	var shape := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 14.0
	shape.shape = c
	add_child(shape)
	collision_layer = 0
	collision_mask = 2  # player only
	body_entered.connect(_on_touch)

	# ponytail: a glowing diamond stands in until a per-ability icon exists
	var halo := ColorRect.new()
	halo.size = Vector2(22, 22)
	halo.position = Vector2(-11, -11)
	halo.color = Color("1e33d9")
	halo.rotation = PI / 4.0
	add_child(halo)
	_core = ColorRect.new()
	_core.size = Vector2(12, 12)
	_core.position = Vector2(-6, -6)
	_core.color = Color("35c6f4")
	_core.rotation = PI / 4.0
	add_child(_core)


func _process(delta: float) -> void:
	_t += delta
	position.y += sin(_t * 2.4) * 0.14          # slow hover
	_core.modulate.a = 0.65 + 0.35 * sin(_t * 5.0)  # pulse


func _on_touch(body: Node) -> void:
	if not body.is_in_group("player"):
		return
	Game.grant(id)
	Game.toast.emit("ABILITY ACQUIRED · %s" % label)
	Fx.burst(global_position, Color("35c6f4"))
	Fx.shake(3.0)
	Fx.hitstop(6)
	queue_free()
