extends Node3D

var _authored_animation_lookup: Dictionary = {
	"board_vehicle": "BoardVehicle",
	"alight_vehicle": "AlightVehicle",
	"drive_car": "DriveCar",
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
	var drive := Animation.new()
	drive.length = 0.86
	drive.loop_mode = Animation.LOOP_LINEAR
	library.add_animation("DriveCar", drive)
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


func set_vehicle_driver_pose(enabled: bool, _kind: String = "Car") -> bool:
	if enabled:
		var clip := _authored_animation_player.get_animation("DriveCar")
		clip.loop_mode = Animation.LOOP_LINEAR
		return play_action("drive_car")
	var body := get_parent()
	if is_instance_valid(body) and str(body.get_meta("character_action_state", "")) == "drive_car":
		body.remove_meta("character_action_state")
	return true


func set_first_person_view(_enabled: bool) -> void:
	pass
