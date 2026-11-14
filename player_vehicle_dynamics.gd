extends RigidBody3D
class_name PlayerVehicleDynamics

const WHEEL_RADIUS := 0.34
const GEAR_RATIOS: Array[float] = [3.35,2.18,1.55,1.16,0.91,0.74]
const FINAL_DRIVE := 3.2
const REDLINE_RPM := 6800.0

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
var _steering := 0.0
var _empty_notice_sent := false
var _last_speed := 0.0

func configure(wrapper: Node3D,kind: String,dimensions: Vector3) -> void:
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
    center_of_mass = Vector3(0.0,-dimensions.y*0.23,0.0)
    gravity_scale = 1.0
    linear_damp = 0.045
    angular_damp = 1.1
    can_sleep = false
    continuous_cd = true
    collision_layer = 2
    collision_mask = 1
    var collision := CollisionShape3D.new()
    collision.name = "DrivingChassisCollision"
    var box := BoxShape3D.new()
    box.size = Vector3(dimensions.x*0.90,maxf(0.46,dimensions.y*0.66),dimensions.z*0.88)
    collision.shape = box
    collision.position.y = dimensions.y*0.38
    add_child(collision)
    vehicle_camera = get_node_or_null("VehicleCamera") as Camera3D
    vehicle_first_person_camera = get_node_or_null("VehicleFirstPersonCamera") as Camera3D
    _collect_wheels(self)
    if is_instance_valid(vehicle_first_person_camera):
        vehicle_first_person_camera.current = false
    if is_instance_valid(vehicle_camera):
        vehicle_camera.current = true

func _collect_wheels(node: Node) -> void:
    for child in node.get_children():
        if child is Node3D:
            var child_node := child as Node3D
            if child_node.name == "RollingWheel" or child_node.name.to_lower().contains("wheel"):
                if not wheel_pivots.has(child_node):
                    wheel_pivots.append(child_node)
        _collect_wheels(child)

func _physics_process(delta: float) -> void:
    var steer := Input.get_axis("move_left","move_right")
    var throttle := Input.get_action_strength("vehicle_accelerate")
    var brake_input := Input.get_action_strength("vehicle_brake")
    var reverse_input := Input.get_action_strength("vehicle_reverse")
    var handbrake := Input.get_action_strength("vehicle_handbrake")

    # Existing circular movement stick remains a fallback for the accelerator
    # and reverse; dedicated touch pedals work independently.
    if throttle < 0.05 and reverse_input < 0.05:
        throttle = Input.get_action_strength("move_forward")
        reverse_input = Input.get_action_strength("move_back")

    var max_speed := _maximum_speed_kmh()/3.6
    var forward := -global_transform.basis.z.normalized()
    var right := global_transform.basis.x.normalized()
    var forward_speed := linear_velocity.dot(forward)
    speed = linear_velocity.length()

    var wheel_rpm := absf(forward_speed)/(TAU*WHEEL_RADIUS)*60.0
    engine_rpm = clampf(wheel_rpm*GEAR_RATIOS[clampi(current_gear-1,0,GEAR_RATIOS.size()-1)]*FINAL_DRIVE,900.0,REDLINE_RPM)
    if engine_rpm > 6350.0 and current_gear < GEAR_RATIOS.size():
        current_gear += 1
    elif engine_rpm < 1850.0 and current_gear > 1:
        current_gear -= 1
    var ratio: float = GEAR_RATIOS[clampi(current_gear-1,0,GEAR_RATIOS.size()-1)]
    engine_rpm = clampf(wheel_rpm*ratio*FINAL_DRIVE+900.0,900.0,REDLINE_RPM)

    var max_torque := 280.0
    if vehicle_type.to_lower()=="bus":
        max_torque = 650.0
    elif vehicle_type.to_lower()=="motorcycle":
        max_torque = 75.0
    elif vehicle_type.to_lower()=="rickshaw":
        max_torque = 42.0
    elif vehicle_type.to_lower()=="cng":
        max_torque = 120.0
    var torque_curve := lerpf(0.75,1.0,clampf(engine_rpm/REDLINE_RPM,0.0,1.0))
    var engine_force := max_torque*ratio*FINAL_DRIVE/WHEEL_RADIUS*torque_curve

    if fuel > 0.01 and throttle > 0.01:
        if forward_speed < -0.75:
            apply_central_force(forward*mass*12.0)
        else:
            apply_central_force(forward*engine_force*throttle)
        fuel = maxf(0.0,fuel-delta*(0.15+absf(forward_speed)*0.025))
        _empty_notice_sent = false
    elif reverse_input > 0.01 and absf(forward_speed)<4.0 and fuel>0.01:
        apply_central_force(-forward*engine_force*0.42*reverse_input)
        fuel = maxf(0.0,fuel-delta*0.10)

    if brake_input > 0.01:
        apply_central_force(-forward*signf(forward_speed)*mass*13.5*brake_input)
    if handbrake > 0.01:
        var rear_grip := 0.22
        apply_central_force(-right*linear_velocity.dot(right)*mass*lerpf(1.0,8.0,handbrake)*rear_grip)
        if absf(forward_speed)>5.0 and absf(steer)>0.12:
            drift_score += absf(linear_velocity.dot(right))*absf(forward_speed)*delta*1.4

    if fuel <= 0.01:
        if not _empty_notice_sent and is_instance_valid(vehicle_wrapper):
            var game_world := vehicle_wrapper.get_parent()
            if is_instance_valid(game_world):
                game_world.set("event_text","FUEL EMPTY • REFUEL OR EXIT VEHICLE")
                game_world.set("event_time_left",5.0)
            _empty_notice_sent = true

    # Tire lateral force, wet-road grip and aerodynamic drag act on the rigid body.
    var lateral_speed := linear_velocity.dot(right)
    var wet := false
    if is_instance_valid(vehicle_wrapper):
        var game_world := vehicle_wrapper.get_parent()
        wet = is_instance_valid(game_world) and bool(game_world.get("rain"))
    var lateral_grip := 10.5 if not wet else 7.2
    if handbrake > 0.1:
        lateral_grip *= lerpf(1.0,0.34,handbrake)
    apply_central_force(-right*lateral_speed*mass*lateral_grip)

    var speed_fraction := clampf(absf(forward_speed)/maxf(max_speed,1.0),0.0,1.0)
    var target_steer := steer*0.50*clampf(1.0-speed_fraction*0.45,0.45,1.0)
    _steering = move_toward(_steering,target_steer,delta*(2.5+speed_fraction*1.8))
    apply_torque(Vector3.UP*_steering*mass*2.8*clampf(absf(forward_speed)/4.0,0.18,1.0))

    var air_drag := -linear_velocity*linear_velocity.length()*0.32
    var rolling_drag := -linear_velocity*mass*0.012
    apply_central_force(air_drag+rolling_drag)

    speed = linear_velocity.length()
    _animate_wheels(delta,forward_speed)
    _update_cameras(delta)

    if Input.is_action_just_pressed("interact") and is_instance_valid(vehicle_wrapper) and vehicle_wrapper.has_method("exit_player"):
        vehicle_wrapper.call("exit_player")

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

func _animate_wheels(delta: float,forward_speed: float) -> void:
    var spin := forward_speed/WHEEL_RADIUS*delta
    for wheel in wheel_pivots:
        if not is_instance_valid(wheel):
            continue
        wheel.rotation.x += spin

func _update_cameras(delta: float) -> void:
    if vehicle_camera_mode == "third_person" and is_instance_valid(vehicle_camera):
        var target := global_position+global_transform.basis*Vector3(0.0,3.2,7.3)
        vehicle_camera.global_position = vehicle_camera.global_position.lerp(target,1.0-exp(-delta*4.5))
        vehicle_camera.look_at(global_position+Vector3(0,1.0,0),Vector3.UP)

func toggle_vehicle_camera_mode() -> String:
    vehicle_camera_mode = "first_person" if vehicle_camera_mode=="third_person" else "third_person"
    if vehicle_camera_mode=="first_person" and is_instance_valid(vehicle_first_person_camera):
        vehicle_first_person_camera.make_current()
    elif is_instance_valid(vehicle_camera):
        vehicle_camera.make_current()
    return vehicle_camera_mode

func refuel(amount: float) -> bool:
    if amount<=0.0 or fuel>=99.9:
        return false
    fuel = minf(100.0,fuel+amount)
    _empty_notice_sent = false
    return true
