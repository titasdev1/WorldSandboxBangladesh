extends "res://systems/combat_mode_controller.gd"

var _smoke_enemy_id := 0


func _spawn_enemy(at: Vector3, _is_practice_target: bool) -> void:
	_smoke_enemy_id += 1
	var entity := Node3D.new()
	entity.name = "SmokeCombatOperator_%02d" % _smoke_enemy_id
	entity.add_to_group("combat_enemy")
	world.add_child(entity)
	entity.global_position = at
