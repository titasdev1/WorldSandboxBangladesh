extends Node
class_name SaveSystem

const SAVE_PATH := "user://world_sandbox_save.json"
const TEMP_PATH := "user://world_sandbox_save.tmp"
const BACKUP_PATH := "user://world_sandbox_save.bak"
const MAX_SAVE_BYTES := 1000000

static func save_world(world: Node) -> bool:
 if not is_instance_valid(world):
  return false
 var player: Node3D = world.get("player") as Node3D
 if not is_instance_valid(player):
  return false
 var map_context := "real_world" if bool(world.get("real_dhaka_loaded")) else "procedural_fallback"
 var player_position := player.global_position
 var player_ll: Array = []
 var target_ll: Array = []
 var real_targets_ll: Array = []
 var local_target: Array = []
 var loader: Node = world.get("real_dhaka_loader") as Node
 if map_context == "real_world" and is_instance_valid(loader) and loader.has_method("world_to_lat_lon"):
  var ll: Variant = loader.call("world_to_lat_lon", player_position)
  if ll is Vector2:
   player_ll = [ll.x, ll.y]
  var mll: Variant = loader.call("world_to_lat_lon", world.get("mission_target"))
  if mll is Vector2:
   target_ll = [mll.x, mll.y]
  var targets: Variant = world.get("real_mission_targets")
  if targets is Array:
   for p in targets:
    if p is Vector3:
     var geo: Variant = loader.call("world_to_lat_lon", p)
     if geo is Vector2:
      real_targets_ll.append([geo.x, geo.y])
  if player_ll.is_empty():
   map_context = "real_world_unlocated"
 else:
  var mt: Vector3 = world.get("mission_target")
  local_target = [mt.x, mt.y, mt.z]
 var inventory_state: Dictionary = {}
 var inventory_node: Node = world.get("inventory_system") as Node
 if is_instance_valid(inventory_node) and inventory_node.has_method("get_persistence_state"):
 	inventory_state = inventory_node.call("get_persistence_state")
 var side_missions: Dictionary = {}
 var factory: Node = world.get_node_or_null("MissionFactory")
 if is_instance_valid(factory) and factory.has_method("get_persistence_state"):
  var state: Variant = factory.call("get_persistence_state")
  if state is Dictionary:
   side_missions = state
 var discovery: Dictionary = {}
 for node in world.get_tree().get_nodes_in_group("district_map_display"):
  if is_instance_valid(node) and node.has_method("get_persistence_state"):
   discovery = node.call("get_persistence_state")
   break
 var data := {
  "version": 2, "saved_at_unix": Time.get_unix_time_from_system(),
  "map_context": map_context, "cash": int(world.get("cash")),
  "wanted": int(world.get("wanted")), "rain": bool(world.get("rain")),
  "day_time": float(world.get("day_time")), "mission_active": bool(world.get("mission_active")),
  "mission_stage": int(world.get("mission_stage")), "mission_progress": int(world.get("mission_progress")),
  "mission_target_position": local_target, "mission_target_lat_lon": target_ll,
  "real_mission_targets_lat_lon": real_targets_ll, "fare_requested": int(world.get("fare_requested")),
  "bargain_offer": int(world.get("bargain_offer")),
  "player_position": [player_position.x, player_position.y, player_position.z],
  "player_lat_lon": player_ll, "player_health": int(player.get("health")),
  "player_ammo": int(player.get("ammo")), "player_reserve_ammo": int(player.get("reserve_ammo")),
  "player_stamina": float(player.get("stamina")),
  "inventory": inventory_state, "side_missions": side_missions, "district_discovery": discovery
 }
 return _atomic_write(JSON.stringify(data))

static func _atomic_write(contents: String) -> bool:
 var file := FileAccess.open(TEMP_PATH, FileAccess.WRITE)
 if file == null:
  return false
 file.store_string(contents)
 file.flush()
 var write_error := file.get_error()
 file.close()
 if write_error != OK:
  return false
 var directory := DirAccess.open("user://")
 if directory == null:
  return false
 if directory.file_exists("world_sandbox_save.bak"):
  directory.remove("world_sandbox_save.bak")
 if directory.file_exists("world_sandbox_save.json"):
  var backup_error := directory.rename("world_sandbox_save.json", "world_sandbox_save.bak")
  if backup_error != OK:
   directory.remove("world_sandbox_save.tmp")
   return false
 var commit_error := directory.rename("world_sandbox_save.tmp", "world_sandbox_save.json")
 if commit_error != OK:
  if directory.file_exists("world_sandbox_save.bak") and not directory.file_exists("world_sandbox_save.json"):
   directory.rename("world_sandbox_save.bak", "world_sandbox_save.json")
  return false
 return true

static func _read_payload(path: String) -> Dictionary:
 if not FileAccess.file_exists(path):
  return {}
 var file := FileAccess.open(path, FileAccess.READ)
 if file == null:
  return {}
 if file.get_length() <= 0 or file.get_length() > MAX_SAVE_BYTES:
  file.close()
  return {}
 var parsed: Variant = JSON.parse_string(file.get_as_text())
 file.close()
 if not (parsed is Dictionary):
  return {}
 var version := _safe_int(parsed.get("version", 0), 0, 1, 2)
 return parsed if version >= 1 and version <= 2 else {}

static func has_valid_save() -> bool:
 return not _read_payload(SAVE_PATH).is_empty() or not _read_payload(BACKUP_PATH).is_empty()

static func _safe_int(value: Variant, fallback: int, low: int, high: int) -> int:
 if typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
  return fallback
 var n := float(value)
 if is_nan(n) or is_inf(n):
  return fallback
 return clampi(int(n), low, high)

static func _valid_array(value: Variant, length: int) -> bool:
 if not value is Array or value.size() != length:
  return false
 for item in value:
  if typeof(item) not in [TYPE_INT, TYPE_FLOAT] or is_nan(float(item)) or is_inf(float(item)):
   return false
 return true

static func _valid_position(value: Variant) -> bool:
 return _valid_array(value, 3) and absf(float(value[0])) <= 20000.0 and absf(float(value[1])) <= 1000.0 and absf(float(value[2])) <= 20000.0

static func _valid_lat_lon(value: Variant) -> bool:
 return _valid_array(value, 2) and absf(float(value[0])) <= 90.0 and absf(float(value[1])) <= 180.0

static func _inside_map(loader: Node, lat: float, lon: float) -> bool:
 var bounds: Variant = loader.get("_region_bounds_lat_lon") if is_instance_valid(loader) else []
 return bounds is Array and bounds.size() == 4 and lat >= float(bounds[0]) and lat <= float(bounds[2]) and lon >= float(bounds[1]) and lon <= float(bounds[3])

static func load_world(world: Node) -> bool:
 if not is_instance_valid(world):
  return false
 var data := _read_payload(SAVE_PATH)
 var recovered := false
 if data.is_empty():
  data = _read_payload(BACKUP_PATH)
  recovered = not data.is_empty()
 if data.is_empty():
  return false
 world.set("cash", _safe_int(data.get("cash", world.get("cash")), int(world.get("cash")), 0, 999999999))
 world.set("wanted", _safe_int(data.get("wanted", 0), 0, 0, 5))
 world.set("rain", bool(data.get("rain", false)))
 world.set("day_time", fposmod(float(data.get("day_time", world.get("day_time"))), 24.0))
 world.set("mission_active", bool(data.get("mission_active", world.get("mission_active"))))
 world.set("mission_stage", _safe_int(data.get("mission_stage", 0), 0, 0, 2))
 world.set("mission_progress", _safe_int(data.get("mission_progress", 0), 0, 0, 1))
 world.set("fare_requested", _safe_int(data.get("fare_requested", 120), 120, 0, 100000))
 world.set("bargain_offer", _safe_int(data.get("bargain_offer", 80), 80, 0, 100000))
 var player: Node3D = world.get("player") as Node3D
 if not is_instance_valid(player):
  return false
 player.set("health", _safe_int(data.get("player_health", 100), 100, 1, 100))
 player.set("stamina", clampf(float(data.get("player_stamina", 100.0)), 0.0, 100.0))
 player.set("ammo", _safe_int(data.get("player_ammo", player.get("ammo")), int(player.get("ammo")), 0, 999))
 player.set("reserve_ammo", _safe_int(data.get("player_reserve_ammo", player.get("reserve_ammo")), int(player.get("reserve_ammo")), 0, 9999))
 var inventory_node: Node = world.get("inventory_system") as Node
 var saved_inventory: Variant = data.get("inventory", {})
 if is_instance_valid(inventory_node) and saved_inventory is Dictionary and inventory_node.has_method("restore_persistence_state"):
 	inventory_node.call("restore_persistence_state", saved_inventory)
 var loader: Node = world.get("real_dhaka_loader") as Node
 var restored := false
 var map_context := str(data.get("map_context", "procedural_fallback"))
 if bool(world.get("real_dhaka_loaded")):
  var ll: Variant = data.get("player_lat_lon", [])
  if map_context == "real_world" and _valid_lat_lon(ll) and _inside_map(loader, float(ll[0]), float(ll[1])) and loader.has_method("teleport_player_to_lat_lon"):
   var move_result: Variant = loader.call("teleport_player_to_lat_lon", float(ll[0]), float(ll[1]), player)
   restored = move_result is Dictionary and bool(move_result.get("ok", false))
 elif map_context == "procedural_fallback" and _valid_position(data.get("player_position", [])):
  var p: Array = data["player_position"]
  player.global_position = Vector3(float(p[0]), float(p[1]), float(p[2]))
  restored = true
 world.set("save_location_status", "LOCATION RESTORED" if restored else "LOCATION SKIPPED: MAP CHANGED OR UNAVAILABLE")
 if bool(world.get("real_dhaka_loaded")) and is_instance_valid(loader):
  var saved_targets: Variant = data.get("real_mission_targets_lat_lon", [])
  var world_targets: Array[Vector3] = []
  if saved_targets is Array and loader.has_method("lat_lon_to_world"):
   for entry in saved_targets:
    if _valid_lat_lon(entry) and _inside_map(loader, float(entry[0]), float(entry[1])):
     world_targets.append(loader.call("lat_lon_to_world", float(entry[0]), float(entry[1])))
  if not world_targets.is_empty():
   world.set("real_mission_targets", world_targets)
  var mtll: Variant = data.get("mission_target_lat_lon", [])
  if _valid_lat_lon(mtll) and _inside_map(loader, float(mtll[0]), float(mtll[1])) and loader.has_method("lat_lon_to_world"):
   world.set("mission_target", loader.call("lat_lon_to_world", float(mtll[0]), float(mtll[1])))
  elif world.has_method("refresh_mission_targets_after_load"):
   world.call("refresh_mission_targets_after_load")
 elif _valid_position(data.get("mission_target_position", [])):
  var t: Array = data["mission_target_position"]
  world.set("mission_target", Vector3(float(t[0]), float(t[1]), float(t[2])))
 var environment_node := world.get_node_or_null("WorldEnvironment")
 if is_instance_valid(environment_node) and environment_node.environment:
  environment_node.environment.background_color = Color("#52677a") if bool(world.get("rain")) else Color("#8eb9d2")
 var factory: Node = world.get_node_or_null("MissionFactory")
 var side_state: Variant = data.get("side_missions", {})
 if is_instance_valid(factory) and side_state is Dictionary and factory.has_method("restore_persistence_state"):
  factory.call("restore_persistence_state", side_state)
 var discovery: Variant = data.get("district_discovery", {})
 if discovery is Dictionary:
  for node in world.get_tree().get_nodes_in_group("district_map_display"):
   if is_instance_valid(node) and node.has_method("restore_persistence_state"):
    node.call("restore_persistence_state", discovery)
 if world.has_method("update_marker"):
  world.call("update_marker")
 if recovered:
  world.set("event_text", "SAVE RECOVERED FROM BACKUP")
  world.set("event_time_left", 7.0)
 return true
