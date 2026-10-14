extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var extreme_speed := 55.0 # 198 km/h in game-world units; optional free-roam boost
var extreme_speed_enabled := false
var gravity := 20.0
var jump_velocity := 7.2
var health := 100
var stamina := 100.0
var max_stamina := 100.0
var stamina_drain := 28.0
var stamina_recovery := 19.0
var ammo := 30
var reserve_ammo := 120
var reload_time := 0.0
var camera: Camera3D
var camera_yaw := 0.0
var camera_pitch := -28.0
var _collision_shape: CollisionShape3D
var _humanoid_visual: Node3D
var _is_crouching := false

func _ready():
 _collision_shape = get_node_or_null("CollisionShape3D") as CollisionShape3D
 _humanoid_visual = get_node_or_null("HumanoidVisual") as Node3D
 camera = Camera3D.new()
 camera.name = "ThirdPersonCamera"
 camera.position = Vector3(0, 5.2, 7.4)
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
 var target := global_position + Vector3(0, 1.0 if not _is_crouching else 0.72, 0)
 var offset := Vector3(sin(yaw) * cos(pitch) * 7.4, -sin(pitch) * 7.4 + 0.8, cos(yaw) * cos(pitch) * 7.4)
 var desired_position := target + offset
 # Keep the third-person camera outside walls and building interiors.
 var query := PhysicsRayQueryParameters3D.create(target, desired_position, 1, [get_rid()])
 var hit := get_world_3d().direct_space_state.intersect_ray(query)
 if not hit.is_empty():
  desired_position = hit.position + hit.normal * 0.22
 camera.global_position = desired_position
 camera.look_at(target, Vector3.UP)

func _set_crouching(should_crouch: bool) -> void:
 if _is_crouching == should_crouch:
  return
 _is_crouching = should_crouch
 if _collision_shape and _collision_shape.shape is CapsuleShape3D:
  var capsule := _collision_shape.shape as CapsuleShape3D
  capsule.height = 1.22 if _is_crouching else 1.8
  _collision_shape.position.y = capsule.height * 0.5
 if _humanoid_visual:
  _humanoid_visual.scale.y = 0.78 if _is_crouching else 1.0

func _physics_process(delta):
 if reload_time > 0.0:
  reload_time -= delta
  if reload_time <= 0.0:
   var loaded: int = mini(30 - ammo, reserve_ammo)
   ammo += loaded
   reserve_ammo -= loaded

 var input_vec: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
 var yaw := deg_to_rad(camera_yaw)
 var forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
 var right := Vector3(cos(yaw), 0.0, -sin(yaw))
 var dir := (right * input_vec.x + forward * -input_vec.y).normalized()

 _set_crouching(Input.is_action_pressed("crouch"))
 var wants_sprint := Input.is_action_pressed("sprint") and not _is_crouching and input_vec.length_squared() > 0.02 and stamina > 0.0
 if wants_sprint:
  stamina = maxf(0.0, stamina - stamina_drain * delta)
 else:
  stamina = minf(max_stamina, stamina + stamina_recovery * delta)
 var current_speed: float = 3.1 if _is_crouching else (extreme_speed if extreme_speed_enabled else (sprint_speed if wants_sprint else speed))
 var acceleration: float = (100.0 if extreme_speed_enabled else (28.0 if dir.length_squared() > 0.001 else 34.0))
 velocity.x = move_toward(velocity.x, dir.x * current_speed, acceleration * delta)
 velocity.z = move_toward(velocity.z, dir.z * current_speed, acceleration * delta)

 if dir.length_squared() > 0.001:
  rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), minf(1.0, delta * 12.0))

 if not is_on_floor():
  velocity.y -= gravity * delta
 else:
  velocity.y = -0.5
  if Input.is_action_just_pressed("jump") and not _is_crouching:
   velocity.y = jump_velocity

 move_and_slide()
 var movement_bound := 1100.0 if world and world.has_meta("osm_road_paths") else 285.0
 position.x = clamp(position.x, -movement_bound, movement_bound)
 position.z = clamp(position.z, -movement_bound, movement_bound)
 _update_camera()

 if Input.is_action_just_pressed("fire") and world and ammo > 0 and reload_time <= 0.0:
  ammo -= 1
  world.try_fire()
 if Input.is_action_just_pressed("interact") and world:
  if ammo < 30 and reserve_ammo > 0:
   reload_time = 1.35
  interact()

func set_extreme_speed_enabled(enabled: bool) -> void:
 extreme_speed_enabled = enabled

func interact():
 if not world:
  return
 if world.has_method("try_street_vendor") and world.try_street_vendor(global_position):
  return
 if world.has_method("try_osm_shop_interaction") and world.try_osm_shop_interaction(global_position):
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
