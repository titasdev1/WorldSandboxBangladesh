extends Node3D

var _authored_animation_lookup: Dictionary = {
	"board_vehicle": "BoardVehicle",
	"alight_vehicle": "AlightVehicle",
}
var _authored_animation_player: AnimationPlayer
var played_actions: Array[String] = []


func _ready() -> void:
	_authored_animation_player = AnimationPlayer.new()
	_authored_animation_player.name = "SmokeAnimationPlayer"
	var library := AnimationLibrary.new()
	var board := Animation.new()
	board.length = 0.48
	library.add_animation("BoardVehicle", board)
	var alight := Animation.new()
	alight.length = 0.52
	library.add_animation("AlightVehicle", alight)
	_authored_animation_player.add_animation_library("", library)
	add_child(_authored_animation_player)


func play_action(action_name: String) -> bool:
	var animation_name := String(_authored_animation_lookup.get(action_name, ""))
	if animation_name.is_empty():
		return false
	played_actions.append(action_name)
	_authored_animation_player.play(animation_name)
	get_parent().set_meta("character_action_state", action_name)
	return true


func set_first_person_view(_enabled: bool) -> void:
	pass
