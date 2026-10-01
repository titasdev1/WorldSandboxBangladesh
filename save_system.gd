extends Node
class_name SaveSystem

const SAVE_PATH := "user://world_sandbox_save.json"

static func save_world(world) -> bool:
 if not world or not world.player:
  return false
 var data = {
  "version": 1,
  "cash": world.cash,
  "wanted": world.wanted,
  "rain": world.rain,
  "day_time": world.day_time,
  "mission_active": world.mission_active,
  "mission_stage": world.mission_stage,
  "mission_progress": world.mission_progress,
  "fare_requested": world.fare_requested,
  "bargain_offer": world.bargain_offer,
  "player_position": [world.player.position.x, world.player.position.y, world.player.position.z],
  "player_health": world.player.health
 }
 var file = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
 if not file:
  return false
 file.store_string(JSON.stringify(data))
 return true

static func load_world(world) -> bool:
 if not world or not FileAccess.file_exists(SAVE_PATH):
  return false
 var file = FileAccess.open(SAVE_PATH, FileAccess.READ)
 if not file:
  return false
 var parsed = JSON.parse_string(file.get_as_text())
 if typeof(parsed) != TYPE_DICTIONARY:
  return false
 world.cash = int(parsed.get("cash", world.cash))
 world.wanted = int(parsed.get("wanted", 0))
 world.rain = bool(parsed.get("rain", false))
 world.day_time = float(parsed.get("day_time", world.day_time))
 world.mission_active = bool(parsed.get("mission_active", world.mission_active))
 world.mission_stage = int(parsed.get("mission_stage", world.mission_stage))
 world.mission_progress = int(parsed.get("mission_progress", world.mission_progress))
 world.fare_requested = int(parsed.get("fare_requested", world.fare_requested))
 world.bargain_offer = int(parsed.get("bargain_offer", world.bargain_offer))
 var p = parsed.get("player_position", [])
 if p is Array and p.size() == 3 and world.player:
  world.player.position = Vector3(float(p[0]), float(p[1]), float(p[2]))
  world.player.health = int(parsed.get("player_health", 100))
 world.update_marker()
 return true
