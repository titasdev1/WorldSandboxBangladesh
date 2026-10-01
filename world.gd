extends Node3D

var player: CharacterBody3D
var cash := 850
var wanted := 0
var rain := false
var day_time := 15.0
var mission_active := true
var mission_stage := 0
var mission_progress := 0
var fare_requested := 120
var bargain_offer := 80
var mission_target := Vector3(42, 0, 42)
var rng := RandomNumberGenerator.new()
var police_timer := 0.0
var event_timer := 0.0
var traffic_clock := 0.0
var traffic_cycle := 16.0
var rain_particles: GPUParticles3D

var road_x := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]
var road_z := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]

func _ready():
 rng.randomize()
 build_environment()
 build_traffic_lights()
 build_rain_system()
 build_city()
 build_landmarks()
 spawn_player()
 spawn_traffic()
 spawn_npcs()
 spawn_police()
 create_mission_marker()

func make_mat(c: Color, roughness := 0.8, metallic := 0.0):
 var m = StandardMaterial3D.new()
 m.albedo_color = c
 m.roughness = roughness
 m.metallic = metallic
 return m

func box(pos: Vector3, size: Vector3, c: Color, collision := true):
 var body: Node3D
 if collision:
  var static_body = StaticBody3D.new()
  var shape = CollisionShape3D.new()
  var bs = BoxShape3D.new()
  bs.size = size
  shape.shape = bs
  static_body.add_child(shape)
  body = static_body
 else:
  body = MeshInstance3D.new()
 var mesh = MeshInstance3D.new()
 var bm = BoxMesh.new()
 bm.size = size
 mesh.mesh = bm
 mesh.material_override = make_mat(c)
 body.add_child(mesh)
 body.position = pos
 add_child(body)
 return body

func cylinder(pos: Vector3, radius: float, height: float, c: Color):
 var mesh = MeshInstance3D.new()
 var cm = CylinderMesh.new()
 cm.top_radius = radius
 cm.bottom_radius = radius
 cm.height = height
 mesh.mesh = cm
 mesh.material_override = make_mat(c)
 mesh.position = pos
 add_child(mesh)
 return mesh

func build_environment():
 var env = WorldEnvironment.new()
 var e = Environment.new()
 e.background_mode = Environment.BG_COLOR
 e.background_color = Color("#8fb9d2")
 e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 e.ambient_light_color = Color("#d7e7ff")
 e.ambient_light_energy = 0.78
 e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
 env.environment = e
 add_child(env)
 var sun = DirectionalLight3D.new()
 sun.name = "Sun"
 sun.rotation_degrees = Vector3(-48, -25, 0)
 sun.light_energy = 1.2
 sun.shadow_enabled = true
 add_child(sun)
 box(Vector3(0, -0.5, 0), Vector3(180, 1, 180), Color("#58714b"), true)

func build_city():
 for x in road_x:
  box(Vector3(x, 0.02, 0), Vector3(8.5, 0.14, 170), Color("#303438"), false)
  for z in range(-78, 79, 8):
   box(Vector3(x, 0.11, z), Vector3(0.16, 0.035, 3.4), Color("#d8cfa7"), false)
 for z in road_z:
  box(Vector3(0, 0.03, z), Vector3(170, 0.14, 8.5), Color("#303438"), false)
  for x in range(-78, 79, 8):
   box(Vector3(x, 0.12, z), Vector3(3.4, 0.035, 0.16), Color("#d8cfa7"), false)
 for x in range(-72, 73, 12):
  for z in range(-72, 73, 12):
   var on_road = false
   for rx in road_x:
    if abs(float(x) - rx) < 8.0:
     on_road = true
   for rz in road_z:
    if abs(float(z) - rz) < 8.0:
     on_road = true
   if on_road:
    continue
   if Vector2(x, z).distance_to(Vector2(0, 50)) < 12:
    continue
   var h = rng.randf_range(5.0, 20.0)
   var w = rng.randf_range(7.0, 10.0)
   var d = rng.randf_range(7.0, 10.0)
   var c = Color.from_hsv(rng.randf(), 0.12, rng.randf_range(0.55, 0.78))
   box(Vector3(x, h / 2.0, z), Vector3(w, h, d), c, true)
   if h > 14:
    cylinder(Vector3(x, h + 1.2, z), 1.1, 2.2, Color("#6b747a"))

func build_landmarks():
 box(Vector3(0, -0.02, 48), Vector3(170, 0.12, 18), Color("#247c9e"), false)
 box(Vector3(0, 0.2, 38.8), Vector3(170, 0.35, 0.8), Color("#aeb8a1"), false)
 box(Vector3(0, 0.2, 57.2), Vector3(170, 0.35, 0.8), Color("#aeb8a1"), false)
 box(Vector3(42, 1.5, 42), Vector3(20, 3, 14), Color("#a95e39"), true)
 box(Vector3(42, 3.3, 42), Vector3(22, 0.5, 16), Color("#e1b24e"), true)
 box(Vector3(-36, 6, -36), Vector3(8, 12, 8), Color("#d58c3b"), true)
 box(Vector3(-36, 12.8, -36), Vector3(11, 1.0, 11), Color("#e4c35b"), true)
 cylinder(Vector3(-36, 17, -36), 1.4, 7.0, Color("#d5dbe0"))
 box(Vector3(30, 0.9, -30), Vector3(28, 1.8, 20), Color("#805038"), true)
 for i in range(5):
  box(Vector3(20 + i * 5, 2.0, -30), Vector3(3.2, 1.0, 16), Color("#b88a56"), false)
 for x in road_x:
  for z in range(-72, 73, 24):
   cylinder(Vector3(x + 5.0, 3.0, z), 0.12, 6.0, Color("#3e4549"))
   var lamp = OmniLight3D.new()
   lamp.position = Vector3(x + 5.0, 6.1, z)
   lamp.omni_range = 9
   lamp.light_energy = 0.35
   add_child(lamp)

func spawn_player():
 player = CharacterBody3D.new()
 player.name = "Player"
 player.set_script(load("res://player.gd"))
 player.world = self
 player.position = Vector3(0, 1, -12)
 var cs = CollisionShape3D.new()
 var cap = CapsuleShape3D.new()
 cap.radius = 0.45
 cap.height = 1.8
 cs.shape = cap
 cs.position.y = 1
 player.add_child(cs)
 var mesh = MeshInstance3D.new()
 var cm = CapsuleMesh.new()
 cm.radius = 0.45
 cm.height = 1.8
 mesh.mesh = cm
 mesh.material_override = make_mat(Color("#3b577a"))
 mesh.position.y = 1
 player.add_child(mesh)
 var cam = Camera3D.new()
 cam.position = Vector3(0, 6.2, 9.5)
 cam.rotation_degrees = Vector3(-28, 180, 0)
 cam.current = true
 cam.fov = 68
 player.add_child(cam)
 add_child(player)

func spawn_traffic():
 var types = [
  {"name":"Rickshaw","size":Vector3(1.5, 1.5, 2.5), "speed":4.2, "color":Color("#168447")},
  {"name":"CNG","size":Vector3(1.8, 1.5, 3.0), "speed":5.0, "color":Color("#168b70")},
  {"name":"Car","size":Vector3(2.1, 1.0, 4.0), "speed":6.2, "color":Color("#d94a45")},
  {"name":"Bus","size":Vector3(2.5, 2.6, 7.0), "speed":3.8, "color":Color("#d5a629")}
 ]
 for i in range(30):
  var t = types[rng.randi_range(0, types.size() - 1)]
  var v = CharacterBody3D.new()
  v.set_script(load("res://vehicle.gd"))
  v.world = self
  v.vehicle_type = t.name
  v.speed = t.speed * rng.randf_range(0.8, 1.2)
  v.lane_axis = "z" if rng.randi_range(0, 1) == 0 else "x"
  var lane = road_x[rng.randi_range(0, road_x.size() - 1)] if v.lane_axis == "z" else road_z[rng.randi_range(0, road_z.size() - 1)]
  if v.lane_axis == "z":
   v.position = Vector3(lane + (1.8 if i % 2 == 0 else -1.8), 0, rng.randf_range(-78, 78))
  else:
   v.position = Vector3(rng.randf_range(-78, 78), 0, lane + (1.8 if i % 2 == 0 else -1.8))
  v.body_size = t.size
  v.body_color = t.color
  add_child(v)

func spawn_npcs():
 for i in range(45):
  var npc = CharacterBody3D.new()
  npc.name = "NPC_%02d" % i
  npc.set_script(load("res://npc.gd"))
  npc.world = self
  npc.position = Vector3(rng.randf_range(-70, 70), 0, rng.randf_range(-70, 70))
  npc.walk_speed = rng.randf_range(1.0, 2.4)
  var mesh = MeshInstance3D.new()
  var cm = CapsuleMesh.new()
  cm.radius = 0.3
  cm.height = 1.5
  mesh.mesh = cm
  mesh.material_override = make_mat(Color.from_hsv(rng.randf(), 0.35, 0.65))
  mesh.position.y = 0.75
  npc.add_child(mesh)
  var cs = CollisionShape3D.new()
  var cap = CapsuleShape3D.new()
  cap.radius = 0.3
  cap.height = 1.5
  cs.shape = cap
  cs.position.y = 0.75
  npc.add_child(cs)
  add_child(npc)

func spawn_police():
 for i in range(3):
  var v = CharacterBody3D.new()
  v.set_script(load("res://vehicle.gd"))
  v.world = self
  v.vehicle_type = "Police"
  v.speed = 7.0
  v.lane_axis = "z"
  v.body_size = Vector3(2.1, 1.0, 4.0)
  v.body_color = Color("#263d8f")
  v.is_police = true
  v.position = Vector3(road_x[i * 2], 0, -70.0 - i * 8.0)
  add_child(v)

func create_mission_marker():
 var marker = MeshInstance3D.new()
 marker.name = "MissionMarker"
 var torus = TorusMesh.new()
 torus.inner_radius = 2.0
 torus.outer_radius = 2.25
 marker.mesh = torus
 marker.material_override = make_mat(Color("#ffd34e"), 0.3, 0.1)
 marker.position = mission_target + Vector3(0, 0.15, 0)
 add_child(marker)

func _process(delta):
 day_time = fmod(day_time + delta * 0.08, 24.0)
 var sun = get_node_or_null("Sun")
 if sun:
  sun.rotation_degrees.x = -35 - sin(day_time / 24.0 * TAU) * 35.0
  sun.light_energy = 0.65 + max(0.0, sin(day_time / 24.0 * TAU)) * 0.7
 if player and mission_active:
  var distance = player.position.distance_to(mission_target)
  if mission_stage == 0 and distance < 6:
   mission_stage = 1
   mission_target = Vector3(-36, 0, -36)
   update_marker()
  elif mission_stage == 1 and player.position.distance_to(mission_target) < 6:
   mission_stage = 2
   mission_target = Vector3(30, 0, -30)
   cash += 250
   update_marker()
  elif mission_stage == 2 and player.position.distance_to(mission_target) < 6:
   mission_active = false
   mission_progress = 1
   cash += 750
   update_marker()
 if wanted > 0:
  police_timer += delta
  if police_timer > 18.0:
   wanted = max(0, wanted - 1)
   police_timer = 0.0
 traffic_clock = fmod(traffic_clock + delta, traffic_cycle)
 event_timer += delta
 if event_timer > 30.0:
  event_timer = 0.0
  if rng.randf() < 0.35:
   cash += 50
 if Input.is_action_just_pressed("save_game"):
  SaveSystem.save_world(self)
 if Input.is_action_just_pressed("load_game"):
  SaveSystem.load_world(self)
 if Input.is_action_just_pressed("rain"):
  rain = !rain
  var env = get_node_or_null("WorldEnvironment")
  if env:
   env.environment.background_color = Color("#52677a") if rain else Color("#8eb9d2")
  if rain_particles:
   rain_particles.emitting = rain
   if player:
    rain_particles.position = Vector3(player.position.x, 28, player.position.z)

func update_marker():
 var marker = get_node_or_null("MissionMarker")
 if marker:
  marker.position = mission_target + Vector3(0, 0.15, 0)

func try_fire():
 if not player:
  return
 wanted = min(5, wanted + 1)
 var origin = player.global_position + Vector3(0, 1.3, 0)
 var dir = -player.global_transform.basis.z
 var query = PhysicsRayQueryParameters3D.create(origin, origin + dir * 30.0)
 query.exclude = [player]
 var hit = get_world_3d().direct_space_state.intersect_ray(query)
 if hit and hit.collider and hit.collider is CharacterBody3D:
  if hit.collider.has_method("on_hit"):
   hit.collider.on_hit()


func respawn_player():
 if not player:
  return
 player.health = 100
 player.position = Vector3(0, 1, -12)
 wanted = 0
 cash = max(0, cash - 100)

func build_traffic_lights():
 for x in road_x:
  for z in road_z:
   var pole = box(Vector3(x + 4.8, 2.6, z + 4.8), Vector3(0.18, 5.2, 0.18), Color("#34383b"), true)
   box(Vector3(x + 4.8, 5.0, z + 4.8), Vector3(0.55, 1.4, 0.45), Color("#202326"), false)

func build_rain_system():
 rain_particles = GPUParticles3D.new()
 rain_particles.name = "RainParticles"
 rain_particles.amount = 700
 rain_particles.lifetime = 0.8
 rain_particles.emitting = false
 var process_mat = ParticleProcessMaterial.new()
 process_mat.direction = Vector3(0, -1, 0)
 process_mat.initial_velocity_min = 18.0
 process_mat.initial_velocity_max = 26.0
 process_mat.gravity = Vector3(0, -3, 0)
 process_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
 process_mat.emission_box_extents = Vector3(70, 2, 70)
 rain_particles.process_material = process_mat
 var quad = QuadMesh.new()
 quad.size = Vector2(0.025, 0.5)
 var mat = StandardMaterial3D.new()
 mat.albedo_color = Color(0.65, 0.75, 0.9, 0.45)
 mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
 mat.shading_mode = BaseMaterial3D.SHADING_UNSHADED
 quad.material = mat
 rain_particles.draw_pass_1 = quad
 rain_particles.position = Vector3(0, 28, 0)
 add_child(rain_particles)

func is_red_for_axis(axis: String, vehicle_position: Vector3) -> bool:
 var near_intersection = false
 if axis == "z":
  for x in road_x:
   if abs(vehicle_position.x - x) < 3.0:
    near_intersection = true
    break
 else:
  for z in road_z:
   if abs(vehicle_position.z - z) < 3.0:
    near_intersection = true
    break
 if not near_intersection:
  return false
 return fmod(traffic_clock, traffic_cycle) > 8.0

func try_vehicle_interaction():
 if not player:
  return
 var nearest = null
 var best = 4.0
 for node in get_children():
  if node is CharacterBody3D and node.has_method("enter_player") and not node.occupied:
   var d = player.global_position.distance_to(node.global_position)
   if d < best:
    best = d
    nearest = node
 if nearest:
  nearest.enter_player(player)
