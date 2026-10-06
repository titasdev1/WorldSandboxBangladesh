extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var crouch_speed := 3.5
var gravity := 20.0
var jump_velocity := 7.0
var health := 100
var ammo := 30
var reserve_ammo := 120
var reload_time := 0.0
var crouched := false
var camera_yaw := 0.0
var camera_pitch := -14.0
var camera_distance := 8.5
var camera_sensitivity := 0.12
var camera: Camera3D

func _ready():
    # One authoritative camera, directly owned by the player.
    # This avoids the nested-pivot/camera state that caused the blank build.
    camera = Camera3D.new()
    camera.name = "ThirdPersonCamera"
    camera.fov = 68.0
    camera.near = 0.05
    camera.far = 500.0
    camera.current = true
    add_child(camera)
    camera.make_current()
    _update_camera()

func _input(event):
    if event is InputEventScreenDrag:
        # Right half of the landscape viewport is camera-look territory.
        if event.position.x > get_viewport().get_visible_rect().size.x * 0.42:
            rotate_camera(event.relative.x, event.relative.y)
    elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
        rotate_camera(event.relative.x, event.relative.y)
    elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func rotate_camera(dx: float, dy: float):
    camera_yaw -= dx * camera_sensitivity
    camera_pitch = clamp(camera_pitch - dy * camera_sensitivity, -55.0, 25.0)

func _update_camera():
    if not camera:
        return
    var yaw := deg_to_rad(camera_yaw)
    var pitch := deg_to_rad(camera_pitch)
    var target := global_position + Vector3(0, 1.35 if not crouched else 1.0, 0)
    var offset := Vector3(
        sin(yaw) * cos(pitch) * camera_distance,
        -sin(pitch) * camera_distance + 0.8,
        cos(yaw) * cos(pitch) * camera_distance
    )
    camera.global_position = target + offset
    camera.look_at(target, Vector3.UP)

func _physics_process(delta):
    if reload_time > 0.0:
        reload_time -= delta
        if reload_time <= 0.0:
            var needed := 30 - ammo
            var loaded := min(needed, reserve_ammo)
            ammo += loaded
            reserve_ammo -= loaded
    var input_vec = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var local_dir = Vector3(input_vec.x, 0, input_vec.y)
    var dir = local_dir.normalized()
    if dir.length() > 0.01:
        dir = dir.rotated(Vector3.UP, deg_to_rad(camera_yaw))
    var current_speed = crouch_speed if crouched else (sprint_speed if Input.is_action_pressed("sprint") else speed)
    velocity.x = dir.x * current_speed
    velocity.z = dir.z * current_speed

    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump") and not crouched:
        velocity.y = jump_velocity
    else:
        velocity.y = -0.5

    move_and_slide()
    position.x = clamp(position.x, -84.0, 84.0)
    position.z = clamp(position.z, -84.0, 84.0)
    _update_camera()

    if Input.is_action_just_pressed("crouch"):
        crouched = !crouched
        _update_camera()

    if Input.is_action_just_pressed("fire") and world:
        if reload_time <= 0.0 and ammo > 0:
            ammo -= 1
            world.try_fire()
    if Input.is_action_just_pressed("interact") and reload_time <= 0.0 and ammo < 30 and reserve_ammo > 0:
        reload_time = 1.35
    if Input.is_action_just_pressed("interact") and world:
        interact()

func interact():
    if not world:
        return
    if position.distance_to(Vector3(42, 0, 42)) < 15:
        world.cash = max(0, world.cash - world.bargain_offer)
        world.bargain_offer = min(world.fare_requested, world.bargain_offer + 10)
    elif position.distance_to(Vector3(30, 0, -30)) < 18:
        world.cash += 100
    else:
        world.try_vehicle_interaction()

func take_damage(amount: int):
    health = max(0, health - amount)
    if health <= 0 and world:
        world.respawn_player()

func heal(amount: int):
    health = min(100, health + amount)
