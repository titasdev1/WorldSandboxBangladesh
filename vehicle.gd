extends CharacterBody3D

var world
var speed := 4.0
var lane_axis := "z"
var vehicle_type := "Car"
var body_size := Vector3(2.0, 1.0, 4.0)
var body_color := Color("#d94a45")
var is_police := false
var occupied := false
var cruise_speed := 4.0
var steering_velocity := 0.0
var vehicle_camera: Camera3D

func _ready():
    cruise_speed = speed
    var mesh = MeshInstance3D.new()
    var bm = BoxMesh.new()
    bm.size = body_size
    mesh.mesh = bm
    mesh.material_override = make_mat(body_color)
    mesh.position.y = body_size.y * 0.5
    add_child(mesh)

    var cs = CollisionShape3D.new()
    var bs = BoxShape3D.new()
    bs.size = body_size
    cs.shape = bs
    cs.position.y = body_size.y * 0.5
    add_child(cs)

    # A dedicated camera follows the vehicle while the player is driving.
    vehicle_camera = Camera3D.new()
    vehicle_camera.name = "VehicleCamera"
    vehicle_camera.fov = 72.0
    vehicle_camera.near = 0.05
    vehicle_camera.far = 500.0
    vehicle_camera.position = Vector3(0, body_size.y + 3.2, body_size.z * 1.35)
    vehicle_camera.rotation_degrees = Vector3(-12, 180, 0)
    add_child(vehicle_camera)

func make_mat(c: Color):
    var m = StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = 0.65
    return m

func _physics_process(delta):
    if occupied and world and world.player:
        _drive_player_vehicle(delta)
        return

    # Ambient traffic follows its assigned road axis and respects signals.
    if world and not is_police and world.is_red_for_axis(lane_axis, global_position):
        velocity = Vector3.ZERO
        return

    if lane_axis == "z":
        velocity = Vector3(0, 0, speed)
        move_and_slide()
        if position.z > 86:
            position.z = -86
        elif position.z < -86:
            position.z = 86
        rotation.y = 0.0
    else:
        velocity = Vector3(speed, 0, 0)
        move_and_slide()
        if position.x > 86:
            position.x = -86
        elif position.x < -86:
            position.x = 86
        rotation.y = PI * 0.5

    if is_police and world and world.wanted > 0 and world.player:
        var distance = global_position.distance_to(world.player.global_position)
        if distance < 18:
            world.wanted = min(5, world.wanted + 1)

func _drive_player_vehicle(delta):
    var steer = Input.get_axis("move_left", "move_right")
    var throttle = Input.get_axis("move_back", "move_forward")

    # Mobile controls can accelerate/decelerate without needing a keyboard.
    if abs(throttle) > 0.01:
        speed = move_toward(speed, throttle * 14.0, delta * 10.0)
    else:
        speed = move_toward(speed, 0.0, delta * 3.0)

    var steering_strength = clamp(abs(speed) / 8.0, 0.25, 1.0)
    rotation.y -= steer * delta * 1.8 * steering_strength

    velocity = -global_transform.basis.z * speed
    move_and_slide()

    # Keep the hidden player anchored to the vehicle for interaction/save state.
    world.player.global_position = global_position + Vector3(0, 1.0, 0)

    if vehicle_camera:
        vehicle_camera.look_at(global_position - global_transform.basis.z * 8.0 + Vector3.UP * 1.2, Vector3.UP)

    if Input.is_action_just_pressed("interact"):
        exit_player()

func on_hit():
    if world:
        world.cash += 20
        if is_police:
            world.wanted = min(5, world.wanted + 2)

func enter_player(p):
    if occupied or not p:
        return false
    occupied = true
    p.visible = false
    p.set_physics_process(false)
    speed = 0.0
    if p.camera:
        p.camera.current = false
    if vehicle_camera:
        vehicle_camera.current = true
        vehicle_camera.make_current()
    return true

func exit_player():
    if not occupied or not world or not world.player:
        return
    var p = world.player
    occupied = false
    p.visible = true
    p.set_physics_process(true)
    p.global_position = global_position + global_transform.basis.x * 2.5 + Vector3(0, 0.9, 0)
    if p.camera:
        p.camera.current = true
        p.camera.make_current()
    speed = 0.0
