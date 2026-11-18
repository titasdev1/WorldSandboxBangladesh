extends SceneTree

const PLAYER_SCRIPT: Script = preload("res://player.gd")


func _initialize() -> void:
	call_deferred("_run_runtime_input_test")


func _run_runtime_input_test() -> void:
	var stage := Node3D.new()
	stage.name = "PlayerInputRuntimeTest"
	root.add_child(stage)
	current_scene = stage

	var floor_body := StaticBody3D.new()
	floor_body.name = "TestFloor"
	var floor_collision := CollisionShape3D.new()
	var floor_shape := BoxShape3D.new()
	floor_shape.size = Vector3(100.0, 1.0, 100.0)
	floor_collision.shape = floor_shape
	floor_collision.position.y = -0.5
	floor_body.add_child(floor_collision)
	stage.add_child(floor_body)

	var player := CharacterBody3D.new()
	player.name = "TestPlayer"
	player.set_script(PLAYER_SCRIPT)
	var player_collision := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.45
	capsule.height = 1.8
	player_collision.shape = capsule
	player_collision.position.y = 1.0
	player.add_child(player_collision)
	stage.add_child(player)

	# Allow the body to settle onto the floor before testing the buffered jump.
	for _frame in range(36):
		await physics_frame
	if not player.is_on_floor():
		push_error("PLAYER_INPUT_RUNTIME_FAIL: test player did not settle on the floor.")
		quit(1)
		return

	var walk_start := player.global_position
	Input.action_press("move_forward", 1.0)
	for _frame in range(30):
		await physics_frame
	Input.action_release("move_forward")
	var walk_end := player.global_position
	var walk_distance := Vector2(walk_end.x - walk_start.x, walk_end.z - walk_start.z).length()
	if walk_distance < 1.5:
		push_error("PLAYER_INPUT_RUNTIME_FAIL: forward input moved only %.3f m." % walk_distance)
		quit(1)
		return

	var sprint_start := player.global_position
	Input.action_press("move_forward", 1.0)
	Input.action_press("sprint", 1.0)
	for _frame in range(30):
		await physics_frame
	Input.action_release("sprint")
	Input.action_release("move_forward")
	var sprint_end := player.global_position
	var sprint_distance := Vector2(sprint_end.x - sprint_start.x, sprint_end.z - sprint_start.z).length()
	if sprint_distance <= walk_distance * 1.25:
		push_error("PLAYER_INPUT_RUNTIME_FAIL: sprint distance %.3f m was not sufficiently faster than walk %.3f m." % [sprint_distance, walk_distance])
		quit(1)
		return

	if not player.is_on_floor():
		for _frame in range(12):
			await physics_frame
	if not player.is_on_floor():
		push_error("PLAYER_INPUT_RUNTIME_FAIL: player left the floor before jump test.")
		quit(1)
		return

	var jump_start_y := player.global_position.y
	var jump_peak_y := jump_start_y
	player.call("queue_jump")
	for _frame in range(22):
		await physics_frame
		jump_peak_y = maxf(jump_peak_y, player.global_position.y)
	var jump_height := jump_peak_y - jump_start_y
	if jump_height < 0.5:
		push_error("PLAYER_INPUT_RUNTIME_FAIL: buffered jump peak was only %.3f m." % jump_height)
		quit(1)
		return

	print("PLAYER_INPUT_RUNTIME_PASS • walk=%.2fm • sprint=%.2fm • jump_peak=%.2fm" % [
		walk_distance, sprint_distance, jump_height
	])
	quit(0)
