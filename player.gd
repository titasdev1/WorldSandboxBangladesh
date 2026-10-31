extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var gravity := 20.0
var health := 100
var stamina := 100.0
var ammo := 30
var reserve_ammo := 120
var reload_time := 0.0
var fire_cooldown := 0.0
var camera: Camera3D
var camera_yaw := 0.0
var camera_sensitivity := 0.12
var camera_pitch := -22.0
# First-person look starts level; the third-person orbit retains its raised camera angle.
var first_person_pitch := 0.0
# Recoil is an additive camera impulse, separate from the player's look input.
# This lets sustained fire kick the sight upward without corrupting saved sensitivity
# or the player's manually controlled camera angles.
var camera_recoil_pitch := 0.0
var camera_recoil_yaw := 0.0

var camera_view_mode := "third_person"
var jump_velocity := 7.2
var crouch_speed := 3.2
var _collision_shape: CollisionShape3D
var _standing_capsule_height := 1.8
const HUMANOID_BASE_SCALE := Vector3(0.90, 0.90, 0.90)
var _is_crouched := false

func set_camera_view_mode(mode: String) -> void:
 camera_view_mode = "first_person" if mode == "first_person" else "third_person"
 var visual := get_node_or_null("HumanoidVisual")
 if visual:
  visual.visible = camera_view_mode != "first_person"
 _update_camera()

func toggle_camera_view_mode() -> String:
 set_camera_view_mode("first_person" if camera_view_mode == "third_person" else "third_person")
 return camera_view_mode

func _ready():
 var controls_config := ConfigFile.new()
 if controls_config.load("user://graphics_settings.cfg") == OK:
  camera_sensitivity = clampf(float(controls_config.get_value("controls", "look_sensitivity", 0.12)), 0.05, 0.25)
 _collision_shape = get_node_or_null("CollisionShape3D") as CollisionShape3D
 if _collision_shape and _collision_shape.shape is CapsuleShape3D:
  _standing_capsule_height = (_collision_shape.shape as CapsuleShape3D).height
 camera = Camera3D.new()
 camera.name = "ThirdPersonCamera"
 camera.position = Vector3(0, 4.1, 6.2)
 camera.rotation_degrees = Vector3(-28, 180, 0)
 camera.fov = 68.0
 camera.near = 0.05
 camera.far = 500.0
 camera.current = true
 add_child(camera)
 camera.make_current()

func _unhandled_input(event):
 # Let on-screen HUD controls consume their own touch gestures first. Only
 # unhandled drags on the open right-hand look area should rotate the camera;
 # dragging FIRE/AIM/RELOAD must not accidentally move the view.
 if event is InputEventScreenDrag:
  if event.position.x > get_viewport().get_visible_rect().size.x * 0.42:
   camera_yaw -= event.relative.x * camera_sensitivity
   camera_pitch = clamp(camera_pitch - event.relative.y * camera_sensitivity, -55.0, 15.0)
   first_person_pitch = clampf(first_person_pitch - event.relative.y * camera_sensitivity, -65.0, 65.0)
 elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
  camera_yaw -= event.relative.x * camera_sensitivity
  camera_pitch = clamp(camera_pitch - event.relative.y * camera_sensitivity, -55.0, 15.0)
  first_person_pitch = clampf(first_person_pitch - event.relative.y * camera_sensitivity, -65.0, 65.0)

func _update_camera():
 if not camera:
  return
 var yaw := deg_to_rad(camera_yaw + camera_recoil_yaw)
 var effective_pitch := clampf(camera_pitch + camera_recoil_pitch, -55.0, 15.0)
 var pitch := deg_to_rad(effective_pitch)
 var target := global_position + Vector3(0, 1.0, 0)
 if camera_view_mode == "first_person":
  # In first-person, positive recoil rotates the view a few degrees upward.
  var eye := global_position + Vector3(0, 1.58, 0)
  camera.global_position = eye
  camera.fov = 50.0 if Input.is_action_pressed("aim") else 68.0
  camera.global_rotation = Vector3(deg_to_rad(first_person_pitch + camera_recoil_pitch), yaw, 0.0)
  return
 var camera_distance := 4.4 if Input.is_action_pressed("aim") else 6.2
 if world:
  var interior_node: Node = world.get("interior_factory")
  if is_instance_valid(interior_node) and interior_node.has_method("is_inside") and bool(interior_node.call("is_inside")):
   camera_distance = 4.2
 # Camera stays behind the player. Its horizontal offset and movement basis
 # must use opposite signs: forward movement points from camera toward target.
 var offset := Vector3(sin(yaw) * cos(pitch) * camera_distance, -sin(pitch) * camera_distance + 1.0, cos(yaw) * cos(pitch) * camera_distance)
 camera.global_position = target + offset
 camera.fov = 56.0 if Input.is_action_pressed("aim") else 68.0
 camera.look_at(target, Vector3.UP)

func _physics_process(delta):
 if reload_time > 0.0:
  reload_time -= delta
  if reload_time <= 0.0:
   var loaded: int = mini(30 - ammo, reserve_ammo)
   ammo += loaded
   reserve_ammo -= loaded
   if world:
    world.event_text = "RELOAD COMPLETE • %d/%d" % [ammo, reserve_ammo]
    world.event_time_left = 1.8
 fire_cooldown = maxf(0.0, fire_cooldown - delta)
 camera_recoil_pitch = move_toward(camera_recoil_pitch, 0.0, 3.8 * delta)
 camera_recoil_yaw = move_toward(camera_recoil_yaw, 0.0, 3.0 * delta)

 # Four-button movement is camera-relative. Godot's get_vector returns
 # negative Y for "forward"; convert it to a positive forward amount here.
 var input_vec: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
 var yaw := deg_to_rad(camera_yaw)
 # The camera is positioned at (+sin(yaw), +cos(yaw)) behind the player.
 # Forward therefore points away from that offset, not toward it.
 var forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
 var right := Vector3(cos(yaw), 0.0, -sin(yaw))
 var dir := (right * input_vec.x + forward * -input_vec.y).normalized()
 # Hold crouch to lower the profile and reduce movement speed; sprint is disabled while crouched.
 _set_crouched(Input.is_action_pressed("crouch"))
 var sprinting := Input.is_action_pressed("sprint") and not _is_crouched and dir.length_squared() > 0.001 and stamina > 0.1
 if sprinting:
  stamina = maxf(0.0, stamina - 24.0 * delta)
 else:
  stamina = minf(100.0, stamina + 12.0 * delta)
 var current_speed: float = crouch_speed if _is_crouched else (sprint_speed if sprinting else speed)
 velocity.x = dir.x * current_speed
 velocity.z = dir.z * current_speed
 if Input.is_action_just_pressed("jump") and is_on_floor() and not _is_crouched:
  velocity.y = jump_velocity
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
 if Input.is_action_pressed("fire") and world and ammo > 0 and reload_time <= 0.0 and fire_cooldown <= 0.0:
  ammo -= 1
  _apply_weapon_recoil()
  world.try_fire()
  fire_cooldown = 0.13 if Input.is_action_pressed("aim") else 0.17
  if ammo == 0 and reserve_ammo > 0:
   reload_time = 1.35
   world.event_text = "MAGAZINE EMPTY • RELOADING"
   world.event_time_left = 1.8
 if Input.is_action_just_pressed("reload") and ammo < 30 and reserve_ammo > 0 and reload_time <= 0.0:
  reload_time = 1.35
  world.event_text = "RELOADING"
  world.event_time_left = 1.5
 if Input.is_action_just_pressed("interact") and world:
  interact()

func _apply_weapon_recoil() -> void:
 # Accurate taps settle quickly; sustained automatic fire accumulates a readable
 # upward impulse. Hip-fire has slightly more spread than aimed fire.
 camera_recoil_pitch = minf(
  camera_recoil_pitch + (0.72 if Input.is_action_pressed("aim") else 0.98),
  4.8
 )
 camera_recoil_yaw = clampf(camera_recoil_yaw + randf_range(-0.18, 0.18), -1.1, 1.1)


func _set_crouched(should_crouch: bool) -> void:
 if _is_crouched == should_crouch:
  return
 _is_crouched = should_crouch
 if _collision_shape and _collision_shape.shape is CapsuleShape3D:
  var capsule := _collision_shape.shape as CapsuleShape3D
  capsule.height = _standing_capsule_height * 0.64 if _is_crouched else _standing_capsule_height
  _collision_shape.position.y = capsule.height * 0.5 + 0.1
 var visual := get_node_or_null("HumanoidVisual") as Node3D
 if visual:
  # Preserve the model's measured base scale while crouching; setting only Y to
  # 1.0 used to undo part of the character normalization when standing back up.
  visual.scale = HUMANOID_BASE_SCALE * Vector3(1.0, 0.72, 1.0) if _is_crouched else HUMANOID_BASE_SCALE
  visual.position.y = 0.0

func interact():
 if not world:
  return
 # A vehicle within reach owns the Interact button before nearby buildings.
 # This prevents a building-anchor overlap from making parked cars undrivable.
 if world.has_method("try_vehicle_interaction") and world.try_vehicle_interaction():
  return
 if world.has_method("try_street_vendor") and world.try_street_vendor(global_position):
  return
 if world.has_method("try_open_interior_door") and world.try_open_interior_door(global_position):
  return
 if world.has_method("try_interior_interaction") and world.try_interior_interaction(global_position):
  return
 # These starter-city coordinates only belong to the fictional fallback map.
 # Never award/charge money at arbitrary real-world coordinates in Shariatpur.
 if not bool(world.get("real_dhaka_loaded")):
  if position.distance_to(Vector3(42, 0, 42)) < 15:
   world.cash = max(0, world.cash - world.bargain_offer)
   world.bargain_offer = min(world.fare_requested, world.bargain_offer + 10)
  elif position.distance_to(Vector3(30, 0, -30)) < 18:
   world.cash += 100
  else:
   return
 else:
  return

func take_damage(amount: int):
 health = max(0, health - amount)
 if health <= 0 and world:
  world.respawn_player()
