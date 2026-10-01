extends CharacterBody3D

var world
var speed := 4.0
var lane_axis := "z"
var vehicle_type := "Car"
var body_size := Vector3(2.0, 1.0, 4.0)
var body_color := Color("#d94a45")
var is_police := false

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
