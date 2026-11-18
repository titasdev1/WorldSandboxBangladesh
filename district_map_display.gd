extends Control
class_name DistrictMapDisplay

var world: Node
var expanded := false
var current_district := "Noborongo City"
var discovered: Dictionary = {}
var _player_position := Vector3.ZERO
var _player_yaw := 0.0
var _target_position := Vector3.ZERO
var _has_target := false
var _last_place_lookup_position := Vector3(1.0e20, 0.0, 1.0e20)
var _nearby_place_name := ""
var _has_place_lookup := false

const DISTRICTS := [
 {"name":"Old Town","pos":Vector2(-60,-60),"color":Color("#d9a86c")},
 {"name":"Nobo Bazar","pos":Vector2(0,0),"color":Color("#f0c95b")},
 {"name":"Shonar Core","pos":Vector2(60,-60),"color":Color("#6fc9e5")},
 {"name":"Shikkha Para","pos":Vector2(-60,60),"color":Color("#91d49b")},
 {"name":"Nodi Ghat","pos":Vector2(0,48),"color":Color("#68bce9")},
 {"name":"Karkhana Edge","pos":Vector2(60,60),"color":Color("#c69ce8")}
]

func _ready() -> void:
 mouse_filter = Control.MOUSE_FILTER_IGNORE
 queue_redraw()

func update_world(target_world: Node) -> void:
 world = target_world
 if not is_instance_valid(world):
  return
 var player = world.get("player")
 if is_instance_valid(player):
  _player_position = player.global_position
  _player_yaw = player.global_rotation.y
  if bool(world.get("real_dhaka_loaded")):
   var loader = world.get("real_dhaka_loader")
   var moved_since_place_lookup := Vector2(
    _player_position.x - _last_place_lookup_position.x,
    _player_position.z - _last_place_lookup_position.z
   ).length()
   if not _has_place_lookup or moved_since_place_lookup >= 25.0:
    _nearby_place_name = ""
    if is_instance_valid(loader) and loader.has_method("get_nearest_named_place"):
     var nearest: Dictionary = loader.call("get_nearest_named_place", _player_position, 180.0)
     _nearby_place_name = str(nearest.get("name", ""))
    _last_place_lookup_position = _player_position
    _has_place_lookup = true
   if not _nearby_place_name.is_empty():
    current_district = "Near " + _nearby_place_name
   elif is_instance_valid(loader) and loader.has_method("get_map_display_name"):
    current_district = str(loader.call("get_map_display_name"))
   else:
    current_district = "Real-world map"
  else:
   var best_name := "Noborongo City"
   var best_distance := INF
   for district in DISTRICTS:
    var point: Vector2 = district.pos
    var distance := Vector2(_player_position.x, _player_position.z).distance_to(point)
    if distance < best_distance:
     best_distance = distance
     best_name = str(district.name)
    if distance < 28.0:
     discovered[str(district.name)] = true
   current_district = best_name
 var active: bool = bool(world.get("mission_active"))
 _has_target = active
 if active:
  _target_position = world.get("mission_target")
 var mission_factory := world.get_node_or_null("MissionFactory")
 if is_instance_valid(mission_factory) and int(mission_factory.get("active_index")) >= 0:
  var side_target = mission_factory.get("active_target")
  if is_instance_valid(side_target):
   _target_position = side_target.global_position
   _has_target = true
 queue_redraw()

func get_persistence_state() -> Dictionary:
 var names: Array[String] = []
 for district_name in discovered.keys():
  names.append(str(district_name))
 names.sort()
 return {"schema_version": 1, "discovered_districts": names, "current_district": current_district}


func restore_persistence_state(state: Dictionary) -> void:
 discovered.clear()
 var allowed_names: Array[String] = []
 for district in DISTRICTS:
  allowed_names.append(str(district.name))
 var saved_names: Variant = state.get("discovered_districts", [])
 if saved_names is Array:
  for district_name in saved_names:
   var name_text := str(district_name)
   if allowed_names.has(name_text):
    discovered[name_text] = true
 var saved_current := str(state.get("current_district", "Noborongo City"))
 current_district = saved_current if allowed_names.has(saved_current) else "Noborongo City"
 queue_redraw()


func _draw() -> void:
 var bounds := Rect2(Vector2.ZERO, size)
 draw_rect(bounds, Color(0.015,0.035,0.055,0.94), true)
 draw_rect(bounds, Color("#3a8397"), false, 2.0)
 var margin := 14.0 if expanded else 10.0
 var map_rect := Rect2(Vector2(margin, margin), size - Vector2(margin*2.0, margin*2.0))
 var range_m := 300.0 if expanded else 105.0
 var center := map_rect.position + map_rect.size * 0.5
 var pixels_per_m := minf(map_rect.size.x, map_rect.size.y) / (range_m * 2.0)
 var real_map := is_instance_valid(world) and bool(world.get("real_dhaka_loaded"))
 if real_map:
  var loader = world.get("real_dhaka_loader")
  if is_instance_valid(loader) and loader.has_method("get_road_routes"):
   var routes: Array
   if loader.has_method("get_minimap_road_routes"):
    routes = loader.call("get_minimap_road_routes", _player_position, range_m)
   else:
    routes = loader.get_road_routes()
   for route in routes:
    for i in range(1, route.size()):
     var a3: Vector3 = route[i - 1]
     var b3: Vector3 = route[i]
     var a := _world_to_panel(Vector2(a3.x, a3.z), center, pixels_per_m)
     var b := _world_to_panel(Vector2(b3.x, b3.z), center, pixels_per_m)
     # Clip each road segment to the actual map viewport. The raw OSM route
     # coordinates can extend kilometres outside this moving minimap.
     _draw_clipped_line(a, b, map_rect, Color("#65727a"), 4.5 if expanded else 2.5)
     _draw_clipped_line(a, b, map_rect, Color("#c6b98d", 0.8), 1.0)
   if expanded and loader.has_method("get_road_labels"):
    for road_label in loader.get_road_labels():
     var label_points: Array = road_label.get("points", [])
     if label_points.size() < 2:
      continue
     var midpoint: Vector3 = label_points[int(label_points.size() / 2)]
     var label_position := _world_to_panel(Vector2(midpoint.x, midpoint.z), center, pixels_per_m)
     if map_rect.has_point(label_position):
      draw_string(ThemeDB.fallback_font, label_position + Vector2(4, -4), str(road_label.get("name", "")), HORIZONTAL_ALIGNMENT_LEFT, 145.0, 11, Color("#f1e7bf"))

   if loader.has_method("get_navigation_route"):
    var nav_route: Array = loader.get_navigation_route()
    for i in range(1, nav_route.size()):
     var route_a: Vector3 = nav_route[i - 1]
     var route_b: Vector3 = nav_route[i]
     var panel_a := _world_to_panel(Vector2(route_a.x, route_a.z), center, pixels_per_m)
     var panel_b := _world_to_panel(Vector2(route_b.x, route_b.z), center, pixels_per_m)
     _draw_clipped_line(panel_a, panel_b, map_rect, Color("#ffcf5c"), 4.0 if expanded else 2.5)

 else:
  for i in range(-3,4):
   var road_coord := float(i) * 24.0
   if absf(road_coord) > range_m:
    continue
   var px := center.x + (road_coord - _player_position.x) * pixels_per_m
   var py := center.y + (road_coord - _player_position.z) * pixels_per_m
   draw_line(Vector2(px,map_rect.position.y), Vector2(px,map_rect.end.y), Color("#56636a"), 5.0 if expanded else 3.0, true)
   draw_line(Vector2(map_rect.position.x,py), Vector2(map_rect.end.x,py), Color("#56636a"), 5.0 if expanded else 3.0, true)
   draw_line(Vector2(px,map_rect.position.y), Vector2(px,map_rect.end.y), Color("#c6b98d",0.8), 1.0, true)
   draw_line(Vector2(map_rect.position.x,py), Vector2(map_rect.end.x,py), Color("#c6b98d",0.8), 1.0, true)
  for district in DISTRICTS:
   var p := _world_to_panel(district.pos, center, pixels_per_m)
   if map_rect.has_point(p):
    var discovered_now: bool = discovered.has(str(district.name))
    var col: Color = district.color if (expanded or discovered_now) else Color("#65727a")
    draw_circle(p, 5.5 if expanded else 3.5, col)
    if expanded:
     draw_string(ThemeDB.fallback_font, p + Vector2(8,-7), str(district.name), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#e8f2f8") if discovered_now else Color("#9cabb5"))
 if _has_target:
  var target := _world_to_panel(Vector2(_target_position.x,_target_position.z), center, pixels_per_m)
  if map_rect.has_point(target):
   draw_circle(target, 7.0 if expanded else 5.0, Color("#ffce55"))
   draw_circle(target, 11.0 if expanded else 8.0, Color("#ffce55",0.65), false, 2.0)
 var player_point := _world_to_panel(Vector2(_player_position.x,_player_position.z), center, pixels_per_m)
 if map_rect.has_point(player_point):
  var direction := Vector2(-sin(_player_yaw), -cos(_player_yaw))
  var side := Vector2(-direction.y, direction.x)
  var tip := player_point + direction * (11.0 if expanded else 8.0)
  var left := player_point - direction * 5.0 + side * 5.0
  var right := player_point - direction * 5.0 - side * 5.0
  draw_colored_polygon(PackedVector2Array([tip,left,right]), Color("#65f0d0"))
 var label_size := 16 if expanded else 12
 draw_string(ThemeDB.fallback_font, Vector2(margin+4, size.y-margin-5), "N  ↑   •   " + current_district, HORIZONTAL_ALIGNMENT_LEFT, -1, label_size, Color("#d9f2fb"))
 if expanded:
  var map_title := "NOBORONGO CITY / DISTRICT ATLAS"
  if real_map:
   var title_loader = world.get("real_dhaka_loader")
   var real_map_name := "REAL-WORLD MAP"
   if is_instance_valid(title_loader) and title_loader.has_method("get_map_display_name"):
    real_map_name = str(title_loader.call("get_map_display_name")).to_upper()
   map_title = real_map_name + " / REAL ROAD MAP"
  draw_string(ThemeDB.fallback_font, Vector2(margin+4, margin+17), map_title, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#50d7e9"))
  if real_map:
   var loader = world.get("real_dhaka_loader")
   if is_instance_valid(loader) and loader.has_method("world_to_lat_lon"):
    var lat_lon: Vector2 = loader.world_to_lat_lon(_player_position)
    draw_string(ThemeDB.fallback_font, Vector2(margin+4, margin+34), "%.6f, %.6f" % [lat_lon.x, lat_lon.y], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color("#b6d8e5"))

func set_navigation_target(place: Dictionary) -> void:
 if not is_instance_valid(world):
  return
 var loader = world.get("real_dhaka_loader")
 if not is_instance_valid(loader) or not loader.has_method("lat_lon_to_world"):
  return
 if not place.has("latitude") or not place.has("longitude"):
  return
 _target_position = loader.lat_lon_to_world(float(place["latitude"]), float(place["longitude"]))
 _has_target = true
 queue_redraw()


func _draw_clipped_line(a: Vector2, b: Vector2, bounds: Rect2, line_color: Color, line_width: float) -> void:
 var clipped := _clip_segment_to_rect(a, b, bounds)
 if clipped.size() == 2:
  draw_line(clipped[0], clipped[1], line_color, line_width, true)


func _clip_segment_to_rect(a: Vector2, b: Vector2, bounds: Rect2) -> Array[Vector2]:
 # Liang-Barsky line clipping: retain only the piece inside the square map frame.
 var delta := b - a
 var t_min := 0.0
 var t_max := 1.0
 var p := [-delta.x, delta.x, -delta.y, delta.y]
 var q := [
  a.x - bounds.position.x,
  bounds.end.x - a.x,
  a.y - bounds.position.y,
  bounds.end.y - a.y,
 ]
 for index in range(4):
  if is_zero_approx(float(p[index])):
   if float(q[index]) < 0.0:
    return []
   continue
  var ratio := float(q[index]) / float(p[index])
  if float(p[index]) < 0.0:
   if ratio > t_max:
    return []
   t_min = maxf(t_min, ratio)
  else:
   if ratio < t_min:
    return []
   t_max = minf(t_max, ratio)
  if t_min > t_max:
   return []
 return [a + delta * t_min, a + delta * t_max]


func _world_to_panel(point: Vector2, center: Vector2, scale_value: float) -> Vector2:
 return center + Vector2(point.x - _player_position.x, point.y - _player_position.z) * scale_value

func set_expanded(value: bool) -> void:
 expanded = value
 position = Vector2(760, 82) if expanded else Vector2(1015, 78)
 size = Vector2(480, 480) if expanded else Vector2(230, 230)
 z_index = 25 if expanded else 5
 mouse_filter = Control.MOUSE_FILTER_IGNORE
 queue_redraw()
