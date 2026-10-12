extends Control
## Circular, analog mobile movement stick. It feeds the existing InputMap actions,
## so keyboard movement continues to work and the player code needs no platform fork.

const RADIUS := 88.0
const KNOB_RADIUS := 35.0
const DEADZONE := 0.14

var _touch_index := -1
var _stick_vector := Vector2.ZERO
var _center := Vector2(110.0, 110.0)
var _active := false

func _ready() -> void:
	custom_minimum_size = Vector2(220.0, 220.0)
	size = custom_minimum_size
	mouse_filter = Control.MOUSE_FILTER_STOP
	z_index = 20
	set_process_input(true)
	queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _touch_index == -1 and Rect2(Vector2.ZERO, size).has_point(event.position - global_position):
			_touch_index = event.index
			_active = true
			_update_stick(event.position - global_position)
			accept_event()
		elif not event.pressed and event.index == _touch_index:
			_release_stick()
			accept_event()
	elif event is InputEventScreenDrag and event.index == _touch_index:
		_update_stick(event.position - global_position)
		accept_event()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed and _touch_index == -1 and Rect2(Vector2.ZERO, size).has_point(event.position):
			_touch_index = -2
			_active = true
			_update_stick(event.position)
			accept_event()
		elif not event.pressed and _touch_index == -2:
			_release_stick()
			accept_event()
	elif event is InputEventMouseMotion and _touch_index == -2:
		_update_stick(event.position)
		accept_event()

func _update_stick(local_point: Vector2) -> void:
	var offset := local_point - _center
	if offset.length() > RADIUS:
		offset = offset.normalized() * RADIUS
	_stick_vector = offset / RADIUS
	if _stick_vector.length() < DEADZONE:
		_stick_vector = Vector2.ZERO
	_sync_actions()
	queue_redraw()

func _release_stick() -> void:
	_touch_index = -1
	_active = false
	_stick_vector = Vector2.ZERO
	_sync_actions()
	queue_redraw()

func _sync_actions() -> void:
	# Input.get_vector() understands action strengths and normalizes diagonals.
	_set_action("move_left", maxf(0.0, -_stick_vector.x))
	_set_action("move_right", maxf(0.0, _stick_vector.x))
	_set_action("move_forward", maxf(0.0, -_stick_vector.y))
	_set_action("move_back", maxf(0.0, _stick_vector.y))

func _set_action(action_name: StringName, strength: float) -> void:
	if strength > 0.01:
		Input.action_press(action_name, strength)
	else:
		Input.action_release(action_name)

func _draw() -> void:
	# Soft dark base, clear rim, and a thumb knob that follows the finger.
	var base_color := Color(0.025, 0.04, 0.055, 0.48 if not _active else 0.68)
	var rim_color := Color(0.72, 0.88, 0.96, 0.72)
	draw_circle(_center, RADIUS + 5.0, Color(0.0, 0.0, 0.0, 0.25))
	draw_circle(_center, RADIUS, base_color)
	draw_arc(_center, RADIUS, 0.0, TAU, 64, rim_color, 3.0, true)
	var knob_center := _center + _stick_vector * RADIUS
	draw_circle(knob_center, KNOB_RADIUS + 3.0, Color(0.0, 0.0, 0.0, 0.25))
	draw_circle(knob_center, KNOB_RADIUS, Color(0.25, 0.72, 0.88, 0.88 if _active else 0.72))
	draw_arc(knob_center, KNOB_RADIUS, 0.0, TAU, 48, Color(0.88, 0.97, 1.0, 0.95), 2.0, true)
