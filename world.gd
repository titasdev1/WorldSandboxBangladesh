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
var rng := RandomNumberGenerator.new()
var police_timer := 0.0
var event_timer := 0.0
var event_text := "CITY LIFE ACTIVE"
var event_time_left := 0.0
var material_cache: Dictionary = {}
var city_asset_factory
var pbr_surface_factory
var combat_controller
var interior_active := false
var interior_return_position := Vector3.ZERO
var interior_shop_name := "Local Shop"
var interior_shop_type := "general"
var shop_interior_root: Node3D
var shop_counter_position := Vector3(0, 120, 2)
var shop_exit_position := Vector3(0, 120, -4.8)

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
 var has_real_world_map := _load_optional_real_world_map()
 if not has_real_world_map:
  build_city()
  build_landmarks()
 var street_life = load("res://street_life_factory.gd").new()
 street_life.build(self)
 spawn_player()
 spawn_traffic()
 spawn_npcs()
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
 var world_ground = box(Vector3(0, -0.5, 0), Vector3(180, 1, 180), Color("#58714b"), true, "ground")
 world_ground.name = "WorldGround"

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
 var types = [
  {"name":"Rickshaw","size":Vector3(1.5, 1.5, 2.5), "speed":4.2, "color":Color("#168447")},
  {"name":"CNG","size":Vector3(1.8, 1.5, 3.0), "speed":5.0, "color":Color("#168b70")},
  {"name":"Car","size":Vector3(2.1, 1.0, 4.0), "speed":6.2, "color":Color("#d94a45")},
  {"name":"Bus","size":Vector3(2.5, 2.6, 7.0), "speed":3.8, "color":Color("#d5a629")},
  {"name":"Motorcycle","size":Vector3(1.0, 1.2, 2.1), "speed":7.0, "color":Color("#3d4248")}
 ]
 var osm_paths: Array = get_meta("osm_road_paths", []) if has_meta("osm_road_paths") else []
 var usable_paths: Array = []
 for path in osm_paths:
  if path is Array and path.size() >= 2:
   usable_paths.append(path)
 for i in range(30):
  var t = types[rng.randi_range(0, types.size() - 1)]
  var v = CharacterBody3D.new()
  v.set_script(load("res://vehicle.gd"))
  v.world = self
  v.vehicle_type = t.name
  v.speed = t.speed * rng.randf_range(0.8, 1.2)
  v.body_size = t.size
  v.body_color = t.color
  if not usable_paths.is_empty():
   var selected_path: Array = usable_paths[rng.randi_range(0, usable_paths.size() - 1)]
   v.road_route = selected_path.duplicate()
   v.road_route_index = rng.randi_range(0, v.road_route.size() - 1)
   v.road_route_direction = 1 if rng.randi_range(0, 1) == 0 else -1
   v.road_route_lane_offset = (1.0 if i % 2 == 0 else -1.0) * v.road_route_direction
   v.position = v.call("_road_route_point", v.road_route_index)
   v.lane_axis = "osm"
  else:
   # Synthetic traffic remains the reliable fallback if OSM is unavailable.
   v.lane_axis = "z" if rng.randi_range(0, 1) == 0 else "x"
   var lane = road_x[rng.randi_range(0, road_x.size() - 1)] if v.lane_axis == "z" else road_z[rng.randi_range(0, road_z.size() - 1)]
   if v.lane_axis == "z":
    v.position = Vector3(lane + (1.8 if i % 2 == 0 else -1.8), 0, rng.randf_range(-78, 78))
   else:
    v.position = Vector3(rng.randf_range(-78, 78), 0, lane + (1.8 if i % 2 == 0 else -1.8))
  add_child(v)

func spawn_npcs():
 var osm_paths: Array = get_meta("osm_road_paths", []) if has_meta("osm_road_paths") else []
 var usable_paths: Array = []
 for path in osm_paths:
  if path is Array and path.size() >= 2:
   usable_paths.append(path)
 for i in range(45):
  var npc = CharacterBody3D.new()
  npc.name = "NPC_%02d" % i
  npc.set_script(load("res://npc.gd"))
  npc.world = self
  if not usable_paths.is_empty():
   var path: Array = usable_paths[rng.randi_range(0, usable_paths.size() - 1)]
   var point_index := rng.randi_range(0, path.size() - 1)
   var road_point: Vector3 = path[point_index]
   var previous_point: Vector3 = path[maxi(0, point_index - 1)]
   var next_point: Vector3 = path[mini(path.size() - 1, point_index + 1)]
   var tangent := next_point - previous_point
   tangent.y = 0.0
   if tangent.length_squared() > 0.001:
    tangent = tangent.normalized()
    var sidewalk_side := Vector3(-tangent.z, 0.0, tangent.x)
    var side_sign := 1.0 if rng.randi_range(0, 1) == 0 else -1.0
    road_point += sidewalk_side * rng.randf_range(4.0, 12.0) * side_sign
   npc.position = road_point
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
 var osm_paths: Array = get_meta("osm_road_paths", []) if has_meta("osm_road_paths") else []
 var usable_paths: Array = []
 for path in osm_paths:
  if path is Array and path.size() >= 2:
   usable_paths.append(path)
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
  if not usable_paths.is_empty():
   var selected_path: Array = usable_paths[rng.randi_range(0, usable_paths.size() - 1)]
   v.road_route = selected_path.duplicate()
   v.road_route_index = rng.randi_range(0, v.road_route.size() - 1)
   v.road_route_direction = 1 if i % 2 == 0 else -1
   v.road_route_lane_offset = 1.0 * v.road_route_direction
   v.position = v.call("_road_route_point", v.road_route_index)
   v.lane_axis = "osm"
  else:
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

func _setup_a_square():
    district_factory = load("res://systems/district_factory.gd").new()
    district_factory.name = "DistrictFactory"
    add_child(district_factory)
    district_factory.build(self, player)
    gameplay_director = load("res://systems/gameplay_director.gd").new()
    gameplay_director.name = "GameplayDirector"
    add_child(gameplay_director)
    gameplay_director.configure(self, player, district_factory)

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


# Interactable market stalls: spend a little cash to recover health.
func try_street_vendor(at: Vector3) -> bool:
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


# OSM-tagged storefronts are enterable and use the existing in-game economy.
func try_osm_shop_interaction(at: Vector3) -> bool:
    if interior_active:
        var exit_distance := Vector2(at.x - shop_exit_position.x, at.z - shop_exit_position.z).length()
        if exit_distance < 1.8:
            exit_osm_shop()
            return true
        var counter_distance := Vector2(at.x - shop_counter_position.x, at.z - shop_counter_position.z).length()
        if counter_distance < 2.6:
            _purchase_shop_item()
            return true
        event_text = "SHOP: WALK TO THE COUNTER OR THE EXIT"
        event_time_left = 3.0
        return true

    var nearest_shop: StaticBody3D
    var nearest_distance := 6.0
    for node in get_children():
        if not node is StaticBody3D or not node.has_meta("is_shop"):
            continue
        var distance := Vector2(at.x - node.global_position.x, at.z - node.global_position.z).length()
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_shop = node
    if not is_instance_valid(nearest_shop):
        return false
    enter_osm_shop(nearest_shop)
    return true


func enter_osm_shop(shop: StaticBody3D) -> void:
    if not is_instance_valid(shop) or not player:
        return
    interior_return_position = player.global_position
    interior_shop_type = str(shop.get_meta("shop_type", "general")).to_lower()
    interior_shop_name = str(shop.get_meta("shop_name", "Local Shop"))
    if is_instance_valid(shop_interior_root):
        shop_interior_root.queue_free()
    shop_interior_root = Node3D.new()
    shop_interior_root.name = "GeneratedShopInterior"
    add_child(shop_interior_root)
    _build_shop_interior()
    interior_active = true
    player.velocity = Vector3.ZERO
    player.global_position = Vector3(0, 120, -2.5)
    event_text = "ENTERED: " + interior_shop_name
    event_time_left = 4.0


func exit_osm_shop() -> void:
    if not interior_active:
        return
    interior_active = false
    if player:
        player.velocity = Vector3.ZERO
        player.global_position = interior_return_position + Vector3(0, 0.1, 0)
    if is_instance_valid(shop_interior_root):
        shop_interior_root.queue_free()
    shop_interior_root = null
    event_text = "LEFT: " + interior_shop_name
    event_time_left = 3.0


func _build_shop_interior() -> void:
    # A reusable generated shop shell is placed in a separate vertical layer so
    # mapped exterior geometry stays intact while the player can walk indoors.
    _interior_box("ShopFloor", Vector3(0, 119.5, 0), Vector3(12, 1, 12), Color("#75634f"), true)
    _interior_box("BackWall", Vector3(0, 123, 5.9), Vector3(12, 6, 0.35), Color("#d2c3a7"), true)
    _interior_box("LeftWall", Vector3(-5.9, 123, 0), Vector3(0.35, 6, 12), Color("#c4b49a"), true)
    _interior_box("RightWall", Vector3(5.9, 123, 0), Vector3(0.35, 6, 12), Color("#c4b49a"), true)
    # Split the front wall around an open doorway.
    _interior_box("FrontWallLeft", Vector3(-4.3, 123, -5.9), Vector3(3.2, 6, 0.35), Color("#c4b49a"), true)
    _interior_box("FrontWallRight", Vector3(4.3, 123, -5.9), Vector3(3.2, 6, 0.35), Color("#c4b49a"), true)
    _interior_box("Ceiling", Vector3(0, 126.1, 0), Vector3(12, 0.25, 12), Color("#b7ad9d"), false)
    _interior_box("ShopCounter", shop_counter_position, Vector3(5, 1.1, 0.9), Color("#80543a"), true)
    _interior_box("ProductShelf", Vector3(0, 122.4, 4.7), Vector3(7, 2.6, 0.45), Color("#5c4635"), true)
    _interior_box("ShelfProductsA", Vector3(-2.0, 123.0, 4.35), Vector3(0.75, 0.6, 0.35), Color("#d89e39"), false)
    _interior_box("ShelfProductsB", Vector3(-0.65, 123.0, 4.35), Vector3(0.75, 0.6, 0.35), Color("#529a6b"), false)
    _interior_box("ShelfProductsC", Vector3(0.7, 123.0, 4.35), Vector3(0.75, 0.6, 0.35), Color("#4e8ab8"), false)
    _interior_box("ShelfProductsD", Vector3(2.05, 123.0, 4.35), Vector3(0.75, 0.6, 0.35), Color("#b45b50"), false)
    var sign := Label3D.new()
    sign.name = "InteriorShopSign"
    sign.text = interior_shop_name
    sign.font_size = 32
    sign.pixel_size = 0.006
    sign.position = Vector3(0, 125.0, 5.65)
    sign.modulate = Color("#30251c")
    shop_interior_root.add_child(sign)
    var keeper := Node3D.new()
    keeper.name = "Shopkeeper"
    keeper.position = Vector3(0, 120, 3.0)
    var keeper_visual := HumanoidVisual.new()
    keeper_visual.name = "HumanoidVisual"
    keeper_visual.outfit_color = Color("#3c7869")
    keeper_visual.skin_color = Color("#b97850")
    keeper_visual.hair_color = Color("#24201f")
    keeper.add_child(keeper_visual)
    shop_interior_root.add_child(keeper)
    var light := OmniLight3D.new()
    light.name = "InteriorLight"
    light.position = Vector3(0, 125.2, 0)
    light.light_color = Color("#ffe3b2")
    light.light_energy = 1.4
    light.omni_range = 22.0
    shop_interior_root.add_child(light)
    shop_counter_position = Vector3(0, 120, 2.0)
    shop_exit_position = Vector3(0, 120, -4.8)


func _interior_box(node_name: String, pos: Vector3, size: Vector3, color: Color, collision: bool) -> void:
    var holder: Node3D
    if collision:
        holder = StaticBody3D.new()
        var shape_node := CollisionShape3D.new()
        var shape := BoxShape3D.new()
        shape.size = size
        shape_node.shape = shape
        holder.add_child(shape_node)
    else:
        holder = Node3D.new()
    holder.name = node_name
    var visual := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = size
    visual.mesh = mesh
    visual.material_override = make_mat(color, 0.82)
    holder.add_child(visual)
    holder.position = pos
    shop_interior_root.add_child(holder)


func _purchase_shop_item() -> void:
    if not player:
        return
    var price := 35
    var product := "snack"
    var health_gain := 18
    if interior_shop_type in ["pharmacy", "chemist", "medical_supply"]:
        price = 90
        product = "first-aid medicine"
        health_gain = 45
    elif interior_shop_type in ["restaurant", "fast_food", "food", "cafe", "bakery"]:
        price = 45
        product = "meal"
        health_gain = 25
    elif interior_shop_type in ["supermarket", "convenience", "grocery"]:
        price = 30
        product = "packed food"
        health_gain = 15

    if player.health >= 100:
        event_text = interior_shop_name + ": YOU DON'T NEED A RECOVERY ITEM"
        event_time_left = 3.5
    elif cash < price:
        event_text = "%s: NEED ৳%d FOR %s" % [interior_shop_name, price, product.to_upper()]
        event_time_left = 3.5
    else:
        cash -= price
        player.health = mini(100, player.health + health_gain)
        event_text = "%s: BOUGHT %s  -৳%d  +%d HEALTH" % [interior_shop_name, product.to_upper(), price, health_gain]
        event_time_left = 4.5


# Real-world GeoJSON replaces the synthetic grid when data is available.
# Never stack the procedural test city on top of the imported real street network.
func _load_optional_real_world_map() -> bool:
    var data_path := "res://content/realworld/area.geojson"
    if not FileAccess.file_exists(data_path):
        return false
    var importer = load("res://systems/osm_real_world_importer.gd").new()
    importer.name = "OSMRealWorldImporter"
    add_child(importer)
    if importer.import_geojson(self, data_path):
        # The downloaded starter district is roughly 2 km wide; the synthetic
        # prototype floor was only 180 m wide. Expand both render surface and
        # collision so mapped buildings outside the tiny center patch have ground.
        var ground := get_node_or_null("WorldGround")
        if ground:
            var ground_collision := ground.get_node_or_null("CollisionShape3D") as CollisionShape3D
            if ground_collision and ground_collision.shape is BoxShape3D:
                (ground_collision.shape as BoxShape3D).size = Vector3(2500, 1, 2500)
            var ground_mesh := ground.get_node_or_null("MeshInstance3D") as MeshInstance3D
            if ground_mesh and ground_mesh.mesh is BoxMesh:
                (ground_mesh.mesh as BoxMesh).size = Vector3(2500, 1, 2500)
        event_text = "REAL-WORLD MAP DATA LOADED"
        event_time_left = 6.0
        return true
    importer.queue_free()
    return false
