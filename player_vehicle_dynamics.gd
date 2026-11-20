extends RigidBody3D
class_name PlayerVehicleDynamics

const WHEEL_RADIUS := 0.34
const GEAR_RATIOS: Array[float] = [3.35,2.18,1.55,1.16,0.91,0.74]
const FINAL_DRIVE := 3.2
const REDLINE_RPM := 6800.0

# A small raycast suspension/tire model replaces the previous single-force
# steering approximation. The wheel anchor is chassis-local; the visual wheel
# is allowed to travel relative to that anchor as the suspension compresses.
const SUSPENSION_REST_LENGTH := 0.30
const SUSPENSION_TRAVEL := 0.18
const SUSPENSION_RAY_START := 0.45
const SUSPENSION_TARGET_SAG := 0.14
const CORNERING_STIFFNESS := 2400.0
const DRY_TIRE_GRIP := 1.12
const WET_TIRE_GRIP := 0.78
const BRAKE_DECELERATION := 9.0
const YAW_STABILITY := 0.55
const ROAD_COLLISION_MASK := 1
const MAX_SIMULATED_WHEELS := 6

var vehicle_wrapper: Node3D
var vehicle_type := "Car"
var fuel := 100.0
var engine_rpm := 900.0
var current_gear := 1
var speed := 0.0
var drift_score := 0.0
var vehicle_damage := 0.0
var vehicle_camera_mode := "third_person"
var vehicle_camera: Camera3D
var vehicle_first_person_camera: Camera3D
var wheel_pivots: Array[Node3D] = []
var _wheel_states: Array[Dictionary] = []
var _steering := 0.0
var _empty_notice_sent := false
var _last_speed := 0.0
var debug_physics_tick_count := 0
var debug_last_throttle := 0.0
var debug_contact_wheels := 0
var debug_wheel_count := 0
var debug_grounded_wheels := 0
var debug_last_steering := 0.0
var debug_last_suspension_force := 0.0
var debug_last_lateral_force := 0.0
var debug_last_drive_force := 0.0


func configure(wrapper: Node3D, kind: String, dimensions: Vector3) -> void:
    vehicle_wrapper = wrapper
    vehicle_type = kind
    mass = 1380.0
    match vehicle_type.to_lower():
        "cng":
            mass = 930.0
        "rickshaw":
            mass = 280.0
        "bus":
            mass = 5600.0
        "motorcycle", "bike":
            mass = 205.0
        "police":
            mass = 1560.0

    center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
    center_of_mass = Vector3(0.0, -dimensions.y * 0.23, 0.0)
    gravity_scale = 1.0
    linear_damp = 0.045
    angular_damp = 0.75
    can_sleep = false
    continuous_cd = true
    collision_layer = 2
    collision_mask = ROAD_COLLISION_MASK

    var collision := CollisionShape3D.new()
    collision.name = "DrivingChassisCollision"
    var box := BoxShape3D.new()
    box.size = Vector3(dimensions.x * 0.90, maxf(0.46, dimensions.y * 0.66), dimensions.z * 0.88)
    collision.shape = box
    # Keep the chassis clear of the road so the tyres and suspension, rather
    # than a large friction box, carry the vehicle's weight.
    collision.position.y = dimensions.y * 0.52

    var chassis_contact_material := PhysicsMaterial.new()
    chassis_contact_material.friction = 0.05
    chassis_contact_material.bounce = 0.0
    chassis_contact_material.rough = false
    physics_material_override = chassis_contact_material
    add_child(collision)

    wheel_pivots.clear()
    _wheel_states.clear()
    _collect_wheels(self)
    _build_wheel_states(dimensions)

    vehicle_camera = get_node_or_null("VehicleCamera") as Camera3D
    vehicle_first_person_camera = get_node_or_null("VehicleFirstPersonCamera") as Camera3D
    if is_instance_valid(vehicle_first_person_camera):
        vehicle_first_person_camera.current = false
    if is_instance_valid(vehicle_camera):
        vehicle_camera.current = true


func _collect_wheels(node: Node) -> void:
    for child in node.get_children():
        if child is Node3D:
            var child_node := child as Node3D
            var lower_name := child_node.name.to_lower()
            if child_node.name == "RollingWheel" or lower_name.contains("wheel") or lower_name.contains("tire"):
                if not wheel_pivots.has(child_node):
                    wheel_pivots.append(child_node)
        _collect_wheels(child)


func _wheel_radius_for_kind() -> float:
    match vehicle_type.to_lower():
        "bus":
            return 0.48
        "rickshaw":
            return 0.23
        "cng":
            return 0.28
        "motorcycle", "bike":
            return 0.29
        _:
            return 0.31


func _target_wheel_count() -> int:
    match vehicle_type.to_lower():
        "cng", "rickshaw":
            return 3
        "motorcycle", "bike":
            return 2
        _:
            return 4


func _has_wheel_position(records: Array[Dictionary], position: Vector3) -> bool:
    for record in records:
        var existing: Vector3 = record["position"]
        if existing.distance_to(position) < 0.12:
            return true
    return false


func _append_center_wheel(candidates: Array[Dictionary], selected: Array[Dictionary]) -> void:
    var best_record: Dictionary = {}
    var best_distance := INF
    for record in candidates:
        var position: Vector3 = record["position"]
        var lateral_distance := absf(position.x)
        if lateral_distance < best_distance and not _has_wheel_position(selected, position):
            best_distance = lateral_distance
            best_record = record
    if not best_record.is_empty():
        selected.append(best_record)


func _append_lateral_wheels(candidates: Array[Dictionary], wanted: int, selected: Array[Dictionary]) -> void:
    if wanted <= 0:
        return
    var left_record: Dictionary = {}
    var right_record: Dictionary = {}
    var left_x := INF
    var right_x := -INF
    for record in candidates:
        var position: Vector3 = record["position"]
        if position.x < left_x:
            left_x = position.x
            left_record = record
        if position.x > right_x:
            right_x = position.x
            right_record = record

    var added := 0
    if not left_record.is_empty():
        var left_position: Vector3 = left_record["position"]
        if not _has_wheel_position(selected, left_position):
            selected.append(left_record)
            added += 1
    if added < wanted and not right_record.is_empty():
        var right_position: Vector3 = right_record["position"]
        if not _has_wheel_position(selected, right_position):
            selected.append(right_record)
            added += 1

    for record in candidates:
        if added >= wanted:
            break
        var position: Vector3 = record["position"]
        if not _has_wheel_position(selected, position):
            selected.append(record)
            added += 1


func _select_wheel_candidates(candidates: Array[Dictionary], target_count: int) -> Array[Dictionary]:
    var front: Array[Dictionary] = []
    var rear: Array[Dictionary] = []
    for record in candidates:
        var position: Vector3 = record["position"]
        if position.z < 0.0:
            front.append(record)
        else:
            rear.append(record)

    var selected: Array[Dictionary] = []
    if target_count == 2:
        _append_center_wheel(front, selected)
        _append_center_wheel(rear, selected)
    elif target_count == 3:
        _append_center_wheel(front, selected)
        _append_lateral_wheels(rear, 2, selected)
    else:
        _append_lateral_wheels(front, 2, selected)
        _append_lateral_wheels(rear, 2, selected)

    for record in candidates:
        if selected.size() >= target_count:
            break
        var position: Vector3 = record["position"]
        if not _has_wheel_position(selected, position):
            selected.append(record)
    return selected


func _fallback_wheel_positions(dimensions: Vector3) -> Array[Vector3]:
    var radius := _wheel_radius_for_kind()
    var wheel_y := radius
    var half_track := maxf(0.30, dimensions.x * 0.40)
    var front_z := -maxf(0.42, dimensions.z * 0.33)
    var rear_z := maxf(0.42, dimensions.z * 0.33)
    var result: Array[Vector3] = []

    match vehicle_type.to_lower():
        "motorcycle", "bike":
            result.append(Vector3(0.0, wheel_y, front_z))
            result.append(Vector3(0.0, wheel_y, rear_z))
        "cng", "rickshaw":
            result.append(Vector3(0.0, wheel_y, front_z))
            result.append(Vector3(-half_track, wheel_y, rear_z))
            result.append(Vector3(half_track, wheel_y, rear_z))
        _:
            result.append(Vector3(-half_track, wheel_y, front_z))
            result.append(Vector3(half_track, wheel_y, front_z))
            result.append(Vector3(-half_track, wheel_y, rear_z))
            result.append(Vector3(half_track, wheel_y, rear_z))
    return result


func _build_wheel_states(dimensions: Vector3) -> void:
    _wheel_states.clear()
    var target_count := mini(_target_wheel_count(), MAX_SIMULATED_WHEELS)
    var candidates: Array[Dictionary] = []
    var seen_positions: Array[Vector3] = []

    for visual in wheel_pivots:
        if not is_instance_valid(visual):
            continue
        var local_position := to_local(visual.global_position)
        var duplicate := false
        for previous in seen_positions:
            if previous.distance_to(local_position) < 0.12:
                duplicate = true
                break
        if duplicate:
            continue
        seen_positions.append(local_position)
        candidates.append({"visual": visual, "position": local_position})

    var selected := _select_wheel_candidates(candidates, target_count)
    wheel_pivots.clear()
    for record in selected:
        var visual: Node3D = record["visual"] as Node3D
        var local_position: Vector3 = record["position"]
        wheel_pivots.append(visual)
        _wheel_states.append({
            "visual": visual,
            "rest_position": local_position,
            "base_rotation": visual.rotation,
            "front": local_position.z < 0.0,
            "driven": vehicle_type.to_lower() == "police" or local_position.z >= 0.0,
            "radius": _wheel_radius_for_kind(),
            "spin": 0.0,
            "compression": 0.0,
            "extension": SUSPENSION_TRAVEL
        })

    # Fill missing imported wheel names/layout positions with deterministic
    # invisible anchors, while keeping exactly 2/3/4 simulated wheels.
    for fallback_position in _fallback_wheel_positions(dimensions):
        if _wheel_states.size() >= target_count:
            break
        var covered := false
        for state in _wheel_states:
            var rest_position: Vector3 = state["rest_position"]
            if rest_position.distance_to(fallback_position) < 0.18:
                covered = true
                break
        if covered:
            continue
        var anchor := Node3D.new()
        anchor.name = "PhysicsWheelAnchor_%02d" % _wheel_states.size()
        anchor.position = fallback_position
        add_child(anchor)
        wheel_pivots.append(anchor)
        _wheel_states.append({
            "visual": anchor,
            "rest_position": fallback_position,
            "base_rotation": anchor.rotation,
            "front": fallback_position.z < 0.0,
            "driven": vehicle_type.to_lower() == "police" or fallback_position.z >= 0.0,
            "radius": _wheel_radius_for_kind(),
            "spin": 0.0,
            "compression": 0.0,
            "extension": SUSPENSION_TRAVEL
        })

    debug_wheel_count = _wheel_states.size()
    debug_grounded_wheels = 0
    debug_contact_wheels = 0

func _physics_process(delta: float) -> void:
    debug_physics_tick_count += 1
    var steer := Input.get_axis("move_left", "move_right")
    var throttle := Input.get_action_strength("vehicle_accelerate")
    debug_last_throttle = throttle
    var brake_input := Input.get_action_strength("vehicle_brake")
    var reverse_input := Input.get_action_strength("vehicle_reverse")
    var handbrake := Input.get_action_strength("vehicle_handbrake")

    # The circular movement stick remains a fallback for the accelerator and
    # reverse; dedicated touch pedals work independently.
    if throttle < 0.05 and reverse_input < 0.05:
        throttle = Input.get_action_strength("move_forward")
        reverse_input = Input.get_action_strength("move_back")
        debug_last_throttle = throttle

    var max_speed := _maximum_speed_kmh() / 3.6
    var forward := -global_transform.basis.z.normalized()
    var forward_speed := linear_velocity.dot(forward)
    speed = linear_velocity.length()

    var wheel_rpm := absf(forward_speed) / (TAU * _wheel_radius_for_kind()) * 60.0
    engine_rpm = clampf(wheel_rpm * GEAR_RATIOS[clampi(current_gear - 1, 0, GEAR_RATIOS.size() - 1)] * FINAL_DRIVE, 900.0, REDLINE_RPM)
    if engine_rpm > 6350.0 and current_gear < GEAR_RATIOS.size():
        current_gear += 1
    elif engine_rpm < 1850.0 and current_gear > 1:
        current_gear -= 1
    var ratio: float = GEAR_RATIOS[clampi(current_gear - 1, 0, GEAR_RATIOS.size() - 1)]
    engine_rpm = clampf(wheel_rpm * ratio * FINAL_DRIVE + 900.0, 900.0, REDLINE_RPM)

    var max_torque := 280.0
    if vehicle_type.to_lower() == "bus":
        max_torque = 650.0
    elif vehicle_type.to_lower() == "motorcycle":
        max_torque = 75.0
    elif vehicle_type.to_lower() == "rickshaw":
        max_torque = 42.0
    elif vehicle_type.to_lower() == "cng":
        max_torque = 120.0
    var torque_curve := lerpf(0.75, 1.0, clampf(engine_rpm / REDLINE_RPM, 0.0, 1.0))
    var engine_force := max_torque * ratio * FINAL_DRIVE / _wheel_radius_for_kind() * torque_curve

    var drive_input := 0.0
    var requested_brake := brake_input
    if fuel > 0.01 and throttle > 0.01:
        if forward_speed < -0.75:
            requested_brake = maxf(requested_brake, throttle)
        else:
            drive_input = throttle
        fuel = maxf(0.0, fuel - delta * (0.15 + absf(forward_speed) * 0.025))
        _empty_notice_sent = false
    elif reverse_input > 0.01 and absf(forward_speed) < 4.0 and fuel > 0.01:
        drive_input = -0.42 * reverse_input
        fuel = maxf(0.0, fuel - delta * 0.10)

    if absf(forward_speed) >= max_speed and signf(forward_speed) == signf(drive_input):
        drive_input = 0.0

    var speed_fraction := clampf(absf(forward_speed) / maxf(max_speed, 1.0), 0.0, 1.0)
    var target_steer := steer * 0.49 * clampf(1.0 - speed_fraction * 0.66, 0.22, 1.0)
    _steering = move_toward(_steering, target_steer, delta * (2.8 + speed_fraction * 1.7))
    debug_last_steering = _steering

    var wet := false
    if is_instance_valid(vehicle_wrapper):
        var game_world := vehicle_wrapper.get_parent()
        wet = is_instance_valid(game_world) and (game_world.get("rain") == true)

    _simulate_wheel_forces(engine_force * drive_input, requested_brake, handbrake, wet)

    if handbrake > 0.01 and absf(forward_speed) > 5.0 and absf(steer) > 0.12:
        drift_score += absf(linear_velocity.dot(global_transform.basis.x.normalized())) * absf(forward_speed) * delta * 1.4

    if fuel <= 0.01:
        if not _empty_notice_sent and is_instance_valid(vehicle_wrapper):
            var game_world := vehicle_wrapper.get_parent()
            if is_instance_valid(game_world):
                game_world.set("event_text", "FUEL EMPTY • REFUEL OR EXIT VEHICLE")
                game_world.set("event_time_left", 5.0)
            _empty_notice_sent = true

    # The tyre forces act at their individual contact patches. Drag and mild
    # yaw stability remain chassis-level forces, not substitutes for tyre grip.
    var air_drag := -linear_velocity * linear_velocity.length() * 0.32
    var rolling_drag := -linear_velocity * mass * 0.012
    apply_central_force(air_drag + rolling_drag)
    apply_torque(Vector3.UP * -angular_velocity.y * mass * YAW_STABILITY)

    speed = linear_velocity.length()
    _animate_wheels(delta, forward_speed)
    _update_cameras(delta)

    if Input.is_action_just_pressed("interact") and is_instance_valid(vehicle_wrapper) and vehicle_wrapper.has_method("exit_player"):
        vehicle_wrapper.call("exit_player")


func _velocity_at_world_point(world_point: Vector3) -> Vector3:
    return linear_velocity + angular_velocity.cross(world_point - global_position)


func _simulate_wheel_forces(drive_force: float, brake_input: float, handbrake: float, wet: bool) -> void:
    debug_grounded_wheels = 0
    debug_contact_wheels = 0
    debug_last_suspension_force = 0.0
    debug_last_lateral_force = 0.0
    debug_last_drive_force = 0.0
    if _wheel_states.is_empty() or not is_inside_tree():
        return

    var wheel_count := mini(_wheel_states.size(), MAX_SIMULATED_WHEELS)
    var driven_wheel_count := 0
    var rear_wheel_count := 0
    for index in range(wheel_count):
        var state: Dictionary = _wheel_states[index]
        if state.get("driven", false):
            driven_wheel_count += 1
        if not state.get("front", false):
            rear_wheel_count += 1
    driven_wheel_count = maxi(1, driven_wheel_count)
    rear_wheel_count = maxi(1, rear_wheel_count)

    var static_load: float = mass * 9.81 / float(wheel_count)
    var spring_stiffness: float = static_load / SUSPENSION_TARGET_SAG
    var spring_damping: float = 2.0 * sqrt(spring_stiffness * (mass / float(wheel_count))) * 0.72
    var space_state := get_world_3d().direct_space_state

    for index in range(wheel_count):
        var state: Dictionary = _wheel_states[index]
        var rest_position: Vector3 = state["rest_position"]
        var anchor_position := rest_position + Vector3.UP * SUSPENSION_REST_LENGTH
        var wheel_radius: float = float(state["radius"])
        var cast_origin := global_transform * (anchor_position + Vector3.UP * SUSPENSION_RAY_START)
        var cast_length := SUSPENSION_RAY_START + wheel_radius + SUSPENSION_REST_LENGTH + SUSPENSION_TRAVEL + 0.08
        var cast_end := cast_origin + Vector3.DOWN * cast_length
        var query := PhysicsRayQueryParameters3D.create(cast_origin, cast_end, ROAD_COLLISION_MASK)
        query.exclude = [get_rid()]
        query.collide_with_areas = false
        query.collide_with_bodies = true
        var hit: Dictionary = space_state.intersect_ray(query)

        if hit.is_empty():
            state["compression"] = 0.0
            state["extension"] = SUSPENSION_TRAVEL
            continue

        var hit_position: Vector3 = hit.get("position", Vector3.ZERO)
        var surface_normal: Vector3 = hit.get("normal", Vector3.UP)
        surface_normal = surface_normal.normalized()
        var hit_distance := cast_origin.distance_to(hit_position)
        var suspension_length := hit_distance - SUSPENSION_RAY_START - wheel_radius
        if suspension_length > SUSPENSION_REST_LENGTH + SUSPENSION_TRAVEL:
            state["compression"] = 0.0
            state["extension"] = SUSPENSION_TRAVEL
            continue

        debug_grounded_wheels += 1
        debug_contact_wheels = debug_grounded_wheels
        var compression := clampf(SUSPENSION_REST_LENGTH - suspension_length, 0.0, SUSPENSION_TRAVEL)
        var extension := clampf(suspension_length - SUSPENSION_REST_LENGTH, 0.0, SUSPENSION_TRAVEL)
        state["compression"] = compression
        state["extension"] = extension

        var local_contact := to_local(hit_position)
        var contact_velocity: Vector3 = _velocity_at_world_point(hit_position)
        var suspension_velocity: float = contact_velocity.dot(surface_normal)
        var spring_force: float = spring_stiffness * compression - spring_damping * suspension_velocity
        spring_force = clampf(spring_force, 0.0, static_load * 3.2)
        if spring_force <= 0.1:
            continue

        debug_last_suspension_force += spring_force
        apply_force(surface_normal * spring_force, local_contact)

        var is_front: bool = state.get("front", false)
        var is_driven: bool = state.get("driven", false)
        var steer_angle := _steering if is_front else 0.0
        var local_wheel_forward := Vector3(sin(steer_angle), 0.0, -cos(steer_angle))
        var wheel_forward := (global_transform.basis * local_wheel_forward).normalized()
        wheel_forward = (wheel_forward - surface_normal * wheel_forward.dot(surface_normal)).normalized()
        var wheel_right := wheel_forward.cross(surface_normal).normalized()
        var longitudinal_speed: float = contact_velocity.dot(wheel_forward)
        var lateral_speed: float = contact_velocity.dot(wheel_right)

        var tire_grip := WET_TIRE_GRIP if wet else DRY_TIRE_GRIP
        if not is_front and handbrake > 0.01:
            tire_grip *= lerpf(1.0, 0.26, clampf(handbrake, 0.0, 1.0))
        var grip_limit := spring_force * tire_grip

        var lateral_force := -lateral_speed * CORNERING_STIFFNESS
        var longitudinal_force := 0.0
        if is_driven:
            longitudinal_force += drive_force / float(driven_wheel_count)
        if brake_input > 0.01 and absf(longitudinal_speed) > 0.03:
            longitudinal_force -= signf(longitudinal_speed) * (mass * BRAKE_DECELERATION / float(wheel_count)) * clampf(brake_input, 0.0, 1.0)
        if not is_front and handbrake > 0.01 and absf(longitudinal_speed) > 0.03:
            longitudinal_force -= signf(longitudinal_speed) * (mass * 5.5 / float(rear_wheel_count)) * clampf(handbrake, 0.0, 1.0)

        # A friction circle caps combined longitudinal and lateral tyre force.
        var requested_force_length := Vector2(longitudinal_force, lateral_force).length()
        if requested_force_length > grip_limit and requested_force_length > 0.001:
            var grip_scale := grip_limit / requested_force_length
            longitudinal_force *= grip_scale
            lateral_force *= grip_scale

        debug_last_lateral_force += absf(lateral_force)
        debug_last_drive_force += absf(longitudinal_force)
        apply_force(wheel_forward * longitudinal_force + wheel_right * lateral_force, local_contact)

func _maximum_speed_kmh() -> float:
    match vehicle_type.to_lower():
        "cng":
            return 72.0
        "rickshaw":
            return 34.0
        "bus":
            return 86.0
        "motorcycle", "bike":
            return 138.0
        "police":
            return 172.0
        _:
            return 165.0


func _animate_wheels(delta: float, forward_speed: float) -> void:
    for state in _wheel_states:
        var visual := state.get("visual") as Node3D
        if not is_instance_valid(visual):
            continue
        var radius: float = maxf(0.05, float(state.get("radius", WHEEL_RADIUS)))
        var spin_value: float = float(state.get("spin", 0.0)) + forward_speed / radius * delta
        state["spin"] = spin_value
        var base_rotation: Vector3 = state.get("base_rotation", visual.rotation)
        var wheel_rotation := base_rotation
        wheel_rotation.x += spin_value
        if state.get("front", false):
            wheel_rotation.y = base_rotation.y - _steering
        visual.rotation = wheel_rotation

        var rest_position: Vector3 = state["rest_position"]
        var displacement := float(state.get("compression", 0.0)) - float(state.get("extension", SUSPENSION_TRAVEL))
        visual.global_position = global_transform * (rest_position + Vector3.UP * displacement)


func _update_cameras(delta: float) -> void:
    if vehicle_camera_mode == "third_person" and is_instance_valid(vehicle_camera):
        var target := global_position + global_transform.basis * Vector3(0.0, 3.2, 7.3)
        vehicle_camera.global_position = vehicle_camera.global_position.lerp(target, 1.0 - exp(-delta * 4.5))
        vehicle_camera.look_at(global_position + Vector3(0, 1.0, 0), Vector3.UP)


func toggle_vehicle_camera_mode() -> String:
    vehicle_camera_mode = "first_person" if vehicle_camera_mode == "third_person" else "third_person"
    if vehicle_camera_mode == "first_person" and is_instance_valid(vehicle_first_person_camera):
        vehicle_first_person_camera.make_current()
    elif is_instance_valid(vehicle_camera):
        vehicle_camera.make_current()
    return vehicle_camera_mode


func refuel(amount: float) -> bool:
    if amount <= 0.0 or fuel >= 99.9:
        return false
    fuel = minf(100.0, fuel + amount)
    _empty_notice_sent = false
    return true
