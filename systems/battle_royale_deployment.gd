extends Node

const CARGO_PLANE_PATH := "res://external_content/battle_royale_aircraft/cargo-plane.glb"
const PARACHUTE_PATH := "res://external_content/battle_royale_parachute/a_square_ram_air_canopy.glb"

var world: Node3D
var player: CharacterBody3D
var aircraft: Node3D
var parachute: Node3D
var phase := "inactive"
var phase_time := 0.0
var flight_direction := Vector3.RIGHT
var flight_speed := 48.0
var _propellers: Array[Node3D] = []
var _ramp: Node3D
var _cargo_door: Node3D
var _landing_reported := false
var _plane_resource: PackedScene
var _parachute_resource: PackedScene
var _flight_camera: Camera3D
var _canopy_animation_player: AnimationPlayer
const CANOPY_INFLATION_SECONDS := 0.85


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


func configure(game_world: Node3D) -> void:
	world = game_world


func can_start_solo_deployment() -> bool:
	if not ResourceLoader.exists(CARGO_PLANE_PATH) or not ResourceLoader.exists(PARACHUTE_PATH):
		return false
	_plane_resource = load(CARGO_PLANE_PATH) as PackedScene
	_parachute_resource = load(PARACHUTE_PATH) as PackedScene
	return _plane_resource != null and _parachute_resource != null


func start_solo_deployment() -> bool:
	if not is_instance_valid(world) or not is_instance_valid(world.player):
		return false
	if _plane_resource == null and not can_start_solo_deployment():
		push_warning("BR_DEPLOYMENT_UNAVAILABLE: CC0 plane or authored parachute assembly is missing.")
		world.event_text = "BR DEPLOYMENT UNAVAILABLE • AIRCRAFT OR PARACHUTE ASSET MISSING"
		world.event_time_left = 8.0
		return false
	var packed := _plane_resource

	_reset_previous_deployment()
	player = world.player
	aircraft = packed.instantiate() as Node3D
	if aircraft == null:
		world.event_text = "BR DEPLOYMENT FAILED • INVALID AIRCRAFT ROOT"
		world.event_time_left = 8.0
		return false

	aircraft.name = "A2_BattleRoyale_CargoAircraft"
	world.add_child(aircraft)
	aircraft.global_position = player.global_position + Vector3(-420.0, 360.0, -35.0)
	aircraft.look_at(aircraft.global_position + flight_direction, Vector3.UP)
	_collect_aircraft_parts()
	_open_cargo_ramp()

	# The operator travels with the aircraft as a real character scene. No
	# screenshot overlay or static cut-out is used for the flight sequence.
	player.set_physics_process(false)
	player.set_meta("br_deployment_state", "plane")
	player.visible = true
	var visual := player.get_node_or_null("HumanoidVisual")
	if is_instance_valid(visual) and visual.has_method("set_first_person_view"):
		visual.call("set_first_person_view", false)
	player.reparent(aircraft, true)
	player.position = Vector3(0.0, 1.7, 4.2)
	player.rotation = Vector3.ZERO
	player.call("_play_visual_action", "idle_look")
	_create_flight_overview_camera()
	phase = "flight"
	phase_time = 0.0
	_landing_reported = false
	world.event_text = "BATTLE ROYALE • CARGO FLIGHT • CHOOSE YOUR DROP"
	world.event_time_left = 8.0
	return true


func _collect_aircraft_parts() -> void:
	_propellers.clear()
	_ramp = null
	_cargo_door = null
	if not is_instance_valid(aircraft):
		return
	for child in aircraft.find_children("*", "Node3D", true, false):
		var node := child as Node3D
		var lower := node.name.to_lower()
		if lower.contains("propeller") or lower.contains("prop_"):
			_propellers.append(node)
		if _ramp == null and lower.contains("cargo_ramp"):
			_ramp = node
		if _cargo_door == null and lower.contains("cargo_door"):
			_cargo_door = node


func _open_cargo_ramp() -> void:
	if is_instance_valid(_ramp):
		_ramp.rotation.x = 0.0
		var ramp_tween := create_tween()
		ramp_tween.tween_property(_ramp, "rotation:x", deg_to_rad(-28.4), 0.9).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	if is_instance_valid(_cargo_door):
		_cargo_door.rotation.x = 0.0
		var door_tween := create_tween()
		door_tween.tween_property(_cargo_door, "rotation:x", deg_to_rad(-40.0), 0.85).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func _create_flight_overview_camera() -> void:
	if not is_instance_valid(aircraft):
		return
	_flight_camera = Camera3D.new()
	_flight_camera.name = "BattleRoyaleFlightOverviewCamera"
	_flight_camera.position = Vector3(-12.0, 26.0, 40.0)
	_flight_camera.fov = 52.0
	_flight_camera.near = 0.1
	_flight_camera.far = 2600.0
	aircraft.add_child(_flight_camera)
	_flight_camera.look_at(Vector3(0.0, -25.0, -55.0), Vector3.UP)
	_flight_camera.make_current()


func _close_cargo_ramp() -> void:
	if is_instance_valid(_ramp):
		var tween := create_tween()
		tween.tween_property(_ramp, "rotation:x", 0.0, 1.1).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	if is_instance_valid(_cargo_door):
		var door_tween := create_tween()
		door_tween.tween_property(_cargo_door, "rotation:x", 0.0, 1.0).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)


func jump_from_plane() -> bool:
	if phase != "flight" or not is_instance_valid(player) or not is_instance_valid(aircraft):
		return false
	var drop_position := aircraft.to_global(Vector3(0.0, 1.8, 7.0))
	player.reparent(world, true)
	player.global_position = drop_position
	player.global_rotation = aircraft.global_rotation
	player.velocity = flight_direction * 34.0 + Vector3(0.0, -14.0, 0.0)
	player.set_physics_process(true)
	player.set_meta("br_deployment_state", "freefall")
	player.call("_play_visual_action", "skydive")
	if is_instance_valid(_flight_camera):
		_flight_camera.queue_free()
	_flight_camera = null
	if is_instance_valid(player.camera):
		player.camera.make_current()
	phase = "freefall"
	phase_time = 0.0
	_close_cargo_ramp()
	world.event_text = "FREEFALL • STEER OVER THE DISTRICT • DEPLOY WHEN READY"
	world.event_time_left = 7.0
	return true


func deploy_parachute() -> bool:
	if phase != "freefall" or not is_instance_valid(player):
		return false
	if not ResourceLoader.exists(PARACHUTE_PATH):
		push_warning("BR_PARACHUTE_ASSET_MISSING: refusing to show a placeholder canopy.")
		world.event_text = "PARACHUTE ASSEMBLY NOT AVAILABLE • FREEFALL CONTINUES"
		world.event_time_left = 5.0
		return false
	if _parachute_resource == null:
		_parachute_resource = load(PARACHUTE_PATH) as PackedScene
	var packed := _parachute_resource
	if packed == null:
		world.event_text = "PARACHUTE IMPORT FAILED • FREEFALL CONTINUES"
		world.event_time_left = 5.0
		return false
	var visual := player.get_node_or_null("HumanoidVisual") as Node3D
	if not is_instance_valid(visual):
		return false
	parachute = packed.instantiate() as Node3D
	if parachute == null:
		return false
	parachute.name = "A2_RamAir_Parachute"
	visual.add_child(parachute)
	parachute.position = Vector3(0.0, -0.15, 0.32)
	parachute.rotation = Vector3.ZERO
	parachute.scale = Vector3(0.68, 0.24, 0.68)
	var inflation_tween := create_tween()
	inflation_tween.tween_property(parachute, "scale", Vector3.ONE, CANOPY_INFLATION_SECONDS).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	var canopy_clip := StringName("A2_Parachute_Canopy_Wind_Sway")
	var canopy_animation_nodes := parachute.find_children("*", "AnimationPlayer", true, false)
	_canopy_animation_player = null
	for animation_node in canopy_animation_nodes:
		var candidate_player := animation_node as AnimationPlayer
		if is_instance_valid(candidate_player) and candidate_player.has_animation(canopy_clip):
			_canopy_animation_player = candidate_player
			break
	if is_instance_valid(_canopy_animation_player):
		var animation := _canopy_animation_player.get_animation(canopy_clip)
		animation.loop_mode = Animation.LOOP_LINEAR
		_canopy_animation_player.play(canopy_clip)
	else:
		push_warning("BR_PARACHUTE_WIND_ANIMATION_MISSING: using physics-driven canopy sway.")
	player.set_meta("br_deployment_state", "deploying")
	player.velocity.y = -18.0
	phase = "deploying"
	phase_time = 0.0
	world.event_text = "CANOPY INFLATING • KEEP STEERING TOWARD THE LANDING ZONE"
	world.event_time_left = 7.0
	return true


func notify_player_landed() -> void:
	if _landing_reported or phase not in ["freefall", "deploying", "gliding"]:
		return
	_landing_reported = true
	phase = "landing"
	phase_time = 0.0
	if is_instance_valid(player):
		player.set_physics_process(false)
		player.set_meta("br_deployment_state", "landing")
		player.velocity = Vector3.ZERO
	world.event_text = "LANDING • PREPARE FOR THE FIRST ENGAGEMENT"
	world.event_time_left = 4.0


func _finish_landing() -> void:
	if is_instance_valid(parachute):
		parachute.queue_free()
	parachute = null
	if is_instance_valid(player):
		player.remove_meta("br_deployment_state")
		# Clear the one-shot skydive/idle action so normal locomotion resumes.
		player.remove_meta("character_action_state")
		player.global_position.y = maxf(player.global_position.y, 0.25)
		player.velocity = Vector3.ZERO
		player.set_physics_process(true)
	phase = "landed"
	phase_time = 0.0
	world.event_text = "DROP COMPLETE • SURVIVE • STAY INSIDE THE SAFE ZONE"
	world.event_time_left = 8.0


func get_action_label() -> String:
	match phase:
		"flight":
			return "JUMP FROM PLANE"
		"freefall":
			return "DEPLOY PARACHUTE"
		"deploying":
			return ""
		_:
			return ""


func get_status_text() -> String:
	match phase:
		"flight":
			return "CARGO FLIGHT • ALTITUDE %dm • PICK A DROP" % int(maxf(0.0, aircraft.global_position.y) if is_instance_valid(aircraft) else 0.0)
		"freefall":
			return "FREEFALL • ALTITUDE %dm • DEPLOY CANOPY" % int(maxf(0.0, player.global_position.y) if is_instance_valid(player) else 0.0)
		"deploying":
			return "CANOPY INFLATING • ALTITUDE %dm" % int(maxf(0.0, player.global_position.y) if is_instance_valid(player) else 0.0)
		"gliding":
			return "CANOPY GLIDE • ALTITUDE %dm • STEER" % int(maxf(0.0, player.global_position.y) if is_instance_valid(player) else 0.0)
		"landing":
			return "LANDING"
		"landed":
			return "BR DROP COMPLETE"
		_:
			return ""


func get_phase() -> String:
	return phase


func _process(delta: float) -> void:
	if phase == "inactive" or phase == "landed":
		return
	phase_time += delta

	if phase in ["flight", "freefall", "deploying", "gliding", "landing"] and is_instance_valid(aircraft):
		aircraft.global_position += flight_direction * flight_speed * delta
		for propeller in _propellers:
			if is_instance_valid(propeller):
				propeller.rotate_object_local(Vector3.FORWARD, 24.0 * delta)

	if phase == "deploying" and phase_time >= CANOPY_INFLATION_SECONDS:
		phase = "gliding"
		phase_time = 0.0
		if is_instance_valid(player):
			player.set_meta("br_deployment_state", "gliding")
			player.velocity.y = -8.2
		world.event_text = "CANOPY OPEN • GLIDE AND STEER TOWARD THE LANDING ZONE"
		world.event_time_left = 7.0

	if phase in ["deploying", "gliding"] and is_instance_valid(parachute):
		# Keep the authored canopy wind animation on its internal rig, while the
		# parachute root visibly banks with the same left/right input that steers
		# the player. This makes the glide readable instead of a static loop.
		var steer_axis := Input.get_axis("move_left", "move_right")
		var forward_axis := Input.get_axis("move_back", "move_forward")
		var wind_roll := sin(phase_time * 0.72) * deg_to_rad(1.8)
		var wind_pitch := cos(phase_time * 0.53) * deg_to_rad(1.1)
		var target_roll := -steer_axis * deg_to_rad(12.0) + wind_roll
		var target_pitch := -forward_axis * deg_to_rad(3.2) + wind_pitch
		var bank_blend := clampf(delta * 5.5, 0.0, 1.0)
		parachute.rotation.z = lerp_angle(parachute.rotation.z, target_roll, bank_blend)
		parachute.rotation.x = lerp_angle(parachute.rotation.x, target_pitch, bank_blend)

	if phase == "landing" and phase_time >= 1.0:
		_finish_landing()


func _reset_previous_deployment() -> void:
	if is_instance_valid(parachute):
		parachute.queue_free()
	parachute = null
	if is_instance_valid(aircraft):
		aircraft.queue_free()
	aircraft = null
	if is_instance_valid(_flight_camera):
		_flight_camera.queue_free()
	_flight_camera = null
	_canopy_animation_player = null
	phase = "inactive"
	phase_time = 0.0
	_landing_reported = false
