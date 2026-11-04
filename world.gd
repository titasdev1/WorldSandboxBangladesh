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
var gunfire_wanted_cooldown := 0.0
var combat_hit_marker_time := 0.0
var combat_hit_marker_headshot := false
const COMBAT_HEADSHOT_MIN_HEIGHT := 1.62
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
var save_location_status := ""
var inventory_system: Node
var shop_system: Node
var occupied_vehicle: Node3D

var road_x := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]
var road_z := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]

func _ready():
 rng.randomize()
 inventory_system = load("res://inventory_system.gd").new()
 inventory_system.name = "InventorySystem"
 add_child(inventory_system)
 shop_system = load("res://shop_system.gd").new()
 shop_system.name = "ShopSystem"
 add_child(shop_system)
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
 var map_runtime_report: Dictionary = real_dhaka_loader.get_runtime_map_diagnostics()
 map_runtime_report["real_map_loaded"] = real_dhaka_loaded
 print("REAL_MAP_RUNTIME:" + JSON.stringify(map_runtime_report))
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
 call_deferred("_load_saved_session")

func _load_saved_session() -> void:
 await get_tree().process_frame
 await get_tree().process_frame
 if SaveSystem.load_world(self):
  event_text = "PROGRESS RESTORED • " + str(save_location_status)
  event_time_left = 8.0


func save_game_progress(show_feedback := true) -> bool:
 var saved := SaveSystem.save_world(self)
 if show_feedback:
  event_text = "GAME SAVED TO THIS DEVICE" if saved else "SAVE FAILED • CHECK DEVICE STORAGE"
  event_time_left = 6.0
 return saved


func load_saved_progress() -> bool:
 var restored := SaveSystem.load_world(self)
 if restored:
  event_text = "PROGRESS LOADED • " + str(save_location_status)
 else:
  event_text = "NO VALID SAVE FOUND"
 event_time_left = 7.0
 return restored


func _notification(what: int) -> void:
 if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED:
  save_game_progress(false)


func refresh_mission_targets_after_load() -> void:
 if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader) or not is_instance_valid(player):
  return
 if real_dhaka_loader.has_method("is_navigation_index_ready") and not real_dhaka_loader.is_navigation_index_ready():
  return
 var candidates: Array[Vector3] = []
 for route in real_dhaka_loader.get_road_routes():
  if not route is Array:
   continue
  for point in route:
   if not point is Vector3:
    continue
   var distance := Vector2(point.x - player.global_position.x, point.z - player.global_position.z).length()
   if distance < 25.0 or distance > 220.0:
    continue
   var unique := true
   for existing in candidates:
    if Vector2(existing.x - point.x, existing.z - point.z).length() < 18.0:
     unique = false
     break
   if unique:
    candidates.append(point)
 candidates.sort_custom(func(a: Vector3, b: Vector3) -> bool:
  return a.distance_to(player.global_position) < b.distance_to(player.global_position)
 )
 real_mission_targets.clear()
 for i in range(mini(3, candidates.size())):
  real_mission_targets.append(candidates[i])
 if not real_mission_targets.is_empty():
  mission_target = real_mission_targets[clampi(mission_stage, 0, real_mission_targets.size() - 1)]


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
 var initial_spawn := Vector3(0, 0, -12)
 if real_dhaka_loaded and is_instance_valid(real_dhaka_loader):
  initial_spawn = _nearest_mapped_respawn_position(initial_spawn)
 player.position = initial_spawn
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
 visual.is_player_character = true
 player.add_child(visual)
 add_child(player)

func spawn_traffic():
 if real_dhaka_loaded and real_dhaka_loader:
  var mapped_routes: Array = real_dhaka_loader.get_vehicle_route_records()
  if mapped_routes.is_empty():
   push_warning("Real map loaded but no access-allowed OSM road paths were found for traffic.")
   return
  for i in range(TARGET_MAPPED_TRAFFIC_COUNT):
   _spawn_mapped_traffic_vehicle(mapped_routes)
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

func _configure_mapped_vehicle_route(vehicle_node: Node3D, road: Dictionary) -> bool:
 var points: Array = road.get("points", [])
 if points.size() < 2:
  return false
 vehicle_node.set("route_points", points.duplicate())
 vehicle_node.set("route_oneway", bool(road.get("one_way", false)))
 vehicle_node.set("route_id", str(road.get("route_id", "")))
 var one_way := bool(road.get("one_way", false))
 var direction := int(road.get("one_way_direction", 1)) if one_way else (1 if rng.randi_range(0, 1) == 0 else -1)
 vehicle_node.set("route_direction", direction)
 var start_index := rng.randi_range(0, points.size() - 2) if direction > 0 else rng.randi_range(1, points.size() - 1)
 vehicle_node.set("route_index", start_index)
 vehicle_node.position = points[start_index]
 return true


func _spawn_mapped_traffic_vehicle(route_records: Array = []) -> void:
 if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader):
  return
 var available: Array = route_records if not route_records.is_empty() else real_dhaka_loader.get_vehicle_route_records()
 var candidates: Array[Dictionary] = []
 for item in available:
  if item is Dictionary and item.get("points", []) is Array and item["points"].size() >= 2:
   candidates.append(item)
 if candidates.is_empty():
  return
 var mapped_types := [
  {"name":"Rickshaw","size":Vector3(1.5, 1.5, 2.5), "speed":2.8, "color":Color("#168447")},
  {"name":"CNG","size":Vector3(1.8, 1.5, 3.0), "speed":3.5, "color":Color("#168b70")},
  {"name":"Car","size":Vector3(2.1, 1.0, 4.0), "speed":4.2, "color":Color("#d94a45")},
  {"name":"Bus","size":Vector3(2.5, 2.6, 7.0), "speed":2.6, "color":Color("#d5a629")},
  {"name":"Motorcycle","size":Vector3(1.0, 1.2, 2.1), "speed":4.8, "color":Color("#3d4248")}
 ]
 var selected_type: Dictionary = mapped_types[rng.randi_range(0, mapped_types.size() - 1)]
 var selected_road: Dictionary = candidates[rng.randi_range(0, candidates.size() - 1)]
 var v := CharacterBody3D.new()
 v.set_script(load("res://vehicle.gd"))
 v.world = self
 v.vehicle_type = selected_type.name
 v.speed = float(selected_type.speed) * rng.randf_range(0.8, 1.2)
 v.body_size = selected_type.size
 v.body_color = selected_type.color
 if not _configure_mapped_vehicle_route(v, selected_road):
  v.free()
  return
 v.add_to_group("mapped_traffic_vehicle")
 add_child(v)


func _spawn_mapped_police_vehicle(route_records: Array = []) -> void:
 if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader):
  return
 var available: Array = route_records if not route_records.is_empty() else real_dhaka_loader.get_vehicle_route_records()
 var candidates: Array[Dictionary] = []
 for item in available:
  if item is Dictionary and item.get("points", []) is Array and item["points"].size() >= 2:
   candidates.append(item)
 if candidates.is_empty():
  return
 var road: Dictionary = candidates[rng.randi_range(0, candidates.size() - 1)]
 var v := CharacterBody3D.new()
 v.set_script(load("res://vehicle.gd"))
 v.world = self
 v.vehicle_type = "Police"
 v.speed = 4.5
 v.body_size = Vector3(2.1, 1.0, 4.0)
 v.body_color = Color("#263d8f")
 v.is_police = true
 if not _configure_mapped_vehicle_route(v, road):
  v.free()
  return
 v.add_to_group("mapped_police_vehicle")
 add_child(v)


func advance_mapped_traffic_route(vehicle_node: Node3D) -> bool:
 if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader) or not is_instance_valid(vehicle_node):
  return false
 var points: Array = vehicle_node.get("route_points")
 if points.size() < 2:
  return false
 var direction := int(vehicle_node.get("route_direction"))
 var endpoint: Vector3 = points[points.size() - 1] if direction > 0 else points[0]
 var current_id := str(vehicle_node.get("route_id"))
 var available: Array = real_dhaka_loader.get_vehicle_route_records()
 var best_record: Dictionary = {}
 var best_direction := 1
 var best_distance := 18.0
 for candidate in available:
  if not candidate is Dictionary or str(candidate.get("route_id", "")) == current_id:
   continue
  var next_points: Array = candidate.get("points", [])
  if next_points.size() < 2:
   continue
  var is_oneway := bool(candidate.get("one_way", false))
  var candidate_direction := int(candidate.get("one_way_direction", 1)) if is_oneway else 1
  var entry_index := 0 if candidate_direction > 0 else next_points.size() - 1
  if not is_oneway:
   var to_start := Vector2(next_points[0].x - endpoint.x, next_points[0].z - endpoint.z).length()
   var to_end := Vector2(next_points[next_points.size() - 1].x - endpoint.x, next_points[next_points.size() - 1].z - endpoint.z).length()
   entry_index = next_points.size() - 1 if to_end < to_start else 0
   candidate_direction = -1 if entry_index == next_points.size() - 1 else 1
  var entry: Vector3 = next_points[entry_index]
  var distance := Vector2(entry.x - endpoint.x, entry.z - endpoint.z).length()
  if distance < best_distance:
   best_distance = distance
   best_record = candidate
   best_direction = candidate_direction
 if best_record.is_empty():
  return false
 var next_points: Array = best_record["points"]
 vehicle_node.set("route_points", next_points.duplicate())
 vehicle_node.set("route_oneway", bool(best_record.get("one_way", false)))
 vehicle_node.set("route_id", str(best_record.get("route_id", "")))
 vehicle_node.set("route_direction", best_direction)
 vehicle_node.set("route_index", 0 if best_direction > 0 else next_points.size() - 1)
 return true


func spawn_npcs():
 var mapped_routes: Array = []
 if real_dhaka_loaded and real_dhaka_loader:
  mapped_routes = real_dhaka_loader.get_road_routes()
 if real_dhaka_loaded and mapped_routes.is_empty():
  push_warning("Real-world map is loaded but its road window has no NPC spawn routes yet; refusing fictional fallback positions.")
  return
 var first_npc_index := get_tree().get_nodes_in_group("mapped_road_npc").size() if real_dhaka_loaded else 0
 for i in range(first_npc_index, 45):
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
  if real_dhaka_loaded:
   npc.add_to_group("mapped_road_npc")
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
  var mapped_routes: Array = real_dhaka_loader.get_vehicle_route_records()
  if mapped_routes.is_empty():
   return
  for i in range(3):
   _spawn_mapped_police_vehicle(mapped_routes)
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
 gunfire_wanted_cooldown = maxf(0.0, gunfire_wanted_cooldown - delta)
 combat_hit_marker_time = maxf(0.0, combat_hit_marker_time - delta)
 day_time = fmod(day_time + delta * 0.08, 24.0)
 event_time_left = max(0.0, event_time_left - delta)
 var sun = get_node_or_null("Sun")
 if sun:
  sun.rotation_degrees.x = -35 - sin(day_time / 24.0 * TAU) * 35.0
  sun.light_energy = 0.65 + max(0.0, sin(day_time / 24.0 * TAU)) * 0.7
 # Real-world map streaming is incremental. Keep forming the story stops from the
 # offline road graph until three mapped destinations are available; never substitute
 # fictional-city coordinates into a real map.
 if real_dhaka_loaded and real_mission_targets.size() < 3:
  real_story_setup_timer += delta
  if real_story_setup_timer >= 1.0:
   real_story_setup_timer = 0.0
   _configure_real_missions()
 var mission_factory_for_navigation := get_node_or_null("MissionFactory")
 var side_job_active := is_instance_valid(mission_factory_for_navigation) and int(mission_factory_for_navigation.get("active_index")) >= 0
 if player and mission_active and not side_job_active and (not real_dhaka_loaded or real_mission_targets.size() >= 3):
  var distance = player.position.distance_to(mission_target)
  if mission_stage == 0 and distance < 6:
   mission_stage = 1
   mission_target = real_mission_targets[1] if real_dhaka_loaded else Vector3(-36, 0, -36)
   update_marker()
   refresh_active_world_navigation()
  elif mission_stage == 1 and player.position.distance_to(mission_target) < 6:
   mission_stage = 2
   mission_target = real_mission_targets[2] if real_dhaka_loaded else Vector3(30, 0, -30)
   cash += 250
   update_marker()
   refresh_active_world_navigation()
  elif mission_stage == 2 and player.position.distance_to(mission_target) < 6:
   mission_active = false
   mission_progress = 1
   cash += 750
   update_marker()
   refresh_active_world_navigation()
 if real_dhaka_loaded and real_mission_targets.size() < 3 and mission_active:
  event_text = "STORY ROUTE LOADING • waiting for mapped road coverage"
  event_time_left = maxf(event_time_left, 1.0)
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
 autosave_timer += delta
 if autosave_timer >= AUTOSAVE_INTERVAL:
  autosave_timer = 0.0
  save_game_progress(false)
 if real_dhaka_loaded:
  mapped_traffic_maintenance_timer += delta
  if mapped_traffic_maintenance_timer >= 5.0:
   mapped_traffic_maintenance_timer = 0.0
   var traffic_count := get_tree().get_nodes_in_group("mapped_traffic_vehicle").size()
   if traffic_count < TARGET_MAPPED_TRAFFIC_COUNT:
    _spawn_mapped_traffic_vehicle()
   var police_count := get_tree().get_nodes_in_group("mapped_police_vehicle").size()
   if police_count < 3:
    _spawn_mapped_police_vehicle()
   var mapped_npc_count := get_tree().get_nodes_in_group("mapped_road_npc").size()
   if mapped_npc_count < 45:
    spawn_npcs()

func update_marker():
 var marker = get_node_or_null("MissionMarker")
 if marker:
  marker.position = mission_target + Vector3(0, 0.15, 0)

func _spawn_bullet_impact(point: Vector3, surface_normal: Vector3) -> void:
 if surface_normal.length_squared() < 0.1:
  return
 var mark := MeshInstance3D.new()
 mark.name = "TemporaryBulletImpact"
 var mesh := SphereMesh.new()
 mesh.radius = 0.042
 mesh.height = 0.084
 mesh.radial_segments = 10
 mesh.rings = 6
 mark.mesh = mesh
 mark.scale = Vector3(1.2, 1.2, 0.22)
 var material := StandardMaterial3D.new()
 material.albedo_color = Color("#292c2d")
 material.roughness = 0.98
 mark.material_override = material
 add_child(mark)
 var normal := surface_normal.normalized()
 mark.global_position = point + normal * 0.025
 var up_axis := Vector3.FORWARD if absf(normal.dot(Vector3.UP)) > 0.92 else Vector3.UP
 mark.look_at(mark.global_position + normal, up_axis)
 get_tree().create_timer(8.0).timeout.connect(func():
  if is_instance_valid(mark):
   mark.queue_free()
 )


func try_fire():
 if not player:
  return
 var hero_visual := player.get_node_or_null("HumanoidVisual")
 if is_instance_valid(hero_visual) and hero_visual.has_method("play_muzzle_flash"):
  hero_visual.call("play_muzzle_flash")
 var controlled_combat_mode: bool = is_instance_valid(combat_controller) and bool(combat_controller.active) and not bool(combat_controller.run_over) and String(combat_controller.active_mode) in ["survival", "arena_training", "street_skirmish"]
 if not controlled_combat_mode and gunfire_wanted_cooldown <= 0.0:
  wanted = min(5, wanted + 1)
  gunfire_wanted_cooldown = 2.5
 var camera: Camera3D = player.get("camera") as Camera3D
 var origin: Vector3 = camera.global_position if is_instance_valid(camera) else player.global_position + Vector3(0, 1.3, 0)
 var dir: Vector3 = -camera.global_transform.basis.z.normalized() if is_instance_valid(camera) else -player.global_transform.basis.z.normalized()
 var query = PhysicsRayQueryParameters3D.create(origin, origin + dir * 80.0)
 query.exclude = [player]
 var hit = get_world_3d().direct_space_state.intersect_ray(query)
 if hit and hit.collider and not (hit.collider is CharacterBody3D):
  _spawn_bullet_impact(hit.position, hit.normal)
 if hit and hit.collider and hit.collider is CharacterBody3D:
  if hit.collider.is_in_group("combat_enemy") and hit.collider.has_method("on_hit"):
   var target_position: Vector3 = hit.collider.global_position
   var is_headshot: bool = float(hit.position.y) >= target_position.y + COMBAT_HEADSHOT_MIN_HEIGHT
   var damage: int = 100 if is_headshot else 50
   hit.collider.call("on_hit", damage, is_headshot)
   combat_hit_marker_time = 0.18
   combat_hit_marker_headshot = is_headshot
  elif hit.collider.has_method("on_hit"):
   hit.collider.on_hit()

func respawn_player():
 if not player:
  return
 player.health = 100
 if real_dhaka_loaded and is_instance_valid(real_dhaka_loader):
  player.global_position = _nearest_mapped_respawn_position(player.global_position)
  event_text = "RESPAWNED AT A MAPPED ROAD"
 else:
  player.position = Vector3(0, 0, -12)
  event_text = "RESPAWNED IN STARTER CITY"
 event_time_left = 4.0
 wanted = 0
 cash = max(0, cash - 100)


func _nearest_mapped_respawn_position(from_position: Vector3) -> Vector3:
 var best_point := Vector3.ZERO
 var best_side := Vector3.ZERO
 var best_distance := INF
 # Prefer an actual streamed road polyline and spawn beside its centreline.
 if is_instance_valid(real_dhaka_loader) and real_dhaka_loader.has_method("get_road_routes"):
  for route in real_dhaka_loader.get_road_routes():
   if not (route is Array) or route.size() < 2:
    continue
   for point_index in range(route.size()):
    var point: Vector3 = route[point_index]
    var distance := Vector2(point.x - from_position.x, point.z - from_position.z).length()
    if distance >= best_distance:
     continue
    var before: Vector3 = route[maxi(0, point_index - 1)]
    var after: Vector3 = route[mini(route.size() - 1, point_index + 1)]
    var direction := Vector3(after.x - before.x, 0.0, after.z - before.z).normalized()
    if direction.length_squared() < 0.001:
     continue
    best_distance = distance
    best_point = point
    best_side = Vector3(-direction.z, 0.0, direction.x)
 if best_distance < INF and best_distance <= 450.0:
  return best_point + best_side * 3.0 + Vector3(0.0, 0.4, 0.0)
 # If the player's tile has unloaded after a fall, query the district-wide
 # navigation graph before falling back to a known story road stop.
 if is_instance_valid(real_dhaka_loader) and real_dhaka_loader.has_method("get_nearby_road_points"):
  var graph_points: Array = real_dhaka_loader.call("get_nearby_road_points", from_position, 0.0, 900.0)
  var graph_best := Vector3.ZERO
  var graph_distance := INF
  for point in graph_points:
   if not (point is Vector3):
    continue
   var distance := Vector2(point.x - from_position.x, point.z - from_position.z).length()
   if distance < graph_distance:
    graph_distance = distance
    graph_best = point
  if graph_distance < INF:
   return graph_best + Vector3(0.0, 0.4, 0.0)
 if not real_mission_targets.is_empty():
  return real_mission_targets[0] + Vector3(0.0, 0.4, 0.0)
 # Do not teleport into the fictional starter-city origin if no map route exists.
 return Vector3(from_position.x, 0.4, from_position.z)

func try_vehicle_interaction() -> bool:
 if not is_instance_valid(player):
  return false
 var nearest: Node3D = null
 var best_distance := 4.0
 for node in get_children():
  if node is CharacterBody3D and node.has_method("enter_player") and not bool(node.get("occupied")):
   var distance := player.global_position.distance_to(node.global_position)
   if distance < best_distance:
    best_distance = distance
    nearest = node as Node3D
 if not is_instance_valid(nearest):
  return false
 return bool(nearest.call("enter_player", player))

func refuel_nearest_vehicle(from_position: Vector3, amount: float) -> bool:
 var nearest: Node3D = null
 var best_distance := 6.0
 for node in get_children():
  if not (node is Node3D) or not node.has_method("refuel") or bool(node.get("occupied")):
   continue
  var distance: float = node.global_position.distance_to(from_position)
  if distance < best_distance:
   nearest = node
   best_distance = distance
 if not is_instance_valid(nearest):
  return false
 return bool(nearest.call("refuel", amount))


func is_red_for_axis(_axis: String, _vehicle_position: Vector3) -> bool:
 return false


# Project A-Square integrated world director.
var district_factory
var gameplay_director
var city_stream_timer := 0.0
var autosave_timer := 0.0
const AUTOSAVE_INTERVAL := 60.0
var mapped_traffic_maintenance_timer := 0.0
const TARGET_MAPPED_TRAFFIC_COUNT := 30
var real_story_setup_timer := 0.0
var real_map_spawn_positioned := false

func _configure_real_missions() -> void:
    if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader) or not is_instance_valid(player):
        return
    # Do not select objectives from a partially constructed road graph during startup.
    if real_dhaka_loader.has_method("is_navigation_index_ready") and not real_dhaka_loader.is_navigation_index_ready():
        return
    # Position the player beside a mapped street at most once. A later retry
    # must never move the player out from under an active side mission.
    var side_factory := get_node_or_null("MissionFactory")
    var side_job_active := is_instance_valid(side_factory) and int(side_factory.get("active_index")) >= 0
    if not real_map_spawn_positioned and not side_job_active:
        var nearest_point := Vector3.ZERO
        var nearest_distance := INF
        var nearest_route: Array = []
        var nearest_route_index := 0
        for route in real_dhaka_loader.get_road_routes():
            for point_index in range(route.size()):
                var road_point: Vector3 = route[point_index]
                var road_distance := Vector2(road_point.x - player.position.x, road_point.z - player.position.z).length()
                if road_distance < nearest_distance:
                    nearest_distance = road_distance
                    nearest_point = road_point
                    nearest_route = route
                    nearest_route_index = point_index
        if nearest_distance < INF and not nearest_route.is_empty():
            var before: Vector3 = nearest_route[maxi(0, nearest_route_index - 1)]
            var after: Vector3 = nearest_route[mini(nearest_route.size() - 1, nearest_route_index + 1)]
            var road_direction := (after - before).normalized()
            var sidewalk_offset := Vector3(-road_direction.z, 0, road_direction.x) * 2.5
            player.position = nearest_point + sidewalk_offset + Vector3(0, 0.2, 0)
            real_map_spawn_positioned = true

    var candidates: Array[Vector3] = []
    if real_dhaka_loader.has_method("get_nearby_road_points"):
        candidates = real_dhaka_loader.call("get_nearby_road_points", player.global_position, 25.0, 220.0)
    else:
        # Compatibility path if an older map-loader pack is mounted.
        for route in real_dhaka_loader.get_road_routes():
            for point in route:
                var p: Vector3 = point
                var distance_from_player := Vector2(p.x - player.position.x, p.z - player.position.z).length()
                if distance_from_player >= 25.0 and distance_from_player <= 220.0:
                    candidates.append(p)
    candidates.sort_custom(func(a: Vector3, b: Vector3) -> bool:
        return a.distance_to(player.position) < b.distance_to(player.position)
    )
    var unique_targets: Array[Vector3] = []
    for candidate in candidates:
        var unique := true
        for existing in unique_targets:
            if Vector2(existing.x - candidate.x, existing.z - candidate.z).length() < 35.0:
                unique = false
                break
        if unique:
            unique_targets.append(candidate)
        if unique_targets.size() >= 3:
            break
    if unique_targets.size() < 3:
        real_mission_targets.clear()
        if real_dhaka_loader.has_method("clear_navigation_route"):
            real_dhaka_loader.clear_navigation_route()
        return
    real_mission_targets = unique_targets
    mission_target = real_mission_targets[clampi(mission_stage, 0, 2)]
    if not side_job_active:
        refresh_active_world_navigation()


func refresh_active_world_navigation() -> void:
    if not real_dhaka_loaded or not is_instance_valid(real_dhaka_loader) or not is_instance_valid(player):
        return
    var side_factory := get_node_or_null("MissionFactory")
    if is_instance_valid(side_factory) and int(side_factory.get("active_index")) >= 0:
        # The side job owns the single visible road route until it is completed.
        return
    if not mission_active:
        if real_dhaka_loader.has_method("clear_navigation_route"):
            real_dhaka_loader.clear_navigation_route()
        return
    if real_mission_targets.size() < 3 or not real_dhaka_loader.has_method("navigate_to_world_position"):
        if real_dhaka_loader.has_method("clear_navigation_route"):
            real_dhaka_loader.clear_navigation_route()
        return
    # Do not allocate the full district routing graph on cold boot. The explicit
    # Navigate action or accepted mission prepares it on demand.
    if real_dhaka_loader.has_method("is_navigation_graph_ready") and not real_dhaka_loader.is_navigation_graph_ready():
        return
    var result: Dictionary = await real_dhaka_loader.navigate_to_world_position(mission_target, player)
    if not bool(result.get("ok", false)) and real_dhaka_loader.has_method("clear_navigation_route"):
        real_dhaka_loader.clear_navigation_route()

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
    # Register the catalogue under the node name used by HUD/save persistence.
    # Keep the data-driven Deshi mission catalogue in this canonical world.
    # It shares the same player, streamed map, HUD, economy, and progression.
    
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



func _nearest_real_building_entry(at: Vector3, max_distance := 3.5) -> Node3D:
 var nearest: Node3D = null
 var nearest_distance := max_distance
 for node in get_tree().get_nodes_in_group("real_building_entry"):
  if not node is Node3D:
   continue
  var distance := at.distance_to((node as Node3D).global_position)
  if distance < nearest_distance:
   nearest_distance = distance
   nearest = node as Node3D
 return nearest


func get_interior_interaction_label(at: Vector3) -> String:
 if is_instance_valid(interior_factory) and interior_factory.has_method("is_inside") and interior_factory.is_inside():
  return interior_factory.get_interaction_label(at)
 var entry := _nearest_real_building_entry(at)
 if not is_instance_valid(entry):
  return ""
 var door := entry.get_node_or_null("DoorHinge") as Node3D
 if is_instance_valid(door) and not bool(entry.get_meta("door_open", false)):
  return "OPEN DOOR"
 var seed: Dictionary = entry.get_meta("interior_seed", {})
 var category := str(seed.get("category", "")).to_lower()
 if category.contains("shop") or category.contains("retail") or category.contains("convenience"):
  return "ENTER SHOP"
 if category.contains("house") or category.contains("residential") or category.contains("home"):
  return "ENTER HOME"
 return "ENTER BUILDING"


func try_open_interior_door(at: Vector3) -> bool:
 if is_instance_valid(interior_factory) and interior_factory.has_method("is_inside") and interior_factory.is_inside():
  return false
 var entry := _nearest_real_building_entry(at)
 if not is_instance_valid(entry):
  return false
 var hinge := entry.get_node_or_null("DoorHinge") as Node3D
 if not is_instance_valid(hinge) or bool(entry.get_meta("door_open", false)):
  return false
 entry.set_meta("door_open", true)
 var tween := create_tween()
 tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
 tween.tween_property(hinge, "rotation:y", deg_to_rad(-100.0), 0.34)
 event_text = "DOOR OPENED • ENTER THE BUILDING"
 event_time_left = 3.0
 return true


func try_interior_interaction(at: Vector3) -> bool:
 if not is_instance_valid(interior_factory):
  return false
 if interior_factory.has_method("is_inside") and interior_factory.is_inside():
  return interior_factory.try_interact(at)
 var entry := _nearest_real_building_entry(at)
 if not is_instance_valid(entry) or not bool(entry.get_meta("door_open", false)):
  return false
 var seed: Dictionary = entry.get_meta("interior_seed", {})
 var direction: Vector3 = entry.get_meta("exit_direction", Vector3(0, 0, 1))
 var tile_id := str(entry.get_meta("tile_id", ""))
 interior_factory.open_interior(seed, entry.global_position, direction, tile_id, entry)
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
