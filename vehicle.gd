extends CharacterBody3D

var world
var speed := 4.0
var lane_axis := "z"
var vehicle_type := "Car"
var body_size := Vector3(2.0, 1.0, 4.0)
var body_color := Color("#d94a45")
var is_police := false
var occupied := false

func _ready():
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

func make_mat(c: Color):
 var m = StandardMaterial3D.new()
 m.albedo_color = c
 m.roughness = 0.65
 return m

func _physics_process(delta):
 if occupied and world and world.player:
  var steer = Input.get_axis("move_left", "move_right")
  var throttle = Input.get_axis("move_back", "move_forward")
  speed = clamp(speed + throttle * delta * 8.0, -5.0, 14.0)
  rotation.y += steer * delta * 1.8
  velocity = -global_transform.basis.z * speed
  move_and_slide()
  world.player.global_position = global_position + Vector3(0, 1.2, 0)
  if Input.is_action_just_pressed("interact"):
   exit_player()
  return
 if world and not is_police and world.is_red_for_axis(lane_axis, global_position):
  velocity = Vector3.ZERO
  return
 if lane_axis == "z":
  position.z += speed * delta
  rotation.y = 0.0
  if position.z > 86:
   position.z = -86
 else:
  position.x += speed * delta
  rotation.y = PI * 0.5
  if position.x > 86:
   position.x = -86
 if is_police and world and world.wanted > 0 and world.player:
  if global_position.distance_to(world.player.global_position) < 18:
   world.wanted = min(5, world.wanted + 1)

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
 return true

func exit_player():
 if not occupied or not world or not world.player:
  return
 var p = world.player
 occupied = false
 p.visible = true
 p.set_physics_process(true)
 p.global_position = global_position + global_transform.basis.x * 2.5 + Vector3(0, 0.9, 0)
