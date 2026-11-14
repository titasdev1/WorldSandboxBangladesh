extends SceneTree

const JOYSTICK_SCRIPT: Script = preload("res://virtual_stick.gd")
const STICK_POSITION := Vector2(24.0, 472.0)
const STICK_SIZE := Vector2(220.0, 220.0)
const STICK_CENTER := Vector2(110.0, 110.0)
const STICK_RADIUS := 88.0


func _initialize() -> void:
	call_deferred("_run_mobile_joystick_test")


func _run_mobile_joystick_test() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "MobileJoystickRuntimeTest"
	root.add_child(canvas)

	var stick := Control.new()
	stick.name = "MovementStick"
	stick.position = STICK_POSITION
	stick.size = STICK_SIZE
	stick.set_script(JOYSTICK_SCRIPT)
	canvas.add_child(stick)
	await process_frame

	# These event positions are already in viewport coordinates, so set
	# in_local_coords=true. Godot then performs the viewport-to-Control-local
	# conversion before calling Control._gui_input().
	var viewport := root.get_viewport()
	var center_touch := InputEventScreenTouch.new()
	center_touch.index = 3
	center_touch.pressed = true
	center_touch.position = STICK_POSITION + STICK_CENTER
	viewport.push_input(center_touch, true)
	await process_frame
	if not _assert_strength("move_right", 0.0, 0.02, "neutral center touch"):
		return

	var right_drag := InputEventScreenDrag.new()
	right_drag.index = 3
	right_drag.position = STICK_POSITION + STICK_CENTER + Vector2(STICK_RADIUS, 0.0)
	viewport.push_input(right_drag, true)
	await process_frame
	if not _assert_strength("move_right", 0.95, 1.0, "right drag"):
		return
	if not _assert_strength("move_forward", 0.0, 0.02, "right drag vertical leakage"):
		return

	var forward_drag := InputEventScreenDrag.new()
	forward_drag.index = 3
	forward_drag.position = STICK_POSITION + STICK_CENTER + Vector2(0.0, -STICK_RADIUS)
	viewport.push_input(forward_drag, true)
	await process_frame
	if not _assert_strength("move_forward", 0.95, 1.0, "forward drag"):
		return
	if not _assert_strength("move_right", 0.0, 0.02, "forward drag horizontal leakage"):
		return

	var back_drag := InputEventScreenDrag.new()
	back_drag.index = 3
	back_drag.position = STICK_POSITION + STICK_CENTER + Vector2(0.0, STICK_RADIUS)
	viewport.push_input(back_drag, true)
	await process_frame
	if not _assert_strength("move_back", 0.95, 1.0, "backward drag"):
		return

	var release := InputEventScreenTouch.new()
	release.index = 3
	release.pressed = false
	release.position = STICK_POSITION + STICK_CENTER
	viewport.push_input(release, true)
	await process_frame
	for action in ["move_left", "move_right", "move_forward", "move_back"]:
		if not _assert_strength(action, 0.0, 0.02, "touch release"):
			return

	print("MOBILE_JOYSTICK_RUNTIME_PASS • right • forward • backward • neutral release")
	canvas.queue_free()
	quit(0)


func _assert_strength(action_name: StringName, minimum: float, maximum: float, phase: String) -> bool:
	var strength := Input.get_action_strength(action_name)
	if strength < minimum or strength > maximum:
		push_error("MOBILE_JOYSTICK_RUNTIME_FAIL: %s had %.3f strength during %s (expected %.3f..%.3f)." % [
			action_name, strength, phase, minimum, maximum
		])
		quit(1)
		return false
	return true
