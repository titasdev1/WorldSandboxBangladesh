extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var crouch_speed := 3.5
var gravity := 20.0
var jump_velocity := 7.0
var health := 100
var crouched := false
var camera_yaw := 0.0
var camera_pitch := -18.0
var camera_sensitivity := 0.12
var camera_pivot: Node3D
var camera: Camera3D

func _ready():
 camera_pivot = Node3D.new()
 camera_pivot.name = "CameraPivot"
 camera_pivot.position = Vector3(0, 2.2, 0)
 add_child(camera_pivot)
 camera = Camera3D.new()
 camera.name = "ThirdPersonCamera"
 camera.position = Vector3(0, 2.8, 7.8)
 camera.rotation_degrees = Vector3(-18, 180, 0)
 camera.current = true
 camera.fov = 68
 camera_pivot.add_child(camera)

func _unhandled_input(event):
 if event is InputEventScreenDrag:
  if event.position.x > 300.0:
   rotate_camera(event.relative.x, event.relative.y)
 elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
  rotate_camera(event.relative.x, event.relative.y)
 elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
  Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func rotate_camera(dx: float, dy: float):
 camera_yaw -= dx * camera_sensitivity
 camera_pitch = clamp(camera_pitch - dy * camera_sensitivity, -55.0, 25.0)
 camera_pivot.rotation_degrees = Vector3(0, camera_yaw, 0)
 camera.rotation_degrees = Vector3(camera_pitch, 180, 0)

func _physics_process(delta):
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

 if Input.is_action_just_pressed("crouch"):
  crouched = !crouched
  camera_pivot.position.y = 1.45 if crouched else 2.2

 move_and_slide()
 position.x = clamp(position.x, -84.0, 84.0)
 position.z = clamp(position.z, -84.0, 84.0)

 if Input.is_action_just_pressed("fire") and world:
  world.try_fire()
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
