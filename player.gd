extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var gravity := 20.0
var health := 100
var ammo := 30
var reserve_ammo := 120
var reload_time := 0.0
var camera: Camera3D
var camera_yaw := 0.0
var camera_pitch := -28.0

func _ready():
 camera = Camera3D.new()
 camera.name = "ThirdPersonCamera"
 camera.position = Vector3(0, 6.2, 9.5)
 camera.rotation_degrees = Vector3(-28, 180, 0)
 camera.fov = 68.0
 camera.near = 0.05
 camera.far = 500.0
 camera.current = true
 add_child(camera)
 camera.make_current()

func _input(event):
 if event is InputEventScreenDrag:
  if event.position.x > get_viewport().get_visible_rect().size.x * 0.42:
   camera_yaw -= event.relative.x * 0.12
   camera_pitch = clamp(camera_pitch - event.relative.y * 0.12, -55.0, 15.0)
 elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
  camera_yaw -= event.relative.x * 0.12
  camera_pitch = clamp(camera_pitch - event.relative.y * 0.12, -55.0, 15.0)

func _update_camera():
 if not camera:
  return
 var yaw := deg_to_rad(camera_yaw)
 var pitch := deg_to_rad(camera_pitch)
 var target := global_position + Vector3(0, 1.0, 0)
 var offset := Vector3(sin(yaw) * cos(pitch) * 9.5, -sin(pitch) * 9.5 + 1.0, cos(yaw) * cos(pitch) * 9.5)
 camera.global_position = target + offset
 camera.look_at(target, Vector3.UP)

func _physics_process(delta):
 if reload_time > 0.0:
  reload_time -= delta
  if reload_time <= 0.0:
   var loaded := min(30 - ammo, reserve_ammo)
   ammo += loaded
   reserve_ammo -= loaded
 var input_vec = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
 var dir = Vector3(input_vec.x, 0, input_vec.y).normalized()
 var current_speed = sprint_speed if Input.is_action_pressed("sprint") else speed
 velocity.x = dir.x * current_speed
 velocity.z = dir.z * current_speed
 if not is_on_floor():
  velocity.y -= gravity * delta
 else:
  velocity.y = -0.5
 move_and_slide()
 # The playable world now extends to the 600 m outer districts.
 position.x = clamp(position.x, -285.0, 285.0)
 position.z = clamp(position.z, -285.0, 285.0)
 _update_camera()
 if Input.is_action_just_pressed("fire") and world and ammo > 0 and reload_time <= 0.0:
  ammo -= 1
  world.try_fire()
 if Input.is_action_just_pressed("interact") and world:
  if ammo < 30 and reserve_ammo > 0:
   reload_time = 1.35
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
