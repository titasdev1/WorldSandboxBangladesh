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
 var camera_distance := 9.5
 if world:
  var interior_node: Node = world.get("interior_factory")
  if is_instance_valid(interior_node) and interior_node.has_method("is_inside") and bool(interior_node.call("is_inside")):
   camera_distance = 4.2
 # Camera stays behind the player. Its horizontal offset and movement basis
 # must use opposite signs: forward movement points from camera toward target.
 var offset := Vector3(sin(yaw) * cos(pitch) * camera_distance, -sin(pitch) * camera_distance + 1.0, cos(yaw) * cos(pitch) * camera_distance)
 camera.global_position = target + offset
 camera.look_at(target, Vector3.UP)

func _physics_process(delta):
 if reload_time > 0.0:
  reload_time -= delta
  if reload_time <= 0.0:
   var loaded: int = mini(30 - ammo, reserve_ammo)
   ammo += loaded
   reserve_ammo -= loaded

 # Four-button movement is camera-relative. Godot's get_vector returns
 # negative Y for "forward"; convert it to a positive forward amount here.
 var input_vec: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
 var yaw := deg_to_rad(camera_yaw)
 # The camera is positioned at (+sin(yaw), +cos(yaw)) behind the player.
 # Forward therefore points away from that offset, not toward it.
 var forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
 var right := Vector3(cos(yaw), 0.0, -sin(yaw))
 var dir := (right * input_vec.x + forward * -input_vec.y).normalized()
 var current_speed: float = sprint_speed if Input.is_action_pressed("sprint") else speed
 velocity.x = dir.x * current_speed
 velocity.z = dir.z * current_speed
 # Rotate the avatar to face travel direction; -Z is the character forward axis.
 if dir.length_squared() > 0.001:
  rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), minf(1.0, delta * 12.0))
 if not is_on_floor():
  velocity.y -= gravity * delta
 else:
  velocity.y = -0.5
 move_and_slide()
 # The real-data Greater Dhaka map streams geographically positioned tiles.
 # Keep the smaller bounds only for the fictional fallback city.
 if world and bool(world.get("real_dhaka_loaded")):
  var bounds: Dictionary = {}
  var map_loader: Node = world.get("real_dhaka_loader")
  if is_instance_valid(map_loader) and map_loader.has_method("get_world_bounds"):
   bounds = map_loader.call("get_world_bounds")
  if not bounds.is_empty():
   position.x = clamp(position.x, float(bounds.get("min_x", -12000.0)), float(bounds.get("max_x", 12000.0)))
   position.z = clamp(position.z, float(bounds.get("min_z", -10000.0)), float(bounds.get("max_z", 16800.0)))
  else:
   position.x = clamp(position.x, -12000.0, 12000.0)
   position.z = clamp(position.z, -10000.0, 16800.0)
 else:
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
 if world.has_method("try_interior_interaction") and world.try_interior_interaction(global_position):
  return
 if world.has_method("try_street_vendor") and world.try_street_vendor(global_position):
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
