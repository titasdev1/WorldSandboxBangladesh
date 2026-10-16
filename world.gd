extends Node3D

var player: CharacterBody3D
var game_mode := "deshi_story"
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
var real_mission_targets: Array[Vector3] = []
var rng := RandomNumberGenerator.new()
var police_timer := 0.0
var event_timer := 0.0
var event_text := "CITY LIFE ACTIVE"
var event_time_left := 0.0
var material_cache: Dictionary = {}
var city_asset_factory
var pbr_surface_factory
var combat_controller
var interior_factory
var real_dhaka_loader
var real_dhaka_loaded := false

var road_x := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]
var road_z := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]

func _ready():
 rng.randomize()
 pbr_surface_factory = load("res://pbr_surface_factory.gd").new()
 pbr_surface_factory.name = "PBRSurfaceFactory"
 add_child(pbr_surface_factory)
 pbr_surface_factory.configure(self)
 build_environment()
 city_asset_factory = load("res://city_asset_factory.gd").new()
 city_asset_factory.name = "CityAssetFactory"
 add_child(city_asset_factory)
 city_asset_factory.configure(self)
 interior_factory = load("res://systems/interior_factory.gd").new()
 interior_factory.name = "InteriorFactory"
 add_child(interior_factory)
 interior_factory.configure(self)
 # Prefer the streamed, georeferenced Dhaka package when the complete licensed
 # OSM tile package is installed. Keep the existing city as a safe fallback.
 real_dhaka_loader = load("res://real_dhaka_tile_loader.gd").new()
 real_dhaka_loader.name = "RealDhakaTileLoader"
 add_child(real_dhaka_loader)
 real_dhaka_loaded = real_dhaka_loader.configure(self)
 if not real_dhaka_loaded:
  build_city()
  build_landmarks()
 if not real_dhaka_loaded:
  var street_life = load("res://street_life_factory.gd").new()
  street_life.build(self)
 spawn_player()
 spawn_traffic()
 spawn_npcs()
 _configure_real_missions()
 spawn_police()
 create_mission_marker()
 _setup_a_square()
 combat_controller = load("res://systems/combat_mode_controller.gd").new()
 combat_controller.name = "CombatModeController"
 add_child(combat_controller)
 combat_controller.configure(self)

func make_mat(c: Color, roughness := 0.8, metallic := 0.0) -> StandardMaterial3D:
 var key := c.to_html(true) + ":" + str(roughness) + ":" + str(metallic)
 if material_cache.has(key):
  return material_cache[key]
 var m := StandardMaterial3D.new()
 m.albedo_color = c
 m.roughness = roughness
 m.metallic = metallic
 material_cache[key] = m
 return m

func box(pos: Vector3, size: Vector3, c: Color, collision := true, surface_id := ""):
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
 var material := make_mat(c)
 if pbr_surface_factory and not surface_id.is_empty() and pbr_surface_factory.has_method("material_for"):
  material = pbr_surface_factory.material_for(surface_id, material)
 mesh.material_override = material
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
 e.background_mode = Environment.BG_SKY
 var sky := Sky.new()
 var sky_material := ProceduralSkyMaterial.new()
 sky_material.sky_top_color = Color("#3e78a8")
 sky_material.sky_horizon_color = Color("#b6d1df")
 sky_material.ground_bottom_color = Color("#4b5b4a")
 sky_material.ground_horizon_color = Color("#a6b6b0")
 sky_material.sun_angle_max = 25.0
 sky_material.sun_curve = 0.18
 sky.sky_material = sky_material
 e.sky = sky
 e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 e.fog_enabled = true
 e.fog_light_color = Color("#b5cbd4")
 e.fog_density = 0.0012
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
 box(Vector3(0, -0.5, 0), Vector3(180, 1, 180), Color("#58714b"), true, "ground")

func build_city():
 for x in road_x:
  box(Vector3(x, 0.02, 0), Vector3(8.5, 0.14, 170), Color("#303438"), false, "road")
  for z in range(-78, 79, 8):
   box(Vector3(x, 0.11, z), Vector3(0.16, 0.035, 3.4), Color("#d8cfa7"), false)
 for z in road_z:
  box(Vector3(0, 0.03, z), Vector3(170, 0.14, 8.5), Color("#303438"), false, "road")
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
   var authored := false
   if city_asset_factory and city_asset_factory.has_method("spawn_building"):
    authored = city_asset_factory.spawn_building(Vector3(x, 0, z), Vector3(w, h, d))
   if not authored:
    box(Vector3(x, h / 2.0, z), Vector3(w, h, d), c, true, "plaster")
    _add_building_facade_details(x, h, z, w, d)
    if h > 14:
     cylinder(Vector3(x, h + 1.2, z), 1.1, 2.2, Color("#6b747a"))

func _add_building_facade_details(x: float, h: float, z: float, w: float, d: float) -> void:
 # Repeated framed window bands add recognizable apartment/market facades.
 # Keep mesh/material counts bounded for mid-range Android hardware.
 var floors: int = clampi(int(h / 3.8), 1, 4)
 for floor_index in range(floors):
  var y: float = 2.0 + float(floor_index) * 3.45
  if y + 0.6 >= h:
   continue
  var width: float = w * 0.68
  var window_pos := Vector3(x, y, z - d * 0.5 - 0.055)
  box(window_pos, Vector3(width, 0.88, 0.10), Color("#253a43"), false)
  box(window_pos + Vector3(0, 0.015, -0.065), Vector3(width * 0.86, 0.65, 0.035), Color("#6eaabd"), false)
  if w > 8.5:
   box(window_pos, Vector3(0.07, 0.84, 0.045), Color("#b5b9b2"), false)

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
 player.position = Vector3(0, 0, -12)
 var cs = CollisionShape3D.new()
 var cap = CapsuleShape3D.new()
 cap.radius = 0.45
 cap.height = 1.8
 cs.shape = cap
 cs.position.y = 1
 player.add_child(cs)
 var visual := HumanoidVisual.new()
 visual.name = "HumanoidVisual"
 visual.outfit_color = Color("#3b577a")
 visual.skin_color = Color("#b97850")
 visual.hair_color = Color("#24201f")
 player.add_child(visual)
 add_child(player)

func spawn_traffic():
 if real_dhaka_loaded and real_dhaka_loader:
  var mapped_routes: Array = real_dhaka_loader.get_road_routes()
  if mapped_routes.is_empty():
   push_warning("Real Dhaka map loaded but no usable OSM road paths were found for traffic.")
   return
  var mapped_types = [
   {"name":"Rickshaw","size":Vector3(1.5, 1.5, 2.5), "speed":2.8, "color":Color("#168447")},
   {"name":"CNG","size":Vector3(1.8, 1.5, 3.0), "speed":3.5, "color":Color("#168b70")},
   {"name":"Car","size":Vector3(2.1, 1.0, 4.0), "speed":4.2, "color":Color("#d94a45")},
   {"name":"Bus","size":Vector3(2.5, 2.6, 7.0), "speed":2.6, "color":Color("#d5a629")},
   {"name":"Motorcycle","size":Vector3(1.0, 1.2, 2.1), "speed":4.8, "color":Color("#3d4248")}
  ]
  for i in range(30):
   var t: Dictionary = mapped_types[rng.randi_range(0, mapped_types.size() - 1)]
   var v = CharacterBody3D.new()
   v.set_script(load("res://vehicle.gd"))
   v.world = self
   v.vehicle_type = t.name
   v.speed = float(t.speed) * rng.randf_range(0.8, 1.2)
   v.route_points = mapped_routes[rng.randi_range(0, mapped_routes.size() - 1)].duplicate()
   v.route_index = rng.randi_range(0, v.route_points.size() - 1)
   v.body_size = t.size
   v.body_color = t.color
   v.position = v.route_points[v.route_index]
   add_child(v)
  return
 var types = [
  {"name":"Rickshaw","size":Vector3(1.5, 1.5, 2.5), "speed":4.2, "color":Color("#168447")},
  {"name":"CNG","size":Vector3(1.8, 1.5, 3.0), "speed":5.0, "color":Color("#168b70")},
  {"name":"Car","size":Vector3(2.1, 1.0, 4.0), "speed":6.2, "color":Color("#d94a45")},
  {"name":"Bus","size":Vector3(2.5, 2.6, 7.0), "speed":3.8, "color":Color("#d5a629")},
  {"name":"Motorcycle","size":Vector3(1.0, 1.2, 2.1), "speed":7.0, "color":Color("#3d4248")}
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
 var mapped_routes: Array = []
 if real_dhaka_loaded and real_dhaka_loader:
  mapped_routes = real_dhaka_loader.get_road_routes()
 for i in range(45):
  var npc = CharacterBody3D.new()
  npc.name = "NPC_%02d" % i
  npc.set_script(load("res://npc.gd"))
  npc.world = self
  if not mapped_routes.is_empty():
   var route: Array = mapped_routes[rng.randi_range(0, mapped_routes.size() - 1)]
   var route_index: int = rng.randi_range(0, route.size() - 1)
   var route_point: Vector3 = route[route_index]
   var before: Vector3 = route[maxi(0, route_index - 1)]
   var after: Vector3 = route[mini(route.size() - 1, route_index + 1)]
   var direction: Vector3 = (after - before).normalized()
   var sidewalk_offset := Vector3(-direction.z, 0, direction.x) * (3.0 if i % 2 == 0 else -3.0)
   npc.position = route_point + sidewalk_offset
  else:
   npc.position = Vector3(rng.randf_range(-70, 70), 0, rng.randf_range(-70, 70))
  npc.walk_speed = rng.randf_range(1.0, 2.4)
  var visual := HumanoidVisual.new()
  visual.name = "HumanoidVisual"
  visual.outfit_color = Color.from_hsv(rng.randf(), 0.48, rng.randf_range(0.38, 0.78))
  visual.skin_color = [Color("#b97850"), Color("#8c583b"), Color("#d29a6e")][rng.randi_range(0, 2)]
  visual.hair_color = [Color("#211d1a"), Color("#3c3029"), Color("#242a2c")][rng.randi_range(0, 2)]
  visual.has_satchel = i % 5 == 0
  npc.add_child(visual)
  var cs = CollisionShape3D.new()
  var cap = CapsuleShape3D.new()
  cap.radius = 0.3
  cap.height = 1.5
  cs.shape = cap
  cs.position.y = 0.75
  npc.add_child(cs)
  add_child(npc)

func spawn_police():
 if real_dhaka_loaded and real_dhaka_loader:
  var mapped_routes: Array = real_dhaka_loader.get_road_routes()
  if mapped_routes.is_empty():
   return
  for i in range(3):
   var v = CharacterBody3D.new()
   v.set_script(load("res://vehicle.gd"))
   v.world = self
   v.vehicle_type = "Police"
   v.speed = 4.5
   v.body_size = Vector3(2.1, 1.0, 4.0)
   v.body_color = Color("#263d8f")
   v.is_police = true
   v.route_points = mapped_routes[rng.randi_range(0, mapped_routes.size() - 1)].duplicate()
   v.route_index = rng.randi_range(0, v.route_points.size() - 1)
   v.position = v.route_points[v.route_index]
   add_child(v)
  return
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
 event_time_left = max(0.0, event_time_left - delta)
 var sun = get_node_or_null("Sun")
 if sun:
  sun.rotation_degrees.x = -35 - sin(day_time / 24.0 * TAU) * 35.0
  sun.light_energy = 0.65 + max(0.0, sin(day_time / 24.0 * TAU)) * 0.7
 if player and mission_active:
  var distance = player.position.distance_to(mission_target)
  if mission_stage == 0 and distance < 6:
   mission_stage = 1
   mission_target = real_mission_targets[1] if real_dhaka_loaded and real_mission_targets.size() > 1 else Vector3(-36, 0, -36)
   update_marker()
  elif mission_stage == 1 and player.position.distance_to(mission_target) < 6:
   mission_stage = 2
   mission_target = real_mission_targets[2] if real_dhaka_loaded and real_mission_targets.size() > 2 else Vector3(30, 0, -30)
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
 event_timer += delta
 if event_timer > 30.0:
  event_timer = 0.0
  if rng.randf() < 0.35:
   cash += 50
   event_text = "RANDOM JOB: +৳50"
   event_time_left = 8.0
 if Input.is_action_just_pressed("rain"):
  rain = !rain
  var env = get_node_or_null("WorldEnvironment")
  if env:
   env.environment.background_color = Color("#52677a") if rain else Color("#8eb9d2")
 _update_a_square_systems(delta)
 if combat_controller and combat_controller.has_method("update"):
  combat_controller.update(delta)

func update_marker():
 var marker = get_node_or_null("MissionMarker")
 if marker:
  marker.position = mission_target + Vector3(0, 0.15, 0)

func try_fire():
 if not player:
  return
 wanted = min(5, wanted + 1)
 var camera: Camera3D = player.get("camera") as Camera3D
 var origin: Vector3 = camera.global_position if is_instance_valid(camera) else player.global_position + Vector3(0, 1.3, 0)
 var dir: Vector3 = -camera.global_transform.basis.z.normalized() if is_instance_valid(camera) else -player.global_transform.basis.z.normalized()
 var query = PhysicsRayQueryParameters3D.create(origin, origin + dir * 80.0)
 query.exclude = [player]
 var hit = get_world_3d().direct_space_state.intersect_ray(query)
 if hit and hit.collider and hit.collider is CharacterBody3D:
  if hit.collider.has_method("on_hit"):
   hit.collider.on_hit()

func respawn_player():
 if not player:
  return
 player.health = 100
 player.position = Vector3(0, 0, -12)
 wanted = 0
 cash = max(0, cash - 100)

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

func is_red_for_axis(_axis: String, _vehicle_position: Vector3) -> bool:
 return false


# Project A-Square integrated world director.
var district_factory
var gameplay_director
var city_stream_timer := 0.0

func _configure_real_missions() -> void:
    if not real_dhaka_loaded or not real_dhaka_loader:
        return
    var routes: Array = real_dhaka_loader.get_road_routes()
    var candidates: Array[Vector3] = []
    var nearest_point := Vector3.ZERO
    var nearest_distance := INF
    var nearest_route: Array = []
    var nearest_route_index := 0
    for route in routes:
        for point_index in range(route.size()):
            var road_point: Vector3 = route[point_index]
            var road_distance := Vector2(road_point.x - player.position.x, road_point.z - player.position.z).length()
            if road_distance < nearest_distance:
                nearest_distance = road_distance
                nearest_point = road_point
                nearest_route = route
                nearest_route_index = point_index
    if nearest_distance < INF:
        var before: Vector3 = nearest_route[maxi(0, nearest_route_index - 1)]
        var after: Vector3 = nearest_route[mini(nearest_route.size() - 1, nearest_route_index + 1)]
        var road_direction := (after - before).normalized()
        var sidewalk_offset := Vector3(-road_direction.z, 0, road_direction.x) * 2.5
        player.position = nearest_point + sidewalk_offset + Vector3(0, 0.2, 0)
    for route in routes:
        for point in route:
            var p: Vector3 = point
            var distance_from_player := Vector2(p.x - player.position.x, p.z - player.position.z).length()
            if distance_from_player >= 25.0 and distance_from_player <= 220.0:
                var unique := true
                for existing in candidates:
                    if existing.distance_to(p) < 18.0:
                        unique = false
                        break
                if unique:
                    candidates.append(p)
    if candidates.is_empty():
        return
    candidates.sort_custom(func(a: Vector3, b: Vector3) -> bool:
        return a.distance_to(player.position) < b.distance_to(player.position)
    )
    real_mission_targets.clear()
    real_mission_targets.append(candidates[mini(0, candidates.size() - 1)])
    if candidates.size() > 1:
        real_mission_targets.append(candidates[mini(1, candidates.size() - 1)])
    if candidates.size() > 2:
        real_mission_targets.append(candidates[mini(2, candidates.size() - 1)])
    mission_target = real_mission_targets[0]

func _setup_a_square():
    district_factory = load("res://systems/district_factory.gd").new()
    district_factory.name = "DistrictFactory"
    add_child(district_factory)
    if not real_dhaka_loaded:
        district_factory.build(self, player)
    gameplay_director = load("res://systems/gameplay_director.gd").new()
    gameplay_director.name = "GameplayDirector"
    add_child(gameplay_director)
    gameplay_director.configure(self, player, district_factory)
    # Keep the data-driven Deshi mission catalogue in this canonical world.
    # It shares the same player, streamed map, HUD, economy, and progression.
    var mission_factory_node = load("res://systems/mission_factory.gd").new()
    mission_factory_node.name = "MissionFactory"
    add_child(mission_factory_node)

func _update_a_square_systems(delta):
    city_stream_timer += delta
    if city_stream_timer >= 0.5:
        city_stream_timer = 0.0
        if district_factory and district_factory.has_method("update") and player:
            district_factory.update(player)
    if gameplay_director and gameplay_director.has_method("update"):
        gameplay_director.update(delta)

func notify_gameplay_event(event_name: String, value := 1):
    if gameplay_director and gameplay_director.has_method("event"):
        gameplay_director.event(event_name, value)



func get_interior_interaction_label(at: Vector3) -> String:
 if interior_factory and interior_factory.has_method("is_inside") and interior_factory.is_inside():
  return interior_factory.get_interaction_label(at)
 var nearest: Node3D = null
 var nearest_distance := 3.5
 for node in get_tree().get_nodes_in_group("real_building_entry"):
  if not node is Node3D:
   continue
  var distance: float = at.distance_to((node as Node3D).global_position)
  if distance < nearest_distance:
   nearest_distance = distance
   nearest = node as Node3D
 if not is_instance_valid(nearest):
  return ""
 var seed: Dictionary = nearest.get_meta("interior_seed", {})
 var category := str(seed.get("category", "")).to_lower()
 if category.contains("shop") or category.contains("retail") or category.contains("convenience"):
  return "ENTER SHOP"
 if category.contains("house") or category.contains("residential") or category.contains("home"):
  return "ENTER HOME"
 return "ENTER BUILDING"

func try_interior_interaction(at: Vector3) -> bool:
 if not interior_factory:
  return false
 if interior_factory.has_method("is_inside") and interior_factory.is_inside():
  return interior_factory.try_interact(at)
 var nearest: Node3D = null
 var nearest_distance := 3.5
 for node in get_tree().get_nodes_in_group("real_building_entry"):
  if not node is Node3D:
   continue
  var distance: float = at.distance_to((node as Node3D).global_position)
  if distance < nearest_distance:
   nearest_distance = distance
   nearest = node as Node3D
 if not is_instance_valid(nearest):
  return false
 var seed: Dictionary = nearest.get_meta("interior_seed", {})
 var direction: Vector3 = nearest.get_meta("exit_direction", Vector3(0, 0, 1))
 var tile_id := str(nearest.get_meta("tile_id", ""))
 interior_factory.open_interior(seed, nearest.global_position, direction, tile_id)
 return true

func open_generated_interior(seed: Dictionary, exterior_position: Vector3, exit_direction: Vector3, tile_id: String) -> void:
 if interior_factory:
  interior_factory.open_interior(seed, exterior_position, exit_direction, tile_id)

# Interactable market stalls: spend a little cash to recover health.
func try_street_vendor(at: Vector3) -> bool:
    if real_dhaka_loaded:
        return false
    var stalls := [Vector3(18,0,-20), Vector3(23,0,-20), Vector3(28,0,-20), Vector3(33,0,-20), Vector3(18,0,-25), Vector3(33,0,-25)]
    var nearest := 999.0
    for stall in stalls:
        nearest = minf(nearest, Vector2(at.x - stall.x, at.z - stall.z).length())
    if nearest > 4.2:
        return false
    if not player:
        return true
    if player.health >= 100:
        event_text = "MARKET: YOU ARE ALREADY HEALTHY"
        event_time_left = 3.5
    elif cash < 20:
        event_text = "MARKET: NEED ৳20 FOR A SNACK"
        event_time_left = 3.5
    else:
        cash -= 20
        player.health = mini(100, player.health + 15)
        event_text = "STREET SNACK: -৳20  +HEALTH"
        event_time_left = 4.0
    return true
