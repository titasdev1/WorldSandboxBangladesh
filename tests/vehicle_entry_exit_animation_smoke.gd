extends SceneTree

const PLAYER_SCRIPT := "res://player.gd"
const VEHICLE_SCRIPT := "res://vehicle.gd"
const PLAYER_VISUAL_STUB := "res://tests/vehicle_entry_exit_visual_stub.gd"
const WORLD_STUB := "res://tests/vehicle_entry_exit_world_stub.gd"


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var test_world := Node3D.new()
	test_world.name = "VehicleEntryExitSmokeWorld"
	test_world.set_script(load(WORLD_STUB))
	root.add_child(test_world)

	var player := CharacterBody3D.new()
	player.name = "Player"
	player.set_script(load(PLAYER_SCRIPT))
	player.set("world", test_world)
	var collision := CollisionShape3D.new()
	collision.name = "CollisionShape3D"
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.8
	capsule.radius = 0.32
	collision.shape = capsule
	collision.position.y = 0.9
	player.add_child(collision)
	var visual := Node3D.new()
	visual.name = "HumanoidVisual"
	visual.set_script(load(PLAYER_VISUAL_STUB))
	player.add_child(visual)
	test_world.add_child(player)
	test_world.player = player
	await process_frame
	player.call("set_camera_view_mode", "first_person")
	var camera_was_first_person := String(player.get("camera_view_mode")) == "first_person"

	var vehicle := CharacterBody3D.new()
	vehicle.name = "SmokeCar"
	vehicle.set_script(load(VEHICLE_SCRIPT))
	vehicle.set("world", test_world)
	test_world.add_child(vehicle)
	await process_frame
	await physics_frame

	if not bool(vehicle.call("enter_player", player)):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: enter_player rejected a nearby player.")
		quit(1)
		return
	if not bool(vehicle.get("_vehicle_transitioning")) or bool(player.is_physics_processing()):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: board animation phase did not begin or player input was not locked.")
		quit(1)
		return
	var player_visual := player.get_node("HumanoidVisual")
	var action_state := String(player.get_meta("character_action_state", ""))
	if action_state != "board_vehicle" or player_visual.get("played_actions").size() != 1:
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: authored board_vehicle clip was not requested.")
		quit(1)
		return

	# Repeated interaction during the board transition must not create a second body.
	if bool(vehicle.call("enter_player", player)):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: duplicate board input was accepted during transition.")
		quit(1)
		return

	await create_timer(0.68).timeout
	if not bool(vehicle.get("occupied")) or bool(player.visible) or not is_instance_valid(test_world.occupied_vehicle):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: board transition did not transfer control to the rigid-body vehicle.")
		quit(1)
		return

	vehicle.call("exit_player")
	if not bool(vehicle.get("_vehicle_transitioning")) or not bool(player.visible):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: alight animation phase did not show the player.")
		quit(1)
		return
	action_state = String(player.get_meta("character_action_state", ""))
	if action_state != "alight_vehicle" or player_visual.get("played_actions").size() != 2:
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: authored alight_vehicle clip was not requested.")
		quit(1)
		return
	if bool(vehicle.get("enter_player", null)):
		pass

	await create_timer(0.72).timeout
	if bool(vehicle.get("occupied")) or bool(vehicle.get("_vehicle_transitioning")) or not bool(player.is_physics_processing()):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: alight transition did not restore player control.")
		quit(1)
		return
	if String(player.get("camera_view_mode")) != "first_person" or not player.camera.current:
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: original first-person camera mode was not restored after exiting.")
		quit(1)
		return
	if is_instance_valid(test_world.occupied_vehicle):
		push_error("VEHICLE_ACTION_RUNTIME_FAIL: world still references an occupied vehicle after exit.")
		quit(1)
		return

	print("VEHICLE_ENTRY_EXIT_ANIMATION_PASS • board_clip=true • alight_clip=true • duplicate_input_blocked=true • first_person_restored=%s" % str(camera_was_first_person))
	quit(0)
