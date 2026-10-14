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
 for i in range(-3,4):
  var road_coord := float(i) * 24.0
  if absf(road_coord) > range_m:
   continue
  var px := center.x + road_coord * pixels_per_m
  var py := center.y + road_coord * pixels_per_m
  draw_line(Vector2(px,map_rect.position.y), Vector2(px,map_rect.end.y), Color("#56636a"), 5.0 if expanded else 3.0, true)
  draw_line(Vector2(map_rect.position.x,py), Vector2(map_rect.end.x,py), Color("#56636a"), 5.0 if expanded else 3.0, true)
  draw_line(Vector2(px,map_rect.position.y), Vector2(px,map_rect.end.y), Color("#c6b98d",0.8), 1.0, true)
  draw_line(Vector2(map_rect.position.x,py), Vector2(map_rect.end.x,py), Color("#c6b98d",0.8), 1.0, true)
 # Landmark zones use named, color-coded district anchors to reinforce spatial memory.
 for district in DISTRICTS:
  var p := _world_to_panel(district.pos, center, pixels_per_m)
  if map_rect.has_point(p):
   var discovered_now: bool = discovered.has(str(district.name))
   var c: Color = district.color if (expanded or discovered_now) else Color("#65727a")
   draw_circle(p, 5.5 if expanded else 3.5, c)
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
  draw_string(ThemeDB.fallback_font, Vector2(margin+4, margin+17), "NOBORONGO CITY  /  DISTRICT ATLAS", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#50d7e9"))

func _world_to_panel(point: Vector2, center: Vector2, scale_value: float) -> Vector2:
 return center + point * scale_value

func set_expanded(value: bool) -> void:
 expanded = value
 position = Vector2(760, 82) if expanded else Vector2(1015, 78)
 size = Vector2(480, 480) if expanded else Vector2(230, 230)
 z_index = 25 if expanded else 5
 mouse_filter = Control.MOUSE_FILTER_IGNORE
 queue_redraw()
